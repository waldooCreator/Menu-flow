/**
 * Utilidades de las promociones (SPEC-023) que comparten el menú del cliente,
 * el Camino B del mesero y el panel.
 *
 * Aquí NO se decide si una promo vale: eso lo calcula el servidor y llega en
 * `estado_promocion`. Esto solo la describe en palabras.
 */
import { localeRestaurante } from "./tema";

export const esPromocion = (plato) => plato?.tipo === "promocion";

export const DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

export const ESTADOS_PROMOCION = {
  vigente: { texto: "Vigente", clase: "bg-emerald-100 text-emerald-800" },
  programada: { texto: "Programada", clase: "bg-sky-100 text-sky-800" },
  fuera_de_horario: { texto: "Fuera de horario", clase: "bg-amber-100 text-amber-800" },
  vencida: { texto: "Vencida", clase: "bg-panel-alt text-panel-tinta/60" },
  apagada: { texto: "Apagada", clase: "bg-panel-alt text-panel-tinta/60" },
  agotada: { texto: "Agotada", clase: "bg-alerta/10 text-alerta" },
};

/** "2× Hamburguesa clásica · Gaseosa 400 ml": lo que cabe en una tarjeta. */
export function resumenComponentes(plato) {
  return (plato?.componentes ?? [])
    .map((c) => (c.cantidad > 1 ? `${c.cantidad}× ${c.nombre}` : c.nombre))
    .join(" · ");
}

function fechaLocal(isoFecha) {
  // "2026-09-20" como fecha local: `new Date("2026-09-20")` la leería en UTC
  // y en Colombia caería el día anterior.
  const [anio, mes, dia] = isoFecha.split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

function horaLegible(isoHora) {
  const [h, m] = isoHora.split(":").map(Number);
  return new Intl.DateTimeFormat(localeRestaurante(), { hour: "numeric", minute: "2-digit" })
    .format(new Date(2000, 0, 1, h, m));
}

/**
 * Hasta cuándo vale, SOLO si termina pronto: una promo sin fin, o que acaba
 * en dos meses, no necesita decirlo y el texto sobraría.
 *
 * - Con franja horaria: "hasta las 3:00 p. m.", que es lo que le sirve a quien
 *   está mirando el menú hoy.
 * - Con fecha de fin en las próximas dos semanas: "hasta el domingo 20 sep."
 */
export function textoVigencia(plato, prefijo) {
  if (!esPromocion(plato)) return "";
  if (plato.hora_fin) return `${prefijo} ${horaLegible(plato.hora_fin)}`;
  if (!plato.vigente_hasta) return "";
  const fin = fechaLocal(plato.vigente_hasta);
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const dias = Math.round((fin - hoy) / 86400000);
  if (dias < 0 || dias > 14) return "";
  const formato = new Intl.DateTimeFormat(localeRestaurante(), {
    weekday: "long", day: "numeric", month: "short",
  });
  return `${prefijo} ${formato.format(fin)}`;
}

/** "Vie, Sáb, Dom · 12:00 a 15:00": la vigencia en una línea, para el panel. */
export function resumenVigencia(plato) {
  const dias = plato.dias_semana ?? [];
  const textoDias = dias.length === 7 ? "Todos los días" : dias.map((d) => DIAS_SEMANA[d]).join(", ");
  const franja = plato.hora_inicio && plato.hora_fin
    ? ` · ${plato.hora_inicio.slice(0, 5)} a ${plato.hora_fin.slice(0, 5)}`
    : "";
  const hasta = plato.vigente_hasta ? ` · hasta ${plato.vigente_hasta}` : " · sin fecha de fin";
  return `${textoDias}${franja}${hasta}`;
}
