"""
Capturas y medicion responsive para la Guia Practica N.5.

Recorre las cuatro vistas elegidas en los tres tamanos que pide la guia, mas
la orientacion horizontal del telefono. De cada una guarda la imagen y las
medidas (desborde, texto cortado, toques por debajo de 44 px).

    python capturas_responsive.py

Requiere el backend en :8000 y el frontend en :5173, y datos cargados con
`python manage.py poblar_demo`.
"""

import json
import os
import pathlib
import sys

import django
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"


def token_de_admin():
    """
    El token se pide a la base, no se escribe aqui. Dejarlo en el archivo lo
    convertiria en una credencial suelta dentro del repositorio.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nucleo.settings")
    django.setup()
    from django.contrib.auth.models import User
    from rest_framework.authtoken.models import Token
    usuario = User.objects.filter(is_superuser=True).first()
    if usuario is None:
        raise SystemExit("No hay administrador en la base.")
    return Token.objects.get_or_create(user=usuario)[0].key
SALIDA = pathlib.Path(__file__).resolve().parents[1] / "Entregables" / "04_WEB_MOVIL_RESPONSIVE"

VISTAS = [
    ("libro", "/mesero/libro", "Libro de caja"),
    ("salon", "/mesero/salon", "Salon"),
    ("ventas", "/mesero/ventas", "Historial de ventas"),
    ("admin-menu", "/admin/menu", "Administracion del menu"),
]

TAMANOS = [
    # 320 es el suelo declarado en SPEC-022: iPhone SE de primera generacion.
    ("smartphone-320", 320, 568, "03_Diseno_Smartphone"),
    ("smartphone", 375, 812, "03_Diseno_Smartphone"),
    ("tablet", 768, 1024, "04_Diseno_Tablet"),
    ("escritorio", 1366, 768, "05_Diseno_Desktop"),
    ("horizontal", 812, 375, "07_Comparacion"),
]

# El mismo diagnostico de SPEC-022. Se repite aqui para que el script sea
# autosuficiente: quien lo corra no necesita pegar nada en la consola.
DIAGNOSTICO = """
() => {
  const d = document.documentElement, W = d.clientWidth;
  const memo = new Map();
  const oculto = (e) => {
    if (!e || e === document.body) return false;
    if (memo.has(e)) return memo.get(e);
    const s = getComputedStyle(e);
    const propio = s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0'
      || (s.transform && s.transform !== 'none' && !/^matrix\\(1, 0, 0, 1,/.test(s.transform));
    const r = propio || oculto(e.parentElement);
    memo.set(e, r); return r;
  };
  const desc = (e) => {
    const c = [...e.classList].slice(0, 3).join('.');
    const t = (e.innerText || '').trim().replace(/\\s+/g, ' ').slice(0, 40);
    return `${e.tagName.toLowerCase()}${c ? '.' + c : ''}${t ? ` "${t}"` : ''}`;
  };
  const todos = [...document.querySelectorAll('body *')]
    .filter((e) => !oculto(e) && e.getBoundingClientRect().height > 0);
  const cortado = todos.filter((e) => {
    if (e.children.length) return false;
    const s = getComputedStyle(e);
    if (s.overflowX === 'auto' || s.overflowX === 'scroll') return false;
    return e.scrollWidth > e.clientWidth + 1 && (e.textContent || '').trim().length > 0;
  }).map((e) => `${desc(e)} [${e.clientWidth}<${e.scrollWidth}]`);
  const blanco = (e) => (e.type === 'checkbox' || e.type === 'radio') ? (e.closest('label,span') || e) : e;
  const enLinea = (e) => e.tagName === 'A' && getComputedStyle(e).display === 'inline';
  const toc = todos
    .filter((e) => /^(BUTTON|A|SELECT|INPUT|TEXTAREA)$/.test(e.tagName) && !enLinea(e))
    .map((e) => { const r = blanco(e).getBoundingClientRect(); return { h: r.height, w: r.width, d: desc(e) }; })
    .filter((x) => x.h > 0);
  const b44 = toc.filter((x) => x.h < 44 || x.w < 44);
  return {
    ancho: W,
    desborde: d.scrollWidth - W,
    cortados: cortado.length,
    ejemplos_cortados: cortado.slice(0, 5),
    tocables: toc.length,
    bajo44: b44.length,
    minimo: b44.length ? Math.round(Math.min(...b44.map((x) => Math.min(x.h, x.w)))) : null,
    peores: b44.sort((a, b) => Math.min(a.h, a.w) - Math.min(b.h, b.w)).slice(0, 3)
      .map((x) => `${x.d} ${Math.round(x.w)}x${Math.round(x.h)}`),
    texto: document.body.innerText.length,
  };
}
"""


def main():
    TOKEN = token_de_admin()
    medidas = []
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        for clave, ruta, titulo in VISTAS:
            for nombre, ancho, alto, carpeta in TAMANOS:
                # Contexto nuevo por captura: asi el ancho se aplica desde la
                # carga y no al encoger una ventana grande, que deja medidas
                # viejas en los componentes que observan su tamano.
                ctx = navegador.new_context(viewport={"width": ancho, "height": alto},
                                            device_scale_factor=2)
                pagina = ctx.new_page()
                pagina.goto(BASE, wait_until="domcontentloaded")
                pagina.evaluate(
                    "([t, p]) => { localStorage.setItem('terra_admin_token', t);"
                    " localStorage.setItem('terra_perfil', p); }",
                    [TOKEN, json.dumps({"usuario": "admin", "rol": "admin"})])
                pagina.goto(BASE + ruta, wait_until="networkidle")
                pagina.wait_for_timeout(2500)

                destino = SALIDA / carpeta / f"{clave}_{nombre}.png"
                pagina.screenshot(path=str(destino), full_page=True)

                m = pagina.evaluate(DIAGNOSTICO)
                m.update({"vista": titulo, "archivo": destino.name, "tamano": nombre})
                medidas.append(m)
                print(f"  {titulo:26} {nombre:11} {ancho}x{alto}  "
                      f"desborde={m['desborde']:<4} cortados={m['cortados']:<3} "
                      f"bajo44={m['bajo44']}/{m['tocables']}")
                ctx.close()
        navegador.close()

    reporte = SALIDA / "01_Diagnostico_Responsive" / "mediciones.json"
    reporte.write_text(json.dumps(medidas, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nMedidas guardadas en {reporte}")
    malas = [m for m in medidas if m["desborde"] > 0 or m["cortados"] > 0 or m["bajo44"] > 0]
    print("Con hallazgos:", len(malas), "de", len(medidas))
    for m in malas:
        print("  -", m["vista"], m["tamano"], m["peores"] or m["ejemplos_cortados"])
    return 0 if not malas else 1


if __name__ == "__main__":
    sys.exit(main())
