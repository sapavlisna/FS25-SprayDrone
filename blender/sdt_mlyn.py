"""Mlýnkový vozík na vápno: široký a krátký jednonápravový vlek. Vpředu v jedné řadě podél X: cyklónová nádobka na jemné vápno
(vpravo, -X), kladivový mlýn s osou podél X uprostřed a dieselový motor s palivovou nádrží vlevo (+X). Vzadu velká nádoba
na hrubé vápno, ze které vede šnek šikmo dopředu do vstupu mlýna. Hadicová spojka (Storz) je na pravém boku (-X).

Osa vleku: vpředu -Y, Z nahoru, počátek na zemi uprostřed šířky. Kola vně rámu (jako Mini). Oj s kulovou spojkou se zapřahá za
auto nebo za kulový tažný věšák na zádi Maxu (sdt_lime.build_rear_hitch).

Tento soubor je zatím jen model k odsouhlasení; uzly pro hru (fill root, hrdlo nafty, články hadice) se přidají až po schválení.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import parts_lib as PL
import sdt_parts as P
import sdt_rims as RIMS
import sdt_tanks as T
from sdt_tanks import Mesh, V, frame

TAU = 2.0 * math.pi

WHEEL_R = 0.354          # pneu 280/70 R15 jako u Mini a Middle
WHEEL_W = 0.28
TIRE_R = 0.39            # skutečný poloměr pneu 280/70 R15 ve hře
TIRE_Y_OFFSET = 0.031
FENDER_R = TIRE_R + 0.045
AXLE_Z = WHEEL_R + TIRE_Y_OFFSET     # osa kola ve hře
COUPLER_Z = 0.58         # výška koule tažného věšáku Maxu = střed kulové spojky vozíku
TRACK_X = 1.08           # osa kola vně rámu
AXLE_Y = 1.38
DECK_Z = 0.60            # horní plocha paluby
DECK_HX = 0.90
RAIL_X = 0.62            # osa podélníků
Y_FRONT = -0.78          # čelo rámu
Y_REAR = 2.31            # zadní okraj rámu
DRAWBAR_L = 1.40                         # délka oje před čelem rámu
DRAWBAR_TIP_Y = Y_FRONT - DRAWBAR_L - 0.03     # střed kulové spojky
DRAWBAR_Y0 = Y_FRONT - 0.08              # čelo čelního příčníku, odtud ramena oj
DRAWBAR_Z0 = 0.54                        # osa ramen u příčníku
DRAWBAR_SLOPE = 0.0645                   # celá oj leží v jedné rovině, která stoupá k hlavě (osa hlavy 0,62 m)
DRAWBAR_MERGE_Y = Y_FRONT - 0.62         # kde se ramena sbíhají do jedné trubky
JOCKEY_X = 0.115                         # osa nohy podpěrného kolečka vlevo od trubky oje
JOCKEY_Y = Y_FRONT - 0.78
JOCKEY_LIFT = 0.23                       # o kolik se kolečko zvedne po zapřažení (dolní konec vnější trubky nohy je 0,43 m nad zemí)
_DB_TH = math.atan(DRAWBAR_SLOPE)
_DB_F = V(0.0, -math.cos(_DB_TH), math.sin(_DB_TH))   # směr oje dopředu
_DB_N = V(0.0, math.sin(_DB_TH), math.cos(_DB_TH))    # kolmice k rovině oje (nahoru)
DRAWBAR_Z = DRAWBAR_Z0 + DRAWBAR_SLOPE * (DRAWBAR_Y0 - JOCKEY_Y)     # osa trubky oje v místě kolečka

HOPPER_CX, HOPPER_CY = 0.0, 1.43   # střed velké nádoby na hrubé vápno
HOPPER_OUT_Z = 1.00      # spodek nádoby (výsyp) je nad šnekem
HOPPER_SLOPE_Z = 1.60    # dolní hranice plnicího kvádru exactFillRootNode (build_trailer_mill)
HOPPER_RIM_Z = 2.05      # přechod ze šikmých stěn do svislého lemu
HOPPER_TOP_Z = 2.40
HOPPER_HX, HOPPER_HY = 0.86, 0.78
AUGER_BOOT_Z = DECK_Z + 0.16       # osa spodku šneku: trubka leží na paluze vleku

ROW_Y = -0.15            # osa řady bin - mlýn - motor
MILL_X, MILL_Z = -0.08, 0.80   # střed mlýna (osa podél X)
MILL_R = 0.24
MILL_HL = 0.25           # půl délky mlýna
ENG_X0, ENG_X1 = 0.28, 0.80    # motor vlevo od mlýna
ENG_HW = 0.21            # půl šířky bloku motoru (po Y)
ENG_CASE_X0, ENG_CASE_X1 = 0.31, 0.62   # klikovka motoru
ENG_CYL_X = 0.47         # osa válce
ZH0 = 1.14               # spodek hlavy válce
ENG_AIR_X = 0.355        # osa vzduchového filtru
ENG_FRONT_Y = ROW_Y - 0.15       # přední stěna klikovky (k nádrži)
ENG_BACK_Y = ROW_Y + 0.15        # zadní stěna klikovky (k baterii)
STARTER_PLUS = V(0.40, ENG_BACK_Y + 0.04, 0.86)    # svorka solenoidu startéru, sem jde červený kabel z baterie
STARTER_MINUS = V(0.54, ENG_BACK_Y, 0.74)          # kostra na klikovce, sem jde černý
AUGER_P0 = V(0.0, HOPPER_CY - 0.10, AUGER_BOOT_Z)   # spodek šneku na paluze pod výsypem nádoby
AUGER_P1 = V(MILL_X, ROW_Y - 0.04, 1.36)                     # konec šneku nad vstupem do mlýna

BIN_XY = (-0.68, ROW_Y)  # nádobka na jemné vápno (cyklón) vpravo od mlýna
BIN_R = 0.19
BIN_CONE_Z0 = 0.78
BIN_CONE_H = 0.28
BIN_BODY_H = 0.50
PORT_Z = 0.70            # osa hadicové spojky
PORT_X = -1.00           # čelo spojky (směr -X), za lemem paluby
MILL_OUT_X = MILL_X - MILL_HL - 0.085    # čelo příruby výstupního hrdla mlýna (směr -X)

# výsypná roura na plnění big bagu (docs/NAVRH-mlyn-plneni-bigbagu.md): rozdělovač na výstupu pod nádobkou, potrubí po palubě
# do stoupačky v pravém zadním rohu, otočný kloub se svislou osou, vodorovné rameno a plnicí hlava; rameno se staví v přepravní
# poloze (podél pravého boku násypky dopředu, -Y), ve hře se otáčí kolem svislé osy (millSpoutPivot)
VALVE_C = V(-0.80, ROW_Y, PORT_Z)        # střed klapkového rozdělovače na vodorovné trubce ke spojce
VALVE_BRANCH_X = -0.765                  # odbočka k rouře (mezi nohou stojanu nádobky a protizávažím klapky)
VALVE_SHAFT_Y = ROW_Y - 0.25             # konec hřídele klapky vpředu: osa otáčení páky
VALVE_LEVER_L = 0.30                     # páka: vodorovně ven (-X) = hadice, svisle nahoru = roura
SPOUT_PIPE_R = 0.048                     # DN 100
SPOUT_DECK_X = -0.67                     # potrubí po palubě mezi lemem paluby a nohama násypky
SPOUT_DECK_Z = 0.68
SPOUT_X, SPOUT_Y = -1.03, 2.26           # svislá osa otočného kloubu
SPOUT_ARM_Z = 1.62                       # osa vodorovného ramene
SPOUT_ARM_L = 0.80                       # od osy kloubu ke svislé spádové trubce
SPOUT_HEAD_Z = 1.02                      # osa vodorovného ústí plnicí hlavy: z boku vaku pod horní hranou látky (1,10-1,18 m)
SPOUT_MOUTH_L = SPOUT_ARM_L + 0.21       # od osy kloubu k čelu límce (koleno, nátrubek, kužel, límec míří od kloubu ven)
SPOUT_BEARING_Z = 1.46                   # spodek ložiska kloubu

FUEL_Y, FUEL_Z, FUEL_R = ROW_Y - 0.43, DECK_Z + 0.42, 0.14   # nádrž na naftu před motorem


def ports():
    """Hadicová spojka (směr -X), kulová spojka na oji a hrdlo nafty; pro napojení hadice a pozdější uzly."""
    return {"hose_port": V(PORT_X, BIN_XY[1], PORT_Z), "hose_dir": V(-1, 0, 0),
            "hitch": V(0.0, DRAWBAR_TIP_Y, DECK_Z - 0.07),
            "diesel_neck": V((ENG_X0 + ENG_X1) / 2 + 0.03, FUEL_Y, FUEL_Z + FUEL_R + 0.098)}


def _arc_prism(mesh, y_c, z_c, r0, r1, a0, a1, x0, x1, mat, steps=18):
    """Pás po oblouku kolem osy X (blatník): úhel od svislice nahoru, kladný směrem k +Y."""
    t = bmesh.new()
    rings = []
    for k in range(steps + 1):
        a = a0 + (a1 - a0) * k / steps
        dy, dz = math.sin(a), math.cos(a)
        rings.append([t.verts.new((x, y_c + r * dy, z_c + r * dz)) for r, x in ((r0, x0), (r1, x0), (r1, x1), (r0, x1))])
    for lo, hi in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            t.faces.new((lo[i], lo[j], hi[j], hi[i])).smooth = True
    t.faces.new(rings[0][::-1])
    t.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(t, faces=t.faces)
    mesh._absorb(t, Matrix.Identity(4), mat)


def build_chassis():
    f = Mesh("Mill_Chassis")
    for sx in (-1, 1):
        f.box(sx * RAIL_X - 0.045, sx * RAIL_X + 0.045, Y_FRONT, Y_REAR, DECK_Z - 0.15, DECK_Z - 0.02, "SDT_Frame", bevel=0.008)
        f.box(sx * DECK_HX - 0.018, sx * DECK_HX + 0.018, Y_FRONT, Y_REAR, DECK_Z - 0.01, DECK_Z + 0.06, "SDT_Frame", bevel=0.004)
    f.box(-DECK_HX, DECK_HX, Y_FRONT, Y_REAR, DECK_Z - 0.03, DECK_Z, "SDT_DeckPlate", bevel=0.003)
    n = 8
    for k in range(n):
        y = Y_FRONT + 0.05 + (Y_REAR - Y_FRONT - 0.10) * k / (n - 1)
        f.box(-RAIL_X, RAIL_X, y - 0.04, y + 0.04, DECK_Z - 0.13, DECK_Z - 0.03, "SDT_Frame", bevel=0.004)
    f.box(-DECK_HX, DECK_HX, Y_FRONT - 0.016, Y_FRONT, DECK_Z - 0.01, DECK_Z + 0.06, "SDT_Frame", bevel=0.004)
    # zadní čelo se zebrou
    n = 12
    w = 2 * DECK_HX / n
    for k in range(n):
        f.box(-DECK_HX + k * w, -DECK_HX + (k + 1) * w, Y_REAR, Y_REAR + 0.012, DECK_Z - 0.14, DECK_Z + 0.06,
              "SDT_TapeRed" if k % 2 == 0 else "SDT_TapeWhite")
    f.box(-DECK_HX, DECK_HX, Y_REAR - 0.004, Y_REAR, DECK_Z - 0.15, DECK_Z - 0.14, "SDT_Frame")
    # zadní svítilny, odrazky a držák SPZ
    for sx in (-1, 1):
        f.box(sx * 0.78 - 0.05, sx * 0.78 + 0.05, Y_REAR + 0.012, Y_REAR + 0.034, DECK_Z - 0.10, DECK_Z - 0.02, "SDT_LampRed",
              bevel=0.004)
        f.box(sx * 0.78 - 0.03, sx * 0.78 + 0.03, Y_REAR + 0.012, Y_REAR + 0.024, DECK_Z + 0.01, DECK_Z + 0.05, "SDT_LampAmber")
    f.box(-0.12, 0.12, Y_REAR + 0.034, Y_REAR + 0.042, DECK_Z - 0.10, DECK_Z - 0.04, "SDT_PaintWhite")
    # náprava, listová pružina, třmeny
    ay = AXLE_Y
    f.box(-(TRACK_X - 0.13), TRACK_X - 0.13, ay - 0.045, ay + 0.045, AXLE_Z - 0.045, AXLE_Z + 0.045, "SDT_Frame", bevel=0.006)
    for sx in (-1, 1):
        x = sx * RAIL_X
        f.box(x - 0.04, x + 0.04, ay - 0.48, ay + 0.48, AXLE_Z + 0.050, AXLE_Z + 0.082, "SDT_Frame", bevel=0.004)
        for dy in (-0.52, 0.52):
            f.box(x - 0.045, x + 0.045, ay + dy - 0.03, ay + dy + 0.03, AXLE_Z + 0.05, DECK_Z - 0.15, "SDT_Frame", bevel=0.004)
        for dy in (-0.07, 0.07):
            f.cyl(V(x - 0.06, ay + dy, AXLE_Z + 0.115), V(x - 0.06, ay + dy, AXLE_Z - 0.07), 0.009, "SDT_Steel", seg=8)
            f.cyl(V(x + 0.06, ay + dy, AXLE_Z + 0.115), V(x + 0.06, ay + dy, AXLE_Z - 0.07), 0.009, "SDT_Steel", seg=8)
        f.box(x - 0.075, x + 0.075, ay - 0.10, ay + 0.10, AXLE_Z + 0.082, AXLE_Z + 0.100, "SDT_Frame", bevel=0.003)
        hub = V(sx * (TRACK_X - WHEEL_W / 2 - 0.04), ay, AXLE_Z)
        f.cyl(hub, hub + V(sx * 0.06, 0, 0), 0.075, "SDT_CastIron", seg=24)
    # blatníky: oblouk kolem osy kola ve hře (střed o TIRE_Y_OFFSET výš, pneu poloměru TIRE_R) a dvě šikmé vzpěry k lemu paluby
    for sx in (-1, 1):
        x0, x1 = TRACK_X - WHEEL_W / 2 - 0.025, TRACK_X + WHEEL_W / 2 + 0.035
        a = (min(x0, x1) * sx, max(x0, x1) * sx)
        zc = AXLE_Z
        _arc_prism(f, ay, zc, FENDER_R, FENDER_R + 0.012, math.radians(-78), math.radians(78), min(a), max(a), "SDT_Frame")
        xs = sx * (TRACK_X - WHEEL_W / 2 - 0.02)
        for dy in (-0.30, 0.30):
            top = V(xs, ay + dy, zc + FENDER_R * math.cos(math.asin(min(abs(dy) / FENDER_R, 0.95))))
            f.cyl(top, V(sx * (DECK_HX + 0.02), ay + dy * 1.2, DECK_Z + 0.04), 0.012, "SDT_Frame", seg=8)
    f.finish()


def build_wheels():
    for sx, side in ((1, "L"), (-1, "R")):
        c = V(sx * TRACK_X, AXLE_Y, AXLE_Z)
        mirror = PL.Place(mirror_x=True) if sx < 0 else None       # pravé kolo je zrcadlový obraz levého (jeden díl)
        PL.call(RIMS.build_tire, "Wheel", 1, TIRE_R, WHEEL_W, RIMS.RIMS["R15"]["bead"], at=mirror,
                rename=lambda n, side=side: f"Mill_Wheel{side}").matrix_world = Matrix.Translation(c)
        PL.call(RIMS.build_rim, "R15", "Rim", 1, at=mirror, rename=lambda n, side=side: f"Mill_Rim{side}").matrix_world = Matrix.Translation(c)


def _dp(x, d, h=0.0):
    """Bod v rovině oje: x do strany, d podél oje dopředu od čela příčníku, h kolmo k rovině oje (nahoru)."""
    return V(x, DRAWBAR_Y0, DRAWBAR_Z0) + _DB_F * d + _DB_N * h


def _spline(pts, n=5):
    """Catmull-Rom přes řídicí body, n dílků na úsek."""
    pts = [Vector(p) for p in pts]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def _clip(m, c, t, n, r, mat="SDT_Steel"):
    """Pásková příchytka kabelu: pásek přes kabel o poloměru r (střed c, směr t) a dvě nožky přivařené k ploše s kolmicí n."""
    t, n = Vector(t).normalized(), Vector(n).normalized()
    across = n.cross(t).normalized()
    th = 0.0035
    m.obox((0.026, th, 0.014), frame(c + n * (r + th / 2), t, across), mat)
    for s in (-1, 1):
        m.obox((th, 2 * r + th, 0.014), frame(c + n * (th / 2) + across * (s * 0.0125), t, across), mat)


def build_drawbar():
    """Svařená oj jako u jednonápravových přívěsů s najížděcí brzdou: čelní příčník na koncích rámu, dvě ramena do V z čtyřhranných profilů,
    příčná vzpěra, styčníkové plechy, jedna trubka s najížděcím zařízením (pozinkované pouzdro, měch), litá hlava kulové spojky s pákou a
    bezpečnostním lankem, podpěrné kolečko na svěrné objímce s klikou, ruční brzda a kabel zástrčky vedený po oji na příchytkách.
    Celá oj leží v rovině, která mírně stoupá k hlavě (DRAWBAR_SLOPE). Střed koule: DRAWBAR_TIP_Y, COUPLER_Z."""
    d = Mesh("Mill_Drawbar")
    F, N, EX = _DB_F, _DB_N, V(1, 0, 0)
    cs = math.cos(_DB_TH)

    def pbox(x, dd, h, sx, sf, sn, mat, bevel=0.0):
        d.obox((sx, sn, sf), frame(_dp(x, dd, h), F, EX), mat, bevel)

    dm = (DRAWBAR_Y0 - DRAWBAR_MERGE_Y) / cs                 # vzdálenost sbíhání ramen
    by = DRAWBAR_TIP_Y
    yr = by + 0.14                                            # zadní čelo hlavy
    dh = (DRAWBAR_Y0 - yr) / cs
    d_b0 = dh - 0.14                                          # začátek měchu = čelo pouzdra
    hr = d_b0 - 0.29                                          # zadní čelo pouzdra
    hz = DRAWBAR_Z0 + DRAWBAR_SLOPE * (DRAWBAR_Y0 - yr)       # osa hlavy
    zb = COUPLER_Z
    ax0, ax1 = 0.44, 0.02

    def arm_x(dd):
        return ax0 + (ax1 - ax0) * (dd + 0.03) / (dm + 0.03)

    # čelní příčník na koncích podélníků, ramena do V z profilů 50x50, vzpěra mezi rameny
    d.box(-0.665, 0.665, DRAWBAR_Y0, Y_FRONT, 0.455, 0.575, "SDT_Frame", bevel=0.006)
    for sx in (-1, 1):
        d.cyl(_dp(sx * ax0, -0.03), _dp(sx * ax1, dm), 0.025, "SDT_Frame", square=True, ref=N)
    xb, db = arm_x(0.227), 0.227
    d.cyl(_dp(-xb, db), _dp(xb, db), 0.020, "SDT_Frame", square=True, ref=N)
    # styčníkový plech nahoře i dole přes V a začátek trubky
    gus = [(0.34, -0.17), (0.34, 0.17), (0.64, 0.045), (0.64, -0.045)]
    d.plate(gus, _dp(0, 0, 0.0245), F, EX, 0.007, "SDT_Frame")
    d.plate(gus, _dp(0, 0, -0.0315), F, EX, 0.007, "SDT_Frame")
    for dd, x in ((0.40, arm_x(0.40)), (0.40, -arm_x(0.40)), (0.49, arm_x(0.49)), (0.49, -arm_x(0.49)), (0.60, 0.0)):
        d.hex(_dp(x, dd, 0.0315), N, 0.009, 0.006, "SDT_Steel")
    # jedna trubka 60x60 do najížděcího zařízení
    d.cyl(_dp(0, dm - 0.10), _dp(0, hr + 0.02), 0.030, "SDT_Frame", square=True, ref=N)

    # najížděcí zařízení: pozinkované pouzdro 80x80, přírubový kroužek, typový štítek, měch
    pbox(0, (hr + d_b0) / 2, 0, 0.08, d_b0 - hr, 0.08, "SDT_Steel", 0.007)
    pbox(0, d_b0 - 0.006, 0, 0.096, 0.012, 0.096, "SDT_Steel", 0.003)
    for sx in (-1, 1):
        for sh in (-1, 1):
            d.hex(_dp(sx * 0.036, d_b0, sh * 0.036), F, 0.007, 0.006, "SDT_Steel")
    pbox(0.0415, hr + 0.14, 0.0, 0.003, 0.09, 0.04, "SDT_PaintWhite")
    prof = [(0.0, 0.0)] + [(0.036 + 0.008 * (k % 2), 0.14 * k / 8) for k in range(9)] + [(0.0, 0.14)]
    d.lathe(prof, _dp(0, d_b0), F, "SDT_Rubber", seg=16, ref=N)

    # hlava kulové spojky: litý blok, hrnec s kuželovou sukní kolem koule (střed koule COUPLER_Z), kryt a šrouby
    d.box(-0.040, 0.040, by, yr, hz - 0.040, hz + 0.040, "SDT_AluCast", bevel=0.014)
    d.cyl(V(0, by, zb - 0.030), V(0, by, hz + 0.045), 0.058, "SDT_AluCast", seg=32)
    d.cyl(V(0, by, zb - 0.030), V(0, by, zb - 0.052), 0.058, "SDT_AluCast", r1=0.042, seg=32)
    d.torus(V(0, by, zb - 0.052), V(0, 0, 1), 0.042, 0.005, "SDT_Steel", seg=28, rseg=6)
    d.cyl(V(0, by, hz + 0.045), V(0, by, hz + 0.052), 0.028, "SDT_Steel", seg=20)
    d.bolt_circle(V(0, by, hz + 0.045), V(0, 0, 1), 0.043, 4, 0.006, 0.005, "SDT_Steel", phase=math.pi / 4)
    # páka s pojistkou: dvě ucha na zadním okraji hlavy, čep, tyč s červenou rukojetí směrem k oji
    pin = V(0, yr - 0.016, hz + 0.062)
    for sx in (-1, 1):
        d.box(sx * 0.034 - 0.003, sx * 0.034 + 0.003, yr - 0.040, yr - 0.002, hz + 0.040, hz + 0.075, "SDT_Steel", bevel=0.002)
    d.cyl(pin - V(0.042, 0, 0), pin + V(0.042, 0, 0), 0.007, "SDT_Steel", seg=10)
    tip = pin + V(0, 0.15, 0.048)
    d.cyl(pin, tip, 0.0085, "SDT_Steel", seg=10)
    d.cyl(pin + (tip - pin) * 0.45, tip, 0.0155, "SDT_PaintRed", seg=12)
    # bezpečnostní lanko: smyčka kolem pouzdra (lano se obtočí kolem oje), karabina v oku přivařeném k boku hlavy
    rd = hr + 0.2475
    d.torus(_dp(0, rd, 0), F, 0.0585, 0.0035, "SDT_Steel", seg=20, rseg=5)
    p0 = _dp(-0.0585, rd, 0)
    d.cyl(p0 - F * 0.012, p0 + F * 0.012, 0.0075, "SDT_Steel", seg=10)
    d.box(-0.058, -0.038, yr - 0.045, yr - 0.015, hz - 0.018, hz + 0.008, "SDT_Steel", bevel=0.003)
    eye = V(-0.063, yr - 0.030, hz - 0.005)
    d.torus(eye, V(1, 0, 0), 0.012, 0.0035, "SDT_Steel", seg=14, rseg=5)
    cb = eye + V(-0.014, 0, 0)
    d.torus(cb, V(0, 0, 1), 0.013, 0.003, "SDT_Steel", seg=14, rseg=5)
    p3 = cb + V(0, 0.013, 0)
    cable = _spline([p0, p0 + V(-0.016, -0.03, -0.014), (p0 + p3) / 2 + V(-0.012, 0, -0.022), p3 + V(0, 0.04, -0.012), p3], 4)
    d.pipe(cable, 0.0035, "SDT_Steel", seg=6)

    # ruční brzda vpravo na pouzdře: konzola, hlava páky s čepem, páka s červenou rukojetí, bovden k vyrovnávači pod trubkou
    hb = hr + 0.15
    pbox(-0.044, hb, 0.0, 0.008, 0.13, 0.07, "SDT_Steel", 0.003)
    d.cyl(_dp(-0.048, hb, 0.012), _dp(-0.072, hb, 0.012), 0.0165, "SDT_Steel", seg=16)
    d.hex(_dp(-0.072, hb, 0.012), -EX, 0.011, 0.008, "SDT_Steel")
    ld = (-F * 0.40 + N * 0.92).normalized()
    lp = _dp(-0.064, hb, 0.012)
    d.cyl(lp, lp + ld * 0.30, 0.0075, "SDT_Steel", seg=10)
    d.cyl(lp + ld * 0.26, lp + ld * 0.355, 0.0165, "SDT_PaintRed", seg=12)
    dc = 0.56
    pbox(0, dc, -0.0425, 0.06, 0.07, 0.025, "SDT_Steel", 0.003)
    for dd in (dc - 0.025, dc + 0.025):
        d.hex(_dp(0.0, dd, -0.0545), -N, 0.007, 0.005, "SDT_Steel")
    bow = _spline([_dp(-0.064, hb, 0.0), _dp(-0.067, hb - 0.015, -0.050), _dp(-0.052, hb - 0.10, -0.076), _dp(-0.040, hr - 0.07, -0.078),
                   _dp(-0.016, dc + 0.05, -0.066), _dp(-0.003, dc + 0.02, -0.052)], 4)
    d.pipe(bow, 0.0045, "SDT_HoseBlack", seg=6)
    d.cyl(bow[-1], bow[-1] + (bow[-1] - bow[-2]).normalized() * 0.010, 0.0065, "SDT_Steel", seg=8)

    # kabel zástrčky: rozdělovací krabička na příčníku vlevo, kabel po rameni a trubce na příchytkách, zástrčka v držáku na pouzdře
    jb = V(0.30, DRAWBAR_Y0 + 0.04, 0.575)
    d.box(jb.x - 0.040, jb.x + 0.040, jb.y - 0.025, jb.y + 0.025, jb.z, jb.z + 0.040, "SDT_PaintDark", bevel=0.004)
    d.cyl(V(jb.x, jb.y - 0.025, jb.z + 0.020), V(jb.x, jb.y - 0.037, jb.z + 0.020), 0.0105, "SDT_Plastic", seg=12)
    rc = 0.0065
    zp = 0.068                                                # osa zástrčky nad pouzdrem
    pts = [V(jb.x, jb.y - 0.040, jb.z + 0.020), V(jb.x + 0.012, jb.y - 0.055, jb.z + 0.016)]
    pts += [_dp(x, dd, h) for dd, x, h in (
        (0.12, arm_x(0.12), 0.0345), (0.20, arm_x(0.20), 0.0315), (0.28, arm_x(0.28), 0.0315), (0.35, arm_x(0.35), 0.0345),
        (0.42, arm_x(0.42), 0.0380), (0.50, arm_x(0.50), 0.0380), (0.57, 0.016, 0.0380), (0.65, 0.012, 0.0375),
        (hr - 0.06, 0.012, 0.0365), (hr - 0.02, 0.008, 0.0375), (hr + 0.015, 0.004, 0.0465), (hr + 0.035, 0.0, 0.0465),
        (hr + 0.058, 0.0, 0.056), (hr + 0.080, 0.0, zp))]
    cab = _spline(pts, 3)
    d.pipe(cab, rc, "SDT_HoseBlack", seg=6)
    for dd, x, h in ((0.20, arm_x(0.20), 0.0315), (0.45, arm_x(0.45), 0.038), (0.70, 0.012, 0.0365), (hr + 0.03, 0.0, 0.0465)):
        c = _dp(x, dd, h)
        i = min(range(len(cab)), key=lambda k: (cab[k] - c).length)
        t = cab[min(i + 1, len(cab) - 1)] - cab[max(i - 1, 0)]
        _clip(d, c, t, N, rc)
    # držák: podstavec přivařený na pouzdro, pozinkovaný hrnek otevřený dozadu, zástrčka 13pól s krytem kabelu
    cup0, cup1 = hr + 0.185, hr + 0.225
    d.cyl(_dp(0, cup0, zp), _dp(0, cup1, zp), 0.030, "SDT_Steel", seg=18)
    d.cyl(_dp(0, cup0 - 0.006, zp), _dp(0, cup0 + 0.004, zp), 0.034, "SDT_Steel", seg=18)
    d.cyl(_dp(0, hr + 0.115, zp), _dp(0, cup0 + 0.01, zp), 0.0235, "SDT_PaintDark", seg=18)
    d.cyl(_dp(0, hr + 0.145, zp), _dp(0, hr + 0.155, zp), 0.028, "SDT_PaintDark", seg=18)
    d.cyl(_dp(0, hr + 0.080, zp), _dp(0, hr + 0.115, zp), 0.011, "SDT_Rubber", r1=0.0195, seg=14)

    # podpěrné kolečko: svěrná objímka s odnímatelnou nohou vlevo na trubce (čtyři příčné šrouby nad a pod trubkou), vnější trubka s klikou
    dj = (DRAWBAR_Y0 - JOCKEY_Y) / cs
    jx, jy = JOCKEY_X, JOCKEY_Y
    pbox(0.034, dj, 0.0, 0.008, 0.12, 0.16, "SDT_Steel", 0.003)
    pbox(-0.034, dj, 0.0, 0.008, 0.12, 0.12, "SDT_Steel", 0.003)
    for df in (-0.04, 0.04):
        for hh in (-0.052, 0.052):
            d.cyl(_dp(-0.047, dj + df, hh), _dp(0.052, dj + df, hh), 0.0045, "SDT_Steel", seg=8)
            d.hex(_dp(0.038, dj + df, hh), EX, 0.0085, 0.007, "SDT_Steel")
            d.hex(_dp(-0.038, dj + df, hh), -EX, 0.0085, 0.007, "SDT_Steel")
    pbox(0.0615, dj, 0.0, 0.047, 0.07, 0.10, "SDT_Steel", 0.004)
    zc_ = DRAWBAR_Z
    d.cyl(V(jx, jy, zc_ - 0.04), V(jx, jy, zc_ + 0.045), 0.0385, "SDT_Steel", seg=20)
    d.cyl(V(jx, jy, 0.43), V(jx, jy, 0.80), 0.030, "SDT_Steel", seg=20)
    d.cyl(V(jx, jy, 0.43), V(jx, jy, 0.446), 0.0345, "SDT_Steel", seg=20)
    d.cyl(V(jx, jy, 0.80), V(jx, jy, 0.815), 0.034, "SDT_PaintDark", seg=20)
    d.cyl(V(jx, jy, 0.815), V(jx, jy, 0.838), 0.0105, "SDT_Steel", seg=10)
    kx = jx + 0.15
    d.cyl(V(jx, jy, 0.832), V(kx, jy, 0.832), 0.0065, "SDT_Steel", seg=8)
    d.cyl(V(kx, jy, 0.822), V(kx, jy, 0.846), 0.0085, "SDT_Steel", seg=8)
    d.cyl(V(kx, jy, 0.840), V(kx, jy, 0.915), 0.0165, "SDT_PaintRed", seg=12)
    d.cyl(V(jx, jy + 0.036, zc_ + 0.005), V(jx, jy + 0.088, zc_ + 0.028), 0.0045, "SDT_Steel", seg=6)
    d.sphere(V(jx, jy + 0.088, zc_ + 0.028), 0.0105, "SDT_PaintRed", seg=10, rings=5)

    # výsuvná část nohy: vnitřní trubka, vidlice a kolečko
    j = Mesh("Mill_Jockey")
    j.cyl(V(jx, jy, 0.215), V(jx, jy, 0.60), 0.0245, "SDT_Steel", seg=18)
    j.box(jx - 0.040, jx + 0.040, jy - 0.030, jy + 0.030, 0.205, 0.219, "SDT_Steel", bevel=0.003)
    for ox in (jx + 0.031, jx - 0.037):
        j.plate([(-0.042, 0.212), (0.042, 0.212), (0.022, 0.060), (-0.022, 0.060)], V(ox, jy, 0.0), V(0, 1, 0), V(0, 0, 1), 0.006, "SDT_Steel")
    j.cyl(V(jx - 0.043, jy, 0.095), V(jx + 0.043, jy, 0.095), 0.006, "SDT_Steel", seg=8)
    j.hex(V(jx + 0.037, jy, 0.095), V(1, 0, 0), 0.011, 0.008, "SDT_Steel")
    j.cyl(V(jx - 0.027, jy, 0.095), V(jx + 0.027, jy, 0.095), 0.095, "SDT_Rubber", seg=24)
    j.cyl(V(jx - 0.030, jy, 0.095), V(jx + 0.030, jy, 0.095), 0.060, "SDT_Alu", seg=18)
    j.finish()
    d.finish()


def _rib(h, a, b, normal, w, t, mat):
    """Plochá výztuha (pásnice w x t) po přímce a-b na šikmé stěně, tloušťka t směrem normal."""
    a, b = Vector(a), Vector(b)
    d = (b - a)
    n = Vector(normal)
    c = (a + b) / 2 + n.normalized() * (t / 2)
    h.obox((t, w, d.length), frame(c, d, n), mat, bevel=0.002)


def _wall(z):
    """Poloviční rozměry (x, y) šikmé nálevky násypky ve výšce z."""
    t = (z - HOPPER_OUT_Z) / (HOPPER_RIM_Z - HOPPER_OUT_Z)
    return 0.22 + (HOPPER_HX - 0.22) * t, 0.22 + (HOPPER_HY - 0.22) * t


def build_hopper():
    """Zásobník na hrubé vápno vzadu: nálevka s kosými stěnami (čtyřboký jehlan z výsypu do lemu), svislý lem, pásnicové výztuhy po stěnách
    a obvodové obruče, síto v ústí (rám, nosné tyče a drátěná mříž), žebra, čtyři nohy se vzpěrami a žebřík."""
    cx, cy = HOPPER_CX, HOPPER_CY
    h = Mesh("Mill_Hopper")
    hx, hy = HOPPER_HX, HOPPER_HY
    zo, zr, zt = HOPPER_OUT_Z, HOPPER_RIM_Z, HOPPER_TOP_Z
    h.loft(V(cx, cy, zo), [(0.0, 0.22, 0.22, 0.015), (zr - zo, hx, hy, 0.03)], "SDT_PaintGrey")
    h.loft(V(cx, cy, zr), [(0.0, hx, hy, 0.03), (zt - zr, hx, hy, 0.03)], "SDT_PaintGrey", pocket=(0.0, hx - 0.035, hy - 0.035, 0.02, 0.28))
    rim = 0.055
    h.box(cx - hx - 0.012, cx + hx + 0.012, cy - hy - 0.012, cy - hy + rim, zt - 0.03, zt + 0.045, "SDT_PaintDark", bevel=0.004)
    h.box(cx - hx - 0.012, cx + hx + 0.012, cy + hy - rim, cy + hy + 0.012, zt - 0.03, zt + 0.045, "SDT_PaintDark", bevel=0.004)
    for sx in (-1, 1):
        h.box(cx + sx * (hx - rim / 2) - rim / 2 - 0.006, cx + sx * (hx - rim / 2) + rim / 2 + 0.006, cy - hy, cy + hy,
              zt - 0.03, zt + 0.045, "SDT_PaintDark", bevel=0.004)
    # síto: nosné příčky po 0,19 m (plochá ocel na hranu), na nich jemná drátěná mříž (podélné dráty po Y, příčné po X)
    for k in range(-4, 5):
        h.box(cx + k * 0.19 - 0.014, cx + k * 0.19 + 0.014, cy - hy + rim, cy + hy - rim, zt - 0.04, zt + 0.004, "SDT_Mesh", bevel=0.002)
    wz = zt + 0.004
    for k in range(-13, 14):
        x = cx + k * 0.062
        h.box(x - 0.0035, x + 0.0035, cy - hy + rim, cy + hy - rim, wz, wz + 0.007, "SDT_Mesh")
    for k in range(-11, 12):
        y = cy + k * 0.064
        h.box(cx - hx + rim, cx + hx - rim, y - 0.0035, y + 0.0035, wz + 0.007, wz + 0.014, "SDT_Mesh")
    # výztuhy na šikmých stěnách: tři svislé pásnice na stěnu od výsypu k lemu a tři obruče
    z0 = zo + 0.05
    (ex0, ey0), (ex1, ey1) = _wall(z0), _wall(zr)
    for sy in (-1, 1):
        for fr in (-0.7, 0.0, 0.7):
            _rib(h, V(cx + fr * ex0, cy + sy * ey0, z0), V(cx + fr * ex1, cy + sy * ey1, zr), V(0, sy, 0), 0.035, 0.012, "SDT_Frame")
    for sx in (-1, 1):
        for fr in (-0.7, 0.0, 0.7):
            _rib(h, V(cx + sx * ex0, cy + fr * ey0, z0), V(cx + sx * ex1, cy + fr * ey1, zr), V(sx, 0, 0), 0.035, 0.012, "SDT_Frame")
    for z in (1.40, 1.70, zr - 0.02):
        ex, ey = _wall(z)
        for sy in (-1, 1):
            h.box(cx - ex - 0.012, cx + ex + 0.012, cy + sy * ey - 0.020 + sy * 0.012, cy + sy * ey + 0.020 + sy * 0.012, z - 0.025, z + 0.025,
                  "SDT_Frame", bevel=0.003)
        for sx in (-1, 1):
            h.box(cx + sx * ex - 0.020 + sx * 0.012, cx + sx * ex + 0.020 + sx * 0.012, cy - ey - 0.012, cy + ey + 0.012, z - 0.025, z + 0.025,
                  "SDT_Frame", bevel=0.003)
    # žebra na svislém lemu
    for sy in (-1, 1):
        for x in (-0.60, -0.30, 0.0, 0.30, 0.60):
            h.box(cx + x - 0.015, cx + x + 0.015, cy + sy * hy, cy + sy * (hy + 0.014), zr + 0.03, zt - 0.05, "SDT_PaintGrey")
    for sx in (-1, 1):
        for y in (-0.40, -0.20, 0.0, 0.20, 0.40):
            h.box(cx + sx * hx, cx + sx * (hx + 0.014), cy + y - 0.015, cy + y + 0.015, zr + 0.03, zt - 0.05, "SDT_PaintGrey")
    for z in (zr + 0.02, zt - 0.14):
        h.box(cx - hx - 0.010, cx + hx + 0.010, cy - hy - 0.010, cy + hy + 0.010, z - 0.018, z + 0.018, "SDT_Frame", bevel=0.004)
    # oranžový pruh na lemu
    for sy in (-1, 1):
        h.box(cx - hx + 0.03, cx + hx - 0.03, cy + sy * (hy + 0.001), cy + sy * (hy + 0.008), zt - 0.26, zt - 0.20, "SDT_NutIndicator")
    for sx in (-1, 1):
        h.box(cx + sx * (hx + 0.001), cx + sx * (hx + 0.008), cy - hy + 0.03, cy + hy - 0.03, zt - 0.26, zt - 0.20, "SDT_NutIndicator")
    # štítek na boku (-X) a na zádi
    h.box(cx - hx - 0.016, cx - hx - 0.002, cy - 0.20, cy + 0.20, zr + 0.06, zr + 0.22, "SDT_PaintWhite", bevel=0.003)
    h.box(cx - 0.30, cx + 0.30, cy + hy + 0.002, cy + hy + 0.016, zr + 0.06, zr + 0.22, "SDT_PaintWhite", bevel=0.003)
    # nohy z paluby k šikmým stěnám se styčníkovými plechy a vzpěry
    zl = zr - 0.04
    for sx in (-1, 1):
        for sy in (-1, 1):
            p0 = V(cx + sx * (hx - 0.07), cy + sy * (hy - 0.07), DECK_Z)
            h.cyl(p0, V(p0.x, p0.y, zl), 0.033, "SDT_Frame", square=True, ref=V(1, 0, 0))
            h.box(p0.x - 0.06, p0.x + 0.06, p0.y - 0.06, p0.y + 0.06, DECK_Z, DECK_Z + 0.012, "SDT_Frame", bevel=0.003)
            h.obox((0.12, 0.12, 0.014), Matrix.Translation(V(p0.x, p0.y, zl)), "SDT_Frame", bevel=0.003)
            h.obox((0.10, 0.10, 0.012), Matrix.Translation(V(p0.x, p0.y, zl - 0.30)), "SDT_Frame", bevel=0.003)
    zb = 0.80
    for sx in (-1, 1):
        a = V(cx + sx * (hx - 0.07), cy - (hy - 0.07), zb)
        b = V(cx + sx * (hx - 0.07), cy + (hy - 0.07), zb + 0.80)
        h.cyl(a, b, 0.014, "SDT_Frame", seg=6)
        a2 = V(cx + sx * (hx - 0.07), cy + (hy - 0.07), zb)
        b2 = V(cx + sx * (hx - 0.07), cy - (hy - 0.07), zb + 0.80)
        h.cyl(a2, b2, 0.014, "SDT_Frame", seg=6)
    for sy in (-1, 1):
        a = V(cx - (hx - 0.07), cy + sy * (hy - 0.07), zb)
        b = V(cx + (hx - 0.07), cy + sy * (hy - 0.07), zb + 0.80)
        h.cyl(a, b, 0.014, "SDT_Frame", seg=6)
    # žebřík na záď zásobníku (za rámem cívky s hadicí)
    ly = cy + hy + 0.10
    for sx in (-1, 1):
        h.cyl(V(sx * 0.20, ly, DECK_Z - 0.05), V(sx * 0.20, ly, zt + 0.12), 0.014, "SDT_Alu", seg=8)
        for z in (DECK_Z + 0.30, zr + 0.10, zt - 0.20):
            h.box(sx * 0.20 - 0.014, sx * 0.20 + 0.014, cy + hy, ly, z - 0.015, z + 0.015, "SDT_Alu")
    z = DECK_Z + 0.16
    while z < zt + 0.02:
        h.cyl(V(-0.20, ly, z), V(0.20, ly, z), 0.011, "SDT_Alu", seg=8)
        z += 0.20
    h.cyl(V(-0.20, ly, zt + 0.12), V(-0.20, ly - 0.14, zt + 0.12), 0.014, "SDT_Alu", seg=8)
    h.cyl(V(0.20, ly, zt + 0.12), V(0.20, ly - 0.14, zt + 0.12), 0.014, "SDT_Alu", seg=8)
    h.finish()


def build_auger():
    """Šnek z dna nádoby šikmo vpřed nad mlýn: trubka s přírubami, převodovka s motorkem na horním konci, výsypka do mlýna."""
    a = Mesh("Mill_Auger")
    p0, p1 = AUGER_P0, AUGER_P1
    d = (p1 - p0).normalized()
    # svislá výsypka z dna nádoby dolů do spodku šneku na paluze
    zc0 = p0.z + 0.10
    a.loft(V(HOPPER_CX, p0.y, zc0), [(0.0, 0.14, 0.14, 0.012), (HOPPER_OUT_Z - zc0 + 0.01, 0.20, 0.20, 0.015)], "SDT_Alu")
    for z in (zc0 + 0.06, HOPPER_OUT_Z - 0.08):
        a.box(HOPPER_CX - 0.17, HOPPER_CX + 0.17, p0.y - 0.17, p0.y + 0.17, z - 0.012, z + 0.012, "SDT_Frame", bevel=0.003)
    # spodek šneku: pouzdro na paluze
    a.box(HOPPER_CX - 0.15, HOPPER_CX + 0.15, p0.y - 0.15, p0.y + 0.15, DECK_Z, p0.z + 0.02, "SDT_Frame", bevel=0.006)
    rear = V(0, 1, 0)
    a.cyl(p0 + rear * 0.30, p0 + rear * 0.02, 0.125, "SDT_PaintGrey", seg=28)
    a.cyl(p0 + rear * 0.30, p0 + rear * 0.316, 0.135, "SDT_Frame", seg=28)
    a.sphere(p0, 0.132, "SDT_PaintGrey", seg=28, rings=12)
    a.cyl(p0, p1, 0.115, "SDT_PaintGrey", seg=28)
    a.flange(p0 + rear * 0.10, V(0, -1, 0), 0.155, 0.016, "SDT_Frame", bolts=10, bolt_r=0.140, bolt_size=0.0075)
    a.flange(p0 + d * 0.10, d, 0.150, 0.016, "SDT_Frame", bolts=10, bolt_r=0.135, bolt_size=0.0075)
    for t in (0.18, 0.5, 0.82):
        c = p0 + (p1 - p0) * t
        a.cyl(c - d * 0.02, c + d * 0.02, 0.135, "SDT_Frame", seg=28)
        a.bolt_circle(c + d * 0.02, d, 0.125, 8, 0.0065, 0.006, "SDT_Steel")
    # koncová hlava s převodovkou a motorkem
    a.cyl(p1 + d * 0.014, p1 - d * 0.14, 0.140, "SDT_PumpBlue", seg=24)
    a.cyl(p1 - d * 0.14, p1 - d * 0.26, 0.085, "SDT_PumpBlue", seg=20)
    a.fins(p1 - d * 0.16, d, 0.080, 0.105, 0.0, 0.10, 18, 0.004, "SDT_PumpBlue")
    a.cyl(p1 - d * 0.26, p1 - d * 0.31, 0.062, "SDT_TankBlack", seg=18)
    # výsypka do mlýna dolů
    yc = p1.y + 0.04
    zr = MILL_Z + MILL_R - 0.05
    a.loft(V(MILL_X, yc, zr), [(0.0, 0.14, 0.14, 0.012), (p1.z - 0.18 - zr, 0.15, 0.15, 0.012)], "SDT_GenOrange")
    a.box(MILL_X - 0.17, MILL_X + 0.17, yc - 0.17, yc + 0.17, p1.z - 0.195, p1.z - 0.165, "SDT_Frame")
    a.cyl(V(MILL_X, yc, p1.z - 0.17), V(MILL_X, yc, p1.z - 0.105), 0.125, "SDT_Rubber", seg=24)
    # uložení šneku na dvou stojkách
    for t in (0.35, 0.72):
        c = p0 + (p1 - p0) * t
        for sx in (-1, 1):
            a.box(c.x + sx * 0.16 - 0.02, c.x + sx * 0.16 + 0.02, c.y - 0.03, c.y + 0.03, DECK_Z, c.z - 0.10, "SDT_Frame", bevel=0.003)
        a.box(c.x - 0.19, c.x + 0.19, c.y - 0.03, c.y + 0.03, c.z - 0.14, c.z - 0.09, "SDT_Frame", bevel=0.003)
    a.finish()


LID_A0, LID_A1 = math.radians(-62), math.radians(58)    # víko mlýna: úhly od svislice nahoru, kladný k +Y (pant vzadu, upínky vpředu)


def _radial_bar(m, x0, x1, angle, r_mid, w, t, mat):
    """Příruba po hraně víka: pás po ose X v úhlu angle kolem osy mlýna, w = rozměr po poloměru, t = tloušťka po obvodu."""
    d = V(0, math.sin(angle), math.cos(angle))
    c = V((x0 + x1) / 2, ROW_Y + d.y * r_mid, MILL_Z + d.z * r_mid)
    m.obox((abs(x1 - x0), t, w), frame(c, d, V(1, 0, 0)), mat, bevel=0.002)


def build_mill():
    """Skříň kladivového mlýnu s osou podél X: válcový plášť s přírubami, odnímatelné víko na dvou pantech vzadu a třech upínkách vpředu,
    vzduchem hnaný výstup jemného vápna axiálním hrdlem na čele (-X) s přírubou, revizní dvířka vpředu dole, štítek vzadu a sedla k palubě."""
    m = Mesh("Mill_Body")
    zc = MILL_Z
    R = MILL_R
    x0, x1 = MILL_X - MILL_HL, MILL_X + MILL_HL
    m.cyl(V(x0, ROW_Y, zc), V(x1, ROW_Y, zc), R, "SDT_GenOrange", seg=40)
    for x, sgn in ((x0, 1), (x1 - 0.03, -1)):
        m.cyl(V(x, ROW_Y, zc), V(x + 0.03, ROW_Y, zc), R + 0.022, "SDT_Frame", seg=40)
        m.bolt_circle(V(x + (0.03 if sgn > 0 else 0.0), ROW_Y, zc), V(sgn, 0, 0), R + 0.002, 16, 0.007, 0.007, "SDT_Steel")
    # čelo -X: vyklenuté víko a hrdlo výstupu s přírubou (čelo příruby MILL_OUT_X)
    m.cyl(V(x0, ROW_Y, zc), V(x0 - 0.045, ROW_Y, zc), R - 0.03, "SDT_GenOrange", r1=R - 0.11, seg=36)
    m.cyl(V(x0 - 0.045, ROW_Y, zc), V(x0 - 0.075, ROW_Y, zc), 0.118, "SDT_GenOrange", r1=0.080, seg=28)
    m.flange(V(x0 - 0.075, ROW_Y, zc), V(-1, 0, 0), 0.108, 0.010, "SDT_Steel", bolts=6, bolt_r=0.090, bolt_size=0.007)
    # víko na pantech: pláště o 15 mm výš, příruby po hranách a na čelech, dva panty vzadu, tři upínky vpředu
    xa, xb = x0 + 0.045, x1 - 0.045
    _arc_prism(m, ROW_Y, zc, R + 0.001, R + 0.016, LID_A0, LID_A1, xa, xb, "SDT_GenOrange")
    for ang in (LID_A0, LID_A1):
        _radial_bar(m, xa - 0.010, xb + 0.010, ang, R + 0.026, 0.044, 0.014, "SDT_Frame")
    for xe, s in ((xa - 0.008, -1), (xb, 1)):
        _arc_prism(m, ROW_Y, zc, R + 0.001, R + 0.032, LID_A0, LID_A1, min(xe, xe + 0.008), max(xe, xe + 0.008), "SDT_Frame", steps=12)
    ha = V(0, math.sin(LID_A1), math.cos(LID_A1))
    hp = V(0, ROW_Y + ha.y * (R + 0.040), zc + ha.z * (R + 0.040))
    for hx_ in (MILL_X - 0.12, MILL_X + 0.04):
        m.cyl(V(hx_ - 0.045, hp.y, hp.z), V(hx_ + 0.045, hp.y, hp.z), 0.015, "SDT_Steel", seg=14)
        m.obox((0.09, 0.022, 0.060), frame(V(hx_, hp.y + 0.004, hp.z - 0.030), V(0, 0, 1), V(1, 0, 0)), "SDT_Frame", bevel=0.003)
        m.obox((0.09, 0.022, 0.050), frame(V(hx_, hp.y - 0.002, hp.z + 0.028), ha, V(1, 0, 0)), "SDT_Frame", bevel=0.003)
        for dx in (-0.03, 0.03):
            m.hex(V(hx_ + dx, hp.y + 0.016, hp.z - 0.030), V(0, 1, 0), 0.007, 0.006, "SDT_Steel")
    la = V(0, math.sin(LID_A0), math.cos(LID_A0))
    down = V(0, -math.cos(LID_A0), math.sin(LID_A0))
    for lx in (MILL_X - 0.12, MILL_X, MILL_X + 0.12):
        top = V(lx, ROW_Y + la.y * (R + 0.040), zc + la.z * (R + 0.040))
        lo = V(lx, ROW_Y + math.sin(LID_A0 - 0.20) * (R + 0.012), zc + math.cos(LID_A0 - 0.20) * (R + 0.012))
        m.obox((0.05, 0.034, 0.030), frame(lo, la, V(1, 0, 0)), "SDT_Steel", bevel=0.004)
        m.cyl(lo + la * 0.015, top, 0.0065, "SDT_Steel", seg=8)
        m.obox((0.036, 0.020, 0.024), frame(top, la, V(1, 0, 0)), "SDT_Steel", bevel=0.003)
        m.cyl(top, top + down * 0.075, 0.0085, "SDT_Steel", seg=8)
        m.cyl(top + down * 0.075, top + down * 0.125, 0.0125, "SDT_PaintRed", seg=10)
    # revizní dvířka vpředu dole (tlustá deska zapuštěná do pláště) a štítek vzadu
    d = V(MILL_X, ROW_Y - R + 0.005, zc - 0.09)
    m.box(d.x - 0.12, d.x + 0.12, d.y - 0.018, d.y + 0.060, zc - 0.20, zc + 0.01, "SDT_Frame", bevel=0.004)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.hex(V(d.x + sx * 0.095, d.y - 0.018, zc - 0.09 + sz * 0.075), V(0, -1, 0), 0.012, 0.012, "SDT_Steel")
    m.cyl(V(d.x, d.y - 0.018, zc - 0.09), V(d.x, d.y - 0.060, zc - 0.09), 0.014, "SDT_Steel", seg=8)
    m.box(d.x - 0.06, d.x + 0.06, d.y - 0.066, d.y - 0.050, zc - 0.098, zc - 0.080, "SDT_PaintRed", bevel=0.003)
    m.box(MILL_X - 0.10, MILL_X + 0.10, ROW_Y + R - 0.010, ROW_Y + R + 0.004, zc - 0.10, zc - 0.02, "SDT_PaintWhite", bevel=0.003)
    # sedlo k palubě
    for x in (x0 + 0.06, x1 - 0.09):
        m.box(x - 0.04, x + 0.04, ROW_Y - 0.30, ROW_Y + 0.30, DECK_Z, zc - 0.20, "SDT_Frame", bevel=0.004)
        m.box(x - 0.05, x + 0.05, ROW_Y - 0.28, ROW_Y + 0.28, zc - 0.23, zc - 0.18, "SDT_Frame", bevel=0.004)
    m.finish()


def build_engine():
    """Malý vzduchem chlazený jednoválcový diesel (typ Hatz/Lombardini) vlevo od mlýna, klikový hřídel podél X v ose mlýna:
    zvon k mlýnu, klikovka, žebrovaný válec s hlavou, plechový kryt chlazení s mřížkou ventilátoru na čele (+X), vzduchový
    filtr, výfuk s tlumičem a startér. Stojí na příčných profilech, které nesou i nádrž (ta je samostatný díl)."""
    e = Mesh("Mill_Engine")
    cy, zc = ROW_Y, MILL_Z
    x0, x1 = ENG_X0, ENG_X1
    zb, zt = DECK_Z + 0.075, 0.93
    cx0, cx1 = ENG_CASE_X0, ENG_CASE_X1
    hw = 0.15
    cxx = ENG_CYL_X

    # příčné U profily nesou nádrž i motor; motor stojí na čtyřech silentblocích pod patkami přišroubovanými po stranách skříně
    zu = DECK_Z + 0.030
    for xf in (x0 + 0.10, x1 - 0.10):
        e.box(xf - 0.040, xf + 0.040, FUEL_Y - 0.12, cy + 0.22, zu - 0.008, zu, "SDT_Frame", bevel=0.002)
        for sx in (-1, 1):
            e.box(xf + sx * 0.036 - 0.004, xf + sx * 0.036 + 0.004, FUEL_Y - 0.12, cy + 0.22, DECK_Z, zu - 0.008, "SDT_Frame")
        for sy in (-1, 1):
            my = cy + sy * 0.19
            e.cyl(V(xf, my, zu), V(xf, my, zu + 0.005), 0.032, "SDT_Steel", seg=20)
            e.cyl(V(xf, my, zu + 0.005), V(xf, my, zu + 0.011), 0.025, "SDT_Rubber", seg=16)
            e.cyl(V(xf, my, zu + 0.011), V(xf, my, zu + 0.030), 0.017, "SDT_Rubber", seg=16)
            e.cyl(V(xf, my, zu + 0.030), V(xf, my, zu + 0.036), 0.025, "SDT_Rubber", seg=16)
            e.cyl(V(xf, my, zu + 0.036), V(xf, my, zu + 0.040), 0.029, "SDT_Steel", seg=20)
            fy0, fy1 = (cy + 0.125, cy + 0.225) if sy > 0 else (cy - 0.225, cy - 0.125)
            e.box(xf - 0.040, xf + 0.040, fy0, fy1, zu + 0.040, zu + 0.057, "SDT_Frame", bevel=0.003)
            e.cyl(V(xf, my, zu + 0.057), V(xf, my, zu + 0.080), 0.006, "SDT_Steel", seg=8)
            e.cyl(V(xf, my, zu + 0.057), V(xf, my, zu + 0.060), 0.017, "SDT_Steel", seg=16)
            e.hex(V(xf, my, zu + 0.060), V(0, 0, 1), 0.011, 0.010, "SDT_Steel")

    e.cyl(V(MILL_X + MILL_HL, cy, zc), V(0.28, cy, zc), 0.185, "SDT_CastIron", seg=32)
    e.cyl(V(0.275, cy, zc), V(0.295, cy, zc), 0.205, "SDT_CastIron", seg=32)
    e.bolt_circle(V(0.295, cy, zc), V(1, 0, 0), 0.192, 6, 0.009, 0.008, "SDT_Steel")
    e.cyl(V(0.18, cy, zc), V(0.20, cy, zc), 0.215, "SDT_Frame", seg=28)
    e.box(0.205, 0.265, cy - 0.05, cy + 0.05, zc + 0.176, zc + 0.190, "SDT_Steel", bevel=0.003)
    for sx in (0.215, 0.255):
        for sy in (-1, 1):
            e.hex(V(sx, cy + sy * 0.035, zc + 0.190), V(0, 0, 1), 0.007, 0.006, "SDT_PaintDark")

    e.cyl(V(0.285, cy, zc), V(cx0 + 0.01, cy, zc), 0.13, "SDT_CastIron", seg=32)
    e.obox((cx1 - cx0, 2 * hw, zt - zb), Matrix.Translation(((cx0 + cx1) / 2, cy, (zb + zt) / 2)), "SDT_Alu", bevel=0.04,
           segments=2)

    e.cyl(V(cxx, cy, zt - 0.01), V(cxx, cy, 0.945), 0.09, "SDT_Alu", seg=20)
    e.cyl(V(cxx, cy, 0.93), V(cxx, cy, ZH0), 0.062, "SDT_Alu", seg=20)
    for k in range(8):
        z = 0.945 + 0.024 * k
        e.cyl(V(cxx, cy, z), V(cxx, cy, z + 0.010), 0.098, "SDT_Alu", seg=16)
    e.obox((0.17, 0.17, 0.055), Matrix.Translation((cxx, cy, ZH0 + 0.0275)), "SDT_PaintDark", bevel=0.012, segments=2)
    e.obox((0.13, 0.11, 0.046), Matrix.Translation((cxx, cy, ZH0 + 0.078)), "SDT_PaintDark", bevel=0.014, segments=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            e.hex(V(cxx + sx * 0.077, cy + sy * 0.072, ZH0 + 0.055), V(0, 0, 1), 0.008, 0.008, "SDT_Steel")
            e.hex(V(cxx + sx * 0.045, cy + sy * 0.032, ZH0 + 0.101), V(0, 0, 1), 0.008, 0.007, "SDT_Steel")

    # plechový kryt chlazení: skříň s ventilátorem na čele a kapota nad válcem
    sx0, sx1 = 0.60, 0.78
    e.obox((sx1 - sx0, 0.32, 0.31), Matrix.Translation(((sx0 + sx1) / 2, cy, zb + 0.155)), "SDT_EngineRed", bevel=0.055, segments=2)
    e.plate([(0.575, 0.90), (sx1 - 0.01, 0.90), (sx1 - 0.01, 0.985), (0.64, 1.03), (0.575, 1.03)],
            V(0, cy + 0.14, 0), V(1, 0, 0), V(0, 0, 1), 0.28, "SDT_EngineRed")
    for sy in (-1, 1):
        for k in range(3):
            e.box(0.64, 0.74, cy + sy * 0.141 - 0.002, cy + sy * 0.141 + 0.002, 0.915 + 0.025 * k, 0.925 + 0.025 * k, "SDT_PaintDark")
    gx = sx1
    e.cyl(V(gx - 0.004, cy, zc), V(gx + 0.006, cy, zc), 0.118, "SDT_PaintDark", seg=28)
    e.torus(V(gx + 0.004, cy, zc), V(1, 0, 0), 0.118, 0.008, "SDT_Steel", seg=28, rseg=4)
    e.torus(V(gx + 0.008, cy, zc), V(1, 0, 0), 0.066, 0.004, "SDT_Steel", seg=20, rseg=4)
    e.fins(V(gx + 0.006, cy, zc), V(1, 0, 0), 0.026, 0.115, 0.0, 0.007, 8, 0.007, "SDT_Steel", phase=math.radians(22.5))
    e.cyl(V(gx + 0.006, cy, zc), V(gx + 0.026, cy, zc), 0.026, "SDT_Steel", seg=16)
    e.hex(V(gx + 0.026, cy, zc), V(1, 0, 0), 0.015, 0.010, "SDT_Steel")
    for sy in (-1, 1):
        for z in (zb + 0.03, zb + 0.28):
            e.hex(V(gx - 0.002, cy + sy * 0.13, z), V(1, 0, 0), 0.010, 0.008, "SDT_Steel")

    # suchý vzduchový filtr na přední straně skříně: příruba, tělo se čtyřmi pružnými sponami, víko s křídlovou maticí, gumový
    # odprašovací ventil a sací hadice s objímkami do sání hlavy
    ax_, ay_ = ENG_AIR_X, cy - 0.10
    e.cyl(V(ax_, ay_, zt - 0.005), V(ax_, ay_, zt + 0.014), 0.062, "SDT_Steel", seg=24)
    e.bolt_circle(V(ax_, ay_, zt + 0.014), V(0, 0, 1), 0.054, 4, 0.006, 0.006, "SDT_Steel", phase=math.radians(45))
    e.cyl(V(ax_, ay_, zt + 0.014), V(ax_, ay_, 1.085), 0.050, "SDT_PaintDark", seg=24)
    e.torus(V(ax_, ay_, 1.085), V(0, 0, 1), 0.052, 0.005, "SDT_PaintDark", seg=24, rseg=5)
    e.cyl(V(ax_, ay_, 1.085), V(ax_, ay_, 1.160), 0.049, "SDT_PaintDark", seg=24)
    e.cyl(V(ax_, ay_, 1.160), V(ax_, ay_, 1.185), 0.049, "SDT_PaintDark", r1=0.022, seg=24)
    e.cyl(V(ax_, ay_, 1.185), V(ax_, ay_, 1.225), 0.006, "SDT_Steel", seg=8)
    e.cyl(V(ax_, ay_, 1.198), V(ax_, ay_, 1.208), 0.017, "SDT_Steel", r1=0.012, seg=10)
    for sx in (-1, 1):
        e.obox((0.022, 0.007, 0.014), Matrix.Translation((ax_ + sx * 0.017, ay_, 1.222)) @ Matrix.Rotation(sx * math.radians(35), 4, "Y"), "SDT_Steel")
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        sx_, sy_ = ax_ + 0.052 * math.cos(a), ay_ + 0.052 * math.sin(a)
        e.cyl(V(sx_, sy_, 1.060), V(sx_, sy_, 1.118), 0.005, "SDT_Steel", seg=6)
        e.sphere(V(sx_, sy_, 1.060), 0.0075, "SDT_Steel", seg=8, rings=4)
    dv = V(ax_ - 0.036, ay_ - 0.036, 0.985)
    e.cyl(dv, dv + V(-0.022, -0.022, -0.012), 0.014, "SDT_Rubber", r1=0.020, seg=12)
    e.cyl(V(ax_ + 0.046, ay_ + 0.012, 1.050), V(ax_ + 0.062, ay_ + 0.012, 1.050), 0.026, "SDT_PaintDark", seg=14)
    p0 = V(ax_ + 0.062, ay_ + 0.012, 1.050)
    pts = _bez(p0, p0 + V(0.06, 0.0, 0.0), V(cxx - 0.075, cy - 0.095, 1.090), V(cxx - 0.045, cy - 0.085, ZH0 + 0.025), 10)
    for a, b in zip(pts, pts[1:]):
        e.cyl(a, b, 0.021, "SDT_HoseBlack", seg=10, caps=False)
    e.clamp(p0 + V(0.014, 0, 0), V(1, 0, 0), 0.022)
    e.clamp(pts[-1] - (pts[-1] - pts[-2]).normalized() * 0.014, pts[-1] - pts[-2], 0.022)
    e.cyl(pts[-1] - (pts[-1] - pts[-2]).normalized() * 0.012, pts[-1], 0.026, "SDT_Steel", seg=12)

    # výfuk: z hlavy příložkou dozadu a vodorovně do kompaktního tlumiče na dvou konzolách na krytu chlazení; krátká ohnutá koncovka s klapkou
    ey, zx = cy + 0.12, ZH0 + 0.025
    mx0, mx1, rm = 0.565, 0.765, 0.056
    e.cyl(V(cxx, cy + 0.085, zx), V(cxx, cy + 0.096, zx), 0.038, "SDT_Steel", seg=18)
    for sx in (-1, 1):
        e.hex(V(cxx + sx * 0.028, cy + 0.096, zx + 0.0), V(0, 1, 0), 0.007, 0.008, "SDT_Steel")
    e.cyl(V(cxx, cy + 0.096, zx), V(cxx, ey, zx), 0.027, "SDT_Steel", seg=14)
    e.sphere(V(cxx, ey, zx), 0.031, "SDT_Steel", seg=14, rings=7)
    e.cyl(V(cxx, ey, zx), V(mx0 - 0.030, ey, zx), 0.027, "SDT_Steel", seg=14)
    e.torus(V(0.515, ey, zx), V(1, 0, 0), 0.029, 0.004, "SDT_Alu", seg=16, rseg=4)
    e.torus(V(0.525, ey, zx), V(1, 0, 0), 0.029, 0.004, "SDT_Alu", seg=16, rseg=4)
    e.cyl(V(mx0, ey, zx), V(mx0 - 0.030, ey, zx), rm, "SDT_Alu", r1=0.031, seg=24)
    e.cyl(V(mx0, ey, zx), V(mx1, ey, zx), rm, "SDT_Alu", seg=28)
    e.cyl(V(mx1, ey, zx), V(mx1 + 0.030, ey, zx), rm, "SDT_Alu", r1=0.028, seg=24)
    for x in (mx0 + 0.003, mx1 - 0.003):
        e.torus(V(x, ey, zx), V(1, 0, 0), rm, 0.004, "SDT_Steel", seg=28, rseg=4)
    for x, zbase in ((0.600, 1.030), (0.720, 1.003)):
        e.box(x - 0.028, x + 0.028, ey - 0.036, ey + 0.036, zbase - 0.002, zbase + 0.006, "SDT_Frame", bevel=0.002)
        for sy in (-1, 1):
            e.box(x - 0.007, x + 0.007, ey + sy * 0.030 - 0.004, ey + sy * 0.030 + 0.004, zbase, zx - rm + 0.004, "SDT_Frame")
            e.hex(V(x + 0.020, ey + sy * 0.026, zbase + 0.006), V(0, 0, 1), 0.007, 0.006, "SDT_Steel")
            e.hex(V(x - 0.020, ey + sy * 0.026, zbase + 0.006), V(0, 0, 1), 0.007, 0.006, "SDT_Steel")
        e.box(x - 0.012, x + 0.012, ey - 0.040, ey + 0.040, zx - rm - 0.003, zx - rm + 0.003, "SDT_Frame")
        e.torus(V(x, ey, zx), V(1, 0, 0), rm + 0.003, 0.0035, "SDT_Frame", seg=28, rseg=4)
    tx = mx1 + 0.060
    tail = _bez(V(mx1 + 0.028, ey, zx), V(tx - 0.012, ey, zx), V(tx, ey, zx + 0.004), V(tx, ey, zx + 0.040), 8)
    for a, b in zip(tail, tail[1:]):
        e.cyl(a, b, 0.021, "SDT_Steel", seg=10, caps=False)
    e.cyl(V(tx, ey, zx + 0.040), V(tx, ey, zx + 0.130), 0.021, "SDT_Steel", seg=12)
    e.torus(V(tx, ey, zx + 0.055), V(0, 0, 1), 0.021, 0.004, "SDT_Alu", seg=14, rseg=4)
    e.cyl(V(tx, ey, zx + 0.130), V(tx, ey, zx + 0.136), 0.026, "SDT_Steel", seg=14)
    e.cyl(V(tx + 0.016, ey, zx + 0.128), V(tx + 0.016, ey, zx + 0.152), 0.004, "SDT_Steel", seg=6)
    e.obox((0.056, 0.056, 0.005), Matrix.Translation((tx, ey, zx + 0.152)) @ Matrix.Rotation(math.radians(-18), 4, "Y"), "SDT_Steel")

    # startér vzadu u zvonu a svorky pro kabely z baterie
    sy_ = ENG_BACK_Y + 0.04
    e.cyl(V(0.295, sy_, 0.77), V(0.335, sy_, 0.77), 0.030, "SDT_Steel", seg=14)
    e.cyl(V(0.335, sy_, 0.77), V(0.43, sy_, 0.77), 0.040, "SDT_PaintDark", seg=18)
    e.cyl(V(0.43, sy_, 0.77), V(0.44, sy_, 0.77), 0.037, "SDT_Steel", seg=18)
    e.cyl(V(0.345, sy_, 0.822), V(0.415, sy_, 0.822), 0.022, "SDT_ChargerGrey", seg=14)
    e.cyl(V(STARTER_PLUS.x, sy_, 0.838), STARTER_PLUS, 0.008, "SDT_Brass", seg=8)
    e.cyl(STARTER_MINUS, STARTER_MINUS + V(0, 0.016, 0), 0.010, "SDT_Brass", seg=8)
    e.finish()


def build_fuel_tank():
    """Palivová nádrž na naftu před motorem (osa podél X): sedla s pásky, hrdlo s řetízkem a sítkem, odvzdušnění, hodinový
    ukazatel hladiny, kulový uzávěr s palivovým čerpadlem a filtrem s odkalením, vypouštěcí šroub, přepad a štítek NAFTA.
    Vrací polohu hrdla."""
    x0, x1 = ENG_X0, ENG_X1
    ty, tz, tr = FUEL_Y, FUEL_Z, FUEL_R
    ya = ROW_Y - ENG_HW
    t = Mesh("Mill_FuelTank")
    t.cyl(V(x0 + 0.02, ty, tz), V(x1 - 0.02, ty, tz), tr, "SDT_PaintYellow", seg=32)
    for sx in (-1, 1):
        xe = x0 + 0.02 if sx < 0 else x1 - 0.02
        t.cyl(V(xe, ty, tz), V(xe - sx * 0.012, ty, tz), tr + 0.006, "SDT_PaintYellow", seg=32)
        t.torus(V(xe - sx * 0.006, ty, tz), V(1, 0, 0), tr, 0.008, "SDT_PaintYellow", seg=32, rseg=5)
    for x in (x0 + 0.10, x1 - 0.10):
        t.cyl(V(x - 0.012, ty, tz), V(x + 0.012, ty, tz), tr + 0.008, "SDT_Frame", seg=32)
        t.box(x - 0.025, x + 0.025, ty - 0.10, ty + 0.10, DECK_Z, tz - tr + 0.012, "SDT_Frame", bevel=0.004)
        t.box(x - 0.030, x + 0.030, ty - 0.11, ty + 0.11, DECK_Z, DECK_Z + 0.010, "SDT_Frame", bevel=0.003)
        for sy in (-1, 1):
            t.box(x - 0.012, x + 0.012, ty + sy * (tr + 0.008) - 0.010, ty + sy * (tr + 0.008) + 0.010, tz - 0.02, tz + 0.045, "SDT_Frame")
            t.cyl(V(x - 0.02, ty + sy * (tr + 0.020), tz + 0.02), V(x + 0.02, ty + sy * (tr + 0.020), tz + 0.02), 0.008, "SDT_Steel", seg=8)
    # hrdlo se sítkem, víčkem a řetízkem
    xm = (x0 + x1) / 2 + 0.03
    t.cyl(V(xm, ty, tz + tr - 0.012), V(xm, ty, tz + tr + 0.045), 0.045, "SDT_Steel", seg=24)
    t.cyl(V(xm, ty, tz + tr + 0.045), V(xm, ty, tz + tr + 0.052), 0.056, "SDT_Steel", seg=24)
    t.cyl(V(xm, ty, tz + tr + 0.052), V(xm, ty, tz + tr + 0.090), 0.052, "SDT_PaintRed", seg=24)
    t.cyl(V(xm, ty, tz + tr + 0.090), V(xm, ty, tz + tr + 0.098), 0.046, "SDT_PaintRed", seg=24)
    for k in range(8):
        a = TAU * k / 8
        t.box(xm + 0.055 * math.cos(a) - 0.005, xm + 0.055 * math.cos(a) + 0.005, ty + 0.055 * math.sin(a) - 0.005,
              ty + 0.055 * math.sin(a) + 0.005, tz + tr + 0.060, tz + tr + 0.082, "SDT_PaintRed")
    for k in range(6):
        t.torus(V(xm + 0.062 + 0.002 * k, ty + 0.012 * k, tz + tr + 0.048 - 0.008 * k), V(0, 1, 0) if k % 2 == 0 else V(1, 0, 0),
                0.010, 0.0025, "SDT_Steel", seg=8, rseg=4)
    # odvzdušnění a přepad
    t.cyl(V(x1 - 0.07, ty, tz + tr - 0.006), V(x1 - 0.07, ty, tz + tr + 0.035), 0.012, "SDT_Steel", seg=10)
    t.cyl(V(x1 - 0.07, ty, tz + tr + 0.035), V(x1 - 0.07, ty + 0.03, tz + tr + 0.055), 0.012, "SDT_Steel", seg=10)
    t.sphere(V(x1 - 0.07, ty + 0.03, tz + tr + 0.060), 0.016, "SDT_Plastic", seg=10, rings=5)
    # ukazatel hladiny: hodinový budík na přední straně
    gx, gy, gz = x0 + 0.20, ty - tr, tz + 0.02
    t.cyl(V(gx, gy + 0.004, gz), V(gx, gy - 0.016, gz), 0.045, "SDT_Frame", seg=28)
    t.cyl(V(gx, gy - 0.014, gz), V(gx, gy - 0.020, gz), 0.038, "SDT_PaintWhite", seg=28)
    t.torus(V(gx, gy - 0.020, gz), V(0, 1, 0), 0.040, 0.004, "SDT_Steel", seg=28, rseg=5)
    t.box(gx - 0.003, gx + 0.003, gy - 0.026, gy - 0.020, gz - 0.002, gz + 0.032, "SDT_PaintRed")
    t.box(gx - 0.030, gx + 0.030, gy - 0.024, gy - 0.020, gz - 0.032, gz - 0.028, "SDT_TankBlack")
    for k in range(5):
        a = math.radians(-60 + 30 * k)
        t.box(gx + 0.031 * math.sin(a) - 0.002, gx + 0.031 * math.sin(a) + 0.002, gy - 0.026, gy - 0.020,
              gz + 0.031 * math.cos(a) - 0.002, gz + 0.031 * math.cos(a) + 0.002, "SDT_TankBlack")
    # kulový uzávěr s pákou, čerpadlo a filtr s odkalovací miskou
    vx, vy, vz = x0 + 0.34, ty, tz - tr - 0.005
    t.cyl(V(vx, vy, vz), V(vx, vy, vz - 0.03), 0.020, "SDT_Brass", seg=12)
    t.sphere(V(vx, vy, vz - 0.045), 0.030, "SDT_Brass", seg=12, rings=6)
    t.cyl(V(vx, vy, vz - 0.045), V(vx + 0.09, vy, vz - 0.045), 0.012, "SDT_PaintRed", seg=8)
    t.sphere(V(vx + 0.095, vy, vz - 0.045), 0.015, "SDT_PaintRed", seg=8, rings=4)
    t.cyl(V(vx, vy, vz - 0.075), V(vx, vy, vz - 0.16), 0.014, "SDT_HoseBlack", seg=8)
    t.cyl(V(vx - 0.06, vy, vz - 0.17), V(vx + 0.06, vy, vz - 0.17), 0.026, "SDT_Plastic", seg=14)
    t.cyl(V(vx - 0.075, vy, vz - 0.17), V(vx - 0.06, vy, vz - 0.17), 0.030, "SDT_Steel", seg=14)
    t.cyl(V(vx + 0.06, vy, vz - 0.17), V(vx + 0.075, vy, vz - 0.17), 0.030, "SDT_Steel", seg=14)
    t.cyl(V(vx + 0.075, vy, vz - 0.17), V(vx + 0.075, vy, vz - 0.17) + V(0.07, 0, 0), 0.010, "SDT_HoseBlack", seg=8)
    t.cyl(V(vx + 0.145, vy, vz - 0.17), V(vx + 0.145, vy, vz - 0.17 + 0.14), 0.010, "SDT_HoseBlack", seg=8)
    t.cyl(V(vx - 0.075, vy, vz - 0.17), V(vx - 0.075 - 0.04, vy, vz - 0.17), 0.010, "SDT_HoseBlack", seg=8)
    # vypouštěcí šroub dole na zadní straně a štítek NAFTA na přední straně
    t.cyl(V(x1 - 0.18, ty + tr - 0.01, tz - 0.05), V(x1 - 0.18, ty + tr + 0.02, tz - 0.05), 0.014, "SDT_Steel", seg=8)
    t.box(x0 + 0.34, x0 + 0.34 + 0.20, ty - tr - 0.004, ty - tr + 0.010, tz - 0.075, tz + 0.015, "SDT_PaintDark",
          bevel=0.003)
    t.finish()
    return V(xm, ty, tz + tr + 0.098)


def _flange_ring(b, c, axis, r, thick=0.014, bolts=8, bolt_r=None):
    b.flange(c, axis, r, thick, "SDT_Steel", bolts=bolts, bolt_r=bolt_r or r * 0.78, bolt_size=0.007)


def build_bin():
    """Cyklonový odlučovač jemně mletého vápna vpravo od mlýnu (-X): válec s kuželem na stojanu, přírubové víko s vyústěním a filtračním rukávem,
    sání z mlýnu potrubím s koleny a přírubami (stoupačka z hrdla mlýnu k nátrubku ve válci), výstupní klapka s protizávažím,
    potrubí s kolenem a spojkou Storz vpravo (-X), stavoznak se sklem, ochrannou klecí a plovákem."""
    x, y = BIN_XY
    R = BIN_R
    zb = BIN_CONE_Z0
    zj = zb + BIN_CONE_H
    zt = zj + BIN_BODY_H
    b = Mesh("Mill_Bin")
    s = Mesh("Mill_Bin_Stand")
    prof = [(0.0, zb), (0.06, zb), (R, zj), (R + 0.004, zj + 0.012), (R, zj + 0.024), (R, zt - 0.03), (R - 0.012, zt), (R - 0.03, zt),
            (R - 0.03, zt - 0.012), (0.0, zt - 0.012)]
    b.lathe(prof, V(x, y, 0), V(0, 0, 1), "SDT_PaintGrey", seg=40, hard=(1, 2, 4, 6))
    for z in (zb + 0.10, zb + 0.20):
        rz = 0.06 + (R - 0.06) * (z - zb) / BIN_CONE_H
        b.torus(V(x, y, z), V(0, 0, 1), rz + 0.003, 0.005, "SDT_Frame", seg=40, rseg=4)
    # víko: přírubový prstenec se šrouby, vyústění (vírová trubka) s kolenem a filtračním rukávem
    b.cyl(V(x, y, zt - 0.004), V(x, y, zt + 0.014), R + 0.012, "SDT_Frame", seg=40)
    b.bolt_circle(V(x, y, zt + 0.014), V(0, 0, 1), R - 0.008, 10, 0.007, 0.007, "SDT_Steel")
    b.cyl(V(x, y, zt + 0.014), V(x, y, zt + 0.13), 0.050, "SDT_Steel", seg=14)
    b.flange(V(x, y, zt + 0.06), V(0, 0, 1), 0.078, 0.012, "SDT_Steel", bolts=6, bolt_r=0.064, bolt_size=0.006)
    b.sphere(V(x, y, zt + 0.16), 0.058, "SDT_Steel", seg=14, rings=6)
    b.cyl(V(x, y, zt + 0.16), V(x, y + 0.11, zt + 0.16), 0.050, "SDT_Steel", seg=14)
    b.flange(V(x, y + 0.07, zt + 0.16), V(0, 1, 0), 0.078, 0.012, "SDT_Steel", bolts=6, bolt_r=0.064, bolt_size=0.006)
    b.cyl(V(x, y + 0.11, zt + 0.16), V(x, y + 0.21, zt + 0.16), 0.060, "SDT_Mesh", seg=14)
    for dy in (0.14, 0.18):
        b.torus(V(x, y + dy, zt + 0.16), V(0, 1, 0), 0.061, 0.005, "SDT_Steel", seg=16, rseg=4)
    b.cyl(V(x, y + 0.21, zt + 0.16), V(x, y + 0.22, zt + 0.16), 0.062, "SDT_Frame", seg=14)
    # tlakový ventil a revizní poklop na víku
    b.cyl(V(x + 0.09, y - 0.07, zt + 0.014), V(x + 0.09, y - 0.07, zt + 0.07), 0.026, "SDT_Steel", seg=14)
    b.cyl(V(x + 0.09, y - 0.07, zt + 0.07), V(x + 0.09, y - 0.07, zt + 0.095), 0.018, "SDT_PaintRed", seg=14)
    b.obox((0.14, 0.12, 0.012), Matrix.Translation(V(x - 0.07, y - 0.08, zt + 0.020)), "SDT_Frame", bevel=0.003)
    # sání: stoupačka od příruby hrdla mlýna (čelo MILL_OUT_X) přes koleno k nátrubku s přírubou v boku válce
    ox = -0.455
    b.flange(V(MILL_OUT_X, y, MILL_Z), V(-1, 0, 0), 0.108, 0.012, "SDT_Steel", bolts=4, bolt_r=0.090, bolt_size=0.007)
    b.cyl(V(MILL_OUT_X - 0.012, y, MILL_Z), V(ox, y, MILL_Z), 0.050, "SDT_Steel", seg=14)
    b.sphere(V(ox, y, MILL_Z), 0.056, "SDT_Steel", seg=14, rings=6)
    zin = 1.28
    b.cyl(V(ox, y, MILL_Z), V(ox, y, zin), 0.050, "SDT_Steel", seg=14)
    for z in (0.98, 1.14):
        b.flange(V(ox, y, z - 0.007), V(0, 0, 1), 0.075, 0.014, "SDT_Steel", bolts=4, bolt_r=0.061, bolt_size=0.006)
    b.sphere(V(ox, y, zin), 0.056, "SDT_Steel", seg=14, rings=6)
    wall = x + R
    b.cyl(V(ox, y, zin), V(wall - 0.004, y, zin), 0.050, "SDT_Steel", seg=14)
    b.flange(V(wall + 0.018, y, zin), V(-1, 0, 0), 0.075, 0.020, "SDT_Steel", bolts=4, bolt_r=0.061, bolt_size=0.006)
    # výpust: příruba pod kuželem, tělo klapky s protizávažím, koleno, potrubí s přírubou a spojkou Storz (-X)
    b.flange(V(x, y, zb), V(0, 0, -1), 0.088, 0.012, "SDT_Steel", bolts=6, bolt_r=0.070, bolt_size=0.006)
    zh = zb - 0.012
    b.obox((0.16, 0.16, 0.062), Matrix.Translation(V(x, y, zh - 0.031)), "SDT_PaintGrey", bevel=0.010, segments=2)
    za = zh - 0.031
    b.cyl(V(x, y - 0.10, za), V(x, y + 0.11, za), 0.009, "SDT_Steel", seg=10)
    b.obox((0.012, 0.10, 0.014), Matrix.Translation(V(x + 0.012, y + 0.15, za)), "SDT_Steel")
    b.cyl(V(x - 0.035, y + 0.20, za), V(x + 0.035, y + 0.20, za), 0.026, "SDT_Frame", seg=14)
    b.sphere(V(x, y, PORT_Z), 0.058, "SDT_Steel", seg=14, rings=6)
    b.cyl(V(x, y, zh - 0.060), V(x, y, PORT_Z), 0.055, "SDT_Steel", seg=14)
    px = PORT_X
    b.cyl(V(x, y, PORT_Z), V(px + 0.07, y, PORT_Z), 0.055, "SDT_Steel", seg=14)
    b.flange(V(x - 0.17, y, PORT_Z), V(-1, 0, 0), 0.085, 0.014, "SDT_Steel", bolts=6, bolt_r=0.068, bolt_size=0.006)
    b.storz(V(px, y, PORT_Z), V(1, 0, 0), collar="SDT_PaintRed")
    # stavoznak: dvě mosazné odbočky do pláště, skleněná trubice s plovákem, ochranná klec ze dvou tyčí a štítek s dílky
    gy = y - R - 0.032
    z0, z1 = zj + 0.06, zj + 0.40
    for z in (z0, z1):
        b.cyl(V(x, y - R + 0.004, z), V(x, gy, z), 0.012, "SDT_Brass", seg=10)
        b.sphere(V(x, gy, z), 0.017, "SDT_Brass", seg=10, rings=5)
    b.cyl(V(x, gy, z0), V(x, gy, z1), 0.014, "SDT_Screen", seg=14)
    b.cyl(V(x, gy, z0 + 0.10), V(x, gy, z0 + 0.15), 0.0105, "SDT_PaintYellow", seg=10)
    for sx in (-1, 1):
        b.cyl(V(x + sx * 0.030, gy - 0.006, z0 - 0.01), V(x + sx * 0.030, gy - 0.006, z1 + 0.01), 0.0055, "SDT_Steel", seg=6)
    b.box(x - 0.045, x + 0.045, gy - 0.026, gy - 0.020, z0, z1, "SDT_PaintDark", bevel=0.002)
    for k in range(9):
        zz = z0 + 0.03 + k * 0.035
        b.box(x - 0.022, x + 0.022, gy - 0.0215, gy - 0.0200, zz - 0.002, zz + 0.002, "SDT_PaintWhite")
    b.box(x - 0.09, x + 0.09, y - R - 0.008, y - R + 0.030, zj + 0.43, zj + 0.49, "SDT_PaintWhite", bevel=0.003)
    # stojan: čtyři nohy, rám
    h = 0.155
    for sx in (-1, 1):
        for sy in (-1, 1):
            f = V(x + sx * h, y + sy * h, DECK_Z)
            t = V(x + sx * h, y + sy * h, zj + 0.02)
            s.cyl(f, t, 0.020, "SDT_Frame", square=True, ref=V(1, 0, 0))
            s.box(f.x - 0.045, f.x + 0.045, f.y - 0.045, f.y + 0.045, DECK_Z, DECK_Z + 0.010, "SDT_Frame", bevel=0.003)
    for z in (DECK_Z + 0.30, zj - 0.06):
        s.cyl(V(x - h, y - h, z), V(x + h, y - h, z), 0.014, "SDT_Frame", square=True, ref=V(0, 0, 1))
        s.cyl(V(x - h, y + h, z), V(x + h, y + h, z), 0.014, "SDT_Frame", square=True, ref=V(0, 0, 1))
        for sx in (-1, 1):
            s.cyl(V(x + sx * h, y - h, z), V(x + sx * h, y + h, z), 0.014, "SDT_Frame", square=True, ref=V(1, 0, 0))
    b.finish()
    s.finish()
    P.empty("millOutletPort", V(px, y, PORT_Z)).empty_display_size = 0.10


def _bez(p0, p1, p2, p3, n=12):
    out = []
    for k in range(n + 1):
        t = k / n
        u = 1 - t
        out.append(u ** 3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t ** 3 * p3)
    return out


HOSE_TILES_M = 32.0      # závitů spirály na metr hadice (stoupání ~3 cm), shodně s články hadic (build_pump.HOSE_TILES)


def _hose_end(m, p, d, collar="SDT_PaintRed"):
    """Koncovka hadice (hadice má poloměr 0,032 m): zmenšená spojka Storz (prstenec s těsněním, tři ploché packy, červená objímka), kuželový
    přechod na hrdlo a lisovaná objímka se dvěma šroubovými sponami (délka koncovky 0,106 m). Žádná pevná gumová ochrana ohybu: hadice vychází
    rovnou z objímky a ohýbá se až za ní, takže z ohnuté hadice nic netrčí. p = čelo spojky, d = směr dovnitř hadice."""
    p, d = Vector(p), Vector(d).normalized()
    m.storz(p, d, collar=collar, scale=0.62)
    m.cyl(p + d * 0.026, p + d * 0.052, 0.0455, "SDT_AluCast", r1=0.0385, seg=24)
    m.lathe([(0.0335, 0.050), (0.0425, 0.050), (0.0425, 0.057), (0.0405, 0.057), (0.0405, 0.106), (0.0335, 0.106)], p, d, "SDT_Steel",
            seg=24, loop=True)
    for z in (0.066, 0.092):
        m.clamp(p + d * z, d, 0.0405, "SDT_Steel", width=0.012)


def build_hopper_detail():
    cx, cy = HOPPER_CX, HOPPER_CY
    hx, hy = HOPPER_HX, HOPPER_HY
    zt = HOPPER_TOP_Z
    zs = HOPPER_RIM_Z
    h = Mesh("Mill_HopperDetail")
    zm = (zs + zt) / 2 - 0.02
    h.box(cx - hx - 0.010, cx + hx + 0.010, cy - hy - 0.010, cy + hy + 0.010, zm - 0.018, zm + 0.018, "SDT_Alu", bevel=0.004)
    # šrouby v pásech
    for z in (zs + 0.02, zm, zt - 0.14):
        x = -hx + 0.10
        while x < hx - 0.05:
            for sy in (-1, 1):
                h.hex(V(cx + x, cy + sy * (hy + 0.010), z), V(0, sy, 0), 0.010, 0.008, "SDT_Steel")
            x += 0.14
        y = -hy + 0.10
        while y < hy - 0.05:
            for sx in (-1, 1):
                h.hex(V(cx + sx * (hx + 0.010), cy + y, z), V(sx, 0, 0), 0.010, 0.008, "SDT_Steel")
            y += 0.14
    # průhled s měřítkem na boku +X
    gy = cy - 0.30
    h.box(cx + hx, cx + hx + 0.024, gy - 0.045, gy + 0.045, zs + 0.04, zt - 0.05, "SDT_Frame", bevel=0.004)
    h.box(cx + hx + 0.020, cx + hx + 0.030, gy - 0.026, gy + 0.026, zs + 0.07, zt - 0.08, "SDT_Screen", bevel=0.003)
    z = zs + 0.09
    while z < zt - 0.10:
        h.box(cx + hx + 0.024, cx + hx + 0.032, gy + 0.032, gy + 0.075, z - 0.004, z + 0.004, "SDT_PaintWhite")
        z += 0.05
    # táhla na šikmých hranách násypky
    for sx in (-1, 1):
        for sy in (-1, 1):
            a = V(cx + sx * (hx + 0.014), cy + sy * (hy + 0.014), zs + 0.02)
            b = V(cx + sx * 0.235, cy + sy * 0.235, HOPPER_OUT_Z + 0.04)
            h.cyl(a, b, 0.013, "SDT_Frame", seg=8)
    # vibrátor na šikmé stěně vpředu
    t = 0.45
    zf = HOPPER_OUT_Z + t * (zs - HOPPER_OUT_Z)
    yf = cy - (0.22 + (hy - 0.22) * t)
    nrm = V(0, -(zs - HOPPER_OUT_Z), -(hy - 0.22)).normalized()
    ang = math.atan2(nrm.z, nrm.y)
    base = V(cx + 0.28, yf, zf) + nrm * 0.006
    h.obox((0.34, 0.012, 0.20), Matrix.Translation(base) @ Matrix.Rotation(ang - math.pi / 2, 4, "X"), "SDT_Frame", bevel=0.003)
    vc = base + nrm * 0.075
    h.cyl(vc - V(0.14, 0, 0), vc + V(0.14, 0, 0), 0.062, "SDT_PaintDark", seg=24)
    for sx in (-1, 1):
        h.cyl(vc + V(sx * 0.14, 0, 0), vc + V(sx * 0.17, 0, 0), 0.070, "SDT_Steel", seg=24)
        h.cyl(vc + V(sx * 0.14, 0, 0) - nrm * 0.035, base + V(sx * 0.14, 0, 0), 0.012, "SDT_Frame", seg=8)
    h.box(vc.x - 0.05, vc.x + 0.05, vc.y - 0.05, vc.y + 0.05, vc.z + 0.055, vc.z + 0.085, "SDT_PaintDark", bevel=0.005)
    # oka na zvedání na okraji
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = V(cx + sx * (hx - 0.03), cy + sy * (hy - 0.03), zt + 0.045)
            h.cyl(c, c + V(0, 0, 0.022), 0.032, "SDT_Frame", seg=14)
            h.torus(c + V(0, 0, 0.060), V(1, 0, 0), 0.036, 0.009, "SDT_Frame", seg=18, rseg=5)
    # madlo na předním okraji
    for sx in (-1, 1):
        h.cyl(V(cx + sx * 0.20, cy - hy - 0.012, zt + 0.045), V(cx + sx * 0.20, cy - hy - 0.075, zt + 0.045), 0.010, "SDT_Steel", seg=8)
        h.cyl(V(cx + sx * 0.20, cy - hy - 0.075, zt + 0.045), V(cx + sx * 0.20, cy - hy - 0.075, zt + 0.020), 0.010, "SDT_Steel", seg=8)
    h.cyl(V(cx - 0.20, cy - hy - 0.075, zt + 0.045), V(cx + 0.20, cy - hy - 0.075, zt + 0.045), 0.010, "SDT_Steel", seg=8)
    # šoupátko ve výsypce nádoby
    yy = HOPPER_CY - 0.10
    zg = 0.96
    h.box(cx - 0.20, cx + 0.40, yy - 0.115, yy + 0.115, zg - 0.008, zg + 0.008, "SDT_Steel", bevel=0.002)
    h.box(cx + 0.14, cx + 0.40, yy - 0.135, yy - 0.115, zg - 0.025, zg + 0.025, "SDT_Frame", bevel=0.003)
    h.box(cx + 0.14, cx + 0.40, yy + 0.115, yy + 0.135, zg - 0.025, zg + 0.025, "SDT_Frame", bevel=0.003)
    h.cyl(V(cx + 0.40, yy, zg), V(cx + 0.46, yy, zg), 0.012, "SDT_Steel", seg=8)
    h.cyl(V(cx + 0.46, yy - 0.04, zg), V(cx + 0.46, yy + 0.04, zg), 0.012, "SDT_PaintRed", seg=10)
    h.finish()


def build_control_box():
    """Rozvaděč na předním levém sloupku nádoby: hranatá skříňka s jedním velkým tlačítkem (start/stop) a světelným prstencem kolem něj.
    Prstenec je samostatný mesh millStartRing z materiálu SDT_NavLed (zelená barva ve vrcholech); skript ho rozsvítí za chodu mlýnku.
    Kabel jde z průchodky dolů po sloupku na příchytkách do krabičky na palubě. Vrací střed tlačítka (uzel millStartButton)."""
    px = HOPPER_CX + HOPPER_HX - 0.07
    py = HOPPER_CY - HOPPER_HY + 0.07
    y0 = py - 0.033                       # čelo sloupku
    zc = 1.20
    c = Mesh("Mill_Control")
    yb = y0 - 0.008                       # čelo montážní desky
    c.box(px - 0.075, px + 0.075, yb, y0, zc - 0.11, zc + 0.11, "SDT_Frame", bevel=0.003)
    for sx in (-1, 1):
        for sz in (-1, 1):
            c.hex(V(px + sx * 0.055, yb, zc + sz * 0.098), V(0, -1, 0), 0.0055, 0.005, "SDT_Steel")
    c.box(px - 0.065, px + 0.065, yb - 0.060, yb, zc - 0.085, zc + 0.085, "SDT_PaintDark", bevel=0.006)
    yf = yb - 0.076                       # čelo víka
    c.box(px - 0.068, px + 0.068, yf, yb - 0.060, zc - 0.088, zc + 0.088, "SDT_PaintGrey", bevel=0.004)
    for sx in (-1, 1):
        for sz in (-1, 1):
            c.hex(V(px + sx * 0.052, yf, zc + sz * 0.070), V(0, -1, 0), 0.0065, 0.005, "SDT_Steel")
    b = V(px, yf, zc + 0.012)             # střed tlačítka
    c.cyl(b, b + V(0, -0.009, 0), 0.048, "SDT_Steel", seg=32)
    c.cyl(b + V(0, -0.004, 0), b + V(0, -0.022, 0), 0.029, "SDT_Plastic", seg=32)
    c.cyl(b + V(0, -0.022, 0), b + V(0, -0.027, 0), 0.027, "SDT_Plastic", r1=0.020, seg=32)
    # kabel: průchodka pod skříňkou, dolů po čele sloupku (dvě příchytky) do krabičky na palubě
    c.cyl(V(px, yb - 0.030, zc - 0.085), V(px, yb - 0.030, zc - 0.100), 0.011, "SDT_Plastic", seg=12)
    rc = 0.0065
    zj = DECK_Z + 0.050
    yk = y0 - rc
    cab = _spline([V(px, yb - 0.030, zc - 0.100), V(px, yb - 0.030, zc - 0.140), V(px, yk, zc - 0.190), V(px, yk, 0.90), V(px, yk, 0.75),
                   V(px, yk, zj)], 5)
    c.pipe(cab, rc, "SDT_HoseBlack", seg=6, caps=False)
    for z in (0.93, 0.77):
        _clip(c, V(px, yk, z), V(0, 0, -1), V(0, -1, 0), rc)
    c.box(px - 0.040, px + 0.040, y0 - 0.060, y0, DECK_Z, zj, "SDT_PaintDark", bevel=0.004)
    c.cyl(V(px, yk, zj), V(px, yk, zj + 0.004), 0.011, "SDT_Plastic", seg=12)
    c.finish()

    ring = Mesh("millStartRing")
    ring.lathe([(0.030, 0.009), (0.040, 0.009), (0.040, 0.0135), (0.030, 0.0135)], b, V(0, -1, 0), "SDT_NavLed", seg=32, loop=True)
    obj = ring.finish()
    attr = obj.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for item in attr.data:
        item.color_srgb = (0.05, 0.90, 0.15, 1.0)
    obj.data.color_attributes.render_color_index = 0
    return b


def build_deck_details():
    """Akumulátor za motorem, klíny pod kola, obrysová světla."""
    d = Mesh("Mill_DeckDetails")
    bx0, bx1, by0, by1 = 0.52, 0.80, 0.16, 0.36
    bz0, bz1 = DECK_Z + 0.02, DECK_Z + 0.25
    d.box(bx0 - 0.02, bx1 + 0.02, by0 - 0.02, by1 + 0.02, DECK_Z, DECK_Z + 0.02, "SDT_Frame", bevel=0.003)
    d.box(bx0, bx1, by0, by1, bz0, bz1, "SDT_BatteryGrey", bevel=0.008)
    d.box(bx0 + 0.01, bx1 - 0.01, by0 + 0.01, by1 - 0.01, bz1, bz1 + 0.008, "SDT_PaintDark", bevel=0.004)
    for sx, mat in ((-1, "SDT_PaintRed"), (1, "SDT_TankBlack")):
        x = (bx0 + bx1) / 2 + sx * 0.085
        d.cyl(V(x, by0 + 0.045, bz1 + 0.008), V(x, by0 + 0.045, bz1 + 0.030), 0.014, mat, seg=12)
    for y in (by0 + 0.015, by1 - 0.015):
        d.box(bx0 - 0.004, bx1 + 0.004, y - 0.008, y + 0.008, bz0 + 0.04, bz0 + 0.06, "SDT_Frame")
    for sx, mat in ((-1, "SDT_PaintRed"), (1, "SDT_TankBlack")):
        x = (bx0 + bx1) / 2 + sx * 0.085
        end = STARTER_PLUS if sx < 0 else STARTER_MINUS
        pts = _bez(V(x, by0 + 0.045, bz1 + 0.030), V(x, by0 - 0.04, bz1 + 0.06), V(end.x, ENG_BACK_Y + 0.12, 0.92), end, 8)
        for a, b in zip(pts, pts[1:]):
            d.cyl(a, b, 0.0075, mat, seg=6)
    # odvodňovací otvory v palubě (tmavé podélné otvory) mezi zařízením
    for y in (0.25, 0.42, 0.59):
        for x in (-0.60, -0.40, -0.20, 0.0, 0.20, 0.40):
            d.box(x - 0.05, x + 0.05, y - 0.014, y + 0.014, DECK_Z + 0.0005, DECK_Z + 0.002, "SDT_Plastic")
    for y in (-0.62, -0.69):
        for x in (-0.78, -0.62):
            d.box(x - 0.05, x + 0.05, y - 0.014, y + 0.014, DECK_Z + 0.0005, DECK_Z + 0.002, "SDT_Plastic")
    # klíny pod kola, zavěšené vzadu na háčcích
    for x in (0.34, 0.54):
        d.cyl(V(x, Y_REAR + 0.012, DECK_Z - 0.03), V(x, Y_REAR + 0.050, DECK_Z - 0.03), 0.009, "SDT_Steel", seg=6)
        c = V(x, Y_REAR + 0.085, DECK_Z - 0.10)
        d.obox((0.14, 0.26, 0.11), Matrix.Translation(c) @ Matrix.Rotation(math.radians(-15), 4, "X"), "SDT_PaintYellow", bevel=0.012)
        d.obox((0.15, 0.26, 0.018), Matrix.Translation(c + V(0, 0, -0.055)) @ Matrix.Rotation(math.radians(-15), 4, "X"), "SDT_Rubber")
    # obrysová světla na bocích a bílá vpředu
    for sx in (-1, 1):
        for y in (Y_FRONT + 0.16, 0.50, Y_REAR - 0.16):
            d.box(sx * (DECK_HX + 0.020) - 0.012, sx * (DECK_HX + 0.020) + 0.012, y - 0.045, y + 0.045, DECK_Z - 0.015, DECK_Z + 0.04,
                  "SDT_LampAmber", bevel=0.004)
        d.box(sx * 0.70 - 0.045, sx * 0.70 + 0.045, Y_FRONT - 0.034, Y_FRONT - 0.016, DECK_Z + 0.075, DECK_Z + 0.115, "SDT_TapeWhite",
              bevel=0.004)
    d.finish()


def build_engine_detail():
    """Drobnosti motoru: palivový filtr a vstřikovací čerpadlo na přední straně skříně, vstřikovací trubka, hadice z nádrže,
    olejový filtr, víko skříně, měrka s hrdlem oleje, páčka plynu a závěsné oko."""
    e = Mesh("Mill_EngineDetail")
    cy, zc = ROW_Y, MILL_Z
    yf = ENG_FRONT_Y
    cxx = ENG_CYL_X
    ya = ROW_Y - ENG_HW

    fx = 0.40
    e.box(fx - 0.03, fx + 0.03, yf - 0.03, yf, 0.835, 0.865, "SDT_Frame", bevel=0.003)
    e.cyl(V(fx, yf - 0.045, 0.80), V(fx, yf - 0.045, 0.885), 0.024, "SDT_Plastic", seg=16)
    e.cyl(V(fx, yf - 0.045, 0.885), V(fx, yf - 0.045, 0.898), 0.029, "SDT_Steel", seg=16)
    e.cyl(V(fx, yf - 0.045, 0.790), V(fx, yf - 0.045, 0.800), 0.029, "SDT_Steel", seg=16)
    e.cyl(V(fx, yf - 0.045, 0.898), V(fx, yf - 0.045, 0.915), 0.009, "SDT_Brass", seg=8)
    e.cyl(V(fx + 0.015, yf - 0.045, 0.892), V(fx + 0.045, yf - 0.045, 0.892), 0.008, "SDT_Brass", seg=8)

    px, pz = 0.50, 0.87
    e.cyl(V(px, yf, pz), V(px, yf - 0.052, pz), 0.025, "SDT_Steel", seg=16)
    e.cyl(V(px, yf - 0.052, pz), V(px, yf - 0.066, pz), 0.019, "SDT_Brass", seg=14)
    e.cyl(V(px, yf - 0.035, pz + 0.020), V(px, yf - 0.035, pz + 0.034), 0.009, "SDT_Brass", seg=8)
    pts = _bez(V(px, yf - 0.035, pz + 0.034), V(px, yf - 0.002, 1.05), V(cxx + 0.04, yf + 0.03, 1.15), V(cxx + 0.04, cy - 0.07, ZH0 + 0.075), 10)
    for a, b in zip(pts, pts[1:]):
        e.cyl(a, b, 0.0045, "SDT_Steel", seg=5, caps=False)
    e.cyl(V(cxx + 0.04, cy - 0.07, ZH0 + 0.05), V(cxx + 0.04, cy - 0.07, ZH0 + 0.09), 0.013, "SDT_Steel", seg=10)
    e.hex(V(cxx + 0.04, cy - 0.07, ZH0 + 0.09), V(0, 0, 1), 0.012, 0.010, "SDT_Steel")

    vx, vz = ENG_X0 + 0.34, FUEL_Z - FUEL_R - 0.005
    pts = _bez(V(vx + 0.145, FUEL_Y, vz - 0.03), V(vx + 0.145, FUEL_Y + 0.10, vz - 0.05), V(0.52, yf - 0.115, 0.83),
               V(fx + 0.0, yf - 0.045, 0.915), 10)
    for a, b in zip(pts, pts[1:]):
        e.cyl(a, b, 0.0085, "SDT_HoseBlack", seg=6, caps=False)
    pts = _bez(V(fx + 0.045, yf - 0.045, 0.892), V(fx + 0.07, yf - 0.045, 0.892), V(px - 0.03, yf - 0.06, 0.915), V(px, yf - 0.035, pz + 0.034), 6)
    for a, b in zip(pts, pts[1:]):
        e.cyl(a, b, 0.0075, "SDT_HoseBlack", seg=6, caps=False)

    ox = 0.555
    e.cyl(V(ox, yf, 0.735), V(ox, yf - 0.075, 0.735), 0.033, "SDT_PumpBlue", seg=18)
    e.cyl(V(ox, yf - 0.075, 0.735), V(ox, yf - 0.083, 0.735), 0.036, "SDT_Steel", seg=18)
    e.cyl(V(ox, yf, 0.735), V(ox, yf - 0.010, 0.735), 0.042, "SDT_Steel", seg=18)

    cvx, cvz = 0.47, 0.775
    e.cyl(V(cvx, yf, cvz), V(cvx, yf - 0.010, cvz), 0.050, "SDT_ChargerGrey", seg=24)
    e.bolt_circle(V(cvx, yf - 0.010, cvz), V(0, -1, 0), 0.040, 6, 0.006, 0.006, "SDT_Steel")

    e.cyl(V(0.52, cy + 0.115, 0.93), V(0.52, cy + 0.115, 0.965), 0.008, "SDT_Steel", seg=8)
    e.torus(V(0.52, cy + 0.115, 0.982), V(1, 0, 0), 0.014, 0.0035, "SDT_PaintYellow", seg=14, rseg=4)
    e.cyl(V(0.36, cy + 0.10, 0.93), V(0.36, cy + 0.10, 0.955), 0.024, "SDT_Steel", seg=14)
    e.cyl(V(0.36, cy + 0.10, 0.955), V(0.36, cy + 0.10, 0.978), 0.028, "SDT_PaintYellow", seg=14)

    lx = 0.665
    e.cyl(V(lx, yf - 0.010, 0.92), V(lx, yf - 0.032, 0.97), 0.005, "SDT_Steel", seg=5, caps=False)
    e.cyl(V(lx, yf - 0.032, 0.97), V(lx + 0.00, yf - 0.040, 1.000), 0.005, "SDT_Steel", seg=5, caps=False)
    e.sphere(V(lx, yf - 0.041, 1.010), 0.014, "SDT_PaintYellow", seg=10, rings=5)
    e.cyl(V(lx, yf, 0.915), V(lx, yf - 0.012, 0.915), 0.014, "SDT_Steel", seg=10)

    e.torus(V(0.605, cy, 1.05), V(0, 1, 0), 0.022, 0.0045, "SDT_Steel", seg=14, rseg=4)
    for sy in (-1, 1):
        e.hex(V(0.69, cy + sy * 0.06, 1.0127), V(0, 0, 1), 0.009, 0.007, "SDT_Steel")
    e.finish()


def build_mill_detail():
    m = Mesh("Mill_Detail")
    zc = MILL_Z
    R = MILL_R
    top = V(MILL_X, ROW_Y, zc + R + 0.016)
    m.cyl(top, top + V(0, 0, 0.03), 0.030, "SDT_Frame", seg=12)
    m.torus(top + V(0, 0, 0.055), V(1, 0, 0), 0.034, 0.009, "SDT_Frame", seg=18, rseg=5)
    dx = MILL_X - 0.185
    dy = ROW_Y - R - 0.003
    for z in (zc - 0.10, zc + 0.14):
        m.cyl(V(dx, dy - 0.012, z - 0.035), V(dx, dy - 0.012, z + 0.035), 0.012, "SDT_Steel", seg=10)
    for x in (MILL_X - MILL_HL + 0.015, MILL_X + MILL_HL - 0.015):
        m.cyl(V(x, ROW_Y + R + 0.022, zc), V(x, ROW_Y + R + 0.055, zc), 0.007, "SDT_Steel", seg=8)
        m.sphere(V(x, ROW_Y + R + 0.058, zc), 0.011, "SDT_Brass", seg=8, rings=4)
    for k in range(6):
        x = MILL_X - 0.15 + k * 0.06
        m.box(x - 0.005, x + 0.005, ROW_Y + R - 0.004, ROW_Y + R + 0.020, zc - 0.10, zc + 0.05, "SDT_GenOrange")
    m.finish()


def build_port_cap():
    """Slepá krytka spojky Storz s řetízkem na hadicové spojce nádobky (když není hadice připojena)."""
    y = BIN_XY[1]
    px = PORT_X
    c = Mesh("Mill_PortCap")
    c.cyl(V(px - 0.004, y, PORT_Z), V(px - 0.040, y, PORT_Z), 0.090, "SDT_AluCast", r1=0.084, seg=28)
    c.cyl(V(px - 0.040, y, PORT_Z), V(px - 0.050, y, PORT_Z), 0.068, "SDT_AluCast", seg=28)
    c.cyl(V(px - 0.056, y, PORT_Z - 0.050), V(px - 0.056, y, PORT_Z + 0.050), 0.009, "SDT_Steel", seg=8)
    for dz in (-0.04, 0.04):
        c.cyl(V(px - 0.050, y, PORT_Z + dz), V(px - 0.056, y, PORT_Z + dz), 0.006, "SDT_Steel", seg=6)
    anchor = V(px - 0.05, y + 0.07, PORT_Z + 0.09)
    for k in range(7):
        axis = V(0, 1, 0) if k % 2 == 0 else V(1, 0, 0)
        c.torus(V(anchor.x, anchor.y + 0.004 * k, anchor.z - k * 0.030), axis, 0.012, 0.0028, "SDT_Steel", seg=10, rseg=4)
    c.finish()


def build_extra_details():
    """Další součástky: upevňovací oka na paluze, revizní poklop a svorkovnice šneku, silentbloky, tlakoměr a čidla na mlýně, sonda a poklop nádobky, závěs a visací zámek
    mřížky nádoby."""
    d = Mesh("Mill_ExtraDetails")
    # upevňovací oka na paluze
    for sx in (-1, 1):
        for y in (-0.55, 0.60, 2.05):
            x = sx * (DECK_HX + 0.002)
            d.box(min(x, x + sx * 0.040), max(x, x + sx * 0.040), y - 0.040, y + 0.040, DECK_Z - 0.04, DECK_Z + 0.02, "SDT_Frame", bevel=0.004)
            d.torus(V(x + sx * 0.052, y, DECK_Z - 0.01), V(1, 0, 0), 0.026, 0.006, "SDT_Steel", seg=14, rseg=5)
    # šnek: revizní poklop, svorkovnice motoru
    p0, p1 = AUGER_P0, AUGER_P1
    dd = (p1 - p0).normalized()
    side = dd.cross(V(0, 0, 1)).normalized()
    up = side.cross(dd).normalized()
    c = p0 + (p1 - p0) * 0.62 + up * 0.121
    d.obox((0.22, 0.15, 0.010), frame(c, up, ref=dd), "SDT_Frame", bevel=0.003)
    for sa in (-1, 1):
        for sb in (-1, 1):
            d.hex(c + dd * (sa * 0.09) + side * (sb * 0.06) + up * 0.006, up, 0.009, 0.008, "SDT_Steel")
    d.torus(c + up * 0.016, up, 0.030, 0.006, "SDT_Steel", seg=14, rseg=5)
    ct = p1 - dd * 0.20
    d.box(ct.x - 0.045, ct.x + 0.045, ct.y - 0.035, ct.y + 0.035, ct.z + 0.080, ct.z + 0.125, "SDT_PaintDark", bevel=0.005)
    d.cyl(ct + V(0.045, 0, 0.100), ct + V(0.075, 0, 0.100), 0.010, "SDT_Steel", seg=8)
    d.cyl(ct + V(0, 0, 0.125), ct + V(0, 0, 0.14), 0.015, "SDT_Steel", seg=8)
    # mlýn: tlakoměr, teplotní čidla, silentbloky
    zc, R = MILL_Z, MILL_R
    gx, gy = MILL_X + 0.17, ROW_Y + 0.12
    d.cyl(V(gx, gy, zc + R - 0.01), V(gx, gy, zc + R + 0.045), 0.010, "SDT_Steel", seg=8)
    d.cyl(V(gx, gy + 0.025, zc + R + 0.075), V(gx, gy - 0.012, zc + R + 0.075), 0.036, "SDT_Frame", seg=24)
    d.cyl(V(gx, gy - 0.010, zc + R + 0.075), V(gx, gy - 0.016, zc + R + 0.075), 0.030, "SDT_PaintWhite", seg=24)
    d.box(gx - 0.002, gx + 0.002, gy - 0.021, gy - 0.016, zc + R + 0.075, zc + R + 0.100, "SDT_PaintRed")
    for k in range(2):
        px = MILL_X - 0.12 + k * 0.17
        d.cyl(V(px, ROW_Y + R * 0.93, zc + R * 0.37), V(px, ROW_Y + R + 0.07, zc + R * 0.37 + 0.03), 0.011, "SDT_Brass", seg=8)
    for x in (MILL_X - MILL_HL + 0.06, MILL_X + MILL_HL - 0.09):
        for sy in (-1, 1):
            d.cyl(V(x, ROW_Y + sy * 0.24, DECK_Z), V(x, ROW_Y + sy * 0.24, DECK_Z + 0.03), 0.035, "SDT_Rubber", seg=14)
    # cyklónová nádobka: sonda hladiny, tlakový ventil a revizní poklop na zádi
    bx_, by_ = BIN_XY
    zt = BIN_CONE_Z0 + BIN_CONE_H + BIN_BODY_H
    zh = BIN_CONE_Z0 + BIN_CONE_H + 0.28
    d.cyl(V(bx_ + 0.07, by_ - 0.06, zt - 0.01), V(bx_ + 0.07, by_ - 0.06, zt + 0.15), 0.006, "SDT_Steel", seg=8)
    d.box(bx_ + 0.04, bx_ + 0.10, by_ - 0.09, by_ - 0.03, zt + 0.15, zt + 0.19, "SDT_PaintDark", bevel=0.004)
    d.cyl(V(bx_ - 0.07, by_ - 0.06, zt - 0.01), V(bx_ - 0.07, by_ - 0.06, zt + 0.05), 0.026, "SDT_Steel", seg=14)
    d.cyl(V(bx_ - 0.07, by_ - 0.06, zt + 0.05), V(bx_ - 0.07, by_ - 0.06, zt + 0.075), 0.018, "SDT_PaintRed", seg=14)
    d.flange(V(bx_, by_ + BIN_R, zh), V(0, 1, 0), 0.085, 0.014, "SDT_Steel", bolts=8, bolt_r=0.070, bolt_size=0.007)
    d.cyl(V(bx_, by_ + BIN_R + 0.014, zh), V(bx_, by_ + BIN_R + 0.050, zh), 0.012, "SDT_Steel", seg=8)
    d.cyl(V(bx_ - 0.04, by_ + BIN_R + 0.050, zh), V(bx_ + 0.04, by_ + BIN_R + 0.050, zh), 0.010, "SDT_PaintRed", seg=8)
    # nádoba: závěsy mřížky vzadu a visací zámek vpředu
    cx, cy = HOPPER_CX, HOPPER_CY
    zr = HOPPER_TOP_Z + 0.045
    for sx in (-1, 1):
        d.cyl(V(cx + sx * 0.45 - 0.05, cy + HOPPER_HY + 0.030, zr), V(cx + sx * 0.45 + 0.05, cy + HOPPER_HY + 0.030, zr), 0.014,
              "SDT_Steel", seg=10)
    d.box(cx - 0.05, cx + 0.05, cy - HOPPER_HY - 0.040, cy - HOPPER_HY + 0.030, zr - 0.02, zr + 0.025, "SDT_Frame", bevel=0.004)
    d.box(cx - 0.03, cx + 0.03, cy - HOPPER_HY - 0.052, cy - HOPPER_HY - 0.040, zr - 0.04, zr + 0.01, "SDT_PaintYellow", bevel=0.004)
    d.torus(V(cx, cy - HOPPER_HY - 0.046, zr + 0.025), V(0, 1, 0), 0.016, 0.005, "SDT_Steel", seg=12, rseg=4)
    d.finish()


def _elbow_run(m, pts, r, mat):
    """Trubka po lomené čáře s koulí v každém lomu (koleno)."""
    for a, b in zip(pts, pts[1:]):
        m.cyl(a, b, r, mat, seg=16, caps=False)
    for p in pts[1:-1]:
        m.sphere(p, r, mat, seg=16, rings=8)


def build_spout():
    """Plnění big bagu: klapkový rozdělovač na trubce od nádobky ke spojce Storz (Mill_SpoutPipe), páka klapky (Mill_ValveLever:
    v modelu vodorovně ven = hadice), potrubí po palubě se třemi objímkami, stoupačka s patkou a vzpěrou, ložisko otočného kloubu,
    opěrka ramene na boku násypky; rameno s kolenem, kuželem a plnicí hlavou s límcem a objímkou (Mill_SpoutArm, přepravní poloha)
    a hrdlo vaku pod hlavou (Mill_BagNeck, ve hře jen za plnění)."""
    s = Mesh("Mill_SpoutPipe")
    c = VALVE_C
    r = SPOUT_PIPE_R
    # rozdělovač: tělo klapky na vodorovné trubce, protilehlá příruba, odbočka dozadu, hřídel klapky dopředu
    s.box(c.x - 0.045, c.x + 0.055, c.y - 0.065, c.y + 0.065, c.z - 0.065, c.z + 0.062, "SDT_PaintGrey", bevel=0.008)
    s.flange(V(c.x + 0.062, c.y, c.z), V(1, 0, 0), 0.080, 0.012, "SDT_Steel", bolts=6, bolt_r=0.064, bolt_size=0.006)
    bx = VALVE_BRANCH_X
    s.cyl(V(bx, c.y + 0.06, c.z), V(bx, c.y + 0.10, c.z), r + 0.006, "SDT_PaintGrey", seg=16)
    s.flange(V(bx, c.y + 0.10, c.z), V(0, 1, 0), 0.075, 0.012, "SDT_Steel", bolts=4, bolt_r=0.060, bolt_size=0.006)
    s.cyl(V(c.x, c.y - 0.065, c.z), V(c.x, VALVE_SHAFT_Y, c.z), 0.016, "SDT_Steel", seg=12)
    s.cyl(V(c.x, c.y - 0.075, c.z), V(c.x, c.y - 0.065, c.z), 0.034, "SDT_Steel", seg=16)
    s.box(c.x - 0.05, c.x + 0.05, VALVE_SHAFT_Y + 0.03, VALVE_SHAFT_Y + 0.045, DECK_Z, c.z + 0.05, "SDT_Frame", bevel=0.003)
    # potrubí po palubě: z odbočky dozadu, uhne dovnitř k podélníku, pod násypkou k zadnímu rohu a ven ke stoupačce
    z = SPOUT_DECK_Z
    pts = [V(bx, c.y + 0.10, c.z), V(bx, 0.30, z), V(SPOUT_DECK_X, 0.50, z), V(SPOUT_DECK_X, SPOUT_Y, z), V(-0.84, SPOUT_Y, z),
           V(SPOUT_X, SPOUT_Y, z + 0.08)]
    _elbow_run(s, pts, r, "SDT_PaintGrey")
    for y in (0.45, 1.20, 1.95):
        s.box(SPOUT_DECK_X - 0.06, SPOUT_DECK_X + 0.06, y - 0.03, y + 0.03, DECK_Z, z - r + 0.004, "SDT_Frame", bevel=0.004)
        s.clamp(V(SPOUT_DECK_X, y, z), V(0, 1, 0), r + 0.002, "SDT_Steel", width=0.03)
    # stoupačka s patkou na rámu a vzpěrou k zadní noze násypky, ložisko otočného kloubu
    sx, sy = SPOUT_X, SPOUT_Y
    s.cyl(V(sx, sy, z + 0.08), V(sx, sy, SPOUT_BEARING_Z), r, "SDT_PaintGrey", seg=16, caps=False)
    s.box(sx - 0.05, -0.90, sy - 0.04, sy + 0.04, DECK_Z - 0.04, z - 0.03, "SDT_Frame", bevel=0.004)
    s.clamp(V(sx, sy, z + 0.16), V(0, 0, 1), r + 0.002, "SDT_Steel", width=0.03)
    s.cyl(V(sx + 0.04, sy - 0.02, 1.24), V(HOPPER_CX - HOPPER_HX + 0.07, HOPPER_CY + HOPPER_HY - 0.07, 1.24), 0.014, "SDT_Frame", seg=10)
    s.clamp(V(sx, sy, 1.24), V(0, 0, 1), r + 0.002, "SDT_Steel", width=0.03)
    s.cyl(V(sx, sy, SPOUT_BEARING_Z - 0.03), V(sx, sy, SPOUT_BEARING_Z + 0.06), 0.085, "SDT_Steel", seg=24)
    s.bolt_circle(V(sx, sy, SPOUT_BEARING_Z + 0.06), V(0, 0, 1), 0.068, 6, 0.007, 0.007, "SDT_Steel")
    # opěrka ramene v přepravní poloze: konzola z boku násypky a vidlička pod ramenem u hlavy
    ry = sy - SPOUT_ARM_L + 0.10
    zr = SPOUT_ARM_Z - r - 0.012
    wall_x = HOPPER_CX - (0.15 + (zr - HOPPER_OUT_Z) / (HOPPER_RIM_Z - HOPPER_OUT_Z) * (HOPPER_HX - 0.15))
    s.cyl(V(wall_x + 0.02, ry, zr), V(sx, ry, zr), 0.02, "SDT_Frame", seg=4, square=True, ref=V(0, 0, 1))
    s.cyl(V(wall_x + 0.02, ry, zr - 0.30), V(-0.80, ry, zr - 0.012), 0.012, "SDT_Frame", seg=8)
    for dx in (-1, 1):
        s.box(sx + dx * (r + 0.004) - 0.006, sx + dx * (r + 0.004) + 0.006, ry - 0.025, ry + 0.025, zr, zr + 0.05, "SDT_Frame")
    s.box(sx - r - 0.01, sx + r + 0.01, ry - 0.03, ry + 0.03, zr - 0.012, zr + 0.004, "SDT_Rubber", bevel=0.003)
    s.finish()

    lv = Mesh("Mill_ValveLever")
    p = V(c.x, VALVE_SHAFT_Y, c.z)
    lv.cyl(p + V(0, 0.02, 0), p - V(0, 0.02, 0), 0.026, "SDT_Steel", seg=16)
    lv.cyl(p, p + V(-VALVE_LEVER_L, 0, 0), 0.013, "SDT_PaintRed", seg=10)
    lv.cyl(p + V(-VALVE_LEVER_L, 0.04, 0), p + V(-VALVE_LEVER_L, -0.06, 0), 0.022, "SDT_Rubber", seg=14)
    lv.finish()

    # rameno vodorovně, na konci spádová trubka dolů k boku vaku a koleno s ústím vodorovně ven (od kloubu), takže hlava se schová za vak
    # a nic z roury nesahá nad jeho půdorys: plný vak jde zvednout za poutka a odvézt od vozíku
    a = Mesh("Mill_SpoutArm")
    hz = SPOUT_ARM_Z
    hy = sy - SPOUT_ARM_L
    a.cyl(V(sx, sy, SPOUT_BEARING_Z + 0.06), V(sx, sy, SPOUT_BEARING_Z + 0.10), 0.080, "SDT_Steel", seg=24)
    a.cyl(V(sx, sy, SPOUT_BEARING_Z + 0.10), V(sx, sy, hz), r, "SDT_PaintGrey", seg=16, caps=False)
    a.sphere(V(sx, sy, hz), r, "SDT_PaintGrey", seg=16, rings=8)
    a.cyl(V(sx, sy, hz), V(sx, hy, hz), r, "SDT_PaintGrey", seg=16, caps=False)
    a.sphere(V(sx, hy, hz), r, "SDT_PaintGrey", seg=16, rings=8)
    a.flange(V(sx, sy - 0.30, hz), V(0, -1, 0), 0.075, 0.012, "SDT_Steel", bolts=4, bolt_r=0.060, bolt_size=0.006)
    zc = SPOUT_HEAD_Z
    my = sy - SPOUT_MOUTH_L
    a.cyl(V(sx, hy, hz), V(sx, hy, zc), r, "SDT_PaintGrey", seg=16, caps=False)
    a.flange(V(sx, hy, (hz + zc) / 2), V(0, 0, 1), 0.075, 0.012, "SDT_Steel", bolts=4, bolt_r=0.060, bolt_size=0.006)
    a.sphere(V(sx, hy, zc), r, "SDT_PaintGrey", seg=16, rings=8)
    a.cyl(V(sx, hy, zc), V(sx, hy - 0.08, zc), r, "SDT_PaintGrey", seg=16, caps=False)
    a.cyl(V(sx, hy - 0.08, zc), V(sx, hy - 0.16, zc), r, "SDT_Steel", r1=0.098, seg=20)
    a.cyl(V(sx, hy - 0.16, zc), V(sx, my, zc), 0.105, "SDT_Steel", seg=24)
    a.torus(V(sx, my + 0.025, zc), V(0, 1, 0), 0.106, 0.010, "SDT_Rubber", seg=24, rseg=6)
    a.cyl(V(sx + 0.10, my + 0.025, zc), V(sx + 0.17, my + 0.045, zc + 0.02), 0.007, "SDT_PaintRed", seg=8)
    a.finish()

    # hrdlo (plnicí rukáv) vaku: z ústí hlavy vodorovně do horní části boku vaku, vidět jen za sypání
    n = Mesh("Mill_BagNeck")
    n.cyl(V(sx, my + 0.012, zc), V(sx, my - 0.16, zc - 0.01), 0.09, "SDT_PaintWhite", r1=0.095, seg=20)
    n.finish()


def build_decals():
    """Pruhy a štítky (bez textu, atlas se doplní po schválení tvaru)."""
    d = Mesh("Mill_Decals")
    d.box(-DECK_HX + 0.02, DECK_HX - 0.02, Y_FRONT - 0.020, Y_FRONT - 0.016, DECK_Z + 0.015, DECK_Z + 0.045, "SDT_NutIndicator")
    for sx in (-1, 1):
        d.box(sx * (DECK_HX + 0.020), sx * (DECK_HX + 0.024), Y_FRONT + 0.15, Y_REAR - 0.15, DECK_Z + 0.012, DECK_Z + 0.050,
              "SDT_NutIndicator")
    d.finish()


# ------------------------------------------------------------------------------------------------ díly knihovny
# Každý díl se staví ve svém lokálním počátku (střed půdorysu dílu na rovině, kam se montuje: paluba DECK_Z, země) a do vozíku se
# umístí posunem ANCHORS; polohy uzlů a bodů z výsledku jsou po umístění ve vozíku.
ANCHORS = {
    "chassis": (0.0, 0.0, 0.0),
    "drawbar": (0.0, Y_FRONT, 0.0),
    "hopper": (HOPPER_CX, HOPPER_CY, DECK_Z),
    "auger": (HOPPER_CX, HOPPER_CY - 0.10, DECK_Z),
    "mill": (MILL_X, ROW_Y, DECK_Z),
    "engine": ((ENG_X0 + ENG_X1) / 2, ROW_Y, DECK_Z),
    "fuel_tank": ((ENG_X0 + ENG_X1) / 2, ROW_Y, DECK_Z),
    "bin": (BIN_XY[0], BIN_XY[1], DECK_Z),
    "control_box": (HOPPER_CX + HOPPER_HX - 0.07, HOPPER_CY - HOPPER_HY + 0.07, DECK_Z),
    "deck_details": (0.0, 0.0, DECK_Z),
    "port_cap": (PORT_X, BIN_XY[1], PORT_Z),
    "extra_details": (0.0, 0.0, 0.0),
    "spout": (0.0, 0.0, 0.0),
}


def part_chassis():
    """Rám s nápravou, listovými pružinami, blatníky, zadním čelem se zebrou, světly a pruhy (Mill_Chassis, Mill_Decals)."""
    build_chassis()
    build_decals()
    PL.localize(ANCHORS["chassis"])


def part_drawbar():
    """Svařená oj s najížděcím zařízením, kulovou spojkou, podpěrným kolečkem, ruční brzdou a kabelem zástrčky (Mill_Drawbar, Mill_Jockey)."""
    build_drawbar()
    PL.localize(ANCHORS["drawbar"])


def part_hopper():
    """Nádoba na hrubé vápno s mřížkou, žebry a žebříkem a její drobnosti (Mill_Hopper, Mill_HopperDetail)."""
    build_hopper()
    build_hopper_detail()
    PL.localize(ANCHORS["hopper"])


def part_auger():
    """Šnek z dna nádoby do mlýna s převodovkou a výsypkami (Mill_Auger)."""
    build_auger()
    PL.localize(ANCHORS["auger"])


def part_mill():
    """Kladivový mlýn s revizními dvířky, sedly a výstupem jemného vápna (Mill_Body, Mill_Detail)."""
    build_mill()
    build_mill_detail()
    PL.localize(ANCHORS["mill"])


def part_engine():
    """Jednoválcový diesel s krytem chlazení, filtry, výfukem a startérem (Mill_Engine, Mill_EngineDetail)."""
    build_engine()
    build_engine_detail()
    PL.localize(ANCHORS["engine"])


def part_fuel_tank():
    """Palivová nádrž před motorem; vrací polohu hrdla (Mill_FuelTank)."""
    neck = build_fuel_tank()
    PL.localize(ANCHORS["fuel_tank"])
    return neck - V(*ANCHORS["fuel_tank"])


def part_bin():
    """Cyklónová nádobka na jemné vápno se stojanem a hadicovou spojkou Storz (Mill_Bin, Mill_Bin_Stand, millOutletPort)."""
    build_bin()
    PL.localize(ANCHORS["bin"])


def part_control_box():
    """Rozvaděč s jedním tlačítkem a světelným prstencem kolem něj (Mill_Control, millStartRing); vrací střed tlačítka."""
    b = build_control_box()
    PL.localize(ANCHORS["control_box"])
    return b - V(*ANCHORS["control_box"])


def part_deck_details():
    """Akumulátor za motorem, klíny pod kola a obrysová světla (Mill_DeckDetails)."""
    build_deck_details()
    PL.localize(ANCHORS["deck_details"])


def part_port_cap():
    """Slepá spojka Storz s řetízkem (Mill_PortCap)."""
    build_port_cap()
    PL.localize(ANCHORS["port_cap"])


def part_extra_details():
    """Ruční brzda, bezpečnostní řetěz, oka, poklopy, čidla a zámek (Mill_ExtraDetails)."""
    build_extra_details()
    PL.localize(ANCHORS["extra_details"])


def part_spout():
    """Rozdělovač s pákou, potrubí, stoupačka a otočná výsypná roura s plnicí hlavou (Mill_SpoutPipe, Mill_ValveLever, Mill_SpoutArm,
    Mill_BagNeck)."""
    build_spout()
    PL.localize(ANCHORS["spout"])


def part_hose_end(collar="SDT_PaintRed"):
    """Koncovka hadice: rychlospojka Storz s příložkou (osa hadice podél -Y); stejná je u všech tažných hadic."""
    m = Mesh("Mill_Storz")
    _hose_end(m, V(0, 0, 0), V(0, -1, 0), collar)
    return m.finish()


def _at(key):
    return PL.Place.at(*ANCHORS[key])


def build_all():
    """Sestaví vozík z dílů knihovny a z disků a pneu (sdt_rims)."""
    PL.call(part_chassis, at=_at("chassis"))
    build_wheels()
    PL.call(part_drawbar, at=_at("drawbar"))
    PL.call(part_hopper, at=_at("hopper"))
    PL.call(part_auger, at=_at("auger"))
    PL.call(part_mill, at=_at("mill"))
    PL.call(part_engine, at=_at("engine"))
    neck = PL.call(part_fuel_tank, at=_at("fuel_tank"))
    PL.call(part_bin, at=_at("bin"))
    btn = PL.call(part_control_box, at=_at("control_box"))
    PL.call(part_deck_details, at=_at("deck_details"))
    PL.call(part_port_cap, at=_at("port_cap"))
    PL.call(part_extra_details, at=_at("extra_details"))
    PL.call(part_spout, at=_at("spout"))
    p = P.empty("millDieselNeck", neck)
    p.empty_display_size = 0.08
    P.empty("millDustIn", V(MILL_X, ROW_Y, AUGER_P1.z - 0.16)).empty_display_size = 0.08
    P.empty("millStartButton", btn).empty_display_size = 0.05
    return ports()
