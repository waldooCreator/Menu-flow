from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from nucleo.permisos import CocinaLecturaAdminEscritura, EsCocina
from pedidos.models import Notificacion, Pedido

from .models import Comanda, Estacion
from .serializers import ComandaSerializer, EstacionSerializer


class EstacionViewSet(viewsets.ModelViewSet):
    """
    Lectura para el personal de estación (el tablero la necesita) y CRUD
    para el administrador desde el panel (SPEC-007). El borrado se protege
    solo: las comandas apuntan con PROTECT, así que una estación con
    historia no se puede eliminar — se reporta el error, no se pierde nada.
    """

    queryset = Estacion.objects.all()
    serializer_class = EstacionSerializer
    permission_classes = [CocinaLecturaAdminEscritura]


def _recalcular_estado_pedido(pedido):
    """
    El estado del pedido se DERIVA del de sus comandas — nunca se elige a
    mano, salvo "entregado" (acción del mesero) y "anulado".
    """
    if pedido.estado in (Pedido.ENTREGADO, Pedido.ANULADO):
        return

    estados = list(pedido.comandas.values_list("estado", flat=True))
    if not estados:
        return

    if all(e == Comanda.LISTA for e in estados):
        nuevo = Pedido.LISTO
    elif any(e in (Comanda.EN_PREPARACION, Comanda.LISTA) for e in estados):
        nuevo = Pedido.EN_PREPARACION
    else:
        nuevo = Pedido.PENDIENTE

    if nuevo != pedido.estado:
        pedido.estado = nuevo
        pedido.save(update_fields=["estado"])


class ComandaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    El tablero de una estación (SPEC-005): tarjetas pendientes, en
    preparación y listas. Autenticado — es personal interno, no el cliente.
    """

    serializer_class = ComandaSerializer
    permission_classes = [EsCocina]

    def get_queryset(self):
        qs = Comanda.objects.select_related("pedido__mesa", "estacion").prefetch_related("detalles")
        params = self.request.query_params
        estacion_id = params.get("estacion")
        if estacion_id:
            qs = qs.filter(estacion_id=estacion_id)
        # El tablero pide solo lo que está en curso. Sin esto la historia
        # (pedidos entregados o anulados) ocupaba la página, y con estaciones
        # unificadas —todas las comandas juntas— las nuevas quedaban fuera
        # (SPEC-023, sección 7).
        if params.get("activas"):
            qs = qs.exclude(pedido__estado__in=[Pedido.ENTREGADO, Pedido.ANULADO])
        return qs

    def _bloquear(self):
        """
        Relee la comanda con su fila bloqueada, dentro de la transacción que
        abre quien llama (ADR-008). Sin esto, dos cocineros que tocan
        "Empezar" a la vez leen los dos "pendiente" y los dos la toman.

        Se bloquea primero el pedido y después la comanda, siempre en ese
        orden: dos estaciones que terminan comandas del mismo pedido se
        esperan, y el estado derivado del pedido se calcula sobre lo que la
        otra ya guardó. Si no, las dos podían marcar "lista" y el pedido
        quedarse en preparación.

        `get_object()` va primero para conservar el 404 y los permisos; el
        bloqueo va sin `select_related` porque Postgres no bloquea el lado
        nulo de un JOIN, y la mesa de un domicilio es nula.
        """
        comanda = self.get_object()
        Pedido.objects.select_for_update().get(pk=comanda.pedido_id)
        return Comanda.objects.select_for_update().get(pk=comanda.pk)

    @action(detail=True, methods=["post"], url_path="en-preparacion")
    def en_preparacion(self, request, pk=None):
        with transaction.atomic():
            comanda = self._bloquear()
            if comanda.estado != Comanda.PENDIENTE:
                # SPEC-005: la segunda toma se rechaza con un motivo que se
                # pueda mostrar, en vez de aceptarla en silencio.
                detalle = ("Esta comanda ya está lista." if comanda.estado == Comanda.LISTA
                           else "Otra persona ya empezó a preparar esta comanda.")
                return Response({"detalle": detalle}, status=status.HTTP_409_CONFLICT)
            comanda.marcar_en_preparacion()
            _recalcular_estado_pedido(comanda.pedido)
        return Response(ComandaSerializer(comanda).data)

    @action(detail=True, methods=["post"])
    def visto(self, request, pk=None):
        """
        POST /api/comandas/<id>/visto/ — la estación acusa recibo de las
        novedades y su tarjeta deja de estar en rojo (SPEC-011).

        Poder apagar el aviso es parte del mecanismo: una alerta que nadie
        puede cerrar se vuelve papel tapiz, y a las dos horas de servicio el
        rojo dejaría de significar nada.
        """
        comanda = self.get_object()
        comanda.marcar_novedades_vistas()
        return Response(ComandaSerializer(comanda).data)

    @action(detail=True, methods=["post"])
    def lista(self, request, pk=None):
        with transaction.atomic():
            comanda = self._bloquear()
            if comanda.estado == Comanda.LISTA:
                # Dos "Listo" seguidos avisarían dos veces al mesero.
                return Response({"detalle": "Esta comanda ya se marcó como lista."},
                                status=status.HTTP_409_CONFLICT)
            comanda.marcar_lista()

            # Dispara la notificación al mesero dueño del pedido (SPEC-006):
            # una por comanda lista, dirigida solo a él, nunca a todos.
            # `destino` y no `mesa.nombre`: un domicilio no tiene mesa, y
            # caminar hasta ella tumbaba la petición antes de avisar (SPEC-011).
            Notificacion.objects.create(
                mesero=comanda.pedido.mesero,
                pedido=comanda.pedido,
                comanda=comanda,
                mensaje=f"{comanda.estacion.nombre} — {comanda.pedido.destino} está lista",
            )

            _recalcular_estado_pedido(comanda.pedido)
        return Response(ComandaSerializer(comanda).data)
