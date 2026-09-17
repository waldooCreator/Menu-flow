---
tipo: spec
id: SPEC-012
estado: implementada
actualizado: 2026-09-14
tags: [mesero, mesas, salon, ocupacion]
---

# SPEC-012 — Vista de Salon y Estado de Mesas

> [!success] Estado: Implementada — revisada 2026-09-14
> Reemplaza la exclusion que [[SPEC-001 - QR de Mesa]] tenia sobre "estado de ocupacion
> de la mesa".

## Proposito

Que el mesero vea de un vistazo que mesas estan libres y cuales ocupadas, y pueda actuar
sobre cualquiera de ellas sin que el sistema lo haga esperar.

## Regla de oro

> [!important] El mesero manda
> El sistema **nunca espera, nunca adivina y nunca se traba**. No hay temporizadores que
> liberen mesas, no hay estados que el sistema infiera por su cuenta, y ninguna accion del
> mesero puede quedar bloqueada por el estado de un pedido.
>
> El caso que lo justifica: un cliente pide, **empaca la comida y se va**. El sistema no
> tiene forma de saberlo y no debe intentar adivinarlo. El mesero libera la mesa y punto.

## Alcance

- Pantalla de salon con todas las mesas fisicas activas y su estado
- **Zona de domicilios** (2026-08-30): seccion aparte, en la misma pantalla, con todos los
  domicilios en curso
- Tres estados de mesa, con color distinto
- Apartar una mesa a mano (clientes sentados que todavia no piden)
- Liberar una mesa, siempre disponible, en cualquier estado
- Crear un pedido desde la mesa (entra al Camino B de [[SPEC-004 - Modulo Mesero]])
- Deshacer la ultima accion durante 5 segundos

## Fuera de alcance

- **Reservas** — es un modulo aparte
- **Unir o separar mesas** para un grupo grande — ya excluido en SPEC-001; un pedido que
  abarca varias mesas rompe el modelo actual
- **Plano del local** con las mesas en su posicion fisica. La primera version es una
  rejilla de tarjetas. Motivo: hoy **ni siquiera se puede crear una mesa desde el panel**
  (SPEC-001 lo tiene pendiente); un editor de plano antes del CRUD basico es empezar por
  el tejado
- **Asignacion de mesas por mesero** (secciones). El salon es compartido: cualquier mesero
  puede actuar sobre cualquier mesa
- **Cuenta y cobro** — fuera del proyecto entero
- Cantidad de comensales por mesa

## Comportamiento

### Los tres estados

| Estado | Que significa | Como entra | Como sale |
|---|---|---|---|
| **Libre** | Nadie sentado | Al liberar | Se aparta, o se confirma un pedido |
| **Apartada** | Clientes sentados, **sin pedido todavia** (estan mirando el menu) | El mesero la marca a mano | Se confirma un pedido, o se libera |
| **Ocupada** | Clientes con pedido enviado a cocina | **El mesero confirma un pedido** sobre esa mesa | Solo al liberar |

### Que NO cambia el estado

- **Que el cliente escanee el QR de la mesa: no pasa nada.** Sigue como este.
- **Que el cliente genere su QR de pedido: no pasa nada.** Si lo genera y no se lo muestra
  a nadie, no hay pedido y la mesa no cambia.

La mesa pasa a **ocupada** unicamente cuando **el mesero confirma el pedido** — sea
leyendo el QR del cliente (Camino A) o armandolo desde cero (Camino B).

### Acciones sobre una mesa

Al tocar una mesa se abren, para **cualquier mesero**, siempre:

- **Liberar** — se fueron, sin importar el motivo ni el estado del pedido
- **Apartar** — se sentaron y todavia no piden
- **Hacer pedido** — lleva al Camino B con la mesa ya elegida

### Liberar no cierra el pedido

Son dos cosas independientes. Al liberar una mesa con un pedido en curso:

- La mesa queda **libre** de inmediato
- El pedido **sigue su vida normal**: cocina lo prepara, se marca listo, se entrega

El sistema **puede avisar** que queda un pedido en curso, pero **no puede impedir** la
liberacion. Impedirla seria trabarse.

### La zona de domicilios (2026-08-30)

En la misma pantalla del salon, **debajo de la rejilla de mesas**, una seccion propia con
los domicilios en curso.

> [!important] Sin limite de cuantos caben
> El sistema que se va a reemplazar tiene una "ZONA DOMICILIO" con **10 puestos fijos**
> numerados, como si fueran mesas. Aqui no: es una **lista que crece**. Un restaurante con
> 30 domicilios un viernes no deberia quedarse sin donde ponerlos.

#### Que entra y que sale

Un domicilio aparece **desde que se confirma el pedido** y se va **solo cuando se marca
como entregado**. Nada mas lo saca de ahi.

> [!important] Cobrar y entregar son independientes
> Se puede cobrar **antes** (pago anticipado al recibir el pedido), **despues** de
> entregar, o en cualquier orden. **Cobrar NO retira la tarjeta.**
>
> Por eso cada tarjeta muestra **las dos cosas a la vez**: si esta cobrado y si esta
> entregado. Un domicilio cobrado pero sin entregar sigue visible y **debe verse distinto**
> de uno sin cobrar — si no, quien reparte no sabe cual cobrar al llegar.

#### Acciones

Solo dos: **Cobrar** y **Marcar entregado**. Ni liberar ni apartar — esos conceptos son de
mesa fisica y aqui no aplican.

#### Entregar deja de depender del estado de cocina

> [!warning] Cambio deliberado sobre lo ya construido
> `EntregarPedidoView` exigia que el pedido estuviera `listo` o `en_preparacion`. Para un
> domicilio eso no sirve: "entregado" lo decide el mesero **cuando el domiciliario vuelve**,
> que puede ser mucho despues de que cocina terminara.
>
> Ademas filtraba por `mesero=request.user` — **solo quien tomo el pedido podia entregarlo**.
> Eso contradice el salon compartido de esta misma spec, y en un domicilio es peor: quien
> recibe al domiciliario rara vez es quien tomo el pedido.
>
> Las dos restricciones se levantan. Queda registrado quien entrego.

### Deshacer

Toda accion sobre el estado de una mesa muestra un recuadro **abajo a la derecha** con
**"Revertir"**, durante **5 segundos**. No hay dialogo de confirmacion: confirmar es hacer
esperar al mesero, justo lo contrario de la regla de oro.

## Reglas

- La **rejilla de mesas** muestra solo mesas fisicas activas. Los domicilios no tienen
  mesa, asi que no aparecen ahi — van en su propia zona (abajo).
- **Cualquier mesero** puede actuar sobre **cualquier mesa**. No hay dueno.
- El estado es un dato **guardado**, no derivado de los pedidos. Si se dedujera de los
  pedidos, "liberar" tendria que ir a cerrar pedidos — y ahi es exactamente donde el
  sistema se trabaria.
- Cada cambio de estado guarda **cuando** ocurrio, para poder mostrar el tiempo
  transcurrido y, mas adelante, la rotacion de mesas
  ([[SPEC-008 - Contabilidad y Auditoria]]).
- El color de "apartada" y el de "ocupada" deben ser **claramente distintos**.

> [!note] El rojo esta usado dos veces, a proposito
> Aqui rojo = mesa ocupada. En el tablero de cocina, rojo = novedad
> ([[Novedades sobre Pedidos en Curso]]). Son pantallas distintas y el autor lo acepto.
> A tener en cuenta si alguna vez se quiere resaltar una mesa con novedad **en el salon**:
> el rojo ya no estaria disponible para eso.

## Criterios de aceptacion

- [x] El salon lista todas las mesas fisicas activas, y **ninguna** mesa virtual
- [x] Los domicilios en curso aparecen en **su propia zona**, no entre las mesas
- [x] La zona de domicilios **no tiene tope**: 15 domicilios se ven los 15
- [x] Un domicilio **cobrado pero no entregado sigue visible**, y se distingue de uno sin cobrar
- [x] Marcar entregado **si** lo retira de la zona
- [x] Un domicilio se puede entregar **aunque su pedido no este listo** en cocina
- [x] Un domicilio lo puede entregar **cualquier mesero**, no solo quien lo tomo
- [x] Una mesa libre sobre la que el cliente escanea el QR **sigue libre**
- [x] Una mesa libre sobre la que el cliente genera su QR de pedido **sigue libre**
- [x] Confirmar un pedido (Camino A o B) deja esa mesa **ocupada**
- [x] Apartar una mesa libre la deja **apartada**, con color distinto al de ocupada
- [x] Confirmar un pedido sobre una mesa apartada la pasa a **ocupada**
- [x] Liberar funciona en cualquier estado, **incluso con un pedido en cocina**
- [x] Liberar una mesa con pedido en curso **no altera el pedido**: sigue en su estado
- [x] Tras cualquier cambio aparece "Revertir" abajo a la derecha y **desaparece a los 5 s**
- [x] "Revertir" devuelve la mesa al estado anterior
- [x] Desde una mesa se puede arrancar un pedido con esa mesa ya elegida
- [x] Sin desborde horizontal en 375 px

> [!note] Revisado 2026-09-14
> Hasta esta fecha las apps `pedidos` y `estaciones` no tenian ni una prueba, y estos
> criterios estaban construidos pero sin marcar. Se comprobaron con
> `backend/pedidos/tests.py`, que nombra en cada prueba la linea del
> criterio que verifica. "Revertir" desaparece a los 5 s por el `setTimeout` de
> `MeseroSalon.vue`, y arrancar un pedido desde la mesa lleva a `MeseroPedido`, que la
> toma de `route.query.mesa`. El de 375 px sale de
> [[SPEC-022 - Auditoria Responsive]].

## Dependencias

- [[SPEC-001 - QR de Mesa]] — de donde salen las mesas
- [[SPEC-004 - Modulo Mesero]] — Camino B y confirmacion
- [[SPEC-002 - QR de Pedido]] — los domicilios que no tocan el salon

## Preguntas abiertas

- Cuando exista el registro de pedidos del mesero (ver
  [[Novedades sobre Pedidos en Curso]]), la tarjeta de mesa deberia enlazar al pedido
  activo de esa mesa
- Rotacion de mesas como KPI: el dato queda guardado desde ya, el reporte no esta
