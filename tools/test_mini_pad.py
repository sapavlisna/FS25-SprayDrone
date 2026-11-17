# Zkouška pravidel Mini bez hry (LuaJIT/lupa): python tools/test_mini_pad.py
# docs/NAVRH-dron-predmet.md kap. 12 (úprava 2026-10-29 odpoledne): dron na Mini má dvě polohy, bednu (A, přepravní) a rozloženou plošinu
# (B, letová), a sám se mezi nimi nepřesouvá. Hlídá: polohu po načtení staré hry, cíl rozložení dronu, start jen z plošiny (a hlášku
# v plánovači), zákaz složení vleku s dronem na plošině, místa pro R (getSpots / getNearestPad, bedna chytá do BOX_CATCH_DISTANCE,
# přendání R s prázdnýma rukama), příkazy PLACE_PLATE / MOVE_BOX / MOVE_PLATE, okamžité přendání bez animace skládání (debugMoveMini), odepnutí TAKE
# (nejdřív složení, předmět přesně na místě dronu, ne u hráče; Middle/Max z kořene dronu), bit polohy
# ve writePads / readPads a viditelnost plnicí hadice (jen u rozloženého postřikového dronu; Max bez dronu 2 po načtení).
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
CollisionFlag = { STATIC_OBJECT = 1, TREE = 2, BUILDING = 4, VEHICLE = 8, DYNAMIC_OBJECT = 16, PLAYER = 32 }
g_time = 1000
g_currentModDirectory = ""
SprayDroneDebug = { ENABLED = false }
g_i18n = { getText = function(_, key) return key end }
local LOAD = { ["SprayDroneRoute.lua"] = true, ["SprayDroneMixer.lua"] = true, ["SprayDroneFields.lua"] = true,
    ["SprayDroneDrones.lua"] = true, ["SprayDroneService.lua"] = true, ["SprayDronePadDrone.lua"] = true,
    ["SprayDronePadSlots.lua"] = true, ["SprayDronePad.lua"] = true }
source = function(path)
    local name = path:match("([^/]+)$")
    if LOAD[name] then
        dofile(SCRIPTS .. "/" .. name)
    end
end
dofile(SCRIPTS .. "/SprayDroneStation.lua")
dofile(SCRIPTS .. "/events/SprayDronePadSlotEvent.lua")
local S, P, PS, E = SprayDroneStation, SprayDronePad, SprayDronePadSlots, SprayDronePadSlotEvent
SprayDroneSound = { noteAction = function() end }
SprayDroneLevel = { checkDeploy = function() return true end }
S.PAD_NAMES = S.PAD_NAMES or { "S", "M", "L", "K" }

-- Mini: jedna plošina, bedna (pad), dron S; foldTime 0 = rozloženo, 1 = složeno
local function newMini(variant, onPlate, foldTime)
    local spec = { pads = { variant }, numPads = 1, numDrones = 1, activeDrones = 1, hasDrone = variant ~= "", fieldId = 5,
        batteries = { {} }, batteryMoves = {}, transferMode = S.TRANSFER_NONE, trailerFoldEnd = 0.06, dirtyFlag = 1, foldParts = {}, rotors = { { angle = 1.2, appliedAngle = 1.2 } },
        variants = { { name = "S" }, { name = "K", scan = true } }, secondVariants = {}, portable = false,
        state = S.STATE_PARKED, isLinked = true, missionActive = false, unfold = 0, rotorSpeed = 0, rotorsParked = true, hoseT = 0,
        pad = { onPlate = onPlate, foldStart = 0.86, foldEnd = 0.06, settle = 0, boxPoint = "box", platePoint = "plate" },
        padSlots = { nodes = { "drone" }, spawning = {}, folding = {} } }
    spec.drones = { spec }
    local v = { id = 7, foldTime = foldTime or 0, dirty = 0 }
    v[S.SPEC_NAME] = spec
    function v:getFoldAnimTime() return self.foldTime end
    function v:getIsUnfolded() return self.foldTime == 0 end
    function v:getSprayDroneIsParked() return true end
    function v:raiseDirtyFlags() self.dirty = self.dirty + 1 end
    function v:raiseActive() end
    return v, spec
end
local function super() return true, "super" end

-- ------------------------------------------------------------------ poloha po načtení
check("uložená poloha plošina", P.getLoadedOnPlate(true, true, 0) == true)
check("uložená poloha bedna", P.getLoadedOnPlate(false, true, 1) == false)
check("stará hra, rozložený s dronem -> plošina", P.getLoadedOnPlate(nil, true, 1) == true)
check("stará hra, napůl rozložený -> bedna", P.getLoadedOnPlate(nil, true, 0.6) == false)
check("stará hra, složený -> bedna", P.getLoadedOnPlate(nil, true, 0) == false)
check("stará hra bez dronu -> bedna", P.getLoadedOnPlate(nil, false, 1) == false)

-- ------------------------------------------------------------------ dron v bedně (A) na rozloženém vleku
local v, spec = newMini("S", false, 0)
check("A: dron v bedně", P.getIsDroneInBox(v) and not P.getIsDroneOnPlate(v))
check("A: cíl rozložení dronu 0", S.getDroneUnfoldTarget(v) == 0)
check("A: start nejde", not S.getCanStart(v))
check("A: hláška start / plánovač", S.getFoldedWarning(v) == "sdt_planner_droneInBox", S.getFoldedWarning(v))
S.startDrone(v)
check("A: startDrone misi nezaloží", spec.missionActive == false)
local ok, warn = S.getIsFoldAllowed(v, super, 1)
check("A: složení vleku jde", ok == true and warn == "super", tostring(warn))
check("A: blokace kvůli rozložené bedně (getPadBlocker) není", S.getPadBlocker(v, 1) == nil, S.getPadBlocker(v, 1))

-- ------------------------------------------------------------------ dron na plošině (B)
v, spec = newMini("S", true, 0)
check("B: dron na plošině", P.getIsDroneOnPlate(v) and not P.getIsDroneInBox(v))
check("B: cíl rozložení dronu podle vleku", S.getDroneUnfoldTarget(v) == 1)
check("B: start jde", S.getCanStart(v))
check("B: bez hlášky v plánovači", S.getFoldedWarning(v) == nil)
ok, warn = S.getIsFoldAllowed(v, super, 1)
check("B: složení vleku zakázané", ok == false and warn == "sdt_warning_padDroneOnPlate", tostring(warn))
ok, warn = S.getIsFoldAllowed(v, super, -1)
check("B: rozložení (směr -1) se neblokuje", ok == true, tostring(warn))
spec.foldHold = true
check("B: foldHold dron složí", S.getDroneUnfoldTarget(v) == 0)
spec.foldHold = nil

-- ------------------------------------------------------------------ prázdná plošina, složený vlek
v, spec = newMini("", false, 0)
check("prázdná: ani bedna ani plošina", not P.getIsDroneInBox(v) and not P.getIsDroneOnPlate(v))
ok = S.getIsFoldAllowed(v, super, 1)
check("prázdná: složení jde", ok == true)
v, spec = newMini("S", false, 1)
check("složený vlek: hláška složený (ne bedna)", S.getFoldedWarning(v) == "sdt_planner_folded", S.getFoldedWarning(v))
check("složený vlek: vzít ani vložit nejde", S.getPadBlocker(v, 1, true) == "sdt_pad_boxStowed", S.getPadBlocker(v, 1, true))

-- ------------------------------------------------------------------ místa pro R
local realSpot = P.getSpotPosition
P.getSpotPosition = function(_, onPlate) if onPlate then return 0, 0, -3 end return 0, 1, 0 end
getWorldTranslation = function() return 9, 9, 9 end
v, spec = newMini("", false, 0)
local spots = PS.getSpots(v, 1)
check("prázdná rozložená: dvě místa", #spots == 2 and spots[1].onPlate == false and spots[2].onPlate == true)
local i, d, onPlate = PS.getNearestPad(v, 0, 0, -2.6, false)
check("hráč za vlekem vloží na plošinu", i == 1 and onPlate == true, tostring(d))
i, d, onPlate = PS.getNearestPad(v, 0.3, 0, 0.2, false)
check("hráč u bedny vloží do bedny", i == 1 and onPlate == false, tostring(d))
v.foldTime = 1
spots = PS.getSpots(v, 1)
check("složená bedna: jen místo v bedně", #spots == 1 and spots[1].onPlate == false)
v, spec = newMini("S", true, 0)
spots = PS.getSpots(v, 1)
check("dron na plošině: vzít z plošiny, bedna = přendat", #spots == 2 and spots[1].onPlate == false and spots[1].move
    and spots[2].onPlate == true and not spots[2].move)
local move
i, d, onPlate, move = PS.getNearestPad(v, 0.3, 0, 0, true)
check("dron na plošině: u bedny R přendá do bedny", i == 1 and onPlate == false and move == true, tostring(d))
i, d, onPlate, move = PS.getNearestPad(v, 0.2, 0, -2.6, true)
check("dron na plošině: u plošiny R vezme", i == 1 and onPlate == true and move == false, tostring(d))
v, spec = newMini("S", false, 0)
i = PS.getNearestPad(v, 0.3, 0, 0.2, false)
check("dron v bedně: volné místo není", i == nil)
i, d, onPlate, move = PS.getNearestPad(v, 0.2, 0, -2.6, true)
check("dron v bedně: u plošiny R přendá na plošinu", i == 1 and onPlate == true and move == true, tostring(d))
i, d, onPlate, move = PS.getNearestPad(v, 0.3, 0, 0.2, true)
check("dron v bedně: u bedny R vezme", i == 1 and onPlate == false and move == false, tostring(d))
v.foldTime = 1
spots = PS.getSpots(v, 1)
check("dron v bedně, složená bedna: přendat nejde, jen místo v bedně", #spots == 1 and spots[1].onPlate == false and not spots[1].move)
-- bedna chytá: plošina blíž (2,2 m za bednou jako ve hře), ale hráč do BOX_CATCH_DISTANCE od bedny ovládá bednu
P.getSpotPosition = function(_, onPlate) if onPlate then return 0, 0, -2.2 end return 0, 1, 0 end
v, spec = newMini("", false, 0)
i, d, onPlate = PS.getNearestPad(v, 0, 0, -1.3, false)
check("bedna chytá do BOX_CATCH_DISTANCE i když je plošina blíž", i == 1 and onPlate == false, tostring(d))
i, d, onPlate = PS.getNearestPad(v, 0, 0, -1.7, false)
check("za BOX_CATCH_DISTANCE vyhrává bližší plošina", i == 1 and onPlate == true, tostring(d))
v, spec = newMini("S", true, 0)
i, d, onPlate, move = PS.getNearestPad(v, 1.2, 0, -0.5, true)
check("dron na plošině: bok bedny přendá do bedny", i == 1 and onPlate == false and move == true, tostring(d))
check("bod pro míření: bedna / plošina", PS.getSpotNode(v, 1, false) == "box" and PS.getSpotNode(v, 1, true) == "plate")
spec.pad = nil
spots = PS.getSpots(v, 1)
check("vlek bez bedny: jedno místo na uzlu dronu", #spots == 1 and spots[1].onPlate == nil and spots[1].x == 9)
P.getSpotPosition = realSpot

-- ------------------------------------------------------------------ příkazy
check("PLACE_PLATE se liší a vejde do CMD_BITS", E.PLACE_PLATE ~= E.PLACE and E.PLACE_PLATE ~= E.TAKE and E.PLACE_PLATE < 2 ^ E.CMD_BITS)
local placed = {}
local realPlace = PS.doPlace
PS.doPlace = function(_, _, _, padIndex, _, onPlate) placed[#placed + 1] = { padIndex, onPlate } end
v, spec = newMini("", false, 0)
PS.command(v, E.PLACE_PLATE, 1, {}, {}, true)
PS.command(v, E.PLACE, 1, {}, {}, true)
check("PLACE_PLATE -> na plošinu, PLACE -> do bedny", #placed == 2 and placed[1][2] == true and placed[2][2] == false)
PS.doPlace = realPlace
local cmds = { E.PLACE, E.TAKE, E.PLACE_PLATE, E.MOVE_BOX, E.MOVE_PLATE }
local distinct, fits = {}, true
for _, c in ipairs(cmds) do distinct[c] = true; fits = fits and c < 2 ^ E.CMD_BITS end
local count = 0
for _ in pairs(distinct) do count = count + 1 end
check("MOVE_BOX / MOVE_PLATE: různé hodnoty, vejdou se do CMD_BITS", count == #cmds and fits)
check("předmět nesou jen PLACE / PLACE_PLATE", E.hasItem(E.PLACE) and E.hasItem(E.PLACE_PLATE) and not E.hasItem(E.TAKE)
    and not E.hasItem(E.MOVE_BOX) and not E.hasItem(E.MOVE_PLATE))
v, spec = newMini("S", false, 0)
PS.command(v, E.MOVE_PLATE, 1, nil, {}, true)
check("MOVE_PLATE: složený dron z bedny na plošinu", spec.pad.onPlate == true and v.dirty > 0)
check("MOVE_PLATE: okamžitě rozložený, bez skládací sekvence", spec.unfold == 1 and spec.foldHold == nil and spec.padSlots.folding[1] == nil,
    spec.unfold)
spec.rotorSpeed, spec.hoseT, spec.rotors[1].angle = 5, 0.4, 1.2
PS.command(v, E.MOVE_BOX, 1, nil, {}, true)
check("MOVE_BOX: rozložený dron hned v bedně, složený", spec.pad.onPlate == false and spec.unfold == 0 and spec.foldHold == nil
    and spec.padSlots.folding[1] == nil, spec.unfold)
check("MOVE_BOX: vrtule v klidu, hadice namotaná", spec.rotorSpeed == 0 and spec.rotors[1].angle == 0 and spec.hoseT == 0)
PS.update(v)
check("MOVE_BOX: update už nic nepřesouvá", spec.pad.onPlate == false and spec.foldHold == nil)
v.foldTime = 1
PS.command(v, E.MOVE_PLATE, 1, nil, {}, true)
check("MOVE_PLATE u složené bedny nic neudělá", spec.pad.onPlate == false and spec.padSlots.folding[1] == nil)

-- ------------------------------------------------------------------ ladicí přendání
v, spec = newMini("S", false, 0)
local problem = PS.debugMoveMini(v, true)
check("padMiniDeploy: složený dron z bedny hned na plošinu", problem == nil and spec.pad.onPlate == true and v.dirty > 0, problem)
check("setDroneOnPlate vynutí přepočet pózy", spec.pad.appliedTime == nil and spec.pad.settle >= 1)
spec.unfold = 1
problem = PS.debugMoveMini(v, false)
check("padMiniStow: rozložený dron hned v bedně, bez foldHold", problem == nil and spec.pad.onPlate == false and spec.unfold == 0
    and spec.foldHold == nil and spec.padSlots.folding[1] == nil, problem)
v.foldTime = 0.5
problem = PS.debugMoveMini(v, true)
check("padMiniDeploy u napůl složené bedny odmítnuto", problem == "sdt_pad_boxStowed" and spec.pad.onPlate == false, problem)

-- ------------------------------------------------------------------ odepnutí (TAKE): složit, pak předmět přesně na místě dronu
local realGWT, realSetPad = getWorldTranslation, S.setPadDrone
local nodePos = { drone = { 10, 2.5, 20 }, plate = { 4, 0.6, 30 }, middleDrone = { -3, 2.505, 7 } }
local nodeRot = { drone = 0.3, plate = -1.1, middleDrone = 2.0 }
local poses, linked = {}, {}
createTransformGroup = function(name) local p = { name = name }; poses[#poses + 1] = p; return p end
link = function(parent, child) child.parent = parent; linked[#linked + 1] = parent end
setTranslation = function(n, x, y, z) n.t = { x, y, z } end
setRotation = function(n, x, y, z) n.r = { x, y, z } end
delete = function(n) n.deleted = true end
getWorldTranslation = function(n)
    if type(n) == "table" then local p = nodePos[n.parent]; return p[1] + n.t[1], p[2] + n.t[2], p[3] + n.t[3] end
    return unpack(nodePos[n])
end
getWorldRotation = function(n) return n.r[1], nodeRot[n.parent] + n.r[2], n.r[3] end
local loads, notes = {}, {}
VehicleLoadingData = { new = function()
    local d = { isValid = false }
    function d:setFilename() self.isValid = true end
    function d:setPosition(x, y, z) self.pos = { x, y, z } end
    function d:setRotation(x, y, z) self.rot = { x, y, z } end
    function d:setPropertyState() end
    function d:setOwnerFarmId() end
    function d:load(cb) self.cb = cb; loads[#loads + 1] = self end
    return d
end }
g_storeManager = { getItemByXMLFilename = function() return { xmlFilename = "drone.xml" } end }
g_currentMission.slotSystem = { getCanAddLimitedObjects = function() return true end }
SprayDroneRelaySlots.helpers = { notifyLocal = function(_, _, key) notes[#notes + 1] = key end, isAlive = function() return true end,
    getPlayerPosition = function() return 100, 0, 100 end, getHeldNode = function() return nil end }
local padSet = {}
S.setPadDrone = function(veh, padIndex, variant) padSet[#padSet + 1] = variant; veh[S.SPEC_NAME].pads[padIndex] = variant end
local function near(a, b) return math.abs(a - b) < 1e-6 end
local function takeOk(d, node)
    local p = nodePos[node]
    return d ~= nil and near(d.pos[1], p[1]) and near(d.pos[2], p[2] + PS.TAKE_LIFT) and near(d.pos[3], p[3])
        and near(d.rot[2], nodeRot[node] + PS.ITEM_YAW) and d.rot[1] == 0 and d.rot[3] == 0
end
local function finishLoad(d)
    d.cb(nil, { { id = 99, delete = function() end } }, VehicleLoadingState.OK)
end

-- Mini, dron v bedně (složený): odepne se hned, předmět na místě dronu, ne u hráče (hráč 100, 0, 100)
v, spec = newMini("S", false, 0)
v.getOwnerFarmId = function() return 1 end
PS.command(v, E.TAKE, 1, nil, {}, true)
check("TAKE v bedně: předmět se vyrábí hned (dron je složený)", #loads == 1 and spec.foldHold == nil, #loads)
check("TAKE v bedně: poloha = uzel dronu + TAKE_LIFT, ne u hráče", takeOk(loads[1], "drone"),
    loads[1] and string.format("%.2f %.2f %.2f", unpack(loads[1].pos)))
check("TAKE: natočení = kořen dronu + ITEM_YAW, pomocný uzel na kořeni dronu a smazaný", linked[#linked] == "drone" and poses[#poses].deleted)
check("TAKE: předmět vznikne malinko nad plošinou (0 < lift <= 0.1 m)", PS.TAKE_LIFT > 0 and PS.TAKE_LIFT <= 0.1)
check("TAKE: plošina obsazená, dokud se předmět nenačte", spec.pads[1] == "S" and #padSet == 0)
finishLoad(loads[1])
check("TAKE: po načtení předmětu plošina prázdná", spec.pads[1] == "" and padSet[1] == "" and #notes == 0, table.concat(notes, ","))

-- Mini, rozložený dron na plošině: nejdřív se na místě složí, teprve pak předmět (v poloze plošiny)
loads, padSet, notes = {}, {}, {}
v, spec = newMini("S", true, 0)
v.getOwnerFarmId = function() return 1 end
spec.unfold = 1
spec.padSlots.nodes[1] = "plate"
PS.command(v, E.TAKE, 1, nil, {}, true)
check("TAKE rozloženého: nejdřív složení (foldHold), předmět ještě ne", #loads == 0 and spec.foldHold == true and spec.padSlots.folding[1] ~= nil)
check("TAKE rozloženého: dron zůstal na plošině", spec.pad.onPlate == true and spec.pads[1] == "S")
PS.update(v)
check("TAKE: dokud se skládá, předmět nevzniká", #loads == 0)
spec.unfold = 0
PS.update(v)
check("TAKE: po složení předmět přesně na plošině", #loads == 1 and takeOk(loads[1], "plate") and spec.padSlots.folding[1] == nil)
finishLoad(loads[1])
check("TAKE: foldHold pryč, plošina prázdná", spec.foldHold == nil and spec.pads[1] == "")

-- Middle / Max: bez bedny, dron se bere ze skutečného kořene dronu (drone.node), ne z uzlu plošiny
loads, padSet, notes = {}, {}, {}
v, spec = newMini("S", false, 0)
v.getOwnerFarmId = function() return 1 end
spec.pad = nil
spec.node = "middleDrone"
PS.command(v, E.TAKE, 1, nil, {}, true)
check("TAKE Middle/Max: poloha a natočení z kořene dronu na palubě", #loads == 1 and takeOk(loads[1], "middleDrone"))

getWorldTranslation, S.setPadDrone = realGWT, realSetPad

-- ------------------------------------------------------------------ síť
local stream = {}
streamWriteUIntN = function(_, value) stream[#stream + 1] = value end
streamWriteBool = function(_, value) stream[#stream + 1] = value end
local pos = 0
streamReadUIntN = function() pos = pos + 1; return stream[pos] end
streamReadBool = function() pos = pos + 1; return stream[pos] end
local applied = 0
local realApply = S.applyPads
S.applyPads = function() applied = applied + 1 end
local src = newMini("S", true, 0)
src[S.SPEC_NAME].batteryVariant = "S"
local dst, dspec = newMini("S", false, 0)
dspec.batteryVariant = "S"
S.writePads(src, 1)
local written = #stream
S.readPads(dst, 1)
check("bit polohy dojde klientovi", dspec.pad.onPlate == true and pos == written, string.format("%d/%d", pos, written))
check("jen změna polohy dron nepřenačte", applied == 0)
stream, pos = {}, 0
local maxV = newMini("S", false, 0)
maxV[S.SPEC_NAME].pad = nil
S.writePads(maxV, 1)
check("vlek bez bedny bit nepíše", #stream == written - 1, #stream)
S.applyPads = realApply

-- ------------------------------------------------------------------ hadice jen u postřikového dronu
local visible = {}
setVisibility = function(node, value) visible[node] = value end
local realLayout = S.layoutHose
S.layoutHose = function() end
local function hoseCase(variant, unfold)
    local hv, hspec = newMini(variant, true, 0)
    hspec.droneName = variant
    hspec.clamps = {}
    hspec.unfold = unfold
    hspec.hose = { segments = { "seg1", "seg2" }, nozzle = "nozzle", coil = "coil", park = "park", lay = {} }
    hspec.hose.spray = S.getHasSprayDrone(hv)
    visible = {}
    S.updateDroneServiceVisuals(hv, 16)
    return hspec.hose, visible
end
check("postřikový dron: getHasSprayDrone", (function() local hv, hs = newMini("S", true, 0); hs.droneName = "S"; return S.getHasSprayDrone(hv) end)())
check("skenovací dron není postřikový", not (function() local hv, hs = newMini("K", true, 0); hs.droneName = "K"; return S.getHasSprayDrone(hv) end)())
check("prázdná plošina: není postřikový", not (function() local hv, hs = newMini("", true, 0); hs.droneName = ""; return S.getHasSprayDrone(hv) end)())
local hose, vis = hoseCase("S", 1)
check("rozložený postřikový dron: hadice vidět, navíječ ne", vis.seg1 == true and vis.seg2 == true and vis.nozzle == true and vis.coil == false)
hose, vis = hoseCase("", 1)
check("prázdná plošina na rozloženém vleku: hadice schovaná, navíječ vidět", vis.seg1 == false and vis.nozzle == false and vis.coil == true)
hose, vis = hoseCase("K", 1)
check("skenovací dron: hadice schovaná", vis.seg1 == false and vis.nozzle == false and vis.coil == true)
hose, vis = hoseCase("S", 0)
check("složený postřikový dron (Mini v bedně): hadice namotaná", vis.seg1 == false and vis.coil == true)
-- výměna dronu za hry: loadDroneService postaví novou hadici (shown = nil), první update ji srovná
local hv, hspec = newMini("S", true, 0)
hspec.droneName, hspec.clamps, hspec.unfold = "S", {}, 1
hspec.hose = { segments = { "seg1" }, nozzle = "nozzle", coil = "coil", park = "park", lay = {}, spray = true }
S.updateDroneServiceVisuals(hv, 16)
hspec.pads[1], hspec.hasDrone, hspec.droneName = "", false, ""
hspec.hose = { segments = { "seg1" }, nozzle = "nozzle", coil = "coil", park = "park", lay = {}, spray = S.getHasSprayDrone(hv) }
visible = {}
S.updateDroneServiceVisuals(hv, 16)
check("sundání dronu za hry: hadice zmizí", visible.seg1 == false and visible.nozzle == false and visible.coil == true)
S.layoutHose = realLayout

-- Max: prázdná plošina 2 po načtení
local mapping = {}
for _, name in ipairs({ "padClampL2", "padClampR2", "fillHoseBCoil", "fillHoseBNozzle", "fillHoseBSeg1", "fillHoseBSeg2" }) do
    mapping[name] = { nodeId = name }
end
local maxV = { i3dMappings = mapping }
local maxSpec = { numPads = 2, numDrones = 1, secondVariants = { S = { key = "k2" } } }
maxV[S.SPEC_NAME] = maxSpec
local xmlStub = { getValue = function(_, key) if key == "k2#hosePrefix" then return "fillHoseB" end end }
visible = {}
S.stowSecondPad(maxV, xmlStub)
check("Max bez dronu 2: hadice B schovaná, navíječ B a úchyty 2", visible.fillHoseBSeg1 == false and visible.fillHoseBSeg2 == false
    and visible.fillHoseBNozzle == false and visible.fillHoseBCoil == true and visible.padClampL2 == false and visible.padClampR2 == false)
maxSpec.numDrones = 2
visible = {}
S.stowSecondPad(maxV, xmlStub)
check("Max s dronem 2: stowSecondPad nic nemění", next(visible) == nil)

return table.concat(out, "\n"), fails
''')
text, fails = result
print(text)
print(f"\n{'OK' if fails == 0 else 'CHYBY: ' + str(fails)}")
sys.exit(1 if fails else 0)
