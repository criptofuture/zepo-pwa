#!/usr/bin/env python3
"""
QA E2E REAL: borrar un INGRESO desde el Historial lo quita de la vista + etiquetas
ingreso/gasto correctas. Reproduce el bug de Alvaro: el Historial (historyData) es una
fuente aparte de this.expenses; antes deleteExpense no la refrescaba -> el ingreso seguia.
Login demo. Sale 1 si falla.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"
TAG = "HISTDEL_" + str(int(time.time()))

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

LOGIN = """async ([e,p])=>{document.documentElement.classList.remove('browser-mode');
const g=document.getElementById('install-gate');if(g)g.remove();
const c=window.Alpine.$data(document.querySelector('#app'));
c.authMode='login';c.authEmail=e;c.authPassword=p;await c.handleAuth();return c.authError||'';}"""

CREATE_INCOME = """async ([tag])=>{const c=window.Alpine.$data(document.querySelector('#app'));
c.editingExpense=null;c.editingBatch=null;c.parsedItems=[];c.recurringOn=false;
c.form={amount:'321',description:tag,category:'other_income',date:new Date().toISOString().slice(0,10),
is_income:true,is_split:false,split_persona:'',split_pct:'',split_people:[],payment_method:'',
space_id:(c._currentSpaceId?c._currentSpaceId():null)};
await c.saveExpense();const r=(c.expenses||[]).find(e=>(e.description||'')===tag);return r?r.id:null;}"""

LOAD_HISTORY = """async ([id])=>{const c=window.Alpine.$data(document.querySelector('#app'));
c.histAll=true;await c.loadHistory();
return {inData:(c.historyData||[]).some(e=>e.id===id),inView:(c.historyExpenses||[]).some(e=>e.id===id)};}"""

OPEN_EDIT = """([id])=>{const c=window.Alpine.$data(document.querySelector('#app'));
const exp=(c.expenses||[]).find(e=>e.id===id)||(c.historyData||[]).find(e=>e.id===id);
if(!exp)return{ok:false};c.openEdit(exp);
return{ok:true,isIncome:c.form.is_income,editing:!!c.editingExpense};}"""

DELETE = """async ()=>{const c=window.Alpine.$data(document.querySelector('#app'));
c.askConfirm=()=>Promise.resolve(true);await c.deleteExpense();return true;}"""

VERIFY = """([id])=>{const c=window.Alpine.$data(document.querySelector('#app'));
return {inData:(c.historyData||[]).some(e=>e.id===id),inView:(c.historyExpenses||[]).some(e=>e.id===id),
inExpenses:(c.expenses||[]).some(e=>e.id===id)};}"""

def run(url):
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_context(viewport={"width":390,"height":844}).new_page()
        pg.on("dialog", lambda d: d.accept())
        pg.goto(url, wait_until="domcontentloaded"); pg.wait_for_timeout(1200)
        err = pg.evaluate(LOGIN, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); br.close(); return False
        pg.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        pg.wait_for_timeout(1800)
        iid = pg.evaluate(CREATE_INCOME, [TAG]); pg.wait_for_timeout(1500)
        before = pg.evaluate(LOAD_HISTORY, [iid]); pg.wait_for_timeout(300)
        edit = pg.evaluate(OPEN_EDIT, [iid]); pg.wait_for_timeout(300)
        pg.evaluate(DELETE); pg.wait_for_timeout(2500)
        after = pg.evaluate(VERIFY, [iid])
        br.close()
    checks = [
        ("ingreso creado", bool(iid)),
        ("aparece en Historial antes de borrar", before.get("inData") is True and before.get("inView") is True),
        ("al editar, form.is_income=true (etiquetas ingreso)", edit.get("ok") and edit.get("isIncome") is True),
        ("tras borrar: NO en historyData", after.get("inData") is False),
        ("tras borrar: NO en la vista del Historial", after.get("inView") is False),
        ("tras borrar: NO en expenses (home)", after.get("inExpenses") is False),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E borrar ingreso desde Historial ===")
    print(f"  id={iid}  before={before}  edit={edit}  after={after}")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - el Historial se refresca al borrar + etiquetas ingreso" if ok
                  else "FALLO - revisar deleteExpense/_maybeReloadHistory/etiquetas"))
    sys.exit(0 if ok else 1)
