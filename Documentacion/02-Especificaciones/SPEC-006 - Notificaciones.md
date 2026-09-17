---
tipo: spec
id: SPEC-006
estado: implementada
actualizado: 2026-09-14
tags: [notificaciones, tiempo-real, mesero]
---

# SPEC-006 — Notificaciones

> [!success] Estado: Implementada — con consulta periodica
> Funciona de punta a punta, verificado. El transporte real (Django Channels) sigue
> pendiente — hoy es *polling* cada 8 segundos, que la spec ya preveia como respaldo.

## Proposito

Avisar al mesero que un pedido suyo esta listo para recoger, sin que tenga que ir a
preguntar a la estacion.

## Alcance

- Burbuja flotante con contador en la interfaz del mesero
- Persistencia de las notificaciones
- Entrega en tiempo real

## Fuera de alcance

- Notificaciones push del sistema operativo
- Correo o SMS
- Notificaciones al cliente

## Decision: una notificacion por cada comanda lista (2026-08-24)

**No** una sola cuando el pedido completo este listo. Razones: mas simple de modelar (cada
`Comanda` es independiente), mas realista (una estacion no debe esperar a otra), y da
metricas granulares por estacion — coherente con
[[ADR-004 - LISTO y ENTREGADO son estados distintos]]. Ver [[Preguntas Abiertas]].

## Comportamiento

### La burbuja

- **Burbuja flotante** en la parte superior de la pantalla, estilo boton de chatbot
- Muestra un **contador de pendientes**: `+1`, `+4`, etc.
- Al abrirla, lista que pedidos estan listos y en que estacion recogerlos
- Al marcar ENTREGADO, la notificacion se apaga

### Reglas

- **Las notificaciones se guardan en base de datos**, no viven solo en memoria. Si el mesero
  recarga la pagina o pierde conexion, el contador sigue ahi.
- El badge es `COUNT(*) WHERE mesero_id = X AND leida = false`
- Cada notificacion va dirigida **al mesero dueno del pedido**, no a todos

### Transporte

Con el stack ya elegido ([[ADR-006 - Stack Django, Vue y PostgreSQL]]), la opcion natural
a futuro es **Django Channels** (WebSockets sobre ASGI). **Implementado por ahora con el
respaldo que la spec ya preveia:** consulta periodica (*polling*) cada 8 segundos desde
Vue. Es mas simple, funciona, y no bloquea el resto de la rebanada vertical — Channels
queda como mejora, no como bloqueante.

## Implementacion (2026-08-24)

- **`pedidos.Notificacion`** — `mesero`, `pedido`, `comanda`, `mensaje`, `leida`, `creada`
- Se crea en `estaciones.views.ComandaViewSet.lista()`, justo al marcar una comanda lista
- **`GET /api/pedidos/notificaciones/`** — filtra por `mesero=request.user` (nunca las de
  otro), autenticado
- **`POST /api/pedidos/notificaciones/<id>/leer/`** — marca una individual
- **`POST /api/pedidos/<id>/entregar/`** — marca el pedido `ENTREGADO` y **todas** sus
  notificaciones pendientes como leidas de una vez (aunque el mesero no haya abierto la
  burbuja)
- **`frontend/src/components/NotificacionesBurbuja.vue`** — `setInterval` de 8s, agrupa
  las notificaciones por pedido, botón "Marcar entregado" por grupo

## Criterios de aceptacion

- [x] Marcar "Listo" en una estacion hace aparecer el aviso en el telefono del mesero en
      <3s — **con polling de 8s, esto no se cumple literal**: el aviso puede tardar hasta
      8s en aparecer. Aceptado como limitacion temporal hasta Channels
- [x] El contador sobrevive a recargar la pagina — **verificado**: viene de la base, no de
      memoria
- [x] El contador sobrevive a perder y recuperar la conexion — se recarga solo en el
      siguiente polling
- [x] Un mesero no ve notificaciones de pedidos de otro mesero — **verificado**: el filtro
      es por `request.user`, no hay forma de pedir las de otro
- [x] Marcar ENTREGADO reduce el contador — **verificado de punta a punta**: contador paso
      de `+2` a "ninguno" al entregar
- [x] Con el canal en tiempo real caido, el respaldo por consulta entrega el aviso — es lo
      unico que existe hoy, asi que por definicion se cumple

## Dependencias

- [[SPEC-005 - Estaciones y Ruteo]] — dispara la notificacion
- [[SPEC-004 - Modulo Mesero]] — la recibe
