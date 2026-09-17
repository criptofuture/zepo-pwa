#!/usr/bin/env python3
"""
Candado: ningun script de tools/ lee claves de una ruta fija que solo existe en una carpeta.

El 16-sep-2026, corriendo qa-all.py desde un worktree fuera del monorepo, 5 pruebas se
cayeron con FileNotFoundError antes de probar nada: 4 leian el config.json de la skill
supabase (retirada) y 1 buscaba config.json dos carpetas arriba del PWA. Las claves se leen
con tools/qa_cfg.py: load() para config.json y supabase_token()/mgmt() para la Management API.

USO:  python tools/qa-rutas-lint.py      Sale 1 si encuentra alguna ruta prohibida.
"""
import os, re, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
PROHIBIDAS = [
    (re.compile(r"skills/supabase/"), "config.json de la skill supabase (retirada): usa qa_cfg.mgmt()"),
    (re.compile(r'"\.\.",\s*"\.\.",\s*(?:"\.\.",\s*)*"config\.json"'),
     "config.json a N carpetas fijas: usa qa_cfg.load()"),
]

malos = []
for raiz, _, archivos in os.walk(TOOLS):
    for nombre in archivos:
        ruta = os.path.join(raiz, nombre)
        if not nombre.endswith(".py") or ruta == os.path.abspath(__file__):
            continue
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for n, linea in enumerate(fh, 1):
                for rx, motivo in PROHIBIDAS:
                    if rx.search(linea):
                        malos.append(f"  {os.path.relpath(ruta, TOOLS)}:{n}  {motivo}")

if malos:
    print("FALLA: rutas fijas de claves\n" + "\n".join(malos))
    sys.exit(1)
print("OK: ningun script lee claves de una ruta fija")
