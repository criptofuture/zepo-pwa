#!/usr/bin/env python3
"""Verifica: (1) toggle 'Balance' legible en dash, (2) tab-bar de borde a borde sin franjas crema.
Render sobre app real, viewport 430px (Pro Max) para reproducir las franjas."""
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

def run(url):
    with sync_playwright() as p:
        br = p.chromium.launch()
        # 430px = iPhone Pro Max CSS width — reproduce franjas si la barra capa a 430
        page = br.new_context(viewport={"width":440,"height":900}, device_scale_factor=2).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); br.close(); return
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2500)
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));if(c.finishWelcomeCarousel)c.finishWelcomeCarousel();c.showWelcomeCarousel=false;}")
        page.wait_for_timeout(500)
        # Dashboard con Balance seleccionado, periodo año
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.tab='dash';c.dashViewMode='balance';c.dashPeriod='año';}")
        page.wait_for_timeout(900); page.screenshot(path=os.path.join(OUT,"v-dash-balance.png")); print("ok v-dash-balance.png")
        # Recorte del toggle (top de la pantalla)
        page.screenshot(path=os.path.join(OUT,"v-dash-balance-top.png"), clip={"x":0,"y":120,"width":440,"height":120}); print("ok toggle clip")
        # Tab bar (fondo de la pantalla) — recorte para ver franjas
        page.screenshot(path=os.path.join(OUT,"v-tabbar.png"), clip={"x":0,"y":780,"width":440,"height":120}); print("ok tabbar clip")
        br.close()

if __name__ == "__main__":
    port=free_port(); serve(port); time.sleep(0.5)
    run(f"http://127.0.0.1:{port}/index.html")
