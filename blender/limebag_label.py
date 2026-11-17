"""Potisk pytle jemně mletého vápna (1024x512 PNG) pro build_limebag.py; běží v systémovém Pythonu (Pillow).

python blender\\limebag_label.py <výstupní složka> <litrů> <kg>

Textura pokrývá celý pytel shora (u = x od konce ke konci, v = y přes šířku; poměr stran pytle je u všech velikostí stejný 1,73 : 1,
kreslí se v poměru stran 1024 x 593 a před uložením se stlačí na 1024 x 512, takže na modelu není písmo zkreslené). Okraje (lisované konce,
boky) zůstávají čistý papír, tam se textura natahuje. Výstup limebag<litrů>_label.png.
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canister_labels as CL  # noqa: E402

SS = CL.SS
W, H = 1024, 593
PAPER = (238, 238, 232)
GREEN = (122, 184, 28)
DARK = (58, 110, 14)
INK = CL.INK
GREY = CL.GREY


def make(out, liters, kg):
    img = Image.new("RGB", (W * SS, H * SS), PAPER)
    d = ImageDraw.Draw(img)
    # papírová vlákna: jemný šum, ať pytel není hladká plocha
    noise = Image.effect_noise((W * SS // 4, H * SS // 4), 14).convert("RGB").resize((W * SS, H * SS), Image.BILINEAR)
    img = Image.blend(img, noise, 0.05)
    d = ImageDraw.Draw(img)
    # zelené pruhy přes celou délku těla pytle (nejsou na lisovaných koncích)
    for y0, y1 in ((60, 104), (489, 533)):
        d.rectangle((86 * SS, y0 * SS, (W - 86) * SS, y1 * SS), fill=GREEN)
    # štítek uprostřed: nízký (hřbet pytle je u okrajů v příčném směru zakřivený), obsah se rozkládá do vnitřního pole
    # (rámeček + odsazení) podle změřených obrysů písma a nic nesmí přečnívat
    x0, y0, x1, y1 = 150, 148, 874, 446
    frame_w, pad = 10, 26
    d.rounded_rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS), radius=18 * SS, fill=(250, 250, 247), outline=GREEN, width=frame_w * SS)
    hpad = 42
    ix0, iy0, ix1, iy1 = x0 + frame_w + hpad, y0 + frame_w + pad, x1 - frame_w - hpad, y1 - frame_w - pad
    mark_h = 56
    rule_h = 5
    info = "%d l  |  cca %d kg" % (liters, kg)
    info_font = CL.font("arialbd.ttf", 30)
    rows = [
        ("VÁPNO", CL.font("arialbd.ttf", 100), INK),
        ("jemně mleté vápno", CL.font("arial.ttf", 38), GREY),
    ]
    boxes = [d.textbbox((0, 0), t, font=f, anchor="ls") for t, f, _ in rows]
    heights = [(bb[3] - bb[1]) / SS for bb in boxes]
    widths = [(bb[2] - bb[0]) / SS for bb in boxes]
    info_w = d.textlength(info, font=info_font) / SS
    brand_w = mark_h + 16 + d.textlength("BZUK", font=CL.font("arialbd.ttf", 50)) / SS
    assert max(widths) <= ix1 - ix0 and brand_w + 40 + info_w <= ix1 - ix0, "text se nevejde na šířku štítku"
    free = (iy1 - iy0) - mark_h - rule_h - sum(heights)
    assert free >= 3 * 10, "text se nevejde na výšku štítku: volno %.1f px" % free
    gap = free / 3
    y = iy0
    mark = CL.brand_mark(mark_h * SS)
    img.paste(mark, (ix0 * SS, round(y * SS)), mark)
    CL.text(d, ix0 + mark_h + 16, y + mark_h * 0.72, "BZUK", CL.font("arialbd.ttf", 50), DARK, spacing=2.0)
    CL.text(d, ix1, y + mark_h * 0.72, info, info_font, INK, anchor="rs")
    y += mark_h + gap
    d.rectangle((ix0 * SS, round(y * SS), ix1 * SS, round((y + rule_h) * SS)), fill=GREEN)
    y += rule_h
    for (text, fnt, ink), bb, h, w in zip(rows, boxes, heights, widths):
        y += gap
        CL.text(d, ix0 - bb[0] / SS, y - bb[1] / SS, text, fnt, ink)
        print("  %-20s x %.0f..%.0f  y %.0f..%.0f  (pole x %d..%d, y %d..%d)" % (text.encode("ascii", "replace").decode(), ix0, ix0 + w, y, y + h, ix0, ix1, iy0, iy1))
        y += h
    assert y <= iy1 + 0.5
    path = os.path.join(out, "limebag%d_label.png" % liters)
    img.resize((W, 512), Image.LANCZOS).save(path)
    return path


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    print(make(out, int(sys.argv[2]), int(sys.argv[3])))


if __name__ == "__main__":
    main()
