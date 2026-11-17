"""Hrubý střih ukázky traileru: python tools/cinema/cut_v1.py [--dry]

Záběry z out/trailer/raw/<soubor>.mp4 (CLIPS: soubor, začátek v klipu v s, délka v s), křížové prolínání, barevné doladění
(kontrast, sytost, vignetace), 2560x1440 lanczos, titulek a závěrečný titulek (Segoe UI), hudba Inspired.mp3 (fade, ~-14 LUFS),
výstup out/trailer/ukazka_v1.mp4 a kontaktní arch out/trailer/ukazka_v1_nahled.jpg.
"""

import json
import os
import subprocess
import sys

ROOT = r"E:\ClaudeProjects\FS25-SprayDrone"
FFMPEG = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
RAW = os.path.join(ROOT, "out", "trailer", "raw")
OUT = os.path.join(ROOT, "out", "trailer", os.environ.get("CUT_NAME", "ukazka_v1") + ".mp4")
SHEET = os.path.join(ROOT, "out", "trailer", os.environ.get("CUT_NAME", "ukazka_v1") + "_nahled.jpg")
WORK = os.path.join(ROOT, "tmp", "trailer", "cut")
MUSIC = os.path.join(ROOT, "out", "trailer", "hudba", "Inspired.mp3")
MUSIC_START = 80.0
FONT = "C\\:/Windows/Fonts/segoeui.ttf"
FONT_BOLD = "C\\:/Windows/Fonts/segoeuib.ttf"
W, H, FPS = 1920, 1080, 60
XFADE = 0.3
TITLE_LEN = 2.0
END_LEN = 2.0
# ořez horního levého rohu proti Steam FPS překryvu (px zdroje 1920x1080): x, y odstřižené z levého a horního okraje
CROP = (0, 0)

CONFIG = os.path.join(ROOT, "tools", "cinema", os.environ.get("CUT_CFG", "cut_v1.json"))


def load_clips():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)["clips"]


def write_text(name, text):
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(WORK, name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path.replace("\\", "/").replace(":", "\\:")


def build(clips):
    inputs, chains, labels = [], [], []
    # 0: titulek
    t1 = write_text("title1.txt", "SPRAYDRONE")
    t2 = write_text("title2.txt", "Postřikové drony pro Farming Simulator 25")
    inputs += ["-f", "lavfi", "-t", str(TITLE_LEN), "-i", "color=c=black:s=%dx%d:r=%d" % (W, H, FPS)]
    chains.append(
        "[0:v]drawtext=fontfile='%s':textfile='%s':fontcolor=white:fontsize=170:x=(w-text_w)/2:y=(h-text_h)/2-60:alpha='min(1,t/0.6)',"
        "drawtext=fontfile='%s':textfile='%s':fontcolor=0xDDDDDD:fontsize=60:x=(w-text_w)/2:y=(h/2)+90:alpha='min(1,max(0,(t-0.4)/0.6))',"
        "format=yuv420p,setsar=1[v0]" % (FONT_BOLD, t1, FONT, t2))
    labels.append(("v0", TITLE_LEN))
    for i, (name, start, dur) in enumerate(clips, start=1):
        src = os.path.join(RAW, name + (".mkv" if os.path.exists(os.path.join(RAW, name + ".mkv")) else ".mp4"))
        inputs += ["-ss", "%.3f" % start, "-t", "%.3f" % dur, "-i", src]
        crop = "crop=iw-%d:ih-%d:%d:%d," % (CROP[0], CROP[1], CROP[0], CROP[1]) if CROP != (0, 0) else ""
        chains.append("[%d:v]%sscale=%d:%d:flags=lanczos,fps=%d,eq=contrast=1.06:saturation=1.12:gamma=0.98,vignette=angle=PI/15,"
                      "format=yuv420p,setsar=1,setpts=PTS-STARTPTS[v%d]" % (i, crop, W, H, FPS, i))
        labels.append(("v%d" % i, dur))
    n = len(clips) + 1
    t3 = write_text("end1.txt", "Music: Inspired by Kevin MacLeod (incompetech.com) / CC BY 4.0")
    inputs += ["-f", "lavfi", "-t", str(END_LEN), "-i", "color=c=black:s=%dx%d:r=%d" % (W, H, FPS)]
    chains.append("[%d:v]drawtext=fontfile='%s':textfile='%s':fontcolor=0xCCCCCC:fontsize=52:x=(w-text_w)/2:y=(h-text_h)/2,format=yuv420p,setsar=1[v%d]"
                  % (n, FONT, t3, n))
    labels.append(("v%d" % n, END_LEN))
    # řetěz xfade
    cur, cur_len = labels[0]
    for k, (lab, ln) in enumerate(labels[1:], start=1):
        offset = cur_len - XFADE
        out = "x%d" % k
        chains.append("[%s][%s]xfade=transition=fade:duration=%.2f:offset=%.3f[%s]" % (cur, lab, XFADE, offset, out))
        cur, cur_len = out, cur_len + ln - XFADE
    total = cur_len
    inputs += ["-ss", "%.2f" % MUSIC_START, "-t", "%.2f" % (total + 0.5), "-i", MUSIC]
    ai = n + 1
    chains.append("[%d:a]loudnorm=I=-14:TP=-1.5:LRA=7,afade=t=in:st=0:d=1,afade=t=out:st=%.2f:d=2,atrim=0:%.2f[a]" % (ai, total - 2.0, total))
    return inputs, ";".join(chains), cur, total


def main():
    clips = load_clips()
    inputs, graph, last, total = build(clips)
    print("délka %.1f s, %d záběrů" % (total, len(clips)))
    if "--dry" in sys.argv:
        print(graph)
        return
    os.makedirs(WORK, exist_ok=True)
    script = os.path.join(WORK, "graph.txt")
    with open(script, "w", encoding="utf-8") as f:
        f.write(graph)
    cmd = [FFMPEG, "-hide_banner", "-y"] + inputs + ["-filter_complex_script", script, "-map", "[%s]" % last, "-map", "[a]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    subprocess.run([FFMPEG, "-hide_banner", "-y", "-i", OUT, "-vf", "fps=1/2.2,scale=640:-1,tile=5x3", "-frames:v", "1", "-update", "1", "-q:v", "3", SHEET], check=True)
    print(OUT, os.path.getsize(OUT) // 1024, "kB")


main()
