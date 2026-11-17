"""Potisk big bagu na jemně mleté vápno (1024x512 PNG, UV vanilla vaku objects/bigBag/bigBag.i3d) ve stejném stylu jako pytel limeBag50.

python blender\\limebigbag_label.py <výstupní složka>   ->  limebigbag_diffuse.png

Rozložení UV vanilla vaku (ověřeno importem i3d do Blenderu): pás těla přes x 0..~900 jsou čtyři boky vaku po ~224 px (vanilla štítky jsou
na středech prvního a třetího boku, x 115 a 563, y 350), nad ním (y < 262) je sbíraná horní část, vpravo nahoře (x 797..927, y 8..105) poutka
a vpravo dvě půlkruhová víka. Vak je tkanina s jemnou mřížkou; štítek (bílý se zeleným rámem, BZUK, VÁPNO a „jemně mleté vápno“) je na všech
čtyřech bocích a přes tělo vedou dva zelené pruhy jako na pytli. Zapisuje se do mod/objects/limeBigBag/textures/ přes tools/png2dds.py.
"""

import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canister_labels as CL  # noqa: E402

SS = CL.SS
W, H = 1024, 512
FABRIC = (186, 182, 172)
GREEN = (122, 184, 28)
DARK = (58, 110, 14)
INK = CL.INK
GREY = CL.GREY
STRAP = (52, 52, 54)
FACE_W = 224
FACE_X0 = 3            # začátek prvního boku
BODY_END = 900         # konec pásu těla
LABEL_W, LABEL_H = 184, 136
LABEL_Y0 = 284         # horní okraj štítku (střed štítku ~ y 352, jako u vanilla)
STRIPES = ((266, 276), (440, 450))


def fabric():
    img = Image.new("RGB", (W, H), FABRIC)
    px = img.load()
    rnd = random.Random(7)
    for y in range(H):
        for x in range(W):
            weave = 5 if (x // 2 + y // 2) % 2 == 0 else 0
            n = rnd.randint(-4, 4)
            r, g, b = FABRIC
            px[x, y] = (r - weave + n, g - weave + n, b - weave + n)
    return img


def label():
    w, h = LABEL_W * SS, LABEL_H * SS
    img = Image.new("RGB", (w, h), (250, 250, 247))
    d = ImageDraw.Draw(img)
    frame = 5 * SS
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=10 * SS, fill=(250, 250, 247), outline=GREEN, width=frame)
    ix0, ix1 = 14 * SS, w - 14 * SS
    mark_h = 24
    mark = CL.brand_mark(mark_h * SS)
    img.paste(mark, (ix0, 12 * SS), mark)
    CL.text(d, 14 + mark_h + 6, 12 + mark_h * 0.74, "BZUK", CL.font("arialbd.ttf", 22), DARK, spacing=1.0)
    info = "1000 l"
    d.text((ix1, (12 + mark_h * 0.74) * SS), info, font=CL.font("arialbd.ttf", 18), fill=INK, anchor="rs")
    d.rectangle((ix0, 42 * SS, ix1, 46 * SS), fill=GREEN)
    inner = ix1 - ix0
    size = 52
    while d.textlength("VÁPNO", font=CL.font("arialbd.ttf", size)) > inner and size > 20:
        size -= 1
    CL.text(d, 14, 96, "VÁPNO", CL.font("arialbd.ttf", size), INK)
    sub = 19
    while d.textlength("jemně mleté vápno", font=CL.font("arial.ttf", sub)) > inner and sub > 10:
        sub -= 1
    CL.text(d, 15, 123, "jemně mleté vápno", CL.font("arial.ttf", sub), GREY)
    return img.resize((LABEL_W, LABEL_H), Image.LANCZOS)


def make(out):
    img = fabric()
    d = ImageDraw.Draw(img)
    for y0, y1 in STRIPES:
        d.rectangle((0, y0, BODY_END, y1), fill=GREEN)
    d.rounded_rectangle((790, 4, 936, 108), radius=30, fill=STRAP)
    lab = label()
    for face in range(4):
        cx = FACE_X0 + FACE_W * face + FACE_W // 2
        img.paste(lab, (cx - LABEL_W // 2, LABEL_Y0))
    path = os.path.join(out, "limebigbag_diffuse.png")
    img.save(path)
    return path


if __name__ == "__main__":
    os.makedirs(sys.argv[1], exist_ok=True)
    print(make(sys.argv[1]))
