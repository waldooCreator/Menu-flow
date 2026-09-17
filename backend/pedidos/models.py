from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from menu.models import Plato


def _codigo_mesa_default():
    # Opaco a propósito (SPEC-001): nunca "1", "2", "3", para que no se
    # pueda adivinar ni enumerar mesas ajenas.
    return get_random_string(8).lower()


class Mesa(models.Model):
    """
    Mesa fisica del salon. El estado de ocupacion (SPEC-012) es un dato
    GUARDADO, no derivado de los pedidos: si se dedujera, "liberar" tendria
    que ir a cerrar pedidos, y ahi es donde el sistema se trabaria. La regla
    de oro de SPEC-012 es que el mesero manda y el sistema nunca espera.
    """

    LIBRE = "libre"
    APARTADA = "apartada"      # sentados, sin pedido todavia
    OCUPADA = "ocupada"        # con pedido enviado a cocina

    ESTADOS = [
        (LIBRE, "Libre"),
        (APARTADA, "Apartada"),
        (OCUPADA, "Ocupada"),
    ]

    nombre = models.CharField(max_length=40, help_text='p.ej. "Mesa 12"')
    codigo = models.SlugField(max_length=20, unique=True, default=_codigo_mesa_default)
    activa = models.BooleanField(default=True)

    estado = models.CharField(max_length=12, choices=ESTADOS, default=LIBRE)
    # Cuando cambio el estado. Sirve para el tiempo transcurrido en el salon
    # y, mas adelante, para la rotacion de mesas (SPEC-008).
    estado_desde = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def cambiar_estado(self, nuevo):
        """
        Unico camino para mover el estado. No valida transiciones a
        proposito: el mesero puede pasar de cualquier estado a cualquier
        otro (SPEC-012, "el mesero manda"). Lo que si hace es sellar cuando.
        """
        self.estado = nuevo
        self.estado_desde = timezone.now()
        self.save(update_fields=["estado", "estado_desde"])


class Pedido(models.Model):
    PENDIENTE = "pendiente"
    EN_PREPARACION = "en_preparacion"
    LISTO = "listo"
    ENTREGADO = "entregado"
    ANULADO = "anulado"

    ESTADOS = [
        (PENDIENTE, "Pendiente"),
        (EN_PREPARACION, "En preparación"),
        (LISTO, "Listo"),
        (ENTREGADO, "Entregado"),
        (ANULADO, "Anulado"),
    ]

    # Opcional desde 2026-08-26 (SPEC-002): un domicilio NO tiene mesa. Antes
    # se anclaba en una mesa virtual "Domicilio", que con el salon (SPEC-012)
    # apareceria como una mesa mas que alguien tendria que liberar. Sin mesa,
    # el domicilio no toca el salon POR CONSTRUCCION, no por un filtro que
    # alguien pueda olvidar.
    mesa = models.ForeignKey(
        Mesa, on_delete=models.PROTECT, related_name="pedidos", null=True, blank=True,
    )
    es_domicilio = models.BooleanField(
        default=False,
        help_text="Pedido a distancia: sin mesa. La direccion vive en el chat de WhatsApp (SPEC-002)",
    )
    # A que cuenta pertenece (SPEC-013). Una visita tiene MUCHOS pedidos y
    # UNA cuenta: es lo que permite responder "cuanto va la Mesa 5".
    # Opcional solo por los pedidos anteriores a esta spec.
    cuenta = models.ForeignKey(
        "ventas.Cuenta", on_delete=models.PROTECT, related_name="pedidos",
        null=True, blank=True,
    )
    mesero = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos_confirmados",
        help_text="Quien confirmó el pedido (ADR-002): toda venta queda amarrada a un usuario real",
    )
    nombre_cliente = models.CharField(max_length=80, blank=True)

    # Deriva de un hash del texto firmado del QR — anti-duplicado sin
    # necesidad de un campo aleatorio aparte en el payload (SPEC-002).
    codigo_qr = models.CharField(max_length=16, unique=True)

    comentario = models.CharField(max_length=200, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE)
    motivo_anulacion = models.CharField(max_length=200, blank=True)

    creado = models.DateTimeField(auto_now_add=True)

    # Quien entrego y cuando (SPEC-012). Se registra porque entregar dejo de
    # ser exclusivo de quien tomo el pedido: en un domicilio, quien recibe al
    # domiciliario rara vez es el mismo.
    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="pedidos_entregados", null=True, blank=True,
    )
    entregado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado"]

    @property
    def destino(self):
        """
        A dónde va este pedido, SIEMPRE como texto (SPEC-011).

        Antes la estación lo deducía caminando hasta `pedido.mesa.nombre` al
        momento de pintar, y eso fallaba de dos formas: un domicilio no tiene
        mesa (el campo desaparecía del JSON y la tarjeta salía en blanco), y
        una mesa liberada seguía mostrando su nombre aunque ya hubiera otra
        gente sentada ahí.
        """
        if self.es_domicilio:
            return "Domicilio"
        return self.mesa.nombre if self.mesa else "Sin mesa"

    def __str__(self):
        return f"Pedido #{self.id} — {self.destino}"


class DetallePedido(models.Model):
    """
    Precio y nombre CONGELADOS al momento de la venta (regla 1 de
    SPEC-008): si el menú cambia después, este renglón no se altera.
    """

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    plato = models.ForeignKey(Plato, on_delete=models.PROTECT, related_name="+")
    nombre_congelado = models.CharField(max_length=140)
    precio_congelado = models.PositiveIntegerField()
    cantidad = models.PositiveIntegerField()
    observacion = models.CharField(max_length=200, blank=True)

    # Lo que incluía la promoción al venderla: [[cantidad, nombre], ...]
    # (SPEC-023). Congelado por la misma razón que el nombre y el precio: si
    # mañana cambian el postre del combo, el pedido de hoy sigue diciendo lo
    # que se vendió hoy. Vacío en un plato normal.
    desglose_congelado = models.JSONField(default=list, blank=True)

    # A qué comanda (estación) quedó asignado este renglón — lo asigna el
    # ruteador al confirmar (SPEC-005), no se elige a mano.
    comanda = models.ForeignKey(
        "estaciones.Comanda", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="detalles",
    )

    def __str__(self):
        return f"{self.cantidad}× {self.nombre_congelado}"


class Novedad(models.Model):
    """
    Un cambio sobre un pedido YA enviado a cocina (SPEC-011).

    **De solo inserción. Nunca se actualiza ni se borra** (ADR-007). Editar
    con un UPDATE sobre `DetallePedido` destruiría el historial: se perdería
    para siempre que el cliente había pedido 2, y los reportes pasarían a
    decir "a qué quedó editado" en vez de "qué se vendió". Y fallaría en
    silencio — nada se rompe, solo los reportes mienten.

    `DetallePedido` sí refleja el estado actual (lo que finalmente se sirvió,
    que es la venta). La historia de cómo se llegó ahí vive aquí.

    Es además la primera pieza de la Regla 2 de SPEC-008 (auditoría de solo
    inserción), que hasta hoy no tenía ni tabla.
    """

    CAMBIO_DESTINO = "cambio_destino"
    AGREGAR_ITEM = "agregar_item"
    QUITAR_ITEM = "quitar_item"
    CAMBIAR_CANTIDAD = "cambiar_cantidad"
    CAMBIAR_OBSERVACION = "cambiar_observacion"

    TIPOS = [
        (CAMBIO_DESTINO, "Cambio de destino"),
        (AGREGAR_ITEM, "Plato agregado"),
        (QUITAR_ITEM, "Plato quitado"),
        (CAMBIAR_CANTIDAD, "Cantidad cambiada"),
        (CAMBIAR_OBSERVACION, "Observación cambiada"),
    ]

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="novedades")
    tipo = models.CharField(max_length=24, choices=TIPOS)

    # Texto listo para mostrarle a la estación: "Mesa 1 → Mesa 2".
    # Se guarda ya redactado porque describe un hecho pasado: si mañana la
    # mesa cambia de nombre, lo que ocurrió esa noche no cambia.
    descripcion = models.CharField(max_length=200)
    antes = models.CharField(max_length=140, blank=True)
    despues = models.CharField(max_length=140, blank=True)

    # A qué estación le importa. Vacío = a todas (p.ej. un cambio de destino).
    estacion = models.ForeignKey(
        "estaciones.Estacion", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="novedades",
    )

    # Constancia de que el plato ya estaba hecho o en curso cuando se cambió:
    # quitar un plato cocinado no lo descocina (SPEC-011, regla 3). Valorar
    # esa merma es trabajo de SPEC-008; aquí solo se garantiza el dato.
    comanda_estaba = models.CharField(max_length=20, blank=True)

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="novedades",
    )
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creada"]
        verbose_name_plural = "novedades"

    def __str__(self):
        return f"#{self.pedido_id} · {self.get_tipo_display()}: {self.descripcion}"


class Notificacion(models.Model):
    """
    Avisa al mesero que una comanda suya está lista (SPEC-006). Persistida
    a propósito — no vive solo en memoria: si el mesero recarga o pierde
    conexión, el contador sigue ahí.

    Decisión (2026-08-24): una notificación POR CADA comanda lista, no una
    sola al final del pedido completo — ver Preguntas Abiertas.
    """

    mesero = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones",
    )
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="notificaciones")
    comanda = models.ForeignKey(
        "estaciones.Comanda", on_delete=models.CASCADE, related_name="notificaciones",
    )
    mensaje = models.CharField(max_length=140)
    leida = models.BooleanField(default=False)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada"]

    def __str__(self):
        return self.mensaje
