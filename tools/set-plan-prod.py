#!/usr/bin/env python3
"""
Setea el plan REAL (en public.users) de una cuenta de prod por email, SIN tocar
su contrasena. Idempotente. Imprime solo email/id/plan (NUNCA llaves).

USO:
    python tools/set-plan-prod.py --show <email>              # inspecciona
    python tools/set-plan-prod.py --set  <email> <plan>       # setea plan + 365d
"""
import sys, json, urllib.request, urllib.error

ZEPO_CFG = "C:/Users/alvar/lynoia/clients/zepo/config.json"
SB_CFG   = "C:/Users/alvar/.claude/skills/supabase/config.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lynoia-cli/1.0"

def _load():
    z = json.load(open(ZEPO_CFG, encoding="utf-8"))
    s = json.load(open(SB_CFG, encoding="utf-8"))
    sb = z.get("supabase", z)
    ref = s["project_ref"]
    return s["management_token"], ref

MGMT, REF = _load()
MGMT_URL = f"https://api.supabase.com/v1/projects/{REF}/database/query"

def sql(query):
    body = json.dumps({"query": query}).encode()
    r = urllib.request.Request(MGMT_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {MGMT}", "Content-Type": "application/json", "User-Agent": UA})
    return json.loads(urllib.request.urlopen(r, timeout=30).read().decode())

def esc(s): return s.replace("'", "''")

def show(email):
    a = sql(f"select id, email, created_at, last_sign_in_at from auth.users where email='{esc(email)}' limit 1;")
    print("auth.users:", json.dumps(a, indent=2, default=str))
    if not a:
        print("  -> No existe la cuenta en auth (todavia no se ha registrado).")
        return None
    uid = a[0]["id"]
    p = sql(f"select id, email, name, plan, plan_expires_at, payment_status from public.users where id='{uid}' limit 1;")
    print("public.users:", json.dumps(p, indent=2, default=str))
    return uid, (p[0] if p else None)

def set_plan(email, plan):
    res = show(email)
    if not res:
        print("ABORT: la cuenta no existe en auth.users; pide a Alvaro que se registre primero.")
        return
    uid, prow = res
    if prow:
        sql(f"""update public.users
                set plan='{esc(plan)}', plan_expires_at=now() + interval '365 days',
                    payment_status='active'
                where id='{uid}';""")
    else:
        name = email.split("@")[0]
        sql(f"""insert into public.users (id, email, name, plan, plan_expires_at, payment_status)
                values ('{uid}', '{esc(email)}', '{esc(name)}', '{esc(plan)}',
                        now() + interval '365 days', 'active');""")
    print("\n=== Estado final ===")
    show(email)

if __name__ == "__main__":
    if "--show" in sys.argv:
        i = sys.argv.index("--show"); show(sys.argv[i+1])
    elif "--set" in sys.argv:
        i = sys.argv.index("--set"); set_plan(sys.argv[i+1], sys.argv[i+2])
    else:
        print(__doc__)
