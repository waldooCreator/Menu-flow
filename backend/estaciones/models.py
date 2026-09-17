from django.db import models
from django.utils import timezone


class Estacion(models.Model):
    """
    Punto de preparación: cocina, postres, bar (SPEC-005). Configurable,
    no una lista fija — crear una estación nueva es una fila, no código.
    """

    nombre = models.CharField(max_length=60, unique=True)
    orden = models.PositiveIntegerField(default=0)
    por_defecto = models.BooleanField(
        default=False,
        help_text="A dónde caen las categorías sin estación asignada (SPEC-005)",
    )

    class Meta:
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Comanda(models.Model):
    """
    La parte de un pedido que le corresponde a UNA estación. Un pedido con
    items de cocina y de bar produce dos comandas, no una (SPEC-005).
    """

    PENDIENTE = "pendiente"
    EN_PREPARACION = "en_preparacion"
    LISTA = "lista"

    ESTADOS = [
        (PENDIENTE, "Pendiente"),
        (EN_PREPARACION, "En preparación"),
        (LISTA, "Lista"),
    ]

    pedido = models.ForeignKey("pedidos.Pedido", on_delete=models.CASCADE, related_name="comandas")
    estacion = models.ForeignKey(Estacion, on_delete=models.PROTECT, related_name="comandas")
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE)

    # Hasta cuándo esta estación ya vio las novedades de su pedido (SPEC-011).
    # Una marca de tiempo en vez de una tabla de enlace: "hay novedades sin
    # ver" es `novedades.creada > este valor`, y "Visto" es ponerlo en ahora.
    #
    # Poder apagar el aviso es parte del mecanismo, no un adorno: una alerta
    # que nadie puede cerrar termina siendo papel tapiz, y a las dos horas de
    # servicio el rojo deja de significar nada.
    novedades_vistas_hasta = models.DateTimeField(null=True, blank=True)

    # Timestamps para las métricas de ADR-004: cuánto se demora cada estación,
    # y cuánto se demora el mesero en recoger después.
    creada = models.DateTimeField(auto_now_add=True)
    en_preparacion_desde = models.DateTimeField(null=True, blank=True)
    lista_desde = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["creada"]

    def __str__(self):
        return f"Comanda #{self.id} — {self.estacion.nombre} (pedido #{self.pedido_id})"

    def marcar_en_preparacion(self):
        self.estado = self.EN_PREPARACION
        self.en_preparacion_desde = timezone.now()
        self.save(update_fields=["estado", "en_preparacion_desde"])

    def marcar_lista(self):
        self.estado = self.LISTA
        self.lista_desde = timezone.now()
        self.save(update_fields=["estado", "lista_desde"])

    def marcar_novedades_vistas(self):
        self.novedades_vistas_hasta = timezone.now()
        self.save(update_fields=["novedades_vistas_hasta"])

    def reabrir_por_novedad(self):
        """
        Una comanda YA LISTA que recibe una novedad sale de la columna
        "Listas" (SPEC-011). Es el único caso en que una novedad mueve una
        comanda de columna, y tiene motivo: el plato está en la barra con la
        etiqueta equivocada y alguien está a punto de llevarlo. Recolorear
        no alcanza cuando el error ya salió de la cocina.
        """
        if self.estado != self.LISTA:
            return False
        self.estado = self.EN_PREPARACION
        self.lista_desde = None
        self.save(update_fields=["estado", "lista_desde"])
        return True
