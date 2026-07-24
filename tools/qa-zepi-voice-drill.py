#!/usr/bin/env python3
"""
QA E2E REAL: drill del registro por voz (v188) — clics REALES en la app + BD real.

Con max@zepo.test, simulando una llamada en curso (ws de Gemini Live mockeado, TODO
lo demas es el codigo real de la app):
 1. Transcripcion tipo chat: fragmentos de entrada/salida -> 2 burbujas en lados opuestos.
 2. Tool call add_records del agente -> el panel de la llamada se aparta (.zv-away),
    aparece la pildora flotante de 2 botones pegada a la DERECHA, y sube el drill.
 3. El drill trae lo que dijo el agente: descripcion, categoria, monto, metodo de pago
    (nombre exacto del catalogo) y la division con la persona GUARDADA reconocida.
 4. Persona NO guardada -> tarjeta "¿lo agrego?"; clic REAL en "Si, agregar" la suma
    al split y reparte los porcentajes (suma 100%).
 5. Edicion REAL: cambiar categoria (chip) y monto (input) se refleja en el estado.
 6. Silenciar desde la pildora (clic REAL) corta la pista del microfono.
 7. Clic REAL en "Registrar" -> fila REAL en la BD con mi parte, is_split, split_people
    (las 2 personas) y payment_method; el drill se cierra y el chat queda con el aviso.
 8. Sin overflow horizontal en viewport de iPhone y la hoja no se sale por abajo.
 9. Cancelar (control negativo): otra propuesta + "Cancelar" -> NADA en la BD.

Deja screenshots en tools/_shots/. Limpia todo lo que siembra.
USO: python tools/qa-zepi-voice-drill.py     Sale 1 si algo falla.
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
MAX_EMAIL, PASS = "max@zepo.test", "ZepoQA2026!"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lynoia-cli/1.0"
TAG = "ZVQA"
BUD_M, BUD_Y = time.localtime().tm_mon, time.localtime().tm_year

_z = json.load(open(ZEPO_CFG, encoding="utf-8"))
_sb = _z.get("supabase", _z)
BASE = (_sb.get("url") or "").rstrip("/")
PUB = re.search(r"sb_publishable_[A-Za-z0-9_-]+", open(os.path.join(PWA, "index.html"), encoding="utf-8").read()).group(0)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def login_api():
    body = json.dumps({"email": MAX_EMAIL, "password": PASS}).encode()
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

# Llamada "en curso": el ws es lo UNICO mockeado (no hay Gemini Live en CI).
# 'Ana' queda como persona guardada sembrando un gasto dividido en memoria.
CALL_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.a7Active = false;
  window.__zvSent = [];
  window.__zvTrack = { enabled: true };
  c._zv = { ws: { readyState: 1, send: (s) => window.__zvSent.push(JSON.parse(s)) },
            sources: [], micStream: { getAudioTracks: () => [window.__zvTrack] } };
  c.expenses = [{ id: 'zvseed', user_id: c.user.id, date: '2026-07-01', category: 'food',
                  description: 'seed', amount: 10, is_income: false, is_split: true,
                  split_persona: 'Ana', split_people: [{ name: 'Ana', pct: 50, user_id: null }] }];
  c.zepiOpen = true; c.zepiVoiceOpen = true; c.zepiVoiceState = 'listening';
  c.zvTurns = []; c.zvDraft = null; c.zepiVoiceMini = false; c.zepiVoiceMuted = false;
  return c.zvPeopleOptions.map(o => o.name).join(',');
}
"""

TRANSCRIPT_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c._zvOnMessage(JSON.stringify({ serverContent: { inputTranscription: { text: 'anota 24 de la ' } } }));
  c._zvOnMessage(JSON.stringify({ serverContent: { inputTranscription: { text: 'cena con ana y pedro' } } }));
  c._zvOnMessage(JSON.stringify({ serverContent: { outputTranscription: { text: 'Listo, te lo dejo en pantalla' } } }));
  c._zvOnMessage(JSON.stringify({ serverContent: { turnComplete: true } }));
  return c.zvTurns.length;
}
"""

TOOLCALL_JS = """
async ([desc, pm]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  await c._zvToolCall([{ id: 'fc1', name: 'add_records', args: {
    items: [{ amount: 24, description: desc, category: 'Comida', date: c.form.date || undefined }],
    payment_method: pm, split_with: ['ana', 'Pedro'],
  } }]);
  return JSON.stringify(c.zvDraft);
}
"""

# set_budget por voz (F10). Devuelve tambien el espacio destino que resolvio la app.
BUDGET_TOOLCALL_JS = """
async ([amount, cat]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.toast = '';
  await c._zvToolCall([{ id: 'fcb', name: 'set_budget', args: { amount, category: cat } }]);
  return JSON.stringify({ act: c.zvAct, space: c._zepiBudgetSpace() });
}
"""

# Reproduce la causa real del fallo de Alvaro (24-jul): sin espacio resoluble, confirmar
# moria en un `false` mudo dentro de saveBudgets y el usuario solo veia "no pude".
NOSPACE_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.__bakSpaces = c.spaces; c.__bakActive = c.activeSpaceId; c.__bakAll = c.spaceViewAll;
  c.spaces = []; c.activeSpaceId = null; c.spaceViewAll = true; c.toast = '';
  return true;
}
"""

RESTORE_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.spaces = c.__bakSpaces; c.activeSpaceId = c.__bakActive; c.spaceViewAll = c.__bakAll;
  return (c.spaces || []).length;
}
"""


def main():
    print("=== QA drill de voz (clics reales + BD real) ===")
    os.makedirs(SHOTS, exist_ok=True)
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond)))
        print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

    jwt, uid = login_api()
    port = free_port(); srv = serve(port)
    created = []
    bud_before, bud_touched = None, False
    try:
        with sync_playwright() as p:
            br = p.chromium.launch()
            ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
            pg = ctx.new_page()
            pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load")
            pg.wait_for_timeout(1200)
            err = pg.evaluate(LOGIN_JS, [MAX_EMAIL, PASS])
            if err:
                print(f"FATAL: login fallo: {err}"); sys.exit(1)
            pg.wait_for_timeout(2500)

            # Regresion: el login FRESCO (sin recargar) debe cargar tambien metodos de pago,
            # presupuestos, amigos y divisiones — no solo gastos. Antes de v188 no lo hacia.
            try:
                pg.wait_for_function("() => (window.Alpine.$data(document.querySelector('#app')).paymentMethods || []).length > 0", timeout=15000)
                fresh_ok = True
            except Exception:
                fresh_ok = False
            check("0a. login fresco carga los metodos de pago (sin recargar)", fresh_ok)
            people = pg.evaluate(CALL_JS)
            check("0. 'Ana' figura como persona guardada", "Ana" in people, f"opts={people}")

            # 1) transcripcion tipo chat
            pg.evaluate(TRANSCRIPT_JS)
            pg.wait_for_selector(".zv-b", timeout=5000)
            bubbles = pg.evaluate("""() => [...document.querySelectorAll('.zv-b')].map(b => {
                const r = b.getBoundingClientRect();
                return { me: b.className.includes('zv-b-me'), left: Math.round(r.left), right: Math.round(r.right), txt: b.textContent };
            })""")
            check("1a. 2 burbujas (una por lado)", len(bubbles) == 2, f"n={len(bubbles)}")
            if len(bubbles) == 2:
                me, ze = bubbles[0], bubbles[1]
                check("1b. lo mio a la derecha, Zepi a la izquierda",
                      me["me"] and not ze["me"] and me["right"] > ze["right"] and ze["left"] < me["left"],
                      f"me={me['left']}-{me['right']} zepi={ze['left']}-{ze['right']}")
                check("1c. fragmentos unidos en una sola burbuja",
                      me["txt"] == "anota 24 de la cena con ana y pedro", f"txt={me['txt']!r}")
            pg.screenshot(path=os.path.join(SHOTS, "zv-1-chat.png"))

            # 2) el agente propone -> panel fuera, pildora, drill
            draft = json.loads(pg.evaluate(TOOLCALL_JS, [f"Cena {TAG}", "tarjeta"]))
            pg.wait_for_selector(".zv-sheet", timeout=5000)
            pg.wait_for_timeout(500)
            geo = pg.evaluate("""() => {
                const q = s => document.querySelector(s);
                const R = e => { const r = e.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), right: Math.round(r.right), bottom: Math.round(r.bottom) }; };
                const panel = q('.zv-panel'), mini = q('.zv-mini'), sheet = q('.zv-sheet');
                const ms = getComputedStyle(mini), ss = getComputedStyle(sheet);
                return { away: panel.className.includes('zv-away'), panelOpacity: getComputedStyle(panel).opacity,
                         mini: { ...R(mini), btns: mini.querySelectorAll('button').length, opacity: ms.opacity, display: ms.display },
                         sheet: { ...R(sheet), opacity: ss.opacity },
                         vw: innerWidth, vh: innerHeight, scrollW: document.documentElement.scrollWidth };
            }""")
            check("2a. el panel de la llamada se aparta", geo["away"] and float(geo["panelOpacity"]) < 0.05, f"{geo['away']} op={geo['panelOpacity']}")
            check("2b. pildora visible con 2 botones",
                  geo["mini"]["btns"] == 2 and geo["mini"]["display"] != "none" and float(geo["mini"]["opacity"]) > 0.9, f"mini={geo['mini']}")
            check("2c. pildora pegada al borde derecho",
                  geo["vw"] - geo["mini"]["right"] <= 14 and geo["mini"]["x"] > geo["vw"] * 0.6, f"vw={geo['vw']} right={geo['mini']['right']}")
            check("2d. el drill sube y es visible", float(geo["sheet"]["opacity"]) > 0.9 and geo["sheet"]["h"] > 200, f"sheet={geo['sheet']}")
            check("2e. la pildora NO tapa el contenido del drill",
                  geo["mini"]["bottom"] <= geo["sheet"]["y"], f"pildora hasta y={geo['mini']['bottom']}, hoja desde y={geo['sheet']['y']}")
            check("8a. la hoja NO se sale por abajo", geo["sheet"]["bottom"] <= geo["vh"] + 1, f"bottom={geo['sheet']['bottom']} vh={geo['vh']}")
            check("8b. sin overflow horizontal", geo["scrollW"] <= geo["vw"], f"scrollW={geo['scrollW']} vw={geo['vw']}")
            pg.screenshot(path=os.path.join(SHOTS, "zv-2-drill.png"))

            # 3) contenido propuesto
            it = (draft or {}).get("items", [{}])[0]
            check("3a. descripcion y monto del agente", it.get("description") == f"Cena {TAG}" and float(it.get("amount")) == 24.0, f"it={it}")
            check("3b. categoria mapeada ('Comida' -> food)", it.get("category") == "food", f"cat={it.get('category')}")
            check("3c. metodo de pago con el nombre EXACTO del catalogo", draft.get("payment_method") == "Tarjeta", f"pm={draft.get('payment_method')}")
            names = [p["name"] for p in draft.get("people", [])]
            check("3d. reconocio a la persona guardada ('ana' -> 'Ana')", names == ["Tú", "Ana"], f"people={names}")
            check("4a. la persona desconocida va a la tarjeta de pregunta", draft.get("unknown") == ["Pedro"], f"unknown={draft.get('unknown')}")

            # 4) clic REAL en "Si, agregar"
            pg.click(".zv-ask .zv-chip.on")
            pg.wait_for_timeout(400)
            after = pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
                return { people: c.zvDraft.people.map(p => p.name + '=' + p.pct), sum: c.zvSplitSum, ok: c.zvSplitOk,
                         unknown: c.zvDraft.unknown, ask: !!document.querySelector('.zv-ask') }; }""")
            check("4b. 'Si, agregar' suma a Pedro al split",
                  [n.split("=")[0] for n in after["people"]] == ["Tú", "Ana", "Pedro"], f"{after['people']}")
            check("4c. reparte y la suma queda en 100%", after["ok"] and abs(after["sum"] - 100) < 0.005, f"sum={after['sum']}")
            check("4d. la tarjeta de pregunta desaparece", not after["ask"] and not after["unknown"], f"ask={after['ask']}")

            # 5) edicion REAL (categoria por chip + monto por input)
            # ojo: el <template> de Alpine cuenta como hijo -> seleccionar por TEXTO, no por posicion
            pg.click(".zv-item .zv-chips .zv-chip:has-text('Transporte')")
            amt = pg.query_selector(".zv-amt input")
            amt.fill("30")
            amt.dispatch_event("input")
            pg.wait_for_timeout(300)
            edited = pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
                return { cat: c.zvDraft.items[0].category, amount: c.zvDraft.items[0].amount, valid: c.zvDraftValid }; }""")
            check("5a. cambiar la categoria por chip", edited["cat"] == "transport", f"cat={edited['cat']}")
            check("5b. editar el monto a mano", float(edited["amount"]) == 30.0 and edited["valid"], f"amount={edited['amount']}")

            # 5c) editar NO debe inflar el historial (watcher profundo = 1 entrada por tecla,
            # y entonces cerrar con el gesto atras pedia N toques)
            hist = pg.evaluate("""async () => {
                const c = window.Alpine.$data(document.querySelector('#app'));
                const before = history.length;
                for (let i = 0; i < 10; i++) { c.zvDraft.items[0].amount = 30 + i; await new Promise(r => setTimeout(r, 40)); }
                await new Promise(r => setTimeout(r, 300));
                c.zvDraft.items[0].amount = 30;
                return { before, after: history.length };
            }""")
            check("5c. editar no infla el historial (gesto atras sano)",
                  hist["after"] - hist["before"] == 0, f"+{hist['after'] - hist['before']} entradas por 10 ediciones")
            # y el gesto atras cierra el drill de UNA
            pg.go_back()
            pg.wait_for_timeout(700)
            back = pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
                return { draft: !!c.zvDraft, call: c.zepiVoiceOpen, mini: c.zepiVoiceMini }; }""")
            check("5d. un 'atras' cierra el drill y deja viva la llamada",
                  not back["draft"] and back["call"] and not back["mini"], f"{back}")
            # reabrir para seguir con el flujo de guardado
            pg.evaluate(TOOLCALL_JS, [f"Cena {TAG}", "tarjeta"])
            pg.wait_for_selector(".zv-sheet", timeout=5000)
            pg.wait_for_timeout(400)
            pg.click(".zv-ask .zv-chip.on")
            pg.click(".zv-item .zv-chips .zv-chip:has-text('Transporte')")
            amt2 = pg.query_selector(".zv-amt input"); amt2.fill("30"); amt2.dispatch_event("input")
            pg.wait_for_timeout(300)

            # 6) silenciar desde la pildora (clic REAL)
            pg.click(".zv-mini .zv-mini-mute")
            pg.wait_for_timeout(300)
            muted = pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
                return { muted: c.zepiVoiceMuted, track: window.__zvTrack.enabled,
                         on: document.querySelector('.zv-mini .zv-mini-mute').className.includes('on') }; }""")
            check("6. silenciar corta la pista del microfono", muted["muted"] and muted["track"] is False and muted["on"], f"{muted}")
            pg.click(".zv-mini .zv-mini-mute")  # volver a activar
            pg.wait_for_timeout(200)
            pg.screenshot(path=os.path.join(SHOTS, "zv-3-editado.png"))

            # 7) clic REAL en Registrar -> BD
            before = rest(jwt, f"expenses?user_id=eq.{uid}&description=eq.Cena%20{TAG}&select=id")
            pg.click(".zv-sheet-btns .zepi-card-go")
            pg.wait_for_timeout(3500)
            rows = rest(jwt, f"expenses?user_id=eq.{uid}&description=eq.Cena%20{TAG}&select=*")
            created += [r["id"] for r in rows if isinstance(r, dict) and r.get("id")]
            check("7a. quedo UNA fila nueva en la BD", isinstance(rows, list) and len(rows) == len(before) + 1, f"rows={len(rows) if isinstance(rows, list) else rows}")
            if isinstance(rows, list) and rows:
                r = rows[-1]
                sp = r.get("split_people") or []
                spn = sorted([str(x.get("name")) for x in sp]) if isinstance(sp, list) else []
                check("7b. guarda MI parte (30 / 3 personas = 10)", abs(float(r.get("amount", 0)) - 10.0) < 0.02, f"amount={r.get('amount')} pct={r.get('split_pct')}")
                check("7c. marcado como dividido con total 30", r.get("is_split") is True and abs(float(r.get("split_total") or 0) - 30.0) < 0.02, f"is_split={r.get('is_split')} total={r.get('split_total')}")
                check("7d. split_people = las 2 personas", spn == ["Ana", "Pedro"], f"split_people={spn}")
                check("7e. metodo de pago persistido", r.get("payment_method") == "Tarjeta", f"pm={r.get('payment_method')}")
                check("7f. categoria editada persistida", r.get("category") == "transport", f"cat={r.get('category')}")
            ui = pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
                return { draft: !!c.zvDraft, mini: c.zepiVoiceMini, away: !!document.querySelector('.zv-panel.zv-away'),
                         lastMsg: (c.zepiMsgs[c.zepiMsgs.length - 1] || {}).text || '',
                         notified: (window.__zvSent.filter(m => m.clientContent) || []).length }; }""")
            check("7g. el drill se cierra y vuelve la llamada", not ui["draft"] and not ui["mini"] and not ui["away"], f"{ui}")
            check("7h. avisa en el chat y al agente", "Registrado desde la llamada" in ui["lastMsg"] and ui["notified"] >= 1, f"msg={ui['lastMsg'][:60]!r} notif={ui['notified']}")
            pg.screenshot(path=os.path.join(SHOTS, "zv-4-guardado.png"))

            # 9) control negativo: cancelar NO guarda
            pg.evaluate(TOOLCALL_JS, [f"Cancelado {TAG}", "efectivo"])
            pg.wait_for_selector(".zv-sheet", timeout=5000)
            pg.wait_for_timeout(400)
            pg.click(".zv-sheet-btns .zepi-card-no")
            pg.wait_for_timeout(1500)
            gone = rest(jwt, f"expenses?user_id=eq.{uid}&description=eq.Cancelado%20{TAG}&select=id")
            state = pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
                return { draft: !!c.zvDraft, mini: c.zepiVoiceMini }; }""")
            check("9a. cancelar NO escribe en la BD", isinstance(gone, list) and len(gone) == 0, f"filas={gone}")
            check("9b. cancelar cierra el drill y restaura la llamada", not state["draft"] and not state["mini"], f"{state}")

            # 10) presupuesto por voz (F10): tool call -> tarjeta -> clic REAL -> fila en budgets.
            #     Se respalda el mes entero porque saveBudgets borra y reinserta.
            bud_before = rest(jwt, f"budgets?user_id=eq.{uid}&month=eq.{BUD_M}&year=eq.{BUD_Y}&select=*")
            bud_touched = isinstance(bud_before, list)
            info = json.loads(pg.evaluate(BUDGET_TOOLCALL_JS, [317, "Ahorro"]))
            pg.wait_for_selector(".zv-sheet", timeout=5000)
            pg.wait_for_timeout(400)
            space = info.get("space")
            check("10a. la tarjeta abre con la categoria mapeada ('Ahorro' -> savings)",
                  (info.get("act") or {}).get("category") == "savings" and (info.get("act") or {}).get("amount") == 317,
                  f"act={info.get('act')}")
            check("10b. resolvio un espacio destino", bool(space), f"space={space}")
            pg.screenshot(path=os.path.join(SHOTS, "zv-5-presupuesto.png"))
            pg.click(".zv-sheet-btns .zepi-card-go")
            pg.wait_for_timeout(3500)
            bud_after = rest(jwt, f"budgets?user_id=eq.{uid}&month=eq.{BUD_M}&year=eq.{BUD_Y}&select=*")
            saved = [b for b in bud_after if isinstance(b, dict) and b.get("category") == "savings"
                     and abs(float(b.get("amount") or 0) - 317.0) < 0.01] if isinstance(bud_after, list) else []
            check("10c. quedo el presupuesto de ahorro en la BD", len(saved) == 1, f"filas savings=317: {len(saved)} / total={len(bud_after) if isinstance(bud_after, list) else bud_after}")
            prev_cats = {b.get("category") for b in bud_before if isinstance(b, dict) and b.get("category") and b.get("space_id") == space} if isinstance(bud_before, list) else set()
            now_cats = {b.get("category") for b in bud_after if isinstance(b, dict) and b.get("category") and b.get("space_id") == space} if isinstance(bud_after, list) else set()
            check("10d. NO borro las otras categorias del mes", prev_cats.issubset(now_cats), f"antes={sorted(prev_cats)} ahora={sorted(now_cats)}")
            ui2 = pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
                return { act: !!c.zvAct, mini: c.zepiVoiceMini, toast: c.toast,
                         lastMsg: (c.zepiMsgs[c.zepiMsgs.length - 1] || {}).text || '' }; }""")
            check("10e. la tarjeta se cierra y avisa en el chat", not ui2["act"] and not ui2["mini"] and "Presupuesto" in ui2["lastMsg"],
                  f"act={ui2['act']} mini={ui2['mini']} msg={ui2['lastMsg'][:70]!r} toast={ui2['toast']!r}")

            # 11) control negativo (la causa real del bug): sin espacio resoluble NO escribe
            #     y el mensaje DICE por que, en vez del "no pude" mudo de antes.
            pg.evaluate(NOSPACE_JS)
            pg.evaluate(BUDGET_TOOLCALL_JS, [999, "Comida"])
            pg.wait_for_selector(".zv-sheet", timeout=5000)
            pg.wait_for_timeout(300)
            pg.click(".zv-sheet-btns .zepi-card-go")
            pg.wait_for_timeout(2000)
            bud_neg = rest(jwt, f"budgets?user_id=eq.{uid}&month=eq.{BUD_M}&year=eq.{BUD_Y}&select=category,amount")
            bad = [b for b in bud_neg if isinstance(b, dict) and abs(float(b.get("amount") or 0) - 999.0) < 0.01] if isinstance(bud_neg, list) else []
            neg = pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app')); return c.toast || ''; }""")
            check("11a. sin espacio NO escribe en la BD", len(bad) == 0, f"filas 999: {len(bad)}")
            check("11b. el aviso dice el motivo (no el 'no pude' mudo)", "espacio" in neg.lower(), f"toast={neg!r}")
            pg.evaluate(RESTORE_JS)

            ctx.close(); br.close()
    finally:
        for eid in created:
            rest(jwt, f"payment_requests?expense_id=eq.{eid}", method="DELETE")
            rest(jwt, f"expenses?id=eq.{eid}", method="DELETE")
        # Los presupuestos del mes se borran y reinsertan al guardar: se deja el mes como estaba.
        if bud_touched:
            rest(jwt, f"budgets?user_id=eq.{uid}&month=eq.{BUD_M}&year=eq.{BUD_Y}", method="DELETE")
            back = [{k: v for k, v in b.items() if k not in ("id", "created_at")}
                    for b in (bud_before or []) if isinstance(b, dict)]
            if back:
                rest(jwt, "budgets", method="POST", payload=back)
            print(f"  presupuestos del mes restaurados: {len(back)} filas")
        srv.shutdown()

    left = rest(jwt, f"expenses?user_id=eq.{uid}&description=like.*{TAG}*&select=id")
    print(f"  limpieza: {len(created)} borradas, quedan {len(left) if isinstance(left, list) else '?'}")
    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} PASS   (screenshots en tools/_shots/)")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}")
        sys.exit(1)
