---
tipo: investigacion
actualizado: 2026-09-14
tags: [migracion, pos, springfield, comparativa, alcance]
---

# Comparativa Sidebar — Springfield vs Sistema Nuevo

> [!info] Que es esto
> Listado completo de las **48 secciones** del sidebar del sistema en produccion de
> Springfield (`springfield.linkmetric.click`), agrupadas tal como aparecen en su panel,
> con el estado de cada una en este proyecto **al 2026-09-14**.
>
> Se levanto el 2026-08-30 y se reviso completa el 2026-09-14, fila por fila, contra el
> codigo. Hasta esa fecha solo la seccion Contable estaba al dia: el resto seguia marcando
> como pendientes cosas que ya se habian construido (Clientes, los reportes, Lista de
> facturas, Medios de pago…).

## Como leer el estado

| Estado | Significa |
|---|---|
| ✅ Hecho | Existe, funciona, verificado |
| 🟡 Parcial | Existe el dato o la logica, falta pantalla o algun detalle |
| ⬜ Falta | No existe nada todavia, y si hace falta para reemplazar a Springfield |
| ❔ Por decidir | No existe, y no esta claro que haga falta: hay que confirmarlo con el restaurante |
| 🚫 Fuera de alcance | Descartado a proposito, no es un olvido |

## Meseros (5)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Ordenes | ✅ Hecho | Salon (SPEC-012) + Escaner/Pedido (SPEC-004) |
| Online | ❔ Por decidir | El cliente pide por QR y los domicilios entran por WhatsApp; no hay un panel aparte de "pedidos que llegan de la web". Falta saber si Springfield lo usa |
| Mover mesa | ✅ Hecho | Cambiar destino de un pedido (SPEC-011) |
| Pre-factura | ✅ Hecho | Ver la cuenta antes de cobrar (SPEC-013, `MeseroCuentas`) |
| Venta rapida | ✅ Hecho | Camino B con **"cobrar al finalizar"** (SPEC-004) |

## Cajeros (7)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Ingresos/gastos caja | ✅ Hecho | Registrar movimiento (SPEC-014, `MeseroCaja`) |
| Abrir o cerrar turno | ✅ Hecho | `MeseroCaja`, con cierre y base en el cajon (SPEC-020) |
| Lista de facturas | ✅ Hecho | Pantalla **Ventas**, con filtros y totales ([[SPEC-015 - Historial de Ventas]]) |
| Facturas sin cobrar | ✅ Hecho | `MeseroCuentas` (SPEC-013) |
| Movimientos de cajeros | ✅ Hecho | Pantalla **Libro de caja**, con filtros y traslados (SPEC-014) |
| Reporte de turnos | ✅ Hecho | Admin → **Turnos**, con las diferencias de cuadre |
| Clientes | ✅ Hecho | Pantalla **Clientes** ([[SPEC-019 - Clientes]]) |

## Preparacion (2)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Area de preparacion | ✅ Hecho | `EstacionTablero` (SPEC-005), con novedades en rojo (SPEC-011) y agotar platos (SPEC-017) |
| Comandas globales | 🟡 Parcial | El tablero es por estacion; el administrador puede abrir cada una, pero no hay una vista de "todas a la vez" |

## Reportes (6)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Productos mas vendidos | ✅ Hecho | Pantalla **Reportes** ([[SPEC-018 - Reportes de Venta]]) |
| Ingredientes mas usados | 🚫 Fuera de alcance | Springfield no usa recetas (ver abajo) |
| Ventas por mesero | ✅ Hecho | Reportes, atribuido a quien tomo el pedido |
| Ticket por dia | ✅ Hecho | Reportes |
| Clientes frecuentes | ✅ Hecho | Reportes, desde SPEC-019 |
| Hora/Dia demanda | ✅ Hecho | Reportes |

## Inventarios (3)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Stock global | 🚫 Fuera de alcance | Vacio en produccion (ver abajo) |
| Transacciones | 🚫 Fuera de alcance | Cero movimientos en seis años |
| Cotizador | 🚫 Fuera de alcance | Pertenece al bloque de inventario, que el restaurante no adopto |

## Marketing (1)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Enlaces de seguimiento | ❔ Por decidir | No se sabe si el restaurante los usa; hay que revisarlo antes de construir nada |

## Contable (7)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Activos liquidos | ✅ Hecho | Pantalla **Activos** ([[SPEC-020 - Activos Liquidos]]): cada caja con su saldo, el total, y el desglose efectivo/banco |
| Transacciones | ✅ Hecho | El libro de movimientos (SPEC-014) |
| Resumen operativo | 🟡 Parcial | Ventas por medio de pago esta en **Ventas**, el desglose por platillo en **Reportes** y los gastos por categoria en **Activos**; falta juntarlo en una hoja imprimible. La parte de ingredientes se descarto |
| Grafica | ✅ Hecho | Los graficos de **Reportes** (SPEC-018) |
| Ingresos/gastos tesoreria | ✅ Hecho | Registrar ingreso o gasto desde **Activos**, con categoria (SPEC-020) |
| Reporte descargable | ✅ Hecho | **Ventas**: Excel, consolidado y tiquetes (SPEC-015, [[SPEC-016 - Tiquete de Venta]]) |
| Domicilios | ⬜ Falta | Ya se sabe quien entrego, cuando, a quien y donde (SPEC-012 y SPEC-019); **falta el costo del envio**, que hoy no existe en ninguna parte |

## Restaurante (8)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Promociones | ✅ Hecho | Tipo **Promocion** en `AdminMenu`, con componentes, fechas, dias y franja; primera en el menu del cliente y con su reporte ([[SPEC-023 - Promociones]], 2026-09-14) |
| Categorias | ✅ Hecho | `AdminMenu` (SPEC-007), con estacion asociada |
| Platillos o productos | ✅ Hecho | `AdminMenu`, con subida de imagen |
| Recetas | 🚫 Fuera de alcance | Ninguno de los 43 productos de Springfield tiene receta cargada |
| Mapa de zonas | 🟡 Parcial | El Salon cubre mesas **y domicilios** (zona propia, sin tope); falta "recoger" y un mapa visual |
| Logos y fondos | ✅ Hecho | `AdminConfiguracion`, parametros de imagen |
| Visualizar menu | ✅ Hecho | `ClienteMenu` |
| Impresion de carta | 🚫 Fuera de alcance | Imprimir la carta no se hace; solo el tiquete de venta (SPEC-016) |

## Administracion (6)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Gestion de roles | ✅ Hecho | `AdminUsuarios` (SPEC-007), incluye el rol cajero (SPEC-014) y restablecer clave |
| Facturas eliminadas | ✅ Hecho | Interruptor "Ver anuladas" dentro de **Ventas** |
| Datos del establecimiento | 🟡 Parcial | NIT, logo, direccion y telefono ya son parametros y salen en el tiquete (SPEC-016); faltan **razon social** y **representante legal** |
| Restablecer | ⬜ Falta | Existe `limpiar_pedidos` por terminal; no esta en el panel |
| Configuraciones | 🟡 Parcial | Los parametros existen y estan agrupados (propina, impuesto, quien cobra…) en `AdminConfiguracion`, pero no como interruptores si/no |
| Medios de pago | ✅ Hecho | Admin → **Cobro**, con CRUD |

## Herramientas (2) e Instructivos (1)

| Sidebar de Springfield | Estado | Donde vive en este proyecto |
|---|---|---|
| Texto impresion | ✅ Hecho | El mensaje de pie del tiquete, `mensaje-pie-tiquete` (SPEC-016) |
| Software extra | ❔ Por decidir | Utilidades propias de su instalacion; probablemente no aplica |
| Seccion de videos | ❔ Por decidir | Tutoriales de su proveedor; si hicieran falta, serian material de capacitacion, no una funcion del sistema |

## El resumen

| Estado | Al 2026-09-03 | Al 2026-09-14 (con Promociones) |
|---|---|---|
| ✅ Hecho | 18 | **31** |
| 🟡 Parcial | 5 | **5** |
| ⬜ Falta | 22 | **2** |
| ❔ Por decidir | — | **4** |
| 🚫 Fuera de alcance | 3 | **6** |

> [!note] Por que cambio tanto
> No se construyeron 12 secciones en once dias. Entre el 3 y el 8 de septiembre se
> hicieron Clientes (SPEC-019), los reportes (SPEC-018), el tiquete (SPEC-016) y Activos
> (SPEC-020), y el 7 de septiembre se comprobo que Springfield no usa inventario ni recetas.
> Pero esta tabla solo se habia actualizado en la seccion Contable. La revision del
> 2026-09-14 la puso al dia completa.

### Lo que de verdad falta para reemplazar a Springfield

| Seccion | Que falta | Tamaño |
|---|---|---|
| **Domicilios** | El costo del envio: donde se cobra, a que caja entra, como sale en el tiquete | Pequeño, pero toca la cuenta |
| **Resumen operativo** | Juntar en una hoja lo que ya esta repartido en Ventas, Reportes y Activos | Pequeño: solo consultas |
| **Datos del establecimiento** | Razon social y representante legal | Muy pequeño: dos parametros |
| **Configuraciones** | Presentar los parametros si/no como interruptores | Pequeño: solo interfaz |
| **Mapa de zonas** | "Recoger en el local" y, si se quiere, un mapa visual del salon | Por definir |
| **Comandas globales** | Una vista con todas las estaciones a la vez | Pequeño |
| **Restablecer** | Llevar `limpiar_pedidos` al panel, con confirmacion fuerte | Pequeño, pero delicado |

### Lo que hay que preguntarle al restaurante

*Online*, *Enlaces de seguimiento*, *Software extra* y *Videos*. Antes de escribir una
spec conviene entrar a Springfield, en solo lectura, y ver si tienen datos: el mismo
metodo que descarto el inventario.

## Springfield NO usa inventario ni recetas (comprobado 2026-09-07)

> [!important] Esto cambio el alcance del proyecto
> Se reviso el sistema en produccion, en solo lectura. **Los cinco modulos de
> inventario y recetas existen pero estan completamente vacios.** Nunca se
> alimentaron.

| Seccion | Que se encontro |
|---|---|
| Stock global | "No se encontraron productos" — cero ingredientes cargados |
| Transacciones de inventario | Cero movimientos **en un rango de seis años** (2020–2026) |
| Recetas | "No se encontraron recetas" |
| Ingredientes mas usados | Tabla vacia |
| Composicion de recetas | 43 productos listados, **ninguno con ingredientes configurados** |

**Como se comprobo.** La pantalla de transacciones trae por defecto un rango de
los ultimos diez dias, asi que un vacio ahi no probaba nada. Se amplio el rango
a 2020–2026 por la URL (el formulario es GET, o sea solo lectura) y se verifico
que el filtro **si** quedara aplicado antes de concluir. Siguio vacio.

**Que significa.** El software trae el modulo, pero el restaurante nunca lo
adopto — algo comun, porque mantener un inventario al dia exige una disciplina
diaria que un restaurante pequeño rara vez sostiene.

Si algun dia el restaurante quiere llevar inventario de verdad, se construye
entonces — pero como funcionalidad nueva que hoy no tienen, no como requisito
para reemplazar lo que ya usan.

## Lo que no esta en esta tabla, y tambien falta

La comparativa mide pantallas. Para que el sistema **reemplace** a Springfield hace
falta ademas algo que no aparece en ningun sidebar:

- **Pasar los datos.** Clientes, platos, categorias y el historial de ventas de
  Springfield viven en su base PHP. No hay todavia ni un plan para traerlos.
- **Ponerlo en produccion.** Hoy solo corre en local: no hay configuracion de servidor,
  HTTPS ni respaldos. Ver [[SPEC-009 - Portabilidad Multi-restaurante]], que sigue sin
  probarse en un servidor real.

## Enlaces

- [[Inventario del Sistema Actual de Springfield]]
- [[Que le Falta para ser un POS Vendible]]
- [[SPEC-013 - La Cuenta]]
- [[SPEC-014 - Turno de Caja y Cajas de Fondos]]
- [[Inicio]]
