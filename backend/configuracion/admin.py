from django.contrib import admin

from .models import Parametro


@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ("etiqueta", "clave", "grupo", "tipo", "vista_previa", "orden")
    list_filter = ("grupo", "tipo")
    list_editable = ("orden",)
    search_fields = ("clave", "etiqueta")
    ordering = ("grupo", "orden", "clave")
    fields = ("etiqueta", "clave", "grupo", "tipo", "valor", "imagen", "ayuda", "orden")

    @admin.display(description="Valor")
    def vista_previa(self, obj):
        if obj.tipo == Parametro.IMAGEN:
            return obj.imagen.name if obj.imagen else "(sin imagen)"
        if obj.tipo == Parametro.COLOR:
            return obj.valor
        texto = obj.valor or ""
        return texto if len(texto) <= 50 else texto[:47] + "…"
