import cliente from "./cliente";

/**
 * La cuenta (SPEC-013): lo que una mesa debe, y el registro del cobro.
 * Distinta del pedido — el pedido avanza por la cocina, la cuenta por el
 * dinero.
 */

/** Por defecto solo las abiertas: lo servido y no cobrado. */
export function listarCuentas(estado = "abierta") {
  return cliente.get("/cuentas/", { params: { estado } }).then((r) => r.data);
}

export function obtenerCuenta(id) {
  return cliente.get(`/cuentas/${id}/`).then((r) => r.data);
}

/** Cobrar. `medioPago` es obligatorio: sin él la caja no cuadra. */
/**
 * Cobrar. `liberarMesa` (SPEC-013, revisado 2026-09-16): el cliente pagó para
 * irse y la mesa queda libre. En falso es pago anticipado: sigue sentado.
 *
 * `recibidoEfectivo` (SPEC-025): solo tiene efecto si se cobra en un medio de
 * tipo Efectivo. El servidor calcula y devuelve el vuelto.
 */
export function cerrarCuenta(id, medioPago, aplicaPropina = true, liberarMesa = false, recibidoEfectivo = null) {
  return cliente
    .post(`/cuentas/${id}/cerrar/`, {
      medio_pago: medioPago, aplica_propina: aplicaPropina, liberar_mesa: liberarMesa,
      recibido_efectivo: recibidoEfectivo,
    })
    .then((r) => r.data);
}

/** Anular exige motivo, siempre (SPEC-008). */
export function anularCuenta(id, motivo) {
  return cliente.post(`/cuentas/${id}/anular/`, { motivo }).then((r) => r.data);
}

/**
 * Los medios de pago viven en `api/caja.js` como `listarCajas()`: medio de
 * pago y caja son la MISMA entidad (SPEC-014), vista en dos momentos.
 *
 * Aqui habia una copia que apuntaba a `/medios-pago/`, la ruta vieja de
 * antes del renombrado a `Caja`. Al cambiar el backend la copia quedo
 * pidiendo una URL inexistente: la lista llegaba vacia y la pantalla de
 * cobro no mostraba ningun medio para elegir. Dos clientes para el mismo
 * recurso terminan desincronizandose — por eso ahora hay uno solo.
 */

/* --- Historial de ventas (SPEC-015) -------------------------------------- */

/**
 * Las ventas: cuentas que se cobraron. Nada que ver con la DIAN — es el
 * historial interno del restaurante.
 *
 * Devuelve `{ totales, por_medio_pago, ventas }`. Los totales son del rango
 * filtrado COMPLETO y excluyen las anuladas: una venta que se devolvio no se
 * vendio. Y `vendido` NO incluye la propina, que va aparte.
 */
export function listarVentas(filtros = {}) {
  const {
    desde, hasta, medioPago, tipo, mesa, cobradoPor,
    montoMin, montoMax, horaDesde, horaHasta, orden, incluirAnuladas,
  } = filtros;
  const params = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  if (medioPago) params.medio_pago = medioPago;
  if (tipo) params.tipo = tipo;
  if (mesa) params.mesa = mesa;
  if (cobradoPor) params.cobrado_por = cobradoPor;
  if (montoMin) params.monto_min = montoMin;
  if (montoMax) params.monto_max = montoMax;
  // La hora 0 es valida (medianoche), asi que no vale el truco de `if (x)`.
  if (horaDesde !== "" && horaDesde != null) params.hora_desde = horaDesde;
  if (horaHasta !== "" && horaHasta != null) params.hora_hasta = horaHasta;
  if (orden) params.orden = orden;
  if (incluirAnuladas) params.anuladas = 1;
  return cliente.get("/ventas/", { params }).then((r) => r.data);
}

function paramsVentas(filtros = {}) {
  const {
    desde, hasta, medioPago, tipo, mesa, cobradoPor,
    montoMin, montoMax, horaDesde, horaHasta, orden, incluirAnuladas,
    agrupar,
  } = filtros;
  const params = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  if (medioPago) params.medio_pago = medioPago;
  if (tipo) params.tipo = tipo;
  if (mesa) params.mesa = mesa;
  if (cobradoPor) params.cobrado_por = cobradoPor;
  if (montoMin) params.monto_min = montoMin;
  if (montoMax) params.monto_max = montoMax;
  if (horaDesde !== "" && horaDesde != null) params.hora_desde = horaDesde;
  if (horaHasta !== "" && horaHasta != null) params.hora_hasta = horaHasta;
  if (orden) params.orden = orden;
  if (incluirAnuladas) params.anuladas = 1;
  if (agrupar) params.agrupar = agrupar;
  return params;
}

export function obtenerTiquete(id) {
  return cliente.get(`/ventas/${id}/tiquete/`).then((r) => r.data);
}

export function obtenerTiquetes(ids) {
  return cliente.post("/ventas/tiquetes/", { ids }).then((r) => r.data);
}

export function obtenerConsolidado(filtros = {}) {
  return cliente.get("/ventas/consolidado/", { params: paramsVentas(filtros) }).then((r) => r.data);
}

export function exportarVentas(filtros = {}) {
  return cliente.get("/ventas/exportar/", {
    params: paramsVentas(filtros), responseType: "blob",
  });
}
