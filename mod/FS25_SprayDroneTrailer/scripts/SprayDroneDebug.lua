-- DEBUG: ladicí ovládání za běhu hry (jen pro vývoj, hráči se nic nemění).
--
-- Jednou za sekundu (jen server) se čte soubor <profil hry>/modSettings/FS25_SprayDroneTrailer/debug.xml, například
--   <debug infiniteBattery="true" infiniteTank="true" speed="4" mistLoop="false" command="coverField" commandId="7"/>
-- Bez souboru je vše vypnuté. Soubor lze měnit za hry (mění se chování do sekundy); smazáním se vše vrátí.
--   infiniteBattery  baterie dronu se nespotřebovává
--   infiniteTank     nádrž dronu se nevyprazdňuje a nádrž vleku se doplňuje na plno
--   speed            násobek rychlosti simulace letu a servisu (1 = normál, nejvýš MAX_SPEED)
--   concentrateType  druh koncentrátu pro příkaz fillConcentrate do prázdné nádrže: název koncentrátu (SDT_CONCENTRATE_HERBICIDE |
--                    SDT_CONCENTRATE_FERTILIZER), nebo přípravku, který z něj vzniká (herbicide | liquidFertilizer)
--   mistLoop         testovací let: dron bez vzletu jezdí tam a zpět vedle vleku, mlha stále zapnutá, nic se nespotřebuje
--   command          jednorázový příkaz, provede se při změně commandId:
--                    chargeAll (všechny baterie na 100 %), fillTrailer (nádrž vleku plná přípravkem), fillDiesel (nafta plná),
--                    fillWater (hlavní nádrž vleku plná vodou, pro míchání; jen prázdná nebo s vodou),
--                    fillConcentrate (koncentrátová nádrž plná: stávajícím druhem, jinak podle concentrateType, výchozí
--                    koncentrát hnojiva),
--                    coverField (celé vybrané pole včetně úvratí označit za obletěné – další start končí hlášením „pole hotové“),
--                    resetCoverage (smazat paměť obletěného pole),
--                    toolboxFill (všechny sloty v bedně naplnit kanystry s tekutým hnojivem), toolboxOpen (přepnout víko bedny),
--                    toolboxDialog (otevřít dialog bedny na hostiteli i mimo aktivaci),
--                    spawnCanister (vyrobit plný kanystr hnojiva za vlekem, do logu hmotnost a nosnost rukou),
--                    pickCanister (nejbližší kanystr dát místnímu hráči do rukou, do logu jestli jde zvednout),
--                    tiltCanister (vyrobit kanystr a 8 s ho držet nakloněný nad hrdlem koncentrátové nádrže),
--                    view (postavit místního hráče na bod a natočit kameru na jiný bod, obojí v souřadnicích nejbližšího vleku,
--                    atribut view="fx,fy,fz,tx,ty,tz": nohy hráče a cíl pohledu),
--                    soilProbe (stav půdy ve čtverci probeSize m (výchozí 10) kolem bodu probe="x,z" ve světě, bez něj kolem
--                    místního hráče: histogram stavů plevele, podíl plevele 1-6 a násobek spotřeby herbicidu, úroveň hnojení,
--                    s Precision Farming dusík kg/ha a pH; místo a hodnoty si pamatuje),
--                    soilAgain (totéž znovu na zapamatovaném místě a rozdíl proti soilProbe – po přeletu dronu)
-- Vypnutí celého ladění v ostré verzi: SprayDroneDebug.ENABLED = false.

SprayDroneDebug = {}

SprayDroneDebug.ENABLED = false
SprayDroneDebug.FILE = "modSettings/FS25_SprayDroneTrailer/debug.xml"
SprayDroneDebug.POLL_TIME = 1000
SprayDroneDebug.MAX_SPEED = 10

SprayDroneDebug.infiniteBattery = false
SprayDroneDebug.infiniteTank = false
SprayDroneDebug.mistLoop = false
SprayDroneDebug.speed = 1
SprayDroneDebug.concentrateType = nil
SprayDroneDebug.command = nil
SprayDroneDebug.commandId = 0
SprayDroneDebug.view = nil
SprayDroneDebug.EYE_HEIGHT = 1.65
SprayDroneDebug.lastPoll = -1e9
SprayDroneDebug.trace = false
SprayDroneDebug.traceTime = 0
SprayDroneDebug.probePos = nil
SprayDroneDebug.probeSize = 10
SprayDroneDebug.soilSpot = nil

function SprayDroneDebug.readFile()
    local path = getUserProfileAppPath() .. SprayDroneDebug.FILE
    SprayDroneDebug.concentrateType = nil
    local infiniteBattery, infiniteTank, mistLoop, speed, command, commandId = false, false, false, 1, nil, SprayDroneDebug.commandId
    if fileExists(path) then
        local handle = loadXMLFile("sdtDebug", path)
        if handle ~= nil and handle ~= 0 then
            infiniteBattery = Utils.getNoNil(getXMLBool(handle, "debug#infiniteBattery"), false)
            infiniteTank = Utils.getNoNil(getXMLBool(handle, "debug#infiniteTank"), false)
            mistLoop = Utils.getNoNil(getXMLBool(handle, "debug#mistLoop"), false)
            speed = math.clamp(Utils.getNoNil(getXMLFloat(handle, "debug#speed"), 1), 0.1, SprayDroneDebug.MAX_SPEED)
            command = getXMLString(handle, "debug#command")
            SprayDroneDebug.concentrateType = getXMLString(handle, "debug#concentrateType")
            local view = getXMLString(handle, "debug#view")
            SprayDroneDebug.view = nil
            if view ~= nil and view ~= "" then
                local values = {}
                for number in view:gmatch("[^,%s]+") do
                    table.insert(values, tonumber(number))
                end
                SprayDroneDebug.view = #values == 6 and values or nil
            end
            local probe = getXMLString(handle, "debug#probe")
            SprayDroneDebug.probePos = nil
            if probe ~= nil and probe ~= "" then
                local x, z = probe:match("^%s*([%-%d%.]+)%s*,%s*([%-%d%.]+)%s*$")
                if x ~= nil then
                    SprayDroneDebug.probePos = { x = tonumber(x), z = tonumber(z) }
                end
            end
            SprayDroneDebug.probeSize = math.clamp(Utils.getNoNil(getXMLFloat(handle, "debug#probeSize"), 10), 1, 200)
            commandId = Utils.getNoNil(getXMLInt(handle, "debug#commandId"), 0)
            delete(handle)
        end
    end
    local changed = infiniteBattery ~= SprayDroneDebug.infiniteBattery or infiniteTank ~= SprayDroneDebug.infiniteTank
        or mistLoop ~= SprayDroneDebug.mistLoop or speed ~= SprayDroneDebug.speed
    SprayDroneDebug.infiniteBattery, SprayDroneDebug.infiniteTank = infiniteBattery, infiniteTank
    SprayDroneDebug.mistLoop, SprayDroneDebug.speed = mistLoop, speed
    SprayDroneDebug.command = commandId ~= SprayDroneDebug.commandId and command or nil
    SprayDroneDebug.commandId = commandId
    if changed then
        Logging.info("SDT DEBUG: nekonečná baterie %s, nekonečná nádrž %s, testovací let %s, rychlost x%.1f", tostring(infiniteBattery),
            tostring(infiniteTank), tostring(mistLoop), speed)
    end
end

-- Volá se každý snímek z SprayDroneStation:onUpdate na serveru; vrací násobek rychlosti simulace (dt se násobí venku).
function SprayDroneDebug.update(vehicle, dt)
    if not SprayDroneDebug.ENABLED then
        return 1
    end
    if g_time - SprayDroneDebug.lastPoll >= SprayDroneDebug.POLL_TIME then
        SprayDroneDebug.lastPoll = g_time
        SprayDroneDebug.readFile()
    end
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local command = SprayDroneDebug.command
    if command ~= nil and spec.debugCommandId ~= SprayDroneDebug.commandId then
        spec.debugCommandId = SprayDroneDebug.commandId
        SprayDroneDebug.runCommand(vehicle, command)
    end
    if SprayDroneDebug.infiniteTank then
        SprayDroneDebug.topUpTank(vehicle)
    end
    if SprayDroneDebug.trace and g_time >= SprayDroneDebug.traceTime then
        SprayDroneDebug.traceTime = g_time + 1000
        SprayDroneDebug.traceVehicle(vehicle)
    end
    return SprayDroneDebug.speed
end

-- Doplní fill unit na plno daným druhem (jen když je prázdný nebo už ten druh obsahuje); vrací, kolik přidal.
function SprayDroneDebug.fillUnit(vehicle, fillUnitIndex, fillType)
    if fillUnitIndex == nil or fillType == nil or fillType == FillType.UNKNOWN or not vehicle:getFillUnitExists(fillUnitIndex) then
        return 0
    end
    local current = vehicle:getFillUnitFillType(fillUnitIndex)
    if vehicle:getFillUnitFillLevel(fillUnitIndex) > 0 and current ~= fillType then
        Logging.info("SDT DEBUG: nádrž %d obsahuje jiný druh (%s), nedoplněno", fillUnitIndex,
            tostring(g_fillTypeManager:getFillTypeNameByIndex(current)))
        return 0
    end
    local missing = vehicle:getFillUnitCapacity(fillUnitIndex) - vehicle:getFillUnitFillLevel(fillUnitIndex)
    return vehicle:addFillUnitFillLevel(vehicle:getOwnerFarmId(), fillUnitIndex, missing, fillType, ToolType.UNDEFINED, nil)
end

-- Druh koncentrátu podle debug.xml (concentrateType): přímo koncentrát, nebo přípravek, ze kterého mixér koncentrát ředí.
function SprayDroneDebug.getConcentrateType(vehicle)
    local name = SprayDroneDebug.concentrateType
    local index = name ~= nil and g_fillTypeManager:getFillTypeIndexByName(name) or nil
    if index == nil then
        return nil
    end
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    if spec.mixerRatios[index] ~= nil then
        return index
    end
    for _, concentrateType in ipairs(spec.mixerTypes) do
        if spec.mixerProducts[concentrateType] == index then
            return concentrateType
        end
    end
    return nil
end

-- Druh v nádrži, jinak `default`.
function SprayDroneDebug.typeOrDefault(vehicle, fillUnitIndex, default)
    if vehicle:getFillUnitFillLevel(fillUnitIndex) > 0 then
        return vehicle:getFillUnitFillType(fillUnitIndex)
    end
    return default
end

function SprayDroneDebug.topUpTank(vehicle)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    if vehicle:getFillUnitFillLevel(spec.fillUnitIndex) < vehicle:getFillUnitCapacity(spec.fillUnitIndex) * 0.9 then
        local _, fillType = SprayDroneStation.getSprayType(vehicle)
        SprayDroneDebug.fillUnit(vehicle, spec.fillUnitIndex, SprayDroneDebug.typeOrDefault(vehicle, spec.fillUnitIndex, fillType))
    end
    local concIndex = SprayDroneStation.getConcentrateUnit(vehicle)
    if concIndex ~= nil and vehicle:getFillUnitFillLevel(concIndex) > 0
        and vehicle:getFillUnitFillLevel(concIndex) < vehicle:getFillUnitCapacity(concIndex) * 0.9 then
        SprayDroneDebug.fillUnit(vehicle, concIndex, vehicle:getFillUnitFillType(concIndex))
    end
end

-- Pro vybrané pole projde mřížku po 10 m a spočítá, proč se na místě nesmí stříkat (SprayDroneRoute.getIsWorkable).
function SprayDroneDebug.probeField(vehicle)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field == nil then
        return
    end
    local poly = SprayDroneRoute.getPolygon(field)
    local minX, maxX, minZ, maxZ = math.huge, -math.huge, math.huge, -math.huge
    for _, p in ipairs(poly) do
        minX, maxX, minZ, maxZ = math.min(minX, p.x), math.max(maxX, p.x), math.min(minZ, p.z), math.max(maxZ, p.z)
    end
    local count = { inside = 0, farmland = 0, notField = 0, mature = 0, ok = 0 }
    local farmlands = {}
    for x = minX, maxX, 10 do
        for z = minZ, maxZ, 10 do
            if SprayDroneRoute.isPointInPolygon(poly, x, z) then
                count.inside = count.inside + 1
                local fl = g_farmlandManager:getFarmlandIdAtWorldPosition(x, z)
                farmlands[fl or -1] = (farmlands[fl or -1] or 0) + 1
                if fl ~= field:getId() then
                    count.farmland = count.farmland + 1
                elseif not FSDensityMapUtil.getFieldDataAtWorldPosition(x, 0, z) then
                    count.notField = count.notField + 1
                else
                    local fruitIndex, growthState = FSDensityMapUtil.getFruitTypeIndexAtWorldPos(x, z)
                    local fruitType = fruitIndex ~= nil and g_fruitTypeManager:getFruitTypeByIndex(fruitIndex) or nil
                    if fruitType ~= nil and growthState ~= nil and growthState >= fruitType.minHarvestingGrowthState
                        and growthState <= fruitType.maxHarvestingGrowthState then
                        count.mature = count.mature + 1
                    else
                        count.ok = count.ok + 1
                    end
                end
            end
        end
    end
    local text = {}
    for fl, n in pairs(farmlands) do
        table.insert(text, string.format("%s:%d", tostring(fl), n))
    end
    Logging.info("SDT DEBUG probeField %d (id pole %s, %d bodů polygonu, bbox %.0f x %.0f m): uvnitř=%d jiný pozemek=%d není pole=%d zralé=%d ok=%d, pozemky {%s}",
        spec.fieldId, tostring(field:getId()), #poly, maxX - minX, maxZ - minZ, count.inside, count.farmland, count.notField, count.mature, count.ok,
        table.concat(text, " "))
end

-- DEBUG: histogram hodnot kanálů mapy ve čtverci size kolem x,z: {counts[v], total, avg (průměr přes pixely s hodnotou)}.
function SprayDroneDebug.histogram(mapId, firstChannel, numChannels, x, z, size, maxValue)
    local h = size * 0.5
    local modifier = DensityMapModifier.new(mapId, firstChannel, numChannels, g_terrainNode)
    modifier:setParallelogramWorldCoords(x - h, z - h, x + h, z - h, x - h, z + h, DensityCoordType.POINT_POINT_POINT)
    local filter = DensityMapFilter.new(mapId, firstChannel, numChannels)
    local result = { counts = {}, total = 0, sum = 0 }
    for v = 0, maxValue or (2 ^ numChannels - 1) do
        filter:setValueCompareParams(DensityValueCompareType.EQUAL, v)
        local _, pixels = modifier:executeGet(filter)
        if pixels > 0 then
            result.counts[v] = pixels
            result.total = result.total + pixels
            result.sum = result.sum + v * pixels
        end
    end
    result.avg = result.total > 0 and result.sum / result.total or 0
    return result
end

-- DEBUG
function SprayDroneDebug.formatHistogram(hist)
    local parts = {}
    for v, n in pairs(hist.counts) do
        table.insert(parts, { v = v, text = string.format("%d:%d", v, n) })
    end
    table.sort(parts, function(a, b) return a.v < b.v end)
    local text = {}
    for _, p in ipairs(parts) do
        table.insert(text, p.text)
    end
    return table.concat(text, " ")
end

-- DEBUG: jména funkcí objektu včetně tříd v řetězu metatabulek (ověření API Precision Farming ve hře).
function SprayDroneDebug.listFunctions(object)
    local names, seen, depth = {}, {}, 0
    local current = object
    while type(current) == "table" and not seen[current] and depth < 6 do
        seen[current] = true
        for k, v in pairs(current) do
            if type(v) == "function" then
                names[tostring(k)] = true
            end
        end
        local mt = getmetatable(current)
        current = mt ~= nil and mt.__index or nil
        depth = depth + 1
    end
    local list = {}
    for name in pairs(names) do
        table.insert(list, name)
    end
    table.sort(list)
    return table.concat(list, " ")
end

-- DEBUG: jedno měření půdy (plevel, hnojení, PF) ve čtverci kolem x,z; vrací souhrn pro porovnání.
function SprayDroneDebug.measureSoil(vehicle, x, z, size, label)
    local mission = g_currentMission
    local h = size * 0.5
    local snap = { weedShare = nil, spray = nil, nKg = nil, ph = nil }
    Logging.info("SDT SOIL %s: místo %.1f %.1f, čtverec %.0f m", label, x, z, size)

    local probe = SprayDroneStation.getWeedProbe()
    if probe ~= nil then
        local hist = SprayDroneDebug.histogram(probe.mapId, probe.firstChannel, probe.numChannels, x, z, size)
        local weed, total = SprayDroneStation.getWeedPixels(x - h, z - h, x + h, z - h, x - h, z + h)
        snap.weedShare = total ~= nil and total > 0 and weed / total or 0
        Logging.info("SDT SOIL %s: plevel stavy {%s}, podíl 1-6 %.1f %%, násobek herbicidu %.2f", label, SprayDroneDebug.formatHistogram(hist),
            snap.weedShare * 100, SprayDroneRoute.getHerbicideFactor(weed, total))
    else
        Logging.info("SDT SOIL %s: mapa bez plevele", label)
    end

    local groundSystem = mission.fieldGroundSystem
    local sprayMapId, sprayFirst, sprayNum = groundSystem:getDensityMapData(FieldDensityMap.SPRAY_LEVEL)
    if sprayMapId ~= nil then
        local hist = SprayDroneDebug.histogram(sprayMapId, sprayFirst, sprayNum, x, z, size, groundSystem:getMaxValue(FieldDensityMap.SPRAY_LEVEL))
        snap.spray = hist.avg
        Logging.info("SDT SOIL %s: úroveň hnojení {%s}, průměr %.2f", label, SprayDroneDebug.formatHistogram(hist), hist.avg)
    end

    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    if spec.fieldId ~= 0 then
        Logging.info("SDT SOIL %s: vybrané pole %d, plánovací násobek herbicidu %.2f", label, spec.fieldId, SprayDroneStation.getFieldWeedFactor(vehicle))
    end

    local pf = SprayDroneStation.getPrecisionFarming()
    if pf == nil then
        Logging.info("SDT SOIL %s: Precision Farming nenačten (g_precisionFarming ani %s.g_precisionFarming)", label, SprayDroneStation.PF_MOD_NAME)
        return snap
    end
    local control = SprayDroneStation.getPFWeedControl(pf)
    Logging.info("SDT SOIL %s: PF ano, ExtendedWeedControl %s, lastUseSpotSpraying=%s", label, control ~= nil and "nalezen" or "NENALEZEN",
        control ~= nil and tostring(control.lastUseSpotSpraying) or "-")
    if not SprayDroneDebug.pfApiLogged then
        SprayDroneDebug.pfApiLogged = true
        Logging.info("SDT SOIL PF API nitrogenMap: %s", SprayDroneDebug.listFunctions(pf.nitrogenMap))
        Logging.info("SDT SOIL PF API pHMap: %s", SprayDroneDebug.listFunctions(pf.pHMap))
        local fields = {}
        for k, v in pairs(pf.nitrogenMap or {}) do
            if type(v) ~= "function" then
                table.insert(fields, string.format("%s=%s", tostring(k), type(v) == "table" and "{}" or tostring(v)))
            end
        end
        table.sort(fields)
        Logging.info("SDT SOIL PF pole nitrogenMap: %s", table.concat(fields, " "):sub(1, 1500))
    end
    for _, item in ipairs({ { map = pf.nitrogenMap, class = "NitrogenMap", key = "nKg" }, { map = pf.pHMap, class = "PHMap", key = "ph" } }) do
        local ok, err = pcall(function()
            local mapId, first, num = SprayDroneStation.getPFMapLayer(item.map, item.class)
            if mapId == nil then
                Logging.info("SDT SOIL %s: %s bez bitové mapy (bitVectorMap/NUM_BITS) – zápis dronu se nekoná", label, item.class)
                return
            end
            local hist = SprayDroneDebug.histogram(mapId, first, num, x, z, size)
            local value
            if item.key == "nKg" then
                value = item.map:getNitrogenValueFromInternalValue(math.floor(hist.avg + 0.5))
            else
                value = item.map:getPhValueFromInternalValue(math.floor(hist.avg + 0.5))
            end
            snap[item.key] = value
            Logging.info("SDT SOIL %s: %s vnitřní {%s}, průměr %.2f = %s %s", label, item.class, SprayDroneDebug.formatHistogram(hist), hist.avg,
                tostring(value), item.key == "nKg" and "kg N/ha" or "pH")
        end)
        if not ok then
            Logging.info("SDT SOIL %s: %s čtení selhalo: %s", label, item.class, tostring(err))
        end
    end
    return snap
end

-- DEBUG: soilProbe (again = false) změří a zapamatuje místo, soilAgain změří znovu a vypíše rozdíl.
function SprayDroneDebug.soilProbe(vehicle, again)
    local spot = SprayDroneDebug.soilSpot
    if not again or spot == nil then
        local pos = SprayDroneDebug.probePos
        if pos == nil and g_localPlayer ~= nil then
            local px, _, pz = g_localPlayer:getPosition()
            pos = { x = px, z = pz }
        end
        if pos == nil then
            Logging.info("SDT SOIL: chybí místo (atribut probe=\"x,z\" nebo místní hráč)")
            return
        end
        spot = { x = pos.x, z = pos.z, size = SprayDroneDebug.probeSize }
        spot.before = SprayDroneDebug.measureSoil(vehicle, spot.x, spot.z, spot.size, "PŘED")
        SprayDroneDebug.soilSpot = spot
        return
    end
    local after = SprayDroneDebug.measureSoil(vehicle, spot.x, spot.z, spot.size, "PO")
    local function diff(key)
        local a, b = spot.before[key], after[key]
        if type(a) ~= "number" or type(b) ~= "number" then
            return "-"
        end
        return string.format("%.2f -> %.2f (%+.2f)", a, b, b - a)
    end
    Logging.info("SDT SOIL ROZDÍL: plevel 1-6 %s, hnojení %s, dusík kg/ha %s, pH %s", diff("weedShare"), diff("spray"), diff("nKg"), diff("ph"))
end

-- Hráč se postaví na bod fx,fy,fz (v souřadnicích vleku) a kamera se otočí k bodu tx,ty,tz.
function SprayDroneDebug.applyView(vehicle)
    local v = SprayDroneDebug.view
    local player = g_localPlayer
    if v == nil or player == nil or player.camera == nil or not SprayDroneToolbox.debugIsNearest(vehicle) then
        return
    end
    local fx, fy, fz = localToWorld(vehicle.rootNode, v[1], v[2], v[3])
    local tx, ty, tz = localToWorld(vehicle.rootNode, v[4], v[5], v[6])
    -- vynucený letový režim hráče (PlayerMover:setFlightActive s isForced), ať po teleportu nespadne a kamera zůstane na místě
    player.mover:setFlightActive(true, true)
    player.mover:teleportTo(fx, fy, fz, true)
    local dx, dy, dz = tx - fx, ty - (fy + SprayDroneDebug.EYE_HEIGHT), tz - fz
    local length = MathUtil.vector3Length(dx, dy, dz)
    if length > 0.001 then
        local pitch, yaw = MathUtil.directionToPitchYaw(dx / length, dy / length, dz / length)
        player.camera:setRotation(pitch, yaw, 0)
    end
    Logging.info("SDT DEBUG: pohled z [%.2f %.2f %.2f] na [%.2f %.2f %.2f] (svět %.1f %.1f %.1f)", v[1], v[2], v[3], v[4], v[5], v[6], fx, fy, fz)
end

-- Řádek stavu jednou za sekundu (příkaz traceOn / traceOff): měření času plnění, spotřeby a letu.
function SprayDroneDebug.traceVehicle(vehicle)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local dx, dy, dz = 0, 0, 0
    if spec.node ~= nil then
        dx, dy, dz = localToLocal(spec.node, vehicle.rootNode, 0, 0, 0)
    end
    Logging.info("SDT TRACE t=%.1f stav=%d dron=%.2f l baterie=%.0f/%.0f s hlavni=%.1f l pozice=%.1f %.1f %.1f", g_time / 1000, spec.state,
        spec.droneFillLevel, spec.battery, spec.batteryCapacity, vehicle:getFillUnitFillLevel(spec.fillUnitIndex), dx, dy, dz)
end

-- Svislé paprsky shora přes vlek (maska VEHICLE): do logu, co a ve které výšce zasáhly (kolize vleku pro chodce).
function SprayDroneDebug.colProbe(vehicle)
    SprayDroneDebug.probeVehicle = vehicle
    for _, x in ipairs({ -0.8, 0, 0.8 }) do
        for z = -7, 4.5, 0.75 do
            local wx, wy, wz = localToWorld(vehicle.rootNode, x, 5, z)
            local dx, dy, dz = localDirectionToWorld(vehicle.rootNode, 0, -1, 0)
            SprayDroneDebug.probeKey = string.format("x=%.2f z=%.2f", x, z)
            local hit = false
            SprayDroneDebug.probeHit = function() hit = true end
            raycastClosest(wx, wy, wz, dx, dy, dz, 8, "colProbeCallback", SprayDroneDebug, CollisionFlag.VEHICLE)
            if not hit then
                Logging.info("SDT PROBE %s: nic", SprayDroneDebug.probeKey)
            end
        end
    end
end

function SprayDroneDebug:colProbeCallback(hitObjectId, x, y, z, distance)
    local vehicle = SprayDroneDebug.probeVehicle
    local lx, ly = worldToLocal(vehicle.rootNode, x, y, z)
    if not SprayDroneDebug.probeQuiet then
        Logging.info("SDT PROBE %s: %s výška %.2f", SprayDroneDebug.probeKey, getName(hitObjectId), ly)
    end
    SprayDroneDebug.probeHit(lx)
    return false
end

function SprayDroneDebug:deckHitCallback(hitObjectId, x, y, z, distance)
    table.insert(SprayDroneDebug.deckHitList, string.format("%s y=%.2f", getName(hitObjectId), 5 - distance))
    return true
end

-- Vodorovné paprsky zleva doprava přes vlek (maska VEHICLE): mapa kolizí, řádek = výška, sloupec = poloha po délce vleku
-- (krok 0,25 m od z = -7 do z = 4,5); znak = x místa zásahu v desetinách metru (0-9 = |x| ve dm, ' ' žádný zásah).
function SprayDroneDebug.colMap(vehicle)
    SprayDroneDebug.probeVehicle = vehicle
    local wx0, wy0, wz0 = getWorldTranslation(vehicle.rootNode)
    Logging.info("SDT MAP uzel vleku svět %.3f %.3f %.3f typ těla %s terén pod uzlem %.3f čas skládání %.3f", wx0, wy0, wz0, tostring(getRigidBodyType(vehicle.rootNode)), getTerrainHeightAtWorldPos(g_terrainNode, wx0, 0, wz0), vehicle:getFoldAnimTime())
    for _, y in ipairs({ 0.3, 0.6, 0.9, 1.2, 1.6, 2.0, 2.4, 2.8, 3.2 }) do
        local row = {}
        for z = -7, 4.5, 0.25 do
            local wx, wy, wz = localToWorld(vehicle.rootNode, -2.5, y, z)
            local dx, dy, dz = localDirectionToWorld(vehicle.rootNode, 1, 0, 0)
            local hitX
            SprayDroneDebug.probeHit = function(lx) hitX = lx end
            SprayDroneDebug.probeKey = "map"
            SprayDroneDebug.probeQuiet = true
            raycastClosest(wx, wy, wz, dx, dy, dz, 5, "colProbeCallback", SprayDroneDebug, CollisionFlag.VEHICLE)
            SprayDroneDebug.probeQuiet = false
            row[#row + 1] = hitX == nil and "." or tostring(math.min(9, math.floor(math.abs(hitX) * 5)))
        end
        Logging.info("SDT MAP y=%.1f %s", y, table.concat(row))
    end
end

-- Mlýnkový vozík na vápno: ovládání z debug.xml bez aktivace hráčem (millOn, millOff) a řádek stavu (millStatus). -- DEBUG
function SprayDroneDebug.mill(command) -- DEBUG
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        local ms = v[SprayDroneMill.SPEC_NAME]
        if ms ~= nil then
            if command == "millOn" then
                v:sprayDroneMillCommand(SprayDroneMill.CMD_ENGINE_ON)
            elseif command == "millOff" then
                v:sprayDroneMillCommand(SprayDroneMill.CMD_ENGINE_OFF)
            elseif command == "millFill" then
                v:addFillUnitFillLevel(v:getOwnerFarmId(), 1, 1500, FillType.LIME, ToolType.UNDEFINED, nil)
                v:addFillUnitFillLevel(v:getOwnerFarmId(), 2, 30, FillType.DIESEL, ToolType.UNDEFINED, nil)
            end
            Logging.info("SDT MILL: motor=%s mele=%s cerpa=%s | hrube %.1f nafta %.2f jemne %.1f", tostring(ms.engineOn), tostring(ms.milling),
                tostring(ms.pumping), v:getFillUnitFillLevel(1), v:getFillUnitFillLevel(2), v:getFillUnitFillLevel(3))
        end
    end
end

-- Výška podlahy pod hadicí: terén, floorAt a nejbližší zásah paprsku se všemi maskami (kde skutečně leží povrch).
local floorHit = {}
function floorHit:callback(hitObjectId, x, y, z, distance)
    if hitObjectId ~= nil and hitObjectId ~= 0 and self.hit == nil then
        self.hit, self.y = hitObjectId, y
    end
    return false
end

function SprayDroneDebug.millFloor() -- DEBUG
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        local ms = v[SprayDroneMill.SPEC_NAME]
        if ms ~= nil and ms.outlet ~= nil then
            local nx, ny, nz = getWorldTranslation(ms.outlet)
            for k = 0, 5 do
                local x, z = nx - 0.8 * k, nz - 0.4 * k
                local terrain = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
                floorHit.hit, floorHit.y = nil, nil
                raycastClosest(x, terrain + 2, z, 0, -1, 0, 4, "callback", floorHit, 0xFFFFFFFF)
                Logging.info("SDT FLOOR k=%d teren=%.3f floorAt=%.3f raycastVse=%s", k, terrain, SprayDroneHoseLib.floorAt(x, z),
                    floorHit.hit ~= nil and string.format("%.3f (%s)", floorHit.y, tostring(getName(floorHit.hit))) or "-")
            end
        end
    end
end

-- Zkušební zdroj vody: IBC z LSFM Universal Tank Pack 3 m před kamerou, naplněné vodou. -- DEBUG
function SprayDroneDebug.spawnIbc(empty) -- DEBUG
    local mod = g_modManager:getModByName("FS25_lsfmUniversalTankPack")
    if mod == nil then
        Logging.info("SDT IBC: mod FS25_lsfmUniversalTankPack není načtený")
        return
    end
    local cam = getCamera()
    local cx, _, cz = getWorldTranslation(cam)
    local dx, _, dz = localDirectionToWorld(cam, 0, 0, -1)
    local len = math.sqrt(dx * dx + dz * dz)
    local x, z = cx + dx / len * 3, cz + dz / len * 3
    local data = VehicleLoadingData.new()
    data:setFilename(mod.modDir .. "objects/ibcTank_fillable.xml")
    data:setPosition(x, getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.1, z)
    data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(1)
    data:load(function(_, vehicles, state)
        local v = vehicles ~= nil and vehicles[1] or nil
        if state ~= VehicleLoadingState.OK or v == nil then
            Logging.info("SDT IBC: nepodařilo se načíst")
            return
        end
        if not empty then
            v:addFillUnitFillLevel(1, 1, 1000, FillType.WATER, ToolType.UNDEFINED, nil)
        end
        Logging.info("SDT IBC: hotovo %d, voda %.0f l", v.id, v:getFillUnitFillLevel(1))
    end)
end

-- Stav vodních hadic: spojky (poloha v souřadnicích vleku, vzdálenost hráče) a každá hadice zvlášť (vytažená / nesená / připojená, zdroj, bod připojení), hladiny. -- DEBUG
function SprayDroneDebug.whStatus() -- DEBUG
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        local ws = v[SprayDroneWaterHose.SPEC_NAME]
        if ws ~= nil then
            local px, py, pz = g_localPlayer:getPosition()
            Logging.info("SDT WH == %s (id %s)", tostring(v:getName()), tostring(v.id))
            local first = v
            for _, other in ipairs(g_currentMission.vehicleSystem.vehicles) do
                if other[SprayDroneStation.SPEC_NAME] ~= nil and SprayDroneToolbox.debugIsNearest(other) then
                    first = other
                end
            end
            local main = v[SprayDroneStation.SPEC_NAME] ~= nil and v[SprayDroneStation.SPEC_NAME].fillUnitIndex or v[SprayDronePump.SPEC_NAME].waterUnit
            for hi, h in ipairs(ws.hoses) do
                for _, p in ipairs(SprayDroneWaterHose.getActivePorts(v, hi)) do
                    local x, y, z = getWorldTranslation(p.node)
                    local lx, ly, lz = worldToLocal(v.rootNode, x, y, z)
                    local fx, fy, fz = worldToLocal(first.rootNode, x, y, z)
                    Logging.info("SDT WH hadice %d ventil %d (%s): misto vleku %.2f %.2f %.2f hrac->ventil %.2f | v Blenderu prvniho vleku (%s) %.2f %.2f %.2f", hi, p.index,
                        p.port.kind, lx, ly, lz, MathUtil.vector3Length(px - x, py - y, pz - z), tostring(first:getName()), fx, -fz, fy)
                end
                Logging.info("SDT WH hadice %d: vytazena=%s nesena=%s zdroj=%s rybnik=%s ventil=%d cil=%s kohout=%s", hi, tostring(h.out), tostring(h.held),
                    tostring(h.source ~= nil), tostring(h.pond), h.port, tostring(h.targetPort), tostring(h.valveOpen))
                if h.out and not h.held then
                    local ax, ay, az = SprayDroneWaterHose.getAttachWorld(v, h)
                    Logging.info("SDT WH zdroj %s: hladina1 %.1f l, pripojeni svet %.2f %.2f %.2f, lokalne %.2f %.2f %.2f", h.source ~= nil and tostring(h.source:getName()) or "rybnik",
                        h.source ~= nil and h.source:getFillUnitFillLevel(1) or 0, ax or 0, ay or 0, az or 0, h.srcX, h.srcY, h.srcZ)
                    local ms = h.source ~= nil and h.source[SprayDroneMill.SPEC_NAME] or nil
                    if ms ~= nil and ms.outlet ~= nil then
                        local ox, oy, oz = getWorldTranslation(ms.outlet)
                        local lx, ly, lz = worldToLocal(h.source.rootNode, ox, oy, oz)
                        Logging.info("SDT WH vystup mlynku: svet %.2f %.2f %.2f, lokalne %.2f %.2f %.2f", ox, oy, oz, lx, ly, lz)
                    end
                end
            end
            Logging.info("SDT WH: nadrz %.1f l (%s) | koncentrat %.1f l", v:getFillUnitFillLevel(main),
                tostring(g_fillTypeManager:getFillTypeNameByIndex(v:getFillUnitFillType(main))), v:getFillUnitFillLevel(3) or 0)
        end
    end
end

-- Nastaví režim vstupu pumpy (pond = sací koš, jinak nádrž) jako hráč: sací hadici odloží a přepne příkazem; motor musí stát. -- DEBUG
function SprayDroneDebug.setPumpMode(pump, pond) -- DEBUG
    local ps = pump[SprayDronePump.SPEC_NAME]
    if ps.pondMode ~= pond then
        pump:sprayDroneWaterHoseCommand(SprayDroneWaterHose.CMD_DROP, nil, nil, nil, nil, nil, nil, nil, nil, nil, 1)
        pump:sprayDronePumpCommand(SprayDronePump.CMD_MODE_TOGGLE)
    end
    Logging.info("SDT PUMP id %s: vstup v režimu %s", tostring(pump.id), ps.pondMode and "rybník" or "nádrž")
end

-- Simulace hráče u vodní hadice: whConnect<N> vytáhne hadici (první hadici vozidla) z ventilu N a připojí ji k nejbližšímu zdroji (voda / mlýnek), u pumpy
-- přepne vstup na nádrž a připojí ho k IBC / cisterně; whPond přepne vstup pumpy na rybník a položí sací koš do nejbližší vody do 8 m, whOut připojí výstupní
-- hadici pumpy na nejbližší vodní ventil vleku, whValve přepne kohout, whDrop všechny hadice zruší. Port N je číslo z whStatus. -- DEBUG
function SprayDroneDebug.waterHoseSim(command) -- DEBUG
    local W = SprayDroneWaterHose
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        local spec = v[W.SPEC_NAME]
        if spec ~= nil then
            local index = tonumber(command:match("^whConnect(%d+)$"))
            if index ~= nil then
                if v[SprayDronePump.SPEC_NAME] ~= nil then
                    SprayDroneDebug.setPumpMode(v, false)
                end
                local port = W.getPorts(v, 1)[index]
                local active = false
                for _, a in ipairs(W.getActivePorts(v, 1)) do
                    active = active or a.index == index
                end
                if port ~= nil and active then
                    local px, py, pz = getWorldTranslation(port.node)
                    local source, bx, by, bz, bdx, bdz, push = W.findSourceAt(v, px, py, pz, 12, port.kind)
                    if source ~= nil then
                        v:sprayDroneWaterHoseCommand(W.CMD_DROP)
                        v:sprayDroneWaterHoseCommand(W.CMD_TAKE, nil, index, nil, bx, by, bz, -bdx, 0, -bdz)
                        v:sprayDroneWaterHoseCommand(W.CMD_CONNECT, source, push and W.TANK_ARG or 0, nil, bx, by, bz, bdx, 0, bdz)
                        Logging.info("SDT WH SIM: ventil %d (%s) pripojen k %s (id %s) na %s", index, port.kind, tostring(source:getName()), tostring(source.id), tostring(v:getName()))
                    else
                        Logging.info("SDT WH SIM: ventil %d (%s): zadny zdroj do 12 m", index, port.kind)
                    end
                end
            elseif command == "whPond" and v[SprayDronePump.SPEC_NAME] ~= nil then
                SprayDroneDebug.setPumpMode(v, true)
                local port = W.getPorts(v, 1)[1]
                local px, py, pz = getWorldTranslation(port.node)
                local best, bd
                for dx = -8, 8 do
                    for dz = -8, 8 do
                        local wx, wy, wz = W.findPondAt(v, px + dx, pz + dz)
                        local d = dx * dx + dz * dz
                        if wx ~= nil and (bd == nil or d < bd) then
                            best, bd = { wx, wy, wz }, d
                        end
                    end
                end
                if best ~= nil then
                    local dx, dz = best[1] - px, best[3] - pz
                    local l = math.max(math.sqrt(dx * dx + dz * dz), 0.01)
                    v:sprayDroneWaterHoseCommand(W.CMD_DROP, nil, nil, nil, nil, nil, nil, nil, nil, nil, 1)
                    v:sprayDroneWaterHoseCommand(W.CMD_TAKE, nil, 1, nil, best[1], best[2], best[3], dx / l, 0, dz / l, 1)
                    v:sprayDroneWaterHoseCommand(W.CMD_CONNECT, nil, W.POND_ARG, nil, best[1], best[2], best[3], dx / l, 0, dz / l, 1)
                    Logging.info("SDT WH SIM: kos pumpy %s polozen do vody na %.1f %.2f %.1f (%.1f m od pumpy)", tostring(v.id), best[1], best[2], best[3], math.sqrt(bd))
                else
                    Logging.info("SDT WH SIM: do 8 m od pumpy %s neni dost hluboka voda", tostring(v.id))
                end
            elseif command == "whOut" and v[SprayDronePump.SPEC_NAME] ~= nil then
                local port = W.getPorts(v, 2)[1]
                local px, py, pz = getWorldTranslation(port.node)
                local target, tIndex, bx, by, bz, bdx, bdz = W.findSinkAt(v, spec.hoses[2], px, py, pz, 12)
                if target ~= nil then
                    v:sprayDroneWaterHoseCommand(W.CMD_DROP, nil, nil, nil, nil, nil, nil, nil, nil, nil, 2)
                    v:sprayDroneWaterHoseCommand(W.CMD_TAKE, nil, 1, nil, bx, by, bz, -bdx, 0, -bdz, 2)
                    v:sprayDroneWaterHoseCommand(W.CMD_CONNECT, target, tIndex, nil, bx, by, bz, bdx, 0, bdz, 2)
                    Logging.info("SDT WH SIM: vystup pumpy %s pripojen k ventilu %d vleku %s", tostring(v.id), tIndex, tostring(target:getName()))
                else
                    Logging.info("SDT WH SIM: vystup pumpy %s: zadny volny vodni ventil do 12 m", tostring(v.id))
                end
            elseif command == "whDrop" then
                for hi = 1, #spec.hoses do
                    v:sprayDroneWaterHoseCommand(W.CMD_DROP, nil, nil, nil, nil, nil, nil, nil, nil, nil, hi)
                end
            end
        end
    end
end

-- Zkušební Middle: vlek 8 m před kamerou, výchozí konfigurace (rtk = přesná GPS RTK). -- DEBUG
function SprayDroneDebug.spawnMiddle(rtk) -- DEBUG
    local cam = getCamera()
    local cx, _, cz = getWorldTranslation(cam)
    local dx, _, dz = localDirectionToWorld(cam, 0, 0, -1)
    local len = math.sqrt(dx * dx + dz * dz)
    local x, z = cx + dx / len * 9, cz + dz / len * 9
    local data = VehicleLoadingData.new()
    data:setFilename(g_modManager:getModByName(SprayDroneWaterHose.MOD_NAME).modDir .. "vehicles/sprayDroneTrailerMiddle/sprayDroneTrailerMiddle.xml")
    data:setPosition(x, getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.1, z)
    data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(1)
    if rtk then
        data:setConfigurations({ [SprayDroneStation.GPS_CONFIG] = 2 })
    end
    data:load(function(_, vehicles, state)
        local v = vehicles ~= nil and vehicles[1] or nil
        local spec = v ~= nil and v[SprayDroneStation.SPEC_NAME] or nil
        Logging.info("SDT MIDDLE: %s (vozidlo %s, rezerva aplikace podle skenu %s m)", state == VehicleLoadingState.OK and v ~= nil and "hotovo" or "nepodařilo se načíst",
            tostring(v ~= nil and v.id), tostring(spec ~= nil and spec.spotMargin))
    end)
end

-- Smaže z hry všechny vleky Middle (aby nezavazely při focení). -- DEBUG
function SprayDroneDebug.removeMiddle() -- DEBUG
    local list = {}
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v.configFileName ~= nil and v.configFileName:find("sprayDroneTrailerMiddle", 1, true) then
            table.insert(list, v)
        end
    end
    for _, v in ipairs(list) do
        Logging.info("SDT MIDDLE: mažu vlek %s", tostring(v.id))
        v:delete()
    end
end

-- Zkušební scény pro focení (příkazy dostávají šest čísel z atributu view v debug.xml: tools/sdt_debug.ps1 -Raw "a,b,c,d,e,f"). -- DEBUG
local function terrainY(x, z)
    return getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
end

local function firstWithSpec(specName)
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v[specName] ~= nil then
            return v
        end
    end
    return nil
end

local function spawnAt(filename, x, y, z, yaw, onLoad)
    local data = VehicleLoadingData.new()
    data:setFilename(filename)
    data:setPosition(x, y, z)
    data:setRotation(0, yaw, 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(1)
    data:load(function(_, vehicles, state)
        local v = vehicles ~= nil and vehicles[1] or nil
        if state ~= VehicleLoadingState.OK or v == nil then
            Logging.info("SDT SCENA: nepodařilo se načíst %s", filename)
            return
        end
        onLoad(v)
    end)
end

-- Břehy vody do radius m kolem hráče (první číslo, výchozí 500): rovná zem u hladiny, odstup aspoň 60 m, vypíše 25 nejbližších. -- DEBUG
function SprayDroneDebug.shoreScan() -- DEBUG
    local cx, _, cz = g_localPlayer:getPosition()
    local a = SprayDroneDebug.view or {}
    local radius, step, apartMin, count = a[1] or 500, math.max(a[2] or 20, 5), a[3] or 60, a[4] or 25
    if (a[5] or 0) ~= 0 or (a[6] or 0) ~= 0 then
        cx, cz = a[5], a[6]
    end
    local hit = {}
    function hit:callback(nodeId, x, y)
        if nodeId ~= 0 then
            self.y = y
        end
    end
    local found = {}
    local waterPoints, notFlat = 0, 0
    for x = cx - radius, cx + radius, step do
        for z = cz - radius, cz + radius, step do
            local ground = terrainY(x, z)
            hit.y = nil
            raycastClosest(x, ground + 40, z, 0, -1, 0, 80, "callback", hit, CollisionFlag.WATER)
            if hit.y ~= nil and hit.y - ground >= 0.6 then
                local dx, dz = cx - x, cz - z
                local l = math.sqrt(dx * dx + dz * dz)
                if l < 1 then
                    dx, dz, l = 1, 0, 1
                end
                dx, dz = dx / l, dz / l
                local sx, sz = x, z
                for _ = 1, 160 do
                    if hit.y - terrainY(sx, sz) < 0.05 then
                        break
                    end
                    sx, sz = sx + dx * 0.5, sz + dz * 0.5
                end
                local g0 = terrainY(sx, sz)
                local flat = true
                for _, o in ipairs({ { 4, 0 }, { -4, 0 }, { 0, 4 }, { 0, -4 } }) do
                    flat = flat and math.abs(terrainY(sx + o[1], sz + o[2]) - g0) < 1.2
                end
                local apart = true
                for _, f in ipairs(found) do
                    apart = apart and MathUtil.vector2Length(f.x - sx, f.z - sz) >= apartMin
                end
                waterPoints = waterPoints + 1
                if not flat then
                    notFlat = notFlat + 1
                end
                if flat and apart and hit.y - g0 < 0.4 then
                    table.insert(found, { x = sx, z = sz, wy = hit.y, dx = -dx, dz = -dz, d = MathUtil.vector2Length(sx - cx, sz - cz) })
                end
            end
        end
    end
    Logging.info("SDT BREH: hráč %.0f %.0f, bodů s vodou %d, z toho nerovných %d, břehů %d", cx, cz, waterPoints, notFlat, #found)
    table.sort(found, function(a, b) return a.d < b.d end)
    for i = 1, math.min(#found, count) do
        local f = found[i]
        Logging.info("SDT BREH %d: %.1f %.1f hladina %.2f smer k vode %.2f %.2f vzdalenost %.0f", i, f.x, f.z, f.wy, f.dx, f.dz, f.d)
    end
end

-- Hráč na bod (první tři čísla, výška očí) s pohledem na druhý bod (další tři čísla), vše ve světových souřadnicích. -- DEBUG
function SprayDroneDebug.worldView() -- DEBUG
    local a = SprayDroneDebug.view
    if a == nil then
        return
    end
    g_localPlayer.mover:setFlightActive(true, true)
    g_localPlayer.mover:teleportTo(a[1], a[2] - SprayDroneDebug.EYE_HEIGHT, a[3], true)
    local dx, dy, dz = a[4] - a[1], a[5] - a[2], a[6] - a[3]
    local len = MathUtil.vector3Length(dx, dy, dz)
    local pitch, yaw = MathUtil.directionToPitchYaw(dx / len, dy / len, dz / len)
    g_localPlayer.camera:setRotation(pitch, yaw, 0)
end

-- Stanoviště u rybníka: pumpa (x z = první dvě čísla) výtlakem k vleku, směr k vodě = třetí a čtvrté číslo; velký vlek stojí podél břehu bokem s vodními
-- ventily k vodě a pumpa stojí v odstupu pátého čísla (výchozí 3 m) před jeho prvním ventilem. -- DEBUG
function SprayDroneDebug.pondSetup() -- DEBUG
    local a = SprayDroneDebug.view
    local pump = firstWithSpec(SprayDronePump.SPEC_NAME)
    local trailer = firstWithSpec(SprayDroneStation.SPEC_NAME)
    if a == nil or pump == nil or trailer == nil then
        Logging.info("SDT SCENA: pondSetup – chybí pumpa, vlek nebo čísla")
        return
    end
    local sx, sz, dx, dz, gap = a[1], a[2], a[3], a[4], a[5] ~= 0 and a[5] or 3
    local pumpYaw = MathUtil.getYRotationFromDirection(-dz, dx)
    pump:setAbsolutePosition(sx, terrainY(sx, sz) + 0.2, sz, 0, pumpYaw, 0)
    local spec = pump[SprayDronePump.SPEC_NAME]
    pump:addFillUnitFillLevel(1, spec.dieselUnit, 15, FillType.DIESEL, ToolType.UNDEFINED, nil)
    pump:addFillUnitFillLevel(1, spec.waterUnit, -1e6, FillType.WATER, ToolType.UNDEFINED, nil)
    SprayDroneDebug.setPumpMode(pump, true)
    local fx, fz = dz, -dx
    local tx, tz = sx - dx * (gap + 0.89) + 1.44 * fx, sz - dz * (gap + 0.89) + 1.44 * fz
    trailer:setAbsolutePosition(tx, terrainY(tx, tz) + 0.4, tz, 0, MathUtil.getYRotationFromDirection(fx, fz), 0)
    Logging.info("SDT SCENA: rybník – pumpa %.1f %.1f, vlek %.1f %.1f", sx, sz, tx, tz)
end

-- Mapa vody kolem bodu (první dvě čísla; třetí = poloměr, výchozí 30; čtvrté = krok, výchozí 3): řádky ze (sever dole) po z, ~ = voda, . = souš. -- DEBUG
function SprayDroneDebug.waterMap() -- DEBUG
    local a = SprayDroneDebug.view or {}
    local cx, cz, radius, step = a[1] or 0, a[2] or 0, a[3] ~= nil and a[3] > 0 and a[3] or 30, a[4] ~= nil and a[4] > 0 and a[4] or 3
    local hit = {}
    function hit:callback(nodeId, x, y)
        if nodeId ~= 0 then
            self.y = y
        end
    end
    Logging.info("SDT MAPA vody: stred %.0f %.0f polomer %.0f krok %.0f (sloupce x od %.0f)", cx, cz, radius, step, cx - radius)
    for z = cz - radius, cz + radius, step do
        local row = {}
        for x = cx - radius, cx + radius, step do
            local ground = terrainY(x, z)
            hit.y = nil
            raycastClosest(x, ground + 40, z, 0, -1, 0, 80, "callback", hit, CollisionFlag.WATER)
            row[#row + 1] = (hit.y ~= nil and hit.y - ground >= 0.3) and "~" or "."
        end
        Logging.info("SDT MAPA z=%.0f %s", z, table.concat(row))
    end
end

-- Stanoviště na dvoře: pumpa 3 m od prvního vodního ventilu vleku, za ní (na straně vtoku) IBC s vodou a cisterna 4,5 m od druhého ventilu. -- DEBUG
function SprayDroneDebug.station2() -- DEBUG
    local trailer
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v[SprayDroneStation.SPEC_NAME] ~= nil and v[SprayDroneWaterHose.SPEC_NAME] ~= nil then
            trailer = v
        end
    end
    local pump = firstWithSpec(SprayDronePump.SPEC_NAME)
    local ports = trailer ~= nil and SprayDroneWaterHose.getActivePorts(trailer) or {}
    local water = {}
    for _, p in ipairs(ports) do
        if p.port.kind == "water" then
            table.insert(water, p)
        end
    end
    if pump == nil or #water < 2 then
        Logging.info("SDT SCENA: station2 – chybí pumpa nebo dva vodní ventily vleku")
        return
    end
    local function outward()
        local ox, _, oz = localDirectionToWorld(trailer.rootNode, -1, 0, 0)
        local l = math.sqrt(ox * ox + oz * oz)
        return ox / l, oz / l
    end
    local ox, oz = outward()
    local x1, _, z1 = getWorldTranslation(water[1].node)
    local x2, _, z2 = getWorldTranslation(water[2].node)
    local px, pz = x1 + ox * 3, z1 + oz * 3
    pump:setAbsolutePosition(px, terrainY(px, pz) + 0.2, pz, 0, MathUtil.getYRotationFromDirection(-oz, ox), 0)
    local ps = pump[SprayDronePump.SPEC_NAME]
    pump:addFillUnitFillLevel(1, ps.dieselUnit, 15, FillType.DIESEL, ToolType.UNDEFINED, nil)
    pump:addFillUnitFillLevel(1, ps.waterUnit, -1e6, FillType.WATER, ToolType.UNDEFINED, nil)
    SprayDroneDebug.setPumpMode(pump, false)
    local ibcMod = g_modManager:getModByName("FS25_lsfmUniversalTankPack")
    if ibcMod ~= nil then
        local ix, iz = px + ox * 2.6, pz + oz * 2.6
        spawnAt(ibcMod.modDir .. "objects/ibcTank_fillable.xml", ix, terrainY(ix, iz) + 0.1, iz, MathUtil.getYRotationFromDirection(-oz, ox), function(v)
            v:addFillUnitFillLevel(1, 1, 1000, FillType.WATER, ToolType.UNDEFINED, nil)
            Logging.info("SDT SCENA: IBC id %s na %.1f %.1f", tostring(v.id), ix, iz)
        end)
    end
    local cx, cz = x2 + ox * 5, z2 + oz * 5
    spawnAt("data/vehicles/abi/waterTrailer550/waterTrailer550.xml", cx, terrainY(cx, cz) + 0.3, cz, MathUtil.getYRotationFromDirection(ox, oz), function(v)
        v:addFillUnitFillLevel(1, 1, 2000, FillType.WATER, ToolType.UNDEFINED, nil)
        Logging.info("SDT SCENA: cisterna id %s na %.1f %.1f", tostring(v.id), cx, cz)
    end)
end

SprayDroneDebug.CISTERNS = {
    { path = "data/vehicles/abi/waterTrailer550/waterTrailer550.xml" },
    { path = "data/vehicles/abi/waterTrailer1600/waterTrailer1600.xml" },
    { mod = "FS25_lsfmUniversalTankPack", path = "lsfmUniversalTankTrailer2500L.xml" },
    { mod = "FS25_lsfmUniversalTankPack", path = "lsfmUniversalTankTrailer7500L.xml" },
    { mod = "FS25_LizardSelfMadeWaterTank", path = "LizardSelfMadeWaterTank.xml" },
}

-- Cisterna číslo a1 ze SprayDroneDebug.CISTERNS (smaže předchozí), 5 m od druhého vodního ventilu vleku, natočená o a2 stupňů proti směru ven, s vodou;
-- hned k ní připojí hadici z ventilu 4 (a3 = 1: druhý ventil jako výchozí, jinak číslo ventilu). -- DEBUG
function SprayDroneDebug.cistern() -- DEBUG
    local a = SprayDroneDebug.view or {}
    local entry = SprayDroneDebug.CISTERNS[a[1] or 1]
    local trailer
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v[SprayDroneStation.SPEC_NAME] ~= nil and v[SprayDroneWaterHose.SPEC_NAME] ~= nil then
            trailer = v
        end
    end
    if entry == nil or trailer == nil then
        Logging.info("SDT SCENA: cistern – chybí záznam nebo vlek")
        return
    end
    if SprayDroneDebug.lastCistern ~= nil and not SprayDroneDebug.lastCistern.isDeleted then
        SprayDroneDebug.lastCistern:delete()
    end
    SprayDroneDebug.lastCistern = nil
    local filename = entry.path
    if entry.mod ~= nil then
        local mod = g_modManager:getModByName(entry.mod)
        if mod == nil then
            Logging.info("SDT SCENA: cistern – mod %s není načtený", entry.mod)
            return
        end
        filename = mod.modDir .. entry.path
    end
    local water = {}
    for _, p in ipairs(SprayDroneWaterHose.getActivePorts(trailer)) do
        if p.port.kind == "water" then
            table.insert(water, p)
        end
    end
    local ox, _, oz = localDirectionToWorld(trailer.rootNode, -1, 0, 0)
    local l = math.sqrt(ox * ox + oz * oz)
    ox, oz = ox / l, oz / l
    local x2, _, z2 = getWorldTranslation(water[2].node)
    local cx, cz = x2 + ox * 5, z2 + oz * 5
    local yaw = MathUtil.getYRotationFromDirection(ox, oz) + math.rad(a[2] or 0)
    spawnAt(filename, cx, terrainY(cx, cz) + 0.3, cz, yaw, function(v)
        SprayDroneDebug.lastCistern = v
        for i = 1, #v.spec_fillUnit.fillUnits do
            if v:getFillUnitSupportsFillType(i, FillType.WATER) then
                v:addFillUnitFillLevel(1, i, v:getFillUnitCapacity(i) * 0.8, FillType.WATER, ToolType.UNDEFINED, nil)
                break
            end
        end
        local nodes = {}
        for _, dn in ipairs(v.spec_dischargeable ~= nil and v.spec_dischargeable.dischargeNodes or {}) do
            local nx, ny, nz = getWorldTranslation(dn.node)
            local lx, ly, lz = worldToLocal(v.rootNode, nx, ny, nz)
            table.insert(nodes, string.format("(%.2f %.2f %.2f)", lx, ly, lz))
        end
        Logging.info("SDT SCENA: cisterna %s id %s na %.1f %.1f, vypouštěcí uzly lokálně: %s", entry.path, tostring(v.id), cx, cz, table.concat(nodes, " "))
        if (a[3] or 4) ~= 0 then
            SprayDroneDebug.waterHoseSim("whConnect" .. tostring(a[3] or 4))
        end
    end)
end

SprayDroneDebug.SCENES = { shoreScan = SprayDroneDebug.shoreScan, worldView = SprayDroneDebug.worldView, pondSetup = SprayDroneDebug.pondSetup,
    station2 = SprayDroneDebug.station2, cistern = SprayDroneDebug.cistern, waterMap = SprayDroneDebug.waterMap }

-- Nejbližší voda kolem hráče: mřížka paprsků shora na hladinu (CollisionFlag.WATER), hloubka = hladina nad terénem. Vrací x, z, hladinu. -- DEBUG
function SprayDroneDebug.findWater(minDepth) -- DEBUG
    local px, _, pz = g_localPlayer:getPosition()
    local hit = {}
    function hit:callback(nodeId, x, y)
        if nodeId ~= 0 then
            self.y = y
        end
    end
    local best
    for ring = 1, 60 do
        for i = -ring, ring do
            for _, p in ipairs({ { i, -ring }, { i, ring }, { -ring, i }, { ring, i } }) do
                local x, z = px + p[1] * 20, pz + p[2] * 20
                local ground = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
                hit.y = nil
                raycastClosest(x, ground + 40, z, 0, -1, 0, 80, "callback", hit, CollisionFlag.WATER)
                if hit.y ~= nil and hit.y - ground >= minDepth then
                    return x, z, hit.y
                end
            end
        end
    end
    return nil
end

-- Zkušební pumpa: najde nejbližší vodu, postaví pumpu na břeh sacím košem do vody a přenese k ní hráče. -- DEBUG
function SprayDroneDebug.spawnPump() -- DEBUG
    local wx, wz, wy = SprayDroneDebug.findWater(0.6)
    if wx == nil then
        Logging.info("SDT PUMP: v okolí 1200 m není voda")
        return
    end
    local px, _, pz = g_localPlayer:getPosition()
    local dx, dz = wx - px, wz - pz
    local len = math.sqrt(dx * dx + dz * dz)
    dx, dz = dx / len, dz / len
    -- od vody zpět k hráči, dokud hloubka neklesne pod 0,05 m: břeh
    local sx, sz = wx, wz
    for _ = 1, 400 do
        local ground = getTerrainHeightAtWorldPos(g_terrainNode, sx, 0, sz)
        if wy - ground < 0.05 then
            break
        end
        sx, sz = sx - dx * 0.5, sz - dz * 0.5
    end
    local data = VehicleLoadingData.new()
    data:setFilename(g_modManager:getModByName(SprayDronePump.MOD_NAME).modDir .. "objects/pump/waterPump.xml")
    data:setPosition(sx - dx, getTerrainHeightAtWorldPos(g_terrainNode, sx - dx, 0, sz - dz) + 0.2, sz - dz)
    data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(1)
    data:load(function(_, vehicles, state)
        local v = vehicles ~= nil and vehicles[1] or nil
        if state ~= VehicleLoadingState.OK or v == nil then
            Logging.info("SDT PUMP: nepodařilo se načíst")
            return
        end
        local spec = v[SprayDronePump.SPEC_NAME]
        v:addFillUnitFillLevel(1, spec.dieselUnit, 15, FillType.DIESEL, ToolType.UNDEFINED, nil)
        local ex, ey, ez = getWorldTranslation(spec.engineNode)
        g_localPlayer.mover:setFlightActive(true, true)
        g_localPlayer.mover:teleportTo(ex - dz * 1.8, ey + 0.5 - SprayDroneDebug.EYE_HEIGHT, ez + dx * 1.8, true)
        local pitch, yaw = MathUtil.directionToPitchYaw(dz, -0.3, -dx)
        g_localPlayer.camera:setRotation(pitch, yaw, 0)
        Logging.info("SDT PUMP: pumpa id %s u vody (břeh %.1f %.1f, hladina %.2f)", tostring(v.id), sx, sz, wy)
    end)
end

-- Které uzly mlýnku se mezi dvěma voláními mění (poloha vůči rodiči i natočení): nodeSnap uloží, nodeDiff vypíše změněné. -- DEBUG
function SprayDroneDebug.nodeSnap(command) -- DEBUG
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v[SprayDroneMill.SPEC_NAME] ~= nil then
            local snap = {}
            local function walk(node)
                local rx, ry, rz = getRotation(node)
                local tx, ty, tz = getTranslation(node)
                snap[node] = { rx, ry, rz, tx, ty, tz }
                if command == "nodeDiff" and SprayDroneDebug.snaps ~= nil and SprayDroneDebug.snaps[v.id] ~= nil then
                    local old = SprayDroneDebug.snaps[v.id][node]
                    if old ~= nil then
                        for i = 1, 6 do
                            if math.abs(old[i] - snap[node][i]) > 1e-4 then
                                Logging.info("SDT NODE mění se: %s (složka %d: %.4f -> %.4f)", getName(node), i, old[i], snap[node][i])
                                break
                            end
                        end
                    end
                end
                for i = 0, getNumOfChildren(node) - 1 do
                    walk(getChildAt(node, i))
                end
            end
            for _, component in ipairs(v.components) do
                walk(component.node)
            end
            SprayDroneDebug.snaps = SprayDroneDebug.snaps or {}
            SprayDroneDebug.snaps[v.id] = snap
            Logging.info("SDT NODE %s: mlýnek id %s, uzlů %d", command, tostring(v.id), (function() local n = 0 for _ in pairs(snap) do n = n + 1 end return n end)())
        end
    end
end

-- Pohled na mlýnek: millView1 zleva, millView2 zprava, millView3 zezadu (hráč 4 m od vozíku, výška 1,6 m, kamera na střed vozíku). -- DEBUG
function SprayDroneDebug.millView(command) -- DEBUG
    local offsets = { millView1 = { 4, 1.6, 0 }, millView2 = { -4, 1.6, 0 }, millView3 = { 0, 1.6, -5 },
        pumpView1 = { 2.2, 1.3, 1.0 }, pumpView2 = { -2.2, 1.3, 1.0 }, pumpView3 = { 0, 1.5, -2.5 }, pumpView4 = { 0.5, 3.5, -3.5 } }
    local specName = command:find("^pumpView") and SprayDronePump.SPEC_NAME or SprayDroneMill.SPEC_NAME
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v[specName] ~= nil and (specName ~= SprayDronePump.SPEC_NAME or v[SprayDroneHopper.SPEC_NAME] == nil) then
            local o = offsets[command]
            local cx, cy, cz = localToWorld(v.rootNode, o[1], o[2], o[3])
            local tx, ty, tz = localToWorld(v.rootNode, 0, specName == SprayDronePump.SPEC_NAME and 0.3 or 1.0, 0)
            local player = g_localPlayer
            player.mover:setFlightActive(true, true)
            player.mover:teleportTo(cx, cy - SprayDroneDebug.EYE_HEIGHT, cz, true)
            local dx, dy, dz = tx - cx, ty - cy, tz - cz
            local len = MathUtil.vector3Length(dx, dy, dz)
            local pitch, yaw = MathUtil.directionToPitchYaw(dx / len, dy / len, dz / len)
            player.camera:setRotation(pitch, yaw, 0)
            return
        end
    end
end

-- Pumpa 3 m od prvního ventilu vody vleku s vodní hadicí (pro zkoušku napojení hadice mimo břeh). -- DEBUG
function SprayDroneDebug.pumpToTrailer() -- DEBUG
    for _, t in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if t[SprayDroneWaterHose.SPEC_NAME] ~= nil then
            local port = SprayDroneWaterHose.getActivePorts(t)[1]
            for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
                if port ~= nil and v[SprayDronePump.SPEC_NAME] ~= nil then
                    local x, y, z = getWorldTranslation(port.node)
                    local ox, _, oz = localDirectionToWorld(t.rootNode, -1, 0, 0)
                    local l = math.sqrt(ox * ox + oz * oz)
                    ox, oz = ox / l, oz / l
                    local px, pz = x + ox * 3, z + oz * 3
                    v:setAbsolutePosition(px, getTerrainHeightAtWorldPos(g_terrainNode, px, 0, pz) + 0.2, pz, 0, MathUtil.getYRotationFromDirection(-oz, ox), 0)
                    Logging.info("SDT PUMP: pumpa %s přesunuta k ventilu vleku %s", tostring(v.id), tostring(t.id))
                    return
                end
            end
        end
    end
end

-- Pumpa 2,5 m od vypouštěcího uzlu nejbližšího IBC / cisterny (pro zkoušku sací hadice). -- DEBUG
function SprayDroneDebug.pumpToIbc() -- DEBUG
    for _, src in ipairs(g_currentMission.vehicleSystem.vehicles) do
        local dn = src.spec_dischargeable ~= nil and src.spec_dischargeable.dischargeNodes ~= nil and src.spec_dischargeable.dischargeNodes[1] or nil
        local hasWater = false
        for i = 1, src.spec_fillUnit ~= nil and #src.spec_fillUnit.fillUnits or 0 do
            hasWater = hasWater or src:getFillUnitFillType(i) == FillType.WATER and src:getFillUnitFillLevel(i) > 1
        end
        if hasWater and dn ~= nil and dn.node ~= nil and entityExists(dn.node) and src[SprayDronePump.SPEC_NAME] == nil then
            for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
                if v[SprayDronePump.SPEC_NAME] ~= nil then
                    local x, y, z = getWorldTranslation(dn.node)
                    local cx, _, cz = getWorldTranslation(src.rootNode)
                    local l = math.sqrt((x - cx) ^ 2 + (z - cz) ^ 2)
                    local ox, oz = 0, 1
                    if l > 0.05 then
                        ox, oz = (x - cx) / l, (z - cz) / l
                    end
                    local px, pz = x + ox * 2.5, z + oz * 2.5
                    v:setAbsolutePosition(px, getTerrainHeightAtWorldPos(g_terrainNode, px, 0, pz) + 0.2, pz, 0, MathUtil.getYRotationFromDirection(-oz, ox), 0)
                    Logging.info("SDT PUMP: pumpa %s přesunuta k výstupu %s (id %s) na %.1f %.1f %.1f, uzel y=%.2f", tostring(v.id), tostring(src:getName()),
                        tostring(src.id), px, y, pz, y)
                    return
                end
            end
        end
    end
    Logging.info("SDT PUMP: pumpToIbc – nenašel jsem IBC s vypouštěcím uzlem nebo pumpu")
end

-- Stav pump: motor, režim vstupu, hladiny, nafta; pumpModeTank / pumpModePond přepnou režim vstupu (jako levé tlačítko myši u spojky). -- DEBUG
function SprayDroneDebug.pumpStatus(command) -- DEBUG
    if command == "pumpToTrailer" then
        SprayDroneDebug.pumpToTrailer()
        return
    elseif command == "pumpToIbc" then
        SprayDroneDebug.pumpToIbc()
        return
    end
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        local ps = v[SprayDronePump.SPEC_NAME]
        if ps ~= nil then
            if command == "pumpOn" then
                v:sprayDronePumpCommand(SprayDronePump.CMD_ENGINE_ON)
            elseif command == "pumpOff" then
                v:sprayDronePumpCommand(SprayDronePump.CMD_ENGINE_OFF)
            elseif command == "pumpModeTank" or command == "pumpModePond" then
                if ps.pondMode ~= (command == "pumpModePond") then
                    v:sprayDronePumpCommand(SprayDronePump.CMD_MODE_TOGGLE)
                end
            end
            Logging.info("SDT PUMP id %s: motor=%s cerpa=%s vstup=%s | nafta %.2f l, voda v telese %.1f l", tostring(v.id), tostring(ps.engineOn), tostring(ps.flowing),
                ps.pondMode and "rybnik" or "nadrz", v:getFillUnitFillLevel(ps.dieselUnit), v:getFillUnitFillLevel(ps.waterUnit))
        end
    end
end

-- Příkazy, které se mají provést jednou na celou hru (ne jednou na vozidlo). -- DEBUG
-- Scénář hráče pro záznam do logu (DEBUG): mark:<kód> zapíše řádek "SDT KROK: <kód>" (kód kroku z tmp/prubeh.py, bez diakritiky), ostatní příkazy dělají to, co ruka hráče
-- mimo klávesy: nastoupit / vystoupit, zapřáhnout vlek za pickup a vybrat ho, koupit a vybrat nejbližší pole.
SprayDroneDebug.PLAY = { spawnHopper = true, hopperOn = true, hopperOff = true, hopperStatus = true, hopperBag = true, hopperBigBag = true, hopperFill = true,
    hopperCam = true, hopperDrop = true, hopperDrain = true, hopperLegs = true, hopperInfo = true, pumpStore = true, pumpTake = true, pumpSlotInfo = true, pumpFuel = true, enterMax = true, enterPickup = true, leaveSeat = true, attachMax = true, detachMax = true, selectMax = true, fieldInfo = true,
    ownField = true, selectField = true, lookBox = true, fillLime = true, clearBags = true, millModeBag = true, millModeHose = true,
    millValve = true, millSpout = true, millBagInfo = true,
    spawnLimeBigBag = true, spawnLimeBigBagFull = true, bagStatus = true, millCam = true, scanMode = true, sprayMode = true, scanCell0 = true,
    scanCell1 = true, scanCell2 = true, scanInfo = true, scanSetWeeds = true, scanBlockDark = true, scanBlockRain = true, scanBlockWind = true,
    scanBlockNone = true, scanConditions = true, droneCam = true, scanPlanner = true, scanPlannerClose = true, scanLayerOff = true,
    scanLayerWeed = true, scanLayerLime = true, scanLayerFert = true, scanLayerRipe = true, scanLayerStone = true, scanLayerCover = true, scanLayerNitrogen = true, scanLayerPh = true,
    scanOverview = true, scanOverviewOff = true, scanOverviewPick = true, scanAge = true, scanPlannerMiddle = true }

for _, name in ipairs({ "padInfo", "padCam", "padStream", "padMiniStow", "padMiniDeploy", "padMiniInfo", "pad1None", "pad1S", "pad1M", "pad1L", "pad1K", "pad2None", "pad2S", "pad2M", "pad2L", "pad2K",
    "plannerReload", "plannerMiddle", "plannerPage1", "plannerPage2", "plannerPage3", "plannerPage4", "plannerLayout",
    "plannerOpen", "plannerNext", "plannerPrev", "plannerInfo" }) do
    SprayDroneDebug.PLAY[name] = true
end
for i = 1, 9 do
    SprayDroneDebug.PLAY["plannerOpen " .. i] = true
end

-- Přepínání cílů plánovače bez tabletu (DEBUG): plannerOpen = jako Alt+7 ve vozidle, ve kterém hráč sedí (pěšky nejbližší vlek / kufr
-- farmy, jako by v něm seděl); plannerOpen N = N-tý z plannerInfo (všechny vleky a kufry farmy od hráče), otevřený jako ze sedadla bez
-- podmínky nástupu; plannerNext / plannerPrev = PageDown / PageUp v otevřeném plánovači; plannerInfo = režim, origin, cíl a seznam cílů.
function SprayDroneDebug.plannerSwitchCommand(command)
    local screen = SprayDronePlannerScreen.INSTANCE
    local isOpen = screen ~= nil and screen:getIsOpen()
    local px, _, pz = 0, 0, 0
    if g_localPlayer ~= nil and g_localPlayer.getPosition ~= nil then
        px, _, pz = g_localPlayer:getPosition()
    end
    local all = SprayDroneLink.collectTrailers(px, pz, g_currentMission:getFarmId())
    if command == "plannerNext" or command == "plannerPrev" then
        if isOpen then
            screen:requestTarget(command == "plannerNext" and 1 or -1)
        end
    elseif command:find("^plannerOpen") then
        local n = tonumber(command:match("^plannerOpen (%d)$"))
        local seat = g_localPlayer ~= nil and g_localPlayer.getCurrentVehicle ~= nil and g_localPlayer:getCurrentVehicle() or nil
        if n == nil and seat ~= nil and seat[SprayDroneStation.SPEC_NAME] ~= nil then
            SprayDroneStation.actionEventOpenPlanner(seat)
        else
            local entry = all[n or 1]
            if n == nil then
                table.sort(all, function(a, b) return a.distance < b.distance end)
                entry = all[1]
            end
            if entry ~= nil then
                SprayDronePlannerScreen.show(entry.vehicle, SprayDronePlannerScreen.MODE_VEHICLE, entry.vehicle, true)
            end
        end
    end
    local lines = {}
    local targets = isOpen and SprayDroneLink.getPlannerTargets(screen.openMode, screen.originVehicle) or {}
    for i, e in ipairs(isOpen and targets or all) do
        table.insert(lines, string.format("%d) %s%s", i, SprayDroneLink.getTargetLabel(e),
            isOpen and e.vehicle == screen.vehicle and "  <- ovládaný" or ""))
    end
    Logging.info("SDT PLANNER: %s | režim %s, origin %s, cíl %s%s\n  %s", command, isOpen and tostring(screen.openMode) or "zavřeno",
        isOpen and screen.originVehicle ~= nil and tostring(screen.originVehicle.id) or "-", isOpen and tostring(screen.vehicle.id) or "-",
        isOpen and screen.debugAnywhere and " (bez podmínky otevření)" or "",
        #lines > 0 and table.concat(lines, "\n  ") or "žádný cíl")
end

-- Plánovač (DEBUG): plannerReload znovu načte skripty a XML obrazovky a otevře ji (bez restartu hry), plannerMiddle ji otevře
-- pro Middle, plannerPage1..4 přepne záložku, plannerLayout zapíše do logu polohy prvků v pixelech okna (pro skutečné kliky).
function SprayDroneDebug.plannerCommand(max, command)
    if command:find("^plannerOpen") or command == "plannerNext" or command == "plannerPrev" or command == "plannerInfo" then
        SprayDroneDebug.plannerSwitchCommand(command)
        return
    end
    local target = max
    if command == "plannerMiddle" then
        for _, vehicle in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if vehicle.configFileName ~= nil and vehicle.configFileName:find("sprayDroneTrailerMiddle", 1, true) then
                target = vehicle
            end
        end
    end
    if command == "plannerReload" then
        local old = SprayDronePlannerScreen.INSTANCE
        local modDir = SprayDronePlannerScreen.MOD_DIR
        local vehicle = old ~= nil and old.vehicle or max
        g_gui:showGui("")
        if old ~= nil then
            old:delete()
        end
        -- source() stejný soubor podruhé nespustí a loadfile je ve hře vypnutý: tmp/ui.ps1 -Reload zkopíruje skripty plánovače
        -- do _reload/<n>/ a tady se načte nejvyšší n
        local saved = g_currentModDirectory
        g_currentModDirectory = modDir
        local n = 1
        while fileExists(string.format("%s_reload/%d/SprayDronePlannerScreen.lua", modDir, n + 1)) do
            n = n + 1
        end
        local dir = string.format("%s_reload/%d/", modDir, n)
        if fileExists(dir .. "SprayDronePlannerScreen.lua") then
            for _, name in ipairs({ "SprayDronePlannerScreen.lua", "SprayDronePlannerCard.lua", "SprayDroneScanOverlay.lua" }) do
                source(dir .. name)
            end
            Logging.info("SDT plannerReload: skripty z %s", dir)
        end
        g_currentModDirectory = saved
        target = vehicle
    end
    local page = command:match("^plannerPage(%d)$")
    if page ~= nil then
        local screen = SprayDronePlannerScreen.INSTANCE
        if screen ~= nil and screen:getIsOpen() then
            screen:setPage(tonumber(page))
        end
        return
    end
    if command == "plannerLayout" then
        local screen = SprayDronePlannerScreen.INSTANCE
        if screen ~= nil and screen:getIsOpen() then
            screen:logLayout()
        end
        return
    end
    SprayDronePlannerScreen.show(target, SprayDronePlannerScreen.MODE_TABLET)
    Logging.info("SDT PLAY: plánovač otevřen (%s): %s", command, tostring(g_gui:getIsGuiVisible()))
end

-- Zkouška proudu vleku bez druhého počítače (DEBUG): stream* funkce se na chvíli nahradí frontou, vlek zapíše stav pro připojení
-- (onWriteStream), pak se mu plošiny rozhodí na L/L (jako klient se starým stavem) a stejný proud se přečte zpět (onReadStream).
-- Proud sedí, když se přečte přesně tolik hodnot téhož druhu, kolik se zapsalo, a plošiny jsou zase jako při zápisu.
function SprayDroneDebug.padStream(max)
    local spec = SprayDroneDrones.getRoot(max)
    local before = SprayDroneStation.getPadsText(max)
    local queue, pos, errors = {}, 0, {}
    -- _G je tu prostředí modu (funkce enginu jsou až přes __index): náhrada v něm platí pro skripty modu
    local names = {}
    for _, kind in ipairs({ "UIntN", "Bool", "Float32", "UInt8", "UInt16", "Int32", "String" }) do
        local write, read = "streamWrite" .. kind, "streamRead" .. kind
        names[write], names[read] = rawget(_G, write) or false, rawget(_G, read) or false
        _G[write] = function(_, value)
            table.insert(queue, { kind, value })
            return value
        end
        _G[read] = function()
            pos = pos + 1
            local entry = queue[pos]
            if entry == nil then
                table.insert(errors, string.format("%d: čtení %s za koncem", pos, kind))
                return kind == "Bool" and false or (kind == "String" and "" or 0)
            end
            if entry[1] ~= kind then
                table.insert(errors, string.format("%d: zapsáno %s, čteno %s", pos, entry[1], kind))
            end
            return entry[2]
        end
    end
    local saved = names
    local connection = { getIsServer = function() return false end }
    local ok, err = pcall(function()
        SprayDroneStation.onWriteStream(max, 0, connection)
        local pads = {}
        for i = 1, spec.numPads do
            pads[i] = "L"
        end
        SprayDroneStation.applyPads(max, pads)
        SprayDroneStation.onReadStream(max, 0, connection)
    end)
    for name, fn in pairs(saved) do
        rawset(_G, name, fn or nil)
    end
    Logging.info("SDT PLAY: proud vleku: zapsáno %d hodnot, přečteno %d, chyb %d%s | plošiny před %s, po rozhození a čtení %s, dronů %d%s",
        #queue, pos, #errors, #errors > 0 and " (" .. table.concat(errors, "; ", 1, math.min(#errors, 5)) .. ")" or "", before,
        SprayDroneStation.getPadsText(max), spec.numDrones, ok and "" or " | CHYBA " .. tostring(err))
end

-- Mini, dvě polohy dronu (DEBUG, docs/NAVRH-dron-predmet.md kap. 12): padMiniStow = dron do bedny, padMiniDeploy = na plošinu (bez hráče,
-- jako R s prázdnýma rukama u druhého místa, okamžitě), padMiniInfo = poloha, bedna, start a složení vleku do logu. Platí pro první Mini.
function SprayDroneDebug.padMiniCommand(command)
    local mini = nil
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        local s = v[SprayDroneStation.SPEC_NAME]
        if mini == nil and s ~= nil and s.pad ~= nil and not v.isDeleted then
            mini = v
        end
    end
    if mini == nil then
        Logging.info("SDT PLAY: Mini ve světě není")
        return
    end
    if command == "padMiniStow" or command == "padMiniDeploy" then
        local problem = SprayDronePadSlots.debugMoveMini(mini, command == "padMiniDeploy")
        Logging.info("SDT PLAY: Mini %s %s: %s", tostring(mini.id), command == "padMiniDeploy" and "na plošinu" or "do bedny",
            problem ~= nil and "odmítnuto " .. problem .. " (" .. g_i18n:getText(problem) .. ")" or "ok")
        if problem ~= nil then
            g_currentMission:showBlinkingWarning(g_i18n:getText(problem), 2500)
        end
    end
    local spec = SprayDroneDrones.getRoot(mini)
    local foldOk, foldWarning = mini:getIsFoldAllowed(1, false)
    local unfoldOk, unfoldWarning = mini:getIsFoldAllowed(-1, false)
    Logging.info("SDT PLAY: Mini %s: plošina %s, dron %s, bedna %.2f (čas skládání %.3f), dron unfold %.2f cíl %.2f foldHold %s | start: %s | složit: %s %s | rozložit: %s %s",
        tostring(mini.id), SprayDroneStation.getPadsText(mini), spec.pads[1] == "" and "-" or (spec.pad.onPlate and "na plošině (B)" or "v bedně (A)"),
        SprayDronePad.getDeploy(mini), mini:getFoldAnimTime(), spec.unfold or -1, SprayDroneStation.getDroneUnfoldTarget(mini), tostring(spec.foldHold),
        tostring(SprayDroneStation.getFoldedWarning(mini) or (SprayDroneStation.getCanStart(mini) and "jde" or "ne (pole / dron)")),
        tostring(foldOk), tostring(foldWarning), tostring(unfoldOk), tostring(unfoldWarning))
end

-- Dron na plošině (DEBUG, etapa 0 docs/NAVRH-dron-predmet.md): pad<i><None|S|M|L|K> = SprayDroneStation.setPadDrone, padInfo = plošiny,
-- drony a parametry do logu, padCam = hráč šikmo nad bokem vleku s pohledem na plošiny; padMini* viz padMiniCommand.
function SprayDroneDebug.padCommand(max, command)
    if command:find("^padMini") then
        SprayDroneDebug.padMiniCommand(command)
        return
    end
    local spec = SprayDroneDrones.getRoot(max)
    local index, name = command:match("^pad(%d)(%a+)$")
    if index ~= nil then
        local variant = name ~= "None" and name or ""
        local problem = SprayDroneStation.setPadDrone(max, tonumber(index), variant)
        Logging.info("SDT PLAY: plošina %s -> %s: %s", index, name, problem ~= nil and "odmítnuto " .. problem .. " (" .. g_i18n:getText(problem) .. ")" or "ok")
        if problem ~= nil then
            g_currentMission:showBlinkingWarning(g_i18n:getText(problem), 2500)
        end
    elseif command == "padStream" then
        SprayDroneDebug.padStream(max)
    elseif command == "padCam" then
        local tx, ty, tz = localToWorld(max.rootNode, 0, 2.2, 0)
        local fx, fy, fz = localToWorld(max.rootNode, 9, 5.5, 3)
        fy = math.max(fy, getTerrainHeightAtWorldPos(g_terrainNode, fx, 0, fz) + 1)
        g_localPlayer.mover:setFlightActive(true, true)
        g_localPlayer.mover:teleportTo(fx, fy, fz, true)
        local ex, ey, ez = tx - fx, ty - (fy + SprayDroneDebug.EYE_HEIGHT), tz - fz
        local el = MathUtil.vector3Length(ex, ey, ez)
        local pitch, yaw = MathUtil.directionToPitchYaw(ex / el, ey / el, ez / el)
        g_localPlayer.camera:setRotation(pitch, yaw, 0)
    end
    local drones = {}
    for k = 1, spec.numDrones do
        local d = spec.drones[k]
        drones[k] = string.format("%d: %s %s stav %d unfold %.2f baterie %s (%.0f s) náplň %.1f l kamera %s rozsah %.0f",
            k, d.hasDrone and "dron" or "bez dronu", tostring(d.dronePrefix), d.state, d.unfold, tostring(d.droneBattery), d.battery,
            d.droneFillLevel, tostring(d.camera), d.range or -1)
    end
    local levels = {}
    for k, battery in ipairs(spec.batteries) do
        levels[k] = string.format("%d:%.0f%%@%d", k, battery.charge / spec.batteryCapacity * 100, battery.slot)
    end
    Logging.info("SDT PLAY: plošiny %s, dronů %d (v misi %d), první kamera %s | %s | %s | baterie %s", SprayDroneStation.getPadsText(max),
        spec.numDrones, spec.activeDrones, tostring(spec.firstDroneCamera), SprayDroneStation.getPadParamsText(max),
        table.concat(drones, " ; "), table.concat(levels, " "))
end

for _, name in ipairs({ "spotOn", "spotOff", "spotInfo", "spotLimeSet", "spotFillHerbicide", "spotFillLime", "spotLogStart",
    "weatherInfo", "windOff", "wind3", "wind6", "wind8", "wind10", "wind15", "scanTreatedInfo", "scanInfoFert", "scanFly", "scanPfInfo", "pfApi", "pfTarget", "pfSoil", "pfSample", "pfSend", "spotFillFertilizer",
    "spotFertSet", "takeoffCheck", "takeoffPlaces" }) do
    SprayDroneDebug.PLAY[name] = true
end

-- Aplikace podle skenu (DEBUG): spotOn / spotOff = nastavení aplikace, spotFillHerbicide / spotFillLime = hlavní nádrž vleku plná
-- herbicidu / vápna (dron prázdný), spotLimeSet = vápno 0 v západních 40 % pole, jinde plné, spotInfo = maska, srovnání plánů
-- a stav pole západ / východ (plevel, vápno, vrstva postřiku) do logu.
function SprayDroneDebug.spotCommand(max, command)
    local spec = max[SprayDroneStation.SPEC_NAME]
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    local minX, maxX, minZ, maxZ = math.huge, -math.huge, math.huge, -math.huge
    if field ~= nil then
        for _, p in ipairs(SprayDroneRoute.getPolygon(field)) do
            minX, maxX, minZ, maxZ = math.min(minX, p.x), math.max(maxX, p.x), math.min(minZ, p.z), math.max(maxZ, p.z)
        end
    end
    local cut = minX + (maxX - minX) * 0.4
    if command == "spotLogStart" then
        SprayDroneDebug.sprayLog = {}
        Logging.info("SDT PLAY: záznam postřiku pruhů zapnut")
    elseif command == "spotOn" or command == "spotOff" then
        local settings = SprayDroneStation.getSettings(max)
        settings.applyMode = command == "spotOn" and 1 or 0
        max:setSprayDroneSettings(settings)
        Logging.info("SDT PLAY: aplikace %s", spec.applyMode == 1 and "podle skenu" or "celé pole")
    elseif command == "spotFillHerbicide" or command == "spotFillLime" or command == "spotFillFertilizer" then
        local fillType = command == "spotFillLime" and FillType.LIME or FillType.HERBICIDE
        if command == "spotFillFertilizer" then
            fillType = FillType.LIQUIDFERTILIZER
        end
        max:addFillUnitFillLevel(max:getOwnerFarmId(), spec.fillUnitIndex, -1e6, max:getFillUnitFillType(spec.fillUnitIndex), ToolType.UNDEFINED, nil)
        max:addFillUnitFillLevel(max:getOwnerFarmId(), spec.fillUnitIndex, 1e6, fillType, ToolType.UNDEFINED, nil)
        SprayDroneDrones.forEachSpec(max, function(d)
            d.droneFillLevel, d.droneFillType = 0, FillType.UNKNOWN
        end)
        SprayDroneStation.markRouteDirty(max)
        Logging.info("SDT PLAY: hlavní nádrž %.0f l %s", max:getFillUnitFillLevel(spec.fillUnitIndex), g_fillTypeManager:getFillTypeNameByIndex(fillType))
    elseif command == "spotLimeSet" and field ~= nil then
        local system = g_currentMission.fieldGroundSystem
        local mapId, first, num = system:getDensityMapData(FieldDensityMap.LIME_LEVEL)
        local maxLevel = system:getMaxValue(FieldDensityMap.LIME_LEVEL)
        local modifier = DensityMapModifier.new(mapId, first, num, g_terrainNode)
        modifier:setParallelogramWorldCoords(cut, minZ, maxX, minZ, cut, maxZ, DensityCoordType.POINT_POINT_POINT)
        modifier:executeSet(maxLevel)
        modifier:setParallelogramWorldCoords(minX, minZ, cut, minZ, minX, maxZ, DensityCoordType.POINT_POINT_POINT)
        modifier:executeSet(0)
        Logging.info("SDT PLAY: vápno 0 na x %.0f..%.0f, jinde %d (max)", minX, cut, maxLevel)
    elseif command == "spotFertSet" and field ~= nil then
        local system = g_currentMission.fieldGroundSystem
        local mapId, first, num = system:getDensityMapData(FieldDensityMap.SPRAY_LEVEL)
        local maxLevel = system:getMaxValue(FieldDensityMap.SPRAY_LEVEL)
        local modifier = DensityMapModifier.new(mapId, first, num, g_terrainNode)
        modifier:setParallelogramWorldCoords(cut, minZ, maxX, minZ, cut, maxZ, DensityCoordType.POINT_POINT_POINT)
        modifier:executeSet(maxLevel)
        modifier:setParallelogramWorldCoords(minX, minZ, cut, minZ, minX, maxZ, DensityCoordType.POINT_POINT_POINT)
        modifier:executeSet(0)
        Logging.info("SDT PLAY: hnojení 0 na x %.0f..%.0f, jinde %d (max)", minX, cut, maxLevel)
    elseif command == "spotInfo" then
        local sprayType = SprayDroneStation.getSprayType(max)
        local mask = SprayDroneStation.getSpotMask(max, sprayType)
        Logging.info("SDT PLAY: přípravek %s, aplikace %d, maska %s, problém %s", sprayType ~= nil and tostring(sprayType.name) or "-",
            spec.applyMode, mask ~= nil and string.format("%d z %d buněk (nenask. %d), rezerva %.1f m, záběr %.1f m", mask.selected,
            mask.cells, mask.unscanned, mask.margin, (mask.halfWidth or 0) * 2) or "-", tostring(SprayDroneStation.getSpotProblem(max, sprayType)))
        local s = SprayDroneStation.getRouteSummaryAll(max)
        Logging.info("SDT PLAY: plán %d dávek, %.0f l, %.1f min, %.2f ha%s", s.numBatches, s.liters, s.minutes, s.areaHa,
            s.spot ~= nil and s.spot.fullLiters ~= nil and string.format(" | celé pole %.0f l, %.1f min", s.spot.fullLiters, s.spot.fullMinutes) or "")
        for _, line in ipairs(SprayDroneStation.getSpotTexts(s)) do
            Logging.info("SDT PLAY: plánovač: %s", line[1])
        end
        if field == nil then
            return
        end
        if SprayDroneDebug.sprayLog ~= nil then
            -- postříkané pruhy od spotLogStart: délka a litry západně / východně od řezu (pruh rozdělený na řezu poměrem)
            local sums = { { m = 0, l = 0 }, { m = 0, l = 0 } }
            for _, s in ipairs(SprayDroneDebug.sprayLog) do
                local len = MathUtil.vector2Length(s[3] - s[1], s[4] - s[2])
                local west = 0.5
                if math.abs(s[3] - s[1]) > 0.001 then
                    west = math.clamp((cut - math.min(s[1], s[3])) / math.abs(s[3] - s[1]), 0, 1)
                else
                    west = s[1] < cut and 1 or 0
                end
                sums[1].m, sums[1].l = sums[1].m + len * west, sums[1].l + s[5] * west
                sums[2].m, sums[2].l = sums[2].m + len * (1 - west), sums[2].l + s[5] * (1 - west)
            end
            Logging.info("SDT PLAY: postříkáno %d pruhů: západ %.0f m / %.1f l, východ %.0f m / %.1f l (řez x %.0f)", #SprayDroneDebug.sprayLog,
                sums[1].m, sums[1].l, sums[2].m, sums[2].l, cut)
        end
        local poly = SprayDroneRoute.getPolygon(field)
        local state = FieldState.new()
        local stats = { { n = 0, weed = 0, total = 0, lime = 0, sprayed = 0 }, { n = 0, weed = 0, total = 0, lime = 0, sprayed = 0 } }
        local step = 4
        for x = minX + step * 0.5, maxX, step do
            for z = minZ + step * 0.5, maxZ, step do
                if SprayDroneRoute.isPointInPolygon(poly, x, z) then
                    local r = stats[x < cut and 1 or 2]
                    local weed, total = SprayDroneStation.getWeedPixels(x - 2, z - 2, x + 2, z - 2, x - 2, z + 2)
                    state:update(x, z)
                    r.n = r.n + 1
                    r.weed, r.total = r.weed + (weed or 0), r.total + (total or 0)
                    r.lime = r.lime + state.limeLevel
                    if state.sprayType ~= nil and state.sprayType > 0 then
                        r.sprayed = r.sprayed + 1
                    end
                end
            end
        end
        for i, r in ipairs(stats) do
            Logging.info("SDT PLAY: %s: %d bodů, plevel %.1f %% pixelů, vápno průměr %.2f, vrstva postřiku %.0f %% bodů", i == 1 and "západ (40 %)" or "východ",
                r.n, r.total > 0 and r.weed / r.total * 100 or 0, r.n > 0 and r.lime / r.n or 0, r.n > 0 and r.sprayed / r.n * 100 or 0)
        end
    end
end

-- Sken pole (DEBUG): scanMode / sprayMode = druh mise, scanCell0..2 = úroveň skenu, scanSetWeeds = plevel (stav 2, hráči neviditelný) jen
-- v západních 40 % obdélníku vybraného pole, jinde žádný, scanInfo = souhrn mapy a mapa plevele po buňkách do logu, scanBlock* = vynucená
-- překážka skenu (None = zrušit), scanConditions = naměřené podmínky, droneCam = hráč 25 m od dronu 1 a pohled na něj.
function SprayDroneDebug.scanCommand(max, command)
    local spec = max[SprayDroneStation.SPEC_NAME]
    local function setSetting(key, value)
        local settings = SprayDroneStation.getSettings(max)
        settings[key] = value
        max:setSprayDroneSettings(settings)
    end
    if command == "scanMode" or command == "sprayMode" then
        Logging.info("SDT PLAY: druh mise se nemění, určuje ho dron na plošině (pad1K skenovací, pad1S/M/L postřikový): teď %d", spec.missionMode)
    elseif command:find("^scanCell") then
        setSetting("scanCell", tonumber(command:sub(-1)))
        Logging.info("SDT PLAY: úroveň skenu %d, záběr %.0f m, výška %.0f m, rychlost %.1f m/s", spec.scanCell, spec.workWidth, spec.sprayHeight, spec.sprayingSpeed)
    elseif command:find("^scanBlock") then
        local kind = command:sub(10):lower()
        SprayDroneScanMap.debugBlocker = kind ~= "none" and kind or nil
        Logging.info("SDT PLAY: vynucená překážka skenu: %s", tostring(SprayDroneScanMap.debugBlocker))
    elseif command == "windOff" or command:find("^wind%d") then
        SprayDroneScanMap.debugWind = tonumber(command:sub(5))
        Logging.info("SDT PLAY: vynucený vítr %s m/s", tostring(SprayDroneScanMap.debugWind))
    elseif command == "weatherInfo" then
        local scanBlocker, info, scanMax = SprayDroneStation.getWeatherBlocker(max, true)
        local sprayBlocker, _, sprayMax = SprayDroneStation.getWeatherBlocker(max, false)
        Logging.info("SDT PLAY: počasí: %s | sken (vítr max %.1f): %s | postřik (vítr max %.1f, dron %s): %s | plánovač: %s", info, scanMax,
            tostring(scanBlocker), sprayMax, tostring(spec.droneName), tostring(sprayBlocker), (SprayDroneStation.getWeatherText(max)))
    elseif command == "scanTreatedInfo" then
        local map = SprayDroneScanMap.getMap(max:getOwnerFarmId(), spec.fieldId)
        if map == nil then
            Logging.info("SDT PLAY: pole %d nemá mapu skenu", spec.fieldId)
            return
        end
        local counts, unscanned = {}, 0
        for index in pairs(map.treated) do
            local kinds = map.treatedKinds[index] or 0
            counts[kinds] = (counts[kinds] or 0) + 1
            if map.values[index] == nil then
                unscanned = unscanned + 1
            end
        end
        local parts = {}
        for kinds, n in pairs(counts) do
            table.insert(parts, string.format("druhy %d: %d", kinds, n))
        end
        local sprayType = SprayDroneStation.getSprayType(max)
        local mask = SprayDroneStation.getSpotMask(max, sprayType)
        Logging.info("SDT PLAY: ošetřeno po skenu: %s (z toho nenaskenovaných %d) | %s | maska %s: vybráno %s buněk, revize %d",
            table.concat(parts, ", "), unscanned, SprayDroneScanMap.formatSummary(map), sprayType ~= nil and sprayType.name or "?",
            mask ~= nil and tostring(mask.selected) or "bez masky", map.revision)
    elseif command == "scanConditions" then
        local blocker, info = SprayDroneStation.getWeatherBlocker(max)
        local updater = g_currentMission.environment.weather.windUpdater
        local fields = {}
        if updater ~= nil then
            for k, v in pairs(updater) do
                if type(v) == "number" then
                    table.insert(fields, string.format("%s=%.2f", tostring(k), v))
                end
            end
        end
        Logging.info("SDT PLAY: podmínky skenu: překážka %s, %s | windUpdater: %s", tostring(blocker), info, table.concat(fields, " "))
    elseif command == "scanSetWeeds" then
        local field = SprayDroneRoute.getFieldById(spec.fieldId)
        local weedSystem = g_currentMission.weedSystem
        if field == nil or weedSystem == nil or not weedSystem:getMapHasWeed() then
            Logging.info("SDT PLAY: bez vybraného pole nebo mapy plevele")
            return
        end
        local minX, maxX, minZ, maxZ = math.huge, -math.huge, math.huge, -math.huge
        for _, p in ipairs(SprayDroneRoute.getPolygon(field)) do
            minX, maxX, minZ, maxZ = math.min(minX, p.x), math.max(maxX, p.x), math.min(minZ, p.z), math.max(maxZ, p.z)
        end
        local mapId, first, num = weedSystem:getDensityMapData()
        local modifier = DensityMapModifier.new(mapId, first, num, g_terrainNode)
        local cut = minX + (maxX - minX) * 0.4
        modifier:setParallelogramWorldCoords(cut, minZ, maxX, minZ, cut, maxZ, DensityCoordType.POINT_POINT_POINT)
        modifier:executeSet(0)
        modifier:setParallelogramWorldCoords(minX, minZ, cut, minZ, minX, maxZ, DensityCoordType.POINT_POINT_POINT)
        modifier:executeSet(2)
        Logging.info("SDT PLAY: plevel stav 2 na x %.0f..%.0f, z %.0f..%.0f, bez plevele x %.0f..%.0f", minX, cut, minZ, maxZ, cut, maxX)
    elseif command == "scanInfo" then
        local map = SprayDroneScanMap.getMap(max:getOwnerFarmId(), spec.fieldId)
        if map == nil then
            Logging.info("SDT PLAY: pole %d nemá mapu skenu", spec.fieldId)
            return
        end
        Logging.info("SDT PLAY: mapa %s", SprayDroneScanMap.formatSummary(map))
        -- řádky od severu (nejvyšší z dolů): # plevel, . naskenováno bez plevele, o v poli nenaskenováno, mezera mimo pole
        local step = math.max(math.ceil(map.nx / 80), 1)
        for iz = map.nz - 1, 0, -step do
            local row = {}
            for ix = 0, map.nx - 1, step do
                local index = iz * map.nx + ix + 1
                local value = map.values[index]
                local ch = map.inside[index] and "o" or " "
                if value ~= nil then
                    local c = SprayDroneScanMap.decode(value)
                    ch = (c.weedShare > 0 or c.weedState > 0) and "#" or "."
                end
                table.insert(row, ch)
            end
            Logging.info("SDT MAPA |%s|", table.concat(row))
        end
    elseif command == "scanInfoFert" then
        -- hnojení po buňkách: v mapě skenu | skutečně na poli (FieldState ve středu buňky), řádky od severu
        local map = SprayDroneScanMap.getMap(max:getOwnerFarmId(), spec.fieldId)
        if map == nil then
            return
        end
        local state = FieldState.new()
        for iz = map.nz - 1, 0, -1 do
            local inMap, real = {}, {}
            for ix = 0, map.nx - 1 do
                local index = iz * map.nx + ix + 1
                local a, b = map.inside[index] and "o" or " ", map.inside[index] and "o" or " "
                if map.values[index] ~= nil then
                    a = tostring(SprayDroneScanMap.decode(map.values[index]).sprayLevel)
                end
                if map.inside[index] then
                    local cx, cz = SprayDroneScanMap.getCellCenter(map, index)
                    state:update(cx, cz)
                    b = tostring(state.sprayLevel)
                end
                table.insert(inMap, a)
                table.insert(real, b)
            end
            Logging.info("SDT HNOJ |%s| |%s|", table.concat(inMap), table.concat(real))
        end
    elseif command == "pfSoil" or command == "pfSample" or command == "pfSend" then -- DEBUG: odběr vzorků PF z cizího kódu (AIRASI)
        local pf = SprayDroneStation.getPrecisionFarming()
        local function methods(t)
            local seen, list, depth = {}, {}, 0
            while type(t) == "table" and depth < 6 do
                for k, v in pairs(t) do
                    if type(v) == "function" and not seen[k] then
                        seen[k] = true
                        table.insert(list, tostring(k))
                    end
                end
                local mt = getmetatable(t)
                t = mt ~= nil and rawget(mt, "__index") or nil
                depth = depth + 1
            end
            table.sort(list)
            return table.concat(list, " ")
        end
        local function fields(t)
            local list = {}
            for k, v in pairs(t or {}) do
                if type(v) ~= "function" then
                    table.insert(list, tostring(k) .. "=" .. (type(v) == "table" and "{}" or tostring(v)))
                end
            end
            table.sort(list)
            return table.concat(list, " ")
        end
        local farmId = max:getOwnerFarmId()
        if pf == nil then
            Logging.info("SDT PFSOIL: PF není")
            return
        end
        local sm, cm = pf.soilMap, pf.coverMap
        if command == "pfSoil" then
            Logging.info("SDT PFSOIL coverMap metody: %s", methods(cm))
            Logging.info("SDT PFSOIL coverMap pole: %s", fields(cm):sub(1, 2500))
            for _, n in ipairs({ "CoverMap", "DensityMapCircle", "DensityMapParallelogram", "DensityMapPolygon" }) do
                local c = SprayDroneStation.getPFGlobal(n)
                Logging.info("SDT PFSOIL %s%s: %s", n, rawget(_G, n) ~= nil and " (global)" or "", c ~= nil and methods(c) or "NIL")
            end
            Logging.info("SDT PFSOIL cena vzorku %s, vzorků/ha %s", tostring(sm:getPricePerSoilSample()), tostring(sm.getNumSoilSamplesPerHa ~= nil and sm:getNumSoilSamplesPerHa() or nil))
        elseif command == "pfSample" then
            local field = SprayDroneRoute.getFieldById(spec.fieldId)
            if field == nil then
                Logging.info("SDT PFSOIL: pole nevybráno")
                return
            end
            local poly = SprayDroneRoute.getPolygon(field)
            local x, z = 0, 0
            for _, p in ipairs(poly) do
                x, z = x + p.x, z + p.z
            end
            x, z = x / #poly, z / #poly
            local Circle = SprayDroneStation.getPFGlobal("DensityMapCircle")
            local farmlandId = g_farmlandManager:getFarmlandIdAtWorldPosition(x, z)
            local ok, err = pcall(function()
                SprayDroneDebug.pfCircle = SprayDroneDebug.pfCircle or Circle.new()
                SprayDroneDebug.pfCircle:updateFromWorldPosition(x, z, 32.5, 20)
                cm:analyseArea(SprayDroneDebug.pfCircle, nil, farmId, farmlandId)
            end)
            SprayDroneDebug.pfSamples = (SprayDroneDebug.pfSamples or 0) + (ok and 1 or 0)
            Logging.info("SDT PFSOIL vzorek pole %d na (%.0f, %.0f), pozemek %s: %s %s, odebráno %d", spec.fieldId, x, z, tostring(farmlandId), tostring(ok),
                tostring(err), SprayDroneDebug.pfSamples)
        else
            local n = SprayDroneDebug.pfSamples or 0
            local ok, err = pcall(sm.analyseSoilSamples, sm, farmId, n)
            SprayDroneDebug.pfSamples = 0
            Logging.info("SDT PFSOIL odesláno %d vzorků: %s %s", n, tostring(ok), tostring(err))
        end
        for id, d in pairs(sm.pendingSoilSamplesPerFarm or {}) do
            Logging.info("SDT PFSOIL pending farma %s: %s", tostring(id), fields(d))
        end
    elseif command == "pfApi" then -- DEBUG
        local pf = SprayDroneStation.getPrecisionFarming()
        local function dump(label, t)
            local list = {}
            for k, v in pairs(t or {}) do
                if type(v) == "function" then
                    table.insert(list, tostring(k))
                end
            end
            table.sort(list)
            Logging.info("SDT PFAPI %s: %s", label, table.concat(list, " "))
        end
        for _, name in ipairs({ "NitrogenMap", "PHMap", "SoilMap", "PrecisionFarming", "SoilSampler", "SoilSamplerSendEvent",
            "SoilSamplerStartEvent", "SoilSampleEvent", "Laboratory", "FarmlandStatistics", "FarmlandStatistic", "ValueMap",
            "MapFrameExtensionLaboratory", "SoilSampleYesNoDialog" }) do
            dump(name, SprayDroneStation.getPFGlobal(name))
        end
        -- instance: vlastní klíče (hodnoty) a funkce po řetězu metatabulek
        local function dumpInstance(label, t)
            if type(t) ~= "table" then
                Logging.info("SDT PFAPI %s: %s", label, tostring(t))
                return
            end
            local fields = {}
            for k, v in pairs(t) do
                table.insert(fields, tostring(k) .. ":" .. type(v) .. (type(v) ~= "table" and type(v) ~= "function" and ("=" .. tostring(v)) or ""))
            end
            table.sort(fields)
            Logging.info("SDT PFAPI %s pole: %s", label, table.concat(fields, " "):sub(1, 3000))
            local mt, depth = getmetatable(t), 0
            while mt ~= nil and depth < 6 do
                local index = rawget(mt, "__index")
                if type(index) ~= "table" then
                    break
                end
                dump(label .. " meta" .. depth, index)
                mt, depth = getmetatable(index), depth + 1
            end
        end
        if pf ~= nil then
            dumpInstance("pf", pf)
            for _, key in ipairs({ "soilMap", "farmlandStatistics", "laboratory", "pHMap", "nitrogenMap" }) do
                dumpInstance("pf." .. key, pf[key])
            end
            for k, v in pairs(pf) do
                local name = tostring(k):lower()
                if type(v) == "table" and (name:find("sampl") or name:find("lab") or name:find("stat")) then
                    dumpInstance("pf." .. tostring(k), v)
                end
            end
        end
        local nm = pf ~= nil and pf.nitrogenMap or nil
        if nm ~= nil then
            for _, key in ipairs({ "fruitRequirements", "nitrogenValues", "initialValues", "fertilizerUsage" }) do
                local parts = {}
                for k, v in pairs(nm[key] or {}) do
                    table.insert(parts, tostring(k) .. "=" .. (type(v) == "table" and "{}" or tostring(v)))
                end
                table.sort(parts)
                Logging.info("SDT PFAPI nitrogenMap.%s: %s", key, table.concat(parts, " "):sub(1, 1400))
            end
            local req
            for _, r in pairs(nm.fruitRequirements or {}) do
                req = r
                break
            end
            if type(req) == "table" then
                local parts = {}
                for k, v in pairs(req) do
                    table.insert(parts, tostring(k) .. "=" .. (type(v) == "table" and "{}" or tostring(v)))
                end
                table.sort(parts)
                Logging.info("SDT PFAPI fruitRequirement příklad: %s", table.concat(parts, " "):sub(1, 1000))
            end
        end
        local ph = pf ~= nil and pf.pHMap or nil
        if ph ~= nil then
            local parts = {}
            for k, v in pairs(ph) do
                if type(v) ~= "function" then
                    table.insert(parts, tostring(k) .. "=" .. (type(v) == "table" and "{}" or tostring(v)))
                end
            end
            table.sort(parts)
            Logging.info("SDT PFAPI pHMap pole: %s", table.concat(parts, " "):sub(1, 1400))
        end
    elseif command == "pfTarget" then -- DEBUG
        local pf = SprayDroneStation.getPrecisionFarming()
        local map = SprayDroneScanMap.getMap(max:getOwnerFarmId(), spec.fieldId)
        if pf == nil or map == nil then
            Logging.info("SDT PFTARGET: bez PF nebo mapy (pole %s)", tostring(spec.fieldId))
            return
        end
        local shown = 0
        for index in pairs(map.values) do
            if shown < 3 then
                shown = shown + 1
                local x, z = SprayDroneScanMap.getCellCenter(map, index)
                local function try(label, fn)
                    local r = { pcall(fn) }
                    local ok = table.remove(r, 1)
                    for i = 1, #r do
                        r[i] = tostring(r[i])
                    end
                    return string.format("%s=%s%s", label, ok and "" or "CHYBA ", table.concat(r, ","))
                end
                local soil = pf.soilMap:getTypeIndexAtWorldPos(x, z)
                local fruit = FSDensityMapUtil.getFruitTypeIndexAtWorldPos(x, z)
                Logging.info("SDT PFTARGET buňka %d (%.0f, %.0f): půda %s, plodina %s | %s | %s | %s | %s | %s | %s", index, x, z, tostring(soil), tostring(fruit),
                    try("nM.getLevelAtWorldPos", function() return pf.nitrogenMap:getLevelAtWorldPos(x, z) end),
                    try("nM.getTargetLevelAtWorldPos", function() return pf.nitrogenMap:getTargetLevelAtWorldPos(x, z) end),
                    try("nM.getNitrogenTargetLevel(fruit,soil)", function() return pf.nitrogenMap:getNitrogenTargetLevel(fruit, soil) end),
                    try("pH.getLevelAtWorldPos", function() return pf.pHMap:getLevelAtWorldPos(x, z) end),
                    try("pH.optimal(soil)", function() return pf.pHMap:getOptimalPHValueForSoilTypeIndex(soil) end),
                    try("pH.nearest(15)", function() return pf.pHMap:getNearestPhValueFromValue(15) end))
            end
        end
    elseif command == "scanFly" then -- DEBUG
        Logging.info("SDT PLAY: start letu: %s", tostring(SprayDroneStation.startFlight(max)))
    elseif command == "takeoffPlaces" then -- DEBUG: kontrola vzletu uprostřed budov farmy (má najít střechu)
        local n = 0
        for _, p in ipairs(g_currentMission.placeableSystem.placeables) do
            if n < 15 and p.rootNode ~= nil and p:getOwnerFarmId() == max:getOwnerFarmId() then
                local x, _, z = getWorldTranslation(p.rootNode)
                local y = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.5
                local hits = {}
                local ok, reason = SprayDroneLaunch.getClearance(x, y, z, 1.9, 12, nil, hits)
                n = n + 1
                Logging.info("SDT TAKEOFF místo %s (%.0f, %.0f): volno=%s důvod=%s, zásahů %d%s", tostring(p.configFileName):match("([^/]+)%.xml$") or "?",
                    x, z, tostring(ok), tostring(reason), #hits, hits[1] ~= nil and (" první " .. tostring(hits[1].name) .. " " .. tostring(hits[1].reason)) or "")
            end
        end
    elseif command == "takeoffCheck" then -- DEBUG
        for k = 1, SprayDroneDrones.getCount(max) do
            local hits = {}
            local ok, reason = SprayDroneDrones.runAs(max, k, SprayDroneStation.getTakeoffClearance, hits)
            local x, z, rest = SprayDroneDrones.runAs(max, k, SprayDroneStation.getHomePosition)
            Logging.info("SDT TAKEOFF dron %d na (%.1f, %.1f) %.1f m nad terénem: volno=%s důvod=%s, zásahů %d", k, x, z, rest, tostring(ok),
                tostring(reason), #hits)
            for _, hit in ipairs(hits) do
                Logging.info("SDT TAKEOFF   %s %s (%s) %s %s", hit.ray == 0 and "box" or ("paprsek " .. hit.ray), tostring(hit.name),
                    hit.reason, string.format("group=0x%x", getCollisionFilterGroup(hit.node)),
                    hit.distance ~= nil and string.format("%.1f m nad startem, y=%.1f", hit.distance, hit.y) or "")
            end
        end
    elseif command == "scanPfInfo" then -- DEBUG
        local map = SprayDroneScanMap.getMap(max:getOwnerFarmId(), spec.fieldId)
        local pf = SprayDroneStation.getPrecisionFarming()
        if map == nil or pf == nil then
            Logging.info("SDT PLAY: scanPfInfo: mapa %s, PF %s", tostring(map ~= nil), tostring(pf ~= nil))
            local function keys(t)
                local list = {}
                for k, v in pairs(t) do
                    if type(k) == "string" and (k:lower():find("precision") or k:lower():find("farming") or k:lower():find("nitrogen") or k:lower():find("soil")) then
                        table.insert(list, k .. ":" .. type(v))
                    end
                end
                table.sort(list)
                return table.concat(list, " ")
            end
            local env = SprayDroneStation.getModEnv(SprayDroneStation.PF_MOD_NAME)
            local mod = g_modManager ~= nil and g_modManager:getModByName(SprayDroneStation.PF_MOD_NAME) or nil
            local modKeys = {}
            for k, v in pairs(mod or {}) do
                table.insert(modKeys, tostring(k) .. ":" .. type(v))
            end
            table.sort(modKeys)
            local fsGlobals = {}
            for k in pairs(_G) do
                if type(k) == "string" and k:find("^FS25_") then
                    table.insert(fsGlobals, k)
                end
            end
            table.sort(fsGlobals)
            Logging.info("SDT PLAY: PF env %s, modManager %s (%s), FS25_ globály %d: %s", type(env), type(mod), table.concat(modKeys, " "), #fsGlobals,
                table.concat(fsGlobals, " "):sub(1, 600))
            if type(env) == "table" then
                Logging.info("SDT PLAY: PF env klíče: %s", keys(env))
                local pfi = env.g_precisionFarming
                if type(pfi) == "table" then
                    local list = {}
                    for k, v in pairs(pfi) do
                        table.insert(list, tostring(k) .. ":" .. type(v))
                    end
                    table.sort(list)
                    Logging.info("SDT PLAY: g_precisionFarming v env: %s", table.concat(list, " "))
                end
            end
            return
        end
        Logging.info("SDT PLAY: mapa %s", SprayDroneScanMap.formatSummary(map))
        for _, kind in ipairs({ { "vápno", { isLime = true } }, { "hnojivo", { isFertilizer = true } }, { "herbicid", { isHerbicide = true } } }) do
            local select = SprayDroneStation.getSpotSelector(kind[2], map.farmId)
            local n = 0
            for index in pairs(map.inside) do
                if select(SprayDroneScanMap.unpack(map, index), 0, map, index) then
                    n = n + 1
                end
            end
            Logging.info("SDT PLAY: výběr podle skenu (%s): %d z %d buněk", kind[1], n, map.numInside)
        end
        local shown = 0
        for index in pairs(map.pf) do
            if shown < 6 then
                shown = shown + 1
                local x, z = SprayDroneScanMap.getCellCenter(map, index)
                local c = SprayDroneScanMap.unpack(map, index)
                local line = {}
                for _, item in ipairs({ { pf.nitrogenMap, "NitrogenMap" }, { pf.pHMap, "PHMap" } }) do
                    local mapId, first, num = SprayDroneStation.getPFMapLayer(item[1], item[2])
                    local hist = mapId ~= nil and SprayDroneDebug.histogram(mapId, first, num, x, z, map.cellSize) or nil
                    table.insert(line, string.format("%s histogram průměr %s (%s)", item[2], hist ~= nil and string.format("%.2f", hist.avg) or "-",
                        hist ~= nil and SprayDroneDebug.formatHistogram(hist) or "-"))
                end
                Logging.info("SDT PLAY: buňka %d (%.0f, %.0f): sken dusík %s (cíl %s) | %s", index, x, z, tostring(c.nitrogen), tostring(c.targetNitrogen), table.concat(line, " | "))
            end
        end
    elseif command == "scanPlanner" then
        SprayDronePlannerScreen.show(max, SprayDronePlannerScreen.MODE_TABLET)
        Logging.info("SDT PLAY: plánovač otevřen: %s", tostring(g_gui:getIsGuiVisible()))
    elseif command == "scanPlannerClose" then
        g_gui:showGui("")
    elseif command == "scanPlannerMiddle" then
        for _, vehicle in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if vehicle.configFileName ~= nil and vehicle.configFileName:find("sprayDroneTrailerMiddle") then
                SprayDronePlannerScreen.show(vehicle, SprayDronePlannerScreen.MODE_TABLET)
                Logging.info("SDT PLAY: plánovač Middle otevřen: %s", tostring(g_gui:getIsGuiVisible()))
                return
            end
        end
        Logging.info("SDT PLAY: Middle nenalezen")
    elseif command:find("^scanLayer") or command:find("^scanOverview") then
        -- vrstva mapy a přehled polí v otevřeném plánovači (scanLayerWeed..Cover/Off, scanOverview, scanOverviewOff,
        -- scanOverviewPick = klik na první řádek přehledu)
        local screen = SprayDronePlannerScreen.INSTANCE
        if screen == nil or not screen:getIsOpen() then
            Logging.info("SDT PLAY: plánovač není otevřený")
            return
        end
        if command:find("^scanLayer") then
            local index = SprayDroneScanOverlay.getLayerIndex(command:sub(10):lower())
            if index ~= nil then
                screen:setScanLayer(index)
            end
            Logging.info("SDT PLAY: vrstva mapy skenu %s", screen:getScanLayer().id)
        elseif command == "scanOverviewPick" then
            local row = screen:getScanOverviewRows()[1]
            if row ~= nil then
                screen:selectScanOverviewRow(row)
            end
        else
            screen:setScanOverview(command == "scanOverview")
            for i, row in ipairs(screen:getScanOverviewRows()) do
                local s = row.shares
                Logging.info("SDT PLAY: přehled %d: pole %d, %s", i, row.id, s == nil and "nenaskenováno" or string.format(
                    "pokrytí %.0f %%, stáří %.1f h, plevel %.0f %% (nevid. %.0f %%), slabý porost %.0f %%, zralé %.0f %%, naléhavost %.2f",
                    s.coverage * 100, row.age, s.weed * 100, s.invisible * 100, s.unfertilized * 100, s.ripe * 100, s.urgency))
            end
        end
    elseif command == "scanAge" then
        -- mapa vybraného pole o 72 herních hodin starší (vybledlé buňky v plánovači)
        local map = SprayDroneScanMap.getMap(max:getOwnerFarmId(), spec.fieldId)
        if map ~= nil then
            for index, time in pairs(map.times) do
                map.times[index] = time - 72 * 60
            end
            map.updated = map.updated - 72 * 60
            Logging.info("SDT PLAY: mapa pole %d je teď stará %.1f h", spec.fieldId, SprayDroneScanMap.getAgeHours(map))
        end
    elseif command == "droneCam" then
        local d = spec.drones[1]
        local node = d.node
        if node == nil then
            return
        end
        local x, y, z = getWorldTranslation(node)
        local hx, _, hz = getWorldTranslation(max.rootNode)
        local dx, dz = hx - x, hz - z
        local len = math.max(MathUtil.vector2Length(dx, dz), 0.1)
        local fx, fz = x + dx / len * 25, z + dz / len * 25
        local fy = math.max(getTerrainHeightAtWorldPos(g_terrainNode, fx, 0, fz) + 2, y - 6)
        g_localPlayer.mover:setFlightActive(true, true)
        g_localPlayer.mover:teleportTo(fx, fy, fz, true)
        local ex, ey, ez = x - fx, y - (fy + SprayDroneDebug.EYE_HEIGHT), z - fz
        local el = MathUtil.vector3Length(ex, ey, ez)
        local pitch, yaw = MathUtil.directionToPitchYaw(ex / el, ey / el, ez / el)
        g_localPlayer.camera:setRotation(pitch, yaw, 0)
        Logging.info("SDT PLAY: kamera u dronu (%.0f %.0f %.0f)", x, y, z)
    end
end

local function findVehicleByFile(pattern)
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v.configFileName ~= nil and v.configFileName:find(pattern) then
            return v
        end
    end
end

local function getFieldDistances(x, z)
    local list = {}
    for _, field in ipairs(g_fieldManager:getFields()) do
        local fx, fz = field:getCenterOfFieldWorldPosition()
        table.insert(list, { field = field, distance = MathUtil.vector2Length(fx - x, fz - z) })
    end
    table.sort(list, function(a, b)
        return a.distance < b.distance
    end)
    return list
end

-- Držák pumpy na vleku (DEBUG): pumpStore = hráč u pumpy a uložení nejbližšího vleku s držákem, pumpTake = hráč u vleku s uloženou pumpou a vyndání, pumpFuel = v pumpě
-- 9 l nafty, pumpSlotInfo = stav držáků a pumpy do logu.
function SprayDroneDebug.pumpSlotCommand(command)
    local pump
    local trailers = {}
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v[SprayDronePump.SPEC_NAME] ~= nil and not v.isDeleted then
            pump = v
        end
        local station = v[SprayDroneStation.SPEC_NAME]
        if station ~= nil and station.pumpSlot ~= nil then
            table.insert(trailers, v)
        end
    end
    local function describe()
        for _, t in ipairs(trailers) do
            local ps = t[SprayDroneStation.SPEC_NAME].pumpSlot
            local x, y, z = getWorldTranslation(ps.node)
            Logging.info("SDT PLAY: držák pumpy na %s (id %s): obsazen=%s nafta %.1f l, uzel %.1f %.1f %.1f", t.configFileNameClean or "?", tostring(t.id), tostring(ps.occupied), ps.diesel, x, y, z)
        end
        if pump ~= nil then
            local spec = pump[SprayDronePump.SPEC_NAME]
            Logging.info("SDT PLAY: pumpa id %s, nafta %.1f l, motor %s", tostring(pump.id), pump:getFillUnitFillLevel(spec.dieselUnit), tostring(spec.engineOn))
        else
            Logging.info("SDT PLAY: pumpa ve světě není")
        end
    end
    local player = g_localPlayer
    local function standNear(x, y, z)
        player.mover:setFlightActive(true, true)
        player.mover:teleportTo(x, y, z, true)
    end
    if command == "pumpSlotInfo" then
        describe()
    elseif command == "pumpFuel" and pump ~= nil then
        local spec = pump[SprayDronePump.SPEC_NAME]
        local delta = 9 - pump:getFillUnitFillLevel(spec.dieselUnit)
        pump:addFillUnitFillLevel(1, spec.dieselUnit, delta, FillType.DIESEL, ToolType.UNDEFINED, nil)
        describe()
    elseif command == "pumpStore" and pump ~= nil then
        local px, py, pz = getWorldTranslation(pump.rootNode)
        local best, bestDistance
        for _, t in ipairs(trailers) do
            local x, _, z = getWorldTranslation(t.rootNode)
            local d = MathUtil.vector2Length(x - px, z - pz)
            if t.configFileName:find("Middle", 1, true) then
                d = d - 1e6
            end
            if bestDistance == nil or d < bestDistance then
                best, bestDistance = t, d
            end
        end
        if best ~= nil then
            standNear(px + 1.2, py, pz)
            SprayDronePumpSlots.command(best, SprayDronePumpSlotEvent.STORE, pump, player)
        end
        describe()
    elseif command == "pumpTake" then
        for _, t in ipairs(trailers) do
            local ps = t[SprayDroneStation.SPEC_NAME].pumpSlot
            if ps.occupied then
                local sx, sy, sz = getWorldTranslation(ps.node)
                local tx, _, tz = getWorldTranslation(t.rootNode)
                local dx, dz = sx - tx, sz - tz
                local length = math.max(math.sqrt(dx * dx + dz * dz), 0.01)
                local x, z = sx + (dx / length) * 0.5 + 1.5, sz + (dz / length) * 0.5
                standNear(x, getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z), z)
                SprayDronePumpSlots.command(t, SprayDronePumpSlotEvent.TAKE, nil, player)
                break
            end
        end
    end
end

-- Držení objektu na místě po zadanou dobu (kanystr / pytel / big bag nad násypkou bez hráče): place(vehicle) ho každý snímek postaví na místo. -- DEBUG
function SprayDroneDebug.hold(vehicle, seconds, place)
    SprayDroneDebug.holds = SprayDroneDebug.holds or {}
    setRigidBodyType(vehicle.rootNode, RigidBodyType.KINEMATIC)
    table.insert(SprayDroneDebug.holds, { vehicle = vehicle, untilTime = g_time + seconds * 1000, place = place })
end

-- Měření skládání (příkazy foldClockFold / foldClockUnfold): do logu čas skládání po krocích 0,05 a celková doba. -- DEBUG
SprayDroneDebug.foldClocks = {}

function SprayDroneDebug.startFoldClock(vehicle, direction, leaveAfter) -- DEBUG
    local clock = { dir = direction, real = 0, last = vehicle:getFoldAnimTime(), t0 = g_time, leaveAt = leaveAfter ~= nil and g_time + leaveAfter or nil }
    SprayDroneDebug.foldClocks[vehicle] = clock
    vehicle:setFoldState(direction, false)
    Logging.info("SDT FOLDCLOCK %s start dir=%d t=%.3f", vehicle.configFileNameClean or tostring(vehicle.id), direction, clock.last)
end

function SprayDroneDebug.updateFoldClocks(dt) -- DEBUG
    for vehicle, clock in pairs(SprayDroneDebug.foldClocks) do
        if vehicle.isDeleted then
            SprayDroneDebug.foldClocks[vehicle] = nil
        else
            clock.real = clock.real + dt
            if clock.leaveAt ~= nil and g_time >= clock.leaveAt then
                clock.leaveAt = nil
                vehicle:deactivate() -- jako Enterable:leaveVehicle
                Logging.info("SDT FOLDCLOCK %s deactivate (vystoupení) při t=%.3f", vehicle.configFileNameClean or tostring(vehicle.id), vehicle:getFoldAnimTime())
            end
            local t = vehicle:getFoldAnimTime()
            local target = clock.dir > 0 and 1 or 0
            local fs = vehicle.spec_foldable
            local done = t == target or (fs.foldMoveDirection == 0 and g_time - clock.t0 > 1000)
            if done then
                Logging.info("SDT FOLDCLOCK %s konec t=%.6f moveDir=%s turnOnDir=%s unfolded=%s keepFolding=%s", vehicle.configFileNameClean or tostring(vehicle.id), t,
                    tostring(fs.foldMoveDirection), tostring(fs.turnOnFoldDirection), tostring(vehicle:getIsUnfolded()), tostring(fs.keepFoldingWhileDetached))
            end
            if done or math.abs(t - clock.last) >= 0.05 then
                clock.last = t
                local spec = vehicle[SprayDroneStation.SPEC_NAME]
                local drone = 0
                if spec ~= nil then
                    drone = vehicle:getSprayDroneIsParked() and 1 or 0
                end
                Logging.info("SDT FOLDCLOCK %s t=%.3f cas=%.2f s (g_time %.2f s) parked=%s secured=%s", vehicle.configFileNameClean or tostring(vehicle.id), t,
                    clock.real / 1000, (g_time - clock.t0) / 1000, tostring(drone == 1), tostring(spec ~= nil and SprayDroneStation.getIsDroneSecured(vehicle)))
            end
            if done then
                SprayDroneDebug.foldClocks[vehicle] = nil
            end
        end
    end
end

function SprayDroneDebug.updateHolds() -- DEBUG
    local holds = SprayDroneDebug.holds
    if holds == nil then
        return
    end
    for i = #holds, 1, -1 do
        local h = holds[i]
        if g_time > h.untilTime or h.vehicle.isDeleted then
            if not h.vehicle.isDeleted then
                setRigidBodyType(h.vehicle.rootNode, RigidBodyType.DYNAMIC)
            end
            table.remove(holds, i)
        else
            h.vehicle.sdtEjectTime = g_time
            h.place(h.vehicle)
        end
    end
end

-- Vlek se bez pohybu uspí a SprayDroneDebug.update se přestane volat, držení proto jede z vlastního posluchače.
SprayDroneDebugHolds = {}

function SprayDroneDebugHolds:update(dt) -- DEBUG
    if SprayDroneDebug.ENABLED then
        SprayDroneDebug.updateHolds()
        SprayDroneDebug.updateFoldClocks(dt)
    end
end

addModEventListener(SprayDroneDebugHolds)

-- Nejbližší násypka k hráči (pěšky jeho poloha, jinak aktivní kamera); ve světě jich může být víc (ze savu i nově postavená).
local function findHopper()
    local px, py, pz
    if g_localPlayer ~= nil and g_localPlayer.getPosition ~= nil then
        px, py, pz = g_localPlayer:getPosition()
    end
    if px == nil and g_cameraManager ~= nil and g_cameraManager:getActiveCamera() ~= nil then
        px, py, pz = getWorldTranslation(g_cameraManager:getActiveCamera())
    end
    local best, bestDistance
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v[SprayDroneHopper.SPEC_NAME] ~= nil and not v.isDeleted then
            local x, y, z = getWorldTranslation(v.rootNode)
            local d = px ~= nil and MathUtil.vector3Length(x - px, y - py, z - pz) or 0
            if best == nil or d < bestDistance then
                best, bestDistance = v, d
            end
        end
    end
    return best
end

-- Násypka: spawnHopper (3,5 m od vápnové spojky velkého vleku, výstupem k vleku, 10 l nafty), hopperOn / hopperOff (motor), hopperFill (200 l vápna),
-- hopperBag (pytel 50 l víčkem dolů nad ústím 14 s), hopperBigBag (big bag s 300 l položený na výsypnou stolici), hopperDrop (smazat pytle a big bagy),
-- hopperCam (pohled, atribut view v souřadnicích násypky), hopperStatus (stav do logu), hopperLegs (vysunout / zasunout opěry), hopperInfo (zásoba,
-- hladina, opěry, vak na stolici). -- DEBUG
SprayDroneDebug.PLAY.hopperFeet = true

-- hopperFeet: výšky nad terénem (m) spodku rámu v rozích, vizuálních patek a spodku kolizí patek, filtr kolizí patek a typ těla nejbližší násypky.
-- Patky nesou, když jsou opěry venku, filtr je 0x10000 / 0xfffdfbff a spodky kolizí patek ~0,00 a rám ~+0,01; zasunuté: filtr 0 / 0, rám ~0,00. -- DEBUG
function SprayDroneDebug.hopperFeet(hopper)
    local hs = hopper[SprayDroneHopper.SPEC_NAME]
    local function above(x, y, z)
        return y - getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
    end
    local frame = {}
    local cols = getChild(hopper.components[1].node, "collisions")
    local floor = cols ~= 0 and getChild(cols, "floorCollision01") or 0
    if floor ~= 0 then
        for _, c in ipairs({ { 0.54, 0.53 }, { -0.54, 0.53 }, { 0.54, -0.53 }, { -0.54, -0.53 } }) do
            table.insert(frame, string.format("%+.3f", above(localToWorld(floor, c[1], 0, c[2]))))
        end
    end
    local feet = {}
    for i, leg in ipairs(hs.legs) do
        local foot = leg.foot ~= nil and string.format("%+.3f", above(getWorldTranslation(leg.foot))) or "-"
        local col, filter = "-", "-"
        if leg.col ~= nil and entityExists(leg.col) then
            col = string.format("%+.3f", above(getWorldTranslation(leg.col)))
            filter = string.format("0x%x/0x%x", getCollisionFilterGroup(leg.col), getCollisionFilterMask(leg.col))
        end
        table.insert(feet, string.format("%d: patka %s kolize %s filtr %s", i, foot, col, filter))
    end
    local _, ry = getWorldRotation(hopper.rootNode)
    Logging.info("SDT PLAY: násypka id %s opěry %s (poloha %.2f, nesou %s), tělo %s, upnutá %s | rám nad terénem (rohy) %s | %s | natočení %.0f°",
        tostring(hopper.id), hs.legsOut and "venku" or "zasunuté", hs.legsPos, tostring(hs.feetCarry), tostring(getRigidBodyType(hopper.components[1].node)),
        tostring(hopper.dynamicMountObject ~= nil or hopper.tensionMountObject ~= nil), table.concat(frame, " "), table.concat(feet, " | "), math.deg(ry))
end
-- Kufr skenovacího dronu (SprayDroneCase), cílí na nejbližší kufr k hráči: caseInfo = stav (víko, baterie, zdroj nabíjení, nejbližší budova
-- a centrála), caseOpen / caseClose = víko jako R pěšky (s kontrolou getIsFoldAllowed), caseCharge = baterie kufru na 100 %, caseEmpty = na 30 %.
for _, name in ipairs({ "caseInfo", "caseOpen", "caseClose", "caseCharge", "caseEmpty", "caseSpawn", "caseFly", "caseScanInfo", "caseTakeoff", "casePlanner", "casePlannerClose", "caseMapReset" }) do
    SprayDroneDebug.PLAY[name] = true
end

function SprayDroneDebug.caseCommand(command)
    local px, _, pz = 0, 0, 0
    if g_localPlayer ~= nil and g_localPlayer.getPosition ~= nil then
        px, _, pz = g_localPlayer:getPosition()
    end
    if command == "caseSpawn" then -- kufr 4 m od hráče, vlastní farma hráče
        local x, z = px + 15, pz
        local data = VehicleLoadingData.new()
        data:setFilename(SprayDroneHopper.MOD_DIR .. "objects/droneCase/scanCase.xml")
        data:setPosition(x, getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.3, z)
        data:setRotation(0, 0, 0)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(g_currentMission:getFarmId())
        data:load(function(_, vehicles, state)
            local v = vehicles ~= nil and vehicles[1] or nil
            Logging.info("SDT CASE: spawn %s id %s na %.1f %.1f", tostring(state), v ~= nil and tostring(v.id) or "-", x, z)
        end)
        return
    end
    local case, best = nil, math.huge
    for _, vehicle in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if SprayDroneCase.getIsPortable(vehicle) and not vehicle.isDeleted then
            local x, _, z = getWorldTranslation(vehicle.rootNode)
            local d = MathUtil.vector2Length(x - px, z - pz)
            if d < best then
                case, best = vehicle, d
            end
        end
    end
    if case == nil then
        Logging.info("SDT CASE: žádný kufr")
        return
    end
    local spec = case[SprayDroneStation.SPEC_NAME]
    if command == "caseFly" then -- vybere pole 23 (nebo nejbližší) a po spočtení trasy spustí let
        if spec.fieldId == 0 then
            SprayDroneStation.selectField(case, SprayDroneRoute.getFieldById(23))
            Logging.info("SDT CASE: vybráno pole %d", spec.fieldId)
        else
            Logging.info("SDT CASE: start letu pole %d: %s", spec.fieldId, tostring(SprayDroneStation.startFlight(case)))
        end
    elseif command == "caseTakeoff" then
        local hits = {}
        local ok, reason = SprayDroneStation.getTakeoffClearance(case, hits)
        Logging.info("SDT CASE: vzlet volno=%s důvod=%s, zásahů %d", tostring(ok), tostring(reason), #hits)
        for _, hit in ipairs(hits) do
            local object = g_currentMission:getNodeObject(hit.node)
            Logging.info("SDT CASE:   %s %s (%s) objekt %s%s", hit.ray == 0 and "box" or ("paprsek " .. hit.ray), tostring(hit.name), hit.reason,
                object ~= nil and tostring(object.configFileName or object.id) or "-", hit.distance ~= nil and string.format(" %.1f m", hit.distance) or "")
        end
    elseif command == "casePlanner" then
        SprayDronePlannerScreen.show(case, SprayDronePlannerScreen.MODE_TABLET)
        Logging.info("SDT CASE: plánovač otevřen, naplánováno %s", tostring(SprayDroneStation.getAnyPlanned(case)))
    elseif command == "casePlannerClose" then
        g_gui:showGui("")
    elseif command == "caseMapReset" then
        local maps = SprayDroneScanMap.maps[case:getOwnerFarmId()]
        if maps ~= nil then
            maps[spec.fieldId] = nil
        end
        SprayDroneStation.markRouteDirty(case)
        Logging.info("SDT CASE: mapa pole %d smazána", spec.fieldId)
    elseif command == "caseScanInfo" then
        local map = SprayDroneScanMap.getMap(case:getOwnerFarmId(), spec.fieldId)
        Logging.info("SDT CASE: mapa %s", map ~= nil and SprayDroneScanMap.formatSummary(map) or "-")
    end
    if command == "caseOpen" or command == "caseClose" then
        local warning = SprayDroneCase.setLidOpen(case, command == "caseOpen")
        Logging.info("SDT CASE: %s víka: %s", command == "caseOpen" and "otevření" or "zavření", tostring(warning or "ok"))
    elseif command == "caseCharge" or command == "caseEmpty" then
        local level = command == "caseCharge" and 1 or 0.3
        for _, battery in ipairs(spec.batteries) do
            battery.charge = level * spec.batteryCapacity
        end
        if spec.droneBattery ~= nil then
            spec.battery = spec.batteries[spec.droneBattery].charge
        end
        SprayDroneStation.markRouteDirty(case)
        case:raiseDirtyFlags(spec.dirtyFlag)
        case:raiseActive()
        Logging.info("SDT CASE: baterie kufru na %.0f %%", level * 100)
    end
    local x, _, z = getWorldTranslation(case.rootNode)
    local batteries = {}
    for k, battery in ipairs(spec.batteries) do
        batteries[k] = string.format("%d:%.0f%%@%d", k, battery.charge / spec.batteryCapacity * 100, battery.slot)
    end
    local building, buildingDistance = nil, math.huge
    for _, placeable in ipairs(g_currentMission.placeableSystem.placeables) do
        if placeable:getOwnerFarmId() == case:getOwnerFarmId() and SprayDroneCase.getIsBuilding(placeable) then
            local d = SprayDroneCase.getPlaceableDistance(placeable, x, z)
            if d < buildingDistance then
                building, buildingDistance = placeable, d
            end
        end
    end
    local generator = SprayDroneCase.findGenerator(case, x, z, 1000)
    local gx, _, gz = 0, 0, 0
    if generator ~= nil then
        gx, _, gz = getWorldTranslation(generator.rootNode)
    end
    Logging.info("SDT CASE: kufr id %s %.1f m od hráče, víko čas %.2f (rozloženo %s), dron %s stav %d unfold %.2f, baterie %s, zdroj %s (nabíjí %s), "
        .. "nejbližší budova %s %.1f m, centrála s proudem %s %.1f m, rychlost %.1f km/h, stav %s", tostring(case.id), best, case:getFoldAnimTime(),
        tostring(case:getIsUnfolded()), tostring(spec.droneName), spec.state, spec.unfold, table.concat(batteries, " "),
        g_i18n:getText(SprayDroneCase.SOURCE_TEXTS[spec.chargeSource or 0]), tostring(spec.generatorRunning),
        building ~= nil and (tostring(building.configFileName):match("([^/]+)%.xml$") or "?") or "-", buildingDistance,
        generator ~= nil and tostring(generator.id) or "-", generator ~= nil and MathUtil.vector2Length(gx - x, gz - z) or -1, case:getLastSpeed(),
        SprayDroneStation.getDroneStateName(case))
end

-- Relé tyče (SprayDroneLink.getRelayEntry): relayInfo = nejbližší stanice (kufr i vlek), tyče do 2 km (druh, síla, azimut čela,
-- oblast, aktivní, v rádiu stanice, pojistka složení) a signál v bodech vybraného pole; relayRotate <stupně> = nejbližší tyč
-- pootočí (kladně po směru hodin při pohledu shora; rozloženou nejdřív složit, je kinematická). Spawn: relaySpawn [dir]. -- DEBUG
SprayDroneDebug.PLAY.relayInfo = true
for deg = -180, 360, 5 do
    SprayDroneDebug.PLAY["relayRotate " .. deg] = true
end

function SprayDroneDebug.relayCommand(command)
    if g_localPlayer == nil or g_localPlayer.getPosition == nil then
        return
    end
    local px, _, pz = g_localPlayer:getPosition()
    local nearest, nearestDistance = nil, math.huge
    local poles = {}
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if SprayDroneLink.isRelayPole(v) and not v.isDeleted and v.rootNode ~= nil and entityExists(v.rootNode) then
            local x, _, z = getWorldTranslation(v.rootNode)
            local d = MathUtil.vector2Length(x - px, z - pz)
            table.insert(poles, { vehicle = v, distance = d })
            if d < nearestDistance then
                nearest, nearestDistance = v, d
            end
        end
    end
    local deg = tonumber(command:match("^relayRotate (%-?%d+)$") or "")
    if deg ~= nil then
        if nearest == nil then
            Logging.info("SDT RELAY: žádná tyč")
            return
        end
        local x, y, z = getWorldTranslation(nearest.rootNode)
        local dir = SprayDroneLink.getRelayDirection(nearest) + math.rad(deg)
        nearest:setAbsolutePosition(x, y + 0.05, z, 0, math.atan2(math.cos(dir), math.sin(dir)), 0)
        Logging.info("SDT RELAY: tyč id %s pootočena o %d°, azimut čela %.0f°", tostring(nearest.id), deg, SprayDroneLink.getAzimuth(dir))
        return
    end
    -- relayInfo
    local station, best = nil, math.huge
    for _, vehicle in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if vehicle[SprayDroneStation.SPEC_NAME] ~= nil and not vehicle.isDeleted then
            local x, _, z = getWorldTranslation(vehicle.rootNode)
            local d = MathUtil.vector2Length(x - px, z - pz)
            if d < best then
                station, best = vehicle, d
            end
        end
    end
    local radio = station ~= nil and SprayDroneLink.getRadio(station) or nil
    for _, p in ipairs(poles) do
        if p.distance <= 2000 then
            local v = p.vehicle
            local e = SprayDroneLink.getRelayEntry(v)
            local rs = v[SprayDroneRelay.SPEC_NAME]
            local shape = e.r > 0 and string.format("kruh %.0f m", e.r) or "bez kruhu"
            for _, s in ipairs(e.sectors) do
                shape = shape .. string.format(", výseč azimut %.0f° ±%.1f° do %.0f m", SprayDroneLink.getAzimuth(s.dir), math.deg(s.half), s.r)
            end
            Logging.info("SDT RELAY: tyč id %s %s síla %.0f m, %.1f m od hráče, azimut čela %.0f°, %s | rozloženo %s, zapnuto %s, baterie %.0f %%, "
                .. "aktivní %s, v rádiu stanice %s, pojistka složení: %s%s",
                tostring(v.id), e.sectors[1] ~= nil and "směrová" or "všesměrová", e.radius, p.distance,
                SprayDroneLink.getAzimuth(SprayDroneLink.getRelayDirection(v)), shape, tostring(rs ~= nil and rs.unfolded), tostring(rs ~= nil and rs.powered),
                SprayDroneRelay.getBatteryFraction(v) * 100, tostring(SprayDroneLink.isRelayActive(v)),
                radio ~= nil and tostring(SprayDroneLink.isInShape(radio, e.x, e.z)) or "-", tostring(SprayDroneRelay.blockReason(v, "fold")),
                v == nearest and " (nejbližší)" or "")
        end
    end
    if station == nil then
        Logging.info("SDT RELAY: žádná stanice (kufr ani vlek)")
        return
    end
    local spec = station[SprayDroneStation.SPEC_NAME]
    local circles = SprayDroneLink.getSignalCircles(station)
    Logging.info("SDT RELAY: stanice id %s (%s, dron %s) %.1f m od hráče, rádio %.0f m, spojených tyčí %d, bonus dosahu %.0f m, dosah z baterie %.0f m",
        tostring(station.id), tostring(station.configFileName):match("([^/]+)%.xml$") or "?", tostring(spec.droneName), best, radio.r, #circles - 1,
        SprayDroneLink.getRangeBonus(station, radio), spec.range or -1)
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field == nil then
        Logging.info("SDT RELAY: stanice nemá vybrané pole")
        return
    end
    local inside, total, parts = 0, 0, {}
    for i, p in ipairs(SprayDroneRoute.getPolygon(field)) do
        local d = MathUtil.vector2Length(p.x - radio.x, p.z - radio.z)
        local ok = d <= (spec.range or 0) and SprayDroneLink.isInCircles(circles, p.x, p.z)
        total = total + 1
        inside = inside + (ok and 1 or 0)
        if i <= 12 then
            table.insert(parts, string.format("%.0f%s", d, ok and "" or "!"))
        end
    end
    Logging.info("SDT RELAY: pole %d: body obrysu v signálu %d / %d (vzdálenost od stanice, ! = mimo): %s | dávek %d, mimo dosah %d úseků",
        spec.fieldId, inside, total, table.concat(parts, " "), spec.numBatches or 0, #(spec.outOfReachLegs or {}))
end

-- Baterie jako předměty (SprayDroneBatterySlots), cílí na nejbližší vlek nebo kufr k hráči: batteryInfo = šachty, baterie v dronech a bateriové předměty
-- do 10 m; batteryTake [n | d1 | d2] = jako R bez ničeho v ruce (šachta n, baterie z dronu, bez čísla první obsazená šachta, jinak baterie v dronu);
-- batteryPut = jako R s baterií v ruce (nebo nejbližší ležící baterie do 10 m); batterySpawn S|M|L|C|P = plná baterie 1,5 m od hráče.
-- Slovo „case“ za příkazem cílí na nejbližší kufr i u vleku: batteryInfo case, batteryTake case [n | d1], batteryPut case. -- DEBUG
for _, prefix in ipairs({ "", " case" }) do
    for _, name in ipairs({ "batteryInfo", "batteryTake", "batteryTake d1", "batteryTake d2", "batteryPut" }) do
        SprayDroneDebug.PLAY[name:gsub("^(%S+)", "%1" .. prefix)] = true
    end
    for i = 1, 10 do
        SprayDroneDebug.PLAY["batteryTake" .. prefix .. " " .. i] = true
    end
end
for _, size in ipairs({ "S", "M", "L", "C", "P" }) do
    SprayDroneDebug.PLAY["batterySpawn " .. size] = true
end

function SprayDroneDebug.batteryCommand(command)
    local words = {}
    for word in command:gmatch("%S+") do
        table.insert(words, word)
    end
    local name, onlyCase = words[1], words[2] == "case"
    local arg = words[onlyCase and 3 or 2] or ""
    local player = g_localPlayer
    local px, py, pz = 0, 0, 0
    if player ~= nil and player.getPosition ~= nil then
        px, py, pz = player:getPosition()
    end
    if name == "batterySpawn" then
        local size = arg ~= "" and arg or "M"
        local filename = SprayDroneBatterySlots.getItemFilename(size)
        if filename == nil then
            Logging.info("SDT BATTERY: baterie %s není v obchodě", size)
            return
        end
        local x, z = px + 1.5, pz
        local data = VehicleLoadingData.new()
        data:setFilename(filename)
        data:setPosition(x, math.max(getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z), py) + 0.4, z)
        data:setRotation(0, 0, 0)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(g_currentMission:getFarmId())
        data:load(function(_, vehicles, state)
            local v = vehicles ~= nil and vehicles[1] or nil
            Logging.info("SDT BATTERY: spawn %s %s id %s, nabití %.0f %%", size, tostring(state), v ~= nil and tostring(v.id) or "-",
                v ~= nil and SprayDroneItem.getBatteryLevel(v) * 100 or -1)
        end)
        return
    end
    local vehicle, best = nil, math.huge
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if v[SprayDroneStation.SPEC_NAME] ~= nil and not v.isDeleted and SprayDroneDrones.getRoot(v).batterySlots ~= nil
            and (not onlyCase or SprayDroneCase.getIsPortable(v)) then
            local x, _, z = getWorldTranslation(v.rootNode)
            local d = MathUtil.vector2Length(x - px, z - pz)
            if d < best then
                vehicle, best = v, d
            end
        end
    end
    if vehicle == nil then
        Logging.info("SDT BATTERY: %s", onlyCase and "žádný kufr" or "žádný vlek ani kufr")
        return
    end
    local spec = SprayDroneDrones.getRoot(vehicle)
    local items = {}
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if SprayDroneItem.getBatterySize(v) ~= nil and not v.isDeleted then
            local x, y, z = getWorldTranslation(v.rootNode)
            local d = MathUtil.vector3Length(x - px, y - py, z - pz)
            if d <= 10 then
                table.insert(items, { item = v, distance = d })
            end
        end
    end
    table.sort(items, function(a, b)
        return a.distance < b.distance
    end)
    if name == "batteryTake" then
        local target, problem = SprayDroneBatterySlots.getDebugTake(vehicle, arg)
        Logging.info("SDT BATTERY: vyndat cíl %s: %s", tostring(target), problem ~= nil and (problem .. " (" .. g_i18n:getText(problem) .. ")") or "ok")
        if problem == nil then
            SprayDroneBatterySlots.command(vehicle, SprayDroneBatterySlotEvent.TAKE, target, nil, player)
        end
    elseif name == "batteryPut" then
        local held = player ~= nil and SprayDroneBatterySlots.getHeldBattery(player) or nil
        local item = held or (items[1] ~= nil and items[1].item or nil)
        if item == nil then
            Logging.info("SDT BATTERY: žádná baterie v ruce ani do 10 m")
        else
            local problem = SprayDroneBatterySlots.getPutProblem(vehicle, SprayDroneItem.getBatterySize(item), nil)
            Logging.info("SDT BATTERY: vložit baterii %s id %s (%s): %s", tostring(SprayDroneItem.getBatterySize(item)), tostring(item.id), held ~= nil and "v ruce" or "ležící",
                problem ~= nil and (problem .. " (" .. g_i18n:getText(problem) .. ")") or "ok")
            if problem == nil then
                if held ~= nil then
                    SprayDroneBatterySlots.command(vehicle, SprayDroneBatterySlotEvent.PUT, 0, item, player)
                else
                    SprayDroneBatterySlots.doPut(vehicle, nil, item, nil, true)
                end
            end
        end
    end
    local shafts = {}
    for slot = 1, spec.numBatterySlots do
        local k = SprayDroneBatterySlots.getTargetBattery(vehicle, slot)
        shafts[slot] = k ~= nil and string.format("%d:%.0f%%(#%d)", slot, spec.batteries[k].charge / spec.batteryCapacity * 100, k) or string.format("%d:-", slot)
    end
    local drones = {}
    for d = 1, spec.numDrones or 1 do
        local droneSpec = SprayDroneDrones.getSpec(vehicle, d)
        if droneSpec ~= nil and droneSpec.hasDrone then
            local k = droneSpec.droneBattery
            drones[d] = string.format("dron %d stav %d: %s", d, droneSpec.state, k ~= nil and string.format("#%d dron %.1f%% / pool %.1f%%", k,
                droneSpec.battery / spec.batteryCapacity * 100, spec.batteries[k].charge / spec.batteryCapacity * 100) or "bez baterie")
        end
    end
    local itemTexts = {}
    for _, entry in ipairs(items) do
        table.insert(itemTexts, string.format("%s id %s %.0f%% %.1f m", SprayDroneItem.getBatterySize(entry.item), tostring(entry.item.id),
            SprayDroneItem.getBatteryLevel(entry.item) * 100, entry.distance))
    end
    Logging.info("SDT BATTERY: %s id %s %.1f m od hráče, rozloženo %s, typ %s, baterií %d / %d (konfigurace %d) | šachty %s | %s | předměty %s",
        spec.portable and "kufr" or "vlek", tostring(vehicle.id), best, tostring(vehicle.getIsUnfolded == nil or vehicle:getIsUnfolded()), tostring(spec.batteryVariant),
        #spec.batteries, spec.numBatterySlots, spec.batteryConfigCount or -1, table.concat(shafts, " "), table.concat(drones, " | "),
        #itemTexts > 0 and table.concat(itemTexts, ", ") or "-")
end

-- Kufr AIRASI (SprayDroneSamples), cílí na nejbližší vzorkovací kufr k hráči: samplerSpawn = kufr 15 m od hráče, samplerFly = vybere pole 23
-- (nebo nejbližší vlastní), otevře víko, spočte náhled a spustí misi (víko a výběr pole při prvním volání, start při dalším), samplerInfo = body,
-- odebráno, bednička, PF laboratoř do logu, samplerSend = odeslat bedničku do laboratoře, samplerBoxFull = bednička plná (zkouška odmítnutí).
-- Body odběru (cestou plánovače, SprayDroneSamples.requestPick): samplerPickHere / samplerUnpickHere = přidá / odebere bod u hráče (odebrání
-- hledá do 15 m), samplerPickCenter = bod ve středu vybraného pole, samplerPickClear = smaže naklikané body pole, samplerAutoOn / Off =
-- automatické body; samplerSlots = přihrádky bedničky a krabičky dronu (stav, uzly modelu) a body pole s porostem do logu.
for _, name in ipairs({ "samplerSpawn", "samplerFly", "samplerInfo", "samplerSend", "samplerBoxFull", "samplerPlanner", "samplerPickHere",
    "samplerUnpickHere", "samplerPickCenter", "samplerPickClear", "samplerAutoOn", "samplerAutoOff", "samplerSlots" }) do
    SprayDroneDebug.PLAY[name] = true
end

-- Tablet (SprayDroneLink): tabletInfo = cíle (všechny vleky a kufry farmy, kdo je ve spojení), vybraný cíl, registrace levého tlačítka a proč
-- by se plánovač neotevřel; tabletOpen = otevře plánovač jako tablet pro výchozí cíl (i bez tabletu v ruce); tabletNext = další cíl
-- (v otevřeném plánovači ho přepne, jinak jen posune zapamatovaný cíl).
for _, name in ipairs({ "tabletInfo", "tabletOpen", "tabletNext" }) do
    SprayDroneDebug.PLAY[name] = true
end

-- Ovládání (DEBUG): inputInfo vypíše akce, které teď v kontextu hráče (nebo vozidla) leží na klávesách modu a vanilla akcích, které mod
-- používá: akce, klávesa, text, čí je (objekt), aktivní ano/ne, viditelná ano/ne; k tomu vybranou aktivaci a cíle tabletu, displeje a centrály.
SprayDroneDebug.PLAY.inputInfo = true
SprayDroneDebug.INPUT_ACTIONS = { "ACTIVATE_OBJECT", "ACTIVATE_HANDTOOL", "INTERACT", "SDT_TOGGLE_FOOT", "IMPLEMENT_EXTRA", "IMPLEMENT_EXTRA2",
    "IMPLEMENT_EXTRA3", "HANDTOOL_TAKE", "SDT_OPEN_PLANNER", "SDT_START_FLIGHT", "SDT_RETURN_HOME", "SDT_TOGGLE_LINES", "SDT_DRONE_VIEW",
    "SDT_DRAIN_DRONE", "SDT_PUMP_TO_PALLET", "TOGGLE_TIPSTATE_GROUND" }

local function describeTarget(target)
    if target == nil then
        return "-"
    end
    local L = SprayDroneLink
    if target == L then
        return "SprayDroneLink (tablet / displej: " .. tostring(L.openKind) .. ")"
    elseif target == L.toggleTarget then
        return "SprayDroneLink (centrála vleku " .. tostring(L.toggleVehicle ~= nil and L.toggleVehicle.id or "-") .. ")"
    end
    local classes = { { "bedna", SprayDroneToolboxActivatable }, { "nalévání", SprayDroneHandPourActivatable },
        { "mlýnek rozvaděč", SprayDroneMillEngineActivatable }, { "mlýnek výstup", SprayDroneMillModeActivatable },
        { "hadice", SprayDroneWaterHoseActivatable }, { "motor pumpy/násypky", SprayDronePumpEngineActivatable }, { "tyč", SprayDroneRelayActivatable },
        { "kufr", SprayDroneCaseActivatable }, { "šachty baterií", SprayDroneBatterySlotsActivatable }, { "plošina", SprayDronePadSlotsActivatable },
        { "držák pumpy", SprayDronePumpSlotsActivatable }, { "držák tyče", SprayDroneRelaySlotsActivatable } }
    local mt = type(target) == "table" and getmetatable(target) or nil
    for _, entry in ipairs(classes) do
        local name, class = entry[1], entry[2]
        if class ~= nil and mt ~= nil and (mt == class or mt.__index == class) then
            local vehicle = target.vehicle
            return string.format("%s (vozidlo %s %s)", name, vehicle ~= nil and tostring(vehicle.id) or "-", vehicle ~= nil and tostring(vehicle.configFileNameClean or "") or "")
        end
    end
    if type(target) == "table" and target.configFileNameClean ~= nil then
        return string.format("vozidlo %s %s", tostring(target.id), tostring(target.configFileNameClean))
    end
    return tostring(target)
end

local function describeBindings(actionName)
    local action = g_inputBinding.nameActions ~= nil and g_inputBinding.nameActions[actionName] or nil
    if action == nil then
        return "?"
    end
    local keys = {}
    for _, binding in ipairs(action.activeBindings or action.bindings or {}) do
        local text = binding.inputString or (binding.axisNames ~= nil and table.concat(binding.axisNames, " ")) or nil
        if text ~= nil then
            table.insert(keys, text)
        end
    end
    return #keys > 0 and table.concat(keys, " | ") or "žádná"
end

function SprayDroneDebug.inputInfo()
    local L = SprayDroneLink
    local player = g_localPlayer
    local vehicle = player ~= nil and player.getCurrentVehicle ~= nil and player:getCurrentVehicle() or nil
    local selected = L.selected
    Logging.info("SDT INPUT: %s | vybraná aktivace %s | levé tl.: %s | B u centrály: %s | tablet v ruce %s | mayClick %s",
        vehicle ~= nil and ("ve vozidle " .. tostring(vehicle.configFileNameClean or vehicle.id)) or "pěšky",
        describeTarget(selected), tostring(L.openKind), L.toggleVehicle ~= nil and tostring(L.toggleVehicle.id) or "-",
        tostring(L.getHeldTablet() ~= nil), tostring(L.mayClick(nil)))
    local wanted = {}
    for _, name in ipairs(SprayDroneDebug.INPUT_ACTIONS) do
        wanted[name] = true
    end
    local events = g_inputBinding.events
    if type(events) ~= "table" then
        Logging.info("SDT INPUT: g_inputBinding.events není k dispozici, vypisuji jen akce modu")
        events = {}
        for _, id in ipairs({ L.openEventId, L.toggleTarget.eventId, selected ~= nil and selected.clickEventId or nil,
            selected ~= nil and selected.toggleEventId or nil, selected ~= nil and selected.eventId or nil }) do
            Logging.info("  událost %s", tostring(id))
        end
    end
    local count = 0
    for id, event in pairs(events) do
        local actionName = type(event) == "table" and event.actionName or nil
        if actionName ~= nil and wanted[actionName] then
            count = count + 1
            Logging.info("  %-22s %-24s text \"%s\" | %s | aktivní %s, viditelná %s | id %s", actionName, describeBindings(actionName),
                tostring(event.contextDisplayText or ""), describeTarget(event.targetObject), tostring(event.isActive),
                tostring(event.displayIsVisible), tostring(id))
        end
    end
    Logging.info("SDT INPUT: %d akcí", count)
end

function SprayDroneDebug.tabletCommand(command)
    local L = SprayDroneLink
    if command == "tabletOpen" then
        Logging.info("SDT TABLET: otevřeno %s", tostring(L.openTablet() ~= nil))
    elseif command == "tabletNext" then
        local screen = SprayDronePlannerScreen.INSTANCE
        if screen ~= nil and screen:getIsOpen() then
            screen:requestTarget(1)
        else
            local found = L.getTabletTargets()
            local index = L.cycleTarget(found, L.tabletTarget, 1)
            L.tabletTarget = index ~= nil and found[index].vehicle or nil
        end
    end
    local px, _, pz = 0, 0, 0
    if g_localPlayer ~= nil and g_localPlayer.getPosition ~= nil then
        px, _, pz = g_localPlayer:getPosition()
    end
    local lines = {}
    for i, e in ipairs(L.collectTrailers(px, pz, g_currentMission:getFarmId())) do
        local spec = e.vehicle[SprayDroneStation.SPEC_NAME]
        table.insert(lines, string.format("%d) %s id %s %.0f m, dron %s, spojení %s (dosah %.0f m), %s%s%s", i, tostring(e.vehicle.configFileName):match("([^/]+)%.xml$") or "?",
            tostring(e.vehicle.id), e.distance, tostring(spec.hasDrone), tostring(e.inRange), spec.maxRange or -1, spec.portable and "kufr, " or "",
            e.unfolded and "rozloženo" or "složeno", e.missionActive and ", mise" or ""))
    end
    local found = L.getTabletTargets()
    local index = L.pickTarget(found, L.tabletTarget)
    local tool = L.getHeldTablet()
    Logging.info("SDT TABLET: v ruce %s | ovládání %s, akce %s, událost %s | ve spojení %d, výchozí %s, zapamatovaný %s | neotevře: %s\n  %s",
        tool ~= nil and "tablet" or "nic", tostring(L.openKind), tostring(L.openAction), tostring(L.openEventId), #found,
        index ~= nil and L.getTargetLabel(found[index]) or "-", L.tabletTarget ~= nil and tostring(L.tabletTarget.id) or "-",
        tostring(L.getTabletBlocker() or "nic, otevře"), #lines > 0 and table.concat(lines, "\n  ") or "žádný vlek ani kufr farmy")
end

function SprayDroneDebug.samplerCommand(command)
    local px, _, pz = 0, 0, 0
    if g_localPlayer ~= nil and g_localPlayer.getPosition ~= nil then
        px, _, pz = g_localPlayer:getPosition()
    end
    if command == "samplerSpawn" then
        local x, z = px + 15, pz
        local data = VehicleLoadingData.new()
        data:setFilename(SprayDroneHopper.MOD_DIR .. "objects/droneCase/samplerCase.xml")
        data:setPosition(x, getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.3, z)
        data:setRotation(0, 0, 0)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(g_currentMission:getFarmId())
        data:load(function(_, vehicles, state)
            local v = vehicles ~= nil and vehicles[1] or nil
            Logging.info("SDT SAMPLER: spawn %s id %s na %.1f %.1f", tostring(state), v ~= nil and tostring(v.id) or "-", x, z)
        end)
        return
    end
    local case, best = nil, math.huge
    for _, vehicle in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if SprayDroneSamples.getIsSampler(vehicle) and not vehicle.isDeleted then
            local x, _, z = getWorldTranslation(vehicle.rootNode)
            local d = MathUtil.vector2Length(x - px, z - pz)
            if d < best then
                case, best = vehicle, d
            end
        end
    end
    if case == nil then
        Logging.info("SDT SAMPLER: žádný vzorkovací kufr")
        return
    end
    local spec = case[SprayDroneStation.SPEC_NAME]
    if command == "samplerFly" then
        if not case:getIsUnfolded() then
            Logging.info("SDT SAMPLER: otevírám víko: %s", tostring(SprayDroneCase.setLidOpen(case, true) or "ok"))
        end
        if spec.fieldId == 0 then
            local field = SprayDroneRoute.getFieldById(23)
            if field == nil or not SprayDroneStation.getFieldAllowed(case, field) then
                local hx, hz = SprayDroneStation.getHomePosition(case)
                local nearest = math.huge
                for _, f in ipairs(g_fieldManager:getFields()) do
                    local poly = SprayDroneRoute.getPolygon(f)
                    local d = #poly >= 3 and SprayDroneRoute.distanceToPolygon(poly, hx, hz) or math.huge
                    if d < nearest and SprayDroneStation.getFieldAllowed(case, f) then
                        field, nearest = f, d
                    end
                end
            end
            Logging.info("SDT SAMPLER: výběr pole %s: %s", field ~= nil and tostring(field:getId()) or "-",
                field ~= nil and tostring(SprayDroneStation.selectField(case, field) or "ok") or "žádné povolené pole")
            return
        end
        -- náhled se jinak počítá jen v otevřeném plánovači (refreshRoutePreview)
        SprayDroneStation.updateRoutePreview(case)
        Logging.info("SDT SAMPLER: start pole %d (%d dávek): %s", spec.fieldId, spec.numBatches, tostring(SprayDroneStation.startFlight(case) or "ok"))
    elseif command == "samplerPlanner" then
        SprayDronePlannerScreen.show(case, SprayDronePlannerScreen.MODE_TABLET)
    elseif command == "samplerSend" then
        Logging.info("SDT SAMPLER: odeslání: %s", tostring(SprayDroneSamples.requestSend(case) or "ok"))
    elseif command == "samplerBoxFull" then
        spec.sampleBox = spec.sampler.boxCapacity
        SprayDroneStation.markRouteDirty(case)
        case:raiseDirtyFlags(spec.dirtyFlag)
    elseif command == "samplerPickHere" or command == "samplerUnpickHere" or command == "samplerPickCenter" then
        local x, z = px, pz
        local field = SprayDroneRoute.getFieldById(spec.fieldId)
        if command == "samplerPickCenter" and field ~= nil then
            x, z = field:getCenterOfFieldWorldPosition()
        end
        local add = command ~= "samplerUnpickHere"
        local warning, note = SprayDroneSamples.requestPick(case, x, z, add, add and SprayDroneSamples.PICK_MIN_GAP or 15)
        local fruitType, growthState = SprayDroneSamples.getCropAt(x, z)
        Logging.info("SDT SAMPLER: %s bod (%.1f, %.1f) pole %d: %s | plodina %s stav %s %s, nízký porost %s", add and "přidat" or "odebrat", x, z,
            spec.fieldId, tostring(warning or note or "ok"), fruitType ~= nil and tostring(fruitType.name) or "-", tostring(growthState),
            fruitType ~= nil and fruitType.growthStateToName ~= nil and tostring(fruitType.growthStateToName[growthState]) or "",
            tostring(SprayDroneSamples.isLowCrop(fruitType, growthState)))
    elseif command == "samplerPickClear" then
        SprayDroneSamples.setPicks(case, spec.fieldId, nil)
    elseif command == "samplerAutoOn" or command == "samplerAutoOff" then
        local settings = SprayDroneStation.getSettings(case)
        settings.samplerAuto = command == "samplerAutoOn" and 1 or 0
        case:setSprayDroneSettings(settings)
    elseif command == "samplerSlots" then
        local v = spec.samplerVisuals
        local names = { [0] = "-", "prázdná", "plná" }
        local slots = SprayDroneSamples.getSlotStates(spec.sampler.boxCapacity, spec.sampleBox, math.max(spec.samplerBoxes, spec.samplesCarried))
        local boxes = SprayDroneSamples.getDroneBoxStates(spec.sampler.capacity, spec.samplerBoxes, spec.samplesCarried)
        local slotTexts, boxTexts = {}, {}
        for i, state in ipairs(slots) do
            table.insert(slotTexts, string.format("%d:%s", i, names[state]))
        end
        for i, state in ipairs(boxes) do
            table.insert(boxTexts, string.format("%d:%s", i, names[state]))
        end
        Logging.info("SDT SAMPLER: přihrádky %s | dron %s | uzly modelu: přihrádek %d, krabiček dronu %d, sonda %d stupňů (droneProbe %.2f m)",
            table.concat(slotTexts, " "), table.concat(boxTexts, " "), v ~= nil and #v.slots or -1, v ~= nil and #v.droneBoxes or -1,
            v ~= nil and #v.probeStages or -1, spec.sampler.caseProbeTravel or -1)
        SprayDroneStation.updateRoutePreview(case)
        local points = spec.routeInfo ~= nil and spec.routeInfo.samplePoints or nil
        for i, p in ipairs(points ~= nil and points.points or {}) do
            local fruitType, growthState = SprayDroneSamples.getCropAt(p.x, p.z)
            Logging.info("  bod %d (%.0f, %.0f)%s: %s, plodina %s stav %s", i, p.x, p.z, p.custom and " naklikaný" or "",
                p.sampled and "odebráno" or (p.tall and "vysoký porost" or (p.far and "mimo dosah" or "k odběru")),
                fruitType ~= nil and tostring(fruitType.name) or "-", tostring(growthState))
        end
    end
    if spec.fieldId ~= 0 then
        SprayDroneStation.updateRoutePreview(case)
    end
    local info = SprayDroneSamples.getInfo(case)
    local pf = SprayDroneStation.getPrecisionFarming()
    local perHa = SprayDroneSamples.getPerHa(pf)
    Logging.info("SDT SAMPLER: kufr id %s %.1f m od hráče, víko %.2f, stav %s, pole %d | PF %s, %.2f vzorků/ha (rozestup %.1f m), cena %s | body %d, odebráno %d, "
        .. "zbývá %d, mimo dosah %d, vysoký porost %d | auto body %d | dron %d plné z %d krabiček, bednička %d / %d | laboratoř %s | dávek %d, "
        .. "odhad %.1f min, baterie %.0f %%, sonda %s, status %d",
        tostring(case.id), best, case:getFoldAnimTime(), SprayDroneStation.getDroneStateName(case), spec.fieldId, tostring(info.hasPF), perHa,
        SprayDroneSamples.getSpacing(perHa), tostring(info.price), info.total, info.sampled, info.remaining - info.far - info.tall, info.far, info.tall,
        spec.samplerAuto, info.carried, info.boxes, info.box,
        info.boxCapacity, tostring(info.lab), spec.numBatches, (spec.routeInfo.time or 0) / 60, spec.battery / spec.batteryCapacity * 100,
        tostring(spec.probeOut), spec.status)
end

function SprayDroneDebug.hopperCommand(max, command)
    local hopper = findHopper()
    local farmId = max:getOwnerFarmId()
    if command == "spawnHopper" then
        local inlet = SprayDroneStation.getLimeInlet(max)
        if inlet == nil then
            Logging.info("SDT PLAY: vlek nemá vápnovou spojku")
            return
        end
        local ix, _, iz = getWorldTranslation(inlet.node)
        local ox, _, oz = localDirectionToWorld(inlet.node, -1, 0, 0)
        local l = math.max(math.sqrt(ox * ox + oz * oz), 0.01)
        ox, oz = ox / l, oz / l
        local x, z = ix + ox * 3.5, iz + oz * 3.5
        local data = VehicleLoadingData.new()
        data:setFilename(SprayDroneHopper.MOD_DIR .. "objects/hopper/limeHopper.xml")
        data:setPosition(x, getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.2, z)
        data:setRotation(0, math.atan2(-oz, ox), 0)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(farmId)
        data:load(function(_, vehicles, state)
            local v = vehicles ~= nil and vehicles[1] or nil
            if state ~= VehicleLoadingState.OK or v == nil then
                Logging.info("SDT PLAY: násypku se nepodařilo načíst (%s)", tostring(state))
                return
            end
            local ps = v[SprayDronePump.SPEC_NAME]
            v:addFillUnitFillLevel(farmId, ps.dieselUnit, 10, FillType.DIESEL, ToolType.UNDEFINED, nil)
            Logging.info("SDT PLAY: násypka id %s na %.1f %.1f, nafta %.1f l", tostring(v.id), x, z, v:getFillUnitFillLevel(ps.dieselUnit))
        end)
        return
    end
    if hopper == nil then
        Logging.info("SDT PLAY: násypka ve světě není")
        return
    end
    local hs = hopper[SprayDroneHopper.SPEC_NAME]
    local ps = hopper[SprayDronePump.SPEC_NAME]
    if command == "hopperOn" then
        hopper:sprayDronePumpCommand(SprayDronePump.CMD_ENGINE_ON)
    elseif command == "hopperOff" then
        hopper:sprayDronePumpCommand(SprayDronePump.CMD_ENGINE_OFF)
    elseif command == "hopperFill" then
        hopper:addFillUnitFillLevel(farmId, hs.limeUnit, 200, hs.fineType, ToolType.UNDEFINED, nil)
    elseif command == "hopperDrain" then
        local unit = SprayDroneToolbox.getConcentrateUnit(max)
        if unit ~= nil then
            max:addFillUnitFillLevel(farmId, unit, -max:getFillUnitFillLevel(unit) + 100, max:getFillUnitFillType(unit), ToolType.UNDEFINED, nil)
        end
    elseif command == "hopperDrop" then
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if v.configFileName ~= nil and (v.configFileName:find("limeBigBag", 1, true) or SprayDroneToolbox.getCanisterKind(v) == FillType.SDT_FINE_LIME) then
                v:delete()
            end
        end
    elseif command == "hopperBag" then
        local nx, ny, nz = getWorldTranslation(hs.pour.pourNeck)
        SprayDroneToolbox.spawnCanister(max, FillType.SDT_FINE_LIME, 50, function(ok, bag)
            if not ok then
                Logging.info("SDT PLAY: pytel se nepodařilo vyrobit")
                return
            end
            local cap = SprayDroneStation.getMappedNode(bag, "canisterCap")
            local cx, cy, cz = localToLocal(cap, bag.rootNode, 0, 0, 0)
            Logging.info("SDT PLAY: pytel id %s, %.0f l, víčko v pytli %.2f %.2f %.2f", tostring(bag.id), bag:getFillUnitFillLevel(SprayDroneToolbox.CANISTER_UNIT), cx, cy, cz)
            SprayDroneDebug.hold(bag, 14, function(v)
                local hx, hy, hz = getWorldTranslation(hs.pour.pourNeck)
                v:setAbsolutePosition(hx - cy, hy + 0.03 + cx, hz - cz, 0, 0, -math.pi / 2)
            end)
        end, { nx, ny + 1, nz, 0 })
    elseif command == "hopperBigBag" then
        local nx, ny, nz = getWorldTranslation(hs.pour.pourNeck)
        local data = VehicleLoadingData.new()
        data:setFilename(SprayDroneHopper.MOD_DIR .. "objects/limeBigBag/limeBigBag.xml")
        -- uzel funnel je 2 cm nad dosedacím rámem stolice: vak se položí 1 cm nad rám, natočený jako násypka (a sype, jen když jsou vysunuté opěry)
        local dx, _, dz = localDirectionToWorld(hopper.rootNode, 0, 0, 1)
        data:setPosition(nx, ny - 0.01, nz)
        data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz), 0)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(farmId)
        data:load(function(_, vehicles, state)
            local bag = vehicles ~= nil and vehicles[1] or nil
            if state ~= VehicleLoadingState.OK or bag == nil then
                Logging.info("SDT PLAY: big bag se nepodařilo načíst (%s)", tostring(state))
                return
            end
            bag:addFillUnitFillLevel(farmId, 1, 300, FillType.SDT_FINE_LIME, ToolType.UNDEFINED, nil)
            Logging.info("SDT PLAY: big bag id %s s %.0f l položen na stolici násypky (opěry %s)", tostring(bag.id), bag:getFillUnitFillLevel(1),
                hs.legsOut and "vysunuté" or "zasunuté: vak nesype")
        end)
    elseif command == "hopperLegs" then
        hopper:sprayDroneHopperCommand(hs.legsOut and SprayDroneHopper.CMD_LEGS_IN or SprayDroneHopper.CMD_LEGS_OUT)
        Logging.info("SDT PLAY: opěry násypky -> %s", hs.legsOut and "vysunout" or "zasunout")
    elseif command == "hopperFeet" then
        SprayDroneDebug.hopperFeet(hopper)
    elseif command == "hopperInfo" then
        local fu = hopper.spec_fillUnit.fillUnits[hs.limeUnit]
        local planeY, planeScale = -1, -1
        local plane = fu.fillPlane ~= nil and fu.fillPlane.nodes[1] or nil
        if plane ~= nil then
            _, planeY = getTranslation(plane.node)
            planeScale = getScale(plane.node)
        end
        -- vaky do 3 m od stolice: poloha vůči rámu (getStoolPlacement) a stav výpusti (aktivační trigger, cíl paprsku, důvod odmítnutí)
        local fx, fy, fz = getWorldTranslation(hs.pour.pourNeck)
        local bags = {}
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if v.configFileName ~= nil and v.configFileName:find("limeBigBag", 1, true) and not v.isDeleted then
                local bx, by, bz = getWorldTranslation(v.rootNode)
                if MathUtil.vector3Length(bx - fx, by - fy, bz - fz) < 3 then
                    local where, horizontal, dy = SprayDroneHopper.getStoolPlacement(fx, fy, fz, bx, by, bz)
                    local ds = v.spec_dischargeable
                    local dn = ds ~= nil and ds.currentDischargeNode or nil
                    local discharge = dn == nil and "bez výpusti" or string.format("stav %s, v triggeru %d, cíl %s, paprsek trefil %s, důvod %s",
                        tostring(ds.currentDischargeState), dn.activationTrigger.numObjects, dn.dischargeObject == hopper and "tahle násypka"
                        or tostring(dn.dischargeObject ~= nil and dn.dischargeObject.id), tostring(dn.raycastDischargeHitObject ~= nil
                        and dn.raycastDischargeHitObject.id), tostring(dn.raycastDischargeFailedReason))
                    table.insert(bags, string.format("id %s %.0f l: %s (vodorovně %.2f m, dno %+.2f m od rámu) | výpusť: %s", tostring(v.id),
                        v:getFillUnitFillLevel(1), where, horizontal, dy, discharge))
                end
            end
        end
        local onStool = #bags > 0 and table.concat(bags, " || ") or "žádný do 3 m"
        Logging.info("SDT PLAY: násypka id %s: zásoba %.1f / %.0f l, hladina y %.3f (měřítko %.2f, vidět %s) | opěry %s (poloha %.2f), vak smí sypat %s | "
            .. "vak na stolici: %s", tostring(hopper.id), hopper:getFillUnitFillLevel(hs.limeUnit), hopper:getFillUnitCapacity(hs.limeUnit), planeY,
            planeScale, plane ~= nil and tostring(getVisibility(plane.node)) or "-", hs.legsOut and "venku" or "zasunuté", hs.legsPos,
            tostring(hopper:getFillUnitSupportsToolType(hs.limeUnit, ToolType.DISCHARGEABLE)), onStool)
    elseif command == "hopperCam" then
        local v = SprayDroneDebug.view
        if v ~= nil then
            local fx, fy, fz = localToWorld(hopper.rootNode, v[1], v[2], v[3])
            local tx, ty, tz = localToWorld(hopper.rootNode, v[4], v[5], v[6])
            g_localPlayer.mover:setFlightActive(true, true)
            g_localPlayer.mover:teleportTo(fx, fy, fz, true)
            local dx, dy, dz = tx - fx, ty - (fy + SprayDroneDebug.EYE_HEIGHT), tz - fz
            local len = MathUtil.vector3Length(dx, dy, dz)
            local pitch, yaw = MathUtil.directionToPitchYaw(dx / len, dy / len, dz / len)
            g_localPlayer.camera:setRotation(pitch, yaw, 0)
        end
    end
    local nx, ny, nz = getWorldTranslation(hs.pour.pourNeck)
    for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
        if SprayDroneToolbox.getCanisterKind(v) == FillType.SDT_FINE_LIME and not v.isDeleted then
            local cap = SprayDroneStation.getMappedNode(v, "canisterCap")
            local cx, cy, cz = getWorldTranslation(cap)
            local _, upY = localDirectionToWorld(v.rootNode, 0, 1, 0)
            Logging.info("SDT PLAY: pytel id %s: %.1f l, víčko od hrdla %.2f m (výška %+.2f), upY %.2f", tostring(v.id), v:getFillUnitFillLevel(SprayDroneToolbox.CANISTER_UNIT),
                MathUtil.vector3Length(cx - nx, cy - ny, cz - nz), cy - ny, upY)
        end
    end
    local conc = SprayDroneToolbox.getConcentrateUnit(max)
    Logging.info("SDT PLAY: násypka id %s: motor=%s nafta %.1f l, vápno %.1f l, tok=%s | koncentrát vleku %.1f l", tostring(hopper.id), tostring(ps.engineOn),
        hopper:getFillUnitFillLevel(ps.dieselUnit), hopper:getFillUnitFillLevel(hs.limeUnit), tostring(ps.flowing), conc ~= nil and max:getFillUnitFillLevel(conc) or -1)
end

function SprayDroneDebug.play(max, command)
    local pickup = findVehicleByFile("pickup2017")
    local spec = max[SprayDroneStation.SPEC_NAME]
    local mark = command:match("^mark:(.+)$")
    if mark ~= nil then
        Logging.info("SDT KROK: %s", mark)
    elseif command:find("^hopper") or command == "spawnHopper" then
        SprayDroneDebug.hopperCommand(max, command)
    elseif command:find("^case") then
        SprayDroneDebug.caseCommand(command)
    elseif command == "relayInfo" or command:find("^relayRotate ") then
        SprayDroneDebug.relayCommand(command)
    elseif command:find("^sampler") then
        SprayDroneDebug.samplerCommand(command)
    elseif command:find("^tablet") then
        SprayDroneDebug.tabletCommand(command)
    elseif command == "inputInfo" then
        SprayDroneDebug.inputInfo()
    elseif command:find("^battery") then
        SprayDroneDebug.batteryCommand(command)
    elseif command:find("^scan") or command:find("^wind") or command == "weatherInfo" or command == "sprayMode" or command == "droneCam" or command == "pfApi" or command == "pfTarget" or command:find("^pfS") or command == "takeoffCheck" or command == "takeoffPlaces" then
        SprayDroneDebug.scanCommand(max, command)
    elseif command:find("^spot") then
        SprayDroneDebug.spotCommand(max, command)
    elseif command:find("^pad") then
        SprayDroneDebug.padCommand(max, command)
    elseif command:find("^planner") then
        SprayDroneDebug.plannerCommand(max, command)
    elseif command == "enterMax" then
        g_localPlayer:requestToEnterVehicle(max)
    elseif command == "enterPickup" and pickup ~= nil then
        g_localPlayer:requestToEnterVehicle(pickup)
    elseif command == "leaveSeat" then
        g_localPlayer:leaveVehicle()
    elseif command == "millModeBag" or command == "millModeHose" or command == "millValve" or command == "millSpout" or command == "millBagInfo" then
        -- ventil výstupu (millModeBag = na rouru, millModeHose = na hadici, millValve = přepnout), millSpout = další stav roury
        -- (přeprava -> vedle -> za -> přeprava), millBagInfo = stav ventilu, roury, hlavy a vaku pod ní
        local mill = findVehicleByFile("sdtLimeMill")
        local ms = mill ~= nil and mill[SprayDroneMill.SPEC_NAME] or nil
        if ms == nil or ms.fillHead == nil then
            Logging.info("SDT PLAY: mlýnek s výsypnou rourou nenalezen")
            return
        end
        local wantSpout = command == "millModeBag"
        if command == "millValve" or ((command == "millModeBag" or command == "millModeHose") and wantSpout ~= ms.valveSpout) then
            mill:sprayDroneMillCommand(SprayDroneMill.CMD_VALVE_TOGGLE)
        elseif command == "millSpout" then
            SprayDroneMill.cycleSpout(mill)
        end
        local hx, hy, hz = getWorldTranslation(ms.fillHead)
        local bx, _, bz = SprayDroneMill.getBagSpot(mill)
        local target, warning = SprayDroneMill.getFlowTarget(ms.engineOn, ms.valveSpout, ms.spoutState, SprayDroneMill.isSpoutMoving(mill), mill:getLastSpeed())
        local bag, present = SprayDroneMill.findBag(mill)
        Logging.info("SDT PLAY: mlýnek: ventil %s, roura stav %d (animace %.2f, %s), motor %s, rychlost %.1f km/h -> tok %s%s | hlava %.2f %.2f %.2f (nad zemí %.2f), "
            .. "střed vaku %.2f %.2f | vak %s%s | mezisklad %.1f l, hadice připojená %s, hrdlo %s",
            ms.valveSpout and "roura" or "hadice", ms.spoutState, mill:getAnimationTime(SprayDroneMill.SPOUT_ANIM),
            SprayDroneMill.isSpoutMoving(mill) and "v pohybu" or "stojí", tostring(ms.engineOn), mill:getLastSpeed(), tostring(target),
            warning ~= nil and " (" .. warning .. ")" or "", hx, hy, hz, hy - getTerrainHeightAtWorldPos(g_terrainNode, hx, 0, hz), bx, bz,
            bag ~= nil and string.format("id %s %.0f / %.0f l", tostring(bag.id), bag:getFillUnitFillLevel(1), bag:getFillUnitCapacity(1)) or "žádný",
            present and bag == nil and " (stojí tam plný nebo cizí)" or "", mill:getFillUnitFillLevel(ms.fineUnit),
            tostring(SprayDroneMill.isHoseAttached(mill)), ms.bagNeck ~= nil and tostring(getVisibility(ms.bagNeck)) or "-")
    elseif command == "spawnLimeBigBag" or command == "spawnLimeBigBagFull" then
        -- stojící big bag pod plnicí hlavou výsypné roury mlýnku (Full: s 300 l jemného vápna), poutkem kolmo k rameni jako mlýnek
        local mill = findVehicleByFile("sdtLimeMill")
        local mspec = mill ~= nil and mill[SprayDroneMill.SPEC_NAME] or nil
        if mspec == nil or mspec.fillHead == nil then
            Logging.info("SDT PLAY: mlýnek nebo plnicí hlava nenalezeny")
            return
        end
        local nx, _, nz, dx, dz = SprayDroneMill.getBagSpot(mill)
        local _, rootY = getWorldTranslation(mill.rootNode)
        local ny = math.max(getTerrainHeightAtWorldPos(g_terrainNode, nx, 0, nz), rootY) + 0.03
        if mspec.spoutState == SprayDroneMill.SPOUT_TRANSPORT then
            Logging.info("SDT PLAY: pozor, roura je v přepravní poloze, vak bude u boku násypky")
        end
        local data = VehicleLoadingData.new()
        data:setFilename(SprayDroneMill.MOD_DIR .. "objects/limeBigBag/limeBigBag.xml")
        data:setPosition(nx, ny, nz)
        data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz) + math.pi, 0)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(max:getOwnerFarmId())
        data:load(function(_, vehicles, state)
            local v = vehicles ~= nil and vehicles[1] or nil
            if state ~= VehicleLoadingState.OK or v == nil then
                Logging.info("SDT PLAY: big bag se nepodařilo načíst (%s)", tostring(state))
                return
            end
            if command == "spawnLimeBigBagFull" then
                v:addFillUnitFillLevel(max:getOwnerFarmId(), 1, 300, FillType.SDT_FINE_LIME, ToolType.UNDEFINED, nil)
            end
            Logging.info("SDT PLAY: big bag id %s na %.1f %.1f %.1f, %.0f l", tostring(v.id), nx, ny, nz, v:getFillUnitFillLevel(1))
        end)
    elseif command == "millCam" then
        -- pohled v souřadnicích mlýnku (atribut view = 6 čísel jako u příkazu view: nohy hráče a cíl pohledu)
        local mill = findVehicleByFile("sdtLimeMill")
        local v = SprayDroneDebug.view
        if mill ~= nil and v ~= nil then
            local fx, fy, fz = localToWorld(mill.rootNode, v[1], v[2], v[3])
            local tx, ty, tz = localToWorld(mill.rootNode, v[4], v[5], v[6])
            g_localPlayer.mover:setFlightActive(true, true)
            g_localPlayer.mover:teleportTo(fx, fy, fz, true)
            local dx, dy, dz = tx - fx, ty - (fy + SprayDroneDebug.EYE_HEIGHT), tz - fz
            local len = MathUtil.vector3Length(dx, dy, dz)
            local pitch, yaw = MathUtil.directionToPitchYaw(dx / len, dy / len, dz / len)
            g_localPlayer.camera:setRotation(pitch, yaw, 0)
        end
    elseif command == "bagStatus" then
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if v.configFileName ~= nil and v.configFileName:find("limeBigBag") then
                local x, y, z = getWorldTranslation(v.rootNode)
                Logging.info("SDT PLAY: big bag id %s: %.1f l, poloha %.2f %.2f %.2f", tostring(v.id), v:getFillUnitFillLevel(1), x, y, z)
            end
        end
    elseif command == "pumpStore" or command == "pumpTake" or command == "pumpSlotInfo" or command == "pumpFuel" then
        SprayDroneDebug.pumpSlotCommand(command)
    elseif command == "clearBags" then
        local n = 0
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if SprayDroneToolbox.getCanisterKind(v) == FillType.SDT_FINE_LIME then
                v:delete()
                n = n + 1
            end
        end
        for _, part in ipairs(spec.toolbox.parts) do
            part.spawnCounter = 0
        end
        Logging.info("SDT PLAY: smazáno pytlů vápna: %d", n)
    elseif command == "fillLime" then
        local unit = SprayDroneToolbox.getConcentrateUnit(max)
        if unit ~= nil then
            max:addFillUnitFillLevel(max:getOwnerFarmId(), unit, 1e6, FillType.SDT_FINE_LIME, ToolType.UNDEFINED, nil)
            Logging.info("SDT PLAY: koncentrát %.0f l", max:getFillUnitFillLevel(unit))
        end
    elseif command == "lookBox" then
        -- hráč 1,1 m před dvířky bedny (od osy vleku ven), pohled na aktivační uzel: pro skutečný klik myší a klávesu R
        local node = SprayDroneToolbox.getRefNode(max, spec.toolbox.parts[1])
        local nx, ny, nz = getWorldTranslation(node)
        local mx, _, mz = getWorldTranslation(max.rootNode)
        local dx, dz = nx - mx, nz - mz
        local length = math.max(math.sqrt(dx * dx + dz * dz), 0.01)
        local fx, fz = nx + dx / length * 1.1, nz + dz / length * 1.1
        local fy = ny - SprayDroneDebug.EYE_HEIGHT * 0.6
        g_localPlayer.mover:setFlightActive(true, true)
        g_localPlayer.mover:teleportTo(fx, fy, fz, true)
        local ex, ey, ez = nx - fx, ny - (fy + SprayDroneDebug.EYE_HEIGHT), nz - fz
        local el = MathUtil.vector3Length(ex, ey, ez)
        local pitch, yaw = MathUtil.directionToPitchYaw(ex / el, ey / el, ez / el)
        g_localPlayer.camera:setRotation(pitch, yaw, 0)
        Logging.info("SDT PLAY: hráč před dvířky bedny na %.1f %.1f %.1f", fx, fy, fz)
    elseif command == "selectMax" and pickup ~= nil then
        pickup:setSelectedImplementByObject(max)
        local selected = pickup:getSelectedImplement()
        Logging.info("SDT PLAY: vybrané nářadí pickupu: %s", selected ~= nil and tostring(selected.object.configFileNameClean) or "nic")
    elseif command == "detachMax" and pickup ~= nil then
        pickup:detachImplementByObject(max)
    elseif command == "attachMax" and pickup ~= nil then
        if max:getAttacherVehicle() == pickup then
            Logging.info("SDT PLAY: vlek už za pickupem je")
            return
        end
        -- spojka pickupu (trailerCar) s vlekem (trailer) typem nesedí, jako v testovacím savegame se zapřáhne násilně: nejzadnější volný kloub pickupu a první vstup vleku
        local inputs = max.spec_attachable.inputAttacherJoints
        local joints = pickup.spec_attacherJoints.attacherJoints
        local ji, rearZ
        for i, joint in ipairs(joints) do
            local _, _, lz = localToLocal(joint.jointTransform, pickup.rootNode, 0, 0, 0)
            Logging.info("SDT PLAY: kloub pickupu %d: typ %s, vzadu %.2f, obsazen %s", i, tostring(joint.jointType), lz, tostring(joint.jointIndex ~= 0))
            if joint.jointIndex == 0 and (rearZ == nil or lz < rearZ) then
                ji, rearZ = i, lz
            end
        end
        local input = inputs[1]
        if ji == nil or input == nil then
            Logging.info("SDT PLAY: chybí kloub pickupu nebo vstup vleku")
            return
        end
        local joint = joints[ji]
        local rx, ry, rz = getWorldRotation(max.rootNode)
        local mx, my, mz = getWorldTranslation(max.rootNode)
        pickup:setAbsolutePosition(mx, my + 0.5, mz, rx, ry, rz)
        local ix, iy, iz = getWorldTranslation(input.node)
        local jx, jy, jz = getWorldTranslation(joint.jointTransform)
        pickup:setAbsolutePosition(mx + ix - jx, my + 0.5 + iy - jy, mz + iz - jz, rx, ry, rz)
        pickup:attachImplement(max, 1, ji)
        Logging.info("SDT PLAY: pickup zapřažen za vlek (klouby %d/1): %s", ji, tostring(max:getAttacherVehicle() == pickup))
    elseif command == "fieldInfo" or command == "ownField" or command == "selectField" then
        local x, _, z = getWorldTranslation(max.rootNode)
        local list = getFieldDistances(x, z)
        local farmId = max:getOwnerFarmId()
        for i = 1, math.min(#list, command == "fieldInfo" and 6 or 1) do
            local e = list[i]
            if command == "ownField" then
                g_farmlandManager:setLandOwnership(e.field:getId(), farmId)
            elseif command == "selectField" then
                max:sprayDroneCommand(SprayDroneCommandEvent.SELECT_FIELD, e.field:getId())
            end
            Logging.info("SDT PLAY: pole %s ve vzdálenosti %.0f m, vlastník %s, povoleno %s", tostring(e.field:getId()), e.distance, tostring(e.field:getOwner()),
                tostring((SprayDroneStation.getFieldAllowed(max, e.field))))
        end
    end
end

function SprayDroneDebug.runGlobal(command) -- DEBUG
    if command:find("^millView") or command:find("^pumpView") then
        SprayDroneDebug.millView(command)
    elseif command == "nodeSnap" or command == "nodeDiff" then
        SprayDroneDebug.nodeSnap(command)
    elseif command == "spawnPump" then
        SprayDroneDebug.spawnPump()
    elseif command == "pumpStatus" or command == "pumpOn" or command == "pumpOff" or command == "pumpToTrailer" or command == "pumpToIbc"
        or command == "pumpModeTank" or command == "pumpModePond" then
        SprayDroneDebug.pumpStatus(command)
    elseif command == "spawnIbc" or command == "spawnIbcEmpty" then
        SprayDroneDebug.spawnIbc(command == "spawnIbcEmpty")
    elseif command == "spawnMiddle" or command == "spawnMiddleRtk" then
        SprayDroneDebug.spawnMiddle(command == "spawnMiddleRtk")
    elseif command == "removeMiddle" then
        SprayDroneDebug.removeMiddle()
    elseif command == "whStatus" then
        SprayDroneDebug.whStatus()
    elseif command:find("^viewPort") then
        local index = tonumber(command:match("^viewPort(%d+)"))
        local dist = tonumber(command:match("^viewPort%d+_(%d+)")) or 18
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if v[SprayDroneWaterHose.SPEC_NAME] ~= nil then
                for _, a in ipairs(SprayDroneWaterHose.getActivePorts(v)) do
                    if a.index == index then
                        local x, y, z = getWorldTranslation(a.node)
                        local ox, _, oz = localDirectionToWorld(v.rootNode, -1, 0, 0)
                        local d = dist / 10
                        local cx, cy, cz = x + ox * d, y + 0.5, z + oz * d
                        local player = g_localPlayer
                        player.mover:setFlightActive(true, true)
                        player.mover:teleportTo(cx, cy - SprayDroneDebug.EYE_HEIGHT, cz, true)
                        local dx, dy, dz = x - cx, y - cy, z - cz
                        local len = MathUtil.vector3Length(dx, dy, dz)
                        local pitch, yaw = MathUtil.directionToPitchYaw(dx / len, dy / len, dz / len)
                        player.camera:setRotation(pitch, yaw, 0)
                        Logging.info("SDT VIEWPORT: ventil %d na %s", index, tostring(v:getName()))
                    end
                end
            end
        end
    elseif command == "saveGame" then
        local m = g_currentMission
        Logging.info("SDT SAVE: saveSavegame=%s startSaveSavegame=%s controller=%s", type(m.saveSavegame), type(m.startSaveSavegame), type(g_savegameController))
        if g_savegameController ~= nil then
            for k, v in pairs(getmetatable(g_savegameController).__index or {}) do
                if type(v) == "function" and tostring(k):lower():find("save") then
                    Logging.info("SDT SAVE: controller.%s", tostring(k))
                end
            end
        end
        if m.saveSavegame ~= nil then
            m:saveSavegame()
        elseif g_savegameController ~= nil and g_savegameController.saveSavegame ~= nil then
            g_savegameController:saveSavegame(m.missionInfo)
        end
    elseif command == "emptyTanks" then
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            local st = v[SprayDroneStation.SPEC_NAME]
            if st ~= nil and st.fillUnitIndex ~= nil then
                v:addFillUnitFillLevel(v:getOwnerFarmId(), st.fillUnitIndex, -1e6, v:getFillUnitFillType(st.fillUnitIndex), ToolType.UNDEFINED, nil)
            end
        end
    else
        SprayDroneDebug.waterHoseSim(command)
    end
end

function SprayDroneDebug.runCommand(vehicle, command)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    Logging.info("SDT DEBUG: příkaz %s (vozidlo %s)", command, tostring(vehicle.id))
    if SprayDroneDebug.SCENES[command] ~= nil then -- DEBUG
        if SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then
            SprayDroneDebug.globalDone = SprayDroneDebug.commandId
            SprayDroneDebug.SCENES[command]()
        end
        return
    end
    if command == "targetMax" or command == "targetMiddle" then -- DEBUG
        SprayDroneDebug.playTarget = command == "targetMiddle" and "sprayDroneTrailerMiddle" or "sprayDroneTrailerMax"
        return
    end
    if command:find("^mark:") or SprayDroneDebug.PLAY[command] ~= nil then -- DEBUG
        -- příkazy průchodu hrou platí pro jeden vlek (targetMax / targetMiddle), bez volby pro první, který je dostane
        local target = SprayDroneDebug.playTarget
        if target ~= nil and not command:find("^mark:") and (vehicle.configFileName == nil or not vehicle.configFileName:find(target, 1, true)) then
            return
        end
        if SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then
            SprayDroneDebug.globalDone = SprayDroneDebug.commandId
            SprayDroneDebug.play(vehicle, command)
        end
        return
    end
    if command == "traceOn" then
        SprayDroneDebug.trace = true
    elseif command == "traceOff" then
        SprayDroneDebug.trace = false
    elseif command == "chargeAll" then
        for _, battery in ipairs(spec.batteries) do
            battery.charge = spec.batteryCapacity
        end
        SprayDroneDrones.forEachSpec(vehicle, function(d)
            if d.droneBattery ~= nil then
                d.battery = d.batteryCapacity
            end
        end)
        vehicle:raiseDirtyFlags(spec.dirtyFlag)
    elseif command == "fillTrailer" then
        local _, fillType = SprayDroneStation.getSprayType(vehicle)
        SprayDroneDebug.fillUnit(vehicle, spec.fillUnitIndex, fillType)
    elseif command == "fillWater" then
        SprayDroneDebug.fillUnit(vehicle, spec.fillUnitIndex, FillType.WATER)
    elseif command == "fillConcentrate" then
        local concIndex = SprayDroneStation.getConcentrateUnit(vehicle)
        if concIndex ~= nil then
            local wanted = SprayDroneDebug.getConcentrateType(vehicle) or FillType.SDT_CONCENTRATE_FERTILIZER
            SprayDroneDebug.fillUnit(vehicle, concIndex, SprayDroneDebug.typeOrDefault(vehicle, concIndex, wanted))
        end
    elseif command == "fillDiesel" then
        local missing = vehicle:getFillUnitCapacity(spec.dieselFillUnitIndex) - vehicle:getFillUnitFillLevel(spec.dieselFillUnitIndex)
        vehicle:addFillUnitFillLevel(vehicle:getOwnerFarmId(), spec.dieselFillUnitIndex, missing, FillType.DIESEL, ToolType.UNDEFINED, nil)
    elseif command == "toolboxFill" then -- DEBUG
        SprayDroneToolbox.debugFill(vehicle)
    elseif command == "toolboxOpen" then -- DEBUG
        SprayDroneToolbox.debugToggleOpen(vehicle)
    elseif command == "toolboxDialog" then -- DEBUG
        SprayDroneToolbox.debugDialog(vehicle)
    elseif command == "spawnCanister" then -- DEBUG
        SprayDroneToolbox.debugSpawnCanister(vehicle)
    elseif command == "spawnAtCamera" then -- DEBUG
        SprayDroneToolbox.debugSpawnAtCamera(vehicle)
    elseif command == "spawnSet" then -- DEBUG
        SprayDroneToolbox.debugSpawnSet(vehicle)
    elseif command == "spawnDiesel" then -- DEBUG
        SprayDroneToolbox.debugSpawnAtCamera(vehicle, FillType.DIESEL)
    elseif command == "pickConcentrate" then -- DEBUG
        if SprayDroneToolbox.debugIsNearest(vehicle) then
            SprayDroneToolbox.debugPickup(vehicle, true)
        end
    elseif command == "lookNewest" then -- DEBUG
        SprayDroneToolbox.debugLookAtNewest(vehicle)
    elseif command == "handPour" then -- DEBUG
        SprayDroneToolbox.debugHandPour(vehicle)
    elseif command == "millOn" or command == "millOff" or command == "millFill" or command == "millStatus" then -- DEBUG
        SprayDroneDebug.mill(command)
    elseif command == "shop" then -- DEBUG
        g_gui:showGui("ShopMenu")
    elseif command == "view" then -- DEBUG
        SprayDroneDebug.applyView(vehicle)
    elseif command == "feet" then -- DEBUG
        local px, py, pz = g_localPlayer:getPosition()
        local lx, ly, lz = worldToLocal(vehicle.rootNode, px, py, pz)
        Logging.info("SDT DEBUG feet: hráč v souřadnicích vleku x=%.2f výška=%.2f dopředu=%.2f (i3d)", lx, ly, lz)
    elseif command == "colProbe" then -- DEBUG
        SprayDroneDebug.colProbe(vehicle)
    elseif (command == "toolboxRows" or command == "toolboxTake2") and vehicle[SprayDroneStation.SPEC_NAME].toolbox ~= nil then -- DEBUG
        if command == "toolboxTake2" then
            SprayDroneToolbox.command(vehicle, SprayDroneToolboxEvent.OPEN, nil, 1, true)
            SprayDroneToolbox.command(vehicle, SprayDroneToolboxEvent.TAKE, FillType.SDT_CONCENTRATE_FERTILIZER, 2, true)
        end
        local tb = vehicle[SprayDroneStation.SPEC_NAME].toolbox
        local shown, full = {}, 0
        for i = 1, SprayDroneToolbox.MAX_SLOTS do
            local node = SprayDroneStation.getMappedNode(vehicle, "toolboxCanister" .. i)
            if node ~= nil and getVisibility(node) then
                table.insert(shown, i)
            end
        end
        for i = 1, tb.slots do
            if tb.canisters[i].fillType ~= FillType.UNKNOWN then
                full = full + 1
            end
        end
        Logging.info("SDT TOOLBOX %s: slotů %d, plných %d, viditelné pozice modelu: %s", vehicle.configFileNameClean or tostring(vehicle.id), tb.slots, full, table.concat(shown, " "))
    elseif command == "deckInfo" and (vehicle.configFileNameClean == "sprayDroneTrailerMiddle" or vehicle.configFileNameClean == "sprayDroneTrailerMax") then -- DEBUG: kde jsou kolize horní paluby vůči kořeni a těžišti
        local spec = vehicle[SprayDroneStation.SPEC_NAME]
        local node = vehicle.components[1].node
        local cx, cy, cz = getCenterOfMass(node)
        local com = spec.centerOfMass or {}
        Logging.info("SDT DECK %s: frozen %s loadedFrozen %s isDynamic %s, těžiště teď %.3f %.3f %.3f, uložené %s %s %s, hmotnost %.3f t",
            vehicle.configFileNameClean, tostring(spec.frozen), tostring(spec.loadedFrozen), tostring(vehicle.components[1].isDynamic), cx, cy, cz,
            tostring(com[1]), tostring(com[2]), tostring(com[3]), getMass(node))
        local rx, ry, rz = getWorldRotation(node)
        local lx, ly, lz = getRotation(node)
        Logging.info("SDT DECK   rotace kořene svět %.2f %.2f %.2f°, lokální %.2f %.2f %.2f°, rodič %s, typ tělesa %s", math.deg(rx), math.deg(ry), math.deg(rz),
            math.deg(lx), math.deg(ly), math.deg(lz), getName(getParent(node)), tostring(getRigidBodyType(node)))
        for i = 0, getNumOfChildren(node) - 1 do
            local group = getChildAt(node, i)
            if getName(group) == "collisions" then
                for j = 0, getNumOfChildren(group) - 1 do
                    local shape = getChildAt(group, j)
                    local name = getName(shape)
                    if name == "colTopDeck" or name == "colChassis" or name == "colChest" then
                        local x, y, z = getTranslation(shape)
                        Logging.info("SDT DECK   %s: translace %.3f %.3f %.3f, viditelnost %s", name, x, y, z, tostring(getVisibility(shape)))
                    end
                end
            end
        end
        SprayDroneDebug.deckHits = {}
        local points = {}
        for x = -1.0, 1.01, 0.25 do
            table.insert(points, { x, 0 })
        end
        for z = -2.0, 2.01, 0.5 do
            table.insert(points, { 0.4, z })
        end
        for _, p in ipairs(points) do
            local wx, wy, wz = localToWorld(node, p[1], 5, p[2])
            local dx, dy, dz = localDirectionToWorld(node, 0, -1, 0)
            local hits = {}
            SprayDroneDebug.deckHitList = hits
            raycastAll(wx, wy, wz, dx, dy, dz, 8, "deckHitCallback", SprayDroneDebug, CollisionFlag.VEHICLE + CollisionFlag.DYNAMIC_OBJECT)
            Logging.info("SDT DECK   paprsek x=%.1f z=%.1f: %s", p[1], p[2], table.concat(hits, ", "))
        end
    elseif command:find("^deckDrop") and vehicle.configFileNameClean == "sprayDroneTrailerMiddle" then -- DEBUG: deckDrop x z = dron M nad palubu
        local d = SprayDroneDebug.deckDrone
        if command == "deckDropCheck" then
            if d ~= nil and not d.isDeleted then
                local x, y, z = worldToLocal(vehicle.components[1].node, getWorldTranslation(d.rootNode))
                Logging.info("SDT DECKDROP dron ve vleku x=%.2f y=%.2f z=%.2f (paluba 2.50)", x, y, z)
            end
        else
            if d ~= nil and not d.isDeleted then
                d:delete()
            end
            local px, pz = command:match("^deckDrop (%S+) (%S+)$")
            local wx, wy, wz = localToWorld(vehicle.components[1].node, tonumber(px) or 0, 3.3, tonumber(pz) or 0)
            local data = VehicleLoadingData.new()
            data:setFilename(SprayDroneHopper.MOD_DIR .. "objects/drone/droneM.xml")
            data:setPosition(wx, wy, wz)
            data:setRotation(0, 0, 0)
            data:setPropertyState(VehiclePropertyState.OWNED)
            data:setOwnerFarmId(1)
            data:load(function(_, vehicles, state)
                SprayDroneDebug.deckDrone = vehicles ~= nil and vehicles[1] or nil
                Logging.info("SDT DECKDROP spawn %s", tostring(state))
            end)
        end
    elseif command == "accessStatus" then -- DEBUG: nabíječka a držák tyčí podle stavu skládání
        local rs = vehicle[SprayDroneStation.SPEC_NAME].relaySlots
        Logging.info("SDT ACCESS %s: čas skládání %.6f, rozloženo %s, nabíječka %s, držák tyčí: pod plachtou %s, nabízí se %s",
            vehicle.configFileNameClean or tostring(vehicle.id), vehicle:getFoldAnimTime(), tostring(vehicle:getIsUnfolded()),
            tostring(SprayDroneBatterySlots.getAccessProblem(vehicle) or "OK"), tostring(rs ~= nil and rs.underTarp),
            tostring(rs ~= nil and #rs.slots > 0 and not (rs.underTarp and not vehicle:getIsUnfolded())))
    elseif command == "foldTrailer" or command == "unfoldTrailer" then -- DEBUG
        vehicle:setFoldState(command == "foldTrailer" and 1 or -1, false)
    elseif command == "foldClockFold" or command == "foldClockUnfold" then -- DEBUG
        SprayDroneDebug.startFoldClock(vehicle, command == "foldClockFold" and 1 or -1)
    elseif command == "foldLeaveFold" or command == "foldLeaveUnfold" or command == "foldLeaveUnfoldNoKeep" then -- DEBUG
        vehicle.spec_foldable.keepFoldingWhileDetached = command ~= "foldLeaveUnfoldNoKeep"
        SprayDroneDebug.startFoldClock(vehicle, command == "foldLeaveFold" and 1 or -1, 1500)
    elseif command:find("^foldAt%d+$") then -- DEBUG
        local t = tonumber(command:match("%d+")) / 100
        Foldable.setAnimTime(vehicle, t, false, false)
        Logging.info("SDT DEBUG foldAt: %s čas skládání nastaven na %.3f (čte se %.3f)", vehicle.configFileNameClean or tostring(vehicle.id), t, vehicle:getFoldAnimTime())
    elseif (command == "millAttachMax" or command == "millAttachPickup") and SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then -- DEBUG
        SprayDroneDebug.globalDone = SprayDroneDebug.commandId
        local toMax = command == "millAttachMax"
        local mill = findVehicleByFile("sdtLimeMill")
        local max = findVehicleByFile("sprayDroneTrailerMax")
        local carrier = toMax and max or findVehicleByFile("pickup2017")
        if mill == nil or carrier == nil then
            Logging.info("SDT MILLATTACH: chybí mlýnek nebo nosič")
            return
        end
        local old = mill:getAttacherVehicle()
        if old ~= nil then
            old:detachImplementByObject(mill)
        end
        if not toMax and max ~= nil and max:getAttacherVehicle() == carrier then
            carrier:detachImplementByObject(max)
        end
        local joints = carrier.spec_attacherJoints.attacherJoints
        local ji, inputIndex, rearZ = 1, 3, nil
        if not toMax then
            inputIndex = 1
            ji = nil
            for i, joint in ipairs(joints) do
                local _, _, lz = localToLocal(joint.jointTransform, carrier.rootNode, 0, 0, 0)
                if joint.jointIndex == 0 and (rearZ == nil or lz < rearZ) then
                    ji, rearZ = i, lz
                end
            end
        end
        local joint = joints[ji]
        local input = mill.spec_attachable.inputAttacherJoints[inputIndex]
        local rx, ry, rz = getWorldRotation(carrier.rootNode)
        local jx, jy, jz = getWorldTranslation(joint.jointTransform)
        mill:setAbsolutePosition(jx, jy + 0.3, jz, rx, ry, rz)
        local ix, iy, iz = getWorldTranslation(input.node)
        mill:setAbsolutePosition(jx - (ix - jx), jy + 0.3 - (iy - jy), jz - (iz - jz), rx, ry, rz)
        carrier:attachImplement(mill, inputIndex, ji)
        Logging.info("SDT MILLATTACH: mlýnek za %s (kloub %s, vstup %d): %s", toMax and "Max" or "pickup", tostring(ji), inputIndex, tostring(mill:getAttacherVehicle() == carrier))
    elseif command == "millSupport" or command == "detachMill" then -- DEBUG
        local mill = findVehicleByFile("sdtLimeMill")
        if mill ~= nil and SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then
            SprayDroneDebug.globalDone = SprayDroneDebug.commandId
            local carrier = mill:getAttacherVehicle()
            if command == "detachMill" and carrier ~= nil then
                carrier:detachImplementByObject(mill)
            end
            local jw = SprayDroneStation.getMappedNode(mill, "jockeyWheel")
            local _, jy = getTranslation(jw)
            Logging.info("SDT MILLSUPPORT: moveSupport čas %.3f, jockeyWheel y=%.3f, tažen %s", mill:getAnimationTime("moveSupport"), jy, tostring(mill:getAttacherVehicle() ~= nil))
        end
    elseif (command == "spawnRelay" or command == "spawnMiniWood" or command == "spawnMiniSteel") and SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then -- DEBUG
        SprayDroneDebug.globalDone = SprayDroneDebug.commandId
        local cam = getCamera()
        local cx, _, cz = getWorldTranslation(cam)
        local dx, _, dz = localDirectionToWorld(cam, 0, 0, -1)
        local len = math.sqrt(dx * dx + dz * dz)
        local x, z = cx + dx / len * 4, cz + dz / len * 4
        local data = VehicleLoadingData.new()
        if command == "spawnRelay" then
            data:setFilename(SprayDroneHopper.MOD_DIR .. "objects/relay/relayPole.xml")
        else
            data:setFilename(SprayDroneHopper.MOD_DIR .. "vehicles/sprayDroneTrailerMini/sprayDroneTrailerMini.xml")
            data:setConfigurations({ [SprayDroneStation.DECK_EDGE_CONFIG] = command == "spawnMiniWood" and 2 or 1 })
        end
        data:setPosition(x, terrainY(x, z) + 0.2, z)
        data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz) + math.pi / 2, 0)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(1)
        data:load(function(_, vehicles, state)
            local v = vehicles ~= nil and vehicles[1] or nil
            Logging.info("SDT SPAWN %s: %s (id %s, konfigurace deckEdge=%s)", command, state == VehicleLoadingState.OK and "hotovo" or "chyba", tostring(v ~= nil and v.id),
                tostring(v ~= nil and v.configurations ~= nil and v.configurations[SprayDroneStation.DECK_EDGE_CONFIG]))
        end)
    elseif (command == "relaySpawn" or command == "relaySpawn dir") and SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then -- DEBUG
        -- relaySpawn = všesměrová tyč 2 m východně od hráče; relaySpawn dir = směrová 2 m před hráčem, čelem po směru pohledu
        SprayDroneDebug.globalDone = SprayDroneDebug.commandId
        local px, _, pz = g_localPlayer:getPosition()
        local x, z, ry = px + 2, pz, 0
        local file = "objects/relay/relayPole.xml"
        if command == "relaySpawn dir" then
            local dx, _, dz = localDirectionToWorld(g_cameraManager:getActiveCamera(), 0, 0, -1)
            local len = math.max(MathUtil.vector2Length(dx, dz), 0.001)
            dx, dz = dx / len, dz / len
            x, z, ry = px + dx * 2, pz + dz * 2, math.atan2(dx, dz)
            file = "objects/relay/relayPoleDirectional.xml"
        end
        local data = VehicleLoadingData.new()
        data:setFilename(SprayDroneHopper.MOD_DIR .. file)
        data:setPosition(x, terrainY(x, z) + 0.1, z)
        data:setRotation(0, ry, 0)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(1)
        data:load(function(_, vehicles, state)
            Logging.info("SDT RELAY spawn: %s id %s", tostring(state), tostring(vehicles ~= nil and vehicles[1] ~= nil and vehicles[1].id))
        end)
    elseif command == "relayTake" and SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then -- DEBUG: hráč k držáku tyčí, vyndá tyč jako R
        SprayDroneDebug.globalDone = SprayDroneDebug.commandId
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            local spec = v[SprayDroneStation.SPEC_NAME]
            local rs = spec ~= nil and spec.relaySlots or nil
            if rs ~= nil and #rs.slots > 0 and not v.isDeleted then
                local index = 1
                for i, slot in ipairs(rs.slots) do
                    if slot.occupied then
                        index = i
                        break
                    end
                end
                local nx, ny, nz = getWorldTranslation(rs.nodes[index])
                local cx, _, cz = getWorldTranslation(v.rootNode)
                local dx, dz = nx - cx, nz - cz
                local len = math.max(math.sqrt(dx * dx + dz * dz), 0.01)
                local fx, fz = nx + dx / len * 1.2, nz + dz / len * 1.2
                g_localPlayer.mover:teleportTo(fx, terrainY(fx, fz), fz, true)
                if rs.slots[index].occupied then
                    SprayDroneRelaySlots.command(v, SprayDroneRelaySlotEvent.TAKE, nil, index)
                else
                    -- prázdný držák: tyč postavená 1 m za hráčem od vleku, jako by ji vyndal
                    local tx, tz = fx + dx / len, fz + dz / len
                    local data = VehicleLoadingData.new()
                    data:setFilename(SprayDroneHopper.MOD_DIR .. "objects/relay/relayPole.xml")
                    data:setPosition(tx, terrainY(tx, tz) + 0.1, tz)
                    data:setRotation(0, 0, 0)
                    data:setPropertyState(VehiclePropertyState.OWNED)
                    data:setOwnerFarmId(1)
                    data:load(function() end)
                end
                Logging.info("SDT RELAY take: vlek %s slot %d obsazen %s (%.1f %.1f %.1f), hráč na %.1f %.1f", tostring(v.id), index,
                    tostring(rs.slots[index].occupied), nx, ny, nz, fx, fz)
                return
            end
        end
        Logging.info("SDT RELAY take: žádný obsazený držák")
    elseif command == "relayAct" and SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then -- DEBUG: proč tyč nenabízí R
        SprayDroneDebug.globalDone = SprayDroneDebug.commandId
        local px, py, pz = g_localPlayer:getPosition()
        local sys = g_currentMission.activatableObjectsSystem
        for k, val in pairs(sys) do
            if type(val) ~= "function" then
                Logging.info("SDT RELAY systém aktivací: %s = %s%s", tostring(k), tostring(val), type(val) == "table" and (" (" .. tostring(#val) .. ")") or "")
            end
        end
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            local rs = v[SprayDroneRelay.SPEC_NAME]
            if rs ~= nil and not v.isDeleted then
                local act = rs.activatable
                local x, y, z = getWorldTranslation(v.rootNode)
                local registered = false
                for _, list in pairs(sys) do
                    if type(list) == "table" then
                        for key, a in pairs(list) do
                            if a == act or key == act then
                                registered = true
                            end
                        end
                    end
                end
                local hands = g_localPlayer.hands
                Logging.info("SDT RELAY id %s (%s): vzdálenost %.2f (getDistance %s), aktivovatelná %s, v systému %s, stojí %s, rozloženo %s, ovládaná %s, v ruce %s",
                    tostring(v.id), rs.sector ~= nil and "směrová" or "všesměrová", MathUtil.vector3Length(px - x, py - y, pz - z), act ~= nil and tostring(act:getDistance(px, py, pz)) or "-",
                    act ~= nil and tostring(act:getIsActivatable()) or "bez aktivace", tostring(registered), tostring(SprayDroneRelay.isUpright(v)),
                    tostring(rs.unfolded), tostring(v.getIsControlled ~= nil and v:getIsControlled()),
                    tostring(hands ~= nil and hands.getIsHoldingItem ~= nil and hands:getIsHoldingItem()))
            end
        end
        SprayDroneDebug.inputInfo()
    elseif command == "relayFold" or command == "relayUnfold" or command == "relayOn" then -- DEBUG
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if v[SprayDroneRelay.SPEC_NAME] ~= nil and not v.isDeleted then
                SprayDroneRelay.setState(v, command ~= "relayFold", command == "relayOn", true, true)
                local rs = v[SprayDroneRelay.SPEC_NAME]
                Logging.info("SDT RELAY id %s: rozloženo=%s zapnuto=%s průběh %.2f", tostring(v.id), tostring(rs.unfolded), tostring(rs.powered), rs.progress)
            end
        end
    elseif command == "storeConfigs" and SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then -- DEBUG
        SprayDroneDebug.globalDone = SprayDroneDebug.commandId
        for _, item in ipairs(g_storeManager:getItems()) do
            if item.xmlFilename ~= nil and item.xmlFilename:find("FS25_SprayDroneTrailer", 1, true) then
                local names = {}
                for configName, set in pairs(item.configurations or {}) do
                    names[#names + 1] = string.format("%s=%d", configName, #set)
                end
                table.sort(names)
                Logging.info("SDT STORE %s: konfigurace %s", tostring(item.xmlFilename), table.concat(names, " "))
            end
        end
    elseif command:find("^spawnHopperColor%d+$") and SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then -- DEBUG
        SprayDroneDebug.globalDone = SprayDroneDebug.commandId
        local index = tonumber(command:match("%d+"))
        local hopper = findHopper()
        local px, py, pz = getWorldTranslation(hopper.rootNode)
        local rx, ry, rz = getWorldRotation(hopper.rootNode)
        local dx, _, dz = localDirectionToWorld(hopper.rootNode, 1, 0, 0)
        local data = VehicleLoadingData.new()
        data:setFilename(SprayDroneHopper.MOD_DIR .. "objects/hopper/limeHopper.xml")
        SprayDroneDebug.hopperColorCount = (SprayDroneDebug.hopperColorCount or 0) + 1
        data:setPosition(px + dx * 3 * SprayDroneDebug.hopperColorCount, py + 0.3, pz + dz * 3 * SprayDroneDebug.hopperColorCount)
        data:setRotation(rx, ry, rz)
        data:setPropertyState(VehiclePropertyState.OWNED)
        data:setOwnerFarmId(1)
        data:setConfigurations({ baseColor = index })
        data:load(function(_, vehicles, state)
            local v = vehicles ~= nil and vehicles[1] or nil
            Logging.info("SDT HOPPERCOLOR: násypka s barvou %d: %s (id %s, config baseColor=%s)", index, state == VehicleLoadingState.OK and "hotovo" or "chyba", tostring(v ~= nil and v.id),
                tostring(v ~= nil and v.configurations ~= nil and v.configurations.baseColor))
        end)
    elseif command == "spawnIbc" or command == "spawnIbcEmpty" or command == "spawnMiddle" or command == "spawnMiddleRtk" or command == "removeMiddle" or command == "emptyTanks" or command == "saveGame" or command:find("^viewPort") or command:find("^whConnect")
        or command == "whValve" or command == "whDrop" or command == "whStatus" or command == "whPond" or command == "whOut"
        or command == "spawnPump" or command == "pumpStatus" or command == "pumpOn" or command == "pumpOff" or command == "pumpToTrailer" or command == "pumpToIbc" or command == "pumpModeTank" or command == "pumpModePond" or command == "nodeSnap" or command == "nodeDiff" or command:find("^millView") or command:find("^pumpView") then -- DEBUG
        if SprayDroneDebug.globalDone ~= SprayDroneDebug.commandId then
            SprayDroneDebug.globalDone = SprayDroneDebug.commandId
            SprayDroneDebug.runGlobal(command)
        end
    elseif command == "millFloor" then -- DEBUG
        SprayDroneDebug.millFloor()
    elseif command == "hudOff" or command == "hudOn" then -- DEBUG
        g_currentMission.hud:setIsVisible(command == "hudOn")
    elseif command == "shopPose" then -- DEBUG
        spec.pad.shopPose = true
        spec.pad.appliedTime = nil
        vehicle:setFoldState(1, true)
    elseif command == "foldCheck" then -- DEBUG
        for _, d in ipairs({ -1, 1 }) do
            local ok, warning = vehicle:getIsFoldAllowed(d, false)
            Logging.info("SDT DEBUG foldCheck směr %d: %s %s (čas %.3f toggled %s parked %s)", d, tostring(ok), tostring(warning), vehicle:getFoldAnimTime(), tostring(vehicle:getToggledFoldDirection()), tostring(vehicle:getSprayDroneIsParked()))
        end
        local rotors = {}
        SprayDroneDrones.forEach(vehicle, function(drone) rotors[#rotors + 1] = string.format("speed=%.2f parked=%s", drone.rotorSpeed or 0, tostring(drone.rotorsParked)) end)
        Logging.info("SDT DEBUG foldCheck rotory: %s", table.concat(rotors, "; "))
    elseif command == "rimInfo" then -- DEBUG
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            local names = {}
            local function walk(node)
                if getHasClassId(node, ClassIds.SHAPE) then
                    for i = 1, getNumOfMaterials(node) do
                        local slot = getMaterialSlotName(node, i - 1)
                        names[slot] = (names[slot] or 0) + 1
                    end
                end
                for i = 0, getNumOfChildren(node) - 1 do
                    walk(getChildAt(node, i))
                end
            end
            for _, component in ipairs(v.components) do
                walk(component.node)
            end
            local list = {}
            for slot, n in pairs(names) do
                table.insert(list, slot .. "=" .. n)
            end
            table.sort(list)
            Logging.info("SDT DEBUG rimInfo %s: %s", tostring(v.configFileName), table.concat(list, " "):sub(1, 900))
        end
    elseif command == "colMap" then -- DEBUG
        SprayDroneDebug.colMap(vehicle)
    elseif command == "probeTarget" then -- DEBUG
        SprayDroneToolbox.debugProbeUntil = g_time + 60000
        Logging.info("SDT DEBUG: HandToolHands.TARGET_MASK=%s PICKUP_DISTANCE=%s", tostring(HandToolHands.TARGET_MASK), tostring(HandToolHands.PICKUP_DISTANCE))
    elseif command == "probeField" then -- DEBUG
        SprayDroneDebug.probeField(vehicle)
    elseif command == "soilProbe" or command == "soilAgain" then -- DEBUG
        SprayDroneDebug.soilProbe(vehicle, command == "soilAgain")
    elseif command == "status" then -- DEBUG
        local tb = spec.toolbox
        local conc = SprayDroneStation.getConcentrateUnit(vehicle)
        local canisters = 0
        for _, v in ipairs(g_currentMission.vehicleSystem.vehicles) do
            if SprayDroneToolbox.getCanisterKind(v) ~= nil then
                canisters = canisters + 1
            end
        end
        Logging.info("SDT DEBUG: kanystrů ve světě: %d", canisters)
        Logging.info("SDT DEBUG: stav: hlavní %.1f l (%s), koncentrát %.1f l, bedna otevřena=%s", vehicle:getFillUnitFillLevel(spec.fillUnitIndex),
            tostring(g_fillTypeManager:getFillTypeNameByIndex(vehicle:getFillUnitFillType(spec.fillUnitIndex))),
            conc ~= nil and vehicle:getFillUnitFillLevel(conc) or -1, tostring(tb.parts[1].open))
    elseif command == "dropOnBox" then -- DEBUG
        SprayDroneToolbox.debugDropOnBox(vehicle)
    elseif command == "dropHeld" then -- DEBUG
        SprayDroneToolbox.debugDropHeld(vehicle)
    elseif command == "holdCanister" then -- DEBUG
        SprayDroneToolbox.debugHold(vehicle)
    elseif command == "pickCanister" then -- DEBUG
        SprayDroneToolbox.debugPickup(vehicle)
    elseif command == "tiltCanister" then -- DEBUG
        SprayDroneToolbox.debugTilt(vehicle)
    elseif command == "tiltDiesel" then -- DEBUG
        SprayDroneToolbox.debugTilt(vehicle, FillType.DIESEL)
    elseif command == "resetCoverage" then
        if spec.fieldId ~= 0 then
            SprayDroneStation.clearCoverage(vehicle, spec.fieldId)
        end
    elseif command == "coverField" then
        local field = SprayDroneRoute.getFieldById(spec.fieldId)
        local sprayType = SprayDroneStation.getSprayType(vehicle)
        if field ~= nil and sprayType ~= nil then
            local frame = SprayDroneRoute.getFrame(field)
            local entry = { type = sprayType.index, ww = spec.workWidth, hl = spec.headlands, lines = {}, headlands = {}, islands = {} }
            for k = 0, math.ceil((frame.maxN - frame.minN) / spec.workWidth) do
                entry.lines[k] = { { -1e7, 1e7 } }
            end
            for i = 1, spec.headlands do
                entry.headlands[i] = { { -1e9, 1e9 } }
            end
            for islandIndex = 1, #SprayDroneRoute.getFieldShape(field).islands do
                entry.islands[islandIndex] = {}
                for i = 1, spec.headlands do
                    entry.islands[islandIndex][i] = { { -1e9, 1e9 } }
                end
            end
            spec.coverage[spec.fieldId] = entry
            SprayDroneStation.markRouteDirty(vehicle)
            SprayDroneStation.raiseCoverage(vehicle, true)
        end
    end
end
