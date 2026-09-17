<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

const props = defineProps({
  grupos: { type: Array, required: true },
  plegada: { type: Boolean, default: false },
  movilAbierta: { type: Boolean, default: false },
  grupoPrincipal: { type: String, default: "servicio" },
});
const emit = defineEmits(["alternar-plegada", "cerrar-movil"]);
const route = useRoute();
const grupoAbierto = ref(props.grupoPrincipal);
const cajon = ref(null);

const ICONOS = {
  qr: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM15 15h2v2h-2zM18 18h2v2h-2z",
  salon: "M4 5h16v14H4zM8 9h8M8 13h8M8 17h4",
  pedido: "M5 4h14v16H5zM8 8h8M8 12h8M8 16h5",
  cuenta: "M6 3h12v18H6zM9 7h6M9 11h6M9 15h4",
  turno: "M12 6v6l4 2M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0z",
  libro: "M5 4h14v16H5zM8 8h8M8 12h8M8 16h5",
  activos: "M4 18h16M6 15V9M12 15V5M18 15v-3",
  ventas: "M5 19V5h14v14zM8 15l2-3 2 2 4-5",
  reporte: "M5 19V5h14v14zM8 15v-3M12 15V8M16 15v-6",
  clientes: "M5 19a7 7 0 0 1 14 0M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  cocina: "M4 14h16M6 14V8h12v6M8 8V5h3v3M13 8V5h3v3M4 18h16",
  ajustes: "M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.3 1a8 8 0 0 0-1.8-1L14.5 3h-5l-.3 2.1a8 8 0 0 0-1.8 1l-2.3-1-2 3.4L5.1 11a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.3-1a8 8 0 0 0 1.8 1l.3 2.1h5l.3-2.1a8 8 0 0 0 1.8-1l2.3 1 2-3.4-2-1.5c.1-.3.1-.7.1-1z",
};

function alternarGrupo(id) {
  grupoAbierto.value = grupoAbierto.value === id ? "" : id;
  guardarGrupos();
}

function guardarGrupos() {
  localStorage.setItem("terra_nav_grupo", grupoAbierto.value);
}

function enfocarCajon() {
  nextTick(() => {
    const primero = cajon.value?.querySelector("a, button");
    primero?.focus();
  });
}

function controlarTeclado(evento) {
  if (!props.movilAbierta) return;
  if (evento.key === "Escape") {
    emit("cerrar-movil");
    return;
  }
  if (evento.key !== "Tab") return;
  const elementos = [...(cajon.value?.querySelectorAll("a, button") ?? [])]
    .filter((elemento) => !elemento.disabled);
  if (!elementos.length) return;
  const primero = elementos[0];
  const ultimo = elementos.at(-1);
  if (evento.shiftKey && document.activeElement === primero) {
    evento.preventDefault();
    ultimo.focus();
  } else if (!evento.shiftKey && document.activeElement === ultimo) {
    evento.preventDefault();
    primero.focus();
  }
}

watch(() => props.movilAbierta, (abierta) => {
  document.body.style.overflow = abierta ? "hidden" : "";
  if (abierta) enfocarCajon();
});

onMounted(() => {
  const guardado = localStorage.getItem("terra_nav_grupo");
  if (guardado && props.grupos.some((grupo) => grupo.id === guardado)) grupoAbierto.value = guardado;
  document.addEventListener("keydown", controlarTeclado);
});

onUnmounted(() => {
  document.body.style.overflow = "";
  document.removeEventListener("keydown", controlarTeclado);
});
</script>

<template>
  <aside
    class="fixed inset-y-0 left-0 z-50 hidden flex-col border-r border-marca/12 bg-lienzo transition-[width] duration-200 ease-out lg:flex"
    :class="plegada ? 'w-[72px]' : 'w-[280px]'"
    aria-label="Navegación del personal"
  >
    <div class="flex h-20 shrink-0 items-center justify-end border-b border-marca/10 px-3">
      <button
        @click="emit('alternar-plegada')"
        :aria-label="plegada ? 'Abrir barra lateral' : 'Plegar barra lateral'"
        class="grid size-11 cursor-pointer place-items-center rounded-xl text-marca hover:bg-marca/6 focus-visible:ring-2 focus-visible:ring-marca"
      >{{ plegada ? '»' : '«' }}</button>
    </div>
    <nav class="flex-1 overflow-y-auto px-2.5 py-4">
      <section v-for="grupo in grupos" :key="grupo.id" class="mb-3">
        <button
          v-if="!plegada"
          @click="alternarGrupo(grupo.id)"
          class="flex min-h-11 w-full items-center justify-between px-3 text-[10.5px] font-bold tracking-[0.12em] text-marca/55 uppercase focus-visible:ring-2 focus-visible:ring-marca"
          :aria-expanded="grupoAbierto === grupo.id"
        >
          {{ grupo.titulo }} <span>{{ grupoAbierto === grupo.id ? '−' : '+' }}</span>
        </button>
        <div v-show="plegada || grupoAbierto === grupo.id" class="space-y-0.5">
          <RouterLink
            v-for="destino in grupo.destinos" :key="destino.ruta"
            :to="{ name: destino.ruta }"
            @click="emit('cerrar-movil')"
            :title="plegada ? destino.texto : undefined"
            :aria-label="destino.texto"
            :aria-current="route.name === destino.ruta ? 'page' : undefined"
            class="group flex min-h-11 items-center gap-3 rounded-xl border-l-[3px] px-3 text-[14px] font-semibold text-tinta/75 transition-colors hover:bg-marca/6 focus-visible:ring-2 focus-visible:ring-marca"
            :class="route.name === destino.ruta ? 'border-marca bg-marca text-lienzo hover:bg-marca' : 'border-transparent'"
          >
            <svg class="size-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
              <path :d="ICONOS[destino.icono]" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span v-if="!plegada" class="truncate">{{ destino.texto }}</span>
          </RouterLink>
        </div>
      </section>
    </nav>
  </aside>

  <div v-if="movilAbierta" class="fixed inset-0 z-50 flex lg:hidden" @click.self="emit('cerrar-movil')">
    <aside ref="cajon" class="flex h-full w-[min(85vw,320px)] flex-col bg-lienzo shadow-2xl" aria-label="Navegación del personal">
      <div class="flex h-20 shrink-0 items-center justify-between border-b border-marca/10 px-4">
        <strong class="font-display text-2xl font-light text-marca">Menú</strong>
        <button @click="emit('cerrar-movil')" aria-label="Cerrar menú" class="grid size-11 cursor-pointer place-items-center rounded-xl text-2xl text-marca focus-visible:ring-2 focus-visible:ring-marca">×</button>
      </div>
      <nav class="flex-1 overflow-y-auto px-2.5 py-4">
        <section v-for="grupo in grupos" :key="grupo.id" class="mb-3">
          <button @click="alternarGrupo(grupo.id)" class="flex min-h-11 w-full items-center justify-between px-3 text-[10.5px] font-bold tracking-[0.12em] text-marca/55 uppercase focus-visible:ring-2 focus-visible:ring-marca" :aria-expanded="grupoAbierto === grupo.id">
            {{ grupo.titulo }} <span>{{ grupoAbierto === grupo.id ? '−' : '+' }}</span>
          </button>
          <div v-show="grupoAbierto === grupo.id" class="space-y-0.5">
            <RouterLink v-for="destino in grupo.destinos" :key="destino.ruta" :to="{ name: destino.ruta }" @click="emit('cerrar-movil')" :aria-current="route.name === destino.ruta ? 'page' : undefined" class="flex min-h-11 items-center gap-3 rounded-xl border-l-[3px] px-3 text-[14px] font-semibold text-tinta/75 focus-visible:ring-2 focus-visible:ring-marca" :class="route.name === destino.ruta ? 'border-marca bg-marca text-lienzo' : 'border-transparent hover:bg-marca/6'">
              <svg class="size-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path :d="ICONOS[destino.icono]" stroke-linecap="round" stroke-linejoin="round" /></svg>
              <span>{{ destino.texto }}</span>
            </RouterLink>
          </div>
        </section>
      </nav>
    </aside>
  </div>
</template>
