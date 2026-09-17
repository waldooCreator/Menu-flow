---
tipo: adr
id: ADR-006
estado: aceptada
fecha: 2026-08-24
tags: [stack, django, vue, postgresql]
---

# ADR-006 — Stack: Django, Vue y PostgreSQL

**Estado:** Aceptada · **Fecha:** 2026-08-24

## Contexto

El proyecto estaba definido a nivel de producto y diseño, pero sin lenguaje, framework ni
motor de base de datos — bloqueando el arranque de la Fase 1. Ver la versión anterior de
esta decisión en el historial: la nota partía marcada como **pendiente**.

## Decisión

- **Backend:** Python + Django — **solo API y permisos**, sin renderizar ninguna vista
- **Frontend:** Vue para **todo** — página del cliente, panel de mesero/estación y panel
  de administración. Nada se gestiona desde el admin de Django
- **Base de datos:** PostgreSQL, en Docker para desarrollo local

Elegido directamente por el autor, con preferencia explícita por este stack.

> [!info] Resuelto el 2026-08-24: la página del cliente va en Vue
> La primera versión de este ADR dejaba abierto si la página del cliente la servía Django
> (para evitar el salto de paleta por defecto) o Vue. **El autor decidió: todo en Vue,
> Django nunca renderiza HTML.** Ver el riesgo que eso reabre en Consecuencias, y cómo se
> mitiga.

## Justificación

- **PostgreSQL** encaja con [[SPEC-009 - Portabilidad Multi-restaurante]]: `JSONField`
  nativo (usado en `Plato.estadisticas`), y un motor robusto para migraciones versionadas.
- **Django** trae el ORM y las migraciones. Su panel de administración se usó **solo como
  peldaño temporal** para validar el modelo de datos con uso real (ver bitácora del
  2026-08-24) — no es, ni va a ser, la interfaz de gestión del sistema.
- **Vue** para toda la interfaz: la página del cliente, y el panel de administración que
  reemplaza al Django admin.

## Consecuencias

**Positivas**
- El panel de Django admin es utilizable desde el primer día: el modelo de datos se valida
  con uso real, no con suposiciones
- `ImageField` con `upload_to` resuelve directamente la regla de
  [[SPEC-009 - Portabilidad Multi-restaurante|rutas relativas para imágenes]]
- Migraciones de Django cubren la regla de "migraciones versionadas, no dump/restore" de
  esa misma spec

**Negativas / a vigilar**
- **El salto de paleta por defecto es un riesgo real y aceptado.** Con Vue como SPA pura,
  el visitante puede ver un instante la paleta por defecto antes de que cargue la
  configuración del restaurante. Mitigación mínima obligatoria: la API de configuración
  debe responder primero y rápido, con los estilos aplicados antes del primer contenido
  visible (loader neutro o inyección temprana de las variables CSS vía JS antes del
  render de Vue) — pendiente de diseñar en detalle cuando se construya esa página
  (ver [[SPEC-003 - Menu del Cliente]])
- [[SPEC-006 - Notificaciones]] sigue sin resolver su transporte de tiempo real. Con Django,
  la opción natural es **Django Channels** (WebSockets)
- Dos lenguajes en el mismo proyecto (Python + JavaScript): plumbing de CORS y de
  autenticación entre el backend y Vue — y ahora **todo** pasa por esa API, no solo el
  panel de administración

## Arquitectura de la API (implementada 2026-08-24)

Con la decisión de "todo Vue" ya tomada, esto es lo que se construyó y verificó:

- **Django REST Framework**, bajo `/api/`. Cada app expone su propio router
  (`configuracion`, `menu`), unidos en `nucleo/api_router.py`
- **Autenticación:** `TokenAuthentication` de DRF. Login en `POST /api/auth/login/`
  devuelve un token que Vue guarda y reenvía en cada petición (`Authorization: Token …`)
- **Permisos, por defecto cerrados:** `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`.
  Cada vista pública lo declara explícito (`AllowAny` o `IsAuthenticatedOrReadOnly`) —
  nunca al revés, para que un endpoint nuevo no quede abierto por olvido
- **Lo público** (sin login): `GET /api/configuracion/publica/` (forma plana
  `{clave: valor}`, la que consume la página del cliente), y lectura de
  `/api/categorias/`, `/api/platos/`, `/api/etiquetas/`, `/api/observaciones-rapidas/`
- **Lo privado** (requiere token): escritura en todo lo anterior, y CRUD completo de
  `/api/configuracion/` (forma administrativa, con `ayuda`, `grupo`, etc.) — es lo que
  consume el panel Vue
- **CORS:** `django-cors-headers`, origen permitido configurable por `.env`
  (`CORS_ALLOWED_ORIGINS`) — mismo patrón de aislamiento por instancia que puerto/DB/medios

### Verificado de punta a punta

Editar un parámetro en el panel Vue (`http://localhost:5173/admin`) llega por la API a
Postgres, y la página del cliente (`http://localhost:5173/`) lo refleja al recargar. Los
colores y la tipografía que pinta Vue coinciden exactamente con lo guardado en la base
(`color-primario` → `#00473C` → `rgb(0, 71, 60)` computado en el navegador).

### Frontend Vue — estructura

`frontend/` (Vite + Vue 3 + Vue Router + Pinia). `src/api/` concentra las llamadas HTTP,
`src/stores/auth.js` guarda el token, `src/router/` protege `/admin` con un guard.
`ClienteMenu.vue` consume la API pública; `admin/AdminLogin.vue` y
`admin/AdminConfiguracion.vue` son el primer tramo del panel administrativo.

> [!note] Alcance de lo construido hoy
> `ClienteMenu.vue` prueba que el dato fluye de Postgres a Vue y se pinta como estilo real
> — **no** es un port del prototipo visual de Fase 0 (parallax, entradas laterales, modal
> de pedido). Ese port es trabajo aparte. El panel admin edita `Parametro` de tipo texto y
> color; imágenes queda para el siguiente tramo.

## Despliegue multi-instancia en un mismo VPS

El autor aclaró un punto que **SPEC-009** no precisaba: el plan no es "un restaurante, un
servidor", sino **varias instancias del sistema conviviendo en el mismo VPS**, cada una
con su propio puerto, su propia base de datos y su propia carpeta de medios. Ver la
aclaración completa en [[SPEC-009 - Portabilidad Multi-restaurante]].

Esto ya quedó resuelto en el andamiaje: `docker-compose.yml` no fija `container_name` (lo
da el nombre del proyecto), y `.env` controla puerto de base de datos, credenciales y
`MEDIA_ROOT` por instancia.

## Enlaces

- [[Vision del Producto]]
- [[SPEC-007 - Administracion y Parametrizacion]]
- [[SPEC-009 - Portabilidad Multi-restaurante]]
- [[Preguntas Abiertas]]
