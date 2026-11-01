"""Nádrže, čerpadlo, potrubí a zadní bedna na spodní desce malého vleku (build_trailer_middle.build_equipment).

Každá funkce build_* složí své díly do několika meshů s materiály jako sloty (třída Mesh, souřadnice ve světě,
počátek objektu v počátku scény jako P.merge). Polohy koncových napojení počítají čisté funkce *_ports, takže
rozvod (build_plumbing) sedí na nádrže i čerpadlo bez sdíleného stavu.

Osa vleku: vpředu -Y, Z nahoru, počátek na zemi, střed šířky.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import sdt_parts as P
from sdt_contract import MAIN_DRAIN

TAU = 2.0 * math.pi
PUMP_XY = (-0.55, -0.55)            # střed čerpadla na palubě (osa motoru je 0,42 nad palubou)
INDUCTION_XY = (-0.55, -1.25)       # střed indukční nádrže
PUMP_AXIS_H = 0.42                  # výška osy čerpadla nad palubou
PUMP_PORT_U = 0.31                  # čelo příruby sání před středem čerpadla (po X)
TEE_U = PUMP_PORT_U + 0.14          # T-kus před středem čerpadla (po X)
TEE_DY = -0.25                      # T-kus dopředu od osy čerpadla (po Y)
TEE_RUN = 0.085                     # půlka délky T-kusu po X
HEAD = 0.20                         # hloubka eliptického dna hlavní nádrže
INDUCTION_R = 0.22                  # poloměr indukční nádrže (~50 l)
INDUCTION_STAND_H = 0.28            # výška dna kužele nad palubou
INDUCTION_CONE_H = 0.19
INDUCTION_BODY_H = 0.33
INDUCTION_LEG_R = 0.19              # půlrozteč nohou indukční nádrže
INDUCTION_NECK_R = 0.105            # plnicí hrdlo: vnější poloměr krku a zvednutého lemu
INDUCTION_NECK_LIP = 0.117
INDUCTION_R0 = 0.052                # poloměr dna kužele
INDUCTION_WALL = 0.004
MAIN_DRAIN_HOSE = 0.180             # hadice z MAIN_DRAIN začíná tolik před výpustí (v hadicovém nátrubku kohoutu)
MAIN_TANK_REF_R = 0.40              # poloměr, ke kterému jsou vztažené hrdlo, hladinoměr a další drobnosti hlavní nádrže


def V(x, y, z):
    return Vector((x, y, z))


def frame(origin, axis, ref=None):
    """Matice s osou Z podél axis, osou X co nejblíž ref."""
    z = Vector(axis).normalized()
    if ref is None:
        ref = V(1, 0, 0) if abs(z.x) < 0.9 else V(0, 1, 0)
    ref = Vector(ref)
    x = ref - z * ref.dot(z)
    if x.length < 1e-6:
        x = V(0, 1, 0) - z * z.y
    x.normalize()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def attach(obj, parent, pivot):
    """Počátek objektu do pivotu a pod parent (empty s posunem bez natočení v pivotu); vrcholy zůstanou ve světě na místě."""
    pivot = Vector(pivot)
    obj.data.transform(Matrix.Translation(-pivot))
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_world = Matrix.Translation(pivot)


class Mesh:
    """Sběrač geometrie ve světových souřadnicích: jeden bmesh, materiály jako sloty, jeden objekt na konci."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []

    def _absorb(self, t, m, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        idx = self.mats.index(mat)
        vm = {v: self.bm.verts.new(m @ v.co) for v in t.verts}
        for f in t.faces:
            nf = self.bm.faces.new([vm[v] for v in f.verts])
            nf.smooth = f.smooth
            nf.material_index = idx
        t.free()

    # ---- základní tělesa

    def obox(self, size, m, mat, bevel=0.0, segments=1):
        t = bmesh.new()
        bmesh.ops.create_cube(t, size=1.0, matrix=Matrix.Diagonal((*size, 1.0)))
        b = min(bevel, min(size) * 0.45)
        if b > 1e-5:
            bmesh.ops.bevel(t, geom=list(t.edges), offset=b, offset_type="OFFSET", segments=segments, profile=0.5,
                            affect="EDGES")
        self._absorb(t, m, mat)

    def box(self, x0, x1, y0, y1, z0, z1, mat, bevel=0.0):
        self.obox((abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)),
                  Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), mat, bevel)

    def lathe(self, profile, origin, axis, mat, seg=32, ref=None, hard=(), loop=False, phase=0.0):
        """Těleso otáčením profilu [(poloměr, poloha po ose)] kolem osy. Profil se prochází tak, aby při pohybu po
        ose (dolů-nahoru) vně šlo vnější lícem; kruhové čepičky = přechod na poloměr 0. hard = indexy bodů, kde se
        stínování láme (dvojí kruh)."""
        t = bmesh.new()
        n = len(profile)

        def ring(r, a):
            if r < 1e-9:
                return t.verts.new((0.0, 0.0, a))
            return [t.verts.new((r * math.cos(phase + TAU * i / seg), r * math.sin(phase + TAU * i / seg), a))
                    for i in range(seg)]

        def link(r0, r1):
            for i in range(seg):
                j = (i + 1) % seg
                if isinstance(r0, list) and isinstance(r1, list):
                    vs = (r0[i], r0[j], r1[j], r1[i])
                elif isinstance(r0, list):
                    vs = (r0[i], r0[j], r1)
                else:
                    vs = (r0, r1[j], r1[i])
                t.faces.new(vs).smooth = True

        if loop:
            rings = [ring(r, a) for r, a in profile]
            for k in range(n):
                link(rings[k], rings[(k + 1) % n])
        else:
            cuts = [0] + sorted(h for h in hard if 0 < h < n - 1) + [n - 1]
            for s, e in zip(cuts, cuts[1:]):
                rings = [ring(r, a) for r, a in profile[s:e + 1]]
                for r0, r1 in zip(rings, rings[1:]):
                    link(r0, r1)
        self._absorb(t, frame(origin, axis, ref), mat)

    def loft(self, origin, rings, mat, corner_pts=5, pocket=None):
        """Těleso prolože zaoblenými obdélníky: rings = [(z, polovina X, polovina Y, poloměr rohu)] od spodu nahoru, počátek
        původu uprostřed základny. Boky hladce stínované, spodní a horní plocha ploché. pocket = (cx, polovina X, polovina Y,
        poloměr rohu, hloubka): prohlubeň v horní ploše se středem posunutým o cx."""
        t = bmesh.new()

        def outline(hx, hy, r):
            pts = []
            for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
                for i in range(corner_pts):
                    a = math.pi / 2 * (k + i / (corner_pts - 1))
                    pts.append(((hx - r) * sx + r * math.cos(a), (hy - r) * sy + r * math.sin(a)))
            return pts

        def ring(z, hx, hy, r):
            return [t.verts.new((x, y, z)) for x, y in outline(hx, hy, r)]

        built = [ring(*spec) for spec in rings]
        n = len(built[0])
        for lo, hi in zip(built, built[1:]):
            for i in range(n):
                j = (i + 1) % n
                t.faces.new((lo[i], lo[j], hi[j], hi[i])).smooth = True
        z0, hx0, hy0, r0 = rings[0]
        z1, hx1, hy1, r1 = rings[-1]
        t.faces.new(ring(z0, hx0, hy0, r0)[::-1]).smooth = False
        if pocket is None:
            t.faces.new(ring(z1, hx1, hy1, r1)).smooth = False
        else:
            cx, phx, phy, pr, depth = pocket
            top_outer = ring(z1, hx1, hy1, r1)

            def pocket_ring(z, inset):
                return [t.verts.new((x + cx, y, z)) for x, y in outline(phx - inset, phy - inset, max(pr - inset, 0.004))]

            rim = pocket_ring(z1, 0.0)
            for i in range(n):
                j = (i + 1) % n
                t.faces.new((top_outer[i], top_outer[j], rim[j], rim[i])).smooth = False
            levels = [rim] + [pocket_ring(z1 - dz, inset) for dz, inset in
                              ((0.0025, 0.0012), (depth * 0.7, 0.0035), (depth, 0.0065))]
            for lo, hi in zip(levels, levels[1:]):
                for i in range(n):
                    j = (i + 1) % n
                    t.faces.new((lo[i], lo[j], hi[j], hi[i])).smooth = True
            t.faces.new(levels[-1]).smooth = False
        self._absorb(t, Matrix.Translation(Vector(origin)), mat)

    def tube(self, pts, rx, ry, mat, seg=12, scales=None):
        """Oblá trubice s eliptickým průřezem po křivce pts (body v rovině XZ): rx = poloměr v rovině křivky, ry = poloměr po Y,
        scales = násobek průřezu v každém bodě (náběhy na koncích)."""
        t = bmesh.new()
        pts = [Vector(p) for p in pts]
        b = Vector((0, 1, 0))
        rings = []
        for k, p in enumerate(pts):
            a, c = pts[max(k - 1, 0)], pts[min(k + 1, len(pts) - 1)]
            tan = (c - a).normalized()
            nrm = b.cross(tan).normalized()
            s = 1.0 if scales is None else scales[k]
            rings.append([t.verts.new(p + nrm * (math.cos(TAU * i / seg) * rx * s) + b * (math.sin(TAU * i / seg) * ry * s))
                          for i in range(seg)])
        for lo, hi in zip(rings, rings[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                t.faces.new((lo[i], lo[j], hi[j], hi[i])).smooth = True
        t.faces.new(rings[0][::-1]).smooth = False
        t.faces.new(rings[-1]).smooth = False
        self._absorb(t, Matrix.Identity(4), mat)

    def cyl(self, p0, p1, r, mat, r1=None, seg=12, caps=True, ref=None, square=False):
        """Válec/kužel p0 -> p1; square = čtyřhranný profil o polovině strany r (natočený podle ref)."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        r1 = r if r1 is None else r1
        length = d.length
        phase = 0.0
        if square:
            seg, phase, r, r1 = 4, math.pi / 4, r * math.sqrt(2), r1 * math.sqrt(2)
        if caps:
            prof, hard = [(0, 0), (r, 0), (r1, length), (0, length)], (1, 2)
        else:
            prof, hard = [(r, 0), (r1, length)], ()
        self.lathe(prof, p0, d, mat, seg=seg, hard=hard, ref=ref, phase=phase)

    def sphere(self, c, r, mat, seg=16, rings=8, axis=(0, 0, 1)):
        prof = [(r * math.sin(math.pi * k / rings), -r * math.cos(math.pi * k / rings)) for k in range(rings + 1)]
        self.lathe(prof, c, axis, mat, seg=seg)

    def torus(self, c, axis, big, small, mat, seg=24, rseg=6):
        prof = [(big + small * math.cos(TAU * k / rseg), small * math.sin(TAU * k / rseg)) for k in range(rseg)]
        self.lathe(prof, c, axis, mat, seg=seg, loop=True)

    def hex(self, c, axis, r, h, mat):
        c = Vector(c)
        self.cyl(c, c + Vector(axis).normalized() * h, r, mat, seg=6)

    def plate(self, pts, origin, u, v, thick, mat):
        """Deska s obrysem pts (2D v rovině u, v od origin) vytažená o thick po u × v."""
        u, v = Vector(u).normalized(), Vector(v).normalized()
        n = u.cross(v)
        t = bmesh.new()
        a = [t.verts.new(Vector(origin) + u * p[0] + v * p[1]) for p in pts]
        b = [t.verts.new(Vector(origin) + u * p[0] + v * p[1] + n * thick) for p in pts]
        t.faces.new(a)
        t.faces.new(b)
        for i in range(len(pts)):
            j = (i + 1) % len(pts)
            t.faces.new((a[i], a[j], b[j], b[i]))
        bmesh.ops.recalc_face_normals(t, faces=t.faces)
        self._absorb(t, Matrix.Identity(4), mat)

    def arc_band(self, c, r_in, r_out, a0, a1, y0, y1, mat, steps=14):
        """Pás po oblouku kolem osy Y (střed c); úhel od svislice dolů, kladný směrem k +X."""
        t = bmesh.new()
        rings = []
        for k in range(steps + 1):
            a = a0 + (a1 - a0) * k / steps
            dx, dz = math.sin(a), -math.cos(a)
            rings.append([t.verts.new((c[0] + r * dx, y, c[2] + r * dz))
                          for r, y in ((r_in, y0), (r_out, y0), (r_out, y1), (r_in, y1))])
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(4):
                j = (i + 1) % 4
                t.faces.new((r0[i], r0[j], r1[j], r1[i])).smooth = True
        t.faces.new(rings[0][::-1])
        t.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(t, faces=t.faces)
        self._absorb(t, Matrix.Identity(4), mat)

    def scroll(self, c, u0, u1, r_in, r_out0, r_out1, chamfer, theta0, mat, steps=48):
        """Spirálové těleso čerpadla (osa X): průřez (šířka u0..u1, od r_in do r_out) se otáčí od theta0 o 360°
        a vnější poloměr roste od r_out0 k r_out1."""
        t = bmesh.new()
        rings = []
        for k in range(steps + 1):
            th = theta0 + TAU * k / steps
            ro = r_out0 + (r_out1 - r_out0) * k / steps
            sec = [(u0, r_in), (u1, r_in), (u1, ro - chamfer), (u1 - chamfer, ro), (u0 + chamfer, ro),
                   (u0, ro - chamfer)]
            rings.append([t.verts.new((c[0] + u, c[1] + r * math.cos(th), c[2] + r * math.sin(th))) for u, r in sec])
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(6):
                j = (i + 1) % 6
                t.faces.new((r0[i], r0[j], r1[j], r1[i])).smooth = True
        t.faces.new(rings[0][::-1])
        t.faces.new(rings[-1])
        bmesh.ops.recalc_face_normals(t, faces=t.faces)
        self._absorb(t, Matrix.Identity(4), mat)

    # ---- složené drobnosti

    def fins(self, c, axis, r0, r1, u0, u1, count, thick, mat, phase=0.0):
        """Radiální žebra kolem osy axis, na ose od u0 do u1 od bodu c."""
        axis = Vector(axis).normalized()
        c = Vector(c)
        ref = V(0, 0, 1) if abs(axis.z) < 0.9 else V(1, 0, 0)
        e1 = (ref - axis * ref.dot(axis)).normalized()
        e2 = axis.cross(e1)
        for k in range(count):
            a = phase + TAU * k / count
            radial = e1 * math.cos(a) + e2 * math.sin(a)
            mid = c + axis * ((u0 + u1) / 2) + radial * ((r0 + r1) / 2)
            self.obox((r1 - r0, thick, u1 - u0), frame(mid, axis, radial), mat)

    def bolt_circle(self, c, axis, circle_r, count, r, h, mat, phase=0.0):
        axis = Vector(axis).normalized()
        c = Vector(c)
        ref = V(0, 0, 1) if abs(axis.z) < 0.9 else V(1, 0, 0)
        e1 = (ref - axis * ref.dot(axis)).normalized()
        e2 = axis.cross(e1)
        for k in range(count):
            a = phase + TAU * k / count
            self.hex(c + (e1 * math.cos(a) + e2 * math.sin(a)) * circle_r, axis, r, h, mat)

    def flange(self, c, axis, r_out, thick, mat, bolts=4, bolt_r=0.0, bolt_size=0.006, bolt_mat=None, phase=0.0):
        c = Vector(c)
        axis = Vector(axis).normalized()
        self.cyl(c, c + axis * thick, r_out, mat, seg=24)
        if bolts:
            self.bolt_circle(c + axis * thick, axis, bolt_r or r_out * 0.78, bolts, bolt_size, bolt_size * 0.9,
                             bolt_mat or mat, phase)

    def clamp(self, c, axis, r, mat="SDT_Steel", width=0.014):
        """Hadicová spona: pás kolem hadice o poloměru r a šroub."""
        c = Vector(c)
        axis = Vector(axis).normalized()
        self.cyl(c - axis * width / 2, c + axis * width / 2, r + 0.004, mat, seg=20)
        ref = V(0, 0, 1) if abs(axis.z) < 0.9 else V(1, 0, 0)
        up = (ref - axis * ref.dot(axis)).normalized()
        side = axis.cross(up)
        self.obox((width, 0.014, 0.012), frame(c + up * (r + 0.008), side, axis), mat)

    def lever(self, base, stem_dir, handle_dir, length, metal="SDT_Steel", grip="SDT_PaintRed", width=0.018):
        """Páka kulového kohoutu: vřeteno ze středu, matice, plochá páka a barevná rukojeť na konci."""
        base = Vector(base)
        s = Vector(stem_dir).normalized()
        h = Vector(handle_dir).normalized()
        n = s.cross(h).normalized()
        self.cyl(base, base + s * 0.036, 0.007, metal, seg=8)
        self.hex(base + s * 0.028, s, 0.011, 0.008, metal)
        top = base + s * 0.040
        self.obox((length, width * 0.7, 0.005), frame(top + h * (length / 2 - 0.012), n, h), metal)
        self.obox((length * 0.55, width, 0.012), frame(top + h * (length * 0.72) + s * 0.003, n, h), grip, bevel=0.003)

    def ball_valve(self, p0, p1, radius, lever_dir, lever_grip, lever_len=0.11, body="SDT_Brass"):
        """Kulový kohout mezi p0 a p1: mosazné tělo s hrdly a maticemi, páka kolmo na osu ve směru lever_dir."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        ln = d.length
        a = d.normalized()
        rb = radius * 1.55
        prof = [(0, 0), (radius * 0.85, 0), (radius * 0.85, ln * 0.18), (rb * 0.8, ln * 0.26), (rb, ln * 0.40),
                (rb, ln * 0.60), (rb * 0.8, ln * 0.74), (radius * 0.85, ln * 0.82), (radius * 0.85, ln), (0, ln)]
        self.lathe(prof, p0, a, body, seg=20, hard=(1, 8))
        mid = p0 + a * (ln * 0.5)
        ld = Vector(lever_dir).normalized()
        self.lever(mid + ld * (rb * 0.9), ld, a, lever_len, grip=lever_grip)
        return mid

    def hose_tail(self, p0, p1, radius, mat="SDT_Steel", rings=2):
        """Hadicový nátrubek s vroubky mezi p0 a p1 (p1 je na straně hadice)."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        ln = d.length
        a = d.normalized()
        self.cyl(p0, p1, radius, mat, seg=16)
        for k in range(rings):
            s = ln * (0.35 + 0.4 * k / max(rings - 1, 1)) if rings > 1 else ln * 0.6
            self.cyl(p0 + a * s, p0 + a * (s + ln * 0.18), radius * 1.18, mat, r1=radius * 1.02, seg=16)

    def finish(self):
        bm = self.bm
        bm.normal_update()
        P._box_uv(bm)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(P.material(m))
        obj = bpy.data.objects.new(self.name, me)
        P._coll.objects.link(obj)
        obj.parent = P._root
        obj.matrix_world = Matrix.Identity(4)
        return obj


# ------------------------------------------------------------------------------------------ hlavní nádrž

def main_tank_ports(y, z, radius, length):
    """Výpust hlavní nádrže: na předním dně dole vpravo od středu, směr -Y."""
    zc = z + 0.12 + radius
    px, dz = 0.25 * radius, -0.675 * radius
    th = math.asin(math.hypot(px, dz) / radius)
    yd = y - length / 2 + HEAD * (1 - math.cos(th))
    return {"center": V(0, y, zc), "drain": V(px, yd, zc + dz), "drain_dir": V(0, -1, 0)}


def _tank_profile(radius, length, head, grooves, bead=0.006):
    """Profil ležatého PE tanku (poloměr, poloha po ose od středu): eliptická dna, svarové lemy na spojích, vylisované
    drážky."""
    half = length / 2
    ends = (0, 12, 24, 36, 48, 58, 68, 77, 84)
    pts = [(radius * math.sin(math.radians(d)), -half + head * (1 - math.cos(math.radians(d)))) for d in ends]
    samples = {}

    def add(a, r):
        samples[round(a, 5)] = r

    aj = half - head
    for c in (-aj, aj):
        for d, dr in ((-0.014, 0.0), (-0.007, bead * 0.65), (0.0, bead), (0.007, bead * 0.65), (0.014, 0.0)):
            add(c + d, radius + dr)
    for c in grooves:
        for d, dr in ((-0.035, 0.0), (-0.024, -0.003), (-0.012, -0.0075), (0.0, -0.009), (0.012, -0.0075),
                      (0.024, -0.003), (0.035, 0.0)):
            add(c + d, radius + dr)
    for a in (-0.40, -0.14, 0.0, 0.14, 0.40):
        add(a, radius)
    pts +=[(r, a) for a, r in sorted(samples.items())]
    pts += [(radius * math.sin(math.radians(d)), half - head * (1 - math.cos(math.radians(d)))) for d in reversed(ends)]
    return pts


def build_main_tank(prefix, y, z, radius, length):
    """Hlavní nádrž ~1000 l: bílý rotační PE válec s eliptickými dny, svarovými lemy, dvěma vylisovanými drážkami,
    hrdlem (manway) se šroubovacím víkem, odvzdušněním, hladinoměrem na pravém boku, výpustným kohoutem vpředu a
    vypouštěcím kohoutem vzadu, na dvou svařených ocelových sedlech (bez popruhů)."""
    zc = z + 0.12 + radius
    head = HEAD
    shell = Mesh(prefix)
    steel = Mesh(f"{prefix}_Saddles")
    fit = Mesh(f"{prefix}_Fittings")
    lid = Mesh(f"{prefix}_Lid")
    center = V(0, y, zc)
    k = radius / MAIN_TANK_REF_R
    prof = _tank_profile(radius, length, head, grooves=(-0.28, 0.28))
    shell.lathe(prof, V(0, y, zc), V(0, 1, 0), "SDT_TankPE", seg=56, ref=V(0, 0, 1))

    # hrdlo (manway): krk s lemem, šroubovací víko s vroubkováním a madlem
    top = zc + radius
    neck = [(0.15 * k, -0.06), (0.15 * k, 0.005), (0.163 * k, 0.007), (0.163 * k, 0.020), (0.0, 0.020)]
    shell.lathe(neck, V(0, y, top), V(0, 0, 1), "SDT_TankPE", seg=40, hard=(2,))
    cap_z = top + 0.020
    cap = [(0.0, 0.0), (0.168 * k, 0.0), (0.168 * k, 0.026), (0.160 * k, 0.034), (0.0, 0.034)]
    lid.lathe(cap, V(0, y, cap_z), V(0, 0, 1), "SDT_TankPE", seg=40, hard=(1, 2))
    nlug = round(28 * k)
    for i in range(nlug):
        a = TAU * i / nlug
        p = V(0.170 * k * math.cos(a), y + 0.170 * k * math.sin(a), cap_z + 0.013)
        lid.obox((0.008, 0.007, 0.024), frame(p, V(0, 0, 1), V(math.cos(a), math.sin(a), 0)), "SDT_TankPE")
    hg = 0.085 * k
    lid.box(-hg, hg, y - 0.014, y + 0.014, cap_z + 0.034, cap_z + 0.046, "SDT_TankBlack", bevel=0.004)
    for sx in (-1, 1):
        lid.box(sx * hg - 0.007, sx * hg + 0.007, y - 0.014, y + 0.014, cap_z + 0.030, cap_z + 0.036,
                "SDT_TankBlack")
    fit.torus(V(0, y, cap_z + 0.001), V(0, 0, 1), 0.164 * k, 0.002, "SDT_Rubber", seg=40, rseg=4)

    # odvzdušnění: patka po normále plášťě, stopka a černá houbovitá hlavička
    for sx, dy in ((-0.14 * k, -0.40),):
        n = V(sx, 0, math.sqrt(radius ** 2 - sx ** 2)).normalized()
        base = V(sx, y + dy, zc + math.sqrt(radius ** 2 - sx ** 2))
        fit.cyl(base - n * 0.01, base + n * 0.016, 0.034, "SDT_TankPE", seg=18)
        fit.cyl(base + n * 0.016, base + n * 0.046, 0.011, "SDT_TankBlack", seg=10)
        fit.cyl(base + n * 0.046, base + n * 0.058, 0.026, "SDT_TankBlack", r1=0.02, seg=18)

    # výpust vpředu dole: přírubový průchod, kulový kohout s červenou pákou, hadicový nátrubek
    ports = main_tank_ports(y, z, radius, length)
    d = ports["drain"]
    fwd = V(0, -1, 0)
    fit.cyl(d - fwd * 0.035, d + fwd * 0.012, 0.036, "SDT_TankPE", seg=20)
    fit.flange(d + fwd * 0.010, fwd, 0.05, 0.012, "SDT_Steel", bolts=6, bolt_r=0.039, bolt_size=0.0055)
    fit.cyl(d + fwd * 0.022, d + fwd * 0.052, 0.026, "SDT_Steel", seg=14)
    v0, v1 = d + fwd * 0.052, d + fwd * 0.122
    fit.ball_valve(v0, v1, 0.026, V(0, 0, 1), "SDT_PaintRed", lever_len=0.12)
    fit.cyl(v1, v1 + fwd * 0.020, 0.030, "SDT_Brass", seg=6)
    fit.hose_tail(v1 + fwd * 0.020, v1 + fwd * 0.066, 0.0255)

    # vypouštěcí kohout vzadu dole
    rr = 0.825 * radius
    zb = zc - rr
    th = math.asin(min(rr / radius, 0.999))
    yb = y + (length / 2 - head * (1 - math.cos(th)))
    fit.cyl(V(0, yb - 0.02, zb), V(0, yb + 0.014, zb), 0.030, "SDT_TankPE", seg=18)
    fit.cyl(V(0, yb + 0.010, zb), V(0, yb + 0.030, zb), 0.020, "SDT_Steel", seg=12)
    fit.ball_valve(V(0, yb + 0.030, zb), V(0, yb + 0.090, zb), 0.017, V(1, 0, 0), "SDT_ValveBlue", lever_len=0.085)
    fit.cyl(V(0, yb + 0.090, zb), V(0, yb + 0.118, zb), 0.018, "SDT_Brass", seg=14)
    fit.cyl(V(0, yb + 0.118, zb), V(0, yb + 0.132, zb), 0.020, "SDT_Steel", seg=14)

    # hladinoměr na pravém boku: dvě průchodky, kohout dole, průhledná trubka s modrým sloupcem, stupnice
    gy = y + 0.20
    gx = -(radius + 0.03)
    z_lo, z_hi = zc - 0.26 * k, zc + 0.26 * k
    for zz, valve in ((z_lo, True), (z_hi, False)):
        sx = -math.sqrt(radius ** 2 - (zz - zc) ** 2)
        fit.cyl(V(sx + 0.012, gy, zz), V(sx - 0.014, gy, zz), 0.024, "SDT_TankPE", seg=14)
        fit.cyl(V(sx - 0.010, gy, zz), V(sx - 0.030, gy, zz), 0.016, "SDT_Brass", seg=6)
        if valve:
            fit.ball_valve(V(sx - 0.030, gy, zz), V(gx + 0.045, gy, zz), 0.011, V(0, 1, 0), "SDT_PaintRed",
                           lever_len=0.06)
        else:
            fit.cyl(V(sx - 0.030, gy, zz), V(gx + 0.008, gy, zz), 0.011, "SDT_Brass", seg=10)
        fit.sphere(V(gx, gy, zz), 0.019, "SDT_Brass", seg=14, rings=8)
    fit.cyl(V(gx + 0.022, gy, z_lo), V(gx, gy, z_lo), 0.013, "SDT_Brass", seg=10)
    fit.cyl(V(gx, gy, z_lo), V(gx, gy, z_hi), 0.0115, "SDT_TankPE", seg=12)
    fit.cyl(V(gx, gy, z_lo), V(gx, gy, z_lo + 0.29 * k), 0.0119, "SDT_ValveBlue", seg=12)
    fit.box(gx + 0.0175, gx + 0.0225, gy - 0.026, gy + 0.026, z_lo, z_hi, "SDT_Steel", bevel=0.002)
    for i in range(9):
        zz = z_lo + 0.02 + i * (z_hi - z_lo - 0.04) / 8
        ln = 0.026 if i % 2 == 0 else 0.016
        fit.box(gx + 0.0165, gx + 0.0176, gy - 0.026, gy - 0.026 + ln * 0.85, zz - 0.0015, zz + 0.0015,
                "SDT_TankBlack")

    # sedla: patní deska s U profilem, lopatky, ocelový oblouk s gumovou vložkou, šrouby
    sw = 0.9 * radius
    for i, dy in enumerate((-0.42, 0.42)):
        ys = y + dy
        w = 0.055
        steel.box(-sw, sw, ys - w, ys + w, z, z + 0.008, "SDT_Frame")
        for sy in (-1, 1):
            steel.box(-sw, sw, ys + sy * w - 0.003, ys + sy * w + 0.003, z, z + 0.034, "SDT_Frame")
        for wx in (-0.75 * radius, -0.375 * radius, 0.0, 0.375 * radius, 0.75 * radius):
            zt = zc - math.sqrt((radius + 0.006) ** 2 - wx ** 2)
            steel.box(wx - 0.004, wx + 0.004, ys - 0.045, ys + 0.045, z + 0.008, zt + 0.001, "SDT_Frame")
        steel.arc_band(center, radius + 0.0006, radius + 0.0034, math.radians(-54), math.radians(54),
                       ys - 0.05, ys + 0.05, "SDT_Rubber")
        steel.arc_band(center, radius + 0.0034, radius + 0.0094, math.radians(-56), math.radians(56),
                       ys - 0.05, ys + 0.05, "SDT_Frame")
        for bx in (-0.84 * radius, 0.84 * radius):
            for by in (-1, 1):
                steel.hex(V(bx, ys + by * 0.028, z + 0.008), V(0, 0, 1), 0.0085, 0.008, "SDT_Steel")
    shell.finish()
    steel.finish()
    fit.finish()
    lid.finish()


# ------------------------------------------------------------------------------------------ indukční nádrž

def induction_ports(x, y, z, radius=INDUCTION_R, stand_h=INDUCTION_STAND_H, cone_h=INDUCTION_CONE_H):
    """Výpust ze dna kužele: dolů, kohout, koleno a vodorovně dozadu (+Y); konec nátrubku pro hadici."""
    zr = z + stand_h - 0.18
    return {"bottom": V(x, y, z + stand_h), "run_z": zr, "hose_end": V(x, y + 0.20, zr)}


def induction_level_height(litres, radius=INDUCTION_R, cone_h=INDUCTION_CONE_H):
    """Výška hladiny nad dnem kužele (m) pro objem v litrech: vnitřní objem kuželu a válce nad ním (stěna 4 mm)."""
    dh, v, h = 0.0002, 0.0, 0.0
    while v < litres / 1000.0:
        r = INDUCTION_R0 + (radius - INDUCTION_R0) * min(h / cone_h, 1.0) - INDUCTION_WALL
        v += math.pi * r * r * dh
        h += dh
    return h


def _induction_scale(fit, x, y, zb, R, cone_h):
    """Stupnice na pravém boku (-X): černý pruh po povrchu (kužel a válec), bílé rysky po 5 l, delší po 10 l, červená
    na 50 l. Rysky mají v ose Y rozsah y - 0,019 .. y + 0,019 (delší) od levého okraje pruhu."""
    R0 = INDUCTION_R0
    L = math.hypot(R - R0, cone_h)
    n_cone = V(-cone_h / L, 0, -(R - R0) / L)
    m_cone = V(-(R - R0) / L, 0, cone_h / L)

    def surf(h):
        if h < cone_h:
            r = R0 + (R - R0) * h / cone_h
            return V(x - r, y, zb + h), n_cone, m_cone, 0.001
        return V(x - R, y, zb + h), V(-1, 0, 0), V(0, 0, 1), 0.0055

    def strip(h0, h1, thick, mat, y0, y1, off_extra):
        p0, n, m, off = surf((h0 + h1) / 2)
        length = (h1 - h0) / m.z
        c = p0 + n * (off + off_extra + thick / 2)
        c.y = (y0 + y1) / 2
        fit.obox((length, y1 - y0, thick), frame(c, n, m), mat)

    h_lo, h_hi = induction_level_height(2.0, R, cone_h), induction_level_height(52.0, R, cone_h)
    strip(h_lo, cone_h - 0.0005, 0.004, "SDT_TankBlack", y - 0.022, y + 0.022, 0.0)
    strip(cone_h + 0.0005, h_hi, 0.004, "SDT_TankBlack", y - 0.022, y + 0.022, 0.0)
    for litres in range(5, 51, 5):
        h = induction_level_height(litres, R, cone_h)
        p, n, m, off = surf(h)
        big = litres % 10 == 0
        ln = 0.038 if litres == 50 else (0.032 if big else 0.018)
        c = p + n * (off + 0.004 + 0.0008)
        c.y = y - 0.019 + ln / 2
        fit.obox((0.0026, ln, 0.0016), frame(c, n, m), "SDT_PaintRed" if litres == 50 else "SDT_PaintWhite")


def induction_fill_box(x, y, z, radius=INDUCTION_R, stand_h=INDUCTION_STAND_H, cone_h=INDUCTION_CONE_H,
                       body_h=INDUCTION_BODY_H):
    """Kvádr pro concentrateFillRootNode: nádrž od dna kužele po plnicí hrdlo s víčkem; x0, x1, y0, y1, z0, z1."""
    top = z + stand_h + cone_h + body_h + 0.10
    return x - radius - 0.03, x + radius + 0.03, y - radius - 0.03, y + radius + 0.03, z + stand_h - 0.04, top


def build_induction_tank(prefix, x, y, z, radius=INDUCTION_R, stand_h=INDUCTION_STAND_H, cone_h=INDUCTION_CONE_H,
                         body_h=INDUCTION_BODY_H):
    """Plnitelná koncentrátová (indukční) nádrž ~50 l: bílý PE válec s kuželovým dnem na svařeném stojanu (čtyři šikmé
    nohy, rám, patky), nahoře mísa se zdviženým okrajem a plnicí hrdlo se zvednutým lemem a šroubovacím víčkem na lanku
    (nalévá se z kanystru), kalibrovaná stupnice hladiny po 5 l na pravém boku, plocha pro štítek vpředu, hadicová
    přípojka (kamlok) na levém boku a výpust s kohoutem a kolenem. Vrací výšku vrcholu víčka."""
    zb = z + stand_h
    zj = zb + cone_h
    zt = zj + body_h
    R = radius
    s = R / 0.30                            # drobnosti jsou navržené pro poloměr 0,30 a s ním se poměrově mění
    shell = Mesh(prefix)
    stand = Mesh(f"{prefix}_Stand")
    fit = Mesh(f"{prefix}_Fittings")
    lid = Mesh(f"{prefix}_Lid")

    def cz(zz):
        return V(x, y, zz)

    rn, rl = INDUCTION_NECK_R, INDUCTION_NECK_LIP
    prof = [(0.0, zb), (0.052, zb), (R, zj), (R + 0.004, zj + 0.012), (R, zj + 0.024),
            (R, zt - 0.100), (R - 0.006 * s, zt - 0.092), (R - 0.006 * s, zt - 0.070), (R, zt - 0.062),
            (R, zt - 0.030), (R - 0.010, zt - 0.012),
            (R - 0.018, zt), (R - 0.018, zt + 0.012), (R - 0.030, zt + 0.012),     # zdvižený okraj mísy kolem hrdla
            (R - 0.030, zt + 0.002), (0.150, zt), (rn + 0.022, zt), (rn, zt + 0.012),
            (rn, zt + 0.034), (rl, zt + 0.040), (rl, zt + 0.048),                   # krk hrdla se zvednutým lemem
            (rn - 0.012, zt + 0.048), (rn - 0.012, zt - 0.030), (0.0, zt - 0.030)]
    shell.lathe(prof, cz(0), V(0, 0, 1), "SDT_TankPE", seg=48, hard=(1, 11, 12, 13, 20, 21, 22))

    # výpust: nálitek na dně, příruba, kohout s červenou pákou k pravému boku, koleno, nátrubek a spona
    ports = induction_ports(x, y, z, radius, stand_h, cone_h)
    zr = ports["run_z"]
    fit.cyl(cz(zb + 0.03), cz(zb - 0.006), 0.062, "SDT_TankPE", seg=20)
    fit.flange(cz(zb - 0.006), V(0, 0, -1), 0.062, 0.012, "SDT_Steel", bolts=6, bolt_r=0.048, bolt_size=0.0055)
    fit.cyl(cz(zb - 0.018), cz(zb - 0.045), 0.028, "SDT_Steel", seg=14)
    zv1 = zb - 0.045
    zv2 = zv1 - 0.070
    fit.ball_valve(cz(zv1), cz(zv2), 0.028, V(-1, 0, 0), "SDT_PaintRed", lever_len=0.13)
    fit.cyl(cz(zv2), cz(zv2 - 0.020), 0.030, "SDT_Brass", seg=6)
    fit.cyl(cz(zv2 - 0.020), cz(zr), 0.027, "SDT_Steel", seg=12)
    fit.sphere(cz(zr), 0.037, "SDT_Steel", seg=16, rings=8)
    fit.cyl(cz(zr), V(x, y + 0.11, zr), 0.027, "SDT_Steel", seg=12)
    fit.cyl(V(x, y + 0.11, zr), V(x, y + 0.13, zr), 0.033, "SDT_Steel", seg=6)
    fit.hose_tail(V(x, y + 0.13, zr), ports["hose_end"], 0.0255)
    fit.clamp(V(x, y + 0.18, zr), V(0, 1, 0), 0.0255)

    # stojan: čtyři šikmé nohy s patkami a botkami, rám kolem (vzadu volno pro výpust), knotové desky na plášti
    leg_foot, leg_top = INDUCTION_LEG_R, 0.2227 * s
    zt_leg = zj
    for sx in (-1, 1):
        for sy in (-1, 1):
            f = V(x + sx * leg_foot, y + sy * leg_foot, z + 0.004)
            t = V(x + sx * leg_top, y + sy * leg_top, zt_leg)
            stand.cyl(f + V(0, 0, 0.004), t, 0.019, "SDT_Frame", square=True, ref=V(1, 0, 0))
            stand.box(f.x - 0.04, f.x + 0.04, f.y - 0.04, f.y + 0.04, z, z + 0.008, "SDT_Frame", bevel=0.004)
            stand.hex(f + V(0, 0, 0.004), V(0, 0, 1), 0.0085, 0.008, "SDT_Steel")
            dirv = V(sx, sy, 0).normalized()
            stand.obox((0.07, 0.04, 0.008), frame(t + dirv * (-0.012) + V(0, 0, 0.02), V(0, 0, 1), dirv),
                       "SDT_Frame", bevel=0.002)
    zf = z + 0.22
    frac = (zf - (z + 0.004)) / (zt_leg - (z + 0.004))
    half = leg_foot + (leg_top - leg_foot) * frac
    for sx in (-1, 1):
        stand.cyl(V(x + sx * half, y - half, zf), V(x + sx * half, y + half, zf), 0.016, "SDT_Frame", square=True,
                  ref=V(1, 0, 0))
    stand.cyl(V(x - half, y - half, zf), V(x + half, y - half, zf), 0.016, "SDT_Frame", square=True, ref=V(0, 1, 0))
    for sx in (-1, 1):
        stand.cyl(V(x + sx * leg_foot, y - leg_foot, z + 0.05), V(x + sx * half, y - half, zf), 0.010, "SDT_Frame",
                  seg=6)

    # stupnice hladiny na pravém boku (-X), kalibrovaná po 5 l podle skutečného objemu (kužel + válec), a plocha pro štítek
    _induction_scale(fit, x, y, zb, R, cone_h)
    hw = 0.065
    xe = math.sqrt(R * R - hw * hw)
    fit.box(x - hw, x + hw, y - R - 0.003, y - xe + 0.004, zj + 0.115, zj + 0.215, "SDT_PaintWhite", bevel=0.003)

    # kamlok na levém boku (+X): patka, trubka, spojka s vačkami, víčko na očku
    zk = zj + 0.17
    ex = x + R
    fit.cyl(V(ex - 0.012, y, zk), V(ex + 0.016, y, zk), 0.036, "SDT_TankPE", seg=16)
    fit.cyl(V(ex + 0.010, y, zk), V(ex + 0.050, y, zk), 0.022, "SDT_Steel", seg=14)
    fit.cyl(V(ex + 0.050, y, zk), V(ex + 0.078, y, zk), 0.029, "SDT_Steel", seg=14)
    fit.cyl(V(ex + 0.078, y, zk), V(ex + 0.090, y, zk), 0.032, "SDT_Frame", seg=14)
    for sy in (-1, 1):
        fit.obox((0.022, 0.006, 0.010), frame(V(ex + 0.060, y + sy * 0.032, zk), V(1, 0, 0), V(0, 1, 0)), "SDT_Steel")
        fit.obox((0.008, 0.008, 0.026), frame(V(ex + 0.056, y + sy * 0.034, zk + 0.008), V(0, 0, 1), V(1, 0, 0)),
                 "SDT_Steel")
    fit.torus(V(ex + 0.030, y, zk - 0.024), V(1, 0, 0), 0.010, 0.0025, "SDT_Steel", seg=10, rseg=5)

    # plnicí hrdlo: šroubovací víčko s vroubkováním a madlem, těsnění, lanko k oku na okraji mísy, odvzdušňovací zátka
    cap_z = zt + 0.049
    cap = [(0.0, cap_z), (0.124, cap_z), (0.124, cap_z + 0.030), (0.117, cap_z + 0.038), (0.0, cap_z + 0.038)]
    lid.lathe(cap, cz(0), V(0, 0, 1), "SDT_TankPE", seg=40, hard=(1, 2))
    nlug = 26
    for k in range(nlug):
        a = TAU * k / nlug
        p = V(x + 0.127 * math.cos(a), y + 0.127 * math.sin(a), cap_z + 0.015)
        lid.obox((0.008, 0.007, 0.024), frame(p, V(0, 0, 1), V(math.cos(a), math.sin(a), 0)), "SDT_TankPE")
    lid.torus(cz(cap_z + 0.001), V(0, 0, 1), 0.105, 0.003, "SDT_Rubber", seg=40, rseg=4)
    lid.box(x - 0.07, x + 0.07, y - 0.013, y + 0.013, cap_z + 0.038, cap_z + 0.050, "SDT_TankBlack", bevel=0.004)
    for sx in (-1, 1):
        lid.box(x + sx * 0.07 - 0.007, x + sx * 0.07 + 0.007, y - 0.013, y + 0.013, cap_z + 0.034, cap_z + 0.040,
                "SDT_TankBlack")
    lid.torus(V(x, y + 0.126, cap_z + 0.014), V(1, 0, 0), 0.008, 0.002, "SDT_Steel", seg=10, rseg=4)
    lid.cyl(V(x, y + 0.132, cap_z + 0.012), V(x, y + 0.155, cap_z - 0.004), 0.0035, "SDT_Rubber", seg=6)
    lid.cyl(V(x, y + 0.155, cap_z - 0.004), V(x, y + 0.165, zt + 0.010), 0.0035, "SDT_Rubber", seg=6)
    lid.box(x - 0.012, x + 0.012, y + 0.158, y + 0.176, zt, zt + 0.010, "SDT_Steel", bevel=0.002)
    fit.cyl(V(x, y - 0.150, zt), V(x, y - 0.150, zt + 0.020), 0.011, "SDT_TankBlack", seg=10)
    fit.cyl(V(x, y - 0.150, zt + 0.020), V(x, y - 0.150, zt + 0.028), 0.017, "SDT_TankBlack", r1=0.012, seg=12)
    shell.finish()
    stand.finish()
    fit.finish()
    lid.finish()
    neck = P.empty("concentrateNeckNode", cz(cap_z + 0.038))
    neck.empty_display_size = 0.10
    return cap_z + 0.050


# ------------------------------------------------------------------------------------------ čerpadlo

def pump_ports(px, py, z):
    """Sání (čelo příruby na +X), osa a výtlak (příruba nahoře) čerpadla."""
    hz = z + PUMP_AXIS_H
    return {"axis_z": hz, "inlet": V(px + PUMP_PORT_U, py, hz), "elbow": V(px + TEE_U, py, hz),
            "tee": V(px + TEE_U, py + TEE_DY, hz), "outlet": V(px + 0.17, py, hz + 0.179),
            "gauge": V(px + 0.20, py + 0.10, hz + 0.205)}


def build_pump(prefix, px, py, z):
    """Odstředivé monoblokové čerpadlo: svařený stojan z trubek, elektromotor s žebrováním, patkami, svorkovnicí a
    ventilátorem pod drátěným krytem, lucerna se spojkou, spirální těleso čerpadla s víkem a šrouby, sání s přírubou
    (+X), výtlak nahoře s přírubou a manometrem, výpustná zátka."""
    hz = z + PUMP_AXIS_H
    m = Mesh(prefix)
    ax = V(1, 0, 0)
    C = V(px, py, hz)

    # stojan
    yy = 0.15
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = px + sx * 0.20, py + sy * yy
            m.cyl(V(lx, ly, z + 0.008), V(lx, ly, z + 0.246), 0.018, "SDT_Frame", square=True, ref=V(1, 0, 0))
            m.box(lx - 0.035, lx + 0.035, ly - 0.035, ly + 0.035, z, z + 0.008, "SDT_Frame", bevel=0.003)
            m.hex(V(lx, ly, z + 0.008), V(0, 0, 1), 0.008, 0.007, "SDT_Steel")
    for sy in (-1, 1):
        m.cyl(V(px - 0.22, py + sy * yy, z + 0.235), V(px + 0.22, py + sy * yy, z + 0.235), 0.017, "SDT_Frame", square=True,
              ref=V(0, 0, 1))
        m.cyl(V(px - 0.20, py + sy * yy, z + 0.10), V(px + 0.20, py + sy * yy, z + 0.10), 0.013, "SDT_Frame", square=True,
              ref=V(0, 0, 1))
    for sx in (-1, 1):
        m.cyl(V(px + sx * 0.20, py - yy, z + 0.235), V(px + sx * 0.20, py + yy, z + 0.235), 0.017, "SDT_Frame", square=True,
              ref=V(1, 0, 0))
        m.cyl(V(px + sx * 0.20, py - yy, z + 0.10), V(px + sx * 0.20, py + yy, z + 0.10), 0.013, "SDT_Frame", square=True,
              ref=V(1, 0, 0))
    m.cyl(V(px, py - yy, z + 0.235), V(px, py + yy, z + 0.235), 0.015, "SDT_Frame", square=True, ref=V(1, 0, 0))
    m.box(px - 0.235, px + 0.235, py - 0.17, py + 0.17, z + 0.250, z + 0.257, "SDT_Frame", bevel=0.002)
    m.box(px - 0.235, px + 0.235, py - 0.17, py + 0.17, z + 0.257, z + 0.259, "SDT_Rubber")

    # motor
    plate_top = z + 0.259
    m.cyl(C + V(-0.170, 0, 0), C + V(0.058, 0, 0), 0.125, "SDT_PumpBlue", seg=32)
    m.fins(C, ax, 0.118, 0.152, -0.160, 0.046, 26, 0.0055, "SDT_PumpBlue")
    m.box(px - 0.145, px + 0.035, py - 0.075, py + 0.075, plate_top, hz - 0.11, "SDT_PumpBlue", bevel=0.003)
    for u in (-0.135, 0.005):
        m.box(px + u - 0.025, px + u + 0.025, py - 0.11, py + 0.11, plate_top, plate_top + 0.014, "SDT_PumpBlue",
              bevel=0.003)
        for sy in (-1, 1):
            m.hex(V(px + u, py + sy * 0.09, plate_top + 0.014), V(0, 0, 1), 0.007, 0.006, "SDT_Steel")
    # svorkovnice s krytem, šrouby a kabelovou vývodkou
    tb_z = hz + 0.168
    m.box(px - 0.115, px - 0.035, py - 0.045, py + 0.045, hz + 0.110, tb_z, "SDT_PumpBlue", bevel=0.004)
    m.box(px - 0.105, px - 0.045, py - 0.038, py + 0.038, tb_z, tb_z + 0.012, "SDT_PumpBlue", bevel=0.003)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.hex(V(px - 0.075 + sx * 0.044, py + sy * 0.03, tb_z + 0.012), V(0, 0, 1), 0.005, 0.004, "SDT_Steel")
    m.cyl(V(px - 0.075, py + 0.045, tb_z - 0.020), V(px - 0.075, py + 0.062, tb_z - 0.020), 0.014, "SDT_Plastic", seg=10)
    m.cyl(V(px - 0.075, py + 0.062, tb_z - 0.020), V(px - 0.075, py + 0.100, tb_z - 0.020), 0.009, "SDT_HoseBlack",
          seg=8)
    # štítek motoru
    m.box(px - 0.06, px + 0.0, py - 0.128, py - 0.1265, hz - 0.02, hz + 0.03, "SDT_Alu")
    # přední štít, lucerna se čtyřmi sloupky a spojkou, víko těsnění
    m.cyl(C + V(0.058, 0, 0), C + V(0.090, 0, 0), 0.140, "SDT_PumpBlue", seg=32)
    m.cyl(C + V(0.090, 0, 0), C + V(0.100, 0, 0), 0.128, "SDT_Alu", seg=32)
    m.cyl(C + V(0.100, 0, 0), C + V(0.130, 0, 0), 0.020, "SDT_Steel", seg=12)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        m.cyl(C + V(0.100, 0.112 * math.cos(a), 0.112 * math.sin(a)), C + V(0.130, 0.112 * math.cos(a),
                                                                            0.112 * math.sin(a)), 0.013, "SDT_Alu",
              seg=8)
    m.cyl(C + V(0.130, 0, 0), C + V(0.140, 0, 0), 0.128, "SDT_Alu", seg=32)

    # spirální těleso čerpadla, zadní deska, čelní víko se šrouby
    m.scroll(C, 0.140, 0.222, 0.05, 0.128, 0.152, 0.014, math.radians(90), "SDT_Alu", steps=56)
    m.cyl(C + V(0.140, 0, 0), C + V(0.150, 0, 0), 0.131, "SDT_Alu", seg=40)
    m.cyl(C + V(0.222, 0, 0), C + V(0.236, 0, 0), 0.136, "SDT_Alu", r1=0.132, seg=40)
    m.bolt_circle(C + V(0.236, 0, 0), ax, 0.114, 8, 0.0075, 0.007, "SDT_Steel", phase=math.radians(11))
    m.cyl(C + V(0.236, 0, 0), C + V(0.276, 0, 0), 0.052, "SDT_Alu", r1=0.044, seg=24)
    m.cyl(C + V(0.276, 0, 0), C + V(0.292, 0, 0), 0.044, "SDT_Alu", seg=24)
    m.flange(C + V(0.292, 0, 0), ax, 0.070, 0.018, "SDT_Steel", bolts=4, bolt_r=0.054, bolt_size=0.007,
             phase=math.radians(45))
    m.cyl(C + V(0.310, 0, 0), C + V(0.311, 0, 0), 0.030, "SDT_Rubber", seg=16)

    # výtlak nahoře: přechod ze skříně do hrdla a příruba
    ox = px + 0.17
    m.cyl(V(ox, py, hz + 0.115), V(ox, py, hz + 0.150), 0.050, "SDT_Alu", r1=0.038, seg=24)
    m.cyl(V(ox, py, hz + 0.150), V(ox, py, hz + 0.165), 0.038, "SDT_Alu", seg=24)
    m.flange(V(ox, py, hz + 0.165), V(0, 0, 1), 0.058, 0.014, "SDT_Steel", bolts=4, bolt_r=0.045, bolt_size=0.0065,
             phase=math.radians(45))
    # výpustná a zálivková zátka
    m.cyl(V(ox, py, hz - 0.155), V(ox, py, hz - 0.125), 0.013, "SDT_Brass", seg=6)
    m.cyl(V(px + 0.20, py - 0.10, hz + 0.12), V(px + 0.20, py - 0.10, hz + 0.155), 0.014, "SDT_Brass", seg=6)

    # manometr: stopka, šroubení, těleso s okrajem, bílý ciferník se stupnicí a červená ručička
    g = pump_ports(px, py, z)["gauge"]
    m.cyl(V(g.x, g.y, hz + 0.090), V(g.x, g.y, g.z - 0.040), 0.008, "SDT_Brass", seg=8)
    m.hex(V(g.x, g.y, hz + 0.100), V(0, 0, 1), 0.013, 0.010, "SDT_Brass")
    m.cyl(g + V(-0.016, 0, 0), g + V(0.016, 0, 0), 0.040, "SDT_Steel", seg=28)
    m.torus(g + V(-0.016, 0, 0), ax, 0.037, 0.004, "SDT_Steel", seg=28, rseg=6)
    m.cyl(g + V(-0.0165, 0, 0), g + V(-0.0155, 0, 0), 0.033, "SDT_PaintWhite", seg=28)
    for k in range(9):
        a = math.radians(-135 + 33.75 * k)
        radial = V(0, math.sin(a), math.cos(a))
        m.obox((0.006 if k % 2 else 0.009, 0.0025, 0.0008), frame(g + V(-0.0172, 0, 0) + radial * 0.027, ax, radial),
               "SDT_TankBlack")
    nd = V(0, math.sin(math.radians(20)), math.cos(math.radians(20)))
    m.obox((0.026, 0.004, 0.0015), frame(g + V(-0.0178, 0, 0) + nd * 0.010, ax, nd), "SDT_LampRed")

    # větrák pod drátěným krytem na zadní straně (-X)
    m.cyl(C + V(-0.200, 0, 0), C + V(-0.170, 0, 0), 0.138, "SDT_PumpBlue", seg=32)
    m.cyl(C + V(-0.200, 0, 0), C + V(-0.232, 0, 0), 0.030, "SDT_TankBlack", seg=14)
    for k in range(10):
        a = TAU * k / 10
        radial = V(0, math.cos(a), math.sin(a))
        mid = C + V(-0.216, 0, 0) + radial * 0.070
        blade = frame(mid, ax, radial)
        blade = blade @ Matrix.Rotation(math.radians(28), 4, "X")
        m.obox((0.085, 0.024, 0.003), blade, "SDT_TankBlack", bevel=0.001)
    gd = -0.258
    for rr in (0.045, 0.085, 0.128):
        m.torus(C + V(gd, 0, 0), ax, rr, 0.0032, "SDT_Steel", seg=32, rseg=5)
    for k in range(12):
        a = TAU * k / 12
        radial = V(0, math.cos(a), math.sin(a))
        m.cyl(C + V(gd, 0, 0), C + V(gd, 0, 0) + radial * 0.130, 0.0028, "SDT_Steel", seg=5)
        m.cyl(C + V(gd, 0, 0) + radial * 0.130, C + V(-0.200, 0, 0) + radial * 0.132, 0.0028, "SDT_Steel", seg=5)
    m.cyl(C + V(gd - 0.004, 0, 0), C + V(gd + 0.030, 0, 0), 0.012, "SDT_Steel", seg=10)
    m.finish()


# ------------------------------------------------------------------------------------------ rozvod

HOSE_R = 0.025                                # poloměr výtlačné hadice
DISCHARGE_BEND = 0.15                         # poloměr oblouků výtlačné hadice (osa hadice)
DISCHARGE_INTO_SWIVEL = 0.015                 # o kolik hadice zajíždí do čela otočné spojky (konec skrytý v ní)


def rounded_path(corners, radii, arc_deg_step=4.0, straight_step=0.20):
    """Lomená čára přes rohy corners (první a poslední bod jsou konce), v každém vnitřním rohu zaoblená kruhovým obloukem
    o poloměru radii[i], vzorkovaným po arc_deg_step stupních (rovnoměrně po úhlu); rovné úseky se dělí po straight_step,
    ať hladké stínování hadice nepřeskakuje mezi vzdálenými kruhy."""
    pts = [Vector(c) for c in corners]
    arcs = []
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        d0, d1 = (a - b).normalized(), (c - b).normalized()
        ang = d0.angle(d1)
        r = radii[i - 1]
        t = r / math.tan(ang / 2)
        assert t < (a - b).length and t < (c - b).length, f"oblouk {i} se nevejde (t={t:.3f})"
        p0, p1 = b + d0 * t, b + d1 * t
        center = b + (d0 + d1).normalized() * (r / math.sin(ang / 2))
        v0, v1 = (p0 - center).normalized(), (p1 - center).normalized()
        sweep_ang = v0.angle(v1)
        n = max(2, math.ceil(math.degrees(sweep_ang) / arc_deg_step))
        arcs.append((p0, p1, [center + v0.slerp(v1, k / n) * r for k in range(n + 1)]))
    out = [pts[0]]
    prev = pts[0]
    for p0, p1, arc in arcs:
        seg = p0 - prev
        for k in range(1, max(1, math.ceil(seg.length / straight_step))):
            out.append(prev + seg * (k / math.ceil(seg.length / straight_step)))
        out.extend(arc)
        prev = p1
    seg = pts[-1] - prev
    for k in range(1, max(1, math.ceil(seg.length / straight_step))):
        out.append(prev + seg * (k / math.ceil(seg.length / straight_step)))
    out.append(pts[-1])
    return out


def hose_hanger(m, c, ceiling_z, axis):
    """Černá objímka hadice (pás se šroubem) na podstavci přišroubovaném ke spodku horní desky; c = osa hadice v místě,
    axis = směr hadice (vodorovně)."""
    c = Vector(c)
    axis = Vector(axis).normalized()
    side = axis.cross(V(0, 0, 1)).normalized()
    w = 0.034
    prof = [(HOSE_R + 0.001, -w / 2), (HOSE_R + 0.005, -w / 2), (HOSE_R + 0.005, w / 2), (HOSE_R + 0.001, w / 2)]
    m.lathe(prof, c, axis, "SDT_Frame", seg=20, loop=True)
    top = c.z + HOSE_R + 0.005
    m.obox((w, 0.040, ceiling_z - top), frame(V(c.x, c.y, (top + ceiling_z) / 2), V(0, 0, 1), axis), "SDT_Frame",
           bevel=0.003)
    m.obox((w + 0.020, 0.095, 0.006), frame(V(c.x, c.y, ceiling_z - 0.003), V(0, 0, 1), axis), "SDT_Frame", bevel=0.002)
    for sx in (-1, 1):
        m.hex(V(c.x, c.y, ceiling_z - 0.006) + side * (sx * 0.036), V(0, 0, -1), 0.006, 0.004, "SDT_Steel")
    for sx in (-1, 1):
        m.hex(c + side * (sx * (HOSE_R + 0.008)), side * sx, 0.005, 0.004, "SDT_Steel")



def build_plumbing(z, tank_y, tank_r, tank_len, discharge_end, ceiling_z=None):
    """Rozvod: sání čerpadla (příruba, trubka, koleno, trubka dopředu) do mixéru (sdt_mixer) místo bývalého T-kusu; do
    něj vede hadice z výpustu hlavní nádrže MAIN_DRAIN (sdt_contract, u všech velikostí nádrže stejný; zprava vedle) a
    z výpustu koncentrátové nádrže (zleva zepředu); výtlak čerpadla přes přírubu a kulový kohout s modrou pákou do hadice
    k otočné spojce navíječe (discharge_end), vodorovný úsek je pod spodkem horní desky ceiling_z na objímkách. Parametry tank_* se už nepoužívají."""
    import importlib
    import sdt_mixer as X
    importlib.reload(X)

    px, py = PUMP_XY
    ix, iy = INDUCTION_XY
    pp = pump_ports(px, py, z)
    fit = Mesh("Plumbing")
    hz = pp["axis_z"]
    inl, el, tee = pp["inlet"], pp["elbow"], pp["tee"]

    fit.flange(inl + V(0.001, 0, 0), V(1, 0, 0), 0.070, 0.016, "SDT_Steel", bolts=4, bolt_r=0.054, bolt_size=0.007,
               phase=math.radians(45))
    fit.cyl(inl + V(0.017, 0, 0), el, 0.031, "SDT_Steel", seg=18)
    fit.cyl(inl + V(0.040, 0, 0), inl + V(0.070, 0, 0), 0.041, "SDT_Steel", seg=6)
    fit.sphere(el, 0.040, "SDT_Steel", seg=18, rings=9)
    fit.cyl(el + V(0, TEE_DY * 0.45, 0), el + V(0, TEE_DY * 0.45 - 0.030, 0), 0.041, "SDT_Steel", seg=6)
    X.build_mixer(tee, z, el)
    ports = X.mixer_ports(tee)

    o = pp["outlet"]
    fit.flange(o + V(0, 0, 0.001), V(0, 0, 1), 0.058, 0.014, "SDT_Steel", bolts=4, bolt_r=0.045, bolt_size=0.0065,
               phase=math.radians(45))
    fit.cyl(o + V(0, 0, 0.016), o + V(0, 0, 0.034), 0.030, "SDT_Steel", seg=16)
    fit.ball_valve(o + V(0, 0, 0.034), o + V(0, 0, 0.120), 0.030, V(-1, 0, 0), "SDT_ValveBlue", lever_len=0.14)
    fit.cyl(o + V(0, 0, 0.120), o + V(0, 0, 0.134), 0.033, "SDT_Brass", seg=6)
    fit.hose_tail(o + V(0, 0, 0.134), o + V(0, 0, 0.186), 0.0255)
    fit.clamp(o + V(0, 0, 0.172), V(0, 0, 1), 0.0255)
    top = o + V(0, 0, 0.170)

    drain = MAIN_DRAIN
    a = drain + V(0, -MAIN_DRAIN_HOSE, 0)
    fit.clamp(drain + V(0, -(MAIN_DRAIN_HOSE - 0.014), 0), V(0, 1, 0), 0.0255)
    b = ports["water_end"]
    P.sweep("Pump_Suction", P.hermite_path([a, b], tangents={0: (0, -1, 0), 1: (-1, 0, 0)}, samples=20), 0.025,
            "SDT_HoseBlack", segments=20)

    ip = induction_ports(ix, iy, z)
    a = ip["hose_end"] + V(0, -0.030, 0)
    b = ports["conc_end"]
    mids = [V(ix + 0.06, iy + 0.37, hz - 0.20), V(ix + 0.20, iy + 0.44, hz - 0.08)]
    P.sweep("Tank_Induction_Pipe", P.hermite_path([a] + mids + [b], tangents={0: (0, 1, 0), 3: (1, 0, 0)}, samples=12),
            0.025, "SDT_HoseBlack", segments=20)

    # výtlak: jedna souvislá hadice, svisle vzhůru z čerpadla, plynulým obloukem vodorovně pod deskou (přímo, rovnoběžně
    # s nosníky), plynulým obloukem svisle dolů a druhým obloukem o plných 90° vodorovně do osy otočné spojky navíječe
    # (osa X); všechny oblouky mají poloměr DISCHARGE_BEND; vpravo od indukční nádrže zůstává nad hrdlem volno
    end = Vector(discharge_end) + V(-DISCHARGE_INTO_SWIVEL, 0, 0)
    zh = ceiling_z - HOSE_R - 0.025 if ceiling_z else top.z + 0.9
    R = DISCHARGE_BEND
    corners = [top, V(top.x, top.y, zh), V(top.x, end.y, zh), V(top.x, end.y, end.z), end]
    pipe = rounded_path(corners, [R, R, R])
    P.sweep("Pump_Discharge", pipe, HOSE_R, "SDT_HoseBlack", segments=24)
    if ceiling_z:
        y0, y1 = top.y - R - 0.07, end.y + R + 0.06
        for k in range(4):
            hose_hanger(fit, V(top.x, y0 + (y1 - y0) * k / 3, zh), ceiling_z, V(0, 1, 0))
    fit.finish()


# ------------------------------------------------------------------------------------------ skříň na kanystry

TOOLBOX_XY = (-0.92, 0.95, 1.56, 2.04)      # x0, x1, y0, y1 půdorysu skříně; zadní stěna nádrže 5000 l je na y 1,32
CANISTER = (0.25, 0.17, 0.26)                # kanystr 20 l (herní měřítko): šířka po X, hloubka po Y, výška těla (bez hrdla a madla)


POCKET_CX, POCKET_HX, POCKET_HY, POCKET_DEPTH = -0.040, 0.044, 0.036, 0.016    # prohlubeň pod madlem v horní ploše
HANDLE_X = (-0.070, -0.010)                                                       # osy sloupků madla


def canister_shape(m, c, mat, cap_mat=None):
    """Tvar kanystru 20 l do sběrače m se středem základny v c: zaoblené tělo prolože (kulatá svislá i spodní hrana, rameno
    do hrdla), žebra, oblé madlo s přechody, hrdlo s fazetovaným víčkem. Polohy hrdla (x 0,062; vrch víčka H + 0,057) a štítku
    na bocích (y = +-D/2) se nesmí měnit, drží se na nich sloty, Lua a štítky."""
    W, D, H = CANISTER
    cap_mat = cap_mat or mat
    c = Vector(c)
    hx, hy = W / 2, D / 2
    top = H + 0.016
    m.loft(c, [
        (0.000, hx - 0.026, hy - 0.024, 0.030),
        (0.004, hx - 0.012, hy - 0.010, 0.034),
        (0.014, hx - 0.002, hy - 0.001, 0.038),
        (0.030, hx, hy, 0.040),
        (0.205, hx, hy, 0.040),
        (0.228, hx - 0.005, hy - 0.004, 0.040),
        (0.246, hx - 0.018, hy - 0.016, 0.040),
        (0.262, hx - 0.027, hy - 0.026, 0.036),
        (top, hx - 0.032, hy - 0.030, 0.032),
    ], mat, pocket=(POCKET_CX, POCKET_HX, POCKET_HY, 0.020, POCKET_DEPTH))
    for sy in (-1, 1):
        for zz in (0.05, 0.16):
            m.obox((W - 0.10, 0.007, 0.014), Matrix.Translation(c + V(0, sy * D / 2, zz)), mat, bevel=0.0032, segments=2)
    # madlo: oblý plochý oblouk z jednoho kusu, vystupuje z dna prohlubně, pod příčkou je místo na prsty
    x0, x1 = HANDLE_X
    floor = top - POCKET_DEPTH
    zt = top + 0.040
    rb = 0.017
    path, scales = [], []

    def add(x, z, s=1.0):
        path.append(V(x, 0, z))
        scales.append(s)

    add(x0, floor - 0.004, 1.45)
    add(x0, floor + 0.006, 1.2)
    add(x0, floor + 0.016, 1.0)
    add(x0, zt - rb)
    for k in range(1, 6):
        a = math.pi / 2 * k / 6
        add(x0 + rb - rb * math.cos(a), zt - rb + rb * math.sin(a))
    add(x0 + rb, zt)
    add((x0 + x1) / 2, zt)
    add(x1 - rb, zt)
    for k in range(1, 6):
        a = math.pi / 2 * k / 6
        add(x1 - rb + rb * math.sin(a), zt - rb + rb * math.cos(a))
    add(x1, zt - rb)
    add(x1, floor + 0.016, 1.0)
    add(x1, floor + 0.006, 1.2)
    add(x1, floor - 0.004, 1.45)
    m.tube([c + p for p in path], 0.0092, 0.0155, mat, seg=12, scales=scales)
    # hrdlo s náběhem, víčkem s fazetou, pojistným kroužkem a vroubky
    sx = 0.062
    m.cyl(c + V(sx, 0, top - 0.005), c + V(sx, 0, top + 0.004), 0.031, mat, r1=0.022, seg=20)
    m.cyl(c + V(sx, 0, top + 0.004), c + V(sx, 0, top + 0.011), 0.022, mat, seg=20)
    m.cyl(c + V(sx, 0, top + 0.011), c + V(sx, 0, top + 0.037), 0.027, cap_mat, seg=20)
    m.cyl(c + V(sx, 0, top + 0.037), c + V(sx, 0, top + 0.041), 0.027, cap_mat, r1=0.0235, seg=20)
    m.torus(c + V(sx, 0, top + 0.013), V(0, 0, 1), 0.0235, 0.0028, cap_mat, seg=20, rseg=5)
    for k in range(12):
        a = TAU * k / 12
        m.obox((0.005, 0.005, 0.022), frame(c + V(sx + 0.0285 * math.cos(a), 0.0285 * math.sin(a), top + 0.025),
                                            V(0, 0, 1), V(math.cos(a), math.sin(a), 0)), cap_mat, bevel=0.0012)


CANISTER_LABEL = (0.168, 0.084, 0.063)       # šířka, výška, spodek štítku nad základnou: mezi žebry jako build_canister.py


def canister_label(name, c, parent):
    """Neutrální štítek BZUK 20 l (oblast atlasu canisterLabel) na obou širokých stranách, dítě kanystru <name>_label."""
    lw, lh, lz = CANISTER_LABEL
    hy = CANISTER[1] / 2
    quads = [P.decal_quad(f"{name}_label{k}", c + V(-ux * lw / 2, sy * hy, lz), (ux, 0, 0), (0, 0, 1), lw, lh,
                          "canisterLabel", offset=0.0025)
             for k, (sy, ux) in enumerate(((-1, 1), (1, -1)))]
    bm = bmesh.new()
    for q in quads:
        q.data.transform(q.matrix_world)
        bm.from_mesh(q.data)
    me = bpy.data.meshes.new(f"{name}_label")
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(f"{name}_label", me)
    P._coll.objects.link(obj)
    obj.data.materials.append(P.material("SDT_Decal"))
    obj["i3D_decalLayer"] = 1
    obj["i3D_castsShadows"] = False
    for q in quads:
        data = q.data
        bpy.data.objects.remove(q)
        bpy.data.meshes.remove(data)
    obj.data.transform(Matrix.Translation(-c))
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = Matrix.Identity(4)
    return obj


def build_canister(name, c):
    """Zaoblený plastový kanystr 20 l se středem základny v c (tvar canister_shape), materiál SDT_Canister, barvu obsahu
    nastavuje skript přes colorScale. Dítě <name>_label je neutrální štítek z atlasu nálepek. Počátek objektu = c;
    build_canister.py má stejný tvar."""
    c = Vector(c)
    m = Mesh(name)
    canister_shape(m, c, "SDT_Canister")
    obj = m.finish()
    attach(obj, P._root, c)
    canister_label(name, c, obj)
    return obj
