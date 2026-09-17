---
tipo: spec
id: SPEC-001
estado: implementada
actualizado: 2026-09-14
tags: [qr, mesa, cliente]
---

# SPEC-001 — QR de Mesa

> [!success] Estado: Implementada — flujo del cliente y administracion completos (revisada 2026-09-14)
> Modelo `Mesa`, validacion, entrada por `/m/:codigo`, y desde 2026-08-27 el CRUD
> completo desde el panel (crear, desactivar, regenerar QR, descargar para imprimir).

## Proposito

Identificar automaticamente en que mesa esta sentado el cliente, sin que tenga que
escribir un numero.

## Alcance

- QR estatico impreso una sola vez y pegado en cada mesa
- Al escanearlo, el cliente entra al sitio con la mesa ya asociada a su sesion
- Administracion de mesas: alta, baja y regeneracion del QR

## Fuera de alcance

- Reserva de mesas
- Union de varias mesas en un mismo pedido

> [!note] Cambio de alcance (2026-08-26)
> "Estado de ocupacion de la mesa" **salio de esta lista**: ahora lo cubre
> [[SPEC-012 - Vista de Salon y Estado de Mesas]]. Se deja constancia porque durante
> meses fue una exclusion explicita de esta spec, no un olvido.

## Comportamiento

1. El administrador crea una mesa desde configuracion. El sistema genera un
   **codigo opaco aleatorio** para ella (por ejemplo `x7f2q9`), no un numero secuencial.
2. El sistema produce el QR con una URL del tipo `https://dominio.com/m/x7f2q9`.
3. El restaurante imprime ese QR y lo pega en la mesa.
4. El cliente lo escanea. El servidor resuelve el codigo contra la tabla de mesas y guarda
   la mesa en la sesion del navegador.
5. Toda la navegacion posterior (menu, carrito, generacion del QR de pedido) ya conoce la mesa.

## Reglas

- **El codigo debe ser opaco.** Si fuera `1`, `2`, `3`, cualquiera podria adivinar o
  enumerar mesas ajenas y mandar pedidos a otra mesa.
- **La entrada por QR de mesa va directo al menu**, saltandose el hero de presentacion.
  El cliente ya llego al restaurante: no necesita ver fotos del local ni como llegar.
  Ver [[Modelo de Pagina del Cliente]].
- Si el codigo no existe o esta desactivado, el sitio abre en modo normal (sin mesa) y
  avisa que debe pedirle ayuda a un mesero.

## Criterios de aceptacion

- [x] Al escanear el QR de la mesa 12, la sesion queda asociada a la mesa 12 —
      **verificado**: entrar por `/m/x7f2q9` deja "Mesa 12" fijada en el carrito
- [x] El codigo de mesa no es adivinable ni enumerable — `get_random_string(8)`, no secuencial
- [ ] La entrada por QR de mesa aterriza directamente en el menu, no en el hero —
      **no se cumple (revisado 2026-09-14)**: el hero ya existe desde el port de Fase 0
      ([[SPEC-003 - Menu del Cliente]]), pero `/m/<codigo>` solo fija la mesa; la pagina
      abre arriba, en el hero, igual que entrando sin QR
- [x] El administrador puede crear, desactivar y regenerar el QR de una mesa —
      **implementado y verificado 2026-08-27**: pestaña Mesas del panel, con el QR
      dibujado en el navegador (URL `/m/<codigo>` con el origen actual) y boton de
      descarga para imprimir. Regenerar invalida el QR impreso anterior
- [x] Un codigo de mesa inexistente no rompe la pagina: abre en modo sin mesa — por diseño
      (`if (mesa.encontrada) …`), verificado el endpoint (`{"encontrada": false}`) pero no
      recorrido en la UI en vivo
- [x] La mesa asociada aparece en el QR de pedido que genera el cliente — **verificado**:
      el pedido resuelto trae `mesa_codigo: "x7f2q9"`

## Dependencias

- [[SPEC-003 - Menu del Cliente]] — el destino del escaneo
- [[SPEC-012 - Vista de Salon y Estado de Mesas]] — el estado de ocupacion
- [[SPEC-007 - Administracion y Parametrizacion]] — donde se administran las mesas

## Notas

Este patron esta validado en produccion: **me&u** (antes Mr Yum) usa QR estaticos por mesa
con el numero incrustado desde 2021. Ver [[Analisis de Competencia]].
