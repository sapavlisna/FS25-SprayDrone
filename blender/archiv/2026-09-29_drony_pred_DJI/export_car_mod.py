"""Sestaví mód FS25_SprayDroneTrailer z malé verze vleku (spraydrone_trailer_car.blend).

Kroky: export i3d komunitním GIANTS exportérem -> i3dMappings spočítané z hotového i3d ->
vehicle.xml ze šablony (hodnoty animace žebříku z build_trailer_car.py) -> obrázek do obchodu
a ikona jako nekomprimované DDS.

i3dMappings se nepočítají exportérem: jeho "Update XML" bere celou scénu (dron, reference),
takže by čísla uzlů neseděla. Tady se čtou z toho, co se opravdu vyexportovalo.

Spuštění v Blenderu (se scénou z spraydrone_trailer_car.blend):
    p = r"...\\export_car_mod.py"; exec(open(p, encoding="utf-8").read(), {"__file__": p, "__name__": "__main__"})
"""

import contextlib
import importlib
import io
import math
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
MOD_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer")
VEH_DIR = os.path.join(MOD_DIR, "vehicles", "sprayDroneTrailerCar")
I3D_PATH = os.path.join(VEH_DIR, "sprayDroneTrailerCar.i3d")
XML_PATH = os.path.join(VEH_DIR, "sprayDroneTrailerCar.xml")
TEMPLATE = os.path.join(HERE, "templates", "sprayDroneTrailerCar.xml.in")
STORE_DDS = os.path.join(VEH_DIR, "store_sprayDroneTrailerCar.dds")
ICON_DDS = os.path.join(MOD_DIR, "icon_sprayDroneTrailer.dds")
SHOT_DIR = os.path.join(PROJECT, "out", "mod_build")
GAME_DIR = r"E:\SteamLibrary\steamapps\common\Farming Simulator 25"

MAPPED_NODES = [
    "sprayDroneTrailerCar_main_component1", "sprayDroneTrailerCar_vis", "attacherJoint",
    "wheelFrontLeft", "wheelFrontRight", "wheelBackLeft", "wheelBackRight",
    "ladderSlide", "ladderHinge", "jockeyWheel", "chargerLid",
    "fillTrigger", "exactFillRootNode",
    "rearLight52_left", "rearLight52_right", "plateNumberLight03", "sideMarker05_left", "sideMarker05_right",
    "exitPoint", "outdoorCameraTarget", "outdoorCamera",
    "occlusionAreaStart", "occlusionAreaWidth", "occlusionAreaHeight", "licensePlateBack", "generatorExhaust", "dieselFillRootNode",
] + [f"{kind}{i}" for kind in ("battery", "batterySlotTransport", "batterySlotDeck") for i in range(1, 6)] + \
    [f"battery{i}{size}" for i in range(1, 6) for size in "SML"] + [
    "batteryCharger", "chargerCable", "fillHoseCoil", "fillHoseStart",
] + [f"fillHoseLay{i}" for i in range(1, 9)] + [f"fillHoseSeg{i}" for i in range(1, 25)] + [
    "fillHoseNozzle", "fillHoseParkPos",
]
BATTERY_HIDDEN = [f"battery{i}{size}" for i in range(1, 6) for size in "SL"]   # v i3d skryté, skript ukáže podle varianty
# LED materiál: vehicleShader staticLight_vertex, barva z vrcholů, svit (lightIds0.x) řídí skript
EMISSIVE_MATERIALS = {"SDT_NavLed": (0.35, 0.35, 0.35)}
BLINKING_LEDS = (3, 4)                             # zadní ramena blikají, přední svítí (sprayDrone.navLight#blink)
SHADER = "$data/shaders/vehicleShader.xml"
TEMPLATES_XML = os.path.join(GAME_DIR, "data", "shared", "detailLibrary", "materialTemplates.xml")
BASE_MAPS = {"Texture": "$data/shared/white_diffuse.png", "Normalmap": "$data/shared/default_normal.png",
             "Glossmap": "$data/shared/default_vmask.png"}
TEX_DIR = os.path.join(VEH_DIR, "textures")
# vmask (R škrábance, G AO, B špína) na druhé UV (DirtUV, varianta vmaskUV2); kreslí ho bake_vmasks
VMASK = {"trailer": "textures/sdt_vmask_trailer.dds", "drone": "textures/sdt_vmask_drone.dds"}
VMASK_SIZE = {"trailer": 2048, "drone": 1024}
DECAL_TEXTURE = "textures/sdt_decals.dds"
DRONE_SUFFIX = "__D"
# náš materiál -> (šablona z detailLibrary, colorScale nebo None = barva šablony, parametry navíc)
MATERIAL_MAP = {
    "SDT_Frame": ("metalPaintedGraphite", (0.03, 0.03, 0.032), {}),
    "SDT_DeckWood": ("wood1", (0.42, 0.28, 0.16), {}),
    "SDT_TopDeck": ("steelTreadPlate", (0.62, 0.63, 0.64), {}),
    "SDT_TankWhite": ("plasticPainted", (0.85, 0.85, 0.82), {}),
    "SDT_TankBlack": ("plasticPainted", (0.02, 0.02, 0.02), {}),
    "SDT_Rubber": ("rubberBlack", (0.03, 0.03, 0.03), {}),
    "SDT_Rim": ("metalPainted", (0.03, 0.03, 0.03), {}),
    "SDT_GenOrange": ("calibratedPaint", (0.80, 0.30, 0.03), {}),
    "SDT_EngineRed": ("calibratedPaint", (0.55, 0.03, 0.03), {}),
    "SDT_TapeRed": ("reflectorRed", None, {}),
    "SDT_TapeWhite": ("reflectorWhite", None, {}),
    "SDT_Mesh": ("metalPaintedGraphite", (0.06, 0.06, 0.07), {}),
    "SDT_HoseBlue": ("rubber", (0.05, 0.20, 0.60), {}),
    "SDT_HoseBlack": ("rubberBlackHoses", None, {}),
    "SDT_Steel": ("metalGalvanized", None, {}),
    "SDT_LampRed": ("plasticPainted", (0.80, 0.02, 0.02), {}),
    "SDT_LampAmber": ("plasticPainted", (0.90, 0.45, 0.02), {}),
    "SDT_PaintWhite": ("powderCoatMatte", (0.85, 0.85, 0.85), {}),
    "SDT_PaintDark": ("powderCoatMatte", (0.05, 0.055, 0.06), {}),
    "SDT_BatteryGrey": ("plasticGraniteGrainSmall", (0.05, 0.05, 0.055), {}),
    "SDT_ChargerGrey": ("plasticGraniteGrainSmall", (0.13, 0.135, 0.14), {}),
    "SDT_LedGreen": ("plasticPainted", (0.05, 0.85, 0.12), {}),
    "SDT_Screen": ("plasticPainted", (0.02, 0.07, 0.14), {}),
    "SDT_CastIron": ("calibratedCastIron", (0.045, 0.045, 0.048), {}),
    "SDT_PaintRed": ("calibratedPaint", (0.60, 0.02, 0.02), {}),
    "SDT_Plastic": ("plasticGraniteGrainSmall", (0.03, 0.03, 0.03), {}),
    "SDT_Decal": ("plasticPainted", (1.0, 1.0, 1.0), {"clearCoatIntensity": "0.3", "clearCoatSmoothness": "0.7"}),
    "Carbon": ("carbonPattern02", None, {}),
    "Drone_White": ("calibratedGlossPaint", (0.80, 0.81, 0.82), {}),
    "Drone_Accent_A": ("calibratedPaint", (0.75, 0.28, 0.02), {}),
    "Glass_Dark": ("chrome", (0.02, 0.025, 0.03), {}),
    "Steel_Galvanized": ("metalGalvanized", None, {}),
    "Lamp_Green": ("plasticPainted", (0.05, 0.45, 0.08), {}),
    "Lamp_Red": ("plasticPainted", (0.55, 0.02, 0.02), {}),
}
DECAL_MATERIALS = ("SDT_Decal",)
ROTOR_DIRECTIONS = {1: 1, 2: -1, 3: -1, 4: 1}     # souosé rotory se točí proti sobě, úhlopříčky stejně
ARM_UNFOLD_TIME = (0.0, 0.6)                       # části času rozložení (skript: SprayDroneStation.UNFOLD_TIME)
BLADE_UNFOLD_TIME = (0.5, 1.0)
WHEEL_ORDER = [("wheelFrontLeft", True), ("wheelFrontRight", False), ("wheelBackLeft", True), ("wheelBackRight", False)]


def load_car_module():
    p = os.path.join(HERE, "build_trailer_car.py")
    ns = {"__file__": p, "__name__": "car_module"}
    exec(open(p, encoding="utf-8").read(), ns)
    return ns


def b2i(v):
    """Blender (Z nahoru, vpřed -Y) -> i3d (Y nahoru, vpřed +Z), stejně jako BAKE_TRANSFORMS."""
    return Vector((v[0], v[2], -v[1]))


def fmt(v):
    return " ".join("%g" % (0.0 if abs(c) < 5e-7 else round(c, 6)) for c in v)


def export_i3d(car):
    os.makedirs(VEH_DIR, exist_ok=True)
    s = bpy.context.scene.I3D_UIexportSettings
    s.i3D_exportUseSoftwareFileName = False
    s.i3D_exportFileLocation = I3D_PATH
    s.i3D_gameLocationDisplay = GAME_DIR
    s.i3D_binaryFiles = True
    s.i3D_exportAxisOrientations = "BAKE_TRANSFORMS"
    s.i3D_exportRelativePaths = True
    s.i3D_exportLights = True
    s.i3D_exportCameras = True
    s.i3D_exportAnimation = False

    comp = bpy.data.objects[car["COMPONENT_NAME"]]
    car["set_ladder"](0.0)
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
    # výběr z outlineru čte exportér přes ctypes a na zastaralém stromu outlineru shodí Blender; bez něj vezme
    # bpy.context.selected_objects, které tady nastavuje select_set
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


def spray_nozzles(prefix):
    return sorted(o.name for o in bpy.data.objects if o.name.startswith(prefix + "SprayNozzle_"))


def drone_nodes(car):
    """Mapované uzly všech tří dronů (kontrakt docs/PLAN-0.9.md) včetně úchytů lyžin."""
    out = []
    for prefix in car["DRONE_VARIANTS"].values():
        levels = car["rotor_levels"](prefix)
        out += [prefix + "Root", prefix + "Tilt"] + [f"{prefix}ArmPivot_{i}" for i in range(1, 5)]
        out += [f"{prefix}Rotor_{i}{lv}" for i in range(1, 5) for lv in levels]
        out += [name for name, _, _, kind in car["drone_fold_parts"](prefix) if kind == "blade"]
        out += [f"{prefix}{kind}_{i}" for i in range(1, 5) for kind in ("Led", "LedLight")]
        out += [prefix + "FillPort", prefix + "BatterySlot"] + spray_nozzles(prefix)
        out += [f"{prefix}{kind}_{i}" for i in range(1, 5) for kind in ("Clamp", "ClampHinge")]
    return out


def hidden_nodes(car):
    """Uzly, které mají v i3d visibility false: drony a úchyty mimo výchozí variantu, baterie S a L."""
    out = list(BATTERY_HIDDEN)
    for key in car["DRONE_HIDDEN"]:
        prefix = car["DRONE_VARIANTS"][key]
        out += [prefix + "Root"] + [f"{prefix}Clamp_{i}" for i in range(1, 5)]
    return out


def drone_parts_xml(car, prefix):
    """Uzly dronu pro SprayDroneStation: náklon, kloubové díly (složeno/rozloženo), rotory a LED."""
    out = [f'        <tilt node="{prefix}Tilt"/>']
    for name, folded, unfolded, kind in car["drone_fold_parts"](prefix):
        t0, t1 = ARM_UNFOLD_TIME if kind == "arm" else BLADE_UNFOLD_TIME
        out.append(f'        <foldPart node="{name}" foldedRot="0 {math.degrees(folded):.3f} 0" '
                   f'unfoldedRot="0 {math.degrees(unfolded):.3f} 0" startTime="{t0:g}" endTime="{t1:g}"/>')
    for i in range(1, 5):
        for lv in car["rotor_levels"](prefix):
            d = ROTOR_DIRECTIONS[i] * (1 if lv == "Top" else -1)
            out.append(f'        <rotor node="{prefix}Rotor_{i}{lv}" direction="{d}"/>')
    for i in range(1, 5):
        out.append(f'        <navLight node="{prefix}Led_{i}" lightNode="{prefix}LedLight_{i}" '
                   f'blink="{str(i in BLINKING_LEDS).lower()}"/>')
    return "\n".join(out)


def hide_nodes(path, names):
    tree = ET.parse(path)
    left = set(names)
    for el in tree.getroot().find("Scene").iter():
        if el.get("name") in left:
            el.set("visibility", "false")
            left.discard(el.get("name"))
    if left:
        raise RuntimeError(f"skrývané uzly v i3d chybí: {sorted(left)}")
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")


def i3d_mappings(path, names):
    scene = ET.parse(path).getroot().find("Scene")
    found = {}

    def walk(node, comp_index, trail):
        for i, ch in enumerate(list(node)):
            name = ch.get("name")
            idx = trail + [i]
            if name in names:
                if name in found:
                    raise RuntimeError(f"uzel {name} je v i3d víckrát")
                found[name] = f"{comp_index}>" + "|".join(map(str, idx))
            walk(ch, comp_index, idx)

    for ci, comp in enumerate(list(scene)):
        if comp.get("name") in names:
            found[comp.get("name")] = f"{ci}>"
        walk(comp, ci, [])
    missing = [n for n in names if n not in found]
    if missing:
        raise RuntimeError(f"v i3d chybí uzly: {missing}")
    lines = ["    <i3dMappings>"]
    lines += [f'        <i3dMapping id="{n}" node="{found[n]}"/>' for n in names]
    lines.append("    </i3dMappings>")
    return "\n".join(lines), found


def load_templates():
    root = ET.parse(TEMPLATES_XML).getroot()
    return {t.get("name"): t.attrib for t in root.iter("template")}


def apply_vehicle_shader(path):
    """Přepíše materiály v hotovém i3d na vehicleShader s detailními texturami z knihovny hry.

    Uspořádání jako vanilla díly bez vlastní barevné textury: white_diffuse + default_normal, barva přes
    colorScale, parametry šablony (clearCoat, smoothness, porosity). Glossmap je vlastní vmask na druhé UV
    (varianta vmaskUV2): vlek sdt_vmask_trailer, dron (materiály s příponou __D) sdt_vmask_drone. Nálepky
    mají jako Texture atlas sdt_decals. Materiály mimo MATERIAL_MAP dostanou plast nebo kov podle metalické
    složky a barvu ze své diffuseColor. Soubory z Blenderu (zdrojový .png atlasu), na které už nic neodkazuje,
    se z <Files> vyhodí.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    files = root.find("Files")
    if files is None:
        files = ET.Element("Files")
        root.insert(0, files)
    by_name = {f.get("filename"): f.get("fileId") for f in files}
    next_id = [max([int(f.get("fileId")) for f in files] + [0]) + 1]

    def file_id(name):
        if name not in by_name:
            ET.SubElement(files, "File", fileId=str(next_id[0]), filename=name)
            by_name[name] = str(next_id[0])
            next_id[0] += 1
        return by_name[name]

    templates = load_templates()
    shader_id = file_id(SHADER)
    used = {}
    for mat in root.find("Materials"):
        name = mat.get("name")
        if name in EMISSIVE_MATERIALS:
            for child in list(mat):
                mat.remove(child)
            mat.attrib.pop("specularColor", None)
            mat.set("customShaderId", shader_id)
            mat.set("customShaderVariation", "staticLight_vertex")
            ET.SubElement(mat, "CustomParameter", name="colorScale", value="%g %g %g" % EMISSIVE_MATERIALS[name])
            ET.SubElement(mat, "CustomParameter", name="lightIds0", value="0 0 0 0")
            ET.SubElement(mat, "CustomParameter", name="lightTypeBitMask", value="0")
            for tag, fname in BASE_MAPS.items():
                ET.SubElement(mat, tag, fileId=file_id(fname))
            used[name] = "staticLight_vertex"
            continue
        base = name[:-len(DRONE_SUFFIX)] if name.endswith(DRONE_SUFFIX) else name
        atlas = "drone" if name.endswith(DRONE_SUFFIX) else "trailer"
        extra = {}
        if base in MATERIAL_MAP:
            tpl_name, color, extra = MATERIAL_MAP[base]
        else:
            rgb = [float(v) for v in (mat.get("diffuseColor") or "0.5 0.5 0.5 1").split()[:3]]
            metallic = float((mat.get("specularColor") or "0 0 0").split()[2])
            tpl_name, color = ("metalPainted" if metallic > 0.5 else "plasticPainted"), tuple(rgb)
        tpl = templates[tpl_name]
        for child in list(mat):
            mat.remove(child)
        for attr in ("specularColor", "customShaderVariation", "alphaBlending"):
            mat.attrib.pop(attr, None)
        mat.set("customShaderId", shader_id)
        mat.set("customShaderVariation", "vmaskUV2")
        scale = color if color is not None else tuple(float(v) for v in tpl.get("colorScale", "1 1 1").split())
        params = {"colorScale": "%g %g %g" % scale}
        for p in ("porosity", "smoothnessScale", "metalnessScale", "clearCoatIntensity", "clearCoatSmoothness"):
            if p in tpl:
                params[p] = tpl[p]
        params.update(extra)
        for p in sorted(params):
            ET.SubElement(mat, "CustomParameter", name=p, value=params[p])
        for m in ("detailDiffuse", "detailNormal", "detailSpecular"):
            ET.SubElement(mat, "Custommap", name=m, fileId=file_id(tpl[m]))
        maps = dict(BASE_MAPS, Glossmap=VMASK[atlas])
        if base in DECAL_MATERIALS:
            maps["Texture"] = DECAL_TEXTURE
        for tag, fname in maps.items():
            ET.SubElement(mat, tag, fileId=file_id(fname))
        used[name] = tpl_name
    referenced = {el.get(a) for el in root.iter() if el.tag != "File"
                  for a in ("fileId", "customShaderId", "referenceId") if el.get(a)}
    for f in list(files):
        if f.get("fileId") not in referenced:
            files.remove(f)
    tree.write(path, xml_declaration=True, encoding="iso-8859-1", method="xml")
    return used


def ladder_values(car):
    dcc = importlib.import_module("io_export_i3d_reworked.dcc.dccBlender")
    _, _, length = car["ladder_geometry"]()
    hinge_y, hinge_z = car["LADDER_HINGE_Y"], car["LADDER_HINGE_Z"]
    angle = car["ladder_fold_angle"]()

    def i3d_rot(m):
        e = dcc.bakeTransformMatrix(m).to_euler("XYZ")
        return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))

    jx, jy, jz = car["JOCKEY_X"], car["JOCKEY_Y"], car["DRAWBAR_Z"]
    return {
        "JOCKEY_DOWN": fmt(b2i((jx, jy, jz))),
        "JOCKEY_UP": fmt(b2i((jx, jy, jz + car["JOCKEY_LIFT"]))),
        "SLIDE_DEPLOYED": fmt(b2i((0, hinge_y, hinge_z))),
        "SLIDE_STOWED": fmt(b2i((0, hinge_y - length, hinge_z))),
        "HINGE_DEPLOYED": fmt(i3d_rot(Matrix.Identity(4))),
        "HINGE_STOWED": fmt(i3d_rot(Matrix.Rotation(angle, 4, "X"))),
        "LID_OPEN": fmt(i3d_rot(bpy.data.objects["chargerLid"].matrix_local.to_quaternion().to_matrix().to_4x4())),
        "LID_START": "%g" % car["CHEST_LID_TIME"][0],
        "LID_END": "%g" % car["CHEST_LID_TIME"][1],
        "CABLE_START": "%g" % car["CHEST_CABLE_TIME"][0],
        "CABLE_END": "%g" % car["CHEST_CABLE_TIME"][1],
    }


def clamp_parts_xml(car):
    """Úchyty lyžin dronu v animaci foldLadder: z otevřené polohy (stav v i3d) do zavřené."""
    dcc = importlib.import_module("io_export_i3d_reworked.dcc.dccBlender")
    t0, t1 = car["CLAMP_TIME"]
    out = []
    for prefix in car["DRONE_VARIANTS"].values():
        for i in range(1, 5):
            hinge = bpy.data.objects[f"{prefix}ClampHinge_{i}"]
            rot = hinge.matrix_local.to_quaternion().to_matrix().to_4x4()
            e = dcc.bakeTransformMatrix(rot).to_euler("XYZ")
            opened = fmt((math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)))
            out.append(f'            <part node="{hinge.name}" startTime="{t0:g}" endTime="{t1:g}" startRot="{opened}" '
                       f'endRot="0 0 0"/>')
    return "\n".join(out)


def vehicle_size(car):
    coll = bpy.data.collections[car["COLLECTION_NAME"]]
    mn, mx = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in coll.objects:
        if o.type == "MESH" and not o.get("i3D_nonRenderable") and not o.name.startswith(tuple(car["DRONE_VARIANTS"].values())):
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                mn, mx = Vector(map(min, mn, w)), Vector(map(max, mx, w))
    return {
        "SIZE_WIDTH": "%.2f" % (mx.x - mn.x),
        "SIZE_LENGTH": "%.2f" % (mx.y - mn.y),
        "SIZE_HEIGHT": "%.2f" % (mx.z - mn.z),
        "SIZE_LENGTH_OFFSET": "%.2f" % (-(mn.y + mx.y) / 2),
        "BEND_MIN_Z": "%.2f" % car["BASE_Y0"],
        "BEND_MAX_Z": "%.2f" % car["BASE_Y1"],
    }


def wheels_xml(car):
    out = []
    for repr_node, is_left in WHEEL_ORDER:
        rim = "0|0" if is_left else "0|1"
        out.append(
            f'                    <wheel dimensions="{car["TIRE_DIMENSIONS"]}" isLeft="{str(is_left).lower()}" '
            f'hasTireTracks="true" hasParticles="true" rimOffset="0.02">\n'
            f'                        <physics tipOcclusionAreaGroupId="1" restLoad="0.2" repr="{repr_node}" '
            f'forcePointRatio="0.3" initialCompression="10" suspTravel="0.10" spring="15" damper="30" '
            f'frictionScale="2.8"/>\n'
            f'                        <outerRim filename="$data/shared/wheels/rims/stema/rim001.i3d" node="{rim}" '
            f'widthAndDiam="7.5 13.5"/>\n'
            f'                    </wheel>')
    return "\n".join(out)


def write_vehicle_xml(car, mappings):
    values = {"WHEELS": wheels_xml(car), "I3D_MAPPINGS": mappings, "ATTACHER_HEIGHT": "%.2f" % car["COUPLER_Z"],
              "CLAMP_PARTS": clamp_parts_xml(car)}
    for key, prefix in car["DRONE_VARIANTS"].items():
        values[f"DRONE_PARTS_{key}"] = drone_parts_xml(car, prefix)
    values["DRONE_PARTS"] = values["DRONE_PARTS_M"]   # starý zástupce, dokud ho šablona má
    values.update(ladder_values(car))
    values.update(vehicle_size(car))
    text = open(TEMPLATE, encoding="utf-8").read()
    for k, v in values.items():
        if "{{" + k + "}}" not in text:
            if k.startswith("DRONE_PARTS"):
                print(f"VAROVÁNÍ: zástupce {{{{{k}}}}} v šabloně není")
            continue
        text = text.replace("{{" + k + "}}", v)
    left = sorted(set(re.findall(r"\{\{(\w+)\}\}", text)))
    if left:
        raise RuntimeError(f"v šabloně zůstal nevyplněný zástupce: {left}")
    ET.fromstring(text.encode("utf-8"))
    with open(XML_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return values


def png2dds(src, dst, fmt, *extra):
    """Převod přes tools/png2dds.py (Pillow) v systémovém Pythonu; Python Blenderu Pillow nemá."""
    exe = shutil.which("python") or shutil.which("py")
    if exe is None or os.path.dirname(exe).lower().startswith(os.path.dirname(bpy.app.binary_path).lower()):
        raise RuntimeError("chybí systémový python s Pillow pro převod na DDS")
    cmd = [exe, os.path.join(PROJECT, "tools", "png2dds.py"), src, dst, "--format", fmt, *extra]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"png2dds selhal: {r.stderr[-1500:]}")
    return dst


def _math(tree, op, a, b=None, clamp=False):
    n = tree.nodes.new("ShaderNodeMath")
    n.label = "_sdt_bake"
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            tree.links.new(v, n.inputs[i])
    return n.outputs[0]


def _bake_nodes(mat, drone):
    """Emise = vmask: R škrábance (hrany z bevel uzlu + skvrny), G AO, B špína (dutiny, výška nad zemí, šum).
    Dron se špiní méně a hlavně zespodu (letí nad polem, na zem sedá jen lyžinami)."""
    t = mat.node_tree
    nodes = []

    def new(kind):
        n = t.nodes.new(kind)
        n.label = "_sdt_bake"
        nodes.append(n)
        return n

    geo = new("ShaderNodeNewGeometry")
    ao = new("ShaderNodeAmbientOcclusion")
    ao.samples = 16
    ao.inputs["Distance"].default_value = 0.3
    bevel = new("ShaderNodeBevel")
    bevel.samples = 8
    bevel.inputs["Radius"].default_value = 0.012
    dot = new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    t.links.new(bevel.outputs["Normal"], dot.inputs[0])
    t.links.new(geo.outputs["Normal"], dot.inputs[1])
    pos = new("ShaderNodeSeparateXYZ")
    t.links.new(geo.outputs["Position"], pos.inputs[0])
    nrm = new("ShaderNodeSeparateXYZ")
    t.links.new(geo.outputs["Normal"], nrm.inputs[0])
    noise = new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.5
    noise.inputs["Detail"].default_value = 3.0
    t.links.new(geo.outputs["Position"], noise.inputs["Vector"])
    spots = new("ShaderNodeTexNoise")
    spots.inputs["Scale"].default_value = 9.0
    spots.inputs["Detail"].default_value = 2.0
    t.links.new(geo.outputs["Position"], spots.inputs["Vector"])

    a = ao.outputs["AO"]
    cavity = _math(t, "SUBTRACT", 1.0, a)
    n_rnd = _math(t, "SUBTRACT", noise.outputs["Fac"], 0.5)
    edge = _math(t, "MULTIPLY", _math(t, "SUBTRACT", 1.0, dot.outputs["Value"]), 6.0, clamp=True)
    spot = _math(t, "MAXIMUM", _math(t, "SUBTRACT", spots.outputs["Fac"], 0.55), 0.0)
    scratch = _math(t, "ADD", _math(t, "MULTIPLY", edge, 0.85), _math(t, "MULTIPLY", spot, 0.8), clamp=True)
    if drone:
        below = _math(t, "MAXIMUM", _math(t, "MULTIPLY", nrm.outputs["Z"], -1.0), 0.0)
        dirt = _math(t, "ADD", _math(t, "MULTIPLY", cavity, 0.5), _math(t, "MULTIPLY", below, 0.4))
        dirt = _math(t, "ADD", dirt, _math(t, "MULTIPLY", n_rnd, 0.4))
        dirt = _math(t, "MULTIPLY", _math(t, "ADD", dirt, 0.15), 0.6, clamp=True)
        scratch = _math(t, "MULTIPLY", scratch, 0.8)
    else:
        low = _math(t, "SUBTRACT", 1.0, _math(t, "DIVIDE", pos.outputs["Z"], 2.6), clamp=True)
        up = _math(t, "MAXIMUM", nrm.outputs["Z"], 0.0)
        dirt = _math(t, "ADD", _math(t, "MULTIPLY", cavity, 0.55), _math(t, "MULTIPLY", low, 0.45))
        dirt = _math(t, "ADD", dirt, _math(t, "MULTIPLY", n_rnd, 0.5))
        dirt = _math(t, "ADD", _math(t, "ADD", dirt, _math(t, "MULTIPLY", up, 0.12)), 0.1, clamp=True)
    g = _math(t, "ADD", _math(t, "MULTIPLY", a, 0.65), 0.35)
    rgb = new("ShaderNodeCombineColor")
    t.links.new(scratch, rgb.inputs[0])
    t.links.new(g, rgb.inputs[1])
    t.links.new(dirt, rgb.inputs[2])
    emit = new("ShaderNodeEmission")
    t.links.new(rgb.outputs[0], emit.inputs["Color"])
    out = next(n for n in t.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
    old = [l.from_socket for l in out.inputs["Surface"].links]
    t.links.new(emit.outputs[0], out.inputs["Surface"])
    img = new("ShaderNodeTexImage")
    uvn = new("ShaderNodeUVMap")
    uvn.uv_map = "DirtUV"
    t.links.new(uvn.outputs["UV"], img.inputs["Vector"])
    for n in t.nodes:
        n.select = n == img
    t.nodes.active = img
    return img, out, old


def _restore_material(mat, out, old):
    t = mat.node_tree
    for n in [n for n in t.nodes if n.label == "_sdt_bake"]:
        t.nodes.remove(n)
    for s in old:
        t.links.new(s, out.inputs["Surface"])


def bake_groups(car):
    """Průchody bake: každá skupina se peče samotná (ostatní meshe skryté pro render), aby AO nedělaly díly,
    které se hýbou nebo jsou jen v jiné variantě (drony, baterie tří velikostí ve stejných slotech, hadice)."""
    meshes = car["dirt_meshes"]()
    passes = {}
    for o in meshes:
        atlas = car["dirt_atlas"](o)
        if atlas == "drone":
            key = ("drone", next(k for k, p in car["DRONE_VARIANTS"].items() if o.name.startswith(p)))
        elif re.match(r"^battery\d[SML]$", o.name):
            key = ("trailer", "battery" + o.name[-1])
        elif re.match(r"^(fillHoseSeg\d+|HoseNozzle_\w+)$", o.name):
            key = ("trailer", "hose")
        else:
            key = ("trailer", "static")
        passes.setdefault(key, []).append(o)
    return meshes, passes


def bake_vmasks(car):
    """Upeče vmask obou atlasů do PNG (out/mod_build) a převede je na DDS do textures/ (DXT1, mipmapy)."""
    import numpy as np
    sc = bpy.context.scene
    meshes, passes = bake_groups(car)
    renderable = [o for o in bpy.data.objects if o.type == "MESH"]
    saved_hide = {o.name: o.hide_render for o in renderable}
    engine = sc.render.engine
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 8
    sc.render.bake.margin = 6
    mats = {}
    for o in meshes:
        for m in o.data.materials:
            if m is not None and m.name not in mats:
                img, out, old = _bake_nodes(m, m.name.endswith(DRONE_SUFFIX))
                mats[m.name] = (m, img, out, old)
    results = {}
    try:
        for (atlas, tag), objs in sorted(passes.items()):
            size = VMASK_SIZE[atlas]
            target = bpy.data.images.new(f"_sdt_vmask_{atlas}_{tag}", size, size, alpha=True)
            target.colorspace_settings.name = "Non-Color"
            target.pixels.foreach_set(np.zeros(size * size * 4, dtype=np.float32))
            for m, img, _, _ in mats.values():
                img.image = target
            names = {o.name for o in objs}
            for o in renderable:
                o.hide_render = o.name not in names
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            for o in objs:
                o.hide_set(False)
                o.select_set(True)
                o.data.uv_layers.active_index = 1
            bpy.context.view_layer.objects.active = objs[0]
            bpy.ops.object.bake(type="EMIT", margin=6, use_clear=False)
            for o in objs:
                o.data.uv_layers.active_index = 0
            px = np.empty(size * size * 4, dtype=np.float32)
            target.pixels.foreach_get(px)
            results.setdefault(atlas, []).append(px.reshape(size, size, 4))
            bpy.data.images.remove(target)
            print(f"vmask {atlas}/{tag}: {len(objs)} meshů")
    finally:
        for m, img, out, old in mats.values():
            _restore_material(m, out, old)
        for o in renderable:
            o.hide_render = saved_hide[o.name]
        sc.render.engine = engine
    os.makedirs(SHOT_DIR, exist_ok=True)
    os.makedirs(TEX_DIR, exist_ok=True)
    for atlas, layers in results.items():
        size = VMASK_SIZE[atlas]
        acc = np.zeros((size, size, 4), dtype=np.float32)
        acc[..., 1] = 1.0
        acc[..., 3] = 1.0
        for px in layers:
            mask = px[..., 3] > 0.5
            acc[mask, :3] = px[mask, :3]
        final = bpy.data.images.new(f"_sdt_vmask_{atlas}", size, size, alpha=False)
        final.colorspace_settings.name = "Non-Color"
        final.pixels.foreach_set(acc.ravel())
        png = os.path.join(SHOT_DIR, f"sdt_vmask_{atlas}.png")
        final.filepath_raw = png
        final.file_format = "PNG"
        final.save()
        bpy.data.images.remove(final)
        png2dds(png, os.path.join(VEH_DIR, VMASK[atlas]), "dxt1", "--linear")
        print(f"vmask {atlas}: {png} -> {VMASK[atlas]}")


STORE_VIEW_DIR = Vector((0.62, -0.72, 0.34))    # pohled zepředu zleva mírně shora jako vanilla obrázky obchodu
STORE_RES = 1024


def _store_pose(car):
    """Vlek složený (žebřík zasunutý, úchyty zavřené, ležící hadice skrytá), střední dron složený, S a L skryté.
    Vrací funkci, která stav vrátí."""
    prefix = car["DRONE_VARIANTS"]["M"]
    others = tuple(p for k, p in car["DRONE_VARIANTS"].items() if k != "M")
    parts = car["drone_fold_parts"](prefix)
    car["set_drone_unfold"](0.0, parts, prefix)
    car["set_ladder"](1.0)
    hinges = [o for o in bpy.data.objects if o.name.startswith(prefix + "ClampHinge_")]
    opened = {o.name: o.rotation_euler.y for o in hinges}
    for o in hinges:
        o.rotation_euler.y = 0.0
    hidden = {}
    for o in bpy.data.objects:
        hide = (o.name.startswith(others) or bool(o.get("i3D_nonRenderable"))
                or re.match(r"^battery\d[SL]$", o.name) is not None
                or re.match(r"^(fillHoseSeg\d+|HoseNozzle_\w+)$", o.name) is not None)
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
        car["set_ladder"](0.0)
    return restore


def _fit_camera(cam, objs, direction, margin=0.06):
    """Kamera ve směru direction od středu soupravy, vzdálenost a posun tak, aby obrys vyplnil snímek."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    center = sum(pts, Vector()) / len(pts)
    d = direction.normalized()
    cam.data.shift_x = cam.data.shift_y = 0.0
    lo, hi = 2.0, 60.0
    for _ in range(30):
        dist = (lo + hi) / 2
        cam.location = center + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        ps = [world_to_camera_view(sc, cam, p) for p in pts]
        xs, ys = [p.x for p in ps], [p.y for p in ps]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        if span > 1 - 2 * margin:
            lo = dist
        else:
            hi = dist
    ps = [world_to_camera_view(sc, cam, p) for p in pts]
    xs, ys = [p.x for p in ps], [p.y for p in ps]
    cam.data.shift_x = ((max(xs) + min(xs)) / 2 - 0.5)
    cam.data.shift_y = ((max(ys) + min(ys)) / 2 - 0.5)


def make_images(car):
    """Obrázek do obchodu (512) a ikona módu (256) z renderu EEVEE bez okna: průhledné pozadí, studiové světlo,
    střední dron složený na vleku s nabíječkou. DDS nekomprimované A8R8G8B8 s alfou (jako dřív, bez mipmap)."""
    sc = bpy.context.scene
    os.makedirs(SHOT_DIR, exist_ok=True)
    restore = _store_pose(car)
    state = (sc.render.engine, sc.render.film_transparent, sc.render.resolution_x, sc.render.resolution_y,
             sc.render.resolution_percentage, sc.camera, sc.world, sc.render.filepath)
    made = []
    exposure = sc.view_settings.exposure
    try:
        sc.view_settings.exposure = 0.5
        try:
            sc.render.engine = "BLENDER_EEVEE"
        except TypeError:
            sc.render.engine = "BLENDER_EEVEE_NEXT"
        sc.render.film_transparent = True
        sc.render.resolution_x = sc.render.resolution_y = STORE_RES
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA"
        world = bpy.data.worlds.new("_sdt_store_world")
        world.use_nodes = True
        bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
        bg.inputs[0].default_value = (0.8, 0.82, 0.86, 1.0)
        bg.inputs[1].default_value = 0.9
        sc.world = world
        made.append(world)
        lights = []
        for name, kind, energy, rot in (("_sdt_key", "SUN", 3.2, (0.75, 0.15, -0.55)),
                                        ("_sdt_fill", "SUN", 1.0, (1.1, -0.2, 2.4))):
            data = bpy.data.lights.new(name, kind)
            data.energy = energy
            data.angle = 0.2
            ob = bpy.data.objects.new(name, data)
            ob.rotation_euler = rot
            sc.collection.objects.link(ob)
            lights.append(ob)
        cd = bpy.data.cameras.new("_sdt_store_cam")
        cd.lens = 70
        cd.clip_start = 0.1
        cam = bpy.data.objects.new("_sdt_store_cam", cd)
        sc.collection.objects.link(cam)
        sc.camera = cam
        objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.hide_render
                and not any(c.name.startswith("REF_") for c in o.users_collection)]
        _fit_camera(cam, objs, STORE_VIEW_DIR)
        shot = os.path.join(SHOT_DIR, "store_shot.png")
        sc.render.filepath = shot
        bpy.ops.render.render(write_still=True)
        png2dds(shot, STORE_DDS, "rgba", "--no-mips", "--size", "512")
        png2dds(shot, ICON_DDS, "rgba", "--no-mips", "--size", "256")
        print(f"obrázek do obchodu: {shot} -> {STORE_DDS}, ikona {ICON_DDS}")
    finally:
        (sc.render.engine, sc.render.film_transparent, sc.render.resolution_x, sc.render.resolution_y,
         sc.render.resolution_percentage, sc.camera, sc.world, sc.render.filepath) = state
        sc.view_settings.exposure = exposure
        for ob in [o for o in bpy.data.objects if o.name.startswith(("_sdt_key", "_sdt_fill", "_sdt_store_cam"))]:
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if isinstance(data, bpy.types.Light):
                bpy.data.lights.remove(data)
            elif isinstance(data, bpy.types.Camera):
                bpy.data.cameras.remove(data)
        for w in made:
            bpy.data.worlds.remove(w)
        restore()


def build_mod():
    car = load_car_module()
    if "--no-bake" not in sys.argv:
        bake_vmasks(car)
    n = export_i3d(car)
    used = apply_vehicle_shader(I3D_PATH)
    print(f"materiály na vehicleShader: {len(used)} ({sorted(set(used.values()))})")
    hide_nodes(I3D_PATH, hidden_nodes(car))
    mappings, found = i3d_mappings(I3D_PATH, MAPPED_NODES + drone_nodes(car))
    values = write_vehicle_xml(car, mappings)
    make_images(car)
    print(f"i3d: {n} uzlů | mapování: {len(found)} | žebřík: {values['SLIDE_STOWED']} -> {values['SLIDE_DEPLOYED']}, "
          f"{values['HINGE_STOWED']} -> {values['HINGE_DEPLOYED']}")
    print(f"rozměry: {values['SIZE_WIDTH']} x {values['SIZE_LENGTH']} x {values['SIZE_HEIGHT']} m, "
          f"lengthOffset {values['SIZE_LENGTH_OFFSET']}")
    for f in sorted(os.listdir(VEH_DIR)) + [os.path.basename(ICON_DDS)]:
        p = os.path.join(VEH_DIR, f) if os.path.exists(os.path.join(VEH_DIR, f)) else ICON_DDS
        print(f"  {f}: {os.path.getsize(p):,} B")


if __name__ == "__main__":
    build_mod()
