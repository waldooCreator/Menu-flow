<script setup>
/** Marco compartido y navegación del personal (SPEC-021). */
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { obtenerPerfil } from "../api/auth";
import { obtenerConfiguracionPublica } from "../api/configuracion";
import { aplicarTemaCliente } from "../lib/tema";
import { gruposVisibles } from "../lib/navegacion";
import BarraLateral from "./BarraLateral.vue";

defineProps({
  titulo: { type: String, required: true },
  ancho: { type: String, default: "max-w-3xl" },
});

const auth = useAuthStore();
const router = useRouter();
const nombre = ref("");
const barraPlegada = ref(localStorage.getItem("terra_nav_plegada") === "1");
const menuMovilAbierto = ref(false);

const grupos = computed(() => gruposVisibles({
  rol: auth.rol,
  roles: auth.roles,
  puede_cobrar: auth.puedeCobrar,
}));

const grupoPrincipal = computed(() => {
  if (auth.roles.includes("cocina") && !auth.roles.some((rol) => ["admin", "mesero", "cajero"].includes(rol))) return "cocina";
  if (auth.roles.includes("admin")) return "ajustes";
  if (auth.roles.includes("cajero") || auth.puedeCobrar) return "caja";
  return "servicio";
});

onMounted(async () => {
  try {
    const [configuracion, perfil] = await Promise.all([
      obtenerConfiguracionPublica(), obtenerPerfil(),
    ]);
    aplicarTemaCliente(configuracion);
    nombre.value = configuracion["nombre-restaurante"] || "";
    auth.guardarPerfil(perfil);
  } catch {
    // Los valores por defecto cubren una API temporalmente no disponible.
  }
});

function alternarBarra() {
  barraPlegada.value = !barraPlegada.value;
  localStorage.setItem("terra_nav_plegada", barraPlegada.value ? "1" : "0");
}

function salir() {
  auth.cerrarSesion();
  router.push({ name: "admin-login" });
}
</script>

<template>
  <div class="min-h-screen bg-lienzo font-sans text-tinta">
    <BarraLateral
      :grupos="grupos"
      :plegada="barraPlegada"
      :movil-abierta="menuMovilAbierto"
      :grupo-principal="grupoPrincipal"
      @alternar-plegada="alternarBarra"
      @cerrar-movil="menuMovilAbierto = false"
    />

    <header
      class="sticky top-0 z-40 border-b border-marca/15 bg-lienzo/95 backdrop-blur lg:ml-[72px]"
      :class="{ 'lg:ml-[280px]': !barraPlegada }"
    >
      <div class="mx-auto flex min-h-16 items-center justify-between gap-3 px-4 py-3 sm:px-5">
        <div class="flex min-w-0 items-center gap-2.5">
          <button
            @click="menuMovilAbierto = true"
            aria-label="Abrir menú de navegación"
            class="grid size-11 shrink-0 cursor-pointer place-items-center rounded-xl text-marca hover:bg-marca/6 focus-visible:ring-2 focus-visible:ring-marca lg:hidden"
          >☰</button>
          <span class="truncate font-display text-[18px] text-marca sm:text-[22px]">{{ nombre || "…" }}</span>
        </div>

        <div class="flex min-w-0 shrink-0 items-center gap-2.5">
          <slot name="acciones" />
          <span v-if="auth.usuario" class="hidden max-w-32 truncate text-[12px] font-semibold text-marca/60 uppercase sm:inline">
            {{ auth.usuario }}
          </span>
          <button
            @click="salir"
            class="min-h-11 cursor-pointer rounded-full border border-marca/15 px-3.5 text-[11px] font-semibold tracking-[0.06em] text-marca uppercase transition-colors hover:border-alerta hover:text-alerta focus-visible:ring-2 focus-visible:ring-marca"
          >Salir</button>
        </div>
      </div>
    </header>

    <main
      class="mx-auto min-w-0 px-5 py-8 lg:ml-[72px]"
      :class="[ancho, { 'lg:ml-[280px]': !barraPlegada }]"
    >
      <h1 class="mb-7 font-display text-4xl font-light text-marca">{{ titulo }}</h1>
      <slot />
    </main>
  </div>
</template>
