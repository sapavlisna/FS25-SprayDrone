"""Společné stavební díly vleků (build_trailer3.py, build_trailer_car.py).

Každý díl je samostatný objekt s měřítkem 1 a vlastním počátkem, zavěšený pod kořenový empty
aktuálního vleku (begin()). Osa vleku: přední část na -Y, Z nahoru, počátek na zemi.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

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
    "SDT_NavLed": ((0.55, 0.55, 0.55), 0.0, 0.15),
}

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
    """Ležatá nádrž na sedlech s pásy, osa podél vleku, na středu šířky."""
    zc = z + 0.12 + radius
    capsule(prefix, (0, y, zc), radius, length, "Y", "SDT_TankWhite")
    for i, dy in enumerate(band_offsets):
        tube(f"{prefix}_Band{i}", (0, y + dy - 0.02, zc), (0, y + dy + 0.02, zc), radius + 0.012,
             "SDT_TankBlack", segments=32)
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
