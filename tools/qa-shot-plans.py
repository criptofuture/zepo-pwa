#!/usr/bin/env python3
"""
QA VISUAL del rediseño de planes. Login REAL por cuenta y captura:
- Home (badge del plan)
- Pantalla Planes (4 tarjetas, sin overflow a 390px)
- Checkout de Max (precio $15 mensual y $150 anual)
PNGs en tools/_plan-shots/. Revisar a ojo (overflow / badge / precio).
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_plan-shots")
os.makedirs(OUT, exist_ok=True)
PASSWORD = "ZepoQA2026!"
ACCOUNTS = [("free@zepo.test","free"), ("pro@zepo.test","pro"),
            ("elite@zepo.test","elite"), ("max@zepo.test","max")]

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

def shot(page, name):
    page.wait_for_timeout(700)
    page.screenshot(path=os.path.join(OUT, name))
    print("  shot:", name)

def run(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for email, plan in ACCOUNTS:
            ctx = browser.new_context(viewport={"width":390,"height":844})
            ctx.add_init_script("localStorage.setItem('zepo_onboarded_v1','1');localStorage.setItem('zepo:onboarded','1');")
            page = ctx.new_page(); page.on("dialog", lambda d: d.accept())
            page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1000)
            err = page.evaluate(LOGIN_JS, [email, PASSWORD])
            if err: print(f"[FALLA] login {email}:", err); ctx.close(); continue
            page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
            page.wait_for_timeout(1500)
            print(f"=== {email} ({plan}) ===")
            page.evaluate("()=>{window.Alpine.$data(document.querySelector('#app')).tab='home';}")
            shot(page, f"{plan}-home.png")
            page.evaluate("()=>{window.Alpine.$data(document.querySelector('#app')).tab='plans';}")
            page.wait_for_timeout(500)
            page.evaluate("()=>window.scrollTo(0,0)")
            page.screenshot(path=os.path.join(OUT, f"{plan}-plans-full.png"), full_page=True)
            print("  shot:", f"{plan}-plans-full.png")
            if plan == "max":
                # checkout Max mensual y anual
                page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.annualBilling=false;c.startCheckout('max');}")
                shot(page, "max-checkout-mensual.png")
                page.evaluate("()=>{window.Alpine.$data(document.querySelector('#app')).annualBilling=true;}")
                shot(page, "max-checkout-anual.png")
            ctx.close()
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1: run(sys.argv[1])
    else:
        port=free_port(); serve(port); time.sleep(0.5); run(f"http://127.0.0.1:{port}/index.html")
    print("\nPNGs en:", OUT)
