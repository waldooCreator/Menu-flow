---
tipo: bitacora
fecha: 2026-08-25
tags: [bitacora, correccion, decoracion, mapa, whatsapp, qr, bug]
---

# 2026-08-25 — Corrección del fondo decorativo, mapa real y dos bugs de campo

Quinta tanda del día. Dos frentes distintos: ajustar el papel tapiz que se había
sobrecargado, y corregir dos fallas reales que el autor encontró probando el
sistema desde el celular en la calle.

## Que se hizo

1. **Papel tapiz: menos figuras, más grandes, mucho más suave.** El autor lo
   describió como "muy fuerte" y con "muchas imágenes" que "quita la
   seriedad". Se regeneró el mosaico con **cuatro figuras únicas a gran
   tamaño** en una tesela de 1400px (antes: ocho instancias pequeñas en
   900px), desplegada a 900px en escritorio / 460px en móvil — de ~115
   figuras visibles por pantalla a **~6**. Opacidad 0.45 → **0.12**.
   Verificado con un test de costura contra línea base (no una comparación
   directa de dos filas, que siempre difieren algo) y una composición real
   a la escala de despliegue: el peor píxel del fondo ahora se aleja 30/255
   del crema, antes 114/255 — y el contraste del texto del menú contra el
   punto más oscuro del fondo da 11.7:1 (WCAG AA pide 4.5:1).
2. **Mini-mapa real en "Encuéntranos".** El recuadro con cuadrícula dibujada
   y un punto fijo no era un mapa, era decoración — el autor lo llamó "un
   recuadro falso" y pidió que fuera funcional. Nuevo componente
   `MapaUbicacion.vue`: incrusta OpenStreetMap (`embed.html`, sin llave de
   API) centrado en coordenadas configurables (`mapa-latitud`/
   `mapa-longitud`, nuevo grupo de parámetros), nace sin interacción
   (`pointer-events-none`) para no atrapar el scroll y se activa con un
   toque, más un botón "Cómo llegar" que abre Google Maps con la ruta ya
   trazada desde donde esté el cliente.
3. **Coordenadas geocodificadas** con Nominatim (OpenStreetMap) a partir de
   la dirección real: Calle 18A, barrio Libertad, Cúcuta — aproximado al
   tramo de calle (el edificio exacto #8-71 no está en el mapa base). Queda
   anotado en el comando de siembra para que el cliente lo afine desde el
   panel.
4. **Deuda destapada de paso:** el teléfono (`+57 300 123 4567`) y el correo
   (`hola@terra.com`) del tema Springfield seguían siendo los de Terra —
   nadie los había actualizado con los datos reales. Se corrigió el
   teléfono; el correo se deja **vacío a propósito** (no fue entregado) y
   el pie de "Encuéntranos" ya no imprime una línea en blanco cuando un
   dato falta.

## Dos bugs reales, encontrados probando desde el celular

> [!bug] Subir una foto para leer el QR se quedaba cargando para siempre
> `alSeleccionarArchivo` llamaba `await decodificarImagen(archivo)` sin
> `try/catch`. Cuando el archivo no es algo que un `<img>` pueda decodificar,
> la promesa de carga se rechaza (`img.onerror`) — y como nadie atrapaba ese
> rechazo, la pantalla se quedaba en "Leyendo el código…" indefinidamente.
> Reproducido de forma controlada: se inyectó un archivo con bytes al azar y
> extensión `.jpg` directo en el `<input type="file">` (sin cámara física),
> y la consola mostró exactamente `Uncaught (in promise)` sobre el evento de
> error de la imagen — confirmando la causa antes de tocar el código.
> **Corregido** con `try/catch` alrededor de la decodificación, mensaje claro
> ("no se pudo abrir esa imagen, prueba con otra foto o usa la cámara") y se
> limpia el input al seleccionar para poder reintentar con el mismo archivo.
> Verificado también que el camino normal —una imagen válida sin QR— sigue
> distinguiendo su propio mensaje ("no se pudo leer un QR en esa imagen").

> [!bug] El botón "Enviar por WhatsApp" fallaba
> La API nativa de compartir (`navigator.share`, para adjuntar la imagen del
> QR) **exige un contexto seguro**: HTTPS, o `localhost`. Probar desde el
> celular por el hotspot cae en `http://<ip-de-la-red>:5173` — ni HTTPS ni
> localhost —, así que en el mejor de los casos la API ni existe, y en el
> peor existe pero cualquier llamado a `share()` se rechaza. El botón
> prometía algo que ese contexto no podía cumplir. Reproducido simulando
> ambos casos (API ausente, y API presente que rechaza) — mismo mensaje que
> describió el autor.
> **Corregido:** se comprueba `canShare()` con el archivo real apenas se
> genera el QR (no con una prueba aparte), y el botón que depende de la API
> nativa **solo se muestra si de verdad puede cumplir**. Cuando no puede,
> el enlace directo a WhatsApp (`wa.me`, que es solo una navegación y no
> depende de ningún permiso) pasa a ser la acción principal, con la
> instrucción de pegar la imagen a mano. De paso, el `title` que se le
> pasaba a `share()` estaba fijo en `"Pedido Terra"` — otra violación de la
> regla de parametrización — ahora usa `nombreRestaurante()`.
>
> Importante para el autor: **en producción, detrás de HTTPS real, el
> camino con adjunto automático va a funcionar** — esto es un bug de verdad
> (el botón fallaba sin avisar por qué), no solo un artefacto del entorno de
> pruebas. Lo que cambió es que ahora el sistema se adapta a lo que el
> navegador puede cumplir, en vez de asumirlo.

## Cómo se probó, dado que el panel de este entorno no compone frames

Los flujos dependían de un empujón de scroll (`fueraDelHero`) que solo se
actualiza dentro de `requestAnimationFrame` — y este panel de navegador no
pinta fotogramas en segundo plano (limitación ya documentada). Para probar
la lógica real sin depender de eso, se sobrescribió `window.requestAnimationFrame`
para que ejecute el callback de inmediato, solo dentro del contexto de
prueba — el componente en sí no se tocó. Con eso se pudo: agregar un plato,
abrir el carrito, generar el QR "a distancia", y ejercitar el botón de
WhatsApp en sus tres variantes (API ausente, API que rechaza, API que
funciona) confirmando en cada caso el archivo adjunto, el texto y el
título correctos.

## Verificado

- Costura del mosaico dentro de rango normal; peso del tile 1.3 MB → 136 KB
  tras cuantizar (imperceptible al 12% de opacidad)
- Mini-mapa carga teselas reales de OpenStreetMap; enlace "Cómo llegar" abre
  Google Maps con las coordenadas correctas
- Sin desborde horizontal en 375px en ninguno de los dos flujos corregidos
- API pública sirviendo teléfono y coordenadas correctas tras el TTL de 60s
  del caché

## Enlaces

- [[SPEC-002 - QR de Pedido]]
- [[SPEC-007 - Administracion y Parametrizacion]]
- [[Inicio]]
