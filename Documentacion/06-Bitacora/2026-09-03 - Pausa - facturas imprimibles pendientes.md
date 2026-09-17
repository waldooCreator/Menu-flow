---
fecha: 2026-09-03
tipo: bitacora
specs: [SPEC-015, SPEC-016]
---

# 2026-09-03 — Pausa: facturas imprimibles quedan pendientes

Se cambió de tema con el trabajo entendido pero sin empezar. Esta entrada
existe para poder retomarlo sin releer la conversación.

## Lo último que sí se terminó

**Filtros ampliados en el historial de ventas** (SPEC-015): mesa, quién cobró,
rango de monto, franja horaria y orden, detrás de un botón "Más filtros" con
contador. Dos detalles que se resolvieron porque si no el filtro mentiría:

- La franja horaria **cruza la medianoche** — "de 22:00 a 02:59" es el horario
  real de un restaurante y como rango normal no devolvería nada
- Los desplegables **solo ofrecen mesas y personas con ventas**: un filtro que
  no devuelve nada es peor que no ofrecerlo

46 tests en verde. Saldos verificados intactos.

## Lo que queda en pausa

[[SPEC-016 - Impresion y Exportacion de Facturas]], en estado **bloqueada**.

El autor pidió: factura individual en PDF imprimible, un documento con todo lo
vendido respetando filtros, descarga en Excel que respete esos mismos filtros,
y **estética muy parecida a una factura real**.

Eso **revierte una regla del proyecto** — `CLAUDE.md` dice "Sin impresión". El
autor lo confirmó, pero su mensaje quedó cortado a media frase, así que puede
faltar contexto.

## Por qué está bloqueada y no solo pendiente

Tres cosas que no se pueden inventar:

1. **Cómo debe decir el encabezado.** "FACTURA" tiene peso legal en Colombia y
   esto no pasa por la DIAN. Necesita consulta con el contador.
2. **NIT, régimen tributario y logo** — no existen en la configuración. Sin
   ellos el documento no puede verse real.
3. **Si el consolidado es un resumen o las facturas en fila** — dos cosas muy
   distintas de construir.

## Buena noticia para cuando se retome

Casi todo el trabajo de datos ya está hecho:

- `GET /api/ventas/` con todos los filtros — el Excel y el consolidado salen de
  la **misma consulta**, así que respetan el filtro por construcción
- `GET /api/cuentas/<id>/` ya devuelve la venta completa a precio congelado
- La configuración es clave/valor, así que NIT y logo son filas nuevas, sin
  migración

Lo que falta es el diseño del documento y decidir si el PDF se genera en el
servidor o se deja al navegador con hoja de estilos de impresión.

## Lo otro que sigue pendiente

**Clientes** — la única de la lista que necesita modelo nuevo. Con campo de
observaciones desde el primer día: en Springfield el personal escribe "pago
nequi" en el campo de teléfono porque no hay dónde anotar.
