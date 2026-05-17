"""
app.py — Punto de entrada de NEWS_GLOBO | Terminal V.1 Geo-Scanner

Responsabilidades:
  1. Carga variables de entorno (.env o Replit Secrets)
  2. Inicializa la base de datos SQLite (crea tablas si no existen)
  3. Registra los Blueprints de Flask (rutas modularizadas)
  4. Arranca el scheduler de ingesta automática en background
  5. Levanta el servidor Flask en el puerto configurado
"""

import os
import logging
from dotenv import load_dotenv

# Carga .env antes que cualquier otro módulo lo necesite.
# En Replit, las variables vienen de Secrets y load_dotenv() no sobrescribe las existentes.
load_dotenv()

from flask import Flask
from routes.main_routes import main_bp
from routes.api_routes import api_bp
from routes.news_api_routes import news_api_bp
from routes.docs_routes import docs_bp
import services.news_service as svc
from models.database import init_db
from services.scheduler import scheduler

# Configuración de logging global: nivel INFO, formato con timestamp
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear la aplicación Flask
app = Flask(__name__)

# Inicializar la base de datos al arranque (CREATE TABLE IF NOT EXISTS + migraciones seguras)
init_db()

# Registrar blueprints — cada uno maneja un dominio de rutas:
#   main_bp       → GET /              (sirve el frontend)
#   api_bp        → /country-news, /article, /cache-*, /api-status
#   news_api_bp   → /v1/* (fuentes, noticias, scheduler REST API)
#   docs_bp       → /docs             (documentación interactiva)
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)
app.register_blueprint(news_api_bp)
app.register_blueprint(docs_bp)

# Arrancar el scheduler en un hilo daemon — ingesta automática cada N minutos
# El primer fetch ocurre FETCH_INITIAL_DELAY_SECONDS segundos después del arranque
scheduler.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Iniciando News_globo en puerto {port}")
    logger.info(f"🔑 {len(svc.API_KEYS)} API Key(s) configuradas")
    logger.info(f"⚡ Caché: 6h países | 4h global")
    logger.info(f"📡 REST API disponible en /api/")
    logger.info(f"🤖 Scheduler activo — cada {scheduler.interval_min} min")
    # debug=False en producción; usar gunicorn para despliegues reales
    app.run(host='0.0.0.0', port=port, debug=False)
