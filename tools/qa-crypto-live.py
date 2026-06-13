#!/usr/bin/env python3
"""WebKit (motor iOS): certifica cripto con precio en vivo en Patrimonio.
fetch a CoinGecko STUBBEADO (determinista, sin red):
 [1] 0.5 BTC @ $60.000 -> current_value = $30.000 (cantidad x precio).
 [2] DOM: badge "en vivo" + item muestra "0.5 BTC · precio en vivo".
 [3] fallback: si el fetch falla, mantiene el valor previo (nunca $0).
 [4] form: el toggle Cripto revela Moneda+Cantidad y oculta el valor manual."""
import os, socket, threading, http.server, functools
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

PREP = """() => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
}"""
LOGIN = """async ([email, password]) => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.devUnlockAll = true;
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}"""
STUB_OK = """() => {
  window.__origFetch = window.fetch;
  window.fetch = (u, o) => {
    if (String(u).includes('api.coingecko.com'))
      return Promise.resolve(new Response(JSON.stringify({ bitcoin: { usd: 60000 } }),
        { status:200, headers:{'Content-Type':'application/json'} }));
    return window.__origFetch(u, o);
  };
  try { localStorage.removeItem('zepo_crypto_prices'); } catch(e){}
}"""
STUB_FAIL = """() => {
  window.fetch = (u, o) => {
    if (String(u).includes('api.coingecko.com')) return Promise.reject(new Error('offline'));
    return window.__origFetch(u, o);
  };
  try { localStorage.removeItem('zepo_crypto_prices'); } catch(e){}
}"""
SEED_LIVE = """async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showWelcomeCarousel=false; c.showOnbV2=false; c.tab='patrimonio'; c.patSheetOpen=false;
  c.patrimonyItems = [
    { id:'qa-btc', kind:'investment', name:'Mi Bitcoin', coingecko_id:'bitcoin', symbol:'BTC', quantity:0.5, current_value:0, status:'active', sort_order:0 },
  ];
  await c.loadCryptoPrices(true);
  return { current_value:c.patrimonyItems[0].current_value, net:c.patNetWorth,
           hasCrypto:c.patHasCrypto, fresh:c.cryptoFreshLabel, at:c.cryptoPricesAt };
}"""
READ_DOM = """() => {
  const all = [...document.querySelectorAll('#app *')].filter(e => e.children.length === 0);
  const badge = all.find(e => /en vivo/.test(e.textContent));
  const meta  = all.find(e => /BTC . precio en vivo/.test(e.textContent));
  const vis = el => el && el.getBoundingClientRect().height>2 && el.offsetParent!==null;
  return {
    badge: badge ? { txt:badge.textContent.trim(), visible:vis(badge) } : null,
    meta:  meta  ? { txt:meta.textContent.trim(),  visible:vis(meta) }  : null
  };
}"""
SEED_FALLBACK = """async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.patrimonyItems = [
    { id:'qa-eth', kind:'investment', name:'Mi ETH', coingecko_id:'ethereum', symbol:'ETH', quantity:2, current_value:999, status:'active', sort_order:0 },
  ];
  await c.loadCryptoPrices(true);
  return { current_value:c.patrimonyItems[0].current_value };
}"""
FORM_CHECK = """() => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.openPatNew('investment'); c.patForm.is_crypto = true;
  return new Promise(res => setTimeout(() => {
    const sel = document.querySelector('select[x-model=\\"patForm.coingecko_id\\"]');
    const qty = document.querySelector('input[x-model=\\"patForm.quantity\\"]');
    const curr = document.querySelector('input[x-model=\\"patForm.current_value\\"]');
    const vis = el => el && el.getBoundingClientRect().height>2 && el.offsetParent!==null;
    res({ selVisible:vis(sel), qtyVisible:vis(qty), currHidden: !vis(curr) });
  }, 350));
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
        page.wait_for_timeout(1000)

        page.evaluate(STUB_OK)
        s = page.evaluate(SEED_LIVE); page.wait_for_timeout(500)
        print("\n[1] precio en vivo (0.5 BTC @ 60000):")
        print("   ", s)
        if abs(s["current_value"] - 30000) > 0.01:
            print("   [FALLA] current_value esperado 30000, got", s["current_value"]); failures += 1
        elif not (s["hasCrypto"] and s["at"] and s["fresh"]):
            print("   [FALLA] badge/estado en vivo no activo"); failures += 1
        else:
            print("   [PASS] 0.5 x 60000 = 30000 + badge en vivo")

        dom = page.evaluate(READ_DOM)
        print("\n[2] DOM (badge + meta del item):")
        print("   ", dom)
        if not (dom["badge"] and dom["badge"]["visible"]):
            print("   [FALLA] badge 'en vivo' no visible"); failures += 1
        elif not (dom["meta"] and dom["meta"]["visible"]):
            print("   [FALLA] meta '0.5 BTC · precio en vivo' no visible"); failures += 1
        else:
            print("   [PASS] badge:", dom["badge"]["txt"], "| meta:", dom["meta"]["txt"])
        page.screenshot(path=os.path.join(os.environ.get("TEMP","."), "zepo-crypto-live.png"))

        page.evaluate(STUB_FAIL)
        fb = page.evaluate(SEED_FALLBACK); page.wait_for_timeout(300)
        print("\n[3] fallback (fetch falla -> mantiene valor previo):")
        print("   ", fb)
        if abs(fb["current_value"] - 999) > 0.01:
            print("   [FALLA] esperado 999 (sin cambio), got", fb["current_value"]); failures += 1
        else:
            print("   [PASS] mantiene 999, no cae a 0")

        page.evaluate(STUB_OK)
        fc = page.evaluate(FORM_CHECK)
        print("\n[4] form: toggle cripto revela moneda+cantidad, oculta valor manual:")
        print("   ", fc)
        if not (fc["selVisible"] and fc["qtyVisible"] and fc["currHidden"]):
            print("   [FALLA] el form no alterna bien"); failures += 1
        else:
            print("   [PASS] Moneda+Cantidad visibles, Valor actual oculto")

        ctx.close(); wk.close()
    print("\n=== %s ===" % ("TODO PASS" if failures==0 else f"{failures} FALLAS"))
    print("screenshot: %TEMP%/zepo-crypto-live.png")
    return failures

if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
