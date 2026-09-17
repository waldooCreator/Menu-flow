---
tipo: bitacora
fecha: 2026-08-24
tags: [bitacora, backend, django, postgresql, fase-1]
---

# 2026-08-24 — Backend Django y primera configuración real

Primer código de backend del proyecto. Cierra [[ADR-006 - Stack Django, Vue y PostgreSQL]]
y arranca la implementación de [[SPEC-007 - Administracion y Parametrizacion]].

## Decisión de stack

El autor decidió directamente: **Django (Python) + Vue + PostgreSQL**, con Postgres en
Docker para desarrollo local y migración a base local en el VPS más adelante.

También aclaró un punto que [[SPEC-009 - Portabilidad Multi-restaurante]] no precisaba:
el despliegue real es **varias instancias del sistema en el mismo VPS**, aisladas por
puerto + base de datos + carpeta de medios — no un servidor por restaurante. Quedó anotado
en la spec y en el ADR.

## Qué se hizo

1. **`docker-compose.yml`** con Postgres 16, sin `container_name` fijo (para que varias
   instancias convivan), puerto y credenciales desde `.env`. Puerto 5433 porque 5432 ya
   estaba ocupado por otro Postgres local en esta máquina.

2. **Proyecto Django** (`backend/`), apps `configuracion` y `menu`.

3. **`configuracion.Parametro`** — tabla clave/valor para toda la identidad visual y los
   textos (colores, tipografías, nombre, hero, contacto, horario, galería), tal como manda
   ADR-003. Con `configuracion.helpers.config()` cacheado y su invalidación automática al
   guardar.

4. **App `menu`** — `Categoria`, `Plato`, `Etiqueta`, `ObservacionRapida`, reflejando 1:1 el
   contrato que ya usaba `prototipo/data.js`.

5. **Comandos de siembra** (`cargar_configuracion_demo`, `cargar_menu_demo`) que cargan en
   la base los mismos valores que hoy están fijos en el prototipo, **copiando también las
   fotos reales** desde `prototipo/assets/`.

6. **Django admin** activo y en español, como panel funcional interino mientras se
   construye el panel Vue.

## Verificado end-to-end

- Postgres levantado, migraciones aplicadas (`configuracion.0001`, `menu.0001`)
- 23 parámetros y 19 platos sembrados, con imágenes reales copiadas y servidas por
  `/media/...` (verificado con 200 en cada ruta)
- **Acentos y eñes verificados en UTF-8 real** en la base (no solo en pantalla): la mojibake
  que se veía en la consola de Windows era únicamente el codepage de la terminal, no
  corrupción de datos — se confirmó escribiendo a un archivo UTF-8 y leyéndolo aparte
- Login del admin funcionando, con el título "Terra" ya tomado de la configuración
- Lista de 19 platos con categoría, filtros por categoría/disponible/etiqueta funcionando
- Ficha de un plato: precio, disponibilidad y archivo de foto correctos

## Decisión pendiente que quedó expuesta

Construir esto obligó a ver un problema que antes no era visible: **si la página del
cliente se sirve como SPA de Vue, el visitante ve la paleta por defecto un instante antes
de que cargue la configuración real del restaurante** — inaceptable en una página pública
que debe abrir rápido en 4G. Quedó anotada como pregunta bloqueante en
[[Preguntas Abiertas]]: la alternativa es que Django renderice esa página con los tokens ya
inyectados, y Vue se use solo para el panel de administración.

## Estado al cierre

- [[ADR-006 - Stack Django, Vue y PostgreSQL]] cerrado
- [[SPEC-007 - Administracion y Parametrizacion]] pasó de Borrador a Aprobada, con modelo
  de datos real y parcialmente implementado (ver tabla de estado en la spec)
- Backend corriendo en `http://localhost:8000/admin/`
- Pendiente inmediato: decidir cómo se sirve la página del cliente, luego panel Vue, luego
  la prueba técnica del QR (permiso ya dado por el autor para esta sesión)

## Enlaces

- [[SPEC-007 - Administracion y Parametrizacion]]
- [[SPEC-009 - Portabilidad Multi-restaurante]]
- [[ADR-006 - Stack Django, Vue y PostgreSQL]]
- [[Preguntas Abiertas]]
- [[Inicio]]
