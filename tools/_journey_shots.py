#!/usr/bin/env python3
"""Capturas del Journey (v178) para revision visual: Home card + hoja + config.
Usa free@zepo.test (baseline limpio). NO es parte del gate; herramienta puntual."""
import sys, os, json, socket, threading, http.server, functools, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
EMAIL = "free@zepo.test"; PASS = "ZepoQA2026!"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_journey-shots")
os.makedirs(OUT, exist_ok=True)
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}


def admin(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, headers=H, method=method, data=data)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


LOGIN = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

port = free_port()
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
srv = http.server.HTTPServer(("127.0.0.1", port), h)
threading.Thread(target=srv.serve_forever, daemon=True).start()

with sync_playwright() as p:
    browser = p.webkit.launch()
    page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
    page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    page.wait_for_function("()=>window.Alpine && window.Alpine.$data(document.querySelector('#app'))", timeout=15000)
    err = page.evaluate(LOGIN, [EMAIL, PASS])
    if err:
        print("login error:", err); sys.exit(1)
    page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user && !!c.jrn;}", timeout=25000)
    page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.showWelcomeCarousel=false;c.showOnbV2=false;c.tab='home';}")
    page.wait_for_timeout(1500)
    page.screenshot(path=os.path.join(OUT, "1-home-card.png"))
    page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.jrnOpen=true;}")
    page.wait_for_timeout(700)
    page.screenshot(path=os.path.join(OUT, "2-journey-sheet.png"))
    page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));const el=document.querySelector('.jrn-body');if(el)el.scrollTop=el.scrollHeight;}")
    page.wait_for_timeout(400)
    page.screenshot(path=os.path.join(OUT, "3-journey-sheet-bottom.png"))
    page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.jrnOpen=false;c.tab='settings';}")
    page.wait_for_timeout(700)
    page.evaluate("()=>{const el=document.querySelector('.main-content[style], .main-content');window.scrollTo(0,400);}")
    page.screenshot(path=os.path.join(OUT, "4-settings.png"))
    browser.close()

# limpiar la fila de journey creada para la captura (baseline para otros tests)
uid_status = None
r = urllib.request.Request(URL + "/auth/v1/admin/users?page=1&per_page=200", headers=H)
with urllib.request.urlopen(r) as resp:
    users = json.loads(resp.read().decode()).get("users", [])
uid = next((x["id"] for x in users if x.get("email") == EMAIL), None)
if uid:
    admin("DELETE", f"/rest/v1/zepo_journey?user_id=eq.{uid}")
print("OK — capturas en", OUT)
