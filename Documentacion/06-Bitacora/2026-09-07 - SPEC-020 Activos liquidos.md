---
tipo: bitacora
fecha: 2026-09-07
tags: [contabilidad, caja, gastos, activos]
---

# 2026-09-07 — SPEC-020: Activos liquidos

## Que se hizo

Una pantalla que dice cuanta plata tiene el negocio y donde esta, categorias
para los gastos, saldo de arranque por caja, y —lo que mas cambia— el cierre
diario del efectivo.

## El hallazgo que justificaba la spec

Al investigar salio esto: **el efectivo nunca salia del libro**. Al cerrar el
turno se contaba el cajon y se guardaba el numero, pero no se registraba que la
plata se hubiera retirado. El saldo de Efectivo crecia dia tras dia como si
nadie hubiera sacado nada.

En la base de desarrollo iba en **$1.790.800** acumulados de 125 ventas. Ese
numero no significaba nada: nadie tiene millon y medio en un cajon.

Ahora, al cerrar: se registra la diferencia si la hay, sale el retiro, y el
cajon queda en la base declarada. Comprobado con clics: 1.720.800 → 50.000, con
el retiro escrito en el libro.

## Tres cosas que solo salieron al ver la pantalla

Las 24 pruebas del servidor pasaban en las tres. Vale la pena anotarlo porque
es el mismo patron que en [[SPEC-019 - Clientes]] y ya van dos seguidas.

### 1. Un boton que iba a duplicar la plata

«Con cuanto arranco» aparecia en cajas que ya tenian 1.790.800 de historia. Lo
que el administrador iba a escribir ahi era el saldo que veia en pantalla — y
se habria **sumado**, dejando la caja con el doble.

Corregido en los dos lados: el servidor exige que la caja este vacia y remite
al ajuste si no lo esta; la pantalla ya no ofrece el boton.

### 2. Dos numeros distintos llamados «diferencia»

La pantalla de cierre comparaba lo contado contra lo que movio **ese turno**
($50.000). El servidor iba a registrar el arqueo contra lo que dice el libro
que hay en el **cajon** ($1.720.800), base de ayer y ventas de los companeros
incluidas.

La pantalla habria dicho *"sobran 1.670.800"* y el libro habria guardado
*"cuadra exacto"*.

> [!important] Los dos numeros hacen falta, no sobra ninguno
> `esperado_efectivo` responde "de la plata que paso por mis manos, ¿cuadra?".
> `esperado_en_cajon` responde "¿cuadra el cajon?".
>
> Son preguntas distintas. El error no fue tener dos, fue mostrar uno y
> guardar el otro.

### 3. La categoria preseleccionada mentia

El selector arrancaba en la primera categoria de la lista. Al registrar un
gasto escribiendo solo monto y descripcion, quedo guardado como **nomina** un
gasto de pollo.

En produccion eso convertiria en ruido el unico reporte que este modulo existe
para hacer posible. Ya no se preselecciona: hay que elegir.

## Decisiones del autor

Tres preguntas, tres respuestas que definieron la forma del modulo:

| Pregunta | Respuesta |
|---|---|
| ¿El saldo se reinicia? | El efectivo si, cada dia. El banco no |
| ¿Los gastos llevan categoria? | Si, configurables desde el panel |
| ¿Efectivo y banco son distintos? | Si: uno se cuenta, el otro se concilia |

## Lo que se decidio en la spec y conviene recordar

**El descuadre se registra, no se disimula.** SPEC-014 decia "el cuadre no se
maquilla para que de cero". Aqui se afino: el faltante **si** entra al libro,
pero como movimiento propio con autor y motivo obligatorio. Un ajuste anonimo
seria maquillaje; uno firmado es un registro contable — y ademas deja el saldo
coincidiendo con la realidad.

**Cerrar el cajon es opcional.** Si quedan companeros vendiendo, vaciarlo les
descuadraria el turno. La pantalla lo advierte diciendo cuantos turnos quedan
abiertos.

## Estado

- 24 pruebas nuevas; **110 en total, todas pasando**
- SPEC-020 → implementada
- De las **7 secciones «Contable» de Springfield, 6 estan hechas**
- La comparativa quedo revisada en esa seccion (el resto sigue siendo del 30
  de agosto)

Los datos que se crearon para probar se borraron: la base quedo como estaba.

## Siguiente

**Domicilios**, lo unico que falta de Contable. Ya se sabe quien entrego,
cuando, a quien y donde. **Falta el costo del envio**, que hoy no existe en
ninguna parte: un domicilio se cobra igual que una mesa. Trae preguntas de
negocio que solo puede responder el autor — tarifa fija o por zona, si el
domiciliario cobra parte, si el envio paga propina e impuesto.
