-- Dron jako předmět (objects/drone/drone<S|M|L|K>.xml, vehicle type sdtDrone = pallet + tahle specializace): složený dron, který jde koupit zvlášť, nést v rukou
-- a nasadit na plošinu vleku (SprayDronePadSlots, docs/NAVRH-dron-predmet.md, etapa 1). Předmět je hloupý: nese jen jméno varianty (shoduje se s <drone name> ve vleku)
-- a svou náplň v obyčejném fill unitu 1 (skenovací dron fill unit nemá); let a obsluhu řeší vlek, na jehož plošině dron žije.
-- Baterie jako předmět (objects/battery/battery<S|M|L|C|P>.xml, vehicle type sdtBattery, F4): nese velikost (#battery, shoduje se s typem baterií vleku
-- nebo kufru, spec.batteryVariant) a nabití ve fill unitu 1 (ELECTRICCHARGE 0..100), takže savegame a síť řeší vanilla FillUnit. Diody led(?) ukazují nabití.
-- Do šachty nabíječky ji vkládá a z ní vyndává SprayDroneBatterySlots.

SprayDroneItem = {}
SprayDroneItem.MOD_NAME = g_currentModName
SprayDroneItem.SPEC_NAME = string.format("spec_%s.sprayDroneItem", g_currentModName)
SprayDroneItem.BATTERY_UNIT = 1

function SprayDroneItem.prerequisitesPresent(specializations)
    return true
end

function SprayDroneItem.initSpecialization()
    local schema = Vehicle.xmlSchema
    schema:setXMLSpecializationType("SprayDroneItem")
    schema:register(XMLValueType.STRING, "vehicle.sprayDroneItem#variant", "Varianta dronu (jméno <drone name> ve vleku: S, M, L, K)")
    schema:register(XMLValueType.STRING, "vehicle.sprayDroneItem#battery", "Velikost baterie (typ baterií vleku nebo kufru: S, M, L, C, P); nabití je fill unit 1")
    schema:register(XMLValueType.NODE_INDEX, "vehicle.sprayDroneItem.led(?)#node", "Dioda nabití baterie (zdola nahoru)")
    schema:setXMLSpecializationType()
end

function SprayDroneItem.registerEventListeners(vehicleType)
    SpecializationUtil.registerEventListener(vehicleType, "onLoad", SprayDroneItem)
    SpecializationUtil.registerEventListener(vehicleType, "onLoadFinished", SprayDroneItem)
    SpecializationUtil.registerEventListener(vehicleType, "onFillUnitFillLevelChanged", SprayDroneItem)
end

function SprayDroneItem:onLoad(savegame)
    local spec = self[SprayDroneItem.SPEC_NAME]
    spec.variant = self.xmlFile:getValue("vehicle.sprayDroneItem#variant", "")
    spec.battery = self.xmlFile:getValue("vehicle.sprayDroneItem#battery", "")
    if spec.variant == "" and spec.battery == "" then
        Logging.xmlWarning(self.xmlFile, "SprayDroneItem: chybí vehicle.sprayDroneItem#variant nebo #battery")
    end
    spec.leds, spec.ledShown = {}, {}
    self.xmlFile:iterate("vehicle.sprayDroneItem.led", function(_, ledKey)
        local node = self.xmlFile:getValue(ledKey .. "#node", nil, self.components, self.i3dMappings)
        if node ~= nil then
            table.insert(spec.leds, node)
        end
    end)
end

function SprayDroneItem:onLoadFinished(savegame)
    SprayDroneItem.updateLeds(self)
end

function SprayDroneItem:onFillUnitFillLevelChanged(fillUnitIndex, fillLevelDelta)
    if fillUnitIndex == SprayDroneItem.BATTERY_UNIT then
        SprayDroneItem.updateLeds(self)
    end
end

-- Varianta dronu předmětu, nebo nil, když vozidlo není dronový předmět.
function SprayDroneItem.getVariant(vehicle)
    local spec = vehicle ~= nil and vehicle[SprayDroneItem.SPEC_NAME] or nil
    return spec ~= nil and spec.variant ~= "" and spec.variant or nil
end

-- Náplň dronového předmětu: litry a druh (0, UNKNOWN, když je prázdný nebo bez nádrže).
function SprayDroneItem.getFill(vehicle)
    if vehicle.spec_fillUnit == nil or vehicle:getFillUnitExists(1) == false then
        return 0, FillType.UNKNOWN
    end
    return vehicle:getFillUnitFillLevel(1), vehicle:getFillUnitFillType(1)
end

-- Velikost baterie předmětu (S / M / L / C / P), nebo nil, když vozidlo není baterie.
function SprayDroneItem.getBatterySize(vehicle)
    local spec = vehicle ~= nil and vehicle[SprayDroneItem.SPEC_NAME] or nil
    return spec ~= nil and spec.battery ~= nil and spec.battery ~= "" and spec.battery or nil
end

-- Nabití baterie předmětu (0..1).
function SprayDroneItem.getBatteryLevel(vehicle)
    local unit = SprayDroneItem.BATTERY_UNIT
    if vehicle.spec_fillUnit == nil or vehicle:getFillUnitExists(unit) == false then
        return 0
    end
    local capacity = vehicle:getFillUnitCapacity(unit)
    if capacity == nil or capacity <= 0 then
        return 0
    end
    return math.clamp(vehicle:getFillUnitFillLevel(unit) / capacity, 0, 1)
end

-- Server: nabití baterie předmětu na level (0..1).
function SprayDroneItem.setBatteryLevel(vehicle, level)
    local unit = SprayDroneItem.BATTERY_UNIT
    if vehicle.spec_fillUnit == nil or vehicle:getFillUnitExists(unit) == false then
        return
    end
    local delta = math.clamp(level, 0, 1) * vehicle:getFillUnitCapacity(unit) - vehicle:getFillUnitFillLevel(unit)
    if math.abs(delta) > 0.0001 then
        vehicle:addFillUnitFillLevel(vehicle:getOwnerFarmId(), unit, delta, FillType.ELECTRICCHARGE, ToolType.UNDEFINED, nil)
    end
end

-- Diody: počet rozsvícených podle nabití (aspoň jedna, dokud baterie není prázdná).
function SprayDroneItem.updateLeds(self)
    local spec = self[SprayDroneItem.SPEC_NAME]
    local count = spec ~= nil and #spec.leds or 0
    if count == 0 then
        return
    end
    local level = SprayDroneItem.getBatteryLevel(self)
    local lit = level > 0 and math.max(math.ceil(level * count - 0.001), 1) or 0
    for i, node in ipairs(spec.leds) do
        local show = i <= lit
        if spec.ledShown[i] ~= show then
            spec.ledShown[i] = show
            setVisibility(node, show)
        end
    end
end
