from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Terra — Administración"
admin.site.site_title = "Terra"
admin.site.index_title = "Configuración del sitio"

urlpatterns = [
    # Django es solo API y permisos (ADR-006). El admin de Django se deja
    # disponible como herramienta de depuración de bajo nivel — nada del
    # sistema se gestiona desde aquí; toda la gestión real es el panel Vue
    # consumiendo /api/.
    path("admin/", admin.site.urls),
    path("api/", include("nucleo.api_router")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
