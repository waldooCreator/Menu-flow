from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils.timezone import localtime
from rest_framework import serializers, viewsets
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from nucleo.permisos import EsMesero

from .models import Caja, CategoriaGasto, Cuenta, MovimientoCaja, Turno
from .operaciones import (
    OperacionInvalida,
    abrir_turno,
    ajustar_saldo,
    anular_cuenta,
    calcular_totales,
    cerrar_cuenta,
    cerrar_turno,
    cuadre_de,
    fijar_saldo_inicial,
    puede_cobrar,
    registrar_egreso,
    registrar_gasto,
    registrar_movimiento,
    trasladar,
    turno_abierto_de,
    turnos_abiertos,
    turnos_viejos_abiertos,
    usuarios_para_turno,
)
from .busqueda import (
    LIMITE_MOVIMIENTOS, LIMITE_TURNOS, FiltroInvalido, filtrar_movimientos, filtrar_turnos,
    personas_de_turnos, personas_del_libro, resumen_de_turnos, tanda,
)
from .reportes import todos as reportes_todos
from .reportes import ventas_de_producto
from .tiquetes import crear_xlsx, datos_tiquete, ventas_filtradas


class PuedeCobrar(BasePermission):
    """
    Permiso configurable: admin y cajero siempre; el mesero solo si el
    parámetro lo permite. Vive en el servidor, no en la interfaz.
    """

    def has_permission(self, request, view):
        return puede_cobrar(request.user)


class CajaSerializer(serializers.ModelSerializer):
    # Saldo derivado, nunca almacenado (SPEC-014).
    saldo = serializers.SerializerMethodField()
    # Explícito por lo mismo que en ObservacionRapida: un booleano ausente en
    # un formulario llega como False, y una caja nueva nacería desactivada.
    activo = serializers.BooleanField(default=True)

    class Meta:
        model = Caja
        fields = ["id", "nombre", "tipo", "prefijo", "activo", "orden", "saldo"]

    def get_saldo(self, caja):
        return caja.saldo()


class CategoriaGastoSerializer(serializers.ModelSerializer):
    activo = serializers.BooleanField(default=True)

    class Meta:
        model = CategoriaGasto
        fields = ["id", "nombre", "activo", "orden"]


class CategoriaGastoViewSet(viewsets.ModelViewSet):
    """
    En qué se va la plata (SPEC-020). La lee quien registra gastos; solo el
    administrador la modifica — es configuración, no operación del día.

    Una categoría con gastos registrados **no se borra**: el `PROTECT` del
    movimiento lo impide, y aquí se traduce a un mensaje claro en vez de un
    error 500. Se desactiva.
    """

    serializer_class = CategoriaGastoSerializer

    def get_queryset(self):
        qs = CategoriaGasto.objects.all()
        # Quien va a registrar un gasto solo debe ver las vigentes; el panel
        # de administración las necesita todas para poder reactivarlas.
        if not self.request.user.is_staff:
            qs = qs.filter(activo=True)
        return qs

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [PuedeCobrar()]
        return [IsAdminUser()]

    def destroy(self, request, *args, **kwargs):
        categoria = self.get_object()
        if categoria.movimientos.exists():
            return Response(
                {"detalle": f"«{categoria.nombre}» ya tiene gastos registrados. "
                            "Desactívala en vez de borrarla: si desapareciera, "
                            "esos movimientos quedarían sin explicación."},
                status=400)
        return super().destroy(request, *args, **kwargs)


class CajaViewSet(viewsets.ModelViewSet):
    """
    Lectura para quien cobra (necesita elegir medio de pago), CRUD para el
    administrador. Sin DELETE: una caja con movimientos la protege la base,
    y por uniformidad se desactiva en vez de borrarse.
    """

    queryset = Caja.objects.all()
    serializer_class = CajaSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        # Por defecto solo las activas: quien cobra no debe ver una caja
        # retirada. El panel pide `?todas=1` para poder reactivarla.
        qs = super().get_queryset()
        if not self.request.query_params.get("todas"):
            qs = qs.filter(activo=True)
        return qs

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [EsMesero()]
        return [IsAdminUser()]


def serializar_cuenta(cuenta, con_detalle=False):
    totales = calcular_totales(cuenta)
    datos = {
        "id": cuenta.id,
        "destino": cuenta.destino,
        "mesa_codigo": cuenta.mesa.codigo if cuenta.mesa else None,
        "es_domicilio": cuenta.es_domicilio,
        "estado": cuenta.estado,
        "abierta_en": cuenta.abierta_en,
        "aplica_propina": cuenta.aplica_propina,
        **totales,
        "recibido_efectivo": cuenta.recibido_efectivo,
        "vuelto_efectivo": cuenta.vuelto_efectivo,
        "cerrada_en": cuenta.cerrada_en,
        "cerrada_por": cuenta.cerrada_por.username if cuenta.cerrada_por else None,
        "medio_pago": cuenta.medio_pago.nombre if cuenta.medio_pago else None,
        "motivo_anulacion": cuenta.motivo_anulacion,
        "numero_tiquete": cuenta.numero_tiquete,
        "tiquete_numero": cuenta.tiquete_numero,
        "tiquete_anio": cuenta.tiquete_anio,
    }
    if con_detalle:
        datos["pedidos"] = [
            {
                "id": p.id,
                "estado": p.estado,
                "creado": p.creado,
                "detalles": [
                    {
                        "nombre": d.nombre_congelado,
                        "cantidad": d.cantidad,
                        "precio": d.precio_congelado,
                        "observacion": d.observacion,
                    }
                    for d in p.detalles.all()
                ],
            }
            for p in cuenta.pedidos.all().order_by("creado")
        ]
    return datos


class CuentasView(APIView):
    """
    GET /api/cuentas/ — por defecto solo las ABIERTAS: es la pantalla de
    "lo que se sirvió y no se ha cobrado". `?estado=` para ver otras.
    """

    permission_classes = [EsMesero]

    def get(self, request):
        estado = request.query_params.get("estado", Cuenta.ABIERTA)
        qs = Cuenta.objects.select_related("mesa", "medio_pago", "cerrada_por")
        if estado != "todas":
            qs = qs.filter(estado=estado)
        return Response([serializar_cuenta(c) for c in qs])


class VentasView(APIView):
    """
    GET /api/ventas/ — el historial de ventas (SPEC-015).

    Una venta ES una cuenta que se cobró. No hay entidad "factura" aparte, y
    nada de esto tiene que ver con la DIAN: es el historial interno.

    Se listan las cuentas que **en algún momento se cobraron** — o sea, las
    que tienen totales congelados. Una cuenta anulada estando ABIERTA nunca
    fue una venta (nadie pagó nada), así que no aparece aquí; eso es un
    pedido anulado y vive en la vista de pedidos.

    Filtros: `desde`, `hasta` (YYYY-MM-DD, inclusivos), `medio_pago`, `tipo`
    (mesa | domicilio), `mesa` (id), `cobrado_por` (id), `monto_min`,
    `monto_max`, `hora_desde`, `hora_hasta` (0-23), `orden`
    (fecha | monto | monto_asc), `anuladas` (1 para incluirlas en la lista).
    """

    permission_classes = [PuedeCobrar]

    ORDENES = {
        "fecha": "-cerrada_en",
        "fecha_asc": "cerrada_en",
        "monto": "-total_congelado",
        "monto_asc": "total_congelado",
    }

    def get(self, request):
        p = request.query_params
        qs = (
            Cuenta.objects
            .filter(total_congelado__isnull=False)
            .select_related("mesa", "medio_pago", "cerrada_por", "anulada_por")
        )

        # Por fecha de COBRO, no de apertura: una mesa que se sentó a las 11
        # de la noche y pagó a las 12 es venta del día en que pagó, que es
        # cuando el dinero entró a la caja.
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

        # Rango de monto: para encontrar la venta grande de la noche, o al
        # revés, ver cuántas fueron de menos de X.
        try:
            if p.get("monto_min"):
                qs = qs.filter(total_congelado__gte=int(p["monto_min"]))
            if p.get("monto_max"):
                qs = qs.filter(total_congelado__lte=int(p["monto_max"]))
        except ValueError:
            return Response({"detalle": "El monto debe ser un número."}, status=400)

        # Franja horaria. Django convierte a la zona local (America/Bogota)
        # al comparar la hora, así que "entre 7 y 9 de la noche" significa lo
        # que significa aquí, no en UTC.
        try:
            h_desde = int(p["hora_desde"]) if p.get("hora_desde") not in (None, "") else None
            h_hasta = int(p["hora_hasta"]) if p.get("hora_hasta") not in (None, "") else None
        except ValueError:
            return Response({"detalle": "La hora debe ser un número entre 0 y 23."}, status=400)

        if h_desde is not None and h_hasta is not None:
            if h_desde <= h_hasta:
                qs = qs.filter(cerrada_en__hour__gte=h_desde, cerrada_en__hour__lte=h_hasta)
            else:
                # La franja cruza la medianoche — el caso normal de un
                # restaurante que cierra a las 2 de la mañana. Sin esto,
                # "de 10pm a 2am" no devolvería nada.
                qs = qs.filter(
                    Q(cerrada_en__hour__gte=h_desde) | Q(cerrada_en__hour__lte=h_hasta))
        elif h_desde is not None:
            qs = qs.filter(cerrada_en__hour__gte=h_desde)
        elif h_hasta is not None:
            qs = qs.filter(cerrada_en__hour__lte=h_hasta)

        # Los totales salen SOLO de las cerradas: una venta anulada se
        # devolvió, así que sumarla diría que se vendió algo que no se vendió.
        # Se calculan sobre el rango completo, antes de cualquier tope de
        # filas — si dependieran de lo que cabe en pantalla no servirían para
        # cuadrar (misma regla que el libro de caja).
        cobradas = qs.filter(estado=Cuenta.CERRADA)
        sumas = cobradas.aggregate(
            vendido=Sum("subtotal_congelado"),
            impuestos=Sum("impuesto_congelado"),
            propinas=Sum("propina_congelada"),
            cobrado=Sum("total_congelado"),
        )
        anuladas = qs.filter(estado=Cuenta.ANULADA)

        # Lo que entró por cada medio: es la línea que se compara contra el
        # banco. Suma `cobrado` (con propina incluida) porque es la plata que
        # de verdad se movió a esa caja al cobrar.
        por_medio = [
            {
                "medio_pago": fila["medio_pago__nombre"] or "Sin medio",
                "cobrado": fila["cobrado"] or 0,
                "cantidad": fila["cantidad"],
            }
            for fila in cobradas.values("medio_pago__nombre")
            .annotate(cobrado=Sum("total_congelado"), cantidad=Count("id"))
            .order_by("-cobrado")
        ]

        if p.get("anuladas") not in ("1", "true", "si"):
            qs = cobradas

        return Response({
            "totales": {
                # `vendido` es la comida sola. La propina va aparte y NUNCA
                # sumada aquí (SPEC-015, regla 2): no es plata del
                # restaurante, es de los meseros, y mezclarlas le haría creer
                # al dueño que vendió más de lo que vendió.
                "vendido": sumas["vendido"] or 0,
                "impuestos": sumas["impuestos"] or 0,
                "propinas": sumas["propinas"] or 0,
                # Lo que efectivamente entró a caja: comida + impuesto + propina.
                "cobrado": sumas["cobrado"] or 0,
                "cantidad": cobradas.count(),
                "anuladas": anuladas.count(),
            },
            "por_medio_pago": por_medio,
            # Las opciones de los desplegables viajan aquí para no pedir tres
            # cosas aparte y pintar una sola pantalla. Solo las mesas y las
            # personas que DE VERDAD tienen ventas: ofrecer un filtro que no
            # devuelve nada es peor que no ofrecerlo.
            "opciones": {
                "mesas": [
                    {"id": m["mesa_id"], "nombre": m["mesa__nombre"]}
                    for m in Cuenta.objects.filter(
                        total_congelado__isnull=False, mesa__isnull=False)
                    .values("mesa_id", "mesa__nombre").distinct().order_by("mesa__nombre")
                ],
                "cobradores": [
                    {"id": u["cerrada_por_id"], "username": u["cerrada_por__username"]}
                    for u in Cuenta.objects.filter(
                        total_congelado__isnull=False, cerrada_por__isnull=False)
                    .values("cerrada_por_id", "cerrada_por__username")
                    .distinct().order_by("cerrada_por__username")
                ],
            },
            "ventas": [
                {
                    "id": c.id,
                    "destino": c.destino,
                    "es_domicilio": c.es_domicilio,
                    "estado": c.estado,
                    "cerrada_en": c.cerrada_en,
                    "cerrada_por": c.cerrada_por.username if c.cerrada_por else None,
                    "medio_pago": c.medio_pago.nombre if c.medio_pago else None,
                    "numero_tiquete": c.numero_tiquete,
                    "subtotal": c.subtotal_congelado or 0,
                    "propina": c.propina_congelada or 0,
                    "impuesto": c.impuesto_congelado or 0,
                    # Envío y vuelto (SPEC-013/025, 2026-09-16): faltaban aquí
                    # aunque ya estaban en `/cuentas/` y en el tiquete — el
                    # detalle de Ventas los tomaba de esta lista, no de ahí.
                    "envio": c.costo_envio,
                    "recibido_efectivo": c.recibido_efectivo,
                    "vuelto_efectivo": c.vuelto_efectivo,
                    "total": c.total_congelado or 0,
                    "motivo_anulacion": c.motivo_anulacion,
                    "anulada_por": c.anulada_por.username if c.anulada_por else None,
                }
                for c in qs.order_by(
                    self.ORDENES.get(p.get("orden"), "-cerrada_en"))[:300]
            ],
        })


class TiqueteVentaView(APIView):
    """GET /api/ventas/<id>/tiquete/ — datos de un comprobante (SPEC-016)."""

    permission_classes = [PuedeCobrar]

    def get(self, request, pk):
        cuenta = Cuenta.objects.filter(
            pk=pk, total_congelado__isnull=False,
        ).first()
        if cuenta is None:
            return Response({"detalle": "Ese tiquete no existe."}, status=404)
        return Response(datos_tiquete(cuenta, request))


class TiquetesSeleccionadosView(APIView):
    """POST /api/ventas/tiquetes/ — devuelve varios tiquetes seleccionados."""

    permission_classes = [PuedeCobrar]

    def post(self, request):
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"detalle": "Selecciona al menos una venta."}, status=400)
        cuentas = Cuenta.objects.filter(
            id__in=ids, total_congelado__isnull=False,
        ).order_by("cerrada_en")
        if cuentas.count() != len(set(ids)):
            return Response({"detalle": "Una de las ventas seleccionadas no existe."}, status=400)
        return Response({
            "tiquetes": [datos_tiquete(cuenta, request) for cuenta in cuentas],
        })


class ConsolidadoVentasView(APIView):
    """GET /api/ventas/consolidado/ — resumen por día y segundo nivel."""

    permission_classes = [PuedeCobrar]

    def get(self, request):
        try:
            qs = ventas_filtradas(request.query_params, incluir_anuladas=False)
        except ValueError as error:
            return Response({"detalle": str(error)}, status=400)
        agrupacion = request.query_params.get("agrupar", "medio_pago")
        if agrupacion not in {"mesa", "medio_pago", "cobrador"}:
            return Response({"detalle": "La agrupación no es válida."}, status=400)

        dias = {}
        for cuenta in qs.filter(estado=Cuenta.CERRADA).order_by("cerrada_en"):
            dia = localtime(cuenta.cerrada_en).date().isoformat()
            if agrupacion == "mesa":
                grupo = cuenta.destino
            elif agrupacion == "cobrador":
                grupo = cuenta.cerrada_por.username if cuenta.cerrada_por else "Sin responsable"
            else:
                grupo = cuenta.medio_pago.nombre if cuenta.medio_pago else "Sin medio"
            dias.setdefault(dia, {}).setdefault(grupo, {
                "grupo": grupo, "cantidad": 0, "subtotal": 0,
                "impuestos": 0, "propinas": 0, "total": 0,
            })
            fila = dias[dia][grupo]
            fila["cantidad"] += 1
            fila["subtotal"] += cuenta.subtotal_congelado or 0
            fila["impuestos"] += cuenta.impuesto_congelado or 0
            fila["propinas"] += cuenta.propina_congelada or 0
            fila["total"] += cuenta.total_congelado or 0

        dias_respuesta = []
        total = {"cantidad": 0, "subtotal": 0, "impuestos": 0, "propinas": 0, "total": 0}
        for dia, grupos in sorted(dias.items()):
            filas = list(grupos.values())
            subtotal_dia = {clave: sum(fila[clave] for fila in filas) for clave in total}
            for clave in total:
                total[clave] += subtotal_dia[clave]
            dias_respuesta.append({"dia": dia, "grupos": filas, "total": subtotal_dia})
        return Response({"agrupar": agrupacion, "dias": dias_respuesta, "total": total})


class ExportarVentasView(APIView):
    """GET /api/ventas/exportar/ — Excel de las ventas filtradas."""

    permission_classes = [PuedeCobrar]

    def get(self, request):
        try:
            incluir_anuladas = request.query_params.get("anuladas") in ("1", "true", "si")
            cuentas = ventas_filtradas(request.query_params, incluir_anuladas=incluir_anuladas)
        except ValueError as error:
            return Response({"detalle": str(error)}, status=400)
        archivo = crear_xlsx(cuentas.order_by("cerrada_en"))
        respuesta = HttpResponse(
            archivo.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        respuesta["Content-Disposition"] = 'attachment; filename="ventas-filtradas.xlsx"'
        return respuesta


class ReportesView(APIView):
    """
    GET /api/reportes/?desde=&hasta= — los cuatro reportes de venta (SPEC-018)
    en una sola llamada, porque son una sola pantalla con un solo rango.
    """

    permission_classes = [PuedeCobrar]

    def get(self, request):
        p = request.query_params
        return Response(reportes_todos(
            p.get("desde") or None, p.get("hasta") or None,
            solo_promociones=p.get("solo_promociones") in ("1", "true", "si"),
        ))


class ReporteProductoView(APIView):
    """
    GET /api/reportes/producto/?plato=&desde=&hasta=&agrupar=dia|semana|mes

    Cuanto se vendio de un plato o una promocion, por periodo (SPEC-023).
    Aparte de los demas reportes porque cambia cada vez que se elige otro
    producto, y rehacer los cinco graficos por eso seria trabajo perdido.
    """

    permission_classes = [PuedeCobrar]

    def get(self, request):
        p = request.query_params
        try:
            plato_id = int(p.get("plato", ""))
        except ValueError:
            return Response({"detalle": "Elige un producto."}, status=400)
        datos = ventas_de_producto(
            plato_id, p.get("desde") or None, p.get("hasta") or None, p.get("agrupar") or "dia")
        if datos is None:
            return Response({"detalle": "Ese producto no existe."}, status=404)
        return Response(datos)


class _AccionCuenta(APIView):
    permission_classes = [EsMesero]

    def ejecutar(self, cuenta, request):
        raise NotImplementedError

    def post(self, request, pk):
        cuenta = Cuenta.objects.filter(pk=pk).first()
        if cuenta is None:
            return Response({"detalle": "Esa cuenta no existe."}, status=404)
        try:
            self.ejecutar(cuenta, request)
        except OperacionInvalida as e:
            return Response({"detalle": str(e)}, status=400)
        cuenta.refresh_from_db()
        return Response(serializar_cuenta(cuenta, con_detalle=True))


class DetalleCuentaView(APIView):
    permission_classes = [EsMesero]

    def get(self, request, pk):
        cuenta = Cuenta.objects.filter(pk=pk).first()
        if cuenta is None:
            return Response({"detalle": "Esa cuenta no existe."}, status=404)
        return Response(serializar_cuenta(cuenta, con_detalle=True))


class CerrarCuentaView(_AccionCuenta):
    """POST /api/cuentas/<id>/cerrar/ — cobrar. Exige el permiso configurable."""

    permission_classes = [PuedeCobrar]

    def ejecutar(self, cuenta, request):
        cerrar_cuenta(
            cuenta, request.user,
            medio_pago_id=request.data.get("medio_pago"),
            aplica_propina=request.data.get("aplica_propina"),
            liberar_mesa=bool(request.data.get("liberar_mesa")),
            recibido_efectivo=self._recibido(request),
        )

    @staticmethod
    def _recibido(request):
        valor = request.data.get("recibido_efectivo")
        if valor in (None, ""):
            return None
        try:
            return int(valor)
        except (TypeError, ValueError):
            raise OperacionInvalida("El monto recibido no es un número válido.")


class AnularCuentaView(_AccionCuenta):
    """POST /api/cuentas/<id>/anular/ — con motivo obligatorio."""

    def ejecutar(self, cuenta, request):
        anular_cuenta(cuenta, request.user, motivo=request.data.get("motivo", ""))


# ==========================================================================
# Turno, movimientos y cuadre (SPEC-014)
# ==========================================================================

def serializar_turno(turno, con_cuadre=False):
    datos = {
        "id": turno.id,
        "responsable": turno.responsable.username,
        "estado": turno.estado,
        "abierto_en": turno.abierto_en,
        "cerrado_en": turno.cerrado_en,
        "observacion_apertura": turno.observacion_apertura,
        "observacion_cierre": turno.observacion_cierre,
        "efectivo_contado": turno.efectivo_contado,
        # Se muestra solo cuando NO es el propio responsable: verlo repetido en
        # cada turno normal seria ruido; verlo cuando difiere es justo el dato.
        "cerrado_por": (
            turno.cerrado_por.username
            if turno.cerrado_por_id and turno.cerrado_por_id != turno.responsable_id
            else None
        ),
    }
    if con_cuadre:
        datos["cuadre"] = cuadre_de(turno)
    return datos


class TurnoActualView(APIView):
    """
    GET /api/turnos/actual/ — el estado completo de la pantalla de Caja:
    mi turno (si tengo uno), los turnos abiertos de los demás, a quiénes se
    les puede abrir uno, las cajas para el formulario de apertura, y el aviso
    de turnos viejos. Todo en una llamada porque es una sola pantalla.

    SPEC-014, revisado 2026-09-03: el turno se abre A NOMBRE de un mesero
    elegido, no automáticamente de quien tiene la sesión — "caja" es donde se
    abren y ven los turnos de los meseros, no solo el propio.
    """

    permission_classes = [PuedeCobrar]

    def get(self, request):
        turno = turno_abierto_de(request.user)

        cajas = [
            {"id": c.id, "nombre": c.nombre, "saldo": c.saldo()}
            for c in Caja.objects.filter(activo=True)
        ]
        usuarios = [
            {"id": u.id, "username": u.username} for u in usuarios_para_turno()
        ]
        # Avisa de turnos que quedaron abiertos de dias anteriores. Avisa, no
        # bloquea (SPEC-012, regla de oro).
        viejos = [
            {"id": t.id, "responsable": t.responsable.username, "abierto_en": t.abierto_en}
            for t in turnos_viejos_abiertos()
        ]
        # Los de los demás, con su cuadre: es la lista que reemplaza "mi
        # turno" como concepto único — caja ve y cierra el de cualquiera.
        otros = [
            serializar_turno(t, con_cuadre=True)
            for t in turnos_abiertos() if t.id != (turno.id if turno else None)
        ]

        return Response({
            "abierto": turno is not None,
            "turno": serializar_turno(turno, con_cuadre=True) if turno else None,
            "otros_turnos_abiertos": otros,
            "cajas": cajas,
            "usuarios": usuarios,
            "turnos_viejos": viejos,
        })


class AbrirTurnoView(APIView):
    """
    POST /api/turnos/abrir/ — exige `usuario_id`: el turno se abre A NOMBRE
    de un mesero o cajero elegido de la lista (SPEC-014, 2026-09-03), no
    automáticamente de quien tiene la sesión. Caja abre los turnos de los
    meseros, no solo el propio.
    """

    permission_classes = [PuedeCobrar]

    def post(self, request):
        usuario_id = request.data.get("usuario_id")
        if not usuario_id:
            return Response(
                {"detalle": "Indica a qué usuario se le abre el turno."}, status=400)
        # Restringido a la lista de candidatos, no a User.objects.all(): sin
        # esto, cualquiera con el id correcto podría abrirle un turno a
        # cocina o a un usuario desactivado.
        responsable = usuarios_para_turno().filter(id=usuario_id).first()
        if responsable is None:
            return Response(
                {"detalle": "Ese usuario no existe o no puede tener turno."}, status=400)

        try:
            turno = abrir_turno(
                responsable,
                # {caja_id: monto} — un fondo por caja (SPEC-014).
                fondos=request.data.get("fondos") or {},
                observacion=request.data.get("observacion", ""),
            )
        except (OperacionInvalida, ValueError) as e:
            return Response({"detalle": str(e)}, status=400)
        return Response(serializar_turno(turno, con_cuadre=True), status=201)


class CerrarTurnoView(APIView):
    permission_classes = [PuedeCobrar]

    def post(self, request, pk):
        turno = Turno.objects.filter(pk=pk).first()
        if turno is None:
            return Response({"detalle": "Ese turno no existe."}, status=404)
        try:
            cerrar_turno(
                turno,
                efectivo_contado=request.data.get("efectivo_contado"),
                observacion=request.data.get("observacion", ""),
                # Quien cierra. Sin esto, cualquiera que pudiera cobrar cerraba
                # el turno de otro con solo saber el id.
                autor=request.user,
                # SPEC-020: si viene base, además se cierra el cajón. Si no
                # viene, el turno se cierra y el efectivo se queda — el caso de
                # "todavía quedan compañeros vendiendo".
                base_dejada=request.data.get("base_dejada"),
                destino_efectivo=request.data.get("destino_efectivo"),
                motivo_diferencia=request.data.get("motivo_diferencia", ""),
            )
        except (OperacionInvalida, ValueError, TypeError) as e:
            return Response({"detalle": str(e)}, status=400)
        turno.refresh_from_db()
        return Response(serializar_turno(turno, con_cuadre=True))


class TurnosView(APIView):
    """
    GET /api/turnos/ — historial. Solo administrador, como en el otro sistema.

    Filtros (SPEC-024): `desde`, `hasta` (fecha de apertura), `responsable`,
    `cerrado_por`, `estado`, `cuadre` (cuadro | falto | sobro | sin_contar),
    `diferencia_min`, `orden` (recientes | faltante | sobrante), y la tanda con
    `desde_fila` y `limite`. Antes traía los últimos 100 sin filtros: el
    turno 101 no se podía ver nunca.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        p = request.query_params
        try:
            turnos = filtrar_turnos(p)
            inicio, limite = tanda(p, LIMITE_TURNOS)
        except FiltroInvalido as e:
            return Response({"detalle": str(e)}, status=400)

        resumen = resumen_de_turnos(turnos)
        pagina = list(turnos[inicio:inicio + limite])
        return Response({
            "resumen": resumen,
            "turnos": [serializar_turno(t, con_cuadre=True) for t in pagina],
            "hay_mas": inicio + len(pagina) < resumen["total"],
            "personas": personas_de_turnos(),
        })


class MovimientosView(APIView):
    """
    GET  /api/movimientos/ — el libro.
    POST /api/movimientos/ — registrar un ingreso o un gasto de caja.

    No hay PUT ni DELETE a propósito (SPEC-014, regla 3): un error se
    corrige con el movimiento contrario, nunca editando el original.
    """

    permission_classes = [PuedeCobrar]

    def get(self, request):
        """
        Filtros: `desde` y `hasta` (YYYY-MM-DD, inclusivos), `caja`, `tipo`,
        `concepto`, `categoria`, y desde SPEC-024 `monto`, `monto_min`,
        `monto_max`, `q` (texto o número de tiquete) y `autor`. La tanda se pide
        con `desde_fila` y `limite`. Sin filtros trae lo último — el caso de
        "qué pasó hoy".

        Devuelve además los totales del filtro completo: sin eso, conciliar
        contra el banco obligaría a sumar la lista a mano, que es justo lo que
        este libro existe para evitar.
        """
        p = request.query_params
        try:
            movs = filtrar_movimientos(p)
            inicio, limite = tanda(p, LIMITE_MOVIMIENTOS)
        except FiltroInvalido as e:
            return Response({"detalle": str(e)}, status=400)

        def suma(tipo):
            return movs.filter(tipo=tipo).aggregate(t=Sum("monto"))["t"] or 0

        ingresos, egresos = suma(MovimientoCaja.INGRESO), suma(MovimientoCaja.EGRESO)
        cantidad = movs.count()
        pagina = list(movs[inicio:inicio + limite])

        return Response({
            "totales": {
                "ingresos": ingresos,
                "egresos": egresos,
                "neto": ingresos - egresos,
                "cantidad": cantidad,
            },
            "hay_mas": inicio + len(pagina) < cantidad,
            "personas": personas_del_libro(),
            "movimientos": [
                {
                    "id": m.id,
                    "caja": m.caja.nombre,
                    "caja_id": m.caja_id,
                    "tipo": m.tipo,
                    "concepto": m.concepto,
                    "concepto_texto": m.get_concepto_display(),
                    # De que tipo es el gasto (SPEC-020). Sin esto la
                    # categoria solo existiria al registrarla, y el libro
                    # —que es donde se revisa— no la mostraria.
                    "categoria": m.categoria.nombre if m.categoria else None,
                    "monto": m.monto,
                    "descripcion": m.descripcion,
                    # El tiquete de la venta (SPEC-024): es lo que se busca
                    # cuando un cliente reclama una factura.
                    "tiquete": m.cuenta.numero_tiquete if m.cuenta_id else None,
                    "turno": m.turno_id,
                    "fuera_de_turno": m.turno_id is None,
                    "autor": m.autor.username,
                    "creado": m.creado,
                }
                # La tanda va DESPUES de filtrar y de sumar: los totales son
                # del filtro completo, no solo de lo que cabe en pantalla.
                for m in pagina
            ],
        })

    def post(self, request):
        caja = Caja.objects.filter(id=request.data.get("caja"), activo=True).first()
        if caja is None:
            return Response({"detalle": "Elige una caja válida."}, status=400)
        tipo = request.data.get("tipo")
        if tipo not in (MovimientoCaja.INGRESO, MovimientoCaja.EGRESO):
            return Response({"detalle": "El tipo debe ser ingreso o egreso."}, status=400)

        # Un gasto va por su propia operación porque exige categoría
        # (SPEC-020). Un ingreso suelto sigue por el camino de siempre.
        es_gasto = request.data.get("concepto") == MovimientoCaja.GASTO
        try:
            monto = int(request.data.get("monto") or 0)
            if es_gasto:
                categoria = CategoriaGasto.objects.filter(
                    id=request.data.get("categoria"), activo=True).first()
                mov = registrar_gasto(
                    caja, monto, categoria, request.user,
                    descripcion=request.data.get("descripcion", ""))
            elif tipo == MovimientoCaja.EGRESO:
                # Por `registrar_egreso` y no por `registrar_movimiento`: de
                # una caja no puede salir mas de lo que tiene (SPEC-020).
                mov = registrar_egreso(
                    caja, monto, request.user,
                    descripcion=request.data.get("descripcion", ""))
            else:
                mov = registrar_movimiento(
                    caja, tipo, monto, request.user,
                    descripcion=request.data.get("descripcion", ""))
        except (OperacionInvalida, ValueError) as e:
            return Response({"detalle": str(e)}, status=400)
        return Response({"id": mov.id, "caja": caja.nombre, "monto": mov.monto}, status=201)


class ActivosView(APIView):
    """
    GET /api/activos/ — cuánta plata hay ahora mismo y dónde (SPEC-020).

    El saldo de cada caja ya se sabía calcular; lo que no existía era una
    pantalla que los mostrara juntos y sumados. Sin eso, para saber cuánto
    tiene el negocio había que abrir el Libro caja por caja.

    El desglose entre efectivo y banco no es cosmético: son dos formas
    distintas de cuadrar. El efectivo se cuenta con la mano al cerrar; una
    cuenta de banco se concilia contra el extracto.
    """

    permission_classes = [PuedeCobrar]

    def get(self, request):
        cajas = []
        for caja in Caja.objects.filter(activo=True):
            ultimo = caja.movimientos.order_by("-creado").first()
            cajas.append({
                "id": caja.id,
                "nombre": caja.nombre,
                "tipo": caja.tipo,
                "saldo": caja.saldo(),
                # Si esta vacia se puede declarar con cuanto arranco; si ya
                # tiene historia, declararlo se sumaria a lo que hay y la
                # herramienta correcta pasa a ser el ajuste.
                "puede_declarar_arranque": not caja.movimientos.exists(),
                "ultimo_movimiento": ultimo.creado if ultimo else None,
            })

        def total(tipo=None):
            return sum(c["saldo"] for c in cajas if tipo is None or c["tipo"] == tipo)

        return Response({
            "cajas": cajas,
            "total": total(),
            "total_efectivo": total(Caja.EFECTIVO),
            "total_banco": total(Caja.BANCO),
        })


class SaldoInicialView(APIView):
    """
    POST /api/cajas/<id>/saldo-inicial/ — con cuánto arrancaba esta caja.

    Solo el administrador: declarar que una caja tenía cinco millones no es
    una operación del día a día, es la foto de partida del negocio.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        caja = Caja.objects.filter(pk=pk, activo=True).first()
        if caja is None:
            return Response({"detalle": "Esa caja no existe."}, status=404)
        try:
            fijar_saldo_inicial(caja, int(request.data.get("monto") or 0), request.user)
        except (OperacionInvalida, ValueError) as e:
            return Response({"detalle": str(e)}, status=400)
        return Response({"caja": caja.nombre, "saldo": caja.saldo()}, status=201)


class AjustarSaldoView(APIView):
    """
    POST /api/cajas/<id>/ajustar/ — cuadrar la caja contra la realidad.

    Solo el administrador, y siempre con motivo: no reescribe nada, registra
    la diferencia como su propio movimiento firmado.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        caja = Caja.objects.filter(pk=pk, activo=True).first()
        if caja is None:
            return Response({"detalle": "Esa caja no existe."}, status=404)
        try:
            mov = ajustar_saldo(
                caja, int(request.data.get("saldo_real") or 0),
                request.user, request.data.get("motivo", ""))
        except (OperacionInvalida, ValueError) as e:
            return Response({"detalle": str(e)}, status=400)
        return Response({
            "caja": caja.nombre,
            "saldo": caja.saldo(),
            "ajuste": mov.monto if mov else 0,
            "sin_cambios": mov is None,
        })


class TrasladarView(APIView):
    """
    POST /api/cajas/trasladar/ — consignar el efectivo en el banco, p.ej.

    Lo hace quien puede cobrar, no solo el administrador: consignar es una
    tarea de caja del día a día, y exigir un administrador para registrarla
    llevaría a que se haga sin registrar, que es peor. Deja dos movimientos
    con autor, así que quién lo hizo siempre se sabe.
    """

    permission_classes = [PuedeCobrar]

    def post(self, request):
        origen = Caja.objects.filter(id=request.data.get("origen"), activo=True).first()
        destino = Caja.objects.filter(id=request.data.get("destino"), activo=True).first()
        if origen is None or destino is None:
            return Response({"detalle": "Elige la caja de origen y la de destino."}, status=400)
        try:
            trasladar(origen, destino, int(request.data.get("monto") or 0), request.user,
                      descripcion=request.data.get("descripcion", ""))
        except (OperacionInvalida, ValueError) as e:
            return Response({"detalle": str(e)}, status=400)
        return Response({
            "origen": {"caja": origen.nombre, "saldo": origen.saldo()},
            "destino": {"caja": destino.nombre, "saldo": destino.saldo()},
        })
