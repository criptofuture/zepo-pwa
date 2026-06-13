#!/usr/bin/env python3
"""WebKit (motor iOS): certifica recurrente + dividir.
1) Con monto puesto, AMBOS toggles (Repetir / Dividir) visibles a la vez.
2) Activar uno NO esconde el otro (bug que reportó Alvaro).
3) Guardar recurrente+dividir crea la plantilla con split (is_split, split_persona)
   y aparece en el gestor. Limpia lo que crea."""
import os, socket, threading, http.server, functools
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"
MARK = "__ZRSPLIT_QA__"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

PREP = """() => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const st = document.createElement('style'); st.id='ios-insets';
  st.textContent = ':root{--safe-top:44px !important;--safe-bottom:34px !important;}';
  document.head.appendChild(st);
}"""
LOGIN = """async ([email, password]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.devUnlockAll = true;
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}"""
# Visibilidad por TEXTO: chequea el propio nodo de texto (tiene altura si se pinta).
VIS = """() => {
  const find = (txt) => {
    const el = [...document.querySelectorAll('#app *')].find(e =>
      e.children.length === 0 && e.textContent.trim() === txt);
    if (!el) return { found:false, visible:false };
    const r = el.getBoundingClientRect();
    // "visible" = renderizado y NO oculto por x-show (offsetParent null si display:none).
    // No exigimos estar en el viewport: el formulario hace scroll.
    return { found:true, visible: r.height>2 && el.offsetParent !== null, top:Math.round(r.top), h:Math.round(r.height) };
  };
  return { repetir: find('Repetir cada mes'), dividir: find('Dividir este gasto') };
}"""
SETUP_FORM = """() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showWelcomeCarousel=false; c.showOnbV2=false; c.tab='home';
  c.openNew();
  c.form.amount='40'; c.form.category='food'; c.form.description='QA arriendo';
  c.analyzed=true;  // dispara el x-show de los toggles
  return { is_split:c.form.is_split, recurringOn:c.recurringOn, sheetOpen:c.sheetOpen, onb:c.showOnbV2 };
}"""
ENABLE_BOTH = """() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  if (c.coach) c.coach.open = false;
  c.recurringOn = true; c.recurringDay = 5;
  c.toggleSplit();
  c.form.split_people = [{name:'Tú',pct:50,you:true,color:'#507D5A'},{name:'ZRSPLIT_Ana',pct:50,color:'#7000FF'}];
  c.splitPickerIdx = -1;
  return { is_split:c.form.is_split, recurringOn:c.recurringOn };
}"""
SAVE_TPL = """async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.form.description = '%s';
  await c.saveRecurringTemplate({ amount:40, category:'food', description:'%s', is_income:false, payment_method:null });
  const t = c.recurringTemplates.find(x => x.description === '%s');
  return t ? { is_split:t.is_split, split_pct:t.split_pct, split_total:t.split_total, split_persona:t.split_persona, split_people:t.split_people } : null;
}""" % (MARK, MARK, MARK)

def run():
    port = free_port(); serve(port)
    url = f"http://127.0.0.1:{port}/"
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
        page.wait_for_timeout(1500)

        print("setup form:", page.evaluate(SETUP_FORM)); page.wait_for_timeout(400)
        v1 = page.evaluate(VIS)
        print("\n[1] con monto, ambos toggles visibles ANTES de activar:")
        print("   Repetir:", v1["repetir"], "| Dividir:", v1["dividir"])
        if not (v1["repetir"] and v1["repetir"]["visible"] and v1["dividir"] and v1["dividir"]["visible"]):
            print("   [FALLA] algún toggle no visible"); failures += 1
        else: print("   [PASS] ambos visibles")

        print("enable both:", page.evaluate(ENABLE_BOTH)); page.wait_for_timeout(400)
        v2 = page.evaluate(VIS)
        print("\n[2] con Repetir+Dividir ACTIVADOS, ambos siguen visibles:")
        print("   Repetir:", v2["repetir"], "| Dividir:", v2["dividir"])
        if not (v2["repetir"] and v2["repetir"]["visible"] and v2["dividir"] and v2["dividir"]["visible"]):
            print("   [FALLA] un toggle se escondió al activar el otro"); failures += 1
        else: print("   [PASS] coexisten")
        page.screenshot(path=os.path.join(os.environ.get("TEMP","."), "zepo-rec-split-toggles.png"))

        tpl = page.evaluate(SAVE_TPL)
        print("\n[3] plantilla creada con split:")
        print("   ", tpl)
        if not (tpl and tpl.get("is_split") and tpl.get("split_persona")):
            print("   [FALLA] la plantilla no guardó el split"); failures += 1
        else: print("   [PASS] is_split + split_persona ok")
        # toma limpia del composer con ambos toggles ON (coach fuera)
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); if(c.coach)c.coach.open=false;}")
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(os.environ.get("TEMP","."), "zepo-rec-split-toggles.png"))
        # abrir gestor para screenshot
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app')); if(c.coach)c.coach.open=false; c.sheetOpen=false; c.recurringManagerOpen=true;}")
        page.wait_for_timeout(600)
        page.screenshot(path=os.path.join(os.environ.get("TEMP","."), "zepo-rec-split-manager.png"))
        # limpiar la plantilla de prueba creada en [3]
        page.evaluate("""async () => {
          const c = window.Alpine.$data(document.querySelector('#app'));
          const t = c.recurringTemplates.find(x => x.description === '%s');
          if (t && t.id) { try { await window.sb.from('recurring_templates').delete().eq('id', t.id); } catch(e){} }
        }""" % MARK)
        ctx.close(); wk.close()
    print("\n=== %s ===" % ("TODO PASS" if failures==0 else f"{failures} FALLAS"))
    print("screenshots: %TEMP%/zepo-rec-split-toggles.png , zepo-rec-split-manager.png")
    return failures

if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
