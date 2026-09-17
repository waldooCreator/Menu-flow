<script setup>
/**
 * Tablero de una estación (SPEC-005), pensado como pantalla de cocina:
 * tarjetas grandes, ítems visibles de un vistazo, un solo botón grande por
 * tarjeta. El color aquí significa URGENCIA (el cronómetro), no marca.
 *
 * Nota de alcance: no hay estación asignada por usuario todavía (falta
 * roles finos, SPEC-007) — quien entra elige la estación de la lista.
 */
import { ref, computed, onMounted, onUnmounted } from "vue";
import {
  listarEstaciones, listarComandas, marcarEnPreparacion, marcarLista, marcarNovedadesVistas,
} from "../../api/estaciones";
import { cambiarDisponibilidad, listarPlatos } from "../../api/menu";
import { obtenerConfiguracionPublica } from "../../api/configuracion";
import MarcoInterno from "../../components/MarcoInterno.vue";

const estaciones = ref([]);
const estacionId = ref(null);
// Configuración → Operación → "Unificar estaciones" (SPEC-023, sección 7).
// Encendido: un solo tablero con las comandas de todas las estaciones.
const unificadas = ref(false);
const comandas = ref([]);
const platos = ref([]);
const busquedaPlato = ref("");
const avisoDisponibilidad = ref(null);
const avisoTablero = ref(null);
const disponibilidadAbierta = ref(false);
const umbralAmarillo = ref(10);
const umbralRojo = ref(20);
const ahora = ref(Date.now());
let temporizador = null;
let reloj = null;
let temporizadorDisponibilidad = null;

const COLUMNAS = [
  { clave: "pendiente", titulo: "Por preparar", punto: "bg-marca", fondo: "bg-white" },
  { clave: "en_preparacion", titulo: "En preparación", punto: "bg-amber-400", fondo: "bg-amber-50/70" },
  { clave: "lista", titulo: "Listas", punto: "bg-emerald-500", fondo: "bg-emerald-50/70" },
];

const porColumna = computed(() => {
  const mapa = {};
  for (const col of COLUMNAS) {
    // Las comandas de pedidos ya entregados salen del tablero: son historia.
    mapa[col.clave] = comandas.value.filter(
      (c) => c.estado === col.clave && c.pedido_estado !== "entregado"
    );
  }
  return mapa;
});

function minutosDesde(iso) {
  return Math.max(0, Math.floor((ahora.value - new Date(iso).getTime()) / 60000));
}

/** Cronómetro que envejece (SPEC-005): verde <10, ámbar 10-20, rojo >20. */
function colorTiempo(minutos) {
  if (minutos >= umbralRojo.value) return "bg-red-100 text-red-800";
  if (minutos >= umbralAmarillo.value) return "bg-amber-100 text-amber-800";
  return "bg-emerald-100 text-emerald-800";
}

const tieneNovedades = (comanda) => (comanda.novedades?.length ?? 0) > 0;

const platosFiltrados = computed(() => {
  const termino = busquedaPlato.value.trim().toLowerCase();
  if (!termino) return platos.value;
  return platos.value.filter((plato) => plato.nombre.toLowerCase().includes(termino));
});

function avisarDisponibilidad(texto, error = false) {
  avisoDisponibilidad.value = { texto, error };
  setTimeout(() => (avisoDisponibilidad.value = null), 3000);
}

async function cargarPlatos() {
  try {
    const actualizados = await listarPlatos();
    const porId = new Map(actualizados.map((plato) => [plato.id, plato]));
    for (const plato of platos.value) {
      const actualizado = porId.get(plato.id);
      if (actualizado) Object.assign(plato, actualizado);
    }
    if (!platos.value.length) platos.value = actualizados;
  } catch {
    // El tablero de comandas sigue funcionando aunque falle este refresco.
  }
}

async function alternarDisponibilidad(plato) {
  const siguiente = !plato.disponible;
  try {
    const actualizado = await cambiarDisponibilidad(plato.id, siguiente);
    Object.assign(plato, actualizado);
    avisarDisponibilidad(
      siguiente ? `«${plato.nombre}» quedó disponible.` : `«${plato.nombre}» quedó agotado.`,
    );
  } catch (error) {
    avisarDisponibilidad(
      error.response?.data?.detalle || "No se pudo cambiar la disponibilidad.", true,
    );
  }
}

async function confirmarVisto(comanda) {
  // Optimista: el rojo se apaga de inmediato. Si la llamada falla, el
  // siguiente sondeo lo devuelve solo.
  comanda.novedades = [];
  await marcarNovedadesVistas(comanda.id);
}

async function cargarComandas() {
  if (unificadas.value) {
    comandas.value = await listarComandas();
    return;
  }
  if (!estacionId.value) return;
  comandas.value = await listarComandas(estacionId.value);
}

/**
 * Si otra persona se adelantó (el servidor responde 409), se dice por qué y
 * se recarga: la tarjeta que se ve ya no es la real. Sin esto el botón
 * parecía no hacer nada hasta el siguiente sondeo.
 */
async function cambiarEstado(accion, comanda) {
  try {
    await accion(comanda.id);
  } catch (error) {
    avisarTablero(error.response?.data?.detalle || "No se pudo actualizar la comanda.");
  }
  await cargarComandas();
}

function avisarTablero(texto) {
  avisoTablero.value = texto;
  setTimeout(() => (avisoTablero.value = null), 4000);
}

const empezar = (comanda) => cambiarEstado(marcarEnPreparacion, comanda);
const marcarComoLista = (comanda) => cambiarEstado(marcarLista, comanda);

onMounted(async () => {
  try {
    const configuracion = await obtenerConfiguracionPublica();
    const amarillo = Number(configuracion["umbral-cronometro-amarillo"]);
    const rojo = Number(configuracion["umbral-cronometro-rojo"]);
    if (Number.isFinite(amarillo) && amarillo >= 0) umbralAmarillo.value = amarillo;
    if (Number.isFinite(rojo) && rojo >= umbralAmarillo.value) umbralRojo.value = rojo;
    unificadas.value = configuracion["estaciones-unificadas"] === true;
  } catch {
    // Los umbrales predeterminados mantienen operativo el tablero.
  }
  estaciones.value = await listarEstaciones();
  platos.value = await listarPlatos();
  if (estaciones.value.length) estacionId.value = estaciones.value[0].id;
  await cargarComandas();
  temporizador = setInterval(cargarComandas, 5000);
  temporizadorDisponibilidad = setInterval(cargarPlatos, 60000);
  reloj = setInterval(() => { ahora.value = Date.now(); }, 30000);
});

onUnmounted(() => {
  clearInterval(temporizador);
  clearInterval(temporizadorDisponibilidad);
  clearInterval(reloj);
});
</script>

<template>
  <MarcoInterno titulo="Comandas" ancho="max-w-7xl">
    <template #acciones>
      <select
        v-if="!unificadas"
        v-model.number="estacionId" @change="cargarComandas"
        class="hidden max-w-[9rem] cursor-pointer truncate rounded-full border border-marca/20 bg-white px-3 py-2.5 text-[13px] font-bold text-marca sm:inline-block sm:max-w-none sm:px-4"
        title="Estación"
      >
        <option v-for="e in estaciones" :key="e.id" :value="e.id">{{ e.nombre }}</option>
      </select>
    </template>

    <!-- En telefono el selector no cabe en el encabezado sin aplastar el nombre
         del restaurante (SPEC-022 B5): va aqui, y en el encabezado desde sm. -->
    <label v-if="!unificadas" class="mb-4 block sm:hidden">
      <span class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Estación</span>
      <select
        v-model.number="estacionId" @change="cargarComandas"
        class="w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[14px] font-bold text-marca"
      >
        <option v-for="e in estaciones" :key="e.id" :value="e.id">{{ e.nombre }}</option>
      </select>
    </label>

    <p
      v-if="avisoTablero" role="alert"
      class="mb-4 rounded-xl bg-alerta/10 px-4 py-3 text-[14px] font-semibold text-alerta"
    >{{ avisoTablero }}</p>

    <div class="grid grid-cols-1 gap-5 md:grid-cols-3">
      <section
        v-for="col in COLUMNAS" :key="col.clave"
        class="min-h-[420px] rounded-3xl border border-marca/10 p-4"
        :class="col.fondo"
      >
        <header class="mb-4 flex items-center gap-2.5 px-1">
          <span class="size-3 rounded-full" :class="col.punto"></span>
          <h2 class="text-[13px] font-bold tracking-[0.12em] text-tinta/70 uppercase">{{ col.titulo }}</h2>
          <span class="ml-auto rounded-full bg-white px-3 py-1 text-sm font-bold text-tinta shadow-sm">
            {{ porColumna[col.clave].length }}
          </span>
        </header>

        <!-- Rojo mientras haya novedades sin ver (SPEC-011). El borde grueso
             y el fondo son para que se distinga de un vistazo desde la
             distancia a la que se trabaja en una cocina. -->
        <article
          v-for="c in porColumna[col.clave]" :key="c.id"
          class="mb-3.5 rounded-2xl p-5 shadow-sm"
          :class="tieneNovedades(c)
            ? 'bg-red-50 ring-2 ring-red-500'
            : 'bg-white ring-1 ring-marca/5'"
        >
          <div class="flex items-center justify-between gap-3">
            <strong class="font-display text-[26px] leading-none font-light text-marca">{{ c.destino || c.mesa }}</strong>
            <span
              class="rounded-full px-3 py-1.5 text-sm font-bold tabular-nums"
              :class="colorTiempo(minutosDesde(c.creada))"
            >{{ minutosDesde(c.creada) }} min</span>
          </div>
          <p class="mt-0.5 text-[12px] font-semibold text-tinta/45">
            Pedido #{{ c.pedido }}
            <!-- Unificado: dice de qué estación venía, salvo la principal -->
            <span
              v-if="unificadas && !c.estacion_por_defecto"
              class="ml-1.5 rounded-full bg-marca-suave px-2 py-0.5 text-[11px] font-bold tracking-wide text-marca uppercase"
            >{{ c.estacion_nombre }}</span>
          </p>

          <!-- Dice QUÉ cambió, no que algo cambió. Un aviso genérico
               obligaría al cocinero a comparar de memoria contra el papel. -->
          <div v-if="tieneNovedades(c)" class="mt-3.5 rounded-xl bg-red-500 p-3.5 text-white">
            <p class="mb-2 text-[11px] font-bold tracking-[0.14em] uppercase opacity-90">
              {{ c.novedades.length === 1 ? "Cambió el pedido" : "Cambios en el pedido" }}
            </p>
            <p v-for="n in c.novedades" :key="n.id" class="text-[16px] leading-snug font-bold">
              {{ n.descripcion }}
            </p>
            <button
              @click="confirmarVisto(c)"
              class="mt-3 min-h-11 w-full cursor-pointer rounded-lg bg-white/20 text-[13px] font-bold tracking-[0.08em] text-white uppercase transition-colors hover:bg-white/30"
            >Visto</button>
          </div>

           <ul class="mt-3.5 border-t border-marca/10 pt-3">
             <li v-for="(d, i) in c.detalles" :key="i" class="py-1.5">
               <span class="text-[17px] font-semibold" :class="{ 'uppercase': d.desglose?.length }">
                 {{ d.cantidad }}× {{ d.nombre }}
               </span>
               <!-- Una promoción trae lo que incluye (SPEC-023). Sin
                    ingredientes: la tarjeta se lee desde lejos, y cocina ya
                    sabe cómo se prepara cada cosa. Las cantidades van ya
                    multiplicadas: con 3 combos, cocina prepara 6
                    hamburguesas, y no debe tener que hacer la cuenta. -->
               <div v-if="d.desglose?.length" class="mt-1 border-l-2 border-marca/20 pl-3">
                 <p v-if="d.cantidad > 1" class="text-[11px] font-bold tracking-[0.1em] text-tinta/45 uppercase">
                   En total
                 </p>
                 <ul>
                   <li v-for="(componente, j) in d.desglose" :key="j" class="text-[15px] leading-snug font-medium text-tinta/80">
                     {{ componente[0] * d.cantidad }}× {{ componente[1] }}
                   </li>
                 </ul>
               </div>
               <p v-if="d.observacion" class="mt-0.5 text-[14px] font-bold text-amber-700">
                ⚠ {{ d.observacion }}
              </p>
            </li>
          </ul>

          <button
            v-if="c.estado === 'pendiente'"
            @click="empezar(c)"
            class="mt-4 min-h-13 w-full cursor-pointer rounded-2xl bg-marca text-[15px] font-bold text-lienzo transition-transform active:scale-[0.98]"
          >Empezar a preparar</button>

          <button
            v-else-if="c.estado === 'en_preparacion'"
            @click="marcarComoLista(c)"
            class="mt-4 min-h-13 w-full cursor-pointer rounded-2xl bg-emerald-600 text-[15px] font-bold text-white transition-transform active:scale-[0.98]"
          >✓ Listo — avisar al mesero</button>

          <div
            v-else
            class="mt-4 rounded-2xl bg-emerald-100 py-3.5 text-center text-[14px] font-bold text-emerald-800"
          >Esperando al mesero</div>
        </article>

        <p
          v-if="porColumna[col.clave].length === 0"
          class="rounded-2xl border-2 border-dashed border-tinta/10 py-12 text-center text-[14px] font-medium text-tinta/35"
        >Sin comandas</p>
      </section>
    </div>

    <button
      @click="disponibilidadAbierta = true"
      class="fixed right-4 bottom-5 z-30 flex min-h-12 cursor-pointer items-center gap-2 rounded-full bg-marca px-4 text-[12px] font-bold text-lienzo shadow-lg transition-transform hover:-translate-y-0.5 sm:right-6 sm:top-28 sm:bottom-auto"
    >
      <span class="grid size-6 place-items-center rounded-full bg-acento text-tinta">86</span>
      <span>Disponibilidad</span>
    </button>

    <div
      v-if="disponibilidadAbierta"
      class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/45 backdrop-blur-sm sm:items-stretch sm:justify-end"
      @click.self="disponibilidadAbierta = false"
    >
      <aside class="flex max-h-[90dvh] w-full flex-col overflow-hidden rounded-t-3xl bg-lienzo sm:h-full sm:max-h-none sm:w-[min(92vw,30rem)] sm:rounded-none sm:rounded-l-3xl">
        <header class="flex shrink-0 items-start justify-between gap-4 border-b border-marca/12 px-5 py-5 sm:px-6">
          <div>
            <p class="text-[11px] font-bold tracking-[0.14em] text-marca/60 uppercase">Cocina</p>
            <h2 class="mt-1 font-display text-3xl font-light text-marca">Disponibilidad</h2>
            <p class="mt-1 text-[13px] text-tinta/55">Marca lo que se agotó o vuelve a estar listo.</p>
          </div>
          <button
            @click="disponibilidadAbierta = false"
            aria-label="Cerrar disponibilidad"
            class="grid size-11 shrink-0 cursor-pointer place-items-center rounded-full border border-marca/15 text-marca"
          >×</button>
        </header>

        <div class="flex-1 overflow-y-auto px-5 py-5 sm:px-6">
          <input
            v-model="busquedaPlato" type="search" placeholder="Buscar plato…"
            class="min-h-12 w-full rounded-xl border border-marca/15 bg-white px-4 text-[14px] outline-none focus:border-marca"
          />
          <p
            v-if="avisoDisponibilidad"
            class="mt-3 rounded-xl px-3 py-2.5 text-[13px] font-semibold"
            :class="avisoDisponibilidad.error ? 'bg-alerta/10 text-alerta' : 'bg-emerald-50 text-emerald-800'"
          >{{ avisoDisponibilidad.texto }}</p>

          <div class="mt-5 space-y-2">
            <button
              v-for="plato in platosFiltrados" :key="plato.id"
              @click="alternarDisponibilidad(plato)"
              class="flex min-h-14 w-full items-center gap-3 rounded-2xl border bg-white px-4 py-3 text-left transition-colors"
              :class="plato.disponible
                ? 'border-marca/10 hover:border-alerta/40'
                : 'border-alerta/25 bg-alerta/5 hover:border-emerald-600/40'"
            >
              <span
                class="size-3 shrink-0 rounded-full"
                :class="plato.disponible ? 'bg-emerald-500' : 'bg-alerta'"
              ></span>
              <span class="min-w-0 flex-1">
                <strong class="block truncate text-[14px]" :class="plato.disponible ? 'text-tinta' : 'text-alerta'">{{ plato.nombre }}</strong>
                <small class="text-[11px] text-tinta/50">{{ plato.disponible ? 'Disponible' : 'Agotado' }}</small>
              </span>
              <span class="shrink-0 rounded-full border px-3 py-1.5 text-[11px] font-bold uppercase" :class="plato.disponible ? 'border-alerta/25 text-alerta' : 'border-emerald-600/25 text-emerald-700'">
                {{ plato.disponible ? 'Agotar' : 'Reactivar' }}
              </span>
            </button>
          </div>
        </div>
      </aside>
    </div>
  </MarcoInterno>
</template>
