from django.db import models


class Parametro(models.Model):
    """
    Una tabla clave/valor para TODA la configuración del sitio: colores,
    tipografías, textos, imágenes, contacto, horarios.

    Por qué una sola tabla y no una columna por ajuste (ADR-003, regla 2):
    agregar un parámetro nuevo mañana es una fila, no una migración. Y al
    exportar la base de un restaurante para montarlo en otro servidor
    (SPEC-009), su identidad completa viaja aquí adentro.
    """

    TEXTO = "texto"
    COLOR = "color"
    NUMERO = "numero"
    IMAGEN = "imagen"
    BOOLEANO = "booleano"

    TIPOS = [
        (TEXTO, "Texto"),
        (COLOR, "Color"),
        (NUMERO, "Número"),
        (IMAGEN, "Imagen"),
        (BOOLEANO, "Sí / No"),
    ]

    # Grupos para ordenar el panel de admin. Es texto libre a propósito:
    # crear un grupo nuevo no debe pedir una migración.
    GRUPO_IDENTIDAD = "identidad"
    GRUPO_HERO = "hero"
    GRUPO_CONTACTO = "contacto"
    GRUPO_HORARIO = "horario"
    GRUPO_GALERIA = "galeria"
    GRUPO_DECORACION = "decoracion"
    GRUPO_OPERACION = "operacion"
    # SPEC-014, revisado 2026-09-16: quién cobra, propina e impuesto vivían en
    # "Contacto", donde nadie los buscaba.
    GRUPO_COBRO = "cobro"

    GRUPOS = [
        (GRUPO_IDENTIDAD, "Identidad visual"),
        (GRUPO_HERO, "Portada (hero)"),
        (GRUPO_CONTACTO, "Contacto"),
        (GRUPO_HORARIO, "Horario"),
        (GRUPO_GALERIA, "Galería del local"),
        (GRUPO_DECORACION, "Decoración del menú"),
        (GRUPO_OPERACION, "Operación"),
        (GRUPO_COBRO, "Cobro"),
    ]

    clave = models.SlugField(
        max_length=80, unique=True,
        help_text="Identificador estable usado por el código, p.ej. color-primario",
    )
    etiqueta = models.CharField(
        max_length=120, help_text="Nombre legible en el panel, p.ej. Color primario",
    )
    grupo = models.CharField(max_length=30, choices=GRUPOS, default=GRUPO_IDENTIDAD)
    tipo = models.CharField(max_length=12, choices=TIPOS, default=TEXTO)

    # Un parámetro usa `valor` o `imagen` según su tipo, nunca los dos.
    valor = models.TextField(blank=True, help_text="Usado para texto, color, número y sí/no")
    imagen = models.ImageField(
        upload_to="configuracion/", blank=True, null=True,
        help_text="Usado solo cuando el tipo es Imagen",
    )

    ayuda = models.CharField(
        max_length=200, blank=True,
        help_text="Texto de ayuda que ve el administrador junto al campo",
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Parámetro de configuración"
        verbose_name_plural = "Parámetros de configuración"
        ordering = ["grupo", "orden", "clave"]

    def __str__(self):
        return self.etiqueta

    def valor_resuelto(self):
        """Lo que de verdad se usa: la URL de la imagen o el valor de texto."""
        if self.tipo == self.IMAGEN:
            return self.imagen.url if self.imagen else ""
        if self.tipo == self.BOOLEANO:
            return self.valor.strip().lower() in ("1", "true", "si", "sí")
        return self.valor
