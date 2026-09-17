"""Datos y exportaciones de los tiquetes internos (SPEC-016)."""

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from django.conf import settings
from django.db.models import Q

from configuracion.helpers import obtener_configuracion

from .models import Cuenta


def ventas_filtradas(parametros, incluir_anuladas=True):
    """Aplica los filtros del historial a cuentas que ya fueron cobradas."""
    qs = Cuenta.objects.filter(total_congelado__isnull=False).select_related(
        "mesa", "medio_pago", "cerrada_por", "anulada_por",
    )
    p = parametros
    if p.get("desde"):
        qs = qs.filter(cerrada_en__date__gte=p["desde"])
    if p.get("hasta"):
        qs = qs.filter(cerrada_en__date__lte=p["hasta"])
    if p.get("medio_pago"):
        qs = qs.filter(medio_pago_id=p["medio_pago"])
    if p.get("tipo") == "domicilio":
        qs = qs.filter(es_domicilio=True)
    elif p.get("tipo") == "mesa":
        qs = qs.filter(es_domicilio=False)
    if p.get("mesa"):
        qs = qs.filter(mesa_id=p["mesa"])
    if p.get("cobrado_por"):
        qs = qs.filter(cerrada_por_id=p["cobrado_por"])
    try:
        if p.get("monto_min"):
            qs = qs.filter(total_congelado__gte=int(p["monto_min"]))
        if p.get("monto_max"):
            qs = qs.filter(total_congelado__lte=int(p["monto_max"]))
        h_desde = int(p["hora_desde"]) if p.get("hora_desde") not in (None, "") else None
        h_hasta = int(p["hora_hasta"]) if p.get("hora_hasta") not in (None, "") else None
    except (TypeError, ValueError):
        raise ValueError("Los montos y horas deben ser números válidos.")

    if h_desde is not None and h_hasta is not None:
        if h_desde <= h_hasta:
            qs = qs.filter(cerrada_en__hour__gte=h_desde, cerrada_en__hour__lte=h_hasta)
        else:
            qs = qs.filter(
                Q(cerrada_en__hour__gte=h_desde) | Q(cerrada_en__hour__lte=h_hasta)
            )
    elif h_desde is not None:
        qs = qs.filter(cerrada_en__hour__gte=h_desde)
    elif h_hasta is not None:
        qs = qs.filter(cerrada_en__hour__lte=h_hasta)

    if not incluir_anuladas and p.get("anuladas") not in ("1", "true", "si"):
        qs = qs.filter(estado=Cuenta.CERRADA)
    return qs


def configuracion_tiquete(request):
    cfg = obtener_configuracion()
    logo = cfg.get("logo-tiquete", "")
    if logo.startswith(settings.MEDIA_URL):
        logo = request.build_absolute_uri(logo)
    return {
        "nombre": cfg.get("nombre-restaurante", ""),
        "nit": cfg.get("nit", ""),
        "direccion": " ".join(filter(None, [
            cfg.get("direccion-linea1", ""), cfg.get("direccion-linea2", ""),
        ])),
        "telefono": cfg.get("telefono", ""),
        "logo": logo,
        "formato": cfg.get("formato-tiquete", "rollo") or "rollo",
        "mensaje": cfg.get("mensaje-pie-tiquete", ""),
    }


def datos_tiquete(cuenta, request):
    cuenta = Cuenta.objects.select_related(
        "mesa", "medio_pago", "cerrada_por", "anulada_por",
    ).prefetch_related("pedidos__detalles").get(pk=cuenta.pk)
    return {
        "numero": cuenta.numero_tiquete,
        "fecha": cuenta.cerrada_en,
        "destino": cuenta.destino,
        "mesa": cuenta.mesa.nombre if cuenta.mesa else ("Domicilio" if cuenta.es_domicilio else ""),
        "cobrador": cuenta.cerrada_por.username if cuenta.cerrada_por else "",
        "medio_pago": cuenta.medio_pago.nombre if cuenta.medio_pago else "",
        "estado": cuenta.estado,
        "motivo_anulacion": cuenta.motivo_anulacion,
        "subtotal": cuenta.subtotal_congelado or 0,
        "impuesto": cuenta.impuesto_congelado or 0,
        "propina": cuenta.propina_congelada or 0,
        "envio": cuenta.costo_envio,
        "recibido_efectivo": cuenta.recibido_efectivo,
        "vuelto_efectivo": cuenta.vuelto_efectivo,
        "total": cuenta.total_congelado or 0,
        "items": [
            {
                "nombre": detalle.nombre_congelado,
                "cantidad": detalle.cantidad,
                "precio": detalle.precio_congelado,
                "observacion": detalle.observacion,
            }
            for pedido in cuenta.pedidos.all().order_by("creado")
            for detalle in pedido.detalles.all()
        ],
        "configuracion": configuracion_tiquete(request),
    }


def filas_exportacion(cuentas):
    return [
        [
            cuenta.numero_tiquete or "",
            cuenta.cerrada_en.strftime("%Y-%m-%d %H:%M") if cuenta.cerrada_en else "",
            cuenta.destino,
            cuenta.medio_pago.nombre if cuenta.medio_pago else "",
            cuenta.cerrada_por.username if cuenta.cerrada_por else "",
            cuenta.subtotal_congelado or 0,
            cuenta.impuesto_congelado or 0,
            cuenta.propina_congelada or 0,
            cuenta.costo_envio,
            cuenta.total_congelado or 0,
            "Anulada" if cuenta.estado == Cuenta.ANULADA else "Cobrada",
        ]
        for cuenta in cuentas
    ]


def crear_xlsx(cuentas):
    """Genera un XLSX mínimo sin dependencia externa."""
    encabezados = [
        "Tiquete", "Fecha", "Destino", "Medio de pago", "Quién cobró",
        "Subtotal", "Impuesto", "Propina", "Envío", "Total", "Estado",
    ]
    filas = [encabezados, *filas_exportacion(cuentas)]

    def celda(valor):
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            return f'<c><v>{valor}</v></c>'
        texto = escape(str(valor), {'"': "&quot;"})
        return f'<c t="inlineStr"><is><t>{texto}</t></is></c>'

    filas_xml = "".join(
        f'<row r="{indice}">' + "".join(celda(valor) for valor in fila) + "</row>"
        for indice, fila in enumerate(filas, 1)
    )
    hoja = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{filas_xml}</sheetData></worksheet>"
    )
    contenido = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Ventas" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'
        ),
        "xl/worksheets/sheet1.xml": hoja,
    }
    archivo = BytesIO()
    with ZipFile(archivo, "w", ZIP_DEFLATED) as libro:
        for nombre, xml in contenido.items():
            libro.writestr(nombre, xml)
    archivo.seek(0)
    return archivo
