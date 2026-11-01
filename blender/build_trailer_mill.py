"""Mlýnkový vozík na vápno jako vozidlo FS25 (vehicles/sdtLimeMill): tvary z sdt_mlyn.py, kolizní komponenta, kola, podpěrné kolečko,
plnicí uzly, uzly pro hadici (články millHoseSeg1..N, koncovka millHoseEnd, uložená hadice millHoseStored) a druhá UV vrstva pro vmask.

Spouští ho headless_mill.py (build / export). Osa jako u vleků: vpředu -Y, +X vlevo, Z nahoru, počátek na zemi uprostřed šířky.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import sdt_parts as P  # noqa: E402
import sdt_tanks as T  # noqa: E402
import sdt_mlyn as MILL  # noqa: E402
from sdt_tanks import Mesh, V  # noqa: E402

COLLECTION_NAME = "SprayDroneMill"
PREVIEW_COLLECTION = "SprayDroneMill_Preview"
COMPONENT_NAME = "sdtLimeMill_main_component1"
ROOT_NAME = "sdtLimeMill_vis"

COL_VEHICLE = (0x10004, 0xfe3ffb83)
COL_FILL_ROOT = (0x40000000, 0x20000000)

HOSE_SEGMENTS = 72                     # článků hadice (rozvinutá hadice ~9 m, hustota 8 cm na článek rozhoduje o ohybech)
HOSE_RADIUS = 0.05

TIRE_FILE = "$data/shared/wheels/tires/lizard/destinationFarm/280_70R15.xml"
RIM_FILE, RIM_WIDTH_DIAM = "wheels/sdtRim15.i3d", "8 15.5"
TIRE_Y_OFFSET = MILL.TIRE_Y_OFFSET
TIRE_REST_LOAD, TIRE_COMPRESSION, TIRE_SUSP_TRAVEL = 1.4, 12, 0.05
TIRE_SPRING, TIRE_DAMPER, TIRE_FRICTION = 90, 40, 1.6
LEGACY_WHEEL_IDS = ()

BASE_W = 2 * MILL.DECK_HX
BASE_Y0, BASE_Y1 = MILL.Y_FRONT, MILL.Y_REAR
COUPLER_Z = MILL.COUPLER_Z
COUPLER_Y = MILL.DRAWBAR_TIP_Y
JOCKEY_X, JOCKEY_Y, JOCKEY_Z = MILL.JOCKEY_X, MILL.JOCKEY_Y, MILL.DRAWBAR_Z
JOCKEY_LIFT = MILL.JOCKEY_LIFT
# těžiště: 18 % cesty od nápravy k oji (kolem 10 % se vozík po odpojení v testu ve hře převrátil dozadu na násypku)
AXLE_Y = MILL.AXLE_Y
CENTER_OF_MASS = (0.0, AXLE_Y + (COUPLER_Y - AXLE_Y) * 0.18, 1.05)
HOPPER_CAPACITY = 2400
DIESEL_CAPACITY = 40
FINE_CAPACITY = 150


def _physics(obj, **props):
    for k, v in props.items():
        obj["i3D_" + k] = v
    return obj


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


def _shape_box(name, parent, x0, x1, y0, y1, z0, z1, group_mask, **props):
    return _as_shape(P.box(name, x0, x1, y0, y1, z0, z1, "SDT_Frame"), parent, group_mask, **props)


def _group(name, parent, loc=(0, 0, 0)):
    g = P.empty(name, loc)
    g.parent = parent
    g.matrix_parent_inverse = Matrix.Identity(4)
    g.matrix_world = Matrix.Translation(loc)
    return g


def _set_parent(obj, parent, world):
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = world


def build_hose_nodes(vis):
    """Slepá spojka na výstupu mlýnku (millPortCap): skript ji skrývá, když je na výstup připojená hadice vleku."""
    for name, parent in (("Mill_PortCap", P.empty("millPortCap", (0, 0, 0))),):
        o = bpy.data.objects[name]
        world = o.matrix_world.copy()
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = world


def fill_plane(name, parent, center, size_x, size_y, mat="SDT_PaintWhite"):
    """Rovina hladiny pro vanilla fillPlane (FillUnit.loadFillPlane): mřížka size_x x size_y s počátkem ve středu; hra jí přiřadí
    materiál fillPlane s texturou druhu a hýbe s ní podle klíčů v XML (výška a měřítko)."""
    bm = bmesh.new()
    n = 4
    grid = [[bm.verts.new(((i / n - 0.5) * size_x, (j / n - 0.5) * size_y, 0.0)) for i in range(n + 1)] for j in range(n + 1)]
    for j in range(n):
        for i in range(n):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    P._box_uv(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(P.material(mat))
    o = bpy.data.objects.new(name, me)
    bpy.data.collections[COLLECTION_NAME].objects.link(o)
    _set_parent(o, parent, Matrix.Translation(center))
    return o


def build_spout_nodes(vis):
    """Pohyblivé díly plnění big bagu: páka klapky (millValveLever, osa hřídele po Y), otočná roura (millSpoutPivot, svislá osa)
    s plnicí hlavou (millFillHead = střed čela límce, ústí míří vodorovně od kloubu) a hrdlem vaku (millBagNeck), místo kliknutí pěšky u kloubu (millSpoutJoint)."""
    c = MILL.VALVE_C
    lever = _group("millValveLever", vis, (c.x, MILL.VALVE_SHAFT_Y, c.z))
    o = bpy.data.objects["Mill_ValveLever"]
    _set_parent(o, lever, o.matrix_world.copy())
    sx, sy = MILL.SPOUT_X, MILL.SPOUT_Y
    pivot = _group("millSpoutPivot", vis, (sx, sy, MILL.SPOUT_BEARING_Z))
    for name in ("Mill_SpoutArm", "Mill_BagNeck"):
        o = bpy.data.objects[name]
        _set_parent(o, pivot, o.matrix_world.copy())
    bpy.data.objects["Mill_BagNeck"].name = "millBagNeck"
    _group("millFillHead", pivot, (sx, sy - MILL.SPOUT_MOUTH_L, MILL.SPOUT_HEAD_Z))
    _group("millSpoutJoint", vis, (sx, sy, MILL.SPOUT_BEARING_Z + 0.03))


def build_nodes(vis):
    """Uzly pro hru: kolizní komponenta, kolize, kola, podpěrné kolečko, plnicí kvádry, spojka."""
    zlo = MILL.DECK_Z - 0.15
    comp = _shape_box(COMPONENT_NAME, None, -0.02, 0.02, 0.0, 0.04, zlo, zlo + 0.04, COL_VEHICLE, dynamic=True, compound=True)
    vis.parent = comp
    vis.matrix_parent_inverse = Matrix.Identity(4)
    cols = _group("collisions", comp)
    child = dict(compoundChild=True, density=0.001)
    cx, cy = MILL.HOPPER_CX, MILL.HOPPER_CY
    hx, hy = MILL.HOPPER_HX, MILL.HOPPER_HY
    _shape_box("colChassis", cols, -MILL.DECK_HX, MILL.DECK_HX, BASE_Y0, BASE_Y1, MILL.DECK_Z - 0.15, MILL.DECK_Z + 0.06, COL_VEHICLE, **child)
    _shape_box("colHopper", cols, cx - hx - 0.03, cx + hx + 0.03, cy - hy - 0.03, cy + hy + 0.03, MILL.HOPPER_OUT_Z - 0.12,
               MILL.HOPPER_TOP_Z + 0.05, COL_VEHICLE, **child)
    _shape_box("colMillEngine", cols, MILL.MILL_X - 0.30, MILL.ENG_X1 + 0.08, MILL.ROW_Y - 0.62, MILL.ROW_Y + 0.30, MILL.DECK_Z,
               MILL.DECK_Z + 0.78, COL_VEHICLE, **child)
    bx, by = MILL.BIN_XY
    _shape_box("colBin", cols, bx - MILL.BIN_R - 0.04, bx + MILL.BIN_R + 0.04, by - MILL.BIN_R - 0.04, by + MILL.BIN_R + 0.04,
               MILL.DECK_Z, MILL.BIN_CONE_Z0 + MILL.BIN_CONE_H + MILL.BIN_BODY_H + 0.05, COL_VEHICLE, **child)
    _shape_box("colDrawbar", cols, -0.12, 0.12, COUPLER_Y - 0.10, BASE_Y0, COUPLER_Z - 0.12, COUPLER_Z + 0.07, COL_VEHICLE, **child)
    for side, sx in (("L", 1), ("R", -1)):
        fa, fb = sorted((sx * (MILL.DECK_HX), sx * (MILL.TRACK_X + MILL.WHEEL_W / 2 + 0.035)))
        zc = MILL.AXLE_Z
        _shape_box(f"colFender{side}", cols, fa, fb, AXLE_Y - MILL.FENDER_R * 0.6, AXLE_Y + MILL.FENDER_R * 0.6,
                   zc + MILL.FENDER_R * 0.55, zc + MILL.FENDER_R + 0.012, COL_VEHICLE, **child)

    wheels = _group("wheels", vis)
    bpy.context.view_layer.update()
    for sx, side in ((1, "Left"), (-1, "Right")):
        _group(f"wheelFront{side}", wheels, (sx * MILL.TRACK_X, AXLE_Y, MILL.WHEEL_R))

    pivot = _group("jockeyWheel", vis, (JOCKEY_X, JOCKEY_Y, JOCKEY_Z))
    jockey = bpy.data.objects["Mill_Jockey"]
    _set_parent(jockey, pivot, jockey.matrix_world.copy())
    _shape_box("colJockeyWheel", pivot, JOCKEY_X - 0.07, JOCKEY_X + 0.07, JOCKEY_Y - 0.08, JOCKEY_Y + 0.08, 0.0, 0.44,
               COL_VEHICLE, **child)

    aj = P.empty("attacherJoint", (0, COUPLER_Y, COUPLER_Z))
    aj.rotation_euler = (0, 0, math.radians(90))

    fill = _group("fill", vis)
    _shape_box("exactFillRootNode", fill, cx - hx, cx + hx, cy - hy, cy + hy, MILL.HOPPER_SLOPE_Z, MILL.HOPPER_TOP_Z + 0.30,
               COL_FILL_ROOT, kinematic=True, compound=True)
    x0, x1 = MILL.ENG_X0, MILL.ENG_X1
    fill_plane("coarseFillPlane", fill, (cx, cy, MILL.HOPPER_OUT_Z), 2 * hx, 2 * hy)
    _shape_box("dieselFillRootNode", fill, x0 - 0.04, x1 + 0.04, MILL.FUEL_Y - MILL.FUEL_R - 0.04, MILL.FUEL_Y + MILL.FUEL_R + 0.04,
               MILL.FUEL_Z - MILL.FUEL_R, MILL.FUEL_Z + MILL.FUEL_R + 0.25, COL_FILL_ROOT, kinematic=True, compound=True)
    snd = P.empty("millSoundNode", V((x0 + x1) / 2, MILL.ROW_Y, MILL.DECK_Z + 0.5))
    snd.empty_display_size = 0.10
    enter = _group("enterable", vis)
    _group("exitPoint", enter, (MILL.DECK_HX + 0.55, MILL.ROW_Y + 0.4, 0.0))
    target = _group("outdoorCameraTarget", enter, (0.0, MILL.ROW_Y, MILL.DECK_Z + 1.2))
    cam_data = bpy.data.cameras.get("outdoorCamera") or bpy.data.cameras.new("outdoorCamera")
    cam_data.lens = 22
    cam_data.clip_start = 0.3
    cam_data.clip_end = 5000
    cam = bpy.data.objects.new("outdoorCamera", cam_data)
    bpy.data.collections[COLLECTION_NAME].objects.link(cam)
    cam.parent = target
    cam.matrix_parent_inverse = Matrix.Identity(4)
    cam.matrix_world = Matrix.Translation(Vector((0.0, MILL.ROW_Y, MILL.DECK_Z + 1.2)) + Vector((0, 8, 3)))
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


def dirt_meshes():
    """Meshe s druhou UV vrstvou pro vmask; svítící materiál (staticLight_vertex, prstenec tlačítka) vmask nemá."""
    return [o for o in bpy.data.collections[COLLECTION_NAME].objects if o.type == "MESH" and not o.get("i3D_nonRenderable")
            and not any(m and m.name == "SDT_NavLed" for m in o.data.materials) and o.name != "coarseFillPlane"]


def _ensure_uv0(obj):
    me = obj.data
    if not me.uv_layers:
        bm = bmesh.new()
        bm.from_mesh(me)
        P._box_uv(bm)
        bm.to_mesh(me)
        bm.free()
    uv = me.uv_layers[0]
    uv.name = "UVMap"
    for poly in me.polygons:
        for li in poly.loop_indices:
            u, v = uv.data[li].uv
            uv.data[li].uv = (u + 8.0, v + 8.0)


def build_dirt_uvs():
    """Druhá UV vrstva DirtUV pro vehicleShader (varianta vmaskUV2): jedna společná rozvinutá plocha 0..1 pro celý vozík."""
    meshes = dirt_meshes()
    for o in meshes:
        _ensure_uv0(o)
        me = o.data
        while len(me.uv_layers) > 1:
            me.uv_layers.remove(me.uv_layers[1])
        me.uv_layers.new(name="DirtUV")
        me.uv_layers.active_index = 1
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in meshes:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, correct_aspect=True,
                             scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in meshes:
        o.data.uv_layers.active_index = 0
        o.select_set(False)
    print(f"DirtUV: {len(meshes)} meshů")


def set_ladder(t):
    """Vozík žebřík nemá; jen rozhraní exportu."""
    return None


def build():
    coll, vis = P.begin(COLLECTION_NAME, ROOT_NAME)
    MILL.build_all()
    build_hose_nodes(vis)
    build_spout_nodes(vis)
    build_nodes(vis)
    move_to_preview(("Mill_Wheel", "Mill_Rim"))
    bpy.context.view_layer.update()
    build_dirt_uvs()
    print(f"{COLLECTION_NAME}: {len(coll.objects)} objektů")
    return MILL.ports()


if __name__ == "__main__":
    build()
