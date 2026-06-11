#!/usr/bin/env python3
"""
QA de teclado para la pantalla "Anadir registro" (Zepo PWA).

POR QUE EXISTE: el teclado movil real no se puede abrir headless (Web Speech /
foco nativo). PERO el layout de Zepo NO mira el teclado directamente: reacciona a
la variable CSS --vvh (altura visible), que init() sincroniza desde
window.visualViewport. Asi que para "simular el teclado" basta con FORZAR --vvh a
la altura que deja visible cada teclado (iOS / Android) y medir la geometria.

Esto reproduce de forma deterministica el bug que se colo a produccion:
con el teclado abierto o con "Dividir" expandido, los hijos de .approve-body se
COMPRIMIAN (flex-shrink:1) en vez de scrollear -> Aprobar tapaba "Dividir" y la
tarjeta de split se recortaba. El fix: .approve-body > * { flex-shrink: 0 }.

USO:
    python tools/qa-keyboard.py            # arranca server local y prueba
    python tools/qa-keyboard.py URL        # prueba una URL ya servida
Sale con codigo 1 si alguna asercion falla (apto para CI / pre-deploy).
"""
import sys, subprocess, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Perfiles: altura VISIBLE (px) que deja el teclado sobre un viewport dado.
# Valores tipicos medidos en dispositivos reales (viewport CSS, no fisico).
PROFILES = [
    # nombre,            viewport_w, viewport_h, vvh_con_teclado
    ("Sin teclado",          390,    844,    None),   # control: ningun recorte
    ("iPhone 14 (iOS)",      390,    844,    430),    # teclado iOS ~ deja 430px
    ("iPhone SE (iOS chico)",375,    667,    330),    # peor caso: pantalla corta
    ("Pixel 7 (Android)",    412,    915,    480),    # teclado Android ~ deja 480px
    ("Galaxy S (Android)",   360,    800,    400),
]

SETUP_JS = r"""
() => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.user = { id:'qa', email:'qa@zepo.test' };
  c.appReady = true; c.userPlan = 'elite'; c.tab = 'home'; c.sheetOpen = true;
  c.editingExpense = false; c.editingBatch = false;
  c.form.is_income = false; c.form.description = 'mercado';
  c.form.amount = '20.00'; c.form.category = 'groceries';
  c.parsedItems = [{description:'mercado',label:'mercado',emoji:'🛒',
                    color:'#84AF72',amount:20,category:'groceries',is_income:false}];
  c.analyzed = true; c.form.is_split = true;   // peor caso: split EXPANDIDO
  c.form.split_people = [
    { name:'Tu',  you:true,  pct:50, color:'#507D5A' },
    { name:'Bea', you:false, pct:50, color:'#7000FF' },
  ];
  return true;
}
"""

MEASURE_JS = r"""
(vvh) => {
  if (vvh) document.documentElement.style.setProperty('--vvh', vvh + 'px');
  const body  = document.querySelector('.approve-body');
  const kids   = [...body.children];
  const split = kids.find(d => d.textContent.includes('Dividir este gasto'));
  // Boton de guardar PRIMARIO *visible*: en el flujo normal vive ANCLADO en el header
  // del composer (.cd-save-inline); en edicion/recibo es el grande (.approve-btn).
  // offsetParent === null => display:none, lo saltamos (no es el visible).
  const apr   = [...body.querySelectorAll('.cd-save-inline, .approve-btn')]
                  .find(b => b.offsetParent !== null);
  const r = e => { const x = e.getBoundingClientRect();
                   return { t: Math.round(x.top), b: Math.round(x.bottom) }; };
  return {
    splitClipped: split.scrollHeight > split.clientHeight + 1,
    aprOverlapsDividir: apr ? (r(apr).t < r(split).b) : false,
    splitNatural: split.scrollHeight,
    splitShown: split.clientHeight,
    aprTop: apr ? r(apr).t : null,
    splitBottom: r(split).b,
  };
}
"""

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def run(url):
    ok = True
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, vw, vh, vvh in PROFILES:
            page = browser.new_context(viewport={"width": vw, "height": vh}).new_page()
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(900)            # Alpine init
            page.evaluate(SETUP_JS)
            page.wait_for_timeout(400)
            m = page.evaluate(MEASURE_JS, vvh)
            passed = (not m["splitClipped"]) and (not m["aprOverlapsDividir"])
            ok = ok and passed
            tag = "PASS" if passed else "FALLA"
            print(f"[{tag}] {name:<22} vvh={str(vvh):<5}  "
                  f"split recortado={m['splitClipped']}  "
                  f"Guardar tapa Dividir={m['aprOverlapsDividir']}  "
                  f"(split {m['splitShown']}/{m['splitNatural']}px · "
                  f"btnTop={m['aprTop']} splitBottom={m['splitBottom']})")
            page.context.close()
        browser.close()
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
        ok = run(url)
    else:
        port = free_port(); serve(port)
        time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - sin recortes ni overlaps en ningun teclado simulado"
                  if ok else "FALLO - hay recorte u overlap; revisa .approve-body"))
    sys.exit(0 if ok else 1)
