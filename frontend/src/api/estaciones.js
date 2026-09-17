import cliente from "./cliente";

export function listarEstaciones() {
  return cliente.get("/estaciones/", { params: { page_size: 50 } }).then((r) => r.data.results);
}

/**
 * Las comandas en curso del tablero. Sin `estacionId`, las de TODAS las
 * estaciones: es lo que se ve con estaciones unificadas (SPEC-023, sección 7).
 */
export function listarComandas(estacionId = null) {
  const params = { activas: 1, page_size: 200 };
  if (estacionId) params.estacion = estacionId;
  return cliente.get("/comandas/", { params }).then((r) => r.data.results);
}

export function marcarEnPreparacion(comandaId) {
  return cliente.post(`/comandas/${comandaId}/en-preparacion/`).then((r) => r.data);
}

export function marcarLista(comandaId) {
  return cliente.post(`/comandas/${comandaId}/lista/`).then((r) => r.data);
}

/**
 * La estación acusa recibo de las novedades de esta comanda (SPEC-011): su
 * tarjeta deja de estar en rojo. Poder apagar el aviso es parte del
 * mecanismo — una alerta que nadie puede cerrar se vuelve papel tapiz.
 */
export function marcarNovedadesVistas(comandaId) {
  return cliente.post(`/comandas/${comandaId}/visto/`).then((r) => r.data);
}

/* --- CRUD del panel (SPEC-007): solo el administrador escribe ------------ */

export function guardarEstacion(id, datos) {
  return id
    ? cliente.patch(`/estaciones/${id}/`, datos).then((r) => r.data)
    : cliente.post("/estaciones/", datos).then((r) => r.data);
}

/**
 * Puede fallar con 500 si la estación tiene comandas históricas (PROTECT):
 * ese historial no se borra. El panel muestra el error y sugiere moverle
 * las categorías a otra estación en su lugar.
 */
export function eliminarEstacion(id) {
  return cliente.delete(`/estaciones/${id}/`);
}
