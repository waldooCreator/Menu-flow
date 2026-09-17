import cliente from "./cliente";

/**
 * Clientes (SPEC-019). Se crean solos al confirmar un domicilio; esta API es
 * para consultarlos, corregirlos y borrarlos.
 */

export function listarClientes(buscar = "") {
  const params = { page_size: 200 };
  if (buscar.trim()) params.buscar = buscar.trim();
  return cliente.get("/clientes/", { params }).then((r) => r.data.results ?? r.data);
}

export function guardarCliente(id, datos) {
  return cliente.patch(`/clientes/${id}/`, datos).then((r) => r.data);
}

/**
 * Borrar elimina el dato personal, NO sus ventas: el vinculo es `SET_NULL`,
 * asi que las cuentas quedan con su nombre congelado (Ley 1581 + SPEC-008).
 */
export function borrarCliente(id) {
  return cliente.delete(`/clientes/${id}/`);
}

export function agregarDireccion(id, direccion, indicaciones = "") {
  return cliente
    .post(`/clientes/${id}/direcciones/`, { direccion, indicaciones })
    .then((r) => r.data);
}

export function quitarDireccion(id, direccionId) {
  return cliente.delete(`/clientes/${id}/direcciones/${direccionId}`);
}

/** El 5º reporte de SPEC-018, que este modulo desbloquea. */
export function clientesFrecuentes({ desde = null, hasta = null } = {}) {
  const params = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  return cliente.get("/clientes/frecuentes/", { params }).then((r) => r.data);
}
