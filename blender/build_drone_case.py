"""Přenosné sady dronů v kufru (docs/PLAN-airasi-kufr.md F2, F3; návrh uzlů docs/NAVRH-kufr-modely.md) a baterie jako předměty:

    objects/droneCase/scanCase.i3d      skenovací sada: kufr 0,60 x 0,42 x 0,24 m, dron třídy Mavic 3 Multispectral (prefix Drone_C_)
    objects/droneCase/samplerCase.i3d   AIRASI: kufr 1,15 x 0,75 x 0,55 m, vzorkovací dron na lyžinách se sondou pod trupem (prefix Drone_P_);
                                        víko o 180° (crate_lid), celé ho vyplňuje bedna na vzorky, zavřené visí bedna nad dronem
    objects/battery/battery{S,M,L,C,P}.i3d  baterie jako předmět (S/M/L = baterie vleků z sdt_parts.battery, C/P = baterie kufrových dronů)

Samostatný skript nad prázdnou scénou (jako build_drone_items.py); XML předmětů nepíše, i3dMappings a hodnoty pro blok <drone>
vypisuje do out/case_preview/*.txt:

    blender.exe -b --python blender\\build_drone_case.py [-- scanCase samplerCase batteries]

Dron v kufru má stejnou strukturu uzlů jako drony na plošině vleku (export_middle_mod.drone_nodes): <prefix>Root -> <prefix>Tilt
(bez natočení, skript do něj píše náklon) -> trup, <prefix>ArmPivot_i (kloub ramene, otáčí se kolem svislé osy) -> rameno, LED,
<prefix>Rotor_iTop (bez natočení vůči kloubu, skript ho točí kolem Y) -> <prefix>Blade_iTop{0,1} (skládací list) -> _Tip.
Dron se staví nosem po +X, pak se díly pod Tilt otočí nosem na i3d +Z (Blender -Y) a kořen <prefix>Root dostane natočení
+90° kolem svislé osy, takže v kufru leží nosem podél delší strany. Kufr se staví ZAVŘENÝ (víko caseLid natočení 0).

Otevření (animace víka v XML, blok vypisuje skript do *_export.txt): víko se otevře, ze zapuštění v pěně víka se vyndá složená
přistávací podložka casePad, položí se na zem vedle kufru (strana -X) a rozevře, droneCarrier přenese dron z pěny na střed H
a teprve pak se rozloží ramena (sprayDrone#trailerFoldEnd). Domov dronu je rodič kořene dronu, tedy droneCarrier.
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_canister as C  # noqa: E402
import build_drone as D  # noqa: E402
import build_link_items as LI  # noqa: E402
import export_middle_mod as X  # noqa: E402
import sdt_parts as P  # noqa: E402

PROJECT = os.path.dirname(HERE)
MOD_OBJ = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects")
OUT_CASE = os.path.join(MOD_OBJ, "droneCase")
OUT_BAT = os.path.join(MOD_OBJ, "battery")
WORK = os.path.join(PROJECT, "out", "case_preview")
TMP_SAMPLER = os.path.join(PROJECT, "tmp", "sampler", "v3")
BLEND = os.path.join(HERE, "spraydrone_drone_case.blend")
DECAL_TEXTURE_REL = "../../vehicles/sprayDroneTrailerMiddle/textures/sdt_decals.dds"

# materiály: dronové z build_trailer (Drone_*, Carbon, …) musí být v P.MATERIALS, jinak je LI.shader_materials nepřevede
for _n in ("Drone_Grey", "Drone_GreyDark", "Drone_White", "Drone_Accent_A", "Carbon", "Glass_Dark", "Prop_Blade", "Prop_Tip"):
    P.MATERIALS.setdefault(_n, D.parts.MATERIALS[_n])
NEW_MATERIALS = {
    "SDT_CaseShell": (((0.075, 0.078, 0.082), 0.0, 0.55), ("plasticGraniteGrainSmall", (0.062, 0.065, 0.07), {})),
    "SDT_CaseFoam": (((0.018, 0.018, 0.02), 0.0, 0.95), ("plasticPainted", (0.016, 0.016, 0.018), {"smoothnessScale": "0.1"})),
    "SDT_CaseAccentRed": (((0.60, 0.03, 0.06), 0.0, 0.4), ("calibratedPaint", (0.58, 0.02, 0.05), {})),
    "SDT_SoilJar": (((0.20, 0.13, 0.07), 0.0, 0.5), ("plasticPainted", (0.20, 0.13, 0.07), {"clearCoatIntensity": "0.6",
                                                                                           "clearCoatSmoothness": "0.8"})),
}
for _n, (_blender, _game) in NEW_MATERIALS.items():
    P.MATERIALS.setdefault(_n, _blender)
    X.MATERIAL_MAP.setdefault(_n, _game)

BLACK, GREY, GREY_DARK, WHITE = D.BLACK, D.GREY, D.GREY_DARK, D.WHITE
GROUP_FILL_ROOT, MASK_FILL_ROOT = LI.GROUP_FILL_ROOT, LI.MASK_FILL_ROOT
LED_ON = "SDT_RelayLedGreen"
LED_OFF = "SDT_LedLensOff"
ROTOR_DIRECTIONS = X.ROTOR_DIRECTIONS
BLINKING_LEDS = X.BLINKING_LEDS

# ------------------------------------------------------------------------------------------------ parametry

# body: průřezy trupu (x, půlšířka, spodek, vršek) od nosu (+X) dozadu; front / rear: kloub předního / zadního ramene (x, |y|, z);
# span: rozteč motorů rozloženého dronu (|x|, |y|); fold_y: |y| osy motoru složeného ramene; blade: délka, poloměr náboje,
# tětiva u kořene a u špičky, tloušťka; tilt_z: kloub náklonu nad zemí; battery_at: střed spodku baterie v trupu
DRONES = {
    "C": dict(prefix="Drone_C_", name="sken (Mavic 3M)",
              body=((0.106, 0.026, 0.056, 0.084), (0.094, 0.040, 0.045, 0.094), (0.055, 0.047, 0.038, 0.100),
                    (-0.050, 0.047, 0.038, 0.100), (-0.090, 0.042, 0.042, 0.097), (-0.104, 0.030, 0.050, 0.090)),
              body_mat=GREY_DARK, front=(0.055, 0.046, 0.088), rear=(-0.062, 0.044, 0.052), span=(0.13, 0.135),
              fold_y=0.067, arm_r=0.0065, arm_box=True, arm_mat=GREY_DARK, motor_r=0.0165, motor_h=0.017, motor_mat=GREY_DARK,
              blade=(0.118, 0.010, 0.022, 0.011, 0.0028), led_r=0.0045, tilt_z=0.07, battery="C",
              battery_at=(-0.056, 0.0, 0.060)),
    # AIRASI ~ těžší zemědělský quad (rozvor po úhlopříčce ~1,05 m, vrtule 22"): trup nad pevnými lyžinami ve výšce ~0,2 m
    "P": dict(prefix="Drone_P_", name="AIRASI (vzorkovač)",
              body=((0.245, 0.070, 0.225, 0.285), (0.215, 0.105, 0.205, 0.300), (0.120, 0.120, 0.196, 0.308),
                    (-0.130, 0.118, 0.198, 0.305), (-0.215, 0.098, 0.206, 0.296), (-0.240, 0.070, 0.220, 0.285)),
              body_mat=WHITE, front=(0.130, 0.115, 0.300), rear=(-0.130, 0.115, 0.248), span=(0.375, 0.370),
              fold_y=0.190, arm_r=0.018, arm_box=False, arm_mat="Carbon", motor_r=0.045, motor_h=0.042, motor_mat=WHITE,
              blade=(0.27, 0.024, 0.054, 0.027, 0.0075), led_r=0.0095, tilt_z=0.25, battery="P",
              battery_at=(-0.075, 0.0, 0.290)),
}
# sonda AIRASI (jako odběrové drony s půdním vrtákem pod trupem): ocelová odběrová trubka v pouzdru s pohonem pod trupem, horní
# konec schovaný v hlavě nad hřbetem. Uzel droneProbe (rodič Tilt) skript posune o PROBE_TRAVEL dolů (−Y v i3d); na lyžinách
# (kořen SAMPLER_HEIGHT nad terénem) pak hrot sahá ~0,2 m pod povrch, horní konec trubky zůstává v pouzdru.
PROBE_X = 0.06
PROBE_R = 0.0105
PROBE_Z = (0.030, 0.350)    # hrot a horní konec trubky v zasunutém stavu (souřadnice dronu, zem = 0)
PROBE_TRAVEL = 0.25
PROBE_HOUSING = (0.065, 0.200)
# pevné lyžiny: dvě trubky podél trupu (|y|, půldélka, poloměr), na každé dvě vzpěry k trupu
SKIDS = dict(y=0.165, half=0.21, r=0.011, strut_x=0.13, strut_top=(0.10, 0.085, 0.205))
SAMPLER_HEIGHT = 0.02       # sampler#height: kořen (lyžiny) při odběru nad terénem
# krabička na vzorek (d podél nosu / délky kufru, š, v), stejná v dronu i v přihrádce kufru; počátek uprostřed dna
SAMPLE_BOX = (0.120, 0.095, 0.090)
# dron nese dvě krabičky za sebou v kazetě pod trupem mezi pouzdrem sondy a zádí (středy x, z dna); vedle sebe by se nevešly mezi
# vzpěry lyžin
DRONE_BOXES = ((-0.055, -0.185), 0.094)
BLADE_FOLD_SPREAD = 2.0   # složené listy míří po rameni ven, rozevřené o ±2°; rozložené napříč ramene (±90°)
LID_OPEN_DEG = -110.0     # víko kufru: kolem osy X pantu (i3d stejně), záporně = nahoru a dozadu
SAMPLE_LID_OPEN_DEG = -100.0

# přistávací podložka (pružinová obruč s potahem jako skládací podložky pro DJI): rozložená leží na zemi vedle kufru na straně -X
# (zásuvka s kabelem je na +X, víko jde dozadu), složená (obruč stočená do tří vrstev = třetina průměru, trojitá tloušťka) leží
# zapuštěná v pěně víka. PAD_LIFT = o kolik se při vyndání odtáhne od víka, PAD_HIGH = výška nad zemí, ze které se spouští.
PAD_TH = 0.003
PAD_FOLD_SCALE = 1.0 / 3.0
PAD_FOLD_THICK = 3.0
PAD_LIFT = 0.08
PAD_HIGH = 0.12
DRONE_LIFT = 0.04         # dron se přenáší s lyžinami tolik nad okrajem spodku kufru
DRONE_SETTLE = 0.002      # posledních pár mm dosednutí během rozkládání ramen (viz CASE_ANIM)
# animace víka (Foldable, čas 0 = otevřeno, 1 = zavřeno; tady ve směru zavírání, otevírání jde pozpátku) jako podíl délky
# anim_s: ramena se skládají v 0–0,2 (sprayDrone#trailerFoldEnd), dron se zvedne z podložky, přenese nad pěnu a spustí do výřezu,
# podložka se složí, zvedne, přenese k víku a zasune do pěny víka, víko se zavře. Část „arms“ na droneCarrier dosedá o DRONE_SETTLE,
# aby animace v tom čase běžela (AnimatedVehicle jinak při rozkládání skočí rovnou na čas 0 a Foldable hlásí rozloženo dřív).
CASE_ANIM = dict(arms=(0.0, 0.20), lift=(0.20, 0.28), carry=(0.28, 0.43), lower=(0.43, 0.50), padFold=(0.50, 0.58),
                 padUp=(0.58, 0.63), padSwing=(0.63, 0.70), padIn=(0.70, 0.75), lid=(0.75, 1.0))
# kufr na dvě poloviny (víko 180°): podložka se z víka ležícího za kufrem zvedne nad kufr, přenese nad místo vedle (-X) a teprve
# tam spustí, ať nepřejede nad dronem v pěně
CASE_ANIM_FLAT = dict(CASE_ANIM, padSwing=(0.63, 0.67), padDrop=(0.67, 0.70))
# kufr s bednou přes celé víko (crate_lid): víko otevřené o 180° leží za kufrem po celou dobu rozložení, složená podložka se
# zasouvá do štěrbiny pod bednou z čela ležícího víka -X (zvednout, přenést k čelu víka, spustit na výšku štěrbiny, zasunout)
# a teprve s podložkou uvnitř se víko zavře (bedna se přetočí nad dron v pěně)
CASE_ANIM_CRATE = dict(arms=(0.0, 0.20), lift=(0.20, 0.28), carry=(0.28, 0.44), lower=(0.44, 0.52), padFold=(0.52, 0.60),
                       padUp=(0.60, 0.65), padSwing=(0.65, 0.73), padDrop=(0.73, 0.76), padIn=(0.76, 0.82), lid=(0.82, 1.0))
PAD_SLOT_TH = 0.016       # výška štěrbiny na podložku pod bednou (složená podložka ~0,01 m)
LID_CLEARANCE_MIN = 0.010  # nejmenší vůle zavřeného víka (bedna, krabičky, podložka) nad obsahem spodku (dron, baterie, pěna)

# batteries_xy: šachty v pěně (1 = caseBatterySlot, 2 = caseBatterySlot2). lid_open: víko (stupně kolem X pantu); -180 = kufr na
# dvě poloviny: pant v půlce výšky (hinge_z) a hinge_gap za zadní stěnou, otevřené víko leží vnitřkem nahoru na zemi za kufrem.
# sample_box (x, y v ZAVŘENÉM víku, d, š, v): bednička na vzorky ve víkové polovině. pad_store (x, y v zavřeném víku): složená
# podložka v pěně víka, pad_flip = uložená lícem dolů (po otevření víka o 180° leží lícem nahoru).
CASES = {
    "scanCase": dict(size=(0.60, 0.42, 0.24), base_h=0.15, r=0.040, wall=0.006, accent="SDT_CaseAccentRed", drone="C",
                     drone_xy=(0.0, 0.065), batteries_xy=((-0.08, -0.120), (-0.215, -0.120)), props_xy=(0.12, -0.120), mass=12.0,
                     pad_d=0.90, pad_gap=0.06, anim_s=5.0),
    # sample_box tady: (x, y v zavřeném víku, d, š, v) bedny s mřížkou SAMPLE_GRID přihrádek (sloupce podél délky, řady), bez
    # vlastního víčka; crate_lid = bedna vyplňuje celé víko (otevřené o 180° leží za kufrem), podložka ve štěrbině pod ní.
    # Výška 0,55 m: zavřená bedna s krabičkami (0,094 m pod dnem bedny) musí projít nad složeným dronem (~0,40 m nade dnem
    # kufru, sloupek GNSS, hlava sondy, motory); hinge_z ~ polovina výšky, ať otevřené víko leží vrchem na zemi
    "samplerCase": dict(size=(1.15, 0.75, 0.55), base_h=0.30, r=0.060, wall=0.008, accent="SDT_GenOrange", drone="P",
                        drone_xy=(0.0, 0.100), batteries_xy=((0.12, -0.268), (0.36, -0.268)),
                        sample_box=(0.0, 0.0, 1.060, 0.660, 0.072), lid_open=-180.0, crate_lid=True, hinge_z=0.278,
                        hinge_gap=0.014, pad_flip=True, pocket_floor=0.004, mass=32.0, pad_d=1.60, pad_gap=0.08, anim_s=6.0),
}
SAMPLE_GRID = (6, 4)


def lid_open_deg(cfg):
    return cfg.get("lid_open", LID_OPEN_DEG)


def case_anim_times(cfg):
    if cfg.get("crate_lid"):
        return CASE_ANIM_CRATE
    return CASE_ANIM_FLAT if cfg.get("pad_flip") else CASE_ANIM


NUM_BOX_SAMPLES = SAMPLE_GRID[0] * SAMPLE_GRID[1]
NUM_DRONE_BOXES = 2

# baterie: S/M/L tvarem z sdt_parts.battery (shodné s bateriemi ve vlecích), C/P vlastní (malé, kufrové drony)
SMALL_BATTERY = {"C": dict(size=(0.115, 0.075, 0.045), band="SDT_ValveBlue", handle=False),
                 "P": dict(size=(0.19, 0.095, 0.060), band="SDT_GenOrange", handle=True)}
BATTERY_MASS = {"S": 6.6, "M": 12.1, "L": 14.7, "C": 0.35, "P": 1.1}

# ------------------------------------------------------------------------------------------------ pomocné


def scene_coll():
    return bpy.context.scene.collection


def new_empty(name, parent=None, matrix=None, size=0.03):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    scene_coll().objects.link(e)
    if parent is not None:
        e.parent = parent
        e.matrix_parent_inverse = Matrix.Identity(4)
    e.matrix_basis = matrix if matrix is not None else Matrix.Identity(4)
    return e


def adopt(obj, parent):
    """Zavěsí obj pod parent se zachovanou polohou ve světě."""
    bpy.context.view_layer.update()
    w = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = parent.matrix_world.inverted() @ w
    return obj


def attach_local(obj, parent, matrix=None):
    """Zavěsí obj pod parent s lokální maticí (výchozí jednotková): geometrie je v souřadnicích rodiče."""
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = matrix if matrix is not None else Matrix.Identity(4)
    return obj


def mk(m, name):
    """D.Mesh -> objekt (krabicové UV pro detailní textury vehicleShaderu)."""
    m.bm.normal_update()
    P._box_uv(m.bm)
    return m.build(scene_coll(), name)


def join(name, objs, parent, local=False):
    """Spojí meshe (i vícemateriálové) do jednoho objektu pod parent, vrcholy v souřadnicích rodiče. local = díly už jsou
    postavené v souřadnicích rodiče (kolem počátku scény)."""
    bpy.context.view_layer.update()
    inv = Matrix.Identity(4) if local else parent.matrix_world.inverted()
    bm = bmesh.new()
    mats = []
    for o in objs:
        me = o.data.copy()
        me.transform(inv @ o.matrix_world)
        remap = []
        for mt in me.materials:
            if mt not in mats:
                mats.append(mt)
            remap.append(mats.index(mt))
        n = len(bm.faces)
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n:]:
            f.material_index = remap[f.material_index] if remap else 0
        bpy.data.meshes.remove(me)
    for o in objs:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    scene_coll().objects.link(obj)
    attach_local(obj, parent)
    return obj


def boolean_cut(obj, cutters):
    """Odečte cuttery od obj (modifikátor Boolean, vyhodnocený mesh) a cuttery smaže."""
    for c in cutters:
        mod = obj.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = c
        solvers = [i.identifier for i in mod.bl_rna.properties["solver"].enum_items]
        mod.solver = "EXACT" if "EXACT" in solvers else solvers[0]
        c.hide_render = True
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    bpy.data.meshes.remove(old)
    for c in cutters:
        data = c.data
        bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.meshes.remove(data)
    return obj


def rrect_shell(name, w, h, r, profile, mat, seg=5):
    """Skořepina kolem zaobleného obdélníku (půlrozměry w, h, poloměr rohů r): uzavřený průřez profile = [(odsazení ven, z)]
    obíhá dokola (vnější líc nahoru, vnitřní dolů), každý bod je soustředný zaoblený obdélník. Rovnoběžné odsazení drží
    tloušťku stěny i v rozích."""
    bm = bmesh.new()
    rings = [[bm.verts.new((x, y, z)) for x, y in LI._rrect_path(w + d, h + d, max(r + d, 0.002), seg)] for d, z in profile]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:] + rings[:1]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return P._finish(name, bm, Matrix.Identity(4), mat, smooth_quads=True)


SHARP_DEG = 50.0   # hrana mezi plochami ostřejší než tohle zůstane ostrá (kvádry, čela válců); zkosení a fazety se vyhladí


def smooth_normals(obj):
    """Hladké stínování s váženými normálami: plochy, které už byly hladké (trubky, lofty), zůstanou hladké mezi sebou;
    ostatní hrany se vyhladí, když jsou mírnější než SHARP_DEG. Normály vážené plochou drží velké stěny rovné a zkosení
    a zaoblení přebírají přechod, takže hrany vypadají oblé místo fazetované (ve hře jde normála s vrcholem do i3d)."""
    me = obj.data
    if not me.polygons:
        return
    bm = bmesh.new()
    bm.from_mesh(me)
    limit = math.radians(SHARP_DEG)
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f1, f2 = e.link_faces
        e.smooth = (f1.smooth and f2.smooth) or e.calc_face_angle(math.pi) < limit
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    mod = obj.modifiers.new("wn", "WEIGHTED_NORMAL")
    mod.keep_sharp = True
    mod.weight = 50
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear()
    old = obj.data
    old_name = old.name
    obj.data = new
    if old.users == 0:
        bpy.data.meshes.remove(old)
    new.name = old_name


def rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Z")


def wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def mesh_bbox(objs):
    # vrcholy, ne bound_box: obálka natočeného dílu (složené nohy AIRASI) by přečnívala
    pts = [o.matrix_world @ v.co for o in objs if o.type == "MESH" for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def led_vertex_color(obj, rgb):
    attr = obj.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for item in attr.data:
        item.color_srgb = (*rgb, 1.0)
    obj.data.color_attributes.render_color_index = 0


# ------------------------------------------------------------------------------------------------ dron


def blade_rings(length, r0, chord_root, chord_tip, thick, z_off, grow=1.0, ts=D.BLADE_STATIONS):
    """Průřezy listu podél +X od náboje (r0) ke špičce, profil a zkrut jako build_drone._blade_ring, měřítko malé vrtule."""
    out = []
    for t in ts:
        shape = D.BLADE_SHAPE[-1]
        for i in range(len(D.BLADE_STATIONS) - 1):
            if D.BLADE_STATIONS[i] <= t <= D.BLADE_STATIONS[i + 1]:
                u = (t - D.BLADE_STATIONS[i]) / (D.BLADE_STATIONS[i + 1] - D.BLADE_STATIONS[i])
                shape = D.BLADE_SHAPE[i] + (D.BLADE_SHAPE[i + 1] - D.BLADE_SHAPE[i]) * u
                break
        r = r0 + (length - r0) * t
        chord = (chord_root + (chord_tip - chord_root) * t ** 0.9) * shape * grow
        th = thick * (1.0 - 0.35 * t) * grow
        twist = math.radians(10) * (1.0 - t)
        pts = []
        for sgn, us in ((1, D.BLADE_PROFILE_U), (-1, D.BLADE_PROFILE_U[-2:0:-1])):
            for u in us:
                half = max(0.0003, th / 2 * D._naca(u) / D._NACA_MAX)
                pts.append((chord * (0.5 - u), sgn * half + th * 0.6 * 4 * u * (1 - u) * 0.5))
        out.append([Vector((r, cx * math.cos(twist) - cz * math.sin(twist),
                            cx * math.sin(twist) + cz * math.cos(twist) + z_off)) for cx, cz in pts])
    return out


def fuselage(m, stations, mat):
    """Trup vytažený podél X přes zaoblené průřezy (x, půlšířka, spodek, vršek)."""
    rings = []
    for x, hy, z0, z1 in stations:
        hz, zc = (z1 - z0) / 2, (z1 + z0) / 2
        ring = D.rounded_ring(0, 0, 0, hy, hz, 0.42 * min(hy, hz), arc=4)
        rings.append([Vector((x, p.x, zc + p.y)) for p in ring])
    m.loft(rings, mat, smooth=True)


def sample_box(name, parent, full):
    """Krabička na vzorek pod parent (počátek uprostřed dna, rozměry SAMPLE_BOX). Prázdná: bílá, otevřená, bez víčka, uvnitř
    bílá vložka v půlce výšky (hluboká krabička by ve stínu stěn vypadala černě, tedy plná). Plná: hnědá průsvitná nádoba až po
    okraj plná hlíny, zavřená červeným víčkem, bílý štítek na čele."""
    d, w, h = SAMPLE_BOX
    hx, hy = d / 2, w / 2
    t = 0.0025
    if full:
        hl = 0.010
        parts = [P.chamfer_box(f"{name}_Body", -hx, hx, -hy, hy, 0.0, h - hl, "SDT_SoilJar", 0.003),
                 P.chamfer_box(f"{name}_Lid", -hx - 0.0015, hx + 0.0015, -hy - 0.0015, hy + 0.0015, h - hl, h, "SDT_PaintRed", 0.002),
                 P.box(f"{name}_Label", -hx * 0.7, hx * 0.7, -hy - 0.0008, -hy, h * 0.25, h * 0.6, "SDT_PaintWhite")]
    else:
        parts = [P.box(f"{name}_Floor", -hx, hx, -hy, hy, 0.0, t, "SDT_PaintWhite"),
                 P.box(f"{name}_Insert", -hx + t, hx - t, -hy + t, hy - t, h * 0.45, h * 0.45 + t, "SDT_PaintWhite"),
                 P.box(f"{name}_WallA", -hx, hx, -hy, -hy + t, 0.0, h, "SDT_PaintWhite"),
                 P.box(f"{name}_WallB", -hx, hx, hy - t, hy, 0.0, h, "SDT_PaintWhite"),
                 P.box(f"{name}_WallC", -hx, -hx + t, -hy + t, hy - t, 0.0, h, "SDT_PaintWhite"),
                 P.box(f"{name}_WallD", hx - t, hx, -hy + t, hy - t, 0.0, h, "SDT_PaintWhite")]
        # obroubení okraje (závit na víčko)
        parts.append(LI.rrect_band(f"{name}_Rim", (hx + 0.0012, hy + 0.0012, 0.003), (hx - t, hy - t, 0.001), h - 0.006, h - 0.002,
                                   "SDT_PaintWhite", seg=2))
    return join(name, parts, parent, local=True)


def small_battery_parts(key, handle=None):
    """Baterie kufrového dronu (C ~ Mavic 3 Intelligent Flight Battery, P větší): zaoblený blok, žebrovaný úchop na obou bocích
    u zadního čela (-X), kontakty na čele +X, barevný pruh, na horní straně čtyři zhasnuté čočky ukazatele a tlačítko.
    P má navíc na horní straně skládací poutko. Počátek uprostřed dole. Vrací (díly, pozice diod (střed, půlrozměry))."""
    cfg = SMALL_BATTERY[key]
    lx, ly, lz = cfg["size"][0] / 2, cfg["size"][1] / 2, cfg["size"][2]
    handle = cfg["handle"] if handle is None else handle
    rr = 0.32 * ly
    parts = [LI.rrect_prism(f"bat{key}_Body", 0, 0, lx, ly, rr, 0.0, lz, "SDT_BatteryGrey", seg=4, bevel_top=0.003,
                            bevel_bottom=0.002)]
    for sy in (1, -1):
        y = sy * ly
        parts.append(P.box(f"bat{key}_Band{sy}", -lx * 0.55, lx * 0.85, min(y, y + sy * 0.0015), max(y, y + sy * 0.0015),
                           lz * 0.55, lz * 0.68, cfg["band"]))
        for i in range(5):
            x0 = -lx * 0.92 + i * lx * 0.07
            parts.append(P.box(f"bat{key}_Grip{sy}{i}", x0, x0 + lx * 0.035, min(y, y + sy * 0.0025),
                               max(y, y + sy * 0.0025), lz * 0.18, lz * 0.85, "SDT_Rubber"))
    parts.append(P.box(f"bat{key}_Contacts", lx, lx + 0.003, -ly * 0.5, ly * 0.5, lz * 0.30, lz * 0.70, "SDT_TankBlack"))
    for i in range(3):
        py = (i - 1) * ly * 0.3
        parts.append(P.box(f"bat{key}_Pin{i}", lx + 0.003, lx + 0.0045, py - 0.003, py + 0.003, lz * 0.42, lz * 0.58,
                           "SDT_Steel"))
    leds = []
    lx0 = -lx * 0.74
    parts.append(P.box(f"bat{key}_LedBezel", lx0 - 0.007, lx0 + 0.007, -ly * 0.62, ly * 0.62, lz, lz + 0.0012,
                       "SDT_TankBlack"))
    for i in range(4):
        py = (-0.45 + 0.30 * i) * ly
        hw = 0.08 * ly
        parts.append(P.box(f"bat{key}_LedOff{i}", lx0 - 0.004, lx0 + 0.004, py - hw, py + hw, lz + 0.0012, lz + 0.0020, LED_OFF))
        leds.append(((lx0, py, lz + 0.0026), (0.004, hw, 0.0006)))
    parts.append(P.cylinder_z(f"bat{key}_Button", (lx0, 0.75 * ly, lz + 0.0018), 0.0045, 0.0026, "SDT_Rubber", segments=10))
    if handle:
        for sx in (-1, 1):
            parts.append(P.chamfer_box(f"bat{key}_HandlePost{sx}", sx * lx * 0.30 - 0.008, sx * lx * 0.30 + 0.008,
                                       -0.010, 0.010, lz, lz + 0.022, "SDT_TankBlack", 0.002))
        parts.append(P.tube(f"bat{key}_HandleBar", (-lx * 0.34, 0, lz + 0.020), (lx * 0.34, 0, lz + 0.020), 0.0065,
                            "SDT_Rubber", segments=10))
    return parts, leds


def build_drone(key, parent, base):
    """Dron v kufru (složený). base = matice kořene <prefix>Root ve světě (poloha a natočení v kufru). Vrací (root, info)."""
    s = DRONES[key]
    pre = s["prefix"]
    P._root = None
    root = new_empty(pre + "Root", None, Matrix.Identity(4), 0.06)
    tilt = new_empty(pre + "Tilt", root, Matrix.Translation((0, 0, s["tilt_z"])), 0.05)
    info = {"arms": [], "blades": []}

    # --- trup a pevné díly (souřadnice dronu, nos +X, zem z = 0)
    m = D.Mesh((0, 0, 0))
    fuselage(m, s["body"], s["body_mat"])
    xs = [st[0] for st in s["body"]]
    nose_x, tail_x = max(xs), min(xs)
    if key == "C":
        # přední překážkové senzory, dvojice kamer na zádi, nohy pod trupem s gumovými patkami
        for sy in (1, -1):
            m.tube((nose_x - 0.006, sy * 0.012, 0.074), (nose_x + 0.001, sy * 0.012, 0.074), [0.0045] * 2, "Glass_Dark", segments=10)
            m.tube((tail_x - 0.002, sy * 0.014, 0.075), (tail_x + 0.006, sy * 0.014, 0.075), [0.004] * 2, "Glass_Dark", segments=10)
            for fx in (0.055, -0.072):
                m.tube((fx, sy * 0.030, 0.042), (fx + 0.004, sy * 0.034, 0.006), [0.0045, 0.0038], BLACK, segments=8)
                m.lathe(fx + 0.004, sy * 0.034, [(0.006, 0.0), (0.0065, 0.004), (0.005, 0.008)], "SDT_Rubber", segments=10)
        # sluneční senzor (DLS) na hřbetě: sloupek a bílý difuzor
        m.lathe(0.020, 0.0, [(0.011, 0.098), (0.011, 0.106), (0.010, 0.108)], BLACK, segments=14)
        m.lathe(0.020, 0.0, [(0.0095, 0.108), (0.008, 0.113), (0.004, 0.1155), (0.0005, 0.116)], WHITE, segments=14)
        # kardan s multispektrální hlavou pod nosem: držák, třmen, hlava se 4 čočkami MS a RGB uprostřed
        gx = 0.112
        m.solid((0.088, 0, 0.040), (0.012, 0.022, 0.006), BLACK, frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))),
                cut=0.004)
        for sy in (1, -1):
            m.solid((gx, sy * 0.037, 0.050), (0.010, 0.003, 0.016), BLACK,
                    frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=0.002)
        m.tube((0.098, 0, 0.044), (gx, 0, 0.044), [0.004] * 2, BLACK, segments=8)
        m.solid((gx + 0.004, 0, 0.050), (0.017, 0.033, 0.019), GREY_DARK,
                frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=0.006, ch=0.003)
        face = gx + 0.021
        for ly_, lz_, rr in ((0.0, 0.0, 0.0085), (-0.022, 0.009, 0.005), (-0.022, -0.009, 0.005), (0.022, 0.009, 0.005),
                             (0.022, -0.009, 0.005)):
            m.tube((face - 0.001, ly_, 0.050 + lz_), (face + 0.0025, ly_, 0.050 + lz_), [rr + 0.0018] * 2, BLACK, segments=12)
            m.tube((face + 0.002, ly_, 0.050 + lz_), (face + 0.0035, ly_, 0.050 + lz_), [rr] * 2, "Glass_Dark", segments=12)
        fr3 = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        for sy in (1, -1):
            # větrací mřížka na boku trupu (tmavé pole a lamely)
            m.solid((-0.010, sy * 0.0469, 0.068), (0.028, 0.0006, 0.010), BLACK, frame=fr3, cut=0.0003)
            for k in range(4):
                m.solid((-0.010, sy * 0.0474, 0.0612 + 0.0045 * k), (0.026, 0.0007, 0.0011), GREY_DARK, frame=fr3, cut=0.0004)
            # spodní senzory přistání (dvojice čoček v rámečku)
            m.tube((0.030, sy * 0.016, 0.0392), (0.030, sy * 0.016, 0.0368), [0.0062] * 2, BLACK, segments=12)
            m.tube((0.030, sy * 0.016, 0.0370), (0.030, sy * 0.016, 0.0360), [0.0045] * 2, "Glass_Dark", segments=12)
        # stavová LED na zádi pod zadními kamerami
        m.solid((tail_x - 0.0002, 0.0, 0.062), (0.0018, 0.011, 0.0022), "SDT_LampRed", frame=fr3, cut=0.0008)
    else:
        # AIRASI: šedý spodek trupu, oranžový pruh, kamera pod nosem, pevné lyžiny, pouzdro sondy s pohonem pod trupem a hlava
        # sondy nad hřbetem, kazeta na dvě krabičky pod zádí (krabičky samotné jsou uzly droneSampleBox{1,2})
        frame = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        m.paint_beyond((0, 0, 0.226), (0, 0, -1), GREY_DARK)
        m.lathe(0.200, 0.0, [(0.014, 0.206), (0.022, 0.199), (0.022, 0.190)], BLACK, segments=12)
        m.lathe(0.200, 0.0, [(0.030, 0.191), (0.034, 0.174), (0.029, 0.158), (0.006, 0.153)], BLACK, segments=16)
        m.tube((0.226, 0, 0.173), (0.235, 0, 0.173), [0.013] * 2, "Glass_Dark", segments=12)
        sk = SKIDS
        sz = sk["r"] * 1.25      # osa lyžiny: spodek gumové patky leží na zemi (z = 0 = kořen dronu)
        for sy in (1, -1):
            y = sy * sk["y"]
            m.tube((-sk["half"], y, sz), (sk["half"], y, sz), [sk["r"]] * 2, BLACK, segments=16)
            for sx in (1, -1):
                # ohnutý konec lyžiny (koleno a zvednutá špička s oblou záslepkou)
                p0, p1 = Vector((sx * sk["half"], y, sz)), Vector((sx * (sk["half"] + 0.030), y, 0.042))
                knee = Vector((sx * (sk["half"] + 0.012), y, sz + 0.004))
                m.sweep([p0 - Vector((sx * 0.006, 0, 0)), p0, knee, p1], [sk["r"], sk["r"], sk["r"] * 0.96, sk["r"] * 0.9], BLACK,
                        segments=16)
                d_ = (p1 - knee).normalized()
                m.tube(p1, p1 + d_ * 0.007, [sk["r"] * 0.9, sk["r"] * 0.8, sk["r"] * 0.55, sk["r"] * 0.12], BLACK, segments=16)
                # gumová patka se zkosenými konci (spodek drží na z = 0)
                m.tube((sx * (sk["half"] - 0.06), y, sz), (sx * (sk["half"] - 0.01), y, sz),
                       [sk["r"] * 1.06, sk["r"] * 1.25, sk["r"] * 1.25, sk["r"] * 1.25, sk["r"] * 1.25, sk["r"] * 1.06],
                       "SDT_Rubber", segments=16)
                tx, ty, tz = sk["strut_top"]
                m.tube((sx * sk["strut_x"], y, sz), (sx * tx, sy * ty, tz), [0.011, 0.009], "Carbon", segments=12)
                m.lathe(sx * sk["strut_x"], y, [(0.016, sz - 0.012), (0.016, sz + 0.014)], BLACK, segments=12)
                m.solid((sx * tx, sy * ty, tz - 0.004), (0.018, 0.014, 0.008), BLACK, frame=frame, cut=0.003)
        # pouzdro sondy: vodicí trubka s tryskou dole, pohon (šnek a motor) z boku, hlava nad hřbetem
        h0, h1 = PROBE_HOUSING
        m.lathe(PROBE_X, 0.0, [(0.016, h0 - 0.010), (0.020, h0), (0.029, h0 + 0.010), (0.029, h1 - 0.020), (0.040, h1 - 0.012),
                               (0.040, h1 + 0.004)], GREY_DARK, segments=18)
        m.lathe(PROBE_X, 0.0, [(0.0295, h0 + 0.040), (0.0295, h0 + 0.052)], "Drone_Accent_A", segments=18, cap_start=False,
                cap_end=False)
        m.solid((PROBE_X, 0.046, h1 - 0.055), (0.020, 0.017, 0.040), BLACK, frame=frame, cut=0.004)
        m.lathe(PROBE_X, 0.046, [(0.019, h1 - 0.120), (0.019, h1 - 0.095)], GREY_DARK, segments=14)
        m.lathe(PROBE_X, 0.0, [(0.026, 0.290), (0.026, 0.356), (0.021, 0.366), (0.008, 0.372), (0.0005, 0.373)], GREY_DARK,
                segments=18)
        m.lathe(PROBE_X, 0.0, [(0.0265, 0.330), (0.0265, 0.340)], "Drone_Accent_A", segments=18, cap_start=False, cap_end=False)
        # kazeta krabiček: deska pod trupem přes obě krabičky, boční vodítka a příčka mezi krabičkami
        bxs, bz_ = DRONE_BOXES
        d, w, h = SAMPLE_BOX
        top = bz_ + h
        x0, x1 = min(bxs) - d / 2, max(bxs) + d / 2
        cx_, hl = (x0 + x1) / 2, (x1 - x0) / 2
        m.solid((cx_, 0, top + 0.006), (hl + 0.012, w / 2 + 0.010, 0.006), BLACK, frame=frame, cut=0.003)
        for gy in (-(w / 2 + 0.006), w / 2 + 0.006):
            m.solid((cx_, gy, top - 0.012), (hl + 0.004, 0.003, 0.018), GREY_DARK, frame=frame, cut=0.001)
        m.solid(((bxs[0] + bxs[1]) / 2, 0, top - 0.012), (0.003, w / 2 + 0.003, 0.018), GREY_DARK, frame=frame, cut=0.001)
        for sy in (1, -1):
            m.tube((-0.10, sy * 0.1195, 0.262), (0.11, sy * 0.1195, 0.262), [0.0045] * 2, "Drone_Accent_A", segments=6)
            # větrací mřížky na hřbetě po stranách baterie (tmavé pole, bílé lamely)
            m.solid((-0.085, sy * 0.078, 0.3045), (0.060, 0.016, 0.0030), BLACK, frame=frame, cut=0.0015)
            for k in range(5):
                m.solid((-0.085, sy * (0.0655 + 0.0062 * k), 0.3066), (0.056, 0.0016, 0.0016), WHITE, frame=frame, cut=0.0006)
        # GNSS/RTK anténa na krátkém sloupku před hlavou sondy
        m.lathe(0.165, 0.0, [(0.010, 0.300), (0.010, 0.313), (0.016, 0.315)], BLACK, segments=14)
        m.lathe(0.165, 0.0, [(0.024, 0.314), (0.026, 0.318), (0.024, 0.3245), (0.016, 0.3285), (0.004, 0.330)], WHITE, segments=20)
        # radar / senzor překážek na čele a zadní světlo
        m.solid((0.2455, 0, 0.2515), (0.0018, 0.040, 0.0150), BLACK, frame=frame, cut=0.004)
        m.solid((0.2468, 0, 0.2515), (0.0010, 0.034, 0.0105), "Glass_Dark", frame=frame, cut=0.003)
        m.solid((-0.2405, 0, 0.2585), (0.0018, 0.032, 0.0050), BLACK, frame=frame, cut=0.002)
        m.solid((-0.2418, 0, 0.2585), (0.0010, 0.027, 0.0030), "SDT_LampRed", frame=frame, cut=0.0012)
    body = mk(m, pre + "Body")
    adopt(body, tilt)

    # --- baterie v trupu (samostatný uzel, ať ji skript schová, když se vytáhne)
    bx, by, bz = s["battery_at"]
    slot = new_empty(pre + "BatterySlot", None, Matrix.Translation((bx, by, bz)))
    adopt(slot, tilt)
    parts, _ = small_battery_parts(s["battery"], handle=False)
    join(pre + "Battery", parts, slot, local=True)
    info["battery"] = (bx, by, bz)

    # --- ramena
    span_x, span_y = s["span"]
    arm_r, mr = s["arm_r"], s["motor_r"]
    bl_len, hub_r, chord_root, chord_tip, thick = s["blade"]
    for idx, (sx, sy) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1)), start=1):
        front = sx > 0
        px, py, pz = s["front"] if front else s["rear"]
        py *= sy
        mx, my = sx * span_x, sy * span_y
        length = math.hypot(mx - px, my - py)
        unf = math.degrees(math.atan2(my - py, mx - px))
        a = math.degrees(math.asin((s["fold_y"] - abs(py)) / length))
        folded = sy * (180.0 - a) if front else sy * a
        delta = wrap_deg(unf - folded)
        pivot = new_empty(f"{pre}ArmPivot_{idx}", tilt, None)
        bpy.context.view_layer.update()
        pivot.matrix_basis = tilt.matrix_world.inverted() @ Matrix.Translation((px, py, pz)) @ rz(folded)

        m = D.Mesh((0, 0, 0))
        m.lathe(0, 0, [(arm_r * 1.8, -arm_r * 1.7), (arm_r * 2.1, -arm_r * 1.3), (arm_r * 2.1, arm_r * 1.3),
                       (arm_r * 1.8, arm_r * 1.7)], BLACK, segments=20)
        # šroub kloubu ramene nahoře
        m.lathe(0, 0, [(arm_r * 1.0, arm_r * 1.65), (arm_r * 1.0, arm_r * 1.9), (arm_r * 0.7, arm_r * 2.05)], GREY_DARK,
                segments=12)
        tip_x = length - mr * 0.5
        if s["arm_box"]:
            ha = (tip_x - arm_r * 1.5) / 2
            m.solid((arm_r * 1.5 + ha, 0, 0), (ha, arm_r, arm_r * 0.85), s["arm_mat"],
                    frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=arm_r * 0.45, taper=(0.8, 0.9))
        else:
            m.tube((arm_r * 1.5, 0, 0), (tip_x, 0, 0), [arm_r, arm_r * 0.97, arm_r * 0.9], s["arm_mat"], segments=16)
            m.tube((length * 0.35, 0, 0), (length * 0.42, 0, 0), [arm_r * 1.12] * 2, "Drone_Accent_A", segments=16)
        # držák motoru, motor (stator a zvon)
        m.lathe(length, 0, [(mr * 0.70, -arm_r * 1.4), (mr * 0.92, -arm_r * 0.9), (mr * 0.92, arm_r * 0.9)], BLACK, segments=16)
        z0 = arm_r * 0.9
        h = s["motor_h"]
        ms = 24 if key == "P" else 18
        m.lathe(length, 0, [(mr * 0.88, z0), (mr, z0 + 0.15 * h), (mr, z0 + 0.82 * h), (mr * 0.86, z0 + h), (mr * 0.45, z0 + h)],
                s["motor_mat"], segments=ms)
        m.lathe(length, 0, [(mr * 1.008, z0 + 0.40 * h), (mr * 1.008, z0 + 0.52 * h)], BLACK, segments=ms, cap_start=False,
                cap_end=False)
        # pouzdro LED pod ramenem u motoru
        led_x, lr = length - mr * 1.9, s["led_r"]
        m.lathe(led_x, 0, [(lr * 1.35, -arm_r * 0.4), (lr * 1.35, -arm_r - lr * 0.5), (lr * 1.05, -arm_r - lr * 0.7)], BLACK,
                segments=12, cap_start=False)
        arm = mk(m, f"{pre}Arm_{idx}")
        attach_local(arm, pivot)
        m = D.Mesh((0, 0, 0))
        m.lathe(led_x, 0, [(lr * 1.02, -arm_r - lr * 0.55), (lr * 0.95, -arm_r - lr * 0.95), (lr * 0.5, -arm_r - lr * 1.25)],
                "SDT_NavLed", segments=12, cap_start=False)
        led = mk(m, f"{pre}Led_{idx}")
        led_vertex_color(led, D.LED_COLORS[idx])
        attach_local(led, pivot)
        ldata = bpy.data.lights.new(f"{pre}LedLight_{idx}", "POINT")
        ldata.color = D.LED_COLORS[idx]
        ldata.use_shadow = False
        ldata.use_custom_distance = True
        ldata.cutoff_distance = 2.0
        ldata.energy = 2.0
        light = bpy.data.objects.new(f"{pre}LedLight_{idx}", ldata)
        scene_coll().objects.link(light)
        attach_local(light, led, Matrix.Translation((led_x, 0, -arm_r - lr * 1.3 - 0.02)))

        # rotor (bez natočení vůči kloubu) s nábojem a dvěma skládacími listy
        hub_z = z0 + h + 0.0015
        rotor = new_empty(f"{pre}Rotor_{idx}Top", pivot, Matrix.Translation((length, 0, hub_z)), 0.02)
        m = D.Mesh((0, 0, 0))
        m.lathe(0, 0, [(hub_r * 1.15, 0.0), (hub_r * 1.2, thick * 1.4), (hub_r * 0.7, thick * 2.6), (hub_r * 0.25, thick * 3.0)],
                GREY_DARK, segments=12)
        hub = mk(m, f"{pre}Hub_{idx}")
        attach_local(hub, rotor)
        for b in (0, 1):
            z_off = thick * (0.7 + 1.3 * b)
            m = D.Mesh((0, 0, 0))
            m.loft(blade_rings(bl_len, hub_r, chord_root, chord_tip, thick, z_off), "Prop_Blade", smooth=True)
            m.lathe(hub_r * 0.55, 0, [(hub_r * 0.45, z_off - thick * 0.6), (hub_r * 0.45, z_off + thick * 0.6)], GREY_DARK,
                    segments=8)
            bname = f"{pre}Blade_{idx}Top{b}"
            blade = mk(m, bname)
            fold_b = BLADE_FOLD_SPREAD if b == 0 else -BLADE_FOLD_SPREAD
            attach_local(blade, rotor, rz(fold_b))
            m = D.Mesh((0, 0, 0))
            ts = [0.89 + 0.08 * i / 3 for i in range(4)]
            m.loft(blade_rings(bl_len, hub_r, chord_root, chord_tip, thick, z_off, grow=1.05, ts=ts), "Prop_Tip", smooth=True)
            tip = mk(m, bname + "_Tip")
            attach_local(tip, blade)
            unf_b = 90.0 if b == 0 else -90.0
            info["blades"].append((bname, unf_b - fold_b))
        info["arms"].append((f"{pre}ArmPivot_{idx}", delta, length))

    # --- AIRASI: odběrová sonda (uzel droneProbe v horním konci trubky) a dvě krabičky na vzorky (prázdná / plná, skryté)
    if key == "P":
        z0, z1 = PROBE_Z
        node = new_empty("droneProbe", None, Matrix.Translation((PROBE_X, 0, z1)), 0.03)
        adopt(node, tilt)
        m = D.Mesh((0, 0, 0))
        r_ = PROBE_R
        # odběrová trubka: zesílený břit dole, ocelový dřík, ryska po 10 cm od hrotu, doraz nahoře
        m.lathe(PROBE_X, 0, [(r_ * 0.55, z0), (r_ * 1.12, z0 + 0.006), (r_ * 1.12, z0 + 0.030), (r_, z0 + 0.036)], "SDT_Steel",
                segments=14)
        m.tube((PROBE_X, 0, z0 + 0.034), (PROBE_X, 0, z1), [r_] * 2, "SDT_Steel", segments=14)
        for k in (1, 2):
            zz = z0 + 0.10 * k
            m.lathe(PROBE_X, 0, [(r_ + 0.0004, zz - 0.004), (r_ + 0.0004, zz + 0.004)], "Drone_Accent_A", segments=14,
                    cap_start=False, cap_end=False)
        m.solid((PROBE_X + r_, 0, z0 + 0.10), (0.0012, 0.0035, 0.060), BLACK,
                frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))))
        m.lathe(PROBE_X, 0, [(r_ + 0.004, z1 - 0.012), (r_ + 0.004, z1)], BLACK, segments=14)
        o = mk(m, "droneProbe_vis")
        adopt(o, node)
        bxs, bz_ = DRONE_BOXES
        for i, bx_ in enumerate(bxs, start=1):
            bn = new_empty(f"droneSampleBox{i}", None, Matrix.Translation((bx_, 0.0, bz_)), 0.02)
            adopt(bn, tilt)
            sample_box(f"droneSampleBox{i}Empty", bn, False)
            sample_box(f"droneSampleBox{i}Full", bn, True)

    # nos z +X na i3d +Z (Blender -Y); kořen pak +90°, takže ve světě zůstane +X
    bpy.context.view_layer.update()
    for c in list(tilt.children):
        c.matrix_basis = rz(-90) @ c.matrix_basis
    root.matrix_basis = base @ rz(90)
    adopt(root, parent)
    bpy.context.view_layer.update()
    return root, info


def set_drone_unfold(key, info, t, probe=True):
    """probe = vysunout se sondu AIRASI (náhled rozloženého dronu); ve hře ji vysouvá jen odběr, na podložce je zasunutá."""
    pre = DRONES[key]["prefix"]
    for name, delta, _ in info["arms"]:
        o = bpy.data.objects[name]
        o.rotation_euler.z = info["arm0"][name] + math.radians(delta) * t
    for name, delta in info["blades"]:
        o = bpy.data.objects[name]
        o.rotation_euler.z = info["blade0"][name] + math.radians(delta) * t
    if key == "P":
        bpy.data.objects["droneProbe"].location.z = info["probe0"] - (PROBE_TRAVEL * t if probe else 0.0)
    bpy.context.view_layer.update()


# ------------------------------------------------------------------------------------------------ kufr


def case_battery(key, parent, xy, floor_z, suffix=""):
    slot = new_empty("caseBatterySlot" + suffix, None, Matrix.Translation((xy[0], xy[1], floor_z)))
    adopt(slot, parent)
    parts, _ = small_battery_parts(key)
    return slot, join("caseBattery" + suffix, parts, slot, local=True)


def build_case(name):
    cfg = CASES[name]
    L_, W_, H_ = cfg["size"]
    hb, r, t = cfg["base_h"], cfg["r"], cfg["wall"]
    hx, hy = L_ / 2, W_ / 2
    accent = cfg["accent"]
    P._coll = scene_coll()
    root = C.box_object(f"{name}_main_component1", None, -hx, hx, -hy, hy, 0.0, H_, C.GROUP_ROOT, C.MASK_ROOT, dynamic=True,
                        compound=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0, clipDistance=150.0)
    P._root = root
    cols = new_empty("collisions", root)
    C.props(cols, clipDistance=10.0)
    # kolize jen zavřeného tvaru (i u kufru s bednou ve víku): otevřené víko je bez kolize jako u skenovacího kufru. Pevný tvar
    # pod ležícím víkem by u zavřeného kufru trčel za ním a pohyblivý compoundChild ve víku by fyzika neposouvala spolehlivě.
    C.box_object("floorCollision01", cols, -hx, hx, -hy, hy, 0.0, H_, C.GROUP_FLOOR, C.MASK_FLOOR, compoundChild=True,
                 staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    C.box_object("dynamicMountTrigger", root, -hx - 0.025, hx + 0.025, -hy - 0.025, hy + 0.025, 0.0, 0.04, C.GROUP_MOUNT,
                 C.MASK_MOUNT, kinematic=True, trigger=True)
    C.box_object("exactFillRootNode", root, -hx, hx, -hy, hy, 0.0, H_, GROUP_FILL_ROOT, MASK_FILL_ROOT, kinematic=True,
                 compound=True)
    rp = LI.rrect_prism
    rb = LI.rrect_band
    z_b = 0.005
    # skořepina spodku jedním průřezem: zaoblená spodní hrana, obvodové žebro u dna, zesílený lem u spáry se zkosením
    base_profile = [(-0.007, z_b), (-0.0025, z_b + 0.0012), (-0.0005, z_b + 0.004), (0.0, z_b + 0.008), (0.0, z_b + 0.016),
                    (0.0025, z_b + 0.019), (0.0025, z_b + 0.027), (0.0, z_b + 0.030), (0.0, hb - 0.017), (0.0035, hb - 0.013),
                    (0.0035, hb - 0.003), (0.0015, hb), (-t + 0.001, hb), (-t, hb - 0.0015), (-t, z_b + t)]
    big = L_ > 0.7
    kk = 1.45 if big else 1.0      # kování (zámky, madlo) velkého kufru je úměrně větší
    if big:
        # vysoký spodek: dvojice mělkých obvodových žeber v půlce výšky
        zm = hb * 0.5
        rib = [(0.0, zm - 0.022), (0.0018, zm - 0.020), (0.0018, zm - 0.012), (0.0, zm - 0.010),
               (0.0, zm + 0.010), (0.0018, zm + 0.012), (0.0018, zm + 0.020), (0.0, zm + 0.022)]
        i = next(i for i, (d, z) in enumerate(base_profile) if z > zm)
        base_profile[i:i] = rib
    vis = [
        rp("Bottom", 0, 0, hx - t + 0.001, hy - t + 0.001, r - t + 0.001, z_b, z_b + t, "SDT_CaseShell", seg=5),
        rrect_shell("Walls", hx, hy, r, base_profile, "SDT_CaseShell"),
        # těsnění ve spáře (vidět při otevřeném víku)
        rb("Gasket", (hx - 0.0015, hy - 0.0015, r - 0.0015), (hx - t + 0.0015, hy - t + 0.0015, r - t + 0.0015), hb - 0.001,
           hb + 0.0008, "SDT_Rubber", seg=5),
    ]
    for sx in (1, -1):
        for sy in (1, -1):
            vis.append(P.cylinder_z(f"Foot{sx}{sy}", (sx * (hx - 0.05), sy * (hy - 0.05), 0.0035), 0.016, 0.007, "SDT_Rubber",
                                    segments=16, radius_top=0.0145))
    # rohové chrániče spodku (zesílené rohy u dna jako u přepravních kufrů)
    gh = 0.060 if big else 0.036
    for k in range(4):
        vis.append(rb(f"CornerGuard{k}", (hx + 0.0045, hy + 0.0045, r + 0.0045), (hx - 0.001, hy - 0.001, r - 0.001), z_b + 0.001,
                      z_b + gh, "SDT_CaseShell", seg=5, corner=k, extend=0.026 if big else 0.018))
    # madlo na čele (-Y) u spáry: tvrdé jádro s límci v úchytech a gumový návlek, dvě přezky, panty vzadu
    zh = hb - 0.032 * kk
    hxh = 0.075 if not big else 0.11
    for sx in (1, -1):
        vis.append(P.chamfer_box(f"HandleMount{sx}", sx * hxh - 0.014 * kk, sx * hxh + 0.014 * kk, -hy - 0.030 * kk, -hy + 0.002,
                                 zh - 0.014 * kk, zh + 0.014 * kk, "SDT_CaseShell", 0.005 * kk))
    m = D.Mesh((0, 0, 0))
    gy = -hy - 0.025 * kk
    m.tube((-hxh, gy, zh), (hxh, gy, zh), [0.0085 * kk] * 2, "SDT_TankBlack", segments=14)
    for sx in (1, -1):
        m.tube((sx * (hxh - 0.0155 * kk), gy, zh), (sx * (hxh - 0.0205 * kk), gy, zh), [0.0108 * kk] * 2, "SDT_TankBlack",
               segments=14)
    gx = hxh - 0.021 * kk
    m.sweep([(-gx, gy, zh), (-gx + 0.006 * kk, gy, zh), (-gx + 0.016 * kk, gy, zh), (gx - 0.016 * kk, gy, zh),
             (gx - 0.006 * kk, gy, zh), (gx, gy, zh)], [v * kk for v in (0.0092, 0.0118, 0.0125, 0.0125, 0.0118, 0.0092)],
            "SDT_Rubber", segments=14)
    vis.append(mk(m, "HandleGrip"))
    lid_parts = []
    for sx in (1, -1):
        lx_ = sx * hx * 0.62
        lw = 0.028 * kk
        vis.append(P.chamfer_box(f"LatchBase{sx}", lx_ - lw, lx_ + lw, -hy - 0.006, -hy + 0.002, hb - 0.055 * kk, hb - 0.008,
                                 "SDT_CaseShell", 0.004))
        vis.append(P.chamfer_box(f"LatchLever{sx}", lx_ - 0.022 * kk, lx_ + 0.022 * kk, -hy - 0.014, -hy - 0.005, hb - 0.058 * kk,
                                 hb + 0.012, accent, 0.004))
        # čep páky dole, vroubky na úchop nahoře, oko na visací zámek vedle páky
        vis.append(P.cylinder_x(f"LatchPin{sx}", (lx_, -hy - 0.0095, hb - 0.050 * kk), 0.0034, 2 * lw - 0.002, "SDT_Steel",
                                segments=12))
        for k, zz in enumerate((hb + 0.0005, hb + 0.0055)):
            vis.append(P.chamfer_box(f"LatchRidge{sx}{k}", lx_ - 0.016 * kk, lx_ + 0.016 * kk, -hy - 0.0156, -hy - 0.0135, zz,
                                     zz + 0.0025, accent, 0.0008))
        eye = P.ring_z(f"LatchEye{sx}", (0, 0, 0), 0.0042 * kk, 0.0085 * kk, 0.004, "SDT_CaseShell", segments=16)
        eye.matrix_world = (Matrix.Translation((lx_ - sx * (lw + 0.008 * kk), -hy - 0.003, hb - 0.040 * kk))
                            @ Matrix.Rotation(math.pi / 2, 4, "X"))
        vis.append(eye)
        lid_parts.append(P.chamfer_box(f"LatchCatch{sx}", lx_ - 0.026, lx_ + 0.026, -hy - 0.008, -hy + 0.002, hb + 0.004,
                                       hb + 0.022, "SDT_CaseShell", 0.004))
    # pant: u víka 180° v půlce výšky a kus za zadní stěnou (otevřené víko pak leží na zemi), jinak ve spáře
    hinge_y = hy + cfg.get("hinge_gap", 0.007)
    hz = cfg.get("hinge_z", hb)
    for sx in (1, -1):
        hxk = sx * (hx - 0.12)
        for dx in (-0.024, 0.024):
            vis.append(P.cylinder_x(f"Knuckle{sx}{dx}", (hxk + dx, hinge_y, hz), 0.0075, 0.016, "SDT_CaseShell", segments=16))
            vis.append(P.chamfer_box(f"KnuckleLeaf{sx}{dx}", hxk + dx - 0.008, hxk + dx + 0.008, hy - 0.001, hinge_y, hz - 0.020,
                                     hz - 0.004, "SDT_CaseShell", 0.0015))
        # ocelový čep pantu, konce vykukují z krajních kloubů
        vis.append(P.cylinder_x(f"HingePin{sx}", (hxk, hinge_y, hz), 0.0032, 0.068, "SDT_Steel", segments=12))
        lid_parts.append(P.cylinder_x(f"LidKnuckle{sx}", (hxk, hinge_y, hz), 0.0075, 0.030, "SDT_CaseShell", segments=16))
        if hz < hb:
            # rameno pantu od kloubu nahoru po zadní stěně víka (mimo lem spodku)
            lid_parts.append(P.box(f"LidKnuckleLeaf{sx}", hxk - 0.015, hxk + 0.015, hy + 0.004, hinge_y + 0.002, hz + 0.004,
                                   hb + 0.030, "SDT_CaseShell"))
        else:
            lid_parts.append(P.box(f"LidKnuckleLeaf{sx}", hxk - 0.015, hxk + 0.015, hy - 0.001, hinge_y, hb + 0.004, hb + 0.020,
                                   "SDT_CaseShell"))
    # nabíjecí zásuvka na boku +X a indikátor nabíjení na čele pod madlem
    sock_y, sock_z = -hy * 0.45, hb * 0.48
    vis.append(P.cylinder_x("SocketHousing", (hx + 0.004, sock_y, sock_z), 0.019, 0.010, BLACK, segments=18))
    vis.append(P.cylinder_x("SocketHole", (hx + 0.0095, sock_y, sock_z), 0.011, 0.002, "SDT_ScreenOff", segments=16))
    led_z = hb * 0.36
    vis.append(P.box("LedBezel", -0.040, 0.040, -hy - 0.003, -hy + 0.001, led_z - 0.010, led_z + 0.010, BLACK))
    leds = []
    for i in range(4):
        x0 = -0.034 + i * 0.0175
        vis.append(P.box(f"LedLens{i}", x0, x0 + 0.0145, -hy - 0.0040, -hy - 0.0030, led_z - 0.005, led_z + 0.005, LED_OFF))
        leds.append(P.box(f"caseChargeLed{i}", x0 + 0.0005, x0 + 0.014, -hy - 0.0050, -hy - 0.0040, led_z - 0.0045,
                          led_z + 0.0045, LED_ON))
    vis.append(P.cylinder_x("LedIcon", (0.050, -hy - 0.003, led_z), 0.0055, 0.002, "SDT_LampAmber", segments=10))
    bpy.data.objects["LedIcon"].matrix_world = (Matrix.Translation((0.050, -hy - 0.003, led_z))
                                                 @ Matrix.Rotation(math.radians(90), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "Y"))
    # čelo -X: sklopné boční madlo, pod ním hliníkový typový štítek na nýtech a vyrovnávací ventil tlaku
    ys = 0.055 if L_ < 0.7 else 0.085
    zs = hb - 0.036
    m = D.Mesh((0, 0, 0))
    for sy in (1, -1):
        m.solid((-hx - 0.006, sy * ys, zs), (0.0075, 0.012, 0.012), "SDT_CaseShell",
                frame=(Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), cut=0.004, ch=0.002)
    m.sweep([(-hx - 0.010, -ys, zs - 0.004), (-hx - 0.016, -ys + 0.006, zs - 0.012), (-hx - 0.018, -ys + 0.02, zs - 0.016),
             (-hx - 0.018, ys - 0.02, zs - 0.016), (-hx - 0.016, ys - 0.006, zs - 0.012), (-hx - 0.010, ys, zs - 0.004)],
            [0.0055, 0.0065, 0.0075, 0.0075, 0.0065, 0.0055], "SDT_Rubber", segments=12)
    vis.append(mk(m, "SideHandle"))
    pw, ph = (0.034, 0.012) if L_ < 0.7 else (0.050, 0.018)
    pz = zs - 0.034 - ph
    vis.append(P.chamfer_box("Nameplate", -hx - 0.0012, -hx + 0.001, -pw, pw, pz - ph, pz + ph, "SDT_Alu", 0.0006))
    for sy in (1, -1):
        for sz in (1, -1):
            vis.append(P.cylinder_x(f"Rivet{sy}{sz}", (-hx - 0.0014, sy * (pw - 0.005), pz + sz * (ph - 0.005)), 0.0016, 0.0016,
                                    "SDT_Steel", segments=8))
    vy = -(pw + 0.028)
    m = D.Mesh((0, 0, 0))
    m.tube((-hx + 0.001, vy, pz), (-hx - 0.004, vy, pz), [0.0115, 0.0115], "SDT_TankBlack", segments=16)
    m.tube((-hx - 0.004, vy, pz), (-hx - 0.0085, vy, pz), [0.0095, 0.0088], "SDT_TankBlack", segments=16)
    m.tube((-hx - 0.0085, vy, pz), (-hx - 0.0095, vy, pz), [0.0035, 0.0035], "SDT_Steel", segments=10)
    vis.append(mk(m, "PurgeValve"))

    # víko na pantu
    lid = new_empty("caseLid", root, Matrix.Translation((0, hinge_y, hz)), 0.06)
    lh = H_ - hb
    # stěny víka jedním průřezem: lem u spáry se zkosením a mělké obvodové žebro pod hranou víka
    zr = H_ - min(0.030, lh * 0.3)
    lid_profile = [(0.0015, hb + 0.001), (0.0035, hb + 0.003), (0.0035, hb + 0.013), (0.0, hb + 0.017), (0.0, zr - 0.004),
                   (0.0018, zr - 0.002), (0.0018, zr + 0.004), (0.0, zr + 0.006), (0.0, H_ - t), (-t, H_ - t),
                   (-t, hb + 0.0025), (-t + 0.001, hb + 0.001)]
    lid_parts += [
        rrect_shell("LidWalls", hx, hy, r, lid_profile, "SDT_CaseShell"),
        rp("LidTop", 0, 0, hx, hy, r, H_ - t, H_, "SDT_CaseShell", seg=5, bevel_top=0.007, bevel_seg=3),
        rp("LidPad", 0, 0, hx - t - 0.002, hy - t - 0.002, r - t, H_ - t - 0.012, H_ - t, "SDT_CaseFoam", seg=5),
    ]
    if not cfg.get("crate_lid") and not cfg.get("pad_flip"):
        # vybrání v pěně víka pro složenou podložku a zářez na prsty u jejího okraje
        foam_pad = lid_parts[-1]
        psx, psy = cfg.get("pad_store", (0.0, 0.0))
        pr = cfg["pad_d"] / 2 * PAD_FOLD_SCALE + 0.006
        fl = H_ - t - 0.012
        boolean_cut(foam_pad, [P.cylinder_z("CutPadPocket", (psx, psy, fl + 0.002), pr, 0.014, "SDT_CaseFoam", segments=48),
                               P.cylinder_z("CutPadFinger", (psx + pr, psy, fl + 0.0015), 0.020, 0.013, "SDT_CaseFoam",
                                            segments=20)])
    for sy in (1, -1):
        lid_parts.append(rp(f"LidRib{sy}", 0, sy * hy * 0.70, hx - 0.06, 0.011, 0.009, H_ - 0.002, H_ + 0.004,
                            "SDT_CaseShell", seg=3, bevel_top=0.003))
    if cfg.get("crate_lid"):
        # štěrbina na složenou podložku v čele víka -X, těsně nad pěnou víka (pod bednou na vzorky)
        walls = next(o for o in lid_parts if o.name.startswith("LidWalls"))
        slot_hw = cfg["pad_d"] / 2 * PAD_FOLD_SCALE + 0.015
        foam_in = H_ - t - 0.012
        boolean_cut(walls, [P.box("CutPadSlot", -hx - 0.02, -hx + t + 0.02, -slot_hw, slot_hw, foam_in - PAD_SLOT_TH,
                                  foam_in + 0.001, "SDT_CaseShell")])
    join("caseLid_vis", lid_parts, lid)
    P.brand_decal_set("caseLidTop", "lockupOnDark", (0, -0.01, H_ + 0.0005), (0, 0, 1), (0, 1, 0), min(0.48 * L_, 1.0 * hy * 1.2),
                      parent=lid, designs=("BZUK",), offset=0.0008)
    P.brand_decal_set("caseLidFront", "mark", (0, -hy, hb + lh * 0.55), (0, -1, 0), (0, 0, 1), min(0.06, lh * 0.6),
                      parent=lid, designs=("BZUK",), offset=0.0008)
    stripe_y = -hy - 0.0005
    P.brand_decal_set("caseLidFront", "stripe", (0, stripe_y, hb + 0.016), (0, -1, 0), (0, 0, 1), L_ * 0.72, 0.004,
                      parent=lid, designs=("BZUK",), offset=0.0008, tag="Bar")

    # nabíjecí kabel (zástrčka v zásuvce, smotaný kabel na zemi, síťová vidlice); skrytý, ukazuje ho skript při nabíjení
    cable_node = new_empty("caseChargeCable", root, Matrix.Translation((hx, sock_y, sock_z)))
    m = D.Mesh((0, 0, 0))
    m.tube((hx + 0.006, sock_y, sock_z), (hx + 0.040, sock_y, sock_z), [0.011, 0.012, 0.010], BLACK, segments=14)
    m.tube((hx + 0.040, sock_y, sock_z), (hx + 0.055, sock_y, sock_z), [0.007, 0.005], "SDT_Rubber", segments=10)
    pts = [(hx + 0.055, sock_y, sock_z), (hx + 0.075, sock_y, sock_z - 0.006), (hx + 0.092, sock_y - 0.004, sock_z * 0.55),
           (hx + 0.100, sock_y - 0.008, 0.030), (hx + 0.110, sock_y - 0.014, 0.008)]
    ccx, ccy, cr = hx + 0.175, sock_y - 0.045, 0.062
    a0 = math.atan2(pts[-1][1] - ccy, pts[-1][0] - ccx)
    turns = 2.4
    nseg = 48
    for k in range(1, nseg + 1):
        a = a0 + 2 * math.pi * turns * k / nseg
        rr = cr * (1.0 - 0.07 * k / nseg)
        pts.append((ccx + rr * math.cos(a), ccy + rr * math.sin(a), 0.0055 + 0.009 * k / nseg))
    end = Vector(pts[-1])
    pts += [tuple(end + Vector((0.03, -0.04, -0.004))), tuple(end + Vector((0.07, -0.085, -0.007)))]
    m.sweep(pts, [0.0045] * len(pts), "SDT_HoseBlack", segments=8)
    pe = Vector(pts[-1])
    d = (pe - Vector(pts[-2])).normalized()
    m.tube(pe, pe + d * 0.035, [0.009, 0.014, 0.016, 0.016], BLACK, segments=12)
    side = Vector((-d.y, d.x, 0)).normalized()
    for s_ in (1, -1):
        p0 = pe + d * 0.035 + side * s_ * 0.0095
        m.tube(p0, p0 + d * 0.019, [0.0024] * 2, "SDT_Steel", segments=8)
    cable = mk(m, "caseChargeCable_vis")
    adopt(cable, cable_node)

    # pěna s výřezy: dron, baterie (a u AIRASI bednička na vzorky), u skenu náhradní vrtule
    foam_top = hb - 0.012
    floor_z = z_b + t
    dkey = cfg["drone"]
    dx, dy = cfg["drone_xy"]
    # dron v kufru visí pod droneCarrier (v zavřeném kufru jednotková matice): animace víka ho přenese na podložku a domov dronu
    # (rodič kořene, SprayDroneStation.getHomePosition) jde s ním
    carrier = new_empty("droneCarrier", root, None, 0.05)
    droot, info = build_drone(dkey, carrier, Matrix.Translation((dx, dy, 0.0)))
    dmesh = [o for o in droot.children_recursive if o.type == "MESH"]
    lo, hi = mesh_bbox(dmesh)
    pocket_floor = floor_z + cfg.get("pocket_floor", 0.016)
    droot.location.z = 0.0
    bpy.context.view_layer.update()
    droot.matrix_world = Matrix.Translation((0, 0, pocket_floor - lo.z)) @ droot.matrix_world
    bpy.context.view_layer.update()
    lo, hi = mesh_bbox(dmesh)
    foam = rp("Foam", 0, 0, hx - t - 0.001, hy - t - 0.001, r - t, floor_z, foam_top, "SDT_CaseFoam", seg=5, bevel_top=0.003)
    cutters = [rp("CutDrone", (lo.x + hi.x) / 2, (lo.y + hi.y) / 2, (hi.x - lo.x) / 2 + 0.012, (hi.y - lo.y) / 2 + 0.012, 0.015,
                  pocket_floor, foam_top + 0.02, "SDT_CaseFoam", seg=4)]
    # zářezy na prsty na obou koncích výřezu dronu (dron se bere za trup), jen když se vejdou do pěny
    fr = 0.022 if L_ < 0.7 else 0.032
    fy = (lo.y + hi.y) / 2
    for k, fx in enumerate((hi.x + 0.012, lo.x - 0.012)):
        if abs(fx) + fr < hx - t - 0.012:
            cutters.append(P.cylinder_z(f"CutDroneFinger{k}", (fx, fy, (pocket_floor + 0.02 + foam_top + 0.02) / 2), fr,
                                        foam_top - pocket_floor, "SDT_CaseFoam", segments=20))
    bkey = dkey
    bsize = SMALL_BATTERY[bkey]["size"]
    bat_floor = foam_top - bsize[2] * 0.8
    for i, bxy in enumerate(cfg["batteries_xy"], start=1):
        cutters.append(rp(f"CutBattery{i}", bxy[0], bxy[1], bsize[0] / 2 + 0.006, bsize[1] / 2 + 0.006, 0.010, bat_floor,
                          foam_top + 0.02, "SDT_CaseFoam", seg=3))
        # zářez na prsty vedle baterie
        cutters.append(rp(f"CutFinger{i}", bxy[0], bxy[1] - bsize[1] / 2 - 0.004, 0.022, 0.014, 0.012, bat_floor + 0.012,
                          foam_top + 0.02, "SDT_CaseFoam", seg=3))
    box_parts = []
    sample_info = None
    if "props_xy" in cfg:
        pxy = cfg["props_xy"]
        bl = DRONES[dkey]["blade"]
        cutters.append(rp("CutProps", pxy[0], pxy[1], bl[0] + 0.012, 0.036, 0.010, foam_top - 0.014, foam_top + 0.02,
                          "SDT_CaseFoam", seg=3))
        for k, (oy, sgn) in enumerate(((0.014, 1), (-0.014, -1))):
            m = D.Mesh((0, 0, 0))
            m.loft(blade_rings(bl[0], bl[1], bl[2], bl[3], bl[4], 0.0), "Prop_Blade", smooth=True)
            sp = mk(m, f"SpareProp{k}")
            sp.matrix_world = Matrix.Translation((pxy[0] - sgn * bl[0] / 2, pxy[1] + oy, foam_top - 0.012)) @ rz(0 if sgn > 0 else 180)
            box_parts.append(sp)
    if "sample_box" in cfg:
        # bedna ve víkové polovině: staví se v poloze OTEVŘENÉHO víka (180°, vnitřkem nahoru) pod uzlem caseSampleBox, který
        # je vůči víku otočený o 180°, takže víčko bedny (caseSampleBoxLid, skript ho točí kolem X) zůstává ve vlastních osách.
        # Uvnitř tmavá mřížka SAMPLE_GRID přihrádek, v každé uzel sampleSlotN s krabičkou prázdnou (vidět) a plnou (skrytá).
        sx_, sy_c, sw, sd, sh = cfg["sample_box"]
        cols, rows = SAMPLE_GRID
        fixed = cfg.get("crate_lid", False)
        lid.rotation_euler.x = math.radians(lid_open_deg(cfg))
        bpy.context.view_layer.update()
        sy_ = 2 * hinge_y - sy_c
        # bedna přes celé víko stojí na pěně víka nad štěrbinou na složenou podložku
        box_bottom = 2 * hz - (H_ - t - 0.012) + PAD_SLOT_TH if fixed else 2 * hz - (H_ - t) + 0.002
        box_top = box_bottom + sh
        sbox = new_empty("caseSampleBox", root, None, 0.04)
        adopt(sbox, lid)
        bw = 0.004
        sb_parts = [
            rp("BoxFloor", sx_, sy_, sw / 2, sd / 2, 0.010, box_bottom, box_bottom + bw, "SDT_TankBlack", seg=3),
            rb("BoxWalls", (sw / 2, sd / 2, 0.010), (sw / 2 - bw, sd / 2 - bw, 0.006), box_bottom, box_top, "SDT_TankBlack", seg=3),
        ]
        sb_parts[-1].matrix_world = Matrix.Translation((sx_, sy_, 0.0))     # rrect_band staví kolem počátku
        div_h = min(box_bottom + bw + SAMPLE_BOX[2] * 0.72, box_top - 0.004)
        pitch_x, pitch_y = (sw - 2 * bw) / cols, (sd - 2 * bw) / rows
        for i in range(1, cols):
            xx = sx_ - sw / 2 + bw + pitch_x * i
            sb_parts.append(P.box(f"BoxDivX{i}", xx - 0.002, xx + 0.002, sy_ - sd / 2 + bw, sy_ + sd / 2 - bw, box_bottom,
                                  div_h, GREY_DARK))
        for j in range(1, rows):
            yy = sy_ - sd / 2 + bw + pitch_y * j
            sb_parts.append(P.box(f"BoxDivY{j}", sx_ - sw / 2 + bw, sx_ + sw / 2 - bw, yy - 0.002, yy + 0.002, box_bottom,
                                  div_h, GREY_DARK))
        if fixed:
            # oranžový lem bedny, ať je ve víku vidět
            sb_parts.append(rb("BoxRim", (sw / 2 + 0.003, sd / 2 + 0.003, 0.012), (sw / 2 - bw, sd / 2 - bw, 0.006), box_top - 0.006,
                               box_top + 0.002, accent, seg=3))
            sb_parts[-1].matrix_world = Matrix.Translation((sx_, sy_, 0.0))
        # úchopové otvory v čelech bedny pod lemem
        cut = []
        for k, ex in enumerate((sx_ - sw / 2, sx_ + sw / 2)):
            c = rp(f"CutCrateGrip{k}", 0, 0, 0.0085, min(0.045, sd * 0.12), 0.0084, -0.012, 0.012, "SDT_TankBlack", seg=4)
            c.matrix_world = Matrix.Translation((ex, sy_, box_top - 0.024)) @ Matrix.Rotation(math.pi / 2, 4, "Y")
            cut.append(c)
        bpy.context.view_layer.update()
        boolean_cut(sb_parts[1], cut)
        join("caseSampleBox_vis", sb_parts, sbox)
        if not fixed:
            blid = new_empty("caseSampleBoxLid", root, Matrix.Translation((sx_, sy_ + sd / 2, box_top)), 0.04)
            lp = [rp("BoxLid", sx_, sy_, sw / 2 + 0.002, sd / 2 + 0.002, 0.011, box_top, box_top + 0.006, accent, seg=3,
                     bevel_top=0.002),
                  P.chamfer_box("BoxLidTab", sx_ - 0.025, sx_ + 0.025, sy_ - sd / 2 - 0.012, sy_ - sd / 2 + 0.004, box_top,
                                box_top + 0.006, accent, 0.002)]
            for k in (-1, 1):
                lp.append(P.cylinder_x(f"BoxHinge{k}", (sx_ + k * sw * 0.3, sy_ + sd / 2, box_top), 0.004, 0.03, "SDT_TankPE",
                                       segments=10))
            adopt(blid, sbox)
            join("caseSampleBoxLid_vis", lp, blid)
        # uzel caseSamples uprostřed bedny: na něj hráč míří (SprayDroneSamples.isAimedAtBox); přihrádky číslované po řadách
        # od pantu kufru (řada 1 nejblíž kufru), v řadě od strany -X
        samples = new_empty("caseSamples", root, Matrix.Translation((sx_, sy_, box_bottom + sh / 2)))
        adopt(samples, sbox)
        for i in range(NUM_BOX_SAMPLES):
            col, row = i % cols, i // cols
            cx = sx_ - sw / 2 + bw + pitch_x * (col + 0.5)
            cy = sy_ - sd / 2 + bw + pitch_y * (row + 0.5)
            slot = new_empty(f"sampleSlot{i + 1}", None, Matrix.Translation((cx, cy, box_bottom + bw)), 0.02)
            adopt(slot, samples)
            sample_box(f"sampleSlot{i + 1}Empty", slot, False)
            sample_box(f"sampleSlot{i + 1}Full", slot, True)
        sample_info = (box_bottom, box_top)
        lid.rotation_euler.x = 0.0
        bpy.context.view_layer.update()
    boolean_cut(foam, cutters)
    vis.append(foam)
    vis += box_parts
    join(f"{name}_vis", vis, root)
    for i, bxy in enumerate(cfg["batteries_xy"], start=1):
        case_battery(bkey, root, bxy, bat_floor, "" if i == 1 else str(i))
    for o in leds:
        adopt(o, root)
    bpy.context.view_layer.update()
    info["arm0"] = {n: bpy.data.objects[n].rotation_euler.z for n, _, _ in info["arms"]}
    info["blade0"] = {n: bpy.data.objects[n].rotation_euler.z for n, _ in info["blades"]}
    if dkey == "P":
        info["probe0"] = bpy.data.objects["droneProbe"].location.z
        root_z = droot.matrix_world.translation.z
        tip_low = mesh_bbox([bpy.data.objects["droneProbe_vis"]])[0].z
        # hloubka hrotu vysunuté sondy pod terénem při odběru (kořen SAMPLER_HEIGHT nad terénem)
        info["probe_reach"] = PROBE_TRAVEL - (tip_low - root_z + SAMPLER_HEIGHT)
        info["feet_rel_root"] = lo.z - root_z
    info["drone_root_world"] = tuple(droot.matrix_world.translation)
    info["sample_box"] = sample_info
    info["anim"] = case_anim(cfg, lid, carrier, droot, lo.z)
    for o in root.children_recursive:
        if o.type == "MESH" and not o.name.startswith(("floorCollision", "dynamicMountTrigger", "exactFillRootNode")):
            smooth_normals(o)
    return root, info


def landing_pad(cfg, lid):
    """Podložka casePad pod víkem: kotouč s potahem (oranžový, bílý kruh a H, tmavý lem obruče), počátek uprostřed dole.
    Uzel nese měřítko složené podložky a leží zapuštěný v pěně víka (u AIRASI je nad dronem jen ~1 cm). Vrací (uzel, poloměr)."""
    L_, W_, H_ = cfg["size"]
    t = cfg["wall"]
    R = cfg["pad_d"] / 2
    foam_low = H_ - t - 0.012
    fold = Matrix.Diagonal((PAD_FOLD_SCALE, PAD_FOLD_SCALE, PAD_FOLD_THICK, 1.0))
    sx_, sy_ = cfg.get("pad_store", (0.0, 0.0))
    bpy.context.view_layer.update()
    if cfg.get("crate_lid"):
        # víko je otevřené (volá se s víkem v otevřené poloze): štěrbina pod bednou, podložka lícem nahoru, okraj u čela -X
        hinge_y = W_ / 2 + cfg.get("hinge_gap", 0.007)
        hz = cfg.get("hinge_z", cfg["base_h"])
        world = Vector((-L_ / 2 + t + 0.03 + R * PAD_FOLD_SCALE, 2 * hinge_y, 2 * hz - foam_low + 0.0008))
        stored = lid.matrix_world.inverted() @ world
        basis = Matrix.Translation(stored) @ Matrix.Rotation(math.pi, 4, "X") @ fold
    elif cfg.get("pad_flip"):
        # lícem dolů: po otevření víka o 180° leží v pěně lícem nahoru (podložka se pak už neotáčí)
        stored = lid.matrix_world.inverted() @ Vector((sx_, sy_, foam_low + PAD_TH * PAD_FOLD_THICK * 0.45))
        basis = Matrix.Translation(stored) @ Matrix.Rotation(math.pi, 4, "X") @ fold
    else:
        stored = lid.matrix_world.inverted() @ Vector((sx_, sy_, foam_low - PAD_TH * PAD_FOLD_THICK * 0.45))
        basis = Matrix.Translation(stored) @ fold
    pad = new_empty("casePad", lid, basis, 0.05)
    th, w = PAD_TH, 0.0008
    parts = [P.cylinder_z("PadBase", (0, 0, th / 2), R - 0.004, th, "SDT_GenOrange", segments=64),
             P.ring_z("PadHem", (0, 0, th / 2), R - 0.018, R, th + 0.0012, BLACK, segments=64),
             P.ring_z("PadCircle", (0, 0, th + w / 2), 0.60 * R, 0.68 * R, w, "SDT_PaintWhite", segments=64)]
    # H napříč nosu dronu (nos na podložce míří po +X kufru): svislé tahy podél Y, příčka podél X
    hx_, hl, hw = 0.20 * R, 0.30 * R, 0.045 * R
    for s in (1, -1):
        parts.append(P.box(f"PadH{s}", s * hx_ - hw, s * hx_ + hw, -hl, hl, th, th + w, "SDT_PaintWhite"))
    parts.append(P.box("PadHBar", -hx_ + hw, hx_ - hw, -hw * 0.9, hw * 0.9, th, th + w, "SDT_PaintWhite"))
    join("casePad_vis", parts, pad, local=True)
    return pad, R


def case_anim(cfg, lid, carrier, droot, drone_low):
    """Klíčové polohy animace víka v Blenderu: [(uzel, druh, t0, t1, od, do)], druh trans (Vector, lokálně), rotX (stupně),
    scale (Vector). Časy jsou podíly z CASE_ANIM ve směru zavírání (0 = otevřeno, dron rozložený na podložce)."""
    L_, W_, H_ = cfg["size"]
    hb = cfg["base_h"]
    if cfg.get("crate_lid"):
        return case_anim_crate(cfg, lid, droot, drone_low)
    pad, R = landing_pad(cfg, lid)
    bpy.context.view_layer.update()
    center = Vector((-(L_ / 2 + cfg["pad_gap"] + R), 0.0, 0.0))
    # podložka: polohy v rámci otevřeného víka (víko stojí, podložka se točí jen kolem jeho osy X)
    lid_deg = lid_open_deg(cfg)
    lid.rotation_euler.x = math.radians(lid_deg)
    bpy.context.view_layer.update()
    lw = lid.matrix_world.copy()
    inv = lw.inverted()
    k0 = pad.matrix_basis.to_translation()
    normal = (lw.to_3x3() @ Vector((0, 0, -1))).normalized()
    k1 = inv @ (lw @ k0 + normal * PAD_LIFT)
    k2 = inv @ (center + Vector((0, 0, H_ + PAD_HIGH)))
    k3 = inv @ center
    store_w = lw @ k0
    k2b = inv @ Vector((store_w.x, store_w.y, H_ + PAD_HIGH))
    lid.rotation_euler.x = 0.0
    bpy.context.view_layer.update()
    flat = -lid_deg
    stored_rot = 180.0 if cfg.get("pad_flip") else 0.0
    folded = Vector((PAD_FOLD_SCALE, PAD_FOLD_SCALE, PAD_FOLD_THICK))
    one = Vector((1.0, 1.0, 1.0))
    # dron: posun nosiče (kořen dronu zůstává pod ním beze změny); dole = lyžiny na podložce
    rz0 = droot.matrix_world.translation.z
    feet = drone_low - rz0
    lift = Vector((0, 0, hb + DRONE_LIFT - feet - rz0))
    over = Vector((center.x - droot.matrix_world.translation.x, center.y - droot.matrix_world.translation.y, lift.z))
    on_pad = Vector((over.x, over.y, PAD_TH - feet - rz0))
    above = on_pad + Vector((0, 0, DRONE_SETTLE))
    A = case_anim_times(cfg)
    parts = [
        ("droneCarrier", "trans", *A["arms"], on_pad, above),
        ("droneCarrier", "trans", *A["lift"], above, over),
        ("droneCarrier", "trans", *A["carry"], over, lift),
        ("droneCarrier", "trans", *A["lower"], lift, Vector((0, 0, 0))),
        ("casePad", "scale", *A["padFold"], one, folded),
        ("casePad", "trans", *A["padUp"], k3, k2),
        ("casePad", "rotX", *A["padUp"], flat, flat),
    ]
    if "padDrop" in A:
        parts += [("casePad", "trans", *A["padSwing"], k2, k2b),
                  ("casePad", "rotX", *A["padSwing"], flat, stored_rot),
                  ("casePad", "trans", *A["padDrop"], k2b, k1)]
    else:
        parts += [("casePad", "trans", *A["padSwing"], k2, k1),
                  ("casePad", "rotX", *A["padSwing"], flat, stored_rot)]
    parts += [("casePad", "trans", *A["padIn"], k1, k0),
              ("caseLid", "rotX", *A["lid"], lid_deg, 0.0)]
    return parts


def drone_carry_parts(cfg, A, droot, drone_low, center):
    """Přenos dronu nosičem droneCarrier mezi pěnou kufru a podložkou se středem center (svět)."""
    hb = cfg["base_h"]
    rz0 = droot.matrix_world.translation.z
    feet = drone_low - rz0
    lift = Vector((0, 0, hb + DRONE_LIFT - feet - rz0))
    over = Vector((center.x - droot.matrix_world.translation.x, center.y - droot.matrix_world.translation.y, lift.z))
    on_pad = Vector((over.x, over.y, PAD_TH - feet - rz0))
    above = on_pad + Vector((0, 0, DRONE_SETTLE))
    return [
        ("droneCarrier", "trans", *A["arms"], on_pad, above),
        ("droneCarrier", "trans", *A["lift"], above, over),
        ("droneCarrier", "trans", *A["carry"], over, lift),
        ("droneCarrier", "trans", *A["lower"], lift, Vector((0, 0, 0))),
    ]


def case_anim_crate(cfg, lid, droot, drone_low):
    """Animace kufru s bednou přes celé víko (crate_lid), ve směru zavírání: dron do pěny, podložka (lícem nahoru, natočení vůči
    víku 180°) se složí na zemi, zvedne, přenese před čelo ležícího víka -X, spustí na výšku štěrbiny pod bednou a zasune; pak
    se víko zavře. Polohy podložky jsou v rámci otevřeného víka (v pohybu víka už je uklizená). V i3d zůstává víko zavřené."""
    L_, W_, H_ = cfg["size"]
    lid_deg = lid_open_deg(cfg)
    lid.rotation_euler.x = math.radians(lid_deg)
    bpy.context.view_layer.update()
    pad, R = landing_pad(cfg, lid)
    bpy.context.view_layer.update()
    center = Vector((-(L_ / 2 + cfg["pad_gap"] + R), 0.0, 0.0))
    lw = lid.matrix_world.copy()
    inv = lw.inverted()
    k0 = pad.matrix_basis.to_translation()
    store_w = lw @ k0
    entry_low = Vector((-L_ / 2 - R * PAD_FOLD_SCALE - 0.04, store_w.y, store_w.z))
    entry_high = Vector((entry_low.x, entry_low.y, PAD_HIGH))
    up = center + Vector((0, 0, PAD_HIGH))
    flat = -lid_deg
    folded = Vector((PAD_FOLD_SCALE, PAD_FOLD_SCALE, PAD_FOLD_THICK))
    one = Vector((1.0, 1.0, 1.0))
    A = CASE_ANIM_CRATE
    parts = drone_carry_parts(cfg, A, droot, drone_low, center)
    parts += [
        ("casePad", "scale", *A["padFold"], one, folded),
        ("casePad", "trans", *A["padUp"], inv @ center, inv @ up),
        ("casePad", "rotX", *A["padUp"], flat, flat),
        ("casePad", "trans", *A["padSwing"], inv @ up, inv @ entry_high),
        ("casePad", "trans", *A["padDrop"], inv @ entry_high, inv @ entry_low),
        ("casePad", "trans", *A["padIn"], inv @ entry_low, k0),
        ("caseLid", "rotX", *A["lid"], lid_deg, 0.0),
    ]
    lid.rotation_euler.x = 0.0
    bpy.context.view_layer.update()
    return parts


def anim_value(parts, node, kind, t):
    """Hodnota animace v čase t (lineárně jako AnimatedVehicle; mezi díly drží konec předchozího)."""
    own = sorted((p for p in parts if p[0] == node and p[1] == kind), key=lambda p: p[2])
    if not own:
        return None
    val = own[0][4]
    for _, _, t0, t1, a, b in own:
        if t < t0:
            break
        u = 1.0 if t >= t1 else (t - t0) / max(t1 - t0, 1e-6)
        val = a + (b - a) * u
    return val


def set_case_anim(key, info, t):
    """Náhled kufru v čase animace t (0 = otevřeno, 1 = zavřeno), ramena dronu podle trailerFoldEnd."""
    parts = info["anim"]
    carrier = bpy.data.objects["droneCarrier"]
    carrier.location = anim_value(parts, "droneCarrier", "trans", t)
    pad = bpy.data.objects["casePad"]
    sc = anim_value(parts, "casePad", "scale", t)
    rot = anim_value(parts, "casePad", "rotX", t)
    pad.matrix_basis = (Matrix.Translation(anim_value(parts, "casePad", "trans", t)) @ Matrix.Rotation(math.radians(rot), 4, "X")
                        @ Matrix.Diagonal((sc.x, sc.y, sc.z, 1.0)))
    lid_rot = anim_value(parts, "caseLid", "rotX", t)
    if lid_rot is not None:
        bpy.data.objects["caseLid"].rotation_euler.x = math.radians(lid_rot)
    set_drone_unfold(key, info, min(max(1.0 - t / CASE_ANIM["arms"][1], 0.0), 1.0), probe=False)
    bpy.context.view_layer.update()


def i3d_vec(kind, v):
    """Hodnota z Blenderu do i3d (osy jako exportér: x, z, -y; otočení kolem X beze změny)."""
    if kind == "trans":
        return f"{v.x:.4f} {v.z:.4f} {-v.y:.4f}"
    if kind == "scale":
        return f"{v.x:.4f} {v.z:.4f} {v.y:.4f}"
    return f"{v:.1f} 0 0"


def anim_xml(name, info):
    """Blok <animations> pro XML kufru (časy v sekundách z CASES[name]['anim_s'])."""
    total = CASES[name]["anim_s"]
    attrs = {"trans": ("startTrans", "endTrans"), "rotX": ("startRot", "endRot"), "scale": ("startScale", "endScale")}
    rows = {}
    for node, kind, t0, t1, a, b in info["anim"]:
        row = rows.setdefault((node, t0, t1), [])
        s, e = attrs[kind]
        row.append(f'{s}="{i3d_vec(kind, a)}" {e}="{i3d_vec(kind, b)}"')
    out = ['    <animations>', '        <animation name="caseLidAnim">']
    for (node, t0, t1), vals in sorted(rows.items(), key=lambda r: (r[0][1], r[0][0])):
        out.append(f'            <part node="{node}" startTime="{t0 * total:.2f}" endTime="{t1 * total:.2f}" {" ".join(vals)}/>')
    out += ['        </animation>', '    </animations>']
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------ baterie jako předměty


def build_battery_item(key):
    name = f"battery{key}"
    C.wipe()
    P._coll = scene_coll()
    root = C.box_object(f"{name}_main_component1", None, -0.02, 0.02, -0.02, 0.02, 0.0, 0.04, C.GROUP_ROOT, C.MASK_ROOT,
                        dynamic=True, compound=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0, clipDistance=120.0)
    P._root = root
    cols = new_empty("collisions", root)
    C.props(cols, clipDistance=10.0)
    if key in P.BATTERY_SIZES:
        size = P.BATTERY_SIZES[key]
        orig_box = P.box

        def box_led_off(n, *a):
            if "_Led" in n and n.rsplit("_Led", 1)[1].isdigit():
                a = a[:-1] + (LED_OFF,)
            return orig_box(n, *a)
        P.box = box_led_off
        try:
            vis = P.battery(f"{name}_vis", size)
        finally:
            P.box = orig_box
        dx, dz = P.battery_frame_offset(size)
        vis.data.transform(Matrix.Translation((-dx, 0, -dz)))
        lx, ly, lz = size[0] / 2, size[1] / 2, size[2]
        leds = [((lx * 0.71, (-0.12 + 0.22 * i) * ly, lz + 0.0068), (lx * 0.02, 0.065 * ly, 0.0007)) for i in range(4)]
    else:
        parts, leds = small_battery_parts(key)
        vis = join(f"{name}_vis", parts, root)
    attach_local(vis, root)
    C.props(vis, clipDistance=60.0)
    for i, ((cx, cy, cz), (ax, ay, az)) in enumerate(leds):
        o = P.box(f"batteryLed{i}", cx - ax, cx + ax, cy - ay, cy + ay, cz - az, cz + az, LED_ON)
        adopt(o, root)
        C.props(o, clipDistance=25.0)
    lo, hi = mesh_bbox([vis])
    C.box_object("floorCollision01", cols, lo.x, hi.x, lo.y, hi.y, 0.0, hi.z, C.GROUP_FLOOR, C.MASK_FLOOR, compoundChild=True,
                 staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    bpy.context.view_layer.update()
    return root, name, (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)


# ------------------------------------------------------------------------------------------------ export


def patch_decal_texture(path):
    """Štítky baterií (SDT_Decal) berou atlas sdt_decals z Middle jako vlek; LI.shader_materials jim dává bílou texturu."""
    tree = ET.parse(path)
    r = tree.getroot()
    files = r.find("Files")
    fid = None
    for f in files:
        if f.get("filename") == DECAL_TEXTURE_REL:
            fid = f.get("fileId")
    for mat in r.find("Materials"):
        if mat.get("name") != "SDT_Decal":
            continue
        if fid is None:
            fid = str(max(int(f.get("fileId")) for f in files) + 1)
            ET.SubElement(files, "File", fileId=fid, filename=DECAL_TEXTURE_REL)
        tex = mat.find("Texture")
        if tex is not None:
            tex.set("fileId", fid)
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")


def i3d_tree(path):
    """Strom uzlů i3d (jméno, typ, translation, rotation, visibility) jako text."""
    scene = ET.parse(path).getroot().find("Scene")
    lines = []

    def walk(el, depth, idx):
        attrs = []
        for a in ("translation", "rotation"):
            if el.get(a):
                attrs.append(f"{a[0]}=({el.get(a)})")
        if el.get("visibility") == "false":
            attrs.append("HIDDEN")
        lines.append(f"{'  ' * depth}{idx} {el.tag} {el.get('name')} {' '.join(attrs)}")
        for i, ch in enumerate([c for c in el if c.tag in ("Shape", "TransformGroup", "Light", "Camera")]):
            walk(ch, depth + 1, f"{idx}{i}" if idx.endswith(">") else f"{idx}|{i}")

    for ci, comp in enumerate(scene):
        walk(comp, 0, f"{ci}>")
    return "\n".join(lines)


def i3d_nodes(path):
    out = {}
    for el in ET.parse(path).getroot().find("Scene").iter():
        if el.get("name"):
            out[el.get("name")] = el
    return out


def vec(el, attr):
    v = el.get(attr)
    return [float(c) for c in v.split()] if v else [0.0, 0.0, 0.0]


def drone_block(name, key, info, nodes):
    """Řádky bloku <drone> (náklon, kloubové díly, vrtule, rotory, LED) podle čísel z hotového i3d."""
    pre = DRONES[key]["prefix"]
    out = [f'        <tilt node="{pre}Tilt"/>']
    for node, delta, _ in info["arms"]:
        r = vec(nodes[node], "rotation")
        out.append(f'        <foldPart node="{node}" foldedRot="{r[0]:.3f} {r[1]:.3f} {r[2]:.3f}" '
                   f'unfoldedRot="{r[0]:.3f} {r[1] + delta:.3f} {r[2]:.3f}" startTime="0" endTime="0.6"/>')
        idx = node[-1]
        for b in (0, 1):
            bn = f"{pre}Blade_{idx}Top{b}"
            bd = dict(info["blades"])[bn]
            rb_ = vec(nodes[bn], "rotation")
            out.append(f'        <foldPart node="{bn}" foldedRot="{rb_[0]:.3f} {rb_[1]:.3f} {rb_[2]:.3f}" '
                       f'unfoldedRot="{rb_[0]:.3f} {rb_[1] + bd:.3f} {rb_[2]:.3f}" startTime="0.5" endTime="1"/>')
    if key == "P":
        out.append(f'        <!-- sampler: probeTravel="{PROBE_TRAVEL:g}" capacity="{NUM_DRONE_BOXES}" boxCapacity="{NUM_BOX_SAMPLES}" '
                   f'height="{SAMPLER_HEIGHT:g}"; hrot při odběru {info["probe_reach"]:.3f} m pod terénem, '
                   f'lyžiny {info["feet_rel_root"]:.4f} m nad kořenem -->')
    out.append(f'        <propSource node="{pre}Arm_1"/>')
    for i in range(1, 5):
        for b in (0, 1):
            out.append(f'        <propBlade node="{pre}Blade_{i}Top{b}" tip="{pre}Blade_{i}Top{b}_Tip"/>')
    for i in range(1, 5):
        out.append(f'        <rotor node="{pre}Rotor_{i}Top" direction="{ROTOR_DIRECTIONS[i]}"/>')
    for i in range(1, 5):
        out.append(f'        <navLight node="{pre}Led_{i}" lightNode="{pre}LedLight_{i}" blink="{str(i in BLINKING_LEDS).lower()}"/>')
    return "\n".join(out)


def mapped_names(name, key):
    pre = DRONES[key]["prefix"]
    names = [f"{name}_main_component1", f"{name}_vis", "floorCollision01", "dynamicMountTrigger", "exactFillRootNode",
             "caseLid", "caseLid_vis", "casePad", "casePad_vis", "droneCarrier", "caseBatterySlot", "caseBattery", "caseBatterySlot2",
             "caseBattery2", "caseChargeCable"]
    names += [f"caseChargeLed{i}" for i in range(4)]
    if key == "P":
        names += ["caseSamples"] if CASES[name].get("crate_lid") else ["caseSampleBoxLid", "caseSamples"]
        names += [f"sampleSlot{i + 1}{k}" for i in range(NUM_BOX_SAMPLES) for k in ("", "Empty", "Full")]
    names += [pre + "Root", pre + "Tilt", pre + "Body", pre + "BatterySlot", pre + "Battery"]
    names += [f"{pre}ArmPivot_{i}" for i in range(1, 5)] + [f"{pre}Arm_{i}" for i in range(1, 5)]
    names += [f"{pre}Rotor_{i}Top" for i in range(1, 5)]
    names += [f"{pre}Blade_{i}Top{b}{t}" for i in range(1, 5) for b in (0, 1) for t in ("", "_Tip")]
    names += [f"{pre}{k}_{i}" for i in range(1, 5) for k in ("Led", "LedLight")]
    if key == "P":
        names += ["droneProbe"]
        names += [f"droneSampleBox{i}{k}" for i in range(1, NUM_DRONE_BOXES + 1) for k in ("", "Empty", "Full")]
    return names


def hidden_names(key):
    out = ["caseChargeCable"]
    if key == "P":
        out += [f"sampleSlot{i + 1}Full" for i in range(NUM_BOX_SAMPLES)]
        out += [f"droneSampleBox{i}{k}" for i in range(1, NUM_DRONE_BOXES + 1) for k in ("Empty", "Full")]
    return out


def set_hidden_render(names, hidden):
    for n in names:
        o = bpy.data.objects[n]
        for x in [o] + list(o.children_recursive):
            x.hide_render = hidden


def show_samples(full_slots, drone_full=None):
    """Krabičky pro náhled: přihrádky ve full_slots plné, ostatní prázdné; v dronu plné ty z drone_full, ostatní prázdné
    (drone_full None = dron bez krabiček)."""
    for i in range(1, NUM_BOX_SAMPLES + 1):
        bpy.data.objects[f"sampleSlot{i}Empty"].hide_render = i in full_slots
        bpy.data.objects[f"sampleSlot{i}Full"].hide_render = i not in full_slots
    for i in range(1, NUM_DRONE_BOXES + 1):
        bpy.data.objects[f"droneSampleBox{i}Empty"].hide_render = drone_full is None or i in drone_full
        bpy.data.objects[f"droneSampleBox{i}Full"].hide_render = drone_full is None or i not in drone_full


def sampler_previews(name, info):
    """Náhledy AIRASI do tmp/sampler: bedna s přihrádkami, krabičky zblízka, dron zboku se sondou zasunutou a vysunutou."""
    os.makedirs(TMP_SAMPLER, exist_ok=True)
    out = lambda n: os.path.join(TMP_SAMPLER, f"{name}_{n}.png")  # noqa: E731
    pre = DRONES["P"]["prefix"]
    tray = [bpy.data.objects["caseSampleBox_vis"]]
    show_samples((1, 2, 6, 7, 11), ())
    render(out("tray_top"), Vector((0.0, 0.25, 1.0)), objs=tray)
    render(out("tray_persp"), Vector((-0.35, -0.7, 0.8)), objs=tray)
    pair = [bpy.data.objects[n] for n in ("sampleSlot1Full", "sampleSlot2Full", "sampleSlot3Empty", "sampleSlot4Empty")]
    render(out("boxes_detail"), Vector((-0.25, -0.6, 0.6)), objs=pair)
    # dron zvlášť, zvednutý nad podložku (vysunutá sonda by jí prošla): s krabičkami (1 plná, 2 prázdná), sonda zasunutá a vysunutá
    droot = bpy.data.objects[pre + "Root"]
    base = droot.matrix_basis.copy()
    droot.matrix_basis = Matrix.Translation((0, 0, 0.8)) @ base
    show_samples((1, 2, 6, 7, 11), (1,))
    dobjs = [o for o in droot.children_recursive if o.type == "MESH" and not o.hide_render]
    set_drone_unfold("P", info, 1.0, probe=False)
    render(out("drone_side"), Vector((0.0, -1.0, 0.06)), objs=dobjs)
    render(out("drone_persp"), Vector((0.8, -0.9, 0.35)), objs=dobjs)
    render(out("drone_under"), Vector((0.5, -0.8, -0.35)), objs=dobjs)
    set_drone_unfold("P", info, 1.0, probe=True)
    render(out("drone_side_probe"), Vector((0.0, -1.0, 0.06)), objs=dobjs)
    render(out("drone_under_probe"), Vector((0.5, -0.8, -0.35)), objs=dobjs)
    set_drone_unfold("P", info, 1.0, probe=False)
    droot.matrix_basis = base
    bpy.context.view_layer.update()


def set_lid(open_t, sample_open_t=None):
    """Víko kufru (open_t None = nechat, jak ho nastavil set_case_anim) a víčko bedničky AIRASI."""
    if open_t is not None:
        bpy.data.objects["caseLid"].rotation_euler.x = math.radians(LID_OPEN_DEG) * open_t
    if "caseSampleBoxLid" in bpy.data.objects and sample_open_t is not None:
        bpy.data.objects["caseSampleBoxLid"].rotation_euler.x = math.radians(SAMPLE_LID_OPEN_DEG) * sample_open_t
    bpy.context.view_layer.update()


def render(png, direction, objs=None, res=900, transparent=False, lens=None):
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.film_transparent = transparent
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = -0.2
    world = bpy.data.worlds.get("_prev_world") or bpy.data.worlds.new("_prev_world")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.78, 0.80, 0.84, 1.0)
    bg.inputs[1].default_value = 0.75
    sc.world = world
    for nm, energy, rot in (("_key", 3.2, (0.75, 0.15, -0.55)), ("_fill", 1.0, (1.1, -0.2, 2.4))):
        if nm not in bpy.data.objects:
            data = bpy.data.lights.new(nm, "SUN")
            data.energy = energy
            data.angle = 0.2
            ob = bpy.data.objects.new(nm, data)
            ob.rotation_euler = rot
            sc.collection.objects.link(ob)
    cam = bpy.data.objects.get("_cam")
    if cam is None:
        cd = bpy.data.cameras.new("_cam")
        cd.clip_start = 0.01
        cam = bpy.data.objects.new("_cam", cd)
        sc.collection.objects.link(cam)
    sc.camera = cam
    for o in bpy.data.objects:
        if o.type == "LIGHT" and not o.name.startswith("_"):
            o.hide_render = True      # poziční LED dronu ve hře svítí jen za letu
    objs = objs or [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render]
    lo, hi = mesh_bbox(objs)
    size = max(hi - lo)
    cam.data.lens = lens or max(120.0, 160.0 / max(size, 0.05))
    X._fit_camera(cam, objs, Vector(direction), margin=0.05, drop=0.0)
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)


def store(png, dds):
    render(png, X.STORE_VIEW_DIR, res=X.STORE_RES, transparent=True)
    X.png2dds(png, dds, "dxt5", "--size", "512", "--no-mips")


def finish_scene(prefix_tag):
    """Objekty hotového předmětu přejmenuje (prefix) a skryje z renderu, ať další předmět ve scéně staví čistě."""
    for o in list(bpy.data.objects):
        if o.name.startswith("_") or ":" in o.name:
            continue
        o.name = f"{prefix_tag}:{o.name}"
        o.hide_render = True
        o.hide_set(True)


def _bvh(objs, inv):
    verts, polys = [], []
    for o in objs:
        m = inv @ o.matrix_world
        n = len(verts)
        verts += [m @ v.co for v in o.data.vertices]
        polys += [[n + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys)


def _area_centroid(objs, inv):
    area, acc = 0.0, Vector((0, 0, 0))
    for o in objs:
        m = inv @ o.matrix_world
        for p in o.data.polygons:
            vs = [m @ o.data.vertices[i].co for i in p.vertices]
            a = 0.0
            for i in range(1, len(vs) - 1):
                a += (vs[i] - vs[0]).cross(vs[i + 1] - vs[0]).length / 2
            area += a
            acc += sum(vs, Vector((0, 0, 0))) / len(vs) * a
    return acc / max(area, 1e-9)


# odhad hmotností dílů zavřeného kufru AIRASI (kg, dohromady base#mass 32) na těžiště
CRATE_COM_MASSES = (("base", 14.0), ("lid", 7.6), ("crate", 2.5), ("pad", 1.2), ("drone", 4.5), ("batteries", 2.2))


def crate_lid_report(name):
    """Zavřené víko kufru s bednou (crate_lid) nad obsahem spodku: protnutí a nejmenší vůle bedny, krabiček a podložky nad dronem,
    bateriemi a pěnou, průchod víka celým otáčením (po 5°) a těžiště zavřeného kufru. Řádky „klíč: hodnota“ čte
    tools/test_case_lid.py. Víko po sobě vrátí zavřené."""
    O = bpy.data.objects
    root = O[f"{name}_main_component1"]
    lid = O["caseLid"]
    inv = root.matrix_world.inverted()
    pre = DRONES[CASES[name]["drone"]]["prefix"]
    drone = [o for o in O[pre + "Root"].children_recursive if o.type == "MESH" and not o.name.endswith("Full")]
    bats = [O["caseBattery"], O["caseBattery2"]]
    base = [O[f"{name}_vis"]]
    inner = [o for o in lid.children_recursive if o.type == "MESH" and (o.name.startswith(("caseSampleBox", "sampleSlot", "casePad")))]
    shell = [O["caseLid_vis"]]
    lid.rotation_euler.x = 0.0
    bpy.context.view_layer.update()
    content = drone + bats
    t_inner, t_shell = _bvh(inner, inv), _bvh(shell, inv)
    t_content, t_base = _bvh(content, inv), _bvh(base, inv)
    out = [f"overlap_inner_content: {len(t_inner.overlap(t_content))}",
           f"overlap_inner_base: {len(t_inner.overlap(t_base))}",
           f"overlap_shell_content: {len(t_shell.overlap(t_content))}"]
    gap, at = 9.0, None
    for o in content:
        m = inv @ o.matrix_world
        for v in o.data.vertices:
            p = m @ v.co
            hit = t_inner.ray_cast(p + Vector((0, 0, 1e-5)), Vector((0, 0, 1)))
            if hit[0] is not None and hit[3] < gap:
                gap, at = hit[3], (o.name, tuple(round(c, 3) for c in p))
    near = min((t_inner.find_nearest(inv @ (o.matrix_world @ v.co))[3] for o in content for v in o.data.vertices), default=9.0)
    lo_inner = min((inv @ (o.matrix_world @ v.co)).z for o in inner for v in o.data.vertices)
    hi_content = max((inv @ (o.matrix_world @ v.co)).z for o in content for v in o.data.vertices)
    out += [f"vertical_gap: {gap:.4f}", f"vertical_gap_at: {at}", f"nearest_gap: {near:.4f}",
            f"inner_low_z: {lo_inner:.4f}", f"content_high_z: {hi_content:.4f}", f"clearance_min: {LID_CLEARANCE_MIN:g}"]
    # otáčení víka: bedna, krabičky, podložka ani skořepina víka se nesmí dotknout dronu a baterií v žádné poloze
    worst = []
    for k in range(0, 37):
        lid.rotation_euler.x = math.radians(lid_open_deg(CASES[name]) * k / 36)
        bpy.context.view_layer.update()
        n = len(_bvh(inner + shell, inv).overlap(t_content))
        if n:
            worst.append((round(lid_open_deg(CASES[name]) * k / 36), n))
    out.append(f"sweep_overlaps: {worst}")
    lid.rotation_euler.x = 0.0
    bpy.context.view_layer.update()
    groups = {"base": base, "lid": shell, "crate": [o for o in inner if not o.name.startswith("casePad")],
              "pad": [O["casePad_vis"]], "drone": drone, "batteries": bats}
    total, acc = 0.0, Vector((0, 0, 0))
    for g, mass in CRATE_COM_MASSES:
        acc += _area_centroid(groups[g], inv) * mass
        total += mass
    com = acc / total
    out.append(f"centerOfMass_i3d: {com.x:.2f} {com.z:.2f} {-com.y:.2f}")
    return out


def crate_lid_previews(name, info):
    """Náhledy kufru s bednou ve víku do tmp/sampler/v3: zavřený, otevřený, průběh animace, řez zavřeného víka nad dronem."""
    os.makedirs(TMP_SAMPLER, exist_ok=True)
    out = lambda n: os.path.join(TMP_SAMPLER, f"{name}_{n}.png")  # noqa: E731
    key = CASES[name]["drone"]
    A = case_anim_times(CASES[name])
    set_hidden_render(hidden_names(key), True)
    show_samples((1, 2, 3, 7, 8), ())
    set_case_anim(key, info, 1.0)
    render(out("closed"), X.STORE_VIEW_DIR)
    render(out("closed_back"), Vector((-0.55, 0.75, 0.40)))
    render(out("closed_side"), Vector((0.0, -1.0, 0.12)))
    # řez: bez skořepiny spodku, pěny a víka zůstane dron, baterie, bedna s krabičkami a podložka v zavřené poloze
    hide = [bpy.data.objects[f"{name}_vis"], bpy.data.objects["caseLid_vis"]]
    hide += [o for o in bpy.data.objects if o.name.startswith("Brand")]
    for o in hide:
        o.hide_render = True
    render(out("section_front"), Vector((0.0, -1.0, 0.0)), res=1100)
    render(out("section_end"), Vector((-1.0, 0.0, 0.0)), res=1100)
    render(out("section_persp"), Vector((-0.5, -0.8, -0.25)), res=1100)
    for o in hide:
        o.hide_render = False
    for t in (0.10, 0.36, 0.56, 0.68, 0.75, 0.80, 0.85, 0.90, 0.95):
        set_case_anim(key, info, t)
        render(out(f"anim_{int(round(t * 100)):02d}"), X.STORE_VIEW_DIR, res=700)
    for t in (0.86, 0.91, 0.95):
        set_case_anim(key, info, t)
        render(out(f"anim_side_{int(round(t * 100)):02d}"), Vector((-1.0, 0.0, 0.10)), res=700)
    set_case_anim(key, info, A["lid"][0])
    render(out("open"), X.STORE_VIEW_DIR)
    set_case_anim(key, info, 0.0)
    render(out("deployed"), X.STORE_VIEW_DIR)
    set_case_anim(key, info, 1.0)


def export_case(name):
    cfg = CASES[name]
    key = cfg["drone"]
    root, info = build_case(name)
    set_hidden_render(hidden_names(key), True)
    os.makedirs(OUT_CASE, exist_ok=True)
    path = os.path.join(OUT_CASE, f"{name}.i3d")
    s = bpy.context.scene.I3D_UIexportSettings
    s.i3D_exportLights = True
    C.export_i3d(root, path)
    LI.shader_materials(path)
    C.zero_density(path)
    X.hide_nodes(path, hidden_names(key))
    names = mapped_names(name, key)
    mappings, found = X.i3d_mappings(path, names)
    nodes = i3d_nodes(path)
    os.makedirs(WORK, exist_ok=True)
    pre = DRONES[key]["prefix"]
    with open(os.path.join(WORK, f"{name}_export.txt"), "w", encoding="utf-8") as f:
        f.write(f"# {name}: {path}\n\n## strom uzlů\n{i3d_tree(path)}\n\n## i3dMappings\n{mappings}\n\n")
        f.write(f"## drone block parts ({pre})\n{drone_block(name, key, info, nodes)}\n\n")
        f.write(f"## animace víka, podložky a přenosu dronu (trailerFoldEnd=\"{CASE_ANIM['arms'][1]:g}\")\n{anim_xml(name, info)}\n\n")
        f.write("## uzly s polohou (i3d)\n")
        for n in ["caseLid", "casePad", "droneCarrier", "caseBatterySlot", "caseBatterySlot2", "caseChargeCable", pre + "Root", pre + "Tilt",
                  pre + "BatterySlot"] + \
                (["caseSampleBox", "caseSampleBoxLid", "caseSamples", "sampleSlot1", f"sampleSlot{NUM_BOX_SAMPLES}", "droneProbe",
                  "droneSampleBox1", "droneSampleBox2"] if key == "P" else []):
            if n not in nodes:
                continue
            el = nodes[n]
            f.write(f"{n}: t=({el.get('translation') or '0 0 0'}) r=({el.get('rotation') or '0 0 0'}) s=({el.get('scale') or '1 1 1'})\n")
        f.write(f"\narms (pivot, delta deg, length m): {info['arms']}\nblades (node, delta deg): {info['blades']}\n")
        f.write(f"drone root world (Blender): {info['drone_root_world']}\n")
        if cfg.get("crate_lid"):
            f.write("\n## zavřené víko nad obsahem (tools/test_case_lid.py)\n" + "\n".join(crate_lid_report(name)) + "\n")
    print(open(os.path.join(WORK, f"{name}_export.txt"), encoding="utf-8").read())

    # obrázek do obchodu: kufr otevřený, podložka rozložená, dron na ní rozložený; kabel skrytý; v bedně pár plných krabiček
    set_case_anim(key, info, 0.0)
    set_lid(None, 1.0 if key == "P" else None)
    if key == "P":
        show_samples(range(1, 6), ())
    store(os.path.join(WORK, f"store_{name}.png"), os.path.join(OUT_CASE, f"store_{name}.dds"))
    # náhledy: rozloženo, průběh animace (časy ve směru zavírání), zavřeno
    render(os.path.join(WORK, f"{name}_deployed.png"), X.STORE_VIEW_DIR)
    render(os.path.join(WORK, f"{name}_deployed_top.png"), Vector((0.02, -0.25, 1.0)))
    render(os.path.join(WORK, f"{name}_deployed_side.png"), Vector((0.0, -1.0, 0.12)))
    if key == "P":
        sampler_previews(name, info)
        show_samples((), ())
        set_hidden_render(hidden_names(key), True)
    set_lid(None, 0.0)
    for t in (0.10, 0.24, 0.36, 0.47, 0.55, 0.62, 0.67, 0.73, 0.85):
        set_case_anim(key, info, t)
        render(os.path.join(WORK, f"{name}_anim_{int(round(t * 100)):02d}.png"), X.STORE_VIEW_DIR, res=700)
    set_case_anim(key, info, 1.0)
    set_lid(None, 0.0)
    render(os.path.join(WORK, f"{name}_closed.png"), X.STORE_VIEW_DIR)
    render(os.path.join(WORK, f"{name}_closed_back.png"), Vector((-0.55, 0.75, 0.40)))
    set_hidden_render(hidden_names(key), False)
    if key == "P":
        show_samples(range(1, 4))
    set_case_anim(key, info, case_anim_times(cfg)["lid"][0])
    set_lid(None, 1.0)
    render(os.path.join(WORK, f"{name}_open.png"), X.STORE_VIEW_DIR)
    render(os.path.join(WORK, f"{name}_open_top.png"), Vector((0.02, -0.25, 1.0)))
    render(os.path.join(WORK, f"{name}_open_side.png"), Vector((0.0, -1.0, 0.15)))
    render(os.path.join(WORK, f"{name}_open_end.png"), Vector((1.0, 0.0, 0.25)))
    if key == "P":
        render(os.path.join(TMP_SAMPLER, f"{name}_open_case.png"), Vector((-0.30, -0.75, 1.0)))
        render(os.path.join(TMP_SAMPLER, f"{name}_open_case_top.png"), Vector((0.02, -0.25, 1.0)))
        render(os.path.join(TMP_SAMPLER, f"{name}_lid_top.png"), Vector((0.0, -0.02, 1.0)), objs=[bpy.data.objects["caseLid_vis"]])
        render(os.path.join(TMP_SAMPLER, f"{name}_back.png"), Vector((-0.45, 0.85, 0.55)))
        render(os.path.join(TMP_SAMPLER, f"{name}_side_x.png"), Vector((-1.0, 0.0, 0.12)))
    droot = bpy.data.objects[pre + "Root"]
    base = droot.matrix_basis.copy()
    droot.matrix_basis = Matrix.Translation((0, 0, 0.35 if key == "P" else 0.22)) @ base
    set_drone_unfold(key, info, 1.0)
    render(os.path.join(WORK, f"{name}_drone_unfolded.png"), X.STORE_VIEW_DIR)
    dobjs = [o for o in droot.children_recursive if o.type == "MESH" and not o.hide_render]
    render(os.path.join(WORK, f"{name}_drone_unfolded_top.png"), Vector((0.0, -0.05, 1.0)), objs=dobjs)
    render(os.path.join(WORK, f"{name}_drone_unfolded_side.png"), Vector((0.0, -1.0, 0.08)), objs=dobjs)
    set_drone_unfold(key, info, 0.0)
    render(os.path.join(WORK, f"{name}_drone_folded_top.png"), Vector((0.0, -0.05, 1.0)),
           objs=[o for o in droot.children_recursive if o.type == "MESH" and not o.hide_render])
    droot.matrix_basis = base
    bpy.context.view_layer.update()
    if cfg.get("crate_lid"):
        crate_lid_previews(name, info)
    set_case_anim(key, info, 1.0)
    set_lid(None, 0.0)
    set_hidden_render(hidden_names(key), True)
    bpy.context.view_layer.update()
    return info


def export_battery(key):
    root, name, size = build_battery_item(key)
    os.makedirs(OUT_BAT, exist_ok=True)
    path = os.path.join(OUT_BAT, f"{name}.i3d")
    C.export_i3d(root, path)
    LI.shader_materials(path)
    patch_decal_texture(path)
    C.zero_density(path)
    names = [root.name, f"{name}_vis", "floorCollision01"] + [f"batteryLed{i}" for i in range(4)]
    mappings, found = X.i3d_mappings(path, names)
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, f"{name}_export.txt"), "w", encoding="utf-8") as f:
        f.write(f"# {name}: {path}\nsize (m): {size[0]:.3f} x {size[1]:.3f} x {size[2]:.3f}\nmass (kg): {BATTERY_MASS[key]}\n\n")
        f.write(f"## strom uzlů\n{i3d_tree(path)}\n\n## i3dMappings\n{mappings}\n")
    print(open(os.path.join(WORK, f"{name}_export.txt"), encoding="utf-8").read())
    store(os.path.join(WORK, f"store_{name}.png"), os.path.join(OUT_BAT, f"store_{name}.dds"))
    render(os.path.join(WORK, f"{name}_preview.png"), Vector((0.6, -0.8, 0.5)), res=600)
    return size


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    C.wipe()
    done = []
    for name in CASES:
        if not only or name in only:
            export_case(name)
            finish_scene(name)
            done.append(name)
    if not only or "batteries" in only:
        for key in ("S", "M", "L", "C", "P"):
            # wipe by smazal hotové kufry; baterie se staví ve vlastní scéně a do .blend se neukládají
            export_battery(key)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    for name in done:
        build_case(name)
        finish_scene(name)
    for o in bpy.data.objects:
        o.hide_set(False)
        o.hide_render = False
    off = 0.0
    for name in done:
        r = bpy.data.objects[f"{name}:{name}_main_component1"]
        r.location.x = off
        off += CASES[name]["size"][0] + 0.4
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
