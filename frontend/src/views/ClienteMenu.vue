<script setup>
/**
 * Página del cliente — port del diseño de Fase 0 (`/prototipo`) a Vue con
 * Tailwind, consumiendo la API real.
 *
 * Estructura y reglas: [[Modelo de Pagina del Cliente]] y [[Sistema de Diseno]].
 * Hero a pantalla completa con parallax de recorrido largo, filtros pegajosos
 * con scroll-spy, menú en rejilla (lista en móvil), y "Encuéntranos" al final.
 */

import { ref, onMounted, onUnmounted, computed, nextTick, useTemplateRef } from "vue";
import { useRoute } from "vue-router";
import { obtenerConfiguracionPublica } from "../api/configuracion";
import { listarCategorias, listarPlatos, listarObservacionesRapidas } from "../api/menu";
import { validarMesa } from "../api/pedidos";
import { useCarritoStore } from "../stores/carrito";
import { aplicarTemaCliente, formatearMoneda } from "../lib/tema";
import { useHeroParallax } from "../lib/useHeroParallax";
import { prepararEntradaLateral } from "../lib/useEntradaLateral";
import CarritoPanel from "../components/CarritoPanel.vue";
import DecoracionesFondo from "../components/DecoracionesFondo.vue";
import MapaUbicacion from "../components/MapaUbicacion.vue";
import PromocionDetalle from "../components/PromocionDetalle.vue";
import { esPromocion, resumenComponentes, textoVigencia } from "../lib/promociones";

const route = useRoute();
const carrito = useCarritoStore();

const config = ref({});
const categorias = ref([]);
const platos = ref([]);
const observacionesRapidas = ref([]);
const cargando = ref(true);
const error = ref(null);
const carritoAbierto = ref(false);
// Clave de la sección visible: "promociones" o el id de la categoría como
// texto — así las dos caben en el mismo scroll-spy.
const categoriaActiva = ref(null);
const promoAbierta = ref(null);

const rejilla = useTemplateRef("rejilla");
const barraFiltros = useTemplateRef("barraFiltros");
const { contenedor, fondo, contenido, flechaOculta, fueraDelHero } = useHeroParallax();
let temporizadorDisponibilidad = null;

function aplicarDisponibilidad(nuevos) {
  const porId = new Map(nuevos.map((plato) => [plato.id, plato]));
  for (const plato of platos.value) {
    const actualizado = porId.get(plato.id);
    if (actualizado) {
      plato.disponible = actualizado.disponible;
      plato.estado_promocion = actualizado.estado_promocion;
    } else if (esPromocion(plato)) {
      // La promo dejó de estar vigente (SPEC-023). Se marca no disponible
      // ANTES de sacarla del menú: si ya estaba en el carrito, es el mismo
      // objeto, y el carrito la muestra como agotada en vez de dejar que el
      // pedido falle al generar el QR.
      plato.disponible = false;
    }
  }
  // Las promos que salieron desaparecen, y las que empezaron a valer mientras
  // el cliente miraba el menú aparecen.
  const presentes = new Set(platos.value.map((p) => p.id));
  platos.value = [
    ...platos.value.filter((p) => !esPromocion(p) || porId.has(p.id)),
    ...nuevos.filter((p) => esPromocion(p) && !presentes.has(p.id)),
  ];
}

async function refrescarDisponibilidad() {
  try {
    aplicarDisponibilidad(await listarPlatos());
  } catch {
    // El menú que ya está visible sigue siendo usable si una consulta falla.
  }
}

function alVolverAlMenu() {
  if (document.visibilityState === "visible") refrescarDisponibilidad();
}

const moneda = { format: formatearMoneda };

// SPEC-023: las promociones van de primera, y solo si hay alguna.
const promociones = computed(() => platos.value.filter(esPromocion));
const tituloPromociones = computed(() => config.value["titulo-promociones"] || "Promociones");
const prefijoVigencia = computed(() => config.value["texto-promo-hasta"] || "Válida hasta");

function agregarPromo(promo) {
  carrito.agregar(promo);
  promoAbierta.value = null;
}

const platosPorCategoria = computed(() => {
  const mapa = new Map(categorias.value.map((c) => [c.id, []]));
  for (const p of platos.value) {
    if (mapa.has(p.categoria_id)) mapa.get(p.categoria_id).push(p);
  }
  return mapa;
});

// Papel tapiz del tema (SPEC-007): si el restaurante no lo configura,
// el menú simplemente queda liso.
const patronDeco = computed(() => config.value["deco-patron"] || "");

const fondoHero = computed(() => {
  const url = config.value["hero-imagen-fondo"];
  return url ? { backgroundImage: `url(${url})` } : {};
});

function irACategoria(clave) {
  document.getElementById(`cat-${clave}`)?.scrollIntoView({ behavior: "smooth" });
}

/** Scroll-spy: resalta solo el chip de la categoría que se está viendo. */
function activarScrollSpy() {
  const titulos = document.querySelectorAll("[data-categoria]");
  const spy = new IntersectionObserver(
    (entradas) => {
      entradas.forEach((en) => {
        if (en.isIntersecting) categoriaActiva.value = en.target.dataset.categoria;
      });
    },
    { rootMargin: "-40% 0px -55% 0px", threshold: 0 }
  );
  titulos.forEach((t) => spy.observe(t));
}

onMounted(async () => {
  try {
    const [cfg, cats, pls, obs] = await Promise.all([
      obtenerConfiguracionPublica(), listarCategorias(), listarPlatos(), listarObservacionesRapidas(),
    ]);

    // El tema se aplica ANTES de pintar el menú: evita el salto de paleta
    // por defecto que advertía ADR-006.
    aplicarTemaCliente(cfg);

    config.value = cfg;
    categorias.value = cats;
    platos.value = pls;
    observacionesRapidas.value = obs;
    if (pls.some(esPromocion)) categoriaActiva.value = "promociones";
    else if (cats.length) categoriaActiva.value = String(cats[0].id);

    // Entrada por QR de mesa (SPEC-001): si el código no existe, se sigue en
    // modo sin mesa — no se le muestra un error crudo al cliente.
    const codigoMesa = route.params.codigo;
    if (codigoMesa) {
      const mesa = await validarMesa(codigoMesa);
      if (mesa.encontrada) carrito.fijarMesa(mesa.codigo, mesa.nombre);
    }

    cargando.value = false;
    await nextTick();

    if (rejilla.value) {
      prepararEntradaLateral(rejilla.value, [...rejilla.value.children]);
    }
    if (barraFiltros.value) {
      prepararEntradaLateral(barraFiltros.value, [...barraFiltros.value.children], { escalon: 70 });
    }
    activarScrollSpy();
    temporizadorDisponibilidad = setInterval(refrescarDisponibilidad, 60000);
    document.addEventListener("visibilitychange", alVolverAlMenu);
  } catch (e) {
    error.value = `No se pudo cargar el menú. ¿Está corriendo la API en ${import.meta.env.VITE_API_URL}?`;
    cargando.value = false;
    console.error(e);
  }
});

onUnmounted(() => {
  clearInterval(temporizadorDisponibilidad);
  document.removeEventListener("visibilitychange", alVolverAlMenu);
});
</script>

<template>
  <!-- `isolate` acota el papel tapiz (-z-10) a esta caja: sin él se iría
       detrás del fondo del documento y no se vería. -->
  <div class="relative isolate min-h-screen overflow-x-clip bg-lienzo text-tinta font-sans">
    <!-- Papel tapiz sobre TODO el fondo beige de la página. El hero y la
         sección "Encuéntranos" tienen fondo propio opaco, así que lo tapan
         en sus tramos — el tapiz solo asoma donde el fondo es beige. -->
    <DecoracionesFondo :patron="patronDeco" />

    <!-- ===== Barra superior ===== -->
    <header
      class="fixed inset-x-0 top-0 z-50 flex h-[72px] items-center border-b transition-colors duration-500"
      :class="fueraDelHero
        ? 'border-marca/15 bg-lienzo'
        : 'border-transparent bg-transparent'"
    >
      <div class="mx-auto flex w-full max-w-[1185px] items-center justify-between px-6">
        <span
          class="font-display text-2xl transition-colors duration-500"
          :class="fueraDelHero ? 'text-marca' : 'text-white'"
        >{{ config["nombre-restaurante"] || "…" }}</span>

        <a
          href="#encuentranos"
          class="inline-flex min-h-11 items-center rounded-full bg-acento px-5 py-3 text-[11px] font-semibold tracking-[0.12em] text-tinta uppercase transition-transform hover:-translate-y-px sm:text-[13px]"
        >{{ config["etiqueta-encuentranos"] || "Encuéntranos" }}</a>
      </div>
    </header>

    <!-- ===== Hero: contenedor alto que da el recorrido del parallax ===== -->
    <div ref="contenedor" class="relative h-[200vh] bg-[#10241B]">
      <section class="hero-fijo flex items-center justify-center overflow-hidden">
        <div
          ref="fondo"
          class="absolute inset-x-0 -top-[8%] h-[118%] bg-cover bg-center"
          :style="fondoHero"
        ></div>
        <div class="absolute inset-0 bg-gradient-to-b from-black/55 via-black/25 to-black/75"></div>

        <div ref="contenido" class="relative z-10 max-w-3xl px-6 text-center text-white">
          <p
            v-if="carrito.mesaNombre"
            class="mb-6 inline-block rounded-full bg-acento px-4 py-2 text-[11px] font-semibold tracking-[0.18em] text-tinta uppercase"
          >{{ carrito.mesaNombre }}</p>

          <h1 class="font-display text-[clamp(64px,12vw,132px)] leading-[0.92] font-light tracking-tight">
            {{ config["hero-titulo"] || config["nombre-restaurante"] || "" }}
          </h1>

          <p class="mx-auto mt-6 max-w-md text-lg leading-relaxed text-white/90">
            {{ config["hero-subtitulo"] }}
          </p>

          <a
            href="#menu"
            class="mt-10 inline-flex items-center gap-2.5 rounded-full bg-lienzo px-8 py-4 text-sm font-medium tracking-[0.10em] text-marca uppercase transition-transform hover:-translate-y-0.5"
          >
            {{ config["hero-texto-boton"] || "Ver el menú" }}
            <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" class="rotate-90">
              <path d="M12 5v14M12 19l-6-6M12 19l6-6" stroke="currentColor" stroke-width="2.2"
                    stroke-linecap="round" stroke-linejoin="round" fill="none" />
            </svg>
          </a>
        </div>

        <!-- Señal de que hay más contenido abajo -->
        <div
          class="absolute bottom-8 left-1/2 z-10 -translate-x-1/2 text-white/80 transition-opacity duration-500"
          :class="flechaOculta ? 'opacity-0' : 'opacity-100'"
          aria-hidden="true"
        >
          <svg viewBox="0 0 24 24" width="26" height="26" class="flecha-scroll">
            <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="1.6"
                  stroke-linecap="round" stroke-linejoin="round" fill="none" />
          </svg>
        </div>
      </section>
    </div>

    <!-- ===== Menú ===== -->
    <main id="menu" class="scroll-mt-[72px]">
      <p v-if="cargando" class="py-16 text-center opacity-60">Cargando menú…</p>
      <p v-else-if="error" class="py-16 text-center text-alerta">{{ error }}</p>

      <template v-else>
        <!-- Filtros pegajosos -->
        <div class="sticky top-[72px] z-30 border-b border-marca/15 bg-lienzo">
          <div
            ref="barraFiltros"
            class="mx-auto flex max-w-[1185px] gap-2 overflow-x-auto px-6 py-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
            <!-- Primer chip, con el acento del tema: señala que hay promos
                 aunque la sección todavía no esté en pantalla. -->
            <button
              v-if="promociones.length"
              @click="irACategoria('promociones')"
              class="shrink-0 cursor-pointer rounded-full border px-5 py-3 text-[13px] font-semibold tracking-[0.08em] uppercase transition-colors"
              :class="categoriaActiva === 'promociones'
                ? 'border-marca bg-marca text-lienzo'
                : 'border-acento bg-acento text-tinta hover:border-marca'"
            >★ {{ tituloPromociones }}</button>
            <button
              v-for="cat in categorias"
              :key="cat.id"
              @click="irACategoria(cat.id)"
              class="shrink-0 cursor-pointer rounded-full border px-5 py-3 text-[13px] font-medium tracking-[0.08em] uppercase transition-colors"
              :class="categoriaActiva === String(cat.id)
                ? 'border-marca bg-marca text-lienzo'
                : 'border-marca/15 text-marca hover:border-marca'"
            >{{ cat.nombre }}</button>
          </div>
        </div>

        <section class="relative mx-auto max-w-[1185px] overflow-x-clip px-6 pt-14 pb-32">
          <div ref="rejilla" class="grid grid-cols-1 gap-x-6 gap-y-0 md:grid-cols-2 md:gap-y-10 lg:grid-cols-3">
            <!-- ===== Promociones (SPEC-023, revisado 2026-09-16) =====
                 Mismo fondo, mismo título y misma tarjeta que un plato: el autor
                 descartó la franja de color. Las distingue la insignia "Promo" y
                 un halo de acento que respira despacio alrededor de la foto. -->
            <template v-if="promociones.length">
              <h2
                id="cat-promociones" data-categoria="promociones"
                class="col-span-full scroll-mt-[162px] border-t border-marca/15 pt-7 font-display text-[clamp(38px,5vw,58px)] leading-none font-light text-marca first:border-t-0 first:pt-0 md:mt-12"
              >{{ tituloPromociones }}</h2>

              <article
                v-for="p in promociones" :key="p.id"
                class="grid grid-cols-[1fr_112px] gap-4 border-b border-marca/15 py-5 md:flex md:flex-col md:border-b-0 md:py-0"
                :class="{ 'opacity-70': !p.disponible }"
              >
                <figure
                  class="relative order-2 aspect-square w-28 rounded-[14px] bg-lienzo-alt md:order-none md:mb-6 md:w-full md:rounded-foto"
                  :class="{ 'promo-halo': p.disponible }"
                >
                  <button
                    @click="promoAbierta = p"
                    :aria-label="`Ver qué incluye ${p.nombre}`"
                    class="block h-full w-full cursor-pointer overflow-hidden rounded-[inherit]"
                  >
                    <img
                      v-if="p.foto" :src="p.foto" :alt="p.nombre" loading="lazy"
                      class="h-full w-full object-cover"
                      :class="{ 'grayscale-[0.75] opacity-75': !p.disponible }"
                    />
                    <span v-else class="grid h-full w-full place-items-center bg-marca-suave font-display text-5xl font-light text-marca">
                      {{ p.nombre.charAt(0) }}
                    </span>
                  </button>

                  <span
                    class="pointer-events-none absolute top-1.5 left-1.5 rounded-full bg-acento px-2 py-1 text-[9px] font-bold tracking-[0.12em] text-tinta uppercase md:top-3.5 md:left-3.5 md:px-3 md:py-1.5 md:text-[10px]"
                  >★ {{ config["texto-insignia-promo"] || "Promo" }}</span>

                  <div v-if="!p.disponible" class="pointer-events-none absolute inset-0 grid place-items-center rounded-[inherit] bg-lienzo/75">
                    <span class="rounded-full bg-marca px-3 py-1.5 text-[9px] font-semibold tracking-[0.14em] text-lienzo uppercase md:px-5 md:py-2.5 md:text-[11px]">
                      {{ config["texto-plato-agotado"] || "Agotado hoy" }}
                    </span>
                  </div>

                  <button
                    v-if="p.disponible"
                    @click="carrito.agregar(p)"
                    :aria-label="`Agregar ${p.nombre} al pedido`"
                    class="absolute right-1.5 bottom-1.5 grid size-11 cursor-pointer place-items-center rounded-full text-[15px] font-bold transition-transform active:scale-95 md:right-2.5 md:bottom-2.5 md:hover:scale-110"
                    :class="carrito.cantidadDe(p.id) ? 'bg-marca text-lienzo' : 'bg-acento text-tinta'"
                  >{{ carrito.cantidadDe(p.id) || "+" }}</button>
                </figure>

                <div class="order-1 min-w-0 md:order-none">
                  <div class="flex items-start justify-between gap-3.5">
                    <h3 class="text-base leading-tight font-medium tracking-[0.03em] uppercase md:text-[22px]">
                      {{ p.nombre }}
                    </h3>
                    <span class="shrink-0 pt-0.5 text-[15px] font-medium whitespace-nowrap text-marca md:text-lg">
                      {{ moneda.format(p.precio) }}
                    </span>
                  </div>

                  <!-- Lo que incluye va en lugar de la descripción: es lo que decide la compra -->
                  <p class="mt-1.5 text-[13.5px] leading-snug opacity-80 md:mt-2.5 md:text-base">
                    {{ resumenComponentes(p) }}
                  </p>
                  <p v-if="p.disponible && textoVigencia(p, prefijoVigencia)" class="mt-1.5 text-xs font-semibold text-marca/75 md:mt-2">
                    {{ textoVigencia(p, prefijoVigencia) }}
                  </p>

                  <button
                    @click="promoAbierta = p"
                    class="-ml-1 mt-1 inline-flex min-h-11 cursor-pointer items-center px-1 text-[12px] font-semibold tracking-[0.08em] text-marca uppercase underline decoration-acento decoration-2 underline-offset-4"
                  >{{ config["texto-ver-promo"] || "Ver qué incluye" }}</button>
                </div>
              </article>
            </template>

            <template v-for="cat in categorias" :key="cat.id">
              <h2
                :id="`cat-${cat.id}`"
                :data-categoria="String(cat.id)"
                class="col-span-full scroll-mt-[162px] border-t border-marca/15 pt-7 font-display text-[clamp(38px,5vw,58px)] leading-none font-light text-marca first:border-t-0 first:pt-0 md:mt-12"
              >{{ cat.nombre }}</h2>

              <article
                v-for="p in platosPorCategoria.get(cat.id)"
                :key="p.id"
                class="grid grid-cols-[1fr_112px] gap-4 border-b border-marca/15 py-5 md:flex md:flex-col md:border-b-0 md:py-0"
                :class="{ 'opacity-70': !p.disponible }"
              >
                <!-- Foto: cuadrada, radio 20px, sin sombra (Sistema de Diseño) -->
                <figure
                  class="relative order-2 aspect-square w-28 overflow-hidden rounded-[14px] bg-lienzo-alt md:order-none md:mb-6 md:w-full md:rounded-foto"
                >
                  <img
                    v-if="p.foto" :src="p.foto" :alt="p.nombre" loading="lazy"
                    class="h-full w-full object-cover transition-transform duration-700 md:group-hover:scale-105"
                    :class="{ 'grayscale-[0.75] opacity-75': !p.disponible }"
                  />
                  <div v-else class="grid h-full w-full place-items-center bg-marca-suave font-display text-5xl font-light text-marca">
                    {{ p.nombre.charAt(0) }}
                  </div>

                  <div v-if="p.etiquetas?.length" class="absolute top-1.5 left-1.5 flex gap-1.5 md:top-3.5 md:left-3.5">
                    <span
                      v-for="et in p.etiquetas" :key="et"
                       class="rounded-full bg-lienzo px-2 py-1 text-[9px] font-semibold tracking-[0.10em] text-marca uppercase md:px-3 md:py-1.5 md:text-[10px]"
                    >{{ et }}</span>
                  </div>

                  <div v-if="!p.disponible" class="absolute inset-0 grid place-items-center bg-lienzo/75">
                    <span class="rounded-full bg-marca px-3 py-1.5 text-[9px] font-semibold tracking-[0.14em] text-lienzo uppercase md:px-5 md:py-2.5 md:text-[11px]">
                       {{ config["texto-plato-agotado"] || "Agotado hoy" }}
                    </span>
                  </div>

                  <button
                    v-if="p.disponible"
                    @click="carrito.agregar(p)"
                    :aria-label="`Agregar ${p.nombre} al pedido`"
                    class="absolute right-1.5 bottom-1.5 grid size-11 cursor-pointer place-items-center rounded-full text-[15px] font-bold transition-transform active:scale-95 md:right-2.5 md:bottom-2.5 md:hover:scale-110"
                    :class="carrito.cantidadDe(p.id)
                      ? 'bg-marca text-lienzo'
                      : 'bg-lienzo text-marca md:hover:bg-acento'"
                  >{{ carrito.cantidadDe(p.id) || "+" }}</button>
                </figure>

                <div class="order-1 min-w-0 md:order-none">
                  <div class="flex items-start justify-between gap-3.5">
                    <h3 class="text-base leading-tight font-medium tracking-[0.03em] uppercase md:text-[22px]">
                      {{ p.nombre }}
                    </h3>
                    <span class="shrink-0 pt-0.5 text-[15px] font-medium whitespace-nowrap text-marca md:text-lg">
                      {{ moneda.format(p.precio) }}
                    </span>
                  </div>

                  <!-- La descripción es la lista de ingredientes, no una frase publicitaria -->
                  <p class="mt-1.5 text-[13.5px] leading-snug opacity-80 md:mt-2.5 md:text-base">
                    {{ p.descripcion }}
                  </p>

                  <p v-if="p.alergenos" class="mt-2 text-xs text-marca/70 md:mt-3">
                    {{ p.alergenos }}
                  </p>

                  <div v-if="p.estadisticas?.length" class="mt-3 flex gap-4 border-t border-marca/15 pt-3 md:mt-4.5 md:gap-6.5 md:pt-4">
                    <div v-for="(dato, i) in p.estadisticas" :key="i" class="flex flex-col gap-1">
                      <b class="text-[15px] font-medium text-marca md:text-[17px]">{{ dato[0] }}</b>
                      <span class="text-[10px] font-medium tracking-[0.13em] text-marca/60 uppercase md:text-[11px]">
                        {{ dato[1] }}
                      </span>
                    </div>
                  </div>
                </div>
              </article>
            </template>
          </div>
        </section>
      </template>
    </main>

    <!-- ===== Encuéntranos ===== -->
    <section id="encuentranos" class="scroll-mt-[72px] bg-marca px-6 pt-20 pb-11 text-lienzo md:pt-28">
      <div class="mx-auto max-w-[1185px]">
       <p class="mb-5 inline-block rounded-full bg-acento px-4 py-2 text-[11px] font-semibold tracking-[0.18em] text-tinta uppercase">
           {{ config["etiqueta-visitanos"] || "Visítanos" }}
       </p>
        <h2 class="mb-12 font-display text-[clamp(32px,7vw,90px)] leading-[0.95] font-light">
          {{ config["etiqueta-encuentranos"] || "Encuéntranos" }}
        </h2>

        <div class="mb-14 grid grid-cols-2 gap-2.5 md:grid-cols-4 md:gap-4">
          <figure
            v-for="(img, i) in [
              { url: config['galeria-imagen-salon'], pie: config['galeria-pie-1'] || 'El salón', ancho: true },
              { url: config['galeria-imagen-barra'], pie: config['galeria-pie-2'] || 'La barra' },
              { url: config['galeria-imagen-terraza'], pie: config['galeria-pie-3'] || 'La terraza' },
            ]"
            :key="i"
            v-show="img.url"
            class="relative aspect-square overflow-hidden rounded-foto"
            :class="img.ancho ? 'col-span-2 md:aspect-[2/1]' : ''"
          >
            <img :src="img.url" :alt="img.pie" class="h-full w-full object-cover" loading="lazy" />
            <figcaption class="absolute bottom-3.5 left-3.5 rounded-full bg-lienzo px-3 py-1.5 text-[11px] font-semibold tracking-[0.12em] text-tinta uppercase">
              {{ img.pie }}
            </figcaption>
          </figure>
        </div>

        <div class="grid grid-cols-1 gap-8 border-t border-lienzo/20 pt-12 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <h3 class="mb-4 text-xs font-semibold tracking-[0.16em] uppercase opacity-60">
              {{ config["etiqueta-direccion"] || "Dirección" }}
            </h3>
            <p class="text-lg leading-snug">
              {{ config["direccion-linea1"] }}<br />{{ config["direccion-linea2"] }}
            </p>
          </div>

          <div>
            <h3 class="mb-4 text-xs font-semibold tracking-[0.16em] uppercase opacity-60">
              {{ config["etiqueta-horario"] || "Horario" }}
            </h3>
            <ul class="text-base">
              <li
                v-for="(h, i) in [
                  ['Lun – Jue', config['horario-lun-jue']],
                  ['Vie – Sáb', config['horario-vie-sab']],
                  ['Domingo', config['horario-domingo']],
                ]"
                :key="i"
                class="flex justify-between gap-4 border-b border-lienzo/15 py-2.5 first:pt-0"
              >
                <span class="opacity-60">{{ h[0] }}</span><span>{{ h[1] }}</span>
              </li>
            </ul>
          </div>

          <div>
            <h3 class="mb-4 text-xs font-semibold tracking-[0.16em] uppercase opacity-60">
              {{ config["etiqueta-contacto"] || "Contacto" }}
            </h3>
            <!-- Cada dato se pinta solo si existe: un restaurante sin correo
                 no debe mostrar un renglón en blanco -->
            <p class="text-lg leading-snug">
              <a v-if="config['telefono']" :href="`tel:${config['telefono'].replace(/\s/g, '')}`" class="hover:underline">
                {{ config["telefono"] }}</a>
              <br v-if="config['telefono'] && config['correo']" />
              <a v-if="config['correo']" :href="`mailto:${config['correo']}`" class="hover:underline">
                {{ config["correo"] }}</a>
            </p>
          </div>

          <div>
            <h3 class="mb-4 text-xs font-semibold tracking-[0.16em] uppercase opacity-60">
              {{ config["etiqueta-como-llegar"] || "Cómo llegar" }}
            </h3>
            <MapaUbicacion
              :latitud="config['mapa-latitud']"
              :longitud="config['mapa-longitud']"
              :etiqueta="config['nombre-restaurante']"
            />
          </div>
        </div>

        <footer class="mt-16 border-t border-lienzo/15 pt-7">
          <p class="text-xs tracking-wide opacity-50">
            {{ config["texto-pie-sitio"] || config["nombre-restaurante"] }}
          </p>
        </footer>
      </div>
    </section>

    <!-- ===== Carrito flotante ===== -->
    <Transition
      enter-from-class="translate-y-6 opacity-0" leave-to-class="translate-y-6 opacity-0"
      enter-active-class="transition duration-300" leave-active-class="transition duration-300"
    >
      <button
        v-if="carrito.totalUnidades > 0 && fueraDelHero"
        @click="carritoAbierto = true"
        class="fixed bottom-6 left-1/2 z-40 flex -translate-x-1/2 cursor-pointer items-center gap-2.5 rounded-full bg-marca px-6 py-4 text-[13px] font-medium tracking-[0.10em] text-lienzo uppercase"
      >
        Ver pedido
        <span class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-acento px-1.5 text-xs font-bold text-tinta">
          {{ carrito.totalUnidades }}
        </span>
      </button>
    </Transition>

    <PromocionDetalle
      v-if="promoAbierta"
      :promo="promoAbierta"
      :config="config"
      :cantidad="carrito.cantidadDe(promoAbierta.id)"
      @agregar="agregarPromo"
      @cerrar="promoAbierta = null"
    />

    <CarritoPanel
      v-if="carritoAbierto"
      :observaciones-rapidas="observacionesRapidas"
      :config="config"
      @cerrar="carritoAbierto = false"
    />
  </div>
</template>

<style scoped>
/* Halo de las promociones (SPEC-023, revisado 2026-09-16). Un anillo con el
   color de acento del tema que respira despacio: se nota sin gritar, y no
   parpadea ni cambia de tamaño. El anillo quieto va en la clase y la
   animación solo lo suaviza; con `prefers-reduced-motion` la regla global de
   style.css corta la animación y queda el anillo quieto, así la promo se
   sigue distinguiendo por el color. */
.promo-halo {
  box-shadow:
    0 0 0 2px var(--color-acento),
    0 0 14px 1px color-mix(in srgb, var(--color-acento) 45%, transparent);
  animation: respiro-promo 3.2s ease-in-out infinite alternate;
}
@keyframes respiro-promo {
  from {
    box-shadow:
      0 0 0 2px var(--color-acento),
      0 0 6px 0 color-mix(in srgb, var(--color-acento) 25%, transparent);
  }
  to {
    box-shadow:
      0 0 0 3px var(--color-acento),
      0 0 22px 4px color-mix(in srgb, var(--color-acento) 55%, transparent);
  }
}
</style>
