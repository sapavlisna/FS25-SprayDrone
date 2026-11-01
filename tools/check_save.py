"""Jen ČTE savegame: porovná konfigurace vleků módu v vehicles.xml s tím, co vozidlové XML módu nabízí.

    python tools/check_save.py [slot=12 | cesta/k/vehicles.xml]

Hlídá: vozidlo odkazuje na XML, které v módu není (po přejmenování / smazání), id konfigurace, které XML nezná
(kola `DEFAULT_<ZNAČKA>_<MODEL>` se ověřují proti wheels.xml hry, ostatní proti saveId), počet fillUnitů proti konfiguraci
nádrží. Exit 1 při jakémkoli nesouladu. Nic nezapisuje.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD_NAME = "FS25_SprayDroneTrailer"
MOD = os.path.join(PROJECT, "mod", MOD_NAME)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender"))
import sdt_paths  # noqa: E402

GAME = sdt_paths.GAME_DIR
DOCS = os.path.join(os.path.expanduser("~"), "Documents", "My Games", "FarmingSimulator2025")


def load_wheel_defaults():
    """{(basename tire xml, kategorie): {DEFAULT_ZNAČKA_MODEL, ...}} z wheels.xml hry."""
    path = os.path.join(GAME, "data", "shared", "wheels", "wheels.xml")
    result = {}
    for el in ET.parse(path).getroot().iter("wheel"):
        f = el.get("filename", "")
        m = re.search(r"/tires/([^/]+)/([^/]+)/([^/]+)\.xml$", f)
        if m:
            brand, model, dim = m.groups()
            result.setdefault((dim, el.get("category")), set()).add(f"DEFAULT_{brand}_{model}".upper())
    return result


def wheel_ids(root, defaults):
    block = root.find("wheels/wheelConfigurations")
    ids = set()
    if block is None:
        return ids
    categories = (block.get("tireCategories") or "").split()
    for conf in block.findall("wheelConfiguration"):
        sid = conf.get("saveId")
        if sid:
            ids.add(sid.upper())
        if sid == "DEFAULT":
            for w in conf.iter("wheel"):
                for cat in categories or [None]:
                    ids |= defaults.get((w.get("dimensions"), cat), set())
    return ids


def config_ids(root, name, defaults):
    if name == "wheel":
        return wheel_ids(root, defaults), None
    block = root.find(f".//{name}Configurations")
    if block is None:
        return None, None
    children = list(block)
    ids = {c.get("saveId").upper() for c in children if c.get("saveId")}
    if not ids:
        ids = {str(i + 1) for i in range(len(children))}
    if block.get("useDefaultColors") == "true":
        ids |= brand_colors()
    return ids, children


def brand_colors():
    """Vanilla barvy, které nabídka s useDefaultColors přidá za vlastní (saveId = jméno šablony, např. RABE_BLUE1)."""
    path = os.path.join(GAME, "data", "shared", "brandMaterialTemplates.xml")
    return {t.get("name").upper() for t in ET.parse(path).getroot().iter("template") if t.get("name")}


def fill_unit_count(children, sid):
    for c in children or []:
        if (c.get("saveId") or "").upper() == sid.upper():
            return len(c.findall("fillUnits/fillUnit"))
    return None


def main():
    slot = sys.argv[1] if len(sys.argv) > 1 else "12"
    path = slot if slot.lower().endswith(".xml") else os.path.join(DOCS, f"savegame{slot}", "vehicles.xml")
    if not os.path.exists(path):
        print(f"CHYBA  {path} neexistuje")
        return 1
    defaults = load_wheel_defaults()
    problems = []
    seen = 0
    for v in ET.parse(path).getroot().iter("vehicle"):
        if v.get("modName") != MOD_NAME:
            continue
        seen += 1
        rel = re.sub(r"^\$moddir\$" + MOD_NAME + "/", "", v.get("filename", ""))
        label = f"{os.path.basename(rel)} ({v.get('uniqueId', '')[:14]})"
        xml_path = os.path.join(MOD, rel)
        if not os.path.exists(xml_path):
            problems.append(f"{label}: XML vozidla v módu není ({rel}) — vlek se nenačte")
            continue
        root = ET.parse(xml_path).getroot()
        fill_children = None
        for conf in v.findall("configuration"):
            if conf.get("isActive") == "false":
                continue
            name, cid = conf.get("name"), conf.get("id") or ""
            ids, children = config_ids(root, name, defaults)
            if ids is None:
                continue
            if cid.upper() not in ids:
                problems.append(f"{label}: konfigurace {name} id=\"{cid}\" XML nezná (nabízí: {', '.join(sorted(ids)[:6])}{' …' if len(ids) > 6 else ''})")
            if name == "fillUnit":
                fill_children = (children, cid)
        units = len(v.findall("fillUnit/unit"))
        if fill_children and units:
            expected = fill_unit_count(*fill_children)
            if expected is not None and expected != units:
                problems.append(f"{label}: v savu {units} fillUnitů, konfigurace {fill_children[1]} jich má {expected}")
    print(f"{path}: vleků módu {seen}")
    for p in problems:
        print("CHYBA ", p)
    if not problems:
        print("OK    konfigurace vleků sedí s XML módu")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
