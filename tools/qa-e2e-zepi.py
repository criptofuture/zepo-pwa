#!/usr/bin/env python3
"""
QA E2E REAL: Zepi (companion IA, Max) — v177.

Con max@zepo.test (plan max REAL, login real):
 1. Burbuja .zepi-fab visible en Home.
 2. zepiScan detecta hallazgos deterministas (duplicado + presupuesto >=90%) y pone badge.
 3. Clic REAL en la burbuja -> sheet abre (chat, no candado).
 4. Mensaje REAL (teclear + enviar) con edge function MOCKEADA -> burbuja user +
    respuesta con **negrita** renderizada como <b> + boton de accion.
 5. Clic REAL en el boton de accion -> navega a Presupuestos y cierra el chat (zepiGo).
 6. Descartar hallazgo -> no vuelve tras re-scan (localStorage del dia).
 7. zepiFmt escapa HTML (anti-XSS) pero convierte **negrita**.
 8. Gesto atras (history.back) cierra el chat, no cambia de tab.
Con free@zepo.test (control negativo):
 9. La burbuja abre el CANDADO (Conoce a Zepi, sin input de chat).
10. CTA del candado -> pantalla de planes.

La edge function real ya se certifico por separado (scratchpad test_zepi.py: chat/insight/403).
USO: python tools/qa-e2e-zepi.py    Sale 1 si algo falla.
"""
import os, sys, socket, threading, http.server, functools, json
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_EMAIL = "max@zepo.test"; FREE_EMAIL = "free@zepo.test"; PASS = "ZepoQA2026!"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

LOGIN_JS = """
async ([email, password]) => {
  try { localStorage.setItem('zepo_a7_done_v1', '1'); } catch (e) {}   // sin tour A7 (tapa clics)
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

KILL_TOUR_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.a7Active = false;
  document.querySelectorAll('.driver-popover, .driver-overlay, svg.driver-overlay').forEach(el => el.remove());
  return true;
}
"""

# Datos en memoria con un DUPLICADO exacto y un presupuesto al 95% (para zepiScan).
SEED_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.coachTip = () => false;
  const m = new Date(); const mm = (d) => m.getFullYear() + '-' + String(m.getMonth()+1).padStart(2,'0') + '-' + String(d).padStart(2,'0');
  const mk = (id, d, cat, desc, amt) => ({ id, user_id: c.user.id, date: mm(d), category: cat,
    description: desc, amount: amt, is_income: false, created_at: new Date().toISOString() });
  c.expenses = [
    mk('z1', 5, 'food', 'Pizza familiar', 19.00),
    mk('z2', 5, 'food', 'Pizza familiar', 19.00),
    mk('z3', 6, 'transport', 'Taxi norte', 9.50),
  ];
  c.budgets = [ { category: null, amount: 100 }, { category: 'food', amount: 40 } ];
  try { localStorage.removeItem('zepo_zepi_dis'); } catch (e) {}
  try { localStorage.setItem('zepo_zepi_insight_d', new Date().toISOString().slice(0,10)); } catch (e) {}
  try { localStorage.removeItem('zepo_zepi_chat_' + c.user.id); } catch (e) {}
  c.zepiMsgs = []; c.dataVer++;
  return true;
}
"""

MOCK_REPLY = {"text": "Tu top es **Comida: $38** este mes.\nRevisa tu presupuesto.",
              "title": None, "actions": [{"label": "Abrir presupuestos", "target": "budgets"}], "shot": None}

def run():
    port = free_port(); srv = serve(port)
    url = f"http://127.0.0.1:{port}/index.html"
    results, alpine_errors = [], []
    def check(name, cond):
        results.append((name, bool(cond)))
        print(("  PASS " if cond else "  FAIL ") + name)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ── MAX: chat completo ──
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        page.on("console", lambda m: alpine_errors.append(m.text) if "Alpine Expression Error" in m.text else None)
        page.route("**/functions/v1/zepo-companion", lambda r: r.fulfill(
            status=200, content_type="application/json", body=json.dumps(MOCK_REPLY)))
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1000)
        page.wait_for_function("()=>!!(window.Alpine && document.querySelector('#app') && window.Alpine.$data(document.querySelector('#app')))", timeout=20000)
        err = page.evaluate(LOGIN_JS, [MAX_EMAIL, PASS])
        if err: print("LOGIN max FAIL:", err); sys.exit(1)
        page.wait_for_timeout(2200)
        page.evaluate(KILL_TOUR_JS)
        page.evaluate(SEED_JS)

        # 1. burbuja visible
        page.wait_for_timeout(400)
        check("1. burbuja visible en Home (max)", page.evaluate(
            "() => { const el = document.querySelector('.zepi-fab'); return !!el && getComputedStyle(el).display !== 'none'; }"))

        # 2. scan detecta duplicado + presupuesto
        found = page.evaluate("""() => {
          const c = window.Alpine.$data(document.querySelector('#app'));
          c.zepiScan();
          return { n: c.zepiFindings.length, badge: c.zepiBadge,
                   keys: c.zepiFindings.map(f => String(f.key).split('|')[0]) };
        }""")
        check("2. scan: duplicado + presupuesto (badge>0)",
              found["n"] >= 2 and found["badge"] >= 2 and "dup" in found["keys"] and "bud" in found["keys"])

        # 3. clic real abre el chat (no candado)
        page.click(".zepi-fab"); page.wait_for_timeout(600)
        check("3. sheet abre con chat (input presente, badge=0)", page.evaluate(
            "() => !!document.querySelector('.zepi-sheet') && !!document.querySelector('.zepi-input') && window.Alpine.$data(document.querySelector('#app')).zepiBadge === 0"))

        # 4. mensaje real con respuesta mockeada
        page.fill(".zepi-input", "en que gasto mas?")
        page.click(".zepi-send")
        page.wait_for_selector(".zepi-msg.user", timeout=5000)
        page.wait_for_function("() => document.querySelectorAll('.zepi-row.bot .zepi-msg.bot').length >= 1 && !window.Alpine.$data(document.querySelector('#app')).zepiTyping", timeout=10000)
        ok_bold = page.evaluate("""() => {
          const bots = [...document.querySelectorAll('.zepi-row.bot .zepi-msg.bot:not(.zepi-typing)')];
          const last = bots[bots.length - 1];
          return !!last && last.innerHTML.includes('<b>Comida: $38</b>');
        }""")
        ok_action = page.evaluate("() => [...document.querySelectorAll('.zepi-row .zepi-action')].some(b => b.textContent.trim() === 'Abrir presupuestos')")
        check("4. respuesta renderiza negrita + boton de accion", ok_bold and ok_action)

        # 5. clic en la accion navega
        page.click(".zepi-row .zepi-action >> text=Abrir presupuestos"); page.wait_for_timeout(500)
        st = page.evaluate("() => { const c = window.Alpine.$data(document.querySelector('#app')); return { open: c.zepiOpen, tab: c.tab }; }")
        check("5. zepiGo: cierra chat y va a Presupuestos", st["open"] is False and st["tab"] == "budgets")

        # 6. descartar hallazgo persiste el dia
        gone = page.evaluate("""() => {
          const c = window.Alpine.$data(document.querySelector('#app'));
          c.zepiScan();
          const before = c.zepiFindings.length;
          const key = c.zepiFindings[0].key;
          c.zepiDismissFind(0);
          c.zepiScan();
          return { before, after: c.zepiFindings.length, back: c.zepiFindings.some(f => f.key === key) };
        }""")
        check("6. hallazgo descartado no vuelve tras re-scan", gone["after"] == gone["before"] - 1 and not gone["back"])

        # 7. anti-XSS
        fmt = page.evaluate("() => window.Alpine.$data(document.querySelector('#app')).zepiFmt('<img src=x onerror=alert(1)> y **ojo**')")
        check("7. zepiFmt escapa HTML y respeta negrita", "&lt;img" in fmt and "<b>ojo</b>" in fmt and "<img" not in fmt)

        # 8. gesto atras cierra el chat sin cambiar tab
        page.evaluate("() => { const c = window.Alpine.$data(document.querySelector('#app')); c.tab = 'home'; }")
        page.wait_for_timeout(300)
        page.click(".zepi-fab"); page.wait_for_timeout(500)
        page.evaluate("() => history.back()"); page.wait_for_timeout(600)
        st8 = page.evaluate("() => { const c = window.Alpine.$data(document.querySelector('#app')); return { open: c.zepiOpen, tab: c.tab }; }")
        check("8. atras cierra el chat, tab intacta", st8["open"] is False and st8["tab"] == "home")
        ctx.close()

        # ── FREE: candado ──
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844})
        page2 = ctx2.new_page()
        page2.on("console", lambda m: alpine_errors.append(m.text) if "Alpine Expression Error" in m.text else None)
        page2.goto(url, wait_until="domcontentloaded"); page2.wait_for_timeout(1000)
        page2.wait_for_function("()=>!!(window.Alpine && document.querySelector('#app') && window.Alpine.$data(document.querySelector('#app')))", timeout=20000)
        err2 = page2.evaluate(LOGIN_JS, [FREE_EMAIL, PASS])
        if err2: print("LOGIN free FAIL:", err2); sys.exit(1)
        page2.wait_for_timeout(2200)
        page2.evaluate(KILL_TOUR_JS)
        page2.evaluate("() => { const c = window.Alpine.$data(document.querySelector('#app')); c.showOnbV2 = false; c.coachTip = () => false; c.tab = 'home'; }")
        page2.wait_for_timeout(400)
        page2.click(".zepi-fab"); page2.wait_for_timeout(600)
        lock = page2.evaluate("""() => ({
          sheet: !!document.querySelector('.zepi-sheet'),
          input: !!document.querySelector('.zepi-input'),
          lock: (document.querySelector('.zepi-sheet') || {}).textContent ? document.querySelector('.zepi-sheet').textContent.includes('Conoce a Zepi') : false,
        })""")
        check("9. free ve candado (sin input de chat)", lock["sheet"] and not lock["input"] and lock["lock"])
        page2.click(".zepi-sheet .save-btn"); page2.wait_for_timeout(400)
        check("10. CTA candado lleva a planes", page2.evaluate(
            "() => window.Alpine.$data(document.querySelector('#app')).tab === 'plans'"))
        ctx2.close()
        browser.close()
    srv.shutdown()

    if alpine_errors:
        print("ALPINE ERRORS:"); [print("   ", e[:160]) for e in alpine_errors[:5]]
    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} PASS")
    sys.exit(0 if passed == len(results) and not alpine_errors else 1)

if __name__ == "__main__":
    run()
