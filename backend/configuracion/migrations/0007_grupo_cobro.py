from django.db import migrations, models

# SPEC-014, revisado 2026-09-16. Quién cobra, propina e impuesto estaban en el
# grupo "Contacto": el autor no encontraba cómo decidir si solo caja cobra.
# Se mueven a un grupo propio, y "meseros-pueden-cobrar" pasa a ser sí/no
# elegible en vez de texto escrito a mano.

SI = ("si", "sí", "true", "1", "verdadero")
AYUDA = "Sí: cobran caja, administrador y meseros. No: solo caja y administrador"


def mover_a_cobro(apps, schema_editor):
    Parametro = apps.get_model("configuracion", "Parametro")
    Parametro.objects.filter(
        clave__in=["propina-porcentaje", "impuesto-porcentaje"],
    ).update(grupo="cobro")

    param = Parametro.objects.filter(clave="meseros-pueden-cobrar").first()
    if param is None:
        return
    # Se conserva lo que el restaurante ya tenía. Un valor vacío o raro se
    # lee como "sí", igual que lo leía el servidor antes (arranca encendido).
    valor = (param.valor or "").strip().lower()
    param.valor = "no" if valor in ("no", "false", "0") else "si"
    param.tipo = "booleano"
    param.grupo = "cobro"
    param.etiqueta = "Los meseros también pueden cobrar"
    param.ayuda = AYUDA
    param.save()


def devolver_a_contacto(apps, schema_editor):
    Parametro = apps.get_model("configuracion", "Parametro")
    Parametro.objects.filter(
        clave__in=["propina-porcentaje", "impuesto-porcentaje"],
    ).update(grupo="contacto")
    Parametro.objects.filter(clave="meseros-pueden-cobrar").update(
        grupo="contacto", tipo="texto", etiqueta="Los meseros pueden cobrar")


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0006_promociones_y_estaciones")]

    operations = [
        migrations.AlterField(
            model_name="parametro",
            name="grupo",
            field=models.CharField(
                choices=[
                    ("identidad", "Identidad visual"),
                    ("hero", "Portada (hero)"),
                    ("contacto", "Contacto"),
                    ("horario", "Horario"),
                    ("galeria", "Galería del local"),
                    ("decoracion", "Decoración del menú"),
                    ("operacion", "Operación"),
                    ("cobro", "Cobro"),
                ],
                default="identidad",
                max_length=30,
            ),
        ),
        migrations.RunPython(mover_a_cobro, devolver_a_contacto),
    ]
