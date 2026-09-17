from django.contrib import admin

from .models import Comanda, Estacion

# Registro mínimo, solo para depuración de bajo nivel (ADR-006).


@admin.register(Estacion)
class EstacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "por_defecto")


@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "estacion", "estado", "creada")
    list_filter = ("estacion", "estado")
