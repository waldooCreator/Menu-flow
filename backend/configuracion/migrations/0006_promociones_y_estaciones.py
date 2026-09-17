from django.db import migrations

# SPEC-023. `get_or_create` y no `update_or_create`: si el restaurante ya
# cambió uno de estos textos, correr la migración no debe pisarlo.
PARAMETROS = [
    ("estaciones-unificadas", "Unificar estaciones", "operacion", "booleano", "no",
     "Si: todo llega a la estación por defecto, bebidas incluidas. No: cada plato va a la estación de su categoría"),
    ("titulo-promociones", "Título de la sección de promociones", "identidad", "texto", "Promociones",
     "Encabeza la sección que aparece de primera en el menú"),
    ("texto-promo-incluye", "Texto antes de lo que incluye una promo", "identidad", "texto", "Incluye",
     "Se muestra al abrir el detalle de una promoción"),
    ("texto-promo-hasta", "Texto de la fecha de fin de una promo", "identidad", "texto", "Válida hasta",
     "Seguido de la fecha u hora en que termina"),
]


def crear(apps, schema_editor):
    Parametro = apps.get_model("configuracion", "Parametro")
    for orden, (clave, etiqueta, grupo, tipo, valor, ayuda) in enumerate(PARAMETROS, 200):
        Parametro.objects.get_or_create(
            clave=clave,
            defaults={"etiqueta": etiqueta, "grupo": grupo, "tipo": tipo,
                      "valor": valor, "ayuda": ayuda, "orden": orden},
        )


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0005_alter_parametro_grupo")]

    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]
