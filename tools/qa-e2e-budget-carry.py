#!/usr/bin/env python3
"""
QA E2E REAL: herencia de presupuestos mes a mes.
login demo -> limpia mes actual -> siembra presupuesto del MES PASADO (via sb) ->
loadBudgets -> verifica que el mes actual HEREDA (500 total + 120 food, _inherited) ->
prueba respeta-cero (siembra centinela mes pasado) -> verifica que NO hereda ->
limpieza total. Sale 1 si falla.
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

# Limpia TODO presupuesto del espacio activo (mes actual y el mes pasado sembrado)
CLEAN_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const sf = c._currentSpaceId();
  const now = new Date();
  const pm = now.getMonth() === 0 ? 12 : now.getMonth();
  const py = now.getMonth() === 0 ? now.getFullYear()-1 : now.getFullYear();
  const cm = now.getMonth()+1, cy = now.getFullYear();
  // borra mes actual y mes pasado del espacio
  await sb.from('budgets').delete().eq('user_id', c.user.id).eq('space_id', sf).eq('month', cm).eq('year', cy);
  await sb.from('budgets').delete().eq('user_id', c.user.id).eq('space_id', sf).eq('month', pm).eq('year', py);
  return { sf, pm, py, cm, cy };
}
"""

# Siembra presupuesto del MES PASADO: total 500 + food 120
SEED_PREV_JS = """
async ([sf, pm, py]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await sb.from('budgets').insert([
    { user_id: c.user.id, category: null,   amount: 500, month: pm, year: py, space_id: sf },
    { user_id: c.user.id, category: 'food', amount: 120, month: pm, year: py, space_id: sf },
  ]);
  c.userPlan='elite'; c.spaceViewAll=false; c.activeSpaceId=sf;
  await c.loadBudgets();
  const total = (c.budgets||[]).find(b => !b.category);
  const food  = (c.budgets||[]).find(b => b.category==='food');
  return {
    totalAmt: total ? Number(total.amount) : null,
    totalInh: total ? !!total._inherited : null,
    foodAmt:  food ? Number(food.amount) : null,
    bars:     (c.budgetBars||[]).map(b => b.cat+':'+b.budget),
  };
}
"""

# Siembra CENTINELA (mes pasado puesto en cero) -> no debe heredar
SEED_ZERO_JS = """
async ([sf, pm, py]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  // limpia lo sembrado antes y pone SOLO centinela en el mes pasado
  await sb.from('budgets').delete().eq('user_id', c.user.id).eq('space_id', sf).eq('month', pm).eq('year', py);
  await sb.from('budgets').insert([
    { user_id: c.user.id, category: null, amount: 0, month: pm, year: py, space_id: sf },
  ]);
  await c.loadBudgets();
  return { count: (c.budgets||[]).length, bars: (c.budgetBars||[]).length };
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
        page.wait_for_timeout(2000)
        ctx = page.evaluate(CLEAN_JS); page.wait_for_timeout(1500)
        sf, pm, py = ctx["sf"], ctx["pm"], ctx["py"]
        inh = page.evaluate(SEED_PREV_JS, [sf, pm, py]); page.wait_for_timeout(1500)
        zero = page.evaluate(SEED_ZERO_JS, [sf, pm, py]); page.wait_for_timeout(1000)
        page.evaluate(CLEAN_JS)  # limpieza final
        browser.close()
    checks = [
        ("HEREDA total 500 al mes actual",          inh.get("totalAmt") == 500),
        ("marca el total como heredado",            inh.get("totalInh") is True),
        ("HEREDA categoria food 120",               inh.get("foodAmt") == 120),
        ("food aparece en budgetBars",              "food:120" in (inh.get("bars") or [])),
        ("RESPETA CERO: centinela no hereda (0 filas)", zero.get("count") == 0),
        ("RESPETA CERO: sin barras",                zero.get("bars") == 0),
    ]
    ok = all(v for _,v in checks)
    print("\n=== E2E Herencia de presupuestos (mes a mes) ===")
    for label,v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port=free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - los presupuestos se mantienen mes a mes y respetan el cero" if ok
                  else "FALLO - revisar herencia"))
    sys.exit(0 if ok else 1)
