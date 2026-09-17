from django.core.management.base import BaseCommand

from estaciones.models import Estacion
from menu.models import Categoria

ESTACIONES = [
    ("Cocina", 0, True),   # estación por defecto
    ("Bar", 1, False),
    ("Postres", 2, False),
]

RUTEO = {
    "Para Compartir": "Cocina",
    "Bowls": "Cocina",
    "Del Asador": "Cocina",
    "Bebidas": "Bar",
    "Postres": "Postres",
}


class Command(BaseCommand):
    help = "Siembra estaciones de prueba y asigna las categorías existentes (SPEC-005)"

    def handle(self, *args, **options):
        estaciones = {}
        for nombre, orden, por_defecto in ESTACIONES:
            est, _ = Estacion.objects.update_or_create(
                nombre=nombre, defaults={"orden": orden, "por_defecto": por_defecto},
            )
            estaciones[nombre] = est

        asignadas = 0
        for nombre_cat, nombre_est in RUTEO.items():
            actualizadas = Categoria.objects.filter(nombre=nombre_cat).update(
                estacion=estaciones[nombre_est]
            )
            asignadas += actualizadas

        self.stdout.write(self.style.SUCCESS(
            f"Estaciones: {len(estaciones)} · Categorías ruteadas: {asignadas}"
        ))
