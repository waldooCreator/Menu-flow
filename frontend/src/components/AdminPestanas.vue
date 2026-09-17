<script setup>
/**
 * Navegación interna del panel de administración (SPEC-007). Cada
 * sección con su ruta — así el navegador recuerda dónde
 * estabas y se puede enlazar directo a una sección.
 */
import { useRoute } from "vue-router";

const route = useRoute();

const PESTANAS = [
  { a: "admin-configuracion", texto: "Sitio" },
  { a: "admin-menu", texto: "Menú" },
  { a: "admin-mesas", texto: "Mesas" },
  { a: "admin-estaciones", texto: "Estaciones" },
  { a: "admin-usuarios", texto: "Usuarios" },
  { a: "admin-cobro", texto: "Cobro" },
  { a: "admin-turnos", texto: "Turnos" },
];
</script>

<template>
  <nav class="mb-6 flex flex-wrap gap-1.5">
    <RouterLink
      v-for="p in PESTANAS" :key="p.a"
      :to="{ name: p.a }"
      class="min-h-11 rounded-full px-4 py-2 text-[13px] font-semibold transition-colors"
      :class="route.name === p.a
        ? 'bg-panel-marca text-white'
        : 'border border-panel-borde bg-white text-panel-tinta/70 hover:border-panel-marca'"
    >{{ p.texto }}</RouterLink>
  </nav>
</template>
