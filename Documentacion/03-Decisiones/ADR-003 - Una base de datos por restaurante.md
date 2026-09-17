---
tipo: adr
id: ADR-003
estado: aceptada
fecha: 2026-08-21
tags: [base-de-datos, arquitectura, portabilidad]
---

# ADR-003 — Una base de datos por restaurante

**Estado:** Aceptada · **Fecha:** 2026-08-21

## Contexto

El sistema debe poder montarse para varios restaurantes. El autor lo describio asi:
exportar las tablas de la base original, cambiarle el nombre y conectarla en otro servidor,
donde estarian solo los datos de ese restaurante.

## Opciones consideradas

**A. Multi-inquilino compartido.** Una sola base con una columna `restaurante_id` en cada
tabla. Es lo habitual en productos SaaS. Permite un panel central y ahorra infraestructura,
pero cada consulta debe filtrar correctamente y un error expone datos de otro restaurante.

**B. Una base de datos por restaurante.** Cada restaurante vive aislado en su propia base.

## Decision

**Opcion B.** Una base por restaurante, autosuficiente y portable.

## Justificacion

- Es exactamente el modelo mental del autor, y el mas simple para lo que quiere
- **Aislamiento total:** es imposible que un restaurante vea datos de otro, porque no
  comparten base
- Mudar un restaurante de servidor es copiar una base
- No hace falta filtrar por inquilino en cada consulta, lo que elimina toda una clase de
  errores de seguridad

## Consecuencias

**Positivas**
- Aislamiento por construccion
- Portabilidad trivial
- Consultas mas simples

**Negativas / a vigilar**
- No hay panel central que vea todos los restaurantes a la vez
- Una actualizacion de esquema hay que aplicarla a cada base (de ahi la necesidad de
  migraciones versionadas)
- Mas bases que administrar y respaldar
- **Las imagenes del menu no viajan en el dump.** Hay que copiar tambien la carpeta de
  archivos subidos

## Enlaces

- [[SPEC-009 - Portabilidad Multi-restaurante]]
- [[SPEC-007 - Administracion y Parametrizacion]]
