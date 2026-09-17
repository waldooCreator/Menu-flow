/**
 * Diagnóstico responsive (SPEC-022). Se pega en la consola del navegador con
 * la app abierta en el ancho a probar (320 y 375), y luego:
 *
 *   await __auditar(["mesero-salon", "mesero-libro", ...])
 *
 * Mide cuatro cosas por pantalla, porque **medir el desborde no es verificar
 * el diseño responsive** — ese error ya costó dos correcciones:
 *
 *   ov      desborde horizontal de la página (px sobrantes)
 *   cortado hojas de texto cuyo contenido es más ancho que su caja: el corte
 *           NO produce desborde, y es lo que el desborde nunca ve
 *   bajo44  elementos tocables por debajo de 44 px (ancho o alto)
 *   texto   cuánto contenido había: una pantalla vacía aprueba sin merecerlo
 *
 * Reglas de medición, aprendidas a golpes:
 *   - Un elemento dentro de un ancestro invisible o ESCALADO no se mide: la
 *     animación de entrada deja las tarjetas en scale(0.9) hasta que entran,
 *     y un botón de 44 medía 40 sin estar mal.
 *   - Para una casilla, el blanco es el <label> o <span> que la envuelve.
 *   - Los enlaces en línea dentro de un párrafo quedan fuera: WCAG 2.5.8 los
 *     exime, no son un blanco separado del texto.
 *
 * Antes de medir: `python manage.py poblar_demo`, o media auditoría se hace
 * sobre pantallas vacías.
 */
window.__diag = () => {
  const d = document.documentElement, W = d.clientWidth;
  const memo = new Map();
  const oculto = (e) => {
    if (!e || e === document.body) return false;
    if (memo.has(e)) return memo.get(e);
    const s = getComputedStyle(e);
    const propio = s.display === "none" || s.visibility === "hidden" || s.opacity === "0"
      || (s.transform && s.transform !== "none" && !/^matrix\(1, 0, 0, 1,/.test(s.transform));
    const r = propio || oculto(e.parentElement);
    memo.set(e, r);
    return r;
  };
  const desc = (e) => {
    const c = [...e.classList].slice(0, 3).join(".");
    const t = (e.innerText || "").trim().replace(/\s+/g, " ").slice(0, 32);
    return `${e.tagName.toLowerCase()}${c ? "." + c : ""}${t ? ` "${t}"` : ""}`;
  };
  const todos = [...document.querySelectorAll("body *")]
    .filter((e) => !oculto(e) && e.getBoundingClientRect().height > 0);

  const cortado = todos.filter((e) => {
    if (e.children.length) return false;
    const s = getComputedStyle(e);
    if (s.overflowX === "auto" || s.overflowX === "scroll") return false;
    return e.scrollWidth > e.clientWidth + 1 && (e.textContent || "").trim().length > 0;
  }).map((e) => `${desc(e)} [${e.clientWidth}<${e.scrollWidth}]`);

  const blanco = (e) => (e.type === "checkbox" || e.type === "radio") ? (e.closest("label,span") || e) : e;
  const enLinea = (e) => e.tagName === "A" && getComputedStyle(e).display === "inline";
  const toc = todos
    .filter((e) => /^(BUTTON|A|SELECT|INPUT|TEXTAREA)$/.test(e.tagName) && !enLinea(e))
    .map((e) => { const r = blanco(e).getBoundingClientRect(); return { e, h: r.height, w: r.width }; })
    .filter((x) => x.h > 0);
  const b44 = toc.filter((x) => x.h < 44 || x.w < 44);

  return {
    ov: d.scrollWidth - W,
    cortado: cortado.slice(0, 8), nCortado: cortado.length,
    tocables: toc.length, bajo44: b44.length,
    minTocable: b44.length ? Math.round(Math.min(...b44.map((x) => Math.min(x.h, x.w)))) : null,
    peores: b44.sort((a, b) => Math.min(a.h, a.w) - Math.min(b.h, b.w)).slice(0, 6)
      .map((x) => `${desc(x.e)} ${Math.round(x.w)}x${Math.round(x.h)}`),
    texto: document.body.innerText.length,
  };
};

/** Recorre rutas por nombre con el router de la app y mide cada una. */
window.__auditar = async (rutas) => {
  const router = document.querySelector("#app").__vue_app__.config.globalProperties.$router;
  const espera = (ms) => new Promise((r) => setTimeout(r, ms));
  const out = [];
  for (const n of rutas) {
    await router.push({ name: n }).catch(() => {});
    await espera(1800);
    const d = window.__diag();
    out.push({ p: n, ov: d.ov, cort: d.nCortado, bajo44: `${d.bajo44}/${d.tocables}`, min: d.minTocable, txt: d.texto, ej: d.cortado[0], peor: d.peores[0] });
  }
  return out;
};

/** Abre un estado (modal, panel) tocando el primer control cuyo texto coincida, y mide. */
window.__abrir = async (ruta, expresion) => {
  const router = document.querySelector("#app").__vue_app__.config.globalProperties.$router;
  const espera = (ms) => new Promise((r) => setTimeout(r, ms));
  if (location.pathname !== router.resolve({ name: ruta }).path) {
    await router.push({ name: ruta }).catch(() => {});
    await espera(2200);
  }
  const control = [...document.querySelectorAll("button,li,a,label")]
    .find((b) => new RegExp(expresion, "i").test((b.innerText || "").trim()));
  if (!control) return { estado: `${ruta} › ${expresion}`, abrio: false };
  control.click();
  await espera(1300);
  const d = window.__diag();
  return { estado: `${ruta} › ${expresion}`, abrio: true, ov: d.ov, cort: d.nCortado, bajo44: `${d.bajo44}/${d.tocables}`, min: d.minTocable, peor: d.peores.slice(0, 3) };
};
