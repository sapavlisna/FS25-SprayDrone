"""Víko vzorkovacího kufru AIRASI bez hry a bez Blenderu: python tools/test_case_lid.py

Víko (bedna s přihrádkami přes celé víko) je v animaci caseLidAnim a zavírá se až po uklizení dronu a podložky; i3d má víko
zavřené (složený stav = koupě, přeprava); XML nese animaci a těžiště z posledního exportu modelu; zavřené víko nekoliduje
s obsahem spodku a celým otáčením projde bez dotyku (čísla počítá blender/build_drone_case.py, crate_lid_report, do
out/case_preview/samplerCase_export.txt); kolize jen zavřeného tvaru (žádný pevný tvar za kufrem).
"""

import os
import re
import sys
import xml.etree.ElementTree as ET

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASE_DIR = os.path.join(PROJECT, "mod", "FS25_SprayDroneTrailer", "objects", "droneCase")
EXPORT = os.path.join(PROJECT, "out", "case_preview", "samplerCase_export.txt")

fails = 0


def check(name, ok, info=None):
    global fails
    if not ok:
        fails += 1
    print(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + str(info) if info is not None else ''}")


def vec(s):
    return [float(c) for c in s.split()]


xml = ET.parse(os.path.join(CASE_DIR, "samplerCase.xml")).getroot()
anim = xml.find("animations/animation[@name='caseLidAnim']")
parts = anim.findall("part")
lid = [p for p in parts if p.get("node") == "caseLid"]
check("víko caseLid je v animaci caseLidAnim (jeden díl)", len(lid) == 1, len(lid))
end = max(float(p.get("endTime")) for p in parts)
if lid:
    p = lid[0]
    check("víko: otevřené -180° (leží za kufrem), zavřené 0°", vec(p.get("startRot")) == [-180, 0, 0] and vec(p.get("endRot")) == [0, 0, 0],
          (p.get("startRot"), p.get("endRot")))
    others = max(float(q.get("endTime")) for q in parts if q.get("node") != "caseLid")
    check("víko se zavírá až po uklizení dronu a podložky (a otevírá jako první)", float(p.get("startTime")) >= others - 1e-6,
          (p.get("startTime"), others))
    check("víko končí s animací (čas 1 = zavřeno)", abs(float(p.get("endTime")) - end) < 1e-6)
fold = xml.find("foldable/foldingConfigurations/foldingConfiguration/foldingParts")
check("Foldable začíná složený (startMoveDirection 1)", fold.get("startMoveDirection") == "1")

scene = ET.parse(os.path.join(CASE_DIR, "samplerCase.i3d")).getroot().find("Scene")
nodes = {e.get("name"): e for e in scene.iter() if e.get("name")}
rot = vec(nodes["caseLid"].get("rotation") or "0 0 0")
check("i3d: víko zavřené (koupě, načtení složeného kufru)", all(abs(r) < 1e-3 for r in rot), rot)
cols = [n for n in nodes if n.startswith("floorCollision")]
check("kolize jen zavřeného tvaru (floorCollision01, nic za kufrem)", cols == ["floorCollision01"], cols)
check("podložka casePad visí pod víkem (zavírá se s ním ve štěrbině)", nodes["caseLid"].find(".//TransformGroup[@name='casePad']") is not None)

with open(EXPORT, encoding="utf-8") as f:
    text = f.read()
block = re.search(r"    <animations>.*?    </animations>", text, re.S)
mine = ET.tostring(xml.find("animations"), encoding="unicode")
check("animace v XML = poslední export modelu", block is not None and
      [ET.tostring(e) for e in ET.fromstring(block.group(0)).iter("part")] == [ET.tostring(e) for e in ET.fromstring(mine).iter("part")])
rep = dict(re.findall(r"^(\w+): (.*)$", text.split("## zavřené víko nad obsahem")[-1], re.M)) if "## zavřené víko" in text else {}
check("export má zprávu o zavřeném víku", bool(rep))
if rep:
    need = float(rep["clearance_min"])
    check("zavřené víko: bedna, krabičky a podložka neprotínají dron ani baterie", rep["overlap_inner_content"] == "0", rep["overlap_inner_content"])
    check("zavřené víko: skořepina víka neprotíná dron ani baterie", rep["overlap_shell_content"] == "0")
    check("zavřené víko: bedna neprotíná spodek kufru", rep["overlap_inner_base"] == "0")
    check(f"vůle bedny nad obsahem aspoň {need * 1000:.0f} mm", float(rep["vertical_gap"]) >= need, rep["vertical_gap"])
    check(f"nejbližší místo bedny od obsahu aspoň {need * 1000:.0f} mm", float(rep["nearest_gap"]) >= need, rep["nearest_gap"])
    check("víko projde celým otáčením bez dotyku obsahu", rep["sweep_overlaps"] == "[]", rep["sweep_overlaps"])
    com = vec(xml.find("base/components/component").get("centerOfMass"))
    want = vec(rep["centerOfMass_i3d"])
    check("těžiště v XML = zavřený kufr z exportu (±2 cm)", all(abs(a - b) <= 0.02 + 1e-9 for a, b in zip(com, want)), (com, want))
size = xml.find("base/size")
check("výška v XML odpovídá kufru se zavřeným víkem (0,55 m)", abs(float(size.get("height")) - 0.55) < 1e-6, size.get("height"))

print(f"\n{'OK' if fails == 0 else 'CHYB: ' + str(fails)}")
sys.exit(1 if fails else 0)
