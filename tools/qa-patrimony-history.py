#!/usr/bin/env python3
"""WebKit (motor iOS): certifica el histórico de patrimonio (Fase 3).
Siembra snapshots + items EN MEMORIA (determinista, sin escribir a la BD):
 [1] patHistory = snapshots mensuales + mes actual con el NETO EN VIVO (reemplaza el stale).
 [2] DOM con >=2 puntos: tarjeta con polyline + delta + ejes mes inicial/final.
 [3] 1 solo punto: muestra "vuelve el próximo mes", sin polyline.
 [4] 0 puntos (sin items): no se dibuja la tarjeta."""
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
SEED_HISTORY = """async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.showWelcomeCarousel=false; c.showOnbV2=false; c.tab='patrimonio'; c.patSheetOpen=false;
  // Neto en vivo = 50000 (bien) + 10000 (inversión) = 60000
  c.patrimonyItems = [
    { id:'qa-house', kind:'asset',      name:'Casa',  current_value:50000, status:'active', sort_order:0 },
    { id:'qa-fund',  kind:'investment', name:'Fondo', current_value:10000, status:'active', sort_order:1 },
  ];
  // net_worth como string (la BD entrega NUMERIC como string) — verifica el Number().
  c.patSnapshots = [
    { snapshot_month:'2026-03-01', net_worth:'40000' },
    { snapshot_month:'2026-04-01', net_worth:'45000' },
    { snapshot_month:'2026-05-01', net_worth:'52000' },
    { snapshot_month:'2026-06-01', net_worth:'55000' },  // STALE: patHistory debe usar 60000 (vivo)
  ];
  return {
    net: c.patNetWorth, count: c.patItemCount, histLen: c.patHistory.length,
    firstVal: c.patHistory[0].value, lastVal: c.patHistory[c.patHistory.length-1].value,
    chart: c.patChart ? { line: c.patChart.line, first: c.patChart.firstLabel, last: c.patChart.lastLabel } : null,
    delta: c.patHistoryDelta,
  };
}"""
READ_DOM = """() => {
  const vis = el => el && el.getBoundingClientRect().height>2 && el.offsetParent!==null;
  const poly  = document.querySelector('.pat-chart polyline');
  const delta = document.querySelector('.pat-chart-delta');
  const axis  = [...document.querySelectorAll('.pat-chart-axis span')];
  const soon  = document.querySelector('.pat-chart-soon');
  return {
    polyVisible: vis(poly), polyPoints: poly ? (poly.getAttribute('points')||'').trim().split(' ').length : 0,
    deltaVisible: vis(delta), deltaTxt: delta ? delta.textContent.trim() : null,
    axisTxt: axis.map(s=>s.textContent.trim()), soonPresent: !!soon,
  };
}"""
SEED_ONE = """async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.patSnapshots = [];
  c.patrimonyItems = [ { id:'qa-1', kind:'asset', name:'Auto', current_value:8000, status:'active', sort_order:0 } ];
  return { histLen: c.patHistory.length };
}"""
SEED_EMPTY = """async () => {
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.patSnapshots = []; c.patrimonyItems = [];
  return { histLen: c.patHistory.length };
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

        s = page.evaluate(SEED_HISTORY); page.wait_for_timeout(500)
        print("\n[1] patHistory (4 snapshots, mes actual reemplazado por el neto vivo 60000):")
        print("   ", s)
        if s["net"] != 60000:
            print("   [FALLA] patNetWorth esperado 60000, got", s["net"]); failures += 1
        elif s["histLen"] != 4:
            print("   [FALLA] patHistory esperado 4 puntos, got", s["histLen"]); failures += 1
        elif s["firstVal"] != 40000 or s["lastVal"] != 60000:
            print("   [FALLA] primer/último esperado 40000/60000, got", s["firstVal"], s["lastVal"]); failures += 1
        elif not (s["chart"] and s["chart"]["first"] and s["chart"]["last"]):
            print("   [FALLA] patChart sin geometría/labels"); failures += 1
        elif not (s["delta"] and s["delta"]["up"] and abs(s["delta"]["abs"] - 20000) < 0.01):
            print("   [FALLA] delta esperado +20000 up, got", s["delta"]); failures += 1
        else:
            print("   [PASS] 4 pts, vivo reemplaza stale (60000), delta +20000, labels", s["chart"]["first"], "→", s["chart"]["last"])

        dom = page.evaluate(READ_DOM)
        print("\n[2] DOM (polyline + delta + ejes):")
        print("   ", dom)
        if not (dom["polyVisible"] and dom["polyPoints"] >= 4):
            print("   [FALLA] polyline no visible o sin 4 puntos"); failures += 1
        elif not (dom["deltaVisible"] and dom["deltaTxt"] and "▲" in dom["deltaTxt"]):
            print("   [FALLA] delta no visible o sin flecha de subida"); failures += 1
        elif len(dom["axisTxt"]) != 2 or not all(dom["axisTxt"]):
            print("   [FALLA] ejes (mes inicial/final) incompletos"); failures += 1
        else:
            print("   [PASS] polyline", dom["polyPoints"], "pts | delta", dom["deltaTxt"], "| ejes", dom["axisTxt"])
        page.screenshot(path=os.path.join(os.environ.get("TEMP","."), "zepo-patrimony-history.png"))

        one = page.evaluate(SEED_ONE); page.wait_for_timeout(400)
        d1 = page.evaluate(READ_DOM)
        print("\n[3] 1 solo punto (sin con qué comparar):")
        print("   ", one, d1)
        if one["histLen"] != 1:
            print("   [FALLA] esperado 1 punto, got", one["histLen"]); failures += 1
        elif not d1["soonPresent"]:
            print("   [FALLA] no muestra el mensaje 'vuelve el próximo mes'"); failures += 1
        elif d1["polyVisible"]:
            print("   [FALLA] no debería dibujar polyline con 1 punto"); failures += 1
        else:
            print("   [PASS] muestra punto de partida, sin polyline")

        emp = page.evaluate(SEED_EMPTY); page.wait_for_timeout(400)
        d0 = page.evaluate(READ_DOM)
        print("\n[4] 0 puntos (sin items):")
        print("   ", emp, d0)
        if emp["histLen"] != 0:
            print("   [FALLA] esperado 0 puntos, got", emp["histLen"]); failures += 1
        elif d0["soonPresent"] or d0["polyVisible"]:
            print("   [FALLA] no debería dibujar tarjeta de gráfico sin datos"); failures += 1
        else:
            print("   [PASS] sin tarjeta de gráfico")

        ctx.close(); wk.close()
    print("\n=== %s ===" % ("TODO PASS" if failures==0 else f"{failures} FALLAS"))
    print("screenshot: %TEMP%/zepo-patrimony-history.png")
    return failures

if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
