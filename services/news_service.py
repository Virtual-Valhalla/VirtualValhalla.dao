"""
services/news_service.py — Caché en memoria, rotación de API keys y fetch HTTP

Responsabilidades:
  - Caché en memoria tipo dict con TTL por entrada (evita llamadas repetidas a NewsAPI)
  - Rotación automática de API keys cuando una alcanza su rate limit
  - fetch_url(): petición HTTP con reintentos y sustitución de {api_key}
  - filter_articles(): limpia artículos eliminados o incompletos de NewsAPI
  - extract_article(): scraping básico de un artículo (fallback legado)
"""

import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from config import COUNTRY_NAMES, NEWSAPI_COUNTRIES, build_api_keys

logger = logging.getLogger(__name__)

# ── Caché en memoria ──────────────────────────────────────────────────────────
# Diccionario global: clave → {articles, cached_at, expires_at, ttl, scan_mode}
# Las entradas expiran automáticamente al intentar leerlas (lazy expiry).
_cache = {}


def cache_get(key):
    """
    Devuelve la entrada de caché si existe y no ha expirado.
    Si expiró, la elimina del dict y devuelve None.
    """
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() > entry['expires_at']:
        del _cache[key]
        logger.info(f"🗑️  Caché expirado para: {key}")
        return None
    age_min = int((time.time() - entry['cached_at']) / 60)
    logger.info(f"⚡ Caché HIT para '{key}' (edad: {age_min} min)")
    return entry


def cache_set(key, articles, ttl, scan_mode='direct'):
    """
    Guarda una lista de artículos en caché con un TTL en segundos.
    scan_mode indica el origen de los datos (direct, deep-scan, database-*, etc.)
    """
    now = time.time()
    _cache[key] = {
        'articles':   articles,
        'cached_at':  now,
        'expires_at': now + ttl,
        'ttl':        ttl,
        'scan_mode':  scan_mode,
    }
    logger.info(f"💾 Caché guardado para '{key}' (TTL: {ttl // 3600}h, modo: {scan_mode})")


def cache_entry_info(entry):
    """
    Calcula el tiempo restante de una entrada de caché.
    Devuelve un dict con campos listos para incluir en la respuesta JSON.
    """
    remaining = max(0, entry['expires_at'] - time.time())
    h, m = divmod(int(remaining), 3600)
    m //= 60
    return {
        'cached':     True,
        'cached_at':  datetime.fromtimestamp(entry['cached_at'], tz=timezone.utc).isoformat(),
        'expires_in': f"{h}h {m}m",
    }


# ── Rotación de API keys ──────────────────────────────────────────────────────
# API_KEYS es la lista de objetos de clave definida en config.py.
# current_api_index apunta a la clave actualmente en uso.
API_KEYS = build_api_keys()
current_api_index = 0


def get_next_available_key():
    """
    Devuelve (api_key_str, index) de la próxima clave disponible (no rate-limited).
    Si todas están rate-limited, las resetea y vuelve a la primera.
    """
    global current_api_index
    if not API_KEYS[current_api_index]['rate_limited']:
        return API_KEYS[current_api_index]['key'], current_api_index
    # Buscar la siguiente clave disponible de forma circular
    for _ in range(len(API_KEYS)):
        current_api_index = (current_api_index + 1) % len(API_KEYS)
        if not API_KEYS[current_api_index]['rate_limited']:
            logger.info(f"🔄 Rotando a API Key #{current_api_index + 1}")
            return API_KEYS[current_api_index]['key'], current_api_index
    # Todas agotadas → resetear contadores y reusar la primera
    for key_obj in API_KEYS:
        key_obj['rate_limited'] = False
    current_api_index = 0
    return API_KEYS[current_api_index]['key'], current_api_index


def mark_rate_limited(index):
    """Marca una clave como rate-limited para que la rotación la salte."""
    API_KEYS[index]['rate_limited'] = True
    logger.warning(f"⚠️ API Key #{index + 1} marcada como rate-limited")


def increment_usage(index):
    """Incrementa el contador de uso de una clave (para monitoreo)."""
    API_KEYS[index]['requests_used'] += 1


# ── Fetch HTTP con rotación de keys ──────────────────────────────────────────

def fetch_url(url_template, max_retries=None):
    """
    Realiza una petición GET a NewsAPI sustituyendo '{api_key}' en la URL.

    - Rota automáticamente a la siguiente clave si recibe HTTP 429 (rate limit).
    - Reintenta hasta max_retries veces (por defecto: 2 × número de claves).
    - Lanza una excepción si todas las claves están agotadas o hay otro error.

    Args:
        url_template: URL con el literal {api_key} como placeholder.
        max_retries:  número máximo de intentos (None = 2 × len(API_KEYS)).

    Returns:
        dict con la respuesta JSON de NewsAPI (status, articles, etc.)
    """
    if max_retries is None:
        max_retries = len(API_KEYS) * 2

    for attempt in range(max_retries):
        api_key, idx = get_next_available_key()
        url = url_template.replace('{api_key}', api_key)
        try:
            logger.info(f"📨 Fetch intento {attempt + 1} → {url.split('apiKey')[0]}...")
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            increment_usage(idx)
            if data.get('status') != 'ok':
                raise Exception(f"API error: {data.get('message', 'unknown')}")
            return data
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                mark_rate_limited(idx)
                if attempt < max_retries - 1:
                    continue
                raise Exception("Todas las API Keys están rate-limited")
            raise
        except Exception:
            raise


def filter_articles(articles):
    """
    Filtra artículos inválidos devueltos por NewsAPI.

    Criterios de exclusión:
      - Sin título, o título vacío/solo espacios
      - Título o descripción marcados como '[Removed]' por NewsAPI
      - URL vacía, None, o que contenga '[Removed]'
      - Fuente marcada como '[Removed]'
      - Artículos duplicados (mismo URL)

    Returns:
        Lista de artículos válidos, sin duplicados por URL.
    """
    seen_urls = set()
    valid = []
    for a in articles:
        title  = (a.get('title') or '').strip()
        url    = (a.get('url')   or '').strip()
        source = (a.get('source') or {}).get('name', '')
        desc   = (a.get('description') or '').strip()

        # Descartar si el título está vacío o es una marca de eliminado
        if not title or title == '[Removed]':
            continue
        # Descartar si la URL está vacía o contiene la marca de eliminado
        if not url or '[Removed]' in url:
            continue
        # Descartar si la fuente está marcada como eliminada
        if source == '[Removed]':
            continue
        # Descartar si la descripción es la única cadena de eliminado (artículo fantasma)
        if desc == '[Removed]' and not a.get('content'):
            continue
        # Descartar duplicados por URL
        if url in seen_urls:
            continue

        seen_urls.add(url)
        valid.append(a)
    return valid


# ── Scraping de artículo (fallback legado) ────────────────────────────────────

def extract_video(soup):
    """
    Busca un vídeo incrustado en la página en este orden de prioridad:
    YouTube iframe → meta og:video → tag <video>.
    Devuelve un dict {type, url} o {type: None, url: None} si no hay vídeo.
    """
    for iframe in soup.find_all('iframe'):
        src = iframe.get('src', '')
        if 'youtube.com/embed/' in src or 'youtu.be/' in src:
            # Asegurar que el autoplay está desactivado
            if 'autoplay' not in src:
                src += ('&' if '?' in src else '?') + 'autoplay=0'
            return {'type': 'youtube', 'url': src}
    og = soup.find('meta', property='og:video')
    if og and og.get('content'):
        return {'type': 'video', 'url': og['content']}
    vid = soup.find('video')
    if vid:
        src = vid.get('src') or (vid.find('source') or {}).get('src', '')
        if src:
            return {'type': 'video', 'url': src}
    return {'type': None, 'url': None}


def extract_article(url):
    """
    Scraping básico de un artículo externo (usado como último recurso).
    El ContentExtractor de services/content_extractor.py es la versión completa;
    esta función es un fallback simplificado que solo extrae título, párrafos y vídeo.

    Returns:
        dict con title, content (hasta 5000 chars) y video.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(r.text, 'html.parser')
        title   = soup.title.string if soup.title else 'Sin título'
        content = '\n'.join(p.get_text() for p in soup.find_all('p'))
        video   = extract_video(soup)
        return {'title': title, 'content': content[:5000], 'video': video}
    except Exception as e:
        return {'title': 'Error', 'content': f'No se pudo cargar: {str(e)}',
                'video': {'type': None, 'url': None}}
