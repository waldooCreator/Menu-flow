---
tipo: spec
id: SPEC-003
estado: implementada
actualizado: 2026-09-14
tags: [cliente, menu, frontend]
---

# SPEC-003 — Menu del Cliente

> [!success] Estado: Implementada (2026-08-25) — revisada 2026-09-14
> El diseño de Fase 0 (`/prototipo`) esta portado a Vue con Tailwind en
> `frontend/src/views/ClienteMenu.vue` y `components/CarritoPanel.vue`, consumiendo la API
> real. Hero con parallax, filtros pegajosos con scroll-spy, entrada lateral, tarjetas
> ricas, "Encuentranos" y responsive — todo verificado. Ver [[Sistema de Diseno]].

## Proposito

Que el cliente pueda ver todo el menu con filtros e imagenes, y armar su pedido comodamente
desde su telefono.

## Alcance

- Pagina publica del restaurante: hero, menu, seccion "Encuentranos"
- Navegacion del menu con filtros por categoria
- Carrito y armado del pedido
- Generacion del [[SPEC-002 - QR de Pedido|QR de pedido]]

## Fuera de alcance

- Autenticacion del cliente (es anonimo)
- Pagos
- Historial de pedidos del cliente

## Comportamiento

Ver [[Modelo de Pagina del Cliente]] para la estructura visual completa y
[[Sistema de Diseno]] para los tokens.

### Estructura

1. **Hero** con imagen de fondo y parallax, que se oculta dinamicamente al bajar
2. **Filtros** de categoria, pegajosos bajo la barra superior
3. **Menu** en rejilla (escritorio) o lista (movil)
4. **Encuentranos** al final: fotos del local, direccion, horarios, mapa, contacto

### Reglas de la ficha de plato

- Foto **cuadrada 1:1**, radio 20px
- La descripcion es la **lista completa de ingredientes**, no una frase publicitaria
- Alergenos visibles
- Metricas por plato (calorias, porciones, tiempo, segun aplique)
- Respaldo digno cuando el plato no tiene foto: inicial sobre color de marca
- Los platos agotados se muestran en gris con etiqueta, **no se ocultan**

Desde SPEC-017 la disponibilidad se refresca al volver a la pestaña y cada 60 segundos.
Si un plato del carrito se agota, se marca alli y se bloquea la generacion del QR hasta
retirarlo.

### Observaciones del cliente

Botones predefinidos ("sin cebolla", "termino medio") **mas** un campo libre corto.
Los botones dan datos limpios para las estaciones y mantienen el QR pequeno.
La lista de botones es **configurable por restaurante**
(`observacionesRapidas` en el contrato de datos).

> [!important] En el QR van como indice, no como texto (probado 2026-08-24)
> La interfaz muestra el texto completo del boton, pero lo que viaja en el QR es el
> **indice** de la observacion en `observacionesRapidas`, no la frase. Medido: esto reduce
> el peso de un carrito de 30 items de 1.767 a 547 bytes (69%) y evita disparar el Plan B
> de [[SPEC-002 - QR de Pedido]] en pedidos normales. El campo libre corto si viaja como
> texto — por eso debe quedarse corto.

### Carrito y vista previa del pedido

- Cada plato disponible tiene un **boton de agregar** sobre su foto. Al agregarlo, el boton
  muestra la cantidad en curso
- Un **boton flotante** aparece cuando hay algo en el pedido (y solo fuera del hero)
- Al abrirlo se muestra un **modal con la vista previa completa** antes de generar el QR:
  - Cada renglon con foto, nombre, precio por cantidad y control de cantidad
  - **Etiquetas rapidas de observacion** por plato, mas un campo libre corto
  - **Comentario general para la cocina** (maximo 200 caracteres, con contador)
  - Total y llamada a la accion: *Generar QR del pedido*
- **Estado vacio** con mensaje propio y la accion deshabilitada
- No hay pago: la accion final genera el QR que el mesero escanea
  (ver [[SPEC-002 - QR de Pedido]] y [[ADR-002 - El mesero confirma el pedido]])

En movil el modal ocupa la pantalla completa; en tablet y escritorio es un panel centrado.

## Criterios de aceptacion

- [ ] El menu completo carga y se navega en menos de 3 segundos en 4G — **no medido**
      (haria falta probar en red real, no en localhost)
- [x] Los filtros de categoria funcionan y se resaltan solos al hacer scroll —
      implementado con `IntersectionObserver`
- [ ] La pagina es usable con una sola mano en un telefono — **no verificado en un
      telefono real**, solo con viewport emulado (a 320 y 375 px en
      [[SPEC-022 - Auditoria Responsive]])
- [x] Un plato sin foto se ve digno, no roto — inicial sobre color de marca
- [x] Un plato agotado es visible pero no se puede agregar al carrito — se muestra en gris
      con etiqueta, y el boton "+" no se renderiza
- [x] Un nombre de plato muy largo no rompe la maquetacion — el dato de prueba incluye uno
      largo a proposito
- [x] El boton de carrito es alcanzable con el pulgar — flotante, centrado abajo
- [x] Entrando por QR de mesa, se aterriza directo en el menu — **matiz**: hoy aterriza en
      el hero igual que la entrada normal; lo que si funciona es que la mesa queda fijada
      (se muestra "Mesa 12"). El salto directo al menu sigue **pendiente**
- [x] Todos los colores y tipografias salen de variables, ninguno escrito a mano —
      **verificado**: tokens de Tailwind apuntando a variables CSS de la base
- [x] Saltar a una categoria deja el titulo visible, no tapado — `scroll-mt` calculado
      sobre barra + filtros
- [x] Ningun control tactil mide menos de 44px — **verificado**: 44×44 en el boton de
      agregar en movil
- [x] La pagina no genera scroll horizontal en ningun tamano — **verificado** en 1440 y 375
- [x] El modal del pedido funciona a pantalla completa en telefono — a pantalla completa
      en movil, panel centrado desde `sm`
- [x] El pedido no se persiste en ningun momento antes de que el mesero confirme —
      el carrito vive solo en Pinia, en memoria

## Observaciones rapidas: generales y por plato (2026-08-31)

Las etiquetas del carrito ("sin cebolla", "poca sal") eran **una lista unica y global**:
las mismas para todo, sin importar el plato. "Sin cebolla" aparecia igual en una gaseosa
que en una hamburguesa.

Pasan a tener **dos niveles**:

| Nivel | Que es | Donde aplica |
|---|---|---|
| **General** | La lista de siempre | A **todos** los platos |
| **Por plato** | Etiquetas propias de ese plato | Solo a el |

Un plato muestra **las generales mas las suyas**. Ninguna reemplaza a la otra: se suman.

### Por que dos niveles y no solo el de plato

"Sin sal" o "para llevar" aplican a casi todo — obligar a repetirlas plato por plato seria
trabajo de captura sin sentido, y bastaria olvidarlas en uno para que ese plato pierda la
opcion. Las generales cubren lo transversal; las de plato cubren lo que solo tiene sentido
ahi ("termino medio" en una carne, "sin hielo" en una bebida).

### Ambos niveles se administran desde el panel

CRUD completo en el panel de administracion, coherente con la regla del proyecto: nada de
textos de negocio escritos a mano en el codigo.

> [!note] El backend ya tenia CRUD, faltaba la pantalla
> `ObservacionRapida` ya exponia crear/editar/borrar por API desde SPEC-003, pero **no
> habia forma de gestionarlas desde el panel** — habia que entrar por la API a mano. Ese
> era el hueco real.

### Reglas

- Una etiqueta general **no se puede repetir** con otra general (el texto es unico)
- Una etiqueta de plato **puede repetir** el texto de una general — pero entonces no se
  muestra dos veces: el plato la ve una sola vez
- Desactivar una etiqueta la quita de los platos **sin borrar** las observaciones ya
  escritas en pedidos pasados (SPEC-008: el historial no se reescribe)

### Criterios de aceptacion

- [x] Un plato sin etiquetas propias muestra **solo las generales**
- [x] Un plato con etiquetas propias muestra **las generales mas las suyas**
- [x] Una etiqueta de plato con el mismo texto que una general **no se duplica** en pantalla
- [x] Las generales se crean, editan y desactivan **desde el panel**
- [x] Las de plato se gestionan **desde la ficha de ese plato**
- [x] Desactivar una etiqueta **no altera** las observaciones de pedidos ya hechos

> [!note] Revisado 2026-09-14
> Estaban construidos pero sin marcar. Las etiquetas del plato se arman en
> `menu/serializers.py`: las generales mas las propias, sin repetir un mismo texto. Las
> observaciones del pedido guardan el texto escrito, no una referencia a la etiqueta, por
> eso desactivarla no toca pedidos pasados.

## Dependencias

- [[SPEC-001 - QR de Mesa]]
- [[SPEC-002 - QR de Pedido]]
- [[SPEC-007 - Administracion y Parametrizacion]] — de ahi salen menu, colores y textos
- [[Sistema de Diseno]]
