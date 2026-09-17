---
tipo: producto
actualizado: 2026-08-25
tags: [vision, producto]
---

# Vision del Producto

## En una frase

Un sistema web para restaurantes, **100% parametrizable y desplegable por restaurante**,
que conecta cliente, mesero, estaciones de preparacion y administrador **exclusivamente
por mensajes dentro de la aplicacion** (sin impresoras ni hardware especial), usando
**codigos QR** como puente entre el cliente y el mesero, y dejando **toda venta amarrada
a un usuario responsable** para efectos contables y de auditoria.

## Los tres ejes

### 1. Parametrizacion total
El mismo software sirve a varios restaurantes cambiando configuracion, nunca codigo.
Colores, textos, logo, menu, estaciones, mesas, roles: todo se administra.
Ver [[SPEC-007 - Administracion y Parametrizacion]].

### 2. El QR como puente
El cliente arma su pedido y el mesero lo carga escaneando, sin volver a digitar nada.
Ver [[SPEC-002 - QR de Pedido]] y [[ADR-001 - QR autocontenido y firmado]].

### 3. Trazabilidad
Cada venta tiene dueno, cada cambio queda auditado, todo se resume en KPIs.
Ver [[SPEC-008 - Contabilidad y Auditoria]].

## Requisitos originales

Vienen de una nota manuscrita del autor. Son la semilla de todo lo demas.

| # | Requisito | Spec derivada |
|---|---|---|
| 1 | Sistema 100% parametrizable, panel administrable con modulo contable y KPIs, gestion de usuarios y roles | [[SPEC-007 - Administracion y Parametrizacion]] |
| 2 | Modulo cliente: menu con filtros e imagenes, generacion de QR del pedido, seccion PQRSF | [[SPEC-003 - Menu del Cliente]], [[SPEC-010 - PQRSF]] |
| 3 | Modulo mesero: crear pedido desde cero o escanear el QR del cliente, enviar a cocina con observaciones | [[SPEC-004 - Modulo Mesero]] |
| 4 | Modulo admin: configuracion completa y seccion contable con ventas por dia/semana/mes, KPIs y dashboards | [[SPEC-007 - Administracion y Parametrizacion]], [[SPEC-008 - Contabilidad y Auditoria]] |
| 5 | Gestion de usuarios, toda venta amarrada a un usuario y auditable | [[SPEC-008 - Contabilidad y Auditoria]] |
| 6 | Arquitectura portable: redesplegable en distintos servidores y bases de datos | [[SPEC-009 - Portabilidad Multi-restaurante]] |

## Fuera de alcance

- **Pagos y facturacion electronica.** No hay pasarela de pago ni emision de factura.
  El modulo contable solo *registra* ventas para reportes y auditoria.
- **Domicilios y pedidos remotos.** El sistema asume un cliente sentado en una mesa.
  Ver [[ADR-002 - El mesero confirma el pedido]].
- **Aplicacion nativa.** Todo corre en navegador.

## Plan de fases

**Fase 0 — Contrato de datos + prototipo visual** *(terminada)*
Definir la forma de los datos y construir la pagina del cliente como prototipo estatico.
Sin backend, sin base de datos, sin decidir el stack.

**Fase 1 — Rebanada vertical**
Un solo flujo completo de punta a punta: menu, carrito, QR, escaneo del mesero, comanda a
la estacion, notificacion, entregado. Delgado pero funcionando de verdad.

> [!success] Rebanada vertical CERRADA (2026-08-25)
> Los ocho pasos del flujo funcionan de punta a punta, verificados en la interfaz real:
> menu → carrito → QR real → mesero escanea → verifica → confirma → **rutea a estaciones**
> → estacion marca listo → **notifica al mesero** → **mesero marca entregado**. Con precio
> y nombre congelados en cada detalle.
>
> **Lo que queda fuera a proposito, para la siguiente etapa:** el diseño visual de Fase 0
> (`/prototipo`) — lo construido es funcional, no es ese diseño; el transporte de
> notificaciones en tiempo real (hoy es consulta periodica); el escaneo por camara en vivo
> (hoy es por imagen subida); el Camino B del mesero (armar pedido desde cero); y el
> cronometro/aviso sonoro de las estaciones (UX).

**Fase 2 — Ancho**
Administracion, parametrizacion, contabilidad, KPIs, auditoria, PQRSF.

> [!note] Por que ese orden
> Lo mas riesgoso del proyecto es la cadena QR + notificaciones en tiempo real. Construir
> todo el frontend primero deja ese riesgo para el final, que es el peor momento para
> descubrir un problema.
