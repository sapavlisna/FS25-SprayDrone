# Ruční zkouška vzorkovače AIRASI bez hry (LuaJIT/lupa): python tools/test_samples.py
# SprayDroneSamples: mřížka bodů v poli podle hustoty PF, stav bodu z mapy pokrytí PF (odebráno / odkryto), body k odběru a mimo dosah,
# pořadí bodů dávky, velikost dávky (kapacita dronu, místo v bedničce), přistání (vzorky do bedničky), odeslání do laboratoře, odběr
# na vlastním a cizím pozemku, výsun / výdrž / zasunutí sondy a důvody konce mise (plná bednička, bez PF, hotovo, mimo dosah).
# Porost (isLowCrop nad popisy plodin, body ve vysokém porostu se přeskočí), naklikané body (přidání, odebrání, bez automatických bodů,
# event a uložení), krabičky (prázdná z přihrádky do dronu, plná po odběru, po přistání do přihrádky, odeslání), obrys oblasti odběrů.
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
g_i18n = { getText = function(_, key) return key end, formatMoney = function(_, v) return tostring(v) end }
local LOAD = { ["SprayDroneRoute.lua"] = true, ["SprayDroneMixer.lua"] = true, ["SprayDroneFields.lua"] = true,
    ["SprayDroneDrones.lua"] = true, ["SprayDroneService.lua"] = true, ["SprayDroneCase.lua"] = true,
    ["SprayDronePadDrone.lua"] = true, ["SprayDroneSamples.lua"] = true, ["SprayDroneSamplePointsEvent.lua"] = true }
source = function(path)
    local name = path:match("([^/]+)$")
    if LOAD[name] then
        dofile(SCRIPTS .. "/" .. (name:find("Event%.lua$") and "events/" or "") .. name)
    end
end
Event = { new = function(mt) return setmetatable({}, mt) end }
dofile(SCRIPTS .. "/SprayDroneStation.lua")
local S, P = SprayDroneStation, SprayDroneSamples
SprayDroneSound = { noteAction = function() end }

-- ------------------------------------------------------------------ mřížka
local rect = { { x = 0, z = 0 }, { x = 200, z = 0 }, { x = 200, z = 100 }, { x = 0, z = 100 } }
local spacing = P.getSpacing(5.2)
check("rozestup = sqrt(10000 / n)", near(spacing, math.sqrt(10000 / 5.2)), spacing)
local grid = P.buildGrid(rect, spacing)
local inside, minD = true, math.huge
for i, a in ipairs(grid) do
    inside = inside and a.x > 0 and a.x < 200 and a.z > 0 and a.z < 100
    for j = i + 1, #grid do
        minD = math.min(minD, MathUtil.vector2Length(a.x - grid[j].x, a.z - grid[j].z))
    end
end
local density = #grid * spacing * spacing / 20000
check("body mřížky leží v poli", inside and #grid > 0, #grid)
check("body od sebe aspoň rozestup", minD >= spacing - 1e-6, minD)
check("počet bodů odpovídá hustotě (2 ha × 5,2/ha)", density > 0.6 and density < 1.4, string.format("%d bodů, %.2f", #grid, density))
local grid2 = P.buildGrid({ { x = 500, z = 0 }, { x = 700, z = 0 }, { x = 700, z = 100 }, { x = 500, z = 100 } }, spacing)
check("světová mřížka: posunuté pole má body na stejné síti", near((grid2[1].x / spacing) % 1, 0.5, 1e-6))
local tiny = P.buildGrid({ { x = 1, z = 1 }, { x = 11, z = 1 }, { x = 11, z = 11 }, { x = 1, z = 11 } }, spacing)
check("malé pole: jeden bod v těžišti", #tiny == 1 and near(tiny[1].x, 6) and near(tiny[1].z, 6))

-- ------------------------------------------------------------------ stav bodu v PF
g_currentMission = { terrainSize = 2048, accessHandler = { canFarmAccessOtherId = function(_, a, b) return a == b end } }
local MAP = {}
getBitVectorMapPoint = function(_, px, pz) return MAP[px .. ":" .. pz] or 0 end
local cover = { bitVectorMap = 1, sizeX = 1024, sizeY = 1024, firstChannel = 1, numChannels = 4, maxValue = 7, sampledValue = 8 }
local function setCover(x, z, value)
    MAP[math.floor((x + 1024) / 2048 * 1024) .. ":" .. math.floor((z + 1024) / 2048 * 1024)] = value
end
local pf = { coverMap = cover, nitrogenMap = {}, soilMap = { getNumSoilSamplesPerHa = function() return 5.2 end,
    getPricePerSoilSample = function() return 50 end, pendingSoilSamplesPerFarm = {} } }
setCover(10, 10, 8)
setCover(20, 20, 5)
setCover(30, 30, 1)
check("odebraný vzorek (sampledValue) se pozná", P.getIsSampled(pf, 10, 10))
check("odkrytá půda (2..maxValue) se pozná", P.getIsSampled(pf, 20, 20))
check("zakrytá půda (0, 1) je k odběru", not P.getIsSampled(pf, 30, 30) and not P.getIsSampled(pf, 40, 40))
check("bez PF nic odebrané není", not P.getIsSampled(nil, 10, 10))

-- ------------------------------------------------------------------ kufr se vzorkovačem
local field = { getId = function() return 23 end }
SprayDroneRoute.getFieldById = function(id) return id == 23 and field or nil end
SprayDroneRoute.getPolygon = function() return rect end
local pfOn = true
S.getPrecisionFarming = function() return pfOn and pf or nil end
local home = { 100, -20 }
S.getHomePosition = function() return home[1], home[2], 0.1 end
local range = 1000
S.updateRange = function() return range end
local statuses = {}
S.endMission = function(_, status) table.insert(statuses, status) end
S.markRouteDirty = function() end

local function newCase()
    local spec = { isSamplerDrone = true, sampler = { capacity = 2, boxCapacity = 8, height = 0.05, holdTime = 3, probeTime = 0.8,
        probeTravel = 0.14, tipTravel = 0.16 }, sampleBox = 0, samplesCarried = 0, samplerBoxes = 0, samplerPicks = {}, samplerAuto = 1,
        probeOut = false, fieldId = 23, dirtyFlag = 1,
        state = S.STATE_SERVICING, numDrones = 1, batteries = {}, batteryCapacity = 1500, battery = 1500, droneBattery = 1 }
    spec.drones = { spec }
    local v = { id = 5, farmId = 1, dirty = 0, commands = {} }
    v[S.SPEC_NAME] = spec
    function v:getOwnerFarmId() return 1 end
    function v:raiseDirtyFlags() self.dirty = self.dirty + 1 end
    function v:raiseActive() end
    function v:sprayDroneCommand(command, value) table.insert(self.commands, { command, value }) end
    return v, spec
end
local v, spec = newCase()

MAP = {}
local points = P.getPoints(v)
check("body pole = mřížka", points.total == #grid, points.total)
check("bez odběru: všechny body čekají", #points.pending == points.total and points.sampled == 0)
setCover(grid[1].x, grid[1].z, 8)
setCover(grid[2].x, grid[2].z, 3)
points = P.getPoints(v)
check("odebrané a odkryté body se vynechají", points.sampled == 2 and #points.pending == points.total - 2, points.sampled)
range = 60
points = P.getPoints(v)
check("body dál než dosah: mimo dosah, ne k odběru", points.far > 0 and points.far + #points.pending + points.sampled == points.total, points.far)
range = 1000

local list = { { x = 0, z = 100 }, { x = 0, z = 10 }, { x = 0, z = 30 }, { x = 0, z = 200 } }
local batch, rest = P.pickBatch(list, 0, 0, 2)
check("dávka: nejbližší k domovu, pak nejbližší k předchozímu", #batch == 2 and batch[1].z == 10 and batch[2].z == 30 and #rest == 2)

-- ------------------------------------------------------------------ porost (popisy plodin jako vanilla data/foliage)
local function crop(names, extra)
    local ft = { growthStateToName = {}, numGrowthStates = 0, cutState = 0, cutStates = {}, mulchedState = 0, rolledCutState = 0 }
    for k, name in ipairs(names) do
        ft.growthStateToName[k] = name
    end
    for key, value in pairs(extra or {}) do
        ft[key] = value
    end
    return ft
end
local wheat = crop({ "invisible", "greenSmall", "greenSmall2", "greenMiddle", "greenMiddle2", "greenBig", "greenBig2", "harvestReady", "dead",
    "harvested" }, { numGrowthStates = 8, cutState = 10, cutStates = { [10] = true } })
local maize = crop({ "invisible", "greenSmall", "greenMiddle", "greenBig", "harvestReadyGreen", "harvestReadyGreen2", "harvestReady3", "dead",
    "harvestedGreen", "harvested" }, { numGrowthStates = 7, cutState = 10, cutStates = { [9] = true, [10] = true } })
local potato = crop({ "invisible", "greenSmall", "greenSmall2", "greenMiddle", "greenBig", "harvestReady", "dead", "harvested", "cutHaulm" },
    { numGrowthStates = 6, cutState = 8, cutStates = { [8] = true }, preparedGrowthState = 9 })
local grass = crop({ "invisible", "greenSmall", "greenMiddle", "harvestReady", "cut", "cutRolled" },
    { numGrowthStates = 4, cutState = 5, cutStates = { [5] = true }, mulchedState = 5, rolledCutState = 6 })
local banana = crop({ "regrowSmall", "regrowMiddle", "regrowMiddle2", "noFruits", "greenSmall" }, { numGrowthStates = 5 })
local L = P.isLowCrop
check("porost: holá / obdělaná půda (bez plodiny) je nízká", L(nil, 0) and L(wheat, 0))
check("porost: zaseto (invisible) a první fáze (greenSmall) jsou nízké", L(wheat, 1) and L(wheat, 2) and L(maize, 1) and L(maize, 2))
check("porost: od 3. fáze vysoký (pšenice greenSmall2, kukuřice greenMiddle)", not L(wheat, 3) and not L(maize, 3))
check("porost: zralé a odumřelé jsou vysoké", not L(wheat, 8) and not L(wheat, 9) and not L(maize, 7))
check("porost: sklizeno / strniště je nízké", L(wheat, 10) and L(maize, 9) and L(maize, 10))
check("porost: posečená nať brambor je nízká, zralé brambory ne", L(potato, 9) and not L(potato, 6))
check("porost: posečená a svinutá tráva nízká, vzrostlá vysoká", L(grass, 5) and L(grass, 6) and not L(grass, 4))
check("porost: plodina bez růstu je nízká", L(crop({ "a", "b", "c", "d" }), 4))
check("porost: trvalá kultura (banán) není nízká ani v 1. stavu", not L(banana, 1) and not L(banana, 2))
check("porost: stav bez jména do 2. fáze je nízký", L({ numGrowthStates = 5 }, 2) and not L({ numGrowthStates = 5 }, 3))

check("dávka = kapacita dronu (2)", P.getBatchSize(spec) == 2)
spec.sampleBox = 7
check("dávka omezená místem v bedničce", P.getBatchSize(spec) == 1)
spec.sampleBox, spec.samplesCarried = 6, 1
check("místo v bedničce počítá i vzorky v dronu", P.getBatchSize(spec) == 1)
spec.sampleBox, spec.samplesCarried = 8, 0
check("plná bednička: dávka 0", P.getBatchSize(spec) == 0)
check("plná bednička: start odmítnut", P.getStartWarning(v) == "sdt_sampler_boxFull")
statuses = {}
P.startNextBatch(v)
check("plná bednička: konec mise BOX_FULL", statuses[1] == P.STATUS_BOX_FULL)
spec.sampleBox = 0
pfOn = false
statuses = {}
P.startNextBatch(v)
check("bez PF: konec mise NO_PF", statuses[1] == P.STATUS_NO_PF)
check("bez PF: start odmítnut", P.getStartWarning(v) == "sdt_sampler_noPF")
pfOn = true
for _, p in ipairs(grid) do
    setCover(p.x, p.z, 8)
end
statuses = {}
P.startNextBatch(v)
check("všechny body odebrané: konec mise DONE", statuses[1] == P.STATUS_DONE)
for _, p in ipairs(grid) do
    setCover(p.x, p.z, 0)
end
range = 10
statuses = {}
P.startNextBatch(v)
check("zbývá jen mimo dosah: OUT_OF_REACH", statuses[1] == S.STATUS_OUT_OF_REACH)
range = 1000

-- ------------------------------------------------------------------ dávka: waypointy a baterie
spec.sprayHeight, spec.ascentSpeed, spec.cruiseSpeed, spec.climbSpeed = 4, 4, 12, 2.5
S.getTransit = function(_, x, z, outbound, _, _, opts)
    local h = outbound and 4 or (opts.startH or 4)
    return { wps = { { x = x, z = z, h = h, speed = 12, home = not outbound, land = not outbound } }, height = 15, length = 100 }
end
S.getHopHeight = function() return nil end
S.getHomeYaw = function() return 0 end
S.getFlightParams = function() return { homeYaw = 0, batteryReserve = 30, hoverFactor = 1.15 } end
SprayDroneRoute.drainFactor = function() return 1 end
-- čas i spotřeba 10 s na waypoint
SprayDroneRoute.pathCost = function(pts) return #pts * 10, #pts * 10 end
local two = { { x = 0, z = 0 }, { x = 50, z = 0 } }
local wps = P.buildPath(v, two)
local samples, low = 0, true
for _, wp in ipairs(wps) do
    if wp.sample then
        samples = samples + 1
        low = low and wp.h == spec.sampler.height
    end
end
check("dávka 2 bodů: 2 waypointy odběru ve výšce sampler#height", samples == 2 and low)
local plan = P.planBatch(v, two, 2, 1e6)
check("plná baterie: dávka 2 body", plan ~= nil and #plan.points == 2)
local oneEnergy = P.planBatch(v, two, 1, 1e6).energy
plan = P.planBatch(v, two, 2, oneEnergy + 1)
check("baterie jen na jeden bod: dávka 1 bod", plan ~= nil and #plan.points == 1)
local _, reason = P.planBatch(v, two, 2, oneEnergy - 1)
check("baterie ani na jeden bod: důvod battery", reason == "battery")
check("odhad zahrnuje výdrž nad body a rezervu", oneEnergy >= 30 + (3 + 1.6) * 1.15)

-- ------------------------------------------------------------------ odběr
local analysed = {}
g_farmlandManager = { getFarmlandIdAtWorldPosition = function(_, x) return x < 1000 and 23 or 99 end,
    getFarmlandOwner = function(_, id) return id == 23 and 1 or 2 end }
local circle = { updateFromWorldPosition = function(self, x, z, r) self.x, self.z, self.r = x, z, r end }
S.getPFGlobal = function(name) return name == "DensityMapCircle" and { new = function() return circle end } or nil end
cover.analyseArea = function(_, c, state, farmId, farmlandId)
    table.insert(analysed, { x = c.x, z = c.z, r = c.r, farmId = farmId, farmlandId = farmlandId })
    setCover(c.x, c.z, 8)
end
spec.samplesCarried = 0
P.takeSample(v, grid[3].x, grid[3].z)
check("odběr na vlastním pozemku: analyseArea kruhem 32,5 m", #analysed == 1 and analysed[1].r == 32.5 and analysed[1].farmlandId == 23
    and analysed[1].farmId == 1)
check("odběr: vzorek v dronu", spec.samplesCarried == 1)
check("odebraný bod už nečeká", P.getIsSampled(pf, grid[3].x, grid[3].z))
P.takeSample(v, 1500, 50)
check("cizí pozemek: bez odběru, bod se přeskočí", #analysed == 1 and spec.samplesCarried == 1 and spec.samplerSkip["1500:50"] == true)

-- ------------------------------------------------------------------ sonda
spec.state = S.STATE_FLYING
spec.samplesCarried = 0
analysed = {}
P.startHold(v, { x = grid[4].x, z = grid[4].z })
check("na bodě: sonda vyjede", spec.probeOut == true and spec.sampleHold ~= nil)
local holding, steps = true, 0
while holding and steps < 1000 do
    holding = P.updateHold(v, 100)
    steps = steps + 1
end
check("výsun + výdrž + zasunutí = 0,8 + 3 + 0,8 s", steps >= 45 and steps <= 48, steps)
check("za výdrž právě jeden odběr", #analysed == 1 and spec.samplesCarried == 1)
check("po odběru je sonda zasunutá", spec.probeOut == false and spec.sampleHold == nil)
P.startHold(v, { x = grid[5].x, z = grid[5].z })
spec.state = S.STATE_RETURNING
check("návrat domů za výdrže: sonda zajede, dron letí", P.updateHold(v, 100) == false and spec.probeOut == false and spec.sampleHold == nil)

-- ------------------------------------------------------------------ bednička a laboratoř
spec.samplesCarried, spec.sampleBox = 2, 7
P.onLanded(v)
check("přistání: vzorky do bedničky, nejvýš kapacita", spec.sampleBox == 8 and spec.samplesCarried == 0)
local sent = nil
pf.soilMap.analyseSoilSamples = function(_, farmId, n) sent = { farmId, n } end
P.sendSamples(v)
check("odeslání: analyseSoilSamples(farmId, n), bednička prázdná", sent ~= nil and sent[1] == 1 and sent[2] == 8 and spec.sampleBox == 0)
sent = nil
P.sendSamples(v)
check("prázdná bednička se neodesílá", sent == nil)
check("klient: prázdná bednička hlásí důvod", P.requestSend(v) == "sdt_sampler_boxEmpty" and #v.commands == 0)
spec.sampleBox = 3
g_currentMission.addIngameNotification = function() end
check("klient: odeslání pošle příkaz SEND_SAMPLES", P.requestSend(v) == nil and v.commands[1][1] == SprayDroneCommandEvent.SEND_SAMPLES)

-- ------------------------------------------------------------------ let dávky přes SprayDroneStation.updateFlight
-- (ve hře 2026-10-29 se dron po vzletu hned vracel: updateFlight posílal domů dron s prázdnou nádrží, který neskenuje)
MAP = {}
analysed = {}
local returned = 0
S.startReturnHome = function() returned = returned + 1 end
S.drainBattery = function() end
S.checkWeather = function() return false end
S.updateSignal = function() return true end
S.setDroneWorldPosition = function() end
S.attachDrone = function() end
getTerrainHeightAtWorldPos = function() return 0 end
MathUtil.getYRotationFromDirection = function(dx, dz) return math.atan2(dx, dz) end
MathUtil.getAngleDifference = function(a, b)
    local d = (a - b) % (2 * math.pi)
    return d > math.pi and d - 2 * math.pi or d
end
v.getLastSpeed = function() return 0 end
spec.portable = true
spec.state, spec.missionActive, spec.airborne = S.STATE_FLYING, true, true
spec.missionMode, spec.droneFillLevel, spec.scanning = 1, 0, false
spec.samplesCarried, spec.sampleBox, spec.sampleHold, spec.samplerBatchSamples = 0, 0, nil, 0
spec.path, spec.wpIndex = P.buildPath(v, two), 1
spec.pos = { x = home[1], z = home[2], h = 0.1, yaw = 0 }
spec.moveDir = { x = 0, z = 0 }
spec.speed, spec.yawRate, spec.avoidHeight, spec.avoidClimbTo = 0, 0, 0, nil
spec.acceleration, spec.yawSpeed, spec.flightTime, spec.flightSyncTimer = 3, math.rad(100), 0, 0
spec.returnEnergyTime, spec.returnEnergy, spec.guardOffUntil, spec.guardNextCheck = math.huge, 0, math.huge, math.huge
spec.positionDirtyFlag = 2
local t = 0
while t < 120000 and spec.path ~= nil and returned == 0 do
    S.updateFlight(v, 50)
    t = t + 50
end
check("let dávky: dron s prázdnou nádrží (missionMode 1) se nevrací předčasně", returned == 0, string.format("%.1f s", t / 1000))
check("let dávky: oba body odebrané, po přistání v bedničce", #analysed == 2 and spec.sampleBox == 2 and spec.samplesCarried == 0, #analysed)
check("let dávky: přistane v kufru (servis)", spec.state == S.STATE_SERVICING and spec.path == nil, spec.state)

-- ------------------------------------------------------------------ pojistka: dávky bez vzorku
statuses = {}
spec.missionActive, spec.samplerIdleBatches, spec.samplesCarried = true, 0, 0
spec.samplerBatchSamples = 0
P.onLanded(v)
check("1 dávka bez vzorku: mise běží", #statuses == 0)
spec.samplerBatchSamples = 0
P.onLanded(v)
check("2 dávky po sobě bez vzorku: konec mise STUCK", statuses[1] == P.STATUS_STUCK)
statuses = {}
spec.samplerBatchSamples = 0
P.onLanded(v)
spec.samplerBatchSamples, spec.samplesCarried = 1, 1
P.onLanded(v)
spec.samplerBatchSamples = 0
P.onLanded(v)
check("dávka se vzorkem počítadlo vynuluje", #statuses == 0)

-- ------------------------------------------------------------------ mise a počasí
spec.missionMode = 1
check("vzorkovač má missionMode 1, ale není sken (počasí jako postřik)", not S.getIsScanMode(v))
spec.isSamplerDrone = false
check("skenovací dron (missionMode 1) je sken", S.getIsScanMode(v))
spec.isSamplerDrone = true

-- ------------------------------------------------------------------ body ve vysokém porostu
MAP = {}
spec.state, spec.missionActive = S.STATE_SERVICING, false
spec.sampleBox, spec.samplesCarried, spec.samplerBoxes = 0, 0, 0
local tallKeys = {}
g_fruitTypeManager = { getFruitTypeByIndex = function() return wheat end }
FSDensityMapUtil = { getFruitTypeIndexAtWorldPos = function(x, z)
    if tallKeys[P.getKey(x, z)] then return 1, 6 end
    return 1, 2
end }
tallKeys[P.getKey(grid[1].x, grid[1].z)] = true
points = P.getPoints(v)
check("bod ve vysokém porostu: tall, není k odběru", points.tall == 1 and points.points[1].tall and #points.pending == points.total - 1, points.tall)
for _, p in ipairs(grid) do
    tallKeys[P.getKey(p.x, p.z)] = true
end
points = P.getPoints(v)
spec.routeInfo = { samplePoints = points }
check("vše ve vysokém porostu: start odmítnut s důvodem", P.getStartWarning(v) == "sdt_sampler_tallCrop")
statuses = {}
P.startNextBatch(v)
check("vše ve vysokém porostu: konec mise STATUS_TALL", statuses[1] == P.STATUS_TALL)
tallKeys = {}

-- ------------------------------------------------------------------ naklikané body
local picks = P.newPicks()
local small = { { x = 10, z = 10 }, { x = 50, z = 10 } }
check("přidání bodu", P.addPick(picks, small, true, 30, 30, 3) == true and #picks.added == 1)
local ok2, why = P.addPick(picks, small, true, 31, 30, 0.5)
check("bod těsně u jiného se nepřidá", ok2 == false and why == "sdt_sampler_pickExists")
check("odebrání naklikaného bodu", P.removePick(picks, small, true, 29, 30, 3) == true and #picks.added == 0)
check("odebrání bodu mřížky (roh pole)", P.removePick(picks, small, true, 11, 9, 3) == true and picks.removed[P.getKey(10, 10)] ~= nil)
local merged = P.mergePoints(small, picks, true)
check("odebraný bod mřížky v bodech není", #merged == 1 and merged[1].x == 50)
check("levý klik u odebraného bodu mřížky ho vrátí", P.addPick(picks, small, true, 10, 11, 3) == true and next(picks.removed) == nil
    and #picks.added == 0)
local _, none = P.removePick(picks, small, true, 200, 200, 3)
check("pravý klik bez bodu: důvod", none == "sdt_sampler_pickNone")
P.addPick(picks, small, false, 70, 70, 3)
check("bez automatických bodů: jen naklikané", #P.mergePoints(small, picks, false) == 1 and #P.mergePoints(small, picks, true) == 3)
check("bez automatických bodů se bod mřížky nedá odebrat", P.removePick(P.newPicks(), small, false, 10, 10, 3) == false)

-- přes kufr: přidání v poli, mimo pole a mimo dosah; režim bez automatických bodů
spec.samplerPicks, spec.samplerAuto = {}, 1
SprayDroneRoute.isPointInPolygon = function(poly, x, z) return x > 0 and x < 200 and z > 0 and z < 100 end
check("klik mimo pole: hláška", P.requestPick(v, 300, 50, true, 3) == "sdt_sampler_pickOutside")
range = 10
check("klik mimo dosah: hláška", P.requestPick(v, 20, 90, true, 3) == "sdt_sampler_pickFar")
range = 1000
check("klik v poli přidá bod", P.requestPick(v, 21, 91, true, 3) == nil and #spec.samplerPicks[23].added == 1)
spec.samplerAuto = 0
points = P.getPoints(v)
check("auto body vypnuté: jen naklikaný bod", points.total == 1 and points.points[1].custom == true)
P.requestPick(v, 21, 91, false, 3)
points = P.getPoints(v)
spec.routeInfo = { samplePoints = points }
check("auto body vypnuté a nic naklikané: start odmítnut", points.total == 0 and P.getStartWarning(v) == "sdt_sampler_noPoints")
spec.samplerAuto = 1
check("auto body zapnuté: celá mřížka", #P.getPoints(v).pending == #grid)

-- event: zápis a čtení stavu pole (stream jako seznam hodnot)
local stream = {}
streamWriteUInt16 = function(_, value) table.insert(stream, value) end
streamWriteUInt8 = streamWriteUInt16
streamWriteFloat32 = streamWriteUInt16
local pos = 0
local function readNext() pos = pos + 1 return stream[pos] end
streamReadUInt16, streamReadUInt8, streamReadFloat32 = readNext, readNext, readNext
local sent = P.newPicks()
P.putPick(sent, "added", 12.5, 40)
P.putPick(sent, "removed", 10, 10)
SprayDroneSamplePointsEvent.writePicks(1, 23, sent)
local fid, got, valid = SprayDroneSamplePointsEvent.readPicks(1)
check("event: body pole projdou sítí", fid == 23 and valid and #got.added == 1 and got.added[1].x == 12.5 and got.removed[P.getKey(10, 10)] ~= nil)

-- uložení a načtení
local xml = { values = {} }
function xml:setValue(key, value) self.values[key] = value end
function xml:getValue(key, default)
    local value = self.values[key]
    if value == nil then return default end
    return value
end
function xml:iterate(key, fn)
    local i = 0
    while self.values[string.format("%s(%d)#x", key, i)] ~= nil or self.values[string.format("%s(%d)#fieldId", key, i)] ~= nil do
        fn(i + 1, string.format("%s(%d)", key, i))
        i = i + 1
    end
end
spec.samplerPicks = { [23] = sent }
spec.sampleBox, spec.samplesCarried = 3, 1
P.saveToXMLFile(v, xml, "k")
spec.samplerPicks, spec.sampleBox = {}, 0
P.loadFromSavegame(v, xml, "k")
check("uložení: naklikané body a krabičky přežijí", spec.samplerPicks[23] ~= nil and #spec.samplerPicks[23].added == 1
    and spec.samplerPicks[23].removed[P.getKey(10, 10)] ~= nil and spec.sampleBox == 4, spec.sampleBox)

-- ------------------------------------------------------------------ krabičky: přihrádka -> dron -> plná -> přihrádka -> laboratoř
local E, F, N = P.SLOT_EMPTY, P.SLOT_FULL, P.SLOT_NONE
local function same(a, b)
    if #a ~= #b then return false end
    for i = 1, #a do
        if a[i] ~= b[i] then return false end
    end
    return true
end
spec.sampler.boxCapacity, spec.sampler.capacity = 6, 2
spec.sampleBox, spec.samplesCarried, spec.samplerBoxes = 1, 0, 0
check("bednička: plná, pak prázdné krabičky", same(P.getSlotStates(6, spec.sampleBox, 0), { F, E, E, E, E, E }))
P.takeBoxes(v, 2)
check("před letem: dvě prázdné krabičky z přihrádek do dronu", spec.samplerBoxes == 2
    and same(P.getSlotStates(6, spec.sampleBox, spec.samplerBoxes), { F, N, N, E, E, E })
    and same(P.getDroneBoxStates(2, spec.samplerBoxes, spec.samplesCarried), { E, E }))
check("krabičky v dronu se počítají do místa v bedničce", P.getBatchSize(spec) == 2)
analysed = {}
P.takeSample(v, grid[6].x, grid[6].z)
check("po odběru: krabička na dronu plná", spec.samplesCarried == 1 and same(P.getDroneBoxStates(2, spec.samplerBoxes, spec.samplesCarried), { F, E }))
spec.missionActive = false
P.onLanded(v)
check("po přistání: plná do přihrádky, nepoužitá prázdná zpět", spec.sampleBox == 2 and spec.samplerBoxes == 0 and spec.samplesCarried == 0
    and same(P.getSlotStates(6, spec.sampleBox, 0), { F, F, E, E, E, E }))
spec.sampleBox = 5
P.takeBoxes(v, 2)
check("jen jedna prázdná krabička: dron vezme jednu", spec.samplerBoxes == 1)
spec.samplerBoxes = 0
pf.soilMap.analyseSoilSamples = function() end
P.sendSamples(v)
check("odeslání: všechny přihrádky zpět prázdné", spec.sampleBox == 0 and same(P.getSlotStates(6, spec.sampleBox, 0), { E, E, E, E, E, E }))
spec.sampler.capacity = 1
check("dron s jednou krabičkou: dávka 1", P.getBatchSize(spec) == 1)
spec.sampler.capacity = 2

-- model: počet přihrádek a krabiček z uzlů
spec.samplerVisuals = { slots = { {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {} }, droneBoxes = { {} } }
spec.sampleBox = 20
P.applyModelCapacity(spec)
check("kapacita podle modelu: 12 přihrádek, 1 krabička v dronu", spec.sampler.boxCapacity == 12 and spec.sampler.capacity == 1 and spec.sampleBox == 12)
-- bedna AIRASI přes celé víko: 6 x 4 přihrádek se vejde do BOX_BITS (síť, save)
spec.samplerVisuals = { slots = {}, droneBoxes = { {}, {} } }
for i = 1, 24 do spec.samplerVisuals.slots[i] = {} end
spec.sampleBox = 20
P.applyModelCapacity(spec)
check("kapacita podle modelu: 24 přihrádek, 2 krabičky v dronu", spec.sampler.boxCapacity == 24 and spec.sampler.capacity == 2 and spec.sampleBox == 20)
spec.samplerVisuals = nil

-- bedna ve víku: na zavřený kufr se jako na bednu nemíří (jinak by nešel zvednout), na otevřený ano
do
    local cv, cspec = newCase()
    local aimed = SprayDroneLink.isAimedAt
    SprayDroneLink.isAimedAt = function() return true end
    cspec.samplerVisuals = { box = 1 }
    -- getIsLidOpening: zavírá se / zavřeno = směr shodný s turnOnFoldDirection
    local toggled = 1
    cv.spec_foldable = { turnOnFoldDirection = 1 }
    cv.getToggledFoldDirection = function() return toggled end
    check("bedna: zavřený kufr = nemíří na bednu", not P.isAimedAtBox(cv))
    toggled = -1
    check("bedna: otevřený / otevírající se kufr = míří na bednu", P.isAimedAtBox(cv))
    cv.spec_foldable = nil
    check("bedna: bez Foldable rozhoduje jen míření", P.isAimedAtBox(cv))
    SprayDroneLink.isAimedAt = aimed
end

-- ------------------------------------------------------------------ obrys oblasti odběrů
local lines = P.getCoverageOutline({ { x = 0, z = 0 } }, 10, 16)
check("obrys jednoho bodu: celý kruh", #lines == 16)
lines = P.getCoverageOutline({ { x = 0, z = 0 }, { x = 10, z = 0 } }, 10, 32)
local innerOk = true
for _, l in ipairs(lines) do
    for _, c in ipairs({ { 0, 0 }, { 10, 0 } }) do
        local mx, mz = (l.x1 + l.x2) * 0.5, (l.z1 + l.z2) * 0.5
        innerOk = innerOk and (mx - c[1]) ^ 2 + (mz - c[2]) ^ 2 > 80
    end
end
check("obrys dvou překrytých kruhů: jen vnější oblouky", #lines > 0 and #lines < 64 and innerOk, #lines)

return { out = out, fails = fails }
''')

for line in result["out"].values():
    print(line)
fails = result["fails"]
print(f"\n{'OK' if fails == 0 else 'CHYB: ' + str(fails)}")
sys.exit(1 if fails else 0)
