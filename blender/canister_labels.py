"""Štítky kanystrů s koncentrátem (512x256 PNG, poměr 2:1 jako štítek na modelu) pro build_canister.py; běží v
systémovém Pythonu (Pillow).

python blender\\canister_labels.py <výstupní složka>

Pevná mřížka (základní pixely 512x256, kreslí se 4x a zmenšuje): barevný rám 8 px, vnitřní okraj 16 px, obsah
x 24..488, y 24..232. Levý sloupec (x 24..152, osa 88): piktogram a pod ním objem. Textový sloupec (x 176..488),
všechno zarovnané vlevo: značka, linka, druh (oba druhy stejná velikost písma), podtitulek, linka, poznámka.
"""

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONTS = r"C:\Windows\Fonts"
W, H = 512, 256
SS = 4

FRAME = 8
X0, X1, Y0, Y1 = 24, 488, 24, 232
ICON_CX = 88
TX = 176
TW = X1 - TX

BG = (247, 247, 243)
INK = (28, 28, 28)
GREY = (85, 85, 85)

LABELS = {
    "fertilizer": dict(color=(122, 184, 28), dark=(58, 110, 14), title="HNOJIVO", sub="koncentrované (tekuté)",
                       note="NPK  |  ředit vodou", icon="leaf"),
    "herbicide": dict(color=(217, 64, 20), dark=(200, 20, 20), title="HERBICID", sub="koncentrovaný postřik",
                      note="ředit vodou před použitím", icon="hazard"),
    "diesel": dict(color=(240, 176, 12), dark=(120, 78, 0), title="NAFTA", sub="motorová nafta",
                   note="pro elektrocentrálu", icon="drop"),
}


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), round(size * SS))


def text(d, x, baseline, s, fnt, fill, anchor="ls", spacing=0.0):
    """Text s počátkem x a účařím baseline (základní px); spacing = prostrkání v px."""
    if not spacing:
        d.text((x * SS, baseline * SS), s, font=fnt, fill=fill, anchor=anchor)
        return
    cx = x * SS
    for ch in s:
        d.text((cx, baseline * SS), ch, font=fnt, fill=fill, anchor="ls")
        cx += d.textlength(ch, font=fnt) + spacing * SS


def diamond(d, cx, cy, r, edge):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    pts = [(x * SS, y * SS) for x, y in pts]
    d.polygon(pts, fill=(255, 255, 255))
    d.line(pts + [pts[0]], fill=edge, width=round(r * 0.15 * SS), joint="curve")


def hazard(d, cx, cy, r, edge):
    """Piktogram GHS: bílý kosočtverec s červeným okrajem a vykřičníkem."""
    diamond(d, cx, cy, r, edge)
    d.rounded_rectangle(((cx - r * 0.085) * SS, (cy - r * 0.50) * SS, (cx + r * 0.085) * SS, (cy + r * 0.12) * SS),
                        radius=r * 0.06 * SS, fill=INK)
    d.ellipse(((cx - r * 0.10) * SS, (cy + r * 0.26) * SS, (cx + r * 0.10) * SS, (cy + r * 0.46) * SS), fill=INK)


def leaf(d, cx, cy, r, edge):
    """Stejný kosočtverec, uvnitř list (čočka nakloněná o 45°) s žilkou a řapíkem."""
    diamond(d, cx, cy, r, edge)
    L, Wd = r * 0.56, r * 0.27
    ang = math.radians(-45)
    ca, sa = math.cos(ang), math.sin(ang)

    def tr(u, v):
        return ((cx + (u * ca - v * sa)) * SS, (cy + (u * sa + v * ca)) * SS)

    n = 24
    upper = [tr(-L + 2 * L * t / n, -Wd * math.sin(math.pi * t / n) ** 0.9) for t in range(n + 1)]
    lower = [tr(L - 2 * L * t / n, Wd * math.sin(math.pi * t / n) ** 0.9) for t in range(n + 1)]
    d.polygon(upper + lower, fill=edge)
    d.line([tr(-L * 0.86, 0), tr(L * 0.80, 0)], fill=(255, 255, 255), width=round(r * 0.05 * SS))
    for u in (-0.30, 0.05, 0.40):
        for sgn in (-1, 1):
            d.line([tr(L * u, 0), tr(L * (u + 0.28), sgn * Wd * 0.62)], fill=(255, 255, 255), width=round(r * 0.035 * SS))
    d.line([tr(-L, 0), tr(-L - r * 0.16, 0)], fill=edge, width=round(r * 0.07 * SS))


def drop(d, cx, cy, r, edge):
    """Stejný kosočtverec, uvnitř kapka (špička nahoře) se světlým odleskem."""
    diamond(d, cx, cy, r, edge)
    top, bottom, rc = cy - r * 0.50, cy + r * 0.42, r * 0.30
    ccy = bottom - rc
    theta = math.acos(rc / (ccy - top))
    n = 40
    pts = [(cx, top)]
    for k in range(n + 1):
        a = -math.pi / 2 + theta + (2 * math.pi - 2 * theta) * k / n
        pts.append((cx + math.cos(a) * rc, ccy + math.sin(a) * rc))
    pts.append((cx, top))
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=edge)
    d.ellipse(((cx - rc * 0.60) * SS, (ccy - rc * 0.05) * SS, (cx - rc * 0.28) * SS, (ccy + rc * 0.40) * SS), fill=(255, 255, 255))


def brand_mark(size):
    """Znak BZUK z atlasu značky (textures/sdt_brand.png, oblast mark_BZUK) jako RGBA size x size px."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import brand_layout as BL
    x, y, w, h = BL.REGIONS["mark_BZUK"]
    atlas = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures", BL.ATLAS_PNG)).convert("RGBA")
    return atlas.crop((x, y, x + w, y + h)).resize((size, size), Image.LANCZOS)


def make(kind, cfg, out, title_size):
    img = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)
    color, dark = cfg["color"], cfg["dark"]
    d.rectangle((0, 0, W * SS - 1, H * SS - 1), outline=color, width=FRAME * SS)

    icon_cy = 98
    {"hazard": hazard, "leaf": leaf, "drop": drop}[cfg["icon"]](d, ICON_CX, icon_cy, 58, dark)
    text(d, ICON_CX, 222, "20 l", font("arialbd.ttf", 40), INK, anchor="ms")

    mark = brand_mark(34 * SS)                           # značka BZUK: znak z atlasu sdt_brand a nápis
    img.paste(mark, (TX * SS, 24 * SS), mark)
    text(d, TX + 44, 52, "BZUK", font("arialbd.ttf", 30), dark, spacing=1.0)
    d.rectangle((TX * SS, 62 * SS, X1 * SS, 65 * SS), fill=color)
    text(d, TX - 3, 128, cfg["title"], font("arialbd.ttf", title_size), INK)
    text(d, TX, 168, cfg["sub"], font("arial.ttf", 27), GREY)
    d.rectangle((TX * SS, 188 * SS, X1 * SS, 191 * SS), fill=color)
    text(d, TX, 222, cfg["note"], font("arialbd.ttf", 21), INK)

    path = os.path.join(out, f"canister_label_{kind}.png")
    img.resize((W, H), Image.LANCZOS).save(path)
    return path


def fit_title_size():
    """Jedna velikost písma druhu pro oba štítky: největší, při které se nejširší nápis vejde do textového sloupce."""
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    size = 80
    while size > 20 and max(probe.textlength(c["title"], font=font("arialbd.ttf", size)) for c in LABELS.values()) > (TW - 6) * SS:
        size -= 1
    return size


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    size = fit_title_size()
    for kind, cfg in LABELS.items():
        print(make(kind, cfg, out, size))


if __name__ == "__main__":
    main()
