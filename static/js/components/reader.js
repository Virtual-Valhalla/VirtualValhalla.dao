/* ══════════════════════════════════════════════════════════════════════ */
/* READER / DATA-DECRYPTOR COMPONENT — openReader, closeReader          */
/*                                                                       */
/* Panel lateral que muestra el contenido completo de un artículo.      */
/* Flujo al abrir:                                                       */
/*   1. Mostrar estructura base con los datos del listado (rápido)      */
/*   2. Si hay imagen disponible, mostrarla de inmediato                */
/*   3. Hacer fetch a /article?url=… para enriquecer con:               */
/*        - Prioridad 1: vídeo embebido (YouTube, Vimeo, HTML5)         */
/*        - Prioridad 2: imagen de mejor calidad (og:image del scraper) */
/*        - Prioridad 3: indicador "sin media disponible"               */
/*   4. Inyectar el texto completo o resumen del artículo               */
/* ══════════════════════════════════════════════════════════════════════ */

/**
 * Abre el panel DATA_DECRYPTOR con el contenido del artículo.
 * Muestra la estructura inmediatamente y enriquece en background con /article.
 *
 * @param {Object} article - Objeto de artículo devuelto por /country-news
 */
function openReader(article) {
    const reader = document.getElementById('news-reader');
    const body   = document.getElementById('reader-body');
    reader.classList.add('reader-visible');

    // Formatear fecha si existe
    const pubDate    = article.publishedAt
        ? new Date(article.publishedAt).toLocaleDateString('es-ES',
            { day: 'numeric', month: 'short', year: 'numeric' })
        : '';
    const sourceName = article.source?.name || 'FUENTE DESCONOCIDA';

    // Imagen provisional del listado (puede mejorarse tras el fetch)
    const imageUrl = article.urlToImage || article.imagen || null;

    // Renderizar la estructura base con indicador de carga para la media
    body.innerHTML = `
        <div class="reader-media-wrap reader-media-loading" id="reader-media">
            <span class="reader-media-spinner">⟳ BUSCANDO MEDIA...</span>
        </div>
        <div class="reader-meta">
            <span class="reader-source">▶ ${sourceName.toUpperCase()}</span>
            ${pubDate ? `<span class="reader-date">${pubDate}</span>` : ''}
        </div>
        <p class="reader-title">${article.title || ''}</p>
        <p class="reader-desc">${article.description || 'Sin resumen disponible.'}</p>
        <div id="reader-full-content" class="reader-full-content"></div>
        <a href="${article.url}" target="_blank" class="news-link">[ ACCEDER A FUENTE EXTERNA → ]</a>
    `;

    // Mostrar imagen provisional mientras se carga el artículo completo
    if (imageUrl) {
        const mediaEl = document.getElementById('reader-media');
        if (mediaEl) {
            mediaEl.classList.remove('reader-media-loading');
            mediaEl.innerHTML = `<img class="reader-image" src="${imageUrl}" alt=""
                onerror="this.closest('.reader-media-wrap').classList.add('reader-media-empty'); this.closest('.reader-media-wrap').innerHTML='<span class=\\'reader-no-media\\'>[SIN IMAGEN DISPONIBLE]</span>'">`;
        }
    }

    // ── Enriquecer con contenido completo desde el backend ────────────────────
    fetch(`/article?url=${encodeURIComponent(article.url)}`)
        .then(r => r.json())
        .then(data => {
            const mediaEl = document.getElementById('reader-media');

            // ── PRIORIDAD 1: VÍDEO ───────────────────────────────────────────
            // Si el extractor encontró multimedia, preferir vídeo sobre imagen
            const multimedia = Array.isArray(data.multimedia) ? data.multimedia : [];
            const videoItem  = multimedia.find(m => m.type === 'video');

            if (videoItem && videoItem.embed_url) {
                const src     = videoItem.embed_url;
                const isYT    = src.includes('youtube.com') || src.includes('youtu.be');
                const isVimeo = src.includes('vimeo.com');

                if (isYT || isVimeo) {
                    // Embed iframe para YouTube y Vimeo
                    if (mediaEl) {
                        mediaEl.classList.remove('reader-media-loading');
                        mediaEl.innerHTML = `
                            <iframe class="reader-video"
                                src="${src}" frameborder="0"
                                allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                allowfullscreen></iframe>`;
                    }
                    logToConsole('▶ Video embebido encontrado', 'success');
                } else {
                    // Tag <video> nativo para archivos HTML5 directos
                    if (mediaEl) {
                        mediaEl.classList.remove('reader-media-loading');
                        mediaEl.innerHTML = `
                            <video class="reader-video" controls preload="metadata">
                                <source src="${src}">
                            </video>`;
                    }
                    logToConsole('▶ Video HTML5 encontrado', 'success');
                }
            }
            // ── PRIORIDAD 2: IMAGEN ──────────────────────────────────────────
            // Sin vídeo → usar imagen, mejorando a og:image del scraper si es distinta
            else {
                const finalImage = data.imagen || imageUrl;
                if (finalImage && mediaEl) {
                    mediaEl.classList.remove('reader-media-loading');
                    // Solo reemplazar si el scraper devolvió una imagen diferente (y mejor)
                    if (data.imagen && data.imagen !== imageUrl) {
                        mediaEl.innerHTML = `<img class="reader-image" src="${data.imagen}" alt=""
                            onerror="this.closest('.reader-media-wrap').classList.add('reader-media-empty'); this.closest('.reader-media-wrap').innerHTML='<span class=\\'reader-no-media\\'>[SIN IMAGEN DISPONIBLE]</span>'">`;
                    }
                }
                // ── PRIORIDAD 3: SIN MEDIA ───────────────────────────────────
                else if (!finalImage && mediaEl) {
                    mediaEl.classList.add('reader-media-empty');
                    mediaEl.innerHTML = `<span class="reader-no-media">[ SIN MEDIA DISPONIBLE ]</span>`;
                    logToConsole('ℹ️ Sin media disponible para este artículo', 'info');
                }
            }

            // ── CONTENIDO COMPLETO ────────────────────────────────────────────
            // Prioridad: contenido largo > resumen; mínimo 30 chars para ser útil
            const contentEl = document.getElementById('reader-full-content');
            if (contentEl) {
                const contenido = data.contenido || data.content || '';
                const resumen   = data.resumen || '';
                const text      = (contenido.length >= resumen.length) ? contenido : resumen;
                if (text && text.length > 30) {
                    const label = contenido.length > 30 ? '── CONTENIDO COMPLETO ──' : '── RESUMEN ──';
                    contentEl.innerHTML = `
                        <div class="reader-content-divider">${label}</div>
                        <div class="reader-content-text">${escapeHtml(text)}</div>`;
                }
            }
        })
        .catch(err => {
            // En caso de error de red, mantener la imagen provisional si existe
            logToConsole(`⚠️ Error cargando artículo: ${err.message}`, 'warning');
            const mediaEl = document.getElementById('reader-media');
            if (mediaEl) {
                if (!imageUrl) {
                    mediaEl.classList.add('reader-media-empty');
                    mediaEl.innerHTML = `<span class="reader-no-media">[ ERROR CARGANDO MEDIA ]</span>`;
                } else {
                    mediaEl.classList.remove('reader-media-loading');
                }
            }
        });
}

/**
 * Escapa caracteres HTML especiales para insertar texto plano como innerHTML.
 * Convierte saltos de línea en <br> para preservar el formato del artículo.
 *
 * @param {string} text - Texto a escapar
 * @returns {string} HTML seguro
 */
function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/\n/g, '<br>');
}

/**
 * Cierra el panel DATA_DECRYPTOR quitando la clase 'reader-visible'.
 */
function closeReader() {
    document.getElementById('news-reader').classList.remove('reader-visible');
}

/**
 * Carga un artículo en el visor legacy (#articleViewer).
 * Esta función está mantenida por compatibilidad pero no se usa en la UI principal.
 * El panel DATA_DECRYPTOR (openReader) es el visor activo.
 *
 * @param {string} url - URL del artículo a cargar
 */
function loadArticle(url) {
    const viewer = document.getElementById('articleViewer');
    viewer.style.display = 'block';
    viewer.innerHTML = 'Cargando artículo...';
    fetch(`/article?url=${encodeURIComponent(url)}`)
        .then(res => res.json())
        .then(data => {
            viewer.innerHTML = `
                <h2 style="color:#00ffff;">${data.titulo || data.title || ''}</h2>
                <hr>
                <p style="white-space:pre-line;">${data.contenido || data.content || ''}</p>
                <br>
                <a href="${url}" target="_blank" style="color:#ff00ff;">🔗 Ver original</a>
            `;
        })
        .catch(err => {
            viewer.innerHTML = 'Error cargando artículo';
            console.error(err);
        });
}
