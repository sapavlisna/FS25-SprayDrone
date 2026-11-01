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

-- Záznam zvuků do log.txt (Pavel 2026-10-22: hledá se zvuk, který zůstal hrát po odpojení hadice). SoundManager:playSample a stopSample
-- se obalí a zapíše se každé spuštění a zastavení vzorku, který patří vozidlu z tohoto modu (i zvuky z XML: animace, spojky, WaterTrailer,
-- podvozek): vozidlo, název a soubor vzorku, uzel, důvod a poslední akce. Důvod (stav, který zvuk řídí) předává skript přes because();
-- bez něj zůstane prázdný. Smyčky se zapisují jen při změně (start / stop), jednorázové zvuky při každém přehrání.
SprayDroneSound.MOD_NAME = g_currentModName

function SprayDroneSound.noteAction(text)
    SprayDroneSound.lastAction = text
    SprayDroneSound.lastActionTime = g_time
end

-- Důvod dalšího spuštění / zastavení (platí pro nejbližší volání playSample / stopSample, pak se smaže).
function SprayDroneSound.because(text)
    SprayDroneSound.reason = text
end

-- Informační řádek o změně řídicího stavu (vzorek se přitom nespouští ani nezastavuje).
function SprayDroneSound.log(vehicle, sample, what, text)
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

-- Akce hráče, které řeší vanilla skript (skládání vleku klávesou X): doplní se řádek "SDT akce:", ať je v logu vidět, kdo a odkud je spustil.
local vanillaFold = Foldable.actionEventFold
Foldable.actionEventFold = function(self, ...)
    return vanillaFold(self, ...)
end

function SprayDroneSound.updateSounds(self, dt)
    if not self.isClient then
        return
    end
    local spec = self[SprayDroneStation.SPEC_NAME]
    local sound = spec.sound
    if sound == nil then
        return
    end
    local busy = false
    for _, channel in ipairs(sound.channels) do
        local sample = channel.sample
        if sample ~= nil then
            local def = channel.def
            local target = SprayDroneSound.getDriver(self, def.driver)
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
