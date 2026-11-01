-- Mapa skenu v plánovači (docs/DRON.md, „Skenování pole“ > „Mapa skenu v plánovači“): barevné buňky map skenu farmy nad
-- polem podle zvolené vrstvy (volí se na stránce Mapa levého panelu) a souhrn vlastních polí seřazený podle naléhavosti
-- (stránka Pole). Metody plánovače, překryv se kreslí z jeho onDrawPostIngameMap.

SprayDroneScanOverlay = {}
-- buňka starší než STALE_HOURS herních hodin je vybledlá (plevel mezitím mohl vzejít)
SprayDroneScanOverlay.STALE_HOURS = 48
SprayDroneScanOverlay.STALE_ALPHA = 0.45
-- obdélníky překryvu se přestaví po změně mapy nebo vrstvy, kvůli stárnutí buněk aspoň jednou za REBUILD_TIME ms
SprayDroneScanOverlay.REBUILD_TIME = 5000
SprayDroneScanOverlay.OVERVIEW_REFRESH_TIME = 2000
SprayDroneScanOverlay.WEED_HIGH_SHARE = 0.25
-- hranice tříd vrstvy dusíku Precision Farming (kg N/ha, 5 tříd); popisy tříd v překladech sdt_scanui_c_nitrogenN
SprayDroneScanOverlay.NITROGEN_STEPS = { 30, 60, 90, 120 }

local function getClass(steps, value)
    for i, limit in ipairs(steps) do
        if value < limit then
            return i
        end
    end
    return #steps + 1
end

SprayDroneScanOverlay.COLORS = {
    weedNone = { 0.25, 0.75, 0.3, 0.25 },
    weedLow = { 1, 0.85, 0.1, 0.55 },
    weedHigh = { 1, 0.2, 0.1, 0.65 },
    weedInvisible = { 0.85, 0.3, 1, 0.65 },
    fertNone = { 0.6, 0.6, 0.6, 0.25 },
    fert0 = { 1, 0.3, 0.15, 0.6 },
    fert1 = { 1, 0.8, 0.1, 0.5 },
    fert2 = { 0.25, 0.75, 0.3, 0.3 },
    ripeNone = { 0.55, 0.55, 0.55, 0.35 },
    ripeYoung = { 0.6, 0.95, 0.45, 0.35 },
    ripeGrowing = { 0.2, 0.7, 0.25, 0.5 },
    ripeReady = { 1, 0.75, 0.05, 0.7 },
    ripeOver = { 0.6, 0.38, 0.15, 0.6 },
    stoneNone = { 0.25, 0.75, 0.3, 0.2 },
    stoneSome = { 0.7, 0.7, 0.75, 0.75 },
    nitrogen1 = { 0.85, 0.15, 0.1, 0.65 },
    nitrogen2 = { 1, 0.5, 0.1, 0.6 },
    nitrogen3 = { 1, 0.9, 0.2, 0.55 },
    nitrogen4 = { 0.55, 0.85, 0.3, 0.5 },
    nitrogen5 = { 0.1, 0.6, 0.25, 0.6 },
    treated = { 0.2, 0.45, 1, 0.6 },
    scanned = { 0.1, 0.85, 1, 0.45 },
    unscannedCover = { 1, 0.2, 0.1, 0.35 },
    unscanned = { 0.6, 0.6, 0.6, 0.15 }
}

SprayDroneScanOverlay.LAYERS = {
    { id = "off", text = "sdt_scanui_layerOff" },
    { id = "weed", text = "sdt_scanui_layerWeed", legend = { "weedNone", "weedLow", "weedHigh", "weedInvisible", "treated" } },
    { id = "fert", text = "sdt_scanui_layerFert", legend = { "fert0", "fert1", "fert2", "fertNone", "treated" } },
    { id = "ripe", text = "sdt_scanui_layerRipe", legend = { "ripeNone", "ripeYoung", "ripeGrowing", "ripeReady", "ripeOver" } },
    { id = "nitrogen", text = "sdt_scanui_layerNitrogen", legend = { "nitrogen1", "nitrogen2", "nitrogen3", "nitrogen4", "nitrogen5" } },
    { id = "stone", text = "sdt_scanui_layerStone", legend = { "stoneNone", "stoneSome" } },
    { id = "cover", text = "sdt_scanui_layerCover", legend = { "scanned", "unscannedCover" } }
}
SprayDroneScanOverlay.DEFAULT_LAYER = 2

-- Barva buňky (klíč COLORS) ve vrstvě; c je rozbalená hodnota (SprayDroneScanMap.decode).
function SprayDroneScanOverlay.getCellColorKey(layer, c)
    if layer == "weed" then
        if c.weedShare <= 0 and c.weedState == 0 then
            return "weedNone"
        elseif c.weedState > 0 and c.weedState <= SprayDroneScanMap.INVISIBLE_WEED_MAX then
            return "weedInvisible"
        end
        return c.weedShare > SprayDroneScanOverlay.WEED_HIGH_SHARE and "weedHigh" or "weedLow"
    elseif layer == "fert" then
        -- vitalita porostu: z výšky jde poznat jen tam, kde něco roste
        if c.fruitTypeIndex == 0 then
            return "fertNone"
        end
        return c.sprayLevel == 0 and "fert0" or (c.sprayLevel == 1 and "fert1" or "fert2")
    elseif layer == "ripe" then
        local fruitType = c.fruitTypeIndex > 0 and g_fruitTypeManager:getFruitTypeByIndex(c.fruitTypeIndex) or nil
        if fruitType == nil or c.growthState == 0 then
            return "ripeNone"
        elseif SprayDroneScanMap.getIsRipe(c) then
            return "ripeReady"
        end
        local minState = fruitType.minHarvestingGrowthState or 0
        if minState > 0 and c.growthState > (fruitType.maxHarvestingGrowthState or minState) then
            return "ripeOver"
        elseif minState > 0 and c.growthState * 2 < minState then
            return "ripeYoung"
        end
        return "ripeGrowing"
    elseif layer == "stone" then
        return c.stoneLevel > 0 and "stoneSome" or "stoneNone"
    elseif layer == "nitrogen" then
        return c.nitrogen ~= nil and "nitrogen" .. getClass(SprayDroneScanOverlay.NITROGEN_STEPS, c.nitrogen) or "unscanned"
    end
    return "scanned"
end

SprayDroneScanOverlay.colorCache = {}

-- Barva klíče; „klíč|stale“ = vybledlá (k šedé, menší krytí).
function SprayDroneScanOverlay.getColor(key)
    local color = SprayDroneScanOverlay.colorCache[key]
    if color == nil then
        local base, stale = key:match("^([^|]+)(|?.*)$")
        local c = SprayDroneScanOverlay.COLORS[base]
        if stale ~= "" then
            local a = SprayDroneScanOverlay.STALE_ALPHA
            color = { c[1] * 0.5 + 0.25, c[2] * 0.5 + 0.25, c[3] * 0.5 + 0.25, c[4] * a }
        else
            color = c
        end
        SprayDroneScanOverlay.colorCache[key] = color
    end
    return color
end

-- Obdélníky překryvu ve světových souřadnicích: souvislé úseky řádku se stejnou barvou se slijí a stejné úseky sousedních
-- řádků se spojí do jednoho obdélníku (stovky až tisíce buněk → desítky obdélníků).
-- Vrstva ukazuje buňky ošetřené po skenu jejím přípravkem zvlášť (klíč "treated"; aplikace podle skenu je do dalšího skenu
-- nevybírá): plevel herbicid, vitalita hnojivo.
function SprayDroneScanOverlay.getLayerTreatKind(layer)
    if layer == "weed" then
        return SprayDroneScanMap.TREAT_HERBICIDE
    elseif layer == "fert" then
        return SprayDroneScanMap.TREAT_FERTILIZER
    end
    return nil
end

function SprayDroneScanOverlay.buildRects(map, layer, now)
    local rects = {}
    local cs = map.cellSize
    local staleMinutes = SprayDroneScanOverlay.STALE_HOURS * 60
    local treatKind = SprayDroneScanOverlay.getLayerTreatKind(layer)
    local previous = {}
    for iz = 0, map.nz - 1 do
        local current = {}
        local runKey, runStart = nil, 0
        for ix = 0, map.nx do
            local key = nil
            if ix < map.nx then
                local index = iz * map.nx + ix + 1
                if map.inside[index] then
                    local value = map.values[index]
                    if value == nil then
                        key = layer == "cover" and "unscannedCover" or "unscanned"
                    else
                        key = SprayDroneScanOverlay.getCellColorKey(layer, SprayDroneScanMap.unpack(map, index))
                    end
                    if treatKind ~= nil and map.treated[index] ~= nil and SprayDroneScanMap.getIsTreated(map, index, treatKind) then
                        key = "treated"
                    end
                    if value ~= nil and now - (map.times[index] or now) > staleMinutes then
                        key = key .. "|stale"
                    end
                end
            end
            if key ~= runKey then
                if runKey ~= nil then
                    local id = string.format("%d:%d:%s", runStart, ix, runKey)
                    local rect = previous[id]
                    if rect ~= nil then
                        rect.z2 = map.originZ + (iz + 1) * cs
                    else
                        rect = { x1 = map.originX + runStart * cs, x2 = map.originX + ix * cs, z1 = map.originZ + iz * cs,
                            z2 = map.originZ + (iz + 1) * cs, color = SprayDroneScanOverlay.getColor(runKey) }
                        table.insert(rects, rect)
                    end
                    current[id] = rect
                end
                runKey, runStart = key, ix
            end
        end
        previous = current
    end
    return rects
end

-- Souhrn mapy jako podíly naskenovaných buněk (nil, když není nic naskenované) a naléhavost pro řazení přehledu.
function SprayDroneScanOverlay.getShares(map)
    local s = SprayDroneScanMap.getSummary(map)
    if s.scanned == 0 then
        return nil, s
    end
    local n = s.scanned
    local shares = { weed = s.weedCells / n, invisible = s.invisibleWeedCells / n,
        unfertilized = s.unfertilizedCells / n, ripe = s.ripeCells / n, coverage = s.coverage }
    shares.urgency = shares.weed * 3 + shares.ripe * 3 + shares.unfertilized
    return shares, s
end

-- Text notifikace po dokončení skenu (nil bez mapy nebo bez naskenovaných buněk).
function SprayDroneScanOverlay.getFindingsText(map, fieldName)
    local shares = map ~= nil and SprayDroneScanOverlay.getShares(map) or nil
    if shares == nil then
        return nil
    end
    return string.format(g_i18n:getText("sdt_scanui_notify"), fieldName, shares.weed * 100, shares.invisible * 100,
        shares.unfertilized * 100, shares.ripe * 100)
end

function SprayDroneScanOverlay.formatAge(hours)
    if hours < SprayDroneScanOverlay.STALE_HOURS then
        return string.format(g_i18n:getText("sdt_scanui_ageHours"), hours)
    end
    return string.format(g_i18n:getText("sdt_scanui_ageDays"), hours / 24)
end

---------------------------------------------------------------------------------------------------
-- metody plánovače

function SprayDronePlannerScreen:resetScanUi()
    self.scanLayerIndex = self.scanLayerIndex or SprayDroneScanOverlay.DEFAULT_LAYER
    self.scanRects = {}
    self.scanOverviewRows = nil
end

function SprayDronePlannerScreen:getScanLayer()
    return SprayDroneScanOverlay.LAYERS[self.scanLayerIndex or SprayDroneScanOverlay.DEFAULT_LAYER]
end

function SprayDronePlannerScreen:setScanLayer(index)
    self.scanLayerIndex = math.clamp(index, 1, #SprayDroneScanOverlay.LAYERS)
    SprayDroneSound.noteAction(string.format("plánovač: vrstva mapy skenu %s", self:getScanLayer().id))
end

function SprayDronePlannerScreen:getScanRects(map, layer, now)
    local cache = self.scanRects[map]
    if cache == nil or cache.layer ~= layer or cache.updated ~= map.updated or cache.revision ~= map.revision or g_time >= cache.time then
        cache = { layer = layer, updated = map.updated, revision = map.revision, time = g_time + SprayDroneScanOverlay.REBUILD_TIME,
            rects = SprayDroneScanOverlay.buildRects(map, layer, now) }
        self.scanRects[map] = cache
    end
    return cache.rects
end

-- Buňky všech map skenu farmy vleku, které jsou aspoň zčásti na obrazovce; pod obrysy polí a trasou.
function SprayDronePlannerScreen:drawScanOverlay()
    local layer = self:getScanLayer()
    local farm = SprayDroneScanMap.maps[self.vehicle:getOwnerFarmId()]
    if layer.id == "off" or farm == nil then
        return
    end
    local now = SprayDroneScanMap.getNow()
    for _, map in pairs(farm) do
        local ax, ay = self:worldToScreen(map.originX, map.originZ)
        local bx, by = self:worldToScreen(map.originX + map.nx * map.cellSize, map.originZ + map.nz * map.cellSize)
        if math.max(ax, bx) >= 0 and math.min(ax, bx) <= 1 and math.max(ay, by) >= 0 and math.min(ay, by) <= 1 then
            for _, r in ipairs(self:getScanRects(map, layer.id, now)) do
                local x1, y1 = self:worldToScreen(r.x1, r.z1)
                local x2, y2 = self:worldToScreen(r.x2, r.z2)
                local c = r.color
                drawFilledRect(math.min(x1, x2), math.min(y1, y2), math.abs(x2 - x1), math.abs(y2 - y1), c[1], c[2], c[3], c[4])
            end
        end
    end
end

-- Vlastní pole farmy vleku se souhrnem map skenu: nejdřív naskenovaná podle naléhavosti, pak nenaskenovaná podle čísla.
function SprayDronePlannerScreen:getScanOverviewRows()
    if self.scanOverviewRows ~= nil and g_time < (self.scanOverviewTime or 0) then
        return self.scanOverviewRows
    end
    local farmId = self.vehicle:getOwnerFarmId()
    local now = SprayDroneScanMap.getNow()
    local rows = {}
    for _, field in ipairs(g_fieldManager:getFields()) do
        local id = field:getId()
        local owner = field:getOwner()
        if id ~= nil and owner ~= FarmlandManager.NO_OWNER_FARM_ID and g_currentMission.accessHandler:canFarmAccessOtherId(farmId, owner) then
            local row = { field = field, id = id, name = field:getName() }
            local map = SprayDroneScanMap.getMap(farmId, id)
            if map ~= nil then
                row.shares = SprayDroneScanOverlay.getShares(map)
                row.age = SprayDroneScanMap.getAgeHours(map, now)
            end
            table.insert(rows, row)
        end
    end
    table.sort(rows, function(a, b)
        if (a.shares ~= nil) ~= (b.shares ~= nil) then
            return a.shares ~= nil
        elseif a.shares ~= nil and math.abs(a.shares.urgency - b.shares.urgency) > 0.0001 then
            return a.shares.urgency > b.shares.urgency
        end
        return a.id < b.id
    end)
    self.scanOverviewRows = rows
    self.scanOverviewTime = g_time + SprayDroneScanOverlay.OVERVIEW_REFRESH_TIME
    return rows
end

