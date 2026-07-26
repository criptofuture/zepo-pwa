#!/usr/bin/env python3
"""
QA E2E REAL (2 cuentas): saldar cuentas + centavos que cuadran.

Bug real (26-jul-2026): "Saldar cuentas con <amigo>" marcaba los cobros como 'settled'
pero NO tocaba expenses.split_status. Resultado: cada lado veia que el otro le debia y
que el no debia nada. En la cuenta de Alvaro quedaron $600.36 fantasma y en la de
Beatriz $198.84, con las dos apps mostrando $0 de deuda propia.

Bug real 2: el cobro se calculaba aparte (round(total*pct/100)) mientras la libreta
guardaba (total - mi parte). Con la mitad en medio centavo los dos numeros diferian:
total 2.35 -> libreta 1.17, cobro 1.18. Pasaba en el 50% de los montos.

FASE 1 - matematica de centavos sobre el codigo REAL que corre en la app
         (_splitAmounts): la suma de los cobros debe ser exactamente split_pending.
FASE 2 - saldar de verdad con 2 cuentas: tras settleWithFriend las DOS libretas y los
         cobros de AMBAS direcciones deben quedar en cero.

Verifica el estado REAL en Supabase (admin/service_role). Limpia todo.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
SENDER_EMAIL = "demo@zepo.test"; SENDER_PASS = "ZepoDemo2026!"
RECV_EMAIL = "qa-to@zepo.test"; RECV_PASS = "ZepoQAto2026!"
TAG = "ST_" + str(int(time.time()))
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
        return e.code, e.read().decode()[:300]


def ensure_user(email, password):
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(users, dict):
        for u in users.get("users", []):
            if u.get("email") == email: return u["id"]
    st, res = admin("POST", "/auth/v1/admin/users", {"email": email, "password": password, "email_confirm": True})
    return res.get("id") if isinstance(res, dict) else None


def seed_leg(owner, other, amount, pending, label, persona="QA amigo"):
    """Un gasto dividido pendiente de `owner` + su cobro aceptado hacia `other`."""
    today = time.strftime("%Y-%m-%d")
    st, rows = admin("POST", "/rest/v1/expenses", {
        "user_id": owner, "amount": amount - pending, "description": f"{TAG} {label}",
        "category": "food", "date": today, "is_income": False, "is_split": True,
        "split_status": "pendiente", "split_pending": pending, "split_total": amount,
        "split_pct": 50, "split_persona": persona,
    }, {"Prefer": "return=representation"})
    exp_id = rows[0]["id"] if isinstance(rows, list) and rows else None
    st, prs = admin("POST", "/rest/v1/payment_requests", {
        "from_user_id": owner, "to_user_id": other, "amount": pending,
        "description": f"{TAG} {label}", "category": "food", "expense_date": today,
        "status": "accepted", "origin_expense_id": exp_id,
    }, {"Prefer": "return=representation"})
    return exp_id, (prs[0]["id"] if isinstance(prs, list) and prs else None)


def cero(v):
    """v puede llegar como 0, '0.00' o None; `v or -1` convertiria el cero en -1."""
    return v is not None and float(v) == 0.0


def cleanup():
    admin("DELETE", f"/rest/v1/payment_requests?description=like.{TAG}*")
    admin("DELETE", f"/rest/v1/expenses?description=like.{TAG}*")


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

# Corre el repartidor REAL de la app sobre muchos montos. La regla que debe cumplirse:
# la suma de lo que se cobra es exactamente lo que la libreta dice que deben.
CENTS_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const r2 = n => Math.round(n * 100) / 100;
  let malos = [], probados = 0, ejemplo = null;
  for (let k = 1; k <= 20000; k++) {
    const total = k / 100;
    const pend = r2(total - r2(total * 50 / 100));
    const parts = c._splitAmounts(total, 50, [{ pct: 50, user_id: 'u1' }]);
    const suma = r2(parts.reduce((s, p) => s + p.amount, 0));
    probados++;
    if (suma !== pend) { if (malos.length < 5) malos.push({ total, pend, suma }); }
    if (total === 2.35) ejemplo = { total, pend, cobro: parts[0].amount };
  }
  // reparto entre 3 con porcentajes que no dividen exacto
  const tres = c._splitAmounts(1, 50, [{pct:16.67,user_id:'a'},{pct:16.67,user_id:'b'},{pct:16.66,user_id:'c'}]);
  const sumaTres = r2(tres.reduce((s,p)=>s+p.amount,0));
  return { probados, malos, ejemplo, sumaTres, pendTres: r2(1 - r2(1*50/100)) };
}
"""

SETTLE_JS = """
async (friendId) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.settleWithFriend(friendId, 'QA amigo', 0);
  return true;
}
"""


def login_and(url, email, password, js, arg):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [email, password])
        if err:
            browser.close(); return {"_login_err": err}
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(1500)
        res = page.evaluate(js, arg)
        page.wait_for_timeout(2000)
        browser.close()
        return res


def main():
    sender_id = ensure_user(SENDER_EMAIL, SENDER_PASS)
    recv_id = ensure_user(RECV_EMAIL, RECV_PASS)
    if not sender_id or not recv_id:
        print("[FALLA] no se pudo asegurar usuarios"); return 1
    cleanup()

    checks = []
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        base = f"http://127.0.0.1:{port}/index.html"

        # ── FASE 1: centavos sobre el codigo real ────────────────────────────
        m = login_and(base, SENDER_EMAIL, SENDER_PASS, CENTS_JS, None)
        if m.get("_login_err"):
            print("[FALLA] login remitente:", m["_login_err"]); cleanup(); return 1
        checks.append((f"centavos: {m.get('probados',0)} montos, cobros == libreta",
                       m.get("probados", 0) >= 20000 and not m.get("malos")))
        if m.get("malos"):
            print("   montos que no cuadran:", m["malos"])
        ej = m.get("ejemplo") or {}
        checks.append(("centavos: $2.35 al 50% cobra 1.17 (no 1.18)",
                       ej.get("pend") == 1.17 and ej.get("cobro") == 1.17))
        checks.append(("centavos: reparto entre 3 suma exacto",
                       m.get("sumaTres") == m.get("pendTres")))

        # ── FASE 2: saldar de verdad, 2 cuentas, deuda cruzada ───────────────
        a_exp, a_pr = seed_leg(sender_id, recv_id, 40.00, 20.00, "yo le presto")
        b_exp, b_pr = seed_leg(recv_id, sender_id, 12.00, 6.00, "el me presta")
        if not all([a_exp, a_pr, b_exp, b_pr]):
            print("[FALLA] no se sembro la deuda cruzada"); cleanup(); return 1

        r = login_and(base, SENDER_EMAIL, SENDER_PASS, SETTLE_JS, recv_id)
        if isinstance(r, dict) and r.get("_login_err"):
            print("[FALLA] login para saldar:", r["_login_err"]); cleanup(); return 1

        st, ea = admin("GET", f"/rest/v1/expenses?id=eq.{a_exp}&select=split_status,split_pending")
        ea = ea[0] if isinstance(ea, list) and ea else {}
        st, eb = admin("GET", f"/rest/v1/expenses?id=eq.{b_exp}&select=split_status,split_pending")
        eb = eb[0] if isinstance(eb, list) and eb else {}
        st, pa = admin("GET", f"/rest/v1/payment_requests?id=eq.{a_pr}&select=status")
        pa = pa[0] if isinstance(pa, list) and pa else {}
        st, pb = admin("GET", f"/rest/v1/payment_requests?id=eq.{b_pr}&select=status")
        pb = pb[0] if isinstance(pb, list) and pb else {}

        checks.append(("saldar: MI cobro queda 'settled'", pa.get("status") == "settled"))
        checks.append(("saldar: SU cobro queda 'settled'", pb.get("status") == "settled"))
        checks.append(("saldar: MI libreta baja a 'cobrado'", ea.get("split_status") == "cobrado"))
        checks.append(("saldar: MI libreta queda en $0", cero(ea.get("split_pending"))))
        checks.append(("saldar: SU libreta baja a 'cobrado'", eb.get("split_status") == "cobrado"))
        checks.append(("saldar: SU libreta queda en $0", cero(eb.get("split_pending"))))

        # ── FASE 3: saldar con UNO no puede borrar la deuda de un TERCERO ────
        # Un gasto dividido entre 3 tiene un solo split_pending que suma a todos. Si al
        # saldar con una persona se pone en 0, la deuda de los otros dos desaparece.
        c_exp, c_pr = seed_leg(sender_id, recv_id, 90.00, 60.00, "entre tres",
                               persona="QA amigo, Juan")
        if c_exp and c_pr:
            login_and(base, SENDER_EMAIL, SENDER_PASS, SETTLE_JS, recv_id)
            st, ec = admin("GET", f"/rest/v1/expenses?id=eq.{c_exp}&select=split_status,split_pending")
            ec = ec[0] if isinstance(ec, list) and ec else {}
            checks.append(("3 personas: NO se marca cobrado al saldar con una",
                           ec.get("split_status") == "pendiente"))
            checks.append(("3 personas: la deuda del tercero sigue viva",
                           float(ec.get("split_pending") or 0) == 60.0))
    finally:
        cleanup()

    print("\n=== E2E Saldar cuentas + centavos al centavo ===")
    for label, v in checks:
        print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    ok = len(checks) >= 11 and all(v for _, v in checks)
    print("\n" + ("OK - saldar cierra las DOS libretas y los cobros cuadran al centavo" if ok
                  else "FALLO - quedo descuadre entre las dos cuentas"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
