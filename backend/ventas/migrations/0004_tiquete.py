from django.db import migrations, models
from django.db.models import Q


def prefijos_iniciales(apps, schema_editor):
    Caja = apps.get_model("ventas", "Caja")
    prefijos = {
        "Efectivo": "Ef",
        "Nequi": "Ne",
        "Daviplata": "Da",
        "Bancolombia": "Ba",
        "Datafono": "Df",
    }
    for nombre, prefijo in prefijos.items():
        Caja.objects.filter(nombre=nombre, prefijo="").update(prefijo=prefijo)


class Migration(migrations.Migration):
    dependencies = [("ventas", "0003_turno_cerrado_por")]

    operations = [
        migrations.AddField(
            model_name="caja",
            name="prefijo",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Sigla del consecutivo del tiquete, p.ej. Ef",
                max_length=4,
            ),
        ),
        migrations.AddField(
            model_name="cuenta",
            name="tiquete_anio",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="cuenta",
            name="tiquete_numero",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="cuenta",
            constraint=models.UniqueConstraint(
                condition=Q(
                    ("medio_pago__isnull", False),
                    ("tiquete_anio__isnull", False),
                    ("tiquete_numero__isnull", False),
                ),
                fields=("medio_pago", "tiquete_anio", "tiquete_numero"),
                name="tiquete_unico_por_medio_anio_numero",
            ),
        ),
        migrations.RunPython(prefijos_iniciales, migrations.RunPython.noop),
    ]
