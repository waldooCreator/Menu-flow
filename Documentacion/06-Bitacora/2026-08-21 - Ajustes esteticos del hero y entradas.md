---
tipo: bitacora
fecha: 2026-08-21
tags: [bitacora, diseno, fase-0]
---

# 2026-08-21 — Ajustes estéticos del hero y entradas

Segunda tanda del día, posterior a [[2026-08-21 - Arranque y prototipo visual]].
Primera iteración de cambios estéticos bajo el flujo acordado para Fase 0.

## Qué se hizo

1. **Hero a pantalla completa.** Pasó de `88vh` a ocupar el 100% de la pantalla en
   cualquier resolución. Al cargar ya no se ve la franja crema, ni los filtros, ni el
   botón de pedido, ni la etiqueta de prototipo.

2. **Parallax de recorrido largo.** El hero ahora es `sticky` dentro de un contenedor de
   200vh: la animación se desarrolla durante una pantalla extra de scroll antes de dar
   paso al menú. El fondo se desplaza y escala; el contenido se desvanece en el primer
   65% del recorrido.

3. **Flecha animada que incita a bajar.** Reemplaza la señal que antes daba el borde del
   menú asomando. Late suavemente en bucle y desaparece al primer scroll.

4. **Entrada lateral con profundidad.** Chips de filtro, títulos de categoría y tarjetas
   de plato entran desde el horizonte lateral: salen difuminados, reducidos y
   transparentes, y al llegar a su puesto se enfocan y toman su tamaño real.
   Cada elemento entra desde el lado más cercano a donde queda; la columna central viaja
   menos pero con más desenfoque; en móvil alternan.

## Decisiones

- **Reversión documentada:** el hero pasó de 88% a 100% de pantalla. Era una regla escrita
  a propósito en [[Modelo de Pagina del Cliente]], así que quedó anotada allí con su
  porqué y con la advertencia de no revertirla sin reemplazar la señal de scroll.
- **`100lvh` en lugar de `100dvh`.** Con `dvh` la altura se encoge cuando la barra del
  navegador está visible y puede asomar una franja bajo el hero — justo lo que se quería
  eliminar. Además `.hero-scroll` lleva el fondo oscuro como respaldo.
- **La dirección de entrada se calcula por posición real, no por índice.** Así funciona
  igual con 3 columnas, 2 o lista, y se recalcula al redimensionar.

## Dos bugs encontrados y corregidos

> [!bug] Parpadeo al cargar
> Añadir la clase de entrada **después** de que el elemento ya se pintó hacía que el
> navegador animara desde visible hacia oculto: un parpadeo feo de un segundo al cargar.
> Se corrigió apagando la transición con `.js-preparando` mientras se asigna el estado
> inicial, y retirándola dos frames después.

> [!bug] `requestAnimationFrame` no corre en segundo plano
> La activación diferida dependía solo de rAF. Si la página carga en una pestaña que no
> está visible, rAF nunca dispara y las animaciones no se activarían jamás. Se añadió
> respaldo por temporizador (función `unaVez`).

Ambos quedaron documentados en [[Sistema de Diseno]] para que no se repitan.

## Verificación

Medido en el navegador, en escritorio (1425×900) y móvil (395×812):

- Hero = alto exacto del viewport, en ambos tamaños
- Filtros fuera de pantalla al cargar; carrito y etiqueta ocultos
- Recorrido de parallax: una pantalla completa extra
- Estado inicial de las tarjetas: `opacity 0`, `blur(14px)`, desplazadas y a escala 0.90
- Direcciones en escritorio (3 columnas): 9 izquierda, 5 centro, 5 derecha
- Direcciones en móvil (1 columna): alternancia perfecta izquierda/derecha
- Sin errores de consola

**No verificado visualmente por Claude:** el panel del navegador no compone imagen si no
está visible en pantalla, así que la validación fue por métricas y estilos computados, no
por captura. La revisión visual final la hizo el autor.

## Estado al cierre

- Fase 0 continúa: iterando estética sobre el prototipo
- Stack sigue **sin definir** — ver [[ADR-006 - Stack Django, Vue y PostgreSQL]]

## Enlaces

- [[Modelo de Pagina del Cliente]]
- [[Sistema de Diseno]]
- [[SPEC-003 - Menu del Cliente]]
- [[Inicio]]
