from django.db import migrations

# SPEC-023, revisado 2026-09-16: la tarjeta de promo del cliente dejó de ir en
# una franja y ahora lleva una insignia y un enlace propios. Sus textos salen
# de la configuración, como todo texto de la página pública.
PARAMETROS = [
    ("texto-insignia-promo", "Insignia de las promociones", "Promo",
     "Sale sobre la foto de cada promoción en el menú"),
    ("texto-ver-promo", "Enlace al detalle de una promo", "Ver qué incluye",
     "Abre la lista de lo que incluye la promoción"),
]


def crear(apps, schema_editor):
    Parametro = apps.get_model("configuracion", "Parametro")
    for orden, (clave, etiqueta, valor, ayuda) in enumerate(PARAMETROS, 210):
        Parametro.objects.get_or_create(
            clave=clave,
            defaults={"etiqueta": etiqueta, "grupo": "identidad", "tipo": "texto",
                      "valor": valor, "ayuda": ayuda, "orden": orden},
        )


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0007_grupo_cobro")]

    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]
