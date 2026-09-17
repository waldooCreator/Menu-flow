<script setup>
/**
 * Activos líquidos (SPEC-020): cuánta plata hay ahora mismo y dónde.
 *
 * El saldo de cada caja ya se sabía calcular desde SPEC-014 — lo que no
 * existía era una pantalla que los mostrara juntos y sumados. Para saber
 * cuánto tenía el negocio había que abrir el Libro caja por caja.
 *
 * El desglose entre efectivo y banco no es decoración: son dos formas
 * distintas de cuadrar. El efectivo se cuenta con la mano al cerrar el turno;
 * una cuenta de banco se concilia contra el extracto.
 */
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  obtenerActivos, listarCategoriasGasto, registrarMovimiento,
  trasladarEntreCajas, fijarSaldoInicial, ajustarSaldo,
} from "../../api/caja";
import { useAuthStore } from "../../stores/auth";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const router = useRouter();
const auth = useAuthStore();

const datos = ref(null);
const categorias = ref([]);
const cargando = ref(true);
const error = ref(null);
const aviso = ref(null);

// Un solo panel abierto a la vez: "ingreso" | "gasto" | "traslado" | null,
// más los del administrador, que van por caja.
const panel = ref(null);
const guardando = ref(false);

const monto = ref(null);
const descripcion = ref("");
const cajaElegida = ref(null);
const categoriaElegida = ref(null);
const trasDestino = ref(null);

const cajaAdmin = ref(null);      // la caja sobre la que se fija o ajusta
const modoAdmin = ref(null);      // "arranque" | "ajuste"
const montoAdmin = ref(null);
const motivoAdmin = ref("");

const moneda = formatearMoneda;
const esAdmin = computed(() => auth.rol === "admin");

const cajas = computed(() => datos.value?.cajas ?? []);
const saldoDeLaCaja = computed(
  () => cajas.value.find((c) => c.id === cajaElegida.value)?.saldo ?? 0
);

/**
 * De una caja no puede salir mas de lo que tiene: un saldo negativo no
 * significa nada. El servidor lo impide igual — esto solo evita que la
 * persona escriba todo el formulario para que se lo rechacen al final.
 */
const sePasa = computed(() => {
  if (panel.value === "ingreso" || !monto.value) return false;
  return Number(monto.value) > saldoDeLaCaja.value;
});
// Cajas vacias, que todavia esperan que alguien diga con cuanto arrancaron.
const sinArranque = computed(
  () => cajas.value.filter((c) => c.puede_declarar_arranque)
);

function avisar(texto) {
  aviso.value = texto;
  setTimeout(() => (aviso.value = null), 4000);
}

async function cargar() {
  error.value = null;
  try {
    const [activos, cats] = await Promise.all([
      obtenerActivos(),
      // Si falla, se pueden seguir viendo los saldos: registrar un gasto es
      // lo único que se queda sin poder hacer.
      listarCategoriasGasto().catch(() => []),
    ]);
    datos.value = activos;
    categorias.value = cats;
    if (cajaElegida.value === null) cajaElegida.value = activos.cajas[0]?.id ?? null;
    // La categoria NO se preselecciona a proposito. Con la primera puesta por
    // defecto, quien solo escribe monto y descripcion manda el gasto a la
    // categoria que estuviera de primera — y entonces el reporte de en que se
    // va la plata dice cualquier cosa. Se probo aqui mismo: un gasto de pollo
    // quedo registrado como nomina.
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudieron cargar los activos.";
  } finally {
    cargando.value = false;
  }
}

function abrirPanel(cual) {
  panel.value = panel.value === cual ? null : cual;
  monto.value = null;
  descripcion.value = "";
  categoriaElegida.value = null;
  error.value = null;
  if (cual === "traslado") {
    trasDestino.value = cajas.value.find((c) => c.id !== cajaElegida.value)?.id ?? null;
  }
}

/** Devuelve true si guardó, para que cada acción solo cierre su panel. */
async function conGuardado(accion) {
  if (!monto.value || Number(monto.value) <= 0) {
    error.value = "Escribe un monto mayor que cero.";
    return false;
  }
  guardando.value = true;
  error.value = null;
  try {
    await accion();
    await cargar();
    panel.value = null;
    return true;
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo registrar.";
    return false;
  } finally {
    guardando.value = false;
  }
}

async function guardarIngreso() {
  const ok = await conGuardado(() => registrarMovimiento(
    cajaElegida.value, "ingreso", Number(monto.value), descripcion.value));
  if (ok) avisar("Ingreso registrado");
}

async function guardarGasto() {
  if (!categoriaElegida.value) {
    error.value = "Elige en qué categoría va este gasto.";
    return;
  }
  const ok = await conGuardado(() => registrarMovimiento(
    cajaElegida.value, "egreso", Number(monto.value), descripcion.value,
    categoriaElegida.value));
  if (ok) avisar("Gasto registrado");
}

async function guardarTraslado() {
  const ok = await conGuardado(() => trasladarEntreCajas(
    cajaElegida.value, trasDestino.value, Number(monto.value), descripcion.value));
  if (ok) avisar("Traslado registrado");
}

function abrirAdmin(caja, modo) {
  cajaAdmin.value = caja;
  modoAdmin.value = modo;
  montoAdmin.value = modo === "ajuste" ? caja.saldo : null;
  motivoAdmin.value = "";
  error.value = null;
}

async function guardarAdmin() {
  guardando.value = true;
  error.value = null;
  try {
    if (modoAdmin.value === "arranque") {
      await fijarSaldoInicial(cajaAdmin.value.id, Number(montoAdmin.value));
      avisar(`«${cajaAdmin.value.nombre}» arranca con ${moneda(Number(montoAdmin.value))}`);
    } else {
      const r = await ajustarSaldo(
        cajaAdmin.value.id, Number(montoAdmin.value), motivoAdmin.value);
      avisar(r.sin_cambios
        ? "El saldo ya estaba en ese número: no se registró nada"
        : `Ajuste de ${moneda(r.ajuste)} registrado en el libro`);
    }
    cajaAdmin.value = null;
    await cargar();
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo guardar.";
  } finally {
    guardando.value = false;
  }
}

/** El libro filtrado por esa caja: de ahí salió el número, y hay que poder verlo. */
function verLibro(caja) {
  router.push({ name: "mesero-libro", query: { caja: caja.id } });
}

function cuando(iso) {
  if (!iso) return "sin movimientos";
  const dias = Math.floor((Date.now() - new Date(iso)) / 86400000);
  if (dias === 0) return "hoy";
  if (dias === 1) return "ayer";
  return `hace ${dias} días`;
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Activos" ancho="max-w-4xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <p v-if="error && !panel && !cajaAdmin" class="mb-4 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
      {{ error }}
    </p>
    <p v-if="aviso" class="mb-4 rounded-xl bg-emerald-50 px-3.5 py-2.5 text-[13px] font-semibold text-emerald-700">
      {{ aviso }}
    </p>

    <p v-if="cargando" class="py-16 text-center text-tinta/50">Cargando…</p>

    <template v-else-if="datos">
      <!-- ===== El total ===== -->
      <section class="rounded-2xl border border-marca/12 bg-white p-4 sm:p-6">
        <p class="text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">
          Hay en total
        </p>
        <p class="mt-1.5 font-display text-[32px] leading-none font-light break-words text-marca sm:text-[42px]">
          {{ moneda(datos.total) }}
        </p>
        <div class="mt-4 grid grid-cols-2 gap-2.5">
          <div class="rounded-xl bg-marca/5 px-3.5 py-2.5">
            <p class="text-[10.5px] font-semibold tracking-[0.10em] text-marca/55 uppercase">En efectivo</p>
            <p class="mt-0.5 text-[16px] font-semibold tabular-nums break-words text-tinta sm:text-[18px]">
              {{ moneda(datos.total_efectivo) }}
            </p>
            <p class="mt-0.5 text-[11px] text-tinta/45">se cuenta a mano</p>
          </div>
          <div class="rounded-xl bg-marca/5 px-3.5 py-2.5">
            <p class="text-[10.5px] font-semibold tracking-[0.10em] text-marca/55 uppercase">En bancos</p>
            <p class="mt-0.5 text-[16px] font-semibold tabular-nums break-words text-tinta sm:text-[18px]">
              {{ moneda(datos.total_banco) }}
            </p>
            <p class="mt-0.5 text-[11px] text-tinta/45">se concilia con el extracto</p>
          </div>
        </div>
      </section>

      <!-- Aviso de arranque: solo mientras haya cajas sin estrenar -->
      <p
        v-if="esAdmin && sinArranque.length"
        class="mt-3 rounded-xl bg-amber-50 px-3.5 py-2.5 text-[12.5px] leading-snug text-amber-900"
      >
        {{ sinArranque.length === 1 ? "Una caja no tiene" : `${sinArranque.length} cajas no tienen` }}
        registrado con cuánto arrancaron. Hasta que lo hagas, el total de arriba está incompleto.
      </p>

      <!-- ===== Cada caja ===== -->
      <ul class="mt-3 grid gap-2.5 sm:grid-cols-2">
        <li
          v-for="c in cajas" :key="c.id"
          class="rounded-2xl border border-marca/12 bg-white p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="truncate text-[14px] font-semibold text-tinta">{{ c.nombre }}</p>
              <p class="text-[11.5px] text-tinta/45">
                {{ c.tipo === "efectivo" ? "Efectivo" : "Banco o billetera" }}
                · {{ cuando(c.ultimo_movimiento) }}
              </p>
            </div>
            <p class="shrink-0 font-display text-[20px] leading-none font-light tabular-nums text-marca">
              {{ moneda(c.saldo) }}
            </p>
          </div>
          <div class="mt-3 flex flex-wrap gap-1.5">
            <button
              @click="verLibro(c)"
              class="min-h-11 cursor-pointer rounded-full border border-marca/20 px-3.5 text-[12px] font-semibold text-marca hover:border-marca"
            >Ver movimientos</button>
            <button
              v-if="esAdmin && c.puede_declarar_arranque"
              @click="abrirAdmin(c, 'arranque')"
              class="min-h-11 cursor-pointer rounded-full border border-amber-300 px-3.5 text-[12px] font-semibold text-amber-800 hover:border-amber-500"
            >Con cuánto arrancó</button>
            <button
              v-if="esAdmin"
              @click="abrirAdmin(c, 'ajuste')"
              class="min-h-11 cursor-pointer rounded-full border border-marca/20 px-3.5 text-[12px] font-semibold text-marca hover:border-marca"
            >Ajustar</button>
          </div>
        </li>
      </ul>

      <!-- ===== Las acciones del día a día ===== -->
      <div class="mt-3 flex flex-wrap gap-2">
        <button
          v-for="b in [
            { v: 'ingreso', t: 'Registrar ingreso' },
            { v: 'gasto', t: 'Registrar gasto' },
            { v: 'traslado', t: 'Trasladar' },
          ]"
          :key="b.v" @click="abrirPanel(b.v)"
          class="min-h-11 flex-1 cursor-pointer rounded-2xl border px-4 text-[13px] font-semibold whitespace-nowrap transition-colors"
          :class="panel === b.v
            ? 'border-marca bg-marca text-lienzo'
            : 'border-marca/20 bg-white text-marca hover:border-marca'"
        >{{ b.t }}</button>
      </div>

      <div v-if="panel" class="mt-2.5 rounded-2xl border border-marca/15 bg-white p-4">
        <p v-if="error" class="mb-3 rounded-xl bg-alerta/10 px-3 py-2 text-[12.5px] font-semibold text-alerta">
          {{ error }}
        </p>

        <div class="grid gap-3 sm:grid-cols-2">
          <div>
            <label for="a-caja" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">
              {{ panel === "traslado" ? "Sale de" : "Caja" }}
            </label>
            <select
              id="a-caja" v-model="cajaElegida"
              class="min-h-11 w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[14px]"
            >
              <option v-for="c in cajas" :key="c.id" :value="c.id">
                {{ c.nombre }} · {{ moneda(c.saldo) }}
              </option>
            </select>
          </div>

          <div v-if="panel === 'traslado'">
            <label for="a-destino" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Entra a</label>
            <select
              id="a-destino" v-model="trasDestino"
              class="min-h-11 w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[14px]"
            >
              <option v-for="c in cajas.filter((x) => x.id !== cajaElegida)" :key="c.id" :value="c.id">
                {{ c.nombre }} · {{ moneda(c.saldo) }}
              </option>
            </select>
          </div>

          <div v-if="panel === 'gasto'">
            <label for="a-cat" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Categoría</label>
            <select
              id="a-cat" v-model="categoriaElegida"
              class="min-h-11 w-full cursor-pointer rounded-xl border bg-white px-3 text-[14px]"
              :class="categoriaElegida ? 'border-marca/20' : 'border-amber-400'"
            >
              <option :value="null">Elige una…</option>
              <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
          </div>

          <div>
            <label for="a-monto" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Monto</label>
            <input
              id="a-monto" v-model="monto" type="number" min="1" inputmode="numeric"
              placeholder="0"
              class="min-h-11 w-full rounded-xl border px-3.5 text-[14px] outline-none"
              :class="sePasa ? 'border-alerta focus:border-alerta' : 'border-marca/20 focus:border-marca'"
            />
            <p v-if="sePasa" class="mt-1.5 text-[12px] leading-snug font-semibold text-alerta">
              Esa caja solo tiene {{ moneda(saldoDeLaCaja) }}.
            </p>
          </div>

          <div class="sm:col-span-2">
            <label for="a-desc" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">
              {{ panel === "gasto" ? "En qué exactamente" : "Descripción" }}
            </label>
            <input
              id="a-desc" v-model="descripcion" type="text" maxlength="200"
              :placeholder="panel === 'gasto' ? 'Pollo del jueves, recibo de la luz…' : 'Para qué es'"
              class="min-h-11 w-full rounded-xl border border-marca/20 px-3.5 text-[14px] outline-none placeholder:text-tinta/35 focus:border-marca"
            />
            <p v-if="panel === 'gasto'" class="mt-1.5 text-[11.5px] leading-snug text-tinta/50">
              La categoría dice de qué tipo es; esto dice cuál fue.
            </p>
          </div>
        </div>

        <button
          @click="panel === 'ingreso' ? guardarIngreso() : panel === 'gasto' ? guardarGasto() : guardarTraslado()"
          :disabled="guardando || sePasa"
          class="mt-4 min-h-12 w-full cursor-pointer rounded-2xl bg-marca text-[14px] font-bold text-lienzo disabled:cursor-not-allowed disabled:opacity-50"
        >{{ guardando ? "Guardando…" : "Registrar" }}</button>
      </div>
    </template>

    <!-- ===== Arranque / ajuste (solo administrador) ===== -->
    <div
      v-if="cajaAdmin"
      class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/45 backdrop-blur-sm sm:items-center sm:p-4"
      @click.self="cajaAdmin = null"
    >
      <div class="max-h-[90dvh] w-full overflow-y-auto rounded-t-3xl bg-white p-5 sm:max-w-md sm:rounded-3xl sm:p-6">
        <h3 class="font-display text-[22px] leading-tight font-light text-marca">
          {{ modoAdmin === "arranque" ? `¿Con cuánto arrancó ${cajaAdmin.nombre}?` : `Ajustar ${cajaAdmin.nombre}` }}
        </h3>
        <p class="mt-2 text-[13px] leading-snug text-tinta/60">
          <template v-if="modoAdmin === 'arranque'">
            La plata que ya tenía el día que empezaron a usar el sistema. Se
            registra <strong class="text-tinta">una sola vez</strong>: después se
            corrige con un ajuste.
          </template>
          <template v-else>
            Hoy el sistema dice <strong class="text-tinta">{{ moneda(cajaAdmin.saldo) }}</strong>.
            Escribe lo que hay de verdad. No se borra nada: la diferencia queda
            en el libro con tu nombre y tu motivo.
          </template>
        </p>

        <p v-if="error" class="mt-3 rounded-xl bg-alerta/10 px-3 py-2 text-[12.5px] font-semibold text-alerta">
          {{ error }}
        </p>

        <label for="ad-monto" class="mt-4 mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">
          {{ modoAdmin === "arranque" ? "Saldo de arranque" : "Saldo real" }}
        </label>
        <input
          id="ad-monto" v-model="montoAdmin" type="number" min="0" inputmode="numeric"
          class="min-h-12 w-full rounded-xl border border-marca/20 px-3.5 text-[15px] outline-none focus:border-marca"
        />

        <template v-if="modoAdmin === 'ajuste'">
          <label for="ad-motivo" class="mt-3.5 mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">
            Por qué
          </label>
          <input
            id="ad-motivo" v-model="motivoAdmin" type="text" maxlength="200"
            placeholder="Comisión del banco, consignación no registrada…"
            class="min-h-11 w-full rounded-xl border border-marca/20 px-3.5 text-[14px] outline-none placeholder:text-tinta/35 focus:border-marca"
          />
        </template>

        <div class="mt-5 flex gap-2.5">
          <button
            @click="cajaAdmin = null"
            class="min-h-12 flex-1 cursor-pointer rounded-2xl border border-marca/20 text-[14px] font-semibold text-marca"
          >Cancelar</button>
          <button
            @click="guardarAdmin" :disabled="guardando"
            class="min-h-12 flex-1 cursor-pointer rounded-2xl bg-marca text-[14px] font-bold text-lienzo disabled:opacity-50"
          >{{ guardando ? "Guardando…" : "Guardar" }}</button>
        </div>
      </div>
    </div>
  </MarcoInterno>
</template>
