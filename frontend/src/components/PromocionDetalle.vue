<script setup>
/**
 * Lo que incluye una promoción, al tocarla en el menú (SPEC-023): cada
 * componente con su cantidad y su especificación.
 *
 * Mismo marco que el carrito (hoja desde abajo en teléfono, panel centrado
 * en pantallas grandes) para que no parezca otra aplicación.
 */
import { onMounted, onUnmounted, useTemplateRef } from "vue";
import { formatearMoneda } from "../lib/tema";
import { textoVigencia } from "../lib/promociones";

const props = defineProps({
  promo: { type: Object, required: true },
  config: { type: Object, default: () => ({}) },
  cantidad: { type: Number, default: 0 },
});
const emit = defineEmits(["cerrar", "agregar"]);

const botonCerrar = useTemplateRef("botonCerrar");

function alTeclear(evento) {
  if (evento.key === "Escape") emit("cerrar");
}

onMounted(() => {
  document.body.style.overflow = "hidden";
  document.addEventListener("keydown", alTeclear);
  botonCerrar.value?.focus();
});
onUnmounted(() => {
  document.body.style.overflow = "";
  document.removeEventListener("keydown", alTeclear);
});

const vigencia = textoVigencia(props.promo, props.config["texto-promo-hasta"] || "Válida hasta");
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/55 backdrop-blur-sm sm:items-center"
    @click.self="emit('cerrar')"
  >
    <div
      role="dialog" aria-modal="true" :aria-label="promo.nombre"
      class="flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-t-[26px] bg-lienzo sm:max-w-[560px] sm:rounded-[26px]"
    >
      <div class="relative shrink-0">
        <img
          v-if="promo.foto" :src="promo.foto" :alt="promo.nombre"
          class="aspect-[16/10] w-full object-cover"
          :class="{ 'grayscale-[0.75] opacity-75': !promo.disponible }"
        />
        <div v-else class="grid aspect-[16/10] w-full place-items-center bg-marca font-display text-6xl font-light text-lienzo">
          {{ promo.nombre.charAt(0) }}
        </div>
        <button
          ref="botonCerrar" @click="emit('cerrar')" aria-label="Cerrar"
          class="absolute top-3 right-3 grid size-11 cursor-pointer place-items-center rounded-full bg-lienzo text-marca shadow-sm"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none" />
          </svg>
        </button>
        <span
          v-if="vigencia"
          class="absolute bottom-3 left-3 rounded-full bg-acento px-3.5 py-1.5 text-[11px] font-semibold tracking-[0.08em] text-tinta uppercase"
        >{{ vigencia }}</span>
      </div>

      <div class="flex-1 overflow-y-auto overscroll-contain px-5 pt-5 pb-5 sm:px-7">
        <div class="flex items-start justify-between gap-4">
          <h2 class="font-display text-[30px] leading-none font-light text-marca sm:text-[36px]">{{ promo.nombre }}</h2>
          <span class="shrink-0 pt-1 text-lg font-semibold whitespace-nowrap text-marca">
            {{ formatearMoneda(promo.precio) }}
          </span>
        </div>
        <p v-if="promo.descripcion" class="mt-2.5 text-[15px] leading-snug opacity-80">{{ promo.descripcion }}</p>

        <h3 class="mt-6 mb-2 text-[11px] font-semibold tracking-[0.16em] text-marca/60 uppercase">
          {{ config["texto-promo-incluye"] || "Incluye" }}
        </h3>
        <ul class="divide-y divide-marca/10 border-y border-marca/10">
          <li v-for="c in promo.componentes" :key="c.id" class="flex gap-3.5 py-3.5">
            <span class="grid size-9 shrink-0 place-items-center rounded-full bg-marca-suave text-[14px] font-bold text-marca">
              {{ c.cantidad }}
            </span>
            <div class="min-w-0">
              <p class="text-[15px] leading-tight font-medium tracking-[0.02em] uppercase">{{ c.nombre }}</p>
              <p v-if="c.especificacion" class="mt-1 text-[13.5px] leading-snug opacity-75">{{ c.especificacion }}</p>
            </div>
          </li>
        </ul>

        <p v-if="promo.alergenos" class="mt-3 text-xs text-marca/70">{{ promo.alergenos }}</p>
      </div>

      <footer class="shrink-0 border-t border-marca/15 px-5 py-4 sm:px-7">
        <button
          v-if="promo.disponible"
          @click="emit('agregar', promo)"
          class="min-h-13 w-full cursor-pointer rounded-full bg-marca text-[13px] font-medium tracking-[0.10em] text-lienzo uppercase transition-transform active:scale-[0.98]"
        >
          Agregar al pedido<template v-if="cantidad"> · {{ cantidad }} en el pedido</template>
        </button>
        <p v-else class="rounded-full bg-marca-suave py-3.5 text-center text-[12px] font-semibold tracking-[0.12em] text-marca uppercase">
          {{ config["texto-plato-agotado"] || "Agotado hoy" }}
        </p>
      </footer>
    </div>
  </div>
</template>
