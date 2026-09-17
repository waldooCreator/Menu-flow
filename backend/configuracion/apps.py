from django.apps import AppConfig


class ConfiguracionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "configuracion"
    verbose_name = "Configuración del sitio"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from .helpers import invalidar_cache_configuracion
        from .models import Parametro

        post_save.connect(invalidar_cache_configuracion, sender=Parametro)
        post_delete.connect(invalidar_cache_configuracion, sender=Parametro)
