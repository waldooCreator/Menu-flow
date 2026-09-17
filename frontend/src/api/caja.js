import cliente from "./cliente";

/**
 * Turno, cajas y movimientos (SPEC-014).
 *
 * "Caja" y "medio de pago" son la misma entidad vista en dos momentos: al
 * cobrar se elige, y ahí se acumula el dinero.
 */

/**
 * Cajas con su saldo (derivado de sus movimientos, nunca guardado).
 * Solo las activas; `incluirInactivas` las trae todas, para el panel.
 */
export function listarCajas(incluirInactivas = false) {
  const params = incluirInactivas ? { todas: 1 } : {};
  return cliente.get("/cajas/", { params }).then((r) => r.data.results ?? r.data);
}

export function guardarCaja(id, datos) {
  return id
    ? cliente.patch(`/cajas/${id}/`, datos).then((r) => r.data)
    : cliente.post("/cajas/", datos).then((r) => r.data);
}

/**
 * Mi turno abierto y su cuadre en vivo.
 * `{abierto, turno, cajas, turnos_viejos}` — las cajas y el aviso vienen en la
 * misma respuesta para no pedir tres cosas y pintar una sola pantalla.
 */
export function turnoActual() {
  return cliente.get("/turnos/actual/").then((r) => r.data);
}

/**
 * Abre el turno A NOMBRE de `usuarioId` (SPEC-014, revisado 2026-09-03):
 * caja abre los turnos de los meseros, no automáticamente el de quien tiene
 * la sesión — por eso el usuario es obligatorio, no un valor por defecto.
 *
 * `fondos` es {caja_id: monto}: un fondo inicial POR CAJA. Si el datáfono
 * arranca el día con el saldo de ayer, ignorarlo hace que el cuadre nazca
 * torcido.
 */
export function abrirTurno(usuarioId, fondos = {}, observacion = "") {
  return cliente
    .post("/turnos/abrir/", { usuario_id: usuarioId, fondos, observacion })
    .then((r) => r.data);
}

/**
 * Cerrar exige el efectivo contado: es el unico dato que nadie puede derivar.
 * La observacion es obligatoria cuando se cierra el turno de OTRA persona —
 * eso lo exige el servidor, no esta pantalla.
 */
export function cerrarTurno(id, efectivoContado, observacion = "", cajon = null) {
  const datos = { efectivo_contado: efectivoContado, observacion };
  // `cajon` solo va cuando ademas se cierra el cajon del dia (SPEC-020). Si
  // no va, el turno se cierra y el efectivo se queda donde esta — el caso de
  // "todavia quedan companeros vendiendo".
  if (cajon) {
    datos.base_dejada = cajon.base;
    datos.destino_efectivo = cajon.destino ?? null;
    datos.motivo_diferencia = cajon.motivo ?? "";
  }
  return cliente.post(`/turnos/${id}/cerrar/`, datos).then((r) => r.data);
}

/**
 * Historial de turnos. Solo administrador (SPEC-014).
 *
 * Devuelve `{ resumen, turnos, hay_mas, personas }`. Filtros (SPEC-024):
 * `desde`, `hasta`, `responsable`, `cerrado_por`, `estado`, `cuadre`,
 * `diferencia_min`, `orden`; la tanda con `desde_fila` y `limite`. Los vacíos
 * no se mandan.
 */
export function listarTurnos(filtros = {}) {
  return cliente.get("/turnos/", { params: sinVacios(filtros) }).then((r) => r.data);
}

/** Quita los filtros vacíos: un `?monto=` mandado en blanco no es "sin filtro" para todos. */
function sinVacios(filtros) {
  return Object.fromEntries(
    Object.entries(filtros).filter(([, v]) => v !== null && v !== undefined && v !== ""),
  );
}

/**
 * El libro de caja. Devuelve `{ totales, movimientos, hay_mas, personas }` —
 * los totales son del FILTRO COMPLETO, no solo de las filas que caben en
 * pantalla, que es lo que hace falta para conciliar contra el banco.
 *
 * Filtros: `desde`/`hasta` (YYYY-MM-DD, inclusivos), `caja`, `tipo`,
 * `concepto`, y desde SPEC-024 `monto`, `monto_min`, `monto_max`, `q` (texto o
 * número de tiquete) y `autor`. La tanda con `desde_fila` y `limite`.
 */
export function listarMovimientos(filtros = {}) {
  return cliente.get("/movimientos/", { params: sinVacios(filtros) }).then((r) => r.data);
}

/** Mover plata de una caja a otra: consignar el efectivo en el banco, p.ej. */
export function trasladarEntreCajas(origen, destino, monto, descripcion = "") {
  return cliente
    .post("/cajas/trasladar/", { origen, destino, monto, descripcion })
    .then((r) => r.data);
}

/**
 * Un ingreso o gasto que no es una venta: pagar al domiciliario, comprar hielo…
 *
 * Si es un GASTO, la categoria es obligatoria (SPEC-020): sin ella nunca se
 * podria responder "¿cuanto se fue en nomina el mes pasado?".
 */
export function registrarMovimiento(caja, tipo, monto, descripcion = "", categoria = null) {
  const datos = { caja, tipo, monto, descripcion };
  if (categoria) {
    datos.concepto = "gasto";
    datos.categoria = categoria;
  }
  return cliente.post("/movimientos/", datos).then((r) => r.data);
}

/* --- Activos liquidos (SPEC-020) ---------------------------------------- */

/**
 * Cuanta plata hay ahora y donde: cada caja con su saldo, y los totales ya
 * separados entre efectivo y banco.
 */
export function obtenerActivos() {
  return cliente.get("/activos/").then((r) => r.data);
}

/** En que se va la plata. Solo las activas, salvo para el panel. */
export function listarCategoriasGasto() {
  return cliente.get("/categorias-gasto/").then((r) => r.data.results ?? r.data);
}

export function guardarCategoriaGasto(id, datos) {
  return id
    ? cliente.patch(`/categorias-gasto/${id}/`, datos).then((r) => r.data)
    : cliente.post("/categorias-gasto/", datos).then((r) => r.data);
}

/** Con cuanto arrancaba esta caja. Una sola vez por caja, y solo el admin. */
export function fijarSaldoInicial(cajaId, monto) {
  return cliente
    .post(`/cajas/${cajaId}/saldo-inicial/`, { monto })
    .then((r) => r.data);
}

/**
 * Cuadrar una caja contra la realidad (el extracto del banco, o el conteo).
 * No reescribe el saldo: registra la diferencia como movimiento firmado.
 */
export function ajustarSaldo(cajaId, saldoReal, motivo) {
  return cliente
    .post(`/cajas/${cajaId}/ajustar/`, { saldo_real: saldoReal, motivo })
    .then((r) => r.data);
}
