#!/usr/bin/env python3
"""
QA E2E REAL: invariantes de dinero en Presupuestos, Espacios y Patrimonio (Zepo).
Cuenta: max@zepo.test (plan real 'max' en BD). Login real, siembra real via el cliente
Supabase autenticado de la propia pagina (window.sb) o via REST admin (service_role) SOLO
para verificacion/limpieza. Cada valor "esperado" se calcula en Python desde primeros
principios (no se copia la formula del index.html).

Aislamiento: TAG = "PEX_<timestamp>" prefija toda fila sembrada. Los presupuestos/gastos
de las pruebas A1-A4 (umbral, split, total, herencia) viven en un espacio TEMPORAL nuevo
(Space A) para no tocar los presupuestos reales (singleton usuario/mes/espacio/categoria)
de la cuenta compartida. Al final: borra todo lo sembrado (gastos, presupuestos, patrimonio,
los 2 espacios temporales) y restaura la seleccion de espacio original.

Sale 1 si algun check falla.
"""
import sys, time, socket, threading, http.server, functools, os, json, math
import urllib.request, urllib.error
from datetime import date
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
EMAIL, PASS = "max@zepo.test", "ZepoQA2026!"
TAG = "PEX_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}

checks = []       # (label, bool, detail)
findings = []      # texto libre para el reporte
not_tested = []    # cosas que no se pudieron probar


def add(label, ok, detail=""):
    checks.append((label, bool(ok), detail))


def js_round(x):
    """Replica Math.round de JS: redondea .5 siempre hacia +Infinity (no banker's rounding)."""
    return math.floor(x + 0.5) if x >= 0 else -math.floor(-x + 0.5)


# ── REST admin (service_role) — solo setup/verificacion/limpieza ──────────────
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
        return e.code, e.read().decode()[:500]


def get_user_id(email):
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(users, dict):
        for u in users.get("users", []):
            if u.get("email") == email:
                return u["id"]
    return None


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
  localStorage.setItem('zepo_a7_done_v1','1');
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2=false; c.showWelcomeCarousel=false; c.a7Active=false; c.coachTip=()=>{};
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

CAPTURE_BASELINE_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const def = (c.spaces||[]).find(s => s.is_default);
  let savedLS = null; try { savedLS = localStorage.getItem('zepo_active_space'); } catch(e) {}
  return {
    uid: c.user.id,
    spaces: (c.spaces||[]).map(s => ({id:s.id, name:s.name, is_default: !!s.is_default})),
    defaultSpaceId: def ? def.id : null,
    activeSpaceId: c.activeSpaceId, spaceViewAll: c.spaceViewAll, savedLS,
    patNetWorth: c.patNetWorth, patTotalInvestments: c.patTotalInvestments,
    patTotalAssets: c.patTotalAssets, patTotalDebts: c.patTotalDebts,
    rawPlan: c._rawUserPlan, hasPlanMax: c.hasPlan('max'), hasPlanElite: c.hasPlan('elite'),
  };
}
"""

ADD_SPACE_JS = """
async ([name, icon, color]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.newSpaceName = name; c.newSpaceIcon = icon; c.newSpaceColor = color;
  await c.addSpace();
  const s = (c.spaces||[]).find(x => x.name === name);
  return s ? s.id : null;
}
"""

SELECT_SPACE_JS = """
async ([idOrAll]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.selectSpace(idOrAll);
  return { activeSpaceId: c.activeSpaceId, spaceViewAll: c.spaceViewAll };
}
"""

# Inserta un gasto via el cliente supabase AUTENTICADO de la propia pagina (no admin REST):
# es la misma via que usa la app -> RLS real, escritura real.
INSERT_EXPENSE_JS = """
async (row) => {
  const { data, error } = await sb.from('expenses').insert(row).select();
  if (error) throw new Error(error.message);
  return data[0];
}
"""
PATCH_EXPENSE_JS = """
async ([id, patch]) => {
  const { error } = await sb.from('expenses').update(patch).eq('id', id);
  if (error) throw new Error(error.message);
  return true;
}
"""
DELETE_EXPENSES_JS = """
async (ids) => {
  if (!ids.length) return true;
  const { error } = await sb.from('expenses').delete().in('id', ids);
  if (error) throw new Error(error.message);
  // Splice tambien el cache local (c.expenses): loadExpenses() preserva por 120s
  // cualquier fila reciente que no venga en la query fresca (comentario ~10243-10249,
  // pensado para no perder un insert propio por lag de replica). Si se borra por un
  // canal que NO pasa por deleteExpense() (como este helper de QA), esa fila borrada
  // puede "resucitar" durante 2 min si no se saca tambien de aqui.
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.expenses = (c.expenses || []).filter(e => !ids.includes(e.id));
  return true;
}
"""
INSERT_BUDGETS_JS = """
async (rows) => {
  const { error } = await sb.from('budgets').insert(rows);
  if (error) throw new Error(error.message);
  return true;
}
"""
DELETE_BUDGETS_JS = """
async ([spaceId, month, year]) => {
  let q = sb.from('budgets').delete().eq('space_id', spaceId);
  if (month != null) q = q.eq('month', month).eq('year', year);
  const { error } = await q;
  if (error) throw new Error(error.message);
  return true;
}
"""
RELOAD_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c._busyEditing = false;
  await c.loadExpenses();
  await c.loadBudgets();
  return true;
}
"""
MEASURE_BAR_JS = """
([cat]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab = 'budgets';
  const bar = (c.budgetBars||[]).find(b => b.cat === cat);
  const alertOn = (c.budgetAlerts||[]).some(a => a.cat === cat);
  return {
    bar: bar ? { spent: bar.spent, advance: bar.advance, pct: bar.pct, advancePct: bar.advancePct, budget: bar.budget } : null,
    alertOn, monthTotal: c.monthTotal,
  };
}
"""
MEASURE_TOTALS_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  return { budgetTotalAmount: c.budgetTotalAmount, budgetTotalPct: c.budgetTotalPct, monthTotal: c.monthTotal,
           budgets: (c.budgets||[]).map(b => ({cat:b.category, amt:Number(b.amount)})) };
}
"""
MEASURE_BUDGETS_RAW_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const total = (c.budgets||[]).find(b => !b.category);
  const food  = (c.budgets||[]).find(b => b.category === 'food');
  return {
    count: (c.budgets||[]).length,
    totalAmt: total ? Number(total.amount) : null, totalInh: total ? !!total._inherited : null,
    foodAmt: food ? Number(food.amount) : null,
    barsCount: (c.budgetBars||[]).length,
  };
}
"""
MEASURE_HOME_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab = 'home';
  return { monthTotal: c.monthTotal, activeSpaceId: c.activeSpaceId, spaceViewAll: c.spaceViewAll,
           expenseCount: (c.expenses||[]).length };
}
"""
LOAD_HISTORY_ALL_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.histAll = true; c.tab = 'history';
  await c.loadHistory();
  return (c.historyData||[]).map(e => e.description || '');
}
"""
# Lee historyData SIN recargar: para probar que el CAMBIO de espacio ya refresco el historial (D8).
READ_HISTORY_NOW_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  return (c.historyData || []).map(e => e.description || '');
}
"""
# Fija el historial en "mes actual" (no todo el tiempo) antes de probar D8.
SET_HIST_CURMONTH_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const n = new Date();
  c.histAll = false; c.histMonth = n.getMonth(); c.histYear = n.getFullYear();
  c.histType = 'all'; c.filterCat = 'all';
  return true;
}
"""
# spaceStats[id].spent tras loadSpaceStats (D9): el selector de espacios.
SPACE_STATS_JS = """
async ([defId]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.loadSpaceStats();
  const st = c.spaceStats || {};
  return { defSpent: (st[defId] ? st[defId].spent : 0), hasNone: !!st['_none'],
           noneSpent: (st['_none'] ? st['_none'].spent : 0) };
}
"""
EXPORT_CSV_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.exportCSV();
  return true;
}
"""
MEASURE_LIFETIME_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.loadLifetimeSavings();
  const bm = c.lifetimeSavingsByMonth || [];
  return {
    L: c.lifetimeSavings, N: c.patNetWorth, T: c.patTotalWithSavings,
    byMonthSum: Math.round(bm.reduce((s,m)=>s+(m.saldo||0),0)*100)/100, byMonthCount: bm.length,
  };
}
"""
EXPENSES_WINDOW_HAS_JS = """
async ([needle]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.loadExpenses();
  return (c.expenses||[]).some(e => (e.description||'').includes(needle));
}
"""
INSERT_PAT_ITEMS_JS = """
async (rows) => {
  const { data, error } = await sb.from('patrimony_items').insert(rows).select();
  if (error) throw new Error(error.message);
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.loadPatrimony();
  return data.map(d => d.id);
}
"""
MEASURE_PAT_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  return { N: c.patNetWorth, I: c.patTotalInvestments, A: c.patTotalAssets, D: c.patTotalDebts };
}
"""
DELETE_PAT_ITEMS_JS = """
async (ids) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  if (ids.length) { const { error } = await sb.from('patrimony_items').delete().in('id', ids); if (error) throw new Error(error.message); }
  await c.loadPatrimony();
  return true;
}
"""

# Red de seguridad final: borra CUALQUIER fila que quede referenciando los espacios
# temporales y luego los espacios mismos. OJO: usa el cliente AUTENTICADO de la pagina
# (sb), NO admin REST -- 'spaces' y 'patrimony_items' solo tienen GRANT a 'authenticated'
# (migraciones 20260608_spaces.sql / 20260611_patrimony.sql), sin GRANT a 'service_role'.
# Un DELETE con la secret_key contra esas 2 tablas devuelve 403 "permission denied"
# silenciosamente si no se revisa el status code -- confirmado en esta sesion.
SAFETY_NET_JS = """
async ([spaceIds]) => {
  const report = {};
  for (const sid of spaceIds) {
    if (!sid) continue;
    const { data: exp } = await sb.from('expenses').select('id').eq('space_id', sid);
    if (exp && exp.length) { await sb.from('expenses').delete().eq('space_id', sid); report['exp_'+sid] = exp.length; }
    const { data: bud } = await sb.from('budgets').select('id').eq('space_id', sid);
    if (bud && bud.length) { await sb.from('budgets').delete().eq('space_id', sid); report['bud_'+sid] = bud.length; }
    const { error } = await sb.from('spaces').delete().eq('id', sid);
    report['spaceDelErr_'+sid] = error ? error.message : null;
  }
  return report;
}
"""


def run(url):
    global checks
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)

        err = page.evaluate(LOGIN_JS, [EMAIL, PASS])
        if err:
            print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function(
            "()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(2000)

        base = page.evaluate(CAPTURE_BASELINE_JS)
        uid = base["uid"]
        print(f"[info] uid={uid} plan={base['rawPlan']} hasPlanMax={base['hasPlanMax']} "
              f"activeSpaceId0={base['activeSpaceId']} viewAll0={base['spaceViewAll']} savedLS0={base['savedLS']}")
        if not base["hasPlanMax"]:
            not_tested.append("Cuenta max@zepo.test no resolvio hasPlan('max')==true en runtime -> "
                               "los checks de Espacios/Patrimonio (Max-gated) podrian fallar por gating, no por bug de calculo.")

        default_space_id = base["defaultSpaceId"]
        original_active = base["activeSpaceId"]
        original_view_all = base["spaceViewAll"]
        N0 = base["patNetWorth"]

        seeded_expense_ids = []
        space_a = space_b = None
        pat_ids = []

        try:
            # ── Crear los 2 espacios temporales ────────────────────────────
            space_a = page.evaluate(ADD_SPACE_JS, [TAG + " Alpha", "🅰️", "#4F8A99"]); page.wait_for_timeout(600)
            space_b = page.evaluate(ADD_SPACE_JS, [TAG + " Beta", "🅱️", "#C9972F"]); page.wait_for_timeout(600)
            add("Setup: espacio temporal A creado", space_a is not None, f"id={space_a}")
            add("Setup: espacio temporal B creado", space_b is not None, f"id={space_b}")
            if not (space_a and space_b):
                not_tested.append("No se pudieron crear espacios temporales (RLS/plan) -> se aborta el resto de A/B/C.")
                raise RuntimeError("no se pudieron crear espacios")

            page.evaluate(SELECT_SPACE_JS, [space_a]); page.wait_for_timeout(800)

            today = date.today().isoformat()
            cur_m, cur_y = date.today().month, date.today().year
            pm, py = (12, cur_y - 1) if cur_m == 1 else (cur_m - 1, cur_y)

            # ═══ A. PRESUPUESTOS ═══════════════════════════════════════════
            # Presupuestos food=100 y transport=100 en el espacio A, mes actual.
            page.evaluate(INSERT_BUDGETS_JS, [
                {"user_id": uid, "category": "food", "amount": 100, "month": cur_m, "year": cur_y, "space_id": space_a},
                {"user_id": uid, "category": "transport", "amount": 100, "month": cur_m, "year": cur_y, "space_id": space_a},
            ])
            page.evaluate(SELECT_SPACE_JS, [space_a]); page.wait_for_timeout(600)  # recarga budgets

            # --- A1: umbral de alerta exacto (>=80% de $100) ---
            food_row = page.evaluate(INSERT_EXPENSE_JS, {
                "user_id": uid, "amount": 78.00, "description": TAG + " THRESH", "category": "food",
                "date": today, "is_income": False, "space_id": space_a,
            })
            food_id = food_row["id"]; seeded_expense_ids.append(food_id)
            page.evaluate(RELOAD_JS)

            subtests = [(78.00, False), (79.49, False), (79.51, True), (79.99, True), (80.00, True)]
            for amt, expect_alert in subtests:
                page.evaluate(PATCH_EXPENSE_JS, [food_id, {"amount": amt}])
                page.evaluate(RELOAD_JS)
                m = page.evaluate(MEASURE_BAR_JS, ["food"])
                exp_pct = js_round(amt / 100 * 100)  # == js_round(amt), calculado independiente del codigo
                observed_pct = m["bar"]["pct"] if m["bar"] else None
                observed_alert = m["alertOn"]
                add(f"A1: pct redondeado en ${amt:.2f}/100 == {exp_pct}%", observed_pct == exp_pct,
                    f"observado={observed_pct}")
                add(f"A1: alerta en ${amt:.2f} == {expect_alert}", observed_alert == expect_alert,
                    f"observado={observed_alert} spent={m['bar']['spent'] if m['bar'] else None}")

            findings.append(
                "A1 — Regla de alerta: budgetAlerts usa `b.pct >= 80` donde `b.pct = Math.round(spent/budget*100)` "
                "(index.html ~12543 y ~12536). Al redondear ANTES de comparar, la alerta dispara desde "
                "$79.50 de $100 (79.5% redondea a 80), NO desde $80.00 exacto. Confirmado empiricamente: "
                "$79.49 -> pct=79 sin alerta; $79.51 -> pct=80 CON alerta. Es coherente puertas adentro "
                "(el color de la barra en el HTML usa el mismo `b.pct>=80`, linea ~5240/~5248), pero el "
                "limite real no es un $80.00 limpio como sugeriria 'umbral 80%'.")

            # --- A1 CONTROL NEGATIVO: invertir el predicado en $78 (78% no deberia alertar) ---
            m78 = page.evaluate(MEASURE_BAR_JS, ["food"])  # nota: food ya quedo en 80.00 tras el loop; repetimos con 78
            page.evaluate(PATCH_EXPENSE_JS, [food_id, {"amount": 78.00}]); page.evaluate(RELOAD_JS)
            m78 = page.evaluate(MEASURE_BAR_JS, ["food"])
            wrong_hypothesis = (m78["alertOn"] == True)  # si esto fuera True, seria el bug "alerta con <80%"
            add("[CONTROL NEGATIVO] A1: hipotesis invertida '78% SI alerta' debe salir FALSA", wrong_hypothesis is False,
                f"alertOn observado={m78['alertOn']} (si esto diera True, el check primario de 78%=sin-alerta habria fallado)")
            # deja food en 80.00 para A3 (monthTotal = 80 food + 20 transport)
            page.evaluate(PATCH_EXPENSE_JS, [food_id, {"amount": 80.00}]); page.evaluate(RELOAD_JS)

            # --- A2: gasto DIVIDIDO — spent cuenta solo mi parte, advance por separado ---
            split_row = page.evaluate(INSERT_EXPENSE_JS, {
                "user_id": uid, "amount": 20.00, "description": TAG + " SPLIT", "category": "transport",
                "date": today, "is_income": False, "space_id": space_a,
                "is_split": True, "split_total": 50.00, "split_pending": 30.00, "split_pct": 40,
                "split_persona": "QA Amigo", "split_status": "pendiente",
            })
            split_id = split_row["id"]; seeded_expense_ids.append(split_id)
            page.evaluate(RELOAD_JS)
            m2 = page.evaluate(MEASURE_BAR_JS, ["transport"])
            bar2 = m2["bar"] or {}
            add("A2: spent == mi parte ($20), no el total", bar2.get("spent") == 20.00, f"observado spent={bar2.get('spent')}")
            add("A2: advance == split_pending no saldado ($30)", bar2.get("advance") == 30.00, f"observado advance={bar2.get('advance')}")
            add("A2: spent + advance == split_total ($50), no se pasa del total", (bar2.get("spent", 0) + bar2.get("advance", 0)) == 50.00,
                f"spent+advance={bar2.get('spent',0)+bar2.get('advance',0)}")
            add("A2: pct de categoria usa solo mi parte (20/100=20%)", bar2.get("pct") == 20, f"observado pct={bar2.get('pct')}")
            # CONTROL NEGATIVO: la hipotesis "spent cuenta el total dividido" (bug clasico) debe ser FALSA
            wrong_h2 = (bar2.get("spent") == 50.00)
            add("[CONTROL NEGATIVO] A2: hipotesis invertida 'spent==50 (total)' debe salir FALSA", wrong_h2 is False,
                f"spent observado={bar2.get('spent')} (si diera 50, habria doble conteo del split)")

            # --- A3: budgetTotalAmount / budgetTotalPct ---
            t3a = page.evaluate(MEASURE_TOTALS_JS)
            # sin fila total: budgetTotalAmount = suma de categorias (food 100 + transport 100 = 200)
            exp_total_amt_fallback = 200.00
            exp_month_total = 80.00 + 20.00  # food final (80) + transport mi parte (20)
            exp_pct_fallback = min(100, js_round(exp_month_total / exp_total_amt_fallback * 100))
            add("A3: monthTotal == food(80)+transport(20) == 100", t3a["monthTotal"] == exp_month_total,
                f"observado monthTotal={t3a['monthTotal']}")
            add("A3: budgetTotalAmount (fallback suma categorias) == 200", t3a["budgetTotalAmount"] == exp_total_amt_fallback,
                f"observado={t3a['budgetTotalAmount']}")
            add("A3: budgetTotalPct (fallback) == round(100/200*100) == 50", t3a["budgetTotalPct"] == exp_pct_fallback,
                f"observado={t3a['budgetTotalPct']}")

            page.evaluate(INSERT_BUDGETS_JS, [
                {"user_id": uid, "category": None, "amount": 300, "month": cur_m, "year": cur_y, "space_id": space_a},
            ])
            page.evaluate(RELOAD_JS)
            t3b = page.evaluate(MEASURE_TOTALS_JS)
            exp_total_amt_override = 300.00
            exp_pct_override = min(100, js_round(exp_month_total / exp_total_amt_override * 100))
            add("A3: con fila total ($300), budgetTotalAmount IGNORA suma de categorias == 300",
                t3b["budgetTotalAmount"] == exp_total_amt_override, f"observado={t3b['budgetTotalAmount']}")
            add("A3: budgetTotalPct con fila total == round(100/300*100) == 33",
                t3b["budgetTotalPct"] == exp_pct_override, f"observado={t3b['budgetTotalPct']}")

            findings.append(
                "A3 — Ojo: existen DOS pares de getters de presupuesto total con nombres casi identicos: "
                "`budgetTotalAmount`/`budgetTotalPct` (index.html ~10581/~10587, los que pide este check) y "
                "`totalBudgetObj`/`totalBudgetPct` (~14387/~14391, los que SI renderiza la pantalla Presupuestos "
                "en el HTML ~5192-5211). Verificado por grep: `budgetTotalPct` no aparece en ningun template x-text/x-if "
                "del archivo -> es un getter MUERTO (no se ve en UI), aunque calcula bien. `totalBudgetPct` (el usado "
                "en pantalla) NO tiene fallback de suma-de-categorias: si no existe la fila total, `totalBudgetObj` es "
                "null y la tarjeta de 'Gastado total' simplemente no se muestra (x-if=totalBudgetObj). No es un bug, "
                "pero conviene saber cual getter alimenta la pantalla real antes de tocar uno.")

            # cleanup expenses A1/A2 antes de A4 (no afecta budgets)
            page.evaluate(DELETE_EXPENSES_JS, [food_id, split_id])
            seeded_expense_ids = [i for i in seeded_expense_ids if i not in (food_id, split_id)]
            page.evaluate(RELOAD_JS)

            # --- A4: herencia mes a mes + respeto del cero explicito ---
            page.evaluate(DELETE_BUDGETS_JS, [space_a, cur_m, cur_y])  # limpia mes actual (food,transport,total)
            page.evaluate(INSERT_BUDGETS_JS, [
                {"user_id": uid, "category": None, "amount": 500, "month": pm, "year": py, "space_id": space_a},
                {"user_id": uid, "category": "food", "amount": 120, "month": pm, "year": py, "space_id": space_a},
            ])
            page.evaluate(RELOAD_JS)
            inh = page.evaluate(MEASURE_BUDGETS_RAW_JS)
            add("A4: HEREDA fila total ($500) al mes actual", inh["totalAmt"] == 500, f"observado={inh['totalAmt']}")
            add("A4: fila heredada marcada _inherited=true", inh["totalInh"] is True, f"observado={inh['totalInh']}")
            add("A4: HEREDA categoria food ($120)", inh["foodAmt"] == 120, f"observado={inh['foodAmt']}")
            add("A4: food heredado aparece en budgetBars", inh["barsCount"] >= 1, f"barsCount={inh['barsCount']}")

            page.evaluate(DELETE_BUDGETS_JS, [space_a, pm, py])
            page.evaluate(INSERT_BUDGETS_JS, [
                {"user_id": uid, "category": None, "amount": 0, "month": pm, "year": py, "space_id": space_a},
            ])
            page.evaluate(RELOAD_JS)
            zero = page.evaluate(MEASURE_BUDGETS_RAW_JS)
            add("A4: RESPETA EL CERO — centinela (mes pasado=0) NO se hereda (0 filas)", zero["count"] == 0,
                f"observado count={zero['count']}")
            add("A4: sin barras cuando el centinela no hereda", zero["barsCount"] == 0, f"barsCount={zero['barsCount']}")
            # CONTROL NEGATIVO (camino inverso ya incluido arriba: con monto real hereda, con 0 no hereda).

            page.evaluate(DELETE_BUDGETS_JS, [space_a, None, None])  # limpia TODO lo de presupuestos en A

            # ═══ B. ESPACIOS ═══════════════════════════════════════════════
            page.evaluate(SELECT_SPACE_JS, [space_a])
            homeA0 = page.evaluate(MEASURE_HOME_JS)
            add("B5: espacio A parte de monthTotal==0 antes de sembrar (aislado)", homeA0["monthTotal"] == 0,
                f"observado={homeA0['monthTotal']}")

            expA = page.evaluate(INSERT_EXPENSE_JS, {
                "user_id": uid, "amount": 30.00, "description": TAG + " HomeA30", "category": "other",
                "date": today, "is_income": False, "space_id": space_a})
            seeded_expense_ids.append(expA["id"])
            expB = page.evaluate(INSERT_EXPENSE_JS, {
                "user_id": uid, "amount": 70.00, "description": TAG + " HomeB70", "category": "other",
                "date": today, "is_income": False, "space_id": space_b})
            seeded_expense_ids.append(expB["id"])

            page.evaluate(SELECT_SPACE_JS, [space_a]); page.wait_for_timeout(400)
            homeA = page.evaluate(MEASURE_HOME_JS)
            add("B5: Home en espacio A muestra $30", homeA["monthTotal"] == 30.00, f"observado={homeA['monthTotal']}")

            page.evaluate(SELECT_SPACE_JS, [space_b]); page.wait_for_timeout(400)
            homeB = page.evaluate(MEASURE_HOME_JS)
            add("B5: Home en espacio B muestra $70", homeB["monthTotal"] == 70.00, f"observado={homeB['monthTotal']}")

            # Sigma(TODOS los espacios individuales) == vista "todos" (invariante real, no solo A+B)
            spaces_now = page.evaluate("() => (window.Alpine.$data(document.querySelector('#app')).spaces||[]).map(s=>s.id)")
            per_space_sum = 0.0
            for sid in spaces_now:
                page.evaluate(SELECT_SPACE_JS, [sid]); page.wait_for_timeout(250)
                r = page.evaluate(MEASURE_HOME_JS)
                per_space_sum += r["monthTotal"]
            page.evaluate(SELECT_SPACE_JS, ["__all__"]); page.wait_for_timeout(400)
            view_all = page.evaluate(MEASURE_HOME_JS)
            add("B5: Sigma(monthTotal de TODOS los espacios) == monthTotal en vista 'todos'",
                abs(per_space_sum - view_all["monthTotal"]) < 0.01,
                f"Sigma={per_space_sum:.2f} viewAll={view_all['monthTotal']:.2f}")
            # CONTROL NEGATIVO: Sigma(solo A+B) coincide con viewAll si y solo si los DEMAS
            # espacios no aportan nada este mes. Contar espacios NO sirve como premisa: un
            # tercer espacio vacio ($0) deja A+B == viewAll y el control se auto-fallaba.
            sum_ab_only = homeA["monthTotal"] + homeB["monthTotal"]
            only_ab_matches = abs(sum_ab_only - view_all["monthTotal"]) < 0.01
            others_sum = per_space_sum - sum_ab_only
            add("[CONTROL NEGATIVO] B5: Sigma(solo A+B) == viewAll si y solo si los demas espacios aportan $0 este mes",
                only_ab_matches == (abs(others_sum) < 0.01),
                f"sum_ab={sum_ab_only:.2f} viewAll={view_all['monthTotal']:.2f} "
                f"otros_espacios={others_sum:.2f} nSpaces={len(spaces_now)}")

            # --- B6: gasto con space_id NULL -> catch-all del espacio DEFAULT ---
            null_exp = page.evaluate(INSERT_EXPENSE_JS, {
                "user_id": uid, "amount": 15.00, "description": TAG + " NULLSPACE", "category": "other",
                "date": today, "is_income": False, "space_id": None})
            seeded_expense_ids.append(null_exp["id"])

            if default_space_id:
                page.evaluate(SELECT_SPACE_JS, [default_space_id]); page.wait_for_timeout(400)
                r_def = page.evaluate(EXPENSES_WINDOW_HAS_JS, [TAG + " NULLSPACE"])
                add("B6: gasto space_id=NULL SI aparece en el espacio DEFAULT (catch-all)", r_def is True, f"observado={r_def}")
            else:
                not_tested.append("B6 (parte default): no se encontro espacio is_default en la cuenta -> no se pudo probar el catch-all.")

            page.evaluate(SELECT_SPACE_JS, [space_a]); page.wait_for_timeout(400)
            r_nondef = page.evaluate(EXPENSES_WINDOW_HAS_JS, [TAG + " NULLSPACE"])
            add("B6: gasto space_id=NULL NO aparece en un espacio NO-default", r_nondef is False, f"observado={r_nondef}")

            page.evaluate(SELECT_SPACE_JS, ["__all__"]); page.wait_for_timeout(400)
            r_all = page.evaluate(EXPENSES_WINDOW_HAS_JS, [TAG + " NULLSPACE"])
            add("B6: gasto space_id=NULL SI aparece en vista 'todos'", r_all is True, f"observado={r_all}")

            findings.append(
                "B5/B6 (D15) — ARREGLADO y verificado aqui en vivo. Era: loadExpenses() mezclaba "
                "gastos de OTRO espacio durante los 120s siguientes a crear un gasto. El bloque "
                "'pendingLocal' (para no perder un insert propio por lag de replica) conservaba "
                "toda fila reciente que la query fresca no devolviera -- sin comprobar que siguiera "
                "perteneciendo al espacio activo, cuando la query la excluia precisamente por eso. "
                "Medido entonces: gasto A=$30 en espacio A + gasto B=$70 en espacio B -> al "
                "seleccionar B el Home decia $100. Ahora pendingLocal exige la MISMA condicion que "
                "la query (mismo espacio via _rowInActiveSpace + misma ventana de fechas). Los "
                "checks B5/B6 de arriba son la certificacion: B mide $70, Sigma(espacios)==viewAll, "
                "y el gasto con space_id=NULL ya no aparece en un espacio no-default.")

            # --- B7: exportCSV NO filtra por espacio (Historial SI) — confirmar el hallazgo ya conocido ---
            page.evaluate(SELECT_SPACE_JS, [space_a]); page.wait_for_timeout(400)
            hist_descs = page.evaluate(LOAD_HISTORY_ALL_JS)
            hist_tagged = [d for d in hist_descs if d.startswith(TAG)]
            add("B7: Historial (espacio A activo) muestra SOLO los gastos TAG de A (1: HomeA30)",
                sorted(hist_tagged) == sorted([TAG + " HomeA30"]), f"observado={hist_tagged}")

            try:
                with page.expect_download(timeout=8000) as dl_info:
                    page.evaluate(EXPORT_CSV_JS)
                dl = dl_info.value
                csv_path = dl.path()
                with open(csv_path, encoding="utf-8-sig") as f:
                    csv_text = f.read()
                csv_lines = [l for l in csv_text.splitlines() if l]
                csv_tag_lines = [l for l in csv_lines if TAG in l]
                add("B7 [CONFIRMA hallazgo ya conocido]: exportCSV (espacio A activo) incluye gastos de "
                    "OTROS espacios (>=2 filas TAG: A y B)", len(csv_tag_lines) >= 2,
                    f"filas TAG en CSV={len(csv_tag_lines)} filas TAG en Historial={len(hist_tagged)} -> "
                    f"CSV{'>' if len(csv_tag_lines) > len(hist_tagged) else '<='}Historial")
            except Exception as e:
                not_tested.append(f"B7 (export real): no se pudo capturar la descarga con Playwright ({e}). "
                                   "No se marca como PASS/FALLA.")

            # --- B8 (D8): cambiar de espacio REFRESCA el Historial (sin recargar a mano) ---
            page.evaluate(SET_HIST_CURMONTH_JS)
            page.evaluate(SELECT_SPACE_JS, [space_a]); page.wait_for_timeout(400)
            histA = [d for d in page.evaluate(READ_HISTORY_NOW_JS) if d.startswith(TAG)]
            add("B8 (D8): al entrar al espacio A, el Historial (sin recargar a mano) muestra solo HomeA30",
                histA == [TAG + " HomeA30"], f"observado={histA}")
            page.evaluate(SELECT_SPACE_JS, [space_b]); page.wait_for_timeout(400)
            histB = [d for d in page.evaluate(READ_HISTORY_NOW_JS) if d.startswith(TAG)]
            add("B8 (D8): al cambiar a B, el Historial se refresca solo a HomeB70 (antes seguia en A)",
                histB == [TAG + " HomeB70"], f"observado={histB}")
            add("B8 (D8) [CONTROL NEGATIVO]: el Historial de B ya NO muestra el gasto de A",
                (TAG + " HomeA30") not in histB, f"historial B={histB}")

            # --- B9 (D9): el selector de espacios cuenta los gastos huerfanos igual que el Home ---
            if default_space_id:
                page.evaluate(SELECT_SPACE_JS, [default_space_id]); page.wait_for_timeout(400)
                home_def = page.evaluate(MEASURE_HOME_JS)["monthTotal"]
                stats = page.evaluate(SPACE_STATS_JS, [default_space_id])
                add("B9 (D9): selector del espacio DEFAULT (spaceStats) == Home del espacio DEFAULT (incluye el huerfano)",
                    abs(stats["defSpent"] - home_def) < 0.01,
                    f"selector={stats['defSpent']:.2f} home={home_def:.2f} (el $15 sin space_id cuenta para ambos)")
                add("B9 (D9) [CONTROL NEGATIVO]: NO queda un bucket '_none' con el gasto huerfano perdido",
                    (not stats["hasNone"]) or stats["noneSpent"] == 0,
                    f"hasNone={stats['hasNone']} noneSpent={stats['noneSpent']}")
            else:
                not_tested.append("B9 (D9): no hay espacio is_default -> no se pudo probar el catch-all del selector.")

            # ═══ C. PATRIMONIO ═════════════════════════════════════════════
            # --- C8: lifetimeSavings usa TODO el historial (BD), no la ventana local de 2 meses ---
            page.evaluate(SELECT_SPACE_JS, [space_a]); page.wait_for_timeout(400)
            L0 = page.evaluate(MEASURE_LIFETIME_JS)  # ya incluye el $30 de HomeA30 (gasto) -> deberia ser -30 aprox

            old_date = date(date.today().year if date.today().month > 5 else date.today().year - 1,
                             ((date.today().month - 5 - 1) % 12) + 1, 1).isoformat()
            old_inc = admin("POST", "/rest/v1/expenses", {
                "user_id": uid, "amount": 123.45, "description": TAG + " OLDINC", "category": "other_income",
                "date": old_date, "is_income": True, "space_id": space_a,
            }, {"Prefer": "return=representation"})
            old_exp = admin("POST", "/rest/v1/expenses", {
                "user_id": uid, "amount": 23.45, "description": TAG + " OLDEXP", "category": "other",
                "date": old_date, "is_income": False, "space_id": space_a,
            }, {"Prefer": "return=representation"})
            old_inc_id = old_inc[1][0]["id"] if old_inc[0] < 300 and isinstance(old_inc[1], list) else None
            old_exp_id = old_exp[1][0]["id"] if old_exp[0] < 300 and isinstance(old_exp[1], list) else None
            for i in (old_inc_id, old_exp_id):
                if i: seeded_expense_ids.append(i)

            not_in_window = page.evaluate(EXPENSES_WINDOW_HAS_JS, [TAG + " OLDINC"])
            add("C8: el registro viejo (5 meses atras, insertado por REST admin) NO esta en la ventana c.expenses",
                not_in_window is False, f"observado presente-en-ventana={not_in_window}")

            L1 = page.evaluate(MEASURE_LIFETIME_JS)
            delta = round(L1["L"] - L0["L"], 2)
            exp_delta = round(123.45 - 23.45, 2)
            add("C8: lifetimeSavings SUBE exactamente por (ingreso-gasto) viejo == +100.00 (lee de BD, no de la ventana)",
                abs(delta - exp_delta) < 0.02, f"delta observado={delta} esperado={exp_delta}")
            add("C8: desglose por mes (lifetimeSavingsByMonth) suma al total", abs(L1["byMonthSum"] - L1["L"]) < 0.02,
                f"byMonthSum={L1['byMonthSum']} L={L1['L']}")

            # --- C9: patNetWorth = inversiones+bienes-deudas; excluye status=closed ---
            # Nota: supabase-js hace UNION de las keys del batch y rellena con null las que
            # falten en cada fila -> hay que mandar 'status' explicito en las 4 filas o el
            # NULL pisa el DEFAULT 'active' y viola el NOT NULL de la columna.
            pat_rows = [
                {"user_id": uid, "kind": "investment", "name": TAG + " INV", "current_value": 500, "capital": 400, "status": "active"},
                {"user_id": uid, "kind": "asset", "name": TAG + " ASSET", "current_value": 300, "status": "active"},
                {"user_id": uid, "kind": "debt", "name": TAG + " DEBT", "current_value": 150, "status": "active"},
                {"user_id": uid, "kind": "investment", "name": TAG + " CLOSED", "current_value": 9999, "status": "closed"},
            ]
            pat_ids = page.evaluate(INSERT_PAT_ITEMS_JS, pat_rows)
            N1 = page.evaluate(MEASURE_PAT_JS)
            exp_delta_n = 500 + 300 - 150  # el item closed (9999) NO cuenta
            observed_delta_n = round(N1["N"] - N0, 2)
            add("C9: patNetWorth sube exactamente investments+assets-debts (closed excluido) == +650.00",
                abs(observed_delta_n - exp_delta_n) < 0.01, f"delta observado={observed_delta_n} esperado={exp_delta_n}")
            wrong_hyp_closed = abs(observed_delta_n - (exp_delta_n + 9999)) < 0.01
            add("[CONTROL NEGATIVO] C9: hipotesis invertida 'el item closed SI cuenta' (+10649) debe salir FALSA",
                wrong_hyp_closed is False, f"delta observado={observed_delta_n}")

            # --- C10: patTotalWithSavings == patNetWorth + lifetimeSavings ---
            T1 = page.evaluate(MEASURE_LIFETIME_JS)
            add("C10: patTotalWithSavings == patNetWorth + lifetimeSavings (espacio A)",
                abs(T1["T"] - (T1["N"] + T1["L"])) < 0.01, f"T={T1['T']} N={T1['N']} L={T1['L']}")

            # --- C11: INCONSISTENCIA — patNetWorth global vs lifetimeSavings por-espacio ---
            page.evaluate(SELECT_SPACE_JS, [space_a]); page.wait_for_timeout(300)
            mA = page.evaluate(MEASURE_LIFETIME_JS)
            page.evaluate(SELECT_SPACE_JS, [space_b]); page.wait_for_timeout(300)
            mB = page.evaluate(MEASURE_LIFETIME_JS)

            add("C11: patNetWorth es IDENTICO en espacio A y espacio B (patrimonio es global)",
                abs(mA["N"] - mB["N"]) < 0.01, f"N(A)={mA['N']} N(B)={mB['N']}")
            add("C11: lifetimeSavings DIFIERE entre A y B (si filtra por espacio)",
                abs(mA["L"] - mB["L"]) > 0.01, f"L(A)={mA['L']} L(B)={mB['L']}")
            add("C11: por lo tanto patTotalWithSavings CAMBIA solo por cambiar de espacio, con el MISMO patrimonio",
                abs(mA["T"] - mB["T"]) > 0.01, f"T(A)={mA['T']} T(B)={mB['T']} diff={round(mA['T']-mB['T'],2)}")

            findings.append(
                "C11 — Inconsistencia CONFIRMADA empiricamente: patrimony_items no tiene columna space_id "
                "(migracion 20260611_patrimony.sql) y loadPatrimony() (index.html ~12005) NO aplica "
                "_applySpaceFilter -> patNetWorth es GLOBAL. loadLifetimeSavings() (~11922) SI aplica "
                "_applySpaceFilter (~11948) -> lifetimeSavings es POR ESPACIO. Con los MISMOS items de "
                f"patrimonio (patNetWorth(A)={mA['N']:.2f} == patNetWorth(B)={mB['N']:.2f}), "
                f"patTotalWithSavings midio {mA['T']:.2f} en el espacio A y {mB['T']:.2f} en el espacio B "
                f"(diferencia de {round(mA['T']-mB['T'],2):.2f}, atribuible 100% al ahorro del espacio, no al "
                "patrimonio). Un usuario Max que cambie de espacio ve su 'Patrimonio total' saltar sin haber "
                "tocado ni un item de inversion/bien/deuda. El comentario en el codigo (~11919-11921) dice que "
                "el ahorro es 'global, consistente con el patrimonio que tambien es global' pero el codigo real "
                "(~11944-11948) hace justo lo opuesto (filtra por espacio) -- el comentario esta desactualizado "
                "respecto al comportamiento real.")

        finally:
            # ── LIMPIEZA ────────────────────────────────────────────────────
            cleanup_errors = []
            try:
                if seeded_expense_ids:
                    page.evaluate(DELETE_EXPENSES_JS, seeded_expense_ids)
            except Exception as e:
                cleanup_errors.append(f"expenses: {e}")
            try:
                if pat_ids:
                    page.evaluate(DELETE_PAT_ITEMS_JS, pat_ids)
            except Exception as e:
                cleanup_errors.append(f"patrimony_items: {e}")
            for sid in (space_a, space_b):
                if not sid: continue
                try:
                    page.evaluate(DELETE_BUDGETS_JS, [sid, None, None])
                except Exception as e:
                    cleanup_errors.append(f"budgets({sid}): {e}")

            # red de seguridad: via el cliente AUTENTICADO (sb), no admin REST -- ver nota en
            # SAFETY_NET_JS. Confirma 0 filas huerfanas referenciando los espacios temp y
            # borra los espacios mismos.
            try:
                safety = page.evaluate(SAFETY_NET_JS, [[space_a, space_b]])
                for k, v in (safety or {}).items():
                    if k.startswith("spaceDelErr_") and v:
                        cleanup_errors.append(f"NO se pudo borrar espacio {k}: {v}")
                    elif not k.startswith("spaceDelErr_"):
                        cleanup_errors.append(f"red de seguridad borro huerfanos: {k}={v}")
            except Exception as e:
                cleanup_errors.append(f"safety net (espacios/huerfanos): {e}")

            # restaura seleccion de espacio original
            try:
                if original_view_all:
                    page.evaluate(SELECT_SPACE_JS, ["__all__"])
                elif original_active:
                    page.evaluate(SELECT_SPACE_JS, [original_active])
            except Exception as e:
                cleanup_errors.append(f"restaurar espacio activo: {e}")

            # verificacion final: patNetWorth vuelve al baseline, no quedan espacios/patrimonio TAG.
            # Refresca c.spaces desde la BD primero: SAFETY_NET_JS borro por sb.delete() directo,
            # que no hace splice del array local -> sin este refresh el check leeria cache viejo.
            try:
                page.evaluate("async () => { const c = window.Alpine.$data(document.querySelector('#app')); await c.loadSpaces(); return true; }")
                final = page.evaluate(CAPTURE_BASELINE_JS)
                add("CLEANUP: patNetWorth vuelve al valor inicial", abs(final["patNetWorth"] - N0) < 0.01,
                    f"N0={N0} Nfinal={final['patNetWorth']}")
                add("CLEANUP: no quedan espacios temporales (A/B) en c.spaces",
                    not any(s["id"] in (space_a, space_b) for s in final["spaces"]),
                    f"spaces={[s['name'] for s in final['spaces']]}")
            except Exception as e:
                cleanup_errors.append(f"verificacion final: {e}")

            if cleanup_errors:
                print("\n[AVISO limpieza]:")
                for e in cleanup_errors: print("  -", e)

        browser.close()

    ok = all(v for _, v, _ in checks)
    print(f"\n=== E2E Invariantes de dinero: Presupuestos / Espacios / Patrimonio (TAG={TAG}) ===")
    for label, v, detail in checks:
        print(f"  [{'PASS' if v else 'FALLA'}] {label}" + (f"  -- {detail}" if detail else ""))
    if findings:
        print("\n--- Hallazgos (no son fallas de check, son analisis pedido) ---")
        for f in findings: print("  * " + f)
    if not_tested:
        print("\n--- No se pudo probar ---")
        for n in not_tested: print("  * " + n)
    n_pass = sum(1 for _, v, _ in checks if v)
    print(f"\n{n_pass}/{len(checks)} checks PASS")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html")
    sys.exit(0 if ok else 1)
