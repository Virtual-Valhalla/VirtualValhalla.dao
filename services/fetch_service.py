"""
services/fetch_service.py — Orquestador de ingesta desde todas las fuentes activas

Responsabilidades:
  - Despachar cada fuente al scraper correcto (RSS o HTML) según su campo 'tipo'
  - Ejecutar las ingestas de forma concurrente usando un ThreadPoolExecutor
  - Almacenar los artículos obtenidos llamando a upsert_news()
  - Devolver un resumen con conteos y errores por fuente

Funciones públicas:
  fetch_all_sources(only_active)  → ingesta completa de todas las fuentes
  fetch_source_by_id(source_id)  → ingesta de una sola fuente por ID
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from models.database import get_all_sources, upsert_news
from scrapers.rss_scraper import scrape_rss
from scrapers.html_scraper import scrape_html

logger = logging.getLogger(__name__)

# Número máximo de fuentes procesadas en paralelo
MAX_WORKERS = 5


def fetch_all_sources(only_active=True):
    """
    Obtiene noticias de todas las fuentes configuradas de forma concurrente.

    Args:
        only_active: si True (por defecto), solo procesa fuentes con activa=1

    Returns:
        dict con:
          total_sources:  número de fuentes procesadas
          total_inserted: total de artículos nuevos insertados en BD
          results:        lista de dicts por fuente con fetched/inserted/error
    """
    sources = get_all_sources(only_active=only_active)
    if not sources:
        logger.warning("⚠️ No hay fuentes configuradas")
        return {"total_sources": 0, "total_inserted": 0, "results": []}

    results = []
    total_inserted = 0

    # Procesar cada fuente en su propio hilo; as_completed() permite recoger
    # los resultados en el orden en que terminan, no en orden de envío.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_source = {
            executor.submit(_fetch_source, src): src
            for src in sources
        }
        for future in as_completed(future_to_source):
            src = future_to_source[future]
            try:
                fetched, inserted, error = future.result()
                total_inserted += inserted
                results.append({
                    "source_id":   src["id"],
                    "source_name": src["nombre"],
                    "tipo":        src["tipo"],
                    "fetched":     fetched,
                    "inserted":    inserted,
                    "error":       error,
                })
            except Exception as e:
                results.append({
                    "source_id":   src["id"],
                    "source_name": src["nombre"],
                    "tipo":        src["tipo"],
                    "fetched":     0,
                    "inserted":    0,
                    "error":       str(e),
                })

    logger.info("🏁 Ingesta completa: %d nuevos artículos de %d fuentes",
                total_inserted, len(sources))
    return {
        "total_sources":  len(sources),
        "total_inserted": total_inserted,
        "results":        results,
    }


def fetch_source_by_id(source_id):
    """
    Obtiene noticias de una sola fuente identificada por su ID.

    Returns:
        dict con source_id, source_name, tipo, fetched, inserted, error.
        Devuelve None si la fuente no existe en la BD.
    """
    from models.database import get_source_by_id
    source = get_source_by_id(source_id)
    if not source:
        return None
    fetched, inserted, error = _fetch_source(source)
    return {
        "source_id":   source["id"],
        "source_name": source["nombre"],
        "tipo":        source["tipo"],
        "fetched":     fetched,
        "inserted":    inserted,
        "error":       error,
    }


def _fetch_source(source):
    """
    Despacha una fuente al scraper correspondiente y persiste los resultados.

    Lógica de despacho:
      - tipo 'rss'      → scrape_rss()
      - tipo 'scraping' → scrape_html()
      - tipo desconocido → lista vacía + aviso en log

    Returns:
        Tupla (fetched, inserted, error):
          fetched:  número de artículos extraídos del feed
          inserted: número de artículos nuevos guardados en BD
          error:    mensaje de error (str) o None si todo fue bien
    """
    tipo = source.get("tipo", "rss").lower()
    try:
        if tipo == "rss":
            articles = scrape_rss(source)
        elif tipo == "scraping":
            articles = scrape_html(source)
        else:
            logger.warning("⚠️ Tipo desconocido '%s' para fuente %s", tipo, source["nombre"])
            articles = []

        if not articles:
            return 0, 0, None

        inserted = upsert_news(articles)
        return len(articles), inserted, None

    except Exception as e:
        logger.error("❌ Error en fuente '%s': %s", source["nombre"], e)
        return 0, 0, str(e)
