"""Rozbor telemetrie jízdy (řádky "TEL t x z yaw kmh" v runlog.json): rychlost, rotace, rozptyl rychlosti a zrychlení.

python tools/cinema/tel_analyze.py out/trailer/raw/t_obs_a_t1.runlog.json
"""

import json
import math
import re
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8")
data = json.load(open(sys.argv[1], encoding="utf-8"))
rows = []
for line in data.get("log", []):
    m = re.search(r"TEL (\d+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)", line)
    if m:
        rows.append(tuple(float(g) for g in m.groups()))
print("vzorků:", len(rows))
if len(rows) < 10:
    sys.exit()
t0 = rows[0][0]
dts = [b[0] - a[0] for a, b in zip(rows, rows[1:])]
print("dt snímků ms: průměr %.1f max %.1f" % (statistics.mean(dts), max(dts)))
sp = [r[4] for r in rows]
print("rychlost km/h: min %.1f max %.1f průměr %.1f sm.odch. %.2f" % (min(sp), max(sp), statistics.mean(sp), statistics.pstdev(sp)))
vx = []
for a, b in zip(rows, rows[1:]):
    dt = (b[0] - a[0]) / 1000
    if dt > 0:
        vx.append((b[0], math.hypot(b[1] - a[1], b[2] - a[2]) / dt * 3.6))
print("rychlost z polohy km/h: min %.1f max %.1f sm.odch. %.2f" % (min(v for _, v in vx), max(v for _, v in vx), statistics.pstdev([v for _, v in vx])))
yaw = [r[3] for r in rows]
dy = [abs(math.atan2(math.sin(b - a), math.cos(b - a))) for a, b in zip(yaw, yaw[1:])]
print("změna yaw/snímek (rad): průměr %.5f max %.5f" % (statistics.mean(dy), max(dy)))
step = max(len(rows) // 25, 1)
print("t[s] km/h x z yaw")
for r in rows[::step]:
    print("%5.1f %5.1f %8.1f %8.1f %6.3f" % ((r[0] - t0) / 1000, r[4], r[1], r[2], r[3]))
