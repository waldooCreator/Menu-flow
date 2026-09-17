<script setup>
/**
 * Panel Vue de configuración — reemplaza al Django admin para esta gestión
 * (ADR-006). Edita `Parametro` vía la API.
 *
 * Pendiente: subida de imágenes y CRUD de menú.
 */
import { ref, onMounted, computed } from "vue";
import { listarParametros, actualizarParametro, subirImagenParametro } from "../../api/configuracion";
import MarcoInterno from "../../components/MarcoInterno.vue";
import AdminPestanas from "../../components/AdminPestanas.vue";

const parametros = ref([]);
const cargando = ref(true);
const guardandoId = ref(null);
const mensaje = ref(null);

const ETIQUETAS_GRUPO = {
  identidad: "Identidad visual",
  hero: "Portada",
  contacto: "Contacto",
  horario: "Horario",
  galeria: "Galería del local",
  decoracion: "Decoración de fondo",
  operacion: "Operación",
  cobro: "Cobro",
};

const porGrupo = computed(() => {
  const mapa = new Map();
  for (const p of parametros.value) {
    if (!mapa.has(p.grupo)) mapa.set(p.grupo, []);
    mapa.get(p.grupo).push(p);
  }
  return mapa;
});

async function cargar() {
  cargando.value = true;
  parametros.value = await listarParametros();
  cargando.value = false;
}

async function guardar(param) {
  guardandoId.value = param.id;
  mensaje.value = null;
  try {
    await actualizarParametro(param.id, { valor: param.valor });
    mensaje.value = { texto: `Guardado: ${param.etiqueta}`, error: false };
  } catch {
    mensaje.value = { texto: `Error guardando ${param.etiqueta}`, error: true };
  } finally {
    guardandoId.value = null;
    setTimeout(() => (mensaje.value = null), 2500);
  }
}

/**
 * Subida de imágenes — el "próximo tramo" que quedó pendiente el 2026-08-25.
 * El servidor cachea la configuración 60 s, así que el sitio del cliente
 * puede tardar hasta un minuto en reflejar la imagen nueva.
 */
async function subirImagen(param, evento) {
  const archivo = evento.target.files[0];
  evento.target.value = "";
  if (!archivo) return;
  guardandoId.value = param.id;
  try {
    const actualizado = await subirImagenParametro(param.id, archivo);
    param.valor_resuelto = actualizado.valor_resuelto;
    mensaje.value = { texto: `Imagen de «${param.etiqueta}» subida — visible en el sitio en ~1 min`, error: false };
  } catch {
    mensaje.value = { texto: `Error subiendo la imagen de ${param.etiqueta}`, error: true };
  } finally {
    guardandoId.value = null;
    setTimeout(() => (mensaje.value = null), 3500);
  }
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Configuración del sitio" ancho="max-w-3xl">
    <AdminPestanas />

    <p v-if="cargando" class="py-8 text-panel-tinta/50">Cargando…</p>

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

    <section
      v-for="[grupo, items] in porGrupo" :key="grupo"
      class="mb-6 overflow-hidden rounded-xl border border-panel-borde bg-white"
    >
      <h2 class="border-b border-panel-borde bg-panel-alt px-4 py-3 text-[13px] font-semibold">
        {{ ETIQUETAS_GRUPO[grupo] || grupo }}
      </h2>

      <div class="divide-y divide-panel-borde">
        <div
          v-for="p in items" :key="p.id"
          class="flex flex-col gap-2.5 px-4 py-3.5 sm:flex-row sm:items-center sm:gap-3"
        >
          <label :for="`p-${p.id}`" class="text-[13px] text-panel-tinta/70 sm:w-52 sm:shrink-0">
            {{ p.etiqueta }}
            <!-- La ayuda dice qué pasa con cada valor: sin ella, "Los meseros
                 también pueden cobrar" no aclaraba que caja cobra siempre
                 (SPEC-014, revisado 2026-09-16). -->
            <span v-if="p.ayuda" class="mt-0.5 block text-[11.5px] leading-snug text-panel-tinta/45">{{ p.ayuda }}</span>
          </label>

          <div v-if="p.tipo === 'imagen'" class="flex flex-1 items-center gap-3">
            <img
              v-if="p.valor_resuelto" :src="p.valor_resuelto" alt=""
              class="h-10 w-16 rounded-md object-cover"
            />
            <div v-else class="grid h-10 w-16 place-items-center rounded-md bg-panel-alt text-panel-tinta/30">—</div>
            <input
              type="file" accept="image/*" :disabled="guardandoId === p.id"
              @change="subirImagen(p, $event)"
              class="cursor-pointer text-[12px] file:mr-2 file:cursor-pointer file:rounded-lg file:border-0 file:bg-panel-alt file:px-3 file:py-1.5 file:text-[12px] file:font-semibold"
            />
          </div>

          <template v-else>
            <div class="flex flex-1 items-center gap-2.5">
              <input
                v-if="p.tipo === 'color'" :id="`p-${p.id}`" v-model="p.valor" type="color"
                class="h-9 w-12 cursor-pointer rounded border-0 bg-transparent p-0"
              />
              <input
                v-if="p.tipo === 'color'" v-model="p.valor" type="text" spellcheck="false"
                class="w-28 rounded-lg border border-panel-borde px-2.5 py-2 font-mono text-[13px] uppercase outline-none focus:border-panel-marca"
              />
              <!-- Un parámetro sí/no se elige, no se escribe: con texto libre
                   un "Si" o un "sí " valía distinto que un "si". -->
              <select
                v-else-if="p.tipo === 'booleano'" :id="`p-${p.id}`" v-model="p.valor"
                class="flex-1 rounded-lg border border-panel-borde bg-white px-3 py-2 text-sm outline-none focus:border-panel-marca"
              >
                <option value="si">Sí</option>
                <option value="no">No</option>
              </select>
              <select
                v-else-if="p.clave === 'formato-tiquete'" :id="`p-${p.id}`" v-model="p.valor"
                class="flex-1 rounded-lg border border-panel-borde bg-white px-3 py-2 text-sm outline-none focus:border-panel-marca"
              >
                <option value="rollo">Rollo térmico (80 mm)</option>
                <option value="carta">Carta</option>
              </select>
              <input
                v-else :id="`p-${p.id}`" v-model="p.valor" type="text"
                class="flex-1 rounded-lg border border-panel-borde px-3 py-2 text-sm outline-none focus:border-panel-marca"
              />
            </div>

            <button
              @click="guardar(p)" :disabled="guardandoId === p.id"
              class="cursor-pointer rounded-lg bg-panel-marca px-4 py-2 text-[13px] font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 sm:shrink-0"
            >{{ guardandoId === p.id ? "…" : "Guardar" }}</button>
          </template>
        </div>
      </div>
    </section>
  </MarcoInterno>
</template>
