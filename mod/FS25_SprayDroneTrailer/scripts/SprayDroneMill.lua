-- Mlýnkový vozík na vápno (vehicles/sdtLimeMill): dieselový kladivový mlýn mele klasické vápno (vanilla LIME) z velké nádoby na
-- jemně mleté vápno (SDT_FINE_LIME). Jemné vápno z vozíku odčerpá pumpa velkého vleku (Max, Middle) sací hadicí napojenou na výstup
-- mlýnku (spojka Storz u cyklónu, uzel outlet) do nádobky na koncentrát (SprayDroneWaterHose); mlýn při tom musí běžet.
--
-- Fill units vozíku: 1 hrubé vápno (exactFillRootNode: do nádoby se vyklopí vanilla návěs / big bag), 2 nafta pro motor,
-- 3 jemné vápno (mezisklad pod cyklónem). Do vozíku se nastupuje jako do velkého vleku (enterable), motor zapíná a vypíná akce
-- IMPLEMENT_EXTRA (B) ve vozíku, pěšky levé tlačítko myši nebo B u velkého tlačítka na rozvaděči (uzel button); prstenec kolem tlačítka
-- (uzel ring, materiál staticLight_vertex) svítí zeleně, dokud motor běží. Za chodu motoru mlýn přesouvá vápno 1 -> 3 rychlostí millRate
-- a spotřebovává naftu.
--
-- Stav (motor, mletí, čerpání) rozhoduje server a jde klientům ve stavu vozidla (dirty flag); příkazy jdou eventem.
--
-- Výstup jemného vápna jde přes klapkový rozdělovač (ventil) pod nádobkou: hadice (spojka Storz, jemné vápno odčerpá pumpa vleku, viz výš) nebo výsypná
-- roura (docs/NAVRH-mlyn-plneni-bigbagu.md). Ventil přepíná páka (pěšky levé tlačítko na páku, ve vozíku IMPLEMENT_EXTRA3 = Y); jde přepnout i s připojenou
-- hadicí, hadice pak nedostane nic (nápověda to řekne). Roura se otáčí kolem svislé osy kloubu v pravém zadním rohu (animace spoutSwing, ne vanilla Pipe):
-- přeprava (čas 0) -> vedle vozíku (0,5) -> za vozíkem (1) -> přeprava, ve vozíku TOGGLE_PIPE = O, pěšky levé tlačítko na kloub. Do vaku se sype rychlostí
-- hoseRate, když běží motor, ventil je na rouře, roura stojí vyklopená a vozík stojí (getFlowTarget). Vak (objects/limeBigBag/limeBigBag.xml, vanilla bigBag
-- s druhem SDT_FINE_LIME) stojí u plnicí hlavy: hlava je z boku vaku na straně k vozíku (ústí vodorovně do horní části boku), střed vaku je o neckOffset dál
-- od kloubu (<bagOutput head pivot neckOffset halfWidth depth>), takže nic z roury nesahá nad vak a plný vak jde zvednout a odvézt; server ho hledá každých
-- BAG_SEARCH_MS a když tam žádný nestojí (ani plný), postaví nový prázdný na zem, hloubkou podél ramene.
--
-- Za mletí se z mlýnku práší (jen vizuál na klientech, effects/millDust.i3d): lehký prach u výsypky šneku a pod plnicí hlavou, když se do vaku sype;
-- hrdlo vaku pod hlavou (uzel neck) je vidět jen za sypání. Řídí je synchronizovaný stav (spec.milling, spec.pumping, spec.valveSpout, spec.spoutState).

source(g_currentModDirectory .. "scripts/events/SprayDroneMillEvent.lua")

SprayDroneMill = {}
SprayDroneMill.MOD_NAME = g_currentModName
SprayDroneMill.MOD_DIR = g_currentModDirectory
SprayDroneMill.SPEC_NAME = string.format("spec_%s.sprayDroneMill", g_currentModName)

SprayDroneMill.CMD_ENGINE_ON = 1
SprayDroneMill.CMD_ENGINE_OFF = 2
SprayDroneMill.CMD_VALVE_TOGGLE = 3
SprayDroneMill.CMD_SPOUT_TRANSPORT = 4     -- CMD_SPOUT_TRANSPORT + stav - 1: roura do stavu 1, 2, 3
SprayDroneMill.CMD_BITS = 3

SprayDroneMill.SPOUT_TRANSPORT = 1
SprayDroneMill.SPOUT_SIDE = 2
SprayDroneMill.SPOUT_REAR = 3
SprayDroneMill.SPOUT_TIMES = { 0, 0.5, 1 }  -- čas animace spoutSwing pro stavy roury
SprayDroneMill.SPOUT_ANIM = "spoutSwing"
SprayDroneMill.VALVE_ANIM = "valveLever"
SprayDroneMill.SPOUT_TEXTS = { "sdt_mill_spoutSide", "sdt_mill_spoutRear", "sdt_mill_spoutFold" }
SprayDroneMill.MAX_FILL_SPEED = 1         -- do vaku se sype jen pod touto rychlostí vozíku (km/h)

SprayDroneMill.MIN_LITERS = 0.001
SprayDroneMill.CONTROL_DISTANCE = 3.2      -- hráč nejvýš tak daleko od motoru, aby ho mohl zapnout z chůze (m)
SprayDroneMill.POUR_INTERVAL_MS = 100
SprayDroneMill.POUR_UP_MAX = 0.2
SprayDroneMill.POUR_BELOW = 0.08           -- víčko nejvýš tak hluboko pod uzlem hrdla (m); spec.pourBelow ho zvětší (lievec násypky je hluboký)
SprayDroneMill.POUR_PLAYER_DISTANCE = 15
SprayDroneMill.OUTLET_USED_MS = 400        -- tak dlouho po posledním hlášení hadice zůstává slepá spojka výstupu skrytá
SprayDroneMill.BAG_SEARCH_MS = 250         -- jak často se hledá big bag pod ústím roury
SprayDroneMill.BAG_FLOW_QUIET_MS = 800     -- tok do big bagu se po tolika ms bez litru zapíše jako skončený
SprayDroneMill.BAG_MIN_BELOW = 0.8        -- kořen vaku (dno) nejméně tolik pod plnicí hlavou (m)
SprayDroneMill.BAG_SPAWN_RETRY_MS = 5000   -- po nepovedeném vytvoření big bagu se zkusí znovu až za tuto dobu
SprayDroneMill.POUR_FLOW_QUIET_MS = 800    -- nalévání z kanystru / pytle se po tolika ms bez litru zapíše jako skončené
SprayDroneMill.MODE_DISTANCE = 2.6        -- hráč nejvýš tak daleko od páky ventilu, aby ji přepnul (m)
SprayDroneMill.SPOUT_DISTANCE = 2.8       -- hráč nejvýš tak daleko od kloubu roury, aby ji otočil (m)
SprayDroneMill.HINT_DISTANCE = 12         -- do této vzdálenosti od mlýnku se hráči pěšky ukazují nápovědy ventilu a roury (m)
SprayDroneMill.WARNING_MS = 2500

local function getSpec(self)
    return self[SprayDroneMill.SPEC_NAME]
end

function SprayDroneMill.prerequisitesPresent(specializations)
    return SpecializationUtil.hasSpecialization(FillUnit, specializations)
end

function SprayDroneMill.initSpecialization()
    local schema = Vehicle.xmlSchema
    schema:setXMLSpecializationType("SprayDroneMill")
    local key = "vehicle.sprayDroneMill"
    schema:register(XMLValueType.INT, key .. "#coarseFillUnitIndex", "Nádoba na hrubé vápno", 1)
    schema:register(XMLValueType.INT, key .. "#dieselFillUnitIndex", "Nafta pro motor", 2)
    schema:register(XMLValueType.INT, key .. "#fineFillUnitIndex", "Mezisklad jemného vápna", 3)
    schema:register(XMLValueType.STRING, key .. "#fineFillType", "Druh jemného vápna", "SDT_FINE_LIME")
    schema:register(XMLValueType.FLOAT, key .. "#millRate", "Mletí (l/s)", 6)
    schema:register(XMLValueType.FLOAT, key .. "#dieselPerHour", "Spotřeba motoru za chodu (l/h)", 6)
    schema:register(XMLValueType.FLOAT, key .. "#hoseRate", "Nejvyšší průtok výstupem jemného vápna (l/s)", 8)
    schema:register(XMLValueType.FLOAT, key .. "#pourRadius", "Víčko kanystru nafty nejvýš tak daleko od hrdla (m)", 0.3)
    schema:register(XMLValueType.FLOAT, key .. "#pourRate", "Nalévání z kanystru (l/s)", 4)
    schema:register(XMLValueType.FLOAT, key .. "#ringIntensity", "Svit prstence kolem tlačítka za chodu (lightIds0)", 4)
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#engine", "Střed motoru (zvuk)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#button", "Tlačítko na rozvaděči (ovládání pěšky: klik myší, B)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#ring", "Svítící prstenec kolem tlačítka (materiál staticLight_vertex)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#dieselNeck", "Hrdlo nádrže nafty")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#outlet", "Výstup jemného vápna (čelo spojky, sem se napojí hadice vleku)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#portCap", "Slepá spojka na výstupu (skrytá, když je připojená hadice)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#valveLever", "Páka ventilu výstupu (klik pěšky přepne hadice / roura)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".nodes#spoutJoint", "Kloub výsypné roury (klik pěšky otočí rouru)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".bagOutput#head", "Plnicí hlava výsypné roury (spodek límce)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".bagOutput#pivot", "Svislá osa kloubu výsypné roury")
    schema:register(XMLValueType.NODE_INDEX, key .. ".bagOutput#neck", "Hrdlo vaku pod hlavou (vidět jen za sypání)")
    schema:register(XMLValueType.FLOAT, key .. ".bagOutput#neckOffset", "Střed vaku je o tolik dál od kloubu než hlava (m)", 0.26)
    schema:register(XMLValueType.FLOAT, key .. ".bagOutput#halfWidth", "Vak se hledá do této vodorovné vzdálenosti od očekávaného středu (m)", 0.6)
    schema:register(XMLValueType.FLOAT, key .. ".bagOutput#depth", "Do jaké hloubky pod hlavou se vak hledá (m)", 2.5)
    EffectManager.registerEffectXMLPaths(schema, key .. ".dust.milling")
    EffectManager.registerEffectXMLPaths(schema, key .. ".dust.blowing")
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "engine")
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "grind")
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "pump")
    schema:setXMLSpecializationType()

    local savegame = Vehicle.xmlSchemaSavegame
    savegame:register(XMLValueType.BOOL, string.format("vehicles.vehicle(?).%s.sprayDroneMill#valveSpout", SprayDroneMill.MOD_NAME),
        "Ventil výstupu mlýnku je přepnutý na výsypnou rouru")
    savegame:register(XMLValueType.INT, string.format("vehicles.vehicle(?).%s.sprayDroneMill#spoutState", SprayDroneMill.MOD_NAME),
        "Stav výsypné roury (1 přeprava, 2 vedle vozíku, 3 za vozíkem)")
end

function SprayDroneMill.registerFunctions(vehicleType)
    SpecializationUtil.registerFunction(vehicleType, "sprayDroneMillCommand", SprayDroneMill.command)
end

function SprayDroneMill.registerEventListeners(vehicleType)
    SpecializationUtil.registerEventListener(vehicleType, "onLoad", SprayDroneMill)
    SpecializationUtil.registerEventListener(vehicleType, "onRegisterActionEvents", SprayDroneMill)
    SpecializationUtil.registerEventListener(vehicleType, "onDelete", SprayDroneMill)
    SpecializationUtil.registerEventListener(vehicleType, "onUpdate", SprayDroneMill)
    SpecializationUtil.registerEventListener(vehicleType, "onReadStream", SprayDroneMill)
    SpecializationUtil.registerEventListener(vehicleType, "onWriteStream", SprayDroneMill)
    SpecializationUtil.registerEventListener(vehicleType, "onReadUpdateStream", SprayDroneMill)
    SpecializationUtil.registerEventListener(vehicleType, "onWriteUpdateStream", SprayDroneMill)
end

function SprayDroneMill:onLoad(savegame)
    local spec = getSpec(self)
    local xml = self.xmlFile
    local key = "vehicle.sprayDroneMill"
    spec.coarseUnit = xml:getValue(key .. "#coarseFillUnitIndex", 1)
    spec.dieselUnit = xml:getValue(key .. "#dieselFillUnitIndex", 2)
    spec.fineUnit = xml:getValue(key .. "#fineFillUnitIndex", 3)
    local fineName = xml:getValue(key .. "#fineFillType", "SDT_FINE_LIME")
    spec.fineType = g_fillTypeManager:getFillTypeIndexByName(fineName) or FillType.UNKNOWN
    spec.millRate = math.max(xml:getValue(key .. "#millRate", 6), 0.01)
    spec.dieselPerSecond = math.max(xml:getValue(key .. "#dieselPerHour", 6), 0) / 3600
    spec.hoseRate = math.max(xml:getValue(key .. "#hoseRate", 8), 0.01)
    spec.pourRadius = math.max(xml:getValue(key .. "#pourRadius", 0.3), 0.05)
    spec.pourRate = math.max(xml:getValue(key .. "#pourRate", 4), 0.1)
    spec.engineNode = xml:getValue(key .. ".nodes#engine", nil, self.components, self.i3dMappings)
    spec.buttonNode = xml:getValue(key .. ".nodes#button", nil, self.components, self.i3dMappings)
    spec.ringNode = xml:getValue(key .. ".nodes#ring", nil, self.components, self.i3dMappings)
    spec.ringIntensity = xml:getValue(key .. "#ringIntensity", 4)
    spec.ringOn = false
    spec.dieselNeck = xml:getValue(key .. ".nodes#dieselNeck", nil, self.components, self.i3dMappings)
    spec.outlet = xml:getValue(key .. ".nodes#outlet", nil, self.components, self.i3dMappings)
    spec.portCap = xml:getValue(key .. ".nodes#portCap", nil, self.components, self.i3dMappings)
    spec.valveLever = xml:getValue(key .. ".nodes#valveLever", nil, self.components, self.i3dMappings)
    spec.spoutJoint = xml:getValue(key .. ".nodes#spoutJoint", nil, self.components, self.i3dMappings)
    spec.fillHead = xml:getValue(key .. ".bagOutput#head", nil, self.components, self.i3dMappings)
    spec.spoutPivot = xml:getValue(key .. ".bagOutput#pivot", nil, self.components, self.i3dMappings)
    spec.bagNeck = xml:getValue(key .. ".bagOutput#neck", nil, self.components, self.i3dMappings)
    spec.neckOffset = xml:getValue(key .. ".bagOutput#neckOffset", 0.26)
    spec.bagHalfWidth = xml:getValue(key .. ".bagOutput#halfWidth", 0.6)
    spec.bagDepth = xml:getValue(key .. ".bagOutput#depth", 2.5)
    spec.valveSpout = false
    spec.spoutState = SprayDroneMill.SPOUT_TRANSPORT
    spec.animGoal = {}
    spec.animSnap = true
    spec.neckShown = nil
    spec.warningTime = 0
    spec.bagTimer = 0
    spec.bag = nil
    spec.bagSpawning = false
    spec.bagSpawnRetry = 0
    spec.bagFlow = { on = false, total = 0, start = 0, last = 0 }
    spec.engineOn = false
    spec.milling = false
    spec.pumping = false
    spec.pumpUntil = 0
    spec.outletUsedTime = -1e9
    spec.capShown = true
    spec.actionEvents = {}
    spec.pourTimer = 0
    spec.pourAcc = 0
    spec.dirtyFlag = self:getNextDirtyFlag()

    if savegame ~= nil and not savegame.resetVehicles and self.isServer and spec.fillHead ~= nil then
        local saveKey = string.format("%s.%s.sprayDroneMill", savegame.key, SprayDroneMill.MOD_NAME)
        spec.valveSpout = savegame.xmlFile:getValue(saveKey .. "#valveSpout", false)
        spec.spoutState = math.clamp(savegame.xmlFile:getValue(saveKey .. "#spoutState", SprayDroneMill.SPOUT_TRANSPORT), 1, 3)
    end

    if self.isClient then
        spec.dustMilling = SprayDroneStation.loadSprayMist(self, xml, key .. ".dust.milling")
        spec.dustBlowing = SprayDroneStation.loadSprayMist(self, xml, key .. ".dust.blowing")
        for _, effect in ipairs(spec.dustMilling) do
            setRotation(effect.node, math.pi, 0, 0)
        end
        spec.dustMillingOn = false
        spec.dustBlowingOn = false
        spec.samples = {}
        for _, name in ipairs({ "engine", "grind", "pump" }) do
            if xml:hasProperty(key .. ".sounds." .. name) then
                spec.samples[name] = g_soundManager:loadSampleFromXML(xml, key .. ".sounds", name, self.baseDirectory, self.components, 0,
                    AudioGroup.VEHICLE, self.i3dMappings, self)
            end
        end
        spec.soundState = {}
        if g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
            spec.engineActivatable = SprayDroneMillEngineActivatable.new(self)
            g_currentMission.activatableObjectsSystem:addActivatable(spec.engineActivatable)
            if spec.fillHead ~= nil then
                spec.modeActivatable = SprayDroneMillModeActivatable.new(self)
                g_currentMission.activatableObjectsSystem:addActivatable(spec.modeActivatable)
                if spec.spoutJoint ~= nil then
                    spec.spoutActivatable = SprayDroneMillSpoutActivatable.new(self)
                    g_currentMission.activatableObjectsSystem:addActivatable(spec.spoutActivatable)
                end
            end
        end
    end
    -- první onUpdate dorovná páku ventilu a rouru na uložený stav (animSnap)
    self:raiseActive()
end

function SprayDroneMill:onDelete()
    local spec = getSpec(self)
    if spec == nil then
        return
    end
    if spec.engineActivatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(spec.engineActivatable)
    end
    spec.engineActivatable = nil
    if spec.modeActivatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(spec.modeActivatable)
    end
    spec.modeActivatable = nil
    if spec.spoutActivatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(spec.spoutActivatable)
    end
    spec.spoutActivatable = nil
    for _, field in ipairs({ "dustMilling", "dustBlowing" }) do
        if spec[field] ~= nil then
            SprayDroneStation.deleteSprayMist(spec[field])
            spec[field] = nil
        end
    end
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
    streamWriteBool(streamId, spec.milling)
    streamWriteBool(streamId, spec.pumping)
    streamWriteBool(streamId, spec.valveSpout)
    streamWriteUIntN(streamId, spec.spoutState, 2)
end

local function readState(self, streamId)
    local spec = getSpec(self)
    spec.engineOn = streamReadBool(streamId)
    spec.milling = streamReadBool(streamId)
    spec.pumping = streamReadBool(streamId)
    spec.valveSpout = streamReadBool(streamId)
    spec.spoutState = math.clamp(streamReadUIntN(streamId, 2), 1, 3)
    self:raiseActive()
end

function SprayDroneMill:onWriteStream(streamId, connection)
    writeState(self, streamId)
end

function SprayDroneMill:onReadStream(streamId, connection)
    readState(self, streamId)
    getSpec(self).animSnap = true
end

function SprayDroneMill:onWriteUpdateStream(streamId, connection, dirtyMask)
    if not connection:getIsServer() then
        local spec = getSpec(self)
        if streamWriteBool(streamId, bit32.band(dirtyMask, spec.dirtyFlag) ~= 0) then
            writeState(self, streamId)
        end
    end
end

function SprayDroneMill:onReadUpdateStream(streamId, timestamp, connection)
    if connection:getIsServer() and streamReadBool(streamId) then
        readState(self, streamId)
    end
end

function SprayDroneMill:saveToXMLFile(xmlFile, key, usedModNames)
    local spec = getSpec(self)
    if spec.valveSpout then
        xmlFile:setValue(key .. "#valveSpout", true)
    end
    if spec.spoutState ~= SprayDroneMill.SPOUT_TRANSPORT then
        xmlFile:setValue(key .. "#spoutState", spec.spoutState)
    end
end

---------------------------------------------------------------------------------------------------
-- příkazy (server) a rozhraní pro pumpu vleku

function SprayDroneMill.isConnectionAllowed(self, connection)
    return SprayDroneStation.isConnectionAllowed(self, connection)
end

-- Důvod (klíč textu), proč motor nejde zapnout; nil = jde.
function SprayDroneMill.getEngineBlocker(self)
    local spec = getSpec(self)
    if self:getFillUnitFillLevel(spec.dieselUnit) <= 0.01 then
        return "sdt_mill_noFuel"
    end
    return nil
end

-- Výstup jemného vápna pro pumpu vleku: uzel spojky, nádrž s vápnem, jeho druh, nejvyšší průtok a closed (ventil je na rouře: hadice zůstane připojená,
-- ale nic nedostane); nil, když vozík výstup nemá.
function SprayDroneMill.getOutlet(self)
    local spec = getSpec(self)
    if spec == nil or spec.outlet == nil or not entityExists(spec.outlet) then
        return nil
    end
    return { node = spec.outlet, fillUnitIndex = spec.fineUnit, fillType = spec.fineType, rate = spec.hoseRate, closed = spec.valveSpout }
end

-- Kam teče jemné vápno z meziskladu: "hose" (ventil na hadici, vápno si bere pumpa vleku), "bag" (do vaku pod plnicí hlavou), nil (nikam).
-- Druhá hodnota: klíč hlášky pro hráče, proč do vaku neteče (nil = nehlásit). Čistá funkce stavu, testuje ji tools/test_mill_flow.py.
function SprayDroneMill.getFlowTarget(engineOn, valveSpout, spoutState, spoutMoving, speed)
    if not engineOn then
        return nil, nil
    end
    if not valveSpout then
        return "hose", nil
    end
    if spoutState == SprayDroneMill.SPOUT_TRANSPORT then
        return nil, "sdt_mill_spoutFolded"
    end
    if spoutMoving or (speed or 0) >= SprayDroneMill.MAX_FILL_SPEED then
        return nil, nil
    end
    return "bag", nil
end

-- Roura se právě otáčí (animace běží nebo ještě nedojela do času stavu).
function SprayDroneMill.isSpoutMoving(self)
    local spec = getSpec(self)
    local name = SprayDroneMill.SPOUT_ANIM
    if self.getAnimationExists == nil or not self:getAnimationExists(name) then
        return false
    end
    return self:getIsAnimationPlaying(name) or math.abs(self:getAnimationTime(name) - SprayDroneMill.SPOUT_TIMES[spec.spoutState]) > 0.01
end

-- Očekávaný střed vaku pod rourou (svět): plnicí hlava posunutá o neckOffset ve směru ramene od kloubu; vrací x, výšku hlavy, z a směr ramene.
function SprayDroneMill.getBagSpot(self)
    local spec = getSpec(self)
    local hx, hy, hz = getWorldTranslation(spec.fillHead)
    local px, _, pz = getWorldTranslation(spec.spoutPivot or spec.fillHead)
    local dx, dz = hx - px, hz - pz
    local length = math.sqrt(dx * dx + dz * dz)
    if length < 0.01 then
        dx, _, dz = localDirectionToWorld(self.rootNode, 0, 0, 1)
        length = math.max(math.sqrt(dx * dx + dz * dz), 0.01)
    end
    dx, dz = dx / length, dz / length
    return hx + dx * spec.neckOffset, hy, hz + dz * spec.neckOffset, dx, dz
end

-- Pumpa vleku hlásí každý snímek, že je na výstup připojená hadice (klient i server): slepá spojka zůstane skrytá.
function SprayDroneMill.markOutletUsed(self)
    local spec = getSpec(self)
    spec.outletUsedTime = g_time
    self:raiseActive()
end

function SprayDroneMill.isRunning(self)
    return getSpec(self).engineOn
end

-- Server: pumpa právě čerpá vápno z vozíku (zvuk čerpání na všech klientech).
function SprayDroneMill.markPumping(self)
    local spec = getSpec(self)
    spec.pumpUntil = g_time + 400
    self:raiseActive()
end

function SprayDroneMill.command(self, command, target, noEventSend, x, y, z)
    if SprayDroneMillEvent.sendEvent(self, command, target, noEventSend, x, y, z) then
        return
    end
    local spec = getSpec(self)
    if command == SprayDroneMill.CMD_ENGINE_ON then
        SprayDroneSound.noteAction("mlýnek: zapnutí motoru")
        if not spec.engineOn and SprayDroneMill.getEngineBlocker(self) == nil then
            spec.engineOn = true
            self:raiseDirtyFlags(spec.dirtyFlag)
            self:raiseActive()
        end
    elseif command == SprayDroneMill.CMD_ENGINE_OFF then
        SprayDroneSound.noteAction("mlýnek: vypnutí motoru")
        if spec.engineOn then
            spec.engineOn, spec.milling, spec.pumping = false, false, false
            self:raiseDirtyFlags(spec.dirtyFlag)
            self:raiseActive()
        end
    elseif command == SprayDroneMill.CMD_VALVE_TOGGLE then
        if spec.fillHead == nil then
            return
        end
        spec.valveSpout = not spec.valveSpout
        SprayDroneSound.noteAction("mlýnek: ventil přepnut na " .. (spec.valveSpout and "výsypnou rouru" or "hadici")
            .. (spec.valveSpout and SprayDroneMill.isHoseAttached(self) and " (připojená hadice nic nedostane)" or ""))
        spec.bag = nil
        SprayDroneMill.flushBagFlow(self, true)
        self:raiseDirtyFlags(spec.dirtyFlag)
        self:raiseActive()
    elseif command >= SprayDroneMill.CMD_SPOUT_TRANSPORT and command <= SprayDroneMill.CMD_SPOUT_TRANSPORT + 2 then
        local state = command - SprayDroneMill.CMD_SPOUT_TRANSPORT + 1
        if spec.fillHead == nil or state == spec.spoutState then
            return
        end
        SprayDroneSound.noteAction(string.format("mlýnek: výsypná roura %d -> %d", spec.spoutState, state))
        spec.spoutState = state
        spec.bag = nil
        SprayDroneMill.flushBagFlow(self, true)
        self:raiseDirtyFlags(spec.dirtyFlag)
        self:raiseActive()
    end
end

-- K výstupu je právě připojená hadice vleku (hadice hlásí spojku každý snímek, markOutletUsed).
function SprayDroneMill.isHoseAttached(self)
    return g_time - getSpec(self).outletUsedTime < SprayDroneMill.OUTLET_USED_MS * 2
end

-- Záznam sypání do big bagu do log.txt (SDT děj): začátek a po BAG_FLOW_QUIET_MS bez litru konec s množstvím.
function SprayDroneMill.flushBagFlow(self, force)
    local spec = getSpec(self)
    local f = spec.bagFlow
    if f.on and (force or g_time - f.last >= SprayDroneMill.BAG_FLOW_QUIET_MS) then
        f.on = false
    end
end

-- Server: nejbližší vozidlo pod plnicí hlavou, jehož první fill unit přijímá jemné vápno a má místo (stojící vanilla big bag; jeho kořen je u dna vaku, tedy u
-- země), do halfWidth od očekávaného středu vaku (getBagSpot). Druhá návratová hodnota: stojí tam nějaký big bag, i plný nebo cizí (pak se nový nevytváří).
function SprayDroneMill.findBag(self)
    local spec = getSpec(self)
    local nx, ny, nz = SprayDroneMill.getBagSpot(self)
    local best, bestDistance, present
    local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, v in ipairs(vehicles) do
        if v ~= self and not v.isDeleted and v.rootNode ~= nil and v.spec_fillUnit ~= nil and entityExists(v.rootNode)
            and v:getFillUnitExists(1) and v:getFillUnitSupportsFillType(1, spec.fineType) then
            local x, y, z = getWorldTranslation(v.rootNode)
            local dx, dz = x - nx, z - nz
            local distance = math.sqrt(dx * dx + dz * dz)
            if distance <= spec.bagHalfWidth and y <= ny - SprayDroneMill.BAG_MIN_BELOW and y >= ny - spec.bagDepth then
                present = true
                if v:getFillUnitFreeCapacity(1) > SprayDroneMill.MIN_LITERS and g_currentMission.accessHandler:canFarmAccess(self:getOwnerFarmId(), v)
                    and (best == nil or distance < bestDistance) then
                    best, bestDistance = v, distance
                end
            end
        end
    end
    return best, present
end

-- Server: k plnicí hlavě postaví nový prázdný big bag: kořen (dno) na zem, natočený osou z (hloubka 0,84 m) podél ramene, bokem těsně za čelem hlavy.
function SprayDroneMill.spawnBag(self)
    local spec = getSpec(self)
    spec.bagSpawning = true
    local x, _, z, dx, dz = SprayDroneMill.getBagSpot(self)
    local _, rootY = getWorldTranslation(self.rootNode)
    local y = math.max(getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z), rootY) + 0.03
    local data = VehicleLoadingData.new()
    data:setFilename(SprayDroneMill.MOD_DIR .. "objects/limeBigBag/limeBigBag.xml")
    data:setPosition(x, y, z)
    data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz) + math.pi, 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(self:getOwnerFarmId())
    data:load(function(_, vehicles, state)
        spec.bagSpawning = false
        local v = vehicles ~= nil and vehicles[1] or nil
        if state ~= VehicleLoadingState.OK or v == nil then
            spec.bagSpawnRetry = g_time + SprayDroneMill.BAG_SPAWN_RETRY_MS
            return
        end
        spec.bag = v
    end)
end

-- Server: když jemné vápno teče do vaku (getFlowTarget), sypat ho z meziskladu do big bagu pod plnicí hlavou; vrací, jestli něco přeteklo.
function SprayDroneMill.updateBag(self, dt, seconds)
    local spec = getSpec(self)
    local target = spec.fillHead ~= nil and SprayDroneMill.getFlowTarget(spec.engineOn, spec.valveSpout, spec.spoutState, SprayDroneMill.isSpoutMoving(self),
        self:getLastSpeed()) or nil
    SprayDroneMill.flushBagFlow(self, target ~= "bag")
    if target ~= "bag" or not entityExists(spec.fillHead) then
        return false
    end
    spec.bagTimer = spec.bagTimer - dt
    if spec.bagTimer <= 0 or (spec.bag ~= nil and spec.bag.isDeleted) then
        spec.bagTimer = SprayDroneMill.BAG_SEARCH_MS
        local present
        spec.bag, present = SprayDroneMill.findBag(self)
        if spec.bag == nil and not present and not spec.bagSpawning and g_time >= spec.bagSpawnRetry then
            SprayDroneMill.spawnBag(self)
        end
    end
    local bag = spec.bag
    if bag == nil or bag.isDeleted then
        return false
    end
    local farmId = self:getOwnerFarmId()
    local amount = math.min(spec.hoseRate * seconds, self:getFillUnitFillLevel(spec.fineUnit), bag:getFillUnitFreeCapacity(1))
    if amount <= SprayDroneMill.MIN_LITERS then
        return false
    end
    local before = bag:getFillUnitFillLevel(1)
    bag:addFillUnitFillLevel(farmId, 1, amount, spec.fineType, ToolType.UNDEFINED, nil)
    local moved = bag:getFillUnitFillLevel(1) - before
    if moved <= 0 then
        return false
    end
    self:addFillUnitFillLevel(farmId, spec.fineUnit, -moved, spec.fineType, ToolType.UNDEFINED, nil)
    local f = spec.bagFlow
    if not f.on then
        f.on, f.total, f.start = true, 0, g_time
    end
    f.total = f.total + moved
    f.last = g_time
    return true
end

---------------------------------------------------------------------------------------------------
-- chod (server): mletí, spotřeba nafty, nalévání nafty z kanystru

function SprayDroneMill.updateServer(self, dt)
    local spec = getSpec(self)
    local seconds = dt * 0.001
    local farmId = self:getOwnerFarmId()
    local milling = false
    if spec.engineOn then
        self:raiseActive()
        local diesel = self:getFillUnitFillLevel(spec.dieselUnit)
        if diesel <= 0.001 then
            spec.engineOn = false
            self:raiseDirtyFlags(spec.dirtyFlag)
        else
            self:addFillUnitFillLevel(farmId, spec.dieselUnit, -math.min(spec.dieselPerSecond * seconds, diesel), FillType.DIESEL,
                ToolType.UNDEFINED, nil)
            local coarse = self:getFillUnitFillLevel(spec.coarseUnit)
            local freeFine = self:getFillUnitFreeCapacity(spec.fineUnit)
            local amount = math.min(spec.millRate * seconds, coarse, freeFine)
            if amount > SprayDroneMill.MIN_LITERS then
                local before = self:getFillUnitFillLevel(spec.fineUnit)
                self:addFillUnitFillLevel(farmId, spec.fineUnit, amount, spec.fineType, ToolType.UNDEFINED, nil)
                local made = self:getFillUnitFillLevel(spec.fineUnit) - before
                if made > 0 then
                    self:addFillUnitFillLevel(farmId, spec.coarseUnit, -made, FillType.LIME, ToolType.UNDEFINED, nil)
                    milling = true
                end
            end
        end
    end
    if SprayDroneMill.updateBag(self, dt, seconds) then
        spec.pumpUntil = g_time + 400
    end
    local pumping = spec.engineOn and g_time < spec.pumpUntil
    if g_time < spec.pumpUntil then
        self:raiseActive()
    end
    if milling ~= spec.milling or pumping ~= spec.pumping then
        spec.milling, spec.pumping = milling, pumping
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
    SprayDroneMill.updatePour(self, dt)
end

-- Varování hráčům (jen na serveru bez klientů je to hláška do logu, klient dostane text přes lokální volání).
function SprayDroneMill.notify(self, key)
    if g_currentMission ~= nil and g_currentMission.showBlinkingWarning ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(key), 3000)
    end
end

local function getPlayers()
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    return system ~= nil and system.players or {}
end

-- Záznam nalévání z kanystru / pytle do log.txt (SDT děj): začátek a po POUR_FLOW_QUIET_MS bez litru konec s množstvím.
local function notePour(self, spec, moved, from)
    local f = spec.pourFlow
    if f == nil then
        f = { on = false, total = 0, start = 0, last = 0 }
        spec.pourFlow = f
    end
    if moved > 0 then
        if not f.on then
            f.on, f.total, f.start = true, 0, g_time
        end
        f.total = f.total + moved
        f.last = g_time
    elseif f.on and g_time - f.last >= SprayDroneMill.POUR_FLOW_QUIET_MS then
        f.on = false
    end
end

-- Kanystr nafty (nebo pytel jemného vápna) z modu u hrdla nádrže a nakloněný hrdlem dolů: teče z něj do nádrže (pourRate l/s). U hrdla a naklonění
-- posuzuje SprayDroneToolbox.isCapAtNeck / getPourUp (držený předmět podle hráče, pytel podle hubice).
-- Spec s polem dieselUnit, dieselNeck, pourRadius, pourRate, pourAcc, pourTimer: mlýnek, ale i přenosná pumpa (SprayDronePump); volitelně pourUnit,
-- pourNeck, pourKind (výchozí nafta) a pourBelow pro jiný fill unit, hrdlo, druh a hloubku pod hrdlem (násypka na vápno, SprayDroneHopper).
function SprayDroneMill.updatePour(self, dt, spec)
    spec = spec or getSpec(self)
    spec.pourAcc = spec.pourAcc + dt
    spec.pourTimer = spec.pourTimer - dt
    local unit = spec.pourUnit or spec.dieselUnit
    local neckNode = spec.pourNeck or spec.dieselNeck
    local kind = spec.pourKind or FillType.DIESEL
    if spec.pourTimer > 0 or neckNode == nil then
        return
    end
    spec.pourTimer = SprayDroneMill.POUR_INTERVAL_MS
    local seconds = math.min(spec.pourAcc, 500) * 0.001
    spec.pourAcc = 0
    local movedFrom, moved = nil, 0
    local nx, ny, nz = getWorldTranslation(neckNode)
    local anyNear = false
    for _, player in ipairs(getPlayers()) do
        local px, py, pz
        if player.getPosition ~= nil then
            px, py, pz = player:getPosition()
        end
        if px ~= nil and MathUtil.vector3Length(px - nx, py - ny, pz - nz) <= SprayDroneMill.POUR_PLAYER_DISTANCE then
            anyNear = true
            break
        end
    end
    if anyNear and self:getFillUnitFreeCapacity(unit) > 0.001 then
        local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
        local held = SprayDroneToolbox.getHeldNodes()
        for _, v in ipairs(vehicles) do
            if v ~= self and v.spec_pallet ~= nil and v.spec_fillUnit ~= nil and not v.isDeleted and v.rootNode ~= nil and entityExists(v.rootNode)
                and SprayDroneToolbox ~= nil and SprayDroneToolbox.getCanisterKind(v) == kind then
                if SprayDroneToolbox.isCapAtNeck(v, neckNode, spec.pourRadius, spec.pourBelow or SprayDroneMill.POUR_BELOW, SprayDroneToolbox.getHolder(v, held)) then
                    local upY = SprayDroneToolbox.getPourUp(v, kind)
                    local liters = v:getFillUnitFillLevel(SprayDroneToolbox.CANISTER_UNIT) or 0
                    if upY <= SprayDroneMill.POUR_UP_MAX and liters > 0.001 then
                        local scale = math.clamp((SprayDroneMill.POUR_UP_MAX + 0.6 - upY) / 0.8, 0.3, 1)
                        local amount = math.min(liters, spec.pourRate * scale * seconds, self:getFillUnitFreeCapacity(unit))
                        local before = self:getFillUnitFillLevel(unit)
                        self:addFillUnitFillLevel(self:getOwnerFarmId(), unit, amount, kind, ToolType.UNDEFINED, nil)
                        moved = self:getFillUnitFillLevel(unit) - before
                        if moved > 0 then
                            v:addFillUnitFillLevel(self:getOwnerFarmId(), SprayDroneToolbox.CANISTER_UNIT, -moved, kind, ToolType.UNDEFINED, nil)
                            movedFrom = v
                        end
                        break
                    end
                end
            end
        end
    end
    notePour(self, spec, moved, movedFrom)
end

---------------------------------------------------------------------------------------------------
-- zvuk a vizuál (klient i server)

local function setSample(self, spec, name, playing)
    local sample = spec.samples ~= nil and spec.samples[name] or nil
    if sample == nil or spec.soundState[name] == playing then
        return
    end
    spec.soundState[name] = playing
    local reason = string.format("mlýnek: engineOn=%s milling=%s pumping=%s, pumpUntil za %d ms", tostring(spec.engineOn),
        tostring(spec.milling), tostring(spec.pumping), spec.pumpUntil - g_time)
    if playing then
        SprayDroneSound.play(self, sample, reason)
    else
        SprayDroneSound.stop(self, sample, reason)
    end
end

-- Prach (částicový efekt, jen klient) podle synchronizovaného stavu: u výsypky za mletí, pod plnicí hlavou, když se do big bagu sype.
local function setDust(self, spec, field, effects, on, what)
    if #effects == 0 or spec[field] == on then
        return
    end
    spec[field] = on
    SprayDroneStation.setSprayMistEmitting(effects, on)
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

-- Animace páky ventilu a roury dojedou do času podle synchronizovaného stavu (server i klienti každý sám, bez událostí animace); snap = skočit hned
-- (načtení, připojení klienta).
local function driveAnimation(self, spec, name, goal, snap)
    if self.getAnimationExists == nil or not self:getAnimationExists(name) then
        return
    end
    if snap then
        self:setAnimationTime(name, goal, true)
        spec.animGoal[name] = goal
        return
    end
    if spec.animGoal[name] ~= goal then
        spec.animGoal[name] = goal
        local t = self:getAnimationTime(name)
        if math.abs(t - goal) > 0.001 then
            self:playAnimation(name, goal > t and 1 or -1, t, true)
            self:setAnimationStopTime(name, goal)
        end
    end
end

-- Hráč, kterého se týkají hlášky mlýnku: nastoupený / ovládá mlýnek z tahače, nebo stojí pěšky do HINT_DISTANCE od něj.
local function isPlayerConcerned(self)
    if self.getIsActiveForInput ~= nil and self:getIsActiveForInput(true) then
        return true
    end
    local px, py, pz = getPlayerPosition()
    if px == nil then
        return false
    end
    local x, y, z = getWorldTranslation(self.rootNode)
    return MathUtil.vector3Length(px - x, py - y, pz - z) <= SprayDroneMill.HINT_DISTANCE
end

function SprayDroneMill:onUpdate(dt)
    local spec = getSpec(self)
    if self.isServer then
        SprayDroneMill.updateServer(self, dt)
    end
    if spec.fillHead ~= nil then
        driveAnimation(self, spec, SprayDroneMill.VALVE_ANIM, spec.valveSpout and 1 or 0, spec.animSnap)
        driveAnimation(self, spec, SprayDroneMill.SPOUT_ANIM, SprayDroneMill.SPOUT_TIMES[spec.spoutState], spec.animSnap)
        spec.animSnap = false
    end
    if spec.portCap ~= nil then
        local used = g_time - spec.outletUsedTime < SprayDroneMill.OUTLET_USED_MS
        if used == spec.capShown then
            spec.capShown = not used
            setVisibility(spec.portCap, spec.capShown)
        end
        if used then
            self:raiseActive()
        end
    end
    if self.isClient then
        if spec.ringNode ~= nil and spec.ringOn ~= spec.engineOn and entityExists(spec.ringNode) then
            spec.ringOn = spec.engineOn
            setShaderParameter(spec.ringNode, "lightIds0", spec.engineOn and spec.ringIntensity or 0, 0, 0, 0, false)
        end
        setSample(self, spec, "engine", spec.engineOn)
        setSample(self, spec, "grind", spec.milling)
        setSample(self, spec, "pump", spec.pumping)
        setDust(self, spec, "dustMillingOn", spec.dustMilling, spec.milling, "u výsypky do mlýna")
        local filling = spec.valveSpout and spec.pumping
        setDust(self, spec, "dustBlowingOn", spec.dustBlowing, filling, "pod plnicí hlavou")
        if spec.bagNeck ~= nil and spec.neckShown ~= filling then
            spec.neckShown = filling
            setVisibility(spec.bagNeck, filling)
        end
        local eventId = spec.engineEventId
        if eventId ~= nil then
            g_inputBinding:setActionEventText(eventId, g_i18n:getText(spec.engineOn and "sdt_mill_stop" or "sdt_mill_start"))
        end
        if spec.outputEventId ~= nil then
            g_inputBinding:setActionEventText(spec.outputEventId, g_i18n:getText(SprayDroneMill.getValveText(self)))
        end
        if spec.spoutEventId ~= nil then
            g_inputBinding:setActionEventText(spec.spoutEventId, g_i18n:getText(SprayDroneMill.SPOUT_TEXTS[spec.spoutState]))
        end
        if spec.fillHead ~= nil and spec.valveSpout and isPlayerConcerned(self) then
            if SprayDroneMill.isHoseAttached(self) then
                g_currentMission:addExtraPrintText(g_i18n:getText("sdt_mill_hoseSpout"))
            end
            local _, warning = SprayDroneMill.getFlowTarget(spec.engineOn, spec.valveSpout, spec.spoutState, false, 0)
            if warning ~= nil and g_time >= spec.warningTime then
                spec.warningTime = g_time + SprayDroneMill.WARNING_MS
                g_currentMission:showBlinkingWarning(g_i18n:getText(warning), SprayDroneMill.WARNING_MS)
            end
        end
    end
    if spec.engineOn then
        self:raiseActive()
    end
end

---------------------------------------------------------------------------------------------------
-- ovládání ve vozidle jako vanilla stroje (nastoupený ve vozíku nebo vozík vybraný z tahače): B (IMPLEMENT_EXTRA) motor,
-- Y (IMPLEMENT_EXTRA3) ventil výstupu, O (TOGGLE_PIPE) výsypná roura; pěšky u rozvaděče B nebo levé tlačítko, levé tlačítko na páku ventilu a na kloub roury

function SprayDroneMill:onRegisterActionEvents(isActiveForInput, isActiveForInputIgnoreSelection)
    local spec = getSpec(self)
    if not self.isClient then
        return
    end
    self:clearActionEventsTable(spec.actionEvents)
    spec.engineEventId = nil
    spec.outputEventId = nil
    spec.spoutEventId = nil
    if isActiveForInput then
        local _, eventId = self:addActionEvent(spec.actionEvents, InputAction.IMPLEMENT_EXTRA, self, SprayDroneMill.actionEventEngine,
            false, true, false, true, nil)
        if eventId ~= nil then
            g_inputBinding:setActionEventTextPriority(eventId, GS_PRIO_HIGH)
            g_inputBinding:setActionEventTextVisibility(eventId, true)
            spec.engineEventId = eventId
        end
        if spec.fillHead ~= nil then
            -- ventil (hadice / roura) jde přepnout i ze sedadla, ne jen pěšky myší na páku
            local _, outputId = self:addActionEvent(spec.actionEvents, InputAction.IMPLEMENT_EXTRA3, self, SprayDroneMill.actionEventOutput,
                false, true, false, true, nil)
            if outputId ~= nil then
                g_inputBinding:setActionEventTextPriority(outputId, GS_PRIO_HIGH)
                g_inputBinding:setActionEventTextVisibility(outputId, true)
                spec.outputEventId = outputId
            end
            -- výsypná roura jako roura kombajnu nebo překládacího vozu (O), stavy přeprava -> vedle -> za -> přeprava
            local _, spoutId = self:addActionEvent(spec.actionEvents, InputAction.TOGGLE_PIPE, self, SprayDroneMill.actionEventSpout,
                false, true, false, true, nil)
            if spoutId ~= nil then
                g_inputBinding:setActionEventTextPriority(spoutId, GS_PRIO_HIGH)
                g_inputBinding:setActionEventTextVisibility(spoutId, true)
                spec.spoutEventId = spoutId
            end
        end
    end
end

function SprayDroneMill.actionEventOutput(self, actionName, inputValue, callbackState, isAnalog)
    SprayDroneMill.toggleValve(self)
end

function SprayDroneMill.actionEventSpout(self, actionName, inputValue, callbackState, isAnalog)
    SprayDroneMill.cycleSpout(self)
end

-- Klíč textu akce ventilu podle stavu.
function SprayDroneMill.getValveText(self)
    return getSpec(self).valveSpout and "sdt_mill_valveToHose" or "sdt_mill_valveToSpout"
end

-- Další stav roury v cyklu přeprava -> vedle -> za -> přeprava (z ovládání hráče, klient).
function SprayDroneMill.cycleSpout(self)
    local spec = getSpec(self)
    local nextState = spec.spoutState % 3 + 1
    self:sprayDroneMillCommand(SprayDroneMill.CMD_SPOUT_TRANSPORT + nextState - 1)
end

function SprayDroneMill.actionEventEngine(self, actionName, inputValue, callbackState, isAnalog)
    local spec = getSpec(self)
    if spec.engineOn then
        self:sprayDroneMillCommand(SprayDroneMill.CMD_ENGINE_OFF)
        return
    end
    local blocker = SprayDroneMill.getEngineBlocker(self)
    if blocker ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(blocker), 2500)
        return
    end
    self:sprayDroneMillCommand(SprayDroneMill.CMD_ENGINE_ON)
end

local function isUsable(vehicle)
    if vehicle == nil or vehicle.isDeleted or g_localPlayer == nil then
        return false
    end
    if VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG then
        return false
    end
    return g_currentMission.accessHandler:canFarmAccess(g_localPlayer.farmId, vehicle)
end

local function distanceTo(x, y, z, node)
    if node == nil or not entityExists(node) then
        return math.huge
    end
    local nx, ny, nz = getWorldTranslation(node)
    return MathUtil.vector3Length(x - nx, y - ny, z - nz)
end

SprayDroneMillEngineActivatable = {}
local SprayDroneMillEngineActivatable_mt = Class(SprayDroneMillEngineActivatable)

function SprayDroneMillEngineActivatable.new(vehicle)
    local self = setmetatable({}, SprayDroneMillEngineActivatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_mill_start")
    return self
end

function SprayDroneMillEngineActivatable:getIsActivatable()
    local vehicle = self.vehicle
    local spec = getSpec(vehicle)
    local px, py, pz = getPlayerPosition()
    if px == nil or not isUsable(vehicle) or distanceTo(px, py, pz, spec.buttonNode or spec.engineNode) > SprayDroneMill.CONTROL_DISTANCE then
        return false
    end
    self.activateText = g_i18n:getText(spec.engineOn and "sdt_mill_stop" or "sdt_mill_start")
    if self.toggleEventId ~= nil then
        g_inputBinding:setActionEventText(self.toggleEventId, self.activateText)
        g_inputBinding:setActionEventTextVisibility(self.toggleEventId, SprayDroneLink.mayToggle(self))
    end
    if self.clickEventId ~= nil then
        g_inputBinding:setActionEventText(self.clickEventId, self.activateText)
        g_inputBinding:setActionEventTextVisibility(self.clickEventId, SprayDroneLink.mayClick(self))
    end
    return true
end

function SprayDroneMillEngineActivatable:getDistance(x, y, z)
    local spec = getSpec(self.vehicle)
    local node = spec.buttonNode or spec.engineNode
    return SprayDroneLink.aimDistance(distanceTo(x, y, z, node), node)
end

-- Pěšky u rozvaděče: B (zapnout stroj, jako u pumpy) nebo levé tlačítko na tlačítku rozvaděče zapne a vypne mlýnek.
function SprayDroneMillEngineActivatable:registerCustomInput(inputContext)
    self.toggleEventId = SprayDroneLink.registerToggle(self, self.run, self.activateText)
    self.clickEventId = SprayDroneLink.registerClick(self, self.runClick, self.activateText)
    SprayDroneLink.setSelected(self, true)
end

function SprayDroneMillEngineActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    SprayDroneLink.setSelected(self, false)
    self.toggleEventId = nil
    self.clickEventId = nil
end

function SprayDroneMillEngineActivatable:run()
    if not SprayDroneLink.mayToggle(self) then
        return
    end
    SprayDroneSound.noteAction("mlýnek: B pěšky u rozvaděče")
    SprayDroneMill.actionEventEngine(self.vehicle)
end

function SprayDroneMillEngineActivatable:runClick()
    if not SprayDroneLink.mayClick(self) then
        return
    end
    SprayDroneSound.noteAction("mlýnek: levé tlačítko myši u rozvaděče")
    SprayDroneMill.actionEventEngine(self.vehicle)
end

function SprayDroneMillEngineActivatable:activate() end

function SprayDroneMillEngineActivatable:deactivate() end

function SprayDroneMillEngineActivatable:draw() end

---------------------------------------------------------------------------------------------------
-- ventil výstupu: levé tlačítko myši na páku rozdělovače (R u spojky patří hadici vleku, SprayDroneWaterHose)

SprayDroneMillModeActivatable = {}
local SprayDroneMillModeActivatable_mt = Class(SprayDroneMillModeActivatable)

function SprayDroneMillModeActivatable.new(vehicle)
    local self = setmetatable({}, SprayDroneMillModeActivatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_mill_valveToSpout")
    return self
end

local function getValveNode(spec)
    return spec.valveLever or spec.outlet
end

function SprayDroneMillModeActivatable:getIsActivatable()
    local vehicle = self.vehicle
    local spec = getSpec(vehicle)
    local px, py, pz = getPlayerPosition()
    if px == nil or not isUsable(vehicle) or distanceTo(px, py, pz, getValveNode(spec)) > SprayDroneMill.MODE_DISTANCE then
        return false
    end
    self.activateText = g_i18n:getText(SprayDroneMill.getValveText(vehicle))
    if self.clickEventId ~= nil then
        g_inputBinding:setActionEventText(self.clickEventId, self.activateText)
        g_inputBinding:setActionEventTextVisibility(self.clickEventId, SprayDroneLink.mayClick(self))
    end
    return true
end

function SprayDroneMillModeActivatable:getDistance(x, y, z)
    local node = getValveNode(getSpec(self.vehicle))
    return SprayDroneLink.aimDistance(distanceTo(x, y, z, node), node)
end

function SprayDroneMillModeActivatable:registerCustomInput(inputContext)
    self.clickEventId = SprayDroneLink.registerClick(self, self.run, self.activateText)
    SprayDroneLink.setSelected(self, true)
end

function SprayDroneMillModeActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    SprayDroneLink.setSelected(self, false)
    self.clickEventId = nil
end

function SprayDroneMillModeActivatable:run()
    if not SprayDroneLink.mayClick(self) then
        return
    end
    SprayDroneSound.noteAction("mlýnek: levé tlačítko myši na páku ventilu")
    SprayDroneMill.toggleValve(self.vehicle)
end

function SprayDroneMillModeActivatable:activate() end

function SprayDroneMillModeActivatable:deactivate() end

function SprayDroneMillModeActivatable:draw() end

-- Přepnutí ventilu z ovládání hráče (klient); jde i s připojenou hadicí (ta pak nic nedostane, nápověda v onUpdate).
function SprayDroneMill.toggleValve(self)
    self:sprayDroneMillCommand(SprayDroneMill.CMD_VALVE_TOGGLE)
end

---------------------------------------------------------------------------------------------------
-- výsypná roura pěšky: levé tlačítko myši na kloub roury (stejný cyklus jako O ve vozidle)

SprayDroneMillSpoutActivatable = {}
local SprayDroneMillSpoutActivatable_mt = Class(SprayDroneMillSpoutActivatable)

function SprayDroneMillSpoutActivatable.new(vehicle)
    local self = setmetatable({}, SprayDroneMillSpoutActivatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText(SprayDroneMill.SPOUT_TEXTS[1])
    return self
end

function SprayDroneMillSpoutActivatable:getIsActivatable()
    local vehicle = self.vehicle
    local spec = getSpec(vehicle)
    local px, py, pz = getPlayerPosition()
    if px == nil or not isUsable(vehicle) or distanceTo(px, py, pz, spec.spoutJoint) > SprayDroneMill.SPOUT_DISTANCE then
        return false
    end
    self.activateText = g_i18n:getText(SprayDroneMill.SPOUT_TEXTS[spec.spoutState])
    if self.clickEventId ~= nil then
        g_inputBinding:setActionEventText(self.clickEventId, self.activateText)
        g_inputBinding:setActionEventTextVisibility(self.clickEventId, SprayDroneLink.mayClick(self))
    end
    return true
end

function SprayDroneMillSpoutActivatable:getDistance(x, y, z)
    local node = getSpec(self.vehicle).spoutJoint
    return SprayDroneLink.aimDistance(distanceTo(x, y, z, node), node)
end

function SprayDroneMillSpoutActivatable:registerCustomInput(inputContext)
    self.clickEventId = SprayDroneLink.registerClick(self, self.run, self.activateText)
    SprayDroneLink.setSelected(self, true)
end

function SprayDroneMillSpoutActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    SprayDroneLink.setSelected(self, false)
    self.clickEventId = nil
end

function SprayDroneMillSpoutActivatable:run()
    if not SprayDroneLink.mayClick(self) then
        return
    end
    SprayDroneSound.noteAction("mlýnek: levé tlačítko myši na kloub roury")
    SprayDroneMill.cycleSpout(self.vehicle)
end

function SprayDroneMillSpoutActivatable:activate() end

function SprayDroneMillSpoutActivatable:deactivate() end

function SprayDroneMillSpoutActivatable:draw() end
