#!/usr/bin/env python3
"""
QA E2E REAL: los 5 verbos que la voz de Zepi NO tenia (v199) — clics reales + BD real.

Con max@zepo.test y el ws de Gemini Live mockeado (todo lo demas es el codigo real):
 1. Las 9 herramientas declaradas son las esperadas y delete_record NO esta: borrar por
    voz quedo fuera a proposito (irreversible + hablando no hay forma segura de saber cual).
 2. Fail-closed: un token alucinado (r99), un uuid crudo y un patch vacio NO abren tarjeta,
    devuelven error al modelo.
 3. El mapa de tokens de la llamada esta CONGELADO: escribir en el chat a media llamada
    regenera _zepiRefMap, y aun asi el r# de la voz sigue apuntando al mismo registro.
 4. edit_record: tarjeta con antes -> despues, clic REAL en "Guardar cambio", el cambio
    queda EN LA BD y el chat se entera con la marca de llamada.
 5. mark_paid: tarjeta con persona y monto, clic REAL, split_status queda 'cobrado' en BD.
 6. accept_cobro: una deuda que TE cobraron resuelve (antes era un verbo muerto: el
    snapshot nunca le daba token) — y cruzar los tipos c# esta prohibido en ambos sentidos.
    OJO: aqui NO se verifica la escritura de accept_cobro (necesita 2 cuentas; esa parte la
    cubren las suites de cobros). Se verifica que resuelve, que pinta y que no se cruza.
 7. remind_whatsapp: avisa que cerrara la llamada, y al confirmar la CIERRA y abre wa.me.
 8. set_goal: monto editable a mano, clic REAL, la meta queda en zepi_goals con lo editado.
 9. Cancelar no escribe nada y le nombra a Zepi el verbo correcto.
10. Sin overflow horizontal a 390px con la tarjeta arriba.

Deja screenshots en tools/_shots/voz-verbos-*.png. Limpia todo lo que siembra.
USO: python tools/qa-zepi-voz-verbos.py     Sale 1 si algo falla.
"""
import functools
import http.server
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
except Exception:
    pass

TOOLS = os.path.dirname(os.path.abspath(__file__))
PWA = os.path.dirname(TOOLS)
SHOTS = os.path.join(TOOLS, "_shots")
ZEPO_CFG = "C:/Users/alvar/lynoia/clients/zepo/config.json"
EMAIL, PASS = "max@zepo.test", "ZepoQA2026!"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lynoia-cli/1.0"
TAG = "ZVVERB"
TODAY = time.strftime("%Y-%m-%d")

_z = json.load(open(ZEPO_CFG, encoding="utf-8"))
_sb = _z.get("supabase", _z)
BASE = (_sb.get("url") or "").rstrip("/")
PUB = re.search(r"sb_publishable_[A-Za-z0-9_-]+", open(os.path.join(PWA, "index.html"), encoding="utf-8").read()).group(0)

EXPECTED_TOOLS = ["query_records", "add_records", "set_budget", "split_handoff",
                  "edit_record", "mark_paid", "accept_cobro", "remind_whatsapp", "set_goal"]


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def login_api():
    body = json.dumps({"email": EMAIL, "password": PASS}).encode()
    r = urllib.request.Request(f"{BASE}/auth/v1/token?grant_type=password", data=body, method="POST",
                               headers={"apikey": PUB, "Content-Type": "application/json", "User-Agent": UA})
    j = json.loads(urllib.request.urlopen(r, timeout=30).read().decode())
    return j["access_token"], j["user"]["id"]


def rest(jwt, path, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(f"{BASE}/rest/v1/{path}", data=data, method=method,
                               headers={"apikey": PUB, "Authorization": f"Bearer {jwt}",
                                        "Content-Type": "application/json", "User-Agent": UA,
                                        "Prefer": "return=representation"})
    try:
        raw = urllib.request.urlopen(r, timeout=30).read().decode()
        return json.loads(raw) if raw.strip() else []
    except urllib.error.HTTPError as e:
        return {"_err": e.code, "_body": e.read().decode()[:300]}


LOGIN_JS = """
async ([email, password]) => {
  try { localStorage.setItem('zepo_a7_done_v1', '1'); } catch (e) {}
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode = 'login'; c.authEmail = email; c.authPassword = password;
  await c.handleAuth(); return c.authError || '';
}
"""

# Llamada "en curso": el ws es lo UNICO mockeado. _zvSetup() congela el mapa de tokens.
CALL_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.a7Active = false;
  window.__zvSent = []; window.__wa = null;
  window.open = (u) => { window.__wa = u; return null; };
  c._zv = { ws: { readyState: 1, send: (s) => window.__zvSent.push(JSON.parse(s)) },
            sources: [], micStream: { getAudioTracks: () => [] } };
  c.zepiOpen = true; c.zepiVoiceOpen = true; c.zepiVoiceState = 'listening';
  c.zvTurns = []; c.zvDraft = null; c.zvAct = null; c.zepiVoiceMini = false;
  const setup = c._zvSetup();
  const snap = JSON.parse(setup.setup.systemInstruction.parts[0].text.split('SNAPSHOT=')[1]);
  return JSON.stringify({
    tools: setup.setup.tools[0].functionDeclarations.map(f => f.name),
    refMap: c._zvRefMap, recent: snap.recentRecords || [], cobros: snap.cobros || [],
    sys: setup.setup.systemInstruction.parts[0].text.slice(0, 4000),
  });
}
"""

TOOL_JS = """
async ([name, args]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  window.__zvSent = [];
  await c._zvToolCall([{ id: 'fc', name, args }]);
  const last = window.__zvSent[window.__zvSent.length - 1] || {};
  const resp = (((last.toolResponse || {}).functionResponses || [])[0] || {}).response || {};
  return JSON.stringify({ resp: resp.result, act: c.zvAct ? { kind: c.zvAct.kind, it: c.zvAct.it } : null,
                          mini: c.zepiVoiceMini, valid: c.zvActValid });
}
"""

# Un gasto NUEVO desplaza toda la numeracion r# del snapshot (r1 pasa a ser r2...).
# Es exactamente lo que pasa si escribes en el chat a media llamada.
SHIFT_MAP_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const before = JSON.stringify(c._zvRefMap);
  c.expenses = [{ id: 'intruso-1', user_id: c.user.id, date: '2099-01-01', category: 'food',
                  description: 'intruso', amount: 1, is_income: false }, ...c.expenses];
  c._zepiSnapshot();
  return JSON.stringify({ frozen: c._zvRefMap, live: c._zepiRefMap,
                          same: before === JSON.stringify(c._zvRefMap),
                          moved: c._zepiRefMap.r1 === 'intruso-1' });
}
"""


def main():
    print("=== QA verbos de voz de Zepi (clics reales + BD real) ===")
    os.makedirs(SHOTS, exist_ok=True)
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond)))
        print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

    jwt, uid = login_api()
    # Siembra ANTES de abrir el navegador: la app los carga sola, como datos de verdad.
    # Uno por uno: PostgREST exige que un lote traiga EXACTAMENTE las mismas claves.
    seeded = []
    for row in ({"user_id": uid, "amount": 12.5, "category": "food", "description": f"{TAG} editar",
                 "date": TODAY, "is_income": False},
                {"user_id": uid, "amount": 15, "category": "food", "description": f"{TAG} cobro",
                 "date": TODAY, "is_income": False, "is_split": True, "split_total": 30, "split_pct": 50,
                 "split_persona": "Ana", "split_pending": 15, "split_status": "pendiente",
                 "split_people": [{"name": "Ana", "pct": 50, "user_id": None}]}):
        got = rest(jwt, "expenses", "POST", row)
        if isinstance(got, dict) or not got:
            print(f"FATAL: no pude sembrar: {got}"); sys.exit(1)
        seeded.append(got[0])
    ids = {r["description"]: r["id"] for r in seeded}
    edit_id, cobro_id = ids[f"{TAG} editar"], ids[f"{TAG} cobro"]
    port = free_port(); srv = serve(port)
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load")
            pg.wait_for_timeout(1200)
            err = pg.evaluate(LOGIN_JS, [EMAIL, PASS])
            if err:
                print(f"FATAL: login fallo: {err}"); sys.exit(1)
            pg.wait_for_timeout(2500)
            pg.wait_for_function("() => (window.Alpine.$data(document.querySelector('#app')).expenses || []).length > 0", timeout=15000)

            st = json.loads(pg.evaluate(CALL_JS))
            tools, refmap = st["tools"], st["refMap"]

            # 1) superficie declarada
            check("1a. las 9 herramientas de voz estan declaradas", sorted(tools) == sorted(EXPECTED_TOOLS), f"tools={tools}")
            check("1b. delete_record NO se declara por voz", "delete_record" not in tools)
            check("1c. el prompt dice que borrar por voz no se puede", "BORRAR NO SE PUEDE POR VOZ" in st["sys"])
            r = json.loads(pg.evaluate(TOOL_JS, ["delete_record", {"id": "r1"}]))
            check("1d. si el modelo lo intenta igual, no hay herramienta", (r["resp"] or {}).get("error") == "unknown_tool" and r["act"] is None)

            # El gasto dividido sale en las DOS listas (es un gasto y es un cobro): para
            # marcarlo pagado hace falta su token c#, no el r# que tambien tiene.
            tok_edit = next((k for k, v in refmap.items() if v == edit_id and k[0] == "r"), None)
            tok_cobro = next((k for k, v in refmap.items() if v == cobro_id and k[0] == "c"), None)
            check("1e. el gasto sembrado tiene token r#", bool(tok_edit), f"refMap={refmap}")
            check("1f. el cobro sembrado tiene token c#", bool(tok_cobro), f"cobros={st['cobros']}")
            if not (tok_edit and tok_cobro):
                print("\nFATAL: sin tokens no hay nada que probar"); sys.exit(1)

            # 2) fail-closed
            for label, args in [("token alucinado (r99)", {"id": "r99", "patch": {"amount": 5}}),
                                ("uuid crudo", {"id": edit_id, "patch": {"amount": 5}}),
                                ("patch vacio", {"id": tok_edit, "patch": {}}),
                                ("patch que no cambia nada", {"id": tok_edit, "patch": {"amount": 12.5}})]:
                r = json.loads(pg.evaluate(TOOL_JS, ["edit_record", args]))
                check(f"2. {label} NO abre tarjeta", r["act"] is None and bool((r["resp"] or {}).get("error")),
                      f"resp={r['resp']}")

            # 3) mapa congelado
            sh = json.loads(pg.evaluate(SHIFT_MAP_JS))
            check("3a. el mapa de la llamada no se movio", sh["same"] is True)
            check("3b. el del chat SI se corrio (control negativo)", sh["moved"] is True and sh["live"] != sh["frozen"],
                  f"live.r1={sh['live'].get('r1')}")
            r = json.loads(pg.evaluate(TOOL_JS, ["edit_record", {"id": tok_edit, "patch": {"amount": 19.9, "category": "Transporte"}}]))
            check("3c. el r# de la voz sigue apuntando al MISMO gasto",
                  bool(r["act"]) and r["act"]["it"]["_before"]["id"] == edit_id, f"resp={r['resp']}")

            # 4) edit_record de punta a punta
            pg.wait_for_selector(".zv-sheet", timeout=5000)
            card = pg.evaluate("""() => {
              const s = document.querySelector('.zv-sheet');
              const btn = [...s.querySelectorAll('button')].find(b => /Guardar cambio/.test(b.textContent));
              return { txt: s.innerText, btn: !!btn, w: document.documentElement.scrollWidth };
            }""")
            check("4a. la tarjeta pregunta por el cambio", "¿Aplico este cambio?" in card["txt"], card["txt"][:120])
            check("4b. muestra el antes y el despues", "12.50" in card["txt"] and "19.90" in card["txt"], card["txt"][:200])
            check("4c. el boton dice 'Guardar cambio'", card["btn"] is True)
            check("4d. sin overflow horizontal a 390px", card["w"] <= 390, f"scrollWidth={card['w']}")
            pg.screenshot(path=os.path.join(SHOTS, "voz-verbos-editar.png"))
            pg.evaluate("""() => [...document.querySelectorAll('.zv-sheet button')].find(b => /Guardar cambio/.test(b.textContent)).click()""")
            pg.wait_for_timeout(3500)
            row = rest(jwt, f"expenses?id=eq.{edit_id}&select=amount,category")
            check("4e. el cambio quedo EN LA BD", isinstance(row, list) and row and float(row[0]["amount"]) == 19.9
                  and row[0]["category"] == "transport", f"row={row}")
            after = pg.evaluate("""() => {
              const c = window.Alpine.$data(document.querySelector('#app'));
              const last = (c.zepiMsgs || []).slice(-1)[0] || {};
              const sys = (window.__zvSent || []).map(s => JSON.stringify(s)).join(' ');
              return { act: !!c.zvAct, msg: last.text || '', sys };
            }""")
            check("4f. la tarjeta se cierra sola", after["act"] is False)
            check("4g. queda escrito en el chat con la marca de llamada", after["msg"].startswith("🎙"), after["msg"][:80])
            check("4h. y se lo dice a Zepi", "El usuario confirmó" in after["sys"])

            # 5) mark_paid
            r = json.loads(pg.evaluate(TOOL_JS, ["mark_paid", {"id": tok_cobro}]))
            check("5a. la tarjeta del cobro abre", bool(r["act"]) and r["act"]["kind"] == "mark_paid", f"resp={r['resp']}")
            txt = pg.evaluate("() => (document.querySelector('.zv-sheet') || {}).innerText || ''")
            check("5b. dice quien te pago y cuanto", "Ana" in txt and "15.00" in txt, txt[:140])
            pg.screenshot(path=os.path.join(SHOTS, "voz-verbos-cobro.png"))
            pg.evaluate("""() => [...document.querySelectorAll('.zv-sheet button')].find(b => /Marcar pagado/.test(b.textContent)).click()""")
            pg.wait_for_timeout(3500)
            row = rest(jwt, f"expenses?id=eq.{cobro_id}&select=split_status,split_pending")
            check("5c. el cobro quedo saldado en la BD", isinstance(row, list) and row
                  and row[0]["split_status"] == "cobrado" and float(row[0]["split_pending"] or 0) == 0, f"row={row}")

            # 6) accept_cobro + cruce de tipos prohibido
            deuda = pg.evaluate("""() => {
              const c = window.Alpine.$data(document.querySelector('#app'));
              c.payReqs = [{ id: '00000000-0000-4000-8000-0000000000ab', status: 'pending',
                             from_name: 'Bruno', amount: 9, created_at: new Date().toISOString() }];
              c._zvSetup();
              const t = Object.keys(c._zvRefMap).find(k => c._zvRefMap[k] === '00000000-0000-4000-8000-0000000000ab');
              const pend = Object.keys(c._zvRefMap).find(k => k[0] === 'c' && k !== t);
              return JSON.stringify({ t, pend });
            }""")
            deuda = json.loads(deuda)
            check("6a. la deuda que te cobraron YA tiene token c#", bool(deuda["t"]), f"map={deuda}")
            if deuda["t"]:
                r = json.loads(pg.evaluate(TOOL_JS, ["accept_cobro", {"id": deuda["t"]}]))
                check("6b. accept_cobro resuelve y pinta la tarjeta", bool(r["act"]) and r["act"]["kind"] == "accept_cobro", f"resp={r['resp']}")
                txt = pg.evaluate("() => (document.querySelector('.zv-sheet') || {}).innerText || ''")
                check("6c. la tarjeta nombra al acreedor y el monto", "Bruno" in txt and "9.00" in txt, txt[:140])
                pg.evaluate("() => window.Alpine.$data(document.querySelector('#app')).zvActCancel()")
                r = json.loads(pg.evaluate(TOOL_JS, ["mark_paid", {"id": deuda["t"]}]))
                check("6d. marcar pagada una deuda TUYA esta prohibido", r["act"] is None and bool((r["resp"] or {}).get("error")), f"resp={r['resp']}")
            if deuda["pend"]:
                r = json.loads(pg.evaluate(TOOL_JS, ["accept_cobro", {"id": deuda["pend"]}]))
                check("6e. aceptar un cobro que te deben A TI esta prohibido", r["act"] is None and bool((r["resp"] or {}).get("error")), f"resp={r['resp']}")

            # 7) remind_whatsapp
            wa_tok = pg.evaluate("""() => {
              const c = window.Alpine.$data(document.querySelector('#app'));
              c.pendingSplits = [{ id: 'wa-1', is_income: false, is_split: true, split_status: 'pendiente',
                                   split_pending: 7, split_persona: 'Ana', description: 'cena', date: '%s' }];
              c._zvSetup();
              return Object.keys(c._zvRefMap).find(k => c._zvRefMap[k] === 'wa-1') || '';
            }""" % TODAY)
            check("7a. el cobro pendiente tiene token", bool(wa_tok))
            if wa_tok:
                r = json.loads(pg.evaluate(TOOL_JS, ["remind_whatsapp", {"id": wa_tok}]))
                check("7b. la tarjeta abre y avisa que cerrara la llamada",
                      bool(r["act"]) and "call ENDS" in str((r["resp"] or {}).get("note", "")), f"resp={r['resp']}")
                txt = pg.evaluate("() => (document.querySelector('.zv-sheet') || {}).innerText || ''")
                check("7c. y se lo dice tambien en pantalla", "se cierra la llamada" in txt, txt[:160])
                pg.evaluate("""() => [...document.querySelectorAll('.zv-sheet button')].find(b => /Enviar recordatorio/.test(b.textContent)).click()""")
                pg.wait_for_timeout(1200)
                out = pg.evaluate("""() => {
                  const c = window.Alpine.$data(document.querySelector('#app'));
                  return { wa: window.__wa || '', open: c.zepiVoiceOpen, act: !!c.zvAct };
                }""")
                check("7d. abre WhatsApp con el recordatorio", "wa.me" in out["wa"] and "Ana" in out["wa"], out["wa"][:90])
                check("7e. y cuelga la llamada (no la deja zombi)", out["open"] is False and out["act"] is False)

            # 8) set_goal con monto editado a mano
            pg.evaluate("""() => {
              const c = window.Alpine.$data(document.querySelector('#app'));
              c.zepiVoiceOpen = true; c.zepiVoiceState = 'listening';
              c._zv = { ws: { readyState: 1, send: (s) => window.__zvSent.push(JSON.parse(s)) }, sources: [], micStream: { getAudioTracks: () => [] } };
            }""")
            r = json.loads(pg.evaluate(TOOL_JS, ["set_goal", {"goal_kind": "save", "title": f"{TAG} viaje", "target_amount": 500}]))
            check("8a. la tarjeta de meta abre", bool(r["act"]) and r["act"]["kind"] == "set_goal", f"resp={r['resp']}")
            inp = pg.query_selector(".zv-sheet .zv-amt input")
            check("8b. el monto es editable a mano", inp is not None)
            if inp:
                inp.fill("640")
                pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(SHOTS, "voz-verbos-meta.png"))
            pg.evaluate("""() => [...document.querySelectorAll('.zv-sheet button')].find(b => /Crear meta/.test(b.textContent)).click()""")
            pg.wait_for_timeout(3500)
            goals = rest(jwt, f"zepi_goals?user_id=eq.{uid}&title=eq.{TAG}%20viaje&select=id,target_amount,kind")
            check("8c. la meta quedo en la BD con lo EDITADO (640, no 500)",
                  isinstance(goals, list) and goals and float(goals[0]["target_amount"]) == 640, f"goals={goals}")

            # 9) cancelar no escribe y nombra el verbo
            r = json.loads(pg.evaluate(TOOL_JS, ["set_goal", {"goal_kind": "limit", "title": f"{TAG} nope", "target_amount": 100}]))
            pg.evaluate("""() => { window.__zvSent = []; window.Alpine.$data(document.querySelector('#app')).zvActCancel(); }""")
            pg.wait_for_timeout(400)
            out = pg.evaluate("""() => {
              const c = window.Alpine.$data(document.querySelector('#app'));
              return { act: !!c.zvAct, sys: (window.__zvSent || []).map(s => JSON.stringify(s)).join(' ') };
            }""")
            check("9a. cancelar cierra la tarjeta", out["act"] is False)
            check("9b. y le dice a Zepi que fue 'esa meta'", "esa meta" in out["sys"], out["sys"][:160])
            nope = rest(jwt, f"zepi_goals?user_id=eq.{uid}&title=eq.{TAG}%20nope&select=id")
            check("9c. cancelar NO escribio nada", isinstance(nope, list) and len(nope) == 0, f"nope={nope}")

            br.close()
    finally:
        srv.shutdown()
        for eid in (edit_id, cobro_id):
            rest(jwt, f"expenses?id=eq.{eid}", "DELETE")
        gone = rest(jwt, f"zepi_goals?user_id=eq.{uid}&title=like.{TAG}%25", "DELETE")
        print(f"  limpieza: 2 gastos y {len(gone) if isinstance(gone, list) else '?'} metas borradas")

    ok = sum(1 for _, c in results if c)
    print(f"\n{ok}/{len(results)} PASS   (screenshots en tools/_shots/voz-verbos-*.png)")
    if ok != len(results):
        print("FALLAN: " + ", ".join(n for n, c in results if not c))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
