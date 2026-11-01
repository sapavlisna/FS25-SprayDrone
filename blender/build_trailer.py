"""Parametricky postaví servisní vlek pro postřikové drony (hranatá technika, primitivy).

Spustit v Blenderu (Text editor -> Run Script, nebo přes `blender --python build_trailer.py`,
nebo přes Blender MCP execute_blender_code). Idempotentní - smaže předchozí verzi kolekce
SprayDroneTrailer a postaví znovu, takže úprava parametru = přegenerování.

Rozměry jsou orientační (viz PLAN.md), ne přesná strojní data.
"""

import os
import sys

import bpy
import bmesh
import math
import mathutils

COLLECTION_NAME = "SprayDroneTrailer"

# IBC nádrž bereme z herních dat - při exportu z ní bude reference na $data, ne kopie
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdt_paths  # noqa: E402

FS25_DATA = os.path.join(sdt_paths.GAME_DIR, "data")
IBC_I3D = os.path.join(FS25_DATA, "objects", "pallets", "liquidTank", "liquidTank.i3d")
IBC_ASSET_COLLECTION = "Asset_LiquidTank"
IBC_DATA_PATH = "$data/objects/pallets/liquidTank/liquidTank.i3d"

# --- Parametry (m) ---
DECK_LEN = 9.0
DECK_WIDTH = 2.4
DECK_THICK = 0.08
GOOSENECK_LEN = 2.2
HITCH_Z = 1.0

WHEEL_RADIUS = 0.42
WHEEL_WIDTH = 0.35
AXLE_CENTER_X = -2.9
# rozteč tandemu podle velikosti kol - mezi plášti ~16 cm
AXLE_SPACING = 2 * WHEEL_RADIUS + 0.16
AXLE_X = [AXLE_CENTER_X - AXLE_SPACING / 2, AXLE_CENTER_X + AXLE_SPACING / 2]
FENDER_CLEARANCE = 0.04
# rozchod tak, aby se i blatníky vešly do obrysu korby (přepravní šířka = DECK_WIDTH)
TRACK_Y = DECK_WIDTH / 2 - (WHEEL_WIDTH + 0.15) / 2 - 0.03
RAIL_HEIGHT = 0.08

# ložná plocha musí být nad blatníky (jinak kola prorážejí korbu), ale co nejníž,
# ať paluba nevisí nad koly ve vzduchu
FENDER_TOP_Z = WHEEL_RADIUS + (WHEEL_RADIUS + FENDER_CLEARANCE)
DECK_TOP_Z = FENDER_TOP_Z + 0.02 + RAIL_HEIGHT + DECK_THICK

IBC_DIMS = (1.0, 1.2, 1.16)  # standard 1000l IBC kontejner
GEN_DIMS = (1.0, 0.8, 0.9)

PLATFORM_LEN = DECK_LEN
PLATFORM_WIDTH = DECK_WIDTH
PLATFORM_THICK = 0.06
# výška plošiny je kompromis: sklopená křídla musí zůstat pod 4 m přepravní výšky
PLATFORM_Z = DECK_TOP_Z + 1.78

# sklopná křídla plošiny - plocha pro drony je otevřená, bez zábradlí
WING_WIDTH = 1.0
WINGS_FOLDED = 0.0  # 0 = rozloženo (široká plocha), 1 = sklopeno nahoru pro transport


def clear_collection():
    if COLLECTION_NAME in bpy.data.collections:
        coll = bpy.data.collections[COLLECTION_NAME]
        for obj in list(coll.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        coll = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(coll)
    return coll


def _move_to_collection(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def add_box(coll, name, dims, loc, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = dims
    obj.rotation_euler = rot
    _move_to_collection(obj, coll)
    return obj


def add_cylinder(coll, name, radius, depth, loc, rot=(0, 0, 0), verts=20):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rot
    _move_to_collection(obj, coll)
    return obj


def add_multibox(coll, name, boxes, loc=(0, 0, 0)):
    """Jeden mesh objekt složený z víc kvádrů - šetří počet objektů (klec, mříže)."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for dims, center in boxes:
        matrix = mathutils.Matrix.Translation(center) @ mathutils.Matrix.Diagonal(
            (dims[0], dims[1], dims[2], 1.0)
        )
        bmesh.ops.create_cube(bm, size=1.0, matrix=matrix)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    coll.objects.link(obj)
    return obj


def add_beveled_box(coll, name, dims, loc, bevel=0.06, segments=2):
    """Kvádr se sraženými hranami - měřítko zůstává 1, aby bylo sražení rovnoměrné."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.Diagonal((dims[0], dims[1], dims[2], 1.0)))
    bmesh.ops.bevel(
        bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        offset=bevel, segments=segments, affect='EDGES', profile=0.5,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    coll.objects.link(obj)
    return obj


def _rounded_rect_path(size_x, size_y, radius, corner_segments=4):
    """Body uzavřené cesty obdélníku se zaoblenými rohy (v rovině XY, kolem počátku)."""
    hx = size_x / 2 - radius
    hy = size_y / 2 - radius
    pts = []
    for cx, cy, start in (
        (hx, hy, 0.0),
        (-hx, hy, math.pi / 2),
        (-hx, -hy, math.pi),
        (hx, -hy, 1.5 * math.pi),
    ):
        for i in range(corner_segments + 1):
            a = start + (math.pi / 2) * i / corner_segments
            pts.append(mathutils.Vector((cx + radius * math.cos(a), cy + radius * math.sin(a), 0.0)))
    return pts


def _tube(bm, points, radius, sides=6, closed=False):
    """Kruhová trubka vedená po zadané cestě - drát klece místo hranatého prutu."""
    n = len(points)
    rings = []
    for i, p in enumerate(points):
        if closed:
            tangent = (points[(i + 1) % n] - points[(i - 1) % n])
        else:
            prev = points[max(i - 1, 0)]
            nxt = points[min(i + 1, n - 1)]
            tangent = nxt - prev
        tangent.normalize()
        up = mathutils.Vector((0, 0, 1))
        if abs(tangent.dot(up)) > 0.99:
            up = mathutils.Vector((1, 0, 0))
        n1 = tangent.cross(up).normalized()
        n2 = tangent.cross(n1).normalized()
        rings.append([
            bm.verts.new(p + n1 * (radius * math.cos(2 * math.pi * k / sides))
                           + n2 * (radius * math.sin(2 * math.pi * k / sides)))
            for k in range(sides)
        ])
    span = n if closed else n - 1
    for i in range(span):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new((a[k], a[k2], b[k2], b[k]))


def add_wire_cage(coll, name, size, loc, wire_radius, corner_radius, n_x=6, n_y=7, n_z=6, sides=6):
    """Drátěná klec IBC: vodorovné obruče se zaoblenými rohy + svislé pruty na rovných úsecích."""
    sx, sy, sz = size
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    path = _rounded_rect_path(sx, sy, corner_radius)
    for i in range(n_z):
        z = -sz / 2 + sz * i / (n_z - 1)
        _tube(bm, [p + mathutils.Vector((0, 0, z)) for p in path], wire_radius, sides=sides, closed=True)

    # svislé pruty jen tam, kde je stěna rovná - v rozích je jen oblouk obruče
    flat_x = sx / 2 - corner_radius
    flat_y = sy / 2 - corner_radius
    posts = []
    for i in range(n_x):
        px = -flat_x + 2 * flat_x * i / (n_x - 1)
        posts += [(px, sy / 2), (px, -sy / 2)]
    for i in range(n_y):
        py = -flat_y + 2 * flat_y * i / (n_y - 1)
        posts += [(sx / 2, py), (-sx / 2, py)]
    for px, py in posts:
        _tube(
            bm,
            [mathutils.Vector((px, py, -sz / 2)), mathutils.Vector((px, py, sz / 2))],
            wire_radius, sides=sides,
        )

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    coll.objects.link(obj)
    return obj


def add_tube_frame(coll, name, size, loc, tube_radius=0.03, corner_radius=0.12, sides=6):
    """Ochranný trubkový rám: dolní a horní obruč se zaoblenými rohy + svislé trubky v rozích."""
    sx, sy, sz = size
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    path = _rounded_rect_path(sx, sy, corner_radius)
    for z in (-sz / 2, sz / 2):
        _tube(bm, [p + mathutils.Vector((0, 0, z)) for p in path], tube_radius, sides=sides, closed=True)

    inset = corner_radius * 0.7
    for px in (sx / 2 - inset, -(sx / 2 - inset)):
        for py in (sy / 2 - inset, -(sy / 2 - inset)):
            _tube(
                bm,
                [mathutils.Vector((px, py, -sz / 2)), mathutils.Vector((px, py, sz / 2))],
                tube_radius, sides=sides,
            )

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    coll.objects.link(obj)
    return obj


def add_louvers(coll, prefix, center, size, axis, count=6, slat_angle=math.radians(25)):
    """Větrací žaluzie: rámeček a v něm šikmá žebra. `axis` je normála mřížky ('x' nebo 'y')."""
    w, h = size  # šířka a výška otvoru v rovině mřížky
    cx, cy, cz = center
    frame_t = 0.02
    if axis == 'x':
        add_box(coll, f"{prefix}_Frame_T", (frame_t, w, 0.025), (cx, cy, cz + h / 2))
        add_box(coll, f"{prefix}_Frame_B", (frame_t, w, 0.025), (cx, cy, cz - h / 2))
        add_box(coll, f"{prefix}_Frame_L", (frame_t, 0.025, h), (cx, cy + w / 2, cz))
        add_box(coll, f"{prefix}_Frame_R", (frame_t, 0.025, h), (cx, cy - w / 2, cz))
    else:
        add_box(coll, f"{prefix}_Frame_T", (w, frame_t, 0.025), (cx, cy, cz + h / 2))
        add_box(coll, f"{prefix}_Frame_B", (w, frame_t, 0.025), (cx, cy, cz - h / 2))
        add_box(coll, f"{prefix}_Frame_L", (0.025, frame_t, h), (cx + w / 2, cy, cz))
        add_box(coll, f"{prefix}_Frame_R", (0.025, frame_t, h), (cx - w / 2, cy, cz))

    slat_h = h / count
    for i in range(count):
        z = cz - h / 2 + slat_h * (i + 0.5)
        # lamela se naklápí kolem své podélné osy, jinak trčí z pláště
        if axis == 'x':
            add_box(
                coll, f"{prefix}_Slat_{i}", (0.03, w - 0.05, slat_h * 0.8), (cx, cy, z),
                rot=(0, slat_angle, 0),
            )
        else:
            add_box(
                coll, f"{prefix}_Slat_{i}", (w - 0.05, 0.03, slat_h * 0.8), (cx, cy, z),
                rot=(slat_angle, 0, 0),
            )


def add_sheet_shell(coll, name, outer_pts, thickness, width, loc):
    """Plech dané tloušťky vedený po profilu v rovině XZ a protažený do šířky (blatník).

    `outer_pts` je vnější líc profilu; vnitřní vznikne odsazením po normále.
    """
    n = len(outer_pts)
    inner = []
    for i, p in enumerate(outer_pts):
        prev = outer_pts[max(i - 1, 0)]
        nxt = outer_pts[min(i + 1, n - 1)]
        tangent = (mathutils.Vector(nxt) - mathutils.Vector(prev)).normalized()
        normal = mathutils.Vector((-tangent.y, tangent.x))  # kolmice v XZ, ven z plechu
        inner.append(mathutils.Vector(p) - normal * thickness)

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rows = []
    for y in (-width / 2, width / 2):
        rows.append((
            [bm.verts.new((p[0], y, p[1])) for p in outer_pts],
            [bm.verts.new((p.x, y, p.y)) for p in inner],
        ))
    (o0, i0), (o1, i1) = rows
    for i in range(n - 1):
        bm.faces.new((o0[i], o0[i + 1], o1[i + 1], o1[i]))  # vnější líc
        bm.faces.new((i0[i + 1], i0[i], i1[i], i1[i + 1]))  # vnitřní líc
        bm.faces.new((o0[i], i0[i], i0[i + 1], o0[i + 1]))  # bok y-
        bm.faces.new((o1[i + 1], i1[i + 1], i1[i], o1[i]))  # bok y+
    for a in (0, n - 1):  # čela plechu
        bm.faces.new((o0[a], o1[a], i1[a], i0[a]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    coll.objects.link(obj)
    return obj


def tandem_fender_profile(axle_xs, radius, center_z, skirt_z, arc_segments=10):
    """Profil blatníku přes obě kola tandemu: oblouky nad koly + spojení mezi nimi."""
    start_a, end_a = math.radians(168), math.radians(12)
    pts = [(axle_xs[0] - radius * abs(math.cos(start_a)), skirt_z)]
    for k, ax in enumerate(axle_xs):
        for i in range(arc_segments + 1):
            a = start_a + (end_a - start_a) * i / arc_segments
            pts.append((ax + radius * math.cos(a), center_z + radius * math.sin(a)))
    pts.append((axle_xs[-1] + radius * abs(math.cos(end_a)), skirt_z))
    return pts


MATERIALS = {
    # název: (base color RGB, metallic, roughness)
    "Steel_Dark": ((0.09, 0.10, 0.11), 0.9, 0.45),
    "Steel_Galvanized": ((0.62, 0.64, 0.66), 0.85, 0.35),
    "Deck_Plate": ((0.24, 0.26, 0.27), 0.8, 0.55),
    "Paint_Green": ((0.07, 0.24, 0.10), 0.25, 0.4),
    "Paint_Yellow": ((0.72, 0.52, 0.04), 0.2, 0.45),
    "Plastic_White": ((0.82, 0.83, 0.80), 0.0, 0.35),
    "Plastic_Black": ((0.03, 0.03, 0.035), 0.0, 0.5),
    "Rubber": ((0.02, 0.02, 0.02), 0.0, 0.85),
    "Wood": ((0.28, 0.18, 0.09), 0.0, 0.8),
    "Glass_Dark": ((0.01, 0.02, 0.02), 0.0, 0.15),
    "Lamp_Red": ((0.55, 0.02, 0.02), 0.0, 0.2),
    "Lamp_Green": ((0.05, 0.45, 0.08), 0.0, 0.2),
    "Steel_Hot": ((0.16, 0.14, 0.13), 0.7, 0.65),
    "Drone_White": ((0.84, 0.85, 0.86), 0.0, 0.32),
    "Drone_Grey": ((0.27, 0.28, 0.30), 0.05, 0.5),
    "Drone_GreyDark": ((0.13, 0.135, 0.14), 0.1, 0.5),
    "Carbon": ((0.045, 0.045, 0.055), 0.25, 0.4),
    "Prop_Blade": ((0.06, 0.06, 0.065), 0.0, 0.38),
    "Prop_Tip": ((0.90, 0.40, 0.03), 0.0, 0.3),
    "Drone_Accent_A": ((0.75, 0.28, 0.02), 0.1, 0.35),
    "Drone_Accent_B": ((0.05, 0.28, 0.62), 0.1, 0.35),
}

# fragment jména, první shoda vyhrává - proto od nejkonkrétnějšího
MATERIAL_RULES = [
    (("Wheel_",), "Rubber"),
    (("HubCap_",), "Steel_Galvanized"),
    (("Fender_",), "Paint_Green"),
    (("Susp",), "Steel_Dark"),
    (("IBC_1_Cage", "IBC_2_Cage"), "Steel_Galvanized"),
    (("IBC_1_PalletTop", "IBC_1_PalletFoot", "IBC_2_PalletTop", "IBC_2_PalletFoot"), "Wood"),
    (("_Valve", "_ValveLever", "_Neck", "_Cap"), "Plastic_Black"),
    (("IBC_1", "IBC_2"), "Plastic_White"),
    (("_Display", "_GaugeGlass"), "Glass_Dark"),
    (("Lamp_Red", "_EStop"), "Lamp_Red"),
    (("Lamp_Green",), "Lamp_Green"),
    (("_Muffler", "_TailPipe", "_TailTip", "_DownPipe", "_HeatShield"), "Steel_Hot"),
    (("_Fuel", "_Knob_", "_Socket", "_Switch", "_Breaker", "_Gauge", "_Mount_"), "Plastic_Black"),
    (("_Grille",), "Steel_Dark"),
    (("_Hood", "_Panel"), "Paint_Yellow"),
    (("_Exhaust", "_Fin_", "_Knob_", "_Socket", "_Frame", "_Skid"), "Steel_Dark"),
    (("_Net",), "Steel_Galvanized"),
    (("_Post_", "Stair_"), "Paint_Yellow"),
    (("Deck", "Platform", "_Beam_", "_Rib_"), "Deck_Plate"),
    (("Strut_", "Brace_"), "Paint_Green"),
    (("ChassisRail_", "Gooseneck", "HitchEye", "Axle_"), "Steel_Dark"),
]


# materiály, které hra v obchodě přebarvuje podle jména slotu (materialSlotName v XML): barva bedny Mini a barva ráfků
MATERIAL_SLOT_NAMES = {"SDT_CrateGreen": "SDT_CrateGreen", "SDT_RimPaint": "rim_outer_mat"}


def get_material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    color, metallic, roughness = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    if name in MATERIAL_SLOT_NAMES:
        mat["materialSlotName"] = MATERIAL_SLOT_NAMES[name]     # jméno slotu pro baseColorConfigurations / rimColorConfigurations (exportér ho zapíše do .shapes)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1.0)  # jen viewport solid mode
    return mat


def apply_materials(coll):
    for obj in coll.objects:
        if obj.type != 'MESH':
            continue
        mat_name = "Paint_Green"
        for fragments, candidate in MATERIAL_RULES:
            if any(f in obj.name for f in fragments):
                mat_name = candidate
                break
        obj.data.materials.clear()
        obj.data.materials.append(get_material(mat_name))


def add_platform_wing(coll, name, side, wings_folded):
    """Sklopné křídlo plošiny - rozložené rozšíří plochu pro drony, složené stojí svisle."""
    sy = 1 if side == "L" else -1
    hinge_y = sy * PLATFORM_WIDTH / 2
    collected = []

    # rošt křídla a nosníky pod ním
    collected.append(add_box(
        coll, f"{name}_Deck", (PLATFORM_LEN, WING_WIDTH, PLATFORM_THICK),
        (0, hinge_y + sy * WING_WIDTH / 2, PLATFORM_Z),
    ))
    for t in (0.25, 0.85):
        collected.append(add_box(
            coll, f"{name}_Beam_{t}", (PLATFORM_LEN, 0.07, 0.09),
            (0, hinge_y + sy * WING_WIDTH * t, PLATFORM_Z - PLATFORM_THICK / 2 - 0.045),
        ))
    n_ribs = 7
    for i in range(n_ribs):
        x = -PLATFORM_LEN / 2 + PLATFORM_LEN * i / (n_ribs - 1)
        collected.append(add_box(
            coll, f"{name}_Rib_{i}", (0.06, WING_WIDTH, 0.07),
            (x, hinge_y + sy * WING_WIDTH / 2, PLATFORM_Z - PLATFORM_THICK / 2 - 0.035),
        ))

    # plocha pro drony je otevřená - žádná síť ani zábradlí na okraji křídla

    pivot = bpy.data.objects.new(f"{name}_Pivot", None)
    pivot.empty_display_type = 'PLAIN_AXES'
    pivot.empty_display_size = 0.4
    pivot.location = (0, hinge_y, PLATFORM_Z - PLATFORM_THICK / 2)
    coll.objects.link(pivot)
    bpy.context.view_layer.update()
    for obj in collected:
        obj.parent = pivot
        obj.matrix_parent_inverse = pivot.matrix_world.inverted()
    # sklopení DOLŮ podél boku spodní paluby kolem podélné osy, po zavěšení dílů
    pivot.rotation_euler = (-sy * math.radians(92) * wings_folded, 0, 0)
    return pivot


def clip_z_range(obj, z_min, z_max, margin=50.0):
    """Ořízne mesh objektu do rozsahu Z <z_min, z_max> - odřízne přesah pod spodní
    a nad horní palubou (boolean rozdíl proti dvěma velkým kvádrům)."""
    for is_min, z_bound in ((True, z_min), (False, z_max)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
        cutter = bpy.context.active_object
        cutter.dimensions = (margin * 2, margin * 2, margin)
        cutter.location = (obj.location.x, obj.location.y, z_bound + (-margin / 2 if is_min else margin / 2))
        mod = obj.modifiers.new(name="Clip", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)  # bez explicitního select modifier_apply někdy ořízne nepřesně
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter, do_unlink=True)


def cut_hole(obj, x_range, y_range, z_margin=1.0):
    """Vyřízne v deskovém objektu obdélníkový průchod (boolean rozdíl) - nástup ze schodiště."""
    (x0, x1), (y0, y1) = x_range, y_range
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, obj.location.z))
    cutter = bpy.context.active_object
    cutter.dimensions = (x1 - x0, y1 - y0, z_margin * 2)
    mod = obj.modifiers.new(name="Hole", type='BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.object = cutter
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def build_staircase(coll):
    """Šikmé schody v zadním rohu plošiny - stoupačky mezi dvěma schodnicemi, madlo po boku."""
    total_rise = PLATFORM_Z - DECK_TOP_Z
    step_rise = 0.22
    n_steps = max(3, round(total_rise / step_rise))
    step_rise = total_rise / n_steps
    step_run = 0.24
    total_run = step_run * n_steps

    width = 0.6
    # schody jsou UVNITŘ půdorysu plošiny (ne ve vzduchu za vlekem) a stoupají
    # od zadní hrany dovnitř; posazené na vnitřní stranu od sloupků/vzpěr
    # (ty jsou na y=+-0.95, tl. do 0.06), aby se o konstrukci opíraly a nekřížily ji
    x0 = -PLATFORM_LEN / 2 + 0.1
    x1 = x0 + total_run
    y_center = (PLATFORM_WIDTH / 2 - 0.25) - width / 2 - 0.08

    # schodnice vedou POD nášlapnou hranou schodů, ne jejich středem
    stringer_len = math.hypot(total_run, total_rise)
    angle = math.atan2(total_rise, total_run)
    stringer_drop = 0.14
    for side, sy in (("L", 1), ("R", -1)):
        y = y_center + sy * width / 2
        stringer = add_box(
            coll, f"Stair_Stringer_{side}", (stringer_len, 0.05, 0.1),
            ((x0 + x1) / 2, y, (DECK_TOP_Z + PLATFORM_Z) / 2 - stringer_drop), rot=(0, -angle, 0),
        )
        # schodnice ať nepřečnívá pod spodní palubu ani nad horní
        clip_z_range(stringer, DECK_TOP_Z, PLATFORM_Z)

    # poslední "stupeň" je samotná plošina, proto jen n_steps - 1 fyzických nášlapů
    for i in range(n_steps - 1):
        step_x = x0 + step_run * (i + 1)
        step_z = DECK_TOP_Z + step_rise * (i + 1)
        add_box(coll, f"Stair_Tread_{i}", (step_run + 0.02, width, 0.035), (step_x - step_run / 2, y_center, step_z))

    # zábradlí po vnější straně schodů - u horní paluby zkrácené, ať nad ni nečouhá
    rail_h = 0.55
    y_rail = y_center + width / 2 + 0.03
    for i in range(n_steps + 1):
        t = i / n_steps
        x = x0 + total_run * t
        z = DECK_TOP_Z + total_rise * t
        post_h = min(rail_h, max(0.0, PLATFORM_Z - z))
        if post_h < 0.02:
            continue
        add_cylinder(coll, f"Stair_RailPost_{i}", 0.018, post_h, (x, y_rail, z + post_h / 2), verts=8)
    rail_top = add_box(
        coll, "Stair_RailTop", (stringer_len, 0.03, 0.03),
        ((x0 + x1) / 2, y_rail, (DECK_TOP_Z + PLATFORM_Z) / 2 + rail_h), rot=(0, -angle, 0),
    )
    clip_z_range(rail_top, DECK_TOP_Z, PLATFORM_Z)

    # návratová hodnota: kudy se nastupuje z posledního schodu na plošinu -
    # sem se do plošiny prořízne průchod, jinak by nahoře byla slepá deska
    return (x1 - 0.45, x1 + 0.05), (y_center - width / 2 - 0.03, y_center + width / 2 + 0.03)


def ensure_ibc_asset():
    """Naimportuje herní IBC jednou do vlastní kolekce; na vleku z ní visí jen instance."""
    if IBC_ASSET_COLLECTION in bpy.data.collections:
        return bpy.data.collections[IBC_ASSET_COLLECTION]
    if not hasattr(bpy.ops.import_scene, "fs25_i3d"):
        print("VAROVANI: i3d importer neni aktivni, IBC zustane jen jako prazdny uzel")
        return None
    if not os.path.isfile(IBC_I3D):
        print(f"VAROVANI: herni asset nenalezen: {IBC_I3D}")
        return None

    before = set(bpy.data.objects)
    bpy.ops.import_scene.fs25_i3d(filepath=IBC_I3D)
    imported = [o for o in bpy.data.objects if o not in before]

    asset = bpy.data.collections.new(IBC_ASSET_COLLECTION)  # záměrně nelinkovaná do scény
    keep = [o for o in imported if o.type == 'MESH' and "fertilizerTank_vis" in o.name]
    for obj in imported:
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        if obj in keep:
            obj.parent = None
            asset.objects.link(obj)
        else:
            bpy.data.objects.remove(obj, do_unlink=True)

    # importer si zakládá vlastní kolekci; prázdnou po přesunu dílů zahodíme
    for c in list(bpy.data.collections):
        if c is not asset and not c.objects and not c.children and "liquidTank" in c.name:
            bpy.data.collections.remove(c)

    # počátek instance na střed spodku palety, ať sedí na ložné ploše
    bpy.context.view_layer.update()
    corners = [o.matrix_world @ mathutils.Vector(c) for o in keep for c in o.bound_box]
    center_x = (min(p.x for p in corners) + max(p.x for p in corners)) / 2
    center_y = (min(p.y for p in corners) + max(p.y for p in corners)) / 2
    asset.instance_offset = (center_x, center_y, min(p.z for p in corners))
    return asset


def add_ibc_instances(coll, positions):
    asset = ensure_ibc_asset()
    for name, loc in positions:
        empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0.3
        empty.location = loc
        if asset:
            empty.instance_type = 'COLLECTION'
            empty.instance_collection = asset
        empty["i3dReference"] = IBC_DATA_PATH
        coll.objects.link(empty)


def build():
    coll = clear_collection()

    # Deck (ložná plocha)
    add_box(coll, "Deck", (DECK_LEN, DECK_WIDTH, DECK_THICK), (0, 0, DECK_TOP_Z - DECK_THICK / 2))

    # Rámové nosníky pod plochou
    rail_z = DECK_TOP_Z - DECK_THICK - RAIL_HEIGHT / 2
    add_box(coll, "ChassisRail_L", (DECK_LEN, 0.1, RAIL_HEIGHT), (0, DECK_WIDTH / 2 - 0.15, rail_z))
    add_box(coll, "ChassisRail_R", (DECK_LEN, 0.1, RAIL_HEIGHT), (0, -(DECK_WIDTH / 2 - 0.15), rail_z))

    # Gooseneck + oko tažného zařízení - sklon dopočítaný z výšky korby a závěsu
    drop = rail_z - HITCH_Z
    add_box(
        coll, "Gooseneck", (math.hypot(GOOSENECK_LEN, drop), 0.4, 0.15),
        (DECK_LEN / 2 + GOOSENECK_LEN / 2, 0, (rail_z + HITCH_Z) / 2),
        rot=(0, math.atan2(drop, GOOSENECK_LEN), 0),
    )
    add_cylinder(
        coll, "HitchEye", 0.05, 0.3,
        (DECK_LEN / 2 + GOOSENECK_LEN - 0.2, 0, HITCH_Z), rot=(math.radians(90), 0, 0),
    )

    # Nápravy a kola (tandem)
    HUB_RADIUS = 0.15
    HUB_DEPTH = 0.05
    for i, ax_x in enumerate(AXLE_X, start=1):
        add_cylinder(coll, f"Axle_{i}", 0.06, 2 * TRACK_Y, (ax_x, 0, WHEEL_RADIUS), rot=(math.radians(90), 0, 0))
        for side, sy in (("L", 1), ("R", -1)):
            add_cylinder(
                coll, f"Wheel_{i}{side}", WHEEL_RADIUS, WHEEL_WIDTH,
                (ax_x, sy * TRACK_Y, WHEEL_RADIUS), rot=(math.radians(90), 0, 0),
            )
            add_cylinder(
                coll, f"HubCap_{i}{side}", HUB_RADIUS, HUB_DEPTH,
                (ax_x, sy * (TRACK_Y + WHEEL_WIDTH / 2), WHEEL_RADIUS), rot=(math.radians(90), 0, 0),
            )

    # Blatník jako jeden plech přes obě kola tandemu, na každé straně
    fender_profile = tandem_fender_profile(
        AXLE_X, WHEEL_RADIUS + FENDER_CLEARANCE, WHEEL_RADIUS, skirt_z=WHEEL_RADIUS * 0.45,
    )
    for side, sy in (("L", 1), ("R", -1)):
        add_sheet_shell(
            coll, f"Fender_{side}", fender_profile,
            thickness=0.03, width=WHEEL_WIDTH + 0.12, loc=(0, sy * TRACK_Y, 0),
        )

    # Tandemové zavěšení: vahadlo na čepu rámu, pod ním listové péro a třmeny nad nápravami
    susp_y = TRACK_Y - WHEEL_WIDTH / 2 - 0.06
    rocker_z = WHEEL_RADIUS + 0.26
    spring_z = WHEEL_RADIUS + 0.11
    pivot_bottom = DECK_TOP_Z - DECK_THICK - RAIL_HEIGHT
    for side, sy in (("L", 1), ("R", -1)):
        y = sy * susp_y
        # konzole z rámu dolů k čepu vahadla
        add_box(
            coll, f"SuspBracket_{side}", (0.14, 0.09, pivot_bottom - rocker_z),
            (AXLE_CENTER_X, y, (pivot_bottom + rocker_z) / 2),
        )
        add_cylinder(
            coll, f"SuspPivot_{side}", 0.05, 0.16, (AXLE_CENTER_X, y, rocker_z),
            rot=(math.radians(90), 0, 0), verts=12,
        )
        # vahadlo ze dvou ramen k nápravám
        for i, ax_x in enumerate(AXLE_X, start=1):
            dx = ax_x - AXLE_CENTER_X
            dz = spring_z - rocker_z
            add_box(
                coll, f"SuspArm_{i}{side}", (math.hypot(dx, dz), 0.07, 0.09),
                ((AXLE_CENTER_X + ax_x) / 2, y, (rocker_z + spring_z) / 2),
                rot=(0, math.atan2(-dz, abs(dx)) * (1 if dx > 0 else -1), 0),
            )
            # listové péro nad nápravou + třmen
            add_box(coll, f"SuspLeaf_{i}{side}", (0.5, 0.09, 0.05), (ax_x, y, spring_z))
            add_box(
                coll, f"SuspUBolt_{i}{side}", (0.09, 0.12, spring_z - WHEEL_RADIUS + 0.06),
                (ax_x, y, (spring_z + WHEEL_RADIUS) / 2),
            )

    # Dvě herní IBC nádrže na ose vleku (instance, ne vlastní geometrie)
    add_ibc_instances(coll, [("IBC_1", (-0.72, 0, DECK_TOP_Z)), ("IBC_2", (0.72, 0, DECK_TOP_Z))])


    # Elektrocentrály vpředu a vzadu, také na ose
    def add_generator(name, x):
        gx, gy, gz = GEN_DIMS
        base_z = DECK_TOP_Z
        center_z = base_z + gz / 2

        add_tube_frame(coll, f"{name}_Frame", GEN_DIMS, (x, 0, center_z))

        # kapota uvnitř rámu
        hood = (gx - 0.16, gy - 0.16, gz - 0.28)
        hood_z = base_z + 0.06 + hood[2] / 2
        top_z = hood_z + hood[2] / 2
        add_beveled_box(coll, f"{name}_Hood", hood, (x, 0, hood_z), bevel=0.05, segments=2)
        add_box(coll, f"{name}_Skid", (gx - 0.1, gy - 0.1, 0.06), (x, 0, base_z + 0.03))
        for fy in (gy / 2 - 0.12, -(gy / 2 - 0.12)):  # silentbloky pod skidem
            for fx in (gx / 2 - 0.14, -(gx / 2 - 0.14)):
                add_cylinder(
                    coll, f"{name}_Mount_{fx:.2f}_{fy:.2f}", 0.035, 0.06, (x + fx, fy, base_z + 0.03),
                    verts=10,
                )

        # nasávací mřížka na čele, výdech vzadu, boční žaluzie proti panelu
        add_louvers(
            coll, f"{name}_GrilleFront", (x + hood[0] / 2, 0, hood_z + 0.02),
            (hood[1] - 0.12, hood[2] - 0.14), axis='x', count=7,
        )
        add_louvers(
            coll, f"{name}_GrilleRear", (x - hood[0] / 2, 0, hood_z + 0.02),
            (hood[1] - 0.14, hood[2] - 0.2), axis='x', count=5,
        )
        add_louvers(
            coll, f"{name}_GrilleSide", (x + 0.12, hood[1] / 2, hood_z + 0.04),
            (hood[0] - 0.42, hood[2] - 0.26), axis='y', count=5,
        )

        # ovládací panel na obslužné straně (-Y, stejně jako výpusti IBC)
        panel_y = -hood[1] / 2
        face_y = panel_y - 0.035
        add_box(coll, f"{name}_Panel", (0.46, 0.04, 0.32), (x, panel_y, hood_z + 0.04))

        # kruhový voltmetr se sklem
        add_cylinder(coll, f"{name}_Gauge", 0.05, 0.03, (x - 0.15, face_y, hood_z + 0.12),
                     rot=(math.radians(90), 0, 0), verts=16)
        add_cylinder(coll, f"{name}_GaugeGlass", 0.042, 0.01, (x - 0.15, face_y - 0.02, hood_z + 0.12),
                     rot=(math.radians(90), 0, 0), verts=16)
        # displej motohodin
        add_box(coll, f"{name}_Display", (0.13, 0.02, 0.06), (x + 0.02, face_y, hood_z + 0.13))
        # kontrolky
        for i, (lx, lamp) in enumerate(((0.12, "Lamp_Green"), (0.16, "Lamp_Red"), (0.20, "Lamp_Red"))):
            add_cylinder(coll, f"{name}_{lamp}_{i}", 0.015, 0.02, (x + lx, face_y, hood_z + 0.14),
                         rot=(math.radians(90), 0, 0), verts=10)
        # otočné knoflíky a hlavní vypínač s páčkou
        for i, kx in enumerate((-0.06, 0.0)):
            add_cylinder(coll, f"{name}_Knob_{i}", 0.026, 0.035, (x + kx, face_y, hood_z + 0.02),
                         rot=(math.radians(90), 0, 0), verts=12)
        add_cylinder(coll, f"{name}_Switch", 0.035, 0.03, (x + 0.09, face_y, hood_z + 0.02),
                     rot=(math.radians(90), 0, 0), verts=12)
        add_box(coll, f"{name}_SwitchLever", (0.06, 0.03, 0.018), (x + 0.09, face_y - 0.02, hood_z + 0.02))
        # nouzový stop
        add_cylinder(coll, f"{name}_EStopBase", 0.045, 0.02, (x + 0.18, face_y, hood_z + 0.02),
                     rot=(math.radians(90), 0, 0), verts=12)
        add_cylinder(coll, f"{name}_EStop", 0.035, 0.035, (x + 0.18, face_y - 0.02, hood_z + 0.02),
                     rot=(math.radians(90), 0, 0), verts=12)
        # zásuvky 230 V a jedna CEE 400 V + jističe
        for i, sx in enumerate((-0.16, -0.08)):
            add_cylinder(coll, f"{name}_Socket_{i}", 0.038, 0.04, (x + sx, face_y, hood_z - 0.09),
                         rot=(math.radians(90), 0, 0), verts=12)
        add_cylinder(coll, f"{name}_SocketCEE", 0.055, 0.06, (x + 0.02, face_y, hood_z - 0.09),
                     rot=(math.radians(90), 0, 0), verts=12)
        for i, bx in enumerate((0.13, 0.18)):
            add_box(coll, f"{name}_Breaker_{i}", (0.03, 0.03, 0.07), (x + bx, face_y, hood_z - 0.09))

        # palivové hrdlo s nálevkou a víčkem, vedle stavoznak
        neck_x = x + hood[0] / 2 - 0.18
        add_cylinder(coll, f"{name}_FuelNeck", 0.062, 0.07, (neck_x, -0.14, top_z + 0.03), verts=14)
        add_cylinder(coll, f"{name}_FuelFunnel", 0.105, 0.06, (neck_x, -0.14, top_z + 0.09), verts=14)
        add_cylinder(coll, f"{name}_FuelCap", 0.07, 0.035, (neck_x, -0.14, top_z + 0.13), verts=14)
        add_box(coll, f"{name}_FuelGauge", (0.05, 0.09, 0.02), (neck_x - 0.16, -0.14, top_z + 0.01))

        # tlumič výfuku podél stroje s koncovkou trčící dozadu a tepelným štítem
        muff_x = x - 0.06
        muff_y = 0.17
        muff_z = top_z + 0.09
        add_cylinder(coll, f"{name}_Muffler", 0.075, 0.5, (muff_x, muff_y, muff_z),
                     rot=(0, math.radians(90), 0), verts=14)
        add_cylinder(coll, f"{name}_MufflerCapF", 0.078, 0.02, (muff_x + 0.25, muff_y, muff_z),
                     rot=(0, math.radians(90), 0), verts=14)
        add_cylinder(coll, f"{name}_MufflerCapR", 0.078, 0.02, (muff_x - 0.25, muff_y, muff_z),
                     rot=(0, math.radians(90), 0), verts=14)
        add_box(coll, f"{name}_HeatShield", (0.44, 0.19, 0.02), (muff_x, muff_y, muff_z + 0.1))
        for sx in (0.16, -0.16):  # stojánky tlumiče na kapotě
            add_box(coll, f"{name}_MufflerBracket_{sx:.2f}", (0.03, 0.04, 0.1),
                    (muff_x + sx, muff_y, top_z + 0.04))
        # svod z motoru nahoru do tlumiče a koncovka dozadu
        add_cylinder(coll, f"{name}_DownPipe", 0.04, 0.12, (muff_x + 0.12, muff_y, top_z + 0.02), verts=12)
        add_cylinder(coll, f"{name}_TailPipe", 0.042, 0.26, (muff_x - 0.38, muff_y, muff_z),
                     rot=(0, math.radians(90), 0), verts=12)
        add_cylinder(coll, f"{name}_TailTip", 0.05, 0.05, (muff_x - 0.5, muff_y, muff_z),
                     rot=(0, math.radians(90), 0), verts=12)

    # oba agregáty vpředu, ať je zadní roh u schodů volný
    add_generator("Generator_Front", 2.6)
    add_generator("Generator_Rear", 3.65)

    # Svislé vzpěry v rozích plošiny
    # Svislé sloupky po obou stranách (víc než jen rohy, ať drží dlouhou plošinu)
    strut_h = PLATFORM_Z - DECK_TOP_Z
    n_posts = 4
    post_xs = []
    span = PLATFORM_LEN - 0.5
    for i in range(n_posts):
        post_xs.append(-PLATFORM_LEN / 2 + 0.25 + span * i / (n_posts - 1))

    side_ys = (PLATFORM_WIDTH / 2 - 0.25, -(PLATFORM_WIDTH / 2 - 0.25))
    idx = 0
    for sy in side_ys:
        for sx in post_xs:
            idx += 1
            add_box(
                coll, f"Strut_{idx}", (0.12, 0.12, strut_h),
                (sx, sy, DECK_TOP_Z + strut_h / 2),
            )

    # Křížové vzpěry (X) mezi sousedními sloupky na každé straně
    brace_idx = 0
    for sy in side_ys:
        for i in range(n_posts - 1):
            x0, x1 = post_xs[i], post_xs[i + 1]
            dx = x1 - x0
            brace_len = math.sqrt(dx ** 2 + strut_h ** 2)
            angle = math.atan2(dx, strut_h)
            mid_x = (x0 + x1) / 2
            mid_z = DECK_TOP_Z + strut_h / 2
            brace_idx += 1
            add_box(
                coll, f"Brace_{brace_idx}A", (0.06, 0.06, brace_len),
                (mid_x, sy, mid_z), rot=(0, angle, 0),
            )
            brace_idx += 1
            add_box(
                coll, f"Brace_{brace_idx}B", (0.06, 0.06, brace_len),
                (mid_x, sy, mid_z), rot=(0, -angle, 0),
            )

    # Plošina pro drony
    platform = add_box(coll, "Platform", (PLATFORM_LEN, PLATFORM_WIDTH, PLATFORM_THICK), (0, 0, PLATFORM_Z))

    # Sklopná křídla - rozložená rozšíří plochu pro drony
    add_platform_wing(coll, "Wing_L", "L", WINGS_FOLDED)
    add_platform_wing(coll, "Wing_R", "R", WINGS_FOLDED)

    # plocha pro drony je otevřená - žádná síť na čelech plošiny, zábradlí jen u schodiště

    # Schody v zadním rohu, šikmé, se schodnicemi a zábradlím - ne žebřík
    opening_x, opening_y = build_staircase(coll)
    # bez tohohle průchodu by byla plošina nad schody slepá deska
    cut_hole(platform, opening_x, opening_y)

    apply_materials(coll)

    bpy.context.view_layer.update()
    print(f"Trailer built: {len(coll.objects)} objects in '{COLLECTION_NAME}'")


if __name__ == "__main__":
    build()
