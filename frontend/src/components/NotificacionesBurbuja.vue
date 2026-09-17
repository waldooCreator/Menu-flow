<script setup>
/**
 * Centro de notificaciones del mesero (SPEC-006): burbuja con contador.
 * Consulta periódica (polling) — el transporte en tiempo real (Django
 * Channels) sigue pendiente, ver Preguntas Abiertas.
 */
import { ref, computed, onMounted, onUnmounted } from "vue";
import { listarNotificaciones, marcarNotificacionLeida, entregarPedido } from "../api/pedidos";

const notificaciones = ref([]);
const abierta = ref(false);
const entregando = ref(null);
let temporizador = null;

const noLeidas = computed(() => notificaciones.value.filter((n) => !n.leida).length);

const porPedido = computed(() => {
  const mapa = new Map();
  for (const n of notificaciones.value) {
    if (!mapa.has(n.pedido_id)) {
      mapa.set(n.pedido_id, { pedidoId: n.pedido_id, estado: n.estado_pedido, items: [] });
    }
    mapa.get(n.pedido_id).items.push(n);
  }
  return [...mapa.values()];
});

async function cargar() {
  try {
    notificaciones.value = await listarNotificaciones();
  } catch {
    // el interceptor de cliente.js ya cierra sesión si el token expiró
  }
}

async function alternar() {
  abierta.value = !abierta.value;
  if (!abierta.value) return;
  await cargar();
  // Al abrir se marcan como leídas las que se muestran: apaga el contador
  // aunque el mesero todavía no haya entregado.
  for (const n of notificaciones.value.filter((n) => !n.leida)) {
    marcarNotificacionLeida(n.id).catch(() => {});
  }
}

async function entregar(pedidoId) {
  entregando.value = pedidoId;
  try {
    await entregarPedido(pedidoId);
    await cargar();
  } finally {
    entregando.value = null;
  }
}

function alVolver() {
  if (!document.hidden) cargar();
}

onMounted(() => {
  cargar();
  temporizador = setInterval(cargar, 3000);
  // Al volver a esta pestaña se refresca de inmediato: el caso habitual es
  // que el mesero estaba en otra pantalla mientras cocina marcaba listo.
  document.addEventListener("visibilitychange", alVolver);
  window.addEventListener("focus", cargar);
});

onUnmounted(() => {
  clearInterval(temporizador);
  document.removeEventListener("visibilitychange", alVolver);
  window.removeEventListener("focus", cargar);
});
</script>

<template>
  <div class="relative">
    <button
      @click="alternar" :aria-expanded="abierta" aria-label="Notificaciones"
      class="relative grid size-11 cursor-pointer place-items-center rounded-full bg-marca text-lienzo transition-transform hover:scale-105"
    >
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8">
        <path d="M18 8a6 6 0 10-12 0c0 7-3 8-3 8h18s-3-1-3-8" stroke-linecap="round" stroke-linejoin="round" />
        <path d="M13.7 21a2 2 0 01-3.4 0" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span
        v-if="noLeidas > 0"
        class="absolute -top-1 -right-1 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-acento px-1 text-[11px] font-bold text-tinta tabular-nums"
      >+{{ noLeidas }}</span>
    </button>

    <!-- En teléfono el panel es una hoja fija a lo ancho (anclarlo al botón
         lo sacaba por el borde izquierdo); desde sm vuelve a ser un menú
         colgado de la campana. -->
    <div
      v-if="abierta"
      class="fixed inset-x-3 top-16 z-70 max-h-[70dvh] overflow-y-auto rounded-3xl border border-marca/15 bg-white p-4 shadow-xl sm:absolute sm:inset-x-auto sm:top-13 sm:right-0 sm:max-h-96 sm:w-80"
    >
      <h3 class="mb-3 text-[11px] font-bold tracking-[0.14em] text-marca/60 uppercase">Notificaciones</h3>

      <p v-if="porPedido.length === 0" class="py-4 text-center text-[13px] text-tinta/50">
        Nada pendiente por ahora.
      </p>

      <div
        v-for="grupo in porPedido" :key="grupo.pedidoId"
        class="border-t border-marca/10 py-3 first:border-t-0 first:pt-0"
      >
        <p class="mb-1 text-[13px] font-bold text-tinta">
          Pedido #{{ grupo.pedidoId }}
          <span class="font-medium text-tinta/50">· {{ grupo.estado }}</span>
        </p>
        <ul class="mb-2.5 text-[13px] text-tinta/70">
          <li v-for="it in grupo.items" :key="it.id" class="py-0.5">{{ it.mensaje }}</li>
        </ul>
        <button
          v-if="!['entregado', 'anulado'].includes(grupo.estado)"
          @click="entregar(grupo.pedidoId)"
          :disabled="entregando === grupo.pedidoId"
          class="w-full cursor-pointer rounded-full bg-marca py-2.5 text-xs font-bold tracking-[0.06em] text-lienzo uppercase transition-opacity hover:opacity-90 disabled:opacity-60"
        >{{ entregando === grupo.pedidoId ? "…" : "Finalizar pedido" }}</button>
      </div>
    </div>
  </div>
</template>
