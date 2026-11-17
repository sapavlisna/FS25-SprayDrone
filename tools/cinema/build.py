"""Zabalí FS25_SprayDroneCinema do zipu (modDesc.xml v kořeni) a nasadí ho do složky módů.

python tools/cinema/build.py            zabalí a nasadí
python tools/cinema/build.py --no-deploy  jen zip do out/trailer/
Hra drží zip zamčený, dokud běží: nasazení při běžící hře selže (stačí `reload` příkaz módu pro změny Lua).
"""

import argparse
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "tools", "cinema", "FS25_SprayDroneCinema")
OUT = os.path.join(ROOT, "out", "trailer", "FS25_SprayDroneCinema.zip")
MODS = r"E:\SteamLibrary\FS25-Mods"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-deploy", action="store_true")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(SRC):
            for name in sorted(files):
                path = os.path.join(base, name)
                z.write(path, os.path.relpath(path, SRC).replace("\\", "/"))
    print("zip:", OUT, os.path.getsize(OUT), "B")
    if args.no_deploy:
        return
    dst = os.path.join(MODS, "FS25_SprayDroneCinema.zip")
    try:
        shutil.copy2(OUT, dst)
    except PermissionError:
        sys.exit("zip je zamčený (hra běží?): " + dst)
    print("nasazeno:", dst)


main()
