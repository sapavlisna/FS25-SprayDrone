"""Střihový systém SprayDrone: z master.json vyrobí tři verze videa (T trailer ~1 min, P přehled ~3 min, N návod ~10 min).

SPUŠTĚNÍ (z kořene projektu, PowerShell)
  python tools\\cinema\\edit\\render.py --version T            # jedna verze, plná kvalita -> out\\trailer\\final\\SDT_T_v<N>.mp4 (+ _nahled.jpg)
  python tools\\cinema\\edit\\render.py --all                  # všechny tři
  python tools\\cinema\\edit\\render.py --version N --preview  # 960x540 ultrafast -> out\\trailer\\final\\preview\\SDT_N_preview.mp4
  python tools\\cinema\\edit\\render.py --version P --list     # jen výpis plánu (které záběry jsou, které chybí, délky), nic se nerenderuje
  python tools\\cinema\\edit\\render.py --version T --dry      # jen zapíše graf do work a vypíše příkaz
  Další volby: --no-game-audio (bez zvuku hry z klipů), --no-vignette, --no-verify (přeskočí kontrolu po renderu), --out-ver 5 (číslo verze souboru),
  --threads 8 (vlákna x264; render běží s nízkou prioritou, aby nebrzdil hru).

JAK PŘIDAT KLIP
  1. Natočený klip je v out\\trailer\\raw\\<nazev>.mkv (OBS, 1920x1080, CFR 60).
  2. V tools\\cinema\\edit\\master.json najdi záběr podle ID ze scénáře (např. "3.1") a nastav "clip": "<nazev>" (bez přípony).
  3. Nastav výřez "in" a "out" v sekundách (výchozí a pro N) a případně "cuts": {"P": [od, do], "T": [od, do]} (T se na rytmus hudby zaokrouhlí na celé doby).
  4. "versions" určuje, do kterých verzí záběr patří; "audio": true = přidat lehce zvuk hry (u klipů, kde je zvuk hry ticho, se přeskočí samo).
  5. python tools\\cinema\\edit\\render.py --version P --list  ukáže, že záběr už není "chybí"; pak renderuj.
  Záběry bez klipu se přeskočí s varováním ("CHYBÍ").

JAK ZMĚNIT TITULEK
  Záběr v master.json: "cap": {"P": "...", "N": "..."} je hlavní řádek titulku (P krátký, N delší), "steps": ["...", "..."] jsou řádky postupu pro N.
  Klávesy v textu zapiš do hranatých závorek: "Start letu [Alt+8]" se vykreslí jako klávesové štítky "Alt" + "8". Pole "keys" jen doplní štítky na konec řádku, když v textu nejsou.
  Karty (N): záběr typu "card" má "card": {"title", "lines", "numbered", "draft"}; "draft": true zobrazí v rohu značku NÁVRH TEXTU (smaž po kontrole textu).
  Mezititulky kapitol se berou z "chapters" (title, sub). Titulní karta a závěrečná karta z "brand"; kredit hudby (CC BY 4.0) se do závěrečné karty skládá sám z použitých skladeb.
  Obrázky titulků se cachují podle obsahu v work\\gfx, po změně textu se přegenerují samy.

JAK VYROBIT VERZI / ZMĚNIT NASTAVENÍ VERZE
  master.json -> "versions" -> T/P/N: music (seznam skladeb z out\\trailer\\hudba, "start" = kde ve skladbě začít, skladby se řetězí s prolnutím 3 s), xfade (s, 0 = tvrdé střihy),
  captions (null/"P"/"N"), chapter_cards, cards (karty s postupem), game_audio_db (null = bez zvuku hry), title/end délky. Nová verze = nový klíč + --version <klíč>.
  T: střihy se kladou na doby hudby (tempo se odhadne z hudby, první doba skladby je v čase 0); délka záběrů se zaokrouhlí na celé doby (min_beats).

TECHNICKÉ POZNÁMKY
  * Vstup z OBS je CFR 60 fps. Snímky se NEPŘEVZORKUJÍ: settb=1/60,setpts=N přiřadí každému snímku přesné pts (odstraní jitter 16/17 ms), žádné fps= filtru, žádné zdvojení ani zahození.
    Jen klip, který není CFR 60 (probe), projde fps=60. Délky záběrů jsou celé počty snímků (trim=end_frame), takže posuny xfade jsou přesné na snímek.
  * Duplicitní snímky OBS (GPU-bound záběry) zůstávají, jsou součástí záznamu; střih je nezhoršuje.
  * Zvuk: hudba + (volitelně) zvuk hry z mkv o game_audio_db dB jen u záběrů s "audio": true, všechno se normalizuje na -14 LUFS (loudnorm dva průchody, TP -2.0).
    Zvuk se skládá zvlášť do wav (work), pak se připojí k videu; audio-video jsou ze stejného -ss, odchylka je pod 1 snímek.
  * Barva: eq contrast 1.06, saturation 1.10, vinětace PI/15 (vypnutí --no-vignette). Titulky se kladou až po barevném ladění.
"""

import argparse
import glob
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gfx  # noqa: E402

ROOT = r"E:\ClaudeProjects\FS25-SprayDrone"
FFMPEG = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
FFPROBE = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe"
MASTER = os.path.join(HERE, "master.json")
FPS = 60
W, H = 1920, 1080
MUSIC_XFADE = 3.0
CAP_FADE = 0.35
SILENT_DB = -60.0
BELOW_NORMAL = 0x00004000


def load_master():
    with open(MASTER, encoding="utf-8") as f:
        m = json.load(f)
    m["_p"] = {k: os.path.normpath(os.path.join(ROOT, v)) for k, v in m["paths"].items()}
    os.makedirs(m["_p"]["work"], exist_ok=True)
    return m


def run(cmd, log=None, check=True, capture=False):
    kw = dict(creationflags=BELOW_NORMAL)
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    else:
        r = subprocess.run(cmd, **kw)
    if check and r.returncode != 0:
        tail = (r.stderr or "")[-2500:] if capture else ""
        raise SystemExit("ffmpeg selhal (kód %d)\n%s" % (r.returncode, tail))
    return r


class Cache:
    def __init__(self, path):
        self.path = path
        try:
            with open(path, encoding="utf-8") as f:
                self.d = json.load(f)
        except Exception:
            self.d = {}

    def get(self, k):
        return self.d.get(k)

    def put(self, k, v):
        self.d[k] = v
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.d, f, indent=1)


def file_sig(path):
    st = os.stat(path)
    return "%d-%d" % (st.st_size, int(st.st_mtime))


def probe(M, path):
    cache = Cache(os.path.join(M["_p"]["work"], "probe_cache.json"))
    sig = file_sig(path)
    c = cache.get(path)
    if c and c.get("sig") == sig:
        return c
    r = run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,r_frame_rate,avg_frame_rate,width,height:format=duration", "-of", "json", path], capture=True)
    j = json.loads(r.stdout)
    v = [s for s in j["streams"] if s["codec_type"] == "video"]
    a = [s for s in j["streams"] if s["codec_type"] == "audio"]
    info = {"sig": sig, "dur": float(j["format"]["duration"]), "has_audio": bool(a)}
    if v:
        info.update(w=v[0]["width"], h=v[0]["height"], cfr60=(v[0]["r_frame_rate"] == "60/1" and v[0]["avg_frame_rate"] == "60/1"))
    cache.put(path, info)
    return info


def game_audio_level(M, path):
    cache = Cache(os.path.join(M["_p"]["work"], "audio_level_cache.json"))
    sig = file_sig(path)
    c = cache.get(path)
    if c and c.get("sig") == sig:
        return c["max_db"]
    r = run([FFMPEG, "-hide_banner", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"], capture=True, check=False)
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", r.stderr)
    db = float(m.group(1)) if m else -91.0
    cache.put(path, {"sig": sig, "max_db": db})
    return db


def analyze_beats(M, path, start, span=80.0):
    cache = Cache(os.path.join(M["_p"]["work"], "beats_cache.json"))
    key = "%s|%s|%s" % (path, start, file_sig(path))
    c = cache.get(key)
    if c:
        return c
    sr, win, hop = 22050, 1024, 256
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", str(start), "-t", str(span), "-i", path, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, creationflags=BELOW_NORMAL).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768
    n = (len(x) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    spec = np.abs(np.fft.rfft(x[idx] * np.hanning(win), axis=1))[:, :186]
    flux = np.maximum(0, np.diff(np.log1p(spec * 30), axis=0)).sum(axis=1)
    flux = np.maximum(0, flux - np.convolve(flux, np.ones(43) / 43, mode="same"))
    fps = sr / hop
    sm = np.maximum(flux, np.maximum(np.roll(flux, 1), np.roll(flux, -1)))
    ac = np.correlate(flux - flux.mean(), flux - flux.mean(), "full")[len(flux) - 1:]
    lo, hi = int(fps * 60 / 170), int(fps * 60 / 75)
    coarse = 60 * fps / (lo + int(np.argmax(ac[lo:hi])))
    best = (-1, coarse, 0.0)
    for bpm in np.arange(coarse - 3.0, coarse + 3.0, 0.01):
        bf = fps * 60 / bpm
        k = int((len(flux) - bf) // bf)
        ks = np.arange(k)
        phases = np.arange(0, bf, 0.5)
        pos = np.rint(phases[:, None] + ks[None, :] * bf).astype(int)
        sc = sm[pos].sum(axis=1)
        pi = int(np.argmax(sc))
        if sc[pi] > best[0]:
            best = (sc[pi], bpm, phases[pi])
    score, bpm, ph = best
    period = 60.0 / bpm
    first = ((ph + (hop / 2.0 + win / 4.0) / hop) / fps) % period
    k = int((len(flux) - fps * period) // (fps * period))
    ratio = float(score / (k * (sm.mean() + 1e-9)))
    res = {"bpm": float(bpm), "period": float(period), "first_beat": float(start + first), "strength": ratio}
    cache.put(key, res)
    return res


def title_of(fname):
    return os.path.splitext(fname)[0]


def credit_text(titles):
    return "Music: %s by Kevin MacLeod (incompetech.com) / CC BY 4.0" % ", ".join(titles)


def plan_music(M, vcfg, total_s, beat_start=None):
    """Seznam úseků hudby (soubor, ss, délka) tak, aby po řetězení s prolnutím pokryly total_s + rezervu."""
    segs, covered, used = [], 0.0, []
    tracks = vcfg["music"]
    need = total_s + 1.0
    guard = 0
    while covered < need and guard < 12:
        for t in tracks:
            path = os.path.join(M["_p"]["music"], t["file"])
            dur = probe(M, path)["dur"]
            ss = t.get("start", 0.0)
            if beat_start is not None and not segs:
                ss = beat_start
            avail = dur - ss
            overlap = MUSIC_XFADE if segs else 0.0
            remain = need - covered + overlap
            take = min(avail, remain)
            segs.append({"file": path, "name": title_of(t["file"]), "ss": ss, "take": take, "overlap": overlap})
            covered += take - overlap
            if title_of(t["file"]) not in used:
                used.append(title_of(t["file"]))
            if covered >= need:
                break
        guard += 1
    return segs, used


def next_version_number(M, key):
    best = 0
    for p in glob.glob(os.path.join(M["_p"]["final"], "SDT_%s_v*.mp4" % key)):
        m = re.search(r"_v(\d+)\.mp4$", p)
        if m:
            best = max(best, int(m.group(1)))
    return best + 1


def build_plan(M, key, opts, log):
    vcfg = M["versions"][key]
    chmap = {c["id"]: c for c in M["chapters"]}
    xf_s = vcfg.get("xfade", 0)
    xf_frames = int(round(xf_s * FPS))
    black_frames = int(round(0.5 * FPS)) if xf_frames else 0
    beat = None
    if vcfg.get("beat_sync"):
        m0 = vcfg["music"][0]
        beat = analyze_beats(M, os.path.join(M["_p"]["music"], m0["file"]), m0.get("start", 0.0))
    per = beat["period"] if beat else None

    items, missing = [], []
    last_ch = None
    pos_beats = 0.0

    def beats_to_frames(start_b, n):
        return int(round((start_b + n) * per * FPS)) - int(round(start_b * per * FPS))

    for shot in M["shots"]:
        if key not in shot["versions"]:
            continue
        typ = shot["type"]
        if typ in ("video", "shop", "planner"):
            clip = shot.get("clip")
            path = None
            if clip:
                for ext in (".mkv", ".mp4"):
                    p = os.path.join(M["_p"]["raw"], clip + ext)
                    if os.path.exists(p):
                        path = p
                        break
            if not path:
                missing.append(shot["id"])
                log("CHYBÍ  %s %s (%s)" % (shot["id"], shot["title"], "klip " + clip + " nenalezen" if clip else "bez klipu"))
                continue
            info = probe(M, path)
            cut = shot.get("cuts", {}).get(key) or [shot["in"], shot["out"]]
            a, b = float(cut[0]), float(cut[1])
            if b > info["dur"] - 0.05:
                log("VAROVÁNÍ %s: out %.2f > délka klipu %.2f, zkráceno" % (shot["id"], b, info["dur"]))
                b = info["dur"] - 0.05
            if per:
                avail_beats = int((info["dur"] - 0.05 - a) // per)
                unit = vcfg.get("beat_unit", 1)
                n = max(vcfg.get("min_beats", 4), unit * int(round((b - a) / per / unit)))
                n = min(n, avail_beats // unit * unit)
                frames = beats_to_frames(pos_beats, n)
                pos_beats += n
            else:
                frames = int(round((b - a) * FPS))
            if chapter_card_wanted(vcfg, shot["ch"], last_ch):
                items.append(chapter_item(M, vcfg, chmap[shot["ch"]]))
            last_ch = shot["ch"]
            items.append({"kind": "video", "id": shot["id"], "ch": shot["ch"], "title": shot["title"], "path": path, "info": info, "ss": a, "frames": frames,
                          "shot": shot})
        elif typ == "card":
            if not vcfg.get("cards"):
                continue
            if chapter_card_wanted(vcfg, shot["ch"], last_ch):
                items.append(chapter_item(M, vcfg, chmap[shot["ch"]]))
            last_ch = shot["ch"]
            kind = shot["card"].get("kind", "card")
            items.append({"kind": "card", "id": shot["id"], "ch": shot["ch"], "title": shot["title"], "card_kind": kind, "card": shot["card"],
                          "frames": int(round(shot["dur"] * FPS)), "shot": shot})
        elif typ == "title":
            kind = shot["card"].get("kind", "title") if shot.get("card") else "title"
            if per:
                n = vcfg["end_beats"] if kind == "end" else vcfg["title_beats"]
                frames = beats_to_frames(pos_beats, n)
                pos_beats += n
            else:
                frames = int(round(vcfg["end_s" if kind == "end" else "title_s"] * FPS))
            items.append({"kind": "card", "id": shot["id"], "ch": shot["ch"], "title": shot["title"], "card_kind": kind, "card": shot.get("card", {}), "frames": frames,
                          "shot": shot, "fade": "out" if kind == "end" else "in"})

    for i, it in enumerate(items):
        it["trans"] = ("cut", 0)
    if xf_frames:
        for i in range(1, len(items)):
            prev, cur = items[i - 1], items[i]
            if prev["kind"] == "video" and cur["kind"] == "video":
                items[i]["trans"] = ("fade", xf_frames)
            else:
                items[i]["trans"] = ("fadeblack", black_frames)

    start = 0
    for i, it in enumerate(items):
        if i:
            start += items[i - 1]["frames"] - it["trans"][1]
        it["start"] = start
    total_frames = items[-1]["start"] + items[-1]["frames"] if items else 0
    for i, it in enumerate(items):
        tin = it["trans"][1]
        tout = items[i + 1]["trans"][1] if i + 1 < len(items) else 0
        if it["frames"] <= tin + tout + 2:
            raise SystemExit("záběr %s je kratší než jeho prolínání" % it["id"])
        it["tin"], it["tout"] = tin, tout
    return {"key": key, "vcfg": vcfg, "items": items, "total_frames": total_frames, "total_s": total_frames / FPS, "missing": missing, "beat": beat}


def chapter_card_wanted(vcfg, ch, last_ch):
    return bool(vcfg.get("chapter_cards")) and ch != last_ch and ch not in ("K0", "K8")


def chapter_item(M, vcfg, chapter):
    return {"kind": "card", "id": chapter["id"], "ch": chapter["id"], "title": "Kapitola " + chapter["id"][1:] + ": " + chapter["title"], "card_kind": "chapter", "card": chapter,
            "frames": int(round(vcfg["chapter_card_s"] * FPS)), "shot": None}


def caption_for(M, plan, it, opts):
    vcfg = plan["vcfg"]
    mode = vcfg.get("captions")
    if not mode or opts.no_captions or it["kind"] != "video":
        return None
    shot = it["shot"]
    text = shot.get("cap", {}).get(mode) or (shot.get("cap", {}).get("P") if mode == "N" else None)
    if not text:
        return None
    keys = shot.get("keys", [])
    if keys and "[" not in text and mode == "P":
        text = text + "  " + " ".join("[%s]" % k for k in keys)
    lines = [text]
    if mode == "N":
        lines += shot.get("steps", [])
    seg_s = it["frames"] / FPS
    start = 0.6 + it["tin"] / FPS
    tail = it["tout"] / FPS + 0.35
    dur = seg_s - start - tail
    if mode == "P":
        dur = min(dur, 4.2)
    if dur < 1.2:
        return None
    return {"lines": lines, "start": start, "dur": dur}


def build_video_graph(M, plan, opts, preview):
    items = plan["items"]
    scale_out = ("scale=960:540:flags=bilinear," if preview else "")
    inputs, chains = [], []
    nin = 0
    labels = []
    credit = credit_text(plan["music_titles"])
    for it in items:
        lab = "i%d" % len(labels)
        F = it["frames"]
        if it["kind"] == "video":
            inputs += ["-ss", "%.3f" % it["ss"], "-t", "%.3f" % (F / FPS + 0.3), "-i", it["path"]]
            idx = nin
            nin += 1
            pre = "settb=1/60,setpts=N" if it["info"].get("cfr60") else "fps=60:round=near,settb=1/60,setpts=N"
            sc = "" if (it["info"]["w"], it["info"]["h"]) == (W, H) else "scale=%d:%d:flags=lanczos," % (W, H)
            vig = "" if opts.no_vignette else "vignette=angle=PI/15,"
            chain = "[%d:v]%s,trim=end_frame=%d,%seq=contrast=1.06:saturation=1.10,%sformat=yuv420p,setsar=1" % (idx, pre, F, sc, vig)
            scale_f = ",scale=960:540:flags=bilinear,setsar=1" if preview else ""
            cap = caption_for(M, plan, it, opts)
            it["_cap"] = cap
            if cap:
                p, x, y, cw, ch = gfx.caption_png(M["_p"]["work"], cap["lines"])
                inputs += ["-loop", "1", "-framerate", str(FPS), "-t", "%.3f" % (cap["dur"] + 0.1), "-i", p]
                cidx = nin
                nin += 1
                chains.append("[%d:v]format=rgba,fade=t=in:st=0:d=%.2f:alpha=1,fade=t=out:st=%.3f:d=%.2f:alpha=1,setpts=PTS+%.3f/TB[c%s]" % (
                    cidx, CAP_FADE, cap["dur"] - CAP_FADE, CAP_FADE, cap["start"], lab))
                chains.append("%s[%sa]" % (chain, lab))
                chains.append("[%sa][c%s]overlay=x=%d:y=%d:eof_action=pass:format=auto,format=yuv420p,setsar=1%s[%s]" % (lab, lab, x, y, scale_f, lab))
            else:
                chains.append("%s%s[%s]" % (chain, scale_f, lab))
        else:
            data = it["card"]
            p = gfx.card_png(M["_p"]["work"], it["card_kind"], data, M["brand"], chapters=M["chapters"], credit=credit)
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", "%.3f" % (F / FPS + 0.2), "-i", p]
            idx = nin
            nin += 1
            fade = ""
            if it.get("fade") == "in":
                fade = "fade=t=in:st=0:d=0.6,"
            elif it.get("fade") == "out":
                fade = "fade=t=out:st=%.3f:d=1.2," % (F / FPS - 1.2)
            chains.append("[%d:v]settb=1/60,setpts=N,trim=end_frame=%d,format=yuv420p,%s%ssetsar=1[%s]" % (idx, F, fade, scale_out, lab))
        labels.append(lab)

    if all(it["trans"][0] == "cut" for it in items[1:]):
        chains.append("%sconcat=n=%d:v=1:a=0,settb=1/60[vout]" % ("".join("[%s]" % l for l in labels), len(labels)))
    else:
        cur, cur_frames = labels[0], items[0]["frames"]
        for k in range(1, len(items)):
            it = items[k]
            kind, tf = it["trans"]
            out = "x%d" % k
            if kind == "cut":
                chains.append("[%s][%s]concat=n=2:v=1:a=0,settb=1/60[%s]" % (cur, labels[k], out))
                cur_frames += it["frames"]
            else:
                chains.append("[%s][%s]xfade=transition=%s:duration=%.5f:offset=%.5f,settb=1/60[%s]" % (cur, labels[k], kind, tf / FPS, (cur_frames - tf) / FPS, out))
                cur_frames += it["frames"] - tf
            cur = out
        chains.append("[%s]null[vout]" % cur)
    return inputs, ";\n".join(chains), nin


def build_audio_graph(M, plan, opts, log):
    vcfg = plan["vcfg"]
    total = plan["total_s"]
    inputs, chains = [], []
    segs = plan["music_segs"]
    for i, s in enumerate(segs):
        inputs += ["-ss", "%.3f" % s["ss"], "-t", "%.3f" % s["take"], "-i", s["file"]]
        chains.append("[%d:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[m%d]" % (i, i))
    cur = "m0"
    for i in range(1, len(segs)):
        chains.append("[%s][m%d]acrossfade=d=%.2f:c1=tri:c2=tri[mx%d]" % (cur, i, MUSIC_XFADE, i))
        cur = "mx%d" % i
    fade_out = 3.0 if plan["key"] != "T" else 2.5
    chains.append("[%s]atrim=0:%.3f,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.2,afade=t=out:st=%.3f:d=%.2f[mus]" % (cur, total, total - fade_out, fade_out))
    n = len(segs)
    gdb = vcfg.get("game_audio_db")
    gl = []
    if gdb is not None and not opts.no_game_audio:
        for it in plan["items"]:
            if it["kind"] != "video" or not it["shot"].get("audio"):
                continue
            lvl = game_audio_level(M, it["path"])
            if lvl < SILENT_DB or not it["info"].get("has_audio"):
                log("zvuk hry: %s (%s) je ticho (max %.0f dB), přeskočeno" % (it["id"], os.path.basename(it["path"]), lvl))
                continue
            d = it["frames"] / FPS
            inputs += ["-ss", "%.3f" % it["ss"], "-t", "%.3f" % (d + 0.2), "-i", it["path"]]
            ms = int(round(it["start"] / FPS * 1000))
            chains.append("[%d:a]atrim=0:%.3f,asetpts=PTS-STARTPTS,aresample=48000:async=1,aformat=sample_fmts=fltp:channel_layouts=stereo,volume=%.1fdB,"
                          "afade=t=in:st=0:d=0.3,afade=t=out:st=%.3f:d=0.3,adelay=%d|%d[g%d]" % (n, d, gdb, d - 0.3, ms, ms, n))
            gl.append("[g%d]" % n)
            n += 1
    if gl:
        chains.append("[mus]%samix=inputs=%d:duration=first:normalize=0,alimiter=limit=0.95[mix]" % ("".join(gl), 1 + len(gl)))
    else:
        chains.append("[mus]anull[mix]")
    plan["game_audio_clips"] = len(gl)
    return inputs, chains


def loudnorm_two_pass(M, plan, inputs, chains, wav, log):
    base = ";\n".join(chains)
    script = os.path.join(M["_p"]["work"], "audio_%s.txt" % plan["key"])
    with open(script, "w", encoding="utf-8") as f:
        f.write(base + ";\n[mix]loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json[a]")
    r = run([FFMPEG, "-hide_banner", "-y", "-nostats"] + inputs + ["-/filter_complex", script, "-map", "[a]", "-f", "null", "-"], capture=True)
    j = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    log("loudnorm pass 1: I=%s LUFS TP=%s LRA=%s" % (j["input_i"], j["input_tp"], j["input_lra"]))
    with open(script, "w", encoding="utf-8") as f:
        f.write(base + ";\n[mix]loudnorm=I=-14:TP=-2.0:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true,alimiter=limit=0.76:level=disabled[a]" % (
            j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"]))
    run([FFMPEG, "-hide_banner", "-y", "-nostats", "-loglevel", "error"] + inputs + ["-/filter_complex", script, "-map", "[a]", "-ar", "48000", "-ac", "2",
         "-c:a", "pcm_s16le", wav], capture=True)


def print_plan(plan, log):
    log("=== %s: %d položek, %.1f s (%d snímků) ===" % (plan["key"], len(plan["items"]), plan["total_s"], plan["total_frames"]))
    for it in plan["items"]:
        cap = it.get("_cap")
        log("  %6.1f  %5.1f s  %-9s %-5s %-34s %s" % (it["start"] / FPS, it["frames"] / FPS, it["kind"] if it["kind"] == "video" else it.get("card_kind"), it["id"], it["title"][:34],
                                                    os.path.basename(it["path"]) if it["kind"] == "video" else ""))
    if plan["missing"]:
        log("Chybějící záběry (%d): %s" % (len(plan["missing"]), ", ".join(plan["missing"])))
    if plan.get("beat"):
        b = plan["beat"]
        log("tempo hudby %.2f BPM (doba %.4f s), první doba %.3f s, síla %.1f" % (b["bpm"], b["period"], b["first_beat"], b["strength"]))
    log("hudba: %s" % ", ".join(plan.get("music_titles", [])))


def verify(M, path, plan, key, tag, log):
    work = M["_p"]["work"]
    r = run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "csv=p=0", path], capture=True)
    pts = np.array([float(x.strip(",")) for x in r.stdout.split() if x.strip(",")])
    d = np.diff(pts)
    log("verify: %d snímků (plán %d), rozestup pts min %.4f max %.4f s, odchylek od 1/60 > 1 ms: %d" % (len(pts), plan["total_frames"], d.min(), d.max(), int((np.abs(d - 1 / 60) > 0.001).sum())))
    r = run([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "csv=p=0", path], capture=True)
    log("verify: délky streamů %s, plán %.2f s" % (" ".join(r.stdout.split()), plan["total_s"]))
    r = run([FFMPEG, "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"], capture=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    LRA = re.search(r"LRA:\s+([\d.]+) LU", tail)
    PK = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    log("verify: hlasitost I=%s LUFS, LRA=%s LU, true peak=%s dBFS" % (I.group(1) if I else "?", LRA.group(1) if LRA else "?", PK.group(1) if PK else "?"))
    vd = os.path.join(work, "verify_%s_%s" % (key, tag))
    os.makedirs(vd, exist_ok=True)
    for old in glob.glob(os.path.join(vd, "*.jpg")):
        os.remove(old)
    run([FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-i", path, "-vf", "fps=1/2,scale=384:-1,tile=5x6", "-q:v", "4", os.path.join(vd, "s_%02d.jpg")], capture=True)
    log("verify: snímky po 2 s v %s" % vd)


def render_version(M, key, opts):
    logf = open(os.path.join(M["_p"]["work"], "render_%s.log" % key), "w", encoding="utf-8")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n")

    t0 = time.time()
    plan = build_plan(M, key, opts, log)
    if not plan["items"]:
        raise SystemExit("prázdný plán")
    vcfg = plan["vcfg"]
    beat = plan["beat"]
    segs, used = plan_music(M, vcfg, plan["total_s"], beat["first_beat"] if beat else None)
    plan["music_segs"], plan["music_titles"] = segs, used
    a_inputs, a_chains = build_audio_graph(M, plan, opts, log)
    v_inputs, v_graph, nvin = build_video_graph(M, plan, opts, opts.preview)
    print_plan(plan, log)
    work = M["_p"]["work"]
    tag = "preview" if opts.preview else "full"
    vscript = os.path.join(work, "video_%s_%s.txt" % (key, tag))
    with open(vscript, "w", encoding="utf-8") as f:
        f.write(v_graph)
    if opts.list:
        return
    if opts.preview:
        outdir = os.path.join(M["_p"]["final"], "preview")
        out = os.path.join(outdir, "SDT_%s_preview.mp4" % key)
    else:
        outdir = M["_p"]["final"]
        n = opts.out_ver or next_version_number(M, key)
        out = os.path.join(outdir, "SDT_%s_v%d.mp4" % (key, n))
    os.makedirs(outdir, exist_ok=True)
    wav = os.path.join(work, "audio_%s_%s.wav" % (key, tag))
    enc = ["-c:v", "libx264", "-preset", "ultrafast" if opts.preview else opts.preset, "-crf", "28" if opts.preview else "20", "-pix_fmt", "yuv420p",
           "-threads", str(opts.threads), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", "%.4f" % plan["total_s"]]
    cmd = [FFMPEG, "-hide_banner", "-y", "-loglevel", "warning", "-nostats"] + v_inputs + ["-i", wav, "-/filter_complex", vscript, "-map", "[vout]", "-map", "%d:a" % nvin,
          "-fps_mode", "passthrough"] + enc + [out]
    if opts.dry:
        log(" ".join('"%s"' % c if " " in c else c for c in cmd))
        return
    log("zvuk ...")
    loudnorm_two_pass(M, plan, a_inputs, a_chains, wav, log)
    log("video ... -> %s" % out)
    run(cmd)
    sheet = out[:-4] + "_nahled.jpg"
    iv = max(1.0, plan["total_s"] / 24)
    run([FFMPEG, "-hide_banner", "-y", "-loglevel", "error", "-i", out, "-vf", "fps=1/%.3f,scale=384:-1,tile=6x4" % iv, "-frames:v", "1", "-update", "1", "-q:v", "3", sheet], capture=True)
    log("hotovo: %s (%d kB), %.0f s, render %.0f s" % (out, os.path.getsize(out) // 1024, plan["total_s"], time.time() - t0))
    if not opts.no_verify:
        verify(M, out, plan, key, tag, log)
    logf.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--version", help="T, P nebo N (nebo vlastní klíč z master.json)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--preview", action="store_true", help="960x540 ultrafast")
    ap.add_argument("--list", action="store_true", help="jen vypíše plán")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-game-audio", action="store_true")
    ap.add_argument("--no-vignette", action="store_true")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--out-ver", type=int)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--preset", default="medium", help="x264 preset pro plný render (medium, veryfast, ...)")
    opts = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    M = load_master()
    keys = list(M["versions"]) if opts.all else [opts.version]
    if not keys or keys == [None]:
        ap.error("zadej --version nebo --all")
    for k in keys:
        render_version(M, k, opts)


if __name__ == "__main__":
    main()
