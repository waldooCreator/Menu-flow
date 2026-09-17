---
tipo: bitacora
fecha: 2026-09-14
tags: [cocina, concurrencia, domicilios, correccion, pruebas]
---

# 2026-09-14 — Corrección de dos defectos de cocina

Los dos defectos que destapó la [[2026-09-14 - Documentacion puesta al dia|revisión de la
documentación]]. El autor pidió corregirlos antes de pasar a Promociones. No hizo falta
cambiar ninguna spec: las dos ya decían lo que debía pasar y el código no lo cumplía.

## 1. El domicilio listo no le avisaba al mesero

**Qué pasaba.** Al tocar "Listo" en la comanda de un domicilio, la petición respondía 500.
El aviso al mesero se armaba con `pedido.mesa.nombre`, y un domicilio no tiene mesa. La
tarjeta de cocina ya usaba `pedido.destino` desde SPEC-011; el aviso quedó con la forma
vieja.

**Qué se cambió.** El aviso usa `pedido.destino`, igual que la tarjeta. Una línea.

**Por qué importaba más de lo que parece.** Como la petición fallaba, el mesero no se
enteraba de que el domicilio estaba listo. El pedido quedaba en la barra hasta que
alguien lo viera por casualidad.

## 2. Dos cocineros podían tomar la misma comanda

**Qué pasaba.** "Empezar a preparar" no revisaba en qué estado estaba la comanda: una ya
tomada se podía volver a tomar, y dos toques en el mismo instante respondían 200 los dos.
Con "Listo" pasaba lo mismo, con un efecto visible: **dos toques avisaban dos veces al
mesero**.

**Qué se cambió.** El mismo patrón de [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]:
dentro de una transacción se bloquea la fila, se relee el estado y solo entonces se
decide.

- `en-preparacion` solo se acepta si la comanda está **pendiente**. Si no, responde 409
  con el motivo ("Otra persona ya empezó a preparar esta comanda").
- `lista` se rechaza con 409 si la comanda **ya está lista**. Desde pendiente sí se sigue
  aceptando, como antes.
- En el tablero, un 409 muestra el motivo arriba de las columnas y recarga las tarjetas.
  Antes el botón parecía no hacer nada hasta el siguiente sondeo.

> [!note] Se bloquea el pedido, no solo la comanda
> Primero el pedido y después la comanda, siempre en ese orden. El estado del pedido se
> *deriva* de sus comandas, así que cuando cocina y bar terminan en el mismo instante,
> cada una mira la comanda de la otra. Sin bloquear el pedido, las dos podían ver a la
> otra sin terminar y el pedido se quedaba "en preparación" con todo listo.
>
> El bloqueo va sin `select_related`, porque Postgres no bloquea el lado nulo de un JOIN y
> la mesa de un domicilio es nula.

## Cómo se comprobó

Las pruebas nuevas **se corrieron primero contra el código viejo**, para confirmar que
detectaban el fallo y no pasaban por casualidad:

| Prueba | Código viejo | Código nuevo |
|---|---|---|
| "Listo" en un domicilio avisa al mesero | Error: `AttributeError` | Pasa |
| Una comanda ya tomada no se vuelve a tomar | Falla: 200 en vez de 409 | Pasa |
| Dos cocineros a la vez (hilos simultáneos): solo uno la toma | Falla: `[200, 200]` | Pasa |
| Dos "Listo" a la vez avisan una sola vez | Falla: `[200, 200]` | Pasa |
| Cocina y bar terminan a la vez, y el pedido queda listo | **Pasa** | Pasa |

La última pasó también con el código viejo: esa carrera no se reproduce en cada corrida.
Se deja como protección, pero no es la prueba de que existía el fallo.

Suite completa: **163 pruebas, todas en verde**. El frontend compila.

## Archivos

- `backend/estaciones/views.py` — `_bloquear()`, y las acciones `en_preparacion` y `lista`
- `frontend/src/views/estacion/EstacionTablero.vue` — aviso del 409 y recarga
- `backend/pedidos/tests.py` — se quitaron las dos marcas de fallo esperado y se agregaron
  tres pruebas con hilos
- [[SPEC-005 - Estaciones y Ruteo]] y [[SPEC-011 - Novedades sobre Pedidos Enviados]] —
  criterios marcados
