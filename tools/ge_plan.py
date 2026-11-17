"""Plán snímků pro GIANTS Editor: z rozsahu modelu (bbox v souřadnicích i3d) spočítá pro každý pohled vzdálenost kamery tak, aby
model zabral ~70 % záběru, a vypíše řádky Lua pro funkci sdtItem (viz docs/NAVRH-dily.md, sekce Foto v GE).

    python tools/ge_plan.py            seznam všech položek a počet snímků
    python tools/ge_plan.py <id> ...   řádky Lua pro vybrané položky (po dvou čtveřicích pohledů)

Zdroje položek: tmp/ge/items.json (vozidla a objekty z módu, vyrábí tools/ge_prepare.py) a tmp/ge/parts/manifest.json (díly).
Souřadnice kamery: yaw 0 = pohled zepředu (kamera na +Z i3d), kladný yaw doleva (+X), pitch nahoru.
"""

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GE = os.path.join(ROOT, "tmp", "ge")
SHOTS = os.path.join(ROOT, "out", "ge")
FOV_Y = math.radians(60.0)
ASPECT = 1280 / 960
FILL = 0.74
FILL_ITEM = {"drone_M": 0.52}       # exportovaný dron M má víc vyložené listy než model v katalogu, jinak by se ořízl

# pohled: jméno, azimut, sklon (stupně)
VIEWS = [
    ("front", 0, 0), ("rear", 180, 0), ("left", 90, 0), ("right", 270, 0), ("top", 0, 90), ("bottom", 0, -90),
    ("iso1", 45, 30), ("iso2", 225, 30),
    ("t45a", 45, 45), ("t45b", 135, 45), ("t45c", 225, 45), ("t45d", 315, 45),
    ("b45a", 45, -45), ("b45b", 135, -45), ("b45c", 225, -45), ("b45d", 315, -45),
]
VIEW_LABELS = {
    "front": "zepředu", "rear": "zezadu", "left": "zleva", "right": "zprava", "top": "shora", "bottom": "zespodu",
    "iso1": "izometrie zepředu zleva", "iso2": "izometrie zezadu zprava",
    "t45a": "shora 45° zepředu zleva", "t45b": "shora 45° zezadu zleva", "t45c": "shora 45° zezadu zprava",
    "t45d": "shora 45° zepředu zprava",
    "b45a": "zespodu 45° zepředu zleva", "b45b": "zespodu 45° zezadu zleva", "b45c": "zespodu 45° zezadu zprava",
    "b45d": "zespodu 45° zepředu zprava",
}


def direction(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    return (math.sin(y) * math.cos(p), math.sin(p), math.cos(y) * math.cos(p))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(sum(c * c for c in a))
    return tuple(c / n for c in a)


def points_of(item):
    """Vzorek vrcholů položky v souřadnicích i3d (x, z, -y z Blenderu), nebo osm rohů bboxu, když vzorek chybí."""
    import numpy as np
    p = item.get("pts")
    if p:
        path = os.path.join(ROOT, "out", "katalog", p)
        if os.path.exists(path):
            a = np.load(path).astype(float)
            return np.stack([a[:, 0], a[:, 2], -a[:, 1]], axis=1)
    lo, hi = item["bbox"]
    return np.array([(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], dtype=float)


def center_of(pts):
    return (pts.min(axis=0) + pts.max(axis=0)) / 2


def fit_distance(pts, center, yaw, pitch, fill=FILL):
    """Vzdálenost od středu, při které největší odchylka vrcholů od osy záběru zabere `fill` poloviny záběru."""
    import numpy as np
    d = np.array(direction(yaw, pitch))
    f = -d
    up = np.array((0, 0, -1)) if abs(pitch) > 80 else np.array((0, 1, 0))
    right = np.cross(f, up)
    right /= np.linalg.norm(right)
    tup = np.cross(right, f)
    tx, ty = math.tan(FOV_Y / 2) * ASPECT, math.tan(FOV_Y / 2)
    r = pts - center
    rd, rr, ru = r @ d, np.abs(r @ right), np.abs(r @ tup)

    def extent(dist):
        depth = dist - rd
        if depth.min() <= 0.02:
            return 9.0
        return max((rr / (depth * tx)).max(), (ru / (depth * ty)).max())

    lo_d, hi_d = 0.05, 200.0
    for _ in range(60):
        mid = (lo_d + hi_d) / 2
        if extent(mid) > fill:
            lo_d = mid
        else:
            hi_d = mid
    return hi_d


def load_items():
    items = []
    p = os.path.join(GE, "items.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            items += json.load(fh)
    p = os.path.join(GE, "parts", "manifest.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            items += json.load(fh)
    return items


def lua_lines(item):
    """Řádky Lua pro sdtShots(jméno, cx, cy, cz, {pohled, azimut, sklon, vzdálenost}, ...) po čtveřicích pohledů."""
    pts = points_of(item)
    c = center_of(pts)
    out = []
    for k in range(0, len(VIEWS), 4):
        chunk = VIEWS[k:k + 4]
        args = ", ".join(f'{{"{n}", {yaw}, {pit}, {fit_distance(pts, c, yaw, pit, FILL_ITEM.get(item['name'], FILL)):.3f}}}' for n, yaw, pit in chunk)
        out.append(f'sdtShots("{item["name"]}", {c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f}, {args})')
    return out


def lua_chunk(item):
    """Celý kus Lua pro run_lua: načte i3d, nafotí 16 pohledů do out/ge a model smaže."""
    lines = [f'local n = sdtLoad("{item["i3d"]}")'] + lua_lines(item) + ["sdtDrop(n)"]
    return "\n".join(lines)


def main():
    items = load_items()
    args = sys.argv[1:]
    if args and args[0] == "--lua":
        print("\n".join(lua_chunk(it) for it in items if it["name"] in args[1:]))
        print('return "ok"')
        return
    if args and args[0] == "--batches":
        size = int(args[1])
        todo = [it for it in items if not all(os.path.exists(os.path.join(SHOTS, f"{it['name']}_{v[0]}.png")) for v in VIEWS)]
        if len(args) > 2:
            todo = [it for it in todo if it["name"].startswith(tuple(args[2:]))]
        for old in os.listdir(GE):
            if old.startswith("batch_") and old.endswith(".lua"):
                os.remove(os.path.join(GE, old))
        for k in range(0, len(todo), size):
            path = os.path.join(GE, f"batch_{k // size + 1:02d}.lua")
            names = [it["name"] for it in todo[k:k + size]]
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lua_chunk(it) for it in todo[k:k + size]) + '\nreturn "' + " ".join(names) + '"\n')
            print(path.replace("\\", "/"), names)
        return
    if args and args[0] == "--todo":
        for it in items:
            if not all(os.path.exists(os.path.join(SHOTS, f"{it['name']}_{v[0]}.png")) for v in VIEWS):
                print(it["name"])
        return
    want = args
    if not want:
        for it in items:
            print(it["name"], it["bbox"])
        print(len(items), "položek,", len(items) * len(VIEWS), "snímků")
        return
    for it in items:
        if it["name"] in want:
            print("\n".join(lua_lines(it)))


if __name__ == "__main__":
    main()
