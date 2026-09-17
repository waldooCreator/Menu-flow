import cliente from "./cliente";

/** Lectura pública — la usa la página del cliente. */
export function listarCategorias() {
  return cliente.get("/categorias/", { params: { page_size: 100 } }).then((r) => r.data.results);
}

export function listarPlatos() {
  return cliente.get("/platos/", { params: { page_size: 200 } }).then((r) => r.data.results);
}

/**
 * Para el panel: también las promociones programadas, vencidas y apagadas
 * (SPEC-023). El servidor solo lo respeta si quien pide es administrador.
 */
export function listarPlatosPanel() {
  return cliente.get("/platos/", { params: { page_size: 200, todas: 1 } }).then((r) => r.data.results);
}

export function listarObservacionesRapidas() {
  // Solo las generales y activas: son el respaldo para un plato que aun no
  // trae su lista combinada. Las propias de cada plato llegan dentro del
  // plato (SPEC-003).
  return cliente
    .get("/observaciones-rapidas/", { params: { page_size: 100, generales: 1, activo: 1 } })
    .then((r) => r.data.results ?? r.data);
}

/** Escritura — requiere sesión (panel de administración). */
export function actualizarPlato(id, cambios) {
  return cliente.patch(`/platos/${id}/`, cambios).then((r) => r.data);
}

/** Cocina solo puede cambiar disponibilidad (SPEC-017). */
export function cambiarDisponibilidad(id, disponible) {
  return cliente
    .post(`/platos/${id}/disponibilidad/`, { disponible })
    .then((r) => r.data);
}

/* --- CRUD del panel de administración (SPEC-007) ------------------------- */

/**
 * Crea o actualiza un plato. Los datos van siempre como JSON, y la foto, si
 * hay, en una segunda llamada que solo la lleva a ella.
 *
 * Antes todo iba junto en multipart cuando había foto, y un formulario
 * multipart no sabe mandar listas de objetos: los componentes de una
 * promoción (SPEC-023) y las métricas del plato llegaban rotos. Separarlo
 * deja cada formato haciendo lo único que hace bien.
 */
export async function guardarPlato(id, datos, foto = null) {
  const guardado = id
    ? (await cliente.patch(`/platos/${id}/`, datos)).data
    : (await cliente.post("/platos/", datos)).data;
  if (foto instanceof File) {
    const cuerpo = new FormData();
    cuerpo.append("foto", foto);
    return (await cliente.patch(`/platos/${guardado.id}/`, cuerpo)).data;
  }
  return guardado;
}

export function eliminarPlato(id) {
  return cliente.delete(`/platos/${id}/`);
}

export function guardarCategoria(id, datos) {
  return id
    ? cliente.patch(`/categorias/${id}/`, datos).then((r) => r.data)
    : cliente.post("/categorias/", datos).then((r) => r.data);
}

export function eliminarCategoria(id) {
  return cliente.delete(`/categorias/${id}/`);
}

export function guardarObservacionRapida(id, datos) {
  return id
    ? cliente.patch(`/observaciones-rapidas/${id}/`, datos).then((r) => r.data)
    : cliente.post("/observaciones-rapidas/", datos).then((r) => r.data);
}

export function eliminarObservacionRapida(id) {
  return cliente.delete(`/observaciones-rapidas/${id}/`);
}

/* --- Observaciones rapidas: generales, por categoria y por plato (SPEC-003) --- */

/**
 * Sin argumento trae todas; `platoId` las de un plato; `categoriaId` las de
 * una categoria (sin las de sus platos); `soloGenerales` las de todos.
 */
export function listarObservaciones({ platoId = null, categoriaId = null, soloGenerales = false } = {}) {
  const params = { page_size: 200 };
  if (platoId) params.plato = platoId;
  else if (categoriaId) params.categoria = categoriaId;
  if (soloGenerales) params.generales = 1;
  return cliente.get("/observaciones-rapidas/", { params })
    .then((r) => r.data.results ?? r.data);
}

/**
 * Sin `platoId` ni `categoriaId`: general, para todos los platos.
 * Con `categoriaId`: para todos los platos de esa seccion.
 * Con `platoId`: solo para ese plato.
 */
export function crearObservacion(texto, { platoId = null, categoriaId = null } = {}) {
  return cliente
    .post("/observaciones-rapidas/", { texto, plato: platoId, categoria: categoriaId })
    .then((r) => r.data);
}

export function actualizarObservacion(id, cambios) {
  return cliente.patch(`/observaciones-rapidas/${id}/`, cambios).then((r) => r.data);
}

export function borrarObservacion(id) {
  return cliente.delete(`/observaciones-rapidas/${id}/`);
}
