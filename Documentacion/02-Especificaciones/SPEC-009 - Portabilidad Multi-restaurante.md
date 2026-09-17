---
tipo: spec
id: SPEC-009
estado: aprobada
actualizado: 2026-09-14
tags: [portabilidad, base-de-datos, despliegue]
---

# SPEC-009 — Portabilidad Multi-restaurante

> [!success] Estado: Aprobada — sin probar todavia en un servidor real (revisada 2026-09-14)

## Proposito

Poder montar el sistema para otro restaurante exportando la estructura, importandola en
otro servidor y conectandola, sin tocar codigo.

## Alcance

- Una base de datos por restaurante
- Configuracion externa de la conexion
- Migraciones versionadas

## Fuera de alcance

- Multi-restaurante dentro de una misma instalacion
- Panel central que administre varios restaurantes a la vez

## Comportamiento

**Modelo elegido: una base de datos por restaurante.** No es un sistema compartido con
varios restaurantes adentro. Ver [[ADR-003 - Una base de datos por restaurante]].

> [!info] Aclaracion sobre el despliegue (2026-08-24)
> "Portable" no significa "un restaurante, un servidor". El plan real es **varias
> instancias del sistema conviviendo en el mismo VPS**, cada una con:
>
> - su propio **puerto**
> - su propia **base de datos** (Postgres, un contenedor o esquema por instancia)
> - su propia **carpeta de medios** (`MEDIA_ROOT`)
>
> Aislar por variables de entorno, no por servidor fisico, es lo que hace esto posible.
> Ver [[ADR-006 - Stack Django, Vue y PostgreSQL]].

## Reglas

1. **El nombre de la base de datos no aparece escrito en ninguna parte del codigo.** Solo en
   configuracion externa. Nada de referencias con la base calificada por nombre.

2. **La identidad y la marca del restaurante viven dentro de la misma base**, en una tabla de
   configuracion clave/valor. Asi exportar la base se lleva consigo la personalizacion
   completa y no queda nada por reconfigurar aparte.

3. **Sin referencias entre bases de datos.** Cada base es autosuficiente.

4. **Cuidado con las imagenes del menu.** Si se guardan como archivos en disco, exportar la
   base **no** se las lleva y el restaurante nuevo queda sin fotos. Definir una sola carpeta
   de archivos subidos, guardar rutas relativas, y que esa carpeta viaje con el respaldo.

5. **Migraciones versionadas, no dump/restore** para crear un restaurante nuevo: se corren
   las migraciones sobre una base vacia mas un seed con datos base. Se conserva la opcion de
   exportar/importar para *mudar* un restaurante existente de servidor.

6. **Motor objetivo: PostgreSQL** ([[ADR-006 - Stack Django, Vue y PostgreSQL]]). Se accede
   siempre a traves del ORM de Django — no se descarta usar tipos propios de Postgres
   cuando aportan (p.ej. `JSONField` en `Plato.estadisticas`), pero se evita SQL crudo.

> [!note] Sobre la independencia de motor
> No se persigue independencia total de motor: tiene un costo real de mantenimiento que no
> se justifica aqui. El ORM ya da margen para migrar si algun dia hiciera falta, sin pagar
> el precio de sostener compatibilidad con motores que probablemente nunca se usen.

## Criterios de aceptacion

- [ ] Exportar la base, importarla en otro servidor y cambiar la configuracion basta para
      tener el sistema funcionando
- [x] Ninguna consulta menciona el nombre de la base — revisado 2026-09-14: la conexion
      sale de variables de entorno y el codigo usa el ORM
- [ ] La identidad visual del restaurante viaja dentro del respaldo
- [ ] Crear un restaurante nuevo desde cero toma menos de 30 minutos
- [ ] Las imagenes del menu llegan completas al restaurante nuevo
- [ ] Dos instancias corren a la vez en el mismo servidor sin chocar puertos, base de
      datos ni archivos de medios

## Dependencias

- [[SPEC-007 - Administracion y Parametrizacion]] — la configuracion que viaja
