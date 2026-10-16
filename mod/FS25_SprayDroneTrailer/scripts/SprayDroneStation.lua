-- Stanoviště pilota postřikového dronu na servisním vleku a řízení letu dronu (docs/DRON.md).
--
-- Do vleku jde nastoupit složeného i rozloženého; plánovač a let jdou jen u rozloženého. Dokud dron není na vleku
-- a vrtule se netočí, vlek nejde složit.
--
-- Let simuluje server: dron (uzel <prefix>Root varianty) se při vzletu přepojí pod kořen scény a letí po
-- waypointech jedné dávky. Klienti dostávají polohu přes update stream, příkazy posílají eventem.
-- Pole se vybírá v plánovači letu (mapový dialog, scripts/gui/SprayDronePlannerScreen.lua).

source(g_currentModDirectory .. "scripts/SprayDroneRoute.lua")
source(g_currentModDirectory .. "scripts/SprayDroneMixer.lua")
source(g_currentModDirectory .. "scripts/events/SprayDroneCommandEvent.lua")
source(g_currentModDirectory .. "scripts/events/SprayDroneAreaEvent.lua")
source(g_currentModDirectory .. "scripts/events/SprayDroneServiceEvent.lua")
source(g_currentModDirectory .. "scripts/events/SprayDroneSettingsEvent.lua")
source(g_currentModDirectory .. "scripts/events/SprayDroneToolboxEvent.lua")
source(g_currentModDirectory .. "scripts/events/SprayDroneRelaySlotEvent.lua")
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
SprayDroneStation.STATUS_NO_CONCENTRATE = 9
SprayDroneStation.STATUS_NO_WATER = 10
SprayDroneStation.STATUS_GENERATOR_OFF = 11
SprayDroneStation.STATUS_TRAILER_MOVED = 12
SprayDroneStation.STATUS_NO_SIGNAL = 13
SprayDroneStation.STATUS_OUT_OF_REACH = 14
SprayDroneStation.STATUS_NUM_BITS = 4

SprayDroneStation.STATUS_TEXTS = {
    [1] = "sdt_status_fieldDone",
    [2] = "sdt_status_trailerEmpty",
    [3] = "sdt_status_unreachable",
    [4] = "sdt_status_aborted",
    [5] = "sdt_status_notAllowed",
    [6] = "sdt_status_obstacle",
    [7] = "sdt_status_areaNoPath",
    [8] = "sdt_status_noFuel",
    [9] = "sdt_status_noConcentrate",
    [10] = "sdt_status_noWater",
    [11] = "sdt_status_generatorOff",
    [12] = "sdt_status_trailerMoved",
    [13] = "sdt_status_noSignal",
    [14] = "sdt_status_outOfReach"
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
-- prodleva po startu mise (ms), než servis dronu poprvé vyhodnotí plnění a výměnu baterie
SprayDroneStation.START_DELAY = 500
-- rezerva baterie při plánování (s letu; sprayDrone#batteryReserve) a rozsah nabíjení jedné baterie (30 % -> 95 %)
SprayDroneStation.BATTERY_RESERVE = 30
SprayDroneStation.CHARGE_SPAN = 0.65
-- podíl výdrže baterie při postřiku, který se bere za délku jedné dávky při dělení pole mezi drony
SprayDroneStation.SPLIT_BATTERY_SHARE = 0.7
-- dron se při skládání vleku skládá tolikrát rychleji, než se rozkládá
SprayDroneStation.FOLD_SPEEDUP = 1.5
-- baterie: počet míst vleku je power#slots (nejvýš MAX_BATTERY_SLOTS), baterií je 0..počet míst (konfigurace v obchodě); slot 0 = v dronu
SprayDroneStation.CHARGER_LED_BARS = 5
SprayDroneStation.MAX_BATTERY_SLOTS = 10
-- čerpadlo a mixér (plnění dronu, vypouštění, přečerpání do IBC) jedou z centrály: bez ní stojí; za jejich běhu dostane
-- nabíječka jen PUMP_POWER_SHARE výkonu a čerpadlo pálí naftu jako PUMP_DIESEL_LOAD nabíjených baterií
SprayDroneStation.PUMP_POWER_SHARE = 0.5
SprayDroneStation.PUMP_DIESEL_LOAD = 1
-- relé tyč uložená na vleku (SprayDroneRelaySlots) se nabíjí z centrály a pálí naftu jako tolik nabíjených baterií dronu
SprayDroneStation.RELAY_DIESEL_LOAD = 0.1
SprayDroneStation.BATTERY_CONFIG = "sprayDroneBattery"
-- elektrocentrály: 1 nebo 2 (konfigurace v obchodě); druhá zrychlí nabíjení baterií a zdvojnásobí nádrž na naftu
SprayDroneStation.GENERATOR_CONFIG = "sprayDroneGenerator"
-- anténa vysílačky (násobí dosah, #rangeBonus) a přesná GPS / RTK (násobí spotřebu l/ha, #usageFactor); jen Middle a Max
SprayDroneStation.ANTENNA_CONFIG = "sprayDroneAntenna"
SprayDroneStation.GPS_CONFIG = "sprayDroneGps"
-- síla retranslační tyče (#radius, m); konfiguruje se na tyči (objects/relay/relayPole.xml), ne na vleku
SprayDroneStation.RELAY_CONFIG = "sprayDroneRelayStrength"
-- dron: konfigurace v obchodě vybere blok vehicle.sprayDrone.drone(?) podle #drone (prázdné = vlek bez dronu); jeho
-- atributy přepisují společné ze <sprayDrone>, uzly mají prefix (Drone_S_, Drone_A_, Drone_L_) a stejné přípony
SprayDroneStation.DRONE_CONFIG = "sprayDrone"
SprayDroneStation.DEFAULT_DRONE = "M"
-- vzhled vrtulí (konfigurace v obchodě): barva listů (nebo karbon) a barevné proužky na koncích
SprayDroneStation.PROPELLER_CONFIG = "sprayDronePropeller"
SprayDroneStation.TIPS_CONFIG = "sprayDroneTips"
-- výchozí vzhled podle modelu (položka "Podle modelu"): T50 bílé listy bez proužků, T25 a T100 karbon s oranžovými proužky
SprayDroneStation.PROPELLER_DEFAULTS = {
    M = { kind = "paint", color = { 0.06, 0.06, 0.065 }, tips = nil },
    S = { kind = "carbon", color = { 1, 1, 1 }, tips = { 0.90, 0.40, 0.03 } },
    L = { kind = "carbon", color = { 1, 1, 1 }, tips = { 0.90, 0.40, 0.03 } }
}
SprayDroneStation.CLAMPS = 4
SprayDroneStation.VARIANT_FLOATS = { "workWidth", "tankCapacity", "batteryMinutes", "droneMass", "batteryMass", "batteryKwh", "chargeMinutes",
    "dieselPerHour", "rotorPitch", "droneRadius", "maxRange", "cruiseSpeed", "sprayingSpeed", "climbSpeed", "ascentSpeed", "acceleration",
    "yawSpeed", "sprayHeight", "litersPerSecond", "turnAcceleration" }
-- přečerpávání na vleku (SprayDroneServiceEvent)
SprayDroneStation.TRANSFER_NONE = 0
SprayDroneStation.TRANSFER_DRAIN_DRONE = 1
SprayDroneStation.TRANSFER_TO_PALLET = 2
SprayDroneStation.TRANSFER_STOP = 3
SprayDroneStation.PALLET_SEARCH_TIME = 1000
-- podíl koncentrátu v přípravku z mixéru, když ho <mixer> neurčuje
SprayDroneStation.DEFAULT_MIX_RATIO = 0.05
-- hadice: přesun koncovky mezi parkem a hrdlem dronu (s)
SprayDroneStation.HOSE_TIME = 2
-- koncovka nejdřív stoupá (m, nad listy) a do hrdla sjíždí po jeho ose z HOSE_PORT_APPROACH m nad ním
SprayDroneStation.HOSE_LIFT = 0.9
SprayDroneStation.HOSE_PORT_APPROACH = 0.6
-- přenos baterie dron <-> nabíječka (s na jeden kus; vybitá napřed, nabitá po ní); vytahuje se o BATTERY_MOVE_LIFT m
SprayDroneStation.BATTERY_MOVE_TIME = 1.4
SprayDroneStation.BATTERY_MOVE_LIFT = 0.5
-- podíl času skládání vleku (0 rozloženo, 1 složeno), od kterého se baterie z dronu přesouvá do nabíječky / vrací do dronu
SprayDroneStation.BATTERY_STOW_FROM = 0.06
SprayDroneStation.BATTERY_STOW_UNTIL = 0.55
-- pod tuto hodnotou animace skládání (0 rozloženo, 1 složeno) je vlek zamrzlý na místě
SprayDroneStation.FREEZE_BELOW = 0.98
-- hláška u zamrzlého tahače: plyn/brzda nad STUCK_AXIS, rychlost pod STUCK_MAX_SPEED (km/h), nejvýš jednou za
-- STUCK_WARNING_INTERVAL ms, zobrazená STUCK_WARNING_TIME ms
SprayDroneStation.STUCK_AXIS = 0.1
SprayDroneStation.STUCK_MAX_SPEED = 1
SprayDroneStation.STUCK_WARNING_INTERVAL = 4000
SprayDroneStation.STUCK_WARNING_TIME = 2000
-- hadice: řetěz článků fillHoseSeg1..N po křivce fillHoseStart -> fillHoseLay1..M -> koncovka; volná část k dronu
-- prověšená o HOSE_SAG rozpětí (nejvýš HOSE_MAX_SAG m), zbytek leží na desce. Hadice vchází do otočného přívodu koncovky:
-- konec hadice je v HOSE_INLET_POS (lokálně v uzlu koncovky, i3d) a vchází do něj ve směru HOSE_INLET_DIR (šikmo dolů
-- a dopředu, = sdt_nozzle.INLET_END / INLET_OUT); posledních HOSE_NOZZLE_LEAD m je rovně v té ose.
SprayDroneStation.HOSE_SEGMENTS = 96
SprayDroneStation.HOSE_LAY_POINTS = 8
-- Pevný úsek hadice od vodítka u navíječe přes bok a lem na desku končí v bodě fillHoseLay<N> (první ležící na desce);
-- při připojování se nehýbe a volná část začíná nejdřív tam, jinak by hadice při animaci prošla palubou.
SprayDroneStation.HOSE_FIXED_LAY = 3
SprayDroneStation.HOSE_INLET_POS = { 0, 0.12593, -0.24313 }
SprayDroneStation.HOSE_INLET_DIR = { 0, -0.76604, 0.64279 }
SprayDroneStation.HOSE_NOZZLE_LEAD = 0.16
SprayDroneStation.HOSE_RADIUS = 0.02
SprayDroneStation.HOSE_REST_STEP = 0.02
SprayDroneStation.HOSE_SAG = 0.15
SprayDroneStation.HOSE_MAX_SAG = 0.8
SprayDroneStation.HOSE_CURVE_STEPS = 16
-- bodová světla LED nesvítí níž než tolik m nad plošinou
SprayDroneStation.LED_LIGHT_MIN_HEIGHT = 2
source(g_currentModDirectory .. "scripts/SprayDroneFields.lua")
source(g_currentModDirectory .. "scripts/SprayDroneDrones.lua")
source(g_currentModDirectory .. "scripts/SprayDroneService.lua")
source(g_currentModDirectory .. "scripts/SprayDroneToolbox.lua")
source(g_currentModDirectory .. "scripts/SprayDroneRelaySlots.lua")
source(g_currentModDirectory .. "scripts/SprayDronePad.lua")
source(g_currentModDirectory .. "scripts/SprayDroneLevel.lua")
source(g_currentModDirectory .. "scripts/SprayDroneHotspot.lua")
source(g_currentModDirectory .. "scripts/SprayDroneLadder.lua")
source(g_currentModDirectory .. "scripts/SprayDroneSound.lua")
-- DJI DB1560: 30 Ah × 52,22 V; jen pro zobrazení v ukazateli naplnění (baterie se jinak počítá v sekundách letu), varianta
-- dronu má vlastní batteryKwh
SprayDroneStation.BATTERY_KWH = 1.567
SprayDroneStation.POWER_SYNC_TIME = 500
SprayDroneStation.ROUTE_REFRESH_TIME = 5000
SprayDroneStation.RANGE_CHECK_TIME = 250
SprayDroneStation.ACTION_CHECK_TIME = 200
SprayDroneStation.MAX_TRAILER_SPEED = 3
-- signál za letu: kontrola nejvýš jednou za SIGNAL_CHECK_TIME ms, kruhy signálu zvětšené o SIGNAL_MARGIN m; dron mimo signál
-- déle než SIGNAL_LOSS_TIME s přeruší dávku a vrací se. Dávka čekající na výdrž tyče to zkouší znovu po RELAY_RETRY_TIME ms.
SprayDroneStation.SIGNAL_CHECK_TIME = 250
SprayDroneStation.SIGNAL_MARGIN = 15
SprayDroneStation.SIGNAL_LOSS_TIME = 2
SprayDroneStation.RELAY_RETRY_TIME = 5000
SprayDroneStation.MAX_BATCH_RELAYS = 7
SprayDroneStation.PAD_PREVIEW_MAX_SPEED = 1

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
-- podíl rozdílu, o který se za 1 ms přiblíží náklon k cíli (TILT_FOLLOW) a klient dronu k poloze ze serveru (NET_FOLLOW)
SprayDroneStation.TILT_FOLLOW = 0.004
SprayDroneStation.NET_FOLLOW = 0.012

-- pojistka za letu: paprsky dopředu na brzdnou dráhu + GUARD_MARGIN (napříč celým dronem s vrtulemi + GUARD_SIDE_MARGIN,
-- ve výškách GUARD_HEIGHTS nad lyžinami), při zásahu zastavit a vystoupat
SprayDroneStation.GUARD_MARGIN = 4
SprayDroneStation.GUARD_SIDE_MARGIN = 0.3
SprayDroneStation.GUARD_HEIGHTS = { 0.2, 0.8 }
SprayDroneStation.GUARD_EXTRA_CLIMB = 2
-- strop stoupání pojistky: maxTransitHeight + GUARD_CEILING_MARGIN m; po jeho dosažení se paprsky ignorují GUARD_GIVE_UP_TIME ms
SprayDroneStation.GUARD_CEILING_MARGIN = 20
SprayDroneStation.GUARD_GIVE_UP_TIME = 5000
-- paprsky pojistky a odhad energie na návrat se počítají jednou za tolik ms, ne každý snímek
SprayDroneStation.GUARD_CHECK_INTERVAL = 100
SprayDroneStation.RETURN_ENERGY_INTERVAL = 150
-- brzdění dopředu: nejvýš tolik waypointů
SprayDroneStation.LOOKAHEAD_WAYPOINTS = 40

-- nastavení letu v plánovači (celé metry)
-- values = texty hodnot (hodnota v = values[v + 1], text má pak %s místo %.0f), requires = klíč nastavení, které musí
-- být nad nulou, aby šlo toto měnit
SprayDroneStation.SETTINGS = {
    { key = "transitHeight", min = 5, max = 40, text = "sdt_setting_transitHeight" },
    { key = "obstacleClearance", min = 2, max = 20, text = "sdt_setting_obstacleClearance" },
    { key = "sideClearance", min = 1, max = 15, text = "sdt_setting_sideClearance" },
    { key = "headlands", min = 0, max = 4, text = "sdt_setting_headlands" },
    { key = "headlandFirst", min = 0, max = 1, text = "sdt_setting_start", requires = "headlands",
      values = { "sdt_setting_startRows", "sdt_setting_startHeadlands" } },
    { key = "activeDrones", min = 1, max = 2, text = "sdt_setting_activeDrones", minDrones = 2 }
}
-- dva drony: druhý letí o LAYER_GAP m výš při přeletech, nevzlétne, dokud první nelétá do PAD_CLEAR m od jeho plošiny níž než
-- PAD_CLEAR_HEIGHT m; dělení pole se nepočítá z práce pod SPLIT_MIN_LENGTH m (jde celá žadateli), rezervované úseky druhého
-- dronu se z legů vynechají do RESERVE_MARGIN m od nich
SprayDroneStation.LAYER_GAP = 6
SprayDroneStation.PAD_CLEAR = 8
SprayDroneStation.PAD_CLEAR_HEIGHT = 8
SprayDroneStation.SPLIT_MIN_LENGTH = 60
SprayDroneStation.RESERVE_MARGIN = 2
SprayDroneStation.TRANSIT_CACHE_SIZE = 256
SprayDroneStation.EXTENSION_MAX_TURN = math.rad(150)

-- fáze letu pro odběr baterie (svislá rychlost = stoupání / klesání, pomalu vodorovně = vznášení) určují
-- SprayDroneRoute.VERTICAL_PHASE_SPEED a HOVER_PHASE_SPEED, stejné jako v odhadu trasy

-- zvuk rotorů: výška a hlasitost podle otáček (0..1)
SprayDroneStation.SOUND_MIN_PITCH = 0.45
SprayDroneStation.SOUND_VOLUME_EXPONENT = 0.7
-- druhý dron: násobek výšky tónu rotoru a zpoždění přehrání (ms) proti prvnímu
SprayDroneStation.SECOND_ROTOR_PITCH = 0.97
SprayDroneStation.SECOND_ROTOR_DELAY = 170
SprayDroneStation.ROTOR_RETRY_TIME = 400

-- čáry ve světě (kruh dosahu, pole, trasa, přelety); ve výchozím stavu vypnuté, hráč je zapíná a vypíná lokálně akcí
-- SDT_TOGGLE_LINES (Alt+5)
SprayDroneStation.showWorldLines = false

-- Vanilla „složit vše“ (Ctrl+X) registruje sám vlek, takže se v getIsFoldAllowed od vlastního složení (X na vybraném vleku)
-- nepozná podle směru ani výběru; po dobu jeho běhu platí tento příznak a dron se neodvolává.
SprayDroneStation.foldAllActive = false
local vanillaFoldAll = Foldable.actionEventFoldAll
Foldable.actionEventFoldAll = function(...)
    SprayDroneStation.foldAllActive = true
    vanillaFoldAll(...)
    SprayDroneStation.foldAllActive = false
end

function SprayDroneStation.prerequisitesPresent(specializations)
    return SpecializationUtil.hasSpecialization(Enterable, specializations)
        and SpecializationUtil.hasSpecialization(Foldable, specializations)
        and SpecializationUtil.hasSpecialization(FillUnit, specializations)
end

-- Uzly dronu (náklon, klouby, vrtule, LED), zvuk rotorů a efekt postřiku v bloku varianty drone(?).
function SprayDroneStation.registerDronePartPaths(schema, key)
    schema:register(XMLValueType.NODE_INDEX, key .. ".navLight(?)#node", "LED ramene (materiál staticLight_vertex)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".navLight(?)#lightNode", "Bodové světlo LED")
    schema:register(XMLValueType.BOOL, key .. ".navLight(?)#blink", "Bliká (jinak svítí)", false)
    schema:register(XMLValueType.NODE_INDEX, key .. ".tilt#node", "Uzel náklonu dronu za letu")
    schema:register(XMLValueType.NODE_INDEX, key .. ".foldPart(?)#node", "Kloub dronu (rameno, list vrtule)")
    schema:register(XMLValueType.VECTOR_ROT, key .. ".foldPart(?)#foldedRot", "Natočení složeno")
    schema:register(XMLValueType.VECTOR_ROT, key .. ".foldPart(?)#unfoldedRot", "Natočení rozloženo")
    schema:register(XMLValueType.FLOAT, key .. ".foldPart(?)#startTime", "Začátek pohybu (0..1 rozložení)", 0)
    schema:register(XMLValueType.FLOAT, key .. ".foldPart(?)#endTime", "Konec pohybu (0..1 rozložení)", 1)
    schema:register(XMLValueType.NODE_INDEX, key .. ".propBlade(?)#node", "List vrtule (barva a materiál podle konfigurace)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".propBlade(?)#tip", "Barevné proužky na konci listu")
    schema:register(XMLValueType.NODE_INDEX, key .. ".propSource#node", "Uzel s karbonovým materiálem na slotu 0 (zdroj materiálu karbon)")
    schema:register(XMLValueType.NODE_INDEX, key .. ".rotor(?)#node", "Vrtule")
    schema:register(XMLValueType.INT, key .. ".rotor(?)#direction", "Směr otáčení (1 / -1)", 1)
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "rotor")
    SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", "spray")
    EffectManager.registerEffectXMLPaths(schema, key .. ".effects")
    schema:register(XMLValueType.FLOAT, key .. ".effects#meshWidth", "Šířka sítě efektu postřiku ve zdrojovém i3d (m)", 1)
    schema:register(XMLValueType.FLOAT, key .. ".effects#meshHeight", "Výška sítě efektu postřiku ve zdrojovém i3d (m)", 1)
    schema:register(XMLValueType.FLOAT, key .. ".effects#nozzleY", "Výška trysek nad uzlem, ke kterému je efekt připojený (m)", 0)
    schema:register(XMLValueType.ANGLE, key .. ".effects#rotY", "Natočení efektu kolem svislé osy", 0)
    schema:register(XMLValueType.FLOAT, key .. ".effects#coneWidth", "Šířka kužele postřiku jedné trysky u země (m)", 2.5)
    schema:register(XMLValueType.NODE_INDEX, key .. ".effects.nozzle(?)#node", "Tryska (efekty se rozdělí po dvou křížem pod každou)")
    schema:register(XMLValueType.FLOAT, key .. ".effects.nozzle(?)#x", "Tryska bez uzlu: poloha napříč v souřadnicích kořene dronu (m)")
    schema:register(XMLValueType.FLOAT, key .. ".effects.nozzle(?)#z", "Tryska bez uzlu: poloha podél v souřadnicích kořene dronu (m)")
end

-- Vehicle.postInit registruje cesty (#name, #price, objectChange, …) všech konfigurací, které v tu chvíli existují. Když
-- se konfigurace módu přidá až po něm (vanilla fillUnit už je zaregistrovaná), zaregistrují se tady; jinak to udělá postInit.
function SprayDroneStation.registerConfigurationPaths(name)
    local desc = g_vehicleConfigurationManager:getConfigurationDescByName(name)
    local vanilla = g_vehicleConfigurationManager:getConfigurationDescByName("fillUnit")
    local schema = Vehicle.xmlSchema
    if desc == nil or vanilla == nil or type(schema.paths) ~= "table" or schema.paths[vanilla.configurationKey .. "(?)#price"] == nil
        or schema.paths[desc.configurationKey .. "(?)#price"] ~= nil then
        return
    end
    VehicleConfigurationItem.registerXMLPaths(schema, desc.configurationsKey, desc.configurationKey .. "(?)")
    schema:register(XMLValueType.FLOAT, desc.configurationKey .. "(?)#workingWidth", "Work width to display in shop while config is active")
end

-- Číselná hodnota z vybrané položky konfigurace v obchodě (bez konfigurace nebo bez atributu default).
function SprayDroneStation.getConfigValue(self, xml, key, config, attribute, default)
    local id = self.configurations ~= nil and self.configurations[config] or nil
    if id == nil then
        return default
    end
    return xml:getValue(string.format("%s.%sConfigurations.%sConfiguration(%d)#%s", key, config, config, id - 1, attribute), default)
end

function SprayDroneStation.initSpecialization()
    local schema = Vehicle.xmlSchema
    schema:setXMLSpecializationType("SprayDroneStation")
    local key = "vehicle.sprayDrone"
    schema:register(XMLValueType.INT, key .. "#fillUnitIndex", "Nádrž vleku, ze které se dron doplňuje", 1)
    schema:register(XMLValueType.FLOAT, key .. "#range", "Pevný strop dosahu od vleku (m); dosah se jinak počítá z baterie")
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
    schema:register(XMLValueType.FLOAT, key .. "#sideClearance", "Boční odstup dráhy od překážek (m)", 4)
    schema:register(XMLValueType.FLOAT, key .. "#droneRadius", "Poloměr dronu s vrtulemi (m)", 1.6)
    schema:register(XMLValueType.FLOAT, key .. "#turnAcceleration", "Boční zrychlení v oblouku (m/s²), rychlost na oblouku sqrt(a * r)", 2.5)
    schema:register(XMLValueType.FLOAT, key .. "#maxRange", "Strop dosahu počítaného z baterie (m), před vlivem antény", 750)
    schema:register(XMLValueType.FLOAT, key .. ".sprayDroneAntennaConfigurations.sprayDroneAntennaConfiguration(?)#rangeBonus", "Násobek dosahu", 1)
    schema:register(XMLValueType.FLOAT, key .. ".sprayDroneGpsConfigurations.sprayDroneGpsConfiguration(?)#usageFactor", "Násobek spotřeby l/ha (přesnější GPS = méně přesahů)", 1)
    schema:register(XMLValueType.FLOAT, key .. "#batteryReserve", "Rezerva baterie při plánování letu (s letu)", SprayDroneStation.BATTERY_RESERVE)
    schema:register(XMLValueType.FLOAT, key .. "#usageScale", "Násobek spotřeby l/ha oproti vanilla", 1)
    schema:register(XMLValueType.FLOAT, key .. "#litersPerSecond", "Čerpadlo plnění dronu na plošině (l/s)", 1)
    schema:register(XMLValueType.FLOAT, key .. "#securedFoldTime", "Od kterého času skládání vleku (0..1) jsou úchyty dronu zavřené", 0.8)
    schema:register(XMLValueType.FLOAT, key .. "#batteryStowFrom", "Od jakého času skládání (0..1) se baterie z dronu přesouvá do nabíječky", SprayDroneStation.BATTERY_STOW_FROM)
    schema:register(XMLValueType.FLOAT, key .. "#batteryStowUntil", "Do jakého času skládání (0..1) se baterie při rozkládání vrací do dronu", SprayDroneStation.BATTERY_STOW_UNTIL)
    schema:register(XMLValueType.INT, key .. ".power#dieselFillUnitIndex", "Nádrž elektrocentrály (nafta)", 2)
    schema:register(XMLValueType.INT, key .. ".mixer#concentrateFillUnitIndex", "Nádrž koncentrátu pro mixér", 3)
    schema:register(XMLValueType.STRING, key .. ".mixer.ratio(?)#fillType", "Druh koncentrátu v nádrži koncentrátu (vlastní SDT_CONCENTRATE_*)")
    schema:register(XMLValueType.STRING, key .. ".mixer.ratio(?)#product", "Druh hotového přípravku pro dron (vanilla herbicide / liquidFertilizer); bez něj stejný druh jako koncentrát")
    schema:register(XMLValueType.FLOAT, key .. ".mixer.ratio(?)#concentrate", "Podíl koncentrátu v hotovém přípravku (0..1), zbytek je voda",
        SprayDroneStation.DEFAULT_MIX_RATIO)
    schema:register(XMLValueType.INT, key .. ".power#batteries", "Počet baterií dronu bez konfigurace (0..počet slotů)", 3)
    schema:register(XMLValueType.INT, key .. ".power#slots", "Počet šachet nabíječky (1..MAX_BATTERY_SLOTS)", 5)
    schema:register(XMLValueType.INT, key .. ".sprayDroneBatteryConfigurations.sprayDroneBatteryConfiguration(?)#count", "Počet baterií dronu (0..počet slotů)", 3)
    schema:register(XMLValueType.INT, key .. ".sprayDroneGeneratorConfigurations.sprayDroneGeneratorConfiguration(?)#count", "Počet elektrocentrál (1 nebo 2)", 1)
    schema:register(XMLValueType.FLOAT, key .. ".power#dieselPerGenerator", "Nádrž jedné elektrocentrály (l); nádrž na naftu je tolikrát větší, kolik je centrál", 30)
    schema:register(XMLValueType.NODE_INDEX, key .. ".power.exhaust#node2", "Výfuk druhé centrály")
    schema:register(XMLValueType.FLOAT, key .. "#layerGap", "Výškový odstup přeletu druhého dronu od prvního (m)", SprayDroneStation.LAYER_GAP)
    for _, name in ipairs({ SprayDroneStation.PROPELLER_CONFIG, SprayDroneStation.TIPS_CONFIG }) do
        local itemKey = string.format("%s.%sConfigurations.%sConfiguration(?)", key, name, name)
        schema:register(XMLValueType.STRING, itemKey .. "#kind", "default = podle modelu, paint / carbon / none", "default")
        schema:register(XMLValueType.STRING, itemKey .. "#color", "Barva (r g b, 0..1)", "1 1 1")
        schema:register(XMLValueType.FLOAT, itemKey .. "#glow", "Násobek jasu barvy (fosforeskující)", 1)
    end
    schema:register(XMLValueType.FLOAT, key .. ".transfer#drainRate", "Vypouštění nádrže dronu do vleku (l/s)", 1)
    schema:register(XMLValueType.FLOAT, key .. ".transfer#palletRate", "Přečerpávání nádrže vleku do IBC (l/s)", 1.5)
    schema:register(XMLValueType.FLOAT, key .. ".transfer#palletDistance", "Nejvyšší vzdálenost IBC od vleku (m)", 6)
    schema:register(XMLValueType.FLOAT, key .. ".power#chargeMinutes", "Nabití jedné baterie z 30 % na 95 % (min)", 10)
    schema:register(XMLValueType.FLOAT, key .. ".power#dieselPerHour", "Spotřeba centrály na jednu nabíjenou baterii (l/h)", 2.2)
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
    SprayDroneToolbox.registerXMLPaths(schema, key)
    SprayDronePad.registerXMLPaths(schema, key)
    SprayDroneLevel.registerXMLPaths(schema, key)
    SprayDroneSound.registerXMLPaths(schema, key)
    local droneKey = key .. ".drone(?)"
    SprayDroneStation.registerDronePartPaths(schema, droneKey)
    schema:register(XMLValueType.STRING, droneKey .. "#name", "Varianta dronu (S, M, L), vybírá ji konfigurace sprayDrone#drone")
    schema:register(XMLValueType.STRING, droneKey .. "#prefix", "Prefix uzlů dronu v i3d (Drone_S_, …): Root, Tilt, FillPort, BatterySlot, Clamp_i; povinný")
    schema:register(XMLValueType.INT, droneKey .. "#slot", "Dron na vleku: 1 (výchozí) nebo 2 (druhý dron téže varianty; ze slotu 2 se berou jen uzly, ostatní parametry jsou ze slotu 1)", 1)
    schema:register(XMLValueType.STRING, droneKey .. "#hosePrefix", "Prefix uzlů plnicí hadice dronu (fillHose = fillHoseCoil, fillHoseStart, ..., u druhého dronu fillHoseB)", "fillHose")
    schema:register(XMLValueType.INT, droneKey .. "#cameraIndex", "Číslo kamery dronu v enterable.cameras (pohled z dronu, přepíná se akcí SDT_DRONE_VIEW)")
    schema:register(XMLValueType.NODE_INDEX, droneKey .. "#cameraNode", "Kamera dronu (uzel kamery v i3d, za běhu se připojí pod uzel náklonu dronu)")
    schema:register(XMLValueType.VECTOR_TRANS, droneKey .. "#cameraTrans", "Poloha kamery v uzlu náklonu dronu (m)", "0 0 0")
    schema:register(XMLValueType.FLOAT, droneKey .. "#cameraPitch", "Sklon kamery dronu dolů (°)", 15)
    schema:register(XMLValueType.INT, droneKey .. "#outCameraIndex", "Číslo kamery, která se na dron dívá zvenku, v enterable.cameras (klávesa C v pohledu dronu)")
    schema:register(XMLValueType.NODE_INDEX, droneKey .. "#outTargetNode", "Střed otáčení vnější kamery dronu (za běhu se připojí pod uzel dronu)")
    schema:register(XMLValueType.VECTOR_TRANS, droneKey .. "#outTargetTrans", "Poloha středu otáčení vnější kamery v uzlu dronu (m)", "0 0.3 0")
    for _, name in ipairs(SprayDroneStation.VARIANT_FLOATS) do
        schema:register(XMLValueType.FLOAT, droneKey .. "#" .. name, "Parametr varianty (přepisuje atribut <sprayDrone>)")
    end
    schema:register(XMLValueType.VECTOR_TRANS, droneKey .. "#hoseVia",
        "Kudy hadice přechází přes přední hranu trupu k hrdlu (v <prefix>Tilt; znaménko x podle strany fillHoseStart)")
    schema:register(XMLValueType.FLOAT, key .. "#batteryMass", "Hmotnost baterie (kg), přičte se k droneMass", 0)
    schema:register(XMLValueType.FLOAT, key .. "#batteryKwh", "Energie baterie (kWh), jen pro zobrazení", SprayDroneStation.BATTERY_KWH)
    schema:register(XMLValueType.FLOAT, key .. "#rotorPitch", "Výška zvuku rotorů (násobek)", 1)
    schema:register(XMLValueType.STRING, key .. ".sprayDroneConfigurations.sprayDroneConfiguration(?)#drone", "Varianta dronu (prázdné = bez dronu)")
    schema:setXMLSpecializationType()

    local configs = { { SprayDroneStation.BATTERY_CONFIG, "sdt_configuration_batteries" }, { SprayDroneStation.GENERATOR_CONFIG, "sdt_configuration_generators" },
        { SprayDroneStation.ANTENNA_CONFIG, "sdt_configuration_antenna" }, { SprayDroneStation.GPS_CONFIG, "sdt_configuration_gps" },
        { SprayDroneStation.RELAY_CONFIG, "sdt_configuration_relayStrength" },
        { SprayDroneStation.DRONE_CONFIG, "sdt_configuration_drone" },
        { SprayDroneStation.PROPELLER_CONFIG, "sdt_configuration_propellers" }, { SprayDroneStation.TIPS_CONFIG, "sdt_configuration_tips" } }
    for _, config in ipairs(configs) do
        if g_vehicleConfigurationManager:getConfigurationDescByName(config[1]) == nil then
            g_vehicleConfigurationManager:addConfigurationType(config[1], g_i18n:getText(config[2]), "sprayDrone", VehicleConfigurationItem)
            SprayDroneStation.registerConfigurationPaths(config[1])
        end
    end

    local savegame = Vehicle.xmlSchemaSavegame
    local saveKey = string.format("vehicles.vehicle(?).%s.sprayDroneStation", SprayDroneStation.MOD_NAME)
    savegame:register(XMLValueType.INT, saveKey .. "#fieldId", "Vybrané pole (farmland id)")
    savegame:register(XMLValueType.BOOL, saveKey .. "#missionActive", "Mise běží")
    savegame:register(XMLValueType.FLOAT, saveKey .. "#droneFillLevel", "Náplň dronu (l)")
    savegame:register(XMLValueType.STRING, saveKey .. "#droneFillType", "Druh náplně dronu")
    savegame:register(XMLValueType.BOOL, saveKey .. ".drone2#missionActive", "Druhý dron: mise běží")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".drone2#droneFillLevel", "Druhý dron: náplň (l)")
    savegame:register(XMLValueType.STRING, saveKey .. ".drone2#droneFillType", "Druhý dron: druh náplně")
    savegame:register(XMLValueType.INT, saveKey .. ".battery(?)#drone", "Dron, ve kterém baterie je (platí při #slot 0)", 1)
    savegame:register(XMLValueType.INT, saveKey .. ".flightSettings#activeDrones", "Nastavení: kolik dronů je v misi")
    savegame:register(XMLValueType.BOOL, saveKey .. "#generatorEnabled", "Elektrocentrála zapnutá")
    savegame:register(XMLValueType.STRING, saveKey .. "#coverage", "Paměť dronu, kde už postříkal")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".battery(?)#level", "Nabití baterie (0..1); sedí i po výměně dronu jiné velikosti")
    savegame:register(XMLValueType.INT, saveKey .. ".battery(?)#slot", "Kde baterie je: 0 = v dronu, 1..počet slotů = slot na vleku")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".flightSettings#transitHeight", "Nastavení: nejnižší výška přeletu (m)")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".flightSettings#obstacleClearance", "Nastavení: odstup nad překážkami (m)")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".flightSettings#sideClearance", "Nastavení: boční odstup od překážek (m)")
    savegame:register(XMLValueType.INT, saveKey .. ".flightSettings#headlands", "Nastavení: počet úvratí")
    savegame:register(XMLValueType.INT, saveKey .. ".flightSettings#headlandFirst", "Nastavení: začít úvratěmi (1) nebo řádky (0)")
    savegame:register(XMLValueType.INT, saveKey .. ".flightArea(?)#fieldId", "Pole, ke kterému letová plocha patří")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".flightArea(?).point(?)#x", "Vrchol letové plochy (svět x)")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".flightArea(?).point(?)#z", "Vrchol letové plochy (svět z)")
    SprayDroneToolbox.registerSavegamePaths(savegame, saveKey)
    SprayDroneRelaySlots.registerSavegamePaths(savegame, saveKey)
end

function SprayDroneStation.registerFunctions(vehicleType)
    SpecializationUtil.registerFunction(vehicleType, "sprayDroneCommand", SprayDroneStation.sprayDroneCommand)
    SpecializationUtil.registerFunction(vehicleType, "getSprayDroneIsParked", SprayDroneStation.getSprayDroneIsParked)
    SpecializationUtil.registerFunction(vehicleType, "setSprayDroneFlightArea", SprayDroneStation.setSprayDroneFlightArea)
    SpecializationUtil.registerFunction(vehicleType, "setSprayDroneSettings", SprayDroneStation.setSprayDroneSettings)
    SpecializationUtil.registerFunction(vehicleType, "setSprayDroneTransfer", SprayDroneStation.setSprayDroneTransfer)
end

function SprayDroneStation.registerOverwrittenFunctions(vehicleType)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getIsFoldAllowed", SprayDroneStation.getIsFoldAllowed)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "getFillLevelInformation", SprayDroneStation.getFillLevelInformation)
    SpecializationUtil.registerOverwrittenFunction(vehicleType, "setActiveCameraIndex", SprayDroneStation.setActiveCameraIndex)
end

function SprayDroneStation.registerEventListeners(vehicleType)
    SpecializationUtil.registerEventListener(vehicleType, "onLoad", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onDelete", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onUpdate", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onFillUnitFillLevelChanged", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onRegisterActionEvents", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onReadStream", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onWriteStream", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onReadUpdateStream", SprayDroneStation)
    SpecializationUtil.registerEventListener(vehicleType, "onWriteUpdateStream", SprayDroneStation)
end

-- Varianta dronu z konfigurace sprayDrone (bloky vehicle.sprayDrone.drone(?)): kořen <prefix>Root, ostatní varianty se
-- skryjí. Baterie bez dronu jsou typu DEFAULT_DRONE.
function SprayDroneStation.loadDroneVariant(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local getMappedNode = SprayDroneStation.getMappedNode
    local default = SprayDroneStation.DEFAULT_DRONE
    spec.variants = {}
    local second = {}
    xml:iterate(key .. ".drone", function(_, droneKey)
        local name, prefix = xml:getValue(droneKey .. "#name"), xml:getValue(droneKey .. "#prefix")
        if name == nil or prefix == nil then
            Logging.xmlWarning(xml, "SprayDroneStation: %s nemá #name nebo #prefix, přeskočeno", droneKey)
        elseif xml:getValue(droneKey .. "#slot", 1) == 2 then
            second[name] = { name = name, key = droneKey, prefix = prefix }
        else
            table.insert(spec.variants, { name = name, key = droneKey, prefix = prefix })
        end
    end)
    spec.secondVariants = second
    local wanted = default
    local configName = SprayDroneStation.DRONE_CONFIG
    local configId = self.configurations ~= nil and self.configurations[configName] or nil
    if configId ~= nil then
        wanted = xml:getValue(string.format("%s.%sConfigurations.%sConfiguration(%d)#drone", key, configName, configName, configId - 1)) or ""
    end
    spec.hasDrone = wanted ~= ""
    spec.droneName, spec.droneKey, spec.dronePrefix = wanted, nil, nil
    local selected, fallback = nil, nil
    for _, v in ipairs(spec.variants) do
        if v.name == wanted then
            selected = v
        end
        if v.name == default then
            fallback = v
        end
    end
    if selected ~= nil then
        spec.droneKey, spec.dronePrefix = selected.key, selected.prefix
    elseif spec.hasDrone then
        Logging.xmlWarning(xml, "SprayDroneStation: varianta dronu '%s' v %s.drone chybí, vlek je bez dronu", wanted, key)
        spec.hasDrone = false
    end
    local batteryVariant = spec.hasDrone and selected or fallback
    spec.batteryKey = batteryVariant ~= nil and batteryVariant.key or nil
    spec.batteryVariant = batteryVariant ~= nil and batteryVariant.name or (spec.hasDrone and wanted or default)
    if not spec.hasDrone then
        spec.droneName = ""
    end

    local function variantRoot(v)
        return getMappedNode(self, v.prefix .. "Root")
    end
    spec.node = nil
    if spec.hasDrone then
        spec.node = variantRoot(selected)
        if spec.node == nil then
            Logging.xmlWarning(xml, "SprayDroneStation: v i3d chybí kořen dronu %sRoot, dron letí bez modelu", spec.dronePrefix)
            spec.node = SprayDroneStation.createStandInRoot(self, fallback ~= nil and variantRoot(fallback) or nil)
        end
        spec.parent = getParent(spec.node)
        spec.localTrans = { getTranslation(spec.node) }
        spec.localRot = { getRotation(spec.node) }
        setVisibility(spec.node, true)
    else
        spec.parent = self.components[1].node
        spec.localTrans, spec.localRot = { 0, 0, 0 }, { 0, 0, 0 }
    end
    for _, v in ipairs(spec.variants) do
        if v ~= selected then
            local root = variantRoot(v)
            if root ~= nil and root ~= spec.node then
                setVisibility(root, false)
            end
        end
    end
    -- druhý dron téže varianty (bloky drone(?)#slot = 2): jen když je v i3d jeho kořen
    spec.secondVariant = nil
    for name, v in pairs(second) do
        local root = variantRoot(v)
        if name == wanted and spec.hasDrone and selected ~= nil and root ~= nil then
            spec.secondVariant = v
        elseif root ~= nil then
            setVisibility(root, false)
        end
    end
end

-- Náhradní kořen dronu (bez modelu) tam, kde sedí dron ref, když v i3d kořen varianty chybí: let a logika jedou dál.
function SprayDroneStation.createStandInRoot(self, ref)
    local node = createTransformGroup("sprayDroneStandIn")
    link(ref ~= nil and getParent(ref) or self.components[1].node, node)
    if ref ~= nil then
        setTranslation(node, getTranslation(ref))
        setRotation(node, getRotation(ref))
    end
    return node
end

-- Uzly dronu z bloku varianty: LED, náklon, klouby, vrtule.
function SprayDroneStation.loadDroneParts(self, xml, key, partsKey)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local lightScale = xml:getValue(key .. ".navLights#lightScale", 0.3)
    xml:iterate(partsKey .. ".navLight", function(_, lightKey)
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
    spec.tiltNode = xml:getValue(partsKey .. ".tilt#node", nil, self.components, self.i3dMappings)
        or SprayDroneStation.getMappedNode(self, spec.dronePrefix .. "Tilt")
    xml:iterate(partsKey .. ".foldPart", function(_, partKey)
        local node = xml:getValue(partKey .. "#node", nil, self.components, self.i3dMappings)
        local folded = xml:getValue(partKey .. "#foldedRot", nil, true)
        local unfolded = xml:getValue(partKey .. "#unfoldedRot", nil, true)
        if node ~= nil and folded ~= nil and unfolded ~= nil then
            table.insert(spec.foldParts, { node = node, folded = folded, unfolded = unfolded,
                startTime = xml:getValue(partKey .. "#startTime", 0), endTime = xml:getValue(partKey .. "#endTime", 1) })
        end
    end)
    spec.propBlades = {}
    xml:iterate(partsKey .. ".propBlade", function(_, bladeKey)
        local node = xml:getValue(bladeKey .. "#node", nil, self.components, self.i3dMappings)
        if node ~= nil then
            table.insert(spec.propBlades, { node = node, tip = xml:getValue(bladeKey .. "#tip", nil, self.components, self.i3dMappings) })
        end
    end)
    spec.propSource = xml:getValue(partsKey .. ".propSource#node", nil, self.components, self.i3dMappings)
    xml:iterate(partsKey .. ".rotor", function(_, rotorKey)
        local node = xml:getValue(rotorKey .. "#node", nil, self.components, self.i3dMappings)
        if node ~= nil then
            table.insert(spec.rotors, { node = node, direction = xml:getValue(rotorKey .. "#direction", 1), angle = 0, appliedAngle = 0 })
        end
    end)
end

-- Vzhled vrtulí podle konfigurací v obchodě: list má materiál z i3d (Prop_Blade, barva přes colorScale) nebo materiál
-- karbon z ramene; proužky na konci (dítě listu) mají vlastní barvu nebo se schovají.
function SprayDroneStation.applyPropellerLook(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.propBlades == nil or #spec.propBlades == 0 then
        return
    end
    local function item(configName)
        local id = self.configurations ~= nil and self.configurations[configName] or nil
        local base = string.format("%s.%sConfigurations.%sConfiguration(%d)", key, configName, configName, (id or 1) - 1)
        local color = { 1, 1, 1 }
        local text = xml:getValue(base .. "#color", "1 1 1")
        local i = 1
        for v in string.gmatch(text, "%S+") do
            color[i] = tonumber(v) or 1
            i = i + 1
        end
        local glow = xml:getValue(base .. "#glow", 1)
        return xml:getValue(base .. "#kind", "default"), { color[1] * glow, color[2] * glow, color[3] * glow }
    end
    local default = SprayDroneStation.PROPELLER_DEFAULTS[spec.droneName] or SprayDroneStation.PROPELLER_DEFAULTS.M
    local kind, color = item(SprayDroneStation.PROPELLER_CONFIG)
    if kind == "default" then
        kind, color = default.kind, default.color
    end
    local tipKind, tipColor = item(SprayDroneStation.TIPS_CONFIG)
    if tipKind == "default" then
        tipKind = default.tips ~= nil and "paint" or "none"
        tipColor = default.tips or { 1, 1, 1 }
    end
    if spec.propPaintMaterial == nil then
        spec.propPaintMaterial = getMaterial(spec.propBlades[1].node, 0)
    end
    local function setColor(node, c)
        local _, _, _, w = getShaderParameter(node, "colorScale")
        setShaderParameter(node, "colorScale", c[1], c[2], c[3], w or 0, false)
    end
    local carbonMaterial = spec.propSource ~= nil and getMaterial(spec.propSource, 0) or nil
    for _, blade in ipairs(spec.propBlades) do
        if kind == "carbon" and carbonMaterial ~= nil then
            setMaterial(blade.node, carbonMaterial, 0)
            setColor(blade.node, { 1, 1, 1 })
        else
            setMaterial(blade.node, spec.propPaintMaterial, 0)
            setColor(blade.node, color)
        end
        if blade.tip ~= nil then
            setVisibility(blade.tip, tipKind ~= "none")
            if tipKind ~= "none" then
                setColor(blade.tip, tipColor)
            end
        end
    end
end

-- Počáteční stav jednoho dronu (spec dronu v kontextu): mise, náplň, poloha, trasa, cache, rotory a efekty.
function SprayDroneStation.initDroneState(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.isPumping, spec.isSwapping, spec.waitingForCharge = false, false, false
    spec.isMixing, spec.waitingForPower = false, false
    spec.swapTimer = 0
    spec.swapChecked, spec.swapPending = false, false
    spec.pumpCapChecked, spec.pumpTankTarget = false, nil
    spec.waitingForPad = false
    spec.waitingForRelay = false
    -- tyče (vozidla), na kterých závisí rozlétaná dávka (SprayDroneLink.getNeededRelays); jdou po síti kvůli blokaci tyče
    spec.batchRelays = {}
    spec.signalLostTime, spec.signalCheckTime = 0, 0
    spec.unfold = 0
    spec.appliedUnfold = -1
    spec.rotorSpeed = 0
    spec.rotorsParked = true
    spec.drainPos = nil
    spec.drainFactor = 0
    spec.massPerLiter = 1
    spec.soundPitch, spec.soundVolume = 0, 0
    spec.sprayEffectsActive = false
    spec.lastSprayTime = -math.huge
    spec.tilt = { pitch = 0, roll = 0 }
    spec.lastWorldPos = nil
    spec.velocity = { x = 0, z = 0 }
    spec.worldAccel = { x = 0, z = 0 }
    spec.transitCache = {}
    spec.transitCacheSize = 0
    spec.corridor = nil
    spec.pathCache = {}
    spec.pathCacheSize = 0

    spec.state = SprayDroneStation.STATE_PARKED
    spec.status = SprayDroneStation.STATUS_NONE
    spec.notifiedStatus = SprayDroneStation.STATUS_NONE
    spec.missionActive = false
    spec.droneFillLevel = 0
    spec.droneFillType = FillType.UNKNOWN
    -- nabití baterie, která je v dronu (s); bez baterie 0. Ve spec.batteries[droneBattery].charge se srovná při přesunu a uložení
    spec.battery = 0
    spec.batch = 0
    spec.serviceTimer = 0
    spec.pos = { x = 0, z = 0, h = 0, yaw = 0 }
    spec.speed = 0
    spec.yawRate = 0
    spec.moveDir = { x = 0, z = 0 }
    spec.airborne = false
    spec.avoidHeight = 0
    spec.avoidClimbTo = nil
    spec.guardOffUntil = 0
    spec.guardNextCheck = 0
    spec.returnEnergy, spec.returnEnergyTime = 0, -math.huge
    spec.batchHeight = spec.transitHeight
    spec.path = nil
    spec.wpIndex = 1
    spec.sprayFrom = nil
    spec.isSpraying = false
    spec.netTarget = nil

    spec.routeDirty = true
    spec.routeTimer = 0
    spec.drawLegs = {}
    spec.numBatches = 0
    spec.routeClipped = false
    spec.routeInfo = { time = 0, height = spec.transitHeight, tooHigh = false, transits = {} }
end

-- Druhý dron téže varianty (blok drone(?)#slot = 2): pohled na spec, uzly, vizuál, zvuk a efekty. Parametry letu jsou sdílené
-- se slotem 1 (oba drony jsou stejné), z bloku slotu 2 se berou jen uzly, zvuk, efekty a hadice.
function SprayDroneStation.loadSecondDrone(self, xml, key)
    local root = self[SprayDroneStation.SPEC_NAME]
    local variant = root.secondVariant
    if root.numDrones < 2 or variant == nil then
        return
    end
    root.drones[2] = SprayDroneDrones.createView(root, 2)
    root.drones[2].layerOffset = root.layerGap
    SprayDroneDrones.runAs(self, 2, SprayDroneStation.loadDroneInstance, xml, key, variant)
end

function SprayDroneStation.loadDroneInstance(self, xml, key, variant)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.hasDrone = true
    spec.droneKey, spec.dronePrefix = variant.key, variant.prefix
    spec.node = SprayDroneStation.getMappedNode(self, variant.prefix .. "Root")
    spec.parent = getParent(spec.node)
    spec.localTrans = { getTranslation(spec.node) }
    spec.localRot = { getRotation(spec.node) }
    setVisibility(spec.node, true)
    spec.isLinked = true
    spec.range = math.min(spec.maxRange, spec.rangeCap or math.huge)
    spec.rangeKey = nil
    spec.camera = xml:getValue(variant.key .. "#cameraIndex")
    spec.outCamera = xml:getValue(variant.key .. "#outCameraIndex")
    spec.navLights, spec.foldParts, spec.rotors, spec.tiltNode = {}, {}, {}, nil
    SprayDroneStation.loadDroneParts(self, xml, key, variant.key)
    SprayDroneStation.applyPropellerLook(self, xml, key)
    SprayDroneStation.initDroneState(self)
    -- druhý dron je o pár procent níž a s mírným zpožděním roztočení, ať se oba rotory nesléjí v jeden tón
    spec.rotorPitchFactor, spec.rotorStartDelay = SprayDroneStation.SECOND_ROTOR_PITCH, SprayDroneStation.SECOND_ROTOR_DELAY
    SprayDroneStation.loadDroneSounds(self, xml, variant.key)
    SprayDroneStation.applyNavLights(self, false)
    SprayDroneStation.loadDroneService(self, xml, key)
    SprayDroneStation.initHomeYawOffset(self)
    SprayDroneStation.attachDroneCamera(self, xml)
    -- rozteč plošin musí stačit na oba drony s vrtulemi
    local root = spec.rootSpec
    local x1, _, z1 = getWorldTranslation(root.node)
    local x2, _, z2 = getWorldTranslation(spec.node)
    if MathUtil.vector2Length(x2 - x1, z2 - z1) < 2 * spec.droneRadius + 0.8 then
        Logging.xmlWarning(xml, "SprayDroneStation: plošiny dronů jsou blíž než 2 * droneRadius + 0,8 m")
    end
end

-- Zvuky a efekty jednoho dronu (spec dronu v kontextu, jen klient): rotor a postřik ze <sounds> bloku varianty (partsKey),
-- mlha postřiku z <effects>. Chybějící vzorek je nil a dron se bez něj obejde.
function SprayDroneStation.loadDroneSounds(self, xml, partsKey)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.samples = {}
    if not self.isClient then
        return
    end
    local function loadSample(name)
        return g_soundManager:loadSampleFromXML(xml, partsKey .. ".sounds", name, self.baseDirectory, self.components, 0,
            AudioGroup.VEHICLE, self.i3dMappings, self)
    end
    spec.samples.rotor = loadSample("rotor")
    spec.rotorVolumeScale = spec.samples.rotor ~= nil and g_soundManager:getSampleVolumeScale(spec.samples.rotor) or 1
    spec.samples.spray = loadSample("spray")
    local effectsKey = partsKey .. ".effects"
    spec.effects = SprayDroneStation.loadSprayMist(self, xml, effectsKey)
    SprayDroneStation.loadSprayEffectPlacement(self, xml, effectsKey)
end

-- ParticleEffect bere z uzlu efektu jen emitorový tvar a systém částic si vezme z vanilla šablony podle particleType, takže
-- vlastní Dynamic ze sprayMist.i3d nejde použít (hra hlásila "emitter mesh ... could not be loaded"). Proto se Dynamic načte
-- přímo jako v WorkParticles (particleNode): uzel z i3d (effectNode#filename, #node) se připojí k #linkNode a ParticleUtil z něj
-- postaví systém částic. Vrací seznam { node, particleSystem }, jeden záznam na trysku.
function SprayDroneStation.loadSprayMist(self, xml, key)
    local effects = {}
    xml:iterate(key .. ".effectNode", function(_, nodeKey)
        local filename = getXMLString(xml.handle, nodeKey .. "#filename")
        local nodePath = getXMLString(xml.handle, nodeKey .. "#node")
        local linkPath = getXMLString(xml.handle, nodeKey .. "#linkNode")
        local linkNode = linkPath ~= nil and I3DUtil.indexToObject(self.components, linkPath, self.i3dMappings) or nil
        if filename == nil or nodePath == nil or linkNode == nil then
            Logging.xmlWarning(xml, "SprayDroneStation: effectNode '%s' nemá filename, node nebo linkNode", nodeKey)
            return
        end
        local root = g_i3DManager:loadI3DFile(Utils.getFilename(filename, self.baseDirectory), false, false)
        local node = root ~= 0 and I3DUtil.indexToObject(root, nodePath) or nil
        if node == nil then
            Logging.xmlWarning(xml, "SprayDroneStation: uzel '%s' v '%s' nenalezen", nodePath, filename)
        else
            link(linkNode, node)
            local particleSystem = {}
            ParticleUtil.loadParticleSystemFromNode(node, particleSystem, false, true)
            table.insert(effects, { node = node, particleSystem = particleSystem })
        end
        if root ~= 0 then
            delete(root)
        end
    end)
    return effects
end

-- Barva mlhy podle přípravku: materiál mlhy (subUV) tónuje parametr colorAlpha (rgb se násobí s texturou), jako u vanilla částic
-- kol. Neznámý přípravek nebo chyba parametru nechá mlhu bílou.
SprayDroneStation.MIST_COLORS = {
    LIQUIDFERTILIZER = { 0.8, 0.92, 0.5 },
    HERBICIDE = { 0.82, 0.92, 1 },
}
SprayDroneStation.MIST_COLOR_DEFAULT = { 1, 1, 1 }

function SprayDroneStation.setSprayMistColor(effects, fillType)
    local name = g_fillTypeManager:getFillTypeNameByIndex(fillType)
    local color = SprayDroneStation.MIST_COLORS[name] or SprayDroneStation.MIST_COLOR_DEFAULT
    for _, effect in ipairs(effects) do
        local node = effect.particleSystem.shape or effect.node
        if getHasShaderParameter(node, "colorAlpha") then
            setShaderParameter(node, "colorAlpha", color[1], color[2], color[3], 1, false)
        end
    end
end

function SprayDroneStation.setSprayMistEmitting(effects, emitting)
    for _, effect in ipairs(effects) do
        ParticleUtil.setEmittingState(effect.particleSystem, emitting)
    end
end

function SprayDroneStation.deleteSprayMist(effects)
    for _, effect in ipairs(effects) do
        ParticleUtil.deleteParticleSystem(effect.particleSystem)
        if entityExists(effect.node) then
            delete(effect.node)
        end
    end
end

-- Parametry vleku a dronu z XML (atribut varianty drone(?), jinak společný ze <sprayDrone>); po loadDroneVariant.
function SprayDroneStation.loadParameters(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local droneKey = spec.droneKey
    -- atribut varianty (drone(?)), jinak společný ze <sprayDrone>; baterie bez dronu podle výchozí varianty
    local function value(name, default, variantKey)
        variantKey = variantKey or droneKey
        local v = variantKey ~= nil and xml:getValue(variantKey .. "#" .. name) or nil
        if v == nil then
            v = xml:getValue(key .. "#" .. name, default)
        end
        return v
    end
    spec.isLinked = true
    spec.droneIndex = 1
    spec.camera = droneKey ~= nil and xml:getValue(droneKey .. "#cameraIndex") or nil
    spec.outCamera = droneKey ~= nil and xml:getValue(droneKey .. "#outCameraIndex") or nil
    spec.layerOffset = 0
    spec.numDrones = spec.secondVariant ~= nil and 2 or 1
    spec.activeDrones = spec.numDrones
    spec.drones = { spec }
    spec.layerGap = xml:getValue(key .. "#layerGap", SprayDroneStation.LAYER_GAP)

    spec.fillUnitIndex = xml:getValue(key .. "#fillUnitIndex", 1)
    -- dosah se počítá z baterie a výšky přeletu (updateRange); range z XML je jen pevný strop
    spec.rangeCap = xml:getValue(key .. "#range")
    spec.maxRange = value("maxRange", 750) * SprayDroneStation.getConfigValue(self, xml, key, SprayDroneStation.ANTENNA_CONFIG, "rangeBonus", 1)
    spec.range = math.min(spec.maxRange, spec.rangeCap or math.huge)
    spec.rangeKey = nil
    spec.workWidth = value("workWidth", 9)
    spec.tankCapacity = value("tankCapacity", 40)
    local batteryKey = spec.batteryKey
    spec.batteryCapacity = value("batteryMinutes", 8, batteryKey) * 60
    spec.batteryKwh = value("batteryKwh", SprayDroneStation.BATTERY_KWH, batteryKey)
    spec.batteryMass = value("batteryMass", 0, batteryKey)
    -- droneMass ve variantě je bez baterie; spec.droneMass (pro let) je s baterií
    spec.droneMass = value("droneMass", 52) + spec.batteryMass
    spec.rotorPitch = value("rotorPitch", 1)
    spec.hoverFactor = xml:getValue(key .. "#batteryHoverFactor", 1.15)
    spec.climbFactor = xml:getValue(key .. "#batteryClimbFactor", 1.4)
    spec.descentFactor = xml:getValue(key .. "#batteryDescentFactor", 0.8)
    spec.batterySwapBelow = xml:getValue(key .. "#batterySwapBelow", 0.3)
    spec.trailerFoldEnd = math.clamp(xml:getValue(key .. "#trailerFoldEnd", 0.5), 0.05, 1)
    spec.cruiseSpeed = value("cruiseSpeed", 10)
    spec.sprayingSpeed = value("sprayingSpeed", 7)
    spec.climbSpeed = value("climbSpeed", 3)
    spec.ascentSpeed = value("ascentSpeed", 5)
    spec.acceleration = value("acceleration", 2.5)
    spec.yawSpeed = math.rad(value("yawSpeed", 90))
    spec.sprayHeight = value("sprayHeight", 3)
    spec.transitHeight = xml:getValue(key .. "#transitHeight", 12)
    spec.obstacleClearance = xml:getValue(key .. "#obstacleClearance", 5)
    spec.maxTransitHeight = xml:getValue(key .. "#maxTransitHeight", 60)
    spec.corridorHeight = xml:getValue(key .. "#corridorHeight", 8)
    spec.sideClearance = xml:getValue(key .. "#sideClearance", 4)
    spec.headlands = 0
    spec.headlandFirst = 1
    spec.droneRadius = value("droneRadius", 1.6)
    spec.turnAcceleration = math.max(value("turnAcceleration", 2.5), 0.1)
    spec.settingsVersion = 0
    for _, setting in ipairs(SprayDroneStation.SETTINGS) do
        spec[setting.key] = math.clamp(math.floor(spec[setting.key] + 0.5), setting.min, setting.max)
    end
    spec.usageScale = xml:getValue(key .. "#usageScale", 1) * SprayDroneStation.getConfigValue(self, xml, key, SprayDroneStation.GPS_CONFIG, "usageFactor", 1)
    spec.batteryReserve = xml:getValue(key .. "#batteryReserve", SprayDroneStation.BATTERY_RESERVE)
    spec.pumpRate = math.max(value("litersPerSecond", 1), 0.01)
    spec.securedFoldTime = xml:getValue(key .. "#securedFoldTime", 0.8)
    spec.batteryStowFrom = xml:getValue(key .. "#batteryStowFrom", SprayDroneStation.BATTERY_STOW_FROM)
    spec.batteryStowUntil = xml:getValue(key .. "#batteryStowUntil", SprayDroneStation.BATTERY_STOW_UNTIL)
end

-- Elektrocentrála, nabíječka a baterie dronu (po loadParameters).
function SprayDroneStation.loadPower(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local batteryKey = spec.batteryKey
    -- elektrocentrála a nabíječka: všechny baterie v ní se nabíjejí najednou, každá 65 % kapacity (30 % -> 95 %) za
    -- chargeMinutes; nafta dieselPerHour na každou nabíjenou
    local powerKey = key .. ".power"
    spec.dieselFillUnitIndex = xml:getValue(powerKey .. "#dieselFillUnitIndex", 2)
    SprayDroneStation.loadMixer(self, xml, key .. ".mixer")
    local function powerValue(name, default)
        local v = batteryKey ~= nil and xml:getValue(batteryKey .. "#" .. name) or nil
        return v or xml:getValue(powerKey .. "#" .. name, default)
    end
    -- počet centrál z konfigurace: každá nabíjí baterie svou rychlostí (chargeMinutes), takže dvě nabíjejí dvakrát rychleji a spotřebují
    -- za stejnou dobu dvakrát tolik (na jednu nabitou baterii stejně); nádrž na naftu je tolikrát větší
    local generatorId = self.configurations ~= nil and self.configurations[SprayDroneStation.GENERATOR_CONFIG] or nil
    spec.numGenerators = 1
    if generatorId ~= nil then
        spec.numGenerators = math.clamp(xml:getValue(string.format("%s.%sConfigurations.%sConfiguration(%d)#count", key,
            SprayDroneStation.GENERATOR_CONFIG, SprayDroneStation.GENERATOR_CONFIG, generatorId - 1), 1), 1, 2)
    end
    spec.chargeRate = spec.numGenerators * SprayDroneStation.CHARGE_SPAN * spec.batteryCapacity
        / (math.max(powerValue("chargeMinutes", 10), 0.1) * 60)
    spec.dieselPerSecond = spec.numGenerators * powerValue("dieselPerHour", 2.2) / 3600
    local fuelUnit = self.getFillUnitByIndex ~= nil and self:getFillUnitByIndex(spec.dieselFillUnitIndex) or nil
    if fuelUnit ~= nil then
        fuelUnit.capacity = xml:getValue(powerKey .. "#dieselPerGenerator", 30) * spec.numGenerators
    end
    spec.readyCharge = math.clamp(xml:getValue(powerKey .. "#readyLevel", 0.95), 0.1, 1) * spec.batteryCapacity
    spec.swapTime = xml:getValue(powerKey .. "#swapTime", 5) * 1000
    -- baterie: počet z konfigurace v obchodě (0..počet šachet, typ podle dronu); na začátku plné, baterie k ve slotu k (dron bez baterie)
    local numBatteries = xml:getValue(powerKey .. "#batteries", 3)
    local configId = self.configurations ~= nil and self.configurations[SprayDroneStation.BATTERY_CONFIG] or nil
    if configId ~= nil then
        numBatteries = xml:getValue(string.format("%s.%sConfigurations.%sConfiguration(%d)#count", key, SprayDroneStation.BATTERY_CONFIG,
            SprayDroneStation.BATTERY_CONFIG, configId - 1), numBatteries)
    end
    spec.numBatterySlots = math.clamp(xml:getValue(powerKey .. "#slots", 5), 1, SprayDroneStation.MAX_BATTERY_SLOTS)
    spec.batterySlotBits = 1
    while 2 ^ spec.batterySlotBits <= spec.numBatterySlots do
        spec.batterySlotBits = spec.batterySlotBits + 1
    end
    spec.batteries = {}
    for k = 1, math.clamp(numBatteries, 0, spec.numBatterySlots) do
        spec.batteries[k] = { charge = spec.batteryCapacity, slot = k, drone = 1 }
    end
    spec.droneBattery = nil
    SprayDroneStation.loadServiceParts(self, xml, key)
    spec.generatorEnabled = true
    spec.generatorRunning = false
    spec.powerSyncTimer = 0
end

-- Stav vleku z uložené hry (po načtení všech dronů a baterií).
function SprayDroneStation.loadFromSavegame(self, savegame)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local saveKey = savegame.key .. "." .. SprayDroneStation.MOD_NAME .. ".sprayDroneStation"
    spec.fieldId = savegame.xmlFile:getValue(saveKey .. "#fieldId", 0)
    -- po změně konfigurace v dílně se vozidlo načte z uložení znovu: baterií nad počet konfigurace se zahodí, nabití je
    -- v podílu (baterie nového typu mají stejné procento), náplň nad nádrž nové varianty se ořízne
    SprayDroneStation.loadDroneSave(self, savegame.xmlFile, saveKey)
    SprayDroneDrones.runAs(self, 2, SprayDroneStation.loadDroneSave, savegame.xmlFile, saveKey .. ".drone2")
    for _, battery in ipairs(spec.batteries) do
        battery.slot = -1
    end
    savegame.xmlFile:iterate(saveKey .. ".battery", function(k, batteryKey)
        local battery = spec.batteries[k]
        if battery ~= nil then
            local level = savegame.xmlFile:getValue(batteryKey .. "#level", 1)
            battery.charge = math.clamp(level, 0, 1) * spec.batteryCapacity
            local slot = savegame.xmlFile:getValue(batteryKey .. "#slot", k)
            if slot == 0 then
                local owner = savegame.xmlFile:getValue(batteryKey .. "#drone", 1)
                local droneSpec = SprayDroneDrones.getSpec(self, owner)
                if droneSpec ~= nil and droneSpec.hasDrone and droneSpec.droneBattery == nil then
                    droneSpec.droneBattery = k
                    battery.slot = 0
                    battery.drone = owner
                end
            elseif slot ~= nil and slot >= 1 and slot <= spec.numBatterySlots and SprayDroneStation.getBatteryInSlot(self, slot) == nil then
                battery.slot = slot
            end
        end
    end)
    for _, battery in ipairs(spec.batteries) do
        if battery.slot < 0 then
            battery.slot = SprayDroneStation.getFreeBatterySlot(self)
        end
    end
    SprayDroneDrones.forEachSpec(self, function(droneSpec)
        droneSpec.battery = droneSpec.droneBattery ~= nil and spec.batteries[droneSpec.droneBattery].charge or 0
    end)
    spec.generatorEnabled = savegame.xmlFile:getValue(saveKey .. "#generatorEnabled", true)
    spec.coverage = SprayDroneRoute.decodeCoverage(savegame.xmlFile:getValue(saveKey .. "#coverage"))
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
    for _, setting in ipairs(SprayDroneStation.SETTINGS) do
        local value = savegame.xmlFile:getValue(saveKey .. ".flightSettings#" .. setting.key)
        if value ~= nil then
            spec[setting.key] = math.clamp(math.floor(value + 0.5), setting.min, setting.max)
        end
    end
    spec.activeDrones = math.clamp(spec.activeDrones, 1, spec.numDrones)
    SprayDroneDrones.forEach(self, SprayDroneStation.resumeMissionAfterLoad)
end

function SprayDroneStation:onLoad(savegame)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local xml = self.xmlFile
    local key = "vehicle.sprayDrone"

    SprayDroneStation.loadDroneVariant(self, xml, key)
    SprayDroneStation.loadParameters(self, xml, key)
    SprayDroneStation.loadPower(self, xml, key)

    spec.navLightIntensity = xml:getValue(key .. ".navLights#intensity", 4)
    spec.navBlinkPeriod = math.max(xml:getValue(key .. ".navLights#blinkPeriod", 1), 0.1) * 1000
    spec.navBlinkOn = xml:getValue(key .. ".navLights#blinkOn", 0.5) * 1000
    spec.navLights = {}
    spec.foldParts = {}
    spec.rotors = {}
    spec.tiltNode = nil
    if spec.hasDrone then
        SprayDroneStation.loadDroneParts(self, xml, key, spec.droneKey)
    end
    SprayDroneStation.applyPropellerLook(self, xml, key)
    SprayDroneStation.initDroneState(self)

    if spec.hasDrone then
        SprayDroneStation.loadDroneSounds(self, xml, spec.droneKey)
    else
        spec.samples = {}
    end
    if self.isClient then
        SprayDroneSound.loadSounds(self, xml, key)
        SprayDroneStation.loadExhaust(self, xml, key .. ".power.exhaust", "#node", "exhaust")
        if spec.numGenerators >= 2 then
            SprayDroneStation.loadExhaust(self, xml, key .. ".power.exhaust", "#node2", "exhaust2")
        end
    end
    SprayDroneStation.applyNavLights(self, false)
    spec.flightAreas = {}
    spec.coverage = {}
    spec.coverageSyncTime = 0
    spec.areaVersion = 0
    spec.fieldId = 0
    spec.actionEvents = {}
    spec.actionStates = {}

    spec.dirtyFlag = self:getNextDirtyFlag()
    spec.coverageDirtyFlag = self:getNextDirtyFlag()
    spec.positionDirtyFlag = self:getNextDirtyFlag()
    spec.flightSyncTimer = 0
    SprayDroneStation.initHomeYawOffset(self)
    SprayDroneStation.attachDroneCamera(self, xml)
    SprayDroneStation.loadSecondDrone(self, xml, key)
    spec.firstDroneCamera = nil
    for k = 1, spec.numDrones do
        local camera = spec.drones[k].camera
        if camera ~= nil and (spec.firstDroneCamera == nil or camera < spec.firstDroneCamera) then
            spec.firstDroneCamera = camera
        end
    end
    spec.droneCameraRequested = false

    if savegame ~= nil and not savegame.resetVehicles then
        SprayDroneStation.loadFromSavegame(self, savegame)
    end
    SprayDroneToolbox.load(self, savegame)
    SprayDroneRelaySlots.load(self, savegame)
    SprayDronePad.load(self)
    SprayDronePad.openInShop(self)
    SprayDroneLevel.load(self)
    SprayDroneLadder.load(self)
    if SprayDroneLink ~= nil then
        SprayDroneLink.loadScreen(self)
    end
    -- Foldable má v onLoad čas skládání ze savegame (getFoldAnimTime), takže uložený rozložený vlek má dron rozložený hned
    SprayDroneDrones.forEach(self, SprayDroneStation.initDroneFold)
    SprayDroneStation.updateServiceVisuals(self, 0)
end

-- Uložený stav jednoho dronu (baseKey = vlek pro dron 1, .drone2 pro druhý).
function SprayDroneStation.loadDroneSave(self, xmlFile, baseKey)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.missionActive = xmlFile:getValue(baseKey .. "#missionActive", false)
    spec.droneFillLevel = xmlFile:getValue(baseKey .. "#droneFillLevel", 0)
    local fillTypeName = xmlFile:getValue(baseKey .. "#droneFillType")
    spec.droneFillType = g_fillTypeManager:getFillTypeIndexByName(fillTypeName) or FillType.UNKNOWN
    spec.droneFillLevel = math.clamp(spec.droneFillLevel, 0, spec.hasDrone and spec.tankCapacity or 0)
    if spec.droneFillLevel <= 0 then
        spec.droneFillType = FillType.UNKNOWN
    end
end

function SprayDroneStation.resumeMissionAfterLoad(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.missionActive = spec.missionActive and spec.hasDrone and #spec.batteries > 0
    if spec.missionActive then
        -- po načtení dron stojí na vleku; misi obnoví servis, trasa se spočítá ze stavu pole
        spec.state = SprayDroneStation.STATE_SERVICING
        spec.serviceTimer = SprayDroneStation.RESUME_AFTER_LOAD_TIME
    end
end

function SprayDroneStation.initDroneFold(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.unfold = SprayDroneStation.getTrailerUnfold(self)
    SprayDroneStation.applyFold(self)
    if spec.unfold < 1 and spec.droneBattery ~= nil then
        SprayDroneStation.unloadDroneBattery(self)
    end
end

function SprayDroneStation:saveToXMLFile(xmlFile, key, usedModNames)
    local spec = self[SprayDroneStation.SPEC_NAME]
    xmlFile:setValue(key .. "#fieldId", spec.fieldId)
    SprayDroneStation.saveDrone(self, xmlFile, key)
    SprayDroneDrones.runAs(self, 2, SprayDroneStation.saveDrone, xmlFile, key .. ".drone2")
    xmlFile:setValue(key .. "#generatorEnabled", spec.generatorEnabled)
    local coverage = SprayDroneRoute.encodeCoverage(spec.coverage)
    if coverage ~= "" then
        xmlFile:setValue(key .. "#coverage", coverage)
    end
    SprayDroneDrones.forEach(self, SprayDroneStation.syncDroneBatteryCharge)
    for k, battery in ipairs(spec.batteries) do
        local batteryKey = string.format("%s.battery(%d)", key, k - 1)
        xmlFile:setValue(batteryKey .. "#level", battery.charge / spec.batteryCapacity)
        xmlFile:setValue(batteryKey .. "#slot", battery.slot)
        if battery.slot == 0 then
            xmlFile:setValue(batteryKey .. "#drone", battery.drone or 1)
        end
    end
    for _, setting in ipairs(SprayDroneStation.SETTINGS) do
        xmlFile:setValue(key .. ".flightSettings#" .. setting.key, spec[setting.key])
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
    SprayDroneToolbox.save(self, xmlFile, key)
    SprayDroneRelaySlots.save(self, xmlFile, key)
end

-- Uložení jednoho dronu (baseKey = vlek pro dron 1, .drone2 pro druhý).
function SprayDroneStation.saveDrone(self, xmlFile, baseKey)
    local spec = self[SprayDroneStation.SPEC_NAME]
    xmlFile:setValue(baseKey .. "#missionActive", spec.missionActive)
    xmlFile:setValue(baseKey .. "#droneFillLevel", spec.droneFillLevel)
    local fillTypeName = g_fillTypeManager:getFillTypeNameByIndex(spec.droneFillType)
    if fillTypeName ~= nil then
        xmlFile:setValue(baseKey .. "#droneFillType", fillTypeName)
    end
end

-- Úklid jednoho dronu: hotspot, dron ve vzduchu zpět na vlek, zvuk rotorů a efekty postřiku.
function SprayDroneStation.deleteDrone(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    SprayDroneHotspot.delete(spec)
    -- dron létající pod kořenem scény by po smazání vleku zůstal ve světě (prodej, smazání vleku za letu): vrátí se pod vlek
    -- a smaže se s ním; bez živého rodiče se smaže sám
    if spec.node ~= nil and not spec.isLinked and entityExists(spec.node) then
        if spec.parent ~= nil and entityExists(spec.parent) then
            SprayDroneStation.attachDrone(self)
        else
            delete(spec.node)
            spec.node = nil
        end
    end
    spec.path = nil
    spec.batchRelays = {}
    if spec.samples ~= nil then
        g_soundManager:deleteSamples(spec.samples)
    end
    if spec.effects ~= nil then
        SprayDroneStation.deleteSprayMist(spec.effects)
    end
end

function SprayDroneStation:onDelete()
    local spec = self[SprayDroneStation.SPEC_NAME]
    SprayDroneToolbox.delete(self)
    SprayDroneRelaySlots.delete(self)
    SprayDroneLadder.delete(self)
    if spec ~= nil then
        if SprayDroneLink ~= nil then
            SprayDroneLink.deleteScreen(self)
        end
        SprayDroneDrones.forEach(self, SprayDroneStation.deleteDrone)
    end
    SprayDroneSound.deleteSounds(self)
    for _, field in ipairs({ "exhaust", "exhaust2" }) do
        if spec ~= nil and spec[field] ~= nil and spec[field].requestId ~= nil then
            g_i3DManager:releaseSharedI3DFile(spec[field].requestId)
        end
    end
end

function SprayDroneStation:getIsFoldAllowed(superFunc, direction, onAiTurnOn)
    if not self:getSprayDroneIsParked() then
        -- vlastní skládání vleku (směr > 0) dron nejdřív odvolá domů, složit jde až po přistání. Jen když skládá tento vlek
        -- hráč, který ho má vybraný: vanilla „složit vše“ na tahači se ptá i připojených nářadí (se směrem tahače), to
        -- dron odvolávat nemá
        if SprayDroneStation.foldAllActive then
            return false, g_i18n:getText("sdt_warning_droneFlyingFoldAll")
        end
        if direction ~= nil and direction > 0 and direction == self:getToggledFoldDirection()
            and (self:getIsEntered() or self:getIsActiveForInput()) then
            self:sprayDroneCommand(SprayDroneCommandEvent.RETURN_HOME, 0)
        end
        return false, g_i18n:getText("sdt_warning_droneFlying")
    end
    if SprayDroneDrones.any(self, function(d) return d.rotorSpeed > 0 or not d.rotorsParked end) then
        -- složené listy musí mířit podél ramene: nejdřív doběh a dotočení vrtulí do klidové polohy
        return false, g_i18n:getText("sdt_warning_rotorsSpinning")
    end
    if direction ~= nil and direction < 0 then
        local allowed, warning = SprayDronePad.checkDeploy(self)
        if allowed then
            allowed, warning = SprayDroneLevel.checkDeploy(self)
        end
        if not allowed then
            return false, warning
        end
    end
    return superFunc(self, direction, onAiTurnOn)
end

-- Nafta po centrálách: každá centrála má na vleku vlastní nádrž s hrdlem (dieselNeckNode, dieselNeckNode2), ve skriptu jsou
-- ale obě jedna fillUnit, ze které se plní i spotřebovává společně. Ukazatel ji proto dělí rovnoměrně: dílek = nádrž jedné
-- centrály (fillLevel v dílcích, zlomek = rozpitá nádrž), v titulku procenta po centrálách. Dva samostatné řádky nafty
-- nejdou, ukazatel sčítá řádky stejného typu náplně (ControlBarDisplay:addFillLevel).
function SprayDroneStation.getDieselSteps(level, capacity, numGenerators)
    if capacity == nil or capacity <= 0 or numGenerators == nil or numGenerators < 1 then
        return 0, 0, {}
    end
    local ratio = math.max(0, math.min(1, (level or 0) / capacity))
    local percents = {}
    for i = 1, numGenerators do
        percents[i] = ratio * 100
    end
    return ratio * numGenerators, numGenerators, percents
end

-- Vanilla ukazatel naplnění vpravo dole kreslí řádky zdola nahoru v pořadí přidání (FillLevelsDisplay:draw), nejvýš 5:
-- dole nafta a baterie, pak nádrže vleku (hlavní, koncentrát). Vanilla řádky se proto nejdřív posbírají a přidají až
-- ve správném pořadí. Baterie jsou jeden řádek po kusech (TYPE_STEP: plné dílky = připravené), dron i nabíječka
-- dohromady. Se dvěma centrálami (Max) je i nafta jeden řádek po kusech, viz getDieselSteps.
function SprayDroneStation:getFillLevelInformation(superFunc, display)
    local rows = {}
    local collector = setmetatable({ addFillLevel = function(_, ...)
        table.insert(rows, { n = select("#", ...), ... })
    end }, { __index = display })
    superFunc(self, collector)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local splitDiesel = (spec.numGenerators or 1) >= 2
    local function addRows(diesel)
        for _, row in ipairs(rows) do
            if (row[1] == FillType.DIESEL) == diesel and not (diesel and splitDiesel) then
                display:addFillLevel(unpack(row, 1, row.n))
            end
        end
    end
    addRows(true)
    if splitDiesel then
        local steps, numSteps, percents = SprayDroneStation.getDieselSteps(self:getFillUnitFillLevel(spec.dieselFillUnitIndex),
            self:getFillUnitCapacity(spec.dieselFillUnitIndex), spec.numGenerators)
        if numSteps > 0 then
            local parts = {}
            for i, percent in ipairs(percents) do
                parts[i] = string.format("%.0f", percent)
            end
            display:addFillLevel(FillType.DIESEL, steps, numSteps, 0, false, FillLevelsDisplay.TYPE_STEP,
                string.format(g_i18n:getText("sdt_fill_dieselGenerators"), table.concat(parts, " · ")))
        end
    end
    -- baterie: dílek na každou (v dronech i v nabíječce), plné dílky = připravené (aspoň readyCharge); nabití po kusech
    -- v titulku, baterie v dronech první s označením (TYPE_STEP doplňkový text nekreslí). Nádrž dronu se v ukazateli
    -- nezobrazuje (Pavel 2026-10-07): u zaparkovaného dronu šlo jen o duplicitní řádek k nádrži vleku.
    local count, ready, parts = 0, 0, {}
    SprayDroneDrones.forEachSpec(self, function(d, k)
        if not d.hasDrone or d.droneBattery == nil then
            return
        end
        count = count + 1
        if d.battery >= d.readyCharge - 0.01 then
            ready = ready + 1
        end
        table.insert(parts, string.format(g_i18n:getText("sdt_fill_batteryDrone"), d.battery / d.batteryCapacity * 100))
    end)
    for _, battery in ipairs(spec.batteries) do
        if battery.slot > 0 then
            count = count + 1
            if battery.charge >= spec.readyCharge - 0.01 then
                ready = ready + 1
            end
            table.insert(parts, string.format("%.0f", battery.charge / spec.batteryCapacity * 100))
        end
    end
    if count > 0 then
        local title = string.format(g_i18n:getText(spec.generatorRunning and "sdt_fill_batteriesCharging" or "sdt_fill_batteries"),
            table.concat(parts, " · "))
        display:addFillLevel(FillType.ELECTRICCHARGE, ready, count, 0, false, FillLevelsDisplay.TYPE_STEP, title)
    end
    addRows(false)
end

-- Dron stojí na složeném vleku a úchyty na lyžinách jsou zavřené (čas skládání za securedFoldTime).
function SprayDroneStation.getIsDroneSecured(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return spec.isLinked and self:getFoldAnimTime() >= spec.securedFoldTime - 0.001
end

-- Smí hráč z tohoto spojení s vlekem nakládat (farma, která k vozidlu smí)? Pro události na serveru; vzdálenost se nevyžaduje,
-- plánovač a příkazy jdou i z kabiny tahače.
function SprayDroneStation.isConnectionAllowed(self, connection)
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    local player = system ~= nil and system:getPlayerByConnection(connection) or nil
    return player ~= nil and g_currentMission.accessHandler:canFarmAccess(player.farmId, self)
end

function SprayDroneStation:getSprayDroneIsParked()
    return not SprayDroneDrones.any(self, function(d)
        return d.state ~= SprayDroneStation.STATE_PARKED and d.state ~= SprayDroneStation.STATE_SERVICING
    end)
end

---------------------------------------------------------------------------------------------------
-- parametry a pomocné výpočty

function SprayDroneStation.getHomePosition(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local x, y, z
    if spec.isLinked then
        x, y, z = getWorldTranslation(spec.node or spec.parent)
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
    return MathUtil.getYRotationFromDirection(dx, dz) + (spec.homeYawOffset or 0)
end

-- O kolik je dron na plošině natočený vůči směru svého rodiče (přední dron na vleku se dvěma drony sedí nosem dozadu).
function SprayDroneStation.initHomeYawOffset(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.homeYawOffset = 0
    if spec.node == nil or spec.parent == nil then
        return
    end
    local fx, _, fz = localDirectionToWorld(spec.node, 0, 0, 1)
    local px, _, pz = localDirectionToWorld(spec.parent, 0, 0, 1)
    spec.homeYawOffset = MathUtil.getAngleDifference(MathUtil.getYRotationFromDirection(fx, fz), MathUtil.getYRotationFromDirection(px, pz))
end

-- VehicleCamera si při načtení zapamatuje výchozí polohu a natočení kamery (a vrací je při každém přepnutí na ni): po přepojení
-- pod dron se musí zapamatovat nové.
local function resyncCamera(self, node)
    local enterable = self.spec_enterable
    for _, camera in ipairs(enterable ~= nil and enterable.cameras or {}) do
        if camera.cameraNode == node then
            local rotateNode, positionNode = camera.rotateNode or node, camera.cameraPositionNode or node
            camera.origRotX, camera.origRotY, camera.origRotZ = getRotation(rotateNode)
            camera.rotX, camera.rotY, camera.rotZ = camera.origRotX, camera.origRotY, camera.origRotZ
            camera.origTransX, camera.origTransY, camera.origTransZ = getTranslation(positionNode)
            camera.transX, camera.transY, camera.transZ = camera.origTransX, camera.origTransY, camera.origTransZ
            local length = MathUtil.vector3Length(camera.origTransX, camera.origTransY, camera.origTransZ) + 0.00001
            camera.zoom, camera.zoomTarget, camera.zoomDefault = length, length, length
            camera.transDirX, camera.transDirY, camera.transDirZ = camera.origTransX / length, camera.origTransY / length, camera.origTransZ / length
        end
    end
end

-- Kamery dronu: pohled z dronu (uzel kamery se připojí pod uzel náklonu a pootočí dolů, aby letěl s ním a za letem se nakláněl;
-- myší se rozhlíží) a vnější pohled na dron (střed otáčení pod uzlem dronu, myší se kolem něj otáčí a přibližuje). Čísla kamer
-- v enterable.cameras jsou drone(?)#cameraIndex a #outCameraIndex.
function SprayDroneStation.attachDroneCamera(self, xml)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.droneKey == nil or not spec.hasDrone then
        return
    end
    local node = xml:getValue(spec.droneKey .. "#cameraNode", nil, self.components, self.i3dMappings)
    if node == nil or spec.tiltNode == nil then
        spec.camera = nil
        return
    end
    link(spec.tiltNode, node)
    local x, y, z = xml:getValue(spec.droneKey .. "#cameraTrans")
    setTranslation(node, x or 0, y or 0, z or 0)
    local pitch = math.rad(xml:getValue(spec.droneKey .. "#cameraPitch", 15))
    -- kamera se dívá po -Z svého uzlu: +Z uzlu míří proti směru pohledu (dopředu a dolů, tedy +Z uzlu dozadu a dolů)
    setDirection(node, 0, -math.sin(pitch), -math.cos(pitch), 0, 1, 0)
    resyncCamera(self, node)

    local target = xml:getValue(spec.droneKey .. "#outTargetNode", nil, self.components, self.i3dMappings)
    if target ~= nil and spec.node ~= nil then
        link(spec.node, target)
        local tx, ty, tz = xml:getValue(spec.droneKey .. "#outTargetTrans")
        setTranslation(target, tx or 0, ty or 0.3, tz or 0)
        resyncCamera(self, getChildAt(target, 0))
    else
        spec.outCamera = nil
    end
end

-- Nastavení letu z plánovače ({transitHeight, obstacleClearance, sideClearance} v celých metrech, headlands počet
-- úvratí, headlandFirst 0/1). Jde eventem na server a od něj ke všem klientům; přepočítá se dosah i trasa.
function SprayDroneStation:setSprayDroneSettings(settings, noEventSend)
    local spec = self[SprayDroneStation.SPEC_NAME]
    for _, setting in ipairs(SprayDroneStation.SETTINGS) do
        local value = settings[setting.key]
        if value ~= nil then
            spec[setting.key] = math.clamp(math.floor(value + 0.5), setting.min, setting.max)
        end
    end
    spec.activeDrones = math.clamp(spec.activeDrones, 1, spec.numDrones)
    SprayDroneSettingsEvent.sendEvent(self, SprayDroneStation.getSettings(self), noEventSend)
    spec.settingsVersion = spec.settingsVersion + 1
    SprayDroneDrones.forEachSpec(self, function(d)
        d.transitCache, d.transitCacheSize = {}, 0
        d.rangeKey = nil
        d.routeDirty = true
    end)
end

-- Přepočet náhledu trasy všech dronů při příští příležitosti (změna pole, plochy, pokrytí).
function SprayDroneStation.markRouteDirty(self)
    SprayDroneDrones.forEachSpec(self, function(d)
        d.routeDirty = true
    end)
end

function SprayDroneStation.getSettings(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local settings = {}
    for _, setting in ipairs(SprayDroneStation.SETTINGS) do
        settings[setting.key] = spec[setting.key]
    end
    return settings
end

-- Jde nastavení index měnit? (Začátek úvratěmi / řádky má smysl jen s aspoň jednou úvratí.)
function SprayDroneStation.isSettingEnabled(self, index)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local setting = SprayDroneStation.SETTINGS[index]
    return setting ~= nil and (setting.requires == nil or spec[setting.requires] > 0)
        and (setting.minDrones == nil or spec.numDrones >= setting.minDrones)
end

-- Změna jednoho nastavení (index do SETTINGS) o delta (metry, kusy, u výběru o jednu volbu); vrací, jestli se hodnota změnila.
function SprayDroneStation.changeSetting(self, index, delta)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local setting = SprayDroneStation.SETTINGS[index]
    if setting == nil or not SprayDroneStation.isSettingEnabled(self, index) then
        return false
    end
    local value = math.clamp(spec[setting.key] + delta, setting.min, setting.max)
    if value == spec[setting.key] then
        return false
    end
    local settings = SprayDroneStation.getSettings(self)
    settings[setting.key] = value
    self:setSprayDroneSettings(settings)
    return true
end

-- Dosah z energie plné baterie ve výšce přeletu (SprayDroneRoute.getBatteryRange), počítá se znovu jen při změně
-- výšky, přípravku (hmotnost) nebo výšky plošiny; nejvýš maxRange a pevný range z XML. Volá se každý snímek, vstupy se
-- proto kontrolují nejvýš jednou za RANGE_CHECK_TIME (rangeKey = nil vynutí kontrolu hned).
function SprayDroneStation.updateRange(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local key = spec.rangeKey
    if key ~= nil and g_time < key.time then
        return spec.range
    end
    local _, _, restHeight = SprayDroneStation.getHomePosition(self)
    local massPerLiter = SprayDroneStation.getMassPerLiter(self)
    local height = spec.transitHeight + spec.layerOffset
    -- relé tyče: o kolik metrů prodlužují dosah rádia (SprayDroneLink.getRangeBonus)
    local relayBonus = SprayDroneLink ~= nil and SprayDroneLink.getRangeBonus(self, spec.maxRange) or 0
    local changed = key == nil or key.height ~= height or math.abs(key.mass - massPerLiter) > 0.0005
        or math.abs(key.rest - restHeight) > 0.05 or math.abs((key.relay or 0) - relayBonus) > 1
    if key == nil then
        key = {}
        spec.rangeKey = key
    end
    key.time = g_time + SprayDroneStation.RANGE_CHECK_TIME
    if changed then
        key.height, key.mass, key.rest, key.relay = height, massPerLiter, restHeight, relayBonus
        local p = SprayDroneStation.getFlightParams(self, nil, restHeight)
        local range = math.min(SprayDroneRoute.getBatteryRange(p, p.transitHeight, spec.tankCapacity, spec.maxRange + relayBonus), spec.rangeCap or math.huge)
        if range ~= spec.range then
            spec.range = range
            spec.routeDirty = true
        end
    end
    return spec.range
end

local function cacheTransit(spec, key, value)
    if spec.transitCacheSize >= SprayDroneStation.TRANSIT_CACHE_SIZE then
        spec.transitCache, spec.transitCacheSize = {}, 0
    end
    spec.transitCache[key] = value
    spec.transitCacheSize = spec.transitCacheSize + 1
end

-- Je přejezd mezi řádky (body {x, z}) ve výšce postřiku volný v šíři dronu? Vodorovné paprsky, výsledek se pamatuje.
function SprayDroneStation.getIsTurnClear(self, points)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local a, b = points[1], points[#points]
    local key = string.format("turn:%.1f:%.1f:%.1f:%.1f:%d", a.x, a.z, b.x, b.z, spec.settingsVersion)
    local cached = spec.transitCache[key]
    if cached ~= nil then
        return cached.clear
    end
    local clear = true
    local halfWidth = spec.droneRadius + SprayDroneStation.GUARD_SIDE_MARGIN
    local h = spec.sprayHeight + SprayDroneRoute.OBSTACLE_RAY_LIFT
    for k = 2, #points do
        local p1, p2 = points[k - 1], points[k]
        local y1 = getTerrainHeightAtWorldPos(g_terrainNode, p1.x, 0, p1.z) + h
        local y2 = getTerrainHeightAtWorldPos(g_terrainNode, p2.x, 0, p2.z) + h
        if SprayDroneRoute.getBandHit({ x = p1.x, z = p1.z, y = y1 }, { x = p2.x, z = p2.z, y = y2 }, halfWidth) ~= nil then
            clear = false
            break
        end
    end
    cacheTransit(spec, key, { clear = clear })
    return clear
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
    SprayDroneStation.markRouteDirty(self)
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

-- Přelet mezi vlekem a bodem (x, z) na poli (SprayDroneRoute.buildTransit, výsledek se pamatuje): outbound = z vleku
-- (svislý vzlet, profil, na konci výška postřiku), jinak na vlek (z výšky opts.startH nebo postřiku, přistání).
-- dir je směr řádku / letu v bodě: přílet a odlet se k němu stočí přes bod APPROACH_LENGTH před / za ním. Bez letové
-- plochy přímo ve výšce nad překážkami (nejméně transitHeight), s plochou nejkratší cestou v ní nízko (corridorHeight),
-- zaoblení jen uvnitř plochy. Vrací nil a NO_PATH_*, když cesta plochou není.
function SprayDroneStation.getTransit(self, x, z, outbound, dirX, dirZ, opts)
    local spec = self[SprayDroneStation.SPEC_NAME]
    opts = opts or {}
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local startH = outbound and restHeight + SprayDroneRoute.TAKEOFF_LIFT or (opts.startH or spec.sprayHeight)
    local endH = outbound and spec.sprayHeight or restHeight + SprayDroneRoute.LANDING_LIFT
    local key = string.format("%s:%.1f:%.1f:%.2f:%.2f:%.1f:%.0f:%.0f:%d:%d:%d:%s", tostring(outbound), x, z, dirX or 0, dirZ or 0, startH,
        hx, hz, spec.settingsVersion, spec.areaVersion, spec.fieldId, tostring(opts.tolerance))
    local cached = spec.transitCache[key]
    if cached == nil then
        local plan, noPath = SprayDroneStation.makeTransit(self, x, z, outbound, dirX, dirZ, opts.tolerance, startH, endH)
        cached = { plan = plan, noPath = noPath }
        cacheTransit(spec, key, cached)
    end
    return cached.plan, cached.noPath
end

-- Přílet po směru řádku / odlet po směru letu přes bod APPROACH_LENGTH před / za ním, jen když se kvůli tomu nemusí
-- otočit skoro nazpět (vlek je za zády víc než EXTENSION_MAX_TURN): pak je lepší otočit se na místě.
function SprayDroneStation.getUseExtension(self, x, z, outbound, dirX, dirZ)
    if dirX == nil then
        return false
    end
    local hx, hz = SprayDroneStation.getHomePosition(self)
    local tx, tz = hx - x, hz - z
    local tl = math.sqrt(tx * tx + tz * tz)
    if tl < 0.01 then
        return false
    end
    return (dirX * tx + dirZ * tz) / tl * (outbound and -1 or 1) >= math.cos(SprayDroneStation.EXTENSION_MAX_TURN)
end

-- direct: bez letové plochy (návrat domů, když cesta plochou není).
function SprayDroneStation.makeTransit(self, x, z, outbound, dirX, dirZ, tolerance, startH, endH, direct)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local c = not direct and SprayDroneStation.getCorridor(self) or nil
    local ex, ez = x, z
    if SprayDroneStation.getUseExtension(self, x, z, outbound, dirX, dirZ) then
        local e = SprayDroneRoute.APPROACH_LENGTH * (outbound and -1 or 1)
        ex, ez = x + dirX * e, z + dirZ * e
        if c ~= nil and not SprayDroneRoute.isInCorridor(c, ex, ez) then
            ex, ez = x, z
        end
    end
    local raw, minHeight = { { x = x, z = z }, { x = ex, z = ez } }, spec.transitHeight + spec.layerOffset
    if c == nil then
        table.insert(raw, { x = hx, z = hz })
    else
        if not c.homeOk then
            return nil, SprayDroneStation.NO_PATH_HOME
        end
        local path = SprayDroneStation.getHomePath(self, ex, ez, 1, tolerance)
        if path == nil then
            return nil, SprayDroneStation.NO_PATH_AREA
        end
        for _, pt in ipairs(path) do
            table.insert(raw, { x = pt.x, z = pt.z })
        end
        minHeight = spec.corridorHeight + spec.layerOffset
    end
    local points = {}
    for _, pt in ipairs(raw) do
        local last = points[#points]
        if last == nil or MathUtil.vector2Length(pt.x - last.x, pt.z - last.z) > 0.05 then
            table.insert(points, pt)
        end
    end
    if #points < 2 then
        table.insert(points, { x = hx, z = hz })
    end
    if outbound then
        local reversed = {}
        for k = #points, 1, -1 do
            table.insert(reversed, points[k])
        end
        points = reversed
    end
    local check = nil
    if c ~= nil then
        check = function(arc)
            for k = 2, #arc do
                if not SprayDroneRoute.isCorridorSegmentFree(c, arc[k - 1].x, arc[k - 1].z, arc[k].x, arc[k].z) then
                    return false
                end
            end
            return true
        end
    end
    local p = SprayDroneStation.getFlightParams(self, nil, restHeight)
    return SprayDroneRoute.buildTransit(points, minHeight, startH, endH, p, outbound, check)
end

-- Rozložení dronu (0..1) z času skládání vleku: dron se skládá na začátku skládání (0..trailerFoldEnd), takže
-- při rozkládání vleku se rozloží až v jeho druhé části. Plyne ze stavu Foldable, sedí tedy i po načtení a u klientů.
function SprayDroneStation.getTrailerUnfold(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return math.clamp(1 - self:getFoldAnimTime() / spec.trailerFoldEnd, 0, 1)
end

-- Mixér: <mixer> ve vozidle dává podíl koncentrátu v hotovém přípravku podle druhu koncentrátu a číslo nádrže koncentrátu.
function SprayDroneStation.loadMixer(self, xml, mixerKey)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.concentrateFillUnitIndex = xml:getValue(mixerKey .. "#concentrateFillUnitIndex", 3)
    spec.mixerRatios, spec.mixerProducts, spec.mixerTypes = {}, {}, {}
    xml:iterate(mixerKey .. ".ratio", function(_, ratioKey)
        local name = xml:getValue(ratioKey .. "#fillType")
        local fillType = name ~= nil and g_fillTypeManager:getFillTypeIndexByName(name) or nil
        local productName = xml:getValue(ratioKey .. "#product")
        local product = productName ~= nil and g_fillTypeManager:getFillTypeIndexByName(productName) or fillType
        if fillType ~= nil and product ~= nil and spec.mixerRatios[fillType] == nil then
            spec.mixerRatios[fillType] = SprayDroneMixer.clampRatio(xml:getValue(ratioKey .. "#concentrate", SprayDroneStation.DEFAULT_MIX_RATIO))
            spec.mixerProducts[fillType] = product
            table.insert(spec.mixerTypes, fillType)
        end
    end)
    if #spec.mixerTypes == 0 then
        local ratio = SprayDroneStation.DEFAULT_MIX_RATIO
        for concentrate, product in pairs({ SDT_CONCENTRATE_FERTILIZER = "LIQUIDFERTILIZER", SDT_CONCENTRATE_HERBICIDE = "HERBICIDE" }) do
            local concentrateType, productType = FillType[concentrate], FillType[product]
            if concentrateType ~= nil and productType ~= nil then
                spec.mixerRatios[concentrateType] = ratio
                spec.mixerProducts[concentrateType] = productType
                table.insert(spec.mixerTypes, concentrateType)
            end
        end
        table.sort(spec.mixerTypes)
    end
    spec.isMixing = false
end

-- Číslo nádrže koncentrátu, nebo nil, když ji vozidlo nemá.
function SprayDroneStation.getConcentrateUnit(self)
    local index = self[SprayDroneStation.SPEC_NAME].concentrateFillUnitIndex
    if index ~= nil and self:getFillUnitExists(index) then
        return index
    end
    return nil
end

-- Odkud dron dostane přípravek (SprayDroneMixer.resolve): hotový přípravek v hlavní nádrži (direct), nebo voda v hlavní
-- nádrži + koncentrát v koncentrátové (mix, přípravek se míchá při plnění dronu). fillType je vždy druh přípravku pro dron
-- (vanilla herbicide / liquidFertilizer, nikdy koncentrát) a je vyplněný (u none odhad podle koncentrátu, jinak první druh
-- z <mixer>), liters je dostupný přípravek, water / concentrate zásoby obou nádrží, concentrateType druh koncentrátu v nádrži.
function SprayDroneStation.getFillSource(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local mainType = self:getFillUnitFillType(spec.fillUnitIndex)
    local mainLevel = self:getFillUnitFillLevel(spec.fillUnitIndex)
    local concIndex = SprayDroneStation.getConcentrateUnit(self)
    local concType, concLevel = nil, 0
    if concIndex ~= nil then
        concType = self:getFillUnitFillType(concIndex)
        concLevel = self:getFillUnitFillLevel(concIndex)
    end
    local source = SprayDroneMixer.resolve(mainType, mainLevel, concType, concLevel, spec.mixerRatios, FillType.WATER, spec.mixerProducts)
    source.water = mainType == FillType.WATER and mainLevel or 0
    source.concentrate = concLevel
    source.concentrateType = concLevel > SprayDroneMixer.EPSILON and concType or nil
    if source.fillType == nil then
        source.fillType = spec.mixerProducts[spec.mixerTypes[1]]
        for _, concentrateType in ipairs(spec.mixerTypes) do
            local product = spec.mixerProducts[concentrateType]
            if self:getFillUnitSupportsFillType(spec.fillUnitIndex, product) then
                source.fillType = product
                break
            end
        end
    end
    if source.fillType == nil then
        source.fillType = self:getFillUnitFirstSupportedFillType(spec.fillUnitIndex)
    end
    return source
end

function SprayDroneStation.getSprayType(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local fillType = spec.droneFillType
    if spec.droneFillLevel <= 0 or fillType == FillType.UNKNOWN then
        fillType = SprayDroneStation.getFillSource(self).fillType
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

-- l/m pro plán (dávky, náplň, souhrn): u herbicidu plná dávka krát průměrný podíl plevele na poli (getFieldWeedFactor),
-- za letu se odečítá podle plevele pod každým pruhem (flushSpray).
function SprayDroneStation.getPlanLitersPerMeter(self, sprayType)
    local lpm = SprayDroneStation.getLitersPerMeter(self, sprayType)
    if sprayType ~= nil and sprayType.isHerbicide then
        lpm = lpm * SprayDroneStation.getFieldWeedFactor(self)
    end
    return lpm
end

---------------------------------------------------------------------------------------------------
-- plevel a Precision Farming

-- poloměr „bez ořezu“ pro buildAllLegs(unlimited): větší než jakákoli mapa
SprayDroneStation.UNLIMITED_RANGE = 1e6
SprayDroneStation.WEED_CACHE_TIME = 120000
SprayDroneStation.WEED_CELL_SIZE = 10
SprayDroneStation.WEED_MAX_CELLS = 1500
SprayDroneStation.PF_MOD_NAME = "FS25_precisionFarming"

-- Modifikátor a filtr plevele ve stavech WEED_FIRST_STATE..WEED_LAST_STATE (vzor ExtendedWeedControl:getWeedModifier);
-- nil na mapě bez plevele.
function SprayDroneStation.getWeedProbe()
    local mission = g_currentMission
    local weedSystem = mission ~= nil and mission.weedSystem or nil
    if weedSystem == nil or not weedSystem:getMapHasWeed() then
        return nil
    end
    local probe = SprayDroneStation.weedProbe
    if probe == nil or probe.mission ~= mission then
        local mapId, firstChannel, numChannels = weedSystem:getDensityMapData()
        if mapId == nil then
            return nil
        end
        probe = { mission = mission }
        probe.modifier = DensityMapModifier.new(mapId, firstChannel, numChannels, g_terrainNode)
        probe.filter = DensityMapFilter.new(mapId, firstChannel, numChannels)
        probe.filter:setValueCompareParams(DensityValueCompareType.BETWEEN, SprayDroneRoute.WEED_FIRST_STATE, SprayDroneRoute.WEED_LAST_STATE)
        probe.mapId, probe.firstChannel, probe.numChannels = mapId, firstChannel, numChannels
        SprayDroneStation.weedProbe = probe
    end
    return probe
end

-- Pixely plevele (stavy 1-6) a všechny pixely v rovnoběžníku; nil bez mapy plevele.
function SprayDroneStation.getWeedPixels(sx, sz, wx, wz, hx, hz)
    local probe = SprayDroneStation.getWeedProbe()
    if probe == nil then
        return nil, nil
    end
    probe.modifier:setParallelogramWorldCoords(sx, sz, wx, wz, hx, hz, DensityCoordType.POINT_POINT_POINT)
    local _, weed, total = probe.modifier:executeGet(probe.filter)
    return weed, total
end

-- Průměrný násobek spotřeby herbicidu na vybraném poli (mřížka buněk WEED_CELL_SIZE uvnitř polygonu). Počítá se jednou a
-- drží: za mise vůbec (postřik plevel mění), jinak WEED_CACHE_TIME nebo do změny pole.
function SprayDroneStation.getFieldWeedFactor(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local cache = spec.weedShareCache
    local missionActive = SprayDroneStation.getAnyMissionActive(self)
    if cache ~= nil and cache.fieldId == spec.fieldId and (missionActive or g_time - cache.time < SprayDroneStation.WEED_CACHE_TIME) then
        return cache.factor
    end
    local factor = 1
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field ~= nil and SprayDroneStation.getWeedProbe() ~= nil then
        local poly = SprayDroneRoute.getPolygon(field)
        local minX, maxX, minZ, maxZ = math.huge, -math.huge, math.huge, -math.huge
        for _, p in ipairs(poly) do
            minX, maxX, minZ, maxZ = math.min(minX, p.x), math.max(maxX, p.x), math.min(minZ, p.z), math.max(maxZ, p.z)
        end
        local size = math.max(SprayDroneStation.WEED_CELL_SIZE,
            math.sqrt((maxX - minX) * (maxZ - minZ) / SprayDroneStation.WEED_MAX_CELLS))
        local cells = {}
        for x = minX + size * 0.5, maxX, size do
            for z = minZ + size * 0.5, maxZ, size do
                if SprayDroneRoute.isPointInPolygon(poly, x, z) then
                    local h = size * 0.5
                    local weed, total = SprayDroneStation.getWeedPixels(x - h, z - h, x + h, z - h, x - h, z + h)
                    table.insert(cells, { weed = weed, total = total })
                end
            end
        end
        factor = SprayDroneRoute.getAverageHerbicideFactor(cells)
    end
    spec.weedShareCache = { fieldId = spec.fieldId, time = g_time, factor = factor }
    return factor
end

-- Instance Precision Farming (g_precisionFarming), nil bez modu. PF je interní mod: proměnná žije v jeho prostředí
-- (_G.FS25_precisionFarming), u některých verzí i globálně.
function SprayDroneStation.getPrecisionFarming()
    local pf = rawget(_G, "g_precisionFarming")
    if type(pf) ~= "table" then
        local env = rawget(_G, SprayDroneStation.PF_MOD_NAME)
        pf = type(env) == "table" and env.g_precisionFarming or nil
    end
    if type(pf) ~= "table" or (pf.nitrogenMap == nil and pf.pHMap == nil) then
        return nil
    end
    return pf
end

-- Třída nebo konstanta PF (NitrogenMap, PHMap, ExtendedWeedControl): globálně, jinak z prostředí modu.
function SprayDroneStation.getPFGlobal(name)
    local value = rawget(_G, name)
    if value == nil then
        local env = rawget(_G, SprayDroneStation.PF_MOD_NAME)
        if type(env) == "table" then
            value = env[name]
        end
    end
    return value
end

-- Instance ExtendedWeedControl uvnitř PF (drží lastUseSpotSpraying): podle jména, jinak podle metod.
function SprayDroneStation.getPFWeedControl(pf)
    if pf == nil then
        return nil
    end
    if pf.sdtWeedControl ~= nil then
        return pf.sdtWeedControl
    end
    local found = pf.extendedWeedControl or pf.weedControl
    if type(found) ~= "table" or type(found.getWeedModifier) ~= "function" then
        found = nil
        for _, v in pairs(pf) do
            if type(v) == "table" and type(v.getWeedModifier) == "function" and type(v.clearWeedArea) == "function" then
                found = v
                break
            end
        end
    end
    pf.sdtWeedControl = found
    return found
end

-- Bitová mapa hodnot PF (ValueMap: dusík, pH) a její kanály. NEOVĚŘENO: zdroje ValueMap/NitrogenMap/PHMap nejsou
-- k dispozici; jméno pole s mapou a kanály jsou odhad podle FS22 (bitVectorMap, firstChannel, numChannels).
function SprayDroneStation.getPFMapLayer(map, className)
    if type(map) ~= "table" then
        return nil
    end
    local mapId = map.bitVectorMap
    if mapId == nil and type(map.getBitVectorMap) == "function" then
        mapId = map:getBitVectorMap()
    end
    if mapId == nil or mapId == 0 then
        return nil
    end
    local class = SprayDroneStation.getPFGlobal(className)
    local numChannels = map.numChannels or (type(class) == "table" and class.NUM_BITS) or nil
    if numChannels == nil then
        return nil
    end
    return mapId, map.firstChannel or 0, numChannels
end

-- Zvedne hodnotu mapy PF v rovnoběžníku o change stavů, nejvýš na maxValue. includeZero: i pixely s hodnotou 0
-- (u PF zřejmě „neinicializováno“ – bez úspěšného preUpdate se nechají být).
function SprayDroneStation.addPFLevel(mapId, firstChannel, numChannels, maxValue, change, includeZero, sx, sz, wx, wz, hx, hz)
    local modifier = DensityMapModifier.new(mapId, firstChannel, numChannels, g_terrainNode)
    modifier:setParallelogramWorldCoords(sx, sz, wx, wz, hx, hz, DensityCoordType.POINT_POINT_POINT)
    local filter = DensityMapFilter.new(mapId, firstChannel, numChannels)
    local low = includeZero and 0 or 1
    local saturateFrom = math.max(maxValue - change + 1, low)
    if saturateFrom <= maxValue then
        filter:setValueCompareParams(DensityValueCompareType.BETWEEN, saturateFrom, maxValue)
        modifier:executeSet(maxValue, filter)
    end
    if maxValue - change >= low then
        filter:setValueCompareParams(DensityValueCompareType.BETWEEN, low, maxValue - change)
        modifier:executeAdd(change, filter)
    end
end

-- Kolik stavů mapy PF odpovídá pevné dávce dronu (l/ha); pamatuje se pro druh a dávku (spec.pfDose).
function SprayDroneStation.getPFStateChange(self, map, isLime, fillType, litersPerHa)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local dose = spec.pfDose
    if dose ~= nil and dose.fillType == fillType and dose.isLime == isLime and math.abs(dose.litersPerHa - litersPerHa) < 0.01 then
        return dose.change, dose.maxValue
    end
    if type(map.getMinMaxValue) ~= "function" or type(map.getLimeUsageByStateChange) ~= "function"
        or type(map.getFertilizerUsageByStateChange) ~= "function" then
        return 0, nil
    end
    local _, _, maxStates = map:getMinMaxValue()
    local maxChange = math.max((tonumber(maxStates) or 16) - 1, 1)
    local usageAt
    if isLime then
        usageAt = function(n) return map:getLimeUsageByStateChange(n) end
    else
        usageAt = function(n) return map:getFertilizerUsageByStateChange(n, fillType) end
    end
    local change = SprayDroneRoute.pickStateChange(litersPerHa, usageAt, maxChange)
    dose = { fillType = fillType, isLime = isLime, litersPerHa = litersPerHa, change = change, maxValue = tonumber(maxStates) }
    spec.pfDose = dose
    return change, dose.maxValue
end

SprayDroneStation.pfLogged = {}

local function logPFOnce(key, text, ...)
    if not SprayDroneStation.pfLogged[key] then
        SprayDroneStation.pfLogged[key] = true
        Logging.warning("SDT PF: " .. text, ...)
    end
end

-- Precision Farming u hnojiva a vápna: jako ExtendedSprayer:processSprayerArea zapíše do mapy dusíku / pH (pevná dávka
-- dronu, ne variabilní). Bez PF nic. API map PF je v dostupných zdrojích jen zčásti: co chybí, se přeskočí (getPFMapLayer).
function SprayDroneStation.applyPrecisionFarming(self, pf, sprayType, fillType, litersPerHa, sx, sz, wx, wz, hx, hz)
    local isLime = sprayType.isLime == true or fillType == FillType.LIME
    local map, className, preName
    if isLime then
        map, className, preName = pf.pHMap, "PHMap", "preUpdatePHLevelAtArea"
    elseif sprayType.isFertilizer and pf.nitrogenMap ~= nil then
        local nitrogen = pf.nitrogenMap
        if type(nitrogen.getFillTypeIsFertilizer) == "function" and nitrogen:getFillTypeIsFertilizer(fillType) then
            map, className, preName = pf.nitrogenMap, "NitrogenMap", "preUpdateNitrogenLevelAtArea"
        end
    end
    if map == nil then
        return
    end
    do
        local change, maxStates = SprayDroneStation.getPFStateChange(self, map, isLime, fillType, litersPerHa)
        if change <= 0 then
            return
        end
        local mapId, firstChannel, numChannels = SprayDroneStation.getPFMapLayer(map, className)
        if mapId == nil then
            logPFOnce("noLayer" .. className, "%s: nenalezena bitová mapa (bitVectorMap / NUM_BITS), zápis vynechán", className)
            return
        end
        -- inicializace nedotčených pixelů jako u stroje (preUpdate s rovnoběžníkem); bez ní se nulové pixely nezvedají
        local initialized = false
        local Parallelogram = SprayDroneStation.getPFGlobal("DensityMapParallelogram")
        if Parallelogram ~= nil and type(map[preName]) == "function" then
            SprayDroneStation.pfParallelogram = SprayDroneStation.pfParallelogram or Parallelogram.new()
            SprayDroneStation.pfParallelogram:updateFromWorldPositions(sx, sz, wx, wz, hx, hz)
            map[preName](map, SprayDroneStation.pfParallelogram, sprayType.index)
            initialized = true
        end
        local maxValue = 2 ^ numChannels - 1
        if maxStates ~= nil and maxStates > 0 and maxStates < maxValue then
            maxValue = maxStates
        end
        SprayDroneStation.addPFLevel(mapId, firstChannel, numChannels, maxValue, change, initialized, sx, sz, wx, wz, hx, hz)
        if sprayType.sprayGroundType ~= nil then
            FSDensityMapUtil.setGroundTypeLayerArea(sx, sz, wx, wz, hx, hz, sprayType.sprayGroundType)
        end
        if type(map.setMinimapRequiresUpdate) == "function" then
            map:setMinimapRequiresUpdate(true)
        end
    end
end

-- Herbicid s PF: ExtendedWeedControl rozhoduje o preventivním postřiku (neviditelné fáze 1-2) podle lastUseSpotSpraying
-- posledního stroje; dron stříká plošně, takže pro svůj zápis ho nastaví na false a pak vrátí.
function SprayDroneStation.updateSprayAreaPreventive(pf, sx, sz, wx, wz, hx, hz, sprayTypeIndex)
    local control = SprayDroneStation.getPFWeedControl(pf)
    if control == nil then
        return FSDensityMapUtil.updateSprayArea(sx, sz, wx, wz, hx, hz, sprayTypeIndex, 1)
    end
    local saved = control.lastUseSpotSpraying
    control.lastUseSpotSpraying = false
    local changedArea, totalArea = FSDensityMapUtil.updateSprayArea(sx, sz, wx, wz, hx, hz, sprayTypeIndex, 1)
    control.lastUseSpotSpraying = saved
    return changedArea, totalArea
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
        transitHeight = spec.transitHeight + spec.layerOffset,
        cruiseSpeed = spec.cruiseSpeed,
        sprayingSpeed = spec.sprayingSpeed,
        climbSpeed = spec.climbSpeed,
        ascentSpeed = spec.ascentSpeed,
        acceleration = spec.acceleration,
        yawSpeed = spec.yawSpeed,
        litersPerMeter = SprayDroneStation.getPlanLitersPerMeter(self, sprayType),
        batteryReserve = spec.batteryReserve,
        restHeight = restHeight,
        homeYaw = SprayDroneStation.getHomeYaw(self),
        turnAcceleration = spec.turnAcceleration,
        droneRadius = spec.droneRadius,
        sideClearance = spec.sideClearance,
        obstacleClearance = spec.obstacleClearance + spec.layerOffset,
        maxTransitHeight = spec.maxTransitHeight + spec.layerOffset,
        getTransit = function(x, z, outbound, dirX, dirZ)
            return SprayDroneStation.getTransit(self, x, z, outbound, dirX, dirZ)
        end,
        getHomePath = SprayDroneStation.getCorridor(self) ~= nil and function(x, z)
            return SprayDroneStation.getHomePath(self, x, z)
        end or nil,
        isTurnClear = function(points)
            return SprayDroneStation.getIsTurnClear(self, points)
        end,
        getHopHeight = function(ax, az, bx, bz)
            return SprayDroneStation.getHopHeight(self, ax, az, bx, bz)
        end
    }
end

-- Výška nad terénem, ve které dron přeletí překážky (remízek, stavba) na přímce a -> b uprostřed pole; nil = nic tam není nebo
-- se nedá přeletět (pak zasáhne pojistka za letu). Výsledek se pamatuje, plán se za letu přepočítává každé 2,5 s.
function SprayDroneStation.getHopHeight(self, ax, az, bx, bz)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local key = string.format("%d:%d:%d:%d", ax, az, bx, bz)
    spec.hopCache = spec.hopCache or {}
    local cached = spec.hopCache[key]
    if cached ~= nil then
        return cached or nil
    end
    local len = MathUtil.vector2Length(bx - ax, bz - az)
    local dirX, dirZ = (bx - ax) / len, (bz - az) / len
    local halfWidth = spec.droneRadius + spec.sideClearance
    local best = 0
    local steps = math.max(math.ceil(len / SprayDroneRoute.OBSTACLE_STEP), 1)
    for i = 0, steps do
        local t = i / steps
        best = math.max(best, (SprayDroneRoute.getBandObstacle(ax + (bx - ax) * t, az + (bz - az) * t, dirX, dirZ, halfWidth)))
    end
    local hop = nil
    if best > 0 then
        hop = best + spec.obstacleClearance + spec.layerOffset
        if hop > spec.maxTransitHeight + spec.layerOffset then
            hop = nil
        end
    end
    local size = 0
    for _ in pairs(spec.hopCache) do
        size = size + 1
    end
    if size > 200 then
        spec.hopCache = {}
    end
    spec.hopCache[key] = hop or false
    return hop
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
    local hx, hz = SprayDroneStation.getHomePosition(self)
    if SprayDroneRoute.distanceToPolygon(SprayDroneRoute.getPolygon(field), hx, hz) > SprayDroneStation.updateRange(self) then
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
    local source = SprayDroneStation.getFillSource(self)
    local mainLiters = self:getFillUnitFillLevel(spec.fillUnitIndex)
    -- přípravek, který vlek dodá: hotový v hlavní nádrži, nebo kolik jde namíchat (zásoba vody a koncentrátu)
    local trailerLiters = source.fillType == fillType and source.liters or 0
    local droneLiters = spec.droneFillType == fillType and spec.droneFillLevel or 0
    local concentrateUnit = SprayDroneStation.getConcentrateUnit(self)
    local mainFillType = self:getFillUnitFillType(spec.fillUnitIndex)
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
        liters = length * SprayDroneStation.getPlanLitersPerMeter(self, sprayType),
        availableLiters = trailerLiters + droneLiters,
        trailerLiters = trailerLiters,
        droneLiters = droneLiters,
        fillTypeTitle = g_fillTypeManager:getFillTypeTitleByIndex(fillType) or "-",
        mainLiters = mainLiters,
        mainCapacity = self:getFillUnitCapacity(spec.fillUnitIndex),
        mainTitle = mainLiters > SprayDroneMixer.EPSILON and g_fillTypeManager:getFillTypeTitleByIndex(mainFillType) or nil,
        hasConcentrateTank = concentrateUnit ~= nil,
        concentrateLiters = source.concentrate,
        concentrateCapacity = concentrateUnit ~= nil and self:getFillUnitCapacity(concentrateUnit) or 0,
        concentrateTitle = source.concentrateType ~= nil and g_fillTypeManager:getFillTypeTitleByIndex(source.concentrateType) or nil,
        sourceKind = source.kind,
        sourceReason = source.reason,
        mixRatio = source.ratio,
        mixLimit = source.limit,
        mixWater = source.water
    }
end

-- Souhrn trasy všech dronů pro plánovač: dávky, plocha, litry, nafta a výměny baterií se sčítají, čas je nejdelší z dronů
-- (drony letí současně). Základ je souhrn dronu 1 (zásoby vleku, nastavení), ostatní hodnoty se z druhého dronu přičtou.
function SprayDroneStation.getRouteSummaryAll(self)
    local root = SprayDroneDrones.getRoot(self)
    local summary = SprayDroneDrones.runAs(self, 1, SprayDroneStation.getRouteSummary)
    if root.numDrones < 2 or root.activeDrones < 2 then
        return summary
    end
    local other = SprayDroneDrones.runAs(self, 2, SprayDroneStation.getRouteSummary)
    summary.numBatches = summary.numBatches + other.numBatches
    summary.areaHa = summary.areaHa + other.areaHa
    summary.liters = summary.liters + other.liters
    summary.dieselUsed = summary.dieselUsed + other.dieselUsed
    summary.batterySwaps = summary.batterySwaps + other.batterySwaps
    summary.transitLength = summary.transitLength + other.transitLength
    summary.droneLiters = summary.droneLiters + other.droneLiters
    summary.availableLiters = summary.trailerLiters + summary.droneLiters
    summary.minutes = math.max(summary.minutes, other.minutes)
    summary.serviceMinutes = math.max(summary.serviceMinutes, other.serviceMinutes)
    summary.waitMinutes = math.max(summary.waitMinutes, other.waitMinutes)
    summary.batteryPercent = math.max(summary.batteryPercent, other.batteryPercent)
    summary.noFuel = summary.noFuel or other.noFuel
    summary.fuelRunsOut = summary.fuelRunsOut or other.fuelRunsOut
    summary.clipped = summary.clipped or other.clipped
    summary.tooHigh = summary.tooHigh or other.tooHigh
    summary.noPath = summary.noPath or other.noPath
    return summary
end

-- Řádky stavu dronů pro plánovač: { { stav, nádrž a baterie }, ... }.
function SprayDroneStation.getDroneStateTexts(self)
    local list = {}
    SprayDroneDrones.forEachSpec(self, function()
        local state, tank = SprayDroneStation.getDroneStateText(self)
        table.insert(list, { state, tank })
    end)
    return list
end

-- Stav a parametry servisu pro odhad plánovače (SprayDroneRoute.splitIntoBatches).
function SprayDroneStation.getPowerParams(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local _, fillType = SprayDroneStation.getSprayType(self)
    local charges = {}
    for _, battery in ipairs(spec.batteries) do
        if battery.slot > 0 then
            table.insert(charges, battery.charge)
        end
    end
    -- náhradní baterie a nafta se dělí mezi drony v misi: nejnabitější střídavě (1., 3., ... prvnímu, 2., 4., ... druhému)
    local drones = math.max(spec.activeDrones, 1)
    local spares = charges
    if drones > 1 then
        table.sort(charges, function(a, b)
            return a > b
        end)
        spares = {}
        for i = SprayDroneDrones.getIndex(self), #charges, drones do
            table.insert(spares, charges[i])
        end
    end
    return {
        spares = spares,
        droneHasBattery = spec.droneBattery ~= nil,
        diesel = self:getFillUnitFillLevel(spec.dieselFillUnitIndex) / drones,
        startFill = spec.droneFillType == fillType and spec.droneFillLevel or 0,
        capacity = spec.batteryCapacity,
        chargeRate = spec.chargeRate,
        dieselPerSecond = spec.dieselPerSecond,
        readyCharge = spec.readyCharge,
        swapTime = spec.swapTime * 0.001,
        pumpRate = spec.pumpRate,
        minService = SprayDroneStation.SERVICE_TIME * 0.001,
        pumpShare = SprayDroneStation.PUMP_POWER_SHARE,
        pumpLoad = SprayDroneStation.PUMP_DIESEL_LOAD
    }
end

-- Legy zbývající práce celého pole od domova dronu 1 (jednotný seznam, ze kterého se dělí práce mezi drony). reserved = úseky,
-- které právě stříká druhý dron (SprayDroneRoute.reserved), se z legů vynechají. unlimited = bez ořezu dosahem a signálem
-- (jen zjistit, jestli na poli ještě něco zbývá). Volat v kontextu dronu 1 (runAs(self, 1, ...)).
function SprayDroneStation.buildAllLegs(self, reserved, unlimited)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    local sprayType = SprayDroneStation.getSprayType(self)
    if field == nil or sprayType == nil then
        return {}, sprayType
    end
    local hx, hz = SprayDroneStation.getHomePosition(self)
    local coverage = SprayDroneRoute.getCoverage(spec.coverage, spec.fieldId, sprayType.index, spec.workWidth, spec.headlands)
    local range = unlimited and SprayDroneStation.UNLIMITED_RANGE or SprayDroneStation.updateRange(self)
    SprayDroneRoute.reserved = reserved
    SprayDroneRoute.reservedMargin = spec.workWidth * 0.5 + SprayDroneStation.RESERVE_MARGIN
    -- s relé je kruh dosahu (rádio + vzdálenost tyče) větší než skutečný signál: stříká se jen tam, kam signál dosáhne
    local circles = not unlimited and SprayDroneLink ~= nil and SprayDroneLink.getSignalCircles(self) or nil
    SprayDroneRoute.signalCircles = circles ~= nil and #circles > 1 and circles or nil
    local legs = SprayDroneRoute.buildLegs(field, hx, hz, range, spec.workWidth, sprayType, coverage, spec.headlands,
        spec.headlandFirst)
    SprayDroneRoute.reserved = nil
    SprayDroneRoute.signalCircles = nil
    return legs, sprayType
end

-- Úseky, které druhý dron (než k) právě stříká (zbytek jeho dávky): prvnímu se nesmí nabídnout znovu. Jen server, za letu.
function SprayDroneStation.getReservedSegments(self, k)
    local root = SprayDroneDrones.getRoot(self)
    local segments = {}
    for j = 1, root.numDrones do
        local d = root.drones[j]
        if j ~= k and d.state == SprayDroneStation.STATE_FLYING and d.path ~= nil then
            if d.sprayFrom ~= nil then
                table.insert(segments, { d.sprayFrom.x, d.sprayFrom.z, d.pos.x, d.pos.z })
            end
            for i = d.wpIndex, #d.path do
                local wp = d.path[i]
                if wp.spray and wp.sx ~= nil then
                    table.insert(segments, { wp.sx, wp.sz, wp.x, wp.z })
                end
            end
        end
    end
    return #segments > 0 and segments or nil
end

-- Kolik dronů si dělí práci: v náhledu ty v misi podle nastavení, za letu ty s aktivní misí.
function SprayDroneStation.getWorkingDrones(self, preview)
    local root = SprayDroneDrones.getRoot(self)
    if preview then
        return root.activeDrones
    end
    local n = 0
    for k = 1, root.numDrones do
        if root.drones[k].missionActive then
            n = n + 1
        end
    end
    return math.max(n, 1)
end

-- Legy tohoto dronu (v kontextu dronu): zbývající práce pole rozdělená mezi drony v misi (SprayDroneRoute.splitLegs), dron 2 bere
-- od vzdáleného konce pole. preview = náhled v plánovači (bez rezervací, podle nastavení activeDrones). Vrací legy a druh postřiku.
function SprayDroneStation.buildLegs(self, preview)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local root = SprayDroneDrones.getRoot(self)
    local index = SprayDroneDrones.getIndex(self)
    if preview and index > root.activeDrones then
        return {}, nil
    end
    local reserved = nil
    if not preview and root.numDrones > 1 then
        reserved = SprayDroneStation.getReservedSegments(self, index)
    end
    local all, sprayType = SprayDroneDrones.runAs(self, 1, SprayDroneStation.buildAllLegs, reserved)
    local n = root.numDrones > 1 and SprayDroneStation.getWorkingDrones(self, preview) or 1
    if n < 2 or #all == 0 then
        return all, sprayType
    end
    local h1x, h1z = SprayDroneDrones.runAs(self, 1, SprayDroneStation.getHomePosition)
    local h2x, h2z = SprayDroneDrones.runAs(self, 2, SprayDroneStation.getHomePosition)
    local litersPerMeter = SprayDroneStation.getPlanLitersPerMeter(self, sprayType)
    local split = SprayDroneRoute.splitLegs(all, n, {
        homes = { { x = h1x, z = h1z }, { x = h2x, z = h2z } },
        batchLength = math.min(spec.tankCapacity / litersPerMeter,
            SprayDroneStation.SPLIT_BATTERY_SHARE * spec.batteryCapacity * spec.sprayingSpeed),
        spraySpeed = spec.sprayingSpeed,
        cruiseSpeed = spec.cruiseSpeed,
        serviceTime = SprayDroneStation.SERVICE_TIME * 0.001 + spec.tankCapacity / spec.pumpRate,
        minSplit = SprayDroneStation.SPLIT_MIN_LENGTH,
        requester = preview and 1 or index
    })
    local mine = split[index]
    if #mine == 0 and not preview then
        mine = all
    end
    return mine, sprayType
end

-- Paměť dronu, kde už postříkal, se změnila: klienti ji dostanou v update streamu (za letu nejvýš jednou za sekundu).
function SprayDroneStation.raiseCoverage(self, force)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if force or g_time - spec.coverageSyncTime >= 1000 then
        spec.coverageSyncTime = g_time
        self:raiseDirtyFlags(spec.coverageDirtyFlag)
    end
end

function SprayDroneStation.clearCoverage(self, fieldId)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.coverage[fieldId] = nil
    spec.weedShareCache = nil
    SprayDroneStation.markRouteDirty(self)
    SprayDroneStation.raiseCoverage(self, true)
end

function SprayDroneStation.updateRoutePreview(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.routeDirty = false
    -- druhý dron se přepočítává posunutě, ať oba nepočítají v témž snímku
    spec.routeTimer = SprayDroneStation.ROUTE_REFRESH_TIME * (1 + (SprayDroneDrones.getIndex(self) - 1) * 0.5)
    spec.drawLegs, spec.numBatches, spec.routeClipped = {}, 0, false
    spec.routeInfo = { time = 0, height = spec.transitHeight, tooHigh = false, transits = {} }
    if spec.fieldId == 0 then
        return
    end
    local legs, sprayType = SprayDroneStation.buildLegs(self, true)
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

-- value: číslo pole u SELECT_FIELD, u SET_GENERATOR 1 = zapnout / 0 = vypnout, jinak se nepoužije.
-- droneIndex: START a RETURN_HOME pro jednoho dronu (1 / 2), nebo pro všechny (0 / nil: START jen pro prvních activeDrones).
function SprayDroneStation:sprayDroneCommand(command, value, noEventSend, droneIndex)
    if SprayDroneCommandEvent.sendEvent(self, command, value, noEventSend, droneIndex) then
        return
    end
    local spec = SprayDroneDrones.getRoot(self)
    -- spící vlek se probudí: nabíjení po zapnutí centrály a mise se řídí z onUpdate
    self:raiseActive()

    if not spec.hasDrone and command ~= SprayDroneCommandEvent.SET_GENERATOR then
        return
    end
    if command == SprayDroneCommandEvent.SELECT_FIELD then
        if SprayDroneStation.getAnyMissionActive(self) or not self:getSprayDroneIsParked() then
            return
        end
        local field = SprayDroneRoute.getFieldById(value)
        if field ~= nil and SprayDroneStation.getFieldAllowed(self, field) then
            spec.fieldId = value
            SprayDroneDrones.forEachSpec(self, function(d)
                d.status = SprayDroneStation.STATUS_NONE
            end)
            SprayDroneStation.markRouteDirty(self)
            self:raiseDirtyFlags(spec.dirtyFlag)
        end

    elseif command == SprayDroneCommandEvent.START then
        for k = 1, spec.numDrones do
            if (droneIndex == nil or droneIndex == 0) and k <= spec.activeDrones or droneIndex == k then
                SprayDroneDrones.runAs(self, k, SprayDroneStation.startDrone)
            end
        end

    elseif command == SprayDroneCommandEvent.RESET_FIELD then
        local field = SprayDroneRoute.getFieldById(spec.fieldId)
        if field == nil or SprayDroneStation.getAnyMissionActive(self) or not self:getSprayDroneIsParked()
            or not SprayDroneStation.getFieldAllowed(self, field) then
            return
        end
        SprayDroneStation.clearCoverage(self, spec.fieldId)
        SprayDroneDrones.forEachSpec(self, function(d)
            d.status = SprayDroneStation.STATUS_NONE
        end)
        self:raiseDirtyFlags(spec.dirtyFlag)

    elseif command == SprayDroneCommandEvent.SET_GENERATOR then
        spec.generatorEnabled = value ~= 0
        self:raiseDirtyFlags(spec.dirtyFlag)

    elseif command == SprayDroneCommandEvent.RETURN_HOME then
        for k = 1, spec.numDrones do
            if droneIndex == nil or droneIndex == 0 or droneIndex == k then
                SprayDroneDrones.runAs(self, k, SprayDroneStation.returnDrone)
            end
        end
    end
end

-- Start mise jednoho dronu (v kontextu dronu).
function SprayDroneStation.startDrone(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if not spec.hasDrone or spec.fieldId == 0 or spec.missionActive or not self:getIsUnfolded() or #spec.batteries == 0 then
        return
    end
    spec.missionActive = true
    spec.status = SprayDroneStation.STATUS_NONE
    if spec.transferMode == SprayDroneStation.TRANSFER_DRAIN_DRONE and spec.transferDrone == SprayDroneDrones.getIndex(self) then
        spec.transferMode = SprayDroneStation.TRANSFER_NONE
    end
    if spec.state == SprayDroneStation.STATE_PARKED then
        SprayDroneStation.setState(self, SprayDroneStation.STATE_SERVICING)
        spec.serviceTimer = SprayDroneStation.START_DELAY
    end
    self:raiseDirtyFlags(spec.dirtyFlag)
end

-- Návrat jednoho dronu domů (v kontextu dronu).
function SprayDroneStation.returnDrone(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if not spec.hasDrone then
        return
    end
    spec.missionActive = false
    if spec.state == SprayDroneStation.STATE_FLYING then
        SprayDroneStation.startReturnHome(self)
    elseif spec.state == SprayDroneStation.STATE_SERVICING then
        SprayDroneStation.setState(self, SprayDroneStation.STATE_PARKED)
    end
    self:raiseDirtyFlags(spec.dirtyFlag)
end

-- Běží mise některého dronu?
function SprayDroneStation.getAnyMissionActive(self)
    return SprayDroneDrones.any(self, function(d)
        return d.missionActive
    end)
end

function SprayDroneStation.setState(self, state)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.state ~= state then
        spec.state = state
        if state ~= SprayDroneStation.STATE_SERVICING then
            spec.isPumping, spec.isSwapping, spec.waitingForCharge, spec.swapTimer = false, false, false, 0
            spec.isMixing, spec.waitingForPower, spec.waitingForRelay = false, false, false
        end
        if state ~= SprayDroneStation.STATE_FLYING and state ~= SprayDroneStation.STATE_RETURNING then
            spec.batchRelays = {}
        end
        spec.signalLostTime = 0
        spec.swapChecked, spec.swapPending = false, false
        spec.pumpCapChecked, spec.pumpTankTarget = false, nil
        spec.waitingForPad = false
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

-- Odebere z vleku `liters` l přípravku pro dron. direct: z hlavní nádrže; mix: na litr přípravku podíl koncentrátu z
-- nádrže koncentrátu a zbytek vody z hlavní nádrže (mixér). Vrací, kolik přípravku se opravdu odebralo.
function SprayDroneStation.takeFromTrailer(self, source, liters)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local farmId = self:getOwnerFarmId()
    if source.kind == SprayDroneMixer.KIND_DIRECT then
        return -self:addFillUnitFillLevel(farmId, spec.fillUnitIndex, -liters, source.fillType, ToolType.UNDEFINED, nil)
    end
    local water, concentrate = SprayDroneMixer.getParts(source.ratio, liters)
    local concIndex = SprayDroneStation.getConcentrateUnit(self)
    local takenWater = -self:addFillUnitFillLevel(farmId, spec.fillUnitIndex, -water, FillType.WATER, ToolType.UNDEFINED, nil)
    local takenConcentrate = -self:addFillUnitFillLevel(farmId, concIndex, -concentrate, source.concentrateType, ToolType.UNDEFINED, nil)
    return math.min(takenWater / (1 - source.ratio), takenConcentrate / source.ratio)
end

-- Kolik litrů přípravku ještě dron potřebuje na zbytek přidělené práce (všechny zbývající legy, ne jen příští dávku).
-- nil = nejde spočítat (bez pole/mise) -> nekrátit, plnit na plnou nádrž.
function SprayDroneStation.getNeededLiters(self)
    local legs, sprayType = SprayDroneStation.buildLegs(self)
    if #legs == 0 or sprayType == nil then
        return nil
    end
    local length = 0
    for _, leg in ipairs(legs) do
        length = length + leg.len
    end
    return length * SprayDroneStation.getPlanLitersPerMeter(self, sprayType)
end

-- Čerpadlo z vleku do dronu na plošině (pumpRate l/s); s vodou v hlavní nádrži míchá přípravek z koncentrátu (mixér).
-- Čerpadlo jede jen z centrály (SprayDroneStation.getHasPower). Vrací, jestli se ještě plní, jestli přitom míchá
-- (spec.isMixing, slyší ho i klienti), a jestli by plnilo, ale stojí bez proudu.
function SprayDroneStation.pumpDrone(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local source = SprayDroneStation.getFillSource(self)
    local filling, mixing, noPower = false, false, false
    if source.kind ~= SprayDroneMixer.KIND_NONE and source.liters > 0 then
        if spec.droneFillType ~= source.fillType and spec.droneFillLevel > 0 then
            -- jiný přípravek ve vleku: zbytek v dronu se nemíchá, zahodí se
            spec.droneFillLevel = 0
        end
        if not spec.pumpCapChecked then
            spec.pumpCapChecked = true
            spec.pumpTankTarget = spec.tankCapacity
            if spec.missionActive then
                local needed = SprayDroneStation.getNeededLiters(self)
                if needed ~= nil then
                    -- poslední dávka mise: natankovat jen co se ještě spotřebuje, ne celou nádrž
                    spec.pumpTankTarget = math.min(spec.tankCapacity, math.max(needed, spec.droneFillLevel))
                end
            end
        end
        -- čerpadlo je jedno: pumpují-li oba drony zároveň, průtok se dělí
        local share = 1
        local root = SprayDroneDrones.getRoot(self)
        for j = 1, root.numDrones do
            if root.drones[j] ~= spec and root.drones[j].isPumping then
                share = share + 1
            end
        end
        local amount = math.min(spec.pumpTankTarget - spec.droneFillLevel, source.liters, spec.pumpRate * dt * 0.001 / share)
        if amount > 0.0001 and not SprayDroneStation.getHasPower(self) then
            noPower = true
        elseif amount > 0.0001 then
            local applied = SprayDroneStation.takeFromTrailer(self, source, amount)
            spec.droneFillLevel = spec.droneFillLevel + applied
            spec.droneFillType = source.fillType
            filling = applied > 0 and spec.droneFillLevel < spec.pumpTankTarget - 0.001
            mixing = filling and source.kind == SprayDroneMixer.KIND_MIX
        end
    end
    if spec.droneFillLevel <= 0 then
        spec.droneFillType = FillType.UNKNOWN
    end
    return filling, mixing, noPower
end

-- Servis dronu na plošině (server): plnění a výměna baterie souběžně, pak další dávka, nebo zaparkovat.
function SprayDroneStation.updateService(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.serviceTimer = spec.serviceTimer - dt
    spec.swapTimer = math.max(spec.swapTimer - dt, 0)
    local pumping, mixing, noPower = SprayDroneStation.pumpDrone(self, dt)
    -- výměna baterie se rozhodne hned na začátku servisu, aby běžela souběžně s plněním
    if spec.missionActive and not spec.swapChecked then
        spec.swapChecked = true
        spec.swapPending = SprayDroneStation.getWantsSwap(self)
    end
    if spec.swapPending and spec.swapTimer <= 0 then
        SprayDroneStation.swapBattery(self)
    end
    local swapping = spec.swapTimer > 0
    if pumping ~= spec.isPumping or swapping ~= spec.isSwapping or mixing ~= spec.isMixing then
        spec.isPumping, spec.isSwapping, spec.isMixing = pumping, swapping, mixing
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
    SprayDroneStation.setWaitingForCharge(self, spec.missionActive and spec.swapPending and not pumping and spec.serviceTimer <= 0)
    -- čerpadlo bez proudu: dron v misi čeká na plošině, dokud se centrála nezapne / nedoplní nafta (HUD řekne proč)
    SprayDroneStation.setWaitingForPower(self, spec.missionActive and noPower)
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
        local blocker = SprayDroneStation.getChargeBlocker(self)
        if blocker ~= nil then
            SprayDroneStation.endMission(self, blocker)
        end
        return
    end
    if spec.waitingForPower then
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
    local source = SprayDroneStation.getFillSource(self)
    local droneFill = spec.droneFillType == source.fillType and spec.droneFillLevel or 0
    local fill = math.min(spec.tankCapacity, droneFill + source.liters)
    if fill < 0.5 then
        return false
    end
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local p = SprayDroneStation.getFlightParams(self, sprayType, restHeight)
    local _, spareCharge = SprayDroneStation.getBestSlottedBattery(self)
    local wps, _, _, _, _, battery = SprayDroneRoute.planBatchWithSwap(legs, 1, 0, hx, hz, fill, spec.battery, p,
        math.max(spareCharge, spec.readyCharge))
    return wps ~= nil and (battery ~= spec.battery or spec.droneBattery == nil)
end

-- Proč se čekající náhradní baterie nenabije (status, kterým se mise ukončí): bez nafty, nebo s vypnutou centrálou; jinak nil.
function SprayDroneStation.getChargeBlocker(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if self:getFillUnitFillLevel(spec.dieselFillUnitIndex) <= 0 then
        return SprayDroneStation.STATUS_NO_FUEL
    elseif not spec.generatorEnabled then
        return SprayDroneStation.STATUS_GENERATOR_OFF
    end
    return nil
end

function SprayDroneStation.setWaitingForCharge(self, waiting)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.waitingForCharge ~= waiting then
        spec.waitingForCharge = waiting
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

function SprayDroneStation.setWaitingForRelay(self, waiting)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.waitingForRelay ~= waiting then
        spec.waitingForRelay = waiting
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

-- Tyče, na kterých závisí dávka s waypointy wps (body mimo rádio vleku v kruhu tyče), se zbývající výdrží.
function SprayDroneStation.getBatchRelays(self, wps)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if SprayDroneLink == nil then
        return {}
    end
    local connected = SprayDroneLink.getConnectedRelays(self)
    if #connected == 0 then
        return {}
    end
    local hx, hz = SprayDroneStation.getHomePosition(self)
    return SprayDroneLink.getNeededRelays(wps, hx, hz, spec.maxRange, connected)
end

-- Tyče rozlétané dávky po síti (blokace tyče se ptá i u klienta): počet a id objektů, nejvýš MAX_BATCH_RELAYS.
function SprayDroneStation.writeBatchRelays(spec, streamId)
    local list = {}
    for _, relay in ipairs(spec.batchRelays or {}) do
        if not relay.isDeleted and #list < SprayDroneStation.MAX_BATCH_RELAYS then
            table.insert(list, relay)
        end
    end
    streamWriteUIntN(streamId, #list, 3)
    for _, relay in ipairs(list) do
        NetworkUtil.writeNodeObject(streamId, relay)
    end
end

function SprayDroneStation.readBatchRelays(spec, streamId)
    spec.batchRelays = {}
    for _ = 1, streamReadUIntN(streamId, 3) do
        local relay = NetworkUtil.readNodeObject(streamId)
        if relay ~= nil then
            table.insert(spec.batchRelays, relay)
        end
    end
end

function SprayDroneStation.setWaitingForPower(self, waiting)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.waitingForPower ~= waiting then
        spec.waitingForPower = waiting
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

---------------------------------------------------------------------------------------------------
-- baterie: sloty na vleku, v dronu, nabíjení (server rozhoduje, klient dostává stav ve writeState)

function SprayDroneStation.getBatteryInSlot(self, slot)
    local spec = self[SprayDroneStation.SPEC_NAME]
    for k, battery in ipairs(spec.batteries) do
        if battery.slot == slot then
            return k
        end
    end
    return nil
end

function SprayDroneStation.getFreeBatterySlot(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    for slot = 1, spec.numBatterySlots do
        if SprayDroneStation.getBatteryInSlot(self, slot) == nil then
            return slot
        end
    end
    return spec.numBatterySlots
end

-- Nejnabitější baterie ve slotech: index a nabití (s); nil, 0 když ve slotech žádná není.
function SprayDroneStation.getBestSlottedBattery(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local best, charge = nil, -1
    for k, battery in ipairs(spec.batteries) do
        if battery.slot > 0 and battery.charge > charge then
            best, charge = k, battery.charge
        end
    end
    return best, math.max(charge, 0)
end

function SprayDroneStation.syncDroneBatteryCharge(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.droneBattery ~= nil then
        spec.batteries[spec.droneBattery].charge = spec.battery
    end
end

-- Baterie z dronu do prvního volného slotu (nabíjí se tam).
function SprayDroneStation.unloadDroneBattery(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.droneBattery == nil then
        return
    end
    SprayDroneStation.syncDroneBatteryCharge(self)
    local battery = spec.batteries[spec.droneBattery]
    battery.slot = SprayDroneStation.getFreeBatterySlot(self)
    spec.droneBattery = nil
    spec.battery = 0
    spec.routeDirty = true
    self:raiseDirtyFlags(spec.dirtyFlag)
end

function SprayDroneStation.loadDroneBattery(self, k)
    local spec = self[SprayDroneStation.SPEC_NAME]
    SprayDroneStation.unloadDroneBattery(self)
    local battery = spec.batteries[k]
    battery.slot = 0
    battery.drone = SprayDroneDrones.getIndex(self)
    spec.droneBattery = k
    spec.battery = battery.charge
    spec.routeDirty = true
    self:raiseDirtyFlags(spec.dirtyFlag)
end

-- Výměna při servisu: vybitá baterie jde hned do slotu (nabíjí se), do dronu první plně nabitá (nejvyšší nabití
-- aspoň readyCharge), jakmile nějaká je; do té doby dron čeká (swapPending). S jedinou baterií se tak nabije ve slotu.
function SprayDroneStation.swapBattery(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    SprayDroneStation.unloadDroneBattery(self)
    local k, charge = SprayDroneStation.getBestSlottedBattery(self)
    if k ~= nil and charge >= spec.readyCharge - 0.01 then
        spec.swapPending = false
        SprayDroneStation.loadDroneBattery(self, k)
        spec.swapTimer = spec.swapTime
        spec.isSwapping = true
        self:raiseDirtyFlags(spec.dirtyFlag)
        return true
    end
    spec.swapPending = true
    return false
end

-- Mimo servis: se skládáním vleku jde baterie z dronu do slotu, na rozloženém vleku si ji zaparkovaný dron vezme
-- (nejnabitější, aspoň readyCharge; jinak zůstane bez baterie, dokud se nějaká nenabije).
function SprayDroneStation.updateBatteryPlacement(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if not spec.isLinked or not spec.hasDrone then
        return
    end
    if spec.droneBattery ~= nil and spec.unfold < 1 then
        SprayDroneStation.unloadDroneBattery(self)
    elseif spec.droneBattery == nil and spec.unfold >= 1 and spec.state == SprayDroneStation.STATE_PARKED and not spec.missionActive then
        local k, charge = SprayDroneStation.getBestSlottedBattery(self)
        if k ~= nil and charge >= spec.readyCharge - 0.01 then
            SprayDroneStation.loadDroneBattery(self, k)
        end
    end
end

-- Počet baterií v nabíječce (ve slotech), které nejsou plné.
function SprayDroneStation.getNumChargingBatteries(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local count = 0
    for _, battery in ipairs(spec.batteries) do
        if battery.slot > 0 and battery.charge < spec.batteryCapacity then
            count = count + 1
        end
    end
    return count
end

-- Rozdělení výkonu centrály (čistá funkce). s = {enabled (zapnutá), diesel (l), charging (nenabitých baterií v nabíječce),
-- pumping (čerpadlo / mixér chce běžet), relays (nenabitých relé tyčí v držácích)}. Vrací {powered (je proud: zapnutá a s naftou),
-- pumpAllowed, running (centrála běží: nabíjí, nebo pohání čerpadlo), chargeFactor (podíl nabíjecího výkonu pro baterie i tyče),
-- dieselLoad (násobek dieselPerSecond)}.
function SprayDroneStation.getPowerShares(s)
    local powered = s.enabled == true and (s.diesel or 0) > 0
    local pumping = powered and s.pumping == true
    local charging = powered and (s.charging or 0) or 0
    local relays = powered and (s.relays or 0) or 0
    local chargeFactor = pumping and SprayDroneStation.PUMP_POWER_SHARE or 1
    local running = charging > 0 or relays > 0 or pumping
    local load = (charging + relays * SprayDroneStation.RELAY_DIESEL_LOAD) * chargeFactor + (pumping and SprayDroneStation.PUMP_DIESEL_LOAD or 0)
    return { powered = powered, pumpAllowed = powered, running = running, chargeFactor = chargeFactor, dieselLoad = load }
end

-- Je proud pro čerpadlo a mixér (centrála zapnutá a má naftu)? Platí na serveru i u klienta (stav je synchronizovaný).
function SprayDroneStation.getHasPower(self)
    local spec = SprayDroneDrones.getRoot(self)
    return SprayDroneStation.getGeneratorAllowed(self) and self:getFillUnitFillLevel(spec.dieselFillUnitIndex) > 0
end

-- Centrála smí běžet jen zapnutá na rozloženém vleku; složená je pod plachtou / bednou.
function SprayDroneStation.getGeneratorAllowed(self)
    local spec = SprayDroneDrones.getRoot(self)
    return spec.generatorEnabled and (self.getIsUnfolded == nil or self:getIsUnfolded())
end

-- Proč čerpadlo stojí: klíč textu (vypnutá centrála / bez nafty).
function SprayDroneStation.getNoPowerTextKey(self)
    local spec = SprayDroneDrones.getRoot(self)
    if not spec.generatorEnabled then
        return "sdt_hud_noPowerOff"
    end
    return SprayDroneStation.getGeneratorAllowed(self) and "sdt_hud_noPowerFuel" or "sdt_hud_noPowerFolded"
end

-- Běží čerpadlo (plnění některého dronu, vypouštění dronu, přečerpání do IBC)?
function SprayDroneStation.getPumpRunning(self)
    local spec = SprayDroneDrones.getRoot(self)
    if spec.transferMode ~= nil and spec.transferMode ~= SprayDroneStation.TRANSFER_NONE then
        return true
    end
    return SprayDroneDrones.any(self, function(d)
        return d.isPumping == true
    end)
end

function SprayDroneStation.getPowerState(self)
    local spec = SprayDroneDrones.getRoot(self)
    return SprayDroneStation.getPowerShares({ enabled = SprayDroneStation.getGeneratorAllowed(self), diesel = self:getFillUnitFillLevel(spec.dieselFillUnitIndex),
        charging = SprayDroneStation.getNumChargingBatteries(self), pumping = SprayDroneStation.getPumpRunning(self),
        relays = SprayDroneRelaySlots.getNumCharging(self) or 0 })
end

-- Centrála běží, když je zapnutá, vlek rozložený, je nafta a některá baterie v nabíječce není plná, nebo jede čerpadlo;
-- nezávisle na misi i na tom, jestli ve vleku někdo sedí.
function SprayDroneStation.getCanCharge(self)
    return SprayDroneStation.getPowerState(self).running
end

-- Elektrocentrála (server): nabíječka nabíjí všechny nenabité baterie ve slotech najednou (za běhu čerpadla jen podílem
-- výkonu), nafta úměrně zátěži (getPowerShares).
function SprayDroneStation.updatePower(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local power = SprayDroneStation.getPowerState(self)
    local running = power.running
    local charging = SprayDroneStation.getNumChargingBatteries(self)
    if running then
        local s = dt * 0.001
        for _, battery in ipairs(spec.batteries) do
            if battery.slot > 0 and battery.charge < spec.batteryCapacity then
                battery.charge = math.min(battery.charge + spec.chargeRate * power.chargeFactor * s, spec.batteryCapacity)
            end
        end
        SprayDroneRelaySlots.charge(self, dt, power.chargeFactor)
        self:addFillUnitFillLevel(self:getOwnerFarmId(), spec.dieselFillUnitIndex, -spec.dieselPerSecond * power.dieselLoad * s, FillType.DIESEL,
            ToolType.UNDEFINED, nil)
        spec.powerSyncTimer = spec.powerSyncTimer - dt
        if spec.powerSyncTimer <= 0 then
            spec.powerSyncTimer = SprayDroneStation.POWER_SYNC_TIME
            self:raiseDirtyFlags(spec.dirtyFlag)
        end
    end
    if running ~= spec.generatorRunning or charging ~= spec.numCharging then
        spec.generatorRunning = running
        spec.numCharging = charging
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

function SprayDroneStation.endMission(self, status)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.missionActive = false
    spec.status = status
    spec.routeDirty = true
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
        -- prázdný vlastní seznam není hotové pole: druhý dron může zbytek stříkat (rezervace) nebo ho ještě nemá. Pole je hotové,
        -- až nic nezbývá ani mimo dosah a signál a nikdo nelétá; paměť se smaže, další mise poletí pole znovu od začátku.
        -- Zbytek jen mimo dosah/signál: mise končí hlášením a paměť zůstane (po přesunu vleku nebo tyče se pokračuje).
        local all = SprayDroneDrones.runAs(self, 1, SprayDroneStation.buildAllLegs, nil)
        local root = SprayDroneDrones.getRoot(self)
        local otherFlying = false
        for j = 1, root.numDrones do
            local d = root.drones[j]
            if d ~= spec and (d.state == SprayDroneStation.STATE_FLYING or d.state == SprayDroneStation.STATE_RETURNING) then
                otherFlying = true
            end
        end
        local total = 0
        if #all == 0 and not otherFlying then
            total = #SprayDroneDrones.runAs(self, 1, SprayDroneStation.buildAllLegs, nil, true)
        end
        local outcome = SprayDroneRoute.getEmptyLegsOutcome(#all, total, otherFlying)
        if outcome == "wait" then
            SprayDroneStation.endMission(self, SprayDroneStation.STATUS_NONE)
        else
            if outcome == "done" then
                SprayDroneStation.clearCoverage(self, spec.fieldId)
            end
            local status = outcome == "done" and SprayDroneStation.STATUS_FIELD_DONE or SprayDroneStation.STATUS_OUT_OF_REACH
            SprayDroneDrones.forEachSpec(self, function(d)
                if d.missionActive or d == spec then
                    SprayDroneStation.endMission(self, status)
                end
            end)
        end
        return
    end
    if spec.droneFillLevel < 0.5 then
        -- v hlavní nádrži je voda bez koncentrátu, nebo koncentrát bez vody: řekne se, co chybí
        local reason = SprayDroneStation.getFillSource(self).reason
        SprayDroneStation.endMission(self, reason == "noConcentrate" and SprayDroneStation.STATUS_NO_CONCENTRATE
            or (reason == "noWater" and SprayDroneStation.STATUS_NO_WATER or SprayDroneStation.STATUS_TRAILER_EMPTY))
        return
    end
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    local p = SprayDroneStation.getFlightParams(self, sprayType, restHeight)
    -- výměna baterie při servisu: jen když je pod batterySwapBelow nebo na dávku nestačí (jako ruční výměna na poli);
    -- náhradní musí být nabitá aspoň na readyCharge, jinak dron na plošině čeká, než se nabije
    local _, spareCharge = SprayDroneStation.getBestSlottedBattery(self)
    local wps, _, _, _, info, battery = SprayDroneRoute.planBatchWithSwap(legs, 1, 0, hx, hz, spec.droneFillLevel, spec.battery, p,
        math.max(spareCharge, spec.readyCharge))
    if wps ~= nil and (battery ~= spec.battery or spec.droneBattery == nil) then
        if not SprayDroneStation.swapBattery(self) then
            local blocker = SprayDroneStation.getChargeBlocker(self)
            if blocker ~= nil then
                SprayDroneStation.endMission(self, blocker)
            end
        end
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
    -- trasa mimo rádio vleku závisí na tyčích: každá musí vydržet dávku s rezervou, jinak dron čeká na plošině a zkusí to znovu
    local relays = SprayDroneStation.getBatchRelays(self, wps)
    if SprayDroneLink ~= nil and SprayDroneLink.getShortRelay(relays, info.time) ~= nil then
        SprayDroneStation.setWaitingForRelay(self, true)
        spec.serviceTimer = SprayDroneStation.RELAY_RETRY_TIME
        return
    end
    SprayDroneStation.setWaitingForRelay(self, false)
    spec.batchRelays = {}
    for _, relay in ipairs(relays) do
        table.insert(spec.batchRelays, relay.vehicle)
    end

    spec.path = wps
    spec.wpIndex = 1
    spec.pos.x, spec.pos.z, spec.pos.h = hx, hz, restHeight
    spec.pos.yaw = SprayDroneStation.getHomeYaw(self)
    spec.speed, spec.yawRate = 0, 0
    spec.airborne = false
    spec.avoidHeight, spec.avoidClimbTo = 0, nil
    spec.returnEnergyTime = -math.huge
    spec.batchHeight = info.height
    spec.sprayFrom = nil
    spec.batch = spec.batch + 1
    -- za letu plná dávka; u herbicidu ji flushSpray násobí podílem plevele pod pruhem
    spec.litersPerMeter = SprayDroneStation.getLitersPerMeter(self, sprayType)
    spec.massPerLiter = p.massPerLiter
    spec.sprayTypeIndex = sprayType.index
    spec.flightTime, spec.estimatedTime = 0, info.time
    spec.batteryAtStart, spec.estimatedEnergy = spec.battery, info.energy
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
    -- zabrzdit po směru letu, pak plynule nahoru a domů (oblouk k vleku, stoupání za letu)
    local brake = spec.speed * spec.speed / (2 * spec.acceleration)
    local dirX, dirZ = spec.moveDir.x, spec.moveDir.z
    local dl = MathUtil.vector2Length(dirX, dirZ)
    if dl > 0.01 then
        dirX, dirZ = dirX / dl, dirZ / dl
    else
        dirX, dirZ = nil, nil
    end
    local bx, bz = pos.x + spec.moveDir.x * brake, pos.z + spec.moveDir.z * brake
    local opts = { tolerance = SprayDroneStation.RETURN_TOLERANCE, startH = pos.h }
    local plan = SprayDroneStation.getTransit(self, bx, bz, false, dirX, dirZ, opts)
    if plan == nil then
        plan = SprayDroneStation.makeTransit(self, bx, bz, false, dirX, dirZ, nil, pos.h,
            select(3, SprayDroneStation.getHomePosition(self)) + SprayDroneRoute.LANDING_LIFT, true)
    end
    spec.batchHeight = math.max(plan.height, pos.h)
    spec.path = { { x = bx, z = bz, h = pos.h, speed = math.max(spec.speed, 1) } }
    for _, wp in ipairs(plan.wps) do
        table.insert(spec.path, wp)
    end
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

    local sprayType = g_sprayTypeManager:getSprayTypeByIndex(spec.sprayTypeIndex)
    local isHerbicide = sprayType ~= nil and sprayType.isHerbicide
    local fullLiters = len * spec.litersPerMeter
    local factor = 1
    if isHerbicide then
        -- plevel se měří před postřikem (herbicid stavy 1-6 přepíše)
        factor = SprayDroneRoute.getHerbicideFactor(SprayDroneStation.getWeedPixels(sx, sz, wx, wz, hx, hz))
    end
    local liters = math.min(fullLiters * factor, spec.droneFillLevel)
    spec.droneFillLevel = spec.droneFillLevel - liters
    local pf = SprayDroneStation.getPrecisionFarming()
    local changedArea
    if pf ~= nil and isHerbicide then
        changedArea = SprayDroneStation.updateSprayAreaPreventive(pf, sx, sz, wx, wz, hx, hz, spec.sprayTypeIndex)
    else
        changedArea = FSDensityMapUtil.updateSprayArea(sx, sz, wx, wz, hx, hz, spec.sprayTypeIndex, 1)
    end
    if pf ~= nil and sprayType ~= nil and not isHerbicide then
        -- dávka pruhu v l/ha (při nedostatku náplně poměrně méně)
        local litersPerHa = liters / (len * spec.workWidth) * 10000
        SprayDroneStation.applyPrecisionFarming(self, pf, sprayType, spec.droneFillType, litersPerHa, sx, sz, wx, wz, hx, hz)
    end

    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field ~= nil then
        SprayDroneRoute.markCovered(spec.coverage, field, spec.sprayTypeIndex, spec.workWidth, spec.headlands, from.x, from.z, x, z)
        SprayDroneStation.raiseCoverage(self, false)
    end

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
    -- volá se jednou za RETURN_ENERGY_INTERVAL: jako startReturnHome zabrzdit po směru letu, pak hrubý přelet (stoupání a klesání po
    -- sklonech, ostré rohy) ve výšce z plánu dávky; cesta plochou se pamatuje po 10m buňkách
    local brake = spec.speed * spec.speed / (2 * spec.acceleration)
    local bx, bz = pos.x + spec.moveDir.x * brake, pos.z + spec.moveDir.z * brake
    local points = { { x = pos.x, z = pos.z }, { x = bx, z = bz } }
    local dl = MathUtil.vector2Length(spec.moveDir.x, spec.moveDir.z)
    if dl > 0.01 and SprayDroneStation.getUseExtension(self, bx, bz, false, spec.moveDir.x / dl, spec.moveDir.z / dl) then
        local e = SprayDroneRoute.APPROACH_LENGTH / dl
        bx, bz = bx + spec.moveDir.x * e, bz + spec.moveDir.z * e
    end
    local path = SprayDroneStation.getHomePath(self, bx, bz, 10, SprayDroneStation.RETURN_TOLERANCE)
        or { { x = bx, z = bz }, { x = hx, z = hz } }
    for _, pt in ipairs(path) do
        local last = points[#points]
        if MathUtil.vector2Length(pt.x - last.x, pt.z - last.z) > 0.05 then
            table.insert(points, pt)
        end
    end
    if #points < 2 then
        table.insert(points, { x = hx, z = hz + 0.1 })
    end
    return SprayDroneRoute.returnEnergy(points, pos.h, spec.speed, pos.yaw, math.max(spec.batchHeight, pos.h), p, spec.droneFillLevel)
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
        if vertical > SprayDroneRoute.VERTICAL_PHASE_SPEED then
            phase = spec.climbFactor
        elseif vertical < -SprayDroneRoute.VERTICAL_PHASE_SPEED then
            phase = spec.descentFactor
        elseif horizontal < SprayDroneRoute.HOVER_PHASE_SPEED then
            phase = spec.hoverFactor
        end
    end
    if last == nil then
        last = {}
        spec.drainPos = last
    end
    last.x, last.z, last.h = pos.x, pos.z, pos.h
    local p = spec.drainParams
    if p == nil then
        p = {}
        spec.drainParams = p
    end
    p.droneMass, p.massPerLiter, p.fullMass = spec.droneMass, spec.massPerLiter, spec.droneMass + spec.tankCapacity * spec.massPerLiter
    spec.drainFactor = SprayDroneRoute.drainFactor(p, spec.droneFillLevel, phase)
    spec.battery = math.max(spec.battery - spec.drainFactor * s, 0)
end

-- Bod p trasy getLookaheadSpeed: waypoint wp ve výšce h, domov (wp.home) na místě vleku hx, hz.
local function setPoint(p, wp, h, hx, hz)
    if wp.home then
        p.x, p.z = hx, hz
    else
        p.x, p.z = wp.x, wp.z
    end
    p.h = h
end

-- Nejvyšší rychlost teď, aby dron stihl zpomalit na každý další bod trasy (průjezd bodem podle
-- SprayDroneRoute.junctionSpeed, stejně jako odhad pathCost): min přes body sqrt(v_bod² + 2 * acc * vzdálenost),
-- dokud je vzdálenost do brzdné dráhy; na konci trasy a před přistáním 0.
function SprayDroneStation.getLookaheadSpeed(self, pos, th, vMax)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local path = spec.path
    local acc = spec.acceleration
    local hx, hz = SprayDroneStation.getHomePosition(self)
    -- tři předalokované body (předchozí, aktuální, další) se v cyklu točí, za snímek se nic nealokuje
    local points = spec.lookaheadPoints
    if points == nil then
        points = { {}, {}, {} }
        spec.lookaheadPoints = points
    end
    local prev, cur, nextPoint = points[1], points[2], points[3]
    prev.x, prev.z, prev.h = pos.x, pos.z, pos.h
    setPoint(cur, path[spec.wpIndex], th, hx, hz)
    local dx, dz, dh = cur.x - prev.x, cur.z - prev.z, cur.h - prev.h
    local dist = math.sqrt(dx * dx + dz * dz + dh * dh)
    if dist < 0.3 and spec.wpIndex > 1 then
        local before = path[spec.wpIndex - 1]
        setPoint(prev, before, before.h + (before.land and 0 or spec.avoidHeight), hx, hz)
    end
    local limit = spec.speed * spec.speed / (2 * acc) + 5
    local target = vMax
    for j = spec.wpIndex, math.min(#path, spec.wpIndex + SprayDroneStation.LOOKAHEAD_WAYPOINTS) do
        local wp = path[j]
        local nextWp = path[j + 1]
        local cap = 0
        local hasNext = nextWp ~= nil and not wp.land
        if hasNext then
            setPoint(nextPoint, nextWp, nextWp.h + (nextWp.land and 0 or spec.avoidHeight), hx, hz)
            cap = SprayDroneRoute.junctionSpeed(prev, cur, nextPoint, wp.speed, nextWp.speed)
        end
        target = math.min(target, math.sqrt(cap * cap + 2 * acc * dist))
        if not hasNext or dist > limit then
            break
        end
        local ex, ez, eh = nextPoint.x - cur.x, nextPoint.z - cur.z, nextPoint.h - cur.h
        dist = dist + math.sqrt(ex * ex + ez * ez + eh * eh)
        prev, cur, nextPoint = cur, nextPoint, prev
    end
    return target
end

-- Pojistka: vodorovné paprsky ve výšce y (+ GUARD_HEIGHTS) přes celou šířku dronu s vrtulemi (+ GUARD_SIDE_MARGIN)
-- po dráze před dronem (od (x, z) po dalších waypointech, i do oblouku) na délku length (brzdná dráha + rezerva).
function SprayDroneStation.getIsPathBlocked(self, x, y, z, length)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local half = spec.droneRadius + SprayDroneStation.GUARD_SIDE_MARGIN
    local hx, hz = SprayDroneStation.getHomePosition(self)
    local ax, az = x, z
    local remaining = length
    for j = spec.wpIndex, #spec.path do
        local wp = spec.path[j]
        if wp.land then
            break
        end
        local bx, bz = wp.x, wp.z
        if wp.home then
            bx, bz = hx, hz
        end
        local dx, dz = bx - ax, bz - az
        local d = math.sqrt(dx * dx + dz * dz)
        if d > 0.3 then
            local dirX, dirZ = dx / d, dz / d
            local len = math.min(d, remaining)
            for _, lift in ipairs(SprayDroneStation.GUARD_HEIGHTS) do
                for s = -2, 2 do
                    local off = half * s / 2
                    if SprayDroneRoute.castRay(ax + dirZ * off, y + lift, az - dirX * off, dirX, 0, dirZ, len) then
                        return true
                    end
                end
            end
            remaining = remaining - len
            if remaining <= 0 then
                break
            end
            ax, az = bx, bz
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

-- Letí jiný dron blízko plošiny tohoto dronu (do PAD_CLEAR m vodorovně a níž než PAD_CLEAR_HEIGHT m nad ní)? Vzlet čeká.
function SprayDroneStation.getIsOtherDroneNearPad(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local root = SprayDroneDrones.getRoot(self)
    if root.numDrones < 2 then
        return false
    end
    local hx, hz, restHeight = SprayDroneStation.getHomePosition(self)
    for j = 1, root.numDrones do
        local d = root.drones[j]
        if d ~= spec and d.airborne and d.pos ~= nil
            and MathUtil.vector2Length(d.pos.x - hx, d.pos.z - hz) < SprayDroneStation.PAD_CLEAR
            and d.pos.h < restHeight + SprayDroneStation.PAD_CLEAR_HEIGHT then
            return true
        end
    end
    return false
end

-- Je dron ve spojení s vlekem? Poloha se porovná s kruhy signálu (SprayDroneLink.getSignalCircles, zvětšené o SIGNAL_MARGIN)
-- nejvýš jednou za SIGNAL_CHECK_TIME; false až po SIGNAL_LOSS_TIME s souvisle mimo signál.
function SprayDroneStation.updateSignal(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if SprayDroneLink == nil or g_time < spec.signalCheckTime then
        return spec.signalLostTime < SprayDroneStation.SIGNAL_LOSS_TIME
    end
    spec.signalCheckTime = g_time + SprayDroneStation.SIGNAL_CHECK_TIME
    if SprayDroneLink.isInCircles(SprayDroneLink.getSignalCircles(self), spec.pos.x, spec.pos.z, SprayDroneStation.SIGNAL_MARGIN) then
        spec.signalLostTime = 0
    else
        spec.signalLostTime = spec.signalLostTime + SprayDroneStation.SIGNAL_CHECK_TIME * 0.001
    end
    return spec.signalLostTime < SprayDroneStation.SIGNAL_LOSS_TIME
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
        if spec.unfold < 1 or spec.rotorSpeed < SprayDroneStation.ROTOR_MAX_SPEED * 0.95 or spec.hoseT > 0 then
            return
        end
        if SprayDroneStation.getIsOtherDroneNearPad(self) then
            spec.waitingForPad = true
            return
        end
        spec.waitingForPad = false
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
            spec.status = SprayDroneStation.STATUS_TRAILER_MOVED
        end
        if g_time >= spec.returnEnergyTime then
            spec.returnEnergyTime = g_time + SprayDroneStation.RETURN_ENERGY_INTERVAL
            spec.returnEnergy = SprayDroneStation.getReturnEnergy(self)
        end
        if trailerMoving or spec.droneFillLevel <= 0 or spec.battery < spec.returnEnergy + 5 then
            SprayDroneStation.startReturnHome(self)
            return
        end
        -- ztráta signálu (vypadlá tyč): postřik se přeruší a dron letí domů; návrat přes místa bez signálu se toleruje
        if not SprayDroneStation.updateSignal(self) then
            spec.missionActive = false
            spec.status = SprayDroneStation.STATUS_NO_SIGNAL
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
    local terrainY = getTerrainHeightAtWorldPos(g_terrainNode, pos.x, 0, pos.z)

    local heading = horizontal > 0.5 and MathUtil.getYRotationFromDirection(dx, dz) or nil
    if horizontal <= 0.5 then
        -- těsně u bodu (hustě dělené oblouky) míří nos už po dalším úseku, jinak by se natáčení zastavilo
        local nextWp = spec.path[spec.wpIndex + 1]
        if wp.home then
            heading = SprayDroneStation.getHomeYaw(self)
        elseif nextWp ~= nil and not nextWp.home and not nextWp.land then
            local nx, nz = nextWp.x - tx, nextWp.z - tz
            if nx * nx + nz * nz > 0.09 then
                heading = MathUtil.getYRotationFromDirection(nx, nz)
            end
        end
    end
    SprayDroneStation.updateYaw(self, heading, s)

    -- pojistka: překážka před dronem -> zabrzdit, stoupat, dokud paprsek neprojde, a ještě GUARD_EXTRA_CLIMB;
    -- pak letět dál o avoidHeight výš, dokud pod dronem něco je
    if spec.avoidClimbTo == nil and horizontal > 0.5 and not wp.land and g_time >= spec.guardOffUntil
        and g_time >= spec.guardNextCheck then
        spec.guardNextCheck = g_time + SprayDroneStation.GUARD_CHECK_INTERVAL
        local length = spec.speed * spec.speed / (2 * acc) + SprayDroneStation.GUARD_MARGIN
        if SprayDroneStation.getIsPathBlocked(self, pos.x, terrainY + pos.h, pos.z, length) then
            spec.avoidClimbTo = math.huge
            spec.avoidRayLength = length
        end
    end
    if spec.avoidClimbTo ~= nil then
        spec.speed = math.max(spec.speed - 2 * acc * s, 0)
        pos.x, pos.z = pos.x + spec.moveDir.x * spec.speed * s, pos.z + spec.moveDir.z * spec.speed * s
        if spec.speed < 0.3 then
            pos.h = pos.h + spec.ascentSpeed * s
            if spec.avoidClimbTo == math.huge and not SprayDroneStation.getIsPathBlocked(self, pos.x, terrainY + pos.h, pos.z,
                spec.avoidRayLength) then
                spec.avoidClimbTo = pos.h + SprayDroneStation.GUARD_EXTRA_CLIMB
            end
            spec.avoidHeight = math.max(spec.avoidHeight, pos.h - (th - spec.avoidHeight))
            if pos.h >= spec.avoidClimbTo then
                spec.avoidClimbTo = nil
            elseif pos.h >= spec.maxTransitHeight + spec.layerOffset + SprayDroneStation.GUARD_CEILING_MARGIN then
                -- překážka nad stropem: dron nestoupá dál; mise končí návratem a hlášením, při návratu paprsky chvíli ignoruje
                spec.avoidClimbTo = nil
                spec.guardOffUntil = g_time + SprayDroneStation.GUARD_GIVE_UP_TIME
                if spec.state == SprayDroneStation.STATE_FLYING then
                    spec.missionActive = false
                    SprayDroneStation.startReturnHome(self)
                    spec.status = SprayDroneStation.STATUS_OBSTACLE
                end
            end
        end
        SprayDroneStation.setDroneWorldPosition(self, pos.x, getTerrainHeightAtWorldPos(g_terrainNode, pos.x, 0, pos.z) + pos.h, pos.z, pos.yaw)
        SprayDroneStation.raiseFlightSync(self, dt)
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
    local target = SprayDroneStation.getLookaheadSpeed(self, pos, th, vMax)
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
            SprayDroneStation.attachDrone(self)
            spec.path = nil
            spec.speed, spec.yawRate, spec.avoidHeight, spec.avoidClimbTo = 0, 0, 0, nil
            spec.airborne = false
            SprayDroneStation.setState(self, SprayDroneStation.STATE_SERVICING)
            spec.serviceTimer = SprayDroneStation.SERVICE_TIME
        end
    end
    SprayDroneStation.raiseFlightSync(self, dt)
end

-- Za letu se každý snímek posílá jen poloha dronů (positionDirtyFlag), celý stav (baterie, náplň, …) jen jednou za
-- POWER_SYNC_TIME; změny stavu (start, přistání, postřik zap/vyp) si celý stav vyžádají samy.
function SprayDroneStation.raiseFlightSync(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    self:raiseDirtyFlags(spec.positionDirtyFlag)
    spec.flightSyncTimer = spec.flightSyncTimer - dt
    if spec.flightSyncTimer <= 0 then
        spec.flightSyncTimer = SprayDroneStation.POWER_SYNC_TIME
        self:raiseDirtyFlags(spec.dirtyFlag)
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
    if self.isClient then
        SprayDroneHotspot.update(spec, flying)
        SprayDroneStation.notifyStatus(self)
    end

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

    -- ve vzduchu zůstává rozložený (vlek se za letu složit nedá). Rozložení jde za časem skládání nejvýš rychlostí,
    -- jakou se dron skládá: při rozkládání vanilla AnimatedVehicle skočí z konce posledního dílu animace (žebřík,
    -- úchyty od 2 s) rovnou na čas 0, takže čas skládání by dron rozložil naráz
    spec.unfoldMoving = false
    if spec.isLinked then
        local target = SprayDroneStation.getTrailerUnfold(self)
        local foldable = self.spec_foldable
        local duration = foldable ~= nil and foldable.maxFoldAnimDuration or 3000
        local step = dt / math.max(spec.trailerFoldEnd * duration, 1)
        if target > spec.unfold then
            spec.unfold = math.min(spec.unfold + step, target)
        else
            spec.unfold = math.max(spec.unfold - step * SprayDroneStation.FOLD_SPEEDUP, target)
        end
        spec.unfoldMoving = spec.unfold ~= target
    end
    SprayDroneStation.applyFold(self)
    spec.rotorsParked = rotorsParked

    SprayDroneStation.updateTilt(self, dt)
    SprayDroneStation.updateRotorSound(self, dt)
    SprayDroneStation.updateSprayEffects(self)
    SprayDroneStation.updateSpraySound(self)
    SprayDroneStation.applyNavLights(self, flying or spec.rotorSpeed > 0)
end

-- Konec mise (nenulový status) se hráči z farmy vleku ohlásí i mimo vlek, jako ingame notifikace; počítá se jen změna statusu
-- vzniklá za hry, ne stav, který klient dostal při připojení (readState ho tam zapíše do notifiedStatus). V kontextu dronu.
function SprayDroneStation.notifyStatus(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local status = spec.status
    if status == spec.notifiedStatus then
        return
    end
    spec.notifiedStatus = status
    local textKey = SprayDroneStation.STATUS_TEXTS[status]
    local mission = g_currentMission
    if textKey == nil or g_dedicatedServer ~= nil or mission == nil or not mission.accessHandler:canFarmAccess(mission:getFarmId(), self) then
        return
    end
    local index = spec.droneIndex or 1
    if (status == SprayDroneStation.STATUS_FIELD_DONE or status == SprayDroneStation.STATUS_OUT_OF_REACH) and index > 1
        and spec.rootSpec.status == status then
        return
    end
    local text = g_i18n:getText(textKey)
    if spec.numDrones > 1 then
        text = string.format("%d: %s", index, text)
    end
    local kind = FSBaseMission.INGAME_NOTIFICATION_CRITICAL
    if status == SprayDroneStation.STATUS_FIELD_DONE then
        kind = FSBaseMission.INGAME_NOTIFICATION_OK
    elseif status == SprayDroneStation.STATUS_ABORTED then
        kind = FSBaseMission.INGAME_NOTIFICATION_INFO
    end
    mission:addIngameNotification(kind, string.format("%s: %s", self:getName(), text))
end

-- Vizuál vleku: výfuk centrály, zvuky vleku, baterie v nabíječce, úchyty a hadice dronů (vozidlový kontext, po vizuálu dronů).
function SprayDroneStation.updateVehicleVisual(self, dt)
    SprayDroneLadder.update(self)
    SprayDroneStation.updateGenerator(self)
    SprayDroneSound.updateSounds(self, dt)
    SprayDroneStation.updateServiceVisuals(self, dt)
end

-- LED ramen: svítí, dokud je dron zapnutý (letí nebo se točí vrtule); blikající LED podle navBlinkPeriod. Svit jde
-- přes parametr lightIds0 materiálu staticLight_vertex (barva je v barvě vrcholů), bodové světlo se zapíná s ním,
-- ale jen výš než LED_LIGHT_MIN_HEIGHT nad plošinou (na vleku by celý vlek nasvítilo do červena a zelena).
function SprayDroneStation.applyNavLights(self, powered)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local blinkOn = g_time % spec.navBlinkPeriod < spec.navBlinkOn
    local lightAllowed = powered and not spec.isLinked
        and SprayDroneStation.getDroneHeightAbovePlatform(self) >= SprayDroneStation.LED_LIGHT_MIN_HEIGHT
    for _, light in ipairs(spec.navLights) do
        local isOn = powered and (not light.blink or blinkOn)
        if light.isOn ~= isOn then
            light.isOn = isOn
            setShaderParameter(light.node, "lightIds0", isOn and spec.navLightIntensity or 0, 0, 0, 0, false)
        end
        local lightOn = isOn and lightAllowed
        if light.lightNode ~= nil and light.lightOn ~= lightOn then
            light.lightOn = lightOn
            setVisibility(light.lightNode, lightOn)
        end
    end
end

-- Výška kořene dronu nad místem, kde sedí na plošině (m); na vleku 0. Z polohy uzlu, takže sedí i u klientů.
function SprayDroneStation.getDroneHeightAbovePlatform(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.isLinked or spec.node == nil then
        return 0
    end
    local _, y, _ = getWorldTranslation(spec.node)
    local _, homeY, _ = localToWorld(spec.parent, spec.localTrans[1], spec.localTrans[2], spec.localTrans[3])
    return y - homeY
end

-- Výfuk centrály (vanilla efekt výfuku z $data), při nabíjení viditelný a bez náklonu.
function SprayDroneStation.loadExhaust(self, xml, key, nodeAttribute, field)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local linkNode = xml:getValue(key .. nodeAttribute, nil, self.components, self.i3dMappings)
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
    spec[field] = { node = node, requestId = requestId, color = xml:getValue(key .. "#color", nil, true) or { 0.1, 0.1, 0.1, 0.3 },
        scale = xml:getValue(key .. "#scale", 0.3), shown = false }
end

function SprayDroneStation.updateGenerator(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local running = spec.generatorRunning
    for _, exhaust in ipairs({ spec.exhaust or false, spec.exhaust2 or false }) do
        if exhaust and exhaust.shown ~= running then
            exhaust.shown = running
            setVisibility(exhaust.node, running)
            if running then
                local c = exhaust.color
                setShaderParameter(exhaust.node, "param", 0, 0, 0, exhaust.scale, false)
                setShaderParameter(exhaust.node, "exhaustColor", c[1], c[2], c[3], c[4], false)
            end
        end
    end
end

-- Výška a místa trysek pro efekty postřiku; emitory umístí až placeSprayEffects při prvním zapnutí postřiku, kdy už je
-- dron rozložený (polohy trysek se berou z uzlů dronu).
function SprayDroneStation.loadSprayEffectPlacement(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.sprayEffectPlacement = {
        nozzleY = xml:getValue(key .. "#nozzleY", 0),
        nozzles = {},
        nozzlePositions = {}
    }
    xml:iterate(key .. ".nozzle", function(_, nozzleKey)
        local node = xml:getValue(nozzleKey .. "#node", nil, self.components, self.i3dMappings)
        local x, z = xml:getValue(nozzleKey .. "#x"), xml:getValue(nozzleKey .. "#z")
        if node ~= nil then
            table.insert(spec.sprayEffectPlacement.nozzles, node)
        elseif x ~= nil and z ~= nil then
            table.insert(spec.sprayEffectPlacement.nozzlePositions, { x = x, z = z })
        end
    end)
end

-- Místa trysek v souřadnicích kořene dronu (x, z): uzly effects.nozzle, pak effects.nozzle#x/#z (varianta S a L: dvě
-- trysky vzadu / na rameni postřiku), jinak pod motory ramen (vrtule, souosé páry jednou), jinak rovnoměrně napříč dronem.
function SprayDroneStation.getNozzlePositions(self, count)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local positions = {}
    local fixed = spec.sprayEffectPlacement.nozzlePositions or {}
    if #spec.sprayEffectPlacement.nozzles == 0 and #fixed >= count then
        for i = 1, count do
            positions[i] = { x = fixed[i].x, z = fixed[i].z }
        end
        return positions
    end
    local nodes = spec.sprayEffectPlacement.nozzles
    if #nodes == 0 then
        nodes = {}
        for _, rotor in ipairs(spec.rotors) do
            table.insert(nodes, rotor.node)
        end
    end
    for _, node in ipairs(nodes) do
        local x, _, z = localToLocal(node, spec.node, 0, 0, 0)
        local duplicate = false
        for _, p in ipairs(positions) do
            duplicate = duplicate or MathUtil.vector2Length(p.x - x, p.z - z) < 0.2
        end
        if not duplicate and #positions < count then
            table.insert(positions, { x = x, z = z })
        end
    end
    if #positions < count then
        positions = {}
        for i = 1, count do
            table.insert(positions, { x = -spec.workWidth * 0.25 + (i - 0.5) * spec.workWidth * 0.5 / count, z = 0 })
        end
    end
    return positions
end

-- Mlha z trysek (vlastní částicový efekt effects/sprayMist.i3d, jeden emitor na trysku): kužel od trysky dolů, který se
-- do výšky postřiku rozšíří na záběr varianty. Emitory se jen umístí pod trysky v souřadnicích kloubu náklonu, směr
-- (dolů) a rozevření kužele jsou v i3d. Vrací, jestli jsou emitory načtené.
function SprayDroneStation.placeSprayEffects(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local effects, pl = spec.effects, spec.sprayEffectPlacement
    for _, effect in ipairs(effects) do
        if effect.node == nil then
            return false
        end
    end
    local nozzles = SprayDroneStation.getNozzlePositions(self, #effects)
    for i, effect in ipairs(effects) do
        local node = effect.node
        local parent = getParent(node)
        local nozzle = nozzles[math.min(i, #nozzles)]
        local _, parentY, _ = localToLocal(parent, spec.node, 0, 0, 0)
        setTranslation(node, localToLocal(spec.node, parent, nozzle.x, parentY + pl.nozzleY, nozzle.z))
    end
    return true
end

-- Postřik je vidět, když dron na řádku opravdu stříká (server) nebo to tak hlásí stav letu (klient).
function SprayDroneStation.updateSprayEffects(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if self.isServer then
        local active = spec.state == SprayDroneStation.STATE_FLYING and spec.lastSprayTime + 150 > g_time
        if active ~= spec.sprayEffectsActive then
            spec.sprayEffectsActive = active
            self:raiseDirtyFlags(spec.dirtyFlag)
        end
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
    if spec.sprayEffectsActive and spec.droneFillType ~= FillType.UNKNOWN then
        SprayDroneStation.setSprayMistColor(spec.effects, spec.droneFillType)
    end
    SprayDroneStation.setSprayMistEmitting(spec.effects, spec.sprayEffectsActive)
end

-- Zvuk postřiku (vzorek spray z <sounds> dronu, vanilla defaultSprayer): hraje, dokud dron stříká (stejně jako mlha).
function SprayDroneStation.updateSpraySound(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local sample = spec.samples.spray
    if sample == nil or spec.sprayEffectsActive == spec.spraySoundOn then
        return
    end
    spec.spraySoundOn = spec.sprayEffectsActive
    if spec.sprayEffectsActive then
        g_soundManager:playSample(sample)
    else
        g_soundManager:stopSample(sample)
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
        -- větší dron hlubší (rotorPitch varianty)
        spec.soundPitch = (minPitch + (1 - minPitch) * f) * spec.rotorPitch * (spec.rotorPitchFactor or 1)
        spec.soundVolume = f ^ SprayDroneStation.SOUND_VOLUME_EXPONENT
        g_soundManager:setSamplePitchOffset(sample, spec.soundPitch - 1)
        g_soundManager:setSampleVolumeScale(sample, spec.rotorVolumeScale * spec.soundVolume)
        -- se zpožděním startu nemusí vzorek hned hlásit, že hraje: znovu se zkouší nejdřív po ROTOR_RETRY_TIME
        if not g_soundManager:getIsSamplePlaying(sample) and g_time >= (spec.rotorRetryTime or 0) then
            spec.rotorRetryTime = g_time + SprayDroneStation.ROTOR_RETRY_TIME
            g_soundManager:playSample(sample, spec.rotorStartDelay)
        end
    elseif g_soundManager:getIsSamplePlaying(sample) then
        spec.soundPitch, spec.soundVolume = 0, 0
        g_soundManager:stopSample(sample)
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
        else
            last = {}
            spec.lastWorldPos = last
        end
        last.x, last.z = x, z
    end
    local f = math.min(dt * SprayDroneStation.TILT_FOLLOW, 1)
    tilt.pitch = tilt.pitch + (pitch - tilt.pitch) * f
    tilt.roll = tilt.roll + (roll - tilt.roll) * f
    setRotation(spec.tiltNode, tilt.pitch, 0, tilt.roll)
end

function SprayDroneStation.getIsFrozen(self)
    return self:getFoldAnimTime() < SprayDroneStation.FREEZE_BELOW
end

-- Hráč sedí v tahači zapřaženého rozloženého vleku a chce jet: tahač s kinematickým vlekem neodjede, tak řekne proč.
-- Jen klient, který řídí; levné podmínky jdou první, takže u stojícího nebo nezapřaženého vleku se nic nepočítá.
function SprayDroneStation.updateStuckWarning(self)
    local attacher = self:getAttacherVehicle()
    if attacher == nil or not SprayDroneStation.getIsFrozen(self) then
        return
    end
    local spec = self[SprayDroneStation.SPEC_NAME]
    if g_time < (spec.stuckWarningTime or 0) then
        return
    end
    local root = self:getRootVehicle()
    local drivable = root ~= nil and root.spec_drivable or nil
    if drivable == nil or root.getIsEntered == nil or not root:getIsEntered() or math.abs(drivable.axisForward) < SprayDroneStation.STUCK_AXIS
        or root:getLastSpeed() >= SprayDroneStation.STUCK_MAX_SPEED or not root:getIsMotorStarted() then
        return
    end
    spec.stuckWarningTime = g_time + SprayDroneStation.STUCK_WARNING_INTERVAL
    g_currentMission:showBlinkingWarning(g_i18n:getText("sdt_warning_trailerUnfolded"), SprayDroneStation.STUCK_WARNING_TIME)
end

-- Rozložený vlek stojí na místě: fyzika komponenty je kinematická (nejde s ním odjet ani ho posunout), připojit a odpojit
-- ho nejde (foldingParts#attachingMinLimit / detachingMinLimit). Po složení se fyzika vrátí.
--
-- Pozor: po přepnutí dynamického tělesa na kinematické za běhu engine odsune všechny dětské kolizní tvary (compoundChild) o těžiště
-- komponenty nahoru (hráč pak prochází nádržemi a propadá palubou; těžiště se v kinematickém stavu čte jako 0). Tvary ve skupině
-- "collisions" (i závěsy kolizí plachet colTarpHinge*, foldLadder je jen otáčí) se proto na dobu zmrazení posunou o těžiště zpět
-- (původní polohy si skript pamatuje). Kořenový tvar komponenty se takhle
-- opravit nedá, proto je v i3d jen drobná krychle a rám vleku je dětský tvar colChassis.
function SprayDroneStation.shiftCollisionShapes(self, spec, frozen)
    local node = self.components[1].node
    local com = spec.centerOfMass
    if com == nil then
        return
    end
    for i = 0, getNumOfChildren(node) - 1 do
        local group = getChildAt(node, i)
        if getName(group) == "collisions" then
            spec.shapeOrigins = spec.shapeOrigins or {}
            for j = 0, getNumOfChildren(group) - 1 do
                local shape = getChildAt(group, j)
                if spec.shapeOrigins[shape] == nil then
                    spec.shapeOrigins[shape] = { getTranslation(shape) }
                end
                local o = spec.shapeOrigins[shape]
                if frozen then
                    setTranslation(shape, o[1] - com[1], o[2] - com[2], o[3] - com[3])
                else
                    setTranslation(shape, o[1], o[2], o[3])
                end
            end
        end
    end
end

-- Kolize panelů bedny (colPad*, Mini) visí na čepech, které se při rozkládání otáčejí: posun o těžiště se proto počítá v lokální soustavě
-- jejich rodiče a při zmrazení se obnovuje každý update.
function SprayDroneStation.updatePadShapes(self, spec)
    local com = spec.centerOfMass
    if com == nil then
        return
    end
    if spec.padShapes == nil then
        spec.padShapes = {}
        local function collect(node)
            for i = 0, getNumOfChildren(node) - 1 do
                local child = getChildAt(node, i)
                if string.sub(getName(child), 1, 6) == "colPad" then
                    table.insert(spec.padShapes, { node = child, parent = node, origin = { getTranslation(child) } })
                end
                collect(child)
            end
        end
        collect(self.components[1].node)
    end
    for _, pad in ipairs(spec.padShapes) do
        local o = pad.origin
        if spec.frozen and not spec.loadedFrozen then
            local dx, dy, dz = localDirectionToLocal(self.components[1].node, pad.parent, -com[1], -com[2], -com[3])
            setTranslation(pad.node, o[1] + dx, o[2] + dy, o[3] + dz)
        else
            setTranslation(pad.node, o[1], o[2], o[3])
        end
    end
end

function SprayDroneStation.updateFreeze(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if self.getFoldAnimTime == nil or self.components == nil or self.components[1] == nil then
        return
    end
    local frozen = SprayDroneStation.getIsFrozen(self)
    if frozen ~= spec.frozen then
        local node = self.components[1].node
        if frozen then
            spec.centerOfMass = { getCenterOfMass(node) }
        end
        -- rozložený vlek uložený ve hře je kinematický od prvního updatu, než se těleso stihlo kdy chovat dynamicky: tam se nic neposouvá
        local loadedFrozen = spec.frozen == nil and frozen
        spec.loadedFrozen = loadedFrozen
        spec.frozen = frozen
        setRigidBodyType(node, frozen and RigidBodyType.KINEMATIC or RigidBodyType.DYNAMIC)
        if not loadedFrozen then
            SprayDroneStation.shiftCollisionShapes(self, spec, frozen)
            SprayDroneStation.updatePadShapes(self, spec)
        end
    end
    if spec.frozen and not spec.loadedFrozen then
        SprayDroneStation.updatePadShapes(self, spec)
    end
end

-- Logika jednoho dronu na serveru: let, nebo servis na plošině (v kontextu dronu).
function SprayDroneStation.updateDroneLogic(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.state == SprayDroneStation.STATE_FLYING or spec.state == SprayDroneStation.STATE_RETURNING then
        SprayDroneStation.updateFlight(self, dt)
    elseif spec.state == SprayDroneStation.STATE_SERVICING then
        SprayDroneStation.updateService(self, dt)
    end
end

function SprayDroneStation.updateDroneClient(self, dt)
    if self[SprayDroneStation.SPEC_NAME].hasDrone then
        SprayDroneStation.updateClientInterpolation(self, dt)
    end
end

-- Nafta do centrály přibyla (čerpací stanice, kanystr): spící vlek se probudí, ať se začne nabíjet.
function SprayDroneStation:onFillUnitFillLevelChanged(fillUnitIndex, fillLevelDelta)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if self.isServer and spec ~= nil and fillUnitIndex == spec.dieselFillUnitIndex and fillLevelDelta > 0 then
        self:raiseActive()
    end
end

function SprayDroneStation:onUpdate(dt, isActiveForInput, isActiveForInputIgnoreSelection, isSelected)
    SprayDroneDrones.restoreRoot(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    -- deska s dronem se hýbe nejdřív, ostatní (hadice, dron) se řídí její polohou
    SprayDronePad.update(self, dt)
    -- bez dronu zůstává stav PARKED: jen vlek (nabíječka, centrála, hadice, přečerpání do IBC)
    SprayDroneDrones.forEach(self, SprayDroneStation.updateDroneParts, dt)
    SprayDroneStation.updateVehicleVisual(self, dt)
    if self.isServer then
        local simDt = dt
        SprayDroneDrones.forEach(self, SprayDroneStation.updateDroneLogic, simDt)
        SprayDroneStation.updateFreeze(self)
        SprayDroneDrones.forEach(self, SprayDroneStation.updateBatteryPlacement)
        SprayDroneStation.updatePower(self, dt)
        SprayDroneStation.updateTransfer(self, dt)
    else
        SprayDroneDrones.forEach(self, SprayDroneStation.updateDroneClient, dt)
    end
    if self.isClient then
        SprayDroneStation.updateStuckWarning(self)
    end

    -- skládání vleku drží vozidlo aktivní jen po dobu animace; rozložení dronu a hadice dobíhají i po ní
    local active = spec.generatorRunning or spec.transferMode ~= SprayDroneStation.TRANSFER_NONE or SprayDronePad.needsUpdate(self) or (self.isServer and SprayDroneStation.getCanCharge(self))
    if not active then
        active = SprayDroneDrones.any(self, function(d)
            return d.state ~= SprayDroneStation.STATE_PARKED or d.rotorSpeed > 0 or not d.rotorsParked or d.unfoldMoving or d.hoseT > 0
        end)
    end
    if active then
        self:raiseActive()
    end

    if self.isClient and self:getIsEntered() then
        SprayDroneStation.updatePilotView(self, dt)
    elseif self.isClient and isActiveForInputIgnoreSelection then
        SprayDroneStation.updateActionEventStates(self)
    end
    -- obrys desky se počítá a kreslí jen u stojícího vleku (před rozložením), ne za jízdy
    if self.isClient and isActiveForInputIgnoreSelection and self:getLastSpeed() < SprayDroneStation.PAD_PREVIEW_MAX_SPEED then
        SprayDronePad.drawPreview(self)
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
-- trasy druhého dronu ve studených barvách
SprayDroneStation.BATCH_COLORS_2 = {
    { 0, 0.9, 0.8 }, { 0.2, 1, 0.2 }, { 1, 1, 1 }, { 1, 0.5, 0.7 }
}

function SprayDroneStation.getBatchColors(index)
    return index == 2 and SprayDroneStation.BATCH_COLORS_2 or SprayDroneStation.BATCH_COLORS
end
-- ve světě se kreslí jen přelety prvních dvou dávek (tam a zpět), dráha zaoblení má hodně bodů
SprayDroneStation.WORLD_TRANSITS = 4

-- Přepočet náhledu trasy, když se změnilo pole nebo stav, a za letu každých ROUTE_REFRESH_TIME.
-- Volá ho pohled pilota i plánovač; vrací vybrané pole.
function SprayDroneStation.refreshRoutePreview(self, dt)
    local spec = SprayDroneDrones.getRoot(self)
    SprayDroneDrones.forEach(self, SprayDroneStation.refreshDroneRoutePreview, dt)
    return SprayDroneRoute.getFieldById(spec.fieldId)
end

function SprayDroneStation.refreshDroneRoutePreview(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.routeTimer = spec.routeTimer - dt
    SprayDroneStation.updateRange(self)
    if spec.routeDirty or (spec.missionActive and spec.routeTimer <= 0) then
        SprayDroneStation.updateRoutePreview(self)
    end
end

-- Dosah ve světě jako nízký "plot" (dvě výšky a sloupky), aby byl vidět i na 300 m: obrys signálu (rádio vleku tyrkysově, úseky
-- relé tyčí oranžově jako v plánovači, SprayDroneLink.getCoverageArcs) a tence dosah z baterie, když se od rádia liší.
SprayDroneStation.WORLD_SIGNAL_SEGMENTS = 90

function SprayDroneStation.drawWorldSignal(self, hx, hz)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local segments = SprayDroneStation.WORLD_SIGNAL_SEGMENTS
    local lines = SprayDroneLink ~= nil and SprayDroneLink.getCoverageArcs(SprayDroneLink.getSignalCircles(self), segments) or nil
    local relayColor = SprayDronePlannerScreen.COLOR_RELAY
    for _, line in ipairs(lines or {}) do
        local r, g, b = 0, 1, 1
        if line.circle ~= 1 then
            r, g, b = relayColor[1], relayColor[2], relayColor[3]
        end
        drawTerrainLine(line.x1, line.z1, line.x2, line.z2, r, g, b, 0.5)
        drawTerrainLine(line.x1, line.z1, line.x2, line.z2, r, g, b, 4)
        local y = getTerrainHeightAtWorldPos(g_terrainNode, line.x1, 0, line.z1)
        drawDebugLine(line.x1, y, line.z1, r, g, b, line.x1, y + 4, line.z1, r, g, b)
    end
    if lines == nil or math.abs(spec.range - spec.maxRange) > 1 then
        for i = 0, segments - 1 do
            local a1, a2 = i / segments * 2 * math.pi, (i + 1) / segments * 2 * math.pi
            drawTerrainLine(hx + math.cos(a1) * spec.range, hz + math.sin(a1) * spec.range,
                hx + math.cos(a2) * spec.range, hz + math.sin(a2) * spec.range, 0, 1, 1, 0.5)
        end
    end
end

function SprayDroneStation.updatePilotView(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if not spec.hasDrone then
        SprayDroneStation.updateActionEventStates(self)
        SprayDroneStation.drawHudTexts(self, nil)
        return
    end
    local hx, hz = SprayDroneStation.getHomePosition(self)

    local showLines = SprayDroneStation.showWorldLines
    if showLines then
        SprayDroneStation.drawWorldSignal(self, hx, hz)
    end

    local field = SprayDroneStation.refreshRoutePreview(self, dt)
    if field ~= nil and showLines then
        drawPolygon(SprayDroneRoute.getPolygon(field), 0, 1, 0, 0.6)
        drawPolygon(SprayDroneRoute.getPolygon(field), 0, 1, 0, 1.5)
        local area = SprayDroneStation.getFlightArea(self)
        if area ~= nil then
            drawPolygon(area, 0.7, 0.4, 1, 1)
        end
        for k = 1, spec.numDrones do
            local d = spec.drones[k]
            local colors = SprayDroneStation.getBatchColors(k)
            for _, leg in ipairs(d.drawLegs) do
                local c = colors[(leg.batch - 1) % #colors + 1]
                drawTerrainLine(leg.x1, leg.z1, leg.x2, leg.z2, c[1], c[2], c[3], 0.3)
            end
            -- přelety prvních dvou dávek po skutečné dráze a ve výšce, ve které je dron poletí; přejezdy mezi řádky
            for n, plan in ipairs(d.routeInfo.transits or {}) do
                if n > SprayDroneStation.WORLD_TRANSITS then
                    break
                end
                for j = 1, #plan.points - 1 do
                    local a, b = plan.points[j], plan.points[j + 1]
                    drawTerrainLine(a.x, a.z, b.x, b.z, 1, 1, 1, plan.heights[j])
                end
            end
            for _, turn in ipairs(d.routeInfo.turns or {}) do
                local c = colors[(turn.batch - 1) % #colors + 1]
                for j = 1, #turn.points - 1 do
                    local a, b = turn.points[j], turn.points[j + 1]
                    drawTerrainLine(a.x, a.z, b.x, b.z, c[1] * 0.6, c[2] * 0.6, c[3] * 0.6, 0.3)
                end
            end
        end
    end

    SprayDroneStation.updateActionEventStates(self)
    SprayDroneStation.drawHudTexts(self, field)
end

-- Textové řádky pod ovládací nápovědou: co nejméně a jen k věci. Dron = jeden řádek (stav, pole, dávky); přečerpávání,
-- míchání a hlášení mise přibudou jen, když se to opravdu děje.
function SprayDroneStation.drawHudTexts(self, field)
    local spec = self[SprayDroneStation.SPEC_NAME]
    SprayDroneLevel.drawTilt(self)
    local mission = g_currentMission
    local i18n = g_i18n
    if not spec.hasDrone then
        mission:addExtraPrintText(i18n:getText("sdt_hud_noDrone"))
        local batteries, generator = SprayDroneStation.getPowerTexts(self)
        mission:addExtraPrintText(batteries .. " · " .. generator)
    else
        SprayDroneDrones.forEachSpec(self, function(d)
            local prefix = spec.numDrones > 1 and string.format("%d: ", d.droneIndex or 1) or ""
            local stateText = SprayDroneStation.getDroneStateName(self)
            if field ~= nil then
                mission:addExtraPrintText(prefix .. string.format(i18n:getText("sdt_hud_droneField"), stateText, field:getName(), d.numBatches))
            else
                mission:addExtraPrintText(prefix .. string.format(i18n:getText("sdt_hud_droneNoField"), stateText))
            end
        end)
    end
    local transferText = SprayDroneStation.getTransferText(self)
    if transferText ~= nil then
        mission:addExtraPrintText(transferText)
    end
    if spec.hasDrone then
        local mixerText = SprayDroneStation.getMixerText(self)
        if mixerText ~= nil then
            mission:addExtraPrintText(mixerText)
        end
        SprayDroneDrones.forEachSpec(self, function(d)
            local statusText = SprayDroneStation.STATUS_TEXTS[d.status]
            if statusText ~= nil then
                mission:addExtraPrintText((spec.numDrones > 1 and string.format("%d: ", d.droneIndex or 1) or "") .. i18n:getText(statusText))
            end
        end)
    end
end

-- Řádek o mixéru: při plnění dronu s mícháním podíl a zásoby; varování, že v hlavní nádrži je voda bez koncentrátu (nebo
-- naopak), jen když je k věci, tedy je vybrané pole, dron není plný a hlášení mise (status) totéž neříká samo; jinak nil.
function SprayDroneStation.getMixerText(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local source = SprayDroneStation.getFillSource(self)
    local isMixing = SprayDroneDrones.any(self, function(d)
        return d.isMixing
    end)
    local notFull = SprayDroneDrones.any(self, function(d)
        return d.droneFillLevel < d.tankCapacity - SprayDroneMixer.EPSILON
    end)
    local noStatus = not SprayDroneDrones.any(self, function(d)
        return SprayDroneStation.STATUS_TEXTS[d.status] ~= nil
    end)
    if isMixing and source.kind == SprayDroneMixer.KIND_MIX then
        return string.format(g_i18n:getText("sdt_hud_mixing"), source.ratio * 100, source.water, source.concentrate)
    elseif source.kind == SprayDroneMixer.KIND_NONE and source.reason ~= "empty" and spec.fieldId ~= 0
        and notFull and noStatus then
        return g_i18n:getText(source.reason == "noConcentrate" and "sdt_hud_noConcentrate" or "sdt_hud_noWater")
    end
    return nil
end

-- Stav dronu slovy ("na vleku", "letí dávku", "čeká na nabití baterie – 40 %", …).
function SprayDroneStation.getDroneStateName(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local stateText = g_i18n:getText(SprayDroneStation.STATE_TEXTS[spec.state])
    if not spec.hasDrone then
        stateText = g_i18n:getText("sdt_state_noDrone")
    elseif #spec.batteries == 0 then
        stateText = g_i18n:getText("sdt_state_noBatteries")
    elseif spec.state == SprayDroneStation.STATE_SERVICING then
        if spec.waitingForCharge then
            local _, charge = SprayDroneStation.getBestSlottedBattery(self)
            stateText = string.format(g_i18n:getText("sdt_state_waitCharge"), charge / spec.batteryCapacity * 100)
        elseif spec.waitingForPower then
            stateText = string.format(g_i18n:getText("sdt_state_waitPower"), g_i18n:getText(SprayDroneStation.getNoPowerTextKey(self)))
        elseif spec.waitingForRelay and not spec.isPumping and not spec.isSwapping then
            stateText = g_i18n:getText("sdt_state_waitRelay")
        elseif spec.isPumping and spec.isSwapping then
            stateText = g_i18n:getText(spec.isMixing and "sdt_state_mixingSwapping" or "sdt_state_pumpingSwapping")
        elseif spec.isPumping then
            stateText = string.format(g_i18n:getText(spec.isMixing and "sdt_state_mixing" or "sdt_state_pumping"), spec.pumpRate * 60)
        elseif spec.isSwapping then
            stateText = g_i18n:getText("sdt_state_swapping")
        end
    elseif spec.state == SprayDroneStation.STATE_FLYING and spec.waitingForPad then
        stateText = g_i18n:getText("sdt_state_waitPad")
    elseif SprayDroneStation.getIsDroneSecured(self) then
        stateText = g_i18n:getText("sdt_state_secured")
    elseif spec.state == SprayDroneStation.STATE_PARKED and spec.droneBattery == nil and spec.unfold >= 1 then
        local _, charge = SprayDroneStation.getBestSlottedBattery(self)
        stateText = string.format(g_i18n:getText("sdt_state_waitCharge"), charge / spec.batteryCapacity * 100)
    end
    return stateText
end

function SprayDroneStation.getDroneStateText(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return string.format(g_i18n:getText("sdt_hud_drone"), SprayDroneStation.getDroneStateName(self)),
        string.format(g_i18n:getText("sdt_hud_droneTank"), spec.droneFillLevel, spec.tankCapacity, spec.battery / spec.batteryCapacity * 100)
end

-- Baterie v nabíječce ("Baterie v nabíječce (3 ks): 100 %, 64 % (nabíjí se), …") a centrála ("Elektrocentrála: nabíjí | nafta 24,0/30 l").
function SprayDroneStation.getPowerTexts(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local parts = {}
    for _, battery in ipairs(spec.batteries) do
        if battery.slot > 0 then
            local text = string.format("%.0f %%", battery.charge / spec.batteryCapacity * 100)
            if spec.generatorRunning and battery.charge < spec.batteryCapacity then
                text = text .. " " .. g_i18n:getText("sdt_hud_charging")
            end
            table.insert(parts, text)
        end
    end
    local count = #parts
    if count == 0 then
        table.insert(parts, "-")
    end
    return string.format(g_i18n:getText("sdt_hud_power"), count, table.concat(parts, ", ")),
        string.format(g_i18n:getText("sdt_hud_generator"), g_i18n:getText(spec.generatorRunning
            and (SprayDroneStation.getNumChargingBatteries(self) > 0 and "sdt_hud_generatorOn" or "sdt_hud_generatorPump")
            or (spec.generatorEnabled and "sdt_hud_generatorOff" or "sdt_hud_generatorDisabled")),
            self:getFillUnitFillLevel(spec.dieselFillUnitIndex), self:getFillUnitCapacity(spec.dieselFillUnitIndex))
end

function SprayDroneStation:onRegisterActionEvents(isActiveForInput, isActiveForInputIgnoreSelection)
    if not self.isClient then
        return
    end
    local spec = self[SprayDroneStation.SPEC_NAME]
    self:clearActionEventsTable(spec.actionEvents)
    spec.actionStates = {}
    if isActiveForInputIgnoreSelection then
        -- centrála, vypuštění dronu, přečerpání do IBC a vypuštění koncentrátu na zem (Ctrl+I) jdou i z tahače s vybraným vlekem; ostatní jen z vleku.
        -- Vlek bez dronu: centrála a přečerpání do IBC. Plánovač se otevírá u displeje na vleku (SprayDroneLink) nebo tabletem.
        local actions = { { InputAction.SDT_TOGGLE_GENERATOR, SprayDroneStation.actionEventToggleGenerator },
            { InputAction.SDT_PUMP_TO_PALLET, SprayDroneStation.actionEventPumpToPallet },
            { InputAction.SDT_DRAIN_DRONE, SprayDroneStation.actionEventDrainDrone },
            { InputAction.TOGGLE_TIPSTATE_GROUND, SprayDroneToolbox.actionEventGroundDrain } }
        if self:getIsEntered() and spec.firstDroneCamera ~= nil then
            table.insert(actions, { InputAction.SDT_DRONE_VIEW, SprayDroneStation.actionEventDroneView })
        end
        if self:getIsEntered() and spec.hasDrone then
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

-- Pohled z dronu: kamery dronů jsou v enterable.cameras vleku (drone(?)#cameraIndex = z dronu, #outCameraIndex = na dron zvenku).
-- Klávesa C (CAMERA_SWITCH) v pohledu dronu přepíná mezi pohledem z dronu a na dron zvenku jako u traktoru, v ostatních
-- pohledech vrací vnější pohled vleku. Na drony se přepíná akcí SDT_DRONE_VIEW (nejdřív dron 1, potom 2, potom zpět na vlek),
-- vystoupení (E) vrací k vleku. Kamera dronu je pod uzlem dronu, takže za letu letí s ním.
local function getDroneCameraPair(spec, index)
    for k = 1, spec.numDrones do
        local d = spec.drones[k]
        if d.camera == index then
            return k, d.outCamera
        elseif d.outCamera == index then
            return k, d.camera
        end
    end
end

function SprayDroneStation:setActiveCameraIndex(superFunc, index)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec ~= nil and spec.firstDroneCamera ~= nil and not spec.droneCameraRequested and index >= spec.firstDroneCamera then
        local enterable = self.spec_enterable
        local current = enterable ~= nil and enterable.camIndex or nil
        local _, partner = getDroneCameraPair(spec, current)
        index = (partner ~= nil and index ~= current) and partner or 1
    end
    return superFunc(self, index)
end

function SprayDroneStation.actionEventDroneView(self, actionName, inputValue, callbackState, isAnalog)
    local spec = SprayDroneDrones.getRoot(self)
    local enterable = self.spec_enterable
    if enterable == nil or g_gui:getIsGuiVisible() then
        return
    end
    local cameras = {}
    for k = 1, spec.numDrones do
        local camera = spec.drones[k].camera
        if camera ~= nil then
            table.insert(cameras, camera)
        end
    end
    local target = cameras[1]
    local current = getDroneCameraPair(spec, enterable.camIndex)
    if current ~= nil then
        local own = spec.drones[current].camera
        for i, camera in ipairs(cameras) do
            if own == camera then
                target = cameras[i + 1] or 1
            end
        end
    end
    if target == nil then
        return
    end
    spec.droneCameraRequested = true
    self:setActiveCameraIndex(target)
    spec.droneCameraRequested = false
end

-- Akce zůstává aktivní a jen se skryje: neaktivní Alt+číslo by pustilo vanilla číslo (tempomat, klakson); do inputu se
-- sahá jen při změně (stav se pamatuje podle akce, po novém založení akcí v onRegisterActionEvents se zapomene).
local function setActionVisible(spec, action, visible, textKey)
    local event = spec.actionEvents[action]
    if event == nil then
        return
    end
    local states = spec.actionStates
    local state = states[action]
    if state == nil then
        state = {}
        states[action] = state
        g_inputBinding:setActionEventActive(event.actionEventId, true)
    end
    if state.visible ~= visible then
        state.visible = visible
        g_inputBinding:setActionEventTextVisibility(event.actionEventId, visible)
    end
    if textKey ~= nil and state.textKey ~= textKey then
        state.textKey = textKey
        g_inputBinding:setActionEventText(event.actionEventId, g_i18n:getText(textKey))
    end
end

function SprayDroneStation.updateActionEventStates(self)
    local spec = SprayDroneDrones.getRoot(self)
    local states = spec.actionStates
    setActionVisible(spec, InputAction.SDT_START_FLIGHT, SprayDroneStation.getCanStart(self))
    setActionVisible(spec, InputAction.SDT_RETURN_HOME, SprayDroneStation.getCanReturnHome(self))
    setActionVisible(spec, InputAction.SDT_TOGGLE_GENERATOR, true, spec.generatorEnabled and "sdt_action_generatorOff" or "sdt_action_generatorOn")
    setActionVisible(spec, InputAction.SDT_TOGGLE_LINES, true)
    -- vypouštění a přečerpání prochází drony a vozidla okolo: znovu se vyhodnotí nejvýš jednou za ACTION_CHECK_TIME
    -- (a hned po změně režimu přečerpávání)
    if states.checkTime == nil or g_time >= states.checkTime or states.transferMode ~= spec.transferMode then
        states.checkTime = g_time + SprayDroneStation.ACTION_CHECK_TIME
        states.transferMode = spec.transferMode
        states.canDrain = spec.transferMode == SprayDroneStation.TRANSFER_DRAIN_DRONE or SprayDroneStation.pickDrainDrone(self) ~= nil
        states.canPump = spec.transferMode == SprayDroneStation.TRANSFER_TO_PALLET
            or SprayDroneStation.getCanTransfer(self, SprayDroneStation.TRANSFER_TO_PALLET)
    end
    setActionVisible(spec, InputAction.SDT_DRAIN_DRONE, states.canDrain)
    setActionVisible(spec, InputAction.SDT_PUMP_TO_PALLET, states.canPump)
    SprayDroneToolbox.updateGroundDrainAction(self, spec)
end

function SprayDroneStation.getCanSelectField(self)
    return self:getSprayDroneIsParked() and not SprayDroneStation.getAnyMissionActive(self)
end

-- Může se spustit aspoň jeden z dronů v misi (activeDrones)?
function SprayDroneStation.getCanStart(self)
    local spec = SprayDroneDrones.getRoot(self)
    if not spec.hasDrone or spec.fieldId == 0 then
        return false
    end
    for k = 1, spec.activeDrones do
        if not spec.drones[k].missionActive then
            return true
        end
    end
    return false
end

function SprayDroneStation.getCanReturnHome(self)
    return SprayDroneStation.getAnyMissionActive(self) or not self:getSprayDroneIsParked()
end

-- Je naplánovaná aspoň jedna dávka některého dronu v misi?
function SprayDroneStation.getAnyPlanned(self)
    local spec = SprayDroneDrones.getRoot(self)
    for k = 1, spec.activeDrones do
        if spec.drones[k].numBatches > 0 then
            return true
        end
    end
    return false
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
    if not spec.hasDrone then
        return "sdt_warning_noDrone"
    end
    if #spec.batteries == 0 then
        return "sdt_warning_noBatteries"
    end
    if spec.fieldId == 0 then
        return "sdt_warning_noFieldSelected"
    end
    if not SprayDroneStation.getCanStart(self) then
        return nil
    end
    if not SprayDroneStation.getAnyPlanned(self) then
        -- důvod je u prvního dronu v misi, který nějaký má
        local info = spec.routeInfo
        for k = 1, spec.activeDrones do
            local candidate = spec.drones[k].routeInfo
            if candidate.noPath ~= nil or candidate.noFuel or candidate.tooHigh then
                info = candidate
                break
            end
        end
        if info.noPath == SprayDroneStation.NO_PATH_HOME then
            return "sdt_planner_areaHomeOutside"
        elseif info.noPath ~= nil then
            return "sdt_planner_areaNoPath"
        elseif info.noFuel then
            return "sdt_status_noFuel"
        end
        return info.tooHigh and "sdt_warning_obstacleTooHigh" or "sdt_status_fieldDone"
    end
    self:sprayDroneCommand(SprayDroneCommandEvent.START, spec.fieldId, nil, 0)
    return nil
end

function SprayDroneStation.actionEventStart(self, actionName, inputValue, callbackState, isAnalog)
    local warning = SprayDroneStation.startFlight(self)
    if warning ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(warning), 2500)
    end
end

function SprayDroneStation.actionEventReturnHome(self, actionName, inputValue, callbackState, isAnalog)
    if not SprayDroneStation.getCanReturnHome(self) then
        return
    end
    self:sprayDroneCommand(SprayDroneCommandEvent.RETURN_HOME, 0, nil, 0)
end

---------------------------------------------------------------------------------------------------
-- síť

-- Poloha dronu v síti: letí-li, jeho světová poloha a natočení.
local function writeDronePosition(self, streamId)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if streamWriteBool(streamId, not spec.isLinked) then
        local x, y, z = getWorldTranslation(spec.node)
        streamWriteFloat32(streamId, x)
        streamWriteFloat32(streamId, y)
        streamWriteFloat32(streamId, z)
        streamWriteFloat32(streamId, spec.pos.yaw)
    end
end

local function readDronePosition(self, streamId, snap)
    local spec = self[SprayDroneStation.SPEC_NAME]
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

-- Blok druhého dronu (stav, mise, náplň, baterie, efekty, poloha); píše se za blok vozidla a prvního dronu.
local function writeDroneBlock(self, streamId)
    local spec = self[SprayDroneStation.SPEC_NAME]
    streamWriteUIntN(streamId, spec.state, SprayDroneStation.STATE_NUM_BITS)
    streamWriteUIntN(streamId, spec.status, SprayDroneStation.STATUS_NUM_BITS)
    streamWriteBool(streamId, spec.missionActive)
    streamWriteFloat32(streamId, spec.droneFillLevel)
    streamWriteUIntN(streamId, spec.droneFillType, FillTypeManager.SEND_NUM_BITS)
    streamWriteFloat32(streamId, spec.battery)
    streamWriteBool(streamId, spec.sprayEffectsActive)
    streamWriteBool(streamId, spec.isPumping)
    streamWriteBool(streamId, spec.isMixing)
    streamWriteBool(streamId, spec.isSwapping)
    streamWriteBool(streamId, spec.waitingForCharge)
    streamWriteBool(streamId, spec.waitingForPower)
    streamWriteBool(streamId, spec.waitingForRelay)
    SprayDroneStation.writeBatchRelays(spec, streamId)
    writeDronePosition(self, streamId)
end

local function readDroneBlock(self, streamId, snap)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local state = streamReadUIntN(streamId, SprayDroneStation.STATE_NUM_BITS)
    spec.status = streamReadUIntN(streamId, SprayDroneStation.STATUS_NUM_BITS)
    spec.missionActive = streamReadBool(streamId)
    spec.droneFillLevel = streamReadFloat32(streamId)
    spec.droneFillType = streamReadUIntN(streamId, FillTypeManager.SEND_NUM_BITS)
    spec.battery = streamReadFloat32(streamId)
    spec.sprayEffectsActive = streamReadBool(streamId)
    spec.isPumping = streamReadBool(streamId)
    spec.isMixing = streamReadBool(streamId)
    spec.isSwapping = streamReadBool(streamId)
    spec.waitingForCharge = streamReadBool(streamId)
    spec.waitingForPower = streamReadBool(streamId)
    spec.waitingForRelay = streamReadBool(streamId)
    SprayDroneStation.readBatchRelays(spec, streamId)
    if snap then
        spec.notifiedStatus = spec.status
    end
    if state ~= spec.state then
        spec.routeDirty = true
    end
    spec.state = state
    readDronePosition(self, streamId, snap)
end

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
    streamWriteBool(streamId, spec.isMixing)
    streamWriteBool(streamId, spec.isSwapping)
    streamWriteBool(streamId, spec.waitingForCharge)
    streamWriteBool(streamId, spec.waitingForPower)
    streamWriteBool(streamId, spec.waitingForRelay)
    SprayDroneStation.writeBatchRelays(spec, streamId)
    streamWriteBool(streamId, spec.generatorRunning)
    streamWriteBool(streamId, spec.generatorEnabled)
    SprayDroneDrones.forEach(self, SprayDroneStation.syncDroneBatteryCharge)
    for _, battery in ipairs(spec.batteries) do
        streamWriteFloat32(streamId, battery.charge)
        streamWriteUIntN(streamId, battery.slot, spec.batterySlotBits)
    end
    if spec.numDrones > 1 then
        for _, battery in ipairs(spec.batteries) do
            if battery.slot == 0 then
                streamWriteUIntN(streamId, (battery.drone or 1) - 1, 1)
            end
        end
    end
    streamWriteUIntN(streamId, spec.transferMode, SprayDroneServiceEvent.NUM_BITS)
    if spec.numDrones > 1 then
        streamWriteUIntN(streamId, (spec.transferDrone or 1) - 1, 1)
    end
    SprayDroneToolbox.writeState(self, streamId)
    SprayDroneRelaySlots.writeState(self, streamId)
    writeDronePosition(self, streamId)
    if spec.numDrones > 1 then
        SprayDroneDrones.runAs(self, 2, writeDroneBlock)
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
    spec.isMixing = streamReadBool(streamId)
    spec.isSwapping = streamReadBool(streamId)
    spec.waitingForCharge = streamReadBool(streamId)
    spec.waitingForPower = streamReadBool(streamId)
    spec.waitingForRelay = streamReadBool(streamId)
    SprayDroneStation.readBatchRelays(spec, streamId)
    spec.generatorRunning = streamReadBool(streamId)
    spec.generatorEnabled = streamReadBool(streamId)
    if snap then
        spec.notifiedStatus = spec.status
    end
    for j = 1, spec.numDrones do
        spec.drones[j].droneBattery = nil
    end
    for _, battery in ipairs(spec.batteries) do
        battery.charge = streamReadFloat32(streamId)
        battery.slot = streamReadUIntN(streamId, spec.batterySlotBits)
    end
    for k, battery in ipairs(spec.batteries) do
        if battery.slot == 0 then
            battery.drone = spec.numDrones > 1 and streamReadUIntN(streamId, 1) + 1 or 1
            local droneSpec = spec.drones[battery.drone]
            if droneSpec ~= nil then
                droneSpec.droneBattery = k
            end
        end
    end
    spec.transferMode = streamReadUIntN(streamId, SprayDroneServiceEvent.NUM_BITS)
    if spec.numDrones > 1 then
        spec.transferDrone = streamReadUIntN(streamId, 1) + 1
    end
    SprayDroneToolbox.readState(self, streamId, snap)
    SprayDroneRelaySlots.readState(self, streamId)
    self:raiseActive()
    if fieldId ~= spec.fieldId then
        SprayDroneStation.markRouteDirty(self)
    end
    if state ~= spec.state then
        spec.routeDirty = true
    end
    spec.fieldId = fieldId
    spec.state = state
    readDronePosition(self, streamId, snap)
    if spec.numDrones > 1 then
        SprayDroneDrones.runAs(self, 2, readDroneBlock, snap)
    end
end

function SprayDroneStation.updateClientInterpolation(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local target = spec.netTarget
    if target == nil or spec.isLinked then
        return
    end
    local x, y, z = getWorldTranslation(spec.node)
    local f = math.min(dt * SprayDroneStation.NET_FOLLOW, 1)
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
    SprayDroneSettingsEvent.writeSettings(streamId, SprayDroneStation.getSettings(self))
    streamWriteString(streamId, SprayDroneRoute.encodeCoverage(spec.coverage))
end

function SprayDroneStation:onReadStream(streamId, connection)
    readState(self, streamId, true)
    local spec = self[SprayDroneStation.SPEC_NAME]
    for _ = 1, streamReadUInt8(streamId) do
        local fieldId, points = SprayDroneAreaEvent.readArea(streamId)
        if #points >= 3 then
            spec.flightAreas[fieldId] = points
        end
    end
    self:setSprayDroneSettings(SprayDroneSettingsEvent.readSettings(streamId), true)
    spec.coverage = SprayDroneRoute.decodeCoverage(streamReadString(streamId))
    spec.areaVersion = spec.areaVersion + 1
    SprayDroneStation.markRouteDirty(self)
end

function SprayDroneStation:onWriteUpdateStream(streamId, connection, dirtyMask)
    if not connection:getIsServer() then
        local spec = self[SprayDroneStation.SPEC_NAME]
        if streamWriteBool(streamId, bit32.band(dirtyMask, spec.dirtyFlag) ~= 0) then
            writeState(self, streamId)
        end
        if streamWriteBool(streamId, bit32.band(dirtyMask, spec.coverageDirtyFlag) ~= 0) then
            streamWriteString(streamId, SprayDroneRoute.encodeCoverage(spec.coverage))
        end
        if streamWriteBool(streamId, bit32.band(dirtyMask, spec.positionDirtyFlag) ~= 0) then
            SprayDroneDrones.forEach(self, writeDronePosition, streamId)
        end
    end
end

function SprayDroneStation:onReadUpdateStream(streamId, timestamp, connection)
    if connection:getIsServer() then
        if streamReadBool(streamId) then
            readState(self, streamId, false)
        end
        if streamReadBool(streamId) then
            local spec = self[SprayDroneStation.SPEC_NAME]
            spec.coverage = SprayDroneRoute.decodeCoverage(streamReadString(streamId))
            SprayDroneStation.markRouteDirty(self)
        end
        if streamReadBool(streamId) then
            SprayDroneDrones.forEach(self, readDronePosition, streamId, false)
        end
    end
end
