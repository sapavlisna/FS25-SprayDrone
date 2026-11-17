-- Geometrie pro postřikový dron: pole pod bodem, řádky přes polygon pole (boustrophedon),
-- ořez dosahem, vynechání už ošetřených míst a rozdělení práce na dávky.
-- Všechno v rovině xz; výšky řeší až let (relativně k terénu).

SprayDroneRoute = {}

SprayDroneRoute.SAMPLE_STEP = 2
SprayDroneRoute.MIN_LEG_LENGTH = 2

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

function SprayDroneRoute.distanceToPolygon(poly, x, z)
    if SprayDroneRoute.isPointInPolygon(poly, x, z) then
        return 0
    end
    local best = math.huge
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
        best = math.min(best, MathUtil.vector2Length(x - px, z - pz))
        j = i
    end
    return best
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

local function legPoint(leg, offset)
    local t = leg.len > 0 and offset / leg.len or 0
    return leg.x1 + (leg.x2 - leg.x1) * t, leg.z1 + (leg.z2 - leg.z1) * t
end

-- Jedna dávka od (legIndex, offset): kolik zvládne nádrž (fill litrů) a baterie (battery s) včetně cesty
-- tam a zpět. Vrací waypointy {x, z, h, speed, spray, home, land}, index a offset, kde další dávka začne,
-- a délku postřiku. Waypointy s home=true se za letu přepočítají na aktuální polohu dronu na vleku.
-- p: workWidth, sprayHeight, transitHeight, cruiseSpeed, sprayingSpeed, climbSpeed, litersPerMeter, batteryReserve, restHeight
function SprayDroneRoute.planBatch(legs, legIndex, offset, homeX, homeZ, fill, battery, p)
    local climbToTransit = math.max(p.transitHeight - p.restHeight, 0) / p.climbSpeed
    local transitToSpray = math.max(p.transitHeight - p.sprayHeight, 0) / p.climbSpeed
    local budget = battery - p.batteryReserve

    local timeUsed = climbToTransit
    local curX, curZ = homeX, homeZ
    local atSprayHeight = false
    local sprayed = 0
    local wps = { { x = homeX, z = homeZ, h = p.transitHeight, speed = p.climbSpeed, home = true } }

    local function returnTime(x, z)
        return transitToSpray + MathUtil.vector2Length(x - homeX, z - homeZ) / p.cruiseSpeed + climbToTransit
    end

    local i, off = legIndex, offset
    while i <= #legs do
        local leg = legs[i]
        local sx, sz = legPoint(leg, off)
        local moveTime = MathUtil.vector2Length(sx - curX, sz - curZ) / p.cruiseSpeed
        if not atSprayHeight then
            moveTime = moveTime + transitToSpray
        end
        local remaining = leg.len - off
        local maxLen = math.min(remaining, fill / p.litersPerMeter)

        local function fits(len)
            local ex, ez = legPoint(leg, off + len)
            return timeUsed + moveTime + len / p.sprayingSpeed + returnTime(ex, ez) <= budget
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
            table.insert(wps, { x = sx, z = sz, h = p.transitHeight, speed = p.cruiseSpeed })
            table.insert(wps, { x = sx, z = sz, h = p.sprayHeight, speed = p.climbSpeed })
        else
            table.insert(wps, { x = sx, z = sz, h = p.sprayHeight, speed = p.cruiseSpeed })
        end
        local ex, ez = legPoint(leg, off + len)
        table.insert(wps, { x = ex, z = ez, sx = sx, sz = sz, h = p.sprayHeight, speed = p.sprayingSpeed, spray = true })

        timeUsed = timeUsed + moveTime + len / p.sprayingSpeed
        fill = fill - len * p.litersPerMeter
        sprayed = sprayed + len
        curX, curZ = ex, ez
        atSprayHeight = true

        if len < remaining - 0.01 then
            off = off + len
            break
        end
        i, off = i + 1, 0
    end

    if sprayed == 0 then
        return nil, legIndex, offset, 0
    end
    table.insert(wps, { x = curX, z = curZ, h = p.transitHeight, speed = p.climbSpeed })
    table.insert(wps, { x = homeX, z = homeZ, h = p.transitHeight, speed = p.cruiseSpeed, home = true })
    table.insert(wps, { x = homeX, z = homeZ, h = p.restHeight, speed = p.climbSpeed, home = true, land = true })
    return wps, i, off, sprayed
end

-- Všechny dávky s plnou nádrží a baterií (jen pro zobrazení trasy). Každý leg dostane batch = číslo dávky.
function SprayDroneRoute.splitIntoBatches(legs, homeX, homeZ, tankCapacity, battery, p)
    local drawLegs = {}
    local i, off, batch = 1, 0, 0
    while i <= #legs and batch < 500 do
        local wps, ni, noff = SprayDroneRoute.planBatch(legs, i, off, homeX, homeZ, tankCapacity, battery, p)
        if wps == nil then
            break
        end
        batch = batch + 1
        for _, wp in ipairs(wps) do
            if wp.spray then
                table.insert(drawLegs, { x1 = wp.sx, z1 = wp.sz, x2 = wp.x, z2 = wp.z, batch = batch })
            end
        end
        i, off = ni, noff
    end
    return drawLegs, batch, i <= #legs
end
