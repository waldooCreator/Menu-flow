---
tipo: bitacora
fecha: 2026-08-24
tags: [bitacora, api, vue, django-rest-framework]
---

# 2026-08-24 — API REST y frontend Vue conectado

Tercera tanda del día, después de
[[2026-08-24 - Prueba tecnica del QR y Vue confirmado]]. Cierra el ciclo: ahora hay un
frontend Vue real hablando con el backend Django real.

## Instrucción del autor

Reforzó la decisión de arquitectura: **todo el frontend, no solo el panel de
administración, debe ser consumible desde Vue.** Django queda exclusivamente como API y
permisos.

## Qué se hizo

### Backend — API REST

- **Django REST Framework** instalado y configurado bajo `/api/`
- **Permisos cerrados por defecto** (`IsAuthenticated`), cada vista pública lo declara
  explícito — nunca al revés
- **`TokenAuthentication`**: `POST /api/auth/login/` devuelve un token
- **Endpoints públicos:** `configuracion/publica/` (forma plana `{clave:valor}`),
  lectura de categorías, platos (con sus fotos y etiquetas resueltas), etiquetas y
  observaciones rápidas
- **Endpoints privados:** CRUD completo de `Parametro` y de todo `menu`, solo con token
- **CORS** (`django-cors-headers`), origen configurable por `.env` — mismo patrón de
  aislamiento por instancia que puerto/DB/medios

### Frontend — proyecto Vue real

`frontend/`: Vite + Vue 3 + Vue Router + Pinia. Estructura: `src/api/` (llamadas HTTP),
`src/stores/auth.js` (token), `src/router/` (protege `/admin` con un guard).

- **`ClienteMenu.vue`** — consume `/api/configuracion/publica/` y `/api/platos/`,
  `/api/categorias/`; pinta colores y tipografía como variables CSS tomadas de la
  respuesta, no escritas a mano
- **`admin/AdminLogin.vue`** — login contra `/api/auth/login/`, guarda el token
- **`admin/AdminConfiguracion.vue`** — lista los 23 parámetros agrupados, edita texto y
  color, guarda con `PATCH`

## Verificado de punta a punta

1. La página del cliente carga 19 platos reales desde Postgres, con sus 19 fotos
   (servidas por Django, cargadas en Vue sin problema de CORS)
2. El color de marca pintado por Vue (`rgb(0, 71, 60)`) coincide exacto con el valor
   guardado en la base (`#00473C`); la tipografía también coincide (`Sofia Sans`)
3. `/admin` sin sesión redirige a `/admin/login` (guard de ruta funcionando)
4. Login real, redirección a `/admin`, carga de los 23 parámetros
5. **Se editó "Nombre del restaurante" desde el panel Vue → se guardó en Postgres →
   la página del cliente lo mostró actualizado al recargar.** Ciclo completo probado, no
   simulado. Se revirtió el valor de prueba al terminar
6. Escritura sin token → 401. Escritura con token → 200

## Falsa alarma (tercera de la sesión)

Al probar `curl ... | python -m json.tool` para inspeccionar la API, apareció un
guion en-dash mostrado como `â€“` en vez de `–` — parecía corrupción
real de datos, a diferencia de las mojibake anteriores (que eran solo el terminal).
Se verificó en tres capas: bytes del archivo fuente (correctos), valor en Postgres vía ORM
(correcto), **bytes crudos de la respuesta HTTP guardados a archivo** (UTF-8 válido,
correcto). La causa: `python -m json.tool` en este entorno Windows/Git Bash decodifica
`stdin` con el codepage de la consola en vez de UTF-8 cuando recibe una tubería — un
defecto de la herramienta de prueba, no del sistema.

## Estado al cierre

- [[SPEC-007 - Administracion y Parametrizacion]]: identidad visual y API, **hechas**;
  panel Vue, en progreso (falta imágenes y CRUD de menú)
- Backend en `http://localhost:8000` (API bajo `/api/`), frontend en
  `http://localhost:5173`
- Pendiente inmediato: CRUD de menú desde Vue, edición de imágenes, y portar el diseño
  visual de Fase 0 (`/prototipo`) a `ClienteMenu.vue` — hoy es funcional pero no es ese
  diseño

## Enlaces

- [[SPEC-007 - Administracion y Parametrizacion]]
- [[ADR-006 - Stack Django, Vue y PostgreSQL]]
- [[SPEC-009 - Portabilidad Multi-restaurante]]
- [[Inicio]]
