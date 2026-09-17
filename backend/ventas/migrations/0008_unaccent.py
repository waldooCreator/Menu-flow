from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """
    SPEC-024: buscar "cafe" en el libro debe encontrar "Café". La extensión
    `unaccent` de PostgreSQL lo resuelve en la base, sin traer filas a Python.
    Requiere que el usuario de la base pueda crear extensiones (lo puede en el
    Postgres de desarrollo; en producción, anotarlo en la spec de despliegue).
    """

    dependencies = [("ventas", "0007_datos_activos_liquidos")]

    operations = [UnaccentExtension()]
