"""Ikony relé tyče pro plánovač (mapRelay aktivní, mapRelayOff neaktivní) stejným postupem jako tools/make_map_icons.py:
Pillow v 4x nadvzorkování -> PNG -> tools/png2dds.py (DXT5 s mipmapami).

python tools/make_relay_icon.py
"""

import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "mod", "FS25_SprayDroneTrailer", "gui", "icons")
TMP = os.path.join(ROOT, "out", "icons")
SIZE = 128
SS = 4


def relay(path, active):
    """Kotouč s obrysem, tyč na stativu s anténou nahoře; aktivní má oranžové vlny signálu, neaktivní je šedý bez vln."""
    n = SIZE * SS
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = int(n * 0.04)
    d.ellipse((m, m, n - m, n - m), fill=(20, 20, 20, 255))
    m2 = int(n * 0.10)
    d.ellipse((m2, m2, n - m2, n - m2), fill=(245, 245, 245, 255) if active else (150, 150, 150, 255))
    ink = (25, 25, 25, 255) if active else (70, 70, 70, 255)
    c = n / 2
    top, foot = c - n * 0.17, c + n * 0.27
    hub = c + n * 0.10
    d.line((c, top, c, hub), fill=ink, width=int(n * 0.05))
    for sx in (-1, 0, 1):
        d.line((c, hub, c + sx * n * 0.17, foot), fill=ink, width=int(n * 0.04))
    r = n * 0.055
    d.ellipse((c - r, top - r, c + r, top + r), fill=ink)
    if active:
        wave = (235, 130, 20, 255)
        for k, rr in enumerate((n * 0.12, n * 0.20)):
            box = (c - rr, top - rr, c + rr, top + rr)
            w = int(n * 0.035)
            d.arc(box, 200, 250, fill=wave, width=w)
            d.arc(box, 290, 340, fill=wave, width=w)
    im.resize((SIZE, SIZE), Image.LANCZOS).save(path)


def main():
    os.makedirs(TMP, exist_ok=True)
    for name, active in (("mapRelay", True), ("mapRelayOff", False)):
        png = os.path.join(TMP, name + ".png")
        relay(png, active)
        dds = os.path.join(OUT, name + ".dds")
        subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "png2dds.py"), png, dds, "--format", "dxt5"])
        print(dds)


main()
