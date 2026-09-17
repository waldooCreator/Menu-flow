<script setup>
/**
 * Cuentas por cobrar (SPEC-013).
 *
 * Es la pantalla de "qué se sirvió y todavía nadie pagó". Aquí se cobra, y
 * de aquí sale el dinero que después tiene que cuadrar con la caja.
 *
 * Regla vigente desde 2026-09-16: **cobrar significa que el cliente pagó
 * para irse**, y la mesa queda libre en el mismo paso — salvo que se marque
 * pago anticipado, que la deja ocupada (decisión del autor).
 */
import { computed, onMounted, onUnmounted, ref } from "vue";
import { listarCuentas, obtenerCuenta, cerrarCuenta, anularCuenta } from "../../api/cuentas";
import { listarCajas } from "../../api/caja";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const cuentas = ref([]);
const mediosPago = ref([]);
const cargando = ref(true);
const abierta = ref(null);      // cuenta con detalle
const error = ref(null);
const cobrando = ref(false);
const aplicaPropina = ref(true);
const medioElegido = ref(null);
const anulando = ref(false);
const motivo = ref("");
// Pago anticipado: el cliente paga y sigue en la mesa (SPEC-013, 2026-09-16).
const anticipado = ref(false);
const aviso = ref(null);
// Vuelto (SPEC-025): solo aplica en efectivo, y es opcional.
const recibido = ref("");

const moneda = { format: formatearMoneda };

const cajaElegida = computed(() => mediosPago.value.find((m) => m.id === medioElegido.value));
const esEfectivo = computed(() => cajaElegida.value?.tipo === "efectivo");
/** Lo que falta o sobra, calculado en el momento — el servidor recalcula igual al cobrar. */
const vuelto = computed(() => {
  if (!esEfectivo.value || recibido.value === "" || !abierta.value) return null;
  return Number(recibido.value) - totalCuenta.value;
});
const totalCuenta = computed(() =>
  abierta.value ? abierta.value.subtotal + (aplicaPropina.value ? abierta.value.propina : 0)
    + abierta.value.impuesto + (abierta.value.envio || 0) : 0
);

const totalPorCobrar = computed(() =>
  cuentas.value.reduce((t, c) => t + c.total, 0)
);

async function cargar() {
  try {
    cuentas.value = await listarCuentas("abierta");
  } finally {
    cargando.value = false;
  }
}

async function abrir(cuenta) {
  error.value = null;
  motivo.value = "";
  anulando.value = false;
  abierta.value = await obtenerCuenta(cuenta.id);
  aplicaPropina.value = abierta.value.aplica_propina;
  anticipado.value = false;
  recibido.value = "";
  medioElegido.value = mediosPago.value[0]?.id ?? null;
}

async function cobrar() {
  if (!medioElegido.value) {
    error.value = "Elige con qué medio de pago se cobró.";
    return;
  }
  if (esEfectivo.value && vuelto.value !== null && vuelto.value < 0) {
    error.value = `Faltan ${moneda.format(-vuelto.value)}: eso no alcanza para cobrar la cuenta.`;
    return;
  }
  cobrando.value = true;
  error.value = null;
  try {
    const liberar = !anticipado.value && !!abierta.value.mesa_codigo;
    const recibidoEfectivo = esEfectivo.value && recibido.value !== "" ? Number(recibido.value) : null;
    const cerrada = await cerrarCuenta(
      abierta.value.id, medioElegido.value, aplicaPropina.value, liberar, recibidoEfectivo);
    abierta.value = null;
    await cargar();
    const destino = cerrada.destino;
    // El vuelto es lo primero que quien cobra necesita ver (SPEC-025).
    const vueltoTexto = cerrada.vuelto_efectivo ? ` · Vuelto: ${moneda.format(cerrada.vuelto_efectivo)}` : "";
    if (!cerrada.mesa_codigo) {
      aviso.value = `${destino} cobrado: ${moneda.format(cerrada.total)} · ${cerrada.medio_pago}${vueltoTexto}`;
    } else if (liberar) {
      aviso.value = `${destino} cobrada y libre: ${moneda.format(cerrada.total)} · ${cerrada.medio_pago}${vueltoTexto}`;
    } else {
      aviso.value = `${destino} cobrada por anticipado: la mesa sigue ocupada. Si piden algo más, es un pedido nuevo.${vueltoTexto}`;
    }
    setTimeout(() => (aviso.value = null), vueltoTexto ? 9000 : 6000);
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo cobrar la cuenta.";
  } finally {
    cobrando.value = false;
  }
}

async function confirmarAnulacion() {
  error.value = null;
  try {
    await anularCuenta(abierta.value.id, motivo.value);
    abierta.value = null;
    await cargar();
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo anular.";
  }
}

let temporizador = null;
onMounted(async () => {
  await cargar();
  mediosPago.value = await listarCajas();
  temporizador = setInterval(cargar, 10000);
});
onUnmounted(() => clearInterval(temporizador));
</script>

<template>
  <MarcoInterno titulo="Cuentas por cobrar" ancho="max-w-3xl">
    <p v-if="aviso" role="status" class="mb-4 rounded-xl bg-emerald-50 px-3.5 py-2.5 text-[13px] font-semibold text-emerald-800">{{ aviso }}</p>
    <template #acciones><NotificacionesBurbuja /></template>

    <div v-if="!cargando && cuentas.length" class="mb-6 rounded-2xl border border-marca/12 bg-white px-5 py-4">
      <p class="text-[11px] font-semibold tracking-[0.14em] text-marca/60 uppercase">Sin cobrar</p>
      <p class="mt-1 font-display text-[30px] leading-none font-light text-marca">
        {{ moneda.format(totalPorCobrar) }}
      </p>
      <p class="mt-1 text-[12px] text-tinta/45">
        {{ cuentas.length }} {{ cuentas.length === 1 ? "cuenta abierta" : "cuentas abiertas" }}
      </p>
    </div>

    <p v-if="cargando" class="py-14 text-center text-tinta/50">Cargando cuentas…</p>

    <p
      v-else-if="cuentas.length === 0"
      class="rounded-3xl border-2 border-dashed border-tinta/10 py-14 text-center text-[14px] font-medium text-tinta/40"
    >
      No hay cuentas por cobrar.
    </p>

    <div v-else class="grid gap-3">
      <button
        v-for="c in cuentas" :key="c.id"
        @click="abrir(c)"
        class="cursor-pointer rounded-2xl border border-marca/12 bg-white p-5 text-left transition-transform active:scale-[0.99]"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <strong class="font-display text-[22px] leading-none font-light text-marca">
              {{ c.destino }}
            </strong>
            <p class="mt-1.5 text-[12px] font-semibold text-tinta/45">Cuenta #{{ c.id }}</p>
          </div>
          <span class="shrink-0 text-[17px] font-semibold text-marca">{{ moneda.format(c.total) }}</span>
        </div>
      </button>
    </div>

    <!-- ===== Panel de cobro ===== -->
    <div
      v-if="abierta"
      class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/55 backdrop-blur-sm sm:items-center"
      @click.self="abierta = null"
    >
      <div class="flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-t-[26px] bg-lienzo sm:max-w-md sm:rounded-[26px]">
        <header class="shrink-0 border-b border-marca/15 px-5 py-5">
          <p class="text-[11px] font-semibold tracking-[0.16em] text-marca/60 uppercase">
            Cuenta #{{ abierta.id }}
          </p>
          <h2 class="font-display text-[28px] leading-none font-light text-marca">{{ abierta.destino }}</h2>
        </header>

        <div class="flex-1 overflow-y-auto overscroll-contain px-5 py-4">
          <p v-if="error" class="mb-3.5 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
            {{ error }}
          </p>

          <!-- Consumo, agrupado por pedido: es como se fue pidiendo -->
          <template v-for="p in abierta.pedidos" :key="p.id">
            <ul class="mb-2.5">
              <li v-for="(d, i) in p.detalles" :key="i" class="flex justify-between gap-3 py-1 text-[15px]">
                <span>
                  {{ d.cantidad }}× {{ d.nombre }}
                  <span v-if="d.observacion" class="text-[13px] font-semibold text-amber-700">
                    — {{ d.observacion }}
                  </span>
                </span>
                <span class="shrink-0 font-medium text-marca">{{ moneda.format(d.precio * d.cantidad) }}</span>
              </li>
            </ul>
          </template>

          <div class="mt-4 border-t border-marca/15 pt-4 text-[15px]">
            <div class="flex justify-between py-1">
              <span class="text-tinta/60">Subtotal</span>
              <span class="font-medium">{{ moneda.format(abierta.subtotal) }}</span>
            </div>

            <!-- La propina es VOLUNTARIA: tiene que poder quitarse -->
            <label class="flex cursor-pointer items-center justify-between gap-3 py-1">
              <span class="flex items-center gap-2 text-tinta/60">
                <span class="-m-2.5 grid min-h-11 min-w-11 place-items-center p-2.5"><input type="checkbox" v-model="aplicaPropina" class="size-4 cursor-pointer" /></span>
                Propina (voluntaria)
              </span>
              <span class="font-medium">
                {{ moneda.format(aplicaPropina ? abierta.propina : 0) }}
              </span>
            </label>

            <div v-if="abierta.impuesto > 0" class="flex justify-between py-1">
              <span class="text-tinta/60">Impuesto</span>
              <span class="font-medium">{{ moneda.format(abierta.impuesto) }}</span>
            </div>

            <!-- Costo de envío del domicilio (SPEC-013/025): fijo, no cambia aquí -->
            <div v-if="abierta.envio > 0" class="flex justify-between py-1">
              <span class="text-tinta/60">Envío</span>
              <span class="font-medium">{{ moneda.format(abierta.envio) }}</span>
            </div>

            <div class="mt-2 flex items-baseline justify-between border-t border-marca/15 pt-3">
              <span class="text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">Total</span>
              <b class="text-[26px] font-medium text-marca">{{ moneda.format(totalCuenta) }}</b>
            </div>
          </div>

          <template v-if="!anulando">
            <h3 class="mt-6 mb-2.5 text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
              ¿Con qué pagó?
            </h3>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="m in mediosPago" :key="m.id"
                @click="medioElegido = m.id"
                class="min-h-12 cursor-pointer rounded-xl border-2 text-[14px] font-semibold transition-colors"
                :class="medioElegido === m.id
                  ? 'border-marca bg-marca text-lienzo'
                  : 'border-marca/20 text-marca'"
              >{{ m.nombre }}</button>
            </div>

            <!-- Vuelto (SPEC-025): solo en efectivo, opcional -->
            <div v-if="esEfectivo" class="mt-4">
              <h3 class="mb-2 text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
                ¿Con cuánto pagó? (opcional)
              </h3>
              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="billete in [10000, 20000, 50000, 100000]" :key="billete"
                  v-show="billete >= totalCuenta"
                  @click="recibido = String(billete)"
                  class="min-h-11 cursor-pointer rounded-full border border-marca/20 px-3.5 text-[13px] font-semibold text-marca hover:border-marca"
                >{{ moneda.format(billete) }}</button>
                <button
                  @click="recibido = String(totalCuenta)"
                  class="min-h-11 cursor-pointer rounded-full border border-marca/20 px-3.5 text-[13px] font-semibold text-marca hover:border-marca"
                >Exacto</button>
              </div>
              <input
                v-model="recibido" type="number" min="0" step="1000" inputmode="numeric"
                placeholder="Cuánto entregó el cliente"
                class="mt-2 min-h-12 w-full rounded-xl border border-marca/20 px-3.5 text-[15px] outline-none focus:border-marca"
              />
              <p
                v-if="vuelto !== null"
                class="mt-2 rounded-xl px-3.5 py-2.5 text-[14px] font-bold"
                :class="vuelto < 0 ? 'bg-alerta/10 text-alerta' : 'bg-emerald-50 text-emerald-800'"
              >{{ vuelto < 0 ? `Faltan ${moneda.format(-vuelto)}` : `Vuelto: ${moneda.format(vuelto)}` }}</p>
            </div>

            <!-- Qué significa cobrar (SPEC-013, revisado 2026-09-16) -->
            <template v-if="abierta.mesa_codigo">
              <p
                class="mt-5 rounded-xl px-3.5 py-3 text-[13px] leading-snug"
                :class="anticipado ? 'bg-amber-50 text-amber-900' : 'bg-marca-suave/60 text-tinta/75'"
              >
                <template v-if="!anticipado">
                  <strong>Cobra cuando el cliente esté pagando para irse.</strong>
                  Al cobrar, {{ abierta.destino }} queda libre y la cuenta se cierra: ya no se le puede agregar nada.
                </template>
                <template v-else>
                  <strong>Pago anticipado:</strong> el cliente paga y sigue en la mesa, que queda ocupada.
                  Si luego pide algo más, será un pedido nuevo con otra cuenta.
                </template>
              </p>
              <label class="mt-2 flex cursor-pointer items-center gap-2 text-[13px] font-semibold text-tinta/70">
                <span class="-m-2.5 grid min-h-11 min-w-11 place-items-center p-2.5"><input v-model="anticipado" type="checkbox" class="size-4 cursor-pointer" /></span>
                Pago anticipado (el cliente sigue en la mesa)
              </label>
            </template>

            <button
              @click="cobrar" :disabled="cobrando || (vuelto !== null && vuelto < 0)"
              class="mt-4 min-h-14 w-full cursor-pointer rounded-2xl bg-marca text-[15px] font-bold text-lienzo transition-transform active:scale-[0.98] disabled:opacity-50"
            >{{ cobrando ? "Cobrando…" : abierta.mesa_codigo && !anticipado ? `Cobrar y liberar ${abierta.destino}` : "Cobrar y cerrar cuenta" }}</button>

            <button
              @click="anulando = true"
              class="mt-2 min-h-12 w-full cursor-pointer text-[13px] font-semibold text-alerta"
            >Anular esta cuenta</button>
          </template>

          <!-- Anular exige motivo, siempre -->
          <template v-else>
            <h3 class="mt-6 mb-2 text-[11px] font-semibold tracking-[0.14em] text-alerta uppercase">
              Anular la cuenta
            </h3>
            <p class="mb-3 text-[13px] leading-snug text-tinta/60">
              Queda registrado con tu nombre y no se puede deshacer. El motivo es obligatorio.
            </p>
            <input
              v-model="motivo" type="text" maxlength="200"
              placeholder="¿Por qué se anula?"
              class="w-full rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[14px] outline-none focus:border-alerta"
            />
            <div class="mt-3 flex gap-2">
              <button
                @click="anulando = false"
                class="min-h-12 flex-1 cursor-pointer rounded-xl border border-marca/20 text-[14px] font-semibold text-marca"
              >Volver</button>
              <button
                @click="confirmarAnulacion"
                class="min-h-12 flex-1 cursor-pointer rounded-xl bg-alerta text-[14px] font-semibold text-white"
              >Anular</button>
            </div>
          </template>

          <button
            v-if="!anulando"
            @click="abierta = null"
            class="mt-1 min-h-12 w-full cursor-pointer text-[14px] font-semibold text-tinta/50"
          >Cerrar</button>
        </div>
      </div>
    </div>

  </MarcoInterno>
</template>
