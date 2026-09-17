---
tipo: spec
id: SPEC-023
estado: implementada
actualizado: 2026-09-16
tags: [menu, promociones, cliente, cocina, reportes, estaciones]
---

# SPEC-023 — Promociones

> [!success] Estado: Implementada — revisada por el autor y corregida el 2026-09-16
> Construida el 2026-09-14. El 2026-09-16 el autor la reviso en pantalla y pidio dos
> cambios, ya hechos: la seccion de promos del cliente sin franja de color (seccion 3) y
> que con estaciones unificadas cocina vea todo en un solo tablero (seccion 7). Ver
> [[2026-09-16 - Revision del autor - promos, cobro, cocina, libro y turnos]].
>
> Historial: aprobada y construida el 2026-09-14
> Las cinco preguntas abiertas se cerraron ese mismo dia. Se agrego, a pedido del autor,
> el interruptor para **unificar o separar estaciones** (seccion 7). La decision de modelar
> la promocion como un tipo de plato esta en
> [[ADR-009 - La promocion es un tipo de plato]]. Detalle en la bitacora
> [[2026-09-14 - SPEC-023 Promociones]].

## Proposito

Que el restaurante pueda vender combos con precio propio y tiempo limitado
("dos hamburguesas, postre y gaseosa por $50.000"), que el cliente los vea
**antes que nada** en el menu y que el dueño sepa cuantos se venden y cuanto dejan.

## El problema real

La mayoria de restaurantes vive de promociones que duran unos dias: se activan hoy
y se quitan en quince, o solo valen de lunes a jueves al mediodia. Hoy el sistema
no tiene como representarlas. Para vender un combo habria que crear un plato
normal, perdido entre las categorias, encenderlo y apagarlo a mano y recordar
hacerlo a tiempo, y en los reportes quedaria mezclado con todo lo demas.

Springfield tiene una seccion "Promociones" en su panel
([[Comparativa Sidebar - Springfield vs Sistema Nuevo]]). Es una de las tres
secciones que faltan para reemplazarlo.

## Lo que decidio el autor (2026-09-14)

| Pregunta | Decision |
|---|---|
| ¿Que es una promocion? | Un **tipo de plato**. Se crea desde el mismo panel del menu, eligiendo "Promocion" en vez de plato normal, y se configura igual: nombre, foto, descripcion y precio |
| ¿Que incluye? | Una lista **libre**, que no sale de los platos del menu. Cada componente tiene su propia especificacion (por ejemplo, los ingredientes de la hamburguesa) |
| ¿Que ve el cliente? | La seccion de promociones **de primera** y resaltada. Al tocar una promo se abre todo su detalle: cada componente con su especificacion |
| ¿Que ve cocina? | **La promocion y el desglose** de lo que incluye |
| ¿Se puede cambiar algo del combo? | **No.** Solo se permiten observaciones ("sin cebolla") |
| ¿Cuanto dura? | Tiene **fechas** de inicio y fin, y ademas **horario**: dias de la semana y franja de horas |
| ¿Como se cuenta en reportes? | **El combo es la unidad.** 20 combos son 20 unidades de ese combo; no se reparten en hamburguesas ni gaseosas |
| ¿Donde se revisa? | En **Reportes**. Se puede filtrar una promocion, o **cualquier plato**, y ver cuantas unidades se vendieron y cuanto dejaron por dia, semana o mes |
| ¿A que estacion llega? | **Todo el combo a cocina** (la estacion por defecto), bebidas incluidas: los de cocina sacan tambien las bebidas |
| ¿Cocina y bar separados? | **Configurable.** Un interruptor en Configuracion unifica todas las estaciones en la de por defecto, o las deja separadas como hoy |
| ¿Foto por componente? | **No.** Solo la foto de la promo |
| ¿Observacion por componente? | **No.** Una observacion para todo el combo |
| ¿Varias franjas horarias? | **No.** Una sola franja por promo |
| ¿Que sale en el tiquete? | **Solo el nombre** de la promo |

## Alcance

- Tipo **Promocion** al crear un plato en el panel
- Componentes libres: nombre, cantidad y especificacion de cada uno
- Vigencia por fechas, dias de la semana y franja horaria, que se aplica sola
- Seccion **Promociones** primero en el menu del cliente, resaltada, solo si hay alguna vigente
- Detalle de la promo al tocarla, con cada componente y su especificacion
- La promo tambien aparece al armar un pedido desde cero (Camino B de
  [[SPEC-004 - Modulo Mesero]])
- La tarjeta de cocina muestra la promo con su desglose
- En **Reportes**: filtro por producto (promocion o plato) con unidades e ingresos
  agrupados por dia, semana o mes, y un filtro para ver solo promociones

## Fuera de alcance

- **Cambiar componentes** (gaseosa por jugo, papas por ensalada). Decidido por el autor
- **Componentes tomados del menu.** Son libres por decision del autor. Por eso una promo
  **no se agota sola** cuando se acaba un componente: se agota a mano (ver Reglas)
- **Descuentos sobre la cuenta** (10% los martes, 2x1 automatico, cupones). Una promocion
  aqui es un producto con precio propio, no una regla de descuento
- **"Ahorras $X"** o precio tachado. Los componentes no tienen precio, asi que no hay
  contra que comparar
- Promociones por cliente o por cantidad de visitas
- Repartir las ventas del combo entre sus componentes en los reportes. Decidido por el autor

## Comportamiento

### 1. Crear una promocion (administrador)

En el panel del menu, al crear un plato se elige el tipo: **Plato** o **Promocion**.
La promocion tiene los mismos campos de un plato (nombre, descripcion, precio, foto,
etiquetas, observaciones rapidas) y ademas:

**Componentes.** Una lista que se arma a mano, en el orden en que se quieren mostrar:

| Campo | Ejemplo |
|---|---|
| Cantidad | 2 |
| Nombre | Hamburguesa clasica |
| Especificacion | Pan brioche, carne de res 150 g, queso cheddar, tomate, lechuga, salsa de la casa |

Tiene que haber al menos un componente. La especificacion es opcional: "Gaseosa 400 ml"
no necesita mas.

**Estacion.** Una promo no pertenece a ninguna categoria y no se le elige estacion: el
combo entero llega a la **estacion por defecto** (cocina), bebidas incluidas
([[SPEC-005 - Estaciones y Ruteo]]).

**Vigencia.**

| Campo | Obligatorio | Ejemplo |
|---|---|---|
| Desde (fecha) | Si | 15 sep 2026 |
| Hasta (fecha) | No: vacio = sin fecha de fin | 30 sep 2026 |
| Dias de la semana | Si: por defecto, todos | Lunes a jueves |
| Franja horaria | No: vacia = todo el dia | 12:00 a 15:00 |

**Activa.** Un interruptor para apagarla antes de tiempo sin tocar las fechas.

### 2. Cuando esta vigente

Una promocion se ofrece **solo** si se cumplen todas estas condiciones a la vez, con la
hora de Colombia (`America/Bogota`):

1. Esta activa
2. Hoy es igual o posterior a *Desde*, y anterior o igual a *Hasta* (si tiene)
3. Hoy es uno de los dias marcados
4. La hora actual esta dentro de la franja (si tiene)
5. No esta agotada

Nadie la enciende ni la apaga: el sistema la evalua cada vez que alguien pide el menu.

En el panel, cada promo muestra en que estado esta, para que el administrador entienda
por que no la ve en el menu:

| Estado | Cuando |
|---|---|
| **Vigente** | Se esta ofreciendo ahora |
| **Programada** | Todavia no llega su fecha de inicio |
| **Fuera de horario** | Esta en fechas, pero hoy no es su dia o no es su hora |
| **Vencida** | Ya paso su fecha de fin |
| **Apagada** | El interruptor esta apagado |
| **Agotada** | Cocina o el administrador la marcaron agotada |

Una promo vencida **no se borra**: queda en el panel y en los reportes, y se puede volver
a usar cambiandole las fechas.

### 3. El menu del cliente

- Si hay al menos una promo vigente, la seccion **Promociones** va **antes de todas las
  categorias**, y tambien de primera en los filtros de arriba. Si no hay ninguna, la
  seccion no aparece: nunca una seccion vacia.
- **Revisado 2026-09-16 (pedido del autor): sin franja de color.** La primera version
  ponia las promos en una banda con el color de marca y el autor la descarto: *"se ve muy
  mal esa franja"*. Ahora las promos van **sobre el mismo fondo que el resto del menu**,
  con el mismo titulo de seccion y la misma tarjeta que un plato, para no romper la
  estetica. Lo que las distingue:
  - una **insignia "Promo"** con el color de acento sobre la foto
  - un **halo suave** con el color de acento alrededor de la foto, que **respira**
    despacio (un ciclo de unos 3 segundos). Es movimiento continuo pero lento y tenue: no
    parpadea ni cambia de tamaño
  - el resumen de lo que incluye en lugar de la descripcion, y un enlace "Ver que incluye"
  - Con `prefers-reduced-motion`, el halo queda **quieto**: la promo se sigue distinguiendo
    por el color, no por el movimiento.
- Cada tarjeta muestra el nombre, la foto, el precio, un resumen de lo que incluye
  ("2 hamburguesas · postre · gaseosa") y, si termina pronto, hasta cuando vale
  ("Hasta el domingo", "Hasta las 3:00 p. m.").
- **Al tocarla** se abre el mismo detalle que ya tienen los platos
  ([[SPEC-003 - Menu del Cliente]]), con la lista completa de componentes, cada uno con su
  cantidad y su especificacion.
- Se agrega al carrito como cualquier plato, con cantidad y observaciones.
- El titulo de la seccion ("Promociones") sale de la configuracion, no del codigo.

Si una promo deja de estar vigente mientras el cliente mira el menu, desaparece en el
siguiente refresco del menu (hoy, cada 60 segundos, [[SPEC-017 - Agotar un Plato desde Cocina]]).

### 4. Del QR a la confirmacion

La promo viaja en el QR igual que un plato: su id, la cantidad y la observacion
([[SPEC-002 - QR de Pedido]]). El QR no crece.

Al confirmar, el mesero ve la promo como una sola linea con su precio. **La vigencia se
comprueba otra vez al confirmar**, dentro de la misma transaccion en que ya se comprueba
si un plato esta agotado. Si el cliente armo el carrito a las 2:58 y el mesero confirma a
las 3:02, con franja hasta las 3:00, la confirmacion se rechaza con un mensaje claro
("La promo «Combo Parrillero» ya no esta vigente"), igual que con un plato agotado.

### 5. Cocina

La tarjeta de la comanda muestra la promo como un renglon destacado, y **debajo su
desglose**:

```
3× COMBO PARRILLERO
   EN TOTAL
   6× Hamburguesa clasica
   3× Brownie con helado
   3× Gaseosa 400 ml
   ⚠ hamburguesas sin cebolla
```

**Las cantidades del desglose van ya multiplicadas** por la cantidad de combos (agregado al
implementar, 2026-09-14): con 3 combos, cocina prepara 6 hamburguesas y no tiene que hacer
la cuenta de cabeza. Con un solo combo no aparece "En total".

La especificacion de cada componente (los ingredientes) **no** se muestra en la tarjeta,
que tiene que leerse de un vistazo desde lejos. Cocina ya sabe como se hace la
hamburguesa clasica.

**El desglose se congela en la venta**, igual que el nombre y el precio. Si mañana el
administrador cambia el postre del combo, los pedidos de hoy siguen mostrando lo que se
vendio hoy.

### 6. Reportes

En la pantalla **Reportes** ([[SPEC-018 - Reportes de Venta]]), con el rango de fechas que
ya existe:

- **Un filtro de producto.** Se elige una promocion o un plato cualquiera y se ve:
  - unidades vendidas e ingresos del rango
  - la misma cifra agrupada **por dia, por semana o por mes**, en una grafica y en una tabla
- **Un filtro "Solo promociones"** que deja el ranking de productos mas vendidos solo con
  promociones, para compararlas entre si.

Las cuentas siguen las reglas que ya usa Reportes:

- **Unidades** = suma de cantidades vendidas
- **Ingresos** = precio congelado × cantidad, sin propina ni impuesto
- Los pedidos anulados no cuentan
- La fecha es la del cobro de la cuenta

Un combo es **una unidad**. 20 combos vendidos son 20 unidades de ese combo y sus ingresos.

### 7. Unificar o separar estaciones

En **Configuracion → Operacion** hay un interruptor: **"Unificar estaciones"**.

| Valor | Que pasa |
|---|---|
| **No** (por defecto) | Como hoy: cada plato llega a la estacion de su categoria, y las promociones a la estacion por defecto |
| **Si** | **Todo** llega a la estacion por defecto, sin importar la categoria. Cocina recibe tambien las bebidas |

- Encenderlo **no borra** a que estacion pertenece cada categoria: al apagarlo, todo vuelve
  a rutearse como estaba.
- Afecta los pedidos que se confirman **despues** del cambio, y lo que se agregue a un
  pedido en curso. Las comandas que ya existen se quedan donde estan.
- Es un parametro de configuracion, no un cambio de codigo: sirve igual para un
  restaurante con cocina, bar y parrilla.

**El tablero sigue al interruptor (revisado 2026-09-16, pedido del autor).** Unificar solo el
ruteo no bastaba: el tablero seguia mostrando una estacion a la vez, con su selector, y las
comandas que habian llegado al bar antes de unificar se quedaban donde nadie las veia. El
autor lo pidio asi: *"que cocina no tenga que desplazarse a postres o bar, sino que todo le
llegue al mismo dashboard"*.

| Valor | El tablero |
|---|---|
| **Si** | Muestra **todas las comandas de todas las estaciones** en un solo tablero, sin selector. Cada tarjeta dice de que estacion es cuando no es la de por defecto, para no perder ese dato |
| **No** | Como hoy: se elige la estacion arriba y se ven solo sus comandas |

Las estaciones se siguen creando en **Administracion → Estaciones**, y esa pantalla dice en
que modo esta el restaurante y donde se cambia.

## Reglas

1. **Una promocion es un plato.** Se congela en la venta como cualquier plato: nombre,
   precio y, ademas, su desglose.
2. **La vigencia la calcula el servidor**, con la hora de Colombia. El navegador del cliente
   nunca decide si una promo vale.
3. **La vigencia se revalida al confirmar**, no solo al mostrar el menu.
4. **Una franja puede cruzar la medianoche.** "De 8:00 p. m. a 2:00 a. m." es valida, y el
   tramo despues de medianoche pertenece al dia en que empezo. Una promo de viernes a esa
   hora sigue valiendo el sabado a la 1:00 a. m.
5. **No hay cambios de componentes**, solo observaciones.
6. **Una promo se agota a mano**, desde cocina o desde el panel, como cualquier plato
   ([[SPEC-017 - Agotar un Plato desde Cocina]]). Sus componentes son texto, asi que el
   sistema no puede saber que se acabo la carne.
7. **No se borra** una promocion que ya se vendio. Se apaga.
8. **Nada escrito a mano:** el titulo de la seccion y los textos del cliente salen de la
   configuracion, y los colores, de los tokens del tema.
9. **Solo el administrador** crea y edita promociones.

## Criterios de aceptacion

### Panel

- [x] Al crear un plato se puede elegir el tipo **Promocion**
- [x] Una promocion sin componentes **no se puede guardar**
- [x] Cada componente guarda cantidad, nombre y especificacion, y se pueden **reordenar**
- [x] Una promo sin fecha de fin sigue vigente indefinidamente
- [x] El panel muestra el **estado** de cada promo: vigente, programada, fuera de horario,
      vencida, apagada o agotada
- [x] Una promo que ya se vendio **no se puede borrar**, solo apagar
- [x] Solo el administrador puede crear o editar promociones, **tambien desde la API**

### Vigencia

- [x] Una promo con inicio mañana **no aparece** hoy
- [x] Una promo que termino ayer **no aparece** hoy
- [x] Una promo de lunes a jueves **no aparece** un viernes
- [x] Una promo de 12:00 a 15:00 aparece a las 14:59 y **no** a las 15:01
- [x] Una promo de viernes de 20:00 a 02:00 **sigue valiendo** el sabado a la 01:00, y
      **no** el viernes a la 01:00
- [x] Apagar una promo la quita del menu aunque este en fechas
- [x] Confirmar un QR con una promo que **dejo de estar vigente** se rechaza con un mensaje
      que la nombra
- [x] Una promo agotada se ve en gris y no se puede agregar, como un plato agotado

### Cliente

- [x] Con al menos una promo vigente, la seccion Promociones es **la primera** del menu y
      del filtro de categorias
- [x] **(2026-09-16)** La seccion de promos va sobre el mismo fondo del menu, **sin franja
      de color**, con el mismo titulo y la misma tarjeta que los platos
- [x] **(2026-09-16)** Cada promo lleva la insignia "Promo" y el halo de acento que respira
      despacio
- [x] Sin ninguna vigente, la seccion **no aparece**
- [x] Al tocar una promo se abren **todos sus componentes con su especificacion**
- [x] La promo se agrega al carrito con cantidad y observacion, y **no** ofrece cambiar
      componentes
- [x] El titulo de la seccion sale de la configuracion
- [x] Con `prefers-reduced-motion`, el halo queda **quieto** (revisado 2026-09-16) — la regla
      global de `style.css` corta la animacion y el anillo quieto esta en la propia clase
- [x] Sin desborde horizontal en 320 y 375 px, y lo tocable mide 44 px o mas
      ([[SPEC-022 - Auditoria Responsive]])

### Pedido y cocina

- [x] La promo ocupa **un solo renglon** en el pedido, en la cuenta y en el tiquete, con
      su precio
- [x] La tarjeta de cocina muestra la promo **y su desglose**
- [x] Cambiar los componentes de una promo **no altera** los pedidos ya hechos
- [x] Cambiar el precio de una promo **no altera** las cuentas ya cobradas
- [x] La promo llega entera a la estacion por defecto, aunque haya estacion de bar
- [x] Con "Unificar estaciones" en **Si**, un plato de una categoria del bar llega a la
      estacion por defecto
- [x] Al volver a **No**, ese plato vuelve a llegar al bar, sin reconfigurar categorias
- [x] **(2026-09-16)** Con "Unificar estaciones" en **Si**, el tablero muestra las comandas
      de todas las estaciones juntas y **no** muestra el selector de estacion
- [x] **(2026-09-16)** En ese modo, una comanda que llego al bar antes de unificar tambien
      aparece, y su tarjeta dice "Bar" — prueba en `pedidos/tests.py`; en la base de
      desarrollo no habia comandas del bar en curso para verlo en pantalla
- [x] **(2026-09-16)** Con **No**, el tablero vuelve a mostrar el selector y una estacion a
      la vez
- [x] **(2026-09-16)** Administracion → Estaciones dice si el restaurante esta unificado y
      donde se cambia
- [x] La promo aparece en el Camino B del mesero, con la misma vigencia que para el cliente
- [x] Agregar una promo a un pedido en curso funciona como con cualquier plato
      ([[SPEC-011 - Novedades sobre Pedidos Enviados]])

### Reportes

- [x] Filtrar una promo muestra sus **unidades e ingresos** del rango
- [x] Se puede agrupar **por dia, por semana y por mes**, y los totales de la agrupacion
      cuadran con el total del rango
- [x] El mismo filtro funciona con **un plato normal**
- [x] 20 combos vendidos cuentan como **20 unidades** del combo, y no suman nada a los
      platos que se llaman igual que sus componentes
- [x] "Solo promociones" deja el ranking solo con promociones
- [x] Los pedidos anulados **no cuentan**
- [x] Una promo **renombrada** sigue sumando sus ventas anteriores en el filtro

> [!note] Como se verifico (2026-09-14)
> - **Pruebas automaticas** en `backend/menu/tests.py`: 36 nuevas. La vigencia se prueba con
>   la hora fijada, incluida la franja que cruza medianoche; el resto, contra la API y la
>   base real (panel, venta, cocina, estaciones unificadas y reportes).
> - **Recorrido en el navegador** con la base de desarrollo: crear una promo desde el panel
>   (franja de 20:00 a 02:00, sin domingo), verla primera en el menu del cliente, abrir su
>   detalle, venderla desde el Camino B, verla en la tarjeta de cocina con el desglose,
>   filtrarla en Reportes por dia y por mes, y el selector Si/No de "Unificar estaciones".
> - **Medido a 320 px** (el ancho mas estrecho de SPEC-022): seccion de promos, detalle,
>   panel con el formulario abierto, Reportes, Camino B y tarjeta de cocina. Desborde 0,
>   texto cortado 0, toques bajo 44 px 0. Los botones de los dias median 33 px de ancho en
>   el formulario y se pasaron a 4 columnas en telefono.
> - "Sin ninguna vigente la seccion no aparece" y "sin animacion con
>   `prefers-reduced-motion`" se comprobaron en el codigo (`v-if` y la regla global de
>   `style.css`), no en pantalla.

## Dependencias

- [[SPEC-003 - Menu del Cliente]] — la pagina, el detalle del plato y los filtros
- [[SPEC-002 - QR de Pedido]] — la promo viaja como un plato
- [[SPEC-005 - Estaciones y Ruteo]] — a que estacion llega
- [[SPEC-007 - Administracion y Parametrizacion]] — el panel del menu y los textos
- [[SPEC-017 - Agotar un Plato desde Cocina]] — agotar, y la revalidacion al confirmar
- [[SPEC-018 - Reportes de Venta]] — donde vive el filtro por producto
- [[SPEC-016 - Tiquete de Venta]] — la promo como un renglon del tiquete
- [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]] — revalidar dentro de la transaccion

## Plan de implementacion

### Paso 1 — Modelo y vigencia

- `Plato.tipo`: `plato` o `promocion`. Una promocion **no** tiene categoria; un plato
  normal la exige, y lo impone una restriccion en la base
- `ComponentePromocion`: promocion, orden, cantidad, nombre, especificacion
- Vigencia en el plato: desde, hasta, dias (lista de 0 = lunes a 6 = domingo), hora de
  inicio, hora de fin, y `activa`
- `DetallePedido.desglose_congelado`: los componentes (cantidad y nombre) en el momento de
  la venta
- Una sola funcion, `estado_promocion(plato, momento)`, que usan el menu, la confirmacion y
  el panel. La regla no se repite en tres sitios
- Pruebas de vigencia **con la hora fijada**, incluida la franja que cruza medianoche

### Paso 2 — Menu publico, confirmacion y ruteo

- La lista publica de platos solo trae las promos **vigentes o agotadas**. El panel pide
  todas con `?todas=1`, que solo se respeta para el administrador: una promo programada no
  se filtra por la API antes de tiempo
- Firmar, verificar, confirmar y agregar como novedad revalidan la vigencia
- El ruteo manda a la estacion por defecto lo que no tiene categoria, y **todo** cuando el
  parametro `estaciones-unificadas` esta en si
- Congelar el desglose al crear el renglon

### Paso 3 — Panel

- Seccion **Promociones** en `AdminMenu`, con su propio boton "+ Promocion"
- Editor de componentes: agregar, quitar y reordenar
- Vigencia: fechas, dias y franja, con el estado calculado a la vista
- Los parametros si/no de Configuracion se muestran como selector Si/No

### Paso 4 — Menu del cliente y cocina

- Seccion Promociones primero, con su estilo y su entrada breve
- Detalle con componentes y especificaciones
- Desglose en la tarjeta de `EstacionTablero`
- Medir a 320 y 375 px

### Paso 5 — Reportes

- Filtro por producto, agrupado por dia, semana o mes. **Por id de plato**, no por nombre
  congelado, para que una promo renombrada no parta su historia en dos
- Filtro "Solo promociones"

## Preguntas resueltas (2026-09-14)

- [x] **¿A que estacion llega una promo que mezcla cocina y bar?** Todo a cocina (la
      estacion por defecto). Ademas, interruptor para unificar estaciones (seccion 7).
- [x] **¿Cada componente lleva foto?** No, solo la foto de la promo.
- [x] **¿La observacion va para todo el combo o por componente?** Para todo el combo.
- [x] **¿Una promo puede tener varias franjas?** No, una sola.
- [x] **¿El tiquete muestra el desglose?** No, solo el nombre de la promo.
- [x] **¿Como usa Springfield su seccion de Promociones?** El autor decidio no revisarla:
      la spec basta.
