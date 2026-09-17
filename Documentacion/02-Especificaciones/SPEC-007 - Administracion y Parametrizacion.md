---
tipo: spec
id: SPEC-007
estado: implementada
actualizado: 2026-09-14
tags: [admin, configuracion, parametrizable, django]
---

# SPEC-007 — Administracion y Parametrizacion

> [!success] Estado: Implementada — revisada 2026-09-14
> El panel propio (Vue) cubre menu, mesas, estaciones, usuarios, cobro, turnos y
> configuracion. Quedan abiertos dos criterios: la auditoria de los cambios de
> configuracion (depende de SPEC-008) y la prueba con un menu de 200 platos.

## Proposito

Que el mismo software sirva a cualquier restaurante cambiando solo configuracion, nunca
codigo.

## Alcance

Todo lo siguiente se administra desde el modulo de configuracion:

- **Identidad visual:** colores, textos, logo, nombre del restaurante, imagenes
- **Menu:** categorias, platos, precios, fotos, disponibilidad, filtros
- **Estaciones:** cuales existen y que categoria se rutea a cual
- **Mesas:** alta, baja y regeneracion de sus QR
- **Usuarios y roles:** tipos de usuario y que puede hacer cada uno
- **Parametros operativos:** moneda, horarios, vencimiento del QR de pedido, umbrales de
  color del cronometro de las estaciones
- **Pagina informativa:** bloques configurables (hero, historia, galeria, sedes, horarios,
  contacto, mapa) que se pueden encender, apagar y reordenar

## Fuera de alcance

- Editor visual tipo arrastrar y soltar
- Multi-restaurante dentro de la misma instalacion
  (ver [[ADR-003 - Una base de datos por restaurante]])

## Comportamiento

### Gestion de usuarios

- Administrar usuarios y tipos de usuario; agregar y desactivar
- Garantizar que **toda venta quede amarrada a un usuario**, para que sea auditable
- Los usuarios **no se borran**, se desactivan: si se borraran, las ventas historicas
  quedarian huerfanas

### Limites de la parametrizacion

El diseno debe aguantar cualquier configuracion, incluida una mala:
nombres de plato larguisimos, 200 items, ninguna foto, y colores de mal gusto. Conviene
acotar las opciones de color a combinaciones que garanticen contraste legible.

## Modelo de datos (implementado)

Dos apps de Django, `configuracion` y `menu`. Codigo en `backend/`.

### `configuracion.Parametro` — clave/valor, TODA la identidad visual y los textos

Una sola tabla en vez de una columna por ajuste (ADR-003, regla 2): agregar un parametro
nuevo manana es una fila, no una migracion.

| Campo | Que es |
|---|---|
| `clave` | Identificador estable usado por el codigo, p.ej. `color-primario` |
| `etiqueta` | Nombre legible en el panel |
| `grupo` | Identidad, Portada, Contacto, Horario, Galeria — agrupa la vista del admin |
| `tipo` | Texto, Color, Numero, Imagen, Si/No |
| `valor` / `imagen` | Segun el tipo. La imagen usa `ImageField` con ruta relativa |

Se lee via `configuracion.helpers.config("clave")`, con cache en memoria que se invalida
solo cuando algo cambia (nunca una consulta directa a la tabla desde el resto del codigo).

### `menu` — categorias, platos, etiquetas, observaciones rapidas

Refleja 1:1 el contrato de datos que ya usaba el prototipo (`prototipo/data.js`):
`Categoria` (nombre, orden), `Plato` (categoria, nombre, descripcion, precio, foto,
disponible, alergenos, `estadisticas` como JSON — `[["380","Cal"], ...]` —, etiquetas),
`Etiqueta` (vegetariano, picante...), `ObservacionRapida` (los botones del carrito,
SPEC-003).

Las `estadisticas` se editan desde la ficha del plato en el panel. No existe una lista
cerrada de nombres: cada restaurante puede usar proteina, gramos, calorias, porciones,
tiempo o cualquier metrica que necesite.

### Panel de administracion

> [!warning] El Django admin fue un peldaño de validación, no el destino
> Se uso `/admin/` para probar el modelo de datos con uso real. **Decision del autor
> (2026-08-24): nada se gestiona desde el admin de Django.** Django queda como API y
> permisos unicamente; toda gestion, incluida esta, pasa a un panel Vue.
> Ver [[ADR-006 - Stack Django, Vue y PostgreSQL]].

### Comandos de siembra

`cargar_configuracion_demo` y `cargar_menu_demo` cargan en la base los mismos valores que
hoy estan fijos en el prototipo, copiando tambien las fotos reales — prueban que el modelo
reemplaza al CSS/HTML escritos a mano sin cambiar el resultado visual.

**`cargar_tema_springfield` (2026-08-25)** es la prueba de fuego de esta spec: convierte el
sitio completo en otro restaurante (paleta Simpson, tipografias cartoon, nombre, textos,
imagenes, numero de WhatsApp) **sin tocar una linea de codigo** — solo parametros. Volver a
Terra es correr `cargar_configuracion_demo` de nuevo. Ese cambio de marca en un comando es
exactamente lo que el requisito 1 promete.

Claves nuevas: `numero-whatsapp` (grupo contacto — el enlace wa.me de los pedidos a
distancia, ver [[SPEC-002 - QR de Pedido]]).

### Parametros que son PLANTILLA, no texto plano (2026-08-26)

`whatsapp-mensaje` dejo de ser una frase fija: ahora es una **plantilla con variables** que
se rellenan con lo que el cliente escribio en el formulario de domicilio.

| Variable | Se reemplaza por |
|---|---|
| `{nombre}` | Nombre de quien recibe el domicilio |
| `{direccion}` | Direccion exacta que digito el cliente |

Reglas de una plantilla parametrizable:

- **Una variable desconocida se deja tal cual**, no se borra ni revienta la pagina. Si el
  administrador escribe `{telefono}` (que no existe), vera `{telefono}` en el mensaje — es
  visible y se corrige solo; fallar en silencio seria peor.
- **La ayuda del parametro debe listar las variables disponibles.** Un campo de plantilla
  sin la lista de que se puede poner adentro es una trampa para el administrador.
- El resultado se codifica para URL al armar el enlace `wa.me`, no antes.

### Panel completo (2026-08-27)

El panel dejo de ser solo parametros. Cinco pestañas: **Sitio** (parametros, ahora con
subida de imagenes), **Menu** (CRUD de categorias y platos, foto incluida, y la asignacion
categoria→estacion que es la base del ruteo de SPEC-005), **Mesas** (SPEC-001: crear,
desactivar, regenerar y descargar el QR), **Estaciones** (CRUD, con la estacion por
defecto exclusiva) y **Usuarios** (contratar con rol, restablecer clave, desactivar).

Reglas comunes: mesas y usuarios **no se borran** — se desactivan (toda venta conserva su
mesa y su responsable); un plato con ventas esta protegido por la base y el panel sugiere
marcarlo agotado; una estacion con comandas historicas tampoco se puede eliminar.

## Estado de implementacion

| Pieza | Estado |
|---|---|
| Identidad visual (colores, tipografias, textos) | **Hecho** — `Parametro`, editable desde Vue via API |
| Menu (categorias, platos, etiquetas, observaciones) | **Hecho** en modelo y API; edicion desde Vue aun no construida |
| API REST (DRF, permisos, CORS) | **Hecho** — ver [[ADR-006 - Stack Django, Vue y PostgreSQL]] |
| Pagina del cliente leyendo de la base | **Hecho (funcional)** — Vue consume `/api/`; falta portar el diseño de Fase 0 |
| Panel Vue de administracion | **En progreso** — login y edicion de texto/color de `Parametro` funcionando; falta imagenes y el CRUD de menu |
| Estaciones (cuales existen, ruteo por categoria) | Pendiente — depende de [[SPEC-005 - Estaciones y Ruteo]] |
| Mesas (alta, baja, regenerar QR) | Pendiente — depende de [[SPEC-001 - QR de Mesa]] |
| Usuarios y roles | **Parcial (2026-08-25)** — grupos `mesero` y `cocina` con separación real: 403 en la API fuera del rol, guardia por rol en la interfaz, y cada rol entra directo a su pantalla. Falta: crear/gestionar usuarios desde el panel (hoy es el comando `crear_usuarios_demo`) |
| Métricas y etiquetas del plato | **Hecho (2026-09-07)** — métricas editables desde la ficha; las etiquetas no dependen de un nombre fijo como `picante` |
| Moneda, locale, QR y cronómetro | **Hecho (2026-09-07)** — parámetros en Admin → Sitio → Operación |
| Textos de ubicación y estado agotado | **Hecho (2026-09-07)** — parámetros de identidad editables desde Admin → Sitio |

## Criterios de aceptacion

- [x] Cambiar el color primario se refleja sin tocar codigo — **verificado de punta a
      punta 2026-08-24**: editado desde el panel Vue, guardado via API en Postgres, la
      pagina del cliente lo pinta al recargar
- [x] La configuracion vive dentro de la misma base de datos del restaurante
- [x] Las imagenes se sirven por ruta relativa, no como blob
- [x] Solo un usuario autenticado puede escribir configuracion — **verificado**: la API
      rechaza con 401 una escritura sin token, y acepta con token valido
- [x] Crear una categoria y asignarla a una estacion funciona sin reiniciar — la categoria
      guarda su estacion y el ruteo la lee en cada pedido ([[SPEC-005 - Estaciones y Ruteo]])
- [x] Desactivar un usuario no rompe las ventas historicas que le pertenecen — los usuarios
      se desactivan, no se borran, y las ventas conservan su responsable
- [ ] Un menu de 200 platos sigue siendo navegable — la pagina real ya existe; falta
      probarla con ese volumen
- [ ] Los cambios de configuracion quedan registrados en auditoria — **no se cumple
      (revisado 2026-09-14)**: el panel guarda el cambio pero no quien lo hizo ni el valor
      anterior. Depende de [[SPEC-008 - Contabilidad y Auditoria]], que sigue en borrador

## Dependencias

- [[SPEC-009 - Portabilidad Multi-restaurante]] — la configuracion viaja con la base
- [[SPEC-008 - Contabilidad y Auditoria]] — los cambios se auditan
- [[ADR-006 - Stack Django, Vue y PostgreSQL]] — el stack sobre el que esto se construyo
