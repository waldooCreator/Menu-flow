<script setup>
/**
 * Administración de mesas (SPEC-001, el pendiente más viejo del proyecto):
 * crear, desactivar, y el QR listo para imprimir y pegar en la mesa.
 *
 * El QR no se guarda en ningún lado: es la URL `/m/<codigo>` dibujada aquí
 * mismo con la misma librería que dibuja el QR del pedido. Regenerar el
 * código invalida el impreso anterior — esa es su utilidad (se filtró una
 * foto del QR de una mesa y alguien pide desde su casa: se regenera y ya).
 */
import { onMounted, ref } from "vue";
import QRCode from "qrcode";
import { listarMesasAdmin, guardarMesa, regenerarCodigoMesa } from "../../api/administracion";
import { nombreRestaurante } from "../../lib/tema";
import MarcoInterno from "../../components/MarcoInterno.vue";
import AdminPestanas from "../../components/AdminPestanas.vue";

const mesas = ref([]);
const cargando = ref(true);
const mensaje = ref(null);
const nuevoNombre = ref("");
const qrAbierto = ref(null); // { mesa, dataUrl, url }

function avisar(texto, error = false) {
  mensaje.value = { texto, error };
  setTimeout(() => (mensaje.value = null), 3000);
}

async function cargar() {
  mesas.value = await listarMesasAdmin();
  cargando.value = false;
}

async function crear() {
  const nombre = nuevoNombre.value.trim();
  if (!nombre) return;
  try {
    await guardarMesa(null, { nombre });
    nuevoNombre.value = "";
    await cargar();
    avisar(`«${nombre}» creada — imprime su QR con el botón`);
  } catch {
    avisar("No se pudo crear la mesa.", true);
  }
}

async function alternarActiva(mesa) {
  mesa.activa = !mesa.activa;
  try {
    await guardarMesa(mesa.id, { activa: mesa.activa });
    avisar(mesa.activa ? `«${mesa.nombre}» activada` : `«${mesa.nombre}» desactivada — su QR deja de funcionar`);
  } catch {
    mesa.activa = !mesa.activa;
    avisar("No se pudo cambiar.", true);
  }
}

async function regenerar(mesa) {
  const r = await regenerarCodigoMesa(mesa.id);
  mesa.codigo = r.codigo;
  avisar(`Código nuevo para «${mesa.nombre}»: el QR impreso anterior ya no vale.`);
  if (qrAbierto.value?.mesa.id === mesa.id) await verQr(mesa);
}

/**
 * La URL del QR usa el ORIGEN ACTUAL del navegador: en desarrollo la IP
 * local, en producción el dominio del restaurante. Nada que configurar.
 */
async function verQr(mesa) {
  const url = `${location.origin}/m/${mesa.codigo}`;
  const dataUrl = await QRCode.toDataURL(url, { errorCorrectionLevel: "M", scale: 10, margin: 2 });
  qrAbierto.value = { mesa, dataUrl, url };
}

function descargarQr() {
  const { mesa, dataUrl } = qrAbierto.value;
  const enlace = document.createElement("a");
  enlace.href = dataUrl;
  enlace.download = `qr-${(nombreRestaurante() || "mesa").toLowerCase()}-${mesa.nombre.toLowerCase().replace(/\s+/g, "-")}.png`;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Mesas" ancho="max-w-3xl">
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
      <div class="overflow-hidden rounded-xl border border-panel-borde bg-white">
        <div class="divide-y divide-panel-borde">
          <div
            v-for="m in mesas" :key="m.id"
            class="flex flex-wrap items-center gap-3 px-4 py-3"
            :class="{ 'opacity-50': !m.activa }"
          >
            <div class="min-w-0 flex-1 basis-full sm:basis-auto">
              <p class="text-[14px] font-semibold">{{ m.nombre }}</p>
              <p class="font-mono text-[12px] text-panel-tinta/50">/m/{{ m.codigo }}
                <span v-if="m.pedidos_historicos" class="ml-1 font-sans">
                  · {{ m.pedidos_historicos }} {{ m.pedidos_historicos === 1 ? "pedido" : "pedidos" }}</span>
              </p>
            </div>

            <button
              @click="verQr(m)"
              class="cursor-pointer rounded-lg bg-panel-marca px-3 py-1.5 text-[12px] font-semibold text-white"
            >Ver QR</button>
            <button
              @click="regenerar(m)"
              class="cursor-pointer rounded-lg border border-panel-borde px-3 py-1.5 text-[12px] font-semibold"
            >Regenerar</button>
            <button
              @click="alternarActiva(m)"
              class="cursor-pointer rounded-full px-3 py-1.5 text-[11px] font-bold tracking-wide uppercase"
              :class="m.activa ? 'bg-emerald-100 text-emerald-800' : 'bg-alerta/10 text-alerta'"
            >{{ m.activa ? "Activa" : "Inactiva" }}</button>
          </div>
        </div>
      </div>

      <p class="mt-2 text-[12px] text-panel-tinta/45">
        Las mesas no se borran: una mesa con pedidos es parte del historial de ventas.
        Desactívala y su QR deja de funcionar.
      </p>

      <div class="mt-4 flex gap-2">
        <input
          v-model="nuevoNombre" type="text" maxlength="40"
          placeholder="Nueva mesa (p.ej. Mesa 14, Terraza 2)…" @keyup.enter="crear"
          class="flex-1 rounded-lg border border-panel-borde bg-white px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
        />
        <button
          @click="crear"
          class="cursor-pointer rounded-lg bg-panel-marca px-4 py-2.5 text-[13px] font-semibold text-white"
        >Crear</button>
      </div>
    </template>

    <!-- ===== QR listo para imprimir ===== -->
    <div
      v-if="qrAbierto"
      class="fixed inset-0 z-50 flex items-center justify-center bg-panel-tinta/50 p-5 backdrop-blur-sm"
      @click.self="qrAbierto = null"
    >
      <div class="w-full max-w-xs rounded-2xl bg-white p-6 text-center">
        <h2 class="text-[16px] font-semibold">{{ qrAbierto.mesa.nombre }}</h2>
        <img :src="qrAbierto.dataUrl" alt="QR de la mesa" class="mx-auto my-4 w-56" />
        <p class="mb-4 font-mono text-[11px] break-all text-panel-tinta/50">{{ qrAbierto.url }}</p>
        <div class="grid gap-2">
          <button
            @click="descargarQr"
            class="min-h-11 cursor-pointer rounded-lg bg-panel-marca text-[13px] font-semibold text-white"
          >Descargar para imprimir</button>
          <button
            @click="qrAbierto = null"
            class="min-h-11 cursor-pointer text-[13px] font-semibold text-panel-tinta/50"
          >Cerrar</button>
        </div>
      </div>
    </div>
  </MarcoInterno>
</template>
