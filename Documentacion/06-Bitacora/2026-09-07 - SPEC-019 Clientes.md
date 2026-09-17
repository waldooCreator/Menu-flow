---
tipo: bitacora
fecha: 2026-09-07
tags: [clientes, domicilios, privacidad, reportes]
---

# 2026-09-07 — SPEC-019: Clientes

## Que se hizo

Se implemento el directorio de clientes: se crean solos al confirmar un
domicilio, se consultan y corrigen desde una pantalla propia, y se pueden
borrar de verdad. Con eso quedo desbloqueado el quinto reporte de
[[SPEC-018 - Reportes de Venta]].

## La pregunta que lo empezo

El autor la planteo asi:

> ¿Como podriamos hacer que se enlacen si por ejemplo dicen en el pedido #1
> "maria angelica" "barrio xxx" y despues en el pedido #2 dice "angelica lopez"
> "xxx barrio"?

La respuesta fue **el telefono**, y se probo exactamente con ese caso:

```
=== PEDIDO 1: 'maria angelica', 'barrio xxx' ===
  antes de confirmar, ¿lo conoce?: None
=== PEDIDO 2: 'angelica lopez', '+57 320 276 6485', 'barrio xxx' ===
  antes de confirmar lo reconoce: maria angelica | 0 compras previas
=== RESULTADO ===
  angelica lopez | tel 3202766485 | direcciones: ['Barrio xxx']
  clientes totales: 1 (debe ser 1)
  cuentas enganchadas: 2
```

## La decision mas dificil: no reordenar las palabras de la direccion

Normalizar la direccion (minusculas, sin tildes, sin puntuacion) resuelve
`Barrio XXX` contra `barrio xxx`. **Ordenar las palabras** resolveria tambien
`barrio xxx` contra `xxx barrio`, que es la mitad del caso que pregunto el
autor.

Se decidio **no hacerlo**, porque el mismo truco haria coincidir
`calle 5 casa 20` con `calle 20 casa 5` — dos casas distintas. Equivocarse ahi
es mandar la comida a otra direccion.

La regla que quedo: **ante la duda, se guardan las dos y decide la persona.**
Duplicar una direccion es ruido menor; entregar en la casa equivocada no.

## El telefono se captura sin darle trabajo al mesero

El autor lo puso claro: *"pero eso implicaria un trabajo para el mesero. no
queremos eso"*.

El telefono y la direccion pasaron a viajar **dentro del QR firmado**: el
cliente los escribe una vez en el carrito, el navegador se los guarda para la
proxima, y llegan firmados hasta el servidor. Ocupan 166 de los ~1800
caracteres disponibles. Ver [[SPEC-002 - QR de Pedido]], que cambio por esto.

Un paso manual en hora pico es un paso que no se hace.

## Un defecto que ninguna prueba encontro

Al hacer el recorrido completo con clics salio esto: la pantalla de recibir
pedido pedia elegir mesa para **cualquier** QR sin mesa, y dejaba el boton de
enviar deshabilitado hasta elegirla. **Un domicilio no tiene mesa**, asi que no
se podia confirmar un domicilio desde la pantalla.

El servidor ya lo hacia bien (`if not es_domicilio:` antes de exigir mesa). La
interfaz no. Las 84 pruebas pasaban todas.

> [!important] La leccion, que ya se repitio antes
> Las pruebas cubren el servidor. Lo que la pantalla deja hacer o no dejar
> hacer solo se ve haciendo el recorrido. Es el mismo tipo de error que el
> "responsive verificado" del 2026-09-07 por la manana: dar por bueno lo que no
> se recorrio.

## Lo que quedo sin hacer, y se anoto como tal

Dos criterios de aceptacion **no** se cumplieron y estan marcados sin marcar en
la spec:

1. **Elegir entre varias direcciones al pedir.** Guardar varias funciona;
   ofrecerselas al cliente no, porque en ese momento el sistema todavia no sabe
   quien es — y consultarlas apenas teclee un telefono expondria datos de otra
   persona a quien adivine el numero.
2. **Que el enlace "Clientes" no se le muestre a quien no puede cobrar.** El
   servidor si lo impide (403, con prueba). El enlace en la barra si se muestra
   — igual que Caja, Libro y Ventas. Es una brecha de toda esa familia y se
   arregla de una vez en `MarcoInterno.vue`.

## Estado

- 20 pruebas nuevas en `clientes/tests.py`; **86 en total, todas pasando**
- SPEC-019 → implementada
- SPEC-002 → actualizada: el QR de domicilio lleva telefono y direccion
- SPEC-018 → el quinto reporte ya existe

Los datos que se crearon para verificar en pantalla se borraron al terminar: la
base quedo con 0 clientes.

## Siguiente

Quedan de la comparativa con Springfield: Resumen operativo, Grafica,
Domicilios (contable), Promociones, Mapa de zonas, Configuraciones agrupadas y
Restablecer. Sigue pendiente decidir si se borran las 123 ventas de demostracion.
