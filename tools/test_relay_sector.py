# Směrová relé tyč bez hry (LuaJIT/lupa): python tools/test_relay_sector.py
# SprayDroneLink: oblast tyče (getRelayShape) – všesměrová kruh, směrová jen výseč 99° s dosahem 1,75× poloměru (525 / 700 m) a mimo
# ni nic; hranice úhlu, přechod ±180°, obrys (getCoverageLines bez kruhu r = 0); ve „hře“ se stuby: soubory tyčí (isRelayPole), oblast
# z natočení tyče (getRelayEntry), getSignalCircles / isConnected / getNeededRelays / isRelayNeeded / getRangeBonus a pojistka složení
# getRelayBlockReason se směrovou tyčí; SprayDroneRelaySlots.getPoleKind (držák bere obě tyče).
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
local function near(a, b, eps) return math.abs(a - b) <= (eps or 1e-6) end
local rad = math.rad

addModEventListener = function() end
entityExists = function() return true end
getWorldTranslation = function(node) return node.x, 0, node.z end
-- otočení kolem Y o ry: místní +Z = (sin ry, cos ry)
localDirectionToWorld = function(node, x, y, z)
    if y == 1 then return 0, node.up or 1, 0 end
    return math.sin(node.ry or 0), 0, math.cos(node.ry or 0)
end
SprayDroneStation = { SPEC_NAME = "spec_sd", STATE_FLYING = 1, STATE_RETURNING = 2,
    getHomePosition = function(v) return v.rootNode.x, v.rootNode.z end }
SprayDroneDrones = { getRoot = function(v) return v.spec_sd end, getCount = function() return 1 end, getSpec = function(v) return v.spec_sd end,
    runAs = function(v, k, fn, ...) return fn(v, ...) end }
SprayDroneRelay = { SPEC_NAME = "spec_relay", isOperating = function(v)
    local s = v.spec_relay
    return s.unfolded and s.powered and s.progress >= 1
end }
dofile(SCRIPTS .. "/SprayDroneLink.lua")
local L = SprayDroneLink

---------------------------------------------------------------------------------------------------
-- čisté funkce
local SECTOR = { angle = rad(99), factor = 1.75 }
local function pt(dist, deg) return dist * math.cos(rad(deg)), dist * math.sin(rad(deg)) end
local function inside(shape, dist, deg, margin)
    local x, z = pt(dist, deg)
    return L.isInShape(shape, x, z, margin)
end

local omni = L.getRelayShape(0, 0, 300)
check("všesměrová: kruh 300, bez výseče", omni.r == 300 and #omni.sectors == 0 and inside(omni, 299, 123) and not inside(omni, 301, 0))
local dir = L.getRelayShape(0, 0, 300, SECTOR, 0)
check("směrová standard: bez kruhu, výseč 525", dir.r == 0 and #dir.sectors == 1 and near(dir.sectors[1].r, 525) and dir.radius == 300)
check("směrová: 520 m v ose ano, 530 ne", inside(dir, 520, 0) and not inside(dir, 530, 0))
check("směrová: hranice 49,5° ano, 49,6° ne", inside(dir, 400, 49.5) and inside(dir, 400, -49.5) and not inside(dir, 400, 49.6))
check("směrová: za tyčí a do stran nic (ani 10 m)", not inside(dir, 10, 180) and not inside(dir, 10, 90) and not inside(dir, 100, -90))
check("směrová: těsně před tyčí ano", inside(dir, 5, 0))
check("směrová: dosah v bodě 525 ve výseči, 0 mimo", near(L.getShapeRange(dir, pt(100, 10)), 525) and L.getShapeRange(dir, pt(100, 120)) == 0)
check("směrová: nejdál 525", near(L.getShapeMaxRange(dir), 525))
local strong = L.getRelayShape(0, 0, 400, SECTOR, 0)
check("směrová silná: výseč 700", near(strong.sectors[1].r, 700) and inside(strong, 690, 0) and not inside(strong, 710, 0))
local wrap = L.getRelayShape(0, 0, 300, SECTOR, rad(179))
check("přechod ±180°: osa 179°, bod na -179°", inside(wrap, 400, -179) and inside(wrap, 400, 135) and not inside(wrap, 400, 120))
local wrap2 = L.getRelayShape(0, 0, 300, SECTOR, rad(-540))
check("směr mimo (-pi, pi> se srovná", near(wrap2.sectors[1].dir, math.pi) and inside(wrap2, 400, 180))
check("stará tyč {x, z, radius} v isInShape", L.isInShape({ x = 0, z = 0, radius = 300 }, 299, 0) and not L.isInShape({ x = 0, z = 0, radius = 300 }, 301, 0))
check("isInCircles s výsečí bez kruhu", L.isInCircles({ dir }, 400, 0) and not L.isInCircles({ dir }, -50, 0))

-- obrys
local function length(lines)
    local s = 0
    for _, l in ipairs(lines) do s = s + math.sqrt((l.x2 - l.x1) ^ 2 + (l.z2 - l.z1) ^ 2) end
    return s
end
local alone = L.getCoverageLines({ { x = dir.x, z = dir.z, r = dir.r, sectors = dir.sectors } }, 192)
local expect = rad(99) * 525 + 2 * 525
check("obrys směrové: jen oblouk a dva boky od tyče", near(length(alone), expect, 10), string.format("%.0f / %.0f", length(alone), expect))
local radio = { x = -400, z = 0, r = 500, sectors = {} }
local both = L.getCoverageLines({ radio, { x = 0, z = 0, r = 0, sectors = dir.sectors } }, 192)
local inRadio, onCircle = 0, 0
for _, l in ipairs(both) do
    local mx, mz = (l.x1 + l.x2) / 2, (l.z1 + l.z2) / 2
    if l.sector and math.sqrt((mx + 400) ^ 2 + mz ^ 2) < 499 then inRadio = inRadio + 1 end
    if l.circle == 1 then onCircle = onCircle + 1 end
end
check("obrys: boky výseče uvnitř rádia se nekreslí, kruh rádia ano", inRadio == 0 and onCircle > 0)

---------------------------------------------------------------------------------------------------
-- stuby vozidel
local function station(x, z, maxRange)
    return { rootNode = { x = x, z = z }, configFileName = "x/vehicles/max.xml",
        spec_sd = { maxRange = maxRange, hasDrone = true, state = 0 }, getOwnerFarmId = function() return 1 end }
end
-- deg = azimut čela (0 = sever = -Z, 90 = východ = +X)
local function pole(file, x, z, deg, radius, sector, state)
    local d = rad((deg or 0) - 90)
    local ry = math.atan2(math.cos(d), math.sin(d))
    return { rootNode = { x = x, z = z, ry = ry }, configFileName = "data/mods/FS25_SprayDroneTrailer/objects/relay/" .. file,
        spec_relay = state or { unfolded = true, powered = true, progress = 1, radius = radius or 300, sector = sector } }
end
local trailer = station(0, 0, 750)
local dirEast = pole("relayPoleDirectional.xml", 700, 0, 90, 300, SECTOR)       -- v rádiu, čelem na východ
local dirNorth = pole("relayPoleDirectional.xml", 0, -700, 90, 400, SECTOR)     -- silná, čelem na východ
local omniSouth = pole("relayPole.xml", 0, 700)
local dirFar = pole("relayPoleDirectional.xml", 1000, 0, 90, 300, SECTOR)        -- mimo rádio vleku
local dirOff = pole("relayPoleDirectional.xml", -700, 0, 270, 300, SECTOR, { unfolded = true, powered = false, progress = 1, radius = 300, sector = SECTOR })
local other = { rootNode = { x = 5, z = 5 }, configFileName = "x/objects/antenna/whatever.xml", spec_relay = { unfolded = true, powered = true, progress = 1 } }
g_currentMission = { vehicleSystem = { vehicles = { trailer, dirEast, dirNorth, omniSouth, dirFar, dirOff, other } } }

check("isRelayPole: obě tyče, cizí soubor ne", L.isRelayPole(dirEast) and L.isRelayPole(omniSouth) and not L.isRelayPole(other) and not L.isRelayPole(trailer))
local e = L.getRelayEntry(dirEast)
check("getRelayEntry: směr čela z natočení (východ = 0 rad), výseč 525", near(e.sectors[1].dir, 0, 1e-9) and near(e.sectors[1].r, 525) and e.r == 0 and e.vehicle == dirEast)
check("azimut čela 90°", near(L.getAzimuth(L.getRelayDirection(dirEast)), 90, 1e-6))
local active = L.getActiveRelays()
check("aktivní: 4 tyče (vypnutá a cizí ne)", #active == 4, #active)
check("getRelays: všech 5 tyčí, vypnutá neaktivní", #L.getRelays() == 5)

local circles = L.getSignalCircles(trailer)
check("kruhy signálu: rádio + 3 spojené tyče (vzdálená ne)", #circles == 4, #circles)
check("isConnected: 1200 m na východ přes výseč ano", L.isConnected(trailer, 1200, 0))
check("isConnected: 1300 m na východ ne (za výsečí)", not L.isConnected(trailer, 1300, 0))
check("isConnected: za směrovou tyčí (na sever od ní) ne", not L.isConnected(trailer, 700, -400))
check("isConnected: silná na severu míří na východ: (650, -700) ano, (0, -1000) ne", L.isConnected(trailer, 650, -700) and not L.isConnected(trailer, 0, -1000))
check("isConnected: všesměrová na jihu 900 m ano", L.isConnected(trailer, 0, 900))
check("isConnected: vzdálená tyč (mimo rádio) nepomáhá", not L.isConnected(trailer, 1400, 0))
check("isInCircles s oblastmi tyčí", L.isInCircles(circles, 1200, 0) and not L.isInCircles(circles, 1300, 0))

local radioShape = L.getRadio(trailer)
local connected = L.getConnectedRelays(trailer)
local needed = L.getNeededRelays({ { x = 500, z = 0 }, { x = 1100, z = 0 }, { x = 700, z = -400 } }, 0, 0, radioShape, connected)
check("getNeededRelays: bod ve výseči zaváže směrovou, bod v rádiu nic", #needed == 1 and needed[1].vehicle == dirEast)
local neededNone = L.getNeededRelays({ { x = 760, z = -300 } }, 0, 0, radioShape, connected)
check("getNeededRelays: bod mimo výseč tyč nezaváže", #neededNone == 0)
check("getNeededRelays se starým {x, z, radius}", #L.getNeededRelays({ { x = 900, z = 0 } }, 0, 0, 750, { { x = 700, z = 0, radius = 300 } }) == 1)

check("isRelayNeeded: dron ve výseči bez jiného signálu", L.isRelayNeeded(e, { { x = 1100, z = 0, others = { radioShape } } }))
check("isRelayNeeded: dron za tyčí (mimo výseč) ne", not L.isRelayNeeded(e, { { x = 900, z = -300, others = { radioShape } } }))
check("isRelayNeeded: dávka na ní závisí", L.isRelayNeeded(e, { { relays = { dirEast } } }))

-- strop dosahu z baterie: vzdálenost tyče, u směrové dál než rádio i rozdíl (silná na severu: 700 + 700 - 750 = 650 < 700)
check("getRangeBonus: 700 (tyče 700 m, výseč nepřesahuje rádio)", near(L.getRangeBonus(trailer, radioShape), 700))
local case = station(0, 0, 400)
g_currentMission.vehicleSystem.vehicles = { case, pole("relayPoleDirectional.xml", 350, 0, 90, 400, SECTOR) }
check("getRangeBonus u kufru 400 m se silnou směrovou 350 m: 350 + 700 - 400 = 650", near(L.getRangeBonus(case, L.getRadio(case)), 650))
check("kufr: 1040 m na východ ve spojení, 1060 ne", L.isConnected(case, 1040, 0) and not L.isConnected(case, 1060, 0))

-- pojistka složení / vypnutí směrové tyče (getRelayBlockReason, i se seznamem tyčí dávky)
g_currentMission.vehicleSystem.vehicles = { trailer, dirEast, omniSouth }
local function flying(x, z, relays)
    trailer.spec_sd.state = SprayDroneStation.STATE_FLYING
    trailer.spec_sd.node = x ~= nil and { x = x, z = z } or nil
    trailer.spec_sd.isLinked = x == nil
    trailer.spec_sd.batchRelays = relays
end
flying(1100, 0)
check("pojistka: dron 1100 m ve výseči -> tyč nejde složit", L.getRelayBlockReason(dirEast, "fold") == "sdt_relay_blockedDrone")
flying(700, -300)
check("pojistka: dron mimo výseč (v rádiu) -> jde", L.getRelayBlockReason(dirEast, "fold") == nil)
flying(nil, nil, { dirEast })
check("pojistka: dávka závisí na tyči -> nejde vypnout", L.getRelayBlockReason(dirEast, "off") == "sdt_relay_blockedDrone")
trailer.spec_sd.state = 0
check("pojistka: dron nestartoval -> jde", L.getRelayBlockReason(dirEast, "fold") == nil)
check("pojistka: cizí předmět nic neblokuje", L.getRelayBlockReason(other, "fold") == nil)

-- výdrž před dávkou: platí pro obě tyče (remaining)
check("getShortRelay: směrová s malou baterií", L.getShortRelay({ { remaining = 100 }, { remaining = 5000 } }, 600).remaining == 100)

---------------------------------------------------------------------------------------------------
-- držák tyčí: druh podle souboru
g_currentModDirectory = ""
Class = function() return {} end
local ok, err = pcall(dofile, SCRIPTS .. "/SprayDroneRelaySlots.lua")
if ok then
    local S = SprayDroneRelaySlots
    check("držák: relayPole.xml = 1, relayPoleDirectional.xml = 2, jiné nil",
        S.getPoleKind("data/mods/FS25_SprayDroneTrailer/objects/relay/relayPole.xml") == 1
        and S.getPoleKind("C:/x/objects/relay/RELAYPOLEDIRECTIONAL.xml") == 2
        and S.getPoleKind("x/objects/relay/myRelayPole.xml") == nil and S.getPoleKind("x/antennaOmni.xml") == nil and S.getPoleKind(nil) == nil)
    check("držák: nový slot je všesměrová", S.newSlot().kind == 1)
else
    check("SprayDroneRelaySlots.lua se načte", false, err)
end

return table.concat(out, "\n"), fails
''')
text, fails = result
print(text)
print(f"\n{'SELHALO ' + str(fails) if fails else 'vše v pořádku'}")
raise SystemExit(1 if fails else 0)
