"""Hlavní nádrž vleku v pěti velikostech (800 / 1000 / 1500 l válcové, 3000 / 5000 l hranaté), každá jako skupina
tankMain<litry>. Hranatá varianta (BoxTank, rozměry decal_layout.BOX_GEOM) vyplní místo pod horní plošinou, kam se kulatá
nádrž takového objemu nevejde; má stejné armatury, výpust, hrdlo a nálepky, ale kvádr se zaoblenými hranami na rámu.

Ležatá polyetylenová nádrž s eliptickými dny, svarovými lemy a vylisovanými drážkami na tvarovaných sedlech
s vodicími lištami, na svařeném rámu s patkami a nárazníky. Výbava: hrdlo (manway) s víkem na výklopných šroubech,
odvzdušnění, pojistný ventil, hladinoměr s průhlednou hadičkou ve hliníkovém krytu, výpust vpředu (kontrakt
sdt_contract.MAIN_DRAIN), vypouštěcí kohout vzadu, vylisované panely pro nálepky a štítek, u největší nádrže žebřík.
Všechny nálepky (objem, nápis, stupnice, piktogramy, výrobní štítek) jsou z atlasu decal_layout.py a patří do skupiny
své velikosti, takže se skrývají s nádrží.

Osa vleku: vpředu -Y, Z nahoru, počátek na zemi, střed šířky. Přední konec všech nádrží je na MAIN_TANK_Y_FRONT,
zadní se s velikostí posouvá dozadu. Spodek nádrže sedí GAP nad palubou.

Výpust: kohout a hadicový nátrubek jsou u všech velikostí na stejném místě (kontrakt sdt_contract): od bodu MAIN_DRAIN
(kde leží líc dna původní nádrže 1000 l) míří po MAIN_DRAIN_DIR a jejich konec je OUTLET_TIP_LEN před ním, kam navazuje
hadice rozvodu. Příruba sedí na dně dané velikosti a krátký krk dosáhne ke kohoutu.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import decal_layout as L
import sdt_parts as P
from sdt_contract import MAIN_DRAIN, MAIN_DRAIN_DIR, MAIN_TANK_Y_FRONT, TANK_SIZES
from sdt_tanks import Mesh, V, frame

TAU = 2.0 * math.pi
GAP = 0.12                      # mezera mezi palubou a spodkem nádrže (sedla)
OUTLET_TIP_LEN = 0.188          # konec hadicového nátrubku před MAIN_DRAIN (stejně jako u původní nádrže)
# uspořádání po ose (od předního konce, m): střed sedla, střed drážky (zadní jsou zrcadlově)
LAYOUT = {800: (0.26, 0.37), 1000: (0.28, 0.39), 1500: (0.31, 0.43)}
BOX_GAP = 0.06                  # hranatá nádrž: mezera mezi palubou a spodkem (příčníky a podélné nosníky rámu)
BOX_EDGE_R = 0.05               # zaoblení hran hranaté nádrže
BOX_RIBS = 0.78                 # vylisovaná žebra po obvodu nádrže: poloha nad / pod osou jako podíl poloviny výšky
BOX_MANWAY_R = 0.20             # vnější poloměr hrdla hranaté nádrže
GROOVE = ((-0.035, 0.0), (-0.024, -0.003), (-0.012, -0.0075), (0.0, -0.009), (0.012, -0.0075), (0.024, -0.003),
          (0.035, 0.0))
PE, BLACK, STEEL, BRASS, ALU, RUBBER = "SDT_TankPE", "SDT_TankBlack", "SDT_Steel", "SDT_Brass", "SDT_Alu", "SDT_Rubber"
FRAME_MAT = "SDT_Frame"


class Tank:
    def __init__(self, size, z):
        self.size = size
        self.R, self.Ln = L.TANK_GEOM[size]
        self.hd = L.TANK_HEAD_K * self.R
        self.z = z
        self.y0 = MAIN_TANK_Y_FRONT
        self.yc = self.y0 + self.Ln / 2
        self.zc = z + GAP + self.R
        self.k = self.R / 0.5
        self.kf = min(1.15, max(0.8, self.k))
        self.saddle_u, self.groove_u = LAYOUT[size]
        self.u_a = self.groove_u + 0.055          # volné pole mezi drážkami
        self.u_b = self.Ln - self.groove_u - 0.055
        self.mid = self.Ln / 2
        self.rn = 0.34 * self.R                   # vnější poloměr hrdla
        self.seg = 48 if self.R < 0.4 else 56
        self.wv = min(0.8 * self.R, (self.u_b - self.u_a) - 0.15)     # šířka nálepky s objemem
        self.center = V(0, self.yc, self.zc)
        self.top_z = self.zc + self.R

    def front_y_in(self, d):
        """Y nejpředenějšího bodu podložky výpusti: elipsoidové dno, podložka sahá 0,045 m od osy výpusti ke středu."""
        rho_in = max(math.hypot(d.x, d.z - self.zc) - 0.045, 0.0)
        return self.y0 + self.hd * (1 - math.sqrt(max(1 - (rho_in / self.R) ** 2, 0.0)))

    def wall(self, a_deg, u, lift=0.0):
        """Bod na válcové části (a od svislice dolů, kladně k +X; 180 = vrchol) a vnější normála."""
        a = math.radians(a_deg)
        n = V(math.sin(a), 0, -math.cos(a))
        return V(0, self.y0 + u, self.zc) + n * (self.R + lift), n

    def tangent(self, a_deg):
        a = math.radians(a_deg)
        return V(math.cos(a), 0, math.sin(a))


def volume_l(size):
    """Geometrický objem (válec + dva elipsoidové poloviční díly den) v litrech."""
    R, Ln = L.TANK_GEOM[size]
    return 1000.0 * math.pi * R * R * (Ln - 2.0 * L.TANK_HEAD_K * R / 3.0)


def stack(m, base, n, parts, ref=None):
    """Souosé válce a kužely podél n od bodu base: (t0, t1, r0, r1, materiál, segmenty)."""
    for t0, t1, r0, r1, mat, seg in parts:
        m.cyl(base + n * t0, base + n * t1, r0, mat, r1=r1, seg=seg, ref=ref)


# ------------------------------------------------------------------------------------------------- plášť

def _profile(t):
    R, half, hd = t.R, t.Ln / 2, t.hd
    aj = half - hd
    degs = (0, 9, 18, 27, 36, 45, 54, 62, 69, 75, 80, 84)
    front = [(R * math.sin(math.radians(d)), -half + hd * (1 - math.cos(math.radians(d)))) for d in degs]
    mid = {}
    bead = 0.006
    for s in (-1, 1):
        mid[round(s * aj, 5)] = R + bead
        mid[round(s * (aj - 0.007), 5)] = R + bead * 0.65
        mid[round(s * (aj - 0.014), 5)] = R
    for g in (t.groove_u - half, half - t.groove_u):
        for d, dr in GROOVE:
            mid[round(g + d, 5)] = R + dr
    pts = list(front)
    pts += [(r, a) for a, r in sorted(mid.items())]
    pts += [(R * math.sin(math.radians(d)), half - hd * (1 - math.cos(math.radians(d)))) for d in reversed(degs)]
    return pts


def _panel(t, m, a_c, u_c, w, h, bar=0.010, rise=0.005, solid=False, mat=PE):
    """Vylisovaný panel na válcové části: obdélníkový lem (nebo plná podložka) ve výšce h a šířce w podél osy.
    a_c = střed (rad, od svislice dolů), u_c = střed od předního konce."""
    da = (h / 2) / t.R
    a0, a1 = a_c - da, a_c + da
    y0, y1 = t.y0 + u_c - w / 2, t.y0 + u_c + w / 2
    steps = max(2, int(math.degrees(2 * da) / 6) + 1)
    c = t.center
    if solid:
        m.arc_band(c, t.R - 0.002, t.R + rise, a0, a1, y0, y1, mat, steps=steps)
        return
    b = bar / t.R
    m.arc_band(c, t.R - 0.002, t.R + rise, a1 - b, a1, y0, y1, mat, steps=2)
    m.arc_band(c, t.R - 0.002, t.R + rise, a0, a0 + b, y0, y1, mat, steps=2)
    m.arc_band(c, t.R - 0.002, t.R + rise, a0, a1, y0, y0 + bar, mat, steps=steps)
    m.arc_band(c, t.R - 0.002, t.R + rise, a0, a1, y1 - bar, y1, mat, steps=steps)


def label_geometry(t):
    """Rozměry a polohy nálepek na bocích: {jméno: (u střed, dz střed od osy, šířka, výška)}."""
    wv = t.wv
    hv = wv / 1.6
    wt = 0.96 * wv
    ht = wt / 8.0
    wp = 0.13 + 0.08 * t.R
    hp = wp / 1.6
    u_left = 0.5 * (t.u_a + t.u_b)
    dz_v = 0.02
    dz_t = dz_v + hv / 2 + 0.03 + ht / 2
    dz_p = dz_v - hv / 2 - 0.03 - hp / 2
    return {
        "volL": (u_left, dz_v, wv, hv), "text": (u_left, dz_t, wt, ht), "plate": (u_left, dz_p, wp, hp),
        "volR": (t.u_a + wv / 2, dz_v, wv, hv),
    }


def _shell(t, shell):
    shell.lathe(_profile(t), t.center, V(0, 1, 0), PE, seg=t.seg, ref=V(0, 0, 1))
    lab = label_geometry(t)
    for key in ("volL", "volR"):
        u, dz, w, h = lab[key]
        a = math.pi / 2 + math.asin(dz / t.R)
        _panel(t, shell, a if key == "volL" else -a, u, w + 0.03, h + 0.03)
    u, dz, w, h = lab["text"]
    a = math.pi / 2 + math.asin(dz / t.R)
    _panel(t, shell, a, u, w + 0.024, h + 0.024, bar=0.007, rise=0.004)
    u, dz, w, h = lab["plate"]
    a = math.pi / 2 + math.asin(dz / t.R)
    _panel(t, shell, a, u, w + 0.03, h + 0.03, bar=0.007, rise=0.003)
    _panel(t, shell, a, u, w + 0.012, h + 0.012, solid=True, rise=0.0045)
    ur = lab["volR"][0]
    dz_o = -0.42 * t.R
    ho = 0.96 * t.wv / 4.57
    a = math.pi / 2 + math.asin(dz_o / t.R)
    _panel(t, shell, -a, ur, 0.96 * t.wv + 0.022, ho + 0.022, bar=0.006, rise=0.0035)


def _manway(t, shell, fit, lid, u):
    rn = t.rn
    y = t.y0 + u
    top = t.top_z
    shell.lathe([(rn, -0.06), (rn, 0.020), (rn + 0.014, 0.022), (rn + 0.014, 0.036), (rn - 0.008, 0.038), (0.0, 0.038)],
                V(0, y, top), V(0, 0, 1), PE, seg=40, hard=(1, 2, 3, 4))
    z0 = top + 0.038
    rl = rn + 0.012
    lid.lathe([(0, 0), (rl, 0), (rl, 0.014), (rl - 0.008, 0.022), (rl * 0.70, 0.028), (0, 0.030)],
              V(0, y, z0), V(0, 0, 1), BLACK, seg=40, hard=(1, 2, 3))
    for i in range(8):
        a = TAU * (i + 0.5) / 8
        lid.obox((rl * 0.55, 0.012, 0.008), frame(V(rl * 0.36 * math.cos(a), y + rl * 0.36 * math.sin(a), z0 + 0.030),
                                                  V(0, 0, 1), V(math.cos(a), math.sin(a), 0)), BLACK)
    fit.torus(V(0, y, z0 + 0.001), V(0, 0, 1), rl - 0.006, 0.0035, RUBBER, seg=40, rseg=4)
    angles = (150, 210, 270, 330, 30) if rn >= 0.15 else (180, 270, 0)
    for deg in angles:
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        rr = rn + 0.036
        radial = V(c, s, 0)
        fit.obox((0.036, 0.020, 0.026), frame(V((rn + 0.026) * c, y + (rn + 0.026) * s, top + 0.024), V(0, 0, 1), radial),
                 STEEL)
        lid.obox((0.034, 0.024, 0.010), frame(V((rl + 0.020) * c, y + (rl + 0.020) * s, z0 + 0.012), V(0, 0, 1), radial),
                 BLACK)
        fit.cyl(V(rr * c, y + rr * s, top + 0.012), V(rr * c, y + rr * s, z0 + 0.030), 0.0055, STEEL, seg=8)
        fit.hex(V(rr * c, y + rr * s, z0 + 0.024), V(0, 0, 1), 0.0115, 0.010, STEEL)
        fit.obox((0.040, 0.008, 0.006), frame(V(rr * c, y + rr * s, z0 + 0.038), V(0, 0, 1), V(-s, c, 0)), STEEL)
    for sx in (-1, 1):
        kx = sx * rl * 0.55
        fit.cyl(V(kx - 0.022, y + rl + 0.010, z0 + 0.008), V(kx + 0.022, y + rl + 0.010, z0 + 0.008), 0.010, STEEL, seg=10)
        fit.box(kx - 0.022, kx + 0.022, y + rn + 0.006, y + rl + 0.012, top + 0.030, top + 0.036, STEEL)
        lid.box(kx - 0.022, kx + 0.022, y + rl - 0.012, y + rl + 0.012, z0, z0 + 0.008, BLACK)
    hg = 0.36 * rl
    hx = 0.14 * rl
    for sx in (-1, 1):
        fit.cyl(V(sx * hg, y - hx, z0 + 0.028), V(sx * hg, y - hx, z0 + 0.052), 0.007, STEEL, seg=8)
    fit.cyl(V(-hg, y - hx, z0 + 0.052), V(hg, y - hx, z0 + 0.052), 0.008, STEEL, seg=10)


def _vent(t, fit, a_deg, u):
    p, n = t.wall(a_deg, u)
    _vent_at(fit, p, n, t.kf)


def _vent_at(fit, p, n, s):
    stack(fit, p, n, [(-0.012, 0.014, 0.034 * s, 0.034 * s, PE, 18), (0.014, 0.038, 0.011 * s, 0.011 * s, BLACK, 10),
                      (0.038, 0.046, 0.019 * s, 0.017 * s, STEEL, 6)])
    fit.lathe([(0, 0), (0.028 * s, 0), (0.028 * s, 0.008 * s), (0.021 * s, 0.017 * s), (0, 0.020 * s)],
              p + n * 0.046, n, BLACK, seg=18, hard=(1, 2))


def _relief(t, fit, a_deg, u):
    p, n = t.wall(a_deg, u)
    _relief_at(fit, p, n, t.tangent(a_deg), t.kf)


def _relief_at(fit, p, n, tg, s):
    stack(fit, p, n, [(-0.012, 0.016, 0.038 * s, 0.038 * s, PE, 20), (0.016, 0.026, 0.034 * s, 0.034 * s, STEEL, 6),
                      (0.026, 0.050, 0.030 * s, 0.030 * s, BRASS, 6), (0.050, 0.070, 0.021 * s, 0.021 * s, BRASS, 14),
                      (0.070, 0.148, 0.027 * s, 0.024 * s, "SDT_PaintRed", 16), (0.148, 0.158, 0.019 * s, 0.019 * s, STEEL, 6)])
    for k in range(3):
        fit.torus(p + n * (0.082 + 0.024 * k), n, 0.0265 * s, 0.0025, "SDT_PaintRed", seg=16, rseg=4)
    o = p + n * 0.060
    fit.cyl(o, o + tg * 0.052 * s, 0.013 * s, BRASS, seg=10)
    fit.cyl(o + tg * 0.052 * s, o + tg * 0.052 * s - n * 0.04 * s, 0.013 * s, BRASS, seg=10)
    fit.sphere(o + tg * 0.052 * s, 0.017 * s, BRASS, seg=12, rings=6)
    top = p + n * 0.158
    fit.obox((0.075 * s, 0.008, 0.008), frame(top + tg * 0.03 * s + n * 0.010, tg, V(0, 1, 0)), STEEL)
    fit.sphere(top + tg * 0.068 * s + n * 0.010, 0.010, "SDT_PaintRed", seg=10, rings=6)


# ------------------------------------------------------------------------------------------------- výpusť

def _outlet(t, fit):
    """Příruba, kohout a hadicový nátrubek na předním dně, konec nátrubku OUTLET_TIP_LEN před MAIN_DRAIN."""
    d = Vector(MAIN_DRAIN)
    fwd = Vector(MAIN_DRAIN_DIR).normalized()
    ys = t.front_y_in(d)
    tf = d.y - ys + 0.003                                # zadní líc příruby: před nejpředenějším bodem podložky
    tv = max(0.052, tf + 0.012 + 0.014)
    fit.lathe([(0.062, tf - 0.045), (0.040, tf + 0.004), (0.036, tf + 0.010)], d, fwd, PE, seg=24)
    fit.flange(d + fwd * tf, fwd, 0.05, 0.012, STEEL, bolts=6, bolt_r=0.039, bolt_size=0.0055)
    fit.cyl(d + fwd * (tf + 0.012), d + fwd * tv, 0.026, STEEL, seg=14)
    v1 = d + fwd * 0.122
    fit.ball_valve(d + fwd * tv, v1, 0.026, V(0, 0, 1), "SDT_PaintRed", lever_len=0.12)
    fit.cyl(v1, v1 + fwd * 0.020, 0.030, BRASS, seg=6)
    fit.hose_tail(v1 + fwd * 0.020, d + fwd * OUTLET_TIP_LEN, 0.0255)


def _rear_drain(t, fit):
    """Vypouštěcí kohout na pravém boku u zadního dna (vzadu je bedna): boss, příruba, kohout, zátka na řetízku."""
    p, n = t.wall(-72, t.Ln - t.hd - 0.06)
    _rear_drain_at(fit, p, n, t.tangent(-72))


def _rear_drain_at(fit, p, n, tg, ks=1.0):
    """ks zkracuje armaturu po normále n (hranatá nádrž má pravý bok těsně u okraje paluby)."""
    def q(d):
        return p + n * (d * ks)

    stack(fit, p, n, [(-0.03, 0.016, 0.036, 0.036, PE, 20)])
    fit.flange(q(0.014), n, 0.05, 0.012, STEEL, bolts=6, bolt_r=0.039, bolt_size=0.0055)
    fit.cyl(q(0.026), q(0.046), 0.024, STEEL, seg=14)
    fit.ball_valve(q(0.046), q(0.112), 0.022, V(0, 1, 0), "SDT_ValveBlue", lever_len=0.10)
    fit.cyl(q(0.112), q(0.130), 0.026, BRASS, seg=6)
    fit.cyl(q(0.130), q(0.160), 0.024, STEEL, seg=14)
    fit.lathe([(0, 0), (0.028, 0), (0.028, 0.026), (0.020, 0.030), (0, 0.030)], q(0.160), n, BRASS, seg=16, hard=(1, 2))
    fit.hex(q(0.190), n, 0.014, 0.010, BRASS)
    for k in range(4):
        fit.torus(q(0.140) + V(0, 0.020, 0) + tg * (-0.012 * k) - n * 0.020 * k, V(0, 1, 0) if k % 2 == 0 else tg,
                  0.006, 0.0018, STEEL, seg=10, rseg=4)


# ------------------------------------------------------------------------------------------------- rám

def _frame(t, m):
    R, z, zc = t.R, t.z, t.zc
    sw = 0.9 * R
    xr = 0.86 * R
    y_a, y_b = t.y0 + 0.035, t.y0 + t.Ln - 0.035
    ys_list = (t.y0 + t.saddle_u, t.y0 + t.Ln - t.saddle_u)
    zg = zc - 0.62 * R
    for sx in (-1, 1):
        m.box(sx * xr - 0.03, sx * xr + 0.03, y_a, y_b, z, z + 0.06, FRAME_MAT, bevel=0.005)
        m.box(sx * xr - 0.024, sx * xr + 0.024, y_a + 0.01, y_b - 0.01, z + 0.06, z + 0.064, RUBBER)
        for y, ye in ((y_a, -1), (y_b, 1)):
            m.box(sx * xr - 0.06, sx * xr + 0.06, y - ye * 0.03 - 0.05, y - ye * 0.03 + 0.05, z, z + 0.008, FRAME_MAT)
            for bx in (-1, 1):
                for by in (-1, 1):
                    m.hex(V(sx * xr + bx * 0.042, y - ye * 0.03 + by * 0.032, z + 0.008), V(0, 0, 1), 0.0085, 0.008, STEEL)
    for y, ye in ((y_a, -1), (y_b, 1)):
        m.cyl(V(-xr, y + ye * 0.0, z + 0.036), V(xr, y + ye * 0.0, z + 0.036), 0.021, FRAME_MAT, seg=12)
        for sx in (-1, 1):
            m.cyl(V(sx * xr, y, z + 0.036), V(sx * (xr + 0.048), y, z + 0.036), 0.028, RUBBER, seg=12)
            m.sphere(V(sx * (xr + 0.048), y, z + 0.036), 0.028, RUBBER, seg=12, rings=6)
    for i, ys in enumerate(ys_list):
        w = 0.055
        m.box(-sw, sw, ys - w, ys + w, z, z + 0.008, FRAME_MAT)
        for sy in (-1, 1):
            m.box(-sw, sw, ys + sy * w - 0.003, ys + sy * w + 0.003, z, z + 0.034, FRAME_MAT)
        for wx in (-0.75 * R, -0.375 * R, 0.0, 0.375 * R, 0.75 * R):
            zt = zc - math.sqrt((R + 0.006) ** 2 - wx ** 2)
            m.box(wx - 0.004, wx + 0.004, ys - 0.045, ys + 0.045, z + 0.008, zt + 0.001, FRAME_MAT)
        m.arc_band(t.center, R + 0.0006, R + 0.0034, math.radians(-54), math.radians(54), ys - 0.05, ys + 0.05, RUBBER)
        m.arc_band(t.center, R + 0.0034, R + 0.0094, math.radians(-56), math.radians(56), ys - 0.05, ys + 0.05, FRAME_MAT)
        for bx in (-0.84 * R, 0.84 * R):
            for by in (-1, 1):
                m.hex(V(bx, ys + by * 0.028, z + 0.008), V(0, 0, 1), 0.0085, 0.008, STEEL)
        for sx in (-1, 1):
            xg = sx * (xr + 0.036)
            m.box(xg - 0.004, xg + 0.004, ys - 0.04, ys + 0.04, z + 0.06, zg, FRAME_MAT, bevel=0.002)
            m.box(xg - 0.004, xg - sx * 0.030, ys - 0.04, ys + 0.04, zg - 0.008, zg, FRAME_MAT, bevel=0.002)
    for sx in (-1, 1):
        xg = sx * (xr + 0.036)
        m.cyl(V(xg, ys_list[0], zg + 0.012), V(xg, ys_list[1], zg + 0.012), 0.013, FRAME_MAT, seg=10)
        for ys in ys_list:
            m.sphere(V(xg, ys, zg + 0.012), 0.013, FRAME_MAT, seg=10, rings=5)
        for y, ye in ((y_a, -1), (y_b, 1)):
            xo = sx * (xr + 0.030)
            m.box(xo, xo + sx * 0.010, y - 0.03, y + 0.03, z + 0.008, z + 0.052, FRAME_MAT)
            m.torus(V(xo + sx * 0.012, y, z + 0.040), V(1, 0, 0), 0.019, 0.005, STEEL, seg=16, rseg=6)


def _step(t, m):
    """Žebřík zleva vzadu na horní hrdlo (největší nádrž): dva profily, příčky, distanční ramena k nádrži."""
    R, z, zc = t.R, t.z, t.zc
    xl = R + 0.11
    ua, ub = t.Ln - 0.47, t.Ln - 0.19
    stiles = (t.y0 + ua, t.y0 + ub)
    z0, z1 = z + 0.06, zc + 0.36 * R + 0.36
    for y in stiles:
        m.box(xl - 0.018, xl + 0.018, y - 0.015, y + 0.015, z0, z1, FRAME_MAT, bevel=0.003)
        m.box(xl - 0.055, xl + 0.055, y - 0.05, y + 0.05, z, z + 0.008, FRAME_MAT)
        for a in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            m.hex(V(xl + a[0] * 0.038, y + a[1] * 0.032, z + 0.008), V(0, 0, 1), 0.0085, 0.008, STEEL)
    for i in range(4):
        zz = z + 0.30 + i * 0.28
        m.cyl(V(xl, stiles[0], zz), V(xl, stiles[1], zz), 0.013, STEEL, seg=10)
        for k in range(1, 6):
            m.box(xl - 0.02, xl + 0.02, stiles[0] + k * (stiles[1] - stiles[0]) / 6 - 0.004,
                  stiles[0] + k * (stiles[1] - stiles[0]) / 6 + 0.004, zz + 0.010, zz + 0.012, STEEL)
    for y in stiles:
        for zz in (z + 0.62, zc + 0.30 * R):
            xs = math.sqrt(max(R * R - (zz - zc) ** 2, 0.0))
            m.cyl(V(xl, y, zz), V(xs + 0.004, y, zz), 0.011, FRAME_MAT, seg=8)
            m.cyl(V(xs - 0.006, y, zz), V(xs + 0.010, y, zz), 0.024, PE, seg=12)
    for y in stiles:
        m.cyl(V(xl, y, z1), V(xl - 0.16, y, z1 + 0.12), 0.011, FRAME_MAT, seg=8)
    m.cyl(V(xl - 0.16, stiles[0], z1 + 0.12), V(xl - 0.16, stiles[1], z1 + 0.12), 0.012, FRAME_MAT, seg=8)


def _top_handle(t, m, u):
    """Madlo na horní ploše u hrdla: obrácené U z trubky, patky přišroubované k plášti."""
    y = t.y0 + u
    top = t.zc + t.R
    for sx in (-1, 1):
        m.cyl(V(sx * 0.13, y, top - 0.005), V(sx * 0.13, y, top + 0.10), 0.011, FRAME_MAT, seg=10)
        m.cyl(V(sx * 0.13, y, top - 0.005), V(sx * 0.13, y, top + 0.004), 0.030, STEEL, seg=12)
        m.sphere(V(sx * 0.13, y, top + 0.10), 0.011, FRAME_MAT, seg=8, rings=4)
    m.cyl(V(-0.13, y, top + 0.10), V(0.13, y, top + 0.10), 0.011, FRAME_MAT, seg=10)


# ------------------------------------------------------------------------------------------------- nálepky

def _conform(name, shell, t, side, u, dz, w, h, region):
    """Nálepka přitisknutá na bok (side +1 = levý, -1 = pravý) ve výšce dz nad osou."""
    x = side * math.sqrt(max(t.R ** 2 - dz ** 2, 1e-6))
    n = V(x, 0, dz).normalized()
    rows = max(3, int(h / 0.02))
    cols = max(6, int(w / 0.03))
    return P.conform_decal(name, shell, V(x, t.y0 + u, t.zc + dz), n, V(0, 0, 1), w, h, region, offset=0.0022, cols=cols,
                           rows=rows)


def decal_sub_uv(obj, region, sub):
    """Přepíše UV nálepky na výřez oblasti (podíly od levého horního rohu)."""
    u0, v0, u1, v1 = L.uv_rect(region, sub)
    me = obj.data
    layer = me.uv_layers[0]
    ru0, rv0, ru1, rv1 = L.uv_rect(region)
    for loop in me.loops:
        uv = layer.data[loop.index].uv
        s = (uv[0] - ru0) / (ru1 - ru0)
        v = (uv[1] - rv0) / (rv1 - rv0)
        layer.data[loop.index].uv = (u0 + (u1 - u0) * s, v0 + (v1 - v0) * v)


def _decals(t, shell, prefix):
    lab = label_geometry(t)
    out = []
    u, dz, w, h = lab["volL"]
    out.append(_conform(f"{prefix}_VolL", shell, t, 1, u, dz, w, h, f"tankVol{t.size}"))
    u, dz, w, h = lab["volR"]
    out.append(_conform(f"{prefix}_VolR", shell, t, -1, u, dz, w, h, f"tankVol{t.size}"))
    u, dz, w, h = lab["text"]
    out.append(_conform(f"{prefix}_Text", shell, t, 1, u, dz, w, h, "tankText"))
    u, dz, w, h = lab["plate"]
    if t.size in L.TANK_PLATE_SUB:
        plate = _conform(f"{prefix}_Plate", shell, t, 1, u, dz, w, h, "tankPlate")
        decal_sub_uv(plate, "tankPlate", L.TANK_PLATE_SUB[t.size])
    else:
        plate = _conform(f"{prefix}_Plate", shell, t, 1, u, dz, w, h, f"tankPlate{t.size}")
    out.append(plate)
    ur = lab["volR"][0]
    wo = 0.96 * t.wv
    ho = wo / 4.57
    out.append(_conform(f"{prefix}_Outlet", shell, t, -1, ur, -0.42 * t.R, wo, ho, "tankOutlet"))
    s = 0.07 if t.R < 0.4 else 0.09
    for i in range(3):
        p, n = t.wall(128.0, t.mid + (i - 1) * (s + 0.012))
        d = P.conform_decal(f"{prefix}_Warn{i}", shell, p, n, t.tangent(128.0), s, s, "tankWarn", offset=0.0022,
                            cols=5, rows=5)
        decal_sub_uv(d, "tankWarn", L.TANK_WARN_SUB[i])
        out.append(d)
    groove_end = t.Ln - t.groove_u + 0.035
    wa = min(0.13, (t.Ln - t.hd) - groove_end - 0.02)
    out.append(_conform(f"{prefix}_Drain", shell, t, -1, 0.5 * (groove_end + t.Ln - t.hd), -0.20 * t.R, wa, wa / 4.57,
                        "tankArrow"))
    return out


# ------------------------------------------------------------------------------------------------- hranatá nádrž

class BoxTank:
    """Hranatá PE nádrž (3000, 5000 l): kvádr se zaoblenými hranami, přední stěna na MAIN_TANK_Y_FRONT, spodek BOX_GAP nad
    palubou. Rozměry z decal_layout.BOX_GEOM (šířka, výška, délka); stejné rozhraní jako Tank tam, kde ho sdílené díly čtou."""

    def __init__(self, size, z):
        self.size = size
        self.W, self.H, self.Ln = L.BOX_GEOM[size]
        self.hw = self.W / 2
        self.z = z
        self.y0 = MAIN_TANK_Y_FRONT
        self.zb = z + BOX_GAP
        self.zt = self.zb + self.H
        self.zc = self.zb + self.H / 2
        self.top_z = self.zt
        self.mid = self.Ln / 2
        self.rn = BOX_MANWAY_R
        self.wv = 0.62                                    # šířka nálepky s objemem

    def front_y_in(self, d):
        return self.y0


def _rounded_box(m, x0, x1, y0, y1, z0, z1, mat, r):
    t = bmesh.new()
    bmesh.ops.create_cube(t, size=1.0, matrix=Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1.0)))
    bmesh.ops.bevel(t, geom=list(t.edges), offset=r, offset_type="OFFSET", segments=3, profile=0.5, affect="EDGES")
    m._absorb(t, Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), mat)


def _box_panel(t, m, side, y, z, w, h, bar=0.010, rise=0.005, solid=False):
    """Vylisovaný panel na bočním líci (side +1 = levý, -1 = pravý): obdélníkový lem nebo plná podložka."""
    xa, xb = side * (t.hw - 0.002), side * (t.hw + rise)
    y0, y1, z0, z1 = y - w / 2, y + w / 2, z - h / 2, z + h / 2
    if solid:
        m.box(xa, xb, y0, y1, z0, z1, PE)
        return
    m.box(xa, xb, y0, y1, z1 - bar, z1, PE)
    m.box(xa, xb, y0, y1, z0, z0 + bar, PE)
    m.box(xa, xb, y0, y0 + bar, z0, z1, PE)
    m.box(xa, xb, y1 - bar, y1, z0, z1, PE)


def box_label_geometry(t):
    """Rozměry a polohy nálepek na bocích hranaté nádrže: {jméno: (u střed, dz střed od osy, šířka, výška)}."""
    wv = t.wv
    hv = wv / 1.6
    wt = 0.96 * wv
    ht = wt / 8.0
    wp = 0.17
    hp = wp / 1.6
    dz_v = 0.10
    return {"vol": (t.mid, dz_v, wv, hv), "text": (t.mid, dz_v + hv / 2 + 0.03 + ht / 2, wt, ht),
            "plate": (t.mid, dz_v - hv / 2 - 0.03 - hp / 2, wp, hp)}


def _box_shell(t, shell):
    hw, zc = t.hw, t.zc
    _rounded_box(shell, -hw, hw, t.y0, t.y0 + t.Ln, t.zb, t.zt, PE, BOX_EDGE_R)
    ya, yb = t.y0 + 0.10, t.y0 + t.Ln - 0.10
    rib = BOX_RIBS * t.H / 2
    for dz in (rib, -rib):
        z0, z1 = zc + dz - 0.016, zc + dz + 0.016
        for s in (-1, 1):
            shell.box(s * (hw - 0.002), s * (hw + 0.007), ya, yb, z0, z1, PE, bevel=0.004)
        shell.box(-(hw - 0.10), hw - 0.10, t.y0 + 0.002, t.y0 - 0.007, z0, z1, PE, bevel=0.004)
        shell.box(-(hw - 0.10), hw - 0.10, t.y0 + t.Ln - 0.002, t.y0 + t.Ln + 0.007, z0, z1, PE, bevel=0.004)
    lab = box_label_geometry(t)
    u, dz, w, h = lab["vol"]
    for side in (1, -1):
        _box_panel(t, shell, side, t.y0 + u, zc + dz, w + 0.03, h + 0.03)
    u, dz, w, h = lab["text"]
    _box_panel(t, shell, 1, t.y0 + u, zc + dz, w + 0.024, h + 0.024, bar=0.007, rise=0.004)
    u, dz, w, h = lab["plate"]
    _box_panel(t, shell, 1, t.y0 + u, zc + dz, w + 0.03, h + 0.03, bar=0.007, rise=0.003)
    _box_panel(t, shell, 1, t.y0 + u, zc + dz, w + 0.012, h + 0.012, solid=True, rise=0.001)
    ho = 0.96 * t.wv / 4.57
    _box_panel(t, shell, -1, t.y0 + t.mid, zc - 0.25, 0.96 * t.wv + 0.022, ho + 0.022, bar=0.006, rise=0.0035)


def _box_frame(t, m, eyes=True):
    """Rám: příčníky na palubě, dva podélné nosníky pod nádrží, trubkové ochrany svislých hran, kotvicí oka a (eyes) ucha
    pro zdvih na horní ploše."""
    hw, z, zb = t.hw, t.z, t.zb
    zr = z + 0.03
    ya, yb = t.y0 + 0.02, t.y0 + t.Ln - 0.02
    for sx in (-1, 1):
        xr = sx * (hw - 0.32)
        m.box(xr - 0.045, xr + 0.045, ya, yb, zr, zb, FRAME_MAT, bevel=0.004)
    for u in (0.10, t.mid, t.Ln - 0.10):
        y = t.y0 + u
        m.box(-(hw - 0.05), hw - 0.05, y - 0.04, y + 0.04, z, zr, FRAME_MAT, bevel=0.004)
        for sx in (-1, 1):
            m.torus(V(sx * (hw - 0.05) + sx * 0.012, y, z + 0.040), V(1, 0, 0), 0.019, 0.005, STEEL, seg=16, rseg=6)
    r = BOX_EDGE_R
    zlo, zhi = zb + 0.10, t.zt - 0.10
    for sx in (-1, 1):
        for yf, e in ((t.y0, -1), (t.y0 + t.Ln, 1)):
            cx = sx * (hw - r + r * 0.7071 + 0.010)
            cy = yf - e * r + e * (r * 0.7071 + 0.010)
            m.cyl(V(cx, cy, zlo), V(cx, cy, zhi), 0.012, FRAME_MAT, seg=10)
    for sx in (-1, 1) if eyes else ():
        for u in (0.20, t.Ln - 0.20):
            y = t.y0 + u
            x = sx * (hw - 0.22)
            m.box(x - 0.045, x + 0.045, y - 0.03, y + 0.03, t.zt, t.zt + 0.006, STEEL)
            m.torus(V(x, y, t.zt + 0.014), V(0, 1, 0), 0.026, 0.006, STEEL, seg=16, rseg=6)


def _box_fittings(t, fit):
    x = -0.55
    _vent_at(fit, V(x, t.y0 + t.mid + 0.40, t.zt), V(0, 0, 1), 1.0)
    _relief_at(fit, V(x, t.y0 + t.mid - 0.30, t.zt), V(0, 0, 1), V(1, 0, 0), 1.0)
    _rear_drain_at(fit, V(-t.hw, t.y0 + t.Ln - 0.14, t.zb + 0.14), V(-1, 0, 0), V(0, 0, -1), 0.62)


def _box_decals(t, prefix):
    lab = box_label_geometry(t)
    out = []

    def put(name, side, u, dz, w, h, region, sub=None, offset=0.0022):
        uax = V(0, side, 0)
        vax = V(0, 0, 1)
        c = V(side * t.hw, t.y0 + u, t.zc + dz)
        out.append(P.decal_quad(name, c - uax * w / 2 - vax * h / 2, uax, vax, w, h, region, sub=sub, offset=offset))

    u, dz, w, h = lab["vol"]
    put(f"{prefix}_VolL", 1, u, dz, w, h, f"tankVol{t.size}")
    put(f"{prefix}_VolR", -1, u, dz, w, h, f"tankVol{t.size}")
    u, dz, w, h = lab["text"]
    put(f"{prefix}_Text", 1, u, dz, w, h, "tankText")
    u, dz, w, h = lab["plate"]
    sub = L.TANK_PLATE_SUB.get(t.size)
    put(f"{prefix}_Plate", 1, u, dz, w, h, "tankPlate" if sub else f"tankPlate{t.size}", sub=sub, offset=0.0025)
    wo = 0.96 * t.wv
    put(f"{prefix}_Outlet", -1, t.mid, -0.25, wo, wo / 4.57, "tankOutlet")
    for i in range(3):
        put(f"{prefix}_Warn{i}", 1, 0.12 + 0.10 * i, 0.30, 0.08, 0.08, "tankWarn", sub=L.TANK_WARN_SUB[i])
    put(f"{prefix}_Drain", -1, t.Ln - 0.30, -0.43, 0.13, 0.13 / 4.57, "tankArrow")
    return out


def build_box_tank(size, z):
    t = BoxTank(size, z)
    name = f"Tank_Main{size}"
    shell = Mesh(name)
    fit = Mesh(f"{name}_Fittings")
    lid = Mesh(f"{name}_Lid")
    frm = Mesh(f"{name}_Frame")
    _box_shell(t, shell)
    _manway(t, shell, fit, lid, t.mid)
    _box_fittings(t, fit)
    _outlet(t, fit)
    _box_frame(t, frm)
    meshes = [m.finish() for m in (shell, fit, lid, frm)]
    bpy.context.view_layer.update()
    return P.group(f"tankMain{size}", meshes + _box_decals(t, name))


def tank_envelope(size):
    """(poloviční šířka, délka, výška horní hrany nad palubou) obalového kvádru nádrže dané velikosti; kolize a plnicí uzel."""
    if size in L.BOX_GEOM:
        w, h, ln = L.BOX_GEOM[size]
        return w / 2, ln, BOX_GAP + h
    r, ln = L.TANK_GEOM[size]
    return r, ln, GAP + 2 * r


# ------------------------------------------------------------------------------------------------- sestavení

def build_main_tank(size, z):
    if size in L.BOX_GEOM:
        return build_box_tank(size, z)
    t = Tank(size, z)
    name = f"Tank_Main{size}"
    shell = Mesh(name)
    fit = Mesh(f"{name}_Fittings")
    lid = Mesh(f"{name}_Lid")
    frm = Mesh(f"{name}_Frame")
    _shell(t, shell)
    _manway(t, shell, fit, lid, t.mid)
    _vent(t, fit, 152, t.mid + 0.16 * t.kf)
    _relief(t, fit, 212, t.mid - 0.12 * t.kf)
    _outlet(t, fit)
    _rear_drain(t, fit)
    _frame(t, frm)
    if size == 1500:
        _step(t, frm)
        _top_handle(t, frm, t.mid + t.rn + 0.17)
    meshes = [shell.finish(), fit.finish(), lid.finish(), frm.finish()]
    bpy.context.view_layer.update()
    decals = _decals(t, meshes[0], name)
    return P.group(f"tankMain{size}", meshes + decals)


def build_main_tanks(z):
    """Postaví všechny velikosti (skupiny tankMain800 / 1000 / 1500 / 3000 / 5000, v i3d všechny viditelné)."""
    return {size: build_main_tank(size, z) for size in TANK_SIZES}
