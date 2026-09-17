---
tipo: bitacora
fecha: 2026-08-25
tags: [bitacora, tema, springfield, whatsapp, parametrizacion]
---

# 2026-08-25 — Tema Springfield y enlace WhatsApp

Cuarta tanda del día. Boceto visual para el cliente potencial: convertir el sitio en
"Springfield" (estética Los Simpson) — y de paso, la prueba de fuego del requisito 1.

## Lo esencial

**El cambio de marca completo fue configuración, no código.** Un comando nuevo
(`cargar_tema_springfield`) actualiza parámetros: paleta, tipografías, nombre, textos e
imágenes. Volver a Terra es correr `cargar_configuracion_demo`. Ninguna vista cambió por
el tema en sí — eso es exactamente lo que promete [[SPEC-007 - Administracion y Parametrizacion]].

## Investigación (fuentes reales)

- Amarillo oficial del logo **#FFDE00**, paleta extendida con azul **#2F64D6** y rosa dona
  **#FF81C1** ([brandpalettes.com](https://brandpalettes.com/the-simpsons-color-codes/),
  [color-hex.com](https://www.color-hex.com/color-palette/12626))
- Tipografía: la fuente exacta del show no está en Google Fonts;
  [Luckiest Guy](https://fonts.google.com/specimen/Luckiest+Guy) es la aproximación cartoon
  gratuita (títulos), con **Nunito** de cuerpo (redondeada, pesos completos, legible)

**Decisión de paleta:** el amarillo va de **acento**, no de fondo dominante — texto sobre
amarillo intenso no se lee. Se conservó la estructura del [[Sistema de Diseno]]: fondo
cálido (#FFF9E6), marca profunda (azul #2F64D6), acento vibrante (#FFDE00).

## Imágenes: provisionales, y ahora sí alusivas

El primer intento usó placeholders de banco (cielo, diner, donas) — el autor lo rechazó
con razón: "no tiene nada alusivo a Los Simpson". Segunda pasada con material real del
show, descargado como provisional (el restaurante entregará su material licenciado tras la
reunión; ellos afirman tener la licencia de los personajes):

- **Hero:** panorama "Welcome to Springfield" con la planta nuclear (wallpapercave)
- **Galería:** el restaurante **Krusty Burger** (simpsonswiki.com), la familia en el sofá
  (wallpapers.com) y la multitud de personajes de Springfield
- Favicon: dona rosada en SVG propio

De paso se destapó otra violación de la regla: los **pies de la galería** ("El salón",
"La barra", "La terraza") estaban escritos a mano en `ClienteMenu.vue` — con fotos
temáticas no aplicaban. Se parametrizaron (`galeria-pie-1/2/3`); Springfield los pone en
"Krusty Burger", "En familia" y "Todo Springfield".

## Figuras decorativas detrás del menú (tercera pasada)

El autor entregó cuatro imágenes de personajes y pidió ponerlas de fondo tras el menú,
con movimiento al hacer scroll.

**Recorte de fondo.** Las cuatro venían en JPG con fondo sólido, no transparente:

| Imagen | Fondo que traía |
|---|---|
| Familia con donas | Tablero de transparencia **quemado** en el JPG (blanco + gris) |
| Krusty | Blanco puro |
| Homer con hamburguesa | Blanco puro |
| Bart | Azul lavanda `#EDF4FC` |

Se recortaron con **relleno por inundación desde los bordes**, no reemplazo global de
color — así el fondo desaparece pero la camisa blanca de Homer, que no toca el borde, se
conserva. Script en el scratchpad de la sesión; resultados en
`backend/recursos/springfield/deco/*.png` (26–53% de píxeles transparentes).

Krusty y Homer conservan su borde blanco de calcomanía: es parte del diseño original y a
baja opacidad sobre crema resulta invisible.

**Nuevo modelo:** grupo `decoracion` con `deco-imagen-1..4` (migración
`0002_alter_parametro_grupo`). Se crean **vacías**: un restaurante que no las llene no
tiene decoración, y `cargar_configuracion_demo` las borra al volver al tema base.

### Corrección: papel tapiz, no figuras sueltas

La primera versión puso las cuatro figuras sueltas en los márgenes del menú, con parallax
individual. **El autor la rechazó**: quería las imágenes *en el fondo del menú*, como
papel tapiz que lo anima. Se preguntó antes de rehacer, en vez de adivinar por segunda vez.

**Mosaico sin costuras.** Se compuso un tile de 900×900 con ocho instancias de los cuatro
personajes (tamaños y giros variados, 25% de cobertura). La técnica: cada figura se pega
en las **9 posiciones de una malla 3×3** (±ancho, ±alto) y se recorta el cuadro central —
así lo que sobresale por un borde reaparece exacto en el opuesto. Verificado repitiendo el
patrón 2×2: sin junturas visibles en las líneas centrales.

Nueva clave `deco-patron`; `deco-imagen-1..4` quedan como las piezas de origen. Regenerar
el mosaico tras cambiar las figuras es hoy un paso manual (script en el scratchpad) — no
automático, anotado como límite.

**`DecoracionesFondo.vue`** lo pinta como `background-repeat`, desplazando
`background-position` con el scroll (factor 0.12) para animarlo. Reglas duras: `-z-10`
(siempre bajo el contenido), `pointer-events-none` (nunca bloquea un toque), y quieto con
`prefers-reduced-motion`.

### Segunda corrección: sobre TODO el fondo beige, y más visible

Puesto solo dentro de la sección del menú, el tapiz quedaba acotado y —al 22% con figuras
pálidas sobre crema— apenas se percibía; el autor lo leyó como que estaba "en el footer".

**Se movió al contenedor raíz de la página**, no a la sección del menú. Detalle que lo
hace posible: la raíz lleva `isolate` (`isolation: isolate`), porque sin crear un contexto
de apilamiento propio la capa `-z-10` se iría **detrás del fondo del documento** y no se
vería nada. El hero (`bg-[#10241B]`) y "Encuéntranos" (`bg-marca`) tienen fondo opaco
propio, así que lo tapan en sus tramos: el tapiz asoma **solo donde el fondo es beige**,
que es exactamente lo pedido.

Ajustes de visibilidad: tesela 300px escritorio / 210px móvil ("medianos"), opacidad
0.45 / 0.40. Verificado que cubre el documento completo (10.032 px) sin desborde
horizontal y sin tapar ningún control.

### Datos reales del restaurante

Entregados por el autor: sede **Calle 18a #8-71, Libertad, Cúcuta (Norte de Santander)**,
horario **5:30 pm – 11:00 pm**, WhatsApp **573202766485**.

> [!warning] El enlace venía envuelto por Instagram
> El autor pasó `https://l.instagram.com/?u=https%3A%2F%2Fwa.me%2F573202766485%3Ftext%3D...`
> — el envoltorio que Instagram pone a los enlaces salientes. **No se usó**: lleva un token
> `e=` firmado que caduca y añade un salto de redirección por servidores de Instagram. Se
> extrajo el `wa.me` real de dentro (número + mensaje, doblemente codificado en el
> original). El enlace que genera el sitio es idéntico en destino y no depende de Instagram.

El mensaje también se parametrizó (`whatsapp-mensaje`), que estaba fijo en el código —
otra deuda de la misma regla.

### Verificado

- Las 4 figuras cargan y se pintan; contenedor en `z-index: -10`, `pointer-events: none`
- **Un plato sigue siendo clicable** con una figura detrás: `elementFromPoint` devuelve el
  botón y el clic agrega al carrito
- Sin desborde horizontal en 375px ni al hacer scroll
- Texto del menú sin cambio de contraste (`rgb(38,32,26)` sobre crema)

### Dos falsas alarmas (misma familia de siempre)

`platoClicable: false` en la primera medición: el botón estaba en `top: -609`, fuera de
pantalla por mi propio scroll de prueba — `elementFromPoint` con Y negativo devuelve null.
Y `seMovio: false`: **`requestAnimationFrame` no corre en el panel del navegador**
(comprobado explícitamente), así que el parallax no puede observarse aquí. No hace falta
respaldo por temporizador como en las entradas laterales: si rAF nunca corre, las figuras
solo se quedan quietas — son decorativas, no se pierde contenido.

> [!warning] No verificado por Claude
> El **movimiento** de las figuras al hacer scroll. La lógica está, pero solo se confirma
> en un navegador real.

## Deuda pagada: los "Terra" escritos a mano

Este ejercicio destapó textos de negocio fijos en el código, contra la regla del proyecto:
el header interno, el login, el título de la pestaña, el texto del mensaje de WhatsApp y el
nombre del archivo del QR. Todos leen ahora de `nombre-restaurante` (las pantallas internas
y el login cargan la configuración pública y aplican el tema al montar).

## Enlace wa.me (pedido a distancia)

Nueva clave `numero-whatsapp` (solo dígitos con indicativo). En el resultado "A distancia"
aparecen las dos vías juntas: el botón de compartir (adjunta la imagen, el cliente elige el
chat) y el enlace `wa.me` directo al restaurante con texto precargado (la imagen la pega el
cliente). Verificado el href generado con número y mensaje correctos. Ver
[[SPEC-002 - QR de Pedido]] y [[Viabilidad Tecnica del QR]].

## Bug real encontrado: caché de configuración entre procesos

> [!bug] El servidor servía la configuración vieja para siempre
> `obtener_configuracion()` cacheaba con `timeout=None` en LocMemCache — memoria **local de
> proceso**. La invalidación por señal solo alcanza al proceso donde ocurre el guardado: un
> cambio hecho desde un comando de management (o desde otro worker en producción) jamás
> invalidaba el caché del servidor. Se descubrió porque la API siguió sirviendo Terra
> después de aplicar Springfield. **Corregido:** TTL de 60 segundos — converge solo.

Hallazgo menor: la API css2 de Google Fonts ya no rechaza pesos inexistentes (hace
fallback y responde 200), así que el doble `<link>` defensivo de `tema.js` es redundante
pero inofensivo. Y `document.fonts.check()` dio falso negativo con las caras ya cargadas
(`status: loaded` confirmado) — medir por las caras, no por `check()`.

## Verificado

- API sirviendo Springfield completo (nombre, colores, fuentes, hero, numero-whatsapp)
- Cliente: título de pestaña "Springfield", marca #2F64D6 computada, Luckiest Guy y Nunito
  cargadas, hero de cielo, flujo "A distancia" con botón compartir + enlace wa.me correcto
- Internas: header "Springfield" y tema aplicado en mesero y admin
- Móvil 375px: cliente, mesero y estación sin desborde horizontal

## Pendiente

- Imágenes definitivas licenciadas del restaurante (post-reunión)
- Elementos decorativos de tema (patrones de donas, mascota) — trabajo visual aparte
- La fuente exacta del show exigiría auto-hospedar el archivo — decisión del cliente

## Enlaces

- [[SPEC-002 - QR de Pedido]]
- [[SPEC-007 - Administracion y Parametrizacion]]
- [[Sistema de Diseno]]
- [[Viabilidad Tecnica del QR]]
- [[Inicio]]

## Quinta pasada: fondo más discreto y mapa funcional de verdad

El autor vio la sección Encuéntranos y marcó dos cosas: el fondo del menú
"quita la seriedad" con tantas imágenes — pidió **pocas y grandes**, no
muchas y pequeñas — y el recuadro de "Cómo llegar" nunca fue un mapa, era
una cuadrícula dibujada con un punto fijo.

### Tapiz: de 8 figuras pequeñas a 4 grandes

La tesela pasó de 900px (8 instancias por tile, repetida a 300px) a
**1400px con una sola instancia de cada uno de los 4 personajes**, mostrada
a 900px en escritorio / 460px en móvil. Opacidad 0.45→**0.12**.

Medido el efecto neto, no solo el número: se compuso el fondo real a escala
de pantalla (1440×820) y se midió cuánto se aleja del crema puro.

| | figuras/pantalla | desviación media | peor píxel | contraste texto |
|---|---|---|---|---|
| Antes | ~115 | 20.2/255 | 114/255 | — |
| Ahora | ~6 | 5.5/255 | 30/255 | 11.7:1 (AA pide 4.5:1) |

Costura verificada igual que la vez anterior (repetir 2×2, comparar el
empalme contra la diferencia típica entre filas contiguas): dentro de rango,
sin junta visible. De paso el PNG bajó de 1.3 MB a 136 KB (cuantizado a 128
colores — imperceptible al 12% de opacidad).

### Mapa real, no decorativo

**`MapaUbicacion.vue`** nuevo, con OpenStreetMap embed (no Google Maps: sin
llave de API, sin tarjeta, sin gestionar una llave por restaurante — sigue
[[SPEC-007 - Administracion y Parametrizacion]]). Nace sin interacción
(`pointer-events-none`) y se activa con un toque, para que el iframe no
atrape la rueda del ratón de quien solo quiere seguir bajando la página. El
botón "Cómo llegar" abre `google.com/maps/dir` con la ruta trazada — eso sí
en la app nativa del teléfono.

Nuevos parámetros `mapa-latitud` / `mapa-longitud` (grupo contacto,
GRUPO_CONTACTO). Se validan en rango en el propio componente — un `0,0` por
un campo a medio llenar no debe apuntar al Golfo de Guinea en silencio.

**Coordenadas de Springfield**, geocodificadas con Nominatim/OSM a partir de
la dirección real: `7.8865671, -72.4788715` — cae sobre la Calle 18A del
barrio Libertad. Aproximado al tramo de calle, no a la puerta exacta (el
`#8-71` no está indexado en OSM); el cliente lo afina desde el panel con el
clic derecho de Google Maps sobre su local.

### Deuda pagada de paso: contacto con datos inventados

Al revisar "Cómo llegar" salió que **teléfono y correo seguían siendo los de
Terra** (`+57 300 123 4567`, `hola@terra.com`) — el comando de Springfield
nunca los tocó. Corregido: `telefono` a `+57 320 276 6485` (el mismo número
de WhatsApp), y `correo` se deja **vacío a propósito** — no hay uno
entregado, y mejor un dato menos que uno inventado. La plantilla ahora
oculta cada renglón de contacto que esté vacío en vez de imprimir un hueco.

### Verificado

- Fondo: `figurasPorPantalla` 6 en escritorio y móvil, opacidad 0.12/0.10,
  documento sin desborde horizontal
- Mapa: iframe monta con el `bbox` correcto, las teselas de
  `tile.openstreetmap.org` cargan (85ms, sin bloqueo del panel), enlace
  "Cómo llegar" con destino correcto
- Botón "Cómo llegar" corregido a 44px de alto en móvil (medía 37px, bajo el
  mínimo táctil) — encontrado en esta misma verificación, no reportado
- Contraste del texto del menú sobre el peor punto del fondo: 11.7:1

> [!warning] No verificado por Claude
> El **movimiento** del tapiz al hacer scroll (rAF no corre en el panel,
> igual que en la pasada anterior) — y el mapa mismo, más allá de que la
> tesela HTTP responde: cómo se ve y se siente el toque para activarlo, solo
> en un navegador real.
