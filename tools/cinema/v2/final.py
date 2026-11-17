"""Finální filmy SprayDrone v2: hrubý střih + úvodní karta + epilog (spol) + koncová karta s kreditem hudby, hudba, loudnorm -14 LUFS.

Spuštění: python tools/cinema/v2/final.py <mini|middle|max|prod|all> [--dry] [--cpu] [--jen-list]
  --dry       jen vypíše plán (délky, hudba, kodér), nic nerenderuje
  --cpu       vynutí libx264 crf 18 (jinak NVENC, když je GPU volné: nvidia-smi < 4 GB a prázdné ollama ps)
  --jen-list  přegeneruje jen poster a kontaktní list z hotového finále
Výstup: out/trailer/v2/final/SDT_<Film>_v2.mp4 (+ .jpg poster, _nahled.jpg kontaktní list). Mezivýstupy v tmp/v2/final.
Zdroje: out/trailer/v2/hruby/<film>.mp4 (+ spol.mp4 pro mini/middle/max), karty z tools/cinema/edit/gfx.py, hudba out/trailer/hudba.
Barva/vinětace: vignette=angle=PI/15 jen na záběrech (karty bez). Přechody 0,5 s (fade), start z černé, konec do černé.
"""
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "cinema", "edit"))
import gfx  # noqa: E402

HRUBY = os.path.join(ROOT, "out", "trailer", "v2", "hruby")
FINAL = os.path.join(ROOT, "out", "trailer", "v2", "final")
WORK = os.path.join(ROOT, "tmp", "v2", "final")
HUDBA = os.path.join(ROOT, "out", "trailer", "hudba")
FFMPEG = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
FFPROBE = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe"
NVSMI = "nvidia-smi"
FPS = 60
XF = 30
MUSIC_XFADE = 3.0
BRAND = {"title": "SPRAYDRONE", "subtitle": "Postřikové drony pro Farming Simulator 25"}

FILMY = {
    "mini": dict(nazev="Mini", latka="herbicid", soubor="SDT_Mini_v2", hudba="Inspired", epilog=True),
    "middle": dict(nazev="Middle", latka="hnojivo", soubor="SDT_Middle_v2", hudba="Heroic Age", epilog=True),
    "max": dict(nazev="Max", latka="vápno", soubor="SDT_Max_v2", hudba="Dreams Become Real", epilog=True),
    "prod": dict(nazev="Produkty", latka=None, soubor="SDT_Produkty_v2", hudba="Impact Moderato", epilog=False),
}
INTRO_S, END_S = 3.0, 5.0


def run(cmd, capture=True, check=True):
    r = subprocess.run(cmd, capture_output=capture, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode:
        raise SystemExit("příkaz selhal (%d)\n%s" % (r.returncode, (r.stderr or "")[-2500:]))
    return r


def dur(path):
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(r.stdout.strip())


def gpu_volne():
    try:
        r = run([NVSMI, "--query-gpu=memory.used", "--format=csv,noheader,nounits"], check=False)
        used = int(r.stdout.strip().splitlines()[0])
        o = run(["ollama", "ps"], check=False).stdout.strip().splitlines()
        return used < 4000 and len(o) <= 1
    except Exception:
        return False


def plan_filmu(film):
    c = FILMY[film]
    kus = []
    intro_sub = c["nazev"] if not c["latka"] else "%s  ·  %s" % (c["nazev"], c["latka"])
    kus.append(dict(typ="karta", id="intro", frames=int(INTRO_S * FPS), karta=("title", {"title": BRAND["title"], "subtitle": intro_sub}, None), fade="in"))
    kus.append(dict(typ="film", id=film, path=os.path.join(HRUBY, film + ".mp4")))
    if c["epilog"]:
        kus.append(dict(typ="film", id="spol", path=os.path.join(HRUBY, "spol.mp4")))
    credit = "Music: %s by Kevin MacLeod (incompetech.com) / CC BY 4.0" % c["hudba"]
    kus.append(dict(typ="karta", id="konec", frames=int(END_S * FPS), karta=("end", None, credit), fade="out"))
    for k in kus:
        if k["typ"] == "film":
            k["frames"] = int(round(dur(k["path"]) * FPS))
    start = 0
    for i, k in enumerate(kus):
        if i:
            start += kus[i - 1]["frames"] - XF
        k["start"] = start
    total = kus[-1]["start"] + kus[-1]["frames"]
    return kus, total, credit


def graf_video(kus, work):
    inputs, ch, labels = [], [], []
    for i, k in enumerate(kus):
        F = k["frames"]
        if k["typ"] == "film":
            inputs += ["-i", k["path"]]
            ch.append("[%d:v]settb=1/60,setpts=N,trim=end_frame=%d,vignette=angle=PI/15,format=yuv420p,setsar=1[i%d]" % (i, F, i))
        else:
            kind, data, credit = k["karta"]
            png = gfx.card_png(work, kind, data, data or BRAND, credit=credit)
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", "%.3f" % (F / FPS + 0.2), "-i", png]
            fade = "fade=t=in:st=0:d=0.6," if k["fade"] == "in" else "fade=t=out:st=%.3f:d=1.2," % (F / FPS - 1.2)
            ch.append("[%d:v]settb=1/60,setpts=N,trim=end_frame=%d,format=yuv420p,%ssetsar=1[i%d]" % (i, F, fade, i))
        labels.append("i%d" % i)
    cur, curfr = labels[0], kus[0]["frames"]
    for i in range(1, len(kus)):
        out = "x%d" % i
        ch.append("[%s][%s]xfade=transition=fade:duration=%.5f:offset=%.5f,settb=1/60[%s]" % (cur, labels[i], XF / FPS, (curfr - XF) / FPS, out))
        curfr += kus[i]["frames"] - XF
        cur = out
    ch.append("[%s]null[vout]" % cur)
    return inputs, ";\n".join(ch)


def graf_audio(film, total_s):
    path = os.path.join(HUDBA, FILMY[film]["hudba"] + ".mp3")
    d = dur(path)
    need = total_s + 1.0
    segs, covered = [], 0.0
    while covered < need:
        overlap = MUSIC_XFADE if segs else 0.0
        take = min(d, need - covered + overlap)
        segs.append((take, overlap))
        covered += take - overlap
    inputs, ch = [], []
    for i, (take, _) in enumerate(segs):
        inputs += ["-t", "%.3f" % take, "-i", path]
        ch.append("[%d:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[m%d]" % (i, i))
    cur = "m0"
    for i in range(1, len(segs)):
        ch.append("[%s][m%d]acrossfade=d=%.2f:c1=tri:c2=tri[mx%d]" % (cur, i, MUSIC_XFADE, i))
        cur = "mx%d" % i
    ch.append("[%s]atrim=0:%.3f,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.2,afade=t=out:st=%.3f:d=3.0[mix]" % (cur, total_s, total_s - 3.0))
    return inputs, ch, len(segs)


def loudnorm(a_inputs, a_chain, wav, tag):
    base = ";\n".join(a_chain)
    sk = os.path.join(WORK, "audio_%s.txt" % tag)
    with open(sk, "w", encoding="utf-8") as f:
        f.write(base + ";\n[mix]loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json[a]")
    r = run([FFMPEG, "-hide_banner", "-y", "-nostats"] + a_inputs + ["-/filter_complex", sk, "-map", "[a]", "-f", "null", "-"])
    j = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    print("   loudnorm pass 1: I=%s LUFS TP=%s LRA=%s" % (j["input_i"], j["input_tp"], j["input_lra"]))
    with open(sk, "w", encoding="utf-8") as f:
        f.write(base + ";\n[mix]loudnorm=I=-14:TP=-2.0:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true,alimiter=limit=0.76:level=disabled[a]" % (
            j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"]))
    run([FFMPEG, "-hide_banner", "-y", "-nostats", "-loglevel", "error"] + a_inputs + ["-/filter_complex", sk, "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", wav])


def kodek(nv):
    if nv:
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr", "-cq", "18", "-b:v", "0", "-spatial-aq", "1", "-profile:v", "high", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]


def poster_a_list(film, kus, total):
    from PIL import Image, ImageDraw, ImageFont
    out = os.path.join(FINAL, FILMY[film]["soubor"] + ".mp4")
    zaklad = out[:-4]
    t_film = kus[1]["start"] / FPS
    d_film = kus[1]["frames"] / FPS
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "%.3f" % (t_film + d_film * 0.35), "-i", out, "-frames:v", "1", "-q:v", "2", zaklad + ".jpg"])
    total_s = total / FPS
    casy = [INTRO_S / 2] + [INTRO_S + (total_s - INTRO_S - END_S) * (i + 0.5) / 22 for i in range(22)] + [total_s - END_S / 2 - 0.3]
    sloupcu, tw = 6, 384
    th = tw * 9 // 16
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 14)
    img = Image.new("RGB", (sloupcu * tw, 4 * (th + 20)), (24, 24, 24))
    d = ImageDraw.Draw(img)
    tmp = os.path.join(WORK, "_snimek.jpg")
    for i, t in enumerate(casy):
        run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "%.3f" % t, "-i", out, "-frames:v", "1", "-vf", "scale=%d:%d" % (tw, th), "-q:v", "3", tmp])
        im = Image.open(tmp)
        x, y = (i % sloupcu) * tw, (i // sloupcu) * (th + 20)
        img.paste(im, (x, y + 20))
        d.text((x + 4, y + 2), "%.1f s" % t, font=font, fill=(150, 210, 255))
        im.close()
    os.remove(tmp)
    img.save(zaklad + "_nahled.jpg", quality=88)


def overeni(path, total):
    r = run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=width,height,r_frame_rate,avg_frame_rate,nb_read_frames,codec_name:format=duration", "-of", "json", path])
    j = json.loads(r.stdout)
    st = j["streams"][0]
    ok = st["r_frame_rate"] == "60/1" and st["avg_frame_rate"] == "60/1" and (st["width"], st["height"]) == (1920, 1080) and abs(int(st["nb_read_frames"]) - total) <= 1
    print("   ffprobe: %s %dx%d r=%s avg=%s snímků %s (plán %d) %.2f s  %s" % (st["codec_name"], st["width"], st["height"], st["r_frame_rate"], st["avg_frame_rate"], st["nb_read_frames"], total, float(j["format"]["duration"]), "OK" if ok else "ODCHYLKA"))
    r = run([FFMPEG, "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"])
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    pk = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    print("   hlasitost I=%s LUFS, true peak=%s dBFS" % (I.group(1) if I else "?", pk.group(1) if pk else "?"))
    ra = run([FFPROBE, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name,channels,sample_rate,bit_rate", "-of", "csv=p=0", path])
    print("   audio: %s, velikost %.1f MB" % (ra.stdout.strip(), os.path.getsize(path) / 1e6))


def zpracuj(film, opts):
    os.makedirs(FINAL, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    kus, total, credit = plan_filmu(film)
    total_s = total / FPS
    nv = ("--cpu" not in opts) and gpu_volne()
    print("== %s: %.2f s (%d snímků), hudba %s, kodér %s" % (film, total_s, total, FILMY[film]["hudba"], "h264_nvenc" if nv else "libx264 crf 18"))
    for k in kus:
        print("  %6.2f  %6.2f s  %s" % (k["start"] / FPS, k["frames"] / FPS, k["id"]))
    print("  kredit: %s" % credit)
    out = os.path.join(FINAL, FILMY[film]["soubor"] + ".mp4")
    if "--dry" in opts:
        return
    if "--jen-list" not in opts:
        v_in, v_graf = graf_video(kus, WORK)
        sk = os.path.join(WORK, "video_%s.txt" % film)
        with open(sk, "w", encoding="utf-8") as f:
            f.write(v_graf)
        a_in, a_chain, _ = graf_audio(film, total_s)
        wav = os.path.join(WORK, "audio_%s.wav" % film)
        loudnorm(a_in, a_chain, wav, film)
        cmd = [FFMPEG, "-hide_banner", "-y", "-loglevel", "warning", "-stats"] + v_in + ["-i", wav, "-/filter_complex", sk, "-map", "[vout]", "-map", "%d:a" % len(kus),
               "-fps_mode", "cfr", "-r", str(FPS)] + kodek(nv) + ["-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", "-t", "%.4f" % total_s, out]
        run(cmd, capture=False)
        overeni(out, total)
    poster_a_list(film, kus, total)
    print("   hotovo: %s" % out)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    opts = [x for x in sys.argv[1:] if x.startswith("--")]
    if not a or (a[0] != "all" and a[0] not in FILMY):
        raise SystemExit(__doc__)
    for film in (list(FILMY) if a[0] == "all" else [a[0]]):
        zpracuj(film, opts)


if __name__ == "__main__":
    main()
