---
tipo: spec
id: SPEC-016
estado: implementada
actualizado: 2026-09-07
tags: [ventas, tiquetes, impresion]
---

# SPEC-016 — Tiquete de Venta

> [!success] Estado: Implementada — decisiones cerradas el 2026-09-03

## Proposito

Que el restaurante pueda entregar al cliente un comprobante de su compra, y
descargar lo vendido para revisarlo o entregarlo al contador.

## Que es y que NO es

Es un **tiquete de venta**: el comprobante que se entrega al cliente, con lo
que pidio, cuanto costo y como pago.

> [!important] Sin DIAN (decision del autor, 2026-09-03)
> **No es un documento tributario.** Ni numeracion autorizada por la DIAN, ni
> CUFE, ni envio a la entidad. Es un comprobante interno del negocio. Si algun
> dia hace falta facturacion electronica, es otra spec y un proveedor externo.

## El cambio de regla que esto implica

> [!warning] Revierte una decision anterior del proyecto
> `CLAUDE.md` decia: **"Sin impresion. Todo va por mensajes dentro de la
> aplicacion."** El autor revirtio esa regla el 2026-09-03 **para los
> tiquetes de venta**.
>
> **Sigue vigente para las comandas de cocina** (SPEC-005): esas no se
> imprimen, siguen yendo por mensajes en la app. Lo que cambia es solo el
> comprobante al cliente.
>
> Al implementar hay que actualizar `CLAUDE.md` y SPEC-013 dejando escrito
> que cambio y por que.

## Alcance

- **Tiquete individual** de una venta, imprimible y descargable
- **Tiquetes de varias ventas seleccionadas** a mano en la lista
- **Consolidado de un periodo** (semana, mes o rango), agrupado y con subtotales
- **Numeracion propia por medio de pago**, con reinicio anual
- **Dos formatos de impresion** (rollo termico y carta), elegibles desde el panel
- **NIT y logo** del negocio, administrables desde el panel
- **Exportacion a Excel** respetando los filtros puestos

## Fuera de alcance

- Facturacion electronica DIAN
- Impresion de comandas de cocina (sigue descartada, SPEC-005)
- Envio automatico del tiquete por correo o WhatsApp

## Comportamiento

### La numeracion

Cada medio de pago lleva **su propio consecutivo, con su propia sigla, que se
reinicia cada año**:

```
Ef-2026-00001   Ef-2026-00002   ...   Ef-2027-00001
Ne-2026-00001   Ba-2026-00001   ...
```

La sigla se configura **por medio de pago desde el panel** — si mañana se crea
"Rappi", el administrador le pone "Ra" sin pedirle nada a nadie.

**Por que reinicia cada año.** Con 150 ventas diarias el negocio hace unas
54.000 al año. Un contador corrido llegaria a seis digitos en pocos años y
nadie dicta eso por telefono sin equivocarse. Reiniciando, el numero se queda
en cinco digitos para siempre y ademas **dice de que año es con solo verlo**.

> [!danger] El contador necesita bloqueo
> Dos cajeros cobrando en el mismo instante con el mismo medio de pago se
> llevarian el mismo numero. Es exactamente el fallo de
> [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]], que ya costo
> un cobro duplicado. El consecutivo se toma con la fila bloqueada, dentro de
> la misma transaccion que cierra la cuenta.

**Un tiquete anulado conserva su numero.** El tiquete existio y el cliente lo
tuvo en la mano; saltarselo seria esconder que existio. Se muestra marcado como
anulado y el numero queda consumido.

### Los dos formatos

El formato se elige **desde el panel**, porque no todos los restaurantes tienen
lo mismo:

| Formato | Cuando | Como se ve |
|---|---|---|
| **Rollo termico (80 mm)** | Para entregar al cliente | Una columna angosta, monoespaciada, sin color |
| **Carta** | Para archivar o entregar al contador | Hoja completa, con mas aire |

El consolidado de un periodo usa **siempre carta**: una tirilla de tres metros
no le sirve a nadie.

### Contenido del tiquete

Logo, nombre, NIT, direccion y telefono del negocio. Numero de tiquete, fecha y
hora, mesa o domicilio, y quien atendio. Los platos con cantidad, observaciones
y precio **congelado** al momento de la venta (SPEC-008). Subtotal, impuesto si
lo hay, propina, total y medio de pago. Un mensaje de pie configurable.

### El consolidado

Agrupado por **dia** y, dentro de cada dia, por un segundo nivel a elegir
(mesa, medio de pago o mesero), con subtotal por grupo y total del periodo.
Respeta los filtros que esten puestos en la pantalla de ventas.

### La animacion de impresion

> [!important] Pedido explicito del autor (2026-09-03)
> Al pulsar imprimir, el tiquete debe aparecer **como si una impresora de rollo
> lo fuera sacando poco a poco**: rapida, estetica, muy amigable y responsive.

Se revela de arriba hacia abajo, con el borde inferior dentado como el papel
cortado. Dura menos de un segundo — es un gesto, no una espera. Se respeta la
preferencia del sistema de **reducir movimiento**: quien la tenga activada ve
el tiquete completo de inmediato, sin animacion.

## Reglas

1. **Un tiquete es una venta cobrada.** No hay entidad "factura" aparte.
2. **El numero se asigna al cobrar**, dentro de la transaccion y con bloqueo.
3. **El numero nunca se reutiliza**, ni siquiera si la venta se anula.
4. **Los precios del tiquete son los congelados** de esa venta.
5. **El tiquete no se edita.** Una venta equivocada se anula con motivo.
6. Las comandas de cocina **siguen sin imprimirse** (SPEC-005).

## Criterios de aceptacion

- [x] Al cobrar, la venta recibe un numero con la forma `Xx-AAAA-NNNNN`
- [x] Cada medio de pago lleva **su propio consecutivo**, independiente de los demas
- [x] El consecutivo **reinicia** al cambiar de año
- [x] Dos cobros simultaneos del mismo medio **no reciben el mismo numero**
- [x] La sigla de cada medio de pago se configura **desde el panel**
- [x] Una venta anulada **conserva** su numero
- [x] El NIT y el logo se cargan **desde el panel** y salen en el tiquete
- [x] El formato (rollo o carta) se elige **desde el panel** y cambia el diseño
- [x] El tiquete individual se puede imprimir y descargar
- [x] Se pueden **seleccionar varias ventas** en la lista y descargar sus tiquetes
- [x] El consolidado de un periodo agrupa por dia con subtotales
- [x] El Excel respeta **los filtros puestos**
- [x] La animacion de impresion corre en menos de un segundo
- [x] Con "reducir movimiento" activado, **no hay animacion**
- [x] Sin desborde horizontal en 375 px

## Plan de implementacion

### Paso 0 — Dejar la base en blanco

> [!danger] Irreversible — se confirma con el autor antes de ejecutar
> Se borran **solo los datos de operacion**. La configuracion, el menu, las
> mesas, los usuarios y los medios de pago **no se tocan**.

| Se borra | Hoy hay | | Se conserva | Hoy hay |
|---|---|---|---|---|
| Pedidos | 7 | | Mesas | 7 |
| Renglones de pedido | 10 | | Estaciones | 3 |
| Comandas | 7 | | Categorias | 5 |
| Notificaciones | 7 | | Platos | 19 |
| Novedades | 6 | | Observaciones | 2 |
| Cuentas | 13 | | Medios de pago | 5 |
| Movimientos de caja | 4 | | Usuarios | 5 |
| Turnos | 2 | | Parametros del sitio | todos |

Con esto se resuelve tambien la pregunta de las ventas viejas sin numero: no
quedan ventas viejas.

### Paso 1 — Numeracion (medio dia)

- Campo `prefijo` en el medio de pago, editable desde el panel
- Campos `tiquete_numero` y `tiquete_anio` en la cuenta
- El numero se asigna dentro de `cerrar_cuenta`, **con la fila del medio de
  pago bloqueada**, en la misma transaccion
- Migracion

**Tests primero:** dos cobros simultaneos del mismo medio no colisionan; el
contador reinicia al cambiar de año; cada medio cuenta aparte; una venta
anulada conserva su numero.

### Paso 2 — Datos del negocio (1 hora)

Parametros nuevos: `nit`, `logo`, `formato-tiquete` (rollo | carta) y
`mensaje-pie-tiquete`. Todos administrables desde Admin → Sitio, sin migracion
de modelo porque la configuracion ya es clave/valor.

### Paso 3 — El tiquete en pantalla (medio dia)

Componente unico que se pinta en los dos formatos segun el parametro. Incluye
la animacion de rollo y una hoja de estilos de impresion (`@media print`) para
que salga limpio tanto en termica como en carta.

### Paso 4 — Seleccion multiple y descargas (medio dia)

- Casillas de seleccion en la lista de ventas, con "seleccionar todo lo filtrado"
- Descargar el tiquete de una venta
- Descargar los tiquetes de las seleccionadas
- Descargar el consolidado del periodo filtrado

### Paso 5 — Excel (2 horas)

Exportacion de lo filtrado, con una fila por venta y las columnas del listado.

### Paso 6 — Comprobacion y documentacion (media dia)

Prueba end-to-end con clics reales, actualizacion de `CLAUDE.md` y SPEC-013 por
el cambio de regla, y bitacora.

**Total estimado: dos dias y medio.**

## Dependencias

- [[SPEC-015 - Historial de Ventas]] — los filtros y la lista salen de ahi
- [[SPEC-013 - La Cuenta]] — un tiquete es una cuenta cerrada
- [[SPEC-007 - Administracion y Parametrizacion]] — NIT, logo y formato
- [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]] — el bloqueo del consecutivo

## Preguntas resueltas

1. **Nombre del documento** — TIQUETE DE VENTA.
2. **Numeracion** — por medio de pago, con año, reinicio anual (`Ef-2026-00001`).
3. **Siglas** — configurables desde el panel.
4. **NIT y logo** — parametros nuevos, administrables desde el panel.
5. **Formato de impresion** — los dos, elegible desde el panel.
6. **Ventas viejas sin numero** — no aplica: la base queda en blanco.
7. **Tiquete anulado** — conserva su numero.
8. **Descargas** — individual, seleccionadas y por periodo.
