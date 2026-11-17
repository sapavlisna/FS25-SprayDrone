"""Grafika střihu: titulky (dolní třetina s klávesovými štítky) a karty (titulní, kapitolová, postupová, závěrečná) jako PNG přes Pillow.

Texty podporují značku [Alt+8] = zaoblené klávesové štítky "Alt" "8". Vše se kreslí 2x a zmenšuje (antialiasing zaoblených tvarů).
Soubory se cachují podle obsahu v <work>/gfx.
"""

import hashlib
import json
import os
import re
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
SS = 2
ACCENT = (244, 180, 0)
FONT_DIR = r"C:\Windows\Fonts"
FONTS = {"reg": "segoeui.ttf", "semi": "seguisb.ttf", "bold": "segoeuib.ttf", "light": "segoeuil.ttf"}


@lru_cache(maxsize=None)
def font(kind, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS[kind]), int(round(size * SS)))


def parse(text):
    out = []
    for part in re.split(r"(\[[^\]]+\])", text):
        if part.startswith("[") and part.endswith("]"):
            out.append(("k", [k.strip() for k in part[1:-1].split("+")]))
        else:
            for w in re.findall(r"\S+|\s+", part):
                out.append(("s" if w.isspace() else "w", w))
    return out


def chip_w(label, size):
    f = font("semi", size * 0.80)
    return max(size * 1.27, f.getlength(label) / SS + size * 0.75)


def item_width(it, kind, size):
    f = font(kind, size)
    if it[0] in ("w", "s"):
        return f.getlength(it[1]) / SS
    gap = size * 0.5
    ws = [chip_w(k, size) for k in it[1]]
    return sum(ws) + gap * (len(ws) - 1) + size * 0.3


def layout(text, kind, size, maxw):
    items = parse(text)
    lines, cur, curw = [], [], 0.0
    for it in items:
        w = item_width(it, kind, size)
        if it[0] == "s":
            if cur:
                cur.append((it, w))
                curw += w
            continue
        if cur and curw + w > maxw:
            while cur and cur[-1][0][0] == "s":
                curw -= cur[-1][1]
                cur.pop()
            lines.append((cur, curw))
            cur, curw = [], 0.0
        cur.append((it, w))
        curw += w
    while cur and cur[-1][0][0] == "s":
        curw -= cur[-1][1]
        cur.pop()
    if cur:
        lines.append((cur, curw))
    return lines or [([], 0.0)]


def draw_chip(d, x, base, label, size):
    S = SS
    w = chip_w(label, size)
    h = size * 1.2
    top = base - size * 0.93
    r = h * 0.24
    sh = size * 0.1
    box = [x * S, top * S, (x + w) * S, (top + h) * S]
    d.rounded_rectangle([box[0], box[1] + sh * S, box[2], box[3] + sh * S], r * S, fill=(112, 114, 118, 255))
    d.rounded_rectangle(box, r * S, fill=(250, 250, 248, 255), outline=(196, 198, 200, 255), width=max(1, int(S * 1.2)))
    f = font("semi", size * 0.80)
    d.text(((x + w / 2) * S, (top + h / 2) * S + 1), label, font=f, fill=(30, 32, 36, 255), anchor="mm")
    return w


def draw_items(d, x, base, line, kind, size, color):
    S = SS
    f = font(kind, size)
    for it, w in line:
        if it[0] in ("w", "s"):
            if it[0] == "w":
                d.text((x * S, base * S), it[1], font=f, fill=color, anchor="ls")
        else:
            cx = x + size * 0.15
            gap = size * 0.5
            for i, k in enumerate(it[1]):
                if i:
                    d.text(((cx + gap / 2) * S, (base - size * 0.28) * S), "+", font=font("semi", size * 0.62), fill=(215, 215, 215, 255), anchor="mm")
                    cx += gap
                cx += draw_chip(d, cx, base, k, size)
        x += w
    return x


def work_dir(work):
    p = os.path.join(work, "gfx")
    os.makedirs(p, exist_ok=True)
    return p


def cached(work, spec, ext, render):
    key = hashlib.sha1(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    path = os.path.join(work_dir(work), "%s_%s.%s" % (spec["fn"], key, ext))
    if not os.path.exists(path):
        img = render()
        img.save(path)
    return path


def caption_png(work, lines, hd_size=46):
    """lines[0] = hlavní řádek (tučně), další = postup. Vrací (cesta, x, y, w, h) pro overlay (výchozí 1920x1080)."""
    spec = {"fn": "cap", "lines": lines, "sz": hd_size}
    meta = {}

    def render():
        sizes = [hd_size] + [hd_size * 0.76] * (len(lines) - 1)
        kinds = ["bold"] + ["reg"] * (len(lines) - 1)
        padx, pady, stripe, maxw = 44, 28, 12, 1480
        laid = []
        for t, k, s in zip(lines, kinds, sizes):
            laid.append((layout(t, k, s, maxw), k, s))
        contw = max(max(w for _, w in L) for L, _, _ in laid)
        boxw = int(contw + padx * 2 + stripe)
        boxh = pady * 2
        rows = []
        for gi, (L, k, s) in enumerate(laid):
            for (line, w) in L:
                lh = s * 1.42
                rows.append((line, k, s, boxh, lh))
                boxh += lh
            boxh += s * 0.12
        boxh = int(boxh - (laid[-1][2] * 0.12) + 4)
        m = 44
        cw, ch = boxw + 2 * m, boxh + 2 * m
        S = SS
        canvas = Image.new("RGBA", (cw * S, ch * S), (0, 0, 0, 0))
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([m * S, (m + 6) * S, (m + boxw) * S, (m + 6 + boxh) * S], 24 * S, fill=(0, 0, 0, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(14 * S))
        canvas = Image.alpha_composite(canvas, sh)
        bar = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(bar)
        bd.rounded_rectangle([m * S, m * S, (m + boxw) * S, (m + boxh) * S], 24 * S, fill=(9, 11, 15, 205))
        bd.rounded_rectangle([m * S, m * S, (m + stripe) * S, (m + boxh) * S], 6 * S, fill=ACCENT + (255,))
        bd.rectangle([(m + 6) * S, m * S, (m + stripe) * S, (m + boxh) * S], fill=ACCENT + (255,))
        canvas = Image.alpha_composite(canvas, bar)
        d = ImageDraw.Draw(canvas)
        for line, k, s, top, lh in rows:
            base = m + top + s * 1.03 + (lh - s * 1.42) / 2
            col = (255, 255, 255, 255) if k == "bold" else (226, 228, 230, 255)
            draw_items(d, m + stripe + padx, base, line, k, s, col)
        meta["size"] = (cw, ch)
        return canvas.resize((cw, ch), Image.LANCZOS)

    path = cached(work, spec, "png", render)
    with Image.open(path) as im:
        cw, ch = im.size
    x = 110 - 44
    y = H - 96 - (ch - 44)
    return path, x, y, cw, ch


def gradient_bg(top, bottom):
    col = Image.new("RGB", (1, H))
    px = col.load()
    for y in range(H):
        t = y / (H - 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return col.resize((W, H), Image.NEAREST)


def vignette_bg(center=(26, 34, 30), edge=(4, 6, 6)):
    small = Image.new("RGB", (96, 54))
    px = small.load()
    for y in range(54):
        for x in range(96):
            dx, dy = (x - 47.5) / 47.5, (y - 26.5) / 26.5
            t = min(1.0, (dx * dx * 0.55 + dy * dy * 0.9) ** 0.5)
            px[x, y] = tuple(int(center[i] + (edge[i] - center[i]) * t) for i in range(3))
    return small.resize((W, H), Image.BICUBIC)


def spaced(d, xy, text, f, fill, spacing, anchor="center", S=SS):
    widths = [f.getlength(c) for c in text]
    total = sum(widths) + spacing * S * (len(text) - 1)
    x, y = xy
    if anchor == "center":
        x = x - total / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=f, fill=fill, anchor="ls")
        x += w + spacing * S


def card_png(work, kind, data, brand, chapters=None, credit=None):
    spec = {"fn": "card_" + kind, "data": data, "brand": brand, "ch": chapters, "credit": credit}

    def render():
        S = SS
        if kind in ("title", "end"):
            bg = vignette_bg().convert("RGBA").resize((W * S, H * S), Image.BICUBIC)
            d = ImageDraw.Draw(bg)
            cy = H / 2 - (40 if kind == "end" else 20)
            size = 170 if kind == "title" else 150
            spaced(d, (W * S / 2, (cy + size * 0.28) * S), brand["title"], font("bold", size), (255, 255, 255, 255), 8)
            d.rounded_rectangle([(W / 2 - 90) * S, (cy + 84) * S, (W / 2 + 90) * S, (cy + 92) * S], 4 * S, fill=ACCENT + (255,))
            d.text((W * S / 2, (cy + 168) * S), brand["subtitle"], font=font("light", 58), fill=(214, 218, 216, 255), anchor="mm")
            if kind == "end" and credit:
                lines = layout(credit, "reg", 36, 1500)
                y = H - 150
                for line, w in lines:
                    draw_items(d, (W - w) / 2, y, line, "reg", 36, (178, 184, 182, 255))
                    y += 52
            return bg.resize((W, H), Image.LANCZOS)
        if kind == "chapter":
            bg = gradient_bg((20, 28, 34), (8, 12, 15)).convert("RGBA").resize((W * S, H * S), Image.BICUBIC)
            d = ImageDraw.Draw(bg)
            num = data["id"][1:]
            big = Image.new("RGBA", bg.size, (0, 0, 0, 0))
            ImageDraw.Draw(big).text(((W - 120) * S, (H / 2 + 230) * S), num, font=font("bold", 760), fill=(255, 255, 255, 22), anchor="rs")
            bg = Image.alpha_composite(bg, big)
            d = ImageDraw.Draw(bg)
            spaced(d, (170 * S, (H / 2 - 100) * S), "KAPITOLA %s" % num, font("semi", 40), ACCENT + (255,), 7, anchor="left")
            d.text((170 * S, (H / 2 + 30) * S), data["title"], font=font("bold", 118), fill=(255, 255, 255, 255), anchor="ls")
            d.rounded_rectangle([170 * S, (H / 2 + 62) * S, 290 * S, (H / 2 + 70) * S], 4 * S, fill=ACCENT + (255,))
            if data.get("sub"):
                y = H / 2 + 150
                for line, w in layout(data["sub"], "light", 46, 1350):
                    draw_items(d, 170, y, line, "light", 46, (200, 206, 204, 255))
                    y += 66
            return bg.resize((W, H), Image.LANCZOS)
        bg = gradient_bg((22, 31, 36), (10, 14, 17)).convert("RGBA").resize((W * S, H * S), Image.BICUBIC)
        d = ImageDraw.Draw(bg)
        d.text((160 * S, 190 * S), data["title"], font=font("bold", 84), fill=(255, 255, 255, 255), anchor="ls")
        d.rounded_rectangle([160 * S, 222 * S, 280 * S, 230 * S], 4 * S, fill=ACCENT + (255,))
        if kind == "chapters":
            rows = [("%s" % c["id"][1:], c["title"]) for c in chapters if c["id"] not in ("K0", "K8")]
            numbered = True
        else:
            rows = [(str(i + 1), t) for i, t in enumerate(data["lines"])]
            numbered = data.get("numbered", False)
        y = 330
        size = 46
        for i, (n, t) in enumerate(rows):
            tx = 260 if numbered else 200
            laid = layout(t, "reg", size, 1900 - tx - 140)
            lh = size * 1.45
            if numbered:
                cx, cy = 160 + 36, y + size * 0.55
                d.ellipse([(cx - 36) * S, (cy - 36) * S, (cx + 36) * S, (cy + 36) * S], fill=ACCENT + (255,))
                d.text((cx * S, cy * S + 2), n, font=font("bold", 40), fill=(20, 20, 20, 255), anchor="mm")
            else:
                d.ellipse([(168) * S, (y + size * 0.42) * S, (192) * S, (y + size * 0.42 + 24) * S], fill=ACCENT + (255,))
            for line, w in laid:
                draw_items(d, tx, y + size * 1.0, line, "reg", size, (236, 238, 238, 255))
                y += lh
            y += size * 0.65
        if data.get("draft"):
            f = font("semi", 30)
            label = "NÁVRH TEXTU"
            tw = f.getlength(label) / S
            x0, y0 = W - 160 - tw - 44, 120
            d.rounded_rectangle([x0 * S, y0 * S, (x0 + tw + 44) * S, (y0 + 56) * S], 14 * S, outline=ACCENT + (255,), width=3 * S)
            d.text(((x0 + (tw + 44) / 2) * S, (y0 + 28) * S), label, font=f, fill=ACCENT + (255,), anchor="mm")
        return bg.resize((W, H), Image.LANCZOS)

    return cached(work, spec, "png", render)
