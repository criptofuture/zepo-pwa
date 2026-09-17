#!/usr/bin/env python3
"""
QA E2E REAL (2 cuentas, clics de verdad): rechazar un cobro con comentario y que el emisor
acepte o no el rechazo (v203). Reemplaza a qa-e2e-cancel-cobro.py ("pedir revision").

Siembra (service_role) tres cobros del EMISOR (demo) al RECEPTOR (qa-to):
  A  pizza    pendiente, ligado a un gasto dividido entre qa-to (40%) y "Pedro QA" (20%, sin Zepo)
  B  directo  ya ACEPTADO, sin gasto origen, con gasto espejo del receptor
  C  solo     pendiente, ligado a un gasto dividido SOLO con qa-to (50%)
  E  cambio   pendiente, sin gasto origen: el receptor lo rechaza y despues lo ACEPTA igual
FASE 1 receptor: rechaza A (con comentario), C (sin comentario) y B (deuda ya aceptada).
FASE 2 emisor:   ve los 3 en RECHAZADOS; NO acepta A (con respuesta); acepta B y C.
FASE 3 receptor: ve el aviso de B y C; ve la respuesta en A y lo rechaza otra vez; "Entendido" en B;
                 acepta E aunque lo habia rechazado (el rechazo se retira).
FASE 4 emisor:   acepta el rechazo de A -> el gasto absorbe SOLO la parte de qa-to; Pedro sigue.
Luego seguridad por RPC con el token de cada uno. Verifica en Supabase tras cada paso. Limpia todo.
Falla sobre v202 (no existe el boton "Rechazar"). Sale 1 si algo falla.
"""
import sys, re, time, socket, threading, http.server, functools, os, json, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
# La llave anon "legacy" del config esta apagada desde el 27-may; la publica es la que usa la app.
ANON = re.search(r"sb_publishable_[A-Za-z0-9_-]+", open(os.path.join(PWA_DIR, "index.html"), encoding="utf-8").read()).group(0)
SENDER_EMAIL = "demo@zepo.test"; SENDER_PASS = "ZepoDemo2026!"
RECV_EMAIL = "qa-to@zepo.test"; RECV_PASS = "ZepoQAto2026!"
TAG = "RJ_" + str(int(time.time()))
TODAY = time.strftime("%Y-%m-%d")
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}
CHECKS = []


def req(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, data=data, headers=headers or H, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            txt = resp.read().decode() or "[]"
            return resp.status, (json.loads(txt) if txt.strip()[:1] in "[{tf" else txt)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def admin(method, path, body=None, ret=False):
    h = dict(H)
    if ret: h["Prefer"] = "return=representation"
    return req(method, path, body, h)


def one(table, id_, cols):
    st, rows = admin("GET", f"/rest/v1/{table}?id=eq.{id_}&select={cols}")
    return rows[0] if isinstance(rows, list) and rows else {}


def check(label, ok):
    CHECKS.append((label, bool(ok)))


def user_id(email, password):
    st, users = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    for u in (users.get("users", []) if isinstance(users, dict) else []):
        if u.get("email") == email: return u["id"]
    st, res = admin("POST", "/auth/v1/admin/users", {"email": email, "password": password, "email_confirm": True})
    return res.get("id") if isinstance(res, dict) else None


def token(email, password):
    st, res = req("POST", "/auth/v1/token?grant_type=password", {"email": email, "password": password},
                  {"apikey": ANON, "Content-Type": "application/json"})
    return res.get("access_token") if isinstance(res, dict) else None


def rpc(tok, fn, args):
    h = {"apikey": ANON, "Content-Type": "application/json", "Authorization": "Bearer " + (tok or ANON)}
    return req("POST", f"/rest/v1/rpc/{fn}", args, h)


def seed(snd, rcv):
    def exp(body):
        st, rows = admin("POST", "/rest/v1/expenses", body, ret=True)
        return rows[0]["id"]
    def pr(body):
        st, rows = admin("POST", "/rest/v1/payment_requests", body, ret=True)
        return rows[0]["id"]
    base = {"user_id": snd, "category": "food", "date": TODAY, "is_income": False, "is_split": True, "split_status": "pendiente"}
    oa = exp({**base, "amount": 12, "description": TAG + " pizza", "split_total": 30, "split_pct": 40, "split_pending": 18,
              "split_persona": "QA To, Pedro QA",
              "split_people": [{"name": "QA To", "pct": 40, "user_id": rcv}, {"name": "Pedro QA", "pct": 20, "user_id": None}]})
    oc = exp({**base, "amount": 10, "description": TAG + " solo", "split_total": 20, "split_pct": 50, "split_pending": 10,
              "split_persona": "QA To", "split_people": [{"name": "QA To", "pct": 50, "user_id": rcv}]})
    mirror = exp({"user_id": rcv, "amount": 7, "category": "food", "date": TODAY, "is_income": False,
                  "is_split": False, "split_status": None, "description": TAG + " directo espejo"})
    p = {"from_user_id": snd, "to_user_id": rcv, "category": "food", "expense_date": TODAY}
    a = pr({**p, "amount": 12, "description": TAG + " pizza", "status": "pending", "origin_expense_id": oa})
    b = pr({**p, "amount": 7, "description": TAG + " directo", "status": "accepted", "receiver_expense_id": mirror})
    c = pr({**p, "amount": 10, "description": TAG + " solo", "status": "pending", "origin_expense_id": oc})
    d = pr({**p, "amount": 3, "description": TAG + " seguridad", "status": "pending"})
    e = pr({**p, "amount": 4, "description": TAG + " cambio", "status": "pending"})
    return dict(oa=oa, oc=oc, mirror=mirror, a=a, b=b, c=c, d=d, e=e)


def cleanup():
    admin("DELETE", f"/rest/v1/payment_requests?description=like.{TAG}*")
    admin("DELETE", f"/rest/v1/expenses?description=like.{TAG}*")


def wait_db(fn, secs=10):
    end = time.time() + secs
    while time.time() < end:
        if fn(): return True
        time.sleep(0.5)
    return fn()


# La app cierra la hoja ANTES de terminar de recargar los cobros (submitRejectSheet), asi que
# leer la pantalla tras una espera fija falla a ratos: se espera la condicion.
wait_ui = wait_db


def sheet_text(page):
    s = page.locator(".sheet:visible")
    return s.last.inner_text() if s.count() else ""


def serve():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}/index.html"


LOGIN_JS = """async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}"""

GOTO_JS = """async (sub) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showWelcomeCarousel = false; c.showOnbV2 = false;  // las cuentas de QA no terminaron la bienvenida
  c.tab = 'cuentas'; c.cuentasTab = sub;
  await Promise.all([c.loadSplits(), c.loadPaymentRequests()]);
}"""

def session(base, email, password, fn):
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.goto(base, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        err = page.evaluate(LOGIN_JS, [email, password])
        if err:
            b.close(); raise SystemExit(f"[FALLA] login {email}: {err}")
        page.wait_for_function("()=>!!window.Alpine.$data(document.querySelector('#app')).user", timeout=20000)
        page.wait_for_timeout(1500)
        try:
            fn(page)
        finally:
            b.close()


def goto(page, sub):
    page.evaluate(GOTO_JS, sub); page.wait_for_timeout(700)


def card(page, text, button):
    """El div mas interno que contiene `text` y un boton `button` (una tarjeta de lista)."""
    return page.locator(f"xpath=//div[contains(., '{text}')][.//button[normalize-space()='{button}']]").last


def sheet(page):
    return page.locator(".sheet", has=page.locator("#rej-text"))


def send_sheet(page, text, submit):
    sheet(page).wait_for(timeout=5000)
    if text: page.locator("#rej-text").fill(text)
    sheet(page).get_by_role("button", name=submit, exact=True).click()
    sheet(page).wait_for(state="detached", timeout=10000)


def row_has(page, text, chip, who=None):
    """La fila (el div clicable) que muestra `text` tiene una linea exactamente `chip`."""
    els = page.get_by_text(text, exact=True)
    for i in range(els.count()):
        if not els.nth(i).is_visible():
            continue
        row = els.nth(i).locator("xpath=ancestor::div[contains(@style,'cursor:pointer')][1]")
        lines = row.inner_text().splitlines() if row.count() else []
        if chip in [l.strip() for l in lines] and (who is None or any(who in l for l in lines)):
            return True
    return False


def open_solicitud(page, text):
    item = page.get_by_text(text, exact=True).first
    if not item.is_visible():
        page.locator("xpath=//div[contains(normalize-space(), ' solicitudes · $')][not(.//div[contains(normalize-space(), ' solicitudes · $')])]").first.click()
        page.wait_for_timeout(400)
    item.click()
    page.get_by_role("button", name="Aceptar cobro").wait_for(timeout=5000)


def fase1(page, ids):
    goto(page, "debo")
    open_solicitud(page, TAG + " pizza")
    check("receptor: el detalle tiene Aceptar cobro y Rechazar", page.get_by_role("button", name="Rechazar", exact=True).is_visible())
    check("receptor: ya no hay Ignorar ni Pedir revision",
          page.get_by_role("button", name="Ignorar").count() == 0 and page.get_by_text("Pedir revision").count() == 0)
    # x-show le borra el display:flex al boton y el icono queda desalineado (visto el 16-sep)
    check("receptor: el botón Rechazar mantiene su diseño (flex)",
          page.get_by_role("button", name="Rechazar", exact=True).evaluate("b => getComputedStyle(b).display") == "flex")
    page.get_by_role("button", name="Rechazar", exact=True).click()
    send_sheet(page, "No comí pizza ese día", "Enviar rechazo")
    check("rechazar A -> rechazo abierto con el comentario", wait_db(lambda: one("payment_requests", ids["a"], "review_requested,reject_comment")
          == {"review_requested": True, "reject_comment": "No comí pizza ese día"}))

    open_solicitud(page, TAG + " solo")
    page.get_by_role("button", name="Rechazar", exact=True).click()
    send_sheet(page, "", "Enviar rechazo")
    check("rechazar C sin comentario -> comentario vacío (null)", wait_db(lambda: one("payment_requests", ids["c"], "review_requested,reject_comment")
          == {"review_requested": True, "reject_comment": None}))

    open_solicitud(page, TAG + " cambio")
    page.get_by_role("button", name="Rechazar", exact=True).click()
    send_sheet(page, "Creo que no", "Enviar rechazo")

    page.get_by_text(TAG + " directo", exact=True).first.click()
    page.get_by_role("button", name="Rechazar", exact=True).click()
    send_sheet(page, "Ya te pagué en efectivo", "Enviar rechazo")
    check("rechazar B (deuda YA aceptada) -> rechazo abierto", wait_db(lambda: one("payment_requests", ids["b"], "status,review_requested")
          == {"status": "accepted", "review_requested": True}))
    check("receptor: la fila de A dice RECHAZASTE · ESPERANDO", wait_ui(lambda: row_has(page, TAG + " pizza", "RECHAZASTE · ESPERANDO")))


def fase2(page, ids):
    goto(page, "me-deben")
    a = card(page, TAG + " pizza", "No aceptar")
    check("emisor: A aparece en RECHAZADOS con su comentario", wait_ui(lambda: a.is_visible() and "No comí pizza ese día" in a.inner_text()))
    check("emisor: la fila de A en PENDIENTES dice RECHAZADO", wait_ui(lambda: row_has(page, TAG + " pizza", "RECHAZADO", "QA To")))
    chips = page.get_by_text("RECHAZADO", exact=True)
    widths = [chips.nth(i).bounding_box()["width"] for i in range(chips.count()) if chips.nth(i).is_visible()]
    check("emisor: la etiqueta RECHAZADO no se estira (x-show le quitaba el inline-block)", widths and max(widths) < 120)
    a.get_by_role("button", name="No aceptar").click()
    send_sheet(page, "Sí fuiste, tengo el recibo", "Enviar respuesta")
    r = {}
    def denied():
        r.update(one("payment_requests", ids["a"], "status,review_requested,reject_reply,rejection_denied_at"))
        return (r.get("review_requested") is False and r.get("reject_reply") == "Sí fuiste, tengo el recibo"
                and bool(r.get("rejection_denied_at")) and r.get("status") == "pending")
    check("no aceptar A -> vuelve al receptor con la respuesta", wait_db(denied))
    check("emisor: la fila de A vuelve a POR ACEPTAR", wait_ui(lambda: row_has(page, TAG + " pizza", "POR ACEPTAR", "QA To")))

    card(page, TAG + " directo", "Aceptar rechazo").get_by_role("button", name="Aceptar rechazo").click()
    txt = sheet(page).inner_text()
    check("hoja de B: explica que se anula y que se borra el gasto del otro", "ya no te debe esos $7.00" in txt and "se borra el gasto" in txt)
    send_sheet(page, "Tienes razón, fue un error", "Aceptar rechazo")
    check("aceptar B -> cobro anulado con comentario", wait_db(lambda: one("payment_requests", ids["b"], "status,reject_reply,rejection_notice_seen")
          == {"status": "cancelled", "reject_reply": "Tienes razón, fue un error", "rejection_notice_seen": False}))
    check("aceptar B -> se borra el gasto espejo del receptor", one("expenses", ids["mirror"], "id") == {})

    card(page, TAG + " solo", "Aceptar rechazo").get_by_role("button", name="Aceptar rechazo").click()
    check("hoja de C: dice que tu parte pasa de $10.00 a $20.00", "pasa de $10.00 a $20.00" in sheet(page).inner_text())
    send_sheet(page, "", "Aceptar rechazo")
    check("aceptar C -> anulado", wait_db(lambda: one("payment_requests", ids["c"], "status").get("status") == "cancelled"))
    oc = one("expenses", ids["oc"], "is_split,amount,split_people,split_pending,split_status")
    check("aceptar C (una sola persona) -> el gasto vuelve a 100% ($20)", oc.get("is_split") is False
          and abs(float(oc.get("amount") or 0) - 20) < 0.01 and oc.get("split_people") is None and oc.get("split_status") is None)


def fase3(page, ids):
    goto(page, "debo")
    nb = card(page, TAG + " directo", "Entendido")
    check("receptor: aviso de B con el comentario del emisor", wait_ui(lambda: nb.is_visible() and "Tienes razón, fue un error" in nb.inner_text()))
    check("receptor: aviso de C (sin comentario)", wait_ui(lambda: card(page, TAG + " solo", "Entendido").is_visible()))
    open_solicitud(page, TAG + " pizza")
    check("receptor: A muestra 'no aceptó tu rechazo' con la respuesta", wait_ui(lambda: "no aceptó tu rechazo" in sheet_text(page)
          and "Sí fuiste, tengo el recibo" in sheet_text(page)))
    page.get_by_role("button", name="Rechazar otra vez").click()
    send_sheet(page, "Revisa bien, fue Pedro", "Enviar rechazo")
    check("rechazar otra vez A -> rechazo abierto, respuesta vieja limpia", wait_db(lambda: one("payment_requests", ids["a"],
          "review_requested,reject_comment,reject_reply,rejection_denied_at") == {"review_requested": True,
          "reject_comment": "Revisa bien, fue Pedro", "reject_reply": None, "rejection_denied_at": None}))
    open_solicitud(page, TAG + " cambio")
    check("receptor: E rechazado muestra 'Rechazaste' y deja aceptar igual", wait_ui(lambda: "Rechazaste este cobro" in sheet_text(page)
          and page.get_by_role("button", name="Rechazar", exact=True).count() == 0))
    page.get_by_role("button", name="Aceptar cobro").click()
    page.get_by_role("button", name="Solo aceptar (sin registrar)").click()
    check("aceptar E rechazado -> aceptado y el rechazo se retira", wait_db(lambda: one("payment_requests", ids["e"],
          "status,review_requested,rejection_denied_at") == {"status": "accepted", "review_requested": False, "rejection_denied_at": None}))
    card(page, TAG + " directo", "Entendido").get_by_role("button", name="Entendido").click()
    check("Entendido -> el aviso de B queda visto", wait_db(lambda: one("payment_requests", ids["b"], "rejection_notice_seen")
          .get("rejection_notice_seen") is True))


def fase4(page, ids):
    goto(page, "me-deben")
    card(page, TAG + " pizza", "Aceptar rechazo").get_by_role("button", name="Aceptar rechazo").click()
    txt = sheet(page).inner_text()
    check("hoja de A: $12.00 -> $24.00 y avisa que los demás siguen igual", "pasa de $12.00 a $24.00" in txt and "demás personas" in txt)
    send_sheet(page, "", "Aceptar rechazo")
    check("aceptar A -> anulado", wait_db(lambda: one("payment_requests", ids["a"], "status").get("status") == "cancelled"))
    oa = one("expenses", ids["oa"], "is_split,amount,split_total,split_pct,split_pending,split_persona,split_people,split_status")
    people = oa.get("split_people") or []
    num = lambda k: float(oa.get(k) or 0)
    check("aceptar A (varias personas) -> absorbes SOLO la parte de qa-to", oa.get("is_split") is True
          and abs(num("amount") - 24) < 0.01 and abs(num("split_pending") - 6) < 0.01
          and abs(num("split_pct") - 80) < 0.01 and abs(num("split_total") - 30) < 0.01)
    check("aceptar A -> Pedro sigue en el gasto", oa.get("split_persona") == "Pedro QA"
          and len(people) == 1 and people[0].get("name") == "Pedro QA" and oa.get("split_status") == "pendiente")


def seguridad(ids):
    ts, tr = token(SENDER_EMAIL, SENDER_PASS), token(RECV_EMAIL, RECV_PASS)
    d = {"p_cobro_id": ids["d"]}
    check("seguridad: el emisor NO puede rechazar su propio cobro", rpc(ts, "reject_cobro", d)[1] is False)
    check("seguridad: sin sesión no se puede rechazar", rpc(None, "reject_cobro", d)[0] >= 400)
    check("seguridad: el receptor sí rechaza D", rpc(tr, "reject_cobro", d)[1] is True)
    check("seguridad: el receptor NO puede aceptar su propio rechazo", rpc(tr, "accept_cobro_rejection", d)[1] is False)
    check("seguridad: el receptor NO puede negar su propio rechazo", rpc(tr, "deny_cobro_rejection", d)[1] is False)
    check("seguridad: el emisor NO puede marcar como visto un aviso ajeno",
          rpc(ts, "dismiss_rejection_notice", {"p_cobro_id": ids["b"]})[1] is False)
    check("seguridad: la función interna no se puede llamar", rpc(tr, "_cobro_comment", {"p_text": "x"})[0] >= 400)
    check("seguridad: D sigue pendiente y rechazado", one("payment_requests", ids["d"], "status,review_requested")
          == {"status": "pending", "review_requested": True})
    rpc(ts, "deny_cobro_rejection", {"p_cobro_id": ids["d"], "p_comment": "x" * 400})
    check("comentario de más de 280 caracteres se recorta",
          len(one("payment_requests", ids["d"], "reject_reply").get("reject_reply") or "") == 280)


def main():
    snd, rcv = user_id(SENDER_EMAIL, SENDER_PASS), user_id(RECV_EMAIL, RECV_PASS)
    if not snd or not rcv:
        print("[FALLA] no se pudo asegurar las cuentas de prueba"); return 1
    cleanup()
    ok_run = True
    try:
        ids = seed(snd, rcv)
        base = serve(); time.sleep(0.5)
        session(base, RECV_EMAIL, RECV_PASS, lambda p: fase1(p, ids))
        session(base, SENDER_EMAIL, SENDER_PASS, lambda p: fase2(p, ids))
        session(base, RECV_EMAIL, RECV_PASS, lambda p: fase3(p, ids))
        session(base, SENDER_EMAIL, SENDER_PASS, lambda p: fase4(p, ids))
        seguridad(ids)
    except Exception as e:
        ok_run = False
        print(f"[FALLA] se cortó después de {len(CHECKS)} comprobaciones: {type(e).__name__}: {str(e)[:300]}")
    finally:
        cleanup()
    print("\n=== E2E Rechazar cobro + aceptar/no aceptar el rechazo (2 cuentas) ===")
    for label, v in CHECKS:
        print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    ok = ok_run and len(CHECKS) >= 30 and all(v for _, v in CHECKS)
    bad = sum(1 for _, v in CHECKS if not v)
    print("\n" + (f"OK - {len(CHECKS)} comprobaciones" if ok else f"FALLO - {bad} de {len(CHECKS)} fallaron (corrida completa: {ok_run})"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
