from django.db import migrations


def crear_parametros_tiquete(apps, schema_editor):
    Parametro = apps.get_model("configuracion", "Parametro")
    valores = [
        (
            "nit", "NIT del negocio", "identidad", "texto", "",
            "Identificación que aparece en el tiquete interno",
        ),
        (
            "formato-tiquete", "Formato del tiquete", "identidad", "texto", "rollo",
            "Valores: rollo o carta",
        ),
        (
            "mensaje-pie-tiquete", "Mensaje al pie del tiquete", "identidad", "texto",
            "Gracias por visitarnos", "Texto configurable para el comprobante",
        ),
        (
            "logo-tiquete", "Logo del tiquete", "identidad", "imagen", "",
            "Imagen que aparece en el comprobante de venta",
        ),
    ]
    for orden, (clave, etiqueta, grupo, tipo, valor, ayuda) in enumerate(valores):
        Parametro.objects.get_or_create(
            clave=clave,
            defaults={
                "etiqueta": etiqueta, "grupo": grupo, "tipo": tipo,
                "valor": valor, "ayuda": ayuda, "orden": orden,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0002_alter_parametro_grupo")]

    operations = [
        migrations.RunPython(crear_parametros_tiquete, migrations.RunPython.noop),
    ]
