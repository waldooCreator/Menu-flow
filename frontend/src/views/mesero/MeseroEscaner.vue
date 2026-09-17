<script setup>
/**
 * El mesero recibe el pedido del cliente (SPEC-004, Camino A):
 * escanea el QR con la cámara, o sube una imagen de él. Solo aquí, con
 * sesión, se crea el pedido de verdad (ADR-002).
 *
 * El Camino B (armar el pedido desde cero, si el cliente no usó la app)
 * vive en /mesero/pedido.
 *
 * Escaneo con `qr-scanner` (ADR-005): librería JS con la API nativa como
 * acelerador — Safari/iOS no trae BarcodeDetector. La cámara exige contexto
 * seguro (localhost o HTTPS); si no está disponible, queda la vía de imagen.
 */

import { computed, ref, nextTick, onMounted, onUnmounted } from "vue";
import QrScanner from "qr-scanner";
import { decodificarImagen } from "../../lib/qr";
import { verificarPedido, confirmarPedido, listarMesas } from "../../api/pedidos";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const estado = ref("inicio"); // inicio | camara | leyendo | resuelto | confirmando | confirmado | error
const error = ref(null);
const pedido = ref(null);
const textoQr = ref(null);
const pedidoCreado = ref(null);
const video = ref(null);
let escaner = null;

// Mesa elegida a mano: solo hace falta cuando el QR no la trae (el cliente
// entró por el enlace general, no escaneando el QR de su mesa — SPEC-001).
const mesas = ref([]);
const mesaElegida = ref("");

const moneda = { format: formatearMoneda };

const agotadosEnPedido = computed(() =>
  (pedido.value?.items ?? []).filter((item) => !item.disponible)
);
const nombresAgotados = computed(() =>
  agotadosEnPedido.value.map((item) => `«${item.nombre}»`).join(", ")
);

/**
 * Un domicilio **no tiene mesa**, y eso no es un dato que falte: es que no
 * existe. Sin distinguirlo, la pantalla pedía elegir mesa y dejaba el botón
 * de enviar deshabilitado, así que un domicilio no se podía confirmar desde
 * aquí (SPEC-019).
 */
const esDomicilio = computed(() => !!pedido.value?.es_domicilio);
const faltaMesa = computed(
  () => !esDomicilio.value && !pedido.value?.mesa_nombre && !mesaElegida.value
);

// Costo de envío (SPEC-013/025): solo domicilios, opcional — vacío es gratis.
const costoEnvio = ref("");

onMounted(async () => {
  try {
    mesas.value = await listarMesas();
  } catch {
    // Si falla, el flujo con QR que sí trae mesa sigue funcionando igual.
  }
});

/* --- Cámara ------------------------------------------------------------ */

async function abrirCamara() {
  estado.value = "camara";
  error.value = null;
  await nextTick();
  escaner = new QrScanner(video.value, (r) => alDetectar(r.data), {
    returnDetailedScanResult: true,
    highlightScanRegion: true,
    preferredCamera: "environment",
  });
  try {
    await escaner.start();
  } catch {
    cerrarCamara();
    error.value = "No se pudo acceder a la cámara. Usa la opción de subir imagen.";
    estado.value = "error";
  }
}

function cerrarCamara() {
  if (escaner) {
    escaner.stop();
    escaner.destroy();
    escaner = null;
  }
}

function alDetectar(texto) {
  cerrarCamara();
  procesarTexto(texto);
}

onUnmounted(cerrarCamara);

/* --- Imagen ------------------------------------------------------------ */

async function alSeleccionarArchivo(evento) {
  const archivo = evento.target.files[0];
  // Se limpia ya mismo: si no, seleccionar el MISMO archivo dos veces
  // seguidas no dispara "change" y el mesero se queda sin poder reintentar.
  evento.target.value = "";
  if (!archivo) return;
  estado.value = "leyendo";
  error.value = null;

  let texto;
  try {
    // `<img>` no decodifica cualquier archivo que la cámara del teléfono
    // entregue como "foto" (HEIC de iPhone, o un archivo dañado): sin este
    // try/catch, ese rechazo quedaba sin manejar y la pantalla se congelaba
    // para siempre en "Leyendo el código…".
    texto = await decodificarImagen(archivo);
  } catch {
    error.value = "No se pudo abrir esa imagen. Prueba con otra foto (JPG o PNG) o usa la cámara.";
    estado.value = "error";
    return;
  }
  if (!texto) {
    error.value = "No se pudo leer un QR en esa imagen.";
    estado.value = "error";
    return;
  }
  procesarTexto(texto);
}

/* --- Común: verificar y confirmar --------------------------------------- */

async function procesarTexto(texto) {
  estado.value = "leyendo";
  try {
    pedido.value = await verificarPedido(texto);
    textoQr.value = texto;
    estado.value = "resuelto";
  } catch (e) {
    error.value = e.response?.data?.detalle || "El código no es válido.";
    estado.value = "error";
  }
}

async function confirmar() {
  estado.value = "confirmando";
  error.value = null;
  try {
    const envio = esDomicilio.value && costoEnvio.value !== "" ? Number(costoEnvio.value) : null;
    pedidoCreado.value = await confirmarPedido(textoQr.value, mesaElegida.value, null, envio);
    estado.value = "confirmado";
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo enviar el pedido.";
    // Si solo falta la mesa, no se pierde el pedido leído.
    estado.value = e.response?.data?.falta_mesa ? "resuelto" : "error";
  }
}

function reiniciar() {
  cerrarCamara();
  estado.value = "inicio";
  error.value = null;
  pedido.value = null;
  textoQr.value = null;
  pedidoCreado.value = null;
  mesaElegida.value = "";
  costoEnvio.value = "";
}
</script>

<template>
  <MarcoInterno titulo="Recibir pedido" ancho="max-w-2xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <!-- ===== Inicio: las tres formas de tomar un pedido ===== -->
    <div v-if="estado === 'inicio'" class="grid gap-4 sm:grid-cols-3">
      <button
        @click="abrirCamara"
        class="cursor-pointer rounded-3xl border border-marca/10 bg-white p-7 text-center transition-transform hover:-translate-y-0.5"
      >
        <span class="mx-auto mb-4 grid size-14 place-items-center rounded-full bg-marca-suave text-marca">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" stroke-linejoin="round" />
            <circle cx="12" cy="13" r="4" />
          </svg>
        </span>
        <span class="block font-semibold">Escanear con cámara</span>
        <span class="mt-1 block text-[13px] text-tinta/55">Apunta al QR del cliente</span>
      </button>

      <label
        class="cursor-pointer rounded-3xl border border-marca/10 bg-white p-7 text-center transition-transform hover:-translate-y-0.5"
      >
        <span class="mx-auto mb-4 grid size-14 place-items-center rounded-full bg-marca-suave text-marca">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.7">
            <rect x="3" y="3" width="18" height="18" rx="3" />
            <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" stroke="none" />
            <path d="M21 15l-5-5L5 21" stroke-linejoin="round" />
          </svg>
        </span>
        <span class="block font-semibold">Subir imagen del QR</span>
        <span class="mt-1 block text-[13px] text-tinta/55">Una foto o captura</span>
        <input type="file" accept="image/*" class="hidden" @change="alSeleccionarArchivo" />
      </label>

      <RouterLink
        :to="{ name: 'mesero-pedido' }"
        class="cursor-pointer rounded-3xl border border-marca/10 bg-white p-7 text-center transition-transform hover:-translate-y-0.5"
      >
        <span class="mx-auto mb-4 grid size-14 place-items-center rounded-full bg-acento text-tinta">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.9">
            <path d="M12 5v14M5 12h14" stroke-linecap="round" />
          </svg>
        </span>
        <span class="block font-semibold">Crear pedido</span>
        <span class="mt-1 block text-[13px] text-tinta/55">Si el cliente no usó la app</span>
      </RouterLink>
    </div>

    <!-- ===== Cámara en vivo ===== -->
    <div v-else-if="estado === 'camara'" class="text-center">
      <div class="overflow-hidden rounded-3xl border border-marca/10 bg-black">
        <video ref="video" class="aspect-square w-full object-cover"></video>
      </div>
      <p class="mt-4 text-[14px] text-tinta/60">Apunta la cámara al QR que muestra el cliente.</p>
      <button
        @click="reiniciar"
        class="mt-4 cursor-pointer rounded-full border border-marca/20 px-7 py-3 text-sm font-semibold text-marca transition-colors hover:border-marca"
      >Cancelar</button>
    </div>

    <!-- ===== Leyendo ===== -->
    <p v-else-if="estado === 'leyendo'" class="py-14 text-center text-tinta/50">Leyendo el código…</p>

    <!-- ===== Error ===== -->
    <div v-else-if="estado === 'error'" class="rounded-3xl border border-alerta/20 bg-white p-6 text-center">
      <p class="font-medium text-alerta">{{ error }}</p>
      <button
        @click="reiniciar"
        class="mt-5 cursor-pointer rounded-full bg-marca px-7 py-3 text-sm font-semibold tracking-[0.06em] text-lienzo uppercase"
      >Intentar de nuevo</button>
    </div>

    <!-- ===== Confirmado ===== -->
    <div v-else-if="estado === 'confirmado'" class="rounded-3xl border border-marca/10 bg-white p-8 text-center">
      <span class="mx-auto mb-4 grid size-16 place-items-center rounded-full bg-marca-suave text-marca">
        <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M20 6L9 17l-5-5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
      <p class="font-display text-2xl font-light text-marca">Pedido #{{ pedidoCreado.pedido_id }} enviado a cocina</p>
      <p class="mt-2 text-[14px] text-tinta/60">Las estaciones ya lo tienen en su tablero.</p>
      <button
        @click="reiniciar"
        class="mt-6 cursor-pointer rounded-full bg-marca px-8 py-3.5 text-sm font-semibold tracking-[0.08em] text-lienzo uppercase"
      >Recibir otro pedido</button>
    </div>

    <!-- ===== Pedido resuelto, pendiente de enviar ===== -->
    <div v-else class="rounded-3xl border border-marca/10 bg-white p-6">
      <p v-if="pedido.ya_usado" class="mb-4 rounded-2xl bg-alerta/8 px-4 py-3 text-sm font-semibold text-alerta">
        Este QR ya fue usado en otro pedido.
      </p>

      <p
        v-if="agotadosEnPedido.length"
        class="mb-4 rounded-2xl bg-alerta/10 px-4 py-3 text-sm font-semibold text-alerta"
      >{{ nombresAgotados }} se agotó. Pídele al cliente que elija otra cosa.</p>

      <p v-if="pedido.mesa_nombre" class="font-display text-2xl font-light text-marca">
        {{ pedido.mesa_nombre }}
        <span v-if="pedido.nombre_cliente" class="font-sans text-base text-tinta/55">
          · {{ pedido.nombre_cliente }}
        </span>
      </p>

      <!-- Domicilio: no hay mesa que elegir, hay una dirección a la que llegar -->
      <div v-else-if="esDomicilio" class="rounded-2xl bg-marca/6 p-4">
        <p class="text-[11px] font-semibold tracking-[0.12em] text-marca/60 uppercase">
          Domicilio
        </p>
        <p class="mt-1 font-display text-[19px] leading-tight font-light text-marca">
          {{ pedido.nombre_cliente || "Sin nombre" }}
        </p>
        <p v-if="pedido.telefono" class="mt-0.5 text-[13px] text-tinta/60">
          {{ pedido.telefono }}
        </p>
        <p v-if="pedido.direccion" class="mt-1.5 text-[13.5px] leading-snug text-tinta">
          {{ pedido.direccion }}
        </p>

        <!-- Costo de envío (SPEC-013/025): opcional, se suma al total al confirmar -->
        <label for="costo-envio" class="mt-3 block text-[12px] font-bold text-marca/80">
          Costo del envío (opcional)
        </label>
        <div class="mt-1 flex items-center gap-2">
          <span class="text-sm text-tinta/60">$</span>
          <input
            id="costo-envio" v-model="costoEnvio" type="number" min="0" step="500"
            inputmode="numeric" placeholder="0"
            class="min-h-11 w-full rounded-xl border border-marca/20 bg-white px-3 text-sm outline-none focus:border-marca"
          />
        </div>
      </div>

      <!-- El QR no trae mesa: el mesero la indica — él está ahí y sabe dónde
           está sentado el cliente -->
      <div v-else class="rounded-2xl bg-amber-50 p-4">
        <label for="mesa" class="block text-[13px] font-bold text-amber-900">
          ¿En qué mesa está el cliente?
        </label>
        <p class="mt-0.5 mb-2.5 text-xs text-amber-800/70">
          Este código no trae la mesa porque el cliente no escaneó el QR de su mesa.
        </p>
        <select
          id="mesa" v-model="mesaElegida"
          class="w-full cursor-pointer rounded-xl border border-amber-300 bg-white px-3.5 py-3 text-sm"
        >
          <option value="">Selecciona la mesa…</option>
          <option v-for="m in mesas" :key="m.codigo" :value="m.codigo">{{ m.nombre }}</option>
        </select>
        <p v-if="pedido.nombre_cliente" class="mt-2 text-[13px] text-amber-900">
          Cliente: {{ pedido.nombre_cliente }}
        </p>
      </div>

      <!-- Ya le hemos vendido a ese teléfono (SPEC-019).
           Se muestra ANTES de confirmar a propósito: es lo que convierte un
           dígito mal escrito en un error visible, en vez de un cliente
           duplicado en silencio. Y es donde aparecen sus observaciones, que
           es lo único que las hace útiles al tomar el pedido. -->
      <div
        v-if="pedido.cliente_conocido"
        class="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4"
      >
        <p class="text-[11px] font-semibold tracking-[0.12em] text-emerald-800/70 uppercase">
          Cliente conocido
        </p>
        <p class="mt-1 text-[14px] font-semibold text-emerald-900">
          {{ pedido.cliente_conocido.nombre }}
          <span class="font-normal text-emerald-800/70">
            · {{ pedido.cliente_conocido.compras }}
            {{ pedido.cliente_conocido.compras === 1 ? "compra" : "compras" }}
          </span>
        </p>
        <p
          v-if="pedido.cliente_conocido.observaciones"
          class="mt-2 text-[13.5px] leading-snug font-medium text-emerald-900"
        >{{ pedido.cliente_conocido.observaciones }}</p>
        <ul
          v-if="pedido.cliente_conocido.direcciones.length"
          class="mt-2 space-y-0.5 text-[12.5px] text-emerald-900/70"
        >
          <li v-for="d in pedido.cliente_conocido.direcciones" :key="d.id">
            {{ d.direccion }}<template v-if="d.indicaciones"> — {{ d.indicaciones }}</template>
          </li>
        </ul>
      </div>

      <ul class="my-4">
        <li
          v-for="it in pedido.items" :key="it.plato_id"
          class="border-b border-marca/10 py-3.5 last:border-b-0"
          :class="{ 'opacity-60': !it.disponible }"
        >
          <div class="flex justify-between gap-3">
            <strong class="text-[15px] font-medium">{{ it.cantidad }}× {{ it.nombre }}</strong>
            <span class="shrink-0 font-medium whitespace-nowrap text-marca">
              {{ moneda.format(it.precio * it.cantidad) }}
            </span>
          </div>
          <p v-if="it.observacion" class="mt-1 text-[13px] font-medium text-amber-700">{{ it.observacion }}</p>
          <p v-if="!it.disponible" class="mt-1 text-xs font-semibold text-alerta">Ya no está disponible</p>
        </li>
      </ul>

      <p v-if="error" class="mb-3 text-[13px] font-semibold text-alerta">{{ error }}</p>

      <div class="flex gap-3">
        <button
          @click="reiniciar"
          class="flex-1 cursor-pointer rounded-full border border-marca/20 py-3.5 text-sm font-semibold text-marca transition-colors hover:border-marca"
        >Cancelar</button>
        <button
          @click="confirmar"
          :disabled="estado === 'confirmando' || pedido.ya_usado || agotadosEnPedido.length || faltaMesa"
          class="flex-1 cursor-pointer rounded-full bg-marca py-3.5 text-sm font-semibold tracking-[0.06em] text-lienzo uppercase transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >{{ estado === "confirmando" ? "Enviando…" : "Enviar a cocina" }}</button>
      </div>
    </div>
  </MarcoInterno>
</template>
