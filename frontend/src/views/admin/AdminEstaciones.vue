<script setup>
/**
 * Estaciones de preparación (SPEC-005/007): crear una estación nueva es una
 * fila, no código — esta pantalla es donde esa promesa se cumple para el
 * administrador. Las categorías se asignan a estación desde la pestaña Menú.
 */
import { computed, onMounted, ref } from "vue";
import { listarEstaciones, guardarEstacion, eliminarEstacion } from "../../api/estaciones";
import { obtenerConfiguracionPublica } from "../../api/configuracion";
import MarcoInterno from "../../components/MarcoInterno.vue";
import AdminPestanas from "../../components/AdminPestanas.vue";

const estaciones = ref([]);
const cargando = ref(true);
const mensaje = ref(null);
const nuevoNombre = ref("");
// SPEC-023, sección 7: esta pantalla dice en qué modo está el restaurante,
// porque aquí es donde se piensa en las estaciones.
const unificadas = ref(false);
const porDefecto = computed(() => estaciones.value.find((e) => e.por_defecto)?.nombre ?? "la estación por defecto");

function avisar(texto, error = false) {
  mensaje.value = { texto, error };
  setTimeout(() => (mensaje.value = null), 3500);
}

async function cargar() {
  const [lista, configuracion] = await Promise.all([
    listarEstaciones(),
    obtenerConfiguracionPublica().catch(() => ({})),
  ]);
  estaciones.value = lista;
  unificadas.value = configuracion["estaciones-unificadas"] === true;
  cargando.value = false;
}

async function crear() {
  const nombre = nuevoNombre.value.trim();
  if (!nombre) return;
  try {
    await guardarEstacion(null, { nombre, orden: estaciones.value.length });
    nuevoNombre.value = "";
    await cargar();
    avisar(`Estación «${nombre}» creada — asígnale categorías desde Menú`);
  } catch (e) {
    avisar(e.response?.data?.nombre?.[0] || "No se pudo crear.", true);
  }
}

async function renombrar(est) {
  const nombre = est.nombre.trim();
  if (!nombre) return;
  await guardarEstacion(est.id, { nombre });
  avisar("Nombre guardado");
}

/**
 * Solo puede haber UNA por defecto: es a donde caen las categorías sin
 * estación asignada (SPEC-005). Marcar una desmarca la anterior.
 */
async function marcarPorDefecto(est) {
  const anterior = estaciones.value.find((e) => e.por_defecto && e.id !== est.id);
  if (anterior) await guardarEstacion(anterior.id, { por_defecto: false });
  await guardarEstacion(est.id, { por_defecto: true });
  await cargar();
  avisar(`«${est.nombre}» es ahora la estación por defecto`);
}

async function borrar(est) {
  try {
    await eliminarEstacion(est.id);
    await cargar();
    avisar(`«${est.nombre}» eliminada`);
  } catch {
    // PROTECT: tiene comandas históricas. El historial no se toca.
    avisar(`«${est.nombre}» tiene comandas registradas y no se puede eliminar. Mueve sus categorías a otra estación.`, true);
  }
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Estaciones" ancho="max-w-2xl">
    <AdminPestanas />

    <Transition
      enter-from-class="opacity-0 -translate-y-1" leave-to-class="opacity-0"
      enter-active-class="transition duration-200" leave-active-class="transition duration-200"
    >
      <p
        v-if="mensaje"
        class="mb-4 rounded-lg px-3.5 py-2.5 text-sm font-semibold"
        :class="mensaje.error ? 'bg-alerta/8 text-alerta' : 'bg-panel-marca/8 text-panel-marca'"
      >{{ mensaje.texto }}</p>
    </Transition>

    <p v-if="cargando" class="py-8 text-panel-tinta/50">Cargando…</p>

    <template v-else>
      <div class="mb-4 rounded-xl border border-panel-borde bg-panel-alt/60 px-4 py-3 text-[13px] leading-snug">
        <p v-if="unificadas">
          <strong>Estaciones unificadas.</strong> Todo llega a <strong>{{ porDefecto }}</strong>,
          y el tablero de cocina muestra las comandas de todas las estaciones juntas.
        </p>
        <p v-else>
          <strong>Estaciones separadas.</strong> Cada plato llega a la estación de su categoría
          (se asigna en la pestaña Menú), y cada estación ve solo lo suyo.
        </p>
        <p class="mt-1 text-panel-tinta/60">
          Se cambia en <RouterLink :to="{ name: 'admin-configuracion' }" class="font-semibold text-panel-marca underline">Configuración → Operación → Unificar estaciones</RouterLink>.
        </p>
      </div>

      <div class="overflow-hidden rounded-xl border border-panel-borde bg-white">
        <div class="divide-y divide-panel-borde">
          <div v-for="e in estaciones" :key="e.id" class="flex flex-wrap items-center gap-3 px-4 py-3">
            <input
              v-model="e.nombre" type="text" maxlength="60" @change="renombrar(e)"
              class="min-w-0 basis-full rounded-lg border border-transparent px-2 py-1.5 text-[14px] font-semibold outline-none hover:border-panel-borde sm:flex-1 sm:basis-auto focus:border-panel-marca"
            />

            <button
              v-if="e.por_defecto"
              class="rounded-full bg-panel-marca/10 px-3 py-1.5 text-[11px] font-bold tracking-wide text-panel-marca uppercase"
            >Por defecto</button>
            <button
              v-else @click="marcarPorDefecto(e)"
              class="cursor-pointer rounded-full border border-panel-borde px-3 py-1.5 text-[11px] font-semibold tracking-wide text-panel-tinta/50 uppercase hover:border-panel-marca"
            >Hacer por defecto</button>

            <button
              @click="borrar(e)" aria-label="Eliminar estación"
              class="grid min-h-11 min-w-11 cursor-pointer place-items-center text-panel-tinta/35 hover:text-alerta"
            >✕</button>
          </div>
        </div>
      </div>

      <p class="mt-2 text-[12px] text-panel-tinta/45">
        La estación <b>por defecto</b> recibe las categorías que no tienen estación asignada.
        Qué categoría va a qué estación se decide en la pestaña <b>Menú</b>.
      </p>

      <div class="mt-4 flex gap-2">
        <input
          v-model="nuevoNombre" type="text" maxlength="60"
          placeholder="Nueva estación (p.ej. Parrilla, Bebidas)…" @keyup.enter="crear"
          class="flex-1 rounded-lg border border-panel-borde bg-white px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
        />
        <button
          @click="crear"
          class="cursor-pointer rounded-lg bg-panel-marca px-4 py-2.5 text-[13px] font-semibold text-white"
        >Crear</button>
      </div>
    </template>
  </MarcoInterno>
</template>
