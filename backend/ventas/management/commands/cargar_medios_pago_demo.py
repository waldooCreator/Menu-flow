"""
Siembra los medios de pago (SPEC-013).

Son los que usa de verdad un restaurante en Colombia. Configurables: cada
cliente activa o desactiva los suyos desde el panel, nunca se tocan aqui.

NO se incluye "creditos pendientes" (fiar): el autor lo descarto — toda
cuenta cerrada esta cobrada de verdad, para que el reporte de ventas y el
cuadre de caja no puedan discrepar.
"""

from django.core.management.base import BaseCommand

from ventas.models import Caja

MEDIOS = [
    ("Efectivo", "Ef"),
    ("Nequi", "Ne"),
    ("Daviplata", "Da"),
    ("Bancolombia", "Ba"),
    ("Datafono", "Df"),
]


class Command(BaseCommand):
    help = "Siembra los medios de pago basicos"

    def handle(self, *args, **options):
        creados = 0
        for orden, (nombre, prefijo) in enumerate(MEDIOS):
            _, nuevo = Caja.objects.update_or_create(
                nombre=nombre,
                defaults={"orden": orden, "prefijo": prefijo},
            )
            creados += nuevo
        self.stdout.write(self.style.SUCCESS(f"Cajas: {creados} creados."))
