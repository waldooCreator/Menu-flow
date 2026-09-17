---
tipo: spec
id: SPEC-005
estado: implementada
actualizado: 2026-09-14
tags: [estaciones, ruteo, cocina, solid]
---

# SPEC-005 — Estaciones y Ruteo

> [!success] Estado: Implementada — ruteo y tablero verificados; revisada y corregida 2026-09-14
> Ver **Estado de implementacion** al final. El cronometro, el aviso sonoro y el aviso al
> admin por categoria sin asignar **no** estan construidos — son UX/diseño, pendientes a
> proposito para la siguiente etapa del proyecto.

## Proposito

Que un pedido se reparta automaticamente entre los puestos de preparacion que le
corresponden, y que cada estacion vea solo lo suyo.

## Alcance

- Definicion de estaciones configurables
- Ruteo de items a estaciones segun su categoria
- Tablero de comandas por estacion
- Estados de la comanda

## Fuera de alcance

- Impresion de comandas (**explicitamente descartado**: todo por mensajes en la app)
- Gestion de inventario o insumos
- Asignacion de cocineros a comandas

## Comportamiento

### Ruteo

Si el cliente pide *carne* y *helado*, la carne llega a **cocina** y el helado a **postres**.

1. Cada item del menu pertenece a una **categoria**
2. Cada categoria se asigna a una **estacion**
3. Al confirmar el pedido, un componente distribuidor lo divide en **comandas**, una por
   estacion involucrada
4. Cada estacion recibe unicamente su comanda

Categorias y estaciones son **100% configurables**. Crear una estacion nueva o mover una
categoria de una estacion a otra es **configuracion, jamas cambio de codigo**.

Debe existir una **estacion por defecto** para categorias sin asignar, y el sistema avisa
al administrador cuando algo cae ahi.

### Diseno del distribuidor (SOLID)

- **Responsabilidad unica** — el distribuidor *solo* divide el pedido en comandas. No lo
  guarda, no notifica, no imprime.
- **Abierto/cerrado** — agregar una estacion o cambiar el ruteo se hace por configuracion;
  el distribuidor no se modifica.
- **Inversion de dependencias** — el distribuidor depende de una abstraccion de "regla de
  ruteo", no de una lista fija de estaciones escrita en codigo.
- **Sustitucion** — deben poder convivir varias estrategias de ruteo (por categoria, por
  tipo de plato, mixta) sin romper el flujo.

### Tablero de estacion

- Pantalla principal: **tablero de tarjetas (cards)** con las comandas esperando
- Tres columnas: **Nuevas / En preparacion / Listas**
- Se abre una card, se ve el pedido completo con sus especificaciones
- Dos acciones: **"Atras"** (volver) y **"Listo"** (terminar y notificar)
- **Cronometro visible por card** con color que envejece: verde <10 min, amarillo 10-20,
  rojo >20 (umbrales configurables)
- Aviso sonoro corto al entrar una comanda nueva

## Implementacion (2026-08-25)

`backend/estaciones/`: modelos `Estacion` y `Comanda`, mas `menu.Categoria.estacion` (FK
nula = estacion por defecto) y `pedidos.DetallePedido.comanda`.

- **`ruteo.py`** — `rutear_pedido(pedido)`, llamada dentro de la misma transaccion que
  `ConfirmarPedidoView`. Agrupa los `DetallePedido` por la estacion de su categoria y crea
  una `Comanda` por estacion involucrada. **Rutea solo lo que falta por rutear**, reusando
  las comandas existentes: asi es idempotente de verdad y ademas sirve al ruteo incremental
  de [[SPEC-011 - Novedades sobre Pedidos Enviados]] (un plato agregado a un pedido en curso
  tiene que llegar a su estacion). Antes salia con `if pedido.comandas.exists(): return`, y
  un plato agregado despues **no llegaba nunca a cocina** — corregido 2026-08-27
- **`GET /api/comandas/?estacion=<id>`** — el tablero de una estacion
- **`POST /api/comandas/<id>/en-preparacion/`** y **`.../lista/`** — transiciones, con
  timestamp (`en_preparacion_desde`, `lista_desde`) para las metricas de
  [[ADR-004 - LISTO y ENTREGADO son estados distintos]]
- **`frontend/src/views/estacion/EstacionTablero.vue`** — tres columnas, selector de
  estacion, card → detalle → "Atras"/"Listo"

> [!note] Simplificacion consciente sobre SOLID
> El distribuidor cumple responsabilidad unica y abierto/cerrado en la practica (agregar
> una estacion o mover una categoria es config, no codigo). **No** se construyo una capa
> de abstraccion de "estrategia de ruteo" intercambiable (Strategy pattern) — hoy solo
> existe una estrategia (por categoria) y anadir esa capa sin una segunda estrategia real
> que la necesite habria sido sobre-ingenieria. Si aparece una segunda estrategia, ese es
> el momento de extraer la abstraccion, no antes.

## Estado de implementacion

| Pieza | Estado |
|---|---|
| Ruteo por categoria → estacion | **Hecho y verificado**: pedido con items de cocina y bar genero 2 comandas |
| Tablero de estacion (3 columnas, card → detalle → Listo) | **Hecho** |
| Estacion por defecto para categorias sin asignar | **Hecho** (el fallback funciona) |
| Aviso al admin cuando algo cae en la estacion por defecto | Pendiente |
| Cronometro con color que envejece | **Hecho** (2026-08-25): verde <10min, ambar 10-20, rojo >20 |
| Aviso sonoro al entrar comanda nueva | Pendiente — es diseño/UX |
| Bloqueo para que dos personas no tomen la misma comanda | **Hecho** (2026-09-14) — la fila se bloquea y el estado se revisa dentro de la transaccion (ADR-008); la segunda toma recibe 409 y el tablero lo explica |
| Unificar estaciones | **Hecho** (2026-09-14, [[SPEC-023 - Promociones]]) — parametro `estaciones-unificadas` en Configuracion → Operacion: en Si, todo llega a la estacion por defecto. No toca la estacion de cada categoria, asi que apagarlo devuelve el ruteo de antes |
| Productos sin categoria (promociones) | **Hecho** (2026-09-14) — van enteros a la estacion por defecto, con su desglose en la tarjeta |

## Criterios de aceptacion

- [x] Un pedido con items de 3 categorias distintas genera 3 comandas en 3 estaciones —
      **verificado con 2** (cocina + bar); el mismo mecanismo cubre una tercera
- [x] Cada estacion ve solo sus comandas — **verificado**: el tablero filtra por `estacion`
- [x] Crear una estacion nueva no requiere tocar codigo — es una fila en `Estacion`
- [x] Mover una categoria de cocina a bar se refleja en el siguiente pedido — cambia
      `Categoria.estacion`, sin tocar el ruteador
- [x] Una categoria sin estacion asignada cae en la estacion por defecto — **verificado en
      el fallback**; el aviso al admin no esta implementado
- [x] Marcar "Listo" en una comanda notifica al mesero dueno del pedido — **verificado de
      punta a punta**, ver [[SPEC-006 - Notificaciones]]
- [x] El cronometro cambia de color segun los umbrales — **verificado 2026-08-25**:
      comandas de 20 y 22 minutos se pintaron en rojo. **Matiz:** los umbrales estan fijos
      en codigo (10/20 min), la spec pedia que fueran configurables — pendiente
- [x] Dos personas de la misma estacion no pueden tomar la misma comanda a la vez —
      **corregido 2026-09-14**. Antes no habia bloqueo: dos "Empezar" simultaneos
      respondian 200 los dos. Ahora `en-preparacion` y `lista` bloquean el pedido y la
      comanda ([[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]) y rechazan con
      409 lo que ya se hizo; el tablero muestra el motivo y se recarga. De paso, un "Listo"
      repetido ya no avisa dos veces al mesero. Pruebas con hilos simultaneos en
      `backend/pedidos/tests.py`

## Dependencias

- [[SPEC-004 - Modulo Mesero]] — quien confirma y dispara el ruteo
- [[SPEC-006 - Notificaciones]] — que pasa al marcar Listo
- [[SPEC-007 - Administracion y Parametrizacion]] — donde se configuran estaciones
