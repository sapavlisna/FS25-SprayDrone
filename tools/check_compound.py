"""Limit fyziky: kompound komponenty smí mít nejvýš 40 dětí VČETNĚ kolizních tvarů kol.

Hra jinak hlásí "Failed to create compound ... with N children. Maximum is 40" (vozidlo pak nemá kolize vůbec) nebo
"Failed to add wheel collision shape - would create compound with 41 children" (kola bez kolizních tvarů). Počítají se
compoundChild tvary pod kompoundem v i3d; tvary, které přepíná konfigurace (objectChange compoundChildActive, např. nádrže),
jen tolik, kolik jich je v nejhorší konfiguraci aktivních; k tomu kořenový tvar kompoundu a nejvíc kol z wheelConfiguration
(sedí s logem hry: Middle 46 tvarů, 5 nádrží z toho 1 aktivní -> "with 43 children"; Max 41/5/2 + 1 kolo = 40, další kolo selže).

    python tools/check_compound.py
"""

import os
import sys
import xml.etree.ElementTree as ET

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEH = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "vehicles")
LIMIT = 40


def count(name):
    base = os.path.join(VEH, name, name)
    scene = ET.parse(base + ".i3d").getroot().find("Scene")
    xml = ET.parse(base + ".xml").getroot()
    out = []
    for comp in scene:
        if comp.get("compound") != "true":
            continue
        shapes = [e.get("name") for e in comp.iter() if e.get("compoundChild") == "true"]
        toggled = {oc.get("node") for oc in xml.iter("objectChange") if oc.get("compoundChildActive") is not None}
        toggled &= set(shapes)
        worst = 0
        for cfg in xml.iter():
            if cfg.tag.endswith("Configuration"):
                active = {oc.get("node") for oc in cfg.iter("objectChange") if oc.get("compoundChildActive") == "true"}
                worst = max(worst, len(active & toggled))
        wheels = max([len(list(c.iter("wheel"))) for c in xml.iter("wheelConfiguration")] or [0])
        total = len(shapes) - len(toggled) + worst + 1 + wheels
        out.append((comp.get("name"), len(shapes), len(toggled), worst, wheels, total))
    return out


def main():
    bad = 0
    for name in sorted(os.listdir(VEH)):
        if not os.path.exists(os.path.join(VEH, name, name + ".i3d")):
            continue
        for comp, shapes, toggled, worst, wheels, total in count(name):
            ok = total <= LIMIT
            bad += not ok
            print(f"{'OK' if ok else 'CHYBA'}  {comp}: {shapes} tvarů ({toggled} z konfigurace, aktivních nejvýš {worst}) "
                  f"+ kořen + {wheels} kol = {total} / {LIMIT}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
