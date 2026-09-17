---
tipo: investigacion
actualizado: 2026-08-26
tags: [novedades, pedidos, cocina, mesero, auditoria]
---

# Novedades sobre Pedidos en Curso

> [!info] Que es esto
> Estudio pedido por el autor (2026-08-26) a partir de un requerimiento concreto: **que el
> mesero pueda editar un pedido ya enviado a cocina, y que el plato afectado se ponga en
> rojo en el tablero de la estacion**. El encargo incluyo buscar "novedades como esa" que
> un sistema de restaurantes deba tener si o si.
>
> Esto es investigacion, no spec. Lo que se apruebe de aqui se convierte en
> SPEC-011 y en uno o dos ADR.

## El requerimiento original

1. El mesero tiene un **registro de los pedidos que envio a cocina** y que aun no terminan
2. Puede **entrar y editarlos**
3. Al editar, se **notifica a la estacion**
4. El plato afectado —este *pendiente*, *en preparacion* o *listo*— **se pone en rojo**
   indicando que hay una novedad
5. La interfaz debe mostrar **el cambio**, de forma muy intuitiva

## Parte 1 — Lo que el requerimiento destapa

Antes del catalogo, cinco cosas que este pedido obliga a resolver y que hoy no estan.
No son opinion: se verificaron leyendo el codigo.

### 1.1 El mesero no tiene registro de pedidos. No existe.

El unico listado que ve el mesero es el de **notificaciones** (comandas ya listas). No hay
`GET /api/pedidos/` en `nucleo/api_router.py`: la API expone `firmar`, `verificar`,
`confirmar`, `notificaciones`, `<id>/entregar`. Nada mas.

**El punto 1 del requerimiento no es una pantalla nueva sobre algo existente — es
construir el registro desde cero.** Es el prerrequisito de todo lo demas.

### 1.2 "Editar" no puede ser un UPDATE

Este es el hallazgo mas importante del estudio.

`DetallePedido` guarda `nombre_congelado` y `precio_congelado` justamente para que el
historial no se reescriba solo — es la **Regla 1 de [[SPEC-008 - Contabilidad y Auditoria]]**,
marcada ahi como no negociable.

Si editar hace `detalle.cantidad = 3; detalle.save()`:

- se pierde para siempre que el cliente **habia pedido 2**
- los reportes dejan de decir "que se vendio" y pasan a decir "a que quedo editado"
- se viola la **Regla 2** (auditoria de solo insercion) — que ademas **hoy no tiene tabla:
  no existe ningun modelo de auditoria en el backend**

> [!danger] La conclusion
> Una novedad es un **hecho nuevo que se agrega**, nunca una modificacion sobre el hecho
> anterior. El estado actual del pedido se **deriva** de la suma de sus novedades.
> Si esto se implementa como UPDATE, se rompe el cimiento contable del proyecto
> completo, y se rompe de forma silenciosa: nada falla, solo los reportes mienten.

Esto merece un ADR propio.

### 1.3 El rojo es estado, no color

"Que se ponga en rojo" suena a CSS, pero no lo es:

- **Debe sobrevivir a recargar.** Si el rojo es una variable de Vue, el cocinero recarga y
  la novedad desaparece sin que nadie la haya visto. Tiene que ser un campo persistido.
- **Debe poder apagarse.** El cocinero necesita un boton tipo **"Visto"**. Sin eso, a las
  dos horas de servicio media pantalla esta en rojo y el rojo deja de significar nada.
  *Una alerta que nadie puede cerrar se vuelve papel tapiz.*
- **Debe decir QUE cambio**, no que "algo" cambio. Ver 3.2.
- **No todas las novedades pesan igual.** Cancelar un plato que ya esta en el fuego no es
  lo mismo que agregar una gaseosa.

### 1.4 Las notificaciones hoy son de una sola via

`pedidos.Notificacion` tiene FK **`mesero`** al usuario. Estructuralmente solo sabe hablarle
a un mesero. No hay forma de dirigir un aviso **a una estacion**.

El punto 3 del requerimiento (notificar a cocina) **no cabe en el modelo actual**. Hay que
abrir el destinatario: o usuario, o estacion.

Esto ademas desbloquea toda la familia B del catalogo (cocina → mesero), que hoy es
imposible.

### 1.5 Editar crea una carrera con "Listo"

El mesero edita en el mismo segundo en que la estacion marca la comanda lista. Hoy
`ComandaViewSet.lista()` no valida nada contra ediciones concurrentes.

Hace falta una **regla explicita por estado de comanda**:

| Estado de la comanda | Que pasa al editar |
|---|---|
| **Pendiente** | Edicion limpia. Se aplica y se avisa |
| **En preparacion** | Edicion **de riesgo**. Se aplica, se marca en rojo, y la estacion decide si alcanza |
| **Lista** | **Ya es tarde para ese plato.** El sistema debe decirlo, no aceptarlo en silencio |
| **Entregado / anulado** | No se edita. Si hay problema, es *devolucion* (D-10), no edicion |

SPEC-005 ya tenia pendiente el bloqueo de concurrencia entre dos personas de la misma
estacion. Editar en vivo agrava ese pendiente: pasa de teorico a probable.

## Parte 2 — Catalogo de novedades

Agrupadas por origen. La columna **Hoy** dice que existe en el codigo actual.

### A — Nacen en el mesero, sobre un pedido en curso

| # | Novedad | Por que es obligatoria | Hoy |
|---|---|---|---|
| A-1 | **Agregar platos** al pedido existente | La mas frecuente del servicio real ("otra cerveza"). Sin esto el mesero crea pedidos sueltos y la cuenta de la mesa queda partida en pedazos | No |
| A-2 | **Cambiar cantidad** | Lo que el autor pidio explicitamente | No |
| A-3 | **Quitar un plato** (sin anular el resto) | El cliente se arrepiente de un item, no de la comida entera | No |
| A-4 | **Cambiar o agregar observacion** | La mas urgente en el tiempo: "sin cebolla" a los 30 segundos se atiende, a los 5 minutos ya no | No |
| A-5 | **Anular el pedido completo** con motivo y responsable | **Ya es regla no negociable de SPEC-008.** El modelo tiene `ANULADO` y `motivo_anulacion`, pero **no hay endpoint que los use**: la regla existe escrita y no existe implementada | Modelo si, API no |
| A-6 | **Cambiar de mesa** | Los clientes se cambian de mesa. Sin esto la comida sale hacia el lugar equivocado y nadie entiende por que | No |

### B — Nacen en cocina (la via que hoy no existe)

Toda esta familia esta bloqueada por 1.4.

| # | Novedad | Por que es obligatoria | Hoy |
|---|---|---|---|
| B-7 | **Agotado / "86"** — se acabo un plato | El evento mas comun de una cocina real. Debe: avisar al mesero, **apagar solo el plato en el menu del cliente** (`Plato.disponible` ya existe, pero nadie puede cambiarlo desde el tablero) y marcar los pedidos en vuelo que lo llevan | No |
| B-8 | **Rechazo con motivo** — "no lo podemos hacer sin gluten" | Hoy la estacion solo puede decir "listo". No tiene forma de decir "esto no se puede" | No |
| B-9 | **Demora estimada** — "va a tardar 30 min" | Permite al mesero manejar la expectativa del cliente antes del reclamo, en vez de despues | No |

### C — Sobre platos ya entregados

| # | Novedad | Por que es obligatoria | Hoy |
|---|---|---|---|
| C-10 | **Devolucion** (frio, mal punto, no es lo pedido) con motivo | Necesita saber si se rehace o no, y **debe contar como merma**, no desaparecer. Es distinto de anular: aqui hubo costo real | No |
| C-11 | **Cortesia / invitacion de la casa** | Contablemente unico: el costo ocurrio, el ingreso es cero. Si se registra como anulacion, la merma se vuelve invisible | No |

### D — Coordinacion y tiempos

Esto es lo que separa un tablero de cocina de una lista de tareas.

| # | Novedad | Por que es obligatoria | Hoy |
|---|---|---|---|
| D-12 | **Cursos / tiempos** (entradas → fuertes → postres) | Sin esto todo se dispara junto y el postre sale con la sopa. Con varias estaciones es la diferencia entre que la comida llegue junta o no | No |
| D-13 | **Priorizar / apurar** un pedido | "Esta mesa lleva 40 minutos". Hoy el cronometro se pone rojo pero nadie puede intervenir el orden | No |
| D-14 | **Coordinar entre estaciones** | La hamburguesa (cocina) y el malteado (bar) deberian salir juntos. Hoy cada estacion trabaja ciega respecto de la otra | No |

### E — Seguridad. No es negociable.

| # | Novedad | Por que es obligatoria | Hoy |
|---|---|---|---|
| E-15 | **Alergias como dato estructurado**, no como texto libre | `Plato.alergenos` existe, pero describe **el plato**, no lo que el comensal no puede comer. Un "sin mani" escrito en el campo de observacion se ve igual que "sin cebolla" — y no lo es. Deberia ser un marcador imposible de pasar por alto, y **no deberia poderse marcar una comanda como lista sin reconocerlo** | Parcial, y mal ubicado |

> [!danger] Esta es la que pondria de primera
> Es la unica del catalogo donde el costo de fallar no es un cliente molesto. Ademas es
> barata: un campo estructurado en el detalle y un tratamiento visual aparte. No requiere
> el resto de la arquitectura.

### F — Integridad operativa

| # | Novedad | Por que es obligatoria | Hoy |
|---|---|---|---|
| F-16 | **Tabla de auditoria de solo insercion** | **Regla 2 de SPEC-008. No existe ningun modelo de auditoria en el backend.** Cada novedad de este catalogo tiene que caer ahi o el relato contable es ficcion | No |
| F-17 | **Bloqueo de concurrencia** en la comanda | Ya estaba pendiente en SPEC-005; editar en vivo lo vuelve probable en vez de teorico | No |
| F-18 | **Turnos / quien estaba de servicio** | El proyecto exige que toda venta tenga responsable. Con turnos se sabe ademas *quien respondia por el salon* cuando ocurrio la novedad | No |

## Parte 3 — Recomendacion

### 3.1 Un solo modelo `Novedad` como columna vertebral

No construir "editar cantidad" como funcion suelta. Construir **el registro de novedades**,
y que editar cantidad sea el primer tipo que lo usa.

Un modelo `Novedad` con: pedido, detalle afectado (opcional), tipo, datos antes, datos
despues, motivo, quien la hizo, cuando, y si la estacion ya la vio.

Por que asi:

- **Sirve a las 18 novedades del catalogo**, no solo a la que se pidio
- **Es de solo insercion por naturaleza** — cumple la Regla 2 de SPEC-008 en vez de pelearse
  con ella, y de paso resuelve F-16 sin trabajo aparte
- **El rojo del tablero sale gratis**: hay novedades sin ver → la card esta en rojo
- **La notificacion sale gratis**: crear una novedad es el evento que dispara el aviso

Hacerlo como UPDATE sobre `DetallePedido` es mas rapido esta semana y hay que deshacerlo
entero cuando llegue la contabilidad.

### 3.2 Como deberia verse el rojo

Lo que pidio el autor —"muy intuitiva mostrando el cambio"— se traduce en cinco reglas:

1. **Decir que cambio, no que algo cambio.** No "hay una novedad", sino
   `2× → 3× Hamburguesa` con lo viejo tachado y lo nuevo resaltado.
2. **Graduar por gravedad.** Agregar un item, cancelar uno que ya esta en el fuego y cambiar
   una alergia no pueden verse igual.
3. **Boton de "Visto"** que apaga el rojo. Sin el, todo termina rojo y el rojo no informa.
4. **Si la comanda ya estaba LISTA**, la novedad no puede ser un simple recoloreo: tiene que
   sacarla de la columna "Listas" y escalarla, porque el plato ya estaba en la barra.
5. **Que no se pueda perder**: sonido al entrar, y que siga marcada hasta que alguien la
   reconozca — no que desaparezca sola a los segundos.

### 3.3 Orden que propongo

| Orden | Que | Por que primero |
|---|---|---|
| 1 | **E-15 Alergias estructuradas** | Unica con riesgo de dano real. Barata e independiente |
| 2 | **Modelo `Novedad` + auditoria (F-16)** | Cimiento de todo lo demas. Y salda una regla de SPEC-008 que hoy esta escrita pero no construida |
| 3 | **Registro de pedidos del mesero (1.1)** | No existe. Sin esto no hay donde entrar a editar |
| 4 | **A-1, A-2, A-3, A-4 + rojo en el tablero** | Lo que se pidio |
| 5 | **A-5 Anular con motivo** | SPEC-008 ya lo exige y no esta |
| 6 | **B-7 Agotado / 86** | El evento mas frecuente de una cocina real |
| 7 | **A-6 cambio de mesa · C-10 devolucion** | Alta frecuencia, ya con el cimiento puesto |
| 8 | **D-12 cursos · D-13 prioridad · F-17 bloqueo** | Refinamiento operativo |

## Parte 4 — Que documentos toca

- **Nueva SPEC-011 — Novedades sobre Pedidos en Curso**
- **Nuevo ADR — Una novedad es un evento, no una modificacion** (justifica 1.2)
- **Nuevo ADR — Las alergias son dato estructurado** (justifica E-15)
- Modificar [[SPEC-004 - Modulo Mesero]] — registro de pedidos y edicion; cierra la
  pregunta abierta "puede el mesero agregar items a un pedido ya enviado?"
- Modificar [[SPEC-005 - Estaciones y Ruteo]] — novedades en el tablero, 86, rechazo
- Modificar [[SPEC-006 - Notificaciones]] — destinatario deja de ser solo un mesero
- Modificar [[SPEC-008 - Contabilidad y Auditoria]] — merma, cortesias, devoluciones
- [[Preguntas Abiertas]] — se resuelve una de las tres importantes

## Enlaces

- [[SPEC-004 - Modulo Mesero]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[SPEC-006 - Notificaciones]]
- [[SPEC-008 - Contabilidad y Auditoria]]
- [[ADR-004 - LISTO y ENTREGADO son estados distintos]]
- [[Preguntas Abiertas]]
- [[Inicio]]
