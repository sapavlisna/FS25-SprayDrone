"""Rozvržení atlasu nápisů a nálepek malého vleku (textures/sdt_decals.dds, 1024 x 1024).

Oblasti jsou v pixelech (x, y, šířka, výška) od levého horního rohu. Kreslí je tools/make_decal_atlas.py
(Pillow), build_trailer_middle.py z nich počítá UV. Bez bpy, ať jde načíst z obou.
"""

ATLAS_SIZE = 1024
ATLAS_PNG = "sdt_decals.png"
ATLAS_DDS = "sdt_decals.dds"

REGIONS = {
    "stripe": (0, 0, 1024, 64),
    "sideText": (0, 64, 1024, 64),
    "batteryS": (0, 128, 256, 72),
    "batteryM": (256, 128, 256, 72),
    "batteryL": (512, 128, 256, 72),
    "chargerScreen": (768, 128, 256, 176),
    "chargerLabel": (0, 320, 512, 128),
    "dieselLabel": (512, 320, 192, 128),
    "led": (720, 320, 32, 32),
    "droneS": (0, 464, 256, 64),
    "droneM": (256, 464, 256, 64),
    "droneL": (512, 464, 256, 64),
    "genPanel": (0, 544, 480, 280),
    "genWarn": (512, 544, 384, 112),
    "genPlate": (512, 672, 256, 160),
    "genGauge": (784, 672, 64, 256),
    "tankVol3000": (0, 200, 192, 120),
    "tankVol800": (192, 200, 192, 120),
    "tankVol1000": (384, 200, 192, 120),
    "tankVol1500": (576, 200, 192, 120),
    "tankVol5000": (0, 832, 192, 120),
    "tankPlate": (768, 320, 256, 160),          # 2 x 2 štítky 128 x 80: 3000, 800 / 1000, 1500
    "tankPlate5000": (192, 832, 128, 80),
    "tankVol300": (320, 832, 192, 120),          # nádrž malého vleku (build_trailer_mini.py)
    "tankPlate300": (512, 832, 128, 80),
    "tankArrow": (768, 484, 256, 56),
    "tankText": (0, 960, 512, 64),
    "tankOutlet": (512, 960, 256, 56),
    "tankWarn": (848, 672, 176, 176),
    "concLabel": (848, 848, 176, 80),          # štítek koncentrátové nádrže 0,13 x 0,10 m (kreslí se v poměru 1,3 : 1)
    "concNums": (640, 832, 120, 48),           # 3 x 2 dlaždice 40 x 24 s čísly stupnice: 10, 20, 30, 40, 50 l
    "mixPlate": (640, 884, 128, 34),           # výrobní štítek mixéru 0,104 x 0,028 m
    "mixArrow": (640, 922, 128, 28),           # šipky toku na komoře: voda (vlevo dlaždice), koncentrát (vpravo)
    "boxText": (768, 928, 256, 42),            # víko bedny: SERVIS / NÁŘADÍ
    "boxConc": (768, 972, 256, 52),            # víko bedny: KANYSTRY (obecně, bez vazby na obsah) - 12 x 20 l
    "boxWarn": (896, 544, 128, 128),           # víko bedny: výstražný trojúhelník Nestoupat
    "sideText8": (192, 912, 128, 32),          # pravá čtvrtina sideText (od SIDE_TEXT_SPLIT) s nápisem 8 × 52 V, poloviční rozlišení
    "canisterLabel": (512, 912, 128, 48),      # neutrální štítek kanystru v bedně BZUK 20 l (0,168 x 0,084 m, kreslí se 2 : 1)
}

# nápis na boku horní plošiny: sideText končí počtem baterií vleku Middle (5 × 52 V) za tímto podílem šířky; vlek s jiným počtem
# (sideText<počet>) skládá nápis z levé části sideText a oblasti sideText<počet> (build_trailer_middle.build_decals)
SIDE_TEXT_SPLIT = 0.75

# hlavní nádrž (sdt_bigtank.py): objem l -> (poloměr, délka celkem s dny) v m; dna jsou elipsoidy hloubky HEAD_K * poloměr
TANK_GEOM = {800: (0.46, 1.32), 1000: (0.50, 1.40), 1500: (0.58, 1.55)}
TANK_HEAD_K = 0.40
# hranaté PE nádrže (3000, 5000 l): objem l -> (šířka, výška, délka) v m. Kulatá nádrž takového objemu se pod horní plošinu
# a před zadní bednu nevejde; 5000 l zabírá všechno volné místo (geometricky ~4000 l)
BOX_GEOM = {3000: (1.76, 1.26, 1.40), 5000: (1.84, 1.34, 1.62)}
TANK_SIZES = (800, 1000, 1500, 3000, 5000)
PAD_TANK_LITERS = 300                      # hranatá nádrž pod dronem na malém vleku (štítky ve vlastních oblastech atlasu)

# ovládací panel elektrocentrály: nálepka genPanel má 1 px = 1 mm; polohy prvků v metrech od levého dolního rohu panelu
# (pohled zvenku, vpravo = dozadu vleku). Podle nich kreslí legendy tools/make_decal_atlas.py a staví prvky sdt_generator.py.
GEN_PANEL_SIZE = (0.48, 0.28)
GEN_PANEL = {
    "volt": (0.090, 0.215), "hours": (0.235, 0.220),
    "ledRun": (0.335, 0.225), "ledOil": (0.385, 0.225), "ledTemp": (0.435, 0.225),
    "key": (0.080, 0.105), "preheat": (0.080, 0.035),
    "socket": (0.240, 0.130), "rocker": (0.240, 0.035),
    "mcb": (0.395, 0.115), "earth": (0.435, 0.035),
}

# texty na nálepkách: kapacity podle build_drone.SPECS / docs/DRON.md
BATTERY_TEXT = {"S": ("S", "0,81 kWh"), "M": ("M", "1,57 kWh"), "L": ("L", "2,13 kWh")}
DRONE_TEXT = {"S": "BZ-S", "M": "BZ-M", "L": "BZ-L"}


def uv_rect(name, sub=None):
    """(u0, v0, u1, v1) oblasti v UV (v odspodu). sub = (fx0, fy0, fx1, fy1) výřez oblasti v podílech."""
    x, y, w, h = REGIONS[name]
    fx0, fy0, fx1, fy1 = sub or (0.0, 0.0, 1.0, 1.0)
    s = float(ATLAS_SIZE)
    inset = 0.5
    u0 = (x + inset + (w - 2 * inset) * fx0) / s
    u1 = (x + inset + (w - 2 * inset) * fx1) / s
    v1 = 1.0 - (y + inset + (h - 2 * inset) * fy0) / s
    v0 = 1.0 - (y + inset + (h - 2 * inset) * fy1) / s
    return u0, v0, u1, v1


CONC_NUMS_SUB = [(c / 3, r / 2, (c + 1) / 3, (r + 1) / 2) for r in range(2) for c in range(3)]
MIX_ARROW_SUB = ((0.0, 0.0, 0.5, 1.0), (0.5, 0.0, 1.0, 1.0))
TANK_PLATE_SUB = {3000: (0.0, 0.0, 0.5, 0.5), 800: (0.5, 0.0, 1.0, 0.5), 1000: (0.0, 0.5, 0.5, 1.0), 1500: (0.5, 0.5, 1.0, 1.0)}
TANK_WARN_SUB = ((0.0, 0.0, 0.5, 0.5), (0.5, 0.0, 1.0, 0.5), (0.0, 0.5, 0.5, 1.0), (0.5, 0.5, 1.0, 1.0))
