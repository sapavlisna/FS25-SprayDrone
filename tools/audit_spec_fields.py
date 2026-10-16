"""Kontrola klasifikace polí spec.<jméno> (scripts/SprayDroneFields.lua) proti zdrojům.

Selže, když (a) pole použité ve zdrojích není v žádném seznamu, (b) je v obou seznamech. Vypíše pole ze seznamů, která se nikde
nepoužívají (varování), a s volbou --functions tabulku funkcí, které sahají na per-drone pole (D) a na sdílená (S): funkce
označené D (nebo smíšené) se smí volat jen v kontextu dronu (runAs / forEach), viz docs/DVA_DRONY_NAVRH.md kap. 1.4.

    python tools/audit_spec_fields.py [--functions]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "scripts"


def load_lists():
    text = (ROOT / "SprayDroneFields.lua").read_text(encoding="utf-8")
    result = {}
    for name in ("shared", "drone"):
        m = re.search(r"SprayDroneFields\." + name + r" = \{(.*?)\n\}", text, re.S)
        body = re.sub(r"--[^\n]*", "", m.group(1))
        result[name] = set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', body))
    return result["shared"], result["drone"]


def main():
    shared, drone = load_lists()
    used = {}
    functions = {}
    func_re = re.compile(r"^(?:local )?function ([A-Za-z0-9_.:]+)\(")
    for path in sorted(ROOT.rglob("*.lua")):
        if path.name in ("SprayDroneFields.lua", "SprayDroneDrones.lua"):
            continue
        current = None
        for line in path.read_text(encoding="utf-8").splitlines():
            m = func_re.match(line)
            if m:
                current = f"{path.name}:{m.group(1)}"
            for field in re.findall(r"\bspec\.([A-Za-z_][A-Za-z0-9_]*)", line):
                used.setdefault(field, set()).add(path.name)
                if current is not None:
                    functions.setdefault(current, set()).add(field)
    bad = False
    for field in sorted(used):
        if field not in shared and field not in drone:
            print(f"CHYBÍ v seznamech: spec.{field} ({', '.join(sorted(used[field]))})")
            bad = True
    for field in sorted(shared & drone):
        print(f"V OBOU seznamech: {field}")
        bad = True
    for field in sorted((shared | drone) - set(used)):
        print(f"varování: {field} se nikde nepoužívá")
    if "--functions" in sys.argv:
        print()
        for name, fields in sorted(functions.items()):
            d = sorted(f for f in fields if f in drone)
            s = sorted(f for f in fields if f in shared)
            kind = "D+S" if d and s else ("D" if d else ("S" if s else "-"))
            print(f"{kind:3} {name}: " + ", ".join(d[:6]) + (" ..." if len(d) > 6 else ""))
    print(f"\n{len(used)} použitých polí, {len(shared)} sdílených, {len(drone)} dronu: {'CHYBA' if bad else 'v pořádku'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
