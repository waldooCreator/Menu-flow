---
tipo: investigacion
fecha: 2026-08-21
tags: [qr, viabilidad, investigacion, probado]
---

# Viabilidad Tecnica del QR

> Investigado el 2026-08-21 con fuentes actuales. **Probado tecnicamente el 2026-08-24**
> con una implementacion real — ver la seccion al final. Ya no es solo investigacion de
> escritorio: hay numeros medidos.

## Conclusion

**Ambas piezas son posibles, tienen precedente de produccion a gran escala, y ahora estan
probadas con codigo real que genera, firma, decodifica y verifica QR de punta a punta.**

## 1. QR de pedido autocontenido

El patron —un dispositivo codifica datos firmados en un QR, otro los lee con la camara y
los verifica **sin viaje al servidor**— es exactamente el del **Certificado COVID Digital de
la UE**: miles de millones de verificaciones offline, con datos y firma dentro del QR.

Tecnicamente usa CBOR + COSE (firma) + deflate, y verificacion contra claves publicas
cacheadas. El principio es el mismo que se adopto aqui.

### Capacidad

Sobra espacio. Un QR version 40 aguanta:

| Correccion de errores | Alfanumerico | Bytes |
|---|---|---|
| L (~7%) | 4.296 | 2.953 |
| H (~30%) | 1.852 | 1.273 |

El formato compacto definido en [[SPEC-002 - QR de Pedido]] ocupa ~300-400 caracteres para
un pedido de 15-20 items. Los generadores ajustan la version automaticamente al contenido.

## 2. QR estatico de mesa

**me&u** (antes Mr Yum), la plataforma lider de pedido por QR, usa desde 2021 **QR unicos
por mesa con el numero incrustado**, impresos una sola vez, "eliminando la necesidad de que
el cliente escriba su numero de mesa". Es literalmente [[SPEC-001 - QR de Mesa]] validado
en produccion.

## 3. Hallazgo critico — compatibilidad de navegador

**Safari en iOS no soporta `BarcodeDetector` y no hay anuncio de que Apple lo agregue.**
Como todos los navegadores en iPhone corren sobre el motor de Safari, apoyarse solo en esa
API deja el escaner roto en todo iPhone.

Solucion: libreria JavaScript con la API nativa como acelerador opcional.
Ver [[ADR-005 - Escaneo con libreria JS]].

### Comparacion de librerias

| Libreria | Notas |
|---|---|
| **`qr-scanner`** (Nimiq) | ~16 KB, **Web Worker por defecto**, usa API nativa si esta. Recomendada |
| `html5-qrcode` | Mas completa, mas pesada |
| `jsQR` | Ligera pero corre en el hilo principal: hay que limitar cuadros a mano |
| `zxing-js` | Muchos formatos, paquete grande, menos mantenida |

Rendimiento: 10-30 cuadros por segundo en un telefono moderno.

## 4. Prueba tecnica ejecutada (2026-08-24)

Script Node.js en `pruebas/prueba-qr/prueba.js`. Librerias: `qrcode` (generar), `jsQR`
(decodificar — misma familia que `qr-scanner`, la elegida en ADR-005), `pngjs` (renderizar
a pixeles reales). Pipeline completo: construir payload → firmar HMAC-SHA256 → generar QR →
**renderizar a PNG real** → decodificar con jsQR → verificar firma → reconstruir el pedido.

> [!note] Simplificacion deliberada
> La firma se hizo en el mismo proceso Node, no en un endpoint Django, para poder medir el
> pipeline sin levantar el backend. En produccion firma el servidor (el secreto vive ahi,
> ADR-001) — eso no cambia nada de lo que esto prueba.

### Resultados — tamano real y version de QR

| Carrito | Bytes | Version QR | ¿Cabe en 900b? | Decodifica limpio | Decodifica con ruido+desenfoque |
|---|---|---|---|---|---|
| 3 items, sin obs. | 148 | 8 | Si | Si | Si |
| 8 items, obs. cortas | 263 | 12 | Si | Si | Si |
| 15 items, obs. cortas | 357 | 14 | Si | Si | Si |
| 30 items, obs. largas (texto libre) | **1.767** | 35 | **No** | Si | Si |
| 50 items, obs. largas | 5.541 | — (excede la capacidad del QR) | No | — | — |

**El caso de 50 items no genero QR** — la libreria fallo con "amount of data is too big".
Es la prueba real de que el Plan B de [[SPEC-002 - QR de Pedido]] no es un caso teorico.

**El caso de 30 items con texto libre resulto casi 3x mas pesado que la estimacion
original** de la spec (~700 caracteres estimados vs. 1.767 medidos). La estimacion no
contaba con observaciones reales en lenguaje natural.

### Hallazgo: observaciones por indice en vez de texto

Repitiendo el carrito de 30 items pero codificando las observaciones rapidas como indices a
`ObservacionRapida` (SPEC-003) en vez de como frases completas:

| Codificacion | Bytes | Version QR |
|---|---|---|
| Texto libre | 1.767 | 35 (impractico) |
| Indices | **547** | **18 (comodo)** |

**69% menos peso.** Se anadio como regla en [[SPEC-002 - QR de Pedido]].

### Verificaciones de seguridad e integridad

- **Firma alterada → rechazada.** Se cambio un caracter de la firma y `verificarYDecodificar`
  devolvio `valido: false`, con comparacion en tiempo constante (`crypto.timingSafeEqual`)
- **Payload recuperado identico al original** en todos los casos que generaron QR
- **Umbral de tamano en pantalla:** se probaron escalas de render de 1 a 8 px/modulo — todas
  decodificaron correctamente en el render limpio. *(Limite del metodo: esto prueba que la
  estructura del QR sobrevive a baja densidad de pixeles en una imagen sintetica perfecta,
  no que una camara de telefono real enfoque un QR de 69px de una pantalla a distancia. La
  recomendacion de tamano fisico minimo en pantalla sigue siendo la practica estandar del
  sector, no algo que esta prueba pueda descartar.)*
- **Robustez ante degradacion:** se aplico ruido aleatorio por pixel + desenfoque de caja 3x3
  (aproximacion de una foto de camara imperfecta) — decodifico correctamente en todos los
  casos probados

### Tiempos medidos (firmar + generar + renderizar + decodificar, de punta a punta)

| Carrito | Tiempo total |
|---|---|
| 3 items | ~119-136 ms |
| 8 items | ~119-137 ms |
| 15 items | ~104-150 ms |
| 30 items (texto libre, QR version 35) | ~511-526 ms |

Confirma lo que pedia la idea original: el QR se genera y se lee **de manera inmediata**
para pedidos normales. El caso pesado (30 items, texto libre) sigue siendo subsegundo.

### Artefacto de prueba

Se genero un QR real escaneable (`pruebas/prueba-qr/salida/pedido-ejemplo.png`) con un
pedido de 8 items, enviado al autor para escanear con su propio telefono como verificacion
final independiente de este analisis.

## 5. Compartir el QR por WhatsApp (investigado 2026-08-25)

Petición del autor: que el pedido "a distancia" pueda enviarse por WhatsApp con la foto del
QR, para confirmar domicilios. Hay que separar dos mecanismos que se confunden fácil,
porque cada uno logra la mitad de lo que se pidió y ninguno logra las dos a la vez sin pagar
por una integración de negocio:

| Mecanismo | Adjunta la imagen | Dirige a un número fijo sin que el usuario elija | Requiere backend/costo |
|---|---|---|---|
| Enlace `wa.me/<numero>?text=...` | **No** — la API de enlace de WhatsApp solo admite texto, no hay forma de adjuntar un archivo por URL | Sí, automático | No |
| Web Share API (`navigator.share`) con el PNG como `File` | **Sí** | No — abre el panel nativo para compartir del teléfono, y el cliente elige WhatsApp y el contacto ahí mismo | No |
| WhatsApp Business API (Meta) | Sí | Sí | **Sí** — verificación de negocio, backend propio, costo por conversación |

**Lo que se implementó:** la Web Share API. Es real, funciona hoy, y no depende de ningún
servicio de pago — pero el cliente da un toque más (elegir WhatsApp en el panel que le
aparece, y confirmar el chat) en vez de que la app lo mande sola a un número fijo. Es la
misma limitación de cualquier sitio web que "comparte a WhatsApp": ningún estándar público
permite adjuntar un archivo Y dirigirlo automáticamente a la vez, sin la API de negocio.

**Compatibilidad:** Chrome Android y Safari iOS 15+ soportan compartir archivos de sobra.
Exige contexto seguro (HTTPS o `localhost`) — el mismo requisito que ya tiene la cámara
del mesero (ADR-005). En navegadores sin soporte, la app cae a un aviso pidiendo guardar la
captura y enviarla a mano.

**Si en el futuro se quiere el envío automático a un número fijo**, el camino es la API de
WhatsApp Business — un proyecto aparte, con verificación de Meta y costo por conversación,
fuera de alcance de esta rebanada.

## Fuentes

- [Consilium — EU Digital COVID Certificate](https://www.consilium.europa.eu/en/policies/coronavirus-pandemic/eu-digital-covid-certificate/)
- [eHealth Network — especificaciones tecnicas](https://health.ec.europa.eu/document/download/c0a07892-a01c-4bc8-8e9f-1e91d9597d17_en)
- [me&u — QR Code Table Signage](https://help.meandu.com/hc/en-us/articles/6539880067599-Introduction-to-QR-Code-Table-Signage)
- [MDN — BarcodeDetector](https://developer.mozilla.org/en-US/docs/Web/API/BarcodeDetector)
- [npm-compare — librerias de escaneo](https://npm-compare.com/@zxing/library,html5-qrcode,jsqr,qr-scanner,qrcode-reader)
- [ME-QR — capacidad de un QR](https://me-qr.com/page/blog/how-much-data-can-qr-code-hold)

## Enlaces

- [[SPEC-001 - QR de Mesa]]
- [[SPEC-002 - QR de Pedido]]
- [[ADR-001 - QR autocontenido y firmado]]
- [[ADR-005 - Escaneo con libreria JS]]
