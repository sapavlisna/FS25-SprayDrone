"""Export vlastních disků (sdt_rims.py) do módu: mod/FS25_SprayDroneTrailer/wheels/sdtRim22.i3d a sdtRim17.i3d.

Každý soubor má kořen sdtRim<typ> a pod ním levý (uzel 0|0) a pravý (0|1) tvar; vehicle XML na ně odkazuje přes
<outerRim filename="wheels/sdtRim22.i3d" node="0|0"/>. Materiály jsou vehicleShader bez varianty (jako vanilla
wheelChock01): bílá textura, výchozí normála a vmask, barva a detailní mapy ze šablony detailLibrary.

Bez okna: blender.exe -b --python blender\\export_rims.py [-- render]
"""

import contextlib
import importlib
import io
import math
import os
import sys
import xml.etree.ElementTree as ET

import addon_utils
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sdt_parts as P  # noqa: E402
import sdt_rims as RIMS  # noqa: E402

PROJECT = os.path.dirname(HERE)
MOD_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer")
OUT_DIR = os.path.join(MOD_DIR, "wheels")
SHOT_DIR = os.path.join(PROJECT, "tmp", "rims")
import sdt_paths  # noqa: E402

GAME_DIR = sdt_paths.GAME_DIR
TEMPLATES_XML = os.path.join(GAME_DIR, "data", "shared", "detailLibrary", "materialTemplates.xml")
SHADER = "$data/shaders/vehicleShader.xml"
MAPS = {"Texture": "$data/shared/white_diffuse.png", "Normalmap": "$data/shared/default_normal.png",
        "Glossmap": "$data/shared/default_vmask.png"}
MATERIAL_MAP = {
    "SDT_RimPaint": ("metalPainted", (0.55, 0.56, 0.58)),   # po exportu přejmenovaný na rim_outer_mat (RIM_NAMES): tak ho hra přebarvuje podle rimColorConfigurations
    "SDT_Steel": ("metalGalvanized", None),
    "SDT_NutIndicator": ("plasticPainted", (0.95, 0.40, 0.02)),
    "SDT_Rubber": ("rubberBlack", (0.03, 0.03, 0.03)),
}
RIM_NAMES = {"SDT_RimPaint": "rim_outer_mat"}
KINDS = {"R22": "sdtRim22", "R15": "sdtRim15"}


def export_selected(objs, path):
    s = bpy.context.scene.I3D_UIexportSettings
    s.i3D_exportUseSoftwareFileName = False
    s.i3D_exportFileLocation = path
    s.i3D_gameLocationDisplay = GAME_DIR
    s.i3D_binaryFiles = True
    s.i3D_exportAxisOrientations = "BAKE_TRANSFORMS"
    s.i3D_exportRelativePaths = True
    s.i3D_exportLights = False
    s.i3D_exportCameras = False
    s.i3D_exportAnimation = False
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
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
    log = io.StringIO()
    try:
        with contextlib.redirect_stdout(log), override:
            exp.I3DExportSelected()
    finally:
        sel.get_outliner_selected_nodes = outliner_nodes
    for f in (path, path + ".shapes"):
        if not os.path.exists(f):
            raise RuntimeError(f"export nevytvořil {f}\n{log.getvalue()[-2000:]}")


def apply_shader(path):
    templates = {t.get("name"): t.attrib for t in ET.parse(TEMPLATES_XML).getroot().iter("template")}
    tree = ET.parse(path)
    root = tree.getroot()
    files = root.find("Files")
    if files is None:
        files = ET.Element("Files")
        root.insert(0, files)
    by_name = {f.get("filename"): f.get("fileId") for f in files}
    next_id = [max([int(f.get("fileId")) for f in files] + [0]) + 1]

    def file_id(name):
        if name not in by_name:
            ET.SubElement(files, "File", fileId=str(next_id[0]), filename=name)
            by_name[name] = str(next_id[0])
            next_id[0] += 1
        return by_name[name]

    shader_id = file_id(SHADER)
    for mat in root.find("Materials"):
        tpl_name, color = MATERIAL_MAP[mat.get("name")]
        mat.set("name", RIM_NAMES.get(mat.get("name"), mat.get("name")))
        tpl = templates[tpl_name]
        for child in list(mat):
            mat.remove(child)
        for attr in ("specularColor", "customShaderVariation", "alphaBlending"):
            mat.attrib.pop(attr, None)
        mat.set("customShaderId", shader_id)
        scale = color if color is not None else tuple(float(v) for v in tpl.get("colorScale", "1 1 1").split())
        params = {"colorScale": "%g %g %g" % scale}
        for p in ("porosity", "smoothnessScale", "metalnessScale", "clearCoatIntensity", "clearCoatSmoothness"):
            if p in tpl:
                params[p] = tpl[p]
        for p in sorted(params):
            ET.SubElement(mat, "CustomParameter", name=p, value=params[p])
        for m in ("detailDiffuse", "detailNormal", "detailSpecular"):
            ET.SubElement(mat, "Custommap", name=m, fileId=file_id(tpl[m]))
        for tag, fname in MAPS.items():
            ET.SubElement(mat, tag, fileId=file_id(fname))
    referenced = {el.get(a) for el in root.iter() if el.tag != "File"
                  for a in ("fileId", "customShaderId") if el.get(a)}
    for f in list(files):
        if f.get("fileId") not in referenced:
            files.remove(f)
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")


def check_nodes(path, root_name):
    """Uzel 0|0 musí být levý tvar a 0|1 pravý (tak na ně odkazuje vehicle XML)."""
    scene = ET.parse(path).getroot().find("Scene")
    top = list(scene)[0]
    kids = [c.get("name") for c in top]
    if top.get("name") != root_name or kids[:2] != [root_name + "L", root_name + "R"]:
        raise RuntimeError(f"{path}: nečekané pořadí uzlů {top.get('name')} -> {kids}")


def render(objs, name):
    os.makedirs(SHOT_DIR, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 900, 900
    world = bpy.data.worlds.get("w") or bpy.data.worlds.new("w")
    world.color = (0.30, 0.31, 0.33)
    sc.world = world
    cam = bpy.data.objects.get("cam")
    if cam is None:
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        sc.collection.objects.link(cam)
    sc.camera = cam
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o not in objs
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    ctr = sum(pts, Vector()) / len(pts)
    size = max((p - ctr).length for p in pts)
    for view, d in (("out", Vector((1.0, -0.35, 0.25))), ("in", Vector((-1.0, -0.35, 0.25)))):
        cam.location = ctr + d.normalized() * size * 2.6
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(SHOT_DIR, f"{name}_{view}.png")
        bpy.ops.render.render(write_still=True)
        print("render:", sc.render.filepath)


def to_unit_space(kind, objs):
    """Vanilla disky jsou v i3d modelované s průměrem a šířkou kolem 1 (rim001: y,z ±0,53, x ±0,52) a hra je škáluje podle
    widthAndDiam (šířka a průměr v palcích * 0,0254 v metrech). Skutečné rozměry se proto před zápisem vydělí: x šířkou, y a z průměrem."""
    spec = RIMS.RIMS[kind]
    width_m = spec["width"]
    diam_m = spec["bead"] * 2
    for o in objs:
        o.data.transform(Matrix.Diagonal((1 / width_m, 1 / diam_m, 1 / diam_m, 1.0)))
        o.data.update()


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if "io_export_i3d_reworked" not in bpy.context.preferences.addons:
        addon_utils.enable("io_export_i3d_reworked", default_set=False)
    os.makedirs(OUT_DIR, exist_ok=True)
    P.begin("SDT_Rims", "rimsScene")
    for kind, root_name in KINDS.items():
        root, left, right = RIMS.build_rim_pair(kind, root_name)
        bpy.context.view_layer.update()
        if "render" in args:
            render([left], root_name + "L")
            render([right], root_name + "R")
        to_unit_space(kind, (left, right))
        path = os.path.join(OUT_DIR, root_name + ".i3d")
        export_selected([root, left, right], path)
        apply_shader(path)
        check_nodes(path, root_name)
        dims = left.dimensions
        print(f"{root_name}: {len(left.data.polygons)} ploch na stranu, rozměr {dims.x:.3f} x {dims.y:.3f} m -> {path}")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
