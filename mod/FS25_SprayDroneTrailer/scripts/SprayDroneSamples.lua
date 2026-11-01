-- Vzorkovací dron AIRASI v kufru (docs/DRON.md, „Vzorkovací dron AIRASI (kufr)“; docs/PLAN-airasi-kufr.md F3): varianta dronu
-- s drone#sampler v profilu portable (objects/droneCase/samplerCase.xml). Mise = body mřížky uvnitř pole s hustotou PF
-- (soilMap:getNumSoilSamplesPerHa, rozestup sqrt(10000 / n) m), body s už odebraným nebo odkrytým vzorkem se vynechají podle mapy
-- pokrytí PF (coverMap: sampledValue = odebráno, čeká na laboratoř; 2..maxValue = odkryto). Vlastní evidenci bodů nevede: stav je v PF.
--
-- Dávka = 1..capacity bodů (kolik pojme dron a zbývá v bedničce): přelet (SprayDroneStation.getTransit), nad bodem sestup na
-- sampler#height, výsun sondy, výdrž, odběr (server: coverMap:analyseArea kruhem SAMPLE_RADIUS jako ISARIA), zasunutí, výstup;
-- domů přeletem a přistáním jako sken. Po přistání jdou vzorky z dronu do bedničky (boxCapacity), plná bednička další misi nespustí.
-- Odeslání (akce B u kufru, tlačítko v plánovači) = soilMap:analyseSoilSamples(farmId, n); cenu účtuje PF po analýze.
-- Bez PF je sada v obchodě skrytá (SprayDroneStoreCategories) a kufr misi odmítne.
--
-- Porost: bod jde odebrat jen na nízkém porostu (isLowCrop: holá půda, sklizeno, zaseto, 1. a 2. stav růstu); body ve vysokém porostu se
-- v plánovači ukážou jinou barvou a dron je přeskočí. Body: automatické (mřížka, nastavení samplerAuto) a naklikané v plánovači (levý klik
-- přidá, pravý odebere i bod mřížky); spec.samplerPicks[pole] = { added, removed }, ukládá se s kufrem a jde eventem SprayDroneSamplePointsEvent.
-- Krabičky: bednička má N přihrádek (uzly sampleSlotN s dětmi …Empty / …Full), dron nese 1–2 krabičky (droneSampleBoxN). Před letem si dron
-- vezme prázdné (samplerBoxes), odběr je plní (samplesCarried), po přistání jdou plné do přihrádek (sampleBox), odeslání je vyprázdní.

source(g_currentModDirectory .. "scripts/events/SprayDroneSamplePointsEvent.lua")

SprayDroneSamples = {}

-- poloměr odběru jako vzorkovač ISARIA (PF vehicles/fritzmeier/isariaScout.xml, soilSampler#radius): kruh pokryje celý čtverec mřížky
SprayDroneSamples.SAMPLE_RADIUS = 32.5
SprayDroneSamples.CIRCLE_STEPS = 20
-- PF bez getNumSoilSamplesPerHa (hodnota ověřená ve hře 2026-10-29: 5,197)
SprayDroneSamples.DEFAULT_PER_HA = 5.2
SprayDroneSamples.BOX_BITS = 5
SprayDroneSamples.CARRY_BITS = 2
-- posuv sondy droneProbe dolů, když ho XML (vehicle.sprayDroneCase#probeTravel) neuvádí
SprayDroneSamples.PROBE_TRAVEL = 0.25
-- nízký porost: nejvýš tento stav růstu (1 = zaseto, 2 = první viditelná fáze greenSmall u všech vanilla polních plodin; od 3. má
-- kukuřice greenMiddle ~1 m a obilí s řepkou rychle rostou), a to jen se jménem stavu invisible / greenSmall (trvalé kultury jako banán,
-- réva nebo olivy mají v 1. a 2. stavu dospělé rostliny)
SprayDroneSamples.LOW_GROWTH_MAX = 2
SprayDroneSamples.LOW_STATE_NAMES = { "invisible", "greensmall" }
-- naklikané body: nejvýš tolik přidaných i odebraných bodů mřížky na pole, nový bod nejblíž tolik m od jiného
SprayDroneSamples.MAX_PICKS = 255
SprayDroneSamples.PICK_MIN_GAP = 4
-- obrys oblasti odběrů v plánovači: kruh odběru kolem bodu po tolika úsečkách
SprayDroneSamples.OUTLINE_STEPS = 32
-- stavy přihrádky bedničky a krabičky v dronu
SprayDroneSamples.SLOT_NONE = 0
SprayDroneSamples.SLOT_EMPTY = 1
SprayDroneSamples.SLOT_FULL = 2
-- víčko bedničky po změně počtu vzorků zůstane otevřené tolik ms
SprayDroneSamples.LID_OPEN_TIME = 3000
SprayDroneSamples.LID_SPEED = 2
-- náhled v plánovači: nejvýš tolik dávek se plánuje skutečnými přelety, zbytek se odhadne
SprayDroneSamples.PREVIEW_BATCHES = 12

SprayDroneSamples.PHASE_EXTEND = 1
SprayDroneSamples.PHASE_HOLD = 2
SprayDroneSamples.PHASE_RETRACT = 3

-- statusy konce mise na konci rozsahu STATUS_NUM_BITS (5 bitů), ať se nepotkají s dalšími statusy SprayDroneStation
SprayDroneSamples.STATUS_DONE = 28
SprayDroneSamples.STATUS_BOX_FULL = 29
SprayDroneSamples.STATUS_NO_PF = 30
SprayDroneSamples.STATUS_TALL = 26
SprayDroneStation.STATUS_TEXTS[SprayDroneSamples.STATUS_TALL] = "sdt_status_samplesTall"
SprayDroneStation.STATUS_TEXTS[SprayDroneSamples.STATUS_DONE] = "sdt_status_samplesDone"
SprayDroneStation.STATUS_TEXTS[SprayDroneSamples.STATUS_BOX_FULL] = "sdt_status_samplesBoxFull"
SprayDroneStation.STATUS_TEXTS[SprayDroneSamples.STATUS_NO_PF] = "sdt_status_samplesNoPF"

local function getSpec(self)
    return self[SprayDroneStation.SPEC_NAME]
end

function SprayDroneSamples.getIsSampler(self)
    local spec = self ~= nil and self[SprayDroneStation.SPEC_NAME] or nil
    return spec ~= nil and spec.isSamplerDrone == true
end

---------------------------------------------------------------------------------------------------
-- XML, uložení

function SprayDroneSamples.registerXMLPaths(schema, droneKey)
    schema:register(XMLValueType.BOOL, droneKey .. "#sampler", "Vzorkovací dron (AIRASI): mise = odběr vzorků půdy PF v bodech pole", false)
    schema:register(XMLValueType.INT, droneKey .. ".sampler#capacity", "Kolik vzorků dron unese za jeden let", 2)
    schema:register(XMLValueType.INT, droneKey .. ".sampler#boxCapacity", "Kolik vzorků pojme bednička v kufru", 8)
    schema:register(XMLValueType.FLOAT, droneKey .. ".sampler#height", "Výška kořene dronu nad terénem při odběru (m)", 0.05)
    schema:register(XMLValueType.FLOAT, droneKey .. ".sampler#holdTime", "Jak dlouho je sonda v zemi (s)", 3)
    schema:register(XMLValueType.FLOAT, droneKey .. ".sampler#probeTime", "Výsun i zasunutí sondy (s)", 0.8)
    schema:register(XMLValueType.FLOAT, droneKey .. ".sampler#probeTravel", "Posuv vnější trubky sondy <prefix>Probe dolů (m)", 0.14)
    schema:register(XMLValueType.FLOAT, droneKey .. ".sampler#midTravel", "Posuv každého mezistupně <prefix>ProbeMid, ProbeMid2 dolů vůči rodiči (m)", 0)
    schema:register(XMLValueType.FLOAT, droneKey .. ".sampler#tipTravel", "Posuv hrotu <prefix>ProbeTip dolů vůči rodiči (m)", 0.16)
    schema:register(XMLValueType.FLOAT, "vehicle.sprayDroneCase#probeTravel", "Posuv sondy droneProbe dolů při odběru (m)", SprayDroneSamples.PROBE_TRAVEL)
end

function SprayDroneSamples.registerSavegamePaths(savegame, saveKey)
    savegame:register(XMLValueType.INT, saveKey .. "#samples", "Vzorky půdy v bedničce kufru AIRASI (i ty, co byly při uložení v dronu)")
    savegame:register(XMLValueType.INT, saveKey .. ".samplePoints(?)#fieldId", "Pole s naklikanými body odběru")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".samplePoints(?).added(?)#x", "Naklikaný bod odběru x")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".samplePoints(?).added(?)#z", "Naklikaný bod odběru z")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".samplePoints(?).removed(?)#x", "Odebraný bod mřížky x")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".samplePoints(?).removed(?)#z", "Odebraný bod mřížky z")
end

-- Parametry vzorkovače z bloku varianty dronu (v loadVariantParameters, před applyMissionMode).
function SprayDroneSamples.loadParameters(self, xml, droneKey)
    local spec = getSpec(self)
    spec.isSamplerDrone = droneKey ~= nil and xml:getValue(droneKey .. "#sampler", false)
    if not spec.isSamplerDrone then
        return
    end
    local key = droneKey .. ".sampler"
    spec.sampler = {
        capacity = math.clamp(xml:getValue(key .. "#capacity", 2), 1, 2 ^ SprayDroneSamples.CARRY_BITS - 1),
        boxCapacity = math.clamp(xml:getValue(key .. "#boxCapacity", 8), 1, 2 ^ SprayDroneSamples.BOX_BITS - 1),
        height = xml:getValue(key .. "#height", 0.05),
        holdTime = xml:getValue(key .. "#holdTime", 3),
        probeTime = math.max(xml:getValue(key .. "#probeTime", 0.8), 0.05),
        probeTravel = xml:getValue(key .. "#probeTravel", 0.14),
        midTravel = xml:getValue(key .. "#midTravel", 0),
        tipTravel = xml:getValue(key .. "#tipTravel", 0.16),
        caseProbeTravel = xml:getValue("vehicle.sprayDroneCase#probeTravel", SprayDroneSamples.PROBE_TRAVEL)
    }
    SprayDroneSamples.applyModelCapacity(spec)
    spec.sampleBox = spec.sampleBox or 0
    spec.samplesCarried = 0
    spec.samplerBoxes = 0
    spec.samplerPicks = spec.samplerPicks or {}
    spec.probeOut = false
end

-- Kapacity podle modelu: počet přihrádek sampleSlotN a krabiček droneSampleBoxN (když model uzly má), jinak z XML.
function SprayDroneSamples.applyModelCapacity(spec)
    local v = spec.samplerVisuals
    if v == nil or spec.sampler == nil then
        return
    end
    if #v.slots > 0 then
        spec.sampler.boxCapacity = math.min(#v.slots, 2 ^ SprayDroneSamples.BOX_BITS - 1)
    end
    if #v.droneBoxes > 0 then
        spec.sampler.capacity = math.min(#v.droneBoxes, 2 ^ SprayDroneSamples.CARRY_BITS - 1)
    end
    spec.sampleBox = math.min(spec.sampleBox or 0, spec.sampler.boxCapacity)
end

function SprayDroneSamples.loadFromSavegame(self, xmlFile, saveKey)
    local spec = getSpec(self)
    if not spec.isSamplerDrone then
        return
    end
    -- kapacitu podle modelu zná až load (uzly přihrádek), tam se počet ořízne znovu
    spec.sampleBox = math.clamp(xmlFile:getValue(saveKey .. "#samples", 0), 0, 2 ^ SprayDroneSamples.BOX_BITS - 1)
    spec.samplerPicks = {}
    xmlFile:iterate(saveKey .. ".samplePoints", function(_, fieldKey)
        local fieldId = xmlFile:getValue(fieldKey .. "#fieldId")
        local picks = SprayDroneSamples.newPicks()
        for _, kind in ipairs({ "added", "removed" }) do
            xmlFile:iterate(fieldKey .. "." .. kind, function(_, pointKey)
                local x, z = xmlFile:getValue(pointKey .. "#x"), xmlFile:getValue(pointKey .. "#z")
                if x ~= nil and z ~= nil then
                    SprayDroneSamples.putPick(picks, kind, x, z)
                end
            end)
        end
        if fieldId ~= nil and not SprayDroneSamples.isPicksEmpty(picks) then
            spec.samplerPicks[fieldId] = picks
        end
    end)
end

function SprayDroneSamples.saveToXMLFile(self, xmlFile, key)
    local spec = getSpec(self)
    if not spec.isSamplerDrone then
        return
    end
    -- dron se po načtení vrací do kufru (resumeMissionAfterLoad), vzorky z něj jsou už v bedničce
    xmlFile:setValue(key .. "#samples", math.min(spec.sampleBox + spec.samplesCarried, spec.sampler.boxCapacity))
    local fieldIds = {}
    for fieldId, picks in pairs(spec.samplerPicks) do
        if not SprayDroneSamples.isPicksEmpty(picks) then
            table.insert(fieldIds, fieldId)
        end
    end
    table.sort(fieldIds)
    for i, fieldId in ipairs(fieldIds) do
        local fieldKey = string.format("%s.samplePoints(%d)", key, i - 1)
        xmlFile:setValue(fieldKey .. "#fieldId", fieldId)
        local picks = spec.samplerPicks[fieldId]
        for j, p in ipairs(picks.added) do
            xmlFile:setValue(string.format("%s.added(%d)#x", fieldKey, j - 1), p.x)
            xmlFile:setValue(string.format("%s.added(%d)#z", fieldKey, j - 1), p.z)
        end
        for j, p in ipairs(SprayDroneSamples.getRemovedList(picks)) do
            xmlFile:setValue(string.format("%s.removed(%d)#x", fieldKey, j - 1), p.x)
            xmlFile:setValue(string.format("%s.removed(%d)#z", fieldKey, j - 1), p.z)
        end
    end
end

function SprayDroneSamples.writeStream(self, streamId)
    local spec = getSpec(self)
    if spec.isSamplerDrone then
        streamWriteUIntN(streamId, spec.sampleBox, SprayDroneSamples.BOX_BITS)
        streamWriteUIntN(streamId, spec.samplesCarried, SprayDroneSamples.CARRY_BITS)
        streamWriteUIntN(streamId, spec.samplerBoxes, SprayDroneSamples.CARRY_BITS)
        streamWriteBool(streamId, spec.probeOut)
    end
end

function SprayDroneSamples.readStream(self, streamId)
    local spec = getSpec(self)
    if spec.isSamplerDrone then
        local box = streamReadUIntN(streamId, SprayDroneSamples.BOX_BITS)
        if box ~= spec.sampleBox then
            spec.sampleBox = box
            SprayDroneStation.markRouteDirty(self)
        end
        spec.samplesCarried = streamReadUIntN(streamId, SprayDroneSamples.CARRY_BITS)
        spec.samplerBoxes = streamReadUIntN(streamId, SprayDroneSamples.CARRY_BITS)
        spec.probeOut = streamReadBool(streamId)
    end
end

-- Naklikané body všech polí při připojení klienta (onWriteStream / onReadStream vozidla).
function SprayDroneSamples.writeInitialStream(self, streamId)
    local spec = getSpec(self)
    if not spec.isSamplerDrone then
        return
    end
    local fieldIds = {}
    for fieldId, picks in pairs(spec.samplerPicks) do
        if not SprayDroneSamples.isPicksEmpty(picks) then
            table.insert(fieldIds, fieldId)
        end
    end
    streamWriteUInt16(streamId, #fieldIds)
    for _, fieldId in ipairs(fieldIds) do
        SprayDroneSamplePointsEvent.writePicks(streamId, fieldId, spec.samplerPicks[fieldId])
    end
end

function SprayDroneSamples.readInitialStream(self, streamId)
    local spec = getSpec(self)
    if not spec.isSamplerDrone then
        return
    end
    for _ = 1, streamReadUInt16(streamId) do
        local fieldId, picks = SprayDroneSamplePointsEvent.readPicks(streamId)
        spec.samplerPicks[fieldId] = picks
    end
end

---------------------------------------------------------------------------------------------------
-- body pole a stav v Precision Farming

-- Rozestup mřížky (m) z počtu vzorků na hektar.
function SprayDroneSamples.getSpacing(perHa)
    return math.sqrt(10000 / math.max(perHa or SprayDroneSamples.DEFAULT_PER_HA, 0.1))
end

-- Body mřížky uvnitř polygonu: středy čtverců světové mřížky rozestupu spacing (stejné body při každém výpočtu, nezávisle na
-- tvaru pole). Pole menší než čtverec mřížky dostane jeden bod v těžišti vrcholů, když leží uvnitř.
function SprayDroneSamples.buildGrid(poly, spacing)
    local points = {}
    if poly == nil or #poly < 3 then
        return points
    end
    local minX, maxX, minZ, maxZ = math.huge, -math.huge, math.huge, -math.huge
    local cx, cz = 0, 0
    for _, p in ipairs(poly) do
        minX, maxX, minZ, maxZ = math.min(minX, p.x), math.max(maxX, p.x), math.min(minZ, p.z), math.max(maxZ, p.z)
        cx, cz = cx + p.x, cz + p.z
    end
    for i = math.floor(minX / spacing), math.ceil(maxX / spacing) do
        local x = (i + 0.5) * spacing
        for j = math.floor(minZ / spacing), math.ceil(maxZ / spacing) do
            local z = (j + 0.5) * spacing
            if SprayDroneRoute.isPointInPolygon(poly, x, z) then
                table.insert(points, { x = x, z = z })
            end
        end
    end
    if #points == 0 then
        cx, cz = cx / #poly, cz / #poly
        if SprayDroneRoute.isPointInPolygon(poly, cx, cz) then
            table.insert(points, { x = cx, z = cz })
        end
    end
    return points
end

function SprayDroneSamples.getPerHa(pf)
    local soilMap = pf ~= nil and pf.soilMap or nil
    if soilMap ~= nil and soilMap.getNumSoilSamplesPerHa ~= nil then
        local ok, value = pcall(soilMap.getNumSoilSamplesPerHa, soilMap)
        if ok and type(value) == "number" and value > 0 then
            return value
        end
    end
    return SprayDroneSamples.DEFAULT_PER_HA
end

function SprayDroneSamples.getPrice(pf)
    local soilMap = pf ~= nil and pf.soilMap or nil
    if soilMap ~= nil and soilMap.getPricePerSoilSample ~= nil then
        local ok, value = pcall(soilMap.getPricePerSoilSample, soilMap)
        if ok and type(value) == "number" then
            return value
        end
    end
    return 0
end

-- Je v bodě vzorek odebraný (čeká na laboratoř) nebo už odkrytý? Čte bitovou mapu coverMap přímo (sampledValue = odebráno, 2..maxValue
-- = odkryto, jako PF CoverMap:getIsUncoveredAtBitVectorPos); bez ní getIsUncoveredAtPos.
function SprayDroneSamples.getIsSampled(pf, x, z)
    local cm = pf ~= nil and pf.coverMap or nil
    if cm == nil then
        return false
    end
    local size = g_currentMission ~= nil and g_currentMission.terrainSize or nil
    if cm.bitVectorMap ~= nil and cm.sizeX ~= nil and size ~= nil and getBitVectorMapPoint ~= nil then
        local px = math.floor((x + size * 0.5) / size * cm.sizeX)
        local pz = math.floor((z + size * 0.5) / size * (cm.sizeY or cm.sizeX))
        local ok, value = pcall(getBitVectorMapPoint, cm.bitVectorMap, px, pz, cm.firstChannel or 1, cm.numChannels or 4)
        if ok and type(value) == "number" then
            return value == cm.sampledValue or (value > 1 and value <= (cm.maxValue or 7))
        end
    end
    if cm.getIsUncoveredAtPos ~= nil then
        local ok, value = pcall(cm.getIsUncoveredAtPos, cm, x, z)
        return ok and value == true
    end
    return false
end

---------------------------------------------------------------------------------------------------
-- porost

-- Je porost nízký, takže dron dosedne a sonda dosáhne na půdu? Čistá funkce nad stavem plodiny: fruitType = popis plodiny
-- (FruitTypeDesc: numGrowthStates, cutState, cutStates, mulchedState, rolledCutState, preparedGrowthState, growthStateToName) nebo nil,
-- growthState = stav foliage v bodě (0 = nic). Nízké: holá půda, obděláno, strniště a sklizeno (bez plodiny nebo stav isCut, mulč,
-- svinutá posečená tráva, posečená nať), plodina bez růstu, zaseto a první viditelná fáze (LOW_GROWTH_MAX, jen stavy invisible / greenSmall).
function SprayDroneSamples.isLowCrop(fruitType, growthState)
    if fruitType == nil or growthState == nil or growthState <= 0 then
        return true
    end
    if (fruitType.numGrowthStates or 0) <= 0 then
        return true
    end
    if growthState == fruitType.cutState or (fruitType.cutStates ~= nil and fruitType.cutStates[growthState] == true) then
        return true
    end
    if growthState == fruitType.mulchedState or growthState == fruitType.rolledCutState or growthState == fruitType.preparedGrowthState then
        return true
    end
    if growthState > SprayDroneSamples.LOW_GROWTH_MAX then
        return false
    end
    local name = fruitType.growthStateToName ~= nil and fruitType.growthStateToName[growthState] or nil
    if name == nil then
        return true
    end
    name = string.lower(name)
    for _, prefix in ipairs(SprayDroneSamples.LOW_STATE_NAMES) do
        if string.sub(name, 1, #prefix) == prefix then
            return true
        end
    end
    return false
end

-- Plodina a stav růstu v bodě (FSDensityMapUtil); nil, 0 bez plodiny.
function SprayDroneSamples.getCropAt(x, z)
    if FSDensityMapUtil == nil or FSDensityMapUtil.getFruitTypeIndexAtWorldPos == nil then
        return nil, 0
    end
    local ok, fruitIndex, growthState = pcall(FSDensityMapUtil.getFruitTypeIndexAtWorldPos, x, z)
    if not ok or fruitIndex == nil or fruitIndex == 0 or g_fruitTypeManager == nil then
        return nil, 0
    end
    return g_fruitTypeManager:getFruitTypeByIndex(fruitIndex), growthState or 0
end

function SprayDroneSamples.getIsTallAt(x, z)
    return not SprayDroneSamples.isLowCrop(SprayDroneSamples.getCropAt(x, z))
end

---------------------------------------------------------------------------------------------------
-- naklikané body (čisté funkce nad picks = { added = { {x, z} }, removed = { [klíč] = {x, z} } }, klíč podle getKey)

function SprayDroneSamples.getKey(x, z)
    return string.format("%.0f:%.0f", x, z)
end

function SprayDroneSamples.newPicks()
    return { added = {}, removed = {} }
end

function SprayDroneSamples.isPicksEmpty(picks)
    return picks == nil or (#picks.added == 0 and next(picks.removed) == nil)
end

-- Bod do added nebo removed (načtení, síť); nad MAX_PICKS se zahodí.
function SprayDroneSamples.putPick(picks, kind, x, z)
    if kind == "added" then
        if #picks.added < SprayDroneSamples.MAX_PICKS then
            table.insert(picks.added, { x = x, z = z })
        end
    elseif SprayDroneSamples.countRemoved(picks) < SprayDroneSamples.MAX_PICKS then
        picks.removed[SprayDroneSamples.getKey(x, z)] = { x = x, z = z }
    end
end

function SprayDroneSamples.countRemoved(picks)
    local n = 0
    for _ in pairs(picks.removed) do
        n = n + 1
    end
    return n
end

-- Odebrané body mřížky jako seznam seřazený podle klíče (stejné pořadí v savu i na síti).
function SprayDroneSamples.getRemovedList(picks)
    local keys = {}
    for key in pairs(picks.removed) do
        table.insert(keys, key)
    end
    table.sort(keys)
    local list = {}
    for i, key in ipairs(keys) do
        list[i] = picks.removed[key]
    end
    return list
end

function SprayDroneSamples.copyPicks(picks)
    local copy = SprayDroneSamples.newPicks()
    if picks ~= nil then
        for _, p in ipairs(picks.added) do
            table.insert(copy.added, { x = p.x, z = p.z })
        end
        for key, p in pairs(picks.removed) do
            copy.removed[key] = { x = p.x, z = p.z }
        end
    end
    return copy
end

-- Body pole: s auto body mřížky bez odebraných, pak naklikané (custom = true). Každý bod má klíč.
function SprayDroneSamples.mergePoints(grid, picks, auto)
    local list = {}
    local removed = picks ~= nil and picks.removed or {}
    if auto then
        for _, p in ipairs(grid or {}) do
            local key = SprayDroneSamples.getKey(p.x, p.z)
            if removed[key] == nil then
                table.insert(list, { x = p.x, z = p.z, key = key })
            end
        end
    end
    for _, p in ipairs(picks ~= nil and picks.added or {}) do
        table.insert(list, { x = p.x, z = p.z, key = SprayDroneSamples.getKey(p.x, p.z), custom = true })
    end
    return list
end

-- Nejbližší bod seznamu do radius m od (x, z): index a bod, nebo nil.
function SprayDroneSamples.findNearest(points, x, z, radius)
    local best, bestD = nil, radius * radius
    for i, p in ipairs(points) do
        local d = (p.x - x) ^ 2 + (p.z - z) ^ 2
        if d <= bestD then
            best, bestD = i, d
        end
    end
    if best == nil then
        return nil, nil
    end
    return best, points[best]
end

-- Přidání bodu do picks (mění je): s auto body vrátí odebraný bod mřížky do radius m, jinak přidá nový, když do PICK_MIN_GAP m žádný
-- není. Vrací true, nebo false a klíč textu důvodu.
function SprayDroneSamples.addPick(picks, grid, auto, x, z, radius)
    if auto then
        local removed = SprayDroneSamples.getRemovedList(picks)
        local _, p = SprayDroneSamples.findNearest(removed, x, z, math.max(radius, SprayDroneSamples.PICK_MIN_GAP))
        if p ~= nil then
            picks.removed[SprayDroneSamples.getKey(p.x, p.z)] = nil
            return true
        end
    end
    local current = SprayDroneSamples.mergePoints(grid, picks, auto)
    if SprayDroneSamples.findNearest(current, x, z, SprayDroneSamples.PICK_MIN_GAP) ~= nil then
        return false, "sdt_sampler_pickExists"
    end
    if #picks.added >= SprayDroneSamples.MAX_PICKS then
        return false, "sdt_sampler_pickMax"
    end
    table.insert(picks.added, { x = x, z = z })
    return true
end

-- Odebrání bodu nejblíž (x, z) do radius m (mění picks): naklikaný zmizí, bod mřížky se zapíše mezi odebrané.
function SprayDroneSamples.removePick(picks, grid, auto, x, z, radius)
    local current = SprayDroneSamples.mergePoints(grid, picks, auto)
    local _, p = SprayDroneSamples.findNearest(current, x, z, radius)
    if p == nil then
        return false, "sdt_sampler_pickNone"
    end
    if p.custom then
        for i, a in ipairs(picks.added) do
            if SprayDroneSamples.getKey(a.x, a.z) == p.key then
                table.remove(picks.added, i)
                break
            end
        end
    elseif SprayDroneSamples.countRemoved(picks) < SprayDroneSamples.MAX_PICKS then
        picks.removed[p.key] = { x = p.x, z = p.z }
    else
        return false, "sdt_sampler_pickMax"
    end
    return true
end

---------------------------------------------------------------------------------------------------
-- body vybraného pole

-- Mřížka vybraného pole (pamatuje se pro pole a rozestup), nebo nil bez pole.
function SprayDroneSamples.getGrid(self)
    local spec = getSpec(self)
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field == nil then
        return nil, nil
    end
    local spacing = SprayDroneSamples.getSpacing(SprayDroneSamples.getPerHa(SprayDroneStation.getPrecisionFarming()))
    local grid = spec.samplerGrid
    if grid == nil or grid.fieldId ~= spec.fieldId or math.abs(grid.spacing - spacing) > 0.01 then
        grid = { fieldId = spec.fieldId, spacing = spacing, points = SprayDroneSamples.buildGrid(SprayDroneRoute.getPolygon(field), spacing) }
        spec.samplerGrid = grid
    end
    return grid.points, field
end

-- Je bod v dosahu kufru: do dosahu z baterie a v signálu (kruh rádia kufru, relé i s výsečí směrové tyče; SprayDroneLink.getSignalCircles)?
function SprayDroneSamples.getIsInReach(self, x, z, hx, hz, range, circles)
    if hx == nil then
        hx, hz = SprayDroneStation.getHomePosition(self)
        range = SprayDroneStation.updateRange(self)
        circles = SprayDroneLink ~= nil and SprayDroneLink.getSignalCircles(self) or nil
    end
    return MathUtil.vector2Length(x - hx, z - hz) <= range and (circles == nil or SprayDroneLink.isInCircles(circles, x, z))
end

-- Body vybraného pole se stavem: { points = { {x, z, key, custom, sampled, tall, far} }, total, sampled, tall, far, pending = {body k odběru} }.
-- Body jsou mřížka (nastavení samplerAuto) a naklikané (samplerPicks). Body, kde odběr neprošel (cizí pozemek, mimo plochu pole v PF), jsou
-- v samplerSkip. Pořadí: odebráno, vysoký porost, mimo dosah, k odběru.
function SprayDroneSamples.getPoints(self)
    local spec = getSpec(self)
    local result = { points = {}, total = 0, sampled = 0, pending = {}, far = 0, tall = 0 }
    local grid = SprayDroneSamples.getGrid(self)
    if grid == nil then
        return result
    end
    local pf = SprayDroneStation.getPrecisionFarming()
    local hx, hz = SprayDroneStation.getHomePosition(self)
    local range = SprayDroneStation.updateRange(self)
    local circles = SprayDroneLink ~= nil and SprayDroneLink.getSignalCircles(self) or nil
    local skip = spec.samplerSkip or {}
    local points = SprayDroneSamples.mergePoints(grid, spec.samplerPicks[spec.fieldId], (spec.samplerAuto or 1) > 0)
    for _, p in ipairs(points) do
        p.sampled = skip[p.key] == true or SprayDroneSamples.getIsSampled(pf, p.x, p.z)
        p.tall = not p.sampled and SprayDroneSamples.getIsTallAt(p.x, p.z)
        p.far = not p.sampled and not p.tall and not SprayDroneSamples.getIsInReach(self, p.x, p.z, hx, hz, range, circles)
        table.insert(result.points, p)
        result.total = result.total + 1
        if p.sampled then
            result.sampled = result.sampled + 1
        elseif p.tall then
            result.tall = result.tall + 1
        elseif p.far then
            result.far = result.far + 1
        else
            table.insert(result.pending, p)
        end
    end
    return result
end

-- Proč bod (x, z) nejde přidat (klíč textu), nil = jde: bez vybraného pole, mimo pole, mimo dosah kufru.
function SprayDroneSamples.getPickWarning(self, x, z)
    local spec = getSpec(self)
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field == nil then
        return "sdt_sampler_pickNoField"
    end
    if not SprayDroneRoute.isPointInPolygon(SprayDroneRoute.getPolygon(field), x, z) then
        return "sdt_sampler_pickOutside"
    end
    if not SprayDroneSamples.getIsInReach(self, x, z) then
        return "sdt_sampler_pickFar"
    end
    return nil
end

-- Vrací nil a případně klíč informace (bod ve vysokém porostu), nebo klíč varování. Změna jde eventem na server a ostatním klientům.
function SprayDroneSamples.requestPick(self, x, z, add, radius)
    local spec = getSpec(self)
    if not spec.isSamplerDrone then
        return "sdt_sampler_pickNoField"
    end
    if add then
        local warning = SprayDroneSamples.getPickWarning(self, x, z)
        if warning ~= nil then
            return warning
        end
    end
    local grid = SprayDroneSamples.getGrid(self)
    if grid == nil then
        return "sdt_sampler_pickNoField"
    end
    local picks = SprayDroneSamples.copyPicks(spec.samplerPicks[spec.fieldId])
    local auto = (spec.samplerAuto or 1) > 0
    local ok, reason
    if add then
        ok, reason = SprayDroneSamples.addPick(picks, grid, auto, x, z, radius or SprayDroneSamples.PICK_MIN_GAP)
    else
        ok, reason = SprayDroneSamples.removePick(picks, grid, auto, x, z, radius or SprayDroneSamples.PICK_MIN_GAP)
    end
    if not ok then
        return reason
    end
    SprayDroneSamples.setPicks(self, spec.fieldId, picks)
    SprayDroneSound.noteAction(string.format("vzorkovač %s: bod %s na (%.0f, %.0f), pole %d, přidaných %d, odebraných z mřížky %d",
        tostring(self.id), add and "přidán" or "odebrán", x, z, spec.fieldId, #picks.added, SprayDroneSamples.countRemoved(picks)))
    if add and SprayDroneSamples.getIsTallAt(x, z) then
        return nil, "sdt_sampler_pickTall"
    end
    return nil
end

-- Naklikané body pole fieldId (prázdné = smazat); jde eventem na server a od něj ke všem klientům.
function SprayDroneSamples.setPicks(self, fieldId, picks, noEventSend)
    local spec = getSpec(self)
    SprayDroneSamplePointsEvent.sendEvent(self, fieldId, picks, noEventSend)
    if SprayDroneSamples.isPicksEmpty(picks) then
        spec.samplerPicks[fieldId] = nil
    else
        spec.samplerPicks[fieldId] = SprayDroneSamples.copyPicks(picks)
    end
    SprayDroneStation.markRouteDirty(self)
end

-- n bodů dávky: nejbližší k domovu, pak vždy nejbližší k předchozímu. Vrací dávku a zbytek (nové tabulky).
function SprayDroneSamples.pickBatch(pending, hx, hz, n)
    local rest = {}
    for i, p in ipairs(pending) do
        rest[i] = p
    end
    local batch = {}
    local x, z = hx, hz
    while #batch < n and #rest > 0 do
        local best, bestD = 1, math.huge
        for i, p in ipairs(rest) do
            local d = (p.x - x) ^ 2 + (p.z - z) ^ 2
            if d < bestD then
                best, bestD = i, d
            end
        end
        local p = table.remove(rest, best)
        table.insert(batch, p)
        x, z = p.x, p.z
    end
    return batch, rest
end

-- Kolik vzorků poletí v příští dávce: kapacita dronu, nejvýš kolik je v bedničce prázdných krabiček (krabičky v dronu se počítají
-- jako vzatá přihrádka).
function SprayDroneSamples.getBatchSize(spec)
    local s = spec.sampler
    local inDrone = math.max(spec.samplerBoxes or 0, spec.samplesCarried or 0)
    return math.max(math.min(s.capacity, s.boxCapacity - spec.sampleBox - inDrone), 0)
end

-- Stavy přihrádek bedničky 1..n (SLOT_*): napřed plné (box), pak prázdné místo po krabičkách v dronu (inDrone), zbytek prázdné krabičky.
function SprayDroneSamples.getSlotStates(n, box, inDrone)
    local states = {}
    for i = 1, n do
        if i <= box then
            states[i] = SprayDroneSamples.SLOT_FULL
        elseif i <= box + inDrone then
            states[i] = SprayDroneSamples.SLOT_NONE
        else
            states[i] = SprayDroneSamples.SLOT_EMPTY
        end
    end
    return states
end

-- Stavy krabiček na dronu 1..n (SLOT_*): napřed plné (carried), pak prázdné do počtu vzatých (boxes).
function SprayDroneSamples.getDroneBoxStates(n, boxes, carried)
    local states = {}
    for i = 1, n do
        if i <= carried then
            states[i] = SprayDroneSamples.SLOT_FULL
        elseif i <= boxes then
            states[i] = SprayDroneSamples.SLOT_EMPTY
        else
            states[i] = SprayDroneSamples.SLOT_NONE
        end
    end
    return states
end

-- Před vzletem (server): dron si z bedničky vezme n prázdných krabiček.
function SprayDroneSamples.takeBoxes(self, n)
    local spec = getSpec(self)
    local free = spec.sampler.boxCapacity - spec.sampleBox
    spec.samplerBoxes = math.clamp(n, 0, math.min(free, spec.sampler.capacity))
    spec.samplesCarried = 0
    self:raiseDirtyFlags(spec.dirtyFlag)
end

---------------------------------------------------------------------------------------------------
-- dávka (server)

-- Waypointy dávky z domova přes body batch a zpět, nebo nil a NO_PATH_*. Nad body letí ve výšce postřiku varianty (sprayHeight),
-- mezi body nad překážkou (getHopHeight); waypoint odběru má sample = true.
function SprayDroneSamples.buildPath(self, batch)
    local spec = getSpec(self)
    local s = spec.sampler
    local approach = spec.sprayHeight
    local out, noPath = SprayDroneStation.getTransit(self, batch[1].x, batch[1].z, true)
    if out == nil then
        return nil, noPath
    end
    local wps = {}
    for _, wp in ipairs(out.wps) do
        table.insert(wps, wp)
    end
    local height = out.height
    for i, p in ipairs(batch) do
        if i > 1 then
            local prev = batch[i - 1]
            local h = math.max(approach, SprayDroneStation.getHopHeight(self, prev.x, prev.z, p.x, p.z) or 0)
            if h > approach + 0.05 then
                table.insert(wps, { x = prev.x, z = prev.z, h = h, speed = spec.ascentSpeed })
            end
            table.insert(wps, { x = p.x, z = p.z, h = h, speed = spec.cruiseSpeed })
            if h > approach + 0.05 then
                table.insert(wps, { x = p.x, z = p.z, h = approach, speed = spec.climbSpeed })
            end
            height = math.max(height, h)
        end
        table.insert(wps, { x = p.x, z = p.z, h = s.height, speed = spec.climbSpeed, sample = true })
        table.insert(wps, { x = p.x, z = p.z, h = approach, speed = spec.ascentSpeed })
    end
    local last = batch[#batch]
    local back
    back, noPath = SprayDroneStation.getTransit(self, last.x, last.z, false, nil, nil, { startH = approach })
    if back == nil then
        return nil, noPath
    end
    for _, wp in ipairs(back.wps) do
        table.insert(wps, wp)
    end
    return wps, nil, math.max(height, back.height), (out.length or 0) + (back.length or 0), out.length or 0, back.length or 0
end

-- Čas (s) a spotřeba baterie (s letu) dávky s waypointy wps z domova, i s výdrží nad body a rezervou.
function SprayDroneSamples.getPathCost(self, wps)
    local spec = getSpec(self)
    local s = spec.sampler
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local p = SprayDroneStation.getFlightParams(self, nil, restHeight)
    local pts = { { x = hx, z = hz, h = restHeight } }
    local holds = 0
    for _, wp in ipairs(wps) do
        table.insert(pts, wp)
        if wp.sample then
            holds = holds + 1
        end
    end
    local time, energy = SprayDroneRoute.pathCost(pts, p, 0, 0, 0, p.homeYaw)
    local holdTime = holds * (s.holdTime + 2 * s.probeTime)
    return time + holdTime, energy + holdTime * SprayDroneRoute.drainFactor(p, 0, p.hoverFactor) + p.batteryReserve
end

-- Nejdelší dávka z prvních n bodů pending, na kterou stačí energie battery: waypointy, body, čas, spotřeba, výška, délky; nil a důvod
-- ("noPath" s NO_PATH_*, "battery" = nestačí ani na jeden bod).
function SprayDroneSamples.planBatch(self, pending, n, battery)
    local hx, hz = SprayDroneStation.getHomePosition(self)
    local batch = SprayDroneSamples.pickBatch(pending, hx, hz, n)
    for k = #batch, 1, -1 do
        local part = {}
        for i = 1, k do
            part[i] = batch[i]
        end
        local wps, noPath, height, length, firstOut, firstBack = SprayDroneSamples.buildPath(self, part)
        if wps == nil then
            return nil, "noPath", noPath
        end
        local time, energy = SprayDroneSamples.getPathCost(self, wps)
        if energy <= battery then
            return { wps = wps, points = part, time = time, energy = energy, height = height, length = length, firstOut = firstOut,
                firstBack = firstBack }
        end
    end
    return nil, "battery"
end

-- Místo SprayDroneStation.startNextBatch u vzorkovače (po kontrole pole a počasí, v kontextu dronu).
function SprayDroneSamples.startNextBatch(self)
    local spec = getSpec(self)
    if SprayDroneStation.getPrecisionFarming() == nil then
        SprayDroneStation.endMission(self, SprayDroneSamples.STATUS_NO_PF)
        return
    end
    local n = SprayDroneSamples.getBatchSize(spec)
    if n <= 0 then
        SprayDroneStation.endMission(self, SprayDroneSamples.STATUS_BOX_FULL)
        return
    end
    local points = SprayDroneSamples.getPoints(self)
    if #points.pending == 0 then
        local status = SprayDroneSamples.STATUS_DONE
        if points.tall > 0 then
            status = SprayDroneSamples.STATUS_TALL
        elseif points.far > 0 then
            status = SprayDroneStation.STATUS_OUT_OF_REACH
        end
        SprayDroneStation.endMission(self, status)
        return
    end
    local plan, reason, noPath = nil, "battery", nil
    if spec.droneBattery ~= nil then
        plan, reason, noPath = SprayDroneSamples.planBatch(self, points.pending, n, spec.battery)
    end
    if plan == nil and reason == "noPath" then
        SprayDroneStation.endMission(self, SprayDroneStation.STATUS_NO_AREA_PATH)
        return
    end
    if plan == nil then
        -- nestačí baterie v dronu: s plnou by to šlo -> výměna / nabití jako u postřiku (SprayDroneStation.swapBattery), jinak je bod daleko
        if SprayDroneSamples.planBatch(self, points.pending, 1, spec.batteryCapacity) == nil then
            SprayDroneStation.endMission(self, SprayDroneStation.STATUS_UNREACHABLE)
        elseif not SprayDroneStation.swapBattery(self) then
            local blocker = SprayDroneStation.getChargeBlocker(self)
            if blocker ~= nil then
                SprayDroneStation.endMission(self, blocker)
            end
        end
        return
    end
    local clear, blockedBy = SprayDroneStation.getTakeoffClearance(self)
    if not clear then
        if not spec.waitingForClearance then
            SprayDroneSound.noteAction(string.format("vzorkovač nevzlétne: nad kufrem %s", blockedBy))
        end
        SprayDroneStation.setWaitingForClearance(self, true)
        spec.serviceTimer = SprayDroneStation.RELAY_RETRY_TIME
        return
    end
    SprayDroneStation.setWaitingForClearance(self, false)
    SprayDroneSamples.takeBoxes(self, #plan.points)

    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    spec.batchRelays = {}
    spec.path = plan.wps
    spec.wpIndex = 1
    spec.pos.x, spec.pos.z, spec.pos.h = hx, hz, restHeight
    spec.pos.yaw = SprayDroneStation.getHomeYaw(self)
    spec.speed, spec.yawRate = 0, 0
    spec.airborne = false
    spec.avoidHeight, spec.avoidClimbTo = 0, nil
    spec.returnEnergyTime = -math.huge
    spec.batchHeight = plan.height
    spec.sprayFrom = nil
    spec.batch = spec.batch + 1
    spec.litersPerMeter = 0
    spec.massPerLiter = SprayDroneStation.getMassPerLiter(self)
    spec.sprayTypeIndex = SprayDroneStation.SCAN_TYPE.index
    spec.scanning = false
    spec.sampleHold = nil
    spec.samplerBatchSamples = 0
    spec.weatherCheckTime = g_time + SprayDroneStation.WEATHER_CHECK_TIME
    spec.flightTime, spec.estimatedTime = 0, plan.time
    spec.batteryAtStart, spec.estimatedEnergy = spec.battery, plan.energy
    SprayDroneSound.noteAction(string.format("odběr vzorků pole %d: dávka %d, %d z %d zbývajících bodů, odhad %.0f s, baterie %.0f / %.0f s",
        spec.fieldId, spec.batch, #plan.points, #points.pending, plan.time, plan.energy, spec.battery))
    SprayDroneStation.setState(self, SprayDroneStation.STATE_FLYING)
end

-- Dron došel na waypoint odběru (server, updateFlight): začne výsun sondy.
function SprayDroneSamples.startHold(self, wp)
    local spec = getSpec(self)
    spec.sampleHold = { phase = SprayDroneSamples.PHASE_EXTEND, t = 0, x = wp.x, z = wp.z }
    SprayDroneSamples.setProbeOut(self, true)
end

function SprayDroneSamples.setProbeOut(self, out)
    local spec = getSpec(self)
    if spec.probeOut ~= out then
        spec.probeOut = out
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

-- Výsun, výdrž a zasunutí sondy nad bodem (server, z updateFlight po kontrolách baterie, počasí a signálu). Vrací true, dokud dron
-- stojí; když mise skončila (návrat domů), sondu zasune a pustí let dál.
function SprayDroneSamples.updateHold(self, dt)
    local spec = getSpec(self)
    local hold = spec.sampleHold
    if hold == nil then
        return false
    end
    if spec.state ~= SprayDroneStation.STATE_FLYING then
        spec.sampleHold = nil
        SprayDroneSamples.setProbeOut(self, false)
        return false
    end
    local s = spec.sampler
    hold.t = hold.t + dt * 0.001
    if hold.phase == SprayDroneSamples.PHASE_EXTEND and hold.t >= s.probeTime then
        hold.phase, hold.t = SprayDroneSamples.PHASE_HOLD, 0
    elseif hold.phase == SprayDroneSamples.PHASE_HOLD and hold.t >= s.holdTime then
        SprayDroneSamples.takeSample(self, hold.x, hold.z)
        hold.phase, hold.t = SprayDroneSamples.PHASE_RETRACT, 0
        SprayDroneSamples.setProbeOut(self, false)
    elseif hold.phase == SprayDroneSamples.PHASE_RETRACT and hold.t >= s.probeTime then
        spec.sampleHold = nil
        return false
    end
    spec.speed = 0
    return true
end

-- Odběr v bodě (server): pozemek musí farma smět obdělávat (jako PF SoilSampler:getCanStartSoilSampling), pak coverMap:analyseArea
-- kruhem SAMPLE_RADIUS. Bod, který po odběru v PF pořád není odebraný (mimo plochu pole), se do konce hry přeskakuje.
function SprayDroneSamples.takeSample(self, x, z)
    local spec = getSpec(self)
    local pf = SprayDroneStation.getPrecisionFarming()
    local farmId = self:getOwnerFarmId()
    local farmlandId = g_farmlandManager:getFarmlandIdAtWorldPosition(x, z)
    local owner = farmlandId ~= nil and g_farmlandManager:getFarmlandOwner(farmlandId) or 0
    local allowed = owner ~= 0 and g_currentMission.accessHandler:canFarmAccessOtherId(farmId, owner)
    local ok, err = false, allowed and "" or "cizí pozemek"
    if pf ~= nil and allowed then
        ok, err = pcall(function()
            local Circle = SprayDroneStation.getPFGlobal("DensityMapCircle")
            spec.samplerCircle = spec.samplerCircle or Circle.new()
            spec.samplerCircle:updateFromWorldPosition(x, z, SprayDroneSamples.SAMPLE_RADIUS, SprayDroneSamples.CIRCLE_STEPS)
            pf.coverMap:analyseArea(spec.samplerCircle, nil, farmId, farmlandId)
        end)
        if ok and pf.farmlandStatistics ~= nil then
            pcall(function()
                pf.farmlandStatistics:updateStatistic(farmlandId, "numSoilSamples", 1)
                pf.farmlandStatistics:updateStatistic(farmlandId, "soilSampleCosts", SprayDroneSamples.getPrice(pf))
            end)
        end
    end
    if ok then
        spec.samplerBatchSamples = (spec.samplerBatchSamples or 0) + 1
        spec.samplesCarried = math.min(spec.samplesCarried + 1, 2 ^ SprayDroneSamples.CARRY_BITS - 1)
        spec.samplerBoxes = math.max(spec.samplerBoxes or 0, spec.samplesCarried)
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
    if not ok or not SprayDroneSamples.getIsSampled(pf, x, z) then
        spec.samplerSkip = spec.samplerSkip or {}
        spec.samplerSkip[string.format("%.0f:%.0f", x, z)] = true
    end
    SprayDroneStation.markRouteDirty(self)
    SprayDroneSound.noteAction(string.format("vzorek pole %d na (%.0f, %.0f), pozemek %s: %s %s, v dronu %d", spec.fieldId, x, z,
        tostring(farmlandId), tostring(ok), tostring(err or ""), spec.samplesCarried))
end

-- Dron přistál v kufru (server, updateFlight): vzorky z dronu do bedničky. Pojistka proti smyčce: MAX_IDLE_BATCHES dávek po sobě v běžící
-- misi bez jediného nového vzorku ukončí misi (STATUS_STUCK) s varováním v logu, místo aby dron donekonečna vzlétal a vracel se.
SprayDroneSamples.MAX_IDLE_BATCHES = 2
SprayDroneSamples.STATUS_STUCK = 27
SprayDroneStation.STATUS_TEXTS[SprayDroneSamples.STATUS_STUCK] = "sdt_status_samplesStuck"

function SprayDroneSamples.onLanded(self)
    local spec = getSpec(self)
    if not spec.isSamplerDrone then
        return
    end
    if not spec.missionActive or (spec.samplerBatchSamples or 0) > 0 then
        spec.samplerIdleBatches = 0
    else
        spec.samplerIdleBatches = (spec.samplerIdleBatches or 0) + 1
        if spec.samplerIdleBatches >= SprayDroneSamples.MAX_IDLE_BATCHES then
            Logging.warning("SDT vzorkovač (pole %d): %d dávek po sobě bez vzorku (poslední let %.1f s, status %d), mise končí", spec.fieldId,
                spec.samplerIdleBatches, spec.flightTime or 0, spec.status or 0)
            spec.samplerIdleBatches = 0
            SprayDroneStation.endMission(self, SprayDroneSamples.STATUS_STUCK)
        end
    end
    spec.samplerBatchSamples = 0
    if spec.samplesCarried == 0 and (spec.samplerBoxes or 0) == 0 then
        return
    end
    -- plné krabičky do přihrádek jako plné, nepoužité prázdné zpět jako prázdné
    local unused = math.max((spec.samplerBoxes or 0) - spec.samplesCarried, 0)
    spec.sampleBox = math.min(spec.sampleBox + spec.samplesCarried, spec.sampler.boxCapacity)
    spec.samplesCarried, spec.samplerBoxes = 0, 0
    SprayDroneStation.markRouteDirty(self)
    self:raiseDirtyFlags(spec.dirtyFlag)
    SprayDroneSound.noteAction(string.format("krabičky do bedničky: plných %d / %d, nepoužitých prázdných %d", spec.sampleBox,
        spec.sampler.boxCapacity, unused))
end

-- Odeslání vzorků z bedničky do laboratoře PF (server, příkaz SEND_SAMPLES).
function SprayDroneSamples.sendSamples(self)
    local spec = getSpec(self)
    local pf = SprayDroneStation.getPrecisionFarming()
    local n = spec.isSamplerDrone and spec.sampleBox or 0
    if pf == nil or pf.soilMap == nil or n <= 0 then
        return
    end
    local ok, err = pcall(pf.soilMap.analyseSoilSamples, pf.soilMap, self:getOwnerFarmId(), n)
    if ok then
        spec.sampleBox = 0
        SprayDroneStation.markRouteDirty(self)
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
    SprayDroneSound.noteAction(string.format("odeslání %d vzorků do laboratoře: %s %s", n, tostring(ok), tostring(err or "")))
end

-- Klient: pošle příkaz a ukáže hlášku s počtem a cenou; vrací klíč textu, když není co odeslat.
function SprayDroneSamples.requestSend(self)
    local spec = getSpec(self)
    local pf = SprayDroneStation.getPrecisionFarming()
    if pf == nil then
        return "sdt_sampler_noPF"
    end
    local n = spec.sampleBox or 0
    if n <= 0 then
        return "sdt_sampler_boxEmpty"
    end
    self:sprayDroneCommand(SprayDroneCommandEvent.SEND_SAMPLES, n)
    local price = n * SprayDroneSamples.getPrice(pf)
    g_currentMission:addIngameNotification(FSBaseMission.INGAME_NOTIFICATION_OK,
        string.format(g_i18n:getText("sdt_sampler_sent"), n, g_i18n:formatMoney(price, 0, true, true)))
    return nil
end

-- Proč start mise nejde (startFlight), nil = jde.
function SprayDroneSamples.getStartWarning(self)
    local spec = getSpec(self)
    if SprayDroneStation.getPrecisionFarming() == nil then
        return "sdt_sampler_noPF"
    end
    if SprayDroneSamples.getBatchSize(spec) <= 0 then
        return "sdt_sampler_boxFull"
    end
    local points = spec.routeInfo ~= nil and spec.routeInfo.samplePoints or nil
    if points ~= nil and #points.pending == 0 then
        return SprayDroneSamples.getNoPendingReason(spec, points)
    end
    return nil
end

-- Proč není co odebrat (klíč textu): žádné body (bez automatických), vysoký porost, mimo dosah, nebo hotovo.
function SprayDroneSamples.getNoPendingReason(spec, points)
    if points.total == 0 and (spec.samplerAuto or 1) == 0 then
        return "sdt_sampler_noPoints"
    elseif points.tall > 0 then
        return "sdt_sampler_tallCrop"
    elseif points.far > 0 then
        return "sdt_status_outOfReach"
    end
    return "sdt_status_samplesDone"
end

---------------------------------------------------------------------------------------------------
-- náhled pro plánovač (v kontextu dronu, místo SprayDroneStation.updateRoutePreview)

function SprayDroneSamples.updateRoutePreview(self)
    local spec = getSpec(self)
    local points = SprayDroneSamples.getPoints(self)
    local info = { time = 0, height = spec.transitHeight, tooHigh = false, transits = {}, maxEnergy = 0, transitLength = 0, firstOut = 0,
        firstBack = 0, samplePoints = points }
    info.coverLines = SprayDroneSamples.getCoverageOutline(points.points, SprayDroneSamples.SAMPLE_RADIUS, SprayDroneSamples.OUTLINE_STEPS)
    spec.routeInfo = info
    spec.numBatches = 0
    local size = SprayDroneSamples.getBatchSize(spec)
    if size <= 0 or #points.pending == 0 or SprayDroneStation.getPrecisionFarming() == nil then
        info.boxFull = size <= 0
        return
    end
    -- dávky z bodů, které se ještě vejdou do bedničky; skutečné přelety jen pro prvních PREVIEW_BATCHES, zbytek podle průměru
    local room = spec.sampler.boxCapacity - spec.sampleBox - math.max(spec.samplerBoxes or 0, spec.samplesCarried)
    local pending = points.pending
    local planned, total = 0, math.min(#pending, room)
    local hx, hz = SprayDroneStation.getHomePosition(self)
    while planned < total and spec.numBatches < SprayDroneSamples.PREVIEW_BATCHES do
        local plan, reason, noPath = SprayDroneSamples.planBatch(self, pending, math.min(spec.sampler.capacity, total - planned), spec.batteryCapacity)
        if plan == nil then
            info.noPath = reason == "noPath" and noPath or nil
            break
        end
        if spec.numBatches == 0 then
            info.firstOut, info.firstBack = plan.firstOut, plan.firstBack
        end
        spec.numBatches = spec.numBatches + 1
        planned = planned + #plan.points
        info.time = info.time + plan.time
        info.maxEnergy = math.max(info.maxEnergy, plan.energy)
        info.height = math.max(info.height, plan.height)
        info.transitLength = info.transitLength + plan.length
        local used = {}
        for _, p in ipairs(plan.points) do
            used[p] = true
        end
        local rest = {}
        for _, p in ipairs(pending) do
            if not used[p] then
                table.insert(rest, p)
            end
        end
        pending = rest
    end
    if planned > 0 and planned < total then
        local extra = math.ceil((total - planned) / spec.sampler.capacity)
        info.time = info.time + info.time / spec.numBatches * extra
        info.transitLength = info.transitLength + info.transitLength / spec.numBatches * extra
        spec.numBatches = spec.numBatches + extra
    end
    info.boxLimited = #points.pending > room
    info.serviceTime = spec.numBatches * SprayDroneStation.SERVICE_TIME * 0.001
end

-- Obrys sjednocení kruhů odběru (poloměr radius) kolem bodů: úsečky { x1, z1, x2, z2 } oblouků, které neleží uvnitř jiného kruhu.
-- Čitelnější než kruh u každého bodu (sousední kruhy mřížky se překrývají). Úsek oblouku, který do jiného kruhu vchází, se zkrátí
-- půlením až k průsečíku, aby obrys neměl u průsečíků mezery. Počítá se jen při přepočtu náhledu.
function SprayDroneSamples.getCoverageOutline(points, radius, steps)
    local lines = {}
    local r2 = radius * radius
    for i, p in ipairs(points) do
        local near = {}
        for j, q in ipairs(points) do
            if j ~= i and (q.x - p.x) ^ 2 + (q.z - p.z) ^ 2 < 4 * r2 then
                table.insert(near, q)
            end
        end
        local function isInside(a)
            local x, z = p.x + math.cos(a) * radius, p.z + math.sin(a) * radius
            for _, q in ipairs(near) do
                if (x - q.x) ^ 2 + (z - q.z) ^ 2 < r2 - 1e-3 then
                    return true
                end
            end
            return false
        end
        local function addArc(a1, a2)
            table.insert(lines, { x1 = p.x + math.cos(a1) * radius, z1 = p.z + math.sin(a1) * radius,
                x2 = p.x + math.cos(a2) * radius, z2 = p.z + math.sin(a2) * radius })
        end
        local prevA, prevInside
        for k = 0, steps do
            local a = k / steps * 2 * math.pi
            local inside = isInside(a)
            if k > 0 and inside ~= prevInside then
                -- hranice mezi prevA a a: půlením najdi úhel průsečíku a nakresli vnější část
                local lo, hi = prevA, a
                for _ = 1, 10 do
                    local mid = (lo + hi) / 2
                    if isInside(mid) == prevInside then
                        lo = mid
                    else
                        hi = mid
                    end
                end
                if prevInside then
                    addArc(hi, a)
                else
                    addArc(prevA, lo)
                end
            elseif k > 0 and not inside then
                addArc(prevA, a)
            end
            prevA, prevInside = a, inside
        end
    end
    return lines
end

-- Řádky stavu vzorků pro kartu plánovače a nápovědu u kufru.
function SprayDroneSamples.getInfo(self)
    local spec = getSpec(self)
    local pf = SprayDroneStation.getPrecisionFarming()
    local points = spec.routeInfo ~= nil and spec.routeInfo.samplePoints or nil
    local pending = nil
    if pf ~= nil and pf.soilMap ~= nil and pf.soilMap.pendingSoilSamplesPerFarm ~= nil then
        local data = pf.soilMap.pendingSoilSamplesPerFarm[self:getOwnerFarmId()]
        pending = data ~= nil and data.toAnalyse or 0
    end
    return {
        hasPF = pf ~= nil,
        total = points ~= nil and points.total or 0,
        sampled = points ~= nil and points.sampled or 0,
        remaining = points ~= nil and (points.total - points.sampled) or 0,
        far = points ~= nil and points.far or 0,
        tall = points ~= nil and points.tall or 0,
        carried = spec.samplesCarried or 0,
        boxes = spec.samplerBoxes or 0,
        box = spec.sampleBox or 0,
        boxCapacity = spec.sampler.boxCapacity,
        capacity = spec.sampler.capacity,
        lab = pending,
        price = SprayDroneSamples.getPrice(pf)
    }
end

function SprayDroneSamples.getBoxText(self)
    local i = SprayDroneSamples.getInfo(self)
    return string.format(g_i18n:getText("sdt_sampler_box"), i.box, i.boxCapacity, i.carried, i.boxes)
end

-- Text bloku vzorků v kartě plánovače (body pole, dron a bednička, laboratoř PF a cena).
function SprayDroneSamples.getCardText(self)
    local i = SprayDroneSamples.getInfo(self)
    if not i.hasPF then
        return g_i18n:getText("sdt_sampler_noPF")
    end
    local spec = getSpec(self)
    local lines = {
        string.format(g_i18n:getText("sdt_sampler_points"), i.total, i.sampled, i.remaining - i.far - i.tall, i.far, i.tall),
        SprayDroneSamples.getBoxText(self),
        string.format(g_i18n:getText("sdt_sampler_lab"), i.lab or 0, g_i18n:formatMoney(i.price, 0, true, true))
    }
    local picks = spec.samplerPicks[spec.fieldId]
    if picks ~= nil then
        table.insert(lines, 2, string.format(g_i18n:getText("sdt_sampler_picks"), #picks.added, SprayDroneSamples.countRemoved(picks)))
    end
    return table.concat(lines, "\n")
end

-- Body na mapě plánovače: automatické červeně, naklikané oranžově (a větší), odebrané zeleně, teď neodebratelné (vysoký porost,
-- mimo dosah) šedě. Obrys sjednocení kruhů SAMPLE_RADIUS kolem všech bodů pole světle žlutě.
SprayDroneSamples.COLOR_DONE = { 0.2, 0.8, 0.3, 1 }
SprayDroneSamples.COLOR_AUTO = { 0.9, 0.15, 0.15, 1 }
SprayDroneSamples.COLOR_CUSTOM = { 1, 0.55, 0.1, 1 }
SprayDroneSamples.COLOR_SKIP = { 0.5, 0.5, 0.5, 1 }
SprayDroneSamples.COLOR_COVER = { 1, 0.93, 0.5, 0.85 }

function SprayDroneSamples.getPointColor(p)
    if p.sampled then
        return SprayDroneSamples.COLOR_DONE
    elseif p.tall or p.far then
        return SprayDroneSamples.COLOR_SKIP
    end
    return p.custom and SprayDroneSamples.COLOR_CUSTOM or SprayDroneSamples.COLOR_AUTO
end

function SprayDroneSamples.drawPlannerPoints(screen, vehicle)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local points = spec.isSamplerDrone and spec.routeInfo ~= nil and spec.routeInfo.samplePoints or nil
    if points == nil then
        return
    end
    for _, line in ipairs(spec.routeInfo.coverLines or {}) do
        screen:drawWorldLine(line.x1, line.z1, line.x2, line.z2, 2, SprayDroneSamples.COLOR_COVER)
    end
    for _, p in ipairs(points.points) do
        screen:drawMarker(p.x, p.z, p.custom and 10 or 7, SprayDroneSamples.getPointColor(p))
    end
end

---------------------------------------------------------------------------------------------------
-- vizuál (server i klienti ze synchronizovaného stavu): sonda, vzorkovnice v dronu a v bedničce, víčko bedničky

-- Víčko bedničky se otevře při každé změně obsahu: plné krabičky, krabičky vzaté do dronu.
function SprayDroneSamples.getLidKey(spec)
    return (spec.sampleBox or 0) * 4 + (spec.samplerBoxes or 0)
end

function SprayDroneSamples.load(self)
    local spec = getSpec(self)
    if not spec.isSamplerDrone then
        return
    end
    local get = SprayDroneStation.getMappedNode
    local prefix = spec.dronePrefix or ""
    local v = { droneSamples = {}, boxSamples = {}, slots = {}, droneBoxes = {}, shown = {}, probeT = 0, lidT = 0, lidUntil = 0 }
    -- přihrádky bedničky a krabičky na dronu podle kontraktu modelu (docs/PLAN-airasi-kufr.md): uzel s dětmi …Empty a …Full; počet
    -- přihrádek a krabiček dá kapacitu (applyModelCapacity), bez uzlů platí XML a nic se neukazuje
    local function boxNodes(name)
        local node = get(self, name)
        if node == nil then
            return nil
        end
        return { node = node, empty = get(self, name .. "Empty"), full = get(self, name .. "Full") }
    end
    for i = 1, 2 ^ SprayDroneSamples.BOX_BITS - 1 do
        local slot = boxNodes("sampleSlot" .. i)
        if slot == nil then
            break
        end
        v.slots[i] = slot
    end
    for i = 1, 2 ^ SprayDroneSamples.CARRY_BITS - 1 do
        local box = boxNodes("droneSampleBox" .. i)
        if box == nil then
            break
        end
        v.droneBoxes[i] = box
    end
    spec.samplerVisuals = v
    SprayDroneSamples.applyModelCapacity(spec)
    -- teleskopická sonda: stupně od vnější trubky po hrot, každý vyjede vůči rodiči dolů (chybějící mezistupně se přeskočí); sonda
    -- droneProbe z nového modelu vyjede o vehicle.sprayDroneCase#probeTravel
    local s = spec.sampler
    v.probeStages = {}
    for _, stage in ipairs({ { "droneProbe", s.caseProbeTravel }, { prefix .. "Probe", s.probeTravel }, { prefix .. "ProbeMid", s.midTravel },
        { prefix .. "ProbeMid2", s.midTravel }, { prefix .. "ProbeTip", s.tipTravel } }) do
        local node = get(self, stage[1])
        if node ~= nil then
            table.insert(v.probeStages, { node = node, base = { getTranslation(node) }, travel = stage[2] })
        end
    end
    -- starší model: vzorky bez krabiček (jen plné)
    for i = 1, spec.sampler.capacity do
        v.droneSamples[i] = get(self, prefix .. "Sample" .. i)
    end
    for i = 1, spec.sampler.boxCapacity do
        v.boxSamples[i] = get(self, "caseSample" .. i)
    end
    v.lid = get(self, "caseSampleBoxLid")
    v.box = get(self, "caseSamples")
    if v.box == nil and v.slots[1] ~= nil then
        v.box = getParent(v.slots[1].node)
    end
    v.lastBox = SprayDroneSamples.getLidKey(spec)
    -- klik na bedničku nesmí zároveň zvednout kufr (viz isAimedAtBox); jen pro místního hráče, server nemá jeho kameru
    local canBePickedUp = self.getCanBePickedUp
    if canBePickedUp ~= nil then
        self.getCanBePickedUp = function(vehicle, byPlayer)
            if byPlayer ~= nil and byPlayer == g_localPlayer and SprayDroneSamples.isAimedAtBox(vehicle) then
                return false
            end
            return canBePickedUp(vehicle, byPlayer)
        end
    end
end

local function show(v, key, node, visible)
    if node ~= nil and v.shown[key] ~= visible then
        v.shown[key] = visible
        setVisibility(node, visible)
    end
end

function SprayDroneSamples.updateVisuals(self, dt)
    local spec = getSpec(self)
    local v = spec.samplerVisuals
    if v == nil then
        return
    end
    local s = spec.sampler
    local target = spec.probeOut and 1 or 0
    if v.probeT ~= target then
        local step = dt * 0.001 / s.probeTime
        v.probeT = target > v.probeT and math.min(v.probeT + step, 1) or math.max(v.probeT - step, 0)
        for _, stage in ipairs(v.probeStages) do
            local b = stage.base
            setTranslation(stage.node, b[1], b[2] - stage.travel * v.probeT, b[3])
        end
        self:raiseActive()
    end
    for i, node in pairs(v.droneSamples) do
        show(v, "d" .. i, node, i <= spec.samplesCarried)
    end
    for i, node in pairs(v.boxSamples) do
        show(v, "b" .. i, node, i <= spec.sampleBox)
    end
    local slots = SprayDroneSamples.getSlotStates(#v.slots, spec.sampleBox, math.max(spec.samplerBoxes or 0, spec.samplesCarried))
    for i, slot in ipairs(v.slots) do
        show(v, "se" .. i, slot.empty, slots[i] == SprayDroneSamples.SLOT_EMPTY)
        show(v, "sf" .. i, slot.full, slots[i] == SprayDroneSamples.SLOT_FULL)
    end
    local boxes = SprayDroneSamples.getDroneBoxStates(#v.droneBoxes, spec.samplerBoxes or 0, spec.samplesCarried)
    for i, box in ipairs(v.droneBoxes) do
        -- krabička bez dětí Empty / Full se ukazuje celá
        show(v, "dn" .. i, box.node, boxes[i] ~= SprayDroneSamples.SLOT_NONE or (box.empty ~= nil or box.full ~= nil))
        show(v, "de" .. i, box.empty, boxes[i] == SprayDroneSamples.SLOT_EMPTY)
        show(v, "df" .. i, box.full, boxes[i] == SprayDroneSamples.SLOT_FULL)
    end
    local lidKey = SprayDroneSamples.getLidKey(spec)
    if v.lastBox ~= lidKey then
        v.lastBox = lidKey
        v.lidUntil = g_time + SprayDroneSamples.LID_OPEN_TIME
    end
    local lidTarget = g_time < v.lidUntil and 1 or 0
    if v.lid ~= nil and v.lidT ~= lidTarget then
        local step = dt * 0.001 * SprayDroneSamples.LID_SPEED
        v.lidT = lidTarget > v.lidT and math.min(v.lidT + step, 1) or math.max(v.lidT - step, 0)
        setRotation(v.lid, math.rad(-100) * v.lidT, 0, 0)
        self:raiseActive()
    elseif lidTarget > 0 then
        self:raiseActive()
    end
end

---------------------------------------------------------------------------------------------------
-- pěšky u kufru: levé tlačítko s pohledem na bedničku vzorků (uzel caseSamples) = odeslat vzorky (druhá cesta je tlačítko v plánovači);
-- řádek bedničky v nápovědě. Kufr má jediný activatable (víko na R, SprayDroneCaseActivatable): akce se k němu přidá obalením jeho
-- vstupu, jinak by systém activatable ukázal jen jeden z obou. Dokud hráč míří na bedničku, kufr nejde zvednout rukama (stejné
-- tlačítko), jinak by klik vzorky odeslal a kufr zároveň zvedl.

SprayDroneSamples.BOX_AIM_RADIUS = 0.45  -- m kolem uzlu bedničky, kam musí hráč mířit (bedna AIRASI 1,06 x 0,66 m přes celé víko)

-- Míří místní hráč na bedničku vzorků kufru? Jen u otevřeného (otevírajícího se) kufru: bedna AIRASI je ve víku, zavřená visí
-- uvnitř nad dronem a míření na zavřený kufr by bránilo ho zvednout.
function SprayDroneSamples.isAimedAtBox(vehicle)
    local v = getSpec(vehicle).samplerVisuals
    if v == nil or v.box == nil then
        return false
    end
    if vehicle.spec_foldable ~= nil and SprayDroneCase ~= nil and not SprayDroneCase.getIsLidOpening(vehicle) then
        return false
    end
    return SprayDroneLink.isAimedAt(v.box, SprayDroneSamples.BOX_AIM_RADIUS)
end

function SprayDroneSamples.onSendAction(activatable)
    local vehicle = activatable.vehicle
    if not SprayDroneSamples.isAimedAtBox(vehicle) or not SprayDroneLink.mayClick(activatable) then
        return
    end
    SprayDroneSound.noteAction(string.format("kufr %s: klik na bedničku, odeslat vzorky", tostring(vehicle.id)))
    local warning = SprayDroneSamples.requestSend(vehicle)
    if warning ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(warning), 2000)
    end
end

function SprayDroneSamples.updateSendAction(activatable)
    local id = activatable.sdtSendEventId
    if id == nil then
        return
    end
    local spec = getSpec(activatable.vehicle)
    g_inputBinding:setActionEventText(id, string.format(g_i18n:getText("sdt_sampler_send"), spec.sampleBox or 0))
    g_inputBinding:setActionEventTextVisibility(id, SprayDroneSamples.isAimedAtBox(activatable.vehicle) and SprayDroneLink.mayClick(activatable))
end

if SprayDroneCaseActivatable ~= nil then
    local caseRegister = SprayDroneCaseActivatable.registerCustomInput
    SprayDroneCaseActivatable.registerCustomInput = function(activatable, inputContext)
        caseRegister(activatable, inputContext)
        if SprayDroneSamples.getIsSampler(activatable.vehicle) then
            local id = SprayDroneLink.registerClick(activatable, SprayDroneSamples.onSendAction, nil)
            activatable.sdtSendEventId = id
            activatable.clickEventId = id
            SprayDroneSamples.updateSendAction(activatable)
        end
    end
    local caseRemove = SprayDroneCaseActivatable.removeCustomInput
    SprayDroneCaseActivatable.removeCustomInput = function(activatable, inputContext)
        caseRemove(activatable, inputContext)
        activatable.sdtSendEventId = nil
        activatable.clickEventId = nil
    end
    local caseActivatable = SprayDroneCaseActivatable.getIsActivatable
    SprayDroneCaseActivatable.getIsActivatable = function(activatable)
        local result = caseActivatable(activatable)
        if result then
            SprayDroneSamples.updateSendAction(activatable)
        end
        return result
    end
end

if SprayDroneCase ~= nil and SprayDroneCase.drawNearTexts ~= nil then
    local caseTexts = SprayDroneCase.drawNearTexts
    SprayDroneCase.drawNearTexts = function(self)
        caseTexts(self)
        local player = g_localPlayer
        if not SprayDroneSamples.getIsSampler(self) or player == nil or g_gui:getIsGuiVisible() then
            return
        end
        local px, py, pz = player:getPosition()
        local x, y, z = getWorldTranslation(self.rootNode)
        if px ~= nil and MathUtil.vector3Length(px - x, py - y, pz - z) <= SprayDroneCase.ACTIVATE_DISTANCE + 0.5
            and not (player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil) then
            g_currentMission:addExtraPrintText(SprayDroneSamples.getBoxText(self))
        end
    end
end
