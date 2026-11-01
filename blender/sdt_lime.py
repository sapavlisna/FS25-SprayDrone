"""Nádobka na koncentrát a jemné vápno u mixéru Maxu (jediná, bez volby v obchodě): větší bílý PE válec s kuželovým dnem na stejném
stojanu a se stejným výpustem jako indukční nádobka Middle (sdt_tanks.build_induction_tank), takže rozvod k mixéru zůstává. Na
pravém boku má hadicovou spojku Storz s kulovým kohoutem (otočná páka limeValveLever) pro hadici z mlýnkového vozíku, stupnici
po 50 l, žlutý pruh a plochu pro štítek „JEMNÉ VÁPNO“.
"""

import math

import sdt_parts as P
import sdt_tanks as T
from sdt_tanks import Mesh, V, frame

TAU = 2.0 * math.pi
LIME_R = 0.37
LIME_STAND_H = T.INDUCTION_STAND_H      # stejný výpust jako běžná indukční nádobka
LIME_CONE_H = 0.20
LIME_BODY_H = 0.75
PORT_DY = 0.0                           # spojka míří kolmo ke středu nádobky
PORT_DZ = 0.22                          # a tolik nad přechodem kužel-válec
PORT_REACH = 0.15                       # o kolik vyčnívá čelo spojky za plášť (na stranu -X)


def lime_ports(x, y, z, radius=LIME_R, stand_h=LIME_STAND_H, cone_h=LIME_CONE_H):
    """Čelo hadicové spojky (směr -X, tedy k pravému boku vleku) a středy ostatních míst."""
    zj = z + stand_h + cone_h
    return {"inlet": V(x - radius - PORT_REACH, y + PORT_DY, zj + PORT_DZ), "inlet_dir": V(-1, 0, 0),
            "outlet": T.induction_ports(x, y, z, radius, stand_h, cone_h)["hose_end"]}


def build_lime_vessel(prefix, x, y, z, radius=LIME_R, stand_h=LIME_STAND_H, cone_h=LIME_CONE_H, body_h=LIME_BODY_H):
    """Větší nádobka na jemné vápno se středem v (x, y) na palubě ve výšce z. Vrací {"top": výška víčka, **lime_ports}."""
    zb = z + stand_h
    zj = zb + cone_h
    zt = zj + body_h
    R = radius
    shell = Mesh(prefix)
    stand = Mesh(f"{prefix}_Stand")
    fit = Mesh(f"{prefix}_Fittings")
    lid = Mesh(f"{prefix}_Lid")

    def cz(zz):
        return V(x, y, zz)

    rn, rl = T.INDUCTION_NECK_R, T.INDUCTION_NECK_LIP
    prof = [(0.0, zb), (0.052, zb), (R, zj), (R + 0.004, zj + 0.012), (R, zj + 0.024),
            (R, zt - 0.100), (R - 0.006, zt - 0.092), (R - 0.006, zt - 0.070), (R, zt - 0.062),
            (R, zt - 0.030), (R - 0.010, zt - 0.012),
            (R - 0.018, zt), (R - 0.018, zt + 0.012), (R - 0.030, zt + 0.012),
            (R - 0.030, zt + 0.002), (0.150, zt), (rn + 0.022, zt), (rn, zt + 0.012),
            (rn, zt + 0.034), (rl, zt + 0.040), (rl, zt + 0.048),
            (rn - 0.012, zt + 0.048), (rn - 0.012, zt - 0.030), (0.0, zt - 0.030)]
    shell.lathe(prof, cz(0), V(0, 0, 1), "SDT_TankPE", seg=48, hard=(1, 11, 12, 13, 20, 21, 22))

    # výpust stejný jako u indukční nádobky (rozvod k mixéru se nemění)
    ports = T.induction_ports(x, y, z, R, stand_h, cone_h)
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

    # stojan: čtyři šikmé nohy, rám, knotové desky
    leg_foot, leg_top = 0.31, 0.28
    for sx in (-1, 1):
        for sy in (-1, 1):
            f = V(x + sx * leg_foot, y + sy * leg_foot, z + 0.004)
            t = V(x + sx * leg_top, y + sy * leg_top, zj)
            stand.cyl(f + V(0, 0, 0.004), t, 0.021, "SDT_Frame", square=True, ref=V(1, 0, 0))
            stand.box(f.x - 0.045, f.x + 0.045, f.y - 0.045, f.y + 0.045, z, z + 0.008, "SDT_Frame", bevel=0.004)
            stand.hex(f + V(0, 0, 0.004), V(0, 0, 1), 0.0095, 0.008, "SDT_Steel")
            dirv = V(sx, sy, 0).normalized()
            stand.obox((0.08, 0.045, 0.008), frame(t + dirv * (-0.012) + V(0, 0, 0.02), V(0, 0, 1), dirv), "SDT_Frame", bevel=0.002)
    zf = z + 0.22
    frac = (zf - (z + 0.004)) / (zj - (z + 0.004))
    half = leg_foot + (leg_top - leg_foot) * frac
    for sx in (-1, 1):
        stand.cyl(V(x + sx * half, y - half, zf), V(x + sx * half, y + half, zf), 0.017, "SDT_Frame", square=True, ref=V(1, 0, 0))
    stand.cyl(V(x - half, y - half, zf), V(x + half, y - half, zf), 0.017, "SDT_Frame", square=True, ref=V(0, 1, 0))
    for sx in (-1, 1):
        stand.cyl(V(x + sx * leg_foot, y - leg_foot, z + 0.05), V(x + sx * half, y - half, zf), 0.011, "SDT_Frame", seg=6)

    # stupnice na pravém boku (-X), vpředu od spojky
    T._induction_scale(fit, x, y, zb, R, cone_h, -0.12, litres_max=350, step=50, big=100)

    # plocha pro štítek vpředu a žlutý pruh kolem válce
    hw = 0.11
    xe = math.sqrt(R * R - hw * hw)
    fit.box(x - hw, x + hw, y - R - 0.003, y - xe + 0.004, zj + 0.20, zj + 0.42, "SDT_PaintWhite", bevel=0.003)
    fit.cyl(cz(zj + 0.56), cz(zj + 0.63), R + 0.003, "SDT_PaintYellow", seg=48)

    # hadicová spojka Storz na pravém boku (-X): patka, trubka, tělo s drápy, víčko
    zk = zj + PORT_DZ
    yk = y + PORT_DY
    ex = x - R
    fit.cyl(V(ex + 0.012, yk, zk), V(ex - 0.016, yk, zk), 0.060, "SDT_TankPE", seg=20)
    fit.flange(V(ex - 0.016, yk, zk), V(-1, 0, 0), 0.066, 0.012, "SDT_Steel", bolts=6, bolt_r=0.052, bolt_size=0.0055)
    valve_mid = fit.ball_valve(V(ex - 0.028, yk, zk), V(ex - 0.082, yk, zk), 0.034, V(0, 0, 1), "SDT_PaintRed", lever_len=None)
    T.valve_lever_node("limeValveLever", valve_mid, 0.034, V(0, 0, 1), V(0, 1, 0), 0.21, size=1.9)
    fit.cyl(V(ex - 0.082, yk, zk), V(ex - 0.120, yk, zk), 0.078, "SDT_Alu", seg=24)
    fit.cyl(V(ex - 0.120, yk, zk), V(ex - 0.150, yk, zk), 0.092, "SDT_Alu", seg=24)
    for k in range(3):
        a = TAU * k / 3 + math.pi / 2
        fit.obox((0.030, 0.026, 0.030),
                 frame(V(ex - 0.140, yk + 0.098 * math.cos(a), zk + 0.098 * math.sin(a)), V(1, 0, 0), V(0, 1, 0)), "SDT_Alu")
    fit.cyl(V(ex - 0.150, yk, zk), V(ex - 0.162, yk, zk), 0.085, "SDT_Rubber", seg=24)
    fit.cyl(V(ex - 0.162, yk, zk), V(ex - 0.178, yk, zk), 0.072, "SDT_PaintRed", seg=24)
    fit.torus(V(ex - 0.178, yk, zk), V(-1, 0, 0), 0.024, 0.0055, "SDT_Steel", seg=14, rseg=5)

    # plnicí hrdlo (pytle a kanystry do něj půjdou později): šroubovací víčko, těsnění, lanko
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
        lid.box(x + sx * 0.07 - 0.007, x + sx * 0.07 + 0.007, y - 0.013, y + 0.013, cap_z + 0.034, cap_z + 0.040, "SDT_TankBlack")
    lid.torus(V(x, y + 0.126, cap_z + 0.014), V(1, 0, 0), 0.008, 0.002, "SDT_Steel", seg=10, rseg=4)
    lid.cyl(V(x, y + 0.132, cap_z + 0.012), V(x, y + 0.155, cap_z - 0.004), 0.0035, "SDT_Rubber", seg=6)
    lid.cyl(V(x, y + 0.155, cap_z - 0.004), V(x, y + 0.165, zt + 0.010), 0.0035, "SDT_Rubber", seg=6)
    lid.box(x - 0.012, x + 0.012, y + 0.158, y + 0.176, zt, zt + 0.010, "SDT_Steel", bevel=0.002)
    fit.cyl(V(x, y - 0.200, zt), V(x, y - 0.200, zt + 0.020), 0.011, "SDT_TankBlack", seg=10)
    fit.cyl(V(x, y - 0.200, zt + 0.020), V(x, y - 0.200, zt + 0.028), 0.017, "SDT_TankBlack", r1=0.012, seg=12)
    shell.finish()
    stand.finish()
    fit.finish()
    lid.finish()
    out = lime_ports(x, y, z, R, stand_h, cone_h)
    out["top"] = cap_z + 0.050
    return out


def build_rear_hitch(y_rear=6.50, z_beam_bottom=0.745):
    """Kulový tažný věšák na zádi Maxu pro mlýnkový vozík. Dva příčníky 100×100 mm jsou šrouby přišroubované zespodu na spodní
    pásnice obou I-nosníků rámu (z_beam_bottom = jejich spodní hrana, osy nosníků x = ±0,45), mezi nimi je spojovací deska a pod nimi
    hlava věšáku s tažnou trubkou; trubku k příčníkům navíc tuhne trojúhelníkový žebro a dvě šikmé vzpěry od konců zadního příčníku.
    Koule 50 mm je ve výšce kulové spojky vozíku (z 0,58), na konzole vedle ní zásuvka 13 pólů a vzadu oko řetízku."""
    h = Mesh("Max_RearHitch")
    y0 = y_rear
    zg = z_beam_bottom
    zc0 = zg - 0.10                 # spodek příčníků
    zt0, zt1 = 0.43, 0.51           # tažná trubka
    yb = y0 + 0.46                  # střed koule za zádí
    xt = 0.045                      # půlšířka trubky
    for ya, yb_ in ((-0.40, -0.30), (-0.20, -0.10)):
        h.box(-0.56, 0.56, y0 + ya, y0 + yb_, zc0, zg, "SDT_Frame", bevel=0.004)
        for sx in (-1, 1):
            for xb in (0.40, 0.50):
                yc = y0 + (ya + yb_) / 2
                h.cyl(V(sx * xb, yc, zc0), V(sx * xb, yc, zc0 - 0.003), 0.019, "SDT_Steel", seg=14)
                h.hex(V(sx * xb, yc, zc0 - 0.003), V(0, 0, -1), 0.0115, 0.011, "SDT_Steel")
    h.box(-0.25, 0.25, y0 - 0.30, y0 - 0.20, zc0, zg, "SDT_Frame", bevel=0.004)
    h.box(-0.06, 0.06, y0 - 0.40, y0 - 0.10, zt0, zc0, "SDT_Frame", bevel=0.005)
    h.box(-xt, xt, y0 - 0.40, yb + 0.07, zt0, zt1, "SDT_Frame", bevel=0.006)
    h.plate([(0.0, 0.0), (0.34, 0.0), (0.0, zc0 - zt1)], V(-0.007, y0 - 0.10, zt1), V(0, 1, 0), V(0, 0, 1), 0.014, "SDT_Frame")
    for sx in (-1, 1):
        h.cyl(V(sx * 0.535, y0 - 0.15, zc0 + 0.02), V(sx * (xt + 0.004), y0 + 0.50, zt0 + 0.05), 0.022, "SDT_Frame", seg=8)
        h.plate([(0.0, 0.0), (0.18, 0.0), (0.18, 0.05), (0.12, 0.08), (0.0, 0.08)], V(sx * xt if sx > 0 else -xt, y0 + 0.38, zt0 + 0.01),
                V(0, 1, 0), V(0, 0, 1), sx * 0.012, "SDT_Frame")
    h.box(-0.075, 0.075, yb - 0.075, yb + 0.075, zt1, zt1 + 0.012, "SDT_Frame", bevel=0.004)
    for sx in (-1, 1):
        for sy in (-1, 1):
            h.hex(V(sx * 0.052, yb + sy * 0.052, zt1 + 0.012), V(0, 0, 1), 0.0085, 0.007, "SDT_Steel")
    h.cyl(V(0, yb, zt1 + 0.012), V(0, yb, zt1 + 0.045), 0.016, "SDT_Steel", seg=14)
    h.sphere(V(0, yb, zt1 + 0.070), 0.025, "SDT_Steel", seg=18, rings=9)
    h.cyl(V(0, yb, zt1 + 0.012), V(0, yb, zt1 + 0.026), 0.034, "SDT_Steel", seg=18)
    h.box(-0.02, 0.02, yb + 0.06, yb + 0.14, zt0 + 0.025, zt0 + 0.050, "SDT_Frame")
    h.torus(V(0.0, yb + 0.115, zt0 + 0.0375), V(0, 0, 1), 0.025, 0.007, "SDT_Steel", seg=16, rseg=6)
    h.box(xt - 0.002, 0.20, yb - 0.045, yb + 0.045, zt0 + 0.04, zt0 + 0.056, "SDT_Frame", bevel=0.003)
    h.plate([(0.0, 0.0), (0.12, 0.0), (0.0, -0.04)], V(xt, yb + 0.006, zt0 + 0.04), V(1, 0, 0), V(0, 0, 1), -0.012, "SDT_Frame")
    h.box(0.135, 0.19, yb - 0.025, yb + 0.025, zt0 + 0.056, zt0 + 0.126, "SDT_Plastic", bevel=0.006)
    h.cyl(V(0.1625, yb - 0.025, zt0 + 0.091), V(0.1625, yb - 0.040, zt0 + 0.091), 0.020, "SDT_Rubber", seg=14)
    h.finish()
    return {"ball": V(0, yb, zt1 + 0.070)}
