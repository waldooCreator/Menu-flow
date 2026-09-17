---
tipo: bitacora
fecha: 2026-08-21
tags: [bitacora, diseno, carrito, responsive, fase-0]
---

# 2026-08-21 — Carrito, modal y responsive

Tercera tanda del día. Sigue a [[2026-08-21 - Ajustes esteticos del hero y entradas]].

## Qué se hizo

### 1. Corregido el anclaje al saltar a una categoría

Al pulsar "Ver el menú" (o un chip de categoría), el título quedaba **tapado** por la barra
superior y la barra de filtros, que son pegajosas.

La causa: el `scroll-margin-top` estaba fijo en `calc(--topbar-h + 70px)` = 142px, cuando
la zona tapada real es 145px. Ahora la altura de la barra de filtros **se mide en
JavaScript** y se publica como `--filters-h`, y el anclaje se calcula con
`--anclaje: calc(--topbar-h + --filters-h + 20px)`. Se remide al redimensionar y cuando
terminan de cargar las tipografías.

### 2. Responsive para móvil y tablet

Los usuarios principales serán de teléfono y tablet, así que se aseguró la experiencia en
los tres tamaños. Ver la tabla de rangos en [[Modelo de Pagina del Cliente]].

- **Tablet (641–1024px):** rejilla de 2 columnas, controles agrandados
- **Móvil (≤640px):** lista con miniatura, tipografía y espaciado ajustados
- **Muy angosto (≤380px):** miniatura reducida, galería a una columna
- **Área táctil de 44px** garantizada en chips, botón de agregar, cerrar y cantidad
- **Áreas seguras de iOS** (`env(safe-area-inset-*)`) en barra superior, botón flotante y modal
- **Hover anulado en táctil** con `@media (hover: none)`: en táctil se queda pegado tras el toque
- **Horizontal en pantallas bajas:** recorrido del hero a 150vh y sin subtítulo

### 3. Carrito y modal del pedido

- Botón de agregar sobre cada foto, que pasa a mostrar la cantidad en curso
- Botón flotante que aparece solo cuando hay algo en el pedido **y** ya se salió del hero
- **Modal de vista previa** antes de generar el QR: renglones con foto, precio por cantidad
  y control de cantidad; **etiquetas rápidas de observación** por plato más campo libre;
  **comentario general para la cocina** con contador; total y llamada a la acción
- Estado vacío propio, con la acción deshabilitada
- Se usa `<dialog>` con `showModal()`: da atrapado de foco y cierre con Esc sin código extra
- Las observaciones rápidas se añadieron al contrato de datos como `observacionesRapidas`,
  configurables por restaurante

## Dos bugs encontrados durante la verificación

> [!bug] Scroll horizontal en toda la página
> Las tarjetas entran desplazadas lateralmente (`translateX(±90px)`). Mientras no se
> revelan, ese desplazamiento **extendía el ancho del documento** y generaba barra de
> scroll horizontal — especialmente molesto en móvil, donde se podía arrastrar la página
> de lado. Se corrigió con `overflow-x: clip` en `.menu-section` (`clip` en vez de
> `hidden` porque no crea contenedor de scroll), con respaldo para Safari antiguo.

> [!bug] Botón de agregar recortado en móvil
> Se había colocado con `bottom: -14px` para que sobresaliera bajo la miniatura, pero
> `.card__figure` tiene `overflow: hidden` y lo cortaba a la mitad. Se movió dentro de la
> figura.

## Nota de método

Tres mediciones parecían fallos y no lo eran: los controles daban 39.6px en vez de 44px
porque estaban en su estado de entrada con `scale(0.9)`. Conviene medir **estilos
computados** y no rectángulos cuando hay transformaciones de por medio.

## Estado al cierre

- Fase 0 continúa. El prototipo ya cubre menú, carrito y vista previa del pedido
- Stack sigue **sin definir** — ver [[ADR-006 - Stack Django, Vue y PostgreSQL]]
- La generación real del QR es Fase 1: ver [[SPEC-002 - QR de Pedido]]

## Enlaces

- [[SPEC-003 - Menu del Cliente]]
- [[Modelo de Pagina del Cliente]]
- [[Sistema de Diseno]]
- [[Inicio]]
