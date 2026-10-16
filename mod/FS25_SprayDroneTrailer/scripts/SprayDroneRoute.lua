-- Geometrie pro postřikový dron: pole pod bodem, řádky přes polygon pole (boustrophedon),
-- ořez dosahem, vynechání už ošetřených míst, výška přeletu nad překážkami a rozdělení práce na dávky.
-- Trasa je v rovině xz; výšky jsou relativně k terénu.

SprayDroneRoute = {}

SprayDroneRoute.SAMPLE_STEP = 2
SprayDroneRoute.MIN_LEG_LENGTH = 2

-- překážky: statické objekty (sloupy, ploty), stromy, budovy; terén a vozidla (vlastní vlek) ne
SprayDroneRoute.OBSTACLE_MASK = CollisionFlag.STATIC_OBJECT + CollisionFlag.TREE + CollisionFlag.BUILDING
SprayDroneRoute.OBSTACLE_STEP = 5
-- pás kolem dráhy: poloměr dronu (vrtule) + boční odstup, svislé paprsky nejvýš po LATERAL_STEP napříč
SprayDroneRoute.LATERAL_STEP = 1.2
SprayDroneRoute.OBSTACLE_SCAN_HEIGHT = 120
SprayDroneRoute.OBSTACLE_RAISE_STEP = 2
SprayDroneRoute.OBSTACLE_RAY_LIFT = 0.4
SprayDroneRoute.MAX_RAISE_ROUNDS = 15

-- dráha: zaoblení rohů obloukem (rychlost na oblouku sqrt(turnAcceleration * r)), výškový profil po sklonech
-- ascentSpeed / cruiseSpeed a climbSpeed / cruiseSpeed, takže svislá rychlost v cestovní nepřekročí limity
SprayDroneRoute.PROFILE_STEP = 2
SprayDroneRoute.ARC_STEP = math.rad(12)
SprayDroneRoute.ARC_MIN_RADIUS = 1
SprayDroneRoute.TRANSIT_MAX_RADIUS = 15
SprayDroneRoute.APPROACH_LENGTH = 8
SprayDroneRoute.TAKEOFF_LIFT = 2
SprayDroneRoute.LANDING_LIFT = 3
SprayDroneRoute.SLOPE_MARGIN = 0.9
SprayDroneRoute.SMOOTH_PASSES = 4
-- odbočení nad tento úhel: zastavit a otočit na místě (jako řízení letu)
SprayDroneRoute.TURN_STOP_ANGLE = math.rad(30)

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

-- Nejvyšší překážka v pásu šířky ±halfWidth napříč směrem (dirX, dirZ) v bodě (x, z): výška nad terénem a místo.
function SprayDroneRoute.getBandObstacle(x, z, dirX, dirZ, halfWidth)
    local n = math.max(math.ceil(halfWidth / SprayDroneRoute.LATERAL_STEP), 1)
    local sideX, sideZ = dirZ, -dirX
    local best, bx, bz = 0, x, z
    for i = -n, n do
        local off = halfWidth * i / n
        local px, pz = x + sideX * off, z + sideZ * off
        local h = SprayDroneRoute.getObstacleHeightAt(px, pz)
        if h > best then
            best, bx, bz = h, px, pz
        end
    end
    return best, bx, bz
end

-- Vodorovné paprsky v pásu ±halfWidth mezi body a -> b ({x, z, y} ve světě, y je výška dráhy): první zásah (x, z), nebo nil.
function SprayDroneRoute.getBandHit(a, b, halfWidth)
    local dx, dy, dz = b.x - a.x, b.y - a.y, b.z - a.z
    local d = math.sqrt(dx * dx + dy * dy + dz * dz)
    local hl = math.sqrt(dx * dx + dz * dz)
    if d < 0.01 or hl < 0.01 then
        return nil
    end
    local sideX, sideZ = dz / hl, -dx / hl
    local n = math.max(math.ceil(halfWidth / SprayDroneRoute.LATERAL_STEP), 1)
    for i = -n, n do
        local off = halfWidth * i / n
        local ax, az = a.x + sideX * off, a.z + sideZ * off
        local hit, dist = SprayDroneRoute.castRay(ax, a.y, az, dx / d, dy / d, dz / d, d)
        if hit then
            return ax + dx / d * dist, az + dz / d * dist
        end
    end
    return nil
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

-- Pole s nezoratelným ostrovem uprostřed (remízek, stavba, rybník) má celou hranici v jednom řetězci bodů jako
-- "klíčovou dírku": z vnější hranice vede tenký můstek k ostrovu, oběhne ho a vrátí se skoro stejnou cestou zpátky.
-- Pro bodové testy (isPointInPolygon) to funguje samo, ale offsetPolygon/úvratě by můstek braly jako skutečnou
-- hranu a táhly se podél něj k ostrovu a zpět (místo aby ostrov obkroužily samostatně, jako Courseplay). Funkce
-- most najde (dvojice bodů blíž než ISLAND_BRIDGE_EPS, ale ne sousední v řetězci) a ostrov oddělí od vnější hranice.
SprayDroneRoute.ISLAND_BRIDGE_EPS = 1.5

function SprayDroneRoute.splitIslands(poly)
    local main = {}
    for _, p in ipairs(poly) do
        table.insert(main, p)
    end
    local islands = {}
    for _ = 1, 50 do
        local n = #main
        local foundI, foundJ = nil, nil
        for i = 1, n do
            for j = i + 2, n do
                if not (i == 1 and j == n) then
                    local a, b = main[i], main[j]
                    if MathUtil.vector2Length(a.x - b.x, a.z - b.z) <= SprayDroneRoute.ISLAND_BRIDGE_EPS
                        and (foundJ == nil or (j - i) < (foundJ - foundI)) then
                        foundI, foundJ = i, j
                    end
                end
            end
        end
        if foundI == nil then
            break
        end
        local island = {}
        for k = foundI + 1, foundJ - 1 do
            table.insert(island, main[k])
        end
        if #island >= 3 then
            table.insert(islands, island)
        end
        local kept = {}
        for k = 1, foundI do
            table.insert(kept, main[k])
        end
        for k = foundJ + 1, n do
            table.insert(kept, main[k])
        end
        main = kept
    end
    return main, islands
end

-- {outer, islands}: vnější hranice bez můstků a seznam ostrovů (každý jako samostatný polygon), obojí z poly pole.
function SprayDroneRoute.getFieldShape(field)
    if field.sdtShape == nil then
        local outer, islands = SprayDroneRoute.splitIslands(SprayDroneRoute.getPolygon(field))
        field.sdtShape = { outer = outer, islands = islands }
    end
    return field.sdtShape
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

-- Smí se na místě stříkat? Jen pevné podmínky (pozemek farmy, pole, nezralá plodina, u herbicidu mapa s plevelem);
-- co už dron obletěl, drží vlastní paměť (coverage), stav pole (úroveň hnojení, plevel) se do trasy nepočítá.
function SprayDroneRoute.getIsWorkable(x, z, sprayType, farmlandId)
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

    if sprayType.isHerbicide then
        local weedSystem = g_currentMission.weedSystem
        return weedSystem ~= nil and weedSystem:getMapHasWeed()
    end
    return true
end

-- herbicid: dron stříká jen tam, kde plevel je (stavy 1-6, i neviditelné 1-2); spotřeba pruhu = plná dávka x podíl plochy
-- s plevelem, nejméně HERBICIDE_MIN_SHARE (trysky se neotevírají přesně po pixelech, okraje, rezerva)
SprayDroneRoute.HERBICIDE_MIN_SHARE = 0.2
SprayDroneRoute.WEED_FIRST_STATE = 1
SprayDroneRoute.WEED_LAST_STATE = 6

-- Násobek spotřeby herbicidu pro plochu s weedPixels pixely plevele z totalPixels; bez údajů (nil, 0 pixelů) plná dávka.
function SprayDroneRoute.getHerbicideFactor(weedPixels, totalPixels)
    if weedPixels == nil or totalPixels == nil or totalPixels <= 0 then
        return 1
    end
    local share = math.min(math.max(weedPixels / totalPixels, 0), 1)
    return math.max(share, SprayDroneRoute.HERBICIDE_MIN_SHARE)
end

-- Průměrný násobek spotřeby pro plán: buňky {weed, total} pole, každá s vlastním minimem (stejně jako pruhy za letu),
-- vážené počtem pixelů. Bez buněk plná dávka.
function SprayDroneRoute.getAverageHerbicideFactor(cells)
    local sum, weight = 0, 0
    for _, c in ipairs(cells) do
        if c.total ~= nil and c.total > 0 then
            sum = sum + SprayDroneRoute.getHerbicideFactor(c.weed, c.total) * c.total
            weight = weight + c.total
        end
    end
    if weight <= 0 then
        return 1
    end
    return sum / weight
end

-- Precision Farming: kolik stavů mapy (dusík, pH) odpovídá pevné dávce dronu litersPerHa. usageAt(n) = l/ha pro změnu o n
-- stavů (NitrogenMap:getFertilizerUsageByStateChange / PHMap:getLimeUsageByStateChange); vybere nejbližší n v 0..maxChange.
function SprayDroneRoute.pickStateChange(litersPerHa, usageAt, maxChange)
    if litersPerHa == nil or litersPerHa <= 0 or maxChange == nil or maxChange < 1 then
        return 0
    end
    local best, bestDiff = 0, litersPerHa
    for n = 1, maxChange do
        local usage = usageAt(n)
        if usage ~= nil and usage > 0 then
            local diff = math.abs(usage - litersPerHa)
            if diff < bestDiff then
                best, bestDiff = n, diff
            end
            if usage > litersPerHa then
                break
            end
        end
    end
    return best
end

-- Konec práce dronu, když jeho seznam legů je prázdný: reachable = legy celého pole v dosahu a signálu, total = legy celého
-- pole bez ořezu dosahem a signálem, otherFlying = druhý dron ještě letí. "wait" = zbytek má (nebo může mít) druhý dron,
-- "outOfReach" = zbylá část leží mimo dosah/signál (paměť se nechá, po přesunu vleku/tyče se pokračuje), "done" = hotovo.
function SprayDroneRoute.getEmptyLegsOutcome(reachable, total, otherFlying)
    if reachable > 0 or otherFlying then
        return "wait"
    end
    if total > 0 then
        return "outOfReach"
    end
    return "done"
end

---------------------------------------------------------------------------------------------------
-- paměť dronu, kde už postříkal: pro každé pole a druh postřiku intervaly po řádcích (řádek k = k-tý pruh od okraje pole
-- v šířce záběru, interval = souřadnice t podél řádku v metrech) a po úvratích (headlands[i] = intervaly oblouku s po
-- uzavřené smyčce úvratě i od jejího začátku); nezávislá na hustotních mapách pole. Záznam nese i počet úvratí hl, s nímž
-- vznikl: jiný počet ho zneplatní (řádky a smyčky by pak ležely jinde).

SprayDroneRoute.COVERAGE_PAD = 1
SprayDroneRoute.COVERAGE_MERGE_GAP = 0.5

-- Souřadnice řádků pole: směr podle nejdelší hrany, kolmice, nejmenší a největší posun kolmice.
function SprayDroneRoute.getFrame(field)
    local frame = field.sdtFrame
    if frame == nil then
        local poly = SprayDroneRoute.getPolygon(field)
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
        frame = { dirX = dirX, dirZ = dirZ, nX = nX, nZ = nZ, minN = minN, maxN = maxN }
        field.sdtFrame = frame
    end
    return frame
end

-- Záznam paměti pro pole platí jen pro stejný druh postřiku, šířku záběru a počet úvratí; jinak nil.
function SprayDroneRoute.getCoverage(all, fieldId, sprayTypeIndex, workWidth, headlands)
    local entry = all[fieldId]
    if entry ~= nil and entry.type == sprayTypeIndex and math.abs(entry.ww - workWidth) < 0.01 and entry.hl == (headlands or 0) then
        return entry
    end
    return nil
end

function SprayDroneRoute.isCovered(intervals, t)
    if intervals ~= nil then
        for _, iv in ipairs(intervals) do
            if t >= iv[1] and t <= iv[2] then
                return true
            end
        end
    end
    return false
end

-- Přidá interval [lo, hi] do seznamu a sloučí překryvy; vrací nový seznam.
local function insertInterval(intervals, lo, hi)
    intervals = intervals or {}
    table.insert(intervals, { lo, hi })
    table.sort(intervals, function(a, b) return a[1] < b[1] end)
    local merged = { intervals[1] }
    for i = 2, #intervals do
        local last = merged[#merged]
        if intervals[i][1] <= last[2] + SprayDroneRoute.COVERAGE_MERGE_GAP then
            last[2] = math.max(last[2], intervals[i][2])
        else
            table.insert(merged, intervals[i])
        end
    end
    return merged
end

local function addInterval(intervals, lo, hi)
    return insertInterval(intervals, lo - SprayDroneRoute.COVERAGE_PAD, hi + SprayDroneRoute.COVERAGE_PAD)
end

-- Uloží úsek (x1, z1) -> (x2, z2) jako oblouk na smyčce loop do map[i] (úvrať pole nebo ostrova).
local function storeLoopInterval(map, loop, i, x1, z1, x2, z2)
    local s1, s2 = SprayDroneRoute.projectOnLoop(loop, x1, z1), SprayDroneRoute.projectOnLoop(loop, x2, z2)
    if s1 > s2 then
        s1, s2 = s2, s1
    end
    local list = map[i]
    if s2 - s1 > loop.total * 0.5 then
        -- úsek přechází přes začátek smyčky: dva kusy u jejích konců
        list = addInterval(list, 0, s1)
        list = addInterval(list, s2, loop.total)
    else
        list = addInterval(list, s1, s2)
    end
    -- interval přesahující [0, total] se zrcadlí na druhý konec (smyčka je uzavřená)
    if list[1][1] < 0 then
        list = insertInterval(list, loop.total + list[1][1], loop.total)
    end
    if list[#list][2] > loop.total then
        list = insertInterval(list, 0, list[#list][2] - loop.total)
    end
    map[i] = list
end

-- Zapíše postříkaný úsek (x1, z1) -> (x2, z2) do paměti all (záznam pro jiný druh postřiku, záběr nebo počet úvratí se
-- přepíše). Úsek, jehož střed je blíž hranici ostrova než headlands záběrů (a blíž než vnější hranici pole), patří
-- úvrati floor(vzdálenost / záběr) + 1 kolem toho ostrova; jinak, blíž vnější hranici, úvrati pole; jinak řádku.
function SprayDroneRoute.markCovered(all, field, sprayTypeIndex, workWidth, headlands, x1, z1, x2, z2)
    headlands = headlands or 0
    local entry = SprayDroneRoute.getCoverage(all, field:getId(), sprayTypeIndex, workWidth, headlands)
    if entry == nil then
        entry = { type = sprayTypeIndex, ww = workWidth, hl = headlands, lines = {}, headlands = {}, islands = {} }
        all[field:getId()] = entry
    end
    local cx, cz = (x1 + x2) * 0.5, (z1 + z2) * 0.5
    if headlands > 0 then
        local shape = SprayDroneRoute.getFieldShape(field)
        local threshold = headlands * workWidth - SprayDroneRoute.HEADLAND_ROW_SLACK
        local outerDist = SprayDroneRoute.nearestBoundaryPoint(shape.outer, cx, cz)
        local islandIndex, islandDist = nil, math.huge
        for idx, island in ipairs(shape.islands) do
            local d = SprayDroneRoute.nearestBoundaryPoint(island, cx, cz)
            if d < islandDist then
                islandIndex, islandDist = idx, d
            end
        end
        if islandIndex ~= nil and islandDist < threshold and islandDist <= outerDist then
            local i = math.clamp(math.floor(islandDist / workWidth) + 1, 1, headlands)
            local loop = SprayDroneRoute.getIslandLoop(field, workWidth, islandIndex, i)
            if loop ~= nil then
                entry.islands[islandIndex] = entry.islands[islandIndex] or {}
                storeLoopInterval(entry.islands[islandIndex], loop, i, x1, z1, x2, z2)
                return
            end
        elseif outerDist < threshold then
            local i = math.clamp(math.floor(outerDist / workWidth) + 1, 1, headlands)
            local loop = SprayDroneRoute.getHeadlandLoop(field, workWidth, i)
            if loop ~= nil then
                storeLoopInterval(entry.headlands, loop, i, x1, z1, x2, z2)
                return
            end
        end
    end
    local f = SprayDroneRoute.getFrame(field)
    local k = math.floor((cx * f.nX + cz * f.nZ - f.minN) / workWidth)
    local t1, t2 = x1 * f.dirX + z1 * f.dirZ, x2 * f.dirX + z2 * f.dirZ
    if t1 > t2 then
        t1, t2 = t2, t1
    end
    entry.lines[k] = addInterval(entry.lines[k], t1, t2)
end

local function encodeIntervalMap(map)
    local parts = {}
    for k, intervals in pairs(map) do
        local nums = {}
        for _, iv in ipairs(intervals) do
            table.insert(nums, string.format("%.1f,%.1f", iv[1], iv[2]))
        end
        table.insert(parts, k .. ":" .. table.concat(nums, ","))
    end
    return table.concat(parts, "|")
end

local function decodeIntervalMap(text)
    local map = {}
    for line in string.gmatch(text, "[^|]+") do
        local k, nums = string.match(line, "^(%-?%d+):(.*)$")
        if k ~= nil then
            local intervals, first = {}, nil
            for num in string.gmatch(nums, "[^,]+") do
                if first == nil then
                    first = tonumber(num)
                else
                    table.insert(intervals, { first, tonumber(num) })
                    first = nil
                end
            end
            map[tonumber(k)] = intervals
        end
    end
    return map
end

-- Paměť úvratí ostrovů: map[islandIndex] = intervalMap (stejný tvar jako entry.headlands, jen per ostrov). Ostrovy
-- oddělené "`", uvnitř "islandIndex~intervalMap".
local function encodeIslandsMap(islands)
    local parts = {}
    for islandIndex, levelMap in pairs(islands) do
        local encoded = encodeIntervalMap(levelMap)
        if encoded ~= "" then
            table.insert(parts, islandIndex .. "~" .. encoded)
        end
    end
    return table.concat(parts, "`")
end

local function decodeIslandsMap(text)
    local islands = {}
    for chunk in string.gmatch(text or "", "[^`]+") do
        local idxText, mapText = string.match(chunk, "^(%d+)~(.*)$")
        if idxText ~= nil then
            islands[tonumber(idxText)] = decodeIntervalMap(mapText)
        end
    end
    return islands
end

-- Text paměti: záznamy oddělené ";", záznam = pole/druh/záběr/počet úvratí/řádky/úvratě pole/úvratě ostrovů.
function SprayDroneRoute.encodeCoverage(all)
    local chunks = {}
    for fieldId, entry in pairs(all) do
        local lines = encodeIntervalMap(entry.lines)
        local heads = encodeIntervalMap(entry.headlands or {})
        local islands = encodeIslandsMap(entry.islands or {})
        if lines ~= "" or heads ~= "" or islands ~= "" then
            table.insert(chunks, string.format("%d/%d/%.2f/%d/%s/%s/%s", fieldId, entry.type, entry.ww, entry.hl or 0,
                lines, heads, islands))
        end
    end
    return table.concat(chunks, ";")
end

function SprayDroneRoute.decodeCoverage(text)
    local all = {}
    for chunk in string.gmatch(text or "", "[^;]+") do
        local fieldId, typ, ww, hl, lineText, headText, islandText = string.match(chunk,
            "^(%d+)/(%d+)/([%d%.]+)/(%d+)/([^/]*)/([^/]*)/?([^/]*)$")
        if fieldId ~= nil then
            all[tonumber(fieldId)] = { type = tonumber(typ), ww = tonumber(ww), hl = tonumber(hl),
                lines = decodeIntervalMap(lineText), headlands = decodeIntervalMap(headText),
                islands = decodeIslandsMap(islandText) }
        end
    end
    return all
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

---------------------------------------------------------------------------------------------------
-- úvratě: uzavřené smyčky uvnitř pole ve vzdálenosti (i - 0,5) záběru od hranice (i = 1 je nejblíž hranici)

-- mitr delší než tolik násobků odstupu (jen u vrcholů, kde se hranice láme od pole) se nahradí obloukem
SprayDroneRoute.HEADLAND_MITRE_LIMIT = 2
SprayDroneRoute.HEADLAND_ARC_STEP = math.rad(30)
-- části smyčky blíž hranici než tento podíl odstupu (nebo mimo pole) se vyřadí
SprayDroneRoute.HEADLAND_MIN_DISTANCE = 0.9
-- úsek řádku smí mít střed o tolik blíž hranici než headlands záběrů (okraj běhu se rozšiřuje o půl kroku vzorkování)
SprayDroneRoute.HEADLAND_ROW_SLACK = 1

-- Polygon poly ({x, z}) posunutý dovnitř o d: každá hrana se posune o d ke středu, sousední se protnou (mitr).
-- U vrcholů, kde se hranice lomí směrem od pole, by mitr vyrazil dlouhý výběžek: nad HEADLAND_MITRE_LIMIT se
-- vrchol nahradí obloukem o poloměru d (body zůstanou přesně d od vrcholu). Vrací seznam vrcholů {x, z}, prázdný
-- pro nepoužitelný polygon. Samopřekrytí u malých nebo tenkých polí se neřeší tady, ale vyřazením částí smyčky
-- (getHeadlandLoop se dívá na vzdálenost k hranici).
function SprayDroneRoute.offsetPolygon(poly, d)
    local pts = {}
    for _, p in ipairs(poly) do
        local last = pts[#pts]
        if last == nil or MathUtil.vector2Length(p.x - last.x, p.z - last.z) > 0.05 then
            table.insert(pts, { x = p.x, z = p.z })
        end
    end
    if #pts > 1 and MathUtil.vector2Length(pts[1].x - pts[#pts].x, pts[1].z - pts[#pts].z) <= 0.05 then
        table.remove(pts)
    end
    local n = #pts
    if n < 3 then
        return {}
    end
    local area = 0
    for i = 1, n do
        local a, b = pts[i], pts[i % n + 1]
        area = area + a.x * b.z - b.x * a.z
    end
    local orient = area > 0 and 1 or -1

    -- směr a vnitřní normála každé hrany i (pts[i] -> pts[i + 1])
    local ux, uz, nx, nz = {}, {}, {}, {}
    for i = 1, n do
        local a, b = pts[i], pts[i % n + 1]
        local l = MathUtil.vector2Length(b.x - a.x, b.z - a.z)
        ux[i], uz[i] = (b.x - a.x) / l, (b.z - a.z) / l
        nx[i], nz[i] = -uz[i] * orient, ux[i] * orient
    end

    local out = {}
    for i = 1, n do
        local e1 = (i - 2) % n + 1
        local p = pts[i]
        local dot = nx[e1] * nx[i] + nz[e1] * nz[i]
        local cross = ux[e1] * uz[i] - uz[e1] * ux[i]
        local reflex = cross * orient < 0
        local denom = 1 + dot
        local mitre = denom > 0.02 and 1 / math.sqrt(denom * 0.5) or math.huge
        if denom > 0.02 and (not reflex or mitre <= SprayDroneRoute.HEADLAND_MITRE_LIMIT) then
            table.insert(out, { x = p.x + (nx[e1] + nx[i]) / denom * d, z = p.z + (nz[e1] + nz[i]) / denom * d })
        else
            local a1, a2 = math.atan2(nz[e1], nx[e1]), math.atan2(nz[i], nx[i])
            local delta = a2 - a1
            while delta > math.pi do
                delta = delta - 2 * math.pi
            end
            while delta < -math.pi do
                delta = delta + 2 * math.pi
            end
            local m = math.max(math.ceil(math.abs(delta) / SprayDroneRoute.HEADLAND_ARC_STEP), 1)
            for k = 0, m do
                local a = a1 + delta * k / m
                table.insert(out, { x = p.x + math.cos(a) * d, z = p.z + math.sin(a) * d })
            end
        end
    end
    return out
end

-- Smyčka úvratě i pole: {pts, cum, total, d}, cum[j] = délka oblouku od začátku smyčky k vrcholu j (cum[#pts + 1] = total),
-- smyčka končí hranou zpět k prvnímu vrcholu. Závisí jen na polygonu pole, záběru a i, takže souřadnice oblouku s
-- v paměti dronu platí napříč přepočty trasy. nil, když se smyčka nedá udělat.
function SprayDroneRoute.getHeadlandLoop(field, workWidth, i)
    field.sdtLoops = field.sdtLoops or {}
    local key = string.format("%.3f:%d", workWidth, i)
    local loop = field.sdtLoops[key]
    if loop == nil then
        loop = false
        local d = (i - 0.5) * workWidth
        local pts = SprayDroneRoute.offsetPolygon(SprayDroneRoute.getFieldShape(field).outer, d)
        if #pts >= 3 then
            local cum = { 0 }
            for j = 1, #pts do
                local a, b = pts[j], pts[j % #pts + 1]
                cum[j + 1] = cum[j] + MathUtil.vector2Length(b.x - a.x, b.z - a.z)
            end
            loop = { pts = pts, cum = cum, total = cum[#pts + 1], d = d }
        end
        field.sdtLoops[key] = loop
    end
    return loop or nil
end

-- Oblouk s nejbližšího bodu smyčky k (x, z).
function SprayDroneRoute.projectOnLoop(loop, x, z)
    local best, bestS = math.huge, 0
    local pts = loop.pts
    for j = 1, #pts do
        local a, b = pts[j], pts[j % #pts + 1]
        local ex, ez = b.x - a.x, b.z - a.z
        local len2 = ex * ex + ez * ez
        local t = len2 > 0 and math.clamp(((x - a.x) * ex + (z - a.z) * ez) / len2, 0, 1) or 0
        local d = MathUtil.vector2Length(x - (a.x + ex * t), z - (a.z + ez * t))
        if d < best then
            best, bestS = d, loop.cum[j] + t * (loop.cum[j + 1] - loop.cum[j])
        end
    end
    return bestS
end

-- Legy jedné úvratě: hrany smyčky od vrcholu nejblíž domovu, směrem, kde konec první hrany leží blíž domovu. Části
-- mimo pole nebo blíž hranici než HEADLAND_MIN_DISTANCE · d se vynechají, ořez kruhem dosahu, výběr workable/covered
-- (covered = intervaly oblouku s z paměti) jako u řádků. Hrany na sebe navazují v jednom bodě.
function SprayDroneRoute.buildHeadlandLegs(field, homeX, homeZ, range, workWidth, i, sprayType, covered)
    local loop = SprayDroneRoute.getHeadlandLoop(field, workWidth, i)
    if loop == nil then
        return {}
    end
    local poly = SprayDroneRoute.getPolygon(field)
    local pts, cum = loop.pts, loop.cum
    local m = #pts
    local minDistance = SprayDroneRoute.HEADLAND_MIN_DISTANCE * loop.d
    local farmlandId = field:getId()

    local start, bestDist = 1, math.huge
    for j = 1, m do
        local d = MathUtil.vector2Length(pts[j].x - homeX, pts[j].z - homeZ)
        if d < bestDist then
            start, bestDist = j, d
        end
    end
    local nextV, prevV = pts[start % m + 1], pts[(start - 2) % m + 1]
    local forward = MathUtil.vector2Length(nextV.x - homeX, nextV.z - homeZ) <= MathUtil.vector2Length(prevV.x - homeX, prevV.z - homeZ)

    local legs = {}
    for k = 0, m - 1 do
        local e = forward and (start - 1 + k) % m + 1 or (start - 2 - k) % m + 1
        local a, b = pts[e], pts[e % m + 1]
        local len = cum[e + 1] - cum[e]
        local c1, c2 = clipToCircle(a.x, a.z, b.x, b.z, homeX, homeZ, range)
        if c1 ~= nil then
            local ax, az = a.x + (b.x - a.x) * c1, a.z + (b.z - a.z) * c1
            local bx, bz = a.x + (b.x - a.x) * c2, a.z + (b.z - a.z) * c2
            local parts = {}
            SprayDroneRoute.appendParts(parts, ax, az, bx, bz, function(px, pz, t)
                if SprayDroneRoute.isCovered(covered, cum[e] + (c1 + (c2 - c1) * t) * len) then
                    return false
                end
                return SprayDroneRoute.isPointInPolygon(poly, px, pz)
                    and SprayDroneRoute.nearestBoundaryPoint(poly, px, pz) >= minDistance
                    and SprayDroneRoute.getIsWorkable(px, pz, sprayType, farmlandId)
            end)
            if forward then
                for _, leg in ipairs(parts) do
                    table.insert(legs, leg)
                end
            else
                for j = #parts, 1, -1 do
                    local leg = parts[j]
                    table.insert(legs, { x1 = leg.x2, z1 = leg.z2, x2 = leg.x1, z2 = leg.z1, len = leg.len })
                end
            end
        end
    end
    return legs
end

-- Smyčka úvratě i kolem ostrova islandIndex (remízek, stavba uprostřed pole): stejně jako getHeadlandLoop, jen
-- posunutá ven z ostrova (offsetPolygon se zápornou vzdáleností - ostrov je v polygonu veden opačně než vnější
-- hranice pole, takže "dovnitř" by pro něj znamenalo do ostrova, ne od něj).
function SprayDroneRoute.getIslandLoop(field, workWidth, islandIndex, i)
    field.sdtIslandLoops = field.sdtIslandLoops or {}
    local key = string.format("%d:%.3f:%d", islandIndex, workWidth, i)
    local loop = field.sdtIslandLoops[key]
    if loop == nil then
        loop = false
        local island = SprayDroneRoute.getFieldShape(field).islands[islandIndex]
        if island ~= nil then
            local d = (i - 0.5) * workWidth
            local pts = SprayDroneRoute.offsetPolygon(island, -d)
            if #pts >= 3 then
                local cum = { 0 }
                for j = 1, #pts do
                    local a, b = pts[j], pts[j % #pts + 1]
                    cum[j + 1] = cum[j] + MathUtil.vector2Length(b.x - a.x, b.z - a.z)
                end
                loop = { pts = pts, cum = cum, total = cum[#pts + 1], d = d }
            end
        end
        field.sdtIslandLoops[key] = loop
    end
    return loop or nil
end

-- Legy úvratě i kolem ostrova islandIndex: stejná logika jako buildHeadlandLegs (vrchol nejblíž domovu, výběr
-- workable/covered, ořez dosahem), jen odstup od hranice se měří k samotnému ostrovu, ne k celému poli.
function SprayDroneRoute.buildIslandLegs(field, homeX, homeZ, range, workWidth, islandIndex, i, sprayType, covered)
    local loop = SprayDroneRoute.getIslandLoop(field, workWidth, islandIndex, i)
    if loop == nil then
        return {}
    end
    local poly = SprayDroneRoute.getPolygon(field)
    local island = SprayDroneRoute.getFieldShape(field).islands[islandIndex]
    local pts, cum = loop.pts, loop.cum
    local m = #pts
    local minDistance = SprayDroneRoute.HEADLAND_MIN_DISTANCE * loop.d
    local farmlandId = field:getId()

    local start, bestDist = 1, math.huge
    for j = 1, m do
        local d = MathUtil.vector2Length(pts[j].x - homeX, pts[j].z - homeZ)
        if d < bestDist then
            start, bestDist = j, d
        end
    end
    local nextV, prevV = pts[start % m + 1], pts[(start - 2) % m + 1]
    local forward = MathUtil.vector2Length(nextV.x - homeX, nextV.z - homeZ) <= MathUtil.vector2Length(prevV.x - homeX, prevV.z - homeZ)

    local legs = {}
    for k = 0, m - 1 do
        local e = forward and (start - 1 + k) % m + 1 or (start - 2 - k) % m + 1
        local a, b = pts[e], pts[e % m + 1]
        local len = cum[e + 1] - cum[e]
        local c1, c2 = clipToCircle(a.x, a.z, b.x, b.z, homeX, homeZ, range)
        if c1 ~= nil then
            local ax, az = a.x + (b.x - a.x) * c1, a.z + (b.z - a.z) * c1
            local bx, bz = a.x + (b.x - a.x) * c2, a.z + (b.z - a.z) * c2
            local parts = {}
            SprayDroneRoute.appendParts(parts, ax, az, bx, bz, function(px, pz, t)
                if SprayDroneRoute.isCovered(covered, cum[e] + (c1 + (c2 - c1) * t) * len) then
                    return false
                end
                return SprayDroneRoute.isPointInPolygon(poly, px, pz)
                    and SprayDroneRoute.nearestBoundaryPoint(island, px, pz) >= minDistance
                    and SprayDroneRoute.getIsWorkable(px, pz, sprayType, farmlandId)
            end)
            if forward then
                for _, leg in ipairs(parts) do
                    table.insert(legs, leg)
                end
            else
                for j = #parts, 1, -1 do
                    local leg = parts[j]
                    table.insert(legs, { x1 = leg.x2, z1 = leg.z2, x2 = leg.x1, z2 = leg.z1, len = leg.len })
                end
            end
        end
    end
    return legs
end

-- Seřazené legy k postřiku: {x1, z1, x2, z2, len}. Řádky jdou rovnoběžně s nejdelší hranou pole (boustrophedon od
-- strany bližší domovu, rozteč workWidth). S headlands > 0 se řádky omezí na vnitřek (střed dál od hranice než
-- headlands záběrů) a po obvodu přibude headlands úvratí (buildHeadlandLegs): headlandFirst ~= 0 = úvratě 1..n
-- (vnější první) a pak řádky, headlandFirst == 0 = řádky a pak úvratě n..1 (vnější poslední).
-- coverage je záznam paměti dronu pro toto pole (getCoverage), nebo nil.
function SprayDroneRoute.buildLegs(field, homeX, homeZ, range, workWidth, sprayType, coverage, headlands, headlandFirst)
    local poly = SprayDroneRoute.getPolygon(field)
    if #poly < 3 or sprayType == nil then
        return {}
    end
    headlands = headlands or 0

    local f = SprayDroneRoute.getFrame(field)
    local dirX, dirZ, nX, nZ, minN, maxN = f.dirX, f.dirZ, f.nX, f.nZ, f.minN, f.maxN

    local homeN = homeX * nX + homeZ * nZ
    local offsets = {}
    local s = minN + workWidth * 0.5
    while s < maxN do
        table.insert(offsets, { s = s, k = #offsets })
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
    local rowLegs = {}
    local forward = true
    for _, lineOffset in ipairs(offsets) do
        local off = lineOffset.s
        local covered = coverage ~= nil and coverage.lines[lineOffset.k] or nil
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
                SprayDroneRoute.appendNeededParts(lineLegs, ax, az, bx, bz, sprayType, farmlandId, covered, dirX, dirZ,
                    poly, headlands * workWidth)
            end
        end

        if #lineLegs > 0 then
            if forward then
                for _, leg in ipairs(lineLegs) do
                    table.insert(rowLegs, leg)
                end
            else
                for i = #lineLegs, 1, -1 do
                    local leg = lineLegs[i]
                    table.insert(rowLegs, { x1 = leg.x2, z1 = leg.z2, x2 = leg.x1, z2 = leg.z1, len = leg.len })
                end
            end
            forward = not forward
        end
    end
    if headlands == 0 then
        return rowLegs
    end

    local islands = SprayDroneRoute.getFieldShape(field).islands
    local loops = {}
    for i = 1, headlands do
        loops[i] = SprayDroneRoute.buildHeadlandLegs(field, homeX, homeZ, range, workWidth, i, sprayType,
            coverage ~= nil and coverage.headlands ~= nil and coverage.headlands[i] or nil)
        for islandIndex = 1, #islands do
            local islandCovered = coverage ~= nil and coverage.islands ~= nil
                and coverage.islands[islandIndex] ~= nil and coverage.islands[islandIndex][i] or nil
            local islandLegs = SprayDroneRoute.buildIslandLegs(field, homeX, homeZ, range, workWidth, islandIndex, i,
                sprayType, islandCovered)
            for _, leg in ipairs(islandLegs) do
                table.insert(loops[i], leg)
            end
        end
    end
    local legs = {}
    local function append(list)
        for _, leg in ipairs(list) do
            table.insert(legs, leg)
        end
    end
    if headlandFirst ~= 0 then
        for i = 1, headlands do
            append(loops[i])
        end
        append(rowLegs)
    else
        append(rowLegs)
        for i = headlands, 1, -1 do
            append(loops[i])
        end
    end
    return legs
end

-- Rozdělí úsek a -> b na části, kde needsAt(x, z, t) (t = 0..1 po úseku) říká, že se tam má stříkat (vzorky po
-- SAMPLE_STEP m po středu pruhu).
function SprayDroneRoute.appendParts(target, ax, az, bx, bz, needsAt)
    local len = MathUtil.vector2Length(bx - ax, bz - az)
    if len < SprayDroneRoute.MIN_LEG_LENGTH then
        return
    end
    local step = SprayDroneRoute.SAMPLE_STEP
    local n = math.max(math.floor(len / step), 1)
    local runStart = nil
    for i = 0, n do
        local t = i / n
        local px, pz = ax + (bx - ax) * t, az + (bz - az) * t
        local needs = needsAt(px, pz, t) and not SprayDroneRoute.isReserved(px, pz) and SprayDroneRoute.isInSignal(px, pz)
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

-- Části řádku, kde se smí stříkat a dron tam ještě nebyl; s minBoundary > 0 (řádky uvnitř úvratí) jen ty, jejichž
-- střed je od hranice polygonu poly aspoň minBoundary daleko.
function SprayDroneRoute.appendNeededParts(target, ax, az, bx, bz, sprayType, farmlandId, covered, dirX, dirZ, poly, minBoundary)
    SprayDroneRoute.appendParts(target, ax, az, bx, bz, function(px, pz)
        if minBoundary ~= nil and minBoundary > 0 and SprayDroneRoute.nearestBoundaryPoint(poly, px, pz) < minBoundary then
            return false
        end
        return not SprayDroneRoute.isCovered(covered, px * dirX + pz * dirZ)
            and SprayDroneRoute.getIsWorkable(px, pz, sprayType, farmlandId)
    end)
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

SprayDroneRoute.CORRIDOR_INSET = 3

-- Lomový vrchol posunutý o CORRIDOR_INSET dovnitř plochy (po ose úhlu), aby zaoblená dráha kolem něj nevyšla ven;
-- když by posunutý bod ležel mimo plochu, zůstane vrchol na místě.
function SprayDroneRoute.insetNode(c, prev, cur, nxt, orient)
    local function inward(a, b)
        local dx, dz = b.x - a.x, b.z - a.z
        local l = math.sqrt(dx * dx + dz * dz)
        if l < 1e-6 then
            return 0, 0
        end
        return -dz / l * orient, dx / l * orient
    end
    local n1x, n1z = inward(prev, cur)
    local n2x, n2z = inward(cur, nxt)
    local bx, bz = n1x + n2x, n1z + n2z
    local bl = math.sqrt(bx * bx + bz * bz)
    if bl > 1e-6 then
        local x, z = cur.x + bx / bl * SprayDroneRoute.CORRIDOR_INSET, cur.z + bz / bl * SprayDroneRoute.CORRIDOR_INSET
        if SprayDroneRoute.isInCorridor(c, x, z) and SprayDroneRoute.isCorridorSegmentFree(c, cur.x, cur.z, x, z) then
            return { x = x, z = z }
        end
    end
    return { x = cur.x, z = cur.z }
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
                table.insert(c.nodes, SprayDroneRoute.insetNode(c, prev, cur, nxt, orient))
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

---------------------------------------------------------------------------------------------------
-- dráha letu: waypointy {x, z, h, speed, spray, home, land, sx, sz}, h je výška nad terénem. Rohy přeletů
-- a přejezdů mezi řádky jsou zaoblené, stoupání a klesání jde za letu po profilu; řízení letu (SprayDroneStation)
-- i odhady času a baterie (pathCost) používají stejné pravidlo průjezdu bodem (junctionSpeed).

SprayDroneRoute.VERTICAL_PHASE_SPEED = 0.5
SprayDroneRoute.HOVER_PHASE_SPEED = 2

local function legPoint(leg, offset)
    local t = leg.len > 0 and offset / leg.len or 0
    return leg.x1 + (leg.x2 - leg.x1) * t, leg.z1 + (leg.z2 - leg.z1) * t
end

local function legDir(leg)
    local len = MathUtil.vector2Length(leg.x2 - leg.x1, leg.z2 - leg.z1)
    if len < 0.001 then
        return 1, 0
    end
    return (leg.x2 - leg.x1) / len, (leg.z2 - leg.z1) / len
end

-- Rychlost, kterou dron smí projet bodem b mezi úseky a -> b a b -> c ({x, z, h}): rovně plnou (min z obou
-- úseků), se zlomem pomaleji, pravý úhel a víc zastavit; odbočení nad TURN_STOP_ANGLE = zastavit a otočit na místě.
function SprayDroneRoute.junctionSpeed(a, b, c, v1, v2)
    local x1, z1, y1 = b.x - a.x, b.z - a.z, b.h - a.h
    local x2, z2, y2 = c.x - b.x, c.z - b.z, c.h - b.h
    local l1 = math.sqrt(x1 * x1 + z1 * z1 + y1 * y1)
    local l2 = math.sqrt(x2 * x2 + z2 * z2 + y2 * y2)
    if l1 < 0.01 or l2 < 0.01 then
        return 0
    end
    local h1, h2 = math.sqrt(x1 * x1 + z1 * z1), math.sqrt(x2 * x2 + z2 * z2)
    if h1 > 0.5 and h2 > 0.5 and (x1 * x2 + z1 * z2) / (h1 * h2) < math.cos(SprayDroneRoute.TURN_STOP_ANGLE) then
        return 0
    end
    local cos = (x1 * x2 + z1 * z2 + y1 * y2) / (l1 * l2)
    return math.min(v1, v2) * math.clamp((cos - 0.3) / 0.7, 0, 1)
end

-- Čas a spotřeba baterie po bodech pts ({x, z, h, speed, spray, land}; pts[1] je start): rychlost v bodech podle
-- junctionSpeed, rozjezd i brzdění acceleration (dopředný a zpětný průchod), start vStart, konec vEnd. Otočení nad
-- TURN_STOP_ANGLE na místě, fáze (stoupání, klesání, vznášení) a hmotnost náplně jako SprayDroneStation.drainBattery;
-- na úsecích spray náplň ubývá. Vrací čas, spotřebu, náplň na konci a yaw.
function SprayDroneRoute.pathCost(pts, p, fill, vStart, vEnd, yaw)
    local n = #pts
    if n < 2 then
        return 0, 0, fill, yaw
    end
    local acc = p.acceleration
    local v, len = {}, {}
    v[1] = math.min(vStart or 0, pts[2].speed)
    for k = 2, n - 1 do
        v[k] = SprayDroneRoute.junctionSpeed(pts[k - 1], pts[k], pts[k + 1], pts[k].speed, pts[k + 1].speed)
    end
    v[n] = math.min(vEnd or 0, pts[n].speed)
    for k = 2, n do
        local a, b = pts[k - 1], pts[k]
        local dx, dz, dh = b.x - a.x, b.z - a.z, b.h - a.h
        len[k] = math.sqrt(dx * dx + dz * dz + dh * dh)
        v[k] = math.min(v[k], math.sqrt(v[k - 1] * v[k - 1] + 2 * acc * len[k]))
    end
    for k = n - 1, 1, -1 do
        v[k] = math.min(v[k], math.sqrt(v[k + 1] * v[k + 1] + 2 * acc * len[k + 1]))
    end
    local t, e = 0, 0
    for k = 2, n do
        local a, b = pts[k - 1], pts[k]
        local hl = MathUtil.vector2Length(b.x - a.x, b.z - a.z)
        local dh = b.h - a.h
        if hl > 0.5 then
            local heading = MathUtil.getYRotationFromDirection(b.x - a.x, b.z - a.z)
            if yaw ~= nil and math.abs(MathUtil.getAngleDifference(heading, yaw)) > SprayDroneRoute.TURN_STOP_ANGLE then
                local turn = SprayDroneRoute.turnTime(yaw, heading, p)
                t, e = t + turn, e + turn * SprayDroneRoute.drainFactor(p, fill, p.hoverFactor)
            end
            yaw = heading
        end
        local st
        if b.land then
            st = SprayDroneRoute.landingTime(-dh, p)
        else
            st = SprayDroneRoute.moveTime(len[k], b.speed, acc, v[k - 1], v[k])
        end
        local segFill = fill
        if b.spray then
            local used = math.min(hl * p.litersPerMeter, math.max(fill, 0))
            segFill = fill - used * 0.5
            fill = fill - used
        end
        local phase = 1
        if st > 0 then
            if dh / st > SprayDroneRoute.VERTICAL_PHASE_SPEED then
                phase = p.climbFactor
            elseif dh / st < -SprayDroneRoute.VERTICAL_PHASE_SPEED then
                phase = p.descentFactor
            elseif hl / st < SprayDroneRoute.HOVER_PHASE_SPEED then
                phase = p.hoverFactor
            end
        end
        t, e = t + st, e + st * SprayDroneRoute.drainFactor(p, segFill, phase)
    end
    return t, e, fill, yaw
end

-- Oblouk v rohu c mezi směry d1 a d2 ({x, z} jednotkové): tečné body ve vzdálenosti t od rohu, poloměr r.
function SprayDroneRoute.makeArc(c, d1, d2, t, r, theta)
    local sign = d1[1] * d2[2] - d1[2] * d2[1] > 0 and 1 or -1
    local t1x, t1z = c.x - d1[1] * t, c.z - d1[2] * t
    local cx, cz = t1x - d1[2] * r * sign, t1z + d1[1] * r * sign
    local a0 = math.atan2(t1z - cz, t1x - cx)
    local m = math.max(math.ceil(theta / SprayDroneRoute.ARC_STEP), 1)
    local arc = {}
    for i = 0, m do
        local a = a0 + sign * theta * i / m
        table.insert(arc, { x = cx + math.cos(a) * r, z = cz + math.sin(a) * r })
    end
    return arc
end

-- Zaoblí vnitřní rohy lomené čáry pts ({x, z}) oblouky o poloměru nejvýš rDesired; tečná délka se dělí se sousedním
-- rohem (u krajního úseku celá), takže koncové body zůstanou. check(oblouk) může oblouk odmítnout (zkusí se menší).
-- Vrací body {x, z, seg, seg2, speed} (seg = úsek původní čáry, na oblouku seg2 = další; speed = strop na úseku
-- do bodu, sqrt(aLat * r) na oblouku) a počet ostrých rohů.
function SprayDroneRoute.roundCorners(pts, rDesired, aLat, check)
    local n = #pts
    local out = {}
    local sharp = 0
    local function add(x, z, seg, seg2, speed)
        local last = out[#out]
        if last ~= nil and MathUtil.vector2Length(x - last.x, z - last.z) < 0.05 then
            return
        end
        table.insert(out, { x = x, z = z, seg = seg, seg2 = seg2 or seg, speed = speed })
    end
    local L, D = {}, {}
    for k = 1, n - 1 do
        local dx, dz = pts[k + 1].x - pts[k].x, pts[k + 1].z - pts[k].z
        local l = math.sqrt(dx * dx + dz * dz)
        L[k] = l
        D[k] = l > 1e-6 and { dx / l, dz / l } or { 0, 0 }
    end
    add(pts[1].x, pts[1].z, 1)
    for k = 2, n - 1 do
        local d1, d2 = D[k - 1], D[k]
        local theta = math.acos(math.clamp(d1[1] * d2[1] + d1[2] * d2[2], -1, 1))
        local done = theta <= math.rad(1)
        if not done and theta < math.rad(170) and L[k - 1] > 0.01 and L[k] > 0.01 then
            local tt = math.tan(theta * 0.5)
            local t = math.min(rDesired * tt, L[k - 1] * (k - 1 >= 2 and 0.5 or 1), L[k] * (k + 1 <= n - 1 and 0.5 or 1))
            for _ = 1, 3 do
                local r = t / tt
                if r < SprayDroneRoute.ARC_MIN_RADIUS then
                    break
                end
                local arc = SprayDroneRoute.makeArc(pts[k], d1, d2, t, r, theta)
                if check == nil or check(arc) then
                    local speed = math.sqrt(aLat * r)
                    for i, q in ipairs(arc) do
                        add(q.x, q.z, k - 1, k, i > 1 and speed or nil)
                    end
                    done = true
                    break
                end
                t = t * 0.5
            end
        end
        if not done then
            sharp = sharp + 1
            add(pts[k].x, pts[k].z, k - 1, k)
        end
    end
    add(pts[n].x, pts[n].z, n - 1)
    return out, sharp
end

-- Obálka kuželů: každá hodnota values[i] platí v s[i] a klesá dopředu sklonem kAfter a dozadu sklonem kBefore.
local function coneEnvelope(values, s, kBefore, kAfter)
    local n = #values
    local out = {}
    local run = -math.huge
    for i = 1, n do
        if i > 1 then
            run = run - kAfter * (s[i] - s[i - 1])
        end
        run = math.max(run, values[i])
        out[i] = run
    end
    run = -math.huge
    for i = n, 1, -1 do
        if i < n then
            run = run - kBefore * (s[i + 1] - s[i])
        end
        run = math.max(run, values[i])
        out[i] = math.max(out[i], run)
    end
    return out
end

function SprayDroneRoute.getSlopes(p)
    return p.ascentSpeed / p.cruiseSpeed * SprayDroneRoute.SLOPE_MARGIN, p.climbSpeed / p.cruiseSpeed * SprayDroneRoute.SLOPE_MARGIN
end

-- Výška profilu přeletu ve vzdálenosti sv z L: cestovní H, od startu (hStart) a ke konci (hEnd) po sklonech.
local function rampHeight(sv, L, H, hStart, hEnd, kUp, kDown)
    return math.min(math.max(H, hStart - kDown * sv, hEnd - kUp * (L - sv)), hStart + kUp * sv, hEnd + kDown * (L - sv))
end

-- Zaoblená dráha rozdělená na kroky po PROFILE_STEP: S[i] = {x, z, y (terén), seg, seg2, speed}, s[i] = vzdálenost po dráze.
-- Vrací S, s a délku dráhy.
local function sampleTransitPath(dense)
    local S = {}
    for k, q in ipairs(dense) do
        if k > 1 then
            local a = dense[k - 1]
            local m = math.ceil(MathUtil.vector2Length(q.x - a.x, q.z - a.z) / SprayDroneRoute.PROFILE_STEP)
            local seg2 = a.seg2 == q.seg2 and q.seg2 or q.seg
            for i = 1, m - 1 do
                local f = i / m
                table.insert(S, { x = a.x + (q.x - a.x) * f, z = a.z + (q.z - a.z) * f, seg = q.seg, seg2 = seg2, speed = q.speed })
            end
        end
        table.insert(S, { x = q.x, z = q.z, seg = q.seg, seg2 = q.seg2, speed = q.speed })
    end
    local n = #S
    local s = { 0 }
    for i = 2, n do
        s[i] = s[i - 1] + MathUtil.vector2Length(S[i].x - S[i - 1].x, S[i].z - S[i - 1].z)
    end
    for i = 1, n do
        S[i].y = getTerrainHeightAtWorldPos(g_terrainNode, S[i].x, 0, S[i].z)
    end
    return S, s, s[n]
end

-- Svislé paprsky po OBSTACLE_STEP v pásu kolem dráhy: req[i] = výška, kterou body kroků vyžadují nad překážkou (+ odstup),
-- obstacles = nalezené překážky, scan = indexy kroků, ve kterých se paprsky vypouštěly.
local function scanTransitObstacles(S, s, p)
    local n = #S
    local halfWidth = p.droneRadius + p.sideClearance
    local req, obstacles, scan = {}, {}, {}
    local nextS = 0
    for i = 1, n do
        req[i] = 0
        if s[i] >= nextS - SprayDroneRoute.PROFILE_STEP * 0.5 or i == n then
            table.insert(scan, i)
            nextS = s[i] + SprayDroneRoute.OBSTACLE_STEP
        end
    end
    for _, i in ipairs(scan) do
        local a, b = S[math.max(i - 1, 1)], S[math.min(i + 1, n)]
        local dl = MathUtil.vector2Length(b.x - a.x, b.z - a.z)
        if dl > 0.01 then
            local h, ox, oz = SprayDroneRoute.getBandObstacle(S[i].x, S[i].z, (b.x - a.x) / dl, (b.z - a.z) / dl, halfWidth)
            if h > 0 then
                req[i] = h + p.obstacleClearance
                table.insert(obstacles, { x = ox, z = oz, h = h })
            end
        end
    end
    return req, obstacles, scan
end

-- Výšky profilu h[i]: základ (base) a obálka požadavků req, bez údolí; pak se profil proletí vodorovnými paprsky a co svislé
-- minuly, zvedne ho (mění req a obstacles). Vrací h, nejvyšší výšku a tooHigh (překážka nad maxTransitHeight).
local function liftTransitProfile(S, s, req, scan, obstacles, base, cruise, p)
    local n = #S
    local kUp, kDown = SprayDroneRoute.getSlopes(p)
    local halfWidth = p.droneRadius + p.sideClearance
    local limit = p.maxTransitHeight + p.obstacleClearance
    local lift = SprayDroneRoute.OBSTACLE_RAY_LIFT
    local tooHigh = false
    local h
    local blocked = {}
    for round = 1, 2 * SprayDroneRoute.MAX_RAISE_ROUNDS do
        local env = coneEnvelope(req, s, kUp, kDown)
        h = {}
        for i = 1, n do
            h[i] = math.max(base[i], env[i])
        end
        -- bez údolí: za překážkou u startu (nebo před ní u cíle) dron neklesá, když pak stejně stoupá na cestovní výšku
        local left, right = {}, {}
        for i = 1, n do
            left[i] = math.max(left[i - 1] or -math.huge, h[i])
        end
        for i = n, 1, -1 do
            right[i] = math.max(right[i + 1] or -math.huge, h[i])
        end
        for i = 1, n do
            h[i] = math.max(h[i], math.min(left[i], right[i], cruise[i]))
        end
        local raised = false
        for j = 1, #scan - 1 do
            local i1, i2 = scan[j], scan[j + 1]
            local hx, hz = SprayDroneRoute.getBandHit({ x = S[i1].x, z = S[i1].z, y = S[i1].y + h[i1] + lift },
                { x = S[i2].x, z = S[i2].z, y = S[i2].y + h[i2] + lift }, halfWidth)
            if hx ~= nil then
                local raise = math.max(h[i1], h[i2]) + SprayDroneRoute.OBSTACLE_RAISE_STEP
                if round == 1 then
                    table.insert(obstacles, { x = hx, z = hz, h = (h[i1] + h[i2]) * 0.5 + lift })
                end
                blocked[i1] = math.max(blocked[i1] or 0, h[i1] + lift)
                blocked[i2] = math.max(blocked[i2] or 0, h[i2] + lift)
                if raise > limit then
                    tooHigh = true
                else
                    req[i1], req[i2] = math.max(req[i1], raise), math.max(req[i2], raise)
                    raised = true
                end
            end
        end
        if not raised then
            -- paprsky už projdou: nad tím, co zasáhly, ještě odstup jako u svislých paprsků (překážka + obstacleClearance)
            local changed = false
            for i, hb in pairs(blocked) do
                local need = math.min(math.max(hb, h[i]) + p.obstacleClearance, limit)
                if need > req[i] + 0.01 then
                    req[i] = need
                    changed = true
                end
            end
            blocked = {}
            if not changed then
                break
            end
        end
    end
    local height = 0
    for i = 1, n do
        height = math.max(height, h[i])
    end
    return h, height, tooHigh or height > p.maxTransitHeight + 0.01
end

-- Waypointy přeletu z kroků S a jejich výšek h: kroky na přímce ve stejné rychlosti se slučují. Vrací waypointy, body
-- {x, z} a výšky ponechaných kroků.
local function buildTransitWaypoints(S, h, p, outbound, startH, endH)
    local n = #S
    local wps, points, heights = {}, { { x = S[1].x, z = S[1].z } }, {}
    local function push(wp)
        table.insert(wps, wp)
    end
    if outbound then
        push({ x = S[1].x, z = S[1].z, h = h[1], speed = p.ascentSpeed, home = true })
    elseif h[1] > startH + 0.05 then
        push({ x = S[1].x, z = S[1].z, h = h[1], speed = p.ascentSpeed })
    end
    local kept = 1
    for i = 2, n do
        local speed = S[i].speed ~= nil and math.min(p.cruiseSpeed, S[i].speed) or p.cruiseSpeed
        local keep = i == n
        if not keep then
            local a, b, c = S[kept], S[i], S[i + 1]
            local ux, uz, uh = b.x - a.x, b.z - a.z, h[i] - h[kept]
            local wx, wz, wh = c.x - b.x, c.z - b.z, h[i + 1] - h[i]
            local lu, lw = math.sqrt(ux * ux + uz * uz + uh * uh), math.sqrt(wx * wx + wz * wz + wh * wh)
            local nextSpeed = S[i + 1].speed ~= nil and math.min(p.cruiseSpeed, S[i + 1].speed) or p.cruiseSpeed
            keep = lu < 1e-6 or lw < 1e-6 or (ux * wx + uz * wz + uh * wh) / (lu * lw) < 0.99995 or nextSpeed ~= speed
        end
        if keep then
            push({ x = S[i].x, z = S[i].z, h = h[i], speed = speed })
            table.insert(points, { x = S[i].x, z = S[i].z })
            table.insert(heights, h[i])
            kept = i
        end
    end
    if outbound then
        if h[n] > endH + 0.05 then
            push({ x = S[n].x, z = S[n].z, h = endH, speed = p.climbSpeed })
        end
    else
        if #wps == 0 then
            push({ x = S[n].x, z = S[n].z, h = h[n], speed = p.cruiseSpeed })
        end
        wps[#wps].home = true
        push({ x = S[n].x, z = S[n].z, h = p.restHeight, speed = p.climbSpeed, home = true, land = true })
    end
    return wps, points, heights
end

-- Přelet po lomené čáře pts ({x, z}): zaoblené rohy (check může oblouk odmítnout, např. mimo letovou plochu),
-- výškový profil a překážky. Profil začíná v startH, končí v endH, mezi tím úsek k letí nejméně minHeight a nad
-- nejvyšší překážkou úseku + obstacleClearance; změny výšky jdou po sklonech (stoupání před vyšším úsekem, klesání
-- za nižším). Překážky se hledají svislými paprsky po OBSTACLE_STEP v pásu droneRadius + sideClearance kolem
-- skutečné (zaoblené) dráhy; překážka blízko startu nebo cíle zvedne profil kuželem (sklonem, v nejhorším svislé
-- stoupání na místě). Pak se profil proletí vodorovnými paprsky a co svislé minuly, zvedne ho. outbound: první
-- waypoint je svislý vzlet nad vlekem (home), jinak se končí přistáním na vleku.
-- Vrací {wps, points, heights, mapPoints, height, tooHigh, length, obstacles, corners}.
function SprayDroneRoute.buildTransit(pts, minHeight, startH, endH, p, outbound, check)
    local rDesired = math.min(p.cruiseSpeed * p.cruiseSpeed / p.turnAcceleration, SprayDroneRoute.TRANSIT_MAX_RADIUS)
    local dense = SprayDroneRoute.roundCorners(pts, rDesired, p.turnAcceleration, check)
    local S, s, L = sampleTransitPath(dense)
    local n = #S
    local req, obstacles, scan = scanTransitObstacles(S, s, p)

    local segH = {}
    for k = 1, math.max(#pts - 1, 1) do
        segH[k] = minHeight
    end
    for i = 1, n do
        segH[S[i].seg] = math.max(segH[S[i].seg], req[i])
        segH[S[i].seg2] = math.max(segH[S[i].seg2], req[i])
    end
    local kUp, kDown = SprayDroneRoute.getSlopes(p)
    local cruise = {}
    for i = 1, n do
        cruise[i] = math.max(segH[S[i].seg], segH[S[i].seg2])
    end
    cruise = coneEnvelope(cruise, s, kUp, kDown)
    local base = {}
    for i = 1, n do
        base[i] = rampHeight(s[i], L, cruise[i], startH, endH, kUp, kDown)
    end
    for _ = 1, SprayDroneRoute.SMOOTH_PASSES do
        local prev = base[1]
        for i = 2, n - 1 do
            local cur = base[i]
            base[i] = (prev + 2 * cur + base[i + 1]) * 0.25
            prev = cur
        end
    end

    local h, height, tooHigh = liftTransitProfile(S, s, req, scan, obstacles, base, cruise, p)
    local wps, points, heights = buildTransitWaypoints(S, h, p, outbound, startH, endH)
    local mapPoints = {}
    for _, q in ipairs(dense) do
        table.insert(mapPoints, { x = q.x, z = q.z })
    end
    return { wps = wps, points = points, heights = heights, mapPoints = mapPoints, height = height, tooHigh = tooHigh,
        length = L, obstacles = obstacles, corners = pts }
end

-- Hrubý přelet po lomené čáře pts ({x, z}) pro odhad baterie: bez zaoblení (ostré rohy = zastavit a otočit, tedy
-- opatrněji), z h0 svisle na hStart, pak profil jako buildTransit bez překážek (cestovní H), na konci hEnd a s land
-- přistání na p.restHeight. Vrací body pro pathCost (pts[1] je start).
function SprayDroneRoute.coarseTransit(pts, h0, hStart, hEnd, H, p, land)
    local kUp, kDown = SprayDroneRoute.getSlopes(p)
    local s = { 0 }
    for k = 2, #pts do
        s[k] = s[k - 1] + MathUtil.vector2Length(pts[k].x - pts[k - 1].x, pts[k].z - pts[k - 1].z)
    end
    local L = s[#pts]
    local list = { { x = pts[1].x, z = pts[1].z, h = h0 } }
    if math.abs(hStart - h0) > 0.05 then
        table.insert(list, { x = pts[1].x, z = pts[1].z, h = hStart, speed = hStart > h0 and p.ascentSpeed or p.climbSpeed })
    end
    local marks = {}
    for k = 2, #pts do
        table.insert(marks, s[k])
    end
    for _, m in ipairs({ (H - hStart) / kUp, L - (H - hEnd) / kDown, (hStart - H) / kDown, L - (hEnd - H) / kUp,
        (hEnd + kDown * L - hStart) / (kUp + kDown), (hStart - hEnd + kUp * L) / (kUp + kDown) }) do
        if m > 0.05 and m < L - 0.05 then
            table.insert(marks, m)
        end
    end
    table.sort(marks)
    local k = 2
    for _, m in ipairs(marks) do
        while k < #pts and s[k] < m - 1e-6 do
            k = k + 1
        end
        local a, b = pts[k - 1], pts[k]
        local seg = s[k] - s[k - 1]
        local f = seg > 1e-6 and math.clamp((m - s[k - 1]) / seg, 0, 1) or 1
        local x, z = a.x + (b.x - a.x) * f, a.z + (b.z - a.z) * f
        local last = list[#list]
        if MathUtil.vector2Length(x - last.x, z - last.z) > 0.05 then
            table.insert(list, { x = x, z = z, h = rampHeight(m, L, H, hStart, hEnd, kUp, kDown), speed = p.cruiseSpeed })
        end
    end
    local last = list[#list]
    if math.abs(last.h - hEnd) > 0.05 then
        table.insert(list, { x = last.x, z = last.z, h = hEnd, speed = hEnd > last.h and p.ascentSpeed or p.climbSpeed })
    end
    if land then
        table.insert(list, { x = last.x, z = last.z, h = p.restHeight, speed = p.climbSpeed, land = true })
    end
    return list
end

-- Další leg začíná v místě konce předchozího (roh smyčky úvratě): mezi nimi není přejezd, dron projede rohem
SprayDroneRoute.CONTINUE_DISTANCE = 0.5
SprayDroneRoute.HOP_MIN_GAP = 6
SprayDroneRoute.HOP_VERTICAL_SPEED = 0.5

-- Přejezd z konce řádku (a, směr ad) na začátek dalšího (b, směr bd) ve výšce postřiku: pokračování po přímce
-- rovně, jinak smyčka s oblouky (za konec řádku a před začátek dalšího o půl záběru, řádek se nezkracuje).
-- isClear(body) může smyčku odmítnout (překážka za okrajem pole): pak ostrý přejezd jako dřív (zastavit, otočit,
-- přeletět, otočit). Vrací waypointy bez startu, poslední je b; prázdný seznam, když b leží v a (legy na sebe navazují).
-- Funguje mezi libovolnými dvěma legy, tedy i z řádku na úvrať a mezi úvratěmi.
function SprayDroneRoute.rowTurn(ax, az, adx, adz, bx, bz, bdx, bdz, p, isClear)
    local h, v = p.sprayHeight, p.cruiseSpeed
    local fx, fz = bx - ax, bz - az
    if fx * fx + fz * fz < SprayDroneRoute.CONTINUE_DISTANCE * SprayDroneRoute.CONTINUE_DISTANCE then
        return {}
    end
    if fx * adx + fz * adz > 0 and math.abs(fx * adz - fz * adx) < 0.5 and adx * bdx + adz * bdz > 0.99 then
        -- pokračování po přímce: když uprostřed řádku leží remízek nebo stavba (řádek se tam rozdělil), dron se nad překážkou
        -- svisle zvedne, přeletí ji a na druhé straně svisle klesne; bez toho by tam zabrzdila až pojistka za letu
        if p.getHopHeight ~= nil and fx * fx + fz * fz > SprayDroneRoute.HOP_MIN_GAP * SprayDroneRoute.HOP_MIN_GAP then
            local hop = p.getHopHeight(ax, az, bx, bz)
            if hop ~= nil and hop > h then
                return {
                    { x = ax, z = az, h = hop, speed = SprayDroneRoute.HOP_VERTICAL_SPEED },
                    { x = bx, z = bz, h = hop, speed = v },
                    { x = bx, z = bz, h = h, speed = SprayDroneRoute.HOP_VERTICAL_SPEED }
                }
            end
        end
        return { { x = bx, z = bz, h = h, speed = v } }
    end
    local e = p.workWidth * 0.5
    local pts = { { x = ax, z = az }, { x = ax + adx * e, z = az + adz * e }, { x = bx - bdx * e, z = bz - bdz * e }, { x = bx, z = bz } }
    local rDesired = math.min(p.sprayingSpeed * p.sprayingSpeed / p.turnAcceleration, SprayDroneRoute.TRANSIT_MAX_RADIUS)
    local dense, sharp = SprayDroneRoute.roundCorners(pts, rDesired, p.turnAcceleration)
    if sharp == 0 and (isClear == nil or isClear(dense)) then
        local wps = {}
        for k = 2, #dense do
            local q = dense[k]
            table.insert(wps, { x = q.x, z = q.z, h = h, speed = q.speed ~= nil and math.min(v, q.speed) or v })
        end
        return wps
    end
    return { { x = bx, z = bz, h = h, speed = v } }
end

-- Horní odhad energie na návrat z bodu na řádku (x, z) na vlek: s plochou přes začátek nebo konec řádku (cesty z nich jsou
-- v paměti), jinak přímo. hOut = výška přeletu, rowV = rychlost v bodě, endFill = náplň při návratu.
local function estimateBatchReturn(p, homeX, homeZ, hOut, rowV, x, z, dx, dz, legYaw, leg, endFill)
    local sprayH = p.sprayHeight
    local routes = {}
    if p.getHomePath ~= nil then
        for _, q in ipairs({ { leg.x1, leg.z1 }, { leg.x2, leg.z2 } }) do
            local path = p.getHomePath(q[1], q[2])
            if path ~= nil then
                local pts = { { x = x, z = z } }
                for _, pt in ipairs(path) do
                    table.insert(pts, pt)
                end
                table.insert(routes, pts)
            end
        end
    end
    if #routes == 0 then
        local e = SprayDroneRoute.APPROACH_LENGTH
        table.insert(routes, { { x = x, z = z }, { x = x + dx * e, z = z + dz * e }, { x = homeX, z = homeZ } })
    end
    local best = math.huge
    for _, pts in ipairs(routes) do
        local list = SprayDroneRoute.coarseTransit(pts, sprayH, sprayH, p.restHeight + SprayDroneRoute.LANDING_LIFT, hOut, p, true)
        local _, e = SprayDroneRoute.pathCost(list, p, endFill, rowV, 0, legYaw)
        best = math.min(best, e)
    end
    return best
end

-- Jedna dávka od (legIndex, offset): kolik zvládne nádrž (fill litrů) a baterie (battery = sekundy vodorovného
-- letu s plnou nádrží) včetně cesty tam a zpět. Vrací waypointy {x, z, h, speed, spray, home, land}, index a offset,
-- kde další dávka začne, délku postřiku a info {time, energy, height, tooHigh, outPlan, backPlan, turns}. Waypointy
-- s home=true se za letu přepočítají na aktuální polohu dronu na vleku. Čas a spotřeba se počítají po skutečné dráze
-- (pathCost: zaoblení, profil výšky, rozjezd a brzdění, otáčení na místě, fáze letu a hmotnost náplně).
-- p: workWidth, sprayHeight, transitHeight, cruiseSpeed, sprayingSpeed, climbSpeed, ascentSpeed, acceleration,
-- turnAcceleration, yawSpeed, litersPerMeter, batteryReserve, restHeight, homeYaw, droneMass, fullMass, massPerLiter,
-- hoverFactor, climbFactor, descentFactor,
-- getTransit(x, z, outbound, dirX, dirZ) -> přelet (buildTransit) mezi vlekem a bodem s řádkem ve směru dir, nebo nil
-- a důvod, getHomePath(x, z) -> body cesty na vlek letovou plochou (jen s plochou), isTurnClear(body) -> přejezd volný
function SprayDroneRoute.planBatch(legs, legIndex, offset, homeX, homeZ, fill, battery, p)
    local budget = battery - p.batteryReserve
    if legIndex > #legs then
        return nil, legIndex, offset, 0, { time = 0, height = p.transitHeight }
    end

    local startFill = fill
    local firstX, firstZ = legPoint(legs[legIndex], offset)
    local fdx, fdz = legDir(legs[legIndex])
    local outPlan, noPath = p.getTransit(firstX, firstZ, true, fdx, fdz)
    if outPlan == nil then
        return nil, legIndex, offset, 0, { time = 0, height = p.transitHeight, noPath = noPath }
    end
    local hOut = outPlan.height
    if outPlan.tooHigh then
        return nil, legIndex, offset, 0, { time = 0, height = hOut, tooHigh = true }
    end

    local sprayH, sprayV = p.sprayHeight, p.sprayingSpeed
    local rowV = math.min(sprayV, math.sqrt(p.turnAcceleration * math.max(p.workWidth * 0.5, SprayDroneRoute.ARC_MIN_RADIUS)))
    local home = { x = homeX, z = homeZ, h = p.restHeight }
    local function speedInto(prev, cur, dx, dz, nextSpeed)
        return SprayDroneRoute.junctionSpeed(prev, cur, { x = cur.x + dx, z = cur.z + dz, h = cur.h }, cur.speed, nextSpeed)
    end

    local wps = {}
    local seq = { home }
    for _, wp in ipairs(outPlan.wps) do
        table.insert(wps, wp)
        table.insert(seq, wp)
    end
    local vIn = speedInto(seq[#seq - 1], seq[#seq], fdx, fdz, sprayV)
    local _, energyUsed, _, yaw = SprayDroneRoute.pathCost(seq, p, fill, 0, vIn, p.homeYaw)

    local curX, curZ, curDX, curDZ = firstX, firstZ, fdx, fdz
    local sprayed = 0
    local turns = {}
    local first = true
    local i, off = legIndex, offset
    while i <= #legs do
        local leg = legs[i]
        local sx, sz = legPoint(leg, off)
        local dx, dz = legDir(leg)
        local legYaw = MathUtil.getYRotationFromDirection(dx, dz)
        local trans = {}
        local transE = 0
        local vS = vIn
        local fillHere = fill
        if not first then
            trans = SprayDroneRoute.rowTurn(curX, curZ, curDX, curDZ, sx, sz, dx, dz, p, p.isTurnClear)
            local cur = { x = curX, z = curZ, h = sprayH, speed = sprayV }
            if #trans == 0 then
                -- navazující leg (roh úvratě): rychlost průjezdu rohem, otočení na místě nad TURN_STOP_ANGLE
                vS = SprayDroneRoute.junctionSpeed({ x = curX - curDX, z = curZ - curDZ, h = sprayH }, cur,
                    { x = curX + dx, z = curZ + dz, h = sprayH }, sprayV, sprayV)
                if yaw ~= nil and math.abs(MathUtil.getAngleDifference(legYaw, yaw)) > SprayDroneRoute.TURN_STOP_ANGLE then
                    transE = SprayDroneRoute.turnTime(yaw, legYaw, p) * SprayDroneRoute.drainFactor(p, fill, p.hoverFactor)
                end
            else
                local seqT = { cur }
                for _, wp in ipairs(trans) do
                    table.insert(seqT, wp)
                end
                local vA = SprayDroneRoute.junctionSpeed({ x = curX - curDX, z = curZ - curDZ, h = sprayH }, cur, trans[1], sprayV, trans[1].speed)
                vS = speedInto(seqT[#seqT - 1], seqT[#seqT], dx, dz, sprayV)
                _, transE = SprayDroneRoute.pathCost(seqT, p, fill, vA, vS, yaw)
            end
        end
        local remaining = leg.len - off
        local maxLen = math.min(remaining, fill / p.litersPerMeter)

        local function sprayEnergy(len)
            local ex, ez = legPoint(leg, off + len)
            local _, e = SprayDroneRoute.pathCost({ { x = sx, z = sz, h = sprayH },
                { x = ex, z = ez, h = sprayH, speed = sprayV, spray = true } }, p, fillHere, vS, rowV, legYaw)
            return e
        end
        local function fits(len)
            local ex, ez = legPoint(leg, off + len)
            return energyUsed + transE + sprayEnergy(len)
                + estimateBatchReturn(p, homeX, homeZ, hOut, rowV, ex, ez, dx, dz, legYaw, leg, fill - len * p.litersPerMeter) <= budget
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

        if #trans > 1 then
            local turn = { { x = curX, z = curZ } }
            for _, wp in ipairs(trans) do
                table.insert(turn, { x = wp.x, z = wp.z })
            end
            table.insert(turns, turn)
        end
        for _, wp in ipairs(trans) do
            table.insert(wps, wp)
        end
        local ex, ez = legPoint(leg, off + len)
        table.insert(wps, { x = ex, z = ez, sx = sx, sz = sz, h = sprayH, speed = sprayV, spray = true })
        energyUsed = energyUsed + transE + sprayEnergy(len)
        fill = fill - len * p.litersPerMeter
        sprayed = sprayed + len
        curX, curZ, curDX, curDZ = ex, ez, dx, dz
        yaw = legYaw
        first = false

        if len < remaining - 0.01 then
            off = off + len
            break
        end
        i, off = i + 1, 0
    end

    if sprayed == 0 then
        return nil, legIndex, offset, 0, { time = 0, height = hOut }
    end
    local backPlan, backNoPath = p.getTransit(curX, curZ, false, curDX, curDZ)
    if backPlan == nil then
        return nil, legIndex, offset, 0, { time = 0, height = hOut, noPath = backNoPath }
    end
    if backPlan.tooHigh then
        return nil, legIndex, offset, 0, { time = 0, height = backPlan.height, tooHigh = true }
    end
    for _, wp in ipairs(backPlan.wps) do
        table.insert(wps, wp)
    end
    local full = { home }
    for _, wp in ipairs(wps) do
        table.insert(full, wp)
    end
    local time, energy = SprayDroneRoute.pathCost(full, p, startFill, 0, 0, p.homeYaw)
    return wps, i, off, sprayed, { time = time, energy = energy, height = math.max(hOut, backPlan.height), outPlan = outPlan,
        backPlan = backPlan, turns = turns }
end

-- Odhad spotřeby na návrat z bodu (x, z) ve výšce h0 rychlostí v0 po body path (od (x, z) po vlek) ve výšce H
-- a přistání s náplní fill (hrubý přelet, jako kontrola baterie za letu).
function SprayDroneRoute.returnEnergy(path, h0, v0, yaw, H, p, fill)
    local list = SprayDroneRoute.coarseTransit(path, h0, h0, p.restHeight + SprayDroneRoute.LANDING_LIFT, H, p, true)
    local _, e = SprayDroneRoute.pathCost(list, p, fill, v0, 0, yaw)
    return e
end

-- Dosah z energie plné baterie: nejdelší přímý přelet, kdy let tam s plnou nádrží (vzlet, stoupání na H, klesání na
-- výšku postřiku) a zpět s prázdnou (stoupání, přelet, přistání) i s rezervou vystačí na baterii. Zaokrouhleno dolů
-- na 10 m, nejvýš maxRange.
function SprayDroneRoute.getBatteryRange(p, H, tankFill, maxRange)
    local function energy(d)
        local out = SprayDroneRoute.coarseTransit({ { x = 0, z = 0 }, { x = 0, z = d } }, p.restHeight,
            p.restHeight + SprayDroneRoute.TAKEOFF_LIFT, p.sprayHeight, H, p, false)
        local _, eOut = SprayDroneRoute.pathCost(out, p, tankFill, 0, 0, 0)
        local back = SprayDroneRoute.coarseTransit({ { x = 0, z = d }, { x = 0, z = 0 } }, p.sprayHeight, p.sprayHeight,
            p.restHeight + SprayDroneRoute.LANDING_LIFT, H, p, true)
        local _, eBack = SprayDroneRoute.pathCost(back, p, 0, 0, 0, 0)
        return eOut + eBack + p.batteryReserve
    end
    if energy(maxRange) <= p.batteryCapacity then
        return maxRange
    end
    local lo, hi = 0, maxRange
    for _ = 1, 24 do
        local mid = (lo + hi) * 0.5
        if energy(mid) <= p.batteryCapacity then
            lo = mid
        else
            hi = mid
        end
    end
    return math.floor(lo / 10) * 10
end

SprayDroneRoute.OBSTACLE_MARK_CELL = 12

-- Pro zobrazení: překážky z přeletů dávky (po buňkách OBSTACLE_MARK_CELL m nejvyšší) a přejezdy mezi řádky.
function SprayDroneRoute.collectRouteShapes(info, batchInfo, batch)
    info.obstacles = info.obstacles or {}
    info.obstacleCells = info.obstacleCells or {}
    info.turns = info.turns or {}
    local cell = SprayDroneRoute.OBSTACLE_MARK_CELL
    for _, plan in ipairs({ batchInfo.outPlan, batchInfo.backPlan }) do
        for _, o in ipairs(plan.obstacles or {}) do
            local key = string.format("%d:%d", math.floor(o.x / cell), math.floor(o.z / cell))
            local known = info.obstacleCells[key]
            if known == nil then
                known = { x = o.x, z = o.z, h = o.h }
                info.obstacleCells[key] = known
                table.insert(info.obstacles, known)
            elseif o.h > known.h then
                known.x, known.z, known.h = o.x, o.z, o.h
            end
        end
    end
    for _, turn in ipairs(batchInfo.turns or {}) do
        table.insert(info.turns, { points = turn, batch = batch })
    end
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

-- Odhad nabíjení baterií v nabíječce po dobu seconds: všechny nenabité najednou, nafta úměrně jejich počtu (jako
-- SprayDroneStation.updatePower). sim: {spares, diesel, dieselUsed, noFuel, pumpStarved}; pw: {capacity, chargeRate (s baterie
-- za s, na jednu), dieselPerSecond (na jednu nabíjenou), pumpShare, pumpLoad}. pumping = běží čerpadlo: baterie dostanou jen
-- pw.pumpShare výkonu (i nafty) a čerpadlo pálí pw.pumpLoad * dieselPerSecond; bez nafty čerpadlo stojí (sim.pumpStarved).
function SprayDroneRoute.chargeSpares(sim, pw, seconds, pumping)
    local factor = pumping and (pw.pumpShare or 1) or 1
    local pumpBurn = pumping and (pw.pumpLoad or 0) * pw.dieselPerSecond or 0
    while seconds > 0.001 do
        local charging, dt = 0, seconds
        for _, charge in ipairs(sim.spares) do
            if charge < pw.capacity then
                charging = charging + 1
                dt = math.min(dt, (pw.capacity - charge) / (pw.chargeRate * factor))
            end
        end
        if charging == 0 and pumpBurn <= 0 then
            return
        end
        if sim.diesel <= 0 then
            if charging > 0 then
                sim.noFuel = true
            end
            if pumping then
                sim.pumpStarved = true
            end
            return
        end
        local burn = charging * factor * pw.dieselPerSecond + pumpBurn
        dt = math.min(dt, sim.diesel / burn)
        for k, charge in ipairs(sim.spares) do
            if charge < pw.capacity then
                local charged = charge + dt * pw.chargeRate * factor
                sim.spares[k] = charged > pw.capacity - 1e-6 and pw.capacity or charged
            end
        end
        sim.diesel = math.max(sim.diesel - dt * burn, 0)
        sim.dieselUsed = sim.dieselUsed + dt * burn
        seconds = seconds - dt
    end
end

-- Nabíjení po dobu seconds, z toho prvních pumpSeconds běží čerpadlo (plnění dronu); vrací, kolik sekund čerpání zbývá.
function SprayDroneRoute.runPower(sim, pw, seconds, pumpSeconds)
    local pumping = math.min(seconds, math.max(pumpSeconds or 0, 0))
    if pumping > 0 then
        SprayDroneRoute.chargeSpares(sim, pw, pumping, true)
    end
    SprayDroneRoute.chargeSpares(sim, pw, seconds - pumping)
    return math.max((pumpSeconds or 0) - pumping, 0)
end

-- Čekání, než je některá náhradní baterie nabitá aspoň na pw.readyCharge (prvních pumpSeconds souběžně s plněním dronu);
-- vrací sekundy (nil, když dojde nafta) a kolik sekund čerpání ještě zbývá.
function SprayDroneRoute.waitForReadySpare(sim, pw, pumpSeconds)
    local waited, pumpLeft = 0, pumpSeconds or 0
    while true do
        local _, charge = SprayDroneRoute.getBestSpare(sim.spares)
        if charge >= pw.readyCharge - 0.01 then
            return waited, pumpLeft
        end
        if sim.noFuel or waited > 7200 then
            return nil, pumpLeft
        end
        pumpLeft = SprayDroneRoute.runPower(sim, pw, 5, pumpLeft)
        waited = waited + 5
    end
end

-- Všechny dávky s plnou nádrží (jen pro zobrazení trasy), baterie od aktuální a s výměnami jako na vleku. Každý leg
-- dostane batch = číslo dávky. Vrací legy, počet dávek, jestli zbylo něco nenaplánovaného, a info {time, maxEnergy,
-- batterySwaps, height, tooHigh, noPath, transits, firstOut, firstBack, transitLength} za všechny dávky (přelety a délky
-- tam / zpět u první dávky, nejvyšší spotřeba dávky, počet výměn baterie).
-- S p.power ({spares, diesel, startFill, capacity, chargeRate, dieselPerSecond, readyCharge, swapTime, pumpRate,
-- minService, pumpShare, pumpLoad}) simuluje i servis na vleku: plnění čerpadlem (z centrály, nabíjení mezitím jen
-- pumpShare výkonu), výměnu za náhradní baterii nabitou aspoň na readyCharge, čekání na nabití a spotřebu nafty; info
-- pak má navíc serviceTime, waitTime, dieselUsed, noFuel (dávka čeká na baterii, kterou už bez nafty nejde nabít, nebo na
-- plnění, které bez nafty stojí: mise tam skončí / čeká) a fuelRunsOut (nafta dojde, než se nabije vše potřebné).
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
        sim = { spares = spares, diesel = pw.diesel, dieselUsed = 0, noFuel = false, pumpStarved = false }
        refill = tankCapacity - pw.startFill
    end
    local hasBattery = pw == nil or pw.droneHasBattery ~= false
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
        local swapped = startBattery ~= battery or not hasBattery
        if sim ~= nil then
            -- čerpadlo jede z centrály: po dobu plnění dostanou baterie jen pw.pumpShare výkonu
            local pumpTime = math.max(refill, 0) / pw.pumpRate
            local service = math.max(pumpTime, batch > 0 and pw.minService or 0)
            if swapped then
                -- vybitá baterie jde hned do volného slotu a nabíjí se s ostatními, do dronu jde
                -- nejnabitější, až má readyCharge (s jedinou baterií ta samá po nabití); jako SprayDroneStation.swapBattery
                if hasBattery then
                    table.insert(sim.spares, battery)
                end
                local wait, pumpLeft = SprayDroneRoute.waitForReadySpare(sim, pw, pumpTime)
                if wait == nil then
                    info.noFuel = true
                    break
                end
                bestSlot = SprayDroneRoute.getBestSpare(sim.spares)
                startBattery = table.remove(sim.spares, bestSlot)
                -- plnění, výměna i nabíjení běží souběžně; čekáním je jen to, o co se servis kvůli nabití prodlouží
                info.waitTime = info.waitTime + math.max(wait - service, 0)
                SprayDroneRoute.runPower(sim, pw, math.max(service - wait - pw.swapTime, 0), pumpLeft)
                service = math.max(service, wait + pw.swapTime)
            else
                SprayDroneRoute.runPower(sim, pw, service, pumpTime)
            end
            if sim.pumpStarved then
                -- bez nafty čerpadlo stojí a dron se nenaplní: mise tu čeká na proud
                info.noFuel = true
                break
            end
            info.serviceTime = info.serviceTime + service
            SprayDroneRoute.chargeSpares(sim, pw, batchInfo.time)
            refill = math.min(sprayed * p.litersPerMeter, tankCapacity)
        end
        if swapped and hasBattery then
            info.batterySwaps = info.batterySwaps + 1
        end
        battery = startBattery - batchInfo.energy
        hasBattery = true
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
        SprayDroneRoute.collectRouteShapes(info, batchInfo, batch)
        i, off = ni, noff
    end
    if sim ~= nil then
        info.dieselUsed = sim.dieselUsed
        info.fuelRunsOut = sim.noFuel
    end
    -- řádky, které se do plánu nevešly (došla nafta nebo baterie, nebo se nenašla cesta): plánovač je ukáže červeně
    info.unplanned = {}
    for k = i, #legs do
        table.insert(info.unplanned, legs[k])
    end
    return drawLegs, batch, i <= #legs, info
end

---------------------------------------------------------------------------------------------------
-- dva drony na jednom poli: dělení zbývající práce a rezervace úseků druhého dronu

-- Úseky {ax, az, bx, bz}, které druhý dron právě stříká: části řádků do margin m od nich se při sestavení legů vynechají
-- (nastavuje SprayDroneStation.buildAllLegs jen na dobu volání buildLegs).
SprayDroneRoute.reserved = nil
SprayDroneRoute.reservedMargin = 0
-- kruhy signálu ({x, z, r}: rádio vleku a spojené relé tyče) na dobu stavby legů; ořez kruhem dosahu kolem vleku (rádio +
-- vzdálenost relé) by jinak nechal i místa, kam signál nedosáhne, a dron by tam za letu ztratil spojení. nil = bez omezení.
SprayDroneRoute.signalCircles = nil

function SprayDroneRoute.isInSignal(x, z)
    local circles = SprayDroneRoute.signalCircles
    if circles == nil then
        return true
    end
    for _, c in ipairs(circles) do
        local dx, dz = x - c.x, z - c.z
        if dx * dx + dz * dz <= c.r * c.r then
            return true
        end
    end
    return false
end

function SprayDroneRoute.isReserved(x, z)
    local list = SprayDroneRoute.reserved
    if list == nil then
        return false
    end
    local margin = SprayDroneRoute.reservedMargin
    for _, s in ipairs(list) do
        local dx, dz = s[3] - s[1], s[4] - s[2]
        local l2 = dx * dx + dz * dz
        local t = l2 > 1e-6 and math.clamp(((x - s[1]) * dx + (z - s[2]) * dz) / l2, 0, 1) or 0
        if MathUtil.vector2Length(x - (s[1] + dx * t), z - (s[2] + dz * t)) < margin then
            return true
        end
    end
    return false
end

-- Obrácený leg (konec <-> začátek).
function SprayDroneRoute.reverseLeg(leg)
    return { x1 = leg.x2, z1 = leg.z2, x2 = leg.x1, z2 = leg.z1, len = leg.len }
end

-- Rozdělí seřazený seznam zbývajících legů mezi n dronů (1 nebo 2): dron 1 dostane začátek seznamu, dron 2 zbytek v obráceném
-- pořadí a s obrácenými úseky (od vzdáleného konce pole k prostředku). Řez se volí tak, aby odhad času obou dronů byl nejvyrovnanější.
-- opts: homes = { {x, z}, {x, z} }, batchLength (délka postřiku jedné dávky, m), spraySpeed, cruiseSpeed (m/s), serviceTime (s na
-- dávku), minSplit (m; práce pod tuto délku jde celá žadateli), requester (1 nebo 2).
-- Vrací { legs1, legs2 }.
function SprayDroneRoute.splitLegs(legs, n, opts)
    local requester = opts.requester or 1
    local result = { {}, {} }
    local count = #legs
    local total = 0
    for _, leg in ipairs(legs) do
        total = total + leg.len
    end
    if n < 2 or count < 2 or total < (opts.minSplit or 60) then
        result[requester] = legs
        return result
    end
    local h1, h2 = opts.homes[1], opts.homes[2]
    local prefix, dist1 = { [0] = 0 }, { [0] = 0 }
    for i = 1, count do
        local leg = legs[i]
        local mx, mz = (leg.x1 + leg.x2) * 0.5, (leg.z1 + leg.z2) * 0.5
        prefix[i] = prefix[i - 1] + leg.len
        dist1[i] = dist1[i - 1] + leg.len * MathUtil.vector2Length(mx - h1.x, mz - h1.z)
    end
    local dist2 = { [count] = 0 }
    for i = count - 1, 0, -1 do
        local leg = legs[i + 1]
        local mx, mz = (leg.x1 + leg.x2) * 0.5, (leg.z1 + leg.z2) * 0.5
        dist2[i] = dist2[i + 1] + leg.len * MathUtil.vector2Length(mx - h2.x, mz - h2.z)
    end
    local function estimate(length, meanDistance)
        if length <= 0 then
            return 0
        end
        local batches = math.ceil(length / math.max(opts.batchLength, 1))
        return length / math.max(opts.spraySpeed, 0.1) + batches * (2 * meanDistance / math.max(opts.cruiseSpeed, 0.1) + opts.serviceTime)
    end
    local bestI, bestT = 1, math.huge
    for i = 1, count - 1 do
        local len1, len2 = prefix[i], total - prefix[i]
        local t = math.max(estimate(len1, dist1[i] / math.max(len1, 1e-6)), estimate(len2, dist2[i] / math.max(len2, 1e-6)))
        if t < bestT - 1e-6 then
            bestT, bestI = t, i
        end
    end
    for i = 1, bestI do
        table.insert(result[1], legs[i])
    end
    for i = count, bestI + 1, -1 do
        table.insert(result[2], SprayDroneRoute.reverseLeg(legs[i]))
    end
    return result
end
