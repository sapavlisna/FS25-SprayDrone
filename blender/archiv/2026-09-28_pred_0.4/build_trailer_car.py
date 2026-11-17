"""Servisní vlek pro jeden postřikový dron, menší verze za osobní auto (kulová spojka).

Stejné pojetí jako velká verze (build_trailer3.py): dole paluba s nádržemi a generátorem,
nahoře plošina pro dron. Podvozek porovnaný s vanilla FS25 Stema Trius (evropský valník za auto,
kolekce REF_StemaTrius): kola r 0,30, rozteč náprav 0,70, spojka 0,50-0,55 m nad zemí.

Hmotnost naplněného vleku ~1,3-1,5 t (nádrž 600 l), aby ho utáhlo běžné SUV.

Osa: spojka vpředu na -Y. Počátek = zem, střed šířky, střed paluby.
Staví se ve vlastním souboru spraydrone_trailer_car.blend (jména objektů jsou v .blend globální
a shodují se s velkou verzí). Na plošinu se přesune dron A z kolekce SprayDrone.

Spuštění v Blenderu:
    p = r"...\\build_trailer_car.py"; exec(open(p, encoding="utf-8").read(), {"__file__": p, "__name__": "__main__"})
"""

import importlib
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdt_parts as P  # noqa: E402

importlib.reload(P)

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

DRONE_Y = 0.20

JOCKEY_X, JOCKEY_Y = 0.27, COUPLER_Y + 0.75
JOCKEY_LIFT = 0.20                # o kolik se kolečko při zapřažení zvedne

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
    box("CouplerHead", -0.06, 0.06, COUPLER_Y - 0.08, tip.y + 0.05, COUPLER_Z - 0.04, COUPLER_Z + 0.09, "SDT_Steel")
    box("CouplerLever", -0.03, 0.03, COUPLER_Y - 0.02, tip.y, COUPLER_Z + 0.09, COUPLER_Z + 0.13, "SDT_Frame")
    box("Breakaway_Box", -0.10, 0.10, tip.y + 0.10, tip.y + 0.35, DRAWBAR_Z + 0.04, DRAWBAR_Z + 0.16, "SDT_Frame")
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
    # vanilla přívěsy mají attacherJoint v i3d natočený "0 90 0" (osa Y i3d = osa Z Blenderu)
    aj = empty("attacherJoint", (0, COUPLER_Y, COUPLER_Z))
    aj.rotation_euler = (0, 0, math.radians(90))


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
        parts.append(tube(f"Ladder_Rung_{i:02d}", (LADDER_X[0], p.y, p.z), (LADDER_X[1], p.y, p.z), 0.016,
                          "SDT_Mesh", segments=8))
    for o in parts:
        world = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = world


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
    P.generator("Gen_0", 0.55, -1.35, z)
    px, py = -0.55, -0.55
    P.pump("Pump", px, py, z)
    tube("Pump_Suction", (px + 0.22, py + 0.14, z + 0.42), (px + 0.22, tank_y - tank_len / 2 + 0.15, z + 0.22),
         0.025, "SDT_HoseBlack")
    tube("Pump_Discharge", (px + 0.30, py, z + 0.55), (ix + 0.12, iy + 0.18, top - 0.05), 0.025, "SDT_HoseBlack")
    capsule("Tank_Fresh", (-0.62, 1.55, z + 0.20), 0.18, 0.60, "Y", "SDT_TankWhite")
    box("Toolbox", 0.30, 0.95, 1.30, 1.90, z, z + 0.45, "SDT_Mesh")
    P.hose_reel("HoseReel_0", -POST_X + 0.18, 0.28, POST_TOP - 0.30, -POST_X + 0.04, POST_TOP, "SDT_HoseBlue",
                radius=0.18)


def place_drone():
    """Posadí dron A na plošinu (natočený je už z velké verze po směru jízdy)."""
    objs = P.drone_parts("Drone_A_")
    if not objs:
        return
    target = Vector((0, DRONE_Y, TOP_SURF + 0.005))
    for o in objs:
        if o.parent is not None and not o.parent.name.startswith("Drone_A_"):
            w = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = w
    center = P.drone_footprint(objs)
    if (center - target).length > 1e-3:
        P.transform_hierarchy(objs, "Drone_A_", Matrix.Translation(target - center))
    # dron je součástí vozidla: uzel droneRoot (počátek = střed pod lyžinami), skript letu ho odpojí do světa
    root = _group("droneRoot", bpy.data.objects[ROOT_NAME], tuple(target))
    for o in objs:
        if o.parent is None:
            w = o.matrix_world.copy()
            o.parent = root
            o.matrix_parent_inverse = root.matrix_world.inverted()
            o.matrix_world = w


def _physics(obj, **props):
    for k, v in props.items():
        obj["i3D_" + k] = v
    return obj


def _shape_box(name, parent, x0, x1, y0, y1, z0, z1, group_mask, **props):
    """Neviditelný kolizní/spouštěcí kvádr s počátkem v rodiči (vrcholy leží přímo na místě)."""
    obj = box(name, x0, x1, y0, y1, z0, z1, "SDT_Frame")
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
    build_ladder()
    build_equipment()
    build_i3d_structure(vis)
    move_to_preview(("Wheel_", "Rim_"))
    place_drone()
    bpy.context.view_layer.update()
    print(f"{COLLECTION_NAME}: {len(coll.objects)} objektů")


if __name__ == "__main__":
    build()
