"""Atlas polepů značky (rozvržení blender/brand_layout.py) a obrázek značky do obchodu.

python tools/make_brand_atlas.py

Tvary znaků a barvy podle tmp/logo/znacka-navrhy.html (pole C), rozměry lockupu v CSS px jako .lk tamtéž (znak 54, mezera 12,
nápis line-height 1, podtitul 9 px IBM Plex Mono s odstupem 5). Písma (OFL) v assets/fonts. Kreslí se ve 4x nadvzorkování
přes masky (bez tmavých okrajů), průhledné pixely dostanou barvu nejbližšího obsahu, ať ji mipmapy nezatáhnou do černa.

Výstup: blender/textures/sdt_brand.png -> vehicles/sprayDroneTrailerMiddle/textures/sdt_brand.dds (DXT5 s mipmapami; Max a Mini
si ho kopírují při exportu), brand_bzuk.dds (512 x 256 jako vanilla data/store/brands, světlý text pro tmavé UI) a náhledy
v out/brand/.
"""

import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "blender"))
sys.path.insert(0, os.path.join(PROJECT, "tools"))
import brand_layout as B  # noqa: E402
import png2dds  # noqa: E402

MOD = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer")
SRC_PNG = os.path.join(PROJECT, "blender", "textures", B.ATLAS_PNG)
DDS = os.path.join(MOD, "vehicles", "sprayDroneTrailerMiddle", "textures", B.ATLAS_DDS)
BRAND_DDS = os.path.join(MOD, "brand_bzuk.dds")
OUT = os.path.join(PROJECT, "out", "brand")
FONTS = os.path.join(PROJECT, "assets", "fonts")
SS = 4
WHITE = "#ffffff"


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), max(1, round(size)))
    if weight is not None:
        f.set_variation_by_axes([weight])
    return f


# ------------------------------------------------------------------ geometrie ve viewBoxu 0..100 (y dolů, úhly po směru hodin)
def rot(p, a, c=(0.0, 0.0)):
    a = math.radians(a)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a))


def ellipse(cx, cy, rx, ry, a=0.0, c=None, n=96):
    pts = [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return [rot(p, a, c or (cx, cy)) for p in pts]


def circle(cx, cy, r, n=96):
    return ellipse(cx, cy, r, r, n=n)


def sector(cx, cy, r0, r1, a0, a1, n=48):
    """Mezikruží r0..r1 mezi úhly a0..a1 (stupně) - čárkovaný tah kružnice."""
    outer = [(cx + r1 * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cy + r1 * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
             for k in range(n + 1)]
    inner = [(cx + r0 * math.cos(math.radians(a1 - (a1 - a0) * k / n)), cy + r0 * math.sin(math.radians(a1 - (a1 - a0) * k / n)))
             for k in range(n + 1)]
    return outer + inner


def capsule(p0, p1, w, n=16):
    """Úsečka s kulatými konci (stroke-linecap round), nebo zaoblený obdélník s rx = h / 2."""
    (x0, y0), (x1, y1) = p0, p1
    a = math.atan2(y1 - y0, x1 - x0)
    r = w / 2
    pts = [(x1 + r * math.cos(a - math.pi / 2 + math.pi * k / n), y1 + r * math.sin(a - math.pi / 2 + math.pi * k / n))
           for k in range(n + 1)]
    pts += [(x0 + r * math.cos(a + math.pi / 2 + math.pi * k / n), y0 + r * math.sin(a + math.pi / 2 + math.pi * k / n))
            for k in range(n + 1)]
    return pts


def rrect(x, y, w, h):
    r = h / 2
    return capsule((x + r, y + r), (x + w - r, y + r), h)


def _arc(p0, r, large, sweep, p1, n=32):
    """Oblouk SVG (rx = ry, bez natočení) z p0 do p1, převod na střed podle SVG F.6.5."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    d2 = dx * dx + dy * dy
    r = max(r, math.sqrt(d2))
    k = math.sqrt(max(0.0, (r * r - d2) / d2)) * (-1 if large == sweep else 1)
    cx, cy = k * dy + (x0 + x1) / 2, -k * dx + (y0 + y1) / 2
    t0 = math.atan2(y0 - cy, x0 - cx)
    t1 = math.atan2(y1 - cy, x1 - cx)
    dt = t1 - t0
    if sweep and dt < 0:
        dt += 2 * math.pi
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    return [(cx + r * math.cos(t0 + dt * i / n), cy + r * math.sin(t0 + dt * i / n)) for i in range(1, n + 1)]


def path(d, n=24):
    """Lomená čára z cesty SVG s příkazy M, C, A, Z (absolutní souřadnice), jak je v HTML."""
    tok = re.findall(r"[MCAZ]|-?[\d.]+", d)
    pts, i, cmd = [], 0, None
    while i < len(tok):
        if tok[i] in "MCAZ":
            cmd = tok[i]
            i += 1
            if cmd == "Z":
                continue
        v = lambda j: float(tok[i + j])  # noqa: E731
        if cmd == "M":
            pts.append((v(0), v(1)))
            i += 2
        elif cmd == "C":
            p0, p1, p2, p3 = pts[-1], (v(0), v(1)), (v(2), v(3)), (v(4), v(5))
            for k in range(1, n + 1):
                t = k / n
                a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
                pts.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
            i += 6
        elif cmd == "A":
            pts += _arc(pts[-1], v(0), int(v(3)), int(v(4)), (v(5), v(6)))
            i += 7
    return pts


def polyline_stroke(pts, w):
    return [capsule(pts[k], pts[k + 1], w, 8) for k in range(len(pts) - 1)]


DROP = "M0 -22 C0 -22 -11 -8 -11 0 A11 11 0 0 0 11 0 C11 -8 0 -22 0 -22Z"


def mark_shapes(key, p, s, k=WHITE):
    """Znak designu jako seznam (barva, [polygony]) v pořadí kreslení; k = barva vnitřku (v HTML podklad, tady bílá)."""
    if key == "BZUK":
        octa = [(32.4, 7.5), (67.6, 7.5), (92.5, 32.4), (92.5, 67.6), (67.6, 92.5), (32.4, 92.5), (7.5, 67.6), (7.5, 32.4)]
        # stroke-dasharray 38 53 na kružnici r 29 (start na 3 h, po směru hodin), celé otočené o -20°
        L = 29.0
        dashes = [sector(50, 50, 29 - 2.25, 29 + 2.25, math.degrees(a / L) - 20, math.degrees(b / L) - 20)
                  for a, b in ((0, 38), (91, 129))]
        blades = [ellipse(50, 32, 6.5, 16, a, (50, 50)) for a in (30, 210)]
        return [(p, [octa]), (k, dashes + blades + [circle(50, 50, 9)]), (p, [circle(50, 50, 5)])]
    if key == "ROSA":
        drop = path(DROP)
        drops = []
        for a in (45, 135, 225, 315):
            drops.append([rot((50 + x2, 19 + y2), a, (50, 50)) for x2, y2 in (rot(q, 180) for q in drop)])
        return [(p, drops), (s, [circle(50, 50, 7)])]
    if key == "KAPKA":
        body = path("M50 4 C50 4 16 46 16 64 A34 34 0 0 0 84 64 C84 46 50 4 50 4Z")
        blades = [ellipse(50, 51, 6, 13, a, (50, 64)) for a in (0, 120, 240)]
        shine = polyline_stroke([(29.0, 58.0)] + _arc((29, 58), 22, 0, 1, (38, 41)), 3.5)
        return [(p, [body]), (k, blades + [circle(50, 64, 6.5)]), (p, [circle(50, 64, 3.5)]), (s, shine)]
    if key == "STRATUS":
        bars = [rrect(18, 14, 58, 9), rrect(28, 29, 60, 9), rrect(12, 44, 52, 9)]
        rays = [capsule((a, 64), (b, 94), 5) for a, b in ((40.7, 8), (45.3, 29), (50, 50), (54.7, 71), (59.3, 92))]
        return [(p, bars), (s, rays)]
    raise KeyError(key)


# ------------------------------------------------------------------ kreslení přes masky
class Canvas:
    """RGBA plátno; každá vrstva = maska v odstínech šedi složená barvou přes alpha_composite (žádné tmavé okraje)."""

    def __init__(self, w, h):
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def layer(self, color, opacity=1.0):
        mask = Image.new("L", self.img.size, 0)
        return mask, ImageDraw.Draw(mask), color, opacity

    def put(self, layer):
        mask, _, color, opacity = layer
        if opacity < 1.0:
            mask = mask.point(lambda v: round(v * opacity))
        solid = Image.new("RGBA", self.img.size, rgb(color) + (255,))
        solid.putalpha(mask)
        self.img.alpha_composite(solid)

    def mark(self, key, p, s, x, y, size, k=WHITE):
        sc = size / 100.0
        for color, polys in mark_shapes(key, p, s, k):
            ly = self.layer(color)
            for poly in polys:
                ly[1].polygon([(x + px * sc, y + py * sc) for px, py in poly], fill=255)
            self.put(ly)


def text_runs(key, fg, acc):
    """Nápis (runs: text, písmo, velikost px, letter-spacing em, barva) a podtitul podle word() v HTML."""
    if key == "BZUK":
        word = [("BZUK", "RussoOne-Regular.ttf", None, 32, 0.08, fg)]
        tag, tag_color, tag_gap = "FLYING SPRAYERS", acc, 5
    elif key == "ROSA":
        word = [("ROSA", "Sora-wght.ttf", 800, 30, 0.14, fg)]
        tag, tag_color, tag_gap = "AGRO DRONE SYSTEMS", acc, 5
    elif key == "KAPKA":
        word = [("kapka", "Baloo2-wght.ttf", 800, 36, 0.01, fg)]
        tag, tag_color, tag_gap = "SPRAY DRONES", acc, 0
    elif key == "STRATUS":
        word = [("STRATUS", "BarlowSemiCondensed-ExtraBold.ttf", None, 30, 0.04, fg),
                (" ", "BarlowSemiCondensed-Medium.ttf", None, 30, 0.0, fg),
                ("AGRI", "BarlowSemiCondensed-Medium.ttf", None, 30, 0.0, acc)]
        tag, tag_color, tag_gap = "LOW-ALTITUDE SPRAYING", fg, 5
    else:
        raise KeyError(key)
    return word, (tag, "IBMPlexMono-Medium.ttf", None, 9, 0.16, tag_color), tag_gap


def _draw_run(draw, x, baseline, text, f, spacing):
    for ch in text:
        draw.text((x, baseline), ch, font=f, fill=255, anchor="ls")
        x += f.getlength(ch) + spacing
    return x


def _run_width(text, f, spacing):
    return sum(f.getlength(ch) + spacing for ch in text)


def render_lockup(key, on_dark, scale):
    """Lockup jako .lk v HTML; scale = px na CSS px. Vrací (RGBA, šířka inkoustu, výška layoutu) v px."""
    d = B.DESIGNS[key]
    p = d["pd"] if on_dark else d["p"]
    fg, acc = (d["dark_fg"], d["dark_acc"]) if on_dark else (d["light_fg"], d["light_acc"])
    word, tag, tag_gap = text_runs(key, fg, acc)
    if not on_dark and key == "KAPKA":
        tag = tag[:5] + (p,)                        # světle modrý podtitul z HTML na bílé nejde přečíst
    mark, gap = 54, 12
    word_h = max(r[3] for r in word)
    tag_lh = 1.5 * tag[3]
    block_h = word_h + tag_gap + tag_lh
    H = max(mark, block_h)
    W = mark + gap + 400
    cv = Canvas(int(W * scale), int(H * scale))
    cv.mark(key, p, d["s"], 0, (H - mark) / 2 * scale, mark * scale)
    tx = (mark + gap) * scale
    top = (H - block_h) / 2

    def line(runs, line_top, lh):
        x = tx
        for text, fname, weight, size, ls, color in runs:
            f = font(fname, size * scale, weight)
            asc, desc = f.getmetrics()
            baseline = line_top * scale + (lh * scale - (asc + desc)) / 2 + asc
            ly = cv.layer(color, 0.8 if runs is tag_runs and on_dark else 1.0)
            x = _draw_run(ly[1], x, baseline, text, f, ls * size * scale)
            cv.put(ly)

    tag_runs = [tag]
    line(word, top, word_h)
    line(tag_runs, top + word_h + tag_gap, tag_lh)
    bbox = cv.img.getbbox()
    return cv.img, bbox, H * scale


def fit_lockup(key, on_dark, w, h, margin):
    """Lockup vystředěný do w x h px (vodorovně podle inkoustu, svisle podle layoutu 54 px); vrací (RGBA, podíl šířky, podíl výšky)."""
    probe, bbox, lay_h = render_lockup(key, on_dark, 4.0)
    ink_w = bbox[2] - bbox[0]
    k = min((w - 2 * margin) / (ink_w / 4.0), (h - 2 * margin) / (lay_h / 4.0))
    img, bbox, lay_h = render_lockup(key, on_dark, k * SS)
    crop = img.crop((bbox[0], 0, bbox[2], img.height))
    out = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    out.alpha_composite(crop, ((w * SS - crop.width) // 2, int((h * SS - img.height) / 2)))
    return downsample(out, (w, h)), crop.width / SS / w, img.height / SS / h


def downsample(img, size):
    return img.convert("RGBa").resize(size, Image.BOX).convert("RGBA")


def bleed(img):
    """Průhledným pixelům barvu nejbližšího obsahu (rozmazání s vahou alfy), alfa zůstává."""
    a = np.asarray(img, dtype=np.float32)
    alpha = a[..., 3:4] / 255.0
    pre = Image.fromarray(np.uint8(np.clip(np.concatenate([a[..., :3] * alpha, alpha * 255], -1), 0, 255)), "RGBA")
    out = a.copy()
    todo = a[..., 3] == 0
    for r in (2, 6, 16, 48, 128):
        if not todo.any():
            break
        bl = np.asarray(pre.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32)
        w = bl[..., 3:4] / 255.0
        ok = todo & (bl[..., 3] > 0.5)
        col = bl[..., :3] / np.maximum(w, 1e-4)
        out[ok, :3] = np.clip(col[ok], 0, 255)
        todo &= ~ok
    return Image.fromarray(np.uint8(out), "RGBA")


def main():
    os.makedirs(OUT, exist_ok=True)
    atlas = Image.new("RGBA", (B.ATLAS_SIZE, B.ATLAS_SIZE), (0, 0, 0, 0))
    content = {}
    for key in B.DESIGN_ORDER:
        d = B.DESIGNS[key]
        for kind, on_dark in (("lockupOnDark", True), ("lockupOnLight", False)):
            x, y, w, h = B.REGIONS[f"{kind}_{key}"]
            img, fw, fh = fit_lockup(key, on_dark, w, h, 12)
            atlas.alpha_composite(bleed(img), (x, y))
            content[key] = (round(fw, 3), round(fh, 3))
        x, y, w, h = B.REGIONS[f"mark_{key}"]
        cv = Canvas(w * SS, h * SS)
        m = 8 * SS
        cv.mark(key, d["p"], d["s"], m, m, w * SS - 2 * m)
        atlas.alpha_composite(bleed(downsample(cv.img, (w, h))), (x, y))
        x, y, w, h = B.REGIONS[f"stripe_{key}"]
        cell = Image.new("RGBA", B.STRIPE_CELL, rgb(d["stripe"]) + (255,))
        atlas.alpha_composite(cell, (x - B.STRIPE_INSET, y - B.STRIPE_INSET))
    atlas = bleed(atlas)
    os.makedirs(os.path.dirname(SRC_PNG), exist_ok=True)
    os.makedirs(os.path.dirname(DDS), exist_ok=True)
    atlas.save(SRC_PNG)
    n = png2dds.convert(SRC_PNG, DDS, "dxt5")
    print(f"{SRC_PNG}\n{DDS} ({n} úrovní, {os.path.getsize(DDS):,} B)")
    print("LOCKUP_CONTENT (šířka, výška):", content)

    # značka do obchodu: 512 x 256 jako vanilla, světlý text (UI obchodu je tmavé)
    icon, fw, fh = fit_lockup(B.DEFAULT_DESIGN, True, 512, 256, 8)
    icon = bleed(icon)
    icon_png = os.path.join(OUT, "brand_bzuk.png")
    icon.save(icon_png)
    n = png2dds.convert(icon_png, BRAND_DDS, "dxt5", mips=False)
    print(f"{BRAND_DDS} ({n} úrovní), obsah {fw:.3f} x {fh:.3f}")

    # náhled: atlas na šachovnici a lockupy na tmavé plachtě a světlém laku
    chk = Image.new("RGBA", atlas.size, (90, 90, 90, 255))
    dr = ImageDraw.Draw(chk)
    for yy in range(0, atlas.height, 64):
        for xx in range(0, atlas.width, 64):
            if (xx + yy) // 64 % 2:
                dr.rectangle((xx, yy, xx + 63, yy + 63), fill=(130, 130, 130, 255))
    chk.alpha_composite(atlas)
    chk.convert("RGB").resize((1024, 1024), Image.LANCZOS).save(os.path.join(OUT, "atlas_preview.png"))
    prev = Image.new("RGBA", (1024, 128 * len(B.DESIGN_ORDER)), (0, 0, 0, 255))
    for i, key in enumerate(B.DESIGN_ORDER):
        for j, (kind, bg) in enumerate((("lockupOnDark", B.TARP_COLOR), ("lockupOnLight", "#e6ecf1"))):
            x, y, w, h = B.REGIONS[f"{kind}_{key}"]
            tile = Image.new("RGBA", (w, h), rgb(bg) + (255,))
            tile.alpha_composite(atlas.crop((x, y, x + w, y + h)))
            prev.alpha_composite(tile.resize((512, 128), Image.LANCZOS), (512 * j, 128 * i))
    prev.convert("RGB").save(os.path.join(OUT, "lockups_preview.png"))


if __name__ == "__main__":
    main()
