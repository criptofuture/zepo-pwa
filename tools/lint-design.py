#!/usr/bin/env python3
"""
lint-design.py — Guardrail anti-regresion de la marca editorial Zepo (V2.0 Bricolage).

Que hace:
  - FAIL (exit 1): introduces colores neon de la marca vieja, tokens que no existen,
    o el bug del toggle x-show + :style con display.
  - WARN (exit 0): quedan literales rgba() de la paleta vieja (success/danger/warning)
    que idealmente deberian migrar a triplets de token. No bloquea el deploy.

La barra de dev (DEV TOOLBAR — solo zepo-staging, hasta EOF) esta en allowlist:
nunca se sirve en produccion (gated por IS_STAGING), conserva su estetica neon a proposito.

Uso:
  python tools/lint-design.py            # lint index.html
  python tools/lint-design.py archivo.html
"""
import re
import sys
import os

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- Patrones que BLOQUEAN (neon de marca vieja, fuera de la dev toolbar) ---
FAIL_PATTERNS = [
    (re.compile(r'#00F0FF', re.I), "neon cyan #00F0FF (usar var(--cyan) / token editorial)"),
    (re.compile(r'#7000FF', re.I), "neon purple #7000FF (usar var(--purple) / token editorial)"),
    (re.compile(r'#B794F6', re.I), "neon lavender #B794F6 (solo permitido en dev toolbar)"),
    (re.compile(r'rgba\(\s*0\s*,\s*240\s*,\s*255'), "rgba neon cyan (usar rgba(var(--c-brand-rgb),a))"),
    (re.compile(r'rgba\(\s*112\s*,\s*0\s*,\s*255'), "rgba neon purple (usar rgba(var(--c-accent-rgb),a))"),
    (re.compile(r'var\(--card\)'), "var(--card) NO existe (usar var(--surface))"),
    (re.compile(r'var\(--bg-dark\)'), "var(--bg-dark) NO existe"),
    (re.compile(r'var\(--primary\)'), "var(--primary) NO existe (usar var(--cyan))"),
    (re.compile(r'var\(--secondary\)'), "var(--secondary) NO existe"),
    (re.compile(r'var\(--accent\)'), "var(--accent) NO existe (usar var(--purple) / var(--c-accent))"),
]

# Bug del toggle: x-show="!editingBatch" en el mismo elemento que :style con display
TOGGLE_BUG = re.compile(r'x-show="!editingBatch"[^>]*:style="[^"]*display')

# --- Patrones que AVISAN (residuo de paleta vieja, no bloquea) ---
WARN_PATTERNS = [
    (re.compile(r'rgba\(\s*0\s*,\s*229\s*,\s*160'), "rgba mint viejo (success) — migrar a triplet de token"),
    (re.compile(r'rgba\(\s*255\s*,\s*107\s*,\s*107'), "rgba rojo viejo (danger) — migrar a triplet de token"),
    (re.compile(r'rgba\(\s*255\s*,\s*184\s*,\s*0'), "rgba ambar viejo (warning) — migrar a triplet de token"),
]

DEV_TOOLBAR_MARK = "DEV TOOLBAR"


def find_devtoolbar_start(lines):
    for i, line in enumerate(lines):
        if DEV_TOOLBAR_MARK in line:
            return i
    return len(lines)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    if not os.path.exists(path):
        print(f"❌ No existe: {path}")
        return 2

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    dev_start = find_devtoolbar_start(lines)

    fails = []
    warns = []
    for idx, line in enumerate(lines):
        if idx >= dev_start:  # dev toolbar + lo que sigue: allowlist
            break
        ln = idx + 1
        for rx, msg in FAIL_PATTERNS:
            if rx.search(line):
                fails.append((ln, msg, line.strip()[:90]))
        if TOGGLE_BUG.search(line):
            fails.append((ln, "toggle x-show + :style con display (rompe flex)", line.strip()[:90]))
        for rx, msg in WARN_PATTERNS:
            if rx.search(line):
                warns.append((ln, msg))

    if warns:
        print(f"⚠️  {len(warns)} residuo(s) de paleta vieja (no bloquea):")
        # agrupar por mensaje para no inundar
        from collections import Counter
        c = Counter(m for _, m in warns)
        for msg, n in c.most_common():
            print(f"    · {n}x  {msg}")

    if fails:
        print(f"\n🚨 {len(fails)} regresion(es) de marca — DEPLOY BLOQUEADO:")
        for ln, msg, snippet in fails:
            print(f"    L{ln}: {msg}")
            print(f"          {snippet}")
        print(f"\n(La dev toolbar desde L{dev_start + 1} esta en allowlist.)")
        return 1

    print(f"\n✅ Sin regresiones de marca. ({dev_start} lineas revisadas, dev toolbar omitida.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
