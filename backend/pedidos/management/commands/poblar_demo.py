"""
Deja el sistema con datos en TODAS las pantallas, para poder auditarlas.

Nace de SPEC-022: cuatro pantallas dieron cero fallos responsive **porque
estaban vacias**, y una pantalla vacia aprueba el examen sin merecerlo. Sin
esto, cada auditoria depende de que alguien recuerde crear los datos a mano —
y de que los cree iguales que la vez anterior.

Los textos son **deliberadamente largos**: nombres de cliente de tres apellidos,
direcciones con indicaciones, observaciones de dos frases. Un nombre corto no
prueba nada; lo que rompe la maquetacion es el nombre largo.

    python manage.py poblar_demo          # agrega lo que falte
    python manage.py poblar_demo --limpiar  # borra lo suyo y lo vuelve a crear

No toca las ventas historicas ni la configuracion.
"""

import uuid

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from clientes.models import Cliente
from clientes.operaciones import reconocer_o_crear
from estaciones.models import Comanda
from menu.models import Plato
from pedidos.models import Mesa, Pedido
from ventas.models import Caja, Cuenta, MovimientoCaja, Turno
from ventas.operaciones import abrir_turno, cerrar_cuenta, cerrar_turno

MARCA = "[demo-responsive]"


def _codigo():
    """
    `Pedido.codigo_qr` es unico y no tiene valor por defecto: sin darle uno,
    el segundo pedido choca con el primero por la cadena vacia.
    """
    return f"demo{uuid.uuid4().hex[:11]}"

# Nombres largos a proposito: lo que rompe una fila es el caso extremo.
CLIENTES = [
    ("3202766485", "Maria Angelica Villamizar Rodriguez",
     "Barrio La Libertad, calle 12 num 4-56, casa verde de dos pisos",
     "Paga en efectivo y casi nunca tiene cambio de 50. Timbre danado: hay que llamar al llegar."),
    ("3115554433", "Jose Ramirez", "Av 4 con calle 12, edificio Bucarica apto 802", ""),
    ("3009998877", "Ana Sofia Contreras de la Espriella",
     "Conjunto Residencial Palmeras del Norte, torre 3 apto 302", "Alergica al mani."),
]

MESAS_CON_CUENTA = [
    ("Ana Maria Restrepo Gutierrez", [(0, 2, "sin cebolla, por favor"), (1, 1, "")]),
    ("Grupo de la oficina (somos 8)", [(2, 3, "uno sin picante y dos bien picantes"), (3, 2, "")]),
]


class Command(BaseCommand):
    help = "Puebla todas las pantallas con datos, para auditarlas (SPEC-022)."

    def add_arguments(self, parser):
        parser.add_argument("--limpiar", action="store_true",
                            help="Borra los datos de demostracion antes de crearlos.")

    def handle(self, *args, **opciones):
        if opciones["limpiar"]:
            self._limpiar()

        platos = list(Plato.objects.filter(disponible=True, tipo=Plato.PLATO)[:6])
        mesas = list(Mesa.objects.filter(activa=True)[:4])
        if not platos or not mesas:
            self.stderr.write("Faltan platos o mesas. Corre antes cargar_menu_demo y cargar_mesas_demo.")
            return

        self._clientes()
        self._cuentas_abiertas(platos, mesas)
        self._comandas(platos, mesas)
        self._turnos_cerrados()
        self._resumen()

    # ------------------------------------------------------------------

    def _limpiar(self):
        """Solo lo que este comando creo: se reconoce por la marca."""
        with transaction.atomic():
            pedidos = Pedido.objects.filter(nombre_cliente__contains="") \
                .filter(detalles__observacion__contains=MARCA).distinct()
            cuentas = list(Cuenta.objects.filter(pedidos__in=pedidos).values_list("id", flat=True))
            Comanda.objects.filter(pedido__in=pedidos).delete()
            pedidos.delete()
            Cuenta.objects.filter(id__in=cuentas, estado=Cuenta.ABIERTA).delete()
            MovimientoCaja.objects.filter(descripcion__contains=MARCA).delete()
            Turno.objects.filter(observacion_apertura__contains=MARCA).delete()
            Cliente.objects.filter(telefono__in=[c[0] for c in CLIENTES]).delete()
        self.stdout.write("Datos de demostracion anteriores borrados.")

    def _clientes(self):
        for telefono, nombre, direccion, observaciones in CLIENTES:
            cliente, _, _ = reconocer_o_crear(telefono, nombre, direccion)
            if cliente and observaciones and not cliente.observaciones:
                cliente.observaciones = observaciones
                cliente.save(update_fields=["observaciones", "actualizado"])
        self.stdout.write(f"Clientes: {Cliente.objects.count()}")

    def _cuentas_abiertas(self, platos, mesas):
        """Cuentas por cobrar: lo servido y no pagado."""
        if Cuenta.objects.filter(estado=Cuenta.ABIERTA).count() >= 2:
            return
        mesero = self._usuario("mesero")
        for i, (nombre, items) in enumerate(MESAS_CON_CUENTA):
            mesa = mesas[i % len(mesas)]
            cuenta = Cuenta.objects.create(mesa=mesa)
            pedido = Pedido.objects.create(
                mesa=mesa, cuenta=cuenta, mesero=mesero, codigo_qr=_codigo(),
                nombre_cliente=nombre, estado=Pedido.ENTREGADO)
            for idx, cantidad, obs in items:
                plato = platos[idx % len(platos)]
                pedido.detalles.create(
                    plato=plato, cantidad=cantidad,
                    nombre_congelado=plato.nombre, precio_congelado=plato.precio,
                    observacion=f"{obs} {MARCA}".strip())
        self.stdout.write(f"Cuentas abiertas: {Cuenta.objects.filter(estado=Cuenta.ABIERTA).count()}")

    def _comandas(self, platos, mesas):
        """
        El tablero de cocina: comandas en los tres estados.

        Van como DOMICILIOS, no en mesa, por dos razones: la restriccion
        `una_cuenta_abierta_por_mesa` ya tiene ocupadas las mesas con las
        cuentas por cobrar, y ademas asi se prueba como se ve un domicilio en
        el tablero, que es el caso que nadie mira.
        """
        if Comanda.objects.exclude(estado=Comanda.LISTA).count() >= 3:
            return
        mesero = self._usuario("mesero")
        estados = [Comanda.PENDIENTE, Comanda.EN_PREPARACION, Comanda.PENDIENTE]
        for i, estado in enumerate(estados):
            cuenta = Cuenta.objects.create(es_domicilio=True)
            pedido = Pedido.objects.create(
                cuenta=cuenta, mesero=mesero, codigo_qr=_codigo(), es_domicilio=True,
                nombre_cliente="Cumpleanos de Maria Fernanda (mesa larga)",
                estado=Pedido.PENDIENTE)
            for j in range(3):
                plato = platos[(i + j) % len(platos)]
                pedido.detalles.create(
                    plato=plato, cantidad=j + 1,
                    nombre_congelado=plato.nombre, precio_congelado=plato.precio,
                    observacion=f"Sin sal y con la salsa aparte, por favor {MARCA}" if j == 0 else MARCA)
            estacion = platos[i % len(platos)].categoria.estacion
            Comanda.objects.create(
                pedido=pedido, estacion=estacion, estado=estado,
                en_preparacion_desde=timezone.now() if estado == Comanda.EN_PREPARACION else None)
        self.stdout.write(f"Comandas pendientes: {Comanda.objects.exclude(estado=Comanda.LISTA).count()}")

    def _turnos_cerrados(self):
        """El historial de turnos — la unica pantalla con tabla."""
        if Turno.objects.filter(estado=Turno.CERRADO).count() >= 3:
            return
        efectivo = Caja.objects.filter(tipo=Caja.EFECTIVO).first() or Caja.objects.first()
        for nombre in ("ana", "bryam", "carla"):
            usuario = User.objects.filter(username=nombre).first() or self._usuario("mesero")
            if Turno.objects.filter(responsable=usuario, estado=Turno.ABIERTO).exists():
                continue
            turno = abrir_turno(usuario, fondos={efectivo.id: 50_000},
                                observacion=f"Apertura de prueba {MARCA}")
            # Contado distinto del esperado en uno, para ver el descuadre.
            contado = 50_000 if nombre != "carla" else 42_000
            cerrar_turno(turno, efectivo_contado=contado, autor=usuario,
                         observacion=f"Cierre de prueba {MARCA}")
        self.stdout.write(f"Turnos cerrados: {Turno.objects.filter(estado=Turno.CERRADO).count()}")

    def _usuario(self, rol):
        u = User.objects.filter(groups__name=rol, is_active=True).first()
        if u:
            return u
        u = User.objects.create_user(f"{rol}_demo", password="demo12345")
        u.groups.add(Group.objects.get_or_create(name=rol)[0])
        return u

    def _resumen(self):
        self.stdout.write(self.style.SUCCESS(
            f"\nListo. Clientes {Cliente.objects.count()} · "
            f"cuentas abiertas {Cuenta.objects.filter(estado=Cuenta.ABIERTA).count()} · "
            f"comandas activas {Comanda.objects.exclude(estado=Comanda.LISTA).count()} · "
            f"turnos cerrados {Turno.objects.filter(estado=Turno.CERRADO).count()}"))
