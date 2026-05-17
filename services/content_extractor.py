"""
services/content_extractor.py — Extracción limpia de contenido de artículos web

Responsabilidades:
  - Descargar la página HTML de un artículo externo
  - Extraer título, descripción, imagen og:image y cuerpo de texto limpio
  - Detectar multimedia (vídeos, imágenes) via MediaParser
  - Devolver siempre un dict con estructura fija, incluso en caso de error

Diseño:
  - Se elimina el "ruido" (scripts, estilos, nav, footers) antes de extraer texto
  - Se prioriza el contenido dentro de <article>, clases tipo 'content', o <main>
  - En caso de bloqueo (403) o timeout, devuelve _blocked=True para que la ruta
    api_routes.py pueda caer al contenido almacenado en la BD como fallback
"""

import re
import logging
import requests
from bs4 import BeautifulSoup
from services.media_parser import media_parser

logger = logging.getLogger(__name__)

# Cabeceras que simulan un navegador real para reducir bloqueos por bot-detection
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

# Tags HTML que se eliminan antes de extraer texto (ruido de página)
UNWANTED_TAGS = {"script", "style", "nav", "header", "footer", "aside",
                 "form", "button", "noscript", "svg", "figure"}


class ContentExtractor:
    """Descarga una URL y extrae datos limpios del artículo."""

    def extract(self, url: str, timeout: int = 8) -> dict:
        """
        Punto de entrada principal. Descarga la página y extrae todos los campos.

        Args:
            url:     URL del artículo a extraer
            timeout: segundos máximos de espera para la descarga

        Returns:
            dict con:
              titulo, contenido, resumen, imagen, multimedia, url_original
            Si hay error de red o bloqueo, incluye _blocked=True y los campos vacíos.
        """
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            logger.warning("⏱️ Timeout al extraer: %s", url)
            return self._error(url, "Timeout al cargar el artículo")
        except requests.exceptions.RequestException as e:
            logger.warning("🔌 Error de red al extraer %s: %s", url, e)
            return self._error(url, f"Error de red: {e}")

        soup = BeautifulSoup(resp.text, "html.parser")
        return {
            "titulo":       self._extract_title(soup),
            "contenido":    self._extract_content(soup),
            "resumen":      self._extract_description(soup),
            "imagen":       self._extract_image(soup),
            "multimedia":   media_parser.parse_soup(soup),   # vídeos, embeds, etc.
            "url_original": url,
        }

    # ── Helpers de extracción ─────────────────────────────────────────────────

    def _extract_title(self, soup) -> str:
        """
        Extrae el título en orden de prioridad:
        og:title → twitter:title → <title> → primer <h1>
        """
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            return og["content"].strip()
        twitter = soup.find("meta", {"name": "twitter:title"})
        if twitter and twitter.get("content"):
            return twitter["content"].strip()
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        h1 = soup.find("h1")
        return h1.get_text(strip=True) if h1 else "Sin título"

    def _extract_description(self, soup) -> str:
        """
        Extrae la descripción/resumen del artículo en orden de prioridad:
        og:description → meta description → twitter:description
        """
        for attr, name in [("property", "og:description"),
                           ("name", "description"),
                           ("name", "twitter:description")]:
            tag = soup.find("meta", {attr: name})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return ""

    def _extract_image(self, soup) -> str:
        """
        Extrae la imagen principal en orden de prioridad:
        og:image → twitter:image → primer <img> de la página
        """
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"].strip()
        twitter = soup.find("meta", {"name": "twitter:image"})
        if twitter and twitter.get("content"):
            return twitter["content"].strip()
        img = soup.find("img", src=True)
        return img["src"].strip() if img else ""

    def _extract_content(self, soup) -> str:
        """
        Extrae el cuerpo del artículo como texto limpio.

        Estrategia:
          1. Elimina tags de ruido (scripts, nav, footer, etc.)
          2. Busca el bloque de contenido principal: <article>, clases tipo
             'article|post|content|entry|body', o <main>
          3. Concatena los párrafos <p> del bloque encontrado
          4. Normaliza espacios y corta a 8000 caracteres para la BD
        """
        for tag in soup.find_all(UNWANTED_TAGS):
            tag.decompose()

        # Intentar localizar el cuerpo del artículo con selectores progresivos
        article = (
            soup.find("article")
            or soup.find(class_=re.compile(r"article|post|content|entry|body", re.I))
            or soup.find("main")
        )
        target = article or soup  # fallback a toda la página

        paragraphs = target.find_all("p")
        text = "\n\n".join(p.get_text(separator=" ", strip=True) for p in paragraphs if p.get_text(strip=True))
        text = self._normalize(text)
        return text[:8000]

    @staticmethod
    def _normalize(text: str) -> str:
        """Colapsa espacios múltiples y líneas vacías excesivas."""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def _error(url, message):
        """
        Devuelve un dict de error estándar con _blocked=True.
        La ruta /article lo detecta y cae al contenido almacenado en BD.
        """
        logger.warning("🚫 Extracción bloqueada (%s): %s", url, message)
        return {
            "titulo":       "",
            "contenido":    "",
            "resumen":      "",
            "imagen":       "",
            "multimedia":   [],
            "url_original": url,
            "_blocked":     True,
        }


# Singleton: se importa directamente desde routes y scrapers
content_extractor = ContentExtractor()
