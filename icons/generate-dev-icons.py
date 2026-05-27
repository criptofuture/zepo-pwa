"""Generate Zepo Dev icons with orange DEV badge."""
from PIL import Image, ImageDraw, ImageFont
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

for size in [192, 512]:
    src = os.path.join(SCRIPT_DIR, f"icon-{size}.png")
    dst = os.path.join(SCRIPT_DIR, f"icon-dev-{size}.png")

    img = Image.open(src).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Orange banner at bottom
    banner_h = int(size * 0.22)
    banner_y = size - banner_h
    # Semi-transparent orange rectangle
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [int(size * 0.08), banner_y, int(size * 0.92), size - int(size * 0.08)],
        radius=int(size * 0.06),
        fill=(255, 140, 0, 230),
    )
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # DEV text
    font_size = int(size * 0.13)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    text = "DEV"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = banner_y + (banner_h - int(size * 0.08) - th) // 2
    draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

    img.save(dst, "PNG")
    print(f"Created {dst}")
