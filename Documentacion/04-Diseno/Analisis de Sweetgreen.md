---
tipo: diseno
actualizado: 2026-08-21
tags: [diseno, analisis, referencia]
---

# Analisis de Sweetgreen

> Datos extraidos de los estilos computados reales del sitio (via archivo web, porque
> sweetgreen.com bloquea el acceso automatizado). No son impresiones: son mediciones.

## Paleta exacta

| Rol | Valor | Uso medido |
|---|---|---|
| Fondo | `#F4F3E7` | Crema calido — **nunca blanco** |
| Verde profundo | `#00473C` | **556 elementos**: el color dominante |
| Casi negro verdoso | `#0E150E` | 234 elementos: texto de platos |
| **Lima acido** | `#E6FF55` | El acento que hace que la marca se sienta viva |
| Salvia | `#D8E5D6` | Fondos de seccion |
| Durazno | `#F9DFCE` | Fondos de seccion |
| Azul palido | `#D6E9E9` | Fondos de seccion |

## Tipografia — lo mas revelador

- Cuerpo: `SweetSansText`, **una sola familia, un solo peso (400)**, en **805 elementos**.
  Cero negritas
- Titulos de plato: 24px, **MAYUSCULAS**, letter-spacing 0.72px, peso 400
- Display: `Grenette` serif en **peso 200** (extra fino), a 48px y 80px.
  Apenas 13 elementos en toda la pagina
- Etiquetas de metricas: mayusculas, letter-spacing 1.28px

## Geometria

- Imagenes **cuadradas 1:1** (379x379), `border-radius: 20px` (54 usos)
- Pildoras de `1000px` para botones (5 usos)
- **Una sola sombra en toda la pagina.** Practicamente cero

## Retícula

- 3 columnas de 379px, gap **48px vertical / 24px horizontal**
- Contenedor de 1185px
- Tarjeta de **707px de alto**: la foto es solo el 53%, el resto es texto

## Contenido

- **47 fotografias** en una sola pagina
- Las imagenes son PNG: recortes de estudio, tomas cenitales
- Cada tarjeta trae nombre, **lista completa de ingredientes**, alergenos y **cinco
  metricas** (calorias, proteina, carbos, grasa, CO2e)

## Las dos lecciones

> [!important] 1. La fotografia ES el diseno
> 47 fotos profesionales cenitales, todas con la misma proporcion, luz y encuadre. Ningun
> ajuste de CSS compensa la falta de fotografia real: un degradado de relleno hace que la
> pagina se vea como un boceto.

> [!important] 2. No es minimalista, es generosa
> Tarjetas de 707px llenas de informacion. La sensacion de aire **no viene de quitar
> contenido**, viene del espaciado grande y de la tipografia de un solo peso.

## Errores que se corrigieron gracias a este analisis

| Aspecto | Sweetgreen | Primer intento (fallido) |
|---|---|---|
| Imagen | Foto real 1:1, 47 fotos | Degradado CSS 4:3 |
| Radio | 20px | 6px |
| Tipografia | 1 sans peso 400 + serif ligero 200 | Serif 500 + sans mezclados |
| Acento | Lima acido vibrante | Terracota apagado |
| Sombras | 1 en toda la pagina | Varias |
| Gap vertical | 48px | 28px |
| Contenido por tarjeta | Ingredientes + alergenos + 5 metricas | Una frase corta |
| Altura de tarjeta | 707px | ~280px |

## Enlaces

- [[Sistema de Diseno]]
- [[Referencias Visuales]]
