"""Servisní vlek pro postřikové drony, velká verze za pickup (husí krk), dva drony.

Předloha: nuWay Ag "Spray Ready" gooseneck (22 ft deckover + 32 ft letová plošina nahoře),
fotky v reference/. Podvozek porovnaný s vanilla FS25 Kingston Belvedere (jediný gooseneck
přívěs ve hře), importovaným do kolekce REF_Belvedere. Schváleno Pavlem 2026-09-27.

Osa: přední část (čep husího krku) je na -Y, stejně jako u vanilla vozidel po importu.
Počátek = zem, střed šířky, střed spodní paluby. Každý díl má měřítko 1 a vlastní počátek.

Spuštění v Blenderu:
    p = r"...\\build_trailer3.py"; exec(open(p, encoding="utf-8").read(), {"__file__": p, "__name__": "__main__"})
"""

import importlib
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdt_parts as P  # noqa: E402

importlib.reload(P)

COLLECTION_NAME = "SprayDroneTrailer3"
ROOT_NAME = "SDT3_Root"

# --- spodek: 22 ft deckover ---
BASE_LEN = 6.71
BASE_W = 2.59
BASE_Y0 = -BASE_LEN / 2          # přední hrana spodní paluby
BASE_Y1 = BASE_LEN / 2           # zadní hrana
DECK_TOP = 0.95                  # horní plocha spodní paluby (deckover = nad koly)
DECK_PLATE = 0.04
RAIL_H = 0.25                    # boční C-profil rámu
RAIL_W = 0.08
IBEAM_X = 0.45
IBEAM_H = 0.30

# --- podvozek (srovnáno s Belvedere: rozchod 2,34, rozteč 0,88, čep 0,93 nad zemí) ---
WHEEL_R = 0.40                   # 235/85 R16, 16-ply
WHEEL_W = 0.23
TRACK_X = 1.05
AXLE_Y = [1.35, 2.25]

# --- husí krk ---
NECK_BOTTOM = 1.30
NECK_TOP = 1.55
NECK_Y0 = -5.20
COUPLER_Y = -5.05
COUPLER_Z = 0.93

# --- horní letová plošina: 32 ft ---
TOP_SURF = 3.00
TOP_PLATE = 0.05
TOP_BEAM_H = 0.15
TOP_Y0 = BASE_Y0 - 2.44          # přesah dopředu nad husí krk (pilotní prostor)
TOP_Y1 = BASE_Y1 + 0.60
TOP_W = BASE_W
POST = 0.10
POST_X = TOP_W / 2 - POST / 2
POST_Y = [BASE_Y0 + 0.10, -1.20, 0.90, BASE_Y1 - 0.10]
POST_TOP = TOP_SURF - TOP_PLATE - TOP_BEAM_H
GUSSET = 1.00

# --- schody (levý bok = +X při pohledu po směru jízdy -Y) a otvor v plošině ---
STAIR_X = (0.50, 1.15)
STAIR_Y_BOTTOM = -1.60
STAIR_Y_TOP = BASE_Y0
HOLE_Y = (BASE_Y0, -2.05)
HOLE_X = (0.45, 1.20)

RAIL_HEIGHT = 1.07
PILOT_Y1 = TOP_Y0 + 1.60         # konec pilotního prostoru se zábradlím

DRONE_Y = [-0.55, 2.35]

box, tube, plate_yz, cylinder_x, cylinder_z, capsule, empty = (
    P.box, P.tube, P.plate_yz, P.cylinder_x, P.cylinder_z, P.capsule, P.empty)


def build_chassis():
    rail_z0 = DECK_TOP - RAIL_H
    for side, sx in (("L", 1), ("R", -1)):
        x_out = sx * BASE_W / 2
        box(f"Rail_{side}", x_out, x_out - sx * RAIL_W, BASE_Y0, BASE_Y1, rail_z0, DECK_TOP, "SDT_Frame")
        box(f"IBeam_{side}", sx * IBEAM_X - 0.05, sx * IBEAM_X + 0.05, BASE_Y0, BASE_Y1,
            DECK_TOP - DECK_PLATE - IBEAM_H, DECK_TOP - DECK_PLATE, "SDT_Frame")
        P.reflective_tape(f"Tape_{side}", x_out, sx, BASE_Y0 + 0.05, BASE_Y1 - 0.05, rail_z0 + 0.08, rail_z0 + 0.16)
    box("Deck", -BASE_W / 2 + RAIL_W, BASE_W / 2 - RAIL_W, BASE_Y0, BASE_Y1,
        DECK_TOP - DECK_PLATE, DECK_TOP - 0.005, "SDT_DeckWood")
    box("RearBeam", -BASE_W / 2, BASE_W / 2, BASE_Y1 - 0.10, BASE_Y1, DECK_TOP - RAIL_H, DECK_TOP, "SDT_Frame")
    for side, sx in (("L", 1), ("R", -1)):
        box(f"TailLight_{side}", sx * 1.00, sx * 1.20, BASE_Y1, BASE_Y1 + 0.02, 0.76, 0.84, "SDT_LampRed")

    for i, ay in enumerate(AXLE_Y, 1):
        tube(f"Axle_{i}", (-TRACK_X, ay, WHEEL_R), (TRACK_X, ay, WHEEL_R), 0.045, "SDT_Frame")
        for side, sx in (("L", 1), ("R", -1)):
            cylinder_x(f"Wheel_{i}{side}", (sx * TRACK_X, ay, WHEEL_R), WHEEL_R, WHEEL_W, "SDT_Rubber", segments=32)
            cylinder_x(f"Rim_{i}{side}", (sx * (TRACK_X + 0.005), ay, WHEEL_R), 0.21, WHEEL_W + 0.004, "SDT_Rim")
            box(f"Spring_{i}{side}", sx * IBEAM_X - 0.04, sx * IBEAM_X + 0.04, ay - 0.55, ay + 0.55,
                WHEEL_R + 0.04, WHEEL_R + 0.10, "SDT_Steel")
            box(f"Hanger_{i}{side}", sx * IBEAM_X - 0.03, sx * IBEAM_X + 0.03, ay - 0.04, ay + 0.04,
                WHEEL_R + 0.10, DECK_TOP - DECK_PLATE - IBEAM_H, "SDT_Frame")


def build_gooseneck():
    box("Neck_Riser", -0.40, 0.40, BASE_Y0, BASE_Y0 + 0.35, DECK_TOP, NECK_TOP, "SDT_Frame")
    for side, sx in (("L", 1), ("R", -1)):
        box(f"Neck_Beam_{side}", sx * 0.22, sx * 0.34, NECK_Y0, BASE_Y0 + 0.35, NECK_BOTTOM, NECK_TOP, "SDT_Frame")
        box(f"Neck_Brace_{side}", sx * 0.22, sx * 0.34, BASE_Y0 - 0.02, BASE_Y0 + 0.35,
            DECK_TOP - IBEAM_H, NECK_BOTTOM, "SDT_Frame")
    box("Neck_TopPlate", -0.36, 0.36, NECK_Y0, BASE_Y0 + 0.35, NECK_TOP - 0.02, NECK_TOP + 0.005, "SDT_Frame")
    box("Neck_FrontPlate", -0.34, 0.34, NECK_Y0, NECK_Y0 + 0.02, NECK_BOTTOM, NECK_TOP, "SDT_Frame")
    tube("Coupler", (0, COUPLER_Y, COUPLER_Z), (0, COUPLER_Y, NECK_BOTTOM), 0.06, "SDT_Steel", segments=16)
    tube("Coupler_Sleeve", (0, COUPLER_Y, COUPLER_Z + 0.12), (0, COUPLER_Y, NECK_BOTTOM), 0.08, "SDT_Frame",
         segments=16)
    box("Toolbox", -1.20, -0.45, BASE_Y0 + 0.02, BASE_Y0 + 0.52, DECK_TOP, DECK_TOP + 0.50, "SDT_Mesh")
    for side, sx in (("L", 1), ("R", -1)):
        x = sx * 0.50
        y = BASE_Y0 - 0.12
        box(f"JackMount_{side}", sx * 0.34, sx * 0.56, y - 0.06, y + 0.06, NECK_BOTTOM - 0.06, NECK_BOTTOM + 0.04,
            "SDT_Frame")
        tube(f"Jack_{side}", (x, y, 0.35), (x, y, NECK_BOTTOM + 0.05), 0.055, "SDT_Frame", segments=12)
        tube(f"JackRod_{side}", (x, y, 0.03), (x, y, 0.36), 0.03, "SDT_Steel", segments=12)
        cylinder_z(f"JackFoot_{side}", (x, y, 0.015), 0.12, 0.03, "SDT_Frame", segments=16)
    empty("attacherJoint", (0, COUPLER_Y, COUPLER_Z))


def build_upper_structure():
    for side, sx in (("L", 1), ("R", -1)):
        px = sx * POST_X
        for i, py in enumerate(POST_Y):
            box(f"Post_{side}{i}", px - POST / 2, px + POST / 2, py - POST / 2, py + POST / 2,
                DECK_TOP, POST_TOP, "SDT_Frame")
        # V výztuhy na krajních sloupcích, velká výztuha dopředu nese přesah nad husím krkem
        yf, yr = POST_Y[0], POST_Y[-1]
        plate_yz(f"Gusset_{side}_Front", px, 0.02,
                 [(yf, POST_TOP - GUSSET), (yf, POST_TOP), (yf - 1.6, POST_TOP)], "SDT_Frame")
        plate_yz(f"Gusset_{side}_FrontIn", px, 0.02,
                 [(yf, POST_TOP - 0.6), (yf + 0.6, POST_TOP), (yf, POST_TOP)], "SDT_Frame")
        plate_yz(f"Gusset_{side}_Rear", px, 0.02,
                 [(yr, POST_TOP - GUSSET * 0.7), (yr + 0.6, POST_TOP), (yr, POST_TOP)], "SDT_Frame")
        plate_yz(f"Gusset_{side}_RearIn", px, 0.02,
                 [(yr, POST_TOP - 0.6), (yr, POST_TOP), (yr - 0.6, POST_TOP)], "SDT_Frame")
        for i, py in enumerate(POST_Y[1:-1], 1):
            plate_yz(f"Knee_{side}{i}", px, 0.02,
                     [(py - 0.35, POST_TOP), (py, POST_TOP - 0.35), (py + 0.35, POST_TOP)], "SDT_Frame")
        box(f"TopBeam_{side}", px - POST / 2, px + POST / 2, TOP_Y0, TOP_Y1,
            POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
    for i, py in enumerate([TOP_Y0 + 0.05] + POST_Y + [TOP_Y1 - 0.05]):
        if HOLE_Y[0] <= py <= HOLE_Y[1]:
            # příčník v místě otvoru pro schody je přerušený, jinak by jím schodiště procházelo
            box(f"TopCross_{i}a", -POST_X, HOLE_X[0], py - 0.04, py + 0.04, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
            box(f"TopCross_{i}b", HOLE_X[1], POST_X, py - 0.04, py + 0.04, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
        else:
            box(f"TopCross_{i}", -POST_X, POST_X, py - 0.04, py + 0.04, POST_TOP, POST_TOP + TOP_BEAM_H, "SDT_Frame")
    box("TopCross_HoleRear", HOLE_X[0], HOLE_X[1], HOLE_Y[1] - 0.04, HOLE_Y[1] + 0.04, POST_TOP,
        POST_TOP + TOP_BEAM_H, "SDT_Frame")

    z0, z1 = TOP_SURF - TOP_PLATE, TOP_SURF
    hw = TOP_W / 2
    box("TopDeck_Main", -hw, hw, HOLE_Y[1], TOP_Y1, z0, z1, "SDT_TopDeck")
    box("TopDeck_Front", -hw, hw, TOP_Y0, HOLE_Y[0], z0, z1, "SDT_TopDeck")
    box("TopDeck_Strip_R", -hw, HOLE_X[0], HOLE_Y[0], HOLE_Y[1], z0, z1, "SDT_TopDeck")
    box("TopDeck_Strip_L", HOLE_X[1], hw, HOLE_Y[0], HOLE_Y[1], z0, z1, "SDT_TopDeck")
    for side, sx in (("L", 1), ("R", -1)):
        box(f"TopLip_{side}", sx * hw - sx * 0.04, sx * hw, TOP_Y0, TOP_Y1, z1, z1 + 0.05, "SDT_Frame")


def build_railings_and_stairs():
    hw = TOP_W / 2 - 0.05
    # pilotní prostor vpředu: zábradlí na třech stranách + síťová stěna
    P.railing("PilotRail", [(-hw, PILOT_Y1), (-hw, TOP_Y0 + 0.05), (hw, TOP_Y0 + 0.05), (hw, PILOT_Y1)],
              TOP_SURF, RAIL_HEIGHT)
    box("PilotMesh", -hw + 0.03, hw - 0.03, TOP_Y0 + 0.04, TOP_Y0 + 0.055, TOP_SURF + 0.10,
        TOP_SURF + RAIL_HEIGHT - 0.05, "SDT_Mesh")
    box("PilotLightBar", -0.35, 0.35, TOP_Y0 + 0.03, TOP_Y0 + 0.10, TOP_SURF + RAIL_HEIGHT + 0.03,
        TOP_SURF + RAIL_HEIGHT + 0.10, "SDT_LampAmber")
    P.railing("HoleRail", [(HOLE_X[0] - 0.03, HOLE_Y[0] + 0.05), (HOLE_X[0] - 0.03, HOLE_Y[1] + 0.03),
                           (HOLE_X[1], HOLE_Y[1] + 0.03)], TOP_SURF, RAIL_HEIGHT, post_every=0.7)

    bottom = Vector((0, STAIR_Y_BOTTOM, DECK_TOP))
    top = Vector((0, STAIR_Y_TOP, TOP_SURF))
    for side, x in (("In", STAIR_X[0]), ("Out", STAIR_X[1])):
        tube(f"Stair_Stringer_{side}", (x, bottom.y, bottom.z), (x, top.y, top.z), 0.035, "SDT_Frame", segments=8)
        # madlo rovnoběžně se schodnicí, nahoře končí svislým sloupkem na plošině
        tube(f"Stair_Hand_{side}", (x, bottom.y, bottom.z + 0.9), (x, top.y, top.z + 0.9), 0.02,
             "SDT_Frame", segments=10)
        tube(f"Stair_HandPost_{side}", (x, bottom.y, bottom.z), (x, bottom.y, bottom.z + 0.9), 0.02,
             "SDT_Frame", segments=10)
        tube(f"Stair_HandPostTop_{side}", (x, top.y - 0.02, top.z), (x, top.y - 0.02, top.z + 0.9), 0.02,
             "SDT_Frame", segments=10)
    rise = TOP_SURF - DECK_TOP
    steps = round(rise / 0.24)
    for i in range(1, steps):
        p = bottom.lerp(top, i / steps)
        box(f"Stair_Step_{i:02d}", STAIR_X[0] + 0.03, STAIR_X[1] - 0.03, p.y - 0.12, p.y + 0.12,
            p.z - 0.03, p.z, "SDT_Mesh")


def build_equipment():
    z = DECK_TOP
    tank_r, tank_len, tank_y = 0.74, 2.45, 1.95       # 1000 gal hlavní nádrž vzadu
    P.leg_tank("Tank_Main", tank_y, z, tank_r, tank_len, (-0.75, -0.25, 0.25, 0.75), (-0.8, 0.8), 0.55)
    ix, iy = -0.62, -0.40                             # 175 gal indukční
    P.cone_tank("Tank_Induction", ix, iy, z, 0.48)
    capsule("Tank_Fresh", (-0.72, -2.35, z + 0.30), 0.28, 0.95, "Y", "SDT_TankWhite")  # 50 gal čistá voda
    px, py = -0.55, 0.55
    P.pump("Pump", px, py, z)
    tube("Pump_Suction", (px + 0.22, py + 0.14, z + 0.42), (px + 0.22, tank_y - tank_len / 2 + 0.2, z + 0.25),
         0.03, "SDT_HoseBlack")
    tube("Pump_Discharge", (px + 0.30, py, z + 0.55), (ix + 0.2, iy + 0.3, z + 1.55), 0.03, "SDT_HoseBlack")
    # generátory vedle schodů, ne pod nimi: pod strmým schodištěm není 0,8 m světlé výšky
    for i, gy in enumerate((-2.55, -1.62)):
        P.generator(f"Gen_{i}", 0.05, gy, z)
    for i, ry in enumerate((POST_Y[1], POST_Y[2])):
        P.hose_reel(f"HoseReel_{i}", -POST_X + 0.20, ry + 0.30, POST_TOP - 0.35, -POST_X + 0.05, POST_TOP,
                    "SDT_HoseBlue" if i == 0 else "SDT_HoseBlack")


def place_drones():
    """Přesune hotové drony (kolekce SprayDrone) na horní plošinu, přední částí po směru jízdy."""
    for idx, prefix in enumerate(("Drone_A_", "Drone_B_")):
        objs = P.drone_parts(prefix)
        if not objs:
            continue
        center = P.drone_footprint(objs)
        target = Vector((0, DRONE_Y[idx], TOP_SURF + 0.005))
        if (center - target).length < 1e-3:
            continue
        xf = Matrix.Translation(target) @ Matrix.Rotation(math.radians(-90), 4, "Z") @ Matrix.Translation(-center)
        P.transform_hierarchy(objs, prefix, xf)


def build():
    coll, _ = P.begin(COLLECTION_NAME, ROOT_NAME)
    build_chassis()
    build_gooseneck()
    build_upper_structure()
    build_railings_and_stairs()
    build_equipment()
    place_drones()
    old = bpy.data.collections.get("SprayDroneTrailer")
    if old:
        old.hide_viewport = True
    bpy.context.view_layer.update()
    print(f"{COLLECTION_NAME}: {len(coll.objects)} objektů")


if __name__ == "__main__":
    build()
