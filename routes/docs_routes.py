"""
Documentation routes — serves the API docs page at /docs
"""
from flask import Blueprint, render_template_string

docs_bp = Blueprint("docs", __name__)

DOCS_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>News Globo — API Docs</title>
<style>
  :root { --bg:#0d1117; --card:#161b22; --border:#30363d; --green:#3fb950; --blue:#58a6ff; --yellow:#d29922; --red:#f85149; --text:#e6edf3; --muted:#8b949e; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,sans-serif; line-height:1.6; }
  .container { max-width:900px; margin:0 auto; padding:2rem 1.5rem; }
  h1 { color:var(--green); font-size:2rem; margin-bottom:.25rem; }
  h2 { color:var(--blue); font-size:1.2rem; margin:2rem 0 .75rem; border-bottom:1px solid var(--border); padding-bottom:.4rem; }
  h3 { color:var(--text); font-size:1rem; margin:.75rem 0 .25rem; }
  p  { color:var(--muted); margin-bottom:.75rem; }
  code { background:#1c2128; color:var(--green); padding:.1rem .35rem; border-radius:4px; font-size:.88rem; font-family:monospace; }
  pre { background:#1c2128; border:1px solid var(--border); border-radius:8px; padding:1rem; overflow-x:auto; margin:.75rem 0; }
  pre code { background:none; padding:0; }
  .badge { display:inline-block; padding:.15rem .6rem; border-radius:4px; font-size:.78rem; font-weight:700; margin-right:.4rem; }
  .get    { background:#1c3048; color:var(--blue); }
  .post   { background:#1c3620; color:var(--green); }
  .put    { background:#3a2e0c; color:var(--yellow); }
  .delete { background:#3b1315; color:var(--red); }
  .endpoint { background:var(--card); border:1px solid var(--border); border-radius:8px; padding:1rem 1.25rem; margin:.6rem 0; }
  .endpoint-title { display:flex; align-items:center; gap:.5rem; font-family:monospace; font-size:.95rem; }
  .desc { color:var(--muted); font-size:.9rem; margin-top:.35rem; }
  table { width:100%; border-collapse:collapse; margin:.6rem 0; font-size:.88rem; }
  th { color:var(--muted); text-align:left; padding:.4rem .6rem; border-bottom:1px solid var(--border); }
  td { padding:.4rem .6rem; border-bottom:1px solid #21262d; }
  td:first-child { font-family:monospace; color:var(--yellow); }
  .tag { background:#1c2128; border:1px solid var(--border); color:var(--muted); padding:.1rem .5rem; border-radius:12px; font-size:.78rem; }
  a { color:var(--blue); }
</style>
</head>
<body>
<div class="container">
  <h1>&#x1F30D; News Globo API</h1>
  <p>API REST para gestión de fuentes y noticias. Base URL: <code>{{ request.host_url }}v1</code></p>

  <h2>Noticias</h2>

  <div class="endpoint">
    <div class="endpoint-title"><span class="badge get">GET</span><code>/v1/news</code></div>
    <div class="desc">Lista de noticias almacenadas, paginadas y filtrables.</div>
    <h3>Parámetros</h3>
    <table><tr><th>Param</th><th>Tipo</th><th>Default</th><th>Descripción</th></tr>
      <tr><td>source</td><td>int</td><td>—</td><td>Filtrar por ID de fuente</td></tr>
      <tr><td>limit</td><td>int</td><td>50</td><td>Máximo de resultados (max 100)</td></tr>
      <tr><td>offset</td><td>int</td><td>0</td><td>Paginación</td></tr>
    </table>
    <pre><code>{
  "status": "ok",
  "count": 2,
  "news": [
    {
      "id": 1,
      "titulo": "Título de la noticia",
      "resumen": "Resumen corto",
      "contenido": "Contenido limpio...",
      "imagen": "https://...",
      "fecha_publicacion": "2026-05-06T12:00:00",
      "fuente_id": 1,
      "source_name": "BBC News",
      "url_original": "https://...",
      "multimedia": [
        { "type": "video", "source": "youtube", "embed_url": "https://youtube.com/embed/..." }
      ]
    }
  ]
}</code></pre>
  </div>

  <div class="endpoint">
    <div class="endpoint-title"><span class="badge get">GET</span><code>/v1/news/&lt;id&gt;</code></div>
    <div class="desc">Detalle de una noticia por ID. Añade <code>?full=true</code> para re-extraer el contenido completo en tiempo real.</div>
  </div>

  <h2>Fuentes</h2>

  <div class="endpoint">
    <div class="endpoint-title"><span class="badge get">GET</span><code>/v1/sources</code></div>
    <div class="desc">Lista todas las fuentes. Añade <code>?active=true</code> para sólo las activas.</div>
  </div>

  <div class="endpoint">
    <div class="endpoint-title"><span class="badge post">POST</span><code>/v1/sources</code></div>
    <div class="desc">Crea una nueva fuente de noticias.</div>
    <h3>Body (JSON)</h3>
    <table><tr><th>Campo</th><th>Tipo</th><th>Req.</th><th>Descripción</th></tr>
      <tr><td>nombre</td><td>string</td><td>✔</td><td>Nombre de la fuente</td></tr>
      <tr><td>url</td><td>string</td><td>✔</td><td>URL del feed o web</td></tr>
      <tr><td>tipo</td><td>string</td><td>—</td><td><code>rss</code> | <code>scraping</code> | <code>api</code>  (default: rss)</td></tr>
      <tr><td>activa</td><td>bool</td><td>—</td><td>Activa por defecto (true)</td></tr>
    </table>
    <pre><code>POST /v1/sources
Content-Type: application/json

{ "nombre": "El Mundo", "url": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml", "tipo": "rss" }</code></pre>
  </div>

  <div class="endpoint">
    <div class="endpoint-title"><span class="badge put">PUT</span><code>/v1/sources/&lt;id&gt;</code></div>
    <div class="desc">Actualiza campos de una fuente. Envía sólo los campos que quieres cambiar.</div>
  </div>

  <div class="endpoint">
    <div class="endpoint-title"><span class="badge delete">DELETE</span><code>/v1/sources/&lt;id&gt;</code></div>
    <div class="desc">Elimina una fuente de la base de datos.</div>
  </div>

  <h2>Ingesta</h2>

  <div class="endpoint">
    <div class="endpoint-title"><span class="badge post">POST</span><code>/v1/fetch</code></div>
    <div class="desc">Dispara el scraping/RSS de todas las fuentes activas (o una sola con <code>?source_id=&lt;id&gt;</code>).</div>
    <pre><code># Todas las fuentes
POST /v1/fetch

# Una fuente específica
POST /v1/fetch?source_id=3</code></pre>
    <pre><code>{
  "status": "ok",
  "summary": {
    "total_sources": 5,
    "total_inserted": 42,
    "results": [
      { "source_name": "BBC News", "fetched": 15, "inserted": 8, "error": null },
      ...
    ]
  }
}</code></pre>
  </div>

  <h2>Utilidades heredadas</h2>

  <div class="endpoint">
    <div class="endpoint-title"><span class="badge get">GET</span><code>/country-news?country=&lt;code&gt;</code></div>
    <div class="desc">Noticias de un país vía NewsAPI. Requiere <code>NEWS_API_KEY</code> en <code>.env</code>.</div>
  </div>
  <div class="endpoint">
    <div class="endpoint-title"><span class="badge get">GET</span><code>/article?url=&lt;url&gt;</code></div>
    <div class="desc">Extrae y parsea el contenido de un artículo externo.</div>
  </div>
  <div class="endpoint">
    <div class="endpoint-title"><span class="badge get">GET</span><code>/cache-status</code></div>
    <div class="desc">Estado de la caché en memoria para los países.</div>
  </div>

  <h2>Variables de entorno (.env)</h2>
  <table>
    <tr><th>Variable</th><th>Descripción</th></tr>
    <tr><td>NEWS_API_KEY</td><td>Clave(s) de NewsAPI.org separadas por coma. Requerida para el mapa 3D.</td></tr>
    <tr><td>PORT</td><td>Puerto del servidor (default 5000)</td></tr>
    <tr><td>DB_PATH</td><td>Ruta del archivo SQLite (default: news_globo.db en raíz del proyecto)</td></tr>
  </table>

  <h2>Ejecutar el servidor</h2>
  <pre><code># Desarrollo
pip install -r requirements.txt
python app.py

# Producción
gunicorn app:app --bind 0.0.0.0:5000 --workers 2</code></pre>

  <p style="margin-top:2rem; color:var(--muted); font-size:.85rem;">
    News Globo v2.0 &mdash; Frontend 3D globe intacto &mdash; SQLite storage &mdash; RSS + HTML scraping
  </p>
</div>
</body>
</html>"""


@docs_bp.route("/docs")
def api_docs():
    from flask import request
    return render_template_string(DOCS_HTML)
