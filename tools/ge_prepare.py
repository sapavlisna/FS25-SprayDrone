"""Příprava modelů pro foto v GIANTS Editoru: pro každou položku katalogu (vozidla a objekty z módu) vyrobí v tmp/ge/models kopii i3d,
ve které jsou skryté všechny tvary, které katalog neukazuje (kolize, triggery, varianty mimo výchozí konfiguraci, jiné drony),
a seznam položek tmp/ge/items.json (jméno, i3d, rozsah a vzorek vrcholů pro záběr kamery).

    python tools/ge_prepare.py

Originál v mod/ se nemění: kopie má cesty k texturám absolutní a .shapes je s ní spojený pevným odkazem (žádné kopírování 25 MB).
Vstup: out/katalog/data/<úloha>.json (úlohy catalog_render.py; položka nese visibleNames = tvary, které katalog renderuje).
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import katalog  # noqa: E402

MOD = katalog.MOD
DATA = os.path.join(ROOT, "out", "katalog", "data")
MODELS = os.path.join(ROOT, "tmp", "ge", "models")
GE = os.path.join(ROOT, "tmp", "ge")


# články a koncovky tažných hadic: ve hře je skript ukazuje jen u vytažené hadice, v i3d leží složené v počátku
HOSE_NODE = re.compile(r"(HoseSeg\d+|HoseEnd|StrainerEnd|HoseNozzle)$", re.IGNORECASE)


def b2i(p):
    return [p[0], p[2], -p[1]]


def source_for(item):
    """Cesta k i3d v módu pro položku katalogu: vlastní, nebo vlek Middle pro drony a baterie."""
    iid = item["id"]
    if iid in katalog.SOURCES:
        return katalog.SOURCES[iid][0]
    if iid.startswith(("drone_", "battery_")):
        return katalog.SOURCES["trailer_middle"][0]
    return None


def prepare(item, src_rel):
    src = katalog.resolve_i3d(src_rel)
    tree = ET.parse(src)
    root = tree.getroot()
    parents = {}
    for p in root.iter():
        for c in p:
            parents[c] = p
    visible = {n for n in item["visibleNames"] if not HOSE_NODE.search(n)}
    shown = 0
    scene = root.find("Scene")
    for el in scene.iter():
        if el.tag == "Shape":
            if el.get("name") in visible:
                el.attrib.pop("visibility", None)
                shown += 1
                p = parents.get(el)
                while p is not None and p is not scene:
                    p.attrib.pop("visibility", None)
                    p = parents.get(p)
            else:
                el.set("visibility", "false")
            if el.get("name") in item.get("geMaterialIds", {}):
                el.set("materialIds", str(item["geMaterialIds"][el.get("name")]))
    files = root.find("Files")
    for f in files:
        name = f.get("filename")
        if name and not name.startswith("$"):
            f.set("filename", os.path.normpath(os.path.join(os.path.dirname(src), name)).replace("\\", "/"))
    folder = os.path.join(MODELS, item["id"])
    os.makedirs(folder, exist_ok=True)
    dst = os.path.join(folder, os.path.basename(src))      # .shapes se hledá podle jména i3d, proto zůstává původní jméno
    tree.write(dst, xml_declaration=True, encoding="iso-8859-1", method="xml")
    for ext in (".shapes",):
        d = dst + ext
        if os.path.exists(d):
            os.remove(d)
        os.link(src + ext, d)
    return dst, shown


def main():
    out = []
    groups = []
    for fn in sorted(os.listdir(DATA)):
        if fn.endswith(".json") and fn != "dily.json":
            with open(os.path.join(DATA, fn), encoding="utf-8") as fh:
                groups.append(json.load(fh)["items"])
    if os.path.exists(katalog.VANILLA):
        with open(katalog.VANILLA, encoding="utf-8") as fh:
            groups.append(json.load(fh))
    for items in groups:
        for item in items:
            if "visibleNames" not in item:
                continue
            rel = source_for(item)
            if rel is None:
                print("bez i3d:", item["id"])
                continue
            dst, shown = prepare(item, rel)
            lo, hi = item["bbox"]
            a, b = b2i(lo), b2i(hi)
            out.append({"id": item["id"], "name": item["id"], "i3d": dst.replace("\\", "/"), "title": item["title"],
                        "bbox": [[min(a[i], b[i]) for i in range(3)], [max(a[i], b[i]) for i in range(3)]], "pts": item.get("pts"),
                        "shown": shown, "wanted": len(item["visibleNames"])})
            print(f"{item['id']}: {shown} z {len(item['visibleNames'])} tvarů viditelných")
    with open(os.path.join(GE, "items.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(len(out), "položek")


if __name__ == "__main__":
    main()
