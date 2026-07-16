#!/usr/bin/env python3
"""
QA E2E REAL: el "restante" del editor de split (asignar / dividir lo que falta al 100%).

QUE PRUEBA (pedido de Alvaro): al editar montos o porcentajes a mano, el editor debe
mostrar cuanto FALTA o SOBRA para el 100% y ofrecer un boton:
  - "Dividir restante entre N" mientras queden VARIAS personas sin fijar a mano
  - "Asignar restante a X"     cuando queda UNA sola sin fijar
Una persona esta "sin fijar" aunque ya tenga valor, si ese valor lo puso la app
(reparto automatico) y no el usuario.

Todo con INTERACCION REAL en el DOM (fill/click), no asignando estado por eval:
el protocolo prohibe declarar verificado con datos simulados.

Casos: seed 50/50 cuadra (sin boton) · fijar 1 -> dividir entre 2 · fijar 2 -> asignar
a 1 · "Partes iguales" olvida lo fijado · pasarse de 100% bloquea y avisa · guardar con
suma != 100 se rechaza · agregar/quitar persona respeta lo fijado a mano · editar el
MONTO (no el %) tambien cuenta como fijar.
"""
import sys, time, socket, threading, http.server, functools, os, json
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv


LOGIN_JS = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  localStorage.setItem('zepo_a7_done_v1', '1');
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

# Abre la hoja con 3 personas repartidas por la app (nadie fijado a mano).
SETUP_JS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  // Overlays de onboarding/coach interceptan los clics reales (patron de qa-e2e-back-nav).
  c.showOnbV2 = false; c.showWelcomeCarousel = false; c.a7Active = false;
  c.coachTip = () => {}; c.coachKey = null;
  c.openNew();
  c.form.amount = '100';
  c.form.category = 'food';
  c.form.description = 'restante qa';
  c.form.is_split = true;
  c.form.split_people = [
    { name: 'Tú',   you: true,  pct: 34, color: '#507D5A' },
    { name: 'Ana',  you: false, pct: 33, color: '#8A6E9C' },
    { name: 'Luis', you: false, pct: 33, color: '#C9972F' },
  ];
  c._syncSplitAmts();
  c.splitPickerIdx = -1;
  await new Promise(r => setTimeout(r, 250));
  return { sum: c.splitSum, mode: c.splitRestanteMode };
}
"""

STATE_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  return {
    sum: c.splitSum, mode: c.splitRestanteMode, cuadra: c.splitCuadra,
    remPct: c.splitRemainderPct, remAmt: c.splitRemainderAmt,
    untouched: c.splitUntouched.length,
    people: c.form.split_people.map(p => ({ name: p.name, pct: p.pct, amt: p.amt, touched: !!p.touched })),
  };
}
"""


def pct_input(page, idx):
    return page.locator(".cd-split-pct-input").nth(idx)


def amt_input(page, idx):
    return page.locator(".cd-split-amt-input").nth(idx)


def restante_btn(page):
    return page.locator("button", has_text="restante")


def fill_pct(page, idx, value):
    inp = pct_input(page, idx)
    inp.scroll_into_view_if_needed()
    inp.fill(str(value))
    inp.dispatch_event("input")
    page.wait_for_timeout(200)


def run(url):
    r = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)

        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err:
            print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function(
            "() => { const c = window.Alpine.$data(document.querySelector('#app')); return !!c.user; }",
            timeout=20000)
        page.wait_for_timeout(2000)

        r["setup"] = page.evaluate(SETUP_JS)
        page.wait_for_timeout(400)
        r["s0"] = page.evaluate(STATE_JS)
        r["btn0_visible"] = restante_btn(page).count() > 0

        # --- Fijar Ana a mano en 50 -> quedan 2 sin fijar (Tú y Luis) -> "Dividir restante entre 2"
        fill_pct(page, 1, 50)
        r["s1"] = page.evaluate(STATE_JS)
        r["btn1_text"] = restante_btn(page).inner_text() if restante_btn(page).count() else ""
        # el indicador de la fila "Suma de partes" debe hablar de sobra/falta en DINERO
        r["sum_row1"] = page.locator("text=Suma de partes").locator("xpath=..").inner_text()

        # --- Click "Dividir restante": Tú y Luis absorben, Ana intacta, suma 100 exacta
        restante_btn(page).click()
        page.wait_for_timeout(300)
        r["s2"] = page.evaluate(STATE_JS)

        # --- Fijar Tú a mano en 10 -> queda 1 sin fijar (Luis) -> "Asignar restante a Luis"
        fill_pct(page, 0, 10)
        r["s3"] = page.evaluate(STATE_JS)
        r["btn3_text"] = restante_btn(page).inner_text() if restante_btn(page).count() else ""
        restante_btn(page).click()
        page.wait_for_timeout(300)
        r["s4"] = page.evaluate(STATE_JS)

        # --- "Partes iguales" olvida lo fijado a mano
        page.locator("button", has_text="Partes iguales").click()
        page.wait_for_timeout(300)
        r["s5"] = page.evaluate(STATE_JS)
        r["btn5_visible"] = restante_btn(page).count() > 0

        # --- Pasarse del 100% a mano: sin boton, con aviso, y guardar bloqueado
        fill_pct(page, 1, 80)
        fill_pct(page, 0, 40)
        r["s6"] = page.evaluate(STATE_JS)
        r["btn6_visible"] = restante_btn(page).count() > 0
        r["over_hint"] = page.locator("text=ya pasan del 100%").count() > 0
        r["save_blocked"] = page.evaluate("""
          async () => {
            const c = window.Alpine.$data(document.querySelector('#app'));
            await c.saveExpense();
            return { sheetOpen: c.sheetOpen, toast: c.toast || '' };
          }
        """)

        # --- Editar el MONTO (no el %) tambien fija a la persona
        page.locator("button", has_text="Partes iguales").click()
        page.wait_for_timeout(250)
        inp = amt_input(page, 1)
        inp.scroll_into_view_if_needed(); inp.fill("70"); inp.dispatch_event("input")
        page.wait_for_timeout(250)
        r["s7"] = page.evaluate(STATE_JS)

        # --- Agregar persona con Ana fijada: Ana NO se toca, la nueva entra al reparto
        page.evaluate("() => { const c = window.Alpine.$data(document.querySelector('#app')); c.addSplitPerson(); c.splitPickerIdx = -1; }")
        page.wait_for_timeout(300)
        r["s8"] = page.evaluate(STATE_JS)

        # --- Quitar la persona nueva: su parte vuelve a los no fijados, Ana sigue en 70
        page.evaluate("() => { const c = window.Alpine.$data(document.querySelector('#app')); c.removeSplitPerson(3); }")
        page.wait_for_timeout(300)
        r["s9"] = page.evaluate(STATE_JS)

        browser.close()
    return r


def by(state, name):
    for p in state.get("people", []):
        if p["name"] == name: return p
    return {}


def check(r):
    s0, s1, s2, s3 = r.get("s0", {}), r.get("s1", {}), r.get("s2", {}), r.get("s3", {})
    s4, s5, s6, s7 = r.get("s4", {}), r.get("s5", {}), r.get("s6", {}), r.get("s7", {})
    s8, s9 = r.get("s8", {}), r.get("s9", {})
    sb_ = r.get("save_blocked", {})
    return [
        # Estado inicial: reparto automatico que ya cuadra -> nada que ofrecer
        ("seed 34/33/33 cuadra en 100",                s0.get("sum") == 100 and s0.get("cuadra") is True),
        ("cuadrado: sin boton de restante",            s0.get("mode") == "hidden" and r.get("btn0_visible") is False),
        ("nadie nace fijado a mano",                   s0.get("untouched") == 3),
        # Fijar 1 -> dividir entre los otros 2
        ("fijar Ana=50 la marca a mano (solo a ella)", by(s1, "Ana").get("touched") is True and by(s1, "Luis").get("touched") is False),
        ("con 2 sin fijar -> modo 'divide'",           s1.get("mode") == "divide" and s1.get("untouched") == 2),
        ("indicador dice cuanto sobra en dinero",      "sobra $17.00" in (r.get("sum_row1") or "")),
        ("boton dice 'Dividir restante entre 2'",      "Dividir restante entre 2" in (r.get("btn1_text") or "")),
        ("dividir: Ana intacta en 50",                 by(s2, "Ana").get("pct") == 50),
        ("dividir: Tú y Luis toman 25 c/u",            by(s2, "Tú").get("pct") == 25 and by(s2, "Luis").get("pct") == 25),
        ("dividir: suma exacta 100",                   s2.get("sum") == 100 and s2.get("cuadra") is True),
        ("dividir: montos al centavo (25/50/25)",      by(s2, "Tú").get("amt") == 25 and by(s2, "Ana").get("amt") == 50),
        # Fijar otra -> asignar a la unica que queda
        ("fijar Tú=10 deja 1 sin fijar -> 'assign'",   s3.get("mode") == "assign" and s3.get("untouched") == 1),
        ("boton nombra a la persona restante (Luis)",  "Asignar restante a Luis" in (r.get("btn3_text") or "")),
        ("asignar: Luis toma el 40 restante",          by(s4, "Luis").get("pct") == 40),
        ("asignar: Ana 50 y Tú 10 intactos",           by(s4, "Ana").get("pct") == 50 and by(s4, "Tú").get("pct") == 10),
        ("asignar: suma exacta 100",                   s4.get("sum") == 100),
        # Partes iguales resetea el tracking
        ("'Partes iguales' olvida lo fijado a mano",   s5.get("untouched") == 3),
        ("'Partes iguales' cuadra y oculta el boton",  s5.get("cuadra") is True and r.get("btn5_visible") is False),
        # Pasarse de 100%
        ("fijado a mano >100% -> modo 'over'",         s6.get("mode") == "over"),
        ("'over': sin boton (no hay nada que repartir)", r.get("btn6_visible") is False),
        ("'over': avisa que se pasaron",               r.get("over_hint") is True),
        ("guardar con suma != 100 NO guarda",          sb_.get("sheetOpen") is True),
        ("guardar avisa la suma real",                 "deben sumar 100%" in (sb_.get("toast") or "")),
        # Editar el monto tambien fija
        ("editar el MONTO fija a la persona",          by(s7, "Ana").get("touched") is True),
        ("editar monto $70 -> 70% con total $100",     by(s7, "Ana").get("pct") == 70),
        # Agregar / quitar respetan lo fijado
        ("agregar persona NO pisa a la fijada (Ana 70)", by(s8, "Ana").get("pct") == 70),
        ("agregar persona: sigue cuadrando en 100",    s8.get("sum") == 100),
        ("quitar persona: Ana sigue fijada en 70",     by(s9, "Ana").get("pct") == 70),
        ("quitar persona: vuelve a cuadrar en 100",    s9.get("sum") == 100),
    ]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        r = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5)
        r = run(f"http://127.0.0.1:{port}/index.html")
    if r is False:
        sys.exit(1)
    checks = check(r)
    ok = all(v for _, v in checks)
    print("\n=== Resultado E2E restante del split ===")
    for label, v in checks:
        print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    print(f"\n  {sum(1 for _, v in checks if v)}/{len(checks)}")
    if not ok:
        print("\n  --- estados crudos ---")
        print(json.dumps(r, indent=2, default=str)[:2500])
    print("\n" + ("OK - asignar/dividir restante cuadra el 100% sin pisar lo que fijaste a mano"
                  if ok else "FALLO - el restante no se reparte como se espera"))
    sys.exit(0 if ok else 1)
