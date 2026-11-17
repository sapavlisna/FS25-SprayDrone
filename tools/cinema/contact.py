"""Kontaktní list z náhledů scény: python tools/cinema/contact.py <scéna> [sloupců=4] [šířka dlaždice=480] -> out/trailer/preview/<scéna>/contact.png"""

import glob
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
scene = sys.argv[1]
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 4
tw = int(sys.argv[3]) if len(sys.argv) > 3 else 480
folder = os.path.join(ROOT, "out", "trailer", "preview", scene)
files = sorted(f for f in glob.glob(os.path.join(folder, scene + "_*.png")))
ims = [Image.open(f) for f in files]
th = int(tw * ims[0].height / ims[0].width)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th))
for i, im in enumerate(ims):
    sheet.paste(im.convert("RGB").resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
out = os.path.join(folder, "contact.png")
sheet.save(out)
print(out, len(ims), "snímků")
