"""
scrapers/html_scraper.py — Scraping de artículos desde páginas HTML de noticias

Proceso:
  1. Descarga la página índice de la fuente (portada o sección)
  2. Extrae enlaces de artículos usando una heurística de filtrado
  3. Descarga y extrae el contenido de cada artículo usando ContentExtractor
  4. Normaliza los resultados al esquema de la BD

Limitaciones deliberadas:
  - Máximo 10 artículos por fuente para no sobrecargar el servidor remoto
  - Se descartan links de navegación, redes sociales, páginas de autor, etc.
  - Sin autenticación ni bypass de muros de pago: solo contenido público
"""

import logging
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from services.content_extractor import content_extractor

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
}

# Número máximo de artículos a extraer por fuente en cada ciclo de ingesta
MAX_ARTICLES_PER_SOURCE = 10


def _is_article_link(href, base_url):
    """
    Heurística para distinguir enlaces de artículos de los de navegación.

    Excluye:
      - Anclas internas (#) y javascript:
      - Páginas de taxonomía (/tag/, /category/, /author/, /page/)
      - Páginas institucionales (/about, /contact, /privacy, /terms)
      - Redes sociales (twitter, facebook, instagram, youtube, whatsapp)
      - Emails (mailto:)

    Incluye solo URLs con profundidad de path >= 2 segmentos
    (p. ej. /sección/título-del-artículo).

    Returns:
        True si el href parece un artículo; False en caso contrario.
    """
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return False
    skip_patterns = (
        "/tag/", "/category/", "/author/", "/page/",
        "/about", "/contact", "/privacy", "/terms",
        "twitter.com", "facebook.com", "instagram.com",
        "youtube.com", "whatsapp", "mailto:"
    )
    for pat in skip_patterns:
        if pat in href:
            return False
    # Exigir al menos dos segmentos de path para descartar la portada y secciones raíz
    from urllib.parse import urlparse
    parsed = urlparse(href)
    path_depth = len([p for p in parsed.path.split("/") if p])
    return path_depth >= 2


def _absolute_url(href, base_url):
    """Convierte una URL relativa en absoluta usando la URL base de la fuente."""
    from urllib.parse import urljoin
    return urljoin(base_url, href)


def scrape_html(source: dict, max_articles: int = MAX_ARTICLES_PER_SOURCE) -> list:
    """
    Scraping completo de una fuente HTML.

    Flujo:
      1. GET a source['url'] para obtener la página índice
      2. Recopilar hasta max_articles * 3 candidatos de links válidos
      3. Extraer los primeros max_articles con ContentExtractor
      4. Descartar artículos sin título válido (errores o páginas de error)
      5. Asignar fuente_id y fecha de ingesta a cada artículo

    Args:
        source:       dict de la BD con campos url e id
        max_articles: límite de artículos a extraer (por defecto 10)

    Returns:
        Lista de dicts normalizados listos para upsert_news().
        Devuelve [] en caso de error de red o si no se encuentran artículos válidos.
    """
    url = source["url"]
    source_id = source["id"]
    logger.info("🔎 HTML scrape: %s", url)

    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        logger.error("❌ Error fetching HTML index %s: %s", url, e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    seen = set()

    # Recopilar candidatos de links sin duplicados
    for a in soup.find_all("a", href=True):
        href = _absolute_url(a["href"], url)
        if href not in seen and _is_article_link(href, url):
            seen.add(href)
            links.append(href)
        # Acumular 3× el máximo para tener margen si algunos fallan
        if len(links) >= max_articles * 3:
            break

    articles = []
    for link in links[:max_articles]:
        try:
            data = content_extractor.extract(link, timeout=8)
            # Descartar páginas de error, portadas o artículos sin título detectado
            if not data.get("titulo") or data["titulo"] in ("Error", "Sin título"):
                continue
            data["fuente_id"] = source_id
            # La fecha de extracción sirve como fecha de publicación (no hay pubDate en HTML)
            data["fecha_publicacion"] = datetime.now(timezone.utc).isoformat()
            articles.append(data)
        except Exception as e:
            logger.warning("⚠️ Error extrayendo %s: %s", link, e)
            continue

    logger.info("✅ HTML %s → %d artículos", url, len(articles))
    return articles
