"""
Vigencia de las promociones (SPEC-023).

Una sola regla, en un solo sitio. La usan el menú público, la firma y la
confirmación del pedido, las novedades y el panel: si cada uno la
reescribiera, tarde o temprano dirían cosas distintas sobre la misma promo.

La hora es la del restaurante (`TIME_ZONE`), nunca la del navegador.
"""

from datetime import timedelta

from django.utils import timezone

VIGENTE = "vigente"
PROGRAMADA = "programada"
FUERA_DE_HORARIO = "fuera_de_horario"
VENCIDA = "vencida"
APAGADA = "apagada"
AGOTADA = "agotada"

# Lo que el cliente sí debe ver: una promo agotada se muestra en gris, como un
# plato agotado (SPEC-017); las demás no existen para él.
VISIBLES_AL_CLIENTE = {VIGENTE, AGOTADA}


def _dia_de_servicio(plato, local):
    """
    A qué día pertenece este momento dentro de la franja de la promo, o
    `None` si está fuera de la franja.

    Una franja que cruza la medianoche (20:00 a 02:00) le pertenece al día en
    que empezó: la 1:00 del sábado es todavía la noche del viernes. Sin esto,
    una promo "de viernes por la noche" se cortaría a las 12 en punto.
    """
    hoy, hora = local.date(), local.time()
    inicio, fin = plato.hora_inicio, plato.hora_fin
    if inicio is None or fin is None:
        return hoy
    if inicio < fin:
        return hoy if inicio <= hora < fin else None
    # Cruza la medianoche (o inicio == fin, que se lee como 24 horas).
    if hora >= inicio:
        return hoy
    if hora < fin:
        return hoy - timedelta(days=1)
    return None


def estado_promocion(plato, momento=None):
    """
    En qué estado está una promoción ahora (o en `momento`). `None` si el
    plato no es una promoción.

    El orden importa: se explica primero lo que el administrador decidió
    (apagada, fechas) y al final lo que pasó en el servicio (agotada). Una
    promo vencida y además agotada se reporta como vencida, que es la razón de
    fondo por la que no aparece.
    """
    if not plato.es_promocion:
        return None
    if not plato.activa:
        return APAGADA

    local = timezone.localtime(momento or timezone.now())
    dia = _dia_de_servicio(plato, local)
    referencia = dia or local.date()

    if plato.vigente_hasta and referencia > plato.vigente_hasta:
        return VENCIDA
    if plato.vigente_desde and referencia < plato.vigente_desde:
        return PROGRAMADA
    if dia is None or dia.weekday() not in (plato.dias_semana or []):
        return FUERA_DE_HORARIO
    if not plato.disponible:
        return AGOTADA
    return VIGENTE


def se_puede_vender(plato, momento=None):
    """Disponible y, si es promoción, vigente. Lo que se revisa antes de vender."""
    if plato.es_promocion:
        return estado_promocion(plato, momento) == VIGENTE
    return plato.disponible


def motivo_no_disponible(plato, momento=None):
    """El mensaje para el mesero o el cliente cuando no se puede vender."""
    if plato.es_promocion and estado_promocion(plato, momento) not in (VIGENTE, AGOTADA):
        return f"La promoción «{plato.nombre}» ya no está vigente."
    return f"«{plato.nombre}» se agotó."


def desglose_para_congelar(plato):
    """[[cantidad, nombre], ...] tal como está la promo en el momento de venderla."""
    if not plato.es_promocion:
        return []
    return [[c.cantidad, c.nombre] for c in plato.componentes.all()]
