-- Zvuky vleku: elektrocentrála (naftový agregát), mixér (elektromotor s míchadlem), nalévání, vypouštění, skládání a bedna s kanystry.
--
-- Vzorky jsou vanilla šablony ze soundTemplates.xml, definice (šablona, dosah, hlasitost venku a v kabině) jsou v <sounds>
-- vozidlového XML. Každá vrstva má vlastní plynulou úroveň 0..1: po zapnutí se roztáčí (výška i hlasitost), po vypnutí
-- doběhne a teprve pak se vzorek zastaví. Přehrává se jen na klientovi; stav (spec.generatorRunning, spec.isMixing) se
-- synchronizuje ve stavu vleku.
--
-- Vrstvy:
--   generator      naftový motor agregátu (riceFieldPump), uzel generatorExhaust
--   generatorHum   hluboké elektrické hučení alternátoru (generator05), týž uzel
--   mixer          motor mixéru (mixerLoop), uzel mixerSoundNode
--   mixerLiquid    šplouchání kapaliny v mixéru (riceFieldWater), týž uzel
--   pump           čerpadlo plnění dronu na plošině (pressureWasherRun01), hraje, dokud některý dron plní (isPumping)
--   transfer       přečerpávání (vypuštění dronu do vleku, přečerpání do IBC; defaultRefuelSound), hraje při transferMode ~= 0
--   pour           nalévání z kanystru do koncentrátové nádrže / elektrocentrály (ručně přes R i nakloněným kanystrem), hraje, dokud teče
--   groundDrain    vypouštění koncentrátu na zem (Ctrl+I)
--   fold           skládání / rozkládání vleku (smyčka; od 2026-10-13 ji nemá žádný vlek, zvuky kroků jsou v animacích a v droneUnfoldStep)
--   door           roleta skříně na kanystry (Middle, Max), hraje, dokud se hýbe
-- Jednorázové zvuky (ze změny stavu): droneUnfoldStep / droneFoldStep (cvaknutí ramen a listů při rozkládání a skládání),
-- hoseAttach / hoseDetach (hydraulicHosesAttach / Detach) při vysunutí a zasunutí plnicí
-- hadice, batteryInsert (latchSmall) při výměně baterie v dronu, boxOpen / boxClose při otevření / zavření víka bedny (Mini) nebo vrat
-- skříně (Middle, Max). Voda ve vlece se napouští vanilla WaterTrailer (<waterTrailer><sounds><refill>), tam zvuk řeší hra sama. Postřik (vzorek spray) a rotory jsou u dronu
-- (SprayDroneStation.loadDroneSounds). Chybějící vzorek v XML = bez zvuku, bez hlášení.
--
-- XML (vehicle.sprayDrone.sounds, stejné atributy jako generator): <pump template="pressureWasherRun01" linkNode=... innerRadius=...
-- outerRadius=... fadeIn= fadeOut=> s <volume>, <pitch>, <lowpassGain>; totéž pro transfer, hoseAttach, hoseDetach, batteryInsert.

SprayDroneSound = {}

local DEBUG = SprayDroneDebug.ENABLED

SprayDroneSound.CHANNELS = {
    { name = "generator", driver = "generatorRunning", upTime = 2500, downTime = 3500, minPitch = 0.55, volumeExponent = 0.5 },
    { name = "generatorHum", driver = "generatorRunning", upTime = 3000, downTime = 2500, minPitch = 0.8, volumeExponent = 1 },
    { name = "mixer", driver = "isMixing", upTime = 1200, downTime = 2200, minPitch = 0.6, volumeExponent = 0.7 },
    { name = "mixerLiquid", driver = "isMixing", upTime = 2500, downTime = 1500, minPitch = 0.9, volumeExponent = 1.5 },
    { name = "pump", driver = "isPumping", upTime = 400, downTime = 700, minPitch = 0.85, volumeExponent = 1 },
    { name = "transfer", driver = "transferActive", upTime = 500, downTime = 800, minPitch = 0.9, volumeExponent = 1 },
    { name = "pour", driver = "pouring", upTime = 200, downTime = 500, minPitch = 0.95, volumeExponent = 1 },
    { name = "groundDrain", driver = "groundDrain", upTime = 300, downTime = 700, minPitch = 0.9, volumeExponent = 1 },
    { name = "fold", driver = "foldMoving", upTime = 300, downTime = 500, minPitch = 0.9, volumeExponent = 1 },
    { name = "door", driver = "doorMoving", upTime = 150, downTime = 250, minPitch = 0.95, volumeExponent = 1 },
}

-- jednorázové vzorky: přehrají se při změně pole driver (rising = false -> true, jinak true -> false) u některého dronu
SprayDroneSound.EVENTS = {
    { name = "hoseAttach", driver = "hoseConnect", rising = true },
    { name = "hoseDetach", driver = "hoseConnect", rising = false },
    { name = "batteryInsert", driver = "isSwapping", rising = true },
    { name = "boxOpen", driver = "boxesOpen", rising = true, count = true },
    { name = "boxClose", driver = "boxesOpen", rising = false, count = true },
    -- ramena a listy dronu při rozkládání / skládání: pár cvaknutí místo jedné dlouhé smyčky (stupně viz droneUnfoldStage)
    { name = "droneUnfoldStep", driver = "droneUnfoldStage", rising = true, count = true },
    { name = "droneFoldStep", driver = "droneUnfoldStage", rising = false, count = true },
}

-- Vlastní zdroje stavu (mimo pole spec dronu): funkce (vozidlo) -> bool, u událostí s count = true číslo.
SprayDroneSound.DRIVERS = {
    pouring = function(self)
        local tb = self[SprayDroneStation.SPEC_NAME].toolbox
        return tb ~= nil and tb.pouring == true
    end,
    groundDrain = function(self)
        local tb = self[SprayDroneStation.SPEC_NAME].toolbox
        return tb ~= nil and tb.groundDrain == true
    end,
    foldMoving = function(self)
        local foldable = self.spec_foldable
        return foldable ~= nil and math.abs(foldable.foldMoveDirection or 0) > 0.1
    end,
    doorMoving = function(self)
        local tb = self[SprayDroneStation.SPEC_NAME].toolbox
        if tb ~= nil then
            for _, part in ipairs(tb.parts) do
                if part.doorNode ~= nil and part.lidT > 0.001 and part.lidT < 0.999 then
                    return true
                end
            end
        end
        return false
    end,
    -- kolik z prahů rozložení (ramena, pak listy) už dron překročil; u víc dronů platí nejdál rozložený
    droneUnfoldStage = function(self)
        local root = SprayDroneDrones.getRoot(self)
        local furthest = 0
        for k = 1, root.numDrones or 1 do
            local drone = SprayDroneDrones.getSpec(self, k)
            furthest = math.max(furthest, drone ~= nil and drone.unfold or 0)
        end
        local n = 0
        for _, threshold in ipairs(SprayDroneSound.UNFOLD_STAGES) do
            if furthest >= threshold then
                n = n + 1
            end
        end
        return n
    end,
    boxesOpen = function(self)
        local tb = self[SprayDroneStation.SPEC_NAME].toolbox
        local n = 0
        if tb ~= nil then
            for _, part in ipairs(tb.parts) do
                if part.open then
                    n = n + 1
                end
            end
        end
        return n
    end,
}

SprayDroneSound.UNFOLD_STAGES = { 0.98 }   -- spec.unfold, při kterém cvakne dron (rozložen / začátek skládání); Pavel 2026-10-13: stačí jedno kliknutí

SprayDroneSound.DEBUG_FILE_POLL_TIME = 1000

-- Záznam zvuků do log.txt (Pavel 2026-10-22: hledá se zvuk, který zůstal hrát po odpojení hadice). SoundManager:playSample a stopSample
-- se obalí a zapíše se každé spuštění a zastavení vzorku, který patří vozidlu z tohoto modu (i zvuky z XML: animace, spojky, WaterTrailer,
-- podvozek): vozidlo, název a soubor vzorku, uzel, důvod a poslední akce. Důvod (stav, který zvuk řídí) předává skript přes because();
-- bez něj zůstane prázdný. Smyčky se zapisují jen při změně (start / stop), jednorázové zvuky při každém přehrání.
SprayDroneSound.DEBUG_LOG = true
SprayDroneSound.MOD_NAME = g_currentModName

function SprayDroneSound.noteAction(text)
    SprayDroneSound.lastAction = text
    SprayDroneSound.lastActionTime = g_time
    if SprayDroneSound.DEBUG_LOG then
        Logging.info("SDT akce: %s", text)
    end
end

local function describeSample(sample)
    local file = sample.filename ~= nil and Utils.getFilenameFromPath(sample.filename) or "?"
    if sample.templateName ~= nil then
        return string.format("%s [šablona %s, %s]", sample.sampleName or "?", sample.templateName, file)
    end
    return string.format("%s [%s]", sample.sampleName or "?", file)
end

-- Důvod dalšího spuštění / zastavení (platí pro nejbližší volání playSample / stopSample, pak se smaže).
function SprayDroneSound.because(text)
    SprayDroneSound.reason = text
end

local function logSample(sample, what, extra, vehicle)
    local target = vehicle or sample.modifierTargetObject
    local reason = SprayDroneSound.reason
    SprayDroneSound.reason = nil
    local node = ""
    if sample.linkNode ~= nil and entityExists(sample.linkNode) then
        node = ", uzel " .. getName(sample.linkNode)
    end
    local last = SprayDroneSound.lastAction
    Logging.info("SDT zvuk: %s %s na %s (id %s%s)%s – %s | poslední akce: %s", what, describeSample(sample),
        target.configFileNameClean or "?", tostring(target.id), node, extra or "", reason or "bez udaného důvodu",
        last ~= nil and string.format("%s, před %d ms", last, g_time - SprayDroneSound.lastActionTime) or "žádná")
end

-- Informační řádek o změně řídicího stavu (vzorek se přitom nespouští ani nezastavuje).
function SprayDroneSound.log(vehicle, sample, what, text)
    if SprayDroneSound.DEBUG_LOG then
        SprayDroneSound.reason = text
        logSample(sample, what, nil, vehicle)
    end
end

-- Vzorek patří vozidlu z tohoto modu nebo cizímu vozidlu, které je zdrojem vodní hadice (sdtSoundWatch, nastavuje SprayDroneWaterHose); modifierTargetObject
-- nastavuje loadSampleFromXML i cloneSample, vanilla specializace tam dávají vozidlo.
local function isOwnSample(sample)
    local target = sample ~= nil and sample.modifierTargetObject or nil
    return target ~= nil and type(target) == "table" and (target.customEnvironment == SprayDroneSound.MOD_NAME or target.sdtSoundWatch == true)
end

if SprayDroneSound.DEBUG_LOG and not SprayDroneSound.hooked then
    SprayDroneSound.hooked = true
    SoundManager.playSample = Utils.overwrittenFunction(SoundManager.playSample, function(self, superFunc, sample, delay, afterSample)
        if isOwnSample(sample) and (sample.loops ~= 0 or not sample.sdtLogOn) then
            sample.sdtLogOn = true
            logSample(sample, sample.loops == 0 and "START" or "JEDNORÁZOVĚ", delay ~= nil and delay > 0 and string.format(", zpoždění %d ms", delay) or nil)
        end
        return superFunc(self, sample, delay, afterSample)
    end)
    SoundManager.stopSample = Utils.overwrittenFunction(SoundManager.stopSample, function(self, superFunc, sample, delay, fadeOut)
        if isOwnSample(sample) and sample.sdtLogOn then
            sample.sdtLogOn = false
            logSample(sample, "STOP")
        end
        return superFunc(self, sample, delay, fadeOut)
    end)
end

-- Spuštění / zastavení vzorku s udaným důvodem (logují se v obalu SoundManageru).
function SprayDroneSound.play(vehicle, sample, reason, delay)
    SprayDroneSound.because(reason)
    g_soundManager:playSample(sample, delay)
    SprayDroneSound.reason = nil
end

function SprayDroneSound.stop(vehicle, sample, reason)
    SprayDroneSound.because(reason)
    g_soundManager:stopSample(sample)
    SprayDroneSound.reason = nil
end

function SprayDroneSound.registerXMLPaths(schema, key)
    for _, channel in ipairs(SprayDroneSound.CHANNELS) do
        SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", channel.name)
    end
    for _, event in ipairs(SprayDroneSound.EVENTS) do
        SoundManager.registerSampleXMLPaths(schema, key .. ".sounds", event.name)
    end
end

-- Jen klient (volá SprayDroneStation:onLoad s self.isClient).
function SprayDroneSound.loadSounds(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.sound = { channels = {} }
    for _, def in ipairs(SprayDroneSound.CHANNELS) do
        local channel = { def = def, level = 0, running = false }
        if xml:hasProperty(key .. ".sounds." .. def.name) then
            channel.sample = g_soundManager:loadSampleFromXML(xml, key .. ".sounds", def.name, self.baseDirectory, self.components, 0,
                AudioGroup.VEHICLE, self.i3dMappings, self)
        end
        if channel.sample ~= nil then
            channel.baseVolume = g_soundManager:getSampleVolumeScale(channel.sample)
        elseif SprayDroneStation.DEBUG_SOUND then
            Logging.info("SDT zvuk: vrstva '%s' se nenačetla", def.name)
        end
        table.insert(spec.sound.channels, channel)
    end
    spec.sound.events = {}
    for _, def in ipairs(SprayDroneSound.EVENTS) do
        local event = { def = def }
        if xml:hasProperty(key .. ".sounds." .. def.name) then
            event.sample = g_soundManager:loadSampleFromXML(xml, key .. ".sounds", def.name, self.baseDirectory, self.components, 1,
                AudioGroup.VEHICLE, self.i3dMappings, self)
        end
        table.insert(spec.sound.events, event)
    end
end

-- Ladění (jen s SprayDroneDebug.ENABLED): v debug.xml jde na klientovi zapnout mixér bez logiky míchání: <debug soundMixer="true"/>
function SprayDroneSound.pollDebug()
    if g_time - (SprayDroneSound.lastDebugPoll or -1e9) < SprayDroneSound.DEBUG_FILE_POLL_TIME then
        return
    end
    SprayDroneSound.lastDebugPoll = g_time
    local path = getUserProfileAppPath() .. SprayDroneDebug.FILE
    local mixer = false
    if fileExists(path) then
        local handle = loadXMLFile("sdtDebugSound", path)
        if handle ~= nil and handle ~= 0 then
            mixer = Utils.getNoNil(getXMLBool(handle, "debug#soundMixer"), false)
            delete(handle)
        end
    end
    SprayDroneSound.debugMixer = mixer
end

-- Zvuk vleku se pouští podle pole spec: u pole dronu (míchání) stačí, když platí u některého z dronů.
function SprayDroneSound.getDriver(self, driver)
    local custom = SprayDroneSound.DRIVERS[driver]
    if custom ~= nil then
        return custom(self)
    end
    local root = SprayDroneDrones.getRoot(self)
    if driver == "transferActive" then
        return root.transferMode ~= SprayDroneStation.TRANSFER_NONE
    end
    if SprayDroneDrones.DRONE[driver] then
        for k = 1, root.numDrones do
            if root.drones[k][driver] == true then
                return true
            end
        end
        return false
    end
    return root[driver] == true
end

-- Změny stavu vleku do log.txt (řádky "SDT děj:"), aby šlo k akci ("SDT akce:") dohledat, co se po ní stalo: nastoupení a vystoupení, skládání vleku,
-- stav dronu a mise, přečerpávání, míchání, bedna, centrála a pohyb hladin v nádržích (začátek a konec změny). První průchod stav jen převezme.
-- Jen klient, porovnává se každý snímek; vlek se po dobu pohybu hladiny drží vzhůru.
SprayDroneSound.STATE_NAMES = { [0] = "dron na vleku", [1] = "dron letí dávku", [2] = "dron se vrací", [3] = "servis dronu na plošině" }
SprayDroneSound.FLOW_QUIET_MS = 800
SprayDroneSound.FLOW_EPSILON = 0.01

local function constantName(prefix, value)
    for name, v in pairs(SprayDroneStation) do
        if type(name) == "string" and name:sub(1, #prefix) == prefix and v == value then
            return name:sub(#prefix + 1)
        end
    end
    return tostring(value)
end

function SprayDroneSound.getCommandName(command)
    for name, v in pairs(SprayDroneCommandEvent) do
        if type(name) == "string" and type(v) == "number" and v == command and name:find("^[A-Z_]+$") and not name:find("BITS") then
            return name
        end
    end
    return tostring(command)
end

function SprayDroneSound.getToolboxCommandName(command)
    for name, v in pairs(SprayDroneToolboxEvent) do
        if type(name) == "string" and type(v) == "number" and v == command and name:find("^[A-Z_]+$") and not name:find("BITS") then
            return name
        end
    end
    return tostring(command)
end

local function fillUnitLabel(self, spec, i)
    local role = i == spec.fillUnitIndex and "hlavní" or i == spec.dieselFillUnitIndex and "nafta" or i == SprayDroneStation.getConcentrateUnit(self) and "koncentrát" or "jednotka"
    return string.format("%s %d (%s)", role, i, g_fillTypeManager:getFillTypeNameByIndex(self:getFillUnitFillType(i)) or "?")
end

function SprayDroneSound.watch(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local root = SprayDroneDrones.getRoot(self)
    local w = spec.sdtWatch
    if w == nil then
        w = { values = {}, fills = {} }
        spec.sdtWatch = w
    end
    local name = string.format("%s (id %s)", self.configFileNameClean or "?", tostring(self.id))
    local function change(key, value, text)
        local old = w.values[key]
        if old ~= value then
            w.values[key] = value
            if old ~= nil then
                Logging.info("SDT děj: %s: %s", name, text(old, value))
            end
        end
    end
    local function onOff(on, off)
        return function(_, new)
            return new and on or off
        end
    end
    change("entered", SprayDroneStation.getIsEntered(self), onOff("hráč nastoupil do vleku", "hráč vystoupil z vleku"))
    local foldable = self.spec_foldable
    if foldable ~= nil then
        change("foldMoving", math.abs(foldable.foldMoveDirection or 0) > 0.1, function(_, moving)
            return moving and string.format("skládání / rozkládání vleku začalo (směr %d)", foldable.foldMoveDirection) or "skládání / rozkládání vleku skončilo"
        end)
        change("unfolded", self:getIsUnfolded() == true, onOff("vlek je rozložený", "vlek už není rozložený"))
    end
    change("generatorEnabled", root.generatorEnabled == true, onOff("centrála povolena", "centrála zakázána"))
    change("generatorRunning", root.generatorRunning == true, onOff("centrála běží", "centrála stojí"))
    change("fieldId", root.fieldId or 0, function(old, new)
        return string.format("vybrané pole %d -> %d", old, new)
    end)
    change("transfer", root.transferMode, function(old, new)
        return string.format("přečerpávání %s -> %s", constantName("TRANSFER_", old), constantName("TRANSFER_", new))
    end)
    for k = 1, root.numDrones or 1 do
        local d = SprayDroneDrones.getSpec(self, k)
        if d ~= nil then
            local tag = "dron " .. k
            change(tag .. "state", d.state, function(old, new)
                return string.format("%s: %s -> %s", tag, SprayDroneSound.STATE_NAMES[old] or old, SprayDroneSound.STATE_NAMES[new] or new)
            end)
            change(tag .. "mission", d.missionActive == true, onOff(tag .. ": mise začala", tag .. ": mise skončila"))
            change(tag .. "status", d.status, function(_, new)
                return string.format("%s: hlášení %s", tag, constantName("STATUS_", new))
            end)
            change(tag .. "unfold", d.unfold >= 1 and 2 or (d.unfold > 0 and 1 or 0), function(_, new)
                return string.format("%s: %s", tag, new == 2 and "rozložen" or (new == 0 and "složen" or "rozkládá / skládá se"))
            end)
            change(tag .. "pumping", d.isPumping == true, onOff(tag .. ": plnění nádrže začalo", tag .. ": plnění nádrže skončilo"))
            change(tag .. "mixing", d.isMixing == true, onOff(tag .. ": míchání začalo", tag .. ": míchání skončilo"))
            change(tag .. "swapping", d.isSwapping == true, onOff(tag .. ": výměna baterie", tag .. ": výměna baterie hotová"))
            change(tag .. "wait", (d.waitingForCharge and "nabití" or d.waitingForPower and "proud" or d.waitingForRelay and "relé" or d.waitingForClearance and "volný prostor") or "nic", function(old, new)
                return string.format("%s: čeká na %s -> %s", tag, old, new)
            end)
        end
    end
    local pumpSlot = spec.pumpSlot
    if pumpSlot ~= nil then
        change("pumpSlot", pumpSlot.occupied == true, function(_, occupied)
            return occupied and string.format("pumpa uložena na vleku (nafta %.1f l)", pumpSlot.diesel) or "pumpa vyndána z vleku"
        end)
    end
    local tb = spec.toolbox
    if tb ~= nil then
        for i, part in ipairs(tb.parts) do
            change("box" .. i, part.open == true, onOff(string.format("bedna %d otevřena", i), string.format("bedna %d zavřena", i)))
        end
        change("groundDrain", tb.groundDrain == true, onOff("vypouštění koncentrátu na zem začalo", "vypouštění koncentrátu na zem skončilo"))
        change("pouring", tb.pouring == true, onOff("nalévání z kanystru začalo", "nalévání z kanystru skončilo"))
    end
    local fillUnit = self.spec_fillUnit
    local moving = false
    if fillUnit ~= nil then
        for i, unit in ipairs(fillUnit.fillUnits) do
            local level = unit.fillLevel
            local f = w.fills[i]
            if f == nil then
                w.fills[i] = { last = level, quiet = 0 }
            else
                if math.abs(level - f.last) > SprayDroneSound.FLOW_EPSILON then
                    if not f.moving then
                        f.moving, f.start, f.startTime = true, f.last, g_time
                        Logging.info("SDT děj: %s: nádrž %s: hladina %s z %.1f l", name, fillUnitLabel(self, spec, i), level > f.last and "začala stoupat" or "začala klesat", f.last)
                    end
                    f.quiet = 0
                elseif f.moving then
                    f.quiet = f.quiet + dt
                    if f.quiet >= SprayDroneSound.FLOW_QUIET_MS then
                        f.moving = false
                        Logging.info("SDT děj: %s: nádrž %s: hladina se ustálila na %.1f l (%+.1f l za %.1f s)", name, fillUnitLabel(self, spec, i), level,
                            level - f.start, (g_time - f.startTime - f.quiet) / 1000)
                    end
                end
                f.last = level
                moving = moving or f.moving
            end
        end
    end
    if moving then
        self:raiseActive()
    end
end

-- Akce hráče, které řeší vanilla skript (skládání vleku klávesou X): doplní se řádek "SDT akce:", ať je v logu vidět, kdo a odkud je spustil.
local vanillaFold = Foldable.actionEventFold
Foldable.actionEventFold = function(self, ...)
    if SprayDroneStation ~= nil and self[SprayDroneStation.SPEC_NAME] ~= nil and SprayDroneSound.DEBUG_LOG then
        local player = g_localPlayer
        local seat = player ~= nil and player.getCurrentVehicle ~= nil and player:getCurrentVehicle() or nil
        SprayDroneSound.noteAction(string.format("klávesa skládání (X): vlek %s (id %s), hráč sedí v %s", self.configFileNameClean or "?", tostring(self.id),
            seat == nil and "nikde" or seat == self and "tomto vleku" or (seat.configFileNameClean or "jiném vozidle")))
    end
    return vanillaFold(self, ...)
end

function SprayDroneSound.updateSounds(self, dt)
    if not self.isClient then
        return
    end
    if SprayDroneSound.DEBUG_LOG then
        SprayDroneSound.watch(self, dt)
    end
    local spec = self[SprayDroneStation.SPEC_NAME]
    local sound = spec.sound
    if sound == nil then
        return
    end
    if DEBUG then
        SprayDroneSound.pollDebug()
    end
    local busy = false
    for _, channel in ipairs(sound.channels) do
        local sample = channel.sample
        if sample ~= nil then
            local def = channel.def
            local target = SprayDroneSound.getDriver(self, def.driver)
            if DEBUG and SprayDroneSound.debugMixer and def.driver == "isMixing" then
                target = true
            end
            if not channel.initialized then
                -- první průchod (po načtení, připojení do hry, probuzení vleku při nastoupení) stav jen převezme, ať se
                -- už běžící centrála neroztáčí znovu jako při startu motoru
                channel.initialized = true
                channel.level = target and 1 or 0
            end
            local step = dt / (target and def.upTime or def.downTime)
            channel.level = target and math.min(channel.level + step, 1) or math.max(channel.level - step, 0)
            if channel.target ~= target then
                channel.target = target
                if channel.running or target then
                    SprayDroneSound.log(self, sample, target and "ZAPNUTO" or "VYPNUTO",
                        string.format("řídicí stav %s = %s, úroveň %.2f", def.driver, tostring(target), channel.level))
                end
            end
            if channel.level > 0 then
                local level = channel.level
                -- rychlý nárůst otáček na začátku, pak dosedání do volnoběhu
                local pitch = def.minPitch + (1 - def.minPitch) * (1 - (1 - level) * (1 - level))
                g_soundManager:setSamplePitchOffset(sample, pitch - 1)
                g_soundManager:setSampleVolumeScale(sample, channel.baseVolume * level ^ def.volumeExponent)
                if not g_soundManager:getIsSamplePlaying(sample) then
                    if not channel.running then
                        SprayDroneSound.because(string.format("řídicí stav %s = %s", def.driver, tostring(target)))
                    end
                    g_soundManager:playSample(sample)
                    SprayDroneSound.reason = nil
                end
                channel.running = true
            elseif channel.running or g_soundManager:getIsSamplePlaying(sample) then
                SprayDroneSound.because(string.format("řídicí stav %s = %s, doběh skončil, hrálo %s", def.driver, tostring(target),
                    tostring(g_soundManager:getIsSamplePlaying(sample))))
                g_soundManager:stopSample(sample)
                SprayDroneSound.reason = nil
                channel.running = false
            end
            busy = busy or target or channel.level > 0
        end
    end
    for _, event in ipairs(sound.events) do
        local current = SprayDroneSound.getDriver(self, event.def.driver)
        -- první průchod stav jen převezme (po načtení hry ani při připojení do hry se nic nepřehrává)
        if event.value ~= nil and event.sample ~= nil then
            local fire
            if event.def.count then
                fire = event.def.rising and current > event.value or not event.def.rising and current < event.value
            else
                fire = event.value ~= current and current == event.def.rising
            end
            if fire then
                SprayDroneSound.because(string.format("%s: %s -> %s", event.def.driver, tostring(event.value), tostring(current)))
                g_soundManager:playSample(event.sample)
                SprayDroneSound.reason = nil
            end
        end
        event.value = current
    end
    -- rozjezd a doběh běží i po přenesení stavu, kdy už vlek jinak aktivní být nemusí
    if busy then
        self:raiseActive()
    end
end

function SprayDroneSound.deleteSounds(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec == nil or spec.sound == nil then
        return
    end
    local samples = {}
    for _, channel in ipairs(spec.sound.channels) do
        if channel.sample ~= nil then
            table.insert(samples, channel.sample)
        end
    end
    for _, event in ipairs(spec.sound.events) do
        if event.sample ~= nil then
            table.insert(samples, event.sample)
        end
    end
    g_soundManager:deleteSamples(samples)
    spec.sound = nil
end
