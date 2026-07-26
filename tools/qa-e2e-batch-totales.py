#!/usr/bin/env python3
"""
QA E2E REAL: los montos de un grupo no se contradicen entre pantallas.

Bug (26-jul-2026): la cabecera de "Editar grupo" sumaba split_total mientras el TOTAL
al pie de LA MISMA hoja sumaba amount -> $70.20 arriba y $47.03 abajo. Y la pantalla
Importaciones mostraba un tercer criterio. En Zepo un gasto compartido te cuesta TU
PARTE (asi lo cuentan monthTotal, presupuestos e Importaciones); lo adelantado se
cuenta aparte. La cabecera era la unica que no seguia esa regla.

Ahora: numero grande = tu parte (mismo criterio que Importaciones y el dashboard) y
una linea secundaria con el total completo + lo que te deben, que antes no se veia.

Se prueban los DOS casos, porque el pie de la hoja cambia de base entre ellos:
  MIXTO    (unos compartidos, otros no) -> las filas se editan con TU parte
  UNIFORME (todos 50/50 con la misma persona) -> las filas se editan con el TOTAL

Sale 1 si algun numero se contradice.
"""
import sys, os, time, json, socket, threading, http.server, functools
import urllib.request, urllib.error, urllib.parse
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
EMAIL, PASS = "demo@zepo.test", "ZepoDemo2026!"
TAG = "BT_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}


def admin(method, path, body=None, extra=None):
    headers = dict(H)
    if extra: headers.update(extra)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            txt = resp.read().decode() or "[]"
            return resp.status, (json.loads(txt) if txt.strip().startswith(("[", "{")) else txt)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]


def uid():
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(users, dict):
        for u in users.get("users", []):
            if u.get("email") == EMAIL: return u["id"]
    return None


def seed(user, label, items):
    """items: [(desc, monto_total, fecha, es_split)] -> devuelve (batch_id, ids)"""
    rows = []
    for desc, amt, date, sp in items:
        rows.append({
            "user_id": user, "amount": round(amt / 2, 2) if sp else amt,
            "description": f"{TAG} {desc}", "category": "market", "date": date,
            "is_income": False, "batch_label": label, "is_split": sp,
            "split_status":  "pendiente" if sp else None,
            "split_pending": round(amt - round(amt / 2, 2), 2) if sp else None,
            "split_total":   amt if sp else None,
            "split_pct":     50 if sp else None,
            "split_persona": "Beatriz" if sp else None,
        })
    st, res = admin("POST", "/rest/v1/expenses", rows, {"Prefer": "return=representation"})
    if not isinstance(res, list) or not res:
        print("[FALLA] seed:", st, res); sys.exit(1)
    ids = [r["id"] for r in res]
    admin("PATCH", "/rest/v1/expenses?id=in.(%s)" % ",".join(ids), {"batch_id": ids[0]})
    return ids[0], ids


def cleanup():
    admin("DELETE", "/rest/v1/expenses?description=like.%s" % urllib.parse.quote(TAG + "*"))


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv


LOGIN = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

MEDIR = """
async (batchId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.jrnOpen = false;
  await c.loadExpenses();
  const items = (c.expenses||[]).filter(e => e.batch_id === batchId);
  if (!items.length) return { ok:false };
  c.openEditBatch({ batch_id: batchId, items, date: items[0].date });
  const r2 = n => Math.round(n*100)/100;
  const info = c.batchEditInfo;
  return {
    ok: true,
    cabecera:  r2(info.total),           // el numero grande
    totalFull: r2(info.totalFull),       // linea secundaria: "en total"
    porCobrar: r2(info.porCobrar),       // linea secundaria: "por cobrar"
    pie:       r2(Number(c.form.amount)),// el TOTAL al pie de la hoja
    uniforme:  !!c.form.is_split,        // la hoja edita montos COMPLETOS
    filas:     c.parsedItems.length,
  };
}
"""

IMPORTS = """
async (batchId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.sheetOpen = false; c.editingBatch = null;
  await c.openImportsManager();
  const b = (c.importsList||[]).find(x => x.batch_id === batchId);
  c.importsManagerOpen = false;
  return b ? Math.round(b.total*100)/100 : null;
}
"""


def run(page, batch_id, ids, caso, esperado_parte, esperado_full, esperado_cobrar):
    m = page.evaluate(MEDIR, batch_id)
    if not m.get("ok"):
        return [(f"{caso}: el grupo se abrio", False)]
    imp = page.evaluate(IMPORTS, batch_id)
    checks = [
        (f"{caso}: cabecera = TU PARTE (${esperado_parte})", m["cabecera"] == esperado_parte),
        (f"{caso}: 'en total' = gasto completo (${esperado_full})", m["totalFull"] == esperado_full),
        (f"{caso}: 'por cobrar' = lo que te deben (${esperado_cobrar})", m["porCobrar"] == esperado_cobrar),
        (f"{caso}: cabecera == Importaciones (mismo criterio)", imp == esperado_parte),
    ]
    # Ningun numero de la hoja puede quedar sin respaldo: el pie tiene que coincidir con
    # la cabecera (grupo mixto) o con el "en total" de la linea secundaria (grupo uniforme).
    pie_ok = (m["pie"] == m["cabecera"]) or (m["pie"] == m["totalFull"])
    checks.append((f"{caso}: el TOTAL al pie (${m['pie']}) coincide con un numero mostrado arriba", pie_ok))
    if not pie_ok:
        print(f"   {caso} DESCUADRE -> pie {m['pie']} vs cabecera {m['cabecera']} / total {m['totalFull']}")
    return checks


def main():
    user = uid()
    if not user:
        print("[FALLA] no encuentro la cuenta demo"); return 1
    cleanup()
    checks = []
    try:
        # MIXTO: 2 compartidos (20 y 10) + 2 propios (7 y 3)
        #   tu parte = 10 + 5 + 7 + 3 = 25 | completo = 40 | por cobrar = 15
        b1, i1 = seed(user, "Grupo mixto " + TAG, [
            ("a", 20.00, "2026-07-05", True), ("b", 10.00, "2026-07-11", True),
            ("c",  7.00, "2026-07-14", False), ("d", 3.00, "2026-07-19", False)])
        # UNIFORME: los 3 compartidos 50/50 -> la hoja edita montos completos
        #   tu parte = 4 + 6 + 2.5 = 12.50 | completo = 25 | por cobrar = 12.50
        b2, i2 = seed(user, "Grupo uniforme " + TAG, [
            ("e", 8.00, "2026-07-06", True), ("f", 12.00, "2026-07-12", True),
            ("g", 5.00, "2026-07-18", True)])

        port = free_port(); serve(port); time.sleep(0.5)
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_context(viewport={"width": 390, "height": 844}).new_page()
            pg.on("dialog", lambda d: d.accept())
            pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded")
            pg.wait_for_timeout(1200)
            err = pg.evaluate(LOGIN, [EMAIL, PASS])
            if err:
                print("[FALLA] login:", err); return 1
            pg.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
            pg.wait_for_timeout(1500)
            checks += run(pg, b1, i1, "MIXTO",    25.00, 40.00, 15.00)
            checks += run(pg, b2, i2, "UNIFORME", 12.50, 25.00, 12.50)
            b.close()
    finally:
        cleanup()

    print("\n=== E2E Totales de un grupo (cabecera / pie / Importaciones) ===")
    for label, v in checks:
        print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    ok = len(checks) >= 10 and all(v for _, v in checks)
    print("\n" + ("OK - ningun monto del grupo se contradice entre pantallas" if ok
                  else "FALLO - hay montos que se contradicen"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
