<script setup>
/**
 * Turno de caja (SPEC-014): caja abre y cierra los turnos DE LOS MESEROS —
 * no solo el propio de quien está frente a la pantalla (revisado
 * 2026-09-03). Por eso abrir un turno siempre pide elegir a quién es, y esta
 * pantalla muestra tanto el turno del que la usa (si tiene uno) como los
 * demás que sigan abiertos.
 *
 * La pantalla existe para responder una sola pregunta al final del día:
 * **¿cuánto debería haber en el cajón, y cuánto hay?** La diferencia se
 * muestra tal cual salga — no se maquilla para que dé cero.
 *
 * Cobrar nunca depende de esto: si no hay turno abierto se cobra igual, y la
 * venta queda marcada "fuera de turno".
 */
import { computed, onMounted, ref } from "vue";
import { turnoActual, abrirTurno, cerrarTurno, listarMovimientos, registrarMovimiento } from "../../api/caja";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const turno = ref(null);              // el propio, si quien mira tiene uno
const otrosTurnosAbiertos = ref([]);  // los de los demás — SPEC-014, 2026-09-03
const cajas = ref([]);
const usuarios = ref([]);             // a quién se le puede abrir un turno
const movimientos = ref([]);
const cargando = ref(true);
const error = ref(null);

// {caja_id: monto} — un fondo por caja (SPEC-014). Antes era un solo numero
// que iba siempre a efectivo; si el datafono arranca el dia con el saldo de
// ayer, ignorarlo hace que el cuadre nazca torcido.
const fondos = ref({});
const usuarioElegido = ref(null); // obligatorio: caja abre A NOMBRE de alguien
const obsApertura = ref("");
const abriendo = ref(false);

// Turnos que quedaron abiertos de dias anteriores. Se avisa, no se bloquea.
const turnosViejos = ref([]);
const turnosViejosIds = computed(() => new Set(turnosViejos.value.map((t) => t.id)));

// Cerrar el de OTRA persona (de la lista, o desde el aviso de viejos):
// exige motivo, lo valida el servidor.
const cerrandoAjeno = ref(null);
const efectivoAjeno = ref(null);
const motivoAjeno = ref("");

const efectivoContado = ref(null);
const obsCierre = ref("");
const cerrando = ref(false);

// Cerrar el cajón del día (SPEC-020): la plata sale y queda solo la base.
// Va aparte de cerrar el turno porque no siempre coinciden — si todavía hay
// compañeros vendiendo, vaciar el cajón les dejaría el turno descuadrado.
const cerrarCajon = ref(false);
const baseDejada = ref(0);
const destinoEfectivo = ref("");     // "" = se guarda; un id = se consigna ahí
const motivoDiferencia = ref("");

const cajasBanco = computed(() => cajas.value.filter((c) => c.tipo === "banco"));

const movCaja = ref(null);
const movTipo = ref("egreso");
const movMonto = ref(null);
const movDescripcion = ref("");
const panelMovimiento = ref(false);

const moneda = { format: formatearMoneda };

const hayTurno = computed(() => !!turno.value);
const totalFondos = computed(() =>
  Object.values(fondos.value).reduce((t, v) => t + (Number(v) || 0), 0)
);
const cuadre = computed(() => turno.value?.cuadre ?? null);

/**
 * Lo que resultaría si se cerrara con lo que hay escrito ahora mismo.
 *
 * Se compara contra dos números distintos según lo que se esté haciendo
 * (SPEC-020):
 *
 * - Cerrando solo el turno: contra lo que movió ESTE turno. Responde "de la
 *   plata que pasó por mis manos, ¿cuadra?".
 * - Cerrando también el cajón: contra lo que el libro dice que hay en el
 *   cajón, base de ayer incluida. Es contra eso que el servidor registra la
 *   diferencia de arqueo, así que mostrar el otro número haría que la
 *   pantalla dijera una cosa y el libro guardara otra.
 */
const diferenciaPrevia = computed(() => {
  if (efectivoContado.value === null || efectivoContado.value === "") return null;
  const esperado = cerrarCajon.value
    ? (cuadre.value?.esperado_en_cajon ?? 0)
    : (cuadre.value?.esperado_efectivo ?? 0);
  return Number(efectivoContado.value) - esperado;
});

const fueraDeTurno = computed(() =>
  movimientos.value.filter((m) => m.fuera_de_turno && m.concepto === "venta")
);

async function cargar() {
  try {
    const r = await turnoActual();
    turno.value = r.abierto ? r.turno : null;
    otrosTurnosAbiertos.value = r.otros_turnos_abiertos ?? [];
    cajas.value = r.cajas ?? [];
    usuarios.value = r.usuarios ?? [];
    turnosViejos.value = r.turnos_viejos ?? [];
    // El libro cambio de forma: ahora trae { totales, movimientos }.
    movimientos.value = (await listarMovimientos()).movimientos ?? [];
    movCaja.value = cajas.value[0]?.id ?? null;
    if (usuarioElegido.value === null) usuarioElegido.value = usuarios.value[0]?.id ?? null;
  } finally {
    cargando.value = false;
  }
}

async function abrir() {
  if (!usuarioElegido.value) {
    error.value = "Elige a quién se le abre el turno.";
    return;
  }
  error.value = null;
  abriendo.value = true;
  try {
    await abrirTurno(usuarioElegido.value, fondos.value, obsApertura.value);
    fondos.value = {};
    obsApertura.value = "";
    await cargar();
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo abrir el turno.";
  } finally {
    abriendo.value = false;
  }
}

async function cerrar() {
  error.value = null;
  cerrando.value = true;
  try {
    const cerrado = await cerrarTurno(
      turno.value.id, Number(efectivoContado.value), obsCierre.value,
      cerrarCajon.value
        ? {
            base: Number(baseDejada.value) || 0,
            destino: destinoEfectivo.value || null,
            motivo: motivoDiferencia.value,
          }
        : null,
    );
    turno.value = null;
    efectivoContado.value = null;
    obsCierre.value = "";
    cerrarCajon.value = false;
    baseDejada.value = 0;
    destinoEfectivo.value = "";
    motivoDiferencia.value = "";
    await cargar();
    resumenCierre.value = cerrado;
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo cerrar el turno.";
  } finally {
    cerrando.value = false;
  }
}

const resumenCierre = ref(null);

async function guardarMovimiento() {
  error.value = null;
  try {
    await registrarMovimiento(movCaja.value, movTipo.value, Number(movMonto.value), movDescripcion.value);
    movMonto.value = null;
    movDescripcion.value = "";
    panelMovimiento.value = false;
    await cargar();
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo registrar el movimiento.";
  }
}

/**
 * Cerrar el turno de otra persona: desde la lista de "otros turnos
 * abiertos" o desde el aviso de turnos viejos — el mismo formulario para
 * los dos casos. Cualquiera que pueda cobrar puede hacerlo (SPEC-014,
 * revisado 2026-09-03: caja abre Y cierra los turnos de los meseros, no
 * solo un administrador rescatando un olvido). El motivo obligatorio es lo
 * que deja el rastro, no restringir quién puede.
 */
async function cerrarAjeno() {
  error.value = null;
  try {
    await cerrarTurno(cerrandoAjeno.value.id, Number(efectivoAjeno.value) || 0, motivoAjeno.value);
    cerrandoAjeno.value = null;
    efectivoAjeno.value = null;
    motivoAjeno.value = "";
    await cargar();
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo cerrar ese turno.";
  }
}

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString("es-CO",
    { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Caja" ancho="max-w-3xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <p v-if="cargando" class="py-14 text-center text-tinta/50">Cargando…</p>

    <template v-else>
      <p v-if="error" class="mb-4 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
        {{ error }}
      </p>

      <!-- ===== Turnos que alguien dejo abiertos de dias anteriores ===== -->
      <div
        v-if="turnosViejos.length"
        class="mb-4 rounded-2xl border border-amber-300 bg-amber-50 p-4"
      >
        <p class="text-[13px] font-bold text-amber-900">
          {{ turnosViejos.length === 1 ? "Hay un turno" : `Hay ${turnosViejos.length} turnos` }}
          sin cerrar de días anteriores
        </p>
        <p class="mt-1 text-[12.5px] leading-snug text-amber-800/80">
          Mientras siga abierto, esa persona no puede abrir el suyo de hoy.
        </p>
        <ul class="mt-3 space-y-1.5">
          <li
            v-for="t in turnosViejos" :key="t.id"
            class="flex flex-wrap items-center justify-between gap-2 text-[13px] text-amber-900"
          >
            <span>Turno de <strong>{{ t.responsable }}</strong> · desde {{ fechaCorta(t.abierto_en) }}</span>
            <button
              @click="cerrandoAjeno = t"
              class="min-h-11 cursor-pointer rounded-full border border-amber-400 px-3.5 text-[12px] font-bold text-amber-900 hover:bg-amber-100"
            >Cerrarlo</button>
          </li>
        </ul>
      </div>

      <!-- ===== Tu turno ===== -->
      <div v-if="hayTurno" class="rounded-3xl border border-marca/12 bg-white p-6">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-[11px] font-semibold tracking-[0.14em] text-marca/60 uppercase">
              Turno de {{ turno.responsable }} #{{ turno.id }}
            </p>
            <h2 class="mt-1 font-display text-[26px] leading-none font-light text-marca">
              Debería haber
            </h2>
          </div>
          <span class="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3.5 py-1.5 text-[12px] font-bold text-emerald-700">
            <span class="size-2.5 rounded-full bg-emerald-500"></span> Abierto
          </span>
        </div>

        <p class="mt-3 font-display text-[36px] leading-none font-light text-marca">
          {{ moneda.format(cuadre.esperado_efectivo) }}
        </p>
        <p class="mt-1 text-[12px] text-tinta/45">
          en efectivo, de lo que movió este turno
        </p>
        <!-- El cajón puede tener más: la base que quedó de ayer, y lo de los
             compañeros que siguen vendiendo. Se dice cuando de verdad son
             números distintos, para no llenar la pantalla el resto del tiempo. -->
        <p
          v-if="cuadre.esperado_en_cajon !== cuadre.esperado_efectivo"
          class="mt-2 rounded-xl bg-marca/5 px-3 py-2 text-[12.5px] leading-snug text-tinta/65"
        >
          En el cajón debería haber
          <strong class="text-tinta">{{ moneda.format(cuadre.esperado_en_cajon) }}</strong>
          en total, contando lo que ya estaba antes de este turno.
        </p>

        <!-- Lo que entró por cada caja: el efectivo se cuenta, lo demás se
             compara contra el banco -->
        <ul v-if="cuadre.por_caja.length" class="mt-5 border-t border-marca/12 pt-4">
          <li v-for="c in cuadre.por_caja" :key="c.caja" class="flex justify-between gap-3 py-1.5 text-[15px]">
            <span class="text-tinta/60">{{ c.caja }}</span>
            <span class="font-medium">{{ moneda.format(c.neto) }}</span>
          </li>
        </ul>
      </div>

      <!-- Ingresos y gastos -->
      <template v-if="hayTurno">
        <button
          @click="panelMovimiento = !panelMovimiento"
          class="mt-3 min-h-13 w-full cursor-pointer rounded-2xl border-2 border-marca text-[14px] font-bold text-marca"
        >Registrar ingreso o gasto</button>

        <div v-if="panelMovimiento" class="mt-2.5 rounded-2xl border border-marca/15 bg-white p-4">
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="t in [{v:'ingreso',n:'Entra plata'},{v:'egreso',n:'Sale plata'}]" :key="t.v"
              @click="movTipo = t.v"
              class="min-h-12 cursor-pointer rounded-xl border-2 text-[14px] font-semibold"
              :class="movTipo === t.v ? 'border-marca bg-marca text-lienzo' : 'border-marca/20 text-marca'"
            >{{ t.n }}</button>
          </div>

          <select
            v-model="movCaja"
            class="mt-2.5 min-h-12 w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[14px]"
          >
            <option v-for="c in cajas" :key="c.id" :value="c.id">{{ c.nombre }}</option>
          </select>

          <input
            v-model="movMonto" type="number" min="1" inputmode="numeric" placeholder="Monto"
            class="mt-2.5 w-full rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[15px] outline-none focus:border-marca"
          />
          <input
            v-model="movDescripcion" type="text" maxlength="200" placeholder="¿De qué se trata?"
            class="mt-2.5 w-full rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[15px] outline-none focus:border-marca"
          />
          <button
            @click="guardarMovimiento"
            class="mt-3 min-h-12 w-full cursor-pointer rounded-xl bg-marca text-[14px] font-bold text-lienzo"
          >Registrar</button>
        </div>

        <!-- Cerrar el propio -->
        <div class="mt-6 rounded-3xl border border-marca/12 bg-white p-6">
          <h3 class="font-display text-[22px] leading-none font-light text-marca">Cerrar turno</h3>
          <p class="mt-2 text-[14px] leading-snug text-tinta/60">
            Cuenta el efectivo del cajón y escribe cuánto hay. La diferencia se guarda como salga.
          </p>

          <label for="contado" class="mt-5 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
            Efectivo contado
          </label>
          <input
            id="contado" v-model="efectivoContado" type="number" min="0" inputmode="numeric"
            class="w-full rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[15px] outline-none focus:border-marca"
          />

          <!-- La diferencia, antes de cerrar -->
          <p
            v-if="diferenciaPrevia !== null"
            class="mt-3 rounded-xl px-3.5 py-2.5 text-[14px] font-semibold"
            :class="diferenciaPrevia === 0 ? 'bg-emerald-50 text-emerald-700'
              : diferenciaPrevia > 0 ? 'bg-amber-50 text-amber-800' : 'bg-alerta/10 text-alerta'"
          >
            {{ diferenciaPrevia === 0 ? "Cuadra exacto"
              : diferenciaPrevia > 0 ? `Sobran ${moneda.format(diferenciaPrevia)}`
              : `Faltan ${moneda.format(Math.abs(diferenciaPrevia))}` }}
          </p>

          <!-- ===== Cerrar el cajón del día (SPEC-020) ===== -->
          <label
            class="mt-4 flex cursor-pointer items-start gap-2.5 rounded-2xl border p-3.5 transition-colors"
            :class="cerrarCajon ? 'border-marca bg-marca/5' : 'border-marca/15'"
          >
            <input v-model="cerrarCajon" type="checkbox" class="mt-0.5 size-4.5 shrink-0 cursor-pointer accent-[var(--color-marca)]" />
            <span class="min-w-0">
              <span class="block text-[14px] font-semibold text-tinta">
                También cierro el cajón del día
              </span>
              <span class="mt-0.5 block text-[12.5px] leading-snug text-tinta/55">
                Saca la plata del cajón y deja solo la base para mañana.
                <template v-if="otrosTurnosAbiertos.length">
                  <strong class="text-amber-800">
                    Ojo: quedan {{ otrosTurnosAbiertos.length }} turnos abiertos.
                  </strong>
                  Si vacías el cajón ahora, a esa gente no le va a cuadrar.
                </template>
              </span>
            </span>
          </label>

          <div v-if="cerrarCajon" class="mt-2.5 rounded-2xl border border-marca/15 bg-white p-4">
            <label for="base" class="mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
              Cuánto dejas de base
            </label>
            <input
              id="base" v-model="baseDejada" type="number" min="0" inputmode="numeric"
              class="w-full rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[15px] outline-none focus:border-marca"
            />

            <label for="destino" class="mt-3.5 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
              El resto
            </label>
            <select
              id="destino" v-model="destinoEfectivo"
              class="w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[15px]"
            >
              <option value="">Se guarda (caja fuerte, o se lo llevan)</option>
              <option v-for="c in cajasBanco" :key="c.id" :value="c.id">
                Se consigna en {{ c.nombre }}
              </option>
            </select>

            <p v-if="efectivoContado !== null" class="mt-2.5 text-[12.5px] text-tinta/55">
              Sale del cajón:
              <strong class="text-tinta">
                {{ moneda.format(Math.max(0, Number(efectivoContado) - Number(baseDejada || 0))) }}
              </strong>
            </p>

            <!-- El motivo solo aparece cuando de verdad hace falta: pedirlo
                 siempre entrena a escribir cualquier cosa para pasar. -->
            <template v-if="diferenciaPrevia !== null && diferenciaPrevia !== 0">
              <label for="mot-dif" class="mt-3.5 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-alerta uppercase">
                Qué pasó con la diferencia
              </label>
              <input
                id="mot-dif" v-model="motivoDiferencia" type="text" maxlength="200"
                placeholder="Se pagó un domicilio y no se anotó, se dio mal un cambio…"
                class="w-full rounded-xl border border-alerta/40 bg-white px-3.5 py-3 text-[15px] outline-none placeholder:text-tinta/35 focus:border-alerta"
              />
              <p class="mt-1.5 text-[11.5px] leading-snug text-tinta/50">
                No se borra ni se disimula: queda en el libro con tu nombre.
              </p>
            </template>
          </div>

          <label for="obs-ci" class="mt-4 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
            Observación (opcional)
          </label>
          <input
            id="obs-ci" v-model="obsCierre" type="text" maxlength="200"
            class="w-full rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[15px] outline-none focus:border-marca"
          />

          <button
            @click="cerrar" :disabled="cerrando"
            class="mt-5 min-h-14 w-full cursor-pointer rounded-2xl bg-marca text-[15px] font-bold text-lienzo transition-transform active:scale-[0.98] disabled:opacity-50"
          >{{ cerrando ? "Cerrando…" : "Cerrar turno" }}</button>
        </div>
      </template>

      <!-- ===== Otros turnos abiertos: caja ve el de todos los meseros,
           no solo el propio (SPEC-014, 2026-09-03) ===== -->
      <div :class="hayTurno ? 'mt-6' : ''">
        <h3 class="mb-2.5 text-[11px] font-semibold tracking-[0.14em] text-marca/60 uppercase">
          {{ otrosTurnosAbiertos.length ? "Otros turnos abiertos" : "No hay más turnos abiertos" }}
        </h3>
        <ul v-if="otrosTurnosAbiertos.length" class="space-y-2">
          <li
            v-for="t in otrosTurnosAbiertos" :key="t.id"
            class="flex items-center justify-between gap-3 rounded-2xl border border-marca/12 bg-white px-4 py-3.5"
            :class="{ 'border-amber-300': turnosViejosIds.has(t.id) }"
          >
            <div class="min-w-0">
              <p class="truncate text-[14px] font-semibold text-marca">
                Turno de {{ t.responsable }} #{{ t.id }}
              </p>
              <p class="text-[12px] text-tinta/50">
                {{ moneda.format(t.cuadre.esperado_efectivo) }} en efectivo, según el libro
              </p>
            </div>
            <button
              @click="cerrandoAjeno = t"
              class="min-h-11 shrink-0 cursor-pointer rounded-full border border-marca/20 px-4 text-[12.5px] font-semibold text-marca hover:border-marca"
            >Cerrar</button>
          </li>
        </ul>
      </div>

      <!-- ===== Abrir turno: siempre disponible — caja abre el de CUALQUIER
           mesero, no solo cuando quien mira no tiene el suyo ===== -->
      <div class="mt-6 rounded-3xl border border-marca/12 bg-white p-6">
        <h2 class="font-display text-[22px] leading-none font-light text-marca">Abrir turno</h2>
        <p class="mt-2 text-[14px] leading-snug text-tinta/60">
          Elige a quién se le abre y con cuánto arranca cada caja. Si no tiene turno abierto
          igual puede cobrar: esas ventas quedarán marcadas como fuera de turno.
        </p>

        <label for="usuario-turno" class="mt-5 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
          ¿Para quién?
        </label>
        <select
          id="usuario-turno" v-model="usuarioElegido"
          class="w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[15px] outline-none focus:border-marca"
        >
          <option v-if="!usuarios.length" :value="null" disabled>No hay meseros ni cajeros creados</option>
          <option v-for="u in usuarios" :key="u.id" :value="u.id">{{ u.username }}</option>
        </select>

        <p class="mt-5 mb-2 text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
          Fondo inicial por caja
        </p>
        <p class="mb-3 text-[12.5px] leading-snug text-tinta/50">
          Deja en blanco las que arranquen en cero.
        </p>
        <ul class="space-y-2">
          <li v-for="c in cajas" :key="c.id" class="flex items-center gap-3">
            <label :for="`fondo-${c.id}`" class="min-w-0 flex-1 text-[14px] leading-snug text-tinta/75">
              {{ c.nombre }}
            </label>
            <input
              :id="`fondo-${c.id}`" v-model="fondos[c.id]"
              type="number" min="0" inputmode="numeric" placeholder="0"
              class="w-28 rounded-xl border border-marca/20 bg-white px-3.5 py-2.5 text-right text-[15px] tabular-nums outline-none focus:border-marca sm:w-36"
            />
          </li>
        </ul>
        <p v-if="totalFondos > 0" class="mt-3 text-right text-[13px] font-semibold text-marca">
          Total: {{ moneda.format(totalFondos) }}
        </p>

        <label for="obs-ap" class="mt-4 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
          Observación (opcional)
        </label>
        <input
          id="obs-ap" v-model="obsApertura" type="text" maxlength="200"
          class="w-full rounded-xl border border-marca/20 bg-white px-3.5 py-3 text-[15px] outline-none focus:border-marca"
        />

        <button
          @click="abrir" :disabled="abriendo || !usuarios.length"
          class="mt-5 min-h-14 w-full cursor-pointer rounded-2xl bg-marca text-[15px] font-bold text-lienzo transition-transform active:scale-[0.98] disabled:opacity-50"
        >{{ abriendo ? "Abriendo…" : "Abrir turno" }}</button>
      </div>

      <!-- Ventas cobradas sin turno: se ven, no se pierden -->
      <div v-if="fueraDeTurno.length" class="mt-6 rounded-2xl border-2 border-amber-300 bg-amber-50 p-4">
        <p class="text-[13px] font-bold text-amber-900">
          {{ fueraDeTurno.length }}
          {{ fueraDeTurno.length === 1 ? "venta cobrada fuera de turno" : "ventas cobradas fuera de turno" }}
        </p>
        <p class="mt-1 text-[12.5px] leading-snug text-amber-800/80">
          Se cobraron sin turno abierto. Están registradas, pero no entran en ningún cuadre.
        </p>
      </div>

      <!-- Resumen tras cerrar -->
      <div v-if="resumenCierre" class="mt-6 rounded-3xl border border-marca/12 bg-white p-6">
        <h3 class="font-display text-[22px] leading-none font-light text-marca">
          Turno #{{ resumenCierre.id }} cerrado
        </h3>
        <ul class="mt-4 text-[15px]">
          <li class="flex justify-between py-1">
            <span class="text-tinta/60">Esperado</span>
            <span class="font-medium">{{ moneda.format(resumenCierre.cuadre.esperado_efectivo) }}</span>
          </li>
          <li class="flex justify-between py-1">
            <span class="text-tinta/60">Contado</span>
            <span class="font-medium">{{ moneda.format(resumenCierre.cuadre.efectivo_contado) }}</span>
          </li>
          <li class="mt-1 flex justify-between border-t border-marca/12 pt-2">
            <span class="text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">Diferencia</span>
            <b :class="resumenCierre.cuadre.diferencia === 0 ? 'text-emerald-700'
              : resumenCierre.cuadre.diferencia > 0 ? 'text-amber-800' : 'text-alerta'">
              {{ moneda.format(resumenCierre.cuadre.diferencia) }}
            </b>
          </li>
        </ul>
      </div>

      <!-- ===== Cerrar el turno de otra persona ===== -->
      <div
        v-if="cerrandoAjeno"
        class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/45 p-0 backdrop-blur-sm sm:items-center sm:p-4"
        @click.self="cerrandoAjeno = null"
      >
        <div class="w-full rounded-t-3xl bg-white p-6 sm:max-w-md sm:rounded-3xl">
          <h3 class="font-display text-[24px] leading-none font-light text-marca">
            Cerrar turno de {{ cerrandoAjeno.responsable }}
          </h3>
          <p class="mt-2 text-[13.5px] leading-snug text-tinta/60">
            Turno #{{ cerrandoAjeno.id }}, abierto desde {{ fechaCorta(cerrandoAjeno.abierto_en) }}.
            Queda registrado que lo cerraste tú.
          </p>

          <label for="ef-ajeno" class="mt-5 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
            Efectivo contado
          </label>
          <input
            id="ef-ajeno" v-model="efectivoAjeno" type="number" min="0" inputmode="numeric"
            class="w-full rounded-xl border border-marca/20 px-3.5 py-3 text-[15px] outline-none focus:border-marca"
          />

          <label for="mot-ajeno" class="mt-4 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
            Motivo
          </label>
          <input
            id="mot-ajeno" v-model="motivoAjeno" type="text" maxlength="200"
            placeholder="quedó abierto desde el lunes"
            class="w-full rounded-xl border border-marca/20 px-3.5 py-3 text-[15px] outline-none focus:border-marca"
          />
          <p class="mt-1.5 text-[12px] text-tinta/45">
            Obligatorio: dentro de un mes nadie sabría por qué lo cerró alguien más.
          </p>

          <div class="mt-5 flex gap-2.5">
            <button
              @click="cerrandoAjeno = null"
              class="min-h-13 flex-1 cursor-pointer rounded-2xl border border-marca/20 text-[14px] font-semibold text-marca"
            >Cancelar</button>
            <button
              @click="cerrarAjeno"
              class="min-h-13 flex-1 cursor-pointer rounded-2xl bg-marca text-[14px] font-bold text-lienzo"
            >Cerrar turno</button>
          </div>
        </div>
      </div>
    </template>
  </MarcoInterno>
</template>
