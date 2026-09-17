---
tipo: spec
id: SPEC-025
estado: implementada
actualizado: 2026-09-16
tags: [caja, cobro, efectivo, vueltos]
---

# SPEC-025 — Vueltos

> [!success] Estado: Implementada — decidida y construida el 2026-09-16
> El comportamiento vive en [[SPEC-013 - La Cuenta]] ("Vueltos (efectivo)"), como parte del
> cobro. Esta spec deja el porqué y lo que se decidió dejar fuera.

## Propósito

Que al cobrar en efectivo el sistema sepa **con cuánto pagó el cliente y cuánto se le
devolvió**, para que quien cobra tenga el vuelto calculado en vez de hacerlo de cabeza.

## El problema real

El cobro en efectivo registraba solo el **total** de la cuenta. Si el cliente pagaba
$61.600 con un billete de $100.000, el sistema no sabía que entraron $100.000 ni que
salieron $38.400 de vuelto — eso quedaba en la cabeza de quien cobró.

## Decisión del autor (2026-09-16)

> *"Solo para efectivo, de manera que en caja cuando se vaya a cobrar algo se ingrese la
> cantidad en billetes — por ejemplo 50.000 y eran 40.000, entonces debe dar 10.000 de
> vueltos, en mensaje."*

- **Solo efectivo.** Con cualquier otro medio no se pregunta.
- **Opcional.** Si no se indica con cuánto pagó, se asume el valor exacto — cobrar sigue
  funcionando exactamente igual que antes.
- **Un mensaje**, no un movimiento de caja aparte: "Vuelto: $10.000". Lo que entra a la
  caja sigue siendo el total; el vuelto es información para quien cobra, no una operación
  nueva del libro.
- Se guarda lo recibido y el vuelto en la cuenta, para el tiquete y para revisar después.

## Fuera de alcance (decidido, no por decidir)

- **Avisar si el turno se queda sin sencillo.** Necesitaría llevar el detalle de qué
  billetes tiene cada turno, no solo el total en efectivo. Se deja para una revisión
  futura si en la práctica hace falta.
- **Un movimiento de caja separado para el vuelto.** El neto que entra a la caja ya es
  correcto sin él (recibido − vuelto = total); agregarlo solo duplicaría el dato.
- **Pagos mixtos** (parte en efectivo, parte en Nequi). Una cuenta se sigue cobrando con
  un solo medio, como hoy.
- **Control del sencillo** (billetes y monedas) por turno.

## Cómo funciona

Ver "Vueltos (efectivo)" en [[SPEC-013 - La Cuenta]], sección Comportamiento — el
comportamiento completo, las reglas y los criterios de aceptación viven ahí, porque es
parte del cobro, no un módulo aparte.

## Dependencias

- [[SPEC-013 - La Cuenta]] — donde vive el comportamiento
- [[SPEC-014 - Turno de Caja y Cajas de Fondos]] — el cuadre del efectivo, sin cambios
- [[SPEC-016 - Tiquete de Venta]] — el tiquete muestra recibido y vuelto cuando aplica
