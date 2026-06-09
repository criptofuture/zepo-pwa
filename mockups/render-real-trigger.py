#!/usr/bin/env python3
"""Renderiza la app REAL (index.html) con login demo y le inyecta el disparador
de espacios en la zona del pulgar. Saca screenshots para comparar sobre el app de verdad."""
import sys, time, socket, threading, http.server, functools, os
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

PREP_HOME = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  if (c.finishWelcomeCarousel) c.finishWelcomeCarousel();
  c.showWelcomeCarousel = false;
  c.tab = 'home';
}
"""

# Disparador 1: pildora flotante (usa tokens reales de la app)
PILL_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  // ocultar el chip viejo de arriba
  document.querySelectorAll('button').forEach(b=>{ if(b.getAttribute('@click')==='openSpaceSwitcher()') b.style.display='none'; });
  const old = document.getElementById('__pill'); if(old) old.remove();
  const p = document.createElement('button');
  p.id='__pill';
  p.style.cssText='position:fixed;left:50%;transform:translateX(-50%);bottom:calc(var(--tab-total) + 14px);z-index:90;display:inline-flex;align-items:center;gap:9px;background:var(--surface);border:1px solid var(--border2);border-radius:var(--radius-pill);padding:8px 15px 8px 8px;box-shadow:0 6px 20px rgba(var(--c-ink-rgb),0.18);cursor:pointer;font-family:inherit;';
  p.innerHTML='<span style="width:28px;height:28px;border-radius:9px;display:grid;place-items:center;font-size:15px;background:rgba(var(--c-brand-rgb),0.16)">🏠</span><span style="font-family:var(--font-display);font-weight:700;font-size:14.5px;color:var(--text)">Personal</span><svg viewBox="0 0 24 24" fill="none" stroke="var(--dim)" stroke-width="2.6" width="13" height="13"><polyline points="6 9 12 15 18 9"/></svg>';
  p.onclick=()=>c.openSpaceSwitcher();
  document.querySelector('#app').appendChild(p);
}
"""

OPEN_SHEET = """
() => { const c = window.Alpine.$data(document.querySelector('#app')); c.openSpaceSwitcher(); }
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
        page.evaluate(PREP_HOME); page.wait_for_timeout(800)
        page.screenshot(path=os.path.join(OUT,"real-1-actual.png"))
        print("ok real-1-actual.png")
        page.evaluate(PILL_JS); page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT,"real-2-pildora.png"))
        print("ok real-2-pildora.png")
        page.evaluate(OPEN_SHEET); page.wait_for_timeout(900)
        page.screenshot(path=os.path.join(OUT,"real-3-hoja-abierta.png"))
        print("ok real-3-hoja-abierta.png")
        br.close()

if __name__ == "__main__":
    port=free_port(); serve(port); time.sleep(0.5)
    run(f"http://127.0.0.1:{port}/index.html")
