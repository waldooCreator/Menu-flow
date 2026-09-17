---
tipo: producto
actualizado: 2026-08-21
tags: [glosario, vocabulario]
---

# Glosario

Vocabulario del dominio. Usar estos terminos de forma consistente en specs, codigo e interfaz.

| Termino | Significado |
|---|---|
| **Pedido** | Lo que un cliente ordena en una mesa. Unidad de venta |
| **Comanda** | La parte de un pedido que le corresponde a una estacion |
| **Estacion** | Punto de preparacion: cocina, postres, bar, parrilla |
| **QR de mesa** | QR estatico pegado en la mesa; identifica donde esta el cliente |
| **QR de pedido** | QR dinamico que genera el cliente y contiene su pedido completo |
| **PQRSF** | Peticiones, Quejas, Reclamos, Sugerencias y Felicitaciones |
| **Parametrizable** | Se cambia por configuracion, nunca modificando codigo |
| **Ruteo** | El proceso de dividir un pedido en comandas segun la estacion de cada item |
| **Anulacion** | Cancelacion de un pedido con motivo y responsable. Nunca es un borrado |
| **Rebanada vertical** | Un flujo completo de punta a punta, delgado pero funcional |

## Terminos que NO usamos

- ~~"Orden"~~ --> usamos **Pedido**
- ~~"Cocina"~~ como sinonimo de todas las estaciones --> cocina es *una* estacion
- ~~"Ticket"~~ --> usamos **Comanda**
- ~~"Borrar pedido"~~ --> usamos **Anular**
