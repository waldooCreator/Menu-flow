---
tipo: bitacora
fecha: 2026-08-25
tags: [bitacora, hito, estaciones, notificaciones, vertical-slice]
---

# 2026-08-25 — Rebanada vertical cerrada: estaciones y notificaciones

Sigue a [[2026-08-24 - Rebanada vertical del QR de punta a punta]]. **Cierra la Fase 1**
tal como la definía [[Vision del Producto]] desde el principio del proyecto.

## Qué se pidió

Terminar la rebanada vertical antes de pasar a diseño: ruteo a estaciones, tablero de
comandas, notificación al mesero, marcar entregado.

## Decisión resuelta antes de construir

La pregunta abierta de [[SPEC-006 - Notificaciones]] (¿una notificación por comanda lista,
o una sola al final?) se resolvió: **por cada comanda**. Más simple de modelar, más
realista operacionalmente, y da métricas granulares por estación — coherente con
[[ADR-004 - LISTO y ENTREGADO son estados distintos]]. Quedó documentada en
[[Preguntas Abiertas]] antes de escribir código, no decidida a mitad de la implementación.

## Qué se construyó

### Backend — app `estaciones`

- **`Estacion`** (nombre, orden, `por_defecto`) y **`Comanda`** (pedido, estación, estado,
  con timestamps `en_preparacion_desde` / `lista_desde` para las métricas de ADR-004)
- **`menu.Categoria.estacion`** — el ruteo en sí: qué categoría va a qué estación
- **`ruteo.py`** — `rutear_pedido()`, responsabilidad única (solo divide, no guarda, no
  notifica), llamado dentro de la misma transacción que confirmar el pedido
- **`pedidos.Notificacion`** — se crea al marcar una comanda lista, dirigida solo al
  mesero dueño del pedido
- Endpoints: `GET /api/comandas/`, `POST .../en-preparacion/`, `POST .../lista/`,
  `GET /api/pedidos/notificaciones/`, `POST .../leer/`, `POST /api/pedidos/<id>/entregar/`
- El estado del `Pedido` se **deriva** del de sus comandas (pendiente → en_preparación →
  listo), salvo "entregado", que es la única transición manual del mesero

### Frontend

- **`EstacionTablero.vue`** — tres columnas, selector de estación, card → detalle →
  "Atrás"/"Listo"
- **`NotificacionesBurbuja.vue`** — burbuja flotante con contador, agrupa por pedido,
  botón "Marcar entregado" por grupo, consulta periódica cada 8 segundos

## Verificado de punta a punta, en la interfaz real

1. Cliente arma un pedido con un plato de **Cocina** y uno de **Bar**, genera el QR
2. Mesero lo sube, confirma → **se crean 2 comandas separadas**, una por estación
3. Tablero de Cocina: abrir la card la pasa a "en preparación"; "Listo" la cierra
4. Tablero de Bar: mismo camino
5. Burbuja del mesero: contador `+2` con las dos notificaciones agrupadas bajo
   "Pedido #4 · listo"
6. "Marcar entregado" → el pedido pasa a `entregado`, el contador baja a 0, ambas
   notificaciones quedan leídas

Confirmado en Postgres: `Comanda.lista_desde` poblado en ambas comandas con timestamps
distintos — la métrica de tiempo por estación que prometía ADR-004 ya se puede calcular.

## Simplificaciones conscientes, anotadas, no escondidas

- El distribuidor no implementa una capa de "estrategia de ruteo" intercambiable (Strategy
  pattern) — hoy solo hay una estrategia (por categoría). Añadir esa abstracción sin una
  segunda estrategia real habría sido sobre-ingeniería
- Sin lock de base de datos contra dos clics simultáneos en la misma comanda — la
  protección es práctica (la card cambia de columna), no transaccional
- Notificaciones por consulta periódica (8s), no Django Channels — el respaldo que la
  propia spec ya preveía, no el canal en tiempo real

## Estado al cierre

**La Fase 1 — rebanada vertical — está cerrada.** [[SPEC-004 - Modulo Mesero]], [[SPEC-005 - Estaciones y Ruteo]], [[SPEC-006 - Notificaciones]]
actualizadas con estado de implementación honesto. Lo que queda fuera es diseño/UX
(cronómetro, aviso sonoro), tiempo real de verdad (Channels), y caminos alternativos
(Camino B del mesero, cámara en vivo) — no bloquea nada, es refinamiento.

**Siguiente etapa, por indicación del autor: diseño.** Portar el sistema visual de Fase 0
(`/prototipo`) a la interfaz real, que hoy es funcional pero simple.

## Enlaces

- [[Vision del Producto]]
- [[SPEC-004 - Modulo Mesero]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[SPEC-006 - Notificaciones]]
- [[ADR-004 - LISTO y ENTREGADO son estados distintos]]
- [[Inicio]]
