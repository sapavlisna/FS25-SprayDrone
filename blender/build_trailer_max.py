"""Velký tandemový servisní vlek se dvěma drony: nahoře dvě přistávací plochy (vpředu a vzadu), drony nosem ke středu paluby
(přední nosem dozadu, zadní nosem dopředu), uprostřed nabíječka baterií na levém okraji (víko se vyklápí ven přes okraj) a dva
navíječe hadic zapuštěné v kapsách desky (každý dron má svůj, na straně paluby, kde má plnicí hrdlo); dole dvě hlavní nádrže za sebou, elektrocentrála,
mixér a skříň na kanystry.

Skládá se z build_trailer_middle.py (jeden dron, vlek za auto): ten se spustí do stejného jmenného prostoru, přepíšou se rozměry
a funkce, které se u velkého vleku liší. Nádrž, centrála, čerpadlo, mixér a skříň na kanystry zůstávají stejné; vlastní je
horní deska prodloužená nad centrály, rolovací plachty s polepy designu, teleskopický žebřík, skříňka relé tyčí a záď.
Osa: spojka vpředu na -Y, +X vlevo. Počátek = zem, střed šířky.

    TOP_Y0 ... pad A (dron nosem dozadu) ... | střed: navíječ A vlevo, nabíječka vlevo, navíječ B vpravo | ... pad B (nosem
    dopředu) ... TOP_Y1

Spuštění v Blenderu:
    p = r"...\\\\build_trailer_max.py"; exec(open(p, encoding="utf-8").read(), {"__file__": p, "__name__": "__main__"})
Bez okna: viz headless_max.py.
"""

import inspect
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_big = os.path.join(_HERE, "build_trailer_middle.py")
_source = open(_big, encoding="utf-8").read()
# nabíječka má v původním skriptu tři řady buněk, tady jich je víc
_source = _source.replace("for i in range(2) for j in range(3)}", "for i in range(2) for j in range(len(CHARGER_CELL_Y))}")
# lůžko baterie a plnicí hrdlo dronu mají polohu po Y vzhledem ke středu plochy (u velkého vleku je střed v y = 0)
_source = _source.replace("    bx, by = DRONE_BATTERY[key]\n", "    bx, by = DRONE_BATTERY[key][0], DRONE_BATTERY[key][1] + DRONE_Y\n")
_source = _source.replace("    px, py = DRONE_FILL_PORT[key]\n", "    px, py = DRONE_FILL_PORT[key][0], DRONE_FILL_PORT[key][1] + DRONE_Y\n")
assert "DRONE_BATTERY[key][1] + DRONE_Y" in _source and "DRONE_FILL_PORT[key][1] + DRONE_Y" in _source
# otvor v horní desce pro truhlu nabíječky je jiný než truhla (ta je otočená o 90° a stojí u okraje)
assert "    ox0, ox1, oy0, oy1, _ = chest_box()\n" in _source
_source = _source.replace("    ox0, ox1, oy0, oy1, _ = chest_box()\n", "    ox0, ox1, oy0, oy1, _ = chest_cutout()\n")
_source = _source.replace("REAR_CROSS_OFFSET = 0.14", "REAR_CROSS_OFFSET = 0.04")
exec(compile(_source, _big, "exec"), globals())

# ---------------------------------------------------------------------------------------------------------- konstanty
V = T.V

COLLECTION_NAME = "SprayDroneTrailerMax"
PREVIEW_COLLECTION = "SprayDroneTrailerMax_Preview"
COMPONENT_NAME = "sprayDroneTrailerMax_main_component1"
ROOT_NAME = "sprayDroneTrailerMax_vis"

# výšky: paluba je výš kvůli velkým kolům (385/65 R22,5, vnější průměr 1,07 m); horní plošina o stejný kus výš
_DZ = 0.28
DECK_TOP = 0.72 + _DZ
RAIL_H = 0.24
IBEAM_H = 0.22
IBEAM_X = 0.45
TOP_SURF = 2.50 + _DZ
POST_TOP = TOP_SURF - TOP_PLATE - TOP_BEAM_H
LADDER_HINGE_Z = POST_TOP - LADDER_HINGE_DROP
HOSE_Z = TOP_SURF + HOSE_R + 0.006
for _m in (T, BT):
    _m.MAIN_DRAIN.z = DECK_TOP + 0.2825       # výpust hlavní nádrže se zvedá s palubou (sdt_contract je sdílený objekt)
SL.CONC_TICK_Z = {k: v + _DZ for k, v in SL.CONC_TICK_Z.items()}      # čísla stupnice indukční nádrže (výška nad zemí)

TIRE_DIMENSIONS = "385_65R22_5"
WHEEL_R = (22.5 * 0.0254 + 2 * 0.385 * 0.65) / 2
WHEEL_W = 0.385
# jediná pneu bez výběru (Pavel 2026-10-13): silniční Conti Hybrid HD3 s bloky na běhounu (HT3 je hladká návěsová) a vlastní
# disk sdtRim22 (sdt_rims.py, export_rims.py); yOffset = rozdíl poloměru proti dřívější výchozí HT3 (0,53), jako dřív u HD3
TIRE_FILE = "$data/shared/wheels/tires/continental/contiHybridHD3/315_80R22_5.xml"
TIRE_Y_OFFSET = 0.01
RIM_KIND, RIM_FILE, RIM_WIDTH_DIAM = "R22", "wheels/sdtRim22.i3d", "9 22.5"
# saveId kol, která můžou být v uložených hrách: dynamická výchozí z dřívějšího rozměru a dřívější volby značky
LEGACY_WHEEL_IDS = ("DEFAULT_CONTINENTAL_contiHybridHT3", "DEFAULT_CONTINENTAL_contiCrossTracHS3",
                    "CONTINENTAL_CROSSTRACHD3_295_80R22_5", "CONTINENTAL_HYBRIDHD3_315_80R22_5",
                    "CONTINENTAL_CROSSTRACHS3_385_65R22_5", "CONTINENTAL_CROSSTRACHS3_315_80R22_5",
                    "CONTINENTAL_OFFROADHDO_315_80R22_5")
TRACK_X = 1.27                               # kola vně rámu (lem paluby je na x 1,05), nad nimi blatníky
RIM_R = 22.5 * 0.0254 / 2
AXLE_Y = [2.95, 4.40]                        # tandem kousek za těžištěm plných nádrží (kladná váha na oji ~4 %); o 0,4 m dozadu s delšími nádržemi

BASE_Y0 = -1.85                              # vpředu je volná přední paluba pro dvě elektrocentrály (před horní plošinou, kanystry se do nich lijí shora)
BASE_Y1 = 6.50                               # za zadní nádrží zbývá místo před skříní na kanystry
BASE_LEN = BASE_Y1 - BASE_Y0
TOP_Y0 = -1.25                               # horní plošina a pád A zůstávají, kde byly (nabíječka a navíječe jsou nad mezerou mezi nádržemi)
TOP_Y1 = BASE_Y1 + 0.20
POST_Y = [-0.98, 1.10, 2.70, 4.40, BASE_Y1 - 0.07]

# sklopný žebřík (build_ladder z build_trailer_middle.py): vpravo na boku mezi předními sloupky, před předním blatníkem tandemu
# (ten začíná v y 2,31, rozložený žebřík visí z čepu svisle dolů v y 1,56 až 1,94); složený leží od čepu dopředu (-Y) podél boku
# těsně pod horní deskou (y -0,6 až 1,75)
LADDER_HINGE_Y = 1.75
LADDER_FOLD_DIR = -1.0
SIDE_MARKER_R_Y = BASE_Y1 - 0.12
EXIT_POINT = (BASE_W / 2 + 1.6, TOP_Y1 - 1.0, 0.0)   # hráč vystupuje vlevo vzadu, žebřík je vpravo

# oj podle vanilla Farmtech DPW 1800 (dpw1800.i3d, drawbar): plochý A-rám z ocelových pásnic, který se z kořene (šířka 1,04 m) sbíhá
# do krátké hlavy s tažným okem, tři příčky, bez předních kol a otočné nápravy (pevná). Délka od čela rámu k oku 2,0 m jako u DPW (1,95 m),
# oko i rám leží ve vodorovné rovině COUPLER_Z; tažná síla jde přes úchytky do čelního nosníku a podélníků.
DRAWBAR_LEN = 2.0
COUPLER_Y = BASE_Y0 - DRAWBAR_LEN
COUPLER_Z = 0.70
DRAWBAR_Z = COUPLER_Z
DRAWBAR_ROOT_X = 0.52                        # osa pásnice v kořeni (DPW 0,55)
DRAWBAR_TIP_X = 0.035                        # osa pásnice v místě, kde se sbíhají do hlavy
DRAWBAR_BEAM_W = 0.075
DRAWBAR_BEAM_H = 0.075
DRAWBAR_CONVERGE = 0.50                      # sbíhání končí takhle před okem (DPW 0,49)
JOCKEY_X, JOCKEY_Y = 0.0, COUPLER_Y + 1.35
JOCKEY_COL = (0.09, 0.16, 0.30)

# dvě hlavní kulaté nádrže za sebou (3000 nebo 5000 l, podle konfigurace), mezi nimi mixér s indukční nádrží; elektrocentrály (1 nebo 2,
# konfigurace v obchodě) stojí vpředu na přední palubě, napájecí kabel mají napevno v zadní stěně a vedou ho k nabíječce
CHEST_Y = 2.47                               # střed truhly nabíječky, navíječů a mezery mezi nádržemi (střed horní plošiny)
TANK_SQUASH = 0.92                           # válec je o 8 % nižší, aby výtlačná hadice k navíječům vedla pod horní deskou nad nádrží
TANK_GAP = 1.34                              # mezera mezi nádržemi: mixér s indukční nádrží a čerpadlem
TANK_A_END = CHEST_Y - TANK_GAP / 2          # zadní konec přední nádrže (její čelo se mění s velikostí)
TANK_B_Y_FRONT = CHEST_Y + TANK_GAP / 2      # čelo zadní nádrže (z něj jde sání čerpadla)
ROUND_TANKS = {3000: (0.68, 1.95), 5000: (0.74, 2.45)}    # poloměr a délka válcových nádrží (objem tvaru je ~85 % jmenovitého)
TANK_DRAIN_OFFSET = 0.121                    # výpust (konec příruby) za čelem nádrže, dno je kulaté
GEN_X, GEN_Y = 0.50, -1.28                    # střed levé centrály (druhá je zrcadlově vpravo)
GEN_SOCKET_DZ = 0.43
# čerpadlo s mixérem a indukční nádrž stojí vpravo mezi nádržemi (o odstup nádrže B před jejím čelem jako dřív před nádrží A), výpust zadní nádrže B jim je nejblíž
_GAP_SHIFT = TANK_B_Y_FRONT - BT.MAIN_TANK_Y_FRONT
T.PUMP_XY = (T.PUMP_XY[0], T.PUMP_XY[1] + _GAP_SHIFT)
T.INDUCTION_XY = (T.INDUCTION_XY[0], T.INDUCTION_XY[1] + _GAP_SHIFT)
TANK_SIZES_MAX = (3000, 5000)
BT.L.TANK_GEOM.update(ROUND_TANKS)
BT.LAYOUT.update({3000: (0.40, 0.55), 5000: (0.46, 0.64)})


def tank_extent(size):
    """(poloměr, délka, výška horní hrany nad palubou) válcové nádrže."""
    r, ln = ROUND_TANKS[size]
    return r, ln, BT.GAP + 2 * r * TANK_SQUASH


def tank_front(size, suffix):
    return TANK_B_Y_FRONT if suffix else TANK_A_END - ROUND_TANKS[size][1]


BT.tank_envelope = tank_extent
TANK_R, TANK_LEN, TANK_TOP = tank_extent(max(TANK_SIZES_MAX))
# skříň na kanystry je stejná jako u Middle (dvě řady po šesti, čtyři patra až ke stropu, rolovací vrata) a stojí na samém
# konci vleku (cabinet_y_range z build_trailer_middle.py, BASE_Y1 je tady vlastní) - Pavel 2026-10-09.

# dvě přistávací plochy: dron A vpředu, dron B vzadu; paluba mezi nimi je servisní zóna. Pády se počítají od TOP_Y0, i když
# horní deska je prodloužená dopředu až přes centrály (TOP_FRONT_Y, Pavel 2026-10-15: náhled tmp/plachta/plachta3_shots.py)
PAD_Y = (TOP_Y0 + 1.15, TOP_Y1 - 1.15)
TOP_FRONT_Y = -1.90                          # přední hrana prodloužené desky (čelní nosník rámu -1,85, výfuky centrál -1,816)
POST_FRONT_Y = BASE_Y0 + POST / 2            # přední sloupky Post_LF/RF stojí na čelním nosníku

# rolovací plachta na bocích a vpředu (sdt_parts.tarp): vně sloupků, od nové přední hrany po zadní líc Post_L4/R4, nad
# blatníky tandemu sedí na jejich horní ploše (_side_bottom); srolovaná role je pod horní hranou (foldLadder 2,6-3,0 s, čas 0 = rozloženo = srolováno)
TARP_X = 1.105
TARP_FRONT_Y = TOP_FRONT_Y + 0.015
TARP_Y = (TARP_FRONT_Y, POST_Y[-1] + POST / 2)
TARP_TOP = POST_TOP
TARP_BOTTOM = 0.95                           # lem přes vnější líc lišty paluby
TARP_STRIPE_Z = (1.26, 1.38)
TARP_ROLL_GAP = 0.02                         # role pod vodicí lištou (lišta z 2,595-2,62)
TARP_STRAP_TOP = TARP_STRIPE_Z[1] + 0.14     # popruhy jen dole (nad pruh), lockupy designu začínají nad nimi
SERVICE_Y = (PAD_Y[0] + PAD_Y[1]) / 2
DRONE_Y = PAD_Y[0]
DRONE_VARIANTS_B = {"S": "Drone2_S_", "M": "Drone2_A_", "L": "Drone2_L_"}
CLAMP_Y = (DRONE_Y - 0.075, DRONE_Y + 0.075)

# nabíječka: deset šachet (5 řad po dvou; pátá řada byla do 2026-10-15 ovládací panel a výplň). Staví se v základní poloze (řady
# po Y, víko na přední straně) kolem počátku a pak se otočí o 90° a posune k levému okraji paluby, víko se otevírá ven přes okraj
BATTERY_COUNT = 10
CHARGER_CELL_X = (0.35, 0.655)
CHARGER_CELL_Y = tuple((k - 2) * 0.19 for k in range(5))
CHARGER_SLOTS = [(i, j) for j in range(5) for i in range(2)]
CHARGER_SOCKET_Y = CHARGER_CELL_Y[0]
CHEST_OPEN_DEG = 120                         # víko přejde za svislici ven přes okraj paluby
CHEST_ROT = math.pi / 2
CHEST_EDGE_X = 0.945                         # vnější stěna truhly u levého okraje paluby (lem je na x 1,05)


def _chest_matrix():
    """Základní poloha truhly -> poloha na paluze: otočení o 90° kolem svislé osy, vnější (přední) stěna u levého okraje."""
    ox0, ox1, oy0, oy1, _ = chest_box()
    cxc, cyc = (ox0 + ox1) / 2, (oy0 + oy1) / 2
    lc = oy1 - oy0
    tx = CHEST_EDGE_X - lc / 2
    return Matrix.Translation((tx, CHEST_Y, 0)) @ Matrix.Rotation(CHEST_ROT, 4, "Z") @ Matrix.Translation((-cxc, -cyc, 0))


def chest_cutout():
    """Otvor v horní desce: x0, x1, y0, y1 truhly po otočení (poslední hodnota se nepoužívá)."""
    ox0, ox1, oy0, oy1, zw = chest_box()
    m = _chest_matrix()
    pts = [m @ Vector((x, y, 0)) for x in (ox0, ox1) for y in (oy0, oy1)]
    return min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts), zw


CAMERA_TARGET = (0.0, SERVICE_Y, TOP_SURF + 1.0)
LIGHT_NODES = [
    ("rearLight52_left", (0.86, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("rearLight52_right", (-0.86, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("plateNumberLight03", (0.0, BASE_Y1 + 0.005, DECK_TOP - RAIL_H - 0.005), (-90, 0, -90)),
    ("sideMarker05_left", (BASE_W / 2 + 0.003, BASE_Y1 - 0.12, DECK_TOP - RAIL_H + 0.09), (0, 0, -90)),
    ("sideMarker05_right", (-BASE_W / 2 - 0.003, SIDE_MARKER_R_Y, DECK_TOP - RAIL_H + 0.09), (0, 0, 90)),
]


def drone_spec(prefix):
    for variants in (DRONE_VARIANTS, DRONE_VARIANTS_B):
        for key, p in variants.items():
            if p == prefix:
                return key.rstrip("2"), D.SPECS[key.rstrip("2")]
    raise KeyError(prefix)


def _rename_new(before, suffix):
    """Přejmenuje objekty vzniklé od snímku before (množina jmen) tak, aby měly příponu suffix místo Blenderova .001."""
    for o in [o for o in bpy.data.objects if o.name not in before]:
        base = o.name.rsplit(".", 1)[0] if o.name[-4:-3] == "." and o.name[-3:].isdigit() else o.name
        o.name = base + suffix


def _transform_new(before, matrix):
    """Posune a otočí nově vzniklé objekty (jen kořenové, jejich děti jedou s nimi)."""
    for o in [o for o in bpy.data.objects if o.name not in before]:
        if o.parent is None or o.parent.name in before:
            o.matrix_world = matrix @ o.matrix_world
    bpy.context.view_layer.update()


# --------------------------------------------------------------------------------------------------------- podvozek
_big_build_chassis = build_chassis
LEAF_X = 0.62
LEAF_HALF = 0.36
FENDER_X = (TRACK_X - WHEEL_W / 2 - 0.02, TRACK_X + WHEEL_W / 2 + 0.035)
FENDER_R = WHEEL_R + 0.10
TARP_FENDER_GAP = 0.006                      # boční plachta nad blatníkem kopíruje jeho horní plochu (vrchol z 1,186) s touto vůlí


def _arc_shell(name, x0, x1, cy, cz, r_in, r_out, a0, a1, mat, n=28):
    """Výseč mezikruží (osa X): profil x0..x1 krát r_in..r_out vytažený po oblouku a0..a1 v rovině YZ (úhel od +Y směrem k +Z)."""
    bm = bmesh.new()
    rings = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((x, cy + r * c, cz + r * s)) for x, r in ((x0, r_in), (x1, r_in), (x1, r_out), (x0, r_out))])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(4):
            bm.faces.new((r0[i], r0[(i + 1) % 4], r1[(i + 1) % 4], r1[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return P._finish(name, bm, Matrix.Identity(4), mat)


def build_suspension():
    """Listové pružení každé nápravy: hranatá náprava, na každé straně uvnitř kola svazek šesti listů (nejdelší nahoře, oka a
    třmeny na koncích, úchyty k palubě), třmenové šrouby a brzdový buben."""
    for name in [o.name for o in bpy.data.objects if o.name.startswith(("Axle_", "SwingArm_", "Hanger_"))]:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    frame, steel = "SDT_Frame", "SDT_Steel"
    axle_h = 0.075
    axle_top = WHEEL_R + axle_h
    leaf_t, leaf_gap, rise = 0.014, 0.014, 0.10
    z_main = axle_top + 5 * leaf_gap + leaf_t
    z_below = DECK_TOP - DECK_PLATE
    for n, ay in enumerate(AXLE_Y, 1):
        box(f"Axle_{n}", -TRACK_X + 0.05, TRACK_X - 0.05, ay - axle_h, ay + axle_h, WHEEL_R - axle_h, axle_top, frame)
        for side, sx in (("L", 1), ("R", -1)):
            xs = sx * LEAF_X
            tag = f"{n}{side}"
            for k, half in enumerate((LEAF_HALF, 0.31, 0.26, 0.21, 0.16, 0.11)):
                stations = []
                for i in range(9):
                    u = -1 + i / 4
                    y = ay + half * u
                    yy = (y - ay) / LEAF_HALF
                    top = z_main + rise * yy * yy - k * leaf_gap
                    stations.append((y, 0.045, top - leaf_t, top, 8))
                P.loft_y(f"Leaf_{tag}{k}", stations, steel, x=xs, segments=12)
            box(f"LeafSeat_{tag}", xs - 0.075, xs + 0.075, ay - 0.10, ay + 0.10, z_main, z_main + 0.020, frame)
            box(f"LeafClamp_{tag}", xs - 0.075, xs + 0.075, ay - 0.10, ay + 0.10, WHEEL_R - axle_h - 0.020, WHEEL_R - axle_h, frame)
            for dy in (-0.065, 0.065):
                for dx in (-0.055, 0.055):
                    tube(f"UBolt_{tag}{dx:+.2f}{dy:+.2f}", (xs + dx, ay + dy, WHEEL_R - axle_h - 0.04),
                         (xs + dx, ay + dy, z_main + 0.05), 0.010, steel, segments=8)
            for e in (-1, 1):
                yc = ay + e * LEAF_HALF
                eye_z = z_main + rise
                tube(f"LeafEye_{tag}{e:+d}", (xs - 0.05, yc, eye_z - leaf_t / 2), (xs + 0.05, yc, eye_z - leaf_t / 2), 0.020,
                     steel, segments=12)
                for dx in (-0.062, 0.062):
                    box(f"LeafHanger_{tag}{e:+d}{dx:+.2f}", xs + dx - 0.006, xs + dx + 0.006, yc - 0.035, yc + 0.035,
                        eye_z - 0.025, z_below, frame)
            cylinder_x(f"BrakeDrum_{tag}", (sx * (TRACK_X - WHEEL_W / 2 - 0.045), ay, WHEEL_R), 0.20, 0.08, "SDT_CastIron",
                       segments=28)


def _revolve_x(name, profile, center, mat, seg=48, mirror=False):
    """Těleso otáčením uzavřeného profilu [(x, r)] kolem osy X (střed center); mirror obrátí profil v X (kolo na pravé straně)."""
    bm = bmesh.new()
    rings = []
    for x, r in profile:
        x = -x if mirror else x
        rings.append([bm.verts.new((x, r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)))
                      for i in range(seg)])
    for k in range(len(rings)):
        r0, r1 = rings[k], rings[(k + 1) % len(rings)]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return P._finish(name, bm, Matrix.Translation(center), mat)


def _tire_profile():
    """Pneu 385/65 R22,5 (Continental Hybrid HT3 z wheels.xml, poloměr 0,53, šířka 0,385): boky, rameno, čtyři podélné drážky."""
    r_rim, r_o = RIM_R, WHEEL_R
    side = [(0.150, r_rim + 0.004), (0.176, r_rim + 0.028), (0.1930, r_rim + 0.100), (0.1925, r_rim + 0.170),
            (0.178, r_rim + 0.222), (0.150, r_o - 0.016), (0.128, r_o - 0.004)]
    tread = [(0.112, r_o)]
    for g in (0.090, 0.030):
        tread += [(g + 0.014, r_o), (g + 0.010, r_o - 0.012), (g - 0.010, r_o - 0.012), (g - 0.014, r_o)]
    half = side + tread
    mirrored = [(-x, r) for x, r in reversed(half)]
    return half + [(0.0, r_o)] + mirrored


def build_wheel_previews():
    """Náhled kol (obrázek do obchodu, kontroly v Blenderu): pneu 385/65 R22,5 s drážkami a týž disk, jaký hra načte
    z wheels/sdtRim22.i3d (sdt_rims.build_rim)."""
    for o in [o for o in bpy.data.objects if o.name.startswith(("Wheel_", "Rim_", "HubCap_"))]:
        bpy.data.objects.remove(o, do_unlink=True)
    tire = _tire_profile()
    for i, ay in enumerate(AXLE_Y, 1):
        for side, sx in (("L", 1), ("R", -1)):
            c = Vector((sx * TRACK_X, ay, WHEEL_R))
            _revolve_x(f"Wheel_{i}{side}", tire, c, "SDT_Rubber", seg=72, mirror=sx < 0)
            rim = RIMS.build_rim(RIM_KIND, f"Rim_{i}{side}", sx)
            rim.matrix_world = Matrix.Translation(c)


def build_robust_frame():
    """Těžší rám: I-nosníky s pásnicemi místo plných, příčníky pod palubou mezi nápravami, ochrana proti podjetí vzadu."""
    frame = "SDT_Frame"
    zb = DECK_TOP - DECK_PLATE
    for name in ("IBeam_L", "IBeam_R"):
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    for side, sx in (("L", 1), ("R", -1)):
        x = sx * IBEAM_X
        box(f"Girder_{side}_Web", x - 0.018, x + 0.018, BASE_Y0, BASE_Y1, zb - IBEAM_H, zb, frame)
        box(f"Girder_{side}_TopFlange", x - 0.085, x + 0.085, BASE_Y0, BASE_Y1, zb - 0.025, zb, frame)
        box(f"Girder_{side}_BottomFlange", x - 0.085, x + 0.085, BASE_Y0, BASE_Y1, zb - IBEAM_H, zb - IBEAM_H + 0.028, frame)
    hw = BASE_W / 2 - RAIL_W
    for k, y in enumerate((-0.95, -0.35, 0.25, 0.85, 1.45, 1.95, 3.275, 4.60, 5.05, 5.40)):
        box(f"CrossMember_{k}", -hw, hw, y - 0.045, y + 0.045, zb - 0.15, zb, frame)
    uy = BASE_Y1 - 0.45
    for side, sx in (("L", 1), ("R", -1)):
        box(f"Underrun_Strut_{side}", sx * 0.80 - 0.035, sx * 0.80 + 0.035, uy - 0.045, uy + 0.045, 0.56, zb - 0.15, frame)
    tube("Underrun_Bar", (-0.95, uy, 0.60), (0.95, uy, 0.60), 0.045, frame, segments=8)
    for k, sx in enumerate((-1, 1)):
        box(f"Underrun_Reflector{k}", sx * 0.50 - 0.12, sx * 0.50 + 0.12, uy + 0.045, uy + 0.050, 0.575, 0.625, "SDT_PaintRed")


def build_fenders():
    """Souvislý tandemový blatník na každé straně: přední půlka oblouku nad předním kolem, rovný díl nad oběma koly a zadní
    půlka oblouku nad zadním kolem (mezi koly se nic nestáčí dolů), okrajová lišta a gumová zástěrka za zadním kolem."""
    frame = "SDT_Frame"
    a0, a1 = -0.30, math.pi + 0.30
    top = math.pi / 2
    zc = WHEEL_R
    for side, sx in (("L", 1), ("R", -1)):
        x0, x1 = sorted((sx * FENDER_X[0], sx * FENDER_X[1]))
        xo0, xo1 = (x1 - 0.014, x1) if sx > 0 else (x0, x0 + 0.014)
        # úhel od +Y (dozadu): přední kolo dostane oblouk od vrcholu dopředu dolů, zadní od vrcholu dozadu dolů
        for n, (ay, b0, b1) in enumerate(((AXLE_Y[0], top, a1), (AXLE_Y[-1], a0, top)), 1):
            _arc_shell(f"Fender_{side}{n}", x0, x1, ay, zc, FENDER_R, FENDER_R + 0.014, b0, b1, frame, n=16)
            _arc_shell(f"FenderLip_{side}{n}", xo0, xo1, ay, zc, FENDER_R - 0.030, FENDER_R + 0.014, b0, b1, frame, n=16)
        # vnitřní stěna blatníku: plech na vnitřní straně kol podle obrysu blatníku až ke spojnici konců oblouků, aby přes
        # podběh nebyl vidět vlek
        steps = 12
        outline = [(AXLE_Y[0] + FENDER_R * math.cos(a), zc + FENDER_R * math.sin(a))
                   for a in (a1 + (top - a1) * k / steps for k in range(steps + 1))]
        outline += [(AXLE_Y[-1] + FENDER_R * math.cos(a), zc + FENDER_R * math.sin(a))
                    for a in (top + (a0 - top) * k / steps for k in range(steps + 1))]
        xi = (x0 + 0.004) if sx > 0 else (x1 - 0.004)
        P.plate_yz(f"FenderInner_{side}", xi, 0.008, outline, frame)
        box(f"FenderBridge_{side}", x0, x1, AXLE_Y[0], AXLE_Y[1], zc + FENDER_R, zc + FENDER_R + 0.014, frame)
        box(f"FenderBridgeLip_{side}", xo0, xo1, AXLE_Y[0], AXLE_Y[1], zc + FENDER_R - 0.030, zc + FENDER_R + 0.014, frame)
        y_end = AXLE_Y[-1] + (FENDER_R + 0.007) * math.cos(a0)
        z_end = zc + (FENDER_R + 0.007) * math.sin(a0)
        box(f"MudFlap_{side}", x0 + 0.02, x1 - 0.02, y_end, y_end + 0.014, 0.12, z_end + 0.02, "SDT_Rubber")
        box(f"MudFlapBar_{side}", x0 + 0.02, x1 - 0.02, y_end - 0.012, y_end + 0.026, z_end - 0.030, z_end + 0.02, frame)
        for n, y in enumerate((AXLE_Y[0], (AXLE_Y[0] + AXLE_Y[1]) / 2, AXLE_Y[1])):
            xa = sx * (BASE_W / 2)
            box(f"FenderStay_{side}{n}", min(xa, sx * FENDER_X[0] + sx * 0.015), max(xa, sx * FENDER_X[0] + sx * 0.015),
                y - 0.03, y + 0.03, zc + FENDER_R - 0.05, zc + FENDER_R + 0.014, frame)


def build_chassis():
    _big_build_chassis()
    build_suspension()
    build_wheel_previews()
    build_robust_frame()
    build_fenders()


# ------------------------------------------------------------------------------------------------------------------ oj
def _flat_beam(name, p0, p1, w, z0, z1, mat):
    """Vodorovná hranatá pásnice šířky w mezi body p0 a p1 (x, y), ve výšce z0..z1; konce kolmé na osu."""
    a, b = Vector((p0[0], p0[1])), Vector((p1[0], p1[1]))
    d = (b - a).normalized()
    n = Vector((-d.y, d.x)) * (w / 2)
    quad = [a + n, b + n, b - n, a - n]
    bm = bmesh.new()
    lo = [bm.verts.new((q.x, q.y, z0)) for q in quad]
    hi = [bm.verts.new((q.x, q.y, z1)) for q in quad]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return P._finish(name, bm, Matrix.Identity(4), mat)


def drawbar_x(y):
    """Osa pásnice A-rámu (kladná strana) v místě y: přímka z kořene ke konci sbíhání."""
    y_root, y_conv = BASE_Y0 + 0.05, COUPLER_Y + DRAWBAR_CONVERGE
    t = (y - y_root) / (y_conv - y_root)
    return DRAWBAR_ROOT_X + t * (DRAWBAR_TIP_X - DRAWBAR_ROOT_X)


def _adopt(parent, objs):
    for o in objs:
        w = o.matrix_world.copy()
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = w


def _chain(name, p0, p1, sag, pitch=0.042, wire=0.0045):
    """Řetěz z oválných článků prověšený mezi p0 a p1 (parabola), články střídavě ve svislé a vodorovné rovině."""
    p0, p1 = Vector(p0), Vector(p1)
    path = [p0.lerp(p1, t) + Vector((0, 0, -4 * sag * t * (1 - t))) for t in (i / 40 for i in range(41))]
    pts = P.resample(path, max(int(P.path_length(path) / pitch), 2) + 1)
    links = []
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        d = (b - a).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized() if k % 2 == 0 else Vector((0, 0, 1)).cross(d).cross(d).normalized()
        c = (a + b) / 2
        half = (b - a).length / 2 + wire * 1.5
        ring = [c + d * half * math.cos(t) + side * 0.011 * math.sin(t) for t in (2 * math.pi * i / 14 for i in range(15))]
        links.append(P.sweep(f"{name}_L{k}", ring, wire, "SDT_Steel", segments=6))
    return P.merge(name, links)


def _coupling_head(name, pos, along, mat, hose_from=None):
    """Spojka vzduchové / elektrické hadice zaparkovaná v držáku: tělo spojky, víčko, kousek hadice k držáku."""
    pos, along = Vector(pos), Vector(along).normalized()
    parts = [tube(f"{name}_Body", pos - along * 0.030, pos + along * 0.022, 0.017, mat, segments=12),
             tube(f"{name}_Lip", pos + along * 0.022, pos + along * 0.030, 0.021, mat, segments=12),
             box(f"{name}_Palm", pos.x - 0.006, pos.x + 0.006, pos.y - 0.020, pos.y + 0.020, pos.z - 0.030, pos.z - 0.012,
                 mat)]
    if hose_from is not None:
        start = Vector(hose_from)
        mid = start.lerp(pos - along * 0.03, 0.5) + Vector((0, 0, -0.07))
        parts.append(P.sweep(f"{name}_Hose", P.hermite_path([tuple(start), tuple(mid), tuple(pos - along * 0.03)],
                                                            samples=8), 0.0085, "SDT_HoseBlack", segments=8))
    return P.merge(name, parts)


def build_drawbar_tractor(y_conv, z0, z1, extra=()):
    """Varianta za traktor / nákladní auto (konfigurace TRACTOR, skupina drawbarTractorSet): tažné oko na přírubě se čtyřmi
    šrouby, pojistný řetěz s hákem pod hlavou, držák vzduchových spojek (airIn červená, airOut žlutá) s vedením podél
    pravé pásnice. Uzly airIn / airOut jsou začátky hadic, které hra kreslí k tahači; *_detached jsou zaparkované spojky."""
    steel = "SDT_Steel"
    parts = []
    hy0 = COUPLER_Y + 0.07
    parts.append(P.ring_z("Drawbar_Eye", (0, COUPLER_Y, COUPLER_Z), 0.042, 0.078, 0.05, steel))
    parts.append(_flat_beam("Drawbar_EyeNeck", (0, hy0 + 0.02), (0, COUPLER_Y + 0.02), 0.06, COUPLER_Z - 0.025,
                            COUPLER_Z + 0.025, steel))
    for k, (fy0, fy1) in enumerate(((hy0 - 0.004, hy0 + 0.014), (hy0 + 0.018, hy0 + 0.036))):
        parts.append(box(f"Drawbar_EyeFlange{k}", -0.072, 0.072, fy0, fy1, COUPLER_Z - 0.062, COUPLER_Z + 0.062,
                         "SDT_CastIron" if k == 0 else "SDT_Frame"))
    for bx in (-0.050, 0.050):
        for bz in (-0.040, 0.040):
            c = Vector((bx, hy0, COUPLER_Z + bz))
            parts.append(tube(f"Drawbar_EyeBolt{bx:+.2f}{bz:+.2f}", c + Vector((0, -0.016, 0)), c + Vector((0, 0.05, 0)),
                              0.009, steel, segments=6))
            parts.append(tube(f"Drawbar_EyeNut{bx:+.2f}{bz:+.2f}", c + Vector((0, -0.024, 0)), c + Vector((0, -0.010, 0)),
                              0.015, steel, segments=6))

    lug = Vector((0, COUPLER_Y + 0.22, z0 - 0.012))
    hook = Vector((0, y_conv + 0.06, z0 - 0.012))
    parts.append(box("Drawbar_ChainLug", -0.012, 0.012, lug.y - 0.025, lug.y + 0.025, z0 - 0.035, z0, steel))
    parts.append(box("Drawbar_HookLug", -0.012, 0.012, hook.y - 0.025, hook.y + 0.025, z0 - 0.035, z0, steel))
    parts.append(_chain("Drawbar_Chain", lug + Vector((0, 0, -0.03)), hook + Vector((0, 0, -0.07)), 0.12))
    hook_path = [hook + Vector((0, 0, -0.02)), hook + Vector((0, 0, -0.07)), hook + Vector((0, -0.025, -0.10)),
                 hook + Vector((0, -0.045, -0.075)), hook + Vector((0, -0.040, -0.055))]
    parts.append(P.sweep("Drawbar_ChainHook", P.hermite_path([tuple(p) for p in hook_path], samples=6), 0.008, steel,
                         segments=8))

    by0, by1 = y_conv - 0.035, y_conv - 0.015
    top = z1 + 0.012
    parts.append(box("Drawbar_AirBracket", -0.115, -0.010, by0, by1, top, top + 0.110, "SDT_Frame"))
    parts.append(box("Drawbar_AirBracketFoot", -0.115, -0.010, by0, by1 + 0.06, top, top + 0.008, "SDT_Frame"))
    lines = []
    for tag, x, mat in (("airIn", -0.085, "SDT_PaintRed"), ("airOut", -0.040, "SDT_PaintYellow")):
        z = top + 0.075
        parts.append(tube(f"{tag}_Socket", (x, by0 - 0.028, z), (x, by1, z), 0.016, mat, segments=12))
        parts.append(tube(f"{tag}_SocketLid", (x, by0 - 0.034, z), (x, by0 - 0.028, z), 0.019, "SDT_Rubber", segments=12))
        empty(tag, (x, by0 - 0.034, z))
        _coupling_head(f"{tag}_detached", (x, by1 + 0.095, top + 0.040), (0, 1, 0), mat,
                       hose_from=(x, by1 + 0.005, top + 0.060))
        # vedení od čela rámu po horní hraně pravé pásnice k zadní straně držáku
        ys = [BASE_Y0 + 0.02, BASE_Y0 - 0.25, -1.9, -2.2, y_conv + 0.08]
        pts = [(-0.26 + (x + 0.06) * 0.3, BASE_Y0 + 0.02, DECK_TOP - DECK_PLATE - 0.20)]
        pts += [(-drawbar_x(y) + (x + 0.06) * 0.25 + 0.01, y, z1 + 0.012) for y in ys[1:-1]]
        pts += [(x, ys[-1], z1 + 0.014), (x, by1 + 0.002, z - 0.03)]
        lines.append(P.sweep(f"{tag}_Line", P.hermite_path(pts, samples=8), 0.0065, "SDT_HoseBlack", segments=8))
    parts += lines
    for k, y in enumerate((-1.55, -2.0)):
        bx = -drawbar_x(y)
        parts.append(box(f"Drawbar_LineClip{k}", bx - 0.035, bx + 0.035, y - 0.012, y + 0.012, z1, z1 + 0.026, steel))
    grp = empty("drawbarTractorSet", (0, 0, 0))
    _adopt(grp, parts + list(extra) + [bpy.data.objects[n] for n in ("airIn", "airOut", "airIn_detached", "airOut_detached")])
    return grp


def build_drawbar_car(y_conv, z1):
    """Varianta za auto / pickup (konfigurace CAR, skupina drawbarCarSet): kulová hlava s nájezdovou brzdou jako
    build_coupler z build_trailer_middle.py, rozměry vztažené k COUPLER_Y (Middle má spojku na y -3,55). Střed koule
    tažného zařízení = attacherJoint. Kabel 13pin je společný (build_electric)."""
    by, bz = COUPLER_Y, COUPLER_Z
    az = bz + 0.027
    parts = []
    parts.append(P.loft_y("Coupler_Head", [
        (by - 0.062, 0.020, bz + 0.015, bz + 0.050, 2.5), (by - 0.050, 0.036, bz, bz + 0.066, 3.0),
        (by - 0.020, 0.046, bz - 0.008, bz + 0.074, 3.5), (by + 0.030, 0.046, bz - 0.008, bz + 0.076, 3.5),
        (by + 0.060, 0.040, bz, bz + 0.066, 3.0), (by + 0.080, 0.030, bz + 0.005, bz + 0.050, 2.5)], "SDT_CastIron"))
    parts.append(tube("Coupler_Handle", (0, by - 0.045, bz + 0.072), (0, by + 0.12, bz + 0.107), 0.011, "SDT_CastIron",
                      segments=10))
    parts.append(tube("Coupler_HandleGrip", (0, by + 0.10, bz + 0.103), (0, by + 0.165, bz + 0.116), 0.016, "SDT_PaintRed",
                      segments=12))
    parts.append(cylinder_x("Coupler_WearRing", (0.047, by + 0.005, bz + 0.042), 0.012, 0.008, "SDT_Plastic", segments=16))
    parts.append(cylinder_x("Coupler_WearIndicator", (0.052, by + 0.005, bz + 0.042), 0.008, 0.006, "SDT_LedGreen",
                            segments=12))
    hy1 = by + 0.67
    parts.append(tube("Coupler_DrawTube", (0, by + 0.07, az), (0, by + 0.25, az), 0.025, "SDT_Steel", segments=14))
    pleats = []
    y0, y1, n = by + 0.095, by + 0.185, 8
    for k in range(2 * n + 1):
        r = 0.031 if k % 2 == 0 else 0.042
        pleats.append((y0 + (y1 - y0) * k / (2 * n), r, az - r, az + r, 2.0))
    parts.append(P.loft_y("Coupler_Bellows", pleats, "SDT_Rubber", segments=18))
    parts.append(P.loft_y("Coupler_Housing", [
        (y1, 0.046, az - 0.050, az + 0.050, 6.0), (y1 + 0.02, 0.052, az - 0.055, az + 0.055, 6.0),
        (hy1 - 0.07, 0.052, az - 0.058, az + 0.058, 6.0), (hy1, 0.044, az - 0.040, az + 0.040, 5.0)], "SDT_Steel"))
    for side, sx in (("L", 1), ("R", -1)):
        parts.append(box(f"Coupler_Flange_{side}", sx * 0.050, sx * 0.058, by + 0.29, by + 0.59, az - 0.07, az + 0.06,
                         "SDT_Steel"))
        for k, fy in enumerate((by + 0.35, by + 0.53)):
            parts.append(cylinder_x(f"Coupler_Bolt_{side}{k}", (sx * 0.062, fy, az), 0.011, 0.01, "SDT_Steel", segments=6))
    top = az + 0.058
    px, py = 0.0, by + 0.50
    parts.append(box("Coupler_BrakePivot", px - 0.022, px + 0.022, py - 0.03, py + 0.03, top - 0.005, top + 0.03,
                     "SDT_Steel"))
    lever_end = Vector((px, by + 0.77, top + 0.19))
    parts.append(tube("Coupler_BrakeLever", (px, py, top + 0.02), lever_end, 0.013, "SDT_Frame", segments=10))
    grip_dir = (lever_end - Vector((px, py, top + 0.02))).normalized()
    parts.append(tube("Coupler_BrakeGrip", lever_end - grip_dir * 0.03, lever_end + grip_dir * 0.07, 0.019, "SDT_Rubber",
                      segments=12))
    lever_mid = Vector((px, py, top + 0.02)).lerp(lever_end, 0.4)
    spring_foot = Vector((0.03, by + 0.31, az + 0.035))
    parts.append(tube("Coupler_GasSpring", spring_foot, spring_foot.lerp(lever_mid, 0.6), 0.011, "SDT_Frame", segments=10))
    parts.append(tube("Coupler_GasSpringRod", spring_foot.lerp(lever_mid, 0.6), lever_mid, 0.005, "SDT_Steel", segments=8))
    # táhlo brzdy po horní straně příček (pod nimi by procházelo pásnicemi) k čelu rámu
    # podpěrné kolečko (objímka a trubka) stojí v ose oje: táhlo ho obejde obloukem nad objímkou a vedle trubky
    jy = JOCKEY_Y
    rod = [(0, hy1 + 0.005, az - 0.01), (0, y_conv + 0.25, z1 + 0.018), (0, jy - 0.20, z1 + 0.018), (0.08, jy - 0.12, bz + 0.13),
           (0.08, jy + 0.12, bz + 0.13), (0, jy + 0.20, z1 + 0.018), (0, BASE_Y0 - 0.30, z1 + 0.018),
           (0, BASE_Y0 - 0.02, DECK_TOP - DECK_PLATE - 0.12)]
    parts.append(P.sweep("Coupler_BrakeRod", P.hermite_path(rod, samples=8), 0.008, "SDT_Steel", segments=8))
    cable = P.hermite_path([(0.024, py + 0.02, top + 0.02), (0.06, by + 0.48, az + 0.04), (0.075, by + 0.33, az - 0.04),
                            (0.07, by + 0.18, bz - 0.07), (0.045, by + 0.07, bz - 0.095), (0.035, by + 0.045, bz - 0.10)],
                           samples=10)
    parts.append(P.sweep("Coupler_BreakawayCable", cable, 0.0035, "SDT_Steel", segments=6))
    end = cable[-1]
    ring = [end + Vector((0, 0.018 * math.sin(a), -0.018 - 0.028 * math.cos(a)))
            for a in (2 * math.pi * k / 16 for k in range(17))]
    parts.append(P.sweep("Coupler_Carabiner", ring, 0.0035, "SDT_Steel", segments=6))
    grp = empty("drawbarCarSet", (0, 0, 0))
    _adopt(grp, parts)
    return grp


def build_electric(y_conv, z1):
    """Elektrická přípojka společná oběma variantám: kabel od zásuvky na čele rámu po levé pásnici k držáku na hlavě oje
    (uzel electric = začátek kabelu, který hra kreslí k tahači; electric_detached = zaparkovaná zástrčka v držáku)."""
    top = z1 + 0.012
    x = 0.090
    by0, by1 = y_conv - 0.035, y_conv - 0.015
    box("Drawbar_ElecBracket", x - 0.032, x + 0.032, by0, by1, top, top + 0.110, "SDT_Frame")
    box("Drawbar_ElecDock", 0.40, 0.46, BASE_Y0 - 0.005, BASE_Y0 + 0.001, DECK_TOP - 0.16, DECK_TOP - 0.08, "SDT_Plastic")
    z = top + 0.075
    tube("Drawbar_ElecSocket", (x, by0 - 0.026, z), (x, by1, z), 0.022, "SDT_Plastic", segments=14)
    tube("Drawbar_ElecSocketLid", (x, by0 - 0.032, z), (x, by0 - 0.026, z), 0.025, "SDT_ChargerGrey", segments=14)
    empty("electric", (x, by0 - 0.032, z))
    ys = [BASE_Y0 - 0.25, -1.9, -2.2]
    pts = [(0.43, BASE_Y0 + 0.001, DECK_TOP - 0.12)] + [(drawbar_x(y) - 0.012, y, z1 + 0.012) for y in ys]
    pts += [(x, y_conv + 0.08, z1 + 0.014), (x, by1 + 0.002, z - 0.03)]
    P.sweep("Drawbar_ElecCable", P.hermite_path(pts, samples=8), 0.006, "SDT_HoseBlack", segments=8)
    _coupling_head("electric_detached", (x, by1 + 0.095, top + 0.040), (0, 1, 0), "SDT_Plastic",
                   hose_from=(x, by1 + 0.005, top + 0.060))


def build_drawbar():
    """Pevná oj podle DPW 1800: dvě pásnice A-rámu z čela rámu, tři příčky, hlava (střed oka nebo koule = attacherJoint),
    podpěrné kolečko uprostřed (pohyblivá skupina jockeyWheel, kterou animace moveSupport zvedá). Spojka podle konfigurace
    v obchodě: tažné oko za traktor (drawbarTractorSet) nebo kulová hlava za auto (drawbarCarSet), elektrika je společná."""
    frame, steel = "SDT_Frame", "SDT_Steel"
    zb = DECK_TOP - DECK_PLATE
    z0, z1 = COUPLER_Z - DRAWBAR_BEAM_H / 2, COUPLER_Z + DRAWBAR_BEAM_H / 2
    y_root, y_conv = BASE_Y0 + 0.05, COUPLER_Y + DRAWBAR_CONVERGE
    for side, sx in (("L", 1), ("R", -1)):
        root = (sx * DRAWBAR_ROOT_X, y_root)
        conv = (sx * DRAWBAR_TIP_X, y_conv)
        _flat_beam(f"Drawbar_{side}", root, conv, DRAWBAR_BEAM_W, z0, z1, frame)
        box(f"DrawbarMount_{side}", sx * DRAWBAR_ROOT_X - 0.10, sx * DRAWBAR_ROOT_X + 0.10, BASE_Y0 - 0.03, BASE_Y0 + 0.55,
            z1, zb - IBEAM_H + 0.03, frame)
        box(f"DrawbarGusset_{side}", sx * DRAWBAR_ROOT_X - 0.012, sx * DRAWBAR_ROOT_X + 0.012, BASE_Y0 - 0.03,
            BASE_Y0 + 0.80, z0 - 0.11, z0, frame)
        for k, dy in enumerate((0.07, 0.40)):
            cylinder_z(f"DrawbarBolt_{side}{k}", (sx * DRAWBAR_ROOT_X, BASE_Y0 + dy, zb - IBEAM_H + 0.036), 0.016, 0.014, steel,
                       segments=6)
    for n, t in enumerate((0.31, 0.63, 0.95)):
        y = y_root + t * (y_conv - y_root)
        hx = drawbar_x(y) - DRAWBAR_BEAM_W / 2 + 0.01
        _flat_beam(f"Drawbar_Cross{n}", (-hx, y), (hx, y), 0.06, COUPLER_Z - 0.02, COUPLER_Z + 0.02, frame)
    hy0, hy1 = COUPLER_Y + 0.07, y_conv + 0.10
    _flat_beam("Drawbar_Head", (0, hy1), (0, hy0), 0.07, z0, z1, frame)
    # deska hlavy a šrouby jen u varianty za traktor (kulová hlava za auto má na tomtéž místě skříň nájezdové brzdy)
    head = [_flat_beam("Drawbar_HeadPlate", (0, y_conv + 0.14), (0, y_conv - 0.10), 0.26, z1, z1 + 0.012, frame)]
    for dy in (-0.05, 0.03):
        head.append(cylinder_z(f"Drawbar_HeadBolt{dy:+.2f}", (0, y_conv + dy, z1 + 0.012 + 0.007), 0.013, 0.014, steel,
                               segments=6))
    build_drawbar_tractor(y_conv, z0, z1, head)
    build_drawbar_car(y_conv, z1)
    build_electric(y_conv, z1)

    jx, jy = JOCKEY_X, JOCKEY_Y
    bx = drawbar_x(jy)
    bz = COUPLER_Z
    box("Jockey_Bridge", -bx, bx, jy - 0.05, jy + 0.05, bz - 0.025, bz + 0.025, frame)
    box("Jockey_Clamp", jx - 0.11, jx + 0.11, jy - 0.09, jy + 0.09, bz + 0.025, bz + 0.095, frame)
    moving = [
        tube("Jockey_Tube", (jx, jy, 0.30), (jx, jy, bz + 0.40), 0.045, steel, segments=14),
        tube("Jockey_Crank", (jx - 0.20, jy, bz + 0.40), (jx + 0.20, jy, bz + 0.40), 0.014, frame, segments=8),
        tube("Jockey_CrankGrip", (jx + 0.12, jy, bz + 0.40), (jx + 0.22, jy, bz + 0.40), 0.022, "SDT_Rubber", segments=10),
        box("Jockey_Fork", jx - 0.075, jx + 0.075, jy - 0.035, jy + 0.035, 0.12, 0.31, steel),
        cylinder_x("Jockey_Wheel", (jx, jy, 0.14), 0.14, 0.09, "SDT_Rubber", segments=24),
    ]
    pivot = empty("jockeyWheel", (jx, jy, DRAWBAR_Z))
    for o in moving:
        w = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = w
    cx, cy, cz = JOCKEY_COL
    _shape_box("colJockeyWheel", pivot, jx - cx, jx + cx, jy - cy, jy + cy, 0.0, cz, COL_VEHICLE,
               compoundChild=True, density=0.001)
    aj = empty("attacherJoint", (0, COUPLER_Y, COUPLER_Z))
    aj.rotation_euler = (0, 0, math.radians(90))


# ------------------------------------------------------------------------------------------------------- dvě nádrže
def build_round_tank(size, z):
    """Jedna hlavní nádrž (skupina tankMain<litry>): válec se zaoblenými dny jako u malých nádrží Middle, čelo na BT.MAIN_TANK_Y_FRONT."""
    t = BT.Tank(size, z)
    name = f"Tank_Main{size}"
    shell, fit, lid, frm = BT.Mesh(name), BT.Mesh(f"{name}_Fittings"), BT.Mesh(f"{name}_Lid"), BT.Mesh(f"{name}_Frame")
    BT._shell(t, shell)
    BT._manway(t, shell, fit, lid, t.mid)
    BT._vent(t, fit, 152, t.mid + 0.16 * t.kf)
    BT._relief(t, fit, 212, t.mid - 0.12 * t.kf)
    BT._outlet(t, fit)
    BT._rear_drain(t, fit)
    BT._frame(t, frm)
    meshes = [m.finish() for m in (shell, fit, lid, frm)]
    bpy.context.view_layer.update()
    decals = BT._decals(t, meshes[0], name)
    zb = z + BT.GAP
    squash = Matrix.Translation((0, 0, zb)) @ Matrix.Diagonal((1, 1, TANK_SQUASH, 1)) @ Matrix.Translation((0, 0, -zb))
    for o in meshes + decals:
        o.data.transform(squash)
        o.data.update()
    return P.group(f"tankMain{size}", meshes + decals)


def build_two_tanks(z):
    """Přední nádrž (tankMain3000 / tankMain5000, zadní konec na TANK_A_END) a zadní (tankMain3000B / tankMain5000B, čelo na
    TANK_B_Y_FRONT)."""
    front = BT.MAIN_TANK_Y_FRONT
    drain_z = BT.MAIN_DRAIN.z
    zb = z + BT.GAP
    try:
        for suffix in ("", "B"):
            for size in TANK_SIZES_MAX:
                BT.MAIN_TANK_Y_FRONT = tank_front(size, suffix)
                BT.MAIN_DRAIN.y = BT.MAIN_TANK_Y_FRONT + TANK_DRAIN_OFFSET
                BT.MAIN_DRAIN.z = zb + (drain_z - zb) / TANK_SQUASH      # po zploštění nádrže vyjde výpust ve výšce drain_z
                before = {o.name for o in bpy.data.objects}
                build_round_tank(size, z)
                if suffix:
                    _rename_new(before, suffix)      # výpust zadní nádrže zůstává nastavený: napojuje se na něj sání čerpadla
    finally:
        BT.MAIN_TANK_Y_FRONT = front
        BT.MAIN_DRAIN.z = drain_z


GEN_CABLE_ENDS = [None, None]               # konce průchodek kabelů na zadních stěnách centrál (svět)


def build_equipment():
    z = DECK_TOP
    build_two_tanks(z)
    ix, iy = T.INDUCTION_XY
    T.build_induction_tank("Tank_Induction", ix, iy, z, T.INDUCTION_R, stand_h=T.INDUCTION_STAND_H,
                           cone_h=T.INDUCTION_CONE_H, body_h=T.INDUCTION_BODY_H)
    gen = G.build_generator((GEN_X, GEN_Y), z, None, tag="0", rear_socket=True)
    neck = P.empty("dieselNeckNode", Vector(gen["cap"]))
    neck.empty_display_size = 0.10
    GEN_CABLE_ENDS[0] = gen["cable"]
    gen2 = G.build_generator((-GEN_X, GEN_Y), z, None, tag="1", mirror=True, rear_socket=True)
    neck2 = P.empty("dieselNeckNode2", Vector(gen2["cap"]))
    neck2.empty_display_size = 0.10
    GEN_CABLE_ENDS[1] = gen2["cable"]
    # druhá centrála se zapíná konfigurací v obchodě (objectChange), proto je celá pod jedním uzlem
    P.group("generator2", gen2["objects"] + [gen2["exhaust_node"], neck2])
    px, py = T.PUMP_XY
    T.build_pump("Pump", px, py, z)
    tb_x0, tb_x1, _, _ = T.TOOLBOX_XY
    cy0, cy1 = cabinet_y_range()
    build_canister_cabinet("Toolbox", tb_x0, tb_x1, cy0, cy1, z, ceiling=cabinet_ceiling())
    build_plumbing()


# ----------------------------------------------------------------------------------------------- navíječe a hadice
# Dvě hadice, každý dron má svou. Navíječe jsou zapuštěné v kapsách horní desky (nahoře by stály v pochozí ploše a těsně pod
# rotory): A vlevo hned před truhlou nabíječky (za přední nádrží), B vpravo mezi nádržemi před příčníkem; pod deskou je jinde
# nádrž. Osa navíječe je podél vleku, otočný přívod je na konci k ploše dronu a prochází stěnou kapsy, hadice vychází na
# vnitřní straně bubnu svisle vzhůru, přes vnitřní hranu kapsy na palubu a po ní k držáku koncovky, odkud se zvedá k hrdlu
# dronu. Hrdlo na pravém boku trupu (přední dron nosem dozadu: hrdlo je vlevo, zadní nosem dopředu: hrdlo je vpravo) leží na
# straně paluby, kde stojí navíječ.
REEL_Z = POST_TOP - T.HOSE_R - 0.025           # osa v kapse = výška vodorovného výtlaku pod deskou, výtlak vchází do spojky rovně
REEL_FLANGE = REEL_R + 0.06
POCKET_FLOOR = REEL_Z - REEL_FLANGE - 0.015    # horní plocha dna kapsy (podložka navíječe 15 mm)
POCKET_WALL = 0.010
# osa navíječů je o kus od okraje: zásuvka kabelu nabíječky na zadní stěně truhly je na x 0,75 (viz build_charger_cable)
REEL_X = 0.43
_REEL_A = (REEL_X, chest_cutout()[2] - POCKET_WALL - 0.142, REEL_Z)   # zadní stěna kapsy A sedí na stěně truhly nabíječky
_REEL_B = (REEL_X, chest_cutout()[3] + POCKET_WALL + 0.142, REEL_Z)   # zrcadlově k A: přední stěna kapsy B sedí na zadní stěně truhly


def reel_pocket(cfg):
    """Vnitřní rozměry kapsy navíječe (x0, x1, y0, y1): od bočnic 10 mm, od vnitřní strany (kudy vychází hadice) 30 mm, od
    konzol po Y 7 mm."""
    rx, ry, _ = cfg["center"]
    gap_in, gap_out = REEL_FLANGE + 0.030, REEL_FLANGE + 0.010
    x0, x1 = (rx - gap_in, rx + gap_out) if cfg["ib"] < 0 else (rx - gap_out, rx + gap_in)
    return x0, x1, ry - 0.142, ry + 0.142


def _hose_set(center, e, ib, lay_deck, tip):
    """Hadice z kapsy: start na vnitřní straně bubnu, Lay1 svisle nad ním v úrovni paluby, Lay2 za hranou kapsy, Lay3..Lay5
    (lay_deck) leží na palubě (Lay3 je kotva volné části, z ní se počítá dosah k hrdlu)."""
    rx, ry, rz = center
    y_out = ry - e * 0.08
    x_exit = rx + ib * HOSE_COIL_R
    start = (x_exit, y_out, rz)
    y2 = y_out + (lay_deck[0][1] - y_out) * 0.1
    lay = [(x_exit, y_out, TOP_SURF), (rx + ib * (REEL_FLANGE + 0.090), y2, TOP_SURF + 0.07)]
    lay += [(x, y, HOSE_Z) for x, y in lay_deck]
    return {"center": center, "e": e, "ib": ib, "start": start, "lay": lay, "tip": tip,
            "dir": (0.0, -1.0, 0.0) if e < 0 else (0.0, 1.0, 0.0)}


_MIRROR_Y = _REEL_A[1] + _REEL_B[1]               # B je A zrcadlená přes střed truhly nabíječky (y = _MIRROR_Y / 2)
HOSE_SETS = {
    "": _hose_set(_REEL_A, -1, -1, [(0.33, 1.52), (0.44, 1.00), (-0.70, 1.55)], (-0.35, PAD_Y[0] + 1.05, HOSE_Z + 0.006)),
    "B": _hose_set(_REEL_B, 1, -1, [(0.33, _MIRROR_Y - 1.52), (0.44, _MIRROR_Y - 1.00), (-0.70, _MIRROR_Y - 1.55)],
                   (-0.35, PAD_Y[1] - 1.05, HOSE_Z + 0.006)),
}
CUR_HOSE = HOSE_SETS[""]


def _use_hose_set(tag):
    global CUR_HOSE, REEL, HOSE_START, HOSE_LAY, HOSE_PARK_TIP, HOSE_PARK_DIR
    CUR_HOSE = HOSE_SETS[tag]
    REEL = CUR_HOSE["center"]
    HOSE_START, HOSE_LAY, HOSE_PARK_TIP, HOSE_PARK_DIR = CUR_HOSE["start"], CUR_HOSE["lay"], CUR_HOSE["tip"], CUR_HOSE["dir"]


def build_reel_pocket(cfg):
    """Kapsa navíječe pod horní deskou: dno a čtyři stěny až do roviny paluby (otvor v desce dělá rebuild_top_deck); stěna na
    straně otočného přívodu má pro něj čtvercový průchod."""
    x0, x1, y0, y1 = reel_pocket(cfg)
    w, frame = POCKET_WALL, "SDT_Frame"
    zb = POCKET_FLOOR - w
    box("ReelPocket_Floor", x0 - w, x1 + w, y0 - w, y1 + w, zb, POCKET_FLOOR, frame)
    box("ReelPocket_WallXa", x0 - w, x0, y0, y1, zb, TOP_SURF, frame)
    box("ReelPocket_WallXb", x1, x1 + w, y0, y1, zb, TOP_SURF, frame)
    rx, _, rz = cfg["center"]
    h = 0.036
    for side, (ya, yb) in (("a", (y0 - w, y0)), ("b", (y1, y1 + w))):
        if (cfg["e"] < 0) == (side == "a"):
            box(f"ReelPocket_WallY{side}0", x0 - w, rx - h, ya, yb, zb, TOP_SURF, frame)
            box(f"ReelPocket_WallY{side}1", rx + h, x1 + w, ya, yb, zb, TOP_SURF, frame)
            box(f"ReelPocket_WallY{side}2", rx - h, rx + h, ya, yb, zb, rz - h, frame)
            box(f"ReelPocket_WallY{side}3", rx - h, rx + h, ya, yb, rz + h, TOP_SURF, frame)
        else:
            box(f"ReelPocket_WallY{side}", x0 - w, x1 + w, ya, yb, zb, TOP_SURF, frame)


def build_hose_reel_parts():
    """Modrý navíječ zapuštěný v kapse horní desky (osa podél vleku): buben, bočnice, konzoly vně bočnic na podložce na dně
    kapsy, otočný přívod na konci k ploše dronu (prochází stěnou kapsy) a hadice navinutá v jedné vrstvě (fillHoseCoil).
    Jména dílů obsahují značku sady (A bez ní, B s B)."""
    cfg = CUR_HOSE
    tag = "B" if cfg is HOSE_SETS["B"] else ""
    rx, ry, rz = cfg["center"]
    e, ib = cfg["e"], cfg["ib"]
    frame = "SDT_Frame"
    build_reel_pocket(cfg)
    tube(f"HoseReel_{tag}Drum", (rx, ry - 0.10, rz), (rx, ry + 0.10, rz), REEL_R, "SDT_HoseBlue", segments=32)
    for dy in (-0.11, 0.11):
        tube(f"HoseReel_{tag}Flange{dy:+.2f}", (rx, ry + dy - 0.0075, rz), (rx, ry + dy + 0.0075, rz), REEL_FLANGE, frame,
             segments=32)
    for side, ya, yb in (("Out", ry - 0.135, ry - 0.12), ("In", ry + 0.12, ry + 0.135)):
        box(f"HoseReel_{tag}Bracket{side}", rx - 0.10, rx + 0.10, ya, yb, POCKET_FLOOR, rz + 0.04, frame)
    box(f"HoseReel_{tag}Base", rx - 0.10, rx + 0.10, ry - 0.135, ry + 0.135, POCKET_FLOOR, POCKET_FLOOR + 0.015, frame)
    tube(f"HoseReel_{tag}Axle", (rx, ry - 0.14, rz), (rx, ry + 0.14, rz), 0.02, "SDT_Steel", segments=12)
    tube(f"HoseReel_{tag}Swivel", (rx, ry + e * 0.135, rz), (rx, ry + e * 0.185, rz), 0.03, "SDT_Steel", segments=16)
    turns = 0.16 / (2 * HOSE_R)
    steps = int(turns * 32)
    y_in, y_out = ry + e * 0.08, ry - e * 0.08                  # závit od přívodu ke konci, kde hadice vychází
    coil = []
    for k in range(steps + 1):
        s = k / steps
        a = (0.0 if ib > 0 else math.pi) - ib * (1 - s) * turns * 2 * math.pi     # hadice vždy odchází svisle vzhůru
        coil.append(Vector((rx + HOSE_COIL_R * math.cos(a), y_in + (y_out - y_in) * s, rz + HOSE_COIL_R * math.sin(a))))
    P.sweep("fillHoseCoil", coil, HOSE_R, "SDT_HoseBlack", segments=24)
    build_reel_lid(cfg, tag)


HOSE_LID_T = 0.010
HOSE_LID_OPEN_DEG = 100.0


def build_reel_lid(cfg, tag):
    """Víko kapsy navíječe (hoseLidHinge, u sady B s příponou B): závěs na vnější straně kapsy (hadice vychází z vnitřní), po složení vleku
    se zaklapne přes kapsu (animace foldLadder, stejný čas jako úchyty lyží). V i3d je víko otevřené, vlek je rozložený."""
    x0, x1, y0, y1 = reel_pocket(cfg)
    s = 1 if cfg["ib"] < 0 else -1                     # strana závěsu: za vnější bočnicí kapsy
    hx = x1 + POCKET_WALL if s > 0 else x0 - POCKET_WALL
    z0, z1 = TOP_SURF, TOP_SURF + HOSE_LID_T
    ly0, ly1 = y0 - POCKET_WALL, y1 + POCKET_WALL
    length = (x1 - x0) + 2 * POCKET_WALL + 0.012
    far = hx - s * length
    hinge = empty("hoseLidHinge", (hx, (ly0 + ly1) / 2, z1))
    parts = [
        box(f"HoseLid_Plate", min(hx, far), max(hx, far), ly0, ly1, z0, z1, "SDT_TopDeck"),
        box(f"HoseLid_Rim", min(hx, far), max(hx, far), ly0, ly0 + 0.012, z1, z1 + 0.008, "SDT_Frame"),
        box(f"HoseLid_RimB", min(hx, far), max(hx, far), ly1 - 0.012, ly1, z1, z1 + 0.008, "SDT_Frame"),
        box(f"HoseLid_Latch", min(far, far + s * 0.05), max(far, far + s * 0.05), (ly0 + ly1) / 2 - 0.03,
            (ly0 + ly1) / 2 + 0.03, z1, z1 + 0.014, "SDT_Steel"),
        box(f"HoseLid_Handle", min(far - s * 0.0, far + s * 0.09), max(far, far + s * 0.09), (ly0 + ly1) / 2 - 0.012,
            (ly0 + ly1) / 2 + 0.012, z1 + 0.014, z1 + 0.022, "SDT_Rubber"),
    ]
    for ky in (ly0 + 0.025, ly1 - 0.025):
        parts.append(tube(f"HoseLid_Knuckle{ky:.2f}", (hx, ky - 0.015, z1), (hx, ky + 0.015, z1), 0.012, "SDT_Steel",
                          segments=12))
    for o in parts:
        _set_parent(o, hinge, o.matrix_world.copy())
    hinge.rotation_euler.y = s * math.radians(HOSE_LID_OPEN_DEG)
    return hinge


DISCHARGE_RUN_Y = {"": None, "B": None}        # vodorovný úsek 0,5 m za kapsou (u B přes přední část nádrže B, nad jejím víkem)


def _discharge_hook(top, fit):
    """Výtlak čerpadla: z vývodu vzhůru, pod horní deskou po Y, napříč k ose navíječe a po Y rovně do otočného přívodu (osa
    navíječe je ve výšce vodorovného úseku), dvě větve."""
    zh = POST_TOP - T.HOSE_R - 0.025
    R = T.DISCHARGE_BEND
    for tag in ("", "B"):
        cfg = HOSE_SETS[tag]
        rx, ry, rz = cfg["center"]
        e = cfg["e"]
        end_y = ry + e * 0.18
        yv = DISCHARGE_RUN_Y[tag] or ry + e * 0.50
        corners = [top, V(top.x, top.y, zh), V(top.x, yv, zh), V(rx, yv, zh), V(rx, end_y, rz)]
        pipe = T.rounded_path(corners, [R, R, R])
        P.sweep(f"Pump_Discharge{tag}", pipe, T.HOSE_R, "SDT_HoseBlack", segments=24)


# build_plumbing z sdt_tanks s výtlakem nahrazeným hákem _discharge_hook (jinak počítá jednu hadici k jednomu navíječi)
_pl = inspect.getsource(T.build_plumbing)
_a = _pl.index("    # výtlak: jedna souvislá hadice")
_b = _pl.index("    fit.finish()")
_pl = _pl[:_a] + "    discharge_hook(top, fit)\n" + _pl[_b:]
_pl = _pl.replace("def build_plumbing(", "def build_plumbing_hooked(", 1)
exec(compile(_pl, T.__file__, "exec"), T.__dict__)
T.discharge_hook = _discharge_hook


def build_plumbing():
    T.build_plumbing_hooked(DECK_TOP, TANK_Y, TANK_R, TANK_LEN, (0, 0, 0), ceiling_z=POST_TOP)


def build_both_hoses():
    """Dvě hadice: sada A (jména fillHose*) a sada B (fillHoseB*)."""
    _use_hose_set("")
    build_fill_hose()
    before = {o.name for o in bpy.data.objects}
    _use_hose_set("B")
    build_fill_hose()
    for o in [o for o in bpy.data.objects if o.name not in before]:
        base = o.name.rsplit(".", 1)[0] if o.name[-4:-3] == "." and o.name[-3:].isdigit() else o.name
        o.name = "fillHoseB" + base[len("fillHose"):] if base.startswith("fillHose") else base + "B"
    _use_hose_set("")


def build_plumbing_placeholder():
    return None


# ------------------------------------------------------------------------------------------ nabíječka, kabel, kolize
def _cable_path(start, end, via):
    pts = [tuple(start)] + [tuple(v) for v in via] + [tuple(end)]
    return P.hermite_path(pts, samples=12)


# kabely truhla -> centrály: pod horním nosníkem TopBeam_L mezi stěnou truhly (x 0,945) a vnitřní líc sloupků (0,97), po vnitřní
# straně Post_L0 dolů a po palubě za centrálami k jejich průchodkám. Kabel 1 je níž a k sloupku zahne dřív, kabel 2 nad ním
# pokračuje až k přední hraně sloupku, dole se kříží v jiné výšce.
CHARGER_CABLE_X = 0.9575
CHARGER_CABLE_Z = (2.548, 2.578)            # pod nosníkem (spodek 2,61)
CHARGER_CABLE_TURN_Y = (3.08, 3.12)         # kde kabely za truhlou zahnou k okraji
CHARGER_CABLE_POST_Y = (-0.945, -0.985)     # svislý úsek po vnitřní straně Post_L0
CHARGER_CABLE_DECK_Z = (1.10, DECK_TOP + CABLE_R + 0.004)    # kde kabely dole zahnou dozadu
CHARGER_CABLE_DECK_Y = (-0.76, -0.72)       # běh po palubě za centrálami


def charger_cable_route(k, start):
    gx, gy, gz = GEN_CABLE_ENDS[k]
    x, z, ty, py = CHARGER_CABLE_X, CHARGER_CABLE_Z[k], CHARGER_CABLE_TURN_Y[k], CHARGER_CABLE_POST_Y[k]
    dz, dy = CHARGER_CABLE_DECK_Z[k], CHARGER_CABLE_DECK_Y[k]
    zl = DECK_TOP + CABLE_R + 0.004
    pts = [start, (start.x, ty, start.z), (x, ty, start.z), (x, ty, z), (x, py, z), (x, py, dz), (x, dy, dz)]
    if k == 0:
        pts += [(x - 0.12, dy, zl), (gx, dy, zl)]
    else:
        pts += [(gx, dy, zl)]
    pts += [(gx, dy, gz), (gx, gy, gz)]
    return _rounded_polyline(pts)


def build_charger_cable():
    """Napájecí kabely truhla nabíječky -> elektrocentrály, napevno (průchodky na obou koncích, žádné zástrčky, vidět i složené):
    od truhly pod horní nosník TopBeam_L, pod ním dopředu k Post_L0, po jeho vnitřní straně dolů a po palubě za centrálami
    k jejich průchodkám; příchytky pod nosníkem, na sloupku a na palubě. Kabel druhé centrály (a jeho vlastní příchytky) patří pod
    uzel generator2 (zapíná ho konfigurace). Jen vizuál."""
    m = _chest_matrix()
    ox1, sy, sz = chest_box()[1], CHARGER_SOCKET_Y, chest_floor() + CHARGER_SOCKET_Z
    p0 = m @ Vector((ox1 + 0.02, sy, sz))
    along = (m.to_3x3() @ Vector((1, 0, 0))).normalized()
    start = p0 + along * 0.06
    out = []
    for k in (0, 1):
        name = "chargerCable" if k == 0 else "chargerCable2"
        out.append(P.sweep(name, charger_cable_route(k, start), CABLE_R, "SDT_HoseBlack", segments=10))
    gland = tube("Charger_Gland", tuple(p0), tuple(start), 0.022, "SDT_Rubber", segments=14, radius_end=0.014)
    _set_parent(gland, out[0], gland.matrix_world.copy())

    x, r = CHARGER_CABLE_X, CABLE_R
    chest_y = (chest_cutout()[2] - 0.03, chest_cutout()[3] + 0.03)
    clips, clips2 = [], []
    # pod nosníkem: objímky přes oba kabely zavěšené na spodku nosníku (ne u truhly a u sloupků, tam není místo)
    y = CHARGER_CABLE_TURN_Y[0] - 0.12
    while y > CHARGER_CABLE_POST_Y[0] + 0.10:
        if not (chest_y[0] < y < chest_y[1]) and all(abs(y - py) > 0.08 for py in POST_Y):
            clips.append(box(f"Charger_CableClipTop{len(clips)}", x - r - 0.004, x + r + 0.004, y - 0.01, y + 0.01,
                             CHARGER_CABLE_Z[0] - r - 0.004, TOP_SURF - TOP_PLATE + 0.003, "SDT_Steel"))
        y -= 0.40
    # na sloupku: objímky přes oba svislé kabely, přišroubované k vnitřní stěně sloupku
    for n, z in enumerate((1.35, 1.75, 2.15)):
        clips.append(box(f"Charger_CableClipPost{n}", x - r - 0.004, POST_X - POST / 2 + 0.004,
                         CHARGER_CABLE_POST_Y[1] - r - 0.006, CHARGER_CABLE_POST_Y[0] + r + 0.006, z - 0.015, z + 0.015,
                         "SDT_Steel"))
    # na palubě: příchytky přes kabely ležící za centrálami
    zl = DECK_TOP + r + 0.004
    for n, cx in enumerate((0.70, 0.10, -0.20)):
        ya = CHARGER_CABLE_DECK_Y[0] - r - 0.006 if cx > GEN_CABLE_ENDS[0][0] + 0.05 else CHARGER_CABLE_DECK_Y[1] - r - 0.006
        o = box(f"Charger_CableClipDeck{n}", cx - 0.012, cx + 0.012, ya, CHARGER_CABLE_DECK_Y[1] + r + 0.006, DECK_TOP,
                zl + r + 0.004, "SDT_Steel")
        (clips if cx > GEN_CABLE_ENDS[0][0] + 0.05 else clips2).append(o)
    for o in clips:
        _set_parent(o, out[0], o.matrix_world.copy())
    for o in clips2:
        _set_parent(o, out[1], o.matrix_world.copy())
    grp = bpy.data.objects["generator2"]
    _set_parent(out[1], grp, out[1].matrix_world.copy())
    return out[0], P.path_length(charger_cable_route(0, start))


def equipment_collisions():
    z = DECK_TOP
    px, py = T.PUMP_XY
    ix, iy = T.INDUCTION_XY
    tee = T.pump_ports(px, py, z)["tee"]
    cx0, cx1, cy0, cy1, czw = chest_box()
    tb_x0, tb_x1, _, _ = T.TOOLBOX_XY
    tb_y0, tb_y1 = cabinet_y_range()
    cols = {
        **cabinet_collisions("Toolbox", tb_x0, tb_x1, tb_y0, tb_y1, z, ceiling=cabinet_ceiling()),
        "colGenerator": (GEN_X - G.FX - 0.023, GEN_X + G.FX + 0.023, GEN_Y - G.FY - 0.023, GEN_Y + G.FY + 0.023, z, z + 0.84),
        "colGenerator2": (-GEN_X - G.FX - 0.023, -GEN_X + G.FX + 0.023, GEN_Y - G.FY - 0.023, GEN_Y + G.FY + 0.023, z, z + 0.84),
        "colInductionTank": (ix - T.INDUCTION_R - 0.015, ix + T.INDUCTION_R + 0.015, iy - T.INDUCTION_R - 0.015,
                             iy + T.INDUCTION_R + 0.015, z,
                             z + T.INDUCTION_STAND_H + T.INDUCTION_CONE_H + T.INDUCTION_BODY_H),
        "colPump": (px - 0.262, px + 0.316, py - 0.185, py + 0.185, z, z + T.PUMP_AXIS_H + 0.25),
        "colMixer": (tee.x - 0.150, tee.x + 0.150, tee.y - 0.100, tee.y + 0.250, z, tee.z + 0.47),
        # truhla nabíječky nad horní palubou (Pavel 2026-10-07: chyběla u Middle, stejná díra u Max)
        "colChest": (cx0, cx1, cy0, cy1, TOP_SURF, czw + CHEST_LID_T),
        "colRelayBox": RELAY_BOX,
    }
    for tag in ("", "B"):
        x0, x1, y0, y1 = reel_pocket(HOSE_SETS[tag])
        cols[f"colHoseReel{tag}"] = (x0, x1, y0, y1, POST_TOP, REEL_Z + REEL_FLANGE)
    return cols


def build_i3d_structure(vis):
    """Uspořádání pro FS25 jako u velkého vleku: kolizní komponenta jako kořen, kolize nádrží (obě) a výbavy, plnicí uzly, kola,
    světla."""
    rail_z0 = DECK_TOP - RAIL_H
    # vlastní tvar kořene je jen drobná krychle: skutečný box rámu je dětský tvar colChassis. Po zmrazení rozloženého vleku (kinematické těleso)
    # se kolize dětských tvarů vrací skriptem o těžiště zpět (SprayDroneStation.updateFreeze), kořenový tvar by zůstal posunutý
    comp = _shape_box(COMPONENT_NAME, None, -0.02, 0.02, 0.0, 0.04, DECK_TOP - 0.10, DECK_TOP - 0.06, COL_VEHICLE, dynamic=True,
                      compound=True)
    vis.parent = comp
    vis.matrix_parent_inverse = Matrix.Identity(4)
    cols = _group("collisions", comp)
    child = dict(compoundChild=True, density=0.001)
    _shape_box("colChassis", cols, -BASE_W / 2, BASE_W / 2, BASE_Y0, BASE_Y1, rail_z0, DECK_TOP, COL_VEHICLE, **child)
    _shape_box("colTopDeck", cols, -TOP_W / 2, TOP_W / 2, TOP_FRONT_Y, TOP_Y1, POST_TOP, TOP_SURF, COL_VEHICLE, **child)
    for suffix in ("", "B"):
        for size in TANK_SIZES_MAX:
            hw, ln, top = BT.tank_envelope(size)
            y_front = tank_front(size, suffix)
            _shape_box(f"colTank{size}{suffix}", cols, -hw, hw, y_front, y_front + ln, DECK_TOP, DECK_TOP + top, COL_VEHICLE,
                       **child)
    for name, box_ in equipment_collisions().items():
        _shape_box(name, cols, *box_, COL_VEHICLE, **child)
    _shape_box("colDrawbar", cols, -0.12, 0.12, COUPLER_Y + 0.20, BASE_Y0, COUPLER_Z - 0.05, COUPLER_Z + 0.08,
               COL_VEHICLE, **child)
    # sloupky horní plošiny a tandemové blatníky (Pavel 2026-10-13: kolize všude); blatník jen jako deska nad kolem, pod ní
    # zůstává kolo samo
    for side, sx in (("L", 1), ("R", -1)):
        for i, py in [("F", POST_FRONT_Y)] + list(enumerate(POST_Y)):
            px = sx * POST_X
            _shape_box(f"colPost{side}{i}", cols, px - POST / 2, px + POST / 2, py - POST / 2, py + POST / 2, DECK_TOP,
                       POST_TOP, COL_VEHICLE, **child)
        fx0, fx1 = sorted((sx * FENDER_X[0], sx * FENDER_X[1]))
        _shape_box(f"colFender{side}", cols, fx0, fx1, AXLE_Y[0] - FENDER_R * 0.6, AXLE_Y[1] + FENDER_R * 0.6,
                   WHEEL_R + FENDER_R * 0.55, WHEEL_R + FENDER_R + 0.014, COL_VEHICLE, **child)

    wheels = _group("wheels", vis)
    for ay, pos in zip(AXLE_Y, ("Front", "Back")):
        for sx, side in ((1, "Left"), (-1, "Right")):
            _group(f"wheel{pos}{side}", wheels, (sx * TRACK_X, ay, WHEEL_R))

    fill = _group("fill", vis)
    _shape_box("fillTrigger", fill, -BASE_W / 2 - 0.3, BASE_W / 2 + 0.3, BASE_Y0 - 0.3, BASE_Y1 + 0.3, 0.0,
               DECK_TOP + 1.2, COL_TRIGGER, kinematic=True, compound=True, trigger=True)
    y_a = min(tank_front(s, "") for s in TANK_SIZES_MAX)
    y_b = TANK_B_Y_FRONT + max(tank_extent(s)[1] for s in TANK_SIZES_MAX)
    _shape_box("exactFillRootNode", fill, -TANK_R, TANK_R, y_a, y_b, DECK_TOP + 0.12, DECK_TOP + TANK_TOP, COL_FILL_ROOT,
               kinematic=True, compound=True)
    _shape_box("concentrateFillRootNode", fill, *T.induction_fill_box(*T.INDUCTION_XY, DECK_TOP), COL_FILL_ROOT,
               kinematic=True, compound=True)
    fb1, fb2 = G.fuel_fill_box((GEN_X, GEN_Y), DECK_TOP), G.fuel_fill_box((-GEN_X, GEN_Y), DECK_TOP)
    _shape_box("dieselFillRootNode", fill, fb2[0], fb1[1], fb1[2], fb1[3], fb1[4], fb1[5], COL_FILL_ROOT, kinematic=True, compound=True)

    lights = _group("sharedLights", vis)
    for name, loc, rot in LIGHT_NODES:
        i3d_rot_node(name, lights, loc, rot)

    enter = _group("enterable", vis)
    _group("exitPoint", enter, EXIT_POINT)
    target = _group("outdoorCameraTarget", enter, CAMERA_TARGET)
    cam_data = bpy.data.cameras.get("outdoorCamera") or bpy.data.cameras.new("outdoorCamera")
    cam_data.lens = 22
    cam_data.clip_start = 0.3
    cam_data.clip_end = 5000
    cam = bpy.data.objects.new("outdoorCamera", cam_data)
    bpy.data.collections[COLLECTION_NAME].objects.link(cam)
    cam.parent = target
    cam.matrix_parent_inverse = Matrix.Identity(4)
    cam.matrix_world = Matrix.Translation(Vector(CAMERA_TARGET) + Vector((0, 10, 4)))
    # kamery dronů: za běhu je skript (SprayDroneStation.attachDroneCamera) připojí pod uzel náklonu zvolené varianty dronu
    for n in (1, 2):
        data = bpy.data.cameras.get(f"droneCamera{n}") or bpy.data.cameras.new(f"droneCamera{n}")
        data.lens = 20
        data.clip_start = 0.1
        data.clip_end = 5000
        drone_cam = bpy.data.objects.new(f"droneCamera{n}", data)
        bpy.data.collections[COLLECTION_NAME].objects.link(drone_cam)
        drone_cam.parent = vis
        drone_cam.matrix_parent_inverse = Matrix.Identity(4)
        drone_cam.matrix_world = Matrix.Translation((0, 0, TOP_SURF + 1.0))
        # vnější pohled na dron: střed otáčení a kamera pod ním (skript střed připojí pod uzel dronu, hodnoty kamery jsou v XML)
        out_target = _group(f"droneOutTarget{n}", vis, (0, 0, TOP_SURF + 1.0))
        out_data = bpy.data.cameras.get(f"droneOutCamera{n}") or bpy.data.cameras.new(f"droneOutCamera{n}")
        out_data.lens = 22
        out_data.clip_start = 0.1
        out_data.clip_end = 5000
        out_cam = bpy.data.objects.new(f"droneOutCamera{n}", out_data)
        bpy.data.collections[COLLECTION_NAME].objects.link(out_cam)
        out_cam.parent = out_target
        out_cam.matrix_parent_inverse = Matrix.Identity(4)
        out_cam.matrix_world = Matrix.Translation((0, 5, TOP_SURF + 1.0))

    occ = _group("tipOccluder", vis)
    _group("occlusionAreaStart", occ, (0.9, BASE_Y0, 0))
    _group("occlusionAreaWidth", occ, (-0.9, BASE_Y0, 0))
    _group("occlusionAreaHeight", occ, (0.9, BASE_Y1, 0))
    plate = _group("licensePlateBack", vis, (0, BASE_Y1 + 0.001, rail_z0 - 0.07))
    plate.rotation_euler = (0, 0, math.radians(180))
    return comp


# ------------------------------------------------------------------------------------------------- dva drony a plochy
def rebuild_top_deck():
    """Horní deska znovu z obdélníků kolem otvorů: truhla nabíječky a obě kapsy navíječů (vnější rozměr se stěnami)."""
    for o in [o for o in bpy.data.objects if o.name.startswith("TopDeck_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    w = POCKET_WALL
    holes = [chest_cutout()[:4]]
    for cfg in HOSE_SETS.values():
        x0, x1, y0, y1 = reel_pocket(cfg)
        holes.append((x0 - w, x1 + w, y0 - w, y1 + w))
    hw = TOP_W / 2
    xs = sorted({-hw, hw} | {round(v, 6) for h in holes for v in h[:2] if -hw < v < hw})
    ys = sorted({TOP_FRONT_Y, TOP_Y1} | {round(v, 6) for h in holes for v in h[2:] if TOP_FRONT_Y < v < TOP_Y1})
    rects, open_runs = [], {}
    for ya, yb in zip(ys, ys[1:]):
        ym = (ya + yb) / 2
        runs, cur = [], None
        for xa, xb in zip(xs, xs[1:]):
            xm = (xa + xb) / 2
            solid = not any(h[0] < xm < h[1] and h[2] < ym < h[3] for h in holes)
            if solid:
                cur = [xa, xb] if cur is None else [cur[0], xb]
            elif cur is not None:
                runs.append(tuple(cur))
                cur = None
        if cur is not None:
            runs.append(tuple(cur))
        nxt = {}
        for run in runs:
            k = open_runs.get(run)
            if k is not None:
                rects[k][3] = yb
            else:
                k = len(rects)
                rects.append([run[0], run[1], ya, yb])
            nxt[run] = k
        open_runs = nxt
    for k, (x0, x1, y0, y1) in enumerate(rects):
        box(f"TopDeck_{k}", x0, x1, y0, y1, TOP_SURF - TOP_PLATE, TOP_SURF, "SDT_TopDeck")


def build_drones():
    """Šest dronů z build_drone.py (S, M, L pro každou plochu): pro dron B jsou prefixy Drone2_*."""
    coll = D.clear_collection()
    for variants in (DRONE_VARIANTS, DRONE_VARIANTS_B):
        for key, prefix in variants.items():
            D.build_drone(coll, name=prefix[:-1], spec=D.SPECS[key], arms_folded=1.0)
    bpy.context.view_layer.update()


def build_drone_unit(variants, y, suffix):
    """Posadí drony jedné plochy na její střed (nosem dopředu, -Y) s úchyty lyží, servisními díly a heliport; heliport druhé
    plochy dostane příponu."""
    global DRONE_Y, CLAMP_Y
    DRONE_Y = y
    CLAMP_Y = (y - 0.075, y + 0.075)
    for prefix in variants.values():
        place_drone(prefix)
        build_drone_leds(prefix)
        build_drone_clamps(prefix)
        build_drone_service_parts(prefix)
        build_drone_decals(prefix)
    before = {o.name for o in bpy.data.objects}
    build_heliport()
    if suffix:
        _rename_new(before, suffix)


def rotate_drones(variants, y):
    """Otočí hotové drony (všechny uzly s jejich prefixem) o 180° kolem svislé osy středu plochy: přední dron míří nosem dozadu."""
    prefixes = tuple(variants.values())
    rot = Matrix.Translation((0, y, 0)) @ Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Translation((0, -y, 0))
    for o in [o for o in bpy.data.objects if o.name.startswith(prefixes)]:
        if o.parent is None or not o.parent.name.startswith(prefixes):
            o.matrix_world = rot @ o.matrix_world
    bpy.context.view_layer.update()


def dirt_atlas(obj):
    prefixes = tuple(DRONE_VARIANTS.values()) + tuple(DRONE_VARIANTS_B.values())
    if obj.name.startswith(prefixes) and "Clamp" not in obj.name:
        return "drone"
    return "trailer"


def build_charger_set():
    """Baterie, nabíječka a truhla v základní poloze, pak otočené o 90° k levému okraji paluby (víko ven přes okraj)."""
    before = {o.name for o in bpy.data.objects}
    build_batteries()
    build_charger()
    attach_batteries()
    build_charger_chest()
    _transform_new(before, _chest_matrix())


def build_radio_gear_max():
    """Anténa a GPS u levého okraje paluby: anténa před truhlou nabíječky a víky navijáků, GPS za nimi. Truhla i víka se
    vyklápějí ven přes okraj, takže obě stojí mimo jejich pás a nezavazí uprostřed paluby."""
    objs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("Chest", "HoseLid"))]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lip = bpy.data.objects["TopLip_L"]
    x_edge = min((lip.matrix_world @ Vector(c)).x for c in lip.bound_box) - 0.18
    build_radio_gear(ant_xy=(x_edge, min(p.y for p in pts) - 0.20), gps_xy=(x_edge, max(p.y for p in pts) + 0.20))


# ------------------------------------------------------------------------- prodloužená deska, plachta, záď
_big_build_upper_structure = build_upper_structure


def build_upper_structure():
    """Nástavba z Middle, horní deska prodloužená dopředu nad centrály (TOP_FRONT_Y): přední sloupky Post_LF/RF na čelním nosníku
    rámu s výztuhami, přední příčník, horní nosníky a lemy až k nové hraně (přední lem přesunutý na ni)."""
    _big_build_upper_structure()
    for n in ("TopBeam_L", "TopBeam_R", "TopLip_L", "TopLip_R", "TopLip_Front", "TopLip_FrontL", "TopLip_FrontR"):
        o = bpy.data.objects.get(n)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    hw = TOP_W / 2
    yf = POST_FRONT_Y
    for side, sx in (("L", 1), ("R", -1)):
        px = sx * POST_X
        box(f"Post_{side}F", px - POST / 2, px + POST / 2, yf - POST / 2, yf + POST / 2, DECK_TOP, POST_TOP, "SDT_Frame")
        plate_yz(f"Gusset_{side}_FrontF", px, 0.015, [(yf, POST_TOP - 0.32), (yf + 0.32, POST_TOP), (yf, POST_TOP)], "SDT_Frame")
        box(f"TopBeam_{side}", px - POST / 2, px + POST / 2, TOP_FRONT_Y, TOP_Y1, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
        box(f"TopLip_{side}", sx * hw - sx * 0.035, sx * hw, TOP_FRONT_Y, TOP_Y1, TOP_SURF, TOP_SURF + 0.04, "SDT_Frame")
    box("TopCross_F", -POST_X, POST_X, TOP_FRONT_Y, TOP_FRONT_Y + 0.07, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
    box("TopLip_Front", -hw, hw, TOP_FRONT_Y, TOP_FRONT_Y + 0.035, TOP_SURF, TOP_SURF + 0.04, "SDT_Frame")


def _side_bottom(y):
    """Spodní hrana boční plachty v místě y: lem přes lištu paluby, nad koly horní plocha tandemového blatníku (oblouky
    vpředu a vzadu, rovný díl mezi nápravami) s vůlí TARP_FENDER_GAP."""
    r = FENDER_R + 0.014
    if AXLE_Y[0] <= y <= AXLE_Y[-1]:
        return WHEEL_R + r + TARP_FENDER_GAP
    d = min(abs(y - ay) for ay in AXLE_Y)
    if d >= r:
        return TARP_BOTTOM
    return max(TARP_BOTTOM, WHEEL_R + math.sqrt(r ** 2 - d ** 2) + TARP_FENDER_GAP)


def _side_drop(yc):
    """Výška boční plachty v místě x (lokální osa podél boku, y = yc + x)."""
    return lambda x: TARP_TOP - _side_bottom(yc + x)


def build_tarps():
    """Plachty na bocích (tarpL, tarpR) a vpředu (tarpF) s rolemi a popruhy, vodicí lišty pod horními nosníky a polepy designu
    (lockupOnDark + pruh v z TARP_STRIPE_Z) pod pivoty plachet, ať se při rolování svinou s nimi. Postavené zavřené."""
    y0, y1 = TARP_Y
    yc, ln = (y0 + y1) / 2, y1 - y0
    h = TARP_TOP - TARP_BOTTOM
    off = P.TARP_DECAL_OFFSET
    zs = (TARP_STRIPE_Z[0] + TARP_STRIPE_Z[1]) / 2
    sh = TARP_STRIPE_Z[1] - TARP_STRIPE_Z[0]
    # popruhy krátké, jen u spodního lemu; nad blatníky žádné (plachta tam sedí na blatníku, popruh by sahal výš než jinde)
    straps = [y - yc for y in (y0 + 0.15 + (ln - 0.35) * k / 8 for k in range(9))
              if max(_side_bottom(y + d) for d in (-0.05, 0.0, 0.05)) <= TARP_BOTTOM]
    strap_top = TARP_STRAP_TOP - TARP_BOTTOM
    # zavřená role leží celou délkou ve výšce nejvyššího místa spodní hrany (vrchol blatníku), ať do něj nenarazí
    closed_drop = TARP_TOP - max(_side_bottom(y0 + ln * k / 200) for k in range(201))
    out = {}
    # lockup 4 : 1 (obsah BZUK 68 % šířky, STRATUS 98 %): vlevo obsah zhruba y 0,85-3,65, vpravo (čte se zezadu dopředu)
    # 2,15-6,25; spodní hrana z 1,54 nad popruhy
    lockup = {"L": (2.25, 2.05, 4.1), "R": (4.20, 2.05, 4.1)}
    for side, sx in (("L", 1), ("R", -1)):
        pivot, roll = P.tarp(f"tarp{side}", None, (sx * TARP_X, yc, TARP_TOP), (0, 1, 0), (sx, 0, 0), ln, h,
                             drop_fn=_side_drop(yc), straps=straps, strap_top=strap_top, roll_gap=TARP_ROLL_GAP,
                             closed_drop=closed_drop)
        out[side] = (pivot, roll)
        ly, lz, lw = lockup[side]
        P.brand_decal_set(f"tarp{side}", "lockupOnDark", (sx * (TARP_X + off), ly, lz), (sx, 0, 0), (0, 0, 1), lw,
                          parent=pivot, offset=0.0, tone=True)
        P.brand_decal_set(f"tarp{side}", "stripe", (sx * (TARP_X + off), yc, zs), (sx, 0, 0), (0, 0, 1), ln, sh,
                          parent=pivot, offset=0.0)
        box(f"TarpRail_{side}", *sorted((sx * TOP_W / 2, sx * (TARP_X + 0.015))), TARP_FRONT_Y - 0.02, y1 + 0.02,
            TARP_TOP - 0.015, TARP_TOP + 0.01, "SDT_Alu")
    pivot, roll = P.tarp("tarpF", None, (0, TARP_FRONT_Y, TARP_TOP), (1, 0, 0), (0, -1, 0), 2 * TARP_X, h,
                         straps=(-0.75, 0.0, 0.75), strap_top=strap_top, roll_gap=TARP_ROLL_GAP)
    out["F"] = (pivot, roll)
    P.brand_decal_set("tarpF", "lockupOnDark", (0, TARP_FRONT_Y - off, 1.95), (0, -1, 0), (0, 0, 1), 2.0, parent=pivot,
                      offset=0.0, tone=True)
    P.brand_decal_set("tarpF", "stripe", (0, TARP_FRONT_Y - off, zs), (0, -1, 0), (0, 0, 1), 2 * TARP_X, sh, parent=pivot,
                      offset=0.0)
    build_tarp_collisions(TARP_X, y0, y1, TARP_TOP, _side_bottom, TARP_FRONT_Y, TARP_BOTTOM)
    return out


def set_tarps(t):
    """Náhled plachet: 0 = srolováno (rozložený vlek), 1 = zavřeno (stav v i3d)."""
    for tag in ("L", "R", "F"):
        P.tarp_preview(bpy.data.objects[f"tarp{tag}"], bpy.data.objects[f"tarp{tag}Roll"], t)
    bpy.context.view_layer.update()


def build_rear():
    """Záď: roleta skříně na kanystry v barvě plachty s tmavými linkami lamel, kryt navíjení tmavý, polep designu na pohyblivém
    dílu rolety (Toolbox_Door, svine se s ní), pruh přes zadní líce sloupků Post_L4/R4 a přes zadní příčník (TopCross_6);
    malá výstraha z atlasu nálepek v pravém dolním rohu rolety. Původní polepy rolety (Decal_Lid*) pryč."""
    for o in [o for o in bpy.data.objects if o.name.startswith("Decal_Lid")]:
        bpy.data.objects.remove(o, do_unlink=True)
    tarp, hem = P.material("SDT_Tarp"), P.material("SDT_TarpHem")
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if o.name in ("Toolbox_DoorPanel", "Toolbox_HousingFascia") or o.name.startswith("TopCross_6"):
            o.data.materials[0] = tarp
        elif o.name.startswith("Toolbox_DoorRib"):
            o.data.materials[0] = hem
    door = bpy.data.objects["Toolbox_Door"]
    x0, x1, _, _ = T.TOOLBOX_XY
    y1 = cabinet_y_range()[1]
    zs = (TARP_STRIPE_Z[0] + TARP_STRIPE_Z[1]) / 2
    sh = TARP_STRIPE_Z[1] - TARP_STRIPE_Z[0]
    P.brand_decal_set("rearDoor", "lockupOnDark", ((x0 + x1) / 2, y1, 1.86), (0, 1, 0), (0, 0, 1), 1.75, parent=door,
                      tone=True)
    P.brand_decal_set("rearDoor", "stripe", ((x0 + x1) / 2, y1, zs), (0, 1, 0), (0, 0, 1), x1 - x0, sh, parent=door)
    warn = P.decal_quad("Decal_DoorWarn", (x0 + 0.17, y1, DECK_TOP + 0.035), (-1, 0, 0), (0, 0, 1), 0.10, 0.10, "boxWarn")
    _set_parent(warn, door, warn.matrix_world.copy())
    yr = POST_Y[-1] + POST / 2
    for side, sx in (("L", 1), ("R", -1)):
        px = sx * POST_X
        box(f"RearPostCover_{side}", px - POST / 2, px + POST / 2, yr, yr + 0.004, DECK_TOP, POST_TOP, "SDT_Tarp")
        P.brand_decal_set("rearPosts", "stripe", (px, yr + 0.004, zs), (0, 1, 0), (0, 0, 1), POST, sh, tag=side)
    yc = TOP_Y1 - REAR_CROSS_OFFSET + 0.035
    P.brand_decal_set("rearCross", "stripe", (0, yc, POST_TOP + TOP_BEAM_H / 2), (0, 1, 0), (0, 0, 1), 2 * POST_X, 0.05)


def build_decals():
    """Nálepky z atlasu jako u Middle, posunuté na prodlouženou desku: výstražný pruh na čele předního příčníku (vzadu je místo
    něj pruh designu přes TopCross_6, build_rear), polepky výbavy. Starý nápis SPRAY DRONE SERVICE na horních nosnících
    nahradil malý lockup designu (beamL / beamR, vidět i se srolovanou plachtou)."""
    z0, h = POST_TOP + 0.01, TOP_BEAM_H - 0.02
    w = 2 * (POST_X - POST / 2)
    P.decal_quad("Decal_StripeFront", (-w / 2, TOP_FRONT_Y, z0), (1, 0, 0), (0, 0, 1), w, h, "stripe")
    rz0, rh, rw = DECK_TOP - RAIL_H + 0.03, 0.12, 0.40
    sub = (0.0, 0.0, rw / rh / 16.0, 1.0)
    P.decal_quad("Decal_StripeRearL", (0.70, BASE_Y1, rz0), (-1, 0, 0), (0, 0, 1), rw, rh, "stripe", sub)
    P.decal_quad("Decal_StripeRearR", (-0.30, BASE_Y1, rz0), (-1, 0, 0), (0, 0, 1), rw, rh, "stripe", sub)
    bx = POST_X + POST / 2
    for side, sx in (("L", 1), ("R", -1)):
        P.brand_decal_set(f"beam{side}", "lockupOnDark", (sx * bx, TOP_FRONT_Y + 0.40, POST_TOP + 0.067), (sx, 0, 0), (0, 0, 1),
                          0.40)
    SL.build_equipment_decals(DECK_TOP)


# ---------------------------------------------------------------------------------- teleskopický žebřík
# Dvoudílný hliníkový žebřík bez madel na pravém boku. Rozložený stojí šikmo (pata LAD_FOOT, ~75°), horní díl je vysunutý a nahoře
# má dvě ramena přes lem horní desky (míjí srolovanou roli plachty). Složený leží podélně uvnitř pravého boku mezi Post_R1 a Post_R2
# na dvou hácích. Uzly (lokální X = podél žebříku od paty, Y = napříč, Z = ven z roviny žebříku):
#   ladderHinge  celý žebřík, poloha a natočení (několik <part> za sebou: otočení venku, zasunutí mezi sloupky, spuštění na háky);
#                osy uzlu jsou přeházené (LAD_P: X = dovnitř, Y = napříč, Z = podél), aby v i3d natočení nebylo v gimbal locku,
#                souřadnice žebříku nese až dítě ladderFrame
#   ladderUpper  horní díl, posun po X (teleskop), sdt_mapped
#   ladderArms   ramena na konci horního dílu, sklopí se podél dílu (otočení kolem Y), sdt_mapped
# Řádky animace se ukládají do ladderHinge["sdt_fold_parts"], export je vloží do foldLadder se zástupcem {{TARP_PARTS}}. ladderGrab
# (Middle: madla) zůstává jen jako prázdný uzel kvůli seznamu mapování exportu.
LAD_Y = 1.75
LAD_W = 0.42
LAD_RAIL = (0.045, 0.03)                     # průřez kolejnice: napříč, do hloubky
LAD_INSET = 0.025                            # horní díl je o tolik užší z každé strany
LAD_DEPTH = 0.032                            # horní díl leží před dolním (ven)
LAD_FOOT = Vector((-2.02, LAD_Y, 0.0))
LAD_TOP = Vector((-1.29, LAD_Y, 2.76))
LAD_LEN = (LAD_TOP - LAD_FOOT).length
LAD_OVERLAP = 0.10
LAD_SEC = (LAD_LEN + LAD_OVERLAP) / 2        # délka dílu = délka složeného žebříku (musí se vejít mezi Post_R1 a Post_R2)
LAD_SLIDE = LAD_LEN - LAD_SEC
LAD_RISER = 0.075                            # rameno: prodloužení kolejnice nad lem desky
LAD_LIP_X = -(TOP_W / 2 - 0.035)             # vnitřní líc pravého lemu desky
LAD_FOOT_T = 0.02                            # gumová patka pod kolejnicí
# pata složeného žebříku (dolní díl x -0,933..-0,903, horní -0,965..-0,935); od patky po rameno 1,51 m mezi Post_R1 a Post_R2
LAD_STOW = Vector((-0.918, POST_Y[1] + POST / 2 + LAD_FOOT_T + 0.003, 1.27))
# mezipolohy paty při zasouvání: venku natočený do složené polohy (nad blatníkem), u sloupků, dole na úrovni háků
LAD_STAGES = [Vector((-1.20, LAD_STOW.y, 1.45)), Vector((-0.988, LAD_STOW.y, 1.45)), Vector((-0.988, LAD_STOW.y, 1.27))]
LAD_HOLDER_Y = (1.40, 2.20)
LAD_ARM_TIME = (2.0, 2.12)
LAD_TELE_TIME = (2.10, 2.25)
LAD_SWING_TIME = (2.25, 2.45)
LAD_STAGE_TIMES = (2.52, 2.56, 2.60)         # žebřík je uvnitř před 2,6 s, pak se zavírají plachty
LAD_SWING_STEPS = 3
LADDER_GRAB_TIME = (2.0, 2.6)
_A = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))   # Blender -> i3d (BAKE_TRANSFORMS)


def _lad_frame(origin, along, across):
    a, c = Vector(along).normalized(), Vector(across).normalized()
    m = Matrix((a, c, a.cross(c))).transposed().to_4x4()
    m.translation = origin
    return m


LAD_DEPLOYED = _lad_frame(LAD_FOOT, LAD_TOP - LAD_FOOT, (0, 1, 0))
LAD_P = Matrix(((0, 0, 1, 0), (0, 1, 0, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))   # ladderHinge = rám žebříku @ LAD_P


def _lad_stowed(origin):
    return _lad_frame(origin, (0, 1, 0), (0, 0, -1))


def ladder_keys():
    """[(čas, matice ladderHinge ve světě)] od rozloženého (2,25 s, po zasunutí teleskopu) po složený (2,6 s). Otočení venku
    v LAD_SWING_STEPS krocích (střed dílu po přímce, natočení slerp), pak přímočaré posuny."""
    half = LAD_SEC / 2
    q0, q1 = LAD_DEPLOYED.to_quaternion(), _lad_stowed(LAD_STAGES[0]).to_quaternion()
    c0 = LAD_DEPLOYED @ Vector((half, 0, 0))
    c1 = _lad_stowed(LAD_STAGES[0]) @ Vector((half, 0, 0))
    t0, t1 = LAD_SWING_TIME
    keys = []
    for k in range(LAD_SWING_STEPS + 1):
        s = k / LAD_SWING_STEPS
        q = q0.slerp(q1, s)
        m = q.to_matrix().to_4x4()
        m.translation = c0.lerp(c1, s) - q @ Vector((half, 0, 0))
        keys.append((t0 + (t1 - t0) * s, m))
    for t, origin in zip(LAD_STAGE_TIMES, LAD_STAGES[1:] + [LAD_STOW]):
        keys.append((t, _lad_stowed(origin)))
    return keys


def _i3d_pose(m, prev=None):
    """(posun, natočení v radiánech) uzlu pod kořenem vleku v i3d; natočení navazuje na prev (Euler bez skoků o 360°)."""
    b = _A @ m @ _A.inverted()
    e = b.to_3x3().to_euler("XYZ", prev) if prev is not None else b.to_3x3().to_euler("XYZ")
    return b.to_translation(), e


def _deg(e):
    return P.i3d_fmt([math.degrees(a) for a in e])


def _arm_fold_angle():
    """Sklopení ramen (kolem lokální Y ladderArms) z vodorovné polohy přes lem do polohy podél horního dílu, dlouhou cestou
    přes vrch (krátká by vedla přes desku)."""
    a = LAD_DEPLOYED.inverted().to_3x3() @ Vector((1, 0, 0))     # vodorovně dovnitř v souřadnicích žebříku
    short = math.atan2(a.cross(Vector((-1, 0, 0))).y, a.dot(Vector((-1, 0, 0))))
    return short - 2 * math.pi if short > 0 else short + 2 * math.pi


def ladder_fold_rows():
    rows = []
    t0, t1 = LAD_ARM_TIME
    # rotace o úhel kolem osy Y Blenderu je v i3d rotace o -úhel kolem Z (osa Y -> -Z)
    rows.append(f'            <part node="ladderArms" startTime="{t0:g}" endTime="{t1:g}" startRot="0 0 0" '
                f'endRot="0 0 {-math.degrees(_arm_fold_angle()):.3f}"/>')
    t0, t1 = LAD_TELE_TIME
    rows.append(f'            <part node="ladderUpper" startTime="{t0:g}" endTime="{t1:g}" '
                f'startTrans="{P.i3d_fmt(P.i3d_vec((LAD_SLIDE, 0, LAD_DEPTH)))}" '
                f'endTrans="{P.i3d_fmt(P.i3d_vec((0, 0, LAD_DEPTH)))}"/>')
    prev = None
    poses = []
    for t, m in ladder_keys():
        tr, e = _i3d_pose(m @ LAD_P, prev)
        prev = e
        poses.append((t, tr, e))
    for (ta, tra, ea), (tb, trb, eb) in zip(poses, poses[1:]):
        rows.append(f'            <part node="ladderHinge" startTime="{ta:g}" endTime="{tb:g}" startTrans="{P.i3d_fmt(tra)}" '
                    f'endTrans="{P.i3d_fmt(trb)}" startRot="{_deg(ea)}" endRot="{_deg(eb)}"/>')
    return "\n".join(rows)


def _local(obj, parent):
    """Mesh postavený v souřadnicích uzlu parent (jako by byl v počátku) zavěsí pod parent."""
    m = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = m
    return obj


def _ladder_section(tag, node, inset, mat="SDT_Alu"):
    """Jeden díl: dvě kolejnice a příčky v souřadnicích uzlu (X podél od 0 do LAD_SEC). Vrací osu kolejnice napříč."""
    rw, rd = LAD_RAIL
    yo = LAD_W / 2 - inset - rw / 2
    for k, s in enumerate((-1, 1)):
        _local(box(f"Ladder_{tag}Rail{k}", 0.0, LAD_SEC, s * yo - rw / 2, s * yo + rw / 2, -rd / 2, rd / 2, mat), node)
    for r in range(int(LAD_SEC / 0.28)):
        x = 0.14 + r * 0.28
        _local(box(f"Ladder_{tag}Rung{r}", x - 0.016, x + 0.016, -yo + rw / 2, yo - rw / 2, -0.012, 0.012, mat), node)
    return yo


def build_ladder():
    """Teleskopický žebřík v rozložené poloze (stav v i3d), pevné háky složeného žebříku uvnitř pravého boku. Vrací ladderHinge."""
    vis = bpy.data.objects[ROOT_NAME]
    hinge = _group("ladderHinge", vis)
    hinge.matrix_world = LAD_DEPLOYED @ LAD_P
    frame = _group("ladderFrame", hinge)
    frame.matrix_basis = LAD_P.inverted()
    upper = _group("ladderUpper", frame)
    upper.matrix_basis = Matrix.Translation((LAD_SLIDE, 0, LAD_DEPTH))
    upper["sdt_mapped"] = 1
    arms = _group("ladderArms", upper)
    arms.matrix_basis = Matrix.Translation((LAD_SEC, 0, 0))
    arms["sdt_mapped"] = 1
    bpy.context.view_layer.update()

    rw, rd = LAD_RAIL
    yo = _ladder_section("Low", frame, 0.0)
    for k, s in enumerate((-1, 1)):
        _local(box(f"Ladder_Foot{k}", -LAD_FOOT_T, 0.0, s * yo - rw / 2 - 0.004, s * yo + rw / 2 + 0.004, -rd / 2 - 0.004,
                   rd / 2 + 0.004, "SDT_Rubber"), frame)
        _local(box(f"Ladder_Guide{k}", LAD_SEC - 0.07, LAD_SEC, s * yo - rw / 2 - 0.006, s * yo + rw / 2 + 0.006,
                   -rd / 2 - 0.004, LAD_DEPTH + rd / 2 + 0.004, "SDT_Steel"), frame)
    yu = _ladder_section("Up", upper, LAD_INSET)
    for k, s in enumerate((-1, 1)):
        _local(box(f"Ladder_UpGuide{k}", 0.0, 0.06, s * yu - rw / 2 - 0.004, s * yu + rw / 2 + 0.004, -LAD_DEPTH - rd / 2,
                   rd / 2 + 0.004, "SDT_Steel"), upper)
    # ramena: prodloužení kolejnice, vodorovně přes lem desky dovnitř a hák za lem (stavěno ve světě v rozložené poloze)
    aw = arms.matrix_world.copy()
    for k, s in enumerate((-1, 1)):
        _local(box(f"Ladder_ArmRiser{k}", 0.0, LAD_RISER, s * yu - 0.018, s * yu + 0.018, -rd / 2, rd / 2, "SDT_Alu"), arms)
        p = aw @ Vector((LAD_RISER, s * yu, 0))
        parts = [box(f"Ladder_ArmBar{k}", p.x - 0.02, LAD_LIP_X + 0.022, p.y - 0.018, p.y + 0.018, p.z - 0.012, p.z + 0.012,
                     "SDT_Alu"),
                 box(f"Ladder_ArmHook{k}", LAD_LIP_X + 0.002, LAD_LIP_X + 0.022, p.y - 0.018, p.y + 0.018, TOP_SURF + 0.01,
                     p.z + 0.012, "SDT_Alu"),
                 box(f"Ladder_ArmPad{k}", LAD_LIP_X - 0.04, LAD_LIP_X, p.y - 0.02, p.y + 0.02, p.z - 0.016, p.z - 0.012,
                     "SDT_Rubber")]
        for o in parts:
            o.matrix_world = aw.inverted() @ o.matrix_world
            _local(o, arms)
    # háky složeného žebříku: svislá lišta za ním (na palubě), spodní a horní ozub
    for k, y in enumerate(LAD_HOLDER_Y):
        box(f"LadderHolder_{k}Bar", -0.900, -0.886, y - 0.02, y + 0.02, DECK_TOP, 1.515, "SDT_Frame")
        box(f"LadderHolder_{k}Low", -0.97, -0.886, y - 0.02, y + 0.02, 1.025, 1.045, "SDT_Frame")
        box(f"LadderHolder_{k}High", -0.97, -0.886, y - 0.02, y + 0.02, 1.495, 1.515, "SDT_Frame")
    _group("ladderGrab", vis, tuple(LAD_DEPLOYED.translation))
    hinge["sdt_fold_parts"] = ladder_fold_rows()
    return hinge


def ladder_grab_fold_angle():
    return 0.0


def _shape_local(name, parent, x0, x1, y0, y1, z0, z1, group_mask, **props):
    obj = _local(box(name, x0, x1, y0, y1, z0, z1, "SDT_Frame"), parent)
    obj.display_type = "WIRE"
    obj.hide_render = True
    return _physics(obj, collisionFilterGroup=str(group_mask[0]), collisionFilterMask=str(group_mask[1]), nonRenderable=True,
                    **props)


def build_ladder_collision(pivot):
    """Kolize žebříku: deska v rovině každého dílu (dolní pod ladderHinge od 0,27 m nad zemí, horní pod ladderUpper)."""
    half = LAD_W / 2 + 0.03
    child = dict(compoundChild=True, density=0.001)
    _shape_local("colLadder", bpy.data.objects["ladderFrame"], 0.27, LAD_SEC, -half, half, -0.05, 0.05, COL_VEHICLE, **child)
    return _shape_local("colLadderUpper", bpy.data.objects["ladderUpper"], 0.0, LAD_SEC, -half, half, -0.05, 0.05,
                        COL_VEHICLE, **child)


def build_ladder_trigger(pivot):
    """Spouštěč lezení: kvádr kolem rozloženého žebříku a před ním, nahoře přes lem desky. Je pod ladderHinge, ale natočený
    jako vlek (v rozložené poloze), stejně jako u Middle."""
    half = LAD_W / 2 + 0.05
    trig = box("ladderTrigger", LAD_FOOT.x - 0.75, LAD_LIP_X + 0.07, LAD_Y - half, LAD_Y + half, 0.05, TOP_SURF + 0.70,
               "SDT_Frame")
    trig.data.transform(trig.matrix_world)
    trig.parent = bpy.data.objects["ladderFrame"]
    trig.matrix_parent_inverse = Matrix.Identity(4)
    trig.matrix_basis = LAD_DEPLOYED.inverted()
    trig.display_type = "WIRE"
    trig.hide_render = True
    return _physics(trig, collisionFilterGroup=str(COL_TRIGGER[0]), collisionFilterMask=str(COL_TRIGGER[1]),
                    nonRenderable=True, kinematic=True, compound=True, trigger=True)


def _key_at(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (ta, ma), (tb, mb) in zip(keys, keys[1:]):
        if t <= tb:
            s = (t - ta) / (tb - ta)
            q = ma.to_quaternion().slerp(mb.to_quaternion(), s)
            m = q.to_matrix().to_4x4()
            m.translation = ma.translation.lerp(mb.translation, s)
            return m
    return keys[-1][1]


def set_ladder(t):
    """Náhled: 0 = rozložený (stav v i3d), 1 = složený uvnitř boku; mezi tím jako animace foldLadder 2,0-2,6 s."""
    tt = LADDER_GRAB_TIME[0] + (LADDER_GRAB_TIME[1] - LADDER_GRAB_TIME[0]) * t

    def frac(span):
        return min(max((tt - span[0]) / (span[1] - span[0]), 0.0), 1.0)
    arms, upper, hinge = (bpy.data.objects[n] for n in ("ladderArms", "ladderUpper", "ladderHinge"))
    arms.matrix_basis = Matrix.Translation((LAD_SEC, 0, 0)) @ Matrix.Rotation(_arm_fold_angle() * frac(LAD_ARM_TIME), 4, "Y")
    upper.matrix_basis = Matrix.Translation((LAD_SLIDE * (1 - frac(LAD_TELE_TIME)), 0, LAD_DEPTH))
    hinge.matrix_world = _key_at(ladder_keys(), max(tt, LAD_SWING_TIME[0])) @ LAD_P
    bpy.context.view_layer.update()


# --------------------------------------------------------------- relé tyče ve skříňce a displej plánovače
# Skříňka na čtyři relé tyče na levém boku celá mezi Post_L1 a Post_L2, přístupná z boku (otevřená ven, dva popruhy), tyče stojí
# svisle hlavou nahoru (relaySlot1-4 v ose tyče, x > 0 = vyndaná tyč se postaví vlevo, SprayDroneRelaySlots.getSpawnLocal)
RELAY_BOX = (0.78, 0.96, 1.22, 1.98, DECK_TOP, 2.50)       # x0 x1 y0 y1 z0 z1 (také colRelayBox)
RELAY_POLE_X = 0.88
RELAY_POLE_FOOT = DECK_TOP + 0.018
PLANNER_MAX = ((0.93, -0.68, 1.50), 8.0)                   # uvnitř hned za Post_L0, obrazovkou ven (+X), mírně nahoru


def build_relay_holders():
    x0, x1, y0, y1, z0, z1 = RELAY_BOX
    mat, w = "SDT_PaintDark", 0.012
    box("RelayBox_Floor", x0, x1, y0, y1, z0, z0 + 0.01, mat)
    box("RelayBox_Back", x0, x0 + w, y0, y1, z0, z1, mat)
    box("RelayBox_Top", x0, x1, y0, y1, z1 - 0.02, z1, mat)
    for k, y in enumerate((y0, y1 - w)):
        box(f"RelayBox_End{k}", x0, x1, y, y + w, z0, z1, mat)
    for k in range(3):
        y = y0 + (y1 - y0) * (k + 1) / 4
        box(f"RelayBox_Div{k}", x0, x0 + 0.11, y - 0.004, y + 0.004, z0, z1, mat)
    for k, z in enumerate((1.35, 2.05)):
        box(f"RelayBox_Strap{k}", x1 - 0.008, x1, y0, y1, z - 0.02, z + 0.02, "SDT_TarpStrap")
        for n, (ya, yb) in enumerate(((y0, y0 + 0.03), (y1 - 0.03, y1))):
            box(f"RelayBox_Buckle{k}{n}", x1 - 0.012, x1 + 0.004, ya, yb, z - 0.028, z + 0.028, "SDT_Steel")
    vis = bpy.data.objects[ROOT_NAME]
    for k in range(4):
        y = y0 + (y1 - y0) * (k + 0.5) / 4
        P.relay_pole_mockup(k + 1, vis, (RELAY_POLE_X, y, RELAY_POLE_FOOT + RELAY_POLE_LEN), (RELAY_POLE_X, y, RELAY_POLE_FOOT))


def build_planner_tablet():
    """Displej plánovače uvnitř hned za Post_L0 (obrazovka ven, +X): tenký držák na zadní stěně sloupku, rameno dovnitř
    (za kabely nabíječky, které vedou po vnitřní straně sloupku) a podél boku k patce displeje."""
    (cx, cy, cz), tilt = PLANNER_MAX
    a = math.radians(tilt)
    disp, node, back = planner_display((cx, cy, cz), (math.cos(a), 0, math.sin(a)), (-math.sin(a), 0, math.cos(a)))
    px0, px1 = POST_X - POST / 2, POST_X + POST / 2
    yr = POST_Y[0] + POST / 2
    ya = yr + 0.008
    bx = back.x
    parts = [box("Planner_PostPlate", px0 + 0.005, px1 - 0.005, yr, yr + 0.008, cz - 0.07, cz + 0.07, "SDT_Frame"),
             box("Planner_ArmIn", bx - 0.01, px0 + 0.03, ya, ya + 0.02, back.z - 0.018, back.z + 0.018, "SDT_Frame"),
             box("Planner_ArmAlong", bx - 0.01, bx + 0.008, ya, cy, back.z - 0.018, back.z + 0.018, "SDT_Frame"),
             P.chamfer_box("Planner_Joint", bx - 0.012, bx + 0.012, cy - 0.028, cy + 0.028, back.z - 0.028, back.z + 0.028,
                           "SDT_PaintDark", 0.006)]
    for n, dz in enumerate((-0.045, 0.045)):
        parts.append(P.tube(f"Planner_Bolt{n}", (POST_X, yr + 0.008, cz + dz), (POST_X, yr + 0.016, cz + dz), 0.008,
                            "SDT_Steel", segments=6))
    P.merge("plannerMount", parts)
    return node


def build():
    coll, vis = P.begin(COLLECTION_NAME, ROOT_NAME)
    build_chassis()
    build_drawbar()
    build_upper_structure()
    rebuild_top_deck()
    pivot = build_ladder()
    build_ladder_collision(pivot)
    build_ladder_trigger(pivot)
    build_equipment()
    build_i3d_structure(vis)
    move_to_preview(("Wheel_", "Rim_", "HubCap_"))
    build_drones()
    build_drone_unit(DRONE_VARIANTS, PAD_Y[0], "")
    build_drone_unit(DRONE_VARIANTS_B, PAD_Y[1], "2")
    rotate_drones(DRONE_VARIANTS, PAD_Y[0])
    build_charger_set()
    build_radio_gear_max()
    build_charger_cable()
    build_both_hoses()
    build_decals()
    build_relay_holders()
    build_planner_tablet()
    build_tarps()
    build_rear()
    set_tarps(1.0)
    set_ladder(0.0)
    bpy.context.view_layer.update()
    build_dirt_uvs()
    print(f"{COLLECTION_NAME}: {len(coll.objects)} objektů")


if __name__ == "__main__":
    build()
