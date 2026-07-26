#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA E2E REAL: invariantes de dinero entre Home / Historial / Dashboard de Zepo.

Cuenta: elite@zepo.test (unica asignada a esta campana). Siembra un escenario
controlado en el espacio por defecto, mide ANTES (m0) y DESPUES (m1) de
sembrar via getters reales de Alpine, calcula el DELTA (m1-m0) y lo compara
contra la aritmetica que este script calcula por su cuenta a partir de las
filas realmente guardadas en Supabase (REST, service_role) -- nunca copia la
formula de index.html. Limpia por TAG y mide RESTAURADO (m2).

Escenario:
  - 3 gastos mes actual: $10.00 (hoy), $33.33 (hoy-7, frontera de "semana"),
    $0.01 (hoy)
  - 2 ingresos mes actual: $100.00 y $0.50 (hoy)
  - 2 gastos ultimos 3 dias del mes anterior: $20 y $5
  - 1 gasto de hace ~5 meses: $77 (fuera de la ventana de loadExpenses)
  - 1 gasto dividido: total $90, mi 20% (amount=18, split_pending=72,
    split_persona='INV_x_Ana')

Sale 1 si algun invariante TESTABLE falla.
"""
import sys, time, socket, threading, http.server, functools, os, json, calendar
import urllib.request, urllib.error
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
EMAIL, PASSWORD = "elite@zepo.test", "ZepoQA2026!"
TAG = "INV_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}
TOL = 0.015  # tolerancia float (invariante #11 de redondeo la reporta aparte)


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


def ensure_user(email, password):
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    uid = None
    if isinstance(users, dict):
        for u in users.get("users", []):
            if u.get("email") == email: uid = u["id"]; break
    if uid:
        admin("PUT", f"/auth/v1/admin/users/{uid}", {"password": password, "email_confirm": True})
    else:
        st, res = admin("POST", "/auth/v1/admin/users", {"email": email, "password": password, "email_confirm": True})
        uid = res.get("id") if isinstance(res, dict) else None
    return uid


def count_expenses(user_id):
    st, rows = admin("GET", f"/rest/v1/expenses?user_id=eq.{user_id}&select=id")
    return len(rows) if isinstance(rows, list) else -1


def seed_rows(user_id, space_id, rows):
    inserted = []
    for r in rows:
        payload = dict(r)
        payload["user_id"] = user_id
        if space_id: payload["space_id"] = space_id
        st, res = admin("POST", "/rest/v1/expenses", payload, {"Prefer": "return=representation"})
        if isinstance(res, list) and res:
            inserted.append(res[0])
        else:
            print(f"  [WARN] insert fallo para {r.get('description')}: {st} {str(res)[:200]}")
    return inserted


def cleanup(user_id):
    admin("DELETE", f"/rest/v1/expenses?user_id=eq.{user_id}&description=like.{TAG}*")


def count_tagged(user_id):
    st, rows = admin("GET", f"/rest/v1/expenses?user_id=eq.{user_id}&description=like.{TAG}*&select=id")
    return len(rows) if isinstance(rows, list) else -1


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
  try { localStorage.setItem('zepo_a7_done_v1','1'); } catch {}
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.showWelcomeCarousel = false; c.a7Active = false; c.coachTip = () => {};
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

CLEAR_LOCAL_JS = """
(tag) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  // loadExpenses() preserva por diseno inserciones locales <120s aunque el fetch fresco
  // de BD ya no las traiga (evita parpadeo por lag de replica). Eso interfiere con medir
  // "restaurado" justo despues de borrar via REST -- se purgan a mano antes de remedir.
  c.expenses = (c.expenses || []).filter(e => !(e.description || '').startsWith(tag));
  c.historyData = (c.historyData || []).filter(e => !(e.description || '').startsWith(tag));
  return true;
}
"""

GET_SPACE_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.loadSpaces();
  const def = (c.spaces||[]).find(s=>s.is_default) || c.spaces[0] || null;
  if (def) { c.spaceViewAll = false; c.activeSpaceId = def.id; }
  return def ? def.id : null;
}
"""

# Batch grande: mide TODOS los getters relevantes de una sola pasada (asi evita
# releer getters memoizados con dataVer viejo -- ver ZEPO-GROUND-TRUTH.md).
MEASURE_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const r2 = x => Math.round(x*100)/100;
  await c.loadExpenses();
  // yearlyChart lee this.historyData (no solo this.expenses) -- hay que refrescarlo
  // ANTES del bloque dash o yearlyChart queda con datos viejos/vacios de una pasada anterior.
  c.histAll = true; c.histType = 'all'; c.filterCat = 'all';
  await c.loadHistory();

  c.tab = 'dash';
  await c.ensureDashYear(true);   // el titular y el mapa del año leen dashYearData (D4)
  const dash = {};
  for (const mode of ['expense','income','balance']) {
    c.dashViewMode = mode;
    for (const period of ['semana','mes','año']) {
      c.dashPeriod = period;
      const key = mode + '_' + period;
      const bd = c.categoryBreakdown || [];
      dash[key] = {
        dashPeriodData: c.dashPeriodData,
        breakdown: bd.map(x => ({ key: x.key, total: x.total })),
        breakdownSum: r2(bd.reduce((s,x)=>s+x.total,0)),
      };
      if (period === 'semana') dash[key].weeklyChartSum = r2((c.weeklyChart||[]).reduce((s,x)=>s+x.total,0));
      if (period === 'mes') {
        dash[key].monthlyChartSum = r2((c.monthlyChart||[]).reduce((s,x)=>s+x.total,0));
        dash[key].monthlyDayGridTotal = c.monthlyDayGrid.total;
      }
      if (period === 'año') dash[key].yearlyChartSum = r2(c.yearlyChart.grid.flat().reduce((s,cell)=>s+(cell.total||0),0));
    }
  }
  c.dashViewMode = 'income'; c.dashPeriod = 'semana'; c.catDrillKey = 'salary'; c.catDrillOpen = true;
  const catDrill = { total: c.catDrillTotal, pct: c.catDrillPct };
  c.catDrillOpen = false; c.catDrillKey = null;

  c.tab = 'home';
  // deadGone: los getters muertos de semana/resumen se ELIMINARON (barrido 18-jul). Si alguien
  // los reintroduce sin alinearlos a periodStart (7 dias cerrados en hoy), INV5d lo detecta.
  const DEAD = ['weekTotal','weekExpenseCount','topCategory','topCategoryAmount','topCategoryEmoji','topCategoryPct'];
  const home = { monthTotal: c.monthTotal, monthIncome: c.monthIncome, monthBalance: c.monthBalance,
                 deadGone: DEAD.every(k => typeof c[k] === 'undefined'), liveType: typeof c.monthTotal };

  c.tab = 'history';
  const hist = {};
  const now = new Date();
  c.histAll = false; c.histMonth = now.getMonth(); c.histYear = now.getFullYear();
  c.histType = 'all'; c.filterCat = 'all';
  await c.loadHistory();
  hist.currentMonth_all = { historyTotal: c.historyTotal, groupsSum: r2((c.filteredHistoryGroups||[]).reduce((s,g)=>s+g.total,0)) };
  c.histAll = true;
  for (const ht of ['all','expense','income']) {
    c.histType = ht;
    await c.loadHistory();
    hist['allTime_' + ht] = { historyTotal: c.historyTotal, groupsSum: r2((c.filteredHistoryGroups||[]).reduce((s,g)=>s+g.total,0)) };
  }

  return { dash, catDrill, home, hist };
}
"""


def login(page, url):
    page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
    err = page.evaluate(LOGIN_JS, [EMAIL, PASSWORD])
    if err: raise RuntimeError("login: " + err)
    page.wait_for_function(
        "()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}",
        timeout=20000)
    page.wait_for_timeout(1500)


def bd_dict(m, key):
    return {b["key"]: b["total"] for b in m["dash"][key]["breakdown"]}


def d2(a, b):
    return round(a - b, 2)


def main():
    today = date.today()
    T = today.isoformat()
    T7 = (today - timedelta(days=7)).isoformat()
    T6 = (today - timedelta(days=6)).isoformat()
    if today.month == 1:
        pm_y, pm_m = today.year - 1, 12
    else:
        pm_y, pm_m = today.year, today.month - 1
    pm_last = calendar.monthrange(pm_y, pm_m)[1]
    PM_LAST = date(pm_y, pm_m, pm_last).isoformat()
    PM_LAST2 = date(pm_y, pm_m, pm_last - 2).isoformat()
    om_m, om_y = today.month - 5, today.year
    while om_m <= 0:
        om_m += 12; om_y -= 1
    OLD5 = date(om_y, om_m, 10).isoformat()

    SEED = [
        dict(description=TAG + " gasto10", amount=10.00, category="food", date=T, is_income=False),
        # Las 2 filas frontera de la "semana" (7 dias contando hoy = hoy-6..hoy):
        #   t7 (hoy-7) queda FUERA -> ni el titular ni las barras la cuentan.
        #   t6 (hoy-6) queda DENTRO -> titular y barras la cuentan, las dos.
        # Con la ventana vieja de 8 dias, t7 contaba arriba y en ninguna barra (bug D6).
        dict(description=TAG + " gasto3333_t7", amount=33.33, category="food", date=T7, is_income=False),
        dict(description=TAG + " gasto1234_t6", amount=12.34, category="food", date=T6, is_income=False),
        dict(description=TAG + " gasto001", amount=0.01, category="other", date=T, is_income=False),
        dict(description=TAG + " ingreso100", amount=100.00, category="salary", date=T, is_income=True),
        dict(description=TAG + " ingreso050", amount=0.50, category="salary", date=T, is_income=True),
        dict(description=TAG + " prevmonth20", amount=20.00, category="transport", date=PM_LAST2, is_income=False),
        dict(description=TAG + " prevmonth5", amount=5.00, category="transport", date=PM_LAST, is_income=False),
        dict(description=TAG + " old5m77", amount=77.00, category="travel", date=OLD5, is_income=False),
        dict(description=TAG + " split18", amount=18.00, category="rent", date=T, is_income=False,
             is_split=True, split_total=90, split_pct=20, split_pending=72,
             split_persona="INV_x_Ana", split_status="pendiente"),
    ]

    print(f"=== QA invariantes Dashboard/Home/Historial -- TAG={TAG} hoy={T} dia-mes={today.day} ===")
    uid = ensure_user(EMAIL, PASSWORD)
    if not uid:
        print("[FALLA] no se pudo asegurar elite@zepo.test"); return 1
    n0 = count_expenses(uid)
    print(f"  cuenta elite id={uid}  filas expenses ANTES={n0}")

    inserted = []
    m0 = m1 = m2 = None
    try:
        port = free_port(); serve(port); time.sleep(0.5)
        base_url = f"http://127.0.0.1:{port}/index.html"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
            page.on("dialog", lambda d: d.accept())
            login(page, base_url)
            space_id = page.evaluate(GET_SPACE_JS)
            print(f"  espacio por defecto = {space_id}")

            m0 = page.evaluate(MEASURE_JS)

            inserted = seed_rows(uid, space_id, SEED)
            if len(inserted) != len(SEED):
                print(f"[FALLA] solo se insertaron {len(inserted)}/{len(SEED)} filas -- abortando comparaciones")
            page.wait_for_timeout(400)

            m1 = page.evaluate(MEASURE_JS)

            cleanup(uid)
            page.evaluate(CLEAR_LOCAL_JS, TAG)
            page.wait_for_timeout(400)
            m2 = page.evaluate(MEASURE_JS)
            browser.close()
    finally:
        cleanup(uid)

    n2 = count_expenses(uid)
    n_tagged_left = count_tagged(uid)

    if len(inserted) != len(SEED) or m0 is None or m1 is None:
        print("[FALLA] siembra incompleta, no se puede seguir"); return 1

    # ---------- aritmetica esperada (mia, desde las filas REALES en BD) ----------
    rows = [{"amount": float(r["amount"]), "date": r["date"], "is_income": bool(r["is_income"]),
             "category": r["category"]} for r in inserted]
    cm_start = date(today.year, today.month, 1).isoformat()
    # UNA sola definicion de semana: 7 dias contando hoy. periodStart('semana') y el
    # winStart de weeklyChart deben coincidir; antes eran hoy-7 y hoy-6 (8 vs 7 dias).
    week_start = (today - timedelta(days=6)).isoformat()
    year_start = date(today.year, 1, 1).isoformat()
    win_start = date(pm_y, pm_m, 1).isoformat()
    nw_y, nw_m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    win_end = date(nw_y, nw_m, calendar.monthrange(nw_y, nw_m)[1]).isoformat()

    def in_window(dd): return win_start <= dd <= win_end

    exp_rows = [r for r in rows if not r["is_income"]]
    inc_rows = [r for r in rows if r["is_income"]]

    exp_month = round(sum(r["amount"] for r in exp_rows if r["date"] >= cm_start), 2)
    inc_month = round(sum(r["amount"] for r in inc_rows if r["date"] >= cm_start), 2)
    bal_month = round(inc_month - exp_month, 2)

    # La semana se cierra en HOY (las barras no pasan de hoy).
    exp_semana = round(sum(r["amount"] for r in exp_rows if week_start <= r["date"] <= T and in_window(r["date"])), 2)
    inc_semana = round(sum(r["amount"] for r in inc_rows if week_start <= r["date"] <= T and in_window(r["date"])), 2)
    bal_semana = round(inc_semana - exp_semana, 2)
    # Derivado por separado a proposito: si titular y barras volvieran a usar ventanas
    # distintas, INV5a/INV5b lo cazan cada uno contra la BD, no solo uno contra el otro.
    exp_weekchart = round(sum(r["amount"] for r in exp_rows if week_start <= r["date"] <= T and in_window(r["date"])), 2)

    exp_year_dash = round(sum(r["amount"] for r in exp_rows if r["date"] >= year_start and in_window(r["date"])), 2)
    exp_year_chart = round(sum(r["amount"] for r in exp_rows if r["date"] >= year_start), 2)

    rent_month = round(sum(r["amount"] for r in exp_rows if r["date"] >= cm_start and r["category"] == "rent"), 2)

    alltime_exp = round(sum(r["amount"] for r in exp_rows), 2)
    alltime_inc = round(sum(r["amount"] for r in inc_rows), 2)
    alltime_net = round(alltime_inc - alltime_exp, 2)

    # ---------- deltas observados (m1 - m0) ----------
    d_monthTotal = d2(m1["home"]["monthTotal"], m0["home"]["monthTotal"])
    d_monthIncome = d2(m1["home"]["monthIncome"], m0["home"]["monthIncome"])
    d_monthBalance = d2(m1["home"]["monthBalance"], m0["home"]["monthBalance"])

    d_histCurMonth = d2(m1["hist"]["currentMonth_all"]["historyTotal"], m0["hist"]["currentMonth_all"]["historyTotal"])

    d_dashPeriodData_mes_exp = d2(m1["dash"]["expense_mes"]["dashPeriodData"], m0["dash"]["expense_mes"]["dashPeriodData"])
    d_monthlyChartSum = d2(m1["dash"]["expense_mes"]["monthlyChartSum"], m0["dash"]["expense_mes"]["monthlyChartSum"])
    d_monthlyDayGridTotal = d2(m1["dash"]["expense_mes"]["monthlyDayGridTotal"], m0["dash"]["expense_mes"]["monthlyDayGridTotal"])

    d_dashPeriodData_semana_exp = d2(m1["dash"]["expense_semana"]["dashPeriodData"], m0["dash"]["expense_semana"]["dashPeriodData"])
    d_weeklyChartSum = d2(m1["dash"]["expense_semana"]["weeklyChartSum"], m0["dash"]["expense_semana"]["weeklyChartSum"])

    d_dashPeriodData_year_exp = d2(m1["dash"]["expense_año"]["dashPeriodData"], m0["dash"]["expense_año"]["dashPeriodData"])
    d_yearlyChartSum = d2(m1["dash"]["expense_año"]["yearlyChartSum"], m0["dash"]["expense_año"]["yearlyChartSum"])

    bd0_mes_exp = bd_dict(m0, "expense_mes"); bd1_mes_exp = bd_dict(m1, "expense_mes")
    d_rent_mes = d2(bd1_mes_exp.get("rent", 0), bd0_mes_exp.get("rent", 0))

    d_dashPeriodData_mes_bal = d2(m1["dash"]["balance_mes"]["dashPeriodData"], m0["dash"]["balance_mes"]["dashPeriodData"])

    # Modo balance en las GRAFICAS (D5): antes sumaban ingreso+gasto en positivo mientras
    # el titular restaba. Ahora tienen que netear igual que el titular.
    d_monthlyChartSum_bal = d2(m1["dash"]["balance_mes"]["monthlyChartSum"], m0["dash"]["balance_mes"]["monthlyChartSum"])
    d_monthlyDayGridTotal_bal = d2(m1["dash"]["balance_mes"]["monthlyDayGridTotal"], m0["dash"]["balance_mes"]["monthlyDayGridTotal"])
    d_dashPeriodData_semana_bal = d2(m1["dash"]["balance_semana"]["dashPeriodData"], m0["dash"]["balance_semana"]["dashPeriodData"])
    d_weeklyChartSum_bal = d2(m1["dash"]["balance_semana"]["weeklyChartSum"], m0["dash"]["balance_semana"]["weeklyChartSum"])

    # ---------- checks ----------
    checks = []  # (label, passed_bool, detail_str)
    known = []   # divergencias YA reportadas a Alvaro y NO aprobadas para arreglo:
                 # se miden y se reportan, pero no tumban el gate.

    def chk(label, observed, expected, tol=TOL, detail=""):
        ok = abs(observed - expected) <= tol
        checks.append((label, ok, f"esperado={expected}  observado={observed}  {detail}"))
        return ok

    print("\n--- INV1: monthBalance = monthIncome - monthTotal (Home) ---")
    chk("INV1a monthTotal(delta) == suma BD gastos del mes", d_monthTotal, exp_month)
    chk("INV1b monthIncome(delta) == suma BD ingresos del mes", d_monthIncome, inc_month)
    chk("INV1c monthBalance(delta) == monthIncome-monthTotal(delta)", d_monthBalance, d2(d_monthIncome, d_monthTotal))
    chk("INV1d monthBalance(delta) == BD (ingreso-gasto) del mes", d_monthBalance, bal_month)

    print("--- INV2: Home vs Historial (mes actual, histType=all) ---")
    chk("INV2 monthBalance(delta) == historyTotal mes-actual(delta)", d_histCurMonth, d_monthBalance)

    print("--- INV3: historyTotal == suma filteredHistoryGroups (histAll=true) ---")
    for ht in ("all", "expense", "income"):
        e = m1["hist"]["allTime_" + ht]
        checks.append((f"INV3 {ht}: historyTotal == suma(filteredHistoryGroups)",
                        abs(e["historyTotal"] - e["groupsSum"]) <= TOL,
                        f"historyTotal={e['historyTotal']}  groupsSum={e['groupsSum']}"))
    e0 = m1["hist"]["currentMonth_all"]
    checks.append(("INV3 mes-actual(all): historyTotal == suma(filteredHistoryGroups)",
                    abs(e0["historyTotal"] - e0["groupsSum"]) <= TOL,
                    f"historyTotal={e0['historyTotal']}  groupsSum={e0['groupsSum']}"))

    print("--- INV4: Dashboard mes/gastos ---")
    chk("INV4a dashPeriodData(mes,gasto)(delta) == BD gastos del mes", d_dashPeriodData_mes_exp, exp_month)
    chk("INV4b suma(monthlyChart)(delta) == BD gastos del mes", d_monthlyChartSum, exp_month)
    chk("INV4c monthlyDayGrid.total(delta) == BD gastos del mes", d_monthlyDayGridTotal, exp_month)
    chk("INV4d dashPeriodData(mes,gasto)(delta) == monthTotal(delta) Home", d_dashPeriodData_mes_exp, d_monthTotal)

    print("--- INV5: Dashboard semana ---")
    chk("INV5a dashPeriodData(semana,gasto)(delta) == BD gastos en hoy-6..hoy (NO cuenta la fila de hoy-7)", d_dashPeriodData_semana_exp, exp_semana)
    chk("INV5b suma(weeklyChart)(delta) == BD gastos en hoy-6..hoy", d_weeklyChartSum, exp_weekchart)
    checks.append(("INV5c dashPeriodData(semana) == suma(weeklyChart)  [D6: una sola definicion de semana]",
                    abs(d_dashPeriodData_semana_exp - d_weeklyChartSum) <= TOL,
                    f"dashPeriodData(delta)={d_dashPeriodData_semana_exp}  weeklyChart(delta)={d_weeklyChartSum}  "
                    f"diff={d2(d_dashPeriodData_semana_exp, d_weeklyChartSum)} (con el bug de 8 vs 7 dias daba 33.33)"))
    checks.append(("INV5e la fila del dia frontera hoy-6 ($12.34) SI cuenta en la semana (titular y barras)",
                    abs(d_dashPeriodData_semana_exp - exp_semana) <= TOL and exp_semana >= 12.34,
                    f"exp_semana(BD)={exp_semana} incluye la fila de hoy-6=12.34; observado={d_dashPeriodData_semana_exp}"))
    # Barrido 18-jul: weekTotal/weekExpenseCount/topCategory* eran getters MUERTOS (0 referencias
    # en templates) con la definicion vieja de semana (now-7 = 8 dias) sobre monthExpenses (pierde
    # los dias del mes anterior). Se ELIMINARON; este check vigila que no vuelvan.
    checks.append(("INV5d [barrido] getters muertos de semana (weekTotal/weekExpenseCount/topCategory*) eliminados del codigo",
                    m1["home"].get("deadGone") is True,
                    f"deadGone={m1['home'].get('deadGone')} (los 6 deben dar typeof undefined)"))
    checks.append(("[CONTROL NEGATIVO] INV5d la sonda distingue muerto de vivo: monthTotal SI existe (typeof number)",
                    m1["home"].get("liveType") == "number",
                    f"typeof monthTotal={m1['home'].get('liveType')}"))

    print("--- INV6: Dashboard año (D4: titular y mapa leen dashYearData = año completo) ---")
    chk("INV6a dashPeriodData(año,gasto)(delta) == BD TODOS los gastos del año (incl. el de hace 5 meses)", d_dashPeriodData_year_exp, exp_year_chart)
    chk("INV6b suma(yearlyChart)(delta) == BD TODOS los gastos del año", d_yearlyChartSum, exp_year_chart)
    checks.append(("INV6c [D4] dashPeriodData(año) == suma(yearlyChart)  (titular y mapa ya NO discrepan)",
                    abs(d_dashPeriodData_year_exp - d_yearlyChartSum) <= TOL,
                    f"dashPeriodData(delta)={d_dashPeriodData_year_exp}  yearlyChart(delta)={d_yearlyChartSum}  "
                    f"diff={d2(d_dashPeriodData_year_exp, d_yearlyChartSum)} (con el bug el titular no veia los 77.00 de hace 5 meses)"))
    checks.append(("INV6d [D4] el titular del año SI incluye el gasto de hace 5 meses ($77)",
                    d_dashPeriodData_year_exp >= 77.0 - TOL,
                    f"dashPeriodData(año) delta={d_dashPeriodData_year_exp} (debe incluir el 77.00 fuera de la ventana de 2 meses)"))
    # CONTROL NEGATIVO D4: con la ventana vieja (window-limited) el titular NO habria visto el 77.
    cn4_correctly_fails = abs(d_dashPeriodData_year_exp - exp_year_dash) > TOL
    checks.append(("CN4 [control negativo D4] dashPeriodData(año) == ventana VIEJA de 2 meses (sin el 77) -- debe DAR FALSO",
                    cn4_correctly_fails,
                    f"observado={d_dashPeriodData_year_exp}  ventana-vieja-hubiera-sido={exp_year_dash}  "
                    f"({'discrimina: el titular ya ve el año completo' if cn4_correctly_fails else 'BUG: el titular sigue con la ventana de 2 meses'})"))

    print("--- INV7: categoryBreakdown suma == dashPeriodData (mes/semana, gasto/ingreso) ---")
    for period in ("mes", "semana"):
        for mode in ("expense", "income"):
            key = f"{mode}_{period}"
            e = m1["dash"][key]
            checks.append((f"INV7 {key}: suma(categoryBreakdown) == dashPeriodData",
                            abs(e["breakdownSum"] - e["dashPeriodData"]) <= TOL,
                            f"breakdownSum={e['breakdownSum']}  dashPeriodData={e['dashPeriodData']}"))
    for period in ("mes", "semana"):
        key = f"balance_{period}"
        e = m1["dash"][key]
        checks.append((f"INV7-bonus {key}: suma(categoryBreakdown) == dashPeriodData  [D5: el desglose netea igual que el titular]",
                        abs(e["breakdownSum"] - e["dashPeriodData"]) <= TOL,
                        f"breakdownSum={e['breakdownSum']}  dashPeriodData={e['dashPeriodData']}  "
                        f"(con el bug el desglose sumaba bruto: $161.84 vs titular $39.16)"))

    print("--- INV8: catDrillPct (periodo=semana, modo=ingresos, categoria=salary) ---")
    cd = m1["catDrill"]
    period_income_semana = m1["dash"]["income_semana"]["dashPeriodData"]
    month_total_m1 = m1["home"]["monthTotal"]
    correct_pct = round(cd["total"] / period_income_semana * 100) if period_income_semana else 0
    buggy_pct_via_monthTotal = round(cd["total"] / month_total_m1 * 100) if month_total_m1 else 0
    checks.append(("INV8 catDrillPct usa el denominador correcto del periodo/modo (periodIncome semana), NO monthTotal  [D3]",
                    cd["pct"] == correct_pct,
                    f"catDrillTotal={cd['total']}  catDrillPct(observado)={cd['pct']}  "
                    f"pct-correcto(/periodIncome semana={period_income_semana})={correct_pct}  "
                    f"pct-con-monthTotal(bug, /monthTotal={month_total_m1})={buggy_pct_via_monthTotal}"))

    print("--- INV9: modo 'balance' del dashboard ---")
    chk("INV9 dashPeriodData(mes,balance)(delta) == monthBalance(delta)  [neto ingreso-gasto]", d_dashPeriodData_mes_bal, d_monthBalance)
    gross_mes = d2(exp_month, -inc_month) * -1  # exp+inc bruto
    gross_mes = round(exp_month + inc_month, 2)
    checks.append(("INV9-control dashPeriodData(mes,balance) NO es la suma bruta (gasto+ingreso)",
                    abs(d_dashPeriodData_mes_bal - gross_mes) > TOL,
                    f"observado(delta)={d_dashPeriodData_mes_bal}  bruto-hubiera-sido={gross_mes}"))

    print("--- INV12: modo balance en las GRAFICAS netea (D5) ---")
    chk("INV12a suma(monthlyChart)(balance,mes)(delta) == monthBalance(delta)", d_monthlyChartSum_bal, d_monthBalance)
    chk("INV12b monthlyDayGrid.total(balance,mes)(delta) == monthBalance(delta)", d_monthlyDayGridTotal_bal, d_monthBalance)
    chk("INV12c suma(weeklyChart)(balance,semana)(delta) == dashPeriodData(balance,semana)(delta)",
        d_weeklyChartSum_bal, d_dashPeriodData_semana_bal)
    chk("INV12d dashPeriodData(balance,semana)(delta) == BD (ingreso-gasto) de hoy-6..hoy",
        d_dashPeriodData_semana_bal, bal_semana)
    gross_bal_mes = round(exp_month + inc_month, 2)
    checks.append(("INV12-control suma(monthlyChart)(balance,mes) NO es la suma bruta (gasto+ingreso)",
                    abs(d_monthlyChartSum_bal - gross_bal_mes) > TOL,
                    f"observado(delta)={d_monthlyChartSum_bal}  bruto-hubiera-sido={gross_bal_mes}"))

    print("--- INV10: gasto dividido cuenta 18, no 90 ---")
    chk("INV10a monthTotal(delta) incluye SOLO mi parte del split (18, no 90)", d_monthTotal, exp_month)
    chk("INV10b breakdown categoria 'rent' (mes)(delta) == 18.00 (mi parte)", d_rent_mes, 18.00)
    chk("INV10c dashPeriodData(mes,gasto)(delta) incluye SOLO mi parte del split", d_dashPeriodData_mes_exp, exp_month)

    print("--- INV11: redondeo (33.33 y 0.01 sembrados) ---")
    rounding_pairs = [
        ("monthTotal", d_monthTotal, exp_month),
        ("monthIncome", d_monthIncome, inc_month),
        ("monthBalance", d_monthBalance, bal_month),
        ("historyTotal(mes)", d_histCurMonth, bal_month),
        ("dashPeriodData(mes,gasto)", d_dashPeriodData_mes_exp, exp_month),
        ("suma(monthlyChart)", d_monthlyChartSum, exp_month),
        ("monthlyDayGrid.total", d_monthlyDayGridTotal, exp_month),
        ("breakdown rent(mes)", d_rent_mes, 18.00),
    ]
    max_dev = max(abs(o - e) for _, o, e in rounding_pairs)
    worst = max(rounding_pairs, key=lambda t: abs(t[1] - t[2]))
    checks.append((f"INV11 ningun total se desvia mas de $0.01 de mi calculo (peor caso: {worst[0]})",
                    max_dev <= 0.01 + 1e-9,
                    f"desviacion maxima observada=${max_dev}  (limite $0.01)"))

    print("--- CONTROL NEGATIVO (predicado invertido debe FALLAR) ---")
    inverted1 = d2(d_monthTotal, d_monthIncome)  # gasto - ingreso, orden invertido
    cn1_correctly_fails = abs(d_monthBalance - inverted1) > TOL
    checks.append(("CN1 [control negativo] monthBalance(delta) == monthTotal(delta)-monthIncome(delta) (invertido) -- debe DAR FALSO",
                    cn1_correctly_fails,
                    f"monthBalance(delta)={d_monthBalance}  invertido(gasto-ingreso)={inverted1}  "
                    f"({'el control detecto correctamente el predicado invertido como falso' if cn1_correctly_fails else 'BUG EN EL PROPIO TEST: el control no discrimina'})"))
    cn2_correctly_fails = abs(d_rent_mes - 90.00) > TOL
    checks.append(("CN2 [control negativo] breakdown 'rent'(delta) == 90.00 (total del split, no mi parte) -- debe DAR FALSO",
                    cn2_correctly_fails,
                    f"rent(delta) observado={d_rent_mes}  90.00-invertido={90.00}  "
                    f"({'el control detecto correctamente el predicado invertido como falso' if cn2_correctly_fails else 'BUG EN EL PROPIO TEST: el control no discrimina'})"))

    buggy_semana = round(exp_semana + 33.33, 2)
    cn3_correctly_fails = abs(d_dashPeriodData_semana_exp - buggy_semana) > TOL
    checks.append(("CN3 [control negativo] dashPeriodData(semana,gasto) == ventana VIEJA de 8 dias (incluye la fila de hoy-7) -- debe DAR FALSO",
                    cn3_correctly_fails,
                    f"observado(delta)={d_dashPeriodData_semana_exp}  con-ventana-de-8-dias-hubiera-sido={buggy_semana}  "
                    f"({'el control detecto correctamente la ventana vieja como falsa' if cn3_correctly_fails else 'BUG: la semana sigue contando 8 dias'})"))

    print("--- Cleanup ---")
    restored_row = d2(m2["home"]["monthTotal"], m0["home"]["monthTotal"]) if m2 else None
    checks.append(("cleanup: monthTotal(m2) vuelve al valor inicial (m0)",
                    m2 is not None and abs(restored_row) <= TOL,
                    f"delta(m2-m0)={restored_row}"))
    checks.append(("cleanup: filas de expenses ANTES == DESPUES", n0 == n2, f"antes={n0} despues={n2}"))
    checks.append(("cleanup: 0 filas quedan con el TAG", n_tagged_left == 0, f"filas con TAG restantes={n_tagged_left}"))

    # ---------- reporte ----------
    testable = [(l, ok, det) for (l, ok, det) in checks if ok is not None]
    untestable = [(l, det) for (l, ok, det) in checks if ok is None]
    n_pass = sum(1 for _, ok, _ in testable if ok)
    n_total = len(testable)

    print(f"\n=== RESULTADO: {n_pass}/{n_total} checks TESTABLES en PASS ===")
    for label, ok, det in testable:
        print(f"  [{'PASS' if ok else 'FALLA'}] {label}\n        {det}")
    if untestable:
        print("\n=== NO TESTABLES HOY ===")
        for label, det in untestable:
            print(f"  [NO TESTABLE] {label}\n        {det}")
    if known:
        print("\n=== DIVERGENCIAS CONOCIDAS (reportadas, NO aprobadas para arreglo -> no tumban el gate) ===")
        for label, ok, det in known:
            print(f"  [{'ya no diverge' if ok else 'DIVERGE (esperado)'}] {label}\n        {det}")

    ok_all = all(ok for _, ok, _ in testable)
    print("\n" + ("OK GLOBAL (dado lo reportado arriba)" if ok_all else "HAY FALLAS -- ver detalle arriba"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
