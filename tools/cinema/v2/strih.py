"""Hrubý střih SprayDrone v2: z edl/<film>.json vyrenderuje out/trailer/v2/hruby/<film>.mp4 (1920x1080, CFR 60, libx264, bez zvuku)
a kontaktní list <film>_list.jpg (jeden snímek na střih s popiskem záběr / kamera / pohyb).

Spuštění: python tools/cinema/v2/strih.py <mini|middle|max|spol|prod|all> [--dry] [--jen-list] [--nolist]
  --dry       jen vypíše plán střihů, kontroly a očekávanou délku (nic nerenderuje)
  --jen-list  přegeneruje kontaktní list z už hotového mp4
  --nolist    nerenderuje kontaktní list
Kódování je CPU (libx264), takže GPU se nepoužívá.
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
V2 = os.path.join(ROOT, "tools", "cinema", "v2")
OUT = os.path.join(ROOT, "out", "trailer", "v2", "hruby")
FFMPEG = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
FFPROBE = r"C:\Users\Pavel\AppData\Local\Microsoft\WinGet\Links\ffprobe.exe"
FILMY = ["mini", "middle", "max", "spol", "prod"]
FPS = 60
W, H = 1920, 1080


def nacti(film):
    with open(os.path.join(V2, "edl", film + ".json"), encoding="utf-8") as f:
        return json.load(f)


def plan(edl):
    """Vrací seznam (střih, snímky, xfade_snímky, začátek_ve_filmu_s) a celkový počet snímků."""
    vysl = []
    cur = 0
    for i, s in enumerate(edl["strihy"]):
        n = round((s["out_s"] - s["in_s"]) * FPS)
        tf = 0
        if i > 0 and s["prechod"].startswith("xfade"):
            tf = round(float(s["prechod"].split()[1]) * FPS)
        zac = (cur - tf) if i > 0 else 0
        vysl.append((s, n, tf, zac / FPS))
        cur = zac + n
    return vysl, cur


def filtr(pl):
    r = []
    for i, (s, n, tf, _) in enumerate(pl):
        r.append("[%d:v]fps=%d,trim=end_frame=%d,setpts=PTS-STARTPTS,scale=%d:%d:flags=bicubic,setsar=1,format=yuv420p,settb=1/%d[v%d]"
                 % (i, FPS, n, W, H, FPS, i))
    cur, curfr = "v0", pl[0][1]
    for i in range(1, len(pl)):
        s, n, tf, _ = pl[i]
        out = "x%d" % i
        if tf:
            r.append("[%s][v%d]xfade=transition=fade:duration=%.5f:offset=%.5f,fps=%d,settb=1/%d[%s]"
                     % (cur, i, tf / FPS, (curfr - tf) / FPS, FPS, FPS, out))
            curfr += n - tf
        else:
            r.append("[%s][v%d]concat=n=2:v=1:a=0,fps=%d,settb=1/%d[%s]" % (cur, i, FPS, FPS, out))
            curfr += n
        cur = out
    return ";\n".join(r), cur


def vypis_plan(film, edl, pl, celkem):
    h = edl["hlavicka"]
    print("== %s: %d střihů, %.2f s (cíl %s s)" % (film, len(pl), celkem / FPS, h["cilova_delka_s"]))
    for s, n, tf, zac in pl:
        print("  %6.2f  %-12s %s %-8s %-4s %6.2f-%-6.2f %4.1f s  %-8s %s" % (
            zac, s["zaber"], s["kamera"], s["pohyb"], s["smer"], s["in_s"], s["out_s"], n / FPS, "xfade" if tf else "", s["klip"].rsplit("/", 1)[-1]))
    prev = None
    for s, *_ in pl:
        if prev and prev["pohyb"] == s["pohyb"] and prev["smer"] == s["smer"]:
            print("  POZOR: %s po %s stejný pohyb %s %s" % (s["zaber"], prev["zaber"], s["pohyb"], s["smer"]))
        prev = s


def render(film, edl, pl, celkem):
    os.makedirs(OUT, exist_ok=True)
    skript = os.path.join(OUT, "_%s.filter.txt" % film)
    graf, vystup = filtr(pl)
    with open(skript, "w", encoding="utf-8") as f:
        f.write(graf)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "warning", "-stats"]
    for s, n, tf, _ in pl:
        cmd += ["-ss", "%.3f" % s["in_s"], "-t", "%.3f" % (n / FPS + 0.3), "-i", os.path.join(ROOT, s["klip"])]
    cmd += ["-/filter_complex", skript, "-map", "[%s]" % vystup,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-fps_mode", "cfr", "-an", "-movflags", "+faststart", os.path.join(OUT, film + ".mp4")]
    r = subprocess.run(cmd)
    os.remove(skript)
    if r.returncode:
        raise SystemExit("ffmpeg selhal (%d)" % r.returncode)


def probe(film):
    cesta = os.path.join(OUT, film + ".mp4")
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                        "stream=width,height,r_frame_rate,avg_frame_rate,nb_read_frames,codec_name:format=duration", "-of", "json", cesta],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    st = d["streams"][0]
    return dict(w=st["width"], h=st["height"], r=st["r_frame_rate"], avg=st["avg_frame_rate"], snimky=int(st["nb_read_frames"]),
                delka=float(d["format"]["duration"]))


def kontaktni_list(film, pl):
    from PIL import Image, ImageDraw, ImageFont
    film_mp4 = os.path.join(OUT, film + ".mp4")
    sloupcu, tw = 5, 384
    th = tw * 9 // 16
    popis_h = 38
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 15)
    rady = (len(pl) + sloupcu - 1) // sloupcu
    list_img = Image.new("RGB", (sloupcu * tw, rady * (th + popis_h)), (24, 24, 24))
    tmp = os.path.join(OUT, "_snimek_%s.jpg" % film)
    d = ImageDraw.Draw(list_img)
    for i, (s, n, tf, zac) in enumerate(pl):
        t = zac + (tf + (n - tf) * 0.4) / FPS
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "%.3f" % t, "-i", film_mp4, "-frames:v", "1",
                        "-vf", "scale=%d:%d" % (tw, th), "-q:v", "3", tmp], check=True)
        im = Image.open(tmp)
        x, y = (i % sloupcu) * tw, (i // sloupcu) * (th + popis_h)
        list_img.paste(im, (x, y + popis_h))
        d.text((x + 4, y + 2), "%d  %s  kam %s  %s %s" % (i + 1, s["zaber"], s["kamera"], s["pohyb"], s["smer"] if s["smer"] != "-" else ""), font=font, fill=(255, 255, 255))
        d.text((x + 4, y + 20), "%.1f s%s  [%.1f-%.1f]" % (n / FPS, "  xfade" if tf else "", s["in_s"], s["out_s"]), font=font, fill=(150, 210, 255))
        im.close()
    os.remove(tmp)
    list_img.save(os.path.join(OUT, film + "_list.jpg"), quality=88)


def zpracuj(film, args):
    edl = nacti(film)
    pl, celkem = plan(edl)
    vypis_plan(film, edl, pl, celkem)
    if "--dry" in args:
        return
    if "--jen-list" not in args:
        render(film, edl, pl, celkem)
        p = probe(film)
        ok = p["r"] == "60/1" and p["avg"] == "60/1" and abs(p["snimky"] - celkem) <= 1
        print("   ffprobe: %dx%d r=%s avg=%s snímků %d (plán %d), %.2f s  %s" % (p["w"], p["h"], p["r"], p["avg"], p["snimky"], celkem, p["delka"], "OK" if ok else "ODCHYLKA"))
    if "--nolist" not in args:
        kontaktni_list(film, pl)
        print("   list: %s" % os.path.join(OUT, film + "_list.jpg"))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    opts = [x for x in sys.argv[1:] if x.startswith("--")]
    if not a or (a[0] != "all" and a[0] not in FILMY):
        raise SystemExit(__doc__)
    for film in (FILMY if a[0] == "all" else [a[0]]):
        zpracuj(film, opts)


if __name__ == "__main__":
    main()
