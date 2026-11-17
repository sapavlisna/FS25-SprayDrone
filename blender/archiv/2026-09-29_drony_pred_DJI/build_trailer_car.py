"""Servisní vlek pro jeden postřikový dron, menší verze za osobní auto (kulová spojka).

Stejné pojetí jako velká verze (build_trailer3.py): dole paluba s nádržemi a generátorem,
nahoře plošina pro dron. Podvozek porovnaný s vanilla FS25 Stema Trius (evropský valník za auto,
kolekce REF_StemaTrius): kola r 0,30, rozteč náprav 0,70, spojka 0,50-0,55 m nad zemí.

Hmotnost naplněného vleku ~1,3-1,5 t (nádrž 600 l), aby ho utáhlo běžné SUV.

Osa: spojka vpředu na -Y. Počátek = zem, střed šířky, střed paluby.
Staví se ve vlastním souboru spraydrone_trailer_car.blend (jména objektů jsou v .blend globální
a shodují se s velkou verzí). Kolekci SprayDrone každé sestavení postaví znovu (build_drone.py, drony S, M = A, L)
a všechny tři posadí na střed heliportu.

Spuštění v Blenderu:
    p = r"...\\build_trailer_car.py"; exec(open(p, encoding="utf-8").read(), {"__file__": p, "__name__": "__main__"})
Bez okna (přestavba + uložení + export): viz headless_build.py.
"""

import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdt_parts as P  # noqa: E402
import build_drone as D  # noqa: E402

importlib.reload(P)
importlib.reload(D)

COLLECTION_NAME = "SprayDroneTrailerCar"
PREVIEW_COLLECTION = "SprayDroneTrailerCar_Preview"   # jen do Blenderu, neexportuje se
COMPONENT_NAME = "sprayDroneTrailerCar_main_component1"
ROOT_NAME = "sprayDroneTrailerCar_vis"

# kolizní skupiny a masky převzaté z vanilla ABI Water Trailer 550
COL_VEHICLE = (0x10004, 0xfe3ffb83)
COL_TRIGGER = (0x20000000, 0x40000000)
COL_FILL_ROOT = (0x40000000, 0x20000000)

# --- paluba ---
BASE_LEN = 4.20
BASE_W = 2.10
BASE_Y0 = -BASE_LEN / 2
BASE_Y1 = BASE_LEN / 2
DECK_TOP = 0.72
DECK_PLATE = 0.035
RAIL_H = 0.18
RAIL_W = 0.06
IBEAM_X = 0.40
IBEAM_H = 0.14

# --- podvozek (Stema Trius: pneu 195/50 R13, rozteč 0,70, rozchod ±0,89) ---
# Kola si hra generuje sama z rozměru pneumatiky; modelovaná kola jsou jen náhled.
TIRE_DIMENSIONS = "195_50R13"
WHEEL_R = (13 * 0.0254 + 2 * 0.195 * 0.50) / 2
WHEEL_W = 0.195
TRACK_X = 0.85
AXLE_Y = [0.05, 0.75]

# --- oj do A s kulovou spojkou ---
DRAWBAR_ROOT_X = 0.55
DRAWBAR_Z = 0.50
COUPLER_Y = -3.55
COUPLER_Z = 0.50

# --- horní plošina ---
TOP_SURF = 2.50
TOP_PLATE = 0.05
TOP_BEAM_H = 0.12
TOP_Y0 = BASE_Y0 - 0.20
TOP_Y1 = BASE_Y1 + 0.20
TOP_W = BASE_W
POST = 0.08
POST_X = TOP_W / 2 - POST / 2
POST_Y = [BASE_Y0 + 0.07, 0.0, BASE_Y1 - 0.07]
POST_TOP = TOP_SURF - TOP_PLATE - TOP_BEAM_H

# --- skládací žebřík zezadu na levém boku ---
# Visí na závěsu pod zadní hranou plošiny. Složení: vyklopit dozadu do vodorovné polohy (celý
# pohyb zůstává za vlekem), pak zasunout dopředu do držáků pod plošinou.
LADDER_X = (0.30, 0.72)          # vnější štěrbina míjí zadní světlo (x 0,78-0,98)
LADDER_HINGE_Y = TOP_Y1
LADDER_HINGE_Z = POST_TOP - 0.11
LADDER_Y_BOTTOM = TOP_Y1 + 0.35
LADDER_RACK_Y = (0.35, 1.55)
LADDER_COL_MIN_Z = 0.25          # spodek kolize žebříku nad zemí
LADDER_COL_THICKNESS = 0.10

DRONE_Y = 0.0
# tři velikosti dronu (build_drone.SPECS), všechny v i3d na středu heliportu, viditelnost řídí konfigurace
DRONE_VARIANTS = {"S": "Drone_S_", "M": "Drone_A_", "L": "Drone_L_"}
DRONE_PREFIX = DRONE_VARIANTS["M"]
DRONE_HIDDEN = ("S", "L")         # v i3d skryté (visibility false), výchozí je M
DRONE_COLLECTION = "SprayDrone"
DRONE_TILT_Z = {"S": 0.53, "M": 0.55, "L": 0.65}   # kloub náklonu za letu, nad lyžinami
# LED pod motory: přední ramena (1, 2) červená, zadní (3, 4) zelená jako u DJI Agras; barva jde do barvy vrcholů,
# svit řídí skript parametrem lightIds0 (vehicleShader staticLight_vertex)
LED_COLORS = {1: (1.0, 0.03, 0.02), 2: (1.0, 0.03, 0.02), 3: (0.03, 1.0, 0.08), 4: (0.03, 1.0, 0.08)}
LED_SIZE = (0.07, 0.07, 0.025)
LED_LIGHT_RANGE = 3.0
# úchyty lyžin dronu: dva na každé lyžině mezi příčkou a nohami, čelist se při skládání vleku překlopí přes trubku
CLAMP_Y = (-0.075, 0.075)
CLAMP_W = 0.07
CLAMP_POST = 0.04
CLAMP_GAP = 0.01
CLAMP_JAW_T = 0.02
CLAMP_OPEN_DEG = 100
CLAMP_TIME = (2.0, 2.4)            # s ve foldLadder: po složení dronu (0–2 s), souběžně s vyklopením žebříku
GEN_POS = (0.55, -1.35)
GEN_EXHAUST = (0.80, -1.70, 1.56)  # výfuk centrály nahoře na zadním levém rohu

JOCKEY_X, JOCKEY_Y = 0.27, COUPLER_Y + 0.75
JOCKEY_LIFT = 0.20                # o kolik se kolečko při zapřažení zvedne
# kolize kolečka (vzor supportCol ABI Water Trailer 550): odpojený vlek na ní stojí, animace moveSupport ji zvedá
JOCKEY_COL = (0.06, 0.10, 0.22)   # půl šířky, půl délky, výška nad zemí

# heliport pod dronem: tmavý kruh, bílé mezikruží a "H" (vrstvy nad palubou kvůli z-fightingu)
# (lyžiny S x ±0,34, M ±0,42, L ±0,56 leží vně H; rohy lyžin L uvnitř mezikruží)
HELI_R = 0.98
HELI_RING = (0.83, 0.93)
HELI_H = (0.56, 0.90, 0.12)       # šířka, výška (po Y), tloušťka čar
HELI_LAYER = 0.003

# baterie: držák u centrály (stojí konektorem dolů, po Y za sebou) a nabíječka v levém předním rohu horní paluby
BATTERY_COUNT = 5
RACK_X = 0.70
RACK_Y0 = -0.07                   # čelo první baterie (+Y), další jdou po -Y
RACK_PITCH = 0.165
RACK_DOCK = 0.05
BATTERY_MAX = P.BATTERY_SIZES["L"]  # držák i šachty nabíječky musí pojmout největší (DB2160)
DRONE_BATTERY = {"S": (0.0, 0.18), "M": (0.0, 0.215), "L": (0.0, 0.24)}      # xy baterie na hřbetu trupu (vzadu, napříč)
DRONE_FILL_PORT = {"S": (0.0, -0.11), "M": (0.0, -0.13), "L": (0.0, -0.17)}  # plnicí hrdlo před GPS věží

# nabíječka: šachty 2 × 3 (baterie stojí konektorem dolů, rukojetí nahoru), šestá buňka je ovládací panel
CHARGER_CELL_X = (0.45, 0.755)
CHARGER_CELL_Y = (-2.05, -1.86, -1.67)
CHARGER_SHAFT = (BATTERY_MAX[1] + 0.02, BATTERY_MAX[2] + 0.02)
CHARGER_WALL = 0.035
CHARGER_FEET = 0.015
CHARGER_DOCK = 0.035              # výška dna šachet nad spodkem těla
CHARGER_SLOTS = [(0, 0), (1, 0), (0, 1), (1, 1), (1, 2)]
CHARGER_CONSOLE = (0, 2)
CHARGER_EXPOSED = 0.025           # o kolik tělo baterie vyčnívá nad nabíječku (plus rukojeť)
CABLE_R = 0.01
CHARGER_SOCKET_Y, CHARGER_SOCKET_Z = -1.67, 0.14    # zásuvka na levé vnější stěně truhly (výška nad palubou)
# truhla nabíječky na horní palubě: stěny kolem nabíječky, víko na předním závěsu (chargerLid), otevřené = rozložený vlek
CHEST_WALL = 0.03
CHEST_GAP_X, CHEST_GAP_Y = 0.06, 0.05
CHEST_LID_CLEAR = 0.13            # světlá výška nad okrajem nabíječky (rukojeti největších baterií)
CHEST_LID_T = 0.03
CHEST_OPEN_DEG = 92
CHEST_LID_TIME = (0.2, 1.0)       # s ve foldLadder: víko se zavírá při skládání dronu, kabel se odpojí hned na začátku
CHEST_CABLE_TIME = (0.0, 0.05)
GEN_SOCKET = (0.88, -1.45, 1.15)                     # zásuvka na levém boku elektrocentrály

# modrý navíječ pod plošinou vpředu vpravo, hadice z něj přes vodítko na pravý okraj horní desky a volně po přední
# části desky (před heliportem, vedle nabíječky); k dronu jde zepředu mezi předními rameny
REEL = (-POST_X + 0.18, -1.78, POST_TOP - 0.30)
REEL_R = 0.18
HOSE_R = 0.02
HOSE_SEGMENTS = 24
HOSE_COIL_R = REEL_R + HOSE_R
HOSE_Z = TOP_SURF + HOSE_R + 0.006
_HY = REEL[1] + 0.21
HOSE_FEED = [(REEL[0] - 0.08, REEL[1] + HOSE_COIL_R, REEL[2]), (REEL[0] - 0.08, _HY - 0.005, 2.17),
             (-0.93, _HY, 2.255), (-0.99, _HY, 2.28), (-1.025, _HY, 2.275)]
HOSE_START = (-1.062, _HY, 2.265)
HOSE_LAY = [(-1.097, _HY + 0.055, 2.49), (-1.01, _HY + 0.13, 2.60), (-0.86, -1.20, HOSE_Z), (-0.30, -1.08, HOSE_Z),
            (-0.15, -1.50, HOSE_Z), (-0.85, -1.75, HOSE_Z), (-0.55, -2.12, HOSE_Z + 0.006)]
HOSE_PARK_DIR = (0.966, -0.259, 0.0)
NOZZLE_LEN = 0.20

# uzly pro sdílená světla hry: (jméno, poloha v Blenderu, natočení v i3d ve stupních) podle Stema Trius
LIGHT_NODES = [
    ("rearLight52_left", (0.86, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("rearLight52_right", (-0.86, BASE_Y1 + 0.005, DECK_TOP - RAIL_H + 0.08), (-90, 0, 180)),
    ("plateNumberLight03", (0.0, BASE_Y1 + 0.005, DECK_TOP - RAIL_H - 0.005), (-90, 0, -90)),
    ("sideMarker05_left", (BASE_W / 2 + 0.003, BASE_Y1 - 0.12, DECK_TOP - RAIL_H + 0.09), (0, 0, -90)),
    ("sideMarker05_right", (-BASE_W / 2 - 0.003, BASE_Y1 - 0.12, DECK_TOP - RAIL_H + 0.09), (0, 0, 90)),
]
EXIT_POINT = (BASE_W / 2 + 1.0, TOP_Y1 - 0.6, 0.0)
CAMERA_TARGET = (0.0, DRONE_Y, TOP_SURF + 1.0)

TANK_R, TANK_LEN, TANK_Y = 0.40, 1.30, 0.40       # ~600 l, nad nápravami

box, tube, plate_yz, cylinder_x, cylinder_z, capsule, empty = (
    P.box, P.tube, P.plate_yz, P.cylinder_x, P.cylinder_z, P.capsule, P.empty)


def build_chassis():
    rail_z0 = DECK_TOP - RAIL_H
    for side, sx in (("L", 1), ("R", -1)):
        x_out = sx * BASE_W / 2
        box(f"Rail_{side}", x_out, x_out - sx * RAIL_W, BASE_Y0, BASE_Y1, rail_z0, DECK_TOP, "SDT_Frame")
        box(f"IBeam_{side}", sx * IBEAM_X - 0.04, sx * IBEAM_X + 0.04, BASE_Y0, BASE_Y1,
            DECK_TOP - DECK_PLATE - IBEAM_H, DECK_TOP - DECK_PLATE, "SDT_Frame")
        P.reflective_tape(f"Tape_{side}", x_out, sx, BASE_Y0 + 0.05, BASE_Y1 - 0.05, rail_z0 + 0.05, rail_z0 + 0.12,
                          seg=0.25)
    box("Deck", -BASE_W / 2 + RAIL_W, BASE_W / 2 - RAIL_W, BASE_Y0, BASE_Y1,
        DECK_TOP - DECK_PLATE, DECK_TOP - 0.005, "SDT_DeckWood")
    box("FrontBeam", -BASE_W / 2, BASE_W / 2, BASE_Y0, BASE_Y0 + 0.08, rail_z0, DECK_TOP, "SDT_Frame")
    box("RearBeam", -BASE_W / 2, BASE_W / 2, BASE_Y1 - 0.08, BASE_Y1, rail_z0, DECK_TOP, "SDT_Frame")
    box("LicensePlateMount", -0.28, 0.28, BASE_Y1 - 0.06, BASE_Y1, rail_z0 - 0.14, rail_z0, "SDT_Frame")

    for i, ay in enumerate(AXLE_Y, 1):
        tube(f"Axle_{i}", (-TRACK_X, ay, WHEEL_R), (TRACK_X, ay, WHEEL_R), 0.035, "SDT_Frame")
        for side, sx in (("L", 1), ("R", -1)):
            cylinder_x(f"Wheel_{i}{side}", (sx * TRACK_X, ay, WHEEL_R), WHEEL_R, WHEEL_W, "SDT_Rubber", segments=28)
            cylinder_x(f"Rim_{i}{side}", (sx * (TRACK_X + 0.005), ay, WHEEL_R), 0.17, WHEEL_W + 0.004, "SDT_Rim")
            box(f"SwingArm_{i}{side}", sx * IBEAM_X - 0.03, sx * IBEAM_X + 0.03, ay - 0.30, ay + 0.05,
                WHEEL_R - 0.03, WHEEL_R + 0.05, "SDT_Steel")
            box(f"Hanger_{i}{side}", sx * IBEAM_X - 0.03, sx * IBEAM_X + 0.03, ay - 0.34, ay - 0.26,
                WHEEL_R + 0.05, DECK_TOP - DECK_PLATE - IBEAM_H, "SDT_Frame")


def build_drawbar():
    tip = Vector((0, COUPLER_Y + 0.25, DRAWBAR_Z))
    for side, sx in (("L", 1), ("R", -1)):
        root = Vector((sx * DRAWBAR_ROOT_X, BASE_Y0 + 0.40, DRAWBAR_Z))
        tube(f"Drawbar_{side}", root, tip, 0.045, "SDT_Frame", segments=8)
        box(f"DrawbarMount_{side}", root.x - 0.06, root.x + 0.06, BASE_Y0, BASE_Y0 + 0.45,
            DRAWBAR_Z - 0.05, DECK_TOP - DECK_PLATE, "SDT_Frame")
    build_coupler(tip)
    # opěrné kolečko: pevná objímka + pohyblivá skupina jockeyWheel (animace moveSupport ji zvedá)
    jx, jy = JOCKEY_X, JOCKEY_Y
    box("Jockey_Clamp", jx - 0.14, jx + 0.04, jy - 0.05, jy + 0.05, DRAWBAR_Z - 0.04, DRAWBAR_Z + 0.06, "SDT_Frame")
    moving = [
        tube("Jockey_Tube", (jx, jy, 0.20), (jx, jy, DRAWBAR_Z + 0.30), 0.03, "SDT_Steel", segments=12),
        tube("Jockey_Crank", (jx, jy, DRAWBAR_Z + 0.30), (jx, jy, DRAWBAR_Z + 0.36), 0.012, "SDT_Frame", segments=8),
        box("Jockey_Fork", jx - 0.05, jx + 0.05, jy - 0.03, jy + 0.03, 0.08, 0.21, "SDT_Steel"),
        cylinder_x("Jockey_Wheel", (jx, jy, 0.10), 0.10, 0.07, "SDT_Rubber", segments=20),
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
    # vanilla přívěsy mají attacherJoint v i3d natočený "0 90 0" (osa Y i3d = osa Z Blenderu)
    aj = empty("attacherJoint", (0, COUPLER_Y, COUPLER_Z))
    aj.rotation_euler = (0, 0, math.radians(90))


def build_coupler(tip):
    """Nájezdová brzda s kulovou hlavou (styl přívěsů za auto): střed koule tažného zařízení = attacherJoint
    (0, COUPLER_Y, COUPLER_Z). Hlava s rukojetí a ukazatelem opotřebení, táhlo v gumovém měchu, skříň nájezdu na
    vrcholu oje, ruční brzda s pákou a plynovou vzpěrou, táhlo brzdy, pojistné lanko s karabinou a kabel 13pin
    se zástrčkou. Jen vizuál: kolize colDrawbar a geometrie tažení se nemění."""
    by, bz = COUPLER_Y, COUPLER_Z
    az = bz + 0.027                                   # osa táhla a skříně
    P.loft_y("Coupler_Head", [
        (by - 0.062, 0.020, bz + 0.015, bz + 0.050, 2.5), (by - 0.050, 0.036, bz, bz + 0.066, 3.0),
        (by - 0.020, 0.046, bz - 0.008, bz + 0.074, 3.5), (by + 0.030, 0.046, bz - 0.008, bz + 0.076, 3.5),
        (by + 0.060, 0.040, bz, bz + 0.066, 3.0), (by + 0.080, 0.030, bz + 0.005, bz + 0.050, 2.5)],
        "SDT_CastIron")
    tube("Coupler_Handle", (0, by - 0.045, bz + 0.072), (0, by + 0.12, bz + 0.107), 0.011, "SDT_CastIron", segments=10)
    tube("Coupler_HandleGrip", (0, by + 0.10, bz + 0.103), (0, by + 0.165, bz + 0.116), 0.016, "SDT_PaintRed",
         segments=12)
    cylinder_x("Coupler_WearRing", (0.047, by + 0.005, bz + 0.042), 0.012, 0.008, "SDT_Plastic", segments=16)
    cylinder_x("Coupler_WearIndicator", (0.052, by + 0.005, bz + 0.042), 0.008, 0.006, "SDT_LedGreen", segments=12)
    tube("Coupler_DrawTube", (0, by + 0.07, az), (0, tip.y + 0.02, az), 0.025, "SDT_Steel", segments=14)
    pleats = []
    y0, y1, n = by + 0.095, by + 0.185, 8
    for k in range(2 * n + 1):
        r = 0.031 if k % 2 == 0 else 0.042
        pleats.append((y0 + (y1 - y0) * k / (2 * n), r, az - r, az + r, 2.0))
    P.loft_y("Coupler_Bellows", pleats, "SDT_Rubber", segments=18)
    hy0, hy1 = y1, -2.88
    P.loft_y("Coupler_Housing", [
        (hy0, 0.046, az - 0.050, az + 0.050, 6.0), (hy0 + 0.02, 0.052, az - 0.055, az + 0.055, 6.0),
        (hy1 - 0.07, 0.052, az - 0.058, az + 0.058, 6.0), (hy1, 0.044, az - 0.040, az + 0.040, 5.0)], "SDT_Steel")
    for side, sx in (("L", 1), ("R", -1)):
        box(f"Coupler_Flange_{side}", sx * 0.050, sx * 0.058, -3.26, -2.96, az - 0.07, az + 0.06, "SDT_Steel")
        for k, fy in enumerate((-3.20, -3.02)):
            cylinder_x(f"Coupler_Bolt_{side}{k}", (sx * 0.062, fy, az), 0.011, 0.01, "SDT_Steel", segments=6)
    top = az + 0.058
    px, py = 0.0, -3.05
    box("Coupler_BrakePivot", px - 0.022, px + 0.022, py - 0.03, py + 0.03, top - 0.005, top + 0.03, "SDT_Steel")
    lever_end = Vector((px, -2.78, top + 0.19))
    tube("Coupler_BrakeLever", (px, py, top + 0.02), lever_end, 0.013, "SDT_Frame", segments=10)
    grip_dir = (lever_end - Vector((px, py, top + 0.02))).normalized()
    tube("Coupler_BrakeGrip", lever_end - grip_dir * 0.03, lever_end + grip_dir * 0.07, 0.019, "SDT_Rubber", segments=12)
    lever_mid = Vector((px, py, top + 0.02)).lerp(lever_end, 0.4)
    spring_foot = Vector((0.03, -3.24, az + 0.035))
    tube("Coupler_GasSpring", spring_foot, spring_foot.lerp(lever_mid, 0.6), 0.011, "SDT_Frame", segments=10)
    tube("Coupler_GasSpringRod", spring_foot.lerp(lever_mid, 0.6), lever_mid, 0.005, "SDT_Steel", segments=8)
    tube("Coupler_BrakeRod", (0, hy1 + 0.005, az - 0.01), (0, BASE_Y0 - 0.02, az - 0.01), 0.008, "SDT_Steel", segments=8)
    cable = P.hermite_path([(0.024, py + 0.02, top + 0.02), (0.06, -3.07, az + 0.04), (0.075, -3.22, az - 0.04),
                            (0.07, -3.37, bz - 0.07), (0.045, by + 0.07, bz - 0.095), (0.035, by + 0.045, bz - 0.10)],
                           samples=10)
    P.sweep("Coupler_BreakawayCable", cable, 0.0035, "SDT_Steel", segments=6)
    end = cable[-1]
    ring = [end + Vector((0, 0.018 * math.sin(a), -0.018 - 0.028 * math.cos(a)))
            for a in (2 * math.pi * k / 16 for k in range(17))]
    P.sweep("Coupler_Carabiner", ring, 0.0035, "SDT_Steel", segments=6)

    root = Vector((DRAWBAR_ROOT_X, BASE_Y0 + 0.40, DRAWBAR_Z))
    along = [root.lerp(tip, t) + Vector((-0.012, 0, 0.07)) for t in (0.3, 0.55, 0.8)]
    plug_a, plug_b = Vector((0.08, -3.30, bz - 0.005)), Vector((0.074, -3.39, bz - 0.04))
    wire = P.hermite_path([(0.42, BASE_Y0 + 0.03, DECK_TOP - 0.12)] + [tuple(p) for p in along] +
                          [(0.09, -3.18, bz + 0.02), tuple(plug_a)], samples=10)
    P.sweep("Coupler_13PinCable", wire, 0.006, "SDT_HoseBlack", segments=8)
    d = (plug_b - plug_a).normalized()
    tube("Coupler_13PinPlug", plug_a - d * 0.01, plug_b, 0.021, "SDT_Plastic", segments=14)
    tube("Coupler_13PinCap", plug_b, plug_b + d * 0.012, 0.024, "SDT_ChargerGrey", segments=14)
    box("Coupler_13PinDock", 0.40, 0.46, BASE_Y0 - 0.005, BASE_Y0 + 0.001, DECK_TOP - 0.16, DECK_TOP - 0.08,
        "SDT_Plastic")


def build_upper_structure():
    for side, sx in (("L", 1), ("R", -1)):
        px = sx * POST_X
        for i, py in enumerate(POST_Y):
            box(f"Post_{side}{i}", px - POST / 2, px + POST / 2, py - POST / 2, py + POST / 2,
                DECK_TOP, POST_TOP, "SDT_Frame")
        yf, yr = POST_Y[0], POST_Y[-1]
        plate_yz(f"Gusset_{side}_Front", px, 0.015, [(yf, POST_TOP - 0.45), (yf + 0.45, POST_TOP), (yf, POST_TOP)],
                 "SDT_Frame")
        plate_yz(f"Gusset_{side}_Rear", px, 0.015, [(yr, POST_TOP - 0.45), (yr, POST_TOP), (yr - 0.45, POST_TOP)],
                 "SDT_Frame")
        plate_yz(f"Knee_{side}", px, 0.015,
                 [(POST_Y[1] - 0.30, POST_TOP), (POST_Y[1], POST_TOP - 0.30), (POST_Y[1] + 0.30, POST_TOP)], "SDT_Frame")
        box(f"TopBeam_{side}", px - POST / 2, px + POST / 2, TOP_Y0, TOP_Y1, POST_TOP, POST_TOP + TOP_BEAM_H,
            "SDT_Frame")
    for i, py in enumerate([TOP_Y0 + 0.04] + POST_Y + [TOP_Y1 - 0.04]):
        box(f"TopCross_{i}", -POST_X, POST_X, py - 0.035, py + 0.035, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
    hw = TOP_W / 2
    box("TopDeck", -hw, hw, TOP_Y0, TOP_Y1, TOP_SURF - TOP_PLATE, TOP_SURF, "SDT_TopDeck")
    for side, sx in (("L", 1), ("R", -1)):
        box(f"TopLip_{side}", sx * hw - sx * 0.035, sx * hw, TOP_Y0, TOP_Y1, TOP_SURF, TOP_SURF + 0.04, "SDT_Frame")
    box("TopLip_Front", -hw, hw, TOP_Y0, TOP_Y0 + 0.035, TOP_SURF, TOP_SURF + 0.04, "SDT_Frame")
    box("WorkLight", -0.25, 0.25, TOP_Y0 + 0.01, TOP_Y0 + 0.07, TOP_SURF + 0.04, TOP_SURF + 0.10, "SDT_LampAmber")


def ladder_geometry():
    hinge = Vector((0, LADDER_HINGE_Y, LADDER_HINGE_Z))
    foot = Vector((0, LADDER_Y_BOTTOM, 0.02))
    return hinge, foot, (foot - hinge).length


def build_ladder():
    hinge, foot, length = ladder_geometry()
    # pevné díly: závěsy pod zadní hranou plošiny a kolébky, do kterých se žebřík zasune
    for side, x in (("In", LADDER_X[0] - 0.055), ("Out", LADDER_X[1] + 0.055)):
        box(f"LadderHingeBracket_{side}", x - 0.01, x + 0.01, hinge.y - 0.05, hinge.y + 0.01,
            hinge.z - 0.03, POST_TOP, "SDT_Frame")
    for i, ry in enumerate(LADDER_RACK_Y):
        box(f"LadderRack_{i}_Bar", LADDER_X[0] - 0.08, LADDER_X[1] + 0.08, ry - 0.03, ry + 0.03,
            hinge.z - 0.045, hinge.z - 0.030, "SDT_Frame")
        # kolébky dál od žebříku, než sahají čepy závěsu, jinak by jimi čepy při zasouvání neprošly
        for side, x in (("In", LADDER_X[0] - 0.07), ("Out", LADDER_X[1] + 0.07)):
            box(f"LadderRack_{i}_Hanger{side}", x - 0.01, x + 0.01, ry - 0.03, ry + 0.03,
                hinge.z - 0.045, POST_TOP, "SDT_Frame")

    # pohyblivé díly: ladderSlide (posun dopředu) -> ladderHinge (vyklopení) -> žebřík
    slide = empty("ladderSlide", hinge)
    pivot = empty("ladderHinge", hinge)
    pivot.parent = slide
    pivot.matrix_parent_inverse = Matrix.Identity(4)
    pivot.matrix_world = Matrix.Translation(hinge)
    parts = []
    for side, x in (("In", LADDER_X[0]), ("Out", LADDER_X[1])):
        parts.append(tube(f"Ladder_Rail_{side}", (x, foot.y, foot.z), (x, hinge.y, hinge.z), 0.022, "SDT_Steel",
                          segments=10))
        parts.append(tube(f"Ladder_Pin_{side}", (x - 0.045, hinge.y, hinge.z), (x + 0.045, hinge.y, hinge.z), 0.012,
                          "SDT_Steel", segments=8))
        parts.append(cylinder_z(f"Ladder_Foot_{side}", (x, foot.y, 0.01), 0.035, 0.02, "SDT_Rubber", segments=12))
    rungs = round(length / 0.28)
    for i in range(1, rungs + 1):
        p = foot.lerp(hinge, i / (rungs + 0.4))
        parts.append(box(f"Ladder_Rung_{i:02d}", LADDER_X[0], LADDER_X[1], p.y - 0.04, p.y + 0.04, p.z - 0.012,
                         p.z + 0.012, "SDT_TopDeck"))
    for o in parts:
        world = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = world
    return pivot


def build_ladder_collision(pivot):
    """Kolize žebříku: kvádr podél šikmého žebříku v jeho kloubu, takže se s ním vyklápí i zasouvá.

    Končí LADDER_COL_MIN_Z nad zemí: dotek s terénem by vlek nadzvedával (kompoundní díl téže komponenty).
    """
    hinge, foot, _ = ladder_geometry()
    bottom = hinge.lerp(foot, (hinge.z - LADDER_COL_MIN_Z) / (hinge.z - foot.z))
    d = bottom - hinge
    obj = box("colLadder", LADDER_X[0] - 0.04, LADDER_X[1] + 0.04, -LADDER_COL_THICKNESS / 2, LADDER_COL_THICKNESS / 2,
              0, d.length, "SDT_Frame")
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    obj.matrix_world = Matrix.Translation(Vector((0, hinge.y, hinge.z))) @ rot @ obj.matrix_world
    return _as_shape(obj, pivot, COL_VEHICLE, compoundChild=True, density=0.001)


def ladder_fold_angle():
    """Úhel vyklopení kolem osy X, po kterém žebřík míří vodorovně dozadu (+Y)."""
    hinge, foot, _ = ladder_geometry()
    d = foot - hinge
    return -math.atan2(d.z, d.y)


def set_ladder(t):
    """Náhled animace: 0 = rozložený, 0,5 = vodorovně za vlekem, 1 = zasunutý pod plošinou."""
    _, _, length = ladder_geometry()
    pivot = bpy.data.objects["ladderHinge"]
    slide = bpy.data.objects["ladderSlide"]
    pivot.rotation_euler.x = ladder_fold_angle() * min(t / 0.5, 1.0)
    slide.location.y = LADDER_HINGE_Y - length * max(0.0, (t - 0.5) / 0.5)
    bpy.context.view_layer.update()


def build_equipment():
    z = DECK_TOP
    tank_r, tank_len, tank_y = TANK_R, TANK_LEN, TANK_Y
    P.leg_tank("Tank_Main", tank_y, z, tank_r, tank_len, (-0.40, -0.13, 0.13, 0.40), (-0.40, 0.40), 0.30)
    ix, iy = -0.55, -1.25                             # ~100 l indukční
    top = P.cone_tank("Tank_Induction", ix, iy, z, 0.30, stand_h=0.35, cone_h=0.25, body_h=0.45)
    P.generator("Gen_0", *GEN_POS, z)
    ex, ey, ez = GEN_EXHAUST
    tube("Gen_0_Exhaust", (ex, ey, z + 0.72), (ex, ey, ez), 0.025, "SDT_Steel", segments=10)
    empty("generatorExhaust", (ex, ey, ez + 0.01))
    px, py = -0.55, -0.55
    P.pump("Pump", px, py, z)
    box("Toolbox", -0.92, 0.95, 1.30, 1.90, z, z + 0.45, "SDT_Mesh")
    build_hose_reel()


def build_hose_reel():
    """Modrý navíječ pod plošinou vpravo: buben s osou napříč, bočnice, konzoly vně bočnic (buben mezi nimi zůstává
    volný pro navinutou hadici) a otočný přívod na vnitřním konci osy."""
    rx, ry, rz = REEL
    cylinder_x("HoseReel_0_Drum", (rx, ry, rz), REEL_R, 0.20, "SDT_HoseBlue")
    for dx in (-0.11, 0.11):
        cylinder_x(f"HoseReel_0_Flange{dx:+.2f}", (rx + dx, ry, rz), REEL_R + 0.06, 0.015, "SDT_Frame")
    for side, xa, xb in (("Out", rx - 0.135, rx - 0.12), ("In", rx + 0.12, rx + 0.135)):
        box(f"HoseReel_0_Bracket{side}", xa, xb, ry - 0.04, ry + 0.04, rz - 0.04, TOP_SURF - TOP_PLATE, "SDT_Frame")
    tube("HoseReel_0_Axle", (rx - 0.14, ry, rz), (rx + 0.14, ry, rz), 0.02, "SDT_Steel", segments=12)


def _bbox_center(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(pts, Vector()) / len(pts)


def drone_spec(prefix):
    key = next(k for k, p in DRONE_VARIANTS.items() if p == prefix)
    return key, D.SPECS[key]


def rotor_levels(prefix=DRONE_PREFIX):
    return drone_spec(prefix)[1]["levels"]


def drone_frame(prefix=DRONE_PREFIX):
    """Střed trupu (xy) a azimut nosu dronu (směr od trupu ke kamerám)."""
    body = _bbox_center(bpy.data.objects[prefix + "Body"])
    nose = _bbox_center(bpy.data.objects[prefix + "Nose"])
    return body.xy, math.atan2(nose.y - body.y, nose.x - body.x)


def _set_parent(obj, parent, world):
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = world


def _drone_empty(name, prefix=DRONE_PREFIX):
    e = bpy.data.objects.get(prefix + name)
    if e is None:
        e = bpy.data.objects.new(prefix + name, None)
        e.empty_display_type = "PLAIN_AXES"
        e.empty_display_size = 0.1
        bpy.data.collections[DRONE_COLLECTION].objects.link(e)
    return e


def build_drones():
    """Všechny tři drony znovu z build_drone.py (kolekce SprayDrone), složené, bez staré baterie v trupu,
    spodní listy složené ven podél ramene (dovnitř by vjely do trupu)."""
    coll = D.clear_collection()
    for key, prefix in DRONE_VARIANTS.items():
        D.build_drone(coll, name=prefix[:-1], spec=D.SPECS[key], arms_folded=1.0, with_battery=False, bottom_out=True)
    bpy.context.view_layer.update()


def build_rotors(prefix=DRONE_PREFIX):
    """Každá vrtule (horní a spodní u každého motoru) pod vlastním uzlem na ose motoru, ať se dá točit.

    Uzel rotoru má natočení svého ramene, listy zůstanou na místě (počátek listu = střed náboje).
    """
    for i in range(1, 5):
        pivot = bpy.data.objects[f"{prefix}ArmPivot_{i}"]
        for level in rotor_levels(prefix):
            blades = [bpy.data.objects[f"{prefix}Blade_{i}{level}{b}"] for b in (0, 1)]
            rotor = _drone_empty(f"Rotor_{i}{level}", prefix)
            if rotor.parent is not pivot:
                rot = pivot.matrix_world.to_quaternion().to_matrix().to_4x4()
                _set_parent(rotor, pivot, Matrix.Translation(blades[0].matrix_world.translation) @ rot)
            for b in blades:
                if b.parent is not rotor:
                    _set_parent(b, rotor, b.matrix_world.copy())


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def drone_fold_parts(prefix=DRONE_PREFIX):
    """Natočení kloubů dronu složeno/rozloženo kolem svislé osy (radiány, lokálně k rodiči).

    Ramena: o kolik se kloub musí otočit, aby motor dosedl do rohu rozložené rozteče (build_drone.SPECS arm_span).
    Listy (lokálně k rotoru): horní se roztáhnou napříč ramene, spodní podél, ať se páry kříží.
    Vrací [(uzel, složeno, rozloženo, druh)], druh "arm" nebo "blade".
    """
    bpy.context.view_layer.update()
    span = drone_spec(prefix)[1]["arm_span"]
    center, nose_az = drone_frame(prefix)
    fwd = Vector((math.cos(nose_az), math.sin(nose_az)))
    left = Vector((-fwd.y, fwd.x))
    parts = []
    for i in range(1, 5):
        pivot = bpy.data.objects[f"{prefix}ArmPivot_{i}"]
        p = pivot.matrix_world.translation.xy
        motor = _bbox_center(bpy.data.objects[f"{prefix}Motor_{i}"]).xy
        rel = p - center
        corner = (center + fwd * math.copysign(span[0] / 2, rel.dot(fwd))
                  + left * math.copysign(span[1] / 2, rel.dot(left)))
        delta = _wrap(math.atan2(*reversed(corner - p)) - math.atan2(*reversed(motor - p)))
        folded = pivot.matrix_local.to_euler().z
        parts.append((pivot.name, folded, folded + delta, "arm"))
        for level in rotor_levels(prefix):
            spread = (math.pi / 2, -math.pi / 2) if level == "Top" else (0.0, math.pi)
            for b in (0, 1):
                blade = bpy.data.objects[f"{prefix}Blade_{i}{level}{b}"]
                bf = blade.matrix_local.to_euler().z
                parts.append((blade.name, bf, bf + spread[b], "blade"))
    return parts


def set_drone_unfold(t, parts=None, prefix=DRONE_PREFIX):
    """Náhled rozložení: 0 = složeno (stav v i3d), 1 = rozloženo."""
    for name, folded, unfolded, _ in parts or drone_fold_parts(prefix):
        bpy.data.objects[name].rotation_euler.z = folded + (unfolded - folded) * t
    bpy.context.view_layer.update()


def place_drone(prefix=DRONE_PREFIX):
    """Posadí dron doprostřed plošiny (střed heliportu), nosem po směru jízdy (-Y), s rameny složenými.

    Hierarchie pro hru: <prefix>Root (počátek = střed pod lyžinami, skript letu ho odpojí do světa)
    -> <prefix>Tilt (náklon za letu) -> díly, ramena (ArmPivot) -> rotory -> listy.
    Poloha se počítá z geometrie trupu, takže skript jde pouštět opakovaně.
    """
    # baterii dronu nahrazují modely battery1..5 (skript ji dává do <prefix>BatterySlot)
    for part in ("Battery", "BatteryLatch"):
        o = bpy.data.objects.get(prefix + part)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    objs = P.drone_parts(prefix)
    if not objs:
        return
    # matrix_world dětí se po změně rodiče přepočítá až tady; bez toho se čtou staré polohy
    bpy.context.view_layer.update()
    tilt = _drone_empty("Tilt", prefix)
    for o in P.drone_parts(prefix):
        if o.parent is not None and (o.parent is tilt or o is tilt or not o.parent.name.startswith(prefix)):
            w = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = w
    bpy.context.view_layer.update()
    objs = P.drone_parts(prefix)
    roots = [o for o in objs if o.parent is None and o is not tilt]
    center, nose_az = drone_frame(prefix)
    floor = P.drone_footprint(objs).z
    target = Vector((0, DRONE_Y, TOP_SURF + 0.005))
    xf = (Matrix.Translation(target) @ Matrix.Rotation(-math.pi / 2 - nose_az, 4, "Z")
          @ Matrix.Translation(-Vector((center.x, center.y, floor))))
    for o in roots:
        o.matrix_world = xf @ o.matrix_world
    bpy.context.view_layer.update()
    build_rotors(prefix)
    bpy.context.view_layer.update()
    root = _group(prefix + "Root", bpy.data.objects[ROOT_NAME], tuple(target))
    _set_parent(tilt, root, Matrix.Translation(target + Vector((0, 0, DRONE_TILT_Z[drone_spec(prefix)[0]]))))
    for o in roots:
        _set_parent(o, tilt, o.matrix_world.copy())


def build_drone_leds(prefix=DRONE_PREFIX):
    """LED pod motorem každého ramene (dítě kloubu ramene, skládá se s ním) a malé bodové světlo pod ní.

    Objekty jsou v kolekci vleku, takže je každé sestavení smaže a postaví znovu.
    """
    bpy.context.view_layer.update()
    for i in range(1, 5):
        pivot = bpy.data.objects[f"{prefix}ArmPivot_{i}"]
        motor = bpy.data.objects[f"{prefix}Motor_{i}"]
        pts = [motor.matrix_world @ Vector(c) for c in motor.bound_box]
        cx, cy = sum(p.x for p in pts) / 8, sum(p.y for p in pts) / 8
        z1 = min(p.z for p in pts)
        sx, sy, sz = LED_SIZE
        led = box(f"{prefix}Led_{i}", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z1 - sz, z1, "SDT_NavLed")
        attr = led.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
        for d in attr.data:
            d.color_srgb = (*LED_COLORS[i], 1.0)
        led.data.color_attributes.render_color_index = 0
        _set_parent(led, pivot, led.matrix_world.copy())
        data = bpy.data.lights.get(f"{prefix}LedLight_{i}") or bpy.data.lights.new(f"{prefix}LedLight_{i}", "POINT")
        data.color = LED_COLORS[i]
        data.use_shadow = False
        data.use_custom_distance = True
        data.cutoff_distance = LED_LIGHT_RANGE
        light = bpy.data.objects.new(f"{prefix}LedLight_{i}", data)
        bpy.data.collections[COLLECTION_NAME].objects.link(light)
        _set_parent(light, led, Matrix.Translation((cx, cy, z1 - sz - 0.03)))


def clamp_open_angle(sx):
    """Otevřená čelist úchytu: sklopená nahoru a ven od lyžiny (kolem osy Y, podél lyžiny)."""
    return sx * math.radians(CLAMP_OPEN_DEG)


def build_drone_clamps(prefix=DRONE_PREFIX):
    """Úchyty lyžin dronu: pevný sloupek vedle lyžiny a čelist na závěsu (<prefix>ClampHinge_i), která ve skládací
    animaci vleku (po složení dronu) překlopí přes trubku lyžiny. V i3d je čelist otevřená (vlek rozložený).
    Celý úchyt je pod <prefix>Clamp_i (kvůli skrývání).
    """
    bpy.context.view_layer.update()
    names = []
    i = 0
    for side, sx in (("L", 1), ("R", -1)):
        skid = bpy.data.objects[f"{prefix}Skid_{side}"]
        pts = [skid.matrix_world @ Vector(c) for c in skid.bound_box]
        x_in, x_out = (min(p.x for p in pts), max(p.x for p in pts))[::sx]
        z_top = max(p.z for p in pts)
        hinge_x = x_out + sx * (CLAMP_GAP + CLAMP_POST / 2)
        hinge_z = z_top + CLAMP_JAW_T / 2 + 0.003
        for y in CLAMP_Y:
            i += 1
            y0, y1 = y - CLAMP_W / 2, y + CLAMP_W / 2
            clamp = empty(f"{prefix}Clamp_{i}", (hinge_x, y, TOP_SURF))
            post = box(f"{prefix}ClampPost_{i}", hinge_x - CLAMP_POST / 2, hinge_x + CLAMP_POST / 2, y0, y1, TOP_SURF,
                       hinge_z, "SDT_Frame")
            hinge = empty(f"{prefix}ClampHinge_{i}", (hinge_x, y, hinge_z))
            for o in (post, hinge):
                _set_parent(o, clamp, o.matrix_world.copy())
            tip = x_in - sx * 0.012
            parts = [
                box(f"{prefix}ClampJaw_{i}", min(hinge_x, tip), max(hinge_x, tip), y0, y1, hinge_z - CLAMP_JAW_T / 2,
                    hinge_z + CLAMP_JAW_T / 2, "SDT_LampAmber"),
                box(f"{prefix}ClampLip_{i}", min(tip, tip + sx * 0.012), max(tip, tip + sx * 0.012), y0, y1,
                    z_top - 0.045, hinge_z, "SDT_LampAmber"),
            ]
            for o in parts:
                _set_parent(o, hinge, o.matrix_world.copy())
            hinge.rotation_euler.y = clamp_open_angle(sx)
            names.append(hinge.name)
    bpy.context.view_layer.update()
    return names


def build_heliport():
    """Heliportové H v kruhu pod dronem: tenké vrstvy nad palubou, každá s vlastním decalLayer."""
    cx, cy, z = 0.0, DRONE_Y, TOP_SURF
    t = HELI_LAYER
    disk = cylinder_z("Heliport_Disk", (cx, cy, z + t / 2), HELI_R, t, "SDT_PaintDark", segments=64)
    ring = P.ring_z("Heliport_Ring", (cx, cy, z + 1.5 * t), *HELI_RING, t, "SDT_PaintWhite", segments=64)
    w, h, s = HELI_H
    z0, z1 = z + t, z + 2 * t
    marks = [
        box("Heliport_H_L", cx + w / 2 - s, cx + w / 2, cy - h / 2, cy + h / 2, z0, z1, "SDT_PaintWhite"),
        box("Heliport_H_R", cx - w / 2, cx - w / 2 + s, cy - h / 2, cy + h / 2, z0, z1, "SDT_PaintWhite"),
        box("Heliport_H_Bar", cx - w / 2 + s, cx + w / 2 - s, cy - s / 2, cy + s / 2, z0, z1, "SDT_PaintWhite"),
    ]
    for o, layer in [(disk, 1), (ring, 2)] + [(m, 2) for m in marks]:
        _physics(o, decalLayer=layer)


BATTERY_STAND = Matrix(((0, -1, 0, 0), (0, 0, -1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))  # konektor dolů, rukojeť nahoru


def transport_slot_matrix(k):
    lx = P.BATTERY_SIZE[0] / 2
    return Matrix.Translation((RACK_X, RACK_Y0 - k * RACK_PITCH, DECK_TOP + RACK_DOCK + lx + 0.016)) @ BATTERY_STAND


def build_battery_rack():
    """Držák baterií vedle elektrocentrály: dno s nabíjecími kontakty, rohové sloupky a horní vodítka."""
    z = DECK_TOP
    hw = BATTERY_MAX[1] / 2 + 0.025
    y1 = RACK_Y0 - P.battery_frame_offset(BATTERY_MAX)[1] + 0.025
    y0 = RACK_Y0 - (BATTERY_COUNT - 1) * RACK_PITCH - 0.165
    x0, x1 = RACK_X - hw, RACK_X + hw
    box("BatteryRack_Base", x0, x1, y0, y1, z, z + RACK_DOCK, "SDT_Frame")
    for k in range(BATTERY_COUNT):
        yc = RACK_Y0 - k * RACK_PITCH - P.BATTERY_SIZE[2] / 2
        box(f"BatteryRack_Dock_{k}", RACK_X - 0.07, RACK_X + 0.07, yc - 0.035, yc + 0.035, z + RACK_DOCK,
            z + RACK_DOCK + 0.006, "SDT_TankBlack")
    top = z + RACK_DOCK + 0.30
    for x in (x0, x1):
        for y in (y0, y1):
            tube(f"BatteryRack_Post_{x:+.2f}_{y:+.2f}", (x, y, z + RACK_DOCK), (x, y, top), 0.012, "SDT_Frame", segments=8)
        tube(f"BatteryRack_Rail_{x:+.2f}", (x, y0, top), (x, y1, top), 0.012, "SDT_Frame", segments=8)
        tube(f"BatteryRack_RailLow_{x:+.2f}", (x, y0, z + RACK_DOCK + 0.10), (x, y1, z + RACK_DOCK + 0.10), 0.010,
             "SDT_Frame", segments=8)
    for y in (y0, y1):
        tube(f"BatteryRack_Cross_{y:+.2f}", (x0, y, top), (x1, y, top), 0.012, "SDT_Frame", segments=8)


def build_batteries():
    """Sloty (prázdné uzly, baterie se k nim přilinkuje s nulovou lokální polohou) a baterie ve slotech u centrály.

    battery<k> je kořen, pod ním meshe battery<k>S / M / L (DB800 / DB1560 / DB2160) se stejným rámcem slotu:
    konektor na dně šachty, střed tloušťky jako u M (P.battery). V i3d je viditelná jen M.
    """
    vis = bpy.data.objects[ROOT_NAME]
    build_battery_rack()
    for k in range(BATTERY_COUNT):
        slot = _group(f"batterySlotTransport{k + 1}", vis)
        slot.matrix_world = transport_slot_matrix(k)
        meshes = [P.battery(f"battery{k + 1}{key}", P.BATTERY_SIZES[key]) for key in DRONE_VARIANTS]
        bat = P.group(f"battery{k + 1}", meshes)
        _set_parent(bat, slot, slot.matrix_world.copy())


def charger_box():
    sx, sy = CHARGER_SHAFT
    w = CHARGER_WALL
    x0, x1 = CHARGER_CELL_X[0] - sx / 2 - w, CHARGER_CELL_X[-1] + sx / 2 + w
    y0, y1 = CHARGER_CELL_Y[0] - sy / 2 - w, CHARGER_CELL_Y[-1] + sy / 2 + w
    z0 = TOP_SURF + CHARGER_FEET
    dock = z0 + CHARGER_DOCK
    top = dock + 0.016 + P.BATTERY_SIZE[0] - CHARGER_EXPOSED
    return x0, x1, y0, y1, z0, dock, top


def build_charger():
    """Průmyslová nabíječka (styl DJI) v levém předním rohu horní paluby: šachty pro 5 baterií svisle, konektorem
    dolů na kontakty, nad hranu šachty vyčnívá jen horní čelo s rukojetí. batterySlotDeck1..5 jsou její děti."""
    vis = bpy.data.objects[ROOT_NAME]
    x0, x1, y0, y1, z0, dock, top = charger_box()
    w = CHARGER_WALL
    sx, sy = CHARGER_SHAFT
    charger = _group("batteryCharger", vis, ((x0 + x1) / 2, (y0 + y1) / 2, TOP_SURF))
    parts = []
    for fx in (x0 + 0.05, x1 - 0.05):
        for fy in (y0 + 0.05, y1 - 0.05):
            parts.append(cylinder_z(f"Charger_Foot_{fx:+.2f}_{fy:+.2f}", (fx, fy, TOP_SURF + CHARGER_FEET / 2), 0.025,
                                    CHARGER_FEET, "SDT_Rubber", segments=12))
    parts += [
        box("Charger_Base", x0, x1, y0, y1, z0, dock, "SDT_ChargerGrey"),
        box("Charger_WallFront", x0, x1, y0, y0 + w, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallRear", x0, x1, y1 - w, y1, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallRight", x0, x0 + w, y0 + w, y1 - w, dock, top, "SDT_ChargerGrey"),
        box("Charger_WallLeft", x1 - w, x1, y0 + w, y1 - w, dock, top, "SDT_ChargerGrey"),
        box("Charger_DividerX", CHARGER_CELL_X[0] + sx / 2, CHARGER_CELL_X[1] - sx / 2, y0 + w, y1 - w, dock, top,
            "SDT_TankBlack"),
    ]
    for i in range(len(CHARGER_CELL_Y) - 1):
        ya, yb = CHARGER_CELL_Y[i] + sy / 2, CHARGER_CELL_Y[i + 1] - sy / 2
        parts.append(box(f"Charger_DividerY{i}", x0 + w, x1 - w, ya, yb, dock, top, "SDT_TankBlack"))
    rim = 0.006
    parts += [
        box("Charger_RimFront", x0, x1, y0, y0 + w, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimRear", x0, x1, y1 - w, y1, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimRight", x0, x0 + w, y0 + w, y1 - w, top, top + rim, "SDT_TankBlack"),
        box("Charger_RimLeft", x1 - w, x1, y0 + w, y1 - w, top, top + rim, "SDT_TankBlack"),
    ]
    cells = {(i, j): (CHARGER_CELL_X[i], CHARGER_CELL_Y[j]) for i in range(2) for j in range(3)}
    for k, cell in enumerate(CHARGER_SLOTS, 1):
        cx, cy = cells[cell]
        parts.append(box(f"Charger_Dock_{k}", cx - 0.07, cx + 0.07, cy - 0.035, cy + 0.035, dock, dock + 0.006,
                         "SDT_Steel"))
        lx0, lx1 = (x0 + 0.008, x0 + w - 0.008) if cell[0] == 0 else (x1 - w + 0.008, x1 - 0.008)
        for n in range(4):
            ly = cy - 0.054 + n * 0.036
            led = box(f"Charger_Led_{k}_{n}", lx0, lx1, ly - 0.01, ly + 0.01, top + rim, top + rim + 0.003, "SDT_Decal")
            P.planar_uv(led, (lx0, ly - 0.01, 0), (1, 0, 0), (0, 1, 0), lx1 - lx0, 0.02, "led")
            parts.append(led)
        _group(f"batterySlotDeck{k}", charger).matrix_world = (
            Matrix.Translation((cx, cy + P.BATTERY_SIZE[2] / 2, dock + 0.016 + P.BATTERY_SIZE[0] / 2)) @ BATTERY_STAND)

    cx, cy = cells[CHARGER_CONSOLE]
    parts.append(box("Charger_ConsoleFill", cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, dock, top,
                     "SDT_ChargerGrey"))
    tilt = Matrix.Translation((cx, cy, top + 0.03)) @ Matrix.Rotation(math.radians(-28), 4, "X")
    console = [
        box("Charger_Console", -0.11, 0.11, -0.065, 0.065, -0.08, 0.02, "SDT_ChargerGrey"),
        box("Charger_Screen", -0.08, 0.05, -0.045, 0.045, 0.02, 0.023, "SDT_Decal"),
        box("Charger_Power", 0.07, 0.095, -0.035, -0.01, 0.02, 0.026, "SDT_LedGreen"),
        box("Charger_ButtonA", 0.07, 0.095, 0.0, 0.02, 0.02, 0.028, "SDT_TankBlack"),
        box("Charger_ButtonB", 0.07, 0.095, 0.03, 0.05, 0.02, 0.028, "SDT_TankBlack"),
    ]
    for o in console:
        o.matrix_world = tilt @ o.matrix_world
    rot = tilt.to_3x3()
    P.planar_uv(console[1], tilt @ Vector((0.05, 0.045, 0.023)), rot @ Vector((-1, 0, 0)), rot @ Vector((0, -1, 0)),
                0.13, 0.09, "chargerScreen")
    parts += console

    def grille(tag, axis, face, lo, hi, sign):
        zs = [dock + 0.05 + 0.032 * n for n in range(int((top - dock - 0.16) / 0.032) + 1)]
        out = []
        for n, zc in enumerate(zs):
            a, b = (face, face + sign * 0.006) if sign > 0 else (face + sign * 0.006, face)
            if axis == "y":
                out.append(box(f"Charger_Vent{tag}_{n}", lo, hi, a, b, zc - 0.006, zc + 0.006, "SDT_Mesh"))
            else:
                out.append(box(f"Charger_Vent{tag}_{n}", a, b, lo, hi, zc - 0.006, zc + 0.006, "SDT_Mesh"))
        return out

    parts += grille("Front", "y", y0, x0 + 0.06, x1 - 0.06, -1)
    parts += grille("Right", "x", x0, y0 + 0.06, y1 - 0.06, -1)
    parts += grille("Left", "x", x1, y0 + 0.06, y1 - 0.06, 1)
    parts += [
        box("Charger_Label", x0 + 0.08, x1 - 0.08, y1, y1 + 0.003, dock + 0.12, dock + 0.24, "SDT_Decal"),
        box("Charger_LabelStripe", x0 + 0.08, x1 - 0.08, y1, y1 + 0.004, dock + 0.10, dock + 0.115, "SDT_GenOrange"),
    ]
    P.planar_uv(parts[-2], (x1 - 0.08, y1 + 0.003, dock + 0.12), (-1, 0, 0), (0, 0, 1), x1 - x0 - 0.16, 0.12,
                "chargerLabel")
    for side, fx, s in (("R", x0, -1), ("L", x1, 1)):
        hz = top - 0.06
        hy = (y0 + 0.08, y0 + 0.30)
        for n, py in enumerate(hy):
            parts.append(box(f"Charger_Handle{side}_Post{n}", min(fx, fx + s * 0.035), max(fx, fx + s * 0.035),
                             py - 0.012, py + 0.012, hz - 0.012, hz + 0.012, "SDT_TankBlack"))
        parts.append(tube(f"Charger_Handle{side}_Bar", (fx + s * 0.035, hy[0] - 0.012, hz), (fx + s * 0.035, hy[1] + 0.012, hz),
                          0.012, "SDT_Rubber", segments=10))
    gx, gy, gz = GEN_SOCKET
    parts.append(box("Gen_0_ChargeSocket", gx - 0.005, gx + 0.015, gy - 0.035, gy + 0.035, gz - 0.035, gz + 0.035,
                     "SDT_TankBlack"))
    for o in parts:
        if not o.name.startswith("Gen_0_"):
            _set_parent(o, charger, o.matrix_world.copy())
    return charger


def chest_box():
    x0, x1, y0, y1, _, _, top = charger_box()
    m = CHEST_WALL
    return x0 - CHEST_GAP_X - m, x1 + CHEST_GAP_X + m, y0 - CHEST_GAP_Y - m, y1 + CHEST_GAP_Y + m, top + CHEST_LID_CLEAR


def build_charger_chest():
    """Truhla nabíječky na horní palubě vpředu vlevo: čtyři stěny kolem nabíječky, víko na předním závěsu
    (chargerLid, v i3d otevřené = rozložený vlek) a napájecí zásuvka na vnější stěně vlevo."""
    vis = bpy.data.objects[ROOT_NAME]
    ox0, ox1, oy0, oy1, zw = chest_box()
    m, t = CHEST_WALL, CHEST_LID_T
    mat = "SDT_PaintDark"
    cx = (ox0 + ox1) / 2
    box("Chest_WallFront", ox0, ox1, oy0, oy0 + m, TOP_SURF, zw, mat)
    box("Chest_WallRear", ox0, ox1, oy1 - m, oy1, TOP_SURF, zw, mat)
    box("Chest_WallRight", ox0, ox0 + m, oy0 + m, oy1 - m, TOP_SURF, zw, mat)
    box("Chest_WallLeft", ox1 - m, ox1, oy0 + m, oy1 - m, TOP_SURF, zw, mat)
    sz = TOP_SURF + CHARGER_SOCKET_Z
    box("Chest_Socket", ox1, ox1 + 0.02, CHARGER_SOCKET_Y - 0.035, CHARGER_SOCKET_Y + 0.035, sz - 0.035, sz + 0.035,
        "SDT_TankBlack")
    for n, lx in enumerate((cx - 0.25, cx + 0.25)):
        box(f"Chest_LatchBase{n}", lx - 0.03, lx + 0.03, oy1, oy1 + 0.012, zw - 0.07, zw - 0.01, "SDT_Steel")

    hy = oy0 - 0.012
    lid = [
        box("Chest_Lid", ox0 - 0.012, ox1 + 0.012, hy, oy1 + 0.012, zw, zw + t, mat),
        box("Chest_LidLipLeft", ox1, ox1 + 0.012, oy0 + m, oy1 + 0.012, zw - 0.03, zw, mat),
        box("Chest_LidLipRight", ox0 - 0.012, ox0, oy0 + m, oy1 + 0.012, zw - 0.03, zw, mat),
        box("Chest_LidLipRear", ox0 - 0.012, ox1 + 0.012, oy1, oy1 + 0.012, zw - 0.03, zw, mat),
        box("Chest_LidStripe", ox0 + 0.05, ox1 - 0.05, hy + 0.05, hy + 0.075, zw + t, zw + t + 0.002, "SDT_GenOrange"),
        tube("Chest_LidHandle", (cx - 0.10, oy1 + 0.045, zw + t / 2), (cx + 0.10, oy1 + 0.045, zw + t / 2), 0.01,
             "SDT_Steel", segments=10),
        box("Chest_LidHandlePostA", cx - 0.105, cx - 0.095, oy1 + 0.012, oy1 + 0.045, zw + t / 2 - 0.01,
            zw + t / 2 + 0.01, "SDT_Steel"),
        box("Chest_LidHandlePostB", cx + 0.095, cx + 0.105, oy1 + 0.012, oy1 + 0.045, zw + t / 2 - 0.01,
            zw + t / 2 + 0.01, "SDT_Steel"),
    ]
    for n, lx in enumerate((cx - 0.25, cx + 0.25)):
        lid.append(box(f"Chest_LatchTongue{n}", lx - 0.02, lx + 0.02, oy1 + 0.012, oy1 + 0.02, zw - 0.05, zw + t,
                       "SDT_Steel"))
    for n, lx in enumerate((cx - 0.28, cx + 0.28)):
        lid.append(tube(f"Chest_Hinge{n}", (lx - 0.05, hy, zw + 0.004), (lx + 0.05, hy, zw + 0.004), 0.014, "SDT_Steel",
                        segments=10))
    pivot = _group("chargerLid", vis, (cx, hy, zw))
    for o in lid:
        _set_parent(o, pivot, o.matrix_world.copy())
    pivot.rotation_euler.x = math.radians(CHEST_OPEN_DEG)
    bpy.context.view_layer.update()
    return pivot


def charger_cable_points():
    ox1, sy, sz = chest_box()[1], CHARGER_SOCKET_Y, TOP_SURF + CHARGER_SOCKET_Z
    gx, gy, gz = GEN_SOCKET
    lip_x = BASE_W / 2
    return [(ox1 + 0.05, sy, sz), (ox1 + 0.058, sy - 0.003, sz - 0.07), (ox1 + 0.06, sy - 0.01, TOP_SURF - 0.10),
            (lip_x + 0.022, sy - 0.02, TOP_SURF - 0.25),
            (lip_x + 0.024, sy + 0.01, 1.85), (lip_x + 0.022, sy + 0.07, 1.40), (lip_x + 0.012, gy - 0.10, 1.07),
            (lip_x - 0.03, gy - 0.04, 0.975), (gx + 0.12, gy - 0.01, 1.02), (gx + 0.075, gy, gz - 0.01),
            (gx + 0.045, gy, gz)]


def build_charger_cable():
    """Napájecí kabel truhla nabíječky → elektrocentrála: ze zásuvky na levé stěně truhly přes levou hranu horní desky,
    volně dolů vně rámu (za předním sloupkem) a prověšenou smyčkou k zásuvce na boku centrály. Zástrčky na obou
    koncích jsou jeho děti; animace foldLadder kabel při skládání skryje (viditelnost). Jen vizuál."""
    path = P.hermite_path(charger_cable_points(), samples=12)
    cable = P.sweep("chargerCable", path, CABLE_R, "SDT_HoseBlack", segments=10)
    ox1, sy, sz = chest_box()[1], CHARGER_SOCKET_Y, TOP_SURF + CHARGER_SOCKET_Z
    gx, gy, gz = GEN_SOCKET
    plugs = [
        tube("Charger_Plug", (ox1 + 0.02, sy, sz), (ox1 + 0.055, sy, sz), 0.018, "SDT_Rubber", segments=12,
             radius_end=0.012),
        tube("Gen_0_ChargePlug", (gx + 0.015, gy, gz), (gx + 0.05, gy, gz), 0.018, "SDT_Rubber", segments=12,
             radius_end=0.012),
    ]
    for o in plugs:
        _set_parent(o, cable, o.matrix_world.copy())
    return cable, P.path_length(path)


def build_drone_service_parts(prefix=DRONE_PREFIX):
    """Na trupu dronu: lůžko baterie (<prefix>BatterySlot) a plnicí hrdlo (<prefix>FillPort, +Z i3d míří do hrdla).

    Slot je posunutý tak, aby baterie jeho velikosti (rámec slotu = rámec M, viz P.battery) ležela na lůžku
    konektorem k zásuvce (-X) a uprostřed lůžka.
    """
    key, _ = drone_spec(prefix)
    tilt = bpy.data.objects[prefix + "Tilt"]
    body = bpy.data.objects[prefix + "Body"]
    top = max((body.matrix_world @ Vector(c)).z for c in body.bound_box)
    size = P.BATTERY_SIZES[key]
    lx, ly = size[0] / 2, size[1] / 2
    bx, by = DRONE_BATTERY[key]
    seat = top + 0.005
    # šachta v barvě trupu: baterie je celá uvnitř, nad okraj vystupuje jen víko (Pavel: „nemá z něj trčet“)
    wall = 0.012
    rim = seat + size[2] - 0.008
    x0, x1, y0, y1 = bx - lx - 0.006, bx + lx + 0.006, by - ly - 0.006, by + ly + 0.006
    parts = [
        box(f"{prefix}BatteryBay", x0, x1, y0, y1, top - 0.07, seat, "SDT_TankBlack"),
        box(f"{prefix}BatteryBayWallF", x0 - wall, x1 + wall, y0 - wall, y0, top - 0.07, rim, "Drone_White"),
        box(f"{prefix}BatteryBayWallR", x0 - wall, x1 + wall, y1, y1 + wall, top - 0.07, rim, "Drone_White"),
        box(f"{prefix}BatteryBayWallS", x0 - wall, x0, y0, y1, top - 0.07, rim, "Drone_White"),
        box(f"{prefix}BatteryBayWallC", x1, x1 + wall, y0, y1, top - 0.07, rim, "Drone_White"),
        box(f"{prefix}BatteryBayContacts", x0 + 0.002, x0 + 0.006, by - 0.05, by + 0.05, seat + 0.035, seat + 0.08,
            "SDT_Steel"),
    ]
    px, py = DRONE_FILL_PORT[key]
    port_top = top + 0.05
    parts += [
        cylinder_z(f"{prefix}FillPortNeck", (px, py, (top + port_top) / 2 - 0.015), 0.03, port_top - top + 0.01,
                   "SDT_TankBlack", segments=16),
        cylinder_z(f"{prefix}FillPortRing", (px, py, port_top - 0.006), 0.036, 0.012, "SDT_LampAmber", segments=16),
    ]
    for o in parts:
        _set_parent(o, tilt, o.matrix_world.copy())
    dx, dz = P.battery_frame_offset(size)
    _group(prefix + "BatterySlot", tilt, (bx - dx, by, seat - dz))
    i3d_rot_node(prefix + "FillPort", tilt, (px, py, port_top), (90, 0, 0))


def _aim(d):
    """Natočení, při kterém lokální -Y Blenderu (= +Z i3d) míří po d."""
    return d.normalized().to_track_quat("-Y", "Z").to_matrix().to_4x4()


def hose_lay_points():
    """Start, Lay1..Lay8 (Lay8 = špička koncovky v klidu) a směr koncovky."""
    d = Vector(HOSE_PARK_DIR).normalized()
    lay = [Vector(p) for p in HOSE_LAY]
    return Vector(HOSE_START), lay + [lay[-1] + d * NOZZLE_LEN], d


def hose_rest_path():
    start, lay, d = hose_lay_points()
    feed_dir = Vector(HOSE_START) - Vector(HOSE_FEED[-1])
    n = len(lay)
    return P.hermite_path([start] + lay, tangents={0: feed_dir, n - 1: d, n: d}, samples=16)


def build_hose_reel_parts():
    """Hadice namotaná na modrém bubnu (fillHoseCoil), pevný úsek z bubnu do vodítka na boku rámu a pevná trubka
    z osy navíječe do nádrže vleku."""
    rx, ry, rz = REEL
    turns = 0.16 / (2 * HOSE_R)
    steps = int(turns * 32)
    x_in, x_out = rx + 0.08, rx - 0.08
    coil = []
    for k in range(steps + 1):
        s = k / steps
        a = math.pi / 2 + (1 - s) * turns * 2 * math.pi
        coil.append(Vector((x_in + (x_out - x_in) * s, ry + HOSE_COIL_R * math.sin(a), rz + HOSE_COIL_R * math.cos(a))))
    P.sweep("fillHoseCoil", coil, HOSE_R, "SDT_HoseBlack", segments=10)

    start = Vector(HOSE_START)
    feed = HOSE_FEED + [HOSE_START]
    P.sweep("HoseReel_0_Feed", P.hermite_path(feed, tangents={0: (0, 0, 1), len(feed) - 1: start - Vector(HOSE_FEED[-1])},
                                              samples=10), HOSE_R, "SDT_HoseBlack", segments=10)
    gx, gy, gz = start.x, start.y, start.z
    g = HOSE_R + 0.013
    for dy in (-g, g):
        tube(f"HoseGuide_RollerV{dy:+.2f}", (gx, gy + dy, gz - g - 0.01), (gx, gy + dy, gz + g + 0.01), 0.01, "SDT_Steel",
             segments=8)
    for dz in (-g, g):
        tube(f"HoseGuide_RollerH{dz:+.2f}", (gx, gy - g - 0.01, gz + dz), (gx, gy + g + 0.01, gz + dz), 0.01, "SDT_Steel",
             segments=8)
    for n, (ya, yb) in enumerate(((gy - g - 0.03, gy - g - 0.012), (gy + g + 0.012, gy + g + 0.03))):
        box(f"HoseGuide_Plate{n}", gx - 0.012, gx + 0.012, ya, yb, gz - g - 0.02, POST_TOP, "SDT_Frame")
        box(f"HoseGuide_Arm{n}", gx - 0.012, -POST_X + 0.03, ya, yb, POST_TOP - 0.025, POST_TOP, "SDT_Frame")

    cylinder_x("HoseReel_0_Swivel", (rx + 0.16, ry, rz), 0.03, 0.05, "SDT_Steel", segments=16)
    build_plumbing()


def build_plumbing():
    """Rozvod: výpust vpředu dole na hlavní nádrži a výpust indukční nádrže (ze zadní stěny stojanu) do T-kusu,
    z něj do sání čerpadla (osově na tělese), výtlak nahoře na tělese čerpadla nad indukční nádrží do otočné spojky
    navíječe. Poloha čerpadla a nádrží viz build_equipment / P.pump / P.cone_tank."""
    z = DECK_TOP
    rx, ry, rz = REEL
    pipe_r = 0.025
    px, py = -0.55, -0.55
    hx, hz = px + 0.22 + 0.09, z + 0.42                  # vnější čelo tělesa čerpadla, osa
    tee = Vector((hx + 0.11, py, hz))
    tube("Pump_Inlet", (hx - 0.01, py, hz), (tee.x, py, hz), pipe_r + 0.004, "SDT_Steel", segments=16)
    cylinder_z("Pump_Tee", tuple(tee), 0.035, 0.08, "SDT_Steel", segments=16)
    tube("Pump_TeeRun", (tee.x, py - 0.06, hz), (tee.x, py + 0.06, hz), 0.032, "SDT_Steel", segments=16)

    c = Vector((0.0, TANK_Y - TANK_LEN / 2 + TANK_R, DECK_TOP + 0.12 + TANK_R))
    n = Vector((-0.35, -0.75, -0.55)).normalized()
    surf = c + n * TANK_R
    tube("Tank_Main_Outlet", surf - n * 0.01, surf + n * 0.045, 0.032, "SDT_Steel", segments=16)
    a = surf + n * 0.045
    b = Vector((tee.x, py + 0.06, hz))
    P.sweep("Pump_Suction", P.hermite_path([a, b], tangents={0: n, 1: (0, -1, 0)}, samples=10), pipe_r,
            "SDT_HoseBlack", segments=12)

    iy, half = -1.25, 0.28
    ind = Vector((-0.33, iy + half, z + 0.28))
    tube("Tank_Induction_Outlet", ind - Vector((0, 0.01, 0)), ind + Vector((0, 0.04, 0)), 0.03, "SDT_Steel",
         segments=16)
    a = ind + Vector((0, 0.04, 0))
    b = Vector((tee.x, py - 0.06, hz))
    P.sweep("Tank_Induction_Pipe", P.hermite_path([a, b], tangents={0: (0, 1, 0), 1: (0, 1, 0)}, samples=10), pipe_r,
            "SDT_HoseBlack", segments=12)

    top = Vector((px + 0.22, py, hz + 0.14))
    tube("Pump_Outlet", top - Vector((0, 0, 0.02)), top + Vector((0, 0, 0.05)), pipe_r + 0.004, "SDT_Steel",
         segments=16)
    pipe = [top + Vector((0, 0, 0.05)), (-0.30, -0.80, 1.90), (-0.34, -1.25, 2.10), (-0.46, -1.68, 2.06),
            (rx + 0.185, ry, rz)]
    P.sweep("Pump_Discharge", P.hermite_path(pipe, tangents={0: (0, 0, 1), len(pipe) - 1: (-1, 0, 0)}, samples=10),
            pipe_r, "SDT_HoseBlack", segments=12)


def build_fill_hose():
    """Plnicí hadice z modrého navíječe (kontrakt kola 2).

    fillHoseStart = výstup z vodítka na boku rámu pod pravou hranou horní desky; fillHoseLay1..8 = body volně
    položené hadice (Lay1 visí přes bok, Lay2 přes lem, Lay3..8 leží na desce, Lay8 = špička koncovky v klidu
    = fillHoseParkPos). fillHoseSeg1..24 = válce délky 1 m po +Z i3d s počátkem na začátku, v i3d rozložené po
    klidové křivce (natažené měřítkem z na délku tětivy + HOSE_R·tan(úhel ohybu / 2), aby v ohybu nebyla vidět
    mezera). Koncovka má počátek ve špičce a +Z i3d míří ze špičky ven.
    """
    vis = bpy.data.objects[ROOT_NAME]
    build_hose_reel_parts()
    hose = _group("fillHose", vis)
    start, lay, d = hose_lay_points()
    _group("fillHoseStart", hose, tuple(start))
    for i, p in enumerate(lay, 1):
        _group(f"fillHoseLay{i}", hose, tuple(p))
    pts = P.resample(hose_rest_path(), HOSE_SEGMENTS)
    for i in range(HOSE_SEGMENTS):
        a, b = pts[i], pts[i + 1]
        bend = (b - a).angle(pts[i + 2] - b) if i + 2 < len(pts) else 0.0
        length = (b - a).length + HOSE_R * math.tan(bend / 2)
        seg = tube(f"fillHoseSeg{i + 1}", (0, 0, 0), (0, -1, 0), HOSE_R, "SDT_HoseBlack", segments=12)
        seg.data.transform(seg.matrix_basis)
        seg.matrix_world = Matrix.Identity(4)
        _set_parent(seg, hose, Matrix.Translation(a) @ _aim(b - a) @ Matrix.Diagonal((1, length, 1, 1)))

    tip = [
        tube("HoseNozzle_Tip", (0, -0.004, 0), (0, 0.06, 0), HOSE_R + 0.003, "SDT_Steel", segments=12),
        tube("HoseNozzle_Grip", (0, 0.06, 0), (0, 0.17, 0), 0.027, "SDT_TankBlack", segments=12),
        tube("HoseNozzle_Coupling", (0, 0.17, 0), (0, NOZZLE_LEN, 0), 0.03, "SDT_Steel", segments=12),
        box("HoseNozzle_Lever", -0.008, 0.008, 0.07, 0.15, 0.026, 0.045, "SDT_LampAmber"),
    ]
    park = Matrix.Translation(lay[-1]) @ _aim(d)
    _set_parent(P.group("fillHoseNozzle", tip), hose, park)
    _set_parent(_group("fillHoseParkPos", hose), hose, park)


def _physics(obj, **props):
    for k, v in props.items():
        obj["i3D_" + k] = v
    return obj


def _shape_box(name, parent, x0, x1, y0, y1, z0, z1, group_mask, **props):
    """Neviditelný kolizní/spouštěcí kvádr s počátkem v rodiči (vrcholy leží přímo na místě)."""
    return _as_shape(box(name, x0, x1, y0, y1, z0, z1, "SDT_Frame"), parent, group_mask, **props)


def _as_shape(obj, parent, group_mask, **props):
    world = obj.matrix_world.copy()
    obj.data.transform(world)
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = parent.matrix_world.copy() if parent else Matrix.Identity(4)
    obj.data.transform(obj.matrix_world.inverted())
    obj.display_type = "WIRE"
    obj.hide_render = True
    return _physics(obj, collisionFilterGroup=str(group_mask[0]), collisionFilterMask=str(group_mask[1]),
                    nonRenderable=True, **props)


_TO_I3D = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))


def i3d_rot_node(name, parent, loc, rot_i3d_deg):
    """Prázdný uzel, který po exportu (BAKE_TRANSFORMS: M_i3d = A @ M @ A^-1) dostane dané i3d natočení."""
    r = Euler([math.radians(a) for a in rot_i3d_deg], "XYZ").to_matrix().to_4x4()
    node = _group(name, parent, loc)
    node.matrix_world = Matrix.Translation(loc) @ (_TO_I3D.inverted() @ r @ _TO_I3D)
    return node


def _group(name, parent, loc=(0, 0, 0)):
    g = empty(name, loc)
    g.parent = parent
    g.matrix_parent_inverse = Matrix.Identity(4)
    g.matrix_world = Matrix.Translation(loc)
    return g


def build_i3d_structure(vis):
    """Uspořádání pro FS25 podle vanilla ABI Water Trailer 550: kolizní komponenta jako kořen."""
    rail_z0 = DECK_TOP - RAIL_H
    comp = _shape_box(COMPONENT_NAME, None, -BASE_W / 2, BASE_W / 2, BASE_Y0, BASE_Y1, rail_z0, DECK_TOP,
                      COL_VEHICLE, dynamic=True, compound=True)
    vis.parent = comp
    vis.matrix_parent_inverse = Matrix.Identity(4)

    cols = _group("collisions", comp)
    child = dict(compoundChild=True, density=0.001)
    _shape_box("colTopDeck", cols, -TOP_W / 2, TOP_W / 2, TOP_Y0, TOP_Y1, POST_TOP, TOP_SURF, COL_VEHICLE, **child)
    _shape_box("colTank", cols, -TANK_R, TANK_R, TANK_Y - TANK_LEN / 2, TANK_Y + TANK_LEN / 2, DECK_TOP,
               DECK_TOP + 0.12 + 2 * TANK_R, COL_VEHICLE, **child)
    _shape_box("colEquipmentFront", cols, -BASE_W / 2 + 0.1, BASE_W / 2 - 0.1, BASE_Y0 + 0.1, -0.30, DECK_TOP,
               DECK_TOP + 1.0, COL_VEHICLE, **child)
    _shape_box("colDrawbar", cols, -0.12, 0.12, COUPLER_Y + 0.20, BASE_Y0, COUPLER_Z - 0.05, COUPLER_Z + 0.08,
               COL_VEHICLE, **child)

    wheels = _group("wheels", vis)
    for ay, pos in zip(AXLE_Y, ("Front", "Back")):
        for sx, side in ((1, "Left"), (-1, "Right")):
            _group(f"wheel{pos}{side}", wheels, (sx * TRACK_X, ay, WHEEL_R))

    fill = _group("fill", vis)
    # fillTrigger: postřikovač zajetý vedle vleku se z něj může dočerpat (fillTriggerVehicle)
    _shape_box("fillTrigger", fill, -BASE_W / 2 - 0.3, BASE_W / 2 + 0.3, BASE_Y0 - 0.3, BASE_Y1 + 0.3, 0.0,
               DECK_TOP + 1.2, COL_TRIGGER, kinematic=True, compound=True, trigger=True)
    # exactFillRootNode: tady vlek "vidí" plnicí stanice a palety s hnojivem/herbicidem
    _shape_box("exactFillRootNode", fill, -TANK_R, TANK_R, TANK_Y - TANK_LEN / 2, TANK_Y + TANK_LEN / 2,
               DECK_TOP + 0.12, DECK_TOP + 0.12 + 2 * TANK_R, COL_FILL_ROOT, kinematic=True, compound=True)
    # nádrž elektrocentrály: čerpací stanice a nádrž na naftu plní přes loadTrigger, který hledá exactFillRootNode
    gx, gy = GEN_POS
    _shape_box("dieselFillRootNode", fill, gx - 0.33, gx + 0.33, gy - 0.40, gy + 0.40, DECK_TOP + 0.05, DECK_TOP + 0.72,
               COL_FILL_ROOT, kinematic=True, compound=True)

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
    cam.matrix_world = Matrix.Translation(Vector(CAMERA_TARGET) + Vector((0, 8, 3)))

    occ = _group("tipOccluder", vis)
    _group("occlusionAreaStart", occ, (0.9, BASE_Y0, 0))
    _group("occlusionAreaWidth", occ, (-0.9, BASE_Y0, 0))
    _group("occlusionAreaHeight", occ, (0.9, BASE_Y1, 0))

    plate = _group("licensePlateBack", vis, (0, BASE_Y1 + 0.001, rail_z0 - 0.07))
    plate.rotation_euler = (0, 0, math.radians(180))
    return comp


def build_decals():
    """Nálepky vleku z atlasu (decal_layout.py): výstražné pruhy vpředu a vzadu na horní plošině a na zadním nosníku,
    nápis na bocích horní plošiny, štítek nafty na elektrocentrále. Tenké čtyřúhelníky 1,5 mm nad povrchem."""
    ty = TOP_Y0 + 0.005
    z0, h = POST_TOP + 0.01, TOP_BEAM_H - 0.02
    w = 2 * (POST_X - POST / 2)
    P.decal_quad("Decal_StripeFront", (-w / 2, ty, z0), (1, 0, 0), (0, 0, 1), w, h, "stripe")
    P.decal_quad("Decal_StripeRear", (w / 2, -ty, z0), (-1, 0, 0), (0, 0, 1), w, h, "stripe")
    rz0, rh, rw = DECK_TOP - RAIL_H + 0.03, 0.12, 0.40
    sub = (0.0, 0.0, rw / rh / 16.0, 1.0)
    P.decal_quad("Decal_StripeRearL", (0.70, BASE_Y1, rz0), (-1, 0, 0), (0, 0, 1), rw, rh, "stripe", sub)
    P.decal_quad("Decal_StripeRearR", (-0.30, BASE_Y1, rz0), (-1, 0, 0), (0, 0, 1), rw, rh, "stripe", sub)
    bx = POST_X + POST / 2
    tz, th, tl = POST_TOP + 0.015, 0.09, 1.40
    P.decal_quad("Decal_SideL", (bx, -1.25, tz), (0, 1, 0), (0, 0, 1), tl, th, "sideText")
    P.decal_quad("Decal_SideR", (-bx, -1.25 + tl, tz), (0, -1, 0), (0, 0, 1), tl, th, "sideText")
    gx, gy = GEN_POS
    P.decal_quad("Decal_Diesel", (gx + 0.33, -1.35, DECK_TOP + 0.12), (0, 1, 0), (0, 0, 1), 0.30, 0.20, "dieselLabel")


def build_drone_decals(prefix=DRONE_PREFIX):
    """Označení na obou bocích trupu dronu (pod barevným pásem), přitisknuté na zakřivený trup."""
    key, spec = drone_spec(prefix)
    bpy.context.view_layer.update()
    body = bpy.data.objects[prefix + "Body"]
    tilt = bpy.data.objects[prefix + "Tilt"]
    pts = [body.matrix_world @ Vector(c) for c in body.bound_box]
    c = sum(pts, Vector()) / 8
    half_x = (max(p.x for p in pts) - min(p.x for p in pts)) / 2
    width = 0.4 * spec["body"][0]
    zc = c.z - 0.2 * spec["body"][2]
    for side, sx in (("L", 1), ("R", -1)):
        d = P.conform_decal(f"{prefix}Decal_{side}", body, (c.x + sx * half_x, c.y, zc), (sx, 0, 0), (0, 0, 1),
                            width, width / 4, "drone" + key)
        _set_parent(d, tilt, d.matrix_world.copy())


VMASK_EXCLUDE_MATERIALS = ("SDT_NavLed",)
DRONE_MATERIAL_SUFFIX = "__D"


def dirt_atlas(obj):
    """Do které vmask patří mesh: 'drone' (trup, ramena, lůžko baterie, nálepky dronu), jinak 'trailer'."""
    if obj.name.startswith(tuple(DRONE_VARIANTS.values())) and "Clamp" not in obj.name:
        return "drone"
    return "trailer"


def dirt_meshes():
    colls = [bpy.data.collections[COLLECTION_NAME], bpy.data.collections[DRONE_COLLECTION]]
    out = []
    for coll in colls:
        for o in coll.objects:
            if o.type != "MESH" or o.get("i3D_nonRenderable"):
                continue
            if any(m and m.name.split(DRONE_MATERIAL_SUFFIX)[0] in VMASK_EXCLUDE_MATERIALS for m in o.data.materials):
                continue
            out.append(o)
    return out


def _ensure_uv0(obj):
    """První UV vrstva: krabicová projekce (u meshů bez UV), posunutá do kladných hodnot (mokrost ve vehicleShaderu
    chce UV0 s y > 0); nálepky mají UV0 v atlasu a nechají se."""
    me = obj.data
    if not me.uv_layers:
        bm = bmesh.new()
        bm.from_mesh(me)
        P._box_uv(bm)
        bm.to_mesh(me)
        bm.free()
    uv = me.uv_layers[0]
    uv.name = "UVMap"
    decal = {i for i, m in enumerate(me.materials) if m and m.name.split(DRONE_MATERIAL_SUFFIX)[0] in P.DECAL_MATERIALS}
    for poly in me.polygons:
        if poly.material_index in decal:
            continue
        for li in poly.loop_indices:
            u, v = uv.data[li].uv
            uv.data[li].uv = (u + 8.0, v + 8.0)


def _drone_materials(obj):
    me = obj.data
    for i, m in enumerate(me.materials):
        if m is None or m.name.endswith(DRONE_MATERIAL_SUFFIX):
            continue
        copy = bpy.data.materials.get(m.name + DRONE_MATERIAL_SUFFIX)
        if copy is None:
            copy = m.copy()
            copy.name = m.name + DRONE_MATERIAL_SUFFIX
        # konvertor exportéru slučuje materiály se stejnými hodnotami, kopie se proto musí nepatrně lišit
        c = list(m.diffuse_color)
        c[3] = 0.99
        copy.diffuse_color = c
        bsdf = next((n for n in copy.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if copy.node_tree else None
        if bsdf is not None:
            r = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Roughness"].default_value
            bsdf.inputs["Roughness"].default_value = min(r + 0.01, 1.0)
        me.materials[i] = copy


def build_dirt_uvs():
    """Druhá UV vrstva 'DirtUV' pro vmask (špína v modrém, škrábance v červeném, AO v zeleném kanálu, vehicleShader
    varianta vmaskUV2): jedna společná rozvinutá plocha 0..1 pro celý vlek a jedna pro všechny tři drony
    (smart UV project všech meshů naráz). Meshe dronu dostanou vlastní kopie materiálů (__D), protože vmask je
    vlastnost materiálu."""
    meshes = dirt_meshes()
    groups = {"trailer": [], "drone": []}
    for o in meshes:
        _ensure_uv0(o)
        if dirt_atlas(o) == "drone":
            _drone_materials(o)
        me = o.data
        while len(me.uv_layers) > 1:
            me.uv_layers.remove(me.uv_layers[1])
        me.uv_layers.new(name="DirtUV")
        me.uv_layers.active_index = 1
        groups[dirt_atlas(o)].append(o)
    for name, objs in groups.items():
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in objs:
            o.hide_set(False)
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
        bpy.ops.object.mode_set(mode="OBJECT")
        print(f"DirtUV {name}: {len(objs)} meshů")
    for o in meshes:
        o.data.uv_layers.active_index = 0
        o.select_set(False)
    return groups


def move_to_preview(prefixes):
    """Modelovaná kola hra nepoužije (generuje je z rozměru pneu), v Blenderu zůstanou jako náhled."""
    prev = bpy.data.collections.get(PREVIEW_COLLECTION)
    if prev:
        for o in list(prev.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        prev = bpy.data.collections.new(PREVIEW_COLLECTION)
        bpy.context.scene.collection.children.link(prev)
    coll = bpy.data.collections[COLLECTION_NAME]
    for o in [o for o in coll.objects if o.name.startswith(prefixes)]:
        world = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = world
        coll.objects.unlink(o)
        prev.objects.link(o)


def build():
    coll, vis = P.begin(COLLECTION_NAME, ROOT_NAME)
    build_chassis()
    build_drawbar()
    build_upper_structure()
    build_ladder_collision(build_ladder())
    build_equipment()
    build_i3d_structure(vis)
    move_to_preview(("Wheel_", "Rim_"))
    build_drones()
    for prefix in DRONE_VARIANTS.values():
        place_drone(prefix)
        build_drone_leds(prefix)
        build_drone_clamps(prefix)
    build_heliport()
    build_batteries()
    build_charger()
    build_charger_chest()
    build_charger_cable()
    for prefix in DRONE_VARIANTS.values():
        build_drone_service_parts(prefix)
        build_drone_decals(prefix)
    build_fill_hose()
    build_decals()
    bpy.context.view_layer.update()
    build_dirt_uvs()
    print(f"{COLLECTION_NAME}: {len(coll.objects)} objektů")


if __name__ == "__main__":
    build()
