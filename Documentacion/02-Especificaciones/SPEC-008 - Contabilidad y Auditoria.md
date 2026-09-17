---
tipo: spec
id: SPEC-008
estado: borrador
actualizado: 2026-09-14
tags: [contabilidad, auditoria, kpi]
---

# SPEC-008 — Contabilidad y Auditoria

> [!warning] Estado: Borrador

## Proposito

Registrar bien todas las ventas y no dejar que el pasado cambie, para poder calcular
ingresos, mostrar KPIs y auditar todo.

## Alcance

- Registro de todas las ventas con su detalle
- Reportes por dia, semana, mes y rangos personalizados
- KPIs y dashboards
- Registro de auditoria

## Fuera de alcance

- **Pagos y facturacion electronica.** No hay pasarela ni emision de factura
- Contabilidad formal (libros, impuestos, nomina)
- Integracion con software contable externo

## Comportamiento

### KPIs previstos

Ingresos, ticket promedio, platos mas vendidos, ventas por mesero, ventas por estacion,
tiempos de preparacion y de entrega, horas pico.

Los tiempos salen gratis de los timestamps de los estados del pedido, gracias a
[[ADR-004 - LISTO y ENTREGADO son estados distintos]].

### Dos reglas no negociables

> [!danger] Regla 1 — congelar el precio en la venta
> **El detalle de la venta guarda el precio y el nombre del momento en que se vendio**, no
> solo una referencia al plato. Si manana cambia el precio del menu, los reportes del mes
> pasado deben seguir mostrando el precio de entonces.
>
> Guardar solo el ID y resolver el precio por relacion hace que el historial **se reescriba
> solo** cada vez que se cambia un precio. Es el error mas comun y el mas caro de arreglar
> despues.

> [!danger] Regla 2 — auditoria de solo insercion
> La tabla de auditoria **nunca se actualiza ni se borra**. Registra usuario, accion,
> entidad afectada, datos antes, datos despues, fecha y origen.
>
> Ahi caen las anulaciones, los cambios de precio, las altas y bajas de usuarios y los
> cambios de configuracion.

### Anulaciones

**Los pedidos no se borran nunca.** Se **anulan**, con motivo y usuario responsable.

## Criterios de aceptacion

- [x] Cambiar el precio de un plato no altera los reportes de periodos anteriores — el
      renglon congela precio y nombre, y los reportes suman lo congelado
- [x] Toda venta tiene un usuario responsable — el mesero del pedido y quien cerro la cuenta
- [x] Anular un pedido exige motivo y queda registrado con su responsable —
      [[SPEC-013 - La Cuenta]] y [[SPEC-015 - Historial de Ventas]]
- [ ] La tabla de auditoria no admite actualizacion ni borrado — **no se cumple**: no hay
      una tabla de auditoria como tal. Los registros de dinero (movimientos de caja,
      novedades) solo se insertan, pero por convencion del codigo; nada en la base lo impide
- [x] Los reportes por dia, semana y mes cuadran con la suma de las ventas individuales —
      [[SPEC-018 - Reportes de Venta]], con pruebas
- [ ] Se puede reconstruir quien hizo que y cuando, para cualquier cambio — **a medias**:
      ventas, anulaciones, movimientos de caja, turnos y novedades si guardan autor y fecha;
      los cambios hechos desde el panel de administracion no

> [!note] Revisado 2026-09-14
> La spec sigue en borrador porque su pieza propia —una auditoria general— no se ha
> diseñado. Aun asi, cuatro de sus criterios ya se cumplen por lo que construyeron otras
> specs, y se marcan para que no parezca que no hay nada.

## Dependencias

- [[SPEC-004 - Modulo Mesero]] — origen de las ventas
- [[SPEC-007 - Administracion y Parametrizacion]] — los cambios que se auditan
