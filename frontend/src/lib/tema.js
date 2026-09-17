/**
 * Aplica la paleta, tipografías e identidad del restaurante sobre :root.
 *
 * Van en :root a propósito, no en un componente: las variables de tema de
 * Tailwind (`@theme`) se declaran ahí, y una variable CSS resuelve su valor
 * en el elemento donde se declara — ponerlas más abajo en el árbol no las
 * alcanzaría.
 *
 * Se llama ANTES de pintar el contenido (ADR-006): así el visitante no ve la
 * paleta por defecto y luego un salto a la del restaurante.
 */

const MAPA = {
  "--c-bg": "color-bg",
  "--c-bg-alt": "color-bg-alt",
  "--c-ink": "color-ink",
  "--c-brand": "color-primario",
  "--c-brand-soft": "color-primario-suave",
  "--c-accent": "color-acento",
  "--f-sans": "fuente-cuerpo",
  "--f-display": "fuente-titulos",
};

// El último nombre aplicado — para componentes que lo necesitan fuera del
// flujo de props (texto del mensaje de WhatsApp, nombre del archivo del QR).
let nombreActual = "";
let localeActual = "es-CO";
let formateadorMoneda = new Intl.NumberFormat("es-CO", {
  style: "currency", currency: "COP", maximumFractionDigits: 0,
});

export function nombreRestaurante() {
  return nombreActual;
}

/** El formato regional del restaurante, para fechas y horas (SPEC-023). */
export function localeRestaurante() {
  return localeActual;
}

export function formatearMoneda(valor) {
  return formateadorMoneda.format(valor ?? 0);
}

export function aplicarTemaCliente(config) {
  const raiz = document.documentElement;
  for (const [variable, clave] of Object.entries(MAPA)) {
    const valor = config[clave];
    if (valor) raiz.style.setProperty(variable, valor);
  }

  // La pestaña también es parte de la marca: nada de "Terra" fijo (regla
  // del proyecto: ningún texto de negocio escrito a mano).
  if (config["nombre-restaurante"]) {
    nombreActual = config["nombre-restaurante"];
    document.title = nombreActual;
  }

  const locale = config.locale || "es-CO";
  localeActual = locale;
  const moneda = config.moneda || "COP";
  try {
    formateadorMoneda = new Intl.NumberFormat(locale, {
      style: "currency", currency: moneda, maximumFractionDigits: 0,
    });
  } catch {
    formateadorMoneda = new Intl.NumberFormat("es-CO", {
      style: "currency", currency: "COP", maximumFractionDigits: 0,
    });
  }

  cargarTipografias(config);
}

/**
 * Las tipografías son configurables, así que la hoja de Google Fonts no
 * puede estar fija en index.html — se inyecta según lo que tenga la base.
 *
 * Dos <link> por familia a propósito: la API css2 rechaza la petición
 * completa si se piden pesos que la familia no tiene (p.ej. Luckiest Guy
 * solo existe en 400). El primer link pide los pesos ricos; si esa familia
 * no los tiene, ese link falla solo y el segundo (sin pesos, regular) la
 * carga igual — el navegador sintetiza la negrita.
 */
function cargarTipografias(config) {
  const familias = [config["fuente-titulos"], config["fuente-cuerpo"]].filter(Boolean);
  if (familias.length === 0) return;

  document.querySelectorAll("[data-tipografia-restaurante]").forEach((n) => n.remove());

  for (const familia of familias) {
    const nombre = encodeURIComponent(familia).replace(/%20/g, "+");
    const urls = [
      `https://fonts.googleapis.com/css2?family=${nombre}:wght@300;400;500;600;700&display=swap`,
      `https://fonts.googleapis.com/css2?family=${nombre}&display=swap`,
    ];
    for (const href of urls) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.dataset.tipografiaRestaurante = "1";
      document.head.appendChild(link);
    }
  }
}
