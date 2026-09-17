---
tipo: bitacora
fecha: 2026-09-16
tags: [estres, concurrencia, cocina, caja, cuadre, defecto]
---

# 2026-09-16 — Prueba de estrés: 3 meseros, 50 clientes, 10 minutos

## Cómo se hizo

- **Base aparte:** `terra_estres`, copia de la de desarrollo, con 20 mesas. Backend propio en
  el puerto 8002 (`backend-estres` en `.claude/launch.json`). La base de desarrollo no se tocó.
- **Solo HTTP, como la app:** `scratchpad/estres.py`. Estaciones unificadas (todo a una sola
  cocina) y meseros cobrando.
- **Personal:** ana, bryam y carla, con turno abierto por el admin y $100.000 de fondo cada uno.
  Dos cocineros (`cocina`, `esteban`) que se toman hasta 3 comandas cada uno, sin coordinarse.
- **50 clientes en tres oleadas:** 18 en mesa por QR, 12 en mesa a mano y 20 domicilios por
  QR, 6 de ellos pagados por anticipado. Perfiles: agregan un plato con el pedido en cocina,
  piden otra ronda, pagan antes de recibir, tocan dos veces "Cobrar", o dos meseros leen el
  mismo QR.
- **Pagos:** efectivo con vueltos (billetes de $10.000, $50.000 y $100.000), Nequi, Daviplata,
  Bancolombia y datáfono, con y sin propina.
- **Cierre:** cada mesero cuenta su efectivo, **bryam con $7.000 de menos y carla con $3.500 de
  más, a propósito**. Luego el admin consigna el efectivo a Bancolombia dejando $200.000 de base.

## Resultados

| Qué | Resultado |
|---|---|
| Peticiones | 2.799 en 11 minutos, **0 errores 500** |
| Tiempo de respuesta | p50 ≈ 100 ms, p95 ≤ 285 ms, máximo 385 ms (servidor de desarrollo) |
| Clientes atendidos | **50/50**, 55 pedidos, 50 cuentas cobradas, 0 abiertas, 0 pedidos colgados |
| Cocina | Pico de **15 en cola + 6 preparándose** (minuto 4:25). Espera hasta que la tomaran: mediana 65 s, máx 3 min. Hasta quedar lista: mediana 2:10, máx 4:42 |
| Choques de cocineros | 4 veces tomaron la misma comanda: **409 correcto**, ninguna doble |
| Mismo QR leído por dos meseros | [201, 409]: **un solo pedido** |
| Doble toque en "Cobrar" | 2 veces [200, 400]: **un solo cobro** |
| Cocina intenta editar un pedido | 5 veces: **403 correcto** |
| Mesero agrega plato con el pedido en cocina | 9 veces: la cocina lo vio en rojo y **la cuenta lo cobró** |
| Movimientos | Un movimiento de venta por cuenta y por el total exacto; 0 ventas fuera de turno |
| Cuadres | ana **0**, bryam **−$7.000**, carla **+$3.500**: el sistema detectó exacto los descuadres puestos a propósito |
| Consignación | $2.667.800 a Bancolombia; Efectivo quedó en $200.000 |
| Vueltos | $338.150 dados en vueltos. Ningún mesero se quedó sin cambio, pero **el sistema no lo registra** (ver [[SPEC-025 - Vueltos]]) |

## Defecto encontrado

> [!bug] Se puede agregar un plato a un pedido que ya se cobró, y no se cobra
> Si la cuenta se cobra mientras el pedido sigue en cocina, "agregar plato" lo acepta (200).
> El plato llega a cocina y se sirve, pero la cuenta ya está cerrada con el total viejo.
> Pasó **3 de 3 veces**: $10.000, $16.000 y $26.000, **$52.000 servidos sin cobrar**.
>
> **Causa:** `pedidos/novedades.py` solo revisa el estado del **pedido** (pendiente, en
> preparación o listo), nunca si su **cuenta** sigue abierta. Lo mismo pasa con cambiar la
> cantidad o quitar un plato de un pedido ya cobrado.
>
> **Corregido el mismo día.** Decisión del autor: cobrar significa que el cliente pagó para
> irse. Cobrar ahora **libera la mesa**, salvo que se marque **pago anticipado**. Un pedido
> ya cobrado **rechaza** agregar, quitar o cambiar cantidades (con la cuenta bloqueada, como
> el cobro) y pide crear un pedido nuevo, que abre otra cuenta. La pantalla de Cuentas explica
> esto antes de cobrar. Ver [[SPEC-013 - La Cuenta]].

## Lo que no es defecto, pero se vio

- **Las mesas quedaban "ocupadas" después de cobrar.** Era así por diseño: el mesero la liberaba
  a mano. Desde la corrección de arriba, cobrar la libera.
- **El nombre de la mesa no es único.** Las mesas de prueba "Mesa 7", "Mesa 9" y "Mesa 12"
  convivieron con otras del mismo nombre. Lo causó el simulador, pero la base lo permite.
