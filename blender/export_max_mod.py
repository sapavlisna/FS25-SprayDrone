"""Export velkého tandemového vleku se dvěma drony do módu (vehicles/sprayDroneTrailerMax).

Postup jako export_middle_mod.py (vmask, i3d, materiály na vehicleShader, mapování uzlů, XML ze šablony, obrázek do obchodu):
ten se spustí do stejného jmenného prostoru a přepíšou se cesty, seznam uzlů, kola a části, které se liší (dvě nádrže, osm
šachet nabíječky, druhý dron s prefixy Drone2_*).

Bez okna: blender.exe -b blender\\spraydrone_trailer_max.blend --python blender\\headless_max.py -- export
"""

import os
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_base = os.path.join(_HERE, "export_middle_mod.py")
exec(compile(open(_base, encoding="utf-8").read(), _base, "exec"), globals())

VEH_DIR = os.path.join(MOD_DIR, "vehicles", "sprayDroneTrailerMax")
I3D_PATH = os.path.join(VEH_DIR, "sprayDroneTrailerMax.i3d")
XML_PATH = os.path.join(VEH_DIR, "sprayDroneTrailerMax.xml")
TEMPLATE = os.path.join(HERE, "templates", "sprayDroneTrailerMax.xml.in")
STORE_DDS = os.path.join(VEH_DIR, "store_sprayDroneTrailerMax.dds")
SHOT_DIR = os.path.join(PROJECT, "out", "mod_build_max")
ICON_DDS = os.path.join(SHOT_DIR, "icon_sprayDroneTrailerMax.dds")      # ikona módu zůstává od velkého vleku
TEX_DIR = os.path.join(VEH_DIR, "textures")
DECAL_SOURCE = os.path.join(MOD_DIR, "vehicles", "sprayDroneTrailerMiddle", "textures", "sdt_decals.dds")

BATTERY_SLOTS = 10
MAPPED_NODES = [
    "sprayDroneTrailerMax_main_component1", "sprayDroneTrailerMax_vis", "attacherJoint",
    "wheelFrontLeft", "wheelFrontRight", "wheelBackLeft", "wheelBackRight",
    "ladderHinge", "ladderGrab", "jockeyWheel", "chargerLid", "ladderTrigger",
    "drawbarTractorSet", "drawbarCarSet", "airIn", "airIn_detached", "airOut", "airOut_detached", "electric",
    "electric_detached", "hoseLidHinge", "hoseLidHingeB",
] + [
    "fillTrigger", "exactFillRootNode", "tankMain3000", "tankMain5000", "tankMain3000B", "tankMain5000B",
    "concentrateFillRootNode",
    "mixerMotor", "mixerSoundNode", "toolboxActivateNode", "Toolbox_Door", "concentrateNeckNode", "dieselNeckNode",
    "colTank3000", "colTank5000", "colTank3000B", "colTank5000B", "colGenerator2",
] + [f"toolboxCanister{i}" for i in range(1, 49)] + [
    "rearLight52_left", "rearLight52_right", "plateNumberLight03", "sideMarker05_left", "sideMarker05_right",
    "exitPoint", "outdoorCameraTarget", "outdoorCamera", "droneCamera1", "droneCamera2", "droneOutTarget1", "droneOutTarget2", "droneOutCamera1", "droneOutCamera2",
    "occlusionAreaStart", "occlusionAreaWidth", "occlusionAreaHeight", "licensePlateBack", "generatorExhaust", "dieselFillRootNode",
] + [f"{kind}{i}" for kind in ("battery", "batterySlotDeck") for i in range(1, BATTERY_SLOTS + 1)] + \
    [f"battery{i}{size}" for i in range(1, BATTERY_SLOTS + 1) for size in "SML"] + [
    "batteryCharger", "antennaBase", "antennaBoosted", "antennaLarge", "gpsRtkBox", "antennaBoostedTele1", "antennaBoostedTele2", "antennaLargeTele1", "antennaLargeTele2", "gpsRtkBoxTele1", "gpsRtkBoxTele2", "chargerCable", "chargerCable2", "generator2", "dieselNeckNode2", "generatorExhaust2", "fillHoseCoil", "fillHoseStart",
] + [f"fillHoseLay{i}" for i in range(1, 9)] + [f"fillHoseSeg{i}" for i in range(1, 97)] + [
    "fillHoseNozzle", "fillHoseParkPos", "fillHoseBCoil", "fillHoseBStart",
] + [f"fillHoseBLay{i}" for i in range(1, 9)] + [f"fillHoseBSeg{i}" for i in range(1, 97)] + [
    "fillHoseBNozzle", "fillHoseBParkPos",
] + [f"Charger_Led_{k}_{n}" for k in range(1, BATTERY_SLOTS + 1) for n in range(5)] + \
    [f"relaySlot{i}{tail}" for i in range(1, 5) for tail in ("", "_pole")] + ["plannerScreenNode", "plannerScreenOn"]
# v i3d skryté: baterie S a L (podle varianty je ukáže skript) a šachty 6-10, které skript zatím nepoužívá
BATTERY_HIDDEN = [f"battery{i}{size}" for i in range(1, BATTERY_SLOTS + 1) for size in "SL"] + \
    [f"battery{i}M" for i in range(6, BATTERY_SLOTS + 1)]
DRONE_B_KEYS = {"S2": "Drone2_S_", "M2": "Drone2_A_", "L2": "Drone2_L_"}


def load_car_module():
    p = os.path.join(HERE, "build_trailer_max.py")
    ns = {"__file__": p, "__name__": "car_module"}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    # exportní funkce procházejí DRONE_VARIANTS: oba drony v jednom slovníku, druhý s klíči S2, M2, L2
    ns["DRONE_VARIANTS"] = {**ns["DRONE_VARIANTS"], **DRONE_B_KEYS}
    ns["DRONE_HIDDEN"] = ("S", "L", "S2", "L2")
    return ns


def wheels_xml(car):
    out = []
    for repr_node, is_left in WHEEL_ORDER:
        out.append(
            wheel_open(car, is_left) +
            f'                        <physics tipOcclusionAreaGroupId="1" restLoad="2.5" repr="{repr_node}" '
            f'forcePointRatio="0.35" initialCompression="8" suspTravel="0.10" spring="125" damper="50" '
            f'supportsWheelSink="false" frictionScale="1.6"{y_offset_attr(car)}/>\n' +
            wheel_tail(car, is_left))
    return "\n".join(out)


_base_ladder_values = ladder_values


def ladder_values(car):
    """Žebřík se skládá jako u Middle (HINGE_* z ladder_values v export_middle_mod.py, počítané z geometrie Max); navíc
    víko nabíječky zavřené otočené o 90° kolem svislé osy (truhla stojí u levého okraje)."""
    values = _base_ladder_values(car)
    dcc = importlib.import_module("io_export_i3d_reworked.dcc.dccBlender")
    e = dcc.bakeTransformMatrix(Matrix.Rotation(car["CHEST_ROT"], 4, "Z")).to_euler("XYZ")
    values["LID_CLOSED"] = fmt((math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)))
    return values


def center_of_mass(car):
    """Těžiště vozidla bez nádrží (i3d: y nahoru, z vpřed): 0,25 m za centrálou, výška kolem horní hrany podvozku. Tak zůstává na oji
    kolem 14 % hmotnosti (ekvivalentní náprava tandemu -3,275, závěs +3,45)."""
    return fmt(b2i((0.0, car["GEN_POS"][1] + 0.25, car["DECK_TOP"] + 0.40)))


def hose_lid_parts_xml(car):
    """Víka kapes navíječů v animaci foldLadder: z otevřené polohy (stav v i3d) do zavřené, po složení dronu jako úchyty lyží."""
    dcc = importlib.import_module("io_export_i3d_reworked.dcc.dccBlender")
    t0, t1 = car["CLAMP_TIME"]
    out = []
    for tag in ("", "B"):
        hinge = bpy.data.objects[f"hoseLidHinge{tag}"]
        rot = hinge.matrix_local.to_quaternion().to_matrix().to_4x4()
        e = dcc.bakeTransformMatrix(rot).to_euler("XYZ")
        opened = fmt((math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)))
        out.append(f'            <part node="{hinge.name}" startTime="{t0 + 0.1:g}" endTime="{t1 + 0.2:g}" startRot="{opened}" '
                   f'endRot="0 0 0"/>')
        out.append(f'            <sound template="metalClose" startTime="{t1 + 0.15:g}" direction="1" volumeScale="0.8" '
                   f'pitchScale="1.15" linkNode="{hinge.name}"/>')
        out.append(f'            <sound template="coverMetalOpen" startTime="{t0 + 0.15:g}" direction="-1" volumeScale="0.8" '
                   f'pitchScale="1.1" linkNode="{hinge.name}"/>')
    return "\n".join(out)


def write_vehicle_xml(car, mappings):
    values = {"WHEELS": wheels_xml(car), "LEGACY_WHEELS": legacy_wheels_xml(car), "I3D_MAPPINGS": mappings,
              "ATTACHER_HEIGHT": "%.2f" % car["COUPLER_Z"],
              "CLAMP_PARTS": clamp_parts_xml(car) + ladder_grab_part_xml(car) + "\n" + hose_lid_parts_xml(car),
              "CENTER_OF_MASS": center_of_mass(car)}
    for key, prefix in car["DRONE_VARIANTS"].items():
        values[f"DRONE_PARTS_{key}"] = drone_parts_xml(car, prefix)
    values["DRONE_PARTS"] = values["DRONE_PARTS_M"]
    values.update(ladder_values(car))
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
    """Vlek složený (žebřík zasunutý, úchyty zavřené, víko nabíječky zavřené, kabel a ležící hadice skryté), oba střední
    drony složené, drony S a L skryté, jen výchozí nádrže (2x 3000 l). Vrací funkci, která stav vrátí."""
    shown = (car["DRONE_VARIANTS"]["M"], car["DRONE_VARIANTS"]["M2"])
    others = tuple(p for p in car["DRONE_VARIANTS"].values() if p not in shown)
    hinges, opened = [], {}
    for prefix in shown:
        parts = car["drone_fold_parts"](prefix)
        car["set_drone_unfold"](0.0, parts, prefix)
        hinges += [o for o in bpy.data.objects if o.name.startswith(prefix + "ClampHinge_")]
    hinges += [bpy.data.objects[n] for n in ("hoseLidHinge", "hoseLidHingeB")]
    car["set_ladder"](1.0)
    opened = {o.name: o.rotation_euler.y for o in hinges}
    for o in hinges:
        o.rotation_euler.y = 0.0
    lid = bpy.data.objects["chargerLid"]
    lid_open = lid.rotation_euler.x
    lid.rotation_euler.x = 0.0
    hidden = {}
    for o in bpy.data.objects:
        hide = (o.name.startswith(others) or bool(o.get("i3D_nonRenderable")) or o.name.endswith("_Tip")
                or _under(o, "drawbarCarSet")
                or o.name in ("Charger_Plug", "Gen_0_ChargePlug")
                or re.match(r"^battery\d+[SL]$", o.name) is not None
                or re.match(r"^Tank_Main5000", o.name) is not None
                or re.match(r"^(fillHoseB?Seg\d+|HoseNozzle_\w+)$", o.name) is not None)
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
        car["set_ladder"](0.0)
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
    hide_nodes(I3D_PATH, hidden_nodes(car) + [f"battery{i}M" for i in range(6, BATTERY_SLOTS + 1)] + ["drawbarCarSet"] + ["antennaBase", "antennaBoosted", "antennaLarge", "gpsRtkBox"])
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
