"""
Siembra el menú con los mismos platos que hoy están fijos en
`prototipo/data.js`, copiando también las fotos reales de `prototipo/assets/`.

Es la prueba de que la base reemplaza a data.js sin cambiar nada del
resultado visual.
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from menu.models import Categoria, Etiqueta, ObservacionRapida, Plato

ASSETS = Path(__file__).resolve().parents[4] / "prototipo" / "assets"

OBSERVACIONES_RAPIDAS = [
    "Sin cebolla", "Sin picante", "Poca sal", "Sin cilantro", "Para compartir",
]

CATEGORIAS = [
    ("compartir", "Para Compartir"),
    ("bowls", "Bowls"),
    ("asador", "Del Asador"),
    ("bebidas", "Bebidas"),
    ("postres", "Postres"),
]

# categoria_slug, nombre, descripcion, precio, archivo_foto, tags, alergenos, disponible, stats
PLATOS = [
    ("compartir", "Pan de maíz de la casa",
     "Maíz peto molido en piedra, mantequilla de hierbas del huerto, sal marina de Manaure, horneado cada mañana.",
     14000, "p-pan.jpg", ["vegetariano"], "Contiene lácteos, gluten", True,
     [["380", "Cal"], ["4", "Porciones"], ["8", "Min"]]),
    ("compartir", "Croquetas de yuca y queso",
     "Yuca criolla del Tolima, queso costeño, alioli de cilantro, ají dulce, cebolla larga encurtida.",
     18000, "p-croquetas.jpg", ["vegetariano"], "Contiene lácteos, huevo, gluten", True,
     [["420", "Cal"], ["6", "Unidades"], ["12", "Min"]]),
    ("compartir", "Ceviche de la casa",
     "Pescado blanco del día, leche de tigre de ají amarillo, camote asado, choclo, cebolla morada, cilantro fresco.",
     26000, "p-ceviche.jpg", ["picante"], "Contiene pescado", True,
     [["290", "Cal"], ["24g", "Proteína"], ["10", "Min"]]),
    ("compartir", "Chicharrones con ají",
     "Cerdo de finca, cocción lenta 6 horas, ají casero de tomate de árbol, limón criollo, sal ahumada.",
     22000, "p-chicharrones.jpg", ["picante"], "", True,
     [["610", "Cal"], ["3", "Porciones"], ["15", "Min"]]),

    ("bowls", "Bowl de quinoa y aguacate",
     "Quinoa tricolor de Boyacá, aguacate hass, garbanzo especiado, batata asada, rábano, brotes, vinagreta cítrica.",
     28000, "p-bowl-quinoa.jpg", ["vegetariano"], "", True,
     [["540", "Cal"], ["18g", "Proteína"], ["62g", "Carbs"]]),
    ("bowls", "Bowl de pollo a la brasa",
     "Pollo marinado 24 horas, arroz integral, kale masajeado, huevo de campo, pepino, tomate cherry, salsa de la casa.",
     30000, "p-bowl-pollo.jpg", [], "Contiene huevo", True,
     [["690", "Cal"], ["42g", "Proteína"], ["55g", "Carbs"]]),
    ("bowls", "Bowl de salmón y mango",
     "Salmón sellado, mango de azúcar, edamame, arroz de coco, salsa de maracuyá, ajonjolí tostado.",
     34000, "p-bowl-salmon.jpg", [], "Contiene pescado, soya, ajonjolí", False,
     [["720", "Cal"], ["38g", "Proteína"], ["48g", "Carbs"]]),
    ("bowls", "Bowl vegano de garbanzo",
     "Garbanzo especiado al comino, kale, batata asada, quinoa, tahini de ajonjolí, limón, semillas de girasol.",
     27000, "p-bowl-garbanzo.jpg", ["vegetariano"], "Contiene ajonjolí", True,
     [["480", "Cal"], ["16g", "Proteína"], ["58g", "Carbs"]]),

    ("asador", "Punta de anca a la parrilla",
     "300g de res madurada, brasa de carbón, chimichurri de la casa, sal marina en escamas, término a elección.",
     42000, "p-punta-anca.jpg", [], "", True,
     [["780", "Cal"], ["58g", "Proteína"], ["18", "Min"]]),
    ("asador", "Costillas ahumadas 12 horas",
     "Costilla de cerdo, ahumado lento en leña de naranjo, salsa BBQ de tamarindo y panela, encurtido de cebolla.",
     46000, "p-costillas.jpg", [], "", True,
     [["920", "Cal"], ["52g", "Proteína"], ["20", "Min"]]),
    ("asador", "Pechuga a la brasa con chimichurri",
     "Pechuga marinada en cítricos, papa criolla salteada, brócoli asado, chimichurri fresco de perejil y ajo.",
     32000, "p-pechuga.jpg", [], "", True,
     [["610", "Cal"], ["46g", "Proteína"], ["16", "Min"]]),
    ("asador", "Trucha entera a la leña",
     "Trucha de páramo, hierbas frescas, limón asado, mantequilla de ajo, espinaca salteada, almendras tostadas.",
     38000, "p-trucha.jpg", [], "Contiene pescado, lácteos, frutos secos", True,
     [["520", "Cal"], ["44g", "Proteína"], ["18", "Min"]]),

    ("bebidas", "Limonada de coco",
     "Limón criollo exprimido al momento, leche de coco, hierbabuena fresca, hielo triturado.",
     10000, "p-limonada.jpg", [], "", True,
     [["210", "Cal"], ["16", "Onzas"], ["3", "Min"]]),
    ("bebidas", "Agua de panela con limón",
     "Panela de trapiche, limón criollo, servida bien fría. Receta de la abuela, sin azúcar añadida.",
     8000, "p-panela.jpg", [], "", True,
     [["120", "Cal"], ["16", "Onzas"], ["2", "Min"]]),
    ("bebidas", "Jugo natural del día",
     "Fruta de temporada exprimida al momento. Pregúntale a tu mesero por la fruta de hoy.",
     9000, "p-jugo.jpg", [], "", True,
     [["150", "Cal"], ["12", "Onzas"], ["3", "Min"]]),
    ("bebidas", "Cerveza artesanal",
     "Producción local de Bogotá, rotación de temporada. Consulta la variedad disponible hoy.",
     12000, "p-cerveza.jpg", [], "Contiene gluten", True,
     [["180", "Cal"], ["330", "ml"], ["5.2", "% Alc"]]),

    ("postres", "Flan de café",
     "Café de origen del Huila, caramelo salado, crema de leche, toque de vainilla natural.",
     14000, "p-flan.jpg", ["vegetariano"], "Contiene lácteos, huevo", True,
     [["340", "Cal"], ["1", "Porción"], ["5", "Min"]]),
    ("postres", "Brownie con helado",
     "Chocolate 70% del Chocó, helado de vainilla natural, nueces caramelizadas, salsa tibia de chocolate.",
     16000, "p-brownie.jpg", ["vegetariano"], "Contiene lácteos, huevo, gluten, frutos secos", True,
     [["580", "Cal"], ["1", "Porción"], ["6", "Min"]]),
    ("postres", "Torta de zanahoria con un nombre bastante largo para probar el diseño",
     "Zanahoria fresca, especias de canela y nuez moscada, queso crema batido, nuez pecana. "
     "Ítem de prueba con nombre extenso a propósito.",
     13000, "p-torta.jpg", ["vegetariano"], "Contiene lácteos, huevo, gluten, frutos secos", True,
     [["460", "Cal"], ["1", "Porción"], ["4", "Min"]]),
]


class Command(BaseCommand):
    help = "Siembra el menú inicial con los platos del prototipo visual"

    def handle(self, *args, **options):
        categorias = {}
        for orden, (slug, nombre) in enumerate(CATEGORIAS):
            cat, _ = Categoria.objects.update_or_create(
                nombre=nombre, defaults=dict(orden=orden),
            )
            categorias[slug] = cat

        etiquetas = {}
        for nombre in ("vegetariano", "picante"):
            et, _ = Etiqueta.objects.get_or_create(nombre=nombre)
            etiquetas[nombre] = et

        creados, actualizados = 0, 0
        for orden, (cat_slug, nombre, desc, precio, archivo, tags, alergenos,
                    disponible, stats) in enumerate(PLATOS):
            plato, fue_creado = Plato.objects.update_or_create(
                nombre=nombre,
                defaults=dict(
                    categoria=categorias[cat_slug], descripcion=desc, precio=precio,
                    disponible=disponible, alergenos=alergenos, estadisticas=stats, orden=orden,
                ),
            )
            plato.etiquetas.set([etiquetas[t] for t in tags])

            ruta = ASSETS / archivo
            if ruta.exists() and not plato.foto:
                with open(ruta, "rb") as f:
                    plato.foto.save(archivo, File(f), save=True)
            elif not ruta.exists():
                self.stderr.write(f"  sin foto para «{nombre}»: no existe {ruta}")

            creados += fue_creado
            actualizados += not fue_creado

        for orden, texto in enumerate(OBSERVACIONES_RAPIDAS):
            ObservacionRapida.objects.update_or_create(texto=texto, defaults=dict(orden=orden))

        self.stdout.write(self.style.SUCCESS(
            f"Menú sembrado: {len(categorias)} categorías, {creados} platos creados, "
            f"{actualizados} actualizados, {len(OBSERVACIONES_RAPIDAS)} observaciones rápidas."
        ))
