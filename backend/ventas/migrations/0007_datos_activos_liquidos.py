"""
Datos de arranque para SPEC-020.

Dos cosas que el esquema solo no puede hacer:

1. **Marcar cual caja es efectivo.** El campo nace con `banco` por defecto,
   que es lo correcto para Nequi, Daviplata y el datafono. Pero la caja de
   efectivo si existe y hay que reconocerla, o el cierre de turno no sabria
   de donde retirar la plata.

2. **Sembrar las categorias de gasto.** Arrancan pobladas a proposito: una
   lista vacia obliga a que alguien la llene antes de poder registrar el
   primer gasto, y lo que pasa entonces es que el gasto no se registra.
"""

from django.db import migrations

CATEGORIAS = [
    "Nomina",
    "Insumos",
    "Servicios publicos",
    "Arriendo",
    "Domiciliario",
    "Mantenimiento",
    "Otros",
]


def poblar(apps, schema_editor):
    Caja = apps.get_model("ventas", "Caja")
    CategoriaGasto = apps.get_model("ventas", "CategoriaGasto")

    # `icontains` y no una comparacion exacta: la caja puede llamarse
    # "Efectivo", "EFECTIVO" o "Efectivo caja 1" segun el restaurante.
    Caja.objects.filter(nombre__icontains="efectivo").update(tipo="efectivo")

    for orden, nombre in enumerate(CATEGORIAS):
        CategoriaGasto.objects.get_or_create(
            nombre=nombre, defaults={"orden": orden})


def despoblar(apps, schema_editor):
    """
    Solo quita las categorias que nadie uso. Una con gastos registrados se
    queda: borrarla dejaria movimientos historicos sin explicacion, y eso es
    justo lo que `PROTECT` existe para impedir.
    """
    CategoriaGasto = apps.get_model("ventas", "CategoriaGasto")
    CategoriaGasto.objects.filter(
        nombre__in=CATEGORIAS, movimientos__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0006_categoriagasto_caja_tipo_turno_base_dejada_and_more"),
    ]

    operations = [
        migrations.RunPython(poblar, despoblar),
    ]
