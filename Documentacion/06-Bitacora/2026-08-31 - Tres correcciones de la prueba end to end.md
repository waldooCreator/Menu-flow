---
fecha: 2026-08-31
tipo: bitacora
specs: [SPEC-003, SPEC-004, SPEC-011, SPEC-013]
---

# 2026-08-31 — Tres correcciones de la prueba end to end

Probando el sistema completo aparecieron tres cosas. Se corrigieron las tres.

## 1. Editar un pedido no tenía confirmación

**Lo que pasaba:** cada toque en la pantalla de edición viajaba al servidor de
inmediato. No había "Aplicar" ni forma de revisar antes; para cerrar había que
darle a la X, como si se estuviera cancelando algo que en realidad ya se había
guardado.

**Lo que se hizo:** los cambios se acumulan en pantalla sin salir del navegador.
El pedido se ve **como quedaría**, con cada renglón marcado (`MODIFICADO`,
`SE QUITARÁ` con su Deshacer, `NUEVO`). Abajo una barra dice cuántos cambios hay
sin aplicar. "Aplicar" abre un resumen en palabras normales y solo entonces se
manda.

Dos detalles que importan:

- El sondeo automático **no pisa** una edición a medio redactar.
- Las operaciones entran en **una sola transacción**. Si la cuarta falla, no
  entra ninguna — el botón promete todo o nada, y ahora cumple.

## 2. Al cobrar no se podía elegir medio de pago

**Lo que pasaba:** la pantalla decía "no se ha seleccionado medio de pago" y la
lista estaba vacía. No era un problema de la pantalla.

**La causa:** al renombrar `MedioPago` a `Caja` (SPEC-014) quedó un segundo
cliente apuntando a `/medios-pago/`, la ruta vieja. Devolvía 404, la lista
llegaba vacía y la pantalla pedía elegir de una lista sin opciones.

**Lo que se hizo:** se eliminó el cliente duplicado. Hay uno solo — dos clientes
para el mismo recurso terminan desincronizándose, y esto fue exactamente eso.

Además, **CRUD desde el panel**: pestaña *Cobro*, donde se crean, renombran y
retiran los medios de pago. Una caja con movimientos **no se borra**, se
desactiva: su saldo es la suma de cobros que ya ocurrieron.

## 3. Las observaciones eran una sola lista para todo

**Lo que pasaba:** "sin cebolla" y "poca sal" eran una lista única y global.
Aparecían igual en una gaseosa que en una hamburguesa, y no había pantalla para
tocarlas — solo la API a mano.

**Lo que se hizo:** dos niveles (SPEC-003).

| Nivel | Dónde se edita | A qué aplica |
|---|---|---|
| General | Panel → Cobro | Todos los platos |
| Por plato | Panel → Menú → ficha del plato | Solo ese |

Un plato muestra **las generales más las suyas**. Si el texto coincide, se ve una
sola vez. Desactivar una etiqueta la quita del menú **sin tocar** las
observaciones ya escritas en pedidos pasados.

### Un fallo silencioso que apareció de paso

Al probarlo, una etiqueta creada por formulario nacía **desactivada**: existía en
la base pero no salía en ningún plato, y nada decía por qué.

La razón es una regla de HTML que DRF respeta: una casilla sin marcar no se
envía, así que un booleano ausente en un formulario se lee como `False` — no como
"usa el valor por defecto del modelo". El `default=True` del modelo nunca se
aplicaba.

Se declaró `activo` explícitamente en el serializador, en `ObservacionRapida` y
también en `Caja`, que tenía el mismo agujero: una caja nueva podía nacer
retirada del cobro.

## Comprobado

Sobre el sistema corriendo, no en teoría:

- Dos cambios en cola muestran sus marcas y el servidor sigue **sin novedades** —
  nada se mandó antes de confirmar
- Un lote con una operación inválida responde *"Cambio 2 de 2 … No se aplicó
  ninguno"* y deja el pedido intacto
- `/medios-pago/` responde 404, `/cajas/` responde 200 con los cinco medios
- Un plato sin etiquetas propias ve solo las generales; con propias, las dos
  listas; un texto repetido no se duplica
- Desactivar una general la saca del menú al instante
- Una etiqueta creada **desde el panel** aparece en el menú público del cliente
- Un medio de pago creado por formulario nace **activo**

Los datos de prueba se borraron; las cinco observaciones generales quedaron
intactas.

## Queda pendiente

- Recorrer la sección **Cajeros** del sistema de Springfield (7 secciones)
- Pantallas para APIs que ya existen: movimientos, turnos, facturas anuladas
- Los seis informes de ventas
