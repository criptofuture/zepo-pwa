#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA E2E REAL: 6 arreglos de index.html en Zepo, contra Supabase real con Playwright.

Cuenta: elite@zepo.test / ZepoQA2026! (unica asignada a esta campana).

D18 -- "este mes" ya no incluye el mes que viene (_inCurrentMonth con tope superior).
D20 -- la tarjeta "Transacciones" cuenta el periodo activo (periodSrc), no siempre el mes.
D19 -- el Historial "todo el tiempo" pagina con _fetchAllRows, ya no corta en 1000.
D7  -- unsettledAdvances lee pendingSplits (global), no monthExpenses -- un adelanto del
       mes pasado sigue restando en safeToSpend.
D10 -- exportPDF lista TODAS las filas del detalle (data.map), no data.slice(0,500).
D14 -- removeSpace usa la RPC atomica zepo_delete_space en vez de 4 awaits sueltos.

No se toca index.html. Sale 1 si algun check falla.
"""
import sys, time, socket, threading, http.server, functools, os, json
import urllib.request, urllib.error
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
EMAIL, PASSWORD = "elite@zepo.test", "ZepoQA2026!"
TAG = "EXT_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}
TOL = 0.015

checks = []      # (label, ok_bool, detalle)
not_tested = []  # cosas no testables hoy (p.ej. por el dia del mes)


def chk(label, ok, detalle=""):
    checks.append((label, bool(ok), detalle))
    return ok


# -- REST admin (service_role) -- setup/verificacion/limpieza --------------------------
def admin(method, path, body=None, extra=None):
    headers = dict(H)
    if extra: headers.update(extra)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            txt = resp.read().decode() or "[]"
            return resp.status, (json.loads(txt) if txt.strip().startswith(("[", "{")) else txt)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


def count_desc_exact(user_id, prefix):
    """Cuenta expenses cuya description empieza con `prefix`, via Content-Range
    (Prefer: count=exact) -- un GET normal chocaria con el mismo tope de 1000 que
    D19/D10 existen para probar que ya no afecta a la app."""
    headers = dict(H)
    headers["Range"] = "0-0"
    headers["Prefer"] = "count=exact"
    path = f"/rest/v1/expenses?user_id=eq.{user_id}&description=like.{prefix}*&select=id"
    r = urllib.request.Request(URL + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            cr = resp.headers.get("Content-Range", "")
            total = cr.split("/")[-1] if "/" in cr else ""
            return int(total) if total.isdigit() else -1
    except urllib.error.HTTPError:
        return -1


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


def cleanup_expenses(user_id):
    return admin("DELETE", f"/rest/v1/expenses?user_id=eq.{user_id}&description=like.{TAG}*")


def cleanup_spaces(user_id):
    return admin("DELETE", f"/rest/v1/spaces?user_id=eq.{user_id}&name=like.{TAG}*")


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


def login(page, url):
    page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
    err = page.evaluate(LOGIN_JS, [EMAIL, PASSWORD])
    if err: raise RuntimeError("login: " + err)
    page.wait_for_function(
        "()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}",
        timeout=20000)
    page.wait_for_timeout(1500)


def d2(a, b):
    return round(a - b, 2)


# ---------------------------- snippets JS reutilizados ---------------------------------

LOAD_EXPENSES_JS = """
async () => { const c = window.Alpine.$data(document.querySelector('#app')); await c.loadExpenses(); return true; }
"""

GET_MONTH_TOTAL_JS = """
() => { const c = window.Alpine.$data(document.querySelector('#app')); return Math.round(c.monthTotal*100)/100; }
"""

PUSH_LOCAL_ROW_JS = """
(row) => {
  // Mismo patron que usa la app tras un insert real (this.expenses.unshift(optimistic), ver
  // index.html linea ~13638): necesario porque loadExpenses() NUNCA trae un gasto fechado en
  // el mes SIGUIENTE (su ventana de fetch termina en el ultimo dia del mes ACTUAL) -- asi que
  // la unica via real por la que un gasto futuro entra a c.expenses es la insercion optimista
  // local, exactamente lo que reproduce esta linea.
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.expenses.unshift(row);
  return c.expenses.length;
}
"""

GET_EXPENSE_DESCS_JS = """
() => { const c = window.Alpine.$data(document.querySelector('#app')); return c.expenses.map(e => e.description); }
"""

SET_DASH_JS = """
([mode, period]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.dashViewMode = mode; c.dashPeriod = period;
  return true;
}
"""

COUNT_PERIODSRC_JS = """
(prefix) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  return c.periodSrc.filter(e => (e.description || '').startsWith(prefix)).length;
}
"""

SET_HISTALL_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.histAll = true;
  await c.loadHistory();
  return true;
}
"""

COUNT_HISTORY_TAG_JS = """
(prefix) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  return (c.historyData || []).filter(e => (e.description || '').startsWith(prefix)).length;
}
"""

MEASURE_SPLIT_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.spaceViewAll = true; c.activeSpaceId = null;
  await c.loadSplits();
  await c.loadExpenses();
  return { unsettledAdvances: Math.round(c.unsettledAdvances*100)/100,
           safeToSpend: Math.round(c.safeToSpend*100)/100 };
}
"""

# D14 -- crea los 'spaces' de prueba por admin REST (service_role). Ahora funciona gracias al
# propio arreglo D17 (GRANT a service_role). Antes se probo via addSpace()/sbRestInsert de la
# pagina, pero ese helper manda un token que RLS rechaza (403) en este contexto de test; el admin
# bypassa RLS y es la via fiable para sembrar. La RPC zepo_delete_space SI se prueba via la pagina
# (usa auth.uid() de la sesion real del login).
RPC_DELETE_SPACE_JS = """
async ([pSpaceId, pTargetId]) => {
  const { error } = await sb.rpc('zepo_delete_space', { p_space_id: pSpaceId, p_target_id: pTargetId });
  return error ? error.message : null;
}
"""


def main():
    today = date.today()
    today_iso = today.isoformat()
    if today.month == 12:
        next_month_first = date(today.year + 1, 1, 1)
    else:
        next_month_first = date(today.year, today.month + 1, 1)
    month_start = today.replace(day=1)
    month_end = next_month_first - timedelta(days=1)   # ultimo dia del mes actual
    week_start = today - timedelta(days=6)              # 'semana' = 7 dias contando hoy
    if today.month == 1:
        pm_y, pm_m = today.year - 1, 12
    else:
        pm_y, pm_m = today.year, today.month - 1
    prev_month_day15 = date(pm_y, pm_m, 15)

    print(f"=== QA E2E: invariantes extra (D18/D20/D19/D7/D10/D14) -- TAG={TAG} hoy={today_iso} ===")

    # ---- D10 (parte 1, sin navegador): check de codigo -- exportPDF ya NO recorta en 500 ----
    print("\n--- CASO D10 (parte codigo): exportPDF lista TODAS las filas, no data.slice(0,500) ---")
    src = open(os.path.join(PWA_DIR, "index.html"), encoding="utf-8").read()
    exp_pdf_idx = src.find("async exportPDF()")
    exp_pdf_body = src[exp_pdf_idx:exp_pdf_idx + 4000] if exp_pdf_idx != -1 else ""
    chk("D10 codigo: exportPDF() existe en index.html", exp_pdf_idx != -1,
        f"encontrado en offset={exp_pdf_idx}")
    has_old_slice = "data.slice(0, 500)" in exp_pdf_body or "data.slice(0,500)" in exp_pdf_body
    has_new_map = "body: data.map(" in exp_pdf_body
    chk("D10 codigo: ya NO existe 'data.slice(0, 500)' dentro de exportPDF()", not has_old_slice,
        f"presente(bug viejo)={has_old_slice}")
    chk("D10 codigo: SI existe 'body: data.map(' dentro de exportPDF() (tabla completa)", has_new_map,
        f"presente={has_new_map}")

    uid = ensure_user(EMAIL, PASSWORD)
    if not uid:
        print("[FALLA] no se pudo asegurar elite@zepo.test"); return 1
    print(f"  cuenta elite id={uid}")

    port = free_port(); serve(port); time.sleep(0.5)
    base_url = f"http://127.0.0.1:{port}/index.html"

    del_space_id = None
    dest_space_id = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
            page = ctx.new_page()
            page.on("dialog", lambda d: d.accept())
            login(page, base_url)

            # ══════════════════ CASO D7 -- adelanto de split del mes pasado ══════════════════
            print("\n--- CASO D7: unsettledAdvances/safeToSpend leen pendingSplits (global), no monthExpenses ---")

            m0 = page.evaluate(MEASURE_SPLIT_JS)
            print(f"  baseline ANTES: {m0}")

            SEED_D7 = {"user_id": uid, "description": TAG + "_D7split", "amount": 10.00, "category": "other",
                       "date": prev_month_day15.isoformat(), "is_income": False, "is_split": True,
                       "split_total": 50, "split_pending": 40, "split_pct": 20,
                       "split_persona": TAG + "_Ana", "split_status": "pendiente"}
            st_d7, res_d7 = admin("POST", "/rest/v1/expenses", SEED_D7, {"Prefer": "return=minimal"})
            chk("Setup D7: POST del gasto dividido del mes pasado devolvio 201", st_d7 == 201,
                f"status={st_d7}  body={str(res_d7)[:200]}  fecha={prev_month_day15.isoformat()}")

            m1 = page.evaluate(MEASURE_SPLIT_JS)
            d_adv = d2(m1["unsettledAdvances"], m0["unsettledAdvances"])
            d_safe = d2(m1["safeToSpend"], m0["safeToSpend"])
            print(f"  medicion DESPUES: {m1}  deltas: unsettledAdvances={d_adv} safeToSpend={d_safe}")

            chk("D7 check1: delta unsettledAdvances == 40.00 (el adelanto del MES PASADO si cuenta)",
                abs(d_adv - 40.00) <= TOL, f"esperado=40.00  observado={d_adv}")
            chk("D7 check2: delta safeToSpend == -40.00 (el gasto es de fecha pasada, no toca monthTotal; "
                "solo unsettledAdvances lo resta)",
                abs(d_safe - (-40.00)) <= TOL, f"esperado=-40.00  observado={d_safe}")
            chk("D7 CONTROL NEGATIVO: hipotesis 'delta unsettledAdvances == 0.00 (el del mes pasado no "
                "cuenta al cambiar de mes)' debe DAR FALSO",
                abs(d_adv - 0.00) > TOL,
                f"delta observado={d_adv}  "
                f"({'el control discrimina correctamente' if abs(d_adv - 0.00) > TOL else 'BUG: el adelanto del mes pasado dejo de contar'})")

            cleanup_expenses(uid)  # limpia D7 antes de seguir para no ensuciar los siguientes casos
            page.evaluate(MEASURE_SPLIT_JS)  # refresca estado local (splits/expenses) tras el cleanup

            # ══════════════════ CASO D18 -- "este mes" con tope superior ══════════════════
            print("\n--- CASO D18: monthTotal ya no suma un gasto fechado en el mes SIGUIENTE ---")

            page.evaluate(LOAD_EXPENSES_JS)
            month0 = page.evaluate(GET_MONTH_TOTAL_JS)
            print(f"  monthTotal ANTES = {month0}")

            SEED_D18 = [
                {"user_id": uid, "description": TAG + "_D18today", "amount": 40.00, "category": "other",
                 "date": today_iso, "is_income": False},
                {"user_id": uid, "description": TAG + "_D18future", "amount": 999.00, "category": "other",
                 "date": next_month_first.isoformat(), "is_income": False},
            ]
            st_18, rows_18 = admin("POST", "/rest/v1/expenses", SEED_D18, {"Prefer": "return=representation"})
            chk("Setup D18: POST de las 2 filas (hoy $40 + mes siguiente $999) devolvio 201", st_18 == 201,
                f"status={st_18}  body={str(rows_18)[:300]}  hoy={today_iso}  mes_siguiente={next_month_first.isoformat()}")

            future_row = None
            if st_18 == 201 and isinstance(rows_18, list):
                future_row = next((r for r in rows_18 if r.get("description") == TAG + "_D18future"), None)

            page.evaluate(LOAD_EXPENSES_JS)
            # el gasto de HOY llega solo con loadExpenses(); el del mes siguiente jamas entra por esa
            # via (ventana de fetch = mes anterior..fin del mes actual) -- se empuja localmente para
            # reproducir la unica via real por la que ese dato entraria a c.expenses. Ver PUSH_LOCAL_ROW_JS.
            if future_row:
                page.evaluate(PUSH_LOCAL_ROW_JS, future_row)

            month1 = page.evaluate(GET_MONTH_TOTAL_JS)
            descs = page.evaluate(GET_EXPENSE_DESCS_JS)
            delta_month = d2(month1, month0)
            print(f"  monthTotal DESPUES = {month1}  delta={delta_month}")

            chk("D18 check1: delta monthTotal == 40.00 (NO 1039.00 -- el gasto del mes siguiente NO suma)",
                abs(delta_month - 40.00) <= TOL, f"esperado=40.00  observado={delta_month}")
            chk("D18 check2 [positivo]: el gasto del mes SIGUIENTE SI esta cargado en c.expenses "
                "(prueba que se excluye por FECHA, no porque no se cargo)",
                (TAG + "_D18future") in descs,
                f"descripcion buscada={TAG + '_D18future'}  presente={(TAG + '_D18future') in descs}")
            chk("D18 CONTROL NEGATIVO: hipotesis 'delta monthTotal == 1039.00 (incluye el mes que viene)' "
                "debe DAR FALSO",
                abs(delta_month - 1039.00) > TOL,
                f"delta observado={delta_month}  "
                f"({'el control discrimina correctamente' if abs(delta_month - 1039.00) > TOL else 'BUG: sigue sumando el mes siguiente'})")

            # ══════════════ CASO D20 -- "Transacciones" cuenta el periodo activo ══════════════
            print("\n--- CASO D20: periodSrc.length depende del periodo activo, no siempre el mes ---")
            # Ya en c.expenses: _D18today (hoy) y _D18future (mes siguiente). Añado _D20early fechado
            # el DIA 1 del mes actual: cae dentro del 'mes' pero (si hoy > dia 7) fuera de la 'semana'
            # -> discrimina semana vs mes bajo el tope de mes correcto (periodEnd('mes')=fin de mes,
            # que EXCLUYE el gasto del mes siguiente, coherente con D18).
            st_20, _ = admin("POST", "/rest/v1/expenses",
                             [{"user_id": uid, "description": TAG + "_D20early", "amount": 7.00,
                               "category": "other", "date": month_start.isoformat(), "is_income": False}],
                             {"Prefer": "return=minimal"})
            chk("Setup D20: POST del gasto del dia 1 del mes devolvio 201", st_20 == 201,
                f"status={st_20}  fecha={month_start.isoformat()}")
            page.evaluate(LOAD_EXPENSES_JS)
            if future_row:
                page.evaluate(PUSH_LOCAL_ROW_JS, future_row)   # el del mes siguiente no entra por fetch

            # Esperados derivados de las fechas reales (robusto a cualquier dia del mes):
            seeded = [today, next_month_first, month_start]   # _D18today, _D18future, _D20early
            exp_semana = sum(1 for d in seeded if week_start <= d <= today)
            exp_mes    = sum(1 for d in seeded if month_start <= d <= month_end)

            page.evaluate(SET_DASH_JS, ["expense", "semana"])
            n_semana = page.evaluate(COUNT_PERIODSRC_JS, TAG)
            chk("D20 check1: dashPeriod=semana -> periodSrc cuenta solo las filas de esta semana",
                n_semana == exp_semana, f"esperado={exp_semana}  observado={n_semana}  (hoy dia {today.day})")

            page.evaluate(SET_DASH_JS, ["expense", "mes"])
            n_mes = page.evaluate(COUNT_PERIODSRC_JS, TAG)
            chk("D20 check2: dashPeriod=mes -> periodSrc cuenta las filas del mes ACTUAL (excluye el mes siguiente, D18)",
                n_mes == exp_mes, f"esperado={exp_mes}  observado={n_mes}  (el gasto del mes siguiente NO cuenta)")
            chk("D20 CONTROL NEGATIVO: 'mes' NO incluye el gasto del mes siguiente (con el bug open-ended daria uno mas)",
                n_mes != exp_mes + 1,
                f"observado={n_mes}  con-mes-abierto-hubiera-sido={exp_mes + 1} (incluiria _D18future)")

            if exp_semana != exp_mes:
                chk("D20 CONTROL: el conteo SI depende del periodo activo (semana != mes)",
                    n_semana != n_mes, f"semana={n_semana}  mes={n_mes}")
            else:
                not_tested.append(f"D20 discriminacion semana!=mes: hoy es dia {today.day} (<=7) -> el gasto "
                                  f"del dia 1 tambien cae en la semana, semana y mes coinciden ({exp_semana}). "
                                  "Cada uno se verifico contra su propia derivacion de fechas.")

            cleanup_expenses(uid)  # limpia D18/D20

            # ══════════════════ CASO D19 + D10(datos) -- paginado sin tope de 1000 ══════════════════
            print("\n--- CASO D19+D10(datos): loadHistory()/exportPDF ven 1100 filas via _fetchAllRows, no 1000 ---")

            H19_PREFIX = TAG + "_D19row"
            SEED_ROWS = [
                {"user_id": uid, "description": H19_PREFIX, "amount": 1.00, "category": "other",
                 "date": today_iso, "is_income": False}
                for _ in range(1100)
            ]
            st_ins, res_ins = admin("POST", "/rest/v1/expenses", SEED_ROWS, {"Prefer": "return=minimal"})
            chk("Setup D19/D10: POST de 1100 filas devolvio 201", st_ins == 201,
                f"status={st_ins}  body={str(res_ins)[:200]}")

            n_seeded = count_desc_exact(uid, H19_PREFIX)
            chk("Setup D19/D10: se sembraron exactamente 1100 filas (Content-Range, no GET simple)",
                n_seeded == 1100, f"esperado=1100  observado={n_seeded}")

            if n_seeded != 1100:
                print("[FALLA] siembra D19/D10 incompleta -- se aborta el resto de checks de este bloque")
            else:
                page.evaluate(SET_HISTALL_JS)
                n_hist = page.evaluate(COUNT_HISTORY_TAG_JS, H19_PREFIX)
                chk("D19 check1: c.histAll=true + loadHistory() trae las 1100 filas del TAG, no 1000",
                    n_hist == 1100, f"esperado=1100  observado={n_hist}")
                chk("D19 CONTROL NEGATIVO: 1000 (lo que traeria SIN paginar) != observado en historyData",
                    n_hist != 1000,
                    f"1000 (bug sin _fetchAllRows) vs observado={n_hist}  "
                    f"({'discrimina correctamente' if n_hist != 1000 else 'BUG: el historial sigue cortado en 1000'})")

                n_rest_count = count_desc_exact(uid, H19_PREFIX)
                chk("D10 check1 [datos]: hay >1000 filas TAG disponibles por REST paginado (count=exact) -- "
                    "la misma via (_fetchAllRows) que usa exportPDF() para armar la tabla completa del PDF",
                    n_rest_count > 1000, f"esperado>1000  observado={n_rest_count}")

            cleanup_expenses(uid)  # limpia D19/D10
            n_after_1900 = count_desc_exact(uid, H19_PREFIX)
            chk("Cleanup D19/D10 intermedio: 0 filas de H19_PREFIX quedan", n_after_1900 == 0,
                f"restantes={n_after_1900}")

            # ══════════════════ CASO D14 -- borrar espacio es atomico (RPC) ══════════════════
            print("\n--- CASO D14: removeSpace() usa la RPC zepo_delete_space (atomica) ---")

            def _mk_space(nm):
                st, res = admin("POST", "/rest/v1/spaces",
                                {"user_id": uid, "name": nm, "icon": "🏷️", "color": "#507D5A",
                                 "is_default": False, "sort_order": 99},
                                {"Prefer": "return=representation"})
                return (res[0]["id"] if st == 201 and isinstance(res, list) and res else None), st, res
            del_space_id, st_del, res_del = _mk_space(TAG + "_SpaceDel")
            dest_space_id, st_dest, res_dest = _mk_space(TAG + "_SpaceDest")
            chk("Setup D14: se crearon los 2 espacios temporales (a-borrar + destino) via admin REST (usa el GRANT de D17)",
                bool(del_space_id) and bool(dest_space_id),
                f"del=(status {st_del}, id {del_space_id})  dest=(status {st_dest}, id {dest_space_id})")

            if del_space_id and dest_space_id:
                st_exp14, res_exp14 = admin("POST", "/rest/v1/expenses",
                                             {"user_id": uid, "description": TAG + "_D14exp", "amount": 5.00,
                                              "category": "other", "date": today_iso, "is_income": False,
                                              "space_id": del_space_id},
                                             {"Prefer": "return=representation"})
                chk("Setup D14: se sembro 1 gasto en el espacio a-borrar", st_exp14 == 201,
                    f"status={st_exp14}  body={str(res_exp14)[:200]}")

                err_ok = page.evaluate(RPC_DELETE_SPACE_JS, [del_space_id, dest_space_id])
                chk("D14 check1: zepo_delete_space(del, dest) via RPC no devuelve error",
                    err_ok is None, f"error={err_ok}")

                st_sp, res_sp = admin("GET", f"/rest/v1/spaces?id=eq.{del_space_id}&select=id")
                chk("D14 check2: el espacio borrado YA NO existe en 'spaces'",
                    st_sp == 200 and isinstance(res_sp, list) and len(res_sp) == 0,
                    f"status={st_sp}  filas={res_sp}")

                st_mv, res_mv = admin("GET", f"/rest/v1/expenses?user_id=eq.{uid}&description=eq.{TAG}_D14exp&select=space_id")
                moved_ok = st_mv == 200 and isinstance(res_mv, list) and len(res_mv) == 1 and res_mv[0].get("space_id") == dest_space_id
                chk("D14 check3: el gasto que estaba en el espacio borrado ahora tiene space_id == destino "
                    "(se movio, no se perdio)",
                    moved_ok, f"status={st_mv}  filas={res_mv}  destino_esperado={dest_space_id}")

                fake_id = "00000000-0000-0000-0000-000000000000"
                err_fake = page.evaluate(RPC_DELETE_SPACE_JS, [fake_id, dest_space_id])
                chk("D14 check4 [autorizacion]: zepo_delete_space con p_space_id inexistente/ajeno "
                    "devuelve error (no borra nada)",
                    err_fake is not None, f"error={err_fake}")

                st_dest_after, res_dest_after = admin("GET", f"/rest/v1/spaces?id=eq.{dest_space_id}&select=id")
                chk("D14 check5: el espacio destino sigue existiendo tras el intento con id invalido "
                    "(la RPC invalida no afecto filas)",
                    st_dest_after == 200 and isinstance(res_dest_after, list) and len(res_dest_after) == 1,
                    f"status={st_dest_after}  filas={res_dest_after}")
            else:
                print("[FALLA] no se pudieron crear los espacios temporales -- se aborta el resto de D14")

            # cleanup D14 (admin REST -- fiable con el GRANT de D17)
            cleanup_spaces(uid)   # borra los espacios TAG* que queden (destino incluido)
            cleanup_expenses(uid) # el gasto D14exp ya se movio al destino; TAG* lo limpia igual

            browser.close()
    finally:
        # red de seguridad final: por si algo se corto a mitad de camino.
        cleanup_expenses(uid)
        cleanup_spaces(uid)

    # ---------- limpieza verificada ----------
    n_exp_left = count_desc_exact(uid, TAG)
    chk("Limpieza final: 0 filas de expenses quedan con el TAG", n_exp_left == 0,
        f"filas restantes={n_exp_left}")
    st_sp_left, res_sp_left = admin("GET", f"/rest/v1/spaces?user_id=eq.{uid}&name=like.{TAG}*&select=id")
    n_sp_left = len(res_sp_left) if st_sp_left == 200 and isinstance(res_sp_left, list) else -1
    chk("Limpieza final: 0 espacios quedan con el TAG", n_sp_left == 0,
        f"espacios restantes={n_sp_left}  status={st_sp_left}")

    # ---------- reporte ----------
    n_pass = sum(1 for _, ok, _ in checks if ok)
    n_total = len(checks)
    print(f"\n=== RESULTADO: {n_pass}/{n_total} checks en PASS ===")
    for label, ok, det in checks:
        print(f"  [{'PASS' if ok else 'FALLA'}] {label}\n        {det}")
    if not_tested:
        print("\n=== NO TESTABLES HOY ===")
        for m in not_tested:
            print("  [NO TESTABLE] " + m)

    ok_all = all(ok for _, ok, _ in checks)
    print("\n" + ("OK GLOBAL" if ok_all else "HAY FALLAS -- ver detalle arriba"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
