# Kontrola syntaxe Lua skriptů modu přes LuaJIT (lupa) bez spuštění hry.
# Použití: .venv\Scripts\python.exe tools\lua_check.py  [soubory...]  (bez argumentů všechny scripts/**/*.lua)
import sys
from pathlib import Path

from lupa import luajit21

root = Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "scripts"
files = [Path(a) for a in sys.argv[1:]] or sorted(root.rglob("*.lua"))
lua = luajit21.LuaRuntime()
check = lua.eval("function(src, name) local f, err = loadstring(src, name) return err end")
bad = 0
for f in files:
    err = check(f.read_text(encoding="utf-8"), "@" + f.name)
    if err:
        bad += 1
        print(f"CHYBA {err}")
    else:
        print(f"ok    {f.name}")
sys.exit(1 if bad else 0)
