# Ruční zkouška dusíku a pH z Precision Farming bez hry (LuaJIT/lupa): python tools/test_pf.py
# 1. SprayDroneScanMap.encodePF / decodePF: obrat, ořez, nil, vejde se do PF_BITS eventu.
# 2. readPF s falešnou mapou PF (průměr z executeGet, interpolace mezi stavy, chybějící data, dusík jen nad plodinou, pH se ze skenu
#    nečte), getTargetNitrogen.
# 3. unpack, getSummary a formatSummary s PF (pH ze starých map se ignoruje).
# 4. SprayDroneStation.getSpotSelector (vytažený ze zdroje): vápno podle pH čteného živě jen u odebraných vzorků (coverMap), bez PF
#    vanilla vápno přímo z pole; hnojivo podle cíle, záloha bez PF, ošetřené buňky.
import re
import sys
from pathlib import Path
from lupa import luajit21

lua = luajit21.LuaRuntime(unpack_returned_tuples=True)
scripts = Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "scripts"

lua.execute('''
g_currentModName = "FS25_SprayDroneTrailer"
g_currentModDirectory = ""
source = function() end
math.clamp = function(v, lo, hi) return math.max(lo, math.min(hi, v)) end
unpack = unpack or table.unpack
MathUtil = { vector2Length = function(x, z) return math.sqrt(x * x + z * z) end }
Logging = { warning = function() end, info = function() end }
FruitType = { UNKNOWN = 0 }
DensityCoordType = { POINT_POINT_POINT = 1 }
g_terrainNode = 1

-- falešný DensityMapModifier: executeGet vrací součet a počet pixelů podle tabulky FAKE_DENSITY[mapId]
FAKE_DENSITY = {}
DensityMapModifier = {}
DensityMapModifier.__index = DensityMapModifier
function DensityMapModifier.new(mapId) return setmetatable({ mapId = mapId }, DensityMapModifier) end
function DensityMapModifier:setParallelogramWorldCoords() end
function DensityMapModifier:executeGet()
    local d = FAKE_DENSITY[self.mapId]
    if d == nil then return nil end
    return d[1], d[2]
end

addModEventListener = function() end
Utils = { appendedFunction = function(a, b) return b end }
FieldManager = {}
FSBaseMission = {}
FRUIT_AT = {}
FSDensityMapUtil = { getFruitTypeIndexAtWorldPos = function(x, z) return FRUIT_AT.index end }
-- vanilla stav pole (vápno bez PF)
FAKE_FIELD = { limeLevel = 1 }
FieldState = { new = function() return { update = function(self) self.limeLevel = FAKE_FIELD.limeLevel end } end }
-- odebrané vzorky PF: SAMPLED[farmId] = true; COVER_ERROR = getIsUncoveredAtPos hází chybu
SAMPLED = {}

-- PF jako ve hře: dusík = (stav - 1) x 5 kg/ha, pH = 4,5 + (stav - 1) x 0,125
FAKE_PF = {
    nitrogenMap = {
        bitVectorMap = 11, firstChannel = 0, numChannels = 6, amountPerState = 5,
        getNitrogenValueFromInternalValue = function(self, v) return math.max(v - 1, 0) * 5 end,
        fruitTypeIndexToFruitRequirement = { [24] = { averageTargetLevel = 13 }, [25] = 2, [26] = { } },
        fruitRequirements = { [2] = { averageTargetLevel = 7 } },
    },
    pHMap = {
        bitVectorMap = 12, firstChannel = 0, numChannels = 5,
        getPhValueFromInternalValue = function(self, v) return 4.5 + math.max(v - 1, 0) * 0.125 end,
    },
    coverMap = {
        getIsUncoveredAtPos = function(self, x, z, farmId)
            if COVER_ERROR then error("chyba PF") end
            return SAMPLED[farmId] == true
        end,
    },
}
SprayDroneStation = {
    getPrecisionFarming = function() return FAKE_PF_ACTIVE and FAKE_PF or nil end,
    getPFMapLayer = function(map) return map.bitVectorMap, map.firstChannel, map.numChannels end,
}
FAKE_PF_ACTIVE = true
''')

lua.execute((scripts / "SprayDroneScanMap.lua").read_text(encoding="utf-8"))

station = (scripts / "SprayDroneStation.lua").read_text(encoding="utf-8")
match = re.search(r"^function SprayDroneStation\.getSpotSelector\(sprayType, farmId\).*?^end\n", station, re.S | re.M)
if match is None:
    sys.exit("getSpotSelector ve zdroji nenalezen")
lua.execute(match.group(0))

result = lua.execute(r'''
local out, fails = {}, 0
local function check(name, ok, info)
    if not ok then fails = fails + 1 end
    out[#out + 1] = string.format("%s  %s%s", ok and "ok  " or "FAIL", name, info and ("  " .. info) or "")
end
local function near(a, b, eps) return a ~= nil and math.abs(a - b) <= (eps or 1e-6) end
local M = SprayDroneScanMap

-- ------------------------------------------------------------------ encodePF / decodePF
local n, ph, t = M.decodePF(M.encodePF(25, 6.3, 65))
check("obrat dusík/pH/cíl", n == 25 and near(ph, 6.3) and t == 65, string.format("%s %s %s", tostring(n), tostring(ph), tostring(t)))
n, ph, t = M.decodePF(M.encodePF(nil, 6.3, nil))
check("jen pH", n == nil and near(ph, 6.3) and t == nil)
n, ph, t = M.decodePF(M.encodePF(40, nil, 55))
check("jen dusík a cíl", n == 40 and ph == nil and t == 55)
check("bez dusíku a pH je nil", M.encodePF(nil, nil, 65) == nil)
check("decodePF(nil) vrací samé nil", select("#", M.decodePF(nil)) == 3 and M.decodePF(nil) == nil)
n, ph, t = M.decodePF(M.encodePF(9999, 99, 9999))
check("ořez na maxima", n == M.PF_NITROGEN_MAX and near(ph, M.PF_PH_MAX / 10) and t == M.PF_TARGET_MAX * M.PF_TARGET_STEP)
check("největší hodnota se vejde do PF_BITS", M.encodePF(9999, 99, 9999) < 2 ^ M.PF_BITS)
n, ph, t = M.decodePF(M.encodePF(0.4, 0.04, 2))
check("nula = bez údaje", n == nil and ph == nil and t == nil, string.format("%s %s %s", tostring(n), tostring(ph), tostring(t)))
check("cíl se zaokrouhlí na pětikilový krok", select(3, M.decodePF(M.encodePF(30, 6, 66))) == 65)
local seen = {}
local clash = false
for a = 0, 60, 7 do
    for b = 40, 80, 5 do
        for c = 0, 100, 25 do
            local v = M.encodePF(a + 1, b / 10, c)
            if seen[v] then clash = true end
            seen[v] = true
        end
    end
end
check("různé trojice dávají různé hodnoty", not clash)

-- ------------------------------------------------------------------ getTargetNitrogen
FRUIT_AT.index = 24
check("cíl z požadavku plodiny", M.getTargetNitrogen(FAKE_PF, 0, 0) == 65)
FRUIT_AT.index = 25
check("požadavek daný indexem do fruitRequirements", M.getTargetNitrogen(FAKE_PF, 0, 0) == 35)
FRUIT_AT.index = 26
check("požadavek bez averageTargetLevel = nil", M.getTargetNitrogen(FAKE_PF, 0, 0) == nil)
FRUIT_AT.index = 99
check("neznámá plodina = nil", M.getTargetNitrogen(FAKE_PF, 0, 0) == nil)
FRUIT_AT.index = 0
check("bez plodiny = nil", M.getTargetNitrogen(FAKE_PF, 0, 0) == nil)
FRUIT_AT.index = nil
check("bez hodnoty z mapy = nil", M.getTargetNitrogen(FAKE_PF, 0, 0) == nil)
FRUIT_AT.index = 24
check("bez nitrogenMap = nil", M.getTargetNitrogen({}, 0, 0) == nil)

-- ------------------------------------------------------------------ readPF
local map = { originX = 0, originZ = 0, cellSize = 10, nx = 4, nz = 4 }
local function read(nsum, npix, phsum, phpix)
    FAKE_DENSITY[11] = nsum ~= nil and { nsum, npix } or nil
    FAKE_DENSITY[12] = phsum ~= nil and { phsum, phpix } or nil
    return M.decodePF(M.readPF(map, 1))
end
FRUIT_AT.index = 24
n, ph, t = read(600, 100, 1500, 100)
check("průměr 6 stavů = 25 kg N/ha; pH se ze skenu nečte", n == 25 and ph == nil, string.format("%s %s", tostring(n), tostring(ph)))
check("cílový dusík se ukládá se skenem", t == 65)
n = read(650, 100, 1448, 100)
check("necelý průměr se interpoluje mezi stavy (6,5 = 27,5 = 28 kg)", n == 28, tostring(n))
n = read(0, 100, 0, 100)
check("průměr 0 = bez údaje", n == nil)
n = read(600, 0, 1500, 0)
check("nula pixelů = bez údaje", n == nil)
n, ph, t = read(nil, nil, 1500, 100)
check("chybějící vrstva dusíku = buňka bez údaje PF", n == nil and ph == nil and t == nil)
FRUIT_AT.index = 0
check("bez plodiny se dusík nečte (holá půda)", M.readPF(map, 1) == nil)
FRUIT_AT.index = 24
FAKE_PF_ACTIVE = false
check("bez PF vrací readPF nil", M.readPF(map, 1) == nil)
FAKE_PF_ACTIVE = true
local backup = FAKE_PF.nitrogenMap.getNitrogenValueFromInternalValue
FAKE_PF.nitrogenMap.getNitrogenValueFromInternalValue = function() error("chyba PF") end
FAKE_DENSITY[11] = { 600, 100 }
n = M.decodePF(M.readPF(map, 1))
check("chyba v převodu dusíku nezhodí sken", n == nil)
FAKE_PF.nitrogenMap.getNitrogenValueFromInternalValue = backup

-- ------------------------------------------------------------------ unpack a souhrn
local function cell(extra)
    local c = { weedShare = 0, weedState = 0, sprayLevel = 1, limeLevel = 1, growthState = 1, fruitTypeIndex = 0, stoneLevel = 0 }
    for k, v in pairs(extra or {}) do c[k] = v end
    return M.encode(c)
end
local sm = { values = {}, pf = {}, times = {}, treated = {}, treatedKinds = {}, inside = {}, numInside = 5, updated = 0, cellSize = 10, fieldId = 1 }
sm.values[1], sm.pf[1] = cell(), M.encodePF(25, 6.1, 65)
sm.values[2], sm.pf[2] = cell(), M.encodePF(35, 6.4, 65)
sm.values[3], sm.pf[3] = cell(), M.encodePF(nil, 6.7, nil)
sm.values[4] = cell()
local c = M.unpack(sm, 1)
check("unpack nese dusík a cíl, pH ze staré mapy ignoruje", c.nitrogen == 25 and c.ph == nil and c.targetNitrogen == 65)
c = M.unpack(sm, 4)
check("unpack buňky bez PF", c ~= nil and c.nitrogen == nil and c.ph == nil and c.targetNitrogen == nil)
check("unpack nenaskenované buňky je nil", M.unpack(sm, 5) == nil)
local s = M.getSummary(sm)
check("souhrn: pfCells jen s dusíkem", s.pfCells == 2 and s.scanned == 4)
check("souhrn: dusík průměr/min/max", near(s.avgNitrogen, 30) and s.minNitrogen == 25 and s.maxNitrogen == 35)
check("souhrn: bez pH", s.avgPh == nil and s.minPh == nil)
local text = M.formatSummary(sm)
check("formatSummary zmiňuje PF", text:find("PF 2 buněk", 1, true) ~= nil and text:find("pH", 1, true) == nil, text)
sm.pf = {}
s = M.getSummary(sm)
check("souhrn bez PF nemá průměry", s.pfCells == 0 and s.avgNitrogen == nil)
check("formatSummary bez PF PF nezmiňuje", M.formatSummary(sm):find("PF", 1, true) == nil)

-- ------------------------------------------------------------------ výběr buněk
local FARM = 3
local lime = SprayDroneStation.getSpotSelector({ isLime = true }, FARM)
local fert = SprayDroneStation.getSpotSelector({ isFertilizer = true }, FARM)
local herb = SprayDroneStation.getSpotSelector({ isHerbicide = true }, FARM)
local function pfCell(extra)
    local d = { weedShare = 0, weedState = 0, sprayLevel = 2 }
    for k, v in pairs(extra or {}) do d[k] = v end
    return d
end
local cellMap = { originX = 0, originZ = 0, cellSize = 10, nx = 4, nz = 4 }
-- pH v buňce teď (PF stav = 1 + (pH - 4,5) / 0,125, průměr přes 100 pixelů)
local function soilPh(value)
    FAKE_DENSITY[12] = { (1 + (value - 4.5) / 0.125) * 100, 100 }
end
local function limeAt(c, kinds)
    return lime(c, kinds or 0, cellMap, 1)
end
SAMPLED[FARM] = true
soilPh(6.1)
check("vápno: pH 6,1 pod prahem", limeAt(pfCell()))
soilPh(6.2)
check("vápno: pH 6,2 pod prahem", limeAt(pfCell()))
soilPh(6.3)
check("vápno: pH 6,3 stačí", not limeAt(pfCell()))
soilPh(7.0)
check("vápno: pH 7,0 stačí", not limeAt(pfCell()))
soilPh(5.5)
check("vápno: rozhoduje pH teď, ne sken (ani nenaskenovaná buňka)", limeAt(nil))
SAMPLED[FARM] = nil
check("vápno: bez odebraného vzorku se nevápní", not limeAt(pfCell()))
SAMPLED[FARM + 1] = true
check("vápno: vzorky jiné farmy neplatí", not limeAt(pfCell()))
SAMPLED[FARM + 1] = nil
SAMPLED[FARM] = true
COVER_ERROR = true
check("vápno: chyba coverMap = bez vzorku", not limeAt(pfCell()))
COVER_ERROR = nil
FAKE_DENSITY[12] = nil
check("vápno: vzorek bez dat pH = nevápní", not limeAt(pfCell()))
soilPh(5.5)
check("vápno: ošetřená buňka se přeskočí", not limeAt(pfCell(), M.TREAT_LIME))
check("vápno: ošetření jiným druhem nevadí", limeAt(pfCell(), M.TREAT_FERTILIZER))
check("vápno: bez mapy a indexu nic", not lime(pfCell(), 0))
FAKE_PF_ACTIVE = false
lime = SprayDroneStation.getSpotSelector({ isLime = true }, FARM)
FAKE_FIELD.limeLevel = 0
check("vápno bez PF: vanilla vápno 0 z pole chce vápno", limeAt(pfCell()))
FAKE_FIELD.limeLevel = 1
check("vápno bez PF: vanilla vápno 1 nechce", not limeAt(pfCell()))
FAKE_PF_ACTIVE = true

check("hnojivo: dusík 25 z 65", fert(pfCell({ nitrogen = 25, targetNitrogen = 65 }), 0))
check("hnojivo: dusík 54 z 65 (pod cíl - 10)", fert(pfCell({ nitrogen = 54, targetNitrogen = 65 }), 0))
check("hnojivo: dusík 55 z 65 stačí (tolerance 10)", not fert(pfCell({ nitrogen = 55, targetNitrogen = 65 }), 0))
check("hnojivo: dusík nad cílem stačí", not fert(pfCell({ nitrogen = 90, targetNitrogen = 65 }), 0))
check("hnojivo: dusík bez cíle (bez plodiny) padá zpět na vanilla úroveň, plné stačí", not fert(pfCell({ nitrogen = 10, sprayLevel = 2 }), 0))
check("hnojivo: dusík bez cíle, nehnojeno", fert(pfCell({ nitrogen = 10, sprayLevel = 0 }), 0))
check("hnojivo bez PF: sprayLevel 1 chce hnojit", fert(pfCell({ sprayLevel = 1 }), 0))
check("hnojivo bez PF: sprayLevel 2 nechce", not fert(pfCell({ sprayLevel = 2 }), 0))
check("hnojivo: ošetřená buňka se přeskočí", not fert(pfCell({ nitrogen = 25, targetNitrogen = 65 }), M.TREAT_FERTILIZER))

check("herbicid ignoruje PF", herb(pfCell({ weedShare = 0.5, nitrogen = 90, ph = 7 }), 0) and not herb(pfCell({ nitrogen = 10, ph = 5 }), 0))
check("přípravek bez ošetření výběr nemá", SprayDroneStation.getSpotSelector({ isScan = true }) == nil and SprayDroneStation.getSpotSelector({}) == nil)

return { out = out, fails = fails }
''')

for line in result["out"].values():
    print(line)
fails = result["fails"]
print(f"\n{'OK' if fails == 0 else 'CHYB: ' + str(fails)}")
sys.exit(1 if fails else 0)
