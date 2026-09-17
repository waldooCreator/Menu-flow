---
tipo: spec
id: SPEC-015
estado: implementada
actualizado: 2026-09-14
tags: [ventas, reportes, caja]
---

# SPEC-015 — Historial de Ventas

> [!success] Estado: Implementada — el 2026-09-03

## Proposito

Ver que se vendio: cuanto, cuando, por que medio de pago y en que mesa — con
filtros y totales, para poder cuadrar contra el banco y responder "¿como nos
fue ayer?".

## Que es una "factura" aqui

En el sistema que se va a reemplazar, "factura" significa **cada venta
cobrada**, no un documento tributario. Esta spec usa esa misma idea, con el
nombre que ya tenemos: **una cuenta cerrada es una venta**.

> [!important] Sin DIAN (decision del autor, 2026-09-03)
> **Nada de facturacion electronica.** Ni numeracion autorizada, ni CUFE, ni
> envio a la DIAN. Esto es el historial interno de ventas del restaurante.
> Si algun dia hace falta lo otro, es una spec aparte y un proveedor externo.

## Alcance

- **Lista de ventas**: cada cuenta cerrada, con mesa o domicilio, hora, medio
  de pago y total
- **Detalle de una venta**: los platos con su precio congelado, subtotal,
  propina, impuesto, total y quien cobro
- **Filtros**: rango de fechas (con atajos), medio de pago, tipo (mesa /
  domicilio), y mostrar u ocultar anuladas
- **Totales del filtro puesto**: vendido, propinas y cantidad de ventas
- **Desglose por medio de pago** del rango filtrado
- **Anuladas visibles**, marcadas y sin sumar

## Fuera de alcance

- **Facturacion electronica DIAN** — ver arriba
- **Reportes analiticos** (mas vendidos, ventas por mesero, hora de mayor
  demanda). Son otra spec: esto es el historial crudo, no el analisis
- **Clientes**: el filtro por cliente del sistema viejo no aplica todavia,
  porque no existe el modulo de clientes
- Editar una venta cobrada. Nunca (SPEC-008): se anula, con motivo

## Comportamiento

### Al abrir: hoy, sin filtrar

Lo primero que se ve es el dia en curso — es la pregunta del 95% de las veces.

**Cuatro** numeros arriba, no tres — la spec decia tres, y al implementar se
vio que faltaba uno:

| Numero | Que es |
|---|---|
| **Vendido** | La comida sola. Sin propina |
| **Propinas** | De los meseros |
| **Entro a caja** | Vendido + impuesto + propina: la plata que se movio |
| **Ventas** | Cuantas, y cuantas anuladas |

> [!important] Por que hacen falta dos numeros y no uno
> El total congelado de una cuenta **ya incluye la propina** (`total =
> subtotal + propina + impuesto`). Si la pantalla mostrara un solo numero
> llamado "vendido" usando ese total, estaria contando la propina como venta
> — y el dueño creeria que vendio mas de lo que vendio.
>
> Pero tampoco basta con mostrar solo la comida: lo que hay que comparar
> contra el banco es lo que **entro a caja**, con propina incluida, porque eso
> es lo que fisicamente se movio al cobrar. Por eso van los dos, y por eso el
> desglose por medio de pago suma **lo cobrado**, no lo vendido.

Debajo, el **desglose por medio de pago** del rango: es la linea que se compara
contra lo que dice el banco al cerrar el dia.

### La lista

Cada venta una fila, con tres cosas visibles de un vistazo:

| Donde | Que |
|---|---|
| Izquierda | "Mesa 7" o "Domicilio · Cristian", y debajo la hora |
| Centro | El medio de pago |
| Derecha | El total |

Al tocar una fila se abre el detalle: los platos **con el precio al que se
vendieron** (no el de hoy — SPEC-008, regla 1), subtotal, propina, impuesto,
total, y quien cobro.

### Las anuladas se ven

Tachadas, en gris, y **no suman** en los totales. No se esconden a proposito:
si alguien anula seis ventas en una noche, eso tiene que saltar a la vista.
Cada una muestra su motivo y quien la anulo.

### Los filtros

Atajos de un toque, que es como se usa de verdad:

**Hoy · Ayer · Esta semana · Este mes · [rango a mano]**

Mas medio de pago, tipo (mesa / domicilio) y el interruptor de anuladas.

#### Filtros de detalle (ampliado 2026-09-03)

Detras de un boton **"Mas filtros"**, plegados: la mayoria de las veces solo se
usa la fecha, y mostrarlos todos de entrada convertiria la pantalla en un
formulario antes de dejar ver una sola venta. El boton lleva un contador de
cuantos hay puestos, para que no se olvide uno activo.

| Filtro | Para que |
|---|---|
| **Mesa** | "¿Cuanto vendio la mesa 5 este mes?" |
| **Quien cobro** | Responsabilidad: cuanto paso por cada persona |
| **Desde $ / Hasta $** | Encontrar la venta grande, o contar las pequeñas |
| **Franja horaria** | "¿Cuanto vendemos entre 7 y 9 de la noche?" — decide personal |
| **Ordenar** | Por fecha o por valor, en los dos sentidos |

Los desplegables de mesa y de quien cobro ofrecen **solo lo que de verdad tiene
ventas**. Un filtro que no devuelve nada es peor que no ofrecerlo.

> [!important] La franja horaria cruza la medianoche
> "De 22:00 a 02:59" es el horario real de un restaurante. Tratado como un
> rango normal no devolveria nada nunca, porque 22 no es menor que 2. Cuando la
> hora de inicio es mayor que la de fin, se entiende como noche partida.

Las horas se comparan en **hora local** (America/Bogota), no en UTC: "las 8 de
la noche" significa lo que significa aqui.

**Los totales corresponden SIEMPRE al filtro puesto y al rango completo**, no a
las filas que caben en pantalla — misma regla que el libro de caja: si el total
dependiera de cuanto se alcanza a mostrar, no serviria para cuadrar.

### En el telefono

La lista pasa a tarjetas apiladas en vez de filas, y los tres numeros de arriba
se acomodan en dos lineas. El cajero entra desde el celular mas que desde un
computador.

## Reglas

1. **Una venta es una cuenta cerrada.** No hay una entidad "factura" aparte.
2. **La propina nunca se suma al total de ventas**, se reporta al lado.
3. **Las anuladas se muestran y no suman.** Nada se esconde.
4. **Los totales son del rango filtrado completo**, no de la pagina.
5. **Los precios son los congelados** al momento de la venta, no los de hoy.
6. **Nada se edita.** Una venta equivocada se anula con motivo (SPEC-013).

## Criterios de aceptacion

- [x] Al abrir sin filtros se ve **lo de hoy**
- [x] Los tres numeros (vendido, propinas, cantidad) corresponden al filtro puesto
- [x] La **propina no esta sumada** dentro del total de ventas
- [x] El desglose por medio de pago suma exactamente **lo cobrado** (no lo vendido)
- [x] Filtra por rango de fechas, y los atajos Hoy / Ayer / Esta semana / Este mes funcionan
- [x] Filtra por medio de pago y por tipo (mesa / domicilio)
- [x] Filtra por **mesa**, por **quien cobro**, por **rango de monto** y por **franja horaria**
- [x] La franja horaria **cruza la medianoche** correctamente
- [x] Las horas se interpretan en **hora local**, no en UTC
- [x] Ordena por fecha y por monto, en los dos sentidos
- [x] Los desplegables **solo ofrecen mesas y personas con ventas**
- [x] Un monto mal escrito **avisa**, no revienta
- [x] Los filtros **se combinan** entre si
- [x] Las **anuladas se ven marcadas** y **no suman** en ningun total
- [x] Ocultar anuladas las quita de la lista sin cambiar los totales (ya no sumaban)
- [x] El detalle muestra los platos con el **precio congelado** de esa venta
- [x] El detalle muestra **quien cobro**
- [x] Los totales son del **rango completo**, aunque la lista muestre menos filas
- [x] Quien no puede cobrar **no ve** esta pantalla
- [x] Sin desborde horizontal en 375 px

## Plan de implementacion

Por orden, cada paso comprobable antes de seguir al siguiente.

### 1. Backend: el endpoint del historial (medio dia)

`GET /api/ventas/` sobre las cuentas cerradas y anuladas.

- Filtros: `desde`, `hasta`, `medio_pago`, `tipo` (mesa/domicilio), `anuladas`
- Respuesta: `{ totales: {vendido, propinas, cantidad}, por_medio_pago: [...],
  ventas: [...] }`
- Los totales **excluyen las anuladas** y se calculan sobre el rango completo,
  antes del tope de filas — igual que en el libro de caja
- Permiso: `PuedeCobrar`, el mismo de caja

Reutiliza `Cuenta` tal como esta. **No hace falta modelo nuevo ni migracion**:
todos los campos ya existen (mesa, es_domicilio, estado, cerrada_en,
cerrada_por, medio_pago, subtotal/propina/impuesto/total congelados,
motivo_anulacion, anulada_por).

### 2. Backend: el detalle de una venta — **YA ESTA** (0 horas)

Comprobado contra el codigo: `GET /api/cuentas/<id>/` ya devuelve la cuenta con
sus pedidos y cada renglon con `nombre_congelado` y `precio_congelado`, mas
`cerrada_por`, `medio_pago` y `motivo_anulacion`.

**No hay que escribir nada.** Solo falta que la pantalla lo consuma. Lo unico a
revisar es el permiso: hoy es `EsMesero`; si el historial va a ser de quien
pueda cobrar, conviene que el detalle use el mismo criterio.

### 3. Tests del backend (2 horas)

Antes de la pantalla, porque son los que sostienen las reglas:

- Los totales corresponden al filtro
- Las anuladas no suman
- La propina no esta dentro del total de ventas
- El desglose por medio de pago suma el total
- Los totales son del rango completo, no de la pagina
- Quien no puede cobrar recibe 403

### 4. Pantalla (medio dia)

`/mesero/ventas`, con el enlace en la navegacion.

- Los tres numeros arriba y el desglose por medio de pago
- Atajos de fecha y filtros
- Lista, con las anuladas tachadas
- Detalle al tocar una fila

### 5. Comprobacion end-to-end (1 hora)

Con clics reales en el navegador y capturas: cada filtro, el detalle, una
anulada, y el caso de rango vacio.

### 6. Documentacion (media hora)

Bitacora del dia y el indice.

**Total estimado: dia y medio.** Sin migraciones, sin modelo nuevo, y con el
detalle ya resuelto — el dato esta completo desde SPEC-013 y lo unico
verdaderamente nuevo es la consulta con filtros y la pantalla.

## Dependencias

- [[SPEC-013 - La Cuenta]] — la venta ES una cuenta cerrada
- [[SPEC-014 - Turno de Caja y Cajas de Fondos]] — los medios de pago y el
  patron de "totales del rango completo" salen de ahi
- [[SPEC-008 - Contabilidad y Auditoria]] — precios congelados, nada se borra

## Decisiones tomadas al implementar

- **Una cuenta anulada estando ABIERTA no aparece.** Nadie pago nada: no fue
  una venta. El historial lista solo las que en algun momento se cobraron —
  las que tienen totales congelados. Un pedido anulado antes de cobrar es otra
  cosa y vive en la vista de pedidos.
- **Se filtra por fecha de COBRO, no de apertura.** Una mesa que se sento a las
  11 de la noche y pago a las 12 es venta del dia en que pago, que es cuando el
  dinero entro a la caja.
- **No se incluyo el boton de anular**, segun lo propuesto abajo.

## Preguntas resueltas

1. **¿Quien ve esta pantalla?** En el sistema viejo el cajero la ve completa.
   **Propuesta:** igual, el cajero la ve completa — necesita revisar lo que
   cobro. La alternativa seria que el cajero vea solo lo de su turno y el dueño
   todo. **Resuelto:** se implemento asi — el cajero la ve completa.

2. **¿Se puede anular una venta desde aqui?** Anular ya existe (SPEC-013, con
   motivo y devolviendo la plata a la caja). **Propuesta:** si, porque es donde
   uno encuentra la venta equivocada — pero eso permite anular una de hace tres
   semanas. La alternativa es limitarlo a las de hoy. **Resuelto:** NO se incluyo el boton.
   Agregarlo despues es facil; deshacer una anulacion sobre una venta de hace
   tres semanas, no. Se agrega si se pide.

3. **¿Hace falta descargar la lista?** El sistema viejo tiene un "Reporte
   descargable" aparte. **Resuelto:** no en esta ronda; se agrega si el
   contador lo pide.
