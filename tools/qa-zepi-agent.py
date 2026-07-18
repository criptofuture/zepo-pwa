#!/usr/bin/env python3
"""
QA E2E REAL: Zepi agente lector (tool query_records) — F1.
Pega al edge function DESPLEGADO (sin mocks), patron de qa-accounts.py para credenciales.

 1. Siembra determinista en un mes historico (2025-03) para max@zepo.test via SQL:
    2 gastos de transporte (7.77 + 2.23 = 10.00) + 1 senuelo de comida (5.55).
 2. Control SQL: la suma de transporte de ese mes debe ser exactamente 10.00.
 3. Pregunta REAL a Zepi ("cuanto gaste en transporte en marzo de 2025") -> la
    respuesta debe contener la cifra del control (10) y NO la del senuelo (5.55... como total).
 4. Control negativo: free@zepo.test -> 403 plan_required (candado Max intacto).
 5. No-regresion: chat normal del mes actual responde 200 con texto.
 6. Limpieza de los datos sembrados (solo filas QA-HIST del usuario de QA).

USO: python tools/qa-zepi-agent.py    Sale 1 si algo falla.
"""
import json, re, sys, os, time, urllib.request, urllib.error

try:
    sys.stdout.reconfigure(line_buffering=True)  # que el output sobreviva si el proceso muere
except Exception:
    pass

TOOLS = os.path.dirname(os.path.abspath(__file__))
PWA = os.path.dirname(TOOLS)
ZEPO_CFG = "C:/Users/alvar/lynoia/clients/zepo/config.json"
SB_CFG = "C:/Users/alvar/.claude/skills/supabase/config.json"
PASSWORD = "ZepoQA2026!"
MAX_EMAIL, FREE_EMAIL = "max@zepo.test", "free@zepo.test"
SEED_MONTH = "2025-03"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lynoia-cli/1.0"


def _load():
    z = json.load(open(ZEPO_CFG, encoding="utf-8"))
    s = json.load(open(SB_CFG, encoding="utf-8"))
    sb = z.get("supabase", z)
    ref = s["project_ref"]
    base = (sb.get("url") or f"https://{ref}.supabase.co").rstrip("/")
    html = open(os.path.join(PWA, "index.html"), encoding="utf-8").read()
    m = re.search(r"sb_publishable_[A-Za-z0-9_-]+", html)
    if not m:
        print("FATAL: no encontre la publishable key en index.html"); sys.exit(1)
    return base, m.group(0), s["management_token"], ref


BASE, PUB_KEY, MGMT, REF = _load()
MGMT_URL = f"https://api.supabase.com/v1/projects/{REF}/database/query"


def sql(query):
    body = json.dumps({"query": query}).encode()
    r = urllib.request.Request(MGMT_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {MGMT}", "Content-Type": "application/json", "User-Agent": UA})
    return json.loads(urllib.request.urlopen(r, timeout=30).read().decode())


def login(email):
    # Retry con backoff: corriendo dentro de qa-all.py venimos de ~35 E2E con logins
    # reales seguidos -> GoTrue puede responder 429/5xx transitorio.
    last = None
    for wait in (0, 8, 20):
        if wait:
            time.sleep(wait)
        try:
            body = json.dumps({"email": email, "password": PASSWORD}).encode()
            r = urllib.request.Request(f"{BASE}/auth/v1/token?grant_type=password", data=body, method="POST",
                                       headers={"apikey": PUB_KEY, "Content-Type": "application/json", "User-Agent": UA})
            out = json.loads(urllib.request.urlopen(r, timeout=30).read().decode())
            return out["access_token"], out["user"]["id"]
        except Exception as e:
            last = e
            print(f"  ... login {email} fallo ({e}); reintento")
    raise RuntimeError(f"login imposible para {email}: {last}")


def zepi(jwt, payload):
    body = json.dumps(payload).encode()
    r = urllib.request.Request(f"{BASE}/functions/v1/zepo-companion", data=body, method="POST", headers={
        "apikey": PUB_KEY, "Authorization": f"Bearer {jwt}", "Content-Type": "application/json", "User-Agent": UA})
    try:
        resp = urllib.request.urlopen(r, timeout=90)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def main():
    print("=== QA Zepi agente lector (edge real) ===")
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond)))
        print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

    jwt_max, uid = login(MAX_EMAIL)

    # 1. siembra determinista en mes historico (fuera del snapshot)
    esc_uid = uid.replace("'", "")
    sql(f"delete from public.expenses where user_id='{esc_uid}' and description like 'QA-HIST%';")
    sql(f"""insert into public.expenses (user_id, amount, category, description, is_income, date)
            values ('{esc_uid}', 7.77, 'transport', 'QA-HIST taxi aeropuerto', false, '{SEED_MONTH}-05'),
                   ('{esc_uid}', 2.23, 'transport', 'QA-HIST bus interprovincial', false, '{SEED_MONTH}-12'),
                   ('{esc_uid}', 5.55, 'food', 'QA-HIST almuerzo senuelo', false, '{SEED_MONTH}-08');""")

    # 2. control SQL independiente
    rows = sql(f"""select coalesce(sum(amount),0) as total, count(*) as n from public.expenses
                   where user_id='{esc_uid}' and category='transport' and is_income=false
                   and date >= '{SEED_MONTH}-01' and date <= '{SEED_MONTH}-31'
                   and description like 'QA-HIST%';""")
    total = float(rows[0]["total"]); n = int(rows[0]["n"])
    check("1. control SQL: transporte 2025-03 = 10.00 (2 filas)", abs(total - 10.00) < 0.001 and n == 2, f"total={total} n={n}")

    # 3. pregunta historica real (2 intentos por no-determinismo del modelo)
    snapshot = {"currency": "USD", "plan": "max", "today": __import__("datetime").date.today().isoformat()}
    ok_hist, last_text, last_dbg = False, "", None
    for attempt in range(2):
        status, out = zepi(jwt_max, {"mode": "chat", "snapshot": snapshot, "debug": True, "messages": [
            {"role": "user", "text": "Cuanto gaste en transporte en marzo de 2025? Dame la cifra exacta."}]})
        last_text = str(out.get("text", ""))
        last_dbg = out.get("_dbg")
        if status == 200 and re.search(r"\b10(?:[.,]0{1,2})?\b", last_text):
            ok_hist = True; break
    if not ok_hist and last_dbg is not None:
        print("  DEBUG tool calls: " + json.dumps(last_dbg)[:500])
    check("2. Zepi responde la cifra historica real (10)", ok_hist, f"text={last_text[:120]}")
    check("3. la cifra no mezcla el senuelo de comida como total", "15.55" not in last_text.replace(",", "."), f"text={last_text[:120]}")

    # 4. candado Max intacto (control negativo)
    jwt_free, _ = login(FREE_EMAIL)
    status_f, out_f = zepi(jwt_free, {"mode": "chat", "snapshot": {}, "messages": [
        {"role": "user", "text": "hola"}]})
    check("4. free -> 403 plan_required", status_f == 403 and out_f.get("error") == "plan_required", f"status={status_f}")

    # 5. no-regresion: chat normal sin historia
    status_n, out_n = zepi(jwt_max, {"mode": "chat", "snapshot": snapshot, "messages": [
        {"role": "user", "text": "hola Zepi, que puedes hacer?"}]})
    check("5. chat normal responde 200 con texto", status_n == 200 and len(str(out_n.get("text", ""))) > 10, f"status={status_n}")

    # 6. limpieza
    sql(f"delete from public.expenses where user_id='{esc_uid}' and description like 'QA-HIST%';")
    left = sql(f"select count(*) as n from public.expenses where user_id='{esc_uid}' and description like 'QA-HIST%';")
    check("6. limpieza de datos sembrados", int(left[0]["n"]) == 0)

    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} PASS")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}")
        sys.exit(1)
