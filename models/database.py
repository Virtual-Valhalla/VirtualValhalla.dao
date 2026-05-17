"""
models/database.py — Capa de acceso a datos SQLite

Esquema principal:
  sources  — fuentes de noticias (RSS, scraping, API)
  noticias — artículos almacenados, con referencia a su fuente

Funciones disponibles:
  init_db()              → crea tablas, ejecuta migraciones y siembra fuentes por defecto
  get_all_sources()      → lista todas las fuentes (o solo las activas)
  get_source_by_id()     → busca una fuente por ID
  create_source()        → inserta una nueva fuente
  update_source()        → actualiza campos de una fuente existente
  delete_source()        → elimina una fuente por ID
  upsert_news()          → inserta artículos ignorando duplicados por url_original
  get_news()             → consulta noticias con filtros opcionales y paginación
  get_news_by_id()       → obtiene un artículo por ID
  get_news_by_url()      → busca un artículo por URL original

La base de datos se almacena en la ruta definida por DB_PATH
(por defecto: news_globo.db en la raíz del proyecto).
"""

import sqlite3
import json
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Ruta del archivo SQLite. Se puede sobreescribir con la variable DB_PATH.
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "news_globo.db"))


@contextmanager
def get_db():
    """
    Context manager que abre una conexión SQLite y garantiza commit/rollback.
    Activa WAL (Write-Ahead Logging) para mejor rendimiento en concurrencia.
    La conexión se cierra automáticamente al salir del bloque `with`.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # permite acceder a columnas por nombre
    conn.execute("PRAGMA journal_mode=WAL")  # WAL mejora lecturas concurrentes
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Inicializa la base de datos al arranque de la aplicación.
    Crea las tablas e índices si no existen, aplica migraciones seguras
    (añade columnas nuevas sin perder datos) y siembra fuentes por defecto.
    """
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre      TEXT    NOT NULL,
                url         TEXT    NOT NULL UNIQUE,
                tipo        TEXT    NOT NULL DEFAULT 'rss',
                activa      INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS noticias (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo           TEXT,
                contenido        TEXT,
                resumen          TEXT,
                imagen           TEXT,
                fecha_publicacion TEXT,
                fuente_id        INTEGER REFERENCES sources(id) ON DELETE SET NULL,
                url_original     TEXT UNIQUE,
                multimedia       TEXT DEFAULT '[]',
                created_at       TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_noticias_fuente  ON noticias(fuente_id);
            CREATE INDEX IF NOT EXISTS idx_noticias_fecha   ON noticias(fecha_publicacion DESC);
            CREATE INDEX IF NOT EXISTS idx_sources_activa   ON sources(activa);
        """)
        _migrate(conn)
        _seed_sources(conn)
    logger.info("✅ Base de datos inicializada en %s", DB_PATH)


def _migrate(conn):
    """
    Migraciones seguras: añade columnas nuevas si no existen.
    Nunca elimina ni renombra columnas existentes para preservar datos.
    """
    existing_sources_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(sources)").fetchall()
    }
    existing_noticias_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(noticias)").fetchall()
    }

    if "categoria" not in existing_sources_cols:
        conn.execute("ALTER TABLE sources ADD COLUMN categoria TEXT DEFAULT 'General'")
        logger.info("✅ Columna 'categoria' añadida a sources")

    if "lang" not in existing_sources_cols:
        conn.execute("ALTER TABLE sources ADD COLUMN lang TEXT DEFAULT 'en'")
        logger.info("✅ Columna 'lang' añadida a sources")

    if "categoria" not in existing_noticias_cols:
        conn.execute("ALTER TABLE noticias ADD COLUMN categoria TEXT DEFAULT 'General'")
        logger.info("✅ Columna 'categoria' añadida a noticias")


def _seed_sources(conn):
    """
    Inserta fuentes RSS predeterminadas si aún no existen en la BD.
    Se ejecuta en cada arranque pero solo actúa si falta alguna URL.
    """
    defaults = [
        ("BBC News (RSS)",      "http://feeds.bbci.co.uk/news/rss.xml",             "rss", "en", "General"),
        ("Reuters (RSS)",       "https://feeds.reuters.com/reuters/topNews",          "rss", "en", "General"),
        ("Al Jazeera (RSS)",    "https://www.aljazeera.com/xml/rss/all.xml",         "rss", "en", "General"),
        ("CNN (RSS)",           "http://rss.cnn.com/rss/edition.rss",                "rss", "en", "General"),
        ("El País (RSS)",       "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", "rss", "es", "General"),
    ]
    existing = conn.execute("SELECT url FROM sources").fetchall()
    existing_urls = {r["url"] for r in existing}
    for nombre, url, tipo, lang, categoria in defaults:
        if url not in existing_urls:
            conn.execute(
                "INSERT OR IGNORE INTO sources (nombre, url, tipo, activa, lang, categoria) VALUES (?,?,?,1,?,?)",
                (nombre, url, tipo, lang, categoria)
            )


# ── CRUD de fuentes ───────────────────────────────────────────────────────────

def get_all_sources(only_active=False):
    """Devuelve todas las fuentes. Si only_active=True, filtra las inactivas."""
    with get_db() as conn:
        q = "SELECT * FROM sources"
        if only_active:
            q += " WHERE activa = 1"
        q += " ORDER BY id"
        rows = conn.execute(q).fetchall()
        return [dict(r) for r in rows]


def get_source_by_id(source_id):
    """Devuelve una fuente por su ID, o None si no existe."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return dict(row) if row else None


def create_source(nombre, url, tipo="rss", activa=True):
    """Crea una nueva fuente y devuelve el registro completo recién insertado."""
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO sources (nombre, url, tipo, activa) VALUES (?,?,?,?)",
            (nombre, url, tipo, 1 if activa else 0)
        )
        return get_source_by_id(cur.lastrowid)


def update_source(source_id, **kwargs):
    """
    Actualiza campos de una fuente existente.
    Solo modifica los campos incluidos en kwargs (nombre, url, tipo, activa, categoria, lang).
    Actualiza automáticamente el campo updated_at.
    """
    allowed = {"nombre", "url", "tipo", "activa", "categoria", "lang"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_source_by_id(source_id)
    fields["updated_at"] = "datetime('now')"
    set_clause = ", ".join(
        f"{k} = datetime('now')" if k == "updated_at" else f"{k} = ?"
        for k in fields
    )
    values = [v for k, v in fields.items() if k != "updated_at"]
    values.append(source_id)
    with get_db() as conn:
        conn.execute(f"UPDATE sources SET {set_clause} WHERE id = ?", values)
    return get_source_by_id(source_id)


def delete_source(source_id):
    """Elimina una fuente por ID. Devuelve True si se eliminó algo."""
    with get_db() as conn:
        affected = conn.execute("DELETE FROM sources WHERE id = ?", (source_id,)).rowcount
    return affected > 0


# ── CRUD de noticias ──────────────────────────────────────────────────────────

def upsert_news(items):
    """
    Inserta una lista de artículos en la BD, ignorando duplicados por url_original.
    El campo multimedia se serializa a JSON antes de guardar.
    Devuelve el número de artículos efectivamente insertados (no duplicados).
    """
    inserted = 0
    with get_db() as conn:
        for item in items:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO noticias
                       (titulo, contenido, resumen, imagen, fecha_publicacion,
                        fuente_id, url_original, multimedia, categoria)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        item.get("titulo"),
                        item.get("contenido"),
                        item.get("resumen"),
                        item.get("imagen"),
                        item.get("fecha_publicacion"),
                        item.get("fuente_id"),
                        item.get("url_original"),
                        json.dumps(item.get("multimedia", [])),
                        item.get("categoria", "General"),
                    )
                )
                inserted += conn.execute("SELECT changes()").fetchone()[0]
            except Exception as e:
                logger.warning("⚠️ No se pudo insertar noticia %s: %s", item.get("url_original"), e)
    return inserted


def get_news(source_id=None, categoria=None, limit=200, offset=0):
    """
    Consulta noticias de la BD con filtros opcionales.

    Args:
        source_id: filtra por ID de fuente (None = todas las fuentes)
        categoria: filtra por categoría exacta en español (None o 'general' = sin filtro)
        limit:     máximo de resultados (por defecto 200)
        offset:    paginación — número de filas a saltar

    Returns:
        Lista de dicts con datos de la noticia y nombre/URL de la fuente.
        El campo multimedia se deserializa de JSON a lista Python.
    """
    with get_db() as conn:
        base = """
            SELECT n.*, s.nombre AS source_name, s.url AS source_url
            FROM noticias n
            LEFT JOIN sources s ON n.fuente_id = s.id
        """
        conditions = []
        params = []

        if source_id:
            conditions.append("n.fuente_id = ?")
            params.append(source_id)

        # Ignorar el filtro si la categoría es vacía, 'general' o 'all'
        if categoria and categoria.lower() not in ("", "general", "all"):
            conditions.append("LOWER(n.categoria) = LOWER(?)")
            params.append(categoria)

        if conditions:
            base += " WHERE " + " AND ".join(conditions)

        base += " ORDER BY n.fecha_publicacion DESC, n.id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = conn.execute(base, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["multimedia"] = json.loads(d.get("multimedia") or "[]")
            except Exception:
                d["multimedia"] = []
            result.append(d)
        return result


def get_news_by_id(news_id):
    """
    Devuelve un artículo completo por su ID, incluyendo nombre de la fuente.
    Devuelve None si no existe. El campo multimedia se deserializa de JSON.
    """
    with get_db() as conn:
        row = conn.execute(
            """SELECT n.*, s.nombre AS source_name FROM noticias n
               LEFT JOIN sources s ON n.fuente_id = s.id WHERE n.id = ?""",
            (news_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["multimedia"] = json.loads(d.get("multimedia") or "[]")
        except Exception:
            d["multimedia"] = []
        return d


def get_news_by_url(url_original):
    """
    Busca un artículo por su URL original.
    Usado como fallback cuando el scraping en vivo falla o está bloqueado.
    Devuelve None si la URL no está en la BD.
    """
    with get_db() as conn:
        row = conn.execute(
            """SELECT n.*, s.nombre AS source_name FROM noticias n
               LEFT JOIN sources s ON n.fuente_id = s.id
               WHERE n.url_original = ?""",
            (url_original,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["multimedia"] = json.loads(d.get("multimedia") or "[]")
        except Exception:
            d["multimedia"] = []
        return d
