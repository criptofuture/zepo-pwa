#!/usr/bin/env python3
"""
Candado: lint-design.py bloquea un elemento NUEVO con x-show y display en su style estatico.

Al mostrarlo, Alpine le borra ese display y queda block (boton con icono desalineado,
etiqueta estirada). Volvio el 16-sep-2026 en v203 con la regla ya escrita en memoria.
Esta prueba copia index.html, le mete casos a proposito y exige que el lint falle en los
malos y pase en los buenos. Con el lint de antes del 16-sep los malos pasaban.

USO:  python tools/qa-lint-xshow.py                       Sale 1 si algun caso da mal.
      python tools/qa-lint-xshow.py --lint <otro-lint.py>  Corre los casos contra otro lint.
"""
import os, re, subprocess, sys, tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(os.path.dirname(TOOLS), "index.html")
LINT = sys.argv[sys.argv.index("--lint") + 1] if "--lint" in sys.argv else os.path.join(TOOLS, "lint-design.py")

# (nombre, html que se mete despues de <body>, ¿debe bloquear?)
CASOS = [
    ("inline-flex en una linea", '<span x-show="nuevoBadge" style="display:inline-flex;gap:4px">1</span>', True),
    ("boton en varias lineas y > dentro de x-show",
     '<button x-show="a > b"\n  @click="x()"\n  style="width:36px;display:flex;align-items:center">', True),
    ("comillas simples y grid", "<div x-show='abierto' style='padding:4px; display: grid'>", True),
    ("modificador y mayusculas", '<div x-show.transition="abierto" style="DISPLAY : Inline-Block !important">', True),
    ("copia extra de un caso viejo", '<span x-show="friendBadge > 0" style="display:inline-flex">', True),
    ("img con display:block", '<img x-show="foto" src="x.png" style="display:block">', True),
    ("display:none (evita el parpadeo)", '<div x-show="cargando" style="display:none">', False),
    ("div con display:block", '<div x-show="cargando" style="display:block;padding:4px">', False),
    ("display en una clase", '<div x-show="abierto" class="flex-show" style="gap:4px">', False),
    ("dentro de un comentario", '<!-- <div x-show="a" style="display:flex"> -->', False),
    ("dentro de un script", '<script>const t = \'<div x-show="a" style="display:flex">\';</script>', False),
    ("data-style no es style", '<div x-show="a" data-style="display:flex">', False),
]


def correr(html):
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "index.html")
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        r = subprocess.run([sys.executable, LINT, ruta], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


with open(INDEX, encoding="utf-8") as f:
    original = f.read()
cuerpo = re.search(r"<body\b[^>]*>\n", original).end()
linea_meter = original.count("\n", 0, cuerpo) + 1

malos = []
codigo, salida = correr(original)
if codigo != 0:
    malos.append(f"  index.html actual: el lint deberia pasar y salio {codigo}\n{salida}")

for nombre, trozo, bloquea in CASOS:
    codigo, salida = correr(original[:cuerpo] + trozo + "\n" + original[cuerpo:])
    if bloquea and not (codigo == 1 and f"L{linea_meter}:" in salida):
        malos.append(f"  {nombre}: deberia bloquear en L{linea_meter} y salio {codigo}")
    if not bloquea and codigo != 0:
        malos.append(f"  {nombre}: no deberia bloquear y salio {codigo}\n{salida}")

# Despues de la barra de dev (solo staging) no se revisa, igual que los colores neon.
codigo, _ = correr(original + '\n<div x-show="dev" style="display:flex">\n')
if codigo != 0:
    malos.append(f"  despues de DEV TOOLBAR: no deberia bloquear y salio {codigo}")

# Arreglar un caso viejo no bloquea, pero avisa que hay que borrarlo de la lista.
arreglado = original.replace('x-show="patHasCrypto"', 'x-show="patHasCrypto" class="flex-show"', 1)
arreglado = re.sub(r'(x-show="patHasCrypto" class="flex-show"[^>]*?)display:\s*flex;?', r"\1", arreglado, count=1)
codigo, salida = correr(arreglado)
if arreglado == original or codigo != 0 or "ya no existen" not in salida:
    malos.append(f"  caso viejo arreglado: deberia pasar y avisar 'ya no existen'; salio {codigo}")

if malos:
    print(f"FALLA ({os.path.basename(LINT)}): x-show + display\n" + "\n".join(malos))
    sys.exit(1)
print(f"OK: {len(CASOS) + 3} casos de x-show + display dan lo esperado")
