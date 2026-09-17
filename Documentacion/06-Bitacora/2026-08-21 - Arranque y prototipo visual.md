---
tipo: bitacora
fecha: 2026-08-21
tags: [bitacora]
---

# 2026-08-21 — Arranque y prototipo visual

## Que se hizo

1. **Lectura de la idea original.** Nota manuscrita con 6 requisitos, leida desde un PDF
   escaneado (una sola pagina, imagen sin texto).

2. **Ronda de aclaraciones** que definio: como llega el pedido a las estaciones (solo
   mensajes en la app, tablero de cards), que no hay pagos ni facturacion, el QR de mesa,
   y el soporte multi-estacion con ruteo por categoria.

3. **Investigacion de viabilidad del QR.** Confirmado con precedentes reales. Hallazgo
   importante: Safari/iOS no soporta `BarcodeDetector`.
   Ver [[Viabilidad Tecnica del QR]].

4. **Busqueda de referencias visuales.** Dos rondas: la primera resulto demasiado clasica,
   la segunda (moderna) dio en el blanco. Ver [[Referencias Visuales]].

5. **Prototipo visual, primer intento — fallido.** Se construyo con degradados CSS como
   relleno de foto. Resultado plano y generico. Criticado con razon por el autor.

6. **Analisis medido de Sweetgreen.** Se extrajeron los estilos computados reales via
   archivo web. Ver [[Analisis de Sweetgreen]].

7. **Prototipo visual, segundo intento — exitoso.** Reconstruido sobre el sistema medido,
   con 24 fotografias reales descargadas y asignadas plato por plato. Aprobado por el autor.

8. **Montaje de esta boveda** y adopcion de
   [[Metodologia - Spec Driven Development|Spec Driven Development]].

## Decisiones tomadas hoy

- [[ADR-001 - QR autocontenido y firmado]]
- [[ADR-002 - El mesero confirma el pedido]]
- [[ADR-003 - Una base de datos por restaurante]]
- [[ADR-004 - LISTO y ENTREGADO son estados distintos]]
- [[ADR-005 - Escaneo con libreria JS]]

## Lecciones

> [!quote] La foto ES el diseno
> El primer prototipo fallo por una sola razon: usar degradados en lugar de fotografia real.
> Ningun ajuste de CSS compensa eso.

> [!quote] Medir antes de opinar
> El segundo intento funciono porque se extrajeron los valores reales del sitio de
> referencia en lugar de imitarlo de memoria.

## Estado al cierre

- Fase 0 terminada
- Stack **sin definir** — decision bloqueante para Fase 1
- Proximo paso: elegir stack y arrancar por [[SPEC-002 - QR de Pedido]]

## Enlaces

- [[Inicio]]
- [[Preguntas Abiertas]]
