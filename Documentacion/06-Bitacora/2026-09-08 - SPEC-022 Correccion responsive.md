---
tipo: bitacora
fecha: 2026-09-08
tags: [diseno, responsive, accesibilidad, correccion]
---

# 2026-09-08 — SPEC-022: Correccion responsive

## Que se hizo

Se corrigieron los 12 fallos de la auditoria y otros 6 que salieron durante la
correccion. Resultado, medido en las 20 pantallas con datos, a 375 y a 320 px,
mas 8 paneles y modales: **desborde cero, texto cortado cero, toques bajo 44 px
cero**. Antes habia ~430 toques por debajo del minimo.

## Lo que el autor decidio

*"Que sirva en telefono."* El panel de administracion entro completo. Era el
bloque mas grande: 326 de sus 344 controles estaban por debajo de 44 px.

## Como se corrigio el panel: una regla, no 344 cambios

En vez de tocar cada control, una regla de base en `style.css`: todo `button`,
`select`, `textarea` e `input` (menos casillas y radios) mide 44 px como
minimo. Lo que ya declaraba altura manda por especificidad; lo que no, la
recibe ahi. Mas `min-h-9`/`min-h-10` → `min-h-11` en 54 sitios de 12 archivos.

## Lo que solo aparecio al medir despues de cada cambio

Seis fallos que la auditoria inicial no tenia, casi todos a 320 o en estados
abiertos: el nombre del cliente truncado en Salon, "Bancolombia" cortado en el
fondo por caja, el nombre de usuario en **4 px**, el campo de Estaciones en 31,
el selector de estacion aplastando el nombre del restaurante en Cocina, y cinco
botones ✕ de 8 a 25 px de ancho.

> [!important] Medir despues de cada archivo, no al final
> Subir los toques a 44 px cambio alturas de filas y podia crear desbordes
> nuevos. Se midio pantalla por pantalla despues de cada cambio, y asi se
> supo cual de ellos rompia que.

## Una tercera falsa alarma, y de que sirve

Los botones **+** del cliente median 40 × 40 con `size-11` (44 px) en el
codigo **y en el CSS compilado**. Estaban dentro de tarjetas que aun no habian
entrado: la animacion las deja en `scale(0.9)`, y 44 × 0,9 = 39,6.

Casi se corrige algo que no estaba mal. El diagnostico ahora salta lo que este
dentro de un ancestro escalado o invisible, y la regla quedo escrita.

## Herramientas que quedan

- `python manage.py poblar_demo` — datos largos en todas las pantallas
- `frontend/herramientas/diagnostico-responsive.js` — se pega en la consola;
  `__auditar([...])` mide rutas, `__abrir(ruta, texto)` mide un modal

Los dos juntos hacen la auditoria repetible en diez minutos.

## Lo que queda a mano

El carrito del cliente **no se pudo abrir por automatizacion**. Su codigo no
tiene rejillas fijas ni pixeles, y sus controles reciben los 44 px de la regla
comun — pero nada de eso es una medicion. Hay que abrirlo en un telefono real
con tres platos dentro y llenar nombre, telefono y direccion.

## Estado

- SPEC-022 → implementada, con ese unico pendiente marcado
- 121 pruebas del servidor en verde (el frontend no tiene suite)
- El turno que se abrio para medir el panel de Caja quedo cerrado y marcado
  `[demo-responsive]`; los datos de `poblar_demo` siguen en la base para
  poder repetir la medicion
