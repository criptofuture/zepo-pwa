#!/usr/bin/env python3
"""
QA E2E REAL: presupuestos (crear por categoria -> recompute de barras -> borrar).
login demo -> set budgetForm food=150 (elite) -> saveBudgets -> verifica budgets + budgetBars
-> limpia (budgetForm vacio -> saveBudgets) -> verifica que no queda. Sale 1 si falla.
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

CREATE_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.userPlan='elite'; c.tab='budgets';
  c.budgetForm = { food: '150' };
  await c.saveBudgets();
  return true;
}
"""
VERIFY_CREATE_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='budgets';
  const inData = (c.budgets||[]).some(b => b.category==='food' && Number(b.amount)===150);
  const inBars = (c.budgetBars||[]).some(b => b.cat==='food' && Number(b.budget)===150);
  return { inData, inBars };
}
"""
DELETE_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.userPlan='elite'; c.budgetForm = {};
  await c.saveBudgets();
  return true;
}
"""
VERIFY_DELETE_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='budgets';
  const inData = (c.budgets||[]).some(b => b.category==='food');
  const inBars = (c.budgetBars||[]).some(b => b.cat==='food');
  return { inData, inBars };
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
        page.evaluate(CREATE_JS); page.wait_for_timeout(2500)
        vc = page.evaluate(VERIFY_CREATE_JS)
        page.evaluate(DELETE_JS); page.wait_for_timeout(2500)
        vd = page.evaluate(VERIFY_DELETE_JS)
        browser.close()
    checks = [
        ("CREATE: presupuesto food=150 en budgets", vc.get("inData") is True),
        ("CREATE: aparece en budgetBars",           vc.get("inBars") is True),
        ("DELETE: sale de budgets",                 vd.get("inData") is False),
        ("DELETE: sale de budgetBars",              vd.get("inBars") is False),
    ]
    ok = all(v for _,v in checks)
    print("\n=== E2E Presupuestos (crear/borrar) ===")
    for label,v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port=free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - presupuestos crean/borran y recomputan barras" if ok
                  else "FALLO - revisar saveBudgets/budgetBars"))
    sys.exit(0 if ok else 1)
