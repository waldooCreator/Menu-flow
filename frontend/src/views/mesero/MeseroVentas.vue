<script setup>
/**
 * Historial de ventas (SPEC-015): qué se vendió, cuándo, por qué medio y en
 * qué mesa.
 *
 * "Venta" aquí es una cuenta que se cobró. Nada que ver con la DIAN — esto es
 * el historial interno, no un documento tributario.
 *
 * La regla que manda el diseño: **la propina nunca se suma al total de
 * ventas.** Es de los meseros, no del restaurante; mezclarlas le haría creer
 * al dueño que vendió más de lo que vendió. Por eso hay dos números y no uno:
 * lo vendido (la comida) y lo cobrado (lo que entró a la caja).
 */
import { computed, nextTick, onMounted, ref } from "vue";
import {
  exportarVentas, listarVentas, obtenerConsolidado, obtenerCuenta,
  obtenerTiquete, obtenerTiquetes,
} from "../../api/cuentas";
import { listarCajas } from "../../api/caja";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const ventas = ref([]);
const totales = ref({ vendido: 0, impuestos: 0, propinas: 0, cobrado: 0, cantidad: 0, anuladas: 0 });
const porMedioPago = ref([]);
const cajas = ref([]);
const cargando = ref(true);
const error = ref(null);

// Filtros
const desde = ref("");
const hasta = ref("");
const medioPago = ref("");
const tipo = ref("");
const mesa = ref("");
const cobradoPor = ref("");
const montoMin = ref("");
const montoMax = ref("");
const horaDesde = ref("");
const horaHasta = ref("");
const orden = ref("fecha");
const verAnuladas = ref(false);
const atajoActivo = ref("hoy");

// Los filtros de detalle van plegados: la mayoria de las veces solo se usa la
// fecha, y mostrarlos todos de entrada convertiria la pantalla en un
// formulario antes de dejar ver una sola venta.
const filtrosAbiertos = ref(false);
// Opciones de los desplegables — vienen con la respuesta, solo mesas y
// personas que de verdad tienen ventas.
const opciones = ref({ mesas: [], cobradores: [] });

// Detalle de una venta
const detalle = ref(null);
const cargandoDetalle = ref(false);

// Tiquetes (SPEC-016)
const seleccionadas = ref(new Set());
const tiquetes = ref([]);
const tiqueteAbierto = ref(false);
const cargandoTiquete = ref(false);
const agrupacion = ref("medio_pago");
const consolidado = ref(null);
const cargandoConsolidado = ref(false);

const moneda = { format: formatearMoneda };

function iso(fecha) {
  return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, "0")}`
    + `-${String(fecha.getDate()).padStart(2, "0")}`;
}

/**
 * Atajos de fecha. Son la forma real de usar esto: casi nadie escribe un
 * rango a mano, todos quieren "lo de hoy" o "lo de esta semana".
 */
const ATAJOS = {
  hoy: () => { const d = new Date(); return [iso(d), iso(d)]; },
  ayer: () => {
    const d = new Date(); d.setDate(d.getDate() - 1);
    return [iso(d), iso(d)];
  },
  semana: () => {
    const hoyD = new Date();
    const inicio = new Date(hoyD);
    // La semana arranca el lunes: getDay() da 0 el domingo, por eso el ajuste.
    inicio.setDate(hoyD.getDate() - ((hoyD.getDay() + 6) % 7));
    return [iso(inicio), iso(hoyD)];
  },
  mes: () => {
    const hoyD = new Date();
    return [iso(new Date(hoyD.getFullYear(), hoyD.getMonth(), 1)), iso(hoyD)];
  },
};

function aplicarAtajo(clave) {
  atajoActivo.value = clave;
  [desde.value, hasta.value] = ATAJOS[clave]();
  cargar();
}

/** Si el usuario toca las fechas a mano, ya no hay atajo activo. */
function fechaManual() {
  atajoActivo.value = null;
  cargar();
}

const hayVentas = computed(() => ventas.value.length > 0);
const cantidadSeleccionadas = computed(() => seleccionadas.value.size);
const todasSeleccionadas = computed(() =>
  ventas.value.length > 0 && ventas.value.every((venta) => seleccionadas.value.has(venta.id))
);

/** Cuantos filtros de detalle estan puestos: se muestra en el boton. */
const filtrosPuestos = computed(() =>
  [mesa.value, cobradoPor.value, montoMin.value, montoMax.value,
   horaDesde.value, horaHasta.value].filter((v) => v !== "" && v != null).length
);

function limpiarDetalle() {
  mesa.value = cobradoPor.value = montoMin.value = montoMax.value = "";
  horaDesde.value = horaHasta.value = "";
  cargar();
}

function filtrosActuales() {
  return {
    desde: desde.value || null,
    hasta: hasta.value || null,
    medioPago: medioPago.value || null,
    tipo: tipo.value || null,
    mesa: mesa.value || null,
    cobradoPor: cobradoPor.value || null,
    montoMin: montoMin.value || null,
    montoMax: montoMax.value || null,
    horaDesde: horaDesde.value,
    horaHasta: horaHasta.value,
    orden: orden.value,
    incluirAnuladas: verAnuladas.value,
  };
}

async function cargar() {
  error.value = null;
  try {
    const r = await listarVentas(filtrosActuales());
    ventas.value = r.ventas ?? [];
    totales.value = r.totales;
    porMedioPago.value = r.por_medio_pago ?? [];
    opciones.value = r.opciones ?? { mesas: [], cobradores: [] };
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudieron cargar las ventas.";
  } finally {
    cargando.value = false;
  }
}

function alternarSeleccion(id) {
  const nueva = new Set(seleccionadas.value);
  if (nueva.has(id)) nueva.delete(id); else nueva.add(id);
  seleccionadas.value = nueva;
}

function alternarTodas() {
  if (todasSeleccionadas.value) {
    seleccionadas.value = new Set();
  } else {
    seleccionadas.value = new Set(ventas.value.map((venta) => venta.id));
  }
}

async function abrirTiquetes(ids) {
  if (!ids.length) return;
  cargandoTiquete.value = true;
  tiqueteAbierto.value = true;
  try {
    const respuesta = ids.length === 1
      ? { tiquetes: [await obtenerTiquete(ids[0])] }
      : await obtenerTiquetes(ids);
    tiquetes.value = respuesta.tiquetes;
    await nextTick();
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo preparar el tiquete.";
    tiqueteAbierto.value = false;
  } finally {
    cargandoTiquete.value = false;
  }
}

function imprimirTiquetes() {
  window.print();
}

function descargarTiquetes() {
  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Tiquetes de venta</title><style>body{font-family:Arial,sans-serif;max-width:760px;margin:24px auto}.tiquete{break-after:page;border-bottom:1px dashed #777;padding:20px 0}.fila{display:flex;justify-content:space-between;gap:16px}small{color:#666}</style></head><body>${tiquetes.value.map((t) => plantillaTiquete(t)).join("")}</body></html>`;
  const enlace = document.createElement("a");
  enlace.href = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
  enlace.download = tiquetes.value.length === 1 ? `tiquete-${tiquetes.value[0].numero || "venta"}.html` : "tiquetes.html";
  enlace.click();
  URL.revokeObjectURL(enlace.href);
}

function plantillaTiquete(tiquete) {
  const c = tiquete.configuracion || {};
  const items = (tiquete.items || []).map((item) =>
    `<div class="fila"><span>${item.cantidad} × ${item.nombre}</span><span>${moneda.format(item.precio * item.cantidad)}</span></div>${item.observacion ? `<small>${item.observacion}</small>` : ""}`
  ).join("");
  const vuelto = tiquete.vuelto_efectivo
    ? `<div class="fila"><span>Recibió ${moneda.format(tiquete.recibido_efectivo)} · vuelto</span><b>${moneda.format(tiquete.vuelto_efectivo)}</b></div>` : "";
  return `<article class="tiquete"><h1>${c.nombre || "Restaurante"}</h1><p>${c.nit ? `NIT ${c.nit}<br>` : ""}${c.direccion || ""}<br>${c.telefono || ""}</p><p><strong>${tiquete.numero || "Sin número"}</strong><br>${hora(tiquete.fecha)} · ${tiquete.mesa || tiquete.destino}</p>${items}<hr><div class="fila">Subtotal <b>${moneda.format(tiquete.subtotal)}</b></div>${tiquete.impuesto ? `<div class="fila">Impuesto <b>${moneda.format(tiquete.impuesto)}</b></div>` : ""}${tiquete.propina ? `<div class="fila">Propina <b>${moneda.format(tiquete.propina)}</b></div>` : ""}${tiquete.envio ? `<div class="fila">Envío <b>${moneda.format(tiquete.envio)}</b></div>` : ""}<div class="fila"><strong>Total</strong><strong>${moneda.format(tiquete.total)}</strong></div><p>${tiquete.medio_pago || ""}</p>${vuelto}<p>${c.mensaje || ""}</p></article>`;
}

async function cargarConsolidado() {
  cargandoConsolidado.value = true;
  try {
    consolidado.value = await obtenerConsolidado({ ...filtrosActuales(), agrupacion: agrupacion.value });
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo preparar el consolidado.";
  } finally {
    cargandoConsolidado.value = false;
  }
}

async function descargarExcel() {
  try {
    const respuesta = await exportarVentas(filtrosActuales());
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(respuesta.data);
    enlace.download = "ventas-filtradas.xlsx";
    enlace.click();
    URL.revokeObjectURL(enlace.href);
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo descargar Excel.";
  }
}

async function abrirDetalle(venta) {
  cargandoDetalle.value = true;
  detalle.value = { ...venta, pedidos: null };
  try {
    const completo = await obtenerCuenta(venta.id);
    detalle.value = { ...venta, pedidos: completo.pedidos ?? [] };
  } catch {
    detalle.value = { ...venta, pedidos: [] };
  } finally {
    cargandoDetalle.value = false;
  }
}

function hora(iso_) {
  if (!iso_) return "";
  return new Date(iso_).toLocaleString("es-CO",
    { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

onMounted(async () => {
  aplicarAtajo("hoy");
  cajas.value = await listarCajas();
});
</script>

<template>
  <MarcoInterno titulo="Ventas" ancho="max-w-4xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <p v-if="error" class="mb-4 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
      {{ error }}
    </p>

    <!-- ===== Los números del rango ===== -->
    <div class="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
      <div class="rounded-2xl border border-marca/12 bg-white p-4">
        <p class="text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Vendido</p>
        <p class="mt-1.5 font-display text-[22px] leading-none font-light text-marca">
          {{ moneda.format(totales.vendido) }}
        </p>
        <p class="mt-1 text-[11px] text-tinta/45">sin propina</p>
      </div>
      <div class="rounded-2xl border border-marca/12 bg-white p-4">
        <p class="text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Propinas</p>
        <p class="mt-1.5 font-display text-[22px] leading-none font-light text-amber-700">
          {{ moneda.format(totales.propinas) }}
        </p>
        <p class="mt-1 text-[11px] text-tinta/45">de los meseros</p>
      </div>
      <div class="rounded-2xl border border-marca/12 bg-white p-4">
        <p class="text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Entró a caja</p>
        <p class="mt-1.5 font-display text-[22px] leading-none font-light text-emerald-700">
          {{ moneda.format(totales.cobrado) }}
        </p>
        <p class="mt-1 text-[11px] text-tinta/45">todo incluido</p>
      </div>
      <div class="rounded-2xl border border-marca/12 bg-white p-4">
        <p class="text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Ventas</p>
        <p class="mt-1.5 font-display text-[22px] leading-none font-light text-marca">
          {{ totales.cantidad }}
        </p>
        <p v-if="totales.anuladas" class="mt-1 text-[11px] font-semibold text-alerta">
          {{ totales.anuladas }} {{ totales.anuladas === 1 ? "anulada" : "anuladas" }}
        </p>
        <p v-else class="mt-1 text-[11px] text-tinta/45">ninguna anulada</p>
      </div>
    </div>

    <!-- ===== Por medio de pago: la línea que se compara contra el banco ===== -->
    <div v-if="porMedioPago.length" class="mt-3 rounded-2xl border border-marca/12 bg-white p-4">
      <p class="mb-2.5 text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">
        Entró por cada medio
      </p>
      <ul class="flex flex-wrap gap-x-6 gap-y-2">
        <li v-for="m in porMedioPago" :key="m.medio_pago" class="text-[14px]">
          <span class="text-tinta/60">{{ m.medio_pago }}</span>
          <span class="ml-2 font-semibold tabular-nums">{{ moneda.format(m.cobrado) }}</span>
          <span class="ml-1 text-[12px] text-tinta/40">({{ m.cantidad }})</span>
        </li>
      </ul>
    </div>

    <!-- ===== Filtros ===== -->
    <div class="mt-3 rounded-2xl border border-marca/12 bg-white p-4">
      <div class="mb-3 flex flex-wrap gap-1.5">
        <button
          v-for="(_, clave) in ATAJOS" :key="clave"
          @click="aplicarAtajo(clave)"
          class="min-h-11 cursor-pointer rounded-full border px-4 text-[12.5px] font-semibold capitalize transition-colors"
          :class="atajoActivo === clave
            ? 'border-marca bg-marca text-lienzo'
            : 'border-marca/20 text-marca hover:border-marca'"
        >{{ clave === 'semana' ? 'Esta semana' : clave === 'mes' ? 'Este mes' : clave }}</button>
      </div>

      <div class="flex flex-wrap items-end gap-2.5">
        <div>
          <label for="v-desde" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Desde</label>
          <input
            id="v-desde" v-model="desde" type="date" @change="fechaManual"
            class="min-h-11 rounded-xl border border-marca/20 px-3 text-[13.5px] outline-none focus:border-marca"
          />
        </div>
        <div>
          <label for="v-hasta" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Hasta</label>
          <input
            id="v-hasta" v-model="hasta" type="date" @change="fechaManual"
            class="min-h-11 rounded-xl border border-marca/20 px-3 text-[13.5px] outline-none focus:border-marca"
          />
        </div>
        <div>
          <label for="v-medio" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Medio</label>
          <select
            id="v-medio" v-model="medioPago" @change="cargar"
            class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
          >
            <option value="">Todos</option>
            <option v-for="c in cajas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
          </select>
        </div>
        <div>
          <label for="v-tipo" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Tipo</label>
          <select
            id="v-tipo" v-model="tipo" @change="cargar"
            class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
          >
            <option value="">Todo</option>
            <option value="mesa">Mesa</option>
            <option value="domicilio">Domicilio</option>
          </select>
        </div>

        <label class="flex min-h-11 cursor-pointer items-center gap-2 text-[12.5px] font-semibold text-marca">
          <span class="-m-2.5 grid min-h-11 min-w-11 place-items-center p-2.5"><input
            v-model="verAnuladas" type="checkbox" @change="cargar"
            class="size-4 cursor-pointer accent-marca"
          /></span>
          Ver anuladas
        </label>

        <button
          @click="filtrosAbiertos = !filtrosAbiertos"
          class="ml-auto min-h-11 cursor-pointer rounded-full border px-4 text-[12.5px] font-semibold transition-colors"
          :class="filtrosPuestos
            ? 'border-marca bg-marca text-lienzo'
            : 'border-marca/20 text-marca hover:border-marca'"
        >
          Más filtros<template v-if="filtrosPuestos"> · {{ filtrosPuestos }}</template>
        </button>
      </div>

      <!-- Filtros de detalle: plegados porque la mayoría de las veces solo se
           usa la fecha. Abiertos de entrada, la pantalla sería un formulario
           antes de dejar ver una sola venta. -->
      <div v-if="filtrosAbiertos" class="mt-4 border-t border-marca/12 pt-4">
        <div class="flex flex-wrap items-end gap-2.5">
          <div>
            <label for="v-mesa" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Mesa</label>
            <select
              id="v-mesa" v-model="mesa" @change="cargar"
              class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
            >
              <option value="">Todas</option>
              <option v-for="m in opciones.mesas" :key="m.id" :value="m.id">{{ m.nombre }}</option>
            </select>
          </div>

          <div>
            <label for="v-cobrador" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Cobró</label>
            <select
              id="v-cobrador" v-model="cobradoPor" @change="cargar"
              class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
            >
              <option value="">Cualquiera</option>
              <option v-for="c in opciones.cobradores" :key="c.id" :value="c.id">{{ c.username }}</option>
            </select>
          </div>

          <div>
            <label for="v-min" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Desde $</label>
            <input
              id="v-min" v-model="montoMin" type="number" min="0" inputmode="numeric" placeholder="0"
              @change="cargar"
              class="min-h-11 w-28 rounded-xl border border-marca/20 px-3 text-right text-[13.5px] tabular-nums outline-none focus:border-marca"
            />
          </div>
          <div>
            <label for="v-max" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Hasta $</label>
            <input
              id="v-max" v-model="montoMax" type="number" min="0" inputmode="numeric" placeholder="sin tope"
              @change="cargar"
              class="min-h-11 w-28 rounded-xl border border-marca/20 px-3 text-right text-[13.5px] tabular-nums outline-none focus:border-marca"
            />
          </div>

          <div>
            <label for="v-hd" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Entre las</label>
            <select
              id="v-hd" v-model="horaDesde" @change="cargar"
              class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
            >
              <option value="">—</option>
              <option v-for="h in 24" :key="h" :value="h - 1">{{ String(h - 1).padStart(2, '0') }}:00</option>
            </select>
          </div>
          <div>
            <label for="v-hh" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Y las</label>
            <select
              id="v-hh" v-model="horaHasta" @change="cargar"
              class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
            >
              <option value="">—</option>
              <option v-for="h in 24" :key="h" :value="h - 1">{{ String(h - 1).padStart(2, '0') }}:59</option>
            </select>
          </div>

          <div>
            <label for="v-orden" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Ordenar</label>
            <select
              id="v-orden" v-model="orden" @change="cargar"
              class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
            >
              <option value="fecha">Más reciente primero</option>
              <option value="fecha_asc">Más antigua primero</option>
              <option value="monto">De mayor a menor valor</option>
              <option value="monto_asc">De menor a mayor valor</option>
            </select>
          </div>

          <button
            v-if="filtrosPuestos" @click="limpiarDetalle"
            class="min-h-11 cursor-pointer rounded-full px-3 text-[12.5px] font-semibold text-tinta/50 hover:text-marca"
          >Quitar estos filtros</button>
        </div>

        <p class="mt-3 text-[11.5px] leading-snug text-tinta/45">
          La franja horaria puede cruzar la medianoche: de 22:00 a 02:59 trae la
          noche completa.
        </p>
      </div>
    </div>

    <!-- ===== Acciones de SPEC-016 sobre el filtro actual ===== -->
    <div class="mt-3 flex flex-wrap items-center gap-2 rounded-2xl border border-marca/12 bg-white p-3">
      <label class="flex cursor-pointer items-center gap-2 text-[12.5px] font-semibold text-marca">
        <span class="-m-2.5 grid min-h-11 min-w-11 place-items-center p-2.5"><input
          type="checkbox" :checked="todasSeleccionadas" @change="alternarTodas"
          class="size-4 cursor-pointer accent-marca"
        /></span>
        Seleccionar ventas visibles
      </label>
      <span v-if="cantidadSeleccionadas" class="text-[12px] text-tinta/50">
        {{ cantidadSeleccionadas }} seleccionada{{ cantidadSeleccionadas === 1 ? '' : 's' }}
      </span>
      <button
        v-if="cantidadSeleccionadas" @click="abrirTiquetes([...seleccionadas])"
        class="min-h-11 cursor-pointer rounded-full bg-marca px-4 text-[12px] font-semibold text-lienzo"
      >Ver tiquetes</button>
      <button
        @click="cargarConsolidado"
        class="min-h-11 cursor-pointer rounded-full border border-marca/20 px-4 text-[12px] font-semibold text-marca hover:border-marca"
      >Consolidado</button>
      <button
        @click="descargarExcel"
        class="min-h-11 cursor-pointer rounded-full border border-marca/20 px-4 text-[12px] font-semibold text-marca hover:border-marca"
      >Excel</button>
    </div>

    <!-- ===== La lista ===== -->
    <p v-if="cargando" class="py-14 text-center text-tinta/50">Cargando…</p>

    <template v-else>
      <p v-if="!hayVentas" class="py-14 text-center text-[14px] text-tinta/50">
        No hay ventas en este rango.
      </p>

      <ul v-else class="mt-4 overflow-hidden rounded-2xl border border-marca/12 bg-white">
        <li
          v-for="v in ventas" :key="v.id"
           @click="abrirDetalle(v)"
           class="flex cursor-pointer items-center gap-3 border-b border-marca/8 px-4 py-3.5 transition-colors last:border-b-0 hover:bg-marca/4"
           :class="{ 'opacity-55': v.estado === 'anulada', 'bg-marca/5': seleccionadas.has(v.id) }"
         >
           <!-- Area de toque de 44px sin agrandar el dibujo (SPEC-022 C). El
                `@click.stop` en el label evita abrir la venta al marcarla. -->
           <label class="-m-2.5 grid min-h-11 min-w-11 shrink-0 cursor-pointer place-items-center p-2.5" @click.stop>
             <input
               type="checkbox" :checked="seleccionadas.has(v.id)"
               @change="alternarSeleccion(v.id)"
               class="size-4 cursor-pointer accent-marca"
             />
           </label>
           <div class="min-w-0 flex-1">
            <p class="truncate text-[14px] font-semibold text-tinta"
               :class="{ 'line-through': v.estado === 'anulada' }">
              {{ v.destino }}
            </p>
            <p class="truncate text-[12px] text-tinta/50">
              <template v-if="v.numero_tiquete"><span class="font-mono">{{ v.numero_tiquete }}</span> · </template>
              {{ hora(v.cerrada_en) }}
              <template v-if="v.cerrada_por"> · {{ v.cerrada_por }}</template>
              <span v-if="v.estado === 'anulada'" class="font-semibold text-alerta">
                · anulada: {{ v.motivo_anulacion }}
              </span>
            </p>
          </div>

          <span v-if="v.medio_pago"
                class="hidden shrink-0 rounded-full bg-marca/6 px-3 py-1 text-[11.5px] font-semibold text-marca sm:inline">
            {{ v.medio_pago }}
          </span>

          <span class="shrink-0 text-[15px] font-semibold tabular-nums"
                :class="v.estado === 'anulada' ? 'text-tinta/40 line-through' : 'text-marca'">
            {{ moneda.format(v.total) }}
          </span>
        </li>
      </ul>

      <p v-if="ventas.length >= 300" class="mt-4 text-center text-[12.5px] text-tinta/50">
        Se muestran las 300 más recientes. Los totales de arriba son del rango completo —
        filtra por fechas para ver el resto.
      </p>
    </template>

    <!-- ===== Detalle de una venta ===== -->
    <div
      v-if="detalle"
      class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/45 backdrop-blur-sm sm:items-center sm:p-4"
      @click.self="detalle = null"
    >
      <div class="max-h-[88dvh] w-full overflow-y-auto rounded-t-3xl bg-white p-6 sm:max-w-md sm:rounded-3xl">
         <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="font-display text-[24px] leading-none font-light text-marca">
              {{ detalle.destino }}
            </h3>
            <p class="mt-1.5 text-[12.5px] text-tinta/55">
              {{ hora(detalle.cerrada_en) }}
              <template v-if="detalle.cerrada_por"> · cobró {{ detalle.cerrada_por }}</template>
            </p>
          </div>
           <button
            @click="detalle = null" aria-label="Cerrar"
            class="grid size-11 shrink-0 cursor-pointer place-items-center rounded-full border border-marca/15 text-marca"
           >×</button>
         </div>

         <button
           @click="abrirTiquetes([detalle.id])"
           class="mt-4 min-h-11 w-full cursor-pointer rounded-xl bg-marca px-4 text-[13px] font-semibold text-lienzo"
         >Abrir tiquete de venta</button>

        <p v-if="detalle.estado === 'anulada'"
           class="mt-3 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
          Anulada por {{ detalle.anulada_por }}: {{ detalle.motivo_anulacion }}
        </p>

        <p v-if="cargandoDetalle" class="py-8 text-center text-[13px] text-tinta/50">Cargando…</p>

        <template v-else>
          <!-- Los platos, con el precio al que se vendieron -->
          <ul v-if="detalle.pedidos?.length" class="mt-5 border-t border-marca/12 pt-4">
            <template v-for="p in detalle.pedidos" :key="p.id">
              <li v-for="(d, i) in p.detalles" :key="`${p.id}-${i}`" class="flex gap-3 py-1.5 text-[14px]">
                <span class="shrink-0 text-tinta/45 tabular-nums">{{ d.cantidad }}×</span>
                <span class="min-w-0 flex-1">
                  {{ d.nombre }}
                  <span v-if="d.observacion" class="block text-[12px] text-tinta/50">{{ d.observacion }}</span>
                </span>
                <span class="shrink-0 tabular-nums">{{ moneda.format(d.precio * d.cantidad) }}</span>
              </li>
            </template>
          </ul>

          <ul class="mt-4 border-t border-marca/12 pt-4 text-[14px]">
            <li class="flex justify-between py-1">
              <span class="text-tinta/60">Subtotal</span>
              <span class="tabular-nums">{{ moneda.format(detalle.subtotal) }}</span>
            </li>
            <li v-if="detalle.impuesto" class="flex justify-between py-1">
              <span class="text-tinta/60">Impuesto</span>
              <span class="tabular-nums">{{ moneda.format(detalle.impuesto) }}</span>
            </li>
            <li v-if="detalle.propina" class="flex justify-between py-1">
              <span class="text-tinta/60">Propina</span>
              <span class="tabular-nums text-amber-700">{{ moneda.format(detalle.propina) }}</span>
            </li>
            <li v-if="detalle.envio" class="flex justify-between py-1">
              <span class="text-tinta/60">Envío</span>
              <span class="tabular-nums">{{ moneda.format(detalle.envio) }}</span>
            </li>
            <li class="mt-1.5 flex justify-between border-t border-marca/12 pt-2.5">
              <span class="text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">Total</span>
              <b class="text-[17px] tabular-nums text-marca">{{ moneda.format(detalle.total) }}</b>
            </li>
            <li v-if="detalle.medio_pago" class="flex justify-between pt-1.5">
              <span class="text-[12.5px] text-tinta/50">Pagado con</span>
              <span class="text-[12.5px] font-semibold text-tinta/70">{{ detalle.medio_pago }}</span>
            </li>
            <!-- Vuelto (SPEC-025): solo aparece si se cobró en efectivo con vuelto -->
            <li v-if="detalle.vuelto_efectivo" class="flex justify-between pt-1">
              <span class="text-[12.5px] text-tinta/50">Recibió {{ moneda.format(detalle.recibido_efectivo) }} · vuelto</span>
              <span class="text-[12.5px] font-semibold text-tinta/70">{{ moneda.format(detalle.vuelto_efectivo) }}</span>
            </li>
          </ul>
        </template>
      </div>
    </div>

    <!-- ===== Vista imprimible del tiquete ===== -->
    <div
      v-if="tiqueteAbierto"
      class="ticket-modal fixed inset-0 z-[60] flex items-end justify-center bg-tinta/45 backdrop-blur-sm sm:items-center sm:p-4"
      @click.self="tiqueteAbierto = false"
    >
      <div class="max-h-[92dvh] w-full overflow-y-auto rounded-t-3xl bg-white p-5 sm:max-w-lg sm:rounded-3xl">
        <div class="no-imprimir mb-4 flex items-center justify-between gap-3">
          <h3 class="font-display text-[24px] font-light text-marca">Tiquete de venta</h3>
          <button @click="tiqueteAbierto = false" class="grid size-11 cursor-pointer place-items-center rounded-full border border-marca/15 text-marca">×</button>
        </div>
        <p v-if="cargandoTiquete" class="py-10 text-center text-[13px] text-tinta/50">Preparando…</p>
        <div v-else class="ticket-reveal space-y-5">
          <article v-for="t in tiquetes" :key="t.numero || t.fecha" class="ticket-paper border-b border-dashed border-tinta/25 pb-5 last:border-b-0" :class="{ 'ticket-carta': t.configuracion?.formato === 'carta' }">
            <div class="text-center">
              <img v-if="t.configuracion?.logo" :src="t.configuracion.logo" alt="" class="mx-auto mb-2 h-12 max-w-32 object-contain" />
              <h4 class="font-display text-2xl font-light text-marca">{{ t.configuracion?.nombre || "Restaurante" }}</h4>
              <p class="text-[12px] text-tinta/60">
                <template v-if="t.configuracion?.nit">NIT {{ t.configuracion.nit }}<br /></template>
                {{ t.configuracion?.direccion }}<template v-if="t.configuracion?.telefono"><br />{{ t.configuracion.telefono }}</template>
              </p>
              <p class="mt-3 font-mono text-[13px] font-bold">{{ t.numero || "Sin número" }}</p>
              <p class="text-[12px] text-tinta/55">{{ hora(t.fecha) }} · {{ t.mesa || t.destino }}</p>
            </div>
            <ul class="mt-4 border-t border-marca/12 pt-3 text-[13px]">
              <li v-for="(item, i) in t.items" :key="i" class="flex gap-3 py-1">
                <span class="shrink-0 tabular-nums">{{ item.cantidad }}×</span>
                <span class="min-w-0 flex-1">{{ item.nombre }}<small v-if="item.observacion" class="block text-[11px] text-tinta/50">{{ item.observacion }}</small></span>
                <span class="shrink-0 tabular-nums">{{ moneda.format(item.precio * item.cantidad) }}</span>
              </li>
            </ul>
            <ul class="mt-3 border-t border-marca/12 pt-3 text-[13px]">
              <li class="flex justify-between"><span>Subtotal</span><b>{{ moneda.format(t.subtotal) }}</b></li>
              <li v-if="t.impuesto" class="flex justify-between"><span>Impuesto</span><b>{{ moneda.format(t.impuesto) }}</b></li>
              <li v-if="t.propina" class="flex justify-between"><span>Propina</span><b>{{ moneda.format(t.propina) }}</b></li>
              <li v-if="t.envio" class="flex justify-between"><span>Envío</span><b>{{ moneda.format(t.envio) }}</b></li>
              <li class="mt-2 flex justify-between border-t border-marca/12 pt-2 text-[16px] text-marca"><strong>Total</strong><strong>{{ moneda.format(t.total) }}</strong></li>
              <li class="mt-1 flex justify-between text-[12px] text-tinta/55"><span>Medio de pago</span><span>{{ t.medio_pago }}</span></li>
              <li v-if="t.vuelto_efectivo" class="mt-1 flex justify-between text-[12px] text-tinta/55"><span>Recibió {{ moneda.format(t.recibido_efectivo) }} · vuelto</span><span>{{ moneda.format(t.vuelto_efectivo) }}</span></li>
            </ul>
            <p class="mt-4 text-center text-[12px] text-tinta/55">{{ t.configuracion?.mensaje }}</p>
            <p v-if="t.estado === 'anulada'" class="mt-2 rounded-lg bg-alerta/10 px-3 py-2 text-center text-[12px] font-semibold text-alerta">ANULADO: {{ t.motivo_anulacion }}</p>
          </article>
        </div>
        <div v-if="!cargandoTiquete" class="no-imprimir mt-4 flex gap-2">
          <button @click="imprimirTiquetes" class="min-h-11 flex-1 cursor-pointer rounded-xl bg-marca px-4 text-[13px] font-semibold text-lienzo">Imprimir</button>
          <button @click="descargarTiquetes" class="min-h-11 flex-1 cursor-pointer rounded-xl border border-marca/20 px-4 text-[13px] font-semibold text-marca">Descargar</button>
        </div>
      </div>
    </div>

    <!-- ===== Consolidado ===== -->
    <div
      v-if="consolidado"
      class="fixed inset-0 z-[60] flex items-end justify-center bg-tinta/45 backdrop-blur-sm sm:items-center sm:p-4"
      @click.self="consolidado = null"
    >
      <div class="max-h-[90dvh] w-full overflow-y-auto rounded-t-3xl bg-white p-6 sm:max-w-2xl sm:rounded-3xl">
        <div class="flex items-center justify-between gap-3">
          <h3 class="font-display text-[24px] font-light text-marca">Consolidado del periodo</h3>
          <button @click="consolidado = null" class="grid size-11 cursor-pointer place-items-center rounded-full border border-marca/15 text-marca">×</button>
        </div>
        <div class="mt-4 flex flex-wrap items-center gap-2">
          <label class="text-[12px] font-semibold text-tinta/60">Agrupar por</label>
          <select v-model="agrupacion" @change="cargarConsolidado" class="min-h-11 rounded-xl border border-marca/20 px-3 text-[12px]">
            <option value="medio_pago">Medio de pago</option>
            <option value="mesa">Mesa</option>
            <option value="cobrador">Mesero</option>
          </select>
        </div>
        <p v-if="cargandoConsolidado" class="py-8 text-center text-[13px] text-tinta/50">Calculando…</p>
        <template v-else>
          <section v-for="dia in consolidado.dias" :key="dia.dia" class="mt-5 rounded-xl border border-marca/12 p-3">
            <h4 class="mb-2 text-[13px] font-bold text-marca">{{ dia.dia }}</h4>
            <div v-for="grupo in dia.grupos" :key="grupo.grupo" class="flex flex-wrap justify-between gap-2 border-t border-marca/8 py-2 text-[12.5px]">
              <span>{{ grupo.grupo }} <small class="text-tinta/45">({{ grupo.cantidad }})</small></span>
              <b class="tabular-nums">{{ moneda.format(grupo.total) }}</b>
            </div>
            <div class="mt-2 flex justify-between border-t border-marca/15 pt-2 text-[13px] font-bold"><span>Total del día</span><span>{{ moneda.format(dia.total.total) }}</span></div>
          </section>
          <div class="mt-5 flex justify-between rounded-xl bg-marca px-4 py-3 text-[14px] font-bold text-lienzo"><span>Total del periodo</span><span>{{ moneda.format(consolidado.total.total) }}</span></div>
        </template>
      </div>
    </div>
  </MarcoInterno>
</template>

<style>
.ticket-reveal {
  animation: ticket-reveal 700ms ease-out both;
}

@keyframes ticket-reveal {
  from { opacity: 0; clip-path: inset(0 0 100% 0); transform: translateY(-4px); }
  to { opacity: 1; clip-path: inset(0 0 0 0); transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .ticket-reveal { animation: none; }
}

@media print {
  body * { visibility: hidden !important; }
  .ticket-modal, .ticket-modal * { visibility: visible !important; }
  .ticket-modal { position: absolute !important; inset: 0 !important; background: white !important; }
  .ticket-modal > div { max-height: none !important; max-width: 210mm !important; margin: 0 auto !important; overflow: visible !important; border-radius: 0 !important; }
  .ticket-paper { max-width: 80mm; margin: 0 auto; }
  .ticket-paper.ticket-carta { max-width: 190mm; }
  .no-imprimir { display: none !important; }
  .ticket-paper { break-after: page; }
}
</style>
