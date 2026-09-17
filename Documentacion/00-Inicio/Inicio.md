---
tipo: moc
actualizado: 2026-09-16
tags: [inicio, moc]
---

# Sistema de Gestion para Restaurantes

> [!info] Punto de entrada
> Esta es la boveda de contexto del proyecto. Si eres Claude (Code o Desktop) y estas
> retomando el trabajo, **empieza por aqui**, luego lee [[Metodologia - Spec Driven Development]]
> y [[Vision del Producto]]. Para el detalle de que usa el codigo hoy, ver [[Stack Tecnologico]].

## Estado actual

> [!note] Revisado el 2026-09-14
> Specs, comparativa con Springfield y este tablero se pusieron al dia contra el codigo.
> Detalle en [[2026-09-14 - Documentacion puesta al dia]].

| Aspecto | Estado |
|---|---|
| Fase | **Fase 1 cerrada, con el diseño de Fase 0 portado.** El flujo completo del restaurante funciona **en local**; todavia no esta en produccion |
| Stack tecnologico | **Django (solo API, DRF) + Vue + Tailwind v4 + PostgreSQL** — ver [[ADR-006 - Stack Django, Vue y PostgreSQL]] |
| Codigo escrito | Backend Django en `/backend` (apps `nucleo`, `configuracion`, `menu`, `pedidos`, `estaciones`, `ventas`, `clientes`), frontend Vue en `/frontend` (cliente, carrito, mesero, caja, estacion, admin). `/prototipo` queda como referencia historica |
| Pruebas | **217 del servidor** (2026-09-16). `pedidos/tests.py` cubre SPEC-005, 011, 012 y 013; `menu/tests.py`, SPEC-017 y SPEC-023; `ventas/tests.py`, además, SPEC-024. `configuracion` no tiene pruebas; el frontend no tiene suite |
| Frente a Springfield | **31 de 48** secciones hechas, 5 parciales, 2 faltan, 4 por decidir, 6 fuera de alcance — ver [[Comparativa Sidebar - Springfield vs Sistema Nuevo]] |
| Defectos abiertos | Ninguno conocido. Los dos que salieron en la revision (aviso de domicilio listo y comanda tomada dos veces) se corrigieron el 2026-09-14 |
| Pendiente de producto | Costo de envio de domicilios, resumen operativo, razon social y representante, configuraciones como interruptores, "recoger" en el salon, vista de todas las comandas, restablecer desde el panel. Tiempo real (hoy polling). Recetas e inventario **descartados**: Springfield no los usa |
| Pendiente para produccion | Servidor, HTTPS, ajustes de seguridad (`DEBUG` en `True` por defecto, sin `SECURE_*`), respaldos, **traer los datos de Springfield** desde su base PHP y una base limpia sin datos de demostracion. Nada de esto tiene spec |
| Ultimo cierre | **Revision del autor (2026-09-16):** promos sin franja, quien cobra en Configuracion → Cobro, tablero unificado de cocina y **[[SPEC-024 - Busqueda en Libro e Historial de Turnos]]**. Antes, **[[SPEC-023 - Promociones]]** implementada el 2026-09-14: combos con vigencia, primeros en el menu, desglose en cocina, reporte por producto e interruptor para unificar estaciones. Ese mismo dia: revision de la documentacion y dos defectos de cocina corregidos |
| Proxima etapa | **Costo de envio de domicilios** (lo ultimo que falta del bloque Contable) o **la spec del paso a produccion**. Decide el autor |

## La idea en una frase

Un sistema web para restaurantes, **100% parametrizable y desplegable por restaurante**,
que conecta cliente, mesero, estaciones de preparacion y administrador **solo por mensajes
dentro de la app**, usando **codigos QR** como puente entre cliente y mesero, y dejando
**toda venta amarrada a un usuario responsable**.

## Producto

- [[Vision del Producto]] — el que y el por que
- [[Actores y Roles]] — quien usa el sistema
- [[Flujo Principal]] — el recorrido de punta a punta
- [[Glosario]] — vocabulario del dominio

## Especificaciones

| ID | Spec | Estado |
|---|---|---|
| 001 | [[SPEC-001 - QR de Mesa]] | **Implementada** — abierto: entrar por QR no salta el hero |
| 002 | [[SPEC-002 - QR de Pedido]] | **Implementada** — abiertos: observaciones por indice y Plan B |
| 003 | [[SPEC-003 - Menu del Cliente]] | **Implementada** — sin medir en 4G ni en telefono real |
| 004 | [[SPEC-004 - Modulo Mesero]] | **Implementada** — abierto: editar un pedido escaneado antes de confirmar |
| 005 | [[SPEC-005 - Estaciones y Ruteo]] | **Implementada** |
| 006 | [[SPEC-006 - Notificaciones]] | **Implementada** (polling) |
| 007 | [[SPEC-007 - Administracion y Parametrizacion]] | **Implementada** — abierto: auditoria de cambios de configuracion |
| 008 | [[SPEC-008 - Contabilidad y Auditoria]] | Borrador — 4 de 6 criterios ya se cumplen por otras specs |
| 009 | [[SPEC-009 - Portabilidad Multi-restaurante]] | Aprobada — sin probar en un servidor real |
| 010 | [[SPEC-010 - PQRSF]] | Borrador |
| 011 | [[SPEC-011 - Novedades sobre Pedidos Enviados]] | **Implementada** |
| 012 | [[SPEC-012 - Vista de Salon y Estado de Mesas]] | **Implementada** |
| 013 | [[SPEC-013 - La Cuenta]] | **Implementada** |
| 014 | [[SPEC-014 - Turno de Caja y Cajas de Fondos]] | **Implementada** |
| 015 | [[SPEC-015 - Historial de Ventas]] | **Implementada** |
| 016 | [[SPEC-016 - Tiquete de Venta]] | **Implementada** |
| 017 | [[SPEC-017 - Agotar un Plato desde Cocina]] | **Implementada** |
| 018 | [[SPEC-018 - Reportes de Venta]] | **Implementada** — cinco reportes |
| 019 | [[SPEC-019 - Clientes]] | **Implementada** — abierto a proposito: elegir entre direcciones guardadas |
| 020 | [[SPEC-020 - Activos Liquidos]] | **Implementada** |
| 021 | [[SPEC-021 - Navegacion del Personal]] | **Implementada** — falta el recorrido con cada rol |
| 022 | [[SPEC-022 - Auditoria Responsive]] | **Implementada** — falta revisar el carrito del cliente en un telefono real |
| 023 | [[SPEC-023 - Promociones]] | **Implementada** — revisada 2026-09-16: sin franja y tablero unificado |
| 024 | [[SPEC-024 - Busqueda en Libro e Historial de Turnos]] | **Implementada** (2026-09-16) |
| 025 | [[SPEC-025 - Vueltos]] | Borrador — anotada 2026-09-16, sin definir |

## Decisiones tomadas

- [[ADR-001 - QR autocontenido y firmado]]
- [[ADR-002 - El mesero confirma el pedido]]
- [[ADR-003 - Una base de datos por restaurante]]
- [[ADR-004 - LISTO y ENTREGADO son estados distintos]]
- [[ADR-005 - Escaneo con libreria JS]]
- [[ADR-006 - Stack Django, Vue y PostgreSQL]]
- [[ADR-007 - Una novedad es un evento, no una modificacion]]
- [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]
- [[ADR-009 - La promocion es un tipo de plato]]

## Diseno

- [[Sistema de Diseno]] — tokens, color, tipografia, geometria
- [[Analisis de Sweetgreen]] — de donde salio el sistema
- [[Modelo de Pagina del Cliente]] — estructura de la pagina
- [[Referencias Visuales]] — sitios de referencia

## Investigacion

- [[Viabilidad Tecnica del QR]] — se puede hacer, con precedentes
- [[Analisis de Competencia]] — que hacen me&u, Mr Yum y otros
- [[Novedades sobre Pedidos en Curso]] — editar pedidos enviados, y las 18 novedades que faltan
- [[Que le Falta para ser un POS Vendible]] — ventas, caja, meseros y multi-restaurante
- [[Inventario del Sistema Actual de Springfield]]
- [[Que debe poder hacer un Cajero]] — como funciona su sistema hoy
- [[Comparativa Sidebar - Springfield vs Sistema Nuevo]] — **las 48 secciones, una por una, con estado actual**

## Bitacora

- [[2026-08-21 - Ajustes esteticos del hero y entradas]]
- [[2026-08-21 - Arranque y prototipo visual]]
- [[2026-08-21 - Carrito, modal y responsive]]
- [[2026-08-24 - API REST y frontend Vue conectado]]
- [[2026-08-24 - Backend Django y primera configuracion real]]
- [[2026-08-24 - Prueba tecnica del QR y Vue confirmado]]
- [[2026-08-24 - Rebanada vertical del QR de punta a punta]]
- [[2026-08-25 - Correccion del fondo decorativo, mapa real y dos bugs de campo]]
- [[2026-08-25 - Diseno portado a Vue con Tailwind]]
- [[2026-08-25 - Rebanada vertical cerrada, estaciones y notificaciones]]
- [[2026-08-25 - Roles, camara y Camino B del mesero]]
- [[2026-08-25 - Tema Springfield y enlace WhatsApp]]
- [[2026-08-26 - Salon de mesas y domicilio sin mesa]]
- [[2026-08-27 - La cuenta y el cobro]]
- [[2026-08-27 - Novedades sobre pedidos enviados]]
- [[2026-08-27 - Panel de administracion completo]]
- [[2026-08-27 - Turno de caja y cuadre]]
- [[2026-08-30 - Zona de domicilios y cobrar al finalizar]]
- [[2026-08-31 - Tres correcciones de la prueba end to end]]
- [[2026-09-03 - Concurrencia_ cobro duplicado y pedidos perdidos]]
- [[2026-09-03 - El libro de caja y el historial de turnos]]
- [[2026-09-03 - Historial de ventas]]
- [[2026-09-03 - Notificaciones, tercer nivel de observaciones y turno por usuario]]
- [[2026-09-03 - Pantalla de turno con fondo por caja]]
- [[2026-09-03 - Pausa - facturas imprimibles pendientes]]
- [[2026-09-07 - Parametrizacion de menu y negocio]]
- [[2026-09-07 - SPEC-016 Tiquete de venta]]
- [[2026-09-07 - SPEC-017 Disponibilidad desde cocina]]
- [[2026-09-07 - SPEC-019 Clientes]]
- [[2026-09-07 - SPEC-020 Activos liquidos]]
- [[2026-09-08 - SPEC-020 y SPEC-021]]
- [[2026-09-08 - SPEC-022 Correccion responsive]]
- [[2026-09-14 - Documentacion puesta al dia]]
- [[2026-09-14 - SPEC-023 Promociones]]
- [[2026-09-16 - Revision del autor - promos, cobro, cocina, libro y turnos]]
- [[2026-09-14 - Correccion de dos defectos de cocina]]

## Preguntas abiertas

Ver [[Preguntas Abiertas]] — lo que falta decidir antes de avanzar.
