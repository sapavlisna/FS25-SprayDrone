"""Parametricky postaví postřikový dron podle DJI Agras ve třech velikostech (SPECS, viz docs/PLAN-0.9.md).

"M" = T50: s vrtulemi rozložený 2800 x 3085 mm (rozteč motorů 1425 x 1710 mm; 1590 x 1900 je rozměr se SLOŽENÝMI vrtulemi), výška 820 mm,
nádrž 40 l, souosé bílé vrtule o průměru 1375 mm, 4 trysky.
"S" = T25: jednoduché černé vrtule 50" s oranžovou špičkou, nádrž 20 l, 2 trysky pod zadními motory (rozteč 1368 mm).
"L" = T100: souosé černé vrtule 62" s oranžovou špičkou, nádrž 100 l, 2 trysky na ramenech postřiku (rozteč 1834 mm).
Rozteč motorů = rozměr rozloženého dronu s vrtulemi minus průměr vrtule (S 2585 x 2675 - 1270, M 2800 x 3085 - 1375, L 3220 x 3224 - 1574).

Vrtule jdou postavit složené (parkování na plošině vleku) i rozložené (let).

Tvarosloví podle oficiálních fotek DJI (reference/drone/): šedý fasetovaný trup s válcovým radarem, velká bílá
fasetovaná nádrž pod ním, štíhlá karbonová ramena s černým skládacím kloubem a žlutým štítkem, souosé motorové
gondoly, štíhlé zúžené listy, černé A-nohy s podélnými lyžinami. Díly se skládají do jednoho meshe na skupinu
(Mesh: materiály jako sloty), aby dron nebyl stovky objektů.

Spustit v Blenderu stejně jako build_trailer.py; helpery a materiály sdílí s ním.
"""

import os
import sys

import bpy
import bmesh
import math
import mathutils
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_trailer as parts
import sdt_parts as P

COLLECTION_NAME = "SprayDrone"

# arm_span: rozteč motorů podélně a napříč; body: délka, šířka, výška trupu; blade: délka, tětiva u kořene a u špičky;
# detail: měřítko drobných dílů (radar, gondoly, trubky); skid: y lyžiny, půldélka lyžiny, x nohou;
# fold: azimut předních a zadních ramen po složení; nozzles: ramena s tryskou a jejich vzdálenost od osy napříč
# (None = pod motorem); boom: tryska na rameni postřiku vně motoru; esc: regulátor s žebry na rameni;
# prop: materiál listů a materiál špičky (None = bez barevné špičky)
SPECS = {
    "M": dict(arm_span=(1.425, 1.71), arm_z=0.56, body=(0.56, 0.50, 0.17), tank_top=(0.58, 0.48),
              tank_bottom=(0.44, 0.36), tank_h=0.30, blade=(0.68, 0.095, 0.045), motor_r=0.075,
              levels=("Top", "Bottom"), detail=1.0, mast_h=0.15, skid=(0.42, 0.46, 0.30), fold=(160, 176),
              nozzles=(1, 2, 3, 4), nozzle_y=None, boom=False, esc=False, prop=("Drone_White", None),
              blade_fold={"Top": (10.0, "pairOut"), "Bottom": (10.0, "pairOut")}),
    "S": dict(arm_span=(1.315, 1.405), arm_z=0.55, body=(0.44, 0.40, 0.15), tank_top=(0.46, 0.38),
              tank_bottom=(0.35, 0.29), tank_h=0.24, blade=(0.635, 0.085, 0.04), motor_r=0.065,
              levels=("Top",), detail=0.85, mast_h=0.155, skid=(0.34, 0.38, 0.24), fold=(157, 176),
              nozzles=(3, 4), nozzle_y=0.684, boom=False, esc=True, prop=("Carbon", "Drone_Accent_A"),
              blade_fold={"Top": (10.0, "pair")}),
    "L": dict(arm_span=(1.646, 1.65), arm_z=0.67, body=(0.66, 0.56, 0.20), tank_top=(0.74, 0.62),
              tank_bottom=(0.58, 0.48), tank_h=0.38, blade=(0.787, 0.12, 0.055), motor_r=0.10,
              levels=("Top", "Bottom"), detail=1.2, mast_h=0.09, skid=(0.56, 0.58, 0.40), fold=(157, 176),
              nozzles=(3, 4), nozzle_y=0.917, boom=True, esc=True, prop=("Carbon", "Drone_Accent_A"),
              blade_fold={"Top": (10.0, "pairOut"), "Bottom": (10.0, "pairOut")}),
}

# výchozí parametry (M) pro volání bez spec
ARM_SPAN_X, ARM_SPAN_Y = SPECS["M"]["arm_span"]
PROPS_FOLDED = True
ARMS_FOLDED = 0.0  # 0 = rozloženo, 1 = složeno podél trupu

RING_SEGMENTS = 20
TUBE_SEGMENTS = 12

BLACK = "SDT_TankBlack"
GREY = "Drone_Grey"
GREY_DARK = "Drone_GreyDark"
WHITE = "Drone_White"
YELLOW = "SDT_LampAmber"


def clear_collection():
    if COLLECTION_NAME in bpy.data.collections:
        coll = bpy.data.collections[COLLECTION_NAME]
        for obj in list(coll.objects):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
    else:
        coll = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(coll)
    return coll


def circle_ring(r, z, segments=RING_SEGMENTS):
    return [
        Vector((r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments), z))
        for i in range(segments)
    ]


def octagon_ring(cx, cy, z, hx, hy, cut):
    """Obdélník se seříznutými rohy, proti směru hodin shora."""
    return [Vector((cx + x, cy + y, z)) for x, y in (
        (hx, -hy + cut), (hx, hy - cut), (hx - cut, hy), (-hx + cut, hy),
        (-hx, hy - cut), (-hx, -hy + cut), (-hx + cut, -hy), (hx - cut, -hy))]


def _axis_frame(direction):
    u = Vector(direction).normalized()
    up = Vector((0, 0, 1))
    if abs(u.dot(up)) > 0.98:
        up = Vector((1, 0, 0))
    n1 = u.cross(up).normalized()
    return u, n1, u.cross(n1).normalized()


def tube_rings(p0, p1, radii, segments=TUBE_SEGMENTS):
    """Prstence pro kónickou trubku - `radii` je poloměr v každé stanici podél osy."""
    p0, p1 = Vector(p0), Vector(p1)
    _, n1, n2 = _axis_frame(p1 - p0)
    rings = []
    for i, r in enumerate(radii):
        t = i / (len(radii) - 1)
        center = p0.lerp(p1, t)
        rings.append([
            center + n1 * (r * math.cos(2 * math.pi * k / segments)) + n2 * (r * math.sin(2 * math.pi * k / segments))
            for k in range(segments)
        ])
    return rings


class Mesh:
    """Jeden objekt z víc dílů: geometrie se skládá do jednoho bmesh, materiály jsou sloty.

    Všechny body se zadávají v souřadnicích dronu a posouvají se o `off` (počátek dronu ve scéně).
    """

    def __init__(self, off):
        self.bm = bmesh.new()
        self.mats = []
        self.off = Vector(off)

    def _slot(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def loft(self, rings, mat, smooth=True, cap_start=True, cap_end=True, band_mats=None):
        """Těleso mezi průřezy (proti směru hodin kolem směru lofu). band_mats: materiál každého pásu mezi průřezy."""
        bm = self.bm
        first, last = [Vector(p) for p in rings[0]], [Vector(p) for p in rings[-1]]
        ring_normal = sum((first[i].cross(first[(i + 1) % len(first)]) for i in range(len(first))), Vector())
        axis = sum(last, Vector()) / len(last) - sum(first, Vector()) / len(first)
        if len(rings) > 1 and ring_normal.dot(axis) < 0:
            # lof jde proti normále průřezů (nádrž shora dolů, hubice dolů): bez otočení míří plochy dovnitř
            # a backface culling ve hře odstraní blízké stěny
            rings = rings[::-1]
            band_mats = band_mats[::-1] if band_mats else band_mats
            cap_start, cap_end = cap_end, cap_start
        rv = [[bm.verts.new(Vector(p) + self.off) for p in ring] for ring in rings]
        n = len(rv[0])
        for b, (a, c) in enumerate(zip(rv, rv[1:])):
            slot = self._slot(band_mats[b] if band_mats else mat)
            for k in range(n):
                f = bm.faces.new((a[k], a[(k + 1) % n], c[(k + 1) % n], c[k]))
                f.material_index, f.smooth = slot, smooth
        slot = self._slot(band_mats[0] if band_mats else mat)
        if cap_start:
            f = bm.faces.new(list(reversed(rv[0])))
            f.material_index = slot
        if cap_end:
            f = bm.faces.new(rv[-1])
            f.material_index = self._slot(band_mats[-1] if band_mats else mat)

    def tube(self, p0, p1, radii, mat, segments=TUBE_SEGMENTS, smooth=True):
        self.loft(tube_rings(p0, p1, radii, segments), mat, smooth=smooth)

    def lathe(self, cx, cy, profile, mat, segments=16, smooth=True, cap_start=True, cap_end=True):
        """Těleso otáčením kolem svislé osy: profile = [(poloměr, z)] odspodu nahoru."""
        self.loft([[Vector((cx + r * math.cos(2 * math.pi * i / segments), cy + r * math.sin(2 * math.pi * i / segments), z))
                    for i in range(segments)] for r, z in profile], mat, smooth=smooth,
                  cap_start=cap_start, cap_end=cap_end)

    def solid(self, center, half, mat, frame=None, cut=0.0, ch=0.0, smooth=False, taper=None):
        """Kvádr se seříznutými hranami, osy `frame` = (a, b, c) pravotočivě; průřezy jdou podél a.
        half = (ha, hb, hc), cut = seříznutí podélných hran, ch = zkosení konců, taper = (tb, tc) měřítko konce +a."""
        a, b, c = (frame or (Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, 1, 0))))
        ha, hb, hc = half
        center = Vector(center)
        cuts = ((-ha, -1), (-ha + ch, 0), (ha - ch, 0), (ha, 1)) if ch else ((-ha, 0), (ha, 0))
        rings = []
        for pos, end in cuts:
            shrink = ch if end else 0.0
            tb, tc = (taper if taper and pos > 0 else (1.0, 1.0))
            hb2, hc2 = (hb - shrink) * tb, (hc - shrink) * tc
            ct = min(cut, hb2, hc2)
            pts2 = ((hb2, -hc2 + ct), (hb2, hc2 - ct), (hb2 - ct, hc2), (-hb2 + ct, hc2),
                    (-hb2, hc2 - ct), (-hb2, -hc2 + ct), (-hb2 + ct, -hc2), (hb2 - ct, -hc2))
            rings.append([center + a * pos + b * y + c * z for y, z in pts2])
        self.loft(rings, mat, smooth=smooth)

    def paint_beyond(self, plane_co, plane_no, mat):
        """Rozřízne mesh rovinou a plochy na straně normály přebarví: dvoubarevný trup se švem přesně v rovině."""
        bm = self.bm
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=Vector(plane_co) + self.off, plane_no=plane_no)
        slot = self._slot(mat)
        n = Vector(plane_no)
        for f in bm.faces:
            if (f.calc_center_median() - Vector(plane_co) - self.off).dot(n) > 0:
                f.material_index = slot

    def build(self, coll, name):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(parts.get_material(m))
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        return obj


def set_material(obj, mat_name):
    obj.data.materials.clear()
    obj.data.materials.append(parts.get_material(mat_name))
    return obj


def arm_positions(spec=None):
    span_x, span_y = (spec or SPECS["M"])["arm_span"]
    return [
        (sx * span_x / 2, sy * span_y / 2)
        for sx in (1, -1)
        for sy in (1, -1)
    ]


def add_arm_pivot(coll, name, location):
    """Kloub ramene - v i3d z něj bude animovaný uzel, proto vlastní prázdný objekt."""
    pivot = bpy.data.objects.new(name, None)
    pivot.empty_display_type = 'PLAIN_AXES'
    pivot.empty_display_size = 0.12
    pivot.location = location
    coll.objects.link(pivot)
    return pivot


def parent_keep_transform(obj, pivot):
    obj.parent = pivot
    obj.matrix_parent_inverse = pivot.matrix_world.inverted()


def blade_fold_angles(spec, rotor, ax, ay):
    """Svět. úhly dvou složených listů a jejich natočení do rozložené polohy (přímka napříč ramene), radiány.
    spec["blade_fold"][rotor] = (stupně, režim): "side"/"front" - oba listy na jedné přímce přes střed rotoru, odkloněné od ramene
    o tolik stupňů ("front" jen u předních ramen); "pair" - oba listy míří podél ramene dovnitř k trupu a svírají mezi sebou tolik stupňů;
    "pairOut" - totéž ven od trupu (souosé M a L: dovnitř spodní listy narážejí do trupu). Volitelný třetí prvek stočí dvojici o tolik
    stupňů (zrcadlově podle kvadrantu ramene).
    Hodnoty jsou voleny tak, aby se složené listy neprotínaly s trupem, rameny ani bednou Mini (tmp/blade_fold_test.py, tmp/mini_blade_scan.py)."""
    deg, mode, *skew = spec["blade_fold"].get(rotor, (0.0, "side"))
    arm = math.atan2(ay, ax)
    if mode in ("pair", "pairOut"):
        half = math.radians(deg) / 2
        base = arm + math.pi if mode == "pair" else arm
        if skew:
            base += math.radians(skew[0]) * math.copysign(1.0, ay * ax)
        folded = [base + half, base - half]
    else:
        if mode == "front":
            off = math.copysign(math.radians(deg), ay * ax) if ax > 0 else 0.0
        else:
            off = math.copysign(math.radians(deg), ay)
        folded = [arm + off, arm + off + math.pi]
    wrap = lambda a: (a + math.pi) % (2 * math.pi) - math.pi
    deltas = [wrap(arm + math.pi / 2 + b * math.pi - folded[b]) for b in range(2)]
    return folded, deltas


def brand_decals(coll, name, tank, off, upper, lower, tank_len, k):
    """Polepy značky na šikmých stěnách nádrže (mezi průřezy upper a lower = (z, hx, hy), stěna je tam rovinná): lockup
    s tmavým textem na obou bocích a znak na čele. Všechny designy (sdt_parts.brand_decal_set) pod nádrží; uzly
    brand_<KEY>_<name>_Tank* nesou jméno dronu, takže se drony ve vleku nepletou a export je přepíná s designem vleku."""
    (z1, hx1, hy1), (z2, hx2, hy2) = upper, lower
    saved = P._coll, P._root
    P._coll, P._root = coll, None   # polepy patří do kolekce dronu, ať je clear_collection smaže s ním
    try:
        for side, sy in (("L", 1), ("R", -1)):
            center = off + Vector((0, sy * (hy1 + hy2) / 2, (z1 + z2) / 2))
            normal = Vector((0, sy * (z1 - z2), -(hy1 - hy2)))
            P.brand_decal_set(f"{name}_Tank{side}", "lockupOnLight", center, normal, (0, 0, 1), 0.45 * tank_len, parent=tank)
        center = off + Vector(((hx1 + hx2) / 2, 0, (z1 + z2) / 2))
        P.brand_decal_set(f"{name}_TankF", "mark", center, Vector((z1 - z2, 0, -(hx1 - hx2))), (0, 0, 1), 0.09 * k,
                          parent=tank)
    finally:
        P._coll, P._root = saved


def build_drone(coll, name="Drone", origin=(0, 0, 0), accent="Drone_Accent_A", folded=PROPS_FOLDED,
                arms_folded=ARMS_FOLDED, spec=None):
    s = spec or SPECS["M"]
    k = s["detail"]
    arm_z = s["arm_z"]
    body_len, body_width, body_height = s["body"]
    tank_top, tank_bottom, tank_height = s["tank_top"], s["tank_bottom"], s["tank_h"]
    motor_radius = s["motor_r"]
    coax = len(s["levels"]) == 2
    skid_z = 0.02
    off = Vector(origin)
    ox, oy, oz = origin

    collected = []  # díly právě stavěného ramene, aby šly zavěsit pod jeho kloub

    def emit(mesh, part, arm=False):
        obj = mesh.build(coll, f"{name}_{part}")
        if arm:
            collected.append(obj)
        return obj

    body_z = arm_z
    hull_bottom = body_z - body_height / 2
    hull_top = body_z + body_height / 2
    tank_top_z = hull_bottom - 0.01
    tank_bottom_z = tank_top_z - tank_height
    hx, hy = body_len / 2, body_width / 2

    # trup: šedá fasetovaná skříň s plochým hřbetem (na něm leží šachta baterie), seříznuté rohy
    m = Mesh(off)
    cut = 0.30 * min(hx, hy)
    stations = ((-body_height / 2, 0.78, 0.74), (-body_height / 2 + 0.27 * body_height, 0.96, 0.95),
                (0.0, 1.0, 1.0), (body_height / 2 - 0.30 * body_height, 0.97, 0.96), (body_height / 2, 0.82, 0.80))
    m.loft([octagon_ring(0, 0, body_z + dz, hx * sx, hy * sy, cut * min(sx, sy)) for dz, sx, sy in stations],
           GREY, smooth=False)
    m.paint_beyond((-0.03 * k, 0, 0), (-1, 0, 0), WHITE)   # zadní část hřbetu je horní stěna nádrže
    emit(m, "Body")

    # radar na přední části hřbetu: matný šedý válec s límcem
    mast_r = 0.062 * k
    mast_h = s["mast_h"]
    mast_base = hull_top - 0.005
    mast_x = hx - 0.15 * k
    m = Mesh(off)
    m.lathe(mast_x, 0, [(0.076 * k, mast_base), (0.076 * k, mast_base + 0.016 * k), (mast_r * 1.04, mast_base + 0.02 * k)],
            GREY_DARK, segments=20)
    m.lathe(mast_x, 0, [(mast_r, mast_base + 0.02 * k), (mast_r, mast_base + mast_h - 0.01 * k),
                        (mast_r * 0.94, mast_base + mast_h)], GREY, segments=20)
    emit(m, "GpsMast")

    # nos: čelní modul s dvojicemi světel a čočkami po stranách
    nose_x = hx
    m = Mesh(off)
    m.solid((nose_x + 0.02 * k, 0, body_z - 0.01 * k), (0.07 * k, 0.60 * hy, 0.40 * body_height), GREY,
            frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=0.05 * k, ch=0.02 * k)
    face_x = nose_x + 0.09 * k
    for side in (1, -1):
        for lz in (-0.028 * k, 0.028 * k):
            cy_ = side * 0.36 * hy
            cz = body_z - 0.01 * k + lz
            m.tube((face_x - 0.006 * k, cy_, cz), (face_x + 0.004 * k, cy_, cz), [0.022 * k] * 2, WHITE, segments=14)
            m.tube((face_x, cy_, cz), (face_x + 0.012 * k, cy_, cz), [0.015 * k] * 2, "Glass_Dark", segments=14)
    emit(m, "Nose")

    # zadní radar (plochý modul na zádi)
    m = Mesh(off)
    m.solid((-hx - 0.012 * k, 0, body_z - 0.045 * k), (0.03 * k, 0.11 * k, 0.035 * k), GREY_DARK,
            frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=0.012 * k, ch=0.006 * k)
    emit(m, "RadarRear")

    # nádrž: velká bílá fasetovaná skořepina pod trupem, zúžená ke dnu, s okénkem stavoznaku
    m = Mesh(off)
    stations = []
    for t in (0.0, 0.30, 0.42, 0.80, 1.0):
        u = 0.0 if t <= 0.30 else (t - 0.30) / 0.70
        ax_ = tank_top[0] + (tank_bottom[0] - tank_top[0]) * u
        by_ = tank_top[1] + (tank_bottom[1] - tank_top[1]) * u
        sc = 0.93 if t == 1.0 else 1.0
        stations.append((tank_top_z - tank_height * t, ax_ / 2 * sc, by_ / 2 * sc))
    m.loft([octagon_ring(0, 0, z, ax_, by_, 0.28 * min(ax_, by_)) for z, ax_, by_ in stations], WHITE, smooth=False)
    m.solid((tank_top[0] / 2 + 0.001, -0.10 * k, tank_top_z - 0.16 * tank_height), (0.11 * tank_height, 0.02 * k, 0.004),
            "Glass_Dark", frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((-1, 0, 0))))
    tank = emit(m, "Tank")
    brand_decals(coll, name, tank, off, stations[1], stations[3], tank_top[0], k)

    # čerpadla a rozdělovač pod nádrží
    m = Mesh(off)
    pz = tank_bottom_z - 0.03 * k
    for py in (-0.06 * k, 0.06 * k):
        m.tube((-0.10 * k, py, pz), (0.10 * k, py, pz), [0.038 * k, 0.046 * k, 0.046 * k, 0.038 * k], GREY_DARK, segments=14)
        m.tube((0.10 * k, py, pz), (0.12 * k, py, pz), [0.030 * k, 0.030 * k], accent, segments=12)
    m.solid((0, 0, tank_bottom_z - 0.075 * k), (0.09 * k, 0.11 * k, 0.025 * k), BLACK, cut=0.01 * k)
    emit(m, "Pump")

    # ramena, gondoly, vrtule - každé rameno pod vlastním kloubem, aby šlo složit
    nozzle_no = 0
    tip_r, root_r = 0.024 * k, 0.029 * k
    for idx, (ax, ay) in enumerate(arm_positions(s), start=1):
        root = Vector((math.copysign(hx - 0.06 * k, ax), math.copysign(hy - 0.06 * k, ay), body_z))
        tip = Vector((ax, ay, arm_z + 0.05 * k))
        collected.clear()
        d = (tip - root).normalized()
        length = (tip - root).length
        side = Vector((0, 0, 1)).cross(d).normalized()
        frame = (d, side, d.cross(side).normalized())

        def at(dist):
            return root + d * dist

        m = Mesh(off)
        m.tube(at(0.06 * k), at(length - 0.03 * k), [root_r, root_r * 0.98, tip_r * 1.05, tip_r], "Carbon", segments=12)
        # kořenová patka a skládací kloub (černý plast) s pojistkou na horní straně
        m.solid(at(0.035 * k), (0.045 * k, 0.05 * k, 0.05 * k), BLACK, frame=frame, cut=0.012 * k, ch=0.01 * k)
        m.solid(at(0.17 * k), (0.072 * k, 0.046 * k, 0.05 * k), BLACK, frame=frame, cut=0.014 * k, ch=0.012 * k)
        m.solid(at(0.17 * k) + Vector((0, 0, 0.05 * k)), (0.03 * k, 0.03 * k, 0.012 * k), GREY_DARK, frame=frame,
                cut=0.005 * k)
        # žlutý výstražný pásek na trubce
        m.tube(at(0.30 * k), at(0.34 * k), [root_r * 1.08] * 2, YELLOW, segments=12)
        if s["esc"]:  # regulátor s chladicími žebry na horní straně ramene
            ec = at(length - 0.30 * k) + Vector((0, 0, 0.038 * k))
            m.solid(ec, (0.085 * k, 0.034 * k, 0.020 * k), GREY, frame=frame, cut=0.006 * k, ch=0.006 * k)
            for f_ in range(5):
                m.solid(ec + d * (-0.06 * k + f_ * 0.03 * k) + Vector((0, 0, 0.022 * k)), (0.006 * k, 0.03 * k, 0.010 * k),
                        GREY_DARK, frame=frame)
        # koncová objímka pod gondolou
        m.tube(at(length - 0.09 * k), at(length - 0.005 * k), [tip_r * 1.35, tip_r * 1.45, tip_r * 1.45, tip_r * 1.3],
               BLACK, segments=12)
        emit(m, f"Arm_{idx}", arm=True)

        # gondola: upevnění na konci ramene, statorové válce a bílé zvony (souosé nad i pod ramenem)
        mz = tip.z
        mr = motor_radius
        m = Mesh(off)
        cx, cy = ax, ay
        if coax:
            m.lathe(cx, cy, [(0.050 * k, mz - 0.040 * k), (0.054 * k, mz - 0.03 * k), (0.054 * k, mz + 0.03 * k),
                             (0.050 * k, mz + 0.040 * k)], BLACK, segments=18)
            for sgn in (1, -1):
                m.lathe(cx, cy, [(mr * 0.78, mz + sgn * 0.035 * k), (mr * 0.80, mz + sgn * 0.058 * k)], BLACK,
                        segments=20, cap_start=False, cap_end=False)
                m.lathe(cx, cy, [(mr * 0.86, mz + sgn * 0.052 * k), (mr, mz + sgn * 0.062 * k), (mr, mz + sgn * 0.086 * k),
                                 (mr * 0.90, mz + sgn * 0.096 * k), (mr * 0.45, mz + sgn * 0.098 * k)][::sgn],
                        WHITE, segments=20)
        else:
            m.lathe(cx, cy, [(0.050 * k, mz - 0.05 * k), (0.056 * k, mz - 0.03 * k), (0.056 * k, mz + 0.02 * k)],
                    BLACK, segments=18)
            m.lathe(cx, cy, [(mr * 0.80, mz + 0.015 * k), (mr * 0.86, mz + 0.03 * k), (mr, mz + 0.04 * k),
                             (mr, mz + 0.072 * k), (mr * 0.90, mz + 0.085 * k), (mr * 0.45, mz + 0.088 * k)],
                    WHITE, segments=20)
        emit(m, f"Motor_{idx}", arm=True)

        hubs = {"Top": mz + (0.107 if coax else 0.098) * k}
        if coax:
            hubs["Bottom"] = mz - 0.107 * k
        hubs = {lv: hubs[lv] for lv in s["levels"]}
        for tag, hz in hubs.items():
            up = tag == "Top"
            m = Mesh(off)
            sg = 1 if up else -1
            m.lathe(cx, cy, [(0.036 * k, hz - sg * 0.012 * k), (0.030 * k, hz + sg * 0.012 * k),
                             (0.014 * k, hz + sg * 0.024 * k)][::sg], GREY_DARK, segments=14)
            emit(m, f"Hub{tag}_{idx}", arm=True)

        arm_angle = math.atan2(ay, ax)
        for rotor, hz in hubs.items():
            for b in range(2):
                if folded:
                    # složené listy leží na jedné přímce přes střed rotoru (jeden dopředu, druhý dozadu), bez bočního posunu;
                    # směr přímky vůči rameni určuje BLADE_FOLD
                    angles, deltas = blade_fold_angles(s, rotor, ax, ay)
                    angle, fold_delta = angles[b], deltas[b]
                    side_off = 0.0
                else:
                    fold_delta = None
                    angle = b * math.pi + (0 if rotor == "Top" else math.pi / 2)
                    side_off = 0.0
                blade_obj = add_blade(coll, f"{name}_Blade_{idx}{rotor}{b}", (ox + ax, oy + ay, oz + hz), angle,
                                      side_off, up=(rotor == "Top"), blade=s["blade"], prop=s["prop"])
                if fold_delta is not None:
                    blade_obj["sdt_unfold_delta"] = fold_delta
                collected.append(blade_obj)

        # hadice podél ramene a rozprašovač pod gondolou (nebo na rameni postřiku vně motoru)
        if idx in s["nozzles"]:
            hose_drop = 0.055 * k
            hose_r = 0.010 * k
            m = Mesh(off)
            m.tube((root.x, root.y, root.z - hose_drop), (ax, ay, tip.z - hose_drop), [hose_r, hose_r], "SDT_HoseBlack",
                   segments=8)
            ny = ay if s["nozzle_y"] is None else math.copysign(s["nozzle_y"], ay)
            bz = tip.z - hose_drop
            if s["boom"]:
                # výložník s tryskou visí pod spodním rotorem (jeho listy by jinak metly nosník i trysku), hadice k němu
                # sestupuje osou motoru
                bz_top, bz = bz, hubs["Bottom"] - 0.060
                m.tube((ax, ay, bz_top), (ax, ay, bz), [0.014 * k] * 2, BLACK, segments=10)
                m.tube((ax, ay - math.copysign(0.02, ay), bz), (ax, ny, bz), [0.020 * k, 0.016 * k], BLACK, segments=10)
            nozzle_z = bz - 0.07 * k
            m.tube((ax, ny, bz), (ax, ny, nozzle_z + 0.02 * k), [hose_r * 1.2] * 2, BLACK, segments=8)
            m.lathe(ax, ny, [(0.02 * k, nozzle_z + 0.024 * k), (0.03 * k, nozzle_z + 0.014 * k), (0.03 * k, nozzle_z)], BLACK,
                    segments=14)
            m.lathe(ax, ny, [(0.03 * k, nozzle_z), (0.048 * k, nozzle_z - 0.014 * k), (0.052 * k, nozzle_z - 0.034 * k),
                             (0.040 * k, nozzle_z - 0.042 * k)], accent, segments=16)
            emit(m, f"Nozzle_{idx}", arm=True)
            nozzle_no += 1
            outlet = bpy.data.objects.new(f"{name}_SprayNozzle_{nozzle_no}", None)
            outlet.empty_display_type = "PLAIN_AXES"
            outlet.empty_display_size = 0.05
            outlet.location = off + Vector((ax, ny, nozzle_z - 0.042 * k))
            coll.objects.link(outlet)
            collected.append(outlet)

        arm_objs = list(collected)
        pivot = add_arm_pivot(coll, f"{name}_ArmPivot_{idx}", off + root)
        bpy.context.view_layer.update()
        for obj in arm_objs:
            parent_keep_transform(obj, pivot)
        # rotace až po zavěšení, jinak by ji parent inverse hned vyrušil
        base_az = math.atan2(ay - root.y, ax - root.x)
        fold_front, fold_rear = (math.radians(a) for a in s["fold"])
        target_az = math.copysign(fold_front if ax > 0 else fold_rear, ay)
        pivot.rotation_euler = (0, 0, (target_az - base_az) * arms_folded)

    # podvozek: A-nohy po stranách nádrže spojené horní příčkou, podélná lyžina, příčka mezi lyžinami
    skid_y, skid_half, leg_x = s["skid"]
    leg_r = 0.021 * k
    leg_top_z = tank_top_z - 0.03
    for side, sy in (("L", 1), ("R", -1)):
        y_out = sy * skid_y
        y_top = sy * (tank_top[1] / 2 + 0.014)
        m = Mesh(off)
        for tag, lx in (("F", leg_x), ("R", -leg_x)):
            top = Vector((lx * 0.55, y_top, leg_top_z))
            bottom = Vector((lx, y_out, skid_z + 0.03))
            m.tube(top, bottom, [leg_r * 1.05, leg_r, leg_r], BLACK, segments=10)
            m.solid(top, (0.04 * k, 0.03 * k, 0.05 * k), GREY_DARK, cut=0.01 * k, ch=0.008 * k)
        m.tube((-leg_x * 0.55, y_top, leg_top_z), (leg_x * 0.55, y_top, leg_top_z), [leg_r * 0.85] * 2, BLACK, segments=10)
        emit(m, f"Legs_{side}")
        m = Mesh(off)
        m.tube((-skid_half, y_out, skid_z), (skid_half, y_out, skid_z), [0.024 * k, 0.03 * k, 0.03 * k, 0.024 * k], BLACK,
               segments=10)
        emit(m, f"Skid_{side}")
        for tag, lx in (("F", skid_half - 0.04), ("R", -skid_half + 0.04)):
            m = Mesh(off)
            m.lathe(lx, y_out, [(0.034 * k, skid_z - 0.03), (0.04 * k, skid_z - 0.01), (0.032 * k, skid_z + 0.01)],
                    "SDT_Rubber", segments=12)
            emit(m, f"SkidPad_{side}{tag}")
        light = parts.add_box(coll, f"{name}_NavLight_{side}", (0.05, 0.03, 0.02),
                              (ox + skid_half - 0.06, oy + y_out, oz + skid_z + 0.04))
        set_material(light, "Lamp_Green" if sy > 0 else "Lamp_Red")
    m = Mesh(off)
    m.tube((0, skid_y, skid_z), (0, -skid_y, skid_z), [0.022 * k, 0.026 * k, 0.022 * k], BLACK, segments=10)
    emit(m, "SkidCross")


BLADE_STATIONS = (0.0, 0.08, 0.22, 0.42, 0.62, 0.80, 0.93, 1.0)
BLADE_SHAPE = (0.85, 1.0, 1.0, 0.92, 0.80, 0.66, 0.50, 0.20)
# pruh u špičky listu (rozsah t podél listu): nalepený barevný proužek, samostatný objekt <list>_Tip
BLADE_STRIPES = ((0.89, 0.97),)


def _blade_ring(t, length, chord_root, chord_tip, up, side_offset, grow=1.0):
    """Průřez listu v poloze t (0 náboj .. 1 špička): tětiva se zužuje, profil se zkrucuje; grow zvětší průřez (pruh)."""
    twist_max = math.radians(9)
    shape = BLADE_SHAPE[-1]
    for i in range(len(BLADE_STATIONS) - 1):
        if BLADE_STATIONS[i] <= t <= BLADE_STATIONS[i + 1]:
            u = (t - BLADE_STATIONS[i]) / (BLADE_STATIONS[i + 1] - BLADE_STATIONS[i])
            shape = BLADE_SHAPE[i] + (BLADE_SHAPE[i + 1] - BLADE_SHAPE[i]) * u
            break
    r = 0.05 + (length - 0.05) * t
    chord = (chord_root + (chord_tip - chord_root) * t ** 0.9) * shape * grow
    thick = (0.013 if t < 0.15 else 0.008) * (1.0 - 0.35 * t) * (grow + 0.5 * (grow - 1.0) * 10)
    twist = twist_max * (1.0 - t) * (1 if up else -1)
    ring = []
    for k in range(8):
        a = 2 * math.pi * k / 8
        cx = chord / 2 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a))
        cz = thick / 2 * math.copysign(abs(math.sin(a)) ** 0.5, math.sin(a))
        ring.append(Vector((r, cx * math.cos(twist) - cz * math.sin(twist) + side_offset,
                            cx * math.sin(twist) + cz * math.cos(twist))))
    return ring


def add_blade(coll, name, hub, angle, side_offset, up=True, blade=None, prop=None):
    """List vrtule (materiál Prop_Blade, barvu a karbon nastavuje skript podle konfigurace v obchodě) a jeho dítě
    <list>_Tip s nalepeným pruhem u špičky (materiál Prop_Tip)."""
    length, chord_root, chord_tip = blade or SPECS["M"]["blade"]
    m = Mesh((0, 0, 0))
    m.loft([_blade_ring(t, length, chord_root, chord_tip, up, side_offset) for t in BLADE_STATIONS], "Prop_Blade",
           smooth=True)
    obj = m.build(coll, name)
    obj.location = hub
    obj.rotation_euler = (0, 0, angle)

    m = Mesh((0, 0, 0))
    for t0, t1 in BLADE_STRIPES:
        ts = [t0 + (t1 - t0) * i / 3 for i in range(4)]
        m.loft([_blade_ring(t, length, chord_root, chord_tip, up, side_offset, grow=1.04) for t in ts], "Prop_Tip",
               smooth=True)
    tip = m.build(coll, f"{name}_Tip")
    tip.parent = obj
    tip.matrix_parent_inverse = mathutils.Matrix.Identity(4)
    return obj


PARK_X = 2.1  # rozteč parkovacích míst na plošině


def platform_top_z():
    """Horní hrana plošiny vleku - ať drony sedí správně i po změně jeho rozměrů."""
    return parts.PLATFORM_Z + parts.PLATFORM_THICK / 2


def build(on_trailer=True):
    coll = clear_collection()
    # na vleku drony parkují se složenými rameny i vrtulemi, vizuálně odlišené barvou
    z = platform_top_z() + 0.015 if on_trailer else 0.0
    build_drone(coll, name="Drone_A", origin=(PARK_X, 0, z), accent="Drone_Accent_A", arms_folded=1.0)
    build_drone(coll, name="Drone_B", origin=(-PARK_X, 0, z), accent="Drone_Accent_B", arms_folded=1.0)
    bpy.context.view_layer.update()
    print(f"Drone built: {len(coll.objects)} objects in '{COLLECTION_NAME}'")


if __name__ == "__main__":
    build()
