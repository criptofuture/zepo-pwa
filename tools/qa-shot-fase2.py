#!/usr/bin/env python3
"""Screenshots Fase 2: editor de grupo con fecha por item (C), y edicion individual limpia (G+H)."""
import sys, time, socket, threading, http.server, functools, os, json
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(PWA_DIR, "tools", "_shots"); os.makedirs(SHOT, exist_ok=True)
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def main():
    port = free_port()
    srv = http.server.HTTPServer(("127.0.0.1", port), functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR))
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.4)
    out = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
        pg.on("dialog", lambda d: d.accept())
        pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded"); pg.wait_for_timeout(1200)
        pg.evaluate("""async ([e,p])=>{document.documentElement.classList.remove('browser-mode');const g=document.getElementById('install-gate');if(g)g.remove();const c=window.Alpine.$data(document.querySelector('#app'));c.authMode='login';c.authEmail=e;c.authPassword=p;await c.handleAuth();}""", [DEMO_EMAIL, DEMO_PASS])
        pg.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        pg.wait_for_timeout(900)
        pg.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.showWelcomeCarousel=false;}")

        # C) Editor de grupo con un item expandido (categoria grid + FECHA por item)
        pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));const cats=['food','market','transport','health','coffee','shop'];const items=[];for(let i=0;i<6;i++){items.push({id:'t'+i,description:'Item '+(i+1),amount:3+i*2,category:cats[i%cats.length],is_income:false,date:'2026-05-'+(20+i)});}c.tab='home';c.openEditBatch({batch_id:'qa',items,date:'2026-05-29'});c.editingParsedCatIdx=0;}""")
        pg.wait_for_timeout(700); pg.screenshot(path=os.path.join(SHOT,"f2-group-itemdate.png"))
        hdr = pg.evaluate("""()=>{const t=document.querySelector('.approve-title');return t?t.textContent.trim():'?';}""")
        out["group_header"] = hdr

        # G+H) Edicion individual: aunque venga de un batch sucio, debe limpiar a UI individual
        pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.editingBatch='dirty';c.parsedItems=[{description:'x',amount:1,category:'food'}];c._doOpenEdit({id:'s1',description:'Almuerzo solo',amount:8.5,category:'food',date:'2026-06-04',is_income:false,is_split:false});}""")
        pg.wait_for_timeout(600)
        info = pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));const t=document.querySelector('.approve-title');const grid=document.querySelector('.cd-cat-grid');const gvis=grid&&grid.getBoundingClientRect().height>0;return {header:t?t.textContent.trim():'?',editingBatch:c.editingBatch,parsedLen:c.parsedItems.length,gridVisible:!!gvis};}""")
        out["single_edit"] = info
        pg.screenshot(path=os.path.join(SHOT,"f2-single-edit.png"))
        br.close()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("-> f2-group-itemdate.png, f2-single-edit.png")
    return 0

if __name__ == "__main__":
    sys.exit(main())
