"""
Los cuatro reportes de venta (SPEC-018).

Todo se agrega **en la base de datos**, nunca trayendo filas a memoria para
sumarlas en Python: con miles de ventas eso seria lento sin ninguna razon, y
la base ya sabe hacer justo esto.

Regla que atraviesa el modulo: **solo cuentas cerradas**. Una venta anulada se
devolvio, asi que no se vendio, y sumarla diria que el negocio facturo algo que
no facturo.
"""

from datetime import date, datetime, timedelta

from django.db.models import Avg, Count, ExpressionWrapper, F, IntegerField, Sum
from django.db.models.functions import (
    ExtractHour, ExtractIsoWeekDay, TruncDate, TruncMonth, TruncWeek,
)

from menu.models import Plato
from pedidos.models import DetallePedido, Pedido

from .models import Cuenta

# Cuantos platos y meseros se muestran. Mas alla de eso el grafico deja de
# leerse y el dato deja de servir para decidir nada.
TOPE_PRODUCTOS = 10
TOPE_MESEROS = 10

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

def _valor_renglon():
    """
    Cuanto valio ese renglon: cantidad x precio congelado.

    Es una FUNCION, no una constante, a proposito. Las expresiones de Django
    se mutan al resolverse contra una consulta: reutilizar la misma instancia
    en dos consultas hace que la segunda falle con "is an aggregate". Cada
    llamada devuelve una expresion nueva.

    El `output_field` explicito hace falta porque Django no deduce el tipo de
    una multiplicacion entre dos campos y se niega a sumarla.
    """
    return ExpressionWrapper(
        F("cantidad") * F("precio_congelado"), output_field=IntegerField())


def _cuentas(desde=None, hasta=None):
    """
    Las ventas del rango: cuentas CERRADAS, por fecha de cobro.

    Por fecha de cobro y no de apertura, igual que el historial (SPEC-015):
    una mesa que se sento a las 11 de la noche y pago a las 12 es venta del
    dia en que pago.
    """
    qs = Cuenta.objects.filter(estado=Cuenta.CERRADA)
    if desde:
        qs = qs.filter(cerrada_en__date__gte=desde)
    if hasta:
        qs = qs.filter(cerrada_en__date__lte=hasta)
    return qs


def _renglones(desde=None, hasta=None):
    """
    Los renglones vendidos del rango.

    Se excluyen los pedidos ANULADOS aunque su cuenta este cerrada: un plato
    que se anulo dentro de una cuenta que si se cobro no se vendio.
    """
    return (
        DetallePedido.objects
        .filter(pedido__cuenta__in=_cuentas(desde, hasta))
        .exclude(pedido__estado=Pedido.ANULADO)
    )


def resumen(desde=None, hasta=None):
    """Las cifras de cabecera: cuanto, cuantas y el ticket promedio."""
    datos = _cuentas(desde, hasta).aggregate(
        ventas=Count("id"),
        vendido=Sum("subtotal_congelado"),
        propinas=Sum("propina_congelada"),
        cobrado=Sum("total_congelado"),
        ticket_promedio=Avg("total_congelado"),
    )
    return {
        "ventas": datos["ventas"] or 0,
        "vendido": datos["vendido"] or 0,
        "propinas": datos["propinas"] or 0,
        "cobrado": datos["cobrado"] or 0,
        # Redondeado a peso: mostrar 23.456,78 pesos de ticket promedio sugiere
        # una precision que el dato no tiene.
        "ticket_promedio": round(datos["ticket_promedio"] or 0),
    }


def productos_mas_vendidos(desde=None, hasta=None, solo_promociones=False):
    """
    Por `nombre_congelado`, no por el plato actual: si un plato se renombro,
    lo que se vendio con el nombre viejo se vendio con ese nombre. Agrupar por
    el plato de hoy reescribiria la historia (SPEC-008).

    `solo_promociones` deja el ranking solo con combos (SPEC-023), para
    compararlos entre si sin que el plato mas vendido los tape.
    """
    renglones = _renglones(desde, hasta)
    if solo_promociones:
        renglones = renglones.filter(plato__tipo=Plato.PROMOCION)
    filas = (
        renglones
        .values("nombre_congelado")
        .annotate(
            total=Sum(_valor_renglon()),
            cantidad=Sum("cantidad"),
        )
        .order_by("-cantidad")[:TOPE_PRODUCTOS]
    )
    return [
        {"nombre": f["nombre_congelado"], "cantidad": f["cantidad"], "total": f["total"]}
        for f in filas
    ]


def ventas_por_mesero(desde=None, hasta=None):
    """
    Atribuido a quien TOMO el pedido, no a quien cobro.

    Se suma renglon por renglon, no cuenta por cuenta: una mesa atendida por
    dos meseros reparte su venta entre los dos. Atribuir la cuenta completa al
    que cobro seria mentir sobre el trabajo del otro.

    Se reporta el subtotal (la comida). La propina no es venta del mesero, es
    propina; el impuesto no es de nadie.
    """
    filas = (
        _renglones(desde, hasta)
        .filter(pedido__mesero__isnull=False)
        .values("pedido__mesero__username")
        .annotate(
            vendido=Sum(_valor_renglon()),
            renglones=Sum("cantidad"),
        )
        .order_by("-vendido")[:TOPE_MESEROS]
    )
    return [
        {
            "mesero": f["pedido__mesero__username"],
            "vendido": f["vendido"],
            "renglones": f["renglones"],
        }
        for f in filas
    ]


def ticket_por_dia(desde=None, hasta=None):
    """Evolucion diaria: cuanto entro y cual fue el ticket promedio."""
    filas = (
        _cuentas(desde, hasta)
        .annotate(dia=TruncDate("cerrada_en"))
        .values("dia")
        .annotate(
            ventas=Count("id"),
            cobrado=Sum("total_congelado"),
            ticket_promedio=Avg("total_congelado"),
        )
        .order_by("dia")
    )
    return [
        {
            "fecha": f["dia"].isoformat() if f["dia"] else None,
            "ventas": f["ventas"],
            "cobrado": f["cobrado"] or 0,
            "ticket_promedio": round(f["ticket_promedio"] or 0),
        }
        for f in filas
    ]


def demanda_por_hora(desde=None, hasta=None):
    """
    Cuantas ventas por hora del dia.

    `ExtractHour` sobre un campo con zona horaria devuelve la hora LOCAL
    (America/Bogota), que es lo que significa "a las 8 de la noche" para quien
    arma los turnos. Se devuelven las 24 horas aunque esten en cero: un grafico
    con huecos donde no hubo ventas se lee mal.
    """
    conteo = {
        f["hora"]: f
        for f in _cuentas(desde, hasta)
        .annotate(hora=ExtractHour("cerrada_en"))
        .values("hora")
        .annotate(ventas=Count("id"), cobrado=Sum("total_congelado"))
    }
    return [
        {
            "hora": h,
            "ventas": conteo.get(h, {}).get("ventas", 0),
            "cobrado": conteo.get(h, {}).get("cobrado") or 0,
        }
        for h in range(24)
    ]


def demanda_por_dia_semana(desde=None, hasta=None):
    """
    Cuantas ventas por dia de la semana. `ExtractIsoWeekDay` da 1=lunes,
    7=domingo, que es como se lee una semana aqui — el `ExtractWeekDay` de
    Django arranca en domingo y confundiria el grafico.
    """
    conteo = {
        f["dia"]: f
        for f in _cuentas(desde, hasta)
        .annotate(dia=ExtractIsoWeekDay("cerrada_en"))
        .values("dia")
        .annotate(ventas=Count("id"), cobrado=Sum("total_congelado"))
    }
    return [
        {
            "dia": DIAS_SEMANA[n - 1],
            "ventas": conteo.get(n, {}).get("ventas", 0),
            "cobrado": conteo.get(n, {}).get("cobrado") or 0,
        }
        for n in range(1, 8)
    ]


AGRUPACIONES = {
    "dia": TruncDate,
    "semana": TruncWeek,
    "mes": TruncMonth,
}

# Rellenar con ceros tiene sentido en rangos razonables; mas alla, la tabla
# se volveria un listado de ceros que nadie lee.
TOPE_PERIODOS = 400


def _inicio_de_periodo(dia, agrupar):
    if agrupar == "semana":
        return dia - timedelta(days=dia.weekday())
    if agrupar == "mes":
        return dia.replace(day=1)
    return dia


def _siguiente_periodo(inicio, agrupar):
    if agrupar == "semana":
        return inicio + timedelta(days=7)
    if agrupar == "mes":
        return (inicio.replace(day=28) + timedelta(days=4)).replace(day=1)
    return inicio + timedelta(days=1)


def ventas_de_producto(plato_id, desde=None, hasta=None, agrupar="dia"):
    """
    Cuanto se vendio de UN producto, plato o promocion, agrupado por dia,
    semana o mes (SPEC-023).

    Por `plato_id` y no por nombre, al reves que el ranking: aqui la pregunta
    es "como le va a esta promo", y una promo renombrada a mitad de mes sigue
    siendo la misma promo. Partirla en dos filas esconderia justo lo que se
    quiere ver.

    Un combo cuenta como UNA unidad: 20 combos son 20, no 20 hamburguesas.
    Las reglas de siempre: solo cuentas cerradas, sin pedidos anulados, por
    fecha de cobro, e ingresos sin propina ni impuesto.
    """
    agrupar = agrupar if agrupar in AGRUPACIONES else "dia"
    plato = Plato.objects.filter(pk=plato_id).first()
    if plato is None:
        return None

    renglones = _renglones(desde, hasta).filter(plato_id=plato.id)
    totales = renglones.aggregate(unidades=Sum("cantidad"), ingresos=Sum(_valor_renglon()))
    filas = {
        f["periodo"]: f
        for f in renglones
        .annotate(periodo=AGRUPACIONES[agrupar]("pedido__cuenta__cerrada_en"))
        .values("periodo")
        .annotate(unidades=Sum("cantidad"), ingresos=Sum(_valor_renglon()))
    }
    # TruncWeek y TruncMonth devuelven fecha con hora (ya en hora local);
    # TruncDate, solo fecha. Se normaliza para poder cruzar con el calendario.
    por_inicio = {
        (k.date() if isinstance(k, datetime) else k): v
        for k, v in filas.items() if k is not None
    }

    periodos = []
    if desde and hasta:
        inicio = _inicio_de_periodo(date.fromisoformat(str(desde)), agrupar)
        fin = date.fromisoformat(str(hasta))
        while inicio <= fin and len(periodos) < TOPE_PERIODOS:
            fila = por_inicio.get(inicio, {})
            periodos.append({
                "inicio": inicio.isoformat(),
                "unidades": fila.get("unidades") or 0,
                "ingresos": fila.get("ingresos") or 0,
            })
            inicio = _siguiente_periodo(inicio, agrupar)
    else:
        periodos = [
            {"inicio": k.isoformat(), "unidades": v["unidades"] or 0, "ingresos": v["ingresos"] or 0}
            for k, v in sorted(por_inicio.items())
        ]

    return {
        "plato": {"id": plato.id, "nombre": plato.nombre, "tipo": plato.tipo},
        "agrupar": agrupar,
        "unidades": totales["unidades"] or 0,
        "ingresos": totales["ingresos"] or 0,
        "periodos": periodos,
    }


def catalogo_productos():
    """
    Los productos que se pueden elegir en el filtro: todos, con su nombre de
    hoy. Tambien los que no se han vendido: ver un cero es una respuesta.
    Las promociones primero, que es lo que mas se consulta asi.
    """
    return [
        {"id": p["id"], "nombre": p["nombre"], "tipo": p["tipo"]}
        for p in Plato.objects.order_by("-tipo", "nombre").values("id", "nombre", "tipo")
    ]


def todos(desde=None, hasta=None, solo_promociones=False):
    """
    Los cuatro reportes de una sola vez.

    En una llamada porque son una sola pantalla con un solo rango: pedirlos
    por separado serian cuatro viajes para pintar lo mismo, y los graficos
    apareceran desordenados.
    """
    return {
        "resumen": resumen(desde, hasta),
        "productos": productos_mas_vendidos(desde, hasta, solo_promociones),
        "catalogo": catalogo_productos(),
        "meseros": ventas_por_mesero(desde, hasta),
        "por_dia": ticket_por_dia(desde, hasta),
        "por_hora": demanda_por_hora(desde, hasta),
        "por_dia_semana": demanda_por_dia_semana(desde, hasta),
    }
