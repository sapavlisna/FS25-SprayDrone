# Ruční zkouška kufru skenovacího dronu bez hry (LuaJIT/lupa): python tools/test_case.py
# SprayDroneCase: budova farmy (specializace, kryté plochy, vzdálenost), zdroj nabíjení, nabíjení bez nafty, zátěž centrály vleku,
# důvod konce mise bez zdroje; SprayDroneStation: plán trasy kufru (nafta = zdroj), odmítnutí skenovacího dronu na plošině vleku.
import sys
from pathlib import Path
from lupa import luajit21

scripts = Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "scripts"
lua = luajit21.LuaRuntime(unpack_returned_tuples=True)
lua.globals().SCRIPTS = str(scripts)

result = lua.execute(r'''
local out, fails = {}, 0
local function check(name, ok, info)
    if not ok then fails = fails + 1 end
    out[#out + 1] = string.format("%s  %s%s", ok and "ok  " or "FAIL", name, info ~= nil and ("  " .. tostring(info)) or "")
end
local function near(a, b, eps) return a ~= nil and math.abs(a - b) <= (eps or 1e-6) end

local function dummy()
    return setmetatable({}, { __index = function(t, k) local v = dummy(); rawset(t, k, v); return v end, __call = function() end })
end
setmetatable(_G, { __index = function(t, k) local v = dummy(); rawset(t, k, v); return v end })
unpack = unpack or table.unpack
math.clamp = function(v, lo, hi) return math.max(lo, math.min(hi, v)) end
MathUtil = { vector2Length = function(x, z) return math.sqrt(x * x + z * z) end,
    vector3Length = function(x, y, z) return math.sqrt(x * x + y * y + z * z) end }
Logging = { info = function() end, warning = function() end, xmlWarning = function() end }
CollisionFlag = { STATIC_OBJECT = 1, TREE = 2, BUILDING = 4 }
FillType = { UNKNOWN = 0, WATER = 1, DIESEL = 2 }
g_time = 1000
g_currentModDirectory = ""
SprayDroneDebug = { ENABLED = false }
g_i18n = { getText = function(_, key) return key end }
-- uzly: id -> { x, z }
NODES = {}
getWorldTranslation = function(node) local n = NODES[node]; return n[1], 0, n[2] end
entityExists = function(node) return NODES[node] ~= nil end
local LOAD = { ["SprayDroneRoute.lua"] = true, ["SprayDroneMixer.lua"] = true, ["SprayDroneFields.lua"] = true,
    ["SprayDroneDrones.lua"] = true, ["SprayDroneService.lua"] = true, ["SprayDroneCase.lua"] = true,
    ["SprayDronePadDrone.lua"] = true }
source = function(path)
    local name = path:match("([^/]+)$")
    if LOAD[name] then
        dofile(SCRIPTS .. "/" .. name)
    end
end
dofile(SCRIPTS .. "/SprayDroneStation.lua")
local S, C = SprayDroneStation, SprayDroneCase
SprayDroneSound = { noteAction = function() end }
S.getFillSource = function() return { fillType = FillType.WATER } end

-- ------------------------------------------------------------------ budovy
NODES.a, NODES.w, NODES.h = { 0, 0 }, { 20, 0 }, { 0, 10 }
local area = { start = "a", width = "w", height = "h" }
check("bod v kryté ploše = 0 m", near(C.getAreaDistance(area, 5, 5), 0))
check("bod 6 m od delší strany", near(C.getAreaDistance(area, 10, 16), 6))
check("bod za rohem: vzdálenost od rohu", near(C.getAreaDistance(area, 23, 14), 5))
check("farmhouse je budova", C.getIsBuilding({ spec_farmhouse = {} }))
check("kůlna s krytou plochou je budova", C.getIsBuilding({ spec_indoorAreas = { areas = { area } } }))
check("plot / cesta bez specializace budovou nejsou", not C.getIsBuilding({ spec_fence = {} }) and not C.getIsBuilding({ spec_indoorAreas = { areas = {} } }))

NODES.shedRoot = { 100, 100 }
local shed = { rootNode = "shedRoot", spec_indoorAreas = { areas = { area } }, getOwnerFarmId = function() return 1 end }
NODES.fenceRoot = { 0, 30 }
local fence = { rootNode = "fenceRoot", spec_fence = {}, getOwnerFarmId = function() return 1 end }
NODES.foreignRoot = { 0, 40 }
local foreign = { rootNode = "foreignRoot", spec_farmhouse = {}, getOwnerFarmId = function() return 2 end }
g_currentMission = { placeableSystem = { placeables = { fence, foreign, shed } }, vehicleSystem = { vehicles = {} },
    accessHandler = { canFarmAccess = function(_, farmId, v) return v.farmId == farmId end } }
check("kůlna do 15 m od kryté plochy (kořen je daleko)", C.findBuilding(10, 24, 1, 15) == shed)
check("plot nenabíjí", C.findBuilding(0, 31, 1, 15) == nil)
check("cizí budova nenabíjí", C.findBuilding(0, 41, 1, 0.5) == nil)

-- ------------------------------------------------------------------ kufr
local function newCase(x, z)
    local spec = { portable = true, batteries = { { charge = 50, slot = 1, drone = 1 } }, batteryCapacity = 100, chargeRate = 2,
        numDrones = 1, isLinked = true, state = S.STATE_PARKED, droneBattery = nil, battery = 0, powerSyncTimer = 0, dirtyFlag = 1,
        generatorRunning = false, numCharging = 0, chargeSource = C.SOURCE_NONE, activeDrones = 1, missionMode = 1, spareCharge = 0,
        dieselFillUnitIndex = 1, droneFillLevel = 0, droneFillType = FillType.UNKNOWN, isScanDrone = true, readyCharge = 95, swapTime = 5000, pumpRate = 0.01, dieselPerSecond = 0.01, routeDirty = false }
    spec.drones = { spec }
    NODES["case" .. x] = { x, z }
    local v = { rootNode = "case" .. x, farmId = 1, id = 7 }
    v[S.SPEC_NAME] = spec
    function v:getOwnerFarmId() return 1 end
    function v:raiseDirtyFlags() end
    function v:raiseActive() end
    function v:getFillUnitFillLevel() return 0 end
    return v, spec
end
local v, spec = newCase(200, 200)
S.updatePower(v, 1000)
check("bez zdroje se nenabíjí", spec.batteries[1].charge == 50 and spec.chargeSource == C.SOURCE_NONE and not spec.generatorRunning)
check("bez zdroje: konec mise STATUS_NO_CHARGE", S.getChargeBlocker(v) == S.STATUS_NO_CHARGE)
local p = S.getPowerParams(v)
check("plán bez zdroje: nafta 0 (noFuel)", p.diesel == 0 and p.dieselPerSecond == 0)

v, spec = newCase(10, 20)
S.updatePower(v, 1000)
check("u kůlny: zdroj budova", spec.chargeSource == C.SOURCE_BUILDING)
check("u kůlny: nabíjí rychlostí nabíječky", near(spec.batteries[1].charge, 52) and spec.generatorRunning, spec.batteries[1].charge)
check("u kůlny: mise pokračuje", S.getChargeBlocker(v) == nil)
p = S.getPowerParams(v)
check("plán se zdrojem: neomezená nafta zdarma", p.diesel == math.huge and p.dieselPerSecond == 0)
spec.batteries[1].slot, spec.droneBattery, spec.battery = 0, 1, 52
S.updatePower(v, 1000)
check("baterie v zaparkovaném dronu v kufru se nabíjí taky", near(spec.batteries[1].charge, 54) and near(spec.battery, 54))
spec.isLinked = false
spec.state = S.STATE_FLYING
S.updatePower(v, 1000)
check("baterie v letícím dronu se nenabíjí", near(spec.batteries[1].charge, 54))

-- ------------------------------------------------------------------ centrála vleku
local trailerSpec = { portable = false, batteries = {}, numDrones = 1 }
trailerSpec.drones = { trailerSpec }
NODES.trailer = { 300, 300 }
local trailer = { rootNode = "trailer", farmId = 1, active = 0 }
trailer[S.SPEC_NAME] = trailerSpec
function trailer:raiseActive() self.active = self.active + 1 end
g_currentMission.vehicleSystem.vehicles = { trailer }
local hasPower = true
S.getHasPower = function(vehicle) return vehicle == trailer and hasPower end
v, spec = newCase(305, 300)
NODES[v.rootNode] = { 305, 300 }
S.updatePower(v, 1000)
check("u běžící centrály vleku: zdroj centrála", spec.chargeSource == C.SOURCE_GENERATOR and near(spec.batteries[1].charge, 52))
check("kufr se centrále hlásí jako zátěž", S.getNumCaseLoads(trailer) == 1 and trailer.active > 0)
g_time = 1000 + C.LOAD_TIMEOUT + 1
check("zátěž po LOAD_TIMEOUT vyprší", S.getNumCaseLoads(trailer) == 0)
hasPower = false
spec.caseSourceTimer = 0
S.updatePower(v, 1000)
check("vypnutá centrála: bez zdroje", spec.chargeSource == C.SOURCE_NONE)
spec.batteries[1].charge = 100
hasPower = true
spec.caseSourceTimer = 0
trailerSpec.caseLoads = nil
S.updatePower(v, 1000)
check("plná baterie centrálu nezatěžuje", S.getNumCaseLoads(trailer) == 0 and not spec.generatorRunning)

-- ------------------------------------------------------------------ plošina vleku a skenovací dron
local padSpec = { numPads = 1, portable = false, secondVariants = {},
    variants = { { name = "M", prefix = "Drone_A_" }, { name = "K", prefix = "Drone_K_", scan = true } } }
local pv = {}
pv[S.SPEC_NAME] = padSpec
check("vlek: dron M jde na plošinu", S.getPadsProblem(pv, { "M" }) == nil)
check("vlek: skenovací K na plošinu nejde (D2)", S.getPadsProblem(pv, { "K" }) == "sdt_pad_unknown")
padSpec.portable = true
padSpec.variants = { { name = "C", prefix = "Drone_C_", scan = true } }
check("kufr: skenovací C ano", S.getPadsProblem(pv, { "C" }) == nil)

return { out = out, fails = fails }
''')

for line in result["out"].values():
    print(line)
fails = result["fails"]
print(f"\n{'OK' if fails == 0 else 'CHYB: ' + str(fails)}")
sys.exit(1 if fails else 0)
