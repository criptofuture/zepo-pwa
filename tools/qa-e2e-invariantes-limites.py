#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QA E2E REAL: dos arreglos de limites en Zepo, contra Supabase real con Playwright.

Cuenta: elite@zepo.test / ZepoQA2026! (unica asignada a esta campana).

Caso D2 -- el tope de 1000 filas de PostgREST:
  PostgREST corta TODA respuesta en 1000 filas (Content-Range 0-999/*) y .limit(N) NO
  lo sube. El arreglo fue paginar con .range() en el helper _fetchAllRows (index.html),
  usado por exportCSV, exportExcel, exportPDF, loadSplits y loadLifetimeSavings. Aqui se
  certifica sembrando 1200 gastos y verificando que exportCSV() y loadLifetimeSavings()
  ven los 1200, no 1000.

Caso D1 -- recurrente dividido en "disponible para gastar":
  El getter pendingRecurringThisMonth ahora aplica split_pct (igual que el cron de la
  BD: v_mypart = round(amount * split_pct/100, 2)) en vez de sumar el TOTAL del
  recurrente. Se certifica con 3 plantillas (gasto dividido, gasto normal, ingreso
  dividido) mas un caso borde de split_pct=0.

Sale 1 si algun check falla.
"""
import sys, time, socket, threading, http.server, functools, os, json
import urllib.request, urllib.error
from datetime import date
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json"), encoding="utf-8"))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
EMAIL, PASSWORD = "elite@zepo.test", "ZepoQA2026!"
TAG = "LIM_" + str(int(time.time()))
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}
TOL = 0.015

checks = []  # (label, ok_bool, detalle)


def chk(label, ok, detalle=""):
    checks.append((label, bool(ok), detalle))
    return ok


# ── REST admin (service_role) -- solo setup/verificacion/limpieza de 'expenses' ──
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


def count_tagged_exact(user_id):
    """Cuenta filas con el TAG via Content-Range (Prefer: count=exact), sin bajar las
    1200 filas -- si usaramos un GET normal chocariamos con el mismo tope de 1000 que
    este script existe para probar que ya no afecta a la app."""
    headers = dict(H)
    headers["Range"] = "0-0"
    headers["Prefer"] = "count=exact"
    path = f"/rest/v1/expenses?user_id=eq.{user_id}&description=like.{TAG}*&select=id"
    r = urllib.request.Request(URL + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(r) as resp:
            cr = resp.headers.get("Content-Range", "")
            total = cr.split("/")[-1] if "/" in cr else ""
            return int(total) if total.isdigit() else -1
    except urllib.error.HTTPError as e:
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

GET_SPACE_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.loadSpaces();
  const def = (c.spaces||[]).find(s=>s.is_default) || c.spaces[0] || null;
  if (def) { c.spaceViewAll = false; c.activeSpaceId = def.id; }
  return def ? def.id : null;
}
"""

# Caso D2: descarga real de exportCSV() (mismo patron que tools/qa-e2e-invariantes-presup.py)
EXPORT_CSV_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.exportCSV();
  return true;
}
"""

# Fuerza plan 'max' en runtime SOLO si la cuenta elite@ no lo trae ya -- loadLifetimeSavings
# esta gateado a hasPlan('max') (index.html ~12576). Se reporta si se forzo o no.
MEASURE_LIFETIME_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const forced = !c.hasPlan('max');
  if (forced) c.userPlan = 'max';
  await c.loadLifetimeSavings();
  return { L: c.lifetimeSavings, forced, hasPlanMax: c.hasPlan('max') };
}
"""

# Caso D1: crea/borra recurring_templates via el cliente Supabase AUTENTICADO de la
# pagina (sb) -- la tabla NO tiene GRANT a service_role (verificado en sesiones
# anteriores), un INSERT/DELETE por admin REST devuelve 403 en silencio.
INSERT_TEMPLATES_JS = """
async (rows) => {
  const { data, error } = await sb.from('recurring_templates').insert(rows).select();
  if (error) throw new Error(error.message);
  return data;
}
"""
DELETE_TEMPLATES_JS = """
async (ids) => {
  if (!ids.length) return true;
  const { error } = await sb.from('recurring_templates').delete().in('id', ids);
  if (error) throw new Error(error.message);
  return true;
}
"""
COUNT_TEMPLATES_TAG_JS = """
async (tagPrefix) => {
  const { data, error } = await sb.from('recurring_templates').select('id').like('description', tagPrefix + '%');
  if (error) throw new Error(error.message);
  return data.length;
}
"""
MEASURE_PENDING_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c.loadRecurringTemplates();
  const p = c.pendingRecurringThisMonth;
  return { expenses: Math.round(p.expenses*100)/100, income: Math.round(p.income*100)/100,
           safeToSpend: Math.round(c.safeToSpend*100)/100 };
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


def main():
    today = date.today().isoformat()
    print(f"=== QA E2E: limites (tope 1000 filas + recurrente dividido) -- TAG={TAG} hoy={today} ===")

    uid = ensure_user(EMAIL, PASSWORD)
    if not uid:
        print("[FALLA] no se pudo asegurar elite@zepo.test"); return 1
    print(f"  cuenta elite id={uid}")

    port = free_port(); serve(port); time.sleep(0.5)
    base_url = f"http://127.0.0.1:{port}/index.html"

    rt_ids_abc = []
    rt_id_d = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
            page = ctx.new_page()
            page.on("dialog", lambda d: d.accept())
            login(page, base_url)
            space_id = page.evaluate(GET_SPACE_JS)
            print(f"  espacio por defecto = {space_id}")

            # ══════════════════ CASO D2 -- tope de 1000 filas ══════════════════
            print("\n--- CASO D2: paginado _fetchAllRows (1200 filas, tope PostgREST=1000) ---")

            L0 = page.evaluate(MEASURE_LIFETIME_JS)
            print(f"  lifetimeSavings ANTES = {L0['L']}  (forzado plan max={L0['forced']})")

            SEED_ROWS = [
                {"user_id": uid, "description": TAG + " D2row", "amount": 1.00, "category": "other",
                 "date": today, "is_income": False}
                for _ in range(1200)
            ]
            st_ins, res_ins = admin("POST", "/rest/v1/expenses", SEED_ROWS, {"Prefer": "return=minimal"})
            chk("Setup D2: POST de 1200 filas devolvio 201", st_ins == 201,
                f"status={st_ins}  body={str(res_ins)[:200]}")

            n_seeded = count_tagged_exact(uid)
            chk("D2 check1: se sembraron exactamente 1200 filas con el TAG (Content-Range, no GET simple)",
                n_seeded == 1200, f"esperado=1200  observado={n_seeded}")

            if n_seeded != 1200:
                print("[FALLA] siembra D2 incompleta -- se aborta el resto de checks D2 (export/lifetime)")
            else:
                try:
                    with page.expect_download(timeout=20000) as dl_info:
                        page.evaluate(EXPORT_CSV_JS)
                    dl = dl_info.value
                    csv_path = dl.path()
                    with open(csv_path, encoding="utf-8-sig") as f:
                        csv_text = f.read()
                    csv_lines = [l for l in csv_text.splitlines() if l]
                    csv_tag_lines = [l for l in csv_lines if TAG in l]
                    n_csv = len(csv_tag_lines)
                    chk("D2 check2: exportCSV() trae las 1200 filas del TAG, no 1000",
                        n_csv == 1200, f"esperado=1200  observado={n_csv}")
                    # control negativo: si el paginado NO funcionara, el CSV habria traido
                    # como maximo 1000 filas del TAG (el tope crudo de PostgREST). Afirmamos
                    # que ESO es distinto de lo observado -- si observado fuera 1000, este
                    # control (y el check2 de arriba) fallarian los dos.
                    chk("D2 CONTROL NEGATIVO: 1000 (lo que devolveria SIN paginar) != observado en el CSV",
                        n_csv != 1000,
                        f"1000 (bug sin _fetchAllRows) vs observado={n_csv} -- "
                        f"({'discrimina correctamente' if n_csv != 1000 else 'BUG EN LA APP o EN EL TEST: el CSV sigue cortado en 1000'})")
                except Exception as e:
                    chk("D2 check2: exportCSV() trae las 1200 filas del TAG, no 1000", False,
                        f"no se pudo capturar la descarga: {e}")
                    chk("D2 CONTROL NEGATIVO: 1000 != observado en el CSV", False, "descarga fallo, no hay observado")

                L1 = page.evaluate(MEASURE_LIFETIME_JS)
                delta_L = d2(L1["L"], L0["L"])
                detail_plan = f"(hasPlan('max') forzado en pagina: antes={L0['forced']} despues={L1['forced']})"
                # Las 1200 filas sembradas son GASTOS (is_income=false) -> lifetimeSavings
                # (ingreso-gasto) tiene que BAJAR exactamente 1200.00, no subir.
                chk("D2 check3: loadLifetimeSavings() baja exactamente -1200.00 (1200 gastos, lee TODAS las filas, no 1000)",
                    abs(delta_L - (-1200.00)) <= TOL,
                    f"esperado(delta)=-1200.00  observado(delta)={delta_L}  L0={L0['L']} L1={L1['L']}  {detail_plan}")

            # cleanup D2
            st_del, _ = cleanup_expenses(uid)
            n_left = count_tagged_exact(uid)
            chk("D2 cleanup: 0 filas de expenses quedan con el TAG", n_left == 0,
                f"filas restantes={n_left}  status DELETE={st_del}")

            # ══════════════ CASO D1 -- recurrente dividido en safeToSpend ══════════════
            print("\n--- CASO D1: pendingRecurringThisMonth aplica split_pct (no el total) ---")

            m0 = page.evaluate(MEASURE_PENDING_JS)
            print(f"  baseline ANTES de sembrar: {m0}")

            day = date.today().day
            TEMPLATES_ABC = [
                {"user_id": uid, "description": TAG + " D1_A_split50", "amount": 600, "category": "rent",
                 "is_income": False, "is_split": True, "split_pct": 50, "day_of_month": day,
                 "active": True, "last_generated": None},
                {"user_id": uid, "description": TAG + " D1_B_normal100", "amount": 100, "category": "other",
                 "is_income": False, "is_split": False, "split_pct": None, "day_of_month": day,
                 "active": True, "last_generated": None},
                {"user_id": uid, "description": TAG + " D1_C_income_split25", "amount": 200, "category": "salary",
                 "is_income": True, "is_split": True, "split_pct": 25, "day_of_month": day,
                 "active": True, "last_generated": None},
            ]

            insert_ok = True
            try:
                inserted_abc = page.evaluate(INSERT_TEMPLATES_JS, TEMPLATES_ABC)
                rt_ids_abc = [r["id"] for r in inserted_abc]
                chk("Setup D1: se insertaron las 3 plantillas A/B/C via cliente autenticado (sb)",
                    len(rt_ids_abc) == 3, f"insertadas={len(rt_ids_abc)}/3  ids={rt_ids_abc}")
            except Exception as e:
                insert_ok = False
                chk("Setup D1: se insertaron las 3 plantillas A/B/C via cliente autenticado (sb)", False,
                    f"INSERT FALLO: {e}")

            if not insert_ok or len(rt_ids_abc) != 3:
                print("[FALLA] siembra D1 (A/B/C) incompleta -- se aborta el resto de checks D1")
            else:
                m1 = page.evaluate(MEASURE_PENDING_JS)
                d_exp = d2(m1["expenses"], m0["expenses"])
                d_inc = d2(m1["income"], m0["income"])
                d_safe = d2(m1["safeToSpend"], m0["safeToSpend"])
                print(f"  medicion DESPUES de A/B/C: {m1}  deltas: exp={d_exp} inc={d_inc} safe={d_safe}")

                chk("D1 check5: delta pendingRecurringThisMonth.expenses == 400.00 (300 de A al 50% + 100 de B)",
                    abs(d_exp - 400.00) <= TOL, f"esperado=400.00  observado={d_exp}")
                chk("D1 check6: delta pendingRecurringThisMonth.income == 50.00 (200 de C al 25%)",
                    abs(d_inc - 50.00) <= TOL, f"esperado=50.00  observado={d_inc}")
                chk("D1 check7: delta safeToSpend == -400.00 (resta solo los recurrentes de GASTO pendientes)",
                    abs(d_safe - (-400.00)) <= TOL, f"esperado=-400.00  observado={d_safe}")
                chk("D1 CONTROL NEGATIVO: hipotesis 'delta expenses == 700.00 (suma los TOTALES, 600+100, no mi parte)' debe DAR FALSO",
                    abs(d_exp - 700.00) > TOL,
                    f"delta observado={d_exp}  700.00-invertido={700.00}  "
                    f"({'el control discrimina correctamente' if abs(d_exp - 700.00) > TOL else 'BUG: sigue sumando el total, no split_pct'})")

                # --- check9: caso borde split_pct=0, medido en SU PROPIO delta ---
                m_before_d = page.evaluate(MEASURE_PENDING_JS)
                TEMPLATE_D = {"user_id": uid, "description": TAG + " D1_D_split0", "amount": 600, "category": "rent",
                              "is_income": False, "is_split": True, "split_pct": 0, "day_of_month": day,
                              "active": True, "last_generated": None}
                try:
                    inserted_d = page.evaluate(INSERT_TEMPLATES_JS, [TEMPLATE_D])
                    rt_id_d = inserted_d[0]["id"] if inserted_d else None
                    chk("Setup D1: se inserto la plantilla D (split_pct=0)", rt_id_d is not None,
                        f"insertada id={rt_id_d}")
                except Exception as e:
                    chk("Setup D1: se inserto la plantilla D (split_pct=0)", False, f"INSERT FALLO: {e}")

                if rt_id_d is not None:
                    m_after_d = page.evaluate(MEASURE_PENDING_JS)
                    delta_d_exp = d2(m_after_d["expenses"], m_before_d["expenses"])
                    chk("D1 check9 [borde]: delta expenses con split_pct=0 == 0.00 (NO 600, NO 300 -- '0 || 100' clasico)",
                        abs(delta_d_exp - 0.00) <= TOL,
                        f"esperado=0.00  observado={delta_d_exp}  "
                        f"(si el bug '|| 100' reapareciera daria 600.00; si tomara la mitad por error daria 300.00)")
                else:
                    print("[FALLA] no se pudo sembrar la plantilla D -- check9 no se puede medir")

            # cleanup D1
            all_rt_ids = rt_ids_abc + ([rt_id_d] if rt_id_d else [])
            try:
                page.evaluate(DELETE_TEMPLATES_JS, all_rt_ids)
            except Exception as e:
                chk("D1 cleanup: DELETE de las 4 plantillas", False, f"DELETE FALLO: {e}")
            n_rt_left = page.evaluate(COUNT_TEMPLATES_TAG_JS, TAG)
            chk("D1 cleanup: 0 plantillas quedan con el TAG", n_rt_left == 0, f"plantillas restantes={n_rt_left}")

            browser.close()
    finally:
        # red de seguridad final: por si algo se corto a mitad de camino.
        cleanup_expenses(uid)

    # ---------- reporte ----------
    n_pass = sum(1 for _, ok, _ in checks if ok)
    n_total = len(checks)
    print(f"\n=== RESULTADO: {n_pass}/{n_total} checks en PASS ===")
    for label, ok, det in checks:
        print(f"  [{'PASS' if ok else 'FALLA'}] {label}\n        {det}")

    ok_all = all(ok for _, ok, _ in checks)
    print("\n" + ("OK GLOBAL" if ok_all else "HAY FALLAS -- ver detalle arriba"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
