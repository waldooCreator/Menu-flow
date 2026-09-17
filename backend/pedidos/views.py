from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from clientes.operaciones import reconocer_o_crear
from estaciones.ruteo import rutear_pedido
from ventas.operaciones import cuenta_para
from menu.models import Plato
from menu.promociones import desglose_para_congelar, motivo_no_disponible, se_puede_vender
from nucleo.permisos import EsMesero

from .firma import QRInvalido, codigo_anti_duplicado, firmar_pedido, verificar_pedido
from .models import DetallePedido, Mesa, Notificacion, Pedido
from .novedades import (
    NovedadInvalida,
    agregar_item,
    cambiar_cantidad,
    cambiar_destino,
    cambiar_observacion,
    quitar_item,
)


class ValidarMesaView(APIView):
    """
    GET /api/mesas/validar/<codigo>/ — público. Resuelve el código opaco del
    QR de mesa (SPEC-001) al nombre a mostrar. Si no existe, el cliente abre
    en modo sin mesa (regla de SPEC-001), no se le muestra un error crudo.
    """

    permission_classes = [AllowAny]

    def get(self, request, codigo):
        mesa = Mesa.objects.filter(codigo=codigo, activa=True).first()
        if mesa is None:
            return Response({"encontrada": False})
        return Response({"encontrada": True, "codigo": mesa.codigo, "nombre": mesa.nombre})


class ListarMesasView(APIView):
    """
    GET /api/mesas/ — mesas activas. La usa el mesero para elegir la mesa a
    mano cuando el QR del cliente no la trae (p.ej. el cliente entró por el
    enlace general y no escaneando el QR pegado en su mesa).
    """

    permission_classes = [EsMesero]

    def get(self, request):
        mesas = Mesa.objects.filter(activa=True)
        return Response([{"codigo": m.codigo, "nombre": m.nombre} for m in mesas])


class SalonView(APIView):
    """
    GET /api/mesas/salon/ — el tablero de mesas del mesero (SPEC-012).

    Solo mesas FÍSICAS activas. Un domicilio no tiene mesa, así que no puede
    aparecer aquí ni por accidente — el filtro no depende de recordar
    excluirlo, depende de que no exista la fila.
    """

    permission_classes = [EsMesero]

    def get(self, request):
        from ventas.models import Cuenta
        from ventas.operaciones import calcular_totales

        mesas = Mesa.objects.filter(activa=True)
        # La cuenta abierta de cada mesa, para mostrar cuánto va sin entrar
        # (SPEC-013). Una sola consulta, no una por mesa.
        abiertas = {
            c.mesa_id: c
            for c in Cuenta.objects.filter(
                estado=Cuenta.ABIERTA, mesa__isnull=False,
            ).select_related("mesa")
        }
        # Los domicilios NO ocupan mesa, así que van en su propia zona
        # (SPEC-012). Aparecen desde que se confirma el pedido y solo salen
        # al marcarse ENTREGADOS — cobrarlos no los retira, porque se puede
        # pagar por anticipado o al recibir, en cualquier orden.
        #
        # Sin tope de cuántos: es una lista, no una rejilla de puestos fijos
        # como la del sistema que se va a reemplazar.
        domicilios = (
            Pedido.objects.filter(es_domicilio=True)
            .exclude(estado__in=[Pedido.ENTREGADO, Pedido.ANULADO])
            .select_related("cuenta", "mesero")
            .order_by("creado")
        )

        return Response({
            "mesas": [
                {
                    "codigo": m.codigo,
                    "nombre": m.nombre,
                    "estado": m.estado,
                    "estado_desde": m.estado_desde,
                    "cuenta_id": abiertas[m.id].id if m.id in abiertas else None,
                    "cuenta_total": (
                        calcular_totales(abiertas[m.id])["total"] if m.id in abiertas else 0
                    ),
                }
                for m in mesas
            ],
            "domicilios": [
                {
                    "pedido_id": p.id,
                    "cliente": p.nombre_cliente,
                    "estado_pedido": p.estado,
                    "creado": p.creado,
                    "cuenta_id": p.cuenta_id,
                    # Las dos cosas a la vez: quien reparte necesita saber si
                    # este ya está pago o si cobra al llegar.
                    "cobrada": bool(p.cuenta and p.cuenta.estado == Cuenta.CERRADA),
                    "total": calcular_totales(p.cuenta)["total"] if p.cuenta else 0,
                }
                for p in domicilios
            ],
        })


class CambiarEstadoMesaView(APIView):
    """
    POST /api/mesas/<codigo>/estado/ — apartar, liberar o revertir.

    Acepta cualquier estado válido y NO valida transiciones, a propósito: la
    regla de oro de SPEC-012 es que el mesero manda. Eso también es lo que
    hace trivial el "Revertir" de 5 segundos — es esta misma llamada con el
    estado anterior.

    Liberar una mesa con un pedido en cocina está permitido y **no toca el
    pedido**: son dos cosas independientes. El caso que lo justifica es el
    cliente que empacó su comida y se fue.
    """

    permission_classes = [EsMesero]

    def post(self, request, codigo):
        mesa = Mesa.objects.filter(codigo=codigo, activa=True).first()
        if mesa is None:
            return Response({"detalle": "Esa mesa no existe."}, status=404)

        estado = request.data.get("estado")
        validos = [c for c, _ in Mesa.ESTADOS]
        if estado not in validos:
            return Response(
                {"detalle": f"Estado inválido. Debe ser uno de: {', '.join(validos)}."},
                status=400,
            )

        mesa.cambiar_estado(estado)

        # Se avisa, no se impide: el mesero decide igual.
        pedidos_en_curso = mesa.pedidos.exclude(
            estado__in=[Pedido.ENTREGADO, Pedido.ANULADO]
        ).count()

        return Response({
            "codigo": mesa.codigo,
            "nombre": mesa.nombre,
            "estado": mesa.estado,
            "estado_desde": mesa.estado_desde,
            "pedidos_en_curso": pedidos_en_curso,
        })


class FirmarPedidoView(APIView):
    """
    POST /api/pedidos/firmar/ — público (el cliente nunca se autentica,
    ADR-002). No escribe en base de datos (SPEC-002, paso 2): valida que los
    platos existan y estén disponibles, firma, y devuelve el texto. El QR se
    dibuja en el navegador del cliente, nunca en el servidor.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        items = request.data.get("items") or []
        if not items:
            return Response({"detalle": "El carrito está vacío."}, status=400)

        ids = [it["plato_id"] for it in items]
        platos = {p.id: p for p in Plato.objects.filter(id__in=ids)}
        for it in items:
            plato = platos.get(it["plato_id"])
            if plato is None:
                return Response({"detalle": "Un plato del carrito ya no existe."}, status=400)
            # Una promoción, además, tiene que estar vigente (SPEC-023).
            if not se_puede_vender(plato):
                return Response({"detalle": motivo_no_disponible(plato)}, status=400)

        # Un domicilio NO lleva mesa (SPEC-002): si viene marcado, se ignora
        # cualquier mesa que el cliente tuviera fijada de una visita anterior.
        es_domicilio = bool(request.data.get("es_domicilio"))
        mesa_codigo = "" if es_domicilio else (request.data.get("mesa") or "")
        if mesa_codigo and not Mesa.objects.filter(codigo=mesa_codigo, activa=True).exists():
            return Response({"detalle": "La mesa no es válida."}, status=400)

        texto = firmar_pedido(
            mesa_codigo, request.data.get("cliente", ""), items,
            es_domicilio=es_domicilio,
            telefono=request.data.get("telefono", "") if es_domicilio else "",
            direccion=request.data.get("direccion", "") if es_domicilio else "",
        )
        return Response({"texto": texto})


def _resolver(texto):
    """Verifica el QR y devuelve (resuelto, codigo_qr, error_http_o_None)."""
    if not texto:
        return None, None, Response({"detalle": "Falta el texto del QR."}, status=400)
    try:
        resuelto = verificar_pedido(texto)
    except QRInvalido as e:
        return None, None, Response({"detalle": str(e)}, status=400)
    return resuelto, codigo_anti_duplicado(texto), None


def _cliente_conocido(telefono):
    """
    Lo que se sabe de ese telefono, para mostrarlo antes de confirmar.
    `None` si es cliente nuevo — que tambien es informacion util.
    """
    from clientes.models import Cliente, normalizar_telefono
    from clientes.operaciones import resumen_de

    numero = normalizar_telefono(telefono)
    if not numero:
        return None
    cliente = Cliente.objects.filter(telefono=numero).first()
    if cliente is None:
        return None
    return {
        "id": cliente.id,
        "nombre": cliente.nombre,
        "observaciones": cliente.observaciones,
        "direcciones": [
            {"id": d.id, "direccion": d.direccion, "indicaciones": d.indicaciones}
            for d in cliente.direcciones.all()
        ],
        **resumen_de(cliente),
    }


class VerificarPedidoView(APIView):
    """
    POST /api/pedidos/verificar/ — el mesero escanea o sube el QR; esto
    resuelve el pedido para mostrarlo en pantalla ANTES de confirmar
    (SPEC-002, paso 4). Público a propósito: es una lectura, no crea nada;
    la confirmación (abajo) sí exige sesión.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        resuelto, codigo_qr, error = _resolver(request.data.get("texto", ""))
        if error:
            return error

        ya_usado = Pedido.objects.filter(codigo_qr=codigo_qr).exists()

        # El nombre legible, no el código opaco: el mesero necesita ver
        # "Mesa 12", no "x7f2q9".
        mesa = Mesa.objects.filter(codigo=resuelto["mesa_codigo"], activa=True).first()

        return Response({
            "mesa_codigo": resuelto["mesa_codigo"],
            "mesa_nombre": mesa.nombre if mesa else None,
            "es_domicilio": resuelto["es_domicilio"],
            "nombre_cliente": resuelto["nombre_cliente"],
            "telefono": resuelto.get("telefono", ""),
            "direccion": resuelto.get("direccion", ""),
            # Si ese telefono ya compro antes, la pantalla lo dice ANTES de
            # confirmar: es lo que convierte un digito mal escrito en un error
            # visible en vez de un cliente duplicado en silencio (SPEC-019).
            "cliente_conocido": _cliente_conocido(resuelto.get("telefono", "")),
            "ya_usado": ya_usado,
            "items": [
                {
                    "plato_id": it["plato"].id,
                    "nombre": it["plato"].nombre,
                    "precio": it["plato"].precio,
                    "foto": it["plato"].foto.url if it["plato"].foto else None,
                    # Para una promo, "disponible" ya incluye la vigencia: el
                    # mesero la ve marcada igual que un plato agotado.
                    "disponible": se_puede_vender(it["plato"]),
                    "es_promocion": it["plato"].es_promocion,
                    "cantidad": it["cantidad"],
                    "observacion": it["observacion"],
                }
                for it in resuelto["items"]
            ],
        })


class ConfirmarPedidoView(APIView):
    """
    POST /api/pedidos/confirmar/ — SOLO el mesero autenticado puede
    confirmar (ADR-002): es la salvaguarda contra el pedido fantasma y el
    "pedir e irse". Aquí, y solo aquí, se crea el Pedido en base de datos.
    """

    permission_classes = [EsMesero]

    def post(self, request):
        texto = request.data.get("texto", "")
        resuelto, codigo_qr, error = _resolver(texto)
        if error:
            return error

        # Un domicilio no tiene mesa y no debe pedirla (SPEC-002).
        es_domicilio = resuelto["es_domicilio"]
        mesa = None
        if not es_domicilio:
            # La mesa la trae el QR cuando el cliente entró escaneando el código
            # pegado en su mesa (SPEC-001). Si entró por el enlace general, el QR
            # viene sin mesa y el mesero la indica al confirmar — él está ahí y
            # sabe en qué mesa está sentado el cliente.
            codigo_mesa = resuelto["mesa_codigo"] or request.data.get("mesa", "")
            mesa = Mesa.objects.filter(codigo=codigo_mesa, activa=True).first()
            if mesa is None:
                return Response(
                    {"detalle": "Indica en qué mesa está el cliente para poder confirmar.",
                     "falta_mesa": True},
                    status=400,
                )

        # Costo de envío (SPEC-013/025): opcional, solo aplica a domicilios.
        # Se valida aquí, antes de escribir nada.
        costo_envio = request.data.get("costo_envio") if es_domicilio else None
        if costo_envio not in (None, ""):
            try:
                costo_envio = int(costo_envio)
            except (TypeError, ValueError):
                return Response({"detalle": "El costo de envío no es un número válido."}, status=400)
            if costo_envio < 0:
                return Response({"detalle": "El costo de envío no puede ser negativo."}, status=400)
        else:
            costo_envio = None

        try:
            with transaction.atomic():
                # Bloquea LA MESA antes de decidir nada. Sin esto, tres meseros
                # confirmando a la vez en la misma mesa leen todos "no hay
                # cuenta abierta", los tres intentan crearla, la restricción de
                # la base deja pasar a uno y los otros dos se caen con un 500:
                # sus pedidos se pierden. Medido — 10 simultáneos daban 1 pedido
                # y 9 caídos.
                #
                # El bloqueo es POR MESA: dos meseros en mesas distintas siguen
                # entrando en paralelo. Solo se serializa lo que de verdad
                # compite por el mismo recurso.
                if mesa is not None:
                    Mesa.objects.select_for_update().get(pk=mesa.pk)

                # Ojo: `select_for_update` sobre una consulta que NO encuentra
                # filas no bloquea nada — no hay qué bloquear todavía. Con la
                # mesa ya bloqueada arriba, el segundo en llegar sí ve el
                # pedido del primero y recibe este 409. Para los domicilios,
                # que no tienen mesa, el respaldo es el `unique` de codigo_qr
                # y el `except IntegrityError` de abajo.
                if Pedido.objects.filter(codigo_qr=codigo_qr).exists():
                    return Response(
                        {"detalle": "Este QR ya fue usado en otro pedido."}, status=409)

                # SPEC-017: la disponibilidad se comprueba otra vez contra la
                # base, dentro de la misma transacción y antes de crear cuenta,
                # pedido o comanda. Firmar el QR solo prueba que no fue alterado;
                # no prueba que el menú siga igual cinco minutos después.
                ids_platos = sorted({item["plato"].id for item in resuelto["items"]})
                platos_bloqueados = {
                    plato.id: plato
                    # `of=("self",)`: el orden del plato cruza con su categoría,
                    # nula en una promoción (SPEC-023); se bloquea solo el plato.
                    for plato in Plato.objects.select_for_update(of=("self",)).filter(
                        id__in=ids_platos,
                    ).order_by("id")
                }
                for item in resuelto["items"]:
                    plato = platos_bloqueados[item["plato"].id]
                    # SPEC-023: una promoción que venció entre que el cliente
                    # armó el carrito y el mesero confirma se rechaza igual que
                    # un plato agotado. Se revisa aquí, con la hora de ahora.
                    if not se_puede_vender(plato):
                        return Response(
                            {
                                "detalle": (
                                    f"{motivo_no_disponible(plato)} "
                                    "Pídele al cliente que elija otra cosa."
                                ),
                                "plato_agotado": plato.id,
                            },
                            status=409,
                        )
                    # Usa la instancia bloqueada y actual, no la que se resolvió
                    # antes de entrar a la transacción.
                    item["plato"] = plato

                # La cuenta se abre sola con el primer pedido de la mesa, y los
                # siguientes se suman a ella (SPEC-013). No se abre a mano: un
                # marcado más que recordar es lo primero que se deja de hacer.
                cuenta = cuenta_para(mesa=mesa, es_domicilio=es_domicilio)

                # El cliente se reconoce o se crea SOLO, sin paso previo
                # (SPEC-019). Un alta administrativa antes de vender es lo
                # primero que se deja de hacer en un viernes lleno, y entonces
                # el directorio queda a medias y no sirve para nada.
                #
                # Los datos vienen del QR firmado; si el mesero los corrigio en
                # pantalla, mandan los del cuerpo de la peticion.
                if es_domicilio:
                    telefono = request.data.get("telefono") or resuelto.get("telefono", "")
                    direccion = request.data.get("direccion") or resuelto.get("direccion", "")
                    cliente, _, _ = reconocer_o_crear(
                        telefono, resuelto["nombre_cliente"], direccion)
                    if cliente and cuenta.cliente_id != cliente.id:
                        cuenta.cliente = cliente
                        cuenta.save(update_fields=["cliente"])

                    # Costo de envío (SPEC-013/025, 2026-09-16): validado
                    # antes de entrar aquí; se guarda tal cual. Opcional —
                    # `None` es domicilio gratis.
                    if costo_envio is not None:
                        cuenta.costo_envio = costo_envio
                        cuenta.save(update_fields=["costo_envio"])

                pedido = Pedido.objects.create(
                    mesa=mesa,
                    es_domicilio=es_domicilio,
                    cuenta=cuenta,
                    mesero=request.user,
                    nombre_cliente=resuelto["nombre_cliente"],
                    codigo_qr=codigo_qr,
                )
                for it in resuelto["items"]:
                    DetallePedido.objects.create(
                        pedido=pedido,
                        plato=it["plato"],
                        nombre_congelado=it["plato"].nombre,
                        precio_congelado=it["plato"].precio,
                        desglose_congelado=desglose_para_congelar(it["plato"]),
                        cantidad=it["cantidad"],
                        observacion=it["observacion"],
                    )

                # Distribuye el pedido en comandas por estación (SPEC-005).
                # Dentro de la misma transacción: si el ruteo falla (p.ej. no
                # hay ninguna estación configurada), el pedido no queda a medias.
                rutear_pedido(pedido)

                # Confirmar un pedido es el ÚNICO evento que ocupa una mesa
                # (SPEC-012). Ni escanear el QR de la mesa ni generar el QR del
                # pedido la cambian: hasta que el mesero no lee ese QR, no hay
                # pedido y la mesa sigue como esté.
                if mesa is not None:
                    mesa.cambiar_estado(Mesa.OCUPADA)
        except IntegrityError:
            # Último respaldo para el domicilio simultáneo, que no tiene mesa
            # que bloquear: el `unique` de codigo_qr lo frena en la base. Sin
            # este except el mesero vería un 500 en vez de saber qué pasó.
            #
            # Se COMPRUEBA que fue eso y no otra cosa: culpar al QR de
            # cualquier choque futuro daría un mensaje tranquilizador y falso,
            # y el error real quedaría escondido.
            if Pedido.objects.filter(codigo_qr=codigo_qr).exists():
                return Response(
                    {"detalle": "Este QR ya fue usado en otro pedido."}, status=409)
            raise

        respuesta = {
            "pedido_id": pedido.id,
            "estado": pedido.estado,
            "es_domicilio": pedido.es_domicilio,
            "cuenta_id": pedido.cuenta_id,
        }

        # "Cobrar al finalizar" (SPEC-004): el atajo de mostrador. Es el mismo
        # camino con un paso más al final, no un flujo paralelo — mantener dos
        # versiones de lo mismo termina en que se desincronizan.
        #
        # Va FUERA de la transacción del pedido a propósito: si el cobro falla
        # (medio de pago inválido, sin permiso), el pedido ya está en cocina y
        # debe quedarse ahí. Se avisa y se cobra después desde Cuentas.
        medio_pago = request.data.get("medio_pago")
        if medio_pago:
            from ventas.operaciones import OperacionInvalida, cerrar_cuenta

            try:
                cerrar_cuenta(pedido.cuenta, request.user, medio_pago_id=medio_pago)
                respuesta["cobrada"] = True
            except OperacionInvalida as e:
                respuesta["cobrada"] = False
                respuesta["aviso_cobro"] = str(e)

        return Response(respuesta, status=201)


def _serializar_pedido(pedido):
    """Lo que el mesero necesita para decidir qué hacer con un pedido."""
    return {
        "id": pedido.id,
        "destino": pedido.destino,
        "mesa_codigo": pedido.mesa.codigo if pedido.mesa else None,
        "es_domicilio": pedido.es_domicilio,
        "estado": pedido.estado,
        # Pagado y entregado son independientes (SPEC-012): un pedido cobrado
        # sigue aquí hasta que alguien lo marque entregado.
        "cobrada": bool(pedido.cuenta_id and pedido.cuenta.estado == "cerrada"),
        "nombre_cliente": pedido.nombre_cliente,
        "creado": pedido.creado,
        "total": sum(d.precio_congelado * d.cantidad for d in pedido.detalles.all()),
        "detalles": [
            {
                "id": d.id,
                "nombre": d.nombre_congelado,
                "precio": d.precio_congelado,
                "cantidad": d.cantidad,
                "observacion": d.observacion,
                "estacion": d.comanda.estacion.nombre if d.comanda else None,
                "estado_comanda": d.comanda.estado if d.comanda else None,
            }
            for d in pedido.detalles.all()
        ],
        "novedades": [
            {"descripcion": n.descripcion, "creada": n.creada, "autor": n.autor.username}
            for n in pedido.novedades.all()
        ],
    }


class PedidosActivosView(APIView):
    """
    GET /api/pedidos/ — los pedidos en curso (SPEC-011).

    No existía, y lo necesitaban dos cosas a la vez: editar un pedido ya
    enviado, y llegar a un pedido cuya mesa se liberó — que desde el salón
    es inalcanzable, justamente porque su mesa ya no lo muestra.

    Muestra los de TODOS los meseros, coherente con el salón compartido: no
    hay dueño de mesa ni de pedido (SPEC-012).
    """

    permission_classes = [EsMesero]

    def get(self, request):
        pedidos = (
            Pedido.objects.exclude(estado__in=[Pedido.ENTREGADO, Pedido.ANULADO])
            .select_related("mesa", "cuenta")
            .prefetch_related("detalles__comanda__estacion", "novedades__autor")
            .order_by("-creado")
        )
        return Response([_serializar_pedido(p) for p in pedidos])


class _AccionSobrePedido(APIView):
    """
    Base de las operaciones de SPEC-011. Todas comparten: buscar el pedido,
    ejecutar, traducir `NovedadInvalida` a un 400 con mensaje para el
    mesero, y devolver el pedido ya actualizado.
    """

    permission_classes = [EsMesero]

    def ejecutar(self, pedido, request):
        raise NotImplementedError

    def post(self, request, pk):
        pedido = Pedido.objects.filter(pk=pk).first()
        if pedido is None:
            return Response({"detalle": "Ese pedido no existe."}, status=404)
        try:
            self.ejecutar(pedido, request)
        except NovedadInvalida as e:
            return Response({"detalle": str(e)}, status=400)
        pedido.refresh_from_db()
        return Response(_serializar_pedido(pedido))


class CambiarDestinoView(_AccionSobrePedido):
    """POST /api/pedidos/<id>/destino/ — a otra mesa, o a domicilio."""

    def ejecutar(self, pedido, request):
        cambiar_destino(
            pedido, request.user,
            mesa_codigo=request.data.get("mesa"),
            es_domicilio=bool(request.data.get("es_domicilio")),
        )


class AgregarItemView(_AccionSobrePedido):
    """POST /api/pedidos/<id>/items/agregar/"""

    def ejecutar(self, pedido, request):
        agregar_item(
            pedido, request.user,
            plato_id=request.data.get("plato_id"),
            cantidad=int(request.data.get("cantidad") or 1),
            observacion=request.data.get("observacion", ""),
        )


class QuitarItemView(_AccionSobrePedido):
    """POST /api/pedidos/<id>/items/quitar/"""

    def ejecutar(self, pedido, request):
        quitar_item(pedido, request.user, detalle_id=request.data.get("detalle_id"))


class CambiarCantidadView(_AccionSobrePedido):
    """POST /api/pedidos/<id>/items/cantidad/"""

    def ejecutar(self, pedido, request):
        cambiar_cantidad(
            pedido, request.user,
            detalle_id=request.data.get("detalle_id"),
            cantidad=int(request.data.get("cantidad") or 0),
        )


class CambiarObservacionView(_AccionSobrePedido):
    """POST /api/pedidos/<id>/items/observacion/"""

    def ejecutar(self, pedido, request):
        cambiar_observacion(
            pedido, request.user,
            detalle_id=request.data.get("detalle_id"),
            observacion=request.data.get("observacion", ""),
        )


class EditarPedidoLoteView(APIView):
    """
    POST /api/pedidos/<id>/editar/ — varios cambios en UNA transacción.

    Existe por una razón de honestidad con la interfaz: la pantalla ofrece un
    botón **"Aplicar cambios"**, y si el mesero revisa cinco ediciones y
    confirma una vez, aplicar tres y fallar en la cuarta lo dejaría peor que
    antes — el pedido a medias y él sin saber qué quedó. **O entran todas o
    no entra ninguna.**

    Cada operación sigue generando su propia `Novedad` (SPEC-011): el lote es
    cómo se aplican, no cómo se registran. La cocina ve los cambios uno por
    uno, como debe ser.
    """

    permission_classes = [EsMesero]

    def post(self, request, pk):
        pedido = Pedido.objects.filter(pk=pk).first()
        if pedido is None:
            return Response({"detalle": "Ese pedido no existe."}, status=404)

        operaciones = request.data.get("operaciones") or []
        if not operaciones:
            return Response({"detalle": "No hay cambios que aplicar."}, status=400)

        try:
            with transaction.atomic():
                for i, op in enumerate(operaciones, start=1):
                    tipo = op.get("tipo")
                    if tipo == "destino":
                        cambiar_destino(
                            pedido, request.user,
                            mesa_codigo=op.get("mesa"),
                            es_domicilio=bool(op.get("es_domicilio")),
                        )
                    elif tipo == "cantidad":
                        cambiar_cantidad(pedido, request.user,
                                         detalle_id=op.get("detalle_id"),
                                         cantidad=int(op.get("cantidad") or 0))
                    elif tipo == "quitar":
                        quitar_item(pedido, request.user, detalle_id=op.get("detalle_id"))
                    elif tipo == "observacion":
                        cambiar_observacion(pedido, request.user,
                                            detalle_id=op.get("detalle_id"),
                                            observacion=op.get("observacion", ""))
                    elif tipo == "agregar":
                        agregar_item(pedido, request.user,
                                     plato_id=op.get("plato_id"),
                                     cantidad=int(op.get("cantidad") or 1),
                                     observacion=op.get("observacion", ""))
                    else:
                        raise NovedadInvalida(f"Tipo de cambio desconocido: {tipo}")
        except NovedadInvalida as e:
            # El `atomic` ya revirtió todo. Se dice CUÁL falló para que el
            # mesero sepa qué corregir, en vez de un "no se pudo" a secas.
            return Response(
                {"detalle": f"Cambio {i} de {len(operaciones)}: {e}. No se aplicó ninguno."},
                status=400,
            )
        except (ValueError, TypeError):
            return Response({"detalle": "Alguno de los cambios trae datos inválidos."}, status=400)

        pedido.refresh_from_db()
        return Response(_serializar_pedido(pedido))


class NotificacionesView(APIView):
    """
    GET /api/pedidos/notificaciones/ — solo las del mesero autenticado
    (SPEC-006): nunca las de otro. El badge es simplemente contar las que
    no están leídas.
    """

    permission_classes = [EsMesero]

    def get(self, request):
        notifs = Notificacion.objects.filter(mesero=request.user).select_related(
            "pedido__mesa", "comanda__estacion"
        )
        return Response([
            {
                "id": n.id,
                "pedido_id": n.pedido_id,
                "mensaje": n.mensaje,
                "leida": n.leida,
                "creada": n.creada,
                "estado_pedido": n.pedido.estado,
            }
            for n in notifs
        ])


class MarcarNotificacionLeidaView(APIView):
    permission_classes = [EsMesero]

    def post(self, request, pk):
        actualizadas = Notificacion.objects.filter(pk=pk, mesero=request.user).update(leida=True)
        if not actualizadas:
            return Response({"detalle": "No encontrada."}, status=404)
        return Response({"ok": True})


class EntregarPedidoView(APIView):
    """
    POST /api/pedidos/<id>/entregar/ — se llevó a la mesa, o el domiciliario
    volvió. Cierra la venta y apaga TODAS las notificaciones de ese pedido,
    aunque alguna comanda individual no se haya marcado leída todavía.

    **Cualquier mesero puede entregar cualquier pedido** (SPEC-012, salón
    compartido). Antes filtraba por `mesero=request.user`, lo que en un
    domicilio era peor todavía: quien recibe al domiciliario rara vez es
    quien tomó el pedido.
    """

    permission_classes = [EsMesero]

    def post(self, request, pk):
        pedido = Pedido.objects.filter(pk=pk).first()
        if pedido is None:
            return Response({"detalle": "Pedido no encontrado."}, status=404)

        if pedido.estado in (Pedido.ENTREGADO, Pedido.ANULADO):
            return Response(
                {"detalle": f"El pedido ya está «{pedido.get_estado_display()}»."},
                status=400,
            )

        # Un DOMICILIO se entrega cuando el domiciliario vuelve, que puede ser
        # mucho después de que cocina terminara — o antes de que marquen la
        # comanda. Atarlo al estado de cocina dejaría al mesero esperando por
        # un trámite ajeno (SPEC-012).
        if not pedido.es_domicilio and pedido.estado not in (Pedido.LISTO, Pedido.EN_PREPARACION):
            return Response(
                {"detalle": f"El pedido está «{pedido.estado}», no se puede entregar todavía."},
                status=400,
            )

        pedido.estado = Pedido.ENTREGADO
        pedido.entregado_por = request.user
        pedido.entregado_en = timezone.now()
        pedido.save(update_fields=["estado", "entregado_por", "entregado_en"])
        pedido.notificaciones.filter(leida=False).update(leida=True)

        return Response({"pedido_id": pedido.id, "estado": pedido.estado})
