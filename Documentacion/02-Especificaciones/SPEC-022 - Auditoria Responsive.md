---
tipo: spec
id: SPEC-022
estado: implementada
actualizado: 2026-09-08
tags: [diseno, responsive, accesibilidad, correccion]
---

# SPEC-022 — Auditoria Responsive

> [!success] Estado: Implementada — verificada el 2026-09-08
> Las 20 pantallas, con datos, a 375 y a 320 px, mas 8 paneles y modales:
> **desborde cero, texto cortado cero, toques bajo 44 px cero**. Queda **una
> sola cosa por revisar a mano** —el carrito del cliente—, anotada abajo.

## Proposito

Corregir **todos** los sitios donde el sistema se ve mal o no se puede usar en
un telefono, y dejar escrito el metodo para que no vuelva a pasar.

## De donde sale esto

El autor lo reporto con una captura del **Libro de caja** en telefono: los tres
totales cortados —`$ 13.667.8…`, `$ 2.210.00`, `$ 11.457.80`.

La primera medicion se hizo con la base casi vacia, y **cuatro pantallas
aprobaron sin merecerlo**. El autor lo corto en seco: *"hasta que todas las
pantallas no esten testeadas no puedes terminar el spec"*. Se poblo todo y se
volvio a medir.

> [!danger] Lo que cambio al poner datos
> El **Salon** —la pantalla que mas usa un mesero— habia dado **cero fallos**.
> Con mesas ocupadas de verdad da **95 px de desborde a 375 y 149 px a 320**.
>
> El **Libro** habia dado 3 elementos cortados. Con movimientos reales da
> **138 a 320 px**: una fila cortada por cada movimiento.
>
> Una pantalla vacia no es una pantalla aprobada.

## Como se hizo el estudio

### 1. Poblar

Se creo el comando **`python manage.py poblar_demo`**
(`backend/pedidos/management/commands/poblar_demo.py`), que deja datos en todas
las pantallas: clientes con nombres de tres apellidos y direcciones con
indicaciones, cuentas abiertas, comandas en los tres estados y turnos cerrados
—uno **con descuadre**, para ver ese caso.

Los textos son largos **a proposito**: un nombre corto no prueba nada. Lo que
rompe una fila es `Ana Sofia Contreras de la Espriella`, no `Ana`.

Se puede repetir con `--limpiar`, que borra solo lo suyo.

### 2. Medir

> [!important] Medir el desborde NO es verificar el diseño responsive
> Es el error que ya se cometio dos veces en este proyecto. La seccion de
> reportes se dio por buena habiendo comprobado solo `scrollWidth`, y el autor
> tuvo que corregirla: habia nombres cortados **con desborde cero**.
>
> El corte de texto **no produce desborde**: el contenido se recorta dentro de
> su caja y la pagina sigue midiendo lo mismo. Hay que buscarlo aparte.

```js
window.__diag = () => {
  const d = document.documentElement, W = d.clientWidth;
  const vis = e => { const s = getComputedStyle(e);
    return s.display !== 'none' && s.visibility !== 'hidden'
        && s.opacity !== '0' && e.getBoundingClientRect().height > 0; };
  const todos = [...document.querySelectorAll('body *')].filter(vis);

  // 1. Desborde de la pagina
  const ov = d.scrollWidth - W;

  // 2. TEXTO CORTADO — lo que el desborde no ve.
  const cortado = todos.filter(e => {
    if (e.children.length) return false;                     // solo hojas
    const s = getComputedStyle(e);
    if (s.overflowX === 'auto' || s.overflowX === 'scroll') return false;
    return e.scrollWidth > e.clientWidth + 1 && (e.innerText || '').trim();
  });

  // 3. Toques por debajo de 44 px
  const toc = todos
    .filter(e => /^(BUTTON|A|SELECT|INPUT|TEXTAREA)$/.test(e.tagName))
    .map(e => e.getBoundingClientRect().height).filter(h => h > 0);

  // 4. Cuanto contenido habia: sin esto no se sabe si la pantalla estaba vacia
  return { ov, cortado, tocables: toc.length,
           bajo44: toc.filter(h => h < 44).length,
           texto: document.body.innerText.length };
};
```

El `s.opacity !== '0'` importa: sin el, se cuentan como visibles los elementos
que todavia no han entrado por la animacion.

### 3. Dos falsas alarmas que se descartaron

Se anotan porque quien repita el estudio va a tropezar con las mismas:

1. **"Los platos del menu del cliente estan invisibles"** — tenian
   `opacity: 0`, pero es su estado **normal antes de entrar**: estaban debajo
   del pliegue. Con scroll real entran bien (`opacity: 1`, `transform: none`).
2. **"La animacion de entrada nunca se dispara"** — si se dispara. Un
   `scrollTo` programatico seguido de volver arriba no activa el observador de
   forma fiable; hay que desplazarse y **quedarse ahi** para medir.

## Los fallos

### Grupo A — Desborde horizontal

La pagina se arrastra de lado. Medido en pixeles sobrantes.

| # | Pantalla | A 375 | A 320 | Causa |
|---|---|---|---|---|
| **A1** | **Salon** | **+95** | **+149** | La rejilla es implicita: su columna se dimensiona al **contenido** (449 px) en vez de al contenedor (335 px) |
| **A2** | **Admin › Cobro** | **+37** | **+92** | Cinco hijos con `shrink-0` en una fila que no envuelve |
| **A3** | **Libro** | **+10** | **+28** | `grid-cols-3` sin punto de quiebre |
| **A4** | **Reportes** | 0 | **+30** | El lienzo de Chart.js conserva un ancho fijo de 300 px dentro de un contenedor de 280 |
| **A5** | **Menu del cliente** | 0 | **+29** | Elementos sin entrar en `translateX(90px)`, fuera del recorte de un ancestro |

### Grupo B — Texto cortado

El contenido no cabe en su caja y se recorta. **No produce desborde.**

| # | Pantalla | Elementos cortados | El peor caso |
|---|---|---|---|
| **B1** | **Admin › Menu** | **38** | Nombre del plato en **21 px** a 375; **0 px a 320** — desaparece |
| **B2** | **Libro** | 3 a 375 · **138 a 320** | Totales: caja de **71 px** para un numero de **128 px** |
| **B3** | **Clientes** | 3 a 375 · 6 a 320 | Direccion truncada: **235 px** para **416 px** |
| **B4** | **Admin › Mesas** | 2 | "Domicilio / Para llevar" en 41 px de 60 |
| **B5** | **Todas** (encabezado) | 1 por pantalla | "Springfield" en **103 px** de 125. En Cocina, **47 px de 125** |
| **B6** | **Menu del cliente** | 1 | Titulo con `clamp(46px,…)`: 272 px de caja para 325 de texto (320) |

> [!note] B3 es truncado **a proposito**, y aun asi es un fallo
> La lista de clientes trunca la direccion con `truncate`. No se rompe nada —
> pero la direccion es **el dato que se necesita** para un domicilio, y en
> telefono no se ve ninguna. Hay que mostrarla en dos lineas, no cortarla.

### Grupo C — Toques demasiado pequeños

Medido como **elementos tocables por debajo de 44 px / total de la pantalla**.

| Pantalla | Bajo 44 px | El mas pequeño |
|---|---|---|
| **Admin › Sitio** | **113 / 115** | 30 px |
| **Admin › Menu** | **81 / 83** | 24 px |
| **Admin › Cobro** | **44 / 50** | **17 px** |
| **Admin › Usuarios** | **32 / 34** | 29 px |
| **Crear pedido** | **30 / 33** | 34 px |
| **Admin › Mesas** | **30 / 32** | 29 px |
| **Menu del cliente** | **21 / 23** | 24 px |
| **Admin › Estaciones** | 18 / 20 | 24 px |
| **Ventas** | 16 / 19 · **23 / 26** con filtros abiertos | **16 px** |
| **Activos** | 10 / 16 | 36 px |
| **Admin › Turnos** | 8 / 10 | **16 px** |
| **Libro** | 6 / 9 | 40 px |
| **Reportes** | 6 / 9 | 36 px |
| **Cocina** | 1 / 7 | 42 px |

**En total, unos 430 de 500 elementos tocables estan por debajo de 44 px.**

> [!danger] Los de 16 y 17 px incumplen una norma, no una preferencia
> WCAG 2.2, criterio **2.5.8 Target Size (Minimum)**, nivel **AA**, exige
> **24 × 24 px**. Las casillas de `size-4` (16 px) y el control de 17 px de
> Cobro **no lo cumplen**.
>
> Los de 24 a 42 px si cumplen ese minimo, pero incumplen la regla propia del
> proyecto —44 px, fijada en [[SPEC-021 - Navegacion del Personal]]— y el
> criterio 2.5.5 (AAA).

Las casillas de 16 px estan en: `MeseroVentas.vue:369,481,519` ·
`MeseroCuentas.vue:185` · `MeseroPedido.vue:325` · `AdminMenu.vue:508` ·
`AdminTurnos.vue:68`.

> [!important] El panel de administracion no esta hecho para tocarse
> No son "algunos botones pequeños": son **326 de 344** elementos de las siete
> pantallas de administracion. La causa es la misma en todas — el panel se
> diseño con densidad de escritorio (`min-h-9`, `min-h-10`, campos en linea) y
> nunca se reviso en telefono.
>
> Es el bloque de trabajo mas grande de esta spec, y conviene tratarlo como
> **una sola tarea con un criterio comun**, no pantalla por pantalla.

### Grupo D — Estados que se abren encima

Se midieron los paneles y modales, que en la primera pasada no se habian
mirado. **Ninguno desborda**, pero heredan el problema de los toques:

| Estado | Bajo 44 px | Notas |
|---|---|---|
| Ventas › "Mas filtros" abierto | **23 / 26** | El minimo sigue siendo 16 px |
| Clientes › ficha del cliente | 4 / 13 | Minimo 20 px |
| Libro › traslado entre cajas | 6 / 14 | — |
| Activos › registrar gasto | 10 / 21 | — |

### Lo unico que quedo sin medir

> [!warning] El carrito del cliente (`CarritoPanel.vue`)
> **No se pudo abrir por automatizacion.** El boton "Ver pedido" solo aparece
> cuando el carrito tiene algo **y** se salio del hero, y esa segunda condicion
> no se activa de forma fiable con desplazamiento programatico.
>
> Es **la pantalla de pago del cliente**: donde escribe su nombre, su telefono
> y su direccion. Tiene que revisarse **a mano** en un telefono real antes de
> dar por cerrada esta spec.

## Como se corrige cada uno

### A1 — El Salon (el mas grave)

Medido: el contenedor tiene 335 px, pero su `grid-template-columns` calculado
es **449.42 px**. Una rejilla sin columnas declaradas crea una columna
implicita de tamaño `auto`, que **se estira hasta el contenido** en vez de
ceñirse al contenedor.

```html
<!-- antes: en telefono la columna es implicita y crece con el contenido -->
<div class="grid gap-2.5 sm:grid-cols-2">
<!-- despues: `grid-cols-1` es `minmax(0,1fr)` en Tailwind, y eso si acota -->
<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
```

> [!important] Es el mismo error que A4, con otra cara
> En los dos casos hay un contenedor que **no acota a su hijo**: la rejilla
> deja crecer la columna, y la seccion de la grafica deja crecer el lienzo.
> La regla general esta abajo, en la numero 1.

### A2 y B1, B4 — Filas que no caben

La fila del plato tiene **cinco hijos en una linea que no envuelve**: miniatura
(56) + nombre (`flex-1`) + DISPONIBLE (93) + Editar (58) + ✕ (25) + separaciones
(48) + relleno (32) = 312 de 333. Al nombre le quedan **21 px**.

```html
<!-- antes -->
<div class="flex items-center gap-3 px-4 py-3">
<!-- despues: el nombre toma la linea entera y las acciones bajan -->
<div class="flex flex-wrap items-center gap-3 px-4 py-3">
  <img class="h-11 w-14 shrink-0 …" />
  <div class="min-w-0 flex-1 basis-[calc(100%-5rem)] sm:basis-auto">…</div>
```

Mismo tratamiento en `AdminCobro.vue:221` y `:281`, y en `AdminMesas.vue:113`.

### A3 y B2 — Los totales del Libro

`grid-cols-3` sin punto de quiebre: tres tarjetas en 375 px dejan 71 px de
contenido cada una.

```html
<div class="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
```

Y el numero, que ademas debe poder partirse:

```html
<p class="… text-[20px] break-words tabular-nums sm:text-[22px]">
```

> [!note] Ya existe el patron correcto en el proyecto
> `MeseroVentas.vue:270` usa `grid-cols-2 gap-2.5 sm:grid-cols-4` y no falla.
> **Copiar de ahi**, no inventar otro.

Los **138 elementos cortados a 320 px** son las filas del libro: se resuelven
dejando que la descripcion ocupe dos lineas en vez de una.

### A4 — La grafica que no encoge

El `<main>` da **280 px**, pero la `<section>` mide **330 px** porque el
`<canvas>` conserva el ancho por defecto de Chart.js —300 px— puesto en linea.

Dos cosas, las dos hacen falta:

1. El contenedor del lienzo: `relative w-full min-w-0`
2. El lienzo, que **no pueda** pasarse: `<canvas class="!max-w-full">`

Y comprobar que el observador de tamaño de `GraficoBarras.vue` mide **su propio
contenedor**, no la ventana.

### A5 y B6 — El menu del cliente

La animacion deja los elementos en `translateX(±90px)` hasta que entran. A
320 px eso se sale, porque la `<section>` tiene `overflow-x: clip` pero el
envoltorio de mas afuera no:

```html
<div class="relative isolate min-h-screen overflow-x-clip">
```

Y el titulo: a 320 px, `7vw` = 22 px, asi que gana el piso de 46 px — y
"Encuentranos" a 46 px necesita 325 px. **Bajar el piso**:
`text-[clamp(32px,7vw,90px)]`.

### B3 — Las direcciones de los clientes

Quitar `truncate` de esa linea y dejar **dos lineas** con corte al final:

```html
<p class="line-clamp-2 text-[12px] text-tinta/50">
```

### B5 — El nombre del restaurante

Truncar es el ultimo recurso, no la solucion. Que quepa:

```html
<span class="truncate font-display text-[18px] text-marca sm:text-[22px]">
```

En Cocina se corta a 47 px porque el encabezado lleva mas cosas al lado;
ahi ademas hay que dejar que baje de linea.

### C — Los toques

**Las casillas de 16 px** se agrandan **sin agrandar el dibujo**:

```html
<label class="-m-2.5 flex min-h-11 min-w-11 cursor-pointer items-center justify-center p-2.5">
  <input type="checkbox" class="size-4 cursor-pointer" />
</label>
```

El `-m-2.5` compensa el relleno para que **no cambie la maquetacion**: la
casilla se sigue viendo igual de pequeña, pero se puede tocar.

**El resto**: `min-h-9` → `min-h-11`, `min-h-10` → `min-h-11`.

> [!warning] Revisar la maquetacion despues de sustituir, no solo sustituir
> Subir de 36 a 44 px hace mas altas las filas de filtros y **puede provocar
> desbordes nuevos** donde antes cabian. Cada pantalla se vuelve a medir
> despues del cambio.

## Reglas, para que no vuelva a pasar

1. **Todo contenedor acota a su hijo.** Una rejilla lleva `grid-cols-1`
   explicito en telefono (`minmax(0,1fr)`), y todo lienzo o medio lleva
   `max-w-full` dentro de un padre `min-w-0`. Dos de los cinco desbordes son
   este mismo error.
2. **Ninguna rejilla de 3 o mas columnas sin punto de quiebre.**
3. **Ninguna fila con mas de tres hijos sin `flex-wrap`**, si alguno lleva
   texto de largo variable.
4. **Todo lo tocable, 44 px o mas.** Si el dibujo debe seguir siendo pequeño,
   se agranda el area con relleno y margen negativo.
5. **Ninguna cifra de dinero sin `break-words` y `tabular-nums`.** Los montos
   colombianos son largos: `$ 13.667.800` son 12 caracteres.
6. **`truncate` solo en lo prescindible.** Si el dato hace falta para trabajar
   —una direccion, el nombre de un plato— va en dos lineas.
7. **Ningun `clamp()` con un piso que no quepa a 320 px.**
8. **Se mide con datos y a 320 px.** Con la base vacia, el Salon daba cero.

## Criterios de aceptacion

### Desbordes — cero, a 375 y a 320

- [x] **A1** Salon (hoy +95 / +149)
- [x] **A2** Admin › Cobro (hoy +37 / +92)
- [x] **A3** Libro (hoy +10 / +28)
- [x] **A4** Reportes (hoy 0 / +30)
- [x] **A5** Menu del cliente (hoy 0 / +29)

### Texto cortado — cero elementos

- [x] **B1** Admin › Menu: el nombre del plato se lee completo (hoy 38 cortados)
- [x] **B2** Libro: los totales y las filas (hoy 138 a 320)
- [x] **B3** Clientes: la direccion se lee en dos lineas
- [x] **B4** Admin › Mesas
- [x] **B5** El nombre del restaurante cabe en el encabezado, tambien en Cocina
- [x] **B6** El titulo del menu del cliente cabe a 320

### Toques

- [x] **Ninguno por debajo de 24 px** — es incumplimiento de WCAG AA
- [x] **Ninguno por debajo de 44 px** en ninguna de las 20 pantallas
- [x] Las siete pantallas de administracion, revisadas **como un bloque**
- [x] Los cuatro paneles y modales del grupo D, revisados tambien — y cuatro mas: el gasto de Caja, el cierre con cajon, editar plato y cobrar cuenta
- [x] Tras subir los toques, **ninguna pantalla desborda de nuevo**

### El barrido final

- [x] Las **20 pantallas** con `poblar_demo` corrido, a 375 y a 320
- [x] Desborde **cero** y texto cortado **cero** en todas
- [ ] **El carrito del cliente revisado a mano en un telefono real**
- [x] Nada de lo anterior se rompio en computador (las 121 pruebas del servidor siguen en verde; el frontend no tiene suite)

## Como quedo

### Antes y despues, medido

| Pantalla | Desborde (375 / 320) | Texto cortado (375 / 320) | Toques bajo 44 |
|---|---|---|---|
| Salon | **+95 / +149** → 0 / 0 | 3 / 3 → 0 | 0 |
| Admin › Cobro | **+37 / +92** → 0 / 0 | 0 → 0 | **44 de 50** → 0 |
| Libro | +10 / +28 → 0 / 0 | 3 / **138** → 0 | 6 de 9 → 0 |
| Reportes | 0 / +30 → 0 / 0 | 0 → 0 | 6 de 9 → 0 |
| Menu del cliente | 0 / +29 → 0 / 0 | 1 → 0 | 21 de 23 → 0 |
| Admin › Menu | 0 | **38 / 38** → 0 | **81 de 83** → 0 |
| Admin › Sitio | 0 | 0 | **113 de 115** → 0 |
| Admin › Usuarios | 0 | 0 / 7 → 0 | 32 de 34 → 0 |
| Crear pedido | 0 | 0 | 30 de 33 → 0 |
| Clientes | 0 | 3 / 6 → 0 | 0 |
| Las otras 10 | 0 | 0 → 0 | todas → 0 |

**Total de toques bajo 44 px: de ~430 a 0.**

### Las correcciones que no estaban previstas

Al medir despues de cada cambio salieron seis fallos que la auditoria inicial
no tenia, casi todos **a 320 px** o **en estados abiertos**:

- Salon: el nombre del cliente truncado en la tarjeta (219 px para 324)
- Caja: la etiqueta "Bancolombia" del fondo por caja, cortada a 320
- Usuarios: el nombre de usuario en **4 px** a 320 — la misma fila apretada que el menu
- Estaciones: el campo del nombre en 31 px
- Cocina: el selector de estacion aplastaba el nombre del restaurante a 47 px, y a 320 seguia haciendolo con el ancho acotado — se bajo del encabezado al cuerpo en telefono
- Cinco botones ✕ de 8 a 25 px de ancho, en Clientes, Menu y Estaciones

Ninguno era visible con la base vacia ni a 375.

### La regla comun, en vez de 344 cambios

El panel de administracion se corrigio con **una regla de base en `style.css`**:
todo `button`, `select`, `textarea` e `input` (menos casillas y radios) mide
44 px como minimo. Lo que ya declaraba altura con `min-h-*` manda por
especificidad; lo que no la declaraba —los 344 controles del panel— la recibe
de ahi. Ademas `min-h-9` y `min-h-10` se subieron a `min-h-11` en los 12
archivos que los usaban (54 sitios).

### Una tercera falsa alarma

Los botones **+** de los platos del cliente median **40 × 40** teniendo
`size-11` (44 px) en el codigo y en el CSS compilado. La causa: estaban dentro
de tarjetas que **todavia no habian entrado**, y la animacion las deja en
`scale(0.9)` — 44 × 0.9 = 39,6. El diagnostico ahora salta lo que este dentro
de un ancestro escalado. Se anota junto a las otras dos.

### Tres decisiones de medicion que quedan escritas

1. **Para una casilla, el blanco es el `<label>` que la envuelve.** El dibujo
   sigue midiendo 16 px; el area que se toca mide 44.
2. **Los enlaces en linea dentro de un parrafo no cuentan.** WCAG 2.5.8 los
   exime: no son un blanco separado del texto. Eran dos: "Menu" en Cobro y el
   telefono en el pie del cliente.
3. **Lo que no ha entrado no se mide.** Un elemento con un ancestro en
   `opacity: 0` o `scale(0.9)` se salta.

### Lo que queda a mano

> [!warning] El carrito del cliente
> Sigue sin poderse abrir por automatizacion. Su codigo no tiene rejillas
> fijas ni anchos en pixeles, el contenedor usa `w-full` y `max-h-[88dvh]`, y
> sus controles reciben los 44 px de la regla comun — pero **nada de eso es
> una medicion**. Hay que abrirlo en un telefono real, con tres platos dentro,
> y llenar nombre, telefono y direccion.

## Plan de implementacion

### Paso 1 — Los desbordes (3 horas)

En orden de gravedad: **A1** (Salon, +149), **A2** (Cobro, +92), **A3**
(Libro), **A4** (Reportes), **A5** (cliente).

Despues de **cada** archivo, volver a medir esa pantalla. No al final: si algo
se rompe, hay que saber cual de los cambios fue.

### Paso 2 — El texto cortado (3 horas)

**B1** primero (el nombre desaparece a 320), luego B2, B5, B3, B4, B6.

### Paso 3 — Los toques (medio dia)

Primero las casillas de 16 px y el control de 17 px, que son lo que incumple la
norma. Despues el panel de administracion **como un bloque**, con un criterio
comun. Y volver a medir el desborde de cada pantalla tocada.

### Paso 4 — El barrido final (3 horas)

`poblar_demo`, las 20 pantallas a 320 y 375, el diagnostico **y ademas
mirandolas**. El diagnostico no ve un texto ilegible que si quepa, ni un boton
que quede fuera del alcance del pulgar.

Y el carrito del cliente, a mano.

**Total estimado: dos dias.**

## Dependencias

- [[Sistema de Diseno]] — tokens, movimiento y `prefers-reduced-motion`
- [[SPEC-021 - Navegacion del Personal]] — de ahi sale la regla de los 44 px, y
  el encabezado nuevo donde vive el fallo B5
- [[SPEC-018 - Reportes de Venta]] — el lienzo del fallo A4
- [[SPEC-012 - Vista de Salon y Estado de Mesas]] — la pantalla del fallo A1
- [[SPEC-019 - Clientes]] — las direcciones del fallo B3

## Preguntas abiertas

- [x] **¿El diagnostico deberia quedar en el repositorio**, en vez de vivir
      dentro de esta spec? **Propuesta:** si, en
      `frontend/herramientas/diagnostico-responsive.js`, al lado de
      `poblar_demo`. Los dos juntos hacen la auditoria repetible. **Hecho.**
- [x] **¿Se fija 320 px como el ancho minimo soportado?** **Si, y se verifico ahi.** Es
      el iPhone SE de primera generacion y el suelo practico de Android.
- [x] **¿El panel de administracion debe servir en telefono, o basta con
      tableta?** **Decidido por el autor el 2026-09-08: que sirva en telefono.**
      Las siete pantallas de administracion entran completas en el Paso 3.
