"""
routes/main_routes.py — Blueprint de la ruta principal de la UI

Sirve el frontend (index.html) en GET /.
Las cabeceras de caché están desactivadas para que el navegador
siempre pida la versión más reciente durante el desarrollo.
"""

from flask import Blueprint, render_template, make_response

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """
    Sirve la aplicación principal.
    Cache-Control: no-store asegura que el navegador no guarde en caché
    el HTML del frontend (importante cuando hay cambios frecuentes en JS/CSS).
    """
    resp = make_response(render_template('index.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp
