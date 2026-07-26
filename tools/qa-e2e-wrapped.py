#!/usr/bin/env python3
"""
QA E2E: "Mi mes en Zepo" (wrapped compartible, v189).

Login real demo@zepo.test → siembra 4 movimientos EN MEMORIA (no toca BD) →
llama _drawWrapped() → exige un PNG > 8KB de 1080x1920 y lo guarda para
revisión visual. Además corre el modo privacidad (hideAmounts) y exige que
también genere PNG válido. NO escribe nada en la base (solo dibuja canvas).
"""
import sys, os, json, socket, threading, http.server, functools, base64
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
EMAIL = "demo@zepo.test"; PASS = "ZepoDemo2026!"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")
os.makedirs(OUT, exist_ok=True)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


LOGIN = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

DRAW = """
async (hide) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.hideAmounts = hide;
  const cats = c.categories.slice(0,3);
  const today = localDate();
  c.expenses = (c.expenses||[]).filter(e => !String(e.id||'').startsWith('w_'));
  c.expenses.unshift(
    {id:'w_1',amount:42.5,category:(cats[0]&&cats[0].key)||'other',description:'a',date:today,is_income:false},
    {id:'w_2',amount:18,  category:(cats[1]&&cats[1].key)||'other',description:'b',date:today,is_income:false},
    {id:'w_3',amount:30,  category:(cats[2]&&cats[2].key)||'other',description:'c',date:today,is_income:false},
    {id:'w_4',amount:1200,category:(c.incomeCategories[0]&&c.incomeCategories[0].key)||'other',description:'d',date:today,is_income:true}
  );
  c.dataVer++;
  const canvas = document.createElement('canvas');
  canvas.width=1080; canvas.height=1920;
  await c._drawWrapped(canvas);
  const blob = await new Promise(r=>canvas.toBlob(r,'image/png'));
  return { size: blob?blob.size:0, type: blob?blob.type:'', w:canvas.width, h:canvas.height, dataUrl: canvas.toDataURL('image/png') };
}
"""


def save_png(data_url, name):
    b64 = data_url.split(",", 1)[1]
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(base64.b64decode(b64))


def run():
    port = free_port()
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    fails = []

    def check(name, ok, extra=""):
        print(("  [PASS] " if ok else "  [FALLA] ") + name + (" " + str(extra) if extra and not ok else ""))
        if not ok:
            fails.append(name)

    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        page.wait_for_function("()=>window.Alpine && window.Alpine.$data(document.querySelector('#app'))", timeout=15000)
        err = page.evaluate(LOGIN, [EMAIL, PASS])
        if err:
            print("[FALLA] login:", err); browser.close(); return 1
        page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
        page.wait_for_timeout(1200)

        # 1. modo normal (con montos)
        r = page.evaluate(DRAW, False)
        check("PNG generado (normal)", r["size"] > 8000 and r["type"] == "image/png", r.get("size"))
        check("dimensiones 1080x1920", r["w"] == 1080 and r["h"] == 1920, f"{r['w']}x{r['h']}")
        save_png(r["dataUrl"], "wrapped-normal.png")

        # 2. modo privacidad (montos enmascarados) — debe seguir generando PNG válido
        r2 = page.evaluate(DRAW, True)
        check("PNG generado (privacidad ••••)", r2["size"] > 8000 and r2["type"] == "image/png", r2.get("size"))
        save_png(r2["dataUrl"], "wrapped-hidden.png")

        # 3. el botón existe en Home y su guard aparece con >=3 movimientos
        page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.tab='home';c.showWelcomeCarousel=false;c.showOnbV2=false;}")
        page.wait_for_timeout(400)
        # v197: dejo de ser un boton suelto en mitad de Home; vive DENTRO del box del mes
        # (.hero-card > .hero-recap). Se comprueba tambien que siga ahi dentro, que es el punto.
        btn = page.evaluate("""()=>{
          const el = document.querySelector('.hero-recap');
          return { existe: !!el, dentroDelBox: !!(el && el.closest('.hero-card')) };
        }""")
        check("acceso 'Tu mes en Zepo' presente en Home", btn.get("existe") is True)
        check("y vive DENTRO del box del mes", btn.get("dentroDelBox") is True)

        browser.close()

    print()
    if fails:
        print(f"[FALLA] qa-e2e-wrapped: {len(fails)} fallas: {fails}")
        return 1
    print("[OK] qa-e2e-wrapped: TODO PASS · PNGs en tools/_shots/wrapped-*.png")
    return 0


if __name__ == "__main__":
    sys.exit(run())
