/**
 * Entrada lateral con profundidad (Sistema de Diseño §Movimiento).
 *
 * Cada elemento entra desde el lado más cercano a donde queda. La dirección
 * se calcula por POSICIÓN REAL, no por índice, para que funcione igual con
 * 3 columnas, 2 o lista.
 */

const SIN_MOVIMIENTO =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function esUnaColumna(rejilla) {
  const cols = getComputedStyle(rejilla).gridTemplateColumns.split(" ").filter(Boolean);
  return cols.length <= 1;
}

function direccionDe(el, centroRejilla, unaColumna, indice) {
  // En lista no hay "lado natural": se alterna.
  if (unaColumna) return indice % 2 === 0 ? "izq" : "der";

  const r = el.getBoundingClientRect();
  const delta = r.left + r.width / 2 - centroRejilla;
  // Cerca del eje = columna central: viaja menos pero entra más difuminada.
  if (Math.abs(delta) < r.width * 0.4) return "centro";
  return delta < 0 ? "izq" : "der";
}

/**
 * `requestAnimationFrame` no corre en pestañas en segundo plano: sin el
 * respaldo por temporizador, las entradas nunca se activarían y el menú
 * quedaría invisible de forma permanente.
 */
function unaVez(accion) {
  let hecho = false;
  const correr = () => { if (!hecho) { hecho = true; accion(); } };
  requestAnimationFrame(() => requestAnimationFrame(correr));
  setTimeout(correr, 120);
}

export function prepararEntradaLateral(rejilla, elementos, { escalon = 0 } = {}) {
  if (SIN_MOVIMIENTO || !rejilla || elementos.length === 0) return;

  // Transición apagada mientras se asigna el estado inicial: evita que el
  // elemento ya pintado se vea desvanecerse (parpadeo al cargar).
  document.body.classList.add("preparando");

  const rect = rejilla.getBoundingClientRect();
  const centro = rect.left + rect.width / 2;
  const unaColumna = esUnaColumna(rejilla);

  elementos.forEach((el, i) => {
    el.classList.add("entrada", `entrada--${direccionDe(el, centro, unaColumna, i)}`);
  });

  unaVez(() => {
    document.body.classList.remove("preparando");
    observar(elementos, escalon);
  });
}

function observar(elementos, escalon) {
  const obs = new IntersectionObserver(
    (entradas) => {
      entradas.forEach((en) => {
        if (!en.isIntersecting) return;
        const el = en.target;
        const retraso = escalon ? elementos.indexOf(el) * escalon : 0;
        setTimeout(() => el.classList.add("entrada--visible"), retraso);

        el.addEventListener(
          "transitionend",
          (ev) => { if (ev.propertyName === "transform") el.classList.add("entrada--asentada"); },
          { once: true }
        );
        obs.unobserve(el);
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
  );
  elementos.forEach((el) => obs.observe(el));
}
