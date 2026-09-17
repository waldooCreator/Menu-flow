---
tipo: bitacora
fecha: 2026-08-25
tags: [bitacora, roles, camara, mesero, estacion, demo]
---

# 2026-08-25 — Roles, cámara y Camino B del mesero

Tercera tanda del día, después de [[2026-08-25 - Diseno portado a Vue con Tailwind]].
Preparación final para la primera demostración a un cliente potencial (Springfield).

## Qué pidió el autor

1. El mesero debe poder **escanear con la cámara**, no solo subir una imagen
2. El mesero debe poder **armar el pedido desde cero** si el cliente no usó la app
   (el Camino B de [[SPEC-004 - Modulo Mesero]], que estaba pendiente)
3. Las pantallas internas deben seguir **la misma estética** del sitio del cliente
4. El tablero de cocina debe ser **más grande, más llamativo y más fácil de usar**
5. **Separación de roles**: el mesero no entra a cocina, cocina no entra al mesero,
   y ninguno al panel de administración

## Qué se construyó

### Roles y permisos (backend + frontend)

- Grupos `mesero` y `cocina`; usuarios demo por comando `crear_usuarios_demo`
  (mesero/mesero2026, cocina/cocina2026; admin sigue siendo superusuario y ve todo)
- `nucleo/permisos.py`: `EsMesero`, `EsCocina`, `AdminOSoloLectura` aplicados a toda la
  API — comandas solo cocina, notificaciones/confirmar/entregar solo mesero,
  configuración y escritura del menú solo admin
- `GET /api/auth/perfil/` devuelve el rol; el login de Vue lleva a cada rol directo a
  su pantalla, y la guardia del router rebota los accesos ajenos

### Camino A ampliado: cámara en vivo

`qr-scanner` (la librería que ya recomendaba [[ADR-005 - Escaneo con libreria JS]]) en
`MeseroEscaner.vue`. Tres vías ahora: cámara, imagen subida, o crear el pedido a mano.

### Camino B: crear pedido desde cero

Nueva vista `/mesero/pedido`: el mismo menú del cliente (fotos, categorías,
observaciones rápidas), el mesero elige mesa y envía. Por debajo firma y confirma en un
solo paso — la garantía de [[ADR-002 - El mesero confirma el pedido]] se mantiene,
porque quien confirma sigue siendo el mesero autenticado. **Sin backend nuevo**: reutiliza
`firmar` + `confirmar`.

### Estética unificada y tablero de cocina rediseñado

- `MarcoInterno` rediseñado con la estética del cliente (crema, verde marca, serif) y
  navegación filtrada por rol
- Tablero de cocina como pantalla de cocina de verdad: tarjetas grandes con los platos y
  observaciones visibles de un vistazo, un solo botón grande por tarjeta
  (Empezar a preparar → ✓ Listo — avisar al mesero), columnas con color de fondo,
  cronómetro grande
- Las comandas de pedidos ya entregados **salen solas del tablero** (nuevo campo
  `pedido_estado` en el serializador)

> [!info] Reversión de decisión, el mismo día
> En la tanda anterior yo había decidido que las pantallas internas tuvieran identidad
> propia sobria, separada de la marca. **El autor la revirtió**: todo comparte la estética
> del cliente. Se conserva lo esencial de aquella idea: en cocina el color sigue
> significando urgencia (cronómetro verde/ámbar/rojo), no decoración.
> Actualizado en [[Sistema de Diseno]].

## Verificado

- API: mesero→comandas 403, cocina→notificaciones 403, ambos→configuración 403;
  los accesos propios 200
- Navegador: login como `mesero` aterriza en `/mesero`; intentos de `/estacion` y
  `/admin` rebotan a `/mesero`. Lo mismo en espejo para `cocina`
- Camino B de punta a punta en la interfaz: mesa elegida → plato agregado → panel →
  **Pedido #7 creado en Postgres**
- Tablero cocina: Empezar a preparar → ✓ Listo → "Esperando al mesero", con las
  columnas moviéndose en vivo

## Responsive móvil: dos bugs medidos y corregidos

El autor reportó que en teléfono las notificaciones del mesero obligaban a hacer scroll
horizontal. Se midió en viewport de 375px, pantalla por pantalla, con
`scrollWidth` vs `clientWidth` y detección del elemento culpable:

> [!bug] La burbuja de notificaciones se salía de la pantalla
> El panel (`w-80`, anclado a la campana con `absolute right-0`) quedaba en
> `left: -39px` — 39px fuera del borde izquierdo en 375px. **Corregido**: en móvil el
> panel es una hoja `fixed` a lo ancho bajo el header; desde `sm` vuelve a colgar de la
> campana. Verificado: `left: 12, right: 363`.

> [!bug] El header interno desbordaba la página entera
> Con la sesión admin (nav de 3 enlaces + selector de estación + Salir), el header de
> `MarcoInterno` no envolvía: la página medía **532px** en `/estacion` y 421px en
> `/admin` — ese era el scroll horizontal real. **Corregido** con `flex-wrap` en el
> header (fluye a dos líneas en pantallas angostas).

Barrido final en 375px con la sesión más cargada (admin): cliente, mesero (con burbuja
abierta), crear pedido, estación y admin — **todas sin desborde horizontal**.

## Límites honestos

- La cámara exige contexto seguro (localhost o HTTPS): en el PC de la demo funciona;
  desde el celular por IP http **no** — ahí queda la vía de subir imagen
- No se probó con una cámara física real, solo el cableado de la librería
- Gestión de usuarios desde el panel sigue pendiente (hoy es un comando)
- Editar un pedido escaneado antes de confirmar sigue pendiente

## Enlaces

- [[SPEC-004 - Modulo Mesero]]
- [[SPEC-007 - Administracion y Parametrizacion]]
- [[Sistema de Diseno]]
- [[ADR-005 - Escaneo con libreria JS]]
- [[Inicio]]
