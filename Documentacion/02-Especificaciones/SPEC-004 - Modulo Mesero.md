---
tipo: spec
id: SPEC-004
estado: implementada
actualizado: 2026-09-14
tags: [mesero, pedido]
---

# SPEC-004 — Modulo Mesero

> [!success] Estado: Implementada — revisada 2026-09-14
> Camino A (escanear) y Camino B (armar desde cero) funcionan de punta a punta, con camara
> en vivo y con imagen subida. Falta: editar un pedido escaneado **antes** de confirmarlo, y
> probar la camara en un iPhone real.

## Proposito

Que el mesero pueda tomar un pedido de dos formas — escaneando el QR del cliente o
armandolo desde cero — y sea el responsable que valida toda venta.

## Alcance

- Escaneo del [[SPEC-002 - QR de Pedido|QR de pedido]] del cliente
- Armado manual de un pedido desde cero, con acceso al menu
- Confirmacion y envio a estaciones
- Centro de [[SPEC-006 - Notificaciones|notificaciones]]
- Marcado de entrega

## Fuera de alcance

- Cobro y cierre de cuenta
- Gestion de mesas y reservas

## Comportamiento

### Dos caminos para crear un pedido

**Camino A — escaneando:**
1. El mesero abre el escaner y apunta al QR del cliente
2. La app verifica la firma y resuelve los items contra el menu vigente
3. Muestra el pedido completo en pantalla, con la mesa y las observaciones
4. El mesero revisa y confirma

**Camino B — desde cero:**
1. El mesero elige la mesa
2. Navega el menu y arma el pedido, con observaciones
3. **Opcionalmente marca "cobrar al finalizar"** (2026-08-30)
4. Confirma

### Cobrar al finalizar (2026-08-30)

Es lo que en el sistema que se va a reemplazar se llama **"Venta rapida"**: armar y cobrar
de un tiron, sin pasar despues por la pantalla de cuentas. Tipico de mostrador o para
llevar.

- **Marcado:** al confirmar, se pide el medio de pago y la cuenta **se cierra ahi mismo**
- **Sin marcar:** todo sigue igual que hoy — el pedido va a cocina y la cuenta queda
  abierta para cobrarse despues desde [[SPEC-013 - La Cuenta]]

> [!important] Es un atajo, no un camino aparte
> No se duplica el flujo: es el mismo Camino B con un paso mas al final. Un camino paralelo
> significaria mantener dos versiones de lo mismo, y tarde o temprano se desincronizan.

Quien puede marcarlo depende del **mismo permiso configurable de cobro** que rige todo lo
demas ([[SPEC-014 - Turno de Caja y Cajas de Fondos]]): si el mesero no tiene habilitado
cobrar, la opcion no le aparece — y el servidor la rechaza igual si la fuerza.

Ambos caminos terminan igual: el pedido pasa a **PENDIENTE**, se rutea a estaciones y queda
amarrado al mesero que lo confirmo.

### Por que el mesero confirma siempre

El cliente nunca esta autenticado. Sin esta confirmacion, cualquiera podria generar un QR
desde su casa y meter un pedido en cocina sin haber pisado el restaurante, o pedir en la
mesa e irse. Ver [[ADR-002 - El mesero confirma el pedido]].

### Escaneo

Debe implementarse con una **libreria JavaScript**, no con la API nativa del navegador.
Ver [[ADR-005 - Escaneo con libreria JS]].

## Estado de implementacion (2026-08-24)

`frontend/src/views/mesero/MeseroEscaner.vue` + `backend/pedidos/`. Verificado de punta a
punta: cliente arma carrito real → genera QR real en su navegador → el mesero **sube esa
imagen** (no cámara) → se decodifica con `jsQR` → `POST /api/pedidos/verificar/` resuelve
contra el menú vigente → el mesero confirma → `POST /api/pedidos/confirmar/` crea el
`Pedido` en Postgres, amarrado al usuario logueado.

| Pieza | Estado |
|---|---|
| Camino A — escanear y confirmar | **Hecho** — por imagen subida y por cámara en vivo |
| Escaneo por cámara en vivo | **Hecho (2026-08-25)** — `qr-scanner` (ADR-005); exige contexto seguro (localhost/HTTPS); no probado aún con una cámara física |
| Camino B — armar desde cero | **Hecho y verificado (2026-08-25)** — `/mesero/pedido`: mismo menú del cliente, mesa elegida por el mesero, firma+confirmación en un paso (la garantía de ADR-002 se mantiene: confirma el mesero autenticado) |
| Editar un pedido escaneado antes de confirmar | Pendiente |
| Separación de roles | **Hecho y verificado (2026-08-25)** — usuarios `mesero`/`cocina` en grupos; la API responde 403 fuera del rol y la interfaz rebota a la pantalla propia |
| Ruteo a estaciones | **Hecho** — ver [[SPEC-005 - Estaciones y Ruteo]] |
| Centro de notificaciones | **Hecho** (con polling, no tiempo real aun) — ver [[SPEC-006 - Notificaciones]] |
| Marcar entregado | **Hecho** — `POST /api/pedidos/<id>/entregar/`, cierra el pedido y apaga sus notificaciones |

## Criterios de aceptacion

- [ ] El escaner funciona en Android **y en iPhone** — la camara en vivo ya existe
      (`qr-scanner`, ADR-005); falta probarla en un iPhone real
- [ ] Un pedido escaneado se puede editar antes de confirmar — **no se cumple
      (revisado 2026-09-14)**: `MeseroEscaner` muestra el pedido y lo confirma tal cual.
      Cambiarlo solo se puede despues, como novedad ([[SPEC-011 - Novedades sobre Pedidos Enviados]])
- [x] Con **"cobrar al finalizar"** marcado, confirmar pide medio de pago y **cierra la cuenta**
      — `confirmar` acepta `medio_pago` y cierra con el mismo `cerrar_cuenta` de la caja
- [x] Sin marcarlo, la cuenta queda **abierta**, como hasta ahora
- [x] Un mesero **sin permiso de cobro** no puede usar esa opcion, ni desde la API —
      `cerrar_cuenta` revisa `puede_cobrar` en el servidor, y `MeseroPedido` esconde la opcion
- [x] El mesero puede listar sus pedidos activos y editar los ya enviados — [[SPEC-011 - Novedades sobre Pedidos Enviados]]
- [x] Un pedido armado desde cero produce exactamente la misma estructura que uno escaneado
      — `MeseroPedido` firma el carrito y lo confirma con las mismas dos llamadas
      (`firmarPedido`, `confirmarPedido`) que recorre un QR escaneado
- [x] El pedido confirmado queda amarrado al usuario del mesero — **verificado**:
      `Pedido.mesero` queda seteado al usuario autenticado que confirmó
- [x] La burbuja de notificaciones muestra el contador correcto y sobrevive a recargar —
      **verificado**
- [x] El mesero solo ve notificaciones de **sus** pedidos — **verificado**
- [x] Marcar ENTREGADO apaga la notificacion correspondiente — **verificado**: contador de
      `+2` a 0 al entregar

## Dependencias

- [[SPEC-002 - QR de Pedido]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[SPEC-006 - Notificaciones]]

## Preguntas abiertas

> [!success] Resuelta (2026-08-27)
> *Puede el mesero agregar items a un pedido ya enviado?* **Si**, y ademas cambiarle el
> destino. Ver [[SPEC-011 - Novedades sobre Pedidos Enviados]]. Esa spec incorpora al
> modulo del mesero el **registro de pedidos activos**, que hoy no existe
> (`GET /api/pedidos/`).
