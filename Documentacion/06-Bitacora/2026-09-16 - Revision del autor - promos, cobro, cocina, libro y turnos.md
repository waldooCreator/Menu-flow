---
tipo: bitacora
fecha: 2026-09-16
tags: [revision, promociones, cobro, estaciones, libro, turnos, spec-023, spec-014, spec-024]
---

# 2026-09-16 — Revisión del autor: promos, cobro, cocina, libro y turnos

## Qué pasó

El autor abrió el sistema, lo recorrió y trajo cinco hallazgos. Todos quedaron resueltos
el mismo día, primero en las specs y después en el código.

| # | Hallazgo del autor | Qué se hizo | Spec |
|---|---|---|---|
| 1 | *"La franja de color de las promos se ve muy mal"* | Las promos van sobre el fondo del menú, con el mismo título y la misma tarjeta que un plato. Las distingue una insignia **"★ Promo"** y un **halo de acento que respira despacio** alrededor de la foto; con `prefers-reduced-motion` el halo queda quieto | [[SPEC-023 - Promociones]] §3 |
| 2 | *"¿Cómo configuro que solo caja cobre, o meseros y caja?"* | Ya existía, pero escondido en el grupo **Contacto** y escrito a mano. Ahora está en **Configuración → Cobro** (con propina e impuesto), se elige **Sí/No** y dice debajo qué pasa en cada caso | [[SPEC-014 - Turno de Caja y Cajas de Fondos]] |
| 3 | *"Que cocina no tenga que desplazarse a postres o bar: que todo le llegue al mismo dashboard, o dividido, desde configuración"* | El interruptor **Unificar estaciones** ya ruteaba todo a cocina, pero el tablero seguía mostrando una estación a la vez. Ahora, con Sí, el tablero junta las comandas de todas las estaciones, sin selector, y cada tarjeta dice de cuál viene. Administración → Estaciones dice en qué modo está | [[SPEC-023 - Promociones]] §7 |
| 4 | *"En Libro no se puede buscar una factura de $100.000"* | **Más filtros**: valor exacto, rango, texto sin tildes o número de tiquete, concepto y quién lo registró. El número de tiquete se ve en cada venta. **Cargar más** en lugar del tope de 300 | [[SPEC-024 - Busqueda en Libro e Historial de Turnos]] |
| 5 | *"Ver los turnos cerrados en un histórico, con filtros de fechas, nombres, descuadres y sobrantes"* | Filtros por fechas, a nombre de quién, quién cerró, estado, cuadre (faltó, sobró, cuadró, sin contar), diferencia mínima y orden. Resumen del filtro y **Cargar más**. Antes solo se veían los últimos 100 | [[SPEC-024 - Busqueda en Libro e Historial de Turnos]] |

## Decisiones técnicas

- **Historial de turnos filtrado en la base.** La diferencia de cada turno se anota con
  una subconsulta (`ventas/busqueda.py`, `con_diferencia`) para poder filtrar y ordenar
  sin calcular turno por turno. Es la misma cuenta de `cuadre_de`, y **una prueba
  comprueba que las dos dan el mismo número**.
- **Búsqueda sin tildes con `unaccent` de PostgreSQL**, activado en una migración
  (`ventas/0008_unaccent`). **Para producción:** el usuario de la base debe poder crear
  extensiones, o hay que crearla a mano una vez. Anotado para la spec de despliegue.
- **El número de tiquete se busca por su parte numérica**, así "Ef-2026-00123", "00123" y
  "123" encuentran la misma venta.
- **El parámetro de cobro conserva su valor.** La migración `configuracion/0007` convierte
  lo que estaba escrito ("si", "No ", "false"…) a Sí/No, y se probó con esos casos.
- **Los textos nuevos de la tarjeta de promo** ("Promo", "Ver qué incluye") salen de la
  configuración, como todo texto de la página pública.

## Lo que salió al construir

> [!bug] "Cargar más" podía repetir o saltarse movimientos
> El libro se ordenaba solo por fecha. Dos movimientos del mismo instante (un traslado crea
> dos) no tienen orden fijo, y al pedir la siguiente tanda la base podía devolver uno repetido
> y dejar otro sin mostrar. La prueba con 250 movimientos lo destapó en la suite completa
> (194 distintos en vez de 250) y no al correrla sola: por eso no apareció antes. Se
> desempata por id, en el libro y en los turnos.

- **La pantalla de Configuración no mostraba la ayuda de ningún parámetro.** Se agregó
  debajo de cada nombre, para todos. Sin eso, "Los meseros también pueden cobrar" no
  aclaraba que caja cobra siempre.
- **El tablero pedía todas las comandas, incluidas las ya entregadas**, y la API devuelve
  máximo 100: con estaciones unificadas, las nuevas podían quedar fuera. Ahora pide solo las
  que están en curso (`?activas=1`).
- **El puerto 8000 lo tenía otro proyecto del autor.** Sin darse cuenta, el frontend habría
  hablado con el backend equivocado. El backend de este proyecto corre ahora en el
  **8001**, y `vite.config.js` toma la dirección de `BACKEND_URL` (por defecto sigue siendo el
  8000). Está en `.claude/launch.json`.

## Cómo se comprobó

- **Pruebas nuevas:** 15 de SPEC-024 en `ventas/tests.py`, 2 de cobro en `nucleo/tests.py`
  (incluida la migración) y 1 del tablero unificado en `pedidos/tests.py`.
- **Capturas sin ventana (Playwright)** con la base de desarrollo, porque el panel del
  navegador de la app no dibujaba: menú del cliente, Libro con filtros, Turnos,
  Estaciones, Configuración y tablero, a **1366, 375 y 320 px**. **Desborde 0, texto
  cortado 0, toques bajo 44 px 0** en las 18 combinaciones.
- **Tablero:** con el interruptor en No se ve el selector; en Sí desaparece. El parámetro
  quedó otra vez en **No**. En la base de desarrollo no había comandas del bar en curso,
  así que la etiqueta "Bar" en la tarjeta se comprobó con la prueba automática, no en
  pantalla.

## Después: pedido cobrado que no salía nunca de "Pedidos"

> [!bug] Un pedido pagado quedaba en bucle
> Reportado por el autor. El pedido #259 (Mesa 5) se cobró con cocina en "listo". Al cobrar
> la mesa se libera y la cuenta desaparece de **Cuentas**, pero el pedido seguía activo
> porque nadie lo marcó entregado, y en la pantalla **Pedidos** no había cómo hacerlo: solo
> se podía desde la campana del mesero que lo tomó. Además salía marcado como "sin mesa".

**Corrección** (dentro de SPEC-012, *cualquier mesero entrega cualquier pedido*): la lista de
pedidos trae `cobrada`; cada tarjeta muestra **Pagado** y un botón **Marcar entregado**; un
pedido pagado ya no se marca como huérfano ni se ofrece editar.

**Limpieza para la prueba completa:** cero pedidos en curso, cero cuentas abiertas, cero
turnos abiertos, mesas libres. Nada se borró: lo pendiente se entregó o se anuló con motivo.
