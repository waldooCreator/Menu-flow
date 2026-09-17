---
tipo: investigacion
fecha: 2026-08-21
tags: [competencia, mercado, investigacion]
---

# Analisis de Competencia

## Plataformas de menu QR

| Plataforma | Que hace |
|---|---|
| **me&u** (antes Mr Yum) | Lider del sector. QR estatico por mesa con numero incrustado desde 2021. Pedido y pago desde el telefono |
| **Flipdish** | Pedido con marca propia por restaurante |
| **Sunday** | QR en mesa enfocado en el pago |
| **Toast** | Genera paginas de pedido por restaurante |
| **RestoLabs**, **Jamezz** | Pedido por QR, va directo al POS y la cocina |

## La diferencia clave con este proyecto

> [!important] El mercado quita al mesero; este proyecto lo conserva
> En **todos** los sistemas investigados, el cliente pide **directo desde su telefono al
> servidor**: no hay QR de pedido ni transferencia mesero-cliente, porque no hay mesero de
> por medio en ese paso. El pedido va del navegador del cliente a la cocina.

Este proyecto hace algo distinto **a proposito**: el mesero puede armar el pedido desde cero
**o** recibirlo por QR, y siempre confirma antes de que entre a las estaciones.

La razon es de seguridad, no de comodidad. Ver [[ADR-002 - El mesero confirma el pedido]].

**Consecuencia practica:** hay menos referencias que copiar para el flujo del mesero, porque
casi nadie lo hace asi. Para el resto (QR de mesa, menu, tablero de cocina) si hay abundante
precedente.

## Enlaces

- [[ADR-002 - El mesero confirma el pedido]]
- [[Viabilidad Tecnica del QR]]
- [[Vision del Producto]]
