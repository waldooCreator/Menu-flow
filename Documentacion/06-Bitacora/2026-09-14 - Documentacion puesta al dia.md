---
tipo: bitacora
fecha: 2026-09-14
tags: [documentacion, revision, pruebas, defectos, springfield]
---

# 2026-09-14 — Documentacion puesta al dia

## Por que

Al preguntar *"que falta por hacer"* la respuesta honesta era "no se sabe bien": la
bitacora no se tocaba desde el 8 de septiembre, quince specs seguian en "aprobada"
aunque estaban construidas, habia unos 150 criterios sin marcar y la comparativa con
Springfield solo tenia al dia la seccion Contable. `CLAUDE.md` todavia decia que el
stack estaba sin definir.

## Que se hizo

**Cada criterio sin marcar se comprobo antes de marcarlo.** Nada se marco por memoria.
Tres fuentes, en este orden:

1. **Las 121 pruebas que ya existian** (`clientes` 18, `menu` 9, `nucleo` 3, `ventas`
   91). Cubren casi todo SPEC-013 y SPEC-014.
2. **Pruebas nuevas donde no habia ninguna.** `pedidos` y `estaciones` no tenian ni una.
   Se escribio `backend/pedidos/tests.py`: 39 pruebas, cada una con la
   linea de la spec que verifica. **37 pasan, 2 fallan** (ver abajo).
3. **Lectura del codigo** para lo que es de interfaz (el "Revertir" de 5 s, el impuesto
   escondido en 0, la barra lateral, el Camino B).

Resultado en las specs:

| Cambio | Cuantas |
|---|---|
| De "aprobada" a **implementada** | SPEC-001 a 007 y 011 a 015 |
| Siguen en borrador | SPEC-008 y SPEC-010 |
| Sigue en aprobada | SPEC-009 — nunca se ha probado en un servidor real |
| Preguntas abiertas resueltas con lo que se construyo | SPEC-017 (1), SPEC-020 (2), SPEC-021 (3) |

Tambien se rehizo la [[Comparativa Sidebar - Springfield vs Sistema Nuevo]]: **30 de
48 secciones hechas**, 5 parciales, 3 faltan, 4 por decidir con el restaurante y 6
fuera de alcance.

## Dos defectos reales

Salieron de las pruebas nuevas. En esta revision no se corrigieron, porque la tarea era
documentar. **Se corrigieron despues, el mismo dia:** ver
[[2026-09-14 - Correccion de dos defectos de cocina]].

> [!bug] Marcar "lista" una comanda de domicilio responde 500
> `estaciones/views.py`, accion `lista`: el aviso al mesero se arma con
> `comanda.pedido.mesa.nombre`. En un domicilio la mesa es nula, revienta con
> `AttributeError`, y **el mesero nunca se entera de que el domicilio esta listo**.
> La tarjeta de cocina si usa `pedido.destino`; el aviso se quedo con la forma vieja.
> Anotado en [[SPEC-011 - Novedades sobre Pedidos Enviados]].

> [!bug] Dos cocineros pueden tomar la misma comanda
> `Comanda.marcar_en_preparacion` no bloquea la fila ni mira el estado previo: un
> segundo "en preparacion" responde 200. Es el mismo tipo de carrera que ya se corrigio
> en el cobro ([[ADR-008 - Bloquear la fila antes de decidir sobre dinero]]), aunque aqui
> no hay dinero de por medio. Anotado en [[SPEC-005 - Estaciones y Ruteo]].

## Criterios que siguen abiertos, y por que

| Spec | Criterio | Por que sigue abierto |
|---|---|---|
| 001 | Entrar por QR salta el hero | `/m/<codigo>` fija la mesa pero la pagina abre arriba |
| 002 | Observaciones por indice en el QR | El QR lleva el texto |
| 003 | 3 s en 4G, y uso con una mano | Solo se ha medido en local y con viewport emulado |
| 004 | Editar un pedido escaneado antes de confirmar | No existe; solo se edita despues, como novedad |
| 004 | Escaner en iPhone | La camara existe; falta un iPhone real |
| 007 | Menu de 200 platos | Sin probar con ese volumen |
| 007 / 008 | Auditoria de cambios de configuracion | El panel no guarda quien cambio que |
| 021 | Recorrido con cada rol | Lo medido fue con la sesion de administrador |
| 022 | Carrito del cliente en telefono real | Pendiente desde el 8 de septiembre |

## Lo que la revision dejo a la vista

- **Tres apps sin pruebas.** `pedidos` y `estaciones` ahora tienen el archivo de
  verificacion; `configuracion` sigue en cero.
- **La suite quedo en rojo** con las 2 pruebas de los defectos, hasta que se corrigieron.
- **No hay nada de produccion.** `docker-compose.yml` solo levanta Postgres local,
  `DEBUG` vale `True` por defecto, no hay ajustes `SECURE_*`, ni HTTPS, ni respaldos.
- **No hay plan para traer los datos de Springfield** (clientes, platos, historial) desde
  su base PHP.
- **La base de desarrollo esta llena de datos de demostracion** y usuarios de prueba
  (`walter`, `mesero`). No puede ser la semilla de produccion.

## Lo siguiente

El autor va a describir la spec de **Promociones**: combos con precio propio
("hamburguesa, perro, helado y gaseosa por 50.000"), administrables desde una pestaña del
panel, primeros y resaltados en el menu del cliente, y con su propio reporte de cuantas se
venden y cuanto dejan. No se empieza hasta tener la spec aprobada.
