"""
Gestión de usuarios desde el panel Vue (SPEC-007: "Gestion de usuarios").
Hasta hoy solo existía `crear_usuarios_demo` — un restaurante real no puede
contratar un mesero nuevo por la terminal del servidor.

Deliberadamente básico: usuario, clave, rol (mesero/cocina) y activo.
Sin correo, sin recuperación de clave, sin permisos finos — la clave la
restablece el administrador en persona, que es como funciona un restaurante.
"""

from django.contrib.auth.models import Group, User
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

# El cajero cobra y maneja el turno (SPEC-014). El mesero puede cobrar
# tambien, si el parametro "meseros-pueden-cobrar" esta encendido.
ROLES = ("mesero", "cajero", "cocina")


def _rol_de(user):
    if user.is_superuser:
        return "admin"
    grupo = user.groups.first()
    return grupo.name if grupo else "sin-rol"


class UsuarioSerializer(serializers.ModelSerializer):
    rol = serializers.ChoiceField(choices=ROLES, write_only=True)
    rol_actual = serializers.SerializerMethodField()
    # Solo al crear. Nunca viaja de vuelta.
    password = serializers.CharField(write_only=True, min_length=6, max_length=128)

    class Meta:
        model = User
        fields = ["id", "username", "password", "rol", "rol_actual", "is_active"]

    def get_rol_actual(self, obj):
        return _rol_de(obj)

    def validate_username(self, valor):
        return valor.strip().lower()

    def create(self, datos):
        rol = datos.pop("rol")
        password = datos.pop("password")
        usuario = User.objects.create_user(
            username=datos["username"], password=password,
            is_active=datos.get("is_active", True),
        )
        grupo, _ = Group.objects.get_or_create(name=rol)
        usuario.groups.add(grupo)
        return usuario

    def update(self, usuario, datos):
        # Al editar solo cambian rol y activo; la clave tiene acción propia.
        datos.pop("password", None)
        rol = datos.pop("rol", None)
        if rol:
            usuario.groups.clear()
            grupo, _ = Group.objects.get_or_create(name=rol)
            usuario.groups.add(grupo)
        return super().update(usuario, datos)


class UsuarioViewSet(viewsets.ModelViewSet):
    """
    Solo administrador. Sin DELETE: un usuario con ventas a su nombre no
    puede desaparecer (toda venta tiene responsable, regla del proyecto) —
    se desactiva y no puede entrar más, pero su historial queda.
    """

    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        # Los superusuarios no se administran desde aquí: el panel gestiona
        # al personal, no a quien gestiona el panel.
        return User.objects.filter(is_superuser=False).order_by("username")

    @action(detail=True, methods=["post"], url_path="clave")
    def clave(self, request, pk=None):
        """Restablecer la clave — la fija el administrador en persona."""
        nueva = request.data.get("password", "")
        if len(nueva) < 6:
            return Response({"detalle": "La clave debe tener al menos 6 caracteres."}, status=400)
        usuario = self.get_object()
        usuario.set_password(nueva)
        usuario.save(update_fields=["password"])
        return Response({"detalle": f"Clave de {usuario.username} actualizada."})
