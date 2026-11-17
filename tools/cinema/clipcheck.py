"""Kontrola plynulosti záznamu: CFR (rozptyl rozestupů pts), duplicitní snímky (mpdecimate) a skutečné zaškobrtnutí (rozdíl snímek-snímek).

python tools/cinema/clipcheck.py <soubor.mkv> [...]   (název bez přípony = hledá v out/trailer/raw)
Vypíše: délka, snímků, fps, rozestupy pts, unikátních snímků (mpdecimate) a "zaškobrtnutí" = snímky s téměř nulovým rozdílem oproti předchozímu
uprostřed pohybu (okolní medián rozdílu je velký), tedy opakovaný snímek při pohybující se kameře, ne statická scéna.
"""

import json
import os
import re
import subprocess
import sys

import numpy as np

FFMPEG = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
FFPROBE = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe"
RAW = r"E:\ClaudeProjects\FS25-SprayDrone\out\trailer\raw"
W, H = 320, 180


def resolve(name):
    if os.path.exists(name):
        return name
    for ext in (".mkv", ".mp4"):
        p = os.path.join(RAW, name + ext)
        if os.path.exists(p):
            return p
    raise SystemExit("nenalezeno: " + name)


def frame_diffs(path):
    proc = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-vf", "scale=%d:%d,format=gray" % (W, H), "-f", "rawvideo", "-"], capture_output=True)
    data = np.frombuffer(proc.stdout, dtype=np.uint8)
    n = len(data) // (W * H)
    frames = data[: n * W * H].reshape(n, H, W).astype(np.int16)
    return np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))


def check(path):
    probe = json.loads(subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate,avg_frame_rate,width,height:format=duration",
                                       "-show_entries", "packet=pts_time", "-of", "json", path], capture_output=True, text=True).stdout)
    pts = sorted(float(p["pts_time"]) for p in probe["packets"] if "pts_time" in p)
    gaps = [(b - a) * 1000 for a, b in zip(pts, pts[1:])]
    st = probe["streams"][0]
    big = ["%.2fs:%.0fms" % (a, g) for a, g in zip(pts, gaps) if g > 20]
    if big:
        print("  rozestupy pts > 20 ms:", " ".join(big))
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", path, "-vf", "mpdecimate,showinfo", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    kept = [float(m) for m in re.findall(r"pts_time:\s*([\d.]+)", err)]
    uniq = len(kept)
    d = frame_diffs(path)
    stutter = []
    for i in range(len(d)):
        lo, hi = max(0, i - 8), min(len(d), i + 9)
        neigh = np.concatenate([d[lo:i], d[i + 1:hi]])
        med = np.median(neigh)
        if med > 0.6 and d[i] < 0.25 * med:
            stutter.append(i)
    n = len(pts)
    dur = float(probe["format"]["duration"])
    motion = float(np.median(d))
    late = [i for i in stutter if i / 60.0 >= 2.0 and i / 60.0 <= dur - 1.0]
    print("%s: %dx%d r=%s avg=%s, %.2f s, %d snímků, pts rozestup %.2f..%.2f ms, unikátních %d (mpdecimate), zaškobrtnutí %d (po 2 s: %d %s), medián pohybu %.2f" % (
        os.path.basename(path), st["width"], st["height"], st["r_frame_rate"], st["avg_frame_rate"], dur, n, min(gaps), max(gaps), uniq, len(stutter), len(late),
        ("[" + " ".join("%.2fs" % (i / 60.0) for i in late[:10]) + "]") if late else "", motion))


sys.stdout.reconfigure(encoding="utf-8")
if __name__ == "__main__":
  for arg in sys.argv[1:]:
    check(resolve(arg))
