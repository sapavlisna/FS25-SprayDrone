# Ruční zkouška čisté geometrie úvratí (SprayDroneRoute.lua) přes LuaJIT/lupa: python tools/test_headlands.py
# Offset polygonu, řádky uvnitř úvratí, pořadí legů, paměť (mark/encode/decode) a planBatch přes navazující legy.
import sys
from pathlib import Path
from lupa import luajit21

lua = luajit21.LuaRuntime()
route = Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "scripts" / "SprayDroneRoute.lua"

lua.execute('''
MathUtil = {
    vector2Length = function(x, z) return math.sqrt(x * x + z * z) end,
    getYRotationFromDirection = function(dx, dz) return math.atan2(dx, dz) end,
    getAngleDifference = function(a, b) return (a - b + math.pi) % (2 * math.pi) - math.pi end,
}
math.clamp = function(v, lo, hi) return math.max(lo, math.min(hi, v)) end
CollisionFlag = { STATIC_OBJECT = 1, TREE = 2, BUILDING = 4 }
''')
lua.execute(route.read_text(encoding="utf-8"))
lua.execute('SprayDroneRoute.getIsWorkable = function() return true end')

result = lua.execute(r'''
local R = SprayDroneRoute
local out, fails = {}, 0
local function check(name, ok, info)
    if not ok then fails = fails + 1 end
    out[#out + 1] = string.format("%s  %s%s", ok and "ok  " or "FAIL", name, info and ("  " .. info) or "")
end
local function near(a, b, eps) return math.abs(a - b) <= (eps or 1e-6) end

local function makeField(id, pts)
    return { getId = function() return id end, sdtPolygon = pts }
end
local function dist(poly, x, z) return (R.nearestBoundaryPoint(poly, x, z)) end

-- 1. offset obdélníku 100 x 60 o 4,5, obě orientace
local rect = { { x = 0, z = 0 }, { x = 100, z = 0 }, { x = 100, z = 60 }, { x = 0, z = 60 } }
local rectCW = { rect[4], rect[3], rect[2], rect[1] }
for name, poly in pairs({ ccw = rect, cw = rectCW }) do
    local o = R.offsetPolygon(poly, 4.5)
    local ok = #o == 4
    for _, p in ipairs(o) do
        ok = ok and (near(p.x, 4.5) or near(p.x, 95.5)) and (near(p.z, 4.5) or near(p.z, 55.5))
    end
    check("offset obdélníku " .. name, ok, "vrcholů " .. #o)
end

-- 2. tvar L: vrchol (60,30) je vklesly (reflex); ostrý reflex (tenký klín) dostane oblouk, všechny body d od hranice
local L = { { x = 0, z = 0 }, { x = 100, z = 0 }, { x = 100, z = 30 }, { x = 60, z = 30 }, { x = 60, z = 80 }, { x = 0, z = 80 } }
local oL = R.offsetPolygon(L, 4.5)
local inside, minD = true, math.huge
for _, p in ipairs(oL) do
    inside = inside and R.isPointInPolygon(L, p.x, p.z)
    minD = math.min(minD, dist(L, p.x, p.z))
end
check("offset tvaru L uvnitř pole", inside and minD > 4.5 - 1e-6, string.format("min vzdálenost %.3f", minD))
-- ostrý klín (dovnitř míří špice): vrchol (50,10) mezi (0,0)-(100,0) je reflex s úhlem ~ 20 stupňů
local wedge = { { x = 0, z = 0 }, { x = 45, z = 0 }, { x = 50, z = 40 }, { x = 55, z = 0 }, { x = 100, z = 0 }, { x = 100, z = 80 }, { x = 0, z = 80 } }
local ow = R.offsetPolygon(wedge, 4.5)
local spike, arc = false, false
for _, p in ipairs(ow) do
    local d = math.sqrt((p.x - 50) ^ 2 + (p.z - 40) ^ 2)
    spike = spike or (p.z > 40 and d > 4.5 * R.HEADLAND_MITRE_LIMIT + 0.01 and d < 50)
    arc = arc or near(d, 4.5, 1e-6)
end
check("mitr klínu je omezený, vrchol nahrazen obloukem", not spike and arc)

-- 3. buildLegs: obdélník 100 x 60, domov (-5, 30), range 500, záběr 9
local ww = 9
local field = makeField(7, rect)
local st = {}
local base = R.buildLegs(field, -5, 30, 500, ww, st, nil, 0, 1)
local h2 = R.buildLegs(makeField(7, rect), -5, 30, 500, ww, st, nil, 2, 1)
local function lenSum(legs) local s = 0 for _, l in ipairs(legs) do s = s + l.len end return s end
check("n=0 beze změny (řádky přes celé pole)", #base > 0)

local rowsOnly, loopLegs = 0, 0
local minRowDist = math.huge
for _, l in ipairs(h2) do
    local cx, cz = (l.x1 + l.x2) / 2, (l.z1 + l.z2) / 2
    local d = dist(rect, cx, cz)
    if d >= 2 * ww - 1 then
        rowsOnly = rowsOnly + 1
        minRowDist = math.min(minRowDist, d)
    else
        loopLegs = loopLegs + 1
    end
end
check("řádky uvnitř úvratí a úvratě jsou legy", rowsOnly > 0 and loopLegs > 0, string.format("řádků %d, úvratí %d, nejbližší řádek %.1f", rowsOnly, loopLegs, minRowDist))

-- pořadí: headlandFirst=1 => prvních 4 legů je smyčka 1 (d = 4,5), potom smyčka 2 (13,5), potom řádky
local first = R.buildLegs(field, -5, 30, 500, ww, st, nil, 2, 1)
local function legDist(l) return dist(rect, (l.x1 + l.x2) / 2, (l.z1 + l.z2) / 2) end
local ok = true
for i = 1, 4 do ok = ok and near(legDist(first[i]), 4.5, 0.3) end
for i = 5, 8 do ok = ok and near(legDist(first[i]), 13.5, 0.3) end
check("headlandFirst=1: úvrať 1, úvrať 2, řádky", ok and legDist(first[9]) > 17)
local last = R.buildLegs(field, -5, 30, 500, ww, st, nil, 2, 0)
ok = legDist(last[1]) > 17 and near(legDist(last[#last]), 4.5, 0.3) and near(legDist(last[#last - 4]), 13.5, 0.3)
check("headlandFirst=0: řádky, úvrať 2, úvrať 1", ok)

-- navazování legů smyčky (konec = začátek dalšího), start u domova
local cont = true
for i = 1, 3 do
    cont = cont and math.sqrt((first[i + 1].x1 - first[i].x2) ^ 2 + (first[i + 1].z1 - first[i].z2) ^ 2) < 0.5
end
check("hrany smyčky na sebe navazují", cont)
check("smyčka začíná u domova", math.sqrt((first[1].x1 + 5) ^ 2 + (first[1].z1 - 30) ^ 2) < 30,
    string.format("start %.1f %.1f", first[1].x1, first[1].z1))

-- 4. paměť: zápis chunků po úvrati 1 a po řádku, encode / decode, znovu buildLegs
local cov = {}
local total1 = 0
for _, l in ipairs({ first[1], first[2] }) do
    local n = math.max(math.floor(l.len / 2), 1)
    for k = 0, n - 1 do
        local t1, t2 = k / n, (k + 1) / n
        R.markCovered(cov, field, 1, ww, 2, l.x1 + (l.x2 - l.x1) * t1, l.z1 + (l.z2 - l.z1) * t1,
            l.x1 + (l.x2 - l.x1) * t2, l.z1 + (l.z2 - l.z1) * t2)
    end
end
local entry = R.getCoverage(cov, 7, 1, ww, 2)
check("markCovered: úvrať 1 zapsaná, úvrať 2 a řádky ne", entry ~= nil and entry.headlands[1] ~= nil and entry.headlands[2] == nil
    and next(entry.lines) == nil)
check("hl jiné zneplatní záznam", R.getCoverage(cov, 7, 1, ww, 3) == nil and R.getCoverage(cov, 7, 1, ww, 0) == nil)
local rowLeg = first[9]
R.markCovered(cov, field, 1, ww, 2, rowLeg.x1, rowLeg.z1, rowLeg.x2, rowLeg.z2)
entry = R.getCoverage(cov, 7, 1, ww, 2)
check("markCovered: řádek do lines", next(entry.lines) ~= nil)
local decoded = R.decodeCoverage(R.encodeCoverage(cov))
local dEntry = R.getCoverage(decoded, 7, 1, ww, 2)
check("encode/decode kolem dokola", dEntry ~= nil and #dEntry.headlands[1] == #entry.headlands[1]
    and near(dEntry.headlands[1][1][1], entry.headlands[1][1][1], 0.06))
local after = R.buildLegs(field, -5, 30, 500, ww, st, dEntry, 2, 1)
check("s pamětí legů ubude", #after < #first and lenSum(after) < lenSum(first) - 10,
    string.format("%d -> %d, %.0f -> %.0f m", #first, #after, lenSum(first), lenSum(after)))
-- coverField: vše obletěno
local all = { type = 1, ww = ww, hl = 2, lines = {}, headlands = { { { -1e9, 1e9 } }, { { -1e9, 1e9 } } } }
for k = 0, 10 do all.lines[k] = { { -1e7, 1e7 } } end
check("coverField: nic k postřiku", #R.buildLegs(field, -5, 30, 500, ww, st, all, 2, 1) == 0)

-- 5. planBatch přes navazující legy smyčky a přejezd na řádek
local p = { workWidth = ww, sprayHeight = 3, transitHeight = 12, cruiseSpeed = 10, sprayingSpeed = 7, climbSpeed = 3,
    ascentSpeed = 5, acceleration = 2.5, turnAcceleration = 2.5, yawSpeed = math.rad(90), litersPerMeter = 0.26,
    batteryReserve = 30, restHeight = 1.5, homeYaw = 0, droneMass = 40, fullMass = 92, massPerLiter = 1,
    hoverFactor = 1.15, climbFactor = 1.4, descentFactor = 0.8, batteryCapacity = 480, batterySwapBelow = 0.3 }
p.getTransit = function(x, z, outbound, dx, dz)
    local pts = outbound and { { x = -5, z = 30, h = 12, speed = 10, home = true }, { x = x, z = z, h = 12, speed = 10 } }
        or { { x = x, z = z, h = 12, speed = 10 }, { x = -5, z = 30, h = 12, speed = 10, home = true },
             { x = -5, z = 30, h = 1.5, speed = 3, home = true, land = true } }
    return { wps = pts, height = 12, length = 100, tooHigh = false, points = {}, heights = {}, obstacles = {} }
end
p.isTurnClear = function() return true end
local wps, ni, noff, sprayed, info = R.planBatch(first, 1, 0, -5, 30, 40, 480, p)
local sprayWps, junk, consecutive = 0, false, false
local prevSpray = false
for _, w in ipairs(wps or {}) do
    if w.spray then
        sprayWps = sprayWps + 1
        consecutive = consecutive or prevSpray
    end
    prevSpray = w.spray == true
    if w.x ~= w.x or w.z ~= w.z then junk = true end
end
check("planBatch po legu smyčky", wps ~= nil and sprayWps >= 3 and consecutive and not junk and sprayed > 30 and info.time > 0,
    string.format("spray wps %d, nastříkáno %.0f m, %.0f s", sprayWps, sprayed or 0, info and info.time or 0))
local drawLegs, batches, left = R.splitIntoBatches(first, -5, 30, 40, 480, p)
local drawn = 0
for _, l in ipairs(drawLegs) do drawn = drawn + math.sqrt((l.x2 - l.x1) ^ 2 + (l.z2 - l.z1) ^ 2) end
check("splitIntoBatches pokryje všechny legy", not left and near(drawn, lenSum(first), 1),
    string.format("dávek %d, %.0f z %.0f m", batches, drawn, lenSum(first)))
-- rowTurn: navazující leg = prázdný přejezd
check("rowTurn na místě je prázdný", #R.rowTurn(10, 10, 1, 0, 10, 10, 0, 1, p, nil) == 0)

out[#out + 1] = fails == 0 and "VŠE V POŘÁDKU" or (fails .. " SELHÁNÍ")
return table.concat(out, "\n")
''')
print(result)
sys.exit(1 if "SELHÁNÍ" in result else 0)
