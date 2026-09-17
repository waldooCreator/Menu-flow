<script setup>
/**
 * Papel tapiz del menú: un mosaico del tema repetido detrás del contenido,
 * que se desplaza al hacer scroll para dar sensación de movimiento.
 *
 * El mosaico es una sola imagen construida SIN COSTURAS (lo que sobresale
 * por un borde reaparece en el opuesto), así se puede repetir infinitamente
 * sin junturas visibles.
 *
 * Reglas que se respetan aquí:
 * - **La legibilidad manda.** Opacidad baja y siempre por DEBAJO del
 *   contenido (`-z-10`): el menú es lo que el cliente vino a leer.
 * - **Pocas y grandes, no muchas y pequeñas.** La tesela mide 1400px con
 *   solo cuatro figuras, y se despliega a 900px (460px en móvil): salen
 *   ~6 figuras por pantalla, no ~115 como en la primera versión. Los dos
 *   números que se tocan si el cliente opina son el `bg-[length:…]`
 *   (cuántas se ven) y la opacidad (cuánto pesan).
 * - **`pointer-events-none`**: nunca debe bloquear un toque en un plato.
 * - **Configurable, no fijo** (SPEC-007): sale de `deco-patron`. Un
 *   restaurante que no lo llene simplemente no tiene papel tapiz.
 * - **`prefers-reduced-motion`**: se queda quieto, no desaparece.
 */
import { computed, onMounted, onUnmounted, ref } from "vue";

const props = defineProps({
  patron: { type: String, default: "" },
});

const desplazamiento = ref(0);
const sinMovimiento =
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const estilo = computed(() => ({
  backgroundImage: `url(${props.patron})`,
  // El desfase vertical es lo que "anima" el tapiz al bajar. Al repetirse
  // sin costuras, puede correrse indefinidamente sin mostrar bordes.
  backgroundPosition: `center ${sinMovimiento ? 0 : desplazamiento.value * 0.12}px`,
}));

let pendiente = false;
function alHacerScroll() {
  if (pendiente) return;
  pendiente = true;
  requestAnimationFrame(() => {
    desplazamiento.value = window.scrollY;
    pendiente = false;
  });
}

onMounted(() => {
  if (sinMovimiento) return;
  window.addEventListener("scroll", alHacerScroll, { passive: true });
  alHacerScroll();
});

onUnmounted(() => window.removeEventListener("scroll", alHacerScroll));
</script>

<template>
  <div
    v-if="patron"
    class="pointer-events-none absolute inset-0 -z-10 bg-[length:460px] bg-repeat opacity-[0.10] select-none sm:bg-[length:900px] sm:opacity-[0.12]"
    :style="estilo"
    aria-hidden="true"
  ></div>
</template>
