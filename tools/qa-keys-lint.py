#!/usr/bin/env python3
"""
Lint estatico de keys de x-for (Zepo). Atrapa la clase de bug "keys duplicadas ->
Alpine descarta filas / parpadeo".

Escanea index.html, lista cada <template x-for="... in FUENTE" :key="EXPR"> y marca
SOSPECHOSOS: keys que son SOLO un id (entry.id / c.id / x.id, con o sin ternario de
batch_id) SIN componente de persona ni indice. Esas son riesgosas cuando la FUENTE es
una lista DERIVADA por-persona (una fila por nombre del mismo registro -> mismo id ->
key duplicada).

No bloquea por si solo: imprime una tabla de triaje para revisar a mano cada FLAG.
USO:  python tools/qa-keys-lint.py
"""
import re, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")

def per_person_getters(text):
    """Detecta getters/metodos que producen filas por-persona (empujan _person) y los
    envoltorios que los referencian. Una lista x-for sobre una de estas fuentes con key
    'solo id' es bug seguro (filas con id repetido -> Alpine descarta)."""
    # bloques: SOLO miembros del componente Alpine (indentados a 4 espacios):
    #   "    get NAME() {"  o  "    NAME(args) {"  -> evita capturar if/forEach/callbacks
    blocks = {}
    for m in re.finditer(r"(?m)^    (?:get\s+)?([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{", text):
        name = m.group(1)
        start = m.end()
        depth, i = 1, start
        while i < len(text) and depth:
            ch = text[i]
            if ch == "{": depth += 1
            elif ch == "}": depth -= 1
            i += 1
        blocks.setdefault(name, "")
        blocks[name] += text[start:i]
    leaves = {n for n, body in blocks.items() if "_person" in body and "push" in body}
    # envoltorios: getters cuyo cuerpo referencia un leaf (o groupBy de un leaf)
    pp = set(leaves)
    for _ in range(3):
        for n, body in blocks.items():
            if any(re.search(r"\b" + re.escape(l) + r"\b", body) for l in pp):
                pp.add(n)
    return pp

def main():
    text = open(HTML, encoding="utf-8").read()
    PER_PERSON = per_person_getters(text)
    lines = text.split("\n")
    # localizar cada x-for con su :key (pueden estar en la misma linea)
    pat = re.compile(r'x-for="([^"]*)"(?:[^>]*?):key="([^"]*)"')
    flagged = []
    allrows = []
    for i, line in enumerate(lines, 1):
        for m in pat.finditer(line):
            forexpr, key = m.group(1), m.group(2)
            src = forexpr.split(" in ", 1)[-1].strip()
            allrows.append((i, src, key))
            # key "solo id": contiene .id y NO contiene composicion (+, '|', _person, indice)
            has_id = re.search(r"\.\s*id\b", key) is not None
            composed = ("+" in key) or ("|" in key) or ("_person" in key)
            # indice como key (ci, idx, i, ni...) sola -> segura
            bare_index = re.fullmatch(r"[a-z]{1,3}i?\d?", key.strip()) is not None
            risky = has_id and not composed and not bare_index
            # fuente por-persona: el token base del 'in' es un getter que expande _person
            src_base = re.split(r"[.\s(]", src.strip())[0]
            per_person = src_base in PER_PERSON
            if risky:
                flagged.append((i, src, key, per_person))

    print("=== x-for / :key — TODOS ({}) ===".format(len(allrows)))
    print("\n=== SOSPECHOSOS (key por id, sin persona/indice) ===")
    if not flagged:
        print("  ninguno")
    for i, src, key, pp in flagged:
        tag = "ALTO (fuente por-persona)" if pp else "revisar"
        print(f"  L{i}  [{tag}]")
        print(f"       in: {src}")
        print(f"       key: {key}")
    # exit 1 solo si hay sospechosos de fuente por-persona (alto riesgo)
    high = [f for f in flagged if f[3]]
    print(f"\n  total x-for: {len(allrows)} | sospechosos: {len(flagged)} | ALTO riesgo: {len(high)}")
    return 1 if high else 0

if __name__ == "__main__":
    sys.exit(main())
