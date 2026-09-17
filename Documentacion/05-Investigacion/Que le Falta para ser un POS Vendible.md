---
tipo: investigacion
actualizado: 2026-08-27
tags: [pos, ventas, caja, meseros, cocina, producto]
---

# Que le Falta para ser un POS Vendible

> [!info] Que es esto
> Estudio pedido por el autor (2026-08-27): que necesita un POS **basico** —
> explicitamente **no** de nivel profesional/empresarial— para control de ventas, meseros y
> cocina; y que falta para venderlo a varios restaurantes.
>
> Todo lo de aqui se verifico leyendo el codigo, no de memoria.

## Lo primero, porque cambia el orden de todo lo demas

> [!danger] Un restaurante que compre esto hoy no puede agregar un plato
> El panel de administracion **solo edita `Parametro`** (colores, textos, imagenes). El
> menu, las mesas, las estaciones y los usuarios se crean **con comandos de management**
> desde la terminal del servidor.
>
> Eso no es una funcion pendiente: es la diferencia entre un demo y un producto. Sin ello,
> cada cambio de carta obliga a que alguien con acceso al servidor lo haga a mano.

Todo lo demas de este documento vale menos que resolver esto.

## 1. Control de ventas

Hoy **no existe ninguno**: cero endpoints de reportes, cero registro de cobro.

### 1.1 Registrar el cobro (lo minimo, y no contradice el alcance)

El autor descarto **pasarela de pagos** y **facturacion electronica**. Correcto y sigue en
pie. Pero *registrar que el pedido se pago y con que medio* **no es ninguna de las dos
cosas**: es la unica forma de saber cuanto dinero deberia haber en la caja al cerrar.

Lo minimo: al entregar, marcar **pagado** y con que — efectivo, transferencia (Nequi,
Daviplata), tarjeta. Nada mas. Sin pasarela, sin DIAN, sin factura.

Sin esto, "control de ventas" no existe: el sistema sabe que se pidio, no que se cobro.

### 1.2 La cuenta de la mesa

Hoy cada pedido es una isla. Una mesa que pide entrada, despues otra ronda y despues postre
genera **tres pedidos sueltos** y nadie puede ver el total de esa mesa.

Hace falta agrupar los pedidos de una visita y poder ver **cuanto va**.

> Esto ya lo habia adelantado [[SPEC-012 - Vista de Salon y Estado de Mesas]] al hablar de
> "visita": el mismo concepto sirve para la cuenta y para la rotacion de mesas.

### 1.3 Cierre de turno / caja

Al final del dia alguien tiene que poder ver: cuanto se vendio, cuanto en efectivo, cuanto
por transferencia, cuantos pedidos, cuanto se anulo. Un solo boton y una sola pantalla.

Sin esto el duenño no tiene como cuadrar la caja, que es la razon por la que un restaurante
compra un POS.

### 1.4 Anular con motivo

> [!warning] Ya es regla obligatoria y no tiene implementacion
> `Pedido.ANULADO` y `motivo_anulacion` existen en el modelo **desde el principio**, y
> **no hay ningun endpoint que los use**. La Regla de [[SPEC-008 - Contabilidad y Auditoria]]
> ("los pedidos no se borran, se anulan con motivo y responsable") esta escrita y no
> construida.
>
> Es barato: el modelo `Novedad` de [[ADR-007 - Una novedad es un evento, no una modificacion]]
> ya es el cimiento. Es el siguiente usuario natural.

### 1.5 Impuesto y propina

Dos cosas que en Colombia aparecen en toda cuenta de restaurante y que hoy no existen:

- **Impuesto al consumo** — el porcentaje debe salir de configuracion, nunca del codigo,
  porque cambia por normativa y puede variar entre clientes
- **Propina sugerida** — voluntaria por ley, y por eso mismo el sistema tiene que poder
  mostrarla **y quitarla**. Un porcentaje configurable, que el cliente pueda rechazar

### 1.6 Reportes minimos

No hace falta un tablero de analitica. Con tres numeros por rango de fechas alcanza:

| Reporte | Para que |
|---|---|
| Ventas por dia | Cuadrar caja, comparar dias |
| Platos mas vendidos | Que reforzar y que quitar de la carta |
| Ventas por mesero | Desempeño, y base de las propinas |

Los tiempos de preparacion y entrega **ya salen gratis** de los timestamps de
[[ADR-004 - LISTO y ENTREGADO son estados distintos]]: el dato esta, falta la pantalla.

## 2. Manejo de meseros

| Falta | Por que importa |
|---|---|
| **Turnos** — quien estaba trabajando y desde cuando | Sin esto no hay a quien atribuirle la caja de la noche, ni como repartir propinas |
| **Ventas por mesero** | El dato ya existe (`Pedido.mesero`); falta la consulta |
| **Propinas por mesero** | Depende de 1.5 y de turnos |

Lo que **no** hace falta a este nivel: comisiones, evaluaciones de desempeño, horarios y
planillas. Eso es nomina, otro producto.

## 3. Cocina

Lo grueso ya esta (tablero, estados, cronometro que envejece, novedades en rojo). Falta:

| Falta | Nota |
|---|---|
| **Agotado / "86"** | El evento mas comun de una cocina real. Ya analizado en [[Novedades sobre Pedidos en Curso]] (B-7); exige que `Notificacion` pueda apuntar a una estacion, no solo a un mesero |
| **Aviso sonoro** al entrar comanda nueva | [[SPEC-005 - Estaciones y Ruteo]] ya lo pide y sigue pendiente. En una cocina con ruido, el color no basta |
| **Estacion por usuario** | Hoy quien entra **elige** la estacion de una lista: el de postres puede abrir el tablero del bar. No es grave, pero es una separacion de roles a medias |
| **Umbrales del cronometro configurables** | Hoy 10/20 min fijos en codigo. SPEC-005 pedia que fueran configurables |

## 4. Para venderlo a varios restaurantes

La parte que el autor pidio breve.

### 4.1 El panel de administracion (bloqueante)

Ya dicho arriba. Sin CRUD de **menu, mesas, estaciones y usuarios** desde el panel, el
producto no se puede entregar. Es el trabajo mas grande y el mas importante.

### 4.2 La moneda esta escrita a mano

> [!bug] Contra la regla del propio proyecto
> `new Intl.NumberFormat("es-CO", { currency: "COP" })` aparece **escrito a mano en cinco
> archivos** del frontend: `CarritoPanel`, `ClienteMenu`, `MeseroEscaner`, `MeseroPedido`
> y `MeseroPedidos`.
>
> `CLAUDE.md` dice: *"ningun color, texto o valor de negocio escrito a mano en el codigo"*.
> Hoy no molesta porque todos los clientes son colombianos; el dia que no lo sean, son
> cinco archivos y no una fila de configuracion.

### 4.3 Alta de un restaurante nuevo

Hoy poner en marcha una instancia es: crear base, migrar, correr cuatro comandos de
siembra, crear usuarios a mano. Deberia ser **un comando** que deje el sistema listo y
vacio, con un administrador y nada mas.

### 4.4 Respaldo y actualizacion

- **Respaldo**: no hay ninguno definido. Un restaurante que pierda su base pierde su
  historial de ventas. Es lo primero que pregunta un cliente serio
- **Actualizar**: con N instancias en el VPS, no hay procedimiento escrito para subir una
  version nueva a todas

### 4.5 Impuestos y textos legales por restaurante

El porcentaje de impuesto, el de propina y los datos del establecimiento (NIT, razon
social) tienen que ser configuracion. Hoy no existen.

## Lo que NO recomiendo meter

Para que "basico" siga siendo basico, dejaria fuera: inventario y control de insumos,
compras y proveedores, nomina, fidelizacion y puntos, reservas, integracion con
domiciliarios (Rappi/Didi), multi-sede bajo una misma instancia, y contabilidad formal.

Todo eso es otro producto, o el mismo dentro de dos años.

## Orden que propongo

| # | Que | Por que ahi |
|---|---|---|
| 1 | **CRUD del panel** (menu, mesas, estaciones, usuarios) | Sin esto no hay producto que vender |
| 2 | **Anular con motivo** | Ya es regla obligatoria, no tiene endpoint, y el cimiento (`Novedad`) ya existe |
| 3 | **Registrar el cobro** (pagado + medio) | Es lo que convierte "pedidos" en "ventas" |
| 4 | **Cuenta por mesa (visita)** | Da el total de la mesa y, gratis, la rotacion |
| 5 | **Cierre de turno + los tres reportes** | La razon por la que se compra un POS |
| 6 | **Impuesto y propina configurables** | Aparecen en toda cuenta real |
| 7 | **Agotado / "86"** | El evento mas frecuente de la cocina |
| 8 | **Moneda a configuracion · alta en un comando · respaldo** | Deuda de multi-restaurante |

## Enlaces

- [[SPEC-008 - Contabilidad y Auditoria]]
- [[SPEC-007 - Administracion y Parametrizacion]]
- [[SPEC-009 - Portabilidad Multi-restaurante]]
- [[SPEC-012 - Vista de Salon y Estado de Mesas]]
- [[Novedades sobre Pedidos en Curso]]
- [[ADR-007 - Una novedad es un evento, no una modificacion]]
- [[Inicio]]
