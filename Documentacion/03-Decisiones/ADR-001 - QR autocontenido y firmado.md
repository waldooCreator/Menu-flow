---
tipo: adr
id: ADR-001
estado: aceptada
fecha: 2026-08-21
tags: [qr, arquitectura, seguridad]
---

# ADR-001 — QR autocontenido y firmado

**Estado:** Aceptada · **Fecha:** 2026-08-21

## Contexto

El cliente arma su pedido desde internet y genera un QR que el mesero escanea. Habia que
decidir donde vive la informacion del pedido mientras tanto. El autor pidio expresamente
**no tener que almacenar esos QR en base de datos**.

## Opciones consideradas

**A. Guardar el carrito en el servidor y que el QR lleve solo un token.**
Simple de implementar, pero obliga a escribir en base de datos cada vez que alguien genera
un QR — incluidos los muchos que se generan y nunca se usan. Contradice el pedido explicito
del autor.

**B. Meter el pedido completo dentro del QR, firmado.**
Nada que almacenar. El QR es autosuficiente. Requiere cuidar el tamano y la integridad.

## Decision

**Opcion B.** El QR lleva el pedido adentro, firmado con HMAC. No se guarda ninguna imagen
de QR, y el pedido no se persiste hasta que el mesero lo confirma.

Detalles del formato en [[SPEC-002 - QR de Pedido]].

## Justificacion

- **Hay precedente masivo.** Es el mismo mecanismo del Certificado COVID Digital de la UE:
  datos y firma dentro del QR, verificacion sin viaje al servidor, miles de millones de usos.
- **Cabe de sobra — probado, no solo estimado (2026-08-24).** Un pedido de 15-20 items con
  observaciones ocupa ~350 bytes reales, medidos generando y decodificando QR de verdad.
  El limite comodo esta cerca de 900 bytes. Ver [[Viabilidad Tecnica del QR]] para los
  numeros completos, incluido el caso donde el limite si se supera.
- **No ensucia la base** con carritos abandonados.
- **Privacidad:** el payload viaja en el fragmento de la URL, que nunca llega al servidor,
  asi que el pedido no queda en logs de acceso.

## Consecuencias

**Positivas**
- Cero almacenamiento para los QR
- Funciona aunque el telefono del cliente pierda conexion despues de generarlo
- El control anti-duplicado sale gratis guardando el id del QR en la fila del pedido

**Negativas / a vigilar**
- Hay que respetar el limite de tamano; existe un plan B para pedidos enormes
- Los IDs del menu deben ser estables en el tiempo
- Exige gestionar un secreto de firma en el servidor

## Enlaces

- [[SPEC-002 - QR de Pedido]]
- [[Viabilidad Tecnica del QR]]
- [[ADR-005 - Escaneo con libreria JS]]
