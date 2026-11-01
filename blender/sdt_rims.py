"""Vlastní disky kol pro hru (outerRim ve wheel XML vleku) a náhled kol v Blenderu.

Hra disk z modu nedeformuje (na rozdíl od vanilla disků se shaderem "rim"), takže tvar je skutečný: ráfek s přírubami,
lisovaný talíř s průchozími otvory, náboj, matice a krytka. Osa kola je X, počátek ve středu kola; sx = +1 je levé kolo
(vnější strana na +X), sx = -1 pravé (vanilla náboje hubTrucks mají levý tvar na +X a pravý na -X, hra je nezrcadlí).

    R22  Max:  ocelový návěsový disk 22,5 x 9 pod Conti Hybrid HD3 315/80 R22,5, deset oválných otvorů pro ruce,
               deset matic s oranžovými ukazateli povolení, vypouklá krytka náboje se šrouby, ventilek
    R15  Mini, Middle:  disk 15,5 x 8 pod Lizard Destination Farm 280/70 R15, šest oválných oken, pět matic,
               krytka s oranžovým středem, ventilek
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import sdt_parts as P

RIMS = {
    # bead: poloměr sedla pneu (průměr disku / 2), width: šířka ráfku mezi přírubami, disc: poloha talíře od středu
    # ven, holes: (počet, poloměr roztečné kružnice, poloměr otvoru, protažení podél poloměru), nuts: (počet,
    # poloměr roztečné kružnice, poloměr matice), face: (poloměr dosedací plochy náboje, výška kužele talíře)
    "R22": dict(bead=22.5 * 0.0254 / 2, width=9 * 0.0254, disc=0.050, holes=(10, 0.214, 0.026, 1.45),
                nuts=(10, 0.1675, 0.017), face=(0.192, 0.030), bore=0.072, boss=(0.112, 0.036), cap=(0.078, 0.030),
                indicators=True, cap_bolts=6, mat="SDT_RimPaint"),
    "R15": dict(bead=15.5 * 0.0254 / 2, width=8 * 0.0254, disc=0.036, holes=(6, 0.136, 0.022, 1.55),
                nuts=(5, 0.056, 0.011), face=(0.090, 0.024), bore=0.033, boss=(0.074, 0.018), cap=(0.034, 0.016),
                indicators=False, cap_bolts=0, mat="SDT_RimPaint"),
}
RIM_T = 0.006          # plech ráfku
DISC_T = 0.012         # talíř


def _revolve(name, profile, mat, sx, seg=64):
    """Uzavřený profil [(x, r)] otočený kolem osy X; sx zrcadlí po X."""
    bm = bmesh.new()
    rings = [[bm.verts.new((sx * x, r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)))
              for i in range(seg)] for x, r in profile]
    for k in range(len(rings)):
        r0, r1 = rings[k], rings[(k + 1) % len(rings)]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return P._finish(name, bm, Matrix.Identity(4), mat)


def _barrel_profile(spec):
    """Ráfek: příruby na obou okrajích, sedla patek, hluboké dno posunuté k vnitřní straně (tam se pneu nasazuje)."""
    R, h = spec["bead"], spec["width"] / 2
    outer = [(h, R + 0.026), (h, R + 0.004), (h - 0.018, R - 0.002), (h - 0.040, R - 0.006), (h - 0.060, R - 0.026),
             (-h + 0.075, R - 0.026), (-h + 0.050, R - 0.006), (-h + 0.018, R - 0.002), (-h, R + 0.004), (-h, R + 0.026)]
    inner = [(x - (RIM_T if x > 0 else -RIM_T) * (0 if abs(x) < h - 0.001 else 1), r + RIM_T * 0.6)
             for x, r in reversed(outer)]
    return outer + inner


def _disc_profile(spec):
    """Lisovaný talíř: rovný věnec přivařený k ráfku, kužel ven k dosedací ploše náboje, středový otvor."""
    R, xd = spec["bead"], spec["disc"]
    face_r, rise = spec["face"]
    weld = R - 0.020
    cone_r = face_r + 0.045
    outer = [(xd, weld), (xd, cone_r), (xd + rise, face_r), (xd + rise, spec["bore"])]
    inner = [(x - DISC_T, r) for x, r in reversed(outer)]
    return outer + inner


def _cut_holes(obj, spec, sx):
    """Průchozí otvory v talíři: boolean s protaženými válci podél osy kola."""
    n, pcd, r, stretch = spec["holes"]
    cutters = []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        bm = P._cyl_bm(r, r, 0.20, 24)
        m = (Matrix.Translation((sx * spec["disc"], pcd * math.cos(a), pcd * math.sin(a)))
             @ Matrix.Rotation(a, 4, "X") @ Matrix.Diagonal((1.0, stretch, 1.0, 1.0))
             @ Matrix.Rotation(math.radians(90), 4, "Y"))
        cutters.append(P._finish(f"{obj.name}_Cut{k}", bm, m, spec["mat"]))
    cutter = P.merge(f"{obj.name}_Cutter", cutters)
    mod = obj.modifiers.new("holes", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.remove(mod)
    obj.data = me
    bpy.data.meshes.remove(old)
    data = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(data)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    P._box_uv(bm)
    bm.to_mesh(obj.data)
    bm.free()


def _radial(sx, x, rad, a):
    return Vector((sx * x, rad * math.cos(a), rad * math.sin(a)))


def build_rim(kind, name, sx):
    """Celý disk jedné strany jako jeden objekt (materiály jako sloty), počátek ve středu kola."""
    spec = RIMS[kind]
    mat = spec["mat"]
    xd, (face_r, rise) = spec["disc"], spec["face"]
    x_face = xd + rise
    parts = [_revolve(f"{name}_Barrel", _barrel_profile(spec), mat, sx)]
    disc = _revolve(f"{name}_Disc", _disc_profile(spec), mat, sx)
    _cut_holes(disc, spec, sx)
    parts.append(disc)

    boss_r, boss_h = spec["boss"]
    parts.append(P.cylinder_x(f"{name}_Boss", (sx * (x_face + boss_h / 2), 0, 0), boss_r, boss_h, "SDT_Steel", segments=40))
    n, pcd, nut_r = spec["nuts"]
    x_nut = x_face + 0.004
    for k in range(n):
        a = 2 * math.pi * k / n
        c = _radial(sx, x_nut + 0.012, pcd, a)
        parts.append(P.cylinder_x(f"{name}_Nut{k}", c, nut_r, 0.024, "SDT_Steel", segments=6))
        parts.append(P.cylinder_x(f"{name}_Stud{k}", c + Vector((sx * 0.016, 0, 0)), nut_r * 0.55, 0.012, "SDT_Steel",
                                  segments=10))
        parts.append(P.cylinder_x(f"{name}_Washer{k}", _radial(sx, x_nut + 0.001, pcd, a), nut_r * 1.35, 0.004,
                                  "SDT_Steel", segments=16))
        if spec["indicators"]:
            # ukazatel povolení matice: plastová šipka na matici, sousední dvojice míří proti sobě
            b = a + (1 if k % 2 == 0 else -1) * 0.5 * (2 * math.pi / n)
            tip = _radial(sx, x_nut + 0.026, pcd, b)
            parts.append(P.tube(f"{name}_Ind{k}", c + Vector((sx * 0.014, 0, 0)), tip.lerp(c, 0.25) + Vector((sx * 0.014, 0, 0)),
                                0.006, "SDT_NutIndicator", segments=8, radius_end=0.002))
            parts.append(P.cylinder_x(f"{name}_IndRing{k}", c + Vector((sx * 0.006, 0, 0)), nut_r * 1.2, 0.014,
                                      "SDT_NutIndicator", segments=6))
    cap_r, cap_h = spec["cap"]
    x_cap = x_face + boss_h
    dome = [(x_cap, cap_r), (x_cap + cap_h * 0.55, cap_r * 0.96), (x_cap + cap_h * 0.85, cap_r * 0.75),
            (x_cap + cap_h, cap_r * 0.35), (x_cap + cap_h, 0.0005), (x_cap, 0.0005)]
    parts.append(_revolve(f"{name}_Cap", dome, "SDT_Steel", sx, seg=40))
    for k in range(spec["cap_bolts"]):
        a = 2 * math.pi * (k + 0.5) / spec["cap_bolts"]
        parts.append(P.cylinder_x(f"{name}_CapBolt{k}", _radial(sx, x_cap + 0.004, cap_r * 0.82, a), 0.007, 0.010,
                                  "SDT_Steel", segments=6))
    if kind == "R15":
        parts.append(P.cylinder_x(f"{name}_CapBadge", (sx * (x_cap + cap_h + 0.001), 0, 0), cap_r * 0.42, 0.004,
                                  "SDT_NutIndicator", segments=24))

    # ventilek v mezeře mezi otvory u ráfku, skloněný ven
    a = 2 * math.pi * 0.0
    base = _radial(sx, xd - 0.004, spec["bead"] - 0.030, a)
    tip = _radial(sx, xd + 0.032, spec["bead"] - 0.050, a)
    parts.append(P.tube(f"{name}_Valve", base, tip, 0.005, "SDT_Rubber", segments=8))
    parts.append(P.tube(f"{name}_ValveCap", tip, tip + (tip - base).normalized() * 0.012, 0.0055, "SDT_Steel", segments=8))
    return P.merge(name, parts)


def build_rim_pair(kind, root_name):
    """Kořen <root_name> se dvěma tvary: <root_name>L (uzel 0|0, levé kolo) a <root_name>R (0|1, pravé)."""
    root = bpy.data.objects.new(root_name, None)
    P._coll.objects.link(root)
    left = build_rim(kind, root_name + "L", 1)
    right = build_rim(kind, root_name + "R", -1)
    for o in (left, right):
        o.parent = root
        o.matrix_parent_inverse = Matrix.Identity(4)
    return root, left, right


def build_tire(name, sx, r_out, width, r_bead, mat="SDT_Rubber"):
    """Náhled pneu (jen vzhled do obchodu a kontrol, hra použije vanilla pneu): zaoblená ramena, boky s lemem u ráfku a tři
    podélné drážky běhounu, osa X, počátek ve středu kola."""
    h = width / 2
    side = [(h * 0.80, r_bead + 0.004), (h * 0.93, r_bead + (r_out - r_bead) * 0.18), (h, r_bead + (r_out - r_bead) * 0.50),
            (h * 0.96, r_bead + (r_out - r_bead) * 0.86), (h * 0.80, r_out - 0.010)]
    tread = [(h * 0.62, r_out)]
    for g in (h * 0.36, 0.0, -h * 0.36):
        tread += [(g + 0.010, r_out), (g + 0.007, r_out - 0.008), (g - 0.007, r_out - 0.008), (g - 0.010, r_out)]
    half = side + tread
    mirrored = [(-x, r) for x, r in reversed(side)]
    return _revolve(name, half + mirrored, mat, sx, seg=72)
