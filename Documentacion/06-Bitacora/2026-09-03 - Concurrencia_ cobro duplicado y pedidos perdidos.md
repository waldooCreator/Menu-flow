---
fecha: 2026-09-03
tipo: bitacora
specs: [SPEC-002, SPEC-013, SPEC-014]
adrs: [ADR-008]
---

# 2026-09-03 — Concurrencia: cobro duplicado y pedidos perdidos

Salió de una pregunta sobre el servidor: *si tres meseros crean un pedido en la
misma mesa al mismo tiempo, ¿qué pasa?*

En vez de razonarlo, se midió con hilos reales disparando desde una barrera.
Aparecieron tres fallos. Uno era grave.

## Lo que se encontró

| Caso | ¿Datos corruptos? | Qué veía el usuario |
|---|---|---|
| 3 meseros, misma mesa, primer pedido | No — siempre 1 cuenta | 500; **solo sobrevivía 1 de 3 pedidos** |
| Mismo QR escaneado 2 veces | No — 1 pedido | 500 en vez del 409 amable |
| **2 cajeros cobran la misma cuenta** | **Sí — cobro duplicado** | **200 OK a los dos** |

Con 10 meseros simultáneos: 1 pedido creado, **9 perdidos**.

En el cobro, 61.600 pesos cobrados una sola vez entraban a la caja como
123.200. Los dos cajeros veían "listo". El descuadre aparecía al cerrar turno,
sin forma de saber de dónde venía.

## La causa, una sola para los tres

Mirar y actuar en dos pasos, sin bloquear nada en medio. Dos peticiones
simultáneas miran las dos antes de que ninguna actúe.

El detalle que más engañaba estaba en un comentario del propio código, que
decía que `select_for_update` evitaba el QR duplicado. **No bloquea nada cuando
la consulta no encuentra filas** — no hay qué bloquear todavía. Lo que salvaba
era el `unique` de `codigo_qr`, y por eso salía 500 en vez de 409.

## Lo que se hizo

Está en [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]. En corto:
releer la fila **bloqueada dentro de la transacción** y comprobar el estado ahí
adentro.

- `ConfirmarPedidoView` bloquea **la mesa** antes de resolver la cuenta — la
  cuenta todavía no existe cuando empieza la carrera
- `cerrar_cuenta`, `anular_cuenta` y `cerrar_turno` releen bloqueado
- El QR repetido responde 409 con explicación, también en domicilios

`anular_cuenta` y `cerrar_turno` no se habían reportado: tenían el mismo
defecto y aparecieron al arreglar el cobro. Anular dos veces una cuenta ya
cobrada sacaba la plata **dos veces**.

## Comprobado

Siete tests permanentes en `backend/ventas/tests.py`, con `TransactionTestCase`
para que los hilos vean confirmaciones reales.

Y lo importante: **se comprobó que los tests detectan el fallo**. Revirtiendo
los arreglos, 4 de 7 fallan con exactamente los síntomas medidos:

```
AssertionError: 2 != 1 : cobro duplicado. Salidas: ['cobrada', 'cobrada']
AssertionError: 5 != 1
AssertionError: hubo fallos: [409, 409, 409, 409, 409, 201, 409, 409, 409, 409]
AssertionError: Lists differ: [201, 409, 409] != [201, 201, 201]
```

Con los arreglos puestos: los 7 en verde.

## Lo que deja como aprendizaje

Una prueba de carga con 35 usuarios **no habría encontrado esto**. Habría
salido toda verde mientras la caja se cobraba dos veces, porque necesita que
dos peticiones toquen la misma cuenta en la misma fracción de segundo y con
usuarios al azar eso casi nunca cae.

Medir velocidad y medir corrección son dos pruebas distintas. Las dos hacen
falta, pero la de concurrencia encontró tres fallos al primer intento.

## Pendiente

- Recorrer la sección **Cajeros** del sistema de Springfield
- Prueba de carga (Locust o k6) con 35+ usuarios entre mesas, domicilios,
  meseros y cocina — sigue teniendo sentido, para el otro tipo de riesgo
