---
fecha: 2026-09-07
tipo: bitacora
specs: [SPEC-017, SPEC-003, SPEC-005]
---

# 2026-09-07 — Disponibilidad desde cocina

Se implemento SPEC-017 para que cocina pueda agotar y reactivar platos sin
entrar al panel administrativo.

## Implementado

- Endpoint separado para cambiar solo `disponible`.
- Permiso exclusivo para cocina y administrador.
- Auditoria de usuario y fecha del cambio.
- Bloqueo de fila para dos cambios simultaneos.
- Revalidacion dentro de la transaccion de confirmacion del pedido.
- Rechazo completo, con el nombre del plato, si uno se agoto.
- Los pedidos ya confirmados no se modifican.
- Busqueda y controles de disponibilidad en el tablero de cocina.
- Refresco del menu del cliente al volver a la pestaña y cada 60 segundos.
- Carrito bloqueado con platos agotados y aviso nombrando el plato.
- Aviso rojo en la verificacion del QR y proteccion equivalente en Camino B.

## Comprobacion

La migracion se aplico a la base de desarrollo. `manage.py check`,
`makemigrations --check`, `npm run build` y 59 pruebas Django quedan en verde.
