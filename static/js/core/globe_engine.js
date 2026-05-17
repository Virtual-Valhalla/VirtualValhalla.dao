/* ════════════════════════════════════════════════════════════════════ */
/* GLOBE ENGINE — Inicialización de Three.js / Globe.gl y GeoJSON      */
/*                                                                      */
/* Crea el globo 3D interactivo y gestiona:                            */
/*   - Estilos de polígonos (bordes, colores, hover)                   */
/*   - Eventos de click sobre países y zonas del globo                 */
/*   - Carga del GeoJSON con los límites de los 177 países             */
/*   - Auto-rotación, inclinación y resize responsivo                  */
/*                                                                      */
/* Dependencias globales (cargadas antes en index.html):               */
/*   THREE (three.min.js), Globe (globe.gl.min.js), logToConsole,      */
/*   selectNode, resetToGlobal, selectedCountry                        */
/* ════════════════════════════════════════════════════════════════════ */

/* Variable global del globo — accesible por intro.js y app.js */
let world;
let hoverD = null;             // polígono actualmente bajo el cursor
const BASE_ROTATION_SPEED = 0.5; // velocidad de auto-rotación normal

// ── Inicialización del globo ──────────────────────────────────────────────────

world = Globe()(document.getElementById('globeViz'))
    // Textura del globo y del fondo espacial (desde CDN de three-globe)
    .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
    .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')

    // Estilo de polígonos de países
    .polygonSideColor(() => 'rgba(255, 0, 255, 0.2)')      // laterales magenta translúcido
    .polygonStrokeColor(() => '#ff00ff')                    // borde magenta
    .polygonCapColor(d => d === hoverD                      // tapa: cyan en hover, invisible en reposo
        ? 'rgba(0, 255, 255, 0.3)'
        : 'rgba(0, 255, 255, 0.00)')
    .polygonAltitude(d => d === hoverD ? 0.05 : 0.00175)   // elevación extra en hover

    // Estilo de puntos (no usados en la versión actual, reservado para marcadores)
    .pointColor(() => '#ff00ff')
    .pointAltitude(0.07)
    .pointRadius(0.5)
    .pointsMerge(true)  // fusionar puntos cercanos para mejorar rendimiento

    // ── Eventos de interacción ────────────────────────────────────────────────

    // Hover sobre un país: actualizar hoverD para re-renderizar estilos
    .onPolygonHover(poly => {
        hoverD = poly;
        world.polygonAltitude(world.polygonAltitude()); // forzar re-render de altitudes
    })

    // Click sobre un polígono de país
    .onPolygonClick((polygon, event, { lat, lng }) => {
        logToConsole('🖱️ Polígono clickeado. Inspeccionando propiedades...', 'debug');
        const d = polygon.properties;

        // El GeoJSON de Natural Earth usa ADMIN como nombre principal
        const name = d.ADMIN || d.name || d.NAME || 'Unknown Country';

        // Extraer el código ISO-A2; varios campos de fallback por inconsistencias del GeoJSON
        let code = d.ISO_A2 || d.iso_a2 || '-99';
        if (code === '-99' || !code) code = d.ISO_A2_EH || '-99'; // Kosovo y excepciones
        if (code === '-99' || !code) code = d.WB_A2     || '-99'; // código del Banco Mundial
        if (code === '-99' || !code) {
            // Último recurso: usar el nombre del país como identificador (deep-scan por nombre)
            code = name.toLowerCase().replace(/[\s,.'()]+/g, '_');
            logToConsole(`⚠️ Sin código ISO para "${name}", buscando por nombre`, 'warning');
        }

        selectNode(name, code.toLowerCase(), lat, lng);
    })

    // Click sobre un punto marcador (por si se añaden en el futuro)
    .onPointClick(pt => selectNode(pt.name, pt.id, pt.lat, pt.lng))

    // Click sobre zona vacía del globo: volver a vista global si hay país seleccionado
    .onGlobeClick(() => { if (selectedCountry) resetToGlobal(); });

// Exponer el globo en window para que intro.js pueda acceder a él
window.myGlobe = world;

// ── Posición y controles iniciales ───────────────────────────────────────────

// Posición muy alejada para el efecto de intro (zoom-out inicial)
world.pointOfView({ lat: 25, lng: 0, altitude: 100.0 }, 0);
world.controls().autoRotate = false; // se activa tras la intro

// Activar auto-rotación y establecer velocidad base
world.controls().autoRotate = true;
world.controls().autoRotateSpeed = BASE_ROTATION_SPEED;

// Inclinación sutil para dar sensación de perspectiva más cinematográfica
const tiltAng = 0.05;
world.scene().rotation.z = tiltAng;
world.scene().rotation.x = 0.1;

// ── Responsividad ────────────────────────────────────────────────────────────

// Redimensionar el canvas al cambiar el tamaño de la ventana
window.addEventListener('resize', () => {
    const container = document.getElementById('globeViz');
    world.width(container.clientWidth);
    world.height(container.clientHeight);
});

// ── Carga del GeoJSON ─────────────────────────────────────────────────────────
// Se obtiene desde GitHub CDN (Natural Earth 110m — resolución óptima para el globo).
// El GeoJSON define los polígonos de fronteras de cada país.
// Si la carga falla (sin conexión, CDN caído), el globo funciona sin polígonos.
logToConsole('Cargando GeoJSON...', 'info');

fetch('https://raw.githubusercontent.com/martynafford/natural-earth-geojson/refs/heads/master/110m/cultural/ne_110m_admin_0_countries_lakes.json')
    .then(res => {
        if (!res.ok) throw new Error('No se pudo cargar GeoJSON');
        return res.json();
    })
    .then(countries => {
        // Filtrar features sin propiedades de nombre válido (datos corruptos en el GeoJSON)
        const cleanFeatures = countries.features.filter(f =>
            f.properties &&
            (f.properties.ADMIN || f.properties.name || f.properties.NAME)
        );
        if (cleanFeatures.length === 0) {
            logToConsole('❌ No se encontraron países válidos en el GeoJSON', 'error');
            return;
        }
        logToConsole(`✅ ${cleanFeatures.length} países cargados correctamente`, 'success');
        world.polygonsData(cleanFeatures); // render de todos los polígonos en el globo
    })
    .catch(err => {
        logToConsole(`Error cargando GeoJSON: ${err.message}`, 'error');
        console.error('GeoJSON Error:', err);
    });
