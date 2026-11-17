"""Uloží složenou/cestovní variantu existujícího vleku do nového .blend (Pavel 2026-10-07, přehledová scéna).

Neopakuje build() (to dřív v jednom procesu pro víc vleků/instancí dělalo potíže s referenčními pozicemi dronů) -
jen otevře už hotový uložený .blend vleku a na místě přepne pózu přes _store_pose z export_X_mod.py, pak uloží
jako samostatný soubor (open .blend zůstává nedotčené).

blender.exe -b --python blender\\make_folded_variant.py -- mini|middle|max
"""

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))

VEHICLES = {
    "mini": ("spraydrone_trailer_mini.blend", "export_mini_mod.py", "spraydrone_trailer_mini_folded.blend"),
    "middle": ("spraydrone_trailer_middle.blend", "export_middle_mod.py", "spraydrone_trailer_middle_folded.blend"),
    "max": ("spraydrone_trailer_max.blend", "export_max_mod.py", "spraydrone_trailer_max_folded.blend"),
}


def run(name, ns_name):
    p = os.path.join(HERE, name)
    ns = {"__file__": p, "__name__": ns_name}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    return ns


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    key = args[0]
    src, export_file, dst = VEHICLES[key]
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, src))
    export_ns = run(export_file, "expmod")
    car = export_ns["load_car_module"]()
    export_ns["_store_pose"](car)
    out = os.path.join(HERE, dst)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("uloženo:", out)


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
