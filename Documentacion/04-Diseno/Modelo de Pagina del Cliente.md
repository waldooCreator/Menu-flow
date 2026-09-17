---
tipo: diseno
actualizado: 2026-08-21
tags: [diseno, pagina, cliente, estructura]
---

# Modelo de Pagina del Cliente

## Estructura (una sola pagina, scroll vertical)

```
+----------------------------------------------+
|  [logo]                    Encuentranos       |  <- enlace fijo arriba a la derecha
|                                              |
|         IMAGEN DE FONDO CON PARALLAX         |  <- hero, ~88vh
|              nombre del restaurante           |
|                                              |
|   al bajar, el hero se oculta dinamicamente   |
+----------------------------------------------+
|  [Compartir] [Bowls] [Asador] [Bebidas] ...  |  <- filtros pegajosos
|                                              |
|   +--------+  +--------+  +--------+          |
|   |  foto  |  |  foto  |  |  foto  |          |  <- rejilla de platos
|   | nombre |  | nombre |  | nombre |          |
|   | precio |  | precio |  | precio |          |
|   +--------+  +--------+  +--------+          |
|              ... todo el menu ...             |
+----------------------------------------------+
|  ENCUENTRANOS                                |  <- destino del enlace de arriba
|  fotos del lugar - direccion - como llegar   |
|  horarios - mapa - contacto - PQRSF          |
+----------------------------------------------+
        [ Ver pedido (3) ]                       <- boton flotante, siempre visible
```

## Comportamiento del hero

- Imagen de fondo con **efecto parallax**
- **Ocupa el 100% de la pantalla**, en cualquier resolucion. Al cargar no se ve nada mas:
  ni la franja del menu, ni los filtros, ni el boton de pedido, ni la etiqueta de prototipo
- **Recorrido largo:** el hero se queda fijo (sticky) dentro de un contenedor de 200vh,
  de modo que la animacion se desarrolla durante toda una pantalla extra de scroll antes
  de dar paso al menu
- Al avanzar el recorrido **se oculta gradualmente**: el fondo se desplaza y escala, y el
  contenido se desvanece y sube
- **Flecha animada** en la parte inferior que incita a bajar, y desaparece apenas empieza
  el scroll

> [!warning] Reversion de una decision previa (2026-08-21)
> Este documento decia antes: *"Ocupa ~88% de la altura de pantalla, **no el 100%**: que el
> borde del menu asome por abajo indica que hay mas contenido"*.
>
> **Se cambio a pantalla completa por decision estetica del autor.** La señal de "hay mas
> contenido", que antes daba el borde del menu asomando, se resolvio con la **flecha
> animada**. No volver al 88% sin reemplazar tambien esa señal.

### Detalle tecnico

Se usa `100lvh` (large viewport height) y no `100dvh`. Con `dvh` la altura se encoge cuando
la barra del navegador esta visible y puede asomar una franja del fondo bajo el hero, que es
justo lo que se queria eliminar. Ademas `.hero-scroll` lleva el color oscuro de fondo como
respaldo, para que ninguna franja clara sea posible.

## "Encuentranos"

- Enlace discreto **arriba a la derecha**, visible desde el inicio
- Al hacer clic, lleva con desplazamiento suave **al final de la pagina**
- No es una pagina aparte: es una seccion de la misma pagina

## Dos entradas, dos comportamientos

| Entrada | Publico | Comportamiento |
|---|---|---|
| **QR de mesa** | Ya esta sentado, con hambre | **Entra directo al menu**, se salta el hero |
| **Enlace directo** | Decide si vale la pena ir | Entra por el hero, experiencia completa |

> [!note] Son dos intenciones opuestas
> El cliente que escanea el QR de la mesa ya llego: no necesita ver fotos del local ni como
> llegar. La pagina informativa **no es para el**.

## Responsive

Los usuarios principales son de **movil y tablet**, no de escritorio. La misma experiencia
debe estar asegurada en los tres.

| Rango | Dispositivo tipico | Menu |
|---|---|---|
| > 1024px | Escritorio | Rejilla de **3 columnas** |
| 641 – 1024px | Tablet, movil en horizontal | Rejilla de **2 columnas** |
| <= 640px | Telefono | **Lista** con miniatura + texto |
| <= 380px | iPhone SE y similares | Lista con miniatura reducida |

### Reglas tactiles

- **Area tactil minima de 44px** en todo control: chips, boton de agregar, cerrar,
  cantidad. Es el minimo recomendado por Apple y Android
- Los efectos `hover` se anulan en dispositivos tactiles con `@media (hover: none)`:
  en tactil se quedan "pegados" despues del toque
- `-webkit-tap-highlight-color: transparent` en los controles

### iOS y Android

- **Areas seguras:** barra superior, boton flotante y modal respetan
  `env(safe-area-inset-*)` para no quedar bajo el notch ni la barra de gestos
- El hero usa `100lvh`, no `100dvh` (ver arriba)
- El modal usa `-webkit-overflow-scrolling: touch` y `overscroll-behavior: contain`
  para que el scroll interno no arrastre la pagina de fondo

### Horizontal en pantallas bajas

Con menos de 560px de alto en horizontal, el hero completo deja poco espacio util:
el recorrido se recorta a 150vh y se oculta el subtitulo.

## Cuidados tecnicos

- **El parallax clasico (`background-attachment: fixed`) no funciona en iOS Safari.**
  Resolverlo con transformaciones ligadas al scroll
- Respetar `prefers-reduced-motion`
- Cuando el hero se oculta, barra superior y filtros quedan pegajosos: definir el orden de
  apilamiento desde el principio
- **Todos los colores y tipografias deben ser variables desde la primera linea de CSS**

## Estado

Implementado como prototipo visual en `/prototipo`. Ver [[SPEC-003 - Menu del Cliente]].

## Enlaces

- [[Sistema de Diseno]]
- [[SPEC-001 - QR de Mesa]]
- [[SPEC-003 - Menu del Cliente]]
