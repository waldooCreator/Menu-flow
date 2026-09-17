---
tipo: bitacora
fecha: 2026-08-27
tags: [bitacora, novedades, spec-011, adr-007, cocina, mesero]
---

# 2026-08-27 — Novedades sobre pedidos enviados

Implementación completa de [[SPEC-011 - Novedades sobre Pedidos Enviados]]. Nació de una
pregunta del autor que destapó un cabo suelto de lo entregado el día anterior.

## La pregunta que lo originó

Con [[SPEC-012 - Vista de Salon y Estado de Mesas]], liberar una mesa no toca el pedido.
Correcto — pero el autor preguntó: *¿y entonces el pedido queda en cocina apuntando a una
mesa donde ya hay otra gente?*

Sí. Y al ir a verificarlo apareció además un **bug propio del día anterior**: un domicilio
llegaba a cocina **sin destino**. `ComandaSerializer` armaba la mesa con
`source="pedido.mesa.nombre"`, y sin mesa **DRF borra el campo entero del JSON** — la
tarjeta salía con el título en blanco.

**Causa común de los dos:** el destino de un pedido no existía como dato. Cocina lo deducía
caminando hasta la mesa en el momento de pintar.

## Lo esencial

`Pedido.destino` es ahora una propiedad que **siempre devuelve texto**: `"Mesa 5"`,
`"Domicilio"` o `"Sin mesa"`. Eso solo arregla el domicilio en blanco.

Encima, [[ADR-007 - Una novedad es un evento, no una modificacion]] y el modelo `Novedad`.

## La decisión de fondo

> Editar **no puede ser un UPDATE**.

`DetallePedido` congela nombre y precio para que el historial no se reescriba solo (Regla 1
de [[SPEC-008 - Contabilidad y Auditoria]]). Un `detalle.cantidad = 3; save()` borra para
siempre que el cliente había pedido 2, y los reportes pasan a decir *a qué quedó editado*
en vez de *qué se vendió*. Y **falla en silencio**: nada se rompe, solo mienten.

`Novedad` es de **solo inserción**. `DetallePedido` refleja lo que finalmente se sirvió
(que es la venta); la historia vive aparte. Es además la primera pieza real de la Regla 2
de SPEC-008, que hasta hoy **no tenía ni tabla**.

## Bug encontrado en el camino: los platos agregados no llegaban a cocina

`rutear_pedido` empezaba con:

```python
if pedido.comandas.exists():
    return list(pedido.comandas.all())
```

Idempotente, sí — **en el sentido inútil de la palabra**. Un plato agregado a un pedido en
curso se quedaba con `comanda = None` y **no llegaba nunca a ninguna estación**. Yo mismo
había escrito en `novedades.py` el comentario "es idempotente: no duplica las existentes",
leyendo mal lo que hacía.

Corregido: rutea **lo que falta por rutear**, reusando las comandas que ya existan. Sigue
siendo idempotente de verdad, y ahora sirve al ruteo incremental. Lo cazó la prueba
automatizada, no la lectura.

## Reglas que quedaron en código

- **El precio congelado no se re-cotiza** al cambiar la cantidad. Un plato **agregado
  después** congela el precio de ese momento — si el menú cambió, es correcto
- **Quitar un plato ya cocinado no lo descocina**: la novedad guarda en qué estado estaba
  la comanda (`comanda_estaba`), para que la merma quede registrada
- **No se puede vaciar un pedido editando**: quitar el último renglón se rechaza y remite a
  anular, que exige motivo. Si no, editar sería una anulación por la puerta de atrás
- Una comanda **ya LISTA** que recibe una novedad **sale de la columna "Listas"**. Único
  caso en que una novedad mueve una comanda de columna, y con motivo: el plato está en la
  barra con la etiqueta equivocada
- **La mesa vieja no se libera sola** al mover un pedido: sería adivinar que la gente se
  esfumó

## El rojo, y por qué se puede apagar

La tarjeta va en rojo mientras haya novedades sin ver, y **dice qué cambió**:
`Mesa 12 → Mesa 5`, `2× → 3× Pan de maíz`, `AHORA SIN CEBOLLA`.

El botón **"Visto"** lo apaga. No es adorno: *una alerta que nadie puede cerrar se vuelve
papel tapiz*, y a las dos horas de servicio el rojo dejaría de significar nada.

Se resolvió con `Comanda.novedades_vistas_hasta` — una marca de tiempo en vez de una tabla
de enlace. "Hay novedades sin ver" es `creada > ese valor`, y "Visto" es ponerlo en ahora.
Una novedad **sin estación** (cambio de destino) le importa a todas; una **con estación**,
solo a la suya: cambiar la observación de un trago no pone en rojo la tarjeta de la cocina.

## Atajarlo en el origen

Al liberar una mesa con pedido en curso, el salón ya no lo deja huérfano en silencio:
ofrece **se queda / pásalo a domicilio / muévelo a otra mesa**. Más barato preguntar en el
momento que hacer que el mesero busque después un pedido sin mesa. Y no traba nada: "se
queda" es un toque.

## Verificado

Prueba automatizada contra la API real (script en el scratchpad), **todo en verde**:

- Cocina ve **"Domicilio"**, no un título vacío — el bug que originó la spec
- `GET /api/pedidos/` responde e **incluye los pedidos sin mesa**
- Mover de mesa: cocina ve el destino nuevo y **el cambio concreto**; la mesa nueva queda
  ocupada; **la vieja no se libera sola**; mover al mismo sitio se rechaza
- **"Visto" apaga el rojo** y sigue apagado tras el sondeo — es persistente
- Cantidad: cambia y **no re-cotiza** (14.000 → 14.000)
- Plato agregado: **congela el precio de ahora** y **queda ruteado** (Cocina)
- **No deja vaciar** el pedido editando
- Comanda lista que recibe novedad: **sale de "Listas"** y queda en rojo
- Un pedido **entregado** ya no se edita
- Las 6 novedades quedaron con autor
- Permisos: cocina no lista ni edita pedidos (403); sin sesión, 401

En navegador: el mesero edita cantidad (2→3) y cambia destino a domicilio; el historial de
cambios se ve con su autor; cocina muestra las dos tarjetas en rojo con los avisos
correctos; "Visto" las apaga. Sin desborde horizontal en 375 px ni en la lista ni en el
panel, y ningún control bajo 40 px.

### Falsas alarmas (dos, la misma familia de siempre)

1. *"El historial no se ve"* — la sección **sí** renderiza. Mi comprobación buscaba
   `"Cambios de este pedido"` e `innerText` devuelve el texto ya transformado por
   `text-transform: uppercase`: `"CAMBIOS DE ESTE PEDIDO"`. Comparación sensible a
   mayúsculas contra texto que el CSS ya había cambiado.
2. *"Falta Terraza 1 en las mesas"* — estaba; mi filtro de prueba era `/domicilio|Mesa/`,
   y "Terraza 1" no contiene "Mesa".

> [!warning] No verificado por Claude
> El **aspecto** de ambas pantallas. El panel del navegador no compone frames (los
> screenshots dan tiempo de espera agotado), así que todo se comprobó midiendo DOM y API.

## Pendiente

- **Anular con motivo** es el siguiente usuario natural de `Novedad`, y conviene hacerlo
  enseguida: SPEC-008 ya lo exige y `ANULADO` existe en el modelo **sin ningún endpoint**
- Agotado / "86" y rechazo desde cocina: van en sentido contrario y exigen cambiar el
  destinatario de `Notificacion`, que hoy solo sabe apuntar a un mesero
- Con Channels la novedad llegaría sola, sin esperar el sondeo de 5 s

## Enlaces

- [[SPEC-011 - Novedades sobre Pedidos Enviados]]
- [[ADR-007 - Una novedad es un evento, no una modificacion]]
- [[SPEC-012 - Vista de Salon y Estado de Mesas]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[SPEC-008 - Contabilidad y Auditoria]]
- [[Novedades sobre Pedidos en Curso]]
- [[Inicio]]
