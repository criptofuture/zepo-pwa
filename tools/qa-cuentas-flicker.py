#!/usr/bin/env python3
"""
Sonda del PARPADEO en Cuentas/"Me deben": la lista se pinta completa y luego se
encoge (desaparecen filas) en un re-render.

HIPOTESIS: filteredPendingCobros genera UNA fila por persona del mismo gasto, todas
con el MISMO entry.id; el x-for de PENDIENTES llavea por entry.id -> keys DUPLICADAS
cuando un gasto tiene 2+ deudores -> Alpine, al re-renderizar, descarta nodos.

Esta sonda inicia sesion real (demo), siembra un gasto con 2 deudores (Susana, Bea)
+ uno con 1, abre Cuentas, y mide:
  - keys duplicadas en pendingCobrosGrouped
  - filas de datos (filteredPendingCobros) vs tarjetas realmente renderizadas en DOM
  - si tras forzar un re-render el conteo de tarjetas BAJA (= el parpadeo)
Limpia los datos al final. Sale 1 si detecta el bug.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TAG = "FLK_" + str(int(time.time()))

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

# Siembra: un gasto split con DOS deudores (mismo id -> 2 filas, key duplicada) y uno con uno.
SEED_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  async function mk(desc, people) {
    c.sheetOpen=true; c.editingExpense=null; c.editingBatch=null; c.parsedItems=[]; c.analyzed=true;
    c.form={ amount:'30', description:desc, category:'food',
      date:new Date().toISOString().slice(0,10), is_income:false, is_split:true,
      split_persona:'', split_pct:'', split_people:people };
    await c.saveExpense();
  }
  await mk(tag+' dos', [
    {name:'Tu',you:true,pct:34,color:'#507D5A'},
    {name:tag+'_Susana',you:false,pct:33,color:'#7000FF'},
    {name:tag+'_Bea',   you:false,pct:33,color:'#D6D864'},
  ]);
  await mk(tag+' uno', [
    {name:'Tu',you:true,pct:50,color:'#507D5A'},
    {name:tag+'_Carlos',you:false,pct:50,color:'#7000FF'},
  ]);
  return true;
}
"""

MEASURE_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='cuentas'; c.cuentasTab='me-deben';
  const grouped = c.pendingCobrosGrouped || [];
  // misma key que usa el template (id + persona) para reflejar el render real
  const keys = grouped.map(e => e._isBatch ? ('B:'+e.batch_id) : ('I:'+((e.id||'')+'|'+(e._person||''))));
  const seen={}, dups=[];
  keys.forEach(k => { seen[k]=(seen[k]||0)+1; });
  Object.keys(seen).forEach(k => { if(seen[k]>1) dups.push(k+' x'+seen[k]); });
  return {
    dataRows: (c.filteredPendingCobros||[]).length,
    groupedRows: grouped.length,
    duplicateKeys: dups,
  };
}
"""

# Cuenta tarjetas realmente pintadas en la seccion PENDIENTES del DOM.
DOM_COUNT_JS = """
() => {
  // filas individuales de cobro pendiente = avatares 38px con gradiente (la lista "Me deben")
  const indiv = [...document.querySelectorAll('div[style*="border-radius:19px"]')]
    .filter(d => /gradient/.test(d.getAttribute('style')||'')).length;
  const batches = document.querySelectorAll('.batch-row').length;
  return { rows: indiv + batches };
}
"""

CLEANUP_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.askConfirm = () => Promise.resolve(true);
  const targets = (c.pendingSplits||[]).filter(e => (e.description||'').startsWith(tag));
  let n=0;
  for (const exp of targets) { c.editingExpense=exp; c.sheetOpen=true; await c.deleteExpense(); n++; }
  return n;
}
"""

def run(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2500)
        page.evaluate(SEED_JS, TAG)
        page.wait_for_function(
            "(tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));"
            "return (c.pendingSplits||[]).filter(e=>(e.description||'').startsWith(tag)).length>=2;}",
            arg=TAG, timeout=15000)
        # navegar a cuentas (como el boton: tab + loadSplits)
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.tab='cuentas';c.cuentasTab='me-deben';c.loadSplits&&c.loadSplits();}")
        page.wait_for_timeout(300)
        page.wait_for_timeout(400)
        m1 = page.evaluate(MEASURE_JS, TAG)
        dom1 = page.evaluate(DOM_COUNT_JS)
        # forzar re-render (lo que hace loadSplits al reasignar pendingSplits)
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));const s=c.pendingSplits;c.pendingSplits=[];c.pendingSplits=s.slice();}")
        page.wait_for_timeout(600)
        dom2 = page.evaluate(DOM_COUNT_JS)
        cl = page.evaluate(CLEANUP_JS, TAG)
        browser.close()

    print("\n=== Sonda parpadeo Cuentas/Me deben ===")
    print(f"  filas de datos (filteredPendingCobros): {m1['dataRows']}")
    print(f"  entradas agrupadas (pendingCobrosGrouped): {m1['groupedRows']}")
    print(f"  KEYS DUPLICADAS: {m1['duplicateKeys'] or 'ninguna'}")
    print(f"  DOM filas renderizadas tras 1er pintado: {dom1['rows']}")
    print(f"  DOM filas renderizadas tras re-render:   {dom2['rows']}")
    print(f"  limpieza: {cl} sembrados borrados")
    bug_dupkeys = len(m1['duplicateKeys']) > 0
    # bug si el DOM muestra MENOS filas que las que hay en datos (filas perdidas)
    bug_shrink  = dom2['rows'] < m1['groupedRows'] or dom1['rows'] < m1['groupedRows']
    print("\n  [%s] keys duplicadas presentes" % ('BUG' if bug_dupkeys else 'ok'))
    print("  [%s] DOM muestra menos filas que los datos (filas perdidas)" % ('BUG' if bug_shrink else 'ok'))
    return not (bug_dupkeys or bug_shrink)

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port=free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - sin keys duplicadas ni encogimiento" if ok else "BUG detectado - revisar :key del x-for de cobros"))
    sys.exit(0 if ok else 1)
