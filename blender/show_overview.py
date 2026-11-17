"""Přehledová scéna všech tří vleků (rozložený + složený vedle sebe) pro vizuální kontrolu - Pavel 2026-10-07.

Staví každý vlek dvakrát (build_trailer_X.build()): jednou necháno v základní (rozložené) poloze, podruhé
přes _store_pose z export_X_mod.py přepnuto do složené/cestovní pózy (žebřík zasunutý, dron složený, víka
zavřená). Mezi oběma voláními se nová dávka objektů hned přesune do vlastní kolekce a přejmenuje (P.begin()
jinak při druhém volání smaže celou sdílenou kolekci vleku). Jen geometrie a náhledové materiály, bez pečení
textur/exportu - pro rychlý vizuální přehled v Blenderu, ne pro export do hry.

Bez okna: blender.exe -b --python blender\\show_overview.py
"""

import os

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "prehled_vsechny.blend")

VEHICLES = [
    ("Mini", "export_mini_mod.py"),
    ("Middle", "export_middle_mod.py"),
    ("Max", "export_max_mod.py"),
]
ROW_GAP = 3.0
PAIR_GAP = 6.0


def run(name, ns_name):
    p = os.path.join(HERE, name)
    ns = {"__file__": p, "__name__": ns_name}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    return ns


def snapshot():
    return {o.name for o in bpy.data.objects}


def rename_new(before, suffix):
    new_objs = [o for o in bpy.data.objects if o.name not in before]
    for o in new_objs:
        base = o.name.rsplit(".", 1)[0] if o.name[-4:-3] == "." and o.name[-3:].isdigit() else o.name
        o.name = base + suffix
    return new_objs


def transform_new(objs, matrix, before):
    """Posune jen kořeny nové dávky (rodič mimo dávku, tj. jméno je v `before`); děti jedou s nimi přes parenting."""
    for o in objs:
        if o.parent is None or o.parent.name in before:
            o.matrix_world = matrix @ o.matrix_world
    bpy.context.view_layer.update()


def move_to_collection(objs, coll_name):
    coll = bpy.data.collections.new(coll_name)
    bpy.context.scene.collection.children.link(coll)
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    return coll


def bbox_width_y(objs):
    mn, mx = 1e9, -1e9
    for o in objs:
        if o.type == "MESH":
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mn, mx = min(mn, w.y), max(mx, w.y)
    return (mx - mn) if mx > mn else 4.0


def build_instance(build_file, suffix, pose_fn=None):
    """build_trailer_X.build() s NEMERGED DRONE_VARIANTS (Max má v exportním load_car_module() navíc S2/M2/L2,
    které build_drones() nezná - merge smí přijít až PO postavení geometrie, jinak selže na D.SPECS['S2'])."""
    before = snapshot()
    build_ns = run(build_file, "buildmod_" + suffix)
    build_ns["build"]()
    if pose_fn is not None:
        pose_fn()
    objs = rename_new(before, suffix)
    return objs, before


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    x_cursor = 0.0
    for key, export_file in VEHICLES:
        build_file = f"build_trailer_{key.lower()}.py"

        open_objs, open_before = build_instance(build_file, "_" + key + "_open")
        w = bbox_width_y(open_objs)
        transform_new(open_objs, Matrix.Translation((x_cursor, 0, 0)), open_before)
        move_to_collection(open_objs, key + "_rozlozeny")
        x_cursor += w + ROW_GAP

        def fold():
            export_ns = run(export_file, "expmod_" + key)
            export_ns["_store_pose"](export_ns["load_car_module"]())

        folded_objs, folded_before = build_instance(build_file, "_" + key + "_folded", fold)
        w2 = bbox_width_y(folded_objs)
        transform_new(folded_objs, Matrix.Translation((x_cursor, 0, 0)), folded_before)
        move_to_collection(folded_objs, key + "_slozeny")
        x_cursor += w2 + PAIR_GAP

        print(f"{key}: rozložený šířka {w:.2f} m, složený šířka {w2:.2f} m")

    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("uloženo:", OUT)


try:
    main()
except Exception:
    import sys
    import traceback
    traceback.print_exc()
    sys.exit(1)
