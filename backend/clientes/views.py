"""
API de clientes (SPEC-019). La ve quien puede cobrar y el administrador.
"""

from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ventas.views import PuedeCobrar

from .models import Cliente, DireccionCliente
from .operaciones import frecuentes, resumen_de


class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DireccionCliente
        fields = ["id", "direccion", "indicaciones", "veces_usada", "ultima_vez"]
        read_only_fields = ["veces_usada", "ultima_vez"]


class ClienteSerializer(serializers.ModelSerializer):
    direcciones = DireccionSerializer(many=True, read_only=True)
    resumen = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = ["id", "nombre", "telefono", "observaciones",
                  "direcciones", "resumen", "creado"]

    def get_resumen(self, cliente):
        return resumen_de(cliente)

    def validate_telefono(self, valor):
        from .models import normalizar_telefono

        numero = normalizar_telefono(valor)
        if not numero:
            raise serializers.ValidationError("Escribe un teléfono.")
        return numero


class ClienteViewSet(viewsets.ModelViewSet):
    """
    CRUD completo, incluido BORRAR — es un requisito de la Ley 1581, no una
    comodidad: el titular puede pedir que se supriman sus datos.

    Borrar el cliente **no borra sus ventas**: el vínculo es `SET_NULL`, así
    que las cuentas quedan con su nombre congelado y su historia contable
    intacta (SPEC-008). Solo desaparece el dato personal.
    """

    serializer_class = ClienteSerializer
    permission_classes = [PuedeCobrar]

    def get_queryset(self):
        qs = Cliente.objects.prefetch_related("direcciones")
        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            from django.db.models import Q

            from .models import normalizar_telefono

            # Se busca por nombre O por telefono a la vez: quien busca no
            # deberia tener que decidir antes cual de los dos esta escribiendo.
            solo_digitos = normalizar_telefono(buscar)
            filtro = Q(nombre__icontains=buscar)
            if solo_digitos:
                filtro |= Q(telefono__contains=solo_digitos)
            qs = qs.filter(filtro)
        return qs

    @action(detail=True, methods=["post"], url_path="direcciones")
    def agregar_direccion(self, request, pk=None):
        cliente = self.get_object()
        texto = (request.data.get("direccion") or "").strip()
        if not texto:
            return Response({"detalle": "Escribe la dirección."}, status=400)

        # Si ya la tiene escrita de otra forma, se reusa en vez de duplicar.
        existente = cliente.direccion_parecida(texto)
        if existente:
            return Response(DireccionSerializer(existente).data)

        direccion = DireccionCliente.objects.create(
            cliente=cliente, direccion=texto,
            indicaciones=(request.data.get("indicaciones") or "").strip())
        return Response(DireccionSerializer(direccion).data, status=201)

    @action(detail=True, methods=["delete"], url_path=r"direcciones/(?P<direccion_id>\d+)")
    def quitar_direccion(self, request, pk=None, direccion_id=None):
        cliente = self.get_object()
        borradas, _ = cliente.direcciones.filter(id=direccion_id).delete()
        if not borradas:
            return Response({"detalle": "Esa dirección no existe."}, status=404)
        return Response(status=204)

    @action(detail=False, methods=["get"])
    def frecuentes(self, request):
        """El 5º reporte de SPEC-018, que este módulo desbloquea."""
        p = request.query_params
        return Response(frecuentes(p.get("desde") or None, p.get("hasta") or None))
