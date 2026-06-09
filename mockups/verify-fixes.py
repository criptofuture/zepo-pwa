#!/usr/bin/env python3
"""Verifica las 5 correcciones de auditoria sobre la app real. Siembra gastos de ejemplo
en el estado de Alpine (solo para render, sin tocar la DB) para ver Historial/Dash con datos."""
import time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit")
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"

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
SEED = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  if (c.finishWelcomeCarousel) c.finishWelcomeCarousel();
  c.showWelcomeCarousel = false;
  c.spaces = [{id:'p',name:'Personal',icon:'🏠',color:'#507D5A',is_default:true,sort_order:0},
              {id:'t',name:'Mi tienda',icon:'🏪',color:'#BF8A2A',is_default:false,sort_order:1}];
  c.activeSpaceId='p'; c.spaceViewAll=false;
}
"""

def run(url):
    with sync_playwright() as p:
        br = p.chromium.launch()
        page = br.new_context(viewport={"width":390,"height":844}, device_scale_factor=2).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); br.close(); return
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2500)
        page.evaluate(SEED); page.wait_for_timeout(400)
        for tab, name in [("home","f-home.png"),("dash","f-dash.png"),("history","f-history.png")]:
            page.evaluate(f"()=>{{const c=window.Alpine.$data(document.querySelector('#app'));c.tab='{tab}';}}")
            page.wait_for_timeout(900); page.screenshot(path=os.path.join(OUT,name)); print("ok", name)
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.tab='home';c.openNew&&c.openNew();}")
        page.wait_for_timeout(900); page.screenshot(path=os.path.join(OUT,"f-add.png")); print("ok f-add.png")
        br.close()

if __name__ == "__main__":
    port=free_port(); serve(port); time.sleep(0.5)
    run(f"http://127.0.0.1:{port}/index.html")
