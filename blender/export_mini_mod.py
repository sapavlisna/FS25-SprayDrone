"""Export malého vleku do módu (vehicles/sprayDroneTrailerMini).

Postup jako export_middle_mod.py (vmask, i3d, materiály na vehicleShader, mapování uzlů, XML ze šablony, obrázek do obchodu):
ten se spustí do stejného jmenného prostoru a přepíšou se cesty, seznam uzlů, kola a části, které se u malého vleku liší
(žádný žebřík, jen dron S, šachta baterií místo truhly nabíječky).

Bez okna: blender.exe -b blender\\spraydrone_trailer_mini.blend --python blender\\headless_mini.py -- export
"""

import os
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_base = os.path.join(_HERE, "export_middle_mod.py")
exec(compile(open(_base, encoding="utf-8").read(), _base, "exec"), globals())

VEH_DIR = os.path.join(MOD_DIR, "vehicles", "sprayDroneTrailerMini")
I3D_PATH = os.path.join(VEH_DIR, "sprayDroneTrailerMini.i3d")
XML_PATH = os.path.join(VEH_DIR, "sprayDroneTrailerMini.xml")
TEMPLATE = os.path.join(HERE, "templates", "sprayDroneTrailerMini.xml.in")
STORE_DDS = os.path.join(VEH_DIR, "store_sprayDroneTrailerMini.dds")
SHOT_DIR = os.path.join(PROJECT, "out", "mod_build_mini")
ICON_DDS = os.path.join(SHOT_DIR, "icon_sprayDroneTrailerMini.dds")      # ikona módu zůstává od velkého vleku
TEX_DIR = os.path.join(VEH_DIR, "textures")
DECAL_SOURCE = os.path.join(MOD_DIR, "vehicles", "sprayDroneTrailerMiddle", "textures", "sdt_decals.dds")

MAPPED_NODES = [
    "sprayDroneTrailerMini_main_component1", "sprayDroneTrailerMini_vis", "attacherJoint",
    "wheelFrontLeft", "wheelFrontRight", "jockeyWheel", "chargerLid", "chargerCable",
    "fillTrigger", "exactFillRootNode", "concentrateFillRootNode", "dieselFillRootNode",
    "mixerMotor", "mixerSoundNode", "toolboxLid", "toolboxActivateNode", "toolboxLid2", "toolboxActivateNode2", "concentrateNeckNode", "dieselNeckNode",
    "rearLight52_left", "rearLight52_right", "plateNumberLight03", "sideMarker05_left", "sideMarker05_right",
    "exitPoint", "outdoorCameraTarget", "outdoorCamera",
    "occlusionAreaStart", "occlusionAreaWidth", "occlusionAreaHeight", "licensePlateBack", "generatorExhaust",
    "batteryCharger", "padAnchor", "padHingeZ", "padHingeH", "padHingeP", "padHingeEnd", "droneCarrier", "padSideL", "padSideR",
    "fillHoseCoil", "fillHoseStart", "fillHoseNozzle", "fillHoseParkPos",
] + [f"padLeg{i}" for i in range(1, 7)] + [f"padLegRod{i}" for i in range(1, 7)] + [f"padLegFoot{i}" for i in range(1, 7)] \
  + [f"fillHoseLay{i}" for i in range(1, 9)] + [f"fillHoseSeg{i}" for i in range(1, 97)] \
  + [f"toolboxCanister{i}" for i in range(1, 9)] \
  + [f"{kind}{i}" for kind in ("battery", "batterySlotDeck") for i in range(1, 5)] \
  + [f"battery{i}S" for i in range(1, 5)] \
  + [f"Charger_Led_{k}_{n}" for k in range(1, 5) for n in range(5)] \
  + ["relaySlot1", "relaySlot1_pole", "plannerScreenNode", "plannerScreenOn"]
BATTERY_HIDDEN = []
WHEEL_ORDER = [("wheelFrontLeft", True), ("wheelFrontRight", False)]


def load_car_module():
    p = os.path.join(HERE, "build_trailer_mini.py")
    ns = {"__file__": p, "__name__": "car_module"}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    return ns


def ladder_values(car):
    dcc = importlib.import_module("io_export_i3d_reworked.dcc.dccBlender")
    jx, jy, jz = car["JOCKEY_X"], car["JOCKEY_Y"], car["DRAWBAR_Z"]

    def i3d_rot(m):
        e = dcc.bakeTransformMatrix(m).to_euler("XYZ")
        return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))

    return {
        "JOCKEY_DOWN": fmt(b2i((jx, jy, jz))),
        "JOCKEY_UP": fmt(b2i((jx, jy, jz + car["JOCKEY_LIFT"]))),
        "LID_OPEN": fmt(i3d_rot(bpy.data.objects["chargerLid"].matrix_local.to_quaternion().to_matrix().to_4x4())),
        "LID_CLOSED": fmt(i3d_rot(car["BAY_ROTATE_MATRIX"] @ car["BAY_LID_BASIS"])),
        "LID_START": "%g" % car["LID_TIME"][0],
        "LID_END": "%g" % car["LID_TIME"][1],
        "CABLE_START": "%g" % car["CABLE_TIME"][0],
        "CABLE_END": "%g" % car["CABLE_TIME"][1],
    }


def drone_yaw_deg(car):
    """O kolik stupňů (osa Y v i3d) je dron ve složené bedně otočený navíc; skript otočí carrier o opačný úhel."""
    dcc = importlib.import_module("io_export_i3d_reworked.dcc.dccBlender")
    m = dcc.bakeTransformMatrix(Matrix.Rotation(car["DRONE_EXTRA_ROT"], 4, "Z")).to_3x3()
    v = m @ Vector((0, 0, 1))
    return math.degrees(math.atan2(v.x, v.z))


def pad_values(car):
    """Bedna na dron (build_pad_crate): časování v animaci foldTrailer, rozměry nožiček a otočení dronu v bedně.
    Šířka a hloubka rozložené plošiny se v Lua dopočítají přímo z uzlů (padLeg*, padHingeEnd), nejsou tu duplikované."""
    return {
        "PAD_FOLD_START": "%.4f" % (car["CLAMP_TIME"][0] / car["FOLD_DURATION"]),
        "PAD_FOLD_END": "%.4f" % (car["DRONE_UNFOLD_TIME"] / car["FOLD_DURATION"]),
        "DRONE_FOLD_END": "%.4f" % (car["DRONE_UNFOLD_TIME"] / car["FOLD_DURATION"]),
        "SECURED_FOLD_TIME": "%.4f" % (car["CLAMP_TIME"][1] / car["FOLD_DURATION"]),
        "PAD_LEG_REST": "%g" % car["CRATE_LEG_REST"],
        "PAD_LEG_FOOT": "%g" % car["CRATE_LEG_FOOT"],
        "PAD_MAX_LEG_LENGTH": "%g" % car["CRATE_MAX_LEG_LENGTH"],
        "PAD_MAX_HEIGHT_DIFF": "%g" % car["CRATE_MAX_HEIGHT_DIFF"],
        "PAD_CHECK_HEIGHT": "%g" % car["CRATE_CHECK_HEIGHT"],
        "PAD_LIFT": "%g" % car["CRATE_LIFT"],
        "PAD_DRONE_YAW": "%.4f" % drone_yaw_deg(car),
        "PAD_SETTLE": "%.3f" % car["CRATE_SETTLE"],
        "PAD_SIDE_LENGTH": "%.3f" % car["SIDE_H"],
        "CENTER_OF_MASS": fmt(b2i(car["CENTER_OF_MASS"])),
    }


def clamp_parts_xml(car):
    """Mini nemá svorky lyžin (bedna dron zajišťuje sama, viz build_trailer_mini.mount_drone_on_tray) - žádné
    ClampHinge_i uzly v i3d neexistují, takže se přepisuje verze z export_middle_mod.py (ta by na ně spadla)."""
    return ""


_car_drone_nodes = drone_nodes


def drone_nodes(car):
    """Jako u Middle, ale bez uzlů svorek lyžin (Clamp_i / ClampHinge_i) - bedna dron zajišťuje sama, svorky se nestaví."""
    return [n for n in _car_drone_nodes(car) if "_Clamp" not in n]


def hidden_nodes(car):
    """Nožičky bedny jsou ve složeném stavu skryté, skript je ukáže při rozkládání."""
    return list(BATTERY_HIDDEN) + [f"padLeg{i}" for i in range(1, 7)]


_car_vehicle_size = vehicle_size


def vehicle_size(car):
    """Rozměry včetně složeného dronu (stav v i3d): přečnívá o ~0,5 m za vlek a je nejvyšším dílem. Boční stěny bedny stojí ve složeném
    stavu na palubě, takže rozměr nezvětšují (sklopené jsou vedle vleku, to se nepočítá)."""
    values = _car_vehicle_size(car)
    mn, mx = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in bpy.data.collections[car["COLLECTION_NAME"]].objects:
        if o.type == "MESH" and not o.get("i3D_nonRenderable"):
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mn, mx = Vector(map(min, mn, w)), Vector(map(max, mx, w))
    values.update({
        "SIZE_WIDTH": "%.2f" % (mx.x - mn.x),
        "SIZE_LENGTH": "%.2f" % (mx.y - mn.y),
        "SIZE_HEIGHT": "%.2f" % (mx.z - mn.z),
        "SIZE_LENGTH_OFFSET": "%.2f" % (-(mn.y + mx.y) / 2),
    })
    return values


def write_vehicle_xml(car, mappings):
    values = {"WHEELS": wheels_xml(car), "LEGACY_WHEELS": legacy_wheels_xml(car), "I3D_MAPPINGS": mappings,
              "ATTACHER_HEIGHT": "%.2f" % car["COUPLER_Z"], "CLAMP_PARTS": clamp_parts_xml(car)}
    for key, prefix in car["DRONE_VARIANTS"].items():
        values[f"DRONE_PARTS_{key}"] = drone_parts_xml(car, prefix)
    values.update(ladder_values(car))
    values.update(pad_values(car))
    values.update(vehicle_size(car))
    values.update(shared_values())
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
    """Vlek složený (dron složený, úchyty zavřené, víko šachty zavřené, kabel a zástrčky skryté). Vrací funkci, která
    stav vrátí."""
    prefix = car["DRONE_VARIANTS"]["S"]
    parts = car["drone_fold_parts"](prefix)
    car["set_drone_unfold"](0.0, parts, prefix)
    hinges = [o for o in bpy.data.objects if o.name.startswith(prefix + "ClampHinge_")]
    opened = {o.name: o.rotation_euler.y for o in hinges}
    for o in hinges:
        o.rotation_euler.y = 0.0
    lid = bpy.data.objects["chargerLid"]
    lid_open = lid.rotation_euler.x
    lid.rotation_euler.x = 0.0
    hidden = {}
    for o in bpy.data.objects:
        hide = (bool(o.get("i3D_nonRenderable")) or o.name.endswith("_Tip")
                or o.name in ("chargerCable", "Charger_Plug", "Gen_0_ChargePlug")
                or (o.parent is not None and o.parent.name.startswith("padLeg") and o.parent.name[6:].isdigit()))
        for c in o.users_collection:
            if c.name.startswith("REF_"):
                hide = True
        hidden[o.name] = o.hide_render
        o.hide_render = hide or o.hide_render
    bpy.context.view_layer.update()

    def restore():
        for name, h in hidden.items():
            bpy.data.objects[name].hide_render = h
        for o in hinges:
            o.rotation_euler.y = opened[o.name]
        lid.rotation_euler.x = lid_open
    return restore


def build_mod():
    car = load_car_module()
    os.makedirs(TEX_DIR, exist_ok=True)
    shutil.copy(DECAL_SOURCE, os.path.join(TEX_DIR, "sdt_decals.dds"))
    if "--no-bake" not in sys.argv:
        bake_vmasks(car)
    n = export_i3d(car)
    used = apply_vehicle_shader(I3D_PATH)
    print(f"materiály na vehicleShader: {len(used)} ({sorted(set(used.values()))})")
    hide_nodes(I3D_PATH, hidden_nodes(car))
    mappings, found = i3d_mappings(I3D_PATH, MAPPED_NODES + drone_nodes(car))
    values = write_vehicle_xml(car, mappings)
    make_images(car)
    print(f"i3d: {n} uzlů | mapování: {len(found)}")
    print(f"rozměry: {values['SIZE_WIDTH']} x {values['SIZE_LENGTH']} x {values['SIZE_HEIGHT']} m, "
          f"lengthOffset {values['SIZE_LENGTH_OFFSET']}")
    for f in sorted(os.listdir(VEH_DIR)):
        print(f"  {f}: {os.path.getsize(os.path.join(VEH_DIR, f)):,} B")


if __name__ == "__main__":
    build_mod()
