#!/usr/bin/env python3
"""
QA E2E REAL para Zepo: editar un cobro de "Me deben" y agregar una persona.

POR QUE EXISTE: las pruebas con datos FALSOS no ejercen el flujo guardar->recargar
->recalcular contra Supabase, por eso se colo el bug "edito, agrego persona, guardo
y las cuentas NO se actualizan". Esta prueba inicia sesion REAL con la cuenta demo,
crea un cobro split real, lo edita agregando otra persona, guarda contra Supabase y
verifica:
  (BACKEND)  la fila persiste split_persona con la persona nueva.
  (FRONTEND) filteredPendingCobros / pendingCobrosGrouped reflejan la persona nueva.
  (REGRESION) tras guardar: sheetOpen=false, editingExpense=null, _busyEditing=false
              (el "freno" de performance NO debe quedar congelando las listas).
Limpia el dato de prueba al final. Sale 1 si algo falla (apto pre-deploy / CI).

USO:  python tools/qa-e2e-edit-split.py            # server local + Supabase real
      python tools/qa-e2e-edit-split.py URL        # contra una URL ya servida
"""
import sys, time, socket, threading, http.server, functools, os, json
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"
DEMO_PASS  = "ZepoDemo2026!"
TAG = "E2E_" + str(int(time.time()))   # marca unica para no chocar con datos reales

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

LOGIN_JS = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode = 'login'; c.authEmail = email; c.authPassword = password;
  await c.handleAuth();
  return c.authError || '';
}
"""

CREATE_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.sheetOpen = true; c.editingExpense = null; c.editingBatch = null;
  c.parsedItems = []; c.analyzed = true;
  c.form = {
    amount: '30', description: tag + ' cobro', category: 'food',
    date: new Date().toISOString().slice(0,10), is_income: false, is_split: true,
    split_persona: '', split_pct: '',
    split_people: [
      { name: 'Tu', you: true, pct: 50, color: '#507D5A' },
      { name: tag + '_Ana', you: false, pct: 50, color: '#7000FF' },
    ],
  };
  await c.saveExpense();
  return { sheetOpen: c.sheetOpen, editingExpense: !!c.editingExpense };
}
"""

# Edita el cobro recien creado y agrega una segunda persona (Susana).
EDIT_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab = 'cuentas';   // reproducir el escenario real: Alvaro estaba en "Me deben"
  const exp = (c.pendingSplits || []).find(e => (e.description||'').startsWith(tag));
  if (!exp) return { error: 'no se encontro el cobro creado en pendingSplits' };
  c.openEdit(exp);
  // openEdit reconstruye split_people desde split_persona. Agregamos a Susana.
  c.form.is_split = true;
  c.form.split_people = [
    { name: 'Tu', you: true, pct: 50, color: '#507D5A' },
    { name: tag + '_Ana',    you: false, pct: 25, color: '#7000FF' },
    { name: tag + '_Susana', you: false, pct: 25, color: '#D6D864' },
  ];
  await c.saveExpense();
  return {
    expId: exp.id,
    afterSheetOpen: c.sheetOpen,
    afterEditingExpense: !!c.editingExpense,
    afterBusyEditing: c._busyEditing,
  };
}
"""

VERIFY_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const exp = (c.pendingSplits || []).find(e => (e.description||'').startsWith(tag));
  const backendHasSusana = !!(exp && (exp.split_persona||'').includes('_Susana'));
  const rows = c.filteredPendingCobros || [];
  const frontendHasSusana = rows.some(r => (r.description||'').startsWith(tag)
                                        && (r._person||'').endsWith('_Susana'));
  // pendingCobrosGrouped es el getter MEMOIZADO que se renderiza en cuentas:
  const grouped = JSON.stringify(c.pendingCobrosGrouped || []);
  const groupedHasSusana = grouped.includes('_Susana');
  return { backendHasSusana, frontendHasSusana, groupedHasSusana,
           expId: exp ? exp.id : null };
}
"""

CLEANUP_JS = """
async (expId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.askConfirm = () => Promise.resolve(true);
  const exp = (c.pendingSplits || []).find(e => e.id === expId)
           || (c.expenses || []).find(e => e.id === expId);
  if (!exp) return 'ya no existe';
  c.editingExpense = exp; c.sheetOpen = true;
  await c.deleteExpense();
  return 'borrado';
}
"""

def run(url):
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())   # confirm() de deleteExpense
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)               # Alpine init

        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err:
            print("[FALLA] login:", err); browser.close(); return False
        # esperar sesion + carga inicial de splits
        page.wait_for_function(
            "() => { const c = window.Alpine.$data(document.querySelector('#app')); return !!c.user; }",
            timeout=20000)
        page.wait_for_timeout(2500)               # loadSplits inicial

        page.evaluate(CREATE_JS, TAG)
        # esperar a que el cobro aparezca en pendingSplits (loadSplits en background)
        page.wait_for_function(
            "(tag) => { const c = window.Alpine.$data(document.querySelector('#app'));"
            " return (c.pendingSplits||[]).some(e => (e.description||'').startsWith(tag)); }",
            arg=TAG, timeout=15000)

        ed = page.evaluate(EDIT_JS, TAG)
        results["edit"] = ed
        if ed.get("error"):
            print("[FALLA]", ed["error"]); browser.close(); return False
        # esperar recarga tras la edicion (split_persona con Susana en pendingSplits)
        try:
            page.wait_for_function(
                "(tag) => { const c = window.Alpine.$data(document.querySelector('#app'));"
                " const e = (c.pendingSplits||[]).find(x => (x.description||'').startsWith(tag));"
                " return e && (e.split_persona||'').includes('_Susana'); }",
                arg=TAG, timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(800)
        ver = page.evaluate(VERIFY_JS, TAG)
        results["verify"] = ver

        # limpieza
        if ver.get("expId"):
            cl = page.evaluate(CLEANUP_JS, ver["expId"])
            results["cleanup"] = cl

        browser.close()

    ed = results.get("edit", {}); ver = results.get("verify", {})
    checks = [
        ("tras guardar sheetOpen=false",      ed.get("afterSheetOpen") is False),
        ("tras guardar editingExpense=null",  ed.get("afterEditingExpense") is False),
        ("tras guardar _busyEditing=false",   ed.get("afterBusyEditing") is False),
        ("BACKEND persiste Susana",           ver.get("backendHasSusana") is True),
        ("FRONTEND filteredPendingCobros tiene Susana", ver.get("frontendHasSusana") is True),
        ("cuentas (pendingCobrosGrouped) tiene Susana", ver.get("groupedHasSusana") is True),
    ]
    ok = all(v for _, v in checks)
    print("\n=== Resultado E2E editar cobro + agregar persona ===")
    for label, v in checks:
        print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    print("  limpieza:", results.get("cleanup", "n/a"))
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - editar+agregar persona se refleja en cuentas (backend+frontend)"
                  if ok else "FALLO - la edicion no se reflejo; revisa saveExpense/_busyEditing"))
    sys.exit(0 if ok else 1)
