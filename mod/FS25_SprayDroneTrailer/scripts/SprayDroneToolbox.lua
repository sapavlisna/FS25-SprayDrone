-- Bedna s kanystry na vleku (docs/DRON.md, sekce „Bedna a kanystry“): až 48 slotů po 20 l, slot buď je volný (FillType.UNKNOWN),
-- nebo drží uložený kanystr {fillType, litry}. Kanystry jsou skutečné herní objekty z obchodu
-- (objects/canister/canisterFertilizer.xml, canisterHerbicide.xml a canisterDiesel.xml, třída Pallet, fillUnit 1 = 20 l), hráč je
-- unese v rukou. Nafta je jen další druh kanystru: kterýkoli slot pojme koncentrát i naftu (vlastní kanystr nafty, i cizí z jiných
-- módů: pallet s jedinou naftovou nádrží do 25 l) a bedna s ní zachází stejně jako s koncentrátem.
--
-- Vlek může mít víc samostatných beden (`<box>` v <toolbox>, Mini: pravá sloty 1-4, levá 5-8): každá má vlastní víko, referenční bod,
-- aktivaci, dialog a otvor pro vsátí a pracuje jen se svým rozsahem slotů; bez `<box>` je jedna bedna přes všechny sloty (Middle, Max).
--
-- Obsluha se drží vanilla vzorů, bez vlastních kláves:
--  * KLIKNUTÍ (levé tlačítko myši / X, vanilla akce ACTIVATE_HANDTOOL jako u dveří, registruje ji aktivace bedny): otevře nebo zavře
--    víko. Nereaguje, když hráč něco drží nebo míří na předmět, který jde zvednout (tam klik patří rukám).
--  * AKTIVACE (vanilla „Aktivovat objekt“, R): vanilla ObjectStorageDialog jako u skladu objektů — v jednom okně řádek a počet
--    (vybrat kanystry druhu / vypustit nádrž do kanystrů). Víko ani vrata se samy nezavírají (ani po čase, ani když hráč odejde), zavře je jen hráč.
--  * VSÁTÍ: u OTEVŘENÉ bedny server jednou za ~0,5 s hledá kanystry z modu nad jejím otvorem (i ten, který hráč drží v ruce, ten mu
--    bedna vezme z rukou); je-li volný slot, kanystr smaže a jeho druh + litry zapíše do slotu. Hráč u bedny dostane notifikaci. Prázdný kanystr a
--    kanystr nad kapacitu slotu (cizí naftový do 25 l) se nevsává (prázdný zmizí sám, removeVehicleIfEmpty).
--  * NALÉVÁNÍ RUKOU: kanystr v ruce (nebo volný) nakloněný hrdlem dolů nad hrdlo koncentrátové nádrže (neckNode) nebo nádrže
--    elektrocentrály (dieselNeckNode, jen kanystr nafty) se do ní vylévá; hráč ho naklání vanilla otáčením předmětu v ruce.
--  * VYPOUŠTĚNÍ NA ZEM: vanilla akce TOGGLE_TIPSTATE_GROUND (Ctrl+I) vypouští koncentrátovou nádrž (fillUnit 3), viz updateGroundDrain.
--    Voda se do hlavní nádrže napouští z vodní plochy vanilla spec waterTrailer (R u hladiny), v tomto souboru o ní není nic.
--  * VYBRAT N kanystrů druhu z bedny vyrobí nové objekty za bednou, VYPUSTIT N kanystrů vypustí z koncentrátové nádrže
--    (fillUnit 3) N kusů po 20 l do nových kanystrů.
--
-- Všechny změny stavu dělá server (příkaz jde eventem SprayDroneToolboxEvent), stav (otevřeno, sloty, počítadlo
-- vsátí) se synchronizuje ve stavu vozidla (writeState / readState v SprayDroneStation) a sloty se ukládají do savegame. Uzly
-- bedny z i3d jsou nepovinné: bez nich funguje všechno kromě vizuálu (vzdálenost se pak měří od kořene vleku).

SprayDroneToolbox = {}

SprayDroneToolbox.modDirectory = g_currentModDirectory

SprayDroneToolbox.MAX_SLOTS = 48                  -- Middle: skříň 2 řady x 6 x 4 patra / Max: 4 řady x 6 x 2 patra (Pavel 2026-10-09)
SprayDroneToolbox.DEFAULT_SLOTS = 15
SprayDroneToolbox.DEFAULT_SPAWN_DISTANCE = 2.0
SprayDroneToolbox.SPAWN_SIDE_MIN = 0.3       -- referenční bod bedny je od osy vleku dál než to: kanystry se vyrábějí do strany bedny
SprayDroneToolbox.SPAWN_SIDE_GAP = 0.4
SprayDroneToolbox.CANISTER_UNIT = 1
SprayDroneToolbox.MIN_LITERS = 0.05
SprayDroneToolbox.INTAKE_INTERVAL_MS = 500
SprayDroneToolbox.EJECT_PROTECT_MS = 20000
SprayDroneToolbox.HAND_POUR_LYING = 0.6     -- nalévání přes R: víčko položeného kanystru nejvýš tak daleko od hrdla nádrže (m)
SprayDroneToolbox.HAND_POUR_PLAYER = 2.2    -- hráč (s kanystrem v rukou) nejvýš tak daleko od hrdla nádrže (m)
SprayDroneToolbox.POUR_INTERVAL_MS = 100
SprayDroneToolbox.POUR_UP_MAX = 0.2
SprayDroneToolbox.POUR_PLAYER_DISTANCE = 15  -- nalévání z nakloněného kanystru se hledá, jen když je hráč nejvýš tak daleko od bedny (m)
SprayDroneToolbox.POUR_WARN_MS = 4000
SprayDroneToolbox.POUR_HOLD_MS = 400         -- zvuk nalévání doběhne tolik ms po posledním přelitém litru (ať nebliká mezi tiky)
SprayDroneToolbox.PULSE_MS = 1800
SprayDroneToolbox.NOTIFY_DISTANCE = 10
SprayDroneToolbox.COMMAND_DISTANCE = 8
SprayDroneToolbox.SESSION_MAX_DISTANCE = 5
SprayDroneToolbox.SESSION_TIMEOUT_MS = 90000
SprayDroneToolbox.STORE_COUNTER_BITS = 6
SprayDroneToolbox.MAX_BOXES = 4
SprayDroneToolbox.BOX_BITS = 2

-- barva kanystru (colorScale) podle druhu; prázdný kanystr je šedý
SprayDroneToolbox.COLOR_EMPTY = { 0.7, 0.7, 0.7 }
SprayDroneToolbox.COLORS = {
    SDT_CONCENTRATE_FERTILIZER = { 0.55, 0.8, 0.15 },
    SDT_CONCENTRATE_HERBICIDE = { 0.85, 0.25, 0.08 },
    DIESEL = { 0.93, 0.70, 0.06 }
}
SprayDroneToolbox.ALLOWED = { "SDT_CONCENTRATE_FERTILIZER", "SDT_CONCENTRATE_HERBICIDE", "DIESEL" }
SprayDroneToolbox.DIESEL_UNIT_MAX_LITERS = 25

-- herní objekty kanystrů: druh -> xml (relativně k modu); poznají se podle konce object.configFileName
SprayDroneToolbox.CANISTER_FILES = {
    SDT_CONCENTRATE_FERTILIZER = "objects/canister/canisterFertilizer.xml",
    SDT_CONCENTRATE_HERBICIDE = "objects/canister/canisterHerbicide.xml",
    DIESEL = "objects/canister/canisterDiesel.xml"
}

SprayDroneToolbox.boxes = {}
SprayDroneToolbox.numBoxes = 0
SprayDroneToolbox.mission = nil
SprayDroneToolbox.session = nil

local function getSpec(self)
    return self[SprayDroneStation.SPEC_NAME]
end

local function isDiesel(fillType)
    return fillType ~= nil and FillType.DIESEL ~= nil and fillType == FillType.DIESEL
end

-- Rozsah čísel slotů: žádný slot není vyhrazený pro druh, nafta i koncentrát jdou do kteréhokoli.
-- Má-li vlek víc samostatných beden (`part`), hledá se jen v rozsahu slotů té jedné; bez `part` ve všech.
local function getSlotRange(tb, part)
    if part ~= nil then
        return part.first, part.last
    end
    return 1, tb.slots
end

local function smooth(t)
    return t * t * (3 - 2 * t)
end

local function isAllowedFillType(fillType)
    for _, name in ipairs(SprayDroneToolbox.ALLOWED) do
        if fillType ~= nil and FillType[name] == fillType then
            return true
        end
    end
    return false
end
SprayDroneToolbox.isAllowedFillType = isAllowedFillType

local function getColor(fillType)
    for name, color in pairs(SprayDroneToolbox.COLORS) do
        if FillType[name] == fillType then
            return color
        end
    end
    return SprayDroneToolbox.COLOR_EMPTY
end

---------------------------------------------------------------------------------------------------
-- schéma (vehicle XML i savegame)

function SprayDroneToolbox.registerXMLPaths(schema, key)
    key = key .. ".toolbox"
    schema:register(XMLValueType.STRING, key .. "#lidNode", "i3dMapping víka bedny (otevírá se otočením kolem lokální osy X)")
    schema:register(XMLValueType.FLOAT, key .. "#openAngle", "Otevření víka (° kolem lokální osy X uzlu, se znaménkem; zavřeno = 0)", 105)
    schema:register(XMLValueType.STRING, key .. "#doorNode", "i3dMapping pivotu rolovacích vrat (dítě = panel vrat, pivot nahoře"
        .. " uprostřed otvoru); zavřeno = scale.y 1, otevřeno = scale.y skoro 0 (panel opticky zmizí nahoru jako navinutý)")
    schema:register(XMLValueType.FLOAT, key .. "#lidTime", "Doba otevření / zavření víka / vrat (s)", 1.2)
    schema:register(XMLValueType.FLOAT, key .. "#doorTravel", "Rolovací vrata: o kolik m vyjede uzel doorNode vzhůru po otevření (bez údaje se panel místo toho zmenší scale.y)")
    schema:register(XMLValueType.FLOAT, key .. "#groundDrainRate", "Vypouštění koncentrátu na zem (Ctrl+I): rychlost (l/s)", 4)
    schema:register(XMLValueType.INT, key .. "#slots", "Počet slotů s kanystry celkem (1..48)", SprayDroneToolbox.DEFAULT_SLOTS)
    schema:register(XMLValueType.FLOAT, key .. "#slotLiters", "Kapacita jednoho kanystru (l)", 20)
    schema:register(XMLValueType.STRING, key .. "#activateNode", "i3dMapping referenčního bodu bedny (vzdálenost pro aktivaci, vsátí a místo výdeje)")
    schema:register(XMLValueType.STRING, key .. "#canisterNodePrefix", "Prefix i3dMapping kanystrů (prefix + číslo slotu)", "toolboxCanister")
    schema:register(XMLValueType.FLOAT, key .. "#activateDistance", "Nejvyšší vzdálenost hráče od bedny pro aktivaci (m)", 4)
    schema:register(XMLValueType.FLOAT, key .. "#intakeHalfWidth", "Otvor bedny pro vsátí kanystru: polovina šířky (m, po ose X vozidla od referenčního bodu)", 1.05)
    schema:register(XMLValueType.FLOAT, key .. "#intakeHalfLength", "Otvor bedny pro vsátí kanystru: polovina délky (m, po ose Z vozidla od referenčního bodu)", 0.75)
    schema:register(XMLValueType.FLOAT, key .. "#intakeBelow", "Vsátí kanystru: o kolik pod referenčním bodem ještě (m)", 0.35)
    schema:register(XMLValueType.FLOAT, key .. "#intakeAbove", "Vsátí kanystru: o kolik nad referenčním bodem ještě (m)", 0.9)
    schema:register(XMLValueType.FLOAT, key .. "#spawnDistance",
        "Vzdálenost od referenčního bodu bedny, ve které se vybraný / vypuštěný kanystr objeví (m)", SprayDroneToolbox.DEFAULT_SPAWN_DISTANCE)
    schema:register(XMLValueType.INT, key .. "#spawnSign",
        "Směr podél osy Z vozidla od referenčního bodu bedny, kam se kanystry vyrábějí: 1 dopředu, -1 dozadu (bez údaje: od středu vleku pryč)")
    schema:register(XMLValueType.STRING, key .. "#neckNode", "i3dMapping středu hrdla koncentrátové nádrže (sem se naklání kanystr)", "concentrateNeckNode")
    schema:register(XMLValueType.STRING, key .. "#dieselNeckNode", "i3dMapping hrdla nádrže elektrocentrály (sem se naklání kanystr nafty)", "dieselNeckNode")
    schema:register(XMLValueType.STRING, key .. "#dieselNeckNode2", "i3dMapping hrdla druhé elektrocentrály (jen s konfigurací dvou centrál)", "dieselNeckNode2")
    schema:register(XMLValueType.FLOAT, key .. "#pourRadius", "Nalévání rukou: nejvýš tak daleko je víčko kanystru od hrdla nádrže (m)", 0.3)
    schema:register(XMLValueType.FLOAT, key .. "#pourRate", "Nalévání rukou: rychlost vylévání z nakloněného kanystru (l/s)", 4)
    schema:register(XMLValueType.STRING, key .. ".box(?)#lidNode", "Samostatná bedna: i3dMapping jejího víka")
    schema:register(XMLValueType.STRING, key .. ".box(?)#activateNode", "Samostatná bedna: i3dMapping jejího referenčního bodu (aktivace, vsátí, místo výdeje)")
    schema:register(XMLValueType.INT, key .. ".box(?)#firstSlot", "Samostatná bedna: číslo prvního slotu", 1)
    schema:register(XMLValueType.INT, key .. ".box(?)#slotCount", "Samostatná bedna: kolik slotů drží (bez údaje: do posledního)")
    schema:register(XMLValueType.FLOAT, key .. ".box(?)#openAngle", "Samostatná bedna: otevření víka (° kolem lokální osy X uzlu, se znaménkem)", 105)
end

function SprayDroneToolbox.registerSavegamePaths(savegame, saveKey)
    saveKey = saveKey .. ".toolbox"
    savegame:register(XMLValueType.STRING, saveKey .. ".canister(?)#fillType", "Druh látky v kanystru ve slotu (UNKNOWN = volný slot)")
    savegame:register(XMLValueType.FLOAT, saveKey .. ".canister(?)#liters", "Litry v kanystru ve slotu")
    savegame:register(XMLValueType.BOOL, saveKey .. ".part(?)#open", "Bedna / skříň je otevřená (zavírá je jen hráč)")
end

---------------------------------------------------------------------------------------------------
-- načtení, uložení, smazání

local function findMapped(self, name)
    if name == nil or name == "" then
        return nil
    end
    return SprayDroneStation.getMappedNode(self, name)
end

local function setColorRec(node, r, g, b)
    -- štítek „SDT 20 l“ (<kanystr>_label) si drží barvu atlasu
    if getName(node):sub(-6) == "_label" then
        return
    end
    if getHasClassId(node, ClassIds.SHAPE) and getHasShaderParameter(node, "colorScale") then
        local _, _, _, w = getShaderParameter(node, "colorScale")
        setShaderParameter(node, "colorScale", r, g, b, w or 0, false)
    end
    for i = 0, getNumOfChildren(node) - 1 do
        setColorRec(getChildAt(node, i), r, g, b)
    end
end

function SprayDroneToolbox.load(self, savegame)
    local spec = getSpec(self)
    local xml = self.xmlFile
    local key = "vehicle.sprayDrone.toolbox"
    local tb = {}
    spec.toolbox = tb
    tb.slots = math.clamp(math.floor(xml:getValue(key .. "#slots", SprayDroneToolbox.DEFAULT_SLOTS)), 1, SprayDroneToolbox.MAX_SLOTS)
    tb.slotLiters = math.max(xml:getValue(key .. "#slotLiters", 20), 0.1)
    tb.activateDistance = math.max(xml:getValue(key .. "#activateDistance", 4), 0.5)
    tb.intakeHalfWidth = math.max(xml:getValue(key .. "#intakeHalfWidth", 1.05), 0.1)
    tb.intakeHalfLength = math.max(xml:getValue(key .. "#intakeHalfLength", 0.75), 0.1)
    tb.intakeBelow = math.max(xml:getValue(key .. "#intakeBelow", 0.35), 0)
    tb.intakeAbove = math.max(xml:getValue(key .. "#intakeAbove", 0.9), 0.1)
    tb.spawnDistance = math.max(xml:getValue(key .. "#spawnDistance", SprayDroneToolbox.DEFAULT_SPAWN_DISTANCE), 0.5)
    local spawnSign = xml:getValue(key .. "#spawnSign")
    tb.spawnSign = spawnSign ~= nil and (spawnSign < 0 and -1 or 1) or nil
    tb.pourRadius = math.max(xml:getValue(key .. "#pourRadius", 0.3), 0.05)
    tb.pourRate = math.max(xml:getValue(key .. "#pourRate", 4), 0.1)
    tb.neckNode = findMapped(self, xml:getValue(key .. "#neckNode", "concentrateNeckNode"))
    tb.mixerNode = findMapped(self, "mixerSoundNode")
    tb.dieselNeckNode =findMapped(self, xml:getValue(key .. "#dieselNeckNode", "dieselNeckNode"))
    tb.dieselNeckNode2 = findMapped(self, xml:getValue(key .. "#dieselNeckNode2", "dieselNeckNode2"))
    tb.lidTime = math.max(xml:getValue(key .. "#lidTime", 1.2), 0.05) * 1000
    tb.doorTravel = xml:getValue(key .. "#doorTravel")
    tb.groundDrainRate = math.max(xml:getValue(key .. "#groundDrainRate", 4), 0.1)
    tb.openAngle = math.rad(xml:getValue(key .. "#openAngle", 105))
    tb.lidNode = findMapped(self, xml:getValue(key .. "#lidNode"))
    tb.doorNode = findMapped(self, xml:getValue(key .. "#doorNode"))
    tb.activateNode = findMapped(self, xml:getValue(key .. "#activateNode"))
    -- Bez <box> je jedna bedna přes všechny sloty (Middle, Max); <box> dělí sloty na samostatné bedny, každá s vlastním víkem,
    -- referenčním bodem a dialogem (Mini).
    tb.parts = {}
    local function addPart(lidNode, activateNode, openAngle, first, last)
        local part = { lidNode = lidNode, activateNode = activateNode, openAngle = openAngle, first = first, last = last,
            doorNode = #tb.parts == 0 and tb.doorNode or nil, index = #tb.parts + 1, lidBase = { 0, 0, 0, 1 },
            open = false, lidT = 0, pulse = 0, spawnCounter = 0 }
        if lidNode ~= nil then
            part.lidBase = { mathEulerToQuaternion(getRotation(lidNode)) }
        end
        table.insert(tb.parts, part)
    end
    xml:iterate(key .. ".box", function(_, boxKey)
        if #tb.parts < SprayDroneToolbox.MAX_BOXES then
            local first = math.clamp(math.floor(xml:getValue(boxKey .. "#firstSlot", 1)), 1, tb.slots)
            local count = math.max(math.floor(xml:getValue(boxKey .. "#slotCount", tb.slots - first + 1)), 1)
            addPart(findMapped(self, xml:getValue(boxKey .. "#lidNode")), findMapped(self, xml:getValue(boxKey .. "#activateNode")),
                math.rad(xml:getValue(boxKey .. "#openAngle", 105)), first, math.min(first + count - 1, tb.slots))
        end
    end)
    if #tb.parts == 0 then
        addPart(tb.lidNode, tb.activateNode, tb.openAngle, 1, tb.slots)
    end
    tb.activateNode = tb.parts[1].activateNode or tb.activateNode
    for _, part in ipairs(tb.parts) do
        if part.doorNode ~= nil and tb.doorTravel ~= nil then
            part.doorTravel = tb.doorTravel
            part.doorBase = { getTranslation(part.doorNode) }
            part.doorUp = { localDirectionToLocal(self.rootNode, getParent(part.doorNode), 0, 1, 0) }
        end
    end
    local prefix = xml:getValue(key .. "#canisterNodePrefix", "toolboxCanister")
    tb.canisterNodes, tb.canisters, tb.canisterShown = {}, {}, {}
    for i = 1, tb.slots do
        tb.canisterNodes[i] = findMapped(self, prefix .. i)
        tb.canisters[i] = { fillType = FillType.UNKNOWN, liters = 0 }
    end
    -- sloty nad počet z XML nemají kanystr, tedy ani model
    for i = tb.slots + 1, SprayDroneToolbox.MAX_SLOTS do
        local node = findMapped(self, prefix .. i)
        if node ~= nil then
            setVisibility(node, false)
        end
    end
    tb.intakeTimer = 0
    tb.handPourMain = false
    tb.handPourDiesel = false
    tb.groundDrain = false
    tb.pouring = false
    tb.pourTimer = 0
    tb.pourWarnUntil = 0
    tb.spawning = {}
    tb.storeCounter = 0
    tb.storedFillType = FillType.UNKNOWN
    tb.storedPart = 1

    if savegame ~= nil and not savegame.resetVehicles then
        local saveKey = savegame.key .. "." .. SprayDroneStation.MOD_NAME .. ".sprayDroneStation.toolbox"
        savegame.xmlFile:iterate(saveKey .. ".canister", function(i, canisterKey)
            local c = tb.canisters[i]
            if c ~= nil then
                local name = savegame.xmlFile:getValue(canisterKey .. "#fillType")
                local fillType = name ~= nil and g_fillTypeManager:getFillTypeIndexByName(name) or nil
                local liters = math.clamp(savegame.xmlFile:getValue(canisterKey .. "#liters", 0), 0, tb.slotLiters)
                if fillType ~= nil and isAllowedFillType(fillType) then
                    c.fillType, c.liters = fillType, liters
                end
            end
        end)
        savegame.xmlFile:iterate(saveKey .. ".part", function(i, partKey)
            local part = tb.parts[i]
            if part ~= nil then
                part.open = savegame.xmlFile:getValue(partKey .. "#open", false)
                part.lidT = part.open and 1 or 0
            end
        end)
    end

    for _, part in ipairs(tb.parts) do
        SprayDroneToolbox.applyLid(part)
    end
    SprayDroneToolbox.updateCanisterVisuals(tb)

    if self.isClient and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        for _, part in ipairs(tb.parts) do
            part.activatable = SprayDroneToolboxActivatable.new(self, part)
            g_currentMission.activatableObjectsSystem:addActivatable(part.activatable)
        end
        tb.handPourActivatables = {}
        for _, diesel in ipairs({ false, true }) do
            local a = SprayDroneHandPourActivatable.new(self, diesel)
            table.insert(tb.handPourActivatables, a)
            g_currentMission.activatableObjectsSystem:addActivatable(a)
        end
    end
    SprayDroneToolbox.addBox(self)
end

function SprayDroneToolbox.save(self, xmlFile, key)
    local tb = getSpec(self).toolbox
    if tb == nil then
        return
    end
    key = key .. ".toolbox"
    for i = 1, tb.slots do
        local c = tb.canisters[i]
        local canisterKey = string.format("%s.canister(%d)", key, i - 1)
        xmlFile:setValue(canisterKey .. "#fillType", g_fillTypeManager:getFillTypeNameByIndex(c.fillType) or "UNKNOWN")
        xmlFile:setValue(canisterKey .. "#liters", c.liters)
    end
    for i, part in ipairs(tb.parts) do
        xmlFile:setValue(string.format("%s.part(%d)#open", key, i - 1), part.open)
    end
end

function SprayDroneToolbox.delete(self)
    local spec = getSpec(self)
    local tb = spec ~= nil and spec.toolbox or nil
    if tb == nil then
        return
    end
    if g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        for _, part in ipairs(tb.parts) do
            if part.activatable ~= nil then
                g_currentMission.activatableObjectsSystem:removeActivatable(part.activatable)
            end
            part.activatable = nil
        end
        for _, a in ipairs(tb.handPourActivatables or {}) do
            g_currentMission.activatableObjectsSystem:removeActivatable(a)
        end
    end
    tb.handPourActivatables = nil
    if SprayDroneToolbox.session ~= nil and SprayDroneToolbox.session.vehicle == self then
        SprayDroneToolbox.releaseLocal()
    end
    SprayDroneToolbox.removeBox(self)
end

---------------------------------------------------------------------------------------------------
-- síť (voláno z writeState / readState v SprayDroneStation; pořadí a počty musí sedět)

function SprayDroneToolbox.writeState(self, streamId)
    local tb = getSpec(self).toolbox
    for _, part in ipairs(tb.parts) do
        streamWriteBool(streamId, part.open)
    end
    streamWriteBool(streamId, tb.handPourMain)
    streamWriteBool(streamId, tb.handPourDiesel)
    streamWriteBool(streamId, tb.groundDrain)
    streamWriteBool(streamId, tb.pouring)
    streamWriteUIntN(streamId, tb.storeCounter, SprayDroneToolbox.STORE_COUNTER_BITS)
    streamWriteUIntN(streamId, tb.storedFillType, FillTypeManager.SEND_NUM_BITS)
    streamWriteUIntN(streamId, tb.storedPart - 1, SprayDroneToolbox.BOX_BITS)
    for i = 1, tb.slots do
        local c = tb.canisters[i]
        streamWriteUIntN(streamId, c.fillType, FillTypeManager.SEND_NUM_BITS)
        streamWriteFloat32(streamId, c.liters)
    end
end

function SprayDroneToolbox.readState(self, streamId, snap)
    local tb = getSpec(self).toolbox
    for _, part in ipairs(tb.parts) do
        part.open = streamReadBool(streamId)
    end
    tb.handPourMain = streamReadBool(streamId)
    tb.handPourDiesel = streamReadBool(streamId)
    tb.groundDrain = streamReadBool(streamId)
    tb.pouring = streamReadBool(streamId)
    local counter = streamReadUIntN(streamId, SprayDroneToolbox.STORE_COUNTER_BITS)
    local storedFillType = streamReadUIntN(streamId, FillTypeManager.SEND_NUM_BITS)
    local storedPart = streamReadUIntN(streamId, SprayDroneToolbox.BOX_BITS) + 1
    for i = 1, tb.slots do
        local c = tb.canisters[i]
        c.fillType = streamReadUIntN(streamId, FillTypeManager.SEND_NUM_BITS)
        c.liters = streamReadFloat32(streamId)
    end
    local changed = counter ~= tb.storeCounter
    tb.storeCounter, tb.storedFillType, tb.storedPart = counter, storedFillType, storedPart
    if snap then
        for _, part in ipairs(tb.parts) do
            part.lidT = part.open and 1 or 0
            SprayDroneToolbox.applyLid(part)
        end
    elseif changed then
        SprayDroneToolbox.onStored(self, storedFillType, tb.parts[storedPart])
    end
end

local function raiseDirty(self)
    self:raiseDirtyFlags(getSpec(self).dirtyFlag)
end

---------------------------------------------------------------------------------------------------
-- registr beden a společná aktualizace (updateable, aby šlo i o vozidlo, které zrovna „spí“)

function SprayDroneToolbox.addBox(self)
    if SprayDroneToolbox.mission ~= g_currentMission then
        SprayDroneToolbox.mission = g_currentMission
        SprayDroneToolbox.boxes = {}
        SprayDroneToolbox.numBoxes = 0
        SprayDroneToolbox.releaseLocal()
    end
    if SprayDroneToolbox.boxes[self] then
        return
    end
    SprayDroneToolbox.boxes[self] = true
    SprayDroneToolbox.numBoxes = SprayDroneToolbox.numBoxes + 1
    if SprayDroneToolbox.numBoxes == 1 then
        g_currentMission:addUpdateable(SprayDroneToolbox.controller)
    end
end

function SprayDroneToolbox.removeBox(self)
    if not SprayDroneToolbox.boxes[self] then
        return
    end
    SprayDroneToolbox.boxes[self] = nil
    SprayDroneToolbox.numBoxes = SprayDroneToolbox.numBoxes - 1
    if SprayDroneToolbox.numBoxes <= 0 then
        SprayDroneToolbox.numBoxes = 0
        if g_currentMission ~= nil then
            g_currentMission:removeUpdateable(SprayDroneToolbox.controller)
        end
    end
end

SprayDroneToolbox.controller = {}
function SprayDroneToolbox.controller:update(dt)
    for vehicle in pairs(SprayDroneToolbox.boxes) do
        if vehicle.isDeleted then
            SprayDroneToolbox.removeBox(vehicle)
        else
            SprayDroneToolbox.updateBox(vehicle, dt)
        end
    end
    SprayDroneToolbox.updateSession(dt)
end

function SprayDroneToolbox.updateBox(self, dt)
    local spec = getSpec(self)
    local tb = spec ~= nil and spec.toolbox or nil
    if tb == nil then
        return
    end
    if self.isServer then
        SprayDroneToolbox.updateIntake(self, dt)
        SprayDroneToolbox.updatePour(self, dt)
        SprayDroneToolbox.updateHandPour(self, dt)
        SprayDroneToolbox.updateGroundDrain(self, dt)
    end
    if self.isClient then
        SprayDroneToolbox.updatePourHint(self, dt)
        for _, part in ipairs(tb.parts) do
            if part.pulse > 0 then
                part.pulse = math.max(part.pulse - dt, 0)
            end
            local target = (part.open or part.pulse > 0) and 1 or 0
            if part.lidT ~= target then
                local step = dt / tb.lidTime
                part.lidT = part.lidT < target and math.min(part.lidT + step, target) or math.max(part.lidT - step, target)
                SprayDroneToolbox.applyLid(part)
                self:raiseActive()
            end
        end
        if tb.pouring or tb.groundDrain then
            self:raiseActive() -- zvuky (SprayDroneSound) se počítají v onUpdate vleku, ten spící vlek nevolá
        end
        SprayDroneToolbox.updateCanisterVisuals(tb)
    end
end

SprayDroneToolbox.DOOR_OPEN_SCALE = 0.02   -- vrata zavřená = scale.y 1, otevřená = tahle hodnota (ne přesně 0, ať nemizí normály)
SprayDroneToolbox.DOOR_ROLLED_SCALE = 0.2 -- s doorTravel: panel 1,39 m vyjede o doorTravel nahoru a zmenší se na tuhle část, aby se vešel do pouzdra nad otvorem (0,34 m)

-- Víko: otočení kolem lokální osy X uzlu o openAngle (se znaménkem z XML), zavřeno = původní natočení.
-- Vrata (doorNode): s doorTravel z XML uzel vyjede vzhůru o doorTravel m a zároveň se zmenší na DOOR_ROLLED_SCALE (zmizí v pouzdru roletové schránky nad otvorem), jinak je
-- panel dítě pivotu nahoře uprostřed otvoru (viz build_trailer_middle.build_cabinet_door) a scale.y mezi 1 (zavřeno) a
-- DOOR_OPEN_SCALE (otevřeno) ho opticky navine vzhůru. Žádná rotace, nic nezavazí pevnému žebříku na boku (Pavel 2026-10-09).
function SprayDroneToolbox.applyLid(part)
    if part.lidNode ~= nil then
        local half = part.openAngle * smooth(part.lidT) * 0.5
        local b = part.lidBase
        local x, y, z, w = MathUtil.quaternionMult(b[1], b[2], b[3], b[4], math.sin(half), 0, 0, math.cos(half))
        setQuaternion(part.lidNode, x, y, z, w)
    end
    if part.doorNode ~= nil then
        local t = smooth(part.lidT)
        if part.doorTravel ~= nil then
            local b, u, travel = part.doorBase, part.doorUp, part.doorTravel * t
            setTranslation(part.doorNode, b[1] + u[1] * travel, b[2] + u[2] * travel, b[3] + u[3] * travel)
            setScale(part.doorNode, 1, 1 + (SprayDroneToolbox.DOOR_ROLLED_SCALE - 1) * t, 1)
        else
            setScale(part.doorNode, 1, 1 + (SprayDroneToolbox.DOOR_OPEN_SCALE - 1) * t, 1)
        end
    end
end

-- Kanystr je vidět jen ve slotu, který ho drží (volný slot je prázdná přihrádka); barva podle druhu, prázdný je šedý.
-- Barvu jde přepnout jen tam, kde model uzly má.
function SprayDroneToolbox.updateCanisterVisuals(tb)
    for i = 1, tb.slots do
        local node = tb.canisterNodes[i]
        local c = tb.canisters[i]
        local key = 0
        if c.fillType ~= FillType.UNKNOWN then
            key = c.fillType * 2 + (c.liters > 0.001 and 1 or 0) + 1
        end
        if node ~= nil and tb.canisterShown[i] ~= key then
            tb.canisterShown[i] = key
            if key == 0 then
                setVisibility(node, false)
            else
                local color = c.liters > 0.001 and getColor(c.fillType) or SprayDroneToolbox.COLOR_EMPTY
                setColorRec(node, color[1], color[2], color[3])
                setVisibility(node, true)
            end
        end
    end
end

---------------------------------------------------------------------------------------------------
-- pomocné dotazy

function SprayDroneToolbox.getRefNode(self, part)
    local tb = getSpec(self).toolbox
    return (part ~= nil and part.activateNode) or tb.activateNode or self.rootNode
end

function SprayDroneToolbox.getConcentrateUnit(self)
    return SprayDroneStation.getConcentrateUnit(self)
end

-- Poloha hráče (z vozidla se bere kořen vozidla); nil = nejde zjistit.
local function getPlayerPosition(player)
    if player == nil then
        return nil
    end
    local vehicle = player.getCurrentVehicle ~= nil and player:getCurrentVehicle() or nil
    if vehicle ~= nil and vehicle.rootNode ~= nil then
        return getWorldTranslation(vehicle.rootNode)
    end
    if player.getPosition ~= nil then
        local x, y, z = player:getPosition()
        if x ~= nil then
            return x, y, z
        end
    end
    if player.rootNode ~= nil and entityExists(player.rootNode) then
        return getWorldTranslation(player.rootNode)
    end
    return nil
end

-- Vzdálenost hráče od referenčního bodu bedny `part` (bez ní od nejbližší z beden); nil = hráčovu polohu nejde zjistit.
function SprayDroneToolbox.getDistanceOfPlayer(self, player, part)
    local px, py, pz = getPlayerPosition(player)
    if px == nil then
        return nil
    end
    local best = math.huge
    for _, p in ipairs(part ~= nil and { part } or getSpec(self).toolbox.parts) do
        local nx, ny, nz = getWorldTranslation(SprayDroneToolbox.getRefNode(self, p))
        best = math.min(best, MathUtil.vector3Length(px - nx, py - ny, pz - nz))
    end
    return best
end

-- Vzdálenost místního hráče od bedny `part` (bez ní od nejbližší; bez hráče nekonečno).
function SprayDroneToolbox.getPlayerDistance(self, part)
    if g_localPlayer == nil then
        return math.huge
    end
    return SprayDroneToolbox.getDistanceOfPlayer(self, g_localPlayer, part) or math.huge
end

local function getPlayers()
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    return system ~= nil and system.players or {}
end

local function getFillTypeTitle(fillType)
    return g_fillTypeManager:getFillTypeTitleByIndex(fillType) or "?"
end

local function isAlive(self)
    return self ~= nil and not self.isDeleted and self.rootNode ~= nil and entityExists(self.rootNode)
end

local function isPresent(c)
    return c.fillType ~= FillType.UNKNOWN
end

-- První slot bez kanystru (slot, ze kterého se právě vyrábí objekt, se za volný nepočítá).
function SprayDroneToolbox.getFreeSlot(tb, part)
    local first, last = getSlotRange(tb, part)
    for i = first, last do
        if not isPresent(tb.canisters[i]) and not tb.spawning[i] then
            return i
        end
    end
    return nil
end

local function countFreeSlots(tb, part)
    local n = 0
    local first, last = getSlotRange(tb, part)
    for i = first, last do
        if not isPresent(tb.canisters[i]) and not tb.spawning[i] then
            n = n + 1
        end
    end
    return n
end

-- Až `count` slotů s kanystrem daného druhu (od nejnižšího čísla), bez slotů, ze kterých se právě vyrábí objekt; s
-- `needLiters` jen neprázdné. Vrací seznam čísel slotů a součet litrů.
function SprayDroneToolbox.pickSlots(tb, fillType, count, needLiters, part)
    local slots, liters = {}, 0
    local first, last = getSlotRange(tb, part)
    for i = first, last do
        local c = tb.canisters[i]
        if #slots >= count then
            break
        end
        if c.fillType == fillType and not tb.spawning[i] and (not needLiters or c.liters > 0.001) then
            table.insert(slots, i)
            liters = liters + c.liters
        end
    end
    return slots, liters
end

-- Skupiny uložených kanystrů podle druhu: { fillType, count, liters } (jen druhy, které v bedně jsou).
function SprayDroneToolbox.getGroups(tb, part)
    local groups = {}
    for _, name in ipairs(SprayDroneToolbox.ALLOWED) do
        local fillType = FillType[name]
        if fillType ~= nil then
            local slots, liters = SprayDroneToolbox.pickSlots(tb, fillType, tb.slots, false, part)
            if #slots > 0 then
                table.insert(groups, { fillType = fillType, count = #slots, liters = liters })
            end
        end
    end
    return groups
end

---------------------------------------------------------------------------------------------------
-- kanystry jako herní objekty

-- Druh (fillType) kanystru, když je objekt kanystr z modu (podle konce configFileName), jinak nil.
function SprayDroneToolbox.getCanisterKind(object)
    local name = object ~= nil and object.configFileName or nil
    if type(name) ~= "string" then
        return nil
    end
    name = string.lower(name)
    for kindName, file in pairs(SprayDroneToolbox.CANISTER_FILES) do
        local tail = string.lower(string.match(file, "[^/]+$"))
        if string.sub(name, -#tail) == tail then
            return FillType[kindName]
        end
    end
    -- cizí kanystr nafty z jiného módu: pallet s jedinou naftovou nádrží do DIESEL_UNIT_MAX_LITERS
    if FillType.DIESEL ~= nil and object.spec_pallet ~= nil and object.spec_fillUnit ~= nil and object.getFillUnitCapacity ~= nil then
        local units = object.spec_fillUnit.fillUnits
        local unit = units ~= nil and units[SprayDroneToolbox.CANISTER_UNIT] or nil
        local capacity = object:getFillUnitCapacity(SprayDroneToolbox.CANISTER_UNIT)
        if unit ~= nil and #units == 1 and capacity ~= nil and capacity > 0 and capacity <= SprayDroneToolbox.DIESEL_UNIT_MAX_LITERS
            and unit.supportedFillTypes ~= nil then
            local onlyDiesel = false
            for fillType, supported in pairs(unit.supportedFillTypes) do
                if supported then
                    onlyDiesel = fillType == FillType.DIESEL
                    if not onlyDiesel then
                        break
                    end
                end
            end
            if onlyDiesel then
                return FillType.DIESEL
            end
        end
    end
    return nil
end

-- Cesta k xml kanystru daného druhu, jen když je v obchodě (VehicleLoadingData:setFilename hledá storeItem podle xml).
-- nil = kanystr tohoto druhu nejde vyrobit (xml v modu chybí nebo není v modDesc <storeItems>).
function SprayDroneToolbox.getCanisterFilename(fillType)
    if g_storeManager == nil then
        return nil
    end
    for kindName, file in pairs(SprayDroneToolbox.CANISTER_FILES) do
        if FillType[kindName] == fillType then
            local path = (SprayDroneToolbox.modDirectory or "") .. file
            if g_storeManager:getItemByXMLFilename(path) ~= nil then
                return path
            end
            local tail = string.lower(file)
            for key, item in pairs(g_storeManager.xmlFilenameToItem or {}) do
                if string.sub(key, -#tail) == tail then
                    return item.xmlFilename or key
                end
            end
        end
    end
    return nil
end

-- Uzly (kořeny komponent), které právě drží hráči v rukou: uzel -> hráč (HandToolHands.spec_hands.heldItemNode; server je
-- zná ze HandsPickUpObjectEvent).
local function getHeldNodes()
    local held = {}
    for _, player in ipairs(getPlayers()) do
        local hands = player.hands
        local handsSpec = hands ~= nil and hands.spec_hands or nil
        if handsSpec ~= nil and handsSpec.heldItemNode ~= nil then
            held[handsSpec.heldItemNode] = player
        end
    end
    return held
end

-- Hráč, který kanystr drží v rukou (nebo nil).
local function getHolder(v, held)
    if held[v.rootNode] then
        return held[v.rootNode]
    end
    for _, component in ipairs(v.components or {}) do
        if held[component.node] then
            return held[component.node]
        end
    end
    return nil
end

-- Hráč kanystr pustí z rukou (na všech klientech, vanilla HandsThrowObjectEvent).
local function dropFromHands(player)
    local hands = player ~= nil and player.hands or nil
    if hands ~= nil and hands.dropHeldItem ~= nil then
        hands:dropHeldItem()
    end
end

-- Kanystr nese / drží jiný objekt (dynamické připnutí, upínací pásy).
local function isCanisterMounted(v)
    if v.getDynamicMountObject ~= nil and v:getDynamicMountObject() ~= nil then
        return true
    end
    if v.dynamicMountObject ~= nil or v.tensionMountObject ~= nil then
        return true
    end
    if v.dynamicMountType ~= nil and MountableObject ~= nil and v.dynamicMountType ~= MountableObject.MOUNT_TYPE_NONE then
        return true
    end
    return false
end

-- Je světový bod v otvoru bedny? Otvor je kvádr nad referenčním bodem bedny v souřadnicích vozidla (intakeHalfWidth po X,
-- intakeHalfLength po Z, od intakeBelow pod bodem do intakeAbove nad ním). Vrací i vzdálenost od referenčního bodu.
function SprayDroneToolbox.getIntakeDistance(self, x, y, z, part)
    local tb = getSpec(self).toolbox
    local root = self.rootNode
    local lx, ly, lz = worldToLocal(root, x, y, z)
    local rx, ry, rz = localToLocal(SprayDroneToolbox.getRefNode(self, part), root, 0, 0, 0)
    local dx, dy, dz = lx - rx, ly - ry, lz - rz
    local hw, hl, below, above = tb.intakeHalfWidth, tb.intakeHalfLength, tb.intakeBelow, tb.intakeAbove
    if math.abs(dx) <= hw and math.abs(dz) <= hl and dy >= -below and dy <= above then
        return MathUtil.vector3Length(dx, dy, dz)
    end
    return nil
end

local function getVehicles()
    return g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
end

-- Je `v` žijící kanystr z modu, ke kterému má farma přístup? Vrací druh látky nebo nil.
local function getUsableCanisterKind(self, v)
    if v == self or v.spec_pallet == nil or v.spec_fillUnit == nil or v.isDeleted or v.rootNode == nil then
        return nil
    end
    local kind = SprayDroneToolbox.getCanisterKind(v)
    if kind ~= nil and entityExists(v.rootNode) and g_currentMission.accessHandler:canFarmAccess(self:getOwnerFarmId(), v) then
        return kind
    end
    return nil
end

-- Kanystry z modu v otvoru bedny, i ty v rukou hráče (těm je bedna vezme). Vyrobený kanystr se nevsaje, dokud ho hráč
-- nevezme do ruky (nebo neleží EJECT_PROTECT_MS mimo otvor), jinak by odskočený kanystr skočil zpět. Vrací seznam { vehicle, kind, liters, holder, part }
-- od nejbližšího; `part` je bedna, v jejímž otvoru kanystr je (otvory beden se nepřekrývají).
function SprayDroneToolbox.findIntakeCanisters(self)
    local result = {}
    local held = getHeldNodes()
    for _, v in ipairs(getVehicles()) do
        local kind = getUsableCanisterKind(self, v)
        if kind ~= nil then
            local x, y, z = getWorldTranslation(v.rootNode)
            local distance, part = nil, nil
            for _, p in ipairs(getSpec(self).toolbox.parts) do
                local d = SprayDroneToolbox.getIntakeDistance(self, x, y, z, p)
                if d ~= nil and (distance == nil or d < distance) then
                    distance, part = d, p
                end
            end
            local holder = getHolder(v, held)
            if v.sdtEjectTime ~= nil and (holder ~= nil or (distance == nil and g_time - v.sdtEjectTime > SprayDroneToolbox.EJECT_PROTECT_MS)) then
                v.sdtEjectTime = nil
            end
            if distance ~= nil and v.sdtEjectTime == nil and not isCanisterMounted(v) then
                table.insert(result, { vehicle = v, kind = kind, liters = v:getFillUnitFillLevel(SprayDroneToolbox.CANISTER_UNIT) or 0,
                    distance = distance, holder = holder, part = part })
            end
        end
    end
    table.sort(result, function(a, b) return a.distance < b.distance end)
    return result
end

-- Místo za vlekem, kam se vyrobí n-tý kanystr (řada po šesti, každá další řada o kus dál, všechno mimo otvor bedny). Směr podél
-- osy Z vozidla dává spawnSign z XML, bez něj se jde od referenčního bodu bedny pryč od středu vleku. Leží-li bod bedny u boku
-- vleku (Mini), řada se rozbíhá ještě dál do strany, aby nezasáhla vysunutou desku. Vrací x, y, z, natočení kolem Y.
function SprayDroneToolbox.getSpawnPosition(self, n, part)
    local tb = getSpec(self).toolbox
    local root = self.rootNode
    local lx, _, lz = localToLocal(SprayDroneToolbox.getRefNode(self, part), root, 0, 0, 0)
    local sign = tb.spawnSign or (lz < 0 and -1 or 1)
    local column = n % 6
    local row = math.floor(n / 6) % 3
    local lateral, along = (column - 2.5) * 0.4, sign * (tb.spawnDistance + row * 0.4)
    if math.abs(lx) > SprayDroneToolbox.SPAWN_SIDE_MIN then
        lateral = (lx < 0 and -1 or 1) * (SprayDroneToolbox.SPAWN_SIDE_GAP + column * 0.4)
    end
    local x, _, z = localToWorld(root, lx + lateral, 0, lz + along)
    local y = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.2
    local dx, _, dz = localDirectionToWorld(root, 0, 0, 1)
    return x, y, z, MathUtil.getYRotationFromDirection(dx, dz)
end

-- Místo pro n-tý kanystr z vypuštěné nádrže (Ctrl+I): na zemi vedle kol, na boku vleku s mixérem, řada podél vleku kolem
-- mixéru (po šesti, další řada dál od boku). Bez uzlu mixéru jako getSpawnPosition.
function SprayDroneToolbox.getGroundSpawnPosition(self, n, part)
    local tb = getSpec(self).toolbox
    if tb.mixerNode == nil then
        return SprayDroneToolbox.getSpawnPosition(self, n, part)
    end
    local root = self.rootNode
    local mx, _, mz = localToLocal(tb.mixerNode, root, 0, 0, 0)
    local side = mx < 0 and -1 or 1
    local halfWidth = (self.size ~= nil and self.size.width or 2) / 2
    local column = n % 6
    local row = math.floor(n / 6) % 3
    local lx = side * (halfWidth + SprayDroneToolbox.SPAWN_SIDE_GAP + row * 0.4)
    local lz = mz + (column - 2.5) * 0.4
    local x, _, z = localToWorld(root, lx, 0, lz)
    local y = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.2
    local dx, _, dz = localDirectionToWorld(root, 0, 0, 1)
    return x, y, z, MathUtil.getYRotationFromDirection(dx, dz)
end

-- Vyrobí nový objekt kanystru daného druhu s obsahem `liters` před bednou (jen server). Načtení je asynchronní: vrací true,
-- když se začalo, a pak callback(success, vehicle) přijde vždy (i při chybě načtení). Když se ani nezačalo, vrací
-- false + klíč textu s důvodem a callback se nevolá. Vyrobený kanystr se hned nevsaje zpět (sdtEjectTime). `part` = bedna, před
-- kterou se kanystr objeví (bez ní první).
function SprayDroneToolbox.spawnCanister(self, fillType, liters, callback, at, part)
    local tb = getSpec(self).toolbox
    part = part or tb.parts[1]
    if not g_currentMission:getIsServer() then
        return false, "sdt_toolbox_spawnFailed"
    end
    local filename = SprayDroneToolbox.getCanisterFilename(fillType)
    if filename == nil then
        Logging.warning("SDT: kanystr druhu %s nejde vyrobit (chybí xml nebo storeItem v modu)", getFillTypeTitle(fillType))
        return false, "sdt_toolbox_noCanisterItem"
    end
    local slotSystem = g_currentMission.slotSystem
    if slotSystem ~= nil and SlotSystem ~= nil and SlotSystem.LIMITED_OBJECT_PALLET ~= nil
        and not slotSystem:getCanAddLimitedObjects(SlotSystem.LIMITED_OBJECT_PALLET, 1) then
        Logging.warning("SDT: kanystr nejde vyrobit, je dosažen limit palet a objektů")
        return false, "sdt_toolbox_spawnLimit"
    end
    local data = VehicleLoadingData.new()
    data:setFilename(filename)
    if not data.isValid then
        return false, "sdt_toolbox_noCanisterItem"
    end
    local x, y, z, ry
    if at ~= nil then
        x, y, z, ry = at[1], at[2], at[3], at[4]
    else
        x, y, z, ry = SprayDroneToolbox.getSpawnPosition(self, part.spawnCounter, part)
        part.spawnCounter = part.spawnCounter + 1
    end
    local farmId = self:getOwnerFarmId()
    data:setPosition(x, y, z)
    data:setRotation(0, ry, 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(farmId)
    data:setCustomParameter("spawnEmpty", true)
    data:load(function(_, vehicles, state)
        local vehicle = vehicles ~= nil and vehicles[1] or nil
        if state ~= VehicleLoadingState.OK or vehicle == nil then
            Logging.warning("SDT: kanystr se nepodařilo načíst (%s)", tostring(filename))
            for _, v in ipairs(vehicles or {}) do
                v:delete()
            end
            callback(false)
            return
        end
        vehicle.sdtEjectTime = g_time
        if liters > 0.001 then
            local added = vehicle:addFillUnitFillLevel(farmId, SprayDroneToolbox.CANISTER_UNIT, liters, fillType, ToolType.UNDEFINED, nil)
            if added == nil or added < liters - 0.01 then
                Logging.warning("SDT: do nového kanystru se vešlo %.2f z %.2f l", added or 0, liters)
            end
        end
        callback(true, vehicle)
    end)
    return true
end

-- Klíč textu s důvodem, proč se nádrž nedá plnit danou látkou (nil = jde).
local function getTankReason(self, fillType)
    if isDiesel(fillType) then
        local unit = getSpec(self).dieselFillUnitIndex
        if unit == nil or not self:getFillUnitExists(unit) then
            return "sdt_toolbox_genNoTank"
        end
        if self:getFillUnitFreeCapacity(unit) <= 0.001 then
            return "sdt_toolbox_genFull"
        end
        return nil
    end
    local unit = SprayDroneToolbox.getConcentrateUnit(self)
    if unit == nil then
        return "sdt_toolbox_noTank"
    end
    local level = self:getFillUnitFillLevel(unit)
    if level > 0.001 and self:getFillUnitFillType(unit) ~= fillType then
        return "sdt_toolbox_tankMismatch"
    end
    if not self:getFillUnitSupportsFillType(unit, fillType) then
        return "sdt_toolbox_tankRejects"
    end
    if self:getFillUnitFreeCapacity(unit) <= 0.001 then
        return "sdt_toolbox_tankFull"
    end
    return nil
end

-- Klíč textu s důvodem, proč akce nejde (nil = jde). Volá se na klientu (hláška) i na serveru (rozhodnutí). `fillType` je druh
-- kanystrů (TAKE); pro DRAIN se nepoužívá.
function SprayDroneToolbox.getBlockReason(self, command, fillType, part)
    local tb = getSpec(self).toolbox
    if command == SprayDroneToolboxEvent.TAKE then
        if not isAllowedFillType(fillType) or #SprayDroneToolbox.pickSlots(tb, fillType, 1, false, part) == 0 then
            return "sdt_toolbox_slotFree"
        end
        if SprayDroneToolbox.getCanisterFilename(fillType) == nil then
            return "sdt_toolbox_noCanisterItem"
        end
    elseif command == SprayDroneToolboxEvent.DRAIN then
        local unit = SprayDroneToolbox.getConcentrateUnit(self)
        if unit == nil then
            return "sdt_toolbox_noTank"
        end
        local level = self:getFillUnitFillLevel(unit)
        local tankType = self:getFillUnitFillType(unit)
        if level <= SprayDroneToolbox.MIN_LITERS then
            return "sdt_toolbox_tankEmpty"
        end
        if not isAllowedFillType(tankType) then
            return "sdt_toolbox_typeNotAllowed"
        end
        local chunks = math.ceil((level - SprayDroneToolbox.MIN_LITERS) / tb.slotLiters)
        if chunks > countFreeSlots(tb, part) and SprayDroneToolbox.getCanisterFilename(tankType) == nil then
            return "sdt_toolbox_noCanisterItem"
        end
    end
    return nil
end

---------------------------------------------------------------------------------------------------
-- příkazy a automatika (server)

function SprayDroneToolbox.setOpen(self, open, part)
    part = part or getSpec(self).toolbox.parts[1]
    if part.open == open then
        return
    end
    part.open = open
    raiseDirty(self)
end

-- Efekt vsátí kanystru na klientu (server na hostiteli ho volá přímo, ostatní klienti podle počítadla ve stavu vozidla):
-- hráč poblíž dostane vanilla notifikaci.
function SprayDroneToolbox.onStored(self, fillType, part)
    local tb = getSpec(self).toolbox
    if not self.isClient or tb == nil then
        return
    end
    if part ~= nil then
        part.pulse = SprayDroneToolbox.PULSE_MS
    end
    if SprayDroneToolbox.getPlayerDistance(self, part) <= SprayDroneToolbox.NOTIFY_DISTANCE and g_currentMission ~= nil then
        g_currentMission:addIngameNotification(FSBaseMission.INGAME_NOTIFICATION_OK,
            string.format(g_i18n:getText("sdt_toolbox_stored"), getFillTypeTitle(fillType)))
    end
end

-- VSÁTÍ: neprázdné kanystry nad otvorem otevřené bedny se smažou (tomu v ruce ho bedna z rukou vezme) a jejich obsah (druh + litry)
-- jde do prvních volných slotů; prázdný nebo větší než slot (cizí naftový do 25 l) zůstane ležet.
function SprayDroneToolbox.updateIntake(self, dt)
    local tb = getSpec(self).toolbox
    tb.intakeTimer = tb.intakeTimer - dt
    if tb.intakeTimer > 0 then
        return
    end
    tb.intakeTimer = SprayDroneToolbox.INTAKE_INTERVAL_MS
    -- bedna vsává jen otevřená, každá jen do svých slotů
    local any = false
    for _, part in ipairs(tb.parts) do
        part.canTake = part.open and SprayDroneToolbox.getFreeSlot(tb, part) ~= nil
        any = any or part.canTake
    end
    if not any or not isAlive(self) then
        return
    end
    for _, near in ipairs(SprayDroneToolbox.findIntakeCanisters(self)) do
        local part = near.part
        local slot = SprayDroneToolbox.getFreeSlot(tb, part)
        if slot ~= nil and part.canTake and near.liters > 0.001 and near.liters <= tb.slotLiters + 0.01 then
            local c = tb.canisters[slot]
            c.fillType = near.kind
            c.liters = near.liters
            if near.holder ~= nil then
                dropFromHands(near.holder)
            end
            near.vehicle:delete()
            tb.storeCounter = (tb.storeCounter + 1) % (2 ^ SprayDroneToolbox.STORE_COUNTER_BITS)
            tb.storedFillType = near.kind
            tb.storedPart = part.index
            raiseDirty(self)
            SprayDroneToolbox.onStored(self, near.kind, part)
        end
    end
end

-- Hláška na obrazovce jen tomu, kdo příkaz zadal na tomto počítači (cizímu klientovi server hlášku neposílá).
local function notifyLocal(self, isLocal, key)
    if key ~= nil and isLocal and self.isClient and g_currentMission ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(key), 2500)
    end
end

-- VYBRAT: ze slotu se vyrobí nový objekt kanystru s obsahem slotu; slot se uvolní teprve po úspěšném vytvoření, do té doby
-- je zamčený (tb.spawning), takže při chybě se nic neztratí.
function SprayDroneToolbox.doTake(self, slot, isLocal, part)
    local tb = getSpec(self).toolbox
    local c = tb.canisters[slot]
    if c == nil or not isPresent(c) or tb.spawning[slot] then
        return
    end
    local fillType, liters = c.fillType, c.liters
    tb.spawning[slot] = true
    local started, reason = SprayDroneToolbox.spawnCanister(self, fillType, liters, function(success)
        tb.spawning[slot] = nil
        if success then
            if c.fillType == fillType then
                c.fillType, c.liters = FillType.UNKNOWN, 0
            end
            if isAlive(self) then
                raiseDirty(self)
            end
        else
            notifyLocal(self, isLocal, "sdt_toolbox_spawnFailed")
        end
    end, nil, part)
    if not started then
        tb.spawning[slot] = nil
        notifyLocal(self, isLocal, reason)
    end
end

-- VYBRAT N kanystrů daného druhu.
function SprayDroneToolbox.doTakeGroup(self, fillType, count, isLocal, part)
    local tb = getSpec(self).toolbox
    for _, slot in ipairs(SprayDroneToolbox.pickSlots(tb, fillType, count, false, part)) do
        SprayDroneToolbox.doTake(self, slot, isLocal, part)
    end
end

-- Vrátí litry, které se nepodařilo dát do nového kanystru: do koncentrátové nádrže (když to jde), jinak do volného slotu.
local function restoreLiters(self, fillType, liters)
    if not isAlive(self) or liters <= 0.001 then
        return
    end
    local tb = getSpec(self).toolbox
    local unit = SprayDroneToolbox.getConcentrateUnit(self)
    if unit ~= nil and (self:getFillUnitFillLevel(unit) <= 0.001 or self:getFillUnitFillType(unit) == fillType)
        and self:getFillUnitSupportsFillType(unit, fillType) then
        local added = self:addFillUnitFillLevel(self:getOwnerFarmId(), unit, liters, fillType, ToolType.UNDEFINED, nil) or 0
        liters = liters - added
    end
    if liters > 0.001 then
        local slot = SprayDroneToolbox.getFreeSlot(tb)
        if slot ~= nil then
            tb.canisters[slot].fillType, tb.canisters[slot].liters = fillType, math.min(liters, tb.slotLiters)
            liters = 0
            raiseDirty(self)
        end
    end
    if liters > 0.001 then
        Logging.warning("SDT: %.1f l koncentrátu se nepodařilo vrátit a je ztraceno", liters)
    end
end

-- VYPUSTIT NÁDRŽ: koncentrát jde po slotLiters (20 l) do `count` nových kanystrů, nejdřív do volných slotů bedny, zbytek se
-- vyrobí jako objekty před bednou (zbytek pod 20 l je částečně plný kanystr). Litry se z nádrže odebírají kus po kusu těsně před
-- uložením; když se kanystr nevyrobí, litry se vrátí (restoreLiters). noSlots = nic se nedává do bedny, všechno vznikne vedle vleku
-- (kanystry vedle sebe, Ctrl+I).
function SprayDroneToolbox.doDrain(self, count, isLocal, part, noSlots)
    local tb = getSpec(self).toolbox
    local unit = SprayDroneToolbox.getConcentrateUnit(self)
    if unit == nil then
        return
    end
    local tankType = self:getFillUnitFillType(unit)
    local farmId = self:getOwnerFarmId()

    local function takeFromTank(amount)
        local before = self:getFillUnitFillLevel(unit)
        self:addFillUnitFillLevel(farmId, unit, -math.min(amount, before), tankType, ToolType.UNDEFINED, nil)
        return before - self:getFillUnitFillLevel(unit)
    end

    -- kusy se naplánují dopředu z výchozí hladiny (návrat litrů po nezdařeném spawnu smyčku neprodlužuje)
    local chunks, remaining = {}, self:getFillUnitFillLevel(unit)
    while remaining > SprayDroneToolbox.MIN_LITERS and #chunks < count do
        local liters = math.min(tb.slotLiters, remaining)
        table.insert(chunks, liters)
        remaining = remaining - liters
    end
    for _, wanted in ipairs(chunks) do
        local taken = takeFromTank(wanted)
        if taken <= 0.001 then
            break
        end
        local slot = not noSlots and SprayDroneToolbox.getFreeSlot(tb, part) or nil
        if slot ~= nil then
            tb.canisters[slot].fillType, tb.canisters[slot].liters = tankType, taken
        else
            local at = nil
            if noSlots then
                at = { SprayDroneToolbox.getGroundSpawnPosition(self, part.spawnCounter, part) }
                part.spawnCounter = part.spawnCounter + 1
            end
            local started, reason = SprayDroneToolbox.spawnCanister(self, tankType, taken, function(success)
                if not success then
                    restoreLiters(self, tankType, taken)
                    notifyLocal(self, isLocal, "sdt_toolbox_spawnFailed")
                end
            end, at, part)
            if not started then
                restoreLiters(self, tankType, taken)
                notifyLocal(self, isLocal, reason)
                break
            end
        end
    end
    local rest = self:getFillUnitFillLevel(unit)
    if rest > 0 and rest <= SprayDroneToolbox.MIN_LITERS then
        takeFromTank(rest)
    end
    raiseDirty(self)
end

-- Příkaz z klienta nebo z místní hry; klient bez serveru ho pošle eventem, server / hostitel ho provede.
-- `fillType` = druh kanystrů (TAKE), `count` = kolik kanystrů (TAKE, DRAIN), `partIndex` = která bedna (OPEN, CLOSE, TAKE, DRAIN; bez údaje první).
function SprayDroneToolbox.command(self, command, fillType, count, noEventSend, partIndex)
    if SprayDroneToolboxEvent.sendEvent(self, command, fillType, count, noEventSend, partIndex) then
        return
    end
    local tb = getSpec(self).toolbox
    if tb == nil then
        return
    end
    local part = tb.parts[partIndex or 1] or tb.parts[1]
    local isLocal = not noEventSend
    fillType = fillType or FillType.UNKNOWN
    count = math.clamp(count or 1, 1, tb.slots)
    if command == SprayDroneToolboxEvent.OPEN then
        SprayDroneToolbox.setOpen(self, true, part)
    elseif command == SprayDroneToolboxEvent.CLOSE then
        SprayDroneToolbox.setOpen(self, false, part)
    elseif command == SprayDroneToolboxEvent.GROUND_DRAIN_START or command == SprayDroneToolboxEvent.GROUND_DRAIN_STOP then
        if command == SprayDroneToolboxEvent.GROUND_DRAIN_START then
            local reason = SprayDroneToolbox.getGroundDrainReason(self)
            if reason ~= nil then
                notifyLocal(self, isLocal, reason)
                return
            end
            SprayDroneToolbox.doDrain(self, math.huge, isLocal, part, true)
        end
    elseif command == SprayDroneToolboxEvent.HAND_POUR_START or command == SprayDroneToolboxEvent.HAND_POUR_STOP then
        local diesel = isDiesel(fillType)
        local flag = diesel and "handPourDiesel" or "handPourMain"
        if command == SprayDroneToolboxEvent.HAND_POUR_START then
            local reason = SprayDroneToolbox.getHandPourReason(self, diesel)
            if reason ~= nil then
                notifyLocal(self, isLocal, reason)
                return
            end
        end
        tb[flag] = command == SprayDroneToolboxEvent.HAND_POUR_START
        raiseDirty(self)
    else
        local reason = SprayDroneToolbox.getBlockReason(self, command, fillType, part)
        if reason ~= nil then
            notifyLocal(self, isLocal, reason)
            return
        end
        if command == SprayDroneToolboxEvent.TAKE then
            SprayDroneToolbox.doTakeGroup(self, fillType, count, isLocal, part)
        elseif command == SprayDroneToolboxEvent.DRAIN then
            SprayDroneToolbox.doDrain(self, count, isLocal, part)
        end
    end
end

-- Smí hráč z tohoto spojení bednu ovládat? Server ověřuje farmu a vzdálenost (COMMAND_DISTANCE od bedny; poloha, kterou
-- server nezná, se nezamítá). Vypouštění na zem se ovládá z kabiny tahače, tam se vzdálenost neověřuje (ignoreDistance).
function SprayDroneToolbox.isConnectionAllowed(self, connection, ignoreDistance)
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    local player = system ~= nil and system:getPlayerByConnection(connection) or nil
    if player == nil then
        return false
    end
    if not g_currentMission.accessHandler:canFarmAccess(player.farmId, self) then
        return false
    end
    if ignoreDistance then
        return true
    end
    local distance = SprayDroneToolbox.getDistanceOfPlayer(self, player)
    return distance == nil or distance <= SprayDroneToolbox.COMMAND_DISTANCE
end

-- Střed víčka kanystru ve světě (uzel canisterCap z i3d kanystru; bez něj odhad podle kořene).
local function getCapPosition(v)
    local cap = SprayDroneStation.getMappedNode(v, "canisterCap")
    if cap ~= nil and entityExists(cap) then
        return getWorldTranslation(cap)
    end
    return localToWorld(v.rootNode, 0.062, 0.317, 0)
end

-- Nejbližší hrdlo k bodu x, y, z: koncentrát má jedno, nafta jedno na každou elektrocentrálu (druhé jen u konfigurace se dvěma).
-- Vrací uzel a vzdálenost.
local function getNearestNeck(self, diesel, x, y, z)
    local tb = getSpec(self).toolbox
    local necks = { tb.neckNode }
    if diesel then
        necks = { tb.dieselNeckNode }
        if (getSpec(self).numGenerators or 1) >= 2 then
            necks[2] = tb.dieselNeckNode2
        end
    end
    local best, bestDistance
    for i = 1, 2 do
        local neck = necks[i]
        if neck ~= nil and entityExists(neck) then
            local nx, ny, nz = getWorldTranslation(neck)
            local distance = MathUtil.vector3Length(x - nx, y - ny, z - nz)
            if bestDistance == nil or distance < bestDistance then
                best, bestDistance = neck, distance
            end
        end
    end
    return best, bestDistance
end

-- NALÉVÁNÍ RUKOU: kanystry z modu, jejichž víčko je těsně nad hrdlem koncentrátové nádrže (neckNode, pourRadius) a které jsou
-- nakloněné hrdlem dolů (svislá složka jejich osy nejvýš POUR_UP_MAX). Vrací seznam { vehicle, kind, liters, upY, holder }.
function SprayDroneToolbox.findPourCanisters(self)
    local tb = getSpec(self).toolbox
    local result = {}
    local held = nil
    for _, v in ipairs(getVehicles()) do
        local kind = getUsableCanisterKind(self, v)
        local cx, cy, cz
        local neck
        if kind ~= nil then
            cx, cy, cz = getCapPosition(v)
            neck = getNearestNeck(self, isDiesel(kind), cx, cy, cz)
        end
        if neck ~= nil then
            local nx, ny, nz = getWorldTranslation(neck)
            if cy >= ny - 0.08 and MathUtil.vector3Length(cx - nx, cy - ny, cz - nz) <= tb.pourRadius then
                local _, upY = localDirectionToWorld(v.rootNode, 0, 1, 0)
                if upY <= SprayDroneToolbox.POUR_UP_MAX then
                    held = held or getHeldNodes()
                    table.insert(result, { vehicle = v, kind = kind, liters = v:getFillUnitFillLevel(SprayDroneToolbox.CANISTER_UNIT) or 0,
                        upY = upY, holder = getHolder(v, held) })
                end
            end
        end
    end
    return result
end

-- Server: z nakloněného kanystru nad hrdlem nádrže teče látka do koncentrátové nádrže (pourRate l/s, víc při větším náklonu).
function SprayDroneToolbox.updatePour(self, dt)
    local tb = getSpec(self).toolbox
    tb.pourAcc = (tb.pourAcc or 0) + dt
    tb.pourTimer = tb.pourTimer - dt
    if tb.pourTimer > 0 then
        return
    end
    tb.pourTimer = SprayDroneToolbox.POUR_INTERVAL_MS
    local seconds = math.min(tb.pourAcc, 500) * 0.001
    tb.pourAcc = 0
    if not isAlive(self) then
        return
    end
    -- kanystr nad hrdlem naklání hráč: bez hráče u vleku se vozidla světa neprocházejí
    local anyNear = false
    for _, player in ipairs(getPlayers()) do
        local distance = SprayDroneToolbox.getDistanceOfPlayer(self, player)
        if distance ~= nil and distance <= SprayDroneToolbox.POUR_PLAYER_DISTANCE then
            anyNear = true
            break
        end
    end
    if not anyNear then
        return
    end
    local farmId = self:getOwnerFarmId()
    for _, near in ipairs(SprayDroneToolbox.findPourCanisters(self)) do
        local unit = isDiesel(near.kind) and getSpec(self).dieselFillUnitIndex or SprayDroneToolbox.getConcentrateUnit(self)
        if unit ~= nil and near.liters > 0.001 and getTankReason(self, near.kind) == nil then
            local scale = math.clamp((SprayDroneToolbox.POUR_UP_MAX + 0.6 - near.upY) / 0.8, 0.3, 1)
            local amount = math.min(near.liters, tb.pourRate * scale * seconds, self:getFillUnitFreeCapacity(unit))
            local before = self:getFillUnitFillLevel(unit)
            self:addFillUnitFillLevel(farmId, unit, amount, near.kind, ToolType.UNDEFINED, nil)
            local moved = self:getFillUnitFillLevel(unit) - before
            if moved > 0 then
                near.vehicle:addFillUnitFillLevel(farmId, SprayDroneToolbox.CANISTER_UNIT, -moved, near.kind, ToolType.UNDEFINED, nil)
                tb.pourHold = SprayDroneToolbox.POUR_HOLD_MS
            end
        end
    end
end

-- NALÉVÁNÍ PŘES R: kanystry daného druhu (nafta / koncentrát) u hrdla nádrže: v rukou hráče, který stojí u hrdla
-- (HAND_POUR_PLAYER; držený kanystr fyzika často odtlačí od rámu vleku), nebo položené víčkem k hrdlu (HAND_POUR_LYING), od nejbližšího. Vrací seznam { vehicle, kind, liters, holder }.
function SprayDroneToolbox.findHandPourCanisters(self, diesel)
    local result = {}
    local held = getHeldNodes()
    for _, v in ipairs(getVehicles()) do
        local kind = getUsableCanisterKind(self, v)
        if kind ~= nil and isDiesel(kind) == diesel and not isCanisterMounted(v) then
            local holder = getHolder(v, held)
            local distance, limit = math.huge, SprayDroneToolbox.HAND_POUR_LYING
            if holder ~= nil then
                local px, py, pz = getPlayerPosition(holder)
                if px ~= nil then
                    distance, limit = select(2, getNearestNeck(self, diesel, px, py, pz)) or math.huge, SprayDroneToolbox.HAND_POUR_PLAYER
                end
            else
                local cx, cy, cz = getCapPosition(v)
                distance = select(2, getNearestNeck(self, diesel, cx, cy, cz)) or math.huge
            end
            if distance <= limit then
                table.insert(result, { vehicle = v, kind = kind, liters = v:getFillUnitFillLevel(SprayDroneToolbox.CANISTER_UNIT) or 0,
                    holder = holder, distance = distance })
            end
        end
    end
    table.sort(result, function(a, b) return a.distance < b.distance end)
    return result
end

local function getHandPourUnit(self, diesel)
    if diesel then
        return getSpec(self).dieselFillUnitIndex
    end
    return SprayDroneToolbox.getConcentrateUnit(self)
end

-- Klíč textu, proč nalévání přes R nejde (nil = jde z některého kanystru u hrdla).
function SprayDroneToolbox.getHandPourReason(self, diesel)
    local reason = "sdt_toolbox_pourNoCanister"
    for _, near in ipairs(SprayDroneToolbox.findHandPourCanisters(self, diesel)) do
        if near.liters > 0.001 then
            local r = getTankReason(self, near.kind)
            if r == nil then
                return nil
            end
            reason = r
        elseif reason == "sdt_toolbox_pourNoCanister" then
            reason = "sdt_toolbox_canisterEmpty"
        end
    end
    return reason
end

-- Server: běžící nalévání přes R teče z nejbližšího vhodného kanystru u hrdla (pourRate l/s); skončí, když není z čeho nebo kam.
local function pourFromHand(self, diesel, seconds)
    local tb = getSpec(self).toolbox
    local flag = diesel and "handPourDiesel" or "handPourMain"
    if not tb[flag] then
        return
    end
    local unit = getHandPourUnit(self, diesel)
    local farmId = self:getOwnerFarmId()
    for _, near in ipairs(SprayDroneToolbox.findHandPourCanisters(self, diesel)) do
        if unit ~= nil and near.liters > 0.001 and getTankReason(self, near.kind) == nil then
            local amount = math.min(near.liters, tb.pourRate * seconds, self:getFillUnitFreeCapacity(unit))
            local before = self:getFillUnitFillLevel(unit)
            self:addFillUnitFillLevel(farmId, unit, amount, near.kind, ToolType.UNDEFINED, nil)
            local moved = self:getFillUnitFillLevel(unit) - before
            if moved > 0 then
                near.vehicle:addFillUnitFillLevel(farmId, SprayDroneToolbox.CANISTER_UNIT, -moved, near.kind, ToolType.UNDEFINED, nil)
                tb.pourHold = SprayDroneToolbox.POUR_HOLD_MS
                return
            end
        end
    end
    tb[flag] = false
    raiseDirty(self)
end

function SprayDroneToolbox.updateHandPour(self, dt)
    local tb = getSpec(self).toolbox
    if not tb.handPourMain and not tb.handPourDiesel then
        tb.handPourAcc = 0
        return
    end
    tb.handPourAcc = (tb.handPourAcc or 0) + dt
    if tb.handPourAcc < SprayDroneToolbox.POUR_INTERVAL_MS or not isAlive(self) then
        return
    end
    local seconds = math.min(tb.handPourAcc, 500) * 0.001
    tb.handPourAcc = 0
    pourFromHand(self, false, seconds)
    pourFromHand(self, true, seconds)
end

-- Server: příznak „teče z kanystru“ (tb.pouring) pro zvuk na klientech; drží se POUR_HOLD_MS po posledním přelitém litru.
function SprayDroneToolbox.updatePouringFlag(self, dt)
    local tb = getSpec(self).toolbox
    tb.pourHold = math.max((tb.pourHold or 0) - dt, 0)
    local pouring = tb.pourHold > 0
    if pouring ~= tb.pouring then
        tb.pouring = pouring
        raiseDirty(self)
    end
end

-- VYPUŠTĚNÍ DO KANYSTRŮ (vanilla akce TOGGLE_TIPSTATE_GROUND, Ctrl+I): celý koncentrát z nádrže (fillUnit 3) se hned přelije do
-- kanystrů po slotLiters (20 l), které se objeví vedle sebe vedle vleku; nádrž zůstane prázdná a jde do ní nalít jiný druh.
-- (Starší popis: původně se koncentrát vypouštěl na zem groundDrainRate l/s.) Vanilla Dischargeable to u kapalin neumí (getCanDischargeToGround chce
-- density map height type, který kapaliny nemají), proto vlastní stav tb.groundDrain a akce registrovaná v SprayDroneStation.
function SprayDroneToolbox.getGroundDrainReason(self)
    local unit = SprayDroneToolbox.getConcentrateUnit(self)
    if unit == nil then
        return "sdt_toolbox_noTank"
    end
    if self:getFillUnitFillLevel(unit) <= SprayDroneToolbox.MIN_LITERS then
        return "sdt_toolbox_tankEmpty"
    end
    return nil
end

function SprayDroneToolbox.updateGroundDrain(self, dt)
    local tb = getSpec(self).toolbox
    SprayDroneToolbox.updatePouringFlag(self, dt)
    if not tb.groundDrain then
        return
    end
    local unit = SprayDroneToolbox.getConcentrateUnit(self)
    local level = unit ~= nil and self:getFillUnitFillLevel(unit) or 0
    if level > SprayDroneToolbox.MIN_LITERS then
        local amount = math.min(level, tb.groundDrainRate * math.min(dt, 500) * 0.001)
        self:addFillUnitFillLevel(self:getOwnerFarmId(), unit, -amount, self:getFillUnitFillType(unit), ToolType.UNDEFINED, nil)
        level = self:getFillUnitFillLevel(unit)
    end
    if level <= SprayDroneToolbox.MIN_LITERS then
        tb.groundDrain = false
        raiseDirty(self)
    end
end

-- Klient: akce Ctrl+I je aktivní a vidět jen tehdy, když je z čeho vypouštět (jinak klávesa zůstane ostatním vozidlům soupravy);
-- text se přepíná mezi „vypustit“ a „zastavit“. Volá SprayDroneStation.updateActionEventStates, `spec` nese actionEvents / actionStates.
function SprayDroneToolbox.updateGroundDrainAction(self, spec)
    local event = spec.actionEvents[InputAction.TOGGLE_TIPSTATE_GROUND]
    local tb = getSpec(self).toolbox
    if event == nil or tb == nil then
        return
    end
    local available = tb.groundDrain or SprayDroneToolbox.getGroundDrainReason(self) == nil
    local textKey = tb.groundDrain and "sdt_action_groundDrainOff" or "sdt_action_groundDrainOn"
    local state = spec.actionStates[InputAction.TOGGLE_TIPSTATE_GROUND]
    if state == nil then
        state = {}
        spec.actionStates[InputAction.TOGGLE_TIPSTATE_GROUND] = state
    end
    if state.available ~= available then
        state.available = available
        g_inputBinding:setActionEventActive(event.actionEventId, available)
        g_inputBinding:setActionEventTextVisibility(event.actionEventId, available)
    end
    if state.textKey ~= textKey then
        state.textKey = textKey
        g_inputBinding:setActionEventText(event.actionEventId, g_i18n:getText(textKey))
    end
end

function SprayDroneToolbox.actionEventGroundDrain(self, actionName, inputValue, callbackState, isAnalog)
    local tb = getSpec(self).toolbox
    if tb == nil then
        return
    end
    if tb.groundDrain then
        SprayDroneToolbox.command(self, SprayDroneToolboxEvent.GROUND_DRAIN_STOP)
        return
    end
    local reason = SprayDroneToolbox.getGroundDrainReason(self)
    if reason ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
        return
    end
    SprayDroneToolbox.command(self, SprayDroneToolboxEvent.GROUND_DRAIN_START)
end

-- Klient: když hráč drží kanystr nakloněný nad hrdlem nádrže a nalévání nejde, řekne mu proč (nejvýš jednou za POUR_WARN_MS).
function SprayDroneToolbox.updatePourHint(self, dt)
    local tb = getSpec(self).toolbox
    if g_localPlayer == nil or g_time < tb.pourWarnUntil then
        return
    end
    tb.hintTimer = (tb.hintTimer or 0) - dt
    if tb.hintTimer > 0 then
        return
    end
    tb.hintTimer = 250
    for _, near in ipairs(SprayDroneToolbox.findPourCanisters(self)) do
        if near.holder == g_localPlayer then
            local reason = nil
            if near.liters <= 0.001 then
                reason = "sdt_toolbox_canisterEmpty"
            else
                reason = getTankReason(self, near.kind)
            end
            if reason ~= nil then
                tb.pourWarnUntil = g_time + SprayDroneToolbox.POUR_WARN_MS
                g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
            end
            return
        end
    end
end

---------------------------------------------------------------------------------------------------
-- místní hráč: vanilla ObjectStorageDialog jako u skladu objektů (PlaceableObjectStorage) — řádek i počet v jednom okně

function SprayDroneToolbox.releaseLocal()
    SprayDroneToolbox.session = nil
end

-- Řádky dialogu: vybrat kanystry určitého druhu (koncentrát i nafta pohromadě, žádné vyhrazené zóny), vypustit
-- koncentrátovou nádrž do kanystrů. Jen sloty bedny `part` (bez ní všechny). Každý: { kind = "take"|"drain", fillType, max, text }.
function SprayDroneToolbox.buildEntries(self, part)
    local tb = getSpec(self).toolbox
    local i18n = g_i18n
    local entries = {}
    for _, g in ipairs(SprayDroneToolbox.getGroups(tb, part)) do
        table.insert(entries, { kind = "take", fillType = g.fillType, max = g.count,
            text = string.format(i18n:getText("sdt_toolbox_dlgTakeItem"), getFillTypeTitle(g.fillType)) })
    end
    local unit = SprayDroneToolbox.getConcentrateUnit(self)
    if unit ~= nil and SprayDroneToolbox.getBlockReason(self, SprayDroneToolboxEvent.DRAIN, nil, part) == nil then
        local level = self:getFillUnitFillLevel(unit)
        local chunks = math.min(math.ceil((level - SprayDroneToolbox.MIN_LITERS) / tb.slotLiters), tb.slots)
        table.insert(entries, { kind = "drain", max = math.max(chunks, 1),
            text = string.format(i18n:getText("sdt_toolbox_dlgDrain"), getFillTypeTitle(self:getFillUnitFillType(unit))) })
    end
    return entries
end

local function endSession()
    SprayDroneToolbox.session = nil
end

local function dispatch(session, entry, count)
    local E = SprayDroneToolboxEvent
    if entry.kind == "take" then
        SprayDroneToolbox.command(session.vehicle, E.TAKE, entry.fillType, count, nil, session.part.index)
    elseif entry.kind == "drain" then
        SprayDroneToolbox.command(session.vehicle, E.DRAIN, nil, count, nil, session.part.index)
    end
    SprayDroneToolbox.session = nil
end

local function showDialog(session)
    if ObjectStorageDialog == nil or ObjectStorageDialog.show == nil then
        Logging.warning("SDT: ObjectStorageDialog není k dispozici")
        return false
    end
    local entries = session.entries
    local infos, maxAmount = {}, 1
    for _, e in ipairs(entries) do
        local text = e.text
        local object = {
            getDialogText = function() return text end,
            getIsIdentical = function() return false end,
        }
        table.insert(infos, { objects = { object }, numObjects = e.max })
        maxAmount = math.max(maxAmount, e.max)
    end
    local function onSelected(_, index, amount)
        if SprayDroneToolbox.session ~= session then
            return
        end
        local entry = index ~= nil and entries[index] or nil
        if entry == nil or amount == nil or amount < 1 then
            endSession()
            return
        end
        dispatch(session, entry, math.min(amount, entry.max))
    end
    ObjectStorageDialog.show(onSelected, session, g_i18n:getText("sdt_toolbox_dlgTitle"), infos, maxAmount)
    return true
end

-- Aktivace bedny (R): ukáže dialog s koncentrátem i naftou pohromadě (žádné vyhrazené zóny), jen ze slotů bedny `part` (bez ní
-- první). Bez řádků (prázdná bedna i nádrž) jen hláška.
function SprayDroneToolbox.openDialog(self, part)
    local spec = getSpec(self)
    local tb = spec ~= nil and spec.toolbox or nil
    if tb == nil or not self.isClient or SprayDroneToolbox.session ~= nil then
        return
    end
    part = part or tb.parts[1]
    local entries = SprayDroneToolbox.buildEntries(self, part)
    if #entries == 0 then
        g_currentMission:showBlinkingWarning(g_i18n:getText("sdt_toolbox_dlgNothing"), 3500)
        return
    end
    local session = { vehicle = self, part = part, entries = entries, startTime = g_time }
    SprayDroneToolbox.session = session
    if not showDialog(session) then
        endSession()
    end
end

-- Každý snímek: odchod hráče od bedny a časový limit zavřou dialog. Víko zůstane otevřené, dokud ho hráč nezavře (Pavel 2026-10-11).
function SprayDroneToolbox.updateSession(dt)
    local session = SprayDroneToolbox.session
    if session == nil then
        return
    end
    if not isAlive(session.vehicle) then
        SprayDroneToolbox.session = nil
        return
    end
    if SprayDroneToolbox.getPlayerDistance(session.vehicle, session.part) > SprayDroneToolbox.SESSION_MAX_DISTANCE
        or g_time - session.startTime > SprayDroneToolbox.SESSION_TIMEOUT_MS then
        endSession()
        if g_gui ~= nil and g_gui:getIsDialogVisible() then
            g_gui:closeAllDialogs()
        end
    end
end

---------------------------------------------------------------------------------------------------
-- aktivace bedny (vanilla „Aktivovat objekt“): ActivatableObjectsSystem

-- Aktivace smí běžet jen u živého vleku mimo obchod, bez otevřeného dialogu a pro hráče z farmy, která k vleku smí; vrací stav bedny.
local function getUsableToolbox(vehicle)
    if vehicle == nil or vehicle.isDeleted or g_localPlayer == nil or SprayDroneToolbox.session ~= nil then
        return nil
    end
    if VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG then
        return nil
    end
    local spec = getSpec(vehicle)
    local tb = spec ~= nil and spec.toolbox or nil
    if tb == nil or not g_currentMission.accessHandler:canFarmAccess(g_localPlayer.farmId, vehicle) then
        return nil
    end
    return tb
end

SprayDroneToolboxActivatable = {}
local SprayDroneToolboxActivatable_mt = Class(SprayDroneToolboxActivatable)

function SprayDroneToolboxActivatable.new(vehicle, part)
    local self = setmetatable({}, SprayDroneToolboxActivatable_mt)
    self.vehicle = vehicle
    self.part = part
    self.activateText = g_i18n:getText("sdt_toolbox_open")
    return self
end

function SprayDroneToolboxActivatable:getIsActivatable()
    -- v nastoupeném vozidle (i ve vleku) se bedna neovládá: její klik je na X (ACTIVATE_HANDTOOL), a to patří rozložení vleku (IMPLEMENT_EXTRA2)
    local player = g_localPlayer
    if player ~= nil and player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil then
        return false
    end
    local vehicle = self.vehicle
    local tb = getUsableToolbox(vehicle)
    if tb == nil or SprayDroneToolbox.getPlayerDistance(vehicle, self.part) > tb.activateDistance then
        return false
    end
    self.activateText = g_i18n:getText("sdt_toolbox_menu")
    if self.clickEventId ~= nil then
        g_inputBinding:setActionEventText(self.clickEventId, g_i18n:getText(self.part.open and "sdt_toolbox_dlgClose" or "sdt_toolbox_open"))
    end
    return true
end

-- Kliknutí myší (ACTIVATE_HANDTOOL, X se ignoruje) otevře nebo zavře víko, stejně jako u vanilla dveří. Registruje se jen, dokud je
-- tahle aktivace vybraná (hráč je u bedny).
function SprayDroneToolboxActivatable:registerCustomInput(inputContext)
    local _
    _, self.clickEventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_HANDTOOL, self, self.onClick, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(self.clickEventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(self.clickEventId, true)
    g_inputBinding:setActionEventText(self.clickEventId, g_i18n:getText(self.part.open and "sdt_toolbox_dlgClose" or "sdt_toolbox_open"))
    _, self.menuEventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_OBJECT, self, self.run, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(self.menuEventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(self.menuEventId, true)
    g_inputBinding:setActionEventText(self.menuEventId, g_i18n:getText("sdt_toolbox_menu"))
end

function SprayDroneToolboxActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    self.clickEventId = nil
    self.menuEventId = nil
end

function SprayDroneToolboxActivatable:onClick()
    -- ACTIVATE_HANDTOOL bývá vedle levého tlačítka myši i na X, které patří rozložení vleku: skříň se otevírá jen myší
    if Input.isKeyPressed(Input.KEY_x) then
        return
    end
    local vehicle = self.vehicle
    local hands = g_localPlayer ~= nil and g_localPlayer.hands or nil
    if hands ~= nil then
        if hands:getIsHoldingItem() then
            return
        end
        local targeter = g_localPlayer.targeter
        if targeter ~= nil and hands:getCanPickUpNode(targeter:getClosestTargetedNodeFromType(HandToolHands)) then
            return
        end
    end
    local part = self.part
    SprayDroneToolbox.command(vehicle, part.open and SprayDroneToolboxEvent.CLOSE or SprayDroneToolboxEvent.OPEN, nil, nil, nil, part.index)
end

function SprayDroneToolboxActivatable:getDistance(x, y, z)
    local nx, ny, nz = getWorldTranslation(SprayDroneToolbox.getRefNode(self.vehicle, self.part))
    return MathUtil.vector3Length(x - nx, y - ny, z - nz)
end

function SprayDroneToolboxActivatable:run()
    SprayDroneToolbox.openDialog(self.vehicle, self.part)
end

function SprayDroneToolboxActivatable:activate() end

function SprayDroneToolboxActivatable:deactivate() end

function SprayDroneToolboxActivatable:draw() end

---------------------------------------------------------------------------------------------------
-- nalévání kanystru do nádrže přes R (jako vanilla „Doplnit“ / „Zastavit doplňování“): hráč stojí u hrdla elektrocentrály nebo
-- koncentrátové nádrže a drží kanystr (nebo ho tam položil)

SprayDroneHandPourActivatable = {}
local SprayDroneHandPourActivatable_mt = Class(SprayDroneHandPourActivatable)

function SprayDroneHandPourActivatable.new(vehicle, diesel)
    local self = setmetatable({}, SprayDroneHandPourActivatable_mt)
    self.vehicle = vehicle
    self.diesel = diesel
    self.flag = diesel and "handPourDiesel" or "handPourMain"
    self.activateText = ""
    return self
end

function SprayDroneHandPourActivatable:getNeck()
    local spec = getSpec(self.vehicle)
    local tb = spec ~= nil and spec.toolbox or nil
    if tb == nil then
        return nil, tb
    end
    local px, py, pz = getPlayerPosition(g_localPlayer)
    if px == nil then
        return nil, tb
    end
    return (getNearestNeck(self.vehicle, self.diesel, px, py, pz)), tb
end

function SprayDroneHandPourActivatable:getIsActivatable()
    local vehicle = self.vehicle
    local tb = getUsableToolbox(vehicle)
    local neck = tb ~= nil and self:getNeck() or nil
    if neck == nil then
        return false
    end
    local px, py, pz = getPlayerPosition(g_localPlayer)
    if px == nil then
        return false
    end
    local nx, ny, nz = getWorldTranslation(neck)
    if MathUtil.vector3Length(px - nx, py - ny, pz - nz) > SprayDroneToolbox.HAND_POUR_PLAYER then
        return false
    end
    if tb[self.flag] then
        self.activateText = g_i18n:getText("sdt_handPour_stop")
        return true
    end
    for _, near in ipairs(SprayDroneToolbox.findHandPourCanisters(vehicle, self.diesel)) do
        if near.holder == nil or near.holder == g_localPlayer then
            self.activateText = g_i18n:getText(self.diesel and "sdt_handPour_diesel" or "sdt_handPour_concentrate")
            return true
        end
    end
    return false
end

-- přednost před bednou, která je vedle
function SprayDroneHandPourActivatable:getDistance(x, y, z)
    local neck = self:getNeck()
    if neck == nil then
        return math.huge
    end
    local nx, ny, nz = getWorldTranslation(neck)
    return MathUtil.vector3Length(x - nx, y - ny, z - nz) - 1.5
end

function SprayDroneHandPourActivatable:run()
    local vehicle = self.vehicle
    local _, tb = self:getNeck()
    local fillType = self.diesel and FillType.DIESEL or FillType.UNKNOWN
    if tb ~= nil and tb[self.flag] then
        SprayDroneToolbox.command(vehicle, SprayDroneToolboxEvent.HAND_POUR_STOP, fillType)
        return
    end
    local reason = SprayDroneToolbox.getHandPourReason(vehicle, self.diesel)
    if reason ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
        return
    end
    SprayDroneToolbox.command(vehicle, SprayDroneToolboxEvent.HAND_POUR_START, fillType)
end

function SprayDroneHandPourActivatable:activate() end

function SprayDroneHandPourActivatable:deactivate() end

function SprayDroneHandPourActivatable:draw() end

