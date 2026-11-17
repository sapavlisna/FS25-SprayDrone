"""Knihovna dílů: funkce dílu (např. sdt_generator.build_generator) se zavolá v samostatném procesu Blenderu, díl se uloží
do blender/parts/<modul>.<funkce>_<klíč>.blend a sestavení vleku si ho jen připojí. Výsledek je stejný jako přímé volání
ve vleku: díl se staví na svém místě (UV kvádrů a zaokrouhlení vrcholů závisí na světové poloze), parametry i návratová
hodnota se přenášejí bezztrátově (Vector, Matrix, tuple, dict s libovolnými klíči, objekty podle jména).

Díl je čistá funkce parametrů, která ho staví v lokálním počátku; do vleku se jen umístí (Place: posun, otočení, případně
zrcadlení). Parametry dílu jsou jen to, v čem se díl opravdu liší (varianta, objem), ne poloha. Cache: soubor = funkce +
parametry + verze Blenderu; platnost hlídá .json vedle .blend se sha1 zdrojů modulu dílu a všech
modulů z blender/, které importuje (i nepřímo), a s hodnotami jejich modulových konstant v okamžiku volání (Max a Mini
konstanty modulů nádrží přepisují). Když sestavení v některém z těch modulů nahradilo funkci, díl se postaví přímo ve vleku.

    PL.call(G.build_generator, rear_socket=True, at=PL.Place.at(x, y, z))   # díl se postaví jednou v lokálním počátku
    PL.Place(matrix, mirror_x=True)                          # umístění: zrcadlení podle x (nápisy zůstanou čitelné) a matice
    SDT_PARTS=0                                              # vypne knihovnu, všechno se staví přímo
    blender.exe -b --python blender/parts_lib.py -- preview <.blend> <.png>
"""

import ast
import hashlib
import importlib
import json
import math
import os
import subprocess
import sys
import time
import types

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS_DIR = os.path.join(HERE, "parts")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

ENABLED = os.environ.get("SDT_PARTS", "1") != "0"
# modulové konstanty s polohou dílu ve vleku: díl je čte jen funkce skládající vlek (poloha je teď Place), takže nesmí měnit
# platnost cache (Max je přepisuje, jinak by se díl při každém přepnutí vleku stavěl znovu)
POSITION_CONSTANTS = {"sdt_tanks": {"PUMP_XY", "INDUCTION_XY"}}
stats = {"built": 0, "cached": 0, "inline": 0, "build_s": 0.0, "load_s": 0.0, "parts": [], "calls": []}


# ------------------------------------------------------------------------------------------------ bezztrátový přenos hodnot
def encode(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, Vector):
        return {"__v": [float(c) for c in v]}
    if isinstance(v, Matrix):
        return {"__m": [[float(c) for c in row] for row in v]}
    if isinstance(v, bpy.types.Object):
        return {"__o": v.name}
    if isinstance(v, tuple):
        return {"__t": [encode(x) for x in v]}
    if isinstance(v, list):
        return [encode(x) for x in v]
    if isinstance(v, dict):
        return {"__d": [[encode(k), encode(x)] for k, x in v.items()]}
    raise TypeError(type(v).__name__)


def decode(v, objects=None):
    if isinstance(v, list):
        return [decode(x, objects) for x in v]
    if not isinstance(v, dict):
        return v
    if "__v" in v:
        return Vector(v["__v"])
    if "__m" in v:
        return Matrix(v["__m"])
    if "__o" in v:
        return objects[v["__o"]] if objects is not None else v["__o"]
    if "__t" in v:
        return tuple(decode(x, objects) for x in v["__t"])
    return {decode(k, objects): decode(x, objects) for k, x in v["__d"]}


def _constant(v):
    """Hodnota modulové konstanty pro přenos, nebo None (funkce, moduly, objekty, generátory…)."""
    if isinstance(v, (types.ModuleType, types.FunctionType, type, bpy.types.ID)):
        return None
    try:
        return encode(v)
    except TypeError:
        return None


# ------------------------------------------------------------------------------------------------ závislosti modulů
_ast_cache = {}


def _parse(path):
    st = os.stat(path).st_mtime_ns
    hit = _ast_cache.get(path)
    if hit is None or hit[0] != st:
        tree = ast.parse(open(path, encoding="utf-8").read())
        imports = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports.update(a.name.split(".")[0] for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
                imports.add(n.module.split(".")[0])
        defs = {n.name: n.lineno for n in tree.body if isinstance(n, ast.FunctionDef)}
        hit = (st, imports, defs)
        _ast_cache[path] = hit
    return hit


def deps(module_name):
    """Moduly z blender/, které modul dílu importuje (i nepřímo), včetně něj samotného."""
    out, todo = set(), [module_name]
    while todo:
        name = todo.pop()
        path = os.path.join(HERE, name + ".py")
        if name in out or not os.path.exists(path):
            continue
        out.add(name)
        todo.extend(_parse(path)[1])
    return sorted(out)


def patched_functions(mod):
    """Funkce modulu, které sestavení za běhu nahradilo jinou (jiný soubor nebo řádek než ve zdroji modulu)."""
    path = os.path.abspath(mod.__file__)
    out = []
    for name, line in _parse(path)[2].items():
        code = getattr(getattr(mod, name, None), "__code__", None)
        if code is None or os.path.abspath(code.co_filename) != path or code.co_firstlineno != line:
            out.append(name)
    return out


def file_sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()



# ------------------------------------------------------------------------------------------------ umístění dílu
class Place:
    """Umístění dílu ve vleku: nejdřív se díl případně zrcadlí podle roviny x = 0 (zrcadlí se i UV každé plochy, takže nálepky
    a nápisy zůstanou čitelné), potom se použije matice."""

    def __init__(self, matrix=None, mirror_x=False):
        self.matrix = Matrix.Identity(4) if matrix is None else Matrix(matrix)
        self.mirror_x = mirror_x

    @staticmethod
    def at(x=0.0, y=0.0, z=0.0, rot_z=0.0, mirror_x=False):
        m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot_z, 4, "Z")
        return Place(m, mirror_x)

    def describe(self):
        """Umístění pro katalog: posun, otočení kolem svislé osy ve stupních a zrcadlení."""
        m = self.matrix
        return {"t": [round(c, 3) for c in m.translation], "rot_z": round(math.degrees(math.atan2(m[1][0], m[0][0])), 1),
                "mirror": self.mirror_x}

    def point(self, v):
        v = Vector(v)
        if self.mirror_x:
            v = Vector((-v.x, v.y, v.z))
        return self.matrix @ v


def _mirror_mesh(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    for layer in bm.loops.layers.uv.values():
        for f in bm.faces:
            us = [l[layer].uv.x for l in f.loops]
            lo, hi = min(us), max(us)
            for l in f.loops:
                l[layer].uv.x = lo + hi - l[layer].uv.x
    bm.to_mesh(me)
    bm.free()
    me.update()


_MX = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))


def _transform_top(o, pl):
    """Použije umístění na objekt bez rodiče (potomci jdou s ním). Mesh s jednotkovou maticí (sloučené díly) se přepíše do
    vrcholů, ostatní dostanou matici; zrcadlení se vždy zapíše do vrcholů."""
    basis = o.matrix_basis.copy()
    if o.type == "MESH" and (pl.mirror_x or basis == Matrix.Identity(4)) and not o.children:
        if pl.mirror_x:
            o.data.transform(_MX @ basis)
            _mirror_mesh(o.data)
            o.data.transform(pl.matrix)
        else:
            o.data.transform(pl.matrix)
        o.matrix_basis = Matrix.Identity(4)
        return
    if pl.mirror_x:
        if o.type == "MESH" or o.children:
            raise NotImplementedError(f"zrcadlení objektu {o.name} s potomky")
        o.matrix_basis = pl.matrix @ _MX @ basis @ _MX
    else:
        o.matrix_basis = pl.matrix @ basis


def join_meshes(name, objs):
    """Spojí meshe do jednoho objektu pod kořenem vleku (počátek v počátku scény, materiály jako sloty v pořadí prvního použití,
    plochy v pořadí objektů); původní objekty smaže. Vrací nový objekt."""
    import sdt_parts as P
    bm = bmesh.new()
    mats = []
    for o in objs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        remap = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        n = len(bm.faces)
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n:]:
            f.material_index = remap[f.material_index]
        bpy.data.meshes.remove(me)
    for o in objs:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(data)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    P._coll.objects.link(obj)
    obj.parent = P._root
    obj.matrix_world = Matrix.Identity(4)
    return obj


def localize(anchor):
    """Pro funkci dílu: posune všechno, co právě postavila, o -anchor, takže díl leží ve svém lokálním počátku; do vleku se pak
    umístí Place.at(*anchor). Volá se na konci funkce dílu (poloha uvnitř dílu se tím nemění)."""
    import sdt_parts as P
    pl = Place.at(-anchor[0], -anchor[1], -anchor[2])
    bpy.context.view_layer.update()
    for o in list(P._coll.objects):
        if o is not P._root and o.parent is P._root:
            _transform_top(o, pl)
    bpy.context.view_layer.update()


def _xf_value(v, pl):
    if isinstance(v, Vector):
        return pl.point(v)
    if isinstance(v, tuple):
        return tuple(_xf_value(x, pl) for x in v)
    if isinstance(v, list):
        return [_xf_value(x, pl) for x in v]
    if isinstance(v, dict):
        return {k: _xf_value(x, pl) for k, x in v.items()}
    return v


def _rename(objs, rename):
    for o in objs:
        old = o.name
        new = rename(_base_name(old))
        if new != old:
            if o.data is not None and o.data.name == old:
                o.data.name = new
            o.name = new

# ------------------------------------------------------------------------------------------------ stavba dílu (podproces)
def build_part(request_path, out):
    """Podproces: nastaví konstanty modulů jako ve vleku, zavolá funkci dílu v prázdné scéně a uloží jen jeho objekty;
    do .json zapíše výsledek, pořadí objektů v kolekci a objekty, které visely na kořeni."""
    with open(request_path, encoding="utf-8") as fh:
        req = json.load(fh)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mod = importlib.import_module(req["module"])
    for name, consts in req["constants"].items():
        target = sys.modules.get(name) or importlib.import_module(name)
        for k, v in consts.items():
            setattr(target, k, decode(v))
    P = importlib.import_module("sdt_parts")
    P.begin("SDT_Part", "sdt_part_root")
    root = P._root
    result = getattr(mod, req["function"])(*decode(req["args"]), **decode(req["kwargs"]))
    bpy.context.view_layer.update()
    objs = [o for o in P._coll.objects if o is not root]
    under_root = [o.name for o in objs if o.parent is root]
    for o in objs:
        if o.parent is root:
            basis = o.matrix_basis.copy()
            o.parent = None
            o.matrix_basis = basis
    bpy.data.objects.remove(root, do_unlink=True)
    meta = {
        "result": encode(result),
        "objects": [o.name for o in objs],
        "under_root": under_root,
        "sources": req["sources"],
        "constants": req["constants"],
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        os.remove(out)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=False)
    with open(out[:-6] + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh)


# ------------------------------------------------------------------------------------------------ sestavení (proces vleku)
def module_of(fn):
    """Jméno modulu z blender/, ve kterém funkce leží; skripty se spouštějí i přes exec pod jiným jménem (headless, katalog),
    takže se bere ze souboru funkce."""
    path = fn.__code__.co_filename
    if os.path.dirname(os.path.abspath(path)) == HERE:
        return os.path.splitext(os.path.basename(path))[0]
    return fn.__module__


def _request(fn, args, kwargs, names):
    consts = {}
    for n in names:
        mod = sys.modules.get(n)
        if mod is None:
            continue
        skip = POSITION_CONSTANTS.get(n, ())
        c = {k: e for k, v in vars(mod).items() if not k.startswith("__") and k not in skip for e in (_constant(v),) if e is not None}
        consts[n] = c
    sources = {n + ".py": file_sha(os.path.join(HERE, n + ".py")) for n in names}
    sources["parts_lib.py"] = file_sha(os.path.abspath(__file__))
    return {"module": module_of(fn), "function": fn.__name__, "args": encode(tuple(args)), "kwargs": encode(dict(kwargs)),
            "constants": consts, "sources": sources}


def _path(req):
    h = hashlib.sha1()
    h.update(json.dumps([req["module"], req["function"], req["args"], req["kwargs"], bpy.app.version_string],
                        sort_keys=True).encode())
    return os.path.join(PARTS_DIR, f"{req['module']}.{req['function']}_{h.hexdigest()[:16]}.blend")


def ensure(req):
    """Cesta k .blend dílu a jeho metadata; chybí-li nebo zastaral, postaví ho v samostatném Blenderu."""
    path = _path(req)
    meta_path = path[:-6] + ".json"
    if os.path.exists(path) and os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
        if meta["sources"] == req["sources"] and meta["constants"] == req["constants"]:
            stats["cached"] += 1
            return path, meta, False
    t = time.perf_counter()
    os.makedirs(PARTS_DIR, exist_ok=True)
    req_path = path[:-6] + ".request.json"
    with open(req_path, "w", encoding="utf-8") as fh:
        json.dump(req, fh)
    cmd = [bpy.app.binary_path, "-b", "--factory-startup", "--python", os.path.abspath(__file__), "--", "build",
           req_path, path]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    os.remove(req_path)
    if r.returncode != 0 or not os.path.exists(meta_path):
        raise RuntimeError(f"díl {req['module']}.{req['function']} se nepostavil:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    stats["built"] += 1
    stats["build_s"] += time.perf_counter() - t
    with open(meta_path, encoding="utf-8") as fh:
        return path, json.load(fh), True


def _base_name(name):
    return name.rsplit(".", 1)[0] if len(name) > 4 and name[-4] == "." and name[-3:].isdigit() else name


def place(path, meta, at=None, rename=None):
    """Připojí objekty dílu do kolekce vleku ve stejném pořadí, použije umístění at (Place), objekty z kořene dílu dá pod kořen
    vleku, materiály s příponou .001 nahradí stávajícími podle jména. rename(jméno) -> jméno přejmenuje objekty a jejich data
    (díl se staví s výchozími jmény, vlek si je může přidělit podle místa). Vrací {jméno ve stavbě dílu: objekt}."""
    import sdt_parts as P
    t = time.perf_counter()
    names = meta["objects"]
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(names)
    mapping = dict(zip(names, dst.objects))
    under_root = set(meta["under_root"])
    if at is not None:
        for n in names:
            if mapping[n].parent is None:
                _transform_top(mapping[n], at)
    for n in names:
        o = mapping[n]
        P._coll.objects.link(o)
        if n in under_root:
            basis = o.matrix_basis.copy()
            o.parent = P._root
            o.matrix_parent_inverse = Matrix.Identity(4)
            o.matrix_basis = basis
        for slot in o.material_slots:
            mat = slot.material
            base = _base_name(mat.name) if mat is not None else None
            if base is not None and base != mat.name and base in bpy.data.materials:
                slot.material = bpy.data.materials[base]
    if rename is not None:
        _rename(list(mapping.values()), rename)
    for m in [m for m in bpy.data.materials if m.users == 0]:
        bpy.data.materials.remove(m)
    for img in [i for i in bpy.data.images if i.users == 0]:
        bpy.data.images.remove(img)
    bpy.context.view_layer.update()
    stats["load_s"] += time.perf_counter() - t
    return mapping


def call(fn, *args, at=None, rename=None, **kwargs):
    """Zavolá funkci dílu přes cache (nebo přímo, když je knihovna vypnutá nebo nejde použít) a umístí ji (at = Place);
    vrací totéž co fn, polohy (Vector) už po umístění."""
    module = module_of(fn)
    name = f"{module}.{fn.__name__}"
    names = deps(module)
    blocking = {n: p for n in names if n in sys.modules for p in (patched_functions(sys.modules[n]),) if p}
    if not ENABLED or blocking:
        import sdt_parts as P
        stats["inline"] += 1
        stats["parts"].append((name, "přímo" + (f", přepsané funkce {blocking}" if blocking else "")))
        stats["calls"].append({"func": name, "file": None, "args": encode(tuple(args)), "kwargs": encode(dict(kwargs)),
                                "place": at.describe() if at is not None else None})
        before = {o.name for o in P._coll.objects}
        result = fn(*args, **kwargs)
        new = [o for o in P._coll.objects if o.name not in before]
        if at is not None:
            bpy.context.view_layer.update()
            for o in new:
                if o.parent is None or o.parent is P._root:
                    _transform_top(o, at)
        if rename is not None:
            _rename(new, rename)
        bpy.context.view_layer.update()
        return result if at is None else _xf_value(result, at)
    req = _request(fn, args, kwargs, names)
    path, meta, built = ensure(req)
    mapping = place(path, meta, at, rename)
    stats["parts"].append((name, "postaven" if built else "z cache"))
    stats["calls"].append({"func": name, "file": os.path.basename(path), "args": req["args"], "kwargs": req["kwargs"],
                          "place": at.describe() if at is not None else None})
    result = decode(meta["result"], mapping)
    return result if at is None else _xf_value(result, at)


def report():
    return (f"díly: postaveno {stats['built']} ({stats['build_s']:.1f} s), z cache {stats['cached']}, přímo {stats['inline']}, "
            f"připojení {stats['load_s']:.2f} s")


# ------------------------------------------------------------------------------------------------ náhled
def preview(blend, png, size=640):
    """Náhled dílu (Cycles na CPU, ať nebere GPU): pohled zepředu zleva shora na celý díl."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with open(blend[:-6] + ".json", encoding="utf-8") as fh:
        names = json.load(fh)["objects"]
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = list(names)
    sc = bpy.context.scene
    for o in dst.objects:
        sc.collection.objects.link(o)
    meshes = [o for o in sc.objects if o.type == "MESH"]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center, radius = (lo + hi) / 2, (hi - lo).length / 2
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 24
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("_part_w")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.55, 0.57, 0.60, 1.0)
    sc.world = world
    for name, energy, rot in (("_key", 3.0, (0.75, 0.15, -0.55)), ("_fill", 1.2, (1.1, -0.2, 2.4))):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        lo_ = bpy.data.objects.new(name, ld)
        lo_.rotation_euler = rot
        sc.collection.objects.link(lo_)
    cd = bpy.data.cameras.new("_cam")
    cd.lens = 50
    cam = bpy.data.objects.new("_cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    direction = Vector((0.62, -0.72, 0.40)).normalized()
    cam.location = center + direction * radius * 3.6
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = png
    os.makedirs(os.path.dirname(png), exist_ok=True)
    bpy.ops.render.render(write_still=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    if args[0] == "build":
        build_part(args[1], args[2])
    elif args[0] == "preview":
        preview(args[1], args[2])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
