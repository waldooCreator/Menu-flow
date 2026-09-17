"""
Búsqueda en el libro de caja y en el historial de turnos (SPEC-024).

Todo se filtra **en la base**, sobre la historia completa. El historial de
turnos anterior traía los últimos 100 y filtraba esa lista en pantalla: el
turno 101 no se podía encontrar nunca. Esto existe para que eso no vuelva a
pasar.
"""

import re

from django.contrib.auth import get_user_model
from django.db.models import (
    Case, Count, ExpressionWrapper, F, IntegerField, OuterRef, Q, Subquery, Sum, Value, When,
)
from django.db.models.functions import Abs, Coalesce

from .models import MovimientoCaja, Turno
from .operaciones import caja_efectivo

LIMITE_MOVIMIENTOS = 100
LIMITE_TURNOS = 25
LIMITE_MAXIMO = 500


class FiltroInvalido(ValueError):
    """Un parámetro que no se puede interpretar; el mensaje es para mostrarlo."""


def _entero(params, clave, minimo=None):
    valor = params.get(clave)
    if valor in (None, ""):
        return None
    try:
        numero = int(str(valor).replace(".", "").replace(",", "").strip())
    except ValueError:
        raise FiltroInvalido(f"«{valor}» no es un número válido.")
    if minimo is not None and numero < minimo:
        raise FiltroInvalido(f"«{valor}» no puede ser menor que {minimo}.")
    return numero


def tanda(params, por_defecto):
    """Qué porción mostrar: `desde_fila` y `limite`, con un tope para no traer todo de golpe."""
    inicio = _entero(params, "desde_fila", minimo=0) or 0
    limite = _entero(params, "limite", minimo=1) or por_defecto
    return inicio, min(limite, LIMITE_MAXIMO)


def _personas(filtro):
    Usuario = get_user_model()
    return [
        {"id": u["id"], "username": u["username"]}
        for u in Usuario.objects.filter(filtro).distinct().order_by("username").values("id", "username")
    ]


# --------------------------------------------------------------------------
# Libro de caja
# --------------------------------------------------------------------------

def filtrar_movimientos(params):
    """
    Los movimientos del libro que cumplen TODOS los filtros de `params`.

    El texto (`q`) busca en la descripción sin distinguir mayúsculas ni tildes,
    **o** por el número de tiquete de la venta. El tiquete se busca por su
    parte numérica, así "Ef-2026-00123", "00123" y "123" encuentran lo mismo.
    """
    movs = MovimientoCaja.objects.select_related(
        "caja", "autor", "turno", "categoria", "cuenta__medio_pago")

    # Las fechas se interpretan en la zona horaria local, no en UTC: un
    # movimiento de las 8 de la noche en Cúcuta es de HOY para quien cuadra.
    if params.get("desde"):
        movs = movs.filter(creado__date__gte=params["desde"])
    if params.get("hasta"):
        movs = movs.filter(creado__date__lte=params["hasta"])
    if params.get("caja"):
        movs = movs.filter(caja_id=params["caja"])
    if params.get("tipo") in (MovimientoCaja.INGRESO, MovimientoCaja.EGRESO):
        movs = movs.filter(tipo=params["tipo"])
    if params.get("concepto"):
        movs = movs.filter(concepto=params["concepto"])
    if params.get("categoria"):
        movs = movs.filter(categoria_id=params["categoria"])
    if params.get("autor"):
        movs = movs.filter(autor_id=params["autor"])

    # Con valor exacto, el rango no se usa: pedir "100.000 exacto y entre 50 y
    # 80 mil" no tiene respuesta, y en silencio devolvería vacío.
    exacto = _entero(params, "monto", minimo=0)
    if exacto is not None:
        movs = movs.filter(monto=exacto)
    else:
        minimo = _entero(params, "monto_min", minimo=0)
        maximo = _entero(params, "monto_max", minimo=0)
        if minimo is not None:
            movs = movs.filter(monto__gte=minimo)
        if maximo is not None:
            movs = movs.filter(monto__lte=maximo)

    texto = (params.get("q") or "").strip()
    if texto:
        condicion = Q(descripcion__unaccent__icontains=texto)
        numero = re.search(r"(\d+)\s*$", texto)
        if numero:
            condicion |= Q(cuenta__tiquete_numero=int(numero.group(1)))
        movs = movs.filter(condicion)

    # Orden TOTAL, desempatado por id. Con solo la fecha, dos movimientos del
    # mismo instante (un traslado crea dos) no tienen orden fijo, y al pedir la
    # siguiente tanda la base puede repetir uno y saltarse otro.
    return movs.order_by("-creado", "-id")


def personas_del_libro():
    """Quienes han registrado algo en el libro: las opciones del filtro "Registró"."""
    return _personas(Q(movimientos_caja__isnull=False))


# --------------------------------------------------------------------------
# Historial de turnos
# --------------------------------------------------------------------------

CUADRO, FALTO, SOBRO, SIN_CONTAR = "cuadro", "falto", "sobro", "sin_contar"


def con_diferencia(turnos):
    """
    Anota en cada turno `esperado` y `diferencia`, calculados en la base.

    Es **la misma cuenta que `cuadre_de`** (SPEC-014): lo que entró menos lo
    que salió de la caja de efectivo en ese turno, y contado menos esperado.
    Se repite aquí como expresión de base de datos porque filtrar y ordenar
    cientos de turnos llamando `cuadre_de` uno por uno sería lento; una prueba
    comprueba que las dos dan el mismo número.

    Sin conteo (turno abierto), la diferencia queda nula.
    """
    efectivo = caja_efectivo()
    if efectivo is None:
        esperado = Value(0, output_field=IntegerField())
    else:
        neto = (
            MovimientoCaja.objects.filter(turno=OuterRef("pk"), caja=efectivo)
            .values("turno")
            .annotate(neto=Sum(Case(
                When(tipo=MovimientoCaja.INGRESO, then=F("monto")),
                default=F("monto") * -1,
                output_field=IntegerField(),
            )))
            .values("neto")
        )
        esperado = Coalesce(Subquery(neto, output_field=IntegerField()), 0)

    return turnos.annotate(esperado=esperado).annotate(
        diferencia=ExpressionWrapper(
            F("efectivo_contado") - F("esperado"), output_field=IntegerField()),
    )


def filtrar_turnos(params):
    turnos = con_diferencia(Turno.objects.select_related("responsable", "cerrado_por"))

    # Por la fecha en que se ABRIÓ: un turno de noche que cierra de madrugada
    # pertenece al día en que empezó.
    if params.get("desde"):
        turnos = turnos.filter(abierto_en__date__gte=params["desde"])
    if params.get("hasta"):
        turnos = turnos.filter(abierto_en__date__lte=params["hasta"])
    if params.get("responsable"):
        turnos = turnos.filter(responsable_id=params["responsable"])
    if params.get("cerrado_por"):
        turnos = turnos.filter(cerrado_por_id=params["cerrado_por"])
    if params.get("estado") in (Turno.ABIERTO, Turno.CERRADO):
        turnos = turnos.filter(estado=params["estado"])

    cuadre = params.get("cuadre")
    if cuadre == CUADRO:
        turnos = turnos.filter(diferencia=0)
    elif cuadre == FALTO:
        turnos = turnos.filter(diferencia__lt=0)
    elif cuadre == SOBRO:
        turnos = turnos.filter(diferencia__gt=0)
    elif cuadre == SIN_CONTAR:
        turnos = turnos.filter(efectivo_contado__isnull=True)

    minimo = _entero(params, "diferencia_min", minimo=0)
    if minimo:
        turnos = turnos.annotate(diferencia_abs=Abs("diferencia")).filter(diferencia_abs__gte=minimo)

    orden = params.get("orden")
    if orden == "faltante":
        turnos = turnos.order_by(F("diferencia").asc(nulls_last=True), "-abierto_en", "-id")
    elif orden == "sobrante":
        turnos = turnos.order_by(F("diferencia").desc(nulls_last=True), "-abierto_en", "-id")
    else:
        # Desempate por id, por lo mismo que en el libro: sin orden total, las
        # tandas de "Cargar más" pueden repetir o saltarse turnos.
        turnos = turnos.order_by("-abierto_en", "-id")
    return turnos


def resumen_de_turnos(turnos):
    """Del filtro completo: cuántos, y cuántos faltaron y sobraron con sus sumas."""
    datos = turnos.order_by().aggregate(
        total=Count("id"),
        con_faltante=Count("id", filter=Q(diferencia__lt=0)),
        faltante=Sum("diferencia", filter=Q(diferencia__lt=0)),
        con_sobrante=Count("id", filter=Q(diferencia__gt=0)),
        sobrante=Sum("diferencia", filter=Q(diferencia__gt=0)),
    )
    return {
        "total": datos["total"],
        "con_faltante": datos["con_faltante"],
        "faltante": abs(datos["faltante"] or 0),
        "con_sobrante": datos["con_sobrante"],
        "sobrante": datos["sobrante"] or 0,
    }


def personas_de_turnos():
    """Responsables y quienes han cerrado turnos: las opciones de los dos filtros de persona."""
    return {
        "responsables": _personas(Q(turnos__isnull=False)),
        "cerradores": _personas(Q(turnos_cerrados__isnull=False)),
    }
