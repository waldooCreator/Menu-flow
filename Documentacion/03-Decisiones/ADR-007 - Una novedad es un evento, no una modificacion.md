---
tipo: adr
id: ADR-007
estado: aceptada
fecha: 2026-08-27
tags: [novedades, auditoria, modelo, contabilidad]
---

# ADR-007 — Una novedad es un evento, no una modificacion

**Estado:** Aceptada · **Fecha:** 2026-08-27

## Contexto

El autor pidio que el mesero pueda editar pedidos ya enviados a cocina: cambiar la mesa,
pasarlos a domicilio, agregar y quitar platos, cambiar cantidades y observaciones
(ver [[SPEC-011 - Novedades sobre Pedidos Enviados]]).

La forma obvia de implementarlo es la directa: `detalle.cantidad = 3; detalle.save()`.

## El problema con lo obvio

`DetallePedido` guarda `nombre_congelado` y `precio_congelado` **justamente** para que el
historial no se reescriba solo. Es la **Regla 1 de
[[SPEC-008 - Contabilidad y Auditoria]]**, marcada ahi como no negociable.

Si editar es un `UPDATE` a secas:

- Se pierde para siempre que el cliente **habia pedido 2**
- Los reportes dejan de decir *que se vendio* y pasan a decir *a que quedo editado*
- Se viola la **Regla 2** (auditoria de solo insercion), que ademas **hoy no tiene ni tabla**:
  no existe ningun modelo de auditoria en el backend

> [!danger] Y falla en silencio
> Nada se rompe, nada tira un error. Simplemente los reportes empiezan a mentir, y no hay
> forma de notarlo desde adentro. Es el peor tipo de error: el que no avisa.

## Decision

**Toda novedad se registra como un hecho nuevo que se agrega, nunca como una correccion del
hecho anterior.**

Un unico modelo `Novedad`, de **solo insercion**: pedido, renglon afectado, tipo, valor
antes, valor despues, motivo, autor, fecha, y si la estacion ya la vio.

`DetallePedido` **si** refleja el estado actual — lo que finalmente se sirvio, que es lo que
constituye la venta. La historia de como se llego ahi vive en `Novedad`.

## Justificacion

- **Cumple la Regla 2 por construccion**, en vez de pelearse con ella. Una tabla que solo
  admite inserciones no puede perder historia
- **Sirve a las 18 novedades del catalogo** ([[Novedades sobre Pedidos en Curso]]), no solo
  a cambiar una cantidad. Anular, agotado, devolucion, cortesia: todas caben
- **El rojo del tablero sale gratis**: hay novedades sin ver → la tarjeta esta en rojo
- **La notificacion sale gratis**: crear la novedad es el evento que dispara el aviso
- Hacerlo como `UPDATE` es mas rapido esta semana y hay que deshacerlo entero cuando llegue
  la contabilidad

## Alternativas descartadas

**Renglones versionados** (marcar el `DetallePedido` viejo como anulado y crear uno nuevo
por cada cambio). Da historia completa dentro del propio detalle, pero **complica toda
consulta de venta**: cada reporte tendria que saber cual version cuenta. La historia en una
tabla aparte deja las consultas de venta tan simples como hoy.

**Auditoria generica por senales de Django** (registrar todo cambio de todo modelo
automaticamente). Registra el *que* pero no el *por que* ni el *para quien*: no sabria
distinguir "el mesero movio el pedido a la Mesa 2" de un cambio de configuracion. Y no
sirve para pintar el tablero, que es la mitad del valor.

## Consecuencias

**Positivas**
- La contabilidad queda con cimiento real desde la primera novedad
- Un solo mecanismo para toda la familia: menos codigo, no mas
- Se puede reconstruir quien hizo que y cuando, que es lo que SPEC-008 exige

**Negativas / a vigilar**
- Es mas trabajo que un `UPDATE` para la primera funcion. El pago llega desde la segunda
- La tabla crece sin borrarse nunca. En un restaurante son decenas de filas por servicio,
  asi que no es problema de volumen — pero conviene no meterle datos que no aporten
- Hay que resistir la tentacion de "arreglar" una novedad mal registrada editandola. Si
  quedo mal, se registra otra que la corrija

## Enlaces

- [[SPEC-011 - Novedades sobre Pedidos Enviados]]
- [[SPEC-008 - Contabilidad y Auditoria]]
- [[Novedades sobre Pedidos en Curso]]
- [[SPEC-012 - Vista de Salon y Estado de Mesas]]
