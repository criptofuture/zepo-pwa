"""
tokenize_colors.py
Reemplaza colores hardcodeados en index.html por variables CSS.
Excluye: colores de marca (Google, Mastercard), masks SVG.
"""
import re, shutil
from pathlib import Path

SRC = Path(__file__).parent.parent / "index.html"
BAK = SRC.with_suffix(".html.bak")

# ── 1. Backup ────────────────────────────────────────────────────────────────
shutil.copy(SRC, BAK)
print(f"Backup: {BAK}")

html = SRC.read_text(encoding="utf-8")
original = html

# ── 2. Expansión del :root ────────────────────────────────────────────────────
OLD_ROOT = """    :root {
      --bg: #0A0A0F;
      --surface: #13131A;
      --surface2: #191923;
      --border: #1E1E2E;
      --border2: #2A2A3D;
      --cyan: #00F0FF;
      --purple: #7000FF;
      --gradient: linear-gradient(135deg, #00F0FF 0%, #7000FF 100%);
      --text: #FFFFFF;
      --muted: #8888AA;
      --dim: #5A5A75;
      --success: #00E5A0;
      --warning: #FFB800;
      --danger: #FF6B6B;
      --radius: 16px;
      --radius-sm: 10px;
      --radius-pill: 50px;
      --safe-top: env(safe-area-inset-top, 0px);
      --safe-bottom: env(safe-area-inset-bottom, 0px);
    }"""

NEW_ROOT = """    :root {
      /* ── Fondos ── */
      --bg: #0A0A0F;
      --bg-deep: #07070D;
      --surface: #13131A;
      --surface2: #191923;
      /* ── Bordes ── */
      --border: #1E1E2E;
      --border2: #2A2A3D;
      /* ── Acento primario ── */
      --cyan: #00F0FF;
      --purple: #7000FF;
      --purple-light: #B794F6;
      --gradient: linear-gradient(135deg, #00F0FF 0%, #7000FF 100%);
      /* ── Texto ── */
      --text: #FFFFFF;
      --text-on-accent: #000000;
      --muted: #8888AA;
      --dim: #5A5A75;
      /* ── Semánticos ── */
      --success: #00E5A0;
      --success-dark: #00B383;
      --warning: #FFB800;
      --danger: #FF6B6B;
      --danger-light: #FF7A7A;
      --gold: #C49A6C;
      /* ── RGB channels para rgba() ── */
      --cyan-rgb: 0, 240, 255;
      --purple-rgb: 112, 0, 255;
      --success-rgb: 0, 229, 160;
      --danger-rgb: 255, 107, 107;
      --warning-rgb: 255, 184, 0;
      /* ── Layout ── */
      --radius: 16px;
      --radius-sm: 10px;
      --radius-pill: 50px;
      --safe-top: env(safe-area-inset-top, 0px);
      --safe-bottom: env(safe-area-inset-bottom, 0px);
    }"""

html = html.replace(OLD_ROOT, NEW_ROOT, 1)

# ── 3. Separar :root del resto para no tocar las definiciones ────────────────
# El :root ya fue reemplazado como bloque en el paso 2.
# Ahora separamos el HTML en: [antes-de-:root] + [:root bloque] + [resto]
# y aplicamos reemplazos SOLO en el [resto].
root_start = html.index(':root {')
root_end   = html.index('}', root_start) + 1
# Incluimos el cierre del bloque CSS (la llave de cierre del :root)
# Ajuste: el :root termina en la primera llave '}' que lo cierra
html_before = html[:root_start]
html_root   = html[root_start:root_end]
html_after  = html[root_end:]

def replace_rgba(text, r, g, b, var_name):
    pattern = re.compile(
        r'rgba\(\s*' + str(r) + r'\s*,\s*' + str(g) + r'\s*,\s*' + str(b) +
        r'\s*,\s*([\d.]+)\s*\)'
    )
    def repl(m):
        alpha = m.group(1)
        return f'rgba(var({var_name}), {alpha})'
    return pattern.sub(repl, text)

html_after = replace_rgba(html_after, 0, 240, 255, '--cyan-rgb')
html_after = replace_rgba(html_after, 112, 0, 255, '--purple-rgb')
html_after = replace_rgba(html_after, 0, 229, 160, '--success-rgb')
html_after = replace_rgba(html_after, 255, 107, 107, '--danger-rgb')
html_after = replace_rgba(html_after, 255, 184, 0, '--warning-rgb')

# ── 4. Hex simples → var() (solo fuera del :root) ────────────────────────────
HEX_MAP = [
    # Fondos
    ("#0A0A0F", "var(--bg)"),
    ("#07070D", "var(--bg-deep)"),
    ("#13131A", "var(--surface)"),
    ("#191923", "var(--surface2)"),
    ("#1a1a25", "var(--surface2)"),   # variante case
    ("#15151f", "var(--surface2)"),   # otra variante cercana
    ("#1C1C1E", "var(--border)"),
    ("#1E1E2E", "var(--border)"),
    ("#2A2A3D", "var(--border2)"),
    ("#2a2a3d", "var(--border2)"),
    # Acento primario
    ("#00F0FF", "var(--cyan)"),
    ("#7000FF", "var(--purple)"),
    ("#B794F6", "var(--purple-light)"),
    # Texto
    ("#8888AA", "var(--muted)"),
    ("#5A5A75", "var(--dim)"),
    # Semánticos
    ("#00E5A0", "var(--success)"),
    ("#00B383", "var(--success-dark)"),
    ("#FF6B6B", "var(--danger)"),
    ("#FF7A7A", "var(--danger-light)"),
    ("#FFB800", "var(--warning)"),
    ("#C49A6C", "var(--gold)"),
]

# Colores a excluir (logos de marca — no reemplazar)
EXCLUDE = {
    "#FBBC05", "#EA4335", "#4285F4", "#34A853",   # Google
    "#EB001B", "#F79E1B",                           # Mastercard
    "#F5F5EC", "#E8E8DD",                           # fondos específicos
}

for old, new in HEX_MAP:
    if old in EXCLUDE:
        continue
    pattern = re.compile(re.escape(old) + r'(?![0-9A-Fa-f])', re.IGNORECASE)
    count = len(pattern.findall(html_after))
    html_after = pattern.sub(new, html_after)
    if count:
        print(f"  {old} -> {new}  ({count}x)")

# ── 5. #D8D8E5 → --text-light (no tenía variable aún) ────────────────────────
html_after = html_after.replace('#D8D8E5', 'var(--text-light)')

# ── 6. #000 en botones (texto sobre acento) — solo fuera del :root ───────────
html_after = re.sub(r'(color\s*:\s*)#000([^0-9A-Fa-f])', r'\1var(--text-on-accent)\2', html_after)
html_after = re.sub(r'(fill\s*:\s*)#000([^0-9A-Fa-f])', r'\1var(--text-on-accent)\2', html_after)

# ── 7. Añadir --text-light al :root ──────────────────────────────────────────
html_root = html_root.replace(
    '      --dim: #5A5A75;',
    '      --dim: #5A5A75;\n      --text-light: #D8D8E5;'
)

# ── 8. Reunir y guardar ───────────────────────────────────────────────────────
html = html_before + html_root + html_after
SRC.write_text(html, encoding="utf-8")

changed = html != original
added = html.count("var(--") - original.count("var(--")
print(f"\nListo. Variables añadidas al HTML: +{added}")
print(f"Archivo guardado: {SRC}")
print(f"Backup disponible: {BAK}")
if not changed:
    print("⚠️  Sin cambios — verificar que el :root exacto coincide")
