"""Obrazový katalog modelů módu: out/katalog/index.html + img/, thumb/ a data/.

    python tools/katalog.py              všechny úlohy (Blender: data o modelech a dílech) a stránka
    python tools/katalog.py middle pump  jen vybrané úlohy (stránka se sestaví ze všech uložených dat)
    python tools/katalog.py --page       jen stránka (data z minulého běhu)

Snímky jsou z GIANTS Editoru (out/ge/<položka>_<pohled>.png, vyrábí je tools/ge_plan.py + GE MCP, postup v docs/NAVRH-dily.md);
stránka je převede na JPG. Blender renderuje jen stavy, které v GE nejdou nafotit (rozložený stav vleků a dronů), a karta to uvádí.
Blender běží bez okna s nízkou prioritou (BELOW_NORMAL, dědí ho i podprocesy knihovny dílů); mod/ se nemění.
"""

import html
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "mod", "FS25_SprayDroneTrailer")
OUT = os.path.join(ROOT, "out", "katalog")
LOCAL = os.path.join(ROOT, "local_paths.json")
BLENDER = r"E:\FS25-edit\blender-5.1.2-windows-x64\blender.exe"
JOBS = ["middle", "max", "mini", "mill", "pump", "hopper", "limebag", "canisters", "relay", "tablet", "dily"]
GE = os.path.join(ROOT, "out", "ge")
JPG_WIDTH, JPG_QUALITY = 1280, 76
THUMB, THUMB_QUALITY = 400, 70
BELOW_NORMAL, NO_WINDOW = 0x00004000, 0x08000000

# kde v módu model žije a které XML odkazuje jeho uzly
SOURCES = {
    "trailer_mini": ("vehicles/sprayDroneTrailerMini/sprayDroneTrailerMini.i3d", "vehicles/sprayDroneTrailerMini/sprayDroneTrailerMini.xml"),
    "trailer_middle": ("vehicles/sprayDroneTrailerMiddle/sprayDroneTrailerMiddle.i3d", "vehicles/sprayDroneTrailerMiddle/sprayDroneTrailerMiddle.xml"),
    "trailer_max": ("vehicles/sprayDroneTrailerMax/sprayDroneTrailerMax.i3d", "vehicles/sprayDroneTrailerMax/sprayDroneTrailerMax.xml"),
    "mill": ("vehicles/sdtLimeMill/sdtLimeMill.i3d", "vehicles/sdtLimeMill/sdtLimeMill.xml"),
    "pump": ("objects/pump/waterPump.i3d", "objects/pump/waterPump.xml"),
    "hopper": ("objects/hopper/limeHopper.i3d", "objects/hopper/limeHopper.xml"),
    "limebag50": ("objects/limeBag/limeBag50.i3d", "objects/limeBag/limeBag50.xml"),
    "relay": ("objects/relay/relayPole.i3d", "objects/relay/relayPole.xml"),
    "tablet": ("objects/tablet/droneTablet.i3d", "objects/tablet/droneTablet.xml"),
    "canister_Fertilizer": ("objects/canister/canisterFertilizer.i3d", "objects/canister/canisterFertilizer.xml"),
    "canister_Herbicide": ("objects/canister/canisterHerbicide.i3d", "objects/canister/canisterHerbicide.xml"),
    "canister_Diesel": ("objects/canister/canisterDiesel.i3d", "objects/canister/canisterDiesel.xml"),
    "limebigbag": ("$data/objects/bigBag/bigBag.i3d", "objects/limeBigBag/limeBigBag.xml"),
}
VANILLA = os.path.join(ROOT, "tools", "katalog_vanilla.json")     # položky, jejichž model je z hry (bez Blenderu): data z měření v GE
TRAILER_XML = {k: v[1] for k, v in SOURCES.items() if k.startswith("trailer_")}
CATEGORIES = [("vleky", "Vleky"), ("drony", "Drony"), ("díly", "Díly vleků"), ("vybavení", "Vybavení a objekty")]
STATE_LABEL = {"": "", "slozeny": "složený", "rozlozeny": "rozložený"}
STAV_LABEL = {"opraveno": "opraveno, čeká na schválení", "schvaleno": "schváleno"}     # pole "stav" v tools/katalog_analyza.json
BLENDER_NOTE = ("Snímky z Blenderu: rozložený stav vzniká ve hře animací skriptu (SprayDronePad, rozkládání dronu), "
                "v GIANTS Editoru se nedá nafotit.")
GE_NOTE = "Snímky z GIANTS Editoru (engine hry, výchozí konfigurace, bez animace)."
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "blender"))
import dily_info  # noqa: E402
import ge_plan  # noqa: E402


def blender_exe():
    if os.path.exists(LOCAL):
        with open(LOCAL, encoding="utf-8") as fh:
            p = json.load(fh).get("SDT_BLENDER")
            if p and os.path.exists(p):
                return p
    return BLENDER


def run_job(job):
    log_dir = os.path.join(ROOT, "tmp", "katalog")
    os.makedirs(log_dir, exist_ok=True)
    cmd = [blender_exe(), "-b", "--factory-startup", "--python", os.path.join(ROOT, "blender", "catalog_render.py"), "--", job, OUT]
    t = time.perf_counter()
    with open(os.path.join(log_dir, f"{job}.log"), "w", encoding="utf-8", errors="replace") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, creationflags=BELOW_NORMAL | NO_WINDOW)
    print(f"{job}: {'OK' if r.returncode == 0 else 'CHYBA ' + str(r.returncode)} za {time.perf_counter() - t:.0f} s")
    return r.returncode == 0


def mappings(xml_rel):
    path = os.path.join(MOD, xml_rel)
    if not os.path.exists(path):
        return []
    root = ET.parse(path).getroot()
    return [m.get("id") for m in root.iter("i3dMapping")]


def resolve_i3d(rel):
    """Cesta k i3d: v módu, nebo ve hře u `$data/...`."""
    if rel.startswith("$data/"):
        with open(LOCAL, encoding="utf-8") as fh:
            return os.path.join(json.load(fh)["FS25_GAME_DIR"], "data", rel[6:])
    return os.path.join(MOD, rel)


def i3d_files(i3d_rel):
    path = resolve_i3d(i3d_rel)
    if not os.path.exists(path):
        return []
    root = ET.parse(path).getroot()
    return sorted({f.get("filename") for f in root.iter("File") if f.get("filename")})


def code_refs(names):
    """Jména uzlů, která se objevují v Lua skriptech módu (hledání uzlů podle jména za běhu)."""
    found = set()
    texts = []
    for dp, _, fs in os.walk(os.path.join(MOD, "scripts")):
        for f in fs:
            if f.endswith(".lua"):
                with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                    texts.append(fh.read())
    blob = "\n".join(texts)
    for n in names:
        if re.search(r'["\']' + re.escape(n) + r'["\']', blob):
            found.add(n)
    return found


def save_jpg(src, dst, width, quality):
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        im.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)


def ge_name(item, st):
    """Jméno položky v out/ge: id položky, u dílů s variantou id__varianta; stav „složený“ je výchozí konfigurace."""
    if item.get("job") == "dily":
        return item["id"] + (f"__{st['slug']}" if st.get("slug") else "")
    return item["id"] if st["state"] in ("", "slozeny") else None


def attach_ge(items):
    """Ke každému stavu přiřadí snímky z GE (převede na JPG do img/ a thumb/), jinak nechá Blender; úklid nepoužitých obrázků."""
    img = os.path.join(OUT, "img")
    th = os.path.join(OUT, "thumb")
    os.makedirs(img, exist_ok=True)
    os.makedirs(th, exist_ok=True)
    keep = set()
    result = []
    for it in items:
        ok = []
        variants = {v["slug"]: v for v in it.pop("variants", [])}
        for k in ("visibleNames", "pts", "bbox"):
            it.pop(k, None)
        for st in it["states"]:
            v = variants.get(st.get("slug", ""))
            if v:
                st.update({k: v[k] for k in ("tris", "objects", "size", "materials") if k in v})
            name = ge_name(it, st)
            ge_shots = []
            for view, _, _ in ge_plan.VIEWS:
                src = os.path.join(GE, f"{name}_{view}.png") if name else None
                if src and os.path.exists(src):
                    fn = f"{name}_{view}.jpg"
                    dst = os.path.join(img, fn)
                    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
                        save_jpg(src, dst, JPG_WIDTH, JPG_QUALITY)
                    ge_shots.append({"file": fn, "view": view, "label": ge_plan.VIEW_LABELS[view], "ortho": False, "mpp": None,
                                     "source": "ge"})
            if ge_shots:
                st["shots"] = ge_shots
                st["source"] = "ge"
                st["sourceNote"] = GE_NOTE
            elif st["shots"]:
                st["source"] = "blender"
                st["sourceNote"] = BLENDER_NOTE
            else:
                print("bez snímků:", it["id"], st["state"])
                continue
            for sh in st["shots"]:
                keep.add(sh["file"])
            ok.append(st)
        it["states"] = ok
        if ok:
            result.append(it)
    for d in (img, th):
        for f in os.listdir(d):
            if f not in keep:
                os.remove(os.path.join(d, f))
    for f in keep:
        src, dst = os.path.join(img, f), os.path.join(th, f)
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
            save_jpg(src, dst, THUMB, THUMB_QUALITY)
    return result


def load_items():
    items = []
    for job in JOBS:
        p = os.path.join(OUT, "data", f"{job}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                items += json.load(fh)["items"]
    if os.path.exists(VANILLA):
        with open(VANILLA, encoding="utf-8") as fh:
            items += json.load(fh)
    return items


def enrich(items):
    all_maps = {k: set(mappings(v)) for k, v in TRAILER_XML.items()}
    names_all = set()
    for it in items:
        names_all |= set(it.get("objectNames", []))
    in_code = code_refs(names_all)
    for it in items:
        if it.get("job") == "dily":
            continue
        names = set(it.get("objectNames", []))
        src = SOURCES.get(it["id"])
        maps = set()
        if src:
            maps = set(mappings(src[1]))
            it["i3d"] = src[0]
            it["files"] = i3d_files(src[0])
        else:
            for k, m in all_maps.items():
                maps |= m
        if it["id"].startswith(("trailer_", "mill", "pump", "hopper", "relay", "tablet", "canister", "limebag", "limebigbag")):
            it["mapped"] = sorted(maps)
        else:
            it["mapped"] = sorted(names & maps)
            on = [t.split("_")[1].capitalize() for t, m in all_maps.items() if names & m]
            if on:
                it.setdefault("usedOn", on)
        it["codeNames"] = sorted(names & in_code)
        it.pop("objectNames", None)


def load_analysis():
    p = os.path.join(ROOT, "tools", "katalog_analyza.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def page(items):
    analysis = load_analysis()
    for k, a in analysis.items():
        if a.get("stav") not in (None, *STAV_LABEL):
            raise ValueError(f"katalog_analyza.json: {k}: neznámý stav {a['stav']!r}")
    data = json.dumps({"items": items, "categories": CATEGORIES, "states": STATE_LABEL, "stavy": STAV_LABEL, "groups": dily_info.GROUPS,
                       "analysis": analysis}, ensure_ascii=False)
    with open(os.path.join(ROOT, "tools", "katalog_template.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    out = tpl.replace("/*DATA*/null", data).replace("{{GENERATED}}", html.escape(time.strftime("%Y-%m-%d %H:%M")))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(out)
    print("stránka:", os.path.join(OUT, "index.html"), f"({len(items)} položek)")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--page" not in sys.argv:
        for job in args or JOBS:
            run_job(job)
    items = load_items()
    enrich(items)
    items = attach_ge(items)
    page(items)


if __name__ == "__main__":
    main()
