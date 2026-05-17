"""
services/media_parser.py — Detección y estructuración de multimedia en HTML/texto

Soporta los siguientes tipos de media:
  - YouTube (iframes con embed URL y enlaces watch?v=)
  - Vimeo
  - Twitter/X (tweets por ID)
  - Instagram (posts embed)
  - TikTok (vídeos embed)
  - HTML5 video (archivos .mp4, .webm, .ogg)
  - meta og:video

Devuelve siempre una lista de dicts con estructura:
  { "type": "video"|"social", "source": "youtube"|"vimeo"|…, "embed_url": "…" }

Los embed_url de YouTube incluyen ?autoplay=0 para evitar reproducción automática.
Se usa un set 'seen' para evitar duplicados dentro de una misma página.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Expresiones regulares para detección de plataformas ──────────────────────

# YouTube: detecta tanto URLs de embed como de watch
YOUTUBE_EMBED_RE = re.compile(
    r'(?:youtube\.com/embed/|youtu\.be/)([A-Za-z0-9_\-]{11})', re.IGNORECASE
)
YOUTUBE_WATCH_RE = re.compile(
    r'(?:youtube\.com/watch\?(?:.*&)?v=|youtu\.be/)([A-Za-z0-9_\-]{11})', re.IGNORECASE
)
TWITTER_RE   = re.compile(r'twitter\.com/\w+/status/(\d+)', re.IGNORECASE)
INSTAGRAM_RE = re.compile(r'instagram\.com/p/([A-Za-z0-9_\-]+)', re.IGNORECASE)
TIKTOK_RE    = re.compile(r'tiktok\.com/@[\w.]+/video/(\d+)', re.IGNORECASE)
VIMEO_RE     = re.compile(r'vimeo\.com/(\d+)', re.IGNORECASE)
# Archivos de vídeo directos (mp4, webm, ogg)
VIDEO_EXT_RE = re.compile(r'https?://[^\s"\'<>]+\.(?:mp4|webm|ogg)', re.IGNORECASE)


class MediaParser:
    """
    Analiza HTML (BeautifulSoup) o texto en bruto y devuelve
    una lista de objetos multimedia estructurados y sin duplicados.
    """

    def parse_soup(self, soup):
        """
        Extrae multimedia de un objeto BeautifulSoup.
        Recorre en orden: iframes → enlaces → tags video → meta og:video.

        Returns:
            Lista de dicts multimedia ordenados por aparición en el DOM.
        """
        results = []
        seen = set()

        # 1. Iframes (embeds de YouTube, Vimeo, etc.)
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src", "") or ""
            media = self._classify_url(src)
            if media and media["embed_url"] not in seen:
                seen.add(media["embed_url"])
                results.append(media)

        # 2. Hipervínculos que apuntan a plataformas de vídeo/social
        for a in soup.find_all("a", href=True):
            media = self._classify_url(a["href"])
            if media and media["embed_url"] not in seen:
                seen.add(media["embed_url"])
                results.append(media)

        # 3. Tags <video> con src directo o elemento <source> anidado
        for vid in soup.find_all("video"):
            src = vid.get("src") or ""
            if not src:
                source = vid.find("source")
                if source:
                    src = source.get("src", "")
            if src and src not in seen:
                seen.add(src)
                results.append({"type": "video", "source": "html5", "embed_url": src})

        # 4. Meta og:video (vídeo representativo de la página)
        og = soup.find("meta", property="og:video")
        if og and og.get("content"):
            url = og["content"]
            media = self._classify_url(url)
            if media and media["embed_url"] not in seen:
                seen.add(media["embed_url"])
                results.append(media)
            elif url not in seen:
                seen.add(url)
                results.append({"type": "video", "source": "og", "embed_url": url})

        return results

    def parse_text(self, text):
        """
        Extrae multimedia de un string de texto o HTML en bruto (p. ej. contenido RSS).
        Útil cuando solo se dispone del texto del feed, no del DOM completo.

        Returns:
            Lista de dicts multimedia sin duplicados.
        """
        results = []
        seen = set()

        # YouTube watch URLs (e.g. youtube.com/watch?v=ABC)
        for m in YOUTUBE_WATCH_RE.finditer(text):
            vid_id = m.group(1)
            embed = f"https://www.youtube.com/embed/{vid_id}?autoplay=0"
            if embed not in seen:
                seen.add(embed)
                results.append({"type": "video", "source": "youtube", "embed_url": embed})

        # YouTube embed URLs (e.g. youtube.com/embed/ABC)
        for m in YOUTUBE_EMBED_RE.finditer(text):
            vid_id = m.group(1)
            embed = f"https://www.youtube.com/embed/{vid_id}?autoplay=0"
            if embed not in seen:
                seen.add(embed)
                results.append({"type": "video", "source": "youtube", "embed_url": embed})

        # Vimeo
        for m in VIMEO_RE.finditer(text):
            vid_id = m.group(1)
            embed = f"https://player.vimeo.com/video/{vid_id}"
            if embed not in seen:
                seen.add(embed)
                results.append({"type": "video", "source": "vimeo", "embed_url": embed})

        # Twitter/X tweets
        for m in TWITTER_RE.finditer(text):
            tweet_id = m.group(1)
            url = f"https://twitter.com/i/web/status/{tweet_id}"
            if url not in seen:
                seen.add(url)
                results.append({"type": "social", "source": "twitter", "embed_url": url})

        # Instagram posts
        for m in INSTAGRAM_RE.finditer(text):
            shortcode = m.group(1)
            embed = f"https://www.instagram.com/p/{shortcode}/embed/"
            if embed not in seen:
                seen.add(embed)
                results.append({"type": "social", "source": "instagram", "embed_url": embed})

        # Archivos de vídeo directos (.mp4, .webm, .ogg)
        for m in VIDEO_EXT_RE.finditer(text):
            url = m.group(0)
            if url not in seen:
                seen.add(url)
                results.append({"type": "video", "source": "html5", "embed_url": url})

        return results

    def _classify_url(self, url):
        """
        Clasifica una URL individual y devuelve el dict multimedia correspondiente,
        o None si la URL no corresponde a ninguna plataforma conocida.
        El orden de comprobación importa: embed antes de watch para YouTube.
        """
        if not url:
            return None

        # YouTube embed src (prioridad sobre watch para evitar doble match)
        m = YOUTUBE_EMBED_RE.search(url)
        if m:
            embed = f"https://www.youtube.com/embed/{m.group(1)}?autoplay=0"
            return {"type": "video", "source": "youtube", "embed_url": embed}

        # YouTube watch link
        m = YOUTUBE_WATCH_RE.search(url)
        if m:
            embed = f"https://www.youtube.com/embed/{m.group(1)}?autoplay=0"
            return {"type": "video", "source": "youtube", "embed_url": embed}

        # Vimeo
        m = VIMEO_RE.search(url)
        if m:
            return {"type": "video", "source": "vimeo",
                    "embed_url": f"https://player.vimeo.com/video/{m.group(1)}"}

        # Twitter/X
        m = TWITTER_RE.search(url)
        if m:
            return {"type": "social", "source": "twitter",
                    "embed_url": f"https://twitter.com/i/web/status/{m.group(1)}"}

        # Instagram
        m = INSTAGRAM_RE.search(url)
        if m:
            return {"type": "social", "source": "instagram",
                    "embed_url": f"https://www.instagram.com/p/{m.group(1)}/embed/"}

        # TikTok
        m = TIKTOK_RE.search(url)
        if m:
            return {"type": "social", "source": "tiktok",
                    "embed_url": f"https://www.tiktok.com/embed/{m.group(1)}"}

        # Archivo de vídeo directo
        if VIDEO_EXT_RE.match(url):
            return {"type": "video", "source": "html5", "embed_url": url}

        return None


# Singleton reutilizado por ContentExtractor y RssScraper
media_parser = MediaParser()
