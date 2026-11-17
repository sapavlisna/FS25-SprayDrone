"""Přenosná motorová pumpa na vodu jako herní objekt (pallet) objects/pump/waterPump.i3d: ohýbaný trubkový rám s madly a gumovými patkami,
vzduchem chlazený jednoválcový motor (vzduchový filtr, tlumič výfuku, ručně tažený startér), nad ním hranatá zaoblená palivová nádrž
s velkým víčkem a stavoznakem, vpředu spirální skříň odstředivého čerpadla (výpust, plnicí zátka, tlakoměr) a dvě spojky Storz s barevnou
objímkou a malým nápisem IN / OUT se šipkou toku, ke každé vlastní tažná hadice (skryté články jako u Maxu): VSTUP na boku +X (modrá objímka, hadice
ke zdroji; konec hadice je spojka Storz (IBC / cisterna) nebo sací koš (rybník) podle režimu, který hráč přepíná ručně) a VÝSTUP na boku -X
(červená, hadice k vleku).
Samostatný skript nad prázdnou scénou (jako build_link_items.py):

    blender.exe -b --python blender\\build_pump.py

Osa jako u vleků: vpředu -Y, +X vlevo, Z nahoru, počátek na zemi uprostřed rámu. Kolize má jen těleso. Pravidla objektu (XML) jsou ručně, skript do něj jen přepíše blok <i3dMappings>. Chování řeší scripts/SprayDronePump.lua.
"""

import math
import os
import sys

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parts_lib as PL  # noqa: E402
import build_canister as C  # noqa: E402
import build_link_items as L  # noqa: E402
import export_middle_mod as X  # noqa: E402
import sdt_mlyn as MILL  # noqa: E402
import sdt_parts as P  # noqa: E402
from sdt_tanks import Mesh, V, frame, rounded_path  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects", "pump")
WORK = os.path.join(PROJECT, "out", "pump")
BLEND = os.path.join(HERE, "spraydrone_pump.blend")
NAME = "waterPump"

TAU = 2.0 * math.pi
FX = 0.34                        # osa podélníků rámu po X
Y_FRONT, Y_REAR = -0.46, 0.50    # příčné trubky rámu
Z_BASE, Z_TOP = 0.055, 0.72      # spodní a horní trubky rámu
AX_Z = 0.28                      # osa klikového hřídele a čerpadla
PUMP_Y = -0.12                   # střed spirální skříně čerpadla po Y
TANK_Z, TANK_R = 0.55, 0.085     # střed a poloviční výška nádrže
NECK_Y = 0.20                    # hrdlo nádrže po Y
NECK_TOP = TANK_Z + TANK_R + 0.075
OUTLET = V(-0.48, PUMP_Y, 0.40)  # čelo výtlačné spojky Storz (směr ven -X)
INLET = V(0.48, -0.34, AX_Z)     # čelo sací spojky Storz na boku +X (směr ven +X): sem se napojí hadice pumpy ke zdroji
HOSE_MATERIALS = {"in": "SDT_HoseSpiralBlue", "out": "SDT_HoseSpiralRed"}   # vstup modrý, výstup červený, jako spojky na hlavě pumpy
HOSE_COLLARS = {"in": "SDT_ValveBlue", "out": "SDT_PaintRed"}
HOSES = (("in", 60), ("out", 72))   # tažné hadice pumpy: předpona uzlů a počet článků (SprayDroneWaterHose / SprayDroneHoseLib)
HOSE_TILES = 5.5                 # závitů spirály na 1 m článku (článek se ve hře zkrátí na ~0,17 m: stoupání ~3 cm)
FONT = "C:/Windows/Fonts/arialbd.ttf"
GROUP_FILL_ROOT, MASK_FILL_ROOT = L.GROUP_FILL_ROOT, L.MASK_FILL_ROOT
ENG_ANGLE = math.radians(25)     # sklon válce motoru k +X


def tube_path(m, pts, r, mat, joint=True):
    for a, b in zip(pts, pts[1:]):
        m.cyl(a, b, r, mat, seg=12, caps=False)
    if joint:
        for p in pts[1:-1]:
            m.sphere(p, r, mat, seg=12, rings=6)


def build_frame(m):
    """Rám z ohýbaných trubek: na každém boku jedna smyčka (spodní podélník, svislé sloupky, horní podélník) se zaoblenými rohy,
    příčné trubky, gumová madla, nosná deska motoru a čtyři gumové patky."""
    r = 0.015
    for sx in (-1, 1):
        x = sx * FX
        loop = rounded_path([V(x, 0.0, Z_BASE), V(x, Y_FRONT, Z_BASE), V(x, Y_FRONT, Z_TOP), V(x, Y_REAR, Z_TOP), V(x, Y_REAR, Z_BASE),
                             V(x, 0.0, Z_BASE)], [0.07, 0.09, 0.09, 0.07], arc_deg_step=15, straight_step=1.0)
        m.pipe(loop, r, "SDT_Frame", seg=10)
        m.cyl(V(x, -0.012, Z_BASE), V(x, 0.012, Z_BASE), r + 0.004, "SDT_Steel", seg=10, caps=False)
        for y in (Y_FRONT + 0.12, Y_REAR - 0.12):
            m.cyl(V(x, y, 0.036), V(x, y, Z_BASE), 0.012, "SDT_Frame", seg=8)
            m.box(x - 0.05, x + 0.05, y - 0.06, y + 0.06, 0.0, 0.040, "SDT_Rubber", bevel=0.008)
        m.cyl(V(x, -0.30, Z_TOP), V(x, 0.30, Z_TOP), 0.021, "SDT_Rubber", seg=12)
    for y, z in ((Y_FRONT, Z_BASE), (0.02, Z_BASE), (Y_REAR, Z_BASE), (Y_FRONT, Z_TOP), (Y_REAR, Z_TOP)):
        m.pipe([V(-FX, y, z), V(FX, y, z)], r, "SDT_Frame", seg=10)
    m.cyl(V(-0.14, Y_REAR, Z_TOP), V(0.14, Y_REAR, Z_TOP), 0.021, "SDT_Rubber", seg=12)
    # svislá výztuha uprostřed zadního oblouku k desce motoru
    for sx in (-1, 1):
        m.pipe([V(sx * FX, Y_REAR - 0.02, Z_BASE + 0.01), V(sx * 0.27, Y_REAR - 0.07, Z_BASE + 0.01)], 0.012, "SDT_Frame", seg=8)
    m.box(-0.27, 0.27, -0.32, 0.46, Z_BASE + 0.012, Z_BASE + 0.032, "SDT_Frame", bevel=0.004)


def build_engine(m):
    """Jednoválcový motor s vodorovným klikovým hřídelem podél Y: klikovka, žebrovaný válec skloněný k +X s hlavou a krytem ventilů, vzduchový
    filtr vlevo, tlumič výfuku s krytem vpravo, plechový kryt chlazení a ručně tažený startér s lankem a držadlem vzadu."""
    cy = 0.17
    for y in (0.08, 0.28):
        m.box(-0.095, 0.095, y - 0.03, y + 0.03, Z_BASE + 0.052, AX_Z - 0.10, "SDT_Frame", bevel=0.004)
        for sx in (-1, 1):
            m.cyl(V(sx * 0.07, y, Z_BASE + 0.032), V(sx * 0.07, y, Z_BASE + 0.052), 0.022, "SDT_Rubber", seg=12)
    # klikovka a přírubový zvon k čerpadlu
    m.obox((0.25, 0.28, 0.27), Matrix.Translation((0, cy, AX_Z)), "SDT_CastIron", bevel=0.045, segments=2)
    m.cyl(V(0, -0.045, AX_Z), V(0, 0.035, AX_Z), 0.115, "SDT_AluCast", seg=32)
    m.bolt_circle(V(0, -0.045, AX_Z), V(0, 1, 0), 0.128, 6, 0.008, 0.007, "SDT_Steel")
    # válec skloněný k +X: žebra, hlava, kryt ventilů, svíčka
    d = V(math.cos(ENG_ANGLE), 0, math.sin(ENG_ANGLE))
    p0 = V(0.115, cy, AX_Z + 0.015)
    m.cyl(p0, p0 + d * 0.15, 0.062, "SDT_CastIron", seg=24)
    for k in range(6):
        s = 0.025 + 0.022 * k
        m.cyl(p0 + d * s, p0 + d * (s + 0.008), 0.098, "SDT_CastIron", seg=24)
    hc = p0 + d * 0.20
    m.obox((0.15, 0.14, 0.095), frame(hc, d, V(0, 1, 0)), "SDT_CastIron", bevel=0.012, segments=2)
    m.obox((0.12, 0.10, 0.026), frame(p0 + d * 0.262, d, V(0, 1, 0)), "SDT_AluCast", bevel=0.007, segments=2)
    for sy in (-1, 1):
        for sz in (-1, 1):
            m.hex(p0 + d * 0.276 + V(0, sy * 0.036, 0) + V(-d.z, 0, d.x) * (sz * 0.030), d, 0.007, 0.010, "SDT_Steel")
    side = V(-d.z, 0, d.x)
    m.cyl(hc + side * 0.050 - d * 0.02, hc + side * 0.088, 0.010, "SDT_Steel", seg=8)
    m.cyl(hc + side * 0.088, hc + side * 0.122, 0.015, "SDT_Plastic", seg=10)
    # karburátor a palivová hadička z nádrže
    m.obox((0.055, 0.060, 0.075), Matrix.Translation((0.105, 0.045, AX_Z + 0.055)), "SDT_AluCast", bevel=0.012, segments=2)
    m.cyl(V(0.105, 0.045, AX_Z + 0.09), V(0.105, 0.045, AX_Z + 0.115), 0.011, "SDT_Brass", seg=8)
    m.pipe([V(0.06, 0.045, TANK_Z - TANK_R - 0.004), V(0.075, 0.04, AX_Z + 0.20), V(0.100, 0.045, AX_Z + 0.115)], 0.0055, "SDT_HoseBlack", seg=6)
    # vzduchový filtr vlevo: černá skříň se kulatým víkem a křídlovou maticí, dvě spony
    m.obox((0.08, 0.15, 0.17), Matrix.Translation((-0.165, 0.19, AX_Z + 0.07)), "SDT_Plastic", bevel=0.03, segments=2)
    m.cyl(V(-0.205, 0.19, AX_Z + 0.07), V(-0.217, 0.19, AX_Z + 0.07), 0.058, "SDT_PaintDark", seg=24)
    m.cyl(V(-0.217, 0.19, AX_Z + 0.07), V(-0.236, 0.19, AX_Z + 0.07), 0.009, "SDT_Steel", seg=8)
    m.box(-0.246, -0.236, 0.19 - 0.030, 0.19 + 0.030, AX_Z + 0.07 - 0.007, AX_Z + 0.07 + 0.007, "SDT_Steel", bevel=0.002)
    for dy in (-0.045, 0.045):
        m.box(-0.208, -0.196, 0.19 + dy - 0.008, 0.19 + dy + 0.008, AX_Z + 0.135, AX_Z + 0.158, "SDT_Steel", bevel=0.002)
    m.pipe([V(-0.125, 0.12, AX_Z + 0.10), V(-0.05, 0.08, AX_Z + 0.115), V(0.06, 0.05, AX_Z + 0.10)], 0.017, "SDT_HoseBlack", seg=8)
    # tlumič výfuku s krytem a trubka z hlavy
    m.obox((0.09, 0.17, 0.10), Matrix.Translation((0.26, 0.07, 0.185)), "SDT_AluCast", bevel=0.02, segments=2)
    m.obox((0.006, 0.15, 0.085), Matrix.Translation((0.309, 0.07, 0.185)), "SDT_PaintDark", bevel=0.002)
    for dy in (-0.05, 0.05):
        for dz in (-0.03, 0.03):
            m.hex(V(0.312, 0.07 + dy, 0.185 + dz), V(1, 0, 0), 0.006, 0.006, "SDT_Steel")
    m.pipe([V(0.255, 0.115, 0.345), V(0.285, 0.115, 0.30), V(0.275, 0.10, 0.235)], 0.015, "SDT_Steel", seg=10)
    # plechový kryt chlazení a startér vzadu
    m.obox((0.30, 0.13, 0.32), Matrix.Translation((0, 0.375, AX_Z + 0.03)), "SDT_EngineRed", bevel=0.06, segments=2)
    for sx in (-1, 1):
        for k in range(3):
            m.box(sx * 0.1495 - 0.002, sx * 0.1495 + 0.002, 0.34, 0.41, AX_Z + 0.07 + 0.03 * k, AX_Z + 0.082 + 0.03 * k, "SDT_PaintDark")
    sc = V(0, 0.44, AX_Z)
    m.cyl(sc, sc + V(0, 0.058, 0), 0.075, "SDT_PaintRed", seg=28)
    m.torus(sc + V(0, 0.058, 0), V(0, 1, 0), 0.071, 0.007, "SDT_Steel", seg=28, rseg=4)
    m.cyl(sc + V(0, 0.058, 0), sc + V(0, 0.070, 0), 0.032, "SDT_PaintDark", seg=16)
    for k in range(3):
        a = TAU * k / 3 + math.radians(30)
        ear = sc + V(0.085 * math.cos(a), 0.012, 0.085 * math.sin(a))
        m.obox((0.034, 0.016, 0.026), frame(ear, V(math.cos(a), 0, math.sin(a)), V(0, 1, 0)), "SDT_PaintRed", bevel=0.004)
    m.cyl(V(0.062, 0.462, AX_Z - 0.062), V(0.062, 0.496, AX_Z - 0.062), 0.0125, "SDT_Steel", seg=10)
    m.pipe([V(0.062, 0.496, AX_Z - 0.062), V(0.07, 0.512, AX_Z - 0.09), V(0.07, 0.514, AX_Z - 0.14)], 0.0045, "SDT_Rubber", seg=6)
    m.cyl(V(0.036, 0.514, AX_Z - 0.15), V(0.104, 0.514, AX_Z - 0.15), 0.0125, "SDT_PaintRed", seg=10)
    # čep na doplnění oleje a páčka sytiče
    m.cyl(V(-0.06, 0.06, AX_Z + 0.135), V(-0.06, 0.06, AX_Z + 0.16), 0.016, "SDT_PaintYellow", seg=12)
    m.cyl(V(0.0, 0.31, AX_Z + 0.135), V(0.0, 0.31, AX_Z + 0.165), 0.006, "SDT_Steel", seg=6)
    m.sphere(V(0.0, 0.31, AX_Z + 0.172), 0.011, "SDT_PaintRed", seg=8, rings=4)


def build_tank(m):
    """Hranatá zaoblená palivová nádrž na pryžových podložkách nad motorem: rýha kolem víčka, velké víčko s žebry a řetízkem,
    odvzdušnění, stavoznak na čele a palivová hadička ke karburátoru."""
    cy = 0.20
    top = TANK_Z + TANK_R
    m.obox((0.26, 0.34, 2 * TANK_R), Matrix.Translation((0, cy, TANK_Z)), "SDT_PaintYellow", bevel=0.05, segments=3)
    for y in (0.08, 0.32):
        m.box(-0.07, 0.07, y - 0.025, y + 0.025, AX_Z + 0.135, TANK_Z - TANK_R + 0.012, "SDT_Frame", bevel=0.004)
        m.box(-0.08, 0.08, y - 0.03, y + 0.03, TANK_Z - TANK_R - 0.012, TANK_Z - TANK_R + 0.004, "SDT_Rubber", bevel=0.003)
    m.torus(V(0, NECK_Y, top - 0.004), V(0, 0, 1), 0.066, 0.0055, "SDT_PaintDark", seg=28, rseg=4)
    # hrdlo s velkým víčkem, žebrování a řetízek
    m.cyl(V(0, NECK_Y, top - 0.012), V(0, NECK_Y, top + 0.026), 0.046, "SDT_Steel", seg=24)
    m.cyl(V(0, NECK_Y, top + 0.026), V(0, NECK_Y, top + 0.033), 0.060, "SDT_Steel", seg=24)
    m.cyl(V(0, NECK_Y, top + 0.033), V(0, NECK_Y, top + 0.066), 0.057, "SDT_PaintRed", seg=24)
    m.cyl(V(0, NECK_Y, top + 0.066), V(0, NECK_Y, NECK_TOP), 0.050, "SDT_PaintRed", r1=0.054, seg=24)
    for k in range(10):
        a = TAU * k / 10
        m.box(0.0585 * math.cos(a) - 0.004, 0.0585 * math.cos(a) + 0.004, NECK_Y + 0.0585 * math.sin(a) - 0.004,
              NECK_Y + 0.0585 * math.sin(a) + 0.004, top + 0.040, top + 0.060, "SDT_PaintRed")
    for k in range(5):
        m.torus(V(0.062 + 0.002 * k, NECK_Y + 0.012 * k, top + 0.040 - 0.007 * k), V(0, 1, 0) if k % 2 == 0 else V(1, 0, 0),
                0.009, 0.0022, "SDT_Steel", seg=8, rseg=4)
    # odvzdušnění
    m.cyl(V(0.07, 0.33, top - 0.006), V(0.07, 0.33, top + 0.025), 0.010, "SDT_Steel", seg=10)
    m.sphere(V(0.07, 0.33, top + 0.030), 0.014, "SDT_Plastic", seg=10, rings=5)
    # stavoznak na čele nádrže: rámeček, okénko a plovák
    fy = cy - 0.17
    m.obox((0.05, 0.012, 0.115), Matrix.Translation((-0.065, fy - 0.003, TANK_Z + 0.005)), "SDT_PaintDark", bevel=0.004)
    m.box(-0.080, -0.050, fy - 0.0105, fy - 0.0085, TANK_Z - 0.040, TANK_Z + 0.050, "SDT_Screen")
    m.box(-0.076, -0.054, fy - 0.0115, fy - 0.0095, TANK_Z - 0.012, TANK_Z + 0.002, "SDT_PaintRed")
    # palivový kohout pod nádrží
    m.cyl(V(0.06, 0.04, TANK_Z - TANK_R - 0.004), V(0.06, 0.04, TANK_Z - TANK_R - 0.026), 0.012, "SDT_Brass", seg=8)
    m.cyl(V(0.06, 0.04, TANK_Z - TANK_R - 0.020), V(0.095, 0.04, TANK_Z - TANK_R - 0.020), 0.005, "SDT_PaintRed", seg=6)


def volute_matrix(y):
    return Matrix.Translation((0, y, AX_Z)) @ Matrix.Rotation(math.radians(90), 4, "Z")


def build_pump(m):
    """Spirální skříň odstředivého čerpadla s výtlačným hrdlem, plnicí zátkou a vypouštěcím šroubem, sací krček s odbočkou na bok a dvě spojky
    Storz s barevnou objímkou (nápisy IN / OUT u spojek). Čelní víko s šrouby, tlakoměr na výtlaku."""
    y = PUMP_Y
    c = V(0, y, AX_Z)
    # spirální skříň (osa Y): průřez se otáčí od horního levého místa o 360° a roste do výtlačného hrdla
    m.scroll(V(0, 0, 0), -0.07, 0.055, 0.07, 0.122, 0.170, 0.014, math.radians(53), "SDT_AluCast", steps=56, m=volute_matrix(y))
    # zadní příruba k zvonu motoru a čelní víko se šrouby a nálitkem sání
    m.cyl(V(0, y + 0.055, AX_Z), V(0, y + 0.075, AX_Z), 0.150, "SDT_AluCast", seg=40)
    m.cyl(V(0, y - 0.095, AX_Z), V(0, y - 0.060, AX_Z), 0.150, "SDT_AluCast", seg=40)
    m.bolt_circle(V(0, y - 0.095, AX_Z), V(0, -1, 0), 0.128, 8, 0.009, 0.008, "SDT_Steel")
    m.cyl(V(0, y - 0.095, AX_Z), V(0, y - 0.125, AX_Z), 0.085, "SDT_AluCast", r1=0.072, seg=32)
    # sací krček dopředu k odbočce na bok
    m.cyl(V(0, y - 0.125, AX_Z), V(0, INLET.y, AX_Z), 0.062, "SDT_AluCast", seg=28)
    # odbočka na bok +X (VSTUP) z krčku, příruba a spojka INLET
    m.cyl(V(-0.056, INLET.y, AX_Z), V(0.435, INLET.y, AX_Z), 0.056, "SDT_AluCast", seg=28)
    m.cyl(V(0.29, INLET.y, AX_Z), V(0.304, INLET.y, AX_Z), 0.082, "SDT_AluCast", seg=28)
    m.bolt_circle(V(0.304, INLET.y, AX_Z), V(1, 0, 0), 0.068, 6, 0.007, 0.006, "SDT_Steel")
    m.sphere(V(0, INLET.y, AX_Z), 0.070, "SDT_AluCast", seg=24, rings=10)
    m.storz(INLET, V(-1, 0, 0), collar="SDT_ValveBlue")
    # výtlak: hrdlo ze skříně k boku -X, příruba a spojka OUTLET
    m.cyl(V(-0.07, y, 0.40), V(-0.435, y, 0.40), 0.046, "SDT_AluCast", seg=24)
    m.cyl(V(-0.31, y, 0.40), V(-0.324, y, 0.40), 0.072, "SDT_AluCast", seg=28)
    m.bolt_circle(V(-0.324, y, 0.40), V(-1, 0, 0), 0.058, 4, 0.007, 0.006, "SDT_Steel")
    m.storz(OUTLET, V(1, 0, 0), collar="SDT_PaintRed")
    # zátka zálivky nahoře, vypouštěcí šroub dole
    top = AX_Z + 0.125
    m.cyl(V(0, y, top - 0.010), V(0, y, top + 0.028), 0.034, "SDT_AluCast", seg=20)
    m.cyl(V(0, y, top + 0.028), V(0, y, top + 0.052), 0.040, "SDT_PaintRed", seg=20)
    for k in range(6):
        a = TAU * k / 6
        m.box(0.041 * math.cos(a) - 0.0035, 0.041 * math.cos(a) + 0.0035, y + 0.041 * math.sin(a) - 0.0035, y + 0.041 * math.sin(a) + 0.0035,
              top + 0.032, top + 0.048, "SDT_PaintRed")
    m.hex(V(0, y, AX_Z - 0.152), V(0, 0, -1), 0.016, 0.016, "SDT_Steel")
    m.cyl(V(0, y, AX_Z - 0.140), V(0, y, AX_Z - 0.152), 0.022, "SDT_AluCast", seg=12)
    # tlakoměr na výtlačném hrdle (čelem dopředu)
    gx = -0.17
    m.cyl(V(gx, y, 0.442), V(gx, y, 0.482), 0.008, "SDT_Brass", seg=8)
    m.cyl(V(gx, y + 0.014, 0.512), V(gx, y - 0.010, 0.512), 0.034, "SDT_Frame", seg=20)
    m.cyl(V(gx, y - 0.010, 0.512), V(gx, y - 0.015, 0.512), 0.029, "SDT_PaintWhite", seg=20)
    m.box(gx - 0.002, gx + 0.002, y - 0.0165, y - 0.0145, 0.512, 0.536, "SDT_PaintRed")
    # štítek výrobce na čelním víku (červený pruh)
    m.box(-0.10, 0.10, y - 0.1255, y - 0.1195, AX_Z - 0.115, AX_Z - 0.100, "SDT_PaintRed")
    build_labels(m)


def add_text(m, text, size, frame_m, mat="SDT_PaintDark", depth=0.003):
    """Text písmem FONT převedený na mesh (střed textu v počátku matice frame_m, čte se po její ose X, nahoru je Y, lícem k ose Z)."""
    curve = bpy.data.curves.new("lbl", "FONT")
    curve.body = text
    curve.font = bpy.data.fonts.load(FONT, check_existing=True)
    curve.size = size
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.extrude = depth / 2
    curve.resolution_u = 3
    obj = bpy.data.objects.new("lbl", curve)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    t = bmesh.new()
    t.from_mesh(me)
    ev.to_mesh_clear()
    bpy.data.objects.remove(obj)
    bpy.data.curves.remove(curve)
    m._absorb(t, frame_m, mat)


def plate_frame(center, right, normal):
    x = Vector(right).normalized()
    z = Vector(normal).normalized()
    y = z.cross(x)
    f = Matrix((x, y, z)).transposed().to_4x4()
    f.translation = Vector(center)
    return f


def flow_mark(m, text, x_tip, y, z_top, mat, size=0.030):
    """Ražený nápis a šipka směru toku (k -X) na hřbetu vodorovné trubky: špička šipky v x_tip, za ní text, čte se po ose +X."""
    z = z_top + 0.001
    t = 0.003
    o = V(x_tip, y, z - 0.002)
    m.plate([(0.0, 0.0), (0.016, -0.013), (0.016, 0.013)], o, V(1, 0, 0), V(0, 1, 0), t, mat)
    m.plate([(0.012, -0.005), (0.036, -0.005), (0.036, 0.005), (0.012, 0.005)], o, V(1, 0, 0), V(0, 1, 0), t, mat)
    add_text(m, text, size, plate_frame(V(x_tip + 0.044 + 0.010 * len(text), y, z), V(1, 0, 0), V(0, 0, 1)), mat, depth=t)


def build_labels(m):
    """VSTUP (modře) a VÝSTUP (červeně) jen jako malé ražené IN / OUT se šipkou toku na hřbetu trubky u spojky, bez cedulek."""
    flow_mark(m, "IN", 0.095, INLET.y, AX_Z + 0.056, "SDT_ValveBlue")
    flow_mark(m, "OUT", -0.290, PUMP_Y, 0.40 + 0.046, "SDT_PaintRed")


def strainer_end(m):
    """Koncovka sací hadice v režimu rybník: rychlospojka jako u ostatních a za jejím čelem (+Y Blenderu) mosazný nátrubek se sacím košem."""
    MILL._hose_end(m, V(0, 0, 0), V(0, -1, 0))
    m.cyl(V(0, 0, 0), V(0, 0.045, 0), 0.040, "SDT_Brass", seg=20)
    m.torus(V(0, 0.022, 0), V(0, 1, 0), 0.043, 0.004, "SDT_Steel", seg=20, rseg=4)
    c0 = V(0, 0.045, 0)
    m.cyl(c0, c0 + V(0, 0.015, 0), 0.062, "SDT_Steel", seg=24)
    cage_len = 0.20
    cage_end = c0 + V(0, 0.015 + cage_len, 0)
    base = c0 + V(0, 0.015, 0)
    for k in range(10):
        a = TAU * k / 10
        mid = (base + cage_end) / 2 + V(0.056 * math.cos(a), 0, 0.056 * math.sin(a))
        m.obox((0.006, cage_len, 0.006), Matrix.Translation(mid), "SDT_Steel")
    for t in (0.0, 0.5, 1.0):
        m.torus(base + V(0, cage_len * t, 0), V(0, 1, 0), 0.057, 0.0045, "SDT_Steel", seg=20, rseg=4)
    m.cyl(cage_end, cage_end + V(0, 0.012, 0), 0.060, "SDT_Steel", seg=20)
    m.cyl(cage_end + V(0, 0.012, 0), cage_end + V(0, 0.032, 0), 0.030, "SDT_PaintRed", r1=0.020, seg=14)


def build_hose_nodes():
    """Skryté články dvou tažných hadic (inHoseSeg*, outHoseSeg*: válec délky 1 m podél -Y Blenderu, skript ho natáčí a natahuje)
    a jejich koncovky (inHoseEnd = spojka Storz a inStrainerEnd = sací koš na vstupní hadici, skript ukazuje podle režimu; outHoseEnd):
    hadice se vykreslují jen když jsou vytažené (SprayDroneWaterHose);
    geometrie stejná jako u Maxu, materiál SDT_HoseSpiral (spirálová výztuha z normálové textury, lesk gumy)."""
    for prefix, count in HOSES:
        mat = HOSE_MATERIALS[prefix]
        for i in range(1, count + 1):
            seg = Mesh(f"{prefix}HoseSeg{i}")
            seg.cyl(V(0, 0, 0), V(0, -1.0, 0), 0.05, mat, seg=10)
            seg.spiral = (mat, HOSE_TILES, V(0, 0, 0), V(0, -1, 0))
            seg.finish()
        PL.call(MILL.part_hose_end, collar=HOSE_COLLARS[prefix], rename=lambda n, prefix=prefix: f"{prefix}HoseEnd")
        if prefix == "in":
            PL.call(part_strainer, rename=lambda n: "inStrainerEnd")


def _part(name, builder):
    m = Mesh(name)
    builder(m)
    return m.finish()


def part_frame():
    """Rám z ohýbaných trubek s madly a čtyřmi gumovými patkami (Pump_Frame)."""
    return _part("Pump_Frame", build_frame)


def part_engine():
    """Spalovací motor se vzduchovým filtrem, tlumičem výfuku a startérem (Pump_Engine); stejný je u pumpy i násypky."""
    return _part("Pump_Engine", build_engine)


def part_tank():
    """Hranatá zaoblená palivová nádrž nad motorem s velkým víčkem a stavoznakem (Pump_Tank); stejná je u pumpy i násypky."""
    return _part("Pump_Tank", build_tank)


def part_head():
    """Spirální skříň odstředivého čerpadla se dvěma spojkami Storz a nápisy IN / OUT (Pump_Head)."""
    return _part("Pump_Head", build_pump)


def part_strainer():
    """Koncovka sací hadice v režimu rybník: rychlospojka a mosazný nátrubek se sacím košem (Pump_Strainer)."""
    return _part("Pump_Strainer", strainer_end)


def build_body(name):
    parts = [PL.call(part_frame), PL.call(part_engine), PL.call(part_tank), PL.call(part_head)]
    obj = PL.join_meshes(name, parts)
    C.props(obj, clipDistance=100.0)
    return obj


def build():
    root, cols = L._reset(NAME)
    C.box_object("floorCollision01", cols, -0.36, 0.36, -0.47, 0.52, 0.0, 0.74, C.GROUP_FLOOR, C.MASK_FLOOR,
                 compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    # nalévání nafty: kvádr kolem nádrže (jako exactFillRootNode mlýnku)
    C.box_object("exactFillRootNode", root, -0.11, 0.11, 0.0, 0.40, TANK_Z - TANK_R - 0.02, NECK_TOP + 0.08, GROUP_FILL_ROOT,
                 MASK_FILL_ROOT, kinematic=True, compound=True)
    body = build_body(f"{NAME}_vis")
    L._pivot("pumpSoundNode", (0.0, 0.22, 0.45), root)
    L._pivot("pumpDieselNeck", (0.0, NECK_Y, NECK_TOP), root)
    # hadice tažená ze spojky vychází z uzlu směrem jeho lokálního -X (jako u výtlaku na -X): vstup na +X je otočený o 180° kolem Z
    L._pivot("pumpOutletPort", tuple(OUTLET), root)
    inlet = L._pivot("pumpInletPort", tuple(INLET), root)
    inlet.rotation_euler = (0.0, 0.0, math.pi)
    build_hose_nodes()
    bpy.context.view_layer.update()
    return root, body


def export(root):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{NAME}.i3d")
    C.export_i3d(root, path)
    L.shader_materials(path)
    C.zero_density(path)
    names = [root.name, f"{NAME}_vis", "floorCollision01", "exactFillRootNode", "pumpSoundNode", "pumpDieselNeck",
             "pumpInletPort", "pumpOutletPort", "inStrainerEnd"]
    for prefix, count in HOSES:
        names += [f"{prefix}HoseEnd", *[f"{prefix}HoseSeg{i}" for i in range(1, count + 1)]]
    mappings, found = X.i3d_mappings(path, names)
    print(mappings)
    C.write_mappings(os.path.join(OUT_DIR, f"{NAME}.xml"), found, names)
    C.store_image(root, os.path.join(OUT_DIR, f"store_{NAME}.dds"), os.path.join(WORK, f"store_{NAME}.png"))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    root, body = build()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    export(root)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
