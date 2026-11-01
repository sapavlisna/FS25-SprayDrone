"""Ověří XML módu proti oficiálním schématům FS25 (shared/xml/schema) a že odkazované soubory existují.

python tools/validate_mod.py
"""

import os
import sys

from lxml import etree

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender"))
import sdt_paths  # noqa: E402

SCHEMA_DIR = os.path.join(sdt_paths.GAME_DIR, "shared", "xml", "schema")

CHECKS = [
    ("modDesc.xml", "modDesc.xsd"),
    (os.path.join("xml", "fillTypes.xml"), "fillTypes.xsd"),
    (os.path.join("vehicles", "sprayDroneTrailerMiddle", "sprayDroneTrailerMiddle.xml"), "vehicle.xsd"),
    (os.path.join("objects", "canister", "canisterFertilizer.xml"), "vehicle.xsd"),
    (os.path.join("objects", "canister", "canisterHerbicide.xml"), "vehicle.xsd"),
]


def validate(xml_rel, xsd_name):
    xsd_path = os.path.join(SCHEMA_DIR, xsd_name)
    if not os.path.exists(xsd_path):
        return [f"schéma {xsd_name} ve hře není"]
    schema = etree.XMLSchema(etree.parse(xsd_path))
    doc = etree.parse(os.path.join(MOD, xml_rel))
    if schema.validate(doc):
        return []
    return [f"řádek {e.line}: {e.message}" for e in schema.error_log]


def referenced_files(xml_rel):
    doc = etree.parse(os.path.join(MOD, xml_rel))
    missing = []
    for el in doc.iter():
        for key in ("filename", "xmlFilename", "hud"):
            v = el.get(key)
            if v and v != "-" and not v.startswith("$"):     # "-" = vanilla zápis pro "žádný díl" (innerRim)
                if not os.path.exists(os.path.join(MOD, v)):
                    missing.append(f"<{el.tag} {key}={v}>")
        if el.tag in ("image", "iconFilename", "filename") and el.text and not el.text.startswith("$"):
            if not os.path.exists(os.path.join(MOD, el.text.strip())):
                missing.append(f"<{el.tag}>{el.text.strip()}")
    return missing


def main():
    ok = True
    for xml_rel, xsd in CHECKS:
        errors = validate(xml_rel, xsd)
        missing = referenced_files(xml_rel)
        status = "OK" if not errors and not missing else "CHYBA"
        ok &= status == "OK"
        print(f"{status}  {xml_rel}  (proti {xsd})")
        for e in errors[:30]:
            print("    schéma:", e)
        for m in missing:
            print("    chybí soubor:", m)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
