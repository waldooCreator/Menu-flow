---
tipo: spec
id: SPEC-013
estado: implementada
actualizado: 2026-09-16
tags: [cuenta, ventas, cobro, propina, caja]
---

# SPEC-013 — La Cuenta

> [!success] Estado: Implementada — revisada 2026-09-14
> Es el cimiento del control de ventas. Sale de
> [[Que le Falta para ser un POS Vendible]] y de
> [[Inventario del Sistema Actual de Springfield]].

## Proposito

Saber cuanto debe una mesa, registrar cuando y como se pago, y que "cuanto vendi hoy"
tenga una respuesta que cuadre con la caja.

## El problema

Hoy el sistema tiene **una sola entidad**: `Pedido`, con estados
*pendiente → en preparacion → listo → entregado*. Todos son **estados de cocina**.
Ninguno habla de dinero. "Entregado" significa *el mesero llevo la comida*, no *el cliente
pago*.

Consecuencias medibles hoy:

- Una mesa que pide tres rondas genera **tres pedidos sueltos**; nadie puede responder
  *¿cuanto va la Mesa 5?* sin sumar a mano
- **No existe donde registrar el cobro**: no hay campo, no hay endpoint
- "Cuanto se vendio" no se puede calcular

## La distincion que resuelve todo

| | Que es | Estados |
|---|---|---|
| **Pedido** | "Manden esto a preparar" — instruccion a la cocina | pendiente → en preparacion → listo → entregado |
| **Cuenta** | "Esta mesa debe $X" — registro de dinero | **abierta → cerrada** (o anulada) |

**Son ortogonales.** Una visita tiene **muchos pedidos y una sola cuenta**. El pedido
avanza por la cocina; la cuenta avanza por el dinero. Ninguno de los dos manda sobre el
otro.

> [!note] Se llama CUENTA, no factura
> "Factura" tiene peso legal — sugiere emision ante la DIAN, que este proyecto descarta
> explicitamente. **Cuenta** dice lo que es (lo que la mesa debe) sin prometer lo que el
> sistema no hace. El sistema que se va a reemplazar le dice "factura"; aqui no.

## Alcance

- Entidad **Cuenta**: se abre, acumula pedidos, se cierra con un cobro
- **Una cuenta abierta por mesa** a la vez; un domicilio abre la suya
- **Total en vivo** de la cuenta, visible en el salon
- **Propina** como porcentaje configurable, que se puede quitar
- **Impuesto** como porcentaje configurable (por defecto 0 = apagado)
- **Medios de pago** configurables desde el panel
- **Costo de envio** en los domicilios: se indica al confirmar el pedido y se suma al total
- **Cerrar** la cuenta: registrar pagado, con que medio, quien y cuando
- **Lista de cuentas abiertas** — lo que se sirvio y no se ha cobrado
- **Anular** una cuenta con motivo y responsable

## Fuera de alcance

- **Turno de caja** — agrupa cuentas cerradas; es la spec siguiente y depende de esta
- **Reportes de venta** — consumen cuentas cerradas; van despues
- **Dividir la cuenta** entre comensales, y dos cuentas en una misma mesa
- **Pasarela de pagos y facturacion electronica** — descartadas desde el inicio del proyecto
- **Cliente y puntos** de fidelizacion
- Impresion de la cuenta abierta (el tiquete de una cuenta cerrada pertenece a SPEC-016)
- **Fiar / creditos pendientes.** El sistema actual lo tiene como medio de pago; el autor
  lo descarto (2026-08-27). Toda cuenta cerrada esta cobrada de verdad — asi el reporte de
  ventas y el cuadre de caja no pueden discrepar

## Comportamiento

### Abrir

La cuenta **no se abre a mano**. Se abre sola cuando el mesero confirma el primer pedido:

1. Al confirmar un pedido sobre una mesa, se busca su **cuenta abierta**
2. Si existe, el pedido se suma a ella
3. Si no, se **crea** y el pedido es el primero

Un **domicilio** abre siempre su propia cuenta: no hay mesa donde acumular.

### Acumular

Todo pedido nuevo sobre esa mesa entra a la misma cuenta mientras siga abierta. El total
es la suma de los renglones de todos sus pedidos, con los **precios congelados** de cada
uno (Regla 1 de [[SPEC-008 - Contabilidad y Auditoria]]).

### Cerrar

Cerrar es el acto de cobrar. Exige **medio de pago**, y queda con **quien** cerro y
**cuando**.

Al cerrar se **congelan** el subtotal, la propina, el impuesto y el total final.

> [!important] Por que congelar si los precios ya estan congelados
> Porque una cuenta cerrada es un hecho consumado. Si mañana se corrige un renglon
> historico por cualquier razon, **lo que se cobro esa noche no puede cambiar**. Y de paso,
> un reporte de un mes no tiene que volver a sumar miles de renglones para saber cuanto
> entro.

**Una cuenta cerrada no admite pedidos nuevos.** Si la mesa vuelve a pedir, se abre otra.

### Propina e impuesto

Los dos son **porcentajes configurables** que se aplican sobre el subtotal:

- **La propina se puede quitar.** Es voluntaria y el sistema tiene que permitir
  rechazarla — mostrarla como obligatoria seria mentirle al cliente
- **El impuesto viene en 0 por defecto**: cada restaurante configura el que le aplique.
  Nunca escrito en codigo (regla del proyecto)

### Anular

Una cuenta se **anula**, nunca se borra (Regla de SPEC-008). Exige **motivo** y queda con
**responsable**.

- Anular una cuenta **abierta**: sus pedidos quedan anulados con ella
- Anular una cuenta **cerrada** es reversar un cobro: mas grave, y por eso queda igual de
  registrado. Nada se borra

Esto es lo que finalmente le da uso a `Pedido.ANULADO` y `motivo_anulacion`, que existen
en el modelo **desde el inicio del proyecto sin ningun endpoint que los use**.

### Costo de envio (domicilios, agregado 2026-09-16)

Al confirmar un pedido de domicilio, el mesero indica **cuanto cuesta el envio**. Es
opcional: vacio o cero significa domicilio gratis.

- Se pide en la misma pantalla donde se confirma el QR del domicilio (SPEC-004), justo
  antes de enviarlo a cocina
- Se guarda en la cuenta y se **suma al total**, como una linea propia — igual que la
  propina o el impuesto, pero fijo: no cambia si se agregan mas platos despues
- Aparece en el tiquete y en el detalle de la cuenta como "Envio"
- Una mesa no tiene costo de envio; el campo queda en cero

### Relacion con el salon (SPEC-012)

La tarjeta de cada mesa muestra **el total de su cuenta abierta**, como hace el sistema que
se va a reemplazar (`MESA #3 → $100.000`).

> [!important] Cobrar libera la mesa, salvo pago anticipado (revisado 2026-09-16)
> **Antes:** cerrar la cuenta no liberaba la mesa; se *ofrecia* liberarla despues. En la
> prueba de estres las mesas quedaron ocupadas, y un pedido ya cobrado seguia aceptando
> platos que nunca se cobraban.
>
> **Decision del autor:** *"cuando se cobre es porque el cliente pago y se esta yendo, a
> menos que cobre anticipado"*. Desde esta revision:
>
> - **Cobrar** significa que el cliente pago para irse: **la mesa queda libre** en el mismo
>   paso. La pantalla lo explica antes de cobrar.
> - **Pago anticipado:** una casilla al cobrar. El cliente paga y **sigue en la mesa**; la
>   mesa queda ocupada. Si despues pide algo mas, es un **pedido nuevo** que abre otra
>   cuenta (Regla 5). "Cobrar al finalizar" del Camino B es siempre anticipado.
> - Un domicilio no tiene mesa: cobrar no cambia nada del salon.

Y al reves: **liberar una mesa con cuenta abierta esta permitido** y no toca la cuenta. La
cuenta sigue viva y se llega a ella desde la lista de cuentas abiertas. Es el mismo caso
del cliente que empaco y se fue.

### Vueltos (efectivo, agregado 2026-09-16)

Al cobrar en **efectivo**, quien cobra puede indicar **con cuanto pago el cliente**. El
sistema calcula el vuelto y lo muestra en un mensaje antes de confirmar.

- **Solo aplica a Efectivo.** Con cualquier otro medio de pago el campo no aparece
- **Opcional.** Si se deja vacio, se asume que pago el valor exacto — el cobro sigue
  funcionando igual que antes
- Si lo recibido es **menor** que el total, se rechaza: "Faltan $X"
- Si es mayor o igual, se muestra **"Vuelto: $X"**, y se guarda junto con la cuenta
  (`recibido_efectivo`, `vuelto_efectivo`) para el tiquete y para revisar despues
- **No genera un movimiento de caja aparte.** Lo que entra a la caja sigue siendo el total,
  igual que hoy; el vuelto sale del bolsillo de quien cobra en ese momento. Llevar el
  control del sencillo por turno queda fuera de alcance — ver [[SPEC-025 - Vueltos]]

## Reglas

1. **Una cuenta abierta por mesa.** Dos grupos en la misma mesa es dividir cuenta, fuera
   de alcance.
2. **Los estados de cocina y los de dinero no se mezclan.** Un pedido `entregado` con
   cuenta `abierta` es lo normal: se comieron la comida y todavia no pagan.
3. **Cerrar exige medio de pago.** Sin el, el cierre de caja no puede cuadrar nada.
4. **Cerrar congela los totales.**
5. **Una cuenta cerrada no recibe pedidos** ni cambia de total. Tampoco se pueden agregar,
   quitar ni cambiar cantidades en un pedido ya cobrado: el servidor lo rechaza y dice que
   se cree un pedido nuevo (revisado 2026-09-16, defecto de la prueba de estres).
9. **El envio es fijo por cuenta**, no se recalcula si cambian los platos.
10. **El vuelto es informativo**, no mueve dinero entre cajas.
6. **Anular exige motivo**, siempre, abierta o cerrada.
7. **Cualquier mesero** puede cerrar una cuenta, coherente con el salon compartido. Quien
   cerro queda registrado.
8. **Nada se borra.**

## Criterios de aceptacion

### Revision del 2026-09-16

- [x] Cobrar una mesa sin marcar "pago anticipado" la deja **libre**
- [x] Con "pago anticipado" la mesa sigue **ocupada**
- [x] Antes de cobrar, la pantalla explica que cobrar libera la mesa
- [x] Agregar, quitar o cambiar la cantidad en un pedido cuya cuenta ya se cobro se
      **rechaza** con un mensaje que dice crear un pedido nuevo
- [x] Un pedido nuevo en esa mesa, despues del pago anticipado, abre **otra** cuenta

- [x] Confirmar un domicilio con costo de envio de $8.000 y una venta de $50.000 cobra
      un total de $58.000
- [x] El tiquete y el detalle de la cuenta muestran el envio como linea propia
- [x] Cobrar en efectivo con $50.000 recibidos sobre una cuenta de $40.000 muestra
      "Vuelto: $10.000" y lo guarda
- [x] Cobrar en efectivo con menos de lo que vale la cuenta se rechaza con "Faltan $X"
- [x] Dejar el campo de recibido vacio cobra igual, sin vuelto
- [x] Cobrar con un medio distinto de Efectivo no pide ni guarda recibido ni vuelto

> [!note] Como se verifico (2026-09-16)
> 8 pruebas nuevas: `pedidos/tests.py` (`Spec013CostoDeEnvio`, 4) y `ventas/tests.py`
> (`Spec025Vueltos`, 4), contra el flujo real (firmar QR, confirmar, cobrar). Se probaron
> el domicilio con y sin envio, una mesa que lo ignora, el envio negativo rechazado, el
> vuelto calculado y guardado, pagar de menos rechazado sin cerrar la cuenta, cobrar sin
> indicar recibido, y que un medio que no es Efectivo ignore el campo. El frontend
> (Escaner con el campo de envio, Cuentas con los botones de billete y el mensaje de
> vuelto, y el tiquete con las dos lineas nuevas) se compilo pero no se recorrio en
> pantalla.

### Originales

- [x] Confirmar el primer pedido de una mesa **abre** su cuenta
- [x] Un segundo pedido en esa mesa **se suma** a la misma cuenta, no crea otra
- [x] Un domicilio abre **su propia** cuenta
- [x] El total de la cuenta es la suma de los renglones de todos sus pedidos
- [x] La tarjeta de la mesa en el salon muestra ese total
- [x] Cerrar **exige** medio de pago
- [x] Al cerrar quedan congelados subtotal, propina, impuesto y total
- [x] Cambiar despues el precio de un plato **no altera** el total de una cuenta cerrada
- [x] Una cuenta cerrada **rechaza** pedidos nuevos
- [x] La propina se puede **quitar**
- [x] Con impuesto configurado en 0, no aparece en la cuenta
- [x] La lista de **cuentas abiertas** muestra lo servido y no cobrado, con su total
- [x] Anular **exige motivo** y queda con responsable
- [x] Anular una cuenta abierta deja sus pedidos anulados
- [x] **Liberar una mesa con cuenta abierta** no altera la cuenta
- [x] Cerrar **ofrece** liberar la mesa, no lo hace solo
- [x] Sin sesion no se puede abrir, cerrar ni anular
- [x] Sin desborde horizontal en 375 px

> [!note] Revisado 2026-09-14
> Hasta esta fecha las apps `pedidos` y `estaciones` no tenian ni una prueba, y estos
> criterios estaban construidos pero sin marcar. Se comprobaron con
> `backend/pedidos/tests.py`, que nombra en cada prueba la linea del
> criterio que verifica. Lo del cobro y la anulacion ya tenia pruebas en `ventas`;
> el impuesto en 0 se esconde en `MeseroCuentas` con `v-if="abierta.impuesto > 0"`. El de 375 px sale de
> [[SPEC-022 - Auditoria Responsive]].

## Dependencias

- [[SPEC-012 - Vista de Salon y Estado de Mesas]] — donde se ve el total
- [[SPEC-011 - Novedades sobre Pedidos Enviados]] — editar un pedido cambia el total
- [[SPEC-008 - Contabilidad y Auditoria]] — las reglas que esto empieza a cumplir
- [[ADR-007 - Una novedad es un evento, no una modificacion]] — anular se registra igual

## Preguntas abiertas

- **Numeracion visible.** El sistema actual muestra `N° 7818`; el personal se refiere a las
  cuentas por ese numero. Se usa el id por ahora — si hace falta numeracion por dia o por
  turno, es un refinamiento posterior
- **Cuenta de un domicilio con varias rondas** — hoy cada domicilio es una cuenta; si
  alguien pide dos veces, son dos cuentas
- ~~**Costo de envio de los domicilios**~~ — **resuelto 2026-09-16**, ver "Costo de envio"
  en Comportamiento
