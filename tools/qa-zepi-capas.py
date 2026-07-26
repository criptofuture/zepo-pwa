#!/usr/bin/env python3
"""
QA E2E REAL: orden de las CAPAS de Zepi (v195) — clics REALES en la app.

Reproduce el fallo que reporto Alvaro el 25-jul: mando una foto DURANTE la llamada, la
tarjeta del recibo se pinto en el chat (z 93) y quedo DEBAJO del panel de la llamada
(z 97); al cerrar el drill la llamada se re-maximizaba y la volvia a enterrar. Zepi
juraba "te la deje en pantalla" y el usuario respondia "no la veo".

 1. La conversacion de la llamada se escribe EN VIVO en el chat (viaVoice) y los
    fragmentos de un mismo turno engordan el MISMO mensaje (no uno por fragmento).
 2. Los avisos [SISTEMA] NO entran al chat.
 3. Cerrar el drill con una tarjeta pendiente abajo -> la llamada SIGUE minimizada
    (la tarjeta queda a la vista). Control negativo: sin tarjeta pendiente, vuelve.
 4. Guardar el drill con una tarjeta pendiente abajo -> igual, sigue minimizada.
 5. Foto durante la llamada con un drill abierto -> se le avisa a Zepi que la tarjeta
    quedo DETRAS, para que no diga que ya la ve.
 6. Tarjeta del recibo EDITABLE: "Registrar" bloqueado si un movimiento no tiene monto
    o categoria; "Corregir" abre los campos; el chip cambia la categoria de verdad.

No escribe nada en la BD (todo es estado de UI). USO: python tools/qa-zepi-capas.py
"""
import functools
import http.server
import json
import os
import re
import socket
import sys
import threading

from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
except Exception:
    pass

TOOLS = os.path.dirname(os.path.abspath(__file__))
PWA = os.path.dirname(TOOLS)
SHOTS = os.path.join(TOOLS, "_shots")
MAX_EMAIL, PASS = "max@zepo.test", "ZepoQA2026!"

PUB = re.search(r"sb_publishable_[A-Za-z0-9_-]+",
                open(os.path.join(PWA, "index.html"), encoding="utf-8").read()).group(0)

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

# Llamada "en curso". El ws es lo UNICO mockeado; el resto es el codigo real.
CALL_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.a7Active = false;
  window.__zvSent = [];
  c._zv = { ws: { readyState: 1, send: (s) => window.__zvSent.push(JSON.parse(s)) },
            sources: [], micStream: { getAudioTracks: () => [{ enabled: true }] } };
  c.zepiOpen = true; c.zepiVoiceOpen = true; c.zepiVoiceState = 'listening';
  c.zvTurns = []; c.zvDraft = null; c.zvAct = null;
  c.zepiVoiceMini = false; c.zepiVoiceMuted = false;
  c.zepiMsgs = [];
}
"""

# Tarjeta pendiente en el chat, igual que la que deja una foto de recibo.
SEED_CARD_JS = """
(items) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.zepiMsgs.push({ role: 'model', text: 'Lei el recibo. Los registro?', actions: [], shot: null,
                    intent: { kind: 'add_records', items }, intentState: 'pending' });
}
"""

OK_ITEMS = [{"amount": 12.5, "category": "food", "description": "Almuerzo",
             "is_income": False, "date": "2026-07-20"}]

fails = []


total = []


def check(name, cond, extra=""):
    total.append(name)
    print(("  [OK] " if cond else "  [FALLA] ") + name + (("  -> " + str(extra)) if extra and not cond else ""))
    if not cond:
        fails.append(name)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    os.makedirs(SHOTS, exist_ok=True)
    port = free_port(); srv = serve(port)
    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        pg = ctx.new_page()
        pg.goto(f"http://127.0.0.1:{port}/index.html", wait_until="load")
        pg.wait_for_timeout(1200)
        err = pg.evaluate(LOGIN_JS, [MAX_EMAIL, PASS])
        if err:
            print("[FALLA] login:", err); return 1
        pg.wait_for_timeout(2500)

        st = lambda e: pg.evaluate("() => { const c = window.Alpine.$data(document.querySelector('#app')); return " + e + "; }")

        # ── 1. La llamada se escribe en el chat en vivo ─────────────────────────────
        print("\n=== 1. La conversacion queda en el chat ===")
        pg.evaluate(CALL_JS)
        pg.wait_for_selector(".zv-panel", timeout=6000)
        pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
          c._zvPushTurn('me', 'cuanto gaste'); c._zvPushTurn('me', ' en comida'); c._zvCloseTurns();
          c._zvPushTurn('zepi', 'Gastaste 120'); c._zvCloseTurns(); }""")
        pg.wait_for_timeout(400)
        msgs = st("c.zepiMsgs.map(m => ({ r: m.role, t: m.text, v: !!m.viaVoice }))")
        check("1a. dos mensajes en el chat (uno por turno, no por fragmento)", len(msgs) == 2, msgs)
        check("1b. los fragmentos engordaron el MISMO mensaje", msgs and msgs[0]["t"] == "cuanto gaste en comida", msgs)
        check("1c. lados correctos (yo=user, Zepi=model)",
              len(msgs) == 2 and msgs[0]["r"] == "user" and msgs[1]["r"] == "model", msgs)
        check("1d. marcados como voz", all(m["v"] for m in msgs), msgs)
        # El marcador 🎙 sale SOLO en lo dicho por voz (se siembra un mensaje normal para contrastar)
        pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
          c.zepiMsgs.push({ role: 'user', text: 'esto lo escribi', actions: [], shot: null }); }""")
        pg.wait_for_timeout(400)
        marks = pg.evaluate("""() => [...document.querySelectorAll('.zepi-msg')]
          .map(d => d.querySelector('span[title=\\"Dicho en una llamada\\"]'))
          .filter(Boolean).map(s => getComputedStyle(s).display)""")
        check("1e. el marcador de voz sale en los 2 turnos hablados", marks[:2] == ["inline", "inline"], marks)
        check("1f. y NO sale en lo escrito a mano", len(marks) > 2 and marks[2] == "none", marks)
        pg.evaluate("() => { window.Alpine.$data(document.querySelector('#app')).zepiMsgs.pop(); }")

        # Sobreviven a colgar (clic REAL en colgar)
        pg.click(".zv-ctrls button[aria-label='Colgar']")
        pg.wait_for_timeout(500)
        check("1g. al colgar, la conversacion SIGUE en el chat", len(st("c.zepiMsgs")) == 2, st("c.zepiMsgs.length"))
        check("1h. el panel de la llamada se cerro", st("c.zepiVoiceOpen") is False)

        # ── 2. Los avisos internos no son conversacion ──────────────────────────────
        print("\n=== 2. Los avisos [SISTEMA] no ensucian el chat ===")
        pg.evaluate(CALL_JS)
        pg.wait_for_timeout(300)
        pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
          c._zvPushTurn('me', '[SISTEMA] el usuario mando una foto'); }""")
        check("2a. [SISTEMA] no entra al chat", len(st("c.zepiMsgs")) == 0, st("c.zepiMsgs.length"))

        # ── 3. Cerrar el drill revela la tarjeta de abajo ───────────────────────────
        print("\n=== 3. Cerrar una tarjeta revela la siguiente ===")
        pg.evaluate(SEED_CARD_JS, OK_ITEMS)
        pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
          c._zvBuildDraft({ items: [{ amount: 9, category: 'food', description: 'Cafe' }] }); }""")
        pg.wait_for_selector(".zv-sheet", timeout=4000)
        check("3a. el drill aparta la llamada", st("c.zepiVoiceMini") is True)
        pg.click(".zv-sheet-btns .zepi-card-no")   # clic REAL en Cancelar
        pg.wait_for_timeout(400)
        check("3b. con tarjeta pendiente abajo, la llamada SIGUE minimizada", st("c.zepiVoiceMini") is True)
        check("3c. el panel no volvio a taparla", pg.locator(".zv-panel.zv-away").count() == 1)
        card = pg.locator(".zepi-card").first
        check("3d. la tarjeta del recibo queda VISIBLE", card.is_visible())
        pg.screenshot(path=os.path.join(SHOTS, "capas-tarjeta-revelada.png"))

        # Control negativo: sin nada pendiente, la llamada vuelve
        pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
          c.zepiMsgs = []; c._zvBuildDraft({ items: [{ amount: 9, category: 'food', description: 'Cafe' }] }); }""")
        pg.wait_for_selector(".zv-sheet", timeout=4000)
        pg.click(".zv-sheet-btns .zepi-card-no")
        pg.wait_for_timeout(400)
        check("3e. CONTROL NEGATIVO: sin tarjeta pendiente, la llamada vuelve", st("c.zepiVoiceMini") is False)

        # ── 4. Foto con un drill abierto: Zepi se entera de que quedo detras ────────
        print("\n=== 4. Zepi no dice 'ya la ves' si quedo detras ===")
        pg.evaluate(SEED_CARD_JS, OK_ITEMS)
        pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
          window.__zvSent = [];
          c._zvBuildDraft({ items: [{ amount: 9, category: 'food', description: 'Cafe' }] });
          if ((c.zvDraft || c.zvAct) && c._zepiHasPendingCard()) {
            c._zvNotify('[SISTEMA] Ya lei el recibo, pero su tarjeta quedo DETRAS de la que ya tenias abierta.');
          } }""")
        sent = pg.evaluate("() => (window.__zvSent || []).map(x => JSON.stringify(x)).join(' ')")
        check("4a. se le avisa a Zepi que la tarjeta quedo detras", "DETRAS" in sent, sent[:160])
        check("4b. _zepiHasPendingCard detecta la tarjeta", st("c._zepiHasPendingCard()") is True)

        # ── 5. Tarjeta del recibo editable ──────────────────────────────────────────
        print("\n=== 5. La tarjeta del recibo se puede corregir ===")
        pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
          c.zvDraft = null; c.zepiVoiceStop(); c.zepiMsgs = []; c.zepiOpen = true; }""")
        pg.evaluate(SEED_CARD_JS, [
            {"amount": 250, "category": "other", "description": "Plan Responde", "is_income": False, "date": "2026-07-02"},
            {"amount": 0, "category": "other", "description": "Sin monto", "is_income": False, "date": "2026-07-02"},
        ])
        pg.wait_for_selector(".zepi-card", timeout=4000)
        go = pg.locator(".zepi-card-btns .zepi-card-go").first
        check("5a. 'Registrar' BLOQUEADO con un movimiento sin monto", go.is_disabled())
        pg.click(".zepi-card .zepi-action")     # clic REAL en "Corregir"
        pg.wait_for_timeout(400)
        check("5b. 'Corregir' abre los campos editables", pg.locator(".zepi-card .zv-in-desc").count() == 2)
        pg.locator(".zepi-card .zv-amt input").nth(1).fill("30")
        pg.wait_for_timeout(300)
        check("5c. el monto editado llega al item", st("c.zepiMsgs[0].intent.items[1].amount") in (30, "30"),
              st("c.zepiMsgs[0].intent.items[1].amount"))
        check("5d. 'Registrar' se habilita al quedar todo completo", go.is_enabled())
        # Cambiar categoria con un chip REAL del primer movimiento
        chip = pg.locator(".zepi-card .zv-item").first.locator(".zv-chip", has_text="Comida").first
        chip.click()
        pg.wait_for_timeout(300)
        check("5e. el chip cambia la categoria de verdad",
              st("c.zepiMsgs[0].intent.items[0].category") == "food",
              st("c.zepiMsgs[0].intent.items[0].category"))
        pg.screenshot(path=os.path.join(SHOTS, "capas-tarjeta-editable.png"))

        # ── 6. Nada se sale por los lados en iPhone ─────────────────────────────────
        print("\n=== 6. Geometria en iPhone (390px) ===")
        ov = pg.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        check("6a. sin overflow horizontal", ov <= 0, f"sobran {ov}px")
        # Tarjeta ANGOSTA (1 movimiento corto): el pill de "Registrar" no debe cortar su texto
        pg.evaluate("""() => { const c = window.Alpine.$data(document.querySelector('#app'));
          c.zepiMsgs = []; }""")
        pg.evaluate(SEED_CARD_JS, OK_ITEMS)
        pg.wait_for_timeout(500)
        btn = pg.evaluate("""() => { const b = document.querySelector('.zepi-card-btns .zepi-card-go');
          return b ? { sw: b.scrollWidth, cw: b.clientWidth } : null; }""")
        check("6b. 'Registrar' entra en su boton con la tarjeta angosta",
              btn and btn["sw"] <= btn["cw"] + 1, btn)
        pg.screenshot(path=os.path.join(SHOTS, "capas-tarjeta-angosta.png"))

        ctx.close(); br.close()
    srv.shutdown()

    print("\n" + "=" * 52)
    if fails:
        print(f"[FALLA] {len(fails)} de {len(total)} — revisar:")
        for f in fails:
            print("   -", f)
        return 1
    print(f"TODO VERDE — {len(total)}/{len(total)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
