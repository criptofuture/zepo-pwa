#!/usr/bin/env python3
"""
QA E2E REAL: ciclo de vida de un gasto normal (alta -> editar -> borrar) y su recompute
en Home e Historial. Cubre el flujo base que nunca se probaba E2E.

login demo -> ADD gasto -> verifica en expenses + Home (recentExpensesGrouped) + Historial
-> EDIT monto -> verifica actualizado -> DELETE -> verifica que desaparece de todo. Limpia.
Sale 1 si algun paso falla.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TAG = "CRUD_" + str(int(time.time()))

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

ADD_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.sheetOpen=true; c.editingExpense=null; c.editingBatch=null; c.parsedItems=[]; c.analyzed=true;
  c.form={ amount:'12.34', description:tag+' gasto', category:'food',
    date:new Date().toISOString().slice(0,10), is_income:false, is_split:false,
    split_persona:'', split_pct:'', split_people:[] };
  await c.saveExpense();
  return true;
}
"""

def expid_js(tag):
    return ("(tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));"
            "const e=(c.expenses||[]).find(x=>(x.description||'').startsWith(tag));"
            "return e?e.id:null;}")

EDIT_JS = """
async ([tag, expId]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const exp = (c.expenses||[]).find(x => x.id === expId);
  if (!exp) return { error:'no encontrado para editar' };
  c.openEdit(exp);
  c.form.amount = '99.99';
  await c.saveExpense();
  return { ok:true };
}
"""

VERIFY_ADD_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='home';
  const inExpenses = (c.expenses||[]).some(e=>(e.description||'').startsWith(tag));
  const home = JSON.stringify(c.recentExpensesGrouped||[]);
  const inHome = home.includes(tag);
  return { inExpenses, inHome };
}
"""

VERIFY_EDIT_JS = """
(expId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const e = (c.expenses||[]).find(x=>x.id===expId);
  return { amount: e ? Number(e.amount) : null };
}
"""

VERIFY_HIST_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='history'; c.histAll=true;
  await c.loadHistory();
  const inHist = (c.historyData||[]).some(e=>(e.description||'').startsWith(tag));
  const grouped = JSON.stringify(c.filteredHistoryGroups||[]).includes(tag);
  return { inHist, grouped };
}
"""

DELETE_JS = """
async (expId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.askConfirm = () => Promise.resolve(true);
  const exp = (c.expenses||[]).find(x=>x.id===expId);
  if (!exp) return { error:'no encontrado para borrar' };
  c.editingExpense = exp; c.sheetOpen = true;
  await c.deleteExpense();
  return { ok:true };
}
"""

VERIFY_DEL_JS = """
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

        # ADD
        page.evaluate(ADD_JS, TAG)
        page.wait_for_function("(tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));"
                               "return (c.expenses||[]).some(e=>(e.description||'').startsWith(tag));}",
                               arg=TAG, timeout=15000)
        vadd = page.evaluate(VERIFY_ADD_JS, TAG)
        vhist = page.evaluate(VERIFY_HIST_JS, TAG)
        expId = page.evaluate(expid_js(TAG), TAG)

        # EDIT
        ed = page.evaluate(EDIT_JS, [TAG, expId])
        page.wait_for_timeout(2500)
        vedit = page.evaluate(VERIFY_EDIT_JS, expId)

        # DELETE
        page.evaluate(DELETE_JS, expId)
        page.wait_for_timeout(2500)
        vdel = page.evaluate(VERIFY_DEL_JS, TAG)
        browser.close()

    checks = [
        ("ADD: aparece en expenses",        vadd.get("inExpenses") is True),
        ("ADD: aparece en Home",            vadd.get("inHome") is True),
        ("ADD: aparece en Historial",       vhist.get("inHist") is True),
        ("ADD: aparece en grupos Historial",vhist.get("grouped") is True),
        ("EDIT: monto actualizado a 99.99", vedit.get("amount") == 99.99),
        ("DELETE: sale de expenses",        vdel.get("inExpenses") is False),
        ("DELETE: sale de Home",            vdel.get("inHome") is False),
    ]
    ok = all(v for _,v in checks)
    print("\n=== E2E CRUD gasto (alta/editar/borrar) ===")
    for label,v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port=free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - ciclo CRUD del gasto coherente en Home/Historial" if ok
                  else "FALLO - revisar alta/edicion/borrado o su recompute"))
    sys.exit(0 if ok else 1)
