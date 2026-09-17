---
tipo: producto
actualizado: 2026-09-14
tags: [pendientes, decisiones]
---

# Preguntas Abiertas

Lo que falta decidir. Cada una, cuando se resuelva, se convierte en un ADR o en una
modificacion de spec.

## Importantes

- [ ] **Transporte de tiempo real** — con Django, la opcion natural es Django Channels
      (WebSockets) en vez de SSE. Confirmar y afecta [[SPEC-006 - Notificaciones]].
      **Implementado por ahora con consulta periodica** (el respaldo que la spec ya
      preveia), no con canal en tiempo real — sigue pendiente.

- [ ] **Varios clientes en la misma mesa** — cada uno genera su QR y se suman al mismo
      pedido de la mesa, o cada QR es un pedido independiente?
      Afecta [[SPEC-002 - QR de Pedido]].

- [ ] **Como se pasa Springfield al sistema nuevo** — que datos se traen de su base PHP
      (clientes, platos, historial de ventas), si se importa el historial o se arranca de
      cero con corte en una fecha, y cuanto tiempo conviven los dos sistemas. *(Anotada
      2026-09-14.)*

- [ ] **Donde y como corre en produccion** — servidor, dominio, HTTPS, respaldos y quien
      los vigila. Hoy todo corre en local. Afecta [[SPEC-009 - Portabilidad Multi-restaurante]].
      *(Anotada 2026-09-14.)*

## Menores

- [ ] **PQRSF** — puede el cliente anonimo enviarlo sin identificarse? El admin responde
      dentro del sistema o solo lo lee? Ver [[SPEC-010 - PQRSF]].

- [ ] **Idiomas y moneda** — el sistema debe soportar mas de un idioma?

## Resueltas

- [x] ~~Como llega el pedido a cocina?~~ --> Solo mensajes en la app, tablero de cards.
      Ver [[SPEC-005 - Estaciones y Ruteo]].
- [x] ~~Hay pagos o facturacion?~~ --> Cobro si: cuenta, medios de pago, caja y tiquete
      imprimible ([[SPEC-013 - La Cuenta]], [[SPEC-014 - Turno de Caja y Cajas de Fondos]],
      [[SPEC-016 - Tiquete de Venta]]). Pasarela de pagos y facturacion electronica, no.
- [x] ~~Modelo de datos detallado?~~ --> Vive en los modelos de Django de cada app; no se
      mantiene un documento aparte.
- [x] ~~Como se identifica la mesa?~~ --> QR estatico pegado en la mesa.
      Ver [[SPEC-001 - QR de Mesa]].
- [x] ~~Una estacion o varias?~~ --> Varias, configurables, con ruteo por categoria.
- [x] ~~Es viable el QR autocontenido?~~ --> Si, con precedentes.
      Ver [[Viabilidad Tecnica del QR]].
- [x] ~~Por que confirma el mesero?~~ --> Seguridad.
      Ver [[ADR-002 - El mesero confirma el pedido]].
- [x] ~~Stack tecnologico?~~ --> Django + Vue + PostgreSQL.
      Ver [[ADR-006 - Stack Django, Vue y PostgreSQL]].
- [x] ~~Como se sirve la pagina del cliente?~~ --> Todo en Vue. Django es solo API y
      permisos, nunca renderiza HTML. Ver [[ADR-006 - Stack Django, Vue y PostgreSQL]].
- [x] ~~Modificar un pedido ya enviado?~~ --> Si. El mesero puede cambiar el destino
      (otra mesa o domicilio) y editar los platos de un pedido en curso. Se registra como
      **evento de solo insercion**, nunca como UPDATE, y la estacion lo ve en rojo. Ver
      [[SPEC-011 - Novedades sobre Pedidos Enviados]] y
      [[ADR-007 - Una novedad es un evento, no una modificacion]].
- [x] ~~Notificacion con varias estaciones?~~ --> Por cada comanda lista, no una sola al
      final. Mas simple de modelar, mas realista (una estacion no espera a otra), y da
      metricas granulares por estacion (coherente con
      [[ADR-004 - LISTO y ENTREGADO son estados distintos]]). Ver [[SPEC-006 - Notificaciones]].
