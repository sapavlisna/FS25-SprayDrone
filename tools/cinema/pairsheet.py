"""Sloučí kontaktní archy více záznamů pod sebe (vyrobí je clipsheet.py, pokud chybí).

python tools/cinema/pairsheet.py <výstup> <záznam1> <záznam2> ... [--fps 0.8] [--cols 5] [--w 384]
-> out/trailer/raw/<výstup>_pair.jpg
"""

import argparse
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = r"E:\ClaudeProjects\FS25-SprayDrone\out\trailer\raw"
ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("clips", nargs="+")
ap.add_argument("--fps", default="0.8")
ap.add_argument("--cols", default="5")
ap.add_argument("--w", default="384")
a = ap.parse_args()
ims = []
for c in a.clips:
    subprocess.run([sys.executable, os.path.join(HERE, "clipsheet.py"), c, a.fps, a.cols, a.w], check=True, capture_output=True)
    ims.append(Image.open(os.path.join(RAW, c + "_sheet.jpg")))
w = max(i.width for i in ims)
sheet = Image.new("RGB", (w, sum(i.height for i in ims) + 8 * len(ims)), "red")
y = 0
for i in ims:
    sheet.paste(i, (0, y))
    y += i.height + 8
out = os.path.join(RAW, a.out + "_pair.jpg")
sheet.save(out, quality=85)
print(out, sheet.size)
