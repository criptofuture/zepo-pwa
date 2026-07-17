#!/usr/bin/env python3
"""
GATE DE QA DE ZEPO — corre TODO antes de declarar "listo" / commitear / promover.

Por que existe: en esta sesion varios bugs se colaron porque las pruebas eran con datos
falsos o cubrian solo UNA variante (agregar persona, pero no quitar la division). Este
runner ejecuta, en orden, todas las verificaciones REALES (sintaxis, marca, layout/teclado
y E2E contra Supabase con la cuenta demo) y da un veredicto unico.

USO:
    python tools/qa-all.py
Sale 0 si TODO pasa; 1 si algo falla (apto para pre-commit / pre-deploy / CI).

REGLA (ver QA-PROTOCOL.md): cuando crees o modifiques un flujo, agrega/extiende un E2E
aqui que ejerza CADA boton y CADA variable de esa pantalla (incl. el camino inverso:
crear Y borrar, activar Y desactivar, con 1 y con N), y deja este gate en verde.
"""
import sys, subprocess, os, time

TOOLS = os.path.dirname(os.path.abspath(__file__))

def parse_check():
    code = r'''const fs=require("fs");const h=fs.readFileSync("index.html","utf8");
const re=/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;let m,i=0,b=0;
while((m=re.exec(h))){i++;const c=m[1];if(!c.trim())continue;try{new Function(c)}catch(e){b++;console.log("script #"+i+": "+e.message)}}
process.exit(b>0?1:0);'''
    r = subprocess.run(["node", "-e", code], cwd=os.path.dirname(TOOLS))
    return r.returncode == 0

CHECKS = [
    ("Sintaxis JS (parse)",            parse_check),
    ("Marca / tokens (lint-design)",   ["python", os.path.join(TOOLS, "lint-design.py"), "index.html"]),
    ("Keys x-for por-persona (lint)",  ["python", os.path.join(TOOLS, "qa-keys-lint.py")]),
    ("Layout teclado/split (5 perfiles)", ["python", os.path.join(TOOLS, "qa-keyboard.py")]),
    ("E2E CRUD gasto (alta/editar/borrar)", ["python", os.path.join(TOOLS, "qa-e2e-crud.py")]),
    ("E2E editar cobro + agregar persona", ["python", os.path.join(TOOLS, "qa-e2e-edit-split.py")]),
    ("E2E proporciones desiguales (guardar/cuentas/editar/historico)", ["python", os.path.join(TOOLS, "qa-e2e-split-proportions.py")]),
    ("E2E restante del split (asignar/dividir/fijado a mano)", ["python", os.path.join(TOOLS, "qa-e2e-split-restante.py")]),
    ("E2E editar 'Debo' quitar division",  ["python", os.path.join(TOOLS, "qa-e2e-remove-split.py")]),
    ("Parpadeo Cuentas (keys duplicadas)", ["python", os.path.join(TOOLS, "qa-cuentas-flicker.py")]),
    ("E2E multi-item / batch",         ["python", os.path.join(TOOLS, "qa-e2e-batch.py")]),
    ("E2E importar + quitar + dividir (suma restante)", ["python", os.path.join(TOOLS, "qa-e2e-import-split.py")]),
    ("E2E import tabular determinista (Excel/CSV sin IA)", ["python", os.path.join(TOOLS, "qa-e2e-import-tabular.py")]),
    ("E2E presupuestos",               ["python", os.path.join(TOOLS, "qa-e2e-budgets.py")]),
    ("E2E herencia de presupuestos mes a mes", ["python", os.path.join(TOOLS, "qa-e2e-budget-carry.py")]),
    ("Smoke todas las pantallas (sin errores)", ["python", os.path.join(TOOLS, "qa-smoke-screens.py")]),
    ("E2E solicitudes cobro (aceptar/rechazar/pagar)", ["python", os.path.join(TOOLS, "qa-e2e-payreq.py")]),
    ("E2E registrar cobro aceptado sin registrar", ["python", os.path.join(TOOLS, "qa-e2e-register-accepted.py")]),
    ("E2E retirar gasto dividido (borrar retira cobro+espejo)", ["python", os.path.join(TOOLS, "qa-e2e-retract-split.py")]),
    ("E2E pedir revision + cancelar cobro (vuelve a 100%)", ["python", os.path.join(TOOLS, "qa-e2e-cancel-cobro.py")]),
    ("E2E amigos (aceptar/rechazar conexion)", ["python", os.path.join(TOOLS, "qa-e2e-friends.py")]),
    ("E2E onboarding (primer gasto/presupuesto/finalizar)", ["python", os.path.join(TOOLS, "qa-e2e-onboarding.py")]),
    ("E2E nombres de contacto (anti-UUID)", ["python", os.path.join(TOOLS, "qa-e2e-names.py")]),
    ("E2E Contactos/Amigos (saldo neto + apodo)", ["python", os.path.join(TOOLS, "qa-e2e-contactos.py")]),
    ("E2E gating de planes (free/pro/elite/max)", ["python", os.path.join(TOOLS, "qa-e2e-plan-gating.py")]),
    ("E2E Patrimonio: ahorro acumulado + total", ["python", os.path.join(TOOLS, "qa-e2e-pat-savings.py")]),
    ("E2E borrar ingreso desde Historial + etiquetas", ["python", os.path.join(TOOLS, "qa-e2e-history-delete.py")]),
    ("E2E categorias propias tras reload (nombres + seleccion)", ["python", os.path.join(TOOLS, "qa-e2e-custom-cat.py")]),
    ("E2E categorias propias SYNC nube (sobrevive device nuevo)", ["python", os.path.join(TOOLS, "qa-e2e-custom-cat-sync.py")]),
    ("E2E carrera categoria manual vs IA tardia", ["python", os.path.join(TOOLS, "qa-e2e-cat-race.py")]),
    ("E2E UI v175 (config + cuenta ingreso + chips split)", ["python", os.path.join(TOOLS, "qa-e2e-v175-ui.py")]),
    ("E2E gesto atras = un nivel (init unico, modales, tabs)", ["python", os.path.join(TOOLS, "qa-e2e-back-nav.py")]),
    ("E2E Zepi companion (chat, scan, candado Max)", ["python", os.path.join(TOOLS, "qa-e2e-zepi.py")]),
    ("E2E Journey 30 dias + trials (misiones, reclamo, anti-trampa)", ["python", os.path.join(TOOLS, "qa-e2e-journey.py")]),
    # Invariantes de dinero entre pantallas (campana de calculos, jul-2026). Cada uno deriva
    # la aritmetica por su cuenta desde la BD y lleva controles negativos.
    ("E2E invariantes Dashboard/Home/Historial (semana, balance, drill-down)", ["python", os.path.join(TOOLS, "qa-e2e-invariantes-dash.py")]),
    ("E2E invariantes presupuestos/espacios/patrimonio", ["python", os.path.join(TOOLS, "qa-e2e-invariantes-presup.py")]),
    ("E2E limites (tope 1000 filas paginado + recurrente dividido)", ["python", os.path.join(TOOLS, "qa-e2e-invariantes-limites.py")]),
    ("E2E invariantes extra (mes/año/historial/adelanto/PDF/borrar espacio)", ["python", os.path.join(TOOLS, "qa-e2e-invariantes-extra.py")]),
]

def main():
    root = os.path.dirname(TOOLS)
    results = []
    t0 = time.time()
    for name, runner in CHECKS:
        print(f"\n=== {name} ===")
        if callable(runner):
            ok = runner()
        else:
            r = subprocess.run(runner, cwd=root)
            ok = r.returncode == 0
        results.append((name, ok))
    dt = int(time.time() - t0)
    print("\n" + "=" * 52)
    print("  RESUMEN QA ZEPO  ({}s)".format(dt))
    print("=" * 52)
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FALLA'}] {name}")
    allok = all(ok for _, ok in results)
    print("=" * 52)
    print("  " + ("TODO VERDE — apto para commit/deploy" if allok
                  else "HAY FALLAS — NO commitear/promover hasta arreglar"))
    return 0 if allok else 1

if __name__ == "__main__":
    sys.exit(main())
