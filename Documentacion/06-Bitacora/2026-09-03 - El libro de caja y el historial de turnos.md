---
fecha: 2026-09-03
tipo: bitacora
specs: [SPEC-014]
---

# 2026-09-03 — El libro de caja y el historial de turnos

Lo que faltaba para cerrar el módulo de caja, más un hueco que apareció al
revisar el estado real antes de decir "terminado".

## El hueco: el libro no se podía leer

Al auditar qué estaba hecho y qué no, encontré esto: **se podía registrar un
ingreso o un gasto, pero no había forma de ver los que ya estaban.** La
pantalla de Caja pedía los movimientos al servidor y los usaba solo para
contar las ventas fuera de turno — nunca los mostraba.

Un libro que no se puede leer no es un libro. Y sin poder leerlo, no hay forma
de conciliar contra el banco, que es justamente para lo que existe.

No lo había notado antes porque la pantalla *parecía* completa: registrar un
movimiento funciona y da su confirmación. El hueco solo se ve si uno pregunta
"¿y dónde veo los de ayer?".

## Libro de caja

Pantalla nueva, `/mesero/libro`, para quien pueda cobrar.

- Movimientos **agrupados por día**, con hora, caja, responsable y el monto en
  verde o rojo según entre o salga
- **Filtros** por rango de fechas, caja y tipo, más un atajo de "Hoy"
- Marca las ventas **fuera de turno**, que ya se contaban pero no se veían

### Los totales son del rango, no de la página

Detalle que importa: el tope de 300 filas se aplica **después** de filtrar y de
sumar. Si los totales se calcularan sobre lo que cabe en pantalla, conciliar
contra el banco daría un número distinto según cuánto se alcanzara a mostrar —
peor que no tener totales.

Cuando hay más movimientos que filas mostradas, la pantalla lo dice
explícitamente y sugiere filtrar por fechas.

### Traslado entre cajas

Vive en el libro porque es la operación legítima para mover plata sin
reescribir nada (SPEC-014, regla 3: los movimientos no se editan ni se borran).

Deja **dos movimientos** — uno que sale del origen, otro que entra al destino —
y por eso **no cambia el neto del libro**: la plata cambia de bolsa, no entra
ni sale del negocio. Los dos saldos sí cambian, y quedan bien solos.

**Cambió el permiso:** antes era `IsAdminUser`. Ahora lo hace cualquiera que
pueda cobrar. Consignar el efectivo es tarea de caja del día a día; exigir un
administrador para registrarlo llevaría a que se haga sin registrar, que es
peor. Los dos movimientos guardan su autor, así que quién lo hizo siempre se
sabe.

## Historial de turnos

Pantalla aparte, en el **panel de administración** (`/admin/turnos`), con la
lista de turnos pasados, su cuadre y su diferencia — más un filtro para ver
solo los que no cuadraron, y un contador arriba ("3 turnos · 2 sin cuadrar")
que es lo primero que busca un dueño.

Está en admin y no en Caja a propósito: al revisar el sistema de Springfield,
"Reporte de turnos" es la **única** sección de Cajeros que su rol `cajero` no
ve. La razón es buena y se copia — quien maneja la plata no audita su propio
cuadre.

## Comprobado

Por API y con clics reales en la pantalla:

- Filtro por tipo: solo egresos → entró $0, salió $32.000
- Filtro por caja: solo Nequi → 1 fila, $45.000
- Rango de fechas vacío (enero 2020) → "Nada en ese rango", totales en cero
- Traslado desde la pantalla: Efectivo $3.200 → $200, Nequi $45.000 → $48.000,
  y **el neto quedó igual** ($334.400 antes y después)
- Traslado a la misma caja → rechazado
- Historial: "3 turnos · 2 sin cuadrar", con "Faltó $6.000" y "Faltó $200" en
  rojo, y el filtro dejando solo esos dos

**27 tests** en `ventas/tests.py`, todos en verde — 7 de concurrencia, 13 de
turno, 7 nuevos del libro.

Los datos de prueba quedaron borrados y los saldos volvieron a como estaban
antes de empezar (Efectivo $35.200, Bancolombia $266.200).

## Con esto, caja queda

| | |
|---|---|
| Abrir turno a nombre de un mesero, con fondo por caja | ✅ |
| Cerrar turno propio y ajeno con motivo | ✅ |
| Cuadre y aviso de turnos viejos | ✅ |
| Registrar ingreso o gasto | ✅ |
| **Ver el libro con filtros y totales** | ✅ |
| **Traslado entre cajas** | ✅ |
| **Historial de turnos (admin)** | ✅ |
| Cobrar eligiendo medio de pago | ✅ |
| Venta rápida con cobrar al finalizar | ✅ |
| CRUD de medios de pago | ✅ |

## Lo que sigue

1. **Lista de facturas** — todas las ventas con filtros por fecha, tipo, medio
   y estado. Es la que más pide un dueño, y no existe.
2. **Clientes** — con campo de observaciones desde el primer día (en
   Springfield el personal escribe "pago nequi" en el campo de teléfono porque
   no hay dónde anotar). Es la única que necesita modelo nuevo.
