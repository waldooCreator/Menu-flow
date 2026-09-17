<script setup>
/**
 * Mini-mapa real de la sede, en "Encuéntranos".
 *
 * Antes había aquí un recuadro con una cuadrícula dibujada y un punto —
 * decoración, no un mapa. El cliente pidió que fuera funcional.
 *
 * Decisiones:
 * - **OpenStreetMap, no Google Maps.** El `embed.html` de OSM no pide llave
 *   de API, no cobra por vistas y no exige tarjeta. Incrustar Google Maps
 *   obligaría a gestionar una llave por restaurante — justo lo contrario de
 *   un sistema que se despliega repetido (SPEC-007).
 * - **Para llegar sí se abre Google Maps / la app del teléfono**, que es lo
 *   que la gente usa para navegar. Ver el punto y trazar la ruta son cosas
 *   distintas.
 * - **El mapa nace sin interacción** (`pointer-events-none`). Un iframe de
 *   mapa se traga la rueda del ratón y el usuario que baja por la página
 *   queda atrapado haciendo zoom. Se activa con un clic — patrón habitual.
 * - **Coordenadas configurables** (SPEC-007): nada de un punto fijo en el
 *   código. Sin `mapa-latitud`/`mapa-longitud` el componente no se dibuja.
 */
import { computed, ref } from "vue";

const props = defineProps({
  latitud: { type: [String, Number], default: "" },
  longitud: { type: [String, Number], default: "" },
  etiqueta: { type: String, default: "" },
});

const activo = ref(false);

const punto = computed(() => {
  const lat = Number(props.latitud);
  const lon = Number(props.longitud);
  // Se valida el rango, no solo que sea número: un `0,0` por un parámetro a
  // medio llenar apuntaría al Golfo de Guinea sin avisar.
  const valido =
    Number.isFinite(lat) && Number.isFinite(lon) &&
    Math.abs(lat) <= 90 && Math.abs(lon) <= 180 && (lat !== 0 || lon !== 0);
  return valido ? { lat, lon } : null;
});

// Encuadre: ~350 m alrededor del punto. Suficiente para reconocer la manzana
// sin que el local se pierda en el barrio.
const RADIO = 0.0035;

const urlMapa = computed(() => {
  if (!punto.value) return "";
  const { lat, lon } = punto.value;
  const caja = [lon - RADIO, lat - RADIO, lon + RADIO, lat + RADIO].join(",");
  return `https://www.openstreetmap.org/export/embed.html?bbox=${encodeURIComponent(caja)}&layer=mapnik&marker=${lat}%2C${lon}`;
});

// `dir/?api=1` abre la app nativa de mapas en el teléfono y el navegador en
// escritorio, con la ruta ya trazada desde donde esté el cliente.
const urlComoLlegar = computed(() =>
  punto.value
    ? `https://www.google.com/maps/dir/?api=1&destination=${punto.value.lat},${punto.value.lon}`
    : ""
);
</script>

<template>
  <div v-if="punto">
    <div
      class="relative aspect-square max-w-64 overflow-hidden rounded-foto bg-lienzo/5"
      @click="activo = true"
    >
      <iframe
        :src="urlMapa"
        :title="`Mapa de ${etiqueta || 'la sede'}`"
        class="h-full w-full border-0"
        :class="activo ? '' : 'pointer-events-none'"
        loading="lazy"
        referrerpolicy="no-referrer-when-downgrade"
      ></iframe>

      <!-- Invitación a activarlo; desaparece en cuanto el mapa es interactivo -->
      <button
        v-if="!activo"
        type="button"
        class="absolute inset-x-0 bottom-0 cursor-pointer bg-tinta/55 py-2 text-[11px] font-semibold tracking-[0.12em] text-lienzo uppercase backdrop-blur-sm"
      >
        Tocar para explorar
      </button>
    </div>

    <a
      :href="urlComoLlegar"
      target="_blank"
      rel="noopener noreferrer"
      class="mt-3 inline-flex min-h-11 max-w-64 items-center gap-2 rounded-full bg-acento px-4 py-2.5 text-[11px] font-semibold tracking-[0.12em] text-tinta uppercase transition hover:opacity-85"
    >
      <svg viewBox="0 0 24 24" class="size-4" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M12 21s7-5.4 7-11a7 7 0 1 0-14 0c0 5.6 7 11 7 11Z" />
        <circle cx="12" cy="10" r="2.5" />
      </svg>
      Cómo llegar
    </a>
  </div>
</template>
