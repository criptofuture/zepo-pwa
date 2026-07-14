#!/usr/bin/env python3
"""
Captura las screenshots de la guia de Zepi (companion) -> /pwa/guide/*.webp
+ QA visual del propio chat de Zepi (tools/_zepi-shots/).

- Login REAL con max@zepo.test (plan max => todas las pantallas abiertas).
- Siembra datos EN MEMORIA (c.expenses locales, nunca escribe a la BD) para que
  las pantallas se vean vivas.
- Re-correr cuando cambie el diseno: python tools/capture-guide-shots.py
- Falla (exit 1) si una pantalla no renderiza o hay Alpine Expression Error.

Requiere: playwright chromium + Pillow (webp).
"""
import os, sys, time, socket, threading, http.server, functools, json
from playwright.sync_api import sync_playwright
from PIL import Image

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PWA_DIR, "guide")
QA_OUT = os.path.join(PWA_DIR, "tools", "_zepi-shots")
MAX_EMAIL = "max@zepo.test"; MAX_PASS = "ZepoQA2026!"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

LOGIN_JS = """
async ([email, password]) => {
  try { localStorage.setItem('zepo_a7_done_v1', '1'); } catch (e) {}   // sin tour A7 (tapa la UI)
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

# Datos SOLO en memoria (this.expenses) — jamas tocan Supabase.
SEED_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showOnbV2 = false; c.coachTip = () => false; c.coachKey = null;
  const m = new Date(); const mm = (d) => m.getFullYear() + '-' + String(m.getMonth()+1).padStart(2,'0') + '-' + String(d).padStart(2,'0');
  const mk = (d, cat, desc, amt, extra) => Object.assign({ id: 'seed_' + cat + d + Math.round(amt*100), user_id: c.user.id,
    date: mm(d), category: cat, description: desc, amount: amt, is_income: false, created_at: new Date().toISOString() }, extra || {});
  c.expenses = [
    mk(2, 'salary', 'Sueldo', 1200, { is_income: true }),
    mk(3, 'market', 'Supermaxi semana', 62.40),
    mk(4, 'food', 'Almuerzo oficina', 8.50),
    mk(5, 'transport', 'Taxi aeropuerto', 12.00),
    mk(6, 'coffee', 'Cafe con Andrea', 4.80),
    mk(7, 'food', 'Cena La Briciola', 34.00, { is_split: true, split_status: 'pendiente', split_pending: 17.00, split_persona: 'Bea' }),
    mk(8, 'rent', 'Internet fibra', 28.90),
    mk(9, 'fun', 'Cine multicines', 15.50),
    mk(10, 'food', 'Sushi nocturno', 21.30),
    mk(11, 'gym', 'Mensualidad gym', 45.00),
    mk(12, 'transport', 'Gasolina', 25.00),
    mk(13, 'health', 'Farmacia', 9.60),
  ];
  c.budgets = [ { category: null, amount: 600 }, { category: 'food', amount: 120 }, { category: 'transport', amount: 80 }, { category: 'fun', amount: 60 } ];
  c.dataVer++;
  return c.expenses.length;
}
"""

# (id, js sobre `c`, espera ms, captura?)  — id con _ = paso auxiliar sin captura
STEPS = [
    ("home",        "c.tab='home'",                                          1400, True),
    ("add-expense", "c.openNew()",                                            900, True),
    ("split",       "c.form.amount='24.00'; c.form.description='Cena con amigos'; c.analyzed=true; c.form.is_split=true", 800, True),
    ("_c1",         "c.sheetOpen=false",                                      400, False),
    ("budgets",     "c.tab='budgets'",                                       1000, True),
    ("budget-edit", "c.budgetSheetOpen=true",                                 900, True),
    ("_c2",         "c.budgetSheetOpen=false",                                400, False),
    ("cuentas",     "c.tab='cuentas'; c.loadSplits()",                       1600, True),
    ("dash",        "c.tab='dash'",                                          1200, True),
    ("history",     "c.tab='history'; c.histAll=true; c.loadHistory()",      1600, True),
    ("_c3",         "c.tab='home'",                                           500, False),
    ("patrimonio",  "c.openPatrimonio()",                                    1600, True),
    ("_c4",         "c.tab='settings'",                                       700, False),
    ("spaces",      "c.openSpaceManager()",                                   900, True),
    ("_c5",         "c.spaceManagerOpen=false",                               400, False),
    ("paymethods",  "c.openPmManager()",                                      900, True),
    ("_c6",         "c.pmManagerOpen=false",                                  400, False),
    ("categories",  "c.openCatManager()",                                     900, True),
    ("_c7",         "c.catManagerOpen=false",                                 400, False),
    ("settings",    "c.tab='settings'",                                       800, True),
    ("plans",       "c.tab='plans'",                                          900, True),
]

ZEPI_SEED_MSGS = [
    {"role": "user", "text": "¿En qué gasté más este mes?"},
    {"role": "model", "text": "Tu top este mes es **Comida: $63.80** en 3 registros, seguido de Mercado con $62.40. Vas dentro de tu presupuesto — llevas 45% del total. 👏",
     "actions": [{"label": "Abrir presupuestos", "target": "budgets"}], "shot": None},
]

def run():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(QA_OUT, exist_ok=True)
    port = free_port(); srv = serve(port)
    url = f"http://127.0.0.1:{port}/index.html"
    errors, fails = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.on("console", lambda m: errors.append(m.text) if "Alpine Expression Error" in m.text else None)
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        page.wait_for_function("()=>!!(window.Alpine && document.querySelector('#app') && window.Alpine.$data(document.querySelector('#app')))", timeout=20000)
        err = page.evaluate(LOGIN_JS, [MAX_EMAIL, MAX_PASS])
        if err: print("LOGIN FAIL:", err); sys.exit(1)
        page.wait_for_timeout(2500)
        n = page.evaluate(SEED_JS)
        print(f"login OK · {n} registros sembrados en memoria")

        for sid, js, wait, capture in STEPS:
            try:
                page.evaluate(f"() => {{ const c = window.Alpine.$data(document.querySelector('#app')); {js}; }}")
                page.wait_for_timeout(wait)
                if capture:
                    png = os.path.join(OUT, sid + ".png")
                    page.screenshot(path=png)
                    print("  shot:", sid)
            except Exception as e:
                fails.append(f"{sid}: {e}"); print("  FAIL:", sid, e)

        # ── QA visual del chat de Zepi (no va a guide/) ──
        try:
            page.evaluate("(msgs) => { const c = window.Alpine.$data(document.querySelector('#app')); c.tab='home'; c.zepiMsgs=msgs; c._zepiLoaded=true; c.openZepi(); }", ZEPI_SEED_MSGS)
            page.wait_for_timeout(1200)
            ok_sheet = page.evaluate("() => !!document.querySelector('.zepi-sheet') && !!document.querySelector('.zepi-msg.user')")
            if not ok_sheet: fails.append("zepi-sheet no renderiza")
            page.screenshot(path=os.path.join(QA_OUT, "zepi-chat.png"))
            page.evaluate("() => { const c = window.Alpine.$data(document.querySelector('#app')); c.zepiOpen=false; }")
            page.wait_for_timeout(400)
            ok_fab = page.evaluate("() => { const el = document.querySelector('.zepi-fab'); return !!el && getComputedStyle(el).display !== 'none'; }")
            if not ok_fab: fails.append("zepi-fab no visible en home")
            page.screenshot(path=os.path.join(QA_OUT, "zepi-fab-home.png"))
            print("  QA zepi: sheet+fab OK" if not fails else "  QA zepi con fallos")
        except Exception as e:
            fails.append(f"zepi-qa: {e}")
        browser.close()
    srv.shutdown()

    # PNG -> webp (y borra el png)
    for f in sorted(os.listdir(OUT)):
        if f.endswith(".png"):
            src = os.path.join(OUT, f)
            Image.open(src).save(os.path.join(OUT, f[:-4] + ".webp"), "WEBP", quality=78, method=6)
            os.remove(src)
    sizes = {f: os.path.getsize(os.path.join(OUT, f)) // 1024 for f in sorted(os.listdir(OUT)) if f.endswith(".webp")}
    print(f"\n{len(sizes)} webp en guide/ · total {sum(sizes.values())} KB · max {max(sizes.values()) if sizes else 0} KB")
    if errors: print("ALPINE ERRORS:", "\n".join(errors[:6]))
    if fails: print("FAILS:", "\n".join(fails))
    print("RESULTADO:", "PASS" if not (errors or fails) else "FAIL")
    sys.exit(1 if (errors or fails) else 0)

if __name__ == "__main__":
    run()
