#!/usr/bin/env python3
"""
Candado: en las pantallas de pago (exito y fallo) ningun boton queda debajo de la barra
de abajo (tab-bar) ni del boton + (FAB).

Por que existe: el 17-sep-2026 (v204) esas pantallas recuperaron su display:flex y el
espaciador flex:1 empujo "Empezar a usar" y "Volver a planes" al fondo, debajo de la
barra. Las fotos lo mostraban y nadie lo vio hasta que Alvaro lo marco.

USO:  python tools/qa-botones-sobre-barra.py [carpeta-pwa]   Sale 1 si algun boton queda tapado.
"""
import sys, os, socket, threading, http.server, functools
from playwright.sync_api import sync_playwright

TOOLS = os.path.dirname(os.path.abspath(__file__))
PWA_DIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(TOOLS)
EMAIL, PASS = "demo@zepo.test", "ZepoDemo2026!"
PANTALLAS = ["pay-success", "pay-failed"]

LOGIN_JS = """async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}"""

MIDE_JS = """async (tab) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showWelcomeCarousel = false; c.showOnbV2 = false; if (c.coach) c.coach.open = false;
  c.tab = tab;
  await new Promise(r => setTimeout(r, 600));
  const pant = [...document.querySelectorAll('[x-show]')].find(e => e.getAttribute('x-show') === "tab === '" + tab + "'");
  const tapas = [...document.querySelectorAll('.tab-bar, .fab')].filter(e => getComputedStyle(e).display !== 'none')
    .map(e => e.getBoundingClientRect()).filter(r => r.height > 0);
  const techo = Math.min(...tapas.map(r => r.top));
  return [...pant.querySelectorAll('button')].filter(b => b.offsetParent)
    .map(b => { const r = b.getBoundingClientRect(); return {txt: b.textContent.trim(), bottom: Math.round(r.bottom), techo: Math.round(techo)}; });
}"""


def serve():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}/index.html"


def main():
    base = serve(); fallas = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 390, "height": 844}, service_workers="block").new_page()
        page.goto(base, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [EMAIL, PASS])
        if err: raise SystemExit(f"[FALLA] login: {err}")
        page.wait_for_function("()=>!!window.Alpine.$data(document.querySelector('#app')).user", timeout=20000)
        page.wait_for_timeout(1500)
        for tab in PANTALLAS:
            botones = page.evaluate(MIDE_JS, tab)
            if not botones:
                print(f"[FALLA] {tab}: no hay botones visibles"); fallas += 1; continue
            for x in botones:
                ok = x["bottom"] <= x["techo"]
                fallas += not ok
                print(f"{'OK   ' if ok else '[FALLA]'} {tab} · «{x['txt']}» termina en {x['bottom']} px, la barra empieza en {x['techo']} px")
        b.close()
    print(f"=== RESULTADO: {'TODO OK' if not fallas else str(fallas) + ' boton(es) tapados'} ===")
    sys.exit(1 if fallas else 0)


main()
