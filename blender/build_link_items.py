"""Relé tyč se stativem a tablet (mobilní vysílačka) jako herní objekty typu pallet (jako kanystry):
objects/relay/relayPole.i3d, objects/tablet/droneTablet.i3d a ikony obchodu. Samostatný skript nad prázdnou scénou:

    blender.exe -b --python blender\\build_link_items.py [-- relay | tablet]

Pomocné funkce (kolizní kvádry, export, zápis i3dMappings, ikona obchodu) se berou z build_canister.py. Relé je skládací stativ
(nohy na posuvné objímce, vzpěry, teleskopický stožár, skříňka rádia, sektorová anténa). Pravidla objektů (XML) jsou ručně.
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

import addon_utils
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_canister as C  # noqa: E402
import export_middle_mod as X  # noqa: E402
import sdt_parts as P  # noqa: E402

PROJECT = os.path.dirname(HERE)
MOD = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects")
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
# bateriový box pod skříňkou rádia (strana +Y). Odsazený od stožáru tak, aby složená noha 1 (visí podél stožáru na +Y, y do
# 0,056 m v té výšce) a objímka (jezdí po stožáru do z 0,975) prošly za ním; drží ho jen třmen nad složenou objímkou.
BATTERY_BOX = (-0.09, 0.09, 0.062, 0.162, 0.76, 0.98)
BATTERY_LEDS = 5                 # svisle zdola: červená, 2× oranžová, 2× zelená (relayBatteryLed0..4)
CAMERA_TARGET = (0.0, 0.0, 1.3)  # střed otáčení kamery po nástupu (relayCameraRot)
EXIT_POINT = (0.0, -1.0, 0.0)    # výstup na straně bez boxu, mezi nohama 2 a 3
# barevné diody baterie: obyčejný lesklý plast v barvě diody (staticLight_vertex chce data, která tvary tyče nemají -
# hra pak hlásí „Failed to create Graphics Pipeline State“)
RELAY_LED_MATERIALS = {"SDT_RelayLedRed": (0.90, 0.04, 0.02), "SDT_RelayLedOrange": (0.90, 0.35, 0.02),
                       "SDT_RelayLedGreen": (0.05, 0.80, 0.10)}
for _name, _rgb in RELAY_LED_MATERIALS.items():
    P.MATERIALS.setdefault(_name, (_rgb, 0.0, 0.2))
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


def build_relay():
    """Skládací stativ jako na světla: nohy visí z posuvné objímky, vzpěry vedou od pevného kroužku dole k nohám. Při
    složení objímka (relayCollar) vyjede nahoru a nohy se přiklopí dolů ke stožáru; teleskopická část (relayMast) se
    sektorovou anténou se zasune. Délka vzpěr je dopočítaná tak, aby seděla v obou krajních polohách."""
    root, cols = _reset("relayPole")
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
        P.chamfer_box("RadioBox", -0.10, 0.10, 0.03, 0.11, 1.02, 1.18, "SDT_PaintYellow", 0.008),
        P.box("RadioLid", -0.102, 0.102, 0.028, 0.112, 1.175, 1.185, "SDT_PaintDark"),
        P.box("RadioBandLow", -0.03, 0.03, -0.024, 0.03, 1.04, 1.055, "SDT_Steel"),
        P.box("RadioBandHigh", -0.03, 0.03, -0.024, 0.03, 1.145, 1.16, "SDT_Steel"),
        P.cylinder_x("RadioGland", (0.06, 0.07, 1.025), 0.008, 0.02, "SDT_Rubber", segments=10),
        P.box("RadioLabel", -0.06, 0.06, 0.1105, 0.112, 1.08, 1.14, "SDT_PaintWhite"),
    ]
    m = P.merge("relayPole_vis", fixed)
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

    # teleskopická část: dvě sekce, objímka mezi nimi, sektorová anténa na držácích a krytka
    mast = _pivot("relayMast", (0, 0, 0), root)
    top = [
        P.tube("MastMid", (0, 0, 1.22), (0, 0, 1.90), 0.016, "SDT_Alu", segments=14),
        P.cylinder_z("MidClamp", (0, 0, 1.90), 0.022, 0.04, "SDT_Frame", segments=14),
        P.box("MidClampLever", 0.022, 0.06, -0.006, 0.006, 1.89, 1.91, "SDT_Rubber"),
        P.tube("MastTop", (0, 0, 1.90), (0, 0, 2.42), 0.012, "SDT_Alu", segments=12),
        P.cylinder_z("MastCap", (0, 0, 2.43), 0.014, 0.02, "SDT_Rubber", segments=12),
        P.chamfer_box("Panel", -0.065, 0.065, -0.13, -0.07, 1.97, 2.32, "SDT_PaintWhite", 0.01),
        P.box("PanelArmLow", -0.012, 0.012, -0.07, 0.0, 2.01, 2.03, "SDT_Steel"),
        P.box("PanelArmHigh", -0.012, 0.012, -0.07, 0.0, 2.26, 2.28, "SDT_Steel"),
        P.cylinder_z("PanelClampLow", (0, 0, 2.02), 0.018, 0.03, "SDT_Steel", segments=12),
        P.cylinder_z("PanelClampHigh", (0, 0, 2.27), 0.018, 0.03, "SDT_Steel", segments=12),
        P.cylinder_z("PanelPlug", (0, -0.10, 1.96), 0.008, 0.02, "SDT_Rubber", segments=10),
    ]
    mt = P.merge("relayMast_vis", top)
    C.props(mt, clipDistance=100.0)
    _attach([mt], mast)
    led = P.box("relayLed", -0.008, 0.008, 0.112, 0.116, 1.148, 1.164, "SDT_LedGreen")
    led.parent = root
    led.matrix_parent_inverse = Matrix.Identity(4)
    C.props(led, clipDistance=40.0)
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
    parts = [P.chamfer_box("Body", -w, w, -h, h, 0.0, zb, "SDT_Plastic", 0.006),
             P.box("BezelL", -w + 0.004, -sw, -h + 0.004, h - 0.004, zb - 0.001, t, "SDT_Plastic"),
             P.box("BezelR", sw, w - 0.004, -h + 0.004, h - 0.004, zb - 0.001, t, "SDT_Plastic"),
             P.box("BezelB", -sw, sw, -h + 0.004, -sh, zb - 0.001, t, "SDT_Plastic"),
             P.box("BezelT", -sw, sw, sh, h - 0.004, zb - 0.001, t, "SDT_Plastic")]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0, x1 = (w - 0.025, w + 0.004) if sx > 0 else (-w - 0.004, -w + 0.025)
            y0, y1 = (h - 0.025, h + 0.004) if sy > 0 else (-h - 0.004, -h + 0.025)
            parts.append(P.chamfer_box(f"Corner{sx}{sy}", x0, x1, y0, y1, -0.002, t + 0.003, "SDT_Rubber", 0.006))
    # vypnutý displej (tmavé sklo) je součást těla; svítící obsah (podsvícená plocha a logo designu) je samostatný uzel
    # tabletScreenOn 1 mm nad ním, skript ho skrytím zhasne
    zs = zb + 0.0005
    parts.append(P.box("Screen", -sw, sw, -sh, sh, zb - 0.0005, zs, "SDT_ScreenOff"))
    on = [P.box("Backlight", -sw, sw, -sh, sh, zs + 0.001, zs + 0.0013, "SDT_Screen")]
    parts += [P.cylinder_z("Camera", (0.0, -0.081, t), 0.003, 0.001, "SDT_Screen", segments=10),
              P.box("PowerButton", w, w + 0.004, 0.03, 0.05, 0.008, 0.016, "SDT_Rubber"),
              P.box("VolumeButton", w, w + 0.004, -0.02, 0.01, 0.008, 0.016, "SDT_Rubber"),
              P.box("Grip", -0.10, 0.10, -0.06, 0.06, -0.004, 0.0, "SDT_Rubber")]
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
        for tag, fname in (("Texture", texture), ("Normalmap", X.BASE_MAPS["Normalmap"]),
                           ("Glossmap", "$data/shared/default_vmask.png")):
            ET.SubElement(mat, tag, fileId=file_id(fname))
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")


def write_relay_block(xml_path):
    """Blok <sprayDroneRelay> (nohy: osa a úhel sklopení, vysouvací část stožáru, kontrolka) před <i3dMappings>."""
    lines = ["    <sprayDroneRelay>"]
    for node, (axis, angle) in RELAY_NODES.items():
        lines.append('        <leg node="%s" axis="%.4f %.4f %.4f" angle="%.2f"/>' % (node, *axis, angle))
    lines.append('        <slide node="relayCollar" foldedTrans="0 %g 0"/>' % round(COLLAR_FOLDED_Z - COLLAR_Z, 4))
    lines.append('        <mast node="relayMast" foldedTrans="0 %g 0"/>' % -MAST_FOLD)
    lines.append('        <led node="relayLed"/>')
    for i in range(BATTERY_LEDS):
        lines.append(f'        <batteryLed node="relayBatteryLed{i}"/>')
    lines.append("    </sprayDroneRelay>")
    lines.append("")
    text = open(xml_path, encoding="utf-8").read()
    a, b = text.find("    <sprayDroneRelay>"), text.find("</sprayDroneRelay>")
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
    if name == "relayPole":
        names += [f"relay{part}{k}" for part in ("Leg", "Strut") for k in (1, 2, 3)] + ["relayCollar", "relayMast", "relayLed"]
        names += [f"relayBatteryLed{i}" for i in range(BATTERY_LEDS)]
        names += ["relayCameraRot", "relayCamera", "relayExitPoint", "exactFillRootNode"]
    mappings, found = X.i3d_mappings(path, names)
    print(f"{name}: {path}")
    print(mappings)
    C.write_mappings(os.path.join(out, f"{name}.xml"), found, names)
    if name == "relayPole":
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


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    os.makedirs(WORK, exist_ok=True)
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not only or "relay" in only:
        export_item("relayPole", build_relay(), "relay")
    if not only or "tablet" in only:
        export_tablet(build_tablet())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
