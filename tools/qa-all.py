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
    ("E2E editar cobro + agregar persona", ["python", os.path.join(TOOLS, "qa-e2e-edit-split.py")]),
    ("E2E editar 'Debo' quitar division",  ["python", os.path.join(TOOLS, "qa-e2e-remove-split.py")]),
    ("Parpadeo Cuentas (keys duplicadas)", ["python", os.path.join(TOOLS, "qa-cuentas-flicker.py")]),
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
