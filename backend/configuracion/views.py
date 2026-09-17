from django.conf import settings
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .helpers import obtener_configuracion
from .models import Parametro
from .serializers import ConfiguracionPublicaSerializer, ParametroSerializer


class ParametroViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de configuración — lo consume el panel Vue de
    administración. Requiere autenticación siempre: es donde se cambian
    colores, textos e imágenes de todo el sitio.
    """

    queryset = Parametro.objects.all()
    serializer_class = ParametroSerializer
    # Solo el administrador: ni el mesero ni cocina gestionan configuración
    # (decisión del autor, 2026-08-25).
    permission_classes = [IsAdminUser]
    filterset_fields = ["grupo", "tipo"]


class ConfiguracionPublicaView(APIView):
    """
    GET /api/configuracion/publica/ — {clave: valor}, sin autenticación.
    Es lo que consume la página del cliente en Vue para pintar la paleta,
    los textos y las imágenes del restaurante antes del primer render.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        datos = dict(obtener_configuracion())

        # Las rutas de imagen se guardan relativas (SPEC-009: eso es lo que
        # hace portable la instalación). Pero el frontend corre en OTRO
        # origen —Vue en :5173, Django en :8000— así que una ruta relativa
        # la resolvería contra Vue y la imagen no cargaría. Se absolutizan
        # aquí, en la frontera de la API, no en la base.
        for clave, valor in datos.items():
            if isinstance(valor, str) and valor.startswith(settings.MEDIA_URL):
                datos[clave] = request.build_absolute_uri(valor)

        return Response(ConfiguracionPublicaSerializer(datos).data)
