#!/usr/bin/env python3
"""Screenshots Fase 1: alias modal, cat-grid Nueva, split box, payment box, group breakdown."""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(PWA_DIR, "tools", "_shots"); os.makedirs(SHOT, exist_ok=True)
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def main():
    port = free_port()
    srv = http.server.HTTPServer(("127.0.0.1", port), functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR))
    threading.Thread(target=srv.serve_forever, daemon=True).start(); time.sleep(0.4)
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2).new_page()
        pg.on("dialog", lambda d: d.accept())
        pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded"); pg.wait_for_timeout(1200)
        pg.evaluate("""async ([e,p])=>{document.documentElement.classList.remove('browser-mode');const g=document.getElementById('install-gate');if(g)g.remove();const c=window.Alpine.$data(document.querySelector('#app'));c.authMode='login';c.authEmail=e;c.authPassword=p;await c.handleAuth();}""", [DEMO_EMAIL, DEMO_PASS])
        pg.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        pg.wait_for_timeout(1000)
        pg.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.showWelcomeCarousel=false;}")

        # 1) Alias modal
        pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.aliasModalContact={display_name:'Beatriz',user_id:'x'};c.aliasModalValue='Beti';c.aliasModalOpen=true;}""")
        pg.wait_for_timeout(500); pg.screenshot(path=os.path.join(SHOT,"f1-alias.png"))
        pg.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.aliasModalOpen=false;}")

        # 2) Cat grid con tile Nueva + inline add
        pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.tab='home';c.editingExpense=null;c.editingBatch=null;c.parsedItems=[];c.form={amount:'10',description:'sopa',category:'food',date:'2026-06-05',is_income:false,is_split:false,split_persona:'',split_pct:'',split_people:[]};c.analyzed=true;c.sheetOpen=true;c.gridAddingCat=true;c.newCatLabel='Mascotas';c.newCatEmoji='🐾';}""")
        pg.wait_for_timeout(600); pg.screenshot(path=os.path.join(SHOT,"f1-catgrid.png"))

        # 3) Split box (tu + persona mismo tamano, %/monto alineados)
        pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.gridAddingCat=false;c.form.is_split=true;c.form.split_people=[{name:'Tú',pct:60,you:true,color:'#507D5A'},{name:'Carlos',pct:40,color:'#C2553F'}];}""")
        pg.wait_for_timeout(500); pg.screenshot(path=os.path.join(SHOT,"f1-split.png"))
        pg.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.sheetOpen=false;c.form.is_split=false;}")

        # 4) Payment method box (marca larga 'Visa Pichincha')
        pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.savedCard={brand:'Visa Pichincha',last4:'8200'};c.tab='settings';}""")
        pg.wait_for_timeout(500)
        pg.evaluate("""()=>{const lab=[...document.querySelectorAll('.settings-group-title')].find(e=>/Metodo de pago/i.test(e.textContent));if(lab)lab.scrollIntoView({block:'center'});}""")
        pg.wait_for_timeout(400); pg.screenshot(path=os.path.join(SHOT,"f1-payment.png"))

        # 5) Group editor con desglose por categoria (>5 items)
        pg.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));const cats=['food','market','transport','health','coffee','shop'];const items=[];for(let i=0;i<8;i++){items.push({id:'t'+i,description:'Item '+(i+1),amount:3+i*2,category:cats[i%cats.length],is_income:false,date:'2026-05-29'});}c.tab='home';c.openEditBatch({batch_id:'qa',items,date:'2026-05-29'});}""")
        pg.wait_for_timeout(700); pg.screenshot(path=os.path.join(SHOT,"f1-groupbreakdown.png"), full_page=True)
        br.close()
    print("OK -> f1-alias, f1-catgrid, f1-split, f1-payment, f1-groupbreakdown")
    return 0

if __name__ == "__main__":
    sys.exit(main())
