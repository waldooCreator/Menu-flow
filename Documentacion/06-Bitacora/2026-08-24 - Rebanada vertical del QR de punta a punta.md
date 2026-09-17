---
tipo: bitacora
fecha: 2026-08-24
tags: [bitacora, qr, pedidos, vertical-slice, hito]
---

# 2026-08-24 — Rebanada vertical del QR de punta a punta

Cuarta y última tanda del día, después de
[[2026-08-24 - API REST y frontend Vue conectado]]. Es el hito más importante hasta ahora:
**la primera vez que un flujo completo del producto funciona de verdad, con interfaz real,
no solo por API.**

## Qué se pidió

Cerrar la "rebanada vertical" que define [[Vision del Producto]] para la Fase 1: cliente
arma su pedido, genera un QR real, el mesero lo escanea y confirma, y el pedido queda en
base de datos.

## Qué se construyó

### Backend — app `pedidos`

- **`Mesa`, `Pedido`, `DetallePedido`** — con el precio y el nombre **congelados** en el
  detalle (regla de [[SPEC-008 - Contabilidad y Auditoria]])
- **`firma.py`** usa `django.core.signing` (no el HMAC manual del script de ayer): firma
  con `SECRET_KEY`, expiración (`max_age`) y compresión resueltas por el framework
- **Tres endpoints:** `firmar` (público, no escribe nada), `verificar` (público, resuelve
  el pedido para mostrarlo), `confirmar` (requiere sesión — aquí y solo aquí se crea el
  `Pedido`)
- **Anti-duplicado sin campo aleatorio:** `codigo_qr` es un hash del texto firmado —
  mismo QR, mismo hash, `unique=True` lo bloquea

### Frontend — carrito real y vista de mesero

- **`stores/carrito.js`** (Pinia, en memoria — nunca persiste hasta confirmar, tal como
  manda SPEC-002)
- **`CarritoPanel.vue`** — arma el pedido con observaciones rápidas y genera el QR con la
  librería `qrcode`, dibujado en el navegador del cliente
- **`MeseroEscaner.vue`** — decodifica un QR desde una imagen subida (con `jsQR`), muestra
  el pedido resuelto, confirma
- **Ruta `/m/:codigo`** — entrada por QR de mesa (SPEC-001), resuelve el código contra la
  base y lo fija en el carrito

## Verificado de punta a punta, en la interfaz real

1. Entré por `/m/x7f2q9` → "Mesa 12" se identificó correctamente
2. Agregué 3 unidades de 2 platos distintos, activé una observación rápida
3. Generé el QR → imagen real dibujada en el navegador
4. Pasé esa misma imagen (vía `localStorage`, para cruzar la navegación) a la vista de
   mesero → `jsQR` la decodificó → la API la verificó y resolvió contra el menú vigente
5. Confirmé → **Pedido #2 creado en Postgres**, con `mesero=admin`, precio y nombre
   congelados, observación correcta

Además, por API: firma alterada → rechazada; confirmar sin token → 401; confirmar con
token → 201; reusar el mismo QR → 409.

## Divergencia que quedó pendiente, anotada a propósito

La recomendación medida ayer (observaciones por índice, no por texto — ver
[[2026-08-24 - Prueba tecnica del QR y Vue confirmado]]) **no se implementó así todavía**:
el carrito manda el texto completo de la observación. No rompió nada hoy porque el pedido
de prueba era pequeño, pero vuelve a exponer el riesgo de disparar el Plan B antes de
tiempo en pedidos grandes. Quedó anotado como pendiente en [[SPEC-002 - QR de Pedido]], no
silenciado.

## Lo que NO se cerró (honesto, no se quiso maquillar)

- **Ruteo a estaciones** ([[SPEC-005 - Estaciones y Ruteo]]) — el pedido queda `PENDIENTE`,
  no se reparte en comandas
- **Notificación al mesero** ([[SPEC-006 - Notificaciones]]) — no existe todavía
- **Marcar LISTO/ENTREGADO** — no hay pantalla de estación
- **Camino B del mesero** (armar pedido desde cero, sin QR) — no construido
- **Escaneo por cámara en vivo** — se probó por imagen subida, no por cámara física
- **Diseño visual de Fase 0** — la interfaz de hoy es funcional, no el diseño de
  `/prototipo`

## Estado al cierre

- La Fase 1 tiene su primer flujo real de punta a punta, con las salvedades de arriba
- [[SPEC-001 - QR de Mesa]], [[SPEC-002 - QR de Pedido]], [[SPEC-004 - Modulo Mesero]]:
  actualizadas con estado de implementación honesto y criterios de aceptación reales
- [[ADR-002 - El mesero confirma el pedido]]: la salvaguarda de seguridad que describe
  quedó verificada en código, no solo en diseño

## Enlaces

- [[Vision del Producto]]
- [[SPEC-001 - QR de Mesa]]
- [[SPEC-002 - QR de Pedido]]
- [[SPEC-004 - Modulo Mesero]]
- [[ADR-002 - El mesero confirma el pedido]]
- [[Inicio]]
