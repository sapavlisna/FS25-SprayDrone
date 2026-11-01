-- Mapy ze skenu pole dronem (docs/DRON.md, „Skenování pole“). Mapa patří farmě a poli, ne vleku: mřížka čtvercových buněk
-- zarovnaná na násobky velikosti buňky, každá naskenovaná buňka má jednu zabalenou hodnotu (plevel, vitalita porostu, růst,
-- plodina, kameny) a čas skenu. Sken vidí jen to, co kamera z výšky: vápno ani pH ne (docs/PLAN-airasi-kufr.md F2). Vzorkuje server za letu (scanStrip z SprayDroneStation.flushSpray), klientům jdou změny
-- po dávkách eventem (SprayDroneScanEvent), ukládá se do savegame vedle fields.xml.

SprayDroneScanMap = {}
SprayDroneScanMap.MOD_NAME = g_currentModName
SprayDroneScanMap.FILENAME = "sdtScanMaps.xml"

source(g_currentModDirectory .. "scripts/events/SprayDroneScanEvent.lua")

-- volba v plánovači (nastavení scanCell 0..2): velikost buňky, výška letu, záběr (dvě buňky na pruh) a násobek rychlosti skenu
SprayDroneScanMap.LEVELS = {
    { cell = 5, height = 8, swath = 10, speed = 0.6 },
    { cell = 10, height = 15, swath = 20, speed = 1 },
    { cell = 20, height = 30, swath = 40, speed = 1.5 }
}
-- server posílá změněné buňky klientům nejvýš jednou za SYNC_TIME ms, po MAX_EVENT_CELLS v jednom eventu
SprayDroneScanMap.SYNC_TIME = 2000
SprayDroneScanMap.MAX_EVENT_CELLS = 400
-- plevel ve stavech 1-2 hráč na poli nevidí (SprayDroneRoute.WEED_FIRST_STATE.., stejně jako herbicid)
SprayDroneScanMap.INVISIBLE_WEED_MAX = 2
SprayDroneScanMap.MINUTES_PER_DAY = 1440

-- Pořadí a rozsah položek zabalené hodnoty buňky (celé číslo pod 2^28, poziční zápis): podíl plevele v buňce 0..15 (x/15),
-- stav plevele ve středu, hnojení (vitalita porostu, jen nad plodinou), volné místo, růstový stupeň, plodina, kameny (jen na holé
-- půdě). Volné místo bylo vápno: pozice zůstává, aby šly číst mapy uložené dřív.
SprayDroneScanMap.FIELDS = {
    { "weedShare", 16 }, { "weedState", 16 }, { "sprayLevel", 4 }, { "reserved", 4 }, { "growthState", 32 },
    { "fruitTypeIndex", 256 }, { "stoneLevel", 8 }
}
SprayDroneScanMap.VALUE_BITS = 28
-- Precision Farming (pokud je ve hře): dusík, pH a cílový dusík buňky v jedné hodnotě map.pf[index] = 1 + dusík kg N/ha (0..511) + pH × 10 (0..127) × 512
-- + cílový dusík v pětikilových krocích (0..63) × 65536; 0 v jedné ze složek = bez údaje. Zvlášť od hodnoty buňky, ta je plná (28 bitů).
-- Sken pH nezapisuje (z výšky nejde poznat, vápnění ho čte živě ze vzorků PF, getLivePh); místo zůstává kvůli dřív uloženým mapám.
SprayDroneScanMap.PF_BITS = 23
SprayDroneScanMap.PF_NITROGEN_MAX = 511
SprayDroneScanMap.PF_PH_MAX = 127
SprayDroneScanMap.PF_TARGET_MAX = 63
SprayDroneScanMap.PF_TARGET_STEP = 5
-- aplikace podle skenu s PF: vápno na buňky s pH (ze vzorků, getLivePh) pod PF_PH_TARGET - PF_PH_TOLERANCE, hnojivo na buňky s dusíkem pod cílem - PF_NITROGEN_TOLERANCE
SprayDroneScanMap.PF_PH_TARGET = 6.5
SprayDroneScanMap.PF_PH_TOLERANCE = 0.25
SprayDroneScanMap.PF_NITROGEN_TOLERANCE = 10
-- ošetření buňky po skenu (bity v map.treatedKinds): herbicid, vápno, hnojivo
SprayDroneScanMap.TREAT_HERBICIDE = 1
SprayDroneScanMap.TREAT_LIME = 2
SprayDroneScanMap.TREAT_FERTILIZER = 4
SprayDroneScanMap.TREAT_BITS = 3

-- [farmId][fieldId] = mapa
SprayDroneScanMap.maps = {}
SprayDroneScanMap.syncTimer = 0
SprayDroneScanMap.windSpeed = nil

function SprayDroneScanMap.encode(c)
    local value, factor = 0, 1
    for _, f in ipairs(SprayDroneScanMap.FIELDS) do
        value = value + math.clamp(math.floor((c[f[1]] or 0) + 0.5), 0, f[2] - 1) * factor
        factor = factor * f[2]
    end
    return value
end

function SprayDroneScanMap.decode(value)
    local c = {}
    for _, f in ipairs(SprayDroneScanMap.FIELDS) do
        c[f[1]] = value % f[2]
        value = math.floor(value / f[2])
    end
    c.weedShare = c.weedShare / 15
    return c
end

function SprayDroneScanMap.encodePF(nitrogen, ph, targetNitrogen)
    if nitrogen == nil and ph == nil then
        return nil
    end
    local base = SprayDroneScanMap.PF_NITROGEN_MAX + 1
    return 1 + math.clamp(math.floor((nitrogen or 0) + 0.5), 0, SprayDroneScanMap.PF_NITROGEN_MAX)
        + math.clamp(math.floor((ph or 0) * 10 + 0.5), 0, SprayDroneScanMap.PF_PH_MAX) * base
        + math.clamp(math.floor((targetNitrogen or 0) / SprayDroneScanMap.PF_TARGET_STEP + 0.5), 0, SprayDroneScanMap.PF_TARGET_MAX)
        * base * (SprayDroneScanMap.PF_PH_MAX + 1)
end

-- dusík kg N/ha, pH a cílový dusík kg N/ha (nil = bez údaje)
function SprayDroneScanMap.decodePF(value)
    if value == nil then
        return nil, nil, nil
    end
    value = value - 1
    local base = SprayDroneScanMap.PF_NITROGEN_MAX + 1
    local nitrogen = value % base
    value = math.floor(value / base)
    local ph = value % (SprayDroneScanMap.PF_PH_MAX + 1)
    local target = math.floor(value / (SprayDroneScanMap.PF_PH_MAX + 1)) * SprayDroneScanMap.PF_TARGET_STEP
    return nitrogen > 0 and nitrogen or nil, ph > 0 and ph / 10 or nil, target > 0 and target or nil
end

-- Herní čas v minutách od začátku hry (monotónní den a čas dne).
function SprayDroneScanMap.getNow()
    local env = g_currentMission ~= nil and g_currentMission.environment or nil
    if env == nil then
        return 0
    end
    return (env.currentMonotonicDay or 0) * SprayDroneScanMap.MINUTES_PER_DAY + math.floor((env.dayTime or 0) / 60000)
end

function SprayDroneScanMap.getLevel(index)
    return SprayDroneScanMap.LEVELS[math.clamp((index or 1) + 1, 1, #SprayDroneScanMap.LEVELS)]
end

---------------------------------------------------------------------------------------------------
-- mapy

-- Mapa s danou mřížkou; buňky uvnitř pole (střed v polygonu) se spočítají z pole, takže klient je dopočítá sám stejně.
function SprayDroneScanMap.createMap(farmId, fieldId, cellSize, originX, originZ, nx, nz)
    local map = { farmId = farmId, fieldId = fieldId, cellSize = cellSize, originX = originX, originZ = originZ, nx = nx, nz = nz,
        values = {}, pf = {}, times = {}, treated = {}, treatedKinds = {}, inside = {}, numInside = 0, numScanned = 0, updated = 0, revision = 0,
        dirty = nil }
    local field = SprayDroneRoute.getFieldById(fieldId)
    if field ~= nil then
        local poly = SprayDroneRoute.getPolygon(field)
        for iz = 0, nz - 1 do
            for ix = 0, nx - 1 do
                local cx, cz = originX + (ix + 0.5) * cellSize, originZ + (iz + 0.5) * cellSize
                if SprayDroneRoute.isPointInPolygon(poly, cx, cz) then
                    map.inside[iz * nx + ix + 1] = true
                    map.numInside = map.numInside + 1
                end
            end
        end
    end
    SprayDroneScanMap.maps[farmId] = SprayDroneScanMap.maps[farmId] or {}
    SprayDroneScanMap.maps[farmId][fieldId] = map
    return map
end

function SprayDroneScanMap.getMap(farmId, fieldId)
    local farm = SprayDroneScanMap.maps[farmId]
    return farm ~= nil and farm[fieldId] or nil
end

-- Mapa pro sken pole s buňkou cellSize (server): stávající se stejnou buňkou zůstane (sken přepisuje buňky), jinak nová.
function SprayDroneScanMap.ensureMap(farmId, field, cellSize)
    local fieldId = field:getId()
    local map = SprayDroneScanMap.getMap(farmId, fieldId)
    if map ~= nil and map.cellSize == cellSize then
        return map
    end
    local minX, maxX, minZ, maxZ = math.huge, -math.huge, math.huge, -math.huge
    for _, p in ipairs(SprayDroneRoute.getPolygon(field)) do
        minX, maxX, minZ, maxZ = math.min(minX, p.x), math.max(maxX, p.x), math.min(minZ, p.z), math.max(maxZ, p.z)
    end
    local originX, originZ = math.floor(minX / cellSize) * cellSize, math.floor(minZ / cellSize) * cellSize
    map = SprayDroneScanMap.createMap(farmId, fieldId, cellSize, originX, originZ,
        math.max(math.ceil((maxX - originX) / cellSize), 1), math.max(math.ceil((maxZ - originZ) / cellSize), 1))
    map.reset = true
    SprayDroneScanMap.markDirty(map, nil)
    return map
end

function SprayDroneScanMap.getCellIndex(map, x, z)
    local ix = math.floor((x - map.originX) / map.cellSize)
    local iz = math.floor((z - map.originZ) / map.cellSize)
    if ix < 0 or iz < 0 or ix >= map.nx or iz >= map.nz then
        return nil
    end
    return iz * map.nx + ix + 1
end

function SprayDroneScanMap.getCellCenter(map, index)
    local i = index - 1
    local ix, iz = i % map.nx, math.floor(i / map.nx)
    return map.originX + (ix + 0.5) * map.cellSize, map.originZ + (iz + 0.5) * map.cellSize
end

-- Buňka pod bodem: { weedShare 0..1, weedState, sprayLevel, growthState, fruitTypeIndex, stoneLevel, time, treated,
-- treatedKinds }, nil = nenaskenováno. treated = čas posledního ošetření po skenu (nil = neošetřeno), treatedKinds bity TREAT_*.
function SprayDroneScanMap.getCell(map, x, z)
    local index = SprayDroneScanMap.getCellIndex(map, x, z)
    return index ~= nil and SprayDroneScanMap.unpack(map, index) or nil
end

-- Rozbalená buňka indexu (jako getCell, s dusíkem z Precision Farming, když je v mapě), nil = nenaskenováno. pH z map uložených
-- před F2 se nečte.
function SprayDroneScanMap.unpack(map, index)
    local value = map.values[index]
    if value == nil then
        return nil
    end
    local c = SprayDroneScanMap.decode(value)
    local nitrogen, _, targetNitrogen = SprayDroneScanMap.decodePF(map.pf[index])
    c.nitrogen, c.targetNitrogen = nitrogen, targetNitrogen
    c.time, c.treated, c.treatedKinds = map.times[index], map.treated[index], map.treatedKinds[index] or 0
    return c
end

-- fn(index, x, z, buňka) pro každou naskenovanou buňku.
function SprayDroneScanMap.forEachCell(map, fn)
    for index in pairs(map.values) do
        local x, z = SprayDroneScanMap.getCellCenter(map, index)
        fn(index, x, z, SprayDroneScanMap.unpack(map, index))
    end
end

function SprayDroneScanMap.getIsTreated(map, index, kind)
    return math.floor((map.treatedKinds[index] or 0) / kind) % 2 == 1
end

-- Druh ošetření přípravku (TREAT_*), nil = přípravek mapu nemění.
function SprayDroneScanMap.getTreatKind(sprayType)
    if sprayType == nil or sprayType.isScan then
        return nil
    elseif sprayType.isHerbicide then
        return SprayDroneScanMap.TREAT_HERBICIDE
    elseif sprayType.isLime then
        return SprayDroneScanMap.TREAT_LIME
    elseif sprayType.isFertilizer then
        return SprayDroneScanMap.TREAT_FERTILIZER
    end
    return nil
end

-- Stáří dat (herní hodiny od posledního zápisu do mapy).
function SprayDroneScanMap.getAgeHours(map, now)
    return math.max((now or SprayDroneScanMap.getNow()) - map.updated, 0) / 60
end

function SprayDroneScanMap.getIsRipe(c)
    local fruitType = c.fruitTypeIndex > 0 and g_fruitTypeManager:getFruitTypeByIndex(c.fruitTypeIndex) or nil
    return fruitType ~= nil and fruitType.minHarvestingGrowthState ~= nil and fruitType.minHarvestingGrowthState > 0
        and c.growthState >= fruitType.minHarvestingGrowthState and c.growthState <= fruitType.maxHarvestingGrowthState
end

-- Souhrn mapy: buňky v poli a naskenované, podíl pokrytí, buňky s plevelem (z toho neviditelným), průměrný podíl plevele,
-- buňky se slabým porostem (nehnojené; jen pod plodinou), zralé a s kameny.
function SprayDroneScanMap.getSummary(map)
    local s = { cells = map.numInside, scanned = 0, weedCells = 0, invisibleWeedCells = 0, weedShare = 0,
        unfertilizedCells = 0, ripeCells = 0, stoneCells = 0, treatedCells = 0, pfCells = 0 }
    local nSum, nCount = 0, 0
    for _ in pairs(map.treated) do
        s.treatedCells = s.treatedCells + 1
    end
    for index, value in pairs(map.values) do
        local c = SprayDroneScanMap.decode(value)
        s.scanned = s.scanned + 1
        s.weedShare = s.weedShare + c.weedShare
        if c.weedShare > 0 or c.weedState > 0 then
            s.weedCells = s.weedCells + 1
            if c.weedState > 0 and c.weedState <= SprayDroneScanMap.INVISIBLE_WEED_MAX then
                s.invisibleWeedCells = s.invisibleWeedCells + 1
            end
        end
        if c.sprayLevel == 0 and c.fruitTypeIndex > 0 then
            s.unfertilizedCells = s.unfertilizedCells + 1
        end
        if SprayDroneScanMap.getIsRipe(c) then
            s.ripeCells = s.ripeCells + 1
        end
        if c.stoneLevel > 0 then
            s.stoneCells = s.stoneCells + 1
        end
        local nitrogen = SprayDroneScanMap.decodePF(map.pf[index])
        if nitrogen ~= nil then
            nSum, nCount = nSum + nitrogen, nCount + 1
            s.minNitrogen, s.maxNitrogen = math.min(s.minNitrogen or nitrogen, nitrogen), math.max(s.maxNitrogen or nitrogen, nitrogen)
            s.pfCells = s.pfCells + 1
        end
    end
    s.avgNitrogen = nCount > 0 and nSum / nCount or nil
    s.weedShare = s.scanned > 0 and s.weedShare / s.scanned or 0
    s.coverage = s.cells > 0 and math.min(s.scanned / s.cells, 1) or 0
    return s
end

---------------------------------------------------------------------------------------------------
-- vzorkování (server)

-- Zabalená hodnota buňky teď: stav pole ve středu (vanilla FieldState) a podíl pixelů plevele v celém čtverci buňky. Kamera vidí
-- vitalitu (hnojení) jen u porostu a kameny jen na holé půdě (bez plodiny); vápno nevidí.
function SprayDroneScanMap.readCell(map, index)
    local cx, cz = SprayDroneScanMap.getCellCenter(map, index)
    SprayDroneScanMap.fieldState = SprayDroneScanMap.fieldState or FieldState.new()
    local state = SprayDroneScanMap.fieldState
    state:update(cx, cz)
    local h = map.cellSize * 0.5
    local weed, total = SprayDroneStation.getWeedPixels(cx - h, cz - h, cx + h, cz - h, cx - h, cz + h)
    local share = 0
    if weed ~= nil and total ~= nil and total > 0 and weed > 0 then
        share = math.max(weed / total * 15, 1)
    end
    local fruitTypeIndex = state.fruitTypeIndex
    if fruitTypeIndex == nil or fruitTypeIndex == FruitType.UNKNOWN then
        fruitTypeIndex = 0
    end
    local bare = fruitTypeIndex == 0
    return SprayDroneScanMap.encode({ weedShare = share, weedState = state.weedState, sprayLevel = bare and 0 or state.sprayLevel,
        growthState = state.growthState, fruitTypeIndex = fruitTypeIndex, stoneLevel = bare and state.stoneLevel or 0 })
end

-- Průměr vrstvy mapy Precision Farming (vnitřní hodnota) ve čtverci o straně size kolem (x, z); nil bez dat. Součet hodnot ve čtverci dělený
-- počtem pixelů (DensityMapModifier:executeGet bez filtru).
local function readPFAverage(mapId, firstChannel, numChannels, x, z, size)
    local h = size * 0.5
    local modifier = DensityMapModifier.new(mapId, firstChannel, numChannels, g_terrainNode)
    modifier:setParallelogramWorldCoords(x - h, z - h, x + h, z - h, x - h, z + h, DensityCoordType.POINT_POINT_POINT)
    local sum, pixels = modifier:executeGet()
    if sum == nil or pixels == nil or pixels <= 0 then
        return nil
    end
    return sum / pixels
end

-- Cílový dusík (kg N/ha) plodiny, která na místě roste, podle požadavků plodin Precision Farming (averageTargetLevel ve stavech mapy);
-- nil bez plodiny nebo bez požadavku.
function SprayDroneScanMap.getTargetNitrogen(pf, x, z)
    local nitrogenMap = pf.nitrogenMap
    local fruitTypeIndex = FSDensityMapUtil.getFruitTypeIndexAtWorldPos(x, z)
    if nitrogenMap == nil or fruitTypeIndex == nil or fruitTypeIndex == FruitType.UNKNOWN then
        return nil
    end
    local ok, target = pcall(function()
        local requirement = nitrogenMap.fruitTypeIndexToFruitRequirement ~= nil and nitrogenMap.fruitTypeIndexToFruitRequirement[fruitTypeIndex] or nil
        if type(requirement) == "number" then
            requirement = nitrogenMap.fruitRequirements ~= nil and nitrogenMap.fruitRequirements[requirement] or nil
        end
        if type(requirement) ~= "table" or requirement.averageTargetLevel == nil then
            return nil
        end
        return requirement.averageTargetLevel * (nitrogenMap.amountPerState or SprayDroneScanMap.PF_TARGET_STEP)
    end)
    return ok and target or nil
end

-- Hodnota mapy PF (pfMap třídy className) ve čtverci o straně size kolem (x, z) převedená funkcí convert(mapa, vnitřní stav); necelý
-- průměr se interpoluje mezi sousedními celými stavy. nil bez dat nebo při chybě PF.
function SprayDroneScanMap.readPFValue(pfMap, className, convert, x, z, size)
    local ok, value = pcall(function()
        local mapId, first, num = SprayDroneStation.getPFMapLayer(pfMap, className)
        if mapId == nil then
            return nil
        end
        local avg = readPFAverage(mapId, first, num, x, z, size)
        if avg == nil or avg <= 0 then
            return nil
        end
        local low = math.floor(avg)
        local a, b = convert(pfMap, low), convert(pfMap, low + 1)
        return a + (b - a) * (avg - low)
    end)
    return ok and value or nil
end

-- Dusík (kg N/ha) buňky z mapy Precision Farming zabalený do jedné hodnoty (encodePF), nil, když PF ve hře není nebo na místě nic
-- neroste (dron dusík odhaduje z barvy porostu); pH sken nečte.
function SprayDroneScanMap.readPF(map, index)
    local pf = SprayDroneStation.getPrecisionFarming()
    if pf == nil then
        return nil
    end
    local cx, cz = SprayDroneScanMap.getCellCenter(map, index)
    local fruitTypeIndex = FSDensityMapUtil.getFruitTypeIndexAtWorldPos(cx, cz)
    if fruitTypeIndex == nil or fruitTypeIndex == FruitType.UNKNOWN then
        return nil
    end
    local nitrogen = SprayDroneScanMap.readPFValue(pf.nitrogenMap, "NitrogenMap", function(m, v) return m:getNitrogenValueFromInternalValue(v) end,
        cx, cz, map.cellSize)
    return SprayDroneScanMap.encodePF(nitrogen, nil, SprayDroneScanMap.getTargetNitrogen(pf, cx, cz))
end

-- Je půda v (x, z) odkrytá vzorky půdy farmy farmId (PF coverMap)? Signatura getIsUncoveredAtPos není ověřená: zkusí se (x, z, farmId)
-- a pak (x, z); chyba nebo jiný výsledek než true = neodkryté.
function SprayDroneScanMap.getIsSampled(pf, x, z, farmId)
    local coverMap = pf ~= nil and pf.coverMap or nil
    if coverMap == nil or coverMap.getIsUncoveredAtPos == nil then
        return false
    end
    local ok, result = pcall(coverMap.getIsUncoveredAtPos, coverMap, x, z, farmId)
    if not ok then
        ok, result = pcall(coverMap.getIsUncoveredAtPos, coverMap, x, z)
    end
    return ok and result == true
end

-- pH půdy ve čtverci size kolem (x, z) teď, jen kde jsou odebrané vzorky (getIsSampled ve středu); nil bez PF, bez vzorku nebo bez dat.
function SprayDroneScanMap.getLivePh(pf, x, z, size, farmId)
    if pf == nil or not SprayDroneScanMap.getIsSampled(pf, x, z, farmId) then
        return nil
    end
    return SprayDroneScanMap.readPFValue(pf.pHMap, "PHMap", function(m, v) return m:getPhValueFromInternalValue(v) end, x, z, size)
end

-- Vanilla úroveň vápna v (x, z) teď, pro vápnění bez PF (vanilla vzorky půdy nemá, stav vápna ukazuje i mapa pole ve hře).
function SprayDroneScanMap.getLiveLimeLevel(x, z)
    SprayDroneScanMap.fieldState = SprayDroneScanMap.fieldState or FieldState.new()
    local state = SprayDroneScanMap.fieldState
    state:update(x, z)
    return state.limeLevel or 0
end

-- Sken buňky: hodnota, čas skenu; dřívější ošetření tím přestává platit.
function SprayDroneScanMap.sampleCell(map, index, now)
    local value = SprayDroneScanMap.readCell(map, index)
    if map.values[index] == nil then
        map.numScanned = map.numScanned + 1
    end
    map.values[index] = value
    map.pf[index] = SprayDroneScanMap.readPF(map, index)
    map.times[index] = now
    map.treated[index], map.treatedKinds[index] = nil, nil
    map.revision = map.revision + 1
    SprayDroneScanMap.markDirty(map, index)
end

-- fn(index) pro buňky v poli, jejichž střed leží v pruhu od (ax, az) do (bx, bz) se záběrem 2 × halfWidth. Konec pruhu patří
-- dalšímu pruhu (along < len), aby se buňka na hraně dvou flushů nezapočetla dvakrát. Vrací počet.
function SprayDroneScanMap.forStripCells(map, ax, az, bx, bz, halfWidth, fn)
    local dx, dz = bx - ax, bz - az
    local len = MathUtil.vector2Length(dx, dz)
    if len < 0.01 then
        return 0
    end
    dx, dz = dx / len, dz / len
    local minX, maxX = math.min(ax, bx) - halfWidth, math.max(ax, bx) + halfWidth
    local minZ, maxZ = math.min(az, bz) - halfWidth, math.max(az, bz) + halfWidth
    local size = map.cellSize
    local n = 0
    for iz = math.max(math.floor((minZ - map.originZ) / size), 0), math.min(math.floor((maxZ - map.originZ) / size), map.nz - 1) do
        for ix = math.max(math.floor((minX - map.originX) / size), 0), math.min(math.floor((maxX - map.originX) / size), map.nx - 1) do
            local index = iz * map.nx + ix + 1
            if map.inside[index] then
                local cx, cz = map.originX + (ix + 0.5) * size, map.originZ + (iz + 0.5) * size
                local rx, rz = cx - ax, cz - az
                local along = rx * dx + rz * dz
                local across = math.abs(rx * dz - rz * dx)
                if along >= 0 and along < len and across <= halfWidth then
                    fn(index)
                    n = n + 1
                end
            end
        end
    end
    return n
end

-- Pruh skenu: buňky pod záběrem se navzorkují. Vrací počet.
function SprayDroneScanMap.scanStrip(map, ax, az, bx, bz, halfWidth)
    local now = SprayDroneScanMap.getNow()
    local n = SprayDroneScanMap.forStripCells(map, ax, az, bx, bz, halfWidth, function(index)
        SprayDroneScanMap.sampleCell(map, index, now)
    end)
    if n > 0 then
        map.updated = now
    end
    return n
end

-- Ošetřená buňka (server, po postřiku pruhu): hodnota se přečte znovu ze skutečného stavu pole (vanilla nedovolí třeba druhé
-- hnojení před dalším růstem, takže se nic nedopočítává), čas skenu zůstane a ošetření se zapíše s časem a druhem; přípravek
-- buňku do dalšího skenu znovu nevybere (getSpotSelector). Nenaskenovaná buňka dostane jen záznam o ošetření.
function SprayDroneScanMap.treatCell(map, index, kind, now)
    if map.values[index] ~= nil then
        map.values[index] = SprayDroneScanMap.readCell(map, index)
        map.pf[index] = SprayDroneScanMap.readPF(map, index)
    end
    map.treated[index] = now
    if not SprayDroneScanMap.getIsTreated(map, index, kind) then
        map.treatedKinds[index] = (map.treatedKinds[index] or 0) + kind
    end
    map.revision = map.revision + 1
    SprayDroneScanMap.markDirty(map, index)
end

-- Pruh postřiku přes mapu: buňky se středem pod záběrem se označí jako ošetřené (treatCell). Vrací počet.
function SprayDroneScanMap.treatStrip(map, ax, az, bx, bz, halfWidth, kind)
    local now = SprayDroneScanMap.getNow()
    return SprayDroneScanMap.forStripCells(map, ax, az, bx, bz, halfWidth, function(index)
        SprayDroneScanMap.treatCell(map, index, kind, now)
    end)
end

-- Konec aplikace podle skenu („pole hotové“): buňky v poli, které přípravek pořád vybírá (select jako getSpotSelector), trasa
-- pokrýt nedokázala (okraj pole, kam pruhy nedosáhnou) – označí se jako ošetřené, jinak by nad nimi každá další mise létala marně.
-- Vrací počet.
function SprayDroneScanMap.treatRemaining(map, select, kind)
    local now = SprayDroneScanMap.getNow()
    local n = 0
    for index in pairs(map.inside) do
        local value = map.values[index]
        if select(value ~= nil and SprayDroneScanMap.decode(value) or nil, map.treatedKinds[index] or 0, map, index) then
            SprayDroneScanMap.treatCell(map, index, kind, now)
            n = n + 1
        end
    end
    return n
end

---------------------------------------------------------------------------------------------------
-- podmínky skenu

-- Rychlost větru (m/s) z posledního hlášení vanilla WindUpdater (addWindChangedListener jako větrná elektrárna).
function SprayDroneScanMap:setWindValues(windDirX, windDirZ, windVelocity, cirrusCloudSpeedFactor)
    SprayDroneScanMap.windSpeed = windVelocity
end

-- Vítr teď: WindUpdater.currentVelocity (ve hře ověřeno, že existuje; posluchač se ozve až při změně větru), jinak poslední hlášení.
-- Jednotka m/s: mapy mají <wind speed> v km/h (slunečno 4-13, zataženo 17-28, déšť 38-68) a speed 10 dal currentVelocity 2,8.
function SprayDroneScanMap.getWindSpeed()
    local updater = SprayDroneScanMap.windUpdater
    if updater ~= nil and type(updater.currentVelocity) == "number" then
        return updater.currentVelocity
    end
    return SprayDroneScanMap.windSpeed
end

function SprayDroneScanMap.registerWind()
    local env = g_currentMission ~= nil and g_currentMission.environment or nil
    local updater = env ~= nil and env.weather ~= nil and env.weather.windUpdater or nil
    if updater ~= nil and updater.addWindChangedListener ~= nil and SprayDroneScanMap.windUpdater ~= updater then
        updater:addWindChangedListener(SprayDroneScanMap)
        SprayDroneScanMap.windUpdater = updater
    end
end

-- Proč teď nejde letět: "dark" (slunce nesvítí; jen bez allowDark, postřik smí i v noci), "rain" (prší / sněží), "wind" (vítr nad
-- maxWind m/s), jinak nil. Druhá hodnota je text s naměřenými hodnotami do logu.
function SprayDroneScanMap.getBlocker(maxWind, allowDark)
    local env = g_currentMission ~= nil and g_currentMission.environment or nil
    if env == nil then
        return nil, "bez prostředí"
    end
    local weather = env.weather
    local rain = weather ~= nil and weather.getRainFallScale ~= nil and weather:getRainFallScale() or 0
    local raining = weather ~= nil and weather.getIsRaining ~= nil and weather:getIsRaining() or false
    local wind = SprayDroneScanMap.getWindSpeed()
    local info = string.format("slunce %s, %02d:%02d, srážky %.2f%s, vítr %s m/s", tostring(env.isSunOn), env.currentHour or -1,
        env.currentMinute or 0, rain, raining and " (prší)" or "", wind ~= nil and string.format("%.1f", wind) or "?")
    if env.isSunOn == false and not allowDark then
        return "dark", info
    end
    if raining or rain > 0.05 then
        return "rain", info
    end
    if maxWind ~= nil and wind ~= nil and wind > maxWind then
        return "wind", info
    end
    return nil, info
end

---------------------------------------------------------------------------------------------------
-- přenos klientům

function SprayDroneScanMap.markDirty(map, index)
    if g_server == nil then
        return
    end
    map.dirty = map.dirty or {}
    if index ~= nil then
        map.dirty[index] = true
    end
end

-- Eventy s hlavičkou mapy a buňkami ze seznamu indexů (nil = všechny naskenované nebo ošetřené), po MAX_EVENT_CELLS. Buňka je
-- { index, hodnota (nil = nenaskenováno), čas skenu, čas ošetření (nil = neošetřeno), druhy ošetření, PF hodnota (nil = bez PF) }.
function SprayDroneScanMap.buildEvents(map, indices, reset)
    local list = {}
    if indices == nil then
        for index in pairs(map.values) do
            table.insert(list, index)
        end
        for index in pairs(map.treated) do
            if map.values[index] == nil then
                table.insert(list, index)
            end
        end
    else
        list = indices
    end
    table.sort(list)
    local events = {}
    local i = 1
    repeat
        local cells = {}
        for k = i, math.min(i + SprayDroneScanMap.MAX_EVENT_CELLS - 1, #list) do
            local index = list[k]
            table.insert(cells, { index, map.values[index], map.times[index] or 0, map.treated[index], map.treatedKinds[index] or 0, map.pf[index] })
        end
        table.insert(events, SprayDroneScanEvent.new(map, cells, reset and i == 1))
        i = i + SprayDroneScanMap.MAX_EVENT_CELLS
    until i > #list
    return events
end

function SprayDroneScanMap.flushSync()
    for _, farm in pairs(SprayDroneScanMap.maps) do
        for _, map in pairs(farm) do
            if map.dirty ~= nil then
                local indices = {}
                for index in pairs(map.dirty) do
                    table.insert(indices, index)
                end
                local reset = map.reset == true
                map.dirty, map.reset = nil, nil
                for _, event in ipairs(SprayDroneScanMap.buildEvents(map, indices, reset)) do
                    g_server:broadcastEvent(event)
                end
            end
        end
    end
end

-- Klient: hlavička a buňky ze serveru (SprayDroneScanEvent:run).
function SprayDroneScanMap.applyRemote(header, cells)
    local map = SprayDroneScanMap.getMap(header.farmId, header.fieldId)
    if header.reset or map == nil or map.cellSize ~= header.cellSize or map.originX ~= header.originX or map.originZ ~= header.originZ
        or map.nx ~= header.nx or map.nz ~= header.nz then
        map = SprayDroneScanMap.createMap(header.farmId, header.fieldId, header.cellSize, header.originX, header.originZ, header.nx, header.nz)
    end
    for _, cell in ipairs(cells) do
        local index = cell[1]
        if cell[2] ~= nil then
            if map.values[index] == nil then
                map.numScanned = map.numScanned + 1
            end
            map.values[index] = cell[2]
            map.pf[index] = cell[6]
            map.times[index] = cell[3]
        end
        map.treated[index] = cell[4]
        map.treatedKinds[index] = cell[4] ~= nil and cell[5] or nil
    end
    map.updated = math.max(map.updated, header.updated)
    map.revision = map.revision + 1
end

function SprayDroneScanMap.sendAllToConnection(connection)
    for _, farm in pairs(SprayDroneScanMap.maps) do
        for _, map in pairs(farm) do
            for _, event in ipairs(SprayDroneScanMap.buildEvents(map, nil, true)) do
                connection:sendEvent(event)
            end
        end
    end
end

---------------------------------------------------------------------------------------------------
-- savegame: sdtScanMaps.xml vedle fields.xml (zápis a čtení se připojí k FieldManager:saveToXMLFile / loadFromXMLFile)

local function getDirectory(xmlFilename)
    return xmlFilename ~= nil and xmlFilename:match("^(.*)[/\\][^/\\]+$") or nil
end

function SprayDroneScanMap.save(directory)
    local xmlFile = XMLFile.create("sdtScanMaps", directory .. "/" .. SprayDroneScanMap.FILENAME, "sdtScanMaps")
    if xmlFile == nil then
        return
    end
    local m = 0
    for _, farm in pairs(SprayDroneScanMap.maps) do
        for _, map in pairs(farm) do
            local key = string.format("sdtScanMaps.map(%d)", m)
            xmlFile:setInt(key .. "#farmId", map.farmId)
            xmlFile:setInt(key .. "#fieldId", map.fieldId)
            xmlFile:setFloat(key .. "#cellSize", map.cellSize)
            xmlFile:setFloat(key .. "#originX", map.originX)
            xmlFile:setFloat(key .. "#originZ", map.originZ)
            xmlFile:setInt(key .. "#nx", map.nx)
            xmlFile:setInt(key .. "#nz", map.nz)
            xmlFile:setInt(key .. "#updated", map.updated)
            -- buňky po skupinách se stejným časem skenu: "index:hodnota" šestnáctkově, oddělené mezerou
            local groups = {}
            for index, value in pairs(map.values) do
                local t = map.times[index] or 0
                groups[t] = groups[t] or {}
                table.insert(groups[t], string.format("%x:%x", index, value))
            end
            local g = 0
            for t, parts in pairs(groups) do
                local groupKey = string.format("%s.cells(%d)", key, g)
                xmlFile:setInt(groupKey .. "#time", t)
                xmlFile:setString(groupKey, table.concat(parts, " "))
                g = g + 1
            end
            -- dusík a pH z Precision Farming: "index:hodnota" šestnáctkově
            local pfParts = {}
            for index, value in pairs(map.pf) do
                table.insert(pfParts, string.format("%x:%x", index, value))
            end
            if #pfParts > 0 then
                xmlFile:setString(key .. ".pf", table.concat(pfParts, " "))
            end
            -- ošetření po skenu: "index:čas:druhy" šestnáctkově
            local treated = {}
            for index, t in pairs(map.treated) do
                table.insert(treated, string.format("%x:%x:%x", index, t, map.treatedKinds[index] or 0))
            end
            if #treated > 0 then
                xmlFile:setString(key .. ".treated", table.concat(treated, " "))
            end
            m = m + 1
        end
    end
    xmlFile:save()
    xmlFile:delete()
end

function SprayDroneScanMap.load(directory)
    SprayDroneScanMap.maps = {}
    local xmlFile = XMLFile.loadIfExists("sdtScanMaps", directory .. "/" .. SprayDroneScanMap.FILENAME)
    if xmlFile == nil then
        return
    end
    local m = 0
    while true do
        local key = string.format("sdtScanMaps.map(%d)", m)
        if not xmlFile:hasProperty(key) then
            break
        end
        local map = SprayDroneScanMap.createMap(xmlFile:getInt(key .. "#farmId"), xmlFile:getInt(key .. "#fieldId"),
            xmlFile:getFloat(key .. "#cellSize"), xmlFile:getFloat(key .. "#originX"), xmlFile:getFloat(key .. "#originZ"),
            xmlFile:getInt(key .. "#nx"), xmlFile:getInt(key .. "#nz"))
        map.updated = xmlFile:getInt(key .. "#updated", 0)
        local g = 0
        while true do
            local groupKey = string.format("%s.cells(%d)", key, g)
            if not xmlFile:hasProperty(groupKey) then
                break
            end
            local t = xmlFile:getInt(groupKey .. "#time", 0)
            for indexText, valueText in string.gmatch(xmlFile:getString(groupKey) or "", "(%x+):(%x+)") do
                local index = tonumber(indexText, 16)
                if map.values[index] == nil then
                    map.numScanned = map.numScanned + 1
                end
                map.values[index] = tonumber(valueText, 16)
                map.times[index] = t
            end
            g = g + 1
        end
        for indexText, valueText in string.gmatch(xmlFile:getString(key .. ".pf") or "", "(%x+):(%x+)") do
            map.pf[tonumber(indexText, 16)] = tonumber(valueText, 16)
        end
        for indexText, timeText, kindsText in string.gmatch(xmlFile:getString(key .. ".treated") or "", "(%x+):(%x+):(%x+)") do
            local index = tonumber(indexText, 16)
            map.treated[index] = tonumber(timeText, 16)
            map.treatedKinds[index] = tonumber(kindsText, 16)
        end
        m = m + 1
    end
    xmlFile:delete()
end

FieldManager.saveToXMLFile = Utils.appendedFunction(FieldManager.saveToXMLFile, function(_, xmlFilename)
    local directory = getDirectory(xmlFilename)
    if directory ~= nil then
        SprayDroneScanMap.save(directory)
    end
end)

FieldManager.loadFromXMLFile = Utils.appendedFunction(FieldManager.loadFromXMLFile, function(_, xmlFilename)
    local directory = getDirectory(xmlFilename)
    if directory ~= nil then
        SprayDroneScanMap.load(directory)
    end
end)

if FSBaseMission ~= nil and FSBaseMission.sendInitialClientState ~= nil then
    FSBaseMission.sendInitialClientState = Utils.appendedFunction(FSBaseMission.sendInitialClientState, function(_, connection)
        SprayDroneScanMap.sendAllToConnection(connection)
    end)
end

function SprayDroneScanMap:loadMap()
    SprayDroneScanMap.windUpdater = nil
end

function SprayDroneScanMap:update(dt)
    SprayDroneScanMap.registerWind()
    if g_server == nil then
        return
    end
    SprayDroneScanMap.syncTimer = SprayDroneScanMap.syncTimer - dt
    if SprayDroneScanMap.syncTimer <= 0 then
        SprayDroneScanMap.syncTimer = SprayDroneScanMap.SYNC_TIME
        SprayDroneScanMap.flushSync()
    end
end

function SprayDroneScanMap:deleteMap()
    if SprayDroneScanMap.windUpdater ~= nil and SprayDroneScanMap.windUpdater.removeWindChangedListener ~= nil then
        SprayDroneScanMap.windUpdater:removeWindChangedListener(SprayDroneScanMap)
    end
    SprayDroneScanMap.windUpdater = nil
    SprayDroneScanMap.maps = {}
end

addModEventListener(SprayDroneScanMap)
