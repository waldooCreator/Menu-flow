---
tipo: spec
id: SPEC-014
estado: implementada
actualizado: 2026-09-16
tags: [caja, turno, cajero, cuadre, ventas]
---

# SPEC-014 — Turno de Caja y Cajas de Fondos

> [!success] Estado: Implementada — revisada 2026-09-14
> Depende de [[SPEC-013 - La Cuenta]]. Se acopla al sistema que se va a reemplazar
> (ver [[Inventario del Sistema Actual de Springfield]]), pero **configurable**, no calcado.

## Proposito

Saber cuanto dinero deberia haber, donde, y quien responde por el. Es lo que convierte
"cuentas cobradas" en un cuadre de caja.

## Los tres conceptos

| | Que es |
|---|---|
| **Caja** | Una bolsa de dinero: EFECTIVO, NEQUI, DAVIPLATA, BANCOLOMBIA… Es **lo mismo** que un medio de pago, visto en dos momentos: al cobrar se elige, y ahi se acumula |
| **Movimiento** | Todo lo que entra o sale de una caja: una venta, el fondo inicial, un gasto, un traslado |
| **Turno** | El periodo de trabajo de una persona, con cuanto efectivo abrio y cuanto conto al cerrar |

## Alcance

- **Rol `cajero`**: hace lo del mesero, mas cobrar, turno y movimientos de caja
- **Quien puede cobrar es configurable**: el mesero cobra si el parametro lo permite
- **Cajas** administrables desde el panel, con **saldo acumulado**
- **Libro de movimientos**: venta, fondo inicial, ingreso, gasto, traslado
- **Traslado entre cajas** (consignar el efectivo en el banco)
- **Abrir y cerrar turno** con fondo inicial, efectivo contado y observaciones
- **El cuadre**: esperado contra contado, y la diferencia
- **Ventas fuera de turno**, visibles

## Fuera de alcance

- **Caja fisica / registradora.** El sistema actual tiene una columna `Caja` en el reporte
  de turnos con valor fijo `1`. **Resuelto (2026-08-30):** se inspecciono el formulario de
  apertura de turno sin enviarlo — pide un fondo inicial por cada caja de fondos
  (`fondos[24]` EFECTIVO, `fondos[6]` BANCOLOMBIA… los mismos IDs de `listar_cajas_fondos`)
  y **no existe ningun selector de caja registradora**. Confirmado: es un campo fijo de su
  base de datos, sin interfaz para crear una segunda. No bloquea nada de esta spec — se
  descarta del alcance por completo, no queda pendiente
- **Reportes de venta** (por dia, por mesero, mas vendidos) — la spec siguiente
- Arqueos parciales a mitad de turno
- Multiples turnos simultaneos de la misma persona

## Comportamiento

### Quien puede cobrar

Parametro **`meseros-pueden-cobrar`** (sí / no).

> [!note] Donde se configura (revisado 2026-09-16, pedido del autor)
> El autor pregunto *"si deseo que solo caja pueda cobrar, o que los meseros y caja puedan
> cobrar, ¿como configuro eso?"*. El parametro existia, pero estaba en el grupo
> **Contacto**, se escribia a mano ("si"/"no") y su nombre no decia que el cajero cobra de
> todos modos. Desde esta revision:
>
> - Vive en un grupo propio, **Configuracion → Cobro**, junto con la propina y el impuesto,
>   que tambien estaban en Contacto.
> - Se elige con un **selector Si / No**, no se escribe.
> - Se llama **"Los meseros tambien pueden cobrar"**, y la ayuda dice que pasa en cada caso:
>   *Si: cobran caja, administrador y meseros. No: solo caja y administrador.*
> - El valor guardado se conserva: quien lo tenia en "si" sigue en Si.

| Rol | Puede cerrar una cuenta |
|---|---|
| Administrador | Siempre |
| Cajero | Siempre |
| Mesero | **Solo si el parametro esta encendido** |
| Cocina | Nunca |

**Arranca encendido.** Si arrancara apagado, un restaurante recien instalado no podria
cobrar hasta crear un cajero — una trampa. Springfield lo apaga, porque alli el mesero solo
toma pedidos.

> [!important] La comprobacion va en el servidor
> Esconder el boton no es un permiso. Si la regla vive solo en la interfaz, cualquiera con
> el enlace cobra igual.

### El saldo de una caja se DERIVA, no se guarda

**Saldo = suma de sus movimientos.** No hay un campo `saldo` que se vaya sumando.

> [!important] Por que
> Un numero guardado que se incrementa puede desincronizarse, y cuando pasa **no hay forma
> de saber donde se rompio**: queda un saldo que no corresponde a nada. Derivandolo del
> libro, el saldo siempre cuadra con sus movimientos por construccion.
>
> Es la misma logica de [[ADR-007 - Una novedad es un evento, no una modificacion]]: hechos
> que se agregan, no valores que se sobrescriben.

De paso, el **traslado sale gratis**: consignar el efectivo en el banco son dos movimientos
—egreso de EFECTIVO, ingreso de BANCOLOMBIA— y los dos saldos quedan bien solos.

### Cerrar una cuenta mueve plata

Al cobrar, la cuenta genera **un movimiento de ingreso** a la caja de su medio de pago, por
el total cobrado.

**Sin importar quien la cerro.** Si un mesero cobra $50.000 en Nequi, esos $50.000 entran a
la caja NEQUI igual que si los hubiera cobrado el cajero.

Anular una cuenta ya cerrada genera el **movimiento contrario**, nunca borra el original
(SPEC-008: nada se borra).

### Abrir y cerrar turno

**Abrir:** a nombre de quien se abre, el fondo inicial y una observacion. El fondo
inicial es un movimiento de ingreso, no un campo suelto.

**Cerrar:** se cuenta el efectivo real del cajon y se registra, con observacion de cierre.

#### El turno se abre A NOMBRE de un mesero elegido, no de quien tiene la sesion
(revisado 2026-09-03)

> [!important] Decision del autor (2026-09-03)
> "Caja" abre y ve los turnos **de los meseros**, no un turno propio por
> defecto. Al abrir un turno, la pantalla pide elegir **a quien** se le abre,
> de la lista de meseros y cajeros activos — nunca se asume que es quien esta
> frente a la pantalla.

Antes `abrir_turno` tomaba automaticamente a quien tuviera la sesion iniciada.
Eso asume que cada mesero abre el suyo desde su propio usuario, cuando en la
practica es comun que sea la persona de caja quien administra la apertura de
varios meseros a la vez.

La pantalla de Caja ahora muestra, ademas del turno propio de quien mira (si
tiene uno), la lista de **todos los turnos abiertos de los demas** — "Turno de
Bryam #12", nunca solo "Turno #12" — con la opcion de cerrar cualquiera.

**Quien puede cerrar el turno de otro:** cualquiera que pueda cobrar (cajero o
administrador), no solo el administrador. El motivo obligatorio (mas abajo) es
lo que deja el rastro; restringir a un solo rol no aportaba nada que el motivo
no cubriera ya, y hubiera obligado a esperar a un administrador para una
operacion que caja hace todo el dia.

#### El fondo inicial es POR CAJA (revisado 2026-09-03)

Antes solo se aceptaba fondo en EFECTIVO. Al revisar el sistema que se va a
reemplazar, su formulario de apertura pide fondo para **cada** medio de pago —
los ocho que maneja Springfield.

Tiene sentido: si el datafono arranca el dia con un saldo del cierre anterior, o
Nequi trae plata de ayer, ignorarlo hace que el cuadre arranque torcido y la
diferencia no signifique nada.

Ahora se abre con **un fondo por caja**, todos opcionales. Cada uno genera su
propio movimiento de ingreso a su caja. Un fondo en cero no genera movimiento:
una fila de cero pesos solo ensucia el libro.

#### Cerrar el turno de otra persona (2026-09-03)

Cualquiera con permiso de cobro (cajero o administrador), y queda registrado
quien lo cerro.

> [!warning] El caso que lo obliga
> En el sistema real hay turnos abiertos desde hace semanas — uno del 7 de
> agosto seguia abierto el 3 de septiembre. Nadie los cerro y el sistema no
> avisa.
>
> Con la regla 4 (un turno abierto por persona), esa persona **queda trabada**:
> no puede abrir el turno de hoy hasta que se cierre el viejo. Sin una forma de
> cerrarlo desde afuera, la unica salida seria entrar a la base de datos.

Un turno cerrado por otro guarda **quien lo cerro** y una observacion
obligatoria: es una intervencion administrativa, no una operacion normal, y
tiene que verse como tal.

#### Aviso de turnos viejos

La pantalla avisa cuando hay turnos abiertos de **dias anteriores**. Avisa, no
bloquea — la regla de oro de [[SPEC-012 - Vista de Salon y Estado de Mesas]]
tambien vale aqui.

### El cuadre

```
Esperado = fondo inicial + ventas en efectivo + otros ingresos − gastos ± traslados
Contado  = lo que la persona contó en el cajón
Diferencia = Contado − Esperado
```

La diferencia es el numero que el dueño quiere ver: **sobra o falta**. Se guarda; no se
"corrige" el esperado para que dé cero.

El cierre muestra ademas **lo vendido por cada caja** (cuanto entró por Nequi, por
datáfono…), que es lo que no se cuenta a mano pero si se compara contra el banco.

### El libro se puede LEER, no solo escribir (2026-09-03)

Hasta hoy se podia registrar un movimiento pero **no habia forma de ver la
lista**: la pantalla de Caja los pedia al servidor solo para contar las ventas
fuera de turno, y nunca los mostraba. Un libro que no se puede leer no es un
libro.

La pantalla **Libro de caja** muestra todo lo que entro y salio, agrupado por
dia, con:

- **Filtros** por rango de fechas, caja y tipo (entro / salio)
- **Totales del rango COMPLETO**, no de las filas que caben en pantalla. Si los
  totales dependieran de cuanto se alcanza a mostrar, conciliar contra el banco
  daria un numero distinto cada vez — peor que no tenerlos
- El **traslado entre cajas** desde la misma pantalla: es la operacion legitima
  para mover plata sin reescribir nada

Un traslado **no cambia el neto** del libro: la plata cambia de bolsa, no entra
ni sale del negocio. Los saldos de las dos cajas si cambian.

**Quien lo ve:** cualquiera que pueda cobrar. Consignar el efectivo es tarea de
caja del dia a dia; exigir un administrador para registrarlo llevaria a que se
haga sin registrar, que es peor. Los dos movimientos guardan su autor, asi que
quien lo hizo siempre se sabe.

### El historial de turnos es del administrador, no del cajero (2026-09-03)

Pantalla aparte, en el panel de administracion: la lista de turnos pasados con
su cuadre y su diferencia, y un filtro para ver **solo los que no cuadraron**.

> [!note] Copiado del sistema que se va a reemplazar
> "Reporte de turnos" es la **unica** seccion de Cajeros que su rol `cajero` no
> ve — solo jefe y administrador. La razon es buena y se copia: quien maneja la
> plata no audita su propio cuadre.

### Cobrar NUNCA se bloquea

> [!important] Decision del autor (2026-08-27)
> **Si no hay turno abierto, se cobra igual.** La venta queda **sin turno** y aparece
> marcada como "fuera de turno" en el reporte.
>
> Bloquear el cobro por un olvido administrativo detendria el servicio, contra la regla de
> oro de [[SPEC-012 - Vista de Salon y Estado de Mesas]]. Se pierde algo de rigor contable
> y se gana que el restaurante nunca se pare. La omision **se ve**, en vez de perderse en
> silencio.

## Reglas

1. **El medio de pago siempre es obligatorio** al cobrar (ya venia de SPEC-013).
2. **Toda plata que se mueve deja un movimiento.** No hay forma de cambiar un saldo sin
   dejar rastro.
3. **Los movimientos no se editan ni se borran.** Un error se corrige con el movimiento
   contrario.
4. **Un turno abierto por persona.** Abrir uno nuevo sin cerrar el anterior no se permite.
   Se abre A NOMBRE de quien se elige, no de quien tiene la sesion. Cualquiera con permiso
   de cobro puede cerrar el de otro, con motivo, y queda registrado quien lo hizo.
5. **Una caja con movimientos no se borra**, se desactiva.
6. **El cuadre no se maquilla**: la diferencia se guarda como salió.
7. Cocina no toca nada de esto.

## Criterios de aceptacion

- [x] Existe el rol **cajero** y puede cobrar sin importar el parametro
- [x] Con `meseros-pueden-cobrar` **encendido**, el mesero cierra una cuenta
- [x] Con el parametro **apagado**, el mesero recibe 403 al intentarlo — **desde la API**,
      no solo con el boton escondido
- [x] Cocina nunca puede cobrar
- [x] Cerrar una cuenta **suma su total a la caja** del medio de pago elegido
- [x] Lo cobrado por un **mesero** entra a la caja igual que lo de un cajero
- [x] El saldo de una caja es **exactamente** la suma de sus movimientos
- [x] Un **traslado** deja dos movimientos y ambos saldos correctos
- [x] Anular una cuenta cerrada genera el **movimiento contrario**, sin borrar el original
- [x] Abrir turno registra el **fondo inicial como movimiento**
- [x] Se puede abrir con **fondo en varias cajas**, y cada uno genera su movimiento
- [x] Un fondo en **cero no genera movimiento**
- [x] Abrir turno **exige elegir a quien** se le abre, de la lista de mesero/cajero activos
- [x] No se puede abrir un turno a nombre de cocina ni de un usuario inactivo
- [x] Quien puede cobrar (cajero o administrador) puede cerrar el turno de otra persona, con motivo
- [x] Quien NO puede cobrar (p.ej. cocina) no puede cerrar el turno de nadie
- [x] Un turno cerrado por otro registra **quien lo cerro**
- [x] La pantalla muestra los turnos abiertos **de los demas**, no solo el propio
- [x] La pantalla **avisa** de turnos abiertos de dias anteriores, sin bloquear
- [x] El cajero **no** ve el historial de turnos; el administrador si
- [x] El libro **se puede leer**: lista de movimientos con fecha, caja, monto y autor
- [x] Los **totales son del rango filtrado completo**, no de las filas mostradas
- [x] Filtra por rango de fechas, por caja y por tipo
- [x] Un **traslado no cambia el neto** del libro, pero si los dos saldos
- [x] Quien no puede cobrar **no ve** el libro
- [x] El historial de turnos marca **cuales no cuadraron**
- [x] No se puede abrir un segundo turno sin cerrar el anterior
- [x] Al cerrar, el **esperado** se calcula con la formula de arriba
- [x] La **diferencia** entre contado y esperado se guarda tal cual
- [x] **Sin turno abierto se cobra igual**, y esa venta queda marcada fuera de turno
- [x] Las cajas se crean y desactivan **desde el panel**
- [x] Una caja con movimientos **no se puede borrar**
- [x] Sin desborde horizontal en 375 px
- [x] **(2026-09-16)** "Los meseros tambien pueden cobrar" esta en **Configuracion → Cobro**,
      con propina e impuesto, y se elige con un selector Si / No. La ayuda de cada parametro
      se ve ahora debajo de su nombre
- [x] **(2026-09-16)** Pasar a No desde ese selector hace que el mesero reciba 403 al cobrar,
      y volver a Si lo habilita, sin reiniciar nada — `nucleo/tests.py`
- [x] **(2026-09-16)** Un restaurante que ya tenia "si" o "no" escrito conserva su valor —
      la migracion `configuracion/0007` se prueba con "no", "No ", "false", "si", "Sí" y vacio

> [!note] Revisado 2026-09-14
> Los 33 estaban construidos pero sin marcar. Tienen prueba en `backend/ventas` (turno de
> caja, libro de caja, cobro concurrente, activos liquidos, cobro desde el panel) y en
> `nucleo` (perfil del personal); la caja con movimientos esta protegida en la base con
> `PROTECT`. El de 375 px sale de [[SPEC-022 - Auditoria Responsive]].

## Dependencias

- [[SPEC-013 - La Cuenta]] — lo que se cobra
- [[SPEC-007 - Administracion y Parametrizacion]] — el parametro y las cajas
- [[SPEC-008 - Contabilidad y Auditoria]] — nada se borra
- [[Inventario del Sistema Actual de Springfield]] — de donde sale el modelo

## Preguntas abiertas

- Reportes por turno (que se vendio en el turno) — spec siguiente
