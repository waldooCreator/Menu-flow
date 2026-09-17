---
tipo: spec
id: SPEC-024
estado: implementada
actualizado: 2026-09-16
tags: [caja, libro, turnos, cuadre, filtros, busqueda]
---

# SPEC-024 — Búsqueda en el Libro e Historial de Turnos

> [!success] Estado: Implementada — pedida, aprobada y construida el 2026-09-16
> Sale de la revisión del sistema que hizo el autor ese día (hallazgos #4 y #5). Amplía
> [[SPEC-014 - Turno de Caja y Cajas de Fondos]]; no cambia ninguna de sus reglas.

## Propósito

Encontrar rápido un movimiento o un turno concreto cuando ya hay meses de historia: la
venta de $100.000 que el cliente reclama, el gasto que nadie recuerda o los turnos que
cerraron con faltante.

## El problema real

El autor lo encontró así:

> *"En Libro no existen maneras de buscar una factura específica. Si sabemos que una
> factura fue de 100.000 pesos, debería permitir buscar por valor, o por rango de
> valores."*
>
> *"Cuando hay muchos turnos cerrados debería permitir verlos en un histórico, con filtros
> de fechas, de nombres, de descuadres, sobrantes…"*

Lo que había:

- **Libro:** filtraba solo por fechas, caja y si entró o salió. Mostraba como máximo 300
  movimientos y no había forma de ver los siguientes.
- **Turnos:** traía los últimos 100, sin filtros, más una casilla "solo los que no
  cuadraron" que filtraba sobre esos 100. El turno 101 no se podía ver nunca.

## Alcance

### Libro

- Buscar por **valor exacto** y por **rango de valores** (desde / hasta)
- Buscar por **texto**: la descripción del movimiento o el **número de tiquete** de la venta
- Filtrar por **concepto** (venta, gasto, traslado, fondo inicial, anulación…)
- Filtrar por **quién lo registró**
- Mostrar el número de tiquete en los movimientos de venta
- **Cargar más**: ver todo lo filtrado, de a tandas, sin tope fijo

### Historial de turnos

- Filtrar por **rango de fechas**
- Filtrar por **persona**: a nombre de quién estaba el turno y quién lo cerró
- Filtrar por **estado**: abiertos, cerrados o todos
- Filtrar por **cuadre**: cuadró, con **faltante**, con **sobrante** o sin contar
- Filtrar por **tamaño de la diferencia**: "diferencias de $X o más"
- **Ordenar**: más recientes, mayor faltante o mayor sobrante
- **Resumen del filtro**: cuántos turnos hay, cuántos con faltante y cuánto suman, y
  cuántos con sobrante y cuánto suman
- **Cargar más**, sin tope fijo

## Fuera de alcance

- **Editar o borrar** movimientos o turnos. Siguen siendo solo inserción (SPEC-014, regla 3)
- **Exportar** el libro o los turnos a Excel. Para las ventas ya existe el Excel de
  [[SPEC-015 - Historial de Ventas]]; si hace falta para el libro, se decide después
- **Búsqueda de facturas con todos sus datos** (mesa, mesero, hora). Eso ya lo hace la
  pantalla **Ventas** (SPEC-015). El libro busca **movimientos de dinero**; una venta
  aparece ahí como un ingreso con su tiquete
- Dar el historial de turnos al cajero. Sigue siendo **solo del administrador**: quien
  maneja la plata no audita su propio cuadre (SPEC-014)

## Comportamiento

### 1. Libro: los filtros

Arriba quedan los filtros de siempre (fechas, caja, entró o salió) y el botón **Hoy**.
Debajo, un botón **"Más filtros"** abre el resto, para no llenar la pantalla del teléfono
con campos que casi nunca se usan:

| Filtro | Cómo funciona |
|---|---|
| **Valor exacto** | Solo movimientos de ese monto exacto. Con valor exacto no se usan el mínimo ni el máximo |
| **Valor desde / hasta** | Rango inclusivo. Se puede poner solo uno de los dos |
| **Buscar** | Texto libre. Encuentra movimientos cuya descripción lo contiene, sin distinguir mayúsculas ni tildes, **o** cuya venta tiene ese número de tiquete: "Ef-2026-00123", "00123" o "123" |
| **Concepto** | Venta, anulación, gasto, traslado, fondo inicial, saldo inicial, retiro al cierre, diferencia de arqueo u otro |
| **Registró** | La persona que registró el movimiento |

- Mientras "Más filtros" está cerrado, el botón dice cuántos hay puestos: **"Más filtros
  (2)"**. Así nadie se confunde cuando la lista sale más corta de lo esperado.
- **Quitar filtros** limpia todos, los visibles y los ocultos.
- El texto se busca al dejar de escribir, no con cada letra.
- Los **totales** (entró, salió, neto) siguen siendo del **filtro completo**, no de lo que
  cabe en pantalla.

### 2. Libro: cargar más

- Se muestran los primeros **100** movimientos del filtro.
- Si hay más, al final aparece **"Cargar 100 más (quedan N)"**.
- Arriba se lee cuántos se ven de cuántos: "Mostrando 100 de 437".

### 3. Historial de turnos: los filtros

En **Administración → Turnos**:

| Filtro | Cómo funciona |
|---|---|
| **Desde / hasta** | Por la fecha en que **se abrió** el turno. Un turno de noche que cierra de madrugada pertenece al día en que empezó |
| **A nombre de** | La persona responsable del turno |
| **Cerrado por** | Quien lo cerró. Sirve para encontrar los turnos que cerró alguien distinto del responsable |
| **Estado** | Todos, abiertos o cerrados |
| **Cuadre** | Todos, **cuadró** (diferencia 0), **faltó** (negativa), **sobró** (positiva) o **sin contar** (todavía no tiene conteo) |
| **Diferencia de** | Un monto: deja solo los turnos cuya diferencia, en valor absoluto, es de ese monto o más |
| **Ordenar** | Más recientes primero, mayor faltante primero o mayor sobrante primero |

La diferencia es la misma de siempre: **contado − esperado en efectivo de ese turno**
(SPEC-014). No se recalcula de otra forma para filtrar: el turno que la tabla muestra con
"Faltó $20.000" es el mismo que aparece al filtrar por faltante.

### 4. Historial de turnos: resumen y cargar más

Encima de la tabla, del **filtro completo**:

> **48 turnos** · **7 con faltante** por $86.000 · **3 con sobrante** por $12.500

- Se muestran los primeros **25**, con **"Cargar 25 más (quedan N)"**.
- Se quita la casilla "Solo los que no cuadraron": la reemplaza el filtro de cuadre.

## Reglas

1. **Todo se filtra en el servidor**, sobre la base completa. Nunca sobre lo que ya llegó a
   la pantalla: filtrar 100 filas descargadas fue justo el defecto del historial anterior.
2. **Los totales y el resumen son del filtro completo**, no de la tanda visible.
3. **La diferencia de un turno se calcula igual en la tabla y en el filtro**, con una sola
   definición en el servidor.
4. **Nada se edita.** Buscar no abre ninguna puerta para cambiar un movimiento.
5. **Permisos de siempre:** el libro, quien puede cobrar; el historial de turnos, solo el
   administrador. También desde la API.

## Criterios de aceptación

### Libro

- [x] Buscar el valor exacto **100000** trae solo movimientos de $100.000
- [x] Un rango de 50.000 a 150.000 trae los de 50.000 y los de 150.000 (inclusivo), y no los
      de 49.999 ni 150.001
- [x] Poner solo "valor desde" funciona sin tope, y solo "valor hasta", sin piso
- [x] Buscar "proveedor" encuentra un gasto con descripción "Pago al Proveedor de gas"
- [x] Buscar "cafe" encuentra "Café para la cocina": sin distinguir tildes ni mayúsculas
- [x] Buscar el número de tiquete de una venta ("Ef-2026-00123" y también "123") encuentra
      su movimiento de ingreso
- [x] Los movimientos de venta muestran su número de tiquete
- [x] Filtrar por concepto **gasto** trae solo gastos
- [x] Filtrar por quién registró trae solo sus movimientos
- [x] Los totales cambian con los filtros y son del filtro completo, no de los 100 visibles
- [x] Con 250 movimientos se ven 100, y "Cargar más" trae los siguientes hasta verlos todos
- [x] "Más filtros" cerrado muestra cuántos filtros ocultos hay puestos
- [x] "Quitar filtros" limpia también los ocultos
- [x] Quien no puede cobrar recibe 403, también desde la API

### Historial de turnos

- [x] Un turno número 101 o más viejo **se puede encontrar** (antes había tope de 100)
- [x] El filtro de fechas usa la fecha de apertura
- [x] "A nombre de" trae solo los turnos de esa persona
- [x] "Cerrado por" trae los turnos que cerró esa persona, aunque no fueran suyos
- [x] "Faltó" trae solo diferencias negativas, "Sobró" solo positivas, "Cuadró" solo cero y
      "Sin contar" solo los que no tienen conteo
- [x] "Diferencia de $10.000 o más" incluye un faltante de $15.000 y un sobrante de $10.000,
      y deja fuera uno de $5.000
- [x] "Mayor faltante primero" pone arriba el faltante más grande
- [x] El resumen (cantidad, faltantes y sobrantes con sus sumas) es del filtro completo
- [x] La diferencia que muestra la tabla es la misma con la que se filtró
- [x] Con 60 turnos se ven 25, y "Cargar más" trae los siguientes
- [x] Un cajero recibe 403 en el historial, también desde la API

### Ambas pantallas

- [x] Sin desborde horizontal en 320 y 375 px, y todo lo tocable mide 44 px o más
      ([[SPEC-022 - Auditoria Responsive]])

> [!note] Cómo se verificó (2026-09-16)
> - **15 pruebas** en `backend/ventas/tests.py` (`BusquedaLibro`, `HistorialTurnos`), contra
>   PostgreSQL real: valores exactos y rangos en sus bordes, texto sin tildes, las tres
>   formas del tiquete, tandas de 100 y de 25, el turno 106 encontrado, y que la diferencia
>   filtrada sea la misma de `cuadre_de`.
> - **En el navegador** con la base de desarrollo: "Más filtros" en teléfono con un rango
>   desde $100.000, y el historial con su resumen ("5 turnos · 2 con faltante por $17.600").
> - **Medido** a 1366, 375 y 320 px: desborde 0, texto cortado 0, toques bajo 44 px 0.

## Dependencias

- [[SPEC-014 - Turno de Caja y Cajas de Fondos]] — el libro, los turnos y la definición del cuadre
- [[SPEC-016 - Tiquete de Venta]] — el número de tiquete que se busca
- [[SPEC-020 - Activos Liquidos]] — los conceptos de gasto, saldo inicial y retiro al cierre
- [[SPEC-022 - Auditoria Responsive]] — medidas mínimas en teléfono

## Plan de implementación

### Paso 1 — Libro en el servidor

- `GET /api/movimientos/`: nuevos parámetros `monto`, `monto_min`, `monto_max`, `q`,
  `autor`, `limite` y `desde_fila`. Responde también `hay_mas`, las personas que han
  registrado movimientos (para el selector) y el número de tiquete de cada venta
- La búsqueda sin tildes usa `unaccent` de PostgreSQL. La extensión se activa en una
  migración
- Un número de tiquete se busca por su parte numérica (`tiquete_numero`), así funcionan
  "Ef-2026-00123", "00123" y "123"

### Paso 2 — Turnos en el servidor

- `GET /api/turnos/`: parámetros `desde`, `hasta`, `responsable`, `cerrado_por`, `estado`,
  `cuadre`, `diferencia_min`, `orden`, `limite` y `desde_fila`
- La diferencia se **anota en la consulta** (subconsulta sobre los movimientos en efectivo
  del turno) para filtrar y ordenar en la base. `cuadre_de` y la anotación usan la misma
  definición, y una prueba comprueba que coinciden
- Responde el resumen del filtro, `hay_mas` y las personas para los selectores

### Paso 3 — Pantallas

- `MeseroLibro`: "Más filtros" con su contador, búsqueda que espera a que se deje de
  escribir, tiquete en las ventas y "Cargar más"
- `AdminTurnos`: filtros, resumen y "Cargar más"
- Medir a 320 y 375 px
