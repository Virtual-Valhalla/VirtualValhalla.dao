/* ════════════════════════════════════════════════════════════════════ */
/* APP — selectNode, loadNews, resetToGlobal, window.onload            */
/*                                                                      */
/* Módulo principal que conecta el globo con el panel de noticias.     */
/* Depende de globals definidos en archivos cargados antes:            */
/*   - world, BASE_ROTATION_SPEED (globe_engine.js)                   */
/*   - CATEGORIES, currentCatIndex (terminal.js)                       */
/*   - logToConsole, clearConsole, toggleConsole (console.js)          */
/*   - openReader, closeReader (reader.js)                             */
/*   - initIntro (intro.js)                                            */
/* ════════════════════════════════════════════════════════════════════ */

let selectedCountry     = null;  // código ISO del país actualmente seleccionado
let selectedCountryName = null;  // nombre legible del país (para logs y Deep-Scan)

/**
 * Selecciona un país al hacer click sobre su polígono en el globo.
 * Actualiza el estado global, hace zoom hacia el país y carga sus noticias.
 *
 * @param {string} name - Nombre del país (p.ej. "Spain")
 * @param {string} code - Código ISO-A2 en minúsculas (p.ej. "es")
 * @param {number} lat  - Latitud del centro del click
 * @param {number} lng  - Longitud del centro del click
 */
function selectNode(name, code, lat, lng) {
    // Validar que el nombre sea un valor real (el GeoJSON puede devolver undefined)
    if (!name || name === 'undefined' || name === '') {
        logToConsole(`❌ Nombre de país inválido (${name})`, 'error');
        return;
    }
    const normalizedCode = String(code || name).toLowerCase().trim();
    logToConsole(`📍 Seleccionando: ${name} (${normalizedCode})`, 'debug');

    selectedCountry     = normalizedCode;
    selectedCountryName = name;

    // Actualizar label del panel con el nombre del nodo seleccionado
    document.getElementById('node-label').innerText = `NODE: ${name.toUpperCase()}`;
    // Mostrar el botón de reset cámara al seleccionar un país
    document.getElementById('back-button').style.display = 'block';

    // Proteger contra coordenadas NaN (algunos polígonos del GeoJSON no devuelven lat/lng)
    const validLat = isNaN(lat) ? 0 : lat;
    const validLng = isNaN(lng) ? 0 : lng;

    // Animar cámara hacia el país seleccionado a altitud 0.6 (zoom cercano)
    world.pointOfView({ lat: validLat, lng: validLng, altitude: 0.6 }, 1000);
    // Reducir la auto-rotación al 10% para que el usuario pueda ver mejor el país
    world.controls().autoRotateSpeed = BASE_ROTATION_SPEED * 0.1;

    loadNews(normalizedCode);
}

/**
 * Solicita noticias al backend para el código de país dado y las renderiza
 * en el panel #news-container del NEWS_TERMINAL.
 *
 * Incluye la categoría actualmente seleccionada en la query.
 * Maneja los estados: cargando → éxito → error → sin resultados.
 *
 * @param {string} code - Código ISO-A2 del país o 'global' para feed global
 */
function loadNews(code) {
    const container = document.getElementById('news-container');

    // Validar el código antes de hacer la petición
    if (!code || code === 'undefined' || code === '' || code === null) {
        logToConsole(`❌ Intento de cargar noticias con código inválido: "${code}"`, 'error');
        container.innerHTML = `
            <div class="error-box">
                <strong>❌ CÓDIGO INVÁLIDO</strong><br>
                Por favor, selecciona un país válido.
            </div>`;
        return;
    }

    // Mostrar indicador de carga mientras se espera la respuesta
    container.innerHTML = `<div class="status-line">> ACCEDIENDO A SECTOR ${code.toUpperCase()}...</div>`;
    logToConsole(`Solicitando noticias para: ${code}`, 'info');

    // Construir la URL incluyendo la categoría si está seleccionada
    const encodedCode = encodeURIComponent(code);
    const cat         = CATEGORIES[currentCatIndex].api;
    const catLabel    = CATEGORIES[currentCatIndex].label;
    const newsUrl     = `/country-news?country=${encodedCode}${cat ? '&category=' + cat : ''}`;
    logToConsole(`📨 Endpoint: ${newsUrl}`, 'debug');

    fetch(newsUrl)
        .then(res => {
            logToConsole(`Status HTTP: ${res.status}`, 'debug');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(data => {
            // Informar al usuario cuando se usó el modo Deep-Scan
            if (data.scan_mode === 'deep-scan') {
                const countryLabel = selectedCountryName || code.toUpperCase();
                logToConsole(
                    `[SEARCH] Country not in primary list. Initiating Deep-Scan for ${countryLabel} + ${catLabel}...`,
                    'warning'
                );
            }

            // ── Error del servidor ────────────────────────────────────────────
            if (data.status === 'error') {
                logToConsole(`❌ ${data.type}: ${data.message}`, 'error');
                container.innerHTML = `
                    <div class="error-box">
                        <strong>❌ ${data.type}</strong><br>
                        ${data.message}<br>
                        <small>${data.details || ''}</small><br>
                        <button class="retry-btn" onclick="loadNews('${code}')">↻ REINTENTAR</button>
                    </div>`;
                return;
            }

            // ── Sin resultados ────────────────────────────────────────────────
            if (data.status === 'warning' || !data.articles || data.articles.length === 0) {
                logToConsole(`⚠️ Sin artículos para ${code}`, 'warning');
                container.innerHTML = `
                    <div class="error-box">
                        <strong>⚠️ SIN RESULTADOS</strong><br>
                        ${data.message}<br>
                        <button class="retry-btn" onclick="loadNews('${code}')">↻ REINTENTAR</button>
                    </div>`;
                return;
            }

            // ── Éxito: renderizar la lista de artículos ───────────────────────
            const articles = data.articles;
            const cacheMsg = data.cached
                ? `⚡ CACHÉ (expira en ${data.expires_in})`
                : '🌐 API (datos frescos)';
            const modeTag  = data.scan_mode === 'deep-scan' ? ' [DEEP-SCAN]' : '';
            logToConsole(`✅ ${articles.length} noticias para ${code.toUpperCase()}${modeTag} — ${cacheMsg}`, 'success');

            container.innerHTML = '';
            articles.forEach((art, idx) => {
                const div = document.createElement('div');
                div.className = 'news-item';
                // Nombre de la fuente (opcional)
                const src = art.source?.name ? `<span class="news-src">${art.source.name}</span>` : '';
                // Número de artículo con padding de 2 dígitos (01, 02, …)
                div.innerHTML = `
                    <div class="news-item-body">
                        <span class="news-rank">${String(idx + 1).padStart(2, '0')}</span>
                        <span class="news-title-text">${art.title}</span>
                        ${src}
                    </div>`;
                // Abrir el lector al hacer click en cualquier parte del item
                div.onclick = () => openReader(art);
                container.appendChild(div);
            });
        })
        .catch(err => {
            logToConsole(`🔌 Error de conexión: ${err.message}`, 'error');
            container.innerHTML = `
                <div class="error-box">
                    <strong>❌ ERROR</strong><br>
                    ${err.message}<br>
                    <button class="retry-btn" onclick="loadNews('${code}')">↻ REINTENTAR</button>
                </div>`;
        });
}

/**
 * Resetea la vista al estado global:
 *   - Limpia la selección de país
 *   - Cierra el panel DATA_DECRYPTOR
 *   - Vuelve la cámara a la vista global (latitud 20, altitud 1.5)
 *   - Restablece la velocidad de rotación
 *   - Carga el feed global de noticias
 */
function resetToGlobal() {
    logToConsole('Reseteando a vista global', 'info');
    selectedCountry = null;
    closeReader();
    document.getElementById('node-label').innerText = 'NODE: GLOBAL FEED';
    document.getElementById('back-button').style.display = 'none';
    world.pointOfView({ lat: 20, lng: 0, altitude: 1.5 }, 1000);
    world.controls().autoRotateSpeed = BASE_ROTATION_SPEED;
    loadNews('global');
}

// ── Arranque de la aplicación ─────────────────────────────────────────────────
// window.onload garantiza que todos los scripts y el DOM están listos
window.onload = () => {
    logToConsole('Aplicación cargada', 'success');
    initIntro(); // arrancar la animación de intro (definida en intro.js)
};
