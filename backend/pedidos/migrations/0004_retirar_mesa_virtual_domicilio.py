"""
Retira la mesa virtual "Domicilio" del salón (SPEC-002 / SPEC-012).

Era un parche: `Pedido.mesa` era obligatorio, así que un pedido a distancia
tenía que anclarse en *alguna* mesa. Con la vista de salón esa fila
aparecería como una mesa más, y alguien tendría que "liberarla".

No se BORRA: hay pedidos históricos que la referencian con `PROTECT`, y
borrarla reescribiría el pasado — justo lo que prohíbe la Regla 1 de
SPEC-008. Se desactiva, que la saca del salón y de la lista de mesas sin
tocar un solo pedido.

Los pedidos viejos que apuntan a ella se marcan `es_domicilio=True`, para
que sigan contando como domicilios ahora que la marca vive en el pedido.
"""

from django.db import migrations

CODIGO_MESA_VIRTUAL = "domicilio"


def retirar(apps, schema_editor):
    Mesa = apps.get_model("pedidos", "Mesa")
    Pedido = apps.get_model("pedidos", "Pedido")

    mesa = Mesa.objects.filter(codigo=CODIGO_MESA_VIRTUAL).first()
    if mesa is None:
        return

    # Los pedidos que la usaban eran domicilios: se les pone la marca nueva.
    Pedido.objects.filter(mesa=mesa).update(es_domicilio=True)

    mesa.activa = False
    mesa.save(update_fields=["activa"])


def revertir(apps, schema_editor):
    """Reactivarla es suficiente para volver atrás; la marca no estorba."""
    Mesa = apps.get_model("pedidos", "Mesa")
    Mesa.objects.filter(codigo=CODIGO_MESA_VIRTUAL).update(activa=True)


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0003_mesa_estado_mesa_estado_desde_pedido_es_domicilio_and_more"),
    ]

    operations = [
        migrations.RunPython(retirar, revertir),
    ]
