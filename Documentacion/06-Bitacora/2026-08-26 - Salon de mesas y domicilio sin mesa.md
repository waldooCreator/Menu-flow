---
tipo: bitacora
fecha: 2026-08-26
tags: [bitacora, salon, mesas, domicilio, spec-012]
---

# 2026-08-26 — Salon de mesas y domicilio sin mesa

Dos entregas que resultaron ser la misma: para que el salon sirviera, el domicilio tenia
que dejar de fingir que era una mesa.

## Lo esencial

[[SPEC-012 - Vista de Salon y Estado de Mesas]] nueva, y con ella se retira un parche que
llevaba semanas: la **mesa virtual "Domicilio"**.

## La regla que fijo el autor

> El mesero manda. El sistema nunca espera, nunca adivina y nunca se traba.

El caso que la justifica, en sus palabras: un cliente pide, **empaca la comida y se va**.
El sistema no tiene forma de saberlo y no debe intentar adivinarlo — el mesero libera la
mesa y punto.

Esa regla mato varias ideas que se habian propuesto antes en el estudio previo y que
**el autor rechazo con razon**: liberar por temporizador, deducir presencia del escaneo del
QR de mesa, y preguntarle al cliente si ya se iba. Todas metian al sistema a adivinar.

El resultado es mas simple: **dos transiciones, cada una colgada de un acto humano**.

| Evento | Efecto |
|---|---|
| El cliente escanea el QR de la mesa | **Nada** |
| El cliente genera su QR de pedido | **Nada** |
| El mesero confirma el pedido | Mesa **ocupada** |
| El mesero toca "Liberar" | Mesa **libre** |

Mas "apartar" a mano, para los que se sentaron y todavia estan mirando el menu.

## Decision de fondo: el estado se guarda, no se deduce

Se penso primero en **derivar** el estado de los pedidos activos. Es lo elegante y es lo
equivocado: si el estado se deduce, "liberar" tendria que ir a **cerrar pedidos** — y ahi
es exactamente donde el sistema se trabaria, justo lo que la regla prohibe.

Guardado, en cambio, **liberar la mesa y cerrar el pedido son independientes**: la mesa
queda libre de inmediato y el pedido sigue su vida (cocina lo prepara, se entrega). El
endpoint **avisa** cuantos pedidos quedan en curso, pero **no impide** nada.

`Mesa.cambiar_estado()` no valida transiciones a proposito. Eso ademas hace trivial el
"Revertir": es la misma llamada con el estado anterior.

## El domicilio deja de ser una mesa

`Pedido.mesa` era **obligatorio**, asi que un pedido a distancia se anclaba en una fila
`Mesa` llamada "Domicilio / Para llevar". Con el salon, esa fila **aparecia como una mesa
mas que alguien tendria que liberar**.

Ahora `Pedido.mesa` admite vacio y el pedido lleva `es_domicilio`. Asi el domicilio no toca
el salon **por construccion, no por un filtro que alguien pueda olvidar** — que era el
punto.

> [!note] La fila vieja no se borro
> Migracion `0004`: se **desactiva**, no se elimina. Hay pedidos historicos que la
> referencian con `PROTECT`, y borrarla reescribiria el pasado — justo lo que prohibe la
> Regla 1 de [[SPEC-008 - Contabilidad y Auditoria]]. Los pedidos que la usaban quedaron
> marcados `es_domicilio=True`.

### El formulario y la plantilla

El flujo que definio el autor: carrito → "A distancia" → **formulario (nombre + direccion
exacta)** → QR + **boton de descargar** → WhatsApp con el mensaje **ya armado**.

Los datos se guardan en `localStorage` del propio cliente, para que la proxima vez el
formulario venga lleno.

**Correccion sobre lo que yo habia propuesto:** yo queria meter la direccion **dentro del
QR**. El autor la puso en el **mensaje de WhatsApp**, y es mejor: es donde la persona la va
a leer de todos modos, y el QR no gasta capacidad. Lo unico que el QR necesita es la marca
`d` de domicilio, para que al confirmar no se pida mesa.

`whatsapp-mensaje` dejo de ser una frase fija y paso a ser **plantilla con variables**
(`{nombre}`, `{direccion}`). Una variable desconocida **se deja tal cual**, visible: si el
administrador escribe `{telefono}`, lo ve y lo corrige. Fallar en silencio seria peor.

> [!warning] Consecuencia aceptada, no descuido
> **El sistema no guarda la direccion.** Vive solo en el chat de WhatsApp — que es tambien
> donde se verifica el pago, asi que el chat es el registro operativo de esta etapa. La
> comanda que ve cocina dira "domicilio" sin destino.

## Verificado

Prueba de punta a punta contra la API real (script en el scratchpad), toda en verde:

- El salon lista **solo mesas fisicas**; la virtual no aparece
- Apartar funciona; un estado invalido se rechaza; una mesa inexistente da 404
- **Confirmar un pedido deja la mesa ocupada**
- **Liberar con un pedido en cocina funciona y no toca el pedido** — las comandas siguen ahi
- Domicilio: se firma **sin mesa aunque venga una pegada**, se verifica con la marca, se
  confirma **sin pedir mesa**, y **no ocupa ninguna mesa**
- **Compatibilidad**: un QR emitido antes del cambio (sin la clave `d`) sigue siendo valido
  y no se toma por domicilio

En navegador: tres estados con tres colores distintos, concordancia correcta
("4 libres", "1 apartada"), sin desborde horizontal en 375 px, el formulario valida ambos
campos, el cache pre-llena, el enlace de WhatsApp sale con nombre y direccion dentro, y la
descarga produce `pedido-Springfield.png`.

### Falsa alarma: "el Revertir no se va"

Medi que el recuadro seguia en el DOM a los 6 y a los 10 segundos. **El codigo estaba
bien.** El panel del navegador corre con `document.hidden = true`, y ahi **las
transiciones CSS no terminan**: `transitionend` nunca llega, Vue no elimina el nodo, y
queda conectado con `opacity: 0`. Mi criterio era "existe en el DOM" cuando debia ser
"Vue inicio la salida".

Medido bien: **5,1 segundos**. La misma causa hace que la transicion de *entrada* tampoco
avance, asi que en este panel el recuadro nunca llega a `opacity: 1` — por eso "visible"
no era un criterio utilizable aqui.

> [!warning] No verificado por Claude
> El **aspecto** del salon y la animacion del recuadro de deshacer. El panel no compone
> frames (los screenshots dan tiempo de espera agotado), asi que todo se comprobo por
> medicion del DOM y de la API, nunca mirando.

## Pendiente

- El registro de pedidos del mesero (`GET /api/pedidos/`) **sigue sin existir**. Lo piden
  tanto esta spec (enlazar la mesa a su pedido activo) como
  [[Novedades sobre Pedidos en Curso]]. Es el mismo hueco para las dos cosas
- Plano del local con las mesas en su posicion real — antes hace falta el CRUD de mesas
  desde el panel, que SPEC-001 tiene pendiente
- Rotacion de mesas como KPI: el dato (`estado_desde`) ya se guarda, el reporte no existe

## Enlaces

- [[SPEC-012 - Vista de Salon y Estado de Mesas]]
- [[SPEC-002 - QR de Pedido]]
- [[SPEC-001 - QR de Mesa]]
- [[SPEC-007 - Administracion y Parametrizacion]]
- [[Novedades sobre Pedidos en Curso]]
- [[Inicio]]
