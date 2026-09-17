/**
 * Prueba técnica del QR de pedido (SPEC-002 / ADR-001).
 *
 * No es investigación de escritorio: genera QR reales con el formato exacto
 * de la spec, los renderiza a píxeles, los decodifica con una librería de
 * escaneo real (jsQR — la misma familia que usa `qr-scanner`, la elegida en
 * ADR-005) y verifica la firma HMAC. Mide tamaños, versión de QR, tiempos y
 * robustez ante degradación (simulando una foto de cámara imperfecta).
 *
 * En producción la firma la hace Django (el secreto vive solo en el
 * servidor, ADR-001) — aquí se firma en el mismo proceso solo para poder
 * medir el pipeline completo sin levantar el backend.
 */

const crypto = require("crypto");
const QRCode = require("qrcode");
const { PNG } = require("pngjs");
const jsQR = require("jsqr");

const SECRETO_DEMO = "secreto-solo-para-esta-prueba-nunca-en-produccion";

// ---------------------------------------------------------------------
// 1. Payload — mismo formato que SPEC-002
// ---------------------------------------------------------------------

function base64url(buf) {
  return buf.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function construirPayload(mesa, cliente, items) {
  return {
    v: 1,
    j: crypto.randomBytes(4).toString("hex"), // id corto del QR, anti-duplicado
    ts: Math.floor(Date.now() / 1000),
    m: mesa,
    c: cliente,
    i: items, // [[id, cantidad, observacion], ...]
  };
}

function firmarYCodificar(payload) {
  const json = JSON.stringify(payload);
  const payloadB64 = base64url(Buffer.from(json, "utf8"));
  const firma = crypto.createHmac("sha256", SECRETO_DEMO).update(payloadB64).digest();
  const firmaB64 = base64url(firma).slice(0, 16); // firma truncada, igual que el ejemplo de la spec
  const texto = `${payloadB64}.${firmaB64}`;
  return { json, payloadB64, firmaB64, texto };
}

function verificarYDecodificar(texto) {
  const [payloadB64, firmaRecibida] = texto.split(".");
  const firmaEsperada = base64url(
    crypto.createHmac("sha256", SECRETO_DEMO).update(payloadB64).digest()
  ).slice(0, 16);

  // Comparación en tiempo constante — evita filtrar la firma por timing.
  const ok =
    firmaRecibida.length === firmaEsperada.length &&
    crypto.timingSafeEqual(Buffer.from(firmaRecibida), Buffer.from(firmaEsperada));

  if (!ok) return { valido: false };

  const json = Buffer.from(
    payloadB64.replace(/-/g, "+").replace(/_/g, "/"),
    "base64"
  ).toString("utf8");
  return { valido: true, payload: JSON.parse(json) };
}

// ---------------------------------------------------------------------
// 2. Carritos de prueba — realistas, tomados del menú real del prototipo
// ---------------------------------------------------------------------

const CARRITOS = {
  "pequeño (3 items, sin obs.)": [
    [1, 2, ""], [9, 1, ""], [13, 2, ""],
  ],
  "típico (8 items, obs. cortas)": [
    [1, 1, "sin sal"], [3, 2, "picante"], [5, 1, ""], [6, 2, "sin cebolla"],
    [9, 1, "término medio"], [13, 3, ""], [16, 2, ""], [18, 1, ""],
  ],
  "grande (15 items, obs. cortas)": Array.from({ length: 15 }, (_, i) => [
    (i % 19) + 1, (i % 3) + 1, i % 4 === 0 ? "sin cebolla" : "",
  ]),
  "muy grande (30 items, obs. largas)": Array.from({ length: 30 }, (_, i) => [
    (i % 19) + 1, (i % 3) + 1,
    i % 2 === 0 ? "sin cebolla, poca sal, para compartir" : "término medio, sin picante",
  ]),
  "estrés (50 items, obs. largas)": Array.from({ length: 50 }, (_, i) => [
    (i % 19) + 1, (i % 3) + 1,
    "una observación bastante larga para forzar el límite de tamaño del QR",
  ]),
};

// ---------------------------------------------------------------------
// 3. Render a píxeles reales + decodificación con jsQR
// ---------------------------------------------------------------------

async function renderizarAPixeles(texto, escalaPxPorModulo) {
  const buffer = await QRCode.toBuffer(texto, {
    errorCorrectionLevel: "M",
    scale: escalaPxPorModulo,
    margin: 2,
  });
  const png = PNG.sync.read(buffer);
  return png; // {width, height, data: RGBA Buffer}
}

function decodificar(png) {
  const rgba = new Uint8ClampedArray(png.data);
  const resultado = jsQR(rgba, png.width, png.height);
  return resultado ? resultado.data : null;
}

/** Simula una foto de cámara imperfecta: ruido + desenfoque de caja 3x3. */
function degradar(png, intensidadRuido = 22) {
  const { width: w, height: h, data } = png;
  const salida = Buffer.from(data); // copia

  // Ruido por píxel
  for (let i = 0; i < salida.length; i += 4) {
    const n = (Math.random() - 0.5) * intensidadRuido;
    salida[i] = clamp(salida[i] + n);
    salida[i + 1] = clamp(salida[i + 1] + n);
    salida[i + 2] = clamp(salida[i + 2] + n);
  }

  // Desenfoque de caja 3x3
  const copia = Buffer.from(salida);
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      for (let c = 0; c < 3; c++) {
        let suma = 0;
        for (let dy = -1; dy <= 1; dy++) {
          for (let dx = -1; dx <= 1; dx++) {
            suma += copia[((y + dy) * w + (x + dx)) * 4 + c];
          }
        }
        salida[(y * w + x) * 4 + c] = Math.round(suma / 9);
      }
    }
  }

  return { ...png, data: salida };
}

function clamp(v) {
  return v < 0 ? 0 : v > 255 ? 255 : v;
}

// ---------------------------------------------------------------------
// 4. Ejecutar la prueba completa
// ---------------------------------------------------------------------

async function main() {
  console.log("=".repeat(78));
  console.log("PRUEBA TÉCNICA — QR de pedido autocontenido y firmado (SPEC-002 / ADR-001)");
  console.log("=".repeat(78));
  console.log();

  const resultados = [];

  for (const [nombre, items] of Object.entries(CARRITOS)) {
    const t0 = process.hrtime.bigint();

    const payload = construirPayload("x7f2q9", "Walter", items);
    const { texto } = firmarYCodificar(payload);
    const tFirma = process.hrtime.bigint();
    const bytes = Buffer.byteLength(texto, "utf8");

    // --- Generar QR y medir versión/capacidad ---
    // Si el payload excede la capacidad del QR, es justo el caso que activa
    // el "Plan B" de SPEC-002 (carrito temporal + token corto). Se reporta
    // como hallazgo, no como fallo de la prueba.
    let qrData;
    try {
      qrData = QRCode.create(texto, { errorCorrectionLevel: "M" });
    } catch (err) {
      resultados.push({
        carrito: nombre, items: items.length, caracteres: texto.length, bytes,
        version_qr: "—", modulos: "—",
        cabe_en_900b: bytes <= 900 ? "sí" : "NO",
        decodifica_limpio: "—", decodifica_degradado: "—", firma_valida: "—",
        ms_firmar: "—", ms_generar_y_renderizar: "—", ms_decodificar: "—", ms_total: "—",
      });
      console.log(
        `  [${nombre}] EXCEDE la capacidad del QR (${bytes} bytes) -> ` +
        `dispara el Plan B de SPEC-002 (carrito temporal + token corto)`
      );
      continue;
    }
    const version = qrData.version;
    const modulos = qrData.modules.size;

    // --- Render a una resolución "de pantalla de celular" (scale 8) ---
    const png = await renderizarAPixeles(texto, 8);
    const tRender = process.hrtime.bigint();

    // --- Decodificar limpio ---
    const decodificadoLimpio = decodificar(png);
    const okLimpio = decodificadoLimpio === texto;
    const tDecodeLimpio = process.hrtime.bigint();

    // --- Decodificar degradado (simula foto de cámara) ---
    const pngDegradado = degradar(png);
    const decodificadoDegradado = decodificar(pngDegradado);
    const okDegradado = decodificadoDegradado === texto;

    // --- Verificar firma sobre el resultado decodificado ---
    const verificacion = decodificadoLimpio
      ? verificarYDecodificar(decodificadoLimpio)
      : { valido: false };

    const tFin = process.hrtime.bigint();
    const ms = (n) => Number(n) / 1e6;

    resultados.push({
      carrito: nombre,
      items: items.length,
      caracteres: texto.length,
      bytes,
      version_qr: version,
      modulos: `${modulos}×${modulos}`,
      cabe_en_900b: bytes <= 900 ? "sí" : "NO — usar plan B",
      decodifica_limpio: okLimpio ? "sí" : "NO",
      decodifica_degradado: okDegradado ? "sí" : "no",
      firma_valida: verificacion.valido ? "sí" : "NO",
      ms_firmar: ms(tFirma - t0).toFixed(2),
      ms_generar_y_renderizar: ms(tRender - tFirma).toFixed(2),
      ms_decodificar: ms(tDecodeLimpio - tRender).toFixed(2),
      ms_total: ms(tFin - t0).toFixed(2),
    });

    if (verificacion.valido) {
      const primerItem = verificacion.payload.i[0];
      console.log(
        `  [${nombre}] payload recuperado OK — mesa=${verificacion.payload.m}, ` +
        `${verificacion.payload.i.length} items, primer item=${JSON.stringify(primerItem)}`
      );
    } else {
      console.log(`  [${nombre}] *** FALLÓ LA VERIFICACIÓN ***`);
    }
  }

  console.log();
  console.log("-".repeat(78));
  console.table(resultados);

  // --- Prueba aparte: firma alterada debe rechazarse ---
  console.log("Prueba de manipulación — firma alterada debe rechazarse:");
  const payload = construirPayload("x7f2q9", "Test", [[1, 1, ""]]);
  const { texto } = firmarYCodificar(payload);
  const [p, f] = texto.split(".");
  const textoAlterado = `${p}.${f.slice(0, -1)}X`; // se cambia el último carácter de la firma
  const resultadoAlterado = verificarYDecodificar(textoAlterado);
  console.log(`  Firma alterada -> valido=${resultadoAlterado.valido} (debe ser false)`);
  console.log();

  // --- Prueba aparte: umbral mínimo de tamaño en pantalla ---
  console.log("Umbral de tamaño en pantalla — decodificación limpia a distintas escalas:");
  const textoMedio = firmarYCodificar(
    construirPayload("x7f2q9", "Walter", CARRITOS["típico (8 items, obs. cortas)"])
  ).texto;
  for (const escala of [1, 2, 3, 4, 6, 8]) {
    const png = await renderizarAPixeles(textoMedio, escala);
    const ok = decodificar(png) === textoMedio;
    console.log(
      `  scale=${escala} (${png.width}×${png.height}px) -> decodifica: ${ok ? "sí" : "NO"}`
    );
  }
}

// ---------------------------------------------------------------------
// 5. Experimento: ¿cuánto se ahorra codificando las observaciones rápidas
//    como índice en vez de texto completo? (SPEC-003 ya las modela como
//    lista configurable `ObservacionRapida` — esto las aprovecha en el QR.)
// ---------------------------------------------------------------------

const OBSERVACIONES_RAPIDAS = ["Sin cebolla", "Sin picante", "Poca sal", "Sin cilantro", "Para compartir"];

async function experimentoObservacionesCortas() {
  console.log();
  console.log("-".repeat(78));
  console.log("Experimento — observaciones como índice de ObservacionRapida vs. texto libre:");

  // Mismo carrito "muy grande" (30 items), pero cada observación se expresa
  // como índices a OBSERVACIONES_RAPIDAS (p.ej. "02" = índices 0 y 2) en vez
  // de la frase completa.
  const itemsTexto = CARRITOS["muy grande (30 items, obs. largas)"];
  const itemsIndice = itemsTexto.map(([id, cant], i) => [
    id, cant, i % 2 === 0 ? "02" : "1", // combinaciones cortas de índices
  ]);

  const textoLibre = firmarYCodificar(construirPayload("x7f2q9", "Walter", itemsTexto)).texto;
  const textoIndice = firmarYCodificar(construirPayload("x7f2q9", "Walter", itemsIndice)).texto;

  const bTexto = Buffer.byteLength(textoLibre, "utf8");
  const bIndice = Buffer.byteLength(textoIndice, "utf8");

  console.log(`  Texto libre  : ${bTexto} bytes  (${bTexto <= 900 ? "cabe" : "NO cabe, plan B"})`);
  console.log(`  Por índice   : ${bIndice} bytes  (${bIndice <= 900 ? "cabe" : "NO cabe, plan B"})`);
  console.log(`  Reducción    : ${Math.round((1 - bIndice / bTexto) * 100)}%`);

  try {
    const qr = QRCode.create(textoIndice, { errorCorrectionLevel: "M" });
    console.log(`  QR por índice: versión ${qr.version} (${qr.modules.size}×${qr.modules.size}) — practico de escanear`);
  } catch {
    console.log("  QR por índice: tampoco cupo");
  }
}

main()
  .then(experimentoObservacionesCortas)
  .catch((err) => {
  console.error("ERROR EN LA PRUEBA:", err);
  process.exit(1);
});
