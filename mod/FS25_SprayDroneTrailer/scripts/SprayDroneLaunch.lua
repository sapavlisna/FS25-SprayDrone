-- Volný prostor nad plošinou před vzletem: svislé paprsky nahoru (střed, kruh poloměru dronu + RING_MARGIN a kruh v polovině)
-- a overlapBox nad plošinou na větve mezi paprsky. Vlastní souprava a triggery se přeskakují. Klient se ptá při startu letu
-- (SprayDroneStation.startFlight), server před každou dávkou (startNextBatch čeká a zkouší znovu).

SprayDroneLaunch = {}

SprayDroneLaunch.RAY_MASK = (CollisionFlag.STATIC_OBJECT or 0) + (CollisionFlag.TREE or 0) + (CollisionFlag.BUILDING or 0)
    + (CollisionFlag.PRECIPITATION_BLOCKING or 0) + (CollisionFlag.VEHICLE or 0) + (CollisionFlag.DYNAMIC_OBJECT or 0)
SprayDroneLaunch.BOX_MASK = (CollisionFlag.STATIC_OBJECT or 0) + (CollisionFlag.TREE or 0) + (CollisionFlag.BUILDING or 0)
-- paprsky začínají kousek nad dronem, aby nezačínaly v plošině
SprayDroneLaunch.START_OFFSET = 0.3
SprayDroneLaunch.RING_MARGIN = 0.3
SprayDroneLaunch.RING_POINTS = 8
-- výška kontroly: aspoň cestovní výška a CHECK_HEIGHT (volá SprayDroneStation), nikdy pod MIN_HEIGHT
SprayDroneLaunch.CHECK_HEIGHT = 12
SprayDroneLaunch.MIN_HEIGHT = 8
-- když je zásahů víc, hlásí se nejhorší (střecha / most je jistě natrvalo, strom se dá obletět jen přesunem vleku)
SprayDroneLaunch.REASON_RANK = { obstacle = 1, tree = 2, roof = 3 }

local probe = { root = nil, reason = nil, hits = nil, ray = 0 }

local function hasGroup(node, flag)
    return flag ~= nil and flag ~= 0 and CollisionFlag.getHasGroupFlagSet(node, flag)
end

function SprayDroneLaunch.classify(node)
    if hasGroup(node, CollisionFlag.TREE) then
        return "tree"
    end
    if hasGroup(node, CollisionFlag.BUILDING)
        or (hasGroup(node, CollisionFlag.PRECIPITATION_BLOCKING) and not hasGroup(node, CollisionFlag.VEHICLE)) then
        return "roof"
    end
    return "obstacle"
end

local function isOwn(node)
    if probe.root == nil then
        return false
    end
    local object = g_currentMission:getNodeObject(node)
    return object ~= nil and (object == probe.root or (object.getRootVehicle ~= nil and object:getRootVehicle() == probe.root))
end

local function note(node, x, y, z, distance)
    if node == nil or node == 0 or not entityExists(node) or getHasTrigger(node) or isOwn(node) then
        return
    end
    local reason = SprayDroneLaunch.classify(node)
    if probe.reason == nil or SprayDroneLaunch.REASON_RANK[reason] > SprayDroneLaunch.REASON_RANK[probe.reason] then
        probe.reason = reason
    end
    if probe.hits ~= nil then
        table.insert(probe.hits, { ray = probe.ray, node = node, name = getName(node), reason = reason, x = x, y = y, z = z, distance = distance })
    end
end

function probe.rayCallback(_, hitObjectId, x, y, z, distance)
    note(hitObjectId, x, y, z, distance)
    return true
end

function probe.boxCallback(_, nodeId)
    if nodeId ~= 0 and getHasClassId(nodeId, ClassIds.SHAPE) then
        note(nodeId, nil, nil, nil, nil)
    end
    return true
end

-- Je nad bodem (x, y, z) (dron na plošině) do výšky height volno? radius = poloměr dronu s vrtulemi, rootVehicle = vlastní
-- ({ray (0 = box), node, name, reason, x, y, z, distance}).
function SprayDroneLaunch.getClearance(x, y, z, radius, height, rootVehicle, hits)
    local h = math.max(height or SprayDroneLaunch.CHECK_HEIGHT, SprayDroneLaunch.MIN_HEIGHT)
    local y0 = y + SprayDroneLaunch.START_OFFSET
    local r = radius + SprayDroneLaunch.RING_MARGIN
    probe.root, probe.reason, probe.hits, probe.ray = rootVehicle, nil, hits, 1
    raycastAll(x, y0, z, 0, 1, 0, h, "rayCallback", probe, SprayDroneLaunch.RAY_MASK)
    for _, ringR in ipairs({ r, r * 0.5 }) do
        for i = 1, SprayDroneLaunch.RING_POINTS do
            local a = 2 * math.pi * (i - 1) / SprayDroneLaunch.RING_POINTS
            probe.ray = probe.ray + 1
            raycastAll(x + math.cos(a) * ringR, y0, z + math.sin(a) * ringR, 0, 1, 0, h, "rayCallback", probe, SprayDroneLaunch.RAY_MASK)
        end
    end
    probe.ray = 0
    overlapBox(x, y0 + h * 0.5, z, 0, 0, 0, r, h * 0.5, r, "boxCallback", probe, SprayDroneLaunch.BOX_MASK, true, true, false, true)
    local reason = probe.reason
    probe.root, probe.reason, probe.hits = nil, nil, nil
    return reason == nil, reason
end
