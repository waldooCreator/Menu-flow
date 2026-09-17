---
tipo: borrador
actualizado: 2026-08-27
tags: [borrador, presentacion, pitch]
---

# BORRADOR — Presentación del Proyecto

> [!warning] Es un borrador
> Primera pasada, sin pulir. El punto 4 (tecnología emergente) es el flojo y está
> marcado — hay que decidirlo antes de presentar esto.

## 1. Introducción

Sistema web de gestión para restaurantes que conecta al cliente, al mesero, a las
estaciones de preparación y a la administración dentro de una sola aplicación.

Nace de un caso real: un restaurante en Cúcuta que hoy opera con un sistema heredado, y
que sirve de primer cliente. El sistema se diseña desde el inicio para **venderse a varios
restaurantes**, cada uno con su propia instancia, dominio y base de datos.

## 2. Planteamiento del problema

En un restaurante pequeño o mediano, el pedido viaja por canales frágiles: papel, gritos,
memoria. Eso produce errores de cocina, platos que salen a la mesa equivocada, demoras que
nadie puede medir, y ventas que al final del día no cuadran con la caja.

**A quién afecta:** al mesero, que carga con el error; a la cocina, que trabaja sin saber
prioridades; al dueño, que no puede responder cuánto vendió ni por qué se perdió plata.

**Por qué importa:** el margen de un restaurante es estrecho. Un plato mal hecho o una
venta sin registrar se sienten de inmediato, y las soluciones del mercado suelen ser caras
o pensadas para cadenas grandes.

## 3. Solución propuesta: ¿qué tiene de innovador?

Una aplicación web donde **todo va por mensajes dentro del sistema, sin impresión**.

Lo que la diferencia:

- **QR autocontenido y firmado.** El cliente arma su pedido y genera un código que
  **lleva el pedido completo adentro**, firmado criptográficamente. No se guarda nada en
  base de datos hasta que un mesero lo valida. Elimina el pedido fantasma sin obligar al
  cliente a registrarse.
- **Ruteo automático a estaciones.** Un pedido con carne y postre se divide solo: cada
  estación ve únicamente lo suyo.
- **Novedades visibles.** Si el mesero corrige un pedido ya enviado, la cocina lo ve en
  rojo con el cambio exacto, y debe reconocerlo.
- **Historial que no se puede reescribir.** El precio se congela en la venta y los cambios
  se registran como hechos nuevos, nunca sobrescribiendo.
- **100% parametrizable.** Colores, textos, imágenes, menú y estaciones salen de
  configuración: montar otro restaurante no es tocar código.

## 4. Defensa como proyecto de tecnología emergente

> [!danger] Este punto hay que decidirlo — hoy no se sostiene bien
> El sistema usa Django, Vue, PostgreSQL y Docker: tecnología **madura y probada**, no
> emergente. Eso es una virtud de ingeniería, pero es justo lo contrario de lo que pide
> este apartado. Presentarlo como "emergente" sin más sería inflarlo.

Lo que **sí** es defendible hoy:

- **Criptografía aplicada al borde:** el QR firmado con vigencia funciona como un token
  portador — el dato viaja con el usuario y se valida sin consultar el servidor primero.
- **Arquitectura multi-instancia contenedorizada:** despliegue aislado por cliente.

Lo que **haría falta agregar** para defenderlo de verdad (hoy no existe):

- **Analítica predictiva de demanda** — pronosticar qué platos y a qué horas, para
  compras y preparación. *Nota: el sistema que vamos a reemplazar ya tiene regresión
  lineal de productos y análisis de hora/día de mayor demanda, así que el dominio lo pide.*
- Tiempo real con WebSockets (hoy es consulta periódica).

**Decisión pendiente:** o se agrega un componente predictivo real, o se reencuadra el
proyecto como *aplicación de tecnologías consolidadas a un problema desatendido*. Lo
segundo es más honesto; lo primero encaja mejor con la convocatoria.

## 5. Impacto y relevancia

- **Empresarial:** le da al dueño control de ventas y trazabilidad — quién vendió qué y
  cuándo — con un costo muy por debajo de las soluciones de cadena.
- **Social:** el mesero deja de cargar con errores que no son suyos; el trabajo se vuelve
  medible y defendible.
- **Ambiental:** elimina la impresión de comandas, que en un restaurante activo son
  decenas de tiquetes diarios.
- **Tecnológico:** modelo replicable a otros restaurantes sin desarrollo a la medida.

## 6. Retos y limitaciones

- **Adopción del personal.** Es el riesgo más grande: un mesero con prisa vuelve al papel
  si el sistema lo hace esperar. Ya guió decisiones de diseño (el sistema nunca bloquea al
  mesero), pero se prueba en servicio real, no en demo.
- **Reemplazar un sistema en producción.** El actual tiene 46 secciones; el nuevo, 6. La
  brecha está inventariada y es sobre todo de caja, reportes e inventario.
- **Dependencia de conectividad.** Sin internet en el local, no hay pedidos.
- **Migración de datos históricos** del sistema anterior.
- **Respaldo y actualización** de múltiples instancias: aún sin procedimiento definido.
- **Alcance excluido a propósito:** sin pasarela de pagos ni facturación electrónica. Si
  un cliente las exige, queda fuera.

## Enlaces

- [[Vision del Producto]]
- [[Inventario del Sistema Actual de Springfield]]
- [[Que le Falta para ser un POS Vendible]]
