from django.contrib import admin

from .models import Categoria, ComponentePromocion, Etiqueta, ObservacionRapida, Plato


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "cantidad_platos")
    list_editable = ("orden",)
    ordering = ("orden", "nombre")

    @admin.display(description="Platos")
    def cantidad_platos(self, obj):
        return obj.platos.count()


@admin.register(Etiqueta)
class EtiquetaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug")
    prepopulated_fields = {"slug": ("nombre",)}


class ComponentePromocionInline(admin.TabularInline):
    model = ComponentePromocion
    extra = 0


class PlatoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "categoria", "precio", "disponible", "orden")
    list_filter = ("tipo", "categoria", "disponible", "etiquetas")
    list_editable = ("precio", "disponible", "orden")
    search_fields = ("nombre", "descripcion")
    filter_horizontal = ("etiquetas",)
    inlines = [ComponentePromocionInline]
    fields = (
        "tipo", "categoria", "nombre", "descripcion", "precio", "foto",
        "disponible", "alergenos", "estadisticas", "etiquetas", "orden",
        "activa", "vigente_desde", "vigente_hasta", "dias_semana", "hora_inicio", "hora_fin",
    )


admin.site.register(Plato, PlatoAdmin)


@admin.register(ObservacionRapida)
class ObservacionRapidaAdmin(admin.ModelAdmin):
    list_display = ("texto", "orden")
    list_editable = ("orden",)
