---
tipo: spec
id: SPEC-011
estado: implementada
actualizado: 2026-09-14
tags: [mesero, cocina, novedades, edicion, auditoria]
---

# SPEC-011 — Novedades sobre Pedidos Enviados

> [!success] Estado: Implementada — revisada y corregida 2026-09-14
> Resuelve la pregunta abierta *"puede el mesero modificar un pedido ya enviado?"*
> Nace del estudio [[Novedades sobre Pedidos en Curso]] y de un hueco real detectado en
> [[SPEC-012 - Vista de Salon y Estado de Mesas]].

## Proposito

Que el mesero pueda corregir un pedido que ya esta en cocina, y que la estacion se entere
de que cambio — sin que nadie tenga que ir a avisar de viva voz.

## El problema que lo origina

Con SPEC-012, liberar una mesa **no toca el pedido**: la mesa queda libre y el pedido sigue
su vida. Correcto, pero deja un cabo suelto real:

> El pedido #7 se envio a cocina desde la Mesa 1. El mesero libera la Mesa 1. La tarjeta de
> cocina **sigue diciendo "Mesa 1"**, donde ahora hay comensales distintos. Cuando el plato
> salga, alguien lo lleva al lugar equivocado.

Y un bug detectado al revisar esto: **un domicilio llega a cocina sin destino**. El
serializador arma la mesa con `source="pedido.mesa.nombre"`, y sin mesa el campo desaparece
del JSON — la tarjeta queda con el titulo en blanco.

**Causa comun:** el destino de un pedido no existe como dato. Cocina lo deduce caminando
hasta la mesa en el momento de pintar.

## Alcance

- **Registro de pedidos activos** del mesero (hoy no existe: no hay `GET /api/pedidos/`)
- **Cambiar el destino**: de una mesa a otra, de mesa a domicilio, de domicilio a mesa
- **Editar los platos** de un pedido enviado: agregar, quitar, cambiar cantidad, cambiar
  observacion
- **Modelo `Novedad`** de solo insercion, columna vertebral de todo lo anterior
- **Aviso a la estacion**: tarjeta en rojo con el cambio explicito, y boton "Visto"
- **Atajo al liberar** una mesa que tiene un pedido en curso

## Fuera de alcance

- **Anular el pedido completo** — operacion distinta, exige motivo obligatorio. Es el
  siguiente usuario del mismo cimiento, no parte de esta spec
- **Agotado / "86"** y rechazo desde cocina — van en sentido contrario (cocina → mesero) y
  exigen cambiar el destinatario de `Notificacion`, que hoy solo sabe apuntar a un mesero
- **Devoluciones y cortesias** — pedido ya entregado; tocan contabilidad
- **Cursos y tiempos** (entradas → fuertes → postres)
- **Alergias como dato estructurado** — merece ADR propio, ver [[Novedades sobre Pedidos en Curso]]
- **Editar un pedido ya ENTREGADO o ANULADO**
- La **merma** que genera quitar un plato ya cocinado: se registra, pero valorarla es
  [[SPEC-008 - Contabilidad y Auditoria]]

## Comportamiento

### El destino es un dato, no una consulta

`Pedido` expone un **destino** que siempre es texto: `"Mesa 5"`, `"Domicilio"` o
`"Sin mesa"`. La estacion nunca vuelve a caminar hasta la mesa para averiguarlo.

Esto por si solo arregla el domicilio en blanco.

### Cambiar el destino

Una sola operacion cubre los dos casos, porque son el mismo: cambiar **a donde va**.

1. El mesero abre el pedido (desde la mesa en el salon, o desde su registro de pedidos)
2. Elige el nuevo destino: otra mesa, o domicilio
3. El sistema:
   - actualiza el destino
   - **guarda una `Novedad`** con lo de antes, lo de ahora, quien y cuando
   - **ocupa la mesa nueva** — mismo criterio de SPEC-012: si hay un pedido ahi, hay gente
   - marca las comandas del pedido con **novedad sin ver**

> [!note] La mesa vieja no se libera sola
> Seria el sistema adivinando que la gente se esfumo. Se **ofrece** liberarla en la misma
> pantalla, a un toque — coherente con la regla de oro de SPEC-012.

### Editar los platos

Sobre un pedido no entregado, el mesero puede:

| Accion | Detalle |
|---|---|
| **Agregar un plato** | Congela el precio **del momento en que se agrega**, no el del pedido original. Si cae en otra estacion, se crea la comanda que falte |
| **Quitar un plato** | El renglon sale del pedido. Si la comanda ya estaba lista, ver la regla de merma abajo |
| **Cambiar la cantidad** | No re-cotiza: el precio congelado del renglon no se toca |
| **Cambiar la observacion** | La mas urgente en el tiempo: "sin cebolla" a los 30 segundos se atiende, a los cinco minutos ya no |

Cada una genera su propia `Novedad`.

### Como se entera la estacion

Mientras el pedido tenga **novedades sin ver**, su tarjeta va **en rojo** y muestra **que
cambio**, no que algo cambio:

```
~~Mesa 1~~  ->  MESA 2
2x Hamburguesa  ->  3x Hamburguesa
+ 1x Limonada
- 1x Postre de la casa
AHORA SIN CEBOLLA
```

Un boton **"Visto"** apaga el rojo.

> [!important] Una alerta que nadie puede cerrar se vuelve papel tapiz
> Sin el boton "Visto", a las dos horas de servicio media pantalla esta en rojo y el rojo
> deja de significar nada. Poder apagarlo es parte del mecanismo, no un adorno.

### El caso grave: la comanda ya estaba LISTA

El plato esta en la barra con una etiqueta equivocada, y alguien esta a punto de llevarlo.

Ahi **no basta con recolorear**: la comanda **sale de la columna "Listas"** y vuelve a
"En preparacion" con la novedad marcada. Es el unico caso donde una novedad mueve una
comanda de columna.

### Atajarlo antes de que pase

Al liberar una mesa que tiene un pedido en curso, el salon **no lo deja huerfano en
silencio**. El endpoint ya devuelve `pedidos_en_curso`; la interfaz lo usa para ofrecer,
ahi mismo:

- **Se queda donde esta** — alguien lo recoge
- **Pasalo a domicilio**
- **Muevelo a otra mesa**

Es mas barato preguntar en el momento que hacer que el mesero busque despues un pedido sin
mesa. Y no traba nada: "se queda" es un toque.

## Reglas

### 1. Una novedad es un hecho que se agrega, nunca una correccion del hecho anterior

> [!danger] Esta regla sostiene toda la contabilidad
> La tabla `Novedad` es de **solo insercion**: nunca se actualiza ni se borra. Registra
> quien, que cambio, de que a que, cuando.
>
> Es la **Regla 2 de [[SPEC-008 - Contabilidad y Auditoria]]**, que hoy no tiene ni tabla.
> Esta spec empieza a pagarla.

`DetallePedido` **si** refleja el estado actual — lo que finalmente se sirvio, que es lo que
constituye la venta. La historia de como llego ahi vive en `Novedad`. Las dos cosas juntas
permiten reconstruir cualquier momento sin que los reportes se reescriban solos.

### 2. El precio congelado no se re-cotiza

Cambiar la cantidad de un renglon **no toca su precio congelado** (Regla 1 de SPEC-008).
Un plato **agregado despues** congela el precio vigente al agregarlo — si el menu cambio en
el intermedio, es correcto que cueste lo de ahora.

### 3. Quitar un plato ya cocinado no lo descocina

Si la comanda estaba **lista** o **en preparacion**, el sistema avisa y **deja constancia en
la `Novedad`**. No finge que el plato nunca existio. Valorar esa merma es trabajo de
SPEC-008; aqui solo se garantiza que el dato queda.

### 4. Un pedido no se vacia editando

Quitar el ultimo renglon **no** deja un pedido vacio: eso es una anulacion, y la anulacion
exige motivo y responsable. El sistema lo impide y remite a anular — que esta fuera del
alcance de esta spec.

### 5. Ventana de edicion

| Estado del pedido | Editable |
|---|---|
| Pendiente · En preparacion · Listo | **Si** |
| Entregado · Anulado | **No** — eso es devolucion, otro camino |

### 6. La edicion siempre se acepta

Coherente con SPEC-012: el mesero manda. Si la comanda cambio de estado mientras el mesero
editaba, **la edicion entra igual** y la novedad se marca con mas urgencia. El sistema
avisa; no bloquea.

### 7. Cualquier mesero

Sin dueno, igual que el salon.

## Criterios de aceptacion

- [x] Un domicilio muestra **"Domicilio"** en la tarjeta de cocina, nunca un titulo vacio
- [x] Marcar **lista** una comanda de domicilio avisa al mesero — **corregido
      2026-09-14**. La accion `lista` armaba el aviso con `pedido.mesa.nombre`; en un
      domicilio la mesa es nula, la peticion respondia 500 y el mesero nunca se enteraba.
      Ahora usa `pedido.destino`, igual que la tarjeta
- [x] El mesero puede listar sus pedidos activos, **incluidos los que quedaron sin mesa**
- [x] Mover un pedido de Mesa 1 a Mesa 2 cambia lo que ve cocina, y **la Mesa 2 queda ocupada**
- [x] La Mesa 1 **no** se libera sola al mover el pedido
- [x] Pasar un pedido de mesa a domicilio hace que cocina muestre "Domicilio"
- [x] Cada cambio deja una fila en `Novedad` con autor, antes, despues y fecha
- [x] La tarjeta de cocina se pinta en **rojo** con novedades sin ver, y muestra el **cambio
      concreto**, no un aviso generico
- [x] **"Visto"** apaga el rojo, y no reaparece por esa misma novedad
- [x] Una comanda **ya lista** que recibe una novedad **sale de la columna "Listas"**
- [x] Agregar un plato de otra categoria **crea la comanda de esa estacion**
- [x] Un plato agregado despues congela el **precio del momento de agregarlo**
- [x] Cambiar la cantidad **no altera** el precio congelado del renglon
- [x] Quitar el **ultimo** renglon se rechaza y remite a anular
- [x] Un pedido **entregado** no se puede editar
- [x] Liberar una mesa con pedido en curso **ofrece las tres opciones** y no lo deja huerfano
- [x] Nada de esto se puede hacer sin sesion, y solo con rol mesero o admin
- [x] Sin desborde horizontal en 375 px

> [!note] Revisado 2026-09-14
> Hasta esta fecha las apps `pedidos` y `estaciones` no tenian ni una prueba, y estos
> criterios estaban construidos pero sin marcar. Se comprobaron con
> `backend/pedidos/tests.py`, que nombra en cada prueba la linea del criterio que
> verifica. La del aviso de domicilio destapo un fallo, corregido el mismo dia. El de 375 px sale de
> [[SPEC-022 - Auditoria Responsive]].

## Dependencias

- [[SPEC-004 - Modulo Mesero]] — el registro de pedidos vive ahi
- [[SPEC-005 - Estaciones y Ruteo]] — el tablero que se pinta en rojo, y el re-ruteo
- [[SPEC-012 - Vista de Salon y Estado de Mesas]] — de donde se llega al pedido
- [[SPEC-008 - Contabilidad y Auditoria]] — la regla de auditoria que esto empieza a pagar
- [[Novedades sobre Pedidos en Curso]] — el estudio del que sale

## Preguntas abiertas

- **Anular con motivo** es el siguiente usuario natural del modelo `Novedad`. Conviene
  hacerlo enseguida: SPEC-008 ya lo exige y hoy `ANULADO` existe en el modelo sin ningun
  endpoint que lo use
- Cuando exista tiempo real (Channels), la novedad deberia **llegar sola** a la estacion en
  vez de esperar al siguiente sondeo
- Umbral de urgencia: una novedad sobre una comanda en preparacion, cuanto tiempo puede
  quedar sin ver antes de escalar sola?
