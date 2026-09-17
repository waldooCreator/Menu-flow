import cliente from "./cliente";

/** GET público — {clave: valor}. Lo usa la página del cliente. */
export function obtenerConfiguracionPublica() {
  return cliente.get("/configuracion/publica/").then((r) => r.data);
}

/** CRUD completo — requiere sesión. Lo usa el panel de administración. */
export function listarParametros() {
  return cliente.get("/configuracion/", { params: { page_size: 100 } }).then((r) => r.data.results);
}

export function actualizarParametro(id, cambios) {
  return cliente.patch(`/configuracion/${id}/`, cambios).then((r) => r.data);
}

/** Sube la imagen de un parámetro (multipart). */
export function subirImagenParametro(id, archivo) {
  const forma = new FormData();
  forma.append("imagen", archivo);
  return cliente.patch(`/configuracion/${id}/`, forma).then((r) => r.data);
}
