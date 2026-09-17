<script setup>
/**
 * CRUD del menú desde el panel (SPEC-007). Hasta hoy, agregar un plato
 * exigía la terminal del servidor — la diferencia entre un demo y un
 * producto que un restaurante pueda operar solo.
 *
 * La foto se sube desde aquí mismo (multipart); el precio se guarda en la
 * unidad menor sin decimales, como manda el modelo.
 */
import { computed, onMounted, ref } from "vue";
import {
  listarCategorias, listarPlatosPanel, guardarPlato, eliminarPlato,
  guardarCategoria, eliminarCategoria,
} from "../../api/menu";
import {
  listarObservaciones, crearObservacion, borrarObservacion,
} from "../../api/menu";
import { listarEstaciones } from "../../api/estaciones";
import MarcoInterno from "../../components/MarcoInterno.vue";
import AdminPestanas from "../../components/AdminPestanas.vue";
import { formatearMoneda } from "../../lib/tema";
import {
  DIAS_SEMANA, ESTADOS_PROMOCION, esPromocion, resumenVigencia,
} from "../../lib/promociones";

const categorias = ref([]);
const platos = ref([]);
const estaciones = ref([]);
const cargando = ref(true);
const mensaje = ref(null);

// Formularios
const editando = ref(null);   // plato en edición (copia) o null
const fotoNueva = ref(null);  // File pendiente de subir
const nuevaCategoria = ref("");

/**
 * Observaciones propias del plato en edición (SPEC-003). Solo las suyas: las
 * generales se ven en la pestaña Cobro y aplican a todo, así que repetirlas
 * aquí solo confundiría sobre cuál se está tocando.
 *
 * Se guardan al instante, no con el botón «Guardar» del plato: son filas
 * aparte, y esperar al guardado obligaría a inventar un carrito de cambios
 * para algo que es agregar y quitar etiquetas.
 */
const observacionesPlato = ref([]);
const nuevaObservacion = ref("");

async function cargarObservacionesDe(platoId) {
  observacionesPlato.value = platoId
    ? await listarObservaciones({ platoId })
    : [];
}

async function agregarObservacionPlato() {
  const texto = nuevaObservacion.value.trim();
  if (!texto || !editando.value?.id) return;
  try {
    await crearObservacion(texto, { platoId: editando.value.id });
    nuevaObservacion.value = "";
    await cargarObservacionesDe(editando.value.id);
  } catch (e) {
    avisar(e.response?.data?.texto?.[0] || "Ese plato ya tiene esa etiqueta.", true);
  }
}

async function quitarObservacionPlato(obs) {
  await borrarObservacion(obs.id);
  await cargarObservacionesDe(editando.value.id);
}

/**
 * Observaciones POR CATEGORÍA (SPEC-003, nivel intermedio, 2026-09-03): ni
 * tan anchas como una general ni tan angostas como una de un solo plato —
 * "término medio" en Del Asador, "sin hielo" en Bebidas, para toda la
 * sección de una vez.
 *
 * Se cargan solo de la categoría que el administrador abre, no de todas: la
 * mayoría de las veces no se está tocando ninguna, y cargar N categorías de
 * una sería trabajo desperdiciado.
 */
const categoriaAbierta = ref(null); // id de la categoría con el panel abierto
const observacionesCategoria = ref([]);
const nuevaObservacionCategoria = ref("");

async function alternarObservacionesCategoria(cat) {
  if (categoriaAbierta.value === cat.id) {
    categoriaAbierta.value = null;
    return;
  }
  categoriaAbierta.value = cat.id;
  nuevaObservacionCategoria.value = "";
  observacionesCategoria.value = await listarObservaciones({ categoriaId: cat.id });
}

async function agregarObservacionCategoria(cat) {
  const texto = nuevaObservacionCategoria.value.trim();
  if (!texto) return;
  try {
    await crearObservacion(texto, { categoriaId: cat.id });
    nuevaObservacionCategoria.value = "";
    observacionesCategoria.value = await listarObservaciones({ categoriaId: cat.id });
  } catch (e) {
    avisar(e.response?.data?.texto?.[0] || "Esa categoría ya tiene esa etiqueta.", true);
  }
}

async function quitarObservacionCategoria(obs, cat) {
  await borrarObservacion(obs.id);
  observacionesCategoria.value = await listarObservaciones({ categoriaId: cat.id });
}

const platosPorCategoria = computed(() => {
  const mapa = new Map(categorias.value.map((c) => [c.id, []]));
  for (const p of platos.value) mapa.get(p.categoria_id)?.push(p);
  return mapa;
});

// SPEC-023: las promociones no pertenecen a ninguna categoría.
const promociones = computed(() => platos.value.filter(esPromocion));

/** Primer mensaje legible de una respuesta de error de la API. */
function primerError(datos) {
  if (!datos) return "No se pudo guardar.";
  if (typeof datos === "string") return datos;
  if (datos.detalle) return datos.detalle;
  const primero = Object.values(datos)[0];
  return Array.isArray(primero) ? String(primero[0]) : String(primero);
}

function avisar(texto, error = false) {
  mensaje.value = { texto, error };
  setTimeout(() => (mensaje.value = null), 3000);
}

async function cargar() {
  [categorias.value, platos.value, estaciones.value] = await Promise.all([
    listarCategorias(), listarPlatosPanel(), listarEstaciones(),
  ]);
  cargando.value = false;
}

/* --- Categorías ---------------------------------------------------------- */

async function crearCategoria() {
  const nombre = nuevaCategoria.value.trim();
  if (!nombre) return;
  try {
    await guardarCategoria(null, { nombre, orden: categorias.value.length });
    nuevaCategoria.value = "";
    await cargar();
    avisar(`Categoría «${nombre}» creada`);
  } catch (e) {
    avisar(e.response?.data?.nombre?.[0] || "No se pudo crear la categoría.", true);
  }
}

async function moverCategoria(cat, estacionId) {
  // La base del ruteo (SPEC-005): mover una categoría de cocina a bar es
  // este cambio, nada más. El siguiente pedido ya sale ruteado distinto.
  await guardarCategoria(cat.id, { estacion: estacionId || null });
  avisar(`«${cat.nombre}» ahora va a ${estaciones.value.find((e) => e.id === estacionId)?.nombre || "la estación por defecto"}`);
}

async function borrarCategoria(cat) {
  if (cat.cantidad_platos > 0) {
    avisar("Primero mueve o elimina sus platos.", true);
    return;
  }
  try {
    await eliminarCategoria(cat.id);
    await cargar();
    avisar(`Categoría «${cat.nombre}» eliminada`);
  } catch {
    avisar("No se pudo eliminar.", true);
  }
}

/* --- Platos -------------------------------------------------------------- */

/** Lo que comparten un plato y una promoción al abrir el formulario. */
function formularioVacio(tipo, categoriaId) {
  return {
    id: null, tipo, categoria: categoriaId ?? categorias.value[0]?.id ?? null,
    nombre: "", descripcion: "", precio: null, disponible: true, alergenos: "", estadisticas: [],
    // Promoción (SPEC-023). Arranca hoy, todos los días, todo el día.
    activa: true,
    vigente_desde: new Date().toLocaleDateString("en-CA"),
    vigente_hasta: "",
    dias_semana: [0, 1, 2, 3, 4, 5, 6],
    hora_inicio: "", hora_fin: "",
    componentes: [{ cantidad: 1, nombre: "", especificacion: "" }],
  };
}

function nuevoPlato(categoriaId) {
  editando.value = formularioVacio("plato", categoriaId);
  fotoNueva.value = null;
  observacionesPlato.value = [];
  nuevaObservacion.value = "";
}

function nuevaPromocion() {
  nuevoPlato(null);
  editando.value.tipo = "promocion";
}

function editarPlato(p) {
  editando.value = {
    ...formularioVacio(p.tipo, p.categoria_id),
    id: p.id, nombre: p.nombre,
    descripcion: p.descripcion, precio: p.precio,
    disponible: p.disponible, alergenos: p.alergenos,
    estadisticas: (p.estadisticas ?? []).map((dato) => [dato[0], dato[1]]),
  };
  if (esPromocion(p)) {
    Object.assign(editando.value, {
      activa: p.activa,
      vigente_desde: p.vigente_desde ?? "",
      vigente_hasta: p.vigente_hasta ?? "",
      dias_semana: [...(p.dias_semana ?? [])],
      hora_inicio: p.hora_inicio?.slice(0, 5) ?? "",
      hora_fin: p.hora_fin?.slice(0, 5) ?? "",
      componentes: (p.componentes ?? []).map(({ cantidad, nombre, especificacion }) => (
        { cantidad, nombre, especificacion }
      )),
    });
  }
  fotoNueva.value = null;
  nuevaObservacion.value = "";
  cargarObservacionesDe(p.id);
}

/* --- Componentes y vigencia de una promoción (SPEC-023) ------------------ */

function agregarComponente() {
  editando.value.componentes.push({ cantidad: 1, nombre: "", especificacion: "" });
}

function quitarComponente(indice) {
  editando.value.componentes.splice(indice, 1);
}

function moverComponente(indice, paso) {
  const lista = editando.value.componentes;
  const destino = indice + paso;
  if (destino < 0 || destino >= lista.length) return;
  [lista[indice], lista[destino]] = [lista[destino], lista[indice]];
}

function alternarDia(dia) {
  const dias = editando.value.dias_semana;
  const i = dias.indexOf(dia);
  if (i === -1) dias.push(dia);
  else dias.splice(i, 1);
  dias.sort((a, b) => a - b);
}

/** Qué le falta a la promo, en palabras, antes de mandarla al servidor. */
function faltaEnPromocion(e) {
  const componentes = e.componentes.filter((c) => c.nombre.trim());
  if (!componentes.length) return "La promoción necesita al menos un componente con nombre.";
  if (componentes.some((c) => !c.cantidad || c.cantidad < 1)) return "Cada componente necesita una cantidad de 1 o más.";
  if (!e.vigente_desde) return "Indica desde qué día vale la promoción.";
  if (e.vigente_hasta && e.vigente_hasta < e.vigente_desde) return "La fecha de fin no puede ser antes de la de inicio.";
  if (!e.dias_semana.length) return "Elige al menos un día de la semana.";
  if (Boolean(e.hora_inicio) !== Boolean(e.hora_fin)) return "Indica las dos horas de la franja, o ninguna.";
  return null;
}

function agregarEstadistica() {
  editando.value.estadisticas.push(["", ""]);
}

function quitarEstadistica(indice) {
  editando.value.estadisticas.splice(indice, 1);
}

async function guardar() {
  const e = editando.value;
  const promo = e.tipo === "promocion";
  if (!e.nombre.trim() || !e.precio || e.precio < 0) {
    avisar(promo ? "La promoción necesita nombre y precio." : "El plato necesita nombre y precio.", true);
    return;
  }
  const falta = promo ? faltaEnPromocion(e) : null;
  if (falta) {
    avisar(falta, true);
    return;
  }

  const datos = {
    nombre: e.nombre.trim(),
    descripcion: e.descripcion, precio: e.precio,
    disponible: e.disponible, alergenos: e.alergenos,
    estadisticas: e.estadisticas.filter(([valor, etiqueta]) => String(valor).trim() && String(etiqueta).trim()),
  };
  if (!e.id) datos.tipo = e.tipo;
  if (promo) {
    Object.assign(datos, {
      activa: e.activa,
      vigente_desde: e.vigente_desde,
      vigente_hasta: e.vigente_hasta || null,
      dias_semana: e.dias_semana,
      hora_inicio: e.hora_inicio || null,
      hora_fin: e.hora_fin || null,
      componentes: e.componentes
        .filter((c) => c.nombre.trim())
        .map((c) => ({ cantidad: c.cantidad, nombre: c.nombre.trim(), especificacion: c.especificacion.trim() })),
    });
  } else {
    datos.categoria = e.categoria;
  }

  try {
    await guardarPlato(e.id, datos, fotoNueva.value);
    avisar(e.id ? `«${e.nombre}» actualizado` : `«${e.nombre}» ${promo ? "creada" : "agregado al menú"}`);
    editando.value = null;
    await cargar();
  } catch (err) {
    avisar(primerError(err.response?.data), true);
  }
}

/** Encender o apagar una promoción sin abrir el formulario (SPEC-023). */
async function alternarActiva(p) {
  try {
    const actualizado = await guardarPlato(p.id, { activa: !p.activa });
    Object.assign(p, actualizado);
    await cargar();
    avisar(p.activa ? `«${p.nombre}» encendida` : `«${p.nombre}» apagada`);
  } catch (err) {
    avisar(primerError(err.response?.data), true);
  }
}

/**
 * Disponible/agotado en un toque, sin abrir el formulario: es el cambio
 * más frecuente del servicio (se acabó algo a mitad de noche).
 */
async function alternarDisponible(p) {
  p.disponible = !p.disponible;
  try {
    await guardarPlato(p.id, { disponible: p.disponible });
    avisar(p.disponible ? `«${p.nombre}» disponible` : `«${p.nombre}» agotado`);
  } catch {
    p.disponible = !p.disponible;
    avisar("No se pudo cambiar.", true);
  }
}

async function borrarPlato(p) {
  // Un plato con ventas está protegido por la base (PROTECT): el historial
  // congelado lo referencia. El error se muestra, no se esquiva.
  try {
    await eliminarPlato(p.id);
    await cargar();
    avisar(`«${p.nombre}» eliminado`);
  } catch (err) {
    avisar(err.response?.data?.detalle || `«${p.nombre}» tiene ventas registradas: márcalo agotado en su lugar.`, true);
  }
}

const moneda = { format: formatearMoneda };

onMounted(cargar);
</script>

<template>
  <MarcoInterno titulo="Menú" ancho="max-w-4xl">
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
      <!-- ===== Promociones (SPEC-023) ===== -->
      <section class="mb-6 overflow-hidden rounded-xl border-2 border-panel-marca/30 bg-white">
        <header class="flex flex-wrap items-center gap-3 border-b border-panel-borde bg-panel-alt px-4 py-3">
          <h2 class="text-[14px] font-semibold">Promociones</h2>
          <p class="text-[12px] text-panel-tinta/50">Van de primeras en el menú del cliente, y enteras a la estación por defecto.</p>
          <button
            @click="nuevaPromocion"
            class="ml-auto min-h-11 cursor-pointer rounded-lg bg-panel-marca px-3 text-[12px] font-semibold text-white"
          >+ Promoción</button>
        </header>

        <div class="divide-y divide-panel-borde">
          <div
            v-for="p in promociones" :key="p.id"
            class="flex flex-wrap items-center gap-3 px-4 py-3"
          >
            <img v-if="p.foto" :src="p.foto" alt="" class="h-11 w-14 shrink-0 rounded-md object-cover" />
            <div v-else class="grid h-11 w-14 shrink-0 place-items-center rounded-md bg-panel-alt text-panel-tinta/30">—</div>

            <div class="min-w-0 flex-1 basis-[calc(100%-4.5rem)] sm:basis-auto">
              <p class="flex flex-wrap items-center gap-2 text-[14px] leading-snug font-semibold">
                {{ p.nombre }}
                <span
                  class="rounded-full px-2.5 py-0.5 text-[10.5px] font-bold tracking-wide uppercase"
                  :class="ESTADOS_PROMOCION[p.estado_promocion]?.clase"
                >{{ ESTADOS_PROMOCION[p.estado_promocion]?.texto }}</span>
              </p>
              <p class="text-[12px] text-panel-tinta/50">
                {{ moneda.format(p.precio) }} · {{ resumenVigencia(p) }}
              </p>
            </div>

            <button
              @click="alternarActiva(p)"
              class="min-h-11 cursor-pointer rounded-full px-3 text-[11px] font-bold tracking-wide uppercase"
              :class="p.activa ? 'bg-emerald-100 text-emerald-800' : 'bg-panel-alt text-panel-tinta/60'"
            >{{ p.activa ? "Encendida" : "Apagada" }}</button>
            <button
              @click="alternarDisponible(p)"
              class="min-h-11 cursor-pointer rounded-full px-3 text-[11px] font-bold tracking-wide uppercase"
              :class="p.disponible ? 'bg-emerald-100 text-emerald-800' : 'bg-alerta/10 text-alerta'"
            >{{ p.disponible ? "Disponible" : "Agotada" }}</button>
            <button
              @click="editarPlato(p)"
              class="min-h-11 cursor-pointer rounded-lg border border-panel-borde px-3 text-[12px] font-semibold"
            >Editar</button>
            <button
              @click="borrarPlato(p)" aria-label="Eliminar promoción"
              class="grid min-h-11 min-w-11 cursor-pointer place-items-center text-panel-tinta/35 hover:text-alerta"
            >✕</button>
          </div>

          <p v-if="!promociones.length" class="px-4 py-4 text-[13px] text-panel-tinta/40">
            Sin promociones. Una promoción es un combo con precio propio y tiempo limitado.
          </p>
        </div>
      </section>

      <section
        v-for="cat in categorias" :key="cat.id"
        class="mb-6 overflow-hidden rounded-xl border border-panel-borde bg-white"
      >
        <header class="flex flex-wrap items-center gap-3 border-b border-panel-borde bg-panel-alt px-4 py-3">
          <h2 class="text-[14px] font-semibold">{{ cat.nombre }}</h2>

          <!-- A qué estación va lo de esta categoría (base del ruteo) -->
          <select
            :value="cat.estacion" @change="moverCategoria(cat, Number($event.target.value) || null)"
            class="cursor-pointer rounded-lg border border-panel-borde bg-white px-2.5 py-1.5 text-[12px]"
          >
            <option :value="null">Estación por defecto</option>
            <option v-for="e in estaciones" :key="e.id" :value="e.id">→ {{ e.nombre }}</option>
          </select>

          <div class="ml-auto flex items-center gap-2">
            <button
              @click="alternarObservacionesCategoria(cat)"
              class="cursor-pointer rounded-lg border px-3 py-1.5 text-[12px] font-semibold"
              :class="categoriaAbierta === cat.id
                ? 'border-panel-marca text-panel-marca'
                : 'border-panel-borde text-panel-tinta/70'"
            >Observaciones</button>
            <button
              @click="nuevoPlato(cat.id)"
              class="cursor-pointer rounded-lg bg-panel-marca px-3 py-1.5 text-[12px] font-semibold text-white"
            >+ Plato</button>
            <button
              v-if="cat.cantidad_platos === 0"
              @click="borrarCategoria(cat)"
              class="cursor-pointer rounded-lg px-2 py-1.5 text-[12px] font-semibold text-alerta"
            >Eliminar</button>
          </div>
        </header>

        <!-- Observaciones de TODA la sección (SPEC-003, nivel intermedio):
             se suman a las generales en cada plato de aquí adentro. -->
        <div
          v-if="categoriaAbierta === cat.id"
          class="border-b border-panel-borde bg-panel-alt/40 px-4 py-3.5"
        >
          <p class="mb-2.5 text-[12px] text-panel-tinta/55">
            Se suman a las generales en <strong>todos los platos de «{{ cat.nombre }}»</strong>,
            sin tocar las demás secciones.
          </p>
          <div v-if="observacionesCategoria.length" class="mb-2.5 flex flex-wrap gap-1.5">
            <span
              v-for="o in observacionesCategoria" :key="o.id"
              class="flex items-center gap-1 rounded-full border border-panel-borde bg-white py-1 pr-1 pl-3 text-[12.5px] font-semibold"
            >
              {{ o.texto }}
              <button
                @click="quitarObservacionCategoria(o, cat)" title="Quitar"
                class="-my-3 -mr-1 flex min-h-11 min-w-11 cursor-pointer items-center justify-center rounded-full text-panel-tinta/40 hover:bg-alerta/10 hover:text-alerta"
              >×</button>
            </span>
          </div>
          <div class="flex gap-2">
            <input
              v-model="nuevaObservacionCategoria" type="text" maxlength="60"
              placeholder="término medio, sin hielo…"
              @keyup.enter="agregarObservacionCategoria(cat)"
              class="min-h-11 flex-1 rounded-lg border border-panel-borde bg-white px-3 text-[13px] outline-none focus:border-panel-marca"
            />
            <button
              @click="agregarObservacionCategoria(cat)"
              class="min-h-11 cursor-pointer rounded-lg border border-panel-borde bg-white px-3.5 text-[12.5px] font-semibold hover:border-panel-marca"
            >Agregar</button>
          </div>
        </div>

        <div class="divide-y divide-panel-borde">
          <div
            v-for="p in platosPorCategoria.get(cat.id)" :key="p.id"
            class="flex flex-wrap items-center gap-3 px-4 py-3"
            :class="{ 'opacity-50': !p.disponible }"
          >
            <img v-if="p.foto" :src="p.foto" alt="" class="h-11 w-14 shrink-0 rounded-md object-cover" />
            <div v-else class="grid h-11 w-14 shrink-0 place-items-center rounded-md bg-panel-alt text-panel-tinta/30">—</div>

            <!-- En telefono el nombre toma la linea (menos la miniatura) y las
                 acciones bajan; antes le quedaban 21px (SPEC-022 B1) -->
            <div class="min-w-0 flex-1 basis-[calc(100%-4.5rem)] sm:basis-auto">
              <p class="text-[14px] leading-snug font-semibold">{{ p.nombre }}</p>
              <p class="text-[12px] text-panel-tinta/50">{{ moneda.format(p.precio) }}</p>
            </div>

            <button
              @click="alternarDisponible(p)"
              class="cursor-pointer rounded-full px-3 py-1.5 text-[11px] font-bold tracking-wide uppercase"
              :class="p.disponible ? 'bg-emerald-100 text-emerald-800' : 'bg-alerta/10 text-alerta'"
            >{{ p.disponible ? "Disponible" : "Agotado" }}</button>

            <button
              @click="editarPlato(p)"
              class="cursor-pointer rounded-lg border border-panel-borde px-3 py-1.5 text-[12px] font-semibold"
            >Editar</button>
            <button
              @click="borrarPlato(p)" aria-label="Eliminar plato"
              class="grid min-h-11 min-w-11 cursor-pointer place-items-center text-panel-tinta/35 hover:text-alerta"
            >✕</button>
          </div>

          <p v-if="!platosPorCategoria.get(cat.id)?.length" class="px-4 py-4 text-[13px] text-panel-tinta/40">
            Sin platos todavía.
          </p>
        </div>
      </section>

      <!-- Nueva categoría -->
      <div class="flex gap-2">
        <input
          v-model="nuevaCategoria" type="text" maxlength="80"
          placeholder="Nueva categoría (p.ej. Desayunos)…" @keyup.enter="crearCategoria"
          class="flex-1 rounded-lg border border-panel-borde bg-white px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
        />
        <button
          @click="crearCategoria"
          class="cursor-pointer rounded-lg bg-panel-marca px-4 py-2.5 text-[13px] font-semibold text-white"
        >Crear</button>
      </div>
    </template>

    <!-- ===== Formulario de plato ===== -->
    <div
      v-if="editando"
      class="fixed inset-0 z-50 flex items-end justify-center bg-panel-tinta/50 backdrop-blur-sm sm:items-center"
      @click.self="editando = null"
    >
      <div class="flex max-h-[90dvh] w-full flex-col overflow-y-auto rounded-t-2xl bg-white p-5 sm:max-w-lg sm:rounded-2xl">
        <h2 class="mb-4 text-[16px] font-semibold">
          <template v-if="editando.tipo === 'promocion'">{{ editando.id ? "Editar promoción" : "Nueva promoción" }}</template>
          <template v-else>{{ editando.id ? "Editar plato" : "Nuevo plato" }}</template>
        </h2>

        <!-- El tipo solo se elige al crear: convertir un plato con ventas en
             promoción cambiaría lo que dicen sus reportes (SPEC-023). -->
        <div v-if="!editando.id" class="mb-4 grid grid-cols-2 gap-1 rounded-xl bg-panel-alt p-1" role="radiogroup" aria-label="Tipo">
          <button
            v-for="opcion in [['plato', 'Plato'], ['promocion', 'Promoción']]" :key="opcion[0]"
            role="radio" :aria-checked="editando.tipo === opcion[0]"
            @click="editando.tipo = opcion[0]"
            class="min-h-11 cursor-pointer rounded-lg text-[13px] font-semibold transition-colors"
            :class="editando.tipo === opcion[0] ? 'bg-white text-panel-marca shadow-sm' : 'text-panel-tinta/60'"
          >{{ opcion[1] }}</button>
        </div>

        <label class="mb-1 text-[12px] font-semibold text-panel-tinta/60">Nombre</label>
        <input
          v-model="editando.nombre" type="text" maxlength="140"
          class="mb-3 rounded-lg border border-panel-borde px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
        />

        <label class="mb-1 text-[12px] font-semibold text-panel-tinta/60">Precio (sin decimales)</label>
        <input
          v-model.number="editando.precio" type="number" min="0" step="500"
          class="mb-3 rounded-lg border border-panel-borde px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
        />

        <template v-if="editando.tipo !== 'promocion'">
          <label class="mb-1 text-[12px] font-semibold text-panel-tinta/60">Categoría</label>
          <select
            v-model.number="editando.categoria"
            class="mb-3 cursor-pointer rounded-lg border border-panel-borde bg-white px-3 py-2.5 text-sm"
          >
            <option v-for="c in categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
          </select>
        </template>

        <template v-else>
          <!-- Qué incluye: texto libre, en el orden en que se muestra -->
          <div class="mb-4 rounded-xl border border-panel-borde bg-panel-alt/35 p-3">
            <div class="mb-2 flex items-center justify-between gap-3">
              <div>
                <p class="text-[12px] font-semibold text-panel-tinta/60">Qué incluye</p>
                <p class="mt-0.5 text-[11px] text-panel-tinta/50">La especificación (ingredientes) la ve el cliente al abrir la promo; cocina ve cantidad y nombre.</p>
              </div>
              <button
                @click="agregarComponente"
                class="min-h-11 shrink-0 cursor-pointer rounded-lg border border-panel-borde bg-white px-3 text-[12px] font-semibold hover:border-panel-marca"
              >+ Componente</button>
            </div>

            <div
              v-for="(c, i) in editando.componentes" :key="i"
              class="mb-2 rounded-lg border border-panel-borde bg-white p-2.5 last:mb-0"
            >
              <div class="flex gap-2">
                <input
                  v-model.number="c.cantidad" type="number" min="1" step="1" aria-label="Cantidad"
                  class="w-16 shrink-0 rounded-lg border border-panel-borde px-2 py-2 text-center text-[13px] outline-none focus:border-panel-marca"
                />
                <input
                  v-model="c.nombre" type="text" maxlength="140" placeholder="Hamburguesa clásica" aria-label="Nombre del componente"
                  class="min-w-0 flex-1 rounded-lg border border-panel-borde px-3 py-2 text-[13px] outline-none focus:border-panel-marca"
                />
              </div>
              <textarea
                v-model="c.especificacion" rows="2" maxlength="500"
                placeholder="Pan brioche, carne de res 150 g, queso cheddar…" aria-label="Especificación"
                class="mt-2 w-full resize-y rounded-lg border border-panel-borde px-3 py-2 text-[13px] outline-none focus:border-panel-marca"
              ></textarea>
              <div class="mt-1 flex justify-end gap-1">
                <button
                  @click="moverComponente(i, -1)" :disabled="i === 0" aria-label="Subir"
                  class="grid size-11 cursor-pointer place-items-center rounded-lg text-panel-tinta/50 hover:bg-panel-alt disabled:cursor-default disabled:opacity-30"
                >↑</button>
                <button
                  @click="moverComponente(i, 1)" :disabled="i === editando.componentes.length - 1" aria-label="Bajar"
                  class="grid size-11 cursor-pointer place-items-center rounded-lg text-panel-tinta/50 hover:bg-panel-alt disabled:cursor-default disabled:opacity-30"
                >↓</button>
                <button
                  @click="quitarComponente(i)" aria-label="Quitar componente"
                  class="grid size-11 cursor-pointer place-items-center rounded-lg text-panel-tinta/45 hover:bg-alerta/10 hover:text-alerta"
                >×</button>
              </div>
            </div>
          </div>

          <!-- Vigencia -->
          <div class="mb-4 rounded-xl border border-panel-borde bg-panel-alt/35 p-3">
            <p class="mb-2 text-[12px] font-semibold text-panel-tinta/60">Cuándo vale</p>
            <div class="grid grid-cols-2 gap-2">
              <label class="text-[11.5px] text-panel-tinta/55">
                Desde
                <input
                  v-model="editando.vigente_desde" type="date"
                  class="mt-1 w-full rounded-lg border border-panel-borde bg-white px-2.5 py-2 text-[13px] text-panel-tinta outline-none focus:border-panel-marca"
                />
              </label>
              <label class="text-[11.5px] text-panel-tinta/55">
                Hasta (vacío = sin fin)
                <input
                  v-model="editando.vigente_hasta" type="date" :min="editando.vigente_desde"
                  class="mt-1 w-full rounded-lg border border-panel-borde bg-white px-2.5 py-2 text-[13px] text-panel-tinta outline-none focus:border-panel-marca"
                />
              </label>
            </div>

            <p class="mt-3 mb-1.5 text-[11.5px] text-panel-tinta/55">Días</p>
            <div class="grid grid-cols-4 gap-1 sm:grid-cols-7">
              <button
                v-for="(dia, indice) in DIAS_SEMANA" :key="dia"
                @click="alternarDia(indice)" :aria-pressed="editando.dias_semana.includes(indice)"
                class="min-h-11 cursor-pointer rounded-lg border text-[12px] font-semibold"
                :class="editando.dias_semana.includes(indice)
                  ? 'border-panel-marca bg-panel-marca text-white'
                  : 'border-panel-borde bg-white text-panel-tinta/50'"
              >{{ dia }}</button>
            </div>

            <p class="mt-3 mb-1.5 text-[11.5px] text-panel-tinta/55">Franja horaria (vacía = todo el día)</p>
            <div class="flex items-center gap-2">
              <input
                v-model="editando.hora_inicio" type="time" aria-label="Hora de inicio"
                class="min-w-0 flex-1 rounded-lg border border-panel-borde bg-white px-2.5 py-2 text-[13px] outline-none focus:border-panel-marca"
              />
              <span class="text-[12px] text-panel-tinta/50">a</span>
              <input
                v-model="editando.hora_fin" type="time" aria-label="Hora de fin"
                class="min-w-0 flex-1 rounded-lg border border-panel-borde bg-white px-2.5 py-2 text-[13px] outline-none focus:border-panel-marca"
              />
              <button
                v-if="editando.hora_inicio || editando.hora_fin"
                @click="editando.hora_inicio = ''; editando.hora_fin = ''"
                class="min-h-11 shrink-0 cursor-pointer rounded-lg px-2 text-[12px] font-semibold text-panel-tinta/55"
              >Todo el día</button>
            </div>
            <p
              v-if="editando.hora_inicio && editando.hora_fin && editando.hora_fin <= editando.hora_inicio"
              class="mt-1.5 text-[11.5px] text-panel-tinta/55"
            >Cruza la medianoche: la madrugada cuenta como parte del día en que empezó.</p>

            <label class="mt-3 flex cursor-pointer items-center gap-2 text-[13px] font-semibold">
              <span class="-m-2.5 grid min-h-11 min-w-11 place-items-center p-2.5"><input v-model="editando.activa" type="checkbox" class="size-4 cursor-pointer accent-panel-marca" /></span>
              Encendida
            </label>
          </div>
        </template>

        <label class="mb-1 text-[12px] font-semibold text-panel-tinta/60">Descripción</label>
        <textarea
          v-model="editando.descripcion" rows="2" maxlength="500"
          class="mb-3 resize-y rounded-lg border border-panel-borde px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
        ></textarea>

        <label class="mb-1 text-[12px] font-semibold text-panel-tinta/60">Alérgenos (texto libre)</label>
        <input
          v-model="editando.alergenos" type="text" maxlength="200"
          placeholder="lácteos, gluten…"
          class="mb-3 rounded-lg border border-panel-borde px-3 py-2.5 text-sm outline-none focus:border-panel-marca"
        />

        <div class="mb-4 rounded-xl border border-panel-borde bg-panel-alt/35 p-3">
          <div class="mb-2 flex items-center justify-between gap-3">
            <div>
              <label class="block text-[12px] font-semibold text-panel-tinta/60">Métricas del plato</label>
              <p class="mt-0.5 text-[11px] text-panel-tinta/50">Puedes usar proteína, gramos, calorías, porciones o cualquier métrica propia.</p>
            </div>
            <button
              @click="agregarEstadistica"
              class="shrink-0 cursor-pointer rounded-lg border border-panel-borde px-3 py-1.5 text-[12px] font-semibold hover:border-panel-marca"
            >+ Métrica</button>
          </div>
          <div v-if="editando.estadisticas.length" class="space-y-2">
            <div v-for="(dato, indice) in editando.estadisticas" :key="indice" class="flex gap-2">
              <input
                v-model="dato[0]" type="text" maxlength="30" placeholder="380 g"
                class="min-w-0 flex-1 rounded-lg border border-panel-borde bg-white px-3 py-2 text-[13px] outline-none focus:border-panel-marca"
              />
              <input
                v-model="dato[1]" type="text" maxlength="30" placeholder="Proteína"
                class="min-w-0 flex-1 rounded-lg border border-panel-borde bg-white px-3 py-2 text-[13px] outline-none focus:border-panel-marca"
              />
              <button
                @click="quitarEstadistica(indice)" title="Quitar métrica"
                class="grid size-11 shrink-0 cursor-pointer place-items-center rounded-lg text-panel-tinta/45 hover:bg-red-50 hover:text-red-600"
              >×</button>
            </div>
          </div>
          <p v-else class="text-[12px] text-panel-tinta/45">Este plato no tiene métricas adicionales.</p>
        </div>

        <label class="mb-1 text-[12px] font-semibold text-panel-tinta/60">Foto</label>
        <input
          type="file" accept="image/*"
          @change="fotoNueva = $event.target.files[0] || null"
          class="mb-4 cursor-pointer text-[13px] file:mr-3 file:cursor-pointer file:rounded-lg file:border-0 file:bg-panel-alt file:px-3 file:py-2 file:text-[12px] file:font-semibold"
        />

        <label class="mb-1 text-[12px] font-semibold text-panel-tinta/60">
          Observaciones solo de {{ editando.tipo === "promocion" ? "esta promoción" : "este plato" }}
        </label>
        <p class="mb-2 text-[11.5px] text-panel-tinta/50">
          Se suman a las generales y a las de su sección (botón «Observaciones» en la
          categoría). Un plato nuevo hay que guardarlo antes de poder agregarle las suyas.
        </p>
        <div v-if="editando.id" class="mb-3">
          <div v-if="observacionesPlato.length" class="mb-2 flex flex-wrap gap-1.5">
            <span
              v-for="o in observacionesPlato" :key="o.id"
              class="flex items-center gap-1 rounded-full border border-panel-borde py-1 pr-1 pl-3 text-[12.5px] font-semibold"
            >
              {{ o.texto }}
              <button
                @click="quitarObservacionPlato(o)" title="Quitar"
                class="-my-3 -mr-1 flex min-h-11 min-w-11 cursor-pointer items-center justify-center rounded-full text-panel-tinta/40 hover:bg-red-50 hover:text-red-600"
              >×</button>
            </span>
          </div>
          <div class="flex gap-2">
            <input
              v-model="nuevaObservacion" type="text" maxlength="60"
              placeholder="término medio, sin hielo…"
              @keyup.enter.prevent="agregarObservacionPlato"
              class="min-h-11 flex-1 rounded-lg border border-panel-borde px-3 text-[13px] outline-none focus:border-panel-marca"
            />
            <button
              @click="agregarObservacionPlato"
              class="min-h-11 cursor-pointer rounded-lg border border-panel-borde px-4 text-[12.5px] font-semibold hover:border-panel-marca"
            >Agregar</button>
          </div>
        </div>
        <p v-else class="mb-3 text-[12.5px] text-panel-tinta/40">
          Disponible después de guardar.
        </p>

        <label class="mb-4 flex cursor-pointer items-center gap-2 text-[13px] font-semibold">
          <span class="-m-2.5 grid min-h-11 min-w-11 place-items-center p-2.5"><input v-model="editando.disponible" type="checkbox" class="size-4 cursor-pointer accent-panel-marca" /></span>
          Disponible
        </label>

        <div class="flex gap-2">
          <button
            @click="editando = null"
            class="min-h-11 flex-1 cursor-pointer rounded-lg border border-panel-borde text-[13px] font-semibold"
          >Cancelar</button>
          <button
            @click="guardar"
            class="min-h-11 flex-1 cursor-pointer rounded-lg bg-panel-marca text-[13px] font-semibold text-white"
          >Guardar</button>
        </div>
      </div>
    </div>
  </MarcoInterno>
</template>
