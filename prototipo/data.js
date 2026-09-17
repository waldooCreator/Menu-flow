/**
 * Datos de ejemplo — Fase 0 (prototipo visual, sin backend).
 * Esta es la forma de datos que el backend deberá entregar más adelante (§18 CONTEXTO.md).
 *
 * Nota de diseño: la descripción es la LISTA COMPLETA DE INGREDIENTES, no una frase
 * publicitaria. Es lo que hace Sweetgreen y es lo que el comensal realmente quiere saber.
 */

const MENU_DATA = {
  /**
   * Observaciones rápidas: botones predefinidos que acompañan al campo libre.
   * Dan datos limpios y consistentes a las estaciones, y mantienen pequeño el
   * QR del pedido (SPEC-002). Deben ser configurables por restaurante.
   */
  observacionesRapidas: [
    "Sin cebolla",
    "Sin picante",
    "Poca sal",
    "Sin cilantro",
    "Para compartir",
  ],

  categorias: [
    { id: "compartir", nombre: "Para Compartir" },
    { id: "bowls",     nombre: "Bowls" },
    { id: "asador",    nombre: "Del Asador" },
    { id: "bebidas",   nombre: "Bebidas" },
    { id: "postres",   nombre: "Postres" },
  ],

  platos: [
    // ---------------- Para compartir ----------------
    {
      id: 1, categoria: "compartir", nombre: "Pan de maíz de la casa",
      descripcion: "Maíz peto molido en piedra, mantequilla de hierbas del huerto, sal marina de Manaure, horneado cada mañana.",
      precio: 14000, foto: "assets/p-pan.jpg", tags: ["vegetariano"],
      alergenos: "Contiene lácteos, gluten",
      stats: [["380", "Cal"], ["4", "Porciones"], ["8", "Min"]],
    },
    {
      id: 2, categoria: "compartir", nombre: "Croquetas de yuca y queso",
      descripcion: "Yuca criolla del Tolima, queso costeño, alioli de cilantro, ají dulce, cebolla larga encurtida.",
      precio: 18000, foto: "assets/p-croquetas.jpg", tags: ["vegetariano"],
      alergenos: "Contiene lácteos, huevo, gluten",
      stats: [["420", "Cal"], ["6", "Unidades"], ["12", "Min"]],
    },
    {
      id: 3, categoria: "compartir", nombre: "Ceviche de la casa",
      descripcion: "Pescado blanco del día, leche de tigre de ají amarillo, camote asado, choclo, cebolla morada, cilantro fresco.",
      precio: 26000, foto: "assets/p-ceviche.jpg", tags: ["picante"],
      alergenos: "Contiene pescado",
      stats: [["290", "Cal"], ["24g", "Proteína"], ["10", "Min"]],
    },
    {
      id: 4, categoria: "compartir", nombre: "Chicharrones con ají",
      descripcion: "Cerdo de finca, cocción lenta 6 horas, ají casero de tomate de árbol, limón criollo, sal ahumada.",
      precio: 22000, foto: "assets/p-chicharrones.jpg", tags: ["picante"],
      alergenos: "—",
      stats: [["610", "Cal"], ["3", "Porciones"], ["15", "Min"]],
    },

    // ---------------- Bowls ----------------
    {
      id: 5, categoria: "bowls", nombre: "Bowl de quinoa y aguacate",
      descripcion: "Quinoa tricolor de Boyacá, aguacate hass, garbanzo especiado, batata asada, rábano, brotes, vinagreta cítrica.",
      precio: 28000, foto: "assets/p-bowl-quinoa.jpg", tags: ["vegetariano"],
      alergenos: "—",
      stats: [["540", "Cal"], ["18g", "Proteína"], ["62g", "Carbs"]],
    },
    {
      id: 6, categoria: "bowls", nombre: "Bowl de pollo a la brasa",
      descripcion: "Pollo marinado 24 horas, arroz integral, kale masajeado, huevo de campo, pepino, tomate cherry, salsa de la casa.",
      precio: 30000, foto: "assets/p-bowl-pollo.jpg", tags: [],
      alergenos: "Contiene huevo",
      stats: [["690", "Cal"], ["42g", "Proteína"], ["55g", "Carbs"]],
    },
    {
      id: 7, categoria: "bowls", nombre: "Bowl de salmón y mango",
      descripcion: "Salmón sellado, mango de azúcar, edamame, arroz de coco, salsa de maracuyá, ajonjolí tostado.",
      precio: 34000, foto: "assets/p-bowl-salmon.jpg", tags: [], disponible: false,
      alergenos: "Contiene pescado, soya, ajonjolí",
      stats: [["720", "Cal"], ["38g", "Proteína"], ["48g", "Carbs"]],
    },
    {
      id: 8, categoria: "bowls", nombre: "Bowl vegano de garbanzo",
      descripcion: "Garbanzo especiado al comino, kale, batata asada, quinoa, tahini de ajonjolí, limón, semillas de girasol.",
      precio: 27000, foto: "assets/p-bowl-garbanzo.jpg", tags: ["vegetariano"],
      alergenos: "Contiene ajonjolí",
      stats: [["480", "Cal"], ["16g", "Proteína"], ["58g", "Carbs"]],
    },

    // ---------------- Del asador ----------------
    {
      id: 9, categoria: "asador", nombre: "Punta de anca a la parrilla",
      descripcion: "300g de res madurada, brasa de carbón, chimichurri de la casa, sal marina en escamas, término a elección.",
      precio: 42000, foto: "assets/p-punta-anca.jpg", tags: [],
      alergenos: "—",
      stats: [["780", "Cal"], ["58g", "Proteína"], ["18", "Min"]],
    },
    {
      id: 10, categoria: "asador", nombre: "Costillas ahumadas 12 horas",
      descripcion: "Costilla de cerdo, ahumado lento en leña de naranjo, salsa BBQ de tamarindo y panela, encurtido de cebolla.",
      precio: 46000, foto: "assets/p-costillas.jpg", tags: [],
      alergenos: "—",
      stats: [["920", "Cal"], ["52g", "Proteína"], ["20", "Min"]],
    },
    {
      id: 11, categoria: "asador", nombre: "Pechuga a la brasa con chimichurri",
      descripcion: "Pechuga marinada en cítricos, papa criolla salteada, brócoli asado, chimichurri fresco de perejil y ajo.",
      precio: 32000, foto: "assets/p-pechuga.jpg", tags: [],
      alergenos: "—",
      stats: [["610", "Cal"], ["46g", "Proteína"], ["16", "Min"]],
    },
    {
      id: 12, categoria: "asador", nombre: "Trucha entera a la leña",
      descripcion: "Trucha de páramo, hierbas frescas, limón asado, mantequilla de ajo, espinaca salteada, almendras tostadas.",
      precio: 38000, foto: "assets/p-trucha.jpg", tags: [],
      alergenos: "Contiene pescado, lácteos, frutos secos",
      stats: [["520", "Cal"], ["44g", "Proteína"], ["18", "Min"]],
    },

    // ---------------- Bebidas ----------------
    {
      id: 13, categoria: "bebidas", nombre: "Limonada de coco",
      descripcion: "Limón criollo exprimido al momento, leche de coco, hierbabuena fresca, hielo triturado.",
      precio: 10000, foto: "assets/p-limonada.jpg", tags: [],
      alergenos: "—",
      stats: [["210", "Cal"], ["16", "Onzas"], ["3", "Min"]],
    },
    {
      id: 14, categoria: "bebidas", nombre: "Agua de panela con limón",
      descripcion: "Panela de trapiche, limón criollo, servida bien fría. Receta de la abuela, sin azúcar añadida.",
      precio: 8000, foto: "assets/p-panela.jpg", tags: [],
      alergenos: "—",
      stats: [["120", "Cal"], ["16", "Onzas"], ["2", "Min"]],
    },
    {
      id: 15, categoria: "bebidas", nombre: "Jugo natural del día",
      descripcion: "Fruta de temporada exprimida al momento. Pregúntale a tu mesero por la fruta de hoy.",
      precio: 9000, foto: "assets/p-jugo.jpg", tags: [],
      alergenos: "—",
      stats: [["150", "Cal"], ["12", "Onzas"], ["3", "Min"]],
    },
    {
      id: 16, categoria: "bebidas", nombre: "Cerveza artesanal",
      descripcion: "Producción local de Bogotá, rotación de temporada. Consulta la variedad disponible hoy.",
      precio: 12000, foto: "assets/p-cerveza.jpg", tags: [],
      alergenos: "Contiene gluten",
      stats: [["180", "Cal"], ["330", "ml"], ["5.2", "% Alc"]],
    },

    // ---------------- Postres ----------------
    {
      id: 17, categoria: "postres", nombre: "Flan de café",
      descripcion: "Café de origen del Huila, caramelo salado, crema de leche, toque de vainilla natural.",
      precio: 14000, foto: "assets/p-flan.jpg", tags: ["vegetariano"],
      alergenos: "Contiene lácteos, huevo",
      stats: [["340", "Cal"], ["1", "Porción"], ["5", "Min"]],
    },
    {
      id: 18, categoria: "postres", nombre: "Brownie con helado",
      descripcion: "Chocolate 70% del Chocó, helado de vainilla natural, nueces caramelizadas, salsa tibia de chocolate.",
      precio: 16000, foto: "assets/p-brownie.jpg", tags: ["vegetariano"],
      alergenos: "Contiene lácteos, huevo, gluten, frutos secos",
      stats: [["580", "Cal"], ["1", "Porción"], ["6", "Min"]],
    },
    {
      id: 19, categoria: "postres", nombre: "Torta de zanahoria con un nombre bastante largo para probar el diseño",
      descripcion: "Zanahoria fresca, especias de canela y nuez moscada, queso crema batido, nuez pecana. Ítem de prueba con nombre extenso a propósito.",
      precio: 13000, foto: "assets/p-torta.jpg", tags: ["vegetariano"],
      alergenos: "Contiene lácteos, huevo, gluten, frutos secos",
      stats: [["460", "Cal"], ["1", "Porción"], ["4", "Min"]],
    },
  ],
};
