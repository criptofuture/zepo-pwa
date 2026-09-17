#!/usr/bin/env python3
"""
QA E2E: si la lectura de métodos de pago FALLA, la app no debe sembrar los de fábrica.

Bug v205 (16-sep-2026): con mala señal loadPaymentMethods tomaba el fallo como «lista vacía»
y creaba Efectivo/Tarjeta/Transferencia otra vez (Alvaro quedó con dos Efectivo).
Prueba: bloquea los GET a payment_methods, llama loadPaymentMethods y cuenta las filas
de la cuenta demo antes y después. Deben ser iguales. Si sembró, borra lo sembrado.
Sale 1 si falla.
"""
import sys, os, time, socket, threading, http.server, functools
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    h.log_message = lambda *a: None
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

LOGIN = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""
ROWS = """
async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const r = await fetch(SUPABASE_URL + '/rest/v1/payment_methods?select=id,created_at&user_id=eq.' + c.user.id, { headers: sbAuthHeaders() });
  return await r.json();
}
"""
LOAD = "async () => { const c = window.Alpine.$data(document.querySelector('#app')); await c.loadPaymentMethods(); return c.paymentMethods.length; }"
DELETE = """
async (ids) => {
  for (const id of ids) await fetch(SUPABASE_URL + '/rest/v1/payment_methods?id=eq.' + id, { method: 'DELETE', headers: sbAuthHeaders() });
}
"""

def main():
    port = free_port(); serve(port)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context(viewport={"width": 390, "height": 844}).new_page()
        pg.goto(f"http://127.0.0.1:{port}/index.html")
        pg.wait_for_function("()=>window.Alpine && document.querySelector('#app')", timeout=20000)
        err = pg.evaluate(LOGIN, [DEMO_EMAIL, DEMO_PASS])
        if err: print("FALLA login:", err); return 1
        time.sleep(3)
        before = pg.evaluate(ROWS)
        if not before: print("FALLA: la cuenta demo no tiene métodos; la prueba necesita al menos uno"); return 1
        def block(route):
            if route.request.method == "GET": return route.abort()
            return route.continue_()
        pg.route("**/rest/v1/payment_methods*", block)
        shown = pg.evaluate(LOAD)
        time.sleep(1)
        pg.unroute("**/rest/v1/payment_methods*")
        after = pg.evaluate(ROWS)
        new = [r["id"] for r in after if r["id"] not in {x["id"] for x in before}]
        if new: pg.evaluate(DELETE, new)
        b.close()
    print(f"filas antes {len(before)} · después {len(after)} · en pantalla {shown}")
    ok = not new and shown == len(before)
    print("OK: lectura fallida no siembra ni vacía la lista" if ok else f"FALLA: sembró {len(new)} métodos o vació la lista")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
