#!/usr/bin/env python3
"""Verifica que un gasto guardado HOY con fecha del mes pasado NO encabece
"Movimientos recientes".

this.expenses llega del servidor ordenado por fecha desc, pero las altas optimistas entran con
unshift (al frente): hasta que la recarga de fondo respondia, un gasto con fecha vieja se veia
arriba de todo en Inicio. Ahora _sortExpenses() reordena tras cada mutacion local.

Guarda de verdad (saveExpense real, no simulado) sobre elite@zepo.test y limpia al final.
Siembra 3 gastos de HOY primero: sin ellos la cuenta queda vacia y el gasto viejo seria
legitimamente el primero -> la prueba no probaria nada. Sale 1 si algun check falla."""
import os, socket, threading, http.server, functools, json, time, urllib.request, urllib.error
from datetime import date
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json"), encoding="utf-8"))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
EMAIL, PASSWORD = "elite@zepo.test", "ZepoQA2026!"
TAG = "ORD_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

today = date.today()
pm = today.replace(day=1)
prev = date(pm.year - 1, 12, 15) if pm.month == 1 else date(pm.year, pm.month - 1, 15)

def admin(method, path, body=None, extra=None):
    headers = dict(H)
    if extra: headers.update(extra)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            t = resp.read().decode() or "[]"
            return resp.status, (json.loads(t) if t.strip().startswith(("[", "{")) else t)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]

def uid_of(email):
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    for u in (users or {}).get("users", []):
        if u.get("email") == email: return u["id"]
    raise SystemExit("no encontre el usuario " + email)

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

PREP = """() => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
}"""
LOGIN = """async ([email, password]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.devUnlockAll = true; c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}"""
SAVE = """async ([desc, fecha]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showWelcomeCarousel=false; c.showOnbV2=false; c.tab='home';
  await c.loadExpenses();
  const antes = (c.recentExpenses[0] || {}).description || '(vacio)';
  c.parsedItems = []; c.editingExpense = null; c.editingBatch = null; c.recurringOn = false;
  c.form = { amount:'7.77', description:desc, category:'other', date:fecha,
             is_income:false, is_split:false, split_persona:'', split_pct:'',
             split_people:[], payment_method:null };
  await c.saveExpense();
  const lista = c.recentExpenses.map(e => e.description);
  const fechas = c.recentExpenses.map(e => e.date);
  const ordenadas = fechas.every((f, i) => i === 0 || fechas[i - 1] >= f);
  return { antes, primero: lista[0], enLosRecientes: lista.includes(desc),
           posicion: lista.indexOf(desc), total: c.expenses.length,
           fechas, fechasOrdenadas: ordenadas,
           guardado: c.expenses.some(e => e.description === desc) };
}"""

port = free_port(); srv = serve(port); base = f"http://127.0.0.1:{port}/index.html"
desc = TAG + "_viejo"
ok = True

# Contexto: 3 gastos de HOY. Sin esto la cuenta de QA esta vacia y el gasto viejo seria
# legitimamente el primero -> la prueba no probaria nada.
uid = uid_of(EMAIL)
seed = [{"user_id": uid, "description": f"{TAG}_hoy{i}", "amount": 1.0 + i, "category": "other",
         "date": today.isoformat(), "is_income": False,
         "created_at": "2026-01-01T00:00:00+00:00"} for i in range(3)]
st_seed, _ = admin("POST", "/rest/v1/expenses", seed, {"Prefer": "return=minimal"})
print("siembra de 3 gastos de hoy: status =", st_seed)
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        pg.on("dialog", lambda d: d.accept())
        pg.goto(base, wait_until="networkidle"); pg.wait_for_timeout(1200)
        pg.evaluate(PREP)
        err = pg.evaluate(LOGIN, [EMAIL, PASSWORD]); pg.wait_for_timeout(2500)
        if err: print("LOGIN ERROR:", err)
        pg.evaluate(PREP)
        r = pg.evaluate(SAVE, [desc, prev.isoformat()]); pg.wait_for_timeout(500)
        print("hoy =", today.isoformat(), " fecha del gasto =", prev.isoformat())
        print("resultado:", r)
        print()
        ok &= r["guardado"];            print(f"  [{'PASS' if r['guardado'] else 'FALLA'}] el gasto SI se guardo (la prueba no es vacia)")
        c1 = r["primero"] != desc;      ok &= c1
        print(f"  [{'PASS' if c1 else 'FALLA'}] NO encabeza 'Movimientos recientes' (primero = {r['primero']!r})")
        # Con 3 gastos de hoy sembrados, el de fecha vieja tiene que quedar DESPUES de los 3.
        c2 = r["posicion"] == 3;        ok &= c2
        print(f"  [{'PASS' if c2 else 'FALLA'}] queda detras de los 3 gastos de hoy (posicion esperada=3, observada={r['posicion']})")
        c3 = r["fechasOrdenadas"];      ok &= c3
        print(f"  [{'PASS' if c3 else 'FALLA'}] la lista completa queda ordenada por fecha desc ({r['fechas']})")
        b.close()
finally:
    srv.shutdown()
    st, _ = admin("DELETE", f"/rest/v1/expenses?description=like.{TAG}*")
    print(f"\n  limpieza: DELETE status={st}")
print("\n=== TODO PASS ===" if ok else "\n=== HAY FALLAS ===")
raise SystemExit(0 if ok else 1)
