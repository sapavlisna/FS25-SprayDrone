"""Přestavba malého vleku bez okna Blenderu.

    blender.exe -b --python blender\\headless_mini.py [-- build|render|polep [DESIGN ...] [čísla náhledů]|export]

build: prázdná scéna -> build_trailer_mini.build() -> blender\\spraydrone_trailer_mini.blend;
render: Workbench náhledy z několika stran do tmp\\mini (soubor se otevře z disku);
polep: EEVEE náhledy polepů značky (složeno i rozloženo) do tmp\\stavba_mini\\<DESIGN>, např. -- polep BZUK ROSA 01 08;
export: export_mini_mod.build_mod().
"""

import math
import os
import sys

import addon_utils
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PROJECT = os.path.dirname(HERE)
BLEND = os.path.join(HERE, "spraydrone_trailer_mini.blend")
SHOTS = os.path.join(PROJECT, "tmp", "mini", "v2")


def run(name):
    p = os.path.join(HERE, name)
    ns = {"__file__": p, "__name__": "headless"}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    return ns


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    run("build_trailer_mini.py")["build"]()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("uloženo:", BLEND)


def render_views(views):
    if bpy.data.filepath != BLEND:
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(SHOTS, exist_ok=True)
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
    coll = bpy.data.collections["SprayDroneTrailerMini"]
    hide = [o for o in bpy.data.objects if o.get("i3D_nonRenderable")]
    for o in hide:
        o.hide_render = True
    for o in bpy.data.objects:
        if o.parent is not None and o.parent.name.startswith("padLeg") and o.parent.name[6:].isdigit():
            o.hide_render = True
    for c in list(bpy.data.collections):
        if c.name.endswith("_Preview"):
            for o in c.objects:
                o.hide_render = False
    objs = [o for o in coll.all_objects if o.type == "MESH" and not o.get("i3D_nonRenderable") and not o.hide_render]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    ctr = sum(pts, Vector()) / len(pts)
    for name, az, el, dist, tz in views:
        a, e = math.radians(az), math.radians(el)
        target = Vector((ctr.x, ctr.y, tz))
        pos = target + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
        cam.location = pos
        cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(SHOTS, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("render:", sc.render.filepath)


VIEWS = [
    ("m_left_front", 40, 22, 7.0, 1.0),
    ("m_right_rear", 215, 22, 7.0, 1.0),
    ("m_top", 0, 85, 7.5, 1.0),
    ("m_left", 90, 8, 8.0, 1.0),
    ("m_rear", 180, 12, 7.0, 1.0),
    ("m_rear_low", 150, 6, 5.0, 0.45),
    ("m_right_low", 270, 4, 7.0, 0.45),
    ("m_under", 20, -50, 7.0, 0.4),
]


BRAND_SHOTS = os.path.join(PROJECT, "tmp", "stavba_mini")
# (jméno, rozloženo, azimut, elevace, vzdálenost, cíl x, y, z, ohnisko); azimut 0 = pohled zepředu (od oje), 90 = zleva
BRAND_VIEWS = [
    ("01_slozeno_predni_levy", False, 40, 24, 8.0, 0.0, -0.3, 0.9, 40),
    ("02_slozeno_zadni_pravy", False, 220, 24, 7.5, 0.0, 0.3, 0.9, 40),
    ("03_slozeno_bok_levy", False, 90, 6, 8.5, 0.0, -0.6, 0.9, 40),
    ("04_detail_bedna_zadni_levy", False, 145, 20, 4.2, 0.0, 0.73, 1.15, 40),
    ("05_detail_bedna_celo_vrch", False, 10, 45, 4.0, 0.0, 0.6, 1.3, 40),
    ("06_detail_bedna_bok_pravy", False, 270, 8, 3.6, -0.9, 0.73, 1.15, 40),
    ("07_detail_bedny_kanystry", False, 300, 14, 3.2, -0.3, -0.9, 0.9, 40),
    ("08_rozlozeno_sikmo", True, 60, 38, 9.0, 0.0, 1.9, 0.4, 35),
    ("09_rozlozeno_bok_levy_vnitrek", True, 110, 50, 4.5, 1.4, 0.8, 0.3, 35),
    ("10_rozlozeno_plosina", True, 165, 55, 5.5, 0.0, 3.4, 0.6, 35),
    ("11_celo_P_zprimo", False, 0, 12, 3.0, 0.0, 0.0, 1.2, 40),
    ("12_bok_L_zprimo", False, 90, 3, 3.5, 0.9, 0.73, 1.15, 40),
]


def _unfold_crate():
    """Rozložená bedna jako v SprayDronePad (zjednodušeně, jen pro náhled): panely do roviny, boční stěny vyklopené o SIDE_FALL_DEG,
    nožičky k zemi, dron otočený do letové polohy uprostřed plošiny."""
    ob = bpy.data.objects
    for n in ("padHingeZ", "padHingeH", "padHingeP"):
        ob[n].rotation_euler.x = 0.0
    ob["padSideL"].rotation_euler.y = math.radians(150)
    ob["padSideR"].rotation_euler.y = math.radians(-150)
    bpy.context.view_layer.update()
    for k in range(1, 7):
        rod, foot = ob[f"padLegRod{k}"], ob[f"padLegFoot{k}"]
        ext = rod.matrix_world.translation.z - 0.025
        rod.scale.z *= ext / 0.02
        mw = foot.matrix_world.copy()
        mw.translation.z -= ext - 0.02
        foot.matrix_world = mw
        for o in [rod, foot] + list(rod.parent.children if rod.parent else []):
            o.hide_render = False
    car = ob["droneCarrier"]
    car.matrix_world = Matrix.Rotation(-math.pi / 2, 4, "Z") @ car.matrix_world
    bpy.context.view_layer.update()
    target_y = (ob["padHingeH"].matrix_world.translation.y + ob["padHingeP"].matrix_world.translation.y) / 2
    mw = car.matrix_world.copy()
    mw.translation += Vector((-mw.translation.x, target_y - mw.translation.y, 0.012))
    car.matrix_world = mw
    bpy.context.view_layer.update()


def render_brand(design="BZUK", views=None):
    """Náhledy polepů značky (EEVEE, ať je vidět atlas s alfou) do tmp/stavba_mini; design = který z brand_<KEY>_* ukázat.
    Soubor se neukládá, výchozí design v .blend zůstává BZUK."""
    import brand_layout as BL
    if bpy.data.filepath != BLEND:
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    os.makedirs(BRAND_SHOTS, exist_ok=True)
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.render.resolution_x, sc.render.resolution_y = 1400, 900
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.color = (0.30, 0.31, 0.33)
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.44, 0.47, 1.0)
    bg.inputs[1].default_value = 0.9
    sc.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), math.radians(15), math.radians(30))
    sc.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    for o in bpy.data.objects:
        if o.get("i3D_nonRenderable") or (o.type == "LIGHT" and o is not sun):      # světla dronu (LED) by náhled barvila
            o.hide_render = True
        if o.parent is not None and o.parent.name.startswith("padLeg") and o.parent.name[6:].isdigit():
            o.hide_render = True
    for c in list(bpy.data.collections):
        if c.name.endswith("_Preview"):
            for o in c.objects:
                o.hide_render = False

    def show(o, on):
        o.hide_render = not on
        for ch in o.children:
            show(ch, on)

    for o in bpy.data.objects:
        key = BL.brand_node_design(o.name)
        if key:
            show(o, key == design)
    unfolded = False
    for name, unf, az, el, dist, tx, ty, tz, lens in views or BRAND_VIEWS:
        if unf and not unfolded:
            _unfold_crate()
            unfolded = True
        cam_data.lens = lens
        a, e = math.radians(az), math.radians(el)
        target = Vector((tx, ty, tz))
        pos = target + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
        cam.location = pos
        cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(BRAND_SHOTS, design, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("render:", sc.render.filepath)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    steps = args or ["build", "render"]
    if "build" in steps:
        build()
    if "render" in steps:
        render_views(VIEWS)
    if "polep" in steps:
        designs = [a for a in args if a.isupper() and a not in ("BUILD",)] or ["BZUK"]
        only = [a for a in args if a.startswith("0") or a.startswith("1")]
        for d in designs:
            if bpy.data.filepath == BLEND:
                bpy.ops.wm.open_mainfile(filepath=BLEND)
            render_brand(d, [v for v in BRAND_VIEWS if not only or v[0][:2] in only])
    if "export" in steps:
        if "io_export_i3d_reworked" not in bpy.context.preferences.addons:
            addon_utils.enable("io_export_i3d_reworked", default_set=False)
        if bpy.data.filepath != BLEND:
            bpy.ops.wm.open_mainfile(filepath=BLEND)
        run("export_mini_mod.py")["build_mod"]()


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
