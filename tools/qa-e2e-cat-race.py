#!/usr/bin/env python3
"""
QA E2E REAL: carrera categoria manual vs IA tardia (bug v175).

Repro del bug que reporto Alvaro: al crear un registro cuyo parser local deja la
categoria en 'other', aiCategorizeFallback dispara un fetch a categorize-ai (hasta 5s).
Si el usuario elige categoria A MANO en ese lapso, la respuesta tardia PISABA su
eleccion. Fix v175: _catManual + re-chequeo "sigue siendo other" al llegar la respuesta.

Este test intercepta categorize-ai con 1.5s de retraso devolviendo 'transport':
  FASE A (bug): analiza texto desconocido -> CLIC REAL en la tile 'Comida' antes de que
                la IA responda -> espera la respuesta -> la categoria DEBE seguir 'food'
                y la tile seguir activa en el DOM.
  FASE B (control): mismo flujo SIN eleccion manual -> la IA SI debe aplicar 'transport'
                (el fallback sigue funcionando cuando nadie eligio).
No persiste nada (no se guarda el registro). Sale 1 si algo falla.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TS = str(int(time.time()))
AI_DELAY_MS = 1500

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

LOGIN_JS = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

START_JS = """
(desc) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.coachTip = ()=>{}; c.coachKey = null;  // fuera overlays que tapan
  c.openNew();
  c.form.description = desc;
  c.analyzeTextInput();
  return true;
}
"""

WAIT_PARSED = ("()=>{const c=window.Alpine.$data(document.querySelector('#app'));"
               "return (c.parsedItems||[]).length===1;}")

OPEN_GRID_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.editingParsedCatIdx = 0;
  return c.parsedItems[0].category;
}
"""

STATE_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const it = c.parsedItems[0] || {};
  return { category: it.category, label: it.label, manual: !!it._catManual };
}
"""

def run(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())

        ai_calls = {"n": 0}
        def slow_ai(route):
            ai_calls["n"] += 1
            time.sleep(AI_DELAY_MS / 1000)
            route.fulfill(status=200, content_type="application/json",
                          body='{"categories":["transport"]}')
        page.route("**/functions/v1/categorize-ai", slow_ai)

        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)

        # ── FASE A: eleccion manual DURANTE la espera de la IA ──
        page.evaluate(START_JS, f"qarace{TS} 7")
        page.wait_for_function(WAIT_PARSED, timeout=8000)
        cat_inicial = page.evaluate(OPEN_GRID_JS)
        # clic REAL en la tile 'Comida' del grid por-item (visible)
        tile = page.locator(".cd-cat-grid button.cd-cat-tile", has_text="Comida").locator("visible=true").first
        tile.click()
        mid = page.evaluate(STATE_JS)
        # deja llegar la respuesta tardia de la IA (1.5s + margen)
        page.wait_for_timeout(AI_DELAY_MS + 1500)
        fin = page.evaluate(STATE_JS)
        tile_activa = page.evaluate(
            """() => { const t=[...document.querySelectorAll('.cd-cat-grid button.cd-cat-tile')]
                 .filter(b=>b.offsetParent && b.textContent.includes('Comida'))[0];
               return t ? t.classList.contains('cd-cat-tile-active') : null; }""")

        # ── FASE B (control): sin eleccion manual, la IA SI aplica ──
        page.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
            c.parsedItems=[]; c.analyzed=false; c.editingParsedCatIdx=-1; }""")
        page.evaluate(START_JS, f"qactrl{TS} 9")
        page.wait_for_function(WAIT_PARSED, timeout=8000)
        page.wait_for_timeout(AI_DELAY_MS + 1500)
        ctrl = page.evaluate(STATE_JS)

        # limpieza local (nada se guardo en BD)
        page.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
            c.parsedItems=[]; c.sheetOpen=false; c.form.description=''; c.form.amount=''; }""")
        browser.close()

    checks = [
        ("parser local dejo 'other' (repro valida)",       cat_inicial == "other"),
        ("clic real selecciono 'food' al instante",        mid.get("category") == "food"),
        ("quedo marcada como eleccion manual",             mid.get("manual") is True),
        ("IA tardia NO piso la eleccion (sigue 'food')",   fin.get("category") == "food"),
        ("tile 'Comida' sigue activa en el DOM",           tile_activa is True),
        ("la IA fue llamada (interceptor activo)",         ai_calls["n"] >= 1),
        ("CONTROL: sin eleccion manual la IA SI aplica",   ctrl.get("category") == "transport"),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E carrera categoria manual vs IA tardia ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    if not ok:
        print(f"  debug: inicial={cat_inicial} mid={mid} fin={fin} ctrl={ctrl} calls={ai_calls['n']}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - la eleccion manual de categoria ya no es pisada por la IA tardia" if ok
                  else "FALLO - la carrera categoria manual vs IA sigue viva"))
    sys.exit(0 if ok else 1)
