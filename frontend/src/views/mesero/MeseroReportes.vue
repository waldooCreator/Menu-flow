<script setup>
/**
 * Reportes de venta (SPEC-018): las preguntas que un dueño se hace al cerrar
 * la semana, en una sola pantalla con un solo rango de fechas.
 *
 * Los de venta llegan en **una sola llamada**: varios viajes para pintar la
 * misma pantalla serían trabajo desperdiciado, y además los gráficos
 * aparecerían desordenados. El de clientes frecuentes viaja aparte porque
 * vive en otro módulo (SPEC-019), pero se pide **en paralelo**, no después.
 *
 * Cada gráfico va acompañado de su cifra principal en texto, porque un
 * gráfico sin número obliga a estimar a ojo.
 */
import { computed, onMounted, ref, watch } from "vue";
import { clientesFrecuentes } from "../../api/clientes";
import { obtenerReporteProducto, obtenerReportes } from "../../api/reportes";
import GraficoBarras from "../../components/GraficoBarras.vue";
import MarcoInterno from "../../components/MarcoInterno.vue";
import NotificacionesBurbuja from "../../components/NotificacionesBurbuja.vue";
import { formatearMoneda } from "../../lib/tema";

const datos = ref(null);
const frecuentes = ref([]);
const cargando = ref(true);
const error = ref(null);

const desde = ref("");
const hasta = ref("");
const atajoActivo = ref("mes");

// SPEC-023: el ranking solo con promociones, y un producto en el tiempo.
const soloPromociones = ref(false);
const productoId = ref(null);
const agrupar = ref("dia");
const datosProducto = ref(null);
const cargandoProducto = ref(false);

const AGRUPACIONES = [["dia", "Día"], ["semana", "Semana"], ["mes", "Mes"]];

function iso(f) {
  return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}`
    + `-${String(f.getDate()).padStart(2, "0")}`;
}

const ATAJOS = {
  hoy: () => { const d = new Date(); return [iso(d), iso(d)]; },
  semana: () => {
    const h = new Date();
    const i = new Date(h);
    // La semana arranca el lunes: getDay() da 0 el domingo, de ahí el ajuste.
    i.setDate(h.getDate() - ((h.getDay() + 6) % 7));
    return [iso(i), iso(h)];
  },
  mes: () => {
    const h = new Date();
    return [iso(new Date(h.getFullYear(), h.getMonth(), 1)), iso(h)];
  },
  anio: () => {
    const h = new Date();
    return [iso(new Date(h.getFullYear(), 0, 1)), iso(h)];
  },
};

const NOMBRES_ATAJO = { hoy: "Hoy", semana: "Esta semana", mes: "Este mes", anio: "Este año" };

async function cargar() {
  error.value = null;
  const rango = { desde: desde.value, hasta: hasta.value };

  // `allSettled` y no `all`: si el módulo de clientes falla, los reportes de
  // venta —que son el grueso de la pantalla— deben pintarse igual.
  const [venta, clientes] = await Promise.allSettled([
    obtenerReportes({ ...rango, soloPromociones: soloPromociones.value }),
    clientesFrecuentes(rango),
  ]);

  if (venta.status === "fulfilled") {
    datos.value = venta.value;
    // Arranca mostrando una promoción, que es lo que más se consulta aquí. Al
    // fijar el producto, el `watch` lo carga; si ya había uno, se recarga con
    // el rango nuevo.
    const primero = venta.value.catalogo?.[0]?.id ?? null;
    if (productoId.value === null && primero !== null) productoId.value = primero;
    else cargarProducto();
  } else {
    error.value = venta.reason?.response?.data?.detalle
      || "No se pudieron cargar los reportes.";
  }
  frecuentes.value = clientes.status === "fulfilled" ? clientes.value : [];
  cargando.value = false;
}

async function cargarProducto() {
  if (!productoId.value) {
    datosProducto.value = null;
    return;
  }
  cargandoProducto.value = true;
  try {
    datosProducto.value = await obtenerReporteProducto({
      plato: productoId.value, desde: desde.value, hasta: hasta.value, agrupar: agrupar.value,
    });
  } catch (e) {
    datosProducto.value = null;
    error.value = e.response?.data?.detalle || "No se pudo cargar el producto.";
  } finally {
    cargandoProducto.value = false;
  }
}

watch([productoId, agrupar], cargarProducto);
watch(soloPromociones, cargar);

const catalogo = computed(() => datos.value?.catalogo ?? []);
const catalogoPromos = computed(() => catalogo.value.filter((p) => p.tipo === "promocion"));
const catalogoPlatos = computed(() => catalogo.value.filter((p) => p.tipo !== "promocion"));

/** Etiqueta de cada periodo según cómo se agrupó. */
function etiquetaPeriodo(inicio) {
  const f = new Date(`${inicio}T12:00:00`);
  if (agrupar.value === "mes") return f.toLocaleDateString("es-CO", { month: "short", year: "numeric" });
  if (agrupar.value === "semana") return `Sem. ${f.toLocaleDateString("es-CO", { day: "numeric", month: "short" })}`;
  return f.toLocaleDateString("es-CO", { day: "numeric", month: "short" });
}

const periodosConVentas = computed(() => (datosProducto.value?.periodos ?? []).filter((p) => p.unidades > 0));

function aplicarAtajo(clave) {
  atajoActivo.value = clave;
  [desde.value, hasta.value] = ATAJOS[clave]();
  cargar();
}

function fechaManual() {
  atajoActivo.value = null;
  cargar();
}

const moneda = formatearMoneda;

/* --- Lo que cada gráfico necesita, ya separado en etiquetas y valores --- */

const productos = computed(() => datos.value?.productos ?? []);
const meseros = computed(() => datos.value?.meseros ?? []);
const porDia = computed(() => datos.value?.por_dia ?? []);
const porHora = computed(() => datos.value?.por_hora ?? []);
const porDiaSemana = computed(() => datos.value?.por_dia_semana ?? []);

/** La hora con más ventas: es la cifra que decide cuánta gente poner. */
const horaPico = computed(() => {
  const mejor = [...porHora.value].sort((a, b) => b.ventas - a.ventas)[0];
  return mejor?.ventas ? mejor : null;
});

const diaPico = computed(() => {
  const mejor = [...porDiaSemana.value].sort((a, b) => b.ventas - a.ventas)[0];
  return mejor?.ventas ? mejor : null;
});

function dia(fecha) {
  return new Date(`${fecha}T12:00:00`).toLocaleDateString("es-CO",
    { day: "numeric", month: "short" });
}

/** Para las marcas de tiempo completas, que traen hora y zona. */
function fecha(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-CO", { day: "numeric", month: "short" });
}

onMounted(() => aplicarAtajo("mes"));
</script>

<template>
  <MarcoInterno titulo="Reportes" ancho="max-w-5xl">
    <template #acciones><NotificacionesBurbuja /></template>

    <p v-if="error" class="mb-4 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta">
      {{ error }}
    </p>

    <!-- ===== Rango ===== -->
    <div class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-4">
      <!-- Los atajos se deslizan en una sola linea en telefono: partidos en dos
           filas ocupaban mas alto que el propio grafico. -->
      <div class="-mx-3.5 mb-3 flex gap-1.5 overflow-x-auto px-3.5 pb-1 sm:mx-0 sm:flex-wrap sm:px-0 sm:pb-0
                  [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <button
          v-for="(_, clave) in ATAJOS" :key="clave"
          @click="aplicarAtajo(clave)"
          class="min-h-11 shrink-0 cursor-pointer rounded-full border px-3.5 text-[12.5px] font-semibold whitespace-nowrap transition-colors sm:px-4"
          :class="atajoActivo === clave
            ? 'border-marca bg-marca text-lienzo'
            : 'border-marca/20 text-marca hover:border-marca'"
        >{{ NOMBRES_ATAJO[clave] }}</button>
      </div>
      <!-- Dos columnas desde el telefono: apiladas desperdiciaban media pantalla. -->
      <div class="grid grid-cols-2 gap-2.5 sm:flex sm:flex-wrap sm:items-end">
        <div class="min-w-0">
          <label for="r-desde" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Desde</label>
          <input
            id="r-desde" v-model="desde" type="date" @change="fechaManual"
            class="min-h-11 w-full rounded-xl border border-marca/20 px-2.5 text-[13px] outline-none focus:border-marca sm:w-auto sm:px-3 sm:text-[13.5px]"
          />
        </div>
        <div class="min-w-0">
          <label for="r-hasta" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Hasta</label>
          <input
            id="r-hasta" v-model="hasta" type="date" @change="fechaManual"
            class="min-h-11 w-full rounded-xl border border-marca/20 px-2.5 text-[13px] outline-none focus:border-marca sm:w-auto sm:px-3 sm:text-[13.5px]"
          />
        </div>
      </div>
    </div>

    <p v-if="cargando" class="py-16 text-center text-tinta/50">Cargando…</p>

    <template v-else-if="datos">
      <!-- ===== Las cifras de cabecera ===== -->
      <div class="mt-3 grid grid-cols-2 gap-2.5 md:grid-cols-4">
        <div class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-4">
          <p class="text-[10px] font-semibold tracking-[0.10em] text-marca/55 uppercase sm:text-[10.5px]">Vendido</p>
          <p class="mt-1.5 font-display text-[19px] leading-none font-light break-words sm:text-[24px] text-marca">
            {{ moneda(datos.resumen.vendido) }}
          </p>
          <p class="mt-1 text-[11px] text-tinta/45">sin propina</p>
        </div>
        <div class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-4">
          <p class="text-[10px] font-semibold tracking-[0.10em] text-marca/55 uppercase sm:text-[10.5px]">Entró a caja</p>
          <p class="mt-1.5 font-display text-[19px] leading-none font-light break-words sm:text-[24px] text-emerald-700">
            {{ moneda(datos.resumen.cobrado) }}
          </p>
          <p class="mt-1 text-[11px] text-tinta/45">todo incluido</p>
        </div>
        <div class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-4">
          <p class="text-[10px] font-semibold tracking-[0.10em] text-marca/55 uppercase sm:text-[10.5px]">Ticket promedio</p>
          <p class="mt-1.5 font-display text-[19px] leading-none font-light break-words sm:text-[24px] text-marca">
            {{ moneda(datos.resumen.ticket_promedio) }}
          </p>
          <p class="mt-1 text-[11px] text-tinta/45">por venta</p>
        </div>
        <div class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-4">
          <p class="text-[10px] font-semibold tracking-[0.10em] text-marca/55 uppercase sm:text-[10.5px]">Ventas</p>
          <p class="mt-1.5 font-display text-[19px] leading-none font-light break-words sm:text-[24px] text-marca">
            {{ datos.resumen.ventas }}
          </p>
          <p class="mt-1 text-[11px] text-tinta/45">
            {{ moneda(datos.resumen.propinas) }} en propinas
          </p>
        </div>
      </div>

      <!-- ===== Un producto en el tiempo (SPEC-023) =====
           Una promo o un plato: cuántas unidades y cuánto dejó, por día,
           semana o mes. Un combo cuenta como una unidad. -->
      <section class="mt-3 rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-5">
        <h2 class="font-display text-[17px] leading-tight font-light text-marca sm:text-[20px]">
          Cómo se vende un producto
        </h2>
        <p class="mb-3.5 text-[12.5px] text-tinta/50">Una promoción o cualquier plato, en el rango elegido.</p>

        <div class="grid gap-2.5 sm:grid-cols-[1fr_auto] sm:items-end">
          <div class="min-w-0">
            <label for="r-producto" class="mb-1.5 block text-[10.5px] font-semibold tracking-[0.12em] text-marca/55 uppercase">Producto</label>
            <select
              id="r-producto" v-model.number="productoId"
              class="min-h-11 w-full cursor-pointer rounded-xl border border-marca/20 bg-white px-3 text-[13.5px] outline-none focus:border-marca"
            >
              <optgroup v-if="catalogoPromos.length" label="Promociones">
                <option v-for="p in catalogoPromos" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </optgroup>
              <optgroup label="Platos">
                <option v-for="p in catalogoPlatos" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </optgroup>
            </select>
          </div>
          <div class="grid grid-cols-3 gap-1 rounded-xl bg-marca-suave/60 p-1" role="radiogroup" aria-label="Agrupar por">
            <button
              v-for="[clave, nombre] in AGRUPACIONES" :key="clave"
              role="radio" :aria-checked="agrupar === clave" @click="agrupar = clave"
              class="min-h-11 cursor-pointer rounded-lg px-3.5 text-[12.5px] font-semibold transition-colors"
              :class="agrupar === clave ? 'bg-white text-marca shadow-sm' : 'text-marca/60'"
            >{{ nombre }}</button>
          </div>
        </div>

        <p v-if="cargandoProducto && !datosProducto" class="py-8 text-center text-[13px] text-tinta/45">Cargando…</p>
        <template v-else-if="datosProducto">
          <div class="mt-3.5 grid grid-cols-2 gap-2.5">
            <div class="rounded-xl bg-lienzo-alt/60 p-3">
              <p class="text-[10px] font-semibold tracking-[0.10em] text-marca/55 uppercase">Unidades</p>
              <p class="mt-1 font-display text-[22px] leading-none font-light text-marca">{{ datosProducto.unidades }}</p>
            </div>
            <div class="rounded-xl bg-lienzo-alt/60 p-3">
              <p class="text-[10px] font-semibold tracking-[0.10em] text-marca/55 uppercase">Ingresos</p>
              <p class="mt-1 font-display text-[22px] leading-none font-light break-words text-marca">{{ moneda(datosProducto.ingresos) }}</p>
            </div>
          </div>

          <div class="mt-4">
            <GraficoBarras
              formato="numero"
              :etiquetas="datosProducto.periodos.map((p) => etiquetaPeriodo(p.inicio))"
              :valores="datosProducto.periodos.map((p) => p.unidades)"
              :alto="220"
            />
          </div>

          <div v-if="periodosConVentas.length" class="mt-4 overflow-x-auto rounded-xl border border-marca/12">
            <table class="w-full text-[13px]">
              <thead>
                <tr class="bg-lienzo-alt/60 text-left text-[10.5px] tracking-[0.10em] text-marca/60 uppercase">
                  <th class="px-3 py-2 font-semibold">{{ AGRUPACIONES.find(([c]) => c === agrupar)[1] }}</th>
                  <th class="px-3 py-2 text-right font-semibold">Unidades</th>
                  <th class="px-3 py-2 text-right font-semibold">Ingresos</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in periodosConVentas" :key="p.inicio" class="border-t border-marca/8">
                  <td class="px-3 py-2">{{ etiquetaPeriodo(p.inicio) }}</td>
                  <td class="px-3 py-2 text-right tabular-nums">{{ p.unidades }}</td>
                  <td class="px-3 py-2 text-right tabular-nums">{{ moneda(p.ingresos) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="mt-3 text-[12.5px] text-tinta/50">Sin ventas de este producto en el rango.</p>
        </template>
      </section>

      <!-- ===== Evolución diaria ===== -->
      <section class="mt-3 rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-5">
        <div class="mb-1 flex flex-wrap items-baseline justify-between gap-2">
          <h2 class="font-display text-[17px] leading-tight font-light text-marca sm:text-[20px]">
            Cómo van las ventas
          </h2>
          <p v-if="porDia.length" class="text-[12.5px] text-tinta/55">
            {{ porDia.length }} {{ porDia.length === 1 ? "día con ventas" : "días con ventas" }}
          </p>
        </div>
        <p class="mb-4 text-[12.5px] text-tinta/50">Lo que entró a caja cada día del rango.</p>
        <GraficoBarras
          tipo="line"
          :etiquetas="porDia.map((d) => dia(d.fecha))"
          :valores="porDia.map((d) => d.cobrado)"
          :alto="240"
        />
      </section>

      <div class="mt-3 grid gap-3 md:grid-cols-2">
        <!-- ===== Productos más vendidos ===== -->
        <section class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-5">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 class="font-display text-[17px] leading-tight font-light text-marca sm:text-[20px]">
              Lo que más se vende
            </h2>
            <label class="flex cursor-pointer items-center gap-1.5 text-[12px] font-semibold text-marca/70">
              <span class="-m-2.5 grid min-h-11 min-w-11 place-items-center p-2.5"><input v-model="soloPromociones" type="checkbox" class="size-4 cursor-pointer accent-marca" /></span>
              Solo promociones
            </label>
          </div>
          <p v-if="productos.length" class="mt-1.5 mb-4 text-[12.5px] text-tinta/55">
            <strong class="text-tinta">{{ productos[0].nombre }}</strong>
            encabeza con {{ productos[0].cantidad }} unidades
          </p>
          <p v-else class="mt-1.5 mb-4 text-[12.5px] text-tinta/50">Por unidades vendidas.</p>
          <GraficoBarras
            horizontal formato="numero"
            :etiquetas="productos.map((p) => p.nombre)"
            :valores="productos.map((p) => p.cantidad)"
            :alto="Math.max(200, productos.length * 34)"
          />
        </section>

        <!-- ===== Ventas por mesero ===== -->
        <section class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-5">
          <h2 class="font-display text-[17px] leading-tight font-light text-marca sm:text-[20px]">
            Quién está vendiendo
          </h2>
          <p v-if="meseros.length" class="mt-1.5 mb-4 text-[12.5px] text-tinta/55">
            <strong class="text-tinta">{{ meseros[0].mesero }}</strong>
            lidera con {{ moneda(meseros[0].vendido) }}
          </p>
          <p v-else class="mt-1.5 mb-4 text-[12.5px] text-tinta/50">
            Atribuido a quien tomó el pedido, sin propina.
          </p>
          <GraficoBarras
            horizontal
            :etiquetas="meseros.map((m) => m.mesero)"
            :valores="meseros.map((m) => m.vendido)"
            :alto="Math.max(200, meseros.length * 40)"
          />
        </section>

        <!-- ===== Hora de mayor demanda ===== -->
        <section class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-5">
          <h2 class="font-display text-[17px] leading-tight font-light text-marca sm:text-[20px]">
            A qué horas llega la gente
          </h2>
          <p v-if="horaPico" class="mt-1.5 mb-4 text-[12.5px] text-tinta/55">
            La hora pico son las
            <strong class="text-tinta">{{ String(horaPico.hora).padStart(2, "0") }}:00</strong>,
            con {{ horaPico.ventas }} {{ horaPico.ventas === 1 ? "venta" : "ventas" }}
          </p>
          <p v-else class="mt-1.5 mb-4 text-[12.5px] text-tinta/50">Ventas por hora del día.</p>
          <GraficoBarras
            formato="numero"
            :etiquetas="porHora.map((h) => String(h.hora).padStart(2, '0'))"
            :valores="porHora.map((h) => h.ventas)"
            :alto="220"
          />
        </section>

        <!-- ===== Día de la semana ===== -->
        <section class="rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-5">
          <h2 class="font-display text-[17px] leading-tight font-light text-marca sm:text-[20px]">
            Qué días se mueve más
          </h2>
          <p v-if="diaPico" class="mt-1.5 mb-4 text-[12.5px] text-tinta/55">
            El mejor día es el
            <strong class="text-tinta">{{ diaPico.dia.toLowerCase() }}</strong>,
            con {{ diaPico.ventas }} {{ diaPico.ventas === 1 ? "venta" : "ventas" }}
          </p>
          <p v-else class="mt-1.5 mb-4 text-[12.5px] text-tinta/50">Ventas por día de la semana.</p>
          <GraficoBarras
            formato="numero"
            :etiquetas="porDiaSemana.map((d) => d.dia.slice(0, 3))"
            :valores="porDiaSemana.map((d) => d.ventas)"
            :alto="220"
          />
        </section>
      </div>

      <!-- ===== Clientes frecuentes (SPEC-019) =====
           Lista y no gráfico a propósito: de un cliente frecuente lo que se
           usa es el teléfono para llamarlo, y un número no cabe en una barra. -->
      <section class="mt-3 rounded-2xl border border-marca/12 bg-white p-3.5 sm:p-5">
        <h2 class="font-display text-[17px] leading-tight font-light text-marca sm:text-[20px]">
          Quiénes vuelven
        </h2>
        <p v-if="frecuentes.length" class="mt-1.5 text-[12.5px] text-tinta/55">
          <strong class="text-tinta">{{ frecuentes[0].nombre }}</strong>
          encabeza con {{ frecuentes[0].compras }}
          {{ frecuentes[0].compras === 1 ? "compra" : "compras" }}
        </p>
        <p v-else class="mt-1.5 text-[12.5px] text-tinta/50">
          Todavía no hay domicilios con teléfono en este rango.
        </p>

        <ul v-if="frecuentes.length" class="mt-4 overflow-hidden rounded-xl border border-marca/12">
          <li
            v-for="(c, i) in frecuentes" :key="c.id"
            class="flex items-center gap-3 border-b border-marca/8 px-3 py-3 last:border-b-0 sm:px-4"
          >
            <span class="w-5 shrink-0 text-[12px] font-semibold tabular-nums text-marca/45">
              {{ i + 1 }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-[13.5px] font-semibold text-tinta">{{ c.nombre }}</p>
              <p class="truncate text-[11.5px] text-tinta/50">
                {{ c.telefono }} · última: {{ fecha(c.ultima_compra) }}
              </p>
            </div>
            <div class="shrink-0 text-right">
              <p class="text-[13.5px] font-semibold tabular-nums text-marca">
                {{ moneda(c.gastado) }}
              </p>
              <p class="text-[11.5px] text-tinta/45">
                {{ c.compras }} {{ c.compras === 1 ? "compra" : "compras" }}
              </p>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </MarcoInterno>
</template>
