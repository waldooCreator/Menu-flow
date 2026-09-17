---
tipo: referencia
actualizado: 2026-09-14
tags: [stack, tecnologias, referencia]
---

# Stack Tecnológico

> [!info] Qué es esto
> Inventario de lo que el proyecto usa hoy, y **para qué se usa cada pieza** — no el
> porqué se eligió (eso vive en [[ADR-006 - Stack Django, Vue y PostgreSQL]] y en los
> demás ADR). Cuando se agregue o cambie una dependencia real, este archivo se
> actualiza junto con el código, no después.

## La regla de fondo

**Django es solo API y permisos — nunca renderiza HTML de negocio.** Todo el
frontend, cliente y paneles internos, vive en Vue y consume `/api/`. Ver
[[ADR-006 - Stack Django, Vue y PostgreSQL]].

## Backend — `backend/`

| Pieza | Versión | Para qué |
|---|---|---|
| [Python](https://www.python.org/) | 3.11 | Runtime del backend |
| [Django](https://www.djangoproject.com/) | 5.0.14 | ORM, migraciones, admin de bajo nivel, `django.core.signing` para firmar el QR |
| [Django REST Framework](https://www.django-rest-framework.org/) | 3.15.2 | Toda la API: serializers, viewsets, permisos por rol |
| [django-filter](https://django-filter.readthedocs.io/) | 24.3 | Filtros de query params en los endpoints de listado |
| [django-cors-headers](https://github.com/adamchainz/django-cors-headers) | 4.4.0 | CORS — hoy no hace falta en dev (proxy de Vite, mismo origen), queda listo para cuando frontend y backend vivan en dominios distintos |
| [psycopg 3](https://www.psycopg.org/psycopg3/) (`binary`) | 3.2.3 | Driver de PostgreSQL |
| [Pillow](https://python-pillow.org/) | 11.0.0 | Procesa las imágenes que sube `configuracion.Parametro` (fotos del menú, hero, decoración) |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.0.1 | Carga `.env` en desarrollo |

**Autenticación:** `TokenAuthentication` de DRF — no JWT, no sesiones de Django para
la API. Permisos cerrados por defecto (`IsAuthenticated`); cada vista pública
declara `AllowAny` explícitamente. Roles (`mesero`, `cajero`, `cocina`, `admin`) son grupos de
Django, comprobados por clases propias en `nucleo/permisos.py`.

**Apps internas** (todas del proyecto, ninguna es una dependencia externa):
`nucleo` (settings, ruteo raíz, permisos, usuarios), `configuracion` (parámetros de negocio,
ver [[SPEC-007 - Administracion y Parametrizacion]]), `menu`, `pedidos`, `estaciones`,
`ventas` (cuenta, caja, turnos, reportes, tiquetes) y `clientes`.

**Excel y tiquetes sin dependencias nuevas:** el `.xlsx` del historial de ventas se arma
a mano con `zipfile` y XML de la biblioteca estándar (`ventas/tiquetes.py`).

## Frontend — `frontend/`

| Pieza | Versión | Para qué |
|---|---|---|
| [Node.js](https://nodejs.org/) | 24 | Runtime de desarrollo/build |
| [Vue 3](https://vuejs.org/) | 3.5 | Todo el frontend, `<script setup>` |
| [Vite](https://vitejs.dev/) | 8.2 | Dev server y build; proxy a Django para `/api` y `/media` (sin CORS, funciona igual desde el celular) |
| [Vue Router](https://router.vuejs.org/) | 4.6 | Rutas + guardia por rol (mesero no entra a cocina, cocina no entra a mesero, ninguno al admin) |
| [Pinia](https://pinia.vuejs.org/) | 4.0 | Estado global: carrito, sesión |
| [Tailwind CSS](https://tailwindcss.com/) | v4 (`@tailwindcss/vite`) | Estilos. Sin `tailwind.config.js`: los tokens del bloque `@theme` apuntan a variables CSS, y esas variables las escribe `aplicarTemaCliente()` en tiempo de ejecución — así la paleta de cada restaurante no exige recompilar |
| [Axios](https://axios-http.com/) | 1.19 | Cliente HTTP hacia `/api/` |
| [qrcode](https://github.com/soldair/node-qrcode) | 1.5 | Genera la imagen del QR del pedido (lado cliente) |
| [qr-scanner](https://github.com/nimiq/qr-scanner) (Nimiq) | 1.4 | Lee el QR con la cámara del mesero — corre en Web Worker. Elegida sobre la API nativa `BarcodeDetector` porque Safari/iOS no la implementa, ver [[ADR-005 - Escaneo con libreria JS]] |
| [Chart.js](https://www.chartjs.org/) | 4.5 | Los gráficos de la pantalla Reportes ([[SPEC-018 - Reportes de Venta]]) |
| [jsQR](https://github.com/cozmo/jsQR) | 1.4 | Lee el QR desde una imagen subida (`<input type="file">`) — camino alterno cuando no hay cámara |

## Base de datos

| Pieza | Versión | Para qué |
|---|---|---|
| [PostgreSQL](https://www.postgresql.org/) | 16 (imagen `postgres:16-alpine`) | Una base **por restaurante** (ADR-003), sin importar el motor en instancias futuras — hoy todas corren Postgres |

En desarrollo corre por Docker Compose (`docker-compose.yml`, raíz del repo):
solo levanta la base de datos — Django y Vite corren nativos, no
contenerizados todavía. El puerto y las credenciales salen de `.env`, sin
`container_name` fijo, para que varias instancias del sistema (una por
restaurante) convivan en el mismo VPS sin chocar nombres.

## Cómo encajan las piezas

```
Cliente (navegador) ──► Vue (frontend/) ──► /api/ ──► Django + DRF (backend/) ──► PostgreSQL
                              │                              │
                         Tailwind v4                   TokenAuthentication
                         (tema por variables CSS)       + permisos por rol
```

- El **QR del pedido** lo firma el backend con `django.core.signing` (no HMAC
  manual): el texto codificado lleva firma y vigencia (6 horas por defecto),
  así no hace falta guardar cada QR en la base — ver [[ADR-001 - QR autocontenido y firmado]].
- Las **notificaciones** (cliente → mesero → cocina) van por *polling*: la campana
  cada 3 segundos, el tablero de cocina cada 5, no WebSockets — Django Channels queda como mejora futura, no
  bloqueante hoy (ver [[SPEC-006 - Notificaciones]]).
- La configuración pública (`configuracion.Parametro`) se sirve con caché de
  60 segundos en memoria de proceso — corto a propósito, para que un cambio
  hecho desde otro proceso (otro worker, un comando de management) converja
  solo sin quedar servido "viejo" para siempre.

## Qué NO usa este proyecto (y por qué importa saberlo)

- **Sin framework de CSS aparte de Tailwind** — nada de Bootstrap ni CSS a mano
  en los componentes nuevos (el `prototipo/` histórico sí tiene CSS plano,
  pero es referencia, no código en producción).
- **Sin JWT** — se usa `TokenAuthentication` simple de DRF.
- **Sin Django Channels todavía** — el tiempo real es *polling*.
- **Sin pasarela de pagos ni facturación electrónica** — fuera de alcance del
  proyecto (ver `CLAUDE.md` en la raíz del repo).
- **Sin impresión de comandas** — todo pedido llega a cocina por mensaje dentro de la
  app. Lo único imprimible es el tiquete de venta ([[SPEC-016 - Tiquete de Venta]]).

## Enlaces

- [[ADR-006 - Stack Django, Vue y PostgreSQL]]
- [[ADR-001 - QR autocontenido y firmado]]
- [[ADR-003 - Una base de datos por restaurante]]
- [[ADR-005 - Escaneo con libreria JS]]
- [[SPEC-007 - Administracion y Parametrizacion]]
- [[Inicio]]
