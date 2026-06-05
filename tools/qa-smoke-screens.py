#!/usr/bin/env python3
"""
QA SMOKE amplio: navega TODAS las pantallas con sesion real y verifica que NINGUNA
lanza error de consola / JS, que los getters de Dashboard no truenan en ninguna
combinacion periodo x modo, y que agregar/borrar categoria funciona.

Atrapa crashes/errores silenciosos en cualquier pantalla. login demo. Sale 1 si hay
errores de consola o si una combinacion del dashboard falla o categorias no funciona.
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

# Recorre tabs y combinaciones de dashboard; lee getters; reporta cualquier excepcion.
TOUR_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const errors = [];
  const read = (label, fn) => { try { const v = fn(); JSON.stringify(v); }
                                catch(e){ errors.push(label+': '+e.message); } };
  // tabs simples
  for (const t of ['home','history','cuentas','budgets','dash','settings']) {
    try { c.tab = t; } catch(e){ errors.push('tab '+t+': '+e.message); }
  }
  // cuentas sub-tabs + sus getters
  c.tab='cuentas';
  for (const ct of ['me-deben','debo','amigos']) {
    c.cuentasTab = ct;
    read('pendingCobrosGrouped@'+ct, ()=>c.pendingCobrosGrouped);
    read('deboDeudasGrouped@'+ct,    ()=>c.deboDeudasGrouped);
    read('incomeSplitDebts@'+ct,     ()=>c.incomeSplitDebts);
  }
  // historial
  c.tab='history';
  for (const ha of [false, true]) { c.histAll=ha;
    for (const ht of ['all','expense','income']) { c.histType=ht;
      read(`filteredHistoryGroups@${ha}/${ht}`, ()=>c.filteredHistoryGroups);
    }
  }
  // dashboard: periodo x modo
  c.tab='dash';
  for (const pr of ['semana','mes','año']) { c.dashPeriod=pr;
    for (const vm of ['expense','income','balance']) { c.dashViewMode=vm;
      read(`periodChart@${pr}/${vm}`,       ()=>c.periodChart);
      read(`yearlyChart@${pr}/${vm}`,       ()=>c.yearlyChart);
      read(`monthlyDayGrid@${pr}/${vm}`,    ()=>c.monthlyDayGrid);
      read(`categoryBreakdown@${pr}/${vm}`, ()=>c.categoryBreakdown);
      read(`periodChartSubtitle@${pr}/${vm}`,()=>c.periodChartSubtitle);
    }
  }
  return errors;
}
"""

CATEGORY_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.catManagerMode = 'expense';
  const label = 'QASMOKE_' + Math.floor(performance.now());
  c.newCatLabel = label; c.newCatEmoji = '🧪';
  c.addCategory();
  const added = c.categories.find(x => x.label === label);
  const key = added ? added.key : null;
  let removed = false;
  if (key) { c.removeCategory(key); removed = !c.categories.some(x=>x.key===key); }
  return { added: !!added, removed };
}
"""

def run(url):
    console_errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2500)
        console_errors.clear()   # ignorar ruido previo al login
        getter_errors = page.evaluate(TOUR_JS)
        cat = page.evaluate(CATEGORY_JS)
        page.wait_for_timeout(400)
        browser.close()

    # filtrar ruido conocido de red/recursos
    noise = ("favicon", "manifest", "ERR_", "Failed to load resource", "status of 4", "status of 5")
    real_console = [e for e in console_errors if not any(n in e for n in noise)]

    print("\n=== SMOKE de todas las pantallas ===")
    print(f"  errores de getters (dashboard/historial/cuentas): {len(getter_errors)}")
    for e in getter_errors[:10]: print("     - " + e)
    print(f"  errores de consola/JS al navegar: {len(real_console)}")
    for e in real_console[:10]: print("     - " + e)
    print(f"  categoria agregar/borrar: added={cat.get('added')} removed={cat.get('removed')}")
    ok = (not getter_errors) and (not real_console) and cat.get("added") and cat.get("removed")
    print("\n  [%s] sin errores y categorias OK" % ("PASS" if ok else "FALLA"))
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port=free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - todas las pantallas navegan sin errores" if ok
                  else "FALLO - hay errores al navegar/combinar pantallas"))
    sys.exit(0 if ok else 1)
