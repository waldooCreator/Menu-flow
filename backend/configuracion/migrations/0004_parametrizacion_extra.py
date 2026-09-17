from django.db import migrations


def crear_parametros(apps, schema_editor):
    Parametro = apps.get_model("configuracion", "Parametro")
    valores = [
        ("moneda", "Moneda", "operacion", "COP", "Codigo ISO 4217, p.ej. COP, USD o MXN"),
        ("locale", "Formato regional", "operacion", "es-CO", "Locale Intl, p.ej. es-CO o en-US"),
        ("qr-vigencia-horas", "Vigencia del QR de pedido (horas)", "operacion", "6", "Tiempo antes de exigir un QR nuevo"),
        ("umbral-cronometro-amarillo", "Cronometro: umbral amarillo (minutos)", "operacion", "10", "Desde cuando una comanda pasa a amarillo"),
        ("umbral-cronometro-rojo", "Cronometro: umbral rojo (minutos)", "operacion", "20", "Desde cuando una comanda pasa a rojo"),
        ("etiqueta-encuentranos", "Titulo de ubicacion", "identidad", "Encuéntranos", "Titulo de la seccion de ubicacion"),
        ("etiqueta-visitanos", "Etiqueta de ubicacion", "identidad", "Visítanos", "Texto pequeño sobre el titulo de ubicacion"),
        ("etiqueta-direccion", "Titulo de direccion", "identidad", "Dirección", "Titulo del bloque de direccion"),
        ("etiqueta-horario", "Titulo de horario", "identidad", "Horario", "Titulo del bloque de horario"),
        ("etiqueta-contacto", "Titulo de contacto", "identidad", "Contacto", "Titulo del bloque de contacto"),
        ("etiqueta-como-llegar", "Titulo de mapa", "identidad", "Cómo llegar", "Titulo del bloque del mapa"),
        ("texto-plato-agotado", "Texto de plato agotado", "identidad", "Agotado hoy", "Etiqueta visible sobre platos no disponibles"),
        ("texto-pie-sitio", "Texto del pie del sitio", "identidad", "", "Si se deja vacío se muestra solo el nombre del restaurante"),
    ]
    for orden, (clave, etiqueta, grupo, valor, ayuda) in enumerate(valores, 100):
        Parametro.objects.get_or_create(
            clave=clave,
            defaults={
                "etiqueta": etiqueta, "grupo": grupo, "tipo": "texto",
                "valor": valor, "ayuda": ayuda, "orden": orden,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0003_tiquete")]

    operations = [migrations.RunPython(crear_parametros, migrations.RunPython.noop)]
