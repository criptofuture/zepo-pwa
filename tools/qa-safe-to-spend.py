#!/usr/bin/env python3
"""WebKit (motor iOS): certifica la tarjeta "Disponible para gastar" (safe-to-spend).
Siembra en memoria (sin tocar la BD): ingreso 1000, gasto 300, recurrente pendiente 200.
Espera safeToSpend = 1000 - 300 - 200 = 500, y que la tarjeta lo muestre en el home."""
import os, socket, threading, http.server, functools, datetime
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"
TODAY = datetime.date.today().isoformat()

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

PREP = """() => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const st = document.createElement('style'); st.id='ios-insets';
  st.textContent = ':root{--safe-top:44px !important;--safe-bottom:34px !important;}';
  document.head.appendChild(st);
}"""
LOGIN = """async ([email, password]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.devUnlockAll = true;
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}"""
SEED = """([today]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showWelcomeCarousel=false; c.showOnbV2=false; c.tab='home';
  c.expenses = [
    { id:'qa-inc', amount:1000, is_income:true,  date:today, category:'salary', description:'QA ingreso' },
    { id:'qa-exp', amount:300,  is_income:false, date:today, category:'food',   description:'QA gasto' },
  ];
  // day_of_month 31 -> eff = ultimo dia del mes >= hoy SIEMPRE; last_generated null -> pendiente.
  c.recurringTemplates = [
    { id:'qa-rec', active:true, day_of_month:31, amount:200, is_income:false, last_generated:null, description:'QA arriendo' },
  ];
  return {
    monthIncome:c.monthIncome, monthTotal:c.monthTotal,
    pending:c.pendingRecurringThisMonth, safeToSpend:c.safeToSpend,
    daysLeft:c.daysLeftInMonth, perDay:c.safeToSpendPerDay,
    expectedText:'$' + c.fmtMoney(c.safeToSpend)
  };
}"""
# Lee el DOM de la tarjeta: encuentra el label y sube al card; devuelve el texto del monto .mono.
READ_CARD = """() => {
  const label = [...document.querySelectorAll('#app *')].find(e =>
    e.children.length === 0 && e.textContent.trim() === 'Disponible para gastar');
  if (!label) return { found:false };
  const card = label.closest('div[style*="border-radius"]') || label.parentElement.parentElement;
  const r = card.getBoundingClientRect();
  const mono = card.querySelector('.mono');
  return {
    found:true,
    visible: r.height>2 && card.offsetParent !== null,
    amountText: mono ? mono.textContent.trim() : null,
    subText: card.textContent.replace(/\\s+/g,' ').trim()
  };
}"""

def run():
    port = free_port(); serve(port)
    url = f"http://127.0.0.1:{port}/"
    failures = 0
    with sync_playwright() as p:
        wk = p.webkit.launch()
        ctx = wk.new_context(**p.devices["iPhone 11"])
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1500)
        page.evaluate(PREP)
        err = page.evaluate(LOGIN, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); ctx.close(); wk.close(); return 1
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(1200)

        s = page.evaluate(SEED, [TODAY]); page.wait_for_timeout(500)
        print("\n[1] matematica de los getters:")
        print("   ", s)
        if abs(s["safeToSpend"] - 500) > 0.001:
            print("   [FALLA] safeToSpend esperado 500, got", s["safeToSpend"]); failures += 1
        elif abs(s["pending"]["expenses"] - 200) > 0.001:
            print("   [FALLA] pending.expenses esperado 200, got", s["pending"]); failures += 1
        else:
            print("   [PASS] 1000 - 300 - 200 = 500")

        card = page.evaluate(READ_CARD)
        print("\n[2] tarjeta en el home:")
        print("   ", card)
        if not (card.get("found") and card.get("visible")):
            print("   [FALLA] tarjeta no visible"); failures += 1
        elif card.get("amountText") != s["expectedText"]:
            print("   [FALLA] monto mostrado", card.get("amountText"), "!=", s["expectedText"]); failures += 1
        else:
            print("   [PASS] tarjeta muestra", card.get("amountText"))

        # control negativo: sin ingresos la tarjeta se oculta (x-show monthIncome>0)
        page.evaluate("""() => {
          const c = window.Alpine.$data(document.querySelector('#app'));
          c.expenses = [{ id:'qa-x', amount:50, is_income:false, date:'%s', category:'food', description:'x' }];
        }""" % TODAY); page.wait_for_timeout(400)
        hidden = page.evaluate(READ_CARD)
        print("\n[3] control negativo (sin ingresos -> oculta):")
        print("   ", hidden)
        if hidden.get("found") and hidden.get("visible"):
            print("   [FALLA] la tarjeta sigue visible sin ingresos"); failures += 1
        else:
            print("   [PASS] oculta sin ingresos")

        # screenshot con datos buenos (re-sembrar)
        page.evaluate(SEED, [TODAY]); page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(os.environ.get("TEMP","."), "zepo-safe-to-spend.png"))
        ctx.close(); wk.close()
    print("\n=== %s ===" % ("TODO PASS" if failures==0 else f"{failures} FALLAS"))
    print("screenshot: %TEMP%/zepo-safe-to-spend.png")
    return failures

if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
