"""Elektrocentrála vleku: naftový agregát v klecovém rámu na spodní palubě (build_trailer_middle.build_equipment).

Plechový kryt s větracími žaluziemi, ovládací panel na levém boku (klíč, předehřev, voltmetr, počítadlo hodin, kontrolky,
jistič, vypínač výstupu, zásuvka pro nabíječku), nádrž s hrdlem a průhledným ukazatelem hladiny vzadu, na střeše
tlumič s zahnutým výfukem, jehož ústí míří dopředu vleku (-Y). Legendy a piktogramy jsou nálepky z atlasu
(decal_layout.py, tools/make_decal_atlas.py).

Uzly: Gen_0_Frame, Gen_0_Body, Gen_0_Exhaust, Gen_0_ChargeSocket (zásuvka na stejném místě jako dřív, kabel nabíječky do ní
míří), Gen_0_Decals a empty generatorExhaust u ústí výfuku (osa -Y Blenderu = +Z i3d míří ven z ústí, tudy jde kouř
vanilla efektu). Rozměry jsou lokální vůči středu půdorysu (lx doprava = ven na levý bok, ly dozadu, lz od paluby).
"""

import itertools
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import decal_layout as L
import sdt_parts as P

# rám: kulaté trubky po obvodu nahoře a dole, čtyři sloupky
FX, FY, TUBE_R = 0.36, 0.43, 0.017
FRAME_Z0, FRAME_Z1 = 0.055, 0.76
# kryt motoru a alternátoru + nádrž vzadu
HX, HY0, HY1, HZ0, HZ1 = 0.31, -0.39, 0.17, 0.08, 0.60
TANK = (0.325, 0.16, 0.39, 0.62)            # x vně, y od, y do, výška střechy
CAP_XY = (0.20, 0.275)                      # hrdlo nádrže
PANEL = (0.325, -0.34, 0.30)               # lícová rovina panelu, jeho levý dolní roh (ly, lz); rozměr L.GEN_PANEL_SIZE
# výfuk: tlumič na střeše podél Y, z jeho předního konce trubka nahoru a pak zahnutá dopředu a mírně vzhůru
EXH_X = 0.20
MUFFLER = (-0.26, 0.04, 0.685, 0.058)      # y od, y do, střed z, poloměr
TAIL_R, TAIL_TILT_DEG = 0.023, 12.0
TAIL_TURN = (-0.36, 0.84)                   # y a z kolena, kde trubka přejde do vodorovného ústí
TAIL_LEN = 0.16

_O = Vector((0.0, 0.0, 0.0))
_count = itertools.count()


def _nm(tag):
    return f"_g{tag}{next(_count)}"


def _w(lx, ly, lz):
    return _O + Vector((lx, ly, lz))


def _box(x0, x1, y0, y1, z0, z1, mat):
    return P.box(_nm("b"), _O.x + x0, _O.x + x1, _O.y + y0, _O.y + y1, _O.z + z0, _O.z + z1, mat)


def _cbox(x0, x1, y0, y1, z0, z1, mat, ch):
    return P.chamfer_box(_nm("c"), _O.x + x0, _O.x + x1, _O.y + y0, _O.y + y1, _O.z + z0, _O.z + z1, mat, ch)


def _tube(p0, p1, r, mat, seg=10, r_end=None):
    return P.tube(_nm("t"), _w(*p0), _w(*p1), r, mat, segments=seg, radius_end=r_end)


def _bb(center, b0, b1, b2, size, mat):
    """Kvádr o rozměrech size podél os b0, b1, b2 (pravotočivá báze) se středem center (lokálně)."""
    c = _w(*center)
    m = Matrix(((b0.x, b1.x, b2.x, c.x), (b0.y, b1.y, b2.y, c.y), (b0.z, b1.z, b2.z, c.z), (0, 0, 0, 1)))
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*size, 1.0)))
    return P._finish(_nm("o"), bm, m, mat)


def _face_box(center, n, u, size, mat):
    """Kvádr na ploše s vnější normálou n a vodorovnou osou u (vpravo při pohledu zvenku); size = (hloubka, šířka, výška)."""
    return _bb(center, n, u, n.cross(u), size, mat)


def _ring(center, axis, r_in, r_out, h, mat, seg=20):
    o = P.ring_z(_nm("r"), (0, 0, 0), r_in, r_out, h, mat, segments=seg)
    rot = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized()).to_matrix().to_4x4()
    o.matrix_world = Matrix.Translation(_w(*center)) @ rot
    return o


def _cyl(center, axis, r, length, mat, seg=14, r_end=None):
    a = Vector(axis).normalized()
    c = Vector(center)
    return _tube(tuple(c - a * length / 2), tuple(c + a * length / 2), r, mat, seg=seg, r_end=r_end)


def _fillet(pts, r, n=8):
    """Lomená čára pts se zaoblenými rohy o poloměru r (body vzorkovaného oblouku), lokální souřadnice."""
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        d1, d2 = (b - a).normalized(), (c - b).normalized()
        theta = d1.angle(d2)
        t = r * math.tan(theta / 2)
        start = b - d1 * t
        nrm = (d2 - d1 * d1.dot(d2)).normalized()
        center = start + nrm * r
        for k in range(n + 1):
            phi = theta * k / n
            out.append(center - nrm * r * math.cos(phi) + d1 * r * math.sin(phi))
    out.append(pts[-1])
    return out


def _sweep(pts, r, mat, seg=12):
    return P.sweep(_nm("s"), [_w(*p) for p in pts], r, mat, segments=seg)


FACES = {"+X": (Vector((1, 0, 0)), Vector((0, 1, 0))), "-X": (Vector((-1, 0, 0)), Vector((0, -1, 0))),
         "-Y": (Vector((0, -1, 0)), Vector((1, 0, 0))), "+Y": (Vector((0, 1, 0)), Vector((-1, 0, 0)))}


def _louvre(face, center, w, h, count, tilt=35.0, rim=0.008):
    """Větrací žaluzie na ploše: tmavé pozadí, rám a šikmé lamely (vnější hrana dole, aby dovnitř nepršelo).
    center = střed na povrchu krytu (lokálně)."""
    n, u = FACES[face]
    up = n.cross(u)
    c = Vector(center)
    out = [_face_box(c + n * 0.003, n, u, (0.006, w, h), "SDT_Plastic")]
    for sgn in (1, -1):
        out.append(_face_box(c + up * sgn * (h / 2 + rim / 2) + n * 0.006, n, u, (0.012, w + 2 * rim, rim), "SDT_PaintDark"))
        out.append(_face_box(c + u * sgn * (w / 2 + rim / 2) + n * 0.006, n, u, (0.012, rim, h), "SDT_PaintDark"))
    a = math.radians(tilt)
    s = n * math.cos(a) - up * math.sin(a)
    tt = n * math.sin(a) + up * math.cos(a)
    pitch = h / count
    length = min(0.04, pitch * 1.15)
    for i in range(count):
        z = -h / 2 + (i + 0.5) * pitch
        out.append(_bb(c + up * z + n * (0.010 + length * math.cos(a) / 2), s, u, tt, (length, w - 0.012, 0.0045),
                       "SDT_Mesh"))
    return out


def _decal_tri(name, corner, u_axis, v_axis, width, height, region, sub):
    """Trojúhelníková nálepka (rovnostranná výstražná značka): základna dole, špice nahoře, UV z dlaždice atlasu."""
    c, u, v = Vector(corner), Vector(u_axis).normalized(), Vector(v_axis).normalized()
    c = c + u.cross(v).normalized() * 0.0015
    pts = [c, c + u * width, c + u * width / 2 + v * height]
    center = sum(pts, Vector()) / 3
    bm = bmesh.new()
    f = bm.faces.new([bm.verts.new(p - center) for p in pts])
    layer = bm.loops.layers.uv.new("UVMap")
    u0, v0, u1, v1 = L.uv_rect(region, sub)
    for loop, uv in zip(f.loops, ((u0, v0), (u1, v0), ((u0 + u1) / 2, v1))):
        loop[layer].uv = uv
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    P._coll.objects.link(obj)
    obj.data.materials.append(P.material("SDT_Decal"))
    obj.parent = P._root
    obj.matrix_world = Matrix.Translation(center)
    return obj


def fuel_fill_box(gen_pos, z0):
    """Kvádr pro dieselFillRootNode (kolizní skupina plnicího uzlu): celý agregát včetně hrdla nádrže (hrdlo je v zadní
    třetině, nahoře), aby čerpací stanice nebyla citlivější na polohu než dřív; x0, x1, y0, y1, z0, z1."""
    gx, gy = gen_pos
    return gx - 0.34, gx + 0.36, gy - 0.43, gy + 0.44, z0 + 0.05, z0 + 0.80


def exhaust_geometry():
    """Lokální body výfuku: kolena tail, ústí mouth a jednotkový směr ústí dir (dopředu -Y a mírně vzhůru)."""
    a = math.radians(TAIL_TILT_DEG)
    d = Vector((0, -math.cos(a), math.sin(a)))
    ty, tz = TAIL_TURN
    mouth = Vector((EXH_X, ty, tz)) + d * TAIL_LEN
    return mouth, d


def mirror_objects(objs, x0):
    """Zrcadlí díly podle roviny x = x0 (svět): vrcholy, převrácené plochy a UV každé plochy zpět, aby nálepky zůstaly čitelné."""
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        for v in bm.verts:
            v.co.x = 2 * x0 - v.co.x
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        for layer in bm.loops.layers.uv.values():
            for f in bm.faces:
                us = [l[layer].uv.x for l in f.loops]
                lo, hi = min(us), max(us)
                for l in f.loops:
                    l[layer].uv.x = lo + hi - l[layer].uv.x
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()


def build_generator(gen_pos, z0, socket, tag="0", mirror=False, rear_socket=False):
    """Postaví agregát na desce v z0 se středem půdorysu gen_pos (x, y); socket = střed zásuvky nabíječky na levém boku
    (svět, lícová rovina panelu je o 5 mm za ním). Vrací {'exhaust': poloha ústí (svět), 'cap': hrdlo nádrže (svět)}.
    tag pojmenuje díly (Gen_<tag>_*), mirror zrcadlí agregát podle jeho středu (panel a nádrž jsou pak na pravém boku, nálepky se
    nezrcadlí), rear_socket dává napájecí kabel napevno do zadní stěny (uzdu kabelu) místo zásuvky na boku; vrací pak i 'cable' =
    konec uzdy kabelu (svět)."""
    global _O
    _O = Vector((gen_pos[0], gen_pos[1], z0))
    frame, body, exh, decals = [], [], [], []

    # ---------------------------------------------------------------- rám
    for sx in (1, -1):
        for sy in (1, -1):
            frame.append(_tube((sx * FX, sy * FY, 0.045), (sx * FX, sy * FY, FRAME_Z1), TUBE_R, "SDT_Frame", 8))
            for z in (FRAME_Z0, FRAME_Z1):
                frame.append(_box(sx * FX - 0.023, sx * FX + 0.023, sy * FY - 0.023, sy * FY + 0.023, z - 0.023, z + 0.023,
                                  "SDT_Frame"))
            frame.append(P.cylinder_z(_nm("f"), _w(sx * 0.34, sy * 0.40, 0.0175), 0.034, 0.045, "SDT_Rubber", segments=14))
    for z in (FRAME_Z0, FRAME_Z1):
        for sx in (1, -1):
            frame.append(_tube((sx * FX, -FY, z), (sx * FX, FY, z), TUBE_R, "SDT_Frame", 8))
        for sy in (1, -1):
            frame.append(_tube((-FX, sy * FY, z), (FX, sy * FY, z), TUBE_R, "SDT_Frame", 8))
    frame.append(_box(-0.335, 0.335, -0.425, 0.425, 0.048, 0.060, "SDT_PaintDark"))
    frame.append(_tube((-FX, 0.0, FRAME_Z1), (FX, 0.0, FRAME_Z1), 0.014, "SDT_Frame", 8))
    ring = [Vector((0.0, 0.034 * math.sin(2 * math.pi * k / 20), FRAME_Z1 + 0.034 + 0.034 * math.cos(2 * math.pi * k / 20)))
            for k in range(21)]
    frame.append(_sweep(ring, 0.007, "SDT_Steel", 8))

    # ---------------------------------------------------------------- kryt, nádrž
    body.append(_cbox(-HX, HX, HY0, HY1, HZ0, HZ1, "SDT_GenOrange", 0.012))
    tx, ty0, ty1, tz = TANK
    body.append(_cbox(-HX, tx, ty0, ty1, HZ0, tz, "SDT_TankBlack", 0.014))
    for y in (ty0 + 0.05, ty1 - 0.05):
        body.append(_box(-HX + 0.01, tx - 0.01, y - 0.012, y + 0.012, tz, tz + 0.004, "SDT_Steel"))
    cx, cy = CAP_XY
    body.append(P.cylinder_z(_nm("n"), _w(cx, cy, tz + 0.015), 0.030, 0.030, "SDT_Steel", segments=16))
    body.append(P.cylinder_z(_nm("n"), _w(cx, cy, tz + 0.045), 0.038, 0.030, "SDT_Plastic", segments=16))
    body.append(P.cylinder_z(_nm("n"), _w(cx, cy, tz + 0.061), 0.025, 0.004, "SDT_LampAmber", segments=16))
    body.append(_box(cx - 0.030, cx + 0.030, cy - 0.006, cy + 0.006, tz + 0.061, tz + 0.067, "SDT_Plastic"))
    # ukazatel hladiny: tmavé lůžko, průhledná trubice s naftou, kovové koncovky (stupnice je nálepka vpravo od ní)
    gy_, gz0, gz1 = 0.222, 0.14, 0.42
    body.append(_box(tx, tx + 0.004, gy_ - 0.011, gy_ + 0.011, gz0 - 0.012, gz1 + 0.012, "SDT_Plastic"))
    body.append(P.cylinder_z(_nm("g"), _w(tx + 0.010, gy_, (gz0 + gz1) / 2), 0.0075, gz1 - gz0, "SDT_LampAmber", segments=10))
    for z in (gz0 - 0.012, gz1 + 0.006):
        body.append(_box(tx, tx + 0.020, gy_ - 0.012, gy_ + 0.012, z, z + 0.012, "SDT_Steel"))

    # zadní čelo nádrže: pásky, vypouštěcí šroub, odvzdušnění
    for x in (-0.18, 0.18):
        body.append(_box(x - 0.016, x + 0.016, ty1, ty1 + 0.004, HZ0 + 0.01, tz - 0.01, "SDT_Steel"))
    body.append(_cyl((-0.25, ty1 + 0.008, 0.13), (0, 1, 0), 0.013, 0.016, "SDT_Steel", 6))
    body.append(_cyl((0.0, ty1 + 0.006, 0.50), (0, 1, 0), 0.020, 0.012, "SDT_Mesh", 14))

    # ---------------------------------------------------------------- žaluzie
    body += _louvre("+X", (HX, -0.10, 0.15), 0.48, 0.10, 5)
    body += _louvre("-X", (-HX, -0.10, 0.34), 0.50, 0.42, 10)
    body += _louvre("-Y", (0.0, HY0, 0.34), 0.50, 0.42, 10)

    # ---------------------------------------------------------------- panel
    px, py0, pz0 = PANEL
    pw, ph = L.GEN_PANEL_SIZE
    body.append(_box(HX, px, py0, py0 + pw, pz0, pz0 + ph, "SDT_PaintDark"))
    lip = 0.008
    body.append(_box(HX, px + 0.006, py0 - lip, py0 + pw + lip, pz0 + ph, pz0 + ph + lip, "SDT_Frame"))
    body.append(_box(HX, px + 0.006, py0 - lip, py0 + pw + lip, pz0 - lip, pz0, "SDT_Frame"))
    body.append(_box(HX, px + 0.006, py0 - lip, py0, pz0, pz0 + ph, "SDT_Frame"))
    body.append(_box(HX, px + 0.006, py0 + pw, py0 + pw + lip, pz0, pz0 + ph, "SDT_Frame"))

    def at(name):
        u, v = L.GEN_PANEL[name]
        return py0 + u, pz0 + v

    X = Vector((1, 0, 0))
    y, z = at("volt")
    body.append(_ring((px + 0.006, y, z), X, 0.0275, 0.034, 0.012, "SDT_TankBlack", 24))
    y, z = at("hours")
    for sgn in (1, -1):
        z0_, z1_ = sorted((z + sgn * 0.014, z + sgn * 0.021))
        body.append(_box(px, px + 0.007, y - 0.041, y + 0.041, z0_, z1_, "SDT_Frame"))
        y0_, y1_ = sorted((y + sgn * 0.035, y + sgn * 0.041))
        body.append(_box(px, px + 0.007, y0_, y1_, z - 0.021, z + 0.021, "SDT_Frame"))
    for name, mat in (("ledRun", "SDT_LedGreen"), ("ledOil", "SDT_LampRed"), ("ledTemp", "SDT_LampAmber")):
        y, z = at(name)
        body.append(_ring((px + 0.0035, y, z), X, 0.0075, 0.0115, 0.007, "SDT_Frame", 14))
        body.append(P.cylinder_x(_nm("l"), _w(px + 0.0035, y, z), 0.0078, 0.006, mat, segments=14))
    y, z = at("key")
    body.append(P.cylinder_x(_nm("k"), _w(px + 0.004, y, z), 0.021, 0.008, "SDT_Steel", segments=20))
    body.append(P.cylinder_x(_nm("k"), _w(px + 0.012, y, z), 0.014, 0.010, "SDT_TankBlack", segments=16))
    body.append(_box(px + 0.016, px + 0.026, y - 0.0035, y + 0.0035, z - 0.004, z + 0.020, "SDT_Steel"))
    body.append(_box(px + 0.026, px + 0.032, y - 0.011, y + 0.011, z + 0.014, z + 0.030, "SDT_LampRed"))
    y, z = at("preheat")
    body.append(_ring((px + 0.003, y, z), X, 0.0125, 0.0165, 0.006, "SDT_Frame", 18))
    body.append(P.cylinder_x(_nm("p"), _w(px + 0.008, y, z), 0.0125, 0.010, "SDT_LampAmber", segments=18))
    y, z = at("rocker")
    body.append(_box(px, px + 0.008, y - 0.024, y + 0.024, z - 0.015, z + 0.015, "SDT_Frame"))
    a = math.radians(12)
    body.append(_bb((px + 0.014, y, z), Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0)),
                    Vector((0, 0, 1)), (0.012, 0.038, 0.024), "SDT_TankBlack"))
    y, z = at("mcb")
    body.append(_box(px, px + 0.018, y - 0.018, y + 0.018, z - 0.028, z + 0.028, "SDT_ChargerGrey"))
    body.append(_box(px + 0.018, px + 0.026, y - 0.007, y + 0.007, z + 0.002, z + 0.024, "SDT_TankBlack"))
    body.append(_box(px + 0.026, px + 0.029, y - 0.007, y + 0.007, z + 0.018, z + 0.024, "SDT_LampAmber"))
    y, z = at("earth")
    body.append(P.cylinder_x(_nm("e"), _w(px + 0.008, y, z), 0.0055, 0.016, "SDT_Steel", segments=10))
    body.append(P.cylinder_x(_nm("e"), _w(px + 0.004, y, z), 0.010, 0.008, "SDT_Steel", segments=6))
    body.append(P.cylinder_x(_nm("e"), _w(px + 0.014, y, z), 0.009, 0.005, "SDT_Steel", segments=6))

    # ---------------------------------------------------------------- vzduchový filtr na střeše
    fx, fy = -0.18, -0.24
    body.append(P.cylinder_z(_nm("a"), _w(fx, fy, HZ1 + 0.055), 0.048, 0.11, "SDT_PaintDark", segments=18))
    body.append(P.cylinder_z(_nm("a"), _w(fx, fy, HZ1 + 0.117), 0.050, 0.014, "SDT_Steel", segments=18))
    body.append(P.cylinder_z(_nm("a"), _w(fx, fy, HZ1 + 0.055), 0.052, 0.012, "SDT_Steel", segments=18))
    body.append(_sweep(_fillet([(fx, fy, HZ1 + 0.05), (fx - 0.09, fy, HZ1 + 0.05), (fx - 0.09, fy, HZ1)], 0.03, 5),
                       0.016, "SDT_Rubber", 10))

    # ---------------------------------------------------------------- výfuk
    my0, my1, mz, mr = MUFFLER
    exh.append(_tube((EXH_X, my0, mz), (EXH_X, my1, mz), mr, "SDT_CastIron", 20))
    exh.append(_tube((EXH_X, my0, mz), (EXH_X, my0 - 0.03, mz), mr, "SDT_CastIron", 20, r_end=TAIL_R + 0.004))
    exh.append(_tube((EXH_X, my1, mz), (EXH_X, my1 + 0.03, mz), mr, "SDT_CastIron", 20, r_end=TAIL_R + 0.004))
    for y in (my0 + 0.05, my1 - 0.05):
        exh.append(_tube((EXH_X, y - 0.008, mz), (EXH_X, y + 0.008, mz), mr + 0.004, "SDT_Steel", 20))
        exh.append(_box(EXH_X - 0.034, EXH_X + 0.034, y - 0.02, y + 0.02, HZ1, mz - mr + 0.006, "SDT_Frame"))
    exh.append(P.cylinder_z(_nm("x"), _w(EXH_X, 0.10, HZ1 + 0.004), 0.040, 0.008, "SDT_Steel", segments=16))
    exh.append(_sweep(_fillet([(EXH_X, 0.10, HZ1), (EXH_X, 0.10, mz), (EXH_X, my1 + 0.03, mz)], 0.035, 6),
                      TAIL_R, "SDT_Steel", 12))
    ty, tz_ = TAIL_TURN
    mouth, d = exhaust_geometry()
    exh.append(_sweep(_fillet([(EXH_X, my0 - 0.03, mz), (EXH_X, ty, mz), (EXH_X, ty, tz_), tuple(mouth)], 0.06, 8),
                      TAIL_R, "SDT_Steel", 12))
    exh.append(_tube((EXH_X, ty, HZ1), (EXH_X, ty, mz + 0.03), 0.010, "SDT_Steel", 8))
    exh.append(_box(EXH_X - 0.03, EXH_X + 0.03, ty - 0.03, ty + 0.03, HZ1, HZ1 + 0.006, "SDT_Frame"))
    exh.append(_ring(tuple(mouth + d * 0.004), d, TAIL_R - 0.006, TAIL_R + 0.006, 0.020, "SDT_Steel", 16))
    exh.append(_cyl(tuple(mouth + d * 0.001), d, TAIL_R - 0.006, 0.002, "SDT_Plastic", 16))

    # ---------------------------------------------------------------- zásuvka nabíječky (název a poloha jako dřív)
    cable_end = None
    if rear_socket:
        # kabel je napevno v zadní stěně nádrže: černá průchodka s ochranou proti ohybu a převlečnou maticí, žádná zásuvka
        Y = Vector((0, 1, 0))
        cx_, cz_ = -0.10, 0.30
        sock = [
            _cyl((cx_, ty1 + 0.004, cz_), Y, 0.044, 0.008, "SDT_PaintDark", 20),
            _cyl((cx_, ty1 + 0.019, cz_), Y, 0.030, 0.022, "SDT_Steel", 6),
            _cyl((cx_, ty1 + 0.045, cz_), Y, 0.024, 0.030, "SDT_Rubber", 16, r_end=0.016),
            _cyl((cx_, ty1 + 0.073, cz_), Y, 0.016, 0.026, "SDT_Rubber", 14, r_end=0.011),
        ]
        cable_end = _w(cx_, ty1 + 0.085, cz_)
    else:
        sx = socket[0] - _O.x
        sy, sz = socket[1] - _O.y, socket[2] - _O.z
        sock = [
            P.cylinder_x(_nm("s"), _w(sx - 0.003, sy, sz), 0.038, 0.004, "SDT_PaintDark", segments=24),
            _ring((sx + 0.006, sy, sz), X, 0.022, 0.030, 0.016, "SDT_HoseBlue", 24),
            P.cylinder_x(_nm("s"), _w(sx + 0.003, sy, sz), 0.022, 0.002, "SDT_Plastic", segments=20),
            _ring((sx + 0.014, sy, sz), X, 0.030, 0.033, 0.002, "SDT_Steel", 24),
        ]
        for dy, dz in ((-0.009, 0.0), (0.009, 0.0), (0.0, 0.012)):
            sock.append(P.cylinder_x(_nm("s"), _w(sx + 0.005, sy + dy, sz + dz), 0.0035, 0.006, "SDT_Steel", segments=8))

    # ---------------------------------------------------------------- nálepky
    decals.append(P.decal_quad(_nm("d"), _w(px, py0, pz0), (0, 1, 0), (0, 0, 1), pw, ph, "genPanel"))
    tri_w, tri_h = 0.075, 0.075 * 111.0 / 128.0
    for k in range(3):
        decals.append(_decal_tri(_nm("d"), _w(HX, -0.335 + k * 0.09, 0.219), (0, 1, 0), (0, 0, 1), tri_w, tri_h, "genWarn",
                                 (k / 3.0, 0.0, (k + 1) / 3.0, 1.0)))
    decals.append(P.decal_quad(_nm("d"), _w(HX, 0.02, 0.215), (0, 1, 0), (0, 0, 1), 0.11, 0.0688, "genPlate"))
    decals.append(P.decal_quad(_nm("d"), _w(tx, 0.185, 0.445), (0, 1, 0), (0, 0, 1), 0.18, 0.12, "dieselLabel"))
    decals.append(P.decal_quad(_nm("d"), _w(tx, 0.238, gz0), (0, 1, 0), (0, 0, 1), 0.064, 0.256, "genGauge"))

    # ---------------------------------------------------------------- sloučení do meshů
    merged = [P.merge(f"Gen_{tag}_Frame", frame), P.merge(f"Gen_{tag}_Body", body), P.merge(f"Gen_{tag}_Exhaust", exh),
              P.merge(f"Gen_{tag}_ChargeSocket", sock)]
    dec = P.merge(f"Gen_{tag}_Decals", decals)
    dec["i3D_decalLayer"] = 1
    dec["i3D_castsShadows"] = False
    merged.append(dec)

    exhaust_pos = _w(*(mouth + d * 0.03))
    result = {"exhaust": _w(*mouth), "cap": _w(cx, cy, tz + 0.067), "objects": merged}
    if cable_end is not None:
        result["cable"] = cable_end
    if mirror:
        x0 = _O.x
        mirror_objects(merged, x0)
        exhaust_pos.x = 2 * x0 - exhaust_pos.x
        for key in ("exhaust", "cap", "cable"):
            if key in result:
                result[key].x = 2 * x0 - result[key].x
    e = P.empty("generatorExhaust" if tag == "0" else f"generatorExhaust{int(tag) + 1}", exhaust_pos)
    e.matrix_world = Matrix.Translation(exhaust_pos) @ Matrix.Rotation(math.radians(-TAIL_TILT_DEG), 4, "X")
    result["exhaust_node"] = e
    return result
