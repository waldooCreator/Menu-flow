import cliente from "./cliente";

/**
 * Administración de mesas y usuarios (SPEC-001 / SPEC-007) — solo admin.
 * Ninguno tiene DELETE a propósito: mesas y usuarios con historia se
 * desactivan, nunca se borran (toda venta conserva su mesa y su responsable).
 */

export function listarMesasAdmin() {
  return cliente.get("/mesas-admin/", { params: { page_size: 100 } }).then((r) => r.data.results);
}

export function guardarMesa(id, datos) {
  return id
    ? cliente.patch(`/mesas-admin/${id}/`, datos).then((r) => r.data)
    : cliente.post("/mesas-admin/", datos).then((r) => r.data);
}

/** El QR impreso anterior deja de valer — esa es justamente la utilidad. */
export function regenerarCodigoMesa(id) {
  return cliente.post(`/mesas-admin/${id}/regenerar-codigo/`).then((r) => r.data);
}

export function listarUsuarios() {
  return cliente.get("/usuarios/", { params: { page_size: 100 } }).then((r) => r.data.results);
}

export function guardarUsuario(id, datos) {
  return id
    ? cliente.patch(`/usuarios/${id}/`, datos).then((r) => r.data)
    : cliente.post("/usuarios/", datos).then((r) => r.data);
}

export function restablecerClave(id, password) {
  return cliente.post(`/usuarios/${id}/clave/`, { password }).then((r) => r.data);
}
