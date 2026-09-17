from rest_framework import serializers

from .models import Comanda, Estacion


class EstacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estacion
        fields = ["id", "nombre", "orden", "por_defecto"]


class DetalleComandaSerializer(serializers.Serializer):
    """Lo que ve la estación de cada renglón — nunca el pedido completo (SPEC-005)."""

    nombre = serializers.CharField(source="nombre_congelado")
    cantidad = serializers.IntegerField()
    observacion = serializers.CharField()
    plato_id = serializers.IntegerField(read_only=True)
    # Lo que incluía la promo al venderla (SPEC-023). Vacío en un plato
    # normal; la tarjeta lo pinta debajo del nombre del combo.
    desglose = serializers.ListField(source="desglose_congelado", read_only=True)


class ComandaSerializer(serializers.ModelSerializer):
    # `pedido.destino` y no `pedido.mesa.nombre` (SPEC-011): con `source`
    # apuntando a la mesa, un domicilio (que no tiene mesa) hacía que DRF
    # BORRARA el campo del JSON — la tarjeta salía con el título en blanco.
    destino = serializers.CharField(source="pedido.destino", read_only=True)
    # Se conserva `mesa` por compatibilidad con lo que ya consumía el tablero.
    mesa = serializers.CharField(source="pedido.destino", read_only=True)
    # El tablero oculta las comandas de pedidos ya entregados: sin esto, la
    # columna "Listas" acumularía historia para siempre.
    pedido_estado = serializers.CharField(source="pedido.estado", read_only=True)
    detalles = DetalleComandaSerializer(many=True, read_only=True)
    novedades = serializers.SerializerMethodField()
    # Con estaciones unificadas el tablero junta todas: la tarjeta dice de
    # cuál viene cada comanda para no perder ese dato (SPEC-023, sección 7).
    estacion_nombre = serializers.CharField(source="estacion.nombre", read_only=True)
    estacion_por_defecto = serializers.BooleanField(source="estacion.por_defecto", read_only=True)

    def get_novedades(self, comanda):
        """
        Lo que esta estación todavía no ha marcado como visto (SPEC-011).
        Mientras haya algo aquí, su tarjeta va en rojo — y muestra QUÉ
        cambió, no que algo cambió.
        """
        from pedidos.novedades import novedades_sin_ver

        return [
            {"id": n.id, "tipo": n.tipo, "descripcion": n.descripcion, "creada": n.creada}
            for n in novedades_sin_ver(comanda)
        ]

    class Meta:
        model = Comanda
        fields = [
            "id", "pedido", "pedido_estado", "mesa", "destino", "estacion",
            "estacion_nombre", "estacion_por_defecto", "estado",
            "creada", "en_preparacion_desde", "lista_desde", "detalles", "novedades",
        ]
