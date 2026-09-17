---
tipo: producto
actualizado: 2026-08-21
tags: [flujo, recorrido]
---

# Flujo Principal

```
1. El cliente se sienta y ESCANEA EL QR DE SU MESA
        --> abre el sitio con la mesa ya identificada

2. Navega el menu (filtros + imagenes) y arma su pedido

3. Genera el QR DE SU PEDIDO (items, cantidades, observaciones, mesa)

4. El mesero ESCANEA ese QR
        --> la app carga el pedido completo y lo muestra para confirmar
        --> (alternativa: el mesero arma el pedido desde cero, sin QR)

5. El MESERO CONFIRMA y el pedido SE DIVIDE POR ESTACIONES
        --> carne   --> COCINA
        --> helado  --> POSTRES
        --> gaseosa --> BAR

6. Cada estacion ve su comanda como una CARD en su tablero
        --> abre la card, ve el detalle y las especificaciones
        --> "Atras" para volver, o "Listo" cuando termina

7. Al marcar listo, SE NOTIFICA AL MESERO dueno del pedido
        --> burbuja flotante con contador: +1, +4, ...

8. El mesero recoge, lleva a la mesa y marca ENTREGADO
        --> la venta queda registrada, amarrada a el, y auditable
```

## Dos entradas al sistema

| Entrada | Publico | Comportamiento |
|---|---|---|
| **QR de mesa** | Ya esta sentado, con hambre | **Entra directo al menu**, se salta el hero |
| **Enlace directo** (Google, Instagram) | Decide si vale la pena ir | Entra por el hero, con toda la experiencia visual |

Ver [[Modelo de Pagina del Cliente]].

## Estados

```
PEDIDO (vision del mesero y de contabilidad)
  BORRADOR --> PENDIENTE --> EN_PREPARACION --> LISTO --> ENTREGADO
                                                  |
                                                  +--> ANULADO (con motivo y responsable)

COMANDA (vision de cada estacion)
  PENDIENTE --> EN_PREPARACION --> LISTA
```

- **BORRADOR** vive solo en el navegador del cliente o dentro del QR. **No se guarda en BD.**
- **PENDIENTE** — el mesero confirmo; el pedido se creo y se dividio en comandas
- **EN_PREPARACION** — la estacion abrio la card
- **LISTO / LISTA** — la estacion termino. Dispara la notificacion al mesero
- **ENTREGADO** — el mesero lo llevo a la mesa. Apaga la notificacion y cierra la venta

Ver [[ADR-004 - LISTO y ENTREGADO son estados distintos]].

## Enlaces

- [[SPEC-001 - QR de Mesa]]
- [[SPEC-002 - QR de Pedido]]
- [[SPEC-003 - Menu del Cliente]]
- [[SPEC-004 - Modulo Mesero]]
- [[SPEC-005 - Estaciones y Ruteo]]
- [[SPEC-006 - Notificaciones]]
