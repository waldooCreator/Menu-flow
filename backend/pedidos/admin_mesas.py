"""
Administración de mesas desde el panel Vue (SPEC-001, pendiente desde el
inicio: "el administrador puede crear, desactivar y regenerar el QR de una
mesa" — hasta hoy solo existía el comando de siembra).

El QR de la mesa NO se guarda: es simplemente la URL `/m/<codigo>` dibujada
como código, y eso lo hace el navegador del panel con la misma librería que
ya dibuja el QR del pedido. Regenerar el código invalida el QR impreso
anterior — esa es justamente su utilidad (se filtró una foto del QR, se
imprime uno nuevo).
"""

from django.utils.crypto import get_random_string
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import Mesa, Pedido


class MesaAdminSerializer(serializers.ModelSerializer):
    # Cuántos pedidos históricos la referencian: el panel lo usa para
    # explicar por qué una mesa se desactiva y no se borra (SPEC-008: el
    # pasado no se toca).
    pedidos_historicos = serializers.IntegerField(source="pedidos.count", read_only=True)

    class Meta:
        model = Mesa
        fields = ["id", "nombre", "codigo", "activa", "estado", "pedidos_historicos"]
        # El código lo genera el modelo; cambiarlo tiene endpoint propio
        # (regenerar) para que nunca sea un texto elegido a mano y adivinable.
        read_only_fields = ["codigo", "estado"]


class MesaAdminViewSet(viewsets.ModelViewSet):
    """
    CRUD de mesas, solo administrador. Sin DELETE: una mesa con pedidos
    está protegida por la base (PROTECT) y una sin pedidos tampoco se borra
    por uniformidad — se desactiva, igual que la mesa virtual de domicilio.
    """

    queryset = Mesa.objects.all().order_by("nombre")
    serializer_class = MesaAdminSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "patch", "head", "options"]

    @action(detail=True, methods=["post"], url_path="regenerar-codigo")
    def regenerar_codigo(self, request, pk=None):
        """El QR impreso anterior deja de valer; se imprime el nuevo."""
        mesa = self.get_object()
        mesa.codigo = get_random_string(8).lower()
        mesa.save(update_fields=["codigo"])
        return Response(MesaAdminSerializer(mesa).data)
