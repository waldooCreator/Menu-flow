---
fecha: 2026-09-03
tipo: bitacora
specs: [SPEC-003, SPEC-006, SPEC-014]
---

# 2026-09-03 — Notificaciones, tercer nivel de observaciones y turno por usuario

Tres reportes de prueba end-to-end. El tercero cambió de forma dos veces
durante la conversación — quedó anotado abajo por qué.

## 1. Notificaciones "no salen"

Reproduje el flujo exacto reportado — crear pedido como mesero, pasar por
cocina (en preparación → listo), volver a mesero, tocar la campana — dos
veces: primero por API, después clic por clic en la pantalla real, con
capturas en cada paso. **Funcionó las dos veces.**

No pude reproducir el fallo. La sospecha más razonable: **Docker estaba
caído** al momento de esa prueba — tuvo que reiniciarse en esta misma
conversación antes de poder investigar nada — y es probable que el backend
ya estuviera respondiendo mal o nada cuando se probó.

Sí apareció un bug real de paso: un pedido **anulado** mostraba el botón
"Finalizar pedido" en la campana, cuando solo debía desaparecer al entregar
o al anular. Corregido en
[NotificacionesBurbuja.vue](../../frontend/src/components/NotificacionesBurbuja.vue).

## 2. Observaciones "nada funciona"

Mismo resultado: probé crear, borrar, generales y por plato, con capturas —
**todo funcionaba** en el momento de probarlo. Mismo diagnóstico de fondo
(servidor caído en el momento del reporte anterior).

Lo que sí faltaba de verdad — y se construyó — es el nivel intermedio: **por
categoría**. "Término medio" para toda la sección Del Asador, "sin hielo"
para toda Bebidas, sin tener que repetirlo plato por plato ni ensancharlo a
"general".

### El bug que apareció al construirlo

Al agregar el campo `categoria` al modelo, **crear una observación general
dejó de funcionar** — sin haberla tocado. La causa: DRF arma automáticamente
un validador de unicidad a partir del `UniqueConstraint` del modelo, y ese
validador exige que el campo mencionado en la restricción esté **presente**
en el envío, aunque sea vacío. El formulario del panel nunca manda la clave
`categoria` al crear una general — no hay razón para que la mande — así que
el validador la rechazaba con "este campo es requerido", un mensaje que no
tiene nada que ver con el problema real.

La corrección: declarar `default=None` explícito en el serializador para
`categoria` y `plato`. Con eso, omitir la clave equivale a mandarla vacía, que
es exactamente lo que "general" significa.

> [!note] Por qué no se notó antes
> El cliente del panel para el nivel *por plato* siempre mandaba `plato`
> explícito (aunque fuera `null`), así que nunca pisó este error. Solo se
> hizo visible al agregar un segundo campo (`categoria`) que el cliente NO
> manda por costumbre.

### Comprobado

Con capturas en cada paso: una etiqueta de categoría creada desde el panel
aparece en los platos de esa sección y **no** en los de otra; una etiqueta de
plato se suma a las de su categoría y a las generales, sin duplicar texto
repetido; el filtro `?categoria=` trae solo lo suyo.

## 3. Turno "no debe ser por usuario"

Este pasó por tres versiones del mismo pedido, y vale la pena dejar
constancia de cómo se afinó:

1. Primera lectura mía: "al abrir un turno, preguntar a qué usuario se le
   abre" — la entendí como una casilla más en el formulario.
2. Corrección del autor: *"no, lo que quiero decir es que funciona de esta
   manera: abrir turno de caja, luego caja debe abrir los turnos de los
   meseros y sus cuentas."* — no era una casilla suelta: la pantalla de
   Caja entera deja de ser "mi turno" y pasa a ser el lugar donde se abren y
   se ven los turnos **de todos los meseros**.

### Lo que cambió

- **Abrir turno exige elegir a quién** — de una lista de meseros y cajeros
  activos, nunca de cocina ni de alguien inactivo. Ya no se asume que es
  quien tiene la sesión iniciada.
- La pantalla muestra el turno propio de quien mira (si tiene uno) **y**
  la lista de los demás turnos abiertos, cada uno como "Turno de Bryam
  #12" — nunca solo el número.
- **Quien puede cerrar el turno de otro** dejó de ser "solo administrador"
  y pasó a ser "cualquiera que pueda cobrar" (cajero o administrador): si
  caja abre los turnos de los meseros, tiene sentido que también pueda
  cerrarlos, sin depender de que un administrador esté disponible. El
  motivo obligatorio es lo que deja el rastro — restringir el rol no
  aportaba nada que el motivo no cubriera ya.

Esto **revirtió** una regla que se había escrito hacía apenas unas horas
([[ADR-008 - Bloquear la fila antes de decidir sobre dinero]] no la toca,
pero el bloqueo de "solo admin cierra el ajeno" sí cambió). No fue un
error esa vez — era lo que se sabía entonces. Es lo que pasa cuando una
aclaración llega después: se corrige, se prueba de nuevo, y se sigue.

### Comprobado

Con clics reales en la pantalla: abrí un turno a nombre de un mesero de
prueba (`bryam_demo`) desde la sesión de administrador — apareció en
"Otros turnos abiertos", nunca como si fuera mío. Lo cerré desde ahí: sin
motivo lo rechazó, con motivo lo cerró y quedó registrado `cerrado_por:
admin`. El selector de candidatos no ofrece usuarios de cocina ni
inactivos — probado también por API.

20 tests en `ventas/tests.py`, todos en verde — 7 de concurrencia, 13 de
turno (7 de la ronda anterior + 6 nuevas de esta).

## Lo que deja como aprendizaje

Los dos primeros reportes eran, con altísima probabilidad, el servidor
caído — no un defecto de código. Vale la pena, antes de reportar "nada
funciona", confirmar que `docker ps` y los dos `npm run dev` /
`manage.py runserver` siguen vivos.

El tercero enseña algo distinto: cuando una corrección de alcance llega
después de empezar a construir, no hay que defender lo ya escrito — se
relee la spec, se ajusta, y se prueba otra vez. La primera versión de
"elegir usuario al abrir" era razonable con lo que se sabía en ese momento;
dejó de serlo en cuanto se explicó cómo funciona caja de verdad.
