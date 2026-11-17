"""Spojí akci a kameru do spustitelné scény (multicam: stejná akce, jiná kamera).

python tools/cinema/v2/mk_take.py <akce> <kam>      -> tools/cinema/scenes/v2_<akce>_<kam>.json
python tools/cinema/v2/mk_take.py --dry             projde všechny akce × kamery a vypíše časové osy

<akce>.akce.json: {"vlek", "beat", "zabery": [...], "steps": [...]}; v krocích je jednou
{"kamera": true} = čas 0 kamerové osy. Kroky akce za značkou se nesmí měnit podle kamery.
<akce>.kam<X>.json: {"popis", "steps": [{"at": 0.0, "cmd": "camPath", ...}, ...]}; "at" je čas
od značky. Vložení rozdělí pauzy ({"sleep": s}) akce, takže časování akce zůstane stejné.
Kroky s "wait" nebo čekací příkazy (waitDrone, waitDrive) čas nezvyšují; kamera, která má
navazovat až po nich, použije {"after": "<mark>"} místo "at" (mark v akci: {"mark": "..."}).
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCENES_V2 = os.path.join(HERE, "scenes")
SCENES = os.path.join(os.path.dirname(HERE), "scenes")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge(akce, kam):
    steps = akce["steps"]
    idx = [i for i, s in enumerate(steps) if s.get("kamera")]
    if len(idx) != 1:
        raise ValueError("akce musí mít právě jeden krok {\"kamera\": true}")
    head, tail = steps[:idx[0]], steps[idx[0] + 1:]
    timed = sorted((s for s in kam["steps"] if "after" not in s), key=lambda s: s.get("at", 0.0))
    after = {}
    for s in kam["steps"]:
        if "after" in s:
            after.setdefault(s["after"], []).append(s)

    def strip(s):
        return {k: v for k, v in s.items() if k not in ("at", "after")}

    out = list(head)
    t = 0.0
    q = list(timed)
    while q and q[0].get("at", 0.0) <= 0.0:
        out.append(strip(q.pop(0)))
    for s in tail:
        if "sleep" in s:
            remaining = float(s["sleep"])
            while q and q[0]["at"] <= t + remaining + 1e-6:
                dt = q[0]["at"] - t
                if dt > 1e-6:
                    out.append({"sleep": round(dt, 3)})
                    t += dt
                    remaining -= dt
                out.append(strip(q.pop(0)))
            if remaining > 1e-6:
                out.append({"sleep": round(remaining, 3)})
                t += remaining
            continue
        out.append(s)
        if "mark" in s and s["mark"] in after:
            out.extend(strip(c) for c in after.pop(s["mark"]))
    if q:
        raise ValueError("kamerové kroky po konci akce: %s" % [c.get("at") for c in q])
    if after:
        raise ValueError("neznámé značky after: %s" % list(after))
    return out


def build(akce_id, kam_id, write=True):
    akce = load(os.path.join(SCENES_V2, akce_id + ".akce.json"))
    kam = load(os.path.join(SCENES_V2, "%s.kam%s.json" % (akce_id, kam_id)))
    name = "v2_%s_%s" % (akce_id, kam_id)
    scene = {
        "name": name,
        "title": "%s | kamera %s: %s" % (akce_id, kam_id, kam.get("popis", "")),
        "v2": {"akce": akce_id, "kamera": kam_id, "vlek": akce.get("vlek"), "beat": akce.get("beat"), "zabery": akce.get("zabery", [])},
        "steps": merge(akce, kam),
    }
    if write:
        with open(os.path.join(SCENES, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(scene, f, ensure_ascii=False, indent=1)
    return scene


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["--dry"]:
        bad = 0
        for ap in sorted(glob.glob(os.path.join(SCENES_V2, "*.akce.json"))):
            akce_id = os.path.basename(ap)[:-len(".akce.json")]
            kams = sorted(glob.glob(os.path.join(SCENES_V2, akce_id + ".kam*.json")))
            if not kams:
                print("%-28s BEZ KAMER" % akce_id)
                bad += 1
            for kp in kams:
                kam_id = os.path.basename(kp)[len(akce_id) + 4:-len(".json")]
                try:
                    sc = build(akce_id, kam_id, write=False)
                    print("%-28s %s  %d kroků" % (akce_id, kam_id, len(sc["steps"])))
                except Exception as e:
                    print("%-28s %s  CHYBA %s" % (akce_id, kam_id, e))
                    bad += 1
        sys.exit(1 if bad else 0)
    sc = build(sys.argv[1], sys.argv[2])
    print(sc["name"])


if __name__ == "__main__":
    main()
