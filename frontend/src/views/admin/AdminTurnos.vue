<script setup>
/**
 * Historial de turnos y sus cuadres (SPEC-014), con búsqueda (SPEC-024).
 *
 * Vive en el panel de administración, no en la pantalla de Caja, y eso es
 * deliberado: al revisar el sistema que se va a reemplazar, su "Reporte de
 * turnos" es la única sección de Cajeros que el rol `cajero` NO ve — solo
 * jefe y administrador. Tiene sentido y se copia: quien maneja la plata no
 * audita su propio cuadre.
 *
 * La diferencia se muestra tal cual quedó guardada. No se recalcula ni se
 * ajusta — ese número es justamente el que interesa (SPEC-014, regla 6).
 *
 * Todo se filtra en el servidor (SPEC-024, regla 1). Antes llegaban los
 * últimos 100 y se filtraban aquí: el turno 101 no se podía ver nunca.
 */
import { computed, onMounted, ref, watch } from "vue";
import { listarTurnos } from "../../api/caja";
import MarcoInterno from "../../components/MarcoInterno.vue";
import AdminPestanas from "../../components/AdminPestanas.vue";
import { formatearMoneda } from "../../lib/tema";

const turnos = ref([]);
const resumen = ref({ total: 0, con_faltante: 0, faltante: 0, con_sobrante: 0, sobrante: 0 });
const personas = ref({ responsables: [], cerradores: [] });
const hayMas = ref(false);
const cargando = ref(true);
const cargandoMas = ref(false);
const error = ref(null);

const desde = ref("");
const hasta = ref("");
const responsable = ref("");
const cerradoPor = ref("");
const estado = ref("");
const cuadre = ref("");
const diferenciaMin = ref("");
const orden = ref("recientes");

const CUADRES = [
  ["", "Todos"], ["falto", "Faltó"], ["sobro", "Sobró"], ["cuadro", "Cuadró"], ["sin_contar", "Sin contar"],
];

const moneda = { format: formatearMoneda };

const hayFiltros = computed(() =>
  [desde, hasta, responsable, cerradoPor, estado, cuadre, diferenciaMin].some((f) => f.value !== "")
  || orden.value !== "recientes"
);

function filtros() {
  return {
    desde: desde.value, hasta: hasta.value, responsable: responsable.value,
    cerrado_por: cerradoPor.value, estado: estado.value, cuadre: cuadre.value,
    diferencia_min: diferenciaMin.value, orden: orden.value,
  };
}

async function cargar() {
  error.value = null;
  try {
    const r = await listarTurnos(filtros());
    turnos.value = r.turnos;
    resumen.value = r.resumen;
    personas.value = r.personas;
    hayMas.value = r.hay_mas;
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo cargar el historial.";
  } finally {
    cargando.value = false;
  }
}

async function cargarMas() {
  cargandoMas.value = true;
  try {
    const r = await listarTurnos({ ...filtros(), desde_fila: turnos.value.length });
    turnos.value = [...turnos.value, ...r.turnos];
    hayMas.value = r.hay_mas;
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudieron cargar más turnos.";
  } finally {
    cargandoMas.value = false;
  }
}

// Las listas se aplican al elegir; el monto, al dejar de escribir.
watch([desde, hasta, responsable, cerradoPor, estado, cuadre, orden], cargar);
let espera = null;
watch(diferenciaMin, () => {
  clearTimeout(espera);
  espera = setTimeout(cargar, 400);
});

function limpiar() {
  desde.value = hasta.value = responsable.value = cerradoPor.value = "";
  estado.value = cuadre.value = diferenciaMin.value = "";
  orden.value = "recientes";
}

function fecha(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CO",
    { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Turnos" ancho="max-w-5xl">
    <AdminPestanas />

    <p v-if="error" class="mb-4 rounded-lg bg-alerta/8 px-3.5 py-2.5 text-sm font-semibold text-alerta">{{ error }}</p>

    <!-- ===== Filtros (SPEC-024) ===== -->
    <div class="mb-4 rounded-xl border border-panel-borde bg-white p-3.5">
      <div class="grid grid-cols-2 gap-2.5 md:grid-cols-4">
        <label class="text-[11px] font-semibold tracking-[0.08em] text-panel-tinta/55 uppercase">
          Desde
          <input v-model="desde" type="date" class="mt-1 min-h-11 w-full rounded-lg border border-panel-borde px-2.5 text-[13px] font-normal tracking-normal text-panel-tinta normal-case outline-none focus:border-panel-marca" />
        </label>
        <label class="text-[11px] font-semibold tracking-[0.08em] text-panel-tinta/55 uppercase">
          Hasta
          <input v-model="hasta" type="date" class="mt-1 min-h-11 w-full rounded-lg border border-panel-borde px-2.5 text-[13px] font-normal tracking-normal text-panel-tinta normal-case outline-none focus:border-panel-marca" />
        </label>
        <label class="text-[11px] font-semibold tracking-[0.08em] text-panel-tinta/55 uppercase">
          A nombre de
          <select v-model="responsable" class="mt-1 min-h-11 w-full cursor-pointer rounded-lg border border-panel-borde bg-white px-2.5 text-[13px] font-normal tracking-normal text-panel-tinta normal-case">
            <option value="">Cualquiera</option>
            <option v-for="p in personas.responsables" :key="p.id" :value="p.id">{{ p.username }}</option>
          </select>
        </label>
        <label class="text-[11px] font-semibold tracking-[0.08em] text-panel-tinta/55 uppercase">
          Cerrado por
          <select v-model="cerradoPor" class="mt-1 min-h-11 w-full cursor-pointer rounded-lg border border-panel-borde bg-white px-2.5 text-[13px] font-normal tracking-normal text-panel-tinta normal-case">
            <option value="">Cualquiera</option>
            <option v-for="p in personas.cerradores" :key="p.id" :value="p.id">{{ p.username }}</option>
          </select>
        </label>
        <label class="text-[11px] font-semibold tracking-[0.08em] text-panel-tinta/55 uppercase">
          Estado
          <select v-model="estado" class="mt-1 min-h-11 w-full cursor-pointer rounded-lg border border-panel-borde bg-white px-2.5 text-[13px] font-normal tracking-normal text-panel-tinta normal-case">
            <option value="">Todos</option>
            <option value="abierto">Abiertos</option>
            <option value="cerrado">Cerrados</option>
          </select>
        </label>
        <label class="text-[11px] font-semibold tracking-[0.08em] text-panel-tinta/55 uppercase">
          Diferencia de
          <input
            v-model="diferenciaMin" type="number" min="0" inputmode="numeric" placeholder="$ o más"
            class="mt-1 min-h-11 w-full rounded-lg border border-panel-borde px-2.5 text-[13px] font-normal tracking-normal text-panel-tinta normal-case outline-none focus:border-panel-marca"
          />
        </label>
        <label class="col-span-2 text-[11px] font-semibold tracking-[0.08em] text-panel-tinta/55 uppercase">
          Ordenar
          <select v-model="orden" class="mt-1 min-h-11 w-full cursor-pointer rounded-lg border border-panel-borde bg-white px-2.5 text-[13px] font-normal tracking-normal text-panel-tinta normal-case">
            <option value="recientes">Más recientes primero</option>
            <option value="faltante">Mayor faltante primero</option>
            <option value="sobrante">Mayor sobrante primero</option>
          </select>
        </label>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-1.5" role="radiogroup" aria-label="Cuadre">
        <button
          v-for="[valor, nombre] in CUADRES" :key="valor"
          role="radio" :aria-checked="cuadre === valor" @click="cuadre = valor"
          class="min-h-11 cursor-pointer rounded-full border px-4 text-[12.5px] font-semibold"
          :class="cuadre === valor ? 'border-panel-marca bg-panel-marca text-white' : 'border-panel-borde text-panel-tinta/70 hover:border-panel-marca'"
        >{{ nombre }}</button>
        <button
          v-if="hayFiltros" @click="limpiar"
          class="ml-auto min-h-11 cursor-pointer rounded-full px-3 text-[12.5px] font-semibold text-panel-tinta/50 hover:text-panel-marca"
        >Quitar filtros</button>
      </div>
    </div>

    <p v-if="cargando" class="py-10 text-center text-panel-tinta/50">Cargando…</p>

    <template v-else>
      <!-- Resumen del filtro completo, no de lo que se ve (SPEC-024, regla 2) -->
      <p class="mb-3 text-[13px] leading-relaxed text-panel-tinta/65">
        <strong class="text-panel-tinta">{{ resumen.total }} {{ resumen.total === 1 ? "turno" : "turnos" }}</strong>
        <template v-if="resumen.con_faltante">
          · <strong class="text-alerta">{{ resumen.con_faltante }} con faltante</strong> por {{ moneda.format(resumen.faltante) }}
        </template>
        <template v-if="resumen.con_sobrante">
          · <strong class="text-amber-700">{{ resumen.con_sobrante }} con sobrante</strong> por {{ moneda.format(resumen.sobrante) }}
        </template>
      </p>

      <p v-if="!turnos.length" class="py-10 text-center text-[14px] text-panel-tinta/50">
        {{ hayFiltros ? "Ningún turno cumple esos filtros." : "Todavía no hay turnos." }}
      </p>

      <div v-else class="overflow-x-auto">
        <table class="w-full min-w-[46rem] border-collapse text-[13px]">
          <thead>
            <tr class="border-b border-panel-borde text-left text-[11px] tracking-[0.10em] text-panel-tinta/55 uppercase">
              <th class="py-2.5 pr-3 font-semibold">Turno</th>
              <th class="py-2.5 pr-3 font-semibold">Abierto</th>
              <th class="py-2.5 pr-3 font-semibold">Cerrado</th>
              <th class="py-2.5 pr-3 text-right font-semibold">Esperado</th>
              <th class="py-2.5 pr-3 text-right font-semibold">Contado</th>
              <th class="py-2.5 text-right font-semibold">Diferencia</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in turnos" :key="t.id" class="border-b border-panel-borde/60">
              <td class="py-3 pr-3">
                <p class="font-semibold">Turno de {{ t.responsable }} #{{ t.id }}</p>
                <p v-if="t.cerrado_por" class="text-[11.5px] text-amber-700">
                  cerrado por {{ t.cerrado_por }}
                </p>
                <p v-if="t.observacion_cierre" class="text-[11.5px] text-panel-tinta/50">
                  {{ t.observacion_cierre }}
                </p>
              </td>
              <td class="py-3 pr-3 text-panel-tinta/70">{{ fecha(t.abierto_en) }}</td>
              <td class="py-3 pr-3">
                <span v-if="t.estado === 'abierto'" class="rounded-full bg-emerald-50 px-2.5 py-1 text-[11.5px] font-bold text-emerald-700">
                  Abierto
                </span>
                <span v-else class="text-panel-tinta/70">{{ fecha(t.cerrado_en) }}</span>
              </td>
              <td class="py-3 pr-3 text-right tabular-nums">
                {{ moneda.format(t.cuadre.esperado_efectivo) }}
              </td>
              <td class="py-3 pr-3 text-right tabular-nums text-panel-tinta/70">
                {{ t.cuadre.efectivo_contado === null ? "—" : moneda.format(t.cuadre.efectivo_contado) }}
              </td>
              <td class="py-3 text-right tabular-nums font-semibold">
                <span
                  v-if="t.cuadre.diferencia !== null"
                  :class="t.cuadre.diferencia === 0 ? 'text-emerald-700'
                    : t.cuadre.diferencia > 0 ? 'text-amber-700' : 'text-alerta'"
                >
                  {{ t.cuadre.diferencia === 0 ? "Cuadró"
                    : t.cuadre.diferencia > 0 ? `Sobró ${moneda.format(t.cuadre.diferencia)}`
                    : `Faltó ${moneda.format(Math.abs(t.cuadre.diferencia))}` }}
                </span>
                <span v-else class="text-panel-tinta/40">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="hayMas" class="mt-4 text-center">
        <p class="text-[12.5px] text-panel-tinta/50">Mostrando {{ turnos.length }} de {{ resumen.total }}.</p>
        <button
          @click="cargarMas" :disabled="cargandoMas"
          class="mt-2.5 min-h-11 cursor-pointer rounded-full border border-panel-borde px-5 text-[13px] font-semibold text-panel-marca hover:border-panel-marca disabled:opacity-50"
        >{{ cargandoMas ? "Cargando…" : `Cargar ${Math.min(25, resumen.total - turnos.length)} más (quedan ${resumen.total - turnos.length})` }}</button>
      </div>
    </template>
  </MarcoInterno>
</template>
