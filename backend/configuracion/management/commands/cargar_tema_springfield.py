"""
Aplica el tema Springfield (boceto para el cliente potencial): paleta de
Los Simpson, tipografías cartoon y las imágenes de `backend/recursos/springfield/`.

Es la demostración del requisito 1 del proyecto: cambiar de restaurante es
cambiar configuración, nunca código. El tema Terra se restaura corriendo
`cargar_configuracion_demo` de nuevo.

Paleta (investigada 2026-08-25, ver bitácora):
- Amarillo del logo: #FFDE00 · Azul Simpson: #2F64D6 · Rosa dona: #FF81C1
- Estructura del Sistema de Diseño: fondo cálido + marca profunda + acento
  vibrante. El amarillo va de ACENTO, no de fondo dominante — legibilidad.
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from configuracion.models import Parametro

RECURSOS = Path(__file__).resolve().parents[3] / "recursos" / "springfield"

VALORES = [
    # clave, valor
    ("nombre-restaurante", "Springfield"),
    ("color-bg", "#FFF9E6"),
    ("color-bg-alt", "#FFF0C2"),
    ("color-ink", "#26201A"),
    ("color-primario", "#2F64D6"),
    ("color-primario-suave", "#CFE0FA"),
    ("color-acento", "#FFDE00"),
    ("fuente-titulos", "Luckiest Guy"),
    ("fuente-cuerpo", "Nunito"),
    ("hero-titulo", "Springfield"),
    ("hero-subtitulo", "Hamburguesas, donas y el sabor de la ciudad más famosa de la TV."),
    ("hero-texto-boton", "Ver el menú"),
    # Datos reales del restaurante (entregados por el autor 2026-08-25).
    # El enlace que pasó venía envuelto por Instagram (l.instagram.com/?u=...);
    # se usa el wa.me real que lleva dentro — el envoltorio carga un token
    # firmado que caduca y añade un salto de redirección innecesario.
    ("numero-whatsapp", "573202766485"),
    ("whatsapp-mensaje",
     "Buenas noches, deseo hacer un pedido 🍔🌭 Mi nombre es {nombre} "
     "y mi direccion es {direccion}. Este es mi pedido en QR:"),
    ("telefono", "+57 320 276 6485"),
    # Sin correo entregado por el restaurante: se deja vacio a proposito y la
    # pagina no pinta el renglon. Mejor un dato menos que uno inventado.
    ("correo", ""),
    # Punto del mini-mapa. Geocodificado con Nominatim (OpenStreetMap) a
    # partir de la direccion: cae sobre la Calle 18A del barrio Libertad.
    # APROXIMADO al tramo de calle, no a la puerta — el numero #8-71 no esta
    # en OSM. El cliente lo afina desde el panel con el clic derecho de
    # Google Maps sobre su local.
    ("mapa-latitud", "7.8865671"),
    ("mapa-longitud", "-72.4788715"),
    ("direccion-linea1", "Calle 18a #8-71, Libertad"),
    ("direccion-linea2", "Cúcuta, Norte de Santander"),
    ("horario-lun-jue", "5:30 pm – 11:00 pm"),
    ("horario-vie-sab", "5:30 pm – 11:00 pm"),
    ("horario-domingo", "5:30 pm – 11:00 pm"),
    ("galeria-pie-1", "Krusty Burger"),
    ("galeria-pie-2", "En familia"),
    ("galeria-pie-3", "Todo Springfield"),
]

IMAGENES = [
    # clave, archivo en recursos/springfield/
    ("hero-imagen-fondo", "hero.jpg"),
    ("galeria-imagen-salon", "galeria-1.jpg"),
    ("galeria-imagen-barra", "galeria-2.jpg"),
    ("galeria-imagen-terraza", "galeria-3.jpg"),
    # Papel tapiz del menú: mosaico sin costuras compuesto con las figuras
    # (generado con el script del scratchpad; ver bitácora del 2026-08-25)
    ("deco-patron", "patron.png"),
    # Las figuras sueltas quedan como las piezas de origen del mosaico
    ("deco-imagen-1", "deco/familia.png"),
    ("deco-imagen-2", "deco/krusty.png"),
    ("deco-imagen-3", "deco/homer.png"),
    ("deco-imagen-4", "deco/bart.png"),
]


class Command(BaseCommand):
    help = "Aplica el tema Springfield (paleta Simpson + imágenes del boceto)"

    def handle(self, *args, **options):
        cambiados = 0
        for clave, valor in VALORES:
            filas = Parametro.objects.filter(clave=clave).update(valor=valor)
            if filas:
                cambiados += filas
            else:
                self.stderr.write(f"  clave inexistente (corre antes cargar_configuracion_demo): {clave}")

        for clave, archivo in IMAGENES:
            ruta = RECURSOS / archivo
            if not ruta.exists():
                self.stderr.write(f"  omitida {clave}: no existe {ruta}")
                continue
            param = Parametro.objects.filter(clave=clave).first()
            if param is None:
                self.stderr.write(f"  clave inexistente: {clave}")
                continue
            with open(ruta, "rb") as f:
                param.imagen.save(f"springfield-{archivo}", File(f), save=True)
            cambiados += 1

        self.stdout.write(self.style.SUCCESS(
            f"Tema Springfield aplicado: {cambiados} parámetros actualizados. "
            "Para volver al tema Terra: manage.py cargar_configuracion_demo"
        ))
