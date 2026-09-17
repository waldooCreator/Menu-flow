import cliente from "./cliente";

/**
 * Los reportes de venta (SPEC-018) en una sola llamada: son una sola
 * pantalla con un solo rango, y pedirlos por separado serian varios viajes
 * para pintar lo mismo.
 *
 * `soloPromociones` deja el ranking de productos solo con combos (SPEC-023).
 */
export function obtenerReportes({ desde = null, hasta = null, soloPromociones = false } = {}) {
  const params = {};
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  if (soloPromociones) params.solo_promociones = 1;
  return cliente.get("/reportes/", { params }).then((r) => r.data);
}

/**
 * Un producto, plato o promocion, agrupado por dia, semana o mes (SPEC-023).
 * Aparte porque cambia cada vez que se elige otro producto.
 */
export function obtenerReporteProducto({ plato, desde = null, hasta = null, agrupar = "dia" }) {
  const params = { plato, agrupar };
  if (desde) params.desde = desde;
  if (hasta) params.hasta = hasta;
  return cliente.get("/reportes/producto/", { params }).then((r) => r.data);
}
