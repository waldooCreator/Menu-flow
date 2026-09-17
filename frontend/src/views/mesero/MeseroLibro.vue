<script setup>
/**
 * El libro de caja (SPEC-014): todo lo que entró y salió de cada caja, con
 * filtros por fecha, caja y tipo.
 *
 * Existe para una pregunta concreta: **¿cuadra lo que dice el sistema con lo
 * que dice el banco?** Por eso los totales son del rango filtrado completo,
 * no de las filas que caben en pantalla — sumar la lista a mano es justo lo
 * que este libro evita.
 *
 * No hay editar ni borrar, a propósito (SPEC-014, regla 3): un error se
 * corrige con el movimiento contrario, nunca reescribiendo el original. Por
 * eso el traslado entre cajas también vive aquí — es la operación legítima
 * para mover plata sin tocar nada.
 */
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { listarMovimientos, trasladarEntreCajas, listarCajas } from "../../api/caja";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const movimientos = ref([]);
const totales = ref({ ingresos: 0, egresos: 0, neto: 0, cantidad: 0 });
const cajas = ref([]);
const cargando = ref(true);
const error = ref(null);
const aviso = ref(null);

// Filtros. Arranca sin rango: el caso más común al abrir es "qué pasó hoy",
// y lo último es exactamente eso.
const desde = ref("");
const hasta = ref("");
const cajaFiltro = ref("");
const tipoFiltro = ref("");

// "Más filtros" (SPEC-024): buscar un movimiento concreto cuando ya hay meses
// de historia. Plegados por defecto para no llenar el teléfono de campos.
const masFiltrosAbierto = ref(false);
const montoExacto = ref("");
const montoMin = ref("");
const montoMax = ref("");
const texto = ref("");
const conceptoFiltro = ref("");
const autorFiltro = ref("");
const personas = ref([]);
const hayMas = ref(false);
const cargandoMas = ref(false);

const CONCEPTOS = [
  ["venta", "Venta"], ["anulacion", "Anulación"], ["gasto", "Gasto"], ["traslado", "Traslado"],
  ["fondo_inicial", "Fondo inicial"], ["saldo_inicial", "Saldo inicial"],
  ["retiro_cierre", "Retiro al cierre"], ["diferencia_arqueo", "Diferencia de arqueo"], ["otro", "Otro"],
];

/** Cuántos de los filtros plegados están puestos: se lee en el botón cerrado. */
const filtrosOcultos = computed(() =>
  [montoExacto, montoMin, montoMax, texto, conceptoFiltro, autorFiltro]
    .filter((f) => String(f.value).trim() !== "").length
);

// Traslado entre cajas
const panelTraslado = ref(false);
const trasOrigen = ref(null);
const trasDestino = ref(null);
const trasMonto = ref(null);
const trasDescripcion = ref("");
const trasladando = ref(false);

const moneda = { format: formatearMoneda };

const hayFiltros = computed(() =>
  !!(desde.value || hasta.value || cajaFiltro.value || tipoFiltro.value) || filtrosOcultos.value > 0
);

/** Los movimientos agrupados por día, que es como se lee un libro. */
const porDia = computed(() => {
  const mapa = new Map();
  for (const m of movimientos.value) {
    const dia = new Date(m.creado).toLocaleDateString("es-CO",
      { weekday: "long", day: "numeric", month: "long" });
    if (!mapa.has(dia)) mapa.set(dia, []);
    mapa.get(dia).push(m);
  }
  return [...mapa.entries()].map(([dia, items]) => ({ dia, items }));
});

function filtros() {
  return {
    desde: desde.value, hasta: hasta.value, caja: cajaFiltro.value, tipo: tipoFiltro.value,
    // Con valor exacto no se mandan mínimo ni máximo: el servidor tampoco los usaría.
    monto: montoExacto.value,
    monto_min: montoExacto.value ? "" : montoMin.value,
    monto_max: montoExacto.value ? "" : montoMax.value,
    q: texto.value.trim(), concepto: conceptoFiltro.value, autor: autorFiltro.value,
  };
}

async function cargar() {
  error.value = null;
  try {
    const r = await listarMovimientos(filtros());
    movimientos.value = r.movimientos ?? [];
    totales.value = r.totales ?? { ingresos: 0, egresos: 0, neto: 0, cantidad: 0 };
    hayMas.value = r.hay_mas ?? false;
    personas.value = r.personas ?? [];
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo cargar el libro.";
  } finally {
    cargando.value = false;
  }
}

/** La siguiente tanda del mismo filtro, sumada al final (SPEC-024). */
async function cargarMas() {
  cargandoMas.value = true;
  try {
    const r = await listarMovimientos({ ...filtros(), desde_fila: movimientos.value.length });
    movimientos.value = [...movimientos.value, ...(r.movimientos ?? [])];
    hayMas.value = r.hay_mas ?? false;
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudieron cargar más movimientos.";
  } finally {
    cargandoMas.value = false;
  }
}

// El texto y los montos se buscan al dejar de escribir, no con cada tecla.
let espera = null;
watch([texto, montoExacto, montoMin, montoMax], () => {
  clearTimeout(espera);
  espera = setTimeout(cargar, 400);
});

function limpiarFiltros() {
  desde.value = hasta.value = cajaFiltro.value = tipoFiltro.value = "";
  montoExacto.value = montoMin.value = montoMax.value = texto.value = "";
  conceptoFiltro.value = autorFiltro.value = "";
  clearTimeout(espera);
  cargar();
}

/** Atajo: el rango de hoy, que es el que más se usa al cuadrar. */
function hoy() {
  const d = new Date();
  const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  desde.value = hasta.value = iso;
  cargar();
}

async function hacerTraslado() {
  if (trasOrigen.value === trasDestino.value) {
    error.value = "El origen y el destino son la misma caja.";
    return;
  }
  error.value = null;
  trasladando.value = true;
  try {
    const r = await trasladarEntreCajas(
      trasOrigen.value, trasDestino.value, Number(trasMonto.value), trasDescripcion.value);
    aviso.value = `${r.origen.caja} queda en ${moneda.format(r.origen.saldo)} · `
      + `${r.destino.caja} en ${moneda.format(r.destino.saldo)}`;
    setTimeout(() => (aviso.value = null), 6000);
    trasMonto.value = null;
    trasDescripcion.value = "";
    panelTraslado.value = false;
    await Promise.all([cargar(), cargarCajas()]);
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo hacer el traslado.";
  } finally {
    trasladando.value = false;
  }
}

async function cargarCajas() {
  cajas.value = await listarCajas();
  if (trasOrigen.value === null) trasOrigen.value = cajas.value[0]?.id ?? null;
  if (trasDestino.value === null) trasDestino.value = cajas.value[1]?.id ?? null;
}

function hora(iso) {
  return new Date(iso).toLocaleTimeString("es-CO",
    { hour: "2-digit", minute: "2-digit" });
}

onMounted(async () => {
  // Activos enlaza aquí con `?caja=` para mostrar de dónde salió ese saldo
  // (SPEC-020). Se aplica ANTES de cargar, o se vería primero el libro
  // completo y luego un salto al filtrado.
  const desdeActivos = Number(useRoute().query.caja);
  if (desdeActivos) cajaFiltro.value = desdeActivos;

  await Promise.all([cargar(), cargarCajas()]);
});
</script>

<template>
  <MarcoInterno titulo="Libro de caja" ancho="max-w-4xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <p v-if="error" class="mb-4 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
      {{ error }}
    </p>
    <p v-if="aviso" class="mb-4 rounded-xl bg-emerald-50 px-3.5 py-2.5 text-[13px] font-semibold text-emerald-700">
      {{ aviso }}
    </p>

    <!-- ===== Totales del rango ===== -->
    <!-- Apilados en telefono: tres columnas dejaban 71px para un numero de
         128px (SPEC-022 A3/B2). Mismo patron que Ventas. -->
    <div class="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
      <div class="rounded-2xl border border-marca/12 bg-white p-4">
        <p class="text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Entró</p>
        <p class="mt-1.5 font-display text-[20px] leading-none font-light break-words tabular-nums text-emerald-700 sm:text-[22px]">
          {{ moneda.format(totales.ingresos) }}
        </p>
      </div>
      <div class="rounded-2xl border border-marca/12 bg-white p-4">
        <p class="text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Salió</p>
        <p class="mt-1.5 font-display text-[20px] leading-none font-light break-words tabular-nums text-alerta sm:text-[22px]">
          {{ moneda.format(totales.egresos) }}
        </p>
      </div>
      <div class="rounded-2xl border border-marca/12 bg-white p-4">
        <p class="text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Neto</p>
        <p class="mt-1.5 font-display text-[20px] leading-none font-light break-words tabular-nums text-marca sm:text-[22px]">
          {{ moneda.format(totales.neto) }}
        </p>
      </div>
    </div>

    <!-- ===== Filtros ===== -->
    <div class="mt-3 rounded-2xl border border-marca/12 bg-white p-4">
      <div class="flex flex-wrap items-end gap-2.5">
        <div>
          <label for="desde" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Desde</label>
          <input
            id="desde" v-model="desde" type="date" @change="cargar"
            class="min-h-11 rounded-xl border border-marca/20 px-3 text-[13.5px] outline-none focus:border-marca"
          />
        </div>
        <div>
          <label for="hasta" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Hasta</label>
          <input
            id="hasta" v-model="hasta" type="date" @change="cargar"
            class="min-h-11 rounded-xl border border-marca/20 px-3 text-[13.5px] outline-none focus:border-marca"
          />
        </div>
        <div>
          <label for="f-caja" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Caja</label>
          <select
            id="f-caja" v-model="cajaFiltro" @change="cargar"
            class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
          >
            <option value="">Todas</option>
            <option v-for="c in cajas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
          </select>
        </div>
        <div>
          <label for="f-tipo" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Tipo</label>
          <select
            id="f-tipo" v-model="tipoFiltro" @change="cargar"
            class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
          >
            <option value="">Todo</option>
            <option value="ingreso">Solo lo que entró</option>
            <option value="egreso">Solo lo que salió</option>
          </select>
        </div>

        <button
          @click="hoy"
          class="min-h-11 cursor-pointer rounded-full border border-marca/20 px-4 text-[12.5px] font-semibold text-marca hover:border-marca"
        >Hoy</button>
        <button
          v-if="hayFiltros" @click="limpiarFiltros"
          class="min-h-11 cursor-pointer rounded-full px-3 text-[12.5px] font-semibold text-tinta/50 hover:text-marca"
        >Quitar filtros</button>

        <button
          @click="masFiltrosAbierto = !masFiltrosAbierto" :aria-expanded="masFiltrosAbierto"
          class="min-h-11 cursor-pointer rounded-full border px-4 text-[12.5px] font-semibold"
          :class="filtrosOcultos ? 'border-marca bg-marca text-lienzo' : 'border-marca/20 text-marca hover:border-marca'"
        >Más filtros<template v-if="filtrosOcultos"> ({{ filtrosOcultos }})</template></button>

        <button
          @click="panelTraslado = !panelTraslado"
          class="ml-auto min-h-11 cursor-pointer rounded-full border-2 border-marca px-4 text-[12.5px] font-bold text-marca"
        >Trasladar entre cajas</button>
      </div>

      <!-- Más filtros (SPEC-024) -->
      <div v-if="masFiltrosAbierto" class="mt-4 grid grid-cols-1 gap-2.5 border-t border-marca/12 pt-4 sm:grid-cols-2 lg:grid-cols-3">
        <div class="sm:col-span-2 lg:col-span-3">
          <label for="f-texto" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Buscar</label>
          <input
            id="f-texto" v-model="texto" type="search" maxlength="100"
            placeholder="Descripción o número de tiquete (Ef-2026-00123 o 123)"
            class="min-h-11 w-full rounded-xl border border-marca/20 px-3 text-[13.5px] outline-none focus:border-marca"
          />
        </div>
        <div>
          <label for="f-exacto" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Valor exacto</label>
          <input
            id="f-exacto" v-model="montoExacto" type="number" min="0" inputmode="numeric" placeholder="100000"
            class="min-h-11 w-full rounded-xl border border-marca/20 px-3 text-[13.5px] outline-none focus:border-marca"
          />
        </div>
        <div>
          <label for="f-min" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Valor desde</label>
          <input
            id="f-min" v-model="montoMin" type="number" min="0" inputmode="numeric" placeholder="0"
            :disabled="!!montoExacto"
            class="min-h-11 w-full rounded-xl border border-marca/20 px-3 text-[13.5px] outline-none focus:border-marca disabled:bg-lienzo-alt/60 disabled:opacity-60"
          />
        </div>
        <div>
          <label for="f-max" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Valor hasta</label>
          <input
            id="f-max" v-model="montoMax" type="number" min="0" inputmode="numeric" placeholder="sin tope"
            :disabled="!!montoExacto"
            class="min-h-11 w-full rounded-xl border border-marca/20 px-3 text-[13.5px] outline-none focus:border-marca disabled:bg-lienzo-alt/60 disabled:opacity-60"
          />
        </div>
        <div>
          <label for="f-concepto" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Concepto</label>
          <select
            id="f-concepto" v-model="conceptoFiltro" @change="cargar"
            class="min-h-11 w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
          >
            <option value="">Todos</option>
            <option v-for="[valor, nombre] in CONCEPTOS" :key="valor" :value="valor">{{ nombre }}</option>
          </select>
        </div>
        <div>
          <label for="f-autor" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Registró</label>
          <select
            id="f-autor" v-model="autorFiltro" @change="cargar"
            class="min-h-11 w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px]"
          >
            <option value="">Cualquiera</option>
            <option v-for="p in personas" :key="p.id" :value="p.id">{{ p.username }}</option>
          </select>
        </div>
        <p v-if="montoExacto" class="text-[12px] leading-snug text-tinta/50 sm:col-span-2 lg:col-span-3">
          Con valor exacto no se usan "desde" ni "hasta".
        </p>
      </div>

      <!-- Traslado: la forma legítima de mover plata sin reescribir nada -->
      <div v-if="panelTraslado" class="mt-4 border-t border-marca/12 pt-4">
        <p class="mb-3 text-[12.5px] leading-snug text-tinta/55">
          Consignar el efectivo en el banco, por ejemplo. Deja
          <strong>dos movimientos</strong>: uno que sale del origen y otro que entra al
          destino, así los dos saldos quedan bien solos.
        </p>
        <div class="flex flex-wrap items-end gap-2.5">
          <div>
            <label for="t-origen" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">De</label>
            <select id="t-origen" v-model="trasOrigen" class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[14px]">
              <option v-for="c in cajas" :key="c.id" :value="c.id">{{ c.nombre }} · {{ moneda.format(c.saldo) }}</option>
            </select>
          </div>
          <div>
            <label for="t-destino" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">A</label>
            <select id="t-destino" v-model="trasDestino" class="min-h-11 cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[14px]">
              <option v-for="c in cajas" :key="c.id" :value="c.id">{{ c.nombre }} · {{ moneda.format(c.saldo) }}</option>
            </select>
          </div>
          <input
            v-model="trasMonto" type="number" min="1" inputmode="numeric" placeholder="Monto"
            class="min-h-11 w-36 rounded-xl border border-marca/20 px-3 text-[14px] outline-none focus:border-marca"
          />
          <input
            v-model="trasDescripcion" type="text" maxlength="200" placeholder="Consignación del día…"
            class="min-h-11 min-w-48 flex-1 rounded-xl border border-marca/20 px-3 text-[14px] outline-none focus:border-marca"
          />
          <button
            @click="hacerTraslado" :disabled="trasladando || !trasMonto"
            class="min-h-11 cursor-pointer rounded-xl bg-marca px-5 text-[13.5px] font-bold text-lienzo disabled:opacity-50"
          >{{ trasladando ? "…" : "Trasladar" }}</button>
        </div>
      </div>
    </div>

    <!-- ===== El libro ===== -->
    <p v-if="cargando" class="py-14 text-center text-tinta/50">Cargando…</p>

    <template v-else>
      <p v-if="!movimientos.length" class="py-14 text-center text-[14px] text-tinta/50">
        {{ hayFiltros ? "Nada en ese rango." : "Todavía no hay movimientos." }}
      </p>

      <section v-for="grupo in porDia" :key="grupo.dia" class="mt-6">
        <h2 class="mb-2 text-[11px] font-semibold tracking-[0.14em] text-marca/60 uppercase">
          {{ grupo.dia }}
        </h2>
        <ul class="overflow-hidden rounded-2xl border border-marca/12 bg-white">
          <li
            v-for="m in grupo.items" :key="m.id"
            class="flex items-center gap-3 border-b border-marca/8 px-4 py-3 last:border-b-0"
          >
            <!-- La flecha dice de un vistazo si entró o salió -->
            <span
              class="grid size-8 shrink-0 place-items-center rounded-full text-[15px] font-bold"
              :class="m.tipo === 'ingreso' ? 'bg-emerald-50 text-emerald-700' : 'bg-alerta/10 text-alerta'"
            >{{ m.tipo === 'ingreso' ? '↓' : '↑' }}</span>

            <div class="min-w-0 flex-1">
              <p class="line-clamp-2 text-[14px] leading-snug font-semibold text-tinta">
                {{ m.descripcion || m.concepto_texto }}
                <!-- El tiquete: es lo que se busca cuando reclaman una factura (SPEC-024) -->
                <span v-if="m.tiquete" class="ml-1 rounded-full bg-marca-suave px-2 py-0.5 text-[11px] font-bold whitespace-nowrap text-marca">{{ m.tiquete }}</span>
              </p>
              <p class="line-clamp-2 text-[12px] leading-snug text-tinta/50">
                <!-- La categoría va primero: en un gasto es lo que se busca
                     al repasar el libro (SPEC-020). -->
                <span v-if="m.categoria" class="font-semibold text-marca/70">{{ m.categoria }} · </span>
                {{ hora(m.creado) }} · {{ m.caja }} · {{ m.autor }}
                <span v-if="m.fuera_de_turno" class="font-semibold text-amber-700">· fuera de turno</span>
              </p>
            </div>

            <span
              class="shrink-0 text-[15px] font-semibold tabular-nums"
              :class="m.tipo === 'ingreso' ? 'text-emerald-700' : 'text-alerta'"
            >{{ m.tipo === 'ingreso' ? '+' : '−' }}{{ moneda.format(m.monto) }}</span>
          </li>
        </ul>
      </section>

      <div v-if="movimientos.length && totales.cantidad > movimientos.length" class="mt-4 text-center">
        <p class="text-[12.5px] text-tinta/50">
          Mostrando {{ movimientos.length }} de {{ totales.cantidad }}.
          Los totales de arriba son de todo el filtro.
        </p>
        <button
          v-if="hayMas" @click="cargarMas" :disabled="cargandoMas"
          class="mt-2.5 min-h-11 cursor-pointer rounded-full border border-marca/20 px-5 text-[13px] font-semibold text-marca hover:border-marca disabled:opacity-50"
        >{{ cargandoMas ? "Cargando…" : `Cargar ${Math.min(100, totales.cantidad - movimientos.length)} más (quedan ${totales.cantidad - movimientos.length})` }}</button>
      </div>
    </template>
  </MarcoInterno>
</template>
