---
tipo: adr
id: ADR-004
estado: aceptada
fecha: 2026-08-21
tags: [estados, modelo, kpi]
---

# ADR-004 — LISTO y ENTREGADO son estados distintos

**Estado:** Aceptada · **Fecha:** 2026-08-21

## Contexto

La descripcion original tenia un solo boton en la pantalla de la estacion, llamado
"Entregado", que notificaba al mesero.

## Decision

Separar en dos estados:

- **LISTO** — la estacion termino. Dispara la notificacion al mesero.
- **ENTREGADO** — el mesero lo llevo a la mesa. Apaga la notificacion y cierra la venta.

Se agrega ademas **EN_PREPARACION**, que se activa cuando la estacion abre la card.

## Justificacion

- Con los timestamps de ambos estados salen **gratis** dos metricas de oro para un
  restaurante: cuanto se demora la preparacion y cuanto se demora el mesero en recoger.
  Con un solo estado no se distingue si el plato se enfrio en la estacion o en la barra.
- **EN_PREPARACION** evita que dos personas de la misma estacion tomen la misma comanda, y
  le muestra al mesero que su pedido ya fue visto.

## Consecuencias

**Positivas**
- Metricas de tiempo sin trabajo adicional (alimentan [[SPEC-008 - Contabilidad y Auditoria]])
- Menos colisiones dentro de una estacion
- El mesero tiene visibilidad del avance

**Negativas / a vigilar**
- Un paso mas que el personal debe marcar. Si no lo marcan, los datos de tiempo se ensucian
- El boton de la estacion debe llamarse **"Listo"**, no "Entregado", para no confundir

> [!success] Verificado en codigo real (2026-08-25)
> `Comanda.en_preparacion_desde` y `Comanda.lista_desde` se poblaron correctamente en un
> pedido de prueba real (dos comandas, cocina y bar, cada una con su propio timestamp de
> "lista"). La metrica "cuanto se demora cada estacion" ya se puede calcular hoy, sin
> trabajo adicional — tal como predecia la justificacion original.
>
> La proteccion de EN_PREPARACION contra colisiones es practica, no un lock de base de
> datos: una comanda en preparacion desaparece de la columna "Nuevas" del tablero, asi que
> nadie mas la ve para abrirla. Dos clics exactamente simultaneos sobre la misma card antes
> de que la UI se actualice siguen siendo una condicion de carrera teorica, sin resolver
> (ver [[SPEC-005 - Estaciones y Ruteo]]).

## Enlaces

- [[Flujo Principal]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[SPEC-006 - Notificaciones]]
