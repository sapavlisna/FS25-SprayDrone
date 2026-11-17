"""Kontrola trasy plnicí hadice Mini: délka volné části proti potřebné (SprayDronePad.hoseReaches) a nejmenší poloměr ohybu.

Načte uložený spraydrone_trailer_mini.blend (kvůli výšce hrdla dronu), jednou exekuje build_trailer_mini.py a vyhodnotí body
HOSE_LAY / HOSE_PARK_TIP / HOSE_PARK_DIR přímo v namespace (rychlejší než přestavba). Kandidáty se zkouší voláním evaluate()
na konci souboru.

blender.exe -b blender\\spraydrone_trailer_mini.blend --python blender\\tune_mini_hose.py
"""
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "build_trailer_mini.py")
ns = {"__file__": p, "__name__": "tune_hose"}
exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)

SLACK, ARC, FREE_FACTOR = 1.12, 0.20, 0.97          # stejné konstanty jako SprayDronePad.hoseReaches
MIN_RADIUS = 0.15                                    # ~ 4 x průměr hadice
FIXED_LAY = 3                                        # SprayDroneStation.HOSE_FIXED_LAY


def port_position():
    plate_y = ns["CRATE_Y_ANCHOR"] + ns["CRATE_H"] + ns["CRATE_LH"] / 2
    px, py = ns["DRONE_FILL_PORT"]["S"]
    z = bpy.data.objects["Drone_S_FillPort"].matrix_world.translation.z
    return Vector((px, plate_y + py, z))


def resample(pts, step):
    out, rest = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        seg = b - a
        d = step - rest
        while d <= seg.length:
            out.append(a + seg * (d / seg.length))
            d += step
        rest = seg.length - (d - step)
    return out


def evaluate(lay, tip, pdir, label):
    ns["HOSE_LAY"], ns["HOSE_PARK_TIP"], ns["HOSE_PARK_DIR"] = lay, tip, pdir
    path = [Vector(v) for v in ns["hose_rest_path"]()]
    cum = [0.0]
    for a, b in zip(path, path[1:]):
        cum.append(cum[-1] + (b - a).length)
    anchor = Vector(lay[FIXED_LAY - 1])
    anchor_i = min(range(len(path)), key=lambda i: (path[i] - anchor).length)
    free = (cum[-1] - ns["HOSE_LEAD"] - cum[anchor_i]) * FREE_FACTOR
    need = (port_position() - path[anchor_i]).length * SLACK + ARC
    pts = resample(path, 0.06)
    radii = []
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        cross = (b - a).cross(c - b).length
        if cross > 1e-9 and cum[-1] - 0.06 * i > 0.3:
            radii.append((a - b).length * (c - b).length * (c - a).length / (2 * cross))
    ok = min(radii) >= MIN_RADIUS and free >= need
    print("hadice %s: celkem %.2f m, volná %.2f m, potřeba %.2f m (rezerva %+.2f), min. poloměr ohybu %.3f m%s"
          % (label, cum[-1], free, need, free - need, min(radii), "" if ok else "  <-- NEVYHOVUJE"))


evaluate(list(ns["HOSE_LAY"]), ns["HOSE_PARK_TIP"], ns["HOSE_PARK_DIR"], "podle build_trailer_mini.py")
