"""Společné stavební díly vleků (build_trailer3.py, build_trailer_car.py).

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
    "SDT_PaintWhite": ((0.92, 0.92, 0.92), 0.0, 0.5),
    "SDT_PaintDark": ((0.06, 0.065, 0.07), 0.0, 0.7),
    "SDT_BatteryGrey": ((0.06, 0.06, 0.065), 0.1, 0.5),
    "SDT_ChargerGrey": ((0.16, 0.165, 0.17), 0.2, 0.45),
    "SDT_LedGreen": ((0.05, 0.85, 0.12), 0.0, 0.2),
    "SDT_Screen": ((0.02, 0.07, 0.14), 0.0, 0.1),
    "SDT_CastIron": ((0.03, 0.03, 0.032), 0.3, 0.55),
    "SDT_PaintRed": ((0.60, 0.02, 0.02), 0.0, 0.4),
    "SDT_Plastic": ((0.03, 0.03, 0.03), 0.0, 0.5),
    "SDT_Decal": ((1.0, 1.0, 1.0), 0.0, 0.45),
}
DECAL_MATERIALS = ("SDT_Decal",)
DECAL_ATLAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures", L.ATLAS_PNG)

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
    if name in DECAL_MATERIALS:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(DECAL_ATLAS, check_existing=True)
        uvn = mat.node_tree.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "UVMap"
        mat.node_tree.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
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


def battery(name, size=BATTERY_SIZE):
    """Baterie podle DJI DB800 / DB1560 / DB2160: délka po X, šířka po Y, konektor na čele -X, rukojeť na čele +X
    (baterie se do nabíječky i dronu zasouvá konektorem napřed a nese se za rukojeť).

    Jeden mesh (díly sloučené, materiály jako sloty). Rámec slotu = rámec M: u M je počátek uprostřed dole,
    menší a větší baterie jsou posunuté podle battery_frame_offset, takže ve stejném slotu sedí konektorem
    na stejném místě.
    """
    lx, ly, lz = size[0] / 2, size[1] / 2, size[2]
    fx, fy, fz = (s / m for s, m in zip(size, BATTERY_SIZE))
    hz = lz / 2
    parts = [
        box(f"{name}_Body", -lx, lx, -ly, ly, 0.0, lz - 0.015, "SDT_BatteryGrey"),
        box(f"{name}_Cap", -lx + 0.01, lx - 0.01, -ly + 0.01, ly - 0.01, lz - 0.015, lz, "SDT_TankBlack"),
        box(f"{name}_HandlePostA", lx, lx + 0.025, -0.10 * fy, -0.08 * fy, hz - 0.018 * fz, hz + 0.018 * fz, "SDT_TankBlack"),
        box(f"{name}_HandlePostB", lx, lx + 0.025, 0.08 * fy, 0.10 * fy, hz - 0.018 * fz, hz + 0.018 * fz, "SDT_TankBlack"),
        tube(f"{name}_HandleBar", (lx + 0.02, -0.10 * fy, hz), (lx + 0.02, 0.10 * fy, hz), 0.011, "SDT_Rubber", segments=10),
        box(f"{name}_Connector", -lx - 0.012, -lx, -0.06 * fy, 0.06 * fy, 0.03 * fz, 0.085 * fz, "SDT_TankBlack"),
        box(f"{name}_PinA", -lx - 0.016, -lx - 0.012, -0.04 * fy, -0.02 * fy, 0.045 * fz, 0.07 * fz, "SDT_Steel"),
        box(f"{name}_PinB", -lx - 0.016, -lx - 0.012, 0.02 * fy, 0.04 * fy, 0.045 * fz, 0.07 * fz, "SDT_Steel"),
        box(f"{name}_LabelA", -0.12 * fx, 0.12 * fx, ly, ly + 0.002, 0.025 * fz, 0.09 * fz, "SDT_Decal"),
        box(f"{name}_LabelB", -0.12 * fx, 0.12 * fx, -ly - 0.002, -ly, 0.025 * fz, 0.09 * fz, "SDT_Decal"),
        box(f"{name}_Stripe", -0.12 * fx, 0.12 * fx, ly, ly + 0.003, 0.095 * fz, 0.103 * fz, "SDT_GenOrange"),
        box(f"{name}_Leds", lx, lx + 0.002, -0.05 * fy, 0.05 * fy, lz - 0.03, lz - 0.018, "SDT_Mesh"),
    ]
    key = next(k for k, s in BATTERY_SIZES.items() if tuple(s) == tuple(size))
    lw, lh, lz0 = 0.24 * fx, 0.065 * fz, 0.025 * fz
    planar_uv(parts[8], (0.12 * fx, ly, lz0), (-1, 0, 0), (0, 0, 1), lw, lh, "battery" + key)
    planar_uv(parts[9], (-0.12 * fx, -ly, lz0), (1, 0, 0), (0, 0, 1), lw, lh, "battery" + key)
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
