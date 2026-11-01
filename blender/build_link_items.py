"""Relé tyče se stativem a tablet (mobilní vysílačka) jako herní objekty typu pallet (jako kanystry):
objects/relay/relayPole.i3d (všesměrová), objects/relay/relayPoleDirectional.i3d (směrová: stejný stativ, skříňka a baterie, na
stožáru místo radomu panel čelem k -Y v Blenderu = +Z v i3d se žlutým pruhem), objects/tablet/droneTablet.i3d a ikony obchodu.
Samostatný skript nad prázdnou scénou:

    blender.exe -b --python blender\\build_link_items.py [-- relay | relayDir | tablet]

Bez argumentu staví relay a tablet (relayDir jen na požádání, s náhledy do tmp/relayDir/). SDT_LINK_OUT = jiná složka místo
mod/.../objects (ověření, že build dá stejné soubory).

Pomocné funkce (kolizní kvádry, export, zápis i3dMappings, ikona obchodu) se berou z build_canister.py. Relé je skládací stativ
(nohy na posuvné objímce, vzpěry, teleskopický stožár, skříňka rádia, všesměrová anténa v radomu). Pravidla objektů (XML) jsou ručně.
"""

import math
import os
import re
import sys
import xml.etree.ElementTree as ET

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_canister as C  # noqa: E402
import export_middle_mod as X  # noqa: E402
import sdt_parts as P  # noqa: E402

PROJECT = os.path.dirname(HERE)
MOD = os.environ.get("SDT_LINK_OUT") or os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects")
WORK = os.path.join(PROJECT, "out", "link_items")
MASTER_H = 1.9


def _reset(name):
    C.wipe()
    P._coll = bpy.context.scene.collection
    root = C.box_object(f"{name}_main_component1", None, -0.02, 0.02, -0.02, 0.02, 0.0, 0.04, C.GROUP_ROOT, C.MASK_ROOT,
                        dynamic=True, compound=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0, clipDistance=150.0)
    P._root = root
    cols = bpy.data.objects.new("collisions", None)
    bpy.context.scene.collection.objects.link(cols)
    cols.parent = root
    cols.matrix_parent_inverse = Matrix.Identity(4)
    C.props(cols, clipDistance=10.0)
    return root, cols


HUB_Z = 0.14                     # pevný kroužek dole na stožáru, z něj vedou vzpěry k nohám
COLLAR_Z = 0.70                  # posuvná objímka s klouby nohou (rozloženo)
COLLAR_FOLDED_Z = 0.95           # objímka složeného stativu: vyjede nahoru a nohy se přiklopí ke stožáru
LEG_R = 0.55                     # poloměr rozkročení pat
MAST_FOLD = 1.0                  # o kolik se teleskopická část stožáru zasune ve složeném stavu
FOLD_OFFSET = 0.07               # vzdálenost složené paty od osy stožáru (m)
RELAY_NODES = {}                 # jméno -> (osa v i3d, úhel sklopení) pro nohy a vzpěry v bloku <sprayDroneRelay>
RELAY_TANGENTS = {}              # jméno -> osa sklopení v Blenderu (jen náhled složení)
# bateriový box pod skříňkou rádia (strana +Y). Odsazený od stožáru tak, aby složená noha 1 (visí podél stožáru na +Y, y do
# 0,056 m v té výšce) a objímka (jezdí po stožáru do z 0,975) prošly za ním; drží ho jen třmen nad složenou objímkou.
BATTERY_BOX = (-0.09, 0.09, 0.062, 0.162, 0.76, 0.98)
BATTERY_LEDS = 5                 # svisle zdola: červená, 2× oranžová, 2× zelená (relayBatteryLed0..4)
CAMERA_TARGET = (0.0, 0.0, 1.3)  # střed otáčení kamery po nástupu (relayCameraRot)
EXIT_POINT = (0.0, -1.0, 0.0)    # výstup na straně bez boxu, mezi nohama 2 a 3
# barevné diody baterie: obyčejný lesklý plast v barvě diody (staticLight_vertex chce data, která tvary tyče nemají -
# hra pak hlásí „Failed to create Graphics Pipeline State“)
RELAY_LED_MATERIALS = {"SDT_RelayLedRed": (0.90, 0.04, 0.02), "SDT_RelayLedOrange": (0.90, 0.35, 0.02),
                       "SDT_RelayLedGreen": (0.05, 0.80, 0.10), "SDT_RelayStatusOn": (0.08, 1.0, 0.22)}
for _name, _rgb in RELAY_LED_MATERIALS.items():
    P.MATERIALS.setdefault(_name, (_rgb, 0.0, 0.2))
P.MATERIALS.setdefault("SDT_LedLensOff", ((0.012, 0.035, 0.016), 0.0, 0.1))     # zhasnutá čočka diody pod svítícím uzlem
GROUP_FILL_ROOT, MASK_FILL_ROOT = 0x40000000, 0x20000000   # exactFillRootNode jako na vleku: vidí ho loadTrigger nabíjecí stanice


def _pivot(name, pos, parent):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.matrix_parent_inverse = Matrix.Identity(4)
    e.location = pos
    return e


def _attach(objs, pivot):
    bpy.context.view_layer.update()
    for o in objs:
        w = o.matrix_world.copy()
        o.parent = pivot
        o.matrix_parent_inverse = pivot.matrix_world.inverted()
        o.matrix_world = w


def _signed_angle(a, b, axis):
    a = a - axis * a.dot(axis)
    b = b - axis * b.dot(axis)
    return math.atan2(axis.dot(a.cross(b)), a.dot(b))


def _rrect_path(w, h, r, seg, cx=0.0, cy=0.0):
    """Obrys zaobleného obdélníku (půlrozměry w, h, poloměr rohů r) proti směru hodin, seg+1 bodů na roh."""
    pts = []
    for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        for i in range(seg + 1):
            a = math.radians(90 * k + 90 * i / seg)
            pts.append((cx + sx * (w - r) + r * math.cos(a), cy + sy * (h - r) + r * math.sin(a)))
    return pts


def rrect_prism(name, cx, cy, w, h, r, z0, z1, mat, seg=4, bevel_top=0.0, bevel_bottom=0.0, bevel_seg=2):
    """Hranol se zaoblenými svislými hranami (osa Z), volitelně zaoblené horní a dolní hrany."""
    bm = bmesh.new()
    pts = _rrect_path(w, h, r, seg, cx, cy)
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    bm.faces.new(list(reversed(bot)))
    bm.faces.new(top)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for amount, ring in ((bevel_top, top), (bevel_bottom, bot)):
        if amount > 0:
            ring = set(ring)
            edges = [e for e in bm.edges if e.verts[0] in ring and e.verts[1] in ring]
            bmesh.ops.bevel(bm, geom=edges, offset=amount, offset_type="OFFSET", segments=bevel_seg, profile=0.5,
                            affect="EDGES")
    return P._finish(name, bm, Matrix.Identity(4), mat, smooth_quads=True)


def rrect_band(name, outer, inner, z0, z1, mat, seg=4, corner=None, extend=0.022):
    """Pás mezi dvěma zaoblenými obdélníky outer / inner = (w, h, r), stejného středu: celý rámeček, nebo (corner = 0..3)
    jen jeden roh s rovnými náběhy délky extend."""
    po, pi = _rrect_path(*outer, seg), _rrect_path(*inner, seg)
    if corner is not None:
        n = seg + 1
        lo, hi = corner * n, corner * n + n

        def cut(pts):
            out = list(pts[lo:hi])
            for idx, nb in ((lo, (lo - 1) % len(pts)), (hi - 1, hi % len(pts))):
                a, b = Vector(pts[idx]), Vector(pts[nb])
                e = a + (b - a).normalized() * extend
                out = [(e.x, e.y)] + out if idx == lo else out + [(e.x, e.y)]
            return out
        po, pi = cut(po), cut(pi)
    bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for x, y in pts] for pts, z in ((po, z1), (pi, z1), (pi, z0), (po, z0))]
    n = len(po)
    steps = n if corner is None else n - 1
    for k in range(4):
        a, b = rings[k], rings[(k + 1) % 4]
        for i in range(steps):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if corner is not None:
        for i in (0, n - 1):
            bm.faces.new((rings[0][i], rings[1][i], rings[2][i], rings[3][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return P._finish(name, bm, Matrix.Identity(4), mat, smooth_quads=True)


def _place(objs, matrix):
    for o in objs:
        o.matrix_world = matrix @ o.matrix_world
    return objs


CASE_CY, CASE_W, CASE_H = 0.0725, 0.10, 0.0425     # střed (Y) a poloviny rozměrů skříňky rádia v půdorysu
CASE_Z0, CASE_Z1 = 1.02, 1.18
CASE_FACE = CASE_CY + CASE_H                         # čelo skříňky (+Y) s ovládacím panelem
PLUG_X = CASE_W + 0.024                              # osa kolenového konektoru kabelu u boční zásuvky (+X)
PLUG_Z = 1.10
ANT_BASE_Z = 1.99                                    # spodek hlavy antény (rozvodka), nad ní bílý radom


def radio_case(beacon=True):
    """Odolná skříňka rádia podle RTK základen (DJI D-RTK 2, Emlid Reach): zaoblené tělo s gumovými víky nahoře a dole,
    západky, madlo, konektory (anténa N na boku, krytky portů, průchodky dole) a na čele ovládací panel s kruhovým
    tlačítkem a pruhem stavu. Zhasnutá čočka je v těle; svítící zelený kroužek a pruh jsou samostatný uzel relayLed,
    který skript zobrazuje, jen když je tyč zapnutá. Vrací (díly do relayPole_vis, díly uzlu relayLed)."""
    cy, w, h, z0, z1 = CASE_CY, CASE_W, CASE_H, CASE_Z0, CASE_Z1
    parts = [
        rrect_prism("CaseLow", 0, cy, w + 0.002, h + 0.002, 0.021, z0, 1.05, "SDT_PaintDark", bevel_bottom=0.010, bevel_seg=3),
        rrect_prism("CaseMid", 0, cy, w, h, 0.02, 1.048, 1.152, "SDT_PaintYellow"),
        rrect_prism("CaseTop", 0, cy, w + 0.002, h + 0.002, 0.021, 1.15, z1, "SDT_PaintDark", bevel_top=0.010, bevel_seg=3),
        P.box("CasePlate", -0.04, 0.04, 0.026, 0.031, 1.03, 1.17, "SDT_Frame"),
        # bok +X: zásuvka antény (matice N); konektor kabelu je na stožáru, ať jede s ním
        P.cylinder_x("AntNut", (w + 0.0035, cy, PLUG_Z), 0.013, 0.007, "SDT_Steel", segments=6),
        # bok -X: gumové krytky portů a odvzdušňovací membrána
        P.cylinder_x("PortCapA", (-w - 0.0035, cy - 0.014, 1.12), 0.0105, 0.007, "SDT_Rubber", segments=14),
        P.cylinder_x("PortCapB", (-w - 0.0035, cy + 0.014, 1.12), 0.0105, 0.007, "SDT_Rubber", segments=14),
        P.cylinder_x("Vent", (-w - 0.0025, cy, 1.07), 0.006, 0.005, "SDT_Steel", segments=12),
    ]
    for sx in (-1, 1):
        parts += [P.cylinder_z(f"Gland{sx}", (sx * 0.04, cy, 1.012), 0.009, 0.016, "SDT_Rubber", segments=12),
                  P.cylinder_z(f"GlandNut{sx}", (sx * 0.04, cy, 1.0205), 0.0125, 0.005, "SDT_Steel", segments=6),
                  P.cylinder_z(f"HandleFoot{sx}", (sx * 0.055, cy, z1 + 0.0015), 0.012, 0.008, "SDT_PaintDark", segments=14)]
    arch = P.hermite_path([(-0.055, cy, z1 + 0.002), (-0.055, cy, z1 + 0.025), (-0.03, cy, z1 + 0.046),
                           (0.03, cy, z1 + 0.046), (0.055, cy, z1 + 0.025), (0.055, cy, z1 + 0.002)], samples=3)
    parts.append(P.sweep("Handle", arch, 0.0065, "SDT_Rubber", segments=8))

    # čelo: lokální osy z čela ven (+Y), y dolů (= -Z), počátek ve středu panelu
    front = [rrect_prism("Panel", 0, 0, 0.062, 0.042, 0.008, 0, 0.0025, "SDT_PaintDark", seg=3),
             P.ring_z("PwrRingOff", (-0.035, 0, 0.0031), 0.0145, 0.021, 0.0012, "SDT_LedLensOff", segments=32),
             P.cylinder_z("PwrButton", (-0.035, 0, 0.0042), 0.0125, 0.0034, "SDT_Rubber", segments=24),
             P.box("PwrMark", -0.0362, -0.0338, -0.011, -0.003, 0.0058, 0.0062, "SDT_PaintWhite"),
             rrect_prism("StatusOff", 0.0285, 0, 0.0235, 0.0036, 0.0018, 0.0025, 0.0037, "SDT_LedLensOff", seg=2),
             P.box("StatusLabel", 0.005, 0.052, 0.010, 0.029, 0.0025, 0.0031, "SDT_PaintWhite")]
    for sx in (-1, 1):
        front += [rrect_prism(f"Latch{sx}", sx * 0.073, 0, 0.0045, 0.040, 0.002, 0, 0.0065, "SDT_Rubber", seg=2),
                  P.cylinder_z(f"LatchPin{sx}", (sx * 0.073, 0, 0.0072), 0.0032, 0.0016, "SDT_Steel", segments=10)]
    lit = [P.ring_z("PwrRingOn", (-0.035, 0, 0.0035), 0.0145, 0.021, 0.0012, "SDT_RelayStatusOn", segments=32),
           rrect_prism("StatusOn", 0.0285, 0, 0.0235, 0.0036, 0.0018, 0.0029, 0.0041, "SDT_RelayStatusOn", seg=2)]
    to_face = Matrix.Translation((0, CASE_FACE, 1.10)) @ Matrix.Rotation(math.radians(-90), 4, "X")
    _place(lit, to_face)
    # svítící prstenec na hlavě antény vidět zdálky; relayLed se zobrazuje jen vysunutý, takže míří na vysunutou anténu
    if beacon:
        lit.append(P.ring_z("BeaconOn", (0, 0, ANT_BASE_Z + 0.062), 0.0205, 0.0252, 0.0145, "SDT_RelayStatusOn", segments=24))
    return parts + _place(front, to_face), lit


def antenna_parts():
    """Teleskopická část stožáru (relayMast): všesměrová kolineární anténa v bílém radomu na rozvodce, koaxiální kabel
    s kolenovým konektorem, který ve vysunutém stavu zapadá do zásuvky na skříňce rádia (složeno visí volně dole)."""
    cy = CASE_CY
    cable = P.hermite_path([(PLUG_X, cy, PLUG_Z + 0.02), (PLUG_X, cy, 1.25), (0.108, 0.062, 1.45), (0.075, 0.045, 1.68),
                            (0.045, 0.03, 1.85), (0.03, 0.01, 1.97), (0.026, 0.0, ANT_BASE_Z + 0.025)], samples=3)
    return [
        P.tube("MastMid", (0, 0, 1.22), (0, 0, 1.90), 0.016, "SDT_Alu", segments=14),
        P.cylinder_z("MidClamp", (0, 0, 1.90), 0.022, 0.04, "SDT_Frame", segments=14),
        P.box("MidClampLever", 0.022, 0.06, -0.006, 0.006, 1.89, 1.91, "SDT_Rubber"),
        P.tube("MastTop", (0, 0, 1.90), (0, 0, ANT_BASE_Z + 0.01), 0.012, "SDT_Alu", segments=12),
        P.cylinder_z("AntBlock", (0, 0, ANT_BASE_Z + 0.025), 0.022, 0.05, "SDT_PaintDark", segments=20),
        P.cylinder_z("AntSkirt", (0, 0, ANT_BASE_Z + 0.062), 0.0245, 0.014, "SDT_LedLensOff", segments=20),
        P.cylinder_z("Radome", (0, 0, ANT_BASE_Z + 0.294), 0.021, 0.45, "SDT_PaintWhite", segments=20),
        P.cylinder_z("DomeA", (0, 0, ANT_BASE_Z + 0.523), 0.021, 0.008, "SDT_PaintDark", segments=20, radius_top=0.017),
        P.cylinder_z("DomeB", (0, 0, ANT_BASE_Z + 0.531), 0.017, 0.008, "SDT_PaintDark", segments=20, radius_top=0.009),
        P.cylinder_z("DomeC", (0, 0, ANT_BASE_Z + 0.537), 0.009, 0.004, "SDT_PaintDark", segments=20, radius_top=0.002),
        P.cylinder_x("CablePlugTop", (0.0135, 0, ANT_BASE_Z + 0.025), 0.0065, 0.027, "SDT_PaintDark", segments=10),
        P.sweep("Cable", cable, 0.0045, "SDT_HoseBlack", segments=8),
        P.cylinder_x("CablePlugNut", (CASE_W + 0.008, cy, PLUG_Z), 0.0088, 0.008, "SDT_Steel", segments=10),
        P.cylinder_x("CablePlugBody", (CASE_W + 0.017, cy, PLUG_Z), 0.0085, 0.010, "SDT_PaintDark", segments=12),
        P.cylinder_z("CablePlugElbow", (PLUG_X, cy, PLUG_Z + 0.006), 0.0085, 0.024, "SDT_PaintDark", segments=12),
    ]


# směrový panel (relayPoleDirectional): tvar panelové antény z dřívější směrové antény na stativu, čelo k -Y (= +Z v i3d)
PANEL_Z0, PANEL_Z1 = 2.00, 2.54                     # rozloženo; složeno o MAST_FOLD níž, nad složenou objímkou nohou
PANEL_Y0, PANEL_Y1 = -0.105, -0.055                  # čelo / záda panelu
PANEL_W = 0.16                                       # polovina šířky
PANEL_BRACKETS = (2.30, 2.46)                        # objímky panelu na stožáru: složené nad horní objímkou stožáru (1,25)
PANEL_PLUG = (0.05, (PANEL_Y0 + PANEL_Y1) / 2, PANEL_Z0 - 0.012)


def panel_parts():
    """Teleskopická část stožáru (relayMast) směrové tyče: panelová anténa (bílý radom, tmavý rám a zadní deska, široký žlutý
    pruh nahoře na čele = směr signálu), dvě objímky na stožár, N konektory dole a koaxiální kabel od zásuvky skříňky rádia
    ke konektoru panelu."""
    py0, py1, pw = PANEL_Y0, PANEL_Y1, PANEL_W
    cy = CASE_CY
    top = PANEL_BRACKETS[1] + 0.03
    px, py, pz = PANEL_PLUG
    cable = P.hermite_path([(PLUG_X, cy, PLUG_Z + 0.02), (PLUG_X, cy, 1.25), (0.11, 0.05, 1.45), (0.09, 0.0, 1.70),
                            (0.07, -0.05, 1.88), (px, py, pz - 0.012)], samples=3)
    parts = [
        P.tube("MastMid", (0, 0, 1.22), (0, 0, 1.90), 0.016, "SDT_Alu", segments=14),
        P.cylinder_z("MidClamp", (0, 0, 1.90), 0.022, 0.04, "SDT_Frame", segments=14),
        P.box("MidClampLever", 0.022, 0.06, -0.006, 0.006, 1.89, 1.91, "SDT_Rubber"),
        P.tube("MastTop", (0, 0, 1.90), (0, 0, top), 0.012, "SDT_Alu", segments=12),
        P.cylinder_z("MastCap", (0, 0, top + 0.006), 0.014, 0.012, "SDT_PaintDark", segments=12),
        rrect_prism("Radome", 0, (py0 + py1) / 2, pw, (py1 - py0) / 2, 0.018, PANEL_Z0, PANEL_Z1, "SDT_PaintWhite",
                    bevel_top=0.012, bevel_bottom=0.012, bevel_seg=3),
        P.box("BackPlate", -pw + 0.01, pw - 0.01, py1, py1 + 0.012, PANEL_Z0 + 0.02, PANEL_Z1 - 0.02, "SDT_PaintDark"),
        P.box("FrontStripe", -pw + 0.015, pw - 0.015, py0 - 0.002, py0 + 0.004, PANEL_Z1 - 0.10, PANEL_Z1 - 0.045, "SDT_PaintYellow"),
        P.box("FrontLabel", -0.07, 0.07, py0 - 0.0015, py0 + 0.004, PANEL_Z0 + 0.05, PANEL_Z0 + 0.075, "SDT_PaintDark"),
        P.sweep("Cable", cable, 0.0045, "SDT_HoseBlack", segments=8),
        P.cylinder_x("CablePlugNut", (CASE_W + 0.008, cy, PLUG_Z), 0.0088, 0.008, "SDT_Steel", segments=10),
        P.cylinder_x("CablePlugBody", (CASE_W + 0.017, cy, PLUG_Z), 0.0085, 0.010, "SDT_PaintDark", segments=12),
        P.cylinder_z("CablePlugElbow", (PLUG_X, cy, PLUG_Z + 0.006), 0.0085, 0.024, "SDT_PaintDark", segments=12),
    ]
    for z in PANEL_BRACKETS:
        parts += [P.box(f"Bracket{z:.2f}", -0.03, 0.03, py1 + 0.012, -0.008, z - 0.02, z + 0.02, "SDT_Steel"),
                  P.cylinder_z(f"BracketClamp{z:.2f}", (0, 0, z), 0.020, 0.05, "SDT_Frame", segments=16),
                  P.box(f"BracketBolt{z:.2f}", 0.018, 0.046, -0.006, 0.006, z - 0.006, z + 0.006, "SDT_Rubber")]
    for sx in (-0.05, 0.05):
        parts.append(P.cylinder_z(f"NPlug{sx}", (sx, py, pz), 0.010, 0.024, "SDT_Steel", segments=10))
    return parts


def build_relay(directional=False):
    """Skládací stativ jako na světla: nohy visí z posuvné objímky, vzpěry vedou od pevného kroužku dole k nohám. Při
    složení objímka (relayCollar) vyjede nahoru a nohy se přiklopí dolů ke stožáru; teleskopická část (relayMast) se
    všesměrovou anténou (directional: se směrovým panelem) se zasune. Délka vzpěr je dopočítaná tak, aby seděla v obou
    krajních polohách."""
    name = "relayPoleDirectional" if directional else "relayPole"
    root, cols = _reset(name)
    C.box_object("floorCollision01", cols, -0.40, 0.40, -0.40, 0.40, 0.0, 0.05, C.GROUP_FLOOR, C.MASK_FLOOR,
                 compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    C.box_object("mastCollision", cols, -0.05, 0.05, -0.05, 0.05, 0.05, 1.25, C.GROUP_FLOOR, C.MASK_FLOOR,
                 compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    fixed = [
        P.tube("MastLow", (0, 0, 0.08), (0, 0, 1.25), 0.020, "SDT_Alu", segments=16),
        P.cylinder_z("MastFoot", (0, 0, 0.08), 0.024, 0.03, "SDT_Rubber", segments=16),
        P.cylinder_z("StrutHub", (0, 0, HUB_Z), 0.032, 0.04, "SDT_Frame", segments=16),
        P.cylinder_z("TopClamp", (0, 0, 1.25), 0.028, 0.05, "SDT_Frame", segments=16),
        P.box("TopClampLever", 0.028, 0.07, -0.007, 0.007, 1.24, 1.26, "SDT_Rubber"),
        P.box("RadioBandLow", -0.03, 0.03, -0.024, 0.03, 1.04, 1.055, "SDT_Steel"),
        P.box("RadioBandHigh", -0.03, 0.03, -0.024, 0.03, 1.145, 1.16, "SDT_Steel"),
    ]
    if directional:
        # složený panel (tak se tyč nese a pokládá)
        C.box_object("panelCollision", cols, -0.17, 0.17, -0.12, -0.04, PANEL_Z0 - MAST_FOLD, PANEL_Z1 - MAST_FOLD, C.GROUP_FLOOR,
                     C.MASK_FLOOR, compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    case, led_parts = radio_case(beacon=not directional)
    if directional:
        # svítící prstenec pod panelem kolem horní části stožáru
        led_parts.append(P.ring_z("BeaconOn", (0, 0, PANEL_Z0 - 0.045), 0.0125, 0.0205, 0.014, "SDT_RelayStatusOn", segments=24))
    m = P.merge(f"{name}_vis", fixed + case)
    C.props(m, clipDistance=100.0)

    collar = _pivot("relayCollar", (0, 0, COLLAR_Z), root)
    cm = P.merge("relayCollar_vis", [
        P.cylinder_z("LegCollar", (0, 0, COLLAR_Z), 0.036, 0.05, "SDT_Frame", segments=16),
        P.box("CollarKnob", 0.034, 0.065, -0.008, 0.008, COLLAR_Z - 0.008, COLLAR_Z + 0.008, "SDT_Rubber")])
    C.props(cm, clipDistance=100.0)
    _attach([cm], collar)
    lift = COLLAR_FOLDED_Z - COLLAR_Z
    for k in range(3):
        a = math.radians(90 + 120 * k)
        radial = Vector((math.cos(a), math.sin(a), 0.0))
        tangent = Vector((-math.sin(a), math.cos(a), 0.0))
        hinge = Vector((0.036 * radial.x, 0.036 * radial.y, COLLAR_Z))
        foot = Vector((LEG_R * radial.x, LEG_R * radial.y, 0.02))
        rel = foot - hinge
        length = rel.length
        # složená noha visí z vyjeté objímky skoro svisle, pata FOLD_OFFSET od osy
        out = FOLD_OFFSET - 0.036
        rel_f = radial * out + Vector((0, 0, -math.sqrt(length ** 2 - out ** 2)))
        hinge_f = hinge + Vector((0, 0, lift))
        hub = Vector((0.032 * radial.x, 0.032 * radial.y, HUB_Z))
        # bod na noze, kde končí vzpěra: stejná vzdálenost od kroužku rozloženo i složeno (vzpěra je tuhá)
        lo, hi = 0.15, 0.95
        for _ in range(60):
            f = (lo + hi) / 2
            d_open = (hinge + rel * f - hub).length
            d_fold = (hinge_f + rel_f * f - hub).length
            if d_fold > d_open:
                lo = f
            else:
                hi = f
        f = (lo + hi) / 2
        strut_end = hinge + rel * f

        leg_pivot = _pivot(f"relayLeg{k + 1}", (hinge.x, hinge.y, 0.0), collar)    # vůči objímce
        leg = P.merge(f"relayLeg{k + 1}_vis", [
            P.tube(f"Leg{k}", tuple(hinge), tuple(foot), 0.012, "SDT_Frame", segments=10),
            P.cylinder_z(f"LegHinge{k}", tuple(hinge), 0.010, 0.03, "SDT_Steel", segments=8),
            P.cylinder_z(f"Foot{k}", (foot.x, foot.y, 0.012), 0.022, 0.024, "SDT_Rubber", segments=12)])
        C.props(leg, clipDistance=100.0)
        _attach([leg], leg_pivot)

        strut_pivot = _pivot(f"relayStrut{k + 1}", tuple(hub), root)
        strut = P.merge(f"relayStrut{k + 1}_vis", [
            P.tube(f"Strut{k}", tuple(hub), tuple(strut_end), 0.006, "SDT_Frame", segments=8)])
        C.props(strut, clipDistance=100.0)
        _attach([strut], strut_pivot)

        axis_i3d = (tangent.x, tangent.z, -tangent.y)          # Blender (x, y, z) -> i3d (x, z, -y)
        RELAY_NODES[f"relayLeg{k + 1}"] = (axis_i3d, math.degrees(_signed_angle(rel, rel_f, tangent)))
        RELAY_NODES[f"relayStrut{k + 1}"] = (axis_i3d, math.degrees(
            _signed_angle(strut_end - hub, hinge_f + rel_f * f - hub, tangent)))
        RELAY_TANGENTS[f"relayLeg{k + 1}"] = RELAY_TANGENTS[f"relayStrut{k + 1}"] = tangent.copy()

    # teleskopická část: dvě sekce, objímka mezi nimi, sektorová anténa na držácích a krytka
    mast = _pivot("relayMast", (0, 0, 0), root)
    mt = P.merge("relayMast_vis", panel_parts() if directional else antenna_parts())
    C.props(mt, clipDistance=100.0)
    _attach([mt], mast)
    led = P.merge("relayLed", led_parts)
    led.parent = root
    led.matrix_parent_inverse = Matrix.Identity(4)
    C.props(led, clipDistance=150.0)
    build_battery_box(root)
    build_enter_nodes(root)
    bpy.context.view_layer.update()
    return root


def build_battery_box(root):
    """Bateriový box podle schváleného náhledu (tmp/preview/relay_box_detail.png): tmavě šedé tělo s lemem, panel s pěti
    diodami na čele (+Y), tlačítko, štítek a nabíjecí zásuvka s krytkou na boku +X. Visí na třmenu, který svírá stožár nad
    složenou objímkou. Diody jsou samostatné uzly, skript ukazuje jen tolik, kolik je nabito."""
    x0, x1, y0, y1, z0, z1 = BATTERY_BOX
    parts = [
        P.chamfer_box("BatBody", x0, x1, y0, y1, z0, z1, "SDT_ChargerGrey", 0.004),
        P.box("BatRim", x0 - 0.004, x1 + 0.004, y0 - 0.004, y1 + 0.004, z1 - 0.012, z1, "SDT_PaintDark"),
        P.box("BatFoot", x0 - 0.004, x1 + 0.004, y0 - 0.004, y1 + 0.004, z0, z0 + 0.012, "SDT_PaintDark"),
        # třmen: objímka na stožáru nad složenou objímkou nohou a plech, na kterém box visí
        P.cylinder_z("BatClamp", (0, 0, 0.99), 0.026, 0.02, "SDT_Frame", segments=16),
        P.box("BatHanger", -0.03, 0.03, 0.02, y0 + 0.07, 0.98, 0.995, "SDT_Frame"),
        P.box("BatLedPlate", -0.022, 0.022, y1, y1 + 0.003, z0 + 0.075, z1 - 0.03, "SDT_PaintDark"),
        P.box("BatButton", 0.04, 0.07, y1, y1 + 0.004, z0 + 0.10, z0 + 0.13, "SDT_PaintDark"),
        P.box("BatLabel", -0.07, -0.035, y1, y1 + 0.002, z0 + 0.10, z1 - 0.05, "SDT_PaintWhite"),
        P.box("BatSocketPlate", x1, x1 + 0.004, y0 + 0.02, y1 - 0.02, z0 + 0.03, z0 + 0.08, "SDT_PaintDark"),
        P.cylinder_x("BatSocket", (x1 + 0.006, (y0 + y1) / 2, z0 + 0.055), 0.013, 0.006, "SDT_Steel", segments=16),
        P.cylinder_x("BatSocketHole", (x1 + 0.0095, (y0 + y1) / 2, z0 + 0.055), 0.008, 0.002, "SDT_Rubber", segments=12),
        P.box("BatSocketCap", x1, x1 + 0.005, y1 - 0.04, y1 - 0.017, z0 + 0.062, z0 + 0.086, "SDT_Rubber"),
    ]
    box = P.merge("relayBattery_vis", parts)
    C.props(box, clipDistance=100.0)
    colors = ["SDT_RelayLedRed", "SDT_RelayLedOrange", "SDT_RelayLedOrange", "SDT_RelayLedGreen", "SDT_RelayLedGreen"]
    for i in range(BATTERY_LEDS):
        z = z0 + 0.095 + i * 0.026
        led = P.box(f"relayBatteryLed{i}", -0.012, 0.012, y1 + 0.003, y1 + 0.006, z - 0.008, z + 0.008, colors[i])
        led.parent = root
        led.matrix_parent_inverse = Matrix.Identity(4)
        C.props(led, clipDistance=40.0)
    # nabíjecí stanice (loadTrigger s ELECTRICCHARGE) hledá vozidlo podle exactFillRootNode s příznakem FILLABLE
    C.box_object("exactFillRootNode", root, -0.25, 0.25, -0.25, 0.25, 0.05, 1.25, GROUP_FILL_ROOT, MASK_FILL_ROOT,
                 kinematic=True, compound=True)


def build_enter_nodes(root):
    """Uzly pro nástup (enterable): otočný uzel kamery kolem stožáru, kamera a místo výstupu."""
    target = _pivot("relayCameraRot", CAMERA_TARGET, root)
    data = bpy.data.cameras.new("relayCamera")
    data.lens = 22
    data.clip_start = 0.1
    data.clip_end = 5000
    cam = bpy.data.objects.new("relayCamera", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.parent = target
    cam.matrix_parent_inverse = Matrix.Identity(4)
    cam.location = (0.0, 5.0, 1.5)
    _pivot("relayExitPoint", EXIT_POINT, root)


def build_tablet():
    """Odolný tablet pro pole: gumový rám se zesílenými rohy, zapuštěný displej a na něm logo designu vleku (skutečnou mapu
    ukáže plánovač po otevření tabletu). Je to ruční nástroj jako baterka: kořen bez fyziky, pod ním graphics (model
    natočený displejem k hráči, osa -Z v i3d), handNode a firstPersonNode (polohu dostanou až v i3d, viz TABLET_NODES)."""
    C.wipe()
    P._coll = bpy.context.scene.collection
    root = _pivot("droneTablet", (0, 0, 0), None)
    P._root = root
    graphics = _pivot("graphics", (0, 0, 0), root)
    _pivot("handNode", (0, 0, 0), root)
    _pivot("firstPersonNode", (0, 0, 0), root)
    w, h, t = 0.135, 0.09, 0.022
    sw, sh = 0.115, 0.072
    zb = t - 0.004                   # horní plocha těla pod displejem; lem kolem displeje sahá do t
    rc = 0.02                        # poloměr zaoblení rohů těla; gumové rohy jsou o 4 mm větší soustředné oblouky
    parts = [rrect_prism("Body", 0, 0, w, h, rc, 0.0, zb, "SDT_Plastic", seg=6, bevel_top=0.005, bevel_bottom=0.004),
             rrect_band("Bezel", (w - 0.004, h - 0.004, rc - 0.004), (sw, sh, 0.004), zb - 0.001, t, "SDT_Plastic", seg=6)]
    for k in range(4):
        parts.append(rrect_band(f"Corner{k}", (w + 0.004, h + 0.004, rc + 0.004), (w - 0.003, h - 0.003, rc - 0.003),
                                -0.002, t + 0.003, "SDT_Rubber", seg=6, corner=k, extend=0.024))
    # vypnutý displej (tmavé sklo) je součást těla; svítící obsah (podsvícená plocha a logo designu) je samostatný uzel
    # tabletScreenOn 1 mm nad ním, skript ho skrytím zhasne
    zs = zb + 0.0005
    parts.append(rrect_prism("Screen", 0, 0, sw, sh, 0.004, zb - 0.0005, zs, "SDT_ScreenOff", seg=3))
    on = [rrect_prism("Backlight", 0, 0, sw, sh, 0.004, zs + 0.001, zs + 0.0013, "SDT_Screen", seg=3)]
    parts += [P.cylinder_z("Camera", (0.0, -0.081, t), 0.003, 0.001, "SDT_Screen", segments=10),
              P.box("PowerButton", w, w + 0.004, 0.03, 0.05, 0.008, 0.016, "SDT_Rubber"),
              P.box("VolumeButton", w, w + 0.004, -0.02, 0.01, 0.008, 0.016, "SDT_Rubber"),
              rrect_prism("Grip", 0, 0, 0.10, 0.06, 0.012, -0.004, 0.0, "SDT_Rubber", seg=3)]
    # krátká anténa externího RTK/rádia na horní hraně (v ruce hrana u -Y), mírně nakloněná dozadu; na pantu, ať vypadá sklopná
    base = Vector((-0.085, -h - 0.002, 0.011))
    ant = Vector((0.0, -math.cos(math.radians(20)), -math.sin(math.radians(20))))
    parts += [P.cylinder_x("AntHinge", tuple(base), 0.0075, 0.018, "SDT_Rubber", segments=12),
              P.tube("AntSocket", tuple(base), tuple(base + ant * 0.016), 0.0065, "SDT_Steel", segments=6),
              P.tube("Antenna", tuple(base + ant * 0.016), tuple(base + ant * 0.095), 0.0048, "SDT_Rubber", segments=10,
                     radius_end=0.0035)]
    m = P.merge("droneTablet_vis", parts)
    s = P.merge("tabletScreenOn", on)
    # logo designu vleku, ke kterému by se tablet připojil (SprayDroneLink.updateTabletLogo přepíná viditelnost uzlů
    # brand_<KEY>_tablet); polepy visí pod tabletScreenOn, ať zhasínají s obrazovkou. Staví se před natočením tabletu.
    # natočení níž dává -Y nahoru (hrana u -Y skončí nahoře v ruce), proto up (0, -1, 0) a pruh u +Y dole
    lz = zs + 0.0013
    P.brand_decal_set("tablet", "lockupOnDark", (0.0, -0.010, lz), (0, 0, 1), (0, -1, 0), 2 * sw - 0.006, parent=s,
                      offset=0.0008)
    P.brand_decal_set("tablet", "stripe", (0.0, sh - 0.020, lz), (0, 0, 1), (0, -1, 0), 2 * sw * 0.6, 0.004, parent=s,
                      offset=0.0008, tag="Bar")
    for o in (m, s):
        C.props(o, clipDistance=100.0)
        # displej (+Z v Blenderu) k hráči: Blender +Y = i3d -Z; spodní hrana tabletu v počátku
        o.matrix_world = Matrix.Translation((0, 0, h)) @ Matrix.Rotation(math.radians(-90), 4, "X") @ o.matrix_world
    _attach([m, s], graphics)
    bpy.context.view_layer.update()
    return root


BRAND_TEXTURE_REL = "../../vehicles/sprayDroneTrailerMiddle/textures/sdt_brand.dds"   # z objects/tablet/


def shader_materials(path):
    """Materiály exportu -> vehicleShader s detailLibrary (postup build_canister.vehicle_shader_materials), bez vmask."""
    tree = ET.parse(path)
    root = tree.getroot()
    files = root.find("Files")
    if files is None:
        files = ET.Element("Files")
        root.insert(0, files)
    for f in list(files):
        files.remove(f)
    by_name, counter = {}, [0]

    def file_id(name):
        if name not in by_name:
            counter[0] += 1
            ET.SubElement(files, "File", fileId=str(counter[0]), filename=name)
            by_name[name] = str(counter[0])
        return by_name[name]

    templates = X.load_templates()
    shader = file_id(X.SHADER)
    for mat in root.find("Materials"):
        name = mat.get("name")
        if name not in P.MATERIALS:
            continue
        for child in list(mat):
            mat.remove(child)
        for attr in ("specularColor", "customShaderVariation", "alphaBlending"):
            mat.attrib.pop(attr, None)
        mat.set("customShaderId", shader)
        # LED a displeje svítí stejně jako na vleku (staticLight_vertex)
        emissive = X.EMISSIVE_MATERIALS.get(name)
        if name in RELAY_LED_MATERIALS:
            emissive = None
            tpl = templates["plasticPainted"]
            ET.SubElement(mat, "CustomParameter", name="colorScale", value="%g %g %g" % RELAY_LED_MATERIALS[name])
            if "smoothnessScale" in tpl:
                ET.SubElement(mat, "CustomParameter", name="smoothnessScale", value=tpl["smoothnessScale"])
            for tag, fname in X.BASE_MAPS.items():
                ET.SubElement(mat, tag, fileId=file_id(fname))
            continue
        if emissive is not None:
            mat.set("customShaderVariation", "staticLight_vertex")
            ET.SubElement(mat, "CustomParameter", name="colorScale", value="%g %g %g" % emissive)
            ET.SubElement(mat, "CustomParameter", name="lightIds0", value="0 0 0 0")
            ET.SubElement(mat, "CustomParameter", name="lightTypeBitMask", value="0")
            for tag, fname in X.BASE_MAPS.items():
                ET.SubElement(mat, tag, fileId=file_id(fname))
            continue
        # stejná šablona z detailLibrary jako na vleku (guma, pozinkovaná ocel, prášková barva, …), jinak plast / kov
        if name in X.MATERIAL_MAP:
            tpl_name, color, extra = X.MATERIAL_MAP[name]
        else:
            color, metallic, _ = P.MATERIALS[name]
            tpl_name, extra = ("metalPainted" if metallic > 0.5 else "plasticPainted"), {}
        tpl = templates[tpl_name]
        if color is None:
            color = tuple(float(v) for v in tpl.get("colorScale", "1 1 1").split())
        params = {"colorScale": "%g %g %g" % tuple(color)}
        for p in ("porosity", "smoothnessScale", "metalnessScale", "clearCoatIntensity", "clearCoatSmoothness"):
            if p in tpl:
                params[p] = tpl[p]
        params.update(extra)
        texture = X.BASE_MAPS["Texture"]
        if name in P.BRAND_DECAL_MATERIALS:
            # atlas polepů designu jako na vleku (průhlednost); soubor se nekopíruje, bere se z Middle
            texture = BRAND_TEXTURE_REL
            params["alphaBlendingClipThreshold"] = "1"
            mat.set("alphaBlending", "true")
        for p in sorted(params):
            ET.SubElement(mat, "CustomParameter", name=p, value=params[p])
        for m in ("detailDiffuse", "detailNormal", "detailSpecular"):
            ET.SubElement(mat, "Custommap", name=m, fileId=file_id(tpl[m]))
        normal = X.normal_map_ref(path, name) if name in X.NORMAL_MAPS else X.BASE_MAPS["Normalmap"]
        for tag, fname in (("Texture", texture), ("Normalmap", normal),
                           ("Glossmap", "$data/shared/default_vmask.png")):
            ET.SubElement(mat, tag, fileId=file_id(fname))
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")


def write_relay_block(xml_path):
    """Blok <sprayDroneRelay> (nohy: osa a úhel sklopení, vysouvací část stožáru, kontrolka) před <i3dMappings>; atributy
    otevírací značky (výseč směrové tyče) zůstanou z XML."""
    text = open(xml_path, encoding="utf-8").read()
    found = re.search(r"    <sprayDroneRelay[ >][^>]*>?", text)
    a = found.start() if found else -1
    opening = text[a:text.index(">", a) + 1] if a >= 0 else "    <sprayDroneRelay>"
    lines = [opening]
    for node, (axis, angle) in RELAY_NODES.items():
        lines.append('        <leg node="%s" axis="%.4f %.4f %.4f" angle="%.2f"/>' % (node, *axis, angle))
    lines.append('        <slide node="relayCollar" foldedTrans="0 %g 0"/>' % round(COLLAR_FOLDED_Z - COLLAR_Z, 4))
    lines.append('        <mast node="relayMast" foldedTrans="0 %g 0"/>' % -MAST_FOLD)
    lines.append('        <led node="relayLed"/>')
    for i in range(BATTERY_LEDS):
        lines.append(f'        <batteryLed node="relayBatteryLed{i}"/>')
    lines.append("    </sprayDroneRelay>")
    lines.append("")
    b = text.find("</sprayDroneRelay>")
    if a >= 0:
        end = b + len("</sprayDroneRelay>")
        while text[end] in "\r\n":
            end += 1
        text = text[:a] + text[end:]
    i = text.index("    <i3dMappings>")
    open(xml_path, "w", encoding="utf-8", newline="").write(text[:i] + "\n".join(lines) + "\n" + text[i:])


def export_item(name, root, subdir):
    out = os.path.join(MOD, subdir)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{name}.i3d")
    C.export_i3d(root, path)
    shader_materials(path)
    C.zero_density(path)
    names = [root.name, f"{name}_vis", "floorCollision01"]
    if name.startswith("relayPole"):
        names += [f"relay{part}{k}" for part in ("Leg", "Strut") for k in (1, 2, 3)] + ["relayCollar", "relayMast", "relayLed"]
        names += [f"relayBatteryLed{i}" for i in range(BATTERY_LEDS)]
        names += ["relayCameraRot", "relayCamera", "relayExitPoint", "exactFillRootNode"]
    mappings, found = X.i3d_mappings(path, names)
    print(f"{name}: {path}")
    print(mappings)
    C.write_mappings(os.path.join(out, f"{name}.xml"), found, names)
    if name.startswith("relayPole"):
        write_relay_block(os.path.join(out, f"{name}.xml"))
    C.store_image(root, os.path.join(out, f"store_{name}.dds"), os.path.join(WORK, f"store_{name}.png"))


# úchop a pohled z první osoby převzaté z vanilla baterky (data/handTools/brandless/flashlight/flashlight.i3d), doladit ve hře
TABLET_NODES = {"handNode": ("-0.036 0.093 -0.022", "-169.815994 13.287 91.924004"),
                "firstPersonNode": ("0.214 0.274 -0.565579", "0 0 0")}


def export_tablet(root):
    """Tablet jako ruční nástroj: i3d bez fyziky, uzly úchopu z TABLET_NODES, i3dMappings a ikona obchodu."""
    out = os.path.join(MOD, "tablet")
    path = os.path.join(out, "droneTablet.i3d")
    C.export_i3d(root, path)
    shader_materials(path)
    tree = ET.parse(path)
    for el in tree.getroot().find("Scene").iter():
        if el.get("name") in TABLET_NODES:
            el.set("translation", TABLET_NODES[el.get("name")][0])
            el.set("rotation", TABLET_NODES[el.get("name")][1])
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")
    X.hide_nodes(path, [])           # polepy nevýchozích designů skryté, správný ukáže skript
    names = ["graphics", "handNode", "firstPersonNode", "tabletScreenOn"]
    mappings, found = X.i3d_mappings(path, names)
    print(f"droneTablet: {path}")
    print(mappings)
    C.write_mappings(os.path.join(out, "droneTablet.xml"), found, names)
    C.store_image(root, os.path.join(out, "store_droneTablet.dds"), os.path.join(WORK, "store_droneTablet.png"))


def set_relay_fold(t):
    """Náhled složení tyče jako SprayDroneRelay.applyProgress (t = 1 složeno)."""
    bpy.data.objects["relayCollar"].location = (0, 0, COLLAR_Z + (COLLAR_FOLDED_Z - COLLAR_Z) * t)
    bpy.data.objects["relayMast"].location = (0, 0, -MAST_FOLD * t)
    for node, (_, angle) in RELAY_NODES.items():
        o = bpy.data.objects[node]
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = Matrix.Rotation(math.radians(angle * t), 4, RELAY_TANGENTS[node]).to_quaternion()
    bpy.data.objects["relayLed"].hide_render = t > 0
    bpy.context.view_layer.update()


def relay_previews(name):
    """Náhledy do tmp/relayDir/: rozloženo zepředu (čelo panelu), zezadu, z boku a shora, napůl a složeno."""
    import build_drone_case as DC
    work = os.path.join(PROJECT, "tmp", "relayDir")
    os.makedirs(work, exist_ok=True)
    DC.render(os.path.join(work, f"{name}_front.png"), X.STORE_VIEW_DIR, res=700)
    DC.render(os.path.join(work, f"{name}_back.png"), Vector((-0.6, 0.75, 0.3)), res=700)
    DC.render(os.path.join(work, f"{name}_side.png"), Vector((1.0, 0.0, 0.08)), res=700)
    DC.render(os.path.join(work, f"{name}_top.png"), Vector((0.02, -0.05, 1.0)), res=700)
    set_relay_fold(0.5)
    DC.render(os.path.join(work, f"{name}_half.png"), X.STORE_VIEW_DIR, res=700)
    set_relay_fold(1.0)
    DC.render(os.path.join(work, f"{name}_folded.png"), X.STORE_VIEW_DIR, res=700)
    DC.render(os.path.join(work, f"{name}_folded_side.png"), Vector((1.0, 0.0, 0.08)), res=700)
    set_relay_fold(0.0)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    os.makedirs(WORK, exist_ok=True)
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not only or "relay" in only:
        export_item("relayPole", build_relay(), "relay")
    if "relayDir" in only:
        RELAY_NODES.clear()
        export_item("relayPoleDirectional", build_relay(directional=True), "relay")
        relay_previews("relayPoleDirectional")
    if not only or "tablet" in only:
        export_tablet(build_tablet())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
