<script setup>
/**
 * Directorio de clientes (SPEC-019).
 *
 * Los clientes no se dan de alta a mano: se crean solos al confirmar un
 * domicilio. Esta pantalla es para consultarlos, corregirlos y borrarlos —
 * lo último es un requisito de la Ley 1581, no una comodidad.
 *
 * Borrar un cliente **no borra sus ventas**: quedan con su nombre congelado y
 * su historia contable intacta. Solo desaparece el dato personal.
 */
import { computed, onMounted, ref } from "vue";
import {
  listarClientes, guardarCliente, borrarCliente,
  agregarDireccion, quitarDireccion,
} from "../../api/clientes";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const clientes = ref([]);
const cargando = ref(true);
const error = ref(null);
const aviso = ref(null);
const buscar = ref("");

const abierto = ref(null);        // cliente en edición
const nuevaDireccion = ref("");
const confirmandoBorrado = ref(null);

const moneda = formatearMoneda;

const hayClientes = computed(() => clientes.value.length > 0);

function avisar(texto) {
  aviso.value = texto;
  setTimeout(() => (aviso.value = null), 3500);
}

async function cargar() {
  error.value = null;
  try {
    clientes.value = await listarClientes(buscar.value);
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudieron cargar los clientes.";
  } finally {
    cargando.value = false;
  }
}

function abrir(cliente) {
  // Copia: si el usuario cancela, la lista no debe quedar editada a medias.
  abierto.value = { ...cliente, direcciones: [...cliente.direcciones] };
  nuevaDireccion.value = "";
}

async function guardar() {
  try {
    await guardarCliente(abierto.value.id, {
      nombre: abierto.value.nombre,
      telefono: abierto.value.telefono,
      observaciones: abierto.value.observaciones,
    });
    avisar(`«${abierto.value.nombre}» actualizado`);
    abierto.value = null;
    await cargar();
  } catch (e) {
    error.value = e.response?.data?.telefono?.[0]
      || e.response?.data?.detalle
      || "No se pudo guardar.";
  }
}

async function sumarDireccion() {
  const texto = nuevaDireccion.value.trim();
  if (!texto) return;
  const creada = await agregarDireccion(abierto.value.id, texto);
  if (!abierto.value.direcciones.some((d) => d.id === creada.id)) {
    abierto.value.direcciones.push(creada);
  }
  nuevaDireccion.value = "";
  await cargar();
}

async function sacarDireccion(direccion) {
  await quitarDireccion(abierto.value.id, direccion.id);
  abierto.value.direcciones = abierto.value.direcciones.filter((d) => d.id !== direccion.id);
  await cargar();
}

async function eliminar() {
  const nombre = confirmandoBorrado.value.nombre;
  await borrarCliente(confirmandoBorrado.value.id);
  confirmandoBorrado.value = null;
  abierto.value = null;
  avisar(`«${nombre}» eliminado. Sus ventas siguen en el historial.`);
  await cargar();
}

function fecha(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-CO",
    { day: "numeric", month: "short", year: "numeric" });
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Clientes" ancho="max-w-4xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <p v-if="error" class="mb-4 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
      {{ error }}
    </p>
    <p v-if="aviso" class="mb-4 rounded-xl bg-emerald-50 px-3.5 py-2.5 text-[13px] font-semibold text-emerald-700">
      {{ aviso }}
    </p>

    <!-- ===== Buscador ===== -->
    <div class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-4">
      <input
        v-model="buscar" type="search" maxlength="60"
        placeholder="Buscar por nombre o teléfono…"
        @input="cargar"
        class="min-h-11 w-full rounded-xl border border-marca/20 px-3.5 text-[14px] outline-none focus:border-marca"
      />
      <p class="mt-2 text-[12px] leading-snug text-tinta/50">
        Los clientes se crean solos al confirmar un domicilio. Aquí se consultan y corrigen.
      </p>
    </div>

    <p v-if="cargando" class="py-14 text-center text-tinta/50">Cargando…</p>

    <template v-else>
      <p v-if="!hayClientes" class="py-14 text-center text-[14px] text-tinta/50">
        {{ buscar ? "Nadie con ese nombre o teléfono." : "Todavía no hay clientes." }}
      </p>

      <ul v-else class="mt-3 overflow-hidden rounded-2xl border border-marca/12 bg-white">
        <li
          v-for="c in clientes" :key="c.id"
          @click="abrir(c)"
          class="flex cursor-pointer items-center gap-3 border-b border-marca/8 px-4 py-3.5 transition-colors last:border-b-0 hover:bg-marca/4"
        >
          <div class="min-w-0 flex-1">
            <p class="line-clamp-2 text-[14px] leading-snug font-semibold text-tinta">{{ c.nombre }}</p>
            <p class="line-clamp-2 text-[12px] leading-snug text-tinta/50">
              {{ c.telefono }}
              <template v-if="c.direcciones.length">
                · {{ c.direcciones[0].direccion }}
              </template>
            </p>
          </div>
          <div class="shrink-0 text-right">
            <p class="text-[14px] font-semibold tabular-nums text-marca">
              {{ moneda(c.resumen.gastado) }}
            </p>
            <p class="text-[11.5px] text-tinta/45">
              {{ c.resumen.compras }} {{ c.resumen.compras === 1 ? "compra" : "compras" }}
            </p>
          </div>
        </li>
      </ul>
    </template>

    <!-- ===== Ficha ===== -->
    <div
      v-if="abierto"
      class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/45 backdrop-blur-sm sm:items-center sm:p-4"
      @click.self="abierto = null"
    >
      <div class="max-h-[90dvh] w-full overflow-y-auto rounded-t-3xl bg-white p-5 sm:max-w-md sm:rounded-3xl sm:p-6">
        <div class="flex items-start justify-between gap-3">
          <h3 class="font-display text-[22px] leading-tight font-light text-marca">
            {{ abierto.nombre }}
          </h3>
          <button
            @click="abierto = null" aria-label="Cerrar"
            class="grid size-11 shrink-0 cursor-pointer place-items-center rounded-full border border-marca/15 text-marca"
          >×</button>
        </div>

        <p class="mt-1.5 text-[12.5px] text-tinta/55">
          {{ abierto.resumen.compras }} {{ abierto.resumen.compras === 1 ? "compra" : "compras" }}
          · {{ moneda(abierto.resumen.gastado) }}
          · última: {{ fecha(abierto.resumen.ultima_compra) }}
        </p>

        <label for="c-nombre" class="mt-5 mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Nombre</label>
        <input
          id="c-nombre" v-model="abierto.nombre" type="text" maxlength="120"
          class="min-h-11 w-full rounded-xl border border-marca/20 px-3.5 text-[14px] outline-none focus:border-marca"
        />

        <label for="c-tel" class="mt-3.5 mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Teléfono</label>
        <input
          id="c-tel" v-model="abierto.telefono" type="tel" maxlength="20" inputmode="tel"
          class="min-h-11 w-full rounded-xl border border-marca/20 px-3.5 text-[14px] outline-none focus:border-marca"
        />

        <label for="c-obs" class="mt-3.5 mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Observaciones</label>
        <textarea
          id="c-obs" v-model="abierto.observaciones" rows="2" maxlength="500"
          placeholder="Paga con efectivo, sin cambio de 50. Timbre dañado, llamar al llegar."
          class="w-full resize-y rounded-xl border border-marca/20 px-3.5 py-2.5 text-[14px] outline-none placeholder:text-tinta/35 focus:border-marca"
        ></textarea>

        <!-- Direcciones -->
        <p class="mt-4 mb-2 text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">
          Direcciones
        </p>
        <ul v-if="abierto.direcciones.length" class="mb-2.5 space-y-1.5">
          <li
            v-for="d in abierto.direcciones" :key="d.id"
            class="flex items-start gap-2 rounded-xl border border-marca/12 px-3 py-2.5 text-[13px]"
          >
            <span class="min-w-0 flex-1">
              {{ d.direccion }}
              <span v-if="d.veces_usada > 1" class="text-[11.5px] text-tinta/45">
                · usada {{ d.veces_usada }} veces
              </span>
            </span>
            <button
              @click="sacarDireccion(d)" title="Quitar"
              class="-my-2 -mr-2 grid min-h-11 min-w-11 shrink-0 cursor-pointer place-items-center text-tinta/40 hover:text-alerta"
            >×</button>
          </li>
        </ul>
        <div class="flex gap-2">
          <input
            v-model="nuevaDireccion" type="text" maxlength="250"
            placeholder="Otra dirección…" @keyup.enter="sumarDireccion"
            class="min-h-11 flex-1 rounded-xl border border-marca/20 px-3 text-[13px] outline-none focus:border-marca"
          />
          <button
            @click="sumarDireccion"
            class="min-h-11 cursor-pointer rounded-xl border border-marca/20 px-3.5 text-[12.5px] font-semibold text-marca hover:border-marca"
          >Agregar</button>
        </div>

        <div class="mt-6 flex gap-2.5">
          <button
            @click="confirmandoBorrado = abierto"
            class="min-h-12 cursor-pointer rounded-2xl border border-alerta/30 px-4 text-[13px] font-semibold text-alerta"
          >Eliminar</button>
          <button
            @click="guardar"
            class="min-h-12 flex-1 cursor-pointer rounded-2xl bg-marca text-[14px] font-bold text-lienzo"
          >Guardar</button>
        </div>
      </div>
    </div>

    <!-- ===== Confirmar borrado ===== -->
    <div
      v-if="confirmandoBorrado"
      class="fixed inset-0 z-60 flex items-center justify-center bg-tinta/55 p-4 backdrop-blur-sm"
      @click.self="confirmandoBorrado = null"
    >
      <div class="w-full max-w-sm rounded-3xl bg-white p-6">
        <h3 class="font-display text-[20px] leading-tight font-light text-marca">
          ¿Eliminar a {{ confirmandoBorrado.nombre }}?
        </h3>
        <p class="mt-2.5 text-[13.5px] leading-snug text-tinta/65">
          Se borran su nombre, teléfono, direcciones y observaciones.
        </p>
        <p class="mt-2 text-[13.5px] leading-snug text-tinta/65">
          <strong class="text-tinta">Sus ventas no se borran</strong>: quedan en el historial
          con el nombre que tenían al momento de venderse.
        </p>
        <div class="mt-5 flex gap-2.5">
          <button
            @click="confirmandoBorrado = null"
            class="min-h-12 flex-1 cursor-pointer rounded-2xl border border-marca/20 text-[14px] font-semibold text-marca"
          >Cancelar</button>
          <button
            @click="eliminar"
            class="min-h-12 flex-1 cursor-pointer rounded-2xl bg-alerta text-[14px] font-bold text-white"
          >Eliminar</button>
        </div>
      </div>
    </div>
  </MarcoInterno>
</template>
