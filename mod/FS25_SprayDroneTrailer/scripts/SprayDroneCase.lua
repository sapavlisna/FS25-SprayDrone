-- Přenosný skenovací dron v kufru (docs/DRON.md, „Přenosný skenovací dron (kufr)“; docs/PLAN-airasi-kufr.md F2): SprayDroneStation v profilu
-- portable (vehicle.sprayDrone#portable) na vozidle typu pallet (objects/droneCase/scanCase.xml). Víko je Foldable (otevřené = rozloženo); animace
-- víka po otevření položí vedle kufru přistávací podložku a uzel droneCarrier na ni přenese dron. Domov dronu je rodič jeho kořene
-- (SprayDroneStation.getHomePosition), tedy střed podložky; tablet kufr najde jako každý vlek (SprayDroneLink.collectTrailers). Kufr nemá
-- centrálu, nádrže, hadici ani bednu.
--
-- Baterie kufru (pool spec.batteries: dvě šachty v pěně, strop poolu je i s baterií v dronu, takže po přistání je kam vrátit
-- vybitou a servis ji vymění za nabitou jako u vleku) se nabíjí jen „ze zásuvky“ (rozhodnutí D1): kufr leží do CHARGE_RANGE m od vlastní budovy
-- farmy (placeable farmy se specializací budovy, ploty a cesty ji nemají), nebo od běžící elektrocentrály vleku SprayDrone (getHasPower); ta
-- pak pálí naftu jako za jednu nabíjenou baterii. Zdroj hledá server jednou za SOURCE_CHECK_TIME, klientům jde ve stavu vozidla.

SprayDroneCase = {}

SprayDroneCase.CHARGE_RANGE = 15
SprayDroneCase.SOURCE_CHECK_TIME = 1000
-- elektrocentrála vleku počítá kufr jako zátěž, dokud se kufr ozval před méně než LOAD_TIMEOUT ms
SprayDroneCase.LOAD_TIMEOUT = 2500
-- za letu se kufr nesmí pohnout dál než MOVE_TOLERANCE m od místa vzletu (nesený, na korbě jedoucího pickupu)
SprayDroneCase.MOVE_TOLERANCE = 2
-- hráč pěšky nejvýš tak daleko od kufru: víko (R) a řádky stavu v nápovědě
SprayDroneCase.ACTIVATE_DISTANCE = 2.5
SprayDroneCase.SOURCE_NONE = 0
SprayDroneCase.SOURCE_BUILDING = 1
SprayDroneCase.SOURCE_GENERATOR = 2
SprayDroneCase.SOURCE_BITS = 2
SprayDroneCase.SOURCE_TEXTS = { [0] = "sdt_case_sourceNone", [1] = "sdt_case_sourceBuilding", [2] = "sdt_case_sourceGenerator" }
-- placeable s některou z těchto specializací je budova s elektřinou; kryté stavby (kůlny, haly) poznají indoorAreas
SprayDroneCase.BUILDING_SPECS = { "spec_farmhouse", "spec_workshop", "spec_husbandry", "spec_productionPoint", "spec_silo",
    "spec_objectStorage", "spec_greenhouse", "spec_chargingStation" }

local function getSpec(self)
    return self[SprayDroneStation.SPEC_NAME]
end

function SprayDroneCase.getIsPortable(self)
    local spec = self ~= nil and self[SprayDroneStation.SPEC_NAME] or nil
    return spec ~= nil and SprayDroneDrones.getRoot(self).portable == true
end

---------------------------------------------------------------------------------------------------
-- zdroj nabíjení (server)

function SprayDroneCase.getIsBuilding(placeable)
    for _, name in ipairs(SprayDroneCase.BUILDING_SPECS) do
        if placeable[name] ~= nil then
            return true
        end
    end
    local indoor = placeable.spec_indoorAreas
    return indoor ~= nil and indoor.areas ~= nil and next(indoor.areas) ~= nil
end

-- Vodorovná vzdálenost bodu od kryté plochy placeable (rovnoběžník startNode, widthNode, heightNode jako vanilla IndoorAreas).
function SprayDroneCase.getAreaDistance(area, x, z)
    local sx, _, sz = getWorldTranslation(area.start)
    local wx, _, wz = getWorldTranslation(area.width)
    local hx, _, hz = getWorldTranslation(area.height)
    local ax, az, bx, bz = wx - sx, wz - sz, hx - sx, hz - sz
    local det = ax * bz - az * bx
    if math.abs(det) < 1e-6 then
        return MathUtil.vector2Length(x - sx, z - sz)
    end
    local dx, dz = x - sx, z - sz
    local u = math.clamp((dx * bz - dz * bx) / det, 0, 1)
    local v = math.clamp((ax * dz - az * dx) / det, 0, 1)
    return MathUtil.vector2Length(x - (sx + u * ax + v * bx), z - (sz + u * az + v * bz))
end

-- Nejmenší vzdálenost (x, z) od budovy: od krytých ploch, jinak od kořene placeable.
function SprayDroneCase.getPlaceableDistance(placeable, x, z)
    local best = math.huge
    local indoor = placeable.spec_indoorAreas
    for _, area in pairs(indoor ~= nil and indoor.areas or {}) do
        if area.start ~= nil and area.width ~= nil and area.height ~= nil then
            best = math.min(best, SprayDroneCase.getAreaDistance(area, x, z))
        end
    end
    if placeable.rootNode ~= nil and entityExists(placeable.rootNode) then
        local px, _, pz = getWorldTranslation(placeable.rootNode)
        best = math.min(best, MathUtil.vector2Length(x - px, z - pz))
    end
    return best
end

-- Vlastní budova farmy farmId do range m od (x, z), nebo nil.
function SprayDroneCase.findBuilding(x, z, farmId, range)
    local system = g_currentMission ~= nil and g_currentMission.placeableSystem or nil
    for _, placeable in ipairs(system ~= nil and system.placeables or {}) do
        if not placeable.isDeleted and placeable.getOwnerFarmId ~= nil and placeable:getOwnerFarmId() == farmId
            and SprayDroneCase.getIsBuilding(placeable) and SprayDroneCase.getPlaceableDistance(placeable, x, z) <= range then
            return placeable
        end
    end
    return nil
end

-- Vlek SprayDrone farmy s proudem z centrály (zapnutá, rozložený vlek, nafta) do range m od (x, z), nebo nil.
function SprayDroneCase.findGenerator(self, x, z, range)
    local vehicles = g_currentMission ~= nil and g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, vehicle in ipairs(vehicles) do
        local spec = vehicle ~= self and vehicle[SprayDroneStation.SPEC_NAME] or nil
        if spec ~= nil and not vehicle.isDeleted and not SprayDroneCase.getIsPortable(vehicle) and vehicle.rootNode ~= nil
            and g_currentMission.accessHandler:canFarmAccess(self:getOwnerFarmId(), vehicle) and SprayDroneStation.getHasPower(vehicle) then
            local vx, _, vz = getWorldTranslation(vehicle.rootNode)
            if MathUtil.vector2Length(vx - x, vz - z) <= range then
                return vehicle
            end
        end
    end
    return nil
end

-- Odkud se teď kufr nabíjí: SOURCE_* a vlek s centrálou (u SOURCE_GENERATOR). Budova má přednost (nic nepálí).
function SprayDroneCase.findSource(self)
    local x, _, z = getWorldTranslation(self.rootNode)
    if SprayDroneCase.findBuilding(x, z, self:getOwnerFarmId(), SprayDroneCase.CHARGE_RANGE) ~= nil then
        return SprayDroneCase.SOURCE_BUILDING, nil
    end
    local generator = SprayDroneCase.findGenerator(self, x, z, SprayDroneCase.CHARGE_RANGE)
    if generator ~= nil then
        return SprayDroneCase.SOURCE_GENERATOR, generator
    end
    return SprayDroneCase.SOURCE_NONE, nil
end

-- Baterie, které kufr teď nabíjí: v šachtě a v dronu, který sedí v kufru (nelétá); jen nenabité.
function SprayDroneCase.getChargingBatteries(self)
    local spec = SprayDroneDrones.getRoot(self)
    local docked = spec.isLinked and (spec.state == SprayDroneStation.STATE_PARKED or spec.state == SprayDroneStation.STATE_SERVICING)
    local list = {}
    for k, battery in ipairs(spec.batteries) do
        if battery.charge < spec.batteryCapacity and (battery.slot > 0 or (battery.slot == 0 and docked)) then
            table.insert(list, k)
        end
    end
    return list
end

-- Nabíjení kufru (server, místo SprayDroneStation.updatePower): zdroj se hledá jednou za SOURCE_CHECK_TIME, nabíjí se rychlostí nabíječky
-- vleku (chargeRate z <power> a baterie varianty), bez nafty.
function SprayDroneCase.updatePower(self, dt)
    local spec = getSpec(self)
    spec.caseSourceTimer = (spec.caseSourceTimer or 0) - dt
    -- let vybíjí jen spec.battery dronu; bez srovnání by pool (HUD, diody, nabíjení po přistání) držel nabití ze vzletu
    -- a nabíjení by do dronu zapsalo staré nabití zpět
    SprayDroneDrones.forEach(self, SprayDroneStation.syncDroneBatteryCharge)
    local charging = SprayDroneCase.getChargingBatteries(self)
    if spec.caseSourceTimer <= 0 then
        spec.caseSourceTimer = SprayDroneCase.SOURCE_CHECK_TIME
        local source, generator = SprayDroneCase.findSource(self)
        if source ~= spec.chargeSource then
            spec.chargeSource = source
            SprayDroneStation.markRouteDirty(self)
            self:raiseDirtyFlags(spec.dirtyFlag)
            SprayDroneSound.noteAction(string.format("kufr %s: zdroj nabíjení %s", tostring(self.id), g_i18n:getText(SprayDroneCase.SOURCE_TEXTS[source])))
        end
        if generator ~= nil and #charging > 0 then
            local gspec = SprayDroneDrones.getRoot(generator)
            gspec.caseLoads = gspec.caseLoads or {}
            gspec.caseLoads[self] = g_time + SprayDroneCase.LOAD_TIMEOUT
            generator:raiseActive()
        end
    end
    local running = spec.chargeSource ~= SprayDroneCase.SOURCE_NONE and #charging > 0
    if running then
        local s = dt * 0.001
        for _, k in ipairs(charging) do
            local battery = spec.batteries[k]
            battery.charge = math.min(battery.charge + spec.chargeRate * s, spec.batteryCapacity)
            if battery.slot == 0 and spec.droneBattery == k then
                spec.battery = battery.charge
            end
        end
        spec.powerSyncTimer = spec.powerSyncTimer - dt
        if spec.powerSyncTimer <= 0 then
            spec.powerSyncTimer = SprayDroneStation.POWER_SYNC_TIME
            self:raiseDirtyFlags(spec.dirtyFlag)
        end
    end
    if running ~= spec.generatorRunning or #charging ~= spec.numCharging then
        spec.generatorRunning = running
        spec.numCharging = #charging
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

-- Proč se baterie kufru nenabije (status konce mise), nil = nabíjí se.
function SprayDroneCase.getChargeBlocker(self)
    local spec = SprayDroneDrones.getRoot(self)
    if spec.chargeSource == nil or spec.chargeSource == SprayDroneCase.SOURCE_NONE then
        return SprayDroneStation.STATUS_NO_CHARGE
    end
    return nil
end

---------------------------------------------------------------------------------------------------
-- vizuál (server i klienti ze synchronizovaného stavu): baterie v šachtě kufru, nebo v dronu; kabel do zásuvky, když se nabíjí;
-- LED na čele = průměrné nabití baterií (po čtvrtinách, nejvyšší bliká při nabíjení). Chybějící uzly se přeskočí.

SprayDroneCase.LED_COUNT = 4

function SprayDroneCase.loadVisuals(self)
    local spec = getSpec(self)
    local get = SprayDroneStation.getMappedNode
    local v = { slotBatteries = {}, cable = get(self, "caseChargeCable"), leds = {}, shown = {} }
    for i = 1, spec.numBatterySlots do
        v.slotBatteries[i] = get(self, i == 1 and "caseBattery" or ("caseBattery" .. i))
    end
    v.droneBattery = spec.dronePrefix ~= nil and get(self, spec.dronePrefix .. "Battery") or nil
    for i = 1, SprayDroneCase.LED_COUNT do
        v.leds[i] = get(self, "caseChargeLed" .. (i - 1))
    end
    spec.caseVisuals = v
    SprayDroneCase.loadPickUpLock(self)
end

-- Průměrné nabití baterií kufru (šachty i dron) 0..1, nil = žádná baterie. LED na čele ho ukazují po čtvrtinách.
function SprayDroneCase.getAverageLevel(spec)
    if #spec.batteries == 0 then
        return nil
    end
    local sum = 0
    for _, battery in ipairs(spec.batteries) do
        sum = sum + math.clamp(battery.charge / spec.batteryCapacity, 0, 1)
    end
    return sum / #spec.batteries
end

local function show(v, key, node, visible)
    if node ~= nil and v.shown[key] ~= visible then
        v.shown[key] = visible
        setVisibility(node, visible)
    end
end

function SprayDroneCase.updateVisuals(self)
    local spec = getSpec(self)
    local v = spec.caseVisuals
    if v == nil then
        return
    end
    -- domov dronu jde s droneCarrier z pěny na podložku vedle kufru (animace víka): plán spočtený u zavřeného kufru je o kus vedle
    local open = self.getIsUnfolded ~= nil and self:getIsUnfolded()
    if open ~= v.lidOpen then
        v.lidOpen = open
        SprayDroneStation.markRouteDirty(self)
    end
    for i, node in pairs(v.slotBatteries) do
        show(v, "slot" .. i, node, SprayDroneStation.getBatteryInSlot(self, i) ~= nil)
    end
    show(v, "drone", v.droneBattery, spec.droneBattery ~= nil)
    show(v, "cable", v.cable, spec.generatorRunning == true)
    local level = SprayDroneCase.getAverageLevel(spec)
    local lit = level ~= nil and math.max(math.ceil(level * SprayDroneCase.LED_COUNT - 0.001), 1) or 0
    local blinkOn = math.floor(g_time / 500) % 2 == 0
    for i, node in ipairs(v.leds) do
        show(v, "led" .. i, node, i < lit or (i == lit and (not spec.generatorRunning or blinkOn)))
    end
end

---------------------------------------------------------------------------------------------------
-- texty

-- Řádek baterie a řádek zdroje nabíjení (HUD u kufru, karta plánovače).
function SprayDroneCase.getPowerTexts(self)
    local spec = SprayDroneDrones.getRoot(self)
    local parts = {}
    for _, battery in ipairs(spec.batteries) do
        local text = string.format("%.0f %%", battery.charge / spec.batteryCapacity * 100)
        if spec.generatorRunning and battery.charge < spec.batteryCapacity then
            text = text .. " " .. g_i18n:getText("sdt_hud_charging")
        end
        table.insert(parts, text)
    end
    if #parts == 0 then
        table.insert(parts, "-")
    end
    local source = spec.chargeSource or SprayDroneCase.SOURCE_NONE
    return string.format(g_i18n:getText("sdt_case_battery"), table.concat(parts, ", ")),
        string.format(g_i18n:getText("sdt_case_source"), g_i18n:getText(SprayDroneCase.SOURCE_TEXTS[source]), SprayDroneCase.CHARGE_RANGE)
end

-- Řádky v nápovědě u hráče pěšky do ACTIVATE_DISTANCE od kufru (klient): baterie, zdroj nabíjení, stav dronu.
function SprayDroneCase.drawNearTexts(self)
    local player = g_localPlayer
    if player == nil or g_gui:getIsGuiVisible() or (player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil) then
        return
    end
    local px, py, pz = player:getPosition()
    if px == nil then
        return
    end
    local x, y, z = getWorldTranslation(self.rootNode)
    if MathUtil.vector3Length(px - x, py - y, pz - z) > SprayDroneCase.ACTIVATE_DISTANCE + 0.5 then
        return
    end
    local battery, source = SprayDroneCase.getPowerTexts(self)
    g_currentMission:addExtraPrintText(battery)
    g_currentMission:addExtraPrintText(source)
    local spec = getSpec(self)
    if spec.hasDrone then
        g_currentMission:addExtraPrintText(string.format(g_i18n:getText("sdt_hud_drone"), SprayDroneStation.getDroneStateName(self)))
    end
    if not SprayDroneCase.getIsClosed(self) then
        g_currentMission:addExtraPrintText(g_i18n:getText("sdt_case_closeToCarry"))
    end
end

---------------------------------------------------------------------------------------------------
-- otevřený kufr nejde zvednout ani nést: víko otevřené nebo v pohybu, podložka venku, dron na ní nebo ve vzduchu. Kufr je pallet
-- (supportsPickUp), takže stačí obalit getCanBePickedUp; na korbu se bez zvednutí nedostane. Fyzika se nezamyká (kinematický kufr
-- by na korbě jedoucího auta visel ve vzduchu), odtlačený kufr za letu hlídá MOVE_TOLERANCE (přeruší misi).

-- Je víko zavřené a v klidu?
function SprayDroneCase.getIsClosed(self)
    if self.spec_foldable == nil or self.getToggledFoldDirection == nil then
        return true
    end
    if SprayDroneCase.getIsLidOpening(self) then
        return false
    end
    return not (self.getIsAnimationPlaying ~= nil and self:getIsAnimationPlaying("caseLidAnim"))
end

function SprayDroneCase.loadPickUpLock(self)
    local canBePickedUp = self.getCanBePickedUp
    if canBePickedUp == nil then
        return
    end
    self.getCanBePickedUp = function(vehicle, byPlayer)
        if not SprayDroneCase.getIsClosed(vehicle) then
            return false
        end
        return canBePickedUp(vehicle, byPlayer)
    end
end

---------------------------------------------------------------------------------------------------
-- víko (pěšky): R otevře / zavře; zavřít jde jen s dronem doma (SprayDroneStation.getIsFoldAllowed). R u kufru dělá vždy jen jedno:
-- když hráč míří na baterii (šachta, baterie v dronu) nebo u ní stojí do SprayDroneBatterySlots.CASE_TAKE_DISTANCE, vyndá ji
-- (SprayDroneBatterySlotsActivatable) a víko se nenabízí; jinak R ovládá víko.

function SprayDroneCase.loadActivatable(self)
    local spec = getSpec(self)
    if self.isClient and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        spec.caseActivatable = SprayDroneCaseActivatable.new(self)
        g_currentMission.activatableObjectsSystem:addActivatable(spec.caseActivatable)
    end
end

function SprayDroneCase.deleteActivatable(self)
    local spec = getSpec(self)
    if spec ~= nil and spec.caseActivatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(spec.caseActivatable)
        spec.caseActivatable = nil
    end
end

-- Otevřít (true) nebo zavřít víko, jako vanilla Foldable.actionEventFold; vrací text varování, když to nejde.
function SprayDroneCase.setLidOpen(self, open)
    local foldable = self.spec_foldable
    if foldable == nil or not foldable.hasFoldingParts then
        return "sdt_pad_unknown"
    end
    local direction = open and foldable.turnOnFoldDirection or -foldable.turnOnFoldDirection
    local allowed, warning = self:getIsFoldAllowed(direction, false)
    if not allowed then
        return warning
    end
    self:setFoldState(direction, open)
    return nil
end

-- Je víko otevřené, nebo se otevírá?
function SprayDroneCase.getIsLidOpening(self)
    local foldable = self.spec_foldable
    return foldable ~= nil and self:getToggledFoldDirection() ~= foldable.turnOnFoldDirection
end

SprayDroneCaseActivatable = {}
local SprayDroneCaseActivatable_mt = Class(SprayDroneCaseActivatable)

function SprayDroneCaseActivatable.new(vehicle)
    local self = setmetatable({}, SprayDroneCaseActivatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_case_open")
    return self
end

function SprayDroneCaseActivatable:getIsActivatable()
    local player = g_localPlayer
    if player == nil or (player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil) then
        return false
    end
    local vehicle = self.vehicle
    if vehicle.isDeleted or vehicle.rootNode == nil or not entityExists(vehicle.rootNode) or g_gui:getIsGuiVisible() then
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
    if MathUtil.vector3Length(px - x, py - y, pz - z) > SprayDroneCase.ACTIVATE_DISTANCE then
        return false
    end
    local slots = SprayDroneDrones.getRoot(vehicle).batterySlots
    if slots ~= nil and slots.activatable ~= nil and slots.activatable:evaluate() == "take" then
        return false
    end
    -- řádky stavu kreslí onUpdate kufru, který bez hráče spí
    vehicle:raiseActive()
    local open = SprayDroneCase.getIsLidOpening(vehicle)
    self.activateText = g_i18n:getText(open and "sdt_case_close" or "sdt_case_open")
    if self.eventId ~= nil then
        g_inputBinding:setActionEventText(self.eventId, self.activateText)
    end
    return g_currentMission.accessHandler:canFarmAccess(g_currentMission:getFarmId(), vehicle)
end

function SprayDroneCaseActivatable:registerCustomInput(inputContext)
    local _
    _, self.eventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_OBJECT, self, self.run, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(self.eventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(self.eventId, true)
    g_inputBinding:setActionEventText(self.eventId, self.activateText)
    SprayDroneLink.setSelected(self, true)
end

function SprayDroneCaseActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    SprayDroneLink.setSelected(self, false)
    self.eventId = nil
end

function SprayDroneCaseActivatable:run()
    local vehicle = self.vehicle
    local open = not SprayDroneCase.getIsLidOpening(vehicle)
    SprayDroneSound.noteAction(string.format("kufr %s: R pěšky, %s víko", tostring(vehicle.id), open and "otevřít" or "zavřít"))
    local warning = SprayDroneCase.setLidOpen(vehicle, open)
    if warning ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:hasText(warning) and g_i18n:getText(warning) or warning, 2000)
    end
end

function SprayDroneCaseActivatable:getDistance(x, y, z)
    local nx, ny, nz = getWorldTranslation(self.vehicle.rootNode)
    return MathUtil.vector3Length(x - nx, y - ny, z - nz)
end

function SprayDroneCaseActivatable:activate() end

function SprayDroneCaseActivatable:deactivate() end

function SprayDroneCaseActivatable:draw() end
