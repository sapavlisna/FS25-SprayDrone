# Ruční zkouška čisté aritmetiky mixéru (SprayDroneMixer.lua) přes LuaJIT/lupa: python tools/test_mixer.py
from pathlib import Path
from lupa import luajit21
lua = luajit21.LuaRuntime()
lua.execute(open(Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "scripts" / "SprayDroneMixer.lua", encoding="utf-8").read())
print(lua.execute('''
local M = SprayDroneMixer
local out = {}
local function p(...) out[#out+1] = table.concat({...}, " ") end
local r = { fert = 0.25, herb = 0.10 }
local a, l = M.getAvailable(0.25, 300, 50); p("avail", a, l)
a, l = M.getAvailable(0.10, 300, 50); p("avail2", a, l)
local w, c = M.getParts(0.25, 200); p("parts", w, c)
local s = M.resolve("water", 300, "fert", 50, r, "water"); p("mix", s.kind, s.fillType, s.liters, s.limit)
s = M.resolve("fert", 100, "herb", 50, r, "water"); p("direct", s.kind, s.fillType, s.liters)
s = M.resolve("water", 300, nil, 0, r, "water"); p("noConc", s.kind, s.reason, tostring(s.fillType))
s = M.resolve(nil, 0, "herb", 20, r, "water"); p("noWater", s.kind, s.reason, s.fillType)
s = M.resolve(nil, 0, nil, 0, r, "water"); p("empty", s.kind, s.reason)
local r2 = { cfert = 0.25, cherb = 0.05 }
local prod = { cfert = "fert", cherb = "herb" }
s = M.resolve("water", 300, "cherb", 20, r2, "water", prod); p("mixProduct", s.kind, s.fillType, s.concentrateType, s.limit, s.liters)
s = M.resolve("herb", 100, "cherb", 20, r2, "water", prod); p("directProduct", s.kind, s.fillType, tostring(s.concentrateType))
s = M.resolve(nil, 0, "cfert", 20, r2, "water", prod); p("noWaterProduct", s.kind, s.reason, s.fillType)
s = M.resolve("water", 300, "other", 20, r2, "water", prod); p("unknownConc", s.kind, s.reason, tostring(s.fillType))
p("drain", tostring(M.canAcceptDrained("water", 10, "fert")), tostring(M.canAcceptDrained("fert", 10, "fert")), tostring(M.canAcceptDrained(nil, 0, "fert")))
return table.concat(out, ";")
'''))
