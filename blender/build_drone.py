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
# nozzles: ramena s tryskou a jejich vzdálenost od osy napříč
# (None = pod motorem); boom: tryska na rameni postřiku vně motoru; esc: regulátor s žebry na rameni;
# prop: materiál listů a materiál špičky (None = bez barevné špičky)
SPECS = {
    "M": dict(arm_span=(1.425, 1.71), arm_z=0.56, body=(0.56, 0.50, 0.17), tank_top=(0.58, 0.48),
              tank_bottom=(0.44, 0.36), tank_h=0.30, blade=(0.68, 0.095, 0.045), motor_r=0.075,
              levels=("Top", "Bottom"), detail=1.0, mast_h=0.15, skid=(0.42, 0.46, 0.30),
              nozzles=(1, 2, 3, 4), nozzle_y=None, boom=False, esc=False, prop=("Drone_White", None),
              blade_fold={"Top": (10.0, "pair"), "Bottom": (10.0, "pair")}),
    "S": dict(arm_span=(1.315, 1.405), arm_z=0.55, body=(0.44, 0.40, 0.15), tank_top=(0.46, 0.38),
              tank_bottom=(0.35, 0.29), tank_h=0.24, blade=(0.635, 0.085, 0.04), motor_r=0.065,
              levels=("Top",), detail=0.85, mast_h=0.155, skid=(0.34, 0.38, 0.24),
              nozzles=(3, 4), nozzle_y=0.684, boom=False, esc=True, prop=("Carbon", "Drone_Accent_A"),
              blade_fold={"Top": (10.0, "pair")}),
    "L": dict(arm_span=(1.646, 1.65), arm_z=0.67, body=(0.66, 0.56, 0.20), tank_top=(0.74, 0.62),
              tank_bottom=(0.58, 0.48), tank_h=0.38, blade=(0.787, 0.12, 0.055), motor_r=0.10,
              levels=("Top", "Bottom"), detail=1.2, mast_h=0.09, skid=(0.56, 0.58, 0.40),
              nozzles=(3, 4), nozzle_y=0.917, boom=True, esc=True, prop=("Carbon", "Drone_Accent_A"),
              blade_fold={"Top": (10.0, "pair"), "Bottom": (10.0, "pair")}),
}

# skenovací dron "K": rozměry, ramena, vrtule a lyžiny stejné jako S (stejné uzly, rozložení i úchyty na plošině), ale bez nádrže, čerpadla
# a trysek, s kardanovým podvěsem s kamerou; trup tmavý a kryty ramen v barvě značky; baterie S (battery)
SPECS["K"] = dict(SPECS["S"], scan=True, nozzles=(), battery="S")

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
LED_MATERIAL = "SDT_NavLed"
# poziční světla pod rameny jako u DJI Agras: vpředu vlevo červená, vpředu vpravo zelená, vzadu bílá (číslo ramene = arm_positions)
LED_COLORS = {1: (1.0, 0.03, 0.02), 2: (0.03, 1.0, 0.08), 3: (1.0, 1.0, 1.0), 4: (1.0, 1.0, 1.0)}


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


def rounded_ring(cx, cy, z, hx, hy, radius, arc=3):
    """Obdélník se zaoblenými rohy (arc úseků na roh), proti směru hodin shora."""
    r = min(radius, hx, hy)
    pts = []
    for ccx, ccy, a0 in ((hx - r, hy - r, 0), (-hx + r, hy - r, 90), (-hx + r, -hy + r, 180), (hx - r, -hy + r, 270)):
        for j in range(arc + 1):
            a = math.radians(a0 + 90 * j / arc)
            pts.append(Vector((cx + ccx + r * math.cos(a), cy + ccy + r * math.sin(a), z)))
    return pts


def axis_rings(origin, axis, stations, segments=TUBE_SEGMENTS):
    """Prstence kolmé na osu: stations = [(vzdálenost od origin, poloměr)], stejná vzdálenost dvakrát dá plochý prstenec."""
    u, n1, n2 = _axis_frame(axis)
    origin = Vector(origin)
    return [[origin + u * d + n1 * (r * math.cos(2 * math.pi * k / segments)) + n2 * (r * math.sin(2 * math.pi * k / segments))
             for k in range(segments)] for d, r in stations]


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


def _material(name):
    if name in bpy.data.materials or name in parts.MATERIALS:
        return parts.get_material(name)
    return P.material(name)


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

    def sweep(self, points, radii, mat, segments=TUBE_SEGMENTS, smooth=True):
        """Trubka podél lomené čáry: radii[i] je poloměr v bodě i, průřezy jsou kolmé na průměr sousedních směrů."""
        pts = [Vector(p) for p in points]
        rings = []
        for i, (p, r) in enumerate(zip(pts, radii)):
            tangent = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
            rings.append(axis_rings(p, tangent, [(0.0, r)], segments)[0])
        self.loft(rings, mat, smooth=smooth)

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
            me.materials.append(_material(m))
        obj = bpy.data.objects.new(name, me)
        coll.objects.link(obj)
        return obj


def motor_bell(m, cx, cy, mz, sgn, mr, k, base, top=0.098):
    """Zvon motoru: válcová bílá skořepina s fazetou nahoře, tmavým žlábkem uprostřed a zapuštěným čelem s límcem."""
    z = lambda d: mz + sgn * d * k
    h = top - base
    m.lathe(cx, cy, [(mr * 0.86, z(base)), (mr, z(base + 0.18 * h)), (mr, z(top - 0.18 * h)), (mr * 0.86, z(top)),
                     (mr * 0.55, z(top)), (mr * 0.50, z(top - 0.07 * h))][::sgn], WHITE, segments=18)
    m.lathe(cx, cy, [(mr * 1.006, z(base + 0.46 * h)), (mr * 1.006, z(base + 0.58 * h))][::sgn], GREY_DARK, segments=18,
            cap_start=False, cap_end=False)


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


def blade_fold_angles(spec, rotor, ax, ay, arm=None):
    """Svět. úhly dvou složených listů a jejich natočení do rozložené polohy (přímka napříč ramene), radiány.
    spec["blade_fold"][rotor] = (stupně, režim): "side"/"front" - oba listy na jedné přímce přes střed rotoru, odkloněné od ramene
    o tolik stupňů ("front" jen u předních ramen); "pair" - oba listy míří podél ramene dovnitř k trupu a svírají mezi sebou tolik stupňů;
    "pairOut" - totéž ven od trupu. Volitelný třetí prvek stočí dvojici o tolik
    stupňů (zrcadlově podle kvadrantu ramene).
    Hodnoty jsou voleny tak, aby se složené listy neprotínaly s trupem, rameny ani bednou Mini (tmp/blade_fold_test.py, tmp/mini_blade_scan.py)."""
    deg, mode, *skew = spec["blade_fold"].get(rotor, (0.0, "side"))
    if arm is None:
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
    scan = s.get("scan", False)
    shell = GREY_DARK if scan else GREY
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

    # trup: šedá skříň se zaoblenými hranami a plochým hřbetem (na něm leží šachta baterie), hladké stínování
    m = Mesh(off)
    corner = 0.36 * min(hx, hy)
    edge_b, edge_t = 0.34 * body_height, 0.30 * body_height
    stations = []
    for t in (0.0, 0.3, 0.6, 0.85, 1.0):
        f = 1 - math.sin(t * math.pi / 2)
        stations.append((-body_height / 2 + t * edge_b, 1 - 0.22 * f, 1 - 0.26 * f))
    for t in (1.0, 0.85, 0.6, 0.3, 0.0):
        f = 1 - math.sin(t * math.pi / 2)
        stations.append((body_height / 2 - t * edge_t, 1 - 0.18 * f, 1 - 0.20 * f))
    m.loft([rounded_ring(0, 0, body_z + dz, hx * sx, hy * sy, corner * min(sx, sy)) for dz, sx, sy in stations],
           shell, smooth=True)
    if not scan:
        m.paint_beyond((-0.03 * k, 0, 0), (-1, 0, 0), WHITE)   # zadní část hřbetu je horní stěna nádrže
    emit(m, "Body")

    # lem v pase trupu (tmavá spára nad nádrží) a dvě boční mřížky chlazení; pod hranou trupu, bez změny rozměrů
    m = Mesh(off)
    dz_w, sx_w, sy_w = stations[1]
    waist = [rounded_ring(0, 0, body_z + dz_w + dzz, hx * sx_w * 1.004, hy * sy_w * 1.004, corner * min(sx_w, sy_w)) for dzz in
             (-0.008 * k, -0.004 * k, 0.004 * k, 0.008 * k)]
    m.loft(waist, GREY_DARK, smooth=True, cap_start=False, cap_end=False)
    for sy_ in (1, -1):
        for gx in (-0.05 * k, 0.0, 0.05 * k):
            m.solid((gx, sy_ * hy, body_z + 0.003 * k), (0.008 * k, 0.003 * k, 0.024 * k), BLACK,
                    frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))))
    emit(m, "Trim")

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
    for sy_ in (1, -1):
        m.tube((mast_x - 0.012 * k, sy_ * 0.092 * k, mast_base - 0.001), (mast_x - 0.012 * k, sy_ * 0.092 * k, mast_base + 0.005 * k),
               [0.009 * k] * 2, "Glass_Dark", segments=8)
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
            m.tube((face_x - 0.006 * k, cy_, cz), (face_x + 0.004 * k, cy_, cz), [0.024 * k] * 2, "Glass_Dark", segments=14)
            m.tube((face_x + 0.002 * k, cy_, cz), (face_x + 0.009 * k, cy_, cz), [0.017 * k, 0.017 * k], WHITE, segments=14)
        m.solid((face_x - 0.001 * k, side * 0.36 * hy, body_z - 0.01 * k), (0.004 * k, 0.034 * k, 0.050 * k), GREY_DARK,
                frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=0.016 * k, ch=0.002 * k)
    emit(m, "Nose")

    # zadní radar (plochý modul na zádi)
    m = Mesh(off)
    m.solid((-hx - 0.012 * k, 0, body_z - 0.045 * k), (0.03 * k, 0.11 * k, 0.035 * k), GREY_DARK,
            frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=0.012 * k, ch=0.006 * k)
    emit(m, "RadarRear")

    if not scan:
        # nádrž: oblá bílá skořepina pod trupem (jako DJI T50/T100), zúžená ke dnu, s okénkem stavoznaku
        m = Mesh(off)

        def tank_station(t, sc=1.0):
            u = 0.0 if t <= 0.30 else (t - 0.30) / 0.70
            ax_ = tank_top[0] + (tank_bottom[0] - tank_top[0]) * u
            by_ = tank_top[1] + (tank_bottom[1] - tank_top[1]) * u
            return tank_top_z - tank_height * t, ax_ / 2 * sc, by_ / 2 * sc

        stations = [tank_station(t, sc) for t, sc in
                    ((0.0, 0.95), (0.03, 0.99), (0.12, 1.0), (0.30, 1.0), (0.80, 1.0), (0.90, 0.985), (0.96, 0.94), (1.0, 0.84))]
        m.loft([rounded_ring(0, 0, z, ax_, by_, 0.34 * min(ax_, by_)) for z, ax_, by_ in stations], WHITE, smooth=True)
        m.solid((tank_top[0] / 2 + 0.001, -0.10 * k, tank_top_z - 0.16 * tank_height), (0.11 * tank_height, 0.02 * k, 0.004),
                "Glass_Dark", frame=(Vector((0, 0, 1)), Vector((0, 1, 0)), Vector((-1, 0, 0))))
        tank = emit(m, "Tank")
        brand_decals(coll, name, tank, off, tank_station(0.30), tank_station(0.80), tank_top[0], k)

        # peristaltické čerpadlo pod dnem nádrže jako u DJI Agras: dvě hlavy na společné ose napříč s knoflíkem mezi nimi, držák
        # na desce přišroubované ke dnu, dvě průsvitné hadice ze dna nádrže do kolen na hlavách a výstupní hrdla na koncích
        m = Mesh(off)
        hl = min(0.14 * k, 0.30 * tank_bottom[1])
        pr = 0.040 * k
        pz = tank_bottom_z - 0.085 * k
        m.solid((0, 0, tank_bottom_z - 0.006 * k), (0.006 * k, 0.07 * k, hl), BLACK, cut=0.012 * k)
        for sy in (-1, 1):
            m.solid((0.0, sy * 0.72 * hl, (tank_bottom_z + pz) / 2 - 0.004 * k), (0.030 * k, 0.034 * k, 0.012 * k), BLACK,
                    cut=0.008 * k)
            m.tube((0, sy * 0.05 * k, pz), (0, sy * (hl - 0.014 * k), pz), [pr * 0.9, pr, pr, pr * 0.92], GREY_DARK, segments=10)
            m.tube((0, sy * (hl - 0.014 * k), pz), (0, sy * hl, pz), [pr * 0.78] * 2, BLACK, segments=10)
            m.tube((0, sy * 0.045 * k, pz), (0, sy * 0.056 * k, pz), [pr * 1.12] * 2, accent, segments=10)
            m.tube((0, sy * hl, pz), (0, sy * (hl + 0.02 * k), pz), [0.016 * k] * 2, BLACK, segments=10)
            hy = sy * 0.62 * hl
            m.tube((-0.012 * k, hy, tank_bottom_z), (-0.012 * k, hy, pz + pr * 0.9), [0.0085 * k] * 2, GREY, segments=8)
            m.lathe(-0.012 * k, hy, [(0.012 * k, pz + pr * 0.9 + 0.020 * k), (0.012 * k, pz + pr * 0.9)], BLACK, segments=10)
        m.tube((0, -0.045 * k, pz), (0, 0.045 * k, pz), [0.030 * k] * 2, BLACK, segments=8)
        m.tube((0, -0.020 * k, pz), (0, 0.020 * k, pz), [0.036 * k] * 2, GREY_DARK, segments=10)
        emit(m, "Pump")

    else:
        # skenovací dron: místo nádrže a čerpadla kardanový podvěs s kamerou RGB a čtyřmi multispektrálními čočkami; hy zůstává jako po stavbě
        # čerpadla u S, protože z něj se počítá kořen ramen (stejná geometrie, stejné úhly skládání)
        hy = 0.62 * min(0.14 * k, 0.30 * tank_bottom[1])
        axes = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        m = Mesh(off)
        gx = 0.07 * k
        m.solid((gx, 0, hull_bottom - 0.008 * k), (0.085 * k, 0.07 * k, 0.010 * k), GREY_DARK, frame=axes, cut=0.01 * k, ch=0.006 * k)
        head_z = hull_bottom - 0.125 * k
        for sy_ in (1, -1):
            m.tube((gx, sy_ * 0.058 * k, hull_bottom - 0.014 * k), (gx, sy_ * 0.058 * k, head_z + 0.01 * k), [0.0085 * k] * 2, BLACK, segments=10)
            m.tube((gx, sy_ * 0.050 * k, head_z), (gx, sy_ * 0.070 * k, head_z), [0.016 * k] * 2, GREY, segments=12)
        tilt_a = math.radians(35)
        fa = Vector((math.cos(tilt_a), 0, -math.sin(tilt_a)))
        fb = Vector((0, 1, 0))
        fc = fa.cross(fb)
        head = Vector((gx, 0, head_z))
        m.solid(head, (0.062 * k, 0.050 * k, 0.045 * k), BLACK, frame=(fa, fb, fc), cut=0.014 * k, ch=0.010 * k, smooth=True)
        face = head + fa * (0.058 * k)
        for off_b, off_c, rr in ((0.0, 0.0, 0.026), (0.040, 0.022, 0.010), (-0.040, 0.022, 0.010), (0.040, -0.022, 0.010),
                                 (-0.040, -0.022, 0.010)):
            c0 = face + fb * (off_b * k) + fc * (off_c * k)
            m.tube(c0, c0 + fa * (0.006 * k), [(rr + 0.005) * k] * 2, GREY_DARK, segments=14)
            m.tube(c0 + fa * (0.004 * k), c0 + fa * (0.011 * k), [rr * k] * 2, "Glass_Dark", segments=14)
        emit(m, "Sensor")

    # ramena, gondoly, vrtule - každé rameno pod vlastním kloubem, aby šlo složit
    nozzle_no = 0
    tip_r, root_r = 0.024 * k, 0.029 * k
    lane_gap = s["blade"][1] / 2 + 0.052 * k + 0.035
    for idx, (ax, ay) in enumerate(arm_positions(s), start=1):
        # kloub sedí na boku trupu; složená ramena leží podél boků, přední dozadu a zadní dopředu (jako DJI Agras, složený T50 1115 x 750 mm),
        # zadní ve vnějším pruhu o šířku listů dál, aby se oba páry nekřížily (zadní kloub drží výložník z boku trupu)
        outer = ax < 0
        root = Vector((math.copysign(hx - 0.06 * k, ax), math.copysign(body_width / 2 + 0.005 + (lane_gap if outer else 0.0), ay), body_z))
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
        m.lathe(root.x, root.y, [(0.046 * k, body_z - 0.056 * k), (0.052 * k, body_z - 0.046 * k), (0.052 * k, body_z + 0.046 * k),
                                 (0.046 * k, body_z + 0.056 * k)], BLACK, segments=12)
        m.lathe(root.x, root.y, [(0.034 * k, body_z + 0.056 * k), (0.026 * k, body_z + 0.064 * k)], GREY_DARK, segments=10)
        m.solid(at(0.035 * k), (0.030 * k, 0.040 * k, 0.040 * k), BLACK, frame=frame, cut=0.012 * k, ch=0.008 * k)
        m.loft(tube_rings(at(0.10 * k), at(0.245 * k), [1.30 * root_r, 1.55 * root_r, 1.60 * root_r, 1.55 * root_r,
                                                       1.30 * root_r], 12), BLACK, smooth=True)
        for dist in (0.135, 0.21):
            m.tube(at(dist * k), at((dist + 0.012) * k), [1.68 * root_r] * 2, GREY_DARK, segments=12)
        m.solid(at(0.172 * k) + frame[2] * (1.8 * root_r), (0.032 * k, 0.020 * k, 0.010 * k), GREY_DARK, frame=frame,
                cut=0.005 * k, ch=0.004 * k)
        # žlutý výstražný pásek na trubce
        m.tube(at(0.30 * k), at(0.34 * k), [root_r * 1.08] * 2, YELLOW, segments=12)
        if s["esc"]:  # plynulý kryt regulátoru na rameni s jemnými žebry (tmavé drážky)
            c0, c1 = length - 0.40 * k, length - 0.215 * k
            radii = (1.15, 1.6, 2.1, 2.1, 1.9, 1.9, 2.1, 2.1, 1.9, 1.9, 2.1, 1.6, 1.15)
            up = frame[2]
            rings, bands = [], []
            for q, rr in enumerate(radii):
                cc = at(c0 + (c1 - c0) * q / (len(radii) - 1))
                r_ = tip_r * rr
                rings.append([cc + up * (0.12 * r_) + frame[1] * (r_ * math.cos(a)) + up * (r_ * math.sin(a) * (0.95 if math.sin(a) > 0 else 0.72))
                              for a in (2 * math.pi * j / 10 for j in range(10))])
                if q:
                    bands.append(GREY_DARK if rr == radii[q - 1] == 1.9 else (accent if scan else GREY))
            m.loft(rings, accent if scan else GREY, smooth=True, band_mats=bands)
        # poziční světlo: pouzdro po straně ramene u motoru s kulatou čočkou zapuštěnou do předního okraje, dívá se šikmo
        # dolů a ven od trupu (pod motorem je náboj spodní vrtule nebo tryska)
        out = frame[1] if frame[1].y * ay > 0 else -frame[1]
        led_axis = (out * 0.82 + Vector((0, 0, -0.57))).normalized()
        led_base = at(length - 0.17 * k) + out * (0.01 * k)
        pr, depth, recess = 0.034 * k, 0.074 * k, 0.010 * k
        m.loft(axis_rings(led_base, led_axis, [(0.0, pr * 0.62), (0.03 * k, pr), (depth, pr), (depth, pr * 0.70),
                                               (depth - recess, pr * 0.70)], segments=14), BLACK, smooth=True,
               cap_start=False, band_mats=(BLACK, BLACK, GREY_DARK, BLACK))
        # koncová objímka pod gondolou
        m.tube(at(length - 0.09 * k), at(length - 0.005 * k), [tip_r * 1.35, tip_r * 1.45, tip_r * 1.45, tip_r * 1.3],
               BLACK, segments=12)
        emit(m, f"Arm_{idx}", arm=True)
        if outer:  # výložník od boku trupu ke kloubu zadního ramene zůstává na trupu, neskládá se s ramenem
            y_in = math.copysign(body_width / 2 - 0.03 * k, ay)
            m = Mesh(off)
            m.solid((root.x, (y_in + root.y) / 2, body_z), (0.050 * k, abs(root.y - y_in) / 2, 0.046 * k), BLACK,
                    frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=0.014 * k, ch=0.008 * k)
            emit(m, f"Outrigger_{idx}")

        m = Mesh(off)
        m.loft(axis_rings(led_base, led_axis, [(depth - 0.0085 * k, pr * 0.68), (depth - 0.0065 * k, pr * 0.66),
                                               (depth - 0.0050 * k, pr * 0.50)], segments=14), LED_MATERIAL, smooth=True)
        led = emit(m, f"Led_{idx}", arm=True)
        attr = led.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
        for item in attr.data:
            item.color_srgb = (*LED_COLORS[idx], 1.0)
        led.data.color_attributes.render_color_index = 0

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
                motor_bell(m, cx, cy, mz, sgn, mr, k, 0.052)
        else:
            m.lathe(cx, cy, [(0.050 * k, mz - 0.05 * k), (0.056 * k, mz - 0.03 * k), (0.056 * k, mz + 0.02 * k)],
                    BLACK, segments=18)
            motor_bell(m, cx, cy, mz, 1, mr, k, 0.018, top=0.088)
        emit(m, f"Motor_{idx}", arm=True)

        hubs = {"Top": mz + (0.107 if coax else 0.098) * k}
        if coax:
            hubs["Bottom"] = mz - 0.107 * k
        hubs = {lv: hubs[lv] for lv in s["levels"]}
        for tag, hz in hubs.items():
            up = tag == "Top"
            m = Mesh(off)
            sg = 1 if up else -1
            m.lathe(cx, cy, [(r_ * k, hz + sg * dz * k) for r_, dz in
                             ((0.044, -0.012), (0.051, -0.008), (0.051, 0.010), (0.030, 0.0125), (0.026, 0.018),
                              (0.011, 0.024))][::sg], GREY_DARK, segments=12)
            emit(m, f"Hub{tag}_{idx}", arm=True)

        arm_angle = math.atan2(ay, ax)
        for rotor, hz in hubs.items():
            for b in range(2):
                if folded:
                    # složené listy leží na jedné přímce přes střed rotoru (jeden dopředu, druhý dozadu), bez bočního posunu;
                    # směr přímky vůči rameni určuje BLADE_FOLD
                    angles, deltas = blade_fold_angles(s, rotor, ax, ay, math.atan2(d.y, d.x))
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
            hose_a, hose_b = Vector((root.x, root.y, root.z - hose_drop)), Vector((ax, ay, tip.z - hose_drop))
            m.tube(hose_a, hose_b, [hose_r, hose_r], "SDT_HoseBlack", segments=8)
            hdir = (hose_b - hose_a).normalized()
            for hp in (hose_a + hdir * 0.025 * k, hose_b - hdir * 0.05 * k):
                m.tube(hp, hp + hdir * 0.022 * k, [hose_r * 1.6] * 2, GREY_DARK, segments=6, smooth=False)
            clip_end = length - (0.43 if s["esc"] else 0.30) * k
            for q in range(3):
                cp = hose_a + hdir * (0.42 * k + (clip_end - 0.42 * k) * q / 2)
                m.solid(cp + Vector((0, 0, 0.5 * hose_drop)), (0.011 * k, 0.013 * k, 0.5 * hose_drop + 0.016 * k), BLACK,
                        frame=frame, cut=0.006 * k)
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
            # odstředivá tryska: motorek, plochý kotouč s okrajem v barvě dronu a křídlová matice (DJI Agras T50)
            m.lathe(ax, ny, [(0.034 * k, nozzle_z), (0.034 * k, nozzle_z - 0.010 * k), (0.058 * k, nozzle_z - 0.014 * k),
                             (0.060 * k, nozzle_z - 0.026 * k), (0.054 * k, nozzle_z - 0.030 * k),
                             (0.018 * k, nozzle_z - 0.030 * k)], accent, segments=16)
            m.lathe(ax, ny, [(0.016 * k, nozzle_z - 0.030 * k), (0.008 * k, nozzle_z - 0.042 * k)], "SDT_Steel", segments=8)
            m.solid((ax, ny, nozzle_z - 0.040 * k), (0.016 * k, 0.003 * k, 0.003 * k), "SDT_Steel",
                    frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))))
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
        target_az = math.pi if ax > 0 else 0.0
        pivot.rotation_euler = (0, 0, ((target_az - base_az + math.pi) % (2 * math.pi) - math.pi) * arms_folded)

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
        # lyžina s nahoru zahnutými konci (nenabíhá do trávy); rovný úsek mezi nohami zůstává ve výšce skid_z (sedí v něm úchyty)
        flat = skid_half - 0.12 * k
        profile = ((-skid_half + 0.018 * k, 0.052, 0.020), (-skid_half + 0.05 * k, 0.018, 0.027), (-flat, 0.0, 0.030),
                   (flat, 0.0, 0.030), (skid_half - 0.05 * k, 0.018, 0.027), (skid_half - 0.018 * k, 0.052, 0.020))
        m.sweep([(x_, y_out, skid_z + rise * k) for x_, rise, _ in profile], [r_ * k for _, _, r_ in profile], BLACK, segments=10)
        emit(m, f"Skid_{side}")
        for tag, lx in (("F", leg_x), ("R", -leg_x)):
            # gumová patka pod nohou a černá botka na spojení nohy s lyžinou
            m = Mesh(off)
            m.lathe(lx, y_out, [(0.034 * k, skid_z - 0.03), (0.04 * k, skid_z - 0.01), (0.032 * k, skid_z + 0.01)],
                    "SDT_Rubber", segments=10)
            m.solid((lx, y_out, skid_z + 0.034 * k), (0.032 * k, 0.026 * k, 0.026 * k), GREY_DARK, cut=0.008 * k,
                    frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))))
            emit(m, f"SkidPad_{side}{tag}")
    m = Mesh(off)
    m.tube((0, skid_y, skid_z), (0, -skid_y, skid_z), [0.022 * k, 0.026 * k, 0.022 * k], BLACK, segments=10)
    for sy in (1, -1):
        m.solid((0, sy * (skid_y - 0.03 * k), skid_z), (0.030 * k, 0.020 * k, 0.026 * k), GREY_DARK, cut=0.008 * k,
                frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))))
    emit(m, "SkidCross")


BLADE_STATIONS = (0.0, 0.08, 0.22, 0.42, 0.62, 0.80, 0.95, 1.0)
BLADE_SHAPE = (0.85, 1.0, 1.0, 0.92, 0.80, 0.66, 0.42, 0.14)
# pruh u špičky listu (rozsah t podél listu): nalepený barevný proužek, samostatný objekt <list>_Tip
BLADE_STRIPES = ((0.89, 0.97),)
# profil listu: zaoblená náběžná hrana, ostrá odtoková, mírně vypouklá horní strana (u souřadnice podél tětivy od náběžné hrany)
BLADE_PROFILE_U = (0.0, 0.06, 0.30, 0.70, 1.0)


def _naca(u):
    return 0.2969 * math.sqrt(u) - 0.1260 * u - 0.3516 * u ** 2 + 0.2843 * u ** 3 - 0.1015 * u ** 4


_NACA_MAX = max(_naca(i / 100) for i in range(101))


def _blade_ring(t, length, chord_root, chord_tip, up, side_offset, grow=1.0):
    """Průřez listu v poloze t (0 náboj .. 1 špička): tětiva se zužuje, profil se zkrucuje a špička je mírně zakřivená
    dozadu; grow zvětší průřez (pruh). Náběžná hrana je na straně +y u horního rotoru a -y u spodního."""
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
    le = 1 if up else -1
    sweep = 0.0
    uu = BLADE_PROFILE_U
    pts = []
    for sgn, us in ((1, uu), (-1, uu[-2:0:-1])):
        for u in us:
            half = max(0.0004, thick / 2 * _naca(u) / _NACA_MAX)
            pts.append((chord * (0.5 - u) * le - le * sweep, sgn * half + thick * 0.6 * 4 * u * (1 - u) * 0.5))
    return [Vector((r, cx * math.cos(twist) - cz * math.sin(twist) + side_offset,
                    cx * math.sin(twist) + cz * math.cos(twist))) for cx, cz in pts]


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


# ------------------------------------------------------------------------------------------------ díly dronu pro knihovnu
# Dron se skládá z pěti dílů v jedné souřadné soustavě (počátek na zemi pod středem trupu, rozložený let), takže složené leží
# přesně na sobě. Díly vznikají z build_drone (jediný zdroj tvaru), ostatní objekty se po stavbě smažou. Vlek dron dál staví
# přímo přes build_drone; knihovna slouží katalogu a samostatnému exportu dílů.
PART_ARM = 3          # rameno s tryskou u všech velikostí (S a L mají trysky jen na ramenech 3 a 4)


def _drone_part(size, keep):
    """Postaví dron velikosti size (S, M, L) v rozloženém letovém stavu v prázdné scéně dílu a nechá jen objekty, pro které
    keep(jméno) platí; zachovaný objekt, jehož rodič se maže, zůstane na svém místě."""
    coll = P._coll
    for name in P.MATERIALS:       # build_trailer.get_material zná jen svoje materiály; v samostatné scéně dílu ještě žádné nejsou
        P.material(name)
    build_drone(coll, name="Drone", origin=(0, 0, 0), folded=False, arms_folded=0.0, spec=SPECS[size])
    bpy.context.view_layer.update()
    kept = [o for o in coll.objects if o is not P._root and keep(o.name)]
    for o in kept:
        if o.parent is not None and not keep(o.parent.name):
            w = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = w
    for o in list(coll.objects):
        if o is P._root or keep(o.name):
            continue
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)


def part_fuselage(size):
    """Trup: šedá fasetovaná skříň s radarem, přídí, stožárem GPS a lemem v pase."""
    _drone_part(size, lambda n: n in ("Drone_Body", "Drone_Trim", "Drone_GpsMast", "Drone_Nose", "Drone_RadarRear"))


def part_tank(size):
    """Nádrž pod trupem s čerpadlem."""
    _drone_part(size, lambda n: n in ("Drone_Tank", "Drone_Pump"))


def part_arm(size):
    """Rameno (třetí) s kloubem, motorem, hlavou rotoru, hadicí, tryskou a pozičním světlem; list vrtule je zvláštní díl."""
    tag = f"_{PART_ARM}"
    _drone_part(size, lambda n: (n.endswith(tag) and n.startswith(("Drone_Arm", "Drone_Led", "Drone_Motor", "Drone_Hub", "Drone_Nozzle")))
                or n == f"Drone_ArmPivot_{PART_ARM}" or n == f"Drone_SprayNozzle_{3 if size == 'M' else 1}")


def part_rotor(size):
    """Vrtule jednoho motoru: dva listy (u souosých rotorů čtyři) s barevnou špičkou, rozložené."""
    _drone_part(size, lambda n: n.startswith(f"Drone_Blade_{PART_ARM}"))


def part_gear(size):
    """Podvozek: A-nohy, lyžiny, gumové patky a příčka."""
    _drone_part(size, lambda n: n.startswith(("Drone_Legs_", "Drone_Skid")))


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
