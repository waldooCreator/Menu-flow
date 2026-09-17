---
tipo: producto
actualizado: 2026-08-21
tags: [actores, roles]
---

# Actores y Roles

| Rol | Autenticacion | Que hace |
|---|---|---|
| **Cliente** | Anonimo, no crea cuenta | Escanea el [[SPEC-001 - QR de Mesa|QR de su mesa]], navega el menu, arma su pedido, genera el [[SPEC-002 - QR de Pedido|QR del pedido]], envia [[SPEC-010 - PQRSF|PQRSF]] |
| **Mesero** | Con usuario | Toma pedidos desde cero o escaneando el QR del cliente, recibe notificaciones, entrega en mesa |
| **Estacion** | Con usuario | Ve el tablero de comandas de su estacion, marca en preparacion y listo |
| **Administrador** | Con usuario | Configura el sistema, gestiona usuarios y menu, consulta contabilidad, KPIs, auditoria y PQRSF |

## Reglas transversales

- Los roles y sus permisos son **configurables**, no fijos en codigo.
  Ver [[SPEC-007 - Administracion y Parametrizacion]].
- **Toda venta queda amarrada a un usuario real** (el mesero que la confirmo).
  Ver [[ADR-002 - El mesero confirma el pedido]].
- El cliente **nunca se autentica**. Es la razon por la que existe la confirmacion del mesero.

## Sobre las estaciones

Una estacion no es una persona sino un **puesto de preparacion**: cocina, postres, bar,
parrilla. Puede haber varias personas atendiendo una estacion, y el sistema debe soportar
un numero arbitrario de estaciones configurables.

Ver [[SPEC-005 - Estaciones y Ruteo]].
