#!/usr/bin/env python3
"""
CANDADO: un fallo de red NO puede degradar el plan de un usuario que paga.

Bug real (26-jul-2026, se lo comio la cuenta de Alvaro): `ensureUserRow()` arma un payload
con `plan:'free'` para CREAR la fila del usuario. Solo debia usarse si la fila no existia,
pero si el chequeo previo fallaba (timeout de 3s, red floja) la variable quedaba en false
y el upsert corria igual -> UPDATE que pisaba `plan` a 'free'. Un cliente Max perdia su
plan por un hipo de red.

Este test NO toca la BD: intercepta la red del navegador.
  1. NEGATIVO: si el chequeo de la fila FALLA -> no puede salir NINGUNA escritura a users.
  2. POSITIVO: si el chequeo dice "no existe" -> si tiene que escribir (si no, el test
     de arriba pasaria aunque alguien borrase la funcion entera).

Login demo. Sale 1 si falla.
"""
import sys, time, socket, threading, http.server, functools, os
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"

LOGIN_JS = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv


def correr(page, url, modo):
    """modo 'check_roto' = el SELECT de users falla. 'no_existe' = responde lista vacia.
    Devuelve las escrituras (POST/PATCH) que intento hacer contra la tabla users."""
    escrituras = []

    def handler(route, request):
        m = request.method
        if m in ('POST', 'PATCH', 'PUT'):
            escrituras.append({'metodo': m, 'body': (request.post_data or '')[:200]})
            return route.abort()
        if m == 'GET':
            if modo == 'check_roto':
                return route.abort()          # simula el timeout / la red que se cae
            return route.fulfill(status=200, content_type='application/json', body='[]')
        return route.continue_()

    page.route('**/rest/v1/users*', handler)
    page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
    err = page.evaluate(LOGIN_JS, [DEMO_EMAIL, DEMO_PASS])
    if err:
        page.unroute('**/rest/v1/users*')
        return None, err
    page.wait_for_function(
        "()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}",
        timeout=20000)
    page.wait_for_timeout(3500)   # margen para el fallback REST de ensureUserRow
    page.unroute('**/rest/v1/users*')
    return escrituras, None


def main():
    port = free_port(); serve(port); time.sleep(0.5)
    url = f"http://127.0.0.1:{port}/index.html"
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844})

        page = ctx.new_page(); page.on("dialog", lambda d: d.accept())
        roto, err1 = correr(page, url, 'check_roto')
        page.close()

        page2 = ctx.new_page(); page2.on("dialog", lambda d: d.accept())
        vacio, err2 = correr(page2, url, 'no_existe')
        page2.close()
        b.close()

    if err1 or err2:
        print("[FALLA] login:", err1 or err2); return False

    # Solo cuenta como degradacion la escritura que manda plan (el payload de creacion).
    con_plan = [e for e in roto if '"plan"' in e['body'] or "'plan'" in e['body']]

    checks = [
        ("Chequeo roto: NO escribe nada en users", len(roto) == 0),
        ("Chequeo roto: en particular NO manda plan:'free'", len(con_plan) == 0),
        ("Fila inexistente: SI la crea (el test no es un falso verde)", len(vacio) > 0),
    ]
    print("\n=== Candado: el plan no se degrada por un fallo de red ===")
    print(f"  escrituras con el chequeo roto: {roto}")
    print(f"  escrituras con fila inexistente: {len(vacio)}")
    for lab, v in checks:
        print(f"  [{'PASS' if v else 'FALLA'}] {lab}")
    if con_plan:
        print("\n  ⚠️ REGRESION GRAVE: un usuario que paga perderia su plan por un hipo de red."
              "\n  Mirar ensureUserRow() en index.html: solo puede escribir si SABE que la fila no existe.")
    return all(v for _, v in checks)


if __name__ == "__main__":
    ok = main()
    print("\n" + ("OK - el plan sobrevive a la red mala" if ok else "FALLO - revisar ensureUserRow()"))
    sys.exit(0 if ok else 1)
