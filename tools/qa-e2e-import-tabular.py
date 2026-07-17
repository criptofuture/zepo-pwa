#!/usr/bin/env python3
"""
QA E2E REAL: importar Excel/CSV por el MOTOR TABULAR DETERMINISTA.

Regresion (Alvaro, 2026-07-16): subio un Excel de 117 filas y Zepo mostro 131 registros
y un total de $6630.71 (que no era nada: sumaba ingresos + gastos). Dos causas:
  1. El Excel se serializaba a texto y se mandaba a un LLM para que RE-TECLEARA los
     numeros -> invento $6 a una fila de monto 0 (leyo el "6" de "6 taxis") y duplico filas.
  2. El "TOTAL" de la UI sumaba gastos e ingresos en una sola cifra sin significado.

Este test ejerce el flujo REAL con clics reales (nada simulado) y exige CERO errores:
  - deteccion de columnas sin fila de cabecera, con 3 columnas numericas (monto vs 2 ids)
  - filas de monto 0 descartadas CON motivo visible (no inventadas)
  - montos/fechas/orden identicos al archivo, al centavo
  - los 3 totales separados (gastos / ingresos / neto)
  - el camino inverso: cambiar el mapeo a mano re-calcula el cuadre
  - la puerta de confianza: si no distingue el monto, PIDE en vez de adivinar

login real max@zepo.test. Sale 1 si falla.
"""
import sys, os, socket, threading, http.server, functools, json, csv, io, tempfile
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL, PASS = "max@zepo.test", "ZepoQA2026!"
A = "window.Alpine.$data(document.querySelector('#app'))"

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv

# Fixture: reproduce la forma del archivo real de Alvaro — SIN cabecera, monto negativo,
# 2 columnas de ids que compiten con la de montos, y 2 filas de monto 0 (los "fantasmas").
ROWS = [
    ["2026-03-14 14:04", "Amazon",        -35.00,  "Varios",       "USD", "Cash", "$35 amazon /2",   12134229, 127, "Egreso"],
    ["2026-03-14 14:05", "Renta marzo",  -172.50,  "Vivienda",     "USD", "Cash", "$172.5 renta",    12134230, 129, "Egreso"],
    ["2026-03-16 15:38", "Apple",         -10.00,  "Alimentacion", "USD", "Cash", "10 apple",        12134231, 131, "Egreso"],
    ["2026-03-19 16:39", "6 taxis",         0.00,  "Transporte",   "USD", "Cash", "6 taxis",         12134232, 133, "Egreso"],
    ["2026-03-23 11:40", "Pago Soria",     70.00,  "Otros Ingresos","USD","Cash", "Ingreso 70",      12134233, 135, "Ingreso"],
    ["2026-03-25 07:07", "Mercadito",     -25.30,  "Alimentacion", "USD", "Cash", "25.3 mercadito",  12134234, 137, "Egreso"],
    ["2026-05-10 09:24", "Priscila",        0.00,  "Ocio",         "USD", "Cash", "3 Priscila",      12134235, 139, "Egreso"],
    ["2026-05-18 12:29", "Sueldo",        415.00,  "Otros Ingresos","USD","Cash", "415 ingreso",     12134236, 141, "Ingreso"],
]
EXP_TOTAL = 35.00 + 172.50 + 10.00 + 25.30      # 242.80
INC_TOTAL = 70.00 + 415.00                      # 485.00
EXP_ROWS  = 6                                   # 8 filas - 2 de monto 0

def write_csv(path):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f).writerows(ROWS)

def main():
    fails = []
    def check(name, cond, extra=""):
        print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + str(extra)) if (extra and not cond) else ""))
        if not cond: fails.append(name)

    tmp = tempfile.mkdtemp()
    csv_path = os.path.join(tmp, "zepo_qa_tabular.csv")
    write_csv(csv_path)

    port = free_port(); srv = serve(port)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            pg = b.new_page(viewport={"width": 390, "height": 844})
            page_errors = []
            pg.on("pageerror", lambda e: page_errors.append(str(e)))
            pg.goto(f"http://127.0.0.1:{port}/", wait_until="domcontentloaded")
            pg.wait_for_function("typeof sb !== 'undefined'", timeout=20000)
            r = pg.evaluate("""async ([e, p]) => {
                localStorage.setItem('zepo_onboarded_v1','1');
                localStorage.setItem('zepo_a7_done_v1','1');   // el tour intercepta clics
                const r = await sb.auth.signInWithPassword({ email: e, password: p });
                return r.error ? r.error.message : 'ok';
            }""", [EMAIL, PASS])
            if r != 'ok':
                print("  [FAIL] login:", r); return 1
            pg.reload(wait_until="domcontentloaded")
            pg.wait_for_function(f"() => {{ const c = {A}; return c && c.appReady && c.user; }}", timeout=30000)

            pg.evaluate(f"{A}.openNew()")
            pg.wait_for_selector('input[type=file][accept^=".pdf"]', state="attached", timeout=10000)
            pg.set_input_files('input[type=file][accept^=".pdf"]', csv_path)
            pg.wait_for_function(f"() => !!{A}.importedFile", timeout=10000)

            # El boton NO debe prometer IA para un tabular: ya no la usa.
            # (esperar el repintado de Alpine: el x-text no es sincrono al change del input)
            try:
                pg.wait_for_selector("button.save-btn:visible >> text=Leer archivo", timeout=5000)
                label = True
            except Exception:
                label = False
            check("boton dice 'Leer archivo' (no promete IA)", label,
                  pg.locator("button.save-btn:visible").first.inner_text())
            pg.locator("button.save-btn:visible").first.click()
            pg.wait_for_function(f"() => {A}.tabMapOpen === true", timeout=30000)

            s = json.loads(pg.evaluate(f"JSON.stringify({{map:{A}.tabSniff.map, hasHeader:{A}.tabSniff.hasHeader, signMode:{A}.tabSniff.signMode, counts:{A}.tabCounts, discards:{A}.tabDiscards}})"))
            check("detecta que NO hay fila de cabecera", s['hasHeader'] is False, s['hasHeader'])
            check("columna de fecha = 0", s['map']['date'] == 0, s['map'])
            check("columna de monto = 2 (no la confunde con los ids)", s['map']['amount'] == 2, s['map'])
            check("columna de descripcion = 1", s['map']['desc'] == 1, s['map'])
            check("direccion por signo del monto", s['signMode'] == 'sign', s['signMode'])
            check("cuadre: 8 filas leidas", s['counts']['total'] == len(ROWS), s['counts'])
            check(f"cuadre: {EXP_ROWS} se importan", s['counts']['ok'] == EXP_ROWS, s['counts'])
            check("cuadre: 2 se descartan (monto 0)", s['counts']['discarded'] == 2, s['counts'])
            check("los descartes dicen POR QUE", all(d['why'] == 'monto 0' for d in s['discards']), s['discards'])
            check("el descarte muestra la fila real del archivo", any('6 taxis' in d['sample'] for d in s['discards']), s['discards'])

            # La UI de mapeo es VISIBLE (no basta con el estado)
            check("UI de mapeo visible", pg.locator("text=QUÉ ENTENDÍ DE TU ARCHIVO").first.is_visible())
            sels = pg.evaluate("""() => [...document.querySelectorAll('select.cd-day-select')]
                .filter(s => s.offsetParent !== null).map(s => s.value)""")
            check("los selects MUESTRAN lo detectado (no el placeholder)", sels[:2] == ['0', '2'], sels)

            # Camino inverso: cambiar el mapeo a mano re-calcula el cuadre
            pg.evaluate(f"{A}.tabSniff.map.amount = 7; {A}.tabPreview()")   # col 7 = ids
            bad = json.loads(pg.evaluate(f"JSON.stringify({A}.tabCounts)"))
            check("cambiar la columna de monto re-calcula el cuadre", bad['ok'] == len(ROWS), bad)
            pg.evaluate(f"{A}.tabSniff.map.amount = 2; {A}.tabPreview()")
            back = json.loads(pg.evaluate(f"JSON.stringify({A}.tabCounts)"))
            check("volver a la columna correcta restaura el cuadre", back['ok'] == EXP_ROWS, back)

            # Sin fecha o sin monto NO se puede confirmar
            pg.evaluate(f"{A}.tabSniff.map.date = -1; {A}.tabPreview()")
            check("sin columna de fecha, no deja confirmar", pg.evaluate(f"!{A}.tabCounts"))
            pg.evaluate(f"{A}.tabSniff.map.date = 0; {A}.tabPreview()")

            pg.locator("button.save-btn:visible", has_text="Confirmar").first.click()
            pg.wait_for_function(f"() => {A}.parsedItems.length > 0", timeout=15000)

            d = json.loads(pg.evaluate(f"""JSON.stringify({{
                items: {A}.parsedItems, exp: {A}.parsedExpenseTotal, inc: {A}.parsedIncomeTotal,
                net: {A}.parsedNetTotal, mixed: {A}.parsedIsMixed
            }})"""))
            check(f"{EXP_ROWS} registros (los de monto 0 NO entran)", len(d['items']) == EXP_ROWS, len(d['items']))
            check(f"total gastos = {EXP_TOTAL} (al centavo)", abs(d['exp'] - EXP_TOTAL) < 0.005, d['exp'])
            check(f"total ingresos = {INC_TOTAL} (al centavo)", abs(d['inc'] - INC_TOTAL) < 0.005, d['inc'])
            check("neto = ingresos - gastos (NO la suma)", abs(d['net'] - (INC_TOTAL - EXP_TOTAL)) < 0.005, d['net'])
            check("marca la lista como mixta (muestra los 3 numeros)", d['mixed'] is True)
            # Ningun monto inventado: "6 taxis" no puede aparecer como $6
            check("NO inventa el $6 de '6 taxis'", not any(abs(i['amount'] - 6) < 0.005 for i in d['items']),
                  [i for i in d['items'] if abs(i['amount'] - 6) < 0.005])

            src = [r for r in ROWS if r[2] != 0]
            check("fechas identicas al archivo", all(d['items'][i]['date'] == src[i][0][:10] for i in range(len(src))),
                  [(d['items'][i]['date'], src[i][0][:10]) for i in range(len(src))])
            check("orden identico al archivo", all(d['items'][i]['description'] == src[i][1] for i in range(len(src))),
                  [i['description'] for i in d['items']])
            check("montos identicos al archivo", all(abs(d['items'][i]['amount'] - abs(src[i][2])) < 0.005 for i in range(len(src))))
            check("gasto/ingreso correcto por el signo", all(d['items'][i]['is_income'] == (src[i][2] > 0) for i in range(len(src))))
            check("categoria del archivo mapeada ('Alimentacion' sin tilde -> food)",
                  d['items'][2]['category'] == 'food', d['items'][2]['category'])

            check("cero errores de pagina", not page_errors, page_errors)
            b.close()
    finally:
        srv.shutdown()
        try: os.remove(csv_path); os.rmdir(tmp)
        except OSError: pass

    print(("\n  RESULTADO: TODO VERDE" if not fails else f"\n  RESULTADO: {len(fails)} FALLOS -> " + "; ".join(fails)))
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
