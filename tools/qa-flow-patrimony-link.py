#!/usr/bin/env python3
"""WebKit (motor iOS): certifica la conexion flujo<->patrimonio (Fase A).
Ejerce las funciones REALES (savePatItem / _syncPatFlow / openPatEdit / deletePatItem)
interceptando SOLO la capa REST (stub en memoria). No escribe en Supabase ni depende
del plan de la cuenta demo (patrimony_items requiere Max via RLS server-side).
 [1] Crear inversion con 'genera ingreso' -> plantilla ligada is_income=true, amount/dia, desc 'Rendimiento'.
 [2] DOM: badge 'genera $.../mes' visible en la lista de patrimonio.
 [3] Editar el monto -> misma plantilla (sin duplicado) + precarga correcta en openPatEdit.
 [4] Apagar el toggle -> la plantilla ligada se borra.
 [5] Crear deuda con cuota -> plantilla is_income=false, desc 'Cuota'.
 [6] Borrar el item -> su plantilla ligada desaparece de recurringTemplates."""
import os, socket, threading, http.server, functools
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

PREP = """() => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  window.confirm = () => true;
}"""
LOGIN = """async ([email, password]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.devUnlockAll = true;
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}"""
# Intercepta la capa REST: recurring_templates vive en memoria; patrimony_items devuelve id fake.
STUB = """() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showWelcomeCarousel=false; c.showOnbV2=false; c.tab='patrimonio'; c.patSheetOpen=false;
  c.patrimonyItems = []; c.recurringTemplates = [];
  let n = 0;
  window.sbRestInsert = async (t, p) => {
    n++;
    if (t === 'recurring_templates') { const row = { ...p, id: 'rt-' + n, amount: Number(p.amount), day_of_month: Number(p.day_of_month) }; c.recurringTemplates.push(row); return [row]; }
    if (t === 'patrimony_items') { return [{ ...p, id: 'pat-' + n }]; }
    return [{ ...p, id: 'x-' + n }];
  };
  window.sbRestUpdate = async (t, k, v, p) => {
    if (t === 'recurring_templates') { const r = c.recurringTemplates.find(x => x[k] === v); if (r) { Object.assign(r, p); if (p.amount != null) r.amount = Number(p.amount); } }
    return true;
  };
  window.sbRestDelete = async (t, f) => {
    if (t === 'recurring_templates') { c.recurringTemplates = c.recurringTemplates.filter(x => x.id !== f.id); }
    return true;
  };
  c.loadRecurringTemplates = async () => {};   // no-op: no pisar la memoria con la BD
  c.loadPatrimony = async () => {};
  return true;
}"""
CREATE = """async (a) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.openPatNew(a.kind);
  c.patForm.name=a.name; c.patForm.current_value=a.val;
  c.patForm.gen_flow=true; c.patForm.flow_amount=a.amt; c.patForm.flow_day=a.day;
  await c.savePatItem();
  const it = c.patrimonyItems.find(x => x.name===a.name);
  const lk = it ? c.recurringTemplates.filter(t => t.patrimony_item_id===it.id) : [];
  return { itemId: it?it.id:null, sheet: c.patSheetOpen, n: lk.length, t: lk[0]||null };
}"""
EDIT = """async (a) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const it = c.patrimonyItems.find(x => x.id===a.itemId);
  c.openPatEdit(it);
  const pre = { gen: c.patForm.gen_flow, amt: c.patForm.flow_amount, day: c.patForm.flow_day };
  c.patForm.flow_amount=a.amt;
  await c.savePatItem();
  const lk = c.recurringTemplates.filter(t => t.patrimony_item_id===a.itemId);
  return { pre, n: lk.length, amount: lk[0]?Number(lk[0].amount):null, id: lk[0]?lk[0].id:null };
}"""
OFF = """async (a) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const it = c.patrimonyItems.find(x => x.id===a.itemId);
  c.openPatEdit(it); c.patForm.gen_flow=false;
  await c.savePatItem();
  return { n: c.recurringTemplates.filter(t => t.patrimony_item_id===a.itemId).length };
}"""
DELITEM = """async (a) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const it = c.patrimonyItems.find(x => x.id===a.itemId);
  c.openPatEdit(it);
  await c.deletePatItem();
  return { n: c.recurringTemplates.filter(t => t.patrimony_item_id===a.itemId).length,
           stillItem: !!c.patrimonyItems.find(x => x.id===a.itemId) };
}"""
BADGE = """() => [...document.querySelectorAll('.pat-flow-badge')].map(e => (e.textContent||'').trim()).filter(Boolean)"""

def run():
    port = free_port(); serve(port)
    url = f"http://127.0.0.1:{port}/"
    fails = 0
    with sync_playwright() as p:
        wk = p.webkit.launch()
        ctx = wk.new_context(**p.devices["iPhone 11"])
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1500)
        page.evaluate(PREP)
        err = page.evaluate(LOGIN, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); ctx.close(); wk.close(); return 1
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(800)
        page.evaluate(STUB); page.wait_for_timeout(300)

        inv = page.evaluate(CREATE, {"kind":"investment","name":"QAFLOW Inv","val":"10000","amt":"400","day":"5"})
        page.wait_for_timeout(600)
        print("\n[1] Inversion con 'genera ingreso':\n   ", inv)
        t = inv.get("t") or {}
        if inv.get("sheet") is not False:
            print("   [FALLA] el sheet no se cerro (savePatItem aborto):", inv.get("sheet")); fails += 1
        elif not inv.get("itemId") or inv.get("n") != 1:
            print("   [FALLA] esperaba 1 plantilla ligada, got", inv.get("n")); fails += 1
        elif not (t.get("is_income") is True and float(t.get("amount") or 0) == 400 and int(t.get("day_of_month") or 0) == 5):
            print("   [FALLA] is_income/amount/dia:", t.get("is_income"), t.get("amount"), t.get("day_of_month")); fails += 1
        elif not str(t.get("description") or "").startswith("Rendimiento"):
            print("   [FALLA] description no empieza 'Rendimiento':", t.get("description")); fails += 1
        else:
            print("   [PASS] ingreso $400 dia 5 -", t.get("description"))

        badges = page.evaluate(BADGE)
        print("\n[2] DOM badge en la lista:\n   ", badges)
        if not any("genera $400" in b for b in badges):
            print("   [FALLA] no se ve el badge 'genera $400/mes'"); fails += 1
        else:
            print("   [PASS] badge visible")

        ed = page.evaluate(EDIT, {"itemId": inv["itemId"], "amt": "500"}); page.wait_for_timeout(500)
        print("\n[3] Editar monto + precarga:\n   ", ed)
        if not (ed["pre"]["gen"] is True and str(ed["pre"]["amt"]) == "400"):
            print("   [FALLA] openPatEdit no precargo el flujo:", ed["pre"]); fails += 1
        elif ed["n"] != 1 or ed["amount"] != 500:
            print("   [FALLA] esperaba 1 plantilla con amount 500, got", ed["n"], ed["amount"]); fails += 1
        elif ed["id"] != (t.get("id")):
            print("   [FALLA] cambio el id (duplicado en vez de update):", ed["id"], "vs", t.get("id")); fails += 1
        else:
            print("   [PASS] misma plantilla, amount 500, sin duplicado")

        off = page.evaluate(OFF, {"itemId": inv["itemId"]}); page.wait_for_timeout(400)
        print("\n[4] Apagar el toggle:\n   ", off)
        if off["n"] != 0:
            print("   [FALLA] la plantilla no se borro, quedan", off["n"]); fails += 1
        else:
            print("   [PASS] plantilla ligada borrada")

        debt = page.evaluate(CREATE, {"kind":"debt","name":"QAFLOW Deuda","val":"8000","amt":"250","day":"10"})
        page.wait_for_timeout(500)
        print("\n[5] Deuda con cuota:\n   ", debt)
        td = debt.get("t") or {}
        if debt.get("n") != 1:
            print("   [FALLA] esperaba 1 plantilla ligada, got", debt.get("n")); fails += 1
        elif not (td.get("is_income") is False and float(td.get("amount") or 0) == 250):
            print("   [FALLA] is_income/amount:", td.get("is_income"), td.get("amount")); fails += 1
        elif not str(td.get("description") or "").startswith("Cuota"):
            print("   [FALLA] description no empieza 'Cuota':", td.get("description")); fails += 1
        else:
            print("   [PASS] gasto $250 dia 10 -", td.get("description"))

        dele = page.evaluate(DELITEM, {"itemId": debt["itemId"]}); page.wait_for_timeout(400)
        print("\n[6] Borrar el item:\n   ", dele)
        if dele["stillItem"] or dele["n"] != 0:
            print("   [FALLA] item/plantilla no desaparecieron:", dele); fails += 1
        else:
            print("   [PASS] item borrado + plantilla ligada desaparece")

        page.screenshot(path=os.path.join(os.environ.get("TEMP","."), "zepo-flow-link.png"))
        ctx.close(); wk.close()
    print("\n=== %s ===" % ("TODO PASS" if fails == 0 else f"{fails} FALLAS"))
    print("screenshot: %TEMP%/zepo-flow-link.png")
    return fails

if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
