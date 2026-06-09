#!/usr/bin/env python3
"""Dispara el cobro de PRUEBA de $1 (plan 'test') contra la tarjeta tokenizada.
NO altera el plan del usuario. El secreto se lee de la variable de entorno
ZEPO_INTERNAL_SECRET (nunca se hardcodea ni se commitea).

USO (PowerShell):
  $env:ZEPO_INTERNAL_SECRET = "<el INTERNAL_SECRET de tu dashboard Supabase>"
  python tools/test-charge-1usd.py

El INTERNAL_SECRET esta en: Supabase -> Project -> Edge Functions -> Secrets -> INTERNAL_SECRET
"""
import json, os, sys, urllib.request, urllib.error

SECRET = os.environ.get("ZEPO_INTERNAL_SECRET", "").strip()
if not SECRET:
    print("FALTA el secreto. Define ZEPO_INTERNAL_SECRET y vuelve a correr.")
    sys.exit(1)

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
H = {"apikey": SK, "Authorization": "Bearer " + SK}

# userId = dueno de la tarjeta tokenizada
with urllib.request.urlopen(urllib.request.Request(URL + "/rest/v1/saved_cards?select=user_id,card_holder_name,last_digits,card_brand", headers=H)) as r:
    cards = json.loads(r.read().decode())
if not cards:
    print("No hay tarjeta tokenizada en saved_cards."); sys.exit(1)
card = cards[0]
uid = card["user_id"]
print(f"Cobrando $1 (prueba) a: {card.get('card_brand')} ****{card.get('last_digits')} · {card.get('card_holder_name')}")

# Disparar charge-token con plan 'test' ($1, no cambia el plan)
fn_url = URL + "/functions/v1/charge-token"
body = json.dumps({"userId": uid, "plan": "test"}).encode()
req = urllib.request.Request(fn_url, data=body, method="POST", headers={
    "Content-Type": "application/json",
    "X-Internal-Secret": SECRET,
})
try:
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:400]); sys.exit(1)

print("--- Respuesta charge-token ---")
print(json.dumps(resp, indent=2, ensure_ascii=False)[:1200])
pp = resp.get("response") or {}
status = pp.get("status") or pp.get("transactionStatus") or pp.get("message") or pp.get("errorCode")
if resp.get("ok"):
    print("\n>>> APROBADO. La tokenizacion y el cobro recurrente FUNCIONAN. ($1 cobrado de verdad)")
elif str(pp.get("errorCode")) == "26":
    print("\n>>> errorCode 26 = limite de 1 cobro/dia por tarjeta. El FORMATO es correcto (no se cobro de nuevo).")
else:
    print(f"\n>>> NO aprobado. Detalle: {status}")
