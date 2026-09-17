---
tipo: bitacora
fecha: 2026-09-16
tags: [domicilios, envio, vueltos, cobro, spec-013, spec-025]
---

# 2026-09-16 — Costo de envío y vueltos

Dos correcciones pedidas por el autor tras la revisión de si el sistema está apto para
producción.

## 1. Costo de envío en domicilios

Al confirmar un pedido de domicilio en **Recibir pedido**, el mesero ve un campo **"Costo
del envío (opcional)"**. Se suma al total, como una línea fija que no cambia si se agregan
más platos después. Vacío o 0 significa domicilio gratis.

- `Cuenta.costo_envio`, nuevo campo
- Se valida antes de escribir nada (no puede ser negativo); una mesa lo ignora aunque lo
  mande
- Aparece como línea "Envío" en el detalle de la cuenta y en el tiquete

## 2. Vueltos, solo en efectivo

En **Cuentas**, al elegir un medio de pago de tipo Efectivo aparece **"¿Con cuánto pagó?
(opcional)"**: botones rápidos por billete ($10.000, $20.000, $50.000, $100.000, o el
valor exacto) y un campo manual. El vuelto se calcula al momento y se muestra: **"Vuelto:
$10.000"**, o **"Faltan $X"** si no alcanza — y en ese caso el botón de cobrar se bloquea.

- `Cuenta.recibido_efectivo` y `Cuenta.vuelto_efectivo`, nuevos campos
- Es opcional: dejarlo vacío cobra igual que antes, sin vuelto
- **No genera un movimiento de caja aparte.** Lo que entra a la caja sigue siendo el
  total; el vuelto es información para quien cobra
- Con cualquier medio que no sea Efectivo, el campo no aparece y el servidor ignora lo
  que llegue

Quedó fuera de alcance, a propósito: avisar si al turno se le acaba el sencillo (exigiría
llevar el detalle de billetes, no solo el total), un movimiento de caja separado para el
vuelto, y pagos mixtos. Ver [[SPEC-025 - Vueltos]].

## Verificación

**8 pruebas nuevas**, contra el flujo real (firmar QR, confirmar, cobrar):
`pedidos/tests.py::Spec013CostoDeEnvio` (4) y `ventas/tests.py::Spec025Vueltos` (4).

**Suite completa de `pedidos` y `ventas`: 159 de 159 en verde**, sin nada roto por el
cambio.

**Sin verificar todavía:** las tres pantallas nuevas en el navegador (el campo de envío en
Recibir pedido, los botones de vuelto en Cuentas, y las líneas nuevas del tiquete). El
frontend compila, pero no se recorrió a ojo. Falta antes de dar esto por completamente
cerrado.

## Specs

- [[SPEC-013 - La Cuenta]]: agregadas las secciones "Costo de envío" y "Vueltos", con sus
  criterios marcados
- [[SPEC-025 - Vueltos]]: pasó de borrador a implementada, con las decisiones del autor y
  lo que se dejó fuera de alcance a propósito

## Verificación en el navegador (2026-09-16, después)

Recorrido de punta a punta con la base de desarrollo: un cliente arma un domicilio real en
el menú, genera su QR de verdad (mismo camino que usaría en su teléfono), el mesero lo lee
en **Recibir pedido**, indica el costo de envío, lo cobra en **Cuentas** con un vuelto, y se
revisa el resultado en **Historial de Ventas**.

> [!bug] El servidor corría con código viejo (`--noreload`)
> El primer intento de confirmar el domicilio dio **500**: `IntegrityError, null value in
> column "costo_envio"`. No era un error de lógica — el proceso de `runserver` llevaba
> corriendo desde antes de hoy y `--noreload` significa que nunca vuelve a leer el código
> ni los modelos del disco. Se reinició el servidor y funcionó. **Hay que recordarlo cada
> vez que se cambian modelos o vistas** mientras el preview sigue abierto de una sesión
> anterior.

> [!bug] El detalle de Ventas no mostraba envío ni vuelto — corregido
> `/mesero/cuentas` sí los mostraba (usa `serializar_cuenta`), y el tiquete impreso también
> (usa `datos_tiquete`), pero **Historial de Ventas** arma su detalle a partir de la fila de
> `/api/ventas/`, que tiene su propia serialización hecha a mano en `VentasView` — nunca se
> le agregaron `envio`, `recibido_efectivo` ni `vuelto_efectivo`. Se agregaron los tres
> campos, con una prueba nueva que lo fija (`Spec025VueltosEnHistorial`).

**Con las dos correcciones, confirmado en pantalla:**
- Domicilio con envío: `Subtotal $18.000 · Propina $900 · Envío $8.000 · Total $26.900`
- Botones de billete: con total $26.900 solo aparecen $50.000 y $100.000 (los menores se
  ocultan, como está diseñado)
- Vuelto en vivo: `$50.000 → "Vuelto: $23.100"`; `$20.000 → "Faltan $6.900"` con el botón de
  cobrar deshabilitado
- Al cobrar: `"Domicilio cobrado: $26.900 · Efectivo · Vuelto: $3.100"`
- Historial de Ventas y el tiquete impreso: ambos muestran Envío y "Recibió $30.000 ·
  vuelto $3.100"

**9 pruebas en total** (las 8 de antes más `Spec025VueltosEnHistorial`), todas en verde.
