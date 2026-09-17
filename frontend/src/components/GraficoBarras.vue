<script setup>
/**
 * Un gráfico de Chart.js envuelto para este proyecto (SPEC-018).
 *
 * Existe para que las pantallas de reportes no repitan la misma configuración,
 * y sobre todo para que **los colores salgan del tema del restaurante**: la
 * misma instalación en otro restaurante debe verse con SUS colores, que es la
 * regla de parametrización del proyecto. Se leen de las variables CSS en
 * tiempo de ejecución, no se escriben aquí.
 *
 * El gráfico se **reconfigura según el ancho disponible**, no solo se encoge.
 * En un teléfono no caben 24 etiquetas de hora ni cifras de siete dígitos en
 * el eje: se muestran menos marcas y los montos se abrevian. Un eje ilegible
 * no informa nada.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Chart from "chart.js/auto";
import { formatearMoneda } from "../lib/tema";

const props = defineProps({
  tipo: { type: String, default: "bar" },       // bar | line
  horizontal: { type: Boolean, default: false },
  etiquetas: { type: Array, required: true },
  valores: { type: Array, required: true },
  /** Cómo formatear el valor: "moneda" o "numero". */
  formato: { type: String, default: "moneda" },
  alto: { type: Number, default: 260 },
});

const contenedor = ref(null);
const lienzo = ref(null);
const angosto = ref(false);
let grafico = null;
let observador = null;

const hayDatos = computed(() => props.valores.some((v) => v > 0));

/** Lee un color del tema; si aún no resolvió, cae a un gris neutro. */
function color(nombre, alfa = 1) {
  const valor = getComputedStyle(document.documentElement)
    .getPropertyValue(nombre).trim();
  if (!valor) return `rgba(120,120,120,${alfa})`;
  if (alfa === 1) return valor;
  return `color-mix(in srgb, ${valor} ${Math.round(alfa * 100)}%, transparent)`;
}

/** El valor completo, para la etiqueta flotante. */
function formatoLargo(v) {
  return props.formato === "moneda" ? formatearMoneda(v) : v.toLocaleString("es-CO");
}

/**
 * El valor abreviado, para los ejes. "$ 1.500.000" no cabe en un teléfono y
 * obliga a rotar el texto en diagonal, que es peor que abreviarlo.
 */
function formatoEje(v) {
  if (props.formato !== "moneda") return v.toLocaleString("es-CO");
  const n = Number(v);
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1).replace(".0", "")}M`;
  if (Math.abs(n) >= 1_000) return `$${Math.round(n / 1_000)}k`;
  return `$${n}`;
}

/** Recorta un nombre largo para que quepa como etiqueta de categoría. */
function recortar(texto, tope) {
  const t = String(texto);
  return t.length > tope ? `${t.slice(0, tope - 1)}…` : t;
}

function construir() {
  if (grafico) grafico.destroy();
  if (!lienzo.value || !hayDatos.value) return;

  const estrecho = angosto.value;
  const tinta = color("--c-ink");
  const marca = color("--c-brand");
  const esLinea = props.tipo === "line";

  // Cuántas marcas caben en el eje de categorías sin encimarse.
  const topeMarcas = estrecho ? 6 : 12;

  const ejeCategorias = {
    grid: { display: false },
    border: { display: false },
    ticks: {
      color: color("--c-ink", 0.55),
      font: { size: estrecho ? 10 : 11 },
      // Sin rotación: el texto en diagonal es lo que hacía ilegible el eje.
      maxRotation: 0,
      minRotation: 0,
      autoSkip: true,
      maxTicksLimit: props.horizontal ? undefined : topeMarcas,
      callback(valor, indice) {
        const texto = this.getLabelForValue(props.horizontal ? indice : valor);
        return recortar(texto, estrecho ? 10 : 14);
      },
    },
  };

  const ejeValores = {
    grid: { color: color("--c-ink", 0.06) },
    border: { display: false },
    beginAtZero: true,
    ticks: {
      color: color("--c-ink", 0.55),
      font: { size: estrecho ? 10 : 11 },
      maxRotation: 0,
      maxTicksLimit: estrecho ? 4 : 6,
      callback: (v) => formatoEje(v),
    },
  };

  grafico = new Chart(lienzo.value, {
    type: props.tipo,
    data: {
      labels: props.etiquetas,
      datasets: [{
        data: props.valores,
        backgroundColor: esLinea ? color("--c-brand", 0.12) : color("--c-brand", 0.85),
        borderColor: marca,
        borderWidth: esLinea ? 2.5 : 0,
        borderRadius: esLinea ? 0 : 6,
        fill: esLinea,
        tension: 0.35,
        pointRadius: esLinea ? (estrecho ? 2 : 3) : 0,
        pointHoverRadius: 5,
        pointBackgroundColor: marca,
        // Barras más delgadas en pantalla angosta: 24 barras gruesas no caben.
        maxBarThickness: estrecho ? 22 : 40,
      }],
    },
    options: {
      indexAxis: props.horizontal ? "y" : "x",
      responsive: true,
      maintainAspectRatio: false,
      // El dedo no apunta tan fino como el ratón: se acepta el toque cercano.
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: tinta,
          padding: 10,
          titleFont: { size: 12 },
          bodyFont: { size: 13 },
          displayColors: false,
          callbacks: {
            // El título del tooltip trae el nombre COMPLETO, aunque el eje lo
            // haya recortado: ahí es donde se consulta el dato exacto.
            title: (items) => props.etiquetas[items[0].dataIndex],
            label: (ctx) => formatoLargo(ctx.parsed[props.horizontal ? "x" : "y"]),
          },
        },
      },
      scales: props.horizontal
        ? { x: ejeValores, y: ejeCategorias }
        : { x: ejeCategorias, y: ejeValores },
    },
  });
}

onMounted(() => {
  // Se mide el CONTENEDOR, no la ventana: el mismo gráfico puede estar en una
  // columna angosta dentro de una pantalla ancha.
  observador = new ResizeObserver(([entrada]) => {
    const nuevo = entrada.contentRect.width < 420;
    if (nuevo !== angosto.value) {
      angosto.value = nuevo;
      construir();
    }
  });
  if (contenedor.value) {
    angosto.value = contenedor.value.clientWidth < 420;
    observador.observe(contenedor.value);
  }
  construir();
});

watch(() => [props.etiquetas, props.valores], construir, { deep: true });

onBeforeUnmount(() => {
  observador?.disconnect();
  grafico?.destroy();
});
</script>

<template>
  <div ref="contenedor" :style="{ height: `${alto}px` }" class="relative w-full min-w-0">
    <p
      v-if="!hayDatos"
      class="absolute inset-0 grid place-items-center text-center text-[13px] text-tinta/40"
    >Sin datos en este rango</p>
    <!-- `!max-w-full`: Chart.js escribe width en linea (300px por defecto) y
         sin esto el lienzo empuja la seccion mas alla del contenedor (SPEC-022 A4) -->
    <canvas v-show="hayDatos" ref="lienzo" class="!max-w-full"></canvas>
  </div>
</template>
