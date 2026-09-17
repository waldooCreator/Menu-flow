---
tipo: diseno
actualizado: 2026-08-25
tags: [diseno, tokens, color, tipografia, tailwind]
---

# Sistema de Diseno

> Derivado del [[Analisis de Sweetgreen]]. **Implementado en produccion** en
> `frontend/src/style.css` con **Tailwind v4** (el `/prototipo` original queda como
> referencia historica). Un restaurante nuevo solo cambia su configuracion en la base.

## Una sola estetica (decision del autor, 2026-08-25)

Las pantallas internas (mesero, estacion, admin) usan **la misma estetica del sitio del
cliente**: fondo crema, verde de marca, serif para titulos, controles en pildora.

> [!info] Esto revirtio una decision del mismo dia
> La primera version de esta seccion separaba las pantallas internas con una paleta
> sobria propia ("panel-*"), por miedo a que una paleta configurable arbitraria
> arruinara la legibilidad de la pantalla de cocina. **El autor decidio unificar.**
> Se conserva lo esencial de aquella preocupacion: en el tablero de cocina el color
> significa **urgencia** (cronometro verde/ambar/rojo, boton "Listo" en esmeralda),
> nunca decoracion — y los avisos criticos (observaciones de un plato) van en ambar
> sobre blanco, legibles con cualquier marca.

Nota tecnica: las pantallas internas no llaman `aplicarTemaCliente()`, asi que hoy pintan
con los valores por defecto de `:root` (la paleta Terra). Si se quisiera que tambien
tomen la paleta del restaurante configurada en la base, bastaria llamarla en
`MarcoInterno` — decision pendiente de necesidad real.

## Puente de tokens: como convive Tailwind con la configuracion dinamica

Tailwind compila estatico, pero los colores del cliente viven en la base de datos. La
solucion: los tokens de `@theme` **apuntan a variables CSS**, y `aplicarTemaCliente()`
las escribe sobre `:root` en tiempo de ejecucion.

```
Postgres  →  /api/configuracion/publica/  →  aplicarTemaCliente()  →  :root
                                                                       ↓
                                              @theme --color-marca: var(--c-brand)
                                                                       ↓
                                                        clase `bg-marca` en cualquier componente
```

Asi `bg-marca` se resuelve a lo que el restaurante tenga configurado, **sin recompilar
nada**. Las variables van en `:root` a proposito: una variable CSS resuelve su valor en el
elemento donde se declara, y los tokens de `@theme` se declaran ahi.

> [!warning] El tema se aplica ANTES de pintar el contenido
> `aplicarTemaCliente(cfg)` se llama apenas responde la API y antes de mostrar el menu.
> Sin eso, el visitante veria la paleta por defecto y luego un salto a la del restaurante
> — el riesgo que quedo anotado en [[ADR-006 - Stack Django, Vue y PostgreSQL]]. Los
> valores por defecto de `:root` son deliberadamente el mismo crema, no blanco brillante,
> para que ni siquiera ese instante se note.

## Color

| Token | Valor | Rol |
|---|---|---|
| `--c-bg` | `#F4F3E7` | Fondo crema calido. **Nunca blanco** |
| `--c-bg-alt` | `#EBE9DA` | Crema un tono mas profundo |
| `--c-ink` | `#0E150E` | Casi negro verdoso, texto de platos |
| `--c-brand` | `#00473C` | Verde profundo, color dominante |
| `--c-brand-soft` | `#D8E5D6` | Salvia |
| `--c-accent` | `#E6FF55` | **Lima acido** — el golpe de energia |
| `--c-peach` | `#F9DFCE` | Durazno |
| `--c-blue` | `#D6E9E9` | Azul palido |

> [!tip] Pendiente de personalizar
> Esta paleta es casi la de Sweetgreen. Para que el proyecto tenga identidad propia habria
> que definir un verde y un acento distintos, conservando la **estructura**: fondo calido no
> blanco + color profundo dominante + un acento vibrante.

## Tipografia

| Token | Valor | Uso |
|---|---|---|
| `--f-sans` | Sofia Sans | **Todo el cuerpo.** Una sola familia |
| `--f-display` | Bodoni Moda, peso 300 | Solo titulos grandes |

Reglas aprendidas del analisis:

- **Una sola familia sans en un solo peso** para casi todo. Nada de negritas por doquier
- **El serif solo para display**, y en peso ligero (300). Nunca para texto corrido
- **Titulos de plato en MAYUSCULAS** con letter-spacing (~0.03em)
- Escala: 10 / 11 / 12 / 13 / 16 / 17 / 18 / 22 y display fluido

## Geometria

| Token | Valor | Uso |
|---|---|---|
| `--r-img` | `20px` | Fotos y bloques |
| `--r-pill` | `1000px` | Botones, chips, etiquetas |

- **Cero sombras.** El prototipo tiene 0 elementos con `box-shadow`, igual que la referencia
- Contraste deliberado: bloques con radio medio, controles en pildora completa

## Espaciado y retícula

- Contenedor: `1185px`
- Retícula del menu: 3 columnas, gap **48px vertical / 24px horizontal**
- El gap vertical grande es lo que da la sensacion de aire

## Fotografia

> [!important] La foto ES el diseno
> En la referencia, la imagen ocupa el 53% de la altura de cada tarjeta. Es el factor que
> mas pesa en que se vea bien o no.

- **Proporcion 1:1 obligatoria**, radio 20px
- Toma cenital, luz consistente, fondo neutro
- Respaldo digno para platos sin foto: inicial sobre color de marca, nunca un bloque gris
- Los platos agotados se ven en gris con etiqueta, **no se ocultan**

**Especificacion para el restaurante:** todas las fotos con la misma proporcion, la misma
luz y el mismo fondo. Sin esa consistencia, ningun CSS salva el resultado.

## Contenido

Otra leccion del analisis: **la referencia no es minimalista, es generosa.** Cada tarjeta
lleva nombre, lista completa de ingredientes, alergenos y varias metricas. La sensacion de
aire viene del espaciado y de la tipografia de un solo peso, no de quitar informacion.

- La descripcion es la **lista de ingredientes**, no una frase publicitaria
- Mostrar alergenos
- Tres metricas por plato segun aplique: calorias, porciones, minutos, onzas, % alcohol

## Movimiento

> [!note] Donde vive esto ahora (2026-08-25)
> Tailwind cubre layout, color, tipografia y espaciado. El movimiento ligado al scroll no
> se expresa en clases, asi que vive en dos sitios:
> - **CSS con nombre propio** (`frontend/src/style.css`): `.hero-fijo`, `.flecha-scroll`,
>   `.entrada--*` y sus keyframes
> - **Composables** (`frontend/src/lib/`): `useHeroParallax.js` (progreso del parallax) y
>   `useEntradaLateral.js` (direccion de entrada por posicion real)

### Valores

| Valor | Uso |
|---|---|
| `200vh` | Alto del contenedor del hero: cuanto scroll dura el parallax |
| `1000ms` | Duracion de la entrada lateral |
| `90px` / `34px` | Desplazamiento lateral: normal / columna central |
| `14px` / `22px` | Desenfoque de partida: normal / columna central |
| `0.90` / `0.86` | Escala de partida: normal / columna central |
| verde <10min · ambar 10-20 · rojo >20 | Cronometro que envejece en las comandas |

### Reglas

- **Parallax de recorrido largo:** el hero es `sticky` dentro de un contenedor de 200vh.
  El progreso se mide sobre todo ese recorrido, no sobre una pantalla, para que la
  animacion se sienta gradual. El fondo se desplaza y escala; el contenido se desvanece
  en el primer 65% del recorrido
- **Entrada lateral con profundidad:** los elementos salen del horizonte lateral,
  difuminados, reducidos y transparentes, y al llegar a su puesto se enfocan y toman su
  tamaño real. Cada uno entra **desde el lado mas cercano a donde queda**: columna
  izquierda desde la izquierda, derecha desde la derecha, y la central viaja menos pero
  con mas desenfoque (no tiene lado natural). En lista de una columna, **alternan**
- La direccion se calcula **por posicion real**, no por indice, para que funcione igual
  en 3 columnas, 2 o lista. Se recalcula al redimensionar, solo para los elementos que
  todavia no han entrado
- **Flecha de scroll** en el hero, con latido suave en bucle, que desaparece al primer
  scroll y no vuelve
- Zoom suave (1.04) en la foto al pasar el mouse
- Respetar `prefers-reduced-motion`: sin recorrido largo, sin entradas laterales, sin
  flecha. Todo aparece directamente en su sitio, visible y legible

### Dos trampas que ya costaron un bug

> [!warning] El estado inicial debe pintarse sin transicion
> Si se añade la clase de entrada **despues** de que el elemento ya se pinto, el navegador
> anima desde visible hacia oculto y se ve un parpadeo al cargar. Solucion: la clase
> `.js-preparando` apaga la transicion mientras se asigna el estado inicial, y se retira
> dos frames despues.

> [!warning] `requestAnimationFrame` no corre en pestañas en segundo plano
> Si la pagina carga sin estar visible, rAF nunca dispara y las animaciones no se activan
> jamas. Toda activacion diferida necesita **respaldo por temporizador**
> (ver la funcion `unaVez` en `script.js`).

`filter: blur()` se retira al terminar la transicion (clase `.is-settled`): mantenerlo
activo deja capas compuestas caras.

## Enlaces

- [[Analisis de Sweetgreen]]
- [[Modelo de Pagina del Cliente]]
- [[Referencias Visuales]]
- [[SPEC-003 - Menu del Cliente]]
