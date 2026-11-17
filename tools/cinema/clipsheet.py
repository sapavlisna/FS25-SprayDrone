"""Kontaktní arch ze záznamu s časy: python tools/cinema/clipsheet.py <soubor bez .mp4> [fps=2] [sloupců=6] [šířka=320]
-> out/trailer/raw/<soubor>_sheet.jpg (každá dlaždice má popisek času v s)"""

import os
import subprocess
import sys

FFMPEG = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
RAW = r"E:\ClaudeProjects\FS25-SprayDrone\out\trailer\raw"
name = sys.argv[1]
fps = float(sys.argv[2]) if len(sys.argv) > 2 else 2
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6
tw = int(sys.argv[4]) if len(sys.argv) > 4 else 320
src = next(p for p in (os.path.join(RAW, name + e) for e in (".mkv", ".mp4")) if os.path.exists(p))
out = os.path.join(RAW, name + "_sheet.jpg")
dur = float(subprocess.run([r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                           capture_output=True, text=True).stdout.strip())
n = int(dur * fps)
rows = (n + cols - 1) // cols
vf = ("fps=%s,scale=%d:-1,drawtext=fontfile='C\\:/Windows/Fonts/segoeui.ttf':text='%%{pts\\:hms}':x=6:y=6:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6,"
      "tile=%dx%d" % (fps, tw, cols, rows))
subprocess.run([FFMPEG, "-v", "error", "-y", "-i", src, "-vf", vf, "-frames:v", "1", "-q:v", "3", out], check=True)
print(out, "%.2f s" % dur)
