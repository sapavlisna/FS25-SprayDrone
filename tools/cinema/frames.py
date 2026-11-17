"""Kontrolní snímky z klipu: python tools/cinema/frames.py <klip bez přípony> t1,t2,... [šířka]
Uloží out/trailer/check/<klip>_<t>.jpg a mozaiku out/trailer/check/<klip>_sheet.jpg (snímky vedle sebe, po 3 ve sloupci mřížky).
"""

import os
import subprocess
import sys

FFMPEG = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
ROOT = r"E:\ClaudeProjects\FS25-SprayDrone"
RAW = os.path.join(ROOT, "out", "trailer", "raw")
CHECK = os.path.join(ROOT, "out", "trailer", "check")

name = sys.argv[1]
times = [float(t) for t in sys.argv[2].split(",")]
width = int(sys.argv[3]) if len(sys.argv) > 3 else 640
src = os.path.join(RAW, name + (".mkv" if os.path.exists(os.path.join(RAW, name + ".mkv")) else ".mp4"))
os.makedirs(CHECK, exist_ok=True)
files = []
for t in times:
    out = os.path.join(CHECK, "%s_%.1f.jpg" % (name, t))
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", str(t), "-i", src, "-frames:v", "1", "-vf", "scale=%d:-1" % width, "-q:v", "3", out], check=True)
    files.append(out)
cols = 2 if len(files) > 1 else 1
args = [FFMPEG, "-v", "error", "-y"]
for f in files:
    args += ["-i", f]
rows = (len(files) + cols - 1) // cols
layout = "|".join("%d_%d" % ((i % cols) * width, (i // cols) * int(width * 9 / 16)) for i in range(len(files)))
if len(files) > 1:
    args += ["-filter_complex", "xstack=inputs=%d:layout=%s" % (len(files), layout)]
sheet = os.path.join(CHECK, name + "_sheet.jpg")
args += ["-frames:v", "1", "-q:v", "3", sheet]
subprocess.run(args, check=True)
print(sheet)
