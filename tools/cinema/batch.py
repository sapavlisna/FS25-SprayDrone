"""Natočí dávku takes a ke každému udělá kontaktní arch a kontrolu plynulosti.

python tools/cinema/batch.py a01_aerial:1 a01_aerial:2 a02_road_b:3 ...    (scéna[:take], výchozí take 1)
Soubor se jmenuje <scéna>_t<N>; log běhu je out/trailer/raw/<scéna>_t<N>.run.log
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RAW = os.path.join(ROOT, "out", "trailer", "raw")
PY = sys.executable
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

for spec in sys.argv[1:]:
    scene, _, take = spec.partition(":")
    take = take or "1"
    name = "%s_t%s" % (scene, take)
    res = subprocess.run([PY, os.path.join(HERE, "run_scene.py"), scene, "--obs", "--take", take], capture_output=True, text=True, encoding="utf-8", errors="replace")
    with open(os.path.join(RAW, name + ".run.log"), "w", encoding="utf-8") as f:
        f.write(res.stdout + res.stderr)
    errs = [l for l in res.stdout.splitlines() if " ERR " in l or "přerušena" in l or "varov" in l.lower()]
    print("==", name, "rc=%d" % res.returncode)
    for l in errs:
        print("   ", l[:200])
    if not os.path.exists(os.path.join(RAW, name + ".mkv")):
        print("    BEZ ZÁZNAMU")
        continue
    sheet = subprocess.run([PY, os.path.join(HERE, "clipsheet.py"), name, "1.2", "4", "480"], capture_output=True, text=True)
    check = subprocess.run([PY, os.path.join(HERE, "clipcheck.py"), name], capture_output=True, text=True, encoding="utf-8")
    print(check.stdout.strip())
