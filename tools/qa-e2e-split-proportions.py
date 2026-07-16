#!/usr/bin/env python3
"""
QA E2E REAL: un split con proporciones DESIGUALES se guarda y se muestra tal cual.

POR QUE EXISTE: se colo a produccion el bug que reporto una usuaria — dividio un INGRESO
con proporciones propias y "Cuentas" se lo mostro en partes IGUALES. Causa: el gasto solo
guardaba split_pct (TU %) + split_persona (nombres) y cobroFor() reconstruia (100-tuPct)/n.
Ningun test probaba proporciones desiguales: por ese hueco se colo. Este test lo cierra.

FASE 1  gasto $100 dividido Tu 20 / Ana 50 / Luis 30 (no-amigos: prueba split_people puro)
        -> BD: split_pct=20 + split_people con 50 y 30 (igualado daria 40/40)
        -> Cuentas: filteredPendingCobros da 50 a Ana y 30 a Luis
FASE 2  abrir a editar -> el editor reconstruye 20/50/30 (antes igualaba a 20/40/40);
        cambiar a Ana 60 / Luis 20 y guardar -> BD y Cuentas reflejan lo nuevo
FASE 3  INGRESO $90 dividido Tu 40 / Ana 35 / Luis 25 -> incomeSplitDebts 31.50 y 22.50
        (era el caso 100% roto: en ingresos el monto salia solo del reparto igualado)
FASE 4  HISTORICO (el caso real de la usuaria): gasto legacy SIN split_people sembrado a
        mano + su cobro REAL de $100 hacia qa-to -> cobroFor debe devolver 100 (el cobro
        emitido), no 80 (el igualado), y el editor debe recuperar el 20/50/30 original.

Verifica BD (service_role) + getters + DOM. Limpia por TAG. Sale 1 si algo falla.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error, urllib.parse
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
RECV_EMAIL = "qa-to@zepo.test"
TAG = "SP_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}
TODAY = time.strftime("%Y-%m-%d")


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


def user_id(email):
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(users, dict):
        for u in users.get("users", []):
            if u.get("email") == email: return u["id"]
    return None


def db_expense(desc_prefix):
    q = urllib.parse.quote(desc_prefix + "*")   # la descripcion lleva espacios: sin quote, URL invalida
    st, rows = admin("GET", f"/rest/v1/expenses?description=like.{q}&select=*")
    return rows[0] if isinstance(rows, list) and rows else None


def seed_legacy(sender_id, recv_id, recv_name):
    """Split viejo (sin split_people) + su cobro real: replica el dato de la usuaria.
    Total 200 = Tu 20% (40) + qa-to 50% (100) + Ana 30% (60). Igualado daria 80 a cada uno."""
    st, rows = admin("POST", "/rest/v1/expenses", {
        "user_id": sender_id, "amount": 40, "description": TAG + " legacy", "category": "food",
        "date": TODAY, "is_income": False, "is_split": True, "split_status": "pendiente",
        "split_pending": 160, "split_total": 200, "split_pct": 20,
        "split_persona": recv_name + ", " + TAG + "_Bea",
    }, {"Prefer": "return=representation"})
    origin_id = rows[0]["id"] if isinstance(rows, list) and rows else None
    admin("POST", "/rest/v1/payment_requests", {
        "from_user_id": sender_id, "to_user_id": recv_id, "amount": 100,
        "description": TAG + " legacy", "category": "food", "expense_date": TODAY,
        "status": "pending", "origin_expense_id": origin_id,
    })
    return origin_id


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
  localStorage.setItem('zepo_a7_done_v1', '1');
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

# Crea un registro dividido con proporciones DESIGUALES via el flujo real de guardado.
CREATE_JS = """
async ([tag, isIncome, amount, pcts]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.sheetOpen = true; c.editingExpense = null; c.editingBatch = null;
  c.parsedItems = []; c.analyzed = true; c.recurringOn = false;
  c.form = {
    amount: String(amount), description: tag + (isIncome ? ' ingreso' : ' gasto'),
    category: isIncome ? 'salary' : 'food', date: new Date().toISOString().slice(0,10),
    is_income: isIncome, is_split: true, split_persona: '', split_pct: '',
    split_people: [
      { name: 'Tú',        you: true,  pct: pcts[0], color: '#507D5A' },
      { name: tag + '_Ana',  you: false, pct: pcts[1], color: '#8A6E9C' },
      { name: tag + '_Luis', you: false, pct: pcts[2], color: '#C9972F' },
    ],
  };
  await c.saveExpense();
  return { sheetOpen: c.sheetOpen };
}
"""

# Lo que ve el usuario en Cuentas, por persona.
CUENTAS_JS = """
([tag, personPrefix, isIncome]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab = 'cuentas';
  const rows = (isIncome ? c.incomeSplitDebts : c.filteredPendingCobros) || [];
  const mine = rows.filter(r => (r.description||'').startsWith(tag));
  const by = {};
  mine.forEach(r => { by[r._person] = r._amount; });
  const exp = (c.pendingSplits||[]).find(e => (e.description||'').startsWith(tag));
  // accountsByPerson se agrupa por PERSONA (no por descripcion): filtrar por el nombre.
  const accBy = {};
  (c.accountsByPerson||[]).filter(a => a.name.startsWith(personPrefix))
    .forEach(a => { accBy[a.name] = isIncome ? a.leDebes : (a.teDebe + a.porAceptar); });
  // CONTROL NEGATIVO: lo que daba la formula vieja (partes iguales). Si algun dia vuelve
  // a coincidir con `by`, el test dejo de discriminar y hay que rehacerlo.
  let oldEqual = null;
  if (exp) {
    const n = (exp.split_persona||'').split(',').filter(Boolean).length || 1;
    const total = exp.split_total || (exp.amount + (exp.split_pending || 0));
    oldEqual = Math.round(total * ((100 - (exp.split_pct || 50)) / n) / 100 * 100) / 100;
  }
  return { by, accBy, oldEqual, expId: exp ? exp.id : null };
}
"""

# Abre el registro guardado para editar y reporta los % que el editor reconstruyo.
OPEN_EDIT_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const exp = (c.pendingSplits||[]).find(e => (e.description||'').startsWith(tag));
  if (!exp) return { error: 'no encontrado en pendingSplits' };
  c.openEdit(exp);
  return { people: (c.form.split_people||[]).map(p => ({ name: p.name, pct: p.pct })),
           amount: c.form.amount };
}
"""

# Cambia las proporciones desde el editor abierto y guarda.
REPROPORTION_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const luis = c.form.split_people.find(p => (p.name||'').endsWith('_Luis'));
  const ana  = c.form.split_people.find(p => (p.name||'').endsWith('_Ana'));
  if (!luis || !ana) return { error: 'faltan personas en el editor' };
  ana.pct = 60; luis.pct = 20;
  await c.saveExpense();
  return { sheetOpen: c.sheetOpen };
}
"""

# Edita el gasto legacy (que YA tiene un cobro pendiente real) y lo vuelve a guardar.
EDIT_LEGACY_JS = """
async (tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const exp = (c.pendingSplits||[]).find(e => (e.description||'').startsWith(tag));
  if (!exp) return { error: 'legacy no encontrado' };
  c.openEdit(exp);
  c.form.description = tag + ' legacy editado';
  await c.saveExpense();
  return { sheetOpen: c.sheetOpen };
}
"""

LEGACY_JS = """
([tag, recvName]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab = 'cuentas';
  const exp = (c.pendingSplits||[]).find(e => (e.description||'').startsWith(tag));
  if (!exp) return { error: 'gasto legacy no cargado en pendingSplits' };
  const cobroReal = c.cobroFor(exp, recvName);
  const rebuilt = c._rebuildSplitPeople(exp).map(p => ({ name: p.name, pct: p.pct }));
  const rows = (c.filteredPendingCobros||[]).filter(r => (r.description||'').startsWith(tag));
  const by = {}; rows.forEach(r => { by[r._person] = r._amount; });
  return { cobroReal, rebuilt, by, hasSplitPeople: !!exp.split_people };
}
"""


def run(url, demo_id, recv_id, recv_name):
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)

        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err:
            print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function(
            "() => { const c = window.Alpine.$data(document.querySelector('#app')); return !!c.user; }",
            timeout=20000)
        page.wait_for_timeout(2500)

        def wait_split(tag):
            page.wait_for_function(
                "(tag) => { const c = window.Alpine.$data(document.querySelector('#app'));"
                " return (c.pendingSplits||[]).some(e => (e.description||'').startsWith(tag)); }",
                arg=tag, timeout=15000)

        # ---- FASE 1: gasto con proporciones desiguales 20/50/30 sobre $100
        page.evaluate(CREATE_JS, [TAG, False, 100, [20, 50, 30]])
        wait_split(TAG + " gasto")
        page.wait_for_timeout(600)
        out["f1_front"] = page.evaluate(CUENTAS_JS, [TAG + " gasto", TAG + "_", False])
        out["f1_db"] = db_expense(TAG + " gasto")

        # ---- FASE 2: editar reconstruye lo real y re-guardar cambia lo real
        out["f2_open"] = page.evaluate(OPEN_EDIT_JS, TAG + " gasto")
        out["f2_save"] = page.evaluate(REPROPORTION_JS, TAG + " gasto")
        page.wait_for_timeout(2500)
        out["f2_db"] = db_expense(TAG + " gasto")
        out["f2_front"] = page.evaluate(CUENTAS_JS, [TAG + " gasto", TAG + "_", False])

        # ---- FASE 3: INGRESO 40/35/25 sobre $90
        page.evaluate(CREATE_JS, [TAG + "I", True, 90, [40, 35, 25]])
        wait_split(TAG + "I ingreso")
        page.wait_for_timeout(600)
        out["f3_front"] = page.evaluate(CUENTAS_JS, [TAG + "I ingreso", TAG + "I_", True])
        out["f3_db"] = db_expense(TAG + "I ingreso")

        # ---- FASE 4: historico sin split_people, con cobro real
        seed_legacy(demo_id, recv_id, recv_name)
        page.evaluate("async () => { const c = window.Alpine.$data(document.querySelector('#app'));"
                      " await Promise.all([c.loadSplits(), c.loadPaymentRequests()]); }")
        page.wait_for_timeout(1500)
        out["f4"] = page.evaluate(LEGACY_JS, [TAG + " legacy", recv_name])

        # ---- FASE 5: editar un split que YA tiene cobro pendiente no lo duplica NI lo borra.
        # qa-to NO es amigo de demo: su cobro no se puede re-emitir, asi que cancelarlo
        # dejaria a la otra persona sin la deuda. Debe sobrevivir intacto.
        out["f5_edit"] = page.evaluate(EDIT_LEGACY_JS, TAG + " legacy")
        page.wait_for_timeout(2500)
        st, prs = admin("GET", f"/rest/v1/payment_requests?description=like.{urllib.parse.quote(TAG + '*')}&select=id,amount,status")
        out["f5_prs"] = prs if isinstance(prs, list) else []

        browser.close()
    return out


def money(v):
    return None if v is None else round(float(v) + 0.0, 2)


def check(out, recv_name):
    f1f, f1d = out.get("f1_front", {}), out.get("f1_db") or {}
    f2o, f2d, f2f = out.get("f2_open", {}), out.get("f2_db") or {}, out.get("f2_front", {})
    f3f, f3d = out.get("f3_front", {}), out.get("f3_db") or {}
    f4 = out.get("f4", {})
    sp1 = {p["name"]: p["pct"] for p in (f1d.get("split_people") or [])}
    sp2 = {p["name"]: p["pct"] for p in (f2d.get("split_people") or [])}
    sp3 = {p["name"]: p["pct"] for p in (f3d.get("split_people") or [])}
    reb = {p["name"]: p["pct"] for p in (f4.get("rebuilt") or [])}
    A, L = TAG + "_Ana", TAG + "_Luis"
    AI, LI = TAG + "I_Ana", TAG + "I_Luis"

    checks = [
        # FASE 1 — persistencia + render por persona
        ("F1 BD guarda split_pct=20 (tu parte)",        money(f1d.get("split_pct")) == 20.0),
        ("F1 BD guarda split_people con 50 y 30",       sp1.get(A) == 50 and sp1.get(L) == 30),
        ("F1 BD mi parte = $20 (no $33.33)",            money(f1d.get("amount")) == 20.0),
        ("F1 Cuentas: Ana $50 (igualado daria $40)",    money(f1f.get("by", {}).get(A)) == 50.0),
        ("F1 Cuentas: Luis $30 (igualado daria $40)",   money(f1f.get("by", {}).get(L)) == 30.0),
        ("F1 saldo por persona: Ana $50",               money(f1f.get("accBy", {}).get(A)) == 50.0),
        ("F1 saldo por persona: Luis $30",              money(f1f.get("accBy", {}).get(L)) == 30.0),
        # FASE 2 — el editor reconstruye lo REAL, no partes iguales
        ("F2 editor reconstruye Tu 20%",                any(p["name"] == "Tú" and p["pct"] == 20 for p in f2o.get("people", []))),
        ("F2 editor reconstruye Ana 50% (no 40)",       any(p["name"] == A and p["pct"] == 50 for p in f2o.get("people", []))),
        ("F2 editor reconstruye Luis 30% (no 40)",      any(p["name"] == L and p["pct"] == 30 for p in f2o.get("people", []))),
        ("F2 editor abre con el TOTAL ($100)",          money(f2o.get("amount")) == 100.0),
        ("F2 re-guardar persiste Ana 60 / Luis 20",     sp2.get(A) == 60 and sp2.get(L) == 20),
        ("F2 Cuentas tras editar: Ana $60",             money(f2f.get("by", {}).get(A)) == 60.0),
        ("F2 Cuentas tras editar: Luis $20",            money(f2f.get("by", {}).get(L)) == 20.0),
        # FASE 3 — INGRESO (el caso reportado)
        ("F3 BD ingreso guarda split_people 35/25",     sp3.get(AI) == 35 and sp3.get(LI) == 25),
        ("F3 Debo ingreso: Ana $31.50 (igualado $27)",  money(f3f.get("by", {}).get(AI)) == 31.5),
        ("F3 Debo ingreso: Luis $22.50 (igualado $27)", money(f3f.get("by", {}).get(LI)) == 22.5),
        ("F3 saldo por persona ingreso: Ana $31.50",    money(f3f.get("accBy", {}).get(AI)) == 31.5),
        # FASE 4 — historico: manda el cobro real, no el igualado
        ("F4 el gasto legacy NO tiene split_people",    f4.get("hasSplitPeople") is False),
        ("F4 cobroFor usa el cobro real ($100, no $80)", money(f4.get("cobroReal")) == 100.0),
        ("F4 Cuentas muestra $100 a " + recv_name,      money(f4.get("by", {}).get(recv_name)) == 100.0),
        ("F4 editor recupera el 50% real de " + recv_name, reb.get(recv_name) == 50),
        ("F4 editor deduce el 30% del resto",           reb.get(TAG + "_Bea") == 30),
        # FASE 5 — editar un split con cobro vivo: ni duplicado ni deuda destruida
        ("F5 editar el legacy guarda (hoja cerrada)",   out.get("f5_edit", {}).get("sheetOpen") is False),
        ("F5 el cobro de $100 sigue vivo tras editar",  [p for p in out.get("f5_prs", []) if p.get("status") == "pending" and money(p.get("amount")) == 100.0] != []),
        ("F5 no se duplico el cobro (sigue 1 pendiente)", len([p for p in out.get("f5_prs", []) if p.get("status") == "pending"]) == 1),
        # CONTROL NEGATIVO — el test solo vale si lo esperado difiere de lo que daba el bug
        ("CTRL la formula vieja daba $40 a cada uno (por eso fallaba)", money(f1f.get("oldEqual")) == 40.0),
        ("CTRL vieja != nueva en gasto",                money(f1f.get("oldEqual")) != money(f1f.get("by", {}).get(A))),
        ("CTRL la formula vieja daba $27 en el ingreso", money(f3f.get("oldEqual")) == 27.0),
        ("CTRL vieja != nueva en ingreso",              money(f3f.get("oldEqual")) != money(f3f.get("by", {}).get(AI))),
    ]
    return checks


if __name__ == "__main__":
    demo_id = user_id(DEMO_EMAIL)
    recv_id = user_id(RECV_EMAIL)
    st, profs = admin("GET", f"/rest/v1/profiles?user_id=eq.{recv_id}&select=display_name")
    recv_name = profs[0]["display_name"] if isinstance(profs, list) and profs else "qa-to"
    if not demo_id or not recv_id:
        print("[FALLA] faltan cuentas de prueba (demo@zepo.test / qa-to@zepo.test)"); sys.exit(1)
    cleanup()
    try:
        if len(sys.argv) > 1:
            out = run(sys.argv[1], demo_id, recv_id, recv_name)
        else:
            port = free_port(); serve(port); time.sleep(0.5)
            out = run(f"http://127.0.0.1:{port}/index.html", demo_id, recv_id, recv_name)
        if out is False:
            sys.exit(1)
        checks = check(out, recv_name)
        ok = all(v for _, v in checks)
        print("\n=== Resultado E2E proporciones de split ===")
        for label, v in checks:
            print(f"  [{'PASS' if v else 'FALLA'}] {label}")
        print(f"\n  {sum(1 for _, v in checks if v)}/{len(checks)}")
        if not ok:
            print("\n  --- datos crudos ---")
            print(json.dumps({k: v for k, v in out.items() if k.startswith(("f1_front", "f2_open", "f3_front", "f4"))}, indent=2, default=str)[:2000])
    finally:
        cleanup()
    print("\n" + ("OK - las proporciones desiguales se guardan y se muestran tal cual (gasto, ingreso, edicion e historico)"
                  if ok else "FALLO - el reparto NO respeta las proporciones guardadas"))
    sys.exit(0 if ok else 1)
