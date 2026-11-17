# Ruční zkouška násypky na jemné vápno bez hry (LuaJIT/lupa + exportovaný model): python tools/test_hopper.py
# SprayDroneHopper: opěry do kříže (směr z osy ramene, šikmé vysunutí, patka klesá až po vysunutí ramene), pravidla opěr (big bag sype jen s vysunutými
# opěrami, s vakem na stolici nejdou ovládat); limeHopper.i3d / .xml / blender/limeHopper_geometry.json: kolize patek,
# vysunuté mimo půdorys rámu, větší opěrná plocha, centerOfMass v XML podle spočteného těžiště a blízko středu stolice.
# Kolize patek stojí pevně ve vysunuté poloze (skupina collisions, ne pod ramenem), jsou nejnižším bodem kolizí (1 cm pod rámem), vizuální patka po
# poklesu drop sedí přesně na nich a skript jim zapíná filtr z i3d jen s celými vysunutými opěrami.
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from lupa import luajit21

root = Path(__file__).resolve().parent.parent
mod = root / "mod" / "FS25_SprayDroneTrailer"
scripts = mod / "scripts"
I3D = mod / "objects" / "hopper" / "limeHopper.i3d"
XML = mod / "objects" / "hopper" / "limeHopper.xml"
GEOMETRY = root / "blender" / "limeHopper_geometry.json"

out, fails = [], 0


def check(name, ok, info=None):
    global fails
    if not ok:
        fails += 1
    out.append(f"{'ok  ' if ok else 'FAIL'}  {name}{'  ' + str(info) if info is not None else ''}")


geo = json.loads(GEOMETRY.read_text(encoding="utf-8"))
xml = ET.parse(XML).getroot()
legs_xml = xml.find("sprayDroneHopper/legs")
travel, drop = float(legs_xml.get("travel")), float(legs_xml.get("drop"))

# ------------------------------------------------------------------ Lua
lua = luajit21.LuaRuntime(unpack_returned_tuples=True)
g = lua.globals()
g.SCRIPTS = str(scripts)
g.TRAVEL, g.DROP = travel, drop
g.LEGS = lua.table_from([lua.table_from(leg["pos"] + leg["dir"]) for leg in geo["legs"]])
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
Logging = { info = function() end, warning = function() end, xmlWarning = function() end }
ToolType = { UNDEFINED = 0, DISCHARGEABLE = 7, TRIGGER = 3 }
g_time = 100000
g_currentModDirectory = ""
g_currentModName = "FS25_SprayDroneTrailer"
SprayDroneSound = { noteAction = function() end }
source = function() end
entityExists = function(node) return node ~= nil end
POS, AXIS = {}, {}
setTranslation = function(node, x, y, z) POS[node] = { x, y, z } end
getTranslation = function(node) local p = POS[node]; return p[1], p[2], p[3] end
getParent = function(node) return 0 end
localDirectionToLocal = function(node, parent, x, y, z) local a = AXIS[node]; return a[1], 0, a[2] end
FILTER = {}
getCollisionFilterGroup = function(node) return 0x10000 end
getCollisionFilterMask = function(node) return 0xfffdfbff end
setCollisionFilter = function(node, group, mask) FILTER[node] = { group, mask } end
dofile(SCRIPTS .. "/SprayDroneMill.lua")
dofile(SCRIPTS .. "/SprayDroneHopper.lua")
local H = SprayDroneHopper

-- ------------------------------------------------------------------ směr opěry z osy ramene
local x, z = H.getLegDirection(0.57, 0.55, 0.7071, 0.7071)
check("osa ramene šikmo ven: směr beze změny", near(x, 0.7071, 1e-3) and near(z, 0.7071, 1e-3))
x, z = H.getLegDirection(-0.57, -0.55, 0.7071, 0.7071)
check("osa ramene míří dovnitř: otočí se ven", near(x, -0.7071, 1e-3) and near(z, -0.7071, 1e-3))
x, z = H.getLegDirection(0.5, 0.5, 2, 0)
check("osa se normalizuje", near(x, 1) and near(z, 0))
x, z = H.getLegDirection(-0.5, 0.2, 0, 0)
check("bez osy: po znaménku x", x == -1 and z == 0)

-- ------------------------------------------------------------------ onLoad: opěry z exportované polohy a natočení ramen
local values = { ["vehicle.sprayDroneHopper.legs#travel"] = TRAVEL, ["vehicle.sprayDroneHopper.legs#drop"] = DROP }
local legNodes = {}
for i, leg in ipairs(LEGS) do
    local node, foot = 100 + i, 200 + i
    POS[node] = { leg[1], leg[2], leg[3] }
    POS[foot] = { 0, -0.045, 0 }
    -- osa x ramene v rodiči: (cos b, 0, -sin b) pro natočení b kolem Y; export dá rameni přesně směr opěry
    AXIS[node] = { leg[4], leg[5] }
    legNodes[i] = { node = node, foot = foot, col = 300 + i }
end
local xmlFile = {}
function xmlFile:getValue(key, default, components, mappings)
    if values[key] ~= nil then return values[key] end
    local i = key:match("leg%((%d+)%)#node")
    if i ~= nil then return legNodes[tonumber(i) + 1].node end
    i = key:match("leg%((%d+)%)#foot")
    if i ~= nil then return legNodes[tonumber(i) + 1].foot end
    i = key:match("leg%((%d+)%)#collision")
    if i ~= nil then return legNodes[tonumber(i) + 1].col end
    return default
end
function xmlFile:iterate(key, fn)
    for i = 1, #legNodes do fn(i, string.format("%s(%d)", key, i - 1)) end
end
local hopper = { isServer = true, isClient = false, xmlFile = xmlFile, rootNode = 31 }
hopper[H.SPEC_NAME] = {}
function hopper:getNextDirtyFlag() return 1 end
function hopper:raiseDirtyFlags() end
function hopper:raiseActive() end
WOKEN = 0
function hopper:wakeUp() WOKEN = WOKEN + 1 end
H.onLoad(hopper, nil)
local hs = hopper[H.SPEC_NAME]
check("načtené 4 opěry, travel z XML", #hs.legs == 4 and near(hs.legTravel, TRAVEL), #hs.legs)
local function feetFilter(group, mask)
    for i = 1, 4 do
        local f = FILTER[300 + i]
        if f == nil or f[1] ~= group or f[2] ~= mask then return false end
    end
    return true
end
check("po načtení zasunuté: kolize patek vypnuté (filtr 0, 0), tělo se nebudí", feetFilter(0, 0) and WOKEN == 0 and hs.feetCarry == false)
local quadrants = {}
for i, leg in ipairs(hs.legs) do
    local outward = leg.ux * leg.x + leg.uz * leg.z > 0
    local diagonal = near(math.abs(leg.ux), math.abs(leg.uz), 0.02) and near(leg.ux * leg.ux + leg.uz * leg.uz, 1, 1e-6)
    check(string.format("opěra %d: směr šikmo ven pod 45° (%.3f, %.3f)", i, leg.ux, leg.uz), outward and diagonal)
    quadrants[(leg.ux > 0 and "+" or "-") .. (leg.uz > 0 and "+" or "-")] = true
end
local nq = 0
for _ in pairs(quadrants) do nq = nq + 1 end
check("opěry do kříže: každá do jiného rohu", nq == 4, nq)

-- ------------------------------------------------------------------ pohyb opěr
local function moved(leg)
    local p = POS[leg.node]
    return math.sqrt((p[1] - leg.x) ^ 2 + (p[3] - leg.z) ^ 2), p[2] - leg.y
end
hs.legsPos = H.LEGS_SLIDE / 2
H.applyLegs(hs)
local d, dy = moved(hs.legs[1])
check("v půli vysouvání: rameno šikmo o polovinu travel, patka nahoře", near(d, TRAVEL / 2, 1e-4) and near(dy, 0) and near(POS[hs.legs[1].foot][2], -0.045),
    string.format("%.3f", d))
hs.legsPos = 1
H.applyLegs(hs)
for i, leg in ipairs(hs.legs) do
    local p = POS[leg.node]
    check(string.format("opěra %d vysunutá: rameno o travel po svém směru, výška ramene stejná, patka o drop níž", i),
        near(p[1], leg.x + leg.ux * TRAVEL, 1e-6) and near(p[3], leg.z + leg.uz * TRAVEL, 1e-6) and near(p[2], leg.y)
        and near(POS[leg.foot][2], -0.045 - DROP, 1e-6))
end
hs.legsPos = 0
H.applyLegs(hs)
check("zasunuto: rameno zpět na místě z i3d", near(POS[hs.legs[2].node][1], hs.legs[2].x) and near(POS[hs.legs[2].node][3], hs.legs[2].z))

-- ------------------------------------------------------------------ kolize patek: filtr podle polohy opěr, nic se neposouvá
hs.legsOut = true
local carryAt = {}
for _, t in ipairs({ 0, 0.5, H.LEGS_SLIDE, 0.99 }) do
    hs.legsPos = t
    H.onUpdate(hopper, 0)
    carryAt[#carryAt + 1] = FILTER[301][1]
end
check("vysouvání: patky nenesou, dokud opěry nejsou celé venku", carryAt[1] == 0 and carryAt[2] == 0 and carryAt[3] == 0 and carryAt[4] == 0)
hs.legsPos = 1
H.onUpdate(hopper, 0)
check("opěry venku: kolize patek s filtrem z i3d (jako rám), tělo se probudí", feetFilter(0x10000, 0xfffdfbff) and WOKEN == 1 and H.getFeetCarry(hs))
for i = 1, 4 do POS[300 + i] = nil end
H.onUpdate(hopper, 0)
check("další snímek venku: filtr se znovu nenastavuje, tělo se nebudí", WOKEN == 1)
check("kolize patek se nikdy neposouvají (setTranslation na ně nesahá)", POS[301] == nil and POS[302] == nil and POS[303] == nil and POS[304] == nil)
hs.legsOut = false
H.onUpdate(hopper, 0)
check("začátek zasouvání (poloha ještě 1): patky hned nenesou", feetFilter(0, 0) and WOKEN == 2, hs.legsPos)
hs.legsPos = 0
H.onUpdate(hopper, 0)
check("zasunuto: patky dál vypnuté", feetFilter(0, 0) and WOKEN == 2)
local loaded = { isServer = false, isClient = false, xmlFile = xmlFile, rootNode = 32 }
loaded[H.SPEC_NAME] = {}
function loaded:getNextDirtyFlag() return 1 end
FILTER = {}
local saved = { resetVehicles = false, key = "v", xmlFile = { getValue = function() return true end } }
loaded.isServer = true
WOKEN = 0
function loaded:wakeUp() WOKEN = WOKEN + 1 end
H.onLoad(loaded, saved)
check("načtení uložené hry s vysunutými opěrami: patky nesou hned po načtení", feetFilter(0x10000, 0xfffdfbff) and loaded[H.SPEC_NAME].legsPos == 1)
FILTER = {}
local client = { isServer = false, isClient = false, xmlFile = xmlFile, rootNode = 33 }
client[H.SPEC_NAME] = {}
function client:getNextDirtyFlag() return 1 end
H.onLoad(client, nil)
streamReadBool = function() return true end
H.onReadStream(client, 1, nil)
check("klient v MP (stav ze streamu: vysunuté): patky nesou i u něj", feetFilter(0x10000, 0xfffdfbff))
hs.legsOut, hs.legsPos = false, 0

-- ------------------------------------------------------------------ pravidla opěr
hs.pour.pourNeck = 30
WORLD = { [30] = { 0, 1.42, 0 }, [31] = { 0, 0, 0 } }
getWorldTranslation = function(node) local p = WORLD[node]; return p[1], p[2], p[3] end
g_currentMission = { vehicleSystem = { vehicles = { hopper } } }
local function super() return true end
local function bagOk() return H.getFillUnitSupportsToolType(hopper, super, hs.limeUnit, ToolType.DISCHARGEABLE) end
check("zasunuté opěry: vak nesype", bagOk() == false)
check("zasunuté opěry: pytel / hadice ano", H.getFillUnitSupportsToolType(hopper, super, hs.limeUnit, ToolType.UNDEFINED) == true)
check("nafta (fill unit 1) vakem ano", H.getFillUnitSupportsToolType(hopper, super, 1, ToolType.DISCHARGEABLE) == true)
H.command(hopper, H.CMD_LEGS_OUT, true)
check("příkaz vysunout", hs.legsOut == true)
hs.legsPos = 0.99
check("opěry ještě v pohybu: vak nesype", bagOk() == false)
hs.legsPos = 1
check("opěry venku: vak sype", bagOk() == true)

local bag = { rootNode = 40, spec_dischargeable = {} }
table.insert(g_currentMission.vehicleSystem.vehicles, bag)
local function bagAt(x, y, z) WORLD[40] = { x, y, z } end
bagAt(0.05, 1.40, -0.03)
check("vak na stolici se najde", H.findStoolBag(hopper) == bag)
H.command(hopper, H.CMD_LEGS_IN, true)
check("s vakem na stolici opěry nejdou zasunout", hs.legsOut == true and bagOk() == true)
bagAt(H.STOOL_BLOCK_REACH - 0.01, 1.40, 0)
check("vak 0,79 m stranou (STOOL_BLOCK_REACH 0,8) pořád blokuje", H.findStoolBag(hopper) == bag)
bagAt(0, 1.40, H.STOOL_BLOCK_REACH + 0.01)
check("vak 0,81 m stranou už neblokuje", H.findStoolBag(hopper) == nil)
bagAt(0, 1.40 - H.STOOL_BLOCK_DEPTH + 0.02, 0)
check("vak propadlý do nástavce blokuje", H.findStoolBag(hopper) == bag)
bagAt(0, 0.0, 0.3)
check("vak na zemi u násypky neblokuje", H.findStoolBag(hopper) == nil)
bagAt(0, 1.62, 0)
check("vak nesený nakladačem 0,2 m nad rámem neblokuje", H.findStoolBag(hopper) == nil)
H.command(hopper, H.CMD_LEGS_IN, true)
check("bez vaku na stolici opěry jdou zasunout", hs.legsOut == false)
bagAt(0.1, 1.40, 0.1)
H.command(hopper, H.CMD_LEGS_OUT, true)
check("s vakem na stolici opěry nejdou vysunout", hs.legsOut == false and bagOk() == false)
check("CMD_BITS stačí na příkazy opěr", H.CMD_LEGS_IN < 2 ^ H.CMD_BITS)

return { out = out, fails = fails }
''')
for line in result["out"].values():
    out.append(line)
fails += result["fails"]

# ------------------------------------------------------------------ sypání z pytle do násypky a do koncentrátové nádrže vleku
# Regrese 2026-10-29 (Pavel: „z pytlů nejde sypat do násypky ani do nádrže na koncentrát na Maxovi a Middle“): pytel držený v rukou se k ústí
# nedostane (kloub rukou se o kolize stolice / nádrže utrhne nebo předmět odtlačí), proto se u drženého měří od hráče; pytel sype hubicí dolů.
lua2 = luajit21.LuaRuntime(unpack_returned_tuples=True)
lua2.globals().SCRIPTS = str(scripts)
pour = lua2.execute(r'''
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
Logging = { info = function() end, warning = function() end, xmlWarning = function() end }
ToolType = { UNDEFINED = 0 }
FillType = { UNKNOWN = 0, DIESEL = 3, SDT_FINE_LIME = 7, SDT_CONCENTRATE_FERTILIZER = 8 }
g_time = 100000
g_currentModDirectory = ""
g_currentModName = "FS25_SprayDroneTrailer"
source = function() end
math.clamp = function(v, a, b) return math.max(a, math.min(b, v)) end
MathUtil = { vector3Length = function(x, y, z) return math.sqrt(x * x + y * y + z * z) end }
entityExists = function(node) return node ~= nil end
-- uzly: POSW = poloha kořene ve světě, AX = světové osy jeho x, y, z; CAP = { rodič, místní poloha }
POSW, AX, CAP = {}, {}, {}
localDirectionToWorld = function(node, a, b, c)
    local r = AX[node]
    return a * r[1][1] + b * r[2][1] + c * r[3][1], a * r[1][2] + b * r[2][2] + c * r[3][2], a * r[1][3] + b * r[2][3] + c * r[3][3]
end
localToWorld = function(node, a, b, c)
    local dx, dy, dz = localDirectionToWorld(node, a, b, c)
    local p = POSW[node]
    return p[1] + dx, p[2] + dy, p[3] + dz
end
getWorldTranslation = function(node)
    local c = CAP[node]
    if c ~= nil then return localToWorld(c[1], c[2], c[3], c[4]) end
    local p = POSW[node]
    return p[1], p[2], p[3]
end
SprayDroneStation = { SPEC_NAME = "spec_station", getMappedNode = function(v, name) return name == "canisterCap" and v.capNode or nil end }
dofile(SCRIPTS .. "/SprayDroneToolbox.lua")
dofile(SCRIPTS .. "/SprayDroneMill.lua")
local T, M = SprayDroneToolbox, SprayDroneMill

-- natočení: osa x pytle (hubice) skloněná o `down` stupňů pod vodorovnou (kolem osy z), nebo převalený na bok o `roll` (kolem osy x)
local function orient(node, down, roll)
    local a, r = math.rad(down or 0), math.rad(roll or 0)
    if roll ~= nil then
        AX[node] = { { 1, 0, 0 }, { 0, math.cos(r), math.sin(r) }, { 0, -math.sin(r), math.cos(r) } }
    else
        AX[node] = { { math.cos(a), -math.sin(a), 0 }, { math.sin(a), math.cos(a), 0 }, { 0, 0, 1 } }
    end
end
-- pytel tak, aby víčko (hubice) bylo v bodě x, y, z
local function bagCapAt(bag, x, y, z)
    POSW[bag.rootNode] = { 0, 0, 0 }
    local cx, cy, cz = localToWorld(bag.rootNode, 0.3744, 0.07488, 0)
    POSW[bag.rootNode] = { x - cx, y - cy, z - cz }
end
local function newItem(id, file, liters, kind)
    local item = { rootNode = id, capNode = id + 1, configFileName = "C:/mods/FS25_SprayDroneTrailer/" .. file, spec_pallet = {}, spec_fillUnit = {},
        liters = liters, id = id }
    CAP[id + 1] = { id, 0.3744, 0.07488, 0 }
    function item:getFillUnitFillLevel() return self.liters end
    function item:addFillUnitFillLevel(_, _, delta) self.liters = self.liters + delta; return delta end
    orient(id, 0)
    POSW[id] = { 50, 0, 50 }
    return item
end
local bag = newItem(40, "objects/limeBag/limeBag50.xml", 50)
check("pytel limeBag50 se pozná jako SDT_FINE_LIME", T.getCanisterKind(bag) == FillType.SDT_FINE_LIME)

local player = { hands = { spec_hands = {} } }
local PX, PY, PZ = 0, 0, 0
function player:getPosition() return PX, PY, PZ end
local function hold(item) player.hands.spec_hands.heldItemNode = item ~= nil and item.rootNode or nil end
local vehicles = { bag }
g_currentMission = { vehicleSystem = { vehicles = vehicles }, playerSystem = { players = { player } },
    accessHandler = { canFarmAccess = function() return true end } }

-- násypka: hrdlo pytlů = hopperFunnel (0, 1,42, 0), zásoba 400 l, parametry jako SprayDroneHopper.onLoad / limeHopper.xml
POSW[30] = { 0, 1.42, 0 }
local hopper = { level = 0, rootNode = 31 }
function hopper:getFillUnitFreeCapacity() return 400 - self.level end
function hopper:getFillUnitFillLevel() return self.level end
function hopper:addFillUnitFillLevel(_, _, delta) self.level = self.level + delta; return delta end
function hopper:getOwnerFarmId() return 1 end
local spec = { pourUnit = 2, pourNeck = 30, pourKind = FillType.SDT_FINE_LIME, pourBelow = 0.35, pourRadius = 0.5, pourRate = 8, pourAcc = 0, pourTimer = 0 }
local function pourHopper()
    local before = hopper.level
    spec.pourTimer = 0
    M.updatePour(hopper, 500, spec)
    return hopper.level - before
end

-- hráč stojí 0,9 m od osy násypky (za rámem), pytel drží hubicí dolů, ale kloub rukou ho drží 1,2 m stranou a níž (víčko daleko od ústí)
PX, PY, PZ = 0, 0, 0.9
hold(bag)
orient(bag.rootNode, 90)
bagCapAt(bag, 0, 1.1, 2.1)
local moved = pourHopper()
check("držený pytel hubicí dolů, hráč u násypky, pytel odtlačený od ústí: sype do násypky", moved > 1, string.format("%.2f l", moved))
check("co přibylo v násypce, ubylo z pytle", math.abs(bag.liters - (50 - moved)) < 1e-6)
orient(bag.rootNode, 60)
check("držený pytel hubicí 60° dolů: sype", pourHopper() > 0)
orient(bag.rootNode, 15)
check("držený pytel hubicí jen 15° dolů: nesype", pourHopper() == 0)
orient(bag.rootNode, 90)
AX[bag.rootNode] = { { -0, 1, 0 }, { 1, 0, 0 }, { 0, 0, -1 } }
check("držený pytel hubicí nahoru: nesype", pourHopper() == 0)
orient(bag.rootNode, nil, 90)
check("držený pytel převalený na bok (hubice vodorovně): nesype", pourHopper() == 0)
orient(bag.rootNode, 90)
PX, PY, PZ = 0, 0, 2.5
check("hráč s pytlem 2,5 m od násypky: nesype", pourHopper() == 0)
hold(nil)
PX, PY, PZ = 0, 0, 0.9
check("položený pytel (nikdo ho nedrží) daleko od ústí: nesype", pourHopper() == 0)
bagCapAt(bag, 0.05, 1.45, 0)
check("volný pytel hubicí dolů víčkem u ústí (ladicí hopperBag): sype", pourHopper() > 0)
orient(bag.rootNode, 0)
bagCapAt(bag, 0.05, 1.45, 0)
check("volný pytel naležato víčkem u ústí: nesype", pourHopper() == 0)
local can = newItem(50, "objects/canister/canisterDiesel.xml", 20)
table.insert(vehicles, can)
hold(can)
AX[can.rootNode] = { { 1, 0, 0 }, { 0, -1, 0 }, { 0, 0, -1 } }
check("kanystr nafty dnem vzhůru v rukou u násypky: do zásoby vápna nic", pourHopper() == 0 and can.liters == 20)

-- vlek: koncentrátová nádrž, hrdlo Middle (-0,55, 1,607, 1,25), pourRadius 0,3
local trailer = { rootNode = 60, level = 0 }
POSW[60], POSW[61] = { 0, 0, 0 }, { -0.55, 1.607, 1.25 }
trailer[SprayDroneStation.SPEC_NAME] = { toolbox = { pourRadius = 0.3, neckNode = 61 } }
function trailer:getOwnerFarmId() return 1 end
hold(bag)
orient(bag.rootNode, 90)
bagCapAt(bag, -2.6, 1.2, 1.25)
PX, PY, PZ = -1.4, 0, 1.25
local found = T.findPourCanisters(trailer)
local hasBag = false
for _, n in ipairs(found) do hasBag = hasBag or (n.vehicle == bag and n.kind == FillType.SDT_FINE_LIME and n.holder == player) end
check("vlek: držený pytel hubicí dolů, hráč u hrdla koncentrátu, pytel odtlačený od nádrže: nalévá se", hasBag)
orient(bag.rootNode, nil, 90)
check("vlek: pytel převalený na bok: nenalévá se", #T.findPourCanisters(trailer) == 0)
orient(bag.rootNode, 90)
PX, PY, PZ = -3.5, 0, 1.25
check("vlek: hráč s pytlem 3 m od hrdla: nenalévá se", #T.findPourCanisters(trailer) == 0)
hold(nil)
bagCapAt(bag, -0.5, 1.65, 1.25)
check("vlek: volný pytel hubicí dolů víčkem u hrdla: nalévá se", #T.findPourCanisters(trailer) == 1)
bagCapAt(bag, -0.5, 1.2, 1.25)
check("vlek: volný pytel víčkem 0,4 m pod hrdlem: nenalévá se", #T.findPourCanisters(trailer) == 0)
return { out = out, fails = fails }
''')
for line in pour["out"].values():
    out.append(line)
fails += pour["fails"]

# ------------------------------------------------------------------ exportovaný model
scene = ET.parse(I3D).getroot().find("Scene")
by_name = {e.get("name"): e for e in scene.iter()}
floor = by_name.get("floorCollision01")
collisions = next((e for e in scene.iter("TransformGroup") if e.get("name") == "collisions"), None)
mappings = {m.get("id"): m.get("node") for m in xml.iter("i3dMapping")}
leg_xml = list(legs_xml.iter("leg"))
check("XML legs drop = drop modelu (vizuální patka dosedne na spodek kolize patky)", abs(drop - geo["drop"]) < 1e-6, f"{drop} / {geo['drop']}")
for i in range(1, 5):
    leg, col = by_name.get(f"hopperLeg{i}"), by_name.get(f"hopperFootCol{i}")
    ok = leg is not None and col is not None and collisions is not None and col in list(collisions) and col.get("compoundChild") == "true" \
        and col.get("collisionFilterGroup") == floor.get("collisionFilterGroup") and col.get("collisionFilterMask") == floor.get("collisionFilterMask") \
        and col.get("nonRenderable") == "true" and col.get("trigger") is None and col.get("kinematic") is None
    check(f"limeHopper.i3d: kolize patky {i} je compoundChild pevně ve skupině collisions (ne pod ramenem), filtr jako rám floorCollision01", ok)
    check(f"limeHopper.i3d: rameno a patka {i} nemají kolizi (za běhu se neposouvá žádný kolizní tvar)",
          leg is not None and not any(e.get("compoundChild") == "true" for e in leg.iter()))
    entry = leg_xml[i - 1] if len(leg_xml) >= i else None
    check(f"XML leg {i}: collision=hopperFootCol{i}, mapování do skupiny collisions",
          entry is not None and entry.get("collision") == f"hopperFootCol{i}" and mappings.get(f"hopperFootCol{i}", "").startswith("0>0|"))
    data = next((l for l in geo["legs"] if l["node"] == f"hopperLeg{i}"), None)
    t = [float(v) for v in leg.get("translation").split()]
    b = math.radians(float(leg.get("rotation").split()[1]))
    fresh = data is not None and all(abs(a - c) < 1e-3 for a, c in zip(t, data["pos"])) \
        and abs(math.cos(b) - data["dir"][0]) < 1e-3 and abs(-math.sin(b) - data["dir"][1]) < 1e-3
    check(f"limeHopper_geometry.json sedí s i3d (rameno {i}: poloha a natočení)", fresh)
floor_el = [s for s in scene.iter("Shape") if s.get("name") == "stoolFloor"]
check("limeHopper.i3d: podlaha stolice stoolFloor (compoundChild, skupina 0x10000)",
      len(floor_el) == 1 and floor_el[0].get("compoundChild") == "true" and floor_el[0].get("collisionFilterGroup") == "0x10000")

comp = xml.find("base/components/component")
com_xml = [float(v) for v in comp.get("centerOfMass").split()]
check("XML centerOfMass = spočtené těžiště (±1 cm)", all(abs(a - b) <= 0.01 for a, b in zip(com_xml, geo["centerOfMass"])),
      f"{com_xml} / {geo['centerOfMass']}")
check("XML mass = součet hmotností dílů", abs(float(comp.get("mass")) - geo["mass"]) < 0.01)
check("XML legs travel = travel modelu (pouzdro, kolize)", abs(travel - geo["travel"]) < 1e-6)
sx, sz = geo["stool"][0], geo["stool"][2]
off = math.hypot(com_xml[0] - sx, com_xml[2] - sz)
check("těžiště nejvýš 6 cm od osy stolice", off <= 0.06, f"{off:.3f} m")
check("těžiště nízko (pod 0,5 m)", com_xml[1] <= 0.5, com_xml[1])

(fx0, fy0, fz0), (fx1, fy1, fz1) = geo["floor"]
check("těžiště nad půdorysem rámu", fx0 < com_xml[0] < fx1 and fz0 < com_xml[2] < fz1)
feet_out = []
for leg in geo["legs"]:
    (cx0, cy0, cz0), (cx1, cy1, cz1) = leg["collision"]
    sink = fy0 - cy0
    check(f"{leg['node']}: spodek kolize patky 0,5-2 cm pod spodkem rámu (je nejnižší, vysunutá násypka stojí na patkách)", 0.005 <= sink <= 0.02,
          f"{sink:.3f} m")
    center = leg["collisionCenter"]
    want = (leg["pos"][0] + leg["dir"][0] * travel, leg["pos"][2] + leg["dir"][1] * travel)
    check(f"{leg['node']}: kolize patky leží pod vysunutou patkou (rameno + travel po směru)",
          abs(center[0] - want[0]) < 1e-3 and abs(center[2] - want[1]) < 1e-3, f"{center} / {want}")
    foot_bottom = leg["foot"][1] - drop
    check(f"{leg['node']}: vizuální patka po poklesu sedí na spodku kolize (±2 mm: nezajede do země ani nevisí)",
          abs(foot_bottom - cy0) <= 0.002, f"patka {foot_bottom:.3f} / kolize {cy0:.3f}")
    check(f"{leg['node']}: zasunutá vizuální patka aspoň 3 cm nad spodkem rámu (zasunutou násypku nese rám)", leg["foot"][1] - fy0 >= 0.03,
          leg["foot"][1])
    ex = (cx0, cx1, cz0, cz1)
    outside = ex[0] > fx1 or ex[1] < fx0 or ex[2] > fz1 or ex[3] < fz0
    check(f"{leg['node']}: kolize patky je celá mimo půdorys rámu", outside, f"x {ex[0]:.2f}..{ex[1]:.2f} z {ex[2]:.2f}..{ex[3]:.2f}")
    feet_out.append(ex)


def hull(points):
    pts = sorted(set(points))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def margin(poly, p):
    """Nejkratší vzdálenost bodu uvnitř konvexního mnohoúhelníku k jeho hraně (rameno síly proti převržení)."""
    best = math.inf
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ex, ez = b[0] - a[0], b[1] - a[1]
        best = min(best, abs(ex * (p[1] - a[1]) - ez * (p[0] - a[0])) / math.hypot(ex, ez))
    return best


rect = [(fx0, fz0), (fx1, fz0), (fx1, fz1), (fx0, fz1)]
feet_pts = [(x, z) for x0, x1, z0, z1 in feet_out for x in (x0, x1) for z in (z0, z1)]
p = (com_xml[0], com_xml[2])
m_in, m_out = margin(hull(rect), p), margin(hull(rect + feet_pts), p)
check("vysunuté opěry zvětší rameno proti převržení aspoň o 30 % (nejslabší směr)", m_out >= 1.3 * m_in, f"{m_in:.2f} -> {m_out:.2f} m")
feet_hull = hull(feet_pts)
check("na patkách: těžiště i celý půdorys rámu uvnitř opěrné plochy patek", margin(feet_hull, p) >= 1.3 * m_in
      and all(margin(feet_hull, c) > 0 and min(x for x, _ in feet_pts) < c[0] < max(x for x, _ in feet_pts) for c in rect))

for line in out:
    print(line)
print(f"\n{'OK' if fails == 0 else 'CHYB: ' + str(fails)}")
sys.exit(1 if fails else 0)
