---
tipo: spec
id: SPEC-021
estado: implementada
actualizado: 2026-09-14
tags: [diseno, navegacion, roles, responsive]
---

# SPEC-021 — Navegacion del Personal

> [!success] Estado: Implementada el 2026-09-08

## Proposito

Que cada trabajador llegue a lo suyo en un toque, viendo **solo lo que le
corresponde**, desde una barra lateral agrupada por tarea en vez de una fila de
doce pastillas apretadas.

## El problema que resuelve

El encabezado de las pantallas internas tiene **doce enlaces**. En computador
se parten en tres filas; en un telefono de 375 px, en cuatro. Ocupan mas alto
que el propio contenido que uno vino a mirar.

Pero el encabezado no esta lleno solo por diseño. Debajo hay tres cosas rotas:

### 1. El filtro por rol casi no filtra

De los doce enlaces, **diez estan marcados `[admin, mesero, cajero]`**. O sea:
un mesero que solo toma pedidos ve *Libro*, *Activos*, *Reportes* y *Clientes*
— el modulo contable completo.

> [!important] Esto es lo mas importante de esta spec
> **Si se arregla solo el filtro, un mesero pasa de diez enlaces a cuatro. Y
> cuatro caben en una sola linea.**
>
> El encabezado esta lleno porque el filtro esta roto, no solo porque las
> pastillas sean mal patron. La barra lateral sigue valiendo la pena —un
> administrador ve doce, y agrupar solo se puede en vertical— pero **si se hace
> la barra sin arreglar el filtro, el problema de fondo sigue ahi**, solo que
> en vertical.

### 2. El servidor no le dice al navegador quien puede cobrar

`GET /api/auth/perfil/` devuelve solo `{usuario, rol}`.

Cinco pantallas —Caja, Libro, Activos, Ventas, Reportes, Clientes— estan
protegidas con `PuedeCobrar` en el servidor, que es un permiso **configurable**
(un mesero cobra o no segun el parametro `meseros-pueden-cobrar`). La barra no
tiene con que saberlo, asi que las muestra siempre.

El resultado es que un mesero con el cobro apagado ve seis enlaces que al
tocarlos le dan error. **Es el criterio que quedo pendiente en
[[SPEC-019 - Clientes]]**, y esta spec lo cierra.

### 3. Las pantallas de administracion llevan dos navegaciones encima

Las siete pantallas del panel usan el mismo marco, asi que muestran **las doce
pastillas del encabezado y ademas sus siete pestañas**: diecinueve elementos de
navegacion antes de llegar al contenido.

Se comprobo abriendo *Admin › Cobro*: primero tres filas de pastillas, luego el
titulo, luego la fila de pestañas, y recien despues los medios de pago.

### 4. El rol se decide con `groups.first()`

Quien pertenezca a dos grupos queda con el que la base devuelva primero, sin
ningun criterio. Una persona que sea mesero **y** cajero puede terminar viendo
la mitad de lo suyo segun el orden de inserccion en la tabla.

## Alcance

- **Barra lateral** en computador y **cajon deslizante** en telefono, en lugar
  de la fila de pastillas
- Destinos **agrupados por tarea**, con el grupo propio abierto
- **Filtro correcto**: por rol *y* por permiso de cobro
- Encabezado reducido a lo minimo
- El perfil devuelve **todos los roles** y **si puede cobrar**
- Estados de foco y teclado: la barra se puede recorrer sin mouse

## Fuera de alcance

- **Rediseñar las pestañas del panel de administracion.**
  `AdminPestanas.vue` se queda como esta: son siete, caben en una linea, y es
  otro contexto de uso — se entra a configurar, no a trabajar.
  **Lo que si se resuelve** es la doble navegacion: al vaciarse el encabezado,
  esas pantallas pasan de diecinueve elementos de navegacion a siete
- **La pantalla del cliente** no se toca: no tiene navegacion de personal
- **Cambiar que puede hacer cada rol.** Esta spec cambia lo que se *ve*, no lo
  que se *puede*. Los permisos del servidor quedan exactamente igual
- **Buscador de pantallas / atajos de teclado.** Con doce destinos no se
  justifica
- **Personalizar el orden** por usuario

## Comportamiento

### Los grupos

Los doce destinos caen en cinco grupos. Se agrupa por **tarea, no por rol**, a
proposito: los roles se solapan —un cajero tambien atiende mesas— y una persona
entiende mejor "esto es lo de caja" que "esto es lo del rol cajero".

| Grupo | Destinos | Quien lo ve |
|---|---|---|
| **Servicio** | Recibir pedido · Salon · Pedidos · Cuentas | mesero, cajero, admin |
| **Caja** | Turno · Libro · Activos | quien puede cobrar |
| **Negocio** | Ventas · Reportes · Clientes | quien puede cobrar |
| **Cocina** | Tablero | cocina, admin |
| **Ajustes** | Panel de administracion | admin |

Un grupo del que no se ve **ningun** destino **no se dibuja**: ni su titulo, ni
su espacio. Un mesero sin cobro ve un solo grupo con cuatro cosas.

### En computador: barra lateral fija

- **Fija a la izquierda**, siempre visible desde `lg` (1024 px)
- **280 px** de ancho abierta, **72 px** plegada a solo iconos
- Se pliega con un boton, y **recuerda el estado** en el navegador
  (`localStorage`) — quien la plega es porque quiere mas espacio, y volver a
  plegarla en cada pantalla es una molestia diaria
- Plegada, cada icono muestra el nombre al pasar el mouse (`title`, mas
  `aria-label` para lectores de pantalla)

### En telefono: cajon deslizante

- **Oculta por defecto**, se abre con un boton de menu arriba a la izquierda
- Entra **desde la izquierda**, con un velo oscuro detras
- Se cierra: tocando el velo, con la tecla `Escape`, al elegir un destino, y
  con un boton de cerrar visible
- Mientras esta abierta, **el fondo no se desplaza** (bloqueo de scroll en
  `body`)
- **Atrapa el foco**: tabular dentro del cajon no se sale a la pagina de atras

> [!note] Por que un cajon y no una barra inferior
> Un mesero usa esto de pie en el salon, y el cajon le cuesta un toque de mas
> para llegar a "Recibir pedido".
>
> Se acepta porque **con el filtro arreglado sus destinos bajan de diez a
> cuatro**, y al abrir el cajon los ve todos de una sin recorrer nada. Una
> barra inferior seria un segundo sistema de navegacion que mantener, y dos
> sistemas se desincronizan.

### El grupo propio, abierto

Al abrir, el grupo que corresponde al rol principal **ya viene desplegado** y
los demas plegados. Un mesero abre y ve sus cuatro cosas, no una lista de doce.

Los grupos se pliegan y despliegan, y ese estado tambien se recuerda.

### El encabezado, con cuatro cosas

Queda solo con:

1. El nombre del restaurante (que sigue viniendo de la configuracion, nunca
   escrito a mano)
2. La campana de notificaciones
3. Quien eres
4. Salir

Y en telefono, el boton de menu. **Nada mas.**

El titulo de la pantalla actual pasa a estar donde ya esta —dentro del
contenido—, no repetido arriba.

### Que ve cada quien, exactamente

| Quien | Grupos que ve |
|---|---|
| Mesero con cobro **apagado** | Servicio |
| Mesero con cobro **encendido** | Servicio · Caja · Negocio |
| Cajero | Servicio · Caja · Negocio |
| Cocina | Cocina |
| Administrador | Todos |

## Diseño

> [!important] Esto no es decoracion: son las medidas que hay que respetar
> Cada valor de aqui sale de una razon, no de un gusto. Si algo se cambia,
> cambiar tambien la razon.

### Medidas

| Que | Valor | Por que |
|---|---|---|
| Ancho abierta | `280px` | Cabe "Recibir pedido" sin cortar en una linea |
| Ancho plegada | `72px` | Icono de 24 con area de toque de 44 y aire |
| Alto de cada destino | **minimo `44px`** | Es el minimo tactil, y es lo que ya usa el resto del sistema (`min-h-11`) |
| Separacion entre destinos | `2px` | Juntos se ven como un bloque; separados se leen como lista |
| Ancho del cajon en telefono | `min(85vw, 320px)` | Deja ver un borde del fondo, que es lo que le dice a la persona que puede tocar ahi para cerrar |
| Velo | `bg-tinta/45` con `backdrop-blur-sm` | El mismo que ya usan los modales de Clientes y Activos |

### Color y estado

Se usan **los tokens que ya existen**, ninguno nuevo: `--color-marca`,
`--color-lienzo`, `--color-tinta`, `--color-marca-suave`.

| Estado | Como se ve |
|---|---|
| Normal | Texto `tinta/75`, sin fondo |
| Encima (mouse) | Fondo `marca/6` |
| **Actual** | Fondo `marca`, texto `lienzo`, y una **barra de 3 px** en el borde izquierdo |
| Foco por teclado | Anillo visible de 2 px en `marca` — **nunca `outline: none` sin reemplazo** |
| Titulo de grupo | `10.5px`, mayusculas, `tracking-[0.12em]`, `marca/55` — igual que las etiquetas de campo del resto del sistema |

> [!warning] El destino actual no se marca solo con color
> Marcarlo solo cambiando el color deja fuera a quien no distingue bien los
> colores. Por eso lleva **ademas** la barra lateral de 3 px y `aria-current`.

### Tipografia

Los nombres de destino en `font-sans` a `14px`, peso semibold cuando estan
activos. **Nada de `font-display`**: la serif es para titulos, y doce nombres
en serif se leen despacio.

## Movimiento

Sigue lo que ya dice [[Sistema de Diseno]], con una diferencia importante: **la
navegacion no es decorativa**. Las entradas laterales del sitio del cliente
duran 1000 ms porque son un gesto de bienvenida; un menu que tarda un segundo
en abrirse es un menu que estorba.

| Que | Valor |
|---|---|
| Apertura del cajon | `220ms`, `ease-out` |
| Cierre | `180ms`, `ease-in` — cerrar siempre se siente mejor un poco mas rapido |
| Velo | `opacity` a la vez que el cajon |
| Plegado de un grupo | `160ms` sobre la altura |

> [!danger] Animar `transform`, nunca `left` ni `width`
> Animar `left` o `width` obliga al navegador a recalcular la maquetacion en
> cada cuadro. En un telefono de gama baja —que es el que va a tener el
> mesero— se ve a tirones.
>
> El cajon se mueve con `transform: translateX(-100%)` → `translateX(0)`.

> [!danger] `prefers-reduced-motion`
> Con movimiento reducido: **sin deslizamiento**. El cajon aparece y desaparece
> directamente. No es un adorno que se pueda dejar "un poquito": hay gente a la
> que el movimiento le produce mareo real.

## Responsive

> [!danger] La leccion que ya costo una correccion
> El 2026-09-07 se dio por bueno "responsive verificado" habiendo comprobado
> **solo que no hubiera desborde horizontal**. El autor tuvo que corregirlo: la
> seccion de reportes tenia nombres cortados y etiquetas ilegibles, y el
> desborde era cero.
>
> **Medir el desborde no es verificar el diseño responsive.** Aqui se exige el
> recorrido completo, tocando, en cada tamaño.

### Los tres tamaños

| Tamaño | Que pasa |
|---|---|
| **< 1024 px** (telefono y tablet) | Cajon oculto + boton de menu |
| **>= 1024 px** (computador) | Barra lateral fija, contenido corrido a la derecha |
| **375 px** (el caso de prueba obligatorio) | Todo lo anterior, sin desborde, con toques de 44 px y sin texto cortado |

Se elige `1024px` y no `768px` porque una tablet en vertical con barra fija
deja el contenido en menos de 500 px utiles — mas estrecho que muchos
telefonos en horizontal.

### Como se verifica (no negociable)

1. Cargar la pantalla **ya** en cada tamaño, no encoger una ventana grande: al
   encoger, componentes con observador de tamaño pueden quedar con medidas
   viejas y dar un falso positivo
2. **Abrir el cajon y tocar cada destino**, uno por uno
3. Comprobar que **ningun nombre queda cortado** ni con puntos suspensivos
4. Comprobar con **cada rol**, no solo con administrador
5. Y ademas, que el desborde horizontal sea cero

## Reglas

1. **La barra se filtra por rol Y por permiso de cobro**, no solo por rol.
2. **Un grupo sin destinos visibles no se dibuja.**
3. **Esconder un enlace no es un permiso.** El servidor sigue comprobando todo
   igual; esta spec no relaja ninguna comprobacion.
4. **El destino actual se distingue por algo mas que el color.**
5. **Nada de `outline: none`** sin un indicador de foco que lo reemplace.
6. **El movimiento se hace con `transform`**, y se apaga con
   `prefers-reduced-motion`.
7. **Toque minimo de 44 px** en todo lo que se pueda tocar.
8. **El encabezado no vuelve a crecer.** Si aparece una pantalla nueva, va a un
   grupo de la barra, no al encabezado.

## Criterios de aceptacion

### Que se vea lo correcto

- [x] Un **mesero con el cobro apagado** ve **solo** el grupo Servicio
- [x] Ese mesero **no ve** Caja, Libro, Activos, Ventas, Reportes ni Clientes
- [x] Un **mesero con el cobro encendido** ve Servicio, Caja y Negocio
- [x] Un **cajero** ve Servicio, Caja y Negocio
- [x] **Cocina** ve solo su tablero
- [x] El **administrador** ve todo
- [x] Una persona en **dos grupos** ve la union de los dos, no uno arbitrario
- [x] Un grupo sin destinos visibles **no deja hueco** en la barra

### Que funcione

- [x] En computador la barra esta **siempre visible** y no tapa el contenido
- [x] Se **pliega y despliega**, y el estado **sobrevive a recargar**
- [x] En telefono el cajon **se abre con el boton** y se cierra con el velo,
      con `Escape`, con el boton de cerrar y **al elegir un destino**
- [x] Con el cajon abierto, **el fondo no se desplaza**
- [x] El **foco queda atrapado** dentro del cajon abierto
- [x] El destino **actual** se distingue, y lleva `aria-current`
- [x] Se puede recorrer **entera con el teclado**, con el foco siempre visible
- [x] El grupo del rol propio **viene abierto**

### Que se vea bien

- [x] Ningun nombre de destino **queda cortado** en ningun tamaño
- [x] Todo lo tocable mide **44 px o mas**
- [x] Con `prefers-reduced-motion` **no hay deslizamiento**
- [x] El encabezado queda con **cuatro elementos** y en **una sola linea** en
      computador
- [x] Sin desborde horizontal en **375 px**
- [x] Una pantalla de administracion muestra **una sola** navegacion
      visible ademas de la barra: sus pestañas
- [ ] Recorrido completo hecho **con cada rol** y en cada tamaño — falta con mesero,
      cajero y cocina; lo medido se hizo con la sesion de administrador

### Que no se rompa

- [x] Las **19 pantallas** que usan el marco siguen funcionando
- [x] La **campana de notificaciones** sigue en su sitio y sigue avisando
- [x] El **nombre y la paleta** del restaurante siguen viniendo de la
      configuracion
- [x] Ninguna comprobacion del servidor se relajo

> [!note] Revisado 2026-09-14
> Comprobado contra `BarraLateral.vue` y `lib/navegacion.js`: pliegue guardado en
> `localStorage`, cierre con `Escape` y al elegir destino, foco atrapado, `aria-current`
> y `prefers-reduced-motion`. Los de tamaño y toque salen de la auditoria de
> [[SPEC-022 - Auditoria Responsive]], y las pruebas del servidor siguen en verde.

## Plan de implementacion

### Paso 1 — El servidor dice quien puede que (1 hora)

En `nucleo/vistas.py`, `PerfilView` pasa a devolver:

```json
{
  "usuario": "carla",
  "rol": "cajero",
  "roles": ["mesero", "cajero"],
  "puede_cobrar": true
}
```

- `roles` en plural resuelve el problema de `groups.first()`. Se **conserva**
  `rol` para no romper lo que ya lo usa, y pasa a ser "el principal" con un
  orden explicito: admin > cajero > mesero > cocina
- `puede_cobrar` sale de la funcion `puede_cobrar()` que ya existe en
  `ventas/operaciones.py`. **No se reimplementa la regla**: si viviera en dos
  sitios, un dia dirian cosas distintas

**Pruebas primero**, en `nucleo/tests.py` o donde corresponda:
- un mesero con el parametro apagado devuelve `puede_cobrar: false`
- el mismo con el parametro encendido, `true`
- alguien en dos grupos devuelve los dos en `roles`

### Paso 2 — Los grupos y el filtro (2 horas)

Sacar la lista de destinos de `MarcoInterno.vue` a su propio archivo
(`frontend/src/lib/navegacion.js`): la lista es datos, y mezclarla con el
componente hace que cualquier cambio de menu obligue a tocar el marco.

```js
export const GRUPOS = [
  { id: "servicio", titulo: "Servicio", destinos: [...] },
  { id: "caja", titulo: "Caja", requiereCobro: true, destinos: [...] },
  // …
];
```

Y una funcion `gruposVisibles(perfil)` que aplica rol + `puede_cobrar`, con
sus pruebas: es logica pura y se prueba sin pintar nada.

### Paso 3 — La barra y el cajon (medio dia)

Componente nuevo `BarraLateral.vue`, usado desde `MarcoInterno.vue`.

- Un solo componente para los dos casos: la diferencia entre barra fija y cajon
  es de clases, no de logica. Dos componentes se desincronizarian
- Iconos en **SVG en linea**, como el resto del proyecto — nada de librerias de
  iconos por doce dibujos
- El bloqueo de scroll y la trampa de foco, con su limpieza al desmontar

### Paso 4 — Vaciar el encabezado (1 hora)

En `MarcoInterno.vue`: quitar las pastillas, dejar los cuatro elementos, y el
boton de menu por debajo de `lg`.

### Paso 5 — Comprobacion (3 horas)

> [!danger] Aqui esta el riesgo de esta spec
> `MarcoInterno.vue` lo usan **19 pantallas**. Es una sola pieza —bueno, se
> cambia en un sitio— pero **si se rompe, se rompen las 19 a la vez**.

El recorrido es obligatorio y completo:

1. Entrar a **cada una** de las 19 pantallas
2. Con **cada rol**: mesero sin cobro, mesero con cobro, cajero, cocina, admin
3. En **375 px y en computador**, cargando ya en ese tamaño
4. Con y sin `prefers-reduced-motion`
5. Recorriendo con el teclado

Actualizar [[SPEC-019 - Clientes]] marcando el criterio que esta spec cierra, y
la bitacora.

**Total estimado: un dia y medio.**

## Dependencias

- [[SPEC-007 - Administracion y Parametrizacion]] — de ahi sale el parametro de
  quien cobra
- [[SPEC-014 - Turno de Caja y Cajas de Fondos]] — define `puede_cobrar()`
- [[SPEC-019 - Clientes]] — **esta spec cierra su criterio pendiente**
- [[SPEC-020 - Activos Liquidos]] — aporta el destino Activos al grupo Caja
- [[Sistema de Diseno]] — tokens, movimiento y `prefers-reduced-motion`

## Preguntas abiertas

- [x] **¿La barra lleva iconos, o solo texto?** Los iconos hacen falta para el
      modo plegado. **Resuelta:** con iconos SVG de trazo fino, como se propuso.
- [x] **¿El cajero deberia ver el grupo Servicio primero, o el de Caja?**
      Depende de si en Springfield el cajero atiende mesas o solo cobra.
      **Resuelta:** Servicio primero para todos, con el grupo del rol propio abierto,
      como se propuso.
- [x] **¿Se agrega un atajo al destino mas usado en el encabezado del
      telefono?** Ahorraria un toque al mesero. **Resuelta:** no se agrego. Si en
      servicio el mesero se queja del toque de mas, se reconsidera.
