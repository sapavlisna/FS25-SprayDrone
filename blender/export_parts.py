"""Export dílů knihovny jako samostatná i3d pro GIANTS Editor (jen pro prohlížení a katalog, do módu se nic neexportuje).

    blender.exe -b --factory-startup --python blender\\export_parts.py -- [<id dílu> ...]

Seznam dílů a variant čte z out/katalog/data/dily.json (úloha `dily` v catalog_render.py), každou variantu načte z cache knihovny
(blender/parts), nechá jen její objekty, přidá DirtUV a vyexportuje komunitním exportérem GIANTS i3d do tmp/ge/parts/<id>[__<varianta>].i3d.
Materiály dostanou vehicleShader jako ve vozidlech (export_middle_mod.apply_vehicle_shader), vmask je vanilla default_vmask, atlas
nálepek leží v tmp/ge/parts/textures. Vedle i3d vznikne <jméno>.json s rozsahem dílu v souřadnicích i3d (pro záběr kamery).
"""

import contextlib
import importlib
import io
import json
import math
import os
import shutil
import sys

import addon_utils
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
OUT = os.path.join(PROJECT, "tmp", "ge", "parts")
DATA = os.path.join(PROJECT, "out", "katalog", "data", "dily.json")
DECAL_SRC = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "vehicles", "sprayDroneTrailerMiddle", "textures", "sdt_decals.dds")


def part_name(item_id, variant_slug):
    return item_id + (f"__{variant_slug}" if variant_slug else "")


def load_variant(blend, keep):
    """Prázdná scéna, v ní objekty dílu z knihovny; zůstanou jen objekty z keep a jejich předci."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if "io_export_i3d_reworked" not in bpy.context.preferences.addons:
        addon_utils.enable("io_export_i3d_reworked", default_set=False)
    with open(blend[:-6] + ".json", encoding="utf-8") as fh:
        names = json.load(fh)["objects"]
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = list(names)
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    wanted = set(keep)
    for o in list(bpy.data.objects):
        if o.name in wanted:
            p = o.parent
            while p is not None:
                wanted.add(p.name)
                p = p.parent
    for o in list(bpy.data.objects):
        if o.name not in wanted:
            for c in list(o.children):
                if c.name in wanted:
                    w = c.matrix_world.copy()
                    c.parent = None
                    c.matrix_world = w
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
    for o in bpy.data.objects:
        o.hide_set(False)
        o.hide_render = False
        o.hide_viewport = False
    bpy.context.view_layer.update()
    return list(bpy.data.objects)


def add_dirt_uv(meshes):
    """DirtUV (druhá UV vrstva pro vmaskUV2): jedno rozbalení všech meshů dílu, jako build_dirt_uvs ve vozidlech."""
    for o in meshes:
        me = o.data
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        while len(me.uv_layers) > 1:
            me.uv_layers.remove(me.uv_layers[1])
        me.uv_layers.new(name="DirtUV")
        me.uv_layers.active_index = 1
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004, area_weight=0.0, correct_aspect=True,
                             scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in meshes:
        o.data.uv_layers.active_index = 0
        o.select_set(False)


def export_i3d(root, path, X):
    s = bpy.context.scene.I3D_UIexportSettings
    s.i3D_exportUseSoftwareFileName = False
    s.i3D_exportFileLocation = path
    s.i3D_gameLocationDisplay = X.GAME_DIR
    s.i3D_binaryFiles = True
    s.i3D_exportAxisOrientations = "BAKE_TRANSFORMS"
    s.i3D_exportRelativePaths = True
    s.i3D_exportLights = False
    s.i3D_exportCameras = False
    s.i3D_exportAnimation = False
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    tree = [root] + list(root.children_recursive)
    for o in tree:
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
    log = io.StringIO()
    try:
        with contextlib.redirect_stdout(log), override:
            exp.I3DExportSelected()
    finally:
        sel.get_outliner_selected_nodes = outliner_nodes
    for f in (path, path + ".shapes"):
        if not os.path.exists(f):
            raise RuntimeError(f"export nevytvořil {f}\n{log.getvalue()[-2000:]}")
    return len(tree)


def main():
    import export_middle_mod as X
    want = set(a for a in sys.argv[sys.argv.index("--") + 1:] if a) if "--" in sys.argv else set()
    X.VMASK = {"trailer": "$data/shared/default_vmask.png", "drone": "$data/shared/default_vmask.png"}
    os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
    shutil.copy(DECAL_SRC, os.path.join(OUT, "textures", "sdt_decals.dds"))
    with open(DATA, encoding="utf-8") as fh:
        items = json.load(fh)["items"]
    manifest = []
    for item in items:
        if want and item["id"] not in want:
            continue
        for v in item["variants"]:
            name = part_name(item["id"], v["slug"])
            blend = os.path.join(HERE, "parts", v["file"])
            objs = load_variant(blend, v["visibleNames"])
            meshes = [o for o in objs if o.type == "MESH"]
            add_dirt_uv(meshes)
            root = bpy.data.objects.new(name, None)
            bpy.context.scene.collection.objects.link(root)
            for o in objs:
                if o.parent is None:
                    o.parent = root
                    o.matrix_parent_inverse = Matrix.Identity(4)
            bpy.context.view_layer.update()
            path = os.path.join(OUT, name + ".i3d")
            n = export_i3d(root, path, X)
            used = X.apply_vehicle_shader(path)
            lo, hi = v["bbox"]
            b2i = lambda p: [p[0], p[2], -p[1]]
            a, b = b2i(lo), b2i(hi)
            box = [[min(a[i], b[i]) for i in range(3)], [max(a[i], b[i]) for i in range(3)]]
            info = {"id": item["id"], "variant": v["slug"], "name": name, "i3d": path.replace("\\", "/"), "bbox": box,
                    "title": item["title"], "label": v["label"], "nodes": n, "pts": v["pts"]}
            with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as fh:
                json.dump(info, fh, ensure_ascii=False)
            manifest.append(info)
            print(f"EXPORT {name}: {n} uzlů, materiály {len(used)}", flush=True)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    print("EXPORT HOTOVO", len(manifest))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
