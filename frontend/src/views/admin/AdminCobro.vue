<script setup>
/**
 * Cobro (SPEC-007): las dos listas que hasta ahora solo existían en la API y
 * había que tocar a mano — medios de pago y observaciones rápidas generales.
 *
 * Van juntas porque las dos son "listas de opciones que el restaurante
 * define y las pantallas consumen", y ninguna da para sección propia.
 *
 * Las observaciones de un plato concreto NO se editan aquí: viven en la
 * ficha de ese plato (Menú), que es donde el administrador las piensa.
 */
import { onMounted, ref } from "vue";
import {
  listarCajas, guardarCaja, listarCategoriasGasto, guardarCategoriaGasto,
} from "../../api/caja";
import {
  listarObservaciones, crearObservacion, actualizarObservacion, borrarObservacion,
} from "../../api/menu";
import MarcoInterno from "../../components/MarcoInterno.vue";
import AdminPestanas from "../../components/AdminPestanas.vue";
import { formatearMoneda } from "../../lib/tema";

const cajas = ref([]);
const observaciones = ref([]);
const categorias = ref([]);
const cargando = ref(true);
const mensaje = ref(null);

const nuevaCaja = ref("");
const nuevaObservacion = ref("");
const nuevaCategoria = ref("");

const moneda = { format: formatearMoneda };

function avisar(texto, error = false) {
  mensaje.value = { texto, error };
  setTimeout(() => (mensaje.value = null), 3200);
}

async function cargar() {
  const [cs, obs, cats] = await Promise.all([
    listarCajas(true),
    listarObservaciones({ soloGenerales: true }),
    listarCategoriasGasto(),
  ]);
  cajas.value = cs;
  observaciones.value = obs;
  categorias.value = cats;
  cargando.value = false;
}

/* --- Medios de pago -------------------------------------------------- */

async function crearCaja() {
  const nombre = nuevaCaja.value.trim();
  if (!nombre) return;
  try {
    await guardarCaja(null, { nombre, orden: cajas.value.length });
    nuevaCaja.value = "";
    avisar(`«${nombre}» agregado`);
    await cargar();
  } catch (e) {
    avisar(e.response?.data?.nombre?.[0] || "No se pudo crear.", true);
  }
}

/**
 * Una caja no se borra: se desactiva. Su saldo es la suma de movimientos
 * que ya ocurrieron, y borrarla dejaría cobros pasados sin a dónde apuntar
 * (SPEC-008: el historial no se reescribe).
 */
async function alternarCaja(caja) {
  const antes = caja.activo;
  caja.activo = !antes;
  try {
    await guardarCaja(caja.id, { activo: caja.activo });
    avisar(caja.activo ? `«${caja.nombre}» activa` : `«${caja.nombre}» retirada del cobro`);
  } catch {
    caja.activo = antes;
    avisar("No se pudo cambiar.", true);
  }
}

async function renombrarCaja(caja) {
  const nombre = caja.nombre.trim();
  if (!nombre) return cargar();
  try {
    await guardarCaja(caja.id, { nombre });
  } catch {
    avisar("Ese nombre ya existe.", true);
    await cargar();
  }
}

async function guardarPrefijo(caja) {
  const prefijo = caja.prefijo.trim().slice(0, 4);
  caja.prefijo = prefijo;
  try {
    await guardarCaja(caja.id, { prefijo });
    avisar(`Prefijo de «${caja.nombre}» guardado`);
  } catch {
    avisar("No se pudo guardar el prefijo.", true);
    await cargar();
  }
}

/**
 * Efectivo o banco (SPEC-020). No es una etiqueta: el efectivo es el que se
 * cuenta a mano y se retira al cerrar el turno. Marcar mal una caja haria
 * que el cierre del dia sacara plata de donde no debe.
 */
async function guardarTipo(caja) {
  try {
    await guardarCaja(caja.id, { tipo: caja.tipo });
    avisar(`«${caja.nombre}» ahora es ${caja.tipo === "efectivo" ? "efectivo" : "banco"}`);
  } catch {
    avisar("No se pudo cambiar el tipo.", true);
    await cargar();
  }
}

/* --- Categorias de gasto (SPEC-020) ----------------------------------- */

async function crearCategoria() {
  const nombre = nuevaCategoria.value.trim();
  if (!nombre) return;
  try {
    await guardarCategoriaGasto(null, { nombre, orden: categorias.value.length });
    nuevaCategoria.value = "";
    avisar(`«${nombre}» agregada`);
    await cargar();
  } catch (e) {
    avisar(e.response?.data?.nombre?.[0] || "Esa categoria ya existe.", true);
  }
}

async function renombrarCategoria(cat) {
  const nombre = cat.nombre.trim();
  if (!nombre) return cargar();
  try {
    await guardarCategoriaGasto(cat.id, { nombre });
  } catch {
    avisar("Ese nombre ya existe.", true);
    await cargar();
  }
}

/**
 * Se desactiva, no se borra: una categoria con gastos registrados que
 * desapareciera dejaria esos movimientos sin explicacion de en que se fue
 * esa plata.
 */
async function alternarCategoria(cat) {
  const antes = cat.activo;
  cat.activo = !antes;
  try {
    await guardarCategoriaGasto(cat.id, { activo: cat.activo });
  } catch {
    cat.activo = antes;
    avisar("No se pudo cambiar.", true);
  }
}

/* --- Observaciones generales ------------------------------------------ */

async function agregarObservacion() {
  const texto = nuevaObservacion.value.trim();
  if (!texto) return;
  try {
    await crearObservacion(texto); // sin plato = general, para todos
    nuevaObservacion.value = "";
    avisar(`«${texto}» ahora aparece en todos los platos`);
    await cargar();
  } catch (e) {
    avisar(e.response?.data?.texto?.[0] || "Esa etiqueta ya existe.", true);
  }
}

async function alternarObservacion(obs) {
  const antes = obs.activo;
  obs.activo = !antes;
  try {
    await actualizarObservacion(obs.id, { activo: obs.activo });
  } catch {
    obs.activo = antes;
    avisar("No se pudo cambiar.", true);
  }
}

async function quitarObservacion(obs) {
  if (!confirm(`¿Quitar «${obs.texto}» de todos los platos?`)) return;
  await borrarObservacion(obs.id);
  avisar(`«${obs.texto}» eliminada`);
  await cargar();
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Cobro y observaciones" ancho="max-w-4xl">
    <AdminPestanas />

    <p
      v-if="mensaje"
      class="mb-4 rounded-lg px-4 py-2.5 text-[13px] font-semibold"
      :class="mensaje.error ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'"
    >{{ mensaje.texto }}</p>

    <p v-if="cargando" class="py-10 text-center text-panel-tinta/50">Cargando…</p>

    <template v-else>
      <!-- ===== Medios de pago ===== -->
      <section class="mb-8 rounded-2xl border border-panel-borde bg-white p-5">
        <h2 class="text-[15px] font-semibold">Medios de pago</h2>
        <p class="mt-1 mb-4 text-[12.5px] text-panel-tinta/60">
          Cada uno es también una caja: al cobrar se elige, y ahí se acumula el dinero.
        </p>

        <ul class="mb-4 divide-y divide-panel-borde">
          <li v-for="c in cajas" :key="c.id" class="flex flex-wrap items-center gap-2 py-2.5">
            <input
              v-model="c.nombre" type="text" maxlength="40"
              @blur="renombrarCaja(c)" @keyup.enter="$event.target.blur()"
              class="min-w-0 basis-full rounded-lg border border-transparent px-2 py-1.5 text-sm font-semibold outline-none hover:border-panel-borde focus:border-panel-marca sm:flex-1 sm:basis-auto"
              :class="{ 'text-panel-tinta/40 line-through': !c.activo }"
            />
            <label class="flex shrink-0 items-center gap-1 text-[11px] text-panel-tinta/55">
              <span>Sigla</span>
              <input
                v-model="c.prefijo" type="text" maxlength="4" placeholder="Ef"
                @blur="guardarPrefijo(c)" @keyup.enter="$event.target.blur()"
                class="w-14 rounded-lg border border-panel-borde px-2 py-1.5 text-center font-mono text-[12px] uppercase outline-none focus:border-panel-marca"
              />
            </label>
            <select
              v-model="c.tipo" @change="guardarTipo(c)"
              class="shrink-0 cursor-pointer rounded-lg border border-panel-borde px-2 py-1.5 text-[12px] outline-none focus:border-panel-marca"
              title="El efectivo se cuenta a mano y se retira al cerrar el turno"
            >
              <option value="efectivo">Efectivo</option>
              <option value="banco">Banco</option>
            </select>
            <span class="shrink-0 text-[13px] tabular-nums text-panel-tinta/60">
              {{ moneda.format(c.saldo) }}
            </span>
            <button
              @click="alternarCaja(c)"
              class="min-h-11 shrink-0 cursor-pointer rounded-full border px-3.5 text-[12px] font-semibold"
              :class="c.activo
                ? 'border-panel-borde text-panel-tinta/70 hover:border-panel-marca'
                : 'border-panel-marca bg-panel-marca text-white'"
            >{{ c.activo ? "Retirar" : "Activar" }}</button>
          </li>
        </ul>

        <div class="flex gap-2">
          <input
            v-model="nuevaCaja" type="text" maxlength="40"
            placeholder="Nuevo medio de pago (Nequi, Datáfono…)"
            @keyup.enter="crearCaja"
            class="min-h-11 min-w-0 flex-1 rounded-lg border border-panel-borde px-3 text-sm outline-none focus:border-panel-marca"
          />
          <button
            @click="crearCaja"
            class="min-h-11 cursor-pointer rounded-lg bg-panel-marca px-5 text-[13px] font-semibold text-white"
          >Agregar</button>
        </div>
      </section>

      <!-- ===== Categorias de gasto (SPEC-020) ===== -->
      <section class="mb-8 rounded-2xl border border-panel-borde bg-white p-5">
        <h2 class="text-[15px] font-semibold">Categorías de gasto</h2>
        <p class="mt-1 mb-4 text-[12.5px] text-panel-tinta/60">
          En qué se va la plata. Sin esto no se podría responder «¿cuánto se fue
          en nómina el mes pasado?». Una categoría con gastos registrados se
          desactiva, no se borra.
        </p>

        <ul class="mb-4 divide-y divide-panel-borde">
          <li v-for="c in categorias" :key="c.id" class="flex flex-wrap items-center gap-2 py-2.5">
            <input
              v-model="c.nombre" type="text" maxlength="60"
              @blur="renombrarCategoria(c)" @keyup.enter="$event.target.blur()"
              class="min-w-0 basis-full rounded-lg border border-transparent px-2 py-1.5 text-sm font-semibold outline-none hover:border-panel-borde focus:border-panel-marca sm:flex-1 sm:basis-auto"
              :class="{ 'text-panel-tinta/40 line-through': !c.activo }"
            />
            <button
              @click="alternarCategoria(c)"
              class="min-h-11 shrink-0 cursor-pointer rounded-full border px-3.5 text-[12px] font-semibold"
              :class="c.activo
                ? 'border-panel-borde text-panel-tinta/70 hover:border-panel-marca'
                : 'border-panel-marca bg-panel-marca text-white'"
            >{{ c.activo ? "Desactivar" : "Activar" }}</button>
          </li>
        </ul>

        <div class="flex gap-2">
          <input
            v-model="nuevaCategoria" type="text" maxlength="60"
            placeholder="Nueva categoría (Publicidad, Impuestos…)"
            @keyup.enter="crearCategoria"
            class="min-h-11 min-w-0 flex-1 rounded-lg border border-panel-borde px-3 text-sm outline-none focus:border-panel-marca"
          />
          <button
            @click="crearCategoria"
            class="min-h-11 cursor-pointer rounded-lg bg-panel-marca px-4 text-[13px] font-semibold text-white"
          >Agregar</button>
        </div>
      </section>

      <!-- ===== Observaciones generales ===== -->
      <section class="rounded-2xl border border-panel-borde bg-white p-5">
        <h2 class="text-[15px] font-semibold">Observaciones de todos los platos</h2>
        <p class="mt-1 mb-4 text-[12.5px] text-panel-tinta/60">
          Etiquetas que el cliente y el mesero pueden tocar en <strong>cualquier</strong>
          plato. Las que solo aplican a uno se agregan en la ficha de ese plato, dentro de
          <RouterLink :to="{ name: 'admin-menu' }" class="font-semibold underline">Menú</RouterLink>.
        </p>

        <div class="mb-4 flex flex-wrap gap-2">
          <span
            v-for="o in observaciones" :key="o.id"
            class="flex items-center gap-1.5 rounded-full border py-1.5 pr-1.5 pl-3.5 text-[13px] font-semibold"
            :class="o.activo
              ? 'border-panel-borde text-panel-tinta'
              : 'border-dashed border-panel-borde text-panel-tinta/40'"
          >
            <button
              @click="alternarObservacion(o)"
              :title="o.activo ? 'Ocultar del menú' : 'Mostrar en el menú'"
              class="cursor-pointer"
              :class="{ 'line-through': !o.activo }"
            >{{ o.texto }}</button>
            <button
              @click="quitarObservacion(o)" title="Eliminar"
              class="flex size-6 cursor-pointer items-center justify-center rounded-full text-panel-tinta/40 hover:bg-red-50 hover:text-red-600"
            >×</button>
          </span>
          <p v-if="!observaciones.length" class="text-[13px] text-panel-tinta/50">
            Todavía no hay ninguna.
          </p>
        </div>

        <div class="flex gap-2">
          <input
            v-model="nuevaObservacion" type="text" maxlength="60"
            placeholder="Nueva etiqueta (sin cebolla, poca sal…)"
            @keyup.enter="agregarObservacion"
            class="min-h-11 min-w-0 flex-1 rounded-lg border border-panel-borde px-3 text-sm outline-none focus:border-panel-marca"
          />
          <button
            @click="agregarObservacion"
            class="min-h-11 cursor-pointer rounded-lg bg-panel-marca px-5 text-[13px] font-semibold text-white"
          >Agregar</button>
        </div>
      </section>
    </template>
  </MarcoInterno>
</template>
