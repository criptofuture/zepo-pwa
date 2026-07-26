#!/usr/bin/env python3
"""
QA E2E REAL: onboarding (primer gasto -> presupuesto -> finalizar).
login demo -> finishOnboardingFirst (crea gasto, va a onb-budget) -> saveOnboardingBudget
(crea presupuesto total, va a onb-method) -> finishOnboarding (marca completado, va a home).
Verifica persistencia + navegacion. Limpia gasto y presupuesto sembrados. Sale 1 si falla.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TAG = "ONB_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

def admin(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, headers=H, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            t = resp.read().decode() or "[]"; return resp.status, (json.loads(t) if t[:1] in "[{" else t)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

def demo_id():
    s, u = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    for x in (u.get("users", []) if isinstance(u, dict) else []):
        if x.get("email") == DEMO_EMAIL: return x["id"]
    return None

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

ONB_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  try { localStorage.removeItem('zepo:onboarded'); } catch {}
  // paso 1: primer gasto
  c.onboardingFirstAmount = '13.50'; c.onboardingFirstDesc = tag + ' primer'; c.onboardingFirstCat = 'food';
  await c.finishOnboardingFirst();
  const afterFirst = { tab: c.tab, hasExpense: (c.expenses||[]).some(e=>(e.description||'').startsWith(tag)) };
  // paso 2: presupuesto total
  c.onboardingBudget = '200';
  await c.saveOnboardingBudget();
  const afterBudget = { tab: c.tab, hasTotalBudget: (c.budgets||[]).some(b=>!b.category && Number(b.amount)===200) };
  // paso 3: finalizar
  c.onboardingMethod = 'text';
  c.finishOnboarding();
  const afterFinish = { tab: c.tab, flag: localStorage.getItem('zepo:onboarded') };
  return { afterFirst, afterBudget, afterFinish };
}
"""

def run(url, tag):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return None
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)
        res = page.evaluate(ONB_JS, tag)
        browser.close()
    return res

def main():
    did = demo_id()
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        res = run(f"http://127.0.0.1:{port}/index.html", TAG)
    finally:
        admin("DELETE", f"/rest/v1/expenses?description=like.{TAG}*")
        if did:
            now = time.localtime()
            admin("DELETE", f"/rest/v1/budgets?user_id=eq.{did}&category=is.null&amount=eq.200&month=eq.{now.tm_mon}&year=eq.{now.tm_year}")
    if res is None: return 1
    f, b, fin = res["afterFirst"], res["afterBudget"], res["afterFinish"]
    checks = [
        ("paso1: primer gasto creado", f.get("hasExpense") is True),
        ("paso1: navega a onb-budget", f.get("tab") == "onb-budget"),
        ("paso2: presupuesto total creado", b.get("hasTotalBudget") is True),
        ("paso2: navega a onb-method", b.get("tab") == "onb-method"),
        ("paso3: marca onboarded", fin.get("flag") == "1"),
        ("paso3: navega a home", fin.get("tab") == "home"),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E Onboarding (primer gasto/presupuesto/finalizar) ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    print("\n" + ("OK - onboarding persiste y navega" if ok else "FALLO - revisar onboarding"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
