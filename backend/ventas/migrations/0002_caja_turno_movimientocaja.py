"""
SPEC-014: la caja de fondos, el turno y el libro de movimientos.

Escrita a mano a propósito. `makemigrations` pregunta de forma interactiva
si `MedioPago` se renombró a `Caja`, y `--no-input` responde que NO: eso
generaría un DeleteModel + CreateModel que **borraría la tabla con sus
datos**. Un `RenameModel` explícito conserva las filas y las llaves foráneas.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ventas", "0001_initial"),
    ]

    operations = [
        # Medio de pago y caja son la misma cosa vista en dos momentos: al
        # cobrar se elige, y ahí se acumula el dinero (SPEC-014).
        migrations.RenameModel(old_name="MedioPago", new_name="Caja"),
        migrations.AlterModelOptions(
            name="caja",
            options={
                "ordering": ["orden", "nombre"],
                "verbose_name": "caja",
                "verbose_name_plural": "cajas",
            },
        ),
        migrations.CreateModel(
            name="Turno",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("estado", models.CharField(
                    choices=[("abierto", "Abierto"), ("cerrado", "Cerrado")],
                    default="abierto", max_length=10)),
                ("abierto_en", models.DateTimeField(auto_now_add=True)),
                ("observacion_apertura", models.CharField(blank=True, max_length=200)),
                ("cerrado_en", models.DateTimeField(blank=True, null=True)),
                ("observacion_cierre", models.CharField(blank=True, max_length=200)),
                ("efectivo_contado", models.PositiveIntegerField(blank=True, null=True)),
                ("responsable", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="turnos", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-abierto_en"]},
        ),
        migrations.AddConstraint(
            model_name="turno",
            constraint=models.UniqueConstraint(
                condition=models.Q(("estado", "abierto")),
                fields=("responsable",),
                name="un_turno_abierto_por_persona",
            ),
        ),
        migrations.CreateModel(
            name="MovimientoCaja",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(
                    choices=[("ingreso", "Ingreso"), ("egreso", "Egreso")], max_length=10)),
                ("concepto", models.CharField(
                    choices=[
                        ("venta", "Venta"),
                        ("anulacion", "Anulación de venta"),
                        ("fondo_inicial", "Fondo inicial de turno"),
                        ("traslado", "Traslado entre cajas"),
                        ("otro", "Ingreso o gasto"),
                    ],
                    default="otro", max_length=20)),
                ("monto", models.PositiveIntegerField()),
                ("descripcion", models.CharField(blank=True, max_length=200)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("autor", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="movimientos_caja", to=settings.AUTH_USER_MODEL)),
                ("caja", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="movimientos", to="ventas.caja")),
                ("cuenta", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="movimientos", to="ventas.cuenta")),
                ("turno", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="movimientos", to="ventas.turno")),
            ],
            options={
                "ordering": ["-creado"],
                "verbose_name": "movimiento de caja",
                "verbose_name_plural": "movimientos de caja",
            },
        ),
    ]
