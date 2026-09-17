---
tipo: spec
id: SPEC-020
estado: implementada
actualizado: 2026-09-14
tags: [contabilidad, caja, gastos, activos]
---

# SPEC-020 — Activos Liquidos

> [!success] Estado: Implementada — verificada el 2026-09-08

## Proposito

Responder en un vistazo **cuanta plata tiene el negocio ahora mismo y donde
esta**, y dejar registrar con la misma facilidad la plata que entra y la que
sale.

## El problema que resuelve

Hoy el sistema **ya sabe** el saldo de cada caja: lo calcula sumando su libro
de movimientos ([[SPEC-014 - Turno de Caja y Cajas de Fondos]]). Pero ese
numero solo se ve **dentro del desplegable de traslados del Libro**, de a una
caja y sin sumar. No hay ninguna pantalla que diga *"hay $340.000 en efectivo,
$1.200.000 en Nequi y $8.500.000 en Bancolombia"*.

Y hay tres cosas que faltan de verdad:

1. **El efectivo nunca sale del libro.** Al cerrar el turno se cuenta el cajon
   y se guarda ese numero, pero **no se registra que la plata se retiro**. El
   saldo de Efectivo sigue creciendo dia tras dia como si nunca se hubiera
   sacado nada, asi que a la semana ya no significa nada.
2. **Los gastos son texto libre.** Se puede registrar "pague al domiciliario",
   pero nunca se podra sumar cuanto se fue en nomina el mes pasado.
3. **No hay saldo de arranque.** Cuando un restaurante empieza a usar el
   sistema, su cuenta de banco ya tiene plata. Hoy no hay donde decirlo.

## Alcance

- **Pantalla de activos liquidos**: cada caja con su saldo actual, y el total
- **Tipo de caja**: efectivo (se cuenta) o banco (se concilia)
- **Saldo de arranque** por caja, una sola vez, al empezar a usar el sistema
- **Categorias de gasto configurables** desde el panel
- **Registrar ingreso o gasto** con su categoria, desde la misma pantalla
- **Cierre diario del efectivo**: al cerrar turno, el efectivo sale del cajon y
  queda la base del dia siguiente
- **Historia del saldo**: como llego a ser lo que es (enlace al Libro filtrado)

## Fuera de alcance

- **Cuentas por pagar y por cobrar.** Esto registra plata que ya se movio, no
  compromisos futuros
- **Conciliacion automatica con el banco.** Nadie va a conectar el sistema al
  banco: la conciliacion se hace mirando el extracto al lado
- **Presupuestos.** Cuanto *deberia* gastarse es otra cosa
- **Impuestos y contabilidad formal.** Esto no reemplaza a un contador ni
  pretende cumplir norma tributaria
- **Nomina.** Un gasto de nomina se registra como cualquier otro gasto; el
  calculo de cuanto se le debe a cada quien no vive aqui

## Comportamiento

### Los dos tipos de caja

> [!important] La diferencia no es cosmetica: son dos formas distintas de cuadrar
> El **efectivo** se puede contar con la mano. Se cuadra abriendo el cajon y
> comparando con lo que dice el sistema.
>
> El **banco** —Nequi, Daviplata, Bancolombia, el datafono— no se puede contar.
> Se cuadra mirando el extracto. Y no se "reinicia" nunca: la plata se queda
> ahi hasta que alguien la mueva.

Cada caja declara su tipo. Springfield tendria: Efectivo (efectivo), y Nequi,
Daviplata y Datafono (banco).

### El saldo de arranque

Cuando el restaurante empieza a usar el sistema, sus cuentas ya tienen plata.
Se registra **una sola vez por caja**, y queda como un movimiento normal de
ingreso con concepto "saldo inicial".

> [!note] Por que un movimiento y no un campo
> [[SPEC-014 - Turno de Caja y Cajas de Fondos]] ya decidio que **el saldo es
> la suma del libro, sin excepciones**. Un campo `saldo_inicial` aparte seria
> la primera excepcion, y a partir de ahi el saldo dejaria de cuadrar con su
> propio libro. Como movimiento, todo sigue sumando igual.

Solo el administrador puede registrarlo, y solo si esa caja no tiene ya uno.

### El efectivo se reinicia cada dia; el banco no

Este es el cambio de fondo respecto a como funciona hoy.

**Al cerrar el turno**, ademas de contar el cajon como ya se hace:

1. La persona indica **cuanto deja de base** para el dia siguiente (puede ser
   cero)
2. El resto **sale del cajon**, y hay que decir a donde va:
   - **Se consigna** → traslado a una caja de banco (queda como ingreso alla)
   - **Se guarda** → egreso con concepto "retiro de cierre" (la caja fuerte, o
     el dueno se lo lleva)
3. El cajon queda en la base declarada, y el dia siguiente arranca desde ahi

Las cajas de tipo banco **no se tocan** al cerrar turno. Su saldo sigue
corriendo.

> [!danger] El descuadre no se maquilla
> Si se contaron $10.000 menos de lo que decia el sistema, ese faltante
> **no desaparece**. Se registra como su propio movimiento —concepto
> "diferencia de arqueo", con autor y motivo obligatorio— y queda en el libro
> para siempre.
>
> Es lo contrario de esconderlo: el saldo vuelve a coincidir con la realidad
> **y** queda escrito quien lo conto, cuanto falto y que dijo. Un ajuste sin
> nombre seria maquillaje; uno firmado es un registro contable.

### Los gastos, con categoria

Hoy un gasto es un monto y una descripcion escrita a mano. Se le agrega una
**categoria**, escogida de una lista que el administrador arma desde el panel.

Categorias de arranque sugeridas: Nomina, Insumos, Servicios publicos,
Arriendo, Domiciliario, Mantenimiento, Otros.

La descripcion **sigue existiendo** y sigue siendo libre: la categoria dice de
que tipo es, la descripcion dice cual fue.

> [!important] La leccion del telefono de Springfield, otra vez
> En [[SPEC-019 - Clientes]] se encontro que el personal escribia "paga nequi"
> dentro del campo del telefono, porque no habia donde anotarlo.
>
> Aqui pasa lo mismo al reves: si la categoria fuera lo unico y no hubiera
> descripcion, la gente escribiria el detalle dentro del nombre de la
> categoria, y terminarian existiendo veinte categorias llamadas
> "Insumos - pollo", "Insumos - pollo 2"…

Una categoria con gastos registrados **no se borra**: se desactiva. Igual que
las cajas.

### Ninguna caja queda en negativo

> [!danger] Corregido el 2026-09-07 — la primera version lo permitia
> El autor lo encontro probando: registro un gasto de **SUELDO por $2.000.000**
> sobre un Efectivo que tenia $1.790.800, y el saldo quedo en **−$209.200**.
> Despues traslado $210.000 desde Nequi con la descripcion "reposicion" para
> taparlo — que es, sin saberlo, el flujo correcto.

**Un saldo negativo no describe nada que exista.** No hay un cajon con menos
cero pesos, ni una cuenta de Nequi que deba plata. Cuando aparece uno, siempre
significa lo mismo: **falta registrar un movimiento**. Es mejor pedirlo en ese
momento que dejar el numero roto y que alguien lo descubra en el cuadre de fin
de mes.

Por eso, de una caja **no puede salir mas de lo que tiene**. Aplica a los
cuatro caminos por donde sale plata:

| Camino | Comprobado |
|---|---|
| Registrar un gasto | Si |
| Trasladar a otra caja | Si (solo el origen) |
| Registrar un egreso suelto | Si |
| **Anular una venta ya cobrada** | Si |

Y a ninguno de los que la meten: un ingreso, una venta o el saldo de arranque
nunca pueden dejar una caja en negativo.

#### Por que anular tambien

Anular fue el caso discutido, y merece quedar escrito porque el primer
razonamiento **estaba equivocado**.

Se argumento que bloquearlo impediria corregir una venta mal cobrada. Es falso,
y el dato que lo desmonta es este:

> **Anular una venta del mismo dia, antes de cerrar el cajon, nunca puede
> dejarlo en negativo** — la plata de esa venta todavia esta ahi. El cobro la
> metio; la anulacion saca exactamente lo mismo que entro.

El negativo solo aparece al anular una venta de **un dia anterior**, cuando el
cajon ya se vacio al cierre. Y entonces la plata de verdad se fue: para
devolversela al cliente hay que traerla de la caja fuerte, del dueno o de otra
caja. **El cajero no puede entregar $200.000 que no tiene**, tenga o no tenga
permiso el sistema.

Asi que bloquearlo no impide la correccion: **la ordena**. Primero entra la
plata, despues se devuelve — que es el orden que ocurre en la vida real. Y
obliga a registrar de donde salio esa plata, con lo que el libro queda **mas**
completo, no menos.

#### El unico caso que se penso distinto, y por que igual se bloquea

Una reversion de datafono o Nequi la hace el banco, pase lo que pase en este
sistema. Negarse a registrarla separaria el libro del extracto.

Se bloquea igual, por tres razones: una sola regla se entiende mejor que dos;
la salida toma quince segundos (registrar el ingreso, luego anular); y si el
extracto muestra plata que el libro no tiene, para eso existe el ajuste de
saldo, que ademas deja constancia del motivo.

#### El mensaje tiene que decir que hacer

Un "no se puede" a secas deja a la persona atascada en hora pico. El mensaje
distingue dos situaciones que **en pantalla se ven identicas**:

| Situacion | Que dice |
|---|---|
| La caja no tiene esa plata | «Efectivo» tiene $800 y estas sacando $2.000.000. Si de verdad hay mas plata de la que dice el sistema, ajusta el saldo antes de registrar esto. |
| La caja esta en cero porque nadie declaro su arranque | «Bancolombia» tiene $0 y estas sacando $150.000. Esta en cero porque todavia no se ha declarado con cuanto arranco. Que el administrador lo registre primero. |

Y al anular, decir el camino de salida:

> «Efectivo» tiene $50.000 y la devolucion es de $200.000. Registra primero de
> donde sale esa plata (un ingreso o un traslado) y vuelve a intentar.

> [!warning] Se comprueba con la fila bloqueada
> Leer el saldo, decidir y escribir sin bloquear la caja es exactamente el
> patron que causo el cobro duplicado
> ([[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]): dos gastos de
> 100.000 a la vez sobre una caja con 150.000 leerian los dos "alcanza",
> pasarian los dos, y la caja terminaria en −50.000.
>
> Cada comprobacion va dentro de `transaction.atomic` con
> `select_for_update()` sobre la caja, y con prueba de concurrencia con hilos.

### La pantalla

Una sola pantalla, **Activos**, con tres partes:

**Arriba — el total.** Cuanta plata hay en total, y debajo el desglose entre
efectivo y banco. Es la cifra que el dueno quiere ver al abrir.

**En medio — cada caja.** Una tarjeta por caja: nombre, tipo, saldo actual, y
cuando fue su ultimo movimiento. Tocar una lleva al Libro ya filtrado por esa
caja — de ahi salio el numero, y hay que poder comprobarlo.

**Abajo — las acciones**, las cuatro que se usan todos los dias:

| Accion | Que hace |
|---|---|
| Registrar ingreso | Plata que entra y no es una venta: un aporte del dueno, una devolucion |
| Registrar gasto | Plata que sale, con su categoria |
| Trasladar | Mover entre cajas: consignar el efectivo, pasar de Nequi al banco |
| Ajustar saldo | Solo administrador. Corrige contra el extracto, con motivo obligatorio |

### Que ve cada quien

- **Administrador**: todo, incluido el saldo de arranque y el ajuste
- **Quien puede cobrar** (cajero, y mesero si esta habilitado): ve los saldos y
  registra ingresos, gastos y traslados. No ajusta ni fija saldos de arranque
- **Los demas**: no ven esta pantalla

## Reglas

1. **El saldo sigue siendo la suma del libro.** Ningun saldo se guarda como
   campo, nunca (hereda de SPEC-014, regla 1).
2. **Toda plata que se mueve deja una fila**, incluido el saldo de arranque, el
   retiro de cierre y el ajuste (SPEC-014, regla 2).
3. **Nada se edita ni se borra.** Un error se corrige con el movimiento
   contrario (SPEC-014, regla 3).
4. **El descuadre se registra, no se disimula**: movimiento propio, autor y
   motivo obligatorio.
5. **El efectivo se retira al cerrar el turno** y queda en la base declarada.
   Las cajas de banco no se tocan.
6. **Un gasto siempre tiene categoria.** Si ninguna encaja, existe "Otros".
7. **El saldo de arranque se registra una sola vez por caja**, y solo el
   administrador.
8. **Ajustar un saldo es del administrador**, siempre con motivo.
9. Una caja o una categoria con movimientos **se desactiva, no se borra**.
10. **Ninguna caja queda en negativo.** De una caja no sale mas de lo que
    tiene, por ningun camino — gasto, traslado, egreso suelto o anulacion de
    una venta ya cobrada.
11. **Cada comprobacion de saldo va con la fila bloqueada** (ADR-008), o dos
    salidas simultaneas la dejan negativa igual.
12. **El mensaje dice que hacer**, y distingue "no hay plata" de "falta
    declarar el saldo de arranque".

## Criterios de aceptacion

Verificados el 2026-09-07 con 24 pruebas automaticas en `ventas/tests.py` y el
recorrido completo con clics.

- [x] La pantalla muestra **cada caja con su saldo actual** y el **total**
- [x] El total esta desglosado entre **efectivo** y **banco**
- [x] Tocar una caja abre el **Libro filtrado por esa caja**
- [x] Se puede registrar un **ingreso** y el saldo cambia de inmediato
- [x] Se puede registrar un **gasto con categoria** y el saldo cambia
- [x] Las **categorias de gasto se administran** desde el panel
- [x] Una categoria con gastos **no se puede borrar**, solo desactivar
- [x] El **saldo de arranque** se puede fijar una vez por caja, solo admin
- [x] Intentar fijarlo dos veces en la misma caja **falla con mensaje claro**
- [x] Al **cerrar turno**, el efectivo sale y la caja queda en la base declarada
- [x] Al cerrar turno, las cajas de **banco no cambian**
- [x] Un **descuadre** queda como movimiento propio, con autor y motivo
- [x] Cerrar turno **sin motivo** cuando hay descuadre **falla**
- [x] El **saldo siempre cuadra** con la suma de los movimientos de esa caja
- [x] Quien **no puede cobrar** no ve la pantalla ni la API
- [x] Quien puede cobrar pero **no es admin** no puede ajustar ni fijar arranque
- [x] Dos personas registrando gastos **a la vez** no descuadran el saldo
- [x] Sin desborde horizontal en **375 px**

### Que ninguna caja quede en negativo

Agregado el 2026-09-07 tras el hallazgo del autor. Los tres primeros ya estan
hechos y probados; **el de anular esta pendiente**.

- [x] Un **gasto** mayor que el saldo se rechaza, y no mueve nada
- [x] Un **traslado** mayor que el saldo se rechaza, y el destino tampoco recibe
- [x] Un **egreso suelto** mayor que el saldo se rechaza
- [x] Gastar **exactamente** el saldo si se puede — el limite es "mas", no "todo"
- [x] **Dos gastos simultaneos** no dejan la caja en negativo: uno entra, el otro se rechaza
- [x] El mensaje **distingue** "no hay plata" de "falta declarar el arranque"
- [x] La defensa esta en el **servidor**, no solo en el boton (comprobado saltandose la pantalla)
- [x] **Anular una venta ya cobrada** con saldo insuficiente se rechaza, y el
      mensaje dice que registre primero de donde sale la plata
- [x] Anular una venta **del mismo dia** sigue funcionando siempre: su propia
      plata todavia esta en la caja
- [x] **Dos anulaciones simultaneas** de la misma cuenta siguen registrando un
      solo egreso (esto ya funcionaba: no romperlo)

## Como quedo implementado

### Lo que se aprendio al probarlo

Tres cosas salieron **al ver la pantalla**, no de las pruebas. Las 24 pruebas
del servidor pasaban en las tres.

**1. El boton que iba a duplicar la plata.** «Con cuanto arranco» aparecia en
cajas que ya tenian 1.790.800 de historia. Lo que el administrador iba a
escribir ahi era el saldo que veia en pantalla — y se habria **sumado**,
dejando la caja con el doble.

Corregido en los dos lados: el servidor ahora exige que la caja este vacia y,
si no lo esta, dice que use el ajuste; la pantalla ya no ofrece el boton. Hay
prueba (`test_no_se_declara_el_arranque_de_una_caja_que_ya_tiene_movimientos`).

**2. Dos numeros distintos llamados «diferencia».** La pantalla de cierre
comparaba lo contado contra lo que movio **ese turno** ($50.000), mientras el
servidor iba a registrar el arqueo contra lo que dice el libro que hay en el
**cajon** ($1.720.800) — la base de ayer y lo de los companeros incluidos.
Habria dicho "sobran 1.670.800" y guardado "cuadra exacto".

Ahora el cuadre trae los dos numeros por separado, `esperado_efectivo` y
`esperado_en_cajon`, y la pantalla usa el que corresponde segun si se esta
cerrando tambien el cajon. Los dos hacen falta: uno responde "de la plata que
paso por mis manos, ¿cuadra?" y el otro "¿cuadra el cajon?".

**3. La categoria preseleccionada mentia.** El selector arrancaba en la
primera categoria, y al registrar un gasto escribiendo solo monto y
descripcion, quedo guardado como **nomina** un gasto de pollo. En produccion
eso convertiria el reporte de gastos en ruido. Ya no se preselecciona: hay que
elegir.

### El cambio de fondo

Hasta esta spec **el efectivo nunca salia del libro**. Al cerrar el turno se
contaba el cajon y se guardaba el numero, pero no se registraba que la plata
se hubiera retirado, asi que el saldo de Efectivo crecia dia tras dia. En la
base de desarrollo iba en 1.790.800 acumulados de 125 ventas.

Ahora, al marcar «tambien cierro el cajon del dia»: se registra la diferencia
si la hay, sale el retiro, y el cajon queda exactamente en la base declarada.
Comprobado de punta a punta: 1.720.800 -> 50.000, con el retiro de 1.670.800
escrito en el libro.

Se dejo **opcional a proposito**. Si quedan companeros con turno abierto,
vaciar el cajon les descuadraria el suyo — la pantalla lo advierte con cuantos
turnos quedan.

### Donde vive

| Que | Donde |
|---|---|
| Tipo de caja, categorias, conceptos nuevos | `backend/ventas/models.py` |
| Fijar arranque, gasto, ajuste, cierre del cajon | `backend/ventas/operaciones.py` |
| API de activos, arranque y ajuste | `backend/ventas/views.py` |
| Migraciones | `ventas/0006_*` y `ventas/0007_datos_activos_liquidos` |
| Pruebas | `backend/ventas/tests.py` (24) |
| Pantalla de activos | `frontend/src/views/mesero/MeseroActivos.vue` |
| Cierre del cajon | `frontend/src/views/mesero/MeseroCaja.vue` |
| Categoria en el libro | `frontend/src/views/mesero/MeseroLibro.vue` |
| Tipo de caja y categorias | `frontend/src/views/admin/AdminCobro.vue` |

Las categorias de gasto se siembran en la migracion de datos (Nomina, Insumos,
Servicios publicos, Arriendo, Domiciliario, Mantenimiento, Otros). Arrancan
pobladas porque una lista vacia obliga a llenarla antes de poder registrar el
primer gasto, y lo que pasa entonces es que el gasto no se registra.

## Plan de implementacion

### Paso 1 — Modelo (3 horas)

- `Caja.tipo`: `efectivo` | `banco`, con `banco` por defecto para las que ya
  existen menos Efectivo. Migracion de datos incluida
- `CategoriaGasto`: nombre, activo, orden
- `MovimientoCaja.categoria`: opcional, obligatorio solo si es gasto
- Conceptos nuevos en `MovimientoCaja`: `saldo_inicial`, `retiro_cierre`,
  `diferencia_arqueo`, `gasto`
- `Turno.base_dejada`: cuanto quedo en el cajon al cerrar

### Paso 2 — Operaciones (medio dia)

En `ventas/operaciones.py`, junto a lo que ya existe:

- `fijar_saldo_inicial(caja, monto, autor)` — falla si ya tiene uno
- `registrar_gasto(caja, monto, categoria, autor, descripcion)`
- `ajustar_saldo(caja, monto_real, autor, motivo)` — calcula la diferencia y
  registra el movimiento que haga falta
- `cerrar_turno(...)` cambia: recibe `base_dejada` y `destino_efectivo`, y
  registra el retiro y la diferencia

> [!danger] Aqui hay una carrera, y ya se pago por ella una vez
> Fijar el saldo inicial y ajustar leen el saldo, deciden, y escriben. Es
> exactamente el patron que causo el cobro duplicado de
> [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]: dos ajustes a
> la vez leerian el mismo saldo viejo y el segundo pisaria al primero.
>
> Van con `select_for_update()` sobre la `Caja` dentro de `transaction.atomic`,
> y con **prueba de concurrencia con hilos**, como las de `ventas/tests.py`.

### Paso 3 — API (3 horas)

- `GET /api/activos/` — todas las cajas con saldo, tipo, ultimo movimiento y
  los totales
- `POST /api/cajas/<id>/saldo-inicial/` — solo admin
- `POST /api/cajas/<id>/ajustar/` — solo admin
- `CategoriaGastoViewSet` — CRUD, solo admin
- `POST /api/movimientos/` acepta `categoria`

### Paso 4 — Pantallas (medio dia)

- `MeseroActivos.vue` — la pantalla nueva
- `MeseroCaja.vue` — el cierre pide base y destino del efectivo
- `AdminCategoriasGasto.vue` — o una seccion dentro de `AdminConfiguracion`

### Paso 5 — Comprobacion y documentacion (3 horas)

Pruebas primero en los pasos 1 y 2. Al final: clics reales en la pantalla
—incluido el recorrido completo de cerrar turno, que es donde
[[SPEC-019 - Clientes]] encontro un defecto que ninguna prueba vio—, 375 px,
actualizar la comparativa y bitacora.

**Total estimado: dos dias y medio.** *(Ejecutado el 2026-09-07.)*

### Paso 6 — Completado el 2026-09-08

`anular_cuenta` bloquea la cuenta y después la caja, valida el saldo dentro de
la transacción y usa un mensaje específico que indica registrar primero el
ingreso o traslado faltante. Se añadieron pruebas para venta antigua, reposición,
venta del mismo día y anulaciones concurrentes.

## Dependencias

- [[SPEC-014 - Turno de Caja y Cajas de Fondos]] — de aqui salen `Caja`,
  `MovimientoCaja` y el turno. **Esta spec lo modifica**: el cierre de turno
  cambia
- [[SPEC-008 - Contabilidad y Auditoria]] — el criterio de que nada se reescribe
- [[SPEC-007 - Administracion y Parametrizacion]] — donde viven las categorias
- [[ADR-007 - Una novedad es un evento, no una modificacion]] — el mismo criterio de
  no reescribir, aplicado a los pedidos
- [[ADR-008 - Bloquear la fila antes de decidir sobre dinero]] — la carrera del
  paso 2

## Preguntas abiertas

- [x] **¿La base que queda en el cajon es fija o se escribe cada dia?**
      **Resuelta en la implementacion (anotado 2026-09-14):** se escribe en cada
      cierre y arranca en 0. No quedo como parametro; si en Springfield la base
      es casi siempre la misma, volverla parametro es el paso siguiente.
- [x] **¿Un descuadre grande deberia impedir cerrar el turno?** **Resuelta:** no
      lo impide nunca. En vez de un monto a partir del cual pedir explicacion,
      **cualquier** diferencia exige motivo.
- [ ] **¿El "Resumen operativo" de Springfield se arma sobre esto?** Le falta
      poco: ventas por medio de pago ya existe, gastos por categoria saldria de
      aqui. *(2026-09-14: sigue sin construirse. SPEC-021 termino siendo la
      navegacion, asi que el resumen queda como pantalla aparte, pendiente.)*
