"""Přenosná násypka na jemně mleté vápno jako herní objekt (pallet) objects/hopper/limeHopper.i3d: čtvercový trubkový rám, uprostřed plechový
lievec (ústí 0,8 x 0,8 m) s nástavcem 0,9 x 0,9 m (drobná zásoba ~400 l) a výsypnou stolicí na big bag (dosedací rám z jeklu, rohová vodítka,
mřížka a nůž; vak se nakladačem jen položí), pod ním komorový podavač s dmychadlem (osa po X), na boku +X zmenšený vzduchem chlazený jednoválcový
diesel s nádrží (motor a nádrž pumpy otočené čelem příruby k podavači), výstupní spojka Storz na boku -X (hadice vleku) a čtyři opěry do kříže
(hopperLeg1..4 s patkami hopperFoot1..4: rameno se vysouvá šikmo z rohu rámu, posouvá je SprayDroneHopper.lua). Hladina zásoby je rovina
limeFillPlane (vanilla fillPlane). Samostatný skript nad prázdnou scénou (jako build_pump.py):

    blender.exe -b --python blender\\build_hopper.py

Osa jako u vleků: vpředu -Y, +X vlevo, Z nahoru, počátek na zemi uprostřed rámu (= osa stolice). Kolize: těleso rámu pod lievcem, stolice a pod každou
vysunutou patkou kvádr hopperFootCol<i> (ve skupině collisions, pevně, spodek FOOT_SINK pod rámem; SprayDroneHopper.lua mu zapíná filtr kolizí jen
s vysunutými opěrami, pak násypka stojí na patkách). Pravidla objektu (XML) jsou ručně, skript do něj jen přepíše blok <i3dMappings>; spočtené těžiště a rozměry kolizí zapíše do
GEOMETRY (souřadnice hry), z nich tools/test_hopper.py hlídá patky a centerOfMass v XML. Chování řeší scripts/SprayDroneHopper.lua a
scripts/SprayDronePump.lua (motor, nafta).
"""

import json
import math
import os
import sys

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parts_lib as PL  # noqa: E402
import build_canister as C  # noqa: E402
import build_link_items as L  # noqa: E402
import build_pump as BP  # noqa: E402
import export_middle_mod as X  # noqa: E402
import sdt_parts as P  # noqa: E402
from sdt_tanks import Mesh, V  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects", "hopper")
WORK = os.path.join(PROJECT, "out", "hopper")
BLEND = os.path.join(HERE, "spraydrone_hopper.blend")
GEOMETRY = os.path.join(HERE, "limeHopper_geometry.json")
NAME = "limeHopper"

FX = 0.52                        # osa podélníků rámu po X
Y_FRONT, Y_REAR = -0.50, 0.50    # příčné trubky rámu (čtverec kolem stolice)
Z_BASE, Z_TOP = BP.Z_BASE, BP.Z_TOP
FUN_Y = 0.0                      # střed lievce a stolice po Y (uprostřed rámu)
THROAT_Z, THROAT_H = 0.47, 0.09  # dno lievce (z) a poloviční strana hrdla
MOUTH_Z, MOUTH_H = 1.02, 0.40    # ústí lievce (z) a poloviční strana
EXT_TOP = 1.40                   # horní hrana nástavce = dosedací rám stolice (kořen big bagu)
EXT_H = 0.45                     # polovina vnitřní strany nástavce
RIM_W = 0.05                     # šířka dosedacího rámu z jeklu
GUIDE_IN = 0.50                  # vnitřní líc rohových vodítek od osy (vak 0,99 x 0,84 m)
GRATE_Z = EXT_TOP - 0.07         # mřížka pod dosedacím rámem
# motor a nádrž pumpy zmenšené na ENG_S kolem spodku motoru, otočené o -90° kolem Z (čelo příruby -Y pumpy míří k podavači na -X) a posunuté na bok +X
ENG_S = 0.72
ENG_X = 0.182
ENG_Z0 = Z_BASE + 0.032          # horní plocha nosné desky = spodek motoru
ENG_M = (Matrix.Translation((ENG_X, 0.0, ENG_Z0)) @ Matrix.Scale(ENG_S, 4) @ Matrix.Rotation(-math.pi / 2, 4, "Z")
         @ Matrix.Translation((0.0, 0.0, -ENG_Z0)))
AX_Z = (ENG_M @ V(0, 0, BP.AX_Z)).z   # osa klikového hřídele a podavače
FEED_X0, FEED_X1 = -0.20, 0.13   # válcové těleso podavače po X (u +X konce příruba motoru)
FEED_R = 0.13
OUTLET_Z = AX_Z + 0.06
OUTLET = V(-0.56, FUN_Y, OUTLET_Z)   # čelo výstupní spojky Storz (směr ven -X): sem se napojí hadice vleku
NECK = ENG_M @ V(0, BP.NECK_Y, BP.NECK_TOP)   # hrdlo nádrže nafty
LEG_Z = 0.095                    # osa ramen opěr
LEG_OUT0 = 0.07                  # svislá trubka zasunuté opěry od rohu rámu po úhlopříčce (vysunutí +travel, SprayDroneHopper <legs travel>)
ARM_L = 0.48                     # rameno opěry od svislé trubky dovnitř pouzdra
SLEEVE_L = 0.42                  # pouzdro opěry od rohu rámu dovnitř po úhlopříčce
LEG_TRAVEL = 0.30                # vysunutí ramene (stejné jako <legs travel> v XML; v pouzdře zůstane 0,145 m)
FOOT_Z = 0.05                    # spodek patky zasunuté opěry nad zemí
FOOT_SINK = 0.01                 # spodek kolize vysunuté patky pod spodkem kolize rámu: vysunutá násypka stojí na patkách
LEG_DROP = FOOT_Z + FOOT_SINK    # o kolik vizuální patka klesne (= <legs drop> v XML), dole sedí na spodku kolize patky
FOOT_HALF = 0.065                # polovina strany kolize patky (gumová patka 0,13 m)
FOOT_COL_TOP = 0.06              # horní plocha kolize patky nad spodkem rámu
GROUP_FILL_ROOT, MASK_FILL_ROOT = L.GROUP_FILL_ROOT, L.MASK_FILL_ROOT
# odhad hmotností dílů pro těžiště (součet = mass komponenty v XML, 120 kg)
MASSES = {"Hopper_Frame": 32, "Pump_Engine": 20, "Pump_Tank": 4, "Hopper_Funnel": 18, "Hopper_Feeder": 18, "Hopper_Stool": 20,
          "Hopper_Leg": 1.2, "Hopper_Foot": 0.8}


def corners():
    """Rohy rámu (sx, sy, roh, jednotkový směr opěry šikmo ven pod 45°)."""
    out = []
    for sx, sy in ((1, -1), (-1, -1), (1, 1), (-1, 1)):
        out.append((sx, sy, V(sx * FX, Y_REAR if sy > 0 else Y_FRONT, 0.0), V(sx, sy, 0.0).normalized()))
    return out


def build_frame(m):
    r = 0.015
    for sx in (-1, 1):
        x = sx * FX
        BP.tube_path(m, [V(x, Y_FRONT, Z_BASE), V(x, Y_REAR, Z_BASE)], r, "SDT_Frame")
        BP.tube_path(m, [V(x, Y_FRONT, Z_BASE), V(x, Y_FRONT, Z_TOP), V(x, Y_REAR, Z_TOP), V(x, Y_REAR, Z_BASE)], r, "SDT_Frame")
        for y in (Y_FRONT, Y_REAR):
            m.sphere(V(x, y, Z_BASE), r, "SDT_Frame", seg=12, rings=6)
            m.sphere(V(x, y, Z_TOP), r, "SDT_Frame", seg=12, rings=6)
            m.cyl(V(x, y, 0.03), V(x, y, Z_BASE), 0.013, "SDT_Frame", seg=10)
            m.box(x - 0.045, x + 0.045, y - 0.05, y + 0.05, 0.0, 0.03, "SDT_Rubber", bevel=0.006)
    for y in (Y_FRONT, Y_REAR):
        m.cyl(V(-FX, y, Z_BASE), V(FX, y, Z_BASE), r, "SDT_Frame", seg=12, caps=False)
        m.cyl(V(-FX, y, Z_TOP), V(FX, y, Z_TOP), r, "SDT_Frame", seg=12, caps=False)
    # dvě příčky pod nosnou deskou podavače a motoru
    for y in (-0.22, 0.22):
        m.cyl(V(-FX, y, Z_BASE), V(FX, y, Z_BASE), r, "SDT_Frame", seg=12, caps=False)
    m.box(-0.30, 0.48, -0.26, 0.26, Z_BASE + 0.012, Z_BASE + 0.032, "SDT_Frame", bevel=0.004)
    for sx in (-1, 1):
        m.cyl(V(sx * FX, -0.30, Z_TOP), V(sx * FX, 0.30, Z_TOP), 0.020, "SDT_Rubber", seg=12)


def build_funnel(m):
    """Čtyři plechové stěny lievce (desky s lichoběžníkovým obrysem), okraj ústí, podpěry z rámu a hrdlo k podavači."""
    cx, cy = 0.0, FUN_Y
    walls = (
        (V(cx, cy - THROAT_H, THROAT_Z), V(cx, cy - MOUTH_H, MOUTH_Z), V(1, 0, 0), V(0, -1, 0)),
        (V(cx, cy + THROAT_H, THROAT_Z), V(cx, cy + MOUTH_H, MOUTH_Z), V(1, 0, 0), V(0, 1, 0)),
        (V(cx - THROAT_H, cy, THROAT_Z), V(cx - MOUTH_H, cy, MOUTH_Z), V(0, 1, 0), V(-1, 0, 0)),
        (V(cx + THROAT_H, cy, THROAT_Z), V(cx + MOUTH_H, cy, MOUTH_Z), V(0, 1, 0), V(1, 0, 0)),
    )
    thick = 0.004
    for bottom, top, u, outward in walls:
        v = (top - bottom)
        length = v.length
        v.normalize()
        pts = [(-THROAT_H, 0.0), (THROAT_H, 0.0), (MOUTH_H, length), (-MOUTH_H, length)]
        n = u.cross(v)
        m.plate(pts, bottom, u, v, thick if n.dot(outward) > 0 else -thick, "SDT_Alu")
    rim_z0, rim_z1 = MOUTH_Z - 0.03, MOUTH_Z + 0.012
    for s in (-1, 1):
        m.box(-MOUTH_H - 0.012, MOUTH_H + 0.012, cy + s * MOUTH_H - 0.012, cy + s * MOUTH_H + 0.012, rim_z0, rim_z1, "SDT_PaintYellow", bevel=0.004)
        m.box(cx + s * MOUTH_H - 0.012, cx + s * MOUTH_H + 0.012, cy - MOUTH_H - 0.012, cy + MOUTH_H + 0.012, rim_z0, rim_z1, "SDT_PaintYellow", bevel=0.004)
    for sx in (-1, 1):
        for sy, y_frame in ((-1, Y_FRONT), (1, Y_REAR)):
            a = V(sx * FX, y_frame, Z_TOP)
            b = V(sx * (MOUTH_H - 0.03), cy + sy * (MOUTH_H - 0.03), MOUTH_Z - 0.04)
            m.cyl(a, b, 0.011, "SDT_Frame", seg=8)
    m.box(cx - THROAT_H - 0.012, cx + THROAT_H + 0.012, cy - THROAT_H - 0.012, cy + THROAT_H + 0.012, THROAT_Z - 0.035, THROAT_Z + 0.02, "SDT_Alu", bevel=0.004)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.hex(V(cx + sx * (THROAT_H + 0.012), cy + sy * 0.05, THROAT_Z - 0.01), V(sx, 0, 0), 0.007, 0.01, "SDT_Steel")


def build_feeder(m):
    """Podavač pod lievcem: válcové těleso po X na ose motoru (komorový podavač s dmychadlem), hrdlo k lievci, víko se šrouby na -X a výstupní
    trubka ke spojce Storz; na +X konci se k němu přišroubuje příruba motoru."""
    x0, x1, ax = FEED_X0, FEED_X1, AX_Z
    m.cyl(V(x0, FUN_Y, ax), V(x1, FUN_Y, ax), FEED_R, "SDT_CastIron", seg=40)
    for x in (x0, x1):
        m.torus(V(x, FUN_Y, ax), V(1, 0, 0), FEED_R, 0.009, "SDT_CastIron", seg=40, rseg=5)
    m.cyl(V(x0, FUN_Y, ax), V(x0 - 0.05, FUN_Y, ax), 0.10, "SDT_CastIron", seg=32)
    m.bolt_circle(V(x0 - 0.05, FUN_Y, ax), V(-1, 0, 0), 0.085, 8, 0.008, 0.007, "SDT_Steel")
    m.cyl(V(x0 - 0.05, FUN_Y, ax), V(x0 - 0.07, FUN_Y, ax), 0.03, "SDT_Steel", seg=16)
    m.cyl(V(x1, FUN_Y, ax), V(x1 + 0.016, FUN_Y, ax), 0.10, "SDT_CastIron", seg=32)
    m.box(-0.10, 0.10, FUN_Y - 0.10, FUN_Y + 0.10, ax + FEED_R - 0.03, THROAT_Z - 0.03, "SDT_CastIron", bevel=0.006)
    for x in (x0 + 0.05, x1 - 0.05):
        m.box(x - 0.025, x + 0.025, FUN_Y - 0.09, FUN_Y + 0.09, Z_BASE + 0.032, ax - FEED_R + 0.03, "SDT_Frame", bevel=0.004)
    m.cyl(V(x0 + 0.02, FUN_Y, OUTLET_Z), V(OUTLET.x + 0.045, FUN_Y, OUTLET_Z), 0.045, "SDT_AluCast", seg=24)
    m.cyl(V(-0.40, FUN_Y, OUTLET_Z), V(-0.415, FUN_Y, OUTLET_Z), 0.070, "SDT_AluCast", seg=28)
    m.bolt_circle(V(-0.415, FUN_Y, OUTLET_Z), V(-1, 0, 0), 0.056, 4, 0.007, 0.006, "SDT_Steel")
    m.storz(OUTLET, V(1, 0, 0), collar="SDT_PaintYellow")


def build_stool(m):
    """Nástavec nad ústím lievce (plechová skříň), dosedací rám z jeklu, rohová vodítka (náběhy pro vak), mřížka, nízký nůž ze dvou zkřížených
    čepelí a šikmá pouzdra opěr v rozích rámu."""
    cy = FUN_Y
    t = 0.004
    for s in (-1, 1):
        m.box(-EXT_H, EXT_H, cy + s * EXT_H - t, cy + s * EXT_H + t, MOUTH_Z, EXT_TOP - RIM_W, "SDT_Alu")
        m.box(s * EXT_H - t, s * EXT_H + t, cy - EXT_H, cy + EXT_H, MOUTH_Z, EXT_TOP - RIM_W, "SDT_Alu")
        m.box(-EXT_H, EXT_H, cy + s * MOUTH_H, cy + s * EXT_H, MOUTH_Z + 0.008, MOUTH_Z + 0.014, "SDT_Alu")
        m.box(s * MOUTH_H, s * EXT_H, cy - EXT_H, cy + EXT_H, MOUTH_Z + 0.008, MOUTH_Z + 0.014, "SDT_Alu")
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (EXT_H + 0.012), cy + sy * (EXT_H + 0.012)
            m.box(x - 0.014, x + 0.014, y - 0.014, y + 0.014, MOUTH_Z - 0.02, EXT_TOP - RIM_W, "SDT_Frame", bevel=0.003)
    for z in (MOUTH_Z + 0.16,):
        for s in (-1, 1):
            m.box(-EXT_H, EXT_H, cy + s * (EXT_H + 0.004), cy + s * (EXT_H + 0.016), z - 0.02, z + 0.02, "SDT_Frame", bevel=0.003)
            m.box(s * (EXT_H + 0.004), s * (EXT_H + 0.016), cy - EXT_H, cy + EXT_H, z - 0.02, z + 0.02, "SDT_Frame", bevel=0.003)
    o = EXT_H + RIM_W / 2
    for s in (-1, 1):
        m.box(-o - RIM_W / 2, o + RIM_W / 2, cy + s * o - RIM_W / 2, cy + s * o + RIM_W / 2, EXT_TOP - RIM_W, EXT_TOP, "SDT_PaintYellow", bevel=0.005)
        m.box(s * o - RIM_W / 2, s * o + RIM_W / 2, cy - o - RIM_W / 2, cy + o + RIM_W / 2, EXT_TOP - RIM_W, EXT_TOP, "SDT_PaintYellow", bevel=0.005)
    # rohová vodítka: dvě ploché lišty v každém rohu, nahoře vyhnuté ven, aby vak sjel na střed
    g, top = GUIDE_IN, EXT_TOP + 0.18
    for sx in (-1, 1):
        for sy in (-1, 1):
            for along_x in (True, False):
                for z0, z1, out0, out1 in ((EXT_TOP - 0.02, EXT_TOP + 0.10, 0.0, 0.0), (EXT_TOP + 0.10, top, 0.0, 0.05)):
                    if along_x:
                        a = V(sx * (g - 0.20), cy + sy * (g + 0.006 + out0), z0)
                        b = V(sx * (g - 0.20), cy + sy * (g + 0.006 + out1), z1)
                        m.plate([(0.0, 0.0), (0.20 + 0.03, 0.0), (0.20 + 0.03, (b - a).length), (0.0, (b - a).length)], a,
                                V(sx, 0, 0), (b - a).normalized(), 0.010 * sy, "SDT_PaintYellow")
                    else:
                        a = V(sx * (g + 0.006 + out0), cy + sy * (g - 0.20), z0)
                        b = V(sx * (g + 0.006 + out1), cy + sy * (g - 0.20), z1)
                        m.plate([(0.0, 0.0), (0.20 + 0.03, 0.0), (0.20 + 0.03, (b - a).length), (0.0, (b - a).length)], a,
                                V(0, sy, 0), (b - a).normalized(), -0.010 * sx, "SDT_PaintYellow")
    # mřížka a nůž (dvě zkřížené čepele 0,34 m, špička 0,04 m nad rámem: protrhne dno vaku, z dálky ho skoro nevidět)
    for k in range(-3, 4):
        m.cyl(V(-EXT_H, cy + k * 0.12, GRATE_Z), V(EXT_H, cy + k * 0.12, GRATE_Z), 0.008, "SDT_Steel", seg=8, caps=False)
    for k in (-1, 1):
        m.cyl(V(k * 0.22, cy - EXT_H, GRATE_Z - 0.018), V(k * 0.22, cy + EXT_H, GRATE_Z - 0.018), 0.010, "SDT_Steel", seg=8, caps=False)
    for ang in (45, -45):
        rot = Matrix.Translation(V(0.0, cy, GRATE_Z + 0.04)) @ Matrix.Rotation(math.radians(ang), 4, "Z")
        m.obox((0.34, 0.005, 0.07), rot, "SDT_Steel")
        m.obox((0.16, 0.003, 0.03), rot @ Matrix.Translation((0, 0, 0.045)), "SDT_Steel")
    # pouzdra opěr: čtyřhranné trubky po úhlopříčce z rohu rámu dovnitř, s plechem přivařeným k rohu
    for _, _, c, u in corners():
        a, b = V(c.x, c.y, LEG_Z) + u * 0.035, V(c.x, c.y, LEG_Z) - u * SLEEVE_L
        m.cyl(a, b, 0.032, "SDT_Frame", square=True, ref=V(0, 0, 1))
        rot = Matrix.Translation(V(c.x, c.y, (Z_BASE + LEG_Z) / 2) - u * 0.05) @ Matrix.Rotation(math.atan2(u.y, u.x), 4, "Z")
        m.obox((0.14, 0.008, LEG_Z - Z_BASE + 0.05), rot, "SDT_Frame", bevel=0.002)


def build_leg(i, c, u, cols):
    """Opěra i v rohu c (směr ven u): rameno se svislou trubkou a klikou (hopperLeg<i>, osa x uzlu = směr vysunutí), patka se šroubem
    (hopperFoot<i>, jen vizuál, klesá), obojí v zasunuté poloze, a kolize patky hopperFootCol<i> ve skupině collisions pevně pod vysunutou patkou."""
    ang = math.atan2(u.y, u.x)
    post = V(c.x, c.y, 0.0) + u * LEG_OUT0
    leg = L._pivot(f"hopperLeg{i}", (post.x, post.y, LEG_Z), P._root)
    leg.rotation_euler = (0.0, 0.0, ang)
    beam = Mesh(f"Hopper_Leg{i}")
    beam.cyl(V(post.x, post.y, LEG_Z) - u * ARM_L, V(post.x, post.y, LEG_Z) + u * 0.035, 0.025, "SDT_PaintYellow", square=True, ref=V(0, 0, 1))
    beam.cyl(V(post.x, post.y, FOOT_Z + 0.05), V(post.x, post.y, LEG_Z + 0.08), 0.024, "SDT_PaintYellow", seg=12)
    beam.cyl(V(post.x, post.y, LEG_Z + 0.08), V(post.x, post.y, LEG_Z + 0.10), 0.010, "SDT_Steel", seg=8)
    knob = V(post.x, post.y, LEG_Z + 0.10) + u * 0.07
    beam.cyl(V(post.x, post.y, LEG_Z + 0.10), knob, 0.006, "SDT_Steel", seg=6)
    beam.cyl(knob, knob + V(0, 0, 0.04), 0.011, "SDT_Rubber", seg=8)
    o = beam.finish()
    L._attach([o], leg)
    foot = L._pivot(f"hopperFoot{i}", (0.0, 0.0, FOOT_Z - LEG_Z), leg)
    pad = Mesh(f"Hopper_Foot{i}")
    # šroub patky: i po poklesu o LEG_DROP zůstane zasunutý ve svislé trubce ramene (ta začíná FOOT_Z + 0,05)
    pad.cyl(V(post.x, post.y, FOOT_Z + 0.02), V(post.x, post.y, FOOT_Z + 0.12), 0.012, "SDT_Steel", seg=8)
    pad.obox((0.13, 0.13, 0.022), Matrix.Translation((post.x, post.y, FOOT_Z + 0.011)) @ Matrix.Rotation(ang, 4, "Z"), "SDT_Rubber", bevel=0.004)
    pad.cyl(V(post.x, post.y, FOOT_Z + 0.022), V(post.x, post.y, FOOT_Z + 0.04), 0.03, "SDT_Steel", r1=0.014, seg=12)
    o = pad.finish()
    L._attach([o], foot)
    # kolize patky: pevně pod vysunutou patkou, počátek uprostřed jejího spodku (FOOT_SINK pod rámem), natočená s ramenem. Za běhu se neposouvá
    # (kolize jezdící s ramenem nenesla, klesající se zabořila do terénu a shodila vak, test ve hře 2026-10-29); skript jí jen zapíná filtr.
    col = C.box_object(f"hopperFootCol{i}", cols, -FOOT_HALF, FOOT_HALF, -FOOT_HALF, FOOT_HALF, 0.0, FOOT_COL_TOP + FOOT_SINK, C.GROUP_FLOOR,
                       C.MASK_FLOOR, compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    out = post + u * LEG_TRAVEL
    col.location = (out.x, out.y, -FOOT_SINK)
    col.rotation_euler = (0.0, 0.0, ang)
    return leg


def fill_plane(name, parent, center, size):
    """Rovina hladiny pro vanilla fillPlane: mřížka size x size s počátkem ve středu (hra jí dá materiál fillPlane a hýbe s ní podle klíčů XML)."""
    import sdt_parts as SP
    bm = bmesh.new()
    n = 4
    grid = [[bm.verts.new(((i / n - 0.5) * size, (j / n - 0.5) * size, 0.0)) for i in range(n + 1)] for j in range(n + 1)]
    for j in range(n):
        for i in range(n):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    SP._box_uv(bm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(SP.material("SDT_PaintWhite"))
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.matrix_parent_inverse = Matrix.Identity(4)
    o.location = center
    return o


def _part(name, builder):
    m = Mesh(name)
    builder(m)
    return m.finish()


def part_frame():
    """Svařený čtvercový rám z trubek s gumovými patkami a nosnou deskou (Hopper_Frame)."""
    return _part("Hopper_Frame", build_frame)


def part_funnel():
    """Čtyřboký lievec na vápno s okrajem ústí a podpěrami z rámu (Hopper_Funnel)."""
    return _part("Hopper_Funnel", build_funnel)


def part_feeder():
    """Komorový podavač s výstupní spojkou Storz (Hopper_Feeder)."""
    return _part("Hopper_Feeder", build_feeder)


def part_stool():
    """Nástavec s výsypnou stolicí na big bag a šikmá pouzdra opěr (Hopper_Stool)."""
    return _part("Hopper_Stool", build_stool)


def game(v):
    """Bod Blenderu v souřadnicích hry (x, výška, z = -y)."""
    return [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]


def centroid(obj):
    """Těžiště povrchu meshe ve světě (plochy vážené obsahem: plech a trubky) a obsah."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    total, acc = 0.0, Vector((0.0, 0.0, 0.0))
    for f in bm.faces:
        a = f.calc_area()
        total += a
        acc += f.calc_center_median() * a
    bm.free()
    return acc / max(total, 1e-9)


def mass_center(objs):
    """Těžiště sestavy z odhadnutých hmotností dílů MASSES (díl podle jména objektu bez čísla opěry); vrací bod a hmotnost."""
    acc, mass = Vector((0.0, 0.0, 0.0)), 0.0
    for o in objs:
        key = o.name.split(".")[0].rstrip("0123456789")
        kg = MASSES[key]
        acc += centroid(o) * kg
        mass += kg
    return acc / mass, mass


def build_body(name):
    parts = [PL.call(part_frame), PL.call(BP.part_engine), PL.call(BP.part_tank), PL.call(part_funnel), PL.call(part_feeder), PL.call(part_stool)]
    for o in parts[1:3]:
        o.matrix_world = ENG_M @ o.matrix_world
    bpy.context.view_layer.update()
    legs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("Hopper_Leg", "Hopper_Foot"))]
    com, mass = mass_center(parts + legs)
    obj = PL.join_meshes(name, parts)
    C.props(obj, clipDistance=100.0)
    return obj, com, mass


def bounds(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo, hi = Vector([min(p[k] for p in pts) for k in range(3)]), Vector([max(p[k] for p in pts) for k in range(3)])
    a, b = game(lo), game(hi)
    return [[min(a[k], b[k]) for k in range(3)], [max(a[k], b[k]) for k in range(3)]]


def write_geometry(com, mass):
    """Spočtené těžiště, kolize rámu a patek (zasunuté) a opěry v souřadnicích hry pro tools/test_hopper.py."""
    legs = []
    for i, (_, _, c, u) in enumerate(corners(), start=1):
        leg = bpy.data.objects[f"hopperLeg{i}"]
        col = bpy.data.objects[f"hopperFootCol{i}"]
        legs.append({"node": leg.name, "pos": game(leg.matrix_world.translation), "dir": [round(u.x, 4), round(-u.y, 4)],
                     "foot": game(bpy.data.objects[f"hopperFoot{i}"].matrix_world.translation), "collisionCenter": game(col.matrix_world.translation),
                     "collision": bounds(col)})
    data = {"mass": mass, "centerOfMass": game(com), "travel": LEG_TRAVEL, "drop": LEG_DROP, "footSink": FOOT_SINK, "footHalf": FOOT_HALF,
            "stool": game(V(0.0, FUN_Y, EXT_TOP)), "floor": bounds(bpy.data.objects["floorCollision01"]), "legs": legs}
    with open(GEOMETRY, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("těžiště (hra):", data["centerOfMass"], "hmotnost", mass)


def build():
    root, cols = L._reset(NAME)
    C.box_object("floorCollision01", cols, -FX - 0.02, FX + 0.02, Y_FRONT - 0.03, Y_REAR + 0.03, 0.0, THROAT_Z + 0.03, C.GROUP_FLOOR,
                 C.MASK_FLOOR, compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    # dosedací rám stolice a rohová vodítka: na nich leží big bag (kořen vaku = dno na EXT_TOP)
    o = EXT_H + RIM_W / 2
    for s in (-1, 1):
        C.box_object(f"stoolRailX{s + 1}", cols, -o - RIM_W / 2, o + RIM_W / 2, FUN_Y + s * o - RIM_W / 2, FUN_Y + s * o + RIM_W / 2, EXT_TOP - RIM_W,
                     EXT_TOP, C.GROUP_FLOOR, C.MASK_FLOOR, compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
        C.box_object(f"stoolRailY{s + 1}", cols, s * o - RIM_W / 2, s * o + RIM_W / 2, FUN_Y - o - RIM_W / 2, FUN_Y + o + RIM_W / 2, EXT_TOP - RIM_W,
                     EXT_TOP, C.GROUP_FLOOR, C.MASK_FLOOR, compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    # podlaha stolice přes celý otvor: vak (jeho kolize jsou jen čtyři kvádry kolem středu, u částečně plného vaku menší než otvor 0,9 m) by jinak
    # propadl mezi rámy; paprsek výpusti vaku ji přeskočí (díl bez fill unitu) a trefí plnicí kvádr pod ní
    C.box_object("stoolFloor", cols, -EXT_H, EXT_H, FUN_Y - EXT_H, FUN_Y + EXT_H, EXT_TOP - 0.03, EXT_TOP, C.GROUP_FLOOR, C.MASK_FLOOR,
                 compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for k, (xa, xb, ya, yb) in enumerate(((GUIDE_IN, GUIDE_IN + 0.03, GUIDE_IN - 0.20, GUIDE_IN + 0.03),
                                                  (GUIDE_IN - 0.20, GUIDE_IN + 0.03, GUIDE_IN, GUIDE_IN + 0.03))):
                x0, x1 = sorted((sx * xa, sx * xb))
                y0, y1 = sorted((FUN_Y + sy * ya, FUN_Y + sy * yb))
                C.box_object(f"stoolGuide{sx + 1}{sy + 1}{k}", cols, x0, x1, y0, y1, EXT_TOP - 0.02, EXT_TOP + 0.18, C.GROUP_FLOOR, C.MASK_FLOOR,
                             compoundChild=True, staticFriction=0.6, dynamicFriction=0.6, density=0.0)
    # plnicí kvádr pod mřížkou: do něj sype vak na stolici (paprsek z jeho výpusti dolů) i vyklopený vak
    C.box_object("limeFillRootNode", root, -EXT_H + 0.01, EXT_H - 0.01, FUN_Y - EXT_H + 0.01, FUN_Y + EXT_H - 0.01, GRATE_Z - 0.12, GRATE_Z - 0.03,
                 GROUP_FILL_ROOT, MASK_FILL_ROOT, kinematic=True, compound=True)
    # nalévání nafty: kvádr kolem otočené a zmenšené nádrže
    tank = [ENG_M @ V(x, y, z) for x in (-0.13, 0.13) for y in (0.03, 0.37) for z in (BP.TANK_Z - BP.TANK_R, BP.NECK_TOP)]
    C.box_object("dieselFillRootNode", root, min(p.x for p in tank) - 0.02, max(p.x for p in tank) + 0.02, min(p.y for p in tank) - 0.02,
                 max(p.y for p in tank) + 0.02, min(p.z for p in tank) - 0.02, NECK.z + 0.08, GROUP_FILL_ROOT, MASK_FILL_ROOT, kinematic=True, compound=True)
    for i, (_, _, c, u) in enumerate(corners(), start=1):
        build_leg(i, c, u, cols)
    _, com, mass = build_body(f"{NAME}_vis")
    L._pivot("hopperSoundNode", tuple(ENG_M @ V(0.0, 0.22, 0.45)), root)
    L._pivot("hopperDieselNeck", tuple(NECK), root)
    L._pivot("hopperFunnel", (0.0, FUN_Y, EXT_TOP + 0.02), root)
    L._pivot("hopperOutletPort", tuple(OUTLET), root)
    fill_plane("limeFillPlane", root, (0.0, FUN_Y, THROAT_Z + 0.01), 2 * EXT_H)
    bpy.context.view_layer.update()
    write_geometry(com, mass)
    return root


def export(root):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{NAME}.i3d")
    C.export_i3d(root, path)
    L.shader_materials(path)
    C.zero_density(path)
    names = [root.name, f"{NAME}_vis", "floorCollision01", "limeFillRootNode", "dieselFillRootNode", "hopperSoundNode", "hopperDieselNeck",
             "hopperFunnel", "hopperOutletPort", "limeFillPlane"] + [f"hopper{k}{i}" for i in range(1, 5) for k in ("Leg", "Foot", "FootCol")]
    mappings, found = X.i3d_mappings(path, names)
    print(mappings)
    C.write_mappings(os.path.join(OUT_DIR, f"{NAME}.xml"), found, names)
    plane = bpy.data.objects["limeFillPlane"]
    plane.hide_render = True
    C.store_image(root, os.path.join(OUT_DIR, f"store_{NAME}.dds"), os.path.join(WORK, f"store_{NAME}.png"))
    plane.hide_render = False


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    root = build()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    export(root)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
