#!/usr/bin/env python3
"""
QA E2E REAL (2 cuentas): retirar un gasto dividido.

Escenario que reproduce el bug de Alvaro (renta $90 borrada de su lado pero viva en el
de Bea) y prueba el arreglo end-to-end:

  Siembra un gasto dividido del REMITENTE (demo) + un cobro pending hacia el RECEPTOR
  (qa-to), ligado por origin_expense_id.
  FASE 1 — login RECEPTOR: acepta el cobro CON gasto (addExpense=true) -> debe crear el
           gasto espejo en su cuenta y ligarlo (receiver_expense_id).
  FASE 2 — login REMITENTE: borra su gasto (deleteExpense -> rpc retract_split_expense) ->
           el cobro debe quedar 'cancelled', el gasto espejo del receptor debe DESAPARECER
           y el gasto origen tambien.

Verifica el estado REAL en Supabase (admin/service_role) tras cada fase. Limpia todo.
Sale 1 si algo no persiste.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
SENDER_EMAIL = "demo@zepo.test"; SENDER_PASS = "ZepoDemo2026!"
RECV_EMAIL = "qa-to@zepo.test"; RECV_PASS = "ZepoQAto2026!"
TAG = "RT_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}


def admin(method, path, body=None, extra=None):
    headers = dict(H)
    if extra: headers.update(extra)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            txt = resp.read().decode() or "[]"
            return resp.status, (json.loads(txt) if txt.strip().startswith(("[", "{")) else txt)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def ensure_user(email, password):
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(users, dict):
        for u in users.get("users", []):
            if u.get("email") == email: return u["id"]
    st, res = admin("POST", "/auth/v1/admin/users", {"email": email, "password": password, "email_confirm": True})
    return res.get("id") if isinstance(res, dict) else None


def seed(sender_id, recv_id):
    # gasto dividido del remitente
    st, rows = admin("POST", "/rest/v1/expenses", {
        "user_id": sender_id, "amount": 90, "description": TAG + " origin", "category": "rent",
        "date": time.strftime("%Y-%m-%d"), "is_income": False, "is_split": True,
        "split_status": "pendiente", "split_pending": 90, "split_total": 180, "split_pct": 50,
    }, {"Prefer": "return=representation"})
    origin_id = rows[0]["id"] if isinstance(rows, list) and rows else None
    # cobro pending hacia el receptor, ligado al gasto origen
    st, prs = admin("POST", "/rest/v1/payment_requests", {
        "from_user_id": sender_id, "to_user_id": recv_id, "amount": 90,
        "description": TAG + " req", "category": "rent", "expense_date": time.strftime("%Y-%m-%d"),
        "status": "pending", "origin_expense_id": origin_id,
    }, {"Prefer": "return=representation"})
    req_id = prs[0]["id"] if isinstance(prs, list) and prs else None
    return origin_id, req_id


def cleanup():
    admin("DELETE", f"/rest/v1/payment_requests?description=like.{TAG}*")
    admin("DELETE", f"/rest/v1/expenses?description=like.{TAG}*")


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

ACCEPT_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='cuentas'; c.cuentasTab='debo';
  await c.loadPaymentRequests();
  const req = (c.payReqs||[]).find(p => (p.description||'')===(tag+' req'));
  if (!req) return { found:false };
  c.acceptPrModal = req;
  await c.acceptPaymentRequest(req.id, true);   // aceptar CON gasto -> crea espejo + liga
  return { found:true };
}
"""

DELETE_JS = """
async (originId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.askConfirm = async () => true;              // saltar el modal de confirmacion
  c.editingExpense = { id: originId, is_split: true };
  await c.deleteExpense();                       // llama rpc retract_split_expense
  return true;
}
"""


def login_and(url, email, password, js, arg):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [email, password])
        if err:
            browser.close(); return {"_login_err": err}
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(1500)
        res = page.evaluate(js, arg)
        page.wait_for_timeout(1500)  # deja terminar los .then() en background (link/borrado)
        browser.close()
        return res


def main():
    sender_id = ensure_user(SENDER_EMAIL, SENDER_PASS)
    recv_id = ensure_user(RECV_EMAIL, RECV_PASS)
    if not sender_id or not recv_id:
        print("[FALLA] no se pudo asegurar usuarios"); return 1
    cleanup()
    origin_id, req_id = seed(sender_id, recv_id)
    if not origin_id or not req_id:
        print("[FALLA] no se sembro origin/req:", origin_id, req_id); cleanup(); return 1

    checks = []
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        base = f"http://127.0.0.1:{port}/index.html"

        # FASE 1 — receptor acepta con gasto
        r1 = login_and(base, RECV_EMAIL, RECV_PASS, ACCEPT_JS, TAG)
        if r1.get("_login_err"):
            print("[FALLA] login receptor:", r1["_login_err"]); cleanup(); return 1
        checks.append(("cobro visible para el receptor", r1.get("found") is True))
        st, pr = admin("GET", f"/rest/v1/payment_requests?id=eq.{req_id}&select=status,receiver_expense_id")
        pr = pr[0] if isinstance(pr, list) and pr else {}
        mirror_id = pr.get("receiver_expense_id")
        checks.append(("aceptar -> cobro 'accepted'", pr.get("status") == "accepted"))
        checks.append(("aceptar -> receiver_expense_id ligado", bool(mirror_id)))
        if mirror_id:
            st, ex = admin("GET", f"/rest/v1/expenses?id=eq.{mirror_id}&select=id")
            checks.append(("aceptar -> gasto espejo existe en cuenta receptor", isinstance(ex, list) and len(ex) == 1))

        # FASE 2 — remitente borra su gasto -> retract
        r2 = login_and(base, SENDER_EMAIL, SENDER_PASS, DELETE_JS, origin_id)
        if isinstance(r2, dict) and r2.get("_login_err"):
            print("[FALLA] login remitente:", r2["_login_err"]); cleanup(); return 1
        st, pr2 = admin("GET", f"/rest/v1/payment_requests?id=eq.{req_id}&select=status")
        pr2 = pr2[0] if isinstance(pr2, list) and pr2 else {}
        checks.append(("borrar -> cobro 'cancelled'", pr2.get("status") == "cancelled"))
        if mirror_id:
            st, ex2 = admin("GET", f"/rest/v1/expenses?id=eq.{mirror_id}&select=id")
            checks.append(("borrar -> gasto espejo del receptor DESAPARECE", isinstance(ex2, list) and len(ex2) == 0))
        st, exo = admin("GET", f"/rest/v1/expenses?id=eq.{origin_id}&select=id")
        checks.append(("borrar -> gasto origen eliminado", isinstance(exo, list) and len(exo) == 0))
    finally:
        cleanup()

    print("\n=== E2E Retirar gasto dividido (2 cuentas) ===")
    for label, v in checks:
        print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    ok = len(checks) >= 6 and all(v for _, v in checks)
    print("\n" + ("OK - borrar un split retira cobro + espejo del receptor" if ok
                  else "FALLO - el retract no se propago correctamente"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
