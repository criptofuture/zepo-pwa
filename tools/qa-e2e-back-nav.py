#!/usr/bin/env python3
"""
QA E2E REAL: gesto/flecha ATRAS = retroceder UN solo nivel (bug v176).

Bug de Alvaro (regresion): el gesto atras en Android (y la flechita/edge-swipe iOS)
saltaba directo a Inicio en vez de cerrar solo el nivel superior. Causas:
  1) Modales SIN cubrir en popstate (acceptPrModal, acceptAllModal, aliasModalOpen,
     showDeleteModal, importOpen, confirmState, catDropdownOpen): el gesto caia a la
     logica de pestanas y cambiaba de pantalla CON el modal abierto.
  2) prevTab guardaba la pestana a la que ENTRAS -> atras desde una pestana principal
     quedaba "pegado" (tab = si misma). Ahora budgets/cuentas/dash/patrimonio -> home.
  3) Cambio de pestana DENTRO del handler disparaba el watcher de tab -> push doble ->
     el siguiente atras se consumia "en vacio" (no pasaba nada). Ahora _navPopping.

Cada page.go_back() de Playwright dispara popstate igual que el gesto real.
Sale 1 si algun paso retrocede 0 niveles o mas de 1.
"""
import sys, time, socket, threading, http.server, functools, os
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
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

def C(expr):
    return f"()=>{{const c=window.Alpine.$data(document.querySelector('#app'));{expr}}}"

def run(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width":390,"height":844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1500)
        page.wait_for_function("()=>!!(window.Alpine && window.Alpine.$data(document.querySelector('#app')))", timeout=20000)
        err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
        if err: print("[FALLA] login:", err); browser.close(); return False
        page.wait_for_function(C("return !!c.user;"), timeout=20000)
        page.wait_for_timeout(2500)
        page.evaluate(C("c.showOnbV2=false; c.coachTip=()=>{}; c.coachKey=null; c.userPlan='elite'; return 1;"))
        checks = []

        state = {"step": "inicio"}
        def back():
            page.go_back(); page.wait_for_timeout(450)
            if page.url.startswith("about:"):
                raise RuntimeError(f"go_back() salio del documento en el paso: {state['step']} (url={page.url})")

        def snap():
            return page.evaluate(C(
                "return {tab:c.tab, sheet:c.sheetOpen, pm:c.pmManagerOpen, accept:!!c.acceptPrModal,"
                "confirm:!!c.confirmState, imp:c.importOpen, alias:c.aliasModalOpen};"))

        state['step'] = '0 init unico'
        # 0) init() corre UNA vez: un cambio de tab = exactamente UNA entrada de historial
        #    (el doble x-init duplicaba popstate/watchers -> atras saltaba 2 niveles)
        page.evaluate(C("c.tab='home'; return 1;")); page.wait_for_timeout(300)
        delta = page.evaluate(C("const b=history.length; c.tab='dash'; "
                                "return new Promise(r=>setTimeout(()=>r(history.length-b),350));"))
        checks.append(("init unico: 1 cambio de tab = +1 entrada (no doble)", delta == 1))
        back()

        state['step'] = '1 cuentas->home'
        # 1) home -> cuentas -> ATRAS = home (antes: quedaba pegado en cuentas)
        page.evaluate(C("c.tab='home'; return 1;")); page.wait_for_timeout(300)
        page.evaluate(C("c.tab='cuentas'; return 1;")); page.wait_for_timeout(300)
        back()
        checks.append(("cuentas -> atras = home (1 nivel)", snap()["tab"] == "home"))

        state['step'] = '2 notifications'
        # 2) home -> settings -> notifications -> ATRAS = settings -> ATRAS = home
        #    (antes el push doble metia un atras "en vacio")
        page.evaluate(C("c.tab='settings'; return 1;")); page.wait_for_timeout(300)
        page.evaluate(C("c.tab='notifications'; return 1;")); page.wait_for_timeout(300)
        back()
        t1 = snap()["tab"]
        back()
        t2 = snap()["tab"]
        checks.append(("notifications -> atras = settings", t1 == "settings"))
        checks.append(("settings -> atras = home (sin atras en vacio)", t2 == "home"))

        state['step'] = '3 pmManager'
        # 3) settings -> gestor de metodos -> ATRAS cierra el gestor y SIGUE en settings
        page.evaluate(C("c.tab='settings'; return 1;")); page.wait_for_timeout(300)
        page.evaluate(C("c.openPmManager(); return 1;")); page.wait_for_timeout(300)
        back()
        s = snap()
        checks.append(("gestor metodos -> atras lo cierra sin moverse", s["pm"] is False and s["tab"] == "settings"))

        state['step'] = '4 acceptPrModal'
        # 4) cuentas + modal aceptar cobro -> ATRAS cierra el modal y SIGUE en cuentas
        page.evaluate(C("c.tab='cuentas'; return 1;")); page.wait_for_timeout(300)
        page.evaluate(C("c.acceptPrModal={id:'qa',amount:5,from_name:'QA'}; return 1;")); page.wait_for_timeout(300)
        back()
        s = snap()
        checks.append(("modal aceptar cobro -> atras lo cierra sin moverse", s["accept"] is False and s["tab"] == "cuentas"))
        back()
        checks.append(("cuentas -> atras = home (tras cerrar modal)", snap()["tab"] == "home"))

        state['step'] = '5 sheet'
        # 5) hoja de registro abierta -> ATRAS la cierra y sigue en home
        page.evaluate(C("c.openNew(); return 1;")); page.wait_for_timeout(300)
        back()
        s = snap()
        checks.append(("hoja registro -> atras la cierra sin moverse", s["sheet"] is False and s["tab"] == "home"))

        state['step'] = '6 confirm'
        # 6) confirm generico (askConfirm) -> ATRAS = cancelar (resuelve false), sin moverse
        page.evaluate(C("c.tab='settings'; return 1;")); page.wait_for_timeout(300)
        page.evaluate(C("window._qaConfirm=null; c.askConfirm({title:'QA?'}).then(v=>window._qaConfirm=v); return 1;"))
        page.wait_for_timeout(300)
        back()
        s = snap()
        resolved = page.evaluate("()=>window._qaConfirm")
        checks.append(("confirm -> atras cancela (false) sin moverse", s["confirm"] is False and resolved is False and s["tab"] == "settings"))

        state['step'] = '7 import'
        # 7) sheet importar -> ATRAS lo cierra sin moverse
        page.evaluate(C("c.importOpen=true; return 1;")); page.wait_for_timeout(300)
        back()
        s = snap()
        checks.append(("sheet importar -> atras lo cierra sin moverse", s["imp"] is False and s["tab"] == "settings"))

        state['step'] = '8 plans'
        # 8) plans -> ATRAS = settings (subnivel de config)
        page.evaluate(C("c.tab='plans'; return 1;")); page.wait_for_timeout(300)
        back()
        checks.append(("plans -> atras = settings", snap()["tab"] == "settings"))

        browser.close()

    ok = all(v for _, v in checks)
    print("\n=== E2E gesto atras = un solo nivel ===")
    for label, v in checks: print(f"  [{'PASS' if v else 'FALLA'}] {label}")
    return ok

if __name__ == "__main__":
    if len(sys.argv) > 1: ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5)
        ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - atras retrocede exactamente un nivel en todo el mapa probado" if ok
                  else "FALLO - el gesto atras sigue saltando o quedandose pegado"))
    sys.exit(0 if ok else 1)
