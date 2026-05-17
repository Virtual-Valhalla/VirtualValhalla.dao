"""
routes/api_routes.py — Blueprint de endpoints de datos (NewsAPI + BD)

Endpoints:
  GET  /country-news   — noticias de un país (caché + NewsAPI + BD)
  GET  /article        — extracción de contenido completo de un artículo
  GET  /cache-status   — estado del caché en memoria
  POST /cache-clear    — vaciar caché (global o por país)
  GET  /api-status     — estado de las API keys
  POST /reset-api-limits — resetear contadores de uso de keys

Estrategia de obtención de noticias (/country-news):
  1. Verificar caché en memoria → devolver si HIT
  2. Consultar BD (artículos scrapeados por el scheduler)
  3. Complementar con NewsAPI si hay menos de 15 artículos:
     - código en NEWSAPI_COUNTRIES → top-headlines?country=XX
     - código fuera del set        → everything?q="Nombre País" (Deep-Scan tier 1)
     - si tier 1 vacío             → everything con ventana de 30 días (tier 2)
  4. Guardar resultado en caché y devolver

El campo 'scan_mode' en la respuesta indica el origen de los datos.
"""

import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
import services.news_service as svc
from config import (CACHE_TTL_COUNTRY, CACHE_TTL_GLOBAL,
                    COUNTRY_NAMES, NEWSAPI_COUNTRIES)
from models import database as db
from services.content_extractor import content_extractor

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

# Categorías válidas que acepta NewsAPI (en inglés)
VALID_CATEGORIES = {'business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology'}

# Mapa de nombres de categoría de NewsAPI (inglés) a nombres en español usados en la BD
CATEGORY_MAP = {
    'technology':     'Tecnología',
    'business':       'Economía',
    'sports':         'Deportes',
    'entertainment':  'Entretenimiento',
    'health':         'Salud',
    'science':        'Ciencia',
    'politics':       'Política',
    'general':        'General',
    '':               None,  # sin filtro de categoría
}


def _quote_name(country_name):
    """Envuelve el nombre del país en comillas para búsqueda exacta en NewsAPI."""
    return f'"{country_name}"'


def build_everything_tier1(country_name, category=''):
    """
    Construye la URL de NewsAPI /everything para búsqueda de 7 días.
    Tier 1: busca en el título del artículo con categoría si se especifica.
    El placeholder {api_key} se sustituye en fetch_url().
    """
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
    base  = _quote_name(country_name)
    if category and category != 'general':
        term = f'{base} AND {category}'
    else:
        term = base
    q = requests.utils.quote(term)
    return (
        f'https://newsapi.org/v2/everything'
        f'?q={q}&searchIn=title&sortBy=publishedAt&from={since}&pageSize=15&apiKey={{api_key}}'
    )


def build_everything_tier2(country_name):
    """
    Construye la URL de NewsAPI /everything para búsqueda amplia de 30 días.
    Tier 2: fallback sin filtro de categoría ni restricción de campo, ventana mayor.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S')
    q = requests.utils.quote(_quote_name(country_name))
    return (
        f'https://newsapi.org/v2/everything'
        f'?q={q}&sortBy=publishedAt&from={since}&pageSize=15&apiKey={{api_key}}'
    )


def fetch_everything_with_fallback(country_name, category=''):
    """
    Intenta obtener noticias para un país no soportado en top-headlines.
    Tier 1 → Tier 2 si el primer intento devuelve artículos vacíos.

    Returns:
        (articles, tier_number) — lista de artículos y el tier usado (1 o 2)
    """
    url1 = build_everything_tier1(country_name, category)
    data = svc.fetch_url(url1)
    articles = svc.filter_articles(data.get('articles', []))
    if articles:
        return articles, 1
    logger.info(
        f"⬇️ Tier 1 vacío para '{country_name}' [{category}] → "
        f"Tier 2: búsqueda amplia 30 días sin filtro de idioma"
    )
    url2 = build_everything_tier2(country_name)
    data = svc.fetch_url(url2)
    articles = svc.filter_articles(data.get('articles', []))
    return articles, 2


def get_db_news_by_country(country_code, category='', limit=200):
    """
    Consulta la BD local en busca de noticias.
    Mapea el nombre de categoría de la API (en inglés) al nombre en español
    antes de consultar, ya que la BD almacena las categorías en español.

    Args:
        country_code: código ISO (no se filtra por país en la BD — todas las noticias son globales)
        category:     nombre de categoría en inglés (de NewsAPI)
        limit:        máximo de artículos a devolver

    Returns:
        Lista de artículos formateados al esquema de NewsAPI para compatibilidad con el frontend.
    """
    try:
        db_categoria = CATEGORY_MAP.get(category, None) if category else None
        news_items = db.get_news(categoria=db_categoria, limit=limit)

        articles = []
        for item in news_items:
            articles.append({
                'title':       item.get('titulo', 'Sin título'),
                'description': item.get('resumen') or item.get('contenido', ''),
                'url':         item.get('url_original', ''),
                'urlToImage':  item.get('imagen') or None,
                'imagen':      item.get('imagen') or None,
                'publishedAt': item.get('fecha_publicacion'),
                'source':      {'id': None, 'name': item.get('source_name', 'BD Local')},
                'content':     item.get('contenido', ''),
                'categoria':   item.get('categoria', 'General'),
                'db_source':   True,  # marca para distinguir origen en el frontend
            })

        logger.info(f"📚 BD: {len(articles)} noticias para '{country_code}' [cat={db_categoria}]")
        return articles
    except Exception as e:
        logger.warning(f"⚠️ Error al consultar BD: {e}")
        return []


# ── Endpoint principal ────────────────────────────────────────────────────────

@api_bp.route('/country-news')
def country_news():
    """
    Devuelve noticias para un país o el feed global.

    Query params:
      country  — código ISO-A2 en minúsculas, o 'world'/'global' para feed global
      category — categoría de noticias (business, sports, technology, etc.)
      force    — si 'true', ignora el caché y fuerza una nueva consulta

    Estrategia de obtención (ver docstring del módulo).
    """
    code     = request.args.get('country',  'world').lower().strip()
    category = request.args.get('category', '').lower().strip()
    force    = request.args.get('force',    '').lower() == 'true'

    # Normalizar categoría inválida a vacío (sin filtro)
    if category not in VALID_CATEGORIES:
        category = ''

    # La clave de caché incluye la categoría si se especifica
    cache_key = f"{code}:{category}" if category else code
    logger.info(f"📡 Solicitud para: '{code}' cat='{category}' force={force}")

    # ── PASO 0: Caché en memoria ──────────────────────────────────────────────
    if not force:
        cached = svc.cache_get(cache_key)
        if cached:
            info = svc.cache_entry_info(cached)
            return jsonify({
                'status':    'ok',
                'articles':  cached['articles'],
                'scan_mode': cached.get('scan_mode', 'direct'),
                **info,
            }), 200

    try:
        scan_mode = 'direct'
        articles = []
        ttl = CACHE_TTL_COUNTRY

        # ── PASO 1: BD local ─────────────────────────────────────────────────
        db_articles = get_db_news_by_country(code, category=category, limit=200)
        if db_articles:
            articles.extend(db_articles)
            scan_mode = 'database-primary'
            logger.info(f"✅ BD para '{code}' cat='{category}': {len(db_articles)} artículos")

        # ── PASO 2: NewsAPI como complemento ──────────────────────────────────
        try:
            api_articles = None

            if code in ('world', 'global'):
                # Feed global: top-headlines en inglés sin filtro de país
                cat_param = f'&category={category}' if category else ''
                url = (f'https://newsapi.org/v2/top-headlines'
                       f'?language=en&pageSize=15{cat_param}&apiKey={{api_key}}')
                data         = svc.fetch_url(url)
                api_articles = svc.filter_articles(data.get('articles', []))
                ttl          = CACHE_TTL_GLOBAL
                if articles:
                    scan_mode = 'database-global-hybrid'

            elif code in NEWSAPI_COUNTRIES:
                # País soportado en top-headlines directamente
                cat_param = f'&category={category}' if category else ''
                url = (f'https://newsapi.org/v2/top-headlines'
                       f'?country={code}&pageSize=15{cat_param}&apiKey={{api_key}}')
                data         = svc.fetch_url(url)
                api_articles = svc.filter_articles(data.get('articles', []))
                if not api_articles:
                    # top-headlines devolvió vacío → usar deep-scan
                    country_name = COUNTRY_NAMES.get(code, code.upper())
                    logger.info(f"🔄 top-headlines vacío → everything tiered para '{country_name}'")
                    api_articles, tier = fetch_everything_with_fallback(country_name, category)
                    scan_mode = f'database-deep-scan-t{tier}' if articles else f'deep-scan-t{tier}'

            else:
                # País sin soporte nativo → deep-scan por nombre del país
                country_name = COUNTRY_NAMES.get(code, code.replace('_', ' ').title())
                logger.info(f"🌍 ISO '{code}' no soportado → Deep-Scan para '{country_name}'")
                api_articles, tier = fetch_everything_with_fallback(country_name, category)
                scan_mode = f'database-deep-scan-t{tier}' if articles else f'deep-scan-t{tier}'

            # Combinar con artículos de BD hasta un máximo de 15 artículos de API
            if api_articles:
                if len(articles) < 15:
                    articles.extend(api_articles[:15 - len(articles)])
                    if scan_mode == 'database-primary':
                        scan_mode = 'database-api-hybrid'

        except Exception as e:
            logger.warning(f"⚠️ Error al obtener noticias de API: {e}")
            if articles:
                # Tenemos artículos de BD — continuar sin los de API
                logger.info(f"✅ Continuando solo con noticias de BD ({len(articles)} artículos)")
            else:
                raise  # sin noticias de ningún origen → error completo

        # ── RESULTADO FINAL ───────────────────────────────────────────────────
        if not articles:
            label = COUNTRY_NAMES.get(code, code.replace('_', ' ').title())
            return jsonify({
                'status':    'warning',
                'message':   f'Sin noticias disponibles para {label}.',
                'articles':  [],
                'cached':    False,
                'scan_mode': scan_mode,
            }), 200

        # Guardar en caché para evitar repetir la consulta en las próximas horas
        svc.cache_set(cache_key, articles, ttl, scan_mode=scan_mode)
        logger.info(f"✅ {cache_key}: {len(articles)} artículos [{scan_mode}]")
        return jsonify({
            'status':    'ok',
            'articles':  articles,
            'cached':    False,
            'scan_mode': scan_mode,
        }), 200

    except requests.exceptions.Timeout:
        logger.error(f"⏱️ TIMEOUT para {code}")
        return jsonify({'status': 'error', 'type': 'timeout',
                        'message': 'Servidor tardó demasiado. Intenta de nuevo.',
                        'articles': [], 'scan_mode': 'error'}), 504
    except requests.exceptions.ConnectionError:
        logger.error(f"🔌 CONNECTION ERROR para {code}")
        return jsonify({'status': 'error', 'type': 'connection',
                        'message': 'Error de conexión con NewsAPI.',
                        'articles': [], 'scan_mode': 'error'}), 503
    except Exception as e:
        logger.error(f"❌ ERROR para {code}: {e}")
        return jsonify({'status': 'error', 'type': 'unknown',
                        'message': 'Error inesperado. Intenta más tarde.',
                        'details': str(e), 'articles': [],
                        'scan_mode': 'error'}), 500


def _db_fallback(url: str) -> dict | None:
    """
    Intenta obtener el contenido de un artículo desde la BD local.
    Se usa cuando el scraping en vivo falla (bloqueo 403, timeout, etc.).
    Devuelve None si el artículo no está almacenado.
    """
    stored = db.get_news_by_url(url)
    if not stored:
        return None
    contenido = stored.get("contenido") or stored.get("resumen") or ""
    return {
        "titulo":       stored.get("titulo", ""),
        "contenido":    contenido,
        "resumen":      stored.get("resumen", ""),
        "imagen":       stored.get("imagen", ""),
        "multimedia":   stored.get("multimedia", []),
        "url_original": url,
        "_source":      "db",  # indica al cliente el origen del contenido
    }


@api_bp.route('/article')
def get_article():
    """
    Extrae el contenido completo de un artículo externo.

    Prioridad:
      1. Scraping en vivo via ContentExtractor (og:image, párrafos limpios, multimedia)
      2. Fallback a BD si el scraping fue bloqueado o devolvió contenido vacío

    Query params:
      url — URL del artículo a extraer (obligatorio)

    Response:
      titulo, contenido, resumen, imagen, multimedia (list), url_original
    """
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Falta URL'}), 400

    try:
        data = content_extractor.extract(url)

        # Si la extracción fue bloqueada o el contenido está vacío, usar BD como respaldo
        if data.get("_blocked") or not data.get("contenido"):
            if data.get("_blocked"):
                logger.info("🔄 Extracción bloqueada → usando contenido de BD para %s", url)
            fallback = _db_fallback(url)
            if fallback:
                # Conservar imagen/multimedia del scraping si existen (pueden ser mejores)
                if not data.get("imagen"):
                    data["imagen"] = fallback["imagen"]
                if not data.get("multimedia"):
                    data["multimedia"] = fallback["multimedia"]
                data["contenido"] = fallback["contenido"]
                data["resumen"]   = data["resumen"] or fallback["resumen"]
                data["titulo"]    = data["titulo"]  or fallback["titulo"]
            data.pop("_blocked", None)

        data.pop("_blocked", None)
        return jsonify(data)

    except Exception as e:
        logger.warning("⚠️ Error extrayendo artículo %s: %s", url, e)
        # Último intento: BD completa, luego scraping legado
        fallback = _db_fallback(url)
        if fallback:
            return jsonify(fallback)
        return jsonify(svc.extract_article(url))


# ── Endpoints de monitoreo ────────────────────────────────────────────────────

@api_bp.route('/cache-status')
def cache_status():
    """Devuelve el estado completo del caché en memoria y el uso de API keys."""
    now = time.time()
    entries = []
    for key, entry in svc._cache.items():
        remaining = max(0, entry['expires_at'] - now)
        h, rem = divmod(int(remaining), 3600)
        m = rem // 60
        entries.append({
            'country':    key,
            'articles':   len(entry['articles']),
            'cached_at':  datetime.fromtimestamp(entry['cached_at'], tz=timezone.utc).isoformat(),
            'expires_in': f"{h}h {m}m",
            'ttl_hours':  entry['ttl'] // 3600,
            'scan_mode':  entry.get('scan_mode', 'direct'),
        })
    entries.sort(key=lambda x: x['country'])
    total_requests = sum(k['requests_used'] for k in svc.API_KEYS)
    return jsonify({
        'cached_countries':   len(entries),
        'total_api_requests': total_requests,
        'entries': entries,
        'api_keys': [
            {'index': i + 1, 'requests_used': k['requests_used'],
             'rate_limited': k['rate_limited']}
            for i, k in enumerate(svc.API_KEYS)
        ],
    }), 200


@api_bp.route('/cache-clear', methods=['POST'])
def cache_clear():
    """
    Vacía el caché en memoria.
    Si se pasa ?country=XX, elimina solo esa entrada.
    Sin parámetros, limpia todo el caché.
    """
    country = request.args.get('country')
    if country:
        removed = svc._cache.pop(country.lower(), None)
        msg = f"Caché de '{country}' eliminado" if removed else f"'{country}' no estaba en caché"
    else:
        count = len(svc._cache)
        svc._cache.clear()
        msg = f"{count} entradas de caché eliminadas"
    logger.info(f"🗑️  {msg}")
    return jsonify({'status': 'success', 'message': msg}), 200


@api_bp.route('/api-status')
def api_status():
    """Devuelve el estado de uso de las API keys (sin revelar los valores de las claves)."""
    return jsonify({
        'current_key_index': svc.current_api_index,
        'keys': [
            {'index': i, 'requests_used': k['requests_used'], 'rate_limited': k['rate_limited']}
            for i, k in enumerate(svc.API_KEYS)
        ],
    }), 200


@api_bp.route('/reset-api-limits', methods=['POST'])
def reset_limits():
    """Resetea los contadores de uso y flags de rate-limit de todas las API keys."""
    for key_obj in svc.API_KEYS:
        key_obj['requests_used'] = 0
        key_obj['rate_limited'] = False
    return jsonify({'status': 'success', 'message': 'Límites reseteados'}), 200
