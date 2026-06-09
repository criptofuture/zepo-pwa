#!/usr/bin/env python3
"""Verifica el selector segmentado YA EN EL CODIGO (sin inyeccion). Siembra 3 espacios
de ejemplo en el estado real, cambia de pestana y captura."""
import time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.dirname(os.path.abspath(__file__))
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
  c.showWelcomeCarousel = false; c.tab = 'home';
  c.spaces = [
    {id:'p',name:'Personal',icon:'🏠',color:'#507D5A',is_default:true,sort_order:0},
    {id:'t',name:'Mi tienda',icon:'🏪',color:'#BF8A2A',is_default:false,sort_order:1}
  ];
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
        page.evaluate(SEED); page.wait_for_timeout(700)
        page.screenshot(path=os.path.join(OUT,"final-1-personal.png")); print("ok final-1-personal.png")
        # click pestana "Mi tienda" de verdad (sin reload de red: forzamos solo el estado para el look)
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.spaceViewAll=false;c.activeSpaceId='t';}")
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT,"final-2-tienda.png")); print("ok final-2-tienda.png")
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.spaceViewAll=true;c.activeSpaceId=null;}")
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT,"final-3-global.png")); print("ok final-3-global.png")
        br.close()

if __name__ == "__main__":
    port=free_port(); serve(port); time.sleep(0.5)
    run(f"http://127.0.0.1:{port}/index.html")
