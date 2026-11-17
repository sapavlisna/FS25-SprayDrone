"""Sestaví přehledovou scénu ze 6 už hotových .blend souborů (3 vleky x rozložený/složený) - Pavel 2026-10-07.

Na rozdíl od show_overview.py (archivováno, mělo problém s referenčními pozicemi dronů při opakovaném build()
ve stejném procesu) jen APPENDuje celé kolekce z už existujících, správně postavených .blend souborů - každý
vznikl v samostatném procesu, takže žádné sdílené globální stavy mezi vleky.

Bez okna: blender.exe -b --python blender\\assemble_overview.py
"""

import os

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "prehled_vsechny.blend")

# (popisek, soubor, název kolekce vleku v tom souboru)
PARTS = [
    ("Mini_rozlozeny", "spraydrone_trailer_mini.blend", "SprayDroneTrailerMini"),
    ("Mini_slozeny", "spraydrone_trailer_mini_folded.blend", "SprayDroneTrailerMini"),
    ("Car_rozlozeny", "spraydrone_trailer_middle.blend", "SprayDroneTrailerMiddle"),
    ("Car_slozeny", "spraydrone_trailer_middle_folded.blend", "SprayDroneTrailerMiddle"),
    ("Max_rozlozeny", "spraydrone_trailer_max.blend", "SprayDroneTrailerMax"),
    ("Max_slozeny", "spraydrone_trailer_max_folded.blend", "SprayDroneTrailerMax"),
]
ROW_GAP = 3.0
PAIR_GAP = 6.0


def append_collection(path, coll_name, new_name):
    with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
        if coll_name not in data_from.collections:
            raise RuntimeError(f"{path}: kolekce {coll_name} nenalezena (má {data_from.collections})")
        data_to.collections = [coll_name]
    coll = bpy.data.collections[coll_name]
    coll.name = new_name
    bpy.context.scene.collection.children.link(coll)
    return coll


def bbox_width_y(coll):
    mn, mx = 1e9, -1e9
    for o in coll.all_objects:
        if o is not None and o.type == "MESH" and not o.get("i3D_nonRenderable"):
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mn, mx = min(mn, w.y), max(mx, w.y)
    return (mx - mn) if mx > mn else 4.0


def move_collection(coll, matrix):
    names = {ob.name for ob in coll.all_objects if ob is not None}
    roots = [o for o in coll.all_objects if o is not None and (o.parent is None or o.parent.name not in names)]
    for o in roots:
        o.matrix_world = matrix @ o.matrix_world
    bpy.context.view_layer.update()


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    x_cursor = 0.0
    prev_key = None
    for i, (label, fname, coll_name) in enumerate(PARTS):
        key = label.split("_")[0]
        coll = append_collection(os.path.join(HERE, fname), coll_name, label)
        w = bbox_width_y(coll)
        move_collection(coll, Matrix.Translation((x_cursor, 0, 0)))
        gap = PAIR_GAP if (prev_key is not None and prev_key != key and label.endswith("_rozlozeny")) else ROW_GAP
        x_cursor += w + gap
        prev_key = key
        # jen první kolekce (Mini_rozlozeny) viditelná ve výchozím stavu - ať se při otevření nesléze víc vleků
        # najednou do jednoho záběru (Pavel 2026-10-09: tohle matlo dřív). Zapínej/vypínej v Outlineru checkboxem.
        coll.hide_render = i != 0
        coll.hide_viewport = i != 0
        print(f"{label}: šířka {w:.2f} m, x_cursor nyní {x_cursor:.2f}, viditelná: {i == 0}")
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print("uloženo:", OUT)


try:
    main()
except Exception:
    import sys
    import traceback
    traceback.print_exc()
    sys.exit(1)
