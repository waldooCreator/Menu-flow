---
tipo: bitacora
fecha: 2026-08-27
tags: [bitacora, admin, panel, crud, spec-001, spec-007]
---

# 2026-08-27 — Panel de administracion completo

Segunda tanda del dia. El punto 1 del estudio [[Que le Falta para ser un POS Vendible]]:
**un restaurante que comprara esto no podia agregar un plato** — el panel solo editaba
parametros, y el menu, las mesas, las estaciones y los usuarios se creaban con comandos de
terminal en el servidor. La diferencia entre un demo y un producto.

## Lo esencial

El panel paso de una pantalla a **cinco pestañas** con ruta propia:

| Pestaña | Que hace | Salda |
|---|---|---|
| **Sitio** | Parametros, ahora con **subida de imagenes** (el "proximo tramo" pendiente desde el 2026-08-25) y el grupo Decoracion que faltaba en las etiquetas | SPEC-007 |
| **Menu** | CRUD de categorias y platos con foto, boton disponible/agotado de un toque, y el selector **categoria → estacion** | SPEC-007, y la base del ruteo de SPEC-005 |
| **Mesas** | Crear, desactivar, **regenerar el codigo** y descargar el QR listo para imprimir | El pendiente mas viejo: SPEC-001 lo pedia desde el inicio |
| **Estaciones** | CRUD con la estacion **por defecto** exclusiva (marcar una desmarca la anterior) | SPEC-005/007 |
| **Usuarios** | Contratar con rol (mesero/cocina), restablecer clave, desactivar | SPEC-007 ("gestion de usuarios") |

## Decisiones que quedaron en codigo

- **Mesas y usuarios no se borran, se desactivan.** Toda venta conserva su mesa y su
  responsable (regla del proyecto); el endpoint de mesas ni siquiera expone DELETE, y el
  queryset de usuarios excluye a los superusuarios — el panel gestiona al personal, no a
  quien gestiona el panel.
- **El QR de mesa no se guarda en ningun lado.** Es la URL `/m/<codigo>` dibujada en el
  navegador con la libreria que ya dibujaba el QR del pedido, usando el **origen actual**
  (IP local en desarrollo, dominio en produccion — nada que configurar). Regenerar el
  codigo invalida el impreso anterior: esa es su utilidad, no un efecto secundario.
- **Un plato con ventas no se elimina** (PROTECT del historial congelado): el panel
  muestra el error y sugiere marcarlo agotado. Una estacion con comandas, igual.
- **La clave la fija el administrador en persona** — sin correos de recuperacion. Es
  deliberadamente basico: asi funciona un restaurante.
- Permiso nuevo `CocinaLecturaAdminEscritura` para estaciones: el tablero las lee, solo
  el admin las escribe. Antes eran de solo lectura absoluta.
- `CategoriaSerializer` **no exponia `estacion`**: el panel no podia mover una categoria
  de cocina a bar, que es literalmente la promesa de SPEC-005 ("mover una categoria es
  configuracion, jamas codigo"). Corregido.

## Verificado

**API** (script en el scratchpad, todo en verde): crear/desactivar/regenerar mesa (DELETE
responde 405 a proposito) · crear usuario con rol y entrar con el · restablecer clave y
entrar con la nueva · clave corta rechazada · usuario desactivado no entra · superusuarios
ocultos · mesero recibe 403 en mesas, usuarios y estaciones · crear y borrar estacion ·
subir foto de plato y de parametro por multipart.

**Navegador** (panel real): las 5 pestañas navegan · crear categoria "Prueba Panel" ·
crear plato con precio · alternar a Agotado de un toque · crear mesa · el QR se genera
como data-URL con la URL correcta · regenerar cambia el codigo · crear estacion · crear
usuaria "maria" y **entrar con su clave** · sin desborde horizontal.

### Tres tropiezos, dos mios

1. **Mi PNG hexadecimal a mano era invalido** — Pillow lo rechazo (correctamente). La
   prueba paso a generar un PNG real con Pillow.
2. **El clic de "Regenerar" cayo en la fila equivocada**: mi selector tomo el contenedor
   completo y el boton de la primera mesa — la virtual "Domicilio", inactiva — y le cambio
   el codigo de verdad. Se restauro a `domicilio` (la migracion 0004 lo referencia por
   nombre). Leccion repetida: los selectores de prueba deben anclar a la fila exacta.
3. **La prueba de API sobrescribio la foto real del primer plato** con el PNG de 4×4.
   `cargar_menu_demo` solo pone foto si esta vacia (`and not plato.foto`), asi que hubo
   que borrarla primero y resembrar.

> [!warning] No verificado por Claude
> El aspecto visual del panel — el entorno de prueba no compone frames. Todo se verifico
> midiendo DOM y API.

## Pendiente

- El **orden** de categorias, platos y estaciones se guarda pero no se puede reordenar
  desde el panel (no hay arrastrar-y-soltar)
- Etiquetas de platos: la API tiene CRUD, el panel aun no las edita
- Los siguientes del estudio: **anular con motivo**, registrar el cobro, cierre de caja

## Enlaces

- [[SPEC-001 - QR de Mesa]]
- [[SPEC-007 - Administracion y Parametrizacion]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[Que le Falta para ser un POS Vendible]]
- [[Inicio]]
