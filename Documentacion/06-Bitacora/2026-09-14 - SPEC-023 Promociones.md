---
tipo: bitacora
fecha: 2026-09-14
tags: [promociones, menu, cocina, reportes, estaciones, spec-023]
---

# 2026-09-14 — SPEC-023: Promociones

## Qué se hizo

Se escribió, aprobó e implementó [[SPEC-023 - Promociones]] el mismo día. Un restaurante
ya puede vender combos con precio propio ("2 hamburguesas, perro, helado y gaseosa por
$50.000") que se encienden y se apagan solos por fecha, día y franja horaria.

| Parte | Qué quedó |
|---|---|
| **Panel** | Sección *Promociones* en Menú. Tipo *Plato* o *Promoción* al crear. Componentes libres (cantidad, nombre, especificación) que se reordenan. Fechas, días y franja, con el estado calculado a la vista: vigente, programada, fuera de horario, vencida, apagada o agotada |
| **Cliente** | Sección de primera, en una banda con el color de marca y chip destacado en los filtros. Al tocar una promo se abre lo que incluye, con los ingredientes. Entrada breve al cargar; con `prefers-reduced-motion`, sin animación |
| **Mesero** | Las promos vigentes también salen de primeras en el Camino B |
| **Cocina** | La tarjeta muestra el combo y **debajo lo que incluye, ya multiplicado** por la cantidad de combos |
| **Reportes** | *Cómo se vende un producto*: una promo o cualquier plato, con unidades e ingresos por día, semana o mes. Filtro *Solo promociones* en el ranking |
| **Configuración** | *Unificar estaciones* (Sí/No): en Sí, todo llega a la estación por defecto. Los parámetros sí/no ahora se eligen con un selector, no se escriben |

## Lo que decidió el autor

- Componentes **libres**, no platos del menú, y cada uno con su especificación.
- El combo cuenta como **una unidad** en reportes.
- **Solo observaciones**, sin cambiar componentes, y una sola observación para todo el combo.
- **Todo el combo a cocina.** Además pidió poder **unificar o separar** cocina y bar desde
  Configuración.
- Una sola franja por promo, solo la foto de la promo, y en el tiquete solo el nombre.
- No revisar la sección de Promociones de Springfield: la spec bastaba.

## Decisiones técnicas

- **La promoción es un tipo de plato**, no un modelo aparte:
  [[ADR-009 - La promocion es un tipo de plato]]. Hereda sin código nuevo el precio
  congelado, el QR, la cuenta, el tiquete y las novedades.
- **Una sola regla de vigencia** en `menu/promociones.py`. La usan el menú, la firma, la
  verificación, la confirmación, las novedades y el panel.
- **Una franja que cruza medianoche pertenece al día en que empezó**: la 1:00 del sábado
  es la noche del viernes.
- **La API pública no deja ver promos programadas.** El panel pide `?todas=1`, que solo se
  respeta para el administrador.
- **El desglose se congela en la venta** (`DetallePedido.desglose_congelado`), igual que el
  nombre y el precio.
- **El reporte por producto va por id de plato**, no por nombre: una promo renombrada no
  parte su historia en dos.

## Lo que salió al construir

> [!bug] Bloquear un plato dejó de funcionar al permitir categoría nula
> El orden por defecto de `Plato` cruza con su categoría. Con la categoría nula, Postgres
> se niega a hacer `SELECT … FOR UPDATE` ("cannot be applied to the nullable side of an
> outer join"). Rompía la confirmación de pedidos y agotar desde cocina. Se corrigió con
> `select_for_update(of=("self",))` en las dos consultas, y quedó anotado en el ADR para
> las que vengan.

> [!bug] Guardar un plato con foto y métricas mandaba las métricas rotas
> Con foto, `guardarPlato` mandaba todo en multipart, y un formulario multipart no sabe
> enviar listas de objetos. Era un problema previo con las métricas, y habría pasado lo
> mismo con los componentes. Ahora los datos van como JSON y la foto en una segunda
> llamada que solo la lleva a ella.

- **Borrar un plato con ventas respondía 500.** Ahora responde 409 con qué hacer en su
  lugar: "apágala" o "márcalo agotado".
- **Cocina tenía que multiplicar.** Con 3 combos la tarjeta decía "2× Hamburguesa". Se vio
  en el recorrido y se cambió a "En total: 6× Hamburguesa". Anotado en la spec.
- **Los botones de los días medían 33 px** a 320 px de ancho. Pasaron a 4 columnas en
  teléfono.

## Cómo se comprobó

- **36 pruebas nuevas** en `backend/menu/tests.py`: vigencia con la hora fijada, panel,
  venta, cocina, estaciones unificadas y reportes.
- **Recorrido en el navegador** con la base de desarrollo, de punta a punta: crear una promo
  desde el formulario, verla en el menú, abrir su detalle, venderla, verla en cocina y
  filtrarla en Reportes.
- **Medido a 320 px**: sección de promos, detalle, formulario del panel, Reportes, Camino B y
  tarjeta de cocina. Desborde 0, texto cortado 0 y ningún toque bajo 44 px.

## Datos de demostración que quedaron en la base de desarrollo

- Tres promos: *Combo Parrillero* (hasta el 19 de septiembre), *Almuerzo ejecutivo* (lunes
  a viernes desde las 11:30) y *Noche de alitas* (programada, empieza en tres días).
- Un pedido de prueba: 3 combos en la **Mesa 12**, ya cobrado en Efectivo. La mesa quedó
  ocupada y la comanda está en cocina. Los pedidos no se borran: si estorba, se libera la
  mesa y se marca entregado.

> [!note] Otro proyecto en el puerto 5173
> Al probar, el puerto 5173 lo tenía otro proyecto del autor. El frontend de este sistema se
> levantó en el **5180** (`.claude/launch.json`).
