---
tipo: metodologia
actualizado: 2026-08-21
tags: [metodologia, sdd, proceso]
---

# Metodologia — Spec Driven Development

> [!important] Esta es la forma de trabajo acordada para el proyecto.
> Aplica tanto al humano como a Claude. Si vas a escribir codigo, primero busca su spec.

## El principio

**La especificacion es la fuente de verdad. El codigo es su implementacion.**

No al reves. Si el codigo hace algo que la spec no dice, o el codigo esta mal o la spec
esta incompleta — pero nunca se resuelve "dejando el codigo como quedo".

## Las reglas

1. **Nada se construye sin una spec aprobada.** Ni siquiera un prototipo de funcionalidad.
   (El prototipo *visual* de Fase 0 es la excepcion deliberada: existe para descubrir la
   spec de diseno, no para implementarla.)

2. **Todo cambio de comportamiento empieza por la spec.** Se edita la spec, se aprueba,
   y despues se toca el codigo. Nunca al reves.

3. **Cada spec tiene criterios de aceptacion verificables.** Si un criterio no se puede
   comprobar con una prueba o una demostracion concreta, esta mal escrito.

4. **Las decisiones arquitectonicas van a un ADR, no a la spec.** La spec dice *que* debe
   pasar; el ADR dice *por que* se eligio ese camino y que se descarto.

5. **El codigo referencia el ID de la spec.** Un comentario `// SPEC-005` en el modulo de
   ruteo vale mas que cualquier documentacion suelta.

6. **Lo que no esta en la spec, esta fuera de alcance.** Si aparece algo nuevo a mitad de
   camino, se anota en la bitacora y se decide despues; no se cuela en la implementacion.

## Estados de una spec

```
Borrador --> En revision --> Aprobada --> Implementada
                                 |
                                 +--> Obsoleta (reemplazada por otra spec)
```

- **Borrador** — se esta escribiendo, faltan decisiones
- **En revision** — completa, esperando aprobacion
- **Aprobada** — lista para implementar, no se cambia sin volver a aprobar
- **Implementada** — el codigo existe y cumple los criterios de aceptacion
- **Obsoleta** — la reemplazo otra; se conserva por historia

## El ciclo de trabajo

1. **Idea** — aparece algo nuevo, se anota en la [[2026-08-21 - Arranque y prototipo visual|bitacora]] del dia
2. **Spec** — se redacta con la [[Plantilla SPEC]], estado Borrador
3. **Decision** — si hay que elegir entre caminos, sale un ADR con la [[Plantilla ADR]]. El registro diario usa la [[Plantilla Bitacora]]
4. **Aprobacion** — la spec pasa a Aprobada
5. **Implementacion** — se construye contra los criterios de aceptacion
6. **Cierre** — la spec pasa a Implementada y se anota en la bitacora

## Que debe contener una spec

- **Proposito** — que problema resuelve, en una frase
- **Alcance** — que incluye
- **Fuera de alcance** — que NO incluye (tan importante como lo anterior)
- **Comportamiento** — como funciona, paso a paso
- **Criterios de aceptacion** — lista verificable
- **Dependencias** — que otras specs necesita
- **Preguntas abiertas** — lo que falta decidir

## Nota para Claude

Cuando retomes este proyecto:

1. Lee [[Inicio]] para el estado general
2. Lee esta nota para saber como trabajar
3. Antes de escribir codigo, **busca y lee la spec correspondiente**
4. Si te piden algo sin spec, **propon escribir la spec primero**
5. Al terminar, actualiza el estado de la spec y anota en la bitacora
