"""Přestavba malého vleku bez okna Blenderu.

    blender.exe -b --python blender\\headless_max.py [-- build|render|stavba|export]

build: prázdná scéna -> build_trailer_max.build() -> blender\\spraydrone_trailer_max.blend;
render: Workbench náhledy z několika stran do tmp\\max (soubor se otevře z disku);
stavba: náhledy plachet, žebříku, skříňky a displeje v různých stavech animace do tmp\\stavba_max;
export: export_max_mod.build_mod().
"""

import math
import os
import sys

import addon_utils
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
BLEND = os.path.join(HERE, "spraydrone_trailer_max.blend")
SHOTS = os.path.join(PROJECT, "tmp", "max")
SHOTS_BUILD = os.path.join(PROJECT, "tmp", "stavba_max")


def run(name):
    p = os.path.join(HERE, name)
    ns = {"__file__": p, "__name__": "headless"}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    return ns


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    run("build_trailer_max.py")["build"]()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("uloženo:", BLEND)


def _scene():
    if bpy.data.filepath != BLEND:
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 1500, 900
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("w")
    world.color = (0.30, 0.31, 0.33)
    sc.world = world
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 32
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    hide = [o for o in bpy.data.objects if o.get("i3D_nonRenderable")]
    for o in hide:
        o.hide_render = True
    for c in list(bpy.data.collections):
        if c.name.endswith("_Preview"):
            for o in c.objects:
                o.hide_render = False
    return sc, cam


def _shoot(sc, cam, path, target, az, el, dist):
    a, e = math.radians(az), math.radians(el)
    target = Vector(target)
    pos = target + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    cam.location = pos
    cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("render:", path)


def render_views(views):
    sc, cam = _scene()
    os.makedirs(SHOTS, exist_ok=True)
    coll = bpy.data.collections["SprayDroneTrailerMax"]
    objs = [o for o in coll.all_objects if o.type == "MESH" and not o.get("i3D_nonRenderable")]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    ctr = sum(pts, Vector()) / len(pts)
    for name, az, el, dist, tz in views:
        _shoot(sc, cam, os.path.join(SHOTS, f"{name}.png"), (ctr.x, ctr.y, tz), az, el, dist)


# stav: (plachty 0 = srolováno .. 1 = zavřeno, žebřík 0 = rozložený .. 1 = složený)
BUILD_VIEWS = [
    ("1_zavreno_predleva", (1, 1), (0, 2.2, 1.6), 35, 18, 13.0),
    ("2_zavreno_predprava", (1, 1), (0, 2.2, 1.6), -35, 18, 13.0),
    ("3_srolovano_leva", (0, 0), (0, 2.2, 1.5), 72, 12, 12.0),
    ("4_srolovano_prava_zebrik", (0, 0), (-0.5, 2.0, 1.5), -68, 12, 11.0),
    ("5_zezadu", (1, 1), (0, 4.5, 1.6), 160, 14, 10.0),
    ("6_detail_skrinka", (0, 0), (0.9, 1.6, 1.75), 68, 8, 3.4),
    ("7_detail_displej", (0, 0), (0.93, -0.7, 1.5), 62, 10, 2.2),
    ("8_detail_zebrik_nahore", (0, 0), (-1.2, 1.75, 2.6), -55, 22, 2.6),
    ("9_zebrik_slozeny", (0, 1), (-0.9, 1.9, 1.3), -70, 15, 4.0),
    ("a_zebrik_t040", (0, 0.4), (-1.3, 1.9, 1.4), -60, 15, 5.5),
    ("b_zebrik_t075", (0, 0.75), (-1.3, 1.9, 1.4), -60, 15, 5.5),
    ("c_zebrik_t088", (0, 0.88), (-1.3, 1.9, 1.4), -60, 15, 5.5),
    ("d_zavreno_prava_bok", (1, 1), (0, 2.2, 1.5), -90, 4, 12.5),
    ("e_zavreno_leva_bok", (1, 1), (0, 2.2, 1.5), 90, 4, 12.5),
    ("f_detail_predek_srolovano", (0, 0), (0.3, -1.6, 2.0), 25, 25, 4.5),
    ("g_zezadu_srolovano", (0, 0), (0, 5.5, 1.6), 150, 14, 9.0),
]


def render_build(views=BUILD_VIEWS):
    sc, cam = _scene()
    sc.display.shading.color_type = "TEXTURE"       # polepy designu z atlasu (jinak bílé obdélníky)
    os.makedirs(SHOTS_BUILD, exist_ok=True)
    car = run("build_trailer_max.py")
    try:
        for name, (tarp, ladder), target, az, el, dist in views:
            car["set_tarps"](tarp)
            car["set_ladder"](ladder)
            _shoot(sc, cam, os.path.join(SHOTS_BUILD, f"{name}.png"), target, az, el, dist)
    finally:
        car["set_tarps"](1.0)
        car["set_ladder"](0.0)


VIEWS = [
    ("x_left_front", 40, 22, 12.0, 1.3),
    ("x_right_rear", 215, 22, 12.0, 1.3),
    ("x_top", 0, 85, 12.0, 1.3),
    ("x_left", 90, 8, 13.0, 1.3),
    ("x_rear", 180, 12, 10.0, 1.3),
    ("x_right", 270, 6, 13.0, 1.3),
    ("x_center", 235, 30, 6.0, 2.4),
    ("x_under", 20, -50, 11.0, 0.8),
]


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    steps = args or ["build", "render"]
    if "build" in steps:
        build()
    if "render" in steps:
        render_views(VIEWS)
    if "stavba" in steps:
        render_build()
    if "export" in steps:
        if "io_export_i3d_reworked" not in bpy.context.preferences.addons:
            addon_utils.enable("io_export_i3d_reworked", default_set=False)
        if bpy.data.filepath != BLEND:
            bpy.ops.wm.open_mainfile(filepath=BLEND)
        run("export_max_mod.py")["build_mod"]()


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
