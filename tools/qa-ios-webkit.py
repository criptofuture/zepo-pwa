#!/usr/bin/env python3
"""
QA iOS con el MOTOR REAL DE SAFARI (WebKit), no Chromium.

Por qué existe: Chromium (lo que usa preview_screenshot) NO reproduce Safari/iOS.
Errores de notch, contraste en oscuro y layout solo aparecen en WebKit. Esta
herramienta renderiza las pantallas clave a tamaño iPhone 11 (insets 44/34 px
inyectados, que WebKit-desktop no provee solo), en claro Y oscuro, guarda los
PNG para revisión y assertea hechos objetivos (notch, barra flush, overflow).

NO sustituye al iPhone real en la nube para la franja inferior y el teclado de
iOS, pero atrapa la gran mayoría de los bugs visuales que Chromium se traga.

Uso:  python tools/qa-ios-webkit.py            (sirve local + corre)
      python tools/qa-ios-webkit.py <url>       (contra una URL)
Salida: PNGs en %TEMP%/zepo-ios/ + PASS/FAIL por chequeo. Exit 1 si algún FAIL.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(os.environ.get("TEMP", "."), "zepo-ios")
os.makedirs(OUT_DIR, exist_ok=True)
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"
SAFE_TOP, SAFE_BOTTOM = 44, 34

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
  st.textContent = ':root{--safe-top:%dpx !important;--safe-bottom:%dpx !important;}';
  document.head.appendChild(st);
}
""" % (SAFE_TOP, SAFE_BOTTOM)

LOGIN = """
async ([email, password]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

# Hechos objetivos que NO dependen del ojo. Devuelve lista de [label, ok, detalle].
CHECKS = """
() => {
  const out = [];
  const vw = window.innerWidth, vh = window.innerHeight;
  const top = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--safe-top')) || 0;
  // 1. Nada se desborda horizontalmente
  let widest = 0, culprit = '';
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > widest) { widest = Math.round(r.right); if (r.right > vw + 1) culprit = el.className || el.tagName; }
  });
  out.push(['sin overflow horizontal', widest <= vw + 1, `derecha max ${widest} vs ancho ${vw}` + (culprit?` (${culprit})`:'')]);
  // 2. Barra inferior: pegada al borde físico + labels densos (sin franja muerta).
  //    position:fixed -> offsetParent es null por spec; chequear visibilidad por display+rect.
  const bar = document.querySelector('.tab-bar');
  const barVisible = bar && getComputedStyle(bar).display !== 'none' && bar.getBoundingClientRect().height > 0;
  if (barVisible) {
    const b = bar.getBoundingClientRect();
    out.push(['tab-bar flush al borde', Math.abs(vh - b.bottom) <= 1, `fondo barra a ${Math.round(vh-b.bottom)}px del borde`]);
    const label = bar.querySelector('.tab-item');
    if (label) { const lr = label.getBoundingClientRect(); const gap = Math.round(vh-lr.bottom); out.push(['label barra denso (<=22px del borde)', gap >= 0 && gap <= 22, `label a ${gap}px`]); }
  }
  // 3. Botón Saltar (carrusel viejo o onbV2) por debajo del notch
  const skip = document.querySelector('.ov2-skip, .wc-skip');
  if (skip && skip.offsetParent !== null) {
    const t = skip.getBoundingClientRect().top;
    out.push(['botón Saltar bajo el notch', t >= top - 1, `top ${Math.round(t)} vs safe-top ${top}`]);
  }
  return out;
}
"""

def cap(page, name):
    page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(OUT_DIR, name + ".png"))

def run_checks(page, screen):
    rows = page.evaluate(CHECKS)
    ok_all = True
    for label, ok, detail in rows:
        if not ok: ok_all = False
        print(f"    [{'PASS' if ok else 'FALLA'}] {label} — {detail}")
    return ok_all

def run(url):
    failures = 0
    with sync_playwright() as p:
        wk = p.webkit.launch()
        ctx = wk.new_context(**p.devices["iPhone 11"])
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1500)
        page.evaluate(PREP)
        err = page.evaluate(LOGIN, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); ctx.close(); wk.close(); return 1
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2500)

        for theme in ("light", "dark"):
            page.evaluate("(t)=>{ if(t==='dark') document.documentElement.setAttribute('data-theme','dark'); else document.documentElement.removeAttribute('data-theme'); }", theme)
            print(f"\n=== TEMA {theme.upper()} (iPhone 11, WebKit) ===")

            # Home + tab bar
            page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); c.showOnbV2=false; c.showWelcomeCarousel=false; c.tab='home';}")
            cap(page, f"home-{theme}")
            print("  [home]");
            if not run_checks(page, "home"): failures += 1

            # Onboarding v2 — pasos 0..4. Camino REAL: openOnbV2() (que mata coach/tour
            # y destruye el popover driver) en vez de forzar showOnbV2 a pelo.
            page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); c._a7done && c._a7done(); c.openOnbV2 && c.openOnbV2(); document.querySelectorAll('.driver-popover,.driver-overlay,#driver-page-overlay').forEach(e=>e.remove());}")
            page.wait_for_timeout(300)
            for step in (0, 1, 3, 4):
                page.evaluate("(s)=>{const c=window.Alpine.$data(document.querySelector('#app')); c.onbV2Step=s;}", step)
                cap(page, f"onbv2-{step}-{theme}")
            print("  [onboarding v2]")
            if not run_checks(page, "onbv2"): failures += 1

            # Tour del primer gasto: GLOBITO FLOTANTE (estilo Android) sobre el textarea.
            # Robusto en iOS porque se crea con el sheet ya asentado (anti-parpadeo) y se
            # RETIRA al empezar a escribir, antes de que suba el teclado.
            page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); c.showOnbV2=false; c._a7done(); c.a7Active=true; c.a7Step=1;}")
            page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); c.openNew && c.openNew();}")
            page.wait_for_timeout(1100)  # cubre el delay anti-parpadeo de 360ms + creacion + refresh
            cap(page, f"tour-write-{theme}")
            tour = page.evaluate("""()=>{
              const pop=document.querySelector('.driver-popover');
              const ta=document.querySelector('#a7-desc');
              if(!pop||!ta) return {shown:false};
              const p=pop.getBoundingClientRect(), a=ta.getBoundingClientRect();
              return {shown:true, above: p.bottom <= a.top + 8, overlaps: (p.bottom>a.top+8 && p.top<a.bottom-8),
                      popBottom:Math.round(p.bottom), taTop:Math.round(a.top)};
            }""")
            print("  [tour: globito flotante sobre textarea]")
            ok = tour.get("shown") and tour.get("above") and not tour.get("overlaps")
            print(f"    [{'PASS' if ok else 'FALLA'}] globito ARRIBA del textarea, sin pisarlo — {tour}")
            if not ok: failures += 1
            # Al empezar a escribir, el globito se RETIRA (antes de que suba el teclado iOS).
            page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); c._a7onWrite();}")
            page.wait_for_timeout(300)
            gone = page.evaluate("()=>!document.querySelector('.driver-popover')")
            print(f"    [{'PASS' if gone else 'FALLA'}] se retira al empezar a escribir (sin teclado encima) — gone={gone}")
            if not gone: failures += 1
            # Paso REVISAR/GUARDAR: el globito final va ARRIBA del RESULTADO y NO debe pisar el
            # textarea (Alvaro vio el de 'Guardar' encima del box). Se prueba a ALTURA CORTA
            # (--vvh 640 ~ Safari navegador) para garantizar que aguanta cualquier pantalla.
            page.evaluate("()=>{document.documentElement.style.setProperty('--vvh','640px');}")
            page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); c._a7done(); c.a7Active=true; c.a7Step=2; c.sheetOpen=true; c.parsedItems=[{description:'sopa',amount:5,category:'food'}]; c.analyzed=true;}")
            page.wait_for_timeout(700)
            cap(page, f"tour-review-{theme}")
            rv = page.evaluate("""()=>{
              const pop=document.querySelector('.driver-popover'); const ta=document.querySelector('#a7-desc');
              if(!pop||!ta) return {shown:false};
              const p=pop.getBoundingClientRect(), a=ta.getBoundingClientRect();
              return {shown:true, overlaps:(p.bottom>a.top+6 && p.top<a.bottom-6), popBottom:Math.round(p.bottom), taTop:Math.round(a.top)};
            }""")
            okr = rv.get("shown") and not rv.get("overlaps")
            print(f"    [{'PASS' if okr else 'FALLA'}] globito 'revisar' sobre el resultado, sin pisar el textarea — {rv}")
            if not okr: failures += 1
            page.evaluate("()=>{document.documentElement.style.removeProperty('--vvh');}")
            page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); c._a7done && c._a7done(); c.sheetOpen=false; c.a7Active=false; c.parsedItems=[];}")
            page.wait_for_timeout(300)

        ctx.close(); wk.close()
    print(f"\n{'='*46}\n  QA iOS WebKit: {'TODO PASS' if failures==0 else str(failures)+' grupo(s) con FALLA'}")
    print(f"  Screenshots: {OUT_DIR}")
    return 1 if failures else 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(run(sys.argv[1]))
    port = free_port(); serve(port); time.sleep(0.5)
    sys.exit(run(f"http://127.0.0.1:{port}/index.html"))
