from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Categoria(models.Model):
    """
    `estacion` implementa el ruteo de SPEC-005: a qué estación llegan los
    platos de esta categoría. Nula = cae en la estación por defecto.
    """

    nombre = models.CharField(max_length=80, unique=True)
    orden = models.PositiveIntegerField(default=0)
    estacion = models.ForeignKey(
        "estaciones.Estacion", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="categorias",
    )

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Etiqueta(models.Model):
    """P.ej. «vegetariano», «picante». Configurable, no una lista fija."""

    nombre = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True, blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


def todos_los_dias():
    """Lunes (0) a domingo (6). Función y no lista literal: un `default` mutable se compartiría."""
    return list(range(7))


class Plato(models.Model):
    """
    Un plato del menú, o una promoción (SPEC-023).

    La promoción es un TIPO de plato y no un modelo aparte: se vende, se
    congela en el renglón, se agota y entra a los reportes exactamente igual
    que un plato. Un modelo aparte obligaba a duplicar todo ese camino, y un
    combo es, para quien cobra, un producto más con su precio.
    """

    PLATO = "plato"
    PROMOCION = "promocion"
    TIPOS = [(PLATO, "Plato"), (PROMOCION, "Promoción")]

    tipo = models.CharField(max_length=10, choices=TIPOS, default=PLATO)

    # Nula SOLO en promociones: no pertenecen a ninguna sección del menú y su
    # combo entero va a la estación por defecto (SPEC-023). Un plato normal la
    # exige, y lo impone la restricción de abajo, no solo el formulario.
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="platos", null=True, blank=True,
    )
    nombre = models.CharField(max_length=140)
    descripcion = models.TextField(
        blank=True, help_text="Ingredientes completos, no una frase publicitaria (§Sistema de Diseño)",
    )
    precio = models.PositiveIntegerField(help_text="En la unidad menor sin decimales, p.ej. COP")
    foto = models.ImageField(upload_to="platos/", blank=True, null=True)
    disponible = models.BooleanField(default=True)
    disponible_cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="platos_disponibilidad", null=True, blank=True,
    )
    disponible_cambiado_en = models.DateTimeField(null=True, blank=True)
    alergenos = models.CharField(max_length=200, blank=True)

    # [["380", "Cal"], ["4", "Porciones"]] — mismo formato que `data.js`.
    # JSON porque la cantidad y el tipo de métricas varían por plato.
    estadisticas = models.JSONField(blank=True, default=list)

    etiquetas = models.ManyToManyField(Etiqueta, blank=True, related_name="platos")
    orden = models.PositiveIntegerField(default=0)

    # --- Vigencia de una promoción (SPEC-023). En un plato normal no se usan.
    # `activa` es el interruptor para apagarla antes de tiempo; `disponible`
    # sigue siendo "se agotó", igual que en cualquier plato (SPEC-017).
    activa = models.BooleanField(default=True)
    vigente_desde = models.DateField(null=True, blank=True)
    vigente_hasta = models.DateField(
        null=True, blank=True, help_text="Vacío = sin fecha de fin")
    dias_semana = models.JSONField(
        default=todos_los_dias, blank=True, help_text="0 = lunes … 6 = domingo")
    # Las dos vacías = todo el día. Si la hora de fin es menor o igual que la
    # de inicio, la franja cruza la medianoche (ver `menu/promociones.py`).
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Plato"
        verbose_name_plural = "Platos"
        ordering = ["categoria__orden", "orden", "nombre"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(tipo="promocion") | models.Q(categoria__isnull=False),
                name="plato_normal_exige_categoria",
            ),
            models.CheckConstraint(
                check=models.Q(tipo="plato") | models.Q(categoria__isnull=True),
                name="promocion_sin_categoria",
            ),
            models.CheckConstraint(
                check=(models.Q(vigente_hasta__isnull=True) | models.Q(vigente_desde__isnull=True)
                       | models.Q(vigente_hasta__gte=models.F("vigente_desde"))),
                name="promocion_hasta_no_antes_de_desde",
            ),
            models.CheckConstraint(
                check=(models.Q(hora_inicio__isnull=True, hora_fin__isnull=True)
                       | models.Q(hora_inicio__isnull=False, hora_fin__isnull=False)),
                name="promocion_franja_completa",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def es_promocion(self):
        return self.tipo == self.PROMOCION


class ComponentePromocion(models.Model):
    """
    Lo que incluye una promoción: texto libre, no platos del menú (SPEC-023).

    Libre por decisión del autor: el combo se arma como se vende ("Hamburguesa
    clásica" con sus ingredientes), sin obligar a crear antes cada pieza como
    plato. El costo de esa libertad es que la promo no se agota sola cuando se
    acaba un componente: se agota a mano.
    """

    promocion = models.ForeignKey(Plato, on_delete=models.CASCADE, related_name="componentes")
    orden = models.PositiveIntegerField(default=0)
    cantidad = models.PositiveSmallIntegerField(default=1)
    nombre = models.CharField(max_length=140)
    especificacion = models.TextField(
        blank=True, help_text="Ingredientes o detalle; lo ve el cliente al abrir la promo")

    class Meta:
        verbose_name = "Componente de promoción"
        verbose_name_plural = "Componentes de promoción"
        ordering = ["orden", "id"]
        constraints = [
            models.CheckConstraint(check=models.Q(cantidad__gte=1), name="componente_cantidad_positiva"),
        ]

    def __str__(self):
        return f"{self.cantidad}× {self.nombre}"


class ObservacionRapida(models.Model):
    """
    Botones de observación del carrito ("sin cebolla"...), configurables por
    restaurante (SPEC-003). Dan datos limpios a las estaciones y mantienen
    pequeño el QR del pedido (SPEC-002).

    Tres niveles (SPEC-003, revisado 2026-09-03):

    - **General** (`plato` y `categoria` vacíos): aparece en TODOS los platos.
      Para lo transversal — "sin sal", "para llevar".
    - **Por categoría** (`categoria` puesta, `plato` vacío): aparece en todos
      los platos de esa sección — "término medio" en Del Asador, "sin hielo"
      en Bebidas. Ni tan ancho como general ni tan angosto como uno solo.
    - **Por plato**: solo en ese.

    Un plato muestra las generales MÁS las de su categoría MÁS las suyas; no
    se reemplazan entre sí.
    """

    texto = models.CharField(max_length=60)
    # Los dos vacíos = general. Solo categoria = por sección. Solo plato = por
    # plato. Nunca las dos a la vez — lo impone la UI (una etiqueta se crea
    # desde un solo lugar: el panel general, la categoría, o la ficha del plato).
    categoria = models.ForeignKey(
        "menu.Categoria", on_delete=models.CASCADE, related_name="observaciones",
        null=True, blank=True,
    )
    plato = models.ForeignKey(
        "menu.Plato", on_delete=models.CASCADE, related_name="observaciones",
        null=True, blank=True,
    )
    activo = models.BooleanField(
        default=True,
        help_text="Desactivarla la quita del menu SIN borrar las observaciones "
                  "ya escritas en pedidos pasados (SPEC-008)",
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Observación rápida"
        verbose_name_plural = "Observaciones rápidas"
        ordering = ["orden", "texto"]
        constraints = [
            # El texto es único DENTRO de su ámbito: no puede haber dos
            # generales iguales, ni dos iguales en la misma categoría, ni dos
            # iguales en el mismo plato. Un plato SÍ puede repetir el texto de
            # una general o de su categoría — al mostrarlas se deduplica, así
            # que no molesta y evita bloquear al administrador por una
            # coincidencia razonable.
            models.UniqueConstraint(
                fields=["texto"], condition=models.Q(plato__isnull=True, categoria__isnull=True),
                name="texto_unico_entre_generales",
            ),
            models.UniqueConstraint(
                fields=["texto", "categoria"], condition=models.Q(categoria__isnull=False),
                name="texto_unico_por_categoria",
            ),
            models.UniqueConstraint(
                fields=["texto", "plato"], condition=models.Q(plato__isnull=False),
                name="texto_unico_por_plato",
            ),
        ]

    def __str__(self):
        return self.texto
