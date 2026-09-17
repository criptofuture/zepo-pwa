#!/usr/bin/env python3
"""
QA de SEGURIDAD (REST, 2 cuentas + 1 tercera): nadie reescribe un cobro por la API.

Hueco visto el 16-sep-2026 en public.payment_requests: la policy pr_update_own
(`FOR UPDATE USING (from_user_id = auth.uid() OR to_user_id = auth.uid())`, sin WITH
CHECK) junto con `GRANT ALL ... TO authenticated` deja que emisor Y receptor cambien
CUALQUIER columna de sus cobros. Sin abrir la app, solo con su token:
  - el receptor baja `amount` a 0.01 y el emisor lo ve como deuda confirmada
    (cobroFor y el saldo de Contactos leen pr.amount);
  - el receptor marca `settled` un cobro que nunca pago;
  - el emisor cambia `to_user_id` y le carga la deuda a un tercero;
  - cualquiera liga `receiver_expense_id` a un gasto AJENO, y despues
    cancel_split_cobro / retract_split_expense (SECURITY DEFINER) lo BORRAN.

Cada ataque se hace con el token del usuario, como lo haria alguien con DevTools, y
se juzga por la fila REAL leida con service_role (no por el codigo HTTP). Si un
ataque pasa, la fila se devuelve a como estaba para que el resto siga teniendo
sentido. Tambien corre los pasos LEGITIMOS de la app para probar que el candado no
los rompe (aceptar, ligar espejo, pagar, confirmar, rechazar, RPCs, borrar gastos).

Sale 1 si algun ataque pasa o algun paso legitimo falla; 2 si no puede ni probar.
Contra la base SIN 20260916_payment_requests_guard.sql tiene que salir 1; con ella, 0.
Limpia todo lo que siembra.   USO: python tools/qa-e2e-payreq-guard.py
"""
import sys, os, time, json, urllib.request, urllib.error, urllib.parse

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]


def _app_key():
    """La llave PUBLICA que usa la app (la misma que viaja en index.html): el login y los
    ataques tienen que entrar por la misma puerta que un usuario real."""
    import re
    src = open(os.path.join(PWA_DIR, "index.html"), encoding="utf-8").read()
    m = re.search(r"const SUPABASE_KEY\s*=\s*'([^']+)'", src)
    return m.group(1) if m else CFG["anon_key"]


ANON = _app_key()
SENDER = ("demo@zepo.test", "ZepoDemo2026!")      # emisor (necesita plan Max para insertar)
RECV = ("qa-to@zepo.test", "ZepoQAto2026!")       # receptor
THIRD = "free@zepo.test"  # tercero ajeno a los cobros; la crea tools/qa-accounts.py (tiene fila en users)
TAG = "GUARD_" + str(int(time.time()))
TODAY = time.strftime("%Y-%m-%d")
R = []  # (tipo, nombre, ok, detalle)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def http(method, path, body=None, token=None, prefer="return=representation"):
    headers = {"apikey": ANON if token else SK, "Authorization": "Bearer " + (token or SK),
               "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode() or ""
            return r.status, (json.loads(txt) if txt.strip().startswith(("[", "{")) else txt)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def ensure_user(email, password=None):
    st, users = http("GET", "/auth/v1/admin/users?page=1&per_page=200", prefer=None)
    for u in (users.get("users", []) if isinstance(users, dict) else []):
        if u.get("email") == email:
            return u["id"]
    if password is None:
        return None
    st, res = http("POST", "/auth/v1/admin/users",
                   {"email": email, "password": password, "email_confirm": True}, prefer=None)
    return res.get("id") if isinstance(res, dict) else None


def login(email, password):
    req = urllib.request.Request(URL + "/auth/v1/token?grant_type=password",
                                 data=json.dumps({"email": email, "password": password}).encode(),
                                 headers={"apikey": ANON, "Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()).get("access_token")
    except urllib.error.HTTPError as e:
        print(f"  login {email}: HTTP {e.code} {e.read().decode()[:120]}")
        return None


def row(pr_id):
    st, rows = http("GET", f"/rest/v1/payment_requests?id=eq.{pr_id}&select=*", prefer=None)
    return rows[0] if isinstance(rows, list) and rows else {}


def admin_patch(pr_id, patch):
    http("PATCH", f"/rest/v1/payment_requests?id=eq.{pr_id}", patch)


def seed_pr(name, **over):
    body = {"from_user_id": S_ID, "to_user_id": R_ID, "amount": 50, "category": "food",
            "description": f"{TAG} {name}", "expense_date": TODAY, "status": "pending"}
    body.update(over)
    st, rows = http("POST", "/rest/v1/payment_requests", body)
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"No pude sembrar el cobro '{name}': HTTP {st} {rows}")
    return rows[0]["id"]


def seed_exp(user_id, name):
    st, rows = http("POST", "/rest/v1/expenses", {
        "user_id": user_id, "amount": 50, "description": f"{TAG} {name}", "category": "food",
        "date": TODAY, "is_income": False})
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f"No pude sembrar el gasto '{name}': HTTP {st} {rows}")
    return rows[0]["id"]


def same(a, b):
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def ataque(nombre, token, pr_id, patch):
    """El ataque queda BLOQUEADO si ninguna columna del patch cambio en la fila real."""
    antes = row(pr_id)
    st, _ = http("PATCH", f"/rest/v1/payment_requests?id=eq.{pr_id}", patch, token=token)
    despues = row(pr_id)
    cambios = {k: (antes.get(k), despues.get(k)) for k in patch if not same(antes.get(k), despues.get(k))}
    R.append(("ataque", nombre, not cambios, f"HTTP {st}; " + (
        ", ".join(f"{k}: {a} -> {b}" for k, (a, b) in cambios.items()) if cambios else "fila intacta")))
    if cambios:  # devolver la fila a como estaba para que lo que sigue tenga sentido
        admin_patch(pr_id, {k: a for k, (a, b) in cambios.items()})


def paso(nombre, token, pr_id, patch):
    """Paso legitimo de la app: cada columna del patch debe quedar con el valor pedido."""
    st, _ = http("PATCH", f"/rest/v1/payment_requests?id=eq.{pr_id}", patch, token=token)
    fila = row(pr_id)
    malos = {k: fila.get(k) for k, v in patch.items() if not same(fila.get(k), v)}
    R.append(("legitimo", nombre, not malos, f"HTTP {st}; " + (
        ", ".join(f"{k} quedo {v}" for k, v in malos.items()) if malos else "aplicado")))


def main():
    global S_ID, R_ID
    S_ID, R_ID, T_ID = ensure_user(*SENDER), ensure_user(*RECV), ensure_user(THIRD)
    ts, tr = login(*SENDER), login(*RECV)
    faltan = [n for n, v in (("id emisor", S_ID), ("id receptor", R_ID), ("id tercero", T_ID),
                             ("login emisor", ts), ("login receptor", tr)) if not v]
    if faltan:
        print("No pude preparar las cuentas de QA (" + ", ".join(faltan) + "). No se probo nada.")
        return 2

    o1 = seed_exp(S_ID, "origen emisor")
    m1 = seed_exp(R_ID, "espejo receptor")
    v1 = seed_exp(T_ID, "gasto del tercero")
    p1 = seed_pr("principal", origin_expense_id=o1)

    # --- cobro pendiente: el receptor intenta reescribirlo ---
    ataque("receptor baja el monto a 0.01", tr, p1, {"amount": 0.01})
    ataque("receptor marca saldado sin pagar", tr, p1, {"status": "settled"})
    ataque("receptor cambia al emisor por un tercero", tr, p1, {"from_user_id": T_ID})
    ataque("receptor cambia descripcion y fecha", tr, p1, {"description": "otra cosa", "expense_date": "2020-01-01"})
    ataque("receptor se marca revision sin la RPC", tr, p1, {"review_requested": True})
    if "rejection_accepted_at" in row(p1):  # columnas de «rechazar cobro» (RPC reject_cobro y cia.)
        ataque("receptor finge que el emisor acepto su rechazo", tr, p1,
               {"rejection_accepted_at": "2026-09-16T00:00:00+00:00", "reject_reply": "ok, lo quito"})
        ataque("emisor escribe el comentario de rechazo del receptor", ts, p1, {"reject_comment": "no debo nada"})
    paso("receptor acepta (pending -> accepted)", tr, p1, {"status": "accepted"})
    ataque("receptor liga como espejo el gasto ORIGEN del emisor", tr, p1, {"receiver_expense_id": o1})
    ataque("receptor liga como espejo un gasto de un tercero", tr, p1, {"receiver_expense_id": v1})
    paso("receptor liga SU gasto espejo", tr, p1, {"receiver_expense_id": m1})
    ataque("receptor cambia el espejo ya ligado", tr, p1, {"receiver_expense_id": o1})

    # --- cobro aceptado: el emisor intenta reescribirlo ---
    ataque("emisor sube el monto despues de aceptado", ts, p1, {"amount": 999})
    ataque("emisor le pasa la deuda a un tercero", ts, p1, {"to_user_id": T_ID})
    ataque("emisor lo da por saldado sin aviso de pago", ts, p1, {"status": "settled"})
    ataque("emisor lo cancela sin la RPC", ts, p1, {"status": "cancelled"})

    # --- pago: receptor avisa, emisor rechaza, avisa otra vez, emisor confirma ---
    paso("receptor avisa que pago (accepted -> paid)", tr, p1, {"status": "paid"})
    ataque("receptor se confirma el pago a si mismo", tr, p1, {"status": "settled"})
    paso("emisor rechaza el pago (paid -> accepted)", ts, p1, {"status": "accepted"})
    paso("receptor avisa otra vez (accepted -> paid)", tr, p1, {"status": "paid"})
    paso("emisor confirma el pago (paid -> settled)", ts, p1, {"status": "settled"})
    ataque("receptor reabre un cobro saldado", tr, p1, {"status": "accepted"})

    # --- borrar gastos ligados: la FK los desliga (ON DELETE SET NULL) sin error ---
    st, _ = http("DELETE", f"/rest/v1/expenses?id=eq.{m1}", token=tr)
    R.append(("legitimo", "receptor borra su gasto espejo", row(p1).get("receiver_expense_id") is None,
              f"HTTP {st}; receiver_expense_id = {row(p1).get('receiver_expense_id')}"))
    st, _ = http("DELETE", f"/rest/v1/expenses?id=eq.{o1}", token=ts)
    R.append(("legitimo", "emisor borra su gasto origen", row(p1).get("origin_expense_id") is None,
              f"HTTP {st}; origin_expense_id = {row(p1).get('origin_expense_id')}"))

    # --- otros caminos legitimos ---
    p2 = seed_pr("para ignorar")
    paso("receptor ignora (pending -> declined)", tr, p2, {"status": "declined"})
    p3 = seed_pr("para revisar y cancelar", origin_expense_id=seed_exp(S_ID, "origen p3"))
    st, res = http("POST", "/rest/v1/rpc/request_cobro_review", {"p_cobro_id": p3}, token=tr, prefer=None)
    R.append(("legitimo", "receptor pide revision (RPC)", row(p3).get("review_requested") is True,
              f"HTTP {st}; review_requested = {row(p3).get('review_requested')}"))
    st, res = http("POST", "/rest/v1/rpc/cancel_split_cobro", {"p_cobro_id": p3}, token=ts, prefer=None)
    R.append(("legitimo", "emisor cancela el cobro (RPC)", row(p3).get("status") == "cancelled",
              f"HTTP {st}; status = {row(p3).get('status')}"))

    # --- insertar: un cobro nuevo nace pendiente y sin espejo ---
    def insertado(name, **over):
        body = {"from_user_id": S_ID, "to_user_id": R_ID, "amount": 20, "category": "food",
                "description": f"{TAG} {name}", "expense_date": TODAY, "status": "pending"}
        body.update(over)
        st, _ = http("POST", "/rest/v1/payment_requests", body, token=ts)
        _, rows = http("GET", f"/rest/v1/payment_requests?description=eq.{urllib.parse.quote(body['description'])}&select=id",
                       prefer=None)
        return st, bool(rows)
    st, ok = insertado("insert legitimo")
    R.append(("legitimo", "emisor envia un cobro pendiente", ok,
              f"HTTP {st}" + ("" if ok else " (si es 403: ¿demo@zepo.test sigue en plan Max?)")))
    st, hay = insertado("insert ya aceptado", status="accepted")
    R.append(("ataque", "emisor inserta un cobro ya aceptado", not hay, f"HTTP {st}; fila creada = {hay}"))
    st, hay = insertado("insert con espejo ajeno", receiver_expense_id=v1)
    R.append(("ataque", "emisor inserta con espejo = gasto de un tercero", not hay, f"HTTP {st}; fila creada = {hay}"))
    st, hay = insertado("insert con rechazo ya aceptado", reject_reply="aceptado",
                        rejection_accepted_at="2026-09-16T00:00:00+00:00")
    R.append(("ataque", "emisor inserta un rechazo ya resuelto", not hay, f"HTTP {st}; fila creada = {hay}"))

    malos = [r for r in R if not r[2]]
    for tipo, nombre, ok, det in R:
        estado = ("bloqueado" if ok else "PASO    ") if tipo == "ataque" else ("funciona " if ok else "ROTO     ")
        print(f"  [{'OK' if ok else 'FALLA'}] {tipo:8} {estado} {nombre}  ({det})")
    ataques = [r for r in R if r[0] == "ataque"]
    print(f"\nAtaques bloqueados: {sum(r[2] for r in ataques)}/{len(ataques)} · "
          f"pasos legitimos que funcionan: {sum(r[2] for r in R if r[0] == 'legitimo')}/{len(R) - len(ataques)}")
    print("TODO VERDE" if not malos else f"FALLA: {len(malos)} punto(s)")
    return 1 if malos else 0


def cleanup():
    http("DELETE", f"/rest/v1/payment_requests?description=like.{TAG}*", prefer=None)
    http("DELETE", f"/rest/v1/expenses?description=like.{TAG}*", prefer=None)


if __name__ == "__main__":
    try:
        code = main()
    finally:
        cleanup()
    sys.exit(code)
