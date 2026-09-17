---
tipo: bitacora
fecha: 2026-08-24
tags: [bitacora, qr, prueba-tecnica, vue]
---

# 2026-08-24 — Prueba técnica del QR y arquitectura Vue confirmada

Segunda tanda del día, después de [[2026-08-24 - Backend Django y primera configuracion real]].

## Decisión de arquitectura

El autor cerró la pregunta bloqueante que quedó abierta en el ADR: **la página del cliente
se sirve en Vue, no en Django.** Y fue más allá de eso: **nada se gestiona desde el admin
de Django** — el que se construyó ayer fue un peldaño de validación, no el destino. Todo
pasa a un panel Vue, incluida la administración.

Actualizado [[ADR-006 - Stack Django, Vue y PostgreSQL]], [[Preguntas Abiertas]] y
[[SPEC-007 - Administracion y Parametrizacion]] con esta decisión y el riesgo que reabre
(el salto de paleta por defecto en la primera pintura de una SPA), que queda anotado como
algo a mitigar cuando se construya esa página.

## Prueba técnica del QR

Con permiso ya dado por el autor, se ejecutó una prueba real (no solo investigación de
escritorio) en `pruebas/prueba-qr/`: generar, firmar, renderizar a píxeles, decodificar con
una librería de escaneo real y verificar — el pipeline completo de SPEC-002.

**Resultado: funciona, con un hallazgo que corrige la spec y una recomendación que la
mejora.**

### El hallazgo

La estimación original de SPEC-002 para un carrito de 30 items ("~700 caracteres") estaba
casi 3 veces por debajo de la realidad: **medido, dio 1.767 bytes**, porque la estimación no
contaba con observaciones en lenguaje natural real. Ese carrito **no genera un QR
escaneable de forma práctica** (versión 35, muy denso) y un carrito de 50 items directamente
**no cabe en ningún QR** — la librería lo rechazó.

Esto no es un problema: es la prueba real de que el "Plan B" que ya estaba en la spec (tabla
temporal + token corto) es necesario, no un caso teórico de sobra.

### La recomendación

Probé codificar las observaciones rápidas como **índice** a `ObservacionRapida` en vez de
como texto completo. Resultado: el mismo carrito de 30 items baja de 1.767 a **547 bytes —
69% menos** — y el QR pasa de versión 35 (impráctico) a versión 18 (cómodo). Se agregó como
regla en [[SPEC-002 - QR de Pedido]] y [[SPEC-003 - Menu del Cliente]].

### Verificado

- Firma HMAC alterada → rechazada, con comparación en tiempo constante
- Payload recuperado idéntico al original en todos los casos que generaron QR
- Robustez ante ruido + desenfoque (aproximación de una foto de cámara imperfecta) → decodificó bien
- Tiempos: pedidos normales bajo 150ms de punta a punta; el caso pesado de 30 items en
  texto libre, ~525ms — sigue siendo subsegundo
- Se generó un QR real (`pruebas/prueba-qr/salida/pedido-ejemplo.png`) y se envió al autor
  para escanear con su propio teléfono como verificación independiente

Todos los números y la metodología completa quedaron en
[[Viabilidad Tecnica del QR]].

## Estado al cierre

- [[ADR-006 - Stack Django, Vue y PostgreSQL]]: arquitectura de servido confirmada (todo Vue)
- [[SPEC-002 - QR de Pedido]]: números corregidos con datos medidos, nueva regla de
  codificación por índice
- Prueba técnica del QR: **concluida, con resultado positivo**
- Pendiente inmediato: diseñar la mitigación del salto de paleta en la SPA de Vue, y
  arrancar el panel Vue de administración (reemplaza al Django admin)

## Enlaces

- [[SPEC-002 - QR de Pedido]]
- [[SPEC-003 - Menu del Cliente]]
- [[Viabilidad Tecnica del QR]]
- [[ADR-001 - QR autocontenido y firmado]]
- [[ADR-006 - Stack Django, Vue y PostgreSQL]]
- [[Inicio]]
