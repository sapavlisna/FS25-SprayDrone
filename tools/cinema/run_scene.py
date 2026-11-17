"""Spustí scénu (JSON) proti běžící hře s módem FS25_SprayDroneCinema.

python tools/cinema/run_scene.py tools/cinema/scenes/s01_aerial.json [--record] [--preview 1.0] [--keep-camera] [--dry]
  --record        kroky {"record": "start"} opravdu spustí tools/cinema/record.ps1 (ffmpeg ddagrab; zabírá OBRAZOVKU, hra musí být vidět)
  --preview SEC   během scény fotí okno hry (PrintWindow, funguje offscreen) po SEC sekundách do out/trailer/preview/<scéna>/
  --keep-camera   na konci nevypíná vlastní kameru (jinak camStop)
  --dry           jen vypíše kroky

Kroky ve scéně ("steps"):
  {"cmd": "setTime", "hour": 18.2}                    příkaz módu (ostatní klíče = parametry; "keys": [...] = klíče kamery; "timeout": s)
  {"cmd": "camPath", "duration": 5, "wait": true, ...}  "wait": true čeká na dokončení (pending ack)
  {"sleep": 2.0}   {"snap": "jmeno"}   {"mark": "text"}
  {"record": "start", "seconds": 8}   {"record": "stop"}
  {"preview": "start", "interval": 1.0}   {"preview": "stop"}
  {"include": "_common_setup"}                        vloží kroky ze scenes/_common_setup.json
  "optional": true u kroku = chyba se jen vypíše
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cinema_client import GAME, send  # noqa: E402
from obs_ctl import Obs  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCENES = os.path.join(ROOT, "tools", "cinema", "scenes")
RAW = os.path.join(ROOT, "out", "trailer", "raw")
PREVIEW = os.path.join(ROOT, "out", "trailer", "preview")
GAMELOG = os.path.join(GAME, "log.txt")
CAPTURE = os.path.join(ROOT, "tools", "fs25_capture.ps1")
RECORD = os.path.join(ROOT, "tools", "cinema", "record.ps1")


def load_steps(path, depth=0):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    steps = data["steps"] if isinstance(data, dict) else data
    out = []
    for step in steps:
        if "include" in step:
            inc = os.path.join(SCENES, step["include"] + ".json")
            out.extend(load_steps(inc, depth + 1))
        else:
            out.append(step)
    return out


class Preview:
    def __init__(self, scene, interval):
        self.dir = os.path.join(PREVIEW, scene)
        os.makedirs(self.dir, exist_ok=True)
        self.scene, self.interval, self.n = scene, interval, 0
        self.stop_flag = threading.Event()
        self.thread = None
        self.files = []

    def capture(self, name):
        subprocess.run(["powershell", "-NoProfile", "-File", CAPTURE, name, "-Scale", "0.5"], capture_output=True, text=True)
        src = os.path.join(ROOT, "out", "mod_build", name + ".png")
        dst = os.path.join(self.dir, name + ".png")
        if os.path.exists(src):
            os.replace(src, dst)
            self.files.append(dst)
        return dst

    def loop(self):
        while not self.stop_flag.is_set():
            start = time.time()
            self.n += 1
            self.capture("%s_%03d" % (self.scene, self.n))
            self.stop_flag.wait(max(self.interval - (time.time() - start), 0.0))

    def start(self):
        if self.thread is None:
            self.stop_flag.clear()
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()

    def stop(self):
        if self.thread is not None:
            self.stop_flag.set()
            self.thread.join()
            self.thread = None


def log_size():
    try:
        return os.path.getsize(GAMELOG)
    except OSError:
        return 0


def log_since(pos):
    try:
        with open(GAMELOG, "rb") as f:
            f.seek(pos)
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    return [line for line in text.splitlines() if "CINEMA" in line or "Error" in line or "attempt to" in line]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--obs", action="store_true", help="záznam přes OBS (CFR 60 fps + zvuk hry) místo ffmpeg ddagrab; výstup out/trailer/raw/<scéna>.mkv")
    ap.add_argument("--preview", type=float, default=0.0)
    ap.add_argument("--keep-camera", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--take", type=int, default=0, help="číslo záběru: záznam i runlog se jmenují <scéna>_t<N>")
    ap.add_argument("--skip-until", help="přeskočí kroky do prvního kroku se značkou {\"mark\": ...} tohoto jména")
    args = ap.parse_args()
    path = args.scene if os.path.exists(args.scene) else os.path.join(SCENES, args.scene + ".json")
    name = os.path.splitext(os.path.basename(path))[0]
    if args.take:
        name = "%s_t%d" % (name, args.take)
    steps = load_steps(path)
    if args.dry:
        for i, s in enumerate(steps):
            print(i, json.dumps(s, ensure_ascii=False)[:160])
        return
    os.makedirs(RAW, exist_ok=True)
    ok, msg = send("ping", timeout=10)
    if not ok:
        sys.exit("mód neodpovídá: " + msg)
    print("mód:", msg)
    preview = Preview(name, args.preview) if args.preview > 0 else None
    runlog = {"scene": name, "started": datetime.now().isoformat(), "steps": []}
    log_pos = log_size()
    record_proc = None
    obs = None
    skipping = bool(args.skip_until)
    for i, step in enumerate(steps):
        if skipping:
            if step.get("mark") == args.skip_until:
                skipping = False
            continue
        entry = {"i": i, "t": datetime.now().isoformat(timespec="milliseconds"), "step": step.get("cmd") or next(iter(step))}
        if "cmd" in step:
            params = {k: v for k, v in step.items() if k not in ("cmd", "keys", "timeout", "optional", "code")}
            timeout = float(step.get("timeout", 20))
            ok, msg = send(step["cmd"], keys=step.get("keys"), code=step.get("code"), timeout=timeout, **params)
            entry.update(ok=ok, msg=msg)
            print("%2d %-14s %s %s" % (i, step["cmd"], "OK " if ok else "ERR", msg[:150]))
            if not ok and not step.get("optional"):
                runlog["steps"].append(entry)
                print("scéna přerušena")
                if obs is not None:
                    try:
                        obs.stop()
                    except Exception as exc:
                        print("OBS stop selhal:", exc)
                break
            if step["cmd"].startswith("cam") and step["cmd"] != "camStop" and preview is not None:
                preview.start()
        elif "sleep" in step:
            time.sleep(float(step["sleep"]))
        elif "snap" in step:
            p = (preview or Preview(name, 1.0)).capture("%s_%s" % (name, step["snap"]))
            print("%2d snímek %s" % (i, p))
        elif "mark" in step:
            print("%2d --- %s" % (i, step["mark"]))
        elif "preview" in step:
            if preview is None:
                preview = Preview(name, float(step.get("interval", 1.0)))
            preview.start() if step["preview"] == "start" else preview.stop()
        elif "record" in step:
            if step["record"] == "start":
                if args.obs:
                    obs = Obs()
                    obs.start(name)
                    time.sleep(float(step.get("lead", 1.0)))
                    print("%2d záznam OBS spuštěn" % i)
                elif args.record:
                    record_proc = subprocess.Popen(["powershell", "-NoProfile", "-File", RECORD, "-Name", name, "-Seconds", str(step.get("seconds", 8))])
                    time.sleep(float(step.get("lead", 1.5)))
                    print("%2d záznam spuštěn" % i)
                else:
                    print("%2d záznam přeskočen (bez --record)" % i)
            elif obs is not None:
                time.sleep(0.5)
                src = obs.stop()
                obs = None
                time.sleep(1.0)
                if src and os.path.exists(src):
                    dst = os.path.join(RAW, name + ".mkv")
                    shutil.move(src, dst)
                    print("%2d záznam OBS uložen %s" % (i, dst))
            elif record_proc is not None:
                record_proc.wait()
                record_proc = None
        runlog["steps"].append(entry)
    if preview is not None:
        preview.stop()
    if not args.keep_camera:
        send("camStop", timeout=10)
    runlog["log"] = log_since(log_pos)
    runlog["previews"] = preview.files if preview else []
    with open(os.path.join(RAW, name + ".runlog.json"), "w", encoding="utf-8") as f:
        json.dump(runlog, f, ensure_ascii=False, indent=1)
    for line in runlog["log"][-12:]:
        print(re.sub(r"\s+", " ", line)[:200])
    print("snímků náhledu:", len(runlog["previews"]))


if __name__ == "__main__":
    main()
