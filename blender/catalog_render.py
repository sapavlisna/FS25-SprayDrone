"""Obrazový katalog modelů módu: postaví model do prázdné scény (stejné build skripty a knihovna dílů jako export),
nastaví stavy (složeno / rozloženo), izoluje položky a vyrenderuje je ze všech stran (EEVEE, neutrální studio).
mod/ ani uložené .blend v blender/ se nemění. Spouští ho tools/katalog.py, ručně:

    blender.exe -b --factory-startup --python blender\\catalog_render.py -- <úloha> <výstupní složka> [dump]

Úlohy: mini, middle, max, mill, pump, hopper, limebag, canisters, relay, tablet. Výstup: img/<id>_<pohled>.jpg
a data/<úloha>.json (položky, pohledy, měřítko ortho pohledů, trojúhelníky, objekty, materiály a obrázky, rozměry, uzly).
"""

import json
import math
import os
import re
import sys

import addon_utils
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Katalog ukazuje snímky z GIANTS Editoru (out/ge, viz tools/ge_plan.py); Blender renderuje jen stavy, které v GE nejdou nafotit
# (rozložený stav vzniká ve hře animací skriptu)
FALLBACK_STATES = ("rozlozeny",)
RES = (1280, 800)
SAMPLES = 16
# pohledy: jméno, popis, směr od modelu ke kameře (Blender: vpředu -Y, vlevo +X), ortografický
VIEWS = [
    ("iso1", "izometrie zepředu zleva", Vector((0.62, -0.78, 0.42)), False),
    ("iso2", "izometrie zezadu zprava", Vector((-0.62, 0.78, 0.42)), False),
    ("front", "zepředu", Vector((0, -1, 0)), True),
    ("rear", "zezadu", Vector((0, 1, 0)), True),
    ("left", "zleva", Vector((1, 0, 0)), True),
    ("right", "zprava", Vector((-1, 0, 0)), True),
    ("top", "shora", Vector((0, 0, 1)), True),
    ("bottom", "zespodu", Vector((0, 0, -1)), True),
]
DETAIL_DIR = Vector((0.55, -0.70, 0.45))


def run(name, ns_name="catalog_mod"):
    p = os.path.join(HERE, name)
    ns = {"__file__": p, "__name__": ns_name}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    return ns


# ------------------------------------------------------------------------------------------------ scéna a render
def setup_render():
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.eevee.taa_render_samples = SAMPLES
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 86
    world = bpy.data.worlds.new("_kat_w")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.50, 0.51, 0.53, 1.0)
    bg.inputs[1].default_value = 0.9
    sc.world = world
    for name, energy, rot in (("_kat_key", 3.0, (math.radians(50), 0, math.radians(-35))),
                              ("_kat_fill", 1.1, (math.radians(65), 0, math.radians(140))),
                              ("_kat_rim", 1.6, (math.radians(-60), 0, math.radians(200)))):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(8)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        sc.collection.objects.link(lo)
    cd = bpy.data.cameras.new("_kat_cam")
    cd.clip_start = 0.01
    cd.clip_end = 500
    cam = bpy.data.objects.new("_kat_cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


def alive(o):
    try:
        o.name
        return True
    except ReferenceError:
        return False


HOSE_NODE = re.compile(r"(HoseSeg\d+|HoseEnd|StrainerEnd|HoseNozzle)$", re.IGNORECASE)


def renderable(o):
    """Články a koncovky tažných hadic ve hře ukazuje skript jen u vytažené hadice, v modelu leží složené v počátku."""
    if o.type not in ("MESH", "CURVE") or HOSE_NODE.search(o.name):
        return False
    if o.get("i3D_nonRenderable") or o.get("i3D_collision") or o.get("i3D_trigger"):
        return False
    if any(c.name.startswith("REF_") for c in o.users_collection):
        return False
    return True


def base_hidden():
    """Skrytí podle stavu modelu (hide_render po stavbě a pózování); kolize, triggery a reference vždy."""
    return {o.name: (o.hide_render or not renderable(o)) for o in bpy.data.objects}


def isolate(objs, hidden):
    keep = {o.name for o in objs}
    for o in bpy.data.objects:
        if o.type in ("MESH", "CURVE"):
            o.hide_render = hidden.get(o.name, True) or o.name not in keep
        elif o.type == "LIGHT" and not o.name.startswith("_kat_"):
            o.hide_render = True
    bpy.context.view_layer.update()
    return [o for o in objs if not o.hide_render]


def points(objs):
    pts = []
    for o in objs:
        pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    return pts


def fit(cam, objs, direction, ortho, margin=0.05):
    sc = bpy.context.scene
    pts = points(objs)
    lo_v = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi_v = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo_v + hi_v) / 2
    radius = max((hi_v - lo_v).length / 2, 0.05)
    d = direction.normalized()
    cam.data.shift_x = cam.data.shift_y = 0.0
    if ortho:
        cam.data.type = "ORTHO"
        cam.location = center + d * (radius * 4 + 2)
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        if abs(d.z) > 0.99:
            cam.rotation_euler = (0, 0, math.pi) if d.z > 0 else (math.pi, 0, 0)
        bpy.context.view_layer.update()
        inv = cam.matrix_world.inverted()
        loc = [inv @ p for p in pts]
        xs, ys = [p.x for p in loc], [p.y for p in loc]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        aspect = sc.render.resolution_x / sc.render.resolution_y
        scale = max(w, h * aspect) * (1 + 2 * margin)
        cam.data.ortho_scale = scale
        cam.data.shift_x = ((max(xs) + min(xs)) / 2) / scale
        cam.data.shift_y = ((max(ys) + min(ys)) / 2) / scale
        cam.data.clip_end = radius * 10 + 10
        return scale / sc.render.resolution_x
    cam.data.type = "PERSP"
    cam.data.lens = 50
    lo, hi = 0.05, max(radius * 20, 5.0)
    for _ in range(28):
        dist = (lo + hi) / 2
        cam.location = center + d * dist
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        ps = [world_to_camera_view(sc, cam, p) for p in pts]
        if min(p.z for p in ps) <= 0.01:
            lo = dist
            continue
        xs, ys = [p.x for p in ps], [p.y for p in ps]
        if max(max(xs) - min(xs), max(ys) - min(ys)) > 1 - 2 * margin:
            lo = dist
        else:
            hi = dist
    cam.location = center + d * hi
    bpy.context.view_layer.update()
    ps = [world_to_camera_view(sc, cam, p) for p in pts]
    xs, ys = [p.x for p in ps], [p.y for p in ps]
    cam.data.shift_x = ((max(xs) + min(xs)) / 2 - 0.5)
    cam.data.shift_y = ((max(ys) + min(ys)) / 2 - 0.5) * sc.render.resolution_y / sc.render.resolution_x
    cam.data.clip_end = hi + radius * 4 + 10
    return None


def shoot(cam, path):
    if os.environ.get("KAT_NORENDER"):
        return
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def stats(objs):
    deps = bpy.context.evaluated_depsgraph_get()
    tris = 0
    mats, images = set(), set()
    for o in objs:
        ev = o.evaluated_get(deps)
        try:
            me = ev.to_mesh()
        except RuntimeError:
            continue
        if me is not None:
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
            ev.to_mesh_clear()
        for slot in o.material_slots:
            m = slot.material
            if m is None:
                continue
            mats.add(re.sub(r"\.\d{3}$", "", m.name))
            if m.node_tree is not None:
                for n in m.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and n.image is not None:
                        images.add(os.path.basename(n.image.filepath or n.image.name))
    pts = points(objs)
    size = [round(max(p[i] for p in pts) - min(p[i] for p in pts), 3) for i in range(3)]
    lo = [round(min(p[i] for p in pts), 4) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
    return {"tris": tris, "objects": len(objs), "materials": sorted(mats), "images": sorted(images),
            "size": {"w": size[0], "l": size[1], "h": size[2]}, "bbox": [lo, hi]}


def save_points(out, key, objs, limit=6000):
    """Vzorek světových vrcholů viditelných objektů (Blender souřadnice) do data/pts/<key>.npy pro záběr kamery v GE; vzorek
    obsahuje i krajní vrcholy ve 200 směrech, takže rozsah v libovolném pohledu sedí."""
    import numpy as np
    chunks = []
    for o in objs:
        if o.type != "MESH" or not len(o.data.vertices):
            continue
        n = len(o.data.vertices)
        a = np.empty(n * 3)
        o.data.vertices.foreach_get("co", a)
        m = np.array(o.matrix_world)
        chunks.append(a.reshape(n, 3) @ m[:3, :3].T + m[:3, 3])
    pts = np.concatenate(chunks)
    rng = np.random.default_rng(1)
    dirs = rng.normal(size=(200, 3))
    ext = pts[np.unique((pts @ dirs.T).argmax(axis=0))]
    if len(pts) > limit:
        pts = pts[rng.choice(len(pts), limit, replace=False)]
    pts = np.concatenate([pts, ext]).astype(np.float32)
    d = os.path.join(out, "data", "pts")
    os.makedirs(d, exist_ok=True)
    np.save(os.path.join(d, key + ".npy"), pts)
    return f"data/pts/{key}.npy"


class Catalog:
    def __init__(self, job, out):
        self.job, self.out = job, out
        self.items = []
        self.calls = []
        os.makedirs(os.path.join(out, "img"), exist_ok=True)
        os.makedirs(os.path.join(out, "data"), exist_ok=True)
        self.cam = None

    def ensure_setup(self):
        try:
            self.cam.name
        except (AttributeError, ReferenceError):
            self.sc, self.cam = setup_render()

    def item(self, iid, title, category, objs, hidden, state=None, note=None, views=VIEWS, extra=None):
        self.ensure_setup()
        objs = isolate(objs, hidden)
        if not objs:
            print(f"KATALOG: {iid} bez viditelných objektů, přeskočeno")
            return None
        entry = next((e for e in self.items if e["id"] == iid), None)
        if entry is None:
            entry = {"id": iid, "title": title, "category": category, "job": self.job, "states": [], "note": note}
            entry.update(stats(objs))
            entry["objectNames"] = sorted({o.name for o in objs} | set((extra or {}).pop("nodeNames", [])))
            entry["visibleNames"] = sorted(o.name for o in objs)
            entry["pts"] = save_points(self.out, iid, objs)
            if extra:
                entry.update(extra)
            self.items.append(entry)
        shots = []
        for name, label, direction, ortho in (views if (state or "") in FALLBACK_STATES else ()):
            fn = f"{iid}{'_' + re.sub(r'[^A-Za-z0-9]+', '', state) if state else ''}_{name}.jpg"
            mpp = fit(self.cam, objs, direction, ortho)
            shoot(self.cam, os.path.join(self.out, "img", fn))
            shots.append({"file": fn, "view": name, "label": label, "ortho": ortho, "mpp": mpp, "source": "blender"})
        entry["states"].append({"state": state or "", "shots": shots})
        return entry

    def save(self):
        with open(os.path.join(self.out, "data", f"{self.job}.json"), "w", encoding="utf-8") as fh:
            json.dump({"job": self.job, "items": self.items, "calls": self.calls}, fh, ensure_ascii=False, indent=1)


def descendants(root):
    out = [root]
    for c in root.children:
        out += descendants(c)
    return out


def ancestors(o):
    out = []
    while o.parent is not None:
        o = o.parent
        out.append(o)
    return out


def with_children(names):
    out = []
    for n in names:
        o = bpy.data.objects.get(n)
        if o is not None:
            out += descendants(o)
    return out


# ------------------------------------------------------------------------------------------------ vleky
TRAILERS = {
    "mini": ("build_trailer_mini.py", "export_mini_mod.py", "Mini"),
    "middle": ("build_trailer_middle.py", "export_middle_mod.py", "Middle"),
    "max": ("build_trailer_max.py", "export_max_mod.py", "Max"),
}
def trailer_job(cat, key):
    build_file, export_file, label = TRAILERS[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    car = run(build_file)
    car["build"]()
    exp = run(export_file, "catalog_exp")
    if "DRONE_B_KEYS" in exp:
        car["DRONE_VARIANTS"] = {**car["DRONE_VARIANTS"], **exp["DRONE_B_KEYS"]}
    for o in bpy.data.objects:
        if any(c.name.endswith("_Preview") for c in o.users_collection):
            o.hide_render = False
    saved_rot = {o.name: o.rotation_euler.copy() for o in bpy.data.objects
                 if o.name.startswith("padClampHinge") or o.name in ("chargerLid", "hoseLidHinge", "hoseLidHingeB")}
    variants = dict(car["DRONE_VARIANTS"])
    variants.update({k + "2": v for k, v in car.get("DRONE_VARIANTS_B", {}).items()})
    restore = exp["_store_pose"](car)
    shown = [p for p in variants.values()
             if any(o.name.startswith(p) and not o.hide_render for o in bpy.data.objects if o.type == "MESH")]
    hidden = base_hidden()
    trailer_objs = [o for o in bpy.data.objects if renderable(o)]
    cat.item(f"trailer_{key}", f"Vlek {label}", "vleky", trailer_objs, hidden, state="slozeny",
             note="Stav jako obrázek do obchodu: žebřík a drony složené, výchozí konfigurace.")
    # rozložený stav
    for prefix in (shown if key != "mini" else ()):
        parts = car["drone_fold_parts"](prefix)
        car["set_drone_unfold"](1.0, parts, prefix)
    car["set_ladder"](0.0)
    P = car.get("P")
    for o in list(bpy.data.objects):
        roll = bpy.data.objects.get(o.name + "Roll")
        if roll is not None and o.name.startswith("tarp") and P is not None:
            P.tarp_preview(o, roll, 0.0)
    for name, rot in saved_rot.items():
        bpy.data.objects[name].rotation_euler = rot
    door = bpy.data.objects.get("Toolbox_Door")
    if door is not None:
        door.matrix_world = Matrix.Translation((0, 0, 0.30)) @ door.matrix_world
    bpy.context.view_layer.update()
    hidden_u = dict(hidden)
    for n in ("chargerCable", "Charger_Plug", "Gen_0_ChargePlug"):
        if n in hidden_u and bpy.data.objects[n].type == "MESH":
            hidden_u[n] = False
    note = ("Bednu s dronem rozkládá až skript ve hře (SprayDronePad); v Blenderu je bedna složená, rozložený stav ukazuje "
            "otevřené víko šachty baterií a zapojený kabel.") if key == "mini" else None
    entry = cat.item(f"trailer_{key}", f"Vlek {label}", "vleky", trailer_objs, hidden_u, state="rozlozeny")
    if note and entry is not None:
        entry["note"] = (entry.get("note") or "") + " " + note
    restore()
    return car, variants, shown, hidden


def drones_and_batteries(cat, car, variants):
    """Drony S, M, L izolovaně ze scény Middle (všechny varianty v ní jsou), složené i rozložené, a baterie."""
    hidden = base_hidden()
    for key in ("S", "M", "L"):
        prefix = variants.get(key)
        if prefix is None:
            continue
        objs = [o for o in bpy.data.objects if o.name.startswith(prefix) and renderable(o)]
        h = {n: (v and not n.startswith(prefix)) for n, v in hidden.items()}
        for o in objs:
            h[o.name] = bool(o.get("i3D_nonRenderable"))
        parts = car["drone_fold_parts"](prefix)
        spec = car["drone_spec"](prefix)
        car["set_drone_unfold"](0.0, parts, prefix)
        nodes = [o.name for o in bpy.data.objects if o.name.startswith(prefix)]
        cat.item(f"drone_{key}", f"Dron {key}", "drony", objs, h, state="slozeny", extra={"nodeNames": nodes})
        car["set_drone_unfold"](1.0, parts, prefix)
        cat.item(f"drone_{key}", f"Dron {key}", "drony", objs, h, state="rozlozeny",
                 note="Varianty dronu jsou uzly vleku (konfigurace), na plošině se přepínají viditelností.")
        car["set_drone_unfold"](0.0, parts, prefix)
    for key in ("S", "M", "L"):
        bat = sorted((o for o in bpy.data.objects if re.match(rf"^battery\d+{key}$", o.name)), key=lambda o: o.name)
        if not bat:
            continue
        objs = [o for o in descendants(bat[0]) if renderable(o)]
        h = {o.name: bool(o.get("i3D_nonRenderable")) for o in objs}
        cat.item(f"battery_{key}", f"Baterie {key}", "vybavení", objs, h,
                 note="Baterie je uzel vleku (šachta nabíječky / dron), velikost podle dronu.")


USAGE_JOBS = {"mini": "Mini", "middle": "Middle", "max": "Max", "mill": "Mlýnek", "pump": "Přenosná pumpa", "hopper": "Násypka"}


def place_text(p):
    if not p:
        return "bez posunu"
    out = [f"poloha ({p['t'][0]:.2f}; {p['t'][1]:.2f}; {p['t'][2]:.2f}) m"]
    if abs(p["rot_z"]) > 0.05:
        out.append(f"otočeno o {p['rot_z']:+.0f}° kolem svislé osy")
    if p["mirror"]:
        out.append("zrcadlově")
    return ", ".join(out)


def load_part(blend):
    """Díl z knihovny v prázdné scéně (lokální počátek); vrací objekty."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with open(blend[:-6] + ".json", encoding="utf-8") as fh:
        names = json.load(fh)["objects"]
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = list(names)
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    return list(dst.objects)


def doc_of(func):
    import importlib
    mod, name = func.split(".", 1)
    try:
        doc = getattr(importlib.import_module(mod), name).__doc__ or ""
    except Exception:
        return ""
    return " ".join(doc.split("\n\n")[0].split())


def dily_job(cat, out):
    """Položky knihovny dílů: jedna karta na díl, varianty jen skutečné rozdíly tvaru, u každé varianty kde a jak je použita.
    Nic se nerenderuje (snímky dílů dělá GIANTS Editor z i3d, které vyrobí blender/export_parts.py)."""
    import dily_info as DI
    import parts_lib as PL
    import sdt_parts as P
    bpy.ops.wm.read_factory_settings(use_empty=True)
    P.begin("SDT_Dily", "dily_root")
    DI.extras(PL)
    calls = [(None, c) for c in PL.stats["calls"]]
    for job, label in USAGE_JOBS.items():
        path = os.path.join(out, "data", f"{job}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                calls += [(label, c) for c in json.load(fh)["calls"]]
    parts = {}
    for label, c in calls:
        info = DI.describe(c)
        entry = parts.setdefault(info["id"], {"info": info, "variants": {}})
        var = entry["variants"].setdefault(info["variant"], {"label": info["variantLabel"], "file": c["file"], "uses": {}})
        if label is not None:
            var["uses"].setdefault(label, []).append(place_text(c.get("place")))
    for pid, entry in sorted(parts.items(), key=lambda kv: (DI.GROUPS.index(kv[1]["info"]["group"]), kv[0])):
        info = entry["info"]
        variants = []
        for slug, var in sorted(entry["variants"].items()):
            objs = load_part(os.path.join(PL.PARTS_DIR, var["file"]))
            subsets = [(slug, var["label"], objs)]
            sizes = sorted({int(m.group(1)) for o in objs for m in [re.match(r"^Tank_Main(\d+)", o.name)] if m})
            if len(sizes) > 1:
                subsets = []
                for size in sizes:
                    sub = [o for o in objs if re.match(rf"^(Tank_Main{size}(?!\d)|tankMain{size}$)", o.name)
                           or any(re.match(rf"^tankMain{size}$", a.name) for a in ancestors(o))]
                    subsets.append((f"{size}l", f"{size} l", sub))
            for sslug, slabel, sub in subsets:
                vis = [o for o in sub if renderable(o) and not o.hide_render]
                if not vis:
                    continue
                st = stats(vis)
                if len(entry["variants"]) == 1 and len(subsets) == 1:
                    sslug = ""
                key = pid + (f"__{sslug}" if sslug else "")
                variants.append({"slug": sslug, "label": slabel, "file": var["file"], **st, "pts": save_points(out, key, vis),
                                 "visibleNames": sorted(o.name for o in vis), "uses": var["uses"]})
        if not variants:
            continue
        used, seen = [], set()
        for slug, var in sorted(entry["variants"].items()):
            for label, places in var["uses"].items():
                if (label, var["file"]) in seen:
                    continue
                seen.add((label, var["file"]))
                used.append({"on": label, "variant": var["label"] if len(entry["variants"]) > 1 else "", "count": len(places),
                             "how": "; ".join(sorted(set(places)))})
        item = {"id": pid, "title": info["title"], "category": "díly", "group": info["group"], "job": "dily",
                "note": info.get("note") or doc_of(info["func"]), "func": info["func"], "variants": variants, "usedBy": used,
                "states": [{"state": v["label"] if len(variants) > 1 else "", "slug": v["slug"], "shots": []} for v in variants]}
        for k in ("tris", "objects", "materials", "images", "size", "bbox"):
            item[k] = variants[0][k]
        cat.items.append(item)


# ------------------------------------------------------------------------------------------------ objekty
def object_job(cat, key):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if "io_export_i3d_reworked" not in bpy.context.preferences.addons:
        try:
            addon_utils.enable("io_export_i3d_reworked", default_set=False)
        except Exception:
            pass
    items = []
    if key == "mill":
        car = run("build_trailer_mill.py")
        car["build"]()
        items.append(("mill", "Mlýnek na vápno", "vybavení"))
    elif key == "pump":
        run("build_pump.py")["build"]()
        items.append(("pump", "Přenosná pumpa", "vybavení"))
    elif key == "hopper":
        run("build_hopper.py")["build"]()
        items.append(("hopper", "Násypka na vápno", "vybavení"))
    elif key == "limebag":
        ns = run("build_limebag.py")
        ns["configure"](50)
        ns["build"]()
        items.append(("limebag50", "Pytel vápna 50 l", "vybavení"))
    elif key == "relay":
        run("build_link_items.py")["build_relay"]()
        items.append(("relay", "Relé tyč", "vybavení"))
    elif key == "tablet":
        run("build_link_items.py")["build_tablet"]()
        items.append(("tablet", "Tablet", "vybavení"))
    elif key == "canisters":
        ns = run("build_canister.py")
        for kind, cfg in ns["KINDS"].items():
            bpy.ops.wm.read_factory_settings(use_empty=True)
            ns = run("build_canister.py")
            ns["build_kind"](kind, ns["KINDS"][kind])
            hidden = {o.name: (not renderable(o)) for o in bpy.data.objects}
            label = {"Fertilizer": "hnojivo", "Herbicide": "herbicid", "Diesel": "nafta"}.get(kind, kind)
            cat.item(f"canister_{kind}", f"Kanystr – {label}", "vybavení", [o for o in bpy.data.objects if renderable(o)], hidden)
        return
    for iid, title, category in items:
        for o in bpy.data.objects:
            if any(c.name.endswith("_Preview") for c in o.users_collection):
                o.hide_render = False
        hidden = base_hidden()
        cat.item(iid, title, category, [o for o in bpy.data.objects if renderable(o)], hidden)


def dump():
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if True:
            print("OBJ", o.type, o.name, "parent=" + (o.parent.name if o.parent else "-"), "hide=" + str(o.hide_render))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    job, out = args[0], args[1]
    cat = Catalog(job, out)
    if job == "dily":
        dily_job(cat, out)
    elif job in TRAILERS:
        car, variants, shown, hidden = trailer_job(cat, job)
        if "dump" in args:
            dump()
        if job == "middle":
            drones_and_batteries(cat, car, variants)
    else:
        object_job(cat, job)
        if "dump" in args:
            dump()
    if job != "dily":
        import parts_lib as PL
        cat.calls = PL.stats["calls"]
    cat.save()
    print("KATALOG HOTOVO", job, len(cat.items))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
