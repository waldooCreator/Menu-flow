"""
Reconocer o crear un cliente a partir de un domicilio (SPEC-019).

Fuera de las vistas por la misma razón que `ventas/operaciones.py`: una
responsabilidad, testeable sin HTTP.
"""

from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Sum

from ventas.models import Cuenta

from .models import Cliente, DireccionCliente, normalizar_telefono


def reconocer_o_crear(telefono, nombre="", direccion=""):
    """
    Devuelve `(cliente, direccion_usada, es_nuevo)`.

    El teléfono manda: si ya existe, se reconoce y se actualiza el nombre con
    el más reciente. Si no, se crea.

    El nombre más reciente gana a propósito: si el cliente dijo "Angélica"
    esta vez, así se llama ahora. Es predecible, y se corrige en un toque
    desde su ficha.
    """
    numero = normalizar_telefono(telefono)
    if not numero:
        return None, None, False

    nombre = (nombre or "").strip()

    try:
        with transaction.atomic():
            cliente, es_nuevo = Cliente.objects.get_or_create(
                telefono=numero, defaults={"nombre": nombre or "Sin nombre"})
    except IntegrityError:
        # Dos domicilios del mismo teléfono confirmados en el mismo instante:
        # el `unique` de la base deja pasar a uno y el otro llega aquí. Se
        # relee en vez de fallar — mismo patrón de ADR-008.
        cliente, es_nuevo = Cliente.objects.get(telefono=numero), False

    if not es_nuevo and nombre and nombre != cliente.nombre:
        cliente.nombre = nombre
        cliente.save(update_fields=["nombre", "actualizado"])

    usada = _registrar_direccion(cliente, direccion) if direccion else None
    return cliente, usada, es_nuevo


def _registrar_direccion(cliente, texto):
    """
    Suma un uso a la dirección si ya la tenía; si no, la guarda como nueva.

    La comparación es exacta tras normalizar (mayúsculas, tildes, puntuación).
    Ante la duda se crea una nueva y que la persona decida: duplicar una
    dirección es un ruido menor, mandar la comida a otra casa no.
    """
    texto = (texto or "").strip()
    if not texto:
        return None

    existente = cliente.direccion_parecida(texto)
    if existente:
        existente.veces_usada += 1
        existente.save(update_fields=["veces_usada", "ultima_vez"])
        return existente

    return DireccionCliente.objects.create(cliente=cliente, direccion=texto)


def resumen_de(cliente):
    """
    Sus compras: cuántas, cuánto lleva gastado y cuándo fue la última.

    Solo cuentas CERRADAS: una venta anulada se devolvió, así que no cuenta
    como compra suya.
    """
    datos = Cuenta.objects.filter(
        cliente=cliente, estado=Cuenta.CERRADA,
    ).aggregate(
        compras=Count("id"),
        gastado=Sum("total_congelado"),
        ultima=Max("cerrada_en"),
    )
    return {
        "compras": datos["compras"] or 0,
        "gastado": datos["gastado"] or 0,
        "ultima_compra": datos["ultima"],
    }


def frecuentes(desde=None, hasta=None, tope=20):
    """
    Los clientes que más compran — el 5º reporte de SPEC-018.

    Ordenado por número de compras, no por monto: "frecuente" es quien vuelve,
    y quien vuelve mucho vale más que quien vino una vez y gastó mucho.
    """
    qs = Cuenta.objects.filter(estado=Cuenta.CERRADA, cliente__isnull=False)
    if desde:
        qs = qs.filter(cerrada_en__date__gte=desde)
    if hasta:
        qs = qs.filter(cerrada_en__date__lte=hasta)

    filas = (
        qs.values("cliente_id", "cliente__nombre", "cliente__telefono")
        .annotate(
            compras=Count("id"),
            gastado=Sum("total_congelado"),
            ultima=Max("cerrada_en"),
        )
        .order_by("-compras", "-gastado")[:tope]
    )
    return [
        {
            "id": f["cliente_id"],
            "nombre": f["cliente__nombre"],
            "telefono": f["cliente__telefono"],
            "compras": f["compras"],
            "gastado": f["gastado"] or 0,
            "ultima_compra": f["ultima"],
        }
        for f in filas
    ]
