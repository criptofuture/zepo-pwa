#!/usr/bin/env python3
"""
QA E2E REAL: conexiones de amigos — aceptar / rechazar una solicitud recibida.
Siembra 2 user_connections hacia la cuenta demo (de qa-from y qa-from2, via admin),
inicia sesion demo y verifica el estado REAL tras recargar:
  aceptar  -> aparece en friends, sale de pendingReceived (status accepted en DB)
  rechazar -> sale de pendingReceived, NO entra a friends (status declined en DB)
Limpia. Sale 1 si algo no persiste.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

def admin(method, path, body=None, extra=None):
    h = dict(H);  h.update(extra or {})
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
async ([conn1, conn2, from1, from2]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='cuentas'; c.cuentasTab='amigos';
  await c.loadFriends();
  const seeded = (c.pendingReceived||[]).filter(p => p.id===conn1 || p.id===conn2).length;
  await c.acceptConnection(conn1);
  await c.declineConnection(conn2);
  await c.loadFriends();
  const accepted = (c.friends||[]).some(f => f.user_id===from1);
  const acceptedGonePending = !(c.pendingReceived||[]).some(p => p.id===conn1);
  const declinedGone = !(c.pendingReceived||[]).some(p => p.id===conn2)
                     && !(c.friends||[]).some(f => f.user_id===from2);
  return { seeded, accepted, acceptedGonePending, declinedGone };
}
"""

def run(url, conn1, conn2, from1, from2):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return None
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)
        res = page.evaluate(ACTIONS_JS, [conn1, conn2, from1, from2])
        browser.close()
    return res

def main():
    demo = ensure_user(DEMO_EMAIL, DEMO_PASS)
    f1 = ensure_user("qa-from@zepo.test", "ZepoQAfrom2026!")
    f2 = ensure_user("qa-from2@zepo.test", "ZepoQAfrom2_2026!")
    if not all([demo, f1, f2]): print("[FALLA] usuarios"); return 1
    # limpiar conexiones previas entre estos
    for fid in (f1, f2):
        admin("DELETE", f"/rest/v1/user_connections?requester_id=eq.{fid}&addressee_id=eq.{demo}")
    s, r1 = admin("POST", "/rest/v1/user_connections",
                  {"requester_id": f1, "addressee_id": demo, "status": "pending"}, {"Prefer": "return=representation"})
    s, r2 = admin("POST", "/rest/v1/user_connections",
                  {"requester_id": f2, "addressee_id": demo, "status": "pending"}, {"Prefer": "return=representation"})
    if not (isinstance(r1, list) and isinstance(r2, list) and r1 and r2):
        print("[FALLA] no se sembraron conexiones:", r1, r2); return 1
    conn1, conn2 = r1[0]["id"], r2[0]["id"]
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        res = run(f"http://127.0.0.1:{port}/index.html", conn1, conn2, f1, f2)
        # estado real en DB
        s, d1 = admin("GET", f"/rest/v1/user_connections?id=eq.{conn1}&select=status")
        s, d2 = admin("GET", f"/rest/v1/user_connections?id=eq.{conn2}&select=status")
    finally:
        admin("DELETE", f"/rest/v1/user_connections?addressee_id=eq.{demo}&requester_id=in.({f1},{f2})")
    if res is None: return 1
    db1 = (d1[0]["status"] if isinstance(d1, list) and d1 else None)
    db2 = (d2[0]["status"] if isinstance(d2, list) and d2 else None)
    checks = [
        ("2 solicitudes recibidas visibles", res.get("seeded") == 2),
        ("ACEPTAR -> aparece en amigos",     res.get("accepted") is True),
        ("ACEPTAR -> sale de pendientes",    res.get("acceptedGonePending") is True),
        ("ACEPTAR persiste en DB (accepted)",db1 == "accepted"),
        ("RECHAZAR -> sale de pendientes y no es amigo", res.get("declinedGone") is True),
        ("RECHAZAR persiste en DB (declined)", db2 == "declined"),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E Amigos (aceptar/rechazar conexion) ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    print("\n" + ("OK - aceptar/rechazar conexiones persiste" if ok
                  else "FALLO - una transicion de conexion no persistio"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
