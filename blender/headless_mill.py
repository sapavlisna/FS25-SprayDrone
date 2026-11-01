"""Mlýnkový vozík na vápno a vápenná varianta Maxu bez okna Blenderu (zatím jen modely k odsouhlasení, nic se neexportuje do modu).

    blender.exe -b --python blender\\headless_mill.py [-- build|render|compose]

build:   prázdná scéna -> build_trailer_mill.build() -> blender\\spraydrone_mill.blend
render:  náhledy vozíku z několika stran do tmp\\vapneni\\modely\\vozik
export:  export_mill_mod.build_mod() (i3d, XML, obrázek do obchodu)
compose: otevře blender\\spraydrone_trailer_max.blend (soubor se neukládá), schová indukční nádobku, postaví vápennou nádobku,
         postaví vozík vedle Maxu, natáhne mezi spojkami hadici a vyrenderuje náhledy do tmp\\vapneni\\modely\\max
"""

import math
import os
import sys

import addon_utils
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PROJECT = os.path.dirname(HERE)
BLEND = os.path.join(HERE, "spraydrone_mill.blend")
MAX_BLEND = os.path.join(HERE, "spraydrone_trailer_max.blend")
OUT = os.path.join(PROJECT, "tmp", "vapneni", "modely")

# vozík je zapřažený za kulovým věšákem na zádi Maxu (sdt_lime.build_rear_hitch)

CART_VIEWS = [
    # jméno, azimut, elevace, vzdálenost, cíl x, y, z, ohnisko
    ("01_predni_pravy", 320, 22, 6.4, 0.0, 0.3, 1.15, 32),
    ("02_predni_levy", 40, 22, 6.4, 0.0, 0.3, 1.15, 32),
    ("03_zadni_pravy", 215, 22, 6.4, 0.0, 0.5, 1.15, 32),
    ("04_bok_pravy", 270, 6, 7.4, 0.0, 0.3, 1.15, 32),
    ("05_zepredu", 0, 10, 6.0, 0.0, 0.0, 1.15, 32),
    ("06_zezadu", 180, 10, 6.0, 0.0, 0.0, 1.15, 32),
    ("07_shora", 0, 86, 6.8, 0.0, 0.3, 1.0, 32),
    ("08_detail_nadobka_a_spojka", 300, 16, 3.4, -0.5, -0.15, 1.1, 38),
    ("09_detail_mlyn_a_motor", 20, 20, 3.6, 0.2, -0.2, 1.0, 38),
    ("10_detail_spojka_hadice", 270, 8, 2.0, -1.0, -0.15, 0.75, 38),
    ("11_detail_civka_hadice_zezadu", 195, 14, 3.0, 0.0, 1.95, 0.95, 38),
    ("12_detail_civka_hadice_zprava", 262, 10, 3.0, 0.0, 1.9, 0.95, 38),
    ("13_detail_civka_hadice_zleva", 105, 10, 3.0, 0.0, 1.9, 0.95, 38),
    ("14_detail_nadoba_ovladani_vibrator", 38, 18, 3.8, 0.4, 0.8, 1.45, 38),
    ("15_detail_nadoba_okraj_sklo", 110, 24, 3.6, 0.8, 0.9, 2.05, 38),
    ("16_detail_motor_bateri", 70, 22, 3.2, 0.55, 0.05, 0.95, 38),
    ("17_detail_klin_a_zebrik", 205, 10, 3.6, 0.2, 2.3, 1.1, 38),
    ("18_detail_nadrz_nafta_zepredu", 15, 18, 2.2, 0.55, -0.55, 0.95, 38),
    ("19_detail_nadrz_nafta_zprava", 300, 20, 2.0, 0.55, -0.55, 0.95, 38),
    ("20_detail_oj_brzda_retez", 330, 22, 3.0, 0.0, -1.7, 0.55, 38),
    ("22_oj_shora", 0, 82, 3.4, 0.0, -1.45, 0.5, 38),
    ("23_oj_z_boku", 270, 8, 3.4, 0.0, -1.45, 0.5, 38),
    ("24_oj_zepredu", 25, 18, 2.6, 0.0, -1.7, 0.5, 38),
    ("21_detail_mlyn_sneka_nadobka", 335, 22, 2.8, -0.3, -0.1, 1.15, 38),
]

MAX_VIEWS = [
    ("01_nadobka_zprava", 250, 18, 3.8, -0.55, 2.3, 1.6, 38),
    ("02_nadobka_zepredu", 330, 18, 3.6, -0.55, 2.3, 1.6, 38),
    ("03_nadobka_zezadu", 200, 20, 3.6, -0.55, 2.3, 1.6, 38),
    ("04_srovnani_puvodni_nadobka", 250, 18, 3.8, -0.55, 2.3, 1.6, 38),
    ("10_max_s_vozikem_zezadu_zprava", 228, 18, 17.0, -0.6, 6.5, 0.9, 34),
    ("11_max_s_vozikem_zezadu", 180, 14, 14.0, 0.0, 7.5, 1.0, 34),
    ("12_max_s_vozikem_shora", 270, 82, 22.0, -0.8, 4.2, 0.5, 34),
    ("13_max_s_vozikem_zprava", 270, 8, 22.0, -0.6, 3.6, 1.0, 34),
    ("14_tazny_vesak_detail", 205, 16, 3.2, 0.0, 6.95, 0.55, 38),
    ("15_zaprazeni_detail", 150, 20, 4.2, 0.0, 7.5, 0.7, 38),
    ("16_hadice_u_nadobky", 232, 20, 4.8, -1.6, 2.6, 1.2, 38),
    ("17_max_s_vozikem_slozena_hadice", 228, 18, 17.0, -0.6, 6.5, 0.9, 34),
]


def run(name):
    p = os.path.join(HERE, name)
    ns = {"__file__": p, "__name__": "headless"}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    return ns


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import build_trailer_mill
    build_trailer_mill.build()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("uloženo:", BLEND)


def setup_render(width=1500, height=900):
    sc = bpy.context.scene
    engine = None
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            engine = eng
            break
        except TypeError:
            pass
    if engine is None:
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.light = "STUDIO"
        sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.46, 0.50, 0.55, 1.0)
    bg.inputs[1].default_value = 0.9
    sc.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sun.rotation_euler = (math.radians(42), math.radians(12), math.radians(35))
    sc.collection.objects.link(sun)
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    for o in bpy.data.objects:
        if o.get("i3D_nonRenderable") or (o.type == "LIGHT" and o is not sun):
            o.hide_render = True
    for c in list(bpy.data.collections):
        if c.name.endswith("_Preview"):
            for o in c.objects:
                o.hide_render = False
    return sc, cam, cam_data


def render_views(views, outdir):
    os.makedirs(outdir, exist_ok=True)
    sc, cam, cam_data = setup_render()
    for name, az, el, dist, tx, ty, tz, lens in views:
        cam_data.lens = lens
        a, e = math.radians(az), math.radians(el)
        target = Vector((tx, ty, tz))
        pos = target + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
        cam.location = pos
        cam.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(outdir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("render:", sc.render.filepath)


def render_cart():
    if bpy.data.filepath != BLEND:
        bpy.ops.wm.open_mainfile(filepath=BLEND)
    for o in bpy.data.objects:
        if o.name.startswith(("millHoseSeg", "millHoseEnd")):
            o.hide_render = True
    render_views(CART_VIEWS, os.path.join(OUT, "vozik"))


def _hose(P, pts_ctrl, radius=0.050):
    """Hadice (korugovaná, černá) po křivce Catmull-Rom přes řídicí body, články válců; na koncích spojky Storz.
    Vrací délku v metrech."""
    from sdt_tanks import Mesh
    ctrl = [Vector(p) for p in pts_ctrl]
    pts = []
    n = 14
    ext = [ctrl[0] * 2 - ctrl[1]] + ctrl + [ctrl[-1] * 2 - ctrl[-2]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n):
            t = k / n
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    pts.append(ctrl[-1])
    h = Mesh("Concept_Hose")
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        h.cyl(a, b, radius, "SDT_HoseBlack", seg=12)
        if k % 2 == 0:
            h.cyl(a, a + (b - a) * 0.45, radius * 1.10, "SDT_HoseBlack", seg=12)
    for p, q in ((pts[0], pts[1]), (pts[-1], pts[-2])):
        d = (q - p).normalized()
        h.cyl(p, p + d * 0.12, 0.078, "SDT_Alu", seg=24)
        h.cyl(p + d * 0.12, p + d * 0.16, 0.092, "SDT_Alu", seg=24)
    h.finish()
    return sum(((b - a).length for a, b in zip(pts, pts[1:])), 0.0)


def compose():
    bpy.ops.wm.open_mainfile(filepath=MAX_BLEND)
    import sdt_parts as P
    import sdt_lime as LIME
    import sdt_mlyn as MILL

    def hide_tree(o):
        o.hide_render = True
        o.hide_viewport = True
        for ch in o.children:
            hide_tree(ch)

    for o in bpy.data.objects:
        if o.name in ("tarpF", "tarpL", "tarpR"):
            hide_tree(o)

    old = [o for o in bpy.data.objects if o.name in ("Tank_Induction", "Tank_Induction_Fittings", "Tank_Induction_Lid",
                                                    "Tank_Induction_Stand")]
    root = old[0].parent
    coll = bpy.data.collections["SprayDroneTrailerMax"]
    P._coll, P._root = coll, root
    ix, iy, deck = -0.55, 2.19, 1.00
    lime_ports = LIME.build_lime_vessel("Tank_InductionLime", ix, iy, deck)
    hitch = LIME.build_rear_hitch()
    print("vápenná nádobka:", {k: tuple(round(c, 3) for c in v) if hasattr(v, "__len__") else round(v, 3) for k, v in lime_ports.items()})
    print("koule:", tuple(round(c, 3) for c in hitch["ball"]))

    P.begin("SprayDroneMill", "SprayDroneMillRoot")
    mill_root = P._root
    ports = MILL.build_all()
    off = Vector((0.0, hitch["ball"].y - ports["hitch"].y, 0.0))
    pc = ports["hose_port"] + off
    inlet = lime_ports["inlet"]
    way = [pc + Vector((-0.035, 0, 0)), pc + Vector((-0.70, -0.10, -0.02)), Vector((-1.75, pc.y - 0.5, 0.42)),
           Vector((-1.85, pc.y - 1.6, 0.12)), Vector((-1.85, 6.3, 0.10)), Vector((-1.85, 4.2, 0.10)), Vector((-1.80, 3.1, 0.35)),
           Vector((-1.62, 2.55, 0.95)), Vector((inlet.x - 0.62, inlet.y + 0.05, inlet.z - 0.05)), inlet + Vector((-0.02, 0, 0))]
    P.begin("ConceptHose", "ConceptHoseRoot")
    length = _hose(P, way)
    print("délka hadice (m): %.2f" % length)
    mill_root.location = off

    stored = [o for o in bpy.data.objects if o.name.startswith(("Mill_HoseStored", "Mill_PortCap"))]
    deployed = [o for o in bpy.data.objects if o.name.startswith("Concept_Hose")]
    for o in stored:
        o.hide_render = True
    for o in old:
        o.hide_render = True
        o.hide_viewport = True
    render_views([v for v in MAX_VIEWS if not v[0].startswith(("04_", "17_"))], os.path.join(OUT, "max"))
    for o in stored:
        o.hide_render = False
    for o in deployed:
        o.hide_render = True
    render_views([v for v in MAX_VIEWS if v[0].startswith("17_")], os.path.join(OUT, "max"))
    for o in stored:
        o.hide_render = True
    for o in deployed:
        o.hide_render = False
    for o in old:
        o.hide_render = False
    for o in bpy.data.objects:
        if o.name.startswith("Tank_InductionLime"):
            o.hide_render = True
    render_views([v for v in MAX_VIEWS if v[0].startswith("04_")], os.path.join(OUT, "max"))


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    steps = args or ["build", "render"]
    if "build" in steps:
        build()
    if "render" in steps:
        render_cart()
    if "compose" in steps:
        compose()
    if "export" in steps:
        if "io_export_i3d_reworked" not in bpy.context.preferences.addons:
            addon_utils.enable("io_export_i3d_reworked", default_set=False)
        if bpy.data.filepath != BLEND:
            bpy.ops.wm.open_mainfile(filepath=BLEND)
        run("export_mill_mod.py")["build_mod"]()


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
