---
tipo: spec
id: SPEC-017
estado: implementada
actualizado: 2026-09-14
tags: [menu, cocina, disponibilidad]
---

# SPEC-017 — Agotar un plato desde Cocina

> [!success] Estado: Implementada — verificada el 2026-09-07

## Proposito

Que cocina pueda marcar un plato como agotado en el momento en que se acaba el
ingrediente, y que **de inmediato** deje de ofrecerse a clientes y meseros.

## El problema real

Hoy solo el administrador puede marcar un plato como agotado, desde el panel.
Pero **quien se entera primero de que no hay carne es cocina**, no el
administrador. En la practica eso significa que se siguen tomando pedidos de
algo que no existe durante todo el rato que tarde alguien en avisarle al
administrador para que lo desmarque.

## Lo que YA existe (revisado en codigo el 2026-09-03)

Buena parte del mecanismo esta construido. Conviene saberlo para no rehacerlo:

| Ya funciona | Donde |
|---|---|
| El campo `disponible` en el plato | `menu/models.py` |
| El cliente ve los agotados en gris, no ocultos | SPEC-003 |
| Al **firmar el QR** se rechaza un plato agotado | `FirmarPedidoView` |
| Al **agregar** a un pedido en curso se rechaza | `novedades.agregar_item` (SPEC-011) |
| La respuesta de **verificar** ya trae `disponible` por renglon | `VerificarPedidoView` |

## Los tres huecos

### Hueco 1: cocina no puede tocarlo

Cambiar `disponible` exige ser administrador (`AdminOSoloLectura` pide
`is_staff`). Cocina no puede, que es justo al reves de lo que hace falta.

### Hueco 2: el QR firmado no se revalida al confirmar

Este es el grave, y es una carrera contra el tiempo real:

1. El cliente arma su pedido a las 8:00 — el plato esta disponible
2. Genera su QR
3. A las 8:05 cocina marca el plato como agotado
4. A las 8:07 el mesero escanea ese QR y confirma

**Hoy el pedido entra igual.** `ConfirmarPedidoView` no vuelve a mirar
`disponible`; confia en que se valido al firmar. Resultado: llega a cocina una
comanda de algo que cocina acaba de declarar imposible.

Que el QR este firmado garantiza que **nadie lo altero**, no que el mundo no
haya cambiado desde entonces.

### Hueco 3: el menu del cliente no se entera

`ClienteMenu` carga los platos una vez y no vuelve a preguntar. Un cliente con
el menu abierto puede seguir agregando al carrito algo que ya se agoto. No se
entera hasta que intenta generar el QR.

## Comportamiento

### Cocina marca el agotado

En el tablero de estacion, cada plato de las comandas visibles y un buscador
del menu permiten marcarlo agotado en un toque. El cambio es **inmediato y
global**: no hay confirmacion del administrador de por medio.

**Solo puede agotar y reactivar**, nada mas del plato. No puede cambiar precio,
nombre ni foto — para eso esta el panel.

> [!note] Por que sin confirmacion del administrador
> Si agotar exigiera aprobacion, en la practica no se usaria: nadie va a
> perseguir al dueño a mitad de servicio. Un plato marcado por error se
> reactiva en un toque, y el costo de ese error es mucho menor que el de
> seguir vendiendo algo que no existe.

### Queda registrado quien lo hizo

Cada cambio de disponibilidad guarda **quien** y **cuando**. Sin eso, "¿por que
no se vendio el ceviche anoche?" no tiene respuesta.

### La revalidacion al confirmar (hueco 2)

Al confirmar, se vuelve a comprobar la disponibilidad de cada renglon **contra
la base, en ese instante**. Si alguno se agoto:

- El pedido **no entra**
- El mesero recibe un mensaje que **nombra el plato**: "«Ceviche de la casa» se
  agoto. Pidele al cliente que elija otra cosa."

Se rechaza el pedido completo, no se cuela lo demas: un pedido a medias que el
cliente no acordo es peor que ninguno. El mesero rehace el pedido con el
cliente delante, que es quien decide con que reemplazarlo.

### El aviso antes de confirmar

`VerificarPedidoView` ya devuelve `disponible` por renglon. La pantalla del
mesero debe **mostrarlo en rojo antes de que pulse confirmar**, para que la
conversacion con el cliente ocurra antes del error, no despues.

### El menu del cliente se refresca (hueco 3)

El menu del cliente vuelve a consultar la disponibilidad **al volver a la
pestaña** y cada cierto tiempo mientras esta abierto. Un plato que se agota
mientras el cliente mira se pone en gris solo.

Si ya estaba en el carrito, se marca ahi tambien y **el boton de generar el QR
se bloquea** hasta que lo quite, explicando cual es el problema.

### Lo que NO cambia

Un pedido **ya confirmado** que contiene el plato **no se toca**. Ya esta en
cocina, ya se esta preparando o ya se preparo. Si de verdad no se puede hacer,
alguien lo anula a mano con su motivo — el sistema no decide eso solo.

## Reglas

1. **Cocina puede agotar y reactivar cualquier plato**, sin aprobacion previa.
2. **Cocina NO puede cambiar nada mas** del plato.
3. **Cada cambio guarda quien y cuando.**
4. **Se revalida al confirmar**, contra la base y en ese instante.
5. **Un plato agotado rechaza el pedido completo**, no parcialmente.
6. **Los pedidos ya confirmados no se alteran.**
7. El agotado **se ve, no se oculta** (SPEC-003): en gris y sin poder pedirse.

## Casos que hay que probar

Escritos como casos, no como buenas intenciones. Cada uno es un test.

### En el servidor

- [x] Cocina marca agotado y el plato queda agotado
- [x] Cocina **reactiva** y vuelve a estar disponible
- [x] Cocina **no puede** cambiar precio ni nombre (403 o campo ignorado)
- [x] Un mesero **no puede** agotar un plato (no es su trabajo)
- [x] Un cliente sin sesion **no puede** agotar nada
- [x] Queda registrado **quien** lo agoto y **cuando**
- [x] **Firmar** un QR con un plato agotado se rechaza, nombrando el plato
- [x] **Confirmar** un QR firmado ANTES de que se agotara se rechaza, nombrando el plato
- [x] Ese rechazo **no crea el pedido ni la cuenta** — nada a medias
- [x] Un pedido con dos platos, uno agotado: **se rechaza completo**, no entra el otro
- [x] **Agregar** un plato agotado a un pedido en curso se rechaza (SPEC-011)
- [x] Un pedido **ya confirmado** con ese plato **sigue igual**: no se anula ni se altera
- [x] Dos cocineros agotando el mismo plato a la vez no rompen nada
- [x] Cocina agota mientras el mesero confirma: gana la base, el pedido se rechaza

### En pantalla

- [x] El cliente ve el plato pasar a gris **sin recargar**
- [x] Un plato agotado **que ya estaba en el carrito** se marca ahi
- [x] Con un agotado en el carrito, **el boton de generar QR se bloquea**
- [x] El mensaje **dice cual plato** es el problema, no un error generico
- [x] Al quitarlo del carrito, el boton **se desbloquea**
- [x] El mesero ve en **rojo** el renglon agotado al verificar, ANTES de confirmar
- [x] En Camino B (mesero arma el pedido) pasa lo mismo
- [x] Sin desborde horizontal en 375 px

## Plan de implementacion

### Paso 1 — Permiso y registro (2 horas)

- Endpoint propio `POST /api/platos/<id>/disponibilidad/` que **solo** cambia
  ese campo. Permiso: cocina o administrador
- Campos `disponible_cambiado_por` y `disponible_cambiado_en` en el plato
- Migracion

**Por que un endpoint propio y no abrir el del plato:** si se le diera permiso
de escritura a cocina sobre `PlatoViewSet`, tendria acceso a precio, nombre y
foto. Un endpoint que solo toca un booleano no puede hacer nada mas, aunque
alguien se equivoque despues.

### Paso 2 — Revalidar al confirmar (2 horas)

En `ConfirmarPedidoView`, dentro de la transaccion que ya existe y **antes** de
crear nada, comprobar la disponibilidad de todos los renglones. Si alguno
fallo, responder 409 nombrando el plato.

Va dentro de la transaccion a proposito: fuera de ella seria otra carrera como
la de [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]].

**Tests primero**, los del bloque "En el servidor".

### Paso 3 — Cocina agota desde su tablero (medio dia)

Un buscador del menu en `EstacionTablero` con el interruptor de agotado por
plato, y el mismo interruptor sobre los platos de las comandas visibles — que
es donde cocina se entera de que se acabo.

### Paso 4 — El cliente se entera (medio dia)

- `ClienteMenu` refresca la disponibilidad al volver a la pestaña y cada 60
  segundos
- El carrito marca los agotados y bloquea el boton de generar QR, nombrandolos
- La pantalla del mesero pinta en rojo los renglones agotados al verificar

### Paso 5 — Comprobacion y documentacion (medio dia)

Los casos de pantalla con clics reales, actualizacion de SPEC-003 y SPEC-005, y
bitacora.

**Total estimado: dos dias.**

## Dependencias

- [[SPEC-003 - Menu del Cliente]] — el agotado se ve en gris, no se oculta
- [[SPEC-005 - Estaciones y Ruteo]] — el tablero de cocina
- [[SPEC-011 - Novedades sobre Pedidos Enviados]] — agregar a un pedido en curso
- [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]] — el patron de revalidar dentro de la transaccion

## Preguntas abiertas

- [x] ¿El aviso de "se agoto el ceviche" deberia llegarle tambien a los meseros
      como notificacion, o basta con que lo vean en gris? **Resuelta (2026-09-14):**
      quedo **sin** notificacion, como se propuso; el mesero lo ve en gris. Si en
      servicio hace falta, agregarla es facil.
