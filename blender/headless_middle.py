"""Přestavba středního vleku a export módu bez okna Blenderu.

    blender.exe -b --python blender\\headless_middle.py [-- build|export|render [filtr]]

Bez argumentu: prázdná scéna → build_trailer_middle.build() → uložit spraydrone_trailer_middle.blend → export_middle_mod.build_mod()
(export jen s předchozím "build" ve stejném běhu, nebo s otevřeným .blend). "build" přestaví a uloží. Obrázek do obchodu a ikona se bez okna nekreslí (zůstávají stávající DDS).
"render" (bez "build" otevře uložený .blend) nakreslí kontrolní pohledy do tmp/stavba_middle (Workbench, .blend se neukládá);
s dalším argumentem jen pohledy, jejichž jméno ho obsahuje.
"""

import addon_utils
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(HERE, "spraydrone_trailer_middle.blend")
SHOTS = os.path.join(os.path.dirname(HERE), "tmp", "stavba_middle")

# stav: (plachty, žebřík, dřív dvířka skříňky relé - už nejsou, víko nabíječky otevřené); 0 = rozloženo, 1 = složeno
STATES = {"zavreno": (1, 1, 1, False), "role": (0, 0, 0, True), "role_slozeny": (0, 1, 1, True)}
# jméno, stav, azimut (0 = zepředu, 90 = zleva), elevace, vzdálenost, cíl
VIEWS = [
    ("01_zavreno_predni_levy", "zavreno", 40, 14, 9.0, (0.0, -0.4, 1.4)),
    ("02_zavreno_predni_pravy", "zavreno", -40, 14, 9.0, (0.0, -0.4, 1.4)),
    ("03_role_pravy_zebrik", "role", -65, 10, 7.5, (-0.2, -1.0, 1.3)),
    ("04_detail_predek_centrala", "role", 25, 10, 4.6, (0.2, -2.1, 1.4)),
    ("05_detail_skrinka", "role", 65, 10, 2.6, (0.9, -0.61, 1.5)),
    ("06_zezadu_vrata", "zavreno", 180, 8, 6.0, (0.0, 2.2, 1.4)),
    ("07_zezadu_vrata_sikmo", "zavreno", 150, 12, 7.0, (0.0, 1.5, 1.4)),
    ("08_detail_zebrik_slozeny", "role_slozeny", -60, 8, 3.2, (-1.1, -2.2, 1.4)),
    ("09_detail_hadice", "role", -45, 35, 2.2, (-0.9, -1.5, 2.3)),
    ("10_detail_displej", "role", 70, 5, 2.0, (1.0, -2.3, 1.5)),
    ("11_detail_predek_zavreno", "zavreno", 15, 8, 5.2, (0.0, -2.5, 1.4)),
    ("12_zebrik_vysunuty_bok", "role", -95, 4, 4.5, (-1.3, -2.3, 1.2)),
    ("13_zebrik_nahore", "role", -70, 22, 2.2, (-1.1, -2.3, 2.3)),
    ("14_role_levy", "role", 70, 10, 7.5, (0.2, -0.4, 1.3)),
]
HIDE_PREFIX = ("Tank_Main800", "Tank_Main1000", "Tank_Main1500", "Tank_Main3000", "antennaBoosted", "antennaLarge",
               "Drone_S_", "Drone_L_")


def run(name):
    p = os.path.join(HERE, name)
    ns = {"__file__": p, "__name__": "headless"}
    exec(open(p, encoding="utf-8").read(), ns)
    return ns


def render(only=None):
    car = run("build_trailer_middle.py")
    P = car["P"]
    os.makedirs(SHOTS, exist_ok=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"            # polepy značky mají průhlednost z atlasu, Workbench ji nekreslí
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.eevee.taa_render_samples = 16
    sc.render.resolution_x, sc.render.resolution_y = 1280, 800
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("_stavba_w")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.55, 0.57, 0.60, 1.0)
    bg.inputs[1].default_value = 1.0
    sc.world = world
    for name, energy, rot in (("_stavba_key", 3.0, (0.75, 0.15, -0.55)), ("_stavba_fill", 1.2, (1.1, -0.2, 2.4))):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        sc.collection.objects.link(lo)
    cam_data = bpy.data.cameras.new("_stavba_cam")
    cam = bpy.data.objects.new("_stavba_cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    for o in bpy.data.objects:
        hidden = o.hide_render
        if o.get("i3D_nonRenderable") or (o.type == "MESH" and (o.name.startswith(HIDE_PREFIX) or
                                                                  (o.name.startswith("battery") and o.name[-1] in "SL"))):
            hidden = True
        if any(c.name.endswith("_Preview") for c in o.users_collection):
            hidden = False
        o.hide_render = hidden
    tarps = [(bpy.data.objects[n], bpy.data.objects[n + "Roll"]) for n in ("tarpSideL", "tarpSideR", "tarpFront")]
    lid = bpy.data.objects["chargerLid"]
    lid_open = lid.rotation_euler.x
    for name, state, az, el, dist, target in VIEWS:
        if only and only not in name:
            continue
        t_tarp, t_lad, t_door, lid_up = STATES[state]
        for pivot, roll in tarps:
            P.tarp_preview(pivot, roll, t_tarp)
        car["set_ladder"](t_lad)
        lid.rotation_euler.x = lid_open if lid_up else 0.0
        bpy.context.view_layer.update()
        a, e = math.radians(az), math.radians(el)
        tgt = Vector(target)
        pos = tgt + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
        cam.location = pos
        cam.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
        cam_data.lens = 32 if dist > 4 else 40
        sc.render.filepath = os.path.join(SHOTS, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("render:", sc.render.filepath)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    steps = args or ["build", "export"]
    if "build" in steps:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        run("build_trailer_middle.py")["build"]()
        bpy.ops.wm.save_as_mainfile(filepath=BLEND)
        print("uloženo:", bpy.data.filepath)
    if "export" in steps:
        if "io_export_i3d_reworked" not in bpy.context.preferences.addons:
            addon_utils.enable("io_export_i3d_reworked", default_set=False)
        run("export_middle_mod.py")["build_mod"]()
    if "render" in steps:
        if "build" not in steps and bpy.data.filepath != BLEND:
            bpy.ops.wm.open_mainfile(filepath=BLEND)
        i = steps.index("render")
        render(steps[i + 1] if i + 1 < len(steps) else None)


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
