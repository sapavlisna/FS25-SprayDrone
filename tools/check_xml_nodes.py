"""Kontrola, že každý uzel, na který odkazuje XML vozidla (node, linkNode, ... jménem z i3dMappings), v i3dMappings existuje.

    python tools/check_xml_nodes.py [vozidlo.xml ...]      (bez argumentů všechna tři vozidla módu)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "vehicles"
ATTRS = ("node", "linkNode", "rotateNode", "lidNode", "activateNode", "neckNode", "cameraNode", "repr", "rootNode")


def check(path):
    text = path.read_text(encoding="utf-8")
    ids = set(re.findall(r'<i3dMapping id="([^"]+)"', text))
    body = text[: text.index("<i3dMappings>")] if "<i3dMappings>" in text else text
    missing = {}
    for attr in ATTRS:
        for m in re.finditer(rf'\b{attr}="([^"]+)"', body):
            value = m.group(1)
            if re.match(r"^[\d>|]+$", value) or value.startswith("$") or "/" in value or "." in value or " " in value:
                continue
            if value not in ids:
                line = body.count("\n", 0, m.start()) + 1
                missing.setdefault(value, []).append(line)
    for name, lines in sorted(missing.items()):
        print(f"  CHYBÍ v i3dMappings: {name} (řádky {lines[:4]})")
    print(f"{'CHYBA' if missing else 'OK   '} {path.name}: {len(ids)} mapování")
    return bool(missing)


def main():
    files = [Path(a) for a in sys.argv[1:]] or sorted(ROOT.glob("*/*.xml"))
    return 1 if any([check(f) for f in files]) else 0


if __name__ == "__main__":
    sys.exit(main())
