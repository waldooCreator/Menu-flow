import json

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Categoria, ComponentePromocion, Etiqueta, ObservacionRapida, Plato
from .promociones import estado_promocion


class EtiquetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Etiqueta
        fields = ["id", "nombre", "slug"]
        read_only_fields = ["slug"]


class CategoriaSerializer(serializers.ModelSerializer):
    cantidad_platos = serializers.IntegerField(source="platos.count", read_only=True)
    estacion_nombre = serializers.CharField(source="estacion.nombre", read_only=True, default=None)

    class Meta:
        model = Categoria
        # `estacion` es la base del ruteo (SPEC-005): mover una categoría de
        # cocina a bar debe ser un cambio desde el panel, jamás de código.
        # Faltaba aquí — sin este campo el panel no podía administrarla.
        fields = ["id", "nombre", "orden", "estacion", "estacion_nombre", "cantidad_platos"]


class ObservacionRapidaSerializer(serializers.ModelSerializer):
    # `default=True` explícito, no heredado del modelo: DRF trata un booleano
    # AUSENTE en un envío de formulario como False (regla de las casillas
    # HTML: una casilla sin marcar no se manda). Sin esto, crear una etiqueta
    # sin mencionar `activo` la dejaba nacida desactivada — existía en la base
    # pero no salía en ningún plato, y nada indicaba por qué.
    activo = serializers.BooleanField(default=True)
    # `required=False` explícito: el modelo ya los declara `blank=True`, pero
    # DRF vuelve a marcarlos como requeridos al construir los validadores de
    # unicidad de los `UniqueConstraint` con `condition` — no reconoce que la
    # condición ya cubre el caso vacío. Sin esto, un envío que no menciona
    # `categoria` (o `plato`) rechaza con "este campo es requerido" aunque el
    # dato sea perfectamente válido: general es, precisamente, no tener plato
    # ni categoría.
    # `default=None`, no solo `required=False`: el validador de unicidad que
    # DRF arma a partir del `UniqueConstraint` exige que el campo esté
    # PRESENTE en los datos para poder comparar contra la base — si el
    # cliente omite la clave por completo, sin un default el campo ni
    # siquiera llega a `validated_data`, y el validador lo rechaza con "este
    # campo es requerido" en vez de tratarlo como vacío.
    categoria = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.all(), required=False, allow_null=True, default=None)
    plato = serializers.PrimaryKeyRelatedField(
        queryset=Plato.objects.all(), required=False, allow_null=True, default=None)

    class Meta:
        model = ObservacionRapida
        # plato y categoria vacios = general; solo categoria = por seccion;
        # plato puesto = por ese plato (SPEC-003).
        fields = ["id", "texto", "categoria", "plato", "activo", "orden"]


class ComponentePromocionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentePromocion
        fields = ["id", "cantidad", "nombre", "especificacion"]


class ListaJSONField(serializers.ListField):
    """
    Una lista que también se acepta como texto JSON. Hace falta porque la
    foto del plato viaja en multipart (SPEC-007), y un formulario multipart
    no sabe mandar una lista de objetos: los componentes llegan como texto.
    """

    def get_value(self, dictionary):
        # En multipart DRF buscaría `campo[0]`, `campo[1]`...; aquí llega un
        # solo valor con el JSON completo.
        if hasattr(dictionary, "getlist") and self.field_name in dictionary:
            return dictionary.get(self.field_name)
        return super().get_value(dictionary)

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data or "[]")
            except ValueError:
                raise serializers.ValidationError("No es una lista válida.")
        return super().to_internal_value(data)


class PlatoSerializer(serializers.ModelSerializer):
    """
    Serializador de escritura (admin): recibe `etiquetas` como lista de IDs.

    Una promoción (SPEC-023) llega por el mismo camino, con sus componentes y
    su vigencia: es un tipo de plato, no un recurso aparte.
    """

    componentes = ListaJSONField(
        child=ComponentePromocionSerializer(), required=False, write_only=True)
    dias_semana = ListaJSONField(
        child=serializers.IntegerField(min_value=0, max_value=6), required=False)

    class Meta:
        model = Plato
        fields = [
            "id", "tipo", "categoria", "nombre", "descripcion", "precio", "foto",
            "disponible", "disponible_cambiado_por", "disponible_cambiado_en",
            "alergenos", "estadisticas", "etiquetas", "orden",
            "activa", "vigente_desde", "vigente_hasta", "dias_semana",
            "hora_inicio", "hora_fin", "componentes",
        ]
        read_only_fields = ["disponible_cambiado_por", "disponible_cambiado_en"]

    def validate(self, datos):
        """
        Las reglas de forma de una promoción. La base ya impide lo grave
        (plato sin categoría, franja a medias); aquí se dice en palabras que el
        administrador entienda, antes de llegar a un error de la base.
        """
        instancia = self.instance

        def valor(campo):
            return datos[campo] if campo in datos else getattr(instancia, campo, None)

        if instancia is not None and "tipo" in datos and datos["tipo"] != instancia.tipo:
            raise serializers.ValidationError(
                {"tipo": "Un plato no se puede convertir en promoción ni al revés."})

        if (valor("tipo") or Plato.PLATO) == Plato.PLATO:
            if valor("categoria") is None:
                raise serializers.ValidationError({"categoria": "El plato necesita una categoría."})
            return datos

        # --- Promoción
        datos["categoria"] = None
        sin_componentes = (instancia is None and not datos.get("componentes")) or (
            "componentes" in datos and not datos["componentes"])
        if sin_componentes:
            raise serializers.ValidationError(
                {"componentes": "La promoción necesita al menos un componente."})
        desde, hasta = valor("vigente_desde"), valor("vigente_hasta")
        if desde is None:
            raise serializers.ValidationError({"vigente_desde": "Indica desde qué día vale."})
        if hasta and hasta < desde:
            raise serializers.ValidationError(
                {"vigente_hasta": "La fecha de fin no puede ser antes de la de inicio."})
        if (valor("hora_inicio") is None) != (valor("hora_fin") is None):
            raise serializers.ValidationError(
                {"hora_fin": "Indica las dos horas de la franja, o ninguna."})
        if "dias_semana" in datos:
            if not datos["dias_semana"]:
                raise serializers.ValidationError({"dias_semana": "Elige al menos un día."})
            datos["dias_semana"] = sorted(set(datos["dias_semana"]))
        return datos

    def to_representation(self, plato):
        datos = super().to_representation(plato)
        datos["componentes"] = ComponentePromocionSerializer(plato.componentes.all(), many=True).data
        return datos

    def _guardar_componentes(self, plato, componentes):
        """Se reemplazan completos: el orden en que llegan es el orden en que se muestran."""
        plato.componentes.all().delete()
        ComponentePromocion.objects.bulk_create([
            ComponentePromocion(
                promocion=plato, orden=i, cantidad=c["cantidad"], nombre=c["nombre"],
                especificacion=c.get("especificacion", ""),
            )
            for i, c in enumerate(componentes)
        ])

    @transaction.atomic
    def create(self, validated_data):
        componentes = validated_data.pop("componentes", None)
        plato = super().create(validated_data)
        if plato.es_promocion and componentes:
            self._guardar_componentes(plato, componentes)
        return plato

    @transaction.atomic
    def update(self, instance, validated_data):
        componentes = validated_data.pop("componentes", None)
        disponibilidad_cambio = (
            "disponible" in validated_data
            and validated_data["disponible"] != instance.disponible
        )
        plato = super().update(instance, validated_data)
        if plato.es_promocion and componentes is not None:
            self._guardar_componentes(plato, componentes)
        if disponibilidad_cambio:
            request = self.context.get("request")
            plato.disponible_cambiado_por = request.user if request else None
            plato.disponible_cambiado_en = timezone.now()
            plato.save(update_fields=["disponible_cambiado_por", "disponible_cambiado_en"])
        return plato


class PlatoLecturaSerializer(serializers.ModelSerializer):
    """
    Serializador de lectura (página del cliente): categoría y etiquetas ya
    resueltas por nombre, no solo el ID — así Vue no necesita otra consulta
    para pintar el menú.
    """

    # `default=None`: una promoción no tiene categoría, y sin default DRF
    # BORRA el campo del JSON en vez de mandarlo vacío.
    categoria = serializers.CharField(source="categoria.nombre", read_only=True, default=None)
    categoria_id = serializers.IntegerField(source="categoria.id", read_only=True, default=None)
    observaciones = serializers.SerializerMethodField()
    componentes = ComponentePromocionSerializer(many=True, read_only=True)
    estado_promocion = serializers.SerializerMethodField()

    def get_estado_promocion(self, plato):
        return estado_promocion(plato)

    def get_observaciones(self, plato):
        """
        Las generales MÁS las de su categoría MÁS las suyas, ya combinadas y
        deduplicadas (SPEC-003, tres niveles). Se resuelve aquí para que la
        pantalla no tenga que cruzar tres listas ni saber la regla.

        Las generales y las por-categoría llegan precargadas en el contexto:
        sin eso serían N+1 consultas, una por plato.
        """
        generales = self.context.get("observaciones_generales")
        if generales is None:
            generales = list(
                ObservacionRapida.objects.filter(
                    plato__isnull=True, categoria__isnull=True, activo=True)
            )
        por_categoria = self.context.get("observaciones_por_categoria")
        if por_categoria is None:
            de_categoria = list(
                ObservacionRapida.objects.filter(
                    categoria_id=plato.categoria_id, plato__isnull=True, activo=True)
            )
        else:
            de_categoria = por_categoria.get(plato.categoria_id, [])
        propias = [o for o in plato.observaciones.all() if o.activo and o.plato_id]

        vistas, salida = set(), []
        for o in list(generales) + de_categoria + propias:
            clave = o.texto.strip().lower()
            if clave in vistas:
                continue
            vistas.add(clave)
            nivel = "plato" if o.plato_id else ("categoria" if o.categoria_id else "general")
            salida.append({"id": o.id, "texto": o.texto, "nivel": nivel})
        return salida
    etiquetas = serializers.SlugRelatedField(
        many=True, slug_field="slug", read_only=True,
    )

    class Meta:
        model = Plato
        fields = [
            "id", "tipo", "categoria", "categoria_id", "nombre", "descripcion", "precio",
            "foto", "disponible", "disponible_cambiado_por", "disponible_cambiado_en",
            "alergenos", "estadisticas", "etiquetas", "orden",
            "observaciones",
            "componentes", "estado_promocion", "activa", "vigente_desde", "vigente_hasta",
            "dias_semana", "hora_inicio", "hora_fin",
        ]
        read_only_fields = ["disponible_cambiado_por", "disponible_cambiado_en"]
