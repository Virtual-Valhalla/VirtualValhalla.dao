/* ════════════════════════════════════════════════════════════════════ */
/* TERMINAL COMPONENT — categorías, dropdown, swipe y toggleTerminal   */
/*                                                                      */
/* Gestiona el selector de categorías del panel NEWS_TERMINAL.         */
/* Las categorías se mapean a parámetros de la API (/country-news).    */
/* Soporta navegación con botones ◄ ►, dropdown y swipe táctil.       */
/* ════════════════════════════════════════════════════════════════════ */

let isTerminalCollapsed = false;

/**
 * Lista de categorías disponibles.
 * 'label' es el texto mostrado en la UI (español);
 * 'api' es el valor enviado al backend (/country-news?category=…).
 * Un 'api' vacío significa "sin filtro de categoría" (todas las noticias).
 */
const CATEGORIES = [
    { label: 'GENERAL',         api: '' },
    { label: 'TECNOLOGÍA',      api: 'technology' },
    { label: 'NEGOCIOS',        api: 'business' },
    { label: 'DEPORTES',        api: 'sports' },
    { label: 'ENTRETENIMIENTO', api: 'entertainment' },
    { label: 'SALUD',           api: 'health' },
    { label: 'CIENCIA',         api: 'science' },
];

// Índice de la categoría actualmente seleccionada
let currentCatIndex = 0;

/**
 * Navega a la categoría anterior (con wrap circular) y recarga las noticias.
 */
function prevCategory() {
    currentCatIndex = (currentCatIndex - 1 + CATEGORIES.length) % CATEGORIES.length;
    updateCategoryUI();
    loadNews(selectedCountry || 'global');
}

/**
 * Navega a la categoría siguiente (con wrap circular) y recarga las noticias.
 */
function nextCategory() {
    currentCatIndex = (currentCatIndex + 1) % CATEGORIES.length;
    updateCategoryUI();
    loadNews(selectedCountry || 'global');
}

/**
 * Actualiza el label del selector con la categoría activa y cierra el dropdown.
 */
function updateCategoryUI() {
    document.getElementById('cat-label').textContent = CATEGORIES[currentCatIndex].label + ' ▾';
    closeCatDropdown();
}

/**
 * Alterna el dropdown de categorías.
 * Si ya está abierto, lo cierra. Si está cerrado, lo construye y muestra.
 * La categoría activa aparece resaltada con la clase 'cat-dd-active'.
 */
function toggleCatDropdown() {
    const dd = document.getElementById('cat-dropdown');
    if (dd.style.display === 'block') {
        closeCatDropdown();
        return;
    }
    dd.innerHTML = '';
    CATEGORIES.forEach((cat, i) => {
        const item = document.createElement('div');
        item.className = 'cat-dd-item' + (i === currentCatIndex ? ' cat-dd-active' : '');
        item.textContent = cat.label;
        item.addEventListener('click', e => {
            e.stopPropagation(); // evitar que el click cierre el dropdown inmediatamente
            currentCatIndex = i;
            updateCategoryUI();
            loadNews(selectedCountry || 'global');
        });
        dd.appendChild(item);
    });
    dd.style.display = 'block';
}

/**
 * Cierra el dropdown de categorías si está abierto.
 */
function closeCatDropdown() {
    const dd = document.getElementById('cat-dropdown');
    if (dd) dd.style.display = 'none';
}

// Cierra el dropdown al hacer click fuera de él (capture phase para mayor fiabilidad)
document.addEventListener('click', e => {
    const dd    = document.getElementById('cat-dropdown');
    const label = document.getElementById('cat-label');
    if (dd && label && !dd.contains(e.target) && e.target !== label) {
        closeCatDropdown();
    }
}, true);

/**
 * Colapsa o expande el panel NEWS_TERMINAL completo.
 * Alterna la clase CSS 'terminal-box-collapsed' y actualiza el botón +/−.
 */
function toggleTerminal() {
    const box = document.querySelector('.terminal-box');
    const btn = document.querySelector('.terminal-box-btn');
    isTerminalCollapsed = !isTerminalCollapsed;
    box.classList.toggle('terminal-box-collapsed', isTerminalCollapsed);
    btn.textContent = isTerminalCollapsed ? '+' : '−';
    if (isTerminalCollapsed) closeCatDropdown(); // cerrar dropdown si el panel se colapsa
}

// ── Soporte táctil: swipe horizontal en la fila de categorías ─────────────────
// Un swipe de > 40 px a la izquierda avanza la categoría; a la derecha, retrocede.
let _swipeStartX = null;

document.addEventListener('DOMContentLoaded', () => {
    // Inicializar el label con la primera categoría
    document.getElementById('cat-label').textContent = CATEGORIES[0].label + ' ▾';

    const catRow = document.querySelector('.category-row');
    if (!catRow) return;

    catRow.addEventListener('touchstart', e => {
        _swipeStartX = e.touches[0].clientX;
    }, { passive: true });

    catRow.addEventListener('touchend', e => {
        if (_swipeStartX === null) return;
        const dx = e.changedTouches[0].clientX - _swipeStartX;
        if (Math.abs(dx) > 40) dx < 0 ? nextCategory() : prevCategory();
        _swipeStartX = null;
    }, { passive: true });
});
