#!/usr/bin/env python3
"""
QA E2E: las categorias PROPIAS (custom_) se resuelven tras recargar la app.

Bug que cubre: loadCustomCategories() empujaba las categorias propias al grid pero NO las
registraba en CAT_MAP. Tras cualquier reload (la PWA sirve HTML fresco a cada rato):
  - el dashboard mostraba el slug crudo "custom_xxx" + ✨ en vez del nombre real (bug nombres)
  - updateParsedItemCat hacia `const cat = CAT_MAP[key]; if (!cat) return;` => tocar la
    categoria propia en un item detectado NO la seleccionaba (bug "clic pero no selecciona").

Siembra una categoria propia en localStorage (como si se hubiera creado en otra sesion),
corre loadCustomCategories() y exige que nombre + seleccion funcionen. No requiere login:
solo el componente Alpine. Sale 1 si algo falla.
"""
import sys, os, socket, threading, http.server, functools
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv


TEST_JS = r"""
() => {
  const out = { steps: [], ok: true };
  const fail = (m) => { out.ok = false; out.steps.push('FAIL: ' + m); };
  const pass = (m) => { out.steps.push('ok: ' + m); };
  const c = window.Alpine.$data(document.querySelector('#app'));
  if (!c) return { ok:false, steps:['no Alpine component'] };
  if (typeof CAT_MAP === 'undefined') return { ok:false, steps:['CAT_MAP no visible en el realm'] };

  const KEY='custom_qatest1', LABEL='Comida rapida QA', EMOJI='🌮';

  // Estado "reload fresco": la categoria propia solo vive en localStorage, no en CAT_MAP.
  localStorage.setItem('zepo:custom-cats', JSON.stringify({
    expense:[{key:KEY, emoji:EMOJI, label:LABEL, color:'#C2553F'}], income:[]
  }));
  c.categories = c.categories.filter(x => x.key !== KEY);
  delete CAT_MAP[KEY];

  c.loadCustomCategories();

  // 1. queda en el grid
  if (c.categories.some(x => x.key===KEY)) pass('categoria en el grid'); else fail('categoria NO esta en el grid');

  // 2. CAT_MAP + getCat* resuelven el nombre real (bug nombres del dashboard)
  if (CAT_MAP[KEY]) pass('CAT_MAP registra la propia'); else fail('CAT_MAP NO tiene la propia');
  if (c.getCatLabel(KEY) === LABEL) pass('getCatLabel = nombre real'); else fail('getCatLabel = "' + c.getCatLabel(KEY) + '" (esperaba "' + LABEL + '")');
  if (c.getCatEmoji(KEY) === EMOJI) pass('getCatEmoji = emoji real'); else fail('getCatEmoji = ' + c.getCatEmoji(KEY));

  // 3. categoryBreakdown (dashboard "Por categoria") usaria el nombre real, no el slug
  const lbl = (CAT_MAP[KEY] && CAT_MAP[KEY].label) || KEY;
  if (lbl === LABEL) pass('label del breakdown = nombre real'); else fail('breakdown mostraria "' + lbl + '"');

  // 4. seleccion en un item detectado (bug: clic no selecciona)
  c.parsedItems = [{ description:'tacos', amount:5, category:'other', date:'2026-07-02', is_income:false, emoji:'✨', label:'Otro', color:'#948E80' }];
  c.updateParsedItemCat(0, KEY);
  if (c.parsedItems[0].category === KEY) pass('updateParsedItemCat selecciona la propia'); else fail('updateParsedItemCat NO selecciono (category=' + c.parsedItems[0].category + ')');
  if (c.parsedItems[0].label === LABEL) pass('el item toma el nombre real'); else fail('item label = ' + c.parsedItems[0].label);

  // 5. robustez: aunque falte en CAT_MAP, cae al array del grid y re-registra
  delete CAT_MAP[KEY];
  c.parsedItems[0].category = 'other';
  c.updateParsedItemCat(0, KEY);
  if (c.parsedItems[0].category === KEY) pass('fallback al grid cuando falta en CAT_MAP'); else fail('fallback fallo (category=' + c.parsedItems[0].category + ')');

  return out;
}
"""


def main():
    port = free_port(); serve(port)
    url = f"http://127.0.0.1:{port}/index.html"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1500)
        page.wait_for_function(
            "()=>window.Alpine && document.querySelector('#app') && window.Alpine.$data(document.querySelector('#app'))",
            timeout=15000)
        res = page.evaluate(TEST_JS)
        browser.close()
    for s in res.get("steps", []):
        print("  " + s)
    if res.get("ok"):
        print("[OK] categorias propias resuelven tras reload (nombres + seleccion)")
        return 0
    print("[FALLA] categorias propias tras reload")
    return 1


if __name__ == "__main__":
    sys.exit(main())
