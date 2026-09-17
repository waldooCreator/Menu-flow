<script setup>
/**
 * Vista de salón (SPEC-012): qué mesas están libres y cuáles ocupadas.
 *
 * La regla de oro de la spec manda sobre todo lo demás: **el mesero manda,
 * el sistema nunca espera ni adivina**. Por eso aquí no hay temporizadores
 * que liberen mesas solas, no hay diálogos de confirmación (confirmar es
 * hacer esperar) y ninguna acción queda bloqueada por el estado de un
 * pedido — liberar funciona incluso con comida en el fuego, porque el caso
 * real es el cliente que empacó y se fue.
 *
 * Liberar la mesa NO cierra el pedido: son dos cosas independientes.
 */
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { listarSalon, cambiarEstadoMesa, listarPedidosActivos, cambiarDestino, entregarPedido } from "../../api/pedidos";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const router = useRouter();
const moneda = { format: formatearMoneda };
const mesas = ref([]);
const domicilios = ref([]);
const cargando = ref(true);
const mesaAbierta = ref(null);
const ahora = ref(Date.now());

// Estilo por estado. El color es la información principal de esta pantalla,
// así que cada estado se distingue por color Y por texto — nunca solo por
// color, que dejaría fuera a quien no lo distingue.
const ESTILOS = {
  libre: {
    etiqueta: "Libre",
    plural: "libres",
    tarjeta: "bg-white border-marca/12",
    punto: "bg-emerald-500",
    texto: "text-emerald-700",
  },
  apartada: {
    etiqueta: "Apartada",
    plural: "apartadas",
    tarjeta: "bg-amber-50 border-amber-300",
    punto: "bg-amber-500",
    texto: "text-amber-800",
  },
  ocupada: {
    etiqueta: "Ocupada",
    plural: "ocupadas",
    tarjeta: "bg-red-50 border-red-400",
    punto: "bg-red-500",
    texto: "text-red-700",
  },
};

const estilo = (estado) => ESTILOS[estado] ?? ESTILOS.libre;

const resumen = computed(() => {
  const c = { libre: 0, apartada: 0, ocupada: 0 };
  for (const m of mesas.value) if (c[m.estado] !== undefined) c[m.estado] += 1;
  return c;
});

function minutosDesde(iso) {
  if (!iso) return null;
  return Math.floor((ahora.value - new Date(iso).getTime()) / 60000);
}

function tiempoLegible(iso) {
  const min = minutosDesde(iso);
  if (min === null || min < 1) return null;
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  return `${h} h ${min % 60} min`;
}

async function cargar() {
  try {
    const salon = await listarSalon();
    mesas.value = salon.mesas;
    domicilios.value = salon.domicilios;
  } finally {
    cargando.value = false;
  }
}

/**
 * Marcar entregado (SPEC-012). Es lo ÚNICO que saca un domicilio de la zona:
 * cobrarlo no lo retira, porque se puede pagar por anticipado o al recibir.
 */
async function entregar(dom) {
  domicilios.value = domicilios.value.filter((d) => d.pedido_id !== dom.pedido_id);
  try {
    await entregarPedido(dom.pedido_id);
  } catch {
    await cargar();
  }
}

function minutosDeDomicilio(iso) {
  return Math.max(0, Math.floor((ahora.value - new Date(iso).getTime()) / 60000));
}

/* --- Al liberar con pedido en curso: preguntar, no dejar huérfano -------- */

/**
 * Atajarlo en el origen (SPEC-011). Antes, liberar una mesa con un pedido
 * en cocina dejaba la tarjeta de la estación apuntando a una mesa donde ya
 * hay otra gente — y el mesero tenía que ir a buscar después ese pedido sin
 * mesa. Es más barato preguntar en el momento.
 *
 * No traba nada: "se queda" es un toque.
 */
const pedidoHuerfano = ref(null); // { mesa, pedidos: [...] }

async function pedidosDeLaMesa(codigo) {
  try {
    const activos = await listarPedidosActivos();
    return activos.filter((p) => p.mesa_codigo === codigo);
  } catch {
    return [];
  }
}

async function liberar(mesa) {
  const enCurso = await pedidosDeLaMesa(mesa.codigo);
  await aplicar(mesa.codigo, "libre");
  if (enCurso.length) pedidoHuerfano.value = { mesa, pedidos: enCurso };
}

async function reubicar(pedido, destino) {
  await cambiarDestino(pedido.id, destino);
  pedidoHuerfano.value = null;
  await cargar();
}

/* --- Deshacer: recuadro abajo a la derecha, 5 segundos (SPEC-012) --------- */

const revertir = ref(null); // { codigo, nombre, estadoAnterior }
let temporizadorRevertir = null;

function ofrecerRevertir(mesa, estadoAnterior) {
  clearTimeout(temporizadorRevertir);
  revertir.value = { codigo: mesa.codigo, nombre: mesa.nombre, estadoAnterior };
  temporizadorRevertir = setTimeout(() => (revertir.value = null), 5000);
}

async function aplicarReversion() {
  const r = revertir.value;
  if (!r) return;
  revertir.value = null;
  clearTimeout(temporizadorRevertir);
  await aplicar(r.codigo, r.estadoAnterior, { ofrecerDeshacer: false });
}

/* --- Acciones ------------------------------------------------------------ */

async function aplicar(codigo, estado, { ofrecerDeshacer = true } = {}) {
  const mesa = mesas.value.find((m) => m.codigo === codigo);
  if (!mesa) return;
  const anterior = mesa.estado;

  // Optimista: la pantalla responde ya. Si la llamada falla se revierte.
  // Hacer esperar al mesero por la red es la misma falta que hacerlo
  // esperar por un diálogo.
  mesa.estado = estado;
  mesa.estado_desde = new Date().toISOString();
  mesaAbierta.value = null;

  try {
    const actualizada = await cambiarEstadoMesa(codigo, estado);
    Object.assign(mesa, actualizada);
    if (ofrecerDeshacer) ofrecerRevertir(mesa, anterior);
  } catch {
    mesa.estado = anterior;
  }
}

function hacerPedido(mesa) {
  // El Camino B de SPEC-004, con la mesa ya elegida.
  router.push({ name: "mesero-pedido", query: { mesa: mesa.codigo } });
}

let reloj = null;
onMounted(() => {
  cargar();
  // Solo mueve el "hace X min" de las tarjetas; no dispara ninguna acción.
  reloj = setInterval(() => (ahora.value = Date.now()), 30000);
});
onUnmounted(() => {
  clearInterval(reloj);
  clearTimeout(temporizadorRevertir);
});
</script>

<template>
  <MarcoInterno titulo="Salón" ancho="max-w-5xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <!-- Resumen: la pregunta que el mesero hace de lejos es "¿cuántas libres?" -->
    <div class="mb-6 flex flex-wrap gap-2.5">
      <span
        v-for="est in ['libre', 'apartada', 'ocupada']"
        :key="est"
        class="inline-flex items-center gap-2 rounded-full border bg-white px-4 py-2 text-[13px] font-bold"
        :class="estilo(est).tarjeta"
      >
        <span class="size-2.5 rounded-full" :class="estilo(est).punto"></span>
        <span :class="estilo(est).texto">{{ resumen[est] }} {{ resumen[est] === 1 ? estilo(est).etiqueta.toLowerCase() : estilo(est).plural }}</span>
      </span>
    </div>

    <p v-if="cargando" class="py-14 text-center text-tinta/50">Cargando el salón…</p>

    <p
      v-else-if="mesas.length === 0"
      class="rounded-3xl border-2 border-dashed border-tinta/10 py-14 text-center text-[14px] font-medium text-tinta/40"
    >
      No hay mesas configuradas todavía.
    </p>

    <div v-else class="grid grid-cols-2 gap-3.5 sm:grid-cols-3 lg:grid-cols-4">
      <button
        v-for="m in mesas"
        :key="m.codigo"
        @click="mesaAbierta = m"
        class="cursor-pointer rounded-3xl border-2 p-5 text-left transition-transform active:scale-[0.98]"
        :class="estilo(m.estado).tarjeta"
      >
        <div class="flex items-start justify-between gap-2">
          <strong class="font-display text-[24px] leading-none font-light text-marca">
            {{ m.nombre }}
          </strong>
          <span class="mt-1 size-3 shrink-0 rounded-full" :class="estilo(m.estado).punto"></span>
        </div>

        <p class="mt-3 text-[12px] font-bold tracking-[0.1em] uppercase" :class="estilo(m.estado).texto">
          {{ estilo(m.estado).etiqueta }}
        </p>

        <!-- Cuánto va la mesa, sin tener que entrar (SPEC-013) -->
        <p v-if="m.cuenta_total > 0" class="mt-1.5 text-[17px] font-semibold text-marca">
          {{ moneda.format(m.cuenta_total) }}
        </p>

        <p v-if="m.estado !== 'libre' && tiempoLegible(m.estado_desde)" class="mt-1 text-[12px] font-semibold text-tinta/45">
          hace {{ tiempoLegible(m.estado_desde) }}
        </p>
      </button>
    </div>

    <!-- ===== Zona de domicilios (SPEC-012) =====
         Aparte de las mesas, porque no ocupan ninguna. Es una LISTA que
         crece, no una rejilla de puestos fijos: un viernes con 30 domicilios
         no debería quedarse sin dónde ponerlos. -->
    <section v-if="!cargando && domicilios.length" class="mt-9">
      <div class="mb-4 flex items-center gap-2.5">
        <h2 class="font-display text-[24px] leading-none font-light text-marca">Domicilios</h2>
        <span class="rounded-full bg-marca px-3 py-1 text-[12px] font-bold text-lienzo">
          {{ domicilios.length }}
        </span>
      </div>

      <!-- `grid-cols-1` explicito: sin el, la columna implicita se dimensiona al
           contenido y la tarjeta media 449px en una pantalla de 375 (SPEC-022 A1) -->
      <div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        <article
          v-for="d in domicilios" :key="d.pedido_id"
          class="rounded-2xl border-2 p-4"
          :class="d.cobrada ? 'border-emerald-300 bg-emerald-50/60' : 'border-marca/12 bg-white'"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <strong class="line-clamp-2 block text-[16px] leading-snug font-semibold text-marca">
                {{ d.cliente || "Sin nombre" }}
              </strong>
              <p class="mt-0.5 text-[12px] font-semibold text-tinta/45">
                Pedido #{{ d.pedido_id }} · hace {{ minutosDeDomicilio(d.creado) }} min
              </p>
            </div>
            <span class="shrink-0 text-[16px] font-semibold text-marca">
              {{ moneda.format(d.total) }}
            </span>
          </div>

          <!-- Cobrado y entregado son independientes: quien reparte necesita
               saber de un vistazo si este ya está pago o si cobra al llegar. -->
          <p
            class="mt-2.5 inline-block rounded-full px-3 py-1 text-[11px] font-bold tracking-[0.08em] uppercase"
            :class="d.cobrada ? 'bg-emerald-600 text-white' : 'bg-amber-100 text-amber-900'"
          >
            {{ d.cobrada ? "Pagado" : "Cobrar al entregar" }}
          </p>

          <div class="mt-3.5 flex gap-2">
            <button
              v-if="!d.cobrada"
              @click="router.push({ name: 'mesero-cuentas' })"
              class="min-h-12 flex-1 cursor-pointer rounded-xl border-2 border-marca text-[13px] font-bold text-marca"
            >Cobrar</button>
            <button
              @click="entregar(d)"
              class="min-h-12 flex-1 cursor-pointer rounded-xl bg-marca text-[13px] font-bold text-lienzo transition-transform active:scale-[0.98]"
            >Marcar entregado</button>
          </div>
        </article>
      </div>
    </section>

    <!-- Panel de acciones. Tres botones, siempre los tres, en cualquier
         estado: el mesero decide, el sistema no le cierra puertas. -->
    <div
      v-if="mesaAbierta"
      class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/55 backdrop-blur-sm sm:items-center"
      @click.self="mesaAbierta = null"
    >
      <div class="w-full rounded-t-[26px] bg-lienzo p-6 sm:max-w-md sm:rounded-[26px]">
        <div class="mb-1 flex items-center gap-2.5">
          <span class="size-3 rounded-full" :class="estilo(mesaAbierta.estado).punto"></span>
          <span class="text-[12px] font-bold tracking-[0.12em] uppercase" :class="estilo(mesaAbierta.estado).texto">
            {{ estilo(mesaAbierta.estado).etiqueta }}
          </span>
        </div>
        <h2 class="font-display text-[32px] leading-none font-light text-marca">
          {{ mesaAbierta.nombre }}
        </h2>

        <div class="mt-6 grid gap-2.5">
          <button
            v-if="mesaAbierta.estado !== 'libre'"
            @click="liberar(mesaAbierta)"
            class="min-h-14 cursor-pointer rounded-2xl bg-marca text-[15px] font-bold text-lienzo transition-transform active:scale-[0.98]"
          >
            Liberar mesa
          </button>

          <button
            v-if="mesaAbierta.estado === 'libre'"
            @click="aplicar(mesaAbierta.codigo, 'apartada')"
            class="min-h-14 cursor-pointer rounded-2xl bg-amber-500 text-[15px] font-bold text-white transition-transform active:scale-[0.98]"
          >
            Apartar — se sentaron
          </button>

          <button
            v-if="mesaAbierta.cuenta_id"
            @click="router.push({ name: 'mesero-cuentas' })"
            class="min-h-14 cursor-pointer rounded-2xl bg-marca text-[15px] font-bold text-lienzo transition-transform active:scale-[0.98]"
          >
            Cobrar {{ moneda.format(mesaAbierta.cuenta_total) }}
          </button>

          <button
            @click="hacerPedido(mesaAbierta)"
            class="min-h-14 cursor-pointer rounded-2xl border-2 border-marca text-[15px] font-bold text-marca transition-transform active:scale-[0.98]"
          >
            Hacer pedido
          </button>

          <button
            @click="mesaAbierta = null"
            class="min-h-12 cursor-pointer text-[14px] font-semibold text-tinta/50"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- La mesa YA quedó libre; esto no bloquea nada, solo evita que el
         pedido se quede apuntando a una mesa donde ahora hay otra gente
         (SPEC-011). "Se queda" es un toque. -->
    <div
      v-if="pedidoHuerfano"
      class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/55 backdrop-blur-sm sm:items-center"
      @click.self="pedidoHuerfano = null"
    >
      <div class="w-full rounded-t-[26px] bg-lienzo p-6 sm:max-w-md sm:rounded-[26px]">
        <h2 class="font-display text-[26px] leading-tight font-light text-marca">
          {{ pedidoHuerfano.mesa.nombre }} quedó libre
        </h2>
        <p class="mt-2 text-[14px] leading-snug text-tinta/65">
          {{ pedidoHuerfano.pedidos.length === 1
            ? "Todavía hay un pedido en cocina para esa mesa."
            : `Todavía hay ${pedidoHuerfano.pedidos.length} pedidos en cocina para esa mesa.` }}
          ¿A dónde va?
        </p>

        <div v-for="p in pedidoHuerfano.pedidos" :key="p.id" class="mt-5 border-t border-marca/12 pt-4">
          <p class="mb-3 text-[13px] font-semibold text-tinta/60">
            Pedido #{{ p.id }} — {{ p.detalles.length }}
            {{ p.detalles.length === 1 ? "plato" : "platos" }}
          </p>
          <div class="grid grid-cols-1 gap-2.5">
            <button
              @click="reubicar(p, { esDomicilio: true })"
              class="min-h-13 cursor-pointer rounded-2xl bg-marca text-[14px] font-bold text-lienzo transition-transform active:scale-[0.98]"
            >Pásalo a domicilio</button>
            <select
              @change="reubicar(p, { mesa: $event.target.value })"
              class="min-h-13 cursor-pointer rounded-2xl border-2 border-marca bg-white px-4 text-[14px] font-bold text-marca"
            >
              <option value="">Muévelo a otra mesa…</option>
              <option
                v-for="m in mesas.filter((x) => x.codigo !== pedidoHuerfano.mesa.codigo)"
                :key="m.codigo" :value="m.codigo"
              >{{ m.nombre }}</option>
            </select>
          </div>
        </div>

        <button
          @click="pedidoHuerfano = null"
          class="mt-5 min-h-12 w-full cursor-pointer text-[14px] font-semibold text-tinta/50"
        >Se queda donde está</button>
      </div>
    </div>

    <!-- Deshacer, 5 s. No hay diálogo de confirmación a propósito: se actúa
         primero y se ofrece volver atrás (SPEC-012). -->
    <Transition
      enter-from-class="translate-y-4 opacity-0" leave-to-class="translate-y-4 opacity-0"
      enter-active-class="transition duration-200" leave-active-class="transition duration-200"
    >
      <div
        v-if="revertir"
        class="fixed right-4 bottom-4 z-50 flex items-center gap-3 rounded-2xl bg-tinta px-4 py-3.5 text-lienzo shadow-lg"
      >
        <span class="text-[13px] font-semibold">{{ revertir.nombre }} actualizada</span>
        <button
          @click="aplicarReversion"
          class="cursor-pointer rounded-full bg-lienzo/15 px-4 py-2 text-[12px] font-bold tracking-[0.08em] uppercase transition-colors hover:bg-lienzo/25"
        >
          Revertir
        </button>
      </div>
    </Transition>
  </MarcoInterno>
</template>
