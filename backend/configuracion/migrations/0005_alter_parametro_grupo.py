from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0004_parametrizacion_extra")]

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
                ],
                default="identidad",
                max_length=30,
            ),
        ),
    ]
