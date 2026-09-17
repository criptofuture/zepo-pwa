#!/usr/bin/env python3
"""
lint-design.py — Guardrail anti-regresion de la marca editorial Zepo (V2.0 Bricolage).

Que hace:
  - FAIL (exit 1): introduces colores neon de la marca vieja, tokens que no existen,
    el bug del toggle x-show + :style con display, o un elemento NUEVO con x-show y
    display en su style estatico (ver XSHOW_VIEJOS).
  - WARN (exit 0): quedan literales rgba() de la paleta vieja (success/danger/warning)
    que idealmente deberian migrar a triplets de token, o elementos VIEJOS con x-show +
    display. No bloquea el deploy.

La barra de dev (DEV TOOLBAR — solo zepo-staging, hasta EOF) esta en allowlist:
nunca se sirve en produccion (gated por IS_STAGING), conserva su estetica neon a proposito.

Uso:
  python tools/lint-design.py            # lint index.html
  python tools/lint-design.py archivo.html
  python tools/lint-design.py index.html --viejos   # lista los x-show + display viejos
"""
import re
import sys
import os
from collections import Counter

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

# --- x-show + display en el style ESTATICO ---
# Al mostrar un elemento, x-show de Alpine v3 hace el.style.removeProperty('display')
# (packages/alpinejs/src/directives/x-show.js, _x_doShow): el flex / inline-flex / grid del
# style="..." se pierde y el elemento queda block. Estaba anotado en memoria y volvio igual
# el 16-sep-2026 (v203): boton con icono desalineado, etiqueta estirada a todo el ancho.
# Los casos que ya existian estan en XSHOW_VIEJOS y solo avisan; uno nuevo bloquea.
# La lista solo debe ACHICARSE: al arreglar uno, se borra su linea.
XSHOW_VIEJOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lint-design-xshow-viejos.tsv")
TAG = re.compile(r'<([a-zA-Z][\w-]*)((?:\s+[^\s=>/"\']+(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>"\']+))?)*)\s*/?>')
ATTR = re.compile(r'([^\s=>/"\']+)(?:\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>"\']+))?')
# Comentarios, <script> y <style> no son elementos: se blanquean conservando los saltos de linea.
NO_ES_HTML = re.compile(r'<!--.*?-->|<(script|style)\b[^>]*>.*?</\1\s*>', re.S | re.I)
# Etiquetas que ya son block sin CSS: ahi perder un display:block no cambia nada.
BLOCK_SIN_CSS = {"div", "section", "article", "aside", "header", "footer", "nav", "main", "form",
                 "p", "ul", "ol", "dl", "h1", "h2", "h3", "h4", "h5", "h6", "fieldset", "figure",
                 "blockquote", "pre", "details"}


def elementos(texto):
    """(linea, match, attrs) de cada etiqueta de apertura, sin comentarios, <script> ni <style>."""
    texto = NO_ES_HTML.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), texto)
    for m in TAG.finditer(texto):
        attrs = {}
        for a in ATTR.finditer(m.group(2) or ""):
            valor = a.group(2) or ""
            if valor[:1] in ('"', "'"):
                valor = valor[1:-1]
            attrs.setdefault(a.group(1).lower(), valor)
        yield texto.count("\n", 0, m.start()) + 1, m, attrs


def xshow_con_display(texto):
    """[(linea, clave, fragmento)] de cada elemento con x-show y display en su style estatico.
    clave = etiqueta<TAB>display<TAB>expresion de x-show (lo que se compara con XSHOW_VIEJOS)."""
    hallados = []
    for linea, m, attrs in elementos(texto):
        xshow = next((v for k, v in attrs.items() if k == "x-show" or k.startswith("x-show.")), None)
        if xshow is None or "style" not in attrs:
            continue
        display = None
        for decl in attrs["style"].split(";"):
            prop, _, valor = decl.partition(":")
            if prop.strip().lower() == "display":
                display = " ".join(valor.split()).lower()  # la ultima declaracion es la que vale
        if display is None:
            continue
        tag = m.group(1).lower()
        base = display.replace("!important", "").strip()
        if base == "none" or (base == "block" and tag in BLOCK_SIN_CSS):
            continue
        clave = "\t".join((tag, display, " ".join(xshow.split())))
        hallados.append((linea, clave, " ".join(m.group(0).split())[:90]))
    return hallados


def xshow_viejos(ruta=None, campos=3):
    ruta = ruta or XSHOW_VIEJOS
    if not os.path.exists(ruta):
        return Counter()
    with open(ruta, encoding="utf-8") as f:
        filas = [l.rstrip("\n").split("\t") for l in f if l.strip() and not l.startswith("#")]
    return Counter("\t".join(p[1:1 + campos]) for p in filas if len(p) >= 1 + campos)


# --- style="..." fijo + :style con un STRING ---
# Alpine v3 (packages/alpinejs/src/utils/styles.js, setStylesFromString) hace
# el.setAttribute('style', valor) cuando :style es un string: el style estatico se pierde
# entero. Con un objeto ({...}) solo toca esas propiedades. Estaba en
# memory/feedback/alpine-frontend-gotchas.md §1 y volvio igual el 17-sep-2026 (v205, ventana
# «Elegir categoria»: casillas sin fondo ni borde). Mismo trato que x-show: viejos avisan,
# uno nuevo bloquea, y la lista solo se achica.
STYLE_VIEJOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lint-design-style-string-viejos.tsv")


def style_con_string(texto):
    """[(linea, clave, fragmento)] de cada elemento con style="..." y :style cuyo valor no es objeto.
    clave = etiqueta<TAB>valor de :style (lo que se compara con STYLE_VIEJOS)."""
    hallados = []
    for linea, m, attrs in elementos(texto):
        din = attrs.get(":style", attrs.get("x-bind:style"))
        if din is None or not attrs.get("style", "").strip() or din.strip().startswith("{"):
            continue
        clave = "\t".join((m.group(1).lower(), " ".join(din.split())))
        hallados.append((linea, clave, " ".join(m.group(0).split())[:90]))
    return hallados

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
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else "index.html"
    if not os.path.exists(path):
        print(f"❌ No existe: {path}")
        return 2

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    dev_start = find_devtoolbar_start(lines)

    # x-show + display: viejos (avisan) y nuevos (bloquean). Si hay mas copias iguales que en
    # la lista no se sabe cual es la nueva, asi que se señalan todas.
    viejos = xshow_viejos()
    xs_todos = xshow_con_display("".join(lines[:dev_start]))
    vistos = Counter(clave for _, clave, _ in xs_todos)
    xs_nuevos = [h for h in xs_todos if vistos[h[1]] > viejos[h[1]]]
    xs_viejos = [h for h in xs_todos if vistos[h[1]] <= viejos[h[1]]]
    ya_no_estan = sum((viejos - vistos).values())

    st_viejos_lista = xshow_viejos(STYLE_VIEJOS, 2)
    st_todos = style_con_string("".join(lines[:dev_start]))
    st_vistos = Counter(clave for _, clave, _ in st_todos)
    st_nuevos = [h for h in st_todos if st_vistos[h[1]] > st_viejos_lista[h[1]]]
    st_viejos = [h for h in st_todos if st_vistos[h[1]] <= st_viejos_lista[h[1]]]
    st_ya_no_estan = sum((st_viejos_lista - st_vistos).values())
    if "--generar-style-viejos" in sys.argv:  # solo para crear la lista la primera vez
        with open(STYLE_VIEJOS, "w", encoding="utf-8", newline="\n") as f:
            f.write("# Elementos con style=\"...\" fijo + :style con un STRING que YA existian el 17-sep-2026.\n"
                    "# lint-design.py solo avisa por estos; uno nuevo bloquea. Al arreglar uno, borra su linea.\n")
            f.writelines(f"{ln}\t{clave}\n" for ln, clave, _ in st_todos)
        print(f"lista escrita: {len(st_todos)} elementos")
        return 0

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

    for ln, clave, frag in xs_nuevos:
        display = clave.split("\t")[1]
        copias = (f" [hay {vistos[clave]} iguales y la lista guarda {viejos[clave]}: uno es nuevo]"
                  if viejos[clave] else "")
        fails.append((ln, f"x-show + style con display:{display} — Alpine borra ese display al mostrarlo "
                          "y queda block. Pasalo a una clase (flex: class=\"flex-show\") o envuelve "
                          f"el elemento con <template x-if>{copias}", frag))
    for ln, clave, frag in st_nuevos:
        fails.append((ln, "style=\"...\" fijo + :style con un string — Alpine reemplaza el style estatico "
                          "COMPLETO. Usa :style con un objeto ({ color: ... }) o junta todo en :style", frag))
    fails.sort(key=lambda f: f[0])

    if xs_viejos:
        print(f"⚠️  {len(xs_viejos)} elemento(s) viejos con x-show + display en su style (no bloquea; "
              f"--viejos los lista, {os.path.basename(XSHOW_VIEJOS)} los guarda)")
        if "--viejos" in sys.argv:
            for ln, clave, frag in xs_viejos:
                print(f"    L{ln}: {frag}")
    if ya_no_estan:
        print(f"ℹ️  {ya_no_estan} de {os.path.basename(XSHOW_VIEJOS)} ya no existen: borra sus lineas "
              "para que la lista solo se achique")

    if st_viejos:
        print(f"⚠️  {len(st_viejos)} elemento(s) viejos con style fijo + :style string (no bloquea; "
              f"--viejos los lista, {os.path.basename(STYLE_VIEJOS)} los guarda)")
        if "--viejos" in sys.argv:
            for ln, clave, frag in st_viejos:
                print(f"    L{ln}: {frag}")
    if st_ya_no_estan:
        print(f"ℹ️  {st_ya_no_estan} de {os.path.basename(STYLE_VIEJOS)} ya no existen: borra sus lineas")

    if warns:
        print(f"⚠️  {len(warns)} residuo(s) de paleta vieja (no bloquea):")
        # agrupar por mensaje para no inundar
        c = Counter(m for _, m in warns)
        for msg, n in c.most_common():
            print(f"    · {n}x  {msg}")

    if fails:
        print(f"\n🚨 {len(fails)} regresion(es) de diseño — DEPLOY BLOQUEADO:")
        for ln, msg, snippet in fails:
            print(f"    L{ln}: {msg}")
            print(f"          {snippet}")
        print(f"\n(La dev toolbar desde L{dev_start + 1} esta en allowlist.)")
        return 1

    print(f"\n✅ Sin regresiones de diseño. ({dev_start} lineas revisadas, dev toolbar omitida.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
