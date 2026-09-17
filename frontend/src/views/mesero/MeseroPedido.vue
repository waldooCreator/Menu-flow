<script setup>
/**
 * Camino B del mesero (SPEC-004): armar el pedido desde cero, con el mismo
 * menú que ve el cliente, cuando el cliente no usó la app.
 *
 * No necesita QR: al enviar, se firma el pedido con la mesa elegida y se
 * confirma en el mismo paso — la garantía de ADR-002 se mantiene, porque
 * quien confirma sigue siendo el mesero autenticado.
 */

import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { listarCategorias, listarPlatos, listarObservacionesRapidas } from "../../api/menu";
import { firmarPedido, confirmarPedido, listarMesas } from "../../api/pedidos";
import { listarCajas } from "../../api/caja";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";
import { esPromocion, resumenComponentes } from "../../lib/promociones";

const categorias = ref([]);
const platos = ref([]);
const observacionesRapidas = ref([]);
const mesas = ref([]);
const cargando = ref(true);

// Si se llega desde el salón (SPEC-012), la mesa viene ya elegida en la URL
// y el mesero no tiene que buscarla en la lista otra vez.
const route = useRoute();
const mesaElegida = ref(route.query.mesa || "");
const nombreCliente = ref("");
const items = ref([]); // { plato, cantidad, observaciones: [], nota }
const panelAbierto = ref(false);
const enviando = ref(false);
const error = ref(null);
const pedidoCreado = ref(null);

// "Cobrar al finalizar" (SPEC-004): el atajo de mostrador. Las cajas solo se
// cargan si el usuario puede cobrar — si la API responde 403, la opción
// sencillamente no aparece, sin romper nada.
const cajas = ref([]);
const cobrarAlFinalizar = ref(false);
const medioPagoElegido = ref(null);
const puedeCobrar = computed(() => cajas.value.length > 0);

const moneda = { format: formatearMoneda };

// SPEC-023: las promos vigentes también se venden desde aquí, de primeras,
// con la misma vigencia que ve el cliente (la API ya las filtra).
const promociones = computed(() => platos.value.filter(esPromocion));

const platosPorCategoria = computed(() => {
  const mapa = new Map(categorias.value.map((c) => [c.id, []]));
  for (const p of platos.value) {
    if (mapa.has(p.categoria_id)) mapa.get(p.categoria_id).push(p);
  }
  return mapa;
});

const totalUnidades = computed(() => items.value.reduce((n, i) => n + i.cantidad, 0));
const totalPrecio = computed(() =>
  items.value.reduce((t, i) => t + i.plato.precio * i.cantidad, 0)
);
const agotadosEnPedido = computed(() => items.value.filter((item) => !item.plato.disponible));

function cantidadDe(platoId) {
  return items.value.find((i) => i.plato.id === platoId)?.cantidad ?? 0;
}

function agregar(plato) {
  const it = items.value.find((i) => i.plato.id === plato.id);
  if (it) it.cantidad += 1;
  else items.value.push({ plato, cantidad: 1, observaciones: [], nota: "" });
}

function quitar(platoId) {
  const it = items.value.find((i) => i.plato.id === platoId);
  if (!it) return;
  it.cantidad -= 1;
  if (it.cantidad <= 0) items.value = items.value.filter((i) => i.plato.id !== platoId);
}

function alternarObservacion(platoId, texto) {
  const it = items.value.find((i) => i.plato.id === platoId);
  if (!it) return;
  const idx = it.observaciones.indexOf(texto);
  if (idx === -1) it.observaciones.push(texto);
  else it.observaciones.splice(idx, 1);
}

function irACategoria(id) {
  document.getElementById(`mp-cat-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function enviar() {
  if (!mesaElegida.value) {
    error.value = "Elige la mesa antes de enviar.";
    return;
  }
  if (agotadosEnPedido.value.length) {
    error.value = `Retira del pedido: ${agotadosEnPedido.value.map((item) => item.plato.nombre).join(", ")}.`;
    return;
  }
  enviando.value = true;
  error.value = null;
  try {
    const arreglo = items.value.map((i) => ({
      plato_id: i.plato.id,
      cantidad: i.cantidad,
      observacion: [...i.observaciones, i.nota].filter(Boolean).join(", "),
    }));
    const texto = await firmarPedido(mesaElegida.value, nombreCliente.value, arreglo);
    // Si se marcó cobrar, el medio de pago viaja en la misma llamada: el
    // pedido entra a cocina y la cuenta se cierra de una.
    const medio = cobrarAlFinalizar.value ? medioPagoElegido.value : null;
    pedidoCreado.value = await confirmarPedido(texto, "", medio);
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo enviar el pedido.";
  } finally {
    enviando.value = false;
  }
}

function nuevoPedido() {
  items.value = [];
  nombreCliente.value = "";
  panelAbierto.value = false;
  pedidoCreado.value = null;
  error.value = null;
}

onMounted(async () => {
  try {
    const [cats, pls, obs, ms] = await Promise.all([
      listarCategorias(), listarPlatos(), listarObservacionesRapidas(), listarMesas(),
    ]);
    categorias.value = cats;
    platos.value = pls;
    observacionesRapidas.value = obs;
    mesas.value = ms;
    try {
      cajas.value = await listarCajas();
      medioPagoElegido.value = cajas.value[0]?.id ?? null;
    } catch {
      // Sin permiso de cobro: la opción no se ofrece.
      cajas.value = [];
    }
    // Una mesa que llegó por la URL pero ya no existe (desactivada) no debe
    // quedar seleccionada en fantasma: se limpia y el mesero elige.
    if (mesaElegida.value && !ms.some((m) => m.codigo === mesaElegida.value)) {
      mesaElegida.value = "";
    }
  } finally {
    cargando.value = false;
  }
});
</script>

<template>
  <MarcoInterno titulo="Crear pedido" ancho="max-w-5xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <p v-if="cargando" class="py-10 text-center text-tinta/50">Cargando menú…</p>

    <template v-else>
      <!-- Mesa y cliente -->
      <div class="mb-6 rounded-3xl border border-marca/10 bg-white p-5">
        <p class="mb-3 text-[11px] font-bold tracking-[0.14em] text-marca/60 uppercase">Mesa</p>
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-for="m in mesas" :key="m.codigo"
            @click="mesaElegida = m.codigo"
            class="cursor-pointer rounded-full border px-5 py-2.5 text-[13px] font-semibold transition-colors"
            :class="mesaElegida === m.codigo
              ? 'border-marca bg-marca text-lienzo'
              : 'border-marca/15 text-marca hover:border-marca'"
          >{{ m.nombre }}</button>

          <input
            v-model="nombreCliente" type="text" maxlength="60"
            placeholder="Nombre del cliente (opcional)"
            class="ml-auto min-w-52 flex-1 rounded-full border border-marca/15 px-4 py-2.5 text-sm outline-none placeholder:text-marca/40 focus:border-marca sm:flex-none"
          />
        </div>
      </div>

      <!-- Chips de categoría -->
      <div class="sticky top-[61px] z-30 -mx-5 border-b border-marca/10 bg-lienzo px-5 py-3">
        <div class="flex gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <button
            v-if="promociones.length"
            @click="irACategoria('promociones')"
            class="shrink-0 cursor-pointer rounded-full border border-acento bg-acento px-4 py-2 text-[12px] font-bold tracking-[0.06em] text-tinta uppercase"
          >★ Promociones</button>
          <button
            v-for="cat in categorias" :key="cat.id"
            @click="irACategoria(cat.id)"
            class="shrink-0 cursor-pointer rounded-full border border-marca/15 px-4 py-2 text-[12px] font-semibold tracking-[0.06em] text-marca uppercase transition-colors hover:border-marca"
          >{{ cat.nombre }}</button>
        </div>
      </div>

      <!-- Promociones (SPEC-023) -->
      <section v-if="promociones.length" class="mt-7">
        <h2 id="mp-cat-promociones" class="mb-4 scroll-mt-32 font-display text-3xl font-light text-marca">
          Promociones
        </h2>
        <div class="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          <article
            v-for="p in promociones" :key="p.id"
            class="flex flex-col gap-2 rounded-2xl border-2 border-acento bg-white p-3.5"
            :class="{ 'opacity-55': !p.disponible }"
          >
            <div class="flex items-start justify-between gap-3">
              <p class="text-[14px] leading-tight font-semibold">{{ p.nombre }}</p>
              <p class="shrink-0 text-[13px] font-semibold text-marca">{{ moneda.format(p.precio) }}</p>
            </div>
            <p class="text-[12.5px] leading-snug text-tinta/60">{{ resumenComponentes(p) }}</p>
            <div class="mt-auto pt-1">
              <span v-if="!p.disponible" class="text-[11px] font-bold tracking-wide text-alerta uppercase">Agotada</span>
              <div v-else-if="cantidadDe(p.id) > 0" class="inline-flex items-center gap-1 rounded-full border border-marca/15 p-0.5">
                <button
                  @click="quitar(p.id)" :aria-label="`Quitar una ${p.nombre}`"
                  class="grid size-11 cursor-pointer place-items-center rounded-full text-lg font-semibold text-alerta hover:bg-marca-suave"
                >−</button>
                <span class="min-w-6 text-center text-sm font-bold">{{ cantidadDe(p.id) }}</span>
                <button
                  @click="agregar(p)" :aria-label="`Agregar otra ${p.nombre}`"
                  class="grid size-11 cursor-pointer place-items-center rounded-full text-lg font-semibold text-marca hover:bg-marca-suave"
                >+</button>
              </div>
              <button
                v-else @click="agregar(p)"
                class="min-h-11 cursor-pointer rounded-full bg-marca px-4 text-[12px] font-bold tracking-[0.04em] text-lienzo uppercase"
              >Agregar</button>
            </div>
          </article>
        </div>
      </section>

      <!-- Menú -->
      <section v-for="cat in categorias" :key="cat.id" class="mt-7">
        <h2
          :id="`mp-cat-${cat.id}`"
          class="mb-4 scroll-mt-32 font-display text-3xl font-light text-marca"
        >{{ cat.nombre }}</h2>

        <div class="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          <article
            v-for="p in platosPorCategoria.get(cat.id)" :key="p.id"
            class="flex gap-3.5 rounded-2xl border border-marca/10 bg-white p-3.5"
            :class="{ 'opacity-55': !p.disponible }"
          >
            <img
              v-if="p.foto" :src="p.foto" :alt="p.nombre"
              class="size-20 shrink-0 rounded-xl object-cover"
            />
            <div v-else class="grid size-20 shrink-0 place-items-center rounded-xl bg-marca-suave font-display text-2xl text-marca">
              {{ p.nombre.charAt(0) }}
            </div>

            <div class="flex min-w-0 flex-1 flex-col">
              <p class="text-[14px] leading-tight font-semibold">{{ p.nombre }}</p>
              <p class="mt-0.5 text-[13px] font-medium text-marca">{{ moneda.format(p.precio) }}</p>

              <div class="mt-auto pt-2">
                <span v-if="!p.disponible" class="text-[11px] font-bold tracking-wide text-alerta uppercase">
                  Agotado hoy
                </span>

                <div v-else-if="cantidadDe(p.id) > 0" class="inline-flex items-center gap-1 rounded-full border border-marca/15 p-0.5">
                  <button
                    @click="quitar(p.id)"
                    class="grid size-8 cursor-pointer place-items-center rounded-full text-lg font-semibold text-[#8A3B18] hover:bg-marca-suave"
                  >−</button>
                  <span class="min-w-6 text-center text-sm font-bold">{{ cantidadDe(p.id) }}</span>
                  <button
                    @click="agregar(p)"
                    class="grid size-8 cursor-pointer place-items-center rounded-full text-lg font-semibold text-marca hover:bg-marca-suave"
                  >+</button>
                </div>

                <button
                  v-else
                  @click="agregar(p)"
                  class="cursor-pointer rounded-full bg-marca px-4 py-2 text-[12px] font-bold tracking-[0.04em] text-lienzo uppercase transition-transform hover:scale-105"
                >Agregar</button>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- Barra inferior -->
      <Transition
        enter-from-class="translate-y-6 opacity-0" leave-to-class="translate-y-6 opacity-0"
        enter-active-class="transition duration-300" leave-active-class="transition duration-300"
      >
        <button
          v-if="totalUnidades > 0 && !panelAbierto && !pedidoCreado"
          @click="panelAbierto = true"
          class="fixed bottom-6 left-1/2 z-40 flex -translate-x-1/2 cursor-pointer items-center gap-3 rounded-full bg-marca px-7 py-4 text-[13px] font-semibold tracking-[0.08em] text-lienzo uppercase"
        >
          Revisar pedido
          <span class="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-acento px-1.5 text-xs font-bold text-tinta">
            {{ totalUnidades }}
          </span>
          <span class="font-bold normal-case">{{ moneda.format(totalPrecio) }}</span>
        </button>
      </Transition>

      <!-- Panel de revisión -->
      <div
        v-if="panelAbierto && !pedidoCreado"
        class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/55 backdrop-blur-sm sm:items-center"
        @click.self="panelAbierto = false"
      >
        <div class="flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-t-[26px] bg-lienzo sm:max-w-[680px] sm:rounded-[26px]">
          <header class="flex shrink-0 items-center justify-between border-b border-marca/15 px-6 pt-5 pb-4">
            <h2 class="font-display text-[28px] font-light text-marca">Revisar pedido</h2>
            <button
              @click="panelAbierto = false" aria-label="Cerrar"
              class="grid size-11 cursor-pointer place-items-center rounded-full border border-marca/15 text-marca hover:bg-marca hover:text-lienzo"
            >✕</button>
          </header>

          <div class="flex-1 overflow-y-auto overscroll-contain px-6 py-3">
            <p class="mb-2 text-[12px] font-semibold text-marca/70">
              {{ mesas.find((m) => m.codigo === mesaElegida)?.nombre || "⚠ Sin mesa elegida" }}
              <span v-if="nombreCliente"> · {{ nombreCliente }}</span>
            </p>

            <ul>
              <li
                v-for="it in items" :key="it.plato.id"
                class="border-b border-marca/10 py-4 last:border-b-0"
              >
                <div class="flex items-center justify-between gap-3">
                  <strong class="text-[15px] font-medium">{{ it.cantidad }}× {{ it.plato.nombre }}</strong>
                  <span class="font-medium text-marca">{{ moneda.format(it.plato.precio * it.cantidad) }}</span>
                </div>

                <div class="mt-2.5 flex flex-wrap gap-1.5">
                  <button
                    v-for="obs in (it.plato.observaciones ?? observacionesRapidas)" :key="obs.id"
                    @click="alternarObservacion(it.plato.id, obs.texto)"
                    class="cursor-pointer rounded-full border px-3 py-1.5 text-[11px] font-semibold tracking-[0.04em] uppercase transition-colors"
                    :class="it.observaciones.includes(obs.texto)
                      ? 'border-marca bg-marca text-lienzo'
                      : 'border-marca/15 text-marca hover:border-marca'"
                  >{{ obs.texto }}</button>
                </div>

                <input
                  v-model="it.nota" type="text" maxlength="80"
                  placeholder="Otra indicación…"
                  class="mt-2 w-full border-b border-marca/15 bg-transparent py-1.5 text-sm outline-none placeholder:text-marca/40 focus:border-marca"
                />
              </li>
            </ul>
          </div>

          <footer class="shrink-0 border-t border-marca/15 bg-lienzo px-6 pt-4 pb-5">
            <div class="mb-3.5 flex items-baseline justify-between">
              <span class="text-xs font-semibold tracking-[0.14em] text-marca/65 uppercase">Total</span>
              <b class="text-2xl font-medium text-marca">{{ moneda.format(totalPrecio) }}</b>
            </div>
            <!-- "Cobrar al finalizar" (SPEC-004): el atajo de mostrador.
                 Solo aparece si este usuario tiene habilitado cobrar — y el
                 servidor lo rechaza igual si lo fuerza. -->
            <template v-if="puedeCobrar">
              <label class="mb-3 flex cursor-pointer items-center gap-2.5 text-[14px] font-semibold text-marca">
                <span class="-m-2.5 grid min-h-11 min-w-11 place-items-center p-2.5"><input type="checkbox" v-model="cobrarAlFinalizar" class="size-4 cursor-pointer" /></span>
                Cobrar al finalizar
              </label>

              <div v-if="cobrarAlFinalizar" class="mb-3.5 grid grid-cols-2 gap-2">
                <button
                  v-for="c in cajas" :key="c.id"
                  @click="medioPagoElegido = c.id"
                  class="min-h-11 cursor-pointer rounded-xl border-2 text-[13px] font-semibold transition-colors"
                  :class="medioPagoElegido === c.id
                    ? 'border-marca bg-marca text-lienzo'
                    : 'border-marca/20 text-marca'"
                >{{ c.nombre }}</button>
              </div>
            </template>

             <p v-if="agotadosEnPedido.length" class="mb-2.5 rounded-xl bg-alerta/10 px-3 py-2 text-[13px] font-semibold text-alerta">
               {{ agotadosEnPedido.map((item) => item.plato.nombre).join(", ") }} se agotó. Retíralo antes de enviar.
             </p>
             <p v-if="error" class="mb-2.5 text-[13px] font-semibold text-alerta">{{ error }}</p>
            <button
              @click="enviar" :disabled="enviando || !mesaElegida"
              class="min-h-13.5 w-full cursor-pointer rounded-full bg-marca text-sm font-semibold tracking-[0.10em] text-lienzo uppercase transition-transform active:scale-[0.985] disabled:opacity-40"
            >
              {{ enviando ? "Enviando…" : cobrarAlFinalizar ? "Enviar y cobrar" : "Enviar a cocina" }}
            </button>
          </footer>
        </div>
      </div>

      <!-- Confirmado -->
      <div
        v-if="pedidoCreado"
        class="fixed inset-0 z-50 grid place-items-center bg-tinta/55 backdrop-blur-sm px-4"
      >
        <div class="w-full max-w-sm rounded-3xl bg-lienzo p-8 text-center">
          <span class="mx-auto mb-4 grid size-16 place-items-center rounded-full bg-marca-suave text-marca">
            <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2.2">
              <path d="M20 6L9 17l-5-5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </span>
          <p class="font-display text-2xl font-light text-marca">
            Pedido #{{ pedidoCreado.pedido_id }} enviado a cocina
          </p>

          <p v-if="pedidoCreado.cobrada" class="mt-3 inline-block rounded-full bg-emerald-600 px-4 py-1.5 text-[12px] font-bold tracking-[0.08em] text-white uppercase">
            Cobrado
          </p>

          <!-- El cobro va fuera de la transacción del pedido a propósito: si
               falla, el pedido YA está en cocina y debe quedarse ahí. Se avisa
               y se cobra después desde Cuentas. -->
          <p v-else-if="pedidoCreado.aviso_cobro" class="mt-3 rounded-xl bg-amber-50 px-3.5 py-2.5 text-[13px] font-semibold text-amber-900">
            El pedido entró a cocina, pero no se pudo cobrar:
            {{ pedidoCreado.aviso_cobro }} Cóbralo desde Cuentas.
          </p>

          <button
            @click="nuevoPedido"
            class="mt-6 w-full cursor-pointer rounded-full bg-marca py-3.5 text-sm font-semibold tracking-[0.08em] text-lienzo uppercase"
          >Crear otro pedido</button>
          <RouterLink
            :to="{ name: 'mesero-escaner' }"
            class="mt-3 block text-[13px] font-semibold text-marca underline-offset-2 hover:underline"
          >Volver al escáner</RouterLink>
        </div>
      </div>
    </template>
  </MarcoInterno>
</template>
