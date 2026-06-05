#!/usr/bin/env python3
"""
QA E2E REAL: el nombre de un CONTACTO se ve legible (NUNCA un fragmento de UUID).
Regla nacida del bug "fb4abcae": user_settings tiene RLS "solo tu fila", asi que la app
no podia leer el nombre de otros y caia al UUID. La tabla profiles (legible entre usuarios)
lo arregla. Este test lo verifica de punta a punta:
  - siembra un perfil 'Beatriz QA' para qa-from + una solicitud pendiente hacia demo
  - inicia demo, loadFriends, y exige que pendingReceived muestre 'Beatriz QA'
  - control: el nombre NO puede ser los primeros 8 chars del user_id (UUID)
Limpia. Sale 1 si el nombre no resuelve.
"""
import sys, time, socket, threading, http.server, functools, os, json, re, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
SEED_NAME = "Beatriz QA"
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
async (connId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='cuentas';
  await c.loadFriends();
  const row = (c.pendingReceived||[]).find(p => p.id===connId);
  return { found: !!row, name: row ? row.display_name : null, uid: row ? row.user_id : null };
}
"""

def run(url, conn_id):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return None
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)
        res = page.evaluate(ACTIONS_JS, conn_id)
        browser.close()
    return res

def main():
    demo = ensure_user(DEMO_EMAIL, DEMO_PASS)
    frm  = ensure_user("qa-from@zepo.test", "ZepoQAfrom2026!")
    if not (demo and frm): print("[FALLA] usuarios"); return 1
    # perfil legible para qa-from
    admin("POST", "/rest/v1/profiles", {"user_id": frm, "display_name": SEED_NAME, "avatar_color": "#507D5A"},
          {"Prefer": "resolution=merge-duplicates"})
    admin("PATCH", f"/rest/v1/profiles?user_id=eq.{frm}", {"display_name": SEED_NAME})
    # solicitud pendiente qa-from -> demo
    admin("DELETE", f"/rest/v1/user_connections?requester_id=eq.{frm}&addressee_id=eq.{demo}")
    s, r = admin("POST", "/rest/v1/user_connections",
                 {"requester_id": frm, "addressee_id": demo, "status": "pending"}, {"Prefer": "return=representation"})
    if not (isinstance(r, list) and r): print("[FALLA] no se sembro la solicitud:", r); return 1
    conn_id = r[0]["id"]
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        res = run(f"http://127.0.0.1:{port}/index.html", conn_id)
    finally:
        admin("DELETE", f"/rest/v1/user_connections?id=eq.{conn_id}")
    if res is None: return 1
    name = res.get("name"); uid = res.get("uid") or ""
    is_uuid_frag = bool(name) and (name == uid[:8] or re.fullmatch(r"[0-9a-f]{8}", name or ""))
    checks = [
        ("solicitud visible para demo", res.get("found") is True),
        ("nombre resuelve al del perfil ('%s')" % SEED_NAME, name == SEED_NAME),
        ("nombre NO es fragmento de UUID", not is_uuid_frag),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E Nombres de contacto (anti-UUID) ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    if name is not None: print(f"  (nombre mostrado: {name!r})")
    print("\n" + ("OK - el nombre de otro usuario se lee legible" if ok
                  else "FALLO - el nombre no resuelve (revisar profiles/RLS)"))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
