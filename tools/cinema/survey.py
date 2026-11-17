"""Rychlý průzkum pohledů kamery bez záznamu: python tools/cinema/survey.py <poses.json> [sloupců=3] [šířka=640]

poses.json = seznam objektů s parametry camSet (x y z rel at tx ty tz trel tat fov) a "name"; každý pohled se nasnímá (PrintWindow, offscreen)
a složí do out/trailer/survey/<jméno souboru>.png. Příkaz "pre" (volitelné pole v objektu: {"cmd": ..., ...}) se provede před pohledem.
"""

import json
import os
import subprocess
import sys
import time

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cinema_client import send  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAPTURE = os.path.join(ROOT, "tools", "fs25_capture.ps1")
OUT = os.path.join(ROOT, "out", "trailer", "survey")

poses = json.load(open(sys.argv[1], encoding="utf-8"))
cols = int(sys.argv[2]) if len(sys.argv) > 2 else 3
tw = int(sys.argv[3]) if len(sys.argv) > 3 else 640
base = os.path.splitext(os.path.basename(sys.argv[1]))[0]
os.makedirs(OUT, exist_ok=True)
files = []
for i, p in enumerate(poses):
    p = dict(p)
    name = p.pop("name", "p%d" % i)
    for pre in p.pop("pre", []):
        pre = dict(pre)
        ok, msg = send(pre.pop("cmd"), timeout=float(pre.pop("timeout", 30)), **pre)
        print("pre", ok, msg[:120])
    ok, msg = send("camSet", timeout=10, **p)
    if not ok:
        print(name, "ERR", msg)
        continue
    time.sleep(float(p.get("settle", 1.2)))
    tag = "%s_%02d" % (base, i)
    subprocess.run(["powershell", "-NoProfile", "-File", CAPTURE, tag, "-Scale", "0.5"], capture_output=True, text=True)
    src = os.path.join(ROOT, "out", "mod_build", tag + ".png")
    dst = os.path.join(OUT, tag + ".png")
    if os.path.exists(src):
        os.replace(src, dst)
        files.append((name, dst))
send("camStop", timeout=10)
ims = []
for name, f in files:
    im = Image.open(f).convert("RGB")
    im = im.resize((tw, int(tw * im.height / im.width)))
    ImageDraw.Draw(im).text((8, 8), name, fill=(255, 255, 0))
    ims.append(im)
if ims:
    th = ims[0].height
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    out = os.path.join(OUT, base + ".png")
    sheet.save(out)
    print(out)
