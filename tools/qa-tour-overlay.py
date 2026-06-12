#!/usr/bin/env python3
"""Reproduce el tour A7 (paso 1: highlight del FAB) en WebKit (motor real iOS)
y verifica si el SVG de overlay (spotlight) se pinta. Diagnostico del bug:
'no muestra el highlight del boton +'."""
import os, socket, threading, http.server, functools
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

PREP = """
() => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const st = document.createElement('style'); st.id='ios-insets';
  st.textContent = ':root{--safe-top:44px !important;--safe-bottom:34px !important;}';
  document.head.appendChild(st);
}
"""
LOGIN = """
async ([email, password]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""
START = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2=false; c.showWelcomeCarousel=false; c.tab='home';
  try { localStorage.removeItem('zepo_a7_done_v1'); } catch(e){}
  c.startFirstExpenseTour();
  return { a7Active: c.a7Active, a7Step: c.a7Step };
}
"""
INSPECT = """
() => {
  const svg = document.querySelector('svg.driver-overlay');
  const pop = document.querySelector('.driver-popover');
  const fab = document.querySelector('.fab.driver-active-element') || document.querySelector('.fab');
  const r = { hasSvg: !!svg, hasPopover: !!pop };
  if (svg) {
    const sr = svg.getBoundingClientRect();
    const cs = getComputedStyle(svg);
    const path = svg.querySelector('path');
    r.svg = { w: Math.round(sr.width), h: Math.round(sr.height), display: cs.display,
              opacity: cs.opacity, visibility: cs.visibility, zIndex: cs.zIndex,
              viewBox: svg.getAttribute('viewBox'),
              pathFill: path ? getComputedStyle(path).fill : null,
              pathOpacity: path ? getComputedStyle(path).opacity : null,
              pathDLen: path ? (path.getAttribute('d')||'').length : 0 };
  }
  if (fab) { const fr = fab.getBoundingClientRect();
    r.fab = { w: Math.round(fr.width), h: Math.round(fr.height), top: Math.round(fr.top), bottom: Math.round(fr.bottom),
              active: fab.classList.contains('driver-active-element') }; }
  r.innerW = window.innerWidth; r.innerH = window.innerHeight;
  // que pinta encima del centro del FAB?
  if (fab) { const fr = fab.getBoundingClientRect();
    const el = document.elementFromPoint(fr.left+fr.width/2, fr.top+fr.height/2);
    r.topAtFabCenter = el ? (el.tagName+'.'+(typeof el.className==='string'?el.className:'')) : null;
    r.fabCenterX = Math.round(fr.left+fr.width/2); }
  if (pop) { const pr = pop.getBoundingClientRect();
    r.pop = { left: Math.round(pr.left), right: Math.round(pr.right), top: Math.round(pr.top), bottom: Math.round(pr.bottom), cx: Math.round(pr.left+pr.width/2) };
    r.popClass = pop.className; }
  const arrow = document.querySelector('.driver-popover-arrow');
  if (arrow) { const ar = arrow.getBoundingClientRect();
    r.arrow = { cls: arrow.className.replace('driver-popover-arrow','').trim(), cx: Math.round(ar.left+ar.width/2), top: Math.round(ar.top), w: Math.round(ar.width), h: Math.round(ar.height) }; }
  return r;
}
"""

def run():
    port = free_port(); serve(port)
    url = f"http://127.0.0.1:{port}/"
    with sync_playwright() as p:
        wk = p.webkit.launch()
        ctx = wk.new_context(**p.devices["iPhone 11"])
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1500)
        page.evaluate(PREP)
        err = page.evaluate(LOGIN, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); ctx.close(); wk.close(); return
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)
        print("inicio tour:", page.evaluate(START))
        for ms in (200, 600, 1200, 2500):
            page.wait_for_timeout(ms if ms == 200 else ms-200)
            r = page.evaluate(INSPECT)
            print(f"\n--- t≈{ms}ms ---")
            for k, v in r.items(): print(f"  {k}: {v}")
        out = os.path.join(os.environ.get("TEMP","."), "zepo-tour-overlay.png")
        page.screenshot(path=out); print("\nscreenshot:", out)
        ctx.close(); wk.close()

if __name__ == "__main__":
    run()
