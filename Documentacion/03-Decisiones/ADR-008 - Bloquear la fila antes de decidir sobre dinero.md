---
id: ADR-008
estado: aceptada
fecha: 2026-09-03
specs: [SPEC-013, SPEC-014, SPEC-002]
---

# ADR-008 — Bloquear la fila antes de decidir sobre dinero

## Contexto

Al preguntarnos qué pasaría con varios meseros trabajando a la vez, medimos el
sistema con hilos reales disparando desde una barrera, para caer en el mismo
milisegundo. Aparecieron tres fallos, todos de la misma forma:

```python
if cuenta.estado == Cuenta.CERRADA:      # 1. mirar
    raise OperacionInvalida(...)
...
registrar_movimiento(...)                # 2. actuar
```

Entre *mirar* y *actuar* pasa tiempo. Dos peticiones que entran a la vez miran
las dos antes de que ninguna actúe, las dos ven "abierta", y las dos actúan.

Lo medido:

| Caso | Resultado antes |
|---|---|
| 3 meseros, misma mesa, primer pedido | 1 pedido creado, 2 caídos con 500 |
| 10 meseros, misma mesa | 1 pedido creado, **9 perdidos** |
| 2 cajeros cobran la misma cuenta | **2 ingresos**: 61.600 entraban como 123.200 |
| 2 anulaciones de una cuenta cobrada | 2 egresos: la plata salía dos veces |

El de la mesa no corrompía datos — la restricción `una_cuenta_abierta_por_mesa`
hacía su trabajo — pero perdía pedidos y mostraba un error crudo.

El del cobro sí corrompe: **los dos cajeros ven 200 OK**. Nadie se entera hasta
el cuadre del turno, y para entonces no hay forma de saber cuál fila sobra. Con
movimientos solo-inserción ([[ADR-007 - Una novedad es un evento, no una modificacion]])
la fila falsa ya no se puede quitar.

No hace falta mala fe ni un restaurante lleno: basta que el cajero toque
"Cobrar" dos veces porque la pantalla tardó.

## Decisión

**Toda operación que decide según un estado y después mueve plata o crea una
cuenta, relee su fila bloqueada dentro de la transacción y comprueba el estado
ahí adentro.**

```python
with transaction.atomic():
    cuenta = Cuenta.objects.select_for_update().get(pk=cuenta.pk)
    if cuenta.estado != Cuenta.ABIERTA:
        raise OperacionInvalida("Esta cuenta ya fue cobrada.")
```

El segundo en llegar espera a que el primero termine, relee el estado real y
recibe un error claro en vez de cobrar otra vez.

Para el pedido se bloquea **la mesa**, no la cuenta: la cuenta todavía no
existe cuando empieza la carrera, y no se puede bloquear lo que no hay.

## Por qué así y no de otra forma

**¿Por qué no `get_or_create`?** Resuelve el caso de la cuenta pero no el del
cobro, que es el grave. Una sola regla para los dos es más fácil de recordar
que dos parches distintos.

**¿Por qué no atrapar el `IntegrityError` y reintentar?** Solo funciona donde
hay una restricción que choque. El cobro duplicado **no viola ninguna**: dos
movimientos de ingreso son perfectamente válidos para la base. Es el sistema
el que sabe que sobran, y por eso tiene que impedirlos antes.

**¿No frena esto el sistema?** El bloqueo es por fila, no global: dos meseros
en mesas distintas siguen entrando en paralelo. Solo se serializa lo que de
verdad compite por el mismo recurso, que es exactamente lo que debía pasar.

**Cuidado con `select_for_update` sobre consultas vacías.** El código tenía:

```python
if Pedido.objects.select_for_update().filter(codigo_qr=codigo_qr).exists():
```

con un comentario diciendo que eso evitaba el QR duplicado. **No bloquea
nada**: si ninguna fila coincide todavía, no hay qué bloquear. Lo que salvaba
era el `unique` de `codigo_qr`, y por eso salía un 500 en vez del 409 previsto.

## Consecuencias

- `cerrar_cuenta`, `anular_cuenta` y `cerrar_turno` releen bloqueado
- `ConfirmarPedidoView` bloquea la mesa antes de resolver la cuenta
- El QR repetido responde 409 con su explicación, también en domicilios
- Los cuatro casos son **tests permanentes** en `backend/ventas/tests.py`,
  con `TransactionTestCase` para que los hilos vean confirmaciones reales
- Cualquier operación nueva sobre dinero sigue esta regla

## Lo que esto enseña sobre cómo probamos

Una prueba de carga con 35 usuarios **no habría encontrado el cobro
duplicado**. Necesita que dos peticiones toquen la misma cuenta en la misma
fracción de segundo, y con usuarios repartidos al azar eso casi nunca cae.
Habría salido toda verde mientras la caja se cobraba dos veces.

Son dos pruebas distintas y las dos hacen falta:

- **Carga** (Locust, k6): mide velocidad — cuántas peticiones aguanta
- **Concurrencia** (la de `ventas/tests.py`): mide corrección — qué queda en la
  base cuando dos cosas caen juntas

La segunda encontró tres fallos al primer intento porque **fuerza** la
coincidencia en vez de esperar a que ocurra.
