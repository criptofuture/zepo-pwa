#!/usr/bin/env python3
"""
QA E2E REAL: lote con FECHAS REPARTIDAS (el caso que no se podia borrar).

Crea un lote de 3 items en 3 fechas distintas (una fuera de la ventana de ~2 meses de
loadExpenses) y verifica:
  1. el historial lo trocea por fecha  ->  el chip "+N en otras fechas" avisa
  2. Importaciones lo lista COMPLETO (3 items, total y rango correctos)
  3. borrar desde Importaciones se lleva las 3 filas, incluida la fuera de ventana

Login demo. Sale 1 si falla.
"""
import sys, time, socket, threading, http.server, functools, os
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
TAG = "IMP_" + str(int(time.time()))

TODAY = date.today()
D_HOY = TODAY.isoformat()
D_MES_PASADO = (TODAY - timedelta(days=25)).isoformat()
D_VIEJO = (TODAY - timedelta(days=200)).isoformat()   # fuera de la ventana de loadExpenses


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

# Inserta directo contra Supabase con la sesion del usuario: replica un Excel importado
# (mismo batch_id, fechas repartidas) sin depender del parser de archivos.
CREATE_JS = """
async ([tag, dates]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const bid = (crypto.randomUUID ? crypto.randomUUID() : 'b'+Date.now());
  const rows = dates.map((d, i) => ({
    user_id: c.user.id, amount: (i+1)*10, category: 'food',
    description: tag + ' item' + i, date: d, is_income: false, is_split: false,
    batch_id: bid, batch_label: tag + ' excel',
    space_id: c._currentSpaceId(),
  }));
  const r = await sb.from('expenses').insert(rows).select('id');
  if (r.error) return { error: r.error.message };
  await c.loadExpenses();
  // El insert de arriba salta el codigo de la app, que es quien invalida el indice:
  // aqui lo forzamos a mano para simular el estado post-importacion.
  await c.loadBatchIndex(true);
  return { batchId: bid, ids: (r.data||[]).map(x=>x.id) };
}
"""

VERIFY_CHIP_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab = 'home';
  const grouped = c.recentExpensesGrouped || [];
  const entry = grouped.find(g => g._isBatch && (g.items||[]).some(it => (it.description||'').startsWith(tag)));
  if (!entry) return { found: false };
  return {
    found: true,
    itemsEnTarjeta: entry.items.length,
    extra: c.batchExtra(entry),
    countTotalCargado: c._batchCounts[entry.batch_id] || 0,
  };
}
"""

VERIFY_IMPORTS_JS = """
async ([tag, batchId]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.openImportsManager();
  const b = (c.importsList||[]).find(x => x.batch_id === batchId);
  if (!b) return { found: false, total: (c.importsList||[]).length, error: c.importsError };
  return {
    found: true, count: b.count, total: b.total,
    minDate: b.minDate, maxDate: b.maxDate,
    rango: c.batchRange(b), label: b.batch_label,
  };
}
"""

VERIFY_EDIT_JS = """
async ([batchId]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const b = (c.importsList||[]).find(x => x.batch_id === batchId);
  await c.editImport(b);
  const info = c.batchEditInfo || {};
  const r = { sheetOpen: c.sheetOpen, editingBatch: c.editingBatch,
              parsed: (c.parsedItems||[]).length,
              infoCount: info.count, infoTotal: info.total, infoLabel: info.label };
  c.sheetOpen = false; c.editingBatch = null; c.batchEditInfo = null; c.parsedItems = [];
  return r;
}
"""

DELETE_JS = """
async ([batchId]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.askConfirm = () => Promise.resolve(true);
  await c.openImportsManager();
  const b = (c.importsList||[]).find(x => x.batch_id === batchId);
  if (!b) return { skipped: true };
  await c.deleteImport(b);
  return { done: true };
}
"""

VERIFY_DELETE_JS = """
async ([tag, batchId]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  // Contra la BD, no contra memoria: la fila vieja vive fuera de la ventana de loadExpenses.
  const r = await sb.from('expenses').select('id').eq('user_id', c.user.id).eq('batch_id', batchId);
  return { quedan: (r.data||[]).length, enMemoria: (c.expenses||[]).filter(e=>(e.description||'').startsWith(tag)).length };
}
"""

CLEANUP_JS = """
async ([batchId]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await sb.from('expenses').delete().eq('user_id', c.user.id).eq('batch_id', batchId);
  return true;
}
"""


def run(url):
    dates = [D_HOY, D_MES_PASADO, D_VIEJO]
    batch_id = None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err:
            print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function(
            "()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}",
            timeout=20000)
        page.wait_for_timeout(2000)

        created = page.evaluate(CREATE_JS, [TAG, dates])
        if created.get("error"):
            print("[FALLA] insert:", created["error"]); browser.close(); return False
        batch_id = created["batchId"]
        page.wait_for_timeout(1500)

        try:
            chip = page.evaluate(VERIFY_CHIP_JS, TAG)
            imports = page.evaluate(VERIFY_IMPORTS_JS, [TAG, batch_id])
            edit = page.evaluate(VERIFY_EDIT_JS, [batch_id])
            page.evaluate(DELETE_JS, [batch_id]); page.wait_for_timeout(2500)
            deleted = page.evaluate(VERIFY_DELETE_JS, [TAG, batch_id])
        finally:
            page.evaluate(CLEANUP_JS, [batch_id])
        browser.close()

    checks = [
        ("HOME: la tarjeta muestra solo parte del lote", chip.get("found") and chip.get("itemsEnTarjeta", 0) < 3),
        ("HOME: el chip avisa de los que faltan", chip.get("extra", 0) >= 1),
        ("IMPORTACIONES: encuentra el lote", imports.get("found") is True),
        ("IMPORTACIONES: cuenta los 3, no solo los visibles", imports.get("count") == 3),
        ("IMPORTACIONES: total = 10+20+30", abs((imports.get("total") or 0) - 60) < 0.01),
        ("IMPORTACIONES: rango cubre la fila vieja", imports.get("minDate") == D_VIEJO and imports.get("maxDate") == D_HOY),
        ("IMPORTACIONES: rango con dos fechas", " – " in (imports.get("rango") or "")),
        ("EDITAR: abre el editor con los 3 items", edit.get("sheetOpen") is True and edit.get("parsed") == 3),
        ("EDITAR: el resumen dice 3 y $60", edit.get("infoCount") == 3 and abs((edit.get("infoTotal") or 0) - 60) < 0.01),
        ("BORRAR: no queda ninguna fila en la BD", deleted.get("quedan") == 0),
        ("BORRAR: sale de memoria", deleted.get("enMemoria") == 0),
    ]
    ok = all(v for _, v in checks)
    print("\n=== E2E Importaciones / lote con fechas repartidas ===")
    print(f"  fechas usadas: {D_VIEJO}, {D_MES_PASADO}, {D_HOY}")
    for label, v in checks:
        print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    if not ok:
        print("\n  chip:", chip, "\n  imports:", imports, "\n  edit:", edit, "\n  deleted:", deleted)
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - el lote con fechas repartidas se ve entero y se borra entero"
                  if ok else "FALLO - revisar loadImports/_batchItems/_purgeBatch/batchExtra"))
    sys.exit(0 if ok else 1)
