---
tipo: bitacora
fecha: 2026-08-27
tags: [bitacora, cuenta, cobro, ventas, spec-013]
---

# 2026-08-27 — La cuenta y el cobro

Implementación de [[SPEC-013 - La Cuenta]]. Es el cimiento del control de ventas: hasta
hoy el sistema sabía qué se pidió, no qué se cobró.

## Lo esencial

Nueva app **`ventas`**, aparte de `pedidos` y `estaciones` a propósito: el dinero es un
dominio distinto del de cocina, y ahí van a caer después el turno de caja y los reportes.

La distinción que resuelve todo:

| | Responde | Avanza por |
|---|---|---|
| `Pedido` | "Manden esto a preparar" | pendiente → listo → entregado |
| `Cuenta` | "Esta mesa debe $X" | abierta → cerrada |

**Son ortogonales.** Un pedido entregado con cuenta abierta es lo normal: se comieron la
comida y todavía no pagan.

## Decisiones que quedaron en código

**La cuenta no se abre a mano.** `cuenta_para()` la busca o la crea al confirmar el primer
pedido de la mesa; los siguientes se suman. Un marcado más que recordar sería trabajo
administrativo puro — lo primero que se deja de hacer un viernes lleno.

**Una sola cuenta abierta por mesa, garantizada por la base.** `UniqueConstraint` con
condición `estado="abierta"`. Dos meseros confirmando a la vez en la misma mesa no pueden
abrir dos cuentas: lo impide Postgres, no un `if`.

**Cerrar exige medio de pago.** Sin él el cierre de caja no puede cuadrar nada, así que un
cierre sin medio no significaría nada.

**Cerrar congela subtotal, propina, impuesto y total**, aunque los precios de cada renglón
ya estuvieran congelados. Motivo: una cuenta cerrada es un hecho consumado — si mañana se
corrige un renglón histórico, lo que se cobró esa noche no puede cambiar. Y un reporte de
un mes no tiene que resumar miles de renglones.

**Un porcentaje mal escrito vale 0.** `_porcentaje()` atrapa el error de conversión y
devuelve 0: cobrar de más por un dedazo en un parámetro es peor que no cobrarlo, y el 0 se
nota enseguida.

**Cerrar NO libera la mesa sola.** Se ofrece a un toque, con "Sigue ocupada" al lado.
Decidirlo por su cuenta sería el sistema adivinando que la gente ya se fue, contra la regla
de oro de [[SPEC-012 - Vista de Salon y Estado de Mesas]].

**La propina se puede quitar.** Es voluntaria; mostrarla como obligatoria sería mentirle al
cliente. En la pantalla es una casilla al lado del monto.

## Anular, por fin

`Pedido.ANULADO` y `motivo_anulacion` existían en el modelo **desde el primer día sin
ningún endpoint que los usara**. Ahora anular una cuenta exige motivo, queda con
responsable, y arrastra sus pedidos. Cumple la regla de
[[SPEC-008 - Contabilidad y Auditoria]] que llevaba meses escrita y sin construir.

## Fiar queda fuera

El sistema actual tiene "créditos pendientes" como medio de pago. El autor lo descartó:
**toda cuenta cerrada está cobrada de verdad**, para que el reporte de ventas y el cuadre
de caja no puedan discrepar. Anotado en el alcance de la spec.

## Verificado

Prueba automatizada contra la API real (script en el scratchpad), **todo en verde**:

- Confirmar abre la cuenta; **el segundo pedido se suma, no abre otra**
- Subtotal = suma de los dos pedidos ($42.000); propina 10% = $4.200; impuesto 0 no aparece
- **El salón trae el total** de la cuenta abierta de cada mesa
- Cerrar sin medio de pago se rechaza; con medio queda con quién cobró y **congelado**
- **No se puede cobrar dos veces**
- Una cuenta cerrada no recibe más: el siguiente pedido **abre otra**
- **Subir el precio de un plato NO altera la cuenta cerrada** — el pasado no se reescribe
- Cerrar sin propina la deja en 0 y el total no la incluye
- Anular sin motivo se rechaza; con motivo anula la cuenta **y sus pedidos**
- El domicilio abre su propia cuenta y **no aparece en el salón**
- **Liberar la mesa no toca la cuenta**: sigue abierta y se llega a ella desde la lista
- Permisos: sin sesión 401, cocina 403, el mesero no crea medios de pago

En navegador: el salón muestra `Mesa 12 · OCUPADA · $50.600`; la pantalla de cuentas
agrupa los dos pedidos con su detalle; los cinco medios de pago aparecen; el interruptor de
propina mueve el total de $30.800 a $28.000 y de vuelta; al cobrar ofrece
**"Liberar Mesa 12" / "Sigue ocupada"**; tras liberar, la mesa queda libre con total 0.
Sin desborde horizontal en 375 px y ningún control bajo 40 px.

### Una falsa alarma

Reporté que el total con y sin propina venía vacío. **La interfaz estaba bien**: mi
expresión regular buscaba `TOTAL` seguido del monto sobre texto plano, y el monto vive en
un `<b>` aparte. Leyendo el elemento en vez del texto, los valores salieron correctos.

## Pendiente

- **Turno de caja** — agrupa cuentas cerradas; es lo siguiente y ya depende solo de esto
- **Reportes de venta** — ventas por día, por mesero con propina, platos más vendidos
- Medios de pago se administran hoy por API; falta su pantalla en el panel
- Dividir la cuenta entre comensales sigue fuera de alcance

## Enlaces

- [[SPEC-013 - La Cuenta]]
- [[SPEC-008 - Contabilidad y Auditoria]]
- [[SPEC-012 - Vista de Salon y Estado de Mesas]]
- [[Que le Falta para ser un POS Vendible]]
- [[Inventario del Sistema Actual de Springfield]]
- [[Inicio]]
