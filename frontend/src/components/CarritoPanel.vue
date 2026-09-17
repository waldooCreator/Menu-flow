<script setup>
/**
 * Vista previa del pedido antes de generar el QR (SPEC-002/003).
 * Port del modal de Fase 0: pantalla completa en móvil, panel centrado en
 * escritorio, con etiquetas rápidas de observación y comentario general.
 */
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useCarritoStore } from "../stores/carrito";
import { firmarPedido } from "../api/pedidos";
import { formatearMoneda, nombreRestaurante } from "../lib/tema";
import QRCode from "qrcode";

const props = defineProps({
  observacionesRapidas: { type: Array, default: () => [] },
  // La configuración pública del restaurante: nombre y número de WhatsApp
  // vienen de la base (SPEC-007), nunca escritos a mano.
  config: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["cerrar"]);

const carrito = useCarritoStore();
const moneda = { format: formatearMoneda };

/**
 * Datos de entrega del domicilio (SPEC-002, revisado 2026-08-26).
 *
 * Antes un pedido "a distancia" se anclaba en una mesa virtual llamada
 * "Domicilio", porque `Pedido.mesa` era obligatorio. Ya no: el domicilio
 * va SIN mesa, y por eso no puede ensuciar el salón (SPEC-012).
 *
 * Los datos se guardan en el navegador del propio cliente para que la
 * próxima vez el formulario venga lleno. No se envían a ningún lado salvo
 * dentro del mensaje de WhatsApp que él mismo manda.
 *
 * La DIRECCIÓN no viaja en el QR a propósito: va en el mensaje, que es
 * donde la persona del restaurante la va a leer de todos modos, y así no
 * gasta capacidad del código.
 */
const CLAVE_CACHE_ENTREGA = "datos-entrega";

function leerDatosEntrega() {
  try {
    const crudo = localStorage.getItem(CLAVE_CACHE_ENTREGA);
    if (!crudo) return { nombre: "", telefono: "", direccion: "" };
    const { nombre = "", telefono = "", direccion = "" } = JSON.parse(crudo);
    return { nombre, telefono, direccion };
  } catch {
    // Ventana privada, almacenamiento bloqueado o JSON corrupto: el
    // formulario arranca vacío. Nunca debe tumbar el carrito.
    return { nombre: "", telefono: "", direccion: "" };
  }
}

function guardarDatosEntrega(datos) {
  try {
    localStorage.setItem(CLAVE_CACHE_ENTREGA, JSON.stringify(datos));
  } catch {
    // Si no se puede guardar solo se pierde la comodidad de autocompletar.
  }
}

const generando = ref(false);
const error = ref(null);
const qrDataUrl = ref(null);
const qrArchivo = ref(null); // el mismo File que se ofrece a compartir
const textoQr = ref(null);
const comentario = ref("");
const modo = ref(null); // "lugar" | "distancia" — cuál botón se pulsó
// El domicilio pasa primero por el formulario; "en el lugar" no.
const pidiendoDatos = ref(false);
const entrega = ref(leerDatosEntrega());
const errorEntrega = ref(null);
const compartiendo = ref(false);
const avisoCompartir = ref(null);
const tieneAgotados = computed(() => carrito.itemsAgotados.length > 0);
const nombresAgotados = computed(() => carrito.nombresAgotados.join(", "));
// Si el navegador puede de verdad compartir un archivo. Antes se mostraba
// el botón sin comprobarlo, y en un contexto no seguro (http:// que no sea
// localhost — el caso real de probar por el hotspot del teléfono) el Web
// Share API existe pero SIEMPRE rechaza compartir archivos: el botón
// prometía algo que nunca podía cumplir. Se comprueba con el archivo real,
// apenas se genera, no con una prueba aparte que podría responder distinto.
const compartirDisponible = ref(false);

/**
 * "A distancia" no genera el QR de una: primero pide los datos de entrega.
 * "Estoy en el lugar" sigue siendo un solo toque, como antes.
 */
function elegirModo(modoElegido) {
  modo.value = modoElegido;
  if (modoElegido === "distancia") {
    pidiendoDatos.value = true;
    return;
  }
  generarQr(modoElegido);
}

function confirmarDatosEntrega() {
  const nombre = entrega.value.nombre.trim();
  const telefono = entrega.value.telefono.trim();
  const direccion = entrega.value.direccion.trim();
  if (!nombre || !direccion || !telefono) {
    errorEntrega.value = "Necesitamos tu nombre, teléfono y dirección exacta para llevarte el pedido.";
    return;
  }
  // Se avisa, NO se bloquea: exigir 10 digitos rechazaria fijos y extranjeros,
  // y dejar a alguien sin poder pedir por una validacion nuestra es peor que
  // guardar un numero raro (SPEC-019).
  const digitos = telefono.replace(/\D/g, "");
  if (digitos.length < 7) {
    errorEntrega.value = "Ese teléfono se ve muy corto. Revísalo, por favor.";
    return;
  }
  entrega.value = { nombre, telefono, direccion };
  guardarDatosEntrega(entrega.value);
  errorEntrega.value = null;
  pidiendoDatos.value = false;
  generarQr("distancia");
}

async function generarQr(modoElegido) {
  error.value = null;
  generando.value = true;
  modo.value = modoElegido;
  try {
    const esDomicilio = modoElegido === "distancia";
    // Un domicilio va sin mesa. El nombre sí viaja: el campo ya existía en
    // el QR, así que no cuesta nada y le da al mesero a quién pertenece.
    // Telefono y direccion viajan DENTRO del QR firmado desde SPEC-019: asi
    // el mesero no tiene que teclear nada al confirmar, y el cliente los
    // escribe una sola vez en su vida (su navegador los recuerda).
    const texto = await firmarPedido(
      esDomicilio ? "" : carrito.mesaCodigo,
      esDomicilio ? entrega.value.nombre : carrito.nombreCliente,
      carrito.aItemsParaFirmar(),
      esDomicilio,
      esDomicilio ? entrega.value.telefono : "",
      esDomicilio ? entrega.value.direccion : "",
    );
    textoQr.value = texto;
    qrDataUrl.value = await QRCode.toDataURL(texto, { errorCorrectionLevel: "M", scale: 8 });

    const blob = await (await fetch(qrDataUrl.value)).blob();
    qrArchivo.value = new File([blob], "pedido.png", { type: "image/png" });
    try {
      compartirDisponible.value = !!navigator.canShare?.({ files: [qrArchivo.value] });
    } catch {
      compartirDisponible.value = false;
    }
  } catch (e) {
    error.value = e.response?.data?.detalle || "No se pudo generar el QR.";
  } finally {
    generando.value = false;
  }
}

/**
 * `whatsapp-mensaje` es una PLANTILLA, no una frase fija (SPEC-007): se
 * rellena con lo que el cliente escribió en el formulario.
 *
 * Una variable desconocida se deja tal cual, sin borrarla: si el
 * administrador escribe `{telefono}` (que no existe), lo ve en el mensaje y
 * lo corrige. Borrarla en silencio dejaría una frase rota sin pista de por
 * qué.
 */
function rellenarPlantilla(plantilla, valores) {
  return plantilla.replace(/\{(\w+)\}/g, (original, clave) =>
    Object.prototype.hasOwnProperty.call(valores, clave) ? valores[clave] : original
  );
}

const mensajeWhatsApp = computed(() => {
  const plantilla =
    props.config["whatsapp-mensaje"] ||
    `Hola, quiero confirmar mi pedido a domicilio en ${nombreRestaurante() || "el restaurante"} 👋`;
  return rellenarPlantilla(plantilla, {
    nombre: entrega.value.nombre,
    direccion: entrega.value.direccion,
  });
});

/**
 * Enlace wa.me al número del restaurante (parámetro `numero-whatsapp`):
 * abre el chat con el texto ya cargado. La API de enlace de WhatsApp solo
 * admite TEXTO — la imagen la adjunta el cliente a mano.
 */
const enlaceWhatsApp = computed(() => {
  const numero = props.config["numero-whatsapp"];
  if (!numero) return null;
  // Se codifica aquí, sobre el mensaje ya relleno — nunca sobre la plantilla.
  return `https://wa.me/${numero}?text=${encodeURIComponent(mensajeWhatsApp.value)}`;
});

/**
 * Descarga el QR como imagen para adjuntarlo a mano en WhatsApp: la API de
 * enlace de WhatsApp solo admite texto, así que la imagen la pega el
 * cliente. En Android funciona directo; en iPhone Safari a veces ignora la
 * descarga, y por eso además se muestra la instrucción de mantener
 * presionada la imagen.
 */
function descargarQr() {
  const enlace = document.createElement("a");
  enlace.href = qrDataUrl.value;
  enlace.download = `pedido-${nombreRestaurante() || "restaurante"}.png`;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
}

/**
 * Atajo: el panel nativo para compartir del teléfono adjunta la imagen solo.
 * No existe forma de enviarla automáticamente a un número fijo — eso exigiría
 * la API de WhatsApp Business (integración pagada y verificada por Meta).
 * Solo se ofrece si `compartirDisponible` dio verdadero.
 */
async function compartirPorWhatsApp() {
  avisoCompartir.value = null;
  compartiendo.value = true;
  try {
    const texto = mensajeWhatsApp.value;

    if (compartirDisponible.value) {
      await navigator.share({
        files: [qrArchivo.value],
        text: texto,
        title: `Pedido ${nombreRestaurante() || "restaurante"}`,
      });
    } else {
      avisoCompartir.value =
        "Tu navegador no permite adjuntar la imagen automáticamente. " +
        "Guarda esta captura y envíala por WhatsApp manualmente.";
    }
  } catch (e) {
    // El usuario cerró el panel de compartir sin elegir nada: no es un error.
    if (e?.name !== "AbortError") {
      avisoCompartir.value = "No se pudo abrir el panel para compartir.";
    }
  } finally {
    compartiendo.value = false;
  }
}

// El scroll de fondo se bloquea mientras el panel está abierto
onMounted(() => { document.body.style.overflow = "hidden"; });
onUnmounted(() => { document.body.style.overflow = ""; });
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-end justify-center bg-tinta/55 backdrop-blur-sm sm:items-center"
    @click.self="emit('cerrar')"
  >
    <div class="flex max-h-[88dvh] w-full flex-col overflow-hidden rounded-t-[26px] bg-lienzo sm:max-w-[760px] sm:rounded-[26px]">

      <!-- Cabecera -->
      <header class="flex shrink-0 items-start justify-between gap-4 border-b border-marca/15 px-5 pt-5 pb-4 sm:px-7 sm:pt-6.5 sm:pb-5">
        <div>
          <p v-if="carrito.mesaNombre" class="mb-1.5 text-[11px] font-semibold tracking-[0.16em] text-marca/60 uppercase">
            {{ carrito.mesaNombre }}
          </p>
          <h2 class="font-display text-[28px] leading-none font-light text-marca sm:text-[34px]">Tu pedido</h2>
        </div>
        <button
          @click="emit('cerrar')"
          aria-label="Cerrar"
          class="grid size-11 shrink-0 cursor-pointer place-items-center rounded-full border border-marca/15 text-marca transition-colors hover:bg-marca hover:text-lienzo"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none" />
          </svg>
        </button>
      </header>

      <!-- Cuerpo desplazable -->
      <div class="flex-1 overflow-y-auto overscroll-contain px-5 pt-2 pb-5 sm:px-7 sm:pb-6">

        <!-- QR generado -->
        <div v-if="qrDataUrl" class="py-6 text-center">
          <img :src="qrDataUrl" alt="QR del pedido" class="mx-auto size-56 rounded-foto" />

          <p v-if="modo === 'lugar'" class="mt-5 text-base text-marca">
            Muéstrale esto a tu mesero para que lo escanee.
          </p>
          <!-- Domicilio: dos pasos numerados. WhatsApp solo admite texto en
               su enlace, así que la imagen la adjunta el cliente — por eso
               el orden importa y se muestra como una secuencia, no como dos
               botones sueltos entre los que hay que adivinar. -->
          <template v-else>
            <p class="mx-auto mt-5 max-w-80 text-[15px] leading-snug text-marca">
              Guarda el código y envíalo por WhatsApp. Tus datos ya van escritos en el mensaje.
            </p>

            <div class="mx-auto mt-5 grid max-w-80 gap-2.5">
              <button
                @click="descargarQr"
                class="flex min-h-13 items-center justify-center gap-2.5 rounded-full border-2 border-marca px-6 text-sm font-semibold tracking-[0.06em] text-marca uppercase transition-transform active:scale-[0.98]"
              >
                <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <path d="M12 3v12m0 0l-4.5-4.5M12 15l4.5-4.5" stroke-linecap="round" stroke-linejoin="round" />
                  <path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke-linecap="round" />
                </svg>
                1 · Descargar el código
              </button>

              <a
                v-if="enlaceWhatsApp"
                :href="enlaceWhatsApp" target="_blank" rel="noopener"
                class="flex min-h-13 items-center justify-center gap-2.5 rounded-full bg-marca px-6 text-sm font-semibold tracking-[0.06em] text-lienzo uppercase transition-transform active:scale-[0.98]"
              >
                <svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor" aria-hidden="true">
                  <path d="M12 2a10 10 0 00-8.5 15.2L2 22l4.9-1.5A10 10 0 1012 2zm5.4 14.2c-.2.6-1.3 1.2-1.8 1.3-.5.1-1 .1-3.3-.7-2.8-1.1-4.6-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.9 0-1.4.7-2 1-2.3.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5.2.5.7 1.8.8 1.9.1.1.1.3 0 .5-.1.2-.2.3-.3.5-.2.2-.3.3-.1.6.2.3.9 1.5 2 2.4 1.4 1.2 2.5 1.6 2.8 1.7.3.1.5.1.7-.1.2-.2.8-.9 1-1.2.2-.3.4-.2.7-.1.3.1 1.8.9 2.1 1 .3.1.5.2.6.3.1.2.1.9-.1 1.5z" />
                </svg>
                2 · Enviar por WhatsApp
              </a>

              <!-- El panel nativo adjunta la imagen solo, pero únicamente
                   existe sobre HTTPS. Se ofrece como atajo cuando el
                   navegador de verdad puede cumplirlo — nunca como el
                   camino principal, que debe funcionar siempre. -->
              <button
                v-if="compartirDisponible"
                @click="compartirPorWhatsApp" :disabled="compartiendo"
                class="min-h-11 cursor-pointer text-[13px] font-semibold text-marca underline-offset-2 hover:underline disabled:opacity-50"
              >
                {{ compartiendo ? "Abriendo…" : "O compartir el código directamente" }}
              </button>
            </div>

            <p class="mx-auto mt-3 max-w-80 text-[12.5px] leading-snug text-marca/60">
              Si la descarga no funciona en tu teléfono, mantén presionada la imagen de arriba
              para guardarla. Después adjúntala en el chat.
            </p>

            <p v-if="avisoCompartir" class="mt-3 text-[13px] text-marca/70">{{ avisoCompartir }}</p>
          </template>

          <p class="mt-2 text-[11px] text-marca/50">{{ textoQr.length }} caracteres codificados</p>
        </div>

        <!-- Formulario de entrega: va ANTES del QR (SPEC-002). Sin nombre y
             dirección no hay domicilio posible, así que ambos son
             obligatorios. Quedan guardados en este teléfono para la próxima. -->
        <div v-else-if="pidiendoDatos" class="py-6">
          <h3 class="font-display text-[26px] leading-none font-light text-marca">¿A dónde lo llevamos?</h3>
          <p class="mt-2 text-[14px] leading-snug text-marca/65">
            Estos datos van escritos en el mensaje de WhatsApp. Los guardamos en tu teléfono
            para que la próxima vez no los tengas que escribir.
          </p>

          <label for="entrega-nombre" class="mt-6 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
            Nombre de quien recibe
          </label>
          <input
            id="entrega-nombre" v-model="entrega.nombre" type="text" maxlength="80"
            autocomplete="name" placeholder="Tu nombre"
            class="w-full rounded-[14px] border border-marca/15 bg-white px-4 py-3.5 text-[15px] text-tinta outline-none placeholder:text-marca/35 focus:border-marca"
          />

          <label for="entrega-telefono" class="mt-5 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
            Teléfono
          </label>
          <input
            id="entrega-telefono" v-model="entrega.telefono" type="tel" maxlength="20"
            autocomplete="tel" inputmode="tel" placeholder="320 123 4567"
            class="w-full rounded-[14px] border border-marca/15 bg-white px-4 py-3.5 text-[15px] text-tinta outline-none placeholder:text-marca/35 focus:border-marca"
          />
          <p class="mt-1.5 text-[12px] leading-snug text-tinta/50">
            Para llamarte si no encontramos la dirección.
          </p>

          <label for="entrega-direccion" class="mt-5 mb-2 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
            Dirección exacta
          </label>
          <textarea
            id="entrega-direccion" v-model="entrega.direccion" maxlength="200" rows="3"
            autocomplete="street-address"
            placeholder="Calle, número, barrio, apartamento, punto de referencia…"
            class="w-full resize-y rounded-[14px] border border-marca/15 bg-white px-4 py-3.5 text-[15px] leading-relaxed text-tinta outline-none placeholder:text-marca/35 focus:border-marca"
          ></textarea>

          <p v-if="errorEntrega" class="mt-3 text-[13px] font-semibold text-alerta">{{ errorEntrega }}</p>

          <!-- Desde SPEC-019 estos datos SI se guardan en el servidor del
               restaurante. La Ley 1581 exige informarlo al titular; antes no
               hacia falta porque no salian de este navegador. -->
          <p class="mt-4 text-[11.5px] leading-snug text-tinta/45">
            Guardamos tu nombre, teléfono y dirección para que no tengas que escribirlos
            la próxima vez. Puedes pedir que los borremos cuando quieras.
          </p>

          <div class="mt-6 grid gap-2.5 sm:grid-cols-2">
            <button
              @click="pidiendoDatos = false; modo = null"
              class="min-h-13 cursor-pointer rounded-full border border-marca/20 text-[13px] font-semibold tracking-[0.06em] text-marca uppercase transition-colors hover:border-marca"
            >Volver</button>
            <button
              @click="confirmarDatosEntrega"
              class="min-h-13 cursor-pointer rounded-full bg-marca text-[13px] font-semibold tracking-[0.06em] text-lienzo uppercase transition-transform active:scale-[0.98]"
            >Generar el código</button>
          </div>
        </div>

        <template v-else>
          <div v-if="carrito.items.length === 0" class="py-14 text-center text-marca">
            <b class="mb-2 block font-display text-2xl font-light">Tu pedido está vacío</b>
            <span class="text-[15px] opacity-65">Agrega platos del menú con el botón +</span>
          </div>

          <ul v-else>
            <li
              v-for="item in carrito.items"
              :key="item.plato.id"
              class="grid grid-cols-[64px_1fr] gap-3.5 border-b border-marca/15 py-4.5 last:border-b-0 sm:grid-cols-[76px_1fr] sm:gap-4 sm:py-5.5"
              :class="{ 'bg-alerta/5': !item.plato.disponible }"
            >
              <img
                v-if="item.plato.foto" :src="item.plato.foto" :alt="item.plato.nombre"
                class="size-16 rounded-[14px] object-cover sm:size-19"
              />
              <div v-else class="grid size-16 place-items-center rounded-[14px] bg-marca-suave font-display text-2xl text-marca sm:size-19">
                {{ item.plato.nombre.charAt(0) }}
              </div>

              <div class="min-w-0">
                <div class="flex items-start justify-between gap-3">
                  <h3 class="text-[15px] leading-tight font-medium tracking-[0.03em] uppercase sm:text-base">
                    {{ item.plato.nombre }}
                  </h3>
                  <span class="shrink-0 text-[15px] font-medium whitespace-nowrap text-marca">
                    {{ moneda.format(item.plato.precio * item.cantidad) }}
                  </span>
                </div>

                <!-- Etiquetas rápidas: dan datos limpios a las estaciones -->
                <div class="mt-3 flex flex-wrap gap-1.5">
                  <button
                    v-for="obs in (item.plato.observaciones ?? observacionesRapidas)" :key="obs.id"
                    @click="carrito.alternarObservacion(item.plato.id, obs.texto)"
                    class="cursor-pointer rounded-full border px-3 py-2 text-[11px] font-semibold tracking-[0.06em] uppercase transition-colors"
                    :class="item.observaciones.includes(obs.texto)
                      ? 'border-marca bg-marca text-lienzo'
                      : 'border-marca/15 text-marca hover:border-marca'"
                  >{{ obs.texto }}</button>
                </div>

                <input
                  v-model="item.nota" type="text" maxlength="80"
                  placeholder="Otra indicación para este plato…"
                  class="mt-2.5 w-full border-b border-marca/15 bg-transparent py-2 text-sm text-tinta outline-none placeholder:text-marca/40 focus:border-marca"
                />

                <div class="mt-3.5 inline-flex items-center gap-0.5 rounded-full border border-marca/15 p-0.5">
                  <button
                    @click="carrito.cambiarCantidad(item.plato.id, -1)"
                    aria-label="Quitar uno"
                    class="grid size-11.5 cursor-pointer place-items-center rounded-full text-[17px] font-semibold text-[#8A3B18] transition-colors hover:bg-marca-suave"
                  >−</button>
                  <span class="min-w-7.5 text-center text-[15px] font-semibold">{{ item.cantidad }}</span>
                  <button
                    @click="carrito.cambiarCantidad(item.plato.id, 1)"
                    aria-label="Agregar uno"
                    class="grid size-11.5 cursor-pointer place-items-center rounded-full text-[17px] font-semibold text-marca transition-colors hover:bg-marca-suave"
                  >+</button>
                </div>
              </div>
            </li>
          </ul>

          <p
            v-if="tieneAgotados"
            class="mt-4 rounded-xl bg-alerta/10 px-3.5 py-2.5 text-[13px] font-semibold text-alerta"
          >{{ nombresAgotados }} se agotó. Quita {{ nombresAgotados }} del pedido para generar el código.</p>

          <div v-if="carrito.items.length" class="mt-6.5 border-t border-marca/15 pt-6">
            <label for="comentario" class="mb-3 block text-[11px] font-semibold tracking-[0.14em] text-marca/65 uppercase">
              Comentario para la cocina
            </label>
            <textarea
              id="comentario" v-model="comentario" maxlength="200"
              placeholder="Alergias, preferencias, algo que debamos saber…"
              class="min-h-21 w-full resize-y rounded-[14px] border border-marca/15 bg-white px-4 py-3.5 text-[15px] leading-relaxed text-tinta outline-none placeholder:text-marca/40 focus:border-marca"
            ></textarea>
            <span class="mt-1.5 block text-right text-xs text-marca/55">{{ comentario.length }} / 200</span>
          </div>

          <p v-if="error" class="mt-4 text-sm text-alerta">{{ error }}</p>
        </template>
      </div>

      <!-- Pie fijo -->
      <footer
        v-if="!qrDataUrl && !pidiendoDatos && carrito.items.length"
        class="shrink-0 border-t border-marca/15 bg-lienzo px-5 pt-4 pb-[calc(1.125rem+env(safe-area-inset-bottom))] sm:px-7 sm:pt-5 sm:pb-[calc(1.375rem+env(safe-area-inset-bottom))]"
      >
        <div class="mb-4 flex items-baseline justify-between">
          <span class="text-xs font-semibold tracking-[0.14em] text-marca/65 uppercase">Total</span>
          <b class="text-[25px] font-medium text-marca sm:text-[28px]">{{ moneda.format(carrito.totalPrecio) }}</b>
        </div>

        <div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          <button
            @click="elegirModo('lugar')" :disabled="generando || tieneAgotados"
            class="flex min-h-14 cursor-pointer items-center justify-center gap-2.5 rounded-full bg-marca text-[13px] font-semibold tracking-[0.06em] text-lienzo uppercase transition-transform active:scale-[0.985] disabled:opacity-40"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
              <path d="M12 21s-7-6.1-7-11a7 7 0 0114 0c0 4.9-7 11-7 11z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round" />
              <circle cx="12" cy="10" r="2.4" stroke="currentColor" stroke-width="2" fill="none" />
            </svg>
            {{ generando && modo === "lugar" ? "Generando…" : "Estoy en el lugar" }}
          </button>

          <button
            @click="elegirModo('distancia')" :disabled="generando || tieneAgotados"
            class="flex min-h-14 cursor-pointer items-center justify-center gap-2.5 rounded-full border-2 border-marca text-[13px] font-semibold tracking-[0.06em] text-marca uppercase transition-transform active:scale-[0.985] disabled:opacity-40"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
              <path d="M3 7h11v9H3zM14 10h4l3 3v3h-7z" stroke="currentColor" stroke-width="2" fill="none" stroke-linejoin="round" />
              <circle cx="7" cy="18" r="1.6" stroke="currentColor" stroke-width="2" fill="none" />
              <circle cx="17" cy="18" r="1.6" stroke="currentColor" stroke-width="2" fill="none" />
            </svg>
            {{ generando && modo === "distancia" ? "Generando…" : "A distancia" }}
          </button>
        </div>

        <p class="mt-3 text-center text-[12.5px] leading-snug text-marca/65">
          En el lugar, tu mesero escanea el código. A distancia, lo envías por WhatsApp
          para confirmar tu domicilio.
        </p>
      </footer>
    </div>
  </div>
</template>
