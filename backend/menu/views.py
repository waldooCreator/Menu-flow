from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from nucleo.permisos import AdminOSoloLectura, CocinaOAdmin

from .models import Categoria, Etiqueta, ObservacionRapida, Plato
from .promociones import VISIBLES_AL_CLIENTE, estado_promocion
from .serializers import (
    CategoriaSerializer,
    EtiquetaSerializer,
    ObservacionRapidaSerializer,
    PlatoLecturaSerializer,
    PlatoSerializer,
)


class CategoriaViewSet(viewsets.ModelViewSet):
    """Lectura pública (la usa la página del cliente), escritura solo admin."""

    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [AdminOSoloLectura]


class EtiquetaViewSet(viewsets.ModelViewSet):
    queryset = Etiqueta.objects.all()
    serializer_class = EtiquetaSerializer
    permission_classes = [AdminOSoloLectura]


class ObservacionRapidaViewSet(viewsets.ModelViewSet):
    """
    Lectura pública (el carrito las muestra), escritura solo admin.

    Tres niveles (SPEC-003): `?generales=1` solo las que aplican a todos;
    `?categoria=<id>` las de esa sección (sin plato); `?plato=<id>` las de ese
    plato. Sin filtro, todas — es lo que consume el panel.

    Filtrado a mano en vez de `filterset_fields`: los tres niveles se
    distinguen por DOS campos nulos a la vez (plato Y categoria vacíos =
    general), algo que un filtro declarativo por campo no expresa limpio.
    """

    queryset = ObservacionRapida.objects.all()
    serializer_class = ObservacionRapidaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("generales"):
            qs = qs.filter(plato__isnull=True, categoria__isnull=True)
        elif params.get("plato"):
            qs = qs.filter(plato_id=params["plato"])
        elif params.get("categoria"):
            qs = qs.filter(categoria_id=params["categoria"], plato__isnull=True)
        if params.get("activo"):
            qs = qs.filter(activo=params["activo"] not in ("0", "false"))
        return qs
    permission_classes = [AdminOSoloLectura]


class PlatoViewSet(viewsets.ModelViewSet):
    """
    Lectura pública con TODOS los platos, incluidos los agotados: la página
    del cliente los muestra en gris, no los oculta (SPEC-003). Escritura
    solo admin, y con un serializador distinto (recibe IDs, no nombres).
    """

    queryset = (
        Plato.objects.select_related("categoria")
        .prefetch_related("etiquetas", "observaciones", "componentes")
        .all()
    )

    def list(self, request, *args, **kwargs):
        """
        Las promociones que no están vigentes (ni agotadas) no salen de la API
        pública (SPEC-023). Se filtran en Python y no en la consulta porque la
        vigencia depende de la hora, los días y una franja que puede cruzar la
        medianoche: son pocas filas, y la regla vive en un solo sitio.

        El panel pide `?todas=1` para ver también las programadas, vencidas y
        apagadas. Solo se respeta para el administrador: una promo que arranca
        el viernes no debe poder leerse por la API el martes.
        """
        if request.query_params.get("todas") and request.user.is_staff:
            return super().list(request, *args, **kwargs)
        platos = [
            p for p in self.filter_queryset(self.get_queryset())
            if not p.es_promocion or estado_promocion(p) in VISIBLES_AL_CLIENTE
        ]
        pagina = self.paginate_queryset(platos)
        if pagina is not None:
            return self.get_paginated_response(self.get_serializer(pagina, many=True).data)
        return Response(self.get_serializer(platos, many=True).data)

    def destroy(self, request, *args, **kwargs):
        """
        Un plato o una promoción con ventas no se borra: el historial
        congelado lo referencia (PROTECT). Se responde con qué hacer en su
        lugar, en vez de un error 500.
        """
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            plato = self.get_object()
            sugerencia = "apágala" if plato.es_promocion else "márcalo agotado"
            return Response(
                {"detalle": f"«{plato.nombre}» tiene ventas registradas: {sugerencia} en su lugar."},
                status=status.HTTP_409_CONFLICT,
            )

    def get_serializer_context(self):
        # Las generales y las de categoría, una sola vez para todos los
        # platos de esta página: resolverlas por plato serían N+1 consultas.
        contexto = super().get_serializer_context()
        contexto["observaciones_generales"] = list(
            ObservacionRapida.objects.filter(
                plato__isnull=True, categoria__isnull=True, activo=True)
        )
        por_categoria = {}
        de_categorias = ObservacionRapida.objects.filter(
            categoria__isnull=False, plato__isnull=True, activo=True)
        for o in de_categorias:
            por_categoria.setdefault(o.categoria_id, []).append(o)
        contexto["observaciones_por_categoria"] = por_categoria
        return contexto
    permission_classes = [AdminOSoloLectura]
    filterset_fields = ["categoria", "disponible"]

    def get_serializer_class(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return PlatoLecturaSerializer
        return PlatoSerializer


class DisponibilidadPlatoView(APIView):
    """Cambia solo disponibilidad desde cocina (SPEC-017)."""

    permission_classes = [CocinaOAdmin]

    def post(self, request, pk):
        disponible = request.data.get("disponible")
        if not isinstance(disponible, bool):
            return Response(
                {"detalle": "Indica disponible como verdadero o falso."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # `of=("self",)`: el orden por defecto del plato cruza con su
            # categoría, que en una promoción es nula (SPEC-023), y Postgres
            # no bloquea el lado nulo de un JOIN. Se bloquea solo el plato.
            plato = Plato.objects.select_for_update(of=("self",)).filter(pk=pk).first()
            if plato is None:
                return Response(
                    {"detalle": "Ese plato no existe."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if plato.disponible != disponible:
                plato.disponible = disponible
                plato.disponible_cambiado_por = request.user
                plato.disponible_cambiado_en = timezone.now()
                plato.save(update_fields=[
                    "disponible", "disponible_cambiado_por", "disponible_cambiado_en",
                ])

        return Response({
            "id": plato.id,
            "nombre": plato.nombre,
            "disponible": plato.disponible,
            "disponible_cambiado_por": (
                plato.disponible_cambiado_por.username
                if plato.disponible_cambiado_por else None
            ),
            "disponible_cambiado_en": plato.disponible_cambiado_en,
        })
