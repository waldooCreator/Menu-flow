---
tipo: bitacora
fecha: 2026-08-30
tags: [bitacora, domicilios, salon, venta-rapida, spec-012, spec-004]
---

# 2026-08-30 — Zona de domicilios y cobrar al finalizar

Dos pedidos del autor, salidos de repasar el sidebar de Springfield seccion por seccion.

## Lo que ya existia

El autor pidio que un QR de "A distancia" se leyera como pedido a distancia y entrara al
ciclo normal con etiqueta de domicilio. **Eso ya estaba** desde SPEC-002 y SPEC-011: el QR
lleva la marca, entra a cocina como cualquier pedido, y muestra `destino: "Domicilio"`.

Lo verdaderamente nuevo fue la **zona en el salon** — que en SPEC-012 se habia excluido a
proposito, porque los domicilios no ocupan mesa.

## La zona de domicilios

Seccion propia debajo de la rejilla de mesas. **Sin tope**: el sistema que se va a
reemplazar tiene 10 puestos fijos numerados, como si fueran mesas; aqui es una lista que
crece. Verificado con 15 a la vez.

### La regla que decidio el autor

> Un domicilio se va de la zona **solo al marcarse entregado**. Cobrarlo NO lo retira.

Cobrar y entregar quedan **desacoplados**: se puede pagar por anticipado, al recibir, o en
cualquier orden. Por eso cada tarjeta muestra **las dos cosas a la vez** — verde
**PAGADO** o ambar **COBRAR AL ENTREGAR** — porque quien reparte necesita saber de un
vistazo si cobra al llegar. Un domicilio pagado pierde el boton de cobrar y solo conserva
el de entregar.

### Dos restricciones que hubo que levantar

`EntregarPedidoView` traia dos supuestos que ya no aplicaban:

**Exigia que el pedido estuviera `listo` o `en_preparacion`.** Para un domicilio no sirve:
"entregado" lo decide el mesero cuando el domiciliario vuelve, que puede ser mucho despues
—o antes— de que cocina marque nada. Se relajo **solo para domicilios**; un pedido de mesa
en `pendiente` se sigue rechazando, y eso quedo verificado.

**Filtraba por `mesero=request.user`** — solo quien tomo el pedido podia entregarlo. Eso ya
contradecia el salon compartido de SPEC-012, y en un domicilio es peor: quien recibe al
domiciliario rara vez es quien tomo el pedido. Se levanto, y a cambio se agregaron
`entregado_por` y `entregado_en` — **la trazabilidad no se pierde, cambia de dueño**.

## Cobrar al finalizar (la "venta rapida")

Casilla en el Camino B. Marcada, el boton cambia a **"Enviar y cobrar"**, aparecen los
medios de pago, y al confirmar el pedido entra a cocina **y la cuenta se cierra en la misma
llamada**. Sin marcar, todo sigue igual que antes.

No se duplico el flujo: es el mismo Camino B con un paso mas. Un camino paralelo
significaria mantener dos versiones de lo mismo, y tarde o temprano se desincronizan.

> [!important] El cobro va FUERA de la transaccion del pedido, a proposito
> Si el cobro falla —medio de pago invalido, sin permiso— el pedido **ya esta en cocina y
> debe quedarse ahi**. Meterlo en la misma transaccion haria que un error de cobro
> cancelara comida que quizas ya estan preparando.
>
> Verificado: con una caja inexistente, el pedido se crea igual (201), la respuesta avisa
> `aviso_cobro`, y la cuenta queda **abierta** para cobrarla desde Cuentas.

La opcion solo aparece si el usuario puede cobrar — se apoya en el mismo permiso
configurable de SPEC-014, y el servidor la rechaza igual si la fuerza.

## Cambio de forma en la API del salon

`GET /api/mesas/salon/` pasa de devolver una lista a `{mesas, domicilios}`. Rompia el
frontend, que se actualizo en la misma tanda.

## Verificado

Prueba automatizada contra la API real, **todo en verde**:

- El salon devuelve mesas **y** domicilios; los domicilios **no** aparecen entre las mesas
- **15 domicilios se ven los 15** — sin tope
- Un domicilio nace sin cobrar; **cobrarlo NO lo retira** y queda marcado como pagado
- **Solo entregar lo retira**
- Un domicilio en `pendiente` **si** se puede entregar; uno de **mesa** en `pendiente` se
  rechaza con su mensaje
- Lo entrega **un mesero distinto** al que lo tomo
- Sin medio de pago la cuenta queda **abierta**; con medio, **cerrada** y con su medio
- Con caja invalida: **el pedido entra igual**, avisa, y la cuenta queda abierta

En navegador: la zona muestra "Ana Ruiz · PAGADO · Marcar entregado" junto a dos con
"COBRAR AL ENTREGAR · Cobrar · Marcar entregado", y la Mesa 12 ocupada aparte. Entregar el
pagado y uno sin cobrar los retira a ambos. En el Camino B, marcar la casilla cambia el
boton a "Enviar y cobrar", muestra los cinco medios, y termina en **COBRADO** — con la
cuenta cerrada en Nequi por $15.400 y la mesa **ocupada con cuenta en cero**, que es lo
correcto: se cobro, pero la mesa no se libera sola.

Sin desborde horizontal en 375 px; el unico control bajo 40 px es "Salir", preexistente.

> [!warning] No verificado por Claude
> El **aspecto** de la zona de domicilios. El panel no compone frames.

## Enlaces

- [[SPEC-012 - Vista de Salon y Estado de Mesas]]
- [[SPEC-004 - Modulo Mesero]]
- [[SPEC-002 - QR de Pedido]]
- [[Comparativa Sidebar - Springfield vs Sistema Nuevo]]
- [[Inicio]]
