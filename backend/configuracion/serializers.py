from rest_framework import serializers

from .models import Parametro


class ParametroSerializer(serializers.ModelSerializer):
    valor_resuelto = serializers.SerializerMethodField()

    class Meta:
        model = Parametro
        fields = [
            "id", "clave", "etiqueta", "grupo", "tipo",
            "valor", "imagen", "ayuda", "orden", "valor_resuelto",
        ]

    def get_valor_resuelto(self, obj):
        return obj.valor_resuelto()


class ConfiguracionPublicaSerializer(serializers.Serializer):
    """
    Forma plana {clave: valor} — lo que de verdad consume la página del
    cliente. No expone `id`, `ayuda` ni el resto de metadatos administrativos.
    """

    def to_representation(self, instance):
        # `instance` es el dict que devuelve configuracion.helpers.obtener_configuracion()
        return instance
