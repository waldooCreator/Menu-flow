from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.operaciones import puede_cobrar


ORDEN_ROLES = {"admin": 0, "cajero": 1, "mesero": 2, "cocina": 3}


class PerfilView(APIView):
    """
    GET /api/auth/perfil/ — quién soy y qué rol tengo. Lo usa Vue justo
    después del login para llevar a cada usuario a SU pantalla (mesero,
    cocina o admin) y ocultarle las que no le corresponden.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        if u.is_superuser:
            rol = "admin"
            roles = ["admin"]
        else:
            roles = sorted(
                u.groups.values_list("name", flat=True),
                key=lambda nombre: ORDEN_ROLES.get(nombre, 99),
            )
            rol = roles[0] if roles else "sin-rol"
        return Response({
            "usuario": u.username,
            "rol": rol,
            "roles": roles,
            "puede_cobrar": puede_cobrar(u),
        })
