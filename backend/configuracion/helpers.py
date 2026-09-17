"""
Acceso de lectura a la configuración, cacheado en memoria.

Este es el punto de entrada que va a usar el resto del sistema (la plantilla
del cliente, la futura API para Vue): `config("color-primario")`, nunca una
consulta directa a Parametro desde otro lado del código.
"""

from django.core.cache import cache

from .models import Parametro

CLAVE_CACHE = "configuracion:todo"


def obtener_configuracion():
    """
    Devuelve {clave: valor_resuelto} de todos los parámetros.

    TTL corto a propósito, no `timeout=None`: el caché por defecto es de
    memoria LOCAL DE PROCESO, y la invalidación por señal solo alcanza al
    proceso donde ocurrió el guardado. Un cambio hecho desde un comando de
    management (o desde otro worker, en producción con varios procesos)
    jamás invalidaría el caché del servidor — con TTL infinito, el servidor
    serviría configuración vieja para siempre. Con 60s, converge solo.
    """
    datos = cache.get(CLAVE_CACHE)
    if datos is None:
        datos = {p.clave: p.valor_resuelto() for p in Parametro.objects.all()}
        cache.set(CLAVE_CACHE, datos, timeout=60)
    return datos


def config(clave, por_defecto=""):
    return obtener_configuracion().get(clave, por_defecto)


def invalidar_cache_configuracion(**kwargs):
    """Conectada a post_save/post_delete de Parametro desde apps.py.ready()."""
    cache.delete(CLAVE_CACHE)
