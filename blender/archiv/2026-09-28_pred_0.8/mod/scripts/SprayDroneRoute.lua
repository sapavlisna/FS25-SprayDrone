-- Geometrie pro postřikový dron: pole pod bodem, řádky přes polygon pole (boustrophedon),
-- ořez dosahem, vynechání už ošetřených míst, výška přeletu nad překážkami a rozdělení práce na dávky.
-- Trasa je v rovině xz; výšky jsou relativně k terénu.

SprayDroneRoute = {}

SprayDroneRoute.SAMPLE_STEP = 2
SprayDroneRoute.MIN_LEG_LENGTH = 2

-- překážky: statické objekty (sloupy, ploty), stromy, budovy; terén a vozidla (vlastní vlek) ne
SprayDroneRoute.OBSTACLE_MASK = CollisionFlag.STATIC_OBJECT + CollisionFlag.TREE + CollisionFlag.BUILDING
SprayDroneRoute.OBSTACLE_STEP = 5
-- pás kolem osy přeletu: rozpětí dronu s vrtulemi je ~3,3 m; pojistka za letu hlídá 0 a ±1,2 m, takže to musí být i tady
SprayDroneRoute.OBSTACLE_SIDES = { -2.4, -1.2, 0, 1.2, 2.4 }
SprayDroneRoute.OBSTACLE_SCAN_HEIGHT = 120
SprayDroneRoute.OBSTACLE_RAISE_STEP = 2

-- přistání: rychlost klesání u země min(climbSpeed, LANDING_MIN_SPEED + LANDING_SLOPE * zbývající výška)
SprayDroneRoute.LANDING_MIN_SPEED = 0.35
SprayDroneRoute.LANDING_SLOPE = 0.5
SprayDroneRoute.TURN_OVERHEAD = 1.0

-- baterie: odběr roste s kvadrátem hmotnosti (DJI T50: 7 min vznášení s plnou nádrží, 22 min prázdný, 92 / 52 kg)
SprayDroneRoute.BATTERY_MASS_EXPONENT = 2

-- Násobek odběru baterie proti vodorovnému letu s plnou nádrží: hmotnost s náplní fill litrů krát fáze letu.
function SprayDroneRoute.drainFactor(p, fill, phase)
    local mass = p.droneMass + math.max(fill, 0) * p.massPerLiter
    return (mass / p.fullMass) ^ SprayDroneRoute.BATTERY_MASS_EXPONENT * (phase or 1)
end

-- Čas přesunu po přímce: rozjezd z vIn, nejvýš vMax, dojezd na vOut, zrychlení i brzdění acc.
function SprayDroneRoute.moveTime(dist, vMax, acc, vIn, vOut)
    if dist <= 0 then
        return 0
    end
    vIn, vOut = math.min(vIn or 0, vMax), math.min(vOut or 0, vMax)
    local dUp = (vMax * vMax - vIn * vIn) / (2 * acc)
    local dDown = (vMax * vMax - vOut * vOut) / (2 * acc)
    if dUp + dDown <= dist then
        return (vMax - vIn) / acc + (vMax - vOut) / acc + (dist - dUp - dDown) / vMax
    end
    local vPeak = math.sqrt((2 * acc * dist + vIn * vIn + vOut * vOut) * 0.5)
    return math.max((2 * vPeak - vIn - vOut) / acc, dist / math.max(vPeak, 0.1))
end

-- Klesání o dh na plošinu: nahoře climbSpeed, u země zpomaluje podle LANDING_*.
function SprayDroneRoute.landingTime(dh, p)
    if dh <= 0 then
        return 0
    end
    local slow = (p.climbSpeed - SprayDroneRoute.LANDING_MIN_SPEED) / SprayDroneRoute.LANDING_SLOPE
    local d = math.min(dh, slow)
    local t = math.log((SprayDroneRoute.LANDING_MIN_SPEED + SprayDroneRoute.LANDING_SLOPE * d) / SprayDroneRoute.LANDING_MIN_SPEED) / SprayDroneRoute.LANDING_SLOPE
    return t + SprayDroneRoute.moveTime(dh - d, p.climbSpeed, p.acceleration, 0, p.climbSpeed)
end

function SprayDroneRoute.turnTime(fromYaw, toYaw, p)
    if fromYaw == nil or toYaw == nil then
        return 0
    end
    return math.abs(MathUtil.getAngleDifference(toYaw, fromYaw)) / p.yawSpeed * SprayDroneRoute.TURN_OVERHEAD
end

function SprayDroneRoute.getHeading(x1, z1, x2, z2)
    if MathUtil.vector2Length(x2 - x1, z2 - z1) < 0.5 then
        return nil
    end
    return MathUtil.getYRotationFromDirection(x2 - x1, z2 - z1)
end

---------------------------------------------------------------------------------------------------
-- překážky

local probe = { hit = false, y = 0 }

function probe:raycastCallback(hitObjectId, x, y, z, distance)
    if hitObjectId ~= nil and hitObjectId ~= 0 then
        self.hit, self.y, self.distance = true, y, distance
    end
    return false
end

-- Nejbližší překážka na paprsku: vrací zasaženo a vzdálenost.
function SprayDroneRoute.castRay(x, y, z, dx, dy, dz, length)
    probe.hit, probe.distance = false, length
    raycastClosest(x, y, z, dx, dy, dz, length, "raycastCallback", probe, SprayDroneRoute.OBSTACLE_MASK)
    return probe.hit, probe.distance
end

-- Výška nejvyšší překážky nad terénem v bodě (svislý paprsek shora); 0, když tam nic není.
function SprayDroneRoute.getObstacleHeightAt(x, z)
    local terrainY = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
    probe.hit = false
    raycastClosest(x, terrainY + SprayDroneRoute.OBSTACLE_SCAN_HEIGHT, z, 0, -1, 0, SprayDroneRoute.OBSTACLE_SCAN_HEIGHT,
        "raycastCallback", probe, SprayDroneRoute.OBSTACLE_MASK)
    return probe.hit and math.max(probe.y - terrainY, 0) or 0
end

-- Výška přeletu nad terénem pro úsek (x1,z1) -> (x2,z2) v pásu OBSTACLE_SIDES kolem osy: nejvyšší překážka
-- (svislé paprsky po OBSTACLE_STEP) + clearance, nejméně minHeight. Pak se ve zvolené výšce proletí paprsky
-- podél úseku; co svislé paprsky minuly (kmen a větve stromu mezi vzorky), výšku zvedne. Hledá se jen do
-- maxHeight + clearance, víc už je stejně odmítnuto. Vrací výšku a nejvyšší nalezenou překážku.
function SprayDroneRoute.getClearHeight(x1, z1, x2, z2, minHeight, clearance, maxHeight)
    local len = MathUtil.vector2Length(x2 - x1, z2 - z1)
    local n = math.max(math.ceil(len / SprayDroneRoute.OBSTACLE_STEP), 1)
    local sideX, sideZ = 0, 0
    if len > 0.01 then
        sideX, sideZ = (z2 - z1) / len, -(x2 - x1) / len
    end
    local points = {}
    local obstacle = 0
    for i = 0, n do
        local t = i / n
        local px, pz = x1 + (x2 - x1) * t, z1 + (z2 - z1) * t
        table.insert(points, { x = px, z = pz, y = getTerrainHeightAtWorldPos(g_terrainNode, px, 0, pz) })
        for _, s in ipairs(SprayDroneRoute.OBSTACLE_SIDES) do
            obstacle = math.max(obstacle, SprayDroneRoute.getObstacleHeightAt(px + sideX * s, pz + sideZ * s))
        end
    end

    local h = math.max(minHeight, obstacle + clearance)
    local limit = maxHeight + clearance
    for i = 1, #points - 1 do
        local a, b = points[i], points[i + 1]
        local raised = false
        while h <= limit do
            local blocked = false
            for _, s in ipairs(SprayDroneRoute.OBSTACLE_SIDES) do
                local ax, az = a.x + sideX * s, a.z + sideZ * s
                local dx, dy, dz = b.x - a.x, b.y - a.y, b.z - a.z
                local d = math.sqrt(dx * dx + dy * dy + dz * dz)
                if d > 0.01 and SprayDroneRoute.castRay(ax, a.y + h, az, dx / d, dy / d, dz / d, d) then
                    blocked = true
                    break
                end
            end
            if not blocked then
                break
            end
            h = h + SprayDroneRoute.OBSTACLE_RAISE_STEP
            raised = true
        end
        if raised then
            obstacle = math.max(obstacle, h - SprayDroneRoute.OBSTACLE_RAISE_STEP)
            h = math.max(h, obstacle + clearance)
        end
    end
    return h, obstacle
end

function SprayDroneRoute.getFieldById(fieldId)
    if fieldId == nil or fieldId == 0 then
        return nil
    end
    for _, field in ipairs(g_fieldManager:getFields()) do
        if field:getId() == fieldId then
            return field
        end
    end
    return nil
end

function SprayDroneRoute.getPolygon(field)
    if field.sdtPolygon == nil then
        local poly = {}
        for _, node in ipairs(field:getPolygonPoints()) do
            local x, _, z = getWorldTranslation(node)
            table.insert(poly, { x = x, z = z })
        end
        field.sdtPolygon = poly
    end
    return field.sdtPolygon
end

function SprayDroneRoute.isPointInPolygon(poly, x, z)
    local inside = false
    local j = #poly
    for i = 1, #poly do
        local a, b = poly[i], poly[j]
        if (a.z > z) ~= (b.z > z) and x < (b.x - a.x) * (z - a.z) / (b.z - a.z) + a.x then
            inside = not inside
        end
        j = i
    end
    return inside
end

-- Nejbližší bod na hranici polygonu: vrací vzdálenost a bod.
function SprayDroneRoute.nearestBoundaryPoint(poly, x, z)
    local best, bx, bz = math.huge, x, z
    local j = #poly
    for i = 1, #poly do
        local a, b = poly[j], poly[i]
        local ex, ez = b.x - a.x, b.z - a.z
        local len2 = ex * ex + ez * ez
        local t = 0
        if len2 > 0 then
            t = math.clamp(((x - a.x) * ex + (z - a.z) * ez) / len2, 0, 1)
        end
        local px, pz = a.x + ex * t, a.z + ez * t
        local d = MathUtil.vector2Length(x - px, z - pz)
        if d < best then
            best, bx, bz = d, px, pz
        end
        j = i
    end
    return best, bx, bz
end

function SprayDroneRoute.distanceToPolygon(poly, x, z)
    if SprayDroneRoute.isPointInPolygon(poly, x, z) then
        return 0
    end
    return (SprayDroneRoute.nearestBoundaryPoint(poly, x, z))
end

-- Pole, ve kterém bod leží; když žádné, nejbližší pole do maxDistance. filterFunc(field) vybírá povolená pole.
function SprayDroneRoute.findField(x, z, maxDistance, filterFunc)
    local bestField, bestDistance = nil, maxDistance or 0
    for _, field in ipairs(g_fieldManager:getFields()) do
        if field:getId() ~= nil and (filterFunc == nil or filterFunc(field)) then
            local poly = SprayDroneRoute.getPolygon(field)
            if #poly >= 3 then
                local d = SprayDroneRoute.distanceToPolygon(poly, x, z)
                if d == 0 then
                    return field
                end
                if d < bestDistance then
                    bestField, bestDistance = field, d
                end
            end
        end
    end
    return bestField
end

-- Potřebuje místo ještě postřik? Stejné podmínky, jaké klade FSDensityMapUtil.updateFertilizerArea/updateHerbicideArea,
-- aby dron nelétal nad plochou, kterou by vanilla postřik stejně nezměnil.
function SprayDroneRoute.getNeedsWork(x, z, sprayType, farmlandId)
    if g_farmlandManager:getFarmlandIdAtWorldPosition(x, z) ~= farmlandId then
        return false
    end
    local isOnField = FSDensityMapUtil.getFieldDataAtWorldPosition(x, 0, z)
    if not isOnField then
        return false
    end

    local fruitIndex, growthState = FSDensityMapUtil.getFruitTypeIndexAtWorldPos(x, z)
    if fruitIndex ~= nil then
        local fruitType = g_fruitTypeManager:getFruitTypeByIndex(fruitIndex)
        if fruitType ~= nil and growthState ~= nil and growthState >= fruitType.minHarvestingGrowthState
            and growthState <= fruitType.maxHarvestingGrowthState then
            return false
        end
    end

    local groundSystem = g_currentMission.fieldGroundSystem
    if sprayType.isHerbicide then
        local weedSystem = g_currentMission.weedSystem
        if weedSystem == nil or not weedSystem:getMapHasWeed() then
            return false
        end
        local replacements = weedSystem:getHerbicideReplacements()
        local weedState = weedSystem:getWeedStateAtWorldPos(x, z)
        return replacements ~= nil and replacements.weed ~= nil and replacements.weed.replacements[weedState] ~= nil
    end

    if groundSystem:getValueAtWorldPos(FieldDensityMap.SPRAY_TYPE, x, 0, z) == sprayType.sprayGroundType then
        return false
    end
    local maxLevel = groundSystem:getMaxValue(FieldDensityMap.SPRAY_LEVEL)
    return groundSystem:getValueAtWorldPos(FieldDensityMap.SPRAY_LEVEL, x, 0, z) < maxLevel
end

local function clipToCircle(x1, z1, x2, z2, cx, cz, radius)
    local dx, dz = x2 - x1, z2 - z1
    local fx, fz = x1 - cx, z1 - cz
    local a = dx * dx + dz * dz
    local b = 2 * (fx * dx + fz * dz)
    local c = fx * fx + fz * fz - radius * radius
    local disc = b * b - 4 * a * c
    if a == 0 or disc <= 0 then
        return nil
    end
    local sq = math.sqrt(disc)
    local t1 = math.max((-b - sq) / (2 * a), 0)
    local t2 = math.min((-b + sq) / (2 * a), 1)
    if t2 <= t1 then
        return nil
    end
    return t1, t2
end

-- Seřazené řádky (legy) k postřiku: {x1, z1, x2, z2, len}. Směr řádků podle nejdelší hrany pole.
function SprayDroneRoute.buildLegs(field, homeX, homeZ, range, workWidth, sprayType)
    local poly = SprayDroneRoute.getPolygon(field)
    if #poly < 3 or sprayType == nil then
        return {}
    end

    local dirX, dirZ, bestLen = 1, 0, 0
    for i = 1, #poly do
        local a, b = poly[i], poly[i % #poly + 1]
        local len = MathUtil.vector2Length(b.x - a.x, b.z - a.z)
        if len > bestLen then
            bestLen = len
            dirX, dirZ = (b.x - a.x) / len, (b.z - a.z) / len
        end
    end
    local nX, nZ = -dirZ, dirX

    local minN, maxN = math.huge, -math.huge
    for _, p in ipairs(poly) do
        local n = p.x * nX + p.z * nZ
        minN, maxN = math.min(minN, n), math.max(maxN, n)
    end

    local homeN = homeX * nX + homeZ * nZ
    local offsets = {}
    local s = minN + workWidth * 0.5
    while s < maxN do
        table.insert(offsets, s)
        s = s + workWidth
    end
    if math.abs(homeN - maxN) < math.abs(homeN - minN) then
        local reversed = {}
        for i = #offsets, 1, -1 do
            table.insert(reversed, offsets[i])
        end
        offsets = reversed
    end

    local farmlandId = field:getId()
    local legs = {}
    local forward = true
    for _, off in ipairs(offsets) do
        local ts = {}
        local j = #poly
        for i = 1, #poly do
            local a, b = poly[j], poly[i]
            local na, nb = a.x * nX + a.z * nZ, b.x * nX + b.z * nZ
            if (na <= off) ~= (nb <= off) then
                local f = (off - na) / (nb - na)
                local ix, iz = a.x + (b.x - a.x) * f, a.z + (b.z - a.z) * f
                table.insert(ts, ix * dirX + iz * dirZ)
            end
            j = i
        end
        table.sort(ts)

        local lineLegs = {}
        for k = 1, #ts - 1, 2 do
            local x1, z1 = nX * off + dirX * ts[k], nZ * off + dirZ * ts[k]
            local x2, z2 = nX * off + dirX * ts[k + 1], nZ * off + dirZ * ts[k + 1]
            local c1, c2 = clipToCircle(x1, z1, x2, z2, homeX, homeZ, range)
            if c1 ~= nil then
                local ax, az = x1 + (x2 - x1) * c1, z1 + (z2 - z1) * c1
                local bx, bz = x1 + (x2 - x1) * c2, z1 + (z2 - z1) * c2
                SprayDroneRoute.appendNeededParts(lineLegs, ax, az, bx, bz, sprayType, farmlandId)
            end
        end

        if #lineLegs > 0 then
            if forward then
                for _, leg in ipairs(lineLegs) do
                    table.insert(legs, leg)
                end
            else
                for i = #lineLegs, 1, -1 do
                    local leg = lineLegs[i]
                    table.insert(legs, { x1 = leg.x2, z1 = leg.z2, x2 = leg.x1, z2 = leg.z1, len = leg.len })
                end
            end
            forward = not forward
        end
    end
    return legs
end

-- Rozdělí úsek na části, kde je ještě co postřikovat (vzorky po SAMPLE_STEP m po středu pruhu).
function SprayDroneRoute.appendNeededParts(target, ax, az, bx, bz, sprayType, farmlandId)
    local len = MathUtil.vector2Length(bx - ax, bz - az)
    if len < SprayDroneRoute.MIN_LEG_LENGTH then
        return
    end
    local step = SprayDroneRoute.SAMPLE_STEP
    local n = math.max(math.floor(len / step), 1)
    local runStart = nil
    for i = 0, n do
        local t = i / n
        local needs = SprayDroneRoute.getNeedsWork(ax + (bx - ax) * t, az + (bz - az) * t, sprayType, farmlandId)
        if needs and runStart == nil then
            runStart = t
        end
        if runStart ~= nil and (not needs or i == n) then
            local runEnd = needs and 1 or t
            -- rozšíření o půl kroku, aby okraje běhu nezůstaly neošetřené
            local pad = 0.5 / n
            local t1, t2 = math.max(runStart - pad, 0), math.min(runEnd + pad, 1)
            local legLen = (t2 - t1) * len
            if legLen >= SprayDroneRoute.MIN_LEG_LENGTH then
                table.insert(target, {
                    x1 = ax + (bx - ax) * t1, z1 = az + (bz - az) * t1,
                    x2 = ax + (bx - ax) * t2, z2 = az + (bz - az) * t2,
                    len = legLen
                })
            end
            runStart = nil
        end
    end
end

---------------------------------------------------------------------------------------------------
-- letová plocha: přelet vlek <-> pole smí vést jen uvnitř nakreslené plochy nebo nad polem (sjednocení obou);
-- nejkratší cesta po grafu viditelnosti nad lomovými vrcholy, Dijkstra od vleku

SprayDroneRoute.AREA_EPS = 0.5

local function segmentHit(ax, az, bx, bz, cx, cz, dx, dz)
    local rx, rz = bx - ax, bz - az
    local sx, sz = dx - cx, dz - cz
    local den = rx * sz - rz * sx
    if math.abs(den) < 1e-9 then
        return nil
    end
    local qx, qz = cx - ax, cz - az
    local t = (qx * sz - qz * sx) / den
    local u = (qx * rz - qz * rx) / den
    if t >= 0 and t <= 1 and u >= 0 and u <= 1 then
        return t
    end
    return nil
end

local function signedArea(poly)
    local s = 0
    for i = 1, #poly do
        local a, b = poly[i], poly[i % #poly + 1]
        s = s + a.x * b.z - b.x * a.z
    end
    return s * 0.5
end

function SprayDroneRoute.isInCorridor(c, x, z)
    for _, poly in ipairs(c.polys) do
        if SprayDroneRoute.isPointInPolygon(poly, x, z) or SprayDroneRoute.nearestBoundaryPoint(poly, x, z) <= SprayDroneRoute.AREA_EPS then
            return true
        end
    end
    return false
end

-- Vede úsek celý uvnitř? Rozdělí se průsečíky se všemi hranami; každý kus je celý uvnitř nebo venku, stačí jeho střed.
function SprayDroneRoute.isCorridorSegmentFree(c, ax, az, bx, bz)
    local len = MathUtil.vector2Length(bx - ax, bz - az)
    if len < 0.05 then
        return SprayDroneRoute.isInCorridor(c, ax, az)
    end
    local minX, maxX, minZ, maxZ = math.min(ax, bx), math.max(ax, bx), math.min(az, bz), math.max(az, bz)
    local ts = { 0, 1 }
    for _, e in ipairs(c.edges) do
        if e.maxX >= minX and e.minX <= maxX and e.maxZ >= minZ and e.minZ <= maxZ then
            local t = segmentHit(ax, az, bx, bz, e.ax, e.az, e.bx, e.bz)
            if t ~= nil then
                table.insert(ts, t)
            end
        end
    end
    table.sort(ts)
    for i = 1, #ts - 1 do
        if (ts[i + 1] - ts[i]) * len > 0.05 then
            local m = (ts[i] + ts[i + 1]) * 0.5
            if not SprayDroneRoute.isInCorridor(c, ax + (bx - ax) * m, az + (bz - az) * m) then
                return false
            end
        end
    end
    return true
end

-- Graf pro plochu area a polygon pole field. Cesta se láme jen v lomových vrcholech hranice sjednocení
-- a v průsečících obou hranic, jiné uzly potřeba nejsou.
function SprayDroneRoute.newCorridor(area, field)
    local c = { polys = { area, field }, edges = {}, nodes = {}, adj = {} }
    for _, poly in ipairs(c.polys) do
        for i = 1, #poly do
            local a, b = poly[i], poly[i % #poly + 1]
            table.insert(c.edges, { ax = a.x, az = a.z, bx = b.x, bz = b.z,
                minX = math.min(a.x, b.x), maxX = math.max(a.x, b.x), minZ = math.min(a.z, b.z), maxZ = math.max(a.z, b.z) })
        end
    end
    for pi, poly in ipairs(c.polys) do
        local other = c.polys[3 - pi]
        local orient = signedArea(poly) > 0 and 1 or -1
        for i = 1, #poly do
            local prev, cur, nxt = poly[(i - 2) % #poly + 1], poly[i], poly[i % #poly + 1]
            local cross = (cur.x - prev.x) * (nxt.z - cur.z) - (cur.z - prev.z) * (nxt.x - cur.x)
            local insideOther = SprayDroneRoute.isPointInPolygon(other, cur.x, cur.z)
                and SprayDroneRoute.nearestBoundaryPoint(other, cur.x, cur.z) > SprayDroneRoute.AREA_EPS
            if cross * orient < -1e-6 and not insideOther then
                table.insert(c.nodes, { x = cur.x, z = cur.z })
            end
        end
    end
    for i = 1, #area do
        local a, b = area[i], area[i % #area + 1]
        for j = 1, #field do
            local f1, f2 = field[j], field[j % #field + 1]
            local t = segmentHit(a.x, a.z, b.x, b.z, f1.x, f1.z, f2.x, f2.z)
            if t ~= nil then
                table.insert(c.nodes, { x = a.x + (b.x - a.x) * t, z = a.z + (b.z - a.z) * t })
            end
        end
    end
    for i = 1, #c.nodes do
        c.adj[i] = {}
    end
    for i = 1, #c.nodes do
        local a = c.nodes[i]
        for j = i + 1, #c.nodes do
            local b = c.nodes[j]
            if SprayDroneRoute.isCorridorSegmentFree(c, a.x, a.z, b.x, b.z) then
                local d = MathUtil.vector2Length(b.x - a.x, b.z - a.z)
                table.insert(c.adj[i], { j, d })
                table.insert(c.adj[j], { i, d })
            end
        end
    end
    return c
end

-- Bod uvnitř beze změny; venku do tolerance posunutý na nejbližší bod hranice; jinak nil.
function SprayDroneRoute.snapToCorridor(c, x, z, tolerance)
    if SprayDroneRoute.isInCorridor(c, x, z) then
        return x, z
    end
    local best, bx, bz = math.huge, x, z
    for _, poly in ipairs(c.polys) do
        local d, px, pz = SprayDroneRoute.nearestBoundaryPoint(poly, x, z)
        if d < best then
            best, bx, bz = d, px, pz
        end
    end
    if best > tolerance then
        return nil
    end
    return bx, bz
end

-- Vlek v grafu: vzdálenosti všech uzlů k vleku (Dijkstra). False, když vlek stojí mimo plochu víc než tolerance.
function SprayDroneRoute.setCorridorHome(c, hx, hz, tolerance)
    c.home = { x = hx, z = hz }
    local gx, gz = SprayDroneRoute.snapToCorridor(c, hx, hz, tolerance)
    c.homeOk = gx ~= nil
    if not c.homeOk then
        return false
    end
    c.home.gx, c.home.gz = gx, gz
    local n = #c.nodes
    local dist, prev, done = {}, {}, {}
    for i = 1, n do
        local v = c.nodes[i]
        dist[i] = math.huge
        if SprayDroneRoute.isCorridorSegmentFree(c, gx, gz, v.x, v.z) then
            dist[i], prev[i] = MathUtil.vector2Length(v.x - gx, v.z - gz), 0
        end
    end
    for _ = 1, n do
        local best, u = math.huge, nil
        for i = 1, n do
            if not done[i] and dist[i] < best then
                best, u = dist[i], i
            end
        end
        if u == nil then
            break
        end
        done[u] = true
        for _, e in ipairs(c.adj[u]) do
            local d = best + e[2]
            if d < dist[e[1]] then
                dist[e[1]], prev[e[1]] = d, u
            end
        end
    end
    c.dist, c.prev = dist, prev
    return true
end

-- Nejkratší cesta z bodu (x, z) na vlek uvnitř plochy: body od (x, z) po vlek, nil, když neexistuje.
function SprayDroneRoute.getCorridorPathHome(c, x, z, tolerance)
    if not c.homeOk then
        return nil
    end
    local qx, qz = SprayDroneRoute.snapToCorridor(c, x, z, tolerance)
    if qx == nil then
        return nil
    end
    local home = c.home
    local best, via = math.huge, nil
    if SprayDroneRoute.isCorridorSegmentFree(c, qx, qz, home.gx, home.gz) then
        best, via = MathUtil.vector2Length(home.gx - qx, home.gz - qz), 0
    end
    for i, v in ipairs(c.nodes) do
        local d = MathUtil.vector2Length(v.x - qx, v.z - qz) + c.dist[i]
        if d < best and SprayDroneRoute.isCorridorSegmentFree(c, qx, qz, v.x, v.z) then
            best, via = d, i
        end
    end
    if via == nil then
        return nil
    end
    local points = {}
    local function add(px, pz)
        local last = points[#points]
        if last == nil or MathUtil.vector2Length(px - last.x, pz - last.z) > 0.1 then
            table.insert(points, { x = px, z = pz })
        end
    end
    add(x, z)
    add(qx, qz)
    while via ~= 0 do
        local v = c.nodes[via]
        add(v.x, v.z)
        via = c.prev[via]
    end
    add(home.gx, home.gz)
    add(home.x, home.z)
    if #points < 2 then
        table.insert(points, { x = home.x, z = home.z })
    end
    return points
end

function SprayDroneRoute.getPathLength(points)
    local length = 0
    for k = 1, #points - 1 do
        length = length + MathUtil.vector2Length(points[k + 1].x - points[k].x, points[k + 1].z - points[k].z)
    end
    return length
end

-- Čas přeletu po lomené čáře plan.points, úsek k ve výšce plan.heights[k] (nebo všude plan.height): před úsekem
-- dron vystoupá svisle, klesá za letu. Vrací čas, yaw, výšku na konci a spotřebu baterie s náplní fill.
function SprayDroneRoute.transitTime(plan, startH, startYaw, p, fill)
    local t, e, h, yaw = 0, 0, startH, startYaw
    local pts = plan.points
    for k = 1, #pts - 1 do
        local a, b = pts[k], pts[k + 1]
        local hs = plan.heights ~= nil and plan.heights[k] or plan.height
        if hs > h then
            local climb = SprayDroneRoute.moveTime(hs - h, p.ascentSpeed, p.acceleration, 0, 0)
            t, e = t + climb, e + climb * p.climbFactor
            h = hs
        end
        local heading = SprayDroneRoute.getHeading(a.x, a.z, b.x, b.z)
        local len = MathUtil.vector2Length(b.x - a.x, b.z - a.z)
        local turn = SprayDroneRoute.turnTime(yaw, heading, p)
        local move = SprayDroneRoute.moveTime(math.sqrt(len * len + (h - hs) * (h - hs)), p.cruiseSpeed, p.acceleration, 0, 0)
        t, e = t + turn + move, e + turn * p.hoverFactor + move
        yaw = heading or yaw
        h = hs
    end
    return t, yaw, h, e * SprayDroneRoute.drainFactor(p, fill or 0)
end

-- Waypointy přeletu: tam z vleku (vzlet svisle), nebo zpět z pole (svislé stoupání, na konci přistání na vleku).
-- Na lomu do vyššího úseku dron vystoupá na místě, do nižšího klesá až za letu.
function SprayDroneRoute.appendTransitWaypoints(wps, plan, p, outbound)
    local pts, hs = plan.points, plan.heights
    local n = #pts
    table.insert(wps, { x = pts[1].x, z = pts[1].z, h = hs[1], speed = p.ascentSpeed, home = outbound or nil })
    for k = 2, n - 1 do
        table.insert(wps, { x = pts[k].x, z = pts[k].z, h = hs[k - 1], speed = p.cruiseSpeed })
        if hs[k] > hs[k - 1] then
            table.insert(wps, { x = pts[k].x, z = pts[k].z, h = hs[k], speed = p.ascentSpeed })
        end
    end
    table.insert(wps, { x = pts[n].x, z = pts[n].z, h = hs[n - 1], speed = p.cruiseSpeed, home = not outbound or nil })
    if not outbound then
        table.insert(wps, { x = pts[n].x, z = pts[n].z, h = p.restHeight, speed = p.climbSpeed, home = true, land = true })
    end
end

local function legPoint(leg, offset)
    local t = leg.len > 0 and offset / leg.len or 0
    return leg.x1 + (leg.x2 - leg.x1) * t, leg.z1 + (leg.z2 - leg.z1) * t
end

-- Spotřeba baterie na cestu z bodu na poli (ve výšce postřiku, natočeného yaw) domů ve výšce h a přistání s náplní fill.
function SprayDroneRoute.returnEnergy(x, z, yaw, homeX, homeZ, h, p, fill)
    local toHome = SprayDroneRoute.getHeading(x, z, homeX, homeZ)
    return (SprayDroneRoute.moveTime(math.max(h - p.sprayHeight, 0), p.ascentSpeed, p.acceleration, 0, 0) * p.climbFactor
        + SprayDroneRoute.turnTime(yaw, toHome, p) * p.hoverFactor
        + SprayDroneRoute.moveTime(MathUtil.vector2Length(x - homeX, z - homeZ), p.cruiseSpeed, p.acceleration, 0, 0)
        + SprayDroneRoute.landingTime(h - p.restHeight, p) * p.descentFactor) * SprayDroneRoute.drainFactor(p, fill)
end

-- Jedna dávka od (legIndex, offset): kolik zvládne nádrž (fill litrů) a baterie (battery = sekundy vodorovného
-- letu s plnou nádrží) včetně cesty tam a zpět. Vrací waypointy {x, z, h, speed, spray, home, land}, index a offset,
-- kde další dávka začne, délku postřiku a info {time, energy, height, tooHigh}. Waypointy s home=true se za letu
-- přepočítají na aktuální polohu dronu na vleku. Časy (od vzletu po dosednutí) počítají s rozjezdem a brzděním
-- na každém waypointu, otáčením a pomalým dosednutím; spotřeba baterie navíc s fází letu (stoupání, otáčení na
-- místě, klesání) a s hmotností náplně, která při postřiku ubývá.
-- p: workWidth, sprayHeight, transitHeight, cruiseSpeed, sprayingSpeed, climbSpeed, ascentSpeed, acceleration,
-- yawSpeed, litersPerMeter, batteryReserve, restHeight, homeYaw, droneMass, fullMass, massPerLiter, hoverFactor,
-- climbFactor, descentFactor,
-- getTransit(x, z, outbound) -> přelet {points, heights, height, tooHigh, length} mezi vlekem a bodem, nebo nil a důvod,
-- getHomePath(x, z) -> body cesty na vlek letovou plochou (jen když je plocha nakreslená)
function SprayDroneRoute.planBatch(legs, legIndex, offset, homeX, homeZ, fill, battery, p)
    local budget = battery - p.batteryReserve
    local acc = p.acceleration
    if legIndex > #legs then
        return nil, legIndex, offset, 0, { time = 0, height = p.transitHeight }
    end

    local firstX, firstZ = legPoint(legs[legIndex], offset)
    local outPlan, noPath = p.getTransit(firstX, firstZ, true)
    if outPlan == nil then
        return nil, legIndex, offset, 0, { time = 0, height = p.transitHeight, noPath = noPath }
    end
    local hOut = outPlan.height
    if outPlan.tooHigh then
        return nil, legIndex, offset, 0, { time = 0, height = hOut, tooHigh = true }
    end

    local timeUsed, yaw, arrivalHeight, energyUsed = SprayDroneRoute.transitTime(outPlan, p.restHeight, p.homeYaw, p, fill)
    local curX, curZ = firstX, firstZ
    local atSprayHeight = false
    local sprayed = 0
    local wps = {}
    SprayDroneRoute.appendTransitWaypoints(wps, outPlan, p, true)

    -- návrat z bodu na řádku: s plochou horní odhad přes začátek nebo konec řádku (cesty z nich jsou v paměti)
    local function estimateReturn(x, z, legYaw, leg, endFill)
        if p.getHomePath ~= nil then
            local best = math.huge
            for _, q in ipairs({ { leg.x1, leg.z1 }, { leg.x2, leg.z2 } }) do
                local path = p.getHomePath(q[1], q[2])
                if path ~= nil then
                    local pts = { { x = x, z = z } }
                    for _, pt in ipairs(path) do
                        table.insert(pts, pt)
                    end
                    local _, _, _, e = SprayDroneRoute.transitTime({ points = pts, height = hOut }, p.sprayHeight, legYaw, p, endFill)
                    best = math.min(best, e + SprayDroneRoute.landingTime(hOut - p.restHeight, p) * p.descentFactor
                        * SprayDroneRoute.drainFactor(p, endFill))
                end
            end
            if best < math.huge then
                return best
            end
        end
        return SprayDroneRoute.returnEnergy(x, z, legYaw, homeX, homeZ, hOut, p, endFill)
    end

    local i, off = legIndex, offset
    while i <= #legs do
        local leg = legs[i]
        local sx, sz = legPoint(leg, off)
        local legYaw = SprayDroneRoute.getHeading(leg.x1, leg.z1, leg.x2, leg.z2)
        local moveYaw = SprayDroneRoute.getHeading(curX, curZ, sx, sz)
        local dist = MathUtil.vector2Length(sx - curX, sz - curZ)
        local turn = SprayDroneRoute.turnTime(yaw, moveYaw or legYaw, p) + SprayDroneRoute.turnTime(moveYaw, legYaw, p)
        local shift = SprayDroneRoute.moveTime(dist, p.cruiseSpeed, acc, 0, 0)
        local descent = 0
        if not atSprayHeight then
            descent = SprayDroneRoute.moveTime(math.max(arrivalHeight - p.sprayHeight, 0), p.climbSpeed, acc, 0, 0)
        end
        local moveTime = turn + shift + descent
        local moveEnergy = (turn * p.hoverFactor + shift + descent * p.descentFactor) * SprayDroneRoute.drainFactor(p, fill)
        local remaining = leg.len - off
        local maxLen = math.min(remaining, fill / p.litersPerMeter)

        -- při postřiku náplň ubývá rovnoměrně, spotřeba se bere s průměrnou náplní úseku
        local function sprayEnergy(len)
            return SprayDroneRoute.moveTime(len, p.sprayingSpeed, acc, 0, 0)
                * SprayDroneRoute.drainFactor(p, fill - len * p.litersPerMeter * 0.5)
        end
        local function fits(len)
            local ex, ez = legPoint(leg, off + len)
            return energyUsed + moveEnergy + sprayEnergy(len)
                + estimateReturn(ex, ez, legYaw, leg, fill - len * p.litersPerMeter) <= budget
        end
        local len = maxLen
        if not fits(len) then
            local lo, hi = 0, maxLen
            for _ = 1, 16 do
                local mid = (lo + hi) * 0.5
                if fits(mid) then
                    lo = mid
                else
                    hi = mid
                end
            end
            len = lo
        end
        if len < 0.5 then
            break
        end

        if not atSprayHeight then
            table.insert(wps, { x = sx, z = sz, h = p.sprayHeight, speed = p.climbSpeed })
        else
            table.insert(wps, { x = sx, z = sz, h = p.sprayHeight, speed = p.cruiseSpeed })
        end
        local ex, ez = legPoint(leg, off + len)
        table.insert(wps, { x = ex, z = ez, sx = sx, sz = sz, h = p.sprayHeight, speed = p.sprayingSpeed, spray = true })

        timeUsed = timeUsed + moveTime + SprayDroneRoute.moveTime(len, p.sprayingSpeed, acc, 0, 0)
        energyUsed = energyUsed + moveEnergy + sprayEnergy(len)
        fill = fill - len * p.litersPerMeter
        sprayed = sprayed + len
        curX, curZ = ex, ez
        yaw = legYaw or yaw
        atSprayHeight = true

        if len < remaining - 0.01 then
            off = off + len
            break
        end
        i, off = i + 1, 0
    end

    if sprayed == 0 then
        return nil, legIndex, offset, 0, { time = 0, height = hOut }
    end
    local backPlan, backNoPath = p.getTransit(curX, curZ, false)
    if backPlan == nil then
        return nil, legIndex, offset, 0, { time = 0, height = hOut, noPath = backNoPath }
    end
    SprayDroneRoute.appendTransitWaypoints(wps, backPlan, p, false)
    local backTime, _, backHeight, backEnergy = SprayDroneRoute.transitTime(backPlan, p.sprayHeight, yaw, p, fill)
    local landing = SprayDroneRoute.landingTime(backHeight - p.restHeight, p)
    local time = timeUsed + backTime + landing
    local energy = energyUsed + backEnergy + landing * p.descentFactor * SprayDroneRoute.drainFactor(p, fill)
    return wps, i, off, sprayed, { time = time, energy = energy, height = math.max(hOut, backPlan.height), outPlan = outPlan, backPlan = backPlan }
end

-- Dávka s baterií, jakou dron na vleku dostane: pod p.batterySwapBelow kapacity se vymění za náhradní s nabitím
-- swapBattery (výchozí plná), a když s rozjetou baterií nejde naplánovat nic (ani přelet), vymění se taky. Vrací totéž
-- co planBatch a baterii na startu.
function SprayDroneRoute.planBatchWithSwap(legs, legIndex, offset, homeX, homeZ, fill, battery, p, swapBattery)
    swapBattery = swapBattery or p.batteryCapacity
    if battery < p.batteryCapacity * p.batterySwapBelow and swapBattery > battery then
        battery = swapBattery
    end
    local wps, ni, noff, sprayed, info = SprayDroneRoute.planBatch(legs, legIndex, offset, homeX, homeZ, fill, battery, p)
    if wps == nil and not info.tooHigh and info.noPath == nil and battery < swapBattery then
        battery = swapBattery
        wps, ni, noff, sprayed, info = SprayDroneRoute.planBatch(legs, legIndex, offset, homeX, homeZ, fill, battery, p)
    end
    return wps, ni, noff, sprayed, info, battery
end

-- Náhradní baterie, která se nabíjí jako první: ta, co už se nabíjí (slot), dokud není plná, jinak nejnabitější
-- z nenabitých. nil, když jsou všechny plné.
function SprayDroneRoute.getChargingSlot(spares, slot, capacity)
    if slot ~= nil and spares[slot] ~= nil and spares[slot] < capacity then
        return slot
    end
    local best = nil
    for k, charge in ipairs(spares) do
        if charge < capacity and (best == nil or charge > spares[best]) then
            best = k
        end
    end
    return best
end

-- Nejnabitější náhradní baterie: slot a nabití (s).
function SprayDroneRoute.getBestSpare(spares)
    local best, charge = nil, -1
    for k, c in ipairs(spares) do
        if c > charge then
            best, charge = k, c
        end
    end
    return best, math.max(charge, 0)
end

-- Odhad nabíjení náhradních baterií centrálou po dobu seconds (jedna nabíječka, jako SprayDroneStation.updatePower).
-- sim: {spares, slot, diesel, dieselUsed, noFuel}; pw: {capacity, chargeRate (s baterie za s), dieselPerSecond}.
function SprayDroneRoute.chargeSpares(sim, pw, seconds)
    while seconds > 0.001 do
        sim.slot = SprayDroneRoute.getChargingSlot(sim.spares, sim.slot, pw.capacity)
        if sim.slot == nil then
            return
        end
        if sim.diesel <= 0 then
            sim.noFuel = true
            return
        end
        local dt = math.min(seconds, (pw.capacity - sim.spares[sim.slot]) / pw.chargeRate, sim.diesel / pw.dieselPerSecond)
        sim.spares[sim.slot] = math.min(sim.spares[sim.slot] + dt * pw.chargeRate, pw.capacity)
        sim.diesel = math.max(sim.diesel - dt * pw.dieselPerSecond, 0)
        sim.dieselUsed = sim.dieselUsed + dt * pw.dieselPerSecond
        seconds = seconds - dt
    end
end

-- Čekání, než je některá náhradní baterie nabitá aspoň na pw.readyCharge; vrací sekundy, nebo nil, když dojde nafta.
function SprayDroneRoute.waitForReadySpare(sim, pw)
    local waited = 0
    while true do
        local _, charge = SprayDroneRoute.getBestSpare(sim.spares)
        if charge >= pw.readyCharge - 0.01 then
            return waited
        end
        if sim.noFuel or waited > 7200 then
            return nil
        end
        SprayDroneRoute.chargeSpares(sim, pw, 5)
        waited = waited + 5
    end
end

-- Všechny dávky s plnou nádrží (jen pro zobrazení trasy), baterie od aktuální a s výměnami jako na vleku. Každý leg
-- dostane batch = číslo dávky. Vrací legy, počet dávek, jestli zbylo něco nenaplánovaného, a info {time, maxEnergy,
-- batterySwaps, height, tooHigh, noPath, transits, firstOut, firstBack, transitLength} za všechny dávky (přelety a délky
-- tam / zpět u první dávky, nejvyšší spotřeba dávky, počet výměn baterie).
-- S p.power ({spares, slot, diesel, startFill, capacity, chargeRate, dieselPerSecond, readyCharge, swapTime, pumpRate,
-- minService}) simuluje i servis na vleku: plnění čerpadlem, výměnu za náhradní baterii nabitou aspoň na readyCharge,
-- čekání na nabití a spotřebu nafty; info pak má navíc serviceTime, waitTime, dieselUsed, noFuel (dávka čeká na
-- baterii, kterou už bez nafty nejde nabít: mise tam skončí) a fuelRunsOut (nafta dojde, než se nabije vše potřebné).
function SprayDroneRoute.splitIntoBatches(legs, homeX, homeZ, tankCapacity, battery, p)
    local drawLegs = {}
    local info = { time = 0, maxEnergy = 0, batterySwaps = 0, height = 0, tooHigh = false, transits = {}, firstOut = 0, firstBack = 0,
        transitLength = 0, serviceTime = 0, waitTime = 0, dieselUsed = 0, noFuel = false }
    local pw = p.power
    local sim = nil
    local refill = 0
    if pw ~= nil then
        local spares = {}
        for k, charge in ipairs(pw.spares) do
            spares[k] = charge
        end
        sim = { spares = spares, slot = pw.slot, diesel = pw.diesel, dieselUsed = 0, noFuel = false }
        refill = tankCapacity - pw.startFill
    end
    local i, off, batch = 1, 0, 0
    while i <= #legs and batch < 500 do
        local swapCharge, bestSlot = nil, nil
        if sim ~= nil then
            local best, charge = SprayDroneRoute.getBestSpare(sim.spares)
            bestSlot, swapCharge = best, math.max(charge, pw.readyCharge)
        end
        local wps, ni, noff, sprayed, batchInfo, startBattery = SprayDroneRoute.planBatchWithSwap(legs, i, off, homeX, homeZ, tankCapacity,
            battery, p, swapCharge)
        info.height = math.max(info.height, batchInfo.height)
        if wps == nil then
            info.tooHigh = batchInfo.tooHigh == true
            info.noPath = batchInfo.noPath
            break
        end
        local swapped = startBattery ~= battery
        if sim ~= nil then
            local service = math.max(refill / pw.pumpRate, batch > 0 and pw.minService or 0)
            if swapped then
                local wait = SprayDroneRoute.waitForReadySpare(sim, pw)
                if wait == nil then
                    info.noFuel = true
                    break
                end
                bestSlot = SprayDroneRoute.getBestSpare(sim.spares)
                startBattery = sim.spares[bestSlot]
                sim.spares[bestSlot] = battery
                -- plnění, výměna i nabíjení běží souběžně; čekáním je jen to, o co se servis kvůli nabití prodlouží
                info.waitTime = info.waitTime + math.max(wait - service, 0)
                SprayDroneRoute.chargeSpares(sim, pw, math.max(service - wait - pw.swapTime, 0))
                service = math.max(service, wait + pw.swapTime)
            else
                SprayDroneRoute.chargeSpares(sim, pw, service)
            end
            info.serviceTime = info.serviceTime + service
            SprayDroneRoute.chargeSpares(sim, pw, batchInfo.time)
            refill = math.min(sprayed * p.litersPerMeter, tankCapacity)
        end
        if swapped then
            info.batterySwaps = info.batterySwaps + 1
        end
        battery = startBattery - batchInfo.energy
        batch = batch + 1
        info.time = info.time + batchInfo.time
        info.maxEnergy = math.max(info.maxEnergy, batchInfo.energy)
        table.insert(info.transits, batchInfo.outPlan)
        table.insert(info.transits, batchInfo.backPlan)
        info.transitLength = info.transitLength + batchInfo.outPlan.length + batchInfo.backPlan.length
        if batch == 1 then
            info.firstOut, info.firstBack = batchInfo.outPlan.length, batchInfo.backPlan.length
        end
        for _, wp in ipairs(wps) do
            if wp.spray then
                table.insert(drawLegs, { x1 = wp.sx, z1 = wp.sz, x2 = wp.x, z2 = wp.z, batch = batch })
            end
        end
        i, off = ni, noff
    end
    if sim ~= nil then
        info.dieselUsed = sim.dieselUsed
        info.fuelRunsOut = sim.noFuel
    end
    return drawLegs, batch, i <= #legs, info
end
