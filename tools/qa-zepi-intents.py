#!/usr/bin/env python3
"""
QA E2E REAL: Zepi agente escritor + memoria + probadita (F2/F4/F5/F6) — edge desplegado.

 1. add_records: "anota 4.56 ... y 1.11 ..." -> intent sanitizado con esos montos exactos.
 2. set_budget:  "ponme 77 de presupuesto de comida" -> {kind:set_budget, amount:77, category:food}.
 3. memoria:     "recuerda que mi meta..." -> fila REAL en zepi_memory (y limpieza).
 4. probadita:   free->pro por SQL: chat 200 con quota{limit:10}; cupo lleno -> upsell sin modelo;
                 insight sigue Max-only (403 para pro).
 5. restaura free -> 403 de nuevo (el candado free sigue intacto) + limpieza de zepi_usage.

El edge NUNCA escribe registros (los intents los ejecuta el cliente tras la tarjeta):
aqui solo se valida el CONTRATO sanitizado. USO: python tools/qa-zepi-intents.py
"""
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
except Exception:
    pass

import os
TOOLS = os.path.dirname(os.path.abspath(__file__))
PWA = os.path.dirname(TOOLS)
ZEPO_CFG = "C:/Users/alvar/lynoia/clients/zepo/config.json"
SB_CFG = "C:/Users/alvar/.claude/skills/supabase/config.json"
PASSWORD = "ZepoQA2026!"
MAX_EMAIL, FREE_EMAIL = "max@zepo.test", "free@zepo.test"
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
    print("=== QA Zepi agente escritor + memoria + probadita (edge real) ===")
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond)))
        print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

    today = datetime.date.today().isoformat()
    month = today[:7]
    snapshot = {"currency": "USD", "plan": "max", "today": today}
    jwt_max, uid_max = login(MAX_EMAIL)
    uid_max = uid_max.replace("'", "")

    # 1. add_records: montos exactos del usuario, sanitizados
    ok1, last = False, {}
    for _ in range(2):
        st, out = zepi(jwt_max, {"mode": "chat", "snapshot": snapshot, "debug": True, "messages": [
            {"role": "user", "text": "anota 4.56 de almuerzo y 1.11 de taxi de ayer"}]})
        last = out
        it = (out.get("intent") or {})
        items = it.get("items") or []
        amounts = sorted(float(x.get("amount", 0)) for x in items)
        dates_ok = all(re.match(r"^\d{4}-\d{2}-\d{2}$", str(x.get("date", ""))) and str(x.get("date")) <= today for x in items)
        if st == 200 and it.get("kind") == "add_records" and amounts == [1.11, 4.56] and dates_ok:
            ok1 = True; break
    check("1. add_records con montos exactos 4.56 + 1.11 y fechas ISO no futuras", ok1,
          f"intent={json.dumps(last.get('intent'), ensure_ascii=False)[:180]}")

    # 2. set_budget por categoria (max = elite+: siempre con categoria)
    ok2, last2 = False, {}
    for _ in range(2):
        st, out = zepi(jwt_max, {"mode": "chat", "snapshot": snapshot, "debug": True, "messages": [
            {"role": "user", "text": "ponme 77 de presupuesto de comida este mes"}]})
        last2 = out
        it = (out.get("intent") or {})
        if st == 200 and it.get("kind") == "set_budget" and float(it.get("amount", 0)) == 77 and it.get("category") == "food":
            ok2 = True; break
    check("2. set_budget {77, food} sanitizado", ok2, f"intent={json.dumps(last2.get('intent'), ensure_ascii=False)[:180]}")

    # 3. memoria de largo plazo: el modelo persiste memory_update en la BD real
    sql(f"delete from public.zepi_memory where user_id='{uid_max}';")
    ok3 = False
    for _ in range(2):
        st, out = zepi(jwt_max, {"mode": "chat", "snapshot": snapshot, "messages": [
            {"role": "user", "text": "recuerda que mi meta es ahorrar 500 al mes"}]})
        rows = sql(f"select facts from public.zepi_memory where user_id='{uid_max}';")
        if st == 200 and rows and rows[0].get("facts"):
            ok3 = True; break
    check("3. memory_update persiste en zepi_memory (fila real)", ok3)
    sql(f"delete from public.zepi_memory where user_id='{uid_max}';")

    # 4. probadita: free -> pro temporal, cupo server-side
    jwt_free, uid_free = login(FREE_EMAIL)
    uid_free = uid_free.replace("'", "")
    sql(f"delete from public.zepi_usage where user_id='{uid_free}';")
    sql(f"update public.users set plan='pro' where id='{uid_free}';")
    try:
        st_p, out_p = zepi(jwt_free, {"mode": "chat", "snapshot": {"today": today}, "messages": [
            {"role": "user", "text": "hola"}]})
        q = out_p.get("quota") or {}
        check("4a. pro entra al chat con cupo {limit:10}", st_p == 200 and q.get("limit") == 10 and q.get("used", 0) >= 1,
              f"status={st_p} quota={q}")
        sql(f"""insert into public.zepi_usage (user_id, month, msgs) values ('{uid_free}', '{month}', 10)
                on conflict (user_id, month) do update set msgs = 10;""")
        st_x, out_x = zepi(jwt_free, {"mode": "chat", "snapshot": {"today": today}, "messages": [
            {"role": "user", "text": "hola de nuevo"}]})
        check("4b. cupo lleno -> upsell sin modelo (quota_exhausted)", st_x == 200 and out_x.get("quota_exhausted") is True
              and "Max" in str(out_x.get("text", "")), f"status={st_x} out={str(out_x)[:140]}")
        st_i, out_i = zepi(jwt_free, {"mode": "insight", "snapshot": {"today": today}})
        check("4c. insight sigue Max-only (pro -> 403)", st_i == 403 and out_i.get("error") == "plan_required",
              f"status={st_i}")
    finally:
        # restaurar SIEMPRE: el usuario QA free debe volver a ser free
        sql(f"update public.users set plan='free' where id='{uid_free}';")
        sql(f"delete from public.zepi_usage where user_id='{uid_free}';")

    # 5. candado free intacto tras restaurar
    st_f, out_f = zepi(jwt_free, {"mode": "chat", "snapshot": {}, "messages": [{"role": "user", "text": "hola"}]})
    check("5. free restaurado -> 403 plan_required", st_f == 403 and out_f.get("error") == "plan_required", f"status={st_f}")

    # 6. limpieza verificada
    left_u = sql(f"select count(*) as n from public.zepi_usage where user_id='{uid_free}';")
    left_m = sql(f"select count(*) as n from public.zepi_memory where user_id='{uid_max}';")
    plan_f = sql(f"select plan from public.users where id='{uid_free}';")
    check("6. limpieza: sin zepi_usage/zepi_memory de QA y free vuelve a free",
          int(left_u[0]["n"]) == 0 and int(left_m[0]["n"]) == 0 and plan_f[0]["plan"] == "free")

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
