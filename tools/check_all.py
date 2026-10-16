"""Jeden příkaz na celý řetězec: rebuild + export vleků v Blenderu, validátory, offline Lua testy, kontrola savu.

    .venv\\Scripts\\python.exe tools\\check_all.py [--no-build] [--only mini middle max] [--save 12] [--blender cesta]

Výstup je tabulka OK / CHYBA / ZNÁMÉ (známé mezery XSD: „sprayDrone“ u Middle, „storeType“ v modDesc) a u chyb posledních pár řádků výstupu.
Exit 1, pokud něco selhalo. Hra se nespouští, nic se nezapisuje do savu (jen čte).
"""

import argparse
import os
import re
import subprocess
import sys
import time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blender"))
import sdt_paths  # noqa: E402

BLENDER = sdt_paths.BLENDER
TRAILERS = ("mini", "middle", "max")
# známé mezery oficiálních XSD: vlastní blok modu u Middle a <storeType> (vlastní záložka obchodu, schéma ho nezná, hra
# i mody jako LSFM ho používají)
KNOWN_XSD = re.compile(r"Element '(sprayDrone|storeType)': This element is not expected")
BAD_TEXT = re.compile(r"Traceback|^CHYBA|\bSELHAL[OA]?\s+[1-9]|\bFAIL\b", re.M)
# Blender při startu i ukončení hlásí chybu odhlášení cizího doplňku (blender_i3d_importer); build ani export se jí neřídí
KNOWN_BLENDER_EXIT = re.compile(r"Traceback[^\n]*\n(?:[ \t]+[^\n]*\n)*?UnboundLocalError: cannot access local variable 'bpy'[^\n]*\n?")

results = []


def run(name, cmd, timeout=1800, check=None):
    start = time.time()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run(cmd, cwd=PROJECT, env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        out, rc = (p.stdout or "") + (p.stderr or ""), p.returncode
    except subprocess.TimeoutExpired:
        out, rc = f"timeout po {timeout} s", 1
    out = KNOWN_BLENDER_EXIT.sub("", out)
    if check is not None:
        status = check(out, rc)
    else:
        status = "OK" if rc == 0 and not BAD_TEXT.search(out) else "CHYBA"
    results.append((name, status, time.time() - start, out))
    print(f"{status:6} {name}  ({time.time() - start:.0f} s)", flush=True)


def check_validate(out, rc):
    errors = [l for l in out.splitlines() if "schéma:" in l or "chybí soubor" in l]
    if rc == 0:
        return "OK"
    return "ZNÁMÉ" if errors and all(KNOWN_XSD.search(l) for l in errors) else "CHYBA"


def check_audit(out, rc):
    return "CHYBA" if rc != 0 or "CHYBA v seznamech" in out else "OK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--only", nargs="+", choices=TRAILERS, default=list(TRAILERS))
    ap.add_argument("--save", default="12")
    ap.add_argument("--blender", default=BLENDER)
    a = ap.parse_args()
    py = sys.executable
    tools = os.path.join(PROJECT, "tools")

    if not a.no_build:
        if not os.path.exists(a.blender):
            print(f"CHYBA  Blender nenalezen: {a.blender} (--blender nebo SDT_BLENDER, nebo --no-build)")
            return 1
        for t in a.only:
            script = os.path.join(PROJECT, "blender", f"headless_{t}.py")
            run(f"build+export {t}", [a.blender, "-b", "--python", script, "--", "build", "export"], timeout=2400)

    run("validate_mod", [py, os.path.join(tools, "validate_mod.py")], check=check_validate)
    run("check_xml_nodes", [py, os.path.join(tools, "check_xml_nodes.py")])
    run("check_compound", [py, os.path.join(tools, "check_compound.py")])
    run("lua_check", [py, os.path.join(tools, "lua_check.py")])
    run("audit_spec_fields", [py, os.path.join(tools, "audit_spec_fields.py")], check=check_audit)
    for t in ("test_split", "test_mixer", "test_headlands"):
        run(t, [py, os.path.join(tools, t + ".py")])
    toolbox_test = os.path.join(PROJECT, "tmp", "test_toolbox_parts.py")
    if os.path.exists(toolbox_test):
        run("test_toolbox_parts", [py, toolbox_test])
    level_test = os.path.join(PROJECT, "tmp", "f", "test_level.py")
    if os.path.exists(level_test):
        run("test_level", [py, level_test])
    power_test = os.path.join(PROJECT, "tmp", "f", "test_power.py")
    if os.path.exists(power_test):
        run("test_power", [py, power_test])
    signal_test = os.path.join(PROJECT, "tmp", "f", "test_signal.py")
    if os.path.exists(signal_test):
        run("test_signal", [py, signal_test])
    spray_test = os.path.join(PROJECT, "tmp", "f", "test_spray.py")
    if os.path.exists(spray_test):
        run("test_spray", [py, spray_test])
    relayslots_test = os.path.join(PROJECT, "tmp", "f", "test_relayslots.py")
    if os.path.exists(relayslots_test):
        run("test_relayslots", [py, relayslots_test])
    for name in ("test_link", "test_tablet_logo"):
        test = os.path.join(PROJECT, "tmp", "f", name + ".py")
        if os.path.exists(test):
            run(name, [py, test])
    run(f"check_save {a.save}", [py, os.path.join(tools, "check_save.py"), a.save])

    bad = [r for r in results if r[1] == "CHYBA"]
    for name, status, _, out in bad:
        print(f"\n--- {name}")
        print("\n".join(out.strip().splitlines()[-15:]))
    print(f"\n{len(results)} kroků, chyb {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
