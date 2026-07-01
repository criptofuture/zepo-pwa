#!/usr/bin/env python3
"""
QA E2E REAL: Patrimonio -> Ahorro acumulado (lifetimeSavings) + Patrimonio total.
Login max. Mide el ahorro; siembra 1 ingreso (+123.45) y 1 gasto (23.45) en un mes
VIEJO (fuera de la ventana de 2 meses de loadExpenses); verifica que:
  - lifetimeSavings sube exactamente por el delta (+100.00) -> usa TODO el historial
  - esos registros viejos NO estan en la ventana c.expenses -> no es solo el mes
  - patTotalWithSavings == patNetWorth + lifetimeSavings
Limpia los sembrados. Sale 1 si algo falla.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL, PASS = "max@zepo.test", "ZepoQA2026!"
TAG = "PATSAV_" + str(int(time.time()))

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

MEASURE_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.loadLifetimeSavings();
  return { L: c.lifetimeSavings, N: c.patNetWorth, T: c.patTotalWithSavings, loaded: c.lifetimeSavingsLoaded };
}
"""

# Siembra 1 registro via saveExpense (parsedItems vacio + no split => camino de insert unico
# usando el form). Devuelve el id que quedo en c.expenses (unshift optimista).
SEED_ONE_JS = """
async ([tag, amount, isIncome, cat]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const d = new Date(); d.setMonth(d.getMonth()-5); d.setDate(1);
  const oldDate = d.toISOString().slice(0,10);
  c.editingExpense=null; c.editingBatch=null; c.parsedItems=[]; c.recurringOn=false;
  c.form = { amount:String(amount), description:tag, category:cat, date:oldDate,
    is_income:isIncome, is_split:false, split_persona:'', split_pct:'', split_people:[],
    payment_method:'', space_id: (c._currentSpaceId ? c._currentSpaceId() : null) };
  await c.saveExpense();
  const row = (c.expenses||[]).find(e => (e.description||'')===tag);
  return { id: row ? row.id : null, oldDate };
}
"""

# Saca los sembrados de la ventana local (c.expenses) a proposito. Asi, si lifetimeSavings
# SIGUE contandolos, es porque consulta la BD (todo el historial), no la ventana de 2 meses.
# (El fix "save-twice" preserva inserts recientes <120s en la ventana pese a su fecha vieja,
#  por eso no basta con loadExpenses para sacarlos: se quitan a mano.)
REMOVE_SEEDS_JS = """
async ([ids, tag]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.expenses = (c.expenses||[]).filter(e => !ids.includes(e.id));
  return { windowCount: (c.expenses||[]).filter(e => (e.description||'').startsWith(tag)).length };
}
"""

DELETE_ONE_JS = """
async ([id]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.askConfirm = () => Promise.resolve(true);
  c.editingExpense = { id }; c.sheetOpen = true;
  await c.deleteExpense();
  return true;
}
"""

def run(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [EMAIL, PASS])
        if err: print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)
        m0 = page.evaluate(MEASURE_JS)
        s1 = page.evaluate(SEED_ONE_JS, [TAG+" inc", 123.45, True, "other_income"]); page.wait_for_timeout(1500)
        s2 = page.evaluate(SEED_ONE_JS, [TAG+" exp", 23.45, False, "other"]);        page.wait_for_timeout(1500)
        win = page.evaluate(REMOVE_SEEDS_JS, [[s1.get("id"), s2.get("id")], TAG]); page.wait_for_timeout(300)
        m1 = page.evaluate(MEASURE_JS)
        # cleanup
        for sid in [s1.get("id"), s2.get("id")]:
            if sid: page.evaluate(DELETE_ONE_JS, [sid]); page.wait_for_timeout(800)
        m2 = page.evaluate(MEASURE_JS)
        browser.close()

    delta = round(m1["L"] - m0["L"], 2)
    restored = round(m2["L"] - m0["L"], 2)
    checks = [
        ("loaded=true tras cargar", m1["loaded"] is True),
        ("lifetimeSavings es numero", isinstance(m1["L"], (int, float))),
        ("sembrados fuera de la ventana local (windowCount=0)", win.get("windowCount") == 0),
        ("lifetimeSavings AUN cuenta +100 (lee de BD, no de la ventana)", abs(delta - 100.00) < 0.02),
        ("patTotalWithSavings == patNetWorth + lifetimeSavings", abs(m1["T"] - (m1["N"] + m1["L"])) < 0.005),
        ("cleanup: ahorro vuelve al inicial", abs(restored) < 0.02),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E Patrimonio: ahorro acumulado + total ===")
    print(f"  L0={m0['L']}  L1={m1['L']}  delta={delta}  N={m1['N']}  T={m1['T']}  windowCount={win.get('windowCount')}  restored={restored}")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - ahorro acumulado usa todo el historial + total correcto" if ok
                  else "FALLO - revisar loadLifetimeSavings / patTotalWithSavings"))
    sys.exit(0 if ok else 1)
