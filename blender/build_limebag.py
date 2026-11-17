"""Pytel jemně mletého vápna jako herní objekt (pallet) ve dvou velikostech, 50 l a 100 l: objects/limeBag/limeBag<litrů>.{i3d,xml},
potisk a ikona obchodu. Samostatný skript nad prázdnou scénou (postup build_canister.py):

    blender.exe -b --python blender\\build_limebag.py

Velikosti jsou v SIZES (měřítko vůči pytli 20 l; ten se nevyrábí a zůstává jen jako měřidlo ve srovnávacím snímku compare.png).
Pytel 20 l je polštář 0,52 x 0,30 x 0,12 m: tělo se zvedá do oblého hřbetu, boky a lisované konce (4 cm, jemně zvlněný šev) jsou
ploché. Celý povrch má jednu texturu (potisk shora, planární UV), takže štítek leží na hřbetu bez plovoucí plošky. Uspořádání
jako vanilla pallet a kanystr: kořen = dynamický compound s kolizemi, dynamicMountTrigger, fillTrigger, viditelný mesh,
kolize podlahy a uzel canisterCap (konec pytle, odkud se sype). Materiál po exportu přepsán na vehicleShader s detailLibrary
(bez vmask), jako u kanystru.
"""

import contextlib
import importlib
import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

import addon_utils
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export_middle_mod as X  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects", "limeBag")
TEX_DIR = os.path.join(OUT_DIR, "textures")
WORK_DIR = os.environ.get("SDT_LIMEBAG_WORK") or os.path.join(PROJECT, "out", "limebag")
GAME_DIR = X.GAME_DIR

BASE = dict(HX=0.22, HY=0.15, FL=0.04, HT=0.068, HB=0.052)   # pytel 20 l: polovina těla po X, polovina šířky, lisovaný konec, hřbet nad středním řezem, prověšení dna
# litrů -> (měřítko vůči pytli 20 l, hmotnost v kg na štítku, cena, vyrábí se)
SIZES = {20: (1.0, 22, 60, False), 50: (1.44, 55, 150, True), 100: (1.71, 110, 300, True)}
LITERS = 50
HX = HY = FL = HT = HB = ZC = LEN = WID = HEIGHT = 0.0
GROUP_ROOT, MASK_ROOT = 0x10004, 0xfffffbff
GROUP_MOUNT, MASK_MOUNT = 0x20000000, 0x20000
GROUP_FILL, MASK_FILL = 0x20000000, 0x40000000
GROUP_FLOOR, MASK_FLOOR = 0x10000, 0xfffdfbff
MAT_NAME = "limebag_paper"
CAP_POS = (0.0, 0.0, 0.0)                # konec pytle uprostřed výšky, nastaví configure


def configure(liters):
    """Rozměry pytle dané velikosti (celé tělo se zvětšuje stejně, tvar i potisk zůstávají)."""
    global LITERS, HX, HY, FL, HT, HB, ZC, LEN, WID, HEIGHT, CAP_POS
    f = SIZES[liters][0]
    LITERS = liters
    HX, HY, FL, HT, HB = (BASE[k] * f for k in ("HX", "HY", "FL", "HT", "HB"))
    ZC = HB                              # střední řez (dno pytle se dotýká podlahy v z = 0)
    LEN = 2 * (HX + FL)
    WID = 2 * HY
    HEIGHT = ZC + HT
    CAP_POS = (HX + FL, 0.0, ZC)


def bag_name():
    return "limeBag%d" % LITERS


def wipe():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for b in list(coll):
            coll.remove(b)


def props(obj, **kw):
    for k, v in kw.items():
        obj["i3D_" + k] = v
    return obj


def box_object(name, parent, x0, x1, y0, y1, z0, z1, group, mask, **kw):
    """Neviditelný kvádr (kolize / trigger) s počátkem v počátku scény a vrcholy na místě."""
    me = bpy.data.meshes.new(name)
    verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.display_type = "WIRE"
    obj.hide_render = True
    return props(obj, collisionFilterGroup=str(group), collisionFilterMask=str(mask), nonRenderable=True, **kw)


def surfaces(x, y):
    """Horní a dolní plocha pytle v bodě (x, y) (z = 0 je podlaha)."""
    u = min(abs(x) / HX, 1.0)
    v = abs(y) / HY
    s = (1.0 - u ** 2.6) ** 0.55 * (1.0 - v ** 2.4) ** 0.5            # tvar polštáře 0..1
    k = SIZES[LITERS][0]
    seam = 0.004 * k * (1.0 - v ** 6)                                       # tloušťka plochých okrajů
    wave = 0.004 * k * s * (math.sin(x * 38 + y * 11) * 0.6 + math.sin(x * 17 - y * 23) * 0.4)
    top = ZC + max(HT * s, seam) + wave
    bottom = ZC - max(HB * min(1.0, s * 1.7), seam)                     # dno je uprostřed ploché
    if abs(x) > HX:                                                     # lisovaný konec: drobné vlnky šíře
        crimp = 0.0013 * k * math.sin(y * 210 / k)
        top += crimp
        bottom += crimp
    return top, bottom


def bag_mesh(parent, name=None):
    import bmesh
    nx, ny = 56, 26
    xs = [-(HX + FL) + LEN * i / nx for i in range(nx + 1)]
    ys = [-HY + WID * j / ny for j in range(ny + 1)]
    bm = bmesh.new()
    top = [[None] * (ny + 1) for _ in range(nx + 1)]
    bot = [[None] * (ny + 1) for _ in range(nx + 1)]
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            zt, zb = surfaces(x, y)
            top[i][j] = bm.verts.new((x, y, zt))
            bot[i][j] = bm.verts.new((x, y, zb))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            bm.faces.new((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
    for j in range(ny):                                                 # uzavření lisovaných konců
        bm.faces.new((top[0][j], top[0][j + 1], bot[0][j + 1], bot[0][j]))
        bm.faces.new((top[nx][j], bot[nx][j], bot[nx][j + 1], top[nx][j + 1]))
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)       # boky: horní a dolní plocha se v okraji potkají
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        f.smooth = True
        for loop in f.loops:
            x, y, _ = loop.vert.co
            loop[uv].uv = ((x + LEN / 2) / LEN, (y + WID / 2) / WID)
    name = name or bag_name() + "_vis"
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = Matrix.Identity(4)
    mat = bpy.data.materials.new(MAT_NAME + "_%d" % LITERS if parent is None else MAT_NAME)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(WORK_DIR, "limebag%d_label.png" % LITERS))
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    obj.data.materials.append(mat)
    return props(obj, clipDistance=100.0)


def build():
    wipe()
    name = bag_name()
    root = box_object(f"{name}_main_component1", None, -LEN / 2, LEN / 2, -WID / 2, WID / 2, 0.0, HEIGHT,
                      GROUP_ROOT, MASK_ROOT, dynamic=True, compound=True, staticFriction=1.0, dynamicFriction=1.0,
                      density=0.0, clipDistance=150.0)
    box_object("dynamicMountTrigger", root, -LEN / 2 - 0.025, LEN / 2 + 0.025, -WID / 2 - 0.025, WID / 2 + 0.025, 0.0, 0.04,
               GROUP_MOUNT, MASK_MOUNT, kinematic=True, trigger=True)
    box_object("fillTrigger", root, -LEN / 2 - 0.04, LEN / 2 + 0.04, -WID / 2 - 0.04, WID / 2 + 0.04, 0.0, HEIGHT + 0.04,
               GROUP_FILL, MASK_FILL, kinematic=True, compound=True, trigger=True)
    cap = bpy.data.objects.new("capNode", None)
    bpy.context.scene.collection.objects.link(cap)
    cap.parent = root
    cap.matrix_parent_inverse = Matrix.Identity(4)
    cap.location = CAP_POS
    cols = bpy.data.objects.new("collisions", None)
    bpy.context.scene.collection.objects.link(cols)
    cols.parent = root
    cols.matrix_parent_inverse = Matrix.Identity(4)
    props(cols, clipDistance=10.0)
    box_object("floorCollision01", cols, -LEN / 2, LEN / 2, -WID / 2, WID / 2, 0.0, HEIGHT, GROUP_FLOOR, MASK_FLOOR,
               compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    vis = bag_mesh(root)
    bpy.context.view_layer.update()
    return root, vis


def export_i3d(root, path):
    s = bpy.context.scene.I3D_UIexportSettings
    s.i3D_exportUseSoftwareFileName = False
    s.i3D_exportFileLocation = path
    s.i3D_gameLocationDisplay = GAME_DIR
    s.i3D_binaryFiles = True
    s.i3D_exportAxisOrientations = "BAKE_TRANSFORMS"
    s.i3D_exportRelativePaths = True
    s.i3D_exportAnimation = False
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in [root] + list(root.children_recursive):
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    for f in (path, path + ".shapes"):
        if os.path.exists(f):
            os.remove(f)
    exp = importlib.import_module("io_export_i3d_reworked.i3d_export")
    sel = importlib.import_module("io_export_i3d_reworked.util.selectionUtil")
    outliner_nodes = sel.get_outliner_selected_nodes
    sel.get_outliner_selected_nodes = lambda: None
    screen = bpy.context.screen
    area = next((a for a in screen.areas if a.type == "VIEW_3D"), None) if screen else None
    override = (bpy.context.temp_override(area=area, region=next(r for r in area.regions if r.type == "WINDOW"))
                if area else contextlib.nullcontext())
    try:
        with override:
            exp.I3DExportSelected()
    finally:
        sel.get_outliner_selected_nodes = outliner_nodes
    for f in (path, path + ".shapes"):
        if not os.path.exists(f):
            raise RuntimeError(f"export nevytvořil {f}")


def zero_density(path):
    """Exportér zapisuje density 0 jako 0.0001; vanilla palety mají 0 (hmotnost dává komponenta v XML)."""
    tree = ET.parse(path)
    for el in tree.getroot().find("Scene").iter("Shape"):
        if el.get("density") == "0.0001":
            el.set("density", "0")
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")


def vehicle_shader_materials(path):
    """Materiál exportu -> vehicleShader (postup build_canister), potisk jako Texture, bez vmask: výchozí vmask hry."""
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
    tpl = templates["plasticPainted"]
    extra = {"smoothnessScale": "0.12", "clearCoatIntensity": "0", "clearCoatSmoothness": "0", "metalnessScale": "0"}
    for mat in root.find("Materials"):
        if mat.get("name") != MAT_NAME:
            continue
        for child in list(mat):
            mat.remove(child)
        for attr in ("specularColor", "customShaderVariation", "alphaBlending"):
            mat.attrib.pop(attr, None)
        mat.set("customShaderId", shader)
        params = {"colorScale": "1 1 1"}
        for p in ("porosity", "smoothnessScale", "metalnessScale", "clearCoatIntensity", "clearCoatSmoothness"):
            if p in tpl:
                params[p] = tpl[p]
        params.update(extra)
        for p in sorted(params):
            ET.SubElement(mat, "CustomParameter", name=p, value=params[p])
        for m in ("detailDiffuse", "detailNormal", "detailSpecular"):
            ET.SubElement(mat, "Custommap", name=m, fileId=file_id(tpl[m]))
        for tag, fname in (("Texture", "textures/limebag%d_label.dds" % LITERS), ("Normalmap", X.BASE_MAPS["Normalmap"]),
                           ("Glossmap", "$data/shared/default_vmask.png")):
            ET.SubElement(mat, tag, fileId=file_id(fname))
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")


XML = """<?xml version="1.0" encoding="utf-8" standalone="no" ?>
<!-- Pravidla objektu ručně; i3d, obrázek a čísla v i3dMappings dává blender/build_limebag.py. Cestu k souboru čte SprayDroneToolbox.lua. -->
<vehicle type="pallet">
    <annotation>Pytel @LITERS@ l jemně mletého vápna z koncentrátové nádrže servisního vleku (Ctrl+I); herní objekt typu pallet.</annotation>

    <storeData>
        <name>$l10n_sdt_limeBag@LITERS@_name</name>
        <functions>
            <function>$l10n_sdt_limeBag_function</function>
        </functions>
        <specs>
            <capacity>@LITERS@</capacity>
            <fillTypes>SDT_FINE_LIME</fillTypes>
            <weight ignore="true"/>
        </specs>
        <image>objects/limeBag/store_limeBag@LITERS@.dds</image>
        <price>@PRICE@</price>
        <allowLeasing>false</allowLeasing>
        <canBeSold>false</canBeSold>
        <showInStore>false</showInStore>
        <rotation>0</rotation>
        <shopHeight>0.2</shopHeight>
        <brand>BZUK</brand>
        <!-- první kategorie (kořenová) je vanilla typu OBJECTS: seznam vlastněných v obchodě (FS25_GarageMenu) podle ní spotřební věci vynechá jako vanilla palety -->
        <category>pallets sprayDroneCanisters</category>
        <financeCategory>PURCHASE_FERTILIZER</financeCategory>
    </storeData>

    <base>
        <typeDesc>$l10n_typeDesc_pallet</typeDesc>
        <filename>objects/limeBag/limeBag@LITERS@.i3d</filename>
        <size width="@WIDTH@" length="@LENGTH@" height="@HEIGHT@"/>
        <canBeReset>false</canBeReset>
        <supportsPickUp>true</supportsPickUp>
        <components>
            <component centerOfMass="0 @COM@ 0" solverIterationCount="10" mass="1"/>
        </components>
        <showInVehicleMenu>false</showInVehicleMenu>
        <mapHotspot available="false"/>
        <input allowed="false"/>
    </base>

    <fillUnit>
        <fillUnitConfigurations>
            <fillUnitConfiguration>
                <fillUnits removeVehicleIfEmpty="true">
                    <fillUnit unitTextOverride="$l10n_unit_literShort" fillTypes="SDT_FINE_LIME" capacity="@LITERS@" startFillType="SDT_FINE_LIME" startFillLevel="@LITERS@" ignoreFillLimit="true" updateMass="false">
                        <fillRootNode node="0&gt;"/>
                    </fillUnit>
                </fillUnits>
            </fillUnitConfiguration>
        </fillUnitConfigurations>
    </fillUnit>

    <fillTriggerVehicle triggerNode="fillTrigger" fillUnitIndex="1" litersPerSecond="@LITERS@"/>

    <dynamicMount triggerNode="dynamicMountTrigger" triggerForceAcceleration="4" additionalMountDistance="0.09" jointTransY="0.02" jointLimitToRotY="true"/>

@MAPPINGS@
</vehicle>
"""


def write_xml(found, names):
    ids = {"capNode": "canisterCap"}
    price = SIZES[LITERS][2]
    lines = ["    <i3dMappings>"]
    lines += [f'        <i3dMapping id="{ids.get(n, n)}" node="{found[n].replace(">", "&gt;")}"/>' for n in names]
    lines.append("    </i3dMappings>")
    text = (XML.replace("@LITERS@", str(LITERS)).replace("@PRICE@", str(price)).replace("@WIDTH@", "%.2f" % LEN).replace("@LENGTH@", "%.2f" % WID).replace("@HEIGHT@", "%.2f" % HEIGHT)
            .replace("@COM@", "%.2f" % (HEIGHT * 0.4)).replace("@MAPPINGS@", "\n".join(lines)))
    ET.fromstring(text.encode("utf-8"))
    with open(os.path.join(OUT_DIR, "limeBag%d.xml" % LITERS), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render(path, direction, store=False, size=None):
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.film_transparent = store
    sc.render.resolution_x = sc.render.resolution_y = X.STORE_RES if store else 900
    if size:
        sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = -0.3
    for ob in [o for o in bpy.data.objects if o.name.startswith("_")]:
        bpy.data.objects.remove(ob, do_unlink=True)
    world = bpy.data.worlds.get("_w") or bpy.data.worlds.new("_w")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.8, 0.82, 0.86, 1.0)
    bg.inputs[1].default_value = 0.7
    sc.world = world
    for name, energy, rot in (("_key", 3.2, (0.75, 0.15, -0.55)), ("_fill", 1.0, (1.1, -0.2, 2.4))):
        data = bpy.data.lights.new(name, "SUN")
        data.energy = energy
        data.angle = 0.2
        ob = bpy.data.objects.new(name, data)
        ob.rotation_euler = rot
        sc.collection.objects.link(ob)
    cd = bpy.data.cameras.new("_cam")
    cd.lens = 200
    cd.clip_start = 0.05
    cam = bpy.data.objects.new("_cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render]
    X._fit_camera(cam, objs, direction, margin=0.05, drop=0.05 if store else 0.0)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def flat_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = color
    return mat


def compare():
    """Srovnávací snímek: pytle 20 l (jen měřidlo), 50 l a 100 l vedle kanystru 20 l (0,26 x 0,18 x 0,34 m) a metru s ryskami po 10 cm."""
    wipe()
    x = 0.0
    for liters in sorted(SIZES):
        configure(liters)
        obj = bag_mesh(None, "cmp_%d" % liters)
        obj.location = (x + LEN / 2, 0.0, 0.0)
        x += LEN + 0.12
    canister = bpy.data.objects.new("cmp_canister", bpy.data.meshes.new("cmp_canister"))
    cw, cd, ch = 0.26, 0.18, 0.34
    canister.data.from_pydata([(a, b, c) for a in (0, cw) for b in (-cd / 2, cd / 2) for c in (0, ch)], [],
                              [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    canister.data.update()
    canister.location = (x, 0.0, 0.0)
    bpy.context.scene.collection.objects.link(canister)
    mat = flat_material("cmp_canister", (0.55, 0.8, 0.15, 1.0))
    canister.data.materials.append(mat)
    for i in range(0, 10):                                   # metr po ryskách 10 cm před pytli, střídavě tmavé a světlé
        bar = bpy.data.objects.new("cmp_ruler%d" % i, bpy.data.meshes.new("cmp_ruler%d" % i))
        bar.data.from_pydata([(a, b, c) for a in (i * 0.1, i * 0.1 + 0.1) for b in (-0.32, -0.30) for c in (0, 0.004)], [],
                             [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
        bar.data.update()
        bpy.context.scene.collection.objects.link(bar)
        m = flat_material("cmp_ruler%d" % i, (0.08, 0.08, 0.08, 1.0) if i % 2 == 0 else (0.92, 0.92, 0.9, 1.0))
        bar.data.materials.append(m)
    bpy.context.view_layer.update()
    render(os.path.join(WORK_DIR, "compare.png"), Vector((0.15, -0.95, 0.45)), size=(1600, 600))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TEX_DIR, exist_ok=True)
    os.makedirs(WORK_DIR, exist_ok=True)
    py = X.shutil.which("python") or X.shutil.which("py")
    for liters, (_, kg, _, produce) in sorted(SIZES.items()):
        subprocess.run([py, os.path.join(HERE, "limebag_label.py"), WORK_DIR, str(liters), str(kg)], check=True)
    for liters, (_, _, _, produce) in sorted(SIZES.items()):
        if not produce:
            continue
        configure(liters)
        root, vis = build()
        X.png2dds(os.path.join(WORK_DIR, "limebag%d_label.png" % liters), os.path.join(TEX_DIR, "limebag%d_label.dds" % liters), "dxt1")
        path = os.path.join(OUT_DIR, "limeBag%d.i3d" % liters)
        export_i3d(root, path)
        vehicle_shader_materials(path)
        zero_density(path)
        names = [root.name, bag_name() + "_vis", "floorCollision01", "dynamicMountTrigger", "fillTrigger", "capNode"]
        mappings, found = X.i3d_mappings(path, names)
        print(mappings)
        write_xml(found, names)
        render(os.path.join(WORK_DIR, "prev%d_top.png" % liters), Vector((0.45, -0.55, 0.70)))
        render(os.path.join(WORK_DIR, "prev%d_side.png" % liters), Vector((0.30, -0.90, 0.18)))
        render(os.path.join(WORK_DIR, "prev%d_end.png" % liters), Vector((0.95, -0.20, 0.25)))
        render(os.path.join(WORK_DIR, "store_limeBag%d.png" % liters), Vector((0.45, -0.55, 0.70)), store=True)
        X.png2dds(os.path.join(WORK_DIR, "store_limeBag%d.png" % liters), os.path.join(OUT_DIR, "store_limeBag%d.dds" % liters), "dxt5", "--size", "512", "--no-mips")
    compare()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
