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
source(g_currentModDirectory .. "scripts/events/SprayDroneAreaEvent.lua")
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
SprayDroneStation.STATUS_OBSTACLE = 6
SprayDroneStation.STATUS_NO_AREA_PATH = 7
SprayDroneStation.STATUS_NO_FUEL = 8
SprayDroneStation.STATUS_NUM_BITS = 4

SprayDroneStation.STATUS_TEXTS = {
    [1] = "sdt_status_fieldDone",
    [2] = "sdt_status_trailerEmpty",
    [3] = "sdt_status_unreachable",
    [4] = "sdt_status_aborted",
    [5] = "sdt_status_notAllowed",
    [6] = "sdt_status_obstacle",
    [7] = "sdt_status_areaNoPath",
    [8] = "sdt_status_noFuel"
}

SprayDroneStation.STATE_TEXTS = {
    [0] = "sdt_state_parked",
    [1] = "sdt_state_flying",
    [2] = "sdt_state_returning",
    [3] = "sdt_state_servicing"
}

-- servis na plošině: nejméně SERVICE_TIME (dosednutí, obsluha), plnění čerpadlem a výměna baterie běží souběžně
SprayDroneStation.SERVICE_TIME = 5000
SprayDroneStation.RESUME_AFTER_LOAD_TIME = 3000
SprayDroneStation.MAX_SPARE_BATTERIES = 8
-- DJI DB1560: 30 Ah × 52,22 V; jen pro zobrazení v ukazateli naplnění (baterie se jinak počítá v sekundách letu)
SprayDroneStation.BATTERY_KWH = 1.567
SprayDroneStation.POWER_SYNC_TIME = 500
SprayDroneStation.ROUTE_REFRESH_TIME = 5000
SprayDroneStation.MAX_TRAILER_SPEED = 3

-- letová plocha: vlek smí stát nejvýš HOME_TOLERANCE m za jejím okrajem; návrat domů odkudkoli do RETURN_TOLERANCE
SprayDroneStation.HOME_TOLERANCE = 6
SprayDroneStation.RETURN_TOLERANCE = 50
SprayDroneStation.MAX_AREA_POINTS = SprayDroneAreaEvent.MAX_POINTS
SprayDroneStation.NO_PATH_HOME = 1
SprayDroneStation.NO_PATH_AREA = 2

-- roztočení vrtulí (vizuál, řídí se stavem letu, takže sedí i u klientů); ramena a listy se skládají s vlekem
SprayDroneStation.ROTOR_MAX_SPEED = 35
SprayDroneStation.ROTOR_SPINUP_TIME = 2
SprayDroneStation.ROTOR_SPINDOWN_TIME = 4
SprayDroneStation.ROTOR_PARK_SPEED = 3

-- dynamika letu
SprayDroneStation.TURN_SLOW_ANGLE = math.rad(30)
SprayDroneStation.TURN_SPEED = 1.5
SprayDroneStation.YAW_ACCELERATION = 3
SprayDroneStation.MIN_CREEP_SPEED = 0.2
SprayDroneStation.TILT_PER_SPEED = 0.009
SprayDroneStation.TILT_PER_ACCELERATION = 0.04
SprayDroneStation.MAX_TILT = math.rad(12)

-- pojistka za letu: paprsek dopředu na brzdnou dráhu + GUARD_MARGIN, při zásahu zastavit a vystoupat
SprayDroneStation.GUARD_MARGIN = 4
SprayDroneStation.GUARD_SIDE = 1.2
SprayDroneStation.GUARD_EXTRA_CLIMB = 2

-- fáze letu pro odběr baterie: svislá rychlost nad / pod hranicí = stoupání / klesání, pomalu vodorovně = vznášení
SprayDroneStation.BATTERY_VERTICAL_SPEED = 0.5
SprayDroneStation.BATTERY_HOVER_SPEED = 2

-- zvuk rotorů: výška a hlasitost podle otáček (0..1)
SprayDroneStation.SOUND_MIN_PITCH = 0.45
SprayDroneStation.SOUND_VOLUME_EXPONENT = 0.7

-- čáry ve světě (kruh dosahu, pole, trasa, přelety); přepíná je hráč lokálně akcí SDT_TOGGLE_LINES
SprayDroneStation.showWorldLines = true

SprayDroneStation.DEBUG_FLIGHT = false
SprayDroneStation.DEBUG_SOUND = false
SprayDroneStation.DEBUG_POWER = false
SprayDroneStation.DEBUG_INTERVAL = 500

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
    schema:register(XMLValueType.FLOAT, key .. "#batteryMinutes", "Výdrž baterie ve vodorovném letu s plnou nádrží (min)", 8)
    schema:register(XMLValueType.FLOAT, key .. "#droneMass", "Hmotnost dronu s baterií bez náplně (kg)", 52)
    schema:register(XMLValueType.FLOAT, key .. "#batteryHoverFactor", "Násobek odběru při vznášení a otáčení na místě", 1.15)
    schema:register(XMLValueType.FLOAT, key .. "#batteryClimbFactor", "Násobek odběru při stoupání", 1.4)
    schema:register(XMLValueType.FLOAT, key .. "#batteryDescentFactor", "Násobek odběru při klesání", 0.8)
    schema:register(XMLValueType.FLOAT, key .. "#batterySwapBelow", "Výměna baterie na vleku pod tímto podílem kapacity (0..1)", 0.3)
    schema:register(XMLValueType.FLOAT, key .. "#trailerFoldEnd", "Do kterého času skládání vleku (0 = rozloženo, 1 = složeno) se skládá dron", 0.5)
    schema:register(XMLValueType.FLOAT, key .. "#cruiseSpeed", "Rychlost přeletu (m/s)", 10)
    schema:register(XMLValueType.FLOAT, key .. "#sprayingSpeed", "Rychlost při postřiku (m/s)", 7)
    schema:register(XMLValueType.FLOAT, key .. "#climbSpeed", "Rychlost klesání (m/s)", 3)
    schema:register(XMLValueType.FLOAT, key .. "#ascentSpeed", "Rychlost stoupání (m/s)", 5)
    schema:register(XMLValueType.FLOAT, key .. "#acceleration", "Zrychlení a brzdění (m/s²)", 2.5)
    schema:register(XMLValueType.FLOAT, key .. "#yawSpeed", "Nejvyšší rychlost otáčení (°/s)", 90)
    schema:register(XMLValueType.FLOAT, key .. "#sprayHeight", "Výška postřiku nad terénem (m)", 3)
    schema:register(XMLValueType.FLOAT, key .. "#transitHeight", "Nejnižší výška přeletu nad terénem (m)", 12)
    schema:register(XMLValueType.FLOAT, key .. "#obstacleClearance", "Odstup přeletu nad překážkou (m)", 5)
    schema:register(XMLValueType.FLOAT, key .. "#maxTransitHeight", "Nejvyšší výška přeletu (m)", 60)
    schema:register(XMLValueType.FLOAT, key .. "#corridorHeight", "Nejnižší výška přeletu letovou plochou nad terénem (m)", 8)
    schema:register(XMLValueType.FLOAT, key .. "#usageScale", "Násobek spotřeby l/ha oproti vanilla", 1)
    schema:register(XMLValueType.FLOAT, key .. "#litersPerSecond", "Čerpadlo plnění dronu na plošině (l/s)", 1)
    schema:register(XMLValueType.FLOAT, key .. "#securedFoldTime", "Od kterého času skládání vleku (0..1) jsou úchyty dronu zavřené", 0.8)
    schema:register(XMLValueType.INT, key .. ".power#dieselFillUnitIndex", "Nádrž elektrocentrály (nafta)", 2)
    schema:register(XMLValueType.INT, key .. ".power#spareBatteries", "Počet náhradních baterií na vleku", 2)
    schema:register(XMLValueType.FLOAT, key .. ".power#chargeMinutes", "Nabití jedné baterie z 30 % na 95 % (min)", 10)
    schema:register(XMLValueType.FLOAT, key .. ".power#dieselPerHour", "Spotřeba centrály při nabíjení (l/h)", 2.2)
    schema:register(XMLValueType.FLOAT, key .. ".power#readyLevel", "Od jakého nabití (0..1) jde náhradní baterie do dronu", 0.95)
    schema:register(XMLValueType.FLOAT, key .. ".power#swapTime", "Výměna baterie (s)", 5)
    schema:register(XMLValueType.NODE_INDEX, key .. ".power.exhaust#node", "Výfuk centrály")
    schema:register(XMLValueType.STRING, key .. ".power.exhaust#filename", "i3d efektu výfuku")
    schema:register(XMLValueType.VECTOR_4, key .. ".power.exhaust#color", "Barva kouře (rgba)")
    schema:register(XMLValueType.FLOAT, key .. ".power.exhaust#scale", "Velikost kouře", 0.3)
    schema:register(XMLValueType.FLOAT, key .. ".navLights#intensity", "Svit LED ramen", 4)
    schema:register(XMLValueType.FLOAT, key .. ".navLights#lightScale", "Násobek barvy bodových světel LED z i3d", 0.3)
    schema:register(XMLValueType.FLOAT, key .. ".navLights#blinkPeriod", "Perioda blikání (s)", 1)
    schema:register(XMLValueType.FLOAT, key .. ".navLights#blinkOn", "Jak dlouho z periody LED svítí (s)", 0.5)
    schema:register(XMLValueType.NODE_INDEX, key .. ".navLight(?)#node", "LED ramene (materiál staticLight_vertex)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".navLight(?)#lightNode", "Bodové světlo LED")
    schema:register(XMLValueType.BOOL, key .. ".navLight(?)#blink", "Bliká (jinak svítí)", false)
    schema:register(XMLValueType.NODE_INDEX, key .. ".tilt#node", "Uzel náklonu dronu za letu")
    schema:register(XMLValueType.NODE_INDEX, key .. ".foldPart(?)#node", "Kloub dronu (rameno, list vrtule)")
    schema:register(XMLValueType.VECTOR_ROT, key .. ".foldPart(?)#foldedRot", "Natočení složeno")
    schema:register(XMLValueType.VECTOR_ROT, key .. ".foldPart(?)#unfoldedRot", "Natočení rozloženo")
    schema:register(XMLValueType.FLOAT, key .. ".foldPart(?)#startTime", "Začátek pohybu (0..1 rozložení)", 0)
    schema:register(XMLValueType.FLOAT, key .. ".foldPart(?)#endTime", "Konec pohybu (0..1 rozložení)", 1)
    schema:register(XMLValueType.NODE_INDEX, key .. ".rotor(?)#node", "Vrtule")
    schema:register(XMLValueType.INT, key .. ".rotor(?)#direction", "Směr otáčení (1 / -1)", 1)
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "rotor")
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "generator")
    EffectManager.registerEffectXMLPaths(schema, key .. ".effects")
    schema:register(XMLValueType.FLOAT, key .. ".effects#meshWidth", "Šířka sítě efektu postřiku ve zdrojovém i3d (m)", 1)
    schema:register(XMLValueType.FLOAT, key .. ".effects#meshHeight", "Výška sítě efektu postřiku ve zdrojovém i3d (m)", 1)
    schema:register(XMLValueType.FLOAT, key .. ".effects#nozzleY", "Výška trysek nad uzlem, ke kterému je efekt připojený (m)", 0)
    schema:register(XMLValueType.ANGLE, key .. ".effects#rotY", "Natočení efektu kolem svislé osy", 0)
    schema:setXMLSpecializationType()

    local savegame = Vehicle.xmlSchemaSavegame
    local saveKey = string.format("vehicles.vehicle(?).%s.sprayDroneStation", SprayDroneStation.MOD_NAME)
    savegame:register(XMLValueType.INT, saveKey .. "#fieldId", "Vybrané pole (farmland id)")
    savegame:register(XMLValueType.BOOL, saveKey .. "#missionActive", "Mise běží")
    savegame:register(XMLValueType.FLOAT, saveKey .. "#droneFillLevel", "Náplň dronu (l)")
    savegame:register(XMLValueType.STRING, saveKey .. "#droneFillType", "Druh náplně dronu")
    savegame:register(XMLValueType.FLOAT, saveKey .. "#battery", "Zbývající baterie (s)")
    savegame:register(XMLValueType.INT, saveKey .. "#chargingSlot", "Náhradní baterie na nabíječce (0 = žádná)")
    savegame:register(XMLValueType.BOOL, saveKey .. "#generatorEnabled", "Elektrocentrála zapnutá")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".spareBattery(?)#charge", "Nabití náhradní baterie (s)")
    savegame:register(XMLValueType.INT, saveKey .. ".flightArea(?)#fieldId", "Pole, ke kterému letová plocha patří")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".flightArea(?).point(?)#x", "Vrchol letové plochy (svět x)")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".flightArea(?).point(?)#z", "Vrchol letové plochy (svět z)")
end

function SprayDroneStation.registerFunctions(vehicleType)
    SpecializationUtil.registerFunction(vehicleType, "sprayDroneCommand", SprayDroneStation.sprayDroneCommand)
    SpecializationUtil.registerFunction(vehicleType, "getSprayDroneIsParked", SprayDroneStation.getSprayDroneIsParked)
    SpecializationUtil.registerFunction(vehicleType, "setSprayDroneFlightArea", SprayDroneStation.setSprayDroneFlightArea)
end

function SprayDroneStation.registerOverwrittenFunctions(vehicleType)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getIsEnterable", SprayDroneStation.getIsEnterable)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getIsFoldAllowed", SprayDroneStation.getIsFoldAllowed)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getFillLevelInformation", SprayDroneStation.getFillLevelInformation)
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
    spec.batteryCapacity = xml:getValue(key .. "#batteryMinutes", 8) * 60
    spec.droneMass = xml:getValue(key .. "#droneMass", 52)
    spec.hoverFactor = xml:getValue(key .. "#batteryHoverFactor", 1.15)
    spec.climbFactor = xml:getValue(key .. "#batteryClimbFactor", 1.4)
    spec.descentFactor = xml:getValue(key .. "#batteryDescentFactor", 0.8)
    spec.batterySwapBelow = xml:getValue(key .. "#batterySwapBelow", 0.3)
    spec.trailerFoldEnd = math.clamp(xml:getValue(key .. "#trailerFoldEnd", 0.5), 0.05, 1)
    spec.cruiseSpeed = xml:getValue(key .. "#cruiseSpeed", 10)
    spec.sprayingSpeed = xml:getValue(key .. "#sprayingSpeed", 7)
    spec.climbSpeed = xml:getValue(key .. "#climbSpeed", 3)
    spec.ascentSpeed = xml:getValue(key .. "#ascentSpeed", 5)
    spec.acceleration = xml:getValue(key .. "#acceleration", 2.5)
    spec.yawSpeed = math.rad(xml:getValue(key .. "#yawSpeed", 90))
    spec.sprayHeight = xml:getValue(key .. "#sprayHeight", 3)
    spec.transitHeight = xml:getValue(key .. "#transitHeight", 12)
    spec.obstacleClearance = xml:getValue(key .. "#obstacleClearance", 5)
    spec.maxTransitHeight = xml:getValue(key .. "#maxTransitHeight", 60)
    spec.corridorHeight = xml:getValue(key .. "#corridorHeight", 8)
    spec.usageScale = xml:getValue(key .. "#usageScale", 1)
    spec.batteryReserve = 30
    spec.pumpRate = math.max(xml:getValue(key .. "#litersPerSecond", 1), 0.01)
    spec.securedFoldTime = xml:getValue(key .. "#securedFoldTime", 0.8)

    -- elektrocentrála a náhradní baterie: nabíjecí rychlost je 65 % kapacity (30 % -> 95 %) za chargeMinutes
    local powerKey = key .. ".power"
    spec.dieselFillUnitIndex = xml:getValue(powerKey .. "#dieselFillUnitIndex", 2)
    spec.chargeRate = 0.65 * spec.batteryCapacity / (math.max(xml:getValue(powerKey .. "#chargeMinutes", 10), 0.1) * 60)
    spec.dieselPerSecond = xml:getValue(powerKey .. "#dieselPerHour", 2.2) / 3600
    spec.readyCharge = math.clamp(xml:getValue(powerKey .. "#readyLevel", 0.95), 0.1, 1) * spec.batteryCapacity
    spec.swapTime = xml:getValue(powerKey .. "#swapTime", 5) * 1000
    spec.spares = {}
    for k = 1, math.clamp(xml:getValue(powerKey .. "#spareBatteries", 2), 1, SprayDroneStation.MAX_SPARE_BATTERIES) do
        spec.spares[k] = spec.batteryCapacity
    end
    spec.chargingSlot = nil
    spec.generatorEnabled = true
    spec.generatorRunning = false
    spec.powerSyncTimer = 0
    spec.isPumping, spec.isSwapping, spec.waitingForCharge = false, false, false
    spec.swapTimer = 0
    spec.swapChecked, spec.swapPending = false, false

    spec.navLightIntensity = xml:getValue(key .. ".navLights#intensity", 4)
    spec.navBlinkPeriod = math.max(xml:getValue(key .. ".navLights#blinkPeriod", 1), 0.1) * 1000
    spec.navBlinkOn = xml:getValue(key .. ".navLights#blinkOn", 0.5) * 1000
    spec.navLights = {}
    local lightScale = xml:getValue(key .. ".navLights#lightScale", 0.3)
    xml:iterate(key .. ".navLight", function(_, lightKey)
        local node = xml:getValue(lightKey .. "#node", nil, self.components, self.i3dMappings)
        if node ~= nil then
            local light = { node = node, lightNode = xml:getValue(lightKey .. "#lightNode", nil, self.components, self.i3dMappings),
                blink = xml:getValue(lightKey .. "#blink", false), isOn = nil }
            if light.lightNode ~= nil then
                local r, g, b = getLightColor(light.lightNode)
                setLightColor(light.lightNode, r * lightScale, g * lightScale, b * lightScale)
            end
            table.insert(spec.navLights, light)
        end
    end)

    spec.tiltNode = xml:getValue(key .. ".tilt#node", nil, self.components, self.i3dMappings)
    spec.foldParts = {}
    xml:iterate(key .. ".foldPart", function(_, partKey)
        local node = xml:getValue(partKey .. "#node", nil, self.components, self.i3dMappings)
        local folded = xml:getValue(partKey .. "#foldedRot", nil, true)
        local unfolded = xml:getValue(partKey .. "#unfoldedRot", nil, true)
        if node ~= nil and folded ~= nil and unfolded ~= nil then
            table.insert(spec.foldParts, { node = node, folded = folded, unfolded = unfolded,
                startTime = xml:getValue(partKey .. "#startTime", 0), endTime = xml:getValue(partKey .. "#endTime", 1) })
        end
    end)
    spec.rotors = {}
    xml:iterate(key .. ".rotor", function(_, rotorKey)
        local node = xml:getValue(rotorKey .. "#node", nil, self.components, self.i3dMappings)
        if node ~= nil then
            table.insert(spec.rotors, { node = node, direction = xml:getValue(rotorKey .. "#direction", 1), angle = 0, appliedAngle = 0 })
        end
    end)
    spec.unfold = 0
    spec.appliedUnfold = -1
    spec.rotorSpeed = 0
    spec.rotorsParked = true
    spec.drainPos = nil
    spec.drainFactor = 0
    spec.massPerLiter = 1
    spec.soundPitch, spec.soundVolume = 0, 0

    spec.samples = {}
    if self.isClient then
        spec.samples.rotor = g_soundManager:loadSampleFromXML(xml, key .. ".sounds", "rotor", self.baseDirectory, self.components, 0,
            AudioGroup.VEHICLE, self.i3dMappings, self)
        spec.rotorVolumeScale = g_soundManager:getSampleVolumeScale(spec.samples.rotor)
        spec.effects = g_effectManager:loadEffect(xml, key .. ".effects", self.components, self, self.i3dMappings)
        SprayDroneStation.loadSprayEffectPlacement(self, xml, key .. ".effects")
        spec.samples.generator = g_soundManager:loadSampleFromXML(xml, key .. ".sounds", "generator", self.baseDirectory, self.components, 0,
            AudioGroup.VEHICLE, self.i3dMappings, self)
        SprayDroneStation.loadExhaust(self, xml, powerKey .. ".exhaust")
    end
    SprayDroneStation.applyNavLights(self, false)
    spec.sprayEffectsActive = false
    spec.lastSprayTime = -math.huge
    spec.tilt = { pitch = 0, roll = 0 }
    spec.lastWorldPos = nil
    spec.velocity = { x = 0, z = 0 }
    spec.worldAccel = { x = 0, z = 0 }
    spec.transitCache = {}
    spec.transitCacheSize = 0
    spec.flightAreas = {}
    spec.areaVersion = 0
    spec.corridor = nil
    spec.pathCache = {}
    spec.pathCacheSize = 0

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
    spec.speed = 0
    spec.yawRate = 0
    spec.moveDir = { x = 0, z = 0 }
    spec.airborne = false
    spec.avoidHeight = 0
    spec.avoidClimbTo = nil
    spec.batchHeight = spec.transitHeight
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
    spec.routeInfo = { time = 0, height = spec.transitHeight, tooHigh = false, transits = {} }

    spec.dirtyFlag = self:getNextDirtyFlag()

    if savegame ~= nil and not savegame.resetVehicles then
        local saveKey = savegame.key .. "." .. SprayDroneStation.MOD_NAME .. ".sprayDroneStation"
        spec.fieldId = savegame.xmlFile:getValue(saveKey .. "#fieldId", 0)
        spec.missionActive = savegame.xmlFile:getValue(saveKey .. "#missionActive", false)
        spec.droneFillLevel = savegame.xmlFile:getValue(saveKey .. "#droneFillLevel", 0)
        local fillTypeName = savegame.xmlFile:getValue(saveKey .. "#droneFillType")
        spec.droneFillType = g_fillTypeManager:getFillTypeIndexByName(fillTypeName) or FillType.UNKNOWN
        spec.battery = math.clamp(savegame.xmlFile:getValue(saveKey .. "#battery", spec.batteryCapacity), 0, spec.batteryCapacity)
        savegame.xmlFile:iterate(saveKey .. ".spareBattery", function(k, spareKey)
            if spec.spares[k] ~= nil then
                spec.spares[k] = math.clamp(savegame.xmlFile:getValue(spareKey .. "#charge", spec.batteryCapacity), 0, spec.batteryCapacity)
            end
        end)
        local slot = savegame.xmlFile:getValue(saveKey .. "#chargingSlot", 0)
        spec.chargingSlot = spec.spares[slot] ~= nil and slot or nil
        spec.generatorEnabled = savegame.xmlFile:getValue(saveKey .. "#generatorEnabled", true)
        savegame.xmlFile:iterate(saveKey .. ".flightArea", function(_, areaKey)
            local fieldId = savegame.xmlFile:getValue(areaKey .. "#fieldId")
            local points = {}
            savegame.xmlFile:iterate(areaKey .. ".point", function(_, pointKey)
                local x, z = savegame.xmlFile:getValue(pointKey .. "#x"), savegame.xmlFile:getValue(pointKey .. "#z")
                if x ~= nil and z ~= nil and #points < SprayDroneStation.MAX_AREA_POINTS then
                    table.insert(points, { x = x, z = z })
                end
            end)
            if fieldId ~= nil and #points >= 3 then
                spec.flightAreas[fieldId] = points
            end
        end)
        if spec.missionActive then
            -- po načtení dron stojí na vleku; misi obnoví servis, trasa se spočítá ze stavu pole
            spec.state = SprayDroneStation.STATE_SERVICING
            spec.serviceTimer = SprayDroneStation.RESUME_AFTER_LOAD_TIME
        end
    end
    -- Foldable má v onLoad čas skládání ze savegame (getFoldAnimTime), takže uložený rozložený vlek má dron rozložený hned
    spec.unfold = SprayDroneStation.getTrailerUnfold(self)
    SprayDroneStation.applyFold(self)
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
    xmlFile:setValue(key .. "#chargingSlot", spec.chargingSlot or 0)
    xmlFile:setValue(key .. "#generatorEnabled", spec.generatorEnabled)
    for k, charge in ipairs(spec.spares) do
        xmlFile:setValue(string.format("%s.spareBattery(%d)#charge", key, k - 1), charge)
    end
    local fieldIds = {}
    for fieldId in pairs(spec.flightAreas) do
        table.insert(fieldIds, fieldId)
    end
    table.sort(fieldIds)
    for i, fieldId in ipairs(fieldIds) do
        local areaKey = string.format("%s.flightArea(%d)", key, i - 1)
        xmlFile:setValue(areaKey .. "#fieldId", fieldId)
        for j, point in ipairs(spec.flightAreas[fieldId]) do
            local pointKey = string.format("%s.point(%d)", areaKey, j - 1)
            xmlFile:setValue(pointKey .. "#x", point.x)
            xmlFile:setValue(pointKey .. "#z", point.z)
        end
    end
end

function SprayDroneStation:onDelete()
    local spec = self[SprayDroneStation.SPEC_NAME]
    -- dron létající pod kořenem scény by po smazání vleku zůstal ve světě
    if spec ~= nil and spec.node ~= nil and not spec.isLinked and entityExists(spec.parent) then
        SprayDroneStation.attachDrone(self)
    end
    if spec ~= nil and spec.samples ~= nil then
        g_soundManager:deleteSamples(spec.samples)
    end
    if spec ~= nil and spec.effects ~= nil then
        g_effectManager:deleteEffects(spec.effects)
    end
    if spec ~= nil and spec.exhaust ~= nil and spec.exhaust.requestId ~= nil then
        g_i3DManager:releaseSharedI3DFile(spec.exhaust.requestId)
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
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.rotorSpeed > 0 or not spec.rotorsParked then
        -- složené listy musí mířit podél ramene: nejdřív doběh a dotočení vrtulí do klidové polohy
        return false, g_i18n:getText("sdt_warning_rotorsSpinning")
    end
    return superFunc(self, direction, onAiTurnOn)
end

-- Vanilla ukazatel naplnění vpravo dole: za nádrží vleku a naftou ještě nádrž dronu, baterie v dronu a náhradní
-- baterie (ELECTRICCHARGE v kWh jako u elektrických strojů; kapacita baterie DB1560 je BATTERY_KWH).
function SprayDroneStation:getFillLevelInformation(superFunc, display)
    superFunc(self, display)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local _, fillType = SprayDroneStation.getSprayType(self)
    if spec.droneFillLevel > 0 and spec.droneFillType ~= FillType.UNKNOWN then
        fillType = spec.droneFillType
    end
    display:addFillLevel(fillType, spec.droneFillLevel, spec.tankCapacity, 0, false, nil, g_i18n:getText("sdt_fill_droneTank"),
        g_i18n:getText(SprayDroneStation.getIsDroneSecured(self) and "sdt_fill_secured" or "sdt_fill_inDrone"))
    -- ukazatel slučuje řádky stejného druhu náplně se stejným doplňkovým textem a ukáže jen pár řádků: baterie
    -- v dronu zvlášť, náhradní baterie jako souhrn sady s procenty po kusech
    local kwh = SprayDroneStation.BATTERY_KWH / spec.batteryCapacity
    display:addFillLevel(FillType.ELECTRICCHARGE, spec.battery * kwh, SprayDroneStation.BATTERY_KWH, 2, false, nil,
        g_i18n:getText("sdt_fill_battery"), g_i18n:getText("sdt_fill_inDrone"))
    local total, parts = 0, {}
    for _, charge in ipairs(spec.spares) do
        total = total + charge
        table.insert(parts, string.format("%.0f", charge / spec.batteryCapacity * 100))
    end
    local info = table.concat(parts, "/") .. " %"
    if spec.generatorRunning then
        info = info .. " " .. g_i18n:getText("sdt_fill_charging")
    end
    display:addFillLevel(FillType.ELECTRICCHARGE, total * kwh, SprayDroneStation.BATTERY_KWH * #spec.spares, 2, false, nil,
        g_i18n:getText("sdt_fill_spares"), info)
end

-- Dron stojí na složeném vleku a úchyty na lyžinách jsou zavřené (čas skládání za securedFoldTime).
function SprayDroneStation.getIsDroneSecured(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return spec.isLinked and self:getFoldAnimTime() >= spec.securedFoldTime - 0.001
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

-- Směr vleku; na plošině dron sedí nosem po směru jízdy.
function SprayDroneStation.getHomeYaw(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local dx, _, dz = localDirectionToWorld(spec.parent, 0, 0, 1)
    return MathUtil.getYRotationFromDirection(dx, dz)
end

-- Výška přeletu nad terénem pro úsek, nejméně minHeight (raycasty, výsledek se pamatuje), a jestli je nad maxTransitHeight.
function SprayDroneStation.getTransitHeight(self, x1, z1, x2, z2, minHeight)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local key = string.format("%d:%d:%d:%d:%d", math.floor(x1 + 0.5), math.floor(z1 + 0.5), math.floor(x2 + 0.5), math.floor(z2 + 0.5),
        math.floor(minHeight * 10 + 0.5))
    local h = spec.transitCache[key]
    if h == nil then
        if spec.transitCacheSize > 512 then
            spec.transitCache, spec.transitCacheSize = {}, 0
        end
        h = SprayDroneRoute.getClearHeight(x1, z1, x2, z2, minHeight, spec.obstacleClearance, spec.maxTransitHeight)
        spec.transitCache[key] = h
        spec.transitCacheSize = spec.transitCacheSize + 1
    end
    return h, h > spec.maxTransitHeight
end

function SprayDroneStation.getFlightArea(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return spec.flightAreas[spec.fieldId]
end

-- Letová plocha pole fieldId (nil nebo méně než 3 body = smazat). Jde eventem na server a od něj ke všem klientům.
function SprayDroneStation:setSprayDroneFlightArea(fieldId, points, noEventSend)
    SprayDroneAreaEvent.sendEvent(self, fieldId, points, noEventSend)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if points ~= nil and #points >= 3 then
        local copy = {}
        for i = 1, math.min(#points, SprayDroneStation.MAX_AREA_POINTS) do
            copy[i] = { x = points[i].x, z = points[i].z }
        end
        spec.flightAreas[fieldId] = copy
    else
        spec.flightAreas[fieldId] = nil
    end
    spec.areaVersion = spec.areaVersion + 1
    spec.routeDirty = true
end

-- Graf letové plochy vybraného pole s vlekem na jeho místě; nil, když pole plochu nemá.
function SprayDroneStation.getCorridor(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local area = spec.flightAreas[spec.fieldId]
    local field = area ~= nil and SprayDroneRoute.getFieldById(spec.fieldId) or nil
    if field == nil then
        return nil
    end
    local c = spec.corridor
    if c == nil or c.version ~= spec.areaVersion or c.fieldId ~= spec.fieldId then
        c = SprayDroneRoute.newCorridor(area, SprayDroneRoute.getPolygon(field))
        c.version, c.fieldId = spec.areaVersion, spec.fieldId
        spec.corridor = c
    end
    local hx, hz = SprayDroneStation.getHomePosition(self)
    if c.home == nil or MathUtil.vector2Length(c.home.x - hx, c.home.z - hz) > 1 then
        SprayDroneRoute.setCorridorHome(c, hx, hz, SprayDroneStation.HOME_TOLERANCE)
        spec.pathCache, spec.pathCacheSize = {}, 0
    end
    return c
end

-- Cesta letovou plochou z bodu na vlek (pamatuje se po buňkách grid m), nil bez plochy nebo když cesta není.
function SprayDroneStation.getHomePath(self, x, z, grid, tolerance)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local c = SprayDroneStation.getCorridor(self)
    if c == nil then
        return nil
    end
    grid = grid or 1
    tolerance = tolerance or SprayDroneStation.HOME_TOLERANCE
    local key = string.format("%d:%d:%d:%d", math.floor(x / grid + 0.5), math.floor(z / grid + 0.5), grid, tolerance)
    local path = spec.pathCache[key]
    if path == nil then
        if spec.pathCacheSize > 1024 then
            spec.pathCache, spec.pathCacheSize = {}, 0
        end
        path = SprayDroneRoute.getCorridorPathHome(c, x, z, tolerance) or false
        spec.pathCache[key] = path
        spec.pathCacheSize = spec.pathCacheSize + 1
    end
    return path or nil
end

-- Přelet po bodech points: výška každého úseku z raycastů, nejméně minHeight.
function SprayDroneStation.makeTransitPlan(self, points, minHeight)
    local heights, height, tooHigh = {}, 0, false
    for k = 1, #points - 1 do
        local a, b = points[k], points[k + 1]
        local h, over = SprayDroneStation.getTransitHeight(self, a.x, a.z, b.x, b.z, minHeight)
        heights[k] = h
        height = math.max(height, h)
        tooHigh = tooHigh or over
    end
    return { points = points, heights = heights, height = height, tooHigh = tooHigh, length = SprayDroneRoute.getPathLength(points) }
end

-- Přelet mezi vlekem a bodem (x, z): bez letové plochy přímo ve výšce nad překážkami, s plochou nejkratší cestou
-- v ní nízko (corridorHeight). Vrací nil a NO_PATH_*, když cesta plochou není.
function SprayDroneStation.getTransit(self, x, z, outbound, tolerance)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local points, minHeight
    local c = SprayDroneStation.getCorridor(self)
    if c == nil then
        local hx, hz = SprayDroneStation.getHomePosition(self)
        points, minHeight = { { x = x, z = z }, { x = hx, z = hz } }, spec.transitHeight
    else
        if not c.homeOk then
            return nil, SprayDroneStation.NO_PATH_HOME
        end
        local path = SprayDroneStation.getHomePath(self, x, z, 1, tolerance)
        if path == nil then
            return nil, SprayDroneStation.NO_PATH_AREA
        end
        points, minHeight = { { x = x, z = z } }, spec.corridorHeight
        for k = 2, #path do
            table.insert(points, path[k])
        end
    end
    if outbound then
        local reversed = {}
        for k = #points, 1, -1 do
            table.insert(reversed, points[k])
        end
        points = reversed
    end
    return SprayDroneStation.makeTransitPlan(self, points, minHeight)
end

-- Rozložení dronu (0..1) z času skládání vleku: dron se skládá na začátku skládání (0..trailerFoldEnd), takže
-- při rozkládání vleku se rozloží až v jeho druhé části. Plyne ze stavu Foldable, sedí tedy i po načtení a u klientů.
function SprayDroneStation.getTrailerUnfold(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return math.clamp(1 - self:getFoldAnimTime() / spec.trailerFoldEnd, 0, 1)
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

-- Hmotnost litru náplně dronu (kg); FillType.massPerLiter je v t/l.
function SprayDroneStation.getMassPerLiter(self)
    local _, fillTypeIndex = SprayDroneStation.getSprayType(self)
    local fillType = g_fillTypeManager:getFillTypeByIndex(fillTypeIndex)
    if fillType ~= nil and fillType.massPerLiter ~= nil and fillType.massPerLiter > 0 then
        return fillType.massPerLiter * 1000
    end
    return 1
end

function SprayDroneStation.getFlightParams(self, sprayType, restHeight)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local massPerLiter = SprayDroneStation.getMassPerLiter(self)
    return {
        droneMass = spec.droneMass,
        massPerLiter = massPerLiter,
        fullMass = spec.droneMass + spec.tankCapacity * massPerLiter,
        batteryCapacity = spec.batteryCapacity,
        batterySwapBelow = spec.batterySwapBelow,
        hoverFactor = spec.hoverFactor,
        climbFactor = spec.climbFactor,
        descentFactor = spec.descentFactor,
        workWidth = spec.workWidth,
        sprayHeight = spec.sprayHeight,
        transitHeight = spec.transitHeight,
        cruiseSpeed = spec.cruiseSpeed,
        sprayingSpeed = spec.sprayingSpeed,
        climbSpeed = spec.climbSpeed,
        ascentSpeed = spec.ascentSpeed,
        acceleration = spec.acceleration,
        yawSpeed = spec.yawSpeed,
        litersPerMeter = SprayDroneStation.getLitersPerMeter(self, sprayType),
        batteryReserve = spec.batteryReserve,
        restHeight = restHeight,
        homeYaw = SprayDroneStation.getHomeYaw(self),
        getTransit = function(x, z, outbound)
            return SprayDroneStation.getTransit(self, x, z, outbound)
        end,
        getHomePath = SprayDroneStation.getCorridor(self) ~= nil and function(x, z)
            return SprayDroneStation.getHomePath(self, x, z)
        end or nil
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
    local info = spec.routeInfo
    local area = SprayDroneStation.getFlightArea(self)
    -- roztočení před každou dávkou a servis na plošině (plnění, výměna baterie, čekání na nabití; ramena jsou rozložená s vlekem)
    local serviceTime = spec.numBatches * SprayDroneStation.ROTOR_SPINUP_TIME + (info.serviceTime or 0)
    return {
        numBatches = spec.numBatches,
        waitMinutes = (info.waitTime or 0) / 60,
        serviceMinutes = (info.serviceTime or 0) / 60,
        dieselUsed = info.dieselUsed or 0,
        diesel = self:getFillUnitFillLevel(spec.dieselFillUnitIndex),
        noFuel = info.noFuel == true,
        fuelRunsOut = info.fuelRunsOut == true,
        clipped = spec.routeClipped,
        partlyOutOfRange = partlyOutOfRange,
        minutes = (info.time + serviceTime) / 60,
        batteryPercent = (info.maxEnergy or 0) / spec.batteryCapacity * 100,
        batterySwaps = info.batterySwaps or 0,
        batteryMinutesFull = spec.batteryCapacity / 60,
        batteryMinutesEmpty = spec.batteryCapacity / 60 / SprayDroneRoute.drainFactor(SprayDroneStation.getFlightParams(self, nil, 0), 0),
        transitHeight = math.min(info.height, spec.maxTransitHeight),
        obstacleRaised = info.height > (area ~= nil and spec.corridorHeight or spec.transitHeight) + 0.01,
        tooHigh = info.tooHigh,
        maxTransitHeight = spec.maxTransitHeight,
        area = area,
        noPath = info.noPath,
        firstOut = info.firstOut or 0,
        firstBack = info.firstBack or 0,
        transitLength = info.transitLength or 0,
        areaHa = length * spec.workWidth / 10000,
        liters = length * SprayDroneStation.getLitersPerMeter(self, sprayType),
        availableLiters = trailerLiters + droneLiters,
        trailerLiters = trailerLiters,
        droneLiters = droneLiters,
        fillTypeTitle = g_fillTypeManager:getFillTypeTitleByIndex(fillType) or "-"
    }
end

-- Stav a parametry servisu pro odhad plánovače (SprayDroneRoute.splitIntoBatches).
function SprayDroneStation.getPowerParams(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local _, fillType = SprayDroneStation.getSprayType(self)
    return {
        spares = spec.spares,
        slot = spec.chargingSlot,
        diesel = self:getFillUnitFillLevel(spec.dieselFillUnitIndex),
        startFill = spec.droneFillType == fillType and spec.droneFillLevel or 0,
        capacity = spec.batteryCapacity,
        chargeRate = spec.chargeRate,
        dieselPerSecond = spec.dieselPerSecond,
        readyCharge = spec.readyCharge,
        swapTime = spec.swapTime * 0.001,
        pumpRate = spec.pumpRate,
        minService = SprayDroneStation.SERVICE_TIME * 0.001
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
    spec.routeInfo = { time = 0, height = spec.transitHeight, tooHigh = false, transits = {} }
    if spec.fieldId == 0 then
        return
    end
    local legs, sprayType = SprayDroneStation.buildLegs(self)
    if #legs == 0 then
        return
    end
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local p = SprayDroneStation.getFlightParams(self, sprayType, restHeight)
    p.power = SprayDroneStation.getPowerParams(self)
    spec.drawLegs, spec.numBatches, spec.routeClipped, spec.routeInfo =
        SprayDroneRoute.splitIntoBatches(legs, hx, hz, spec.tankCapacity, spec.battery, p)
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

    elseif command == SprayDroneCommandEvent.SET_GENERATOR then
        spec.generatorEnabled = fieldId ~= 0
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
        if state ~= SprayDroneStation.STATE_SERVICING then
            spec.isPumping, spec.isSwapping, spec.waitingForCharge, spec.swapTimer = false, false, false, 0
        end
        spec.swapChecked, spec.swapPending = false, false
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

-- Čerpadlo z nádrže vleku do dronu na plošině (pumpRate l/s). Vrací, jestli se ještě plní.
function SprayDroneStation.pumpDrone(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local trailerFillType = self:getFillUnitFillType(spec.fillUnitIndex)
    local trailerLevel = self:getFillUnitFillLevel(spec.fillUnitIndex)
    local filling = false
    if trailerLevel > 0 then
        if spec.droneFillType ~= trailerFillType and spec.droneFillLevel > 0 then
            -- jiný přípravek ve vleku: zbytek v dronu se nemíchá, zahodí se
            spec.droneFillLevel = 0
        end
        local amount = math.min(spec.tankCapacity - spec.droneFillLevel, trailerLevel, spec.pumpRate * dt * 0.001)
        if amount > 0.0001 then
            local applied = -self:addFillUnitFillLevel(self:getOwnerFarmId(), spec.fillUnitIndex, -amount, trailerFillType, ToolType.UNDEFINED, nil)
            spec.droneFillLevel = spec.droneFillLevel + applied
            spec.droneFillType = trailerFillType
            filling = applied > 0 and spec.droneFillLevel < spec.tankCapacity - 0.001
        end
    end
    if spec.droneFillLevel <= 0 then
        spec.droneFillType = FillType.UNKNOWN
    end
    return filling
end

-- Servis dronu na plošině (server): plnění a výměna baterie souběžně, pak další dávka, nebo zaparkovat.
function SprayDroneStation.updateService(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.serviceTimer = spec.serviceTimer - dt
    spec.swapTimer = math.max(spec.swapTimer - dt, 0)
    local pumping = SprayDroneStation.pumpDrone(self, dt)
    -- výměna baterie se rozhodne hned na začátku servisu, aby běžela souběžně s plněním
    if spec.missionActive and not spec.swapChecked then
        spec.swapChecked = true
        spec.swapPending = SprayDroneStation.getWantsSwap(self)
    end
    if spec.swapPending and spec.swapTimer <= 0 then
        local _, charge = SprayDroneRoute.getBestSpare(spec.spares)
        if charge >= spec.readyCharge - 0.01 then
            spec.swapPending = false
            SprayDroneStation.swapBattery(self)
        end
    end
    local swapping = spec.swapTimer > 0
    if pumping ~= spec.isPumping or swapping ~= spec.isSwapping then
        spec.isPumping, spec.isSwapping = pumping, swapping
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
    SprayDroneStation.setWaitingForCharge(self, spec.missionActive and spec.swapPending and not pumping and spec.serviceTimer <= 0)
    spec.powerSyncTimer = spec.powerSyncTimer - dt
    if pumping and spec.powerSyncTimer <= 0 then
        spec.powerSyncTimer = SprayDroneStation.POWER_SYNC_TIME
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
    if spec.serviceTimer > 0 or pumping or swapping then
        return
    end
    if not spec.missionActive then
        SprayDroneStation.setState(self, SprayDroneStation.STATE_PARKED)
        return
    end
    if spec.swapPending then
        -- čeká na nabití náhradní baterie; bez nafty se už nenabije
        if self:getFillUnitFillLevel(spec.dieselFillUnitIndex) <= 0 then
            SprayDroneStation.endMission(self, SprayDroneStation.STATUS_NO_FUEL)
        end
        return
    end
    SprayDroneStation.startNextBatch(self)
    self:raiseDirtyFlags(spec.dirtyFlag)
end

-- Bude další dávka potřebovat výměnu baterie? Plánuje s nádrží, jaká bude po doplnění.
function SprayDroneStation.getWantsSwap(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local legs, sprayType = SprayDroneStation.buildLegs(self)
    if #legs == 0 or sprayType == nil then
        return false
    end
    local trailerFillType = self:getFillUnitFillType(spec.fillUnitIndex)
    local droneFill = spec.droneFillType == trailerFillType and spec.droneFillLevel or 0
    local fill = math.min(spec.tankCapacity, droneFill + self:getFillUnitFillLevel(spec.fillUnitIndex))
    if fill < 0.5 then
        return false
    end
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local p = SprayDroneStation.getFlightParams(self, sprayType, restHeight)
    local _, spareCharge = SprayDroneRoute.getBestSpare(spec.spares)
    local wps, _, _, _, _, battery = SprayDroneRoute.planBatchWithSwap(legs, 1, 0, hx, hz, fill, spec.battery, p,
        math.max(spareCharge, spec.readyCharge))
    return wps ~= nil and battery ~= spec.battery
end

function SprayDroneStation.setWaitingForCharge(self, waiting)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.waitingForCharge ~= waiting then
        spec.waitingForCharge = waiting
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

-- Vybitá baterie z dronu jde na místo nejnabitější náhradní, ta do dronu.
function SprayDroneStation.swapBattery(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local slot, charge = SprayDroneRoute.getBestSpare(spec.spares)
    if SprayDroneStation.DEBUG_FLIGHT then
        Logging.info("SDT výměna baterie: %.0f %% z dronu na nabíječku, do dronu %.0f %% (náhradní %d)",
            spec.battery / spec.batteryCapacity * 100, charge / spec.batteryCapacity * 100, slot)
    end
    spec.spares[slot] = spec.battery
    spec.battery = charge
    spec.swapTimer = spec.swapTime
    spec.isSwapping = true
    self:raiseDirtyFlags(spec.dirtyFlag)
end

-- Nabíjení běží, když je centrála zapnutá, je nafta a některá náhradní baterie není plná; nezávisle na misi,
-- složení vleku i na tom, jestli v něm někdo sedí.
function SprayDroneStation.getCanCharge(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return spec.generatorEnabled and self:getFillUnitFillLevel(spec.dieselFillUnitIndex) > 0
        and SprayDroneRoute.getChargingSlot(spec.spares, spec.chargingSlot, spec.batteryCapacity) ~= nil
end

-- Elektrocentrála (server): nabíjí jednu náhradní baterii (jedna nabíječka) a spotřebovává naftu, jen když nabíjí.
function SprayDroneStation.updatePower(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local running = SprayDroneStation.getCanCharge(self)
    local slot = SprayDroneRoute.getChargingSlot(spec.spares, spec.chargingSlot, spec.batteryCapacity)
    if running then
        local s = dt * 0.001
        spec.spares[slot] = math.min(spec.spares[slot] + spec.chargeRate * s, spec.batteryCapacity)
        self:addFillUnitFillLevel(self:getOwnerFarmId(), spec.dieselFillUnitIndex, -spec.dieselPerSecond * s, FillType.DIESEL,
            ToolType.UNDEFINED, nil)
        spec.powerSyncTimer = spec.powerSyncTimer - dt
        if spec.powerSyncTimer <= 0 then
            spec.powerSyncTimer = SprayDroneStation.POWER_SYNC_TIME
            self:raiseDirtyFlags(spec.dirtyFlag)
        end
    end
    if running ~= spec.generatorRunning or slot ~= spec.chargingSlot then
        spec.generatorRunning = running
        spec.chargingSlot = slot
        self:raiseDirtyFlags(spec.dirtyFlag)
        if SprayDroneStation.DEBUG_POWER then
            Logging.info("SDT centrála %s, nabíječka: baterie %s, nafta %.2f l", running and "běží" or "stojí", tostring(slot),
                self:getFillUnitFillLevel(spec.dieselFillUnitIndex))
        end
    end
    if SprayDroneStation.DEBUG_POWER and running then
        spec.powerDebugTimer = (spec.powerDebugTimer or 0) - dt
        if spec.powerDebugTimer <= 0 then
            spec.powerDebugTimer = 10000
            local parts = {}
            for k, charge in ipairs(spec.spares) do
                table.insert(parts, string.format("%d: %.1f %%", k, charge / spec.batteryCapacity * 100))
            end
            Logging.info("SDT nabíjení (čas hry %.1f s): %s | dron %.1f %% | nafta %.3f l", g_time * 0.001, table.concat(parts, ", "),
                spec.battery / spec.batteryCapacity * 100, self:getFillUnitFillLevel(spec.dieselFillUnitIndex))
        end
    end
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
    -- výměna baterie při servisu: jen když je pod batterySwapBelow nebo na dávku nestačí (jako ruční výměna na poli);
    -- náhradní musí být nabitá aspoň na readyCharge, jinak dron na plošině čeká, než se nabije
    local _, spareCharge = SprayDroneRoute.getBestSpare(spec.spares)
    local wps, _, _, _, info, battery = SprayDroneRoute.planBatchWithSwap(legs, 1, 0, hx, hz, spec.droneFillLevel, spec.battery, p,
        math.max(spareCharge, spec.readyCharge))
    if wps ~= nil and battery ~= spec.battery then
        if spareCharge < spec.readyCharge - 0.01 then
            if self:getFillUnitFillLevel(spec.dieselFillUnitIndex) <= 0 then
                SprayDroneStation.endMission(self, SprayDroneStation.STATUS_NO_FUEL)
            else
                spec.swapPending = true
            end
            return
        end
        SprayDroneStation.swapBattery(self)
        return
    end
    if wps == nil then
        local status = SprayDroneStation.STATUS_UNREACHABLE
        if info.tooHigh then
            status = SprayDroneStation.STATUS_OBSTACLE
        elseif info.noPath ~= nil then
            status = SprayDroneStation.STATUS_NO_AREA_PATH
        end
        SprayDroneStation.endMission(self, status)
        return
    end

    spec.path = wps
    spec.wpIndex = 1
    spec.pos.x, spec.pos.z, spec.pos.h = hx, hz, restHeight
    spec.pos.yaw = SprayDroneStation.getHomeYaw(self)
    spec.speed, spec.yawRate = 0, 0
    spec.airborne = false
    spec.avoidHeight, spec.avoidClimbTo = 0, nil
    spec.batchHeight = info.height
    spec.sprayFrom = nil
    spec.batch = spec.batch + 1
    spec.litersPerMeter = p.litersPerMeter
    spec.massPerLiter = p.massPerLiter
    spec.sprayTypeIndex = sprayType.index
    spec.flightTime, spec.estimatedTime = 0, info.time
    spec.batteryAtStart, spec.estimatedEnergy = spec.battery, info.energy
    if SprayDroneStation.DEBUG_FLIGHT then
        local function describe(plan)
            local parts = {}
            for k, pt in ipairs(plan.points) do
                table.insert(parts, string.format("(%.0f %.0f)%s", pt.x, pt.z, plan.heights[k] ~= nil and string.format(" %.0fm", plan.heights[k]) or ""))
            end
            return string.format("%.0f m: %s", plan.length, table.concat(parts, " "))
        end
        Logging.info("SDT dávka %d: letová plocha %s, odhad %.1f s, baterie %.1f s z %.1f s, náplň %.1f l, maska překážek 0x%x", spec.batch,
            SprayDroneStation.getFlightArea(self) ~= nil and "ano" or "ne", info.time, info.energy, spec.battery, spec.droneFillLevel,
            SprayDroneRoute.OBSTACLE_MASK)
        Logging.info("SDT dávka %d: tam %s", spec.batch, describe(info.outPlan))
        Logging.info("SDT dávka %d: zpět %s", spec.batch, describe(info.backPlan))
    end
    SprayDroneStation.setState(self, SprayDroneStation.STATE_FLYING)
end

function SprayDroneStation.startReturnHome(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if not spec.airborne then
        -- ještě na plošině (rozkládá se): nevzlétat, rovnou zpět do servisu
        spec.path = nil
        SprayDroneStation.setState(self, SprayDroneStation.STATE_SERVICING)
        spec.serviceTimer = 0
        return
    end
    SprayDroneStation.flushSpray(self)
    local pos = spec.pos
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    -- nejdřív zabrzdit po směru letu, pak stoupat
    local brake = spec.speed * spec.speed / (2 * spec.acceleration)
    local bx, bz = pos.x + spec.moveDir.x * brake, pos.z + spec.moveDir.z * brake
    local plan = SprayDroneStation.getTransit(self, bx, bz, false, SprayDroneStation.RETURN_TOLERANCE)
    if plan == nil then
        plan = SprayDroneStation.makeTransitPlan(self, { { x = bx, z = bz }, { x = hx, z = hz } }, spec.transitHeight)
    end
    plan.heights[1] = math.max(plan.heights[1], pos.h)
    spec.batchHeight = math.max(plan.height, pos.h)
    spec.path = { { x = bx, z = bz, h = pos.h, speed = math.max(spec.speed, 1) } }
    SprayDroneRoute.appendTransitWaypoints(spec.path, plan, SprayDroneStation.getFlightParams(self, nil, restHeight), false)
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

-- Spotřeba baterie na návrat z aktuální polohy s aktuální náplní (zabrzdit, vystoupat, přelet, přistát).
function SprayDroneStation.getReturnEnergy(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local p = SprayDroneStation.getFlightParams(self, nil, restHeight)
    local pos = spec.pos
    local h = math.max(spec.batchHeight, pos.h)
    -- volá se každý snímek: cesta plochou se pamatuje po 10m buňkách, výška přeletu je ta z plánu dávky
    local path = SprayDroneStation.getHomePath(self, pos.x, pos.z, 10, SprayDroneStation.RETURN_TOLERANCE)
        or { { x = pos.x, z = pos.z }, { x = hx, z = hz } }
    local _, _, _, transit = SprayDroneRoute.transitTime({ points = path, height = h }, h, pos.yaw, p, spec.droneFillLevel)
    return (spec.speed / spec.acceleration
        + SprayDroneRoute.moveTime(h - pos.h, spec.ascentSpeed, spec.acceleration, 0, 0) * spec.climbFactor
        + SprayDroneRoute.landingTime(h - restHeight, p) * spec.descentFactor) * SprayDroneRoute.drainFactor(p, spec.droneFillLevel)
        + transit
end

-- Odběr baterie za snímek podle fáze letu (z pohybu od minulého snímku) a hmotnosti náplně.
function SprayDroneStation.drainBattery(self, s)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local pos = spec.pos
    local phase = 1
    local last = spec.drainPos
    if last ~= nil and s > 0 then
        local vertical = (pos.h - last.h) / s
        local horizontal = MathUtil.vector2Length(pos.x - last.x, pos.z - last.z) / s
        if vertical > SprayDroneStation.BATTERY_VERTICAL_SPEED then
            phase = spec.climbFactor
        elseif vertical < -SprayDroneStation.BATTERY_VERTICAL_SPEED then
            phase = spec.descentFactor
        elseif horizontal < SprayDroneStation.BATTERY_HOVER_SPEED then
            phase = spec.hoverFactor
        end
    end
    spec.drainPos = { x = pos.x, z = pos.z, h = pos.h }
    local p = { droneMass = spec.droneMass, massPerLiter = spec.massPerLiter, fullMass = spec.droneMass + spec.tankCapacity * spec.massPerLiter }
    spec.drainFactor = SprayDroneRoute.drainFactor(p, spec.droneFillLevel, phase)
    spec.battery = math.max(spec.battery - spec.drainFactor * s, 0)
end

-- Rychlost, na kterou má dron zpomalit v cílovém bodě waypointu: podle úhlu k dalšímu úseku
-- (rovně = plná, pravý úhel a víc = zastavit), před přistáním a na konci trasy 0.
function SprayDroneStation.getExitSpeed(self, wp, tx, tz, th, dx, dz, dh, dist)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local nextWp = spec.path[spec.wpIndex + 1]
    if wp.land or nextWp == nil or dist < 0.01 then
        return 0
    end
    local nx, nz, nh = nextWp.x, nextWp.z, nextWp.h
    if nextWp.home then
        nx, nz = SprayDroneStation.getHomePosition(self)
    end
    local ex, ez, eh = nx - tx, nz - tz, nh - th
    local nextDist = math.sqrt(ex * ex + ez * ez + eh * eh)
    if nextDist < 0.01 then
        return 0
    end
    local cos = (dx * ex + dz * ez + dh * eh) / (dist * nextDist)
    return math.min(wp.speed, nextWp.speed) * math.clamp((cos - 0.3) / 0.7, 0, 1)
end

-- Pojistka: paprsky po směru letu (střed a boky dronu) na délku length (brzdná dráha + rezerva).
function SprayDroneStation.getIsPathBlocked(self, x, y, z, dirX, dirZ, length)
    local sideX, sideZ = dirZ * SprayDroneStation.GUARD_SIDE, -dirX * SprayDroneStation.GUARD_SIDE
    for s = -1, 1 do
        if SprayDroneRoute.castRay(x + sideX * s, y, z + sideZ * s, dirX, 0, dirZ, length) then
            return true
        end
    end
    return false
end

function SprayDroneStation.updateYaw(self, targetYaw, s)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local desired = 0
    if targetYaw ~= nil then
        desired = math.clamp(MathUtil.getAngleDifference(targetYaw, spec.pos.yaw) * 3, -spec.yawSpeed, spec.yawSpeed)
    end
    local maxChange = SprayDroneStation.YAW_ACCELERATION * s
    spec.yawRate = spec.yawRate + math.clamp(desired - spec.yawRate, -maxChange, maxChange)
    spec.pos.yaw = spec.pos.yaw + spec.yawRate * s
end

function SprayDroneStation.updateFlight(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local wp = spec.path ~= nil and spec.path[spec.wpIndex]
    if not wp then
        SprayDroneStation.startReturnHome(self)
        return
    end

    local s = dt * 0.001
    local pos = spec.pos
    if not spec.airborne then
        -- na plošině: vzlétne až s rozloženými rameny a roztočenými vrtulemi
        if spec.unfold < 1 or spec.rotorSpeed < SprayDroneStation.ROTOR_MAX_SPEED * 0.95 then
            return
        end
        SprayDroneStation.detachDrone(self)
        pos.yaw = SprayDroneStation.getHomeYaw(self)
        spec.airborne = true
        spec.drainPos = nil
    end

    spec.flightTime = spec.flightTime + s
    SprayDroneStation.drainBattery(self, s)
    if spec.state == SprayDroneStation.STATE_FLYING then
        local trailerMoving = self:getLastSpeed() > SprayDroneStation.MAX_TRAILER_SPEED
        if trailerMoving then
            spec.missionActive = false
        end
        if trailerMoving or spec.droneFillLevel <= 0 or spec.battery < SprayDroneStation.getReturnEnergy(self) + 5 then
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
    if not wp.land then
        th = th + spec.avoidHeight
    end

    local acc = spec.acceleration
    local dx, dz, dh = tx - pos.x, tz - pos.z, th - pos.h
    local horizontal = math.sqrt(dx * dx + dz * dz)
    local dist = math.sqrt(horizontal * horizontal + dh * dh)
    local dirX, dirZ = 0, 0
    if horizontal > 0.01 then
        dirX, dirZ = dx / horizontal, dz / horizontal
    end
    local terrainY = getTerrainHeightAtWorldPos(g_terrainNode, pos.x, 0, pos.z)

    local heading = horizontal > 0.5 and MathUtil.getYRotationFromDirection(dx, dz) or nil
    if wp.home and horizontal <= 0.5 then
        heading = SprayDroneStation.getHomeYaw(self)
    end
    SprayDroneStation.updateYaw(self, heading, s)

    -- pojistka: překážka před dronem -> zabrzdit, stoupat, dokud paprsek neprojde, a ještě GUARD_EXTRA_CLIMB;
    -- pak letět dál o avoidHeight výš, dokud pod dronem něco je
    if spec.avoidClimbTo == nil and horizontal > 0.5 and not wp.land then
        local length = spec.speed * spec.speed / (2 * acc) + SprayDroneStation.GUARD_MARGIN
        if SprayDroneStation.getIsPathBlocked(self, pos.x, terrainY + pos.h, pos.z, dirX, dirZ, length) then
            spec.avoidClimbTo = math.huge
            spec.avoidRayLength = length
            spec.avoidDir = { x = dirX, z = dirZ }
        end
    end
    if spec.avoidClimbTo ~= nil then
        spec.speed = math.max(spec.speed - 2 * acc * s, 0)
        pos.x, pos.z = pos.x + spec.moveDir.x * spec.speed * s, pos.z + spec.moveDir.z * spec.speed * s
        if spec.speed < 0.3 then
            pos.h = pos.h + spec.ascentSpeed * s
            if spec.avoidClimbTo == math.huge and not SprayDroneStation.getIsPathBlocked(self, pos.x, terrainY + pos.h, pos.z,
                spec.avoidDir.x, spec.avoidDir.z, spec.avoidRayLength) then
                spec.avoidClimbTo = pos.h + SprayDroneStation.GUARD_EXTRA_CLIMB
            end
            spec.avoidHeight = math.max(spec.avoidHeight, pos.h - (th - spec.avoidHeight))
            if pos.h >= spec.avoidClimbTo then
                spec.avoidClimbTo = nil
                if SprayDroneStation.DEBUG_FLIGHT then
                    Logging.info("SDT pojistka: překážka před dronem, vystoupal o %.1f m na %.1f m", spec.avoidHeight, pos.h)
                end
            end
        end
        SprayDroneStation.setDroneWorldPosition(self, pos.x, getTerrainHeightAtWorldPos(g_terrainNode, pos.x, 0, pos.z) + pos.h, pos.z, pos.yaw)
        SprayDroneStation.debugFlight(self, dt)
        self:raiseDirtyFlags(spec.dirtyFlag)
        return
    end
    if spec.avoidHeight > 0 and not SprayDroneRoute.castRay(pos.x, terrainY + pos.h, pos.z, 0, -1, 0, spec.avoidHeight + 1) then
        spec.avoidHeight = math.max(spec.avoidHeight - spec.climbSpeed * 0.5 * s, 0)
    end

    local vMax = wp.speed
    if wp.land then
        vMax = math.min(vMax, SprayDroneRoute.LANDING_MIN_SPEED + SprayDroneRoute.LANDING_SLOPE * dist)
    end
    if horizontal > 0.5 and math.abs(MathUtil.getAngleDifference(heading, pos.yaw)) > SprayDroneStation.TURN_SLOW_ANGLE then
        vMax = math.min(vMax, SprayDroneStation.TURN_SPEED)
    end
    local vExit = SprayDroneStation.getExitSpeed(self, wp, tx, tz, th, dx, dz, dh, dist)
    local target = math.min(vMax, math.sqrt(vExit * vExit + 2 * acc * dist))
    if spec.speed < target then
        spec.speed = math.min(spec.speed + acc * s, target)
    else
        spec.speed = math.max(spec.speed - 2 * acc * s, target)
    end
    local step = math.max(spec.speed, SprayDroneStation.MIN_CREEP_SPEED) * s
    local reached = step >= dist
    local f = reached and 1 or step / dist
    pos.x, pos.z, pos.h = pos.x + dx * f, pos.z + dz * f, pos.h + dh * f
    if dist > 0.01 then
        spec.moveDir.x, spec.moveDir.z = dx / dist, dz / dist
    end

    local y = getTerrainHeightAtWorldPos(g_terrainNode, pos.x, 0, pos.z) + pos.h
    SprayDroneStation.setDroneWorldPosition(self, pos.x, y, pos.z, pos.yaw)
    SprayDroneStation.debugFlight(self, dt)

    if wp.spray and spec.state == SprayDroneStation.STATE_FLYING then
        spec.isSpraying = true
        if spec.droneFillLevel > 0 then
            spec.lastSprayTime = g_time
        end
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
            if SprayDroneStation.DEBUG_FLIGHT then
                Logging.info("SDT dávka %d: let %.1f s, odhad %.1f s, baterie spotřeba %.1f s (odhad %.1f s), zbývá %.0f %%", spec.batch,
                    spec.flightTime, spec.estimatedTime or 0, (spec.batteryAtStart or 0) - spec.battery, spec.estimatedEnergy or 0,
                    spec.battery / spec.batteryCapacity * 100)
            end
            SprayDroneStation.attachDrone(self)
            spec.path = nil
            spec.speed, spec.yawRate, spec.avoidHeight, spec.avoidClimbTo = 0, 0, 0, nil
            spec.airborne = false
            SprayDroneStation.setState(self, SprayDroneStation.STATE_SERVICING)
            spec.serviceTimer = SprayDroneStation.SERVICE_TIME
        end
    end
    self:raiseDirtyFlags(spec.dirtyFlag)
end

function SprayDroneStation.debugFlight(self, dt)
    if not SprayDroneStation.DEBUG_FLIGHT then
        return
    end
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.debugTimer = (spec.debugTimer or 0) - dt
    if spec.debugTimer <= 0 then
        spec.debugTimer = SprayDroneStation.DEBUG_INTERVAL
        local wp = spec.path[spec.wpIndex] or {}
        local kind = wp.land and "land" or (wp.spray and "spray" or (wp.home and "home" or "move"))
        Logging.info("SDT t=%.1f wp=%d/%d %s x=%.1f z=%.1f v=%.2f h=%.1f yaw=%.0f pitch=%.1f roll=%.1f avoid=%.1f%s | baterie %.1f %% odběr %.2f náplň %.1f l | zvuk %.2f / %.2f",
            spec.flightTime, spec.wpIndex, #spec.path, kind, spec.pos.x, spec.pos.z, spec.speed, spec.pos.h, math.deg(spec.pos.yaw) % 360,
            math.deg(spec.tilt.pitch), math.deg(spec.tilt.roll), spec.avoidHeight, spec.avoidClimbTo ~= nil and " STOP" or "",
            spec.battery / spec.batteryCapacity * 100, spec.drainFactor, spec.droneFillLevel, spec.soundPitch, spec.soundVolume)
    end
end

-- Rozložení ramen a listů podle spec.unfold (0 = složeno, 1 = rozloženo), jen když se změnilo.
function SprayDroneStation.applyFold(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.appliedUnfold == spec.unfold then
        return
    end
    spec.appliedUnfold = spec.unfold
    for _, part in ipairs(spec.foldParts) do
        local t = math.clamp((spec.unfold - part.startTime) / math.max(part.endTime - part.startTime, 0.001), 0, 1)
        t = t * t * (3 - 2 * t)
        local a, b = part.folded, part.unfolded
        setRotation(part.node, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t)
    end
end

-- Vizuál dronu, který plyne ze stavu letu a vleku (server i klienti stejně): rozložení podle skládání vleku,
-- roztočení a doběh vrtulí, náklon podle zrychlení a rychlosti, zvuk rotorů.
function SprayDroneStation.updateDroneParts(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local s = dt * 0.001
    local flying = spec.state == SprayDroneStation.STATE_FLYING or spec.state == SprayDroneStation.STATE_RETURNING

    local maxSpeed = SprayDroneStation.ROTOR_MAX_SPEED
    if flying and spec.unfold >= 1 then
        spec.rotorSpeed = math.min(spec.rotorSpeed + maxSpeed / SprayDroneStation.ROTOR_SPINUP_TIME * s, maxSpeed)
    else
        spec.rotorSpeed = math.max(spec.rotorSpeed - maxSpeed / SprayDroneStation.ROTOR_SPINDOWN_TIME * s, 0)
    end
    -- po doběhu se vrtule pomalu dotočí do klidové polohy (úhel 0), jinak by složené listy nemířily podél ramene
    local rotorsParked = true
    for _, rotor in ipairs(spec.rotors) do
        if spec.rotorSpeed > 0 then
            rotor.angle = (rotor.angle + rotor.direction * spec.rotorSpeed * s) % (2 * math.pi)
        elseif rotor.angle ~= 0 then
            local remaining = rotor.direction > 0 and 2 * math.pi - rotor.angle or rotor.angle
            local step = SprayDroneStation.ROTOR_PARK_SPEED * s
            rotor.angle = step >= remaining and 0 or rotor.angle + rotor.direction * step
        end
        if rotor.angle ~= rotor.appliedAngle then
            rotor.appliedAngle = rotor.angle
            setRotation(rotor.node, 0, rotor.angle, 0)
        end
        rotorsParked = rotorsParked and rotor.angle == 0
    end

    -- ve vzduchu zůstává rozložený (vlek se za letu složit nedá)
    if spec.isLinked then
        spec.unfold = SprayDroneStation.getTrailerUnfold(self)
    end
    SprayDroneStation.applyFold(self)
    spec.rotorsParked = rotorsParked

    SprayDroneStation.updateTilt(self, dt)
    SprayDroneStation.updateRotorSound(self, dt)
    SprayDroneStation.updateSprayEffects(self)
    SprayDroneStation.applyNavLights(self, flying or spec.rotorSpeed > 0)
    SprayDroneStation.updateGenerator(self)
end

-- LED ramen: svítí, dokud je dron zapnutý (letí nebo se točí vrtule); blikající LED podle navBlinkPeriod. Svit jde
-- přes parametr lightIds0 materiálu staticLight_vertex (barva je v barvě vrcholů), bodové světlo se zapíná s ním.
function SprayDroneStation.applyNavLights(self, powered)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local blinkOn = g_time % spec.navBlinkPeriod < spec.navBlinkOn
    for _, light in ipairs(spec.navLights) do
        local isOn = powered and (not light.blink or blinkOn)
        if light.isOn ~= isOn then
            light.isOn = isOn
            setShaderParameter(light.node, "lightIds0", isOn and spec.navLightIntensity or 0, 0, 0, 0, false)
            if light.lightNode ~= nil then
                setVisibility(light.lightNode, isOn)
            end
        end
    end
end

-- Výfuk centrály (vanilla efekt výfuku z $data), při nabíjení viditelný a bez náklonu.
function SprayDroneStation.loadExhaust(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local linkNode = xml:getValue(key .. "#node", nil, self.components, self.i3dMappings)
    local filename = xml:getValue(key .. "#filename")
    if linkNode == nil or filename == nil then
        return
    end
    local i3dNode, requestId = g_i3DManager:loadSharedI3DFile(Utils.getFilename(filename, self.baseDirectory), false, false)
    if i3dNode == nil or i3dNode == 0 then
        Logging.xmlWarning(xml, "SprayDroneStation: efekt výfuku '%s' se nenačetl", filename)
        return
    end
    local node = getChildAt(i3dNode, 0)
    link(linkNode, node)
    delete(i3dNode)
    setVisibility(node, false)
    spec.exhaust = { node = node, requestId = requestId, color = xml:getValue(key .. "#color", nil, true) or { 0.1, 0.1, 0.1, 0.3 },
        scale = xml:getValue(key .. "#scale", 0.3), shown = false }
end

function SprayDroneStation.updateGenerator(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local running = spec.generatorRunning
    local sample = spec.samples.generator
    if sample ~= nil and g_soundManager:getIsSamplePlaying(sample) ~= running then
        if running then
            g_soundManager:playSample(sample)
        else
            g_soundManager:stopSample(sample)
        end
    end
    local exhaust = spec.exhaust
    if exhaust ~= nil and exhaust.shown ~= running then
        exhaust.shown = running
        setVisibility(exhaust.node, running)
        if running then
            local c = exhaust.color
            setShaderParameter(exhaust.node, "param", 0, 0, 0, exhaust.scale, false)
            setShaderParameter(exhaust.node, "exhaustColor", c[1], c[2], c[3], c[4], false)
        end
    end
end

-- Rozměry pro efekty postřiku; umístí je až placeSprayEffects, protože síť z $data se načítá asynchronně.
function SprayDroneStation.loadSprayEffectPlacement(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.sprayEffectPlacement = {
        meshWidth = xml:getValue(key .. "#meshWidth", 1),
        meshHeight = xml:getValue(key .. "#meshHeight", 1),
        nozzleY = xml:getValue(key .. "#nozzleY", 0),
        rotY = xml:getValue(key .. "#rotY", 0)
    }
end

-- Efekty postřiku (vanilla síť postřikovače) roztáhne na workWidth vedle sebe napříč dronem a na výšku od trysek
-- k zemi ve výšce postřiku; spodek za terénem shader sám ořízne (isFadeAboveTerrain). Vrací, jestli jsou sítě načtené.
function SprayDroneStation.placeSprayEffects(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local effects, pl = spec.effects, spec.sprayEffectPlacement
    for _, effect in ipairs(effects) do
        if effect.node == nil then
            return false
        end
    end
    -- poloha a směr v souřadnicích kořene dronu (x napříč, z po směru letu), uzel připojení může být natočený jinak
    local width = spec.workWidth / #effects
    for i, effect in ipairs(effects) do
        local node = effect.node
        local parent = getParent(node)
        local _, parentY, _ = localToLocal(parent, spec.node, 0, 0, 0)
        local sy = (spec.sprayHeight + parentY + pl.nozzleY + 0.5) / pl.meshHeight
        local cy = parentY + pl.nozzleY - pl.meshHeight * 0.5 * sy
        setTranslation(node, localToLocal(spec.node, parent, -spec.workWidth * 0.5 + (i - 0.5) * width, cy, 0))
        local zx, zy, zz = localDirectionToLocal(spec.node, parent, math.sin(pl.rotY), 0, math.cos(pl.rotY))
        local ux, uy, uz = localDirectionToLocal(spec.node, parent, 0, 1, 0)
        setDirection(node, zx, zy, zz, ux, uy, uz)
        setScale(node, width / pl.meshWidth, sy, 1)
        if SprayDroneStation.DEBUG_FLIGHT then
            local x, y, z = localToLocal(node, spec.node, 0, 0, 0)
            local ax, ay, az = localDirectionToLocal(node, spec.node, 1, 0, 0)
            Logging.info("SDT postřik: efekt %d pod '%s' na %.2f %.2f %.2f (v dronu), osa x %.2f %.2f %.2f, měřítko %.2f %.2f", i,
                getName(parent), x, y, z, ax, ay, az, width / pl.meshWidth, sy)
        end
    end
    return true
end

-- Postřik je vidět, když dron na řádku opravdu stříká (server) nebo to tak hlásí stav letu (klient).
function SprayDroneStation.updateSprayEffects(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if self.isServer then
        spec.sprayEffectsActive = spec.state == SprayDroneStation.STATE_FLYING and spec.lastSprayTime + 150 > g_time
    end
    if spec.effects == nil or #spec.effects == 0 or spec.sprayEffectsActive == spec.sprayEffectsShown then
        return
    end
    if spec.sprayEffectsActive and not spec.sprayEffectsPlaced then
        spec.sprayEffectsPlaced = SprayDroneStation.placeSprayEffects(self)
        if not spec.sprayEffectsPlaced then
            return
        end
    end
    spec.sprayEffectsShown = spec.sprayEffectsActive
    if spec.sprayEffectsActive then
        local _, fillType = SprayDroneStation.getSprayType(self)
        g_effectManager:setEffectTypeInfo(spec.effects, fillType)
        g_effectManager:startEffects(spec.effects)
    else
        g_effectManager:stopEffects(spec.effects)
    end
end

-- Smyčka rotorů: hraje, dokud se vrtule točí; výška a hlasitost podle otáček, takže je slyšet roztočení i doběh.
-- Hodnoty jdou přes offset výšky a škálu hlasitosti: SoundManager:update výšku a hlasitost vzorku sám přepisuje
-- z vlastních atributů, přímé setSamplePitch/Volume by tedy nevydržely.
function SprayDroneStation.updateRotorSound(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local sample = spec.samples.rotor
    if sample == nil then
        return
    end
    local f = spec.rotorSpeed / SprayDroneStation.ROTOR_MAX_SPEED
    if f > 0 then
        local minPitch = SprayDroneStation.SOUND_MIN_PITCH
        spec.soundPitch = minPitch + (1 - minPitch) * f
        spec.soundVolume = f ^ SprayDroneStation.SOUND_VOLUME_EXPONENT
        g_soundManager:setSamplePitchOffset(sample, spec.soundPitch - 1)
        g_soundManager:setSampleVolumeScale(sample, spec.rotorVolumeScale * spec.soundVolume)
        if not g_soundManager:getIsSamplePlaying(sample) then
            g_soundManager:playSample(sample)
        end
    elseif g_soundManager:getIsSamplePlaying(sample) then
        spec.soundPitch, spec.soundVolume = 0, 0
        g_soundManager:stopSample(sample)
    end
    if SprayDroneStation.DEBUG_SOUND then
        spec.soundDebugTimer = (spec.soundDebugTimer or 0) - dt
        if spec.soundDebugTimer <= 0 and (f > 0 or spec.soundDebugPlaying) then
            spec.soundDebugTimer = SprayDroneStation.DEBUG_INTERVAL
            spec.soundDebugPlaying = f > 0
            Logging.info("SDT zvuk: otáčky %.2f, výška %.2f, hlasitost %.2f, hraje %s", f, spec.soundPitch, spec.soundVolume,
                tostring(g_soundManager:getIsSamplePlaying(sample)))
        end
    end
end

-- Náklon dronu (uzel tilt) z rychlosti a zrychlení ve světě: dopředu = nosem dolů, do boku = na tu stranu.
function SprayDroneStation.updateTilt(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.tiltNode == nil or dt <= 0 then
        return
    end
    local tilt = spec.tilt
    local pitch, roll = 0, 0
    if spec.isLinked then
        spec.lastWorldPos = nil
    else
        local s = dt * 0.001
        local x, _, z = getWorldTranslation(spec.node)
        local last = spec.lastWorldPos
        if last ~= nil then
            local f = math.min(s * 8, 1)
            local vx, vz = (x - last.x) / s, (z - last.z) / s
            local v, a = spec.velocity, spec.worldAccel
            local oldX, oldZ = v.x, v.z
            v.x, v.z = v.x + (vx - v.x) * f, v.z + (vz - v.z) * f
            local ax, az = (v.x - oldX) / s, (v.z - oldZ) / s
            a.x, a.z = a.x + (ax - a.x) * f, a.z + (az - a.z) * f
            local fx, _, fz = localDirectionToWorld(spec.node, 0, 0, 1)
            local lx, _, lz = localDirectionToWorld(spec.node, 1, 0, 0)
            local forward = SprayDroneStation.TILT_PER_SPEED * (v.x * fx + v.z * fz) + SprayDroneStation.TILT_PER_ACCELERATION * (a.x * fx + a.z * fz)
            local right = -(SprayDroneStation.TILT_PER_SPEED * (v.x * lx + v.z * lz) + SprayDroneStation.TILT_PER_ACCELERATION * (a.x * lx + a.z * lz))
            pitch = math.clamp(forward, -SprayDroneStation.MAX_TILT, SprayDroneStation.MAX_TILT)
            roll = math.clamp(right, -SprayDroneStation.MAX_TILT, SprayDroneStation.MAX_TILT)
        end
        spec.lastWorldPos = { x = x, z = z }
    end
    local f = math.min(dt * 0.004, 1)
    tilt.pitch = tilt.pitch + (pitch - tilt.pitch) * f
    tilt.roll = tilt.roll + (roll - tilt.roll) * f
    setRotation(spec.tiltNode, tilt.pitch, 0, tilt.roll)
end

function SprayDroneStation:onUpdate(dt, isActiveForInput, isActiveForInputIgnoreSelection, isSelected)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.node == nil then
        return
    end

    SprayDroneStation.updateDroneParts(self, dt)
    if self.isServer then
        if spec.state == SprayDroneStation.STATE_FLYING or spec.state == SprayDroneStation.STATE_RETURNING then
            SprayDroneStation.updateFlight(self, dt)
        elseif spec.state == SprayDroneStation.STATE_SERVICING then
            SprayDroneStation.updateService(self, dt)
        end
        SprayDroneStation.updatePower(self, dt)
    else
        SprayDroneStation.updateClientInterpolation(self, dt)
    end

    -- rozložení dronu jede se skládáním vleku, během něj drží vozidlo aktivní Foldable
    if spec.state ~= SprayDroneStation.STATE_PARKED or spec.rotorSpeed > 0 or not spec.rotorsParked or spec.generatorRunning
        or (self.isServer and SprayDroneStation.getCanCharge(self)) then
        self:raiseActive()
    end

    if self.isClient and self:getIsEntered() then
        SprayDroneStation.updatePilotView(self, dt)
    elseif self.isClient and isActiveForInputIgnoreSelection then
        SprayDroneStation.updateActionEventStates(self)
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

    local showLines = SprayDroneStation.showWorldLines
    -- kruh dosahu jako nízký "plot" (dvě výšky a sloupky), aby byl vidět i na 300 m
    local segments = showLines and 90 or 0
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
    if field ~= nil and showLines then
        drawPolygon(SprayDroneRoute.getPolygon(field), 0, 1, 0, 0.6)
        drawPolygon(SprayDroneRoute.getPolygon(field), 0, 1, 0, 1.5)
        for _, leg in ipairs(spec.drawLegs) do
            local c = SprayDroneStation.BATCH_COLORS[(leg.batch - 1) % #SprayDroneStation.BATCH_COLORS + 1]
            drawTerrainLine(leg.x1, leg.z1, leg.x2, leg.z2, c[1], c[2], c[3], 0.3)
        end
        local area = SprayDroneStation.getFlightArea(self)
        if area ~= nil then
            drawPolygon(area, 0.7, 0.4, 1, 1)
        end
        -- přelety ve výšce, ve které je dron poletí
        for _, plan in ipairs(spec.routeInfo.transits or {}) do
            for k = 1, #plan.points - 1 do
                local a, b = plan.points[k], plan.points[k + 1]
                drawTerrainLine(a.x, a.z, b.x, b.z, 1, 1, 1, plan.heights[k])
            end
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
    -- nádrž a baterie jsou ve vanilla ukazateli naplnění vpravo dole (getFillLevelInformation)
    mission:addExtraPrintText((SprayDroneStation.getDroneStateText(self)))
    local statusText = SprayDroneStation.STATUS_TEXTS[spec.status]
    if statusText ~= nil then
        mission:addExtraPrintText(g_i18n:getText(statusText))
    end
end

function SprayDroneStation.getDroneStateText(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local stateText = g_i18n:getText(SprayDroneStation.STATE_TEXTS[spec.state])
    if spec.state == SprayDroneStation.STATE_SERVICING then
        if spec.waitingForCharge then
            local _, charge = SprayDroneRoute.getBestSpare(spec.spares)
            stateText = string.format(g_i18n:getText("sdt_state_waitCharge"), charge / spec.batteryCapacity * 100)
        elseif spec.isPumping and spec.isSwapping then
            stateText = g_i18n:getText("sdt_state_pumpingSwapping")
        elseif spec.isPumping then
            stateText = string.format(g_i18n:getText("sdt_state_pumping"), spec.pumpRate * 60)
        elseif spec.isSwapping then
            stateText = g_i18n:getText("sdt_state_swapping")
        end
    elseif SprayDroneStation.getIsDroneSecured(self) then
        stateText = g_i18n:getText("sdt_state_secured")
    end
    return string.format(g_i18n:getText("sdt_hud_drone"), stateText),
        string.format(g_i18n:getText("sdt_hud_droneTank"), spec.droneFillLevel, spec.tankCapacity, spec.battery / spec.batteryCapacity * 100)
end

-- Náhradní baterie ("Baterie na vleku: 100 %, 64 % (nabíjí se)") a centrála ("Centrála: běží | nafta 24,0/30 l").
function SprayDroneStation.getPowerTexts(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local parts = {}
    for k, charge in ipairs(spec.spares) do
        local text = string.format("%.0f %%", charge / spec.batteryCapacity * 100)
        if spec.generatorRunning and k == spec.chargingSlot then
            text = text .. " " .. g_i18n:getText("sdt_hud_charging")
        end
        table.insert(parts, text)
    end
    return string.format(g_i18n:getText("sdt_hud_power"), table.concat(parts, ", ")),
        string.format(g_i18n:getText("sdt_hud_generator"), g_i18n:getText(spec.generatorRunning and "sdt_hud_generatorOn"
            or (spec.generatorEnabled and "sdt_hud_generatorOff" or "sdt_hud_generatorDisabled")),
            self:getFillUnitFillLevel(spec.dieselFillUnitIndex), self:getFillUnitCapacity(spec.dieselFillUnitIndex))
end

function SprayDroneStation:onRegisterActionEvents(isActiveForInput, isActiveForInputIgnoreSelection)
    if not self.isClient then
        return
    end
    local spec = self[SprayDroneStation.SPEC_NAME]
    self:clearActionEventsTable(spec.actionEvents)
    if isActiveForInputIgnoreSelection then
        -- centrála jde zapnout i z tahače (složený vlek, do kterého nastoupit nejde)
        local actions = { { InputAction.SDT_TOGGLE_GENERATOR, SprayDroneStation.actionEventToggleGenerator } }
        if self:getIsEntered() then
            table.insert(actions, { InputAction.SDT_OPEN_PLANNER, SprayDroneStation.actionEventOpenPlanner })
            table.insert(actions, { InputAction.SDT_START_FLIGHT, SprayDroneStation.actionEventStart })
            table.insert(actions, { InputAction.SDT_RETURN_HOME, SprayDroneStation.actionEventReturnHome })
            table.insert(actions, { InputAction.SDT_TOGGLE_LINES, SprayDroneStation.actionEventToggleLines })
        end
        for _, a in ipairs(actions) do
            local _, actionEventId = self:addActionEvent(spec.actionEvents, a[1], self, a[2], false, true, false, true, nil)
            g_inputBinding:setActionEventTextPriority(actionEventId, GS_PRIO_VERY_HIGH)
        end
        SprayDroneStation.updateActionEventStates(self)
    end
end

function SprayDroneStation.actionEventToggleGenerator(self, actionName, inputValue, callbackState, isAnalog)
    local spec = self[SprayDroneStation.SPEC_NAME]
    self:sprayDroneCommand(SprayDroneCommandEvent.SET_GENERATOR, spec.generatorEnabled and 0 or 1)
end

-- Čáry ve světě (kruh dosahu, pole, trasa, přelety, letová plocha) jen lokálně u hráče, plánovač se nemění.
function SprayDroneStation.actionEventToggleLines(self, actionName, inputValue, callbackState, isAnalog)
    SprayDroneStation.showWorldLines = not SprayDroneStation.showWorldLines
    SprayDroneStation.updateActionEventStates(self)
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
    local function setText(action, textKey)
        local event = spec.actionEvents[action]
        if event ~= nil then
            g_inputBinding:setActionEventText(event.actionEventId, g_i18n:getText(textKey))
        end
    end
    setText(InputAction.SDT_TOGGLE_GENERATOR, spec.generatorEnabled and "sdt_action_generatorOff" or "sdt_action_generatorOn")
    setText(InputAction.SDT_TOGGLE_LINES, SprayDroneStation.showWorldLines and "sdt_action_linesHide" or "sdt_action_linesShow")
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
        if spec.routeInfo.noPath == SprayDroneStation.NO_PATH_HOME then
            return "sdt_planner_areaHomeOutside"
        elseif spec.routeInfo.noPath ~= nil then
            return "sdt_planner_areaNoPath"
        elseif spec.routeInfo.noFuel then
            return "sdt_status_noFuel"
        end
        return spec.routeInfo.tooHigh and "sdt_warning_obstacleTooHigh" or "sdt_status_fieldDone"
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
    streamWriteUIntN(streamId, spec.droneFillType, FillTypeManager.SEND_NUM_BITS)
    streamWriteFloat32(streamId, spec.battery)
    streamWriteBool(streamId, spec.sprayEffectsActive)
    streamWriteBool(streamId, spec.isPumping)
    streamWriteBool(streamId, spec.isSwapping)
    streamWriteBool(streamId, spec.waitingForCharge)
    streamWriteBool(streamId, spec.generatorRunning)
    streamWriteBool(streamId, spec.generatorEnabled)
    streamWriteUInt8(streamId, spec.chargingSlot or 0)
    for _, charge in ipairs(spec.spares) do
        streamWriteFloat32(streamId, charge)
    end
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
    spec.droneFillType = streamReadUIntN(streamId, FillTypeManager.SEND_NUM_BITS)
    spec.battery = streamReadFloat32(streamId)
    spec.sprayEffectsActive = streamReadBool(streamId)
    spec.isPumping = streamReadBool(streamId)
    spec.isSwapping = streamReadBool(streamId)
    spec.waitingForCharge = streamReadBool(streamId)
    spec.generatorRunning = streamReadBool(streamId)
    spec.generatorEnabled = streamReadBool(streamId)
    local slot = streamReadUInt8(streamId)
    spec.chargingSlot = slot > 0 and slot or nil
    for k = 1, #spec.spares do
        spec.spares[k] = streamReadFloat32(streamId)
    end
    if spec.generatorRunning then
        self:raiseActive()
    end
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
    local spec = self[SprayDroneStation.SPEC_NAME]
    local count = 0
    for _ in pairs(spec.flightAreas) do
        count = count + 1
    end
    streamWriteUInt8(streamId, count)
    for fieldId, points in pairs(spec.flightAreas) do
        SprayDroneAreaEvent.writeArea(streamId, fieldId, points)
    end
end

function SprayDroneStation:onReadStream(streamId, connection)
    readState(self, streamId, true)
    local spec = self[SprayDroneStation.SPEC_NAME]
    for _ = 1, streamReadUInt8(streamId) do
        local fieldId, points = SprayDroneAreaEvent.readArea(streamId)
        spec.flightAreas[fieldId] = points
    end
    spec.areaVersion = spec.areaVersion + 1
    spec.routeDirty = true
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
