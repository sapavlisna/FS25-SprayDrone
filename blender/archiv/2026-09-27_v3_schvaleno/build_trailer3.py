"""Servisní vlek pro postřikové drony, třetí verze.

Předloha: nuWay Ag "Spray Ready" gooseneck (22 ft deckover + 32 ft letová plošina nahoře),
fotky v reference/. Podvozek porovnaný s vanilla FS25 Kingston Belvedere (jediný gooseneck
přívěs ve hře), importovaným do kolekce REF_Belvedere.

Osa: přední část (čep husího krku) je na -Y, stejně jako u vanilla vozidel po importu.
Počátek = zem, střed šířky, střed spodní paluby. Každý díl má měřítko 1 a vlastní počátek.

Spuštění v Blenderu: exec(open(r"...\\build_trailer3.py", encoding="utf-8").read())
"""

import math

import bmesh
import bpy
import mathutils
from mathutils import Matrix, Vector

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

MATERIALS = {
    "SDT_Frame": ((0.025, 0.025, 0.028), 0.6, 0.45),
    "SDT_DeckWood": ((0.52, 0.40, 0.26), 0.0, 0.8),
    "SDT_TopDeck": ((0.82, 0.82, 0.80), 0.0, 0.6),
    "SDT_TankWhite": ((0.88, 0.88, 0.84), 0.0, 0.35),
    "SDT_TankBlack": ((0.03, 0.03, 0.03), 0.0, 0.5),
    "SDT_Rubber": ((0.015, 0.015, 0.015), 0.0, 0.9),
    "SDT_Rim": ((0.05, 0.05, 0.05), 0.8, 0.35),
    "SDT_GenOrange": ((0.85, 0.33, 0.04), 0.1, 0.4),
    "SDT_EngineRed": ((0.6, 0.03, 0.03), 0.1, 0.4),
    "SDT_TapeRed": ((0.7, 0.02, 0.02), 0.0, 0.3),
    "SDT_TapeWhite": ((0.9, 0.9, 0.9), 0.0, 0.3),
    "SDT_Mesh": ((0.08, 0.08, 0.09), 0.5, 0.5),
    "SDT_HoseBlue": ((0.05, 0.2, 0.6), 0.0, 0.5),
    "SDT_HoseBlack": ((0.02, 0.02, 0.02), 0.0, 0.6),
    "SDT_Steel": ((0.6, 0.62, 0.64), 0.9, 0.3),
    "SDT_LampRed": ((0.8, 0.02, 0.02), 0.0, 0.2),
    "SDT_LampAmber": ((0.9, 0.45, 0.02), 0.0, 0.2),
}

_coll = None
_root = None


def material(name):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    color, metallic, roughness = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1.0)
    return mat


def _finish(name, bm, matrix, mat, smooth_quads=False):
    if smooth_quads:
        for f in bm.faces:
            f.smooth = len(f.verts) == 4
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    _coll.objects.link(obj)
    obj.data.materials.append(material(mat))
    obj.parent = _root
    obj.matrix_world = matrix
    return obj


def box(name, x0, x1, y0, y1, z0, z1, mat):
    size = Vector((abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))
    center = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*size, 1.0)))
    return _finish(name, bm, Matrix.Translation(center), mat)


def _cyl_bm(r1, r2, depth, segments):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=r1, radius2=r2, depth=depth)
    return bm


def tube(name, p0, p1, radius, mat, segments=12, radius_end=None):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = _cyl_bm(radius, radius if radius_end is None else radius_end, d.length, segments)
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    return _finish(name, bm, Matrix.Translation((p0 + p1) / 2) @ rot, mat, smooth_quads=True)


def capsule(name, center, radius, length, axis, mat, end_squash=0.45, segments=24):
    """Ležatá nádrž: válec se zploštělými kulovými čely, osa 'X' nebo 'Y'."""
    bm = bmesh.new()
    body = length - 2 * radius * end_squash
    bmesh.ops.create_cone(bm, cap_ends=False, segments=segments, radius1=radius, radius2=radius, depth=body)
    for sign in (1, -1):
        m = Matrix.Translation((0, 0, sign * body / 2)) @ Matrix.Diagonal((1, 1, end_squash, 1))
        res = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=12, radius=radius, matrix=m)
        cut = [v for v in res["verts"] if (v.co.z - sign * body / 2) * sign < -1e-4]
        bmesh.ops.delete(bm, geom=cut, context="VERTS")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-3)
    for f in bm.faces:
        f.smooth = True
    rot = Matrix.Rotation(math.radians(90), 4, "Y" if axis == "X" else "X")
    return _finish(name, bm, Matrix.Translation(center) @ rot, mat)


def cylinder_z(name, center, radius, height, mat, segments=24, radius_top=None):
    bm = _cyl_bm(radius, radius if radius_top is None else radius_top, height, segments)
    return _finish(name, bm, Matrix.Translation(center), mat, smooth_quads=True)


def cylinder_x(name, center, radius, width, mat, segments=24):
    bm = _cyl_bm(radius, radius, width, segments)
    rot = Matrix.Rotation(math.radians(90), 4, "Y")
    return _finish(name, bm, Matrix.Translation(center) @ rot, mat, smooth_quads=True)


def plate_yz(name, x, thickness, pts_yz, mat):
    """Plech v rovině YZ (trojúhelníkové výztuhy), vytažený do tloušťky po X."""
    bm = bmesh.new()
    front = [bm.verts.new((-thickness / 2, y, z)) for y, z in pts_yz]
    back = [bm.verts.new((thickness / 2, y, z)) for y, z in pts_yz]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(pts_yz)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], front[j], back[j], back[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, Matrix.Translation((x, 0, 0)), mat)


def empty(name, loc):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = 0.3
    _coll.objects.link(e)
    e.parent = _root
    e.matrix_world = Matrix.Translation(loc)
    return e


# ---------------------------------------------------------------- stavba po celcích

def build_chassis():
    rail_z0 = DECK_TOP - RAIL_H
    for side, sx in (("L", 1), ("R", -1)):
        x_out = sx * BASE_W / 2
        box(f"Rail_{side}", x_out, x_out - sx * RAIL_W, BASE_Y0, BASE_Y1, rail_z0, DECK_TOP, "SDT_Frame")
        box(f"IBeam_{side}", sx * IBEAM_X - 0.05, sx * IBEAM_X + 0.05, BASE_Y0, BASE_Y1,
            DECK_TOP - DECK_PLATE - IBEAM_H, DECK_TOP - DECK_PLATE, "SDT_Frame")
        seg, y, i = 0.30, BASE_Y0 + 0.05, 0
        while y + seg <= BASE_Y1 - 0.05:
            xf = x_out + sx * 0.002
            box(f"Tape_{side}_{i:02d}", xf, xf + sx * 0.002, y, y + seg, rail_z0 + 0.08, rail_z0 + 0.16,
                "SDT_TapeRed" if i % 2 == 0 else "SDT_TapeWhite")
            y += seg + 0.02
            i += 1
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


def _railing(prefix, pts, r=0.022, mid=True, post_every=1.2):
    """Trubkové zábradlí po lomené čáře pts=[(x,y)] na horní plošině."""
    z_top = TOP_SURF + RAIL_HEIGHT
    z_mid = TOP_SURF + RAIL_HEIGHT / 2
    k = 0
    for a, b in zip(pts, pts[1:]):
        a3, b3 = Vector((*a, 0)), Vector((*b, 0))
        tube(f"{prefix}_Top{k}", (a[0], a[1], z_top), (b[0], b[1], z_top), r, "SDT_Frame", segments=10)
        if mid:
            tube(f"{prefix}_Mid{k}", (a[0], a[1], z_mid), (b[0], b[1], z_mid), r * 0.8, "SDT_Frame", segments=10)
        n = max(1, round((b3 - a3).length / post_every))
        for j in range(n + (1 if k == len(pts) - 2 else 0)):
            p = a3.lerp(b3, j / n)
            tube(f"{prefix}_Post{k}_{j}", (p.x, p.y, TOP_SURF), (p.x, p.y, z_top), r, "SDT_Frame", segments=10)
        k += 1


def build_railings_and_stairs():
    hw = TOP_W / 2 - 0.05
    # pilotní prostor vpředu: zábradlí na třech stranách + síťová stěna
    _railing("PilotRail", [(-hw, PILOT_Y1), (-hw, TOP_Y0 + 0.05), (hw, TOP_Y0 + 0.05), (hw, PILOT_Y1)])
    box("PilotMesh", -hw + 0.03, hw - 0.03, TOP_Y0 + 0.04, TOP_Y0 + 0.055, TOP_SURF + 0.10,
        TOP_SURF + RAIL_HEIGHT - 0.05, "SDT_Mesh")
    box("PilotLightBar", -0.35, 0.35, TOP_Y0 + 0.03, TOP_Y0 + 0.10, TOP_SURF + RAIL_HEIGHT + 0.03,
        TOP_SURF + RAIL_HEIGHT + 0.10, "SDT_LampAmber")
    # zábradlí kolem otvoru pro schody
    _railing("HoleRail", [(HOLE_X[0] - 0.03, HOLE_Y[0] + 0.05), (HOLE_X[0] - 0.03, HOLE_Y[1] + 0.03),
                          (HOLE_X[1], HOLE_Y[1] + 0.03)], post_every=0.7)

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
        t = i / steps
        p = bottom.lerp(top, t)
        box(f"Stair_Step_{i:02d}", STAIR_X[0] + 0.03, STAIR_X[1] - 0.03, p.y - 0.12, p.y + 0.12,
            p.z - 0.03, p.z, "SDT_Mesh")


def build_equipment():
    z = DECK_TOP
    # 1000 gal hlavní nádrž (ležatá) vzadu, s pásy a sedlem
    tank_r, tank_len, tank_y = 0.74, 2.45, 1.95
    capsule("Tank_Main", (0, tank_y, z + 0.12 + tank_r), tank_r, tank_len, "Y", "SDT_TankWhite")
    for i, dy in enumerate((-0.75, -0.25, 0.25, 0.75)):
        tube(f"Tank_Main_Band{i}", (0, tank_y + dy - 0.02, z + 0.12 + tank_r), (0, tank_y + dy + 0.02,
             z + 0.12 + tank_r), tank_r + 0.012, "SDT_TankBlack", segments=32)
    for i, dy in enumerate((-0.8, 0.8)):
        box(f"Tank_Main_Saddle{i}", -0.55, 0.55, tank_y + dy - 0.06, tank_y + dy + 0.06, z, z + 0.35,
            "SDT_Frame")
    cylinder_z("Tank_Main_Lid", (0, tank_y, z + 0.12 + 2 * tank_r + 0.03), 0.20, 0.08, "SDT_TankWhite")

    # 175 gal indukční nádrž s kuželovým dnem na černém stojanu
    ix, iy, ir = -0.62, -0.40, 0.48
    box("Tank_Induction_Stand", ix - 0.46, ix + 0.46, iy - 0.46, iy + 0.46, z, z + 0.45, "SDT_TankBlack")
    cylinder_z("Tank_Induction_Cone", (ix, iy, z + 0.45 + 0.20), 0.06, 0.40, "SDT_TankBlack", radius_top=ir)
    cylinder_z("Tank_Induction_Body", (ix, iy, z + 0.85 + 0.40), ir, 0.80, "SDT_TankWhite")
    cylinder_z("Tank_Induction_Lid", (ix, iy, z + 1.65 + 0.05), 0.18, 0.10, "SDT_TankBlack")

    # 50 gal čistá voda
    capsule("Tank_Fresh", (-0.72, -2.35, z + 0.30), 0.28, 0.95, "Y", "SDT_TankWhite")

    # čerpadlo 2" s benzínovým motorem
    px, py = -0.55, 0.55
    box("Pump_Stand", px - 0.25, px + 0.25, py - 0.20, py + 0.20, z, z + 0.25, "SDT_Frame")
    box("Pump_Engine", px - 0.20, px + 0.12, py - 0.18, py + 0.18, z + 0.25, z + 0.58, "SDT_EngineRed")
    cylinder_x("Pump_Housing", (px + 0.22, py, z + 0.42), 0.14, 0.18, "SDT_TankBlack")
    tube("Pump_Suction", (px + 0.22, py + 0.14, z + 0.42), (px + 0.22, tank_y - tank_len / 2 + 0.2, z + 0.25),
         0.03, "SDT_HoseBlack")
    tube("Pump_Discharge", (px + 0.30, py, z + 0.55), (ix + 0.2, iy + 0.3, z + 1.55), 0.03, "SDT_HoseBlack")

    # generátory vedle schodů, ne pod nimi: pod strmým schodištěm není 0,8 m světlé výšky
    for i, gy in enumerate((-2.55, -1.62)):
        gx = 0.05
        box(f"Gen_{i}_Body", gx - 0.33, gx + 0.33, gy - 0.40, gy + 0.40, z + 0.05, z + 0.72, "SDT_GenOrange")
        for cx in (gx - 0.36, gx + 0.36):
            for cy in (gy - 0.43, gy + 0.43):
                tube(f"Gen_{i}_Cage_{cx:+.2f}_{cy:+.2f}", (cx, cy, z), (cx, cy, z + 0.78), 0.018, "SDT_Frame",
                     segments=8)
        for cx in (gx - 0.36, gx + 0.36):
            tube(f"Gen_{i}_CageTop_{cx:+.2f}", (cx, gy - 0.43, z + 0.78), (cx, gy + 0.43, z + 0.78), 0.018,
                 "SDT_Frame", segments=8)

    # hadicové navijáky pod plošinou na pravých sloupcích
    for i, ry in enumerate((POST_Y[1], POST_Y[2])):
        rx, rz = -POST_X + 0.20, POST_TOP - 0.35
        cylinder_x(f"HoseReel_{i}_Drum", (rx, ry + 0.30, rz), 0.22, 0.20,
                   "SDT_HoseBlue" if i == 0 else "SDT_HoseBlack")
        for dx in (-0.11, 0.11):
            cylinder_x(f"HoseReel_{i}_Flange{dx:+.2f}", (rx + dx, ry + 0.30, rz), 0.28, 0.015, "SDT_Frame")
        box(f"HoseReel_{i}_Bracket", -POST_X + 0.05, rx + 0.12, ry + 0.26, ry + 0.34, rz, POST_TOP, "SDT_Frame")


def reset():
    global _coll, _root
    coll = bpy.data.collections.get(COLLECTION_NAME)
    if coll:
        for o in list(coll.objects):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)
    else:
        coll = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(coll)
    _coll = coll
    _root = bpy.data.objects.new(ROOT_NAME, None)
    _root.empty_display_type = "PLAIN_AXES"
    coll.objects.link(_root)


def place_drones():
    """Přesune hotové drony (kolekce SprayDrone) na horní plošinu, přední částí po směru jízdy."""
    drones = bpy.data.collections.get("SprayDrone")
    if not drones:
        return
    for idx, prefix in enumerate(("Drone_A_", "Drone_B_")):
        objs = [o for o in drones.all_objects if o.name.startswith(prefix)]
        if not objs:
            continue
        mn = Vector((1e9,) * 3)
        mx = -mn
        for o in objs:
            if o.type == "MESH":
                for c in o.bound_box:
                    w = o.matrix_world @ Vector(c)
                    mn = Vector(map(min, mn, w))
                    mx = Vector(map(max, mx, w))
        center = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
        target = Vector((0, DRONE_Y[idx], TOP_SURF + 0.005))
        if (center - target).length < 1e-3:
            continue
        xf = Matrix.Translation(target) @ Matrix.Rotation(math.radians(-90), 4, "Z") @ Matrix.Translation(-center)
        for o in objs:
            if o.parent is None or not o.parent.name.startswith(prefix):
                o.matrix_world = xf @ o.matrix_world


def build():
    reset()
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
    print(f"{COLLECTION_NAME}: {len(_coll.objects)} objektů")


build()
