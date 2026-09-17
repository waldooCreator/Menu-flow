---
tipo: adr
id: ADR-005
estado: aceptada
fecha: 2026-08-21
tags: [qr, navegador, compatibilidad, ios]
---

# ADR-005 — Escaneo con libreria JS, no con la API nativa

**Estado:** Aceptada · **Fecha:** 2026-08-21

## Contexto

El mesero necesita escanear el QR del cliente desde el navegador. Existe una API nativa
para esto, `BarcodeDetector`, que es rapida porque delega en las bibliotecas de vision del
sistema operativo.

## El hallazgo

**Safari en iOS no implementa `BarcodeDetector`, y no hay anuncio de que Apple lo vaya a
agregar.** Solo funciona en Chrome, Edge, Opera y Samsung Internet sobre Android.

Como **todos los navegadores en iPhone usan el motor de Safari por debajo** (incluido Chrome
para iOS), apoyarse solo en esa API deja el escaner **completamente roto en cualquier
iPhone** — y fallando en silencio, que es peor.

## Decision

Implementar el escaner con una **libreria JavaScript** que decodifica por software leyendo
los cuadros de video, y que use la API nativa **solo como acelerador** cuando este disponible.

Candidata: **`qr-scanner`** (Nimiq) — ~16 KB, corre en un Web Worker para no trabar la
interfaz, decodifica a 10-30 cuadros por segundo en un telefono normal, y detecta sola si
puede usar la API nativa.

Alternativas validas: `html5-qrcode`, `jsQR`.

## Consecuencias

**Positivas**
- Funciona en Android y en iPhone
- El Web Worker evita que la interfaz se congele mientras escanea

**Negativas / a vigilar**
- Algo mas lento que la API nativa en los dispositivos que si la soportan
- Una dependencia externa mas que mantener
- Exige HTTPS para acceder a la camara

> [!warning] No cambia el formato del QR
> Esta decision afecta unicamente **como se lee** el QR, no como se construye.
> Ver [[ADR-001 - QR autocontenido y firmado]].

## Enlaces

- [[SPEC-004 - Modulo Mesero]]
- [[Viabilidad Tecnica del QR]]
