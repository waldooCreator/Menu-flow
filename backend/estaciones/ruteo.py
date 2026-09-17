"""
Distribuidor de pedidos a estaciones (SPEC-005).

Responsabilidad única: SOLO divide un pedido ya confirmado en comandas.
No lo guarda (ya viene guardado), no notifica, no imprime.

Abierto/cerrado: agregar una estación o mover una categoría de una a otra
es cambiar `Categoria.estacion` desde el panel — esta función no cambia.
"""

from django.db import transaction

from configuracion.helpers import config

from .models import Comanda, Estacion

CLAVE_UNIFICADAS = "estaciones-unificadas"


def estaciones_unificadas():
    """
    SPEC-023, sección 7: con el interruptor encendido todo llega a la
    estación por defecto. Se lee en cada ruteo, no se guarda en las
    categorías: apagarlo devuelve cada plato a su estación sin reconfigurar
    nada.
    """
    return config(CLAVE_UNIFICADAS, False) is True


def _estacion_por_defecto():
    return Estacion.objects.filter(por_defecto=True).first() or Estacion.objects.order_by("orden").first()


def rutear_pedido(pedido):
    """
    Agrupa los `DetallePedido` de `pedido` por la estación de su categoría,
    y crea una Comanda por cada estación involucrada.

    **Rutea solo lo que falta por rutear**, reusando las comandas que ya
    existan. Eso lo hace idempotente (correrlo dos veces no duplica nada) y
    además sirve para el ruteo incremental de SPEC-011: un plato agregado a
    un pedido en curso tiene que llegar a su estación.

    > Antes salía por la puerta de atrás con `if pedido.comandas.exists():
    > return`. Era idempotente en el sentido inútil de la palabra: un plato
    > agregado después se quedaba sin comanda y **no llegaba nunca a la
    > cocina**.
    """
    fallback = _estacion_por_defecto()
    unificadas = estaciones_unificadas()
    # Las que ya existen se reusan; no se crea una segunda comanda de cocina
    # porque hayan pedido otra hamburguesa.
    comandas_por_estacion = {c.estacion_id: c for c in pedido.comandas.all()}

    with transaction.atomic():
        detalles = (
            pedido.detalles.filter(comanda__isnull=True)
            .select_related("plato__categoria__estacion")
        )
        for detalle in detalles:
            # Una promoción no tiene categoría: el combo entero va a la
            # estación por defecto, bebidas incluidas (SPEC-023).
            categoria = detalle.plato.categoria
            if unificadas or categoria is None:
                estacion = fallback
            else:
                estacion = categoria.estacion or fallback
            if estacion is None:
                raise ValueError(
                    "No hay ninguna estación configurada. Crea al menos una "
                    "y marca una como estación por defecto."
                )
            if estacion.id not in comandas_por_estacion:
                comandas_por_estacion[estacion.id] = Comanda.objects.create(
                    pedido=pedido, estacion=estacion,
                )
            detalle.comanda = comandas_por_estacion[estacion.id]
            detalle.save(update_fields=["comanda"])

    return list(comandas_por_estacion.values())
