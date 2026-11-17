# Zkouška poolu baterií s dírami bez hry (LuaJIT/lupa): python tools/test_batteries.py
# F4 (docs/PLAN-airasi-kufr.md): baterie jako předměty. SprayDroneStation: proměnný počet baterií (setBatteryCount, addBattery, removeBattery
# i s baterií v dronu a posunem indexů), výměna a vrácení baterie s prázdnými šachtami, počet z uložené hry a změna konfigurace v dílně;
# SprayDroneBatterySlots: kdy jde baterii vložit / vyndat; SprayDroneCase: pool kufru drží nabití dronu po letu (podezření z testu F2).
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
FillType = { UNKNOWN = 0, WATER = 1, DIESEL = 2 }
CollisionFlag = { STATIC_OBJECT = 1, TREE = 2, BUILDING = 4 }
g_time = 1000
g_currentModDirectory = ""
SprayDroneDebug = { ENABLED = false }
g_i18n = { getText = function(_, key) return key end }
NODES = {}
getWorldTranslation = function(node) local n = NODES[node]; return n[1], 0, n[2] end
entityExists = function(node) return NODES[node] ~= nil end
local LOAD = { ["SprayDroneRoute.lua"] = true, ["SprayDroneMixer.lua"] = true, ["SprayDroneFields.lua"] = true,
    ["SprayDroneDrones.lua"] = true, ["SprayDroneService.lua"] = true, ["SprayDroneCase.lua"] = true,
    ["SprayDronePadDrone.lua"] = true, ["SprayDroneBatterySlots.lua"] = true }
source = function(path)
    local name = path:match("([^/]+)$")
    if LOAD[name] then
        dofile(SCRIPTS .. "/" .. name)
    end
end
dofile(SCRIPTS .. "/SprayDroneStation.lua")
local S, B, C = SprayDroneStation, SprayDroneBatterySlots, SprayDroneCase
SprayDroneSound = { noteAction = function() end }
SprayDroneRelaySlots = { charge = function() end, getNumCharging = function() return 0 end }

-- vlek se 6 šachtami, typ baterií M, kapacita 100 s; drony jako pohledy jako ve hře (SprayDroneDrones.createView)
local function newTrailer(numDrones)
    local spec = { portable = false, batteries = {}, batteryCapacity = 100, numBatterySlots = 6, batteryVariant = "M", batteryConfigCount = 3,
        dirtyFlag = 1, readyCharge = 95, swapTime = 5000, batteryParents = { 1 }, batteryShown = { true }, batteryMoves = {},
        numDrones = numDrones or 1, batterySlots = { nodes = {}, spawning = false } }
    spec.drones = { spec }
    local v = { rootNode = "trailer", id = 3, unfolded = true }
    v[S.SPEC_NAME] = spec
    for d = 2, spec.numDrones do
        spec.drones[d] = SprayDroneDrones.createView(spec, d)
    end
    for d = 1, spec.numDrones do
        local ds = spec.drones[d]
        ds.hasDrone, ds.isLinked, ds.state, ds.missionActive, ds.isSwapping = true, true, S.STATE_PARKED, false, false
        ds.droneBattery, ds.battery, ds.routeDirty, ds.unfold = nil, 0, false, 1
    end
    function v:raiseDirtyFlags() end
    function v:raiseActive() end
    function v:getIsUnfolded() return self.unfolded end
    return v, spec
end
local function put(spec, charge, slot) table.insert(spec.batteries, { charge = charge, slot = slot, drone = 1 }) end

-- ------------------------------------------------------------------ počet poolu
local v, spec = newTrailer()
S.setBatteryCount(v, 4)
check("setBatteryCount doplní plné bez šachty", #spec.batteries == 4 and spec.batteries[4].charge == 100 and spec.batteries[4].slot == -1)
check("setBatteryCount srovná modely znovu", next(spec.batteryParents) == nil)
S.setBatteryCount(v, 9)
check("setBatteryCount nejvýš počet šachet", #spec.batteries == 6)
S.setBatteryCount(v, 0)
check("setBatteryCount 0 = bez baterií", #spec.batteries == 0)

-- ------------------------------------------------------------------ vyndání ze šachty s baterií v dronu (posun indexů)
v, spec = newTrailer()
put(spec, 80, 1); put(spec, 60, 2); put(spec, 50, 0)
spec.droneBattery, spec.battery = 3, 35
check("baterie v šachtě 2 je #2", S.getBatteryInSlot(v, 2) == 2)
local charge = S.removeBattery(v, 1)
check("vyndaná ze šachty vrací své nabití", charge == 80 and #spec.batteries == 2)
check("dron drží dál svou baterii (index posunutý)", spec.droneBattery == 2 and spec.batteries[2].slot == 0 and spec.battery == 35)
check("šachta 1 je prázdná, šachta 2 obsazená", S.getBatteryInSlot(v, 1) == nil and S.getBatteryInSlot(v, 2) == 1)
check("trasa se přepočítá (rezerva baterií)", spec.routeDirty == true)

-- vyndání z dronu: nabití z dronu (pool má stará data ze vzletu)
charge = S.removeBattery(v, 2)
check("vyndaná z dronu nese nabití dronu, ne pool", charge == 35 and spec.droneBattery == nil and spec.battery == 0 and #spec.batteries == 1)

-- vložení: první volná šachta
local slot = S.getFreeBatterySlot(v)
local k = S.addBattery(v, 70, slot)
check("vložená jde do první volné šachty", slot == 1 and k == 2 and S.getBatteryInSlot(v, 1) == 2)

-- ------------------------------------------------------------------ výměna a vrácení s dírami
v, spec = newTrailer()
put(spec, 40, 5); put(spec, 98, 3)
spec.state = S.STATE_SERVICING
check("výměna: z děravých šachet vezme nejnabitější", S.swapBattery(v) == true and spec.droneBattery == 2 and spec.battery == 98)
spec.battery = 20
S.unloadDroneBattery(v)
check("vrácení: vybitá do první volné šachty", spec.batteries[2].slot == 1 and spec.batteries[2].charge == 20)
check("výměna bez nabité baterie čeká (swapPending)", S.swapBattery(v) == false and spec.swapPending == true and spec.droneBattery == nil)
v, spec = newTrailer()
check("výměna bez baterií čeká, nespadne", S.swapBattery(v) == false and spec.swapPending == true)

-- ------------------------------------------------------------------ vložit / vyndat (SprayDroneBatterySlots)
v, spec = newTrailer()
put(spec, 90, 1); put(spec, 30, 0)
spec.droneBattery, spec.battery = 2, 30
check("vložit M do volné šachty", B.getPutProblem(v, "M", 2) == nil and B.getPutProblem(v, "M", nil) == nil)
check("vložit S do vleku s M nejde", B.getPutProblem(v, "S", 2) == "sdt_batteryslot_wrongSize")
check("vložit do obsazené šachty nejde", B.getPutProblem(v, "M", 1) == "sdt_batteryslot_occupied")
v.unfolded = false
check("složený vlek: vložit ani vyndat nejde", B.getPutProblem(v, "M", 2) == "sdt_batteryslot_folded" and B.getTakeProblem(v, 1) == "sdt_batteryslot_folded")
v.unfolded = true
for i = 3, 6 do put(spec, 100, i) end
check("plno i s baterií v dronu (6 šachet, 6 baterií)", B.getPutProblem(v, "M", nil) == "sdt_batteryslot_full")
check("vyndat ze šachty 1", B.getTakeProblem(v, 1) == nil)
check("vyndat z prázdné šachty 2 nejde", B.getTakeProblem(v, 2) == "sdt_batteryslot_empty")
local droneTarget = B.getDroneTarget(1)
check("vyndat z dronu doma jde", B.getTargetBattery(v, droneTarget) == 2 and B.getTakeProblem(v, droneTarget) == nil)
spec.state, spec.isLinked = S.STATE_FLYING, false
check("vyndat z letícího dronu nejde", B.getTakeProblem(v, droneTarget) == "sdt_batteryslot_droneBusy")
check("ze šachty za letu dronu jde", B.getTakeProblem(v, 1) == nil)
spec.state, spec.isLinked, spec.missionActive = S.STATE_PARKED, true, true
check("vyndat z dronu v misi nejde", B.getTakeProblem(v, droneTarget) == "sdt_batteryslot_droneBusy")
spec.missionActive = false
spec.batteryMoves[1] = {}
check("při přenosu baterie nejde vyndat", B.getTakeProblem(v, 1) == "sdt_batteryslot_busy")
spec.batteryMoves = {}
-- ladicí batteryTake (hra 2026-10-29: Max 10/10, „batteryTake 2“ hlásil prázdnou šachtu: idiom a and nil or x)
local dt, dp = B.getDebugTake(v, "1")
check("batteryTake 1: plná šachta jde vyndat", dt == 1 and dp == nil, tostring(dp))
dt, dp = B.getDebugTake(v, "")
check("batteryTake bez čísla: první obsazená šachta", dt == 1 and dp == nil, tostring(dp))
dt, dp = B.getDebugTake(v, "d1")
check("batteryTake d1: baterie z dronu", dt == droneTarget and dp == nil, tostring(dp))
dt, dp = B.getDebugTake(v, "2")
check("batteryTake 2: prázdná šachta hlásí empty", dt == 2 and dp == "sdt_batteryslot_empty", tostring(dp))
spec.batterySlots.spawning = true
check("během výroby předmětu nejde vyndat další", B.getTakeProblem(v, 1) == "sdt_batteryslot_busy")

-- dva drony: baterie v dronu 2, vyndá se baterie před ní
v, spec = newTrailer(2)
local d2 = spec.drones[2]
put(spec, 10, 1); put(spec, 20, 0); put(spec, 30, 2)
spec.batteries[2].drone = 2
d2.droneBattery, d2.battery = 2, 15
S.removeBattery(v, 1)
check("dron 2: index baterie se posune", d2.droneBattery == 1 and B.getTargetBattery(v, B.getDroneTarget(2)) == 1)
check("dron 2: vyndaná z dronu 2 nese jeho nabití", S.removeBattery(v, 1) == 15 and d2.droneBattery == nil and #spec.batteries == 1)

-- ------------------------------------------------------------------ uložená hra: počet z uložení, změna konfigurace v dílně
local function savegame(entries, batteryConfig)
    local values = { ["s#batteryConfig"] = batteryConfig }
    for i, e in ipairs(entries) do
        values[string.format("s.battery(%d)#level", i - 1)] = e[1]
        values[string.format("s.battery(%d)#slot", i - 1)] = e[2]
    end
    local xml = {}
    function xml:getValue(key, default) local value = values[key]; if value == nil then return default end return value end
    function xml:iterate(key, fn)
        if key ~= "s.battery" then return end
        for i = 1, #entries do fn(i, string.format("s.battery(%d)", i - 1)) end
    end
    return { xmlFile = xml, key = "x" }
end
S.loadDroneSave = function() end
S.applyMissionMode = function() end
S.resumeMissionAfterLoad = function() end
S.MOD_NAME = "m"
local function load(entries, batteryConfig, configNow)
    local lv, ls = newTrailer()
    ls.batteryConfigCount = configNow
    ls.flightAreas, ls.activeDrones = {}, 1
    for k = 1, configNow do put(ls, 100, k) end
    local sg = savegame(entries, batteryConfig)
    local inner = sg.xmlFile
    -- loadFromSavegame skládá klíč savegame.key .. "." .. MOD_NAME .. ".sprayDroneStation"; zkrátit na "s"
    sg.xmlFile = { getValue = function(_, key, default) return inner:getValue(key:gsub("^x%.m%.sprayDroneStation", "s"), default) end,
        iterate = function(_, key, fn) return inner:iterate(key:gsub("^x%.m%.sprayDroneStation", "s"), fn) end }
    S.loadFromSavegame(lv, sg)
    return lv, ls
end
local _, ls = load({ { 0.5, 2 }, { 0.2, 5 } }, 3, 3)
check("uložení: 2 baterie (jedna vyndaná) zůstanou 2", #ls.batteries == 2 and ls.batteries[1].slot == 2 and near(ls.batteries[2].charge, 20))
_, ls = load({ { 0.5, 2 }, { 0.2, 5 } }, 3, 5)
check("dílna: konfigurace 3 -> 5 přidá 2 plné", #ls.batteries == 4 and ls.batteries[3].charge == 100 and ls.batteries[3].slot >= 1)
_, ls = load({ { 0.5, 1 }, { 0.2, 2 }, { 0.9, 3 } }, nil, 3)
check("stará hra bez #batteryConfig: počet z uložení", #ls.batteries == 3)
_, ls = load({}, 3, 3)
check("uložení bez baterií (všechny vyndané) = prázdný vlek", #ls.batteries == 0)

-- ------------------------------------------------------------------ kufr: pool po letu (podezření z testu F2)
local caseSpec = { portable = true, batteries = { { charge = 100, slot = 0, drone = 1 } }, batteryCapacity = 100, chargeRate = 2,
    numDrones = 1, isLinked = false, state = S.STATE_FLYING, droneBattery = 1, battery = 100, powerSyncTimer = 0, dirtyFlag = 1,
    generatorRunning = false, numCharging = 0, chargeSource = C.SOURCE_BUILDING, caseSourceTimer = 1e9 }
caseSpec.drones = { caseSpec }
local case = { rootNode = "case", id = 9 }
case[S.SPEC_NAME] = caseSpec
function case:getOwnerFarmId() return 1 end
function case:raiseDirtyFlags() end
function case:raiseActive() end
caseSpec.battery = 40
C.updatePower(case, 1000)
check("kufr: pool za letu ukazuje nabití dronu", near(caseSpec.batteries[1].charge, 40), caseSpec.batteries[1].charge)
caseSpec.isLinked, caseSpec.state = true, S.STATE_PARKED
C.updatePower(case, 1000)
check("kufr: po přistání se nabíjí z nabití dronu, ne ze vzletu", near(caseSpec.batteries[1].charge, 42) and near(caseSpec.battery, 42), caseSpec.battery)

-- kufr: R vyndá baterii jen zblízka (nebo při míření na ni), jinak patří víku
check("kufr: u baterie do 0,6 m R vyndá baterii", B.getIsCaseReach("slot", 0.5))
check("kufr: dál než 0,6 m bez míření R ovládá víko", not B.getIsCaseReach("slot", 0.9))

return { out = out, fails = fails }
''')

for line in result["out"].values():
    print(line)
fails = result["fails"]
print(f"\n{'OK' if fails == 0 else 'CHYB: ' + str(fails)}")
sys.exit(1 if fails else 0)
