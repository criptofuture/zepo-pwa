#!/usr/bin/env python3
"""
QA E2E REAL: las 3 mejoras de UI de v175.

1) Configuracion: entradas nuevas "Gestionar metodos de pago" (abre pmManager) y
   "Gestionar espacios" (abre spaceManager o manda a plans si el plan no es Max).
2) Ingresos: el selector de metodos ahora aparece tambien en ingresos con la etiqueta
   "A QUE CUENTA ENTRA?" (en gastos sigue "METODO DE PAGO"); clic real en una tile
   fija form.payment_method.
3) Chips compartido/no saldado: crea un gasto dividido REAL (50/50 con persona sin
   cuenta), verifica chip ambar "por cobrar $X" en Home y en Historial; simula cobrado
   (local) -> chip gris "compartido"; borra el gasto (retract) y verifica que el chip
   desaparece. Limpia todo.

USO: python tools/qa-e2e-v175-ui.py [url] [--shots DIR]
Sale 1 si algo falla.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TAG = "QACHIP_" + str(int(time.time()))

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

PREP_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.coachTip = ()=>{}; c.coachKey = null;
  c.userPlan = 'elite';
  return true;
}
"""

ADD_SPLIT_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.openNew();
  c.parsedItems = []; c.analyzed = true;
  c.form.amount = '10.00'; c.form.description = tag; c.form.category = 'food';
  c.form.date = new Date().toISOString().slice(0,10);
  c.form.is_income = false; c.form.is_split = true;
  c.form.split_people = [ { you:true, name:'Tu', pct:50 }, { you:false, name:'QaChipAmigo', pct:50 } ];
  await c.saveExpense();
  const e = (c.expenses||[]).find(x => (x.description||'') === tag);
  return e ? { id:e.id, pend:Number(e.split_pending), status:e.split_status } : null;
}
"""

def state_js(tag):
    return ("(tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));"
            "const e=(c.expenses||[]).find(x=>(x.description||'')===tag);"
            "return e?{id:e.id,is_split:e.is_split,pend:Number(e.split_pending),status:e.split_status}:null;}")

def run(url, shots=None):
    def shot(page, name):
        if shots: page.screenshot(path=os.path.join(shots, name + ".png"))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        page.wait_for_function("()=>!!(window.Alpine && document.querySelector('#app') && window.Alpine.$data(document.querySelector('#app')))", timeout=20000)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)
        page.evaluate(PREP_JS)
        checks = []

        # ── 1) CONFIGURACION: entradas nuevas ──
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.tab='settings';}")
        page.wait_for_timeout(500)
        btn_pm = page.locator("button", has_text="Gestionar métodos de pago").locator("visible=true").first
        btn_sp = page.locator("button", has_text="Gestionar espacios").locator("visible=true").first
        checks.append(("Config: boton 'Gestionar metodos de pago' visible", btn_pm.count() == 1))
        checks.append(("Config: boton 'Gestionar espacios' visible", btn_sp.count() == 1))
        btn_pm.scroll_into_view_if_needed(); shot(page, "1a-config-entradas")
        btn_pm.click(); page.wait_for_timeout(400)
        pm_open = page.evaluate("()=>window.Alpine.$data(document.querySelector('#app')).pmManagerOpen")
        pm_title = page.locator(".sheet-title", has_text="Métodos de pago").locator("visible=true").count()
        checks.append(("Config: clic abre gestor de metodos", pm_open is True and pm_title >= 1))
        shot(page, "1b-gestor-metodos")
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.pmManagerOpen=false;}")
        page.wait_for_timeout(300)
        btn_sp.click(); page.wait_for_timeout(400)
        sp = page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));"
                           "return {open:c.spaceManagerOpen, tab:c.tab};}")
        checks.append(("Config: clic abre gestor de espacios (o gate a plans)",
                       sp.get("open") is True or sp.get("tab") == "plans"))
        shot(page, "1c-gestor-espacios")
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));"
                      "c.spaceManagerOpen=false;c.tab='settings';}")

        # ── 2) INGRESO: 'A que cuenta entra?' ──
        page.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));
            // la demo puede tener 0 metodos (seed fallido, preexistente): inyecta uno LOCAL
            // (sin tocar BD) para poder verificar el grid + clic real.
            if (!c.paymentMethods.length) c.paymentMethods.push({ id:'qa-pm-local', name:'Efectivo', emoji:'\\ud83d\\udcb5', is_default:true, sort:0 });
            c.openNew(); c.form.is_income=true; c.form.amount='5'; c.analyzed=true;}""")
        page.wait_for_timeout(500)
        lbl_inc = page.locator(".cd-section-label span", has_text="¿A QUÉ CUENTA ENTRA?").locator("visible=true").count()
        checks.append(("Ingreso: etiqueta 'A QUE CUENTA ENTRA?' visible", lbl_inc >= 1))
        n_tiles = page.evaluate(
            """()=>[...document.querySelectorAll('.cd-cat-grid button.cd-cat-tile')]
                 .filter(b=>b.offsetParent&&b.closest('[x-show]')&&b.textContent.trim()).length""")
        shot(page, "2a-ingreso-cuenta")
        tile = page.locator("button.cd-cat-tile", has_text="Efectivo").locator("visible=true").first
        pm_ok = False
        if tile.count():
            tile.click(); page.wait_for_timeout(200)
            pm_ok = page.evaluate("()=>window.Alpine.$data(document.querySelector('#app')).form.payment_method") == "Efectivo"
        checks.append(("Ingreso: clic real en tile fija payment_method", pm_ok))
        shot(page, "2b-ingreso-cuenta-elegida")
        lbl_exp = page.evaluate("""()=>{const c=window.Alpine.$data(document.querySelector('#app'));
            c.form.is_income=false; return true;}""")
        page.wait_for_timeout(300)
        lbl_exp = page.locator(".cd-section-label span", has_text="MÉTODO DE PAGO").locator("visible=true").count()
        checks.append(("Gasto: etiqueta sigue 'METODO DE PAGO'", lbl_exp >= 1))
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.sheetOpen=false;}")

        # ── 3) CHIPS compartido / no saldado ──
        created = page.evaluate(ADD_SPLIT_JS, TAG)
        # espera ACTIVA (no fija): bajo la carga de la suite completa el insert puede
        # tardar mas de 2.5s y el test fallaba por flake de timing
        page.wait_for_function(
            "(tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));"
            "const e=(c.expenses||[]).find(x=>(x.description||'')===tag);"
            "return !!(e && e.is_split);}", arg=TAG, timeout=15000)
        page.wait_for_timeout(400)
        st = page.evaluate(state_js(TAG), TAG)
        checks.append(("Split: gasto dividido creado (pend $5, pendiente)",
                       bool(st) and st.get("is_split") is True and st.get("pend") == 5.0 and st.get("status") == "pendiente"))
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.tab='home';}")
        page.wait_for_timeout(600)
        chip_home = page.locator(".expense-row .split-chip.pend", has_text="por cobrar").locator("visible=true").count()
        checks.append(("Home: chip ambar 'por cobrar' visible", chip_home >= 1))
        if shots:
            row = page.locator(".expense-row", has_text=TAG).locator("visible=true").first
            if row.count(): row.scroll_into_view_if_needed()
        shot(page, "3a-home-chip-por-cobrar")
        page.evaluate("""async ()=>{const c=window.Alpine.$data(document.querySelector('#app'));
            c.tab='history'; await c.loadHistory();}""")
        page.wait_for_timeout(800)
        chip_hist = page.locator(".expense-row .split-chip.pend", has_text="por cobrar").locator("visible=true").count()
        checks.append(("Historial: chip ambar 'por cobrar' visible", chip_hist >= 1))
        shot(page, "3b-historial-chip")
        # simulacion local de 'cobrado' SOLO para verificar el render del estado saldado
        chip_ok = page.evaluate(
            """(tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));
                 const e=(c.expenses||[]).find(x=>(x.description||'')===tag);
                 if(!e) return null; e.split_status='cobrado'; e.split_pending=0; c.tab='home'; return true;}""", TAG)
        page.wait_for_timeout(500)
        chip_comp = page.locator(".expense-row .split-chip.ok", has_text="compartido").locator("visible=true").count()
        checks.append(("Home: saldado muestra chip gris 'compartido'", chip_ok is True and chip_comp >= 1))
        shot(page, "3c-home-chip-compartido")

        # limpieza: borrar el gasto (retract del cobro incluido)
        page.evaluate("""async (tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));
            c.askConfirm=()=>Promise.resolve(true);
            const e=(c.expenses||[]).find(x=>(x.description||'')===tag);
            if(e){ e.split_status='pendiente'; e.split_pending=5; c.editingExpense=e; c.sheetOpen=true; await c.deleteExpense(); }
            return true;}""", TAG)
        page.wait_for_timeout(2500)
        gone = page.evaluate(state_js(TAG), TAG)
        checks.append(("Limpieza: gasto de prueba borrado", gone is None))
        browser.close()

    ok = all(v for _, v in checks)
    print("\n=== E2E mejoras UI v175 (config + ingreso-cuenta + chips split) ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    argv = sys.argv[1:]
    shots = None
    if "--shots" in argv:
        i = argv.index("--shots")
        shots = argv[i + 1]
        os.makedirs(shots, exist_ok=True)
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith("--")]
    if args: ok = run(args[0], shots)
    else:
        port = free_port(); serve(port); time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html", shots)
    print("\n" + ("OK - config, cuenta en ingresos y chips split verificados" if ok
                  else "FALLO - revisar las mejoras de UI v175"))
    sys.exit(0 if ok else 1)
