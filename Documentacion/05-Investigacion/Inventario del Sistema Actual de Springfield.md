---
tipo: investigacion
actualizado: 2026-08-27
tags: [migracion, pos, springfield, competencia, alcance]
---

# Inventario del Sistema Actual de Springfield

> [!info] Que es esto
> Springfield **ya usa un sistema en produccion** (`springfield.linkmetric.click`, PHP).
> Este proyecto lo va a reemplazar, asi que tiene que cubrir lo que ese ya hace.
>
> Recorrido de solo lectura hecho el 2026-08-27 con la sesion del autor. **No se creo,
> edito ni elimino nada.** Se anotan funcionalidades y estructura, nunca datos de clientes.

> [!danger] Paginas que NO se abrieron, a proposito
> - **`limpiar_base_de_datos.php`** (seccion "Restablecer") — el nombre habla solo
> - `crear_transacciones_caja.php`, `seleccion_confirmacion.php` (venta rapida) y
>   `verificar_turno_caja_abrir_o_cerrar.php` — crean movimientos o abren/cierran turnos
>   de caja **reales**
> - Ningun boton de Eliminar / Editar / Guardar dentro de las secciones
>
> En una app PHP de este estilo el borrado suele ser un enlace GET simple. Explorar todo
> a ciegas habria sido borrar datos de produccion.

## Tamaño de lo que hay que igualar

**46 secciones** en 11 areas, sobre **59 paginas PHP**. Para comparar: el sistema nuevo
tiene hoy 6 pantallas.

| Area | Secciones |
|---|---|
| Meseros | Ordenes · Online · Mover mesa · Pre-factura |
| Cajeros | Venta rapida · Ingresos/gastos caja · Abrir o cerrar turno · Lista de facturas · Facturas sin cobrar · Movimientos de cajeros · Reporte de turnos · Clientes |
| Preparacion | Area de preparacion · Comandas globales |
| Reportes | Productos mas vendidos · Ingredientes mas usados · Ventas por mesero · Ticket por dia · Clientes frecuentes · Hora/Dia demanda |
| Inventarios | Stock global · Transacciones · Cotizador |
| Marketing | Enlaces de seguimiento |
| Contable | Activos liquidos · Transacciones · Resumen operativo · Grafica · Ingresos/gastos tesoreria · Reporte descargable · Domicilios |
| Restaurante | Promociones · Categorias · Platillos o productos · Recetas · Mapa de zonas · Logos y fondos · Visualizar menu · Impresion de carta |
| Administracion | Gestion de roles · Facturas eliminadas · Datos del establecimiento · Restablecer · Configuraciones · Medios de pago |
| Herramientas | Texto impresion · Software extra |
| Instructivos | Seccion de videos |

## Los seis conceptos que le faltan al proyecto nuevo

No son pantallas sueltas: son **ideas del modelo de datos** que hoy no existen, y de las
que cuelga casi todo lo demas.

### 1. Zonas, no solo mesas

El sistema actual no tiene "mesas": tiene **zonas con puestos numerados**.

- **ZONA MESA** — 18 puestos
- **ZONA DOMICILIO** — 10 puestos
- **ZONA RECOGER** — 6 puestos

Un domicilio **ocupa un puesto de la zona DOMICILIO** mientras esta en curso. Es la
solucion al problema que el proyecto nuevo resolvio quitandole la mesa al domicilio: aqui
se resuelve al reves, dandole su propia zona.

Cada puesto muestra **libre** o **el total acumulado** ($100.000, $50.000…). Es decir: la
cuenta de la mesa se ve desde el mapa, sin entrar.

### 2. La cuenta (factura), distinta del pedido

El sistema nuevo tiene pedidos sueltos. Este tiene **facturas** que agrupan consumo y
tienen estado **Abierta / Cerrada**. De ahi salen:

- "Facturas sin cobrar" — lo que se sirvio y no se ha pagado
- "Pre-factura" — la cuenta antes de cobrar
- "Lista de facturas" — historico
- "Facturas eliminadas" — auditoria de lo anulado

> Columnas reales de una factura: `N° · Fecha · Mesas · Total · Tipo de pago · Cliente ·
> Direccion · Estatus · Turno · Mesero · Domiciliario · Propina`

### 3. Turno de caja

Todo movimiento cuelga de un turno. Campos reales:

`ID · Fecha Inicio · Fecha Fin · Email · Cajero · Caja · Estado · Efectivo Inicial ·
Efectivo Final · Obs. Inicio · Obs. Fin`

Sin esto no hay cuadre de caja, que es la razon por la que un restaurante compra un POS.

### 4. Medios de pago configurables

Los que Springfield usa hoy: **EFECTIVO · NEQUI · DAVIPLATA · BANCOLOMBIA · DATAFONO ·
CREDITOS PENDIENTES · RAPPI · DIDI FOOD**.

Dos cosas que revela esa lista:

- **Las plataformas de domicilio son un medio de pago**, no una integracion
- **"Creditos pendientes"** existe: se fia. El sistema lo contempla

### 5. Cliente con historial y puntos

`NOMBRE · EMAIL · TELEFONO · DIRECCION · TOTAL COMPRAS · PUNTOS`

Hay fidelizacion por puntos y un reporte de "clientes frecuentes". El proyecto nuevo no
tiene entidad cliente en absoluto.

### 6. Recetas e inventario por ingrediente

Cada platillo tiene **receta** (ingredientes y cantidades). De ahi salen "ingredientes mas
usados", "ingredientes gastados" en el resumen operativo, y el descuento de stock. Es el
puente entre vender un plato y consumir insumos.

## Lo que el sistema actual hace y el nuevo no

### Meseros

| Seccion | Estado en el proyecto nuevo |
|---|---|
| Ordenes (mapa de zonas con total por puesto) | **Parcial** — hay salon con estados, pero sin total acumulado ni zonas |
| Online (pedidos del menu web directo) | **Falta** |
| Mover mesa | **Hecho** (SPEC-011, cambio de destino) |
| Pre-factura | **Falta** |

### Cajeros — el area completa falta

Venta rapida · Ingresos/gastos de caja · Abrir/cerrar turno · Lista de facturas · Facturas
sin cobrar · Movimientos de cajeros · Reporte de turnos · Clientes.

**Ni una sola existe.** Es el hueco mas grande del proyecto.

### Preparacion

El tablero existe en ambos. El actual muestra por comanda: zona+numero, N° de orden,
mesero, fecha/hora, items con observaciones, **total**, y acciones **Imprimir · Eliminar ·
Editar**.

Diferencias con el nuevo: no tiene **total en la comanda** ni **impresion** (descartada por
decision del proyecto). Editar y eliminar ya existen via SPEC-011.

### Reportes — el area completa falta

Productos mas vendidos · Ingredientes mas usados · **Ventas y propinas por mesero** ·
Ticket por dia · Clientes frecuentes · **Hora/Dia de mayor demanda**.

El "Resumen de Ventas" agrupa por dia con `Tickets: N · Total: $X`, filtrable por tipo de
venta y estatus.

### Inventarios — el area completa falta

Stock global · Transacciones de inventario · Cotizador · productos maximos y minimos.

### Contable — el area completa falta

Activos liquidos · Transacciones · **Resumen operativo** · Graficas · Ingresos/gastos de
tesoreria · Reporte descargable · Estatus de domicilios con costo.

El **Resumen operativo** es la pantalla mas densa del sistema: total de ventas desglosado
por medio de pago, propinas, detalle de ingresos y gastos, cruce de informacion, resumen
por platillo e ingredientes gastados. Todo por rango de fechas y con boton de imprimir.

### Restaurante (carta)

| Seccion | Estado |
|---|---|
| Categorias con **posicion**, **visibilidad** y **horario** | **Parcial** — hay categorias con orden, sin visibilidad ni franja horaria |
| Platillos (42 productos) | **Hecho** (API), falta el panel |
| **Promociones** | **Falta** |
| **Recetas** | **Falta** |
| Mapa de zonas | **Parcial** — salon sin zonas |
| Logos y fondos | **Hecho** (parametros) |
| Visualizar menu / Impresion de carta | **Parcial** — hay menu web, no impresion |

> **Categorias con horario** es una idea que vale la pena robar: "desayunos" visible solo
> de 6 a 11. Hoy el proyecto nuevo no puede hacerlo.

### Administracion

| Seccion | Estado |
|---|---|
| Gestion de roles | **Hecho hoy** (usuarios + roles desde la API) |
| **Facturas eliminadas** (auditoria: quien, cuando, motivo) | **Falta** — y coincide con la Regla 2 de [[SPEC-008 - Contabilidad y Auditoria]] |
| **Datos del establecimiento** | **Falta** — `Nombre · NIT · Direccion · Ciudad · Pais · Telefono · Correo · Regimen Fiscal · Representante · Eslogan · Instagram · TikTok` |
| **Medios de pago** | **Falta** |
| Configuraciones | **Parcial** — ver abajo |

## Las 16 configuraciones del sistema actual

Esto es lo que un restaurante real necesita poder prender y apagar. Ninguna existe hoy:

| Interruptor | Que hace |
|---|---|
| Visibilidad menu online | Publica o cierra el menu al publico |
| **Porcentaje de propina** | El % que se aplica a las facturas |
| Nota pedidos online | Aviso visible en el menu web |
| Alimentos en reporte de turnos | Mostrar platillos vendidos en el turno |
| Domicilio en balance | Si el monto del domicilio entra a los balances |
| Domicilio en menu online | Obligar a elegir zona de domicilio |
| Eliminar comanda al cerrar pedido | Limpieza automatica del tablero |
| **Enviar pedidos online directo a cocina** | Saltarse la confirmacion humana |
| Colocar cliente en comanda | Mostrar el nombre en cocina |
| Calculos de saldos manuales | Modo de cuadre |
| Propinas automaticas | Aplicar propina sin preguntar |
| Deshabilitar carrito en menu online | Menu solo de consulta |
| Impresion automatica de comandas | — |
| Unificar comanda antigua al agregar | Si un plato agregado crea comanda nueva o se suma |
| Incluir valor total en comanda | — |
| Tamaño de letra de comandas | — |

> [!note] "Enviar pedidos online directo a cocina" contradice ADR-002
> El proyecto nuevo exige que **siempre** confirme un mesero
> ([[ADR-002 - El mesero confirma el pedido]]). El sistema actual lo deja como
> **interruptor**. Si Springfield lo tiene encendido, hay que decidir: o se respeta ADR-002
> y se les cambia la costumbre, o ADR-002 pasa a ser configurable. **Es una decision de
> producto pendiente**, no un detalle.

## Diferencias de fondo que hay que resolver antes de migrar

1. **Impresion.** El sistema actual imprime comandas y carta, y tiene seccion de "texto de
   impresion" y tamaño de letra. El proyecto nuevo **descarto imprimir** por decision
   explicita. Springfield hoy imprime: hay que confirmar si aceptan dejar de hacerlo.
2. **Confirmacion del mesero.** Ver el aviso de arriba.
3. **Facturacion.** El actual maneja "facturas" con NIT y regimen fiscal, aunque no se vio
   emision electronica. El nuevo descarto facturacion. Hay que precisar hasta donde llega
   lo que ellos llaman factura.
4. **Domicilios propios.** El actual tiene domiciliario asignado y costo de domicilio. El
   nuevo dejo la direccion viviendo solo en WhatsApp ([[SPEC-002 - QR de Pedido]]).
5. **Sin QR de mesa.** El sistema actual **no usa QR**: el mesero abre la orden desde el
   mapa de zonas. El QR es una ventaja del proyecto nuevo, no una paridad — pero el flujo
   de "mesero arma el pedido" tiene que ser igual de rapido que el de ellos.

## Orden sugerido para poder reemplazarlo

| # | Bloque | Por que |
|---|---|---|
| 1 | **Cuenta/factura con estado Abierta/Cerrada** | Todo lo demas cuelga de aqui |
| 2 | **Turno de caja + medios de pago** | Sin cuadre no hay POS |
| 3 | **Zonas (mesa/domicilio/recoger) con total por puesto** | Es como ellos trabajan hoy |
| 4 | **Panel de carta**: categorias con horario, platillos, promociones | Lo que el restaurante toca a diario |
| 5 | **Reportes**: ventas por dia, por mesero con propina, mas vendidos | Lo que mira el dueño |
| 6 | **Clientes** con historial | Base de domicilios y fidelizacion |
| 7 | **Datos del establecimiento + configuraciones** | Multi-restaurante |
| 8 | **Recetas e inventario** | El bloque mas grande; se puede dejar de ultimo |
| 9 | Marketing, cotizador, instructivos | Accesorios |

## Lo que el proyecto nuevo ya hace mejor

Para no perderlo de vista al migrar: QR de mesa y de pedido firmado, ruteo automatico por
estacion, novedades en rojo con historial de solo insercion, precio congelado en la venta,
salon con deshacer, y diseño movil real.

## Enlaces

- [[Que le Falta para ser un POS Vendible]]
- [[SPEC-008 - Contabilidad y Auditoria]]
- [[SPEC-012 - Vista de Salon y Estado de Mesas]]
- [[ADR-002 - El mesero confirma el pedido]]
- [[Analisis de Competencia]]
- [[Inicio]]
