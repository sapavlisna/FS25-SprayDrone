# Ruční zkouška dvou dronů bez hry (LuaJIT/lupa): python tools/test_split.py
# 1. SprayDroneDrones: pohled dronu 2 čte a zapisuje sdílená pole do spec, per-drone drží sám, runAs je vnořený a po chybě obnoví kontext.
# 2. SprayDroneRoute.splitLegs a rezervace úseků: součet délek, žádný překryv, obrácení legů druhého dronu, minSplit, vyvážení.
import sys
from pathlib import Path
from lupa import luajit21

lua = luajit21.LuaRuntime()
scripts = Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "scripts"

lua.execute('''
MathUtil = {
    vector2Length = function(x, z) return math.sqrt(x * x + z * z) end,
    getYRotationFromDirection = function(dx, dz) return math.atan2(dx, dz) end,
    getAngleDifference = function(a, b) return (a - b + math.pi) % (2 * math.pi) - math.pi end,
}
math.clamp = function(v, lo, hi) return math.max(lo, math.min(hi, v)) end
CollisionFlag = { STATIC_OBJECT = 1, TREE = 2, BUILDING = 4 }
Logging = { warning = function(...) WARNINGS = (WARNINGS or 0) + 1 end }
SprayDroneStation = { SPEC_NAME = "spec_test" }
unpack = unpack or table.unpack
''')
for name in ("SprayDroneRoute.lua", "SprayDroneFields.lua", "SprayDroneDrones.lua"):
    lua.execute((scripts / name).read_text(encoding="utf-8"))

result = lua.execute(r'''
local out, fails = {}, 0
local function check(name, ok, info)
    if not ok then fails = fails + 1 end
    out[#out + 1] = string.format("%s  %s%s", ok and "ok  " or "FAIL", name, info and ("  " .. info) or "")
end
local function near(a, b, eps) return math.abs(a - b) <= (eps or 1e-6) end
local D, R = SprayDroneDrones, SprayDroneRoute

-- ------------------------------------------------------------------ pohled dronu
local root = { numDrones = 2, droneIndex = 1, fieldId = 7, state = 0, droneFillLevel = 11 }
root.drones = { root }
root.drones[2] = D.createView(root, 2)
local vehicle = { spec_test = root }
local view = root.drones[2]
check("sdílené pole se čte z kořene", view.fieldId == 7)
view.fieldId = 9
check("zápis sdíleného pole jde do kořene", root.fieldId == 9 and rawget(view, "fieldId") == nil)
check("per-drone pole dronu 2 je nil, ne hodnota dronu 1", view.droneFillLevel == nil)
view.droneFillLevel = 3
check("per-drone pole se drží v pohledu", view.droneFillLevel == 3 and root.droneFillLevel == 11)
local before = WARNINGS or 0
view.neznamePole = 1
check("neklasifikované pole varuje", (WARNINGS or 0) == before + 1)

local seen = {}
local function probe(self, mark)
    local s = self.spec_test
    seen[#seen + 1] = { mark = mark, fill = s.droneFillLevel, field = s.fieldId, index = D.getIndex(self) }
    return s.droneFillLevel
end
check("runAs dosadí dron 2", D.runAs(vehicle, 2, probe, "a") == 3 and vehicle.spec_test == root)
check("runAs dron 1 nepřepíná", D.runAs(vehicle, 1, probe, "b") == 11 and vehicle.spec_test == root)
check("runAs pro neexistující dron vrací nil", D.runAs(vehicle, 3, probe, "c") == nil)
local nested = D.runAs(vehicle, 2, function(self)
    local inner = D.runAs(self, 1, probe, "d")
    return inner + self.spec_test.droneFillLevel
end)
check("vnořený runAs (2 -> 1) a obnovení kontextu", nested == 14 and vehicle.spec_test == root)
local ok = pcall(D.runAs, vehicle, 2, function() error("chyba v dronu 2") end)
D.restoreRoot(vehicle)
check("po výjimce v dronu 2 vrátí restoreRoot kontext", (not ok) and vehicle.spec_test == root)
local count = 0
D.forEach(vehicle, function() count = count + 1 end)
check("forEach pro dva drony", count == 2)
local single = { numDrones = 1, droneIndex = 1 }
single.drones = { single }
local v1 = { spec_test = single }
count = 0
D.forEach(v1, function(self) count = count + 1; assert(self.spec_test == single) end)
check("forEach pro jeden dron nepřepíná", count == 1)

-- ------------------------------------------------------------------ dělení legů
-- pole 12 řádků po 100 m, boustrophedon od domova (0, 0): řádek i ve výšce z = 9 * i
local function makeLegs(rows, length)
    local legs = {}
    for i = 0, rows - 1 do
        local z = 9 * i
        if i % 2 == 0 then
            legs[#legs + 1] = { x1 = 0, z1 = z, x2 = length, z2 = z, len = length }
        else
            legs[#legs + 1] = { x1 = length, z1 = z, x2 = 0, z2 = z, len = length }
        end
    end
    return legs
end
local opts = { homes = { { x = 0, z = -3 }, { x = 0, z = 2 } }, batchLength = 1500, spraySpeed = 7, cruiseSpeed = 10, serviceTime = 60,
    minSplit = 60, requester = 1 }
local legs = makeLegs(12, 100)
local split = R.splitLegs(legs, 2, opts)
local total = 0
for _, l in ipairs(legs) do total = total + l.len end
local sum = 0
for _, l in ipairs(split[1]) do sum = sum + l.len end
for _, l in ipairs(split[2]) do sum = sum + l.len end
check("součet délek obou seznamů = původní", near(sum, total))
check("oba drony dostanou práci", #split[1] > 0 and #split[2] > 0, string.format("%d + %d legů", #split[1], #split[2]))
check("12 stejných řádků se rozdělí napůl", #split[1] == 6 and #split[2] == 6)
local seenZ, overlap = {}, false
for _, l in ipairs(split[1]) do seenZ[l.z1] = true end
for _, l in ipairs(split[2]) do overlap = overlap or seenZ[l.z1] == true end
check("žádný řádek není u obou", not overlap)
check("dron 2 začíná na vzdáleném konci pole", split[2][1].z1 == 99 and split[1][1].z1 == 0)
check("dron 2 má úseky obrácené", near(split[2][1].x1, 0) and near(split[2][1].x2, 100))
local continuous = true
for i = 2, #split[2] do
    local a, b = split[2][i - 1], split[2][i]
    continuous = continuous and near(a.x2, b.x1) and math.abs(a.z2 - b.z1) <= 9 + 1e-6
end
check("obrácený seznam je souvislý (konec legu u začátku dalšího)", continuous)

local single = R.splitLegs(legs, 1, opts)
check("n = 1: všechno žadateli", #single[1] == 12 and #single[2] == 0)
opts.requester = 2
local single2 = R.splitLegs(legs, 1, opts)
check("n = 1: všechno žadateli 2", #single2[2] == 12 and #single2[1] == 0)
opts.requester = 1
local tiny = R.splitLegs(makeLegs(3, 15), 2, opts)
check("práce pod minSplit jde celá žadateli", #tiny[1] == 3 and #tiny[2] == 0)
local one = R.splitLegs(makeLegs(1, 500), 2, opts)
check("jediný leg se nedělí", #one[1] == 1 and #one[2] == 0)
local uneven = makeLegs(12, 100)
for i = 1, 4 do uneven[i].len, uneven[i].x2 = 400, 400 end
local split3 = R.splitLegs(uneven, 2, opts)
local s1, s2 = 0, 0
for _, l in ipairs(split3[1]) do s1 = s1 + l.len end
for _, l in ipairs(split3[2]) do s2 = s2 + l.len end
check("delší začátek: dron 1 dostane méně legů, vyrovná se délka", #split3[1] < #split3[2] and math.abs(s1 - s2) < 450,
    string.format("%d legů / %.0f m a %d legů / %.0f m", #split3[1], s1, #split3[2], s2))

-- simulace: oba drony postupují stejnou rychlostí, po dávkách se rozdělení znovu počítá z toho, co zbylo
local remaining = makeLegs(40, 200)
local done = { 0, 0 }
local rounds = 0
while #remaining > 0 and rounds < 50 do
    rounds = rounds + 1
    local sp = R.splitLegs(remaining, 2, opts)
    local take1 = math.min(2, #sp[1])
    local take2 = math.min(2, #sp[2])
    done[1] = done[1] + take1
    done[2] = done[2] + take2
    -- ubrat odevzdané legy: dron 1 prvních take1 ze začátku, dron 2 prvních take2 ze svého (obráceného) seznamu = konec zbytku
    local nextRemaining = {}
    local first = take1 + 1
    local last = #remaining - take2
    for i = first, last do nextRemaining[#nextRemaining + 1] = remaining[i] end
    remaining = nextRemaining
end
check("vyvažování konverguje, práce se vyčerpá", #remaining == 0, string.format("%d kol, dron 1: %d legů, dron 2: %d legů", rounds, done[1], done[2]))
check("oba drony odvedly podobný díl", math.abs(done[1] - done[2]) <= 4)

-- ------------------------------------------------------------------ rezervace
R.reserved = { { 0, 0, 100, 0 } }
R.reservedMargin = 5.5
check("bod na rezervovaném úseku je rezervovaný", R.isReserved(50, 0))
check("bod o rozteč řádku dál není rezervovaný", not R.isReserved(50, 9))
check("bod za koncem úseku v toleranci je rezervovaný", R.isReserved(103, 0))
R.reserved = nil
check("bez rezervací nic není rezervované", not R.isReserved(50, 0))
local parts = {}
R.reserved, R.reservedMargin = { { 40, 0, 60, 0 } }, 3
R.appendParts(parts, 0, 0, 100, 0, function() return true end)
R.reserved = nil
local lens = 0
for _, p in ipairs(parts) do lens = lens + p.len end
check("appendParts vynechá rezervovaný kus řádku", #parts == 2 and lens < 100 - 20, string.format("%d částí, %.0f m", #parts, lens))

out[#out + 1] = fails == 0 and "VŠE V POŘÁDKU" or (fails .. " SELHALO")
return table.concat(out, "\n")
''')
print(result)
sys.exit(0 if "VŠE V POŘÁDKU" in result else 1)
