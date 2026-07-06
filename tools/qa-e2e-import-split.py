#!/usr/bin/env python3
"""
QA E2E REAL: importar archivo/PDF -> quitar items -> dividir usa la suma RESTANTE.

Regresion (Alvaro, 2026-07-06): tras importar un PDF y borrar algunos items, "Dividir"
repartia sobre la suma ORIGINAL, no sobre lo que quedaba. Causa: el boton "Quitar" de la
lista de importados hacia splice() sin recalcular form.amount (el total que consume el
split). Este test ejerce el boton REAL del DOM y las funciones reales del componente.

login demo. Sale 1 si falla.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"

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

# Simula la IMPORTACION real: usa _finalizeImportItems (arma parsedItems + fija form.amount)
SETUP_IMPORT_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.coachTip = ()=>{}; c.coachKey = null;  // fuera overlays que tapan
  c.userPlan = 'elite';                 // importar es Elite; el split es Pro+
  c.editingExpense = null; c.editingBatch = null; c.receiptPreview = null;
  c.form = { amount:'', description:'', category:'', date:new Date().toISOString().slice(0,10),
             is_income:false, is_split:false, split_persona:'', split_pct:'', split_people:[],
             payment_method:'', space_id:null };
  c.importedFile = { name:'estado.pdf', ext:'PDF', meta:'12 KB' };
  c._finalizeImportItems([
    { description:'Supermaxi',   amount:10, category:'food',      is_income:false },
    { description:'Uber viaje',  amount:20, category:'transport', is_income:false },
    { description:'Farmacia Fybeca', amount:30, category:'other', is_income:false },
  ]);
  c.sheetOpen = true;
  return { n: c.parsedItems.length, amount: c.form.amount };
}
"""

READ_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const you = (c.form.split_people||[]).find(p=>p.you) || null;
  const other = (c.form.split_people||[]).find(p=>!p.you) || null;
  return {
    n: c.parsedItems.length,
    sum: c.parsedItems.reduce((s,p)=>s+(parseFloat(p.amount)||0),0),
    amount: parseFloat(c.form.amount)||0,
    isSplit: !!c.form.is_split,
    youAmt: you ? you.amt : null,
    otherAmt: other ? other.amt : null,
  };
}
"""

TOGGLE_SPLIT_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.toggleSplit();          // crea Tu 50 / otro 50
  c._syncSplitAmts();       // lo que hace el x-init al renderizar las filas
  return true;
}
"""

def run(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(1500)

        checks = []

        # ── ESCENARIO A: borrar (boton real) ANTES de dividir ──
        imp = page.evaluate(SETUP_IMPORT_JS)
        checks.append(("Import: 3 items, total = 60.00", imp["n"] == 3 and imp["amount"] == "60.00"))
        # la lista de importados debe renderizar sus botones "Quitar"
        page.wait_for_selector('[title="Quitar"]:visible', state="visible", timeout=8000)
        # clic REAL en el "Quitar" del 2do item (Uber, 20)
        page.locator('[title="Quitar"]:visible').nth(1).click()
        page.wait_for_timeout(400)
        st = page.evaluate(READ_JS)
        checks.append(("Tras Quitar (boton real): quedan 2 items", st["n"] == 2))
        checks.append(("Tras Quitar: form.amount = suma restante (40)", abs(st["amount"] - 40) < 0.001 and abs(st["sum"] - 40) < 0.001))
        # ahora dividir 50/50 -> mi parte debe ser 20 (de 40), NO 30 (de 60)
        page.evaluate(TOGGLE_SPLIT_JS)
        st = page.evaluate(READ_JS)
        checks.append(("Dividir 50/50 usa la suma RESTANTE (mi parte = 20)", st["youAmt"] == 20 and st["otherAmt"] == 20))

        # ── ESCENARIO B: dividir ON, luego borrar -> reparto se recalcula solo ──
        page.evaluate(SETUP_IMPORT_JS)  # reset a 3 items / 60
        page.evaluate(TOGGLE_SPLIT_JS)  # split 50/50 -> mi parte 30
        st = page.evaluate(READ_JS)
        pre_ok = st["isSplit"] and st["youAmt"] == 30
        page.wait_for_selector('[title="Quitar"]:visible', state="visible", timeout=8000)
        page.locator('[title="Quitar"]:visible').nth(0).click()  # quita Supermaxi (10) -> quedan 50
        page.wait_for_timeout(400)
        st = page.evaluate(READ_JS)
        checks.append(("Split ON + Quitar: reparto se recalcula solo (mi parte 25 de 50)",
                       pre_ok and st["amount"] == 50 and st["youAmt"] == 25 and st["otherAmt"] == 25))

        browser.close()

    ok = all(v for _, v in checks)
    print("\n=== E2E Importar + Quitar + Dividir (suma restante) ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - dividir reparte sobre la suma que queda tras quitar items" if ok
                  else "FALLO - dividir sigue usando la suma original"))
    sys.exit(0 if ok else 1)
