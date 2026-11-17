-- Stanoviště pilota postřikového dronu na servisním vleku a řízení letu dronu (docs/DRON.md).
--
-- Do vleku jde nastoupit jen rozloženého (pilot vyleze po žebříku na plošinu). Dokud je v něm hráč
-- nebo dron není na vleku, vlek nejde složit.
--
-- Let simuluje server: dron (uzel droneRoot) se při vzletu přepojí pod kořen scény a letí po
-- waypointech jedné dávky. Klienti dostávají polohu přes update stream, příkazy posílají eventem.
-- Pole se vybírá v plánovači letu (mapový dialog, scripts/gui/SprayDronePlannerScreen.lua).

source(g_currentModDirectory .. "scripts/SprayDroneRoute.lua")
source(g_currentModDirectory .. "scripts/events/SprayDroneCommandEvent.lua")
source(g_currentModDirectory .. "scripts/gui/SprayDronePlannerScreen.lua")

SprayDroneStation = {}
SprayDroneStation.MOD_NAME = g_currentModName
SprayDroneStation.SPEC_NAME = string.format("spec_%s.sprayDroneStation", g_currentModName)

SprayDroneStation.STATE_PARKED = 0
SprayDroneStation.STATE_FLYING = 1
SprayDroneStation.STATE_RETURNING = 2
SprayDroneStation.STATE_SERVICING = 3
SprayDroneStation.STATE_NUM_BITS = 2

SprayDroneStation.STATUS_NONE = 0
SprayDroneStation.STATUS_FIELD_DONE = 1
SprayDroneStation.STATUS_TRAILER_EMPTY = 2
SprayDroneStation.STATUS_UNREACHABLE = 3
SprayDroneStation.STATUS_ABORTED = 4
SprayDroneStation.STATUS_NOT_ALLOWED = 5
SprayDroneStation.STATUS_NUM_BITS = 3

SprayDroneStation.STATUS_TEXTS = {
    [1] = "sdt_status_fieldDone",
    [2] = "sdt_status_trailerEmpty",
    [3] = "sdt_status_unreachable",
    [4] = "sdt_status_aborted",
    [5] = "sdt_status_notAllowed"
}

SprayDroneStation.STATE_TEXTS = {
    [0] = "sdt_state_parked",
    [1] = "sdt_state_flying",
    [2] = "sdt_state_returning",
    [3] = "sdt_state_servicing"
}

SprayDroneStation.SERVICE_TIME = 5000
SprayDroneStation.RESUME_AFTER_LOAD_TIME = 3000
SprayDroneStation.ROUTE_REFRESH_TIME = 5000
SprayDroneStation.MAX_TRAILER_SPEED = 3

function SprayDroneStation.prerequisitesPresent(specializations)
    return SpecializationUtil.hasSpecialization(Enterable, specializations)
        and SpecializationUtil.hasSpecialization(Foldable, specializations)
        and SpecializationUtil.hasSpecialization(FillUnit, specializations)
end

function SprayDroneStation.initSpecialization()
    local schema = Vehicle.xmlSchema
    schema:setXMLSpecializationType("SprayDroneStation")
    local key = "vehicle.sprayDrone"
    schema:register(XMLValueType.NODE_INDEX, key .. "#node", "Kořen dronu", "droneRoot")
    schema:register(XMLValueType.INT, key .. "#fillUnitIndex", "Nádrž vleku, ze které se dron doplňuje", 1)
    schema:register(XMLValueType.FLOAT, key .. "#range", "Dosah od vleku (m)", 300)
    schema:register(XMLValueType.FLOAT, key .. "#workWidth", "Záběr postřiku (m)", 9)
    schema:register(XMLValueType.FLOAT, key .. "#tankCapacity", "Nádrž dronu (l)", 40)
    schema:register(XMLValueType.FLOAT, key .. "#batteryMinutes", "Výdrž baterie (min)", 9)
    schema:register(XMLValueType.FLOAT, key .. "#cruiseSpeed", "Rychlost přeletu (m/s)", 10)
    schema:register(XMLValueType.FLOAT, key .. "#sprayingSpeed", "Rychlost při postřiku (m/s)", 7)
    schema:register(XMLValueType.FLOAT, key .. "#climbSpeed", "Rychlost stoupání a klesání (m/s)", 3)
    schema:register(XMLValueType.FLOAT, key .. "#sprayHeight", "Výška postřiku nad terénem (m)", 3)
    schema:register(XMLValueType.FLOAT, key .. "#transitHeight", "Výška přeletu nad terénem (m)", 12)
    schema:register(XMLValueType.FLOAT, key .. "#usageScale", "Násobek spotřeby l/ha oproti vanilla", 1)
    schema:setXMLSpecializationType()

    local savegame = Vehicle.xmlSchemaSavegame
    local saveKey = string.format("vehicles.vehicle(?).%s.sprayDroneStation", SprayDroneStation.MOD_NAME)
    savegame:register(XMLValueType.INT, saveKey .. "#fieldId", "Vybrané pole (farmland id)")
    savegame:register(XMLValueType.BOOL, saveKey .. "#missionActive", "Mise běží")
    savegame:register(XMLValueType.FLOAT, saveKey .. "#droneFillLevel", "Náplň dronu (l)")
    savegame:register(XMLValueType.STRING, saveKey .. "#droneFillType", "Druh náplně dronu")
    savegame:register(XMLValueType.FLOAT, saveKey .. "#battery", "Zbývající baterie (s)")
end

function SprayDroneStation.registerFunctions(vehicleType)
    SpecializationUtil.registerFunction(vehicleType, "sprayDroneCommand", SprayDroneStation.sprayDroneCommand)
    SpecializationUtil.registerFunction(vehicleType, "getSprayDroneIsParked", SprayDroneStation.getSprayDroneIsParked)
end

function SprayDroneStation.registerOverwrittenFunctions(vehicleType)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getIsEnterable", SprayDroneStation.getIsEnterable)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getIsFoldAllowed", SprayDroneStation.getIsFoldAllowed)
end

function SprayDroneStation.registerEventListeners(vehicleType)
    SpecializationUtil.registerEventListener(vehicleType, "onLoad", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onDelete", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onUpdate", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onRegisterActionEvents", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onReadStream", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onWriteStream", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onReadUpdateStream", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onWriteUpdateStream", SprayDroneStation)
end

function SprayDroneStation:onLoad(savegame)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local xml = self.xmlFile
    local key = "vehicle.sprayDrone"

    spec.node = xml:getValue(key .. "#node", nil, self.components, self.i3dMappings)
    if spec.node == nil then
        Logging.xmlError(xml, "SprayDroneStation: chybí uzel dronu (%s#node)", key)
    else
        spec.parent = getParent(spec.node)
        spec.localTrans = { getTranslation(spec.node) }
        spec.localRot = { getRotation(spec.node) }
    end
    spec.isLinked = true

    spec.fillUnitIndex = xml:getValue(key .. "#fillUnitIndex", 1)
    spec.range = xml:getValue(key .. "#range", 300)
    spec.workWidth = xml:getValue(key .. "#workWidth", 9)
    spec.tankCapacity = xml:getValue(key .. "#tankCapacity", 40)
    spec.batteryCapacity = xml:getValue(key .. "#batteryMinutes", 9) * 60
    spec.cruiseSpeed = xml:getValue(key .. "#cruiseSpeed", 10)
    spec.sprayingSpeed = xml:getValue(key .. "#sprayingSpeed", 7)
    spec.climbSpeed = xml:getValue(key .. "#climbSpeed", 3)
    spec.sprayHeight = xml:getValue(key .. "#sprayHeight", 3)
    spec.transitHeight = xml:getValue(key .. "#transitHeight", 12)
    spec.usageScale = xml:getValue(key .. "#usageScale", 1)
    spec.batteryReserve = 30

    spec.state = SprayDroneStation.STATE_PARKED
    spec.status = SprayDroneStation.STATUS_NONE
    spec.fieldId = 0
    spec.missionActive = false
    spec.droneFillLevel = 0
    spec.droneFillType = FillType.UNKNOWN
    spec.battery = spec.batteryCapacity
    spec.batch = 0
    spec.serviceTimer = 0
    spec.pos = { x = 0, z = 0, h = 0, yaw = 0 }
    spec.path = nil
    spec.wpIndex = 1
    spec.sprayFrom = nil
    spec.isSpraying = false
    spec.netTarget = nil

    spec.actionEvents = {}
    spec.routeDirty = true
    spec.routeTimer = 0
    spec.drawLegs = {}
    spec.numBatches = 0
    spec.routeClipped = false

    spec.dirtyFlag = self:getNextDirtyFlag()

    if savegame ~= nil and not savegame.resetVehicles then
        local saveKey = savegame.key .. "." .. SprayDroneStation.MOD_NAME .. ".sprayDroneStation"
        spec.fieldId = savegame.xmlFile:getValue(saveKey .. "#fieldId", 0)
        spec.missionActive = savegame.xmlFile:getValue(saveKey .. "#missionActive", false)
        spec.droneFillLevel = savegame.xmlFile:getValue(saveKey .. "#droneFillLevel", 0)
        local fillTypeName = savegame.xmlFile:getValue(saveKey .. "#droneFillType")
        spec.droneFillType = g_fillTypeManager:getFillTypeIndexByName(fillTypeName) or FillType.UNKNOWN
        spec.battery = math.clamp(savegame.xmlFile:getValue(saveKey .. "#battery", spec.batteryCapacity), 0, spec.batteryCapacity)
        if spec.missionActive then
            -- po načtení dron stojí na vleku; misi obnoví servis, trasa se spočítá ze stavu pole
            spec.state = SprayDroneStation.STATE_SERVICING
            spec.serviceTimer = SprayDroneStation.RESUME_AFTER_LOAD_TIME
        end
    end
end

function SprayDroneStation:saveToXMLFile(xmlFile, key, usedModNames)
    local spec = self[SprayDroneStation.SPEC_NAME]
    xmlFile:setValue(key .. "#fieldId", spec.fieldId)
    xmlFile:setValue(key .. "#missionActive", spec.missionActive)
    xmlFile:setValue(key .. "#droneFillLevel", spec.droneFillLevel)
    local fillTypeName = g_fillTypeManager:getFillTypeNameByIndex(spec.droneFillType)
    if fillTypeName ~= nil then
        xmlFile:setValue(key .. "#droneFillType", fillTypeName)
    end
    xmlFile:setValue(key .. "#battery", spec.battery)
end

function SprayDroneStation:onDelete()
    local spec = self[SprayDroneStation.SPEC_NAME]
    -- dron létající pod kořenem scény by po smazání vleku zůstal ve světě
    if spec ~= nil and spec.node ~= nil and not spec.isLinked and entityExists(spec.parent) then
        SprayDroneStation.attachDrone(self)
    end
end

function SprayDroneStation:getIsEnterable(superFunc)
    return superFunc(self) and self:getIsUnfolded()
end

function SprayDroneStation:getIsFoldAllowed(superFunc, direction, onAiTurnOn)
    if self.getIsControlled ~= nil and self:getIsControlled() then
        return false, nil
    end
    if not self:getSprayDroneIsParked() then
        -- volá se jen při pokusu o složení; dron se nejdřív vrátí, složit jde až po přistání
        self:sprayDroneCommand(SprayDroneCommandEvent.RETURN_HOME, 0)
        return false, g_i18n:getText("sdt_warning_droneFlying")
    end
    return superFunc(self, direction, onAiTurnOn)
end

function SprayDroneStation:getSprayDroneIsParked()
    local spec = self[SprayDroneStation.SPEC_NAME]
    return spec.state == SprayDroneStation.STATE_PARKED or spec.state == SprayDroneStation.STATE_SERVICING
end

---------------------------------------------------------------------------------------------------
-- parametry a pomocné výpočty

function SprayDroneStation.getHomePosition(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local x, y, z
    if spec.isLinked then
        x, y, z = getWorldTranslation(spec.node)
    else
        x, y, z = localToWorld(spec.parent, spec.localTrans[1], spec.localTrans[2], spec.localTrans[3])
    end
    local terrainY = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
    return x, z, y - terrainY
end

function SprayDroneStation.getSprayType(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local fillType = spec.droneFillType
    if spec.droneFillLevel <= 0 or fillType == FillType.UNKNOWN then
        fillType = self:getFillUnitFillType(spec.fillUnitIndex)
    end
    if fillType == nil or fillType == FillType.UNKNOWN then
        fillType = self:getFillUnitFirstSupportedFillType(spec.fillUnitIndex)
    end
    return g_sprayTypeManager:getSprayTypeByFillTypeIndex(fillType), fillType
end

-- l/m dráhy: vanilla Sprayer:getSprayerUsage počítá litersPerSecond * rychlost [km/h] * záběr za sekundu,
-- tedy na metr dráhy litersPerSecond * 3,6 * záběr
function SprayDroneStation.getLitersPerMeter(self, sprayType)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local lps = sprayType ~= nil and sprayType.litersPerSecond or 0
    return math.max(lps * 3.6 * spec.workWidth * spec.usageScale, 0.0001)
end

function SprayDroneStation.getFlightParams(self, sprayType, restHeight)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return {
        workWidth = spec.workWidth,
        sprayHeight = spec.sprayHeight,
        transitHeight = spec.transitHeight,
        cruiseSpeed = spec.cruiseSpeed,
        sprayingSpeed = spec.sprayingSpeed,
        climbSpeed = spec.climbSpeed,
        litersPerMeter = SprayDroneStation.getLitersPerMeter(self, sprayType),
        batteryReserve = spec.batteryReserve,
        restHeight = restHeight
    }
end

-- Běžící zakázka farmy na poli, pokud na něm dovoluje postřik (jako vanilla Sprayer přes WorkArea:
-- g_missionManager:getIsMissionWorkAllowed s WorkAreaType.SPRAYER).
function SprayDroneStation.getFieldMission(self, field)
    local mission = field.currentMission
    if mission == nil or mission.farmId ~= self:getOwnerFarmId() or mission.getIsWorkAllowed == nil then
        return nil
    end
    return mission
end

-- Může dron pole ošetřit? Vrací povoleno, klíč textu s důvodem a zakázku (u zakázkového pole).
function SprayDroneStation.getFieldAllowed(self, field)
    if field == nil or field:getId() == nil then
        return false, "sdt_warning_noField"
    end
    local farmId = self:getOwnerFarmId()
    local owner = field:getOwner()
    local mission = nil
    if owner == FarmlandManager.NO_OWNER_FARM_ID or not g_currentMission.accessHandler:canFarmAccessOtherId(farmId, owner) then
        mission = SprayDroneStation.getFieldMission(self, field)
        if mission == nil then
            return false, "sdt_warning_notOwned"
        end
        local x, z = field:getCenterOfFieldWorldPosition()
        if not mission:getIsWorkAllowed(farmId, x, z, WorkAreaType.SPRAYER, self) then
            return false, "sdt_warning_missionNoSpray", mission
        end
        local sprayType = SprayDroneStation.getSprayType(self)
        local typeName = mission.getMissionTypeName ~= nil and mission:getMissionTypeName() or nil
        if sprayType ~= nil and ((typeName == "fertilizeMission" and not sprayType.isFertilizer)
            or (typeName == "herbicideMission" and not sprayType.isHerbicide)) then
            return false, "sdt_warning_missionProduct", mission
        end
    end
    local spec = self[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(self)
    if SprayDroneRoute.distanceToPolygon(SprayDroneRoute.getPolygon(field), hx, hz) > spec.range then
        return false, "sdt_warning_outOfRange", mission
    end
    return true, nil, mission
end

-- Smí se na místě postřikovat? Stejná podmínka jako WorkArea:getIsAccessibleAtWorldPosition u vlastního stroje.
function SprayDroneStation.getIsSprayAllowedAt(self, x, z)
    local farmId = self:getOwnerFarmId()
    return g_currentMission.accessHandler:canFarmAccessLand(farmId, x, z)
        or g_missionManager:getIsMissionWorkAllowed(farmId, x, z, WorkAreaType.SPRAYER, self)
end

-- Souhrn naplánované trasy pro plánovač: dávky, plocha, potřebné litry, obsah vleku a dronu.
function SprayDroneStation.getRouteSummary(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local sprayType, fillType = SprayDroneStation.getSprayType(self)
    local length = 0
    for _, leg in ipairs(spec.drawLegs) do
        length = length + MathUtil.vector2Length(leg.x2 - leg.x1, leg.z2 - leg.z1)
    end
    local trailerLiters = self:getFillUnitFillLevel(spec.fillUnitIndex)
    local droneLiters = spec.droneFillType == fillType and spec.droneFillLevel or 0
    local partlyOutOfRange = false
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field ~= nil then
        local hx, hz = SprayDroneStation.getHomePosition(self)
        for _, p in ipairs(SprayDroneRoute.getPolygon(field)) do
            if MathUtil.vector2Length(p.x - hx, p.z - hz) > spec.range then
                partlyOutOfRange = true
                break
            end
        end
    end
    return {
        numBatches = spec.numBatches,
        clipped = spec.routeClipped,
        partlyOutOfRange = partlyOutOfRange,
        areaHa = length * spec.workWidth / 10000,
        liters = length * SprayDroneStation.getLitersPerMeter(self, sprayType),
        availableLiters = trailerLiters + droneLiters,
        trailerLiters = trailerLiters,
        droneLiters = droneLiters,
        fillTypeTitle = g_fillTypeManager:getFillTypeTitleByIndex(fillType) or "-"
    }
end

function SprayDroneStation.buildLegs(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    local sprayType = SprayDroneStation.getSprayType(self)
    if field == nil or sprayType == nil then
        return {}, sprayType
    end
    local hx, hz = SprayDroneStation.getHomePosition(self)
    return SprayDroneRoute.buildLegs(field, hx, hz, spec.range, spec.workWidth, sprayType), sprayType
end

function SprayDroneStation.updateRoutePreview(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.routeDirty = false
    spec.routeTimer = SprayDroneStation.ROUTE_REFRESH_TIME
    spec.drawLegs, spec.numBatches, spec.routeClipped = {}, 0, false
    if spec.fieldId == 0 then
        return
    end
    local legs, sprayType = SprayDroneStation.buildLegs(self)
    if #legs == 0 then
        return
    end
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local p = SprayDroneStation.getFlightParams(self, sprayType, restHeight)
    spec.drawLegs, spec.numBatches, spec.routeClipped = SprayDroneRoute.splitIntoBatches(legs, hx, hz, spec.tankCapacity, spec.batteryCapacity, p)
end

---------------------------------------------------------------------------------------------------
-- příkazy

function SprayDroneStation:sprayDroneCommand(command, fieldId, noEventSend)
    if SprayDroneCommandEvent.sendEvent(self, command, fieldId, noEventSend) then
        return
    end
    local spec = self[SprayDroneStation.SPEC_NAME]

    if command == SprayDroneCommandEvent.SELECT_FIELD then
        if spec.missionActive or not self:getSprayDroneIsParked() then
            return
        end
        local field = SprayDroneRoute.getFieldById(fieldId)
        if field ~= nil and SprayDroneStation.getFieldAllowed(self, field) then
            spec.fieldId = fieldId
            spec.status = SprayDroneStation.STATUS_NONE
            spec.routeDirty = true
            self:raiseDirtyFlags(spec.dirtyFlag)
        end

    elseif command == SprayDroneCommandEvent.START then
        if spec.fieldId == 0 or spec.missionActive or not self:getIsUnfolded() then
            return
        end
        spec.missionActive = true
        spec.status = SprayDroneStation.STATUS_NONE
        if spec.state == SprayDroneStation.STATE_PARKED then
            SprayDroneStation.setState(self, SprayDroneStation.STATE_SERVICING)
            spec.serviceTimer = 500
        end
        self:raiseDirtyFlags(spec.dirtyFlag)

    elseif command == SprayDroneCommandEvent.RETURN_HOME then
        spec.missionActive = false
        if spec.state == SprayDroneStation.STATE_FLYING then
            SprayDroneStation.startReturnHome(self)
        elseif spec.state == SprayDroneStation.STATE_SERVICING then
            SprayDroneStation.setState(self, SprayDroneStation.STATE_PARKED)
        end
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

function SprayDroneStation.setState(self, state)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.state ~= state then
        spec.state = state
        spec.routeDirty = true
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

---------------------------------------------------------------------------------------------------
-- dron: připojení k vleku a let (server)

function SprayDroneStation.detachDrone(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if not spec.isLinked then
        return
    end
    local x, y, z = getWorldTranslation(spec.node)
    local rx, ry, rz = getWorldRotation(spec.node)
    link(getRootNode(), spec.node)
    setWorldTranslation(spec.node, x, y, z)
    setWorldRotation(spec.node, rx, ry, rz)
    spec.isLinked = false
    local dx, _, dz = localDirectionToWorld(spec.node, 0, 0, 1)
    spec.pos.yaw = MathUtil.getYRotationFromDirection(dx, dz)
end

function SprayDroneStation.attachDrone(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.isLinked then
        return
    end
    link(spec.parent, spec.node)
    setTranslation(spec.node, unpack(spec.localTrans))
    setRotation(spec.node, unpack(spec.localRot))
    spec.isLinked = true
end

function SprayDroneStation.setDroneWorldPosition(self, x, y, z, yaw)
    local spec = self[SprayDroneStation.SPEC_NAME]
    setWorldTranslation(spec.node, x, y, z)
    setWorldRotation(spec.node, 0, yaw, 0)
end

function SprayDroneStation.refillDrone(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local trailerFillType = self:getFillUnitFillType(spec.fillUnitIndex)
    local trailerLevel = self:getFillUnitFillLevel(spec.fillUnitIndex)
    if spec.droneFillType ~= trailerFillType and trailerLevel > 0 then
        -- jiný přípravek ve vleku: zbytek v dronu se nemíchá, zahodí se
        spec.droneFillLevel = 0
    end
    if trailerLevel > 0 then
        local amount = math.min(spec.tankCapacity - spec.droneFillLevel, trailerLevel)
        if amount > 0 then
            local applied = -self:addFillUnitFillLevel(self:getOwnerFarmId(), spec.fillUnitIndex, -amount, trailerFillType, ToolType.UNDEFINED, nil)
            spec.droneFillLevel = spec.droneFillLevel + applied
            spec.droneFillType = trailerFillType
        end
    end
    if spec.droneFillLevel <= 0 then
        spec.droneFillType = FillType.UNKNOWN
    end
    spec.battery = spec.batteryCapacity
end

function SprayDroneStation.endMission(self, status)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.missionActive = false
    spec.status = status
    SprayDroneStation.setState(self, SprayDroneStation.STATE_PARKED)
    self:raiseDirtyFlags(spec.dirtyFlag)
end

function SprayDroneStation.startNextBatch(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if not self:getIsUnfolded() or SprayDroneRoute.getFieldById(spec.fieldId) == nil then
        SprayDroneStation.endMission(self, SprayDroneStation.STATUS_ABORTED)
        return
    end
    if not SprayDroneStation.getFieldAllowed(self, SprayDroneRoute.getFieldById(spec.fieldId)) then
        SprayDroneStation.endMission(self, SprayDroneStation.STATUS_NOT_ALLOWED)
        return
    end
    local legs, sprayType = SprayDroneStation.buildLegs(self)
    if #legs == 0 then
        SprayDroneStation.endMission(self, SprayDroneStation.STATUS_FIELD_DONE)
        return
    end
    if spec.droneFillLevel < 0.5 then
        SprayDroneStation.endMission(self, SprayDroneStation.STATUS_TRAILER_EMPTY)
        return
    end
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local p = SprayDroneStation.getFlightParams(self, sprayType, restHeight)
    local wps = SprayDroneRoute.planBatch(legs, 1, 0, hx, hz, spec.droneFillLevel, spec.battery, p)
    if wps == nil then
        SprayDroneStation.endMission(self, SprayDroneStation.STATUS_UNREACHABLE)
        return
    end

    SprayDroneStation.detachDrone(self)
    spec.path = wps
    spec.wpIndex = 1
    spec.pos.x, spec.pos.z, spec.pos.h = hx, hz, restHeight
    spec.sprayFrom = nil
    spec.batch = spec.batch + 1
    spec.litersPerMeter = p.litersPerMeter
    spec.sprayTypeIndex = sprayType.index
    SprayDroneStation.setState(self, SprayDroneStation.STATE_FLYING)
end

function SprayDroneStation.startReturnHome(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    SprayDroneStation.flushSpray(self)
    local _, _, restHeight = SprayDroneStation.getHomePosition(self)
    local h = math.max(spec.pos.h, spec.transitHeight)
    spec.path = {
        { x = spec.pos.x, z = spec.pos.z, h = h, speed = spec.climbSpeed },
        { x = 0, z = 0, h = h, speed = spec.cruiseSpeed, home = true },
        { x = 0, z = 0, h = restHeight, speed = spec.climbSpeed, home = true, land = true }
    }
    spec.wpIndex = 1
    SprayDroneStation.setState(self, SprayDroneStation.STATE_RETURNING)
end

-- Postřik pruhu od posledního bodu k aktuální poloze stejně jako vanilla Sprayer:processSprayerArea.
function SprayDroneStation.flushSpray(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local from = spec.sprayFrom
    spec.sprayFrom = nil
    spec.isSpraying = false
    if from == nil then
        return
    end
    local x, z = spec.pos.x, spec.pos.z
    local len = MathUtil.vector2Length(x - from.x, z - from.z)
    if len < 0.05 or spec.droneFillLevel <= 0 then
        return
    end
    local dirX, dirZ = (x - from.x) / len, (z - from.z) / len
    local halfW = spec.workWidth * 0.5
    local sideX, sideZ = dirZ * halfW, -dirX * halfW
    local sx, sz = from.x + sideX, from.z + sideZ
    local wx, wz = from.x - sideX, from.z - sideZ
    local hx, hz = x + sideX, z + sideZ

    local cx, cz = (from.x + x) * 0.5, (from.z + z) * 0.5
    if not SprayDroneStation.getIsSprayAllowedAt(self, cx, cz) then
        return
    end

    local liters = math.min(len * spec.litersPerMeter, spec.droneFillLevel)
    spec.droneFillLevel = spec.droneFillLevel - liters
    local changedArea = FSDensityMapUtil.updateSprayArea(sx, sz, wx, wz, hx, hz, spec.sprayTypeIndex, 1)

    -- statistiky jako vanilla Sprayer: farmě, které patří ošetřený pozemek (u zakázky nikomu)
    local statsFarmId = g_farmlandManager:getOwnerIdAtWorldPosition(cx, cz)
    local ha = MathUtil.areaToHa(changedArea or 0, g_currentMission:getFruitPixelsToSqm())
    g_farmManager:updateFarmStats(statsFarmId, "sprayedHectares", ha)
    g_farmManager:updateFarmStats(statsFarmId, "sprayUsage", liters)
end

function SprayDroneStation.getReturnTime(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local climb = math.max(spec.transitHeight - spec.pos.h, 0) / spec.climbSpeed
    local descend = math.max(spec.transitHeight - restHeight, 0) / spec.climbSpeed
    return climb + MathUtil.vector2Length(hx - spec.pos.x, hz - spec.pos.z) / spec.cruiseSpeed + descend
end

function SprayDroneStation.updateFlight(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local wp = spec.path ~= nil and spec.path[spec.wpIndex]
    if not wp then
        SprayDroneStation.startReturnHome(self)
        return
    end

    spec.battery = math.max(spec.battery - dt * 0.001, 0)
    if spec.state == SprayDroneStation.STATE_FLYING then
        local trailerMoving = self:getLastSpeed() > SprayDroneStation.MAX_TRAILER_SPEED
        if trailerMoving then
            spec.missionActive = false
        end
        if trailerMoving or spec.droneFillLevel <= 0 or spec.battery < SprayDroneStation.getReturnTime(self) + 5 then
            SprayDroneStation.startReturnHome(self)
            return
        end
    end

    local tx, tz, th = wp.x, wp.z, wp.h
    if wp.home then
        local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
        tx, tz = hx, hz
        if wp.land then
            th = restHeight
        end
    end

    local pos = spec.pos
    local dx, dz, dh = tx - pos.x, tz - pos.z, th - pos.h
    local dist = math.sqrt(dx * dx + dz * dz + dh * dh)
    local step = wp.speed * dt * 0.001
    local reached = step >= dist
    local f = reached and 1 or step / dist
    pos.x, pos.z, pos.h = pos.x + dx * f, pos.z + dz * f, pos.h + dh * f

    local horizontal = math.sqrt(dx * dx + dz * dz)
    if horizontal > 0.5 then
        local targetYaw = MathUtil.getYRotationFromDirection(dx, dz)
        local diff = MathUtil.getAngleDifference(targetYaw, pos.yaw)
        local maxTurn = 2.5 * dt * 0.001
        pos.yaw = pos.yaw + math.clamp(diff, -maxTurn, maxTurn)
    end

    local y = getTerrainHeightAtWorldPos(g_terrainNode, pos.x, 0, pos.z) + pos.h
    SprayDroneStation.setDroneWorldPosition(self, pos.x, y, pos.z, pos.yaw)

    if wp.spray and spec.state == SprayDroneStation.STATE_FLYING then
        spec.isSpraying = true
        if spec.sprayFrom == nil then
            spec.sprayFrom = { x = wp.sx, z = wp.sz }
        end
        if reached or MathUtil.vector2Length(pos.x - spec.sprayFrom.x, pos.z - spec.sprayFrom.z) >= 2 then
            SprayDroneStation.flushSpray(self)
            if not reached then
                spec.sprayFrom = { x = pos.x, z = pos.z }
                spec.isSpraying = true
            end
        end
    end

    if reached then
        spec.wpIndex = spec.wpIndex + 1
        if wp.land then
            SprayDroneStation.attachDrone(self)
            spec.path = nil
            SprayDroneStation.setState(self, SprayDroneStation.STATE_SERVICING)
            spec.serviceTimer = SprayDroneStation.SERVICE_TIME
        end
    end
    self:raiseDirtyFlags(spec.dirtyFlag)
end

function SprayDroneStation:onUpdate(dt, isActiveForInput, isActiveForInputIgnoreSelection, isSelected)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.node == nil then
        return
    end

    if self.isServer then
        if spec.state == SprayDroneStation.STATE_FLYING or spec.state == SprayDroneStation.STATE_RETURNING then
            SprayDroneStation.updateFlight(self, dt)
        elseif spec.state == SprayDroneStation.STATE_SERVICING then
            spec.serviceTimer = spec.serviceTimer - dt
            if spec.serviceTimer <= 0 then
                SprayDroneStation.refillDrone(self)
                if spec.missionActive then
                    SprayDroneStation.startNextBatch(self)
                else
                    SprayDroneStation.setState(self, SprayDroneStation.STATE_PARKED)
                end
                self:raiseDirtyFlags(spec.dirtyFlag)
            end
        end
    else
        SprayDroneStation.updateClientInterpolation(self, dt)
    end

    if spec.state ~= SprayDroneStation.STATE_PARKED then
        self:raiseActive()
    end

    if self.isClient and self:getIsEntered() then
        SprayDroneStation.updatePilotView(self, dt)
    end
end

---------------------------------------------------------------------------------------------------
-- pilot: kruh dosahu, výběr pole, trasa, HUD (jen lokálně u hráče ve vleku)

local function drawTerrainLine(x1, z1, x2, z2, r, g, b, yOffset)
    local len = MathUtil.vector2Length(x2 - x1, z2 - z1)
    local n = math.max(math.ceil(len / 15), 1)
    local px, pz = x1, z1
    local py = getTerrainHeightAtWorldPos(g_terrainNode, px, 0, pz) + yOffset
    for i = 1, n do
        local t = i / n
        local x, z = x1 + (x2 - x1) * t, z1 + (z2 - z1) * t
        local y = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + yOffset
        drawDebugLine(px, py, pz, r, g, b, x, y, z, r, g, b)
        px, py, pz = x, y, z
    end
end

local function drawPolygon(poly, r, g, b, yOffset)
    for i = 1, #poly do
        local a, c = poly[i], poly[i % #poly + 1]
        drawTerrainLine(a.x, a.z, c.x, c.z, r, g, b, yOffset)
    end
end

SprayDroneStation.BATCH_COLORS = {
    { 1, 0.55, 0 }, { 1, 0, 1 }, { 0, 0.6, 1 }, { 1, 1, 0.2 }
}

-- Přepočet náhledu trasy, když se změnilo pole nebo stav, a za letu každých ROUTE_REFRESH_TIME.
-- Volá ho pohled pilota i plánovač; vrací vybrané pole.
function SprayDroneStation.refreshRoutePreview(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    spec.routeTimer = spec.routeTimer - dt
    if spec.routeDirty or (spec.missionActive and spec.routeTimer <= 0) then
        SprayDroneStation.updateRoutePreview(self)
    end
    return field
end

function SprayDroneStation.updatePilotView(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(self)

    -- kruh dosahu jako nízký "plot" (dvě výšky a sloupky), aby byl vidět i na 300 m
    local segments = 90
    for i = 0, segments - 1 do
        local a1, a2 = i / segments * 2 * math.pi, (i + 1) / segments * 2 * math.pi
        local x1, z1 = hx + math.cos(a1) * spec.range, hz + math.sin(a1) * spec.range
        local x2, z2 = hx + math.cos(a2) * spec.range, hz + math.sin(a2) * spec.range
        drawTerrainLine(x1, z1, x2, z2, 0, 1, 1, 0.5)
        drawTerrainLine(x1, z1, x2, z2, 0, 1, 1, 4)
        local y = getTerrainHeightAtWorldPos(g_terrainNode, x1, 0, z1)
        drawDebugLine(x1, y, z1, 0, 1, 1, x1, y + 4, z1, 0, 1, 1)
    end

    local field = SprayDroneStation.refreshRoutePreview(self, dt)
    if field ~= nil then
        drawPolygon(SprayDroneRoute.getPolygon(field), 0, 1, 0, 0.6)
        drawPolygon(SprayDroneRoute.getPolygon(field), 0, 1, 0, 1.5)
        for _, leg in ipairs(spec.drawLegs) do
            local c = SprayDroneStation.BATCH_COLORS[(leg.batch - 1) % #SprayDroneStation.BATCH_COLORS + 1]
            drawTerrainLine(leg.x1, leg.z1, leg.x2, leg.z2, c[1], c[2], c[3], 0.3)
        end
    end

    SprayDroneStation.updateActionEventStates(self)
    SprayDroneStation.drawHudTexts(self, field)
end

function SprayDroneStation.drawHudTexts(self, field)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local mission = g_currentMission
    local fieldText = field ~= nil and field:getName() or g_i18n:getText("sdt_hud_noField")
    mission:addExtraPrintText(string.format(g_i18n:getText("sdt_hud_field"), fieldText))
    if field ~= nil then
        mission:addExtraPrintText(string.format(g_i18n:getText("sdt_hud_route"), spec.numBatches))
    end
    mission:addExtraPrintText(SprayDroneStation.getDroneStateText(self))
    local statusText = SprayDroneStation.STATUS_TEXTS[spec.status]
    if statusText ~= nil then
        mission:addExtraPrintText(g_i18n:getText(statusText))
    end
end

function SprayDroneStation.getDroneStateText(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return string.format(g_i18n:getText("sdt_hud_drone"), g_i18n:getText(SprayDroneStation.STATE_TEXTS[spec.state]),
        spec.droneFillLevel, spec.tankCapacity, spec.battery / spec.batteryCapacity * 100)
end

function SprayDroneStation:onRegisterActionEvents(isActiveForInput, isActiveForInputIgnoreSelection)
    if not self.isClient then
        return
    end
    local spec = self[SprayDroneStation.SPEC_NAME]
    self:clearActionEventsTable(spec.actionEvents)
    if isActiveForInputIgnoreSelection and self:getIsEntered() then
        local actions = {
            { InputAction.SDT_OPEN_PLANNER, SprayDroneStation.actionEventOpenPlanner },
            { InputAction.SDT_START_FLIGHT, SprayDroneStation.actionEventStart },
            { InputAction.SDT_RETURN_HOME, SprayDroneStation.actionEventReturnHome }
        }
        for _, a in ipairs(actions) do
            local _, actionEventId = self:addActionEvent(spec.actionEvents, a[1], self, a[2], false, true, false, true, nil)
            g_inputBinding:setActionEventTextPriority(actionEventId, GS_PRIO_VERY_HIGH)
        end
        SprayDroneStation.updateActionEventStates(self)
    end
end

function SprayDroneStation.updateActionEventStates(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local parked = self:getSprayDroneIsParked()
    local function setActive(action, active)
        local event = spec.actionEvents[action]
        if event ~= nil then
            g_inputBinding:setActionEventActive(event.actionEventId, active)
        end
    end
    setActive(InputAction.SDT_START_FLIGHT, SprayDroneStation.getCanStart(self))
    setActive(InputAction.SDT_RETURN_HOME, SprayDroneStation.getCanReturnHome(self))
end

function SprayDroneStation.getCanSelectField(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return self:getSprayDroneIsParked() and not spec.missionActive
end

function SprayDroneStation.getCanStart(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return spec.fieldId ~= 0 and not spec.missionActive
end

function SprayDroneStation.getCanReturnHome(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return spec.missionActive or not self:getSprayDroneIsParked()
end

-- Výběr pole z plánovače; vrací klíč textu s důvodem, když pole nejde vybrat.
function SprayDroneStation.selectField(self, field)
    if not SprayDroneStation.getCanSelectField(self) then
        return "sdt_warning_missionRunning"
    end
    local allowed, warning = SprayDroneStation.getFieldAllowed(self, field)
    if not allowed then
        return warning
    end
    self:sprayDroneCommand(SprayDroneCommandEvent.SELECT_FIELD, field:getId())
    return nil
end

-- Start letu; vrací klíč textu s důvodem, když start nejde.
function SprayDroneStation.startFlight(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.fieldId == 0 then
        return "sdt_warning_noFieldSelected"
    end
    if spec.missionActive then
        return nil
    end
    if spec.numBatches == 0 then
        return "sdt_status_fieldDone"
    end
    self:sprayDroneCommand(SprayDroneCommandEvent.START, spec.fieldId)
    return nil
end

function SprayDroneStation.actionEventOpenPlanner(self, actionName, inputValue, callbackState, isAnalog)
    SprayDronePlannerScreen.show(self)
end

function SprayDroneStation.actionEventStart(self, actionName, inputValue, callbackState, isAnalog)
    local warning = SprayDroneStation.startFlight(self)
    if warning ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(warning), 2500)
    end
end

function SprayDroneStation.actionEventReturnHome(self, actionName, inputValue, callbackState, isAnalog)
    self:sprayDroneCommand(SprayDroneCommandEvent.RETURN_HOME, 0)
end

---------------------------------------------------------------------------------------------------
-- síť

local function writeState(self, streamId)
    local spec = self[SprayDroneStation.SPEC_NAME]
    streamWriteUIntN(streamId, spec.state, SprayDroneStation.STATE_NUM_BITS)
    streamWriteUIntN(streamId, spec.status, SprayDroneStation.STATUS_NUM_BITS)
    streamWriteUInt16(streamId, spec.fieldId)
    streamWriteBool(streamId, spec.missionActive)
    streamWriteFloat32(streamId, spec.droneFillLevel)
    streamWriteFloat32(streamId, spec.battery)
    if streamWriteBool(streamId, not spec.isLinked) then
        local x, y, z = getWorldTranslation(spec.node)
        streamWriteFloat32(streamId, x)
        streamWriteFloat32(streamId, y)
        streamWriteFloat32(streamId, z)
        streamWriteFloat32(streamId, spec.pos.yaw)
    end
end

local function readState(self, streamId, snap)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local state = streamReadUIntN(streamId, SprayDroneStation.STATE_NUM_BITS)
    spec.status = streamReadUIntN(streamId, SprayDroneStation.STATUS_NUM_BITS)
    local fieldId = streamReadUInt16(streamId)
    spec.missionActive = streamReadBool(streamId)
    spec.droneFillLevel = streamReadFloat32(streamId)
    spec.battery = streamReadFloat32(streamId)
    if fieldId ~= spec.fieldId or state ~= spec.state then
        spec.routeDirty = true
    end
    spec.fieldId = fieldId
    spec.state = state
    if streamReadBool(streamId) then
        local x, y, z = streamReadFloat32(streamId), streamReadFloat32(streamId), streamReadFloat32(streamId)
        local yaw = streamReadFloat32(streamId)
        if spec.isLinked then
            SprayDroneStation.detachDrone(self)
            snap = true
        end
        spec.netTarget = { x = x, y = y, z = z, yaw = yaw }
        if snap then
            SprayDroneStation.setDroneWorldPosition(self, x, y, z, yaw)
        end
    else
        spec.netTarget = nil
        SprayDroneStation.attachDrone(self)
    end
end

function SprayDroneStation.updateClientInterpolation(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local target = spec.netTarget
    if target == nil or spec.isLinked then
        return
    end
    local x, y, z = getWorldTranslation(spec.node)
    local f = math.min(dt * 0.012, 1)
    local dx, _, dz = localDirectionToWorld(spec.node, 0, 0, 1)
    local yaw = MathUtil.getYRotationFromDirection(dx, dz)
    yaw = yaw + MathUtil.getAngleDifference(target.yaw, yaw) * f
    SprayDroneStation.setDroneWorldPosition(self, x + (target.x - x) * f, y + (target.y - y) * f, z + (target.z - z) * f, yaw)
    spec.pos.yaw = yaw
end

function SprayDroneStation:onWriteStream(streamId, connection)
    writeState(self, streamId)
end

function SprayDroneStation:onReadStream(streamId, connection)
    readState(self, streamId, true)
end

function SprayDroneStation:onWriteUpdateStream(streamId, connection, dirtyMask)
    if not connection:getIsServer() then
        local spec = self[SprayDroneStation.SPEC_NAME]
        if streamWriteBool(streamId, bit32.band(dirtyMask, spec.dirtyFlag) ~= 0) then
            writeState(self, streamId)
        end
    end
end

function SprayDroneStation:onReadUpdateStream(streamId, timestamp, connection)
    if connection:getIsServer() then
        if streamReadBool(streamId) then
            readState(self, streamId, false)
        end
    end
end
