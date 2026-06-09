#!/usr/bin/env python3
"""App REAL con el selector SEGMENTADO de espacios (pestañas) + el picker dentro del +.
Inyecta 3 espacios de ejemplo en el estado real de Alpine y renderiza."""
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

SEED_SPACES = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  if (c.finishWelcomeCarousel) c.finishWelcomeCarousel();
  c.showWelcomeCarousel = false; c.tab = 'home';
  c.spaces = [
    {id:'p',name:'Personal',icon:'🏠',color:'#507D5A',is_default:true,sort_order:0},
    {id:'t',name:'Mi tienda',icon:'🏪',color:'#BF8A2A',is_default:false,sort_order:1},
    {id:'f',name:'Freelance',icon:'💻',color:'#6B8CAE',is_default:false,sort_order:2}
  ];
  c.activeSpaceId='p'; c.spaceViewAll=false;
  c.spaceStats={p:842.5,t:1910,f:320};
}
"""

# Selector segmentado inyectado donde estaba el chip viejo
SEGMENTED_JS = r"""
(activeId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  // ocultar el chip viejo
  document.querySelectorAll('button').forEach(b=>{ if(b.getAttribute('@click')==='openSpaceSwitcher()'){ b.parentElement.style.display='none'; } });
  const old=document.getElementById('__seg'); if(old) old.remove();
  const wrap=document.createElement('div');
  wrap.id='__seg';
  wrap.style.cssText='display:flex;gap:8px;overflow-x:auto;padding:0 20px 14px;-ms-overflow-style:none;scrollbar-width:none;';
  const tint=(hex,a)=>{const n=parseInt(hex.slice(1),16);return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`;};
  const mk=(s)=>{
    const on = !c.spaceViewAll && c.activeSpaceId===s.id;
    const b=document.createElement('button');
    b.style.cssText='display:inline-flex;align-items:center;gap:7px;flex-shrink:0;border-radius:var(--radius-pill);padding:8px 14px;cursor:pointer;font-family:var(--font-display);font-weight:700;font-size:13.5px;'+
      (on?'background:var(--gradient);color:var(--c-brand-contrast);border:1px solid transparent;box-shadow:0 4px 12px rgba(var(--c-brand-rgb),0.3);'
         :'background:var(--surface);color:var(--text);border:1px solid var(--border);');
    b.innerHTML=`<span style="width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-size:13px;${on?'background:rgba(255,255,255,0.22)':'background:'+tint(s.color,0.16)}">${s.icon}</span>${s.name}`;
    b.onclick=()=>{c.spaceViewAll=false;c.activeSpaceId=s.id;render(s.id);};
    return b;
  };
  c.spaces.forEach(s=>wrap.appendChild(mk(s)));
  // pestaña Global
  const g=document.createElement('button');
  const gon=c.spaceViewAll;
  g.style.cssText='display:inline-flex;align-items:center;gap:7px;flex-shrink:0;border-radius:var(--radius-pill);padding:8px 14px;cursor:pointer;font-family:var(--font-display);font-weight:700;font-size:13.5px;'+
    (gon?'background:var(--gradient);color:var(--c-brand-contrast);border:1px solid transparent;'
        :'background:var(--surface2);color:var(--muted);border:1px dashed var(--border2);');
  g.innerHTML='🌐 Global';
  g.onclick=()=>{c.spaceViewAll=true;render(null);};
  wrap.appendChild(g);
  const header=document.querySelector('#app .page-header');
  if(header) header.parentElement.insertBefore(wrap, header.nextSibling);
  window.__renderSeg=render;
  function render(){ /* reinyecta para refrescar highlight */ window.__seg_rerender(); }
}
"""

RERENDER = """
() => { window.__seg_rerender_impl && window.__seg_rerender_impl(); }
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
        page.evaluate(SEED_SPACES); page.wait_for_timeout(500)

        # define un rerender simple en window que vuelve a construir la fila
        page.evaluate("""
        () => {
          window.__build = """ + SEGMENTED_JS + """;
          window.__seg_rerender_impl = () => window.__build();
          window.__seg_rerender = () => window.__build();
          window.__build();
        }
        """)
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT,"seg-1-personal.png")); print("ok seg-1-personal.png")

        # cambiar a Mi tienda
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.spaceViewAll=false;c.activeSpaceId='t';window.__build();}")
        page.wait_for_timeout(400)
        page.screenshot(path=os.path.join(OUT,"seg-2-tienda.png")); print("ok seg-2-tienda.png")

        # abrir el + para mostrar el picker de espacio en zona del pulgar
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.openNew && c.openNew();}")
        page.wait_for_timeout(900)
        page.screenshot(path=os.path.join(OUT,"seg-3-add-picker.png"), full_page=False); print("ok seg-3-add-picker.png")
        br.close()

if __name__ == "__main__":
    port=free_port(); serve(port); time.sleep(0.5)
    run(f"http://127.0.0.1:{port}/index.html")
