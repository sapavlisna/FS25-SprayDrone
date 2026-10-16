"""Kanystr s koncentrátem jako herní objekt (pallet) pro obchod: objects/canister/canister{Fertilizer,Herbicide}.i3d,
štítky a ikony obchodu. Samostatný skript nad prázdnou scénou, s vleku nic nebere:

    blender.exe -b --python blender\\build_canister.py

Tvar je shodný s toolboxCanister v bedně (sdt_tanks.build_canister), navíc barevné víčko a štítek (vlastní malá
textura, sdílený atlas polepek se nemění). Uspořádání jako vanilla pallet: kořen = dynamický compound s kolizemi,
dynamicMountTrigger, fillTrigger, viditelný mesh a kolize podlahy. Materiály se po exportu přepíšou na vehicleShader
s detailLibrary jako u vleku (export_middle_mod.apply_vehicle_shader), jen bez vmask (výchozí vmask hry).
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
import sdt_parts as P  # noqa: E402
import sdt_tanks as T  # noqa: E402
from sdt_tanks import V  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects", "canister")
TEX_DIR = os.path.join(OUT_DIR, "textures")
WORK_DIR = os.environ.get("SDT_CANISTER_WORK") or os.path.join(PROJECT, "out", "agentK")
GAME_DIR = X.GAME_DIR

KINDS = {
    "Fertilizer": dict(label="fertilizer", color=(0.55, 0.80, 0.15)),
    "Herbicide": dict(label="herbicide", color=(0.85, 0.25, 0.08)),
    "Diesel": dict(label="diesel", color=(0.93, 0.70, 0.06)),
}
CAP_COLOR = (0.04, 0.04, 0.045)
W, D, H = T.CANISTER
LABEL_W, LABEL_H, LABEL_Z0 = 0.168, 0.084, 0.063    # štítek 2:1 jako textura 512x256, mezi žebry těla (žebra ve výšce 0,05 a 0,16)
TOP = H + 0.016
CAP_TOP = TOP + 0.041                                # horní plocha víčka hrdla
COL_HEIGHT = CAP_TOP                                 # kolizní kvádr do horní hrany hrdla
NECK_X = 0.062                                       # osa hrdla po X
GROUP_ROOT, MASK_ROOT = 0x10004, 0xfffffbff
GROUP_MOUNT, MASK_MOUNT = 0x20000000, 0x20000
GROUP_FILL, MASK_FILL = 0x20000000, 0x40000000
GROUP_FLOOR, MASK_FLOOR = 0x10000, 0xfffdfbff


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


def canister_geometry(m, mat_body, mat_cap):
    """Geometrie sdt_tanks.build_canister (počátek uprostřed základny), víčko s vroubky ve vlastním materiálu."""
    T.canister_shape(m, V(0, 0, 0), mat_body, mat_cap)


def label_mesh(name, parent, label_png):
    """Dvě ploténky štítku (na obou širokých stranách těla), UV 0..1 přes celou texturu, text čitelný zvenku."""
    import bmesh
    bm = bmesh.new()
    uv = bm.loops.layers.uv.verify()
    z0, z1 = LABEL_Z0, LABEL_Z0 + LABEL_H
    for sy in (-1, 1):
        y = sy * (D / 2 + 0.0025)
        xs = (-LABEL_W / 2, LABEL_W / 2) if sy < 0 else (LABEL_W / 2, -LABEL_W / 2)
        quad = [bm.verts.new((xs[0], y, z0)), bm.verts.new((xs[1], y, z0)),
                bm.verts.new((xs[1], y, z1)), bm.verts.new((xs[0], y, z1))]
        f = bm.faces.new(quad if sy < 0 else quad[::-1])
        f.smooth = False
        for loop in f.loops:
            x, _, z = loop.vert.co
            loop[uv].uv = (0.5 - sy * x / LABEL_W, (z - z0) / LABEL_H)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    mat = bpy.data.materials.new("canister_label")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(label_png)
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    obj.data.materials.append(mat)
    return obj


def build_kind(kind, cfg):
    """Scéna jednoho kanystru; vrací (kořen, [viditelné meshe])."""
    wipe()
    P.MATERIALS["canister_body"] = (cfg["color"], 0.0, 0.45)
    P.MATERIALS["canister_cap"] = (CAP_COLOR, 0.0, 0.5)
    name = f"canister{kind}"
    root = box_object(f"{name}_main_component1", None, -W / 2, W / 2, -D / 2, D / 2, 0.0, COL_HEIGHT,
                      GROUP_ROOT, MASK_ROOT, dynamic=True, compound=True, staticFriction=1.0, dynamicFriction=1.0,
                      density=0.0, clipDistance=150.0)
    box_object("dynamicMountTrigger", root, -W / 2 - 0.025, W / 2 + 0.025, -D / 2 - 0.025, D / 2 + 0.025, 0.0, 0.04,
               GROUP_MOUNT, MASK_MOUNT, kinematic=True, trigger=True)
    box_object("fillTrigger", root, -W / 2 - 0.04, W / 2 + 0.04, -D / 2 - 0.04, D / 2 + 0.04, 0.0, COL_HEIGHT + 0.04,
               GROUP_FILL, MASK_FILL, kinematic=True, compound=True, trigger=True)
    cap = bpy.data.objects.new("capNode", None)
    bpy.context.scene.collection.objects.link(cap)
    cap.parent = root
    cap.matrix_parent_inverse = Matrix.Identity(4)
    cap.location = (NECK_X, 0.0, CAP_TOP)
    cols = bpy.data.objects.new("collisions", None)
    bpy.context.scene.collection.objects.link(cols)
    cols.parent = root
    cols.matrix_parent_inverse = Matrix.Identity(4)
    props(cols, clipDistance=10.0)
    box_object("floorCollision01", cols, -W / 2, W / 2, -D / 2, D / 2, 0.0, COL_HEIGHT, GROUP_FLOOR, MASK_FLOOR,
               compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)

    P._root = root
    P._coll = bpy.context.scene.collection
    m = T.Mesh(f"{name}_vis")
    canister_geometry(m, "canister_body", "canister_cap")
    vis = m.finish()
    props(vis, clipDistance=100.0)
    label = label_mesh(f"{name}_label", root, os.path.join(WORK_DIR, f"canister_label_{cfg['label']}.png"))
    props(label, clipDistance=40.0)
    bpy.context.view_layer.update()
    return root, [vis, label]


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


def vehicle_shader_materials(path, cfg):
    """Materiály exportu -> vehicleShader (postup export_middle_mod.apply_vehicle_shader), bez vmask: výchozí vmask hry."""
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
    spec = {
        "canister_body": ("plasticPainted", cfg["color"], {}),
        "canister_cap": ("plasticPainted", CAP_COLOR, {}),
        "canister_label": ("plasticPainted", (1.0, 1.0, 1.0), {"clearCoatIntensity": "0.3", "clearCoatSmoothness": "0.7"}),
    }
    for mat in root.find("Materials"):
        name = mat.get("name")
        if name not in spec:
            continue
        tpl_name, color, extra = spec[name]
        tpl = templates[tpl_name]
        for child in list(mat):
            mat.remove(child)
        for attr in ("specularColor", "customShaderVariation", "alphaBlending"):
            mat.attrib.pop(attr, None)
        mat.set("customShaderId", shader)
        params = {"colorScale": "%g %g %g" % color}
        for p in ("porosity", "smoothnessScale", "metalnessScale", "clearCoatIntensity", "clearCoatSmoothness"):
            if p in tpl:
                params[p] = tpl[p]
        params.update(extra)
        for p in sorted(params):
            ET.SubElement(mat, "CustomParameter", name=p, value=params[p])
        for m in ("detailDiffuse", "detailNormal", "detailSpecular"):
            ET.SubElement(mat, "Custommap", name=m, fileId=file_id(tpl[m]))
        diffuse = f"textures/canister_label_{cfg['label']}.dds" if name == "canister_label" else X.BASE_MAPS["Texture"]
        for tag, fname in (("Texture", diffuse), ("Normalmap", X.BASE_MAPS["Normalmap"]),
                           ("Glossmap", "$data/shared/default_vmask.png")):
            ET.SubElement(mat, tag, fileId=file_id(fname))
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")


def write_mappings(xml_path, found, names):
    """Přepíše blok <i3dMappings> v XML objektu podle čísel z čerstvého i3d (capNode = canisterCap)."""
    ids = {"capNode": "canisterCap"}
    lines = ["    <i3dMappings>"]
    lines += [f'        <i3dMapping id="{ids.get(n, n)}" node="{found[n].replace(">", "&gt;")}"/>' for n in names]
    lines.append("    </i3dMappings>")
    text = open(xml_path, encoding="utf-8").read()
    a, b = text.index("    <i3dMappings>"), text.index("</i3dMappings>") + len("</i3dMappings>")
    open(xml_path, "w", encoding="utf-8", newline="").write(text[:a] + "\n".join(lines) + text[b:])


def store_image(root, out_dds, png):
    sc = bpy.context.scene
    state = (sc.render.engine, sc.render.film_transparent, sc.render.resolution_x, sc.render.resolution_y,
             sc.render.resolution_percentage, sc.camera, sc.world, sc.render.filepath)
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = X.STORE_RES
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = -0.3
    world = bpy.data.worlds.new("_store_world")
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
    X._fit_camera(cam, objs, X.STORE_VIEW_DIR, margin=0.05, drop=0.05)
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)
    X.png2dds(png, out_dds, "dxt5", "--size", "512", "--no-mips")
    (sc.render.engine, sc.render.film_transparent, sc.render.resolution_x, sc.render.resolution_y,
     sc.render.resolution_percentage, sc.camera, sc.world, sc.render.filepath) = state


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(TEX_DIR, exist_ok=True)
    os.makedirs(WORK_DIR, exist_ok=True)
    py = X.shutil.which("python") or X.shutil.which("py")
    subprocess.run([py, os.path.join(HERE, "canister_labels.py"), WORK_DIR], check=True)
    for kind, cfg in KINDS.items():
        root, vis = build_kind(kind, cfg)
        X.png2dds(os.path.join(WORK_DIR, f"canister_label_{cfg['label']}.png"),
                  os.path.join(TEX_DIR, f"canister_label_{cfg['label']}.dds"), "dxt1")
        path = os.path.join(OUT_DIR, f"canister{kind}.i3d")
        export_i3d(root, path)
        vehicle_shader_materials(path, cfg)
        zero_density(path)
        names = [root.name, f"canister{kind}_vis", "floorCollision01", "dynamicMountTrigger", "fillTrigger", "capNode"]
        mappings, found = X.i3d_mappings(path, names)
        print(f"{kind}: {path}")
        print(mappings)
        write_mappings(os.path.join(OUT_DIR, f"canister{kind}.xml"), found, names)
        store_image(root, os.path.join(OUT_DIR, f"store_canister{kind}.dds"), os.path.join(WORK_DIR, f"store_{kind}.png"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
