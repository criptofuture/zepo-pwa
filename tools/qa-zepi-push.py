#!/usr/bin/env python3
"""
QA E2E: zepi-push-insight (F7 Zepi proactivo) contra el edge DESPLEGADO.

 1. Sin X-Zepi-Secret -> 401 (nadie puede dispararlo sin el secreto del cron).
 2. Con el secreto REAL (extraido del job de pg_cron via SQL) -> 200 con {checked, sent, day}.
 3. El job de pg_cron existe y esta activo.

No valida la entrega del push (requiere un endpoint suscrito real); valida el contrato,
el candado y el cableado del cron. USO: python tools/qa-zepi-push.py
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
except Exception:
    pass

SB_CFG = "C:/Users/alvar/.claude/skills/supabase/config.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lynoia-cli/1.0"

s = json.load(open(SB_CFG, encoding="utf-8"))
REF, MGMT = s["project_ref"], s["management_token"]
MGMT_URL = f"https://api.supabase.com/v1/projects/{REF}/database/query"
FN_URL = f"https://{REF}.supabase.co/functions/v1/zepi-push-insight"


def sql(query):
    body = json.dumps({"query": query}).encode()
    r = urllib.request.Request(MGMT_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {MGMT}", "Content-Type": "application/json", "User-Agent": UA})
    return json.loads(urllib.request.urlopen(r, timeout=30).read().decode())


def call(headers):
    req = urllib.request.Request(FN_URL, data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": UA, **headers})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def main():
    print("=== QA Zepi push proactivo (edge + cron reales) ===")
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond)))
        print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

    # 1. candado: sin secreto -> 401
    st, out = call({})
    check("1. sin X-Zepi-Secret -> 401", st == 401, f"status={st}")

    # 2. el job de pg_cron existe, esta activo y contiene el secreto
    jobs = sql("select jobname, schedule, active, command from cron.job where jobname='zepi-push-insight-daily';")
    check("2. job pg_cron 'zepi-push-insight-daily' activo (0 13 * * *)",
          len(jobs) == 1 and jobs[0]["active"] and jobs[0]["schedule"].strip() == "0 13 * * *",
          f"jobs={[(j.get('jobname'), j.get('schedule'), j.get('active')) for j in jobs]}")
    m = re.search(r"X-Zepi-Secret','([0-9a-f]{16,})'", jobs[0]["command"]) if jobs else None
    check("3. el job lleva el secreto del edge", bool(m))
    if not m:
        print("FATAL: sin secreto no puedo probar el contrato"); sys.exit(1)

    # 3. contrato con secreto real: 200 y JSON {checked, sent, day}
    st2, out2 = call({"X-Zepi-Secret": m.group(1)})
    check("4. con secreto -> 200 {checked, sent, day}",
          st2 == 200 and isinstance(out2.get("checked"), int) and isinstance(out2.get("sent"), int)
          and re.match(r"^\d{4}-\d{2}-\d{2}$", str(out2.get("day", ""))), f"status={st2} out={str(out2)[:120]}")

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
