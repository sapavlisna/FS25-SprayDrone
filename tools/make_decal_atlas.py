"""Nakreslí atlas nápisů a nálepek malého vleku (rozvržení blender/decal_layout.py) a převede ho na DDS.

python tools/make_decal_atlas.py

Zdroj: blender/textures/sdt_decals.png, do módu: vehicles/sprayDroneTrailerMiddle/textures/sdt_decals.dds (DXT1 s mipmapami).
Písmo DejaVu Sans (volná licence), žádná loga cizích značek.
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT, "blender"))
sys.path.insert(0, os.path.join(PROJECT, "tools"))
import decal_layout as L  # noqa: E402
import png2dds  # noqa: E402

SRC_PNG = os.path.join(PROJECT, "blender", "textures", L.ATLAS_PNG)
DDS = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "vehicles", "sprayDroneTrailerMiddle", "textures", L.ATLAS_DDS)
FONT_DIR = r"C:\Windows\Fonts"
SS = 2

ORANGE = (224, 112, 26)
RED = (200, 16, 16)
WHITE = (242, 242, 238)
BLACK = (20, 20, 22)
DARK = (34, 36, 40)
SCREEN = (8, 22, 40)
GREEN = (60, 230, 90)
YELLOW = (240, 196, 20)


def font(size, bold=True, cond=False, mono=False):
    name = "DejaVuSans%s%s.ttf" % ("Mono" if mono else ("Condensed" if cond else ""), "-Bold" if bold else "")
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size * SS)


def box(name):
    x, y, w, h = L.REGIONS[name]
    return x * SS, y * SS, w * SS, h * SS


def text_center(d, cx, cy, s, f, fill):
    b = d.textbbox((0, 0), s, font=f)
    d.text((cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2), s, font=f, fill=fill)


def text_left(d, x, cy, s, f, fill):
    b = d.textbbox((0, 0), s, font=f)
    d.text((x - b[0], cy - (b[1] + b[3]) / 2), s, font=f, fill=fill)
    return x + b[2] - b[0]


def warning_triangle(d, cx, cy, size, fill=YELLOW):
    r = size / 2
    d.polygon([(cx, cy - r), (cx + r * 1.1, cy + r * 0.85), (cx - r * 1.1, cy + r * 0.85)], fill=BLACK)
    rr = r * 0.78
    d.polygon([(cx, cy - rr + r * 0.06), (cx + rr * 1.1, cy + rr * 0.85), (cx - rr * 1.1, cy + rr * 0.85)], fill=fill)
    text_center(d, cx, cy + r * 0.22, "!", font(int(size / SS * 0.55)), BLACK)


def draw_stripe(d):
    x, y, w, h = box("stripe")
    d.rectangle((x, y, x + w, y + h), fill=WHITE)
    pitch = 64 * SS
    for k in range(-2, w // pitch + 3):
        x0 = x + k * pitch
        d.polygon([(x0, y + h), (x0 + pitch / 2, y + h), (x0 + pitch / 2 + h, y), (x0 + h, y)], fill=RED)


def draw_side_text(d, count=5, x=None, y=None):
    """Nápis na boku plošiny; počet baterií je až za L.SIDE_TEXT_SPLIT (tam začíná oblast sideText<počet>)."""
    _, _, w, h = box("sideText")
    if x is None:
        x, y, _, _ = box("sideText")
    d.rectangle((x, y, x + w, y + h), fill=ORANGE)
    d.rectangle((x, y, x + w, y + 4 * SS), fill=BLACK)
    d.rectangle((x, y + h - 4 * SS, x + w, y + h), fill=BLACK)
    cx, cy = x + 60 * SS, y + h / 2
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px, py = cx + dx * 16 * SS, cy + dy * 13 * SS
        d.line((cx, cy, px, py), fill=BLACK, width=4 * SS)
        d.ellipse((px - 9 * SS, py - 4 * SS, px + 9 * SS, py + 4 * SS), outline=BLACK, width=3 * SS)
    d.rounded_rectangle((cx - 8 * SS, cy - 6 * SS, cx + 8 * SS, cy + 6 * SS), 3 * SS, fill=BLACK)
    text_left(d, x + 110 * SS, cy, "BZUK  FLYING SPRAYERS", font(40), BLACK)
    text_left(d, x + w * L.SIDE_TEXT_SPLIT + 18 * SS, cy, "%d × 52 V" % count, font(26, bold=False), BLACK)


def draw_side_text_count(img, count):
    """Oblast sideText<počet>: pravá část nápisu od SIDE_TEXT_SPLIT s jiným počtem baterií, zmenšená do oblasti."""
    _, _, w, h = box("sideText")
    tile = Image.new("RGB", (w, h), ORANGE)
    draw_side_text(ImageDraw.Draw(tile), count, 0, 0)
    x0 = round(w * L.SIDE_TEXT_SPLIT)
    x, y, rw, rh = box("sideText%d" % count)
    img.paste(tile.crop((x0, 0, w, h)).resize((rw, rh), Image.LANCZOS), (x, y))


BRAND_DARK = (36, 39, 42)                   # pruh se značkou jako popruhy plachty (brand_layout.TARP_STRAP_COLOR)
BRAND_RED = (200, 16, 46)                   # BZUK (brand_layout.DESIGNS["BZUK"]["p"])


def brand_mark(size):
    """Znak BZUK z atlasu značky (blender/textures/sdt_brand.png, oblast mark_BZUK) jako RGBA size x size px."""
    import brand_layout as BL
    x, y, w, h = BL.REGIONS["mark_BZUK"]
    atlas = Image.open(os.path.join(PROJECT, "blender", "textures", BL.ATLAS_PNG)).convert("RGBA")
    return atlas.crop((x, y, x + w, y + h)).resize((size, size), Image.LANCZOS)


def draw_canister_label(d, img=None):
    """Neutrální štítek kanystru v bedně (plátno 336 x 168 = 0,168 x 0,084 m): bez druhu obsahu, barvu kanystru dává skript.
    Nahoře tmavý pruh se znakem a nápisem BZUK, dole pruh v barvě značky."""
    d.rectangle((0, 0, 336 * SS, 168 * SS), fill=WHITE)
    d.rectangle((0, 0, 336 * SS, 44 * SS), fill=BRAND_DARK)
    f = font(30)
    tw = d.textbbox((0, 0), "BZUK", font=f)[2]
    mark = 36 * SS
    x0 = (336 * SS - (mark + 10 * SS + tw)) // 2
    if img is not None:
        img.paste(brand_mark(mark), (x0, 4 * SS), brand_mark(mark))
    text_left(d, x0 + mark + 10 * SS, 22 * SS, "BZUK", f, WHITE)
    text_center(d, 168 * SS, 100 * SS, "20 l", font(74, cond=True), BLACK)
    d.rectangle((0, 150 * SS, 336 * SS, 168 * SS), fill=BRAND_RED)
    d.rectangle((2 * SS, 2 * SS, 334 * SS, 166 * SS), outline=BLACK, width=4 * SS)


def draw_battery(d, key):
    x, y, w, h = box("battery" + key)
    size, cap = L.BATTERY_TEXT[key]
    d.rectangle((x, y, x + w, y + h), fill=WHITE)
    d.rectangle((x, y, x + 64 * SS, y + h), fill=ORANGE)
    text_center(d, x + 32 * SS, y + h / 2, size, font(50), BLACK)
    text_left(d, x + 76 * SS, y + 20 * SS, "BZUK POWER", font(18), BLACK)
    text_left(d, x + 76 * SS, y + 44 * SS, cap, font(22), BLACK)
    text_left(d, x + 76 * SS, y + 62 * SS, "52 V Li-ion", font(12, bold=False), DARK)
    warning_triangle(d, x + 228 * SS, y + 50 * SS, 26 * SS)


def draw_screen(d):
    x, y, w, h = box("chargerScreen")
    d.rectangle((x, y, x + w, y + h), fill=BLACK)
    m = 8 * SS
    d.rectangle((x + m, y + m, x + w - m, y + h - m), fill=SCREEN)
    text_left(d, x + 18 * SS, y + 26 * SS, "BZUK CHARGER", font(16), WHITE)
    text_left(d, x + 170 * SS, y + 26 * SS, "9,0 kW", font(14, bold=False), GREEN)
    levels = (1.0, 0.95, 0.64, 0.32, 0.0)
    for i, lv in enumerate(levels):
        by = y + (46 + i * 22) * SS
        text_left(d, x + 18 * SS, by + 8 * SS, str(i + 1), font(13), WHITE)
        d.rectangle((x + 36 * SS, by, x + 186 * SS, by + 16 * SS), outline=(90, 110, 130), width=2 * SS)
        if lv > 0:
            col = GREEN if lv >= 0.95 else (YELLOW if lv > 0.3 else (230, 90, 40))
            d.rectangle((x + 39 * SS, by + 3 * SS, x + 39 * SS + int(144 * SS * lv), by + 13 * SS), fill=col)
        text_left(d, x + 194 * SS, by + 8 * SS, "%d %%" % round(lv * 100) if lv else "--", font(12, bold=False), WHITE)


def draw_charger_label(d):
    x, y, w, h = box("chargerLabel")
    d.rectangle((x, y, x + w, y + h), fill=WHITE)
    d.rectangle((x, y, x + w, y + 10 * SS), fill=ORANGE)
    warning_triangle(d, x + 52 * SS, y + 70 * SS, 70 * SS)
    text_left(d, x + 104 * SS, y + 40 * SS, "BZUK CHARGER C5", font(30), BLACK)
    text_left(d, x + 104 * SS, y + 74 * SS, "VSTUP 230 V AC   VÝSTUP 52 V DC   9 kW", font(17, bold=False), BLACK)
    text_left(d, x + 104 * SS, y + 100 * SS, "Pouze baterie BZUK POWER", font(15, bold=False), DARK)


def draw_diesel(d):
    x, y, w, h = box("dieselLabel")
    d.rectangle((x, y, x + w, y + h), fill=YELLOW)
    d.rectangle((x + 6 * SS, y + 6 * SS, x + w - 6 * SS, y + h - 6 * SS), outline=BLACK, width=4 * SS)
    px, py = x + 40 * SS, y + 64 * SS
    d.rectangle((px - 14 * SS, py - 26 * SS, px + 10 * SS, py + 30 * SS), fill=BLACK)
    d.rectangle((px - 9 * SS, py - 20 * SS, px + 5 * SS, py - 6 * SS), fill=YELLOW)
    d.line((px + 10 * SS, py - 18 * SS, px + 22 * SS, py - 8 * SS, px + 22 * SS, py + 20 * SS), fill=BLACK, width=4 * SS)
    text_left(d, x + 72 * SS, y + 48 * SS, "NAFTA", font(25), BLACK)
    text_left(d, x + 72 * SS, y + 86 * SS, "30 l", font(26, bold=False), BLACK)


def text_right(d, x, cy, s, f, fill):
    b = d.textbbox((0, 0), s, font=f)
    d.text((x - b[2], cy - (b[1] + b[3]) / 2), s, font=f, fill=fill)


def draw_gen_panel(d):
    """Ovládací panel elektrocentrály: 1 px = 1 mm, polohy prvků z L.GEN_PANEL (metry od levého dolního rohu)."""
    x, y, w, h = box("genPanel")
    d.rectangle((x, y, x + w, y + h), fill=(26, 28, 32))
    d.rectangle((x + 3 * SS, y + 3 * SS, x + w - 3 * SS, y + h - 3 * SS), outline=(74, 78, 86), width=2 * SS)
    grey, white, orange = (170, 174, 180), WHITE, ORANGE

    def at(name):
        u, v = L.GEN_PANEL[name]
        return x + u * 1000 * SS, y + h - v * 1000 * SS

    cx, cy = at("volt")
    r = 27 * SS
    d.ellipse((cx - r - 3 * SS, cy - r - 3 * SS, cx + r + 3 * SS, cy + r + 3 * SS), fill=(8, 8, 10))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(234, 234, 228))
    for i in range(11):
        a = math.radians(210 - i * 24)
        c, s_ = math.cos(a), -math.sin(a)
        col = RED if i >= 8 else BLACK
        d.line((cx + c * r * 0.76, cy + s_ * r * 0.76, cx + c * r * 0.94, cy + s_ * r * 0.94), fill=col, width=2 * SS)
    a = math.radians(210 - 7.4 * 24)
    d.line((cx, cy, cx + math.cos(a) * r * 0.82, cy - math.sin(a) * r * 0.82), fill=RED, width=2 * SS)
    d.ellipse((cx - 3 * SS, cy - 3 * SS, cx + 3 * SS, cy + 3 * SS), fill=BLACK)
    text_center(d, cx, cy + 13 * SS, "V", font(13), BLACK)
    text_center(d, cx, cy - r - 11 * SS, "NAPĚTÍ", font(11), white)

    cx, cy = at("hours")
    d.rectangle((cx - 35 * SS, cy - 14 * SS, cx + 35 * SS, cy + 14 * SS), fill=(156, 172, 130), outline=(8, 8, 10),
                width=2 * SS)
    text_center(d, cx, cy, "00128.4", font(15, mono=True), (28, 40, 22))
    text_center(d, cx, cy - 26 * SS, "HODINY", font(11), white)

    for name, label, col in (("ledRun", "CHOD", (40, 120, 55)), ("ledOil", "OLEJ", (130, 25, 25)),
                             ("ledTemp", "TEPL.", (150, 100, 20))):
        cx, cy = at(name)
        d.ellipse((cx - 11 * SS, cy - 11 * SS, cx + 11 * SS, cy + 11 * SS), fill=(8, 8, 10), outline=grey, width=SS)
        d.ellipse((cx - 6 * SS, cy - 6 * SS, cx + 6 * SS, cy + 6 * SS), fill=col)
        text_center(d, cx, cy + 22 * SS, label, font(10), white)

    cx, cy = at("key")
    d.ellipse((cx - 24 * SS, cy - 24 * SS, cx + 24 * SS, cy + 24 * SS), outline=grey, width=2 * SS)
    for ang in (180, 90, 0):
        a = math.radians(ang)
        d.line((cx + math.cos(a) * 26 * SS, cy - math.sin(a) * 26 * SS, cx + math.cos(a) * 32 * SS,
                cy - math.sin(a) * 32 * SS), fill=white, width=2 * SS)
    text_center(d, cx - 50 * SS, cy + 2 * SS, "VYP", font(11), white)
    text_center(d, cx, cy - 40 * SS, "ZAP", font(11), (120, 230, 130))
    text_center(d, cx + 58 * SS, cy + 2 * SS, "START", font(11), orange)

    cx, cy = at("preheat")
    d.ellipse((cx - 17 * SS, cy - 17 * SS, cx + 17 * SS, cy + 17 * SS), outline=grey, width=2 * SS)
    text_left(d, cx + 30 * SS, cy, "ŽHAVENÍ", font(11), white)

    cx, cy = at("socket")
    d.rounded_rectangle((cx - 35 * SS, cy - 35 * SS, cx + 35 * SS, cy + 35 * SS), 8 * SS, outline=(200, 204, 210),
                        width=2 * SS)
    text_center(d, cx, cy - 47 * SS, "230 V ~  16 A", font(14), white)
    text_center(d, cx, cy + 46 * SS, "NABÍJEČKA", font(12), orange)

    cx, cy = at("rocker")
    d.rounded_rectangle((cx - 24 * SS, cy - 15 * SS, cx + 24 * SS, cy + 15 * SS), 4 * SS, outline=grey, width=2 * SS)
    text_center(d, cx - 36 * SS, cy, "0", font(15), white)
    text_center(d, cx + 36 * SS, cy, "I", font(15), white)
    text_center(d, cx, cy - 26 * SS, "VÝSTUP", font(10), grey)

    cx, cy = at("mcb")
    d.rectangle((cx - 20 * SS, cy - 32 * SS, cx + 20 * SS, cy + 32 * SS), outline=grey, width=2 * SS)
    text_center(d, cx, cy - 47 * SS, "JISTIČ 16 A", font(11), white)
    text_center(d, cx + 33 * SS, cy - 18 * SS, "I", font(12), white)
    text_center(d, cx + 33 * SS, cy + 18 * SS, "O", font(12), white)

    cx, cy = at("earth")
    d.ellipse((cx - 14 * SS, cy - 14 * SS, cx + 14 * SS, cy + 14 * SS), outline=grey, width=2 * SS)
    d.line((cx, cy - 8 * SS, cx, cy - SS), fill=white, width=2 * SS)
    for k, hw in enumerate((8, 5, 2)):
        d.line((cx - hw * SS, cy + (1 + 4 * k) * SS, cx + hw * SS, cy + (1 + 4 * k) * SS), fill=white, width=2 * SS)
    text_left(d, x + 318 * SS, y + h - 10 * SS, "BZUK POWER  DG-9D", font(9), (120, 124, 132))


def draw_gen_warn(d):
    """Tři výstražné trojúhelníky (dlaždice 128 x 112, rovnostranný trojúhelník): horký povrch, výfukové plyny,
    vysoké napětí. Mimo trojúhelník je dlaždice černá, aby okraj trojúhelníkové nálepky nebral bílou."""
    x, y, w, h = box("genWarn")
    tw, th = w // 3, h
    for k in range(3):
        ox = x + k * tw
        d.rectangle((ox, y, ox + tw, y + th), fill=BLACK)
        gcx, gcy = ox + tw / 2, y + th * (2 / 3)
        outer = [(ox, y + th), (ox + tw, y + th), (ox + tw / 2, y)]
        sc = 0.80
        d.polygon([(gcx + (px - gcx) * sc, gcy + (py - gcy) * sc) for px, py in outer], fill=YELLOW)
        if k == 0:
            d.rectangle((gcx - 22 * SS, gcy + 14 * SS, gcx + 22 * SS, gcy + 21 * SS), fill=BLACK)
            for dx in (-13, 0, 13):
                pts = [(gcx + (dx + 4 * math.sin(t / 3.0)) * SS, gcy + (8 - t) * SS) for t in range(0, 32, 2)]
                d.line(pts, fill=BLACK, width=3 * SS)
        elif k == 1:
            for ccx, ccy, cr in ((-13, 6, 10), (0, -3, 13), (14, 5, 10)):
                d.ellipse((gcx + (ccx - cr) * SS, gcy + (ccy - cr) * SS, gcx + (ccx + cr) * SS, gcy + (ccy + cr) * SS),
                          fill=BLACK)
            d.rectangle((gcx - 15 * SS, gcy + 6 * SS, gcx + 16 * SS, gcy + 15 * SS), fill=BLACK)
            text_center(d, gcx, gcy + 5 * SS, "CO", font(15), YELLOW)
        else:
            bolt = [(6, -25), (-12, 4), (-2, 4), (-8, 27), (12, -6), (1, -6), (10, -25)]
            d.polygon([(gcx + bx * SS, gcy + by * SS) for bx, by in bolt], fill=BLACK)


def draw_gen_plate(d):
    """Výrobní štítek elektrocentrály (kartáčovaný kov, černé popisky); bez log skutečných firem."""
    x, y, w, h = box("genPlate")
    d.rectangle((x, y, x + w, y + h), fill=(196, 199, 203))
    rnd = random.Random(7)
    for _ in range(90):
        yy = y + rnd.random() * h
        g = rnd.randint(-10, 10)
        d.line((x, yy, x + w, yy), fill=(196 + g, 199 + g, 203 + g), width=SS)
    d.rectangle((x + 3 * SS, y + 3 * SS, x + w - 3 * SS, y + h - 3 * SS), outline=(60, 62, 66), width=2 * SS)
    for rx, ry in ((10, 10), (w / SS - 10, 10), (10, h / SS - 10), (w / SS - 10, h / SS - 10)):
        d.ellipse((x + (rx - 4) * SS, y + (ry - 4) * SS, x + (rx + 4) * SS, y + (ry + 4) * SS), fill=(90, 92, 96))
    d.rectangle((x + 18 * SS, y + 12 * SS, x + w - 18 * SS, y + 42 * SS), fill=ORANGE)
    text_left(d, x + 26 * SS, y + 27 * SS, "BZUK POWER", font(19, cond=True), BLACK)
    text_right(d, x + w - 26 * SS, y + 27 * SS, "DG-9D", font(19, cond=True), BLACK)
    rows = (("ELEKTROCENTRÁLA  NAFTA", True), ("9,0 kW    230 V ~    50 Hz", False), ("1500 min-1     30 l     IP23", False),
            ("NABÍJENÍ BATERIÍ 52 V DC", False), ("S/N 26-04117     2026", False))
    for i, (t, bold) in enumerate(rows):
        text_left(d, x + 22 * SS, y + (60 + i * 21) * SS, t, font(14, bold=bold, cond=True), BLACK)


def draw_gen_gauge(d):
    """Stupnice ukazatele hladiny nafty (F nahoře, E dole), vedle svislé průhledné trubice."""
    x, y, w, h = box("genGauge")
    d.rectangle((x, y, x + w, y + h), fill=(20, 20, 22))
    top, bot = 18 * SS, h - 18 * SS
    for i in range(9):
        yy = y + top + (bot - top) * i / 8
        ln = 22 if i % 4 == 0 else (14 if i % 2 == 0 else 8)
        d.line((x + 4 * SS, yy, x + (4 + ln) * SS, yy), fill=WHITE, width=2 * SS)
    text_center(d, x + 46 * SS, y + top, "F", font(16), (120, 230, 130))
    text_center(d, x + 46 * SS, y + (top + bot) / 2, "1/2", font(11), WHITE)
    text_center(d, x + 46 * SS, y + bot, "E", font(16), (240, 70, 50))
    d.rectangle((x + 2 * SS, y + bot - 22 * SS, x + 5 * SS, y + bot + 2 * SS), fill=RED)


def draw_led(d):
    x, y, w, h = box("led")
    d.rectangle((x, y, x + w, y + h), fill=(20, 150, 50))
    d.ellipse((x + w * 0.2, y + h * 0.2, x + w * 0.8, y + h * 0.8), fill=(150, 255, 170))


def draw_drone(d, key):
    x, y, w, h = box("drone" + key)
    d.rectangle((x, y, x + w, y + h), fill=WHITE)
    d.rectangle((x, y, x + 70 * SS, y + h), fill=ORANGE)
    text_center(d, x + 35 * SS, y + h / 2, "01", font(34), WHITE)
    text_left(d, x + 82 * SS, y + h / 2, L.DRONE_TEXT[key], font(40), BLACK)


BLUE = (22, 82, 152)
GREY = (196, 199, 203)


def droplet(d, cx, cy, r, fill):
    d.polygon([(cx, cy - r * 1.9), (cx + r * 0.92, cy - r * 0.35), (cx - r * 0.92, cy - r * 0.35)], fill=fill)
    d.ellipse((cx - r, cy - r * 0.95, cx + r, cy + r * 1.05), fill=fill)


def draw_tank_vol(d, size):
    """Velký štítek s jmenovitým objemem hlavní nádrže: modrý pruh, číslo a L, dole popis."""
    x, y, w, h = box("tankVol%d" % size)
    d.rectangle((x, y, x + w, y + h), fill=WHITE)
    d.rectangle((x, y, x + w, y + 34 * SS), fill=BLUE)
    droplet(d, x + 20 * SS, y + 19 * SS, 6 * SS, WHITE)
    text_left(d, x + 34 * SS, y + 18 * SS, "NÁDRŽ", font(19, cond=True), WHITE)
    fs = 74
    while True:
        num, unit = font(fs, cond=True), font(int(fs * 0.62), cond=True)
        nb = d.textbbox((0, 0), str(size), font=num)
        ub = d.textbbox((0, 0), "L", font=unit)
        nw, uw = nb[2] - nb[0], ub[2] - ub[0]
        gap = 7 * SS
        if nw + gap + uw <= w - 20 * SS or fs < 30:
            break
        fs -= 2
    x0 = x + (w - (nw + gap + uw)) / 2
    cy = y + 72 * SS
    d.text((x0 - nb[0], cy - (nb[1] + nb[3]) / 2), str(size), font=num, fill=BLACK)
    d.text((x0 + nw + gap - ub[0], cy + (nb[3] - nb[1]) / 2 - ub[3]), "L", font=unit, fill=BLACK)
    text_center(d, x + w / 2, y + 108 * SS, "jmenovitý objem", font(12, bold=False, cond=True), DARK)
    d.rectangle((x + SS, y + SS, x + w - SS, y + h - SS), outline=BLACK, width=2 * SS)


def draw_tank_text(d):
    x, y, w, h = box("tankText")
    d.rectangle((x, y, x + w, y + h), fill=WHITE)
    d.rectangle((x + SS, y + SS, x + w - SS, y + h - SS), outline=BLACK, width=2 * SS)
    d.rectangle((x + 4 * SS, y + 4 * SS, x + 60 * SS, y + h - 4 * SS), fill=BLUE)
    droplet(d, x + 32 * SS, y + 38 * SS, 12 * SS, WHITE)
    text_left(d, x + 72 * SS, y + 22 * SS, "NÁDRŽ", font(30, cond=True), BLACK)
    text_left(d, x + 72 * SS, y + 48 * SS, "kapalné hnojivo · herbicid · voda", font(17, cond=True), BLACK)


def draw_tank_plate(d):
    """Výrobní štítky 128 x 80: 2 x 2 v oblasti tankPlate (3000, 800 / 1000, 1500) a 5000 v oblasti tankPlate5000."""
    x, y, w, h = box("tankPlate")
    rnd = random.Random(11)
    tw, th = w // 2, h // 2
    x5, y5, _, _ = box("tankPlate5000")
    x4, y4, _, _ = box("tankPlate300")
    tiles = [(3000, x, y), (800, x + tw, y), (1000, x, y + th), (1500, x + tw, y + th), (5000, x5, y5),
             (L.PAD_TANK_LITERS, x4, y4)]
    for size, ox, oy in tiles:
        d.rectangle((ox, oy, ox + tw, oy + th), fill=GREY)
        for _ in range(40):
            yy = oy + rnd.random() * th
            g = rnd.randint(-9, 9)
            d.line((ox, yy, ox + tw, yy), fill=(196 + g, 199 + g, 203 + g), width=SS)
        d.rectangle((ox + 2 * SS, oy + 2 * SS, ox + tw - 2 * SS, oy + th - 2 * SS), outline=(60, 62, 66), width=SS)
        for rx, ry in ((6, 6), (tw / SS - 6, 6), (6, th / SS - 6), (tw / SS - 6, th / SS - 6)):
            d.ellipse((ox + (rx - 2.5) * SS, oy + (ry - 2.5) * SS, ox + (rx + 2.5) * SS, oy + (ry + 2.5) * SS),
                      fill=(90, 92, 96))
        d.rectangle((ox + 10 * SS, oy + 6 * SS, ox + tw - 10 * SS, oy + 21 * SS), fill=ORANGE)
        text_left(d, ox + 14 * SS, oy + 14 * SS, "BZUK NÁDRŽ", font(10), BLACK)
        rows = (("%d L   PE-HD" % size, True, 13), ("max. 0,5 bar  (50 kPa)", False, 10),
                ("S/N 26-MT%d-0417" % size, False, 10), ("2026   UV stabilizovaný", False, 9))
        for i, (t, bold, fs) in enumerate(rows):
            text_left(d, ox + 12 * SS, oy + (31 + i * 13.5) * SS, t, font(fs, bold=bold, cond=True), BLACK)


def draw_tank_arrow(d):
    """Šipky proudění k vypouštěcímu kohoutu (míří doleva): tři šípy a nápis DRAIN."""
    x, y, w, h = box("tankArrow")
    d.rectangle((x, y, x + w, y + h), fill=YELLOW)
    d.rectangle((x + SS, y + SS, x + w - SS, y + h - SS), outline=BLACK, width=2 * SS)
    cy = y + h / 2
    for k in range(3):
        cx = x + (34 + k * 40) * SS
        d.polygon([(cx - 22 * SS, cy), (cx + 6 * SS, cy - 20 * SS), (cx + 16 * SS, cy - 20 * SS),
                   (cx - 12 * SS, cy), (cx + 16 * SS, cy + 20 * SS), (cx + 6 * SS, cy + 20 * SS)], fill=BLACK)
    text_left(d, x + 146 * SS, cy, "VYPUSTIT", font(19, cond=True), BLACK)


def draw_tank_outlet(d):
    x, y, w, h = box("tankOutlet")
    d.rectangle((x, y, x + w, y + h), fill=ORANGE)
    d.rectangle((x + SS, y + SS, x + w - SS, y + h - SS), outline=BLACK, width=2 * SS)
    text_left(d, x + 10 * SS, y + h / 2, "VÝTOK", font(26, cond=True), BLACK)
    ax, cy = x + w - 28 * SS, y + h / 2
    d.polygon([(ax - 20 * SS, cy - 6 * SS), (ax + 3 * SS, cy - 6 * SS), (ax + 3 * SS, cy - 15 * SS), (ax + 22 * SS, cy),
               (ax + 3 * SS, cy + 15 * SS), (ax + 3 * SS, cy + 6 * SS), (ax - 20 * SS, cy + 6 * SS)], fill=BLACK)


def draw_tank_warn(d):
    """Čtyři piktogramy 88 x 88: nestoupat, nepřeplňovat, nepitná voda, ochranné pomůcky."""
    x, y, w, h = box("tankWarn")
    d.rectangle((x, y, x + w, y + h), fill=WHITE)
    t = w // 2
    for k in range(4):
        ox, oy = x + (k % 2) * t, y + (k // 2) * t
        cx, cy = ox + t / 2, oy + t * 0.45
        r = t * 0.38
        lw = int(r * 0.16)
        if k == 0:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE, outline=RED, width=lw)
            d.ellipse((cx - 5 * SS, cy - 22 * SS, cx + 5 * SS, cy - 12 * SS), fill=BLACK)
            d.line((cx, cy - 12 * SS, cx + 2 * SS, cy + 5 * SS), fill=BLACK, width=5 * SS)
            d.line((cx + 2 * SS, cy + 5 * SS, cx - 8 * SS, cy + 20 * SS), fill=BLACK, width=5 * SS)
            d.line((cx + 2 * SS, cy + 5 * SS, cx + 12 * SS, cy + 20 * SS), fill=BLACK, width=5 * SS)
            d.line((cx, cy - 8 * SS, cx - 12 * SS, cy + 2 * SS), fill=BLACK, width=4 * SS)
            d.line((cx, cy - 8 * SS, cx + 12 * SS, cy - 2 * SS), fill=BLACK, width=4 * SS)
            d.line((cx - r * 0.707, cy - r * 0.707, cx + r * 0.707, cy + r * 0.707), fill=RED, width=lw)
            cap = "NESTOUPAT"
        elif k == 1:
            warning_triangle(d, cx, cy + 2 * SS, t * 0.82)
            cap = "NEPŘEPLŇOVAT"
        elif k == 2:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE, outline=RED, width=lw)
            d.polygon([(cx - 13 * SS, cy - 17 * SS), (cx + 13 * SS, cy - 17 * SS), (cx + 9 * SS, cy + 15 * SS),
                       (cx - 9 * SS, cy + 15 * SS)], fill=BLUE)
            d.line((cx - r * 0.707, cy - r * 0.707, cx + r * 0.707, cy + r * 0.707), fill=RED, width=lw)
            cap = "NEPITNÁ VODA"
        else:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BLUE)
            d.rounded_rectangle((cx - 12 * SS, cy - 4 * SS, cx + 12 * SS, cy + 20 * SS), 5 * SS, fill=WHITE)
            for fx in (-9, -3, 3, 9):
                d.rounded_rectangle((cx + (fx - 2.5) * SS, cy - 20 * SS, cx + (fx + 2.5) * SS, cy - 2 * SS), 2 * SS,
                                    fill=WHITE)
            d.rounded_rectangle((cx - 20 * SS, cy - 2 * SS, cx - 10 * SS, cy + 10 * SS), 4 * SS, fill=WHITE)
            cap = "OOPP"
        text_center(d, ox + t / 2, oy + t * 0.90, cap, font(9, cond=True), BLACK)


def paste_canvas(img, name, cw, ch, draw, with_tile=False):
    """Nakreslí polepku na plátno cw x ch (souřadnice ve skutečném poměru stran, násobené SS) a zmenší ji do oblasti
    atlasu. with_tile: kreslicí funkce dostane i plátno (vkládání obrázků)."""
    x, y, w, h = box(name)
    tile = Image.new("RGB", (cw * SS, ch * SS), WHITE)
    if with_tile:
        draw(ImageDraw.Draw(tile), tile)
    else:
        draw(ImageDraw.Draw(tile))
    img.paste(tile.resize((w, h), Image.LANCZOS), (x, y))


def draw_conc_label(d):
    """Štítek koncentrátové nádrže (plátno 260 x 200 = 0,13 x 0,10 m)."""
    d.rectangle((0, 0, 260 * SS, 200 * SS), fill=WHITE)
    d.rectangle((0, 0, 260 * SS, 58 * SS), fill=ORANGE)
    text_center(d, 130 * SS, 30 * SS, "KONCENTRÁT", font(33, cond=True), BLACK)
    text_center(d, 130 * SS, 100 * SS, "max 50 l", font(50, cond=True), BLACK)
    d.rectangle((0, 140 * SS, 260 * SS, 200 * SS), fill=YELLOW)
    warning_triangle(d, 40 * SS, 170 * SS, 46 * SS)
    text_left(d, 74 * SS, 158 * SS, "Nemíchat různé", font(22, cond=True), BLACK)
    text_left(d, 74 * SS, 182 * SS, "přípravky", font(22, cond=True), BLACK)
    d.rectangle((2 * SS, 2 * SS, 258 * SS, 198 * SS), outline=BLACK, width=4 * SS)


def draw_conc_nums(img):
    """Čísla stupnice koncentrátové nádrže: šest dlaždic 80 x 48 (0,05 x 0,03 m), použito pět."""
    x, y, w, h = box("concNums")
    tw, th = w // 3, h // 2
    for k, txt in enumerate(("10", "20", "30", "40", "50")):
        tile = Image.new("RGB", (80 * SS, 48 * SS), (226, 228, 223))
        td = ImageDraw.Draw(tile)
        if k == 4:
            text_right(td, 50 * SS, 26 * SS, txt, font(34, cond=True), BLACK)
            text_right(td, 76 * SS, 30 * SS, "l", font(24, bold=False, cond=True), BLACK)
        else:
            text_right(td, 76 * SS, 26 * SS, txt, font(34, cond=True), BLACK)
        img.paste(tile.resize((tw, th), Image.LANCZOS), (x + (k % 3) * tw, y + (k // 3) * th))


def draw_mix_plate(d):
    d.rectangle((0, 0, 208 * SS, 56 * SS), fill=GREY)
    rnd = random.Random(5)
    for _ in range(50):
        yy = rnd.random() * 56 * SS
        g = rnd.randint(-9, 9)
        d.line((0, yy, 208 * SS, yy), fill=(196 + g, 199 + g, 203 + g), width=SS)
    d.rectangle((2 * SS, 2 * SS, 206 * SS, 54 * SS), outline=(60, 62, 66), width=2 * SS)
    for rx in (9, 199):
        d.ellipse(((rx - 4) * SS, 24 * SS, (rx + 4) * SS, 32 * SS), fill=(90, 92, 96))
    text_left(d, 22 * SS, 18 * SS, "MIX-50", font(24, cond=True), BLACK)
    text_right(d, 190 * SS, 18 * SS, "BZUK", font(18, cond=True), (150, 60, 10))
    text_left(d, 22 * SS, 42 * SS, "230 V · 0,75 kW", font(19, bold=False, cond=True), BLACK)


def draw_mix_arrows(d):
    """Dvě dlaždice 64 x 56: voda (modrá, míří doleva k ose komory) a koncentrát (oranžová, míří doprava)."""
    d.rectangle((0, 0, 128 * SS, 56 * SS), fill=WHITE)
    for k, (col, dirn) in enumerate(((BLUE, -1), (ORANGE, 1))):
        cx = (32 + 64 * k) * SS
        cy = 28 * SS
        pts = [(cx + dirn * 26 * SS, cy), (cx + dirn * 4 * SS, cy - 20 * SS), (cx + dirn * 4 * SS, cy - 9 * SS),
               (cx - dirn * 26 * SS, cy - 9 * SS), (cx - dirn * 26 * SS, cy + 9 * SS), (cx + dirn * 4 * SS, cy + 9 * SS),
               (cx + dirn * 4 * SS, cy + 20 * SS)]
        d.polygon(pts, fill=col, outline=BLACK)
        d.rectangle((64 * k * SS, 0, (64 * k + 63) * SS, 55 * SS), outline=(120, 120, 120), width=SS)


def draw_box_text(d):
    d.rectangle((0, 0, 384 * SS, 64 * SS), fill=DARK)
    d.rectangle((3 * SS, 3 * SS, 381 * SS, 61 * SS), outline=ORANGE, width=3 * SS)
    text_left(d, 20 * SS, 26 * SS, "SERVIS / NÁŘADÍ", font(32, cond=True), ORANGE)
    text_left(d, 22 * SS, 52 * SS, "nářadí a kanystry", font(15, bold=False, cond=True), WHITE)
    for k in range(3):
        d.line((318 * SS + k * 18 * SS, 54 * SS, 336 * SS + k * 18 * SS, 10 * SS), fill=ORANGE, width=6 * SS)


def draw_box_conc(d):
    d.rectangle((0, 0, 350 * SS, 68 * SS), fill=YELLOW)
    d.rectangle((3 * SS, 3 * SS, 347 * SS, 65 * SS), outline=BLACK, width=4 * SS)
    d.rounded_rectangle((16 * SS, 20 * SS, 52 * SS, 58 * SS), 5 * SS, fill=BLACK)
    d.rounded_rectangle((22 * SS, 10 * SS, 40 * SS, 22 * SS), 3 * SS, outline=BLACK, width=3 * SS)
    d.rectangle((22 * SS, 28 * SS, 46 * SS, 40 * SS), fill=YELLOW)
    text_left(d, 68 * SS, 24 * SS, "KANYSTRY", font(32, cond=True), BLACK)
    text_left(d, 68 * SS, 52 * SS, "20 l / ks", font(22, cond=True), BLACK)


def draw_box_warn(d):
    d.rectangle((0, 0, 128 * SS, 128 * SS), fill=YELLOW)
    d.rectangle((3 * SS, 3 * SS, 125 * SS, 125 * SS), outline=BLACK, width=4 * SS)
    cx = 64 * SS
    d.polygon([(cx, 12 * SS), (cx + 46 * SS, 88 * SS), (cx - 46 * SS, 88 * SS)], fill=WHITE)
    d.line((cx, 12 * SS, cx + 46 * SS, 88 * SS, cx - 46 * SS, 88 * SS, cx, 12 * SS), fill=RED, width=6 * SS)
    d.ellipse((cx - 6 * SS, 40 * SS, cx + 6 * SS, 52 * SS), fill=BLACK)
    d.line((cx, 52 * SS, cx + 2 * SS, 68 * SS), fill=BLACK, width=6 * SS)
    d.line((cx + 2 * SS, 68 * SS, cx - 9 * SS, 82 * SS), fill=BLACK, width=5 * SS)
    d.line((cx + 2 * SS, 68 * SS, cx + 12 * SS, 82 * SS), fill=BLACK, width=5 * SS)
    d.line((cx, 56 * SS, cx - 12 * SS, 64 * SS), fill=BLACK, width=4 * SS)
    d.line((cx, 56 * SS, cx + 12 * SS, 62 * SS), fill=BLACK, width=4 * SS)
    text_center(d, 64 * SS, 108 * SS, "NESTOUPAT", font(17, cond=True), BLACK)


def main():
    img = Image.new("RGB", (L.ATLAS_SIZE * SS, L.ATLAS_SIZE * SS), WHITE)
    d = ImageDraw.Draw(img)
    draw_stripe(d)
    draw_side_text(d)
    for key in "SML":
        draw_battery(d, key)
        draw_drone(d, key)
    draw_screen(d)
    draw_charger_label(d)
    draw_diesel(d)
    draw_led(d)
    draw_gen_panel(d)
    draw_gen_warn(d)
    draw_gen_plate(d)
    draw_gen_gauge(d)
    for size in L.TANK_SIZES + (L.PAD_TANK_LITERS,):
        draw_tank_vol(d, size)
    draw_tank_text(d)
    draw_tank_plate(d)
    draw_tank_arrow(d)
    draw_tank_outlet(d)
    draw_tank_warn(d)
    paste_canvas(img, "concLabel", 260, 200, draw_conc_label)
    draw_conc_nums(img)
    paste_canvas(img, "mixPlate", 208, 56, draw_mix_plate)
    paste_canvas(img, "mixArrow", 128, 56, draw_mix_arrows)
    paste_canvas(img, "boxText", 384, 64, draw_box_text)
    paste_canvas(img, "boxConc", 350, 68, draw_box_conc)
    paste_canvas(img, "boxWarn", 128, 128, draw_box_warn)
    draw_side_text_count(img, 8)
    paste_canvas(img, "canisterLabel", 336, 168, draw_canister_label, with_tile=True)
    img = img.resize((L.ATLAS_SIZE, L.ATLAS_SIZE), Image.LANCZOS)
    os.makedirs(os.path.dirname(SRC_PNG), exist_ok=True)
    os.makedirs(os.path.dirname(DDS), exist_ok=True)
    img.save(SRC_PNG)
    n = png2dds.convert(SRC_PNG, DDS, "dxt1")
    print(f"{SRC_PNG}\n{DDS} ({n} úrovní, {os.path.getsize(DDS):,} B)")


if __name__ == "__main__":
    main()
