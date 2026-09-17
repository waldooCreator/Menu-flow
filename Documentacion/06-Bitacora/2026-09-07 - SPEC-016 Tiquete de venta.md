---
fecha: 2026-09-07
tipo: bitacora
specs: [SPEC-016, SPEC-013, SPEC-015]
---

# 2026-09-07 — SPEC-016, tiquete de venta

Se implemento el tiquete interno de venta. No es facturacion electronica DIAN.

## Base operativa

Antes de activar la numeracion se ejecuto `manage.py limpiar_pedidos --si`.
El comando borra unicamente la operacion: pedidos, renglones, comandas,
notificaciones, novedades, cuentas, movimientos y turnos. Conserva menu,
etiquetas, mesas, estaciones, cajas, usuarios y parametros del sitio.

La base quedo verificada con todos los datos operativos en cero y con 7 mesas,
3 estaciones, 5 categorias, 19 platos, 2 observaciones, 2 etiquetas, 5 medios
de pago, 5 usuarios y la configuracion intactos. Se agregaron solo los cuatro
parametros nuevos que SPEC-016 necesita: NIT, formato, mensaje y logo del
tiquete.

## Implementado

- Consecutivo por medio de pago y ano, bloqueando la caja dentro del cobro.
- Prefijo editable desde Admin → Cobro.
- Tiquete individual, seleccion multiple y descarga imprimible.
- Formatos rollo termico y carta.
- Consolidado por dia y segundo nivel: medio, mesa o cobrador.
- Exportacion XLSX respetando los filtros del historial.
- Pruebas de numeracion, endpoints, consolidado y exportacion.

## Comprobacion

`manage.py check`, `makemigrations --check`, `npm run build` y 50 pruebas de
Django quedan en verde.
