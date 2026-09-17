---
fecha: 2026-09-03
tipo: bitacora
specs: [SPEC-015]
---

# 2026-09-03 — Historial de ventas

SPEC-015, escrita, aprobada e implementada el mismo día.

## Lo primero: aclarar la palabra

"Factura" significa dos cosas muy distintas, y confundirlas habría costado
semanas:

- En el sistema de Springfield, **cada venta cobrada**. Un registro interno.
- En Colombia, la **factura electrónica DIAN**, con numeración autorizada,
  CUFE y envío a la DIAN.

El autor confirmó: **nada de DIAN**. Esto es el historial interno. Si algún día
hace falta lo otro, es una spec aparte y un proveedor externo. Quedó escrito en
la spec para que nadie lo asuma al revés más adelante.

## Lo que no hubo que construir

El dato ya estaba completo desde SPEC-013: cada cuenta cerrada guarda mesa o
domicilio, fecha, quién cobró, medio de pago y los totales congelados.

Al verificar contra el código **el detalle ya funcionaba**: `GET
/api/cuentas/<id>/` devolvía los platos con `nombre_congelado` y
`precio_congelado`. Un paso del plan se tachó antes de empezar.

Sin migraciones, sin modelo nuevo.

## Tres números eran dos de menos

La spec, tal como se escribió, pedía tres números arriba: vendido, propinas y
cantidad. Al implementarlo apareció el problema: **el total congelado ya
incluye la propina** (`total = subtotal + propina + impuesto`).

Con tres números había que elegir mal:

- Si "vendido" usaba el total → contaba la propina como venta, y el dueño
  creería que vendió más de lo que vendió.
- Si "vendido" usaba solo el subtotal → no había ningún número para comparar
  contra el banco, que es lo que de verdad se movió.

Van los cuatro:

| Vendido | Propinas | Entró a caja | Ventas |
|---|---|---|---|
| La comida sola | De los meseros | Todo incluido | Cuántas, y cuántas anuladas |

Y el desglose por medio de pago suma **lo cobrado**, no lo vendido — porque es
la plata que físicamente entró a cada caja.

La spec se corrigió con el razonamiento, no solo con el número.

## Dos decisiones que aparecieron al construir

**Una cuenta anulada estando abierta no es una venta.** Nadie pagó nada. El
historial lista solo las que en algún momento se cobraron — las que tienen
totales congelados. Un pedido anulado antes de cobrar es otra cosa y vive en la
vista de pedidos.

**Se filtra por fecha de cobro, no de apertura.** Una mesa que se sentó a las
11 de la noche y pagó a las 12 es venta del día en que pagó, que es cuando el
dinero entró a la caja.

## La pantalla

`/mesero/ventas`. Al abrir muestra lo de hoy, sin filtrar.

- Los cuatro números, y debajo el desglose por medio de pago
- Atajos **Hoy · Ayer · Esta semana · Este mes**, más rango a mano
- Filtros por medio de pago y por tipo (mesa / domicilio)
- Interruptor de anuladas: se ven tachadas, en gris, con su motivo y quién las
  anuló — y **no suman**
- Al tocar una venta, el detalle con los platos al precio al que se vendieron

## Comprobado

Con clics reales y capturas:

- La aritmética cierra: vendido + impuestos + propinas = entró a caja, y el
  desglose por medio suma exactamente lo cobrado ($437.800 en las dos cuentas)
- Mostrar las anuladas **no cambió ningún total** — ya no sumaban
- La anulada se ve tachada con "anulada: el cliente devolvió el plato"
- El detalle mostró 3× Ceviche a su precio congelado, subtotal, propina y total
- "Ayer" puso el 2 de septiembre y respondió "No hay ventas en este rango"
- En 375 px no hay desborde: los cuatro números se acomodan en dos filas

**37 tests** en verde — 7 de concurrencia, 13 de turno, 7 del libro, 10 nuevos
del historial.

Un test falló al principio por una razón que vale la pena anotar: el ayudante
generaba dos ventas idénticas en el mismo segundo, y la **protección
anti-duplicado del QR rechazó la segunda**. No era un bug — era la protección
funcionando. Se corrigió el test, no el código.

Los datos de prueba quedaron borrados y los saldos volvieron a como estaban.

## Lo que sigue

**Clientes** — la única de la lista que necesita modelo nuevo. Con campo de
observaciones desde el primer día: en Springfield el personal escribe "pago
nequi" en el campo de teléfono porque no hay dónde anotar.
