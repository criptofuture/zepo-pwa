#!/usr/bin/env python3
"""
QA E2E REAL: editar un registro de "Debo" (ingreso dividido) QUITANDO la division
debe hacerlo DESAPARECER de deudas.

Bug reportado por Alvaro: edito un ingreso dividido quitando el split, guardo, y el
elemento SIGUE en "Debo > deudas". Causa: saveExpense solo recarga splits cuando el
nuevo estado ES split; al quitar el split (isSplit=false) NO llama loadSplits ->
pendingSplits queda viejo -> incomeSplitDebts lo sigue mostrando.

Flujo: login demo -> crea ingreso dividido (aparece en pendingSplits + incomeSplitDebts)
-> lo edita poniendo is_split=false -> verifica que desaparece de pendingSplits y de
incomeSplitDebts/deboDeudasGrouped. Limpia. Sale 1 si el registro sigue apareciendo.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TAG = "RMV_" + str(int(time.time()))

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
  c.sheetOpen=true; c.editingExpense=null; c.editingBatch=null; c.parsedItems=[]; c.analyzed=true;
  c.form={ amount:'100', description:tag+' ingreso', category:'salary',
    date:new Date().toISOString().slice(0,10), is_income:true, is_split:true,
    split_persona:'', split_pct:'',
    split_people:[ {name:'Tu',you:true,pct:50,color:'#507D5A'},
                   {name:tag+'_Ana',you:false,pct:50,color:'#7000FF'} ] };
  await c.saveExpense();
  return true;
}
"""

# Edita el registro creado y QUITA la division (is_split=false).
REMOVE_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab='cuentas'; c.cuentasTab='debo';
  const exp = (c.pendingSplits||[]).find(e => (e.description||'').startsWith(tag));
  if (!exp) return { error:'no se encontro el ingreso creado en pendingSplits' };
  c.openEdit(exp);
  c.form.is_split = false;          // QUITAR la division
  c.form.split_people = [];
  await c.saveExpense();
  return { expId: exp.id };
}
"""

VERIFY_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const stillInPending = (c.pendingSplits||[]).some(e => (e.description||'').startsWith(tag) && e.is_split);
  const debts = c.incomeSplitDebts || [];
  const stillInDebts = debts.some(d => (d.description||'').startsWith(tag));
  const grouped = JSON.stringify(c.deboDeudasGrouped || []);
  const stillInDeboList = grouped.includes(tag);
  return { stillInPending, stillInDebts, stillInDeboList };
}
"""

CLEANUP_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const targets = [...(c.expenses||[]), ...(c.pendingSplits||[])]
    .filter(e => (e.description||'').startsWith(tag));
  const seen = new Set(); let n=0;
  for (const exp of targets) { if (seen.has(exp.id)) continue; seen.add(exp.id);
    c.editingExpense=exp; c.sheetOpen=true; await c.deleteExpense(); n++; }
  return n;
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
        page.wait_for_timeout(2500)
        page.evaluate(CREATE_JS, TAG)
        page.wait_for_function(
            "(tag)=>{const c=window.Alpine.$data(document.querySelector('#app'));"
            "return (c.pendingSplits||[]).some(e=>(e.description||'').startsWith(tag));}",
            arg=TAG, timeout=15000)
        rm = page.evaluate(REMOVE_JS, TAG)
        if rm.get("error"): print("[FALLA]", rm["error"]); browser.close(); return False
        page.wait_for_timeout(3000)   # esperar recarga (si la hubiera)
        ver = page.evaluate(VERIFY_JS, TAG)
        page.evaluate(CLEANUP_JS, TAG)
        browser.close()

    print("\n=== E2E: editar 'Debo' quitando la division ===")
    checks = [
        ("desaparece de pendingSplits (is_split)", ver.get("stillInPending") is False),
        ("desaparece de incomeSplitDebts",         ver.get("stillInDebts") is False),
        ("desaparece de la lista deboDeudasGrouped", ver.get("stillInDeboList") is False),
    ]
    ok = all(v for _, v in checks)
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port=free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - quitar la division saca el registro de deudas"
                  if ok else "FALLO - el registro sigue en deudas tras quitar la division"))
    sys.exit(0 if ok else 1)
