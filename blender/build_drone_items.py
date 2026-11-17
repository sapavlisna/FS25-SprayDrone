"""Drony jako samostatné předměty (docs/NAVRH-dron-predmet.md, etapa 1): složený dron S / M / L / K (ramena podél trupu, listy složené) jako
objekt objects/drone/drone<V>.i3d (pallet, jde nést v rukou a usadit na plošinu vleku). Dron je slitý do jednoho meshe drone<V>_vis, počátek
je na zemi pod středem trupu (lyžiny na z = 0), kolize floorCollision01 je kvádr kolem složeného dronu.
Samostatný skript nad prázdnou scénou (jako build_pump.py):

    blender.exe -b --python blender\\build_drone_items.py

Pravidla objektu (XML) jsou ručně, skript do nich přepíše jen blok <i3dMappings> a rozměr <size> podle složeného dronu.
"""

import math
import os
import re
import sys

import addon_utils
import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parts_lib as PL  # noqa: E402
import build_canister as C  # noqa: E402
import build_drone as D  # noqa: E402
import build_link_items as L  # noqa: E402
import export_middle_mod as X  # noqa: E402
import sdt_parts as P  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects", "drone")
WORK = os.path.join(PROJECT, "out", "drone_items")
BLEND = os.path.join(HERE, "spraydrone_drone_items.blend")
VARIANTS = ("S", "M", "L", "K")


def build(variant):
    name = f"drone{variant}"
    root, cols = L._reset(name)
    coll = bpy.context.scene.collection
    D.build_drone(coll, name="Drone", origin=(0, 0, 0), folded=True, arms_folded=1.0, spec=D.SPECS[variant])
    bpy.context.view_layer.update()
    meshes = [o for o in coll.objects if o.type == "MESH" and o is not root and o.parent is not root and not o.name.startswith("collisions")
              and o.name.startswith("Drone_")]
    body = PL.join_meshes(f"{name}_vis", meshes)
    for o in list(coll.objects):      # patky, kloubové uzly ramen a trysky (prázdné objekty) do předmětu nepatří
        if o.type == "EMPTY" and o is not root and o is not cols:
            bpy.data.objects.remove(o, do_unlink=True)
    me = body.data
    xs, ys, zs = ([v.co[i] for v in me.vertices] for i in range(3))
    me.transform(Matrix.Translation((0, 0, -min(zs))))      # počátek zůstává pod středem trupu, ramena a listy ční dozadu
    me.update()
    size = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    C.props(body, clipDistance=100.0)
    C.box_object("floorCollision01", cols, min(xs), max(xs), min(ys), max(ys), 0.0, size[2], C.GROUP_FLOOR, C.MASK_FLOOR,
                 compoundChild=True, staticFriction=1.0, dynamicFriction=1.0, density=0.0)
    bpy.context.view_layer.update()
    return root, name, size


def ceil05(value):
    return math.ceil(value / 0.05 - 1e-6) * 0.05


def patch_size(xml_path, size):
    text = open(xml_path, encoding="utf-8").read()
    new = '<size width="%.2f" length="%.2f" height="%.2f"/>' % tuple(ceil05(s) for s in size)
    text, n = re.subn(r'<size width="[^"]*" length="[^"]*" height="[^"]*"/>', new, text, count=1)
    assert n == 1, xml_path
    open(xml_path, "w", encoding="utf-8", newline="").write(text)


def export(root, name, size):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.i3d")
    C.export_i3d(root, path)
    L.shader_materials(path)
    C.zero_density(path)
    names = [root.name, f"{name}_vis", "floorCollision01"]
    mappings, found = X.i3d_mappings(path, names)
    xml_path = os.path.join(OUT_DIR, f"{name}.xml")
    C.write_mappings(xml_path, found, names)
    patch_size(xml_path, size)
    C.store_image(root, os.path.join(OUT_DIR, f"store_{name}.dds"), os.path.join(WORK, f"store_{name}.png"))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_export_i3d_reworked", default_set=False)
    for variant in VARIANTS:
        root, name, size = build(variant)
        print("DRON %s: %.3f x %.3f x %.3f m" % ((variant,) + tuple(size)))
        export(root, name, size)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
