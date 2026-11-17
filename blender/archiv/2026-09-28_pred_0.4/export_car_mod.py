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
import struct
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
    "ladderSlide", "ladderHinge", "jockeyWheel",
    "fillTrigger", "exactFillRootNode",
    "rearLight52_left", "rearLight52_right", "plateNumberLight03", "sideMarker05_left", "sideMarker05_right",
    "exitPoint", "outdoorCameraTarget", "outdoorCamera", "droneRoot",
    "occlusionAreaStart", "occlusionAreaWidth", "occlusionAreaHeight", "licensePlateBack",
]
SHADER = "$data/shaders/vehicleShader.xml"
TEMPLATES_XML = os.path.join(GAME_DIR, "data", "shared", "detailLibrary", "materialTemplates.xml")
BASE_MAPS = {"Texture": "$data/shared/white_diffuse.png", "Normalmap": "$data/shared/default_normal.png",
             "Glossmap": "$data/shared/default_vmask.png"}
# náš materiál -> (šablona z detailLibrary, colorScale nebo None = barva šablony)
MATERIAL_MAP = {
    "SDT_Frame": ("metalPainted", (0.02, 0.02, 0.022)),
    "SDT_DeckWood": ("wood1", (0.42, 0.28, 0.16)),
    "SDT_TopDeck": ("plasticPainted", (0.72, 0.72, 0.70)),
    "SDT_TankWhite": ("plasticPainted", (0.85, 0.85, 0.82)),
    "SDT_TankBlack": ("plasticPainted", (0.02, 0.02, 0.02)),
    "SDT_Rubber": ("rubber", (0.02, 0.02, 0.02)),
    "SDT_Rim": ("metalPainted", (0.03, 0.03, 0.03)),
    "SDT_GenOrange": ("metalPainted", (0.80, 0.30, 0.03)),
    "SDT_EngineRed": ("metalPainted", (0.55, 0.03, 0.03)),
    "SDT_TapeRed": ("plasticPainted", (0.70, 0.02, 0.02)),
    "SDT_TapeWhite": ("plasticPainted", (0.90, 0.90, 0.90)),
    "SDT_Mesh": ("metalPainted", (0.06, 0.06, 0.07)),
    "SDT_HoseBlue": ("rubber", (0.05, 0.20, 0.60)),
    "SDT_HoseBlack": ("rubber", (0.02, 0.02, 0.02)),
    "SDT_Steel": ("metalGalvanized", None),
    "SDT_LampRed": ("plasticPainted", (0.80, 0.02, 0.02)),
    "SDT_LampAmber": ("plasticPainted", (0.90, 0.45, 0.02)),
}
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
    s.i3D_exportLights = False
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
    area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
    region = next(r for r in area.regions if r.type == "WINDOW")
    log = io.StringIO()
    with contextlib.redirect_stdout(log), bpy.context.temp_override(area=area, region=region):
        exp.I3DExportSelected()
    for f in (I3D_PATH, I3D_PATH + ".shapes"):
        if not os.path.exists(f):
            raise RuntimeError(f"export nevytvořil {f}\n{log.getvalue()[-2000:]}")
    return len(tree)


def i3d_mappings(path):
    scene = ET.parse(path).getroot().find("Scene")
    found = {}

    def walk(node, comp_index, trail):
        for i, ch in enumerate(list(node)):
            name = ch.get("name")
            idx = trail + [i]
            if name in MAPPED_NODES:
                if name in found:
                    raise RuntimeError(f"uzel {name} je v i3d víckrát")
                found[name] = f"{comp_index}>" + "|".join(map(str, idx))
            walk(ch, comp_index, idx)

    for ci, comp in enumerate(list(scene)):
        if comp.get("name") in MAPPED_NODES:
            found[comp.get("name")] = f"{ci}>"
        walk(comp, ci, [])
    missing = [n for n in MAPPED_NODES if n not in found]
    if missing:
        raise RuntimeError(f"v i3d chybí uzly: {missing}")
    lines = ["    <i3dMappings>"]
    lines += [f'        <i3dMapping id="{n}" node="{found[n]}"/>' for n in MAPPED_NODES]
    lines.append("    </i3dMappings>")
    return "\n".join(lines), found


def load_templates():
    root = ET.parse(TEMPLATES_XML).getroot()
    return {t.get("name"): t.attrib for t in root.iter("template")}


def apply_vehicle_shader(path):
    """Přepíše materiály v hotovém i3d na vehicleShader s detailními texturami z knihovny hry.

    Stejné uspořádání jako vanilla díly bez vlastních textur: white_diffuse + default_normal +
    default_vmask, barva přes colorScale. Materiály, které nejsou v MATERIAL_MAP (dron), dostanou
    plast nebo kov podle metalické složky a barvu ze své diffuseColor.
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
        if name in MATERIAL_MAP:
            tpl_name, color = MATERIAL_MAP[name]
        else:
            rgb = [float(v) for v in (mat.get("diffuseColor") or "0.5 0.5 0.5 1").split()[:3]]
            metallic = float((mat.get("specularColor") or "0 0 0").split()[2])
            tpl_name, color = ("metalPainted" if metallic > 0.5 else "plasticPainted"), tuple(rgb)
        tpl = templates[tpl_name]
        for child in list(mat):
            mat.remove(child)
        for attr in ("specularColor", "customShaderVariation"):
            mat.attrib.pop(attr, None)
        mat.set("customShaderId", shader_id)
        scale = color if color is not None else tuple(float(v) for v in tpl.get("colorScale", "1 1 1").split())
        ET.SubElement(mat, "CustomParameter", name="colorScale", value="%g %g %g" % scale)
        for p in ("porosity", "smoothnessScale"):
            if p in tpl:
                ET.SubElement(mat, "CustomParameter", name=p, value=tpl[p])
        for m in ("detailDiffuse", "detailNormal", "detailSpecular"):
            ET.SubElement(mat, "Custommap", name=m, fileId=file_id(tpl[m]))
        for tag, fname in BASE_MAPS.items():
            ET.SubElement(mat, tag, fileId=file_id(fname))
        used[name] = tpl_name
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
    }


def vehicle_size(car):
    coll = bpy.data.collections[car["COLLECTION_NAME"]]
    mn, mx = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in coll.objects:
        if o.type == "MESH" and not o.get("i3D_nonRenderable"):
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
    values = {"WHEELS": wheels_xml(car), "I3D_MAPPINGS": mappings, "ATTACHER_HEIGHT": "%.2f" % car["COUPLER_Z"]}
    values.update(ladder_values(car))
    values.update(vehicle_size(car))
    text = open(TEMPLATE, encoding="utf-8").read()
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    if "{{" in text:
        raise RuntimeError("v šabloně zůstal nevyplněný zástupce")
    ET.fromstring(text.encode("utf-8"))
    with open(XML_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return values


def write_dds(path, image, size):
    """Nekomprimované DDS A8R8G8B8 (legacy hlavička), čtvercový výřez ze středu obrázku."""
    w, h = image.size
    side = min(w, h)
    x0, y0 = (w - side) // 2, (h - side) // 2
    px = list(image.pixels[:])
    crop = bpy.data.images.new("_sdt_crop", side, side, alpha=True)
    rows = []
    for y in range(y0, y0 + side):
        start = (y * w + x0) * 4
        rows.extend(px[start:start + side * 4])
    crop.pixels[:] = rows
    crop.scale(size, size)
    data = crop.pixels[:]
    bpy.data.images.remove(crop)
    body = bytearray(size * size * 4)
    for y in range(size):
        src = (size - 1 - y) * size * 4          # Blender ukládá odspodu, DDS odshora
        dst = y * size * 4
        for x in range(size):
            r, g, b, a = data[src + x * 4: src + x * 4 + 4]
            body[dst + x * 4: dst + x * 4 + 4] = bytes((int(b * 255 + 0.5), int(g * 255 + 0.5),
                                                        int(r * 255 + 0.5), 255))
    header = struct.pack("<4sIIIIIII44xIIIIIIIIIIIII", b"DDS ", 124, 0x100F, size, size, size * 4, 0, 1,
                         32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000, 0x1000, 0, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(header + bytes(body))


def make_images(car):
    os.makedirs(SHOT_DIR, exist_ok=True)
    area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
    region = next(r for r in area.regions if r.type == "WINDOW")
    sp = area.spaces.active
    hidden = []
    for cn in ("REF_StemaTrius", "REF_Belvedere"):
        c = bpy.data.collections.get(cn)
        if c and not c.hide_viewport:
            c.hide_viewport = True
            hidden.append(c)
    overlays = (sp.overlay.show_overlays, sp.shading.type)
    sp.overlay.show_overlays = False
    sp.shading.type = "SOLID"
    regions = {k: getattr(sp, k) for k in ("show_region_header", "show_region_toolbar", "show_region_ui",
                                           "show_region_tool_header", "show_gizmo")}
    for k in regions:
        setattr(sp, k, False)
    invisible = [o for o in bpy.data.collections[car["COLLECTION_NAME"]].objects
                 if o.get("i3D_nonRenderable") and not o.hide_get()]
    for o in invisible:
        o.hide_set(True)
    cam, target = Vector((5.6, -6.8, 3.4)), Vector((0, -0.4, 1.35))
    r3d = sp.region_3d
    r3d.view_perspective = "PERSP"
    d = target - cam
    r3d.view_rotation = d.to_track_quat("-Z", "Y")
    r3d.view_location = target
    r3d.view_distance = d.length
    car["set_ladder"](0.0)
    bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    shot = os.path.join(SHOT_DIR, "store_shot.png")
    with bpy.context.temp_override(area=area, region=region):
        bpy.ops.screen.screenshot_area(filepath=shot)
    sp.overlay.show_overlays, sp.shading.type = overlays
    for k, v in regions.items():
        setattr(sp, k, v)
    for o in invisible:
        o.hide_set(False)
    for c in hidden:
        c.hide_viewport = False
    img = bpy.data.images.load(shot, check_existing=False)
    write_dds(STORE_DDS, img, 512)
    write_dds(ICON_DDS, img, 256)
    bpy.data.images.remove(img)


def build_mod():
    car = load_car_module()
    n = export_i3d(car)
    used = apply_vehicle_shader(I3D_PATH)
    print(f"materiály na vehicleShader: {len(used)} ({sorted(set(used.values()))})")
    mappings, found = i3d_mappings(I3D_PATH)
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
