"""Mixér: míchací jednotka v sání čerpadla (nahrazuje T-kus, který spojoval hlavní a koncentrátovou nádrž).

Svislý elektromotor s žebrováním sedí přes lucernu se spojkou na míchací komoře. Komora je hliníkový blok
s příruboumi: voda z hlavní nádrže vstupuje zprava (+X), koncentrát zleva (-X) trychtýřovým přechodem, hotová směs
odchází dozadu (+Y) trubkou do sání čerpadla. Vpředu je průhledítko, výrobní štítek a dole vypouštěcí zátka.

Uzly pro skript: mixerMotor (spojka mezi motorem a komorou, počátek na ose motoru; točí se nebo chvěje kolem
svislé osy = osa Y v i3d) a mixerSoundNode (empty uprostřed motoru).
"""

import math

import bpy
from mathutils import Matrix, Vector

import sdt_parts as P
import sdt_tanks as T
from sdt_tanks import Mesh, V

TAU = 2.0 * math.pi
CH_X, CH_Y, CH_Z = 0.085, 0.070, 0.075   # půlrozměry míchací komory (CH_X = půlka bývalého T-kusu)
HOSE_REACH = T.TEE_RUN + 0.052           # konec nátrubku od středu (kam končí hadice)
LAN_BOT = CH_Z + 0.010                   # lucerna: nad víkem komory
LAN_TOP = 0.185
COUPLING_Z = 0.135                       # osa spojky nad středem komory
MOTOR_Z0 = 0.197                         # spodek motoru nad středem komory
MOTOR_Z1 = 0.395
MOTOR_R = 0.082


def mixer_ports(c):
    """Konce hadic a sání: voda zprava, koncentrát zleva, směs dozadu."""
    c = Vector(c)
    return {"water_end": c + V(HOSE_REACH, 0, 0), "conc_end": c - V(HOSE_REACH, 0, 0),
            "out": c + V(0, CH_Y + 0.012, 0)}


def build_mixer(c, deck_z, suction_elbow):
    """Mixér se středem komory v c (bývalé místo T-kusu). deck_z = horní plocha paluby (nohy), suction_elbow = koleno
    na sání čerpadla, kam vede trubka ze zadní stěny komory. Vrací {"motor": empty, "sound": empty}."""
    c = Vector(c)
    ax = V(1, 0, 0)
    up = V(0, 0, 1)
    body = Mesh("Mixer")
    spin = Mesh("Mixer_Coupling")

    # komora: hliníkový blok, přírubové plochy na třech stěnách, víko s přírubou pro lucernu
    body.box(c.x - CH_X, c.x + CH_X, c.y - CH_Y, c.y + CH_Y, c.z - CH_Z, c.z + CH_Z, "SDT_Alu", bevel=0.012)
    body.box(c.x - CH_X - 0.004, c.x + CH_X + 0.004, c.y - CH_Y - 0.004, c.y + CH_Y + 0.004, c.z - 0.004, c.z + 0.004,
             "SDT_Alu", bevel=0.002)
    for sx in (-1, 1):
        e = c + V(sx * CH_X, 0, 0)
        body.flange(e, V(sx, 0, 0), 0.052, 0.012, "SDT_Steel", bolts=4 if sx > 0 else 0, bolt_r=0.041,
                    bolt_size=0.0065, phase=math.radians(45))
    body.flange(c + V(0, CH_Y, 0), V(0, 1, 0), 0.052, 0.012, "SDT_Steel", bolts=4, bolt_r=0.041, bolt_size=0.0065,
                phase=math.radians(45))
    body.flange(c + V(0, 0, CH_Z), up, 0.075, 0.010, "SDT_Steel", bolts=6, bolt_r=0.060, bolt_size=0.006)

    # voda z hlavní nádrže zprava: hadicový nátrubek se sponou
    e = c + V(CH_X + 0.012, 0, 0)
    body.hose_tail(e, c + V(HOSE_REACH + 0.010, 0, 0), 0.0255)
    body.clamp(c + V(HOSE_REACH - 0.010, 0, 0), ax, 0.0255)

    # koncentrát zleva: trychtýřový přechod (široká ústa u komory, červený pásek), pak nátrubek se sponou
    e = c - V(CH_X + 0.012, 0, 0)
    body.cyl(e, e - V(0.034, 0, 0), 0.068, "SDT_Steel", r1=0.0255, seg=28)
    body.cyl(e - V(0.002, 0, 0), e - V(0.010, 0, 0), 0.0695, "SDT_PaintRed", r1=0.0665, seg=28)
    body.hose_tail(e - V(0.034, 0, 0), c - V(HOSE_REACH + 0.010, 0, 0), 0.0255)
    body.clamp(c - V(HOSE_REACH - 0.010, 0, 0), ax, 0.0255)

    # výstup dozadu do sání čerpadla
    o = c + V(0, CH_Y + 0.012, 0)
    body.cyl(o, Vector(suction_elbow), 0.031, "SDT_Steel", seg=18)

    # průhledítko vpředu: přírubka, tmavé sklo, čtyři šrouby
    sg = c + V(0, -CH_Y, 0.018)
    fwd = V(0, -1, 0)
    body.cyl(sg, sg + fwd * 0.006, 0.030, "SDT_Screen", seg=24)
    body.torus(sg + fwd * 0.005, fwd, 0.033, 0.005, "SDT_Steel", seg=24, rseg=6)
    body.bolt_circle(sg + fwd * 0.009, fwd, 0.033, 4, 0.0045, 0.004, "SDT_Steel", phase=math.radians(45))

    # výrobní štítek a vypouštěcí zátka
    body.box(c.x - 0.052, c.x + 0.052, c.y - CH_Y - 0.0025, c.y - CH_Y, c.z - 0.058, c.z - 0.030, "SDT_Alu")
    for sx in (-1, 1):
        body.hex(V(c.x + sx * 0.045, c.y - CH_Y - 0.0025, c.z - 0.044), fwd, 0.0035, 0.002, "SDT_Steel")
    body.cyl(c - V(0, 0, CH_Z), c - V(0, 0, CH_Z + 0.020), 0.013, "SDT_Brass", seg=6)

    # rám: deska pod komorou, čtyři nohy s patkami a kříž mezi nimi
    bz = c.z - CH_Z
    body.box(c.x - 0.095, c.x + 0.095, c.y - 0.085, c.y + 0.085, bz - 0.010, bz, "SDT_Frame", bevel=0.003)
    zf = deck_z + 0.008
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = c.x + sx * 0.070, c.y + sy * 0.055
            body.cyl(V(lx, ly, zf), V(lx, ly, bz - 0.010), 0.013, "SDT_Frame", square=True, ref=V(1, 0, 0))
            body.box(lx - 0.035, lx + 0.035, ly - 0.035, ly + 0.035, deck_z, zf, "SDT_Frame", bevel=0.003)
            body.hex(V(lx, ly, zf), up, 0.007, 0.006, "SDT_Steel")
    zx = deck_z + 0.16
    for sy in (-1, 1):
        body.cyl(V(c.x - 0.070, c.y + sy * 0.055, zx), V(c.x + 0.070, c.y + sy * 0.055, zx), 0.010, "SDT_Frame",
                 square=True, ref=V(0, 0, 1))
    for sx in (-1, 1):
        body.cyl(V(c.x + sx * 0.070, c.y - 0.055, zx), V(c.x + sx * 0.070, c.y + 0.055, zx), 0.010, "SDT_Frame",
                 square=True, ref=V(1, 0, 0))

    # lucerna: čtyři sloupky a přechodová deska pod motorem
    for k in range(4):
        a = math.radians(45 + 90 * k)
        p = V(c.x + 0.064 * math.cos(a), c.y + 0.064 * math.sin(a), 0)
        body.cyl(V(p.x, p.y, c.z + LAN_BOT), V(p.x, p.y, c.z + LAN_TOP), 0.011, "SDT_Alu", seg=8)
    body.cyl(c + V(0, 0, LAN_TOP), c + V(0, 0, LAN_TOP + 0.012), 0.098, "SDT_Alu", seg=32)
    body.bolt_circle(c + V(0, 0, LAN_TOP + 0.012), up, 0.082, 6, 0.0065, 0.006, "SDT_Steel")

    # motor: přední štít, tělo, žebra, štítek, kryt ventilátoru, svorkovnice s vývodkou, oko
    mz0, mz1 = c.z + MOTOR_Z0, c.z + MOTOR_Z1
    body.cyl(V(c.x, c.y, mz0), V(c.x, c.y, mz0 + 0.022), 0.094, "SDT_PumpBlue", seg=32)
    body.cyl(V(c.x, c.y, mz0 + 0.022), V(c.x, c.y, mz1), MOTOR_R, "SDT_PumpBlue", seg=32)
    body.fins(V(c.x, c.y, c.z), up, MOTOR_R - 0.004, 0.100, MOTOR_Z0 + 0.030, MOTOR_Z1 - 0.045, 28, 0.0045,
              "SDT_PumpBlue")
    body.cyl(V(c.x, c.y, mz1 - 0.040), V(c.x, c.y, mz1 + 0.004), 0.088, "SDT_PumpBlue", seg=32)
    body.cyl(V(c.x, c.y, mz1 + 0.004), V(c.x, c.y, mz1 + 0.044), 0.086, "SDT_TankBlack", r1=0.068, seg=32)
    for k in range(8):
        a = TAU * k / 8
        r = V(math.cos(a), math.sin(a), 0)
        body.obox((0.016, 0.006, 0.030), Matrix.Translation(V(c.x, c.y, mz1 + 0.024) + r * 0.077)
                  @ Matrix.Rotation(a, 4, "Z"), "SDT_Steel")
    body.torus(V(c.x, c.y, mz1 + 0.052), ax, 0.017, 0.0055, "SDT_Steel", seg=14, rseg=5)
    body.cyl(V(c.x, c.y, mz1 + 0.040), V(c.x, c.y, mz1 + 0.052), 0.020, "SDT_Steel", seg=10)
    body.box(c.x - 0.0905, c.x - 0.0800, c.y - 0.030, c.y + 0.030, mz1 - 0.030, mz1 - 0.006, "SDT_Alu")
    tb_y0 = c.y + MOTOR_R - 0.006
    body.box(c.x - 0.038, c.x + 0.038, tb_y0, tb_y0 + 0.052, c.z + 0.240, c.z + 0.312, "SDT_PumpBlue", bevel=0.004)
    body.box(c.x - 0.030, c.x + 0.030, tb_y0 + 0.052, tb_y0 + 0.062, c.z + 0.248, c.z + 0.304, "SDT_PumpBlue",
             bevel=0.003)
    for dx in (-1, 1):
        for dz in (-1, 1):
            body.hex(V(c.x + dx * 0.022, tb_y0 + 0.062, c.z + 0.276 + dz * 0.020), V(0, 1, 0), 0.0045, 0.003,
                     "SDT_Steel")
    body.cyl(V(c.x, tb_y0 + 0.052, c.z + 0.276), V(c.x, tb_y0 + 0.078, c.z + 0.276), 0.014, "SDT_Plastic", seg=10)
    cx = c.x + 0.055
    cy = tb_y0 + 0.110
    body.cyl(V(c.x, tb_y0 + 0.078, c.z + 0.276), V(c.x, cy, c.z + 0.276), 0.009, "SDT_HoseBlack", seg=8)
    body.cyl(V(c.x, cy, c.z + 0.276), V(cx, cy, c.z + 0.276), 0.009, "SDT_HoseBlack", seg=8)
    body.sphere(V(cx, cy, c.z + 0.276), 0.009, "SDT_HoseBlack", seg=8, rings=4)
    body.cyl(V(cx, cy, c.z + 0.276), V(cx, cy, deck_z + 0.03), 0.009, "SDT_HoseBlack", seg=8)
    body.box(cx - 0.015, cx + 0.015, cy - 0.012, cy + 0.012, deck_z + 0.008, deck_z + 0.036, "SDT_Plastic", bevel=0.003)

    # spojka (točivá / chvějící se část): dvě náboje se šroubkem a gumová hvězdice; osa spojky = osa motoru
    pivot = c + V(0, 0, COUPLING_Z)
    spin.cyl(pivot + V(0, 0, -0.050), pivot + V(0, 0, -0.008), 0.010, "SDT_Steel", seg=12)
    spin.cyl(pivot + V(0, 0, -0.040), pivot + V(0, 0, -0.005), 0.025, "SDT_Steel", seg=18)
    spin.cyl(pivot + V(0, 0, 0.005), pivot + V(0, 0, 0.040), 0.025, "SDT_Steel", seg=18)
    spin.cyl(pivot + V(0, 0, -0.005), pivot + V(0, 0, 0.005), 0.019, "SDT_PaintRed", seg=12)
    for k in range(3):
        a = TAU * k / 3
        r = V(math.cos(a), math.sin(a), 0)
        spin.obox((0.020, 0.013, 0.014), Matrix.Translation(pivot + r * 0.028) @ Matrix.Rotation(a, 4, "Z"),
                  "SDT_PaintRed", bevel=0.003)
    spin.box(pivot.x + 0.024, pivot.x + 0.0265, pivot.y - 0.004, pivot.y + 0.004, pivot.z + 0.012, pivot.z + 0.034,
             "SDT_PaintWhite")
    spin.hex(pivot + V(0.0, 0.0, 0.040), up, 0.008, 0.006, "SDT_Steel")

    body.finish()
    obj = spin.finish()
    motor = P.empty("mixerMotor", pivot)
    motor.empty_display_size = 0.06
    T.attach(obj, motor, pivot)
    sound = P.empty("mixerSoundNode", c + V(0, 0, 0.29))
    sound.empty_display_size = 0.06
    return {"motor": motor, "sound": sound}
