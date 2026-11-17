"""Natáčení v2: akce × kamera přes OBS, roztřídění klipu, kontaktní list a záznam do clips.json.

python tools/cinema/v2/shoot.py <akce>[:<kam>[,<kam>]] [...] [--take N] [--dry]
  bez :kam natočí všechny kamery akce; take se čísluje sám (další volné číslo u dané akce a kamery)

Klip:   out/trailer/v2/raw/<vlek>/<beat>/<akce>_<kam>_t<N>.mkv (+ .runlog.json)
List:   out/trailer/v2/check/<akce>_<kam>_t<N>_list.jpg (snímek po 1 s, 4 sloupce, čas v rohu)
Záznam: tools/cinema/v2/clips.json, stav "natoceno" (kontrola ho přepíše na ok/slabsi/vyrazeno)
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
from mk_take import SCENES_V2, build  # noqa: E402

FFMPEG = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")
OBS_RAW = os.path.join(ROOT, "out", "trailer", "raw")
V2_RAW = os.path.join(ROOT, "out", "trailer", "v2", "raw")
CHECK = os.path.join(ROOT, "out", "trailer", "v2", "check")
CLIPS = os.path.join(HERE, "clips.json")


def load_clips():
    if os.path.exists(CLIPS):
        with open(CLIPS, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_clips(clips):
    tmp = CLIPS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clips, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CLIPS)


def cams_of(akce):
    out = []
    for p in sorted(glob.glob(os.path.join(SCENES_V2, akce + ".kam*.json"))):
        out.append(os.path.basename(p)[len(akce) + 4:-len(".json")])
    return out


def next_take(akce, kam):
    n = 0
    for p in glob.glob(os.path.join(V2_RAW, "**", "%s_%s_t*.mkv" % (akce, kam)), recursive=True):
        m = re.search(r"_t(\d+)\.mkv$", p)
        if m:
            n = max(n, int(m.group(1)))
    return n + 1


def duration(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 2)
    except ValueError:
        return None


def contact_sheet(path, out):
    vf = ("fps=1,scale=480:-1,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='%{pts\\:hms}':x=6:y=6:fontsize=20:"
          "fontcolor=yellow:box=1:boxcolor=black@0.5,tile=4x6")
    r = subprocess.run([FFMPEG, "-y", "-v", "error", "-i", path, "-vf", vf, "-frames:v", "1", "-q:v", "4", out], capture_output=True, text=True)
    if not os.path.exists(out):
        print("   list selhal:", r.stderr[-400:], flush=True)
    return os.path.exists(out)


def clipcheck(path):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "cinema", "clipcheck.py"), path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()[-600:]


def shoot(akce_id, kam, take, dry):
    akce = json.load(open(os.path.join(SCENES_V2, akce_id + ".akce.json"), encoding="utf-8"))
    scene = build(akce_id, kam)
    name = scene["name"]
    print("== %s take %d" % (name, take), flush=True)
    if dry:
        return True
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "cinema", "run_scene.py"), name, "--obs", "--take", str(take)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1500)
    tail = (r.stdout or "")[-1500:] + (r.stderr or "")[-800:]
    src = os.path.join(OBS_RAW, "%s_t%d.mkv" % (name, take))
    dst_dir = os.path.join(V2_RAW, akce["vlek"], str(akce["beat"]))
    os.makedirs(dst_dir, exist_ok=True)
    os.makedirs(CHECK, exist_ok=True)
    base = "%s_%s_t%d" % (akce_id, kam, take)
    entry = {"soubor": None, "akce": akce_id, "kamera": kam, "take": take, "vlek": akce["vlek"], "beat": akce["beat"],
             "zabery": akce.get("zabery", []), "t_event": akce.get("t_event"), "stav": "chyba", "nalezy": [],
             "natoceno": time.strftime("%Y-%m-%d %H:%M"), "trvani_s": round(time.time() - t0)}
    if r.returncode == 0 and os.path.exists(src):
        dst = os.path.join(dst_dir, base + ".mkv")
        shutil.move(src, dst)
        rl = os.path.join(OBS_RAW, "%s_t%d.runlog.json" % (name, take))
        if os.path.exists(rl):
            shutil.move(rl, os.path.join(dst_dir, base + ".runlog.json"))
        sheet = os.path.join(CHECK, base + "_list.jpg")
        contact_sheet(dst, sheet)
        entry.update({"soubor": os.path.relpath(dst, ROOT).replace("\\", "/"), "delka_s": duration(dst), "stav": "natoceno",
                      "list": os.path.relpath(sheet, ROOT).replace("\\", "/"), "clipcheck": clipcheck(dst)})
        print("   OK %s (%s s) list %s" % (entry["soubor"], entry["delka_s"], entry["list"]), flush=True)
    else:
        entry["nalezy"].append("scéna selhala: " + tail.strip().replace("\n", " | ")[-700:])
        print("   CHYBA\n" + tail, flush=True)
    clips = load_clips()
    clips.append(entry)
    save_clips(clips)
    return entry["stav"] == "natoceno"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+")
    ap.add_argument("--take", type=int, default=0)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    bad = 0
    for item in args.items:
        akce, _, kams = item.partition(":")
        for kam in (kams.split(",") if kams else cams_of(akce)):
            take = args.take or next_take(akce, kam)
            if not shoot(akce, kam, take, args.dry):
                bad += 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
