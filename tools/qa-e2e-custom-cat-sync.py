#!/usr/bin/env python3
"""
QA E2E (nube): las categorias propias sobreviven un cambio de dispositivo.

Flujo real contra Supabase con la cuenta demo:
  1. crea una categoria propia (quickAddCatForForm) -> debe subir a zepo_custom_categories
  2. verifica la fila en la BD (admin REST)
  3. simula DEVICE NUEVO: borra localStorage, recarga, re-login -> loadCustomCategoriesRemote
  4. exige que la categoria vuelva (grid + CAT_MAP + getCatLabel = nombre real)
  5. limpia: removeCategory -> la fila desaparece de la BD
Sale 1 si algo falla. Limpia siempre (admin) por si algo queda a medias.
"""
import sys, os, json, time, socket, threading, http.server, functools, urllib.request, urllib.error, urllib.parse
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(PWA_DIR, "..", "..", "config.json")))["supabase"]
URL, SK = CFG["url"], CFG["secret_key"]
DEMO_EMAIL = "demo@zepo.test"; DEMO_PASS = "ZepoDemo2026!"
LABEL = "QA Sync Cat 9Z"
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}


def admin(method, path):
    r = urllib.request.Request(URL + path, headers=H, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            t = resp.read().decode() or "[]"
            return resp.status, (json.loads(t) if t[:1] in "[{" else t)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def user_id():
    s, u = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(u, dict):
        for x in u.get("users", []):
            if x.get("email") == DEMO_EMAIL:
                return x["id"]
    return None


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
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

CREATE = """
(label) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.openNew();
  c.form.is_income = false;
  c.gridAddingCat = true;
  c.newCatLabel = label;
  c.newCatEmoji = '🧪';
  c.quickAddCatForForm();
  return c.form.category;   // la key nueva
}
"""


def run():
    uid = user_id()
    if not uid:
        print("[FALLA] no encontre el usuario demo"); return 1
    # pre-clean
    admin("DELETE", f"/rest/v1/zepo_custom_categories?user_id=eq.{uid}&label=eq.{urllib.parse.quote(LABEL)}")

    port = free_port(); serve(port)
    url = f"http://127.0.0.1:{port}/index.html"
    ok = True
    key = None
    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        page.wait_for_function("()=>window.Alpine && window.Alpine.$data(document.querySelector('#app'))", timeout=15000)
        err = page.evaluate(LOGIN, [DEMO_EMAIL, DEMO_PASS])
        if err:
            print("[FALLA] login:", err); browser.close(); return 1
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(1500)

        # 1. crear
        key = page.evaluate(CREATE, LABEL)
        print("  key creada:", key)
        if not key or not key.startswith("custom_"):
            print("  FAIL: no se creo la categoria"); ok = False
        page.wait_for_timeout(2000)  # dejar que suba (best-effort)

        # 2. verificar en BD
        s, rows = admin("GET", f"/rest/v1/zepo_custom_categories?user_id=eq.{uid}&label=eq.{urllib.parse.quote(LABEL)}")
        in_db = isinstance(rows, list) and len(rows) == 1 and rows[0].get("key") == key
        print("  en BD tras crear:", "ok" if in_db else f"FAIL ({s} {rows})")
        ok = ok and in_db

        # 3. simular DEVICE NUEVO: borrar localStorage + recargar + re-login
        page.evaluate("() => { try { localStorage.clear(); } catch(e){} }")
        page.reload(wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        page.wait_for_function("()=>window.Alpine && window.Alpine.$data(document.querySelector('#app'))", timeout=15000)
        err = page.evaluate(LOGIN, [DEMO_EMAIL, DEMO_PASS])
        if err:
            # Bajo carga (gate), signInWithPassword puede exceder el timeout de 10s y marcar
            # "conexion lenta", pero la sesion igual se establece (SIGNED_IN llega despues).
            # Lo que importa es que c.user aparezca y la categoria vuelva -> no es fatal.
            print("  (aviso) relogin lento, espero la sesion igual:", err)
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=25000)
        # esperar a que loadCustomCategoriesRemote (en el Promise.all post-login) traiga la cat
        got = page.wait_for_function(
            "(k)=>{const c=window.Alpine.$data(document.querySelector('#app'));return c.categories.some(x=>x.key===k);}",
            arg=key, timeout=15000)
        recovered = page.evaluate("""(k) => {
          const c = window.Alpine.$data(document.querySelector('#app'));
          return { inGrid: c.categories.some(x=>x.key===k), inMap: (typeof CAT_MAP!=='undefined' && !!CAT_MAP[k]), label: c.getCatLabel(k) };
        }""", key)
        okrec = recovered["inGrid"] and recovered["inMap"] and recovered["label"] == LABEL
        print("  tras device nuevo:", recovered, "->", "ok" if okrec else "FAIL")
        ok = ok and okrec

        # 5. limpiar via la app (removeCategory -> borra de la BD)
        page.evaluate("(k)=>{ window.Alpine.$data(document.querySelector('#app')).removeCategory(k); }", key)
        page.wait_for_timeout(2000)
        browser.close()

    s, rows = admin("GET", f"/rest/v1/zepo_custom_categories?user_id=eq.{uid}&label=eq.{urllib.parse.quote(LABEL)}")
    gone = isinstance(rows, list) and len(rows) == 0
    print("  borrada de BD tras removeCategory:", "ok" if gone else f"FAIL ({rows})")
    ok = ok and gone
    # cleanup duro por si acaso
    admin("DELETE", f"/rest/v1/zepo_custom_categories?user_id=eq.{uid}&label=eq.{urllib.parse.quote(LABEL)}")

    print("[OK] categorias propias sincronizan a la nube (sobreviven device nuevo)" if ok else "[FALLA] sync de categorias a la nube")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
