<script setup>
/**
 * Registro de pedidos en curso y edición de los ya enviados (SPEC-011).
 *
 * Esta pantalla no existía, y la necesitaban dos cosas a la vez: editar un
 * pedido que ya está en cocina, y **llegar a un pedido cuya mesa se
 * liberó** — que desde el salón es inalcanzable, justamente porque su mesa
 * ya no lo muestra.
 *
 * Coherente con SPEC-012: no hay dueño. Cualquier mesero ve y edita
 * cualquier pedido.
 */
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";
import { listarPedidosActivos, listarMesas, editarPedidoLote, entregarPedido } from "../../api/pedidos";
import { listarPlatos } from "../../api/menu";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const route = useRoute();
const pedidos = ref([]);
const mesas = ref([]);
const platos = ref([]);
const cargando = ref(true);
const abiertoId = ref(null);
const error = ref(null);
const panelDestino = ref(false);
const panelAgregar = ref(false);
const editandoObs = ref(null); // detalle_id
const textoObs = ref("");

const moneda = { format: formatearMoneda };

const ETIQUETA_ESTADO = {
  pendiente: "En cocina",
  en_preparacion: "Preparándose",
  listo: "Listo para llevar",
};

const abierto = computed(() => pedidos.value.find((p) => p.id === abiertoId.value) || null);

/* --- Edición por lotes ---------------------------------------------------
 * Los cambios NO se mandan al tocarlos: se acumulan aquí y se aplican todos
 * juntos al confirmar. Editar un pedido que ya está en cocina merece que el
 * mesero pueda revisar antes de que salga — distinto de mover una mesa, que
 * es reversible de un toque.
 */
const cambios = ref([]);
const aplicando = ref(false);
const confirmando = ref(false);   // modal de confirmación
const descartando = ref(false);   // modal de descartar
let contadorNuevos = 0;

const hayCambios = computed(() => cambios.value.length > 0);

/** El pedido como QUEDARÍA si se aplicaran los cambios pendientes. */
const detallesPreview = computed(() => {
  if (!abierto.value) return [];
  const lista = abierto.value.detalles.map((d) => ({ ...d, marca: null }));
  for (const c of cambios.value) {
    if (c.tipo === "agregar") {
      lista.push({
        id: c.clave, nombre: c.plato.nombre, precio: c.plato.precio,
        cantidad: c.cantidad, observacion: c.observacion || "",
        estacion: null, marca: "nuevo",
      });
      continue;
    }
    const d = lista.find((x) => x.id === c.detalle_id);
    if (!d) continue;
    if (c.tipo === "quitar") d.marca = "quitado";
    else if (c.tipo === "cantidad") { d.cantidad = c.cantidad; d.marca = d.marca || "editado"; }
    else if (c.tipo === "observacion") { d.observacion = c.observacion; d.marca = d.marca || "editado"; }
  }
  return lista;
});

const destinoPreview = computed(() => {
  const c = [...cambios.value].reverse().find((x) => x.tipo === "destino");
  if (!c) return null;
  return c.es_domicilio ? "Domicilio" : (mesas.value.find((m) => m.codigo === c.mesa)?.nombre ?? "otra mesa");
});

/** Reemplaza el cambio anterior del mismo renglón y tipo, en vez de apilarlos. */
function encolar(cambio) {
  cambios.value = cambios.value.filter(
    (c) => !(c.tipo === cambio.tipo && c.detalle_id === cambio.detalle_id && c.tipo !== "agregar")
  );
  cambios.value.push(cambio);
}

function descartarCambios() {
  cambios.value = [];
  descartando.value = false;
  abiertoId.value = null;
}

function intentarCerrar() {
  if (hayCambios.value) descartando.value = true;
  else abiertoId.value = null;
}

async function aplicarCambios() {
  aplicando.value = true;
  error.value = null;
  try {
    // Las operaciones van sin la clave temporal de los agregados.
    const ops = cambios.value.map(({ clave, plato, ...op }) => op);
    const actualizado = await editarPedidoLote(abiertoId.value, ops);
    const i = pedidos.value.findIndex((p) => p.id === actualizado.id);
    if (i !== -1) pedidos.value[i] = actualizado;
    cambios.value = [];
    confirmando.value = false;
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudieron aplicar los cambios.";
    confirmando.value = false;
  } finally {
    aplicando.value = false;
  }
}

// Un pedido sin mesa y que no es domicilio quedó huérfano al liberar la
// mesa: es exactamente el caso que originó esta spec, así que se marca.
// Un pedido ya cobrado no está huérfano: su mesa se liberó al pagar.
const huerfano = (p) => !p.mesa_codigo && !p.es_domicilio && !p.cobrada;

/**
 * Marcar entregado desde aquí (SPEC-012: cualquier mesero entrega cualquier
 * pedido). Antes solo se podía desde la campana del mesero que lo tomó: un
 * pedido cobrado cuya mesa ya se liberó quedaba en esta lista para siempre.
 */
const puedeEntregar = (p) => p.es_domicilio || ["listo", "en_preparacion"].includes(p.estado);

async function entregar(p) {
  error.value = null;
  try {
    await entregarPedido(p.id);
    await cargar({ forzar: true });
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo marcar entregado.";
  }
}

async function cargar({ forzar = false } = {}) {
  // El sondeo NO pisa una edición a medio redactar: si hay cambios
  // pendientes, refrescar cambiaría los renglones bajo los pies del mesero
  // y sus cambios quedarían apuntando a datos viejos.
  if (!forzar && hayCambios.value) return;
  try {
    pedidos.value = await listarPedidosActivos();
  } finally {
    cargando.value = false;
  }
}

function moverA(mesaCodigo) {
  encolar({ tipo: "destino", mesa: mesaCodigo, es_domicilio: false });
  panelDestino.value = false;
}

function pasarADomicilio() {
  encolar({ tipo: "destino", mesa: null, es_domicilio: true });
  panelDestino.value = false;
}

function sumar(detalle, delta) {
  const nueva = detalle.cantidad + delta;
  if (nueva < 1) return;
  if (String(detalle.id).startsWith("nuevo-")) {
    const c = cambios.value.find((x) => x.clave === detalle.id);
    if (c) c.cantidad = nueva;
    return;
  }
  encolar({ tipo: "cantidad", detalle_id: detalle.id, cantidad: nueva });
}

function quitar(detalle) {
  if (String(detalle.id).startsWith("nuevo-")) {
    cambios.value = cambios.value.filter((x) => x.clave !== detalle.id);
    return;
  }
  encolar({ tipo: "quitar", detalle_id: detalle.id });
}

function deshacerQuitar(detalle) {
  cambios.value = cambios.value.filter(
    (c) => !(c.tipo === "quitar" && c.detalle_id === detalle.id)
  );
}

function agregar(plato) {
  contadorNuevos += 1;
  cambios.value.push({
    tipo: "agregar", plato_id: plato.id, cantidad: 1, observacion: "",
    clave: `nuevo-${contadorNuevos}`, plato,
  });
  panelAgregar.value = false;
}

function empezarObs(detalle) {
  editandoObs.value = detalle.id;
  textoObs.value = detalle.observacion || "";
}

function guardarObs(detalle) {
  if (String(detalle.id).startsWith("nuevo-")) {
    const c = cambios.value.find((x) => x.clave === detalle.id);
    if (c) c.observacion = textoObs.value;
  } else {
    encolar({ tipo: "observacion", detalle_id: detalle.id, observacion: textoObs.value });
  }
  editandoObs.value = null;
}

let temporizador = null;
onMounted(async () => {
  await cargar({ forzar: true });
  // Si se llegó desde el salón con un pedido señalado, se abre solo.
  if (route.query.pedido) abiertoId.value = Number(route.query.pedido);
  [mesas.value, platos.value] = await Promise.all([listarMesas(), listarPlatos()]);
  temporizador = setInterval(cargar, 8000);
});
onUnmounted(() => clearInterval(temporizador));
</script>

<template>
  <MarcoInterno titulo="Pedidos en curso" ancho="max-w-3xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <p v-if="cargando" class="py-14 text-center text-tinta/50">Cargando pedidos…</p>

    <p
      v-else-if="pedidos.length === 0"
      class="rounded-3xl border-2 border-dashed border-tinta/10 py-14 text-center text-[14px] font-medium text-tinta/40"
    >
      No hay pedidos en curso.
    </p>

    <p v-if="error && !abiertoId" class="mb-3.5 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">{{ error }}</p>

    <div v-else class="grid gap-3.5">
      <article
        v-for="p in pedidos" :key="p.id"
        class="rounded-3xl border bg-white p-5"
        :class="huerfano(p) ? 'border-amber-400 bg-amber-50/60' : 'border-marca/10'"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <strong class="font-display text-[24px] leading-none font-light text-marca">
              {{ p.destino }}
            </strong>
            <p class="mt-1.5 text-[12px] font-semibold text-tinta/45">
              Pedido #{{ p.id }} · {{ ETIQUETA_ESTADO[p.estado] || p.estado }}
              <template v-if="p.nombre_cliente"> · {{ p.nombre_cliente }}</template>
              <span v-if="p.cobrada" class="ml-1 rounded-full bg-emerald-100 px-2 py-0.5 text-emerald-800">Pagado</span>
            </p>
          </div>
          <span class="shrink-0 font-semibold text-marca">{{ moneda.format(p.total) }}</span>
        </div>

        <!-- El caso que originó la spec: la mesa se liberó y el pedido quedó
             sin destino. Se avisa aquí porque desde el salón es invisible. -->
        <p v-if="huerfano(p)" class="mt-3 rounded-xl bg-amber-100 px-3.5 py-2.5 text-[13px] font-semibold text-amber-900">
          Este pedido se quedó sin mesa. Asígnale una, o pásalo a domicilio.
        </p>

        <ul class="mt-3 border-t border-marca/10 pt-2.5">
          <li v-for="d in p.detalles" :key="d.id" class="py-1 text-[15px]">
            {{ d.cantidad }}× {{ d.nombre }}
            <span v-if="d.observacion" class="font-semibold text-amber-700">— {{ d.observacion }}</span>
          </li>
        </ul>

        <div class="mt-4 flex gap-2.5">
          <button
            v-if="!p.cobrada"
            @click="abiertoId = p.id; error = null"
            class="min-h-12 flex-1 cursor-pointer rounded-2xl border-2 border-marca text-[14px] font-bold text-marca transition-transform active:scale-[0.98]"
          >Editar pedido</button>
          <button
            v-if="puedeEntregar(p)"
            @click="entregar(p)"
            class="min-h-12 flex-1 cursor-pointer rounded-2xl bg-emerald-600 text-[14px] font-bold text-white transition-transform active:scale-[0.98]"
          >✓ Marcar entregado</button>
        </div>
      </article>
    </div>

    <!-- ===== Panel de edición ===== -->
    <div
      v-if="abierto"
      class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/55 backdrop-blur-sm sm:items-center"
      @click.self="intentarCerrar"
    >
      <div class="flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-t-[26px] bg-lienzo sm:max-w-lg sm:rounded-[26px]">
        <header class="flex shrink-0 items-start justify-between gap-4 border-b border-marca/15 px-5 py-5">
          <div>
            <p class="text-[11px] font-semibold tracking-[0.16em] text-marca/60 uppercase">
              Pedido #{{ abierto.id }}
            </p>
            <h2 class="font-display text-[28px] leading-none font-light text-marca">
              <span :class="destinoPreview ? 'text-tinta/35 line-through' : ''">{{ abierto.destino }}</span>
              <span v-if="destinoPreview" class="text-marca"> → {{ destinoPreview }}</span>
            </h2>
          </div>
          <button
            @click="intentarCerrar" aria-label="Cerrar"
            class="grid size-11 shrink-0 cursor-pointer place-items-center rounded-full border border-marca/15 text-marca"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none" />
            </svg>
          </button>
        </header>

        <div class="flex-1 overflow-y-auto overscroll-contain px-5 py-4">
          <p v-if="error" class="mb-3.5 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
            {{ error }}
          </p>

          <!-- Destino -->
          <button
            @click="panelDestino = !panelDestino"
            class="min-h-12 w-full cursor-pointer rounded-2xl border-2 border-marca px-4 text-[14px] font-bold text-marca"
          >Cambiar destino</button>

          <div v-if="panelDestino" class="mt-2.5 rounded-2xl border border-marca/15 bg-white p-3.5">
            <button
              @click="pasarADomicilio"
              class="mb-2 min-h-12 w-full cursor-pointer rounded-xl bg-marca text-[14px] font-bold text-lienzo"
            >Pasar a domicilio</button>
            <p class="mt-3 mb-2 text-[11px] font-semibold tracking-[0.12em] text-marca/60 uppercase">
              O moverlo a otra mesa
            </p>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="m in mesas" :key="m.codigo"
                :disabled="m.codigo === abierto.mesa_codigo"
                @click="moverA(m.codigo)"
                class="min-h-12 cursor-pointer rounded-xl border border-marca/20 text-[14px] font-semibold text-marca disabled:opacity-35"
              >{{ m.nombre }}</button>
            </div>
          </div>

          <!-- Platos -->
          <h3 class="mt-6 mb-2.5 text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
            Platos
          </h3>
          <div
            v-for="d in detallesPreview" :key="d.id"
            class="mb-2.5 rounded-2xl border p-3.5 transition-colors"
            :class="{
              'border-alerta/40 bg-alerta/5': d.marca === 'quitado',
              'border-emerald-300 bg-emerald-50/60': d.marca === 'nuevo',
              'border-amber-300 bg-amber-50/50': d.marca === 'editado',
              'border-marca/12 bg-white': !d.marca,
            }"
          >
            <p v-if="d.marca" class="mb-1.5 text-[11px] font-bold tracking-[0.1em] uppercase"
               :class="{
                 'text-alerta': d.marca === 'quitado',
                 'text-emerald-700': d.marca === 'nuevo',
                 'text-amber-800': d.marca === 'editado',
               }">
              {{ d.marca === 'quitado' ? 'Se quitará' : d.marca === 'nuevo' ? 'Nuevo' : 'Modificado' }}
            </p>
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <strong class="text-[15px] font-semibold" :class="d.marca === 'quitado' ? 'line-through opacity-60' : ''">{{ d.nombre }}</strong>
                <p v-if="d.estacion" class="mt-0.5 text-[12px] text-tinta/45">{{ d.estacion }}</p>
              </div>
              <span class="shrink-0 text-[14px] font-medium text-marca">
                {{ moneda.format(d.precio * d.cantidad) }}
              </span>
            </div>

            <div class="mt-3 flex flex-wrap items-center gap-2">
              <div class="inline-flex items-center gap-0.5 rounded-full border border-marca/15 p-0.5">
                <button
                  @click="sumar(d, -1)" aria-label="Uno menos"
                  class="grid size-11 cursor-pointer place-items-center rounded-full text-[17px] font-semibold text-[#8A3B18]"
                >−</button>
                <span class="min-w-7 text-center text-[15px] font-semibold">{{ d.cantidad }}</span>
                <button
                  @click="sumar(d, 1)" aria-label="Uno más"
                  class="grid size-11 cursor-pointer place-items-center rounded-full text-[17px] font-semibold text-marca"
                >+</button>
              </div>

              <button
                @click="empezarObs(d)"
                class="min-h-11 cursor-pointer rounded-full border border-marca/20 px-3.5 text-[12px] font-semibold text-marca"
              >{{ d.observacion ? "Cambiar nota" : "Agregar nota" }}</button>

              <button
                v-if="d.marca !== 'quitado'"
                @click="quitar(d)"
                class="ml-auto min-h-11 cursor-pointer rounded-full px-3.5 text-[12px] font-semibold text-alerta"
              >Quitar</button>
              <button
                v-else
                @click="deshacerQuitar(d)"
                class="ml-auto min-h-11 cursor-pointer rounded-full px-3.5 text-[12px] font-semibold text-marca"
              >Deshacer</button>
            </div>

            <p v-if="d.observacion && editandoObs !== d.id" class="mt-2 text-[13px] font-semibold text-amber-700">
              {{ d.observacion }}
            </p>

            <div v-if="editandoObs === d.id" class="mt-2.5">
              <input
                v-model="textoObs" type="text" maxlength="200"
                placeholder="Sin cebolla, término medio…"
                class="w-full rounded-xl border border-marca/20 bg-white px-3.5 py-2.5 text-[14px] outline-none focus:border-marca"
              />
              <div class="mt-2 flex gap-2">
                <button
                  @click="editandoObs = null"
                  class="min-h-11 flex-1 cursor-pointer rounded-xl border border-marca/20 text-[13px] font-semibold text-marca"
                >Cancelar</button>
                <button
                  @click="guardarObs(d)"
                  class="min-h-11 flex-1 cursor-pointer rounded-xl bg-marca text-[13px] font-semibold text-lienzo"
                >Guardar</button>
              </div>
            </div>
          </div>

          <button
            @click="panelAgregar = !panelAgregar"
            class="mt-1 min-h-12 w-full cursor-pointer rounded-2xl border-2 border-dashed border-marca/30 text-[14px] font-bold text-marca"
          >+ Agregar un plato</button>

          <div v-if="panelAgregar" class="mt-2.5 grid gap-2">
            <button
              v-for="pl in platos" :key="pl.id"
              :disabled="!pl.disponible"
              @click="agregar(pl)"
              class="flex min-h-12 cursor-pointer items-center justify-between gap-3 rounded-xl border border-marca/15 bg-white px-3.5 text-left text-[14px] font-semibold disabled:opacity-35"
            >
              <span>{{ pl.nombre }}</span>
              <span class="shrink-0 text-marca">{{ moneda.format(pl.precio) }}</span>
            </button>
          </div>

          <!-- Historial: es la auditoría de ADR-007, visible -->
          <template v-if="abierto.novedades.length">
            <h3 class="mt-6 mb-2 text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
              Cambios de este pedido
            </h3>
            <ul class="rounded-2xl border border-marca/12 bg-white p-3.5">
              <li v-for="(n, i) in abierto.novedades" :key="i" class="py-1 text-[13px]">
                <span class="font-semibold">{{ n.descripcion }}</span>
                <span class="text-tinta/45"> · {{ n.autor }}</span>
              </li>
            </ul>
          </template>
        </div>

        <!-- Pie fijo: nada se manda hasta tocar "Aplicar cambios" -->
        <footer class="shrink-0 border-t border-marca/15 bg-lienzo px-5 py-4">
          <p v-if="hayCambios" class="mb-2.5 text-center text-[12.5px] font-semibold text-amber-800">
            {{ cambios.length }}
            {{ cambios.length === 1 ? "cambio sin aplicar" : "cambios sin aplicar" }}
          </p>
          <p v-else class="mb-2.5 text-center text-[12.5px] text-tinta/45">
            Los cambios no se envían hasta que los apliques.
          </p>

          <button
            @click="confirmando = true" :disabled="!hayCambios || aplicando"
            class="min-h-14 w-full cursor-pointer rounded-2xl bg-marca text-[15px] font-bold text-lienzo transition-transform active:scale-[0.98] disabled:opacity-35"
          >Aplicar cambios</button>

          <button
            @click="intentarCerrar"
            class="mt-1.5 min-h-12 w-full cursor-pointer text-[14px] font-semibold text-tinta/50"
          >{{ hayCambios ? "Descartar y cerrar" : "Cerrar" }}</button>
        </footer>
      </div>
    </div>

    <!-- Confirmación antes de mandar a cocina -->
    <div
      v-if="confirmando"
      class="fixed inset-0 z-[60] flex items-end justify-center bg-tinta/60 backdrop-blur-sm sm:items-center"
      @click.self="confirmando = false"
    >
      <div class="w-full rounded-t-[26px] bg-lienzo p-6 sm:max-w-sm sm:rounded-[26px]">
        <h3 class="font-display text-[24px] leading-tight font-light text-marca">
          ¿Aplicar {{ cambios.length }}
          {{ cambios.length === 1 ? "cambio" : "cambios" }}?
        </h3>
        <p class="mt-2 text-[14px] leading-snug text-tinta/65">
          La cocina lo verá marcado en rojo de inmediato.
        </p>

        <ul class="mt-4 max-h-52 overflow-y-auto rounded-2xl border border-marca/12 bg-white p-3.5">
          <li v-for="(c, i) in cambios" :key="i" class="py-1 text-[13.5px] font-semibold">
            <template v-if="c.tipo === 'destino'">
              Mover a {{ c.es_domicilio ? "Domicilio" : (mesas.find((m) => m.codigo === c.mesa)?.nombre ?? "otra mesa") }}
            </template>
            <template v-else-if="c.tipo === 'agregar'">+ {{ c.cantidad }}× {{ c.plato.nombre }}</template>
            <template v-else-if="c.tipo === 'quitar'">
              − {{ abierto?.detalles.find((d) => d.id === c.detalle_id)?.nombre }}
            </template>
            <template v-else-if="c.tipo === 'cantidad'">
              {{ abierto?.detalles.find((d) => d.id === c.detalle_id)?.nombre }} → {{ c.cantidad }}×
            </template>
            <template v-else-if="c.tipo === 'observacion'">
              {{ abierto?.detalles.find((d) => d.id === c.detalle_id)?.nombre }}:
              {{ c.observacion || "sin nota" }}
            </template>
          </li>
        </ul>

        <div class="mt-5 grid gap-2">
          <button
            @click="aplicarCambios" :disabled="aplicando"
            class="min-h-14 cursor-pointer rounded-2xl bg-marca text-[15px] font-bold text-lienzo disabled:opacity-50"
          >{{ aplicando ? "Aplicando…" : "Sí, aplicar" }}</button>
          <button
            @click="confirmando = false"
            class="min-h-12 cursor-pointer text-[14px] font-semibold text-tinta/50"
          >Volver</button>
        </div>
      </div>
    </div>

    <!-- Descartar: solo aparece si hay algo que perder -->
    <div
      v-if="descartando"
      class="fixed inset-0 z-[60] flex items-end justify-center bg-tinta/60 backdrop-blur-sm sm:items-center"
      @click.self="descartando = false"
    >
      <div class="w-full rounded-t-[26px] bg-lienzo p-6 sm:max-w-sm sm:rounded-[26px]">
        <h3 class="font-display text-[24px] leading-tight font-light text-marca">
          ¿Descartar {{ cambios.length }}
          {{ cambios.length === 1 ? "cambio" : "cambios" }}?
        </h3>
        <p class="mt-2 text-[14px] leading-snug text-tinta/65">
          No se aplicó ninguno todavía. El pedido queda como estaba.
        </p>
        <div class="mt-5 grid gap-2">
          <button
            @click="descartarCambios"
            class="min-h-14 cursor-pointer rounded-2xl bg-alerta text-[15px] font-bold text-white"
          >Sí, descartar</button>
          <button
            @click="descartando = false"
            class="min-h-12 cursor-pointer text-[14px] font-semibold text-tinta/50"
          >Seguir editando</button>
        </div>
      </div>
    </div>
  </MarcoInterno>
</template>
