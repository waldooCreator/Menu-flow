import jsQR from "jsqr";

/**
 * Decodifica un QR desde un archivo de imagen (input type="file").
 *
 * Nota de alcance (ADR-005): en producción el escaneo por cámara debe usar
 * una librería como `qr-scanner`, porque Safari/iOS no soporta
 * `BarcodeDetector`. Esta vía de "subir imagen" es un camino real (el
 * cliente puede mostrar el QR desde una laptop) y además es la que se
 * puede probar de punta a punta sin cámara física.
 */
export function decodificarImagen(file) {
  return cargarImagen(file).then((img) => {
    const canvas = document.createElement("canvas");
    canvas.width = img.width;
    canvas.height = img.height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);
    const { data, width, height } = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const resultado = jsQR(data, width, height);
    return resultado ? resultado.data : null;
  });
}

function cargarImagen(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}
