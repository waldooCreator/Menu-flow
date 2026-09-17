# Proyecto — Sistema de Gestión para Restaurantes

> Este archivo se carga automáticamente en cada sesión de Claude Code.
> Su trabajo es apuntarte al contexto real, no duplicarlo.

## Antes de hacer nada

**Todo el contexto del proyecto vive en la bóveda de Obsidian en `Documentacion/`.**

Lee en este orden:

1. `Documentacion/00-Inicio/Inicio.md` — estado actual y mapa de todo
2. `Documentacion/00-Inicio/Metodologia - Spec Driven Development.md` — cómo se trabaja aquí
3. La spec concreta de lo que te pidan, en `Documentacion/02-Especificaciones/`

## Cómo se trabaja: Spec Driven Development

**La especificación es la fuente de verdad. El código es su implementación.**

- **No escribas código sin una spec aprobada.** Si te piden algo que no tiene spec,
  propón escribir la spec primero.
- **Todo cambio de comportamiento empieza por la spec.** Se edita, se aprueba, y después
  se toca el código. Nunca al revés.
- **Las decisiones arquitectónicas van a un ADR** en `Documentacion/03-Decisiones/`,
  no a la spec. La spec dice *qué* debe pasar; el ADR dice *por qué* se eligió ese camino.
- **El código referencia el ID de la spec.** Un comentario `// SPEC-005` en el módulo de
  ruteo vale más que cualquier documentación suelta.
- **Lo que no está en la spec está fuera de alcance.** Si aparece algo nuevo, se anota en
  la bitácora y se decide después.

Al terminar un trabajo: actualiza el estado de la spec y anota en
`Documentacion/06-Bitacora/`.

## Estado actual (2026-09-16)

| Aspecto | Estado |
|---|---|
| Fase | Fase 1 cerrada — el flujo completo funciona en local; no está en producción |
| Stack tecnológico | Django (solo API, DRF) + Vue 3 + Tailwind v4 + PostgreSQL — ver ADR-006 |
| Código existente | `backend/` (Django) y `frontend/` (Vue). `prototipo/` queda como referencia histórica |
| Specs | SPEC-001 a SPEC-024: implementadas, salvo SPEC-008 y SPEC-010 (borrador) y SPEC-009 (aprobada, sin probar en servidor) |
| Próximo paso | Lo decide el autor: costo de envío de domicilios o paso a producción. El detalle vive en `Documentacion/00-Inicio/Inicio.md` |

> [!] El estado de cada spec y lo que queda pendiente se mantiene en `Inicio.md`, no aquí.
> Esta tabla solo sirve para no arrancar con una idea equivocada del proyecto.

## Estructura del repositorio

```
Restaurant/
├── CLAUDE.md              <- este archivo
├── Documentacion/         <- bóveda Obsidian: TODO el contexto
│   ├── 00-Inicio/         <- punto de entrada y metodología
│   ├── 01-Producto/       <- visión, actores, flujo, glosario
│   ├── 02-Especificaciones/  <- SPEC-001 a SPEC-024
│   ├── 03-Decisiones/     <- ADR-001 a ADR-009
│   ├── 04-Diseno/         <- sistema de diseño y referencias
│   ├── 05-Investigacion/  <- viabilidad, competencia y comparativa con Springfield
│   ├── 06-Bitacora/       <- registro por día
│   └── 99-Plantillas/     <- plantillas SPEC / ADR / bitácora
├── backend/               <- Django: apps nucleo, configuracion, menu, pedidos,
│                             estaciones, ventas, clientes
├── frontend/              <- Vue 3 + Tailwind v4 (src/views: cliente, mesero, estacion, admin)
├── docker-compose.yml     <- solo PostgreSQL local
├── GUION-DEMO.md          <- cómo levantar todo en local y recorrer la demostración
├── Entregables/           <- trabajos académicos sobre el proyecto (no es código)
└── prototipo/             <- Fase 0: prototipo visual estático
    ├── index.html
    ├── styles.css         <- sistema de diseño en variables CSS
    ├── script.js
    ├── data.js            <- contrato de datos que el backend deberá cumplir
    └── assets/            <- 24 fotos de referencia
```

## Reglas del proyecto

- **Idioma:** todo en español — código, comentarios, documentación e interfaz.
- **Parametrizable:** ningún color, texto o valor de negocio escrito a mano en el código.
  Todo sale de variables o configuración.
- **Los pedidos no se borran**, se anulan con motivo y responsable.
- **El precio se congela en la venta.** El detalle guarda precio y nombre del momento en
  que se vendió, no una referencia al menú.
- **Sin impresión de comandas.** Las comandas de cocina van por mensajes dentro de la
  aplicación; los tiquetes de venta son imprimibles según SPEC-016.
- **Código moderno, siempre.** Usa las mejores prácticas y las técnicas actuales de cada
  lenguaje del proyecto — nunca formas antiguas ni patrones heredados. En concreto:
  - **Python/Django:** `select_related`/`prefetch_related` en vez de consultas en bucle,
    `transaction.atomic` para lo que debe ser todo-o-nada, restricciones en la base
    (`UniqueConstraint`) antes que validación solo en código, f-strings, `pathlib`.
  - **JavaScript/Vue:** `<script setup>` con Composition API, nunca Options API;
    `const`/`let` y nunca `var`; encadenamiento opcional (`?.`) y `??`; `async/await`
    en vez de cadenas de `.then()` anidadas.
  - **CSS:** Tailwind v4 con los tokens del tema; `flex`/`grid` y unidades relativas,
    nunca posicionamiento absoluto para maquetar ni tamaños fijos en píxeles.
  - Si una forma vieja ya está en el código, **no la imites**: corrígela o al menos
    no la propagues.

## Cómo ver el prototipo

```bash
cd prototipo && python -m http.server 8791
```

Luego abrir `http://localhost:8791`.
