---
tipo: spec
id: SPEC-018
estado: implementada
actualizado: 2026-09-07
tags: [ventas, reportes]
---

# SPEC-018 — Reportes de Venta

> [!success] Estado: Implementada — verificada el 2026-09-07

## Proposito

Responder las preguntas que un dueño se hace al cerrar la semana: que se vende,
quien vende, como va el ticket promedio y a que horas llega la gente.

## Alcance

Cinco reportes, en **una sola pantalla** con un rango de fechas compartido
(el quinto, clientes frecuentes, se sumo el 2026-09-07 con [[SPEC-019 - Clientes]]):

| Reporte | La pregunta que responde |
|---|---|
| **Productos mas vendidos** | ¿Que plato mueve el negocio? |
| **Ventas por mesero** | ¿Quien esta vendiendo? |
| **Ticket por dia** | ¿Como evoluciona la venta y el ticket promedio? |
| **Hora y dia de mayor demanda** | ¿Cuando necesito mas gente en el turno? |
| **Clientes frecuentes** | ¿Quienes vuelven, y cuanto valen? |

> [!note] Ampliado el 2026-09-14 por [[SPEC-023 - Promociones]]
> - **Como se vende un producto**: se elige una promocion o cualquier plato y se ven sus
>   unidades e ingresos del rango, agrupados por dia, semana o mes, en grafica y tabla. Va
>   por **id de plato**, no por nombre congelado, para que un producto renombrado no parta
>   su historia en dos. `GET /api/reportes/producto/`.
> - **Solo promociones**: filtro del ranking de productos mas vendidos.

## Fuera de alcance

- **Ingredientes mas usados** — descartado: Springfield no usa recetas ni
  inventario (comprobado en produccion el 2026-09-07)
- ~~**Clientes frecuentes**~~ — **ya no esta fuera de alcance.** Dependia del
  modulo de Clientes, que se implemento el 2026-09-07: es el quinto reporte de
  la pantalla. Ver [[SPEC-019 - Clientes]]
- Exportar los reportes: para eso esta el Excel del historial (SPEC-016)

## Comportamiento

### Una pantalla, un rango, cuatro respuestas

Los cuatro reportes comparten el mismo filtro de fechas y se piden en **una
sola llamada**. Cuatro llamadas para una sola pantalla seria trabajo
desperdiciado, y ademas dejaria ver los graficos apareciendo desordenados.

Atajos de fecha iguales a los del historial: **Hoy · Esta semana · Este mes ·
Este año**, mas rango a mano.

### Que cuenta como venta

Solo las cuentas **cerradas**. Las anuladas no suman: una venta que se devolvio
no se vendio. Los pedidos anulados dentro de una cuenta tampoco.

### La atribucion al mesero

Se atribuye al **mesero que tomo el pedido**, no a quien cobro. Una mesa
atendida por dos meseros reparte su venta entre los dos, renglon por renglon —
atribuir la cuenta completa a uno solo seria mentir sobre el trabajo del otro.

Se reporta el **subtotal** (la comida), no el total: la propina no es venta del
mesero, es propina, y el impuesto no es de nadie.

### Los graficos

Con Chart.js, usando **los colores del tema del restaurante**, no una paleta
generica: la misma instalacion en otro restaurante debe verse con SUS colores
(regla de parametrizacion del proyecto).

| Reporte | Grafico | Por que ese |
|---|---|---|
| Productos mas vendidos | Barras horizontales | Los nombres de plato son largos; horizontal se leen |
| Ventas por mesero | Barras horizontales | Comparar personas es comparar longitudes |
| Ticket por dia | Linea | Es evolucion en el tiempo |
| Hora de mayor demanda | Barras verticales | Las 24 horas son una secuencia natural |
| Dia de la semana | Barras verticales | Siete categorias ordenadas |

Cada grafico va acompañado de **su numero mas importante en texto**, porque un
grafico sin cifra obliga a estimar a ojo.

### En pantalla angosta el grafico se RECONFIGURA, no solo se encoge

> [!important] Correccion del autor (2026-09-07)
> La primera version no era responsive. Se habia comprobado que no hubiera
> desborde horizontal, **pero eso no es lo mismo que verse bien**.

Lo que estaba mal y se corrigio:

| Problema | Correccion |
|---|---|
| **Las barras horizontales no mostraban el nombre** — solo barras sueltas | Era un bug: el callback del eje devolvia `undefined`, y en Chart.js eso **oculta** la etiqueta |
| Cifras de siete digitos en el eje, rotadas en diagonal | Se abrevian: `$1,5M`, `$500k` |
| 24 etiquetas de hora encimadas | Se muestran 6, sin rotacion |
| Nombres largos de plato desbordando | Se recortan con `…`; el completo sale en la etiqueta flotante |
| Los cuatro atajos partidos en dos filas de botones enormes | Una sola linea que se desliza |
| Desde/Hasta apilados, media pantalla desperdiciada | Dos columnas desde el telefono |
| Graficos en una columna hasta 1024 px | Dos columnas desde 768 px |

El componente mide **su propio contenedor**, no la ventana: el mismo grafico
puede estar en una columna angosta dentro de una pantalla ancha, y ahi tambien
tiene que reconfigurarse.

### Cuando no hay datos

Cada reporte dice que no hay datos en ese rango, en vez de mostrar un grafico
vacio que parece roto.

## Reglas

1. **Solo cuentas cerradas.** Las anuladas nunca suman.
2. **El mesero es quien tomo el pedido**, no quien cobro.
3. **Se reporta subtotal**, no total: la propina no es venta.
4. Los totales son del **rango filtrado completo**.
5. Los colores salen del **tema del restaurante**, nunca fijos en el codigo.

## Criterios de aceptacion

- [x] Una sola llamada trae los cuatro reportes
- [x] Las cuentas **anuladas no suman** en ninguno
- [x] Los pedidos anulados dentro de una cuenta cerrada **tampoco suman**
- [x] Una mesa atendida por dos meseros **reparte** su venta entre ambos
- [x] El reporte por mesero usa **subtotal**, sin propina
- [x] Los atajos Hoy / Esta semana / Este mes / Este año funcionan
- [x] Cada grafico muestra **su cifra principal** en texto
- [x] Un rango sin ventas muestra un mensaje, **no un grafico vacio**
- [x] Los colores salen de los tokens del tema
- [x] Quien no puede cobrar **no ve** esta pantalla
- [x] Sin desborde horizontal en 375 px
- [x] Las barras horizontales **muestran el nombre** de cada categoria
- [x] Los montos del eje se **abrevian** en pantalla angosta
- [x] Las etiquetas del eje **no se rotan** en diagonal
- [x] Los atajos caben en **una sola fila** en telefono
- [x] Desde/Hasta van **lado a lado**, no apilados
- [x] Dos columnas de graficos desde **768 px**

## Plan de implementacion

### Paso 1 — Backend: un endpoint, cuatro reportes (medio dia)

`GET /api/reportes/?desde=&hasta=` devuelve `resumen`, `productos`, `meseros`,
`por_dia`, `por_hora` y `por_dia_semana`.

Todo con agregaciones en la base (`Sum`, `Count`, `TruncDate`, `ExtractHour`),
nunca sumando en Python: con miles de ventas, traerlas todas a memoria para
sumarlas seria lento sin necesidad.

**Tests primero**, los del bloque de criterios.

### Paso 2 — Pantalla con Chart.js (medio dia)

`/mesero/reportes`, con los atajos de fecha arriba, las cifras principales en
tarjetas y los graficos debajo. Los colores se leen de las variables CSS del
tema en tiempo de ejecucion.

### Paso 3 — Comprobacion (2 horas)

Con datos realistas y clics reales: cada atajo, el caso sin datos, y 375 px.

**Total estimado: dia y medio.**

## Dependencias

- [[SPEC-013 - La Cuenta]] — la venta es una cuenta cerrada
- [[SPEC-015 - Historial de Ventas]] — el patron de filtros y totales
- [[SPEC-007 - Administracion y Parametrizacion]] — los colores del tema
