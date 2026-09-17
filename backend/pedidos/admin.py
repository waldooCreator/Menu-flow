from django.contrib import admin

from .models import DetallePedido, Mesa, Pedido

# Registro mínimo, solo para depuración de bajo nivel (ADR-006): nada del
# sistema se gestiona desde aquí, es el panel Vue quien lo hace.


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "activa")


class DetalleInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ("plato", "nombre_congelado", "precio_congelado", "cantidad", "observacion")


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "mesa", "mesero", "estado", "creado")
    list_filter = ("estado", "mesa")
    inlines = [DetalleInline]
    readonly_fields = ("codigo_qr", "creado")
