"""Koncovka plnicí hadice jako pistole u benzinové pumpy a plnicí hrdlo dronu, do kterého zapadá.

Souřadnice koncovky (Blender, lokální): počátek = uzel fillHoseNozzle, -Y míří ze špičky ven (= +Z i3d, do hrdla),
+Z je "nahoře" (= +Y i3d), spoušť je na straně -Z. Hadice vchází do otočného přívodu, který vyčnívá šikmo nahoru a dozadu
(INLET_ANGLE od osy koncovky); konec hadice leží v INLET_END a hadice se k němu blíží po ose přívodu (INLET_OUT ven).
Špička výtokového hrdla přesahuje počátek o SPOUT_REACH do plnicího hrdla dronu; kuželová přírubka v počátku dosedá na
okraj hrdla.
"""

import math

import bmesh
from mathutils import Matrix, Vector

import sdt_parts as P

INLET_ANGLE = math.radians(50)
INLET_BASE = Vector((0.0, 0.166, 0.034))
INLET_OUT = Vector((0.0, math.cos(INLET_ANGLE), math.sin(INLET_ANGLE)))
INLET_LEN = 0.120                          # konec hadice až za pružinou (ta končí v 0,118): kovové díly přívodu hadicí neprocházejí
INLET_END = INLET_BASE + INLET_OUT * INLET_LEN
SPOUT_REACH = 0.025
SPOUT_R = 0.0125
BORE_R = 0.0092
BODY_Z = 0.022
PORT_HOLE_R = 0.0165
PORT_DEPTH = 0.030


def _quad(bm, verts, want):
    n = (verts[1].co - verts[0].co).cross(verts[2].co - verts[0].co)
    return bm.faces.new(verts if n.dot(want) >= 0 else list(reversed(verts)))


def _spout(name, path, mat, slope=0.7):
    """Ohnuté výtokové hrdlo: trubka po křivce v rovině YZ, špička dutá se šikmým řezem (delší je strana -Z,
    tedy ke spoušti) a zapuštěným otvorem. Vrací objekt a y dna otvoru."""
    path = [Vector(p) for p in path]
    tan = [(path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized() for i in range(len(path))]
    nrm = Vector((1, 0, 0))
    seg = 20
    bm = bmesh.new()

    def ring(p, t, r, cut=False):
        b = t.cross(nrm).normalized()
        out = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            v = p + r * (math.cos(a) * nrm + math.sin(a) * b)
            if cut:
                v.y += slope * (v.z - p.z)
            out.append(bm.verts.new(v))
        return out

    rings = [ring(p, t, SPOUT_R) for p, t in zip(path[:-1], tan[:-1])]
    pe, te = path[-1], tan[-1]
    rings.append(ring(pe, te, SPOUT_R, cut=True))
    for r0, r1 in zip(rings, rings[1:]):
        mid = sum((v.co for v in r0), Vector()) / seg
        for k in range(seg):
            j = (k + 1) % seg
            _quad(bm, [r0[k], r0[j], r1[j], r1[k]], (r0[k].co + r0[j].co) / 2 - mid).smooth = True
    lip_out, lip_in = ring(pe, te, SPOUT_R, cut=True), ring(pe, te, BORE_R, cut=True)
    for k in range(seg):
        j = (k + 1) % seg
        _quad(bm, [lip_out[k], lip_out[j], lip_in[j], lip_in[k]], Vector((0, -1, slope)))
    y_cap = pe.y + slope * SPOUT_R + 0.004
    wall = ring(pe, te, BORE_R, cut=True)
    deep = [bm.verts.new(Vector((v.co.x, y_cap, v.co.z))) for v in wall]
    for k in range(seg):
        j = (k + 1) % seg
        inward = Vector((-wall[k].co.x, 0, pe.z - wall[k].co.z))
        _quad(bm, [wall[k], wall[j], deep[j], deep[k]], inward).smooth = True
    return P._finish(name, bm, Matrix.Identity(4), mat), y_cap


def _spring_axis(name, origin, axis, s0, s1, r0, r1, turns, wire, mat):
    n1 = Vector((1, 0, 0))
    n2 = axis.cross(n1).normalized()
    n = int(turns * 14)
    pts = []
    for k in range(n + 1):
        s = k / n
        a = 2 * math.pi * turns * s
        r = r0 + (r1 - r0) * s
        pts.append(origin + axis * (s0 + (s1 - s0) * s) + r * (math.cos(a) * n1 + math.sin(a) * n2))
    return P.sweep(name, pts, wire, mat, segments=6)


def _flat(obj):
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def _spring(name, y0, y1, r0, r1, turns, wire, mat):
    n = int(turns * 14)
    pts = []
    for k in range(n + 1):
        s = k / n
        a = 2 * math.pi * turns * s
        r = r0 + (r1 - r0) * s
        pts.append(Vector((r * math.cos(a), y0 + (y1 - y0) * s, r * math.sin(a))))
    return P.sweep(name, pts, wire, mat, segments=6)


def nozzle_parts():
    """Všechny díly koncovky v jejích lokálních souřadnicích (počátek scény = počátek uzlu), jména HoseNozzle_*."""
    tube = P.tube
    zc = BODY_Z
    parts = []

    tip_y = -SPOUT_REACH
    path = P.hermite_path([(0, 0.112, zc), (0, 0.034, 0.0), (0, tip_y, 0.0)],
                          tangents={0: (0, -1, -0.8), 1: (0, -1, 0)}, samples=10)
    spout, y_cap = _spout("HoseNozzle_Spout", path, "SDT_Steel")
    parts.append(spout)
    parts.append(tube("HoseNozzle_Mouth", (0, y_cap - 0.0015, 0), (0, y_cap + 0.0005, 0), BORE_R - 0.0004,
                      "SDT_TankBlack", segments=16))
    parts.append(tube("HoseNozzle_Collar", (0, 0.0, 0), (0, 0.013, 0), 0.021, "SDT_Steel", segments=20,
                      radius_end=0.0135))
    parts.append(tube("HoseNozzle_CollarRing", (0, 0.013, 0), (0, 0.020, 0), 0.0165, "SDT_CastIron", segments=20))

    parts.append(P.loft_y("HoseNozzle_Housing", [
        (0.070, 0.0145, -0.0085, 0.0165, 2.2),
        (0.084, 0.019, -0.008, 0.034, 2.4),
        (0.100, 0.025, zc - 0.027, zc + 0.027, 2.8),
        (0.128, 0.026, zc - 0.029, zc + 0.029, 2.8),
    ], "SDT_ValveBlue", segments=24))
    parts.append(P.loft_y("HoseNozzle_Grip", [
        (0.124, 0.0275, zc - 0.031, zc + 0.031, 2.8),
        (0.140, 0.030, zc - 0.034, zc + 0.034, 2.6),
        (0.158, 0.0295, -0.0145, zc + 0.034, 2.6),
        (0.172, 0.027, -0.018, 0.038, 2.4),
        (0.181, 0.024, -0.022, 0.028, 2.2),
    ], "SDT_ValveBlue", segments=24))

    a, u = INLET_BASE, INLET_OUT
    parts.append(tube("HoseNozzle_InletBoss", a - u * 0.012, a + u * 0.008, 0.0315, "SDT_CastIron", segments=20))
    parts.append(tube("HoseNozzle_Swivel", a, a + u * 0.032, 0.0235, "SDT_CastIron", segments=20))
    parts.append(_flat(tube("HoseNozzle_Nut", a + u * 0.028, a + u * 0.042, 0.0295, "SDT_Steel", segments=6)))
    parts.append(tube("HoseNozzle_Ferrule", a + u * 0.042, a + u * 0.074, 0.0245, "SDT_Steel", segments=20,
                      radius_end=0.0235))
    parts.append(_spring_axis("HoseNozzle_Spring", a, u, 0.070, 0.118, 0.0290, 0.0258, 6, 0.0032, "SDT_Steel"))
    parts.append(tube("HoseNozzle_Sleeve", a + u * 0.072, a + u * 0.1185, 0.0215, "SDT_HoseBlack", segments=20))

    parts.append(P.plate_yz("HoseNozzle_Lever", 0.0, 0.016, [
        (0.102, -0.010), (0.126, -0.015), (0.150, -0.021), (0.172, -0.026), (0.178, -0.034),
        (0.170, -0.040), (0.148, -0.037), (0.124, -0.030), (0.102, -0.020)], "SDT_Rubber"))
    parts.append(P.cylinder_x("HoseNozzle_Pivot", (0.0, 0.102, -0.014), 0.0038, 0.054, "SDT_Steel", segments=10))

    guard = [(0, 0.094, -0.009), (0, 0.086, -0.038), (0, 0.104, -0.062), (0, 0.140, -0.069), (0, 0.170, -0.058),
             (0, 0.184, -0.034), (0, 0.181, -0.012)]
    parts.append(P.sweep("HoseNozzle_Guard", P.hermite_path(guard, samples=6), 0.0046, "SDT_Rubber", segments=10))
    parts.append(P.plate_yz("HoseNozzle_Latch", 0.0, 0.007, [
        (0.182, -0.030), (0.182, -0.055), (0.163, -0.055), (0.163, -0.051), (0.171, -0.047), (0.163, -0.047),
        (0.163, -0.043), (0.171, -0.039), (0.163, -0.039), (0.163, -0.035)], "SDT_Steel"))
    return parts


def fill_port_parts(prefix, px, py, top, port_top):
    """Plnicí hrdlo na hřbetu dronu: dutý černý krček s jantarovým lemem, na dně černý talíř; špička koncovky
    (SPOUT_REACH pod uzlem <prefix>FillPort) sjede do díry a příruba dosedne na lem."""
    floor = port_top - PORT_DEPTH
    ring_h = 0.012
    neck_z0 = top - 0.010
    neck_z1 = port_top - ring_h
    return [
        P.ring_z(f"{prefix}FillPortNeck", (px, py, (neck_z0 + neck_z1) / 2), PORT_HOLE_R, 0.030, neck_z1 - neck_z0,
                 "SDT_TankBlack", segments=24),
        P.ring_z(f"{prefix}FillPortRing", (px, py, port_top - ring_h / 2), PORT_HOLE_R, 0.036, ring_h,
                 "SDT_LampAmber", segments=24),
        P.cylinder_z(f"{prefix}FillPortFloor", (px, py, floor - 0.002), PORT_HOLE_R + 0.001, 0.004, "SDT_TankBlack",
                     segments=24),
    ]
