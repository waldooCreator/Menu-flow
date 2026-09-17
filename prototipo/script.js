/**
 * Prototipo visual — Fase 0. Comportamiento estético únicamente
 * (parallax de recorrido largo, entrada lateral, filtros con scroll-spy).
 * Sin lógica de pedido real.
 */

const currency = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

const SIN_MOVIMIENTO = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------------------------------------------------------------------- */
/* Render                                                                  */
/* ---------------------------------------------------------------------- */

function renderMenu() {
  const grid = document.getElementById("menuGrid");
  const filtersInner = document.getElementById("filtersInner");

  MENU_DATA.categorias.forEach((cat, i) => {
    const chip = document.createElement("button");
    chip.className = "chip" + (i === 0 ? " is-active" : "");
    chip.dataset.categoria = cat.id;
    chip.textContent = cat.nombre;
    filtersInner.appendChild(chip);

    const heading = document.createElement("h2");
    heading.className = "category-heading";
    heading.id = `cat-${cat.id}`;
    heading.dataset.categoria = cat.id;
    heading.textContent = cat.nombre;
    grid.appendChild(heading);

    MENU_DATA.platos
      .filter((p) => p.categoria === cat.id)
      .forEach((plato) => grid.appendChild(renderCard(plato)));
  });
}

function renderCard(plato) {
  const disponible = plato.disponible !== false;

  const card = document.createElement("article");
  card.className = "card" + (disponible ? "" : " is-unavailable");

  const badges = (plato.tags || [])
    .map((t) => `<span class="tag tag--${t}">${t}</span>`)
    .join("");

  // Respaldo digno si el plato no tiene foto: inicial sobre color de marca
  const media = plato.foto
    ? `<img class="card__img" src="${plato.foto}" alt="${plato.nombre}" loading="lazy">`
    : `<div class="card__fallback">${plato.nombre.charAt(0)}</div>`;

  const stats = (plato.stats || [])
    .map(([n, l]) => `<div class="card__stat"><b>${n}</b><span>${l}</span></div>`)
    .join("");

  card.innerHTML = `
    <figure class="card__figure">
      ${media}
      <div class="card__badges">${badges}</div>
      ${disponible ? "" : '<div class="card__soldout"><span>Agotado hoy</span></div>'}
      ${disponible
        ? `<button class="card__add" type="button" data-id="${plato.id}"
                   aria-label="Agregar ${plato.nombre} al pedido">+</button>`
        : ""}
    </figure>
    <div class="card__body">
      <div class="card__head">
        <h3 class="card__name">${plato.nombre}</h3>
        <span class="card__price">${currency.format(plato.precio)}</span>
      </div>
      <p class="card__desc">${plato.descripcion}</p>
      ${plato.alergenos && plato.alergenos !== "—"
        ? `<p class="card__allergens">${plato.alergenos}</p>` : ""}
      ${stats ? `<div class="card__stats">${stats}</div>` : ""}
    </div>
  `;
  return card;
}

/* ---------------------------------------------------------------------- */
/* Entrada lateral con profundidad                                         */
/*                                                                         */
/* Cada elemento entra desde el lado más cercano a donde queda. La          */
/* dirección se calcula por posición real, no por índice, para que funcione */
/* igual en 3 columnas, en 2 o en lista.                                    */
/* ---------------------------------------------------------------------- */

/** Ejecuta la acción una sola vez, tras dos frames o por temporizador,
 *  lo que ocurra primero. Necesario porque requestAnimationFrame no corre
 *  si la pestaña está en segundo plano. */
function unaVez(accion) {
  let hecho = false;
  const correr = () => { if (!hecho) { hecho = true; accion(); } };
  requestAnimationFrame(() => requestAnimationFrame(correr));
  setTimeout(correr, 120);
}

function esUnaColumna(grid) {
  const cols = getComputedStyle(grid).gridTemplateColumns.split(" ").filter(Boolean);
  return cols.length <= 1;
}

function direccionDe(el, centroGrid, unaColumna, indice) {
  // En lista de una sola columna no hay "lado natural": se alterna.
  if (unaColumna) return indice % 2 === 0 ? "izq" : "der";

  const r = el.getBoundingClientRect();
  const centroEl = r.left + r.width / 2;
  const delta = centroEl - centroGrid;

  // Cerca del eje = columna central: viaja menos pero entra más difuminada.
  if (Math.abs(delta) < r.width * 0.4) return "centro";
  return delta < 0 ? "izq" : "der";
}

function prepararEntrada() {
  if (SIN_MOVIMIENTO) return;

  const grid = document.getElementById("menuGrid");
  const cards = Array.from(grid.querySelectorAll(".card"));
  const headings = Array.from(grid.querySelectorAll(".category-heading"));
  const chips = Array.from(document.querySelectorAll(".chip"));

  // Transición apagada mientras se asigna el estado inicial (evita el parpadeo).
  document.body.classList.add("js-preparando");

  const rectGrid = grid.getBoundingClientRect();
  const centroGrid = rectGrid.left + rectGrid.width / 2;
  const unaColumna = esUnaColumna(grid);

  cards.forEach((card, i) => {
    card.classList.add("reveal", `reveal--${direccionDe(card, centroGrid, unaColumna, i)}`);
  });

  // Los títulos de categoría entran siempre desde la izquierda: anclan la lectura.
  headings.forEach((h) => h.classList.add("reveal", "reveal--izq"));

  // Los chips entran desde la derecha, en secuencia escalonada.
  chips.forEach((c) => c.classList.add("reveal", "reveal--der"));

  // Una vez pintado el estado inicial, se habilita la animación.
  // Se usa requestAnimationFrame, pero con respaldo por temporizador: en una
  // pestaña en segundo plano rAF no se ejecuta y las entradas nunca se
  // activarían.
  unaVez(() => {
    document.body.classList.remove("js-preparando");
    observarEntrada(cards.concat(headings), 0);
    observarEntrada(chips, 70); // escalonado entre chips
  });

  // Al cambiar el ancho cambia el número de columnas, así que se recalcula
  // la dirección de los elementos que todavía no han entrado.
  let temporizador;
  window.addEventListener("resize", () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => recalcularDirecciones(grid, cards), 180);
  }, { passive: true });
}

function recalcularDirecciones(grid, cards) {
  const rect = grid.getBoundingClientRect();
  const centro = rect.left + rect.width / 2;
  const unaColumna = esUnaColumna(grid);

  cards.forEach((card, i) => {
    if (card.classList.contains("is-revealed")) return; // ya entró: no se toca
    card.classList.remove("reveal--izq", "reveal--der", "reveal--centro");
    card.classList.add(`reveal--${direccionDe(card, centro, unaColumna, i)}`);
  });
}

function observarEntrada(elementos, escalon) {
  const obs = new IntersectionObserver(
    (entradas) => {
      entradas.forEach((en) => {
        if (!en.isIntersecting) return;
        const el = en.target;
        const retraso = escalon ? elementos.indexOf(el) * escalon : 0;

        setTimeout(() => el.classList.add("is-revealed"), retraso);

        // Al terminar, se retiran blur y will-change (capas compuestas caras).
        el.addEventListener(
          "transitionend",
          (ev) => { if (ev.propertyName === "transform") el.classList.add("is-settled"); },
          { once: true }
        );

        obs.unobserve(el); // una sola vez por elemento
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
  );

  elementos.forEach((el) => obs.observe(el));
}

/* ---------------------------------------------------------------------- */
/* Filtros con scroll-spy                                                  */
/* ---------------------------------------------------------------------- */

function setupFilters() {
  const filtersInner = document.getElementById("filtersInner");
  const chips = Array.from(filtersInner.querySelectorAll(".chip"));
  const headings = Array.from(document.querySelectorAll(".category-heading"));

  filtersInner.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    document.getElementById(`cat-${chip.dataset.categoria}`)
      ?.scrollIntoView({ behavior: "smooth" });
  });

  const setActive = (catId) => {
    chips.forEach((c) => c.classList.toggle("is-active", c.dataset.categoria === catId));
    chips.find((c) => c.dataset.categoria === catId)
      ?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  };

  const spy = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => { if (en.isIntersecting) setActive(en.target.dataset.categoria); });
    },
    { rootMargin: "-40% 0px -55% 0px", threshold: 0 }
  );
  headings.forEach((h) => spy.observe(h));
}

/* ---------------------------------------------------------------------- */
/* Hero: parallax de recorrido largo                                       */
/*                                                                         */
/* El hero es sticky dentro de .hero-scroll (200vh). El progreso se mide   */
/* sobre todo ese recorrido, no sobre una sola pantalla, para que la       */
/* animación se sienta larga y gradual.                                     */
/* ---------------------------------------------------------------------- */

function setupHero() {
  const topbar = document.getElementById("topbar");
  const heroScroll = document.getElementById("heroScroll");
  const heroBg = document.getElementById("heroBg");
  const heroContent = document.getElementById("heroContent");
  const cue = document.getElementById("heroCue");
  const protoTag = document.getElementById("protoTag");

  let ticking = false;
  let cueOculta = false;

  function update() {
    const y = window.scrollY;
    const recorrido = Math.max(heroScroll.offsetHeight - window.innerHeight, 1);
    const p = Math.min(Math.max(y / recorrido, 0), 1);

    // La barra superior cambia cuando el hero ya casi termina.
    topbar.classList.toggle("is-scrolled", p > 0.92);

    // La etiqueta aparece al salir del hero; el carrito además exige
    // que haya algo en el pedido.
    fueraDelHero = p > 0.9;
    protoTag.classList.toggle("is-visible", fueraDelHero);
    actualizarBotonCarrito();

    if (!SIN_MOVIMIENTO) {
      // Fondo: se desplaza durante todo el recorrido.
      heroBg.style.transform = `translateY(${p * 18}vh) scale(${1 + p * 0.12})`;

      // Contenido: se desvanece en el primer 65% y sube mientras tanto.
      const pc = Math.min(p / 0.65, 1);
      heroContent.style.opacity = String(1 - pc);
      heroContent.style.transform =
        `translateY(${-pc * 90}px) scale(${1 - pc * 0.12})`;

      // La flecha desaparece apenas empieza el scroll y no vuelve.
      if (!cueOculta && y > 40) {
        cue.classList.add("is-hidden");
        cueOculta = true;
      }
    }
    ticking = false;
  }

  window.addEventListener("scroll", () => {
    if (!ticking) { requestAnimationFrame(update); ticking = true; }
  }, { passive: true });

  window.addEventListener("resize", update, { passive: true });

  update();
}

/* ---------------------------------------------------------------------- */
/* Carrito (visual)                                                        */
/*                                                                         */
/* Estado en memoria únicamente: en Fase 0 no hay persistencia ni backend.  */
/* El pedido NO se guarda en base de datos hasta que el mesero confirma     */
/* (SPEC-002 / ADR-002).                                                   */
/* ---------------------------------------------------------------------- */

const carrito = new Map(); // id -> { plato, cantidad, tags:Set, nota }

function platoPorId(id) {
  return MENU_DATA.platos.find((p) => p.id === id);
}

function agregarAlCarrito(id) {
  const item = carrito.get(id);
  if (item) {
    item.cantidad += 1;
  } else {
    carrito.set(id, { plato: platoPorId(id), cantidad: 1, tags: new Set(), nota: "" });
  }
  sincronizarCarrito();
}

function cambiarCantidad(id, delta) {
  const item = carrito.get(id);
  if (!item) return;
  item.cantidad += delta;
  if (item.cantidad <= 0) carrito.delete(id);
  sincronizarCarrito();
  renderPedido();
}

function totalUnidades() {
  let n = 0;
  carrito.forEach((i) => { n += i.cantidad; });
  return n;
}

function totalPrecio() {
  let t = 0;
  carrito.forEach((i) => { t += i.plato.precio * i.cantidad; });
  return t;
}

/* El botón flotante aparece solo cuando se cumplen las dos condiciones:
   ya se salió del hero Y hay algo en el pedido. */
let fueraDelHero = false;

function actualizarBotonCarrito() {
  const btn = document.getElementById("cartBtn");
  btn.classList.toggle("is-visible", fueraDelHero && totalUnidades() > 0);
}

/** Refleja el estado del carrito en el botón flotante y en las tarjetas. */
function sincronizarCarrito() {
  const n = totalUnidades();
  document.getElementById("cartCount").textContent = String(n);

  document.querySelectorAll(".card__add").forEach((b) => {
    const item = carrito.get(Number(b.dataset.id));
    b.classList.toggle("tiene", !!item);
    b.textContent = item ? String(item.cantidad) : "+";
  });

  actualizarBotonCarrito();
}

/* --- Modal ------------------------------------------------------------- */

function renderPedido() {
  const lista = document.getElementById("pedidoItems");
  const comentario = document.getElementById("pedidoComentario");
  const cta = document.getElementById("pedidoCta");

  document.getElementById("pedidoTotal").textContent = currency.format(totalPrecio());

  if (carrito.size === 0) {
    lista.innerHTML = `
      <li class="pedido__vacio">
        <b>Tu pedido está vacío</b>
        <span>Agrega platos del menú con el botón +</span>
      </li>`;
    comentario.style.display = "none";
    cta.disabled = true;
    return;
  }

  comentario.style.display = "";
  cta.disabled = false;

  lista.innerHTML = Array.from(carrito.values()).map((item) => {
    const p = item.plato;
    const tags = MENU_DATA.observacionesRapidas.map((t) => `
      <button class="obs-tag${item.tags.has(t) ? " is-on" : ""}" type="button"
              data-id="${p.id}" data-tag="${t}">${t}</button>`).join("");

    return `
      <li class="pitem" data-id="${p.id}">
        <img class="pitem__img" src="${p.foto}" alt="${p.nombre}">
        <div class="pitem__body">
          <div class="pitem__head">
            <h3 class="pitem__nombre">${p.nombre}</h3>
            <span class="pitem__precio">${currency.format(p.precio * item.cantidad)}</span>
          </div>

          <div class="pitem__tags">${tags}</div>

          <input class="pitem__nota" type="text" maxlength="80"
                 data-id="${p.id}" value="${item.nota}"
                 placeholder="Otra indicación para este plato…">

          <div class="pitem__qty">
            <button class="qty-btn qty-btn--quitar" type="button"
                    data-id="${p.id}" data-delta="-1" aria-label="Quitar uno">−</button>
            <span class="qty-num">${item.cantidad}</span>
            <button class="qty-btn" type="button"
                    data-id="${p.id}" data-delta="1" aria-label="Agregar uno">+</button>
          </div>
        </div>
      </li>`;
  }).join("");
}

function setupCarrito() {
  const modal = document.getElementById("pedidoModal");
  const abrir = document.getElementById("cartBtn");
  const cerrar = document.getElementById("pedidoClose");
  const lista = document.getElementById("pedidoItems");

  // Agregar desde las tarjetas del menú
  document.getElementById("menuGrid").addEventListener("click", (e) => {
    const btn = e.target.closest(".card__add");
    if (!btn) return;
    agregarAlCarrito(Number(btn.dataset.id));
  });

  abrir.addEventListener("click", () => {
    renderPedido();
    modal.showModal();          // showModal da atrapado de foco y cierre con Esc
    document.body.style.overflow = "hidden";
  });

  const cerrarModal = () => {
    modal.close();
    document.body.style.overflow = "";
  };

  cerrar.addEventListener("click", cerrarModal);
  modal.addEventListener("close", () => { document.body.style.overflow = ""; });

  // Clic fuera del panel cierra
  modal.addEventListener("click", (e) => {
    if (e.target === modal) cerrarModal();
  });

  // Delegación dentro de la lista: cantidad, etiquetas y nota
  lista.addEventListener("click", (e) => {
    const qty = e.target.closest(".qty-btn");
    if (qty) { cambiarCantidad(Number(qty.dataset.id), Number(qty.dataset.delta)); return; }

    const tag = e.target.closest(".obs-tag");
    if (tag) {
      const item = carrito.get(Number(tag.dataset.id));
      if (!item) return;
      const t = tag.dataset.tag;
      item.tags.has(t) ? item.tags.delete(t) : item.tags.add(t);
      tag.classList.toggle("is-on");
    }
  });

  lista.addEventListener("input", (e) => {
    const nota = e.target.closest(".pitem__nota");
    if (!nota) return;
    const item = carrito.get(Number(nota.dataset.id));
    if (item) item.nota = nota.value;
  });

  // Contador del comentario general
  const textarea = document.getElementById("comentarioGeneral");
  const contador = document.getElementById("contadorComentario");
  textarea.addEventListener("input", () => {
    contador.textContent = `${textarea.value.length} / 200`;
  });

  // El QR real llega en Fase 1 (SPEC-002)
  document.getElementById("pedidoCta").addEventListener("click", () => {
    alert(
      "Fase 0: aquí se generará el QR del pedido.\n\n" +
      `${totalUnidades()} unidades · ${currency.format(totalPrecio())}\n\n` +
      "El mesero lo escaneará para confirmar (SPEC-002)."
    );
  });

  sincronizarCarrito();
}

/* ---------------------------------------------------------------------- */

document.addEventListener("DOMContentLoaded", () => {
  renderMenu();
  prepararEntrada();
  setupFilters();
  setupCarrito();
  setupHero();
  medirFiltros();
});

/** La barra de filtros es pegajosa: su altura define cuánto hay que
 *  descontar al saltar a un ancla para que no tape el destino. */
function medirFiltros() {
  const filtros = document.getElementById("filters");
  const aplicar = () => {
    document.documentElement.style.setProperty("--filters-h", `${filtros.offsetHeight}px`);
  };
  aplicar();
  window.addEventListener("resize", aplicar, { passive: true });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(aplicar);
}
