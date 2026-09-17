"""
Las operaciones que cambian un pedido YA enviado a cocina (SPEC-011).

Viven aquí y no en las vistas por la misma razón que `estaciones/ruteo.py`:
una responsabilidad, testeable sin HTTP, y reutilizable desde un comando o
desde otra vista sin arrastrar `request`.

Regla que gobierna todo el módulo (ADR-007): **una novedad es un hecho que
se agrega, nunca una corrección del hecho anterior**. Cada función de aquí
escribe en `Novedad` — tabla de solo inserción — además de dejar
`DetallePedido` reflejando lo que finalmente se sirve.
"""

from django.db import transaction
from django.db.models import Q

from estaciones.ruteo import rutear_pedido
from menu.models import Plato
from menu.promociones import desglose_para_congelar, motivo_no_disponible, se_puede_vender

from .models import DetallePedido, Mesa, Novedad, Pedido

# Un pedido entregado o anulado ya no se edita: eso es una devolución, que
# es otro camino (SPEC-011, regla 5).
ESTADOS_EDITABLES = (Pedido.PENDIENTE, Pedido.EN_PREPARACION, Pedido.LISTO)


class NovedadInvalida(Exception):
    """La operación no se puede hacer; el mensaje es para mostrarle al mesero."""


def _verificar_editable(pedido):
    if pedido.estado not in ESTADOS_EDITABLES:
        raise NovedadInvalida(
            f"El pedido está «{pedido.get_estado_display()}» y ya no se puede editar."
        )


def _verificar_cuenta_abierta(pedido):
    """
    Lo que cambia el dinero de un pedido exige que su cuenta siga abierta
    (SPEC-013, regla 5). Se llama DENTRO de la transacción y bloquea la
    cuenta, como el cobro (ADR-008): sin eso, un plato agregado en el mismo
    instante en que se cobra quedaría servido y sin cobrar. La prueba de
    estrés del 2026-09-16 lo encontró: $52.000 en tres pedidos.
    """
    from ventas.models import Cuenta

    if pedido.cuenta_id is None:
        return
    cuenta = Cuenta.objects.select_for_update().get(pk=pedido.cuenta_id)
    if cuenta.estado != Cuenta.ABIERTA:
        raise NovedadInvalida(
            "Este pedido ya se cobró. Para pedir algo más, crea un pedido nuevo: "
            "se abre una cuenta nueva."
        )


def _anotar(pedido, tipo, descripcion, autor, antes="", despues="", estacion=None,
            comanda=None):
    """
    Registra la novedad y despierta a las estaciones afectadas.

    Una comanda que ya estaba LISTA se reabre: el plato está en la barra con
    la etiqueta equivocada (SPEC-011).
    """
    afectadas = [comanda] if comanda else list(pedido.comandas.all())
    estaba = comanda.estado if comanda else ""

    novedad = Novedad.objects.create(
        pedido=pedido, tipo=tipo, descripcion=descripcion, autor=autor,
        antes=antes, despues=despues, estacion=estacion, comanda_estaba=estaba,
    )

    for c in afectadas:
        c.reabrir_por_novedad()

    return novedad


def cambiar_destino(pedido, autor, mesa_codigo=None, es_domicilio=False):
    """
    Mover el pedido a otra mesa, o pasarlo a domicilio (SPEC-011).

    Los dos casos son el mismo: cambiar a dónde va. Ocupar la mesa nueva es
    el mismo criterio de SPEC-012 — si hay un pedido ahí, hay gente. La mesa
    VIEJA no se libera sola: eso sería el sistema adivinando que la gente se
    esfumó. Se le ofrece al mesero, que está ahí y sabe.
    """
    _verificar_editable(pedido)
    antes = pedido.destino

    mesa = None
    if not es_domicilio:
        mesa = Mesa.objects.filter(codigo=mesa_codigo, activa=True).first()
        if mesa is None:
            raise NovedadInvalida("Esa mesa no existe o está desactivada.")

    despues = "Domicilio" if es_domicilio else mesa.nombre
    if antes == despues:
        raise NovedadInvalida(f"El pedido ya estaba en «{despues}».")

    with transaction.atomic():
        pedido.mesa = mesa
        pedido.es_domicilio = es_domicilio
        pedido.save(update_fields=["mesa", "es_domicilio"])

        if mesa is not None:
            mesa.cambiar_estado(Mesa.OCUPADA)

        _anotar(pedido, Novedad.CAMBIO_DESTINO, f"{antes} → {despues}", autor,
                antes=antes, despues=despues)

    return pedido


def agregar_item(pedido, autor, plato_id, cantidad=1, observacion=""):
    """
    Agrega un plato a un pedido en curso.

    **Congela el precio del momento de agregarlo**, no el del pedido
    original (SPEC-011, regla 2): si el menú cambió en el intermedio, es
    correcto que cueste lo de ahora.
    """
    _verificar_editable(pedido)
    if cantidad < 1:
        raise NovedadInvalida("La cantidad debe ser al menos 1.")

    plato = Plato.objects.filter(id=plato_id).first()
    if plato is None:
        raise NovedadInvalida("Ese plato ya no existe en el menú.")
    if not se_puede_vender(plato):
        raise NovedadInvalida(motivo_no_disponible(plato))

    with transaction.atomic():
        _verificar_cuenta_abierta(pedido)
        detalle = DetallePedido.objects.create(
            pedido=pedido, plato=plato,
            nombre_congelado=plato.nombre, precio_congelado=plato.precio,
            desglose_congelado=desglose_para_congelar(plato),
            cantidad=cantidad, observacion=observacion,
        )
        # Rutea el renglón nuevo: si cae en una estación que aún no tenía
        # comanda, se la crea; si ya la tenía, se le suma.
        rutear_pedido(pedido)
        detalle.refresh_from_db()

        # Se despierta SOLO la estación que recibe el plato: agregar un trago
        # no tiene por qué reabrir la comanda de la cocina.
        comanda = detalle.comanda
        _anotar(pedido, Novedad.AGREGAR_ITEM,
                f"+ {cantidad}× {plato.nombre}", autor,
                despues=f"{cantidad}× {plato.nombre}",
                estacion=comanda.estacion if comanda else None, comanda=comanda)

    return pedido


def _detalle_de(pedido, detalle_id):
    detalle = pedido.detalles.filter(id=detalle_id).first()
    if detalle is None:
        raise NovedadInvalida("Ese renglón no pertenece a este pedido.")
    return detalle


def quitar_item(pedido, autor, detalle_id):
    """
    Quita un renglón.

    **Quitar un plato ya cocinado no lo descocina** (SPEC-011, regla 3): la
    novedad guarda en qué estado estaba su comanda, para que la merma quede
    registrada aunque valorarla sea trabajo de SPEC-008.
    """
    _verificar_editable(pedido)
    detalle = _detalle_de(pedido, detalle_id)

    # Vaciar el pedido editando sería anularlo por la puerta de atrás, sin
    # motivo ni responsable (SPEC-011, regla 4).
    if pedido.detalles.count() <= 1:
        raise NovedadInvalida(
            "Es el único plato del pedido. Para dejarlo sin nada hay que anularlo, "
            "y una anulación exige un motivo."
        )

    with transaction.atomic():
        _verificar_cuenta_abierta(pedido)
        etiqueta = f"{detalle.cantidad}× {detalle.nombre_congelado}"
        comanda = detalle.comanda
        estacion = comanda.estacion if comanda else None
        detalle.delete()

        _anotar(pedido, Novedad.QUITAR_ITEM, f"− {etiqueta}", autor,
                antes=etiqueta, estacion=estacion, comanda=comanda)

    return pedido


def cambiar_cantidad(pedido, autor, detalle_id, cantidad):
    """
    Cambia la cantidad de un renglón.

    **No re-cotiza**: el precio congelado no se toca (SPEC-011, regla 2).
    """
    _verificar_editable(pedido)
    detalle = _detalle_de(pedido, detalle_id)

    if cantidad < 1:
        raise NovedadInvalida("Para dejarlo en cero, quita el plato del pedido.")
    if cantidad == detalle.cantidad:
        raise NovedadInvalida("Esa ya es la cantidad.")

    with transaction.atomic():
        _verificar_cuenta_abierta(pedido)
        antes, despues = detalle.cantidad, cantidad
        detalle.cantidad = cantidad
        detalle.save(update_fields=["cantidad"])

        comanda = detalle.comanda
        _anotar(pedido, Novedad.CAMBIAR_CANTIDAD,
                f"{antes}× → {despues}× {detalle.nombre_congelado}", autor,
                antes=f"{antes}×", despues=f"{despues}×",
                estacion=comanda.estacion if comanda else None, comanda=comanda)

    return pedido


def cambiar_observacion(pedido, autor, detalle_id, observacion):
    """
    Cambia o agrega la observación de un renglón.

    Es la más urgente en el tiempo de toda la familia: "sin cebolla" a los
    30 segundos se atiende, a los cinco minutos ya no.
    """
    _verificar_editable(pedido)
    detalle = _detalle_de(pedido, detalle_id)
    observacion = (observacion or "").strip()

    if observacion == detalle.observacion:
        raise NovedadInvalida("La observación no cambió.")

    with transaction.atomic():
        antes = detalle.observacion
        detalle.observacion = observacion
        detalle.save(update_fields=["observacion"])

        comanda = detalle.comanda
        texto = (
            f"{detalle.nombre_congelado}: AHORA {observacion.upper()}"
            if observacion
            else f"{detalle.nombre_congelado}: se quitó «{antes}»"
        )
        _anotar(pedido, Novedad.CAMBIAR_OBSERVACION, texto, autor,
                antes=antes, despues=observacion,
                estacion=comanda.estacion if comanda else None, comanda=comanda)

    return pedido


def novedades_sin_ver(comanda):
    """
    Las novedades que ESTA estación todavía no marcó como vistas.

    Una novedad sin estación (un cambio de destino) le importa a todas; una
    con estación, solo a la suya — cambiar la observación de un trago no
    tiene por qué poner en rojo la tarjeta de la cocina.
    """
    qs = comanda.pedido.novedades.filter(
        Q(estacion__isnull=True) | Q(estacion=comanda.estacion_id)
    )
    if comanda.novedades_vistas_hasta:
        qs = qs.filter(creada__gt=comanda.novedades_vistas_hasta)
    return qs
