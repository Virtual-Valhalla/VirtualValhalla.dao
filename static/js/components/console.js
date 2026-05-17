/* ════════════════════════════════════════════════════════════════════ */
/* CONSOLE COMPONENT — logToConsole, clearConsole, toggleConsole       */
/*                                                                      */
/* Panel de depuración en pantalla que muestra mensajes de la app      */
/* con nivel (error/warning/success/info/debug), timestamp y color.    */
/* Máximo 50 mensajes en pantalla; los más antiguos se eliminan.       */
/* ════════════════════════════════════════════════════════════════════ */

let isConsoleCollapsed = false;

/**
 * Devuelve la hora actual en formato HH:MM:SS para el prefijo de cada mensaje.
 */
function getTimeStamp() {
    const now = new Date();
    return `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
}

/**
 * Registra un mensaje en el panel de consola y en console.log del navegador.
 *
 * @param {string} message - Texto del mensaje
 * @param {string} type    - Nivel: 'error' | 'warning' | 'success' | 'info' | 'debug'
 * @param {*}      details - Datos adicionales opcionales para console.log
 */
function logToConsole(message, type = 'info', details = '') {
    const timestamp = getTimeStamp();

    // Mapa de tipo → estilo visual
    const typeMap = {
        'error':   { icon: '🔴', label: 'ERROR',   class: 'msg-error' },
        'warning': { icon: '🟡', label: 'WARNING',  class: 'msg-warning' },
        'success': { icon: '🟢', label: 'SUCCESS',  class: 'msg-success' },
        'info':    { icon: '🔵', label: 'INFO',     class: 'msg-info' },
        'debug':   { icon: '⚫', label: 'DEBUG',    class: 'msg-debug' },
    };
    const typeInfo = typeMap[type] || typeMap['info'];

    // Reflejar también en la consola del navegador para depuración con DevTools
    console.log(`[${timestamp}] ${typeInfo.icon} ${typeInfo.label}: ${message}`, details);

    // Crear el elemento DOM del mensaje
    const msgEl = document.createElement('div');
    msgEl.className = `console-message ${typeInfo.class}`;
    msgEl.innerHTML = `
        <span class="console-time">[${timestamp}]</span>
        <span class="console-type">${typeInfo.icon} ${typeInfo.label}</span>
        <span>${message}</span>
    `;

    const consoleContent = document.getElementById('console-content');
    consoleContent.appendChild(msgEl);

    // Limitar a 50 mensajes — eliminar el más antiguo si se supera el límite
    const messages = consoleContent.querySelectorAll('.console-message');
    if (messages.length > 50) messages[0].remove();

    // Auto-scroll al último mensaje
    consoleContent.scrollTop = consoleContent.scrollHeight;
}

/**
 * Vacía todos los mensajes del panel de consola y registra el evento.
 */
function clearConsole() {
    document.getElementById('console-content').innerHTML = '';
    logToConsole('Consola limpiada', 'info');
}

/**
 * Colapsa o expande el panel de consola.
 * Alterna la clase CSS 'console-collapsed' y actualiza el botón +/−.
 */
function toggleConsole() {
    const consoleEl = document.getElementById('error-console');
    const btn       = document.getElementById('collapse-btn');
    isConsoleCollapsed = !isConsoleCollapsed;
    consoleEl.classList.toggle('console-collapsed', isConsoleCollapsed);
    btn.textContent = isConsoleCollapsed ? '+' : '−';
}
