---
tipo: spec
id: SPEC-019
estado: implementada
actualizado: 2026-09-14
tags: [clientes, domicilios, privacidad]
---

# SPEC-019 — Clientes

> [!success] Estado: Implementada — verificada el 2026-09-07

## Proposito

Guardar a quien le vendemos, para no volver a pedirle los mismos datos cada
vez que pide un domicilio y para poder saber quienes son los clientes
frecuentes.

## El problema que resuelve

Hoy el sistema **no guarda clientes**. De un domicilio solo queda
`nombre_cliente` escrito en el pedido, y la direccion ni siquiera llega al
servidor: vive en el navegador del propio cliente y viaja dentro del mensaje de
WhatsApp.

Eso funciona para entregar el pedido, pero significa que:

- Un cliente que pide todas las semanas escribe su direccion todas las semanas
- No se puede saber quien compra mas, ni cuanto
- El reporte "Clientes frecuentes" (SPEC-018) no se puede construir

## La leccion de Springfield

> [!important] Esto define un requisito, no es una anecdota
> Al revisar su directorio de clientes se encontro que el personal escribia
> `pago nequi`, `paga efectivo` y `25k trasnferencia y` **dentro del campo del
> numero de telefono**.
>
> No era descuido: **necesitaban anotar algo y no habia donde**. Cuando un
> sistema no ofrece un lugar para lo que la gente necesita registrar, la gente
> lo improvisa en el campo que tenga a mano, y ese campo deja de significar lo
> que dice.

**Por eso el campo de observaciones va desde el primer dia**, no como mejora
posterior. Es la unica forma de que el telefono siga siendo un telefono.

## Alcance

- **Ficha de cliente**: nombre, telefono, direccion, correo y observaciones
- **Varias direcciones** por cliente (casa, oficina)
- **Buscar** por nombre o telefono, desde la pantalla de domicilios
- **Historial**: sus compras, cuanto lleva gastado y cuando fue la ultima
- **Reporte de clientes frecuentes** (cierra el 5º reporte de SPEC-018)
- El cliente se **crea o se reconoce solo** al tomar un domicilio, sin un paso
  administrativo aparte

## Fuera de alcance

- **Cuentas de cliente con contrasena.** El cliente nunca inicia sesion
  (ADR-002) y eso no cambia
- **Programa de puntos.** Springfield tiene una columna "Puntos" en cero para
  todos: existe y no se usa
- **Marketing automatico** (correos, promociones dirigidas)
- Fiar / credito: descartado por el autor

## Comportamiento

### El cliente se crea solo, no se administra

Cuando llega un domicilio con nombre y telefono, el sistema **busca por
telefono**. Si existe, lo reconoce y le suma el pedido. Si no, lo crea.

Nadie tiene que "dar de alta" un cliente antes de venderle. Un paso
administrativo previo es lo primero que se deja de hacer en un viernes lleno,
y entonces el directorio queda a medias y no sirve para nada.

### El telefono identifica

Es lo unico que la gente da siempre y no cambia. El nombre se escribe distinto
cada vez ("Cristian", "cristian r", "Cris"), y el correo casi nadie lo da.

Un telefono repetido **no crea un cliente nuevo**: actualiza el que existe.

### Varias direcciones

Un cliente puede tener casa y oficina. Al pedir, elige entre las que ya tiene o
escribe una nueva, que queda guardada para la proxima.

### Las observaciones

Campo libre en la ficha, visible al tomar el pedido. Es donde va "paga con
efectivo, no tiene cambio de 50", "timbre danado, llamar al llegar", "alergico
al mani".

### Lo que el cliente puede pedir

> [!danger] Requisito legal, no opcional
> La Ley 1581 de 2012 le da al titular derecho a **conocer, actualizar,
> rectificar y suprimir** sus datos. La ficha debe permitir **corregir** y
> **eliminar** un cliente a peticion suya.

Eliminar un cliente **no borra sus ventas**: las cuentas quedan, se les quita
el vinculo y conservan el nombre congelado que ya tenian. El historial contable
no se reescribe (SPEC-008), pero el dato personal si desaparece.

### Lo que NO se guarda

Nada que no haga falta para entregar un pedido. Sin documento de identidad, sin
fecha de nacimiento, sin genero. Cada campo que se agrega es un dato que hay que
proteger y justificar.

## Reglas

1. **El telefono identifica al cliente.** Repetido, actualiza; no duplica.
2. **El cliente se crea solo** al tomar el domicilio, sin paso previo.
3. **Las observaciones existen desde el primer dia**, para que el telefono siga
   siendo un telefono.
4. **Eliminar un cliente no borra sus ventas**, solo el dato personal.
5. **El cliente nunca inicia sesion** (ADR-002).
6. Solo se guarda lo necesario para entregar un pedido.

## Criterios de aceptacion

Verificados el 2026-09-07 con pruebas automaticas (18 en `clientes/tests.py`)
y clics reales en el navegador.

- [x] Un domicilio con telefono nuevo **crea** el cliente
- [x] El mismo telefono otra vez **reconoce** al existente, no duplica
- [x] El nombre escrito distinto **no crea** un cliente nuevo si el telefono coincide
- [x] Las **observaciones** se ven al tomar el pedido
- [x] La ficha muestra sus compras, el total gastado y la ultima visita
- [x] Se puede **corregir** cualquier dato del cliente
- [x] Se puede **eliminar** un cliente, y sus ventas **siguen existiendo**
- [x] Una venta de un cliente eliminado **conserva su nombre congelado**
- [x] El reporte de **clientes frecuentes** ordena por cantidad de compras
- [x] Buscar por nombre o por telefono encuentra al cliente
- [x] Sin desborde horizontal en 375 px

### Lo que quedo pendiente

Dos criterios **no** se cumplieron al cerrar esta spec. El segundo lo cerro despues
[[SPEC-021 - Navegacion del Personal]]; el primero sigue abierto a proposito:

- [ ] **Un cliente puede tener varias direcciones y elegir entre ellas.**
      Guardar varias funciona: el modelo las admite y la ficha permite
      agregarlas y quitarlas. **Elegir** entre ellas al pedir, no: el cliente
      escribe la direccion en el carrito, y ahi el sistema todavia no sabe
      quien es — el telefono llega en el mismo formulario. Para ofrecerle sus
      direcciones guardadas habria que consultarlas apenas escriba el telefono,
      y eso expone datos de un cliente a quien teclee su numero. Se deja fuera
      a proposito hasta decidir como resolver eso sin abrir esa puerta.

- [x] **Quien no puede cobrar no ve la pantalla de clientes.** *(Cerrado por SPEC-021 el
      2026-09-08: `lib/navegacion.js` esconde el destino a quien no puede cobrar.)*
      El servidor **si** lo impide: `PuedeCobrar` en la API devuelve 403, y hay
      prueba (`test_quien_NO_puede_cobrar_no_ve_los_clientes`). Lo que falta es
      la interfaz: el enlace "Clientes" se le sigue mostrando al mesero aunque
      tenga el cobro apagado, y al entrar ve un error en vez de no ver el
      enlace. Es el mismo comportamiento que Caja, Libro y Ventas — la brecha
      es de toda esa familia, no de esta spec, y se arregla de una vez en
      `MarcoInterno.vue`.

      > [!note] Ya tiene dueño: [[SPEC-021 - Navegacion del Personal]]
      > Esa spec rehace la navegacion del personal y **cierra este criterio**.
      > Al implementarla hay que volver aqui y marcarlo.

## Como quedo implementado

### Lo que cambio respecto a lo planeado

**Se elimino el campo de correo.** Estaba en el alcance original. Springfield
lo tiene y casi nadie lo da; un dato personal que no se usa es solo una
obligacion de custodia. La ficha guarda nombre, telefono, direcciones y
observaciones.

**El telefono y la direccion viajan dentro del QR firmado.** Era la unica forma
de capturarlos sin darle trabajo al mesero: el cliente los escribe una vez en
el carrito, el navegador se los guarda, y viajan firmados hasta el servidor.
Ocupan unos 166 de los ~1800 caracteres disponibles. Ver
[[SPEC-002 - QR de Pedido]].

**La comparacion de direcciones normaliza pero NO reordena palabras.**
Minusculas, sin tildes, sin puntuacion y sin espacios de sobra: asi
`Barrio XXX` y `barrio xxx` se reconocen solas. Ordenar las palabras haria
coincidir tambien `barrio xxx` con `xxx barrio` — que es el caso que planteo
el autor — pero al mismo precio haria coincidir `calle 5 casa 20` con
`calle 20 casa 5`, que son dos casas distintas. **Equivocarse ahi es mandar la
comida a otra direccion.** Ante la duda se guardan las dos y decide la persona:
duplicar una direccion es ruido menor, entregar en la casa equivocada no.

**Lo que enlaza a los dos pedidos del ejemplo es el telefono, no el texto.**
`maria angelica` en el pedido 1 y `angelica lopez` en el 2 quedan como un solo
cliente porque el numero coincide. Gana el nombre mas reciente, y se corrige
en un toque desde la ficha.

### Donde vive

| Que | Donde |
|---|---|
| Modelos y normalizacion | `backend/clientes/models.py` |
| Reconocer o crear, resumen y frecuentes | `backend/clientes/operaciones.py` |
| API (CRUD + direcciones + frecuentes) | `backend/clientes/views.py` |
| Pruebas | `backend/clientes/tests.py` (18) |
| Telefono y direccion en el QR | `backend/pedidos/firma.py` |
| Aviso de cliente conocido al confirmar | `frontend/src/views/mesero/MeseroEscaner.vue` |
| Directorio | `frontend/src/views/mesero/MeseroClientes.vue` |
| Reporte de frecuentes | `frontend/src/views/mesero/MeseroReportes.vue` |
| Captura del telefono | `frontend/src/components/CarritoPanel.vue` |

### Un defecto que salio al probar

La pantalla de recibir pedido pedia elegir mesa para **cualquier** QR sin mesa,
y dejaba el boton de enviar deshabilitado hasta elegirla. Un domicilio no tiene
mesa, asi que **no se podia confirmar un domicilio desde la pantalla**. El
servidor ya lo hacia bien; la interfaz no. Corregido: si es domicilio muestra
nombre, telefono y direccion, y no pide mesa.

Vale la pena anotarlo porque no lo encontro ninguna prueba: las del servidor
pasaban todas. Lo encontro intentar hacer el recorrido completo con clics.

## Plan de implementacion

### Paso 1 — Modelo (2 horas)

`Cliente` con nombre, telefono (unico), correo, observaciones y fechas.
`DireccionCliente` con etiqueta, direccion e indicaciones, ligada al cliente.

En `Cuenta`, un vinculo opcional al cliente — **opcional a proposito**: una
venta de mesa no tiene cliente, y forzar uno obligaria a inventar datos.

`on_delete=SET_NULL` en ese vinculo: **es lo que permite borrar un cliente sin
borrar sus ventas**, que es el requisito legal.

Migracion.

### Paso 2 — Reconocer o crear al tomar el domicilio (3 horas)

Al confirmar un pedido de domicilio con telefono, buscar por telefono y crear
si no existe, dentro de la misma transaccion.

> [!danger] Aqui hay una carrera
> Dos domicilios del mismo telefono confirmados a la vez crearian dos clientes.
> Es el mismo patron de [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]].
> Se resuelve con el `unique` del telefono mas capturar el choque y releer.

**Tests primero:** el duplicado por telefono, la carrera, y que borrar el
cliente deje las ventas intactas.

### Paso 3 — Pantalla de clientes (medio dia)

Lista con buscador por nombre o telefono, y ficha con sus datos, sus
direcciones, sus observaciones y su historial de compras.

### Paso 4 — Clientes frecuentes (2 horas)

El 5º reporte de SPEC-018, con el mismo patron de los otros cuatro.

### Paso 5 — Comprobacion y documentacion (3 horas)

Clics reales, actualizacion de SPEC-018 y bitacora.

**Total estimado: dos dias.**

## Dependencias

- [[SPEC-002 - QR de Pedido]] — de ahi vienen nombre y direccion del domicilio
- [[SPEC-013 - La Cuenta]] — la venta que se le atribuye
- [[SPEC-018 - Reportes de Venta]] — el reporte que esto desbloquea
- [[ADR-002 - El mesero confirma el pedido]] — el cliente no se autentica
- [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]] — la carrera del paso 2

## Preguntas resueltas

**¿La direccion sigue viviendo solo en el navegador del cliente, o pasa a
guardarse en el servidor?**

Pasa a guardarse. El autor lo decidio asi el 2026-09-07: *"si, deseo que la
direccion de los clientes se guarde en bd junto con su nombre"*.

A cambio, el carrito se lo dice de frente antes de enviar: se guarda su nombre,
telefono y direccion, y puede pedir que se borren cuando quiera — que es
exactamente lo que hace el boton Eliminar de la ficha.

**¿Como se enlazan dos pedidos que escriben el nombre distinto?**

Por el telefono. Respondida arriba, en "Como quedo implementado".
