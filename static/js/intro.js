/* ════════════════════════════════════════════════════════════════════ */
/* INTRO — Animación de entrada con GSAP + punto central Three.js      */
/*                                                                      */
/* Flujo de la intro:                                                   */
/*   1. Al cargar la página: crear un punto parpadeante en el globo    */
/*   2. El usuario hace click en cualquier parte de la pantalla        */
/*   3. El punto desaparece y se anima un zoom-in desde altitud 100    */
/*      hasta 1.65 (vista normal del globo) durante 4 segundos         */
/*   4. Al terminar el zoom: revelar los paneles UI con retraso         */
/*      escalonado y cargar las noticias globales                       */
/*                                                                      */
/* Dependencias: GSAP (gsap.min.js), Three.js, window.myGlobe,        */
/*               logToConsole, resetToGlobal                           */
/* ════════════════════════════════════════════════════════════════════ */

console.log("%c[INTRO] Sistema estable cargado", "color:#00ffff; font-weight:bold");

let centralPoint;           // mesh Three.js del punto parpadeante
let isIntroActive = true;   // flag para ejecutar la intro solo una vez

/**
 * Inicializa la animación de intro.
 * Si el globo aún no está listo (world.myGlobe), reintenta cada 500 ms.
 * Se llama desde window.onload en app.js.
 */
window.initIntro = function() {
    if (!window.myGlobe) {
        console.warn("[INTRO] Esperando globo...");
        setTimeout(window.initIntro, 500);
        return;
    }

    const globe = window.myGlobe;
    const scene = globe.scene();

    // Crear el punto central visible como esfera pequeña cyan
    centralPoint = new THREE.Mesh(
        new THREE.SphereGeometry(0.028, 32, 32),
        new THREE.MeshBasicMaterial({
            color: 0x77eeff,
            transparent: true,
            opacity: 1
        })
    );
    scene.add(centralPoint);

    // Animación de parpadeo infinita con GSAP (opacity 1 ↔ 0.15)
    gsap.to(centralPoint.material, {
        opacity: 0.15,
        duration: 0.6,
        repeat: -1,      // infinito
        yoyo: true,      // va y vuelve
        ease: "power2.inOut"
    });

    console.log("%c[INTRO] ✅ Punto central creado y visible", "color:#00ffcc; font-size:15px");
};

// ── Listener de click para disparar el zoom ───────────────────────────────────
// Se registra en el documento para capturar el primer click del usuario.
// El flag isIntroActive asegura que solo se ejecuta una vez.
document.addEventListener('click', () => {
    if (!isIntroActive) return;
    isIntroActive = false;

    const globe = window.myGlobe;
    if (!globe || !centralPoint) return;

    console.log("%c[INTRO] Click detectado → Zoom", "color:#ff00ff");

    // Encoger el punto hasta desaparecer mientras el globo hace zoom
    gsap.to(centralPoint.scale, {
        x: 0.01, y: 0.01, z: 0.01,
        duration: 1.4,
        ease: "power2.in"
    });

    // GSAP no puede animar globe.pointOfView() directamente porque no es una propiedad
    // de objeto plano. Se usa un objeto proxy intermedio: GSAP anima el número en el
    // proxy y onUpdate lo aplica al globo en cada frame.
    const startPov  = globe.pointOfView();
    const povProxy  = { altitude: startPov.altitude };

    gsap.to(povProxy, {
        altitude: 1.65,   // altitud final (vista normal del globo)
        duration: 4.0,
        ease: "power3.out",
        onStart: () => globe.controls().autoRotate = false, // parar rotación durante el zoom
        onUpdate: () => {
            globe.pointOfView({ altitude: povProxy.altitude }, 0);
            globe.controls().update();
        },
        onComplete: () => {
            // Reanudar auto-rotación al terminar el zoom
            globe.controls().autoRotate = true;
            globe.controls().autoRotateSpeed = 0.5;

            // Revelar los paneles UI con animación escalonada (150 ms de diferencia)
            setTimeout(() => {
                document.querySelector('.terminal-box').classList.add('panel-revealed');
            }, 150);
            setTimeout(() => {
                document.getElementById('error-console').classList.add('panel-revealed');
            }, 350);

            logToConsole('🔓 INTRO COMPLETADA - BIENVENIDO AL GLOBO', 'success');
            resetToGlobal(); // cargar noticias globales al terminar la intro
        }
    });
});
