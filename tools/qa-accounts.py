#!/usr/bin/env python3
"""
Crea/asegura las 4 cuentas REALES de QA de planes, cada una con su `plan` real en
public.users. NO simula el plan en el front: la app lo lee del backend como un
usuario de verdad. Idempotente. Imprime solo email/id/plan (NUNCA llaves).

USO:
    python tools/qa-accounts.py            # crea/asegura las 4
    python tools/qa-accounts.py --set pro@zepo.test elite   # cambia el plan de una
    python tools/qa-accounts.py --list     # lista estado actual
"""
import sys, json, urllib.request, urllib.error

ZEPO_CFG = "C:/Users/alvar/lynoia/clients/zepo/config.json"
SB_CFG   = "C:/Users/alvar/.claude/skills/supabase/config.json"
PASSWORD = "ZepoQA2026!"
ACCOUNTS = [("free@zepo.test", "free"), ("pro@zepo.test", "pro"),
            ("elite@zepo.test", "elite"), ("max@zepo.test", "max")]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lynoia-cli/1.0"

def _load():
    z = json.load(open(ZEPO_CFG, encoding="utf-8"))
    s = json.load(open(SB_CFG, encoding="utf-8"))
    sb = z.get("supabase", z)
    secret = sb.get("secret_key")
    ref = s["project_ref"]
    base = sb.get("url") or f"https://{ref}.supabase.co"
    base = base.rstrip("/")
    return secret, s["management_token"], ref, base

SECRET, MGMT, REF, BASE = _load()
MGMT_URL = f"https://api.supabase.com/v1/projects/{REF}/database/query"

def sql(query):
    body = json.dumps({"query": query}).encode()
    r = urllib.request.Request(MGMT_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {MGMT}", "Content-Type": "application/json", "User-Agent": UA})
    return json.loads(urllib.request.urlopen(r, timeout=30).read().decode())

def admin(path, method="POST", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(f"{BASE}/auth/v1/admin/{path}", data=data, method=method, headers={
        "apikey": SECRET, "Authorization": f"Bearer {SECRET}", "Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(r, timeout=30).read().decode(), None
    except urllib.error.HTTPError as e:
        return e.read().decode(), e.code

def esc(s): return s.replace("'", "''")

def auth_id(email):
    rows = sql(f"select id from auth.users where email='{esc(email)}' limit 1;")
    return rows[0]["id"] if rows else None

def ensure(email, plan):
    uid = auth_id(email)
    if not uid:
        out, code = admin("users", "POST", {"email": email, "password": PASSWORD,
                                            "email_confirm": True})
        uid = auth_id(email)
    else:
        admin(f"users/{uid}", "PUT", {"password": PASSWORD, "email_confirm": True})
    if not uid:
        print(f"  [FALLA] {email}: no se obtuvo id"); return None
    # upsert public.users con plan real + expiración lejana + activo
    name = email.split("@")[0].upper()
    sql(f"""insert into public.users (id, email, name, plan, plan_expires_at, payment_status, accepted_privacy, accepted_at)
            values ('{uid}', '{esc(email)}', '{esc(name)}', '{esc(plan)}', now() + interval '365 days', 'active', true, now())
            on conflict (id) do update set plan=excluded.plan,
              plan_expires_at=excluded.plan_expires_at, payment_status='active', name=excluded.name;""")
    # profiles (para que sean buscables como amigos en Capa 2)
    try:
        sql(f"""insert into public.profiles (user_id, display_name)
                values ('{uid}', '{esc(name)}')
                on conflict (user_id) do update set display_name=excluded.display_name;""")
    except Exception:
        pass
    print(f"  [OK] {email}  id={uid}  plan={plan}")
    return uid

def show():
    rows = sql("""select u.email, u.plan, u.plan_expires_at from public.users u
                  where u.email like '%@zepo.test' order by u.email;""")
    print(json.dumps(rows, indent=2, default=str))

if __name__ == "__main__":
    if "--list" in sys.argv:
        show()
    elif "--set" in sys.argv:
        i = sys.argv.index("--set"); ensure(sys.argv[i+1], sys.argv[i+2]); show()
    else:
        print("=== Asegurando 4 cuentas de QA (plan REAL en backend) ===")
        for e, p in ACCOUNTS:
            ensure(e, p)
        print("=== Estado final ===")
        show()
