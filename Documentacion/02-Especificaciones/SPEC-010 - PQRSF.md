---
tipo: spec
id: SPEC-010
estado: borrador
actualizado: 2026-08-21
tags: [pqrsf, cliente, admin]
---

# SPEC-010 — PQRSF

> [!warning] Estado: Borrador
> Faltan decisiones basicas. Es de las ultimas en implementarse (Fase 2).

## Proposito

Dar al cliente un canal para enviar Peticiones, Quejas, Reclamos, Sugerencias y
Felicitaciones, y al administrador un lugar donde leerlas.

## Alcance

- Formulario accesible desde la pagina del cliente
- Bandeja de entrada en el modulo de administracion

## Fuera de alcance

- Encuestas de satisfaccion automaticas
- Integracion con redes sociales o resenas externas

## Comportamiento

1. El cliente accede al formulario desde la seccion "Encuentranos" de la pagina
2. Elige el tipo (peticion, queja, reclamo, sugerencia, felicitacion) y escribe el mensaje
3. El mensaje llega a la bandeja del administrador
4. Si la sesion tiene mesa asociada, se guarda para dar contexto

## Criterios de aceptacion

- [ ] El cliente puede enviar un PQRSF desde la pagina
- [ ] El administrador ve los mensajes clasificados por tipo
- [ ] Si el cliente venia de una mesa, el mensaje conserva ese dato
- [ ] El envio esta protegido contra abuso automatizado

## Dependencias

- [[SPEC-003 - Menu del Cliente]] — donde vive el acceso
- [[SPEC-007 - Administracion y Parametrizacion]] — donde se leen

## Preguntas abiertas

- Puede el cliente anonimo enviarlo sin identificarse, o se le pide nombre y contacto?
- El administrador responde dentro del sistema, o solo lee y contesta por fuera?
- Hay notificacion al administrador cuando entra un PQRSF nuevo?
