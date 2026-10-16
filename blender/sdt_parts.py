"""Společné stavební díly vleků (build_trailer3.py, build_trailer_middle.py).

Každý díl je samostatný objekt s měřítkem 1 a vlastním počátkem, zavěšený pod kořenový empty
aktuálního vleku (begin()). Osa vleku: přední část na -Y, Z nahoru, počátek na zemi.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decal_layout as L  # noqa: E402
import brand_layout as BL  # noqa: E402

MATERIALS = {
    "SDT_Frame": ((0.025, 0.025, 0.028), 0.6, 0.45),
    "SDT_DeckWood": ((0.52, 0.40, 0.26), 0.0, 0.8),
    "SDT_TopDeck": ((0.82, 0.82, 0.80), 0.0, 0.6),
    "SDT_TankWhite": ((0.88, 0.88, 0.84), 0.0, 0.35),
    "SDT_TankBlack": ((0.03, 0.03, 0.03), 0.0, 0.5),
    "SDT_Rubber": ((0.015, 0.015, 0.015), 0.0, 0.9),
    "SDT_Rim": ((0.05, 0.05, 0.05), 0.8, 0.35),
    "SDT_RimPaint": ((0.62, 0.63, 0.65), 0.6, 0.35),
    "SDT_NutIndicator": ((0.95, 0.42, 0.02), 0.0, 0.4),
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
    "SDT_NavLed": ((0.55, 0.55, 0.55), 0.0, 0.15),
    "SDT_PaintWhite": ((0.92, 0.92, 0.92), 0.0, 0.5),
    "SDT_PaintDark": ((0.06, 0.065, 0.07), 0.0, 0.7),
    "SDT_BatteryGrey": ((0.06, 0.06, 0.065), 0.1, 0.5),
    "SDT_ChargerGrey": ((0.16, 0.165, 0.17), 0.2, 0.45),
    "SDT_LedGreen": ((0.05, 0.85, 0.12), 0.0, 0.2),
    "SDT_Screen": ((0.02, 0.07, 0.14), 0.0, 0.1),
    "SDT_ScreenOff": ((0.006, 0.007, 0.009), 0.0, 0.08),
    "SDT_CastIron": ((0.03, 0.03, 0.032), 0.3, 0.55),
    "SDT_PaintRed": ((0.60, 0.02, 0.02), 0.0, 0.4),
    "SDT_PaintYellow": ((0.90, 0.68, 0.03), 0.0, 0.4),
    "SDT_Plastic": ((0.03, 0.03, 0.03), 0.0, 0.5),
    "SDT_Decal": ((1.0, 1.0, 1.0), 0.0, 0.45),
    "SDT_TankPE": ((0.86, 0.87, 0.84), 0.0, 0.5),
    "SDT_Brass": ((0.78, 0.56, 0.20), 0.9, 0.35),
    "SDT_Alu": ((0.72, 0.74, 0.76), 0.85, 0.5),
    "SDT_PumpBlue": ((0.04, 0.16, 0.42), 0.1, 0.4),
    "SDT_ValveBlue": ((0.06, 0.28, 0.75), 0.0, 0.4),
    "SDT_Canister": ((0.90, 0.90, 0.88), 0.0, 0.45),
    "SDT_CrateGreen": ((0.045, 0.30, 0.12), 0.1, 0.45),
    "SDT_TarpGreen": ((0.035, 0.23, 0.095), 0.0, 0.85),
    # plachta (brand_layout.TARP_*): plachtovina #4a4f55, lemy #373b40, popruhy #24272a; design ji nemění
    "SDT_Tarp": ((0.0685, 0.0782, 0.0908), 0.0, 0.9),
    "SDT_TarpHem": ((0.0382, 0.0437, 0.0513), 0.0, 0.9),
    "SDT_TarpStrap": ((0.0176, 0.0204, 0.0232), 0.0, 0.85),
    # polepy značky z atlasu sdt_brand (průhlednost); barva se nepatrně liší od SDT_Decal, ať je konvertor exportéru nesloučí
    "SDT_BrandDecal": ((1.0, 1.0, 0.995), 0.0, 0.44),
}
BRAND_DECAL_MATERIALS = ("SDT_BrandDecal",)
DECAL_MATERIALS = ("SDT_Decal",) + BRAND_DECAL_MATERIALS     # UV0 v atlasu (build_dirt_uvs je neposouvá)
_TEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
DECAL_ATLAS = os.path.join(_TEX_DIR, L.ATLAS_PNG)
BRAND_ATLAS = os.path.join(_TEX_DIR, BL.ATLAS_PNG)

_coll = None
_root = None


def begin(collection_name, root_name):
    """Vyprázdní (nebo založí) kolekci vleku a vytvoří v ní kořenový empty."""
    global _coll, _root
    coll = bpy.data.collections.get(collection_name)
    if coll:
        for o in list(coll.objects):
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
    else:
        coll = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(coll)
    _coll = coll
    _root = bpy.data.objects.new(root_name, None)
    _root.empty_display_type = "PLAIN_AXES"
    coll.objects.link(_root)
    return coll, _root


# materiály, které hra přebarvuje podle jména slotu (materialSlotName v XML): barva bedny Mini, barva plachet a vrat Middle/Max
# a barva ráfků; exportér slot zapíše do .shapes
MATERIAL_SLOT_NAMES = {"SDT_CrateGreen": "SDT_CrateGreen", "SDT_Tarp": "SDT_Tarp", "SDT_RimPaint": "rim_outer_mat"}


def material(name):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    color, metallic, roughness = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    if name in MATERIAL_SLOT_NAMES:
        mat["materialSlotName"] = MATERIAL_SLOT_NAMES[name]
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1.0)
    if name in DECAL_MATERIALS:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(BRAND_ATLAS if name in BRAND_DECAL_MATERIALS else DECAL_ATLAS, check_existing=True)
        uvn = mat.node_tree.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UVMap"
        mat.node_tree.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if name in BRAND_DECAL_MATERIALS:
            mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return mat


def planar_uv(obj, origin, u_axis, v_axis, width, height, region, sub=None):
    """UV0 (první vrstva) z roviny do oblasti atlasu nálepek: origin = levý dolní roh ve světě, osy u/v ve světě.
    Boční stěny tenké krabičky spadnou na okraj oblasti."""
    u0, v0, u1, v1 = L.uv_rect(region, sub)
    origin, u_axis, v_axis = Vector(origin), Vector(u_axis).normalized(), Vector(v_axis).normalized()
    me = obj.data
    mw = obj.matrix_world
    uv = me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        p = mw @ me.vertices[loop.vertex_index].co - origin
        s = min(max(p.dot(u_axis) / width, 0.0), 1.0)
        t = min(max(p.dot(v_axis) / height, 0.0), 1.0)
        uv.data[loop.index].uv = (u0 + (u1 - u0) * s, v0 + (v1 - v0) * t)


def decal_quad(name, corner, u_axis, v_axis, width, height, region, sub=None, offset=0.0015, mat="SDT_Decal"):
    """Nálepka jako tenký čtyřúhelník nad povrchem (normála = u × v míří ven), UV do atlasu, decalLayer 1."""
    c, u, v = Vector(corner), Vector(u_axis).normalized(), Vector(v_axis).normalized()
    n = u.cross(v).normalized()
    c = c + n * offset
    center = c + u * width / 2 + v * height / 2
    bm = bmesh.new()
    vs = [bm.verts.new(p - center) for p in (c, c + u * width, c + u * width + v * height, c + v * height)]
    bm.faces.new(vs)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    _coll.objects.link(obj)
    obj.data.materials.append(material(mat))
    obj.parent = _root
    obj.matrix_world = Matrix.Translation(center)
    planar_uv(obj, c, u, v, width, height, region, sub)
    obj["i3D_decalLayer"] = 1
    obj["i3D_castsShadows"] = False
    return obj


def conform_decal(name, target, center, normal, up, width, height, region, offset=0.0015, cols=10, rows=3):
    """Nálepka přitisknutá na zakřivený povrch target: mřížka v rovině (center, normal) se promítne paprsky
    proti normále na povrch a odsadí o offset po normále povrchu."""
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(target, dg)
    inv = target.matrix_world.inverted()
    n, up = Vector(normal).normalized(), Vector(up).normalized()
    u = up.cross(n).normalized()
    v = n.cross(u).normalized()
    center = Vector(center)
    corner = center - u * width / 2 - v * height / 2
    bm = bmesh.new()
    grid = []
    for j in range(rows + 1):
        row = []
        for i in range(cols + 1):
            p = corner + u * (width * i / cols) + v * (height * j / rows)
            start = inv @ (p + n * 0.3)
            d = (inv.to_3x3() @ -n).normalized()
            hit, hn, _, _ = bvh.ray_cast(start, d, 1.0)
            if hit is None:
                raise RuntimeError(f"{name}: nálepka míjí {target.name}")
            w = target.matrix_world @ hit
            wn = (target.matrix_world.to_3x3() @ hn).normalized()
            if wn.dot(n) < 0:
                wn = -wn
            row.append(bm.verts.new(w + wn * offset - center))
        grid.append(row)
    for j in range(rows):
        for i in range(cols):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    _coll.objects.link(obj)
    obj.data.materials.append(material("SDT_Decal"))
    obj.parent = _root
    obj.matrix_world = Matrix.Translation(center)
    uvl = me.uv_layers.new(name="UVMap")
    u0, v0, u1, v1 = L.uv_rect(region)
    for loop in me.loops:
        k = loop.vertex_index
        i, j = k % (cols + 1), k // (cols + 1)
        uvl.data[loop.index].uv = (u0 + (u1 - u0) * i / cols, v0 + (v1 - v0) * j / rows)
    obj["i3D_decalLayer"] = 1
    obj["i3D_castsShadows"] = False
    return obj


def _box_uv(bm, scale=1.0):
    """Krabicová projekce 1 UV = 1 m: detailní textury vehicleShaderu potřebují UV, jinak jsou rozmazané."""
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        for loop in f.loops:
            co = loop.vert.co
            loop[uv].uv = (co[a] * scale, co[b] * scale)


def _finish(name, bm, matrix, mat, smooth_quads=False):
    if smooth_quads:
        for f in bm.faces:
            f.smooth = len(f.verts) == 4
    bm.normal_update()
    _box_uv(bm)
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


def loft_y(name, stations, mat, x=0.0, segments=20):
    """Těleso vytažené podél Y přes průřezy [(y, polovina šířky, z dole, z nahoře, mocnina superelipsy)]."""
    bm = bmesh.new()
    rings = []
    for y, hw, z0, z1, pw in stations:
        zc, hh, e = (z0 + z1) / 2, (z1 - z0) / 2, 2.0 / pw
        ring = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            c, s = math.cos(a), math.sin(a)
            ring.append(bm.verts.new((x + hw * math.copysign(abs(c) ** e, c), y, zc + hh * math.copysign(abs(s) ** e, s))))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.smooth = True
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, Matrix.Identity(4), mat)


def ring_z(name, center, r_in, r_out, height, mat, segments=48):
    """Plochý mezikruh (hranol) s osou Z, střed výšky v center."""
    bm = bmesh.new()
    h = height / 2
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments), z))
              for i in range(segments)] for r, z in ((r_out, h), (r_in, h), (r_in, -h), (r_out, -h))]
    for k in range(4):
        a, b = rings[k], rings[(k + 1) % 4]
        for i in range(segments):
            j = (i + 1) % segments
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, Matrix.Translation(center), mat)


def group(name, objs, matrix=None):
    """Prázdný uzel v počátku, pod který se díly zavěsí se zachovanou polohou; pak se celý posune maticí."""
    g = empty(name, (0, 0, 0))
    for o in objs:
        w = o.matrix_world.copy()
        o.parent = g
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_world = w
    if matrix is not None:
        g.matrix_world = matrix
    return g


# délka (X, konektor na -X), šířka (Y), tloušťka (Z): S = DB800 (T25), M = DB1560 (T50), L = DB2160 (T100)
BATTERY_SIZES = {"S": (0.30, 0.19, 0.11), "M": (0.37, 0.23, 0.13), "L": (0.41, 0.25, 0.145)}
BATTERY_SIZE = BATTERY_SIZES["M"]     # rámec slotů (všechny sloty se počítají pro M)


def battery_frame_offset(size):
    """Posun středu baterie dané velikosti v rámci slotu (x podél délky, z tloušťka): konektor leží tam, kde
    konektor M, a střed tloušťky tam, kde střed tloušťky M."""
    return size[0] / 2 - BATTERY_SIZE[0] / 2, (BATTERY_SIZE[2] - size[2]) / 2


def chamfer_box(name, x0, x1, y0, y1, z0, z1, mat, ch):
    """Kvádr se zkosenými všemi hranami (zkosení ch)."""
    size = Vector((abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))
    center = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*size, 1.0)))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=ch, offset_type="OFFSET", segments=1, profile=0.5, affect="EDGES")
    return _finish(name, bm, Matrix.Translation(center), mat)


def battery(name, size=BATTERY_SIZE):
    """Baterie podle DJI DB800 / DB1560 / DB2160: černý zkosený blok, konektor na čele -X (deska se 5 kontakty, dva
    šrouby, patky), na čele +X oranžový štítek s diodami a madlo (baterie se do nabíječky i dronu zasouvá
    konektorem napřed a nese se za madlo), na bocích větrací štěrbiny a pojistná lišta.

    Jeden mesh (díly sloučené, materiály jako sloty). Rámec slotu = rámec M: u M je počátek uprostřed dole,
    menší a větší baterie jsou posunuté podle battery_frame_offset, takže ve stejném slotu sedí konektorem
    na stejném místě.
    """
    lx, ly, lz = size[0] / 2, size[1] / 2, size[2]
    fx, fy, fz = (s / m for s, m in zip(size, BATTERY_SIZE))
    hz = lz / 2
    parts = [chamfer_box(f"{name}_Body", -lx, lx, -ly, ly, 0.0, lz, "SDT_BatteryGrey", 0.008)]
    label_a = box(f"{name}_LabelA", -0.12 * fx, 0.12 * fx, ly, ly + 0.002, 0.025 * fz, 0.09 * fz, "SDT_Decal")
    label_b = box(f"{name}_LabelB", -0.12 * fx, 0.12 * fx, -ly - 0.002, -ly, 0.025 * fz, 0.09 * fz, "SDT_Decal")
    parts += [label_a, label_b]
    parts += [
        # horní kryt a pojistné lišty na bocích
        box(f"{name}_Top", -lx * 0.86, lx * 0.80, -ly * 0.84, ly * 0.84, lz - 0.003, lz + 0.003, "SDT_TankBlack"),
        box(f"{name}_RailA", -lx * 0.78, lx * 0.62, ly, ly + 0.005, 0.62 * lz, 0.72 * lz, "SDT_TankBlack"),
        box(f"{name}_RailB", -lx * 0.78, lx * 0.62, -ly - 0.005, -ly, 0.62 * lz, 0.72 * lz, "SDT_TankBlack"),
        # čelo +X: oranžový štítek, diody a madlo na dvou sloupcích
        box(f"{name}_EndPlate", lx, lx + 0.004, -0.55 * ly, 0.55 * ly, 0.58 * lz, 0.82 * lz, "SDT_GenOrange"),
        box(f"{name}_Leds", lx, lx + 0.003, -0.55 * ly, 0.55 * ly, 0.20 * lz, 0.30 * lz, "SDT_LedGreen"),
        chamfer_box(f"{name}_HandlePostA", lx, lx + 0.026, -0.86 * ly, -0.62 * ly, hz - 0.14 * lz, hz + 0.14 * lz,
                    "SDT_TankBlack", 0.004),
        chamfer_box(f"{name}_HandlePostB", lx, lx + 0.026, 0.62 * ly, 0.86 * ly, hz - 0.14 * lz, hz + 0.14 * lz,
                    "SDT_TankBlack", 0.004),
        tube(f"{name}_HandleBar", (lx + 0.022, -0.74 * ly, hz), (lx + 0.022, 0.74 * ly, hz), 0.011, "SDT_Rubber",
             segments=10),
        # čelo -X: konektorová deska s pěti kontakty, dvě patky
        chamfer_box(f"{name}_Connector", -lx - 0.012, -lx, -0.55 * ly, 0.55 * ly, hz - 0.30 * lz, hz + 0.30 * lz,
                    "SDT_TankBlack", 0.003),
        box(f"{name}_ConnectorFrame", -lx - 0.014, -lx - 0.012, -0.44 * ly, 0.44 * ly, hz - 0.22 * lz, hz + 0.22 * lz,
            "SDT_Mesh"),
        box(f"{name}_FootA", -lx - 0.010, -lx, -0.92 * ly, -0.70 * ly, 0.0, 0.16 * lz, "SDT_TankBlack"),
        box(f"{name}_FootB", -lx - 0.010, -lx, 0.70 * ly, 0.92 * ly, 0.0, 0.16 * lz, "SDT_TankBlack"),
    ]
    for i in range(5):
        py = (i - 2) * 0.17 * ly
        parts.append(box(f"{name}_Pin{i}", -lx - 0.018, -lx - 0.014, py - 0.006, py + 0.006, hz - 0.13 * lz,
                         hz + 0.13 * lz, "SDT_Steel"))
    for i in range(5):  # větrací štěrbiny na obou bocích u čela +X
        z0 = (0.18 + 0.11 * i) * lz
        parts.append(box(f"{name}_VentA{i}", lx * 0.74, lx * 0.94, ly, ly + 0.002, z0, z0 + 0.05 * lz, "SDT_Mesh"))
        parts.append(box(f"{name}_VentB{i}", lx * 0.74, lx * 0.94, -ly - 0.002, -ly, z0, z0 + 0.05 * lz, "SDT_Mesh"))
    key = next(k for k, s in BATTERY_SIZES.items() if tuple(s) == tuple(size))
    lw, lh, lz0 = 0.24 * fx, 0.065 * fz, 0.025 * fz
    planar_uv(label_a, (0.12 * fx, ly, lz0), (-1, 0, 0), (0, 0, 1), lw, lh, "battery" + key)
    planar_uv(label_b, (-0.12 * fx, -ly, lz0), (1, 0, 0), (0, 0, 1), lw, lh, "battery" + key)
    dx, dz = battery_frame_offset(size)
    return merge(name, parts, Matrix.Translation((dx, 0.0, dz)))


def merge(name, objs, matrix=None):
    """Sloučí díly do jednoho meshe (materiály jako sloty) s počátkem v počátku scény, díly smaže.
    matrix se použije na vrcholy (posun geometrie vůči počátku)."""
    bm = bmesh.new()
    mats = []
    for o in objs:
        me = o.data.copy()
        me.transform(o.matrix_world if matrix is None else matrix @ o.matrix_world)
        mat = o.data.materials[0]
        if mat not in mats:
            mats.append(mat)
        n = len(bm.faces)
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n:]:
            f.material_index = mats.index(mat)
        bpy.data.meshes.remove(me)
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    _coll.objects.link(obj)
    obj.parent = _root
    obj.matrix_world = Matrix.Identity(4)
    return obj


def hermite_path(pts, tangents=None, samples=10):
    """Hladká křivka body pts (Catmull-Rom); tangents = {index: vektor} přepíše tečnu v bodě."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    tan = []
    for i in range(n):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        t = (b - a) / (2 if 0 < i < n - 1 else 1)
        if tangents and i in tangents:
            t = Vector(tangents[i]).normalized() * t.length
        tan.append(t)
    out = [pts[0]]
    for i in range(n - 1):
        p0, p1, m0, m1 = pts[i], pts[i + 1], tan[i], tan[i + 1]
        for k in range(1, samples + 1):
            s = k / samples
            h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
            out.append(h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1)
    return out


def path_length(path):
    return sum((b - a).length for a, b in zip(path, path[1:]))


def resample(path, count):
    """count + 1 bodů po křivce ve stejných rozestupech po délce."""
    total = path_length(path)
    out, acc, i = [path[0].copy()], 0.0, 0
    for k in range(1, count):
        target = total * k / count
        while acc + (path[i + 1] - path[i]).length < target:
            acc += (path[i + 1] - path[i]).length
            i += 1
        seg = path[i + 1] - path[i]
        out.append(path[i] + seg * ((target - acc) / seg.length))
    out.append(path[-1].copy())
    return out


def sweep(name, path, radius, mat, segments=10):
    """Trubka (hadice, kabel) po hustě vzorkované křivce, rámy paralelním přenosem, zavřené konce.
    Počátek v prvním bodě."""
    path = [Vector(p) for p in path]
    origin = path[0]
    tangents = []
    for i in range(len(path)):
        a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        tangents.append((b - a).normalized())
    ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
    normal = (ref - tangents[0] * ref.dot(tangents[0])).normalized()
    bm = bmesh.new()
    rings = []
    for i, (p, t) in enumerate(zip(path, tangents)):
        if i:
            normal = (normal - t * normal.dot(t)).normalized()
        binormal = t.cross(normal)
        rings.append([bm.verts.new(p - origin + radius * (math.cos(a) * normal + math.sin(a) * binormal))
                      for a in (2 * math.pi * k / segments for k in range(segments))])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(segments):
            j = (k + 1) % segments
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.smooth = True
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _finish(name, bm, Matrix.Translation(origin), mat)


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


# ---------------------------------------------------------------- složené díly

def railing(prefix, pts, z_base, height, r=0.022, mid=True, post_every=1.2):
    """Trubkové zábradlí po lomené čáře pts=[(x,y)] stojící na výšce z_base."""
    z_top = z_base + height
    z_mid = z_base + height / 2
    k = 0
    for a, b in zip(pts, pts[1:]):
        a3, b3 = Vector((*a, 0)), Vector((*b, 0))
        tube(f"{prefix}_Top{k}", (a[0], a[1], z_top), (b[0], b[1], z_top), r, "SDT_Frame", segments=10)
        if mid:
            tube(f"{prefix}_Mid{k}", (a[0], a[1], z_mid), (b[0], b[1], z_mid), r * 0.8, "SDT_Frame", segments=10)
        n = max(1, round((b3 - a3).length / post_every))
        for j in range(n + (1 if k == len(pts) - 2 else 0)):
            p = a3.lerp(b3, j / n)
            tube(f"{prefix}_Post{k}_{j}", (p.x, p.y, z_base), (p.x, p.y, z_top), r, "SDT_Frame", segments=10)
        k += 1


def generator(prefix, gx, gy, z):
    """DJI multifunkční generátor/nabíječka v trubkové kleci, 0,72 x 0,86 x 0,78 m."""
    box(f"{prefix}_Body", gx - 0.33, gx + 0.33, gy - 0.40, gy + 0.40, z + 0.05, z + 0.72, "SDT_GenOrange")
    for cx in (gx - 0.36, gx + 0.36):
        for cy in (gy - 0.43, gy + 0.43):
            tube(f"{prefix}_Cage_{cx:+.2f}_{cy:+.2f}", (cx, cy, z), (cx, cy, z + 0.78), 0.018, "SDT_Frame",
                 segments=8)
    for cx in (gx - 0.36, gx + 0.36):
        tube(f"{prefix}_CageTop_{cx:+.2f}", (cx, gy - 0.43, z + 0.78), (cx, gy + 0.43, z + 0.78), 0.018,
             "SDT_Frame", segments=8)


def leg_tank(prefix, y, z, radius, length, band_offsets, saddle_offsets, saddle_half_w):
    """Ležatá nádrž na sedlech (bez popruhů), osa podél vleku, na středu šířky. band_offsets se nepoužívá."""
    zc = z + 0.12 + radius
    capsule(prefix, (0, y, zc), radius, length, "Y", "SDT_TankWhite")
    for i, dy in enumerate(saddle_offsets):
        box(f"{prefix}_Saddle{i}", -saddle_half_w, saddle_half_w, y + dy - 0.06, y + dy + 0.06, z, z + 0.35,
            "SDT_Frame")
    cylinder_z(f"{prefix}_Lid", (0, y, zc + radius + 0.03), 0.20 if radius > 0.5 else 0.14, 0.08,
               "SDT_TankWhite")


def cone_tank(prefix, x, y, z, radius, stand_h=0.45, cone_h=0.40, body_h=0.80):
    """Indukční nádrž s kuželovým dnem na černém stojanu."""
    half = radius - 0.02
    box(f"{prefix}_Stand", x - half, x + half, y - half, y + half, z, z + stand_h, "SDT_TankBlack")
    cylinder_z(f"{prefix}_Cone", (x, y, z + stand_h + cone_h / 2), 0.06, cone_h, "SDT_TankBlack", radius_top=radius)
    zb = z + stand_h + cone_h
    cylinder_z(f"{prefix}_Body", (x, y, zb + body_h / 2), radius, body_h, "SDT_TankWhite")
    cylinder_z(f"{prefix}_Lid", (x, y, zb + body_h + 0.05), radius * 0.375, 0.10, "SDT_TankBlack")
    return zb + body_h


def pump(prefix, px, py, z):
    """Čerpadlo 2" s benzínovým motorem na stojanu."""
    box(f"{prefix}_Stand", px - 0.25, px + 0.25, py - 0.20, py + 0.20, z, z + 0.25, "SDT_Frame")
    box(f"{prefix}_Engine", px - 0.20, px + 0.12, py - 0.18, py + 0.18, z + 0.25, z + 0.58, "SDT_EngineRed")
    cylinder_x(f"{prefix}_Housing", (px + 0.22, py, z + 0.42), 0.14, 0.18, "SDT_TankBlack")


def hose_reel(prefix, rx, ry, rz, bracket_x, top_z, hose_mat, radius=0.22):
    """Hadicový naviják s osou po X, zavěšený na konzole pod plošinou."""
    cylinder_x(f"{prefix}_Drum", (rx, ry, rz), radius, 0.20, hose_mat)
    for dx in (-0.11, 0.11):
        cylinder_x(f"{prefix}_Flange{dx:+.2f}", (rx + dx, ry, rz), radius + 0.06, 0.015, "SDT_Frame")
    box(f"{prefix}_Bracket", bracket_x, rx + 0.12, ry - 0.04, ry + 0.04, rz, top_z, "SDT_Frame")


def reflective_tape(prefix, x_out, sx, y0, y1, z0, z1, seg=0.30, gap=0.02):
    y, i = y0, 0
    while y + seg <= y1:
        xf = x_out + sx * 0.002
        box(f"{prefix}_{i:02d}", xf, xf + sx * 0.002, y, y + seg, z0, z1,
            "SDT_TapeRed" if i % 2 == 0 else "SDT_TapeWhite")
        y += seg + gap
        i += 1


def drone_parts(prefix, collection="SprayDrone"):
    coll = bpy.data.collections.get(collection)
    return [o for o in coll.all_objects if o.name.startswith(prefix)] if coll else []


def drone_footprint(objs):
    mn = Vector((1e9,) * 3)
    mx = -mn
    for o in objs:
        if o.type == "MESH":
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mn = Vector(map(min, mn, w))
                mx = Vector(map(max, mx, w))
    return Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))


def transform_hierarchy(objs, prefix, xf):
    """Přenese celou hierarchii dílů dronu maticí xf (hýbe jen s kořeny, děti jdou s nimi)."""
    for o in objs:
        if o.parent is None or not o.parent.name.startswith(prefix):
            o.matrix_world = xf @ o.matrix_world


# ---------------------------------------------------------------- polepy značky (atlas sdt_brand, konfigurace Design)
#
# Každý design má vlastní sadu polepů. Polepy jednoho designu na jednom místě visí pod uzlem brand_<KEY>_<místo>
# (brand_layout.brand_node_name), např. brand_BZUK_tarpL, brand_ROSA_tarpL ... Export (export_middle_mod) tyto uzly sám
# přidá do i3dMappings, nevýchozí designy v i3d skryje a vyplní zástupce {{DESIGN_CONFIGURATIONS}} (objectChange
# visibilityActive/Inactive na všech uzlech designu). Polep na pohyblivém dílu (plachta, panel bedny) = uzel pod tím dílem.

def i3d_vec(v):
    """Blender (Z nahoru, vpřed -Y) -> i3d (Y nahoru, vpřed +Z), jako export_middle_mod.b2i."""
    return Vector((v[0], v[2], -v[1]))


def i3d_fmt(v):
    return " ".join("%g" % (0.0 if abs(c) < 5e-7 else round(c, 4)) for c in v)


def _keep_world(obj, parent):
    """Zavěsí obj pod parent se zachovanou polohou ve světě (matrix_parent_inverse = I, ať export nic nepřepočítává)."""
    w = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = w
    return obj


def _face_frame(normal, up):
    """Osy plochy: u = vpravo při pohledu zvenku (proti normále), v = nahoru, n = ven; u × v = n."""
    n = Vector(normal).normalized()
    v = Vector(up)
    v = (v - n * v.dot(n)).normalized()
    return v.cross(n).normalized(), v, n


def brand_decal(name, design, kind, center, normal, up, width, height=None, parent=None, offset=0.0015, sub=None):
    """Polep značky z atlasu sdt_brand: čtyřúhelník se středem center (ve světě) odsazený o offset po normále.
    kind = lockupOnDark | lockupOnLight | mark | stripe (brand_layout.KINDS), design = BZUK | ROSA | KAPKA | STRATUS.
    height None = podle poměru oblasti (lockup 4 : 1, znak 1 : 1); pruh potřebuje height. up = směr nahoru v rovině polepu
    (čte se zleva doprava při pohledu zvenku). sub = výřez oblasti (fx0, fy0, fx1, fy1). Materiál SDT_BrandDecal
    (alphaBlending ve hře), decalLayer 1, bez stínu. Vrací objekt (počátek ve středu, bez natočení)."""
    region = BL.region_name(kind, design)
    if height is None:
        a = BL.aspect(kind)
        if a is None:
            raise ValueError(f"{name}: pruh potřebuje height")
        height = width / a
    u, v, n = _face_frame(normal, up)
    c = Vector(center) + n * offset
    hw, hh = width / 2, height / 2
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in (-u * hw - v * hh, u * hw - v * hh, u * hw + v * hh, -u * hw + v * hh)]
    f = bm.faces.new(vs)
    u0, v0, u1, v1 = BL.uv_rect(region, sub)
    uvl = bm.loops.layers.uv.new("UVMap")
    for loop, uv in zip(f.loops, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
        loop[uvl].uv = uv
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    _coll.objects.link(obj)
    obj.data.materials.append(material("SDT_BrandDecal"))
    obj.parent = _root
    obj.matrix_world = Matrix.Translation(c)
    obj["i3D_decalLayer"] = 1
    obj["i3D_castsShadows"] = False
    if parent is not None:
        _keep_world(obj, parent)
    return obj


def brand_group(design, place, parent=None, loc=None):
    """Uzel brand_<KEY>_<place> pro polepy jednoho designu (založí, nebo vrátí existující). Nevýchozí design má hide_render,
    ať je v náhledech a obrázku do obchodu vidět jen výchozí BZUK."""
    name = BL.brand_node_name(design, place)
    g = bpy.data.objects.get(name)
    if g is None:
        if loc is None:
            loc = parent.matrix_world.translation if parent is not None else (0, 0, 0)
        g = empty(name, loc)
        g.empty_display_size = 0.05
        if parent is not None:
            _keep_world(g, parent)
        g.hide_render = design != BL.DEFAULT_DESIGN
    return g


def brand_tone_group(place, tone, parent=None, loc=None):
    """Uzel brandTone<tone>_<place> (tone Dark | Light) nad polepy jednoho místa: konfigurace barvy (baseColorConfigurations,
    zástupci {{TONE_DARK}} / {{TONE_LIGHT}} v export_middle_mod.shared_values) ukáže na tmavé barvě sadu lockupOnDark a na světlé
    lockupOnLight. Export ho sám namapuje (sdt_mapped); světlá sada je v náhledech skrytá (hide_render)."""
    name = f"brandTone{tone}_{place}"
    g = bpy.data.objects.get(name)
    if g is None:
        if loc is None:
            loc = parent.matrix_world.translation if parent is not None else (0, 0, 0)
        g = empty(name, loc)
        g.empty_display_size = 0.05
        if parent is not None:
            _keep_world(g, parent)
        g["sdt_mapped"] = 1
        g.hide_render = tone != "Dark"
    return g


def _hide_tree(obj, hidden):
    for o in [obj] + list(obj.children_recursive):
        o.hide_render = o.hide_render or hidden


def brand_decal_set(place, kind, center, normal, up, width, height=None, parent=None, offset=0.0015, tag="",
                    designs=BL.DESIGN_ORDER, sub=None, tone=False):
    """Stejný polep ve všech designech: pro každý KEY objekt Brand<Kind>_<place><tag>_<KEY> pod uzlem brand_<KEY>_<place>
    (brand_group, ten visí pod parent). Více polepů na jednom místě (lockup + pruh) sdílí uzel, liší se kind/tag.
    tone = lockup na ploše, jejíž barvu mění konfigurace (plachta, vrata, bedna Mini): dvě sady pod brand_tone_group -
    lockupOnDark (místo <place>Dark) a lockupOnLight (<place>Light); vrací polepy tmavé sady. Bez podkladu pod polepem.
    Vrací {KEY: objekt polepu}."""
    if tone:
        out = None
        for t, k in (("Dark", "lockupOnDark"), ("Light", "lockupOnLight")):
            tg = brand_tone_group(place, t, parent, center)
            res = brand_decal_set(place + t, k, center, normal, up, width, height, tg, offset, tag, designs, sub)
            if t == "Light":
                for o in res.values():
                    _hide_tree(o, True)
            out = out or res
        return out
    out = {}
    for key in designs:
        g = brand_group(key, place, parent, center)
        o = brand_decal(f"Brand{kind[0].upper()}{kind[1:]}_{place}{tag}_{key}", key, kind, center, normal, up, width, height,
                        g, offset, sub)
        o.hide_render = g.hide_render
        out[key] = o
    return out

# ---------------------------------------------------------------- rolovací plachta
#
# Uzly (jména dává volající; vlastnost sdt_mapped = export je sám přidá do i3dMappings):
#   <name>      prázdný uzel s pivotem na HORNÍ hraně plachty, lokální X podél plachty, Z nahoru. Pod ním mesh <name>_Sheet
#               (plachtovina s lemy, sklady harmoniky, oboustranná) a <name>_Straps (popruhy, spony, háčky); polepy designu
#               se věší pod <name> (brand_decal_set(parent=<name>)). Srolování = měřítko lokální Z, v i3d "1 s 1".
#   <name>Roll  role (válec plachtoviny s poutky popruhů), lokální X = osa role. Jede se spodní hranou plachty: zavřeno leží
#               u spodního lemu zmenšená na ROLL_CLOSED_SCALE, srolováno je pod horní hranou v plné velikosti; v i3d posun
#               a měřítko "1 c c".
# Model se staví ZAVŘENÝ (měřítko plachty 1, role dole zmenšená) - stav složeného vleku, ve kterém hra vozidlo načte
# (startMoveDirection 1) a ve kterém je obrázek do obchodu. Ve foldLadder je čas 0 = rozloženo = srolováno, konec = zavřeno;
# tarp(fold_time=...) uloží hotové řádky <part> do vlastnosti sdt_fold_parts uzlu <name>, export je vyplní do {{TARP_PARTS}}.

TARP_FOLD = (0.006, 0.22)          # amplituda a perioda skladů harmoniky (m)
TARP_DECAL_OFFSET = 0.010          # polep nad plachtou: nad sklady, pod popruhy
TARP_STRAP_OFFSET = 0.016
ROLL_CLOSED_SCALE = 0.3            # role u spodního lemu po zavření (Ø 0,15 -> 0,045 m, vypadá jako spodní trubka)


def _sheet_mesh(name, width, drop_fn, hem, rows, fold, col_step=0.0275):
    """Mřížka plachty v lokálních souřadnicích pivotu (x podél, z dolů, líc míří na +Y, sklady po Y). Lem nahoře i dole
    (SDT_TarpHem), rub 2 mm uvnitř s otočenými normálami (plachta je vidět i zevnitř)."""
    amp, per = fold
    ncol = max(2, int(round(width / col_step)))
    xs = [-width / 2 + width * i / ncol for i in range(ncol + 1)]
    body = max(1, int(round((max(drop_fn(x) for x in xs) - 2 * hem) / rows)))
    bm = bmesh.new()
    grid = []
    for x in xs:
        drop = drop_fn(x)
        zs = [0.0] + [-hem - (drop - 2 * hem) * k / body for k in range(body + 1)] + [-drop]
        y = amp * math.sin(2 * math.pi * (x + width / 2) / per) if amp else 0.0
        grid.append([bm.verts.new((x, y, z)) for z in zs])
    faces = []
    last = len(grid[0]) - 2
    for i in range(ncol):
        a, b = grid[i], grid[i + 1]
        for k in range(len(a) - 1):
            f = bm.faces.new((a[k], b[k], b[k + 1], a[k + 1]))
            f.material_index = 1 if k in (0, last) else 0
            f.smooth = True
            faces.append(f)
    back = bmesh.ops.duplicate(bm, geom=faces)
    bmesh.ops.translate(bm, verts=[g for g in back["geom"] if isinstance(g, bmesh.types.BMVert)], vec=(0, -0.002, 0))
    bmesh.ops.reverse_faces(bm, faces=[g for g in back["geom"] if isinstance(g, bmesh.types.BMFace)])
    _box_uv(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material("SDT_Tarp"))
    me.materials.append(material("SDT_TarpHem"))
    obj = bpy.data.objects.new(name, me)
    _coll.objects.link(obj)
    return obj


def _x_cyl(name, x, radius, length, mat, segments=32):
    """Válec s osou X se středem v (x, 0, 0) - díl role."""
    bm = _cyl_bm(radius, radius, length, segments)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    return _finish(name, bm, Matrix.Translation((x, 0, 0)), mat, smooth_quads=True)


def tarp(name, parent, top_center, along, normal, width, height, drop_fn=None, straps=(), strap_top=None, buckles=True,
         hem=0.05, rows=0.15, fold=TARP_FOLD, roll_radius=0.075, roll_out=0.045, roll_gap=0.005, roll_loops=None,
         fold_time=(2.6, 3.0), rolled_scale=None, roll_closed_scale=ROLL_CLOSED_SCALE, closed_drop=None):
    """Rolovací plachta s rolí. top_center = střed horní hrany ve světě, along = směr podél plachty (lokální X),
    normal = ven z vleku (tam jdou popruhy, polepy i role), width x height (m).
    drop_fn(x) -> výška plachty v místě x (x od -width/2 do width/2), např. výřez nad blatníky; jinak všude height.
    straps = polohy x popruhů; strap_top = výška popruhu od spodní hrany (None = celá výška); buckles = spony a háčky.
    roll_loops = polohy x poutek na roli (výchozí = straps). fold_time = (t0, t1) v animaci foldLadder (s) -> <part> pro
    {{TARP_PARTS}} (výchozí 2,6-3,0 s = po složení žebříku, délka animace 3 s se nemění); rolled_scale = měřítko srolované plachty (výchozí: spodní hrana skončí v ose role);
    closed_drop = výška pod horní hranou, kde leží zavřená role (výchozí nejmenší výška plachty, ať nenarazí do blatníku).
    Vrací (pivot plachty, role)."""
    along = Vector(along).normalized()
    up = Vector((0, 0, 1))
    up = (up - along * up.dot(along)).normalized()
    yax = up.cross(along)
    frame = Matrix((along, yax, up)).transposed().to_4x4()
    frame.translation = Vector(top_center)
    ny = 1.0 if Vector(normal).dot(yax) > 0 else -1.0     # na kterou stranu lokální Y je "ven"
    drop_fn = drop_fn or (lambda x: height)

    pivot = empty(name, (0, 0, 0))
    pivot.empty_display_type = "SINGLE_ARROW"
    pivot.empty_display_size = 0.15
    pivot.matrix_world = frame
    if parent is not None:
        _keep_world(pivot, parent)
    pivot["sdt_mapped"] = 1

    sheet = _sheet_mesh(name + "_Sheet", width, drop_fn, hem, rows, fold)
    if ny < 0:
        sheet.data.transform(Matrix.Diagonal((1, -1, 1, 1)))
        sheet.data.flip_normals()
    sheet.parent = pivot
    sheet.matrix_parent_inverse = Matrix.Identity(4)
    sheet.matrix_basis = Matrix.Identity(4)

    rot = frame.to_3x3().to_4x4()
    so = fold[0] + TARP_STRAP_OFFSET
    parts = []
    for i, x in enumerate(straps):
        zb = -drop_fn(x)
        ztop = 0.0 if strap_top is None else zb + strap_top
        pieces = {"Strap": (0.045, so, 0.006, zb - 0.03, ztop, "SDT_TarpStrap")}
        if buckles:
            pieces["Buckle"] = (0.065, so + 0.009, 0.012, zb + 0.11, zb + 0.21, "SDT_Steel")
            pieces["Hook"] = (0.05, so, 0.024, zb - 0.04, zb - 0.01, "SDT_Steel")
        for tag, (w, out, t, z0, z1, mat) in pieces.items():
            bmb = bmesh.new()
            bmesh.ops.create_cube(bmb, size=1.0, matrix=Matrix.Diagonal((w, t, z1 - z0, 1.0)))
            c = frame @ Vector((x, ny * out, (z0 + z1) / 2))
            parts.append(_finish(f"{name}_{tag}{i}", bmb, Matrix.Translation(c) @ rot, mat))
    if parts:
        _keep_world(merge(name + "_Straps", parts), pivot)

    loops = straps if roll_loops is None else roll_loops
    rparts = [_x_cyl(name + "Roll_Body", 0.0, roll_radius, width, "SDT_Tarp")]
    rparts += [_x_cyl(f"{name}Roll_Loop{i}", x, roll_radius + 0.008, 0.044, "SDT_TarpStrap") for i, x in enumerate(loops)]
    rparts += [_x_cyl(f"{name}Roll_Cap{k}", s * (width / 2 - 0.006), roll_radius * 0.55, 0.014, "SDT_TarpHem", 24)
               for k, s in enumerate((-1, 1))]
    roll = merge(name + "Roll", rparts)
    cd = min(drop_fn(-width / 2 + width * k / 50) for k in range(51)) if closed_drop is None else closed_drop
    rc = roll_radius * roll_closed_scale
    open_w = frame @ Vector((0, ny * roll_out, -(roll_radius + roll_gap)))
    closed_w = frame @ Vector((0, ny * (fold[0] + rc + 0.004), -cd + rc))
    roll.matrix_world = Matrix.Translation(closed_w) @ rot @ Matrix.Diagonal((1, roll_closed_scale, roll_closed_scale, 1))
    if parent is not None:
        _keep_world(roll, parent)
    roll["sdt_mapped"] = 1

    s_rolled = rolled_scale if rolled_scale is not None else max(0.02, (roll_radius + roll_gap) / height)
    pinv = roll.parent.matrix_world.inverted() if roll.parent else Matrix.Identity(4)
    t0, t1 = fold_time
    c = roll_closed_scale
    pivot["sdt_fold_parts"] = "\n".join((
        f'            <part node="{name}" startTime="{t0:g}" endTime="{t1:g}" startScale="1 {s_rolled:.4g} 1" '
        f'endScale="1 1 1"/>',
        f'            <part node="{name}Roll" startTime="{t0:g}" endTime="{t1:g}" '
        f'startTrans="{i3d_fmt(i3d_vec(pinv @ open_w))}" endTrans="{i3d_fmt(i3d_vec(pinv @ closed_w))}" '
        f'startScale="1 1 1" endScale="1 {c:g} {c:g}"/>'))
    return pivot, roll


def tarp_preview(pivot, roll, t):
    """Náhled stavu animace v Blenderu podle uložených <part> (t = 0 srolováno .. 1 zavřeno). Exportuje se stav t = 1
    (tak ho tarp postaví) - po náhledu tarp_preview(pivot, roll, 1.0)."""
    import re
    rows = pivot["sdt_fold_parts"].split("\n")
    s0 = float(re.search(r'startScale="1 ([\d.e-]+) 1"', rows[0]).group(1))
    tr = {k: Vector([float(c) for c in v.split()]) for k, v in re.findall(r'(start|end)Trans="([^"]+)"', rows[1])}
    cs = float(re.search(r'endScale="1 ([\d.]+) ', rows[1]).group(1))
    pivot.scale = (1, 1, s0 + (1 - s0) * t)
    p = tr["start"].lerp(tr["end"], t)
    roll.location = (p.x, -p.z, p.y)
    c = 1 + (cs - 1) * t
    roll.scale = (1, c, c)


# ---------------------------------------------------------------- maketa složené relé tyče

RELAY_HEAD_LEN = 0.33             # od čela tyče: skříňka rádia a bateriový box (třmeny musí být dál)


def relay_pole_mockup(i, parent, head, tail, scale=1.0, up=None):
    """Uzel relaySlot<i> ve středu osy uložené tyče a pod ním maketa složené tyče relaySlot<i>_pole (jeden mesh): stožár,
    skříňka rádia a bateriový box u čela (head), objímka a tři přiložené nohy s patkami k patě (tail). head/tail = body osy
    ve světě (~1,45 m od sebe) v libovolném směru: ležatě podél vleku (head (x, y0, z), tail (x, y1, z)) nebo svisle hlavou
    nahoru (head = horní bod). up = směr "nahoru" v průřezu (skříňka je v něm vyšší); výchozí Z, u svislé tyče -Y (dopředu)."""
    head, tail = Vector(head), Vector(tail)
    d = (tail - head).normalized()
    if up is None:
        up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((0, -1, 0))
    up = Vector(up)
    up = (up - d * up.dot(d)).normalized()
    across = d.cross(up).normalized()
    frame = Matrix((across, d, up)).transposed().to_4x4()     # x napříč, y podél osy od čela, z = up; počátek v čele
    frame.translation = head
    length = (tail - head).length
    slot = empty(f"relaySlot{i}", (head + tail) / 2)
    if parent is not None:
        _keep_world(slot, parent)
    s = scale
    mast = 0.030 * s
    tag = f"relaySlot{i}_"
    parts = [tube(tag + "Mast", (0, 0.02, 0), (0, length - 0.02, 0), mast, "SDT_Alu", segments=14),
             tube(tag + "CapHead", (0, 0, 0), (0, 0.02, 0), mast * 1.2, "SDT_Rubber", segments=14),
             tube(tag + "CapTail", (0, length, 0), (0, length - 0.02, 0), mast * 1.2, "SDT_Rubber", segments=14),
             chamfer_box(tag + "Radio", -0.055 * s, 0.055 * s, 0.03, 0.19, -0.075 * s, 0.075 * s, "SDT_PaintYellow", 0.008),
             box(tag + "RadioLid", -0.057 * s, 0.057 * s, 0.03, 0.045, -0.077 * s, 0.077 * s, "SDT_PaintDark"),
             chamfer_box(tag + "Battery", -0.045 * s, 0.045 * s, 0.20, RELAY_HEAD_LEN, -0.05 * s, 0.05 * s, "SDT_BatteryGrey",
                         0.006),
             box(tag + "BatteryBand", -0.046 * s, 0.046 * s, 0.25, 0.27, -0.051 * s, 0.051 * s, "SDT_GenOrange"),
             tube(tag + "Collar", (0, 0.36, 0), (0, 0.41, 0), 0.040 * s, "SDT_Frame", segments=14)]
    for k in range(3):
        a = math.radians(90 + 120 * k)
        lx, lz = 0.050 * s * math.cos(a), 0.050 * s * math.sin(a)
        parts.append(tube(f"{tag}Leg{k}", (lx, 0.40, lz), (lx, length - 0.05, lz), 0.010 * s, "SDT_Frame", segments=8))
        parts.append(tube(f"{tag}Foot{k}", (lx, length - 0.05, lz), (lx, length - 0.02, lz), 0.016 * s, "SDT_Rubber",
                          segments=10))
    pole = merge(f"relaySlot{i}_pole", parts, frame)
    pole.data.transform(slot.matrix_world.inverted())
    pole.parent = slot
    pole.matrix_parent_inverse = Matrix.Identity(4)
    pole.matrix_basis = Matrix.Identity(4)
    return slot, pole
