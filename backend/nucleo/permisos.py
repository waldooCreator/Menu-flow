"""
Permisos por rol (SPEC-007, decisión del autor 2026-08-25):
el mesero no accede a cocina, cocina no accede al mesero, y ninguno de los
dos al panel de administración. El superusuario (admin) pasa por todo.

Los roles son grupos de Django ("mesero", "cocina") — los crea el comando
`crear_usuarios_demo`. La gestión de usuarios desde el panel sigue pendiente.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


def _tiene_rol(user, rol):
    return bool(
        user and user.is_authenticated
        and (user.is_superuser or user.groups.filter(name=rol).exists())
    )


class EsMesero(BasePermission):
    """
    Mesero, cajero o administrador.

    El cajero hace todo lo del mesero y ademas cobra (SPEC-014), igual que
    en el sistema que se va a reemplazar. Cobrar tiene su propio permiso
    configurable en `ventas.views.PuedeCobrar`.
    """

    def has_permission(self, request, view):
        return _tiene_rol(request.user, "mesero") or _tiene_rol(request.user, "cajero")


class EsCocina(BasePermission):
    """Personal de estación (cocina/bar/postres) o administrador."""

    def has_permission(self, request, view):
        return _tiene_rol(request.user, "cocina")


class CocinaOAdmin(BasePermission):
    """Cocina o administración para operaciones de disponibilidad (SPEC-017)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.groups.filter(name="cocina").exists())
        )


class CocinaLecturaAdminEscritura(BasePermission):
    """
    Estaciones (SPEC-005/007): el personal de estación las LEE (el tablero
    necesita la lista), pero crearlas o moverlas es configuración — solo
    el administrador. Antes eran de solo lectura absoluta y crearlas exigía
    la terminal del servidor.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return _tiene_rol(request.user, "cocina")
        return bool(request.user and request.user.is_staff)


class AdminOSoloLectura(BasePermission):
    """Lectura para cualquiera; escritura solo para el administrador."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)
