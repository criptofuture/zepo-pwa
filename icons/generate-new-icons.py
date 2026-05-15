"""
Genera iconos PWA full-bleed que matchean el splash HTML:
- Fondo solido #0A0A0F (sin corners transparentes -> elimina el "doble splash" del OS)
- Anillo orbital estatico cyan -> purpura
- Logo Z gradient en el centro

Outputs:
  icon-192.png, icon-512.png, apple-touch.png, og.png, favicon-32.png
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
BG = (10, 10, 15, 255)        # #0A0A0F
CYAN = (0, 240, 255, 255)
PURPLE = (112, 0, 255, 255)
BLACK = (10, 10, 15, 255)

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))

def make_icon(size):
    """size: 192, 512, etc."""
    img = Image.new('RGBA', (size, size), BG)
    d = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2

    # ── Anillo orbital estatico (mismo gradient que el HTML splash) ──
    # Ring outer radius ~ 36% del tamaño; thickness ~ 4% del tamaño
    ring_outer = int(size * 0.36)
    ring_inner = ring_outer - max(2, int(size * 0.018))
    # Renderizar arco con conic gradient simulada: 0deg-220deg transparent,
    # 220deg-350deg cyan->purple, 350deg-360deg transparent
    # Trabajamos en una capa separada con SS x4 para anti-aliasing
    ss = 4
    ring_layer = Image.new('RGBA', (size*ss, size*ss), (0,0,0,0))
    rd = ImageDraw.Draw(ring_layer)
    steps = 720
    for i in range(steps):
        # Empieza en 220deg, termina en 350deg
        deg_start = 220 + (i / steps) * 130
        deg_end = deg_start + 130 / steps + 0.5
        t = i / steps
        color = lerp_color(CYAN, PURPLE, t)
        # PIL angles: 0 = derecha, sentido horario
        # Splash HTML: from 0deg arriba, gradient va de 220 a 350. Rotamos -90deg
        pil_start = deg_start - 90
        pil_end = deg_end - 90
        rd.arc(
            [
                (cx - ring_outer) * ss,
                (cy - ring_outer) * ss,
                (cx + ring_outer) * ss,
                (cy + ring_outer) * ss
            ],
            start=pil_start, end=pil_end,
            fill=color,
            width=(ring_outer - ring_inner) * ss
        )
    ring_layer = ring_layer.resize((size, size), Image.LANCZOS)
    # Glow soft alrededor del anillo
    glow = ring_layer.filter(ImageFilter.GaussianBlur(radius=size*0.025))
    img.paste(glow, (0,0), glow)
    img.paste(ring_layer, (0,0), ring_layer)

    # ── Logo Z (rounded rect con gradient cyan -> purple) ──
    logo_size = int(size * 0.50)
    logo_radius = int(logo_size * 0.275)
    lx0, ly0 = cx - logo_size // 2, cy - logo_size // 2
    lx1, ly1 = lx0 + logo_size, ly0 + logo_size
    # Gradient layer (diagonal)
    grad_layer = Image.new('RGBA', (logo_size, logo_size), (0,0,0,0))
    gd = ImageDraw.Draw(grad_layer)
    for y in range(logo_size):
        for x in range(logo_size):
            t = ((x + y) / (2 * logo_size))
            t = max(0.0, min(1.0, t))
            gd.point((x, y), fill=lerp_color(CYAN, PURPLE, t))
    # Mask rounded rect
    mask = Image.new('L', (logo_size, logo_size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([(0,0),(logo_size, logo_size)], radius=logo_radius, fill=255)
    img.paste(grad_layer, (lx0, ly0), mask)

    # Glow detras del logo
    logo_glow = Image.new('RGBA', (size, size), (0,0,0,0))
    lgd = ImageDraw.Draw(logo_glow)
    lgd.rounded_rectangle([(lx0-6, ly0-6),(lx1+6, ly1+6)], radius=logo_radius+6, fill=(0,240,255,32))
    logo_glow = logo_glow.filter(ImageFilter.GaussianBlur(radius=size*0.035))
    img2 = Image.new('RGBA', (size, size), BG)
    img2.paste(glow, (0,0), glow)
    img2.paste(ring_layer, (0,0), ring_layer)
    img2.paste(logo_glow, (0,0), logo_glow)
    img2.paste(grad_layer, (lx0, ly0), mask)

    # ── Letra Z encima del rounded rect ──
    z_layer = Image.new('RGBA', (size, size), (0,0,0,0))
    zd = ImageDraw.Draw(z_layer)
    # Buscar fuente
    fonts_to_try = ['arialbd.ttf', 'arial.ttf', 'C:/Windows/Fonts/arialbd.ttf']
    font = None
    z_font_size = int(logo_size * 0.62)
    for f in fonts_to_try:
        try:
            font = ImageFont.truetype(f, z_font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    bbox = zd.textbbox((0, 0), "Z", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    zd.text(
        (cx - tw // 2 - bbox[0], cy - th // 2 - bbox[1] - int(size*0.01)),
        "Z",
        font=font,
        fill=BLACK
    )
    img2.paste(z_layer, (0, 0), z_layer)

    return img2.convert('RGB')

def main():
    sizes = {
        'icon-192.png': 192,
        'icon-512.png': 512,
        'apple-touch.png': 180,
        'og.png': 1200,
        'favicon-32.png': 32,
    }
    for name, sz in sizes.items():
        out_path = os.path.join(OUT_DIR, name)
        if name == 'og.png':
            # OG: 1200x630 con logo+anillo centrado
            base = Image.new('RGB', (1200, 630), (10, 10, 15))
            inner = make_icon(560)
            base.paste(inner, ((1200-560)//2, (630-560)//2))
            base.save(out_path, 'PNG', optimize=True)
        else:
            ic = make_icon(sz)
            ic.save(out_path, 'PNG', optimize=True)
        print(f'  wrote {name} ({sz}px)')

if __name__ == '__main__':
    main()
