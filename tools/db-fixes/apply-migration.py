#!/usr/bin/env python3
"""Aplica un .sql a Supabase via Management API. NO imprime el token jamas.
USO: python tools/db-fixes/apply-migration.py <ruta.sql> [<ruta2.sql> ...]"""
import sys, os, json, urllib.request, urllib.error

CFG = json.load(open(os.path.expanduser("~/.claude/skills/supabase/config.json")))
REF = CFG["project_ref"]; TOKEN = CFG["management_token"]
URL = f"https://api.supabase.com/v1/projects/{REF}/database/query"
H = {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json",
     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def run_sql(sql):
    data = json.dumps({"query": sql}).encode()
    req = urllib.request.Request(URL, data=data, headers=H, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]

ok = True
for path in sys.argv[1:]:
    sql = open(path, encoding="utf-8").read()
    code, body = run_sql(sql)
    tag = "OK" if code in (200, 201) else "FALLA"
    if code not in (200, 201): ok = False
    print(f"[{tag}] {os.path.basename(path)} -> HTTP {code}  {body if code not in (200,201) else ''}")
sys.exit(0 if ok else 1)
