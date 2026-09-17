"""Deja la operación en blanco para iniciar los tiquetes (SPEC-016).

Solo elimina datos operativos. Conserva el restaurante montado: menú,
etiquetas, mesas, estaciones, cajas, usuarios y configuración.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.management.base import BaseCommand

from configuracion.models import Parametro
from estaciones.models import Comanda, Estacion
from menu.models import Categoria, Etiqueta, ObservacionRapida, Plato
from pedidos.models import DetallePedido, Mesa, Notificacion, Novedad, Pedido
from ventas.models import Caja, Cuenta, MovimientoCaja, Turno


class Command(BaseCommand):
    help = "Borra la operación y conserva la configuración del restaurante"

    def add_arguments(self, parser):
        parser.add_argument(
            "--si", action="store_true",
            help="Confirma el borrado sin preguntar",
        )

    def handle(self, *args, **options):
        conteo = {
            "pedidos": Pedido.objects.count(),
            "renglones": DetallePedido.objects.count(),
            "comandas": Comanda.objects.count(),
            "notificaciones": Notificacion.objects.count(),
            "novedades": Novedad.objects.count(),
            "cuentas": Cuenta.objects.count(),
            "movimientos": MovimientoCaja.objects.count(),
            "turnos": Turno.objects.count(),
        }

        if not any(conteo.values()):
            self.stdout.write("Ya está limpia: no hay datos operativos.")
            return

        if not options["si"]:
            self.stdout.write(
                "Se borrarán: " + ", ".join(
                    f"{cantidad} {nombre}" for nombre, cantidad in conteo.items()
                ) + "."
            )
            self.stdout.write("Vuelve a ejecutarlo con --si para confirmar.")
            return

        # Los PROTECT obligan a retirar primero movimientos, hijos y pedidos.
        # Todo queda en una transacción: o se limpia completo o no se toca nada.
        preservados = [
            Mesa, Estacion, Categoria, Plato, Etiqueta, ObservacionRapida,
            Caja, get_user_model(), Parametro,
        ]
        antes_preservados = {modelo: modelo.objects.count() for modelo in preservados}
        with transaction.atomic():
            MovimientoCaja.objects.all().delete()
            Notificacion.objects.all().delete()
            Novedad.objects.all().delete()
            DetallePedido.objects.all().delete()
            Comanda.objects.all().delete()
            Pedido.objects.all().delete()
            Cuenta.objects.all().delete()
            Turno.objects.all().delete()

            if any(
                modelo.objects.count() != cantidad
                for modelo, cantidad in antes_preservados.items()
            ):
                raise RuntimeError("El reinicio alteró datos que debían conservarse.")

            for modelo in (
                Pedido, DetallePedido, Comanda, Notificacion, Novedad,
                Cuenta, MovimientoCaja, Turno,
            ):
                if modelo.objects.exists():
                    raise RuntimeError(f"No se pudo limpiar {modelo.__name__}.")

        self.stdout.write(self.style.SUCCESS(
            "Operación limpia: " + ", ".join(
                f"{cantidad} {nombre}" for nombre, cantidad in conteo.items()
            ) + ". Se conservaron menú, etiquetas, configuración, mesas, estaciones, "
            "cajas y usuarios."
        ))
