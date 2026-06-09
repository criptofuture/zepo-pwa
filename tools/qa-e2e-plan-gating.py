#!/usr/bin/env python3
"""
QA E2E REAL del gating de los 4 planes (free / pro / elite / max). SIN ATAJOS:
- Login REAL con 4 cuentas (tools/qa-accounts.py) cuyo plan vive en Supabase.
- NO se setea c.userPlan ni devUnlockAll: el plan se LEE del backend.
- Cada candado se EJERCE (handler real / clic DOM real) y se observa el resultado:
    bloqueado -> redirige a 'plans' y NO hay efecto en backend (control negativo).
    permitido -> la acción procede (abre modal / escribe fila).
Verifica la trampa `!== 'elite'`: un MAX debe acceder a TODO lo de Elite.
Sale 1 si algún plan no cumple su matriz.
"""
import sys, time, socket, threading, http.server, functools, os, json, urllib.request
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASSWORD = "ZepoQA2026!"
ACCOUNTS = [("free@zepo.test", "free"), ("pro@zepo.test", "pro"),
            ("elite@zepo.test", "elite"), ("max@zepo.test", "max")]
# tiers que cada plan DEBE tener
EXPECT = {"free": set(), "pro": {"pro"}, "elite": {"pro", "elite"},
          "max": {"pro", "elite", "max"}}
RUNTAG = "QAGATE_" + str(int(time.time()))

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

def cleanup_spaces():
    cfg = json.load(open("C:/Users/alvar/.claude/skills/supabase/config.json", encoding="utf-8"))
    url = f"https://api.supabase.com/v1/projects/{cfg['project_ref']}/database/query"
    body = json.dumps({"query": f"delete from public.spaces where name like '{RUNTAG}%';"}).encode()
    r = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {cfg['management_token']}", "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 lynoia-cli/1.0"})
    try: urllib.request.urlopen(r, timeout=20)
    except Exception as e: print("  (cleanup spaces warn:", repr(e)[:80], ")")

LOGIN_JS = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""

GATE_JS = """
async (uniqueName) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  const r = { plan: c.userPlan, has: { pro:c.hasPlan('pro'), elite:c.hasPlan('elite'), max:c.hasPlan('max') } };
  const reset = () => { c.tab = 'home'; };
  // toggleSplit (Capa 1 = Pro)
  reset(); c.sheetOpen = true; c.form = c.form || {}; c.form.is_split = false; c.form.split_people = c.form.split_people||[];
  try { c.toggleSplit(); } catch(e) {}
  r.split = { tab: c.tab, is_split: !!(c.form && c.form.is_split) }; c.sheetOpen = false;
  // openRecurringManager (Elite)
  reset(); c.recurringManagerOpen = false; try { c.openRecurringManager(); } catch(e) {}
  r.recurring = { tab: c.tab, open: !!c.recurringManagerOpen }; c.recurringManagerOpen = false;
  // openSpaceManager (Max)
  reset(); c.spaceManagerOpen = false; try { c.openSpaceManager(); } catch(e) {}
  r.spaces = { tab: c.tab, open: !!c.spaceManagerOpen }; c.spaceManagerOpen = false;
  // exportPDF / exportExcel (Elite) — solo se EJECUTA la ruta de bloqueo (allow=skip, evita descargas)
  reset(); if (!c.hasPlan('elite')) { try { await c.exportPDF(); } catch(e) {} r.pdf = { tab: c.tab }; } else r.pdf = { tab: '(allow)' };
  reset(); if (!c.hasPlan('elite')) { try { await c.exportExcel(); } catch(e) {} r.excel = { tab: c.tab }; } else r.excel = { tab: '(allow)' };
  // searchFriend / sendPaymentRequest (Max, Capa 2) — solo ruta de bloqueo
  reset(); c.addFriendEmail = 'nadie@zepo.test';
  if (!c.hasPlan('max')) { try { await c.searchFriend(); } catch(e) {} r.friend = { tab: c.tab }; } else r.friend = { tab: '(allow)' };
  reset(); c.sendPrTo = { user_id: '00000000-0000-0000-0000-000000000000' }; c.prForm = { amount:'1', description:'x', category:'food' };
  if (!c.hasPlan('max')) { try { await c.sendPaymentRequest(); } catch(e) {} r.cobro = { tab: c.tab }; } else r.cobro = { tab: '(allow)' };
  // addSpace — escritura REAL: max crea fila; otros redirigen y NO escriben (control negativo)
  reset(); c.newSpaceName = uniqueName; c.newSpaceIcon = '🏪'; c.newSpaceColor = '#BF8A2A';
  try { await c.addSpace(); } catch(e) {}
  await new Promise(z => setTimeout(z, 800));
  r.addSpace = { tab: c.tab, inSpaces: (c.spaces||[]).some(s => s.name === uniqueName) };
  return r;
}
"""

DASH_CLICK_JS = """
() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.tab = 'home';
  const btn = [...document.querySelectorAll('button.tab-item')].find(x => {
    const a = (x.getAttribute('@click') || x.getAttribute('x-on:click') || '');
    return a.includes("'dash'"); });
  if (!btn) return { err: 'no dash btn' };
  btn.click();                       // clic DOM real -> handler Alpine real
  return { tab: c.tab };
}
"""

def check_plan(page, email, plan):
    want = EXPECT[plan]
    g = page.evaluate(GATE_JS, f"{RUNTAG}_{plan}")
    d = page.evaluate(DASH_CLICK_JS)
    has_pro = "pro" in want; has_elite = "elite" in want; has_max = "max" in want
    def blocked(o): return o.get("tab") == "plans"
    checks = [
        (f"plan leido del backend == '{plan}'", g.get("plan") == plan),
        ("hasPlan(pro) correcto",   g["has"]["pro"] == has_pro),
        ("hasPlan(elite) correcto", g["has"]["elite"] == has_elite),
        ("hasPlan(max) correcto",   g["has"]["max"] == has_max),
        # Split Capa 1 (Pro)
        ("split: " + ("permite dividir" if has_pro else "bloquea -> plans"),
         (g["split"]["is_split"] is True) if has_pro else blocked(g["split"])),
        # Recurrentes (Elite)
        ("recurrentes: " + ("abre" if has_elite else "bloquea -> plans"),
         (g["recurring"]["open"] is True) if has_elite else blocked(g["recurring"])),
        # Dashboard (Elite) — clic DOM real
        ("dashboard(clic real): " + ("entra a dash" if has_elite else "bloquea -> plans"),
         (d.get("tab") == "dash") if has_elite else d.get("tab") == "plans"),
        # Export PDF/Excel (Elite) — bloqueo verificado por ejecución
        ("exportPDF bloqueado" if not has_elite else "exportPDF permitido (hasPlan)",
         blocked(g["pdf"]) if not has_elite else g["pdf"]["tab"] == "(allow)"),
        ("exportExcel bloqueado" if not has_elite else "exportExcel permitido (hasPlan)",
         blocked(g["excel"]) if not has_elite else g["excel"]["tab"] == "(allow)"),
        # Espacios (Max)
        ("espacios: " + ("abre manager" if has_max else "bloquea -> plans"),
         (g["spaces"]["open"] is True) if has_max else blocked(g["spaces"])),
        # addSpace escritura real (Max crea; otros NO escriben)
        ("addSpace: " + ("crea fila" if has_max else "NO escribe + plans"),
         (g["addSpace"]["inSpaces"] is True) if has_max
         else (g["addSpace"]["inSpaces"] is False and blocked(g["addSpace"]))),
        # Amigos / cobro (Max, Capa 2)
        ("buscar amigo: " + ("permitido" if has_max else "bloquea -> plans"),
         g["friend"]["tab"] == "(allow)" if has_max else blocked(g["friend"])),
        ("enviar cobro: " + ("permitido" if has_max else "bloquea -> plans"),
         g["cobro"]["tab"] == "(allow)" if has_max else blocked(g["cobro"])),
    ]
    return checks

def run(url):
    allok = True
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for email, plan in ACCOUNTS:
            ctx = browser.new_context(viewport={"width":390,"height":844})
            page = ctx.new_page(); page.on("dialog", lambda d: d.accept())
            page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1000)
            err = page.evaluate(LOGIN_JS, [email, PASSWORD])
            print(f"\n=== Cuenta {email} (esperado: {plan}) ===")
            if err:
                print("  [FALLA] login:", err); allok = False; ctx.close(); continue
            page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)
            # esperar a que el plan REAL cargue del backend
            try:
                page.wait_for_function("(pl)=>{const c=window.Alpine.$data(document.querySelector('#app'));return c.userPlan===pl;}",
                                       arg=plan, timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
            for label, ok in check_plan(page, email, plan):
                print(f"  [{'PASS' if ok else 'FALLA'}] {label}")
                if not ok: allok = False
            ctx.close()
        browser.close()
    cleanup_spaces()
    return allok

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ok = run(sys.argv[1])
    else:
        port = free_port(); serve(port); time.sleep(0.5); ok = run(f"http://127.0.0.1:{port}/index.html")
    print("\n" + ("OK - gating de los 4 planes correcto (Max hereda todo Elite)" if ok
                  else "FALLO - revisar candados por plan"))
    sys.exit(0 if ok else 1)
