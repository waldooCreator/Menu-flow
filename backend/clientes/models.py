"""
Los clientes del restaurante (SPEC-019).

Solo existen para los domicilios: una mesa no tiene cliente que guardar, y
forzar uno obligaría a inventar datos.

Se guarda lo mínimo para poder entregar un pedido — nombre, teléfono,
dirección y observaciones. Nada más. Cada campo extra sería un dato personal
que hay que proteger y justificar.
"""

import re

from django.db import models


def normalizar_telefono(valor):
    """
    Deja solo los dígitos, y quita el indicativo de país si viene.

    `320 276 6485`, `+57 320 276 6485` y `3202766485` son el MISMO número
    escrito de tres formas. Sin esto, el mismo cliente entraría tres veces al
    directorio según cómo lo hubiera tecleado ese día.
    """
    digitos = re.sub(r"\D", "", valor or "")
    # Un celular colombiano son 10 dígitos; con indicativo llegan 12.
    if len(digitos) == 12 and digitos.startswith("57"):
        digitos = digitos[2:]
    return digitos


def normalizar_direccion(valor):
    """
    Para COMPARAR dos direcciones, no para mostrarlas: minúsculas, sin tildes,
    sin puntuación y sin espacios de sobra.

    Así "Barrio XXX" y "barrio xxx" se reconocen solas.

    **No se ordenan las palabras** a propósito, aunque eso haría coincidir
    "barrio xxx" con "xxx barrio". El precio sería que `calle 5 casa 20` y
    `calle 20 casa 5` pasarían por la misma dirección, y equivocarse ahí
    significa mandar la comida a otra casa. Cuando no coinciden exactamente,
    se le pregunta a la persona (SPEC-019).
    """
    texto = (valor or "").lower().strip()
    reemplazos = str.maketrans("áéíóúü", "aeiouu")
    texto = texto.translate(reemplazos)
    texto = re.sub(r"[^\w\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


class Cliente(models.Model):
    """
    Identificado por el teléfono (SPEC-019, regla 1).

    Es lo único que la gente da siempre y no cambia. El nombre se escribe
    distinto cada vez — "María Angélica", "angelica lopez", "Cris" — y el
    correo casi nadie lo da. Un teléfono repetido NO crea un cliente nuevo:
    actualiza el que existe.
    """

    telefono = models.CharField(
        max_length=20, unique=True,
        help_text="Solo dígitos. Es el identificador del cliente.",
    )
    nombre = models.CharField(max_length=120)
    observaciones = models.TextField(
        blank=True,
        help_text="Lo que haga falta anotar: 'paga con efectivo, sin cambio de 50', "
                  "'timbre dañado, llamar al llegar'. Existe desde el primer día para "
                  "que el teléfono siga siendo un teléfono (SPEC-019).",
    )

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "cliente"
        verbose_name_plural = "clientes"

    def __str__(self):
        return f"{self.nombre} ({self.telefono})"

    def save(self, *args, **kwargs):
        # Se normaliza SIEMPRE al guardar, venga de donde venga: si la
        # normalización viviera solo en la vista, cualquier otro camino
        # (el panel, un comando, un test) metería duplicados.
        self.telefono = normalizar_telefono(self.telefono)
        super().save(*args, **kwargs)

    def direccion_parecida(self, texto):
        """
        La dirección guardada que coincide EXACTAMENTE tras normalizar, o None.

        Devuelve None ante la menor duda a propósito: quien toma el pedido
        decide en un toque lo que el sistema no puede deducir sin arriesgarse
        a mandar la comida a otra casa.
        """
        buscada = normalizar_direccion(texto)
        if not buscada:
            return None
        for direccion in self.direcciones.all():
            if normalizar_direccion(direccion.direccion) == buscada:
                return direccion
        return None


class DireccionCliente(models.Model):
    """
    Un cliente puede tener casa y oficina. Al pedir elige entre las que ya
    tiene, o escribe una nueva que queda guardada para la próxima.
    """

    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name="direcciones")
    direccion = models.CharField(max_length=250)
    indicaciones = models.CharField(
        max_length=200, blank=True,
        help_text="Cómo llegar: 'casa verde, portón negro', 'apto 302'",
    )
    veces_usada = models.PositiveIntegerField(default=1)
    ultima_vez = models.DateTimeField(auto_now=True)

    class Meta:
        # La más usada primero: es la que el cliente va a querer casi siempre.
        ordering = ["-veces_usada", "-ultima_vez"]
        verbose_name = "dirección de cliente"
        verbose_name_plural = "direcciones de cliente"

    def __str__(self):
        return f"{self.cliente.nombre} — {self.direccion}"
