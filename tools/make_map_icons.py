"""Ikony pro plánovač na mapě (vlek s dronem): kreslí Pillow v 4x nadvzorkování a ukládá PNG i DDS (DXT5 s mipmapami).

python tools/make_map_icons.py
"""

import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "mod", "FS25_SprayDroneTrailer", "gui", "icons")
TMP = os.path.join(os.path.dirname(HERE), "out", "icons")
SIZE = 128
SS = 4


def drone(path):
    n = SIZE * SS
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = int(n * 0.04)
    d.ellipse((m, m, n - m, n - m), fill=(20, 20, 20, 255))
    m2 = int(n * 0.10)
    d.ellipse((m2, m2, n - m2, n - m2), fill=(245, 245, 245, 255))
    c = n / 2
    arm = n * 0.20
    ink = (25, 25, 25, 255)
    for sx in (-1, 1):
        for sy in (-1, 1):
            d.line((c, c, c + sx * arm, c + sy * arm), fill=ink, width=int(n * 0.06))
            rx, ry, r = c + sx * arm, c + sy * arm, n * 0.095
            d.ellipse((rx - r, ry - r, rx + r, ry + r), fill=ink)
    b = n * 0.085
    d.ellipse((c - b, c - b, c + b, c + b), fill=ink)
    im.resize((SIZE, SIZE), Image.LANCZOS).save(path)


def trailer(path):
    """Bílý kotouč s černým obrysem a černou siluetou vleku zboku: ložná plocha s nádrží, kola a oj."""
    n = SIZE * SS
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = int(n * 0.04)
    d.ellipse((m, m, n - m, n - m), fill=(20, 20, 20, 255))
    m2 = int(n * 0.10)
    d.ellipse((m2, m2, n - m2, n - m2), fill=(245, 245, 245, 255))
    ink = (25, 25, 25, 255)
    c = n / 2
    d.rectangle((c - n * 0.25, c + n * 0.02, c + n * 0.24, c + n * 0.09), fill=ink)
    d.ellipse((c - n * 0.18, c - n * 0.17, c + n * 0.10, c + n * 0.03), fill=ink)
    d.rectangle((c + n * 0.10, c - n * 0.14, c + n * 0.22, c + n * 0.03), outline=ink, width=int(n * 0.025))
    d.line((c - n * 0.25, c + n * 0.07, c - n * 0.36, c + n * 0.07), fill=ink, width=int(n * 0.035))
    for wx in (c - n * 0.06, c + n * 0.12):
        r = n * 0.065
        d.ellipse((wx - r, c + n * 0.13 - r, wx + r, c + n * 0.13 + r), fill=ink)
    im.resize((SIZE, SIZE), Image.LANCZOS).save(path)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    for name, fn in (("mapTrailer", trailer), ("mapDrone", drone)):
        png = os.path.join(TMP, name + ".png")
        fn(png)
        dds = os.path.join(OUT, name + ".dds")
        subprocess.check_call([sys.executable, os.path.join(HERE, "png2dds.py"), png, dds, "--format", "dxt5"])
        print(dds)


main()
