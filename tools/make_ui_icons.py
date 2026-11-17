"""Bílé ikony karty plánu a seznamu polí v plánovači (barví je hra přes Overlay:setColor): kreslí Pillow ve 4x nadvzorkování,
ukládá PNG do out/icons a DDS (DXT5 s mipmapami) do gui/icons.

python tools/make_ui_icons.py
"""

import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "mod", "FS25_SprayDroneTrailer", "gui", "icons")
TMP = os.path.join(os.path.dirname(HERE), "out", "icons")
SIZE = 64
SS = 4
N = SIZE * SS
W = (255, 255, 255, 255)


def canvas():
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def s(v):
    return v * N


def batches(d):
    for i, y in enumerate((0.62, 0.45, 0.28)):
        d.rounded_rectangle((s(0.16), s(y), s(0.84), s(y + 0.14)), radius=s(0.04), fill=W)


def time(d):
    d.ellipse((s(0.1), s(0.1), s(0.9), s(0.9)), outline=W, width=int(s(0.09)))
    d.line((s(0.5), s(0.5), s(0.5), s(0.24)), fill=W, width=int(s(0.08)))
    d.line((s(0.5), s(0.5), s(0.69), s(0.6)), fill=W, width=int(s(0.08)))


def area(d):
    d.line((s(0.1), s(0.1), s(0.1), s(0.9), s(0.9), s(0.9)), fill=W, width=int(s(0.07)), joint="curve")
    d.rectangle((s(0.26), s(0.12), s(0.88), s(0.74)), outline=W, width=int(s(0.07)))
    d.line((s(0.26), s(0.74), s(0.88), s(0.12)), fill=W, width=int(s(0.05)))


def liquid(d):
    d.polygon([(s(0.5), s(0.08)), (s(0.22), s(0.55)), (s(0.78), s(0.55))], fill=W)
    d.ellipse((s(0.22), s(0.34), s(0.78), s(0.9)), fill=W)


def diesel(d):
    d.rounded_rectangle((s(0.18), s(0.22), s(0.7), s(0.9)), radius=s(0.06), fill=W)
    d.rectangle((s(0.3), s(0.1), s(0.5), s(0.22)), fill=W)
    d.line((s(0.7), s(0.35), s(0.84), s(0.45), s(0.84), s(0.8)), fill=W, width=int(s(0.07)))
    d.rectangle((s(0.3), s(0.36), s(0.58), s(0.5)), fill=(0, 0, 0, 0))


def battery(d):
    d.rounded_rectangle((s(0.1), s(0.28), s(0.82), s(0.74)), radius=s(0.05), outline=W, width=int(s(0.08)))
    d.rectangle((s(0.82), s(0.42), s(0.92), s(0.6)), fill=W)
    d.rectangle((s(0.2), s(0.38), s(0.56), s(0.64)), fill=W)


def transit(d):
    d.line((s(0.08), s(0.86), s(0.92), s(0.86)), fill=W, width=int(s(0.07)))
    d.line((s(0.5), s(0.74), s(0.5), s(0.2)), fill=W, width=int(s(0.08)))
    d.polygon([(s(0.5), s(0.06)), (s(0.32), s(0.3)), (s(0.68), s(0.3))], fill=W)


def weather(d):
    for y, x2 in ((0.3, 0.7), (0.5, 0.86), (0.7, 0.6)):
        d.line((s(0.1), s(y), s(x2), s(y)), fill=W, width=int(s(0.08)))
    d.arc((s(0.56), s(0.14), s(0.84), s(0.42)), 200, 90, fill=W, width=int(s(0.07)))
    d.arc((s(0.72), s(0.34), s(1.0), s(0.62)), 200, 90, fill=W, width=int(s(0.07)))


def scan(d):
    for i in range(3):
        for j in range(3):
            x, y = 0.12 + i * 0.27, 0.12 + j * 0.27
            d.rectangle((s(x), s(y), s(x + 0.22), s(y + 0.22)), fill=W if (i + j) % 2 == 0 else None, outline=W,
                        width=int(s(0.04)))


def field(d):
    d.polygon([(s(0.08), s(0.78)), (s(0.3), s(0.18)), (s(0.92), s(0.26)), (s(0.84), s(0.86))], fill=W)


def drone(d):
    c = s(0.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            d.line((c, c, c + sx * s(0.27), c + sy * s(0.27)), fill=W, width=int(s(0.08)))
            r = s(0.15)
            d.ellipse((c + sx * s(0.27) - r, c + sy * s(0.27) - r, c + sx * s(0.27) + r, c + sy * s(0.27) + r),
                      outline=W, width=int(s(0.06)))
    d.ellipse((c - s(0.12), c - s(0.12), c + s(0.12), c + s(0.12)), fill=W)


ICONS = {
    "uiBatches": batches, "uiTime": time, "uiArea": area, "uiLiquid": liquid, "uiDiesel": diesel, "uiBattery": battery,
    "uiTransit": transit, "uiWeather": weather, "uiScan": scan, "uiField": field, "uiDrone": drone, "uiHeader": drone,
}


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    for name, fn in ICONS.items():
        im, d = canvas()
        fn(d)
        png = os.path.join(TMP, name + ".png")
        im.resize((SIZE, SIZE), Image.LANCZOS).save(png)
        dds = os.path.join(OUT, name + ".dds")
        subprocess.check_call([sys.executable, os.path.join(HERE, "png2dds.py"), png, dds, "--format", "dxt5"])
        print(dds)


main()
