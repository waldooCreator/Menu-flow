"""
Siembra la configuración con los mismos valores que hoy están fijos en
`prototipo/` (styles.css e index.html), incluidas las imágenes reales.

Es la prueba de que la base reemplaza al CSS/HTML escritos a mano sin
cambiar nada del resultado visual.
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from configuracion.models import Parametro

ASSETS = Path(__file__).resolve().parents[4] / "prototipo" / "assets"

# SPEC-014, revisado 2026-09-16: la ayuda dice qué pasa en cada caso, porque
# el nombre solo no aclaraba que caja y administrador cobran de todos modos.
AYUDA_MESEROS_COBRAN = ("Sí: cobran caja, administrador y meseros. "
                        "No: solo caja y administrador")

TEXTOS = [
    # clave, etiqueta, grupo, tipo, valor, ayuda
    ("nombre-restaurante", "Nombre del restaurante", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Terra", "Aparece en la barra superior y como título del sitio"),
    ("color-bg", "Fondo", Parametro.GRUPO_IDENTIDAD, Parametro.COLOR,
     "#F4F3E7", "Crema cálido — nunca blanco puro (Sistema de Diseño)"),
    ("color-bg-alt", "Fondo alterno", Parametro.GRUPO_IDENTIDAD, Parametro.COLOR, "#EBE9DA", ""),
    ("color-ink", "Texto principal", Parametro.GRUPO_IDENTIDAD, Parametro.COLOR, "#0E150E", ""),
    ("color-primario", "Color de marca", Parametro.GRUPO_IDENTIDAD, Parametro.COLOR,
     "#00473C", "El color dominante en toda la página"),
    ("color-primario-suave", "Color de marca (suave)", Parametro.GRUPO_IDENTIDAD, Parametro.COLOR,
     "#D8E5D6", ""),
    ("color-acento", "Color de acento", Parametro.GRUPO_IDENTIDAD, Parametro.COLOR,
     "#E6FF55", "El golpe de energía: botones destacados, punto del mapa"),
    ("fuente-titulos", "Tipografía de títulos", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Bodoni Moda", "Familia de Google Fonts para títulos grandes"),
    ("fuente-cuerpo", "Tipografía de cuerpo", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Sofia Sans", "Familia de Google Fonts para el resto del texto"),

    ("hero-titulo", "Título de portada", Parametro.GRUPO_HERO, Parametro.TEXTO, "Terra", ""),
    ("hero-subtitulo", "Subtítulo de portada", Parametro.GRUPO_HERO, Parametro.TEXTO,
     "Cocina de fuego y raíz. Ingredientes locales, brasa lenta, sabor de casa.", ""),
    ("hero-texto-boton", "Texto del botón principal", Parametro.GRUPO_HERO, Parametro.TEXTO,
     "Ver el menú", ""),

    ("direccion-linea1", "Dirección (línea 1)", Parametro.GRUPO_CONTACTO, Parametro.TEXTO,
     "Calle 79 # 11 – 32", ""),
    ("direccion-linea2", "Dirección (línea 2)", Parametro.GRUPO_CONTACTO, Parametro.TEXTO,
     "Chapinero, Bogotá", ""),
    ("telefono", "Teléfono", Parametro.GRUPO_CONTACTO, Parametro.TEXTO, "+57 300 123 4567", ""),
    ("correo", "Correo", Parametro.GRUPO_CONTACTO, Parametro.TEXTO, "hola@terra.com", ""),
    ("numero-whatsapp", "WhatsApp para pedidos a distancia", Parametro.GRUPO_CONTACTO, Parametro.TEXTO,
     "573150537542", "Solo dígitos con indicativo de país, sin + ni espacios. Se usa en el enlace wa.me"),
    # PLANTILLA, no frase fija (SPEC-007): se rellena con lo que el cliente
    # escribio en el formulario de domicilio. La ayuda lista las variables
    # disponibles a proposito — un campo de plantilla sin esa lista es una
    # trampa para el administrador.
    ("whatsapp-mensaje", "Plantilla del mensaje de WhatsApp", Parametro.GRUPO_CONTACTO, Parametro.TEXTO,
     "Hola, buen dia. Mi nombre es {nombre}, mi ubicacion para el domicilio es {direccion}, "
     "y este es mi pedido en QR:",
     "Variables disponibles: {nombre} y {direccion}. Se rellenan con el formulario de "
     "domicilio del cliente. Una variable que no exista se deja tal cual, visible"),

    # Coordenadas de la sede para el mini-mapa. Se guardan como texto (igual
    # que todo Parametro) y el frontend valida el rango: un "0,0" por un
    # campo a medio llenar apuntaria al Golfo de Guinea sin avisar.
    ("mapa-latitud", "Latitud de la sede", Parametro.GRUPO_CONTACTO, Parametro.TEXTO,
     "4.6533", "Se saca de Google Maps: clic derecho sobre el local, el primer numero"),
    ("mapa-longitud", "Longitud de la sede", Parametro.GRUPO_CONTACTO, Parametro.TEXTO,
     "-74.0625", "El segundo numero del mismo clic derecho en Google Maps"),

    # Porcentajes de la cuenta (SPEC-013). NUNCA escritos en codigo: cambian
    # por normativa y varian entre clientes.
    # Quien puede cobrar (SPEC-014). Arranca ENCENDIDO: si arrancara apagado,
    # un restaurante recien instalado no podria cobrar hasta crear un cajero.
    ("meseros-pueden-cobrar", "Los meseros también pueden cobrar", Parametro.GRUPO_COBRO, Parametro.BOOLEANO,
     "si", AYUDA_MESEROS_COBRAN),
    ("propina-porcentaje", "Porcentaje de propina sugerida", Parametro.GRUPO_COBRO, Parametro.TEXTO,
     "10", "Se sugiere sobre el subtotal. El cliente SIEMPRE puede rechazarla: es voluntaria"),
    ("impuesto-porcentaje", "Porcentaje de impuesto", Parametro.GRUPO_COBRO, Parametro.TEXTO,
     "0", "En 0 no aparece en la cuenta. Cada restaurante configura el que le aplique"),

    # Parametros de formato y operacion que no deben vivir en el frontend.
    ("moneda", "Moneda", Parametro.GRUPO_OPERACION, Parametro.TEXTO,
     "COP", "Codigo ISO 4217, p.ej. COP, USD o MXN"),
    ("locale", "Formato regional", Parametro.GRUPO_OPERACION, Parametro.TEXTO,
     "es-CO", "Locale Intl, p.ej. es-CO o en-US"),
    ("qr-vigencia-horas", "Vigencia del QR de pedido (horas)", Parametro.GRUPO_OPERACION,
     Parametro.TEXTO, "6", "Tiempo antes de exigir un QR nuevo"),
    ("umbral-cronometro-amarillo", "Cronometro: umbral amarillo (minutos)",
     Parametro.GRUPO_OPERACION, Parametro.TEXTO, "10", "Desde cuando una comanda pasa a amarillo"),
    ("umbral-cronometro-rojo", "Cronometro: umbral rojo (minutos)",
     Parametro.GRUPO_OPERACION, Parametro.TEXTO, "20", "Desde cuando una comanda pasa a rojo"),
    ("estaciones-unificadas", "Unificar estaciones", Parametro.GRUPO_OPERACION, Parametro.BOOLEANO,
     "no", "Si: todo llega a la estación por defecto, bebidas incluidas. No: cada plato va a la estación de su categoría"),

    # Promociones (SPEC-023)
    ("titulo-promociones", "Título de la sección de promociones", Parametro.GRUPO_IDENTIDAD,
     Parametro.TEXTO, "Promociones", "Encabeza la sección que aparece de primera en el menú"),
    ("texto-promo-incluye", "Texto antes de lo que incluye una promo", Parametro.GRUPO_IDENTIDAD,
     Parametro.TEXTO, "Incluye", "Se muestra al abrir el detalle de una promoción"),
    ("texto-promo-hasta", "Texto de la fecha de fin de una promo", Parametro.GRUPO_IDENTIDAD,
     Parametro.TEXTO, "Válida hasta", "Seguido de la fecha u hora en que termina"),
    ("texto-insignia-promo", "Insignia de las promociones", Parametro.GRUPO_IDENTIDAD,
     Parametro.TEXTO, "Promo", "Sale sobre la foto de cada promoción en el menú"),
    ("texto-ver-promo", "Enlace al detalle de una promo", Parametro.GRUPO_IDENTIDAD,
     Parametro.TEXTO, "Ver qué incluye", "Abre la lista de lo que incluye la promoción"),

    # Textos de la pagina publica: el componente solo conoce estructura, no
    # vocabulario particular de un restaurante.
    ("etiqueta-encuentranos", "Titulo de ubicacion", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Encuéntranos", "Titulo de la seccion de ubicacion"),
    ("etiqueta-visitanos", "Etiqueta de ubicacion", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Visítanos", "Texto pequeño sobre el titulo de ubicacion"),
    ("etiqueta-direccion", "Titulo de direccion", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Dirección", "Titulo del bloque de direccion"),
    ("etiqueta-horario", "Titulo de horario", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Horario", "Titulo del bloque de horario"),
    ("etiqueta-contacto", "Titulo de contacto", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Contacto", "Titulo del bloque de contacto"),
    ("etiqueta-como-llegar", "Titulo de mapa", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Cómo llegar", "Titulo del bloque del mapa"),
    ("texto-plato-agotado", "Texto de plato agotado", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "Agotado hoy", "Etiqueta visible sobre platos no disponibles"),
    ("texto-pie-sitio", "Texto del pie del sitio", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "", "Si se deja vacío se muestra solo el nombre del restaurante"),

    # Tiquete interno de venta (SPEC-016). No es facturación electrónica DIAN.
    ("nit", "NIT del negocio", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "", "Identificación que aparece en el tiquete interno"),
    ("formato-tiquete", "Formato del tiquete", Parametro.GRUPO_IDENTIDAD, Parametro.TEXTO,
     "rollo", "Valores: rollo o carta"),
    ("mensaje-pie-tiquete", "Mensaje al pie del tiquete", Parametro.GRUPO_IDENTIDAD,
     Parametro.TEXTO, "Gracias por visitarnos", "Texto configurable para el comprobante"),

    ("horario-lun-jue", "Horario lunes a jueves", Parametro.GRUPO_HORARIO, Parametro.TEXTO,
     "12:00 – 22:00", ""),
    ("horario-vie-sab", "Horario viernes y sábado", Parametro.GRUPO_HORARIO, Parametro.TEXTO,
     "12:00 – 23:30", ""),
    ("horario-domingo", "Horario domingo", Parametro.GRUPO_HORARIO, Parametro.TEXTO,
     "12:00 – 21:00", ""),

    # Pies de las fotos de la galería — parametrizados como todo texto de
    # negocio (regla del proyecto): con fotos temáticas, "La barra" no aplica.
    ("galeria-pie-1", "Pie de la foto grande", Parametro.GRUPO_GALERIA, Parametro.TEXTO,
     "El salón", ""),
    ("galeria-pie-2", "Pie de la segunda foto", Parametro.GRUPO_GALERIA, Parametro.TEXTO,
     "La barra", ""),
    ("galeria-pie-3", "Pie de la tercera foto", Parametro.GRUPO_GALERIA, Parametro.TEXTO,
     "La terraza", ""),
]

# clave, etiqueta, grupo, archivo en prototipo/assets/
IMAGENES = [
    ("hero-imagen-fondo", "Imagen de portada (parallax)", Parametro.GRUPO_HERO, "hero.jpg"),
    ("galeria-imagen-salon", "Galería — El salón", Parametro.GRUPO_GALERIA, "lugar-salon.jpg"),
    ("galeria-imagen-barra", "Galería — La barra", Parametro.GRUPO_GALERIA, "lugar-barra.jpg"),
    ("galeria-imagen-terraza", "Galería — La terraza", Parametro.GRUPO_GALERIA, "lugar-terraza.jpg"),
]

IMAGENES_SIN_ARCHIVO = [
    ("logo-tiquete", "Logo del tiquete", Parametro.GRUPO_IDENTIDAD),
]

# Decoración de fondo del menú: se crean VACÍAS a propósito. Un restaurante
# sin figuras decorativas (como Terra) simplemente no las llena, y el menú
# se ve limpio. Springfield las rellena con los personajes.
DECORACIONES = [
    ("deco-patron", "Papel tapiz del menú"),
] + [(f"deco-imagen-{i}", f"Figura decorativa {i}") for i in range(1, 5)]


class Command(BaseCommand):
    help = "Siembra la configuración inicial con los valores del prototipo visual"

    def handle(self, *args, **options):
        creados, actualizados = 0, 0

        for orden, (clave, etiqueta, grupo, tipo, valor, ayuda) in enumerate(TEXTOS):
            _, fue_creado = Parametro.objects.update_or_create(
                clave=clave,
                defaults=dict(etiqueta=etiqueta, grupo=grupo, tipo=tipo,
                              valor=valor, ayuda=ayuda, orden=orden),
            )
            creados += fue_creado
            actualizados += not fue_creado

        for orden, (clave, etiqueta, grupo, archivo) in enumerate(IMAGENES):
            ruta = ASSETS / archivo
            if not ruta.exists():
                self.stderr.write(f"  omitido {clave}: no existe {ruta}")
                continue
            param, fue_creado = Parametro.objects.get_or_create(
                clave=clave, defaults=dict(etiqueta=etiqueta, grupo=grupo,
                                            tipo=Parametro.IMAGEN, orden=orden),
            )
            with open(ruta, "rb") as f:
                param.imagen.save(archivo, File(f), save=False)
            param.etiqueta, param.grupo, param.tipo, param.orden = (
                etiqueta, grupo, Parametro.IMAGEN, orden,
            )
            param.save()
            creados += fue_creado
            actualizados += not fue_creado

        for orden, (clave, etiqueta, grupo) in enumerate(IMAGENES_SIN_ARCHIVO):
            _, fue_creado = Parametro.objects.get_or_create(
                clave=clave,
                defaults=dict(
                    etiqueta=etiqueta, grupo=grupo, tipo=Parametro.IMAGEN,
                    orden=orden, ayuda="Imagen que aparece en el comprobante de venta",
                ),
            )
            creados += fue_creado
            actualizados += not fue_creado

        for orden, (clave, etiqueta) in enumerate(DECORACIONES):
            param, fue_creado = Parametro.objects.get_or_create(
                clave=clave,
                defaults=dict(
                    etiqueta=etiqueta, grupo=Parametro.GRUPO_DECORACION,
                    tipo=Parametro.IMAGEN, orden=orden,
                    ayuda="PNG transparente. El papel tapiz debe ser un mosaico sin costuras; "
                          "las figuras son las piezas con las que se compone.",
                ),
            )
            # Volver al tema base limpia la decoración del tema anterior.
            if not fue_creado and param.imagen:
                param.imagen.delete(save=True)
            creados += fue_creado
            actualizados += not fue_creado

        self.stdout.write(self.style.SUCCESS(
            f"Configuración sembrada: {creados} creados, {actualizados} actualizados."
        ))
