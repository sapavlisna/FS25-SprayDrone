# Kontrola volného prostoru před vzletem bez hry (LuaJIT/lupa): python tools/test_launch.py
# SprayDroneLaunch.getClearance s falešnými raycastAll / overlapBox: volno, střecha, strom (paprsek i jen box), vlastní souprava,
# trigger, priorita důvodů, 17 paprsků, výška kontroly (min 8 m), zásahy pro ladění.
from pathlib import Path
from lupa import luajit21

lua = luajit21.LuaRuntime(unpack_returned_tuples=True)
scripts = Path(__file__).resolve().parent.parent / "mod" / "FS25_SprayDroneTrailer" / "scripts"

lua.execute('''
CollisionFlag = { STATIC_OBJECT = 1, TREE = 2, BUILDING = 4, PRECIPITATION_BLOCKING = 8, VEHICLE = 16, DYNAMIC_OBJECT = 32 }
ClassIds = { SHAPE = 1 }
GROUPS, NODE_OBJECT, TRIGGERS = {}, {}, {}
function CollisionFlag.getHasGroupFlagSet(node, flag) return bit.band(GROUPS[node] or 0, flag) ~= 0 end
function entityExists(node) return GROUPS[node] ~= nil end
function getHasTrigger(node) return TRIGGERS[node] == true end
function getHasClassId() return true end
function getName(node) return "n" .. node end
g_currentMission = { getNodeObject = function(_, node) return NODE_OBJECT[node] end }

-- RAY_HITS: seznam {node, ray (nil = každý)}; BOX_HITS: uzly v boxu
RAY_HITS, BOX_HITS, RAYS, BOXES = {}, {}, {}, {}
function raycastAll(x, y, z, dx, dy, dz, len, cb, target, mask)
    table.insert(RAYS, { x = x, y = y, z = z, dy = dy, len = len, mask = mask })
    for _, h in ipairs(RAY_HITS) do
        if h.ray == nil or h.ray == #RAYS then
            if not target[cb](target, h.node, x, y + 2, z, 2) then return end
        end
    end
end
function overlapBox(x, y, z, rx, ry, rz, ex, ey, ez, cb, target, mask)
    table.insert(BOXES, { y = y, ex = ex, ey = ey, ez = ez, mask = mask })
    for _, node in ipairs(BOX_HITS) do
        if not target[cb](target, node) then return end
    end
end
''')
lua.execute((scripts / "SprayDroneLaunch.lua").read_text(encoding="utf-8"))

result = lua.execute(r'''
local out, fails = {}, 0
local function check(name, ok, info)
    if not ok then fails = fails + 1 end
    out[#out + 1] = string.format("%s  %s%s", ok and "ok  " or "FAIL", name, info and ("  " .. info) or "")
end
local L = SprayDroneLaunch
local root = { name = "souprava" }
root.getRootVehicle = function(self) return root end
local tool = { getRootVehicle = function() return root end }
local function reset(rayHits, boxHits)
    RAY_HITS, BOX_HITS, RAYS, BOXES = rayHits or {}, boxHits or {}, {}, {}
end
GROUPS = { [1] = CollisionFlag.BUILDING, [2] = CollisionFlag.TREE, [3] = CollisionFlag.VEHICLE, [4] = CollisionFlag.STATIC_OBJECT,
    [5] = CollisionFlag.PRECIPITATION_BLOCKING, [6] = CollisionFlag.VEHICLE + CollisionFlag.PRECIPITATION_BLOCKING, [7] = CollisionFlag.STATIC_OBJECT }
NODE_OBJECT = { [3] = tool, [6] = { getRootVehicle = function(self) return self end } }
TRIGGERS = { [7] = true }

reset()
local ok, reason = L.getClearance(10, 100, 20, 1.6, 30, root)
check("volno", ok and reason == nil)
check("17 paprsků nahoru", #RAYS == 17 and RAYS[1].dy == 1 and RAYS[1].len == 30, #RAYS)
check("start 0,3 m nad dronem", math.abs(RAYS[1].y - 100.3) < 1e-6)
local r = 1.6 + 0.3
check("vnější kruh r + 0,3", math.abs(math.sqrt((RAYS[2].x - 10) ^ 2 + (RAYS[2].z - 20) ^ 2) - r) < 1e-6)
check("vnitřní kruh r / 2", math.abs(math.sqrt((RAYS[10].x - 10) ^ 2 + (RAYS[10].z - 20) ^ 2) - r / 2) < 1e-6)
local m = RAYS[1].mask
check("maska paprsků", m == 1 + 2 + 4 + 8 + 16 + 32, m)
check("box nad plošinou", #BOXES == 1 and math.abs(BOXES[1].ex - r) < 1e-6 and math.abs(BOXES[1].ey - 15) < 1e-6
    and math.abs(BOXES[1].y - (100.3 + 15)) < 1e-6 and BOXES[1].mask == 1 + 2 + 4)

reset()
L.getClearance(0, 0, 0, 1, 3, root)
check("výška aspoň 8 m", RAYS[1].len == 8, RAYS[1].len)
reset()
L.getClearance(0, 0, 0, 1, nil, root)
check("bez výšky CHECK_HEIGHT", RAYS[1].len == 12, RAYS[1].len)

reset({ { node = 1, ray = 5 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("budova = střecha", not ok and reason == "roof", reason)
reset({ { node = 5 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("PRECIPITATION_BLOCKING = střecha", not ok and reason == "roof", reason)
reset({ { node = 6 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("kabina cizího vozidla = překážka", not ok and reason == "obstacle", reason)
reset({ { node = 2, ray = 1 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("strom", not ok and reason == "tree", reason)
reset({}, { 2 })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("větev jen v boxu", not ok and reason == "tree", reason)
reset({ { node = 4 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("statický objekt = překážka", not ok and reason == "obstacle", reason)
reset({ { node = 3 } }, { 3 })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("vlastní souprava se přeskočí", ok, reason)
reset({ { node = 3 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, nil)
check("bez soupravy se vozidlo počítá", not ok and reason == "obstacle", reason)
reset({ { node = 7 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("trigger se přeskočí", ok, reason)
reset({ { node = 3 }, { node = 4 }, { node = 2 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("za vlastní soupravou dál (raycastAll)", reason == "tree", reason)
reset({ { node = 4, ray = 2 }, { node = 1, ray = 9 }, { node = 2, ray = 3 } })
ok, reason = L.getClearance(0, 0, 0, 1.6, 12, root)
check("priorita: střecha nad stromem", reason == "roof", reason)

local hits = {}
reset({ { node = 1, ray = 4 } }, { 2 })
L.getClearance(0, 0, 0, 1.6, 12, root, hits)
check("zásahy pro ladění", #hits == 2 and hits[1].ray == 4 and hits[1].reason == "roof" and hits[1].distance == 2
    and hits[2].ray == 0 and hits[2].reason == "tree", #hits)
reset({ { node = 1 } })
L.getClearance(0, 0, 0, 1.6, 12, root)
reset()
ok = L.getClearance(0, 0, 0, 1.6, 12, root)
check("sonda se po volání vynuluje", ok)

return table.concat(out, "\n"), fails
''')
text, fails = result
print(text)
print(f"\n{'SELHALO ' + str(fails) if fails else 'vše v pořádku'}")
raise SystemExit(1 if fails else 0)
