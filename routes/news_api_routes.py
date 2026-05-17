"""
routes/news_api_routes.py — Blueprint REST API v1 para fuentes y noticias

Prefijo de rutas: /v1

Endpoints de noticias:
  GET  /v1/news              — lista de noticias (paginada, filtrable por fuente)
  GET  /v1/news/<id>         — detalle de una noticia; ?full=true re-extrae contenido

Endpoints de fuentes:
  GET    /v1/sources         — lista todas las fuentes; ?active=true para solo activas
  POST   /v1/sources         — crea una nueva fuente de noticias
  PUT    /v1/sources/<id>    — actualiza campos de una fuente existente
  DELETE /v1/sources/<id>    — elimina una fuente de la BD

Endpoints de ingesta:
  POST /v1/fetch             — dispara scraping de todas las fuentes activas
                               (o una sola con ?source_id=<id>)

Endpoints del scheduler:
  GET  /v1/scheduler         — estado actual del scheduler
  POST /v1/scheduler/start   — arranca la ingesta automática periódica
  POST /v1/scheduler/stop    — detiene la ingesta automática
  POST /v1/scheduler/run-now — lanza una ejecución inmediata en background
  PUT  /v1/scheduler/interval — cambia el intervalo en minutos

Utilidades:
  GET /v1/health             — healthcheck del servicio
"""

import logging
from flask import Blueprint, jsonify, request
from models import database as db
from services.fetch_service import fetch_all_sources, fetch_source_by_id
from services.content_extractor import content_extractor
from services.scheduler import scheduler

logger = logging.getLogger(__name__)

news_api_bp = Blueprint("news_api", __name__, url_prefix="/v1")


# ── Helpers de respuesta ──────────────────────────────────────────────────────

def _ok(data, status=200):
    """Respuesta estándar de éxito: {status: 'ok', ...data}"""
    return jsonify({"status": "ok", **data}), status


def _error(message, status=400, **extra):
    """Respuesta estándar de error: {status: 'error', message: '...', ...extra}"""
    return jsonify({"status": "error", "message": message, **extra}), status


# ── Endpoints de noticias ─────────────────────────────────────────────────────

@news_api_bp.route("/news", methods=["GET"])
def list_news():
    """
    Lista noticias almacenadas en la BD con paginación y filtro opcional por fuente.

    Query params:
      source — ID numérico de la fuente (opcional)
      limit  — máximo de resultados, capped a 100 (default: 50)
      offset — número de filas a saltar para paginación (default: 0)
    """
    source_id = request.args.get("source")
    limit  = min(int(request.args.get("limit",  50)), 100)
    offset = int(request.args.get("offset", 0))

    source_id_int = None
    if source_id:
        try:
            source_id_int = int(source_id)
        except ValueError:
            return _error("Parámetro 'source' debe ser un entero")

    news = db.get_news(source_id=source_id_int, limit=limit, offset=offset)
    return _ok({"news": news, "count": len(news), "offset": offset, "limit": limit})


@news_api_bp.route("/news/<int:news_id>", methods=["GET"])
def get_news(news_id):
    """
    Detalle de una noticia por ID.
    Si ?full=true se incluye en la query, re-extrae el contenido completo
    del artículo en tiempo real (scraping bajo demanda).
    """
    item = db.get_news_by_id(news_id)
    if not item:
        return _error("Noticia no encontrada", 404)

    fetch_full = request.args.get("full", "").lower() == "true"
    if fetch_full and item.get("url_original"):
        # Re-scraping bajo demanda: actualiza contenido y multimedia
        extracted = content_extractor.extract(item["url_original"])
        item["contenido"]  = extracted.get("contenido") or item.get("contenido")
        item["multimedia"] = extracted.get("multimedia") or item.get("multimedia", [])

    return _ok({"news": item})


# ── Endpoints de fuentes ──────────────────────────────────────────────────────

@news_api_bp.route("/sources", methods=["GET"])
def list_sources():
    """
    Lista todas las fuentes de noticias configuradas.
    ?active=true devuelve solo las fuentes con activa=1.
    """
    only_active = request.args.get("active", "").lower() == "true"
    sources = db.get_all_sources(only_active=only_active)
    return _ok({"sources": sources, "count": len(sources)})


@news_api_bp.route("/sources", methods=["POST"])
def create_source():
    """
    Crea una nueva fuente de noticias en la BD.

    Body JSON requerido:
      nombre  (str) — nombre descriptivo de la fuente
      url     (str) — URL del feed RSS o página a scrapear
      tipo    (str, opcional) — 'rss' | 'scraping' | 'api' (default: 'rss')
      activa  (bool, opcional) — true por defecto

    Devuelve 409 si ya existe una fuente con la misma URL.
    """
    body   = request.get_json(silent=True) or {}
    nombre = (body.get("nombre") or "").strip()
    url    = (body.get("url")    or "").strip()
    tipo   = (body.get("tipo")   or "rss").strip().lower()
    activa = body.get("activa", True)

    if not nombre:
        return _error("El campo 'nombre' es obligatorio")
    if not url:
        return _error("El campo 'url' es obligatorio")
    if tipo not in ("rss", "scraping", "api"):
        return _error("El campo 'tipo' debe ser 'rss', 'scraping' o 'api'")

    try:
        source = db.create_source(nombre, url, tipo, activa)
        return _ok({"source": source}, 201)
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            return _error(f"Ya existe una fuente con la URL: {url}", 409)
        logger.error("❌ Error al crear fuente: %s", e)
        return _error(str(e), 500)


@news_api_bp.route("/sources/<int:source_id>", methods=["PUT"])
def update_source(source_id):
    """
    Actualiza campos de una fuente existente.
    Solo modifica los campos presentes en el body JSON.
    Campos permitidos: nombre, url, tipo, activa.
    """
    if not db.get_source_by_id(source_id):
        return _error("Fuente no encontrada", 404)

    body    = request.get_json(silent=True) or {}
    allowed = {}

    if "nombre" in body:
        allowed["nombre"] = str(body["nombre"]).strip()
    if "url" in body:
        allowed["url"] = str(body["url"]).strip()
    if "tipo" in body:
        t = str(body["tipo"]).strip().lower()
        if t not in ("rss", "scraping", "api"):
            return _error("El campo 'tipo' debe ser 'rss', 'scraping' o 'api'")
        allowed["tipo"] = t
    if "activa" in body:
        # Normalizar a 0/1 para SQLite
        allowed["activa"] = 1 if body["activa"] else 0

    updated = db.update_source(source_id, **allowed)
    return _ok({"source": updated})


@news_api_bp.route("/sources/<int:source_id>", methods=["DELETE"])
def delete_source(source_id):
    """
    Elimina una fuente de la BD por su ID.
    Las noticias asociadas conservan su fuente_id como NULL (ON DELETE SET NULL).
    """
    if not db.get_source_by_id(source_id):
        return _error("Fuente no encontrada", 404)
    db.delete_source(source_id)
    return _ok({"message": f"Fuente {source_id} eliminada"})


# ── Endpoints de ingesta ──────────────────────────────────────────────────────

@news_api_bp.route("/fetch", methods=["POST"])
def trigger_fetch():
    """
    Dispara manualmente el scraping de noticias.

    Sin parámetros → procesa todas las fuentes activas en paralelo.
    Con ?source_id=<id> o {"source_id": <id>} en el body → procesa solo esa fuente.

    Devuelve un resumen con el número de artículos extraídos e insertados por fuente.
    """
    source_id = (
        request.args.get("source_id")
        or (request.get_json(silent=True) or {}).get("source_id")
    )

    if source_id:
        try:
            source_id = int(source_id)
        except (ValueError, TypeError):
            return _error("'source_id' debe ser un entero")
        result = fetch_source_by_id(source_id)
        if result is None:
            return _error("Fuente no encontrada", 404)
        return _ok({"result": result})
    else:
        # Ingesta completa de todas las fuentes activas
        summary = fetch_all_sources(only_active=True)
        return _ok({"summary": summary})


# ── Endpoints del scheduler ───────────────────────────────────────────────────

@news_api_bp.route("/scheduler", methods=["GET"])
def scheduler_status():
    """Devuelve el estado actual del scheduler (corriendo, intervalo, última ejecución, etc.)"""
    return _ok({"scheduler": scheduler.status()})


@news_api_bp.route("/scheduler/start", methods=["POST"])
def scheduler_start():
    """Arranca el scheduler de ingesta automática periódica."""
    scheduler.start()
    return _ok({"scheduler": scheduler.status(), "message": "Scheduler iniciado"})


@news_api_bp.route("/scheduler/stop", methods=["POST"])
def scheduler_stop():
    """Detiene el scheduler (la ingesta automática se suspende hasta el próximo start)."""
    scheduler.stop()
    return _ok({"scheduler": scheduler.status(), "message": "Scheduler detenido"})


@news_api_bp.route("/scheduler/run-now", methods=["POST"])
def scheduler_run_now():
    """Lanza una ejecución inmediata de ingesta en un hilo background (no bloquea)."""
    scheduler.run_now()
    return _ok({"message": "Ingesta manual lanzada en background"})


@news_api_bp.route("/scheduler/interval", methods=["PUT"])
def scheduler_interval():
    """
    Cambia el intervalo de ingesta automática.

    Body JSON requerido:
      minutes (int) — nuevo intervalo en minutos, mínimo 1
    """
    body    = request.get_json(silent=True) or {}
    minutes = body.get("minutes")
    if minutes is None:
        return _error("Campo 'minutes' requerido (entero, mínimo 1)")
    try:
        minutes = int(minutes)
    except (ValueError, TypeError):
        return _error("'minutes' debe ser un entero")
    if minutes < 1:
        return _error("El intervalo mínimo es 1 minuto")
    scheduler.set_interval(minutes)
    return _ok({"scheduler": scheduler.status(), "message": f"Intervalo actualizado a {minutes} min"})


# ── Healthcheck ───────────────────────────────────────────────────────────────

@news_api_bp.route("/health", methods=["GET"])
def health():
    """Endpoint de salud para monitoreo externo. Siempre devuelve 200 si el servicio está vivo."""
    return _ok({"service": "news-globo-api", "version": "2.1", "scheduler": scheduler.status()})
