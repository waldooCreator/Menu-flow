"""
Firma y verificación del QR de pedido (SPEC-002 / ADR-001).

Usa `django.core.signing` en vez de HMAC manual: ya trae firma con
`SECRET_KEY` (que vive solo en el servidor), expiración (`max_age`) y
compresión — las mismas garantías que se probaron en `pruebas/prueba-qr`,
con menos código propio que mantener.

El `salt` namesface la firma: aunque alguien reusara `SECRET_KEY` para
firmar otra cosa en este proyecto, esos tokens no serían intercambiables.
"""

import hashlib

from django.core import signing

from configuracion.helpers import config
from menu.models import Plato

SALT = "pedidos.qr"
VIGENCIA_SEGUNDOS = 6 * 3600  # SPEC-002: por defecto 6 horas


def vigencia_qr_segundos():
    """Lee la vigencia del restaurante sin dejar que un valor inválido rompa QR."""
    try:
        horas = float(config("qr-vigencia-horas", "6"))
        return max(1, int(horas * 3600))
    except (TypeError, ValueError):
        return VIGENCIA_SEGUNDOS


class QRInvalido(Exception):
    """El QR está vencido, alterado, o referencia un plato que ya no existe."""


def firmar_pedido(mesa_codigo, nombre_cliente, items, es_domicilio=False,
                 telefono="", direccion=""):
    """
    items: [{"plato_id": int, "cantidad": int, "observacion": str}]

    Solo IDs y cantidades de los PLATOS viajan — nunca nombres ni precios
    (SPEC-002): el menú en base de datos es la única fuente de verdad.

    `es_domicilio` viaja como la clave "d" y solo se incluye cuando es
    verdadera: así un QR de mesa no paga ni un byte por una marca que no
    usa, y los QR viejos (sin "d") se siguen leyendo igual.

    **Teléfono y dirección SÍ viajan, desde SPEC-019 (2026-09-07).** Antes no:
    la dirección iba solo en el mensaje de WhatsApp. Se cambió de criterio
    para que el mesero no tenga que teclear nada al confirmar — el cliente los
    escribe UNA vez, su navegador los recuerda, y el QR los lleva firmados.

    Solo se incluyen en domicilios, y solo si existen: un QR de mesa sigue
    pesando exactamente lo mismo que antes.
    """
    payload = {
        "v": 1,
        "m": mesa_codigo,
        "c": nombre_cliente or None,
        "i": [[it["plato_id"], it["cantidad"], it.get("observacion", "")] for it in items],
    }
    if es_domicilio:
        payload["d"] = 1
        if telefono:
            payload["t"] = telefono
        if direccion:
            payload["a"] = direccion
    return signing.dumps(payload, salt=SALT, compress=True)


def codigo_anti_duplicado(texto_firmado):
    """Deriva un código corto y estable del texto — mismo QR, mismo código."""
    return hashlib.sha256(texto_firmado.encode("utf-8")).hexdigest()[:16]


def verificar_pedido(texto_firmado):
    """Verifica firma y vigencia, y resuelve los platos contra el menú actual."""
    try:
        payload = signing.loads(texto_firmado, salt=SALT, max_age=vigencia_qr_segundos())
    except signing.SignatureExpired:
        raise QRInvalido("Este código venció. Pídele al cliente que genere uno nuevo.")
    except signing.BadSignature:
        raise QRInvalido("Código inválido o alterado.")

    ids = [item[0] for item in payload["i"]]
    platos = {p.id: p for p in Plato.objects.filter(id__in=ids)}

    items_resueltos = []
    for plato_id, cantidad, observacion in payload["i"]:
        plato = platos.get(plato_id)
        if plato is None:
            raise QRInvalido(f"Un plato del pedido ya no existe en el menú (id {plato_id}).")
        items_resueltos.append({
            "plato": plato,
            "cantidad": cantidad,
            "observacion": observacion,
        })

    return {
        "mesa_codigo": payload["m"],
        "nombre_cliente": payload.get("c") or "",
        # `.get` con defecto: los QR emitidos antes del 2026-08-26 no traen
        # la clave y deben seguir siendo válidos hasta que venzan.
        "es_domicilio": bool(payload.get("d")),
        # Mismo criterio de compatibilidad: un QR emitido antes de SPEC-019 no
        # trae telefono ni direccion, y debe seguir siendo valido. En ese caso
        # se piden en pantalla como excepcion, no como norma.
        "telefono": payload.get("t") or "",
        "direccion": payload.get("a") or "",
        "items": items_resueltos,
    }
