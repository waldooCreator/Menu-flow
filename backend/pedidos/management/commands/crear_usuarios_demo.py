"""
Crea los usuarios de rol para la demostración: `mesero` y `cocina`, cada uno
en su grupo. El superusuario `admin` ya existe (createsuperuser) y pasa por
todos los permisos.
"""

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

USUARIOS = [
    # usuario, contraseña, grupo
    ("mesero", "mesero2026", "mesero"),
    ("cocina", "cocina2026", "cocina"),
]


class Command(BaseCommand):
    help = "Crea los usuarios mesero y cocina con sus grupos de rol"

    def handle(self, *args, **options):
        for nombre, clave, grupo_nombre in USUARIOS:
            grupo, _ = Group.objects.get_or_create(name=grupo_nombre)
            usuario, creado = User.objects.get_or_create(username=nombre)
            usuario.set_password(clave)
            usuario.is_active = True
            usuario.save()
            usuario.groups.set([grupo])
            estado = "creado" if creado else "actualizado"
            self.stdout.write(f"  {nombre} ({grupo_nombre}): {estado}")

        self.stdout.write(self.style.SUCCESS("Usuarios de rol listos."))
