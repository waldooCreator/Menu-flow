import cliente from "./cliente";

export function validarMesa(codigo) {
  return cliente.get(`/mesas/validar/${codigo}/`).then((r) => r.data);
}

/** Mesas activas — para que el mesero elija cuando el QR no trae mesa. */
export function listarMesas() {
  return cliente.get("/mesas/").then((r) => r.data);
}

/**
 * El salón (SPEC-012). Devuelve `{mesas, domicilios}`:
 *
 * - `mesas` — la rejilla de mesas físicas con su estado y el total de su cuenta
 * - `domicilios` — su propia zona, **sin tope**. Cada uno trae si ya está
 *   cobrado y si sigue pendiente de entregar, porque son cosas independientes
 */
export function listarSalon() {
  return cliente.get("/mesas/salon/").then((r) => r.data);
}


/**
 * Apartar, liberar o revertir (SPEC-012). Acepta cualquier estado válido y
 * el backend no valida transiciones: el mesero manda. Eso es justamente lo
 * que hace que "Revertir" sea esta misma llamada con el estado anterior.
 */
export function cambiarEstadoMesa(codigo, estado) {
  return cliente.post(`/mesas/${codigo}/estado/`, { estado }).then((r) => r.data);
}

/**
 * Público — arma y firma el QR. No crea nada en base de datos (SPEC-002).
 * `esDomicilio` marca el pedido a distancia: va sin mesa, y al confirmarlo
 * el sistema no la pide.
 */
export function firmarPedido(mesaCodigo, nombreCliente, items, esDomicilio = false,
                             telefono = "", direccion = "") {
  return cliente
    .post("/pedidos/firmar/", {
      mesa: mesaCodigo,
      cliente: nombreCliente,
      items,
      es_domicilio: esDomicilio,
      // Solo viajan en domicilios (SPEC-019): un QR de mesa pesa igual que antes.
      telefono,
      direccion,
    })
    .then((r) => r.data.texto);
}

/** Público — resuelve el QR para mostrarlo al mesero antes de confirmar. */
export function verificarPedido(texto) {
  return cliente.post("/pedidos/verificar/", { texto }).then((r) => r.data);
}

/**
 * Requiere sesión — solo aquí se crea el pedido de verdad (ADR-002).
 * `mesa` solo hace falta si el QR no la traía (el cliente no entró
 * escaneando el código de su mesa).
 */
export function confirmarPedido(texto, mesa = "", medioPago = null, costoEnvio = null) {
  // `medioPago` activa el atajo de "cobrar al finalizar" (SPEC-004): el
  // pedido entra a cocina y la cuenta se cierra en la misma llamada.
  // `costoEnvio` (SPEC-013/025): solo aplica a domicilios; el mesero lo
  // indica al confirmar el QR.
  return cliente
    .post("/pedidos/confirmar/", { texto, mesa, medio_pago: medioPago, costo_envio: costoEnvio })
    .then((r) => r.data);
}

/** Solo las del mesero autenticado (SPEC-006) — nunca las de otro. */
export function listarNotificaciones() {
  return cliente.get("/pedidos/notificaciones/").then((r) => r.data);
}

export function marcarNotificacionLeida(id) {
  return cliente.post(`/pedidos/notificaciones/${id}/leer/`).then((r) => r.data);
}

/** El mesero recogió y llevó a la mesa: cierra la venta y apaga sus notificaciones. */
export function entregarPedido(pedidoId) {
  return cliente.post(`/pedidos/${pedidoId}/entregar/`).then((r) => r.data);
}

/* --- Novedades sobre pedidos ya enviados (SPEC-011) ---------------------- */

/** Pedidos en curso. Incluye los que quedaron sin mesa tras liberarla. */
export function listarPedidosActivos() {
  return cliente.get("/pedidos/").then((r) => r.data);
}

/** Mover a otra mesa, o pasar a domicilio: son la misma operación. */
export function cambiarDestino(pedidoId, { mesa = null, esDomicilio = false } = {}) {
  return cliente
    .post(`/pedidos/${pedidoId}/destino/`, { mesa, es_domicilio: esDomicilio })
    .then((r) => r.data);
}

export function agregarItem(pedidoId, platoId, cantidad = 1, observacion = "") {
  return cliente
    .post(`/pedidos/${pedidoId}/items/agregar/`, { plato_id: platoId, cantidad, observacion })
    .then((r) => r.data);
}

export function quitarItem(pedidoId, detalleId) {
  return cliente
    .post(`/pedidos/${pedidoId}/items/quitar/`, { detalle_id: detalleId })
    .then((r) => r.data);
}

export function cambiarCantidadItem(pedidoId, detalleId, cantidad) {
  return cliente
    .post(`/pedidos/${pedidoId}/items/cantidad/`, { detalle_id: detalleId, cantidad })
    .then((r) => r.data);
}

export function cambiarObservacionItem(pedidoId, detalleId, observacion) {
  return cliente
    .post(`/pedidos/${pedidoId}/items/observacion/`, { detalle_id: detalleId, observacion })
    .then((r) => r.data);
}

/**
 * Aplica VARIOS cambios de un pedido en una sola transacción (SPEC-011).
 *
 * La pantalla acumula las ediciones y las manda juntas al confirmar. El
 * backend las aplica todas o ninguna: aplicar la mitad dejaría el pedido
 * peor que antes de tocarlo.
 */
export function editarPedidoLote(pedidoId, operaciones) {
  return cliente
    .post(`/pedidos/${pedidoId}/editar/`, { operaciones })
    .then((r) => r.data);
}
