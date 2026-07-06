#!/usr/bin/env python3
"""
QA E2E REAL: registrar como gasto un cobro que se aceptó SIN registrar.

Pedido Alvaro (2026-07-06): al aceptar un cobro con "Solo aceptar (sin registrar)", debe
poder cambiar de opinión y registrarlo como gasto después. Este test siembra un cobro real
hacia la cuenta demo, lo acepta SIN registrar (receiver_expense_id null, sin gasto espejo),
llama registerAcceptedDebt y verifica en Supabase que:
  - se creó el gasto espejo (mismo monto/descripción),
  - el cobro quedó ligado (receiver_expense_id == id del espejo).
Limpia cobro + gasto sembrados. Sale 1 si algo no persiste.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
FROM_EMAIL = "qa-from@zepo.test"; FROM_PASS = "ZepoQAfrom2026!"
TAG = "REGACC_" + str(int(time.time()))
AMOUNT = 13.37
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

def admin(method, path, body=None, extra=None):
    headers = dict(H)
    if extra: headers.update(extra)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            txt = resp.read().decode() or "[]"
            return resp.status, (json.loads(txt) if txt.strip().startswith(("[","{")) else txt)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]

def ensure_user(email, password):
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(users, dict):
        for u in users.get("users", []):
            if u.get("email") == email: return u["id"]
    st, res = admin("POST", "/auth/v1/admin/users", {"email": email, "password": password, "email_confirm": True})
    return res.get("id") if isinstance(res, dict) else None

def seed_payreq(to_id, from_id):
    row = [{"from_user_id": from_id, "to_user_id": to_id, "amount": AMOUNT,
            "description": TAG, "category": "food",
            "expense_date": time.strftime("%Y-%m-%d"), "status": "pending"}]
    st, res = admin("POST", "/rest/v1/payment_requests", row, {"Prefer": "return=representation"})
    return res if isinstance(res, list) else []

def cleanup(to_id):
    admin("DELETE", f"/rest/v1/payment_requests?description=like.{TAG}*")
    admin("DELETE", f"/rest/v1/expenses?description=like.{TAG}*&user_id=eq.{to_id}")

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
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='cuentas'; c.cuentasTab='debo';
  await c.loadPaymentRequests();
  const pr = (c.payReqs||[]).find(p => (p.description||'')===tag);
  if (!pr) return { error:'no seeded pr' };
  // aceptar SIN registrar (addExpense=false)
  c.acceptPrModal = pr;
  await c.acceptPaymentRequest(pr.id, false);
  await c.loadPaymentRequests();
  await c.loadExpenses();
  const accepted = (c.deboDeudas||[]).find(p => (p.description||'')===tag) || null;
  const before = {
    isAccepted: !!accepted,
    receiverId: accepted ? (accepted.receiver_expense_id || null) : 'no-row',
    mirrorInExpenses: (c.expenses||[]).some(e => (e.description||'')===tag),
  };
  // cambiar de opinión: registrar como gasto ahora
  if (accepted) await c.registerAcceptedDebt(accepted);
  await c.loadPaymentRequests();
  await c.loadExpenses();
  const afterRow = (c.deboDeudas||[]).find(p => (p.description||'')===tag) || null;
  const mirror = (c.expenses||[]).find(e => (e.description||'')===tag) || null;
  const after = {
    receiverId: afterRow ? (afterRow.receiver_expense_id || null) : 'no-row',
    mirrorInExpenses: !!mirror,
    mirrorAmount: mirror ? Number(mirror.amount) : null,
    linkMatches: !!(afterRow && mirror && afterRow.receiver_expense_id === mirror.id),
    idempotent: true,
  };
  // idempotencia: volver a registrar NO debe crear un 2do espejo
  if (afterRow) await c.registerAcceptedDebt(afterRow);
  await c.loadExpenses();
  after.idempotent = (c.expenses||[]).filter(e => (e.description||'')===tag).length === 1;
  return { before, after };
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
        res = page.evaluate(ACTIONS_JS, TAG)
        browser.close()
    if res.get("error"):
        print("[FALLA]", res["error"]); return False
    b, a = res["before"], res["after"]
    checks = [
        ("Aceptado SIN registrar: aparece como deuda", b["isAccepted"] is True),
        ("SIN registrar: receiver_expense_id null", b["receiverId"] is None),
        ("SIN registrar: NO existe gasto espejo", b["mirrorInExpenses"] is False),
        ("Tras registrar: gasto espejo creado", a["mirrorInExpenses"] is True),
        ("Tras registrar: monto correcto", a["mirrorAmount"] is not None and abs(a["mirrorAmount"] - AMOUNT) < 0.001),
        ("Tras registrar: cobro ligado al espejo", a["linkMatches"] is True),
        ("Idempotente: no crea 2do espejo", a["idempotent"] is True),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E Registrar cobro aceptado sin registrar ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

def main():
    to_id = ensure_user(DEMO_EMAIL, DEMO_PASS)
    from_id = ensure_user(FROM_EMAIL, FROM_PASS)
    if not to_id or not from_id:
        print("[FALLA] no se pudo asegurar usuarios demo/qa-from"); return 1
    cleanup(to_id)
    seeded = seed_payreq(to_id, from_id)
    if len(seeded) != 1:
        print("[FALLA] no se sembró el cobro:", seeded); cleanup(to_id); return 1
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html")
    finally:
        cleanup(to_id)
    print("\n" + ("OK - un cobro aceptado sin registrar se puede registrar después" if ok
                  else "FALLO - registrar cobro aceptado no persistió"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
