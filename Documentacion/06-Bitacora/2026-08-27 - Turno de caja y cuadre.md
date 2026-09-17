---
tipo: bitacora
fecha: 2026-08-27
tags: [bitacora, caja, turno, cajero, cuadre, spec-014]
---

# 2026-08-27 — Turno de caja y cuadre

Implementación de [[SPEC-014 - Turno de Caja y Cajas de Fondos]]. Con esto el sistema ya
responde la pregunta por la que un restaurante compra un POS: **cuánto debería haber en el
cajón, y cuánto hay.**

## De dónde salió el modelo

Investigación de solo lectura sobre el sistema real de Springfield. Dos hallazgos que
corrigieron suposiciones mías:

**"Caja" no es una caja registradora.** Es una bolsa de dinero por medio de pago —
EFECTIVO, NEQUI, DAVIPLATA, BANCOLOMBIA, DATAFONO… De hecho la sección "Medios de pago" de
su panel abre la misma pantalla que las cajas de fondos. Así que **una sola entidad**, no
dos: al cobrar se elige, y ahí se acumula.

**El rol cajero existe, y el mesero allá NO puede cobrar.** Extraje la matriz completa de
permisos del panel (59 botones con su lista `visible`). Seis roles: `administrador`,
`jefe`, `cajero`, `mesero`, `cocina`, `desarrollador`. El cajero hace lo del mesero más
caja y carta; el mesero solo toma pedidos.

> [!note] Dato para el borrador de la presentación
> La **regresión lineal de productos** y los tiempos promedio están marcados
> `visible: ['desarrollador']`. No es una función que el restaurante use: está oculta. No
> sirve como argumento de "ellos ya lo tienen".

## Lo que decidió el autor

**Mixto y configurable.** Parámetro `meseros-pueden-cobrar`: encendido, el mesero cierra la
cuenta él mismo; apagado, solo el cajero y el admin. Springfield lo apagará.

**Arranca encendido**, porque si arrancara apagado un restaurante recién instalado no
podría cobrar hasta crear un cajero — una trampa.

**La caja acumula sin importar quién cobró.** Un mesero que cobra en Nequi mete la plata en
la misma caja que el cajero.

**Cobrar nunca se bloquea.** Sin turno abierto se cobra igual y la venta queda **marcada
fuera de turno**, visible en ámbar. Bloquear por un olvido administrativo detendría el
servicio, contra la regla de oro de [[SPEC-012 - Vista de Salon y Estado de Mesas]].

**Fiar queda descartado** (decisión previa): toda cuenta cerrada está cobrada de verdad.

## Decisiones de ingeniería

**El saldo se deriva, no se guarda.** `Caja.saldo()` es la suma de sus movimientos; no hay
campo `saldo`. Un número que se va incrementando puede desincronizarse, y cuando pasa **no
hay forma de saber dónde se rompió**. De paso, el traslado entre cajas sale gratis: son dos
movimientos y los dos saldos quedan bien solos.

**El fondo inicial no es un campo del turno**, es un movimiento de ingreso a Efectivo. Así
el saldo sigue siendo la suma del libro sin excepciones. Lo que sí se guarda es el
**efectivo contado**: nadie puede derivar eso, alguien lo contó a mano.

**Anular una cuenta cobrada genera el movimiento contrario**, nunca borra el original.

**El cuadre no se maquilla:** la diferencia se guarda como salga.

**Un turno abierto por persona, garantizado por la base** (`UniqueConstraint` con
condición), igual que la cuenta única por mesa.

**El permiso vive en el servidor.** `PuedeCobrar` consulta el parámetro en cada petición.
Esconder el botón no es un permiso: verificado que con el parámetro apagado la API
devuelve 403 al mesero.

## La migración, a mano

`makemigrations` pregunta de forma interactiva si `MedioPago` se renombró a `Caja`, y
**`--no-input` responde que NO**: generaría un `DeleteModel` + `CreateModel` que borraría
la tabla con sus datos. Se escribió `0002` a mano con un `RenameModel` explícito, que
conserva filas y llaves foráneas. Verificado después con `makemigrations --check`: sin
diferencias pendientes.

## Verificado

Prueba automatizada contra la API real, **todo en verde**:

- El rol **cajero** existe, entra y accede al turno; cocina recibe 403
- Con el parámetro en **sí** el mesero cobra; en **no** recibe **403 desde la API**; el
  cajero cobra en ambos casos
- Lo cobrado por cajero **y** admin entra a la misma caja
- **Saldo == suma de sus movimientos**, comprobado sumando el libro aparte
- Anular una cuenta cobrada **baja el saldo** y deja el original intacto más uno de anulación
- Traslado: baja el origen, sube el destino; a la misma caja se rechaza
- Las ventas previas quedaron **marcadas fuera de turno**
- Abrir turno registra el fondo como movimiento; **no deja abrir un segundo**
- Venta en efectivo suma al cuadre; un gasto lo baja
- Cerrar sin contar el efectivo se rechaza
- **Diferencia guardada tal cual** (−3.000) y el esperado sin maquillar
- No se cierra dos veces; el historial es solo del admin; las cajas no se borran (405);
  los movimientos tampoco

En navegador, como cajero: navegación correcta (**sin Cocina ni Admin**), abre turno con
$100.000, la venta lo sube a $130.800, el gasto lo baja a $115.800, y al escribir 112.800
avisa **"Faltan $3.000"** antes de cerrar. Tras cerrar: Esperado $115.800 · Contado
$112.800 · Diferencia −$3.000.

### Dos falsas alarmas

1. **"Desborde horizontal"** — el panel del navegador estaba colapsado y
   `clientWidth` valía **0**, así que todo elemento parecía desbordarse. Medido con ancho
   real de 375 px: **sin desborde**.
2. **La prueba falló al reintentarla** por el pedido duplicado. Causa real:
   `django.core.signing` marca el tiempo **en segundos**, así que dos pedidos idénticos en
   la misma mesa dentro del mismo segundo producen el mismo texto firmado y el
   anti-duplicado rechaza el segundo. **Es el comportamiento correcto** — en uso real no
   ocurre, en una prueba automática todo el tiempo. Se varió el payload.

> [!warning] No verificado por Claude
> El **aspecto** de la pantalla de caja. El panel no compone frames.

## Sin resolver

- **La "Caja 1" del sistema actual.** Su reporte de turnos tiene una columna `Caja` con
  valor `1` que **no corresponde** a las cajas de fondos (IDs 6, 10, 11, 22…). Probablemente
  una registradora física, concepto aparte. La prueba de abrir/cerrar turno **se aplazó**:
  el turno 214 estaba abierto en horario de servicio con $98.000 de fondo real, y tocarlo
  habría descuadrado una caja de verdad
- Pantalla de cajas y traslados en el panel de admin (hoy solo por API)
- **Reportes de venta** — lo siguiente, y ya solo depende de esto

## Enlaces

- [[SPEC-014 - Turno de Caja y Cajas de Fondos]]
- [[SPEC-013 - La Cuenta]]
- [[Inventario del Sistema Actual de Springfield]]
- [[Que le Falta para ser un POS Vendible]]
- [[Inicio]]
