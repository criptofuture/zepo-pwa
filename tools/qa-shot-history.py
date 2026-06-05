#!/usr/bin/env python3
"""Screenshot del Historial 'Todo el historial' scrolleado al fondo (repro bug footer)."""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(PWA_DIR, "tools", "_shots"); os.makedirs(SHOT, exist_ok=True)
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

def adm(m, p, b=None):
    r = urllib.request.Request(URL + p, data=(json.dumps(b).encode() if b is not None else None), headers=H, method=m)
    try:
        with urllib.request.urlopen(r) as x: t = x.read().decode() or "[]"; return json.loads(t) if t[:1] in "[{" else t
    except urllib.error.HTTPError as e: return e.read().decode()[:150]

def demo_id():
    u = adm("GET", "/auth/v1/admin/users?per_page=200")
    return next((x["id"] for x in u.get("users", []) if x.get("email") == DEMO_EMAIL), None)

def seed(demo):
    adm("DELETE", "/rest/v1/expenses?description=like.HIST_QA*")
    rows = []
    for i in range(14):
        day = (datetime_day(i))
        rows.append({"user_id": demo, "amount": round(3 + i * 1.5, 2), "description": f"HIST_QA gasto {i+1}",
                     "category": ["food", "transport", "market", "health"][i % 4], "date": day, "is_income": False, "is_split": False})
    adm("POST", "/rest/v1/expenses", rows)

def datetime_day(i):
    import time as _t
    return _t.strftime("%Y-%m-%d", _t.localtime(_t.time() - i * 86400))

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def main():
    demo = demo_id(); seed(demo)
    port = free_port()
    srv = http.server.HTTPServer(("127.0.0.1", port), functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR))
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.4)
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
        pg.on("dialog", lambda d: d.accept())
        pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded"); pg.wait_for_timeout(1200)
        pg.evaluate("""async ([e,p])=>{document.documentElement.classList.remove('browser-mode');const g=document.getElementById('install-gate');if(g)g.remove();const c=window.Alpine.$data(document.querySelector('#app'));c.authMode='login';c.authEmail=e;c.authPassword=p;await c.handleAuth();}""", [DEMO_EMAIL, DEMO_PASS])
        pg.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        pg.wait_for_timeout(1200)
        pg.evaluate("""async ()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.showWelcomeCarousel=false;c.tab='history';c.histAll=true;await c.loadHistory();}""")
        pg.wait_for_timeout(1000)
        n = pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));return (c.historyData||[]).length;}""")
        # scroll the main-content to the bottom
        pg.evaluate("""()=>{const m=document.querySelector('.main-content:not([style*=\"display: none\"])')||[...document.querySelectorAll('.main-content')].find(e=>e.offsetParent);if(m)m.scrollTop=m.scrollHeight;}""")
        pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(SHOT, "history-bottom.png"))
        br.close()
    adm("DELETE", "/rest/v1/expenses?description=like.HIST_QA*")
    print(f"OK history rows={n} -> {os.path.join(SHOT,'history-bottom.png')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
