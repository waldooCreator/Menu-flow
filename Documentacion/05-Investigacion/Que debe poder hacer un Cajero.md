---
tipo: investigacion
fecha: 2026-09-03
fuente: springfield.linkmetric.click (produccion, solo lectura)
specs: [SPEC-013, SPEC-014]
---

# Qué debe poder hacer un cajero

Catálogo levantado del sistema real de Springfield, en producción y **sin tocar
nada**: solo abrir pantallas y leer.

El panel declara en su propio código qué roles ven cada sección
(`visible: ['cajero', 'jefe', 'administrador']`), así que esta lista no es una
suposición sobre lo que "parece" de cajero: es la regla que el sistema aplica.

Roles del sistema viejo: `mesero`, `cajero`, `jefe`, `administrador`,
`desarrollador`.

## Lo propio del cajero (sección Cajeros)

| Qué | Para qué | En nuestro sistema |
|---|---|---|
| **Abrir o cerrar turno** | Empieza y cierra la jornada de caja | ✅ API (SPEC-014) · ❌ sin pantalla |
| **Venta rápida** | Vender de mostrador sin mesa | ✅ Camino B con «cobrar al finalizar» |
| **Ingresos/gastos caja** | Plata que entra o sale sin ser venta | ✅ API · ❌ sin pantalla |
| **Lista de facturas** | Todas las ventas, con filtros y totales | ❌ no existe |
| **Facturas sin cobrar** | Lo servido y todavía no pagado | ⚠️ parcial: `MeseroCuentas` lista abiertas, sin filtros |
| **Movimientos de cajeros** | Libro de movimientos por turno y responsable | ✅ API · ❌ sin pantalla |
| **Clientes** | Directorio con total de compras y puntos | ❌ no existe |
| ~~Reporte de turnos~~ | Historial de turnos y cuadres | **No es del cajero**: solo jefe y administrador |

> [!note] El cajero no ve el reporte de turnos
> Tiene sentido y conviene copiarlo: quien maneja la plata no audita su propio
> cuadre. Nuestro `cuadre_de()` ya existe, pero al construir la pantalla hay que
> respetar esta separación.

## Lo que además puede hacer (otras secciones)

El cajero de Springfield **no está encerrado en la caja**. También ve:

- **De meseros:** Órdenes, Online, Mover mesa, Pre-factura
- **De preparación:** Área de preparación, Comandas globales
- **De inventarios:** Stock global, Transacciones
- **De contable:** Ingresos/gastos tesorería
- **Del restaurante:** Promociones, Categorías, Platillos, Recetas, Ver menú,
  Impresión de carta
- **Herramientas:** Texto de impresión, Software extra, Videos instructivos

> [!warning] Esto es más permiso del que un cajero necesita
> Que un cajero pueda **editar platillos, precios, recetas y promociones** es
> mucho poder para quien maneja el dinero: puede cambiar un precio, cobrarlo y
> devolverlo. No lo copiamos por inercia. Lo razonable es que **vea** el menú
> y **no** lo edite.

## Hallazgos que cambian cómo construimos lo nuestro

### 1. El turno abre con fondo por CADA medio de pago

El formulario de apertura pide fondo inicial para los ocho: EFECTIVO,
BANCOLOMBIA, CREDITOS PENDIENTES, DATAFONO, DAVIPLATA, DIDI FOOD, NEQUI, RAPPI.

Lo nuestro solo acepta fondo en efectivo. Hay que ampliarlo.

### 2. RAPPI y DIDI FOOD son medios de pago, no un módulo aparte

Las plataformas de domicilio se tratan como una caja más. Es una solución
sencilla y honesta: lo que entra por Rappi se acumula en su propia bolsa y se
concilia contra lo que Rappi consigna. Nuestro modelo de `Caja` ya lo permite
sin cambiar nada.

### 3. Los saldos son MANUALES — nosotros hicimos lo contrario

La pantalla de activos líquidos dice literalmente **«BALANCE CAJAS (MANUAL)»**,
con $440.002.600 repartidos en ocho cajas.

Es exactamente lo que SPEC-014 decidió no hacer: nuestro saldo **se deriva** de
la suma de movimientos. Un número guardado que se va incrementando puede
desincronizarse, y cuando pasa no hay forma de saber dónde se rompió. Aquí
conviene mantener nuestra decisión y no acoplarnos.

### 4. Los movimientos de caja se pueden BORRAR

La pantalla dice «Haz click para eliminar».

Choca de frente con [[ADR-007 - Una novedad es un evento, no una modificacion]]:
para nosotros el libro es solo-inserción y una corrección es un movimiento
contrario, no un borrado. Diferencia deliberada, y a favor nuestro.

### 5. Hay turnos abiertos desde hace semanas

En el reporte: turno 213 abierto el **2026-08-26**, turno 190 abierto el
**2026-08-07**. Ambos siguen en estado `abierto` hoy, 2026-09-03.

Nadie los cerró y el sistema no avisa. Nuestro `UniqueConstraint` de un turno
abierto por persona impide abrir otro encima — bueno para la integridad, pero
significa que **esa persona queda trabada** hasta que alguien cierre el viejo.
Hace falta que el administrador pueda cerrar un turno ajeno, y un aviso de
turnos abiertos de días anteriores.

### 6. El turno tiene una columna «Caja»

Todos los turnos del reporte dicen `Caja 1`. Es un número de caja registradora
física, distinto de las «cajas de fondos» (que son los medios de pago). Con una
sola caja física nunca se nota. Queda anotado: si un restaurante tuviera dos
puntos de cobro, haría falta.

### 7. El personal usa el teléfono del cliente como campo de notas

En el directorio de clientes, la columna TELÉFONO tiene valores como
`pago nequi`, `paga efectivo`, `25k trasnferencia y`.

No es descuido: es que **necesitan anotar algo y no hay dónde**. Si hacemos la
sección de clientes, tiene que traer un campo de observaciones desde el primer
día, o pasará lo mismo.

### 8. Los movimientos exigen turno abierto

`movimientos_caja.php` redirige al panel cuando se entra sin turno abierto
(comprobado: responde con redirección a `tableroadmin.php`).

Nuestra decisión fue la contraria — se registra igual y queda marcado «fuera de
turno», porque cobrar nunca se bloquea. Vale la pena mantenerla, pero sabiendo
que el personal viene acostumbrado a lo otro.

## Qué falta construir, en orden

1. **Pantalla de turno** — abrir con fondo por caja, cerrar con conteo, ver cuadre
2. **Pantalla de movimientos** — ingresos y gastos del turno (la API ya está)
3. **Lista de facturas** — ventas con filtros por fecha, tipo, medio y estado
4. **Reporte de turnos** — historial y cuadres, **solo para admin**
5. **Cerrar turno ajeno** (admin) y aviso de turnos viejos abiertos
6. **Fondo inicial por caja**, no solo efectivo
7. **Clientes** — con campo de observaciones desde el principio

No entra: borrar movimientos, saldos manuales, ni dejar que el cajero edite el
menú.
