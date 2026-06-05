#!/usr/bin/env python3
"""Captura screenshots de las pestanas nuevas Contactos y Amigos (con desglose expandido)."""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT_DIR = os.path.join(PWA_DIR, "tools", "_shots"); os.makedirs(SHOT_DIR, exist_ok=True)
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"; TODAY = time.strftime("%Y-%m-%d")
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

def adm(m, p, b=None, pref=None):
    h = dict(H);  h.update({"Prefer": pref} if pref else {})
    r = urllib.request.Request(URL + p, data=(json.dumps(b).encode() if b is not None else None), headers=h, method=m)
    try:
        with urllib.request.urlopen(r) as x: t = x.read().decode() or "[]"; return x.status, (json.loads(t) if t[:1] in "[{" else t)
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:200]

def uid(email):
    s, u = adm("GET", "/auth/v1/admin/users?per_page=200")
    return next((x["id"] for x in u.get("users", []) if x.get("email") == email), None)

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def main():
    demo = uid(DEMO_EMAIL); frm = uid("qa-from@zepo.test")
    adm("PATCH", f"/rest/v1/profiles?user_id=eq.{frm}", {"display_name": "Beatriz QA"})
    adm("DELETE", "/rest/v1/expenses?description=eq.Almuerzo%20QA")
    adm("DELETE", "/rest/v1/payment_requests?description=eq.Cine%20QA")
    adm("DELETE", f"/rest/v1/user_connections?requester_id=eq.{frm}&addressee_id=eq.{demo}")
    adm("POST", "/rest/v1/expenses", {"user_id": demo, "amount": 10, "description": "Almuerzo QA", "category": "food",
        "date": TODAY, "is_income": False, "is_split": True, "split_persona": "Carlos QA", "split_pct": 50,
        "split_total": 20, "split_status": "pendiente"})
    adm("POST", "/rest/v1/payment_requests", {"from_user_id": frm, "to_user_id": demo, "amount": 4,
        "description": "Cine QA", "category": "food", "expense_date": TODAY, "status": "accepted"})
    adm("POST", "/rest/v1/user_connections", {"requester_id": frm, "addressee_id": demo, "status": "accepted"})

    port = free_port()
    srv = http.server.HTTPServer(("127.0.0.1", port), functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR))
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.4)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
            pg.on("dialog", lambda d: d.accept())
            pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded"); pg.wait_for_timeout(1200)
            pg.evaluate("""async ([e,p])=>{document.documentElement.classList.remove('browser-mode');const g=document.getElementById('install-gate');if(g)g.remove();const c=window.Alpine.$data(document.querySelector('#app'));c.authMode='login';c.authEmail=e;c.authPassword=p;await c.handleAuth();}""", [DEMO_EMAIL, DEMO_PASS])
            pg.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
            pg.wait_for_timeout(1500)
            # Contactos con desglose de Carlos expandido
            pg.evaluate("""async ()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.showWelcomeCarousel=false;c.tab='cuentas';c.cuentasTab='amigos';c.friendsSubTab='contactos';await Promise.all([c.loadExpenses(),c.loadSplits(),c.loadPaymentRequests(),c.loadFriends()]);const carlos=(c.accountsByPerson||[]).find(p=>p.name==='Carlos QA');if(carlos)c.expandedContact=carlos.key;}""")
            pg.wait_for_timeout(800); pg.screenshot(path=os.path.join(SHOT_DIR, "contactos.png"))
            # Amigos con desglose del amigo expandido
            pg.evaluate("""async ()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.friendsSubTab='amigos';await c.loadFriends();const f=(c.friendsWithAccounts||[])[0];if(f)c.expandedContact='amg_'+f.user_id;}""")
            pg.wait_for_timeout(800); pg.screenshot(path=os.path.join(SHOT_DIR, "amigos.png"))
            br.close()
        print("OK shots:", os.path.join(SHOT_DIR, "contactos.png"), "|", os.path.join(SHOT_DIR, "amigos.png"))
    finally:
        adm("DELETE", "/rest/v1/expenses?description=eq.Almuerzo%20QA")
        adm("DELETE", "/rest/v1/payment_requests?description=eq.Cine%20QA")
        adm("DELETE", f"/rest/v1/user_connections?requester_id=eq.{frm}&addressee_id=eq.{demo}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
