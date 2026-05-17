"""
scrapers/rss_scraper.py — Descarga y parseo de feeds RSS/Atom

Proceso:
  1. Descarga el feed con requests usando cabeceras de bot amigable
  2. Parsea el XML con BeautifulSoup (parser 'xml' de lxml)
  3. Extrae hasta 30 items, normalizando todos los campos al esquema de la BD
  4. Infiere la categoría desde el nivel de fuente; si es 'General', la deduce
     del path de la URL de cada artículo

Compatibilidad:
  - RSS 2.0 (<item>, <pubDate>, <description>, <enclosure>)
  - Atom  (<entry>, <published>, <updated>, <content>)
  - Media RSS (<media:content>, <media:thumbnail>)
  - content:encoded para artículos con HTML completo

Devuelve:
  Lista de dicts listos para pasar a upsert_news(), con los campos:
  titulo, contenido, resumen, imagen, fecha_publicacion,
  fuente_id, url_original, multimedia, categoria
"""

import logging
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from services.media_parser import media_parser

logger = logging.getLogger(__name__)

# Cabeceras que identifican el bot pero sin fingir ser un navegador humano
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsGloboBot/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _parse_date(date_str):
    """
    Intenta parsear las fechas más comunes en feeds RSS/Atom.
    Si ningún formato coincide, devuelve la cadena original (la BD acepta texto ISO).
    Si la cadena es None o vacía, devuelve la fecha/hora actual en UTC.
    """
    if not date_str:
        return datetime.now(timezone.utc).isoformat()
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",    # RFC 2822 (RSS clásico)
        "%a, %d %b %Y %H:%M:%S %Z",    # RFC 2822 con timezone como texto
        "%Y-%m-%dT%H:%M:%S%z",          # ISO 8601 con offset
        "%Y-%m-%dT%H:%M:%SZ",           # ISO 8601 UTC
        "%Y-%m-%d %H:%M:%S",            # Formato SQL simple
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).isoformat()
        except (ValueError, TypeError):
            continue
    return date_str  # fallback: devolver tal cual


def _extract_image_from_item(item):
    """
    Busca la imagen del artículo en varios lugares del item RSS,
    en orden de calidad decreciente:
      1. <media:content url="…"> o <media:thumbnail url="…">
      2. <enclosure type="image/…" url="…">
      3. Primer <img src="…"> dentro del HTML de la descripción

    Devuelve la URL de la imagen o cadena vacía si no se encuentra.
    """
    # Media RSS (estándar extendido muy usado por medios de noticias)
    for tag in ("media:content", "media:thumbnail"):
        el = item.find(tag)
        if el and el.get("url"):
            return el["url"]

    # Enclosure (adjunto binario, típicamente imagen)
    enc = item.find("enclosure")
    if enc and enc.get("type", "").startswith("image"):
        return enc.get("url", "")

    # Imagen dentro del HTML de la descripción (búsqueda anidada)
    desc = item.find("description")
    if desc:
        html = desc.get_text()
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find("img", src=True)
        if img:
            return img["src"]

    return ""


def _infer_categoria_from_url(url: str) -> str:
    """
    Deduce la categoría de un artículo a partir del path de su URL.
    Mapea palabras clave en inglés (segmentos de URL) a categorías en español.
    Devuelve 'General' si no hay coincidencia.

    Ejemplos:
      /technology/ai-news  → 'Tecnología'
      /sports/football     → 'Deportes'
      /business/markets    → 'Economía'
    """
    url_lower = url.lower()
    mapping = {
        "technology":    "Tecnología",
        "tech":          "Tecnología",
        "science":       "Ciencia",
        "health":        "Salud",
        "sport":         "Deportes",
        "sports":        "Deportes",
        "business":      "Economía",
        "economy":       "Economía",
        "finance":       "Economía",
        "money":         "Economía",
        "entertainment": "Entretenimiento",
        "culture":       "Entretenimiento",
        "arts":          "Entretenimiento",
        "politics":      "Política",
        "world":         "General",
        "news":          "General",
        "environment":   "Medio Ambiente",
        "climate":       "Medio Ambiente",
        "security":      "Ciberseguridad",
        "cyber":         "Ciberseguridad",
    }
    for keyword, categoria in mapping.items():
        if f"/{keyword}" in url_lower or f"/{keyword}/" in url_lower:
            return categoria
    return "General"


def scrape_rss(source: dict) -> list:
    """
    Descarga y parsea un feed RSS/Atom completo.

    Estrategia de categoría:
      - Si la fuente tiene una categoría definida (distinta de 'General'),
        todos sus artículos heredan esa categoría.
      - Si es 'General', se intenta deducir la categoría del path de cada URL.

    Args:
        source: dict de la BD con al menos los campos: url, id, categoria

    Returns:
        Lista de artículos normalizados (hasta 30 por feed).
        Devuelve [] en caso de error de red o feed vacío.
    """
    url = source["url"]
    source_id = source["id"]
    source_categoria = source.get("categoria") or "General"
    logger.info("📡 RSS fetch: %s [cat: %s]", url, source_categoria)

    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        logger.error("❌ Error fetching RSS %s: %s", url, e)
        return []

    # Parsear con lxml-xml para soporte completo de namespaces (media:, content:, etc.)
    soup = BeautifulSoup(resp.content, "xml")
    # Soportar tanto RSS (<item>) como Atom (<entry>)
    items = soup.find_all("item") or soup.find_all("entry")

    articles = []
    for item in items[:30]:  # limitar a los 30 más recientes del feed
        try:
            # Título (obligatorio — se salta el item si falta)
            title_tag = item.find("title")
            titulo = title_tag.get_text(strip=True) if title_tag else ""
            if not titulo:
                continue

            # URL del artículo (RSS usa <link>, Atom usa <link href="…">)
            link_tag = item.find("link")
            if link_tag and link_tag.string:
                url_original = link_tag.string.strip()
            elif link_tag and link_tag.get("href"):
                url_original = link_tag["href"].strip()
            else:
                url_original = ""

            # Categoría: heredada de la fuente o inferida de la URL
            if source_categoria and source_categoria != "General":
                categoria = source_categoria
            else:
                categoria = _infer_categoria_from_url(url_original) if url_original else "General"

            # Resumen (limitado a 500 chars, con HTML limpiado)
            desc_tag = item.find("description") or item.find("summary")
            raw_desc = desc_tag.get_text(strip=True) if desc_tag else ""
            desc_soup = BeautifulSoup(raw_desc, "html.parser")
            resumen = desc_soup.get_text(separator=" ", strip=True)[:500]

            # Contenido completo (prioriza content:encoded > content > description)
            content_tag = (
                item.find("content:encoded")
                or item.find("content")
                or item.find("description")
            )
            raw_content = content_tag.get_text(strip=True) if content_tag else resumen
            content_soup = BeautifulSoup(raw_content, "html.parser")
            contenido = content_soup.get_text(separator="\n", strip=True)[:6000]

            # Imagen principal
            imagen = _extract_image_from_item(item)

            # Fecha de publicación
            date_tag = item.find("pubDate") or item.find("published") or item.find("updated")
            fecha = _parse_date(date_tag.get_text(strip=True) if date_tag else None)

            # Multimedia embebida en el contenido del feed
            multimedia = media_parser.parse_text(raw_content)

            articles.append({
                "titulo":            titulo,
                "contenido":         contenido,
                "resumen":           resumen,
                "imagen":            imagen,
                "fecha_publicacion": fecha,
                "fuente_id":         source_id,
                "url_original":      url_original,
                "multimedia":        multimedia,
                "categoria":         categoria,
            })
        except Exception as e:
            logger.warning("⚠️ Error parsing RSS item: %s", e)
            continue

    logger.info("✅ RSS %s → %d artículos", url, len(articles))
    return articles
