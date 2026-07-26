#!/usr/bin/env python3
"""
QA E2E REAL: Contactos/Amigos con saldo neto por persona + apodo.
Siembra para la cuenta demo:
  - un SPLIT pendiente: 'Carlos QA' te debe $10 (gasto dividido)
  - una DEUDA aceptada: le debes $4 a 'Beatriz QA' (payment_request aceptada de qa-from)
  - amistad aceptada demo<->qa-from
Verifica:
  - accountsByPerson: Carlos neto +10 (con desglose), Beatriz neto -4 (con desglose)
  - friendsWithAccounts: qa-from con neto -4
  - apodo: saveAlias -> el amigo se ve como 'Beti'
Fuentes disjuntas (te debe=splits, le debes=payreqs) => sin doble conteo. Limpia. Sale 1 si falla.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TODAY = time.strftime("%Y-%m-%d")
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

def admin(method, path, body=None, extra=None):
    h = dict(H); h.update(extra or {})
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            t = resp.read().decode() or "[]"; return resp.status, (json.loads(t) if t[:1] in "[{" else t)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:250]

def ensure_user(email, password):
    s, u = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(u, dict):
        for x in u.get("users", []):
            if x.get("email") == email: return x["id"]
    s, r = admin("POST", "/auth/v1/admin/users", {"email": email, "password": password, "email_confirm": True})
    return r.get("id") if isinstance(r, dict) else None

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

ACTIONS_JS = """
async ([fromId]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  // Simula al usuario PARADO en la pestana cuentas (asi el getter memoizado recomputa en vivo).
  c.tab = 'cuentas'; c.cuentasTab = 'amigos'; c.friendsSubTab = 'contactos';
  await Promise.all([c.loadExpenses(), c.loadSplits(), c.loadPaymentRequests(), c.loadFriends()]);
  const acc = c.accountsByPerson || [];
  const noZepo = c.nonZepoAccounts || [];
  const carlos = acc.find(p => p.name === 'Carlos QA');
  const beatriz = acc.find(p => p.name === 'Beatriz QA');
  const fwa = (c.friendsWithAccounts || []).find(f => f.user_id === fromId);
  await c.saveAlias(fromId, 'Beti');
  await c.loadFriends();
  const renamed = (c.friends || []).find(f => f.user_id === fromId);
  return {
    carlosNeto: carlos ? carlos.neto : null,
    carlosDebeGroups: carlos ? carlos.debeGroups.length : 0,
    carlosEnNoZepo: noZepo.some(p => p.name === 'Carlos QA'),
    beatrizNeto: beatriz ? beatriz.neto : null,
    beatrizDebes: beatriz ? beatriz.debesItems.length : 0,
    beatrizEnNoZepo: noZepo.some(p => p.name === 'Beatriz QA'),
    friendNeto: fwa ? fwa.neto : null,
    friendDebes: fwa ? fwa.debesItems.length : 0,
    aliasApplied: renamed ? renamed.display_name : null,
  };
}
"""

def run(url, from_id):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return None
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)
        res = page.evaluate(ACTIONS_JS, [from_id])
        browser.close()
    return res

def cleanup(demo, frm):
    admin("DELETE", "/rest/v1/expenses?description=eq.Almuerzo%20QA")
    admin("DELETE", "/rest/v1/payment_requests?description=eq.Cine%20QA")
    admin("DELETE", f"/rest/v1/user_connections?requester_id=eq.{frm}&addressee_id=eq.{demo}")
    admin("DELETE", f"/rest/v1/contact_aliases?owner_id=eq.{demo}&contact_id=eq.{frm}")

def main():
    demo = ensure_user(DEMO_EMAIL, DEMO_PASS)
    frm  = ensure_user("qa-from@zepo.test", "ZepoQAfrom2026!")
    if not (demo and frm): print("[FALLA] usuarios"); return 1
    admin("PATCH", f"/rest/v1/profiles?user_id=eq.{frm}", {"display_name": "Beatriz QA"})
    admin("POST", "/rest/v1/profiles", {"user_id": frm, "display_name": "Beatriz QA"}, {"Prefer": "resolution=merge-duplicates"})
    cleanup(demo, frm)
    # split: Carlos QA te debe $10
    admin("POST", "/rest/v1/expenses", {
        "user_id": demo, "amount": 10, "description": "Almuerzo QA", "category": "food", "date": TODAY,
        "is_income": False, "is_split": True, "split_persona": "Carlos QA",
        "split_pct": 50, "split_total": 20, "split_status": "pendiente"})
    # deuda aceptada: le debes $4 a Beatriz QA (qa-from -> demo)
    admin("POST", "/rest/v1/payment_requests", {
        "from_user_id": frm, "to_user_id": demo, "amount": 4, "description": "Cine QA",
        "category": "food", "expense_date": TODAY, "status": "accepted"})
    # amistad aceptada
    admin("POST", "/rest/v1/user_connections",
          {"requester_id": frm, "addressee_id": demo, "status": "accepted"})
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        res = run(f"http://127.0.0.1:{port}/index.html", frm)
    finally:
        cleanup(demo, frm)
    if res is None: return 1
    checks = [
        ("Carlos QA: te debe neto +10",        res.get("carlosNeto") == 10),
        ("Carlos QA: desglose 'te debe' tiene registros", res.get("carlosDebeGroups") >= 1),
        ("Carlos QA en 'Que no Zepo' (no amigo)", res.get("carlosEnNoZepo") is True),
        ("Beatriz QA: le debes neto -4",       res.get("beatrizNeto") == -4),
        ("Beatriz QA: desglose 'le debes' tiene registros", res.get("beatrizDebes") >= 1),
        ("Beatriz QA NO esta en 'Que no Zepo' (es amiga)", res.get("beatrizEnNoZepo") is False),
        ("'Que si Zepo': qa-from con neto -4 + registro le debes", res.get("friendNeto") == -4 and res.get("friendDebes") >= 1),
        ("Apodo: el amigo se ve como 'Beti'",  res.get("aliasApplied") == "Beti"),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E Contactos/Amigos (saldo neto + apodo) ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    print("  datos:", json.dumps(res))
    print("\n" + ("OK - saldo por persona y apodo correctos" if ok
                  else "FALLO - revisar accountsByPerson / friendsWithAccounts / alias"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
