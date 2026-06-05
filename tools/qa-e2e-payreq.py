#!/usr/bin/env python3
"""
QA E2E REAL: solicitudes de cobro ("Debo") — aceptar / rechazar / marcar pagado.

Siembra 3 payment_requests reales hacia la cuenta demo (remitente = usuario qa-from,
creado via admin), inicia sesion demo, y prueba las 3 transiciones verificando el
estado REAL en Supabase tras recargar:
  A) acceptPaymentRequest -> pasa a "deudas" (accepted)
  B) declinePaymentRequest -> sale de la lista (declined)
  C) claimPayment -> pasa a "esperando confirmacion" (paid)
Limpia los 3 registros sembrados. Sale 1 si alguna transicion no persiste.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
FROM_EMAIL = "qa-from@zepo.test"; FROM_PASS = "ZepoQAfrom2026!"
TAG = "PR_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

def admin(method, path, body=None, extra=None):
    headers = dict(H);
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

def seed_payreqs(to_id, from_id):
    rows = [{"from_user_id": from_id, "to_user_id": to_id, "amount": 7.50,
             "description": f"{TAG} {s}", "category": "food",
             "expense_date": time.strftime("%Y-%m-%d"), "status": "pending"} for s in ("A","B","C")]
    st, res = admin("POST", "/rest/v1/payment_requests", rows, {"Prefer": "return=representation"})
    return res if isinstance(res, list) else []

def cleanup():
    admin("DELETE", f"/rest/v1/payment_requests?description=like.{TAG}*")

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
  const find = s => (c.payReqs||[]).find(p => (p.description||'')===(tag+' '+s));
  const seededCount = (c.deboSolicitudes||[]).filter(p=>(p.description||'').startsWith(tag)).length;
  const A=find('A'), B=find('B'), Cc=find('C');
  // A) aceptar
  if (A) { c.acceptPrModal = A; await c.acceptPaymentRequest(A.id, false); }
  // B) rechazar
  if (B) { await c.declinePaymentRequest(B.id); }
  // C) flujo real: aceptar y LUEGO marcar pagado (la base bloquea pendiente->pagado directo)
  if (Cc) { c.acceptPrModal = Cc; await c.acceptPaymentRequest(Cc.id, false); await c.claimPayment(Cc.id); }
  // recargar desde Supabase para verificar persistencia real
  await c.loadPaymentRequests();
  const acc = (c.deboDeudas||[]).some(p=>(p.description||'')===(tag+' A'));
  const declGone = !(c.deboSolicitudes||[]).some(p=>(p.description||'')===(tag+' B'))
                 && !(c.deboDeudas||[]).some(p=>(p.description||'')===(tag+' B'));
  const paid = (c.deboPaidWaiting||[]).some(p=>(p.description||'')===(tag+' C'));
  return { seededCount, accepted: acc, declinedGone: declGone, paid };
}
"""

def run(url, expect_seed):
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
    checks = [
        ("3 solicitudes sembradas visibles", res.get("seededCount")==expect_seed),
        ("ACEPTAR -> pasa a deudas (accepted)", res.get("accepted") is True),
        ("RECHAZAR -> sale de la lista",        res.get("declinedGone") is True),
        ("MARCAR PAGADO -> esperando confirmacion (paid)", res.get("paid") is True),
    ]
    ok = all(v for _,v in checks)
    print("\n=== E2E Solicitudes de cobro (aceptar/rechazar/pagar) ===")
    for label,v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

def main():
    to_id = ensure_user(DEMO_EMAIL, DEMO_PASS)
    from_id = ensure_user(FROM_EMAIL, FROM_PASS)
    if not to_id or not from_id:
        print("[FALLA] no se pudo asegurar usuarios demo/qa-from"); return 1
    cleanup()
    seeded = seed_payreqs(to_id, from_id)
    if len(seeded) != 3:
        print("[FALLA] no se sembraron las 3 solicitudes:", seeded); cleanup(); return 1
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html", 3)
    finally:
        cleanup()
    print("\n" + ("OK - aceptar/rechazar/pagar persisten en Supabase" if ok
                  else "FALLO - una transicion de solicitud no persistio"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
