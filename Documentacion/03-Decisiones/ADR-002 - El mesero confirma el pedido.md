---
tipo: adr
id: ADR-002
estado: aceptada
fecha: 2026-08-21
tags: [seguridad, mesero, flujo]
---

# ADR-002 — El mesero confirma el pedido

**Estado:** Aceptada · **Fecha:** 2026-08-21

## Contexto

En los sistemas de pedido por QR del mercado (me&u, RestoLabs, Jamezz) el cliente pide
**directo desde su telefono al servidor**: no hay mesero de por medio y el pedido va solo a
la cocina. Este proyecto hace algo distinto a proposito, y hay que dejar registrado por que.

## Opciones consideradas

**A. El pedido del cliente entra directo a las estaciones.**
Es el estandar del mercado. Mas rapido, menos personal involucrado.

**B. El mesero escanea el QR y confirma antes de que entre a las estaciones.**
Un paso mas, pero con un humano validando.

## Decision

**Opcion B.** Todo pedido pasa por la confirmacion de un mesero, venga de un QR o armado
desde cero.

## Justificacion

**Es una decision de seguridad, no de comodidad.** El cliente **nunca esta autenticado**.
Sin la confirmacion del mesero quedan abiertos dos fraudes:

1. **Pedido fantasma.** Cualquiera podria generar un QR desde su casa y hacer que un pedido
   aparezca en cocina sin haber pisado el restaurante.
2. **Pedir e irse.** Un cliente podria ordenar en la mesa y marcharse antes de que llegue la
   cuenta, sin que quede registrado quien tomo ese pedido.

Al pasar por el mesero, la venta **siempre queda amarrada a un usuario real y presente**,
que es quien la valida y responde por ella. Eso conecta directamente con el requisito 5 del
proyecto y con [[SPEC-008 - Contabilidad y Auditoria]].

> [!success] Verificado en codigo real (2026-08-24)
> `POST /api/pedidos/confirmar/` exige `IsAuthenticated`. Probado: sin token → **401**; con
> token → crea el pedido y `Pedido.mesero` queda seteado al usuario que confirmo. Los
> endpoints de firmar y verificar (que el cliente anonimo si usa) son publicos a proposito
> — la barrera de seguridad esta exactamente donde debe estar: en la creacion del pedido,
> no en su lectura.

## Consecuencias

**Positivas**
- Toda venta tiene responsable identificable y auditable
- El mesero detecta errores antes de que lleguen a la estacion
- Conserva el rol tradicional del mesero, util para clientes que prefieren pedir en persona

**Negativas / a vigilar**
- Un paso mas en el flujo; el pedido no llega instantaneamente a la estacion
- Se aparta del estandar del mercado, asi que no hay tantas referencias para copiar

## Enlaces

- [[SPEC-004 - Modulo Mesero]]
- [[SPEC-002 - QR de Pedido]]
- [[Analisis de Competencia]]
