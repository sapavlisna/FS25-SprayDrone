-- Přenosná motorová pumpa na vodu (objects/pump/waterPump.xml, vehicle type sdtWaterPump = pallet + tahle specializace + SprayDroneWaterHose): naftový
-- motor žene odstředivé čerpadlo se dvěma popsanými spojkami a dvěma tažnými hadicemi (SprayDroneWaterHose): VSTUP a VÝSTUP (na vodní ventil velkého vleku).
-- Vstup má dva režimy, které hráč přepíná ručně (levé tlačítko myši u vstupní spojky, SprayDronePump.toggleMode): "nádrž" (konec hadice je spojka Storz, napojí se
-- na IBC / cisternu) a "rybník" (konec hadice je sací koš, položí se na dno pod hladinou). Za chodu motoru plní hadice vstupu těleso pumpy (fill unit 2, 200 l)
-- a výstupní hadice z něj plní nádrž vleku. Motor zapíná hráč akcí SDT_TOGGLE_FOOT (B) u pumpy; spotřebovává naftu (fill unit 1), kterou se nalévá z kanystru
-- stejně jako u mlýnku (SprayDroneMill.updatePour). Z pumpy jde vodu brát jen její výstupní hadicí a jen za chodu motoru.
--
-- Stav (motor, čerpá se, režim vstupu) rozhoduje server a jde klientům ve stavu vozidla (dirty flag); příkazy jdou eventem. Režim vstupu se ukládá do savegame.
--
-- Stejný motor má i násypka na jemné vápno (objects/hopper/limeHopper.xml, SprayDroneHopper): v XML se liší popisky (text*), logName, dryWarning a storable
-- (násypku nejde uložit do držáku pumpy na vleku).

source(g_currentModDirectory .. "scripts/events/SprayDronePumpEvent.lua")

SprayDronePump = {}
SprayDronePump.MOD_NAME = g_currentModName
SprayDronePump.SPEC_NAME = string.format("spec_%s.sprayDronePump", g_currentModName)

SprayDronePump.CMD_ENGINE_ON = 1
SprayDronePump.CMD_ENGINE_OFF = 2
SprayDronePump.CMD_MODE_TOGGLE = 3
SprayDronePump.CMD_BITS = 2

SprayDronePump.MIN_LITERS = 0.001
SprayDronePump.CONTROL_DISTANCE = 2.8      -- hráč nejvýš tak daleko od motoru, aby ho mohl zapnout / vypnout (m)
SprayDronePump.DRY_WARNING_MS = 1500       -- tak dlouho po startu bez vody se hráči ukáže varování
SprayDronePump.WAKE_DISTANCE = 20          -- hráč nejvýš tak blízko, aby se stojící pumpa / násypka držela vzhůru (m)
SprayDronePump.instances = {}
SprayDronePump.FLOW_MS = 400               -- tak dlouho po posledním přelití zůstává stav „čerpá se“ (zvuk toku)

local function getSpec(self)
    return self[SprayDronePump.SPEC_NAME]
end

function SprayDronePump.prerequisitesPresent(specializations)
    return SpecializationUtil.hasSpecialization(FillUnit, specializations)
end

function SprayDronePump.initSpecialization()
    local schema = Vehicle.xmlSchema
    schema:setXMLSpecializationType("SprayDronePump")
    local key = "vehicle.sprayDronePump"
    schema:register(XMLValueType.INT, key .. "#dieselFillUnitIndex", "Nafta pro motor", 1)
    schema:register(XMLValueType.INT, key .. "#waterFillUnitIndex", "Voda v tělese čerpadla", 2)
    schema:register(XMLValueType.FLOAT, key .. "#dieselPerHour", "Spotřeba motoru za chodu (l/h)", 3)
    schema:register(XMLValueType.FLOAT, key .. "#minDepth", "Nejmenší hloubka vody pod sacím košem v rybníku (m)", 0.15)
    schema:register(XMLValueType.FLOAT, key .. "#pourRadius", "Víčko kanystru nafty nejvýš tak daleko od hrdla (m)", 0.3)
    schema:register(XMLValueType.FLOAT, key .. "#pourRate", "Nalévání z kanystru (l/s)", 4)
    schema:register(XMLValueType.BOOL, key .. "#storable", "Jde uložit do držáku pumpy na vleku", true)
    schema:register(XMLValueType.BOOL, key .. "#dryWarning", "Varování, když motor běží a nic neteče", true)
    schema:register(XMLValueType.STRING, key .. "#logName", "Jméno v záznamu akcí", "pumpa")
    schema:register(XMLValueType.STRING, key .. "#textStart", "Popisek zapnutí motoru (l10n)", "sdt_pump_start")
    schema:register(XMLValueType.STRING, key .. "#textStop", "Popisek vypnutí motoru (l10n)", "sdt_pump_stop")
    schema:register(XMLValueType.STRING, key .. "#textNoFuel", "Hláška bez nafty (l10n)", "sdt_pump_noFuel")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#engine", "Střed motoru (ovládání, zvuk)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#dieselNeck", "Hrdlo nádrže nafty")
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "engine")
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "flow")
    schema:setXMLSpecializationType()

    Vehicle.xmlSchemaSavegame:register(XMLValueType.BOOL, string.format("vehicles.vehicle(?).%s.sprayDronePump#pondMode", SprayDronePump.MOD_NAME),
        "Vstup pumpy je v režimu rybník (sací koš)")
end

function SprayDronePump.registerFunctions(vehicleType)
    SpecializationUtil.registerFunction(vehicleType, "sprayDronePumpCommand", SprayDronePump.command)
end

function SprayDronePump.registerEventListeners(vehicleType)
    for _, name in ipairs({ "onLoad", "onDelete", "onUpdate", "onReadStream", "onWriteStream", "onReadUpdateStream", "onWriteUpdateStream" }) do
        SpecializationUtil.registerEventListener(vehicleType, name, SprayDronePump)
    end
end

function SprayDronePump:onLoad(savegame)
    local spec = getSpec(self)
    local xml = self.xmlFile
    local key = "vehicle.sprayDronePump"
    spec.dieselUnit = xml:getValue(key .. "#dieselFillUnitIndex", 1)
    spec.waterUnit = xml:getValue(key .. "#waterFillUnitIndex", 2)
    spec.dieselPerSecond = math.max(xml:getValue(key .. "#dieselPerHour", 3), 0) / 3600
    spec.minDepth = math.max(xml:getValue(key .. "#minDepth", 0.15), 0)
    spec.pourRadius = math.max(xml:getValue(key .. "#pourRadius", 0.3), 0.05)
    spec.pourRate = math.max(xml:getValue(key .. "#pourRate", 4), 0.1)
    spec.storable = xml:getValue(key .. "#storable", true)
    spec.dryWarning = xml:getValue(key .. "#dryWarning", true)
    spec.logName = xml:getValue(key .. "#logName", "pumpa")
    spec.textStart = xml:getValue(key .. "#textStart", "sdt_pump_start")
    spec.textStop = xml:getValue(key .. "#textStop", "sdt_pump_stop")
    spec.textNoFuel = xml:getValue(key .. "#textNoFuel", "sdt_pump_noFuel")
    spec.engineNode = xml:getValue(key .. ".nodes#engine", nil, self.components, self.i3dMappings)
    spec.dieselNeck = xml:getValue(key .. ".nodes#dieselNeck", nil, self.components, self.i3dMappings)
    spec.engineOn = false
    spec.pondMode = false
    spec.flowing = false
    spec.flowUntil = 0
    spec.engineTime = 0
    spec.dryWarned = false
    spec.pourTimer = 0
    spec.pourAcc = 0
    spec.dirtyFlag = self:getNextDirtyFlag()
    SprayDronePump.instances[self] = true

    if savegame ~= nil and not savegame.resetVehicles and self.isServer then
        spec.pondMode = savegame.xmlFile:getValue(string.format("%s.%s.sprayDronePump#pondMode", savegame.key, SprayDronePump.MOD_NAME), false)
    end

    if self.isClient then
        spec.samples = {}
        for _, name in ipairs({ "engine", "flow" }) do
            if xml:hasProperty(key .. ".sounds." .. name) then
                spec.samples[name] = g_soundManager:loadSampleFromXML(xml, key .. ".sounds", name, self.baseDirectory, self.components, 0,
                    AudioGroup.VEHICLE, self.i3dMappings, self)
            end
        end
        spec.soundState = {}
        if g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
            spec.engineActivatable = SprayDronePumpEngineActivatable.new(self)
            g_currentMission.activatableObjectsSystem:addActivatable(spec.engineActivatable)
        end
    end
end

function SprayDronePump:onDelete()
    SprayDronePump.instances[self] = nil
    local spec = getSpec(self)
    if spec == nil then
        return
    end
    if spec.engineActivatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(spec.engineActivatable)
    end
    spec.engineActivatable = nil
    if spec.samples ~= nil then
        for _, sample in pairs(spec.samples) do
            g_soundManager:deleteSample(sample)
        end
        spec.samples = nil
    end
end

---------------------------------------------------------------------------------------------------
-- síť

local function writeState(self, streamId)
    local spec = getSpec(self)
    streamWriteBool(streamId, spec.engineOn)
    streamWriteBool(streamId, spec.flowing)
    streamWriteBool(streamId, spec.pondMode)
end

local function readState(self, streamId)
    local spec = getSpec(self)
    local wasOn = spec.engineOn
    spec.engineOn = streamReadBool(streamId)
    spec.flowing = streamReadBool(streamId)
    spec.pondMode = streamReadBool(streamId)
    if spec.engineOn and not wasOn then
        spec.engineTime, spec.dryWarned = 0, false
    end
    self:raiseActive()
end

function SprayDronePump:onWriteStream(streamId, connection)
    writeState(self, streamId)
end

function SprayDronePump:onReadStream(streamId, connection)
    readState(self, streamId)
end

function SprayDronePump:onWriteUpdateStream(streamId, connection, dirtyMask)
    if not connection:getIsServer() then
        local spec = getSpec(self)
        if streamWriteBool(streamId, bit32.band(dirtyMask, spec.dirtyFlag) ~= 0) then
            writeState(self, streamId)
        end
    end
end

function SprayDronePump:onReadUpdateStream(streamId, timestamp, connection)
    if connection:getIsServer() and streamReadBool(streamId) then
        readState(self, streamId)
    end
end

function SprayDronePump:saveToXMLFile(xmlFile, key, usedModNames)
    if getSpec(self).pondMode then
        xmlFile:setValue(key .. "#pondMode", true)
    end
end

---------------------------------------------------------------------------------------------------
-- příkazy (server) a rozhraní pro vodní hadici vleku

function SprayDronePump.isConnectionAllowed(self, connection)
    return SprayDroneStation.isConnectionAllowed(self, connection)
end

-- Důvod (klíč textu), proč motor nejde zapnout; nil = jde.
function SprayDronePump.getEngineBlocker(self)
    local spec = getSpec(self)
    if self:getFillUnitFillLevel(spec.dieselUnit) <= 0.01 then
        return spec.textNoFuel
    end
    return nil
end

-- Důvod (klíč textu), proč nejde přepnout režim vstupu; nil = jde. Přepnout jde se stojícím motorem a bez sací hadice napojené ke zdroji (nesená nebo
-- odložená hadice nevadí).
function SprayDronePump.getModeBlocker(self)
    if getSpec(self).engineOn then
        return "sdt_pump_modeEngineOn"
    end
    local hoses = self[SprayDroneWaterHose.SPEC_NAME]
    local inlet = hoses ~= nil and hoses.hoses[1] or nil
    if inlet ~= nil and inlet.out and not inlet.held then
        return "sdt_pump_modeHoseAttached"
    end
    return nil
end

-- Pumpa čerpá (motor běží): jen z ní jde brát vodu vodní hadicí vleku.
function SprayDronePump.isRunning(self)
    local spec = getSpec(self)
    return spec ~= nil and spec.engineOn
end

-- Server: hadice právě přelila vodu (zvuk toku na všech klientech).
function SprayDronePump.markFlow(self)
    getSpec(self).flowUntil = g_time + SprayDronePump.FLOW_MS
end

function SprayDronePump.command(self, command, noEventSend)
    if SprayDronePumpEvent.sendEvent(self, command, noEventSend) then
        return
    end
    local spec = getSpec(self)
    if command == SprayDronePump.CMD_ENGINE_ON then
        SprayDroneSound.noteAction(string.format("%s id %s: zapnutí motoru", spec.logName, tostring(self.id)))
        if not spec.engineOn and SprayDronePump.getEngineBlocker(self) == nil then
            spec.engineOn = true
            spec.engineTime, spec.dryWarned = 0, false
            self:raiseDirtyFlags(spec.dirtyFlag)
            self:raiseActive()
        end
    elseif command == SprayDronePump.CMD_ENGINE_OFF then
        SprayDroneSound.noteAction(string.format("%s id %s: vypnutí motoru", spec.logName, tostring(self.id)))
        if spec.engineOn then
            spec.engineOn, spec.flowing = false, false
            self:raiseDirtyFlags(spec.dirtyFlag)
        end
    elseif command == SprayDronePump.CMD_MODE_TOGGLE then
        local blocker = SprayDronePump.getModeBlocker(self)
        if blocker ~= nil then
            SprayDroneSound.noteAction(string.format("%s id %s: přepnutí vstupu odmítnuto (%s)", spec.logName, tostring(self.id), blocker))
            return
        end
        spec.pondMode = not spec.pondMode
        SprayDroneSound.noteAction(string.format("%s id %s: vstup přepnut na %s", spec.logName, tostring(self.id), spec.pondMode and "rybník (sací koš)" or "nádrž (Storz)"))
        local hoses = self[SprayDroneWaterHose.SPEC_NAME]
        if hoses ~= nil and hoses.hoses[1] ~= nil and hoses.hoses[1].out then
            self:sprayDroneWaterHoseCommand(SprayDroneWaterHose.CMD_DROP, nil, nil, true, nil, nil, nil, nil, nil, nil, 1)
        end
        self:raiseDirtyFlags(spec.dirtyFlag)
        self:raiseActive()
    end
end

---------------------------------------------------------------------------------------------------
-- chod (server): spotřeba nafty, stav „čerpá se“, nalévání nafty z kanystru (vodu přelévají hadice, SprayDroneWaterHose)

function SprayDronePump.updateServer(self, dt)
    local spec = getSpec(self)
    if spec.engineOn then
        self:raiseActive()
        local diesel = self:getFillUnitFillLevel(spec.dieselUnit)
        if diesel <= 0.001 then
            spec.engineOn, spec.flowing = false, false
            self:raiseDirtyFlags(spec.dirtyFlag)
        else
            local seconds = dt * 0.001
            self:addFillUnitFillLevel(self:getOwnerFarmId(), spec.dieselUnit, -math.min(spec.dieselPerSecond * seconds, diesel), FillType.DIESEL,
                ToolType.UNDEFINED, nil)
        end
    end
    local flowing = spec.engineOn and g_time < spec.flowUntil
    if flowing ~= spec.flowing then
        spec.flowing = flowing
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
    SprayDroneMill.updatePour(self, dt, spec)
end

---------------------------------------------------------------------------------------------------
-- zvuk a varování (klient i server)

local function setSample(self, spec, name, playing)
    local sample = spec.samples ~= nil and spec.samples[name] or nil
    if sample == nil or spec.soundState[name] == playing then
        return
    end
    spec.soundState[name] = playing
    local reason = string.format("%s: engineOn=%s flowing=%s", spec.logName, tostring(spec.engineOn), tostring(spec.flowing))
    if playing then
        SprayDroneSound.play(self, sample, reason)
    else
        SprayDroneSound.stop(self, sample, reason)
    end
end

local function getPlayerPosition()
    local player = g_localPlayer
    if player == nil then
        return nil
    end
    local vehicle = player.getCurrentVehicle ~= nil and player:getCurrentVehicle() or nil
    if vehicle ~= nil then
        return nil
    end
    if player.getPosition ~= nil then
        local x, y, z = player:getPosition()
        return x, y, z
    end
    return nil
end

local function distanceTo(x, y, z, node)
    if node == nil or not entityExists(node) then
        return math.huge
    end
    local nx, ny, nz = getWorldTranslation(node)
    return MathUtil.vector3Length(x - nx, y - ny, z - nz)
end

function SprayDronePump:onUpdate(dt)
    local spec = getSpec(self)
    if self.isServer then
        SprayDronePump.updateServer(self, dt)
    end
    if self.isClient then
        setSample(self, spec, "engine", spec.engineOn)
        setSample(self, spec, "flow", spec.engineOn and spec.flowing)
        if spec.dryWarning and spec.engineOn and not spec.flowing and not spec.dryWarned then
            spec.engineTime = spec.engineTime + dt
            if spec.engineTime >= SprayDronePump.DRY_WARNING_MS then
                spec.dryWarned = true
                local px, py, pz = getPlayerPosition()
                if px ~= nil and distanceTo(px, py, pz, spec.engineNode) <= SprayDronePump.CONTROL_DISTANCE * 3 then
                    g_currentMission:showBlinkingWarning(g_i18n:getText("sdt_pump_dry"), 3000)
                end
            end
        end
    end
    if spec.engineOn then
        self:raiseActive()
    end
end

---------------------------------------------------------------------------------------------------
-- ovládání: motor akcí B u pumpy

local function isUsable(vehicle)
    if vehicle == nil or vehicle.isDeleted or g_localPlayer == nil then
        return false
    end
    if VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG then
        return false
    end
    return g_currentMission.accessHandler:canFarmAccess(g_localPlayer.farmId, vehicle)
end

function SprayDronePump.toggleEngine(self)
    local spec = getSpec(self)
    if spec.engineOn then
        self:sprayDronePumpCommand(SprayDronePump.CMD_ENGINE_OFF)
        return
    end
    local blocker = SprayDronePump.getEngineBlocker(self)
    if blocker ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(blocker), 2500)
        return
    end
    self:sprayDronePumpCommand(SprayDronePump.CMD_ENGINE_ON)
end

-- Přepnutí režimu vstupu z ovládání hráče (klient): levé tlačítko myši u vstupní spojky (SprayDroneWaterHoseActivatable); blokující důvod se ukáže hláškou.
function SprayDronePump.toggleMode(self)
    local blocker = SprayDronePump.getModeBlocker(self)
    if blocker ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(blocker), 2500)
        return
    end
    self:sprayDronePumpCommand(SprayDronePump.CMD_MODE_TOGGLE)
end

function SprayDronePump.getModeText(self)
    return g_i18n:getText(getSpec(self).pondMode and "sdt_pump_modeToTank" or "sdt_pump_modeToPond")
end

SprayDronePumpEngineActivatable = {}
local SprayDronePumpEngineActivatable_mt = Class(SprayDronePumpEngineActivatable)

function SprayDronePumpEngineActivatable.new(vehicle)
    local self = setmetatable({}, SprayDronePumpEngineActivatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText(getSpec(vehicle).textStart)
    return self
end

function SprayDronePumpEngineActivatable:getIsActivatable()
    local vehicle = self.vehicle
    local spec = getSpec(vehicle)
    local px, py, pz = getPlayerPosition()
    if px == nil or not isUsable(vehicle) or distanceTo(px, py, pz, spec.engineNode) > SprayDronePump.CONTROL_DISTANCE then
        return false
    end
    self.activateText = g_i18n:getText(spec.engineOn and spec.textStop or spec.textStart)
    if self.toggleEventId ~= nil then
        g_inputBinding:setActionEventText(self.toggleEventId, self.activateText)
        g_inputBinding:setActionEventTextVisibility(self.toggleEventId, SprayDroneLink.mayToggle(self))
    end
    return true
end

function SprayDronePumpEngineActivatable:getDistance(x, y, z)
    local node = getSpec(self.vehicle).engineNode
    return SprayDroneLink.aimDistance(distanceTo(x, y, z, node), node)
end

function SprayDronePumpEngineActivatable:registerCustomInput(inputContext)
    self.toggleEventId = SprayDroneLink.registerToggle(self, self.run, self.activateText)
    SprayDroneLink.setSelected(self, true)
end

function SprayDronePumpEngineActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    SprayDroneLink.setSelected(self, false)
    self.toggleEventId = nil
end

function SprayDronePumpEngineActivatable:run()
    if SprayDroneLink.mayToggle(self) then
        SprayDronePump.toggleEngine(self.vehicle)
    end
end

function SprayDronePumpEngineActivatable:activate() end

function SprayDronePumpEngineActivatable:deactivate() end

---------------------------------------------------------------------------------------------------
-- Stojící předmět s uspanou fyzikou přestane volat onUpdate; pumpa a násypka ale musí přijímat nalévání z kanystru / pytle (SprayDroneMill.updatePour),
-- proto je server drží vzhůru, dokud je poblíž hráč.

SprayDronePumpWake = {}

function SprayDronePumpWake:update(dt)
    if g_server == nil or g_currentMission == nil or g_currentMission.playerSystem == nil or next(SprayDronePump.instances) == nil then
        return
    end
    for vehicle in pairs(SprayDronePump.instances) do
        if not vehicle.isDeleted and vehicle.rootNode ~= nil and entityExists(vehicle.rootNode) then
            local vx, vy, vz = getWorldTranslation(vehicle.rootNode)
            for _, player in pairs(g_currentMission.playerSystem.players) do
                if player.getPosition ~= nil then
                    local px, py, pz = player:getPosition()
                    if px ~= nil and MathUtil.vector3Length(px - vx, py - vy, pz - vz) <= SprayDronePump.WAKE_DISTANCE then
                        vehicle:raiseActive()
                        break
                    end
                end
            end
        end
    end
end

addModEventListener(SprayDronePumpWake)
