-- Retranslační tyč na stativu (objects/relay/relayPole.xml, vehicle type sdtRelayPole = pallet + enterable + tahle specializace).
-- Je to samostatný předmět z obchodu: hráč ji složenou nese v rukou, postaví na zem a R ji rozloží (nohy stativu se rozevřou
-- a teleskopický stožár vyjede, 3 s). Do rozložené tyče jde nastoupit (E): kamera obíhá stožár, vpravo dole je baterie
-- (fillUnit ELECTRICCHARGE) a B tyč zapne / vypne. Rozložená tyč stojí pevně (kinematická fyzika) a nejde zvednout do ruky.
-- Zapnutá tyč vybíjí baterii (5 h provozu), vybitá se sama vypne. Nabíjí se vanilla nabíjecí stanicí (nastoupit, R u stanice)
-- nebo zvenku přes SprayDroneRelay.charge (např. na vleku). Složená, vypnutá nebo vybitá tyč dosah nezvětšuje; dosah počítá
-- SprayDroneLink (SprayDroneRelay.isOperating + nikdo ji nedrží).
-- Stav (rozloženo, zapnuto) se ukládá do savegame a jde po síti stavem vozidla; baterii ukládá a synchronizuje FillUnit.
-- Příkazy z klienta posílá SprayDroneRelayEvent, server je ověří (getChangeBlock) a provede.

SprayDroneRelay = {}
SprayDroneRelay.MOD_NAME = g_currentModName
SprayDroneRelay.SPEC_NAME = string.format("spec_%s.sprayDroneRelay", g_currentModName)
SprayDroneRelay.FOLD_TIME = 3000        -- ms rozložení / složení
SprayDroneRelay.ACTIVATE_DISTANCE = 2.2 -- m od tyče, do které jde rozložit / složit
SprayDroneRelay.MIN_UP = 0.8            -- svislá složka osy: tyč musí stát, aby šla rozložit a zapnout
-- Výdrž a nabíjení v ms. Spotřeba běží v reálném čase (dt bez zrychlení času) stejně jako vanilla Motorized:updateConsumers
-- a nafta centrály vleku; USE_TIME_SCALE = true by ji násobil zrychlením času hry.
SprayDroneRelay.DISCHARGE_TIME = 5 * 60 * 60 * 1000
SprayDroneRelay.CHARGE_TIME = 20 * 60 * 1000
SprayDroneRelay.USE_TIME_SCALE = false
SprayDroneRelay.CHARGING_HOLD = 1500    -- ms po posledním přírůstku baterie, po které diody ukazují nabíjení
SprayDroneRelay.LED_BLINK = 500         -- ms půlperioda blikání horní diody při nabíjení
SprayDroneRelay.blockChecks = {}

source(g_currentModDirectory .. "scripts/events/SprayDroneRelayEvent.lua")

function SprayDroneRelay.prerequisitesPresent(specializations)
    return true
end

function SprayDroneRelay.initSpecialization()
    local schema = Vehicle.xmlSchema
    schema:setXMLSpecializationType("SprayDroneRelay")
    local key = "vehicle.sprayDroneRelay"
    schema:register(XMLValueType.NODE_INDEX, key .. ".leg(?)#node", "Noha stativu (pivot v nábojnici)")
    schema:register(XMLValueType.VECTOR_3, key .. ".leg(?)#axis", "Osa sklopení nohy v souřadnicích rodiče")
    schema:register(XMLValueType.FLOAT, key .. ".leg(?)#angle", "O kolik stupňů se noha složí kolem osy", 30)
    schema:register(XMLValueType.NODE_INDEX, key .. ".mast#node", "Vysouvací část stožáru")
    schema:register(XMLValueType.VECTOR_TRANS, key .. ".mast#foldedTrans", "Posun vysouvací části ve složeném stavu", "0 -0.6 0")
    schema:register(XMLValueType.NODE_INDEX, key .. ".slide(?)#node", "Další posuvný díl (objímka nohou)")
    schema:register(XMLValueType.VECTOR_TRANS, key .. ".slide(?)#foldedTrans", "Posun dílu ve složeném stavu vůči rozloženému")
    schema:register(XMLValueType.NODE_INDEX, key .. ".led#node", "Kontrolka zapnutí")
    schema:register(XMLValueType.NODE_INDEX, key .. ".batteryLed(?)#node", "Dioda stavu baterie (zdola nahoru)")
    schema:register(XMLValueType.FLOAT, string.format("vehicle.%sConfigurations.%sConfiguration(?)#radius", SprayDroneStation.RELAY_CONFIG,
        SprayDroneStation.RELAY_CONFIG), "Dosah tyče (m) pro danou variantu v obchodě")
    schema:setXMLSpecializationType()

    local savegame = Vehicle.xmlSchemaSavegame
    local saveKey = string.format("vehicles.vehicle(?).%s.sprayDroneRelay", SprayDroneRelay.MOD_NAME)
    savegame:register(XMLValueType.BOOL, saveKey .. "#unfolded", "Rozloženo")
    savegame:register(XMLValueType.BOOL, saveKey .. "#powered", "Zapnuto")
end

function SprayDroneRelay.registerFunctions(vehicleType)
    SpecializationUtil.registerFunction(vehicleType, "setSprayDroneRelayState", SprayDroneRelay.setState)
    SpecializationUtil.registerFunction(vehicleType, "getLoadTriggerMaxFillSpeed", SprayDroneRelay.getLoadTriggerMaxFillSpeed)
end

function SprayDroneRelay.registerOverwrittenFunctions(vehicleType)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getCanBePickedUp", SprayDroneRelay.getCanBePickedUp)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getIsEnterable", SprayDroneRelay.getIsEnterable)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getDistanceToNode", SprayDroneRelay.getDistanceToNode)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getIsMapHotspotVisible", SprayDroneRelay.getIsMapHotspotVisible)
end

function SprayDroneRelay.registerEventListeners(vehicleType)
    for _, name in ipairs({ "onLoad", "onPostLoad", "onDelete", "onUpdate", "onReadStream", "onWriteStream", "onReadUpdateStream",
        "onWriteUpdateStream", "onRegisterActionEvents", "onFillUnitFillLevelChanged", "onEnterVehicle", "onLeaveVehicle" }) do
        SpecializationUtil.registerEventListener(vehicleType, name, SprayDroneRelay)
    end
end

local function getSpec(self)
    return self[SprayDroneRelay.SPEC_NAME]
end

local function warn(key)
    if g_currentMission ~= nil and g_i18n ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(key), 2500)
    end
end

---------------------------------------------------------------------------------------------------
-- veřejné API (dosah a pojistky letu, nabíjení na vleku)

-- Pojistka před složením / vypnutím: fn(vehicle, action) vrací l10n klíč důvodu, nebo nil. action je "fold" nebo "off".
function SprayDroneRelay.registerBlockCheck(fn)
    table.insert(SprayDroneRelay.blockChecks, fn)
end

-- Proč tyč teď nejde složit / vypnout (l10n klíč), nebo nil. Volá se na klientovi (hláška) i na serveru (rozhodnutí).
function SprayDroneRelay.blockReason(vehicle, action)
    for _, fn in ipairs(SprayDroneRelay.blockChecks) do
        local reason = fn(vehicle, action)
        if reason ~= nil then
            return reason
        end
    end
    return nil
end

-- Index fillUnitu baterie (ELECTRICCHARGE), nebo nil.
function SprayDroneRelay.getBatteryUnit(self)
    local state = getSpec(self)
    if state == nil then
        return nil
    end
    if state.batteryUnit == nil then
        state.batteryUnit = false
        if self.getFillUnits ~= nil and self.getFillUnitSupportsFillType ~= nil then
            for i, _ in ipairs(self:getFillUnits()) do
                if self:getFillUnitSupportsFillType(i, FillType.ELECTRICCHARGE) then
                    state.batteryUnit = i
                    break
                end
            end
        end
    end
    return state.batteryUnit or nil
end

-- Nabití 0..1 (tyč bez baterie hlásí 1).
function SprayDroneRelay.getBatteryFraction(vehicle)
    local unit = SprayDroneRelay.getBatteryUnit(vehicle)
    if unit == nil then
        return getSpec(vehicle) ~= nil and 1 or 0
    end
    local capacity = vehicle:getFillUnitCapacity(unit)
    if capacity == nil or capacity <= 0 then
        return 0
    end
    return math.max(0, math.min(1, vehicle:getFillUnitFillLevel(unit) / capacity))
end

-- Kolik reálných sekund ještě vydrží zapnutá tyč při aktuálním zrychlení času.
function SprayDroneRelay.getRemainingSeconds(vehicle)
    local scale = 1
    if SprayDroneRelay.USE_TIME_SCALE and g_currentMission ~= nil and g_currentMission.getEffectiveTimeScale ~= nil then
        scale = math.max(g_currentMission:getEffectiveTimeScale(), 0.001)
    end
    return SprayDroneRelay.getBatteryFraction(vehicle) * SprayDroneRelay.DISCHARGE_TIME / 1000 / scale
end

-- Dobije baterii o fraction (podíl plné kapacity, např. dt / SprayDroneRelay.CHARGE_TIME). Jen server. Vrací skutečně přidaný podíl.
function SprayDroneRelay.charge(vehicle, fraction)
    local unit = SprayDroneRelay.getBatteryUnit(vehicle)
    if unit == nil or not vehicle.isServer or fraction == nil or fraction <= 0 then
        return 0
    end
    local capacity = vehicle:getFillUnitCapacity(unit)
    local free = capacity - vehicle:getFillUnitFillLevel(unit)
    if capacity <= 0 or free <= 0 then
        return 0
    end
    local applied = vehicle:addFillUnitFillLevel(vehicle:getOwnerFarmId(), unit, math.min(fraction * capacity, free), FillType.ELECTRICCHARGE,
        ToolType.UNDEFINED, nil) or 0
    return applied / capacity
end

-- Je relé v provozu (rozložené, zapnuté, nabité a stojí)? Volá SprayDroneLink; držení v rukou kontroluje on.
function SprayDroneRelay.isOperating(self)
    local state = getSpec(self)
    return state ~= nil and state.unfolded and state.powered and state.progress >= 1 and SprayDroneRelay.getBatteryFraction(self) > 0
        and SprayDroneRelay.isUpright(self)
end

-- Je tyč svisle? (rozložit a zapnout jde jen vzpřímenou)
function SprayDroneRelay.isUpright(self)
    local _, upY = localDirectionToWorld(self.rootNode, 0, 1, 0)
    return upY >= SprayDroneRelay.MIN_UP
end

local function isControlled(self)
    return self.getIsControlled ~= nil and self:getIsControlled()
end

-- Proč přechod do (unfolded, powered) teď nejde (l10n klíč), nebo nil.
function SprayDroneRelay.getChangeBlock(self, unfolded, powered)
    local state = getSpec(self)
    if unfolded and not state.unfolded and not SprayDroneRelay.isUpright(self) then
        return "sdt_relay_notUpright"
    end
    if powered and not state.powered then
        if not state.unfolded or state.progress < 1 then
            return "sdt_relay_notUnfolded"
        end
        if SprayDroneRelay.getBatteryFraction(self) <= 0 then
            return "sdt_relay_batteryEmpty"
        end
        if not SprayDroneRelay.isUpright(self) then
            return "sdt_relay_notUpright"
        end
    end
    if state.unfolded and not unfolded then
        if isControlled(self) then
            return "sdt_relay_occupied"
        end
        return SprayDroneRelay.blockReason(self, "fold")
    end
    if state.powered and not powered then
        return SprayDroneRelay.blockReason(self, "off")
    end
    return nil
end

-- Poloha uzlů podle průběhu rozložení t (0 složeno, 1 rozloženo).
function SprayDroneRelay.applyProgress(self)
    local state = getSpec(self)
    local fold = 1 - state.progress
    for _, leg in ipairs(state.legs) do
        local half = math.rad(leg.angle * fold) / 2
        local s = math.sin(half)
        setQuaternion(leg.node, leg.axis[1] * s, leg.axis[2] * s, leg.axis[3] * s, math.cos(half))
    end
    for _, slide in ipairs(state.slides) do
        local b, t = slide.base, slide.foldedTrans
        setTranslation(slide.node, b[1] + t[1] * fold, b[2] + t[2] * fold, b[3] + t[3] * fold)
    end
    if state.led ~= nil then
        setVisibility(state.led, state.powered and state.progress >= 1)
    end
end

-- Diody baterie: svítí za provozu, při nabíjení a po nástupu; počet podle nabití (aspoň jedna, dokud není prázdná), při nabíjení
-- bliká nejvyšší rozsvícená.
function SprayDroneRelay.updateBatteryLeds(self)
    local state = getSpec(self)
    local count = #state.batteryLeds
    if count == 0 then
        return
    end
    local charging = state.chargingUntil > g_time
    local shown = (state.powered and state.progress >= 1) or charging or isControlled(self)
    local lit = 0
    if shown then
        local fraction = SprayDroneRelay.getBatteryFraction(self)
        if fraction > 0 then
            lit = math.max(math.ceil(fraction * count - 0.001), 1)
        end
    end
    local blinkOff = charging and math.floor(g_time / SprayDroneRelay.LED_BLINK) % 2 == 1
    for i, node in ipairs(state.batteryLeds) do
        local show = i < lit or (i == lit and not blinkOff)
        if state.batteryLedShown[i] ~= show then
            state.batteryLedShown[i] = show
            setVisibility(node, show)
        end
    end
end

function SprayDroneRelay:onLoad(savegame)
    local state = {}
    self[SprayDroneRelay.SPEC_NAME] = state
    local xml = self.xmlFile
    local key = "vehicle.sprayDroneRelay"
    state.legs = {}
    xml:iterate(key .. ".leg", function(_, legKey)
        local node = xml:getValue(legKey .. "#node", nil, self.components, self.i3dMappings)
        local axis = xml:getValue(legKey .. "#axis", nil, true)
        if node ~= nil and axis ~= nil then
            local length = math.sqrt(axis[1] ^ 2 + axis[2] ^ 2 + axis[3] ^ 2)
            if length > 0 then
                table.insert(state.legs, { node = node, axis = { axis[1] / length, axis[2] / length, axis[3] / length },
                    angle = xml:getValue(legKey .. "#angle", 30) })
            end
        end
    end)
    -- posuvné díly (stožár a objímka nohou): posun ve složeném stavu se přičítá k poloze z i3d (rozloženo)
    state.slides = {}
    local function addSlide(slideKey, default)
        local node = xml:getValue(slideKey .. "#node", nil, self.components, self.i3dMappings)
        if node ~= nil then
            table.insert(state.slides, { node = node, base = { getTranslation(node) },
                foldedTrans = xml:getValue(slideKey .. "#foldedTrans", nil, true) or default })
        end
    end
    addSlide(key .. ".mast", { 0, -0.6, 0 })
    xml:iterate(key .. ".slide", function(_, slideKey)
        addSlide(slideKey, { 0, 0, 0 })
    end)
    state.led = xml:getValue(key .. ".led#node", nil, self.components, self.i3dMappings)
    state.batteryLeds, state.batteryLedShown = {}, {}
    xml:iterate(key .. ".batteryLed", function(_, ledKey)
        local node = xml:getValue(ledKey .. "#node", nil, self.components, self.i3dMappings)
        if node ~= nil then
            table.insert(state.batteryLeds, node)
        end
    end)
    state.chargingUntil = 0
    state.actionEvents = {}
    state.radius = SprayDroneStation.getConfigValue(self, xml, "vehicle", SprayDroneStation.RELAY_CONFIG, "radius", SprayDroneLink.RELAY_RADIUS)
    state.unfolded, state.powered = false, false
    if savegame ~= nil and not savegame.resetVehicles then
        local saveKey = savegame.key .. "." .. SprayDroneRelay.MOD_NAME .. ".sprayDroneRelay"
        state.unfolded = savegame.xmlFile:getValue(saveKey .. "#unfolded", false)
        state.powered = state.unfolded and savegame.xmlFile:getValue(saveKey .. "#powered", false)
    end
    state.progress = state.unfolded and 1 or 0
    state.lastPowered = state.powered
    state.dirtyFlag = self:getNextDirtyFlag()
    SprayDroneRelay.applyProgress(self)

    if self.isClient and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        state.activatable = SprayDroneRelayActivatable.new(self)
        g_currentMission.activatableObjectsSystem:addActivatable(state.activatable)
    end
end

-- Po načtení: rozložená tyč se hned zmrazí (updateFreeze v prvním updatu), diody podle baterie.
function SprayDroneRelay:onPostLoad(savegame)
    self:raiseActive()
end

function SprayDroneRelay:onDelete()
    local state = getSpec(self)
    if state ~= nil and state.activatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(state.activatable)
        state.activatable = nil
    end
end

function SprayDroneRelay:saveToXMLFile(xmlFile, key, usedModNames)
    local state = getSpec(self)
    xmlFile:setValue(key .. "#unfolded", state.unfolded)
    xmlFile:setValue(key .. "#powered", state.powered)
end

function SprayDroneRelay:onWriteStream(streamId, connection)
    local state = getSpec(self)
    streamWriteBool(streamId, state.unfolded)
    streamWriteBool(streamId, state.powered)
end

function SprayDroneRelay:onReadStream(streamId, connection)
    local state = getSpec(self)
    state.unfolded = streamReadBool(streamId)
    state.powered = streamReadBool(streamId)
    state.progress = state.unfolded and 1 or 0
    state.lastPowered = state.powered
    SprayDroneRelay.applyProgress(self)
end

function SprayDroneRelay:onWriteUpdateStream(streamId, connection, dirtyMask)
    if not connection:getIsServer() then
        local state = getSpec(self)
        if streamWriteBool(streamId, bit32.band(dirtyMask, state.dirtyFlag) ~= 0) then
            streamWriteBool(streamId, state.unfolded)
            streamWriteBool(streamId, state.powered)
        end
    end
end

function SprayDroneRelay:onReadUpdateStream(streamId, timestamp, connection)
    if connection:getIsServer() and streamReadBool(streamId) then
        local state = getSpec(self)
        state.unfolded = streamReadBool(streamId)
        state.powered = streamReadBool(streamId)
        self:raiseActive()
    end
end

-- Změní stav (rozloženo, zapnuto). Klient jen pošle příkaz na server a stav přijde zpátky stavem vozidla; server ho ověří
-- (getChangeBlock) a provede. force = bez kontrol (vybitá baterie vypíná sama). Vrací true, když se změna provedla / odeslala.
function SprayDroneRelay.setState(self, unfolded, powered, noEventSend, force)
    local state = getSpec(self)
    unfolded = unfolded == true
    powered = unfolded and powered == true
    if state.unfolded == unfolded and state.powered == powered then
        return false
    end
    if not force and SprayDroneRelay.getChangeBlock(self, unfolded, powered) ~= nil then
        return false
    end
    if g_server == nil and noEventSend ~= true then
        SprayDroneRelayEvent.sendEvent(self, unfolded, powered)
        return true
    end
    state.unfolded, state.powered = unfolded, powered
    if self.isServer then
        self:raiseDirtyFlags(state.dirtyFlag)
    end
    self:raiseActive()
    return true
end

-- Rozložená tyč stojí pevně: fyzika komponenty je kinematická od začátku rozkládání do konce skládání (jen server, klienti
-- polohu dostávají). Past z vleku (SprayDroneStation.updateFreeze): po přepnutí dynamického tělesa na kinematické za běhu
-- engine odsune dětské kolizní tvary (compoundChild ve skupině "collisions") o těžiště, proto se na dobu zmrazení posunou zpět;
-- kořenový tvar komponenty je jen drobná krychle. Tyč načtená rovnou rozložená se zmrazí v prvním updatu a neposouvá se.
function SprayDroneRelay.updateFreeze(self)
    local state = getSpec(self)
    if self.components == nil or self.components[1] == nil or self.dynamicMountObject ~= nil or self.tensionMountObject ~= nil then
        return
    end
    if Platform ~= nil and Platform.gameplay ~= nil and Platform.gameplay.hasDynamicPallets == false then
        return
    end
    local frozen = state.unfolded or state.progress > 0
    if frozen == state.frozen then
        return
    end
    local node = self.components[1].node
    if frozen then
        state.centerOfMass = { getCenterOfMass(node) }
    end
    local loadedFrozen = state.frozen == nil and frozen
    state.frozen = frozen
    setRigidBodyType(node, frozen and RigidBodyType.KINEMATIC or RigidBodyType.DYNAMIC)
    if not loadedFrozen then
        SprayDroneRelay.shiftCollisionShapes(self, frozen)
    end
end

function SprayDroneRelay.shiftCollisionShapes(self, frozen)
    local state = getSpec(self)
    local com = state.centerOfMass
    if com == nil then
        return
    end
    local node = self.components[1].node
    for i = 0, getNumOfChildren(node) - 1 do
        local group = getChildAt(node, i)
        if getName(group) == "collisions" then
            state.shapeOrigins = state.shapeOrigins or {}
            for j = 0, getNumOfChildren(group) - 1 do
                local shape = getChildAt(group, j)
                if state.shapeOrigins[shape] == nil then
                    state.shapeOrigins[shape] = { getTranslation(shape) }
                end
                local o = state.shapeOrigins[shape]
                if frozen then
                    setTranslation(shape, o[1] - com[1], o[2] - com[2], o[3] - com[3])
                else
                    setTranslation(shape, o[1], o[2], o[3])
                end
            end
        end
    end
end

-- Spotřeba zapnuté tyče (server); vybitá tyč se vypne.
function SprayDroneRelay.updateBattery(self, dt)
    local state = getSpec(self)
    local unit = SprayDroneRelay.getBatteryUnit(self)
    if unit == nil or not state.powered or state.progress < 1 then
        return
    end
    local scale = 1
    if SprayDroneRelay.USE_TIME_SCALE then
        scale = g_currentMission:getEffectiveTimeScale()
    end
    local used = self:getFillUnitCapacity(unit) * dt * scale / SprayDroneRelay.DISCHARGE_TIME
    if self:getFillUnitFillLevel(unit) > 0 then
        self:addFillUnitFillLevel(self:getOwnerFarmId(), unit, -used, FillType.ELECTRICCHARGE, ToolType.UNDEFINED, nil)
    end
    if self:getFillUnitFillLevel(unit) <= 0 then
        self:setSprayDroneRelayState(true, false, true, true)
    end
end

function SprayDroneRelay:onUpdate(dt)
    local state = getSpec(self)
    local target = state.unfolded and 1 or 0
    if state.progress ~= target then
        local step = dt / SprayDroneRelay.FOLD_TIME
        state.progress = state.progress < target and math.min(state.progress + step, 1) or math.max(state.progress - step, 0)
        SprayDroneRelay.applyProgress(self)
        self:raiseActive()
    elseif state.led ~= nil and getVisibility(state.led) ~= (state.powered and state.progress >= 1) then
        SprayDroneRelay.applyProgress(self)
    end
    if self.isServer then
        SprayDroneRelay.updateFreeze(self)
        SprayDroneRelay.updateBattery(self, dt)
    end
    if self.isClient then
        if state.lastPowered and not state.powered and SprayDroneRelay.getBatteryFraction(self) <= 0
            and self.getIsEntered ~= nil and self:getIsEntered() then
            warn("sdt_relay_batteryEmpty")
        end
        SprayDroneRelay.updateBatteryLeds(self)
        SprayDroneRelay.updateActionEvents(self)
    end
    state.lastPowered = state.powered
    if state.powered or state.chargingUntil > g_time then
        self:raiseActive()
    end
end

function SprayDroneRelay:onFillUnitFillLevelChanged(fillUnitIndex, fillLevelDelta)
    local state = getSpec(self)
    if state ~= nil and fillUnitIndex == SprayDroneRelay.getBatteryUnit(self) then
        if fillLevelDelta > 0 then
            state.chargingUntil = g_time + SprayDroneRelay.CHARGING_HOLD
        end
        self:raiseActive()
    end
end

function SprayDroneRelay:onEnterVehicle(isControlling)
    self:raiseActive()
end

function SprayDroneRelay:onLeaveVehicle(wasEntered)
    self:raiseActive()
end

-- Vanilla nabíjecí stanice (LoadTrigger) nabíjí nejvýš rychlostí plné nabití za CHARGE_TIME (l/ms); stanice sama dává 0,015 l/s.
function SprayDroneRelay:getLoadTriggerMaxFillSpeed()
    local unit = SprayDroneRelay.getBatteryUnit(self)
    if unit == nil then
        return math.huge
    end
    return self:getFillUnitCapacity(unit) / SprayDroneRelay.CHARGE_TIME
end

-- Rozloženou (i rozkládanou / skládanou) tyč nejde zvednout do ruky.
function SprayDroneRelay:getCanBePickedUp(superFunc, byPlayer)
    local state = getSpec(self)
    if state ~= nil and (state.unfolded or state.progress > 0) then
        return false
    end
    return superFunc(self, byPlayer)
end

local function canEnter(self)
    local state = getSpec(self)
    return state ~= nil and state.unfolded and state.progress >= 1
end

function SprayDroneRelay:getIsEnterable(superFunc)
    return canEnter(self) and superFunc(self)
end

-- Nabídka „nastoupit“ (E) jen u rozložené tyče; složená se jen nese v rukou.
function SprayDroneRelay:getDistanceToNode(superFunc, node)
    if not canEnter(self) and not isControlled(self) then
        self.interactionFlag = Vehicle.INTERACTION_FLAG_NONE
        return math.huge
    end
    return superFunc(self, node)
end

-- Pallet ikonu na mapě skrývá; tyč ji má (kromě chvíle, kdy v ní někdo sedí: pak je tam značka hráče).
function SprayDroneRelay:getIsMapHotspotVisible(superFunc)
    return not isControlled(self)
end

---------------------------------------------------------------------------------------------------
-- ovládání po nástupu: B (IMPLEMENT_EXTRA) zapne / vypne

function SprayDroneRelay:onRegisterActionEvents(isActiveForInput, isActiveForInputIgnoreSelection)
    if not self.isClient then
        return
    end
    local state = getSpec(self)
    self:clearActionEventsTable(state.actionEvents)
    state.powerEventId = nil
    if isActiveForInputIgnoreSelection then
        local _, id = self:addActionEvent(state.actionEvents, InputAction.IMPLEMENT_EXTRA, self, SprayDroneRelay.actionEventPower, false, true,
            false, true, nil)
        state.powerEventId = id
        g_inputBinding:setActionEventTextPriority(id, GS_PRIO_VERY_HIGH)
        SprayDroneRelay.updateActionEvents(self)
    end
end

function SprayDroneRelay.updateActionEvents(self)
    local state = getSpec(self)
    if state.powerEventId ~= nil then
        g_inputBinding:setActionEventText(state.powerEventId, g_i18n:getText(state.powered and "sdt_relay_off" or "sdt_relay_on"))
        g_inputBinding:setActionEventActive(state.powerEventId, state.unfolded and state.progress >= 1)
    end
end

function SprayDroneRelay.actionEventPower(self, actionName, inputValue, callbackState, isAnalog)
    local state = getSpec(self)
    local powered = not state.powered
    local reason = SprayDroneRelay.getChangeBlock(self, true, powered)
    if reason ~= nil then
        warn(reason)
        return
    end
    self:setSprayDroneRelayState(true, powered)
end

---------------------------------------------------------------------------------------------------
-- ovládání zvenku: R (ACTIVATE_OBJECT) rozloží / složí; E je nástup (Enterable), proto se rozklad na něj nedává

SprayDroneRelayActivatable = {}
local RelayActivatable_mt = Class(SprayDroneRelayActivatable)

function SprayDroneRelayActivatable.new(vehicle)
    local self = setmetatable({}, RelayActivatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_relay_unfold")
    return self
end

function SprayDroneRelayActivatable:getIsActivatable()
    local player = g_localPlayer
    if player == nil or (player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil) then
        return false
    end
    local vehicle = self.vehicle
    if vehicle.isDeleted or vehicle.rootNode == nil or not entityExists(vehicle.rootNode) or g_gui:getIsGuiVisible() or isControlled(vehicle) then
        return false
    end
    local hands = player.hands
    if hands ~= nil and hands.getIsHoldingItem ~= nil and hands:getIsHoldingItem() then
        return false
    end
    local px, py, pz = player:getPosition()
    if px == nil then
        return false
    end
    local x, y, z = getWorldTranslation(vehicle.rootNode)
    if MathUtil.vector3Length(px - x, py - y, pz - z) > SprayDroneRelay.ACTIVATE_DISTANCE + 0.9 then
        return false
    end
    local state = getSpec(vehicle)
    self.activateText = g_i18n:getText(state.unfolded and "sdt_relay_fold" or "sdt_relay_unfold")
    if self.foldEventId ~= nil then
        g_inputBinding:setActionEventText(self.foldEventId, self.activateText)
    end
    return true
end

function SprayDroneRelayActivatable:registerCustomInput(inputContext)
    local _
    _, self.foldEventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_OBJECT, self, self.run, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(self.foldEventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(self.foldEventId, true)
    g_inputBinding:setActionEventText(self.foldEventId, self.activateText)
end

function SprayDroneRelayActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    self.foldEventId = nil
end

-- Rozložit (jen vzpřímená tyč) / složit (složení ji i vypne; pojistky letu mohou složení zakázat).
function SprayDroneRelayActivatable:run()
    local vehicle = self.vehicle
    local state = getSpec(vehicle)
    local unfolded = not state.unfolded
    local reason = SprayDroneRelay.getChangeBlock(vehicle, unfolded, false)
    if reason ~= nil then
        warn(reason)
        return
    end
    vehicle:setSprayDroneRelayState(unfolded, false)
end

function SprayDroneRelayActivatable:getDistance(x, y, z)
    local nx, ny, nz = getWorldTranslation(self.vehicle.rootNode)
    return MathUtil.vector3Length(x - nx, y - ny, z - nz)
end

function SprayDroneRelayActivatable:activate() end

function SprayDroneRelayActivatable:deactivate() end

function SprayDroneRelayActivatable:draw() end
