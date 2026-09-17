---
tipo: adr
id: ADR-009
estado: aceptada
fecha: 2026-09-14
specs: [SPEC-023, SPEC-005, SPEC-018]
tags: [menu, promociones, modelo-de-datos]
---

# ADR-009 — La promoción es un tipo de plato

**Estado:** Aceptada · **Fecha:** 2026-09-14

## Contexto

[[SPEC-023 - Promociones]] pide vender combos con precio propio y tiempo limitado. Un
combo se agrega al carrito, viaja en el QR, se confirma, llega a cocina, se cobra, se
agota y entra a los reportes. Todo ese camino ya existe para los platos, con reglas que
costó llegar a tener: precio congelado en la venta (SPEC-008), revalidación de
disponibilidad dentro de la transacción ([[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]),
ruteo a estaciones (SPEC-005) y novedades sobre pedidos en curso (SPEC-011).

El autor lo pidió así: *"que se trate como otro plato pero especial"*.

## Opciones consideradas

**A. Un modelo `Promocion` aparte.** Separa bien los campos de vigencia. Pero
`DetallePedido` apunta a `Plato`: habría que abrir un segundo camino (renglón de plato o
renglón de promo) en el QR, la confirmación, el ruteo, las novedades, la cuenta, el
tiquete y los reportes. Cada regla existente habría que duplicarla, y dos copias de la
misma regla terminan diciendo cosas distintas.

**B. Un campo `tipo` en `Plato`.** Una promoción es un plato con `tipo = promocion`, sin
categoría, con sus componentes en una tabla aparte y su vigencia en columnas propias. Todo
el camino de venta la trata como un plato; solo cambian los puntos donde la promo es
distinta de verdad.

**C. Una categoría especial "Promociones".** Casi sin código, pero la vigencia no tiene
dónde vivir, una categoría decide la estación (y el combo debe ir entero a cocina), y el
nombre de una categoría es texto editable: el sistema no podría distinguirla con
seguridad.

## Decisión

**B.** `Plato.tipo` (`plato` | `promocion`), `ComponentePromocion` para lo que incluye, y
en `DetallePedido` un `desglose_congelado` con lo que traía la promo al venderla.

## Justificación

- **Una sola regla de venta.** Se agregó `se_puede_vender(plato)` en
  `menu/promociones.py`, que para un plato es "está disponible" y para una promo, además,
  "está vigente". Los cuatro puntos que ya revisaban disponibilidad (firmar, verificar,
  confirmar, agregar como novedad) solo cambiaron qué función llaman.
- **La vigencia vive en un solo sitio.** `estado_promocion(plato, momento)` la usan el menú
  público, la confirmación y el panel.
- **La base impide lo inválido.** Restricciones `CheckConstraint`: un plato normal exige
  categoría, una promo no la tiene, la fecha de fin no es anterior a la de inicio y la
  franja va completa o vacía.
- **Los reportes ya sirven.** Un combo es una unidad de un producto, que es exactamente lo
  que decidió el autor.

## Consecuencias

**Positivas**
- La promo hereda sin código nuevo el precio congelado, el QR, la cuenta, el tiquete y las
  novedades.
- Borrar una promo vendida se protege solo (`PROTECT` desde `DetallePedido`).

**Negativas / a vigilar**
- `Plato` tiene columnas que en un plato normal no se usan (`activa`, fechas, días, horas).
  Es el costo de no duplicar el camino de venta.
- `categoria` pasó a ser nula, y el orden por defecto de `Plato` cruza con ella. Postgres no
  bloquea el lado nulo de un JOIN, así que **todo `select_for_update()` sobre `Plato` debe
  llevar `of=("self",)`**. Las dos consultas que existían se corrigieron. Una nueva sin eso
  falla en cuanto haya una promoción.
- La vigencia se filtra en Python al listar el menú, no en la consulta: depende de días y de
  una franja que puede cruzar la medianoche. Con decenas de promos no importa; con miles
  habría que reconsiderarlo.
- Un plato no se puede convertir en promoción ni al revés: cambiaría el significado de sus
  ventas pasadas.

## Enlaces

- [[SPEC-023 - Promociones]]
- [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[SPEC-018 - Reportes de Venta]]
