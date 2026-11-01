"""Export mlýnkového vozíku na vápno do módu (vehicles/sdtLimeMill).

Postup jako export_mini_mod.py (i3d, materiály na vehicleShader, mapování uzlů, XML ze šablony, obrázek do obchodu): spustí se
export_middle_mod.py do stejného jmenného prostoru a přepíšou se cesty, seznam uzlů, kola a části, které se u vozíku liší
(žádný dron, žádný žebřík, vmask je vanilla default_vmask).

Bez okna: blender.exe -b blender\\spraydrone_mill.blend --python blender\\headless_mill.py -- export
"""

import os
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_base = os.path.join(_HERE, "export_middle_mod.py")
exec(compile(open(_base, encoding="utf-8").read(), _base, "exec"), globals())

VEH_DIR = os.path.join(MOD_DIR, "vehicles", "sdtLimeMill")
I3D_PATH = os.path.join(VEH_DIR, "sdtLimeMill.i3d")
XML_PATH = os.path.join(VEH_DIR, "sdtLimeMill.xml")
TEMPLATE = os.path.join(HERE, "templates", "sdtLimeMill.xml.in")
STORE_DDS = os.path.join(VEH_DIR, "store_sdtLimeMill.dds")
SHOT_DIR = os.path.join(PROJECT, "out", "mod_build_mill")
ICON_DDS = os.path.join(SHOT_DIR, "icon_sdtLimeMill.dds")      # ikona módu zůstává od velkého vleku
TEX_DIR = os.path.join(VEH_DIR, "textures")

VMASK = {"trailer": "$data/shared/default_vmask.png", "drone": "$data/shared/default_vmask.png"}

_p = os.path.join(HERE, "build_trailer_mill.py")
_ns = {"__file__": _p, "__name__": "mill_consts"}
exec(compile(open(_p, encoding="utf-8").read(), _p, "exec"), _ns)
HOSE_SEGMENTS = _ns["HOSE_SEGMENTS"]

MAPPED_NODES = [
    "sdtLimeMill_main_component1", "sdtLimeMill_vis", "attacherJoint", "wheelFrontLeft", "wheelFrontRight", "jockeyWheel",
    "exactFillRootNode", "dieselFillRootNode", "millDieselNeck", "millSoundNode", "millDustIn", "millOutletPort", "millPortCap",
    "millStartButton", "millStartRing", "millValveLever", "millSpoutPivot", "millFillHead", "millBagNeck", "millSpoutJoint", "coarseFillPlane",
    "exitPoint", "outdoorCameraTarget", "outdoorCamera",
]
WHEEL_ORDER = [("wheelFrontLeft", True), ("wheelFrontRight", False)]
HIDDEN = ["millBagNeck", "coarseFillPlane"]


def load_car_module():
    ns = {"__file__": _p, "__name__": "car_module"}
    exec(compile(open(_p, encoding="utf-8").read(), _p, "exec"), ns)
    ns["DRONE_VARIANTS"] = {}
    return ns


def export_i3d(car):
    os.makedirs(VEH_DIR, exist_ok=True)
    s = bpy.context.scene.I3D_UIexportSettings
    s.i3D_exportUseSoftwareFileName = False
    s.i3D_exportFileLocation = I3D_PATH
    s.i3D_gameLocationDisplay = GAME_DIR
    s.i3D_binaryFiles = True
    s.i3D_exportAxisOrientations = "BAKE_TRANSFORMS"
    s.i3D_exportRelativePaths = True
    s.i3D_exportLights = False
    s.i3D_exportCameras = True
    s.i3D_exportAnimation = False

    comp = bpy.data.objects[car["COMPONENT_NAME"]]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    tree = [comp] + list(comp.children_recursive)
    for o in tree:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = comp
    for f in (I3D_PATH, I3D_PATH + ".shapes"):
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
    for f in (I3D_PATH, I3D_PATH + ".shapes"):
        if not os.path.exists(f):
            raise RuntimeError(f"export nevytvořil {f}\n{log.getvalue()[-2000:]}")
    return len(tree)


def shared_values():
    return {}


def drone_nodes(car):
    return []


def hidden_nodes(car):
    return list(HIDDEN)


def jockey_values(car):
    jx, jy, jz = car["JOCKEY_X"], car["JOCKEY_Y"], car["JOCKEY_Z"]
    return {"JOCKEY_DOWN": fmt(b2i((jx, jy, jz))), "JOCKEY_UP": fmt(b2i((jx, jy, jz + car["JOCKEY_LIFT"])))}


def write_vehicle_xml(car, mappings):
    values = {"WHEELS": wheels_xml(car), "I3D_MAPPINGS": mappings, "ATTACHER_HEIGHT": "%.2f" % car["COUPLER_Z"],
              "CENTER_OF_MASS": fmt(b2i(car["CENTER_OF_MASS"])), "HOPPER_CAPACITY": str(car["HOPPER_CAPACITY"]),
              "DIESEL_CAPACITY": str(car["DIESEL_CAPACITY"]), "FINE_CAPACITY": str(car["FINE_CAPACITY"])}
    values.update(jockey_values(car))
    values.update(vehicle_size(car))
    text = open(TEMPLATE, encoding="utf-8").read()
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    left = sorted(set(re.findall(r"\{\{(\w+)\}\}", text)))
    if left:
        raise RuntimeError(f"v šabloně zůstal nevyplněný zástupce: {left}")
    ET.fromstring(text.encode("utf-8"))
    with open(XML_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return values


def _store_pose(car):
    """Obrázek do obchodu: bez rozvinuté hadice (články leží v počátku), uložená hadice na cívce zůstává."""
    hidden = {}
    for o in bpy.data.objects:
        hide = bool(o.get("i3D_nonRenderable")) or o.name in HIDDEN
        for c in o.users_collection:
            if c.name.startswith("REF_"):
                hide = True
        hidden[o.name] = o.hide_render
        o.hide_render = hide or o.hide_render
    bpy.context.view_layer.update()

    def restore():
        for name, h in hidden.items():
            bpy.data.objects[name].hide_render = h
    return restore


def build_mod():
    car = load_car_module()
    os.makedirs(TEX_DIR, exist_ok=True)
    n = export_i3d(car)
    used = apply_vehicle_shader(I3D_PATH)
    print(f"materiály na vehicleShader: {len(used)} ({sorted(set(used.values()))})")
    hide_nodes(I3D_PATH, hidden_nodes(car))
    mappings, found = i3d_mappings(I3D_PATH, MAPPED_NODES)
    values = write_vehicle_xml(car, mappings)
    make_images(car)
    print(f"i3d: {n} uzlů | mapování: {len(found)}")
    print(f"rozměry: {values['SIZE_WIDTH']} x {values['SIZE_LENGTH']} x {values['SIZE_HEIGHT']} m, "
          f"lengthOffset {values['SIZE_LENGTH_OFFSET']}")
    for f in sorted(os.listdir(VEH_DIR)):
        p = os.path.join(VEH_DIR, f)
        if os.path.isfile(p):
            print(f"  {f}: {os.path.getsize(p):,} B")


if __name__ == "__main__":
    build_mod()
