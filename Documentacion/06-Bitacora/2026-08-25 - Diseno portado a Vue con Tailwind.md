---
tipo: bitacora
fecha: 2026-08-25
tags: [bitacora, diseno, tailwind, vue, hito]
---

# 2026-08-25 — Diseño portado a Vue con Tailwind

Sigue a [[2026-08-25 - Rebanada vertical cerrada, estaciones y notificaciones]]. Con la
Fase 1 cerrada, arranca la etapa de diseño.

## Decisiones del autor

1. **Tailwind en vez de CSS a mano.** Se instaló Tailwind v4 (`@tailwindcss/vite`), sin
   `tailwind.config.js` — la configuración vive en `@theme` dentro de `style.css`.
2. **Todo el frontend en Vue**, ya decidido en [[ADR-006 - Stack Django, Vue y PostgreSQL]].

## Decisión que tomé yo (reversible)

La pregunta que quedó abierta —¿las pantallas internas llevan la marca del restaurante o
identidad propia?— la resolví: **identidad propia y fija**. Una pantalla de cocina se lee
de un vistazo en un ambiente caótico; heredar una paleta configurable arbitraria (fucsia
sobre naranja) es un riesgo real de legibilidad. En las pantallas internas el color
**significa urgencia** (el cronómetro), no marca.

Documentado en [[Sistema de Diseno]] con la nota de que se revierte cambiando los tokens
`panel-*`.

## El puente de tokens: Tailwind + configuración dinámica

El problema real: Tailwind compila estático, pero los colores del cliente viven en la base
de datos. La solución fue hacer que los tokens de `@theme` **apunten a variables CSS**, y
que `aplicarTemaCliente()` las escriba sobre `:root` en tiempo de ejecución. Así
`bg-marca` se resuelve a lo que el restaurante tenga configurado, sin recompilar.

Las variables van en `:root` a propósito: una variable CSS resuelve su valor en el elemento
donde se declara, y los tokens de `@theme` se declaran ahí — ponerlas más abajo en el árbol
no las alcanzaría.

Como efecto secundario, esto **resuelve el riesgo del salto de paleta** que quedó anotado
en ADR-006: el tema se aplica antes de pintar el menú, y los valores por defecto son el
mismo crema (no blanco brillante) para que ni ese instante se note.

## Qué se portó

**Página del cliente** — port completo del diseño de Fase 0: hero a pantalla completa con
parallax de recorrido largo (200vh), flecha que incita a bajar, filtros pegajosos con
scroll-spy, entrada lateral con profundidad, tarjetas ricas con foto cuadrada de radio
20px, sección "Encuéntranos", y responsive (rejilla de 3 → 2 → lista).

**Panel del carrito** — pantalla completa en móvil, panel centrado en escritorio, con
etiquetas rápidas, comentario a cocina y generación del QR.

**Pantallas internas** — nuevo `MarcoInterno.vue` compartido con navegación entre las tres,
más el restyle de mesero, estación, admin y login.

**Cronómetro que envejece** — pieza que estaba pendiente en [[SPEC-005 - Estaciones y Ruteo]]:
verde <10 min, ámbar 10-20, rojo >20. Aproveché que estaba en diseño para implementarla.

## Bug real encontrado y corregido

> [!bug] Las 4 imágenes de configuración estaban rotas
> `/api/configuracion/publica/` devolvía las rutas de imagen **relativas**
> (`/media/configuracion/hero.jpg`). Como Vue corre en otro origen (:5173) que Django
> (:8000), el navegador las resolvía contra Vue y no cargaban. Las fotos de platos sí
> funcionaban porque DRF las absolutiza automáticamente vía `ImageField`.
>
> Corregido en `ConfiguracionPublicaView`: se absolutizan en la frontera de la API con
> `request.build_absolute_uri()`. En la base siguen guardándose relativas — eso es lo que
> hace portable la instalación (SPEC-009).

## Verificado

- Tema de la base llegando a `:root` y resuelto por Tailwind (`--color-marca` → `#00473C`)
- Tipografías configurables cargándose desde Google Fonts según la base (Bodoni Moda)
- Hero exactamente a pantalla completa (900px = viewport), recorrido de 900px
- Rejilla de 3×363px en escritorio — idéntica al prototipo original
- Sin desborde horizontal en 1440 y en 375
- En móvil pasa a lista, con área táctil real de 44×44
- Flujo del cliente completo: agregar → panel → etiqueta rápida → generar QR
- Las tres pantallas internas con paleta propia (`#F7F7F5`, distinta del crema del cliente)
- Cronómetro pintando en rojo comandas de 20 y 22 minutos
- Sin errores de consola

## Nota de método (tercera vez que pasa)

Los controles medían 40px en vez de 44px. **No era un fallo**: las tarjetas estaban en su
estado de entrada con `scale(0.9)`, y 44 × 0.9 = 39.6. Cuando hay transformaciones de por
medio hay que medir **estilos computados**, no rectángulos.

## Pendiente

- Subida de imágenes desde el panel Vue (hoy solo vista previa)
- CRUD de menú desde el panel
- Umbrales del cronómetro configurables (hoy fijos en 10/20 min)
- La entrada por QR de mesa aterriza en el hero, no directo al menú
- Verificación en un teléfono real, no solo viewport emulado

## Enlaces

- [[Sistema de Diseno]]
- [[SPEC-003 - Menu del Cliente]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[Modelo de Pagina del Cliente]]
- [[Inicio]]
