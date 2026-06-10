#!/usr/bin/env python3
"""
QA E2E REAL: multi-item / batch (crear varios -> verificar agrupado en Home/Historial ->
borrar el batch -> verificar que desaparece). login demo. Sale 1 si falla.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TAG = "BATCH_" + str(int(time.time()))

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

CREATE_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.sheetOpen=true; c.editingExpense=null; c.editingBatch=null; c.analyzed=true;
  c.form={ amount:'0', description:'', category:'food',
    date:new Date().toISOString().slice(0,10), is_income:false, is_split:false,
    split_persona:'', split_pct:'', split_people:[] };
  c.parsedItems = [
    { description:tag+' uno', amount:5,  category:'food',      is_income:false, emoji:'🍽', label:'Comida',     color:'#C2553F' },
    { description:tag+' dos', amount:8,  category:'transport', is_income:false, emoji:'🚌', label:'Transporte', color:'#4F8A99' },
  ];
  await c.saveExpense();   // routea a saveMultiItems (>=2)
  return true;
}
"""

VERIFY_CREATE_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='home';
  const rows = (c.expenses||[]).filter(e=>(e.description||'').startsWith(tag));
  const batchIds = [...new Set(rows.map(r=>r.batch_id).filter(Boolean))];
  const grouped = c.recentExpensesGrouped||[];
  const batchEntry = grouped.find(g=>g._isBatch && (g.items||[]).some(it=>(it.description||'').startsWith(tag)));
  return { rowCount: rows.length, batchId: batchIds[0]||null, hasBatchEntry: !!batchEntry,
           batchItems: batchEntry ? batchEntry.items.length : 0 };
}
"""

DELETE_JS = """
async (batchId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.askConfirm = () => Promise.resolve(true);
  c.editingBatch = batchId; c.sheetOpen = true;
  await c.deleteBatch();
  return true;
}
"""

VERIFY_DELETE_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='home';
  const inExpenses = (c.expenses||[]).some(e=>(e.description||'').startsWith(tag));
  const inHome = JSON.stringify(c.recentExpensesGrouped||[]).includes(tag);
  return { inExpenses, inHome };
}
"""

def run(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)
        page.evaluate(CREATE_JS, TAG)
        page.wait_for_function("(tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));"
                               "return (c.expenses||[]).filter(e=>(e.description||'').startsWith(tag)).length>=2;}",
                               arg=TAG, timeout=15000)
        vc = page.evaluate(VERIFY_CREATE_JS, TAG)
        if vc.get("batchId"):
            page.evaluate(DELETE_JS, vc["batchId"]); page.wait_for_timeout(2500)
        vd = page.evaluate(VERIFY_DELETE_JS, TAG)
        browser.close()
    checks = [
        ("CREATE: 2 filas con batch_id", vc.get("rowCount")==2 and bool(vc.get("batchId"))),
        ("CREATE: agrupado en Home (batch)", vc.get("hasBatchEntry") is True),
        ("CREATE: el batch tiene 2 items", vc.get("batchItems")==2),
        ("DELETE: sale de expenses", vd.get("inExpenses") is False),
        ("DELETE: sale de Home", vd.get("inHome") is False),
    ]
    ok = all(v for _,v in checks)
    print("\n=== E2E Multi-item / batch (crear/borrar) ===")
    for label,v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port=free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - batch crea agrupado y se borra completo" if ok
                  else "FALLO - revisar saveMultiItems/deleteBatch/agrupado"))
    sys.exit(0 if ok else 1)
