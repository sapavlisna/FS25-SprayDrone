# Ruční zkouška plnění big bagu mlýnkem a opěr násypky bez hry (LuaJIT/lupa): python tools/test_mill_flow.py
# SprayDroneMill: kam teče jemné vápno (motor × ventil × stav roury × pohyb roury × rychlost), hláška složené roury, výstup pro hadici zavřený ventilem,
# cyklus roury (O / klik na kloub), příkazy ventilu a roury na serveru; SprayDroneHopper: big bag sype jen s vysunutými opěrami, pytle vždy, poloha opěr.
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
Logging = { info = function() end, warning = function() end, xmlWarning = function() end }
ToolType = { UNDEFINED = 0, DISCHARGEABLE = 7, TRIGGER = 3 }
g_time = 100000
g_currentModDirectory = ""
g_currentModName = "FS25_SprayDroneTrailer"
SprayDroneSound = { noteAction = function() end }
source = function() end
entityExists = function(node) return node ~= nil end
POS = {}
setTranslation = function(node, x, y, z) POS[node] = { x, y, z } end
dofile(SCRIPTS .. "/SprayDroneMill.lua")
dofile(SCRIPTS .. "/SprayDroneHopper.lua")
local M, H = SprayDroneMill, SprayDroneHopper

-- ------------------------------------------------------------------ kam teče vápno
local names = { "přeprava", "vedle", "za" }
for state = 1, 3 do
    for _, valveSpout in ipairs({ false, true }) do
        for _, engine in ipairs({ false, true }) do
            local target, warning = M.getFlowTarget(engine, valveSpout, state, false, 0)
            local expect
            if not engine then
                expect = nil
            elseif not valveSpout then
                expect = "hose"
            elseif state == M.SPOUT_TRANSPORT then
                expect = nil
            else
                expect = "bag"
            end
            check(string.format("roura %s, ventil %s, motor %s -> %s", names[state], valveSpout and "roura" or "hadice", engine and "běží" or "stojí",
                tostring(expect)), target == expect, tostring(target))
            local expectWarning = engine and valveSpout and state == M.SPOUT_TRANSPORT and "sdt_mill_spoutFolded" or nil
            check(string.format("  hláška (%s, %s, %s)", names[state], tostring(valveSpout), tostring(engine)), warning == expectWarning, tostring(warning))
        end
    end
end
check("roura se otáčí: nesype se, bez hlášky", M.getFlowTarget(true, true, M.SPOUT_SIDE, true, 0) == nil
    and select(2, M.getFlowTarget(true, true, M.SPOUT_SIDE, true, 0)) == nil)
check("vozík jede 1,5 km/h: nesype se", M.getFlowTarget(true, true, M.SPOUT_REAR, false, 1.5) == nil)
check("vozík stojí (0,3 km/h): sype se", M.getFlowTarget(true, true, M.SPOUT_REAR, false, 0.3) == "bag")
check("ventil na hadici za jízdy: hadice (pumpa vleku si bere)", M.getFlowTarget(true, false, M.SPOUT_REAR, true, 20) == "hose")

-- ------------------------------------------------------------------ mlýnek jako vozidlo (server)
local spec = { outlet = 11, fineUnit = 3, fineType = 99, hoseRate = 8, fillHead = 12, valveSpout = false, spoutState = 1, bag = nil,
    bagFlow = { on = false, total = 0, start = 0, last = 0 }, outletUsedTime = -1e9, dirtyFlag = 1 }
local sent = {}
local mill = { isServer = true, dirty = 0 }
mill[M.SPEC_NAME] = spec
function mill:raiseDirtyFlags(f) self.dirty = self.dirty + 1 end
function mill:raiseActive() end
function mill:sprayDroneMillCommand(cmd) sent[#sent + 1] = cmd; M.command(self, cmd, nil, true) end
check("výstup s ventilem na hadici je otevřený", M.getOutlet(mill).closed == false)
M.toggleValve(mill)
check("ventil na rouru", spec.valveSpout == true and mill.dirty == 1)
check("výstup s ventilem na rouře: hadice zůstane, ale je zavřený", M.getOutlet(mill) ~= nil and M.getOutlet(mill).closed == true)
spec.outletUsedTime = g_time
M.toggleValve(mill)
check("ventil jde přepnout i s připojenou hadicí", spec.valveSpout == false and mill.dirty == 2)
local order = {}
for _ = 1, 4 do
    M.cycleSpout(mill)
    order[#order + 1] = spec.spoutState
end
check("O / kloub: přeprava -> vedle -> za -> přeprava -> vedle", table.concat(order, ",") == "2,3,1,2", table.concat(order, ","))
check("příkazy roury 5, 6, 4, 5", table.concat(sent, ",", 3) == "5,6,4,5", table.concat(sent, ","))
local before = mill.dirty
M.command(mill, M.CMD_SPOUT_TRANSPORT + 1, nil, true)
check("stejný stav roury nic nemění", mill.dirty == before and spec.spoutState == 2)
check("CMD_BITS stačí na všechny příkazy", M.CMD_SPOUT_TRANSPORT + 2 < 2 ^ M.CMD_BITS)

-- ------------------------------------------------------------------ násypka: opěry a big bag
local hs = { limeUnit = 2, legs = { { node = 21, x = 0.52, y = 0.1, z = 0.71, dir = 1, foot = 22, fx = 0, fy = -0.05, fz = 0 },
    { node = 23, x = -0.52, y = 0.1, z = 0.71, dir = -1, foot = 24, fx = 0, fy = -0.05, fz = 0 } },
    legTravel = 0.32, legDrop = 0.05, legsOut = false, legsPos = 0, dirtyFlag = 1, pour = { pourNeck = 30 } }
local hopper = { isServer = true, rootNode = 31 }
WORLD = { [30] = { 0, 1.42, 0.22 }, [31] = { 0, 0, 0 } }
getWorldTranslation = function(node) local p = WORLD[node]; return p[1], p[2], p[3] end
g_currentMission = { vehicleSystem = { vehicles = { hopper } } }
hopper[H.SPEC_NAME] = hs
function hopper:raiseDirtyFlags() end
function hopper:raiseActive() end
local function super(self, unit, tool) return true end
check("zasunuté opěry: vak nesype", H.getFillUnitSupportsToolType(hopper, super, 2, ToolType.DISCHARGEABLE) == false)
check("zasunuté opěry: pytel / hadice ano", H.getFillUnitSupportsToolType(hopper, super, 2, ToolType.UNDEFINED) == true)
check("zasunuté opěry: nafta (jiný fill unit) ano", H.getFillUnitSupportsToolType(hopper, super, 1, ToolType.DISCHARGEABLE) == true)
H.command(hopper, H.CMD_LEGS_OUT, true)
check("příkaz vysunout", hs.legsOut == true)
hs.legsPos = 0.5
check("opěry v pohybu: vak ještě nesype", H.getFillUnitSupportsToolType(hopper, super, 2, ToolType.DISCHARGEABLE) == false)
H.applyLegs(hs)
check("v půli: rameno vysunuté o 0,23 m, patka ještě nahoře", near(POS[21][1], 0.52 + 0.32 * 0.5 / 0.7, 1e-4) and near(POS[22][2], -0.05),
    string.format("%.3f / %.3f", POS[21][1], POS[22][2]))
hs.legsPos = 1
H.applyLegs(hs)
check("vysunuto: rameno +0,32 m ven, patka o 0,05 m níž", near(POS[21][1], 0.84) and near(POS[23][1], -0.84) and near(POS[22][2], -0.10))
check("vysunuté opěry: vak sype", H.getFillUnitSupportsToolType(hopper, super, 2, ToolType.DISCHARGEABLE) == true)
H.command(hopper, H.CMD_LEGS_IN, true)
check("příkaz zasunout: vak hned přestane", hs.legsOut == false and H.getFillUnitSupportsToolType(hopper, super, 2, ToolType.DISCHARGEABLE) == false)

-- vak na stolici: opěry nejdou vysunout ani zasunout
local bag = { rootNode = 40, spec_dischargeable = {} }
WORLD[40] = { 0.1, 1.40, 0.2 }
table.insert(g_currentMission.vehicleSystem.vehicles, bag)
check("vak na stolici se najde", H.findStoolBag(hopper) == bag)
H.command(hopper, H.CMD_LEGS_OUT, true)
check("s vakem na stolici opěry nejdou vysunout", hs.legsOut == false)
hs.legsOut, hs.legsPos = true, 1
H.command(hopper, H.CMD_LEGS_IN, true)
check("s vakem na stolici opěry nejdou zasunout", hs.legsOut == true)
WORLD[40] = { 0.0, 0.52, 0.22 }
H.command(hopper, H.CMD_LEGS_IN, true)
check("vak propadlý do nástavce opěry taky blokuje", hs.legsOut == true)
WORLD[40] = { 0.44, 1.23, 0.22 }
check("vyprazdňující se vak svezlý o 0,44 m stranou se pořád počítá (měřeno ve hře)", H.findStoolBag(hopper) == bag)
WORLD[40] = { 0.3, 0.0, 0.2 }
check("vak na zemi těsně u násypky se nepočítá", H.findStoolBag(hopper) == nil)
WORLD[40] = { 1.7, 0.0, 0.2 }
check("vak shozený na zem se nepočítá", H.findStoolBag(hopper) == nil)
H.command(hopper, H.CMD_LEGS_IN, true)
check("bez vaku opěry jdou zasunout", hs.legsOut == false)

-- poloha vaku vůči stolici (uzel funnel 2 cm nad rámem, y 1,42)
local function where(bx, by, bz) return (H.getStoolPlacement(0, 1.42, 0.22, bx, by, bz)) end
check("vak dnem na rámu uprostřed: ok", where(0.05, 1.40, 0.20) == "ok")
check("vak propadl do nástavce (dno 0,5 nad zemí): propadl", where(0.0, 0.52, 0.22) == "propadl")
check("vak 0,5 m vedle: vedle", where(0.5, 1.40, 0.22) == "vedle")
check("vak nese nakladač 0,5 m nad rámem: nad", where(0.0, 1.90, 0.22) == "nad")

return { out = out, fails = fails }
''')

# exportovaná násypka: podlaha stolice přes celý otvor (jinak částečně plný vak propadne mezi rámy, kolize vaku jsou jen kolem středu)
import xml.etree.ElementTree as ET
i3d = scripts.parent / "objects" / "hopper" / "limeHopper.i3d"
floor = [s for s in ET.parse(i3d).getroot().iter("Shape") if s.get("name") == "stoolFloor"]
ok = len(floor) == 1 and floor[0].get("compoundChild") == "true" and floor[0].get("collisionFilterGroup") == "0x10000"
result["out"][len(result["out"]) + 1] = ("ok    " if ok else "FAIL  ") + "limeHopper.i3d: kolize stoolFloor (compoundChild, skupina 0x10000)"
result["fails"] = result["fails"] + (0 if ok else 1)

# plnicí hlava z boku vaku (exportovaný mlýnek): v polohách 90° a 180° je čelo hlavy (uzel millFillHead) i celá roura mimo půdorys vaku
# (vak 0,99 x 0,84 m hloubkou podél ramene, střed = hlava + směr ramene x neckOffset), takže plný vak jde zvednout o 0,5 m a odvézt od vozíku
# (ve směru ramene se od roury jen vzdaluje); hlava pod horní hranou látky vaku (1,10 m), vak mimo kolo a záď.
import math
mill_dir = scripts.parent / "vehicles" / "sdtLimeMill"
mill = ET.parse(mill_dir / "sdtLimeMill.i3d").getroot()
nodes = {e.get("name"): [float(v) for v in e.get("translation", "0 0 0").split()] for e in mill.iter() if e.get("name")}
neck = float(ET.parse(mill_dir / "sdtLimeMill.xml").getroot().find("sprayDroneMill/bagOutput").get("neckOffset"))
px, py, pz = nodes["millSpoutPivot"]
hx, hy, hz = nodes["millFillHead"]          # vůči kloubu, přeprava: rameno míří +z
HEAD_R, BAG_HX, BAG_HZ, MARGIN = 0.105, 0.495, 0.42, 0.05
lines = []
def add(ok, text):
    lines.append(("ok    " if ok else "FAIL  ") + text)
    return 0 if ok else 1
fails2 = 0
for ang in (-90.0, -180.0):
    a = math.radians(ang)
    dx, dz = math.sin(a), math.cos(a)
    reach = math.hypot(hx, hz)
    head = (px + dx * reach, py + hy, pz + dz * reach)
    gap = neck - BAG_HZ - HEAD_R
    fails2 += add(gap >= MARGIN - HEAD_R and neck - BAG_HZ >= MARGIN,
                  f"{ang:.0f}°: bok vaku {neck - BAG_HZ:.2f} m za čelem hlavy, nic z roury nad půdorysem vaku")
    fails2 += add(head[1] + HEAD_R <= 1.18 and head[1] - HEAD_R >= 0.8, f"{ang:.0f}°: hlava v boku vaku (osa {head[1]:.2f} m, látka do 1,10-1,18 m)")
    cx, cz = head[0] + dx * neck, head[2] + dz * neck
    near_x = abs(dz) * BAG_HX + abs(dx) * BAG_HZ
    near_z = abs(dx) * BAG_HX + abs(dz) * BAG_HZ
    wheel_clear = cx + near_x < -1.22 - 0.1 or cx - near_x > -0.94 or cz + near_z < -1.77 - 0.1 or cz - near_z > -0.99
    rear_clear = ang != -180.0 or cz + near_z < -2.53 - 0.2
    fails2 += add(wheel_clear and rear_clear, f"{ang:.0f}°: vak ({cx:+.2f}; {cz:+.2f}) mimo pravé kolo a záď")
for line in lines:
    result["out"][len(result["out"]) + 1] = line
result["fails"] = result["fails"] + fails2

for line in result["out"].values():
    print(line)
fails = result["fails"]
print(f"\n{'OK' if fails == 0 else 'CHYB: ' + str(fails)}")
sys.exit(1 if fails else 0)
