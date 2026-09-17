---
tipo: spec
id: SPEC-002
estado: implementada
actualizado: 2026-09-14
tags: [qr, pedido, cliente, mesero]
---

# SPEC-002 — QR de Pedido

> [!success] Estado: Implementada — revisada 2026-09-14
> Es la pieza central del sistema. Funciona de punta a punta; quedan abiertos las
> observaciones por indice y el Plan B para pedidos que no caben en el QR.

## Proposito

Permitir que el cliente arme su pedido en su propio telefono y se lo transmita al mesero
escaneando un QR, sin que nadie tenga que volver a digitarlo.

## Alcance

- Generacion del QR en el navegador del cliente
- Firma del contenido para impedir falsificacion
- Lectura y verificacion por parte del mesero
- Control de QR duplicados y vencidos

## Fuera de alcance

- Envio del pedido directo a la estacion sin pasar por el mesero
  (ver [[ADR-002 - El mesero confirma el pedido]])
- Pagos dentro del QR

## Comportamiento

1. El cliente arma su carrito en el navegador.
2. Al pulsar "Generar QR", el navegador envia el carrito a un endpoint de firma.
   **Ese endpoint no escribe en base de datos.** Valida que los platos existan y esten
   disponibles, arma el payload compacto, lo firma y devuelve el texto.
3. El navegador **dibuja el QR localmente**. Nunca se genera ni se almacena una imagen en
   el servidor.
4. El mesero escanea. La app verifica la firma, resuelve los IDs contra el menu vigente y
   **muestra el pedido en pantalla para confirmar**.
5. Al confirmar, se crea el pedido en la base de datos y se rutea a las estaciones.

## Formato del payload

Contenido: version del formato, id corto del QR, marca de tiempo, mesa, nombre opcional del
cliente, y la lista de items como `[id, cantidad, observacion]`.

En los domicilios se agregan **`t`** (telefono) y **`a`** (direccion) — solo ahi, y solo
desde [[SPEC-019 - Clientes]]. Un pedido de mesa no los lleva.

```json
{"v":1,"j":"a7f3k2","ts":1755720000,"m":"x7f2q9","c":"Walter",
 "i":[[12,2,"sin cebolla"],[45,1],[7,3,"termino medio"]]}
```

Se pasa a base64url y se le anexa la firma:

```
https://dominio.com/m#P1Z.eJyrVkrLz1eyUlAqLknMS...k3Rf9xQ2
```

> [!info] Sobre comprimir el payload (probado 2026-08-24)
> La prueba tecnica (ver mas abajo) midio tamanos reales **sin comprimir**, y ya cumplen el
> limite comodo para pedidos normales. Comprimir anadiria una dependencia (una libreria de
> deflate) por una ganancia que no hace falta en el caso comun. **No se comprime**, salvo
> que una medicion futura demuestre que si hace falta.

## Reglas

- **Solo IDs y cantidades.** Nunca nombres ni precios: el menu en base de datos es la unica
  fuente de verdad. Asi el QR no puede mentir sobre el precio.
- **El payload viaja en el fragmento (`#`)**, que nunca se envia al servidor: el pedido no
  queda en logs de acceso. Y al ser una URL, cualquier camara la abre en la app del mesero.
- **Firma HMAC obligatoria.** No es por dinero (no hay pagos), sino para impedir que alguien
  fabrique un QR con texto arbitrario que termine pintado en la pantalla de una estacion.
  El secreto vive solo en el servidor.
- **Anti-duplicado:** el id corto `j` se guarda en la fila del pedido al confirmarlo. Si se
  vuelve a escanear el mismo QR, la app avisa que ya fue usado y en que pedido. No requiere
  tabla extra.
- **Vencimiento:** se rechazan QR con mas de N horas (configurable, por defecto 6).

## Limite de tamano

> [!success] Medido, no estimado (2026-08-24)
> La tabla original de esta seccion era una **estimacion** y resulto optimista para
> observaciones en texto libre. Se reemplazo por numeros **medidos de verdad**: payload
> real construido, firmado, convertido a QR y decodificado con una libreria de escaneo real
> (jsQR). Metodologia y script completo en [[Viabilidad Tecnica del QR]].

| Carrito | Bytes reales | Version QR | ¿Cabe en 900b? |
|---|---|---|---|
| 3 items, sin observaciones | 148 | 8 | Si |
| 8 items, observaciones cortas | 263 | 12 | Si |
| 15 items, observaciones cortas | 357 | 14 | Si |
| 30 items, observaciones **largas en texto libre** | **1.767** | 35 (muy denso) | **No — dispara Plan B** |
| 50 items, observaciones largas | 5.541 | — | **No cabe en ningun QR** |

Un QR es comodo de escanear hasta ~900 bytes. Eso cubre sin problema los pedidos normales
(hasta ~15-20 items con observaciones cortas), pero **un pedido grande con observaciones en
texto libre generoso dispara el Plan B mucho antes de los 30 items** que se pensaba.

> [!tip] Recomendacion que salio de la prueba: observaciones por indice, no por texto
> Codificar las **observaciones rapidas** ([[SPEC-003 - Menu del Cliente]]) como indices a
> la lista `ObservacionRapida` en vez de como texto completo reduce el carrito de 30 items
> de **1.767 a 547 bytes — 69% menos**, y el QR pasa de version 35 (impractico) a version 18
> (comodo). El campo libre corto de la ficha del plato si va como texto, pero debe
> mantenerse corto: es el que de verdad pesa.

**Plan B:** si el payload supera ~900 bytes, el servidor guarda el carrito en una tabla
temporal con borrado automatico a las 6 horas y el QR lleva solo un token. Con observaciones
por indice, esto queda reservado para pedidos genuinamente grandes (30+ items); con texto
libre extenso, puede activarse desde los ~20 items.

> [!warning] Divergencia pendiente: observaciones van como texto, no como indice
> La implementacion real (2026-08-24) codifica la observacion tal cual la escribe/elige el
> cliente, concatenada como texto — **no** como indice a `ObservacionRapida`, que era la
> recomendacion medida arriba. Para el pedido de prueba (3 items) no importo, pero en
> pedidos grandes vuelve a exponer el riesgo de disparar el Plan B antes de tiempo.
> Pendiente: cambiar `carritoStore.aItemsParaFirmar()` en el frontend para mandar indices.

## Implementacion (2026-08-24)

Codigo real, no prototipo. `backend/pedidos/`:

- **`firma.py`** — usa `django.core.signing.dumps`/`loads` (con `salt="pedidos.qr"` y
  `max_age`) en vez del HMAC manual del script de prueba. Misma garantia de seguridad
  (firma con `SECRET_KEY`, que vive solo en el servidor), con expiracion y compresion ya
  resueltas por el framework — menos codigo propio que mantener
- **`POST /api/pedidos/firmar/`** (publico) — construye y firma. No escribe en base de datos
- **`POST /api/pedidos/verificar/`** (publico) — el mesero lo llama al escanear/subir el QR;
  resuelve platos contra el menu actual, avisa si ya fue usado o si algo esta agotado
- **`POST /api/pedidos/confirmar/`** (requiere sesion — ADR-002) — aqui y solo aqui se crea
  `Pedido` + `DetallePedido`, con precio y nombre **congelados** (regla de
  [[SPEC-008 - Contabilidad y Auditoria]])
- **Anti-duplicado:** `codigo_qr` en `Pedido` es un hash del texto firmado (no un campo
  aleatorio en el payload) — mismo QR, mismo hash, `unique=True` lo bloquea

**Frontend (`frontend/`):** `stores/carrito.js` (Pinia, en memoria — nunca persiste hasta
confirmar), `components/CarritoPanel.vue` (arma el carrito y genera el QR con la libreria
`qrcode`), `views/mesero/MeseroEscaner.vue` (decodifica con `jsQR` desde una imagen subida,
muestra el pedido resuelto, confirma).

> [!note] Alcance de lo probado
> El escaneo se probo por **imagen subida**, no por camara en vivo — es lo que se puede
> verificar sin un telefono fisico. El escaneo por camara (`qr-scanner`, ADR-005) es un
> tramo aparte, no construido todavia.

## Criterios de aceptacion

- [x] Un pedido de 20 items genera un QR que se escanea en menos de 2 segundos —
      **verificado: pedidos tipicos (hasta 15 items) firman, generan el QR y decodifican
      en menos de 150ms de punta a punta; el caso de 30 items con texto libre extenso
      llega a ~525ms**
- [x] Un QR con la firma alterada es rechazado — **verificado**
- [x] Un QR ya usado avisa en que pedido se consumio — **verificado 2026-08-24**: reusar
      el mismo QR devuelve 409 y `verificar` marca `ya_usado: true` antes de confirmar
- [x] Un QR de mas de 6 horas es rechazado — implementado con
      `django.core.signing` (`max_age`), mecanismo estandar y ya probado por el framework;
      no se forzo el reloj para verlo fallar en vivo
- [x] El pedido no existe en base de datos hasta que el mesero confirma — **verificado**:
      `firmar` y `verificar` no escriben nada; solo `confirmar` (con sesion) crea filas
- [x] No se almacena ninguna imagen de QR en el servidor — **por diseño, la prueba tecnica
      la genera en el mismo proceso que la firma, igual que hara el navegador**
- [x] Si un plato del QR ya no existe o esta agotado, la app lo senala antes de confirmar —
      **verificado**: `verificar` devuelve `disponible` por item y el mesero lo ve marcado
      antes de confirmar (no bloquea la confirmacion, solo avisa — sin definir aun si
      deberia bloquear)
- [x] Un pedido que supera el limite de tamano cae al plan B sin error visible —
      **verificado: el carrito de 50 items excede la capacidad del QR de forma
      predecible y detectable antes de generar la imagen** (el Plan B en si — tabla
      temporal + token — no esta implementado todavia, solo la deteccion)
- [ ] Las observaciones rapidas se codifican por indice, no por texto completo — **sigue
      sin cumplirse (revisado 2026-09-14)**: el QR lleva el texto; ver la divergencia
      anotada arriba

## Dependencias

- [[SPEC-001 - QR de Mesa]] — aporta la mesa al payload
- [[SPEC-004 - Modulo Mesero]] — quien lo escanea y confirma
- [[ADR-001 - QR autocontenido y firmado]]
- [[ADR-005 - Escaneo con libreria JS]]

## Pedido a distancia — domicilio (revisado 2026-08-26)

El cliente elige entre dos botones al generar el QR: **"Estoy en el lugar"** (el flujo de
siempre: el mesero escanea) o **"A distancia"** (domicilio / para llevar).

### El domicilio NO tiene mesa

> [!warning] Cambio respecto a la version del 2026-08-25
> La primera version anclaba el domicilio en una **mesa virtual** (`codigo="domicilio"`),
> porque `Pedido.mesa` era obligatorio. Eso ya no aplica: con
> [[SPEC-012 - Vista de Salon y Estado de Mesas]] esa mesa falsa aparaceria en el salon y
> alguien tendria que "liberarla".
>
> Ahora **`Pedido.mesa` admite vacio** y el pedido lleva su propia marca de domicilio. Asi
> el domicilio no ocupa ninguna mesa **por construccion**, no por un filtro que alguien
> pueda olvidar.

> [!note] Desde 2026-08-30 el domicilio SI aparece en el salon
> Pero en **su propia zona**, no entre las mesas — una lista sin tope, con las acciones
> Cobrar y Marcar entregado. Ver [[SPEC-012 - Vista de Salon y Estado de Mesas]].
> Sigue sin ocupar ninguna mesa fisica: son dos secciones distintas de la misma pantalla.

### Flujo completo

1. El cliente arma el carrito y toca **"A distancia"**
2. Aparece un **formulario**: **nombre de quien recibe**, **telefono** y **direccion
   exacta**. Los tres obligatorios — sin ellos no hay domicilio posible. El telefono se
   pide desde SPEC-019: es lo que permite reconocer al cliente la proxima vez
3. Esos datos se guardan en el **navegador del cliente** (cache local): la proxima vez el
   formulario ya viene lleno
4. Se genera el **QR**, con un boton de **descargar el QR como imagen**
5. El boton de WhatsApp abre el chat del restaurante con el mensaje **ya armado desde una
   plantilla**, con los datos del formulario dentro
6. El cliente **adjunta la imagen del QR a mano** y envia
7. En el restaurante se revisa el pago dentro del chat
8. **Un mesero cualquiera escanea ese QR** con la pantalla de siempre
9. El pedido entra a cocina **como domicilio, sin mesa**

### Que viaja donde

> [!warning] Esta tabla cambio el 2026-09-07 con [[SPEC-019 - Clientes]]
> Antes, la direccion viajaba **solo en el mensaje de WhatsApp** y el telefono no
> viajaba en ningun lado — llegaba solo, como el numero desde el que escribian.
> Eso bastaba para entregar el pedido, pero hacia imposible guardar clientes:
> el servidor nunca veia ni el telefono ni la direccion.
>
> La alternativa era pedirle al mesero que los teclara al confirmar. Se
> descarto: **un paso manual en hora pico es un paso que no se hace.** Ahora
> ambos viajan dentro del QR firmado, que el cliente ya llena una sola vez.

| Dato | Donde va | Por que |
|---|---|---|
| Items y cantidades | En el QR | Es el pedido |
| Nombre de quien recibe | En el QR (campo `c`) y en el mensaje | Ya habia campo; no cuesta nada |
| **Direccion** | **En el QR (campo `a`)** y en el mensaje | El servidor la necesita para reconocer al cliente (SPEC-019). Sigue tambien en el mensaje, que es donde la persona la lee |
| **Telefono** | **En el QR (campo `t`)** | Es lo que identifica al cliente. Sin el, cada pedido seria una persona nueva |
| Marca de "soy domicilio" | En el QR | Para que al confirmar no se pida mesa |

Los campos `t` y `a` **solo se agregan cuando el pedido es domicilio**: un
pedido de mesa no los lleva, porque no los tiene. Y `verificar_pedido` los lee
con valor por defecto, asi que **los QR emitidos antes de este cambio siguen
siendo validos** — hay prueba de eso
(`test_un_QR_viejo_sin_telefono_sigue_siendo_valido`).

Cuestan unos 166 caracteres de los ~1800 disponibles (ver "Limite de tamano"):
no acercan el payload al limite.

> [!note] Lo que esto implica, dicho de frente
> El sistema **si guarda** ahora nombre, telefono y direccion. Por eso el
> carrito se lo dice al cliente antes de enviar, y por eso la ficha tiene un
> boton de eliminar que de verdad borra (Ley 1581). Ver [[SPEC-019 - Clientes]].

### La plantilla del mensaje

El texto sale del parametro `whatsapp-mensaje`, que **deja de ser una frase fija y pasa a
ser una plantilla con variables** — ver [[SPEC-007 - Administracion y Parametrizacion]].

Variables disponibles: `{nombre}` y `{direccion}`.

Ejemplo:

```
Hola, buen dia. Mi nombre es {nombre}, mi ubicacion para el domicilio es
{direccion}, y este es mi pedido en QR:
```

### Descargar la imagen

Boton explicito de **descargar el QR**, porque el cliente tiene que adjuntarlo a mano.

- En Android funciona directo
- En **iPhone** Safari a veces ignora la descarga de una imagen generada asi. Por eso,
  ademas del boton, se muestra la instruccion de **mantener presionada la imagen** para
  guardarla — para que en iPhone no se quede sin salida

La API de enlace de WhatsApp **solo admite texto**: no existe forma de que un sitio web
adjunte la imagen solo. Ver [[Viabilidad Tecnica del QR]].

## Preguntas abiertas

- Varios clientes en la misma mesa: cada QR es un pedido independiente o se suman?
- Un módulo de domicilios de verdad (tarifa de envío, domiciliario, zonas) que guarde la
  dirección **en el sistema** y no solo en el chat de WhatsApp — no está en alcance todavía
