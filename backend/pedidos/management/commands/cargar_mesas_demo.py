from django.core.management.base import BaseCommand

from pedidos.models import Mesa

# Mesas FÍSICAS del salón (SPEC-012). Ya NO hay mesa virtual "Domicilio":
# desde 2026-08-26 un pedido a distancia no tiene mesa (SPEC-002), así que
# no puede ensuciar el salón ni por accidente.
MESAS = [
    ("Mesa 12", "x7f2q9"),  # el código usado en todos los ejemplos de la documentación
    ("Mesa 5", "b3k9m2"),
    ("Mesa 3", "p6w1t4"),
    ("Mesa 7", "n2h8z5"),
    ("Mesa 9", "r4v7c1"),
    ("Terraza 1", "t9j3d6"),
]


class Command(BaseCommand):
    help = "Siembra mesas de prueba"

    def handle(self, *args, **options):
        creadas = 0
        for nombre, codigo in MESAS:
            _, fue_creada = Mesa.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})
            creadas += fue_creada
        self.stdout.write(self.style.SUCCESS(f"Mesas: {creadas} creadas."))
