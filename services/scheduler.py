"""
services/scheduler.py — Ingesta automática periódica de noticias

Lanza un hilo daemon que ejecuta FetchService cada N minutos.
El primer fetch ocurre FETCH_INITIAL_DELAY_SECONDS segundos después del arranque
para no bloquear el inicio de la aplicación.

Variables de entorno:
  FETCH_INTERVAL_MINUTES   — intervalo entre ejecuciones (default: 60)
  FETCH_INITIAL_DELAY_SECONDS — espera antes del primer fetch (default: 30)

Uso:
  from services.scheduler import scheduler
  scheduler.start()          # arrancar
  scheduler.stop()           # detener
  scheduler.run_now()        # ejecución inmediata en background
  scheduler.status()         # estado actual como dict
  scheduler.set_interval(n)  # cambiar intervalo en minutos
"""

import os
import time
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

FETCH_INTERVAL_MINUTES  = int(os.environ.get("FETCH_INTERVAL_MINUTES",  "60"))
FETCH_INITIAL_DELAY_SEC = int(os.environ.get("FETCH_INITIAL_DELAY_SECONDS", "30"))


class NewsScheduler:
    """
    Scheduler de ingesta basado en threading.Thread daemon.

    El hilo principal duerme entre ejecuciones usando threading.Event.wait()
    en lugar de time.sleep(), lo que permite interrumpirlo limpiamente con stop().
    Un Lock protege las estadísticas compartidas contra condiciones de carrera.
    """

    def __init__(self):
        self._stop_event    = threading.Event()   # señal para detener el bucle
        self._thread        = None                # referencia al hilo daemon
        self._lock          = threading.Lock()    # protege atributos de estado
        self.interval_min   = FETCH_INTERVAL_MINUTES
        self.running        = False
        self.last_run_at    = None
        self.last_result    = None
        self.next_run_at    = None
        self.total_runs     = 0
        self.total_inserted = 0

    # ── API pública ─────────────────────────────────────────────────────────

    def start(self):
        """Arranca el hilo de ingesta si no está ya corriendo."""
        if self._thread and self._thread.is_alive():
            logger.info("⏱️  Scheduler ya está corriendo")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="news-scheduler")
        self._thread.start()
        self.running = True
        logger.info(
            "✅ Scheduler iniciado — intervalo: %d min — primer fetch en %d seg",
            self.interval_min, FETCH_INITIAL_DELAY_SEC
        )

    def stop(self):
        """Señala al hilo que debe detenerse en la próxima oportunidad."""
        self._stop_event.set()
        self.running = False
        logger.info("🛑 Scheduler detenido")

    def set_interval(self, minutes: int):
        """Cambia el intervalo entre ejecuciones (mínimo 1 minuto)."""
        with self._lock:
            self.interval_min = max(1, int(minutes))
            self._recompute_next()
        logger.info("🔄 Intervalo actualizado a %d min", self.interval_min)

    def status(self) -> dict:
        """Devuelve un snapshot del estado actual como dict JSON-serializable."""
        with self._lock:
            return {
                "running":        self.running,
                "interval_min":   self.interval_min,
                "total_runs":     self.total_runs,
                "total_inserted": self.total_inserted,
                "last_run_at":    self.last_run_at,
                "next_run_at":    self.next_run_at,
                "last_result":    self.last_result,
            }

    def run_now(self):
        """Lanza una ejecución inmediata en un hilo separado (no bloquea)."""
        t = threading.Thread(target=self._execute, daemon=True, name="news-scheduler-manual")
        t.start()

    # ── Internos ─────────────────────────────────────────────────────────────

    def _loop(self):
        """Bucle principal del hilo daemon: espera inicial → fetch → espera → …"""
        logger.info("⏳ Esperando %d seg antes del primer fetch...", FETCH_INITIAL_DELAY_SEC)
        # Si se llama a stop() durante la espera inicial, el evento lo interrumpe
        if self._stop_event.wait(timeout=FETCH_INITIAL_DELAY_SEC):
            return

        while not self._stop_event.is_set():
            self._execute()
            self._recompute_next()
            interval_sec = self.interval_min * 60
            logger.info("⏰ Próximo fetch automático en %d min", self.interval_min)
            # Event.wait actúa como sleep interrumpible
            if self._stop_event.wait(timeout=interval_sec):
                break

    def _execute(self):
        """
        Ejecuta una ingesta completa llamando a fetch_all_sources().
        Importación tardía para evitar importaciones circulares al arranque.
        Actualiza las estadísticas protegidas por el lock.
        """
        from services.fetch_service import fetch_all_sources
        now = datetime.now(timezone.utc).isoformat()
        logger.info("🤖 Scheduler: iniciando ingesta automática...")
        try:
            result = fetch_all_sources(only_active=True)
            with self._lock:
                self.total_runs     += 1
                self.total_inserted += result.get("total_inserted", 0)
                self.last_run_at    = now
                self.last_result    = {
                    "total_sources":  result.get("total_sources"),
                    "total_inserted": result.get("total_inserted"),
                    "errors":         sum(1 for r in result.get("results", []) if r.get("error")),
                }
            logger.info(
                "✅ Scheduler run #%d — %d fuentes — %d nuevos artículos",
                self.total_runs,
                result.get("total_sources", 0),
                result.get("total_inserted", 0),
            )
        except Exception as e:
            logger.error("❌ Scheduler error: %s", e)
            with self._lock:
                self.last_run_at = now
                self.last_result = {"error": str(e)}

    def _recompute_next(self):
        """Recalcula y guarda el timestamp estimado de la próxima ejecución."""
        next_ts = time.time() + self.interval_min * 60
        self.next_run_at = datetime.fromtimestamp(next_ts, tz=timezone.utc).isoformat()


# Singleton: se importa directamente desde otros módulos
scheduler = NewsScheduler()
