---
fecha: 2026-09-03
tipo: bitacora
specs: [SPEC-014]
---

# 2026-09-03 — Pantalla de turno: fondo por caja y cierre ajeno

Primer punto de la lista que salió de revisar la sección Cajeros de Springfield
(ver [[Que debe poder hacer un Cajero]]).

## Corrección de lo que dije antes

En el resumen de la investigación anoté "Abrir o cerrar turno: ✅ API · ❌ sin
pantalla", y lo mismo para movimientos. **Era falso**: `MeseroCaja.vue` ya hacía
las tres cosas — abrir con fondo, registrar ingresos y gastos, y cerrar con
cuadre. No hubo que construirla, sino extenderla.

## Lo que se agregó

### Fondo inicial por caja

Antes se abría con un solo número que iba siempre a EFECTIVO. Ahora hay una
casilla por caja activa, y cada monto genera su propio movimiento de ingreso.

Un fondo en cero **no** genera movimiento: una fila de cero pesos solo ensucia
el libro.

Los montos se validan **todos antes de crear nada**. Si el tercero viene mal
escrito, no puede quedar un turno abierto con dos fondos ya puestos y el tercero
perdido.

### Cerrar el turno de otra persona

Solo el administrador, y exige motivo. Queda guardado en `cerrado_por`, que solo
se muestra cuando difiere del responsable — verlo repetido en cada turno normal
sería ruido.

> [!warning] El caso que lo obliga
> En el sistema real había turnos abiertos desde hacía casi un mes: uno del 7 de
> agosto seguía abierto el 3 de septiembre.
>
> Con la regla de un turno abierto por persona, esa persona **queda trabada** —
> no puede abrir el de hoy. Sin esto, la única salida sería entrar a la base de
> datos a mano.

### Aviso de turnos viejos

Un recuadro ámbar arriba de la pantalla lista los turnos abiertos de días
anteriores, con desde cuándo. Avisa, **no bloquea**. Para el administrador cada
uno trae su botón de cerrar; para los demás dice que solo el administrador
puede.

El propio turno nunca aparece en esa lista, y un turno de hoy de otra persona
tampoco: eso no es un olvido.

### Un permiso que estaba abierto

`CerrarTurnoView` recibía el turno por `pk` y solo comprobaba `PuedeCobrar`.
**Cualquier cajero podía cerrar el turno de otro** con solo saber el número.
Ahora la vista pasa quién está cerrando y la regla se comprueba en el servidor.

## Comprobado

Sobre el sistema corriendo, no en teoría:

- Abrir con fondo en Efectivo 200.000 y Nequi 75.000 → dos movimientos; el
  Datáfono en 0 **no** generó fila
- El total en pantalla mostró $275.000 antes de abrir
- Un cajero cerrando el turno de otro → *"Solo el administrador puede cerrar el
  turno de otra persona"*
- El administrador sin motivo → *"Escribe el motivo…"*; con motivo → cerrado, con
  `cerrado_por: admin` guardado
- El aviso apareció con un turno de 12 días y desapareció al cerrarlo
- La limpieza confirmó el `PROTECT`: un turno con movimientos no se puede borrar

14 tests en verde (7 de concurrencia + 7 nuevos de turno).

## Siguiente

2. Pantalla de movimientos con filtros — hoy están dentro de Caja, sin rango de fechas
3. Lista de facturas — ventas con filtros por fecha, tipo, medio y estado
4. Reporte de turnos — historial y cuadres, **solo admin** (`TurnosView` ya existe)
5. Clientes — con campo de observaciones desde el principio
