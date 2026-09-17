---
fecha: 2026-09-07
tipo: bitacora
specs: [SPEC-007, SPEC-003, SPEC-002]
---

# 2026-09-07 — Parametrizacion de menu y negocio

La auditoria encontro valores que hacian que el sistema pareciera de un solo
restaurante aunque la base ya fuera configurable.

## Corregido

- Las metricas de cada plato ya se editan desde Admin → Menu: valor y etiqueta
  libres, sin lista fija de proteina, gramos o calorias.
- Moneda y locale se administran desde Operacion y se usan en todas las
  pantallas con importes.
- La vigencia del QR de pedido deja de estar fija en codigo.
- Los umbrales amarillo y rojo del cronometro de cocina son configurables.
- Titulos de ubicacion, bloques de contacto y texto de pie del sitio son
  parametros de identidad.
- "Agotado hoy" se puede cambiar desde configuracion.
- La etiqueta `picante` ya no recibe un tratamiento visual especial escrito en
  codigo; todas las etiquetas del menu son datos.

## Lo que sigue fijo a proposito

Los nombres de modulos, roles, estados de flujo y acciones como "Cobrar" o
"Enviar a cocina" son estructura de la aplicacion, no contenido propio de un
restaurante. Los placeholders de ayuda son instrucciones de uso, no datos del
negocio.
