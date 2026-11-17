# Zkouška výběru cíle tabletu bez hry (LuaJIT/lupa): python tools/test_tablet.py
# SprayDroneLink: kandidáti (vleky i kufry farmy s dronem ve spojení, cizí / bez dronu / mimo dosah ne), pořadí (mise, rozložené,
# vzdálenost), výchozí cíl (naposled použitý, jinak první), přepínání dokola, dosah kufru (jeho maxRange), popis cíle;
# přepínání mimo tablet (getStationTargets / isStationTargetConnected / getPlannerTargets: cíle z vleku, ze kterého se plánovač otevřel).
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

addModEventListener = function() end
entityExists = function() return true end
g_i18n = { getText = function(_, key)
    local t = { sdt_tablet_target = "%s – %.0f m, %s", sdt_tablet_stateMission = "letí", sdt_tablet_stateUnfolded = "rozloženo",
        sdt_tablet_stateFolded = "složeno" }
    return t[key] or key
end }
SprayDroneStation = { SPEC_NAME = "spec_sd", getHomePosition = function(v) return v.x, v.z end }
SprayDroneDrones = { getCount = function() return 1 end, getSpec = function(v) return v.spec_sd end }
dofile(SCRIPTS .. "/SprayDroneLink.lua")
local L = SprayDroneLink
L.getActiveRelays = function() return {} end
L.getVehicleDesign = function() return "BZUK" end

local function vehicle(name, x, z, opts)
    opts = opts or {}
    local v = { name = name, x = x, z = z, farmId = opts.farmId or 1, configFileName = name .. ".xml",
        spec_sd = { hasDrone = opts.hasDrone ~= false, maxRange = opts.maxRange or 750, missionActive = opts.mission == true,
            portable = opts.portable } }
    v.getIsUnfolded = function() return opts.unfolded == true end
    v.getName = function() return name end
    return v
end
local mini = vehicle("Mini", 100, 0, { unfolded = true })
local middle = vehicle("Middle", 50, 0, { unfolded = false })
local max = vehicle("Max", 400, 0, { unfolded = true, mission = true })
local scan = vehicle("scanCase", 1400, 0, { unfolded = true, portable = true, maxRange = 1500 })
local sampler = vehicle("samplerCase", 20, 0, { unfolded = false, portable = true, maxRange = 1500 })
local far = vehicle("MiddleFar", 2000, 0, { unfolded = true })
local noDrone = vehicle("MiniEmpty", 10, 0, { unfolded = true, hasDrone = false })
local foreign = vehicle("MaxForeign", 5, 0, { unfolded = true, farmId = 2 })
g_currentMission = { vehicleSystem = { vehicles = { mini, middle, max, scan, sampler, far, noDrone, foreign } },
    accessHandler = { canFarmAccess = function(_, farmId, v) return v.farmId == farmId end } }

local found = L.findTrailers(0, 0, 1)
local names = {}
for _, e in ipairs(found) do names[#names + 1] = e.vehicle.name end
local order = table.concat(names, ",")
check("pořadí: mise, rozložené od nejbližšího, složené od nejbližšího", order == "Max,Mini,scanCase,samplerCase,Middle", order)
check("kufr 1400 m (maxRange 1500) je ve spojení", L.isConnected(scan, 0, 0))
check("kufr 1600 m už ne", not L.isConnected(scan, -200, 0))
check("vlek 2000 m daleko, bez dronu a cizí nejsou cíle", not order:find("MiddleFar") and not order:find("MiniEmpty") and not order:find("Foreign"))

check("výchozí bez paměti = první (mise)", L.pickTarget(found, nil) == 1)
check("výchozí = naposled použitý kufr", found[L.pickTarget(found, sampler)].vehicle == sampler)
check("naposled použitý mimo spojení -> první", L.pickTarget(found, far) == 1)
check("bez cílů nil", L.pickTarget({}, mini) == nil and L.cycleTarget({}, mini, 1) == nil)

check("další po Max je Mini", found[L.cycleTarget(found, max, 1)].vehicle == mini)
check("další po posledním dokola na první", found[L.cycleTarget(found, middle, 1)].vehicle == max)
check("předchozí od prvního dokola na poslední", found[L.cycleTarget(found, max, -1)].vehicle == middle)
check("přepnutí z vozidla mimo seznam = výchozí", L.cycleTarget(found, far, 1) == 1)
local one = { found[1] }
check("jediný cíl se přepne sám na sebe", L.cycleTarget(one, max, 1) == 1 and L.cycleTarget(one, max, -1) == 1)

-- přepínání mimo tablet (Alt+7 ve vleku, displej): cíle z domova vleku, ze kterého se plánovač otevřel
SprayDronePlannerScreen = { MODE_TABLET = "tablet", MODE_VEHICLE = "vehicle", MODE_SCREEN = "screen" }
g_currentMission.getFarmId = function() return 1 end
local function namesOf(list)
    local t = {}
    for _, e in ipairs(list) do t[#t + 1] = e.vehicle.name end
    return table.concat(t, ",")
end
local fromEmpty = namesOf(L.getStationTargets(noDrone, 1))
check("vlek bez dronu: cíle ve spojení s ním, on sám na konci", fromEmpty == "Max,Mini,scanCase,samplerCase,Middle,MiniEmpty", fromEmpty)
local fromFar = L.getStationTargets(far, 1)
check("vzdálený vlek: jen on a kufr, jehož rádio (1500 m) ho pokryje", namesOf(fromFar) == "MiddleFar,scanCase", namesOf(fromFar))
check("cizí vlek mezi cíli vleku není", not namesOf(L.getStationTargets(mini, 1)):find("Foreign"))
check("PageDown z vleku na kufr a dokola zpět", fromFar[L.cycleTarget(fromFar, far, 1)].vehicle == scan
    and fromFar[L.cycleTarget(fromFar, scan, 1)].vehicle == far and fromFar[L.cycleTarget(fromFar, far, -1)].vehicle == scan)
check("spojení cíle s originem: sám se sebou vždy", L.isStationTargetConnected(noDrone, noDrone))
check("spojení cíle s originem: kufr v dosahu ano, Max 1600 m ne", L.isStationTargetConnected(far, scan) and not L.isStationTargetConnected(far, max))
check("cíl bez dronu jiný než origin ne", not L.isStationTargetConnected(mini, noDrone))
check("getPlannerTargets ve vleku = z originu", namesOf(L.getPlannerTargets("vehicle", far)) == "MiddleFar,scanCase")
check("getPlannerTargets u displeje = z originu", namesOf(L.getPlannerTargets("screen", noDrone)) == fromEmpty)
g_localPlayer = { getPosition = function() return 0, 0, 0 end }
check("getPlannerTargets z tabletu = z polohy hráče", namesOf(L.getPlannerTargets("tablet", far)) == order, namesOf(L.getPlannerTargets("tablet", far)))
g_localPlayer = nil

local label = L.getTargetLabel(found[1])
check("popis: jméno, vzdálenost, stav", label == "Max – 400 m, letí", label)
check("popis složeného kufru", L.getTargetLabel(found[4]) == "samplerCase – 20 m, složeno", L.getTargetLabel(found[4]))

return { out = out, fails = fails }
''')

for line in result["out"].values():
    print(line)
fails = result["fails"]
print(f"\n{'OK' if fails == 0 else 'CHYB: ' + str(fails)}")
sys.exit(1 if fails else 0)
