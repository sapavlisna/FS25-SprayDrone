-- Dron na plošině vleku za hry (docs/NAVRH-dron-predmet.md, etapa 0): spec.pads[i] je varianta dronu na plošině i ("" = prázdná),
-- plošina 1 = dron 1, plošina 2 = dron 2 (Max). setPadDrone vymění dron na jedné plošině tak, jako by vlek byl koupený s tou
-- konfigurací: viditelnost variant, parametry letu, uzly, zvuky, efekty, hadice, kamery a počet dronů. Parametry letu jsou
-- sdílené (SprayDroneFields), proto mají oba drony na Maxu stejnou variantu a dron 2 smí být jen s dronem 1.

-- Proč obsazení plošin pads nejde (klíč textu), nil = jde.
function SprayDroneStation.getPadsProblem(self, pads)
    local spec = SprayDroneDrones.getRoot(self)
    for i = 1, spec.numPads do
        local name = pads[i]
        if name == nil then
            return "sdt_pad_unknown"
        end
        if name ~= "" then
            local known = false
            for _, v in ipairs(spec.variants) do
                -- skenovací dron je od F2 jen kufrová sada (rozhodnutí D2): na plošinu vleku ho nejde dát, ani ze staré uložené hry
                known = known or (v.name == name and (spec.portable or not v.scan))
            end
            if i == 2 then
                local v = spec.secondVariants[name]
                known = known and v ~= nil and SprayDroneStation.getMappedNode(self, v.prefix .. "Root") ~= nil
            end
            if not known then
                return "sdt_pad_unknown"
            end
        end
    end
    if spec.numPads >= 2 and pads[2] ~= "" then
        if pads[1] == "" then
            return "sdt_pad_needFirst"
        elseif pads[1] ~= pads[2] then
            return "sdt_pad_mixed"
        end
    end
    return nil
end

-- Proč teď dron na plošině padIndex nejde vyměnit (klíč textu), nil = jde: nic neletí ani se neobsluhuje, žádný dron se zrovna
-- neskládá ke sundání (foldHold), na Minimu je bedna rozložená a dron na té plošině (je-li tam) je složený. folding: kontrola pro
-- sundání, které si dron samo složí (SprayDronePadSlots.doTake) – rozložený dron ani jeho foldHold nevadí.
function SprayDroneStation.getPadBlocker(self, padIndex, folding)
    local spec = SprayDroneDrones.getRoot(self)
    if padIndex < 1 or padIndex > spec.numPads then
        return "sdt_pad_unknown"
    end
    local busy = spec.transferMode ~= SprayDroneStation.TRANSFER_NONE or next(spec.batteryMoves or {}) ~= nil
    for k = 1, spec.numDrones do
        local d = spec.drones[k]
        busy = busy or d.missionActive or d.state ~= SprayDroneStation.STATE_PARKED or not d.isLinked
            or (d.foldHold == true and not (folding and k == padIndex))
    end
    if busy then
        return "sdt_pad_busy"
    end
    -- Mini: do zavřené bedny se dron nedá vložit ani z ní vyndat; obě polohy (bedna i plošina) jen u rozložené bedny (Pavel 2026-10-29)
    if spec.pad ~= nil and SprayDronePad.getDeploy(self) < 1 then
        return "sdt_pad_boxStowed"
    end
    local drone = SprayDroneDrones.getSpec(self, padIndex)
    if not folding and drone ~= nil and drone.hasDrone and spec.pads[padIndex] ~= "" and drone.unfold > 0 then
        return "sdt_pad_unfolded"
    end
    return nil
end

-- Cíl rozložení dronu (v kontextu dronu): dron, který se sundává (foldHold), se složí i na rozloženém vleku; dron Mini v bedně
-- (přepravní poloha) zůstává složený, rozkládá se jen na plošině.
function SprayDroneStation.getDroneUnfoldTarget(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if spec.foldHold or SprayDronePad.getIsDroneInBox(self) then
        return 0
    end
    return SprayDroneStation.getTrailerUnfold(self)
end

-- Server: na plošinu padIndex dá dron varianty name ("" = sundat). Vrací klíč textu s důvodem, když to nejde.
function SprayDroneStation.setPadDrone(self, padIndex, name)
    local spec = SprayDroneDrones.getRoot(self)
    if not self.isServer then
        return "sdt_pad_unknown"
    end
    if spec.pads[padIndex] == name then
        return nil
    end
    local pads = {}
    for i = 1, spec.numPads do
        pads[i] = spec.pads[i]
    end
    pads[padIndex] = name
    local problem = SprayDroneStation.getPadsProblem(self, pads) or SprayDroneStation.getPadBlocker(self, padIndex)
    SprayDroneSound.noteAction(string.format("vlek %s: plošina %d: %s -> %s%s", tostring(self.id), padIndex,
        spec.pads[padIndex] ~= "" and spec.pads[padIndex] or "prázdná", name ~= "" and name or "prázdná",
        problem ~= nil and " odmítnuto: " .. problem or ""))
    if problem ~= nil then
        return problem
    end
    SprayDroneStation.applyPads(self, pads)
    self:raiseDirtyFlags(spec.dirtyFlag)
    self:raiseActive()
    return nil
end

-- Úklid dronu v kontextu (hotspot, zvuky, efekty, pomocný uzel hadice); baterie z něj jde do nabíječky.
local function releaseDrone(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    SprayDroneStation.unloadDroneBattery(self)
    SprayDroneStation.deleteDrone(self)
    spec.samples, spec.effects = {}, {}
    if spec.hose ~= nil and spec.hose.via ~= nil and entityExists(spec.hose.via) then
        delete(spec.hose.via)
        spec.hose.via = nil
    end
end

-- Dron 2 pryč: model a úchyty se skryjí, hadice zůstane namotaná na navíječi.
local function removeSecondDrone(self)
    local root = SprayDroneDrones.getRoot(self)
    SprayDroneDrones.runAs(self, 2, function(s)
        local spec = s[SprayDroneStation.SPEC_NAME]
        releaseDrone(s)
        if spec.node ~= nil then
            setVisibility(spec.node, false)
        end
        for _, node in ipairs(spec.clamps or {}) do
            setVisibility(node, false)
        end
        local hose = spec.hose
        if hose ~= nil then
            if hose.coil ~= nil then
                setVisibility(hose.coil, true)
            end
            setVisibility(hose.nozzle, false)
            for _, node in ipairs(hose.segments) do
                setVisibility(node, false)
            end
        end
    end)
    root.drones[2] = nil
    root.numDrones = 1
    root.transferDrone = 1
end

-- Dron 1 znovu podle plošiny 1 (varianta, parametry, nabíjení, uzly, zvuky, hadice, kamera); baterie si nechají nabití v podílu.
-- batteryVariant: typ baterií pro prázdnou plošinu (ze sítě), jinak zůstává dosavadní.
local function reloadFirstDrone(self, xml, key, batteryVariant)
    local spec = SprayDroneDrones.getRoot(self)
    releaseDrone(self)
    local levels = {}
    for k, battery in ipairs(spec.batteries) do
        levels[k] = battery.charge / spec.batteryCapacity
    end
    local oldBatteryVariant = spec.batteryVariant
    spec.batteryVariant = batteryVariant or spec.batteryVariant
    SprayDroneStation.selectPadVariants(self, xml, key)
    SprayDroneStation.loadVariantParameters(self, xml, key)
    SprayDroneStation.loadChargeParameters(self, xml, key)
    for k, battery in ipairs(spec.batteries) do
        battery.charge = levels[k] * spec.batteryCapacity
    end
    if spec.batteryVariant ~= oldBatteryVariant then
        SprayDroneStation.applyBatteryVariant(self)
    end
    spec.navLights, spec.foldParts, spec.rotors, spec.tiltNode = {}, {}, {}, nil
    if spec.hasDrone then
        SprayDroneStation.loadDroneParts(self, xml, key, spec.droneKey)
    end
    SprayDroneStation.applyPropellerLook(self, xml, key)
    SprayDroneStation.initDroneState(self)
    spec.pfDose = nil
    if spec.hasDrone then
        SprayDroneStation.loadDroneSounds(self, xml, spec.droneKey)
    end
    SprayDroneStation.applyNavLights(self, false)
    SprayDroneStation.loadDroneService(self, xml, key)
    spec.clampsVisible = nil
    SprayDroneStation.initHomeYawOffset(self)
    SprayDroneStation.attachDroneCamera(self, xml)
    SprayDroneStation.initDroneFold(self)
end

-- Obsazení plošin pads (server po kontrole, klient ze stavu v síti): přenačte jen drony, kterých se změna týká. batteryVariant
-- (klient) srovná typ baterií u prázdné plošiny 1, kde jinak zůstává z dřívějška.
function SprayDroneStation.applyPads(self, pads, batteryVariant)
    SprayDroneDrones.restoreRoot(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local xml, key = self.xmlFile, "vehicle.sprayDrone"
    local changedFirst = pads[1] ~= spec.pads[1] or (pads[1] == "" and batteryVariant ~= nil and batteryVariant ~= spec.batteryVariant)
    local changedSecond = changedFirst or (spec.numPads >= 2 and pads[2] ~= spec.pads[2])
    if spec.numDrones > 1 and changedSecond then
        removeSecondDrone(self)
    end
    for i = 1, spec.numPads do
        spec.pads[i] = pads[i]
    end
    if changedFirst then
        reloadFirstDrone(self, xml, key, pads[1] == "" and batteryVariant or nil)
    end
    if changedSecond then
        SprayDroneStation.selectSecondVariant(self)
        if spec.secondVariant ~= nil then
            spec.numDrones = 2
            SprayDroneStation.loadSecondDrone(self, xml, key)
            SprayDroneDrones.runAs(self, 2, SprayDroneStation.initDroneFold)
        end
    end
    spec.activeDrones = spec.numDrones
    spec.firstDroneCamera = nil
    for k = 1, spec.numDrones do
        local camera = spec.drones[k].camera
        if camera ~= nil and (spec.firstDroneCamera == nil or camera < spec.firstDroneCamera) then
            spec.firstDroneCamera = camera
        end
    end
    SprayDroneStation.applyMissionMode(self)
    spec.settingsVersion = spec.settingsVersion + 1
    SprayDroneStation.markRouteDirty(self)
    SprayDroneStation.updateServiceVisuals(self, 0)
    self:requestActionEventUpdate()
    if SprayDroneDebug and SprayDroneDebug.ENABLED then
        Logging.info("SDT děj: vlek %s: plošiny %s, dronů %d, %s", tostring(self.id), SprayDroneStation.getPadsText(self), spec.numDrones,
            SprayDroneStation.getPadParamsText(self))
    end
end

function SprayDroneStation.getPadsText(self)
    local spec = SprayDroneDrones.getRoot(self)
    local parts = {}
    for i = 1, spec.numPads do
        parts[i] = spec.pads[i] ~= "" and spec.pads[i] or "-"
    end
    return table.concat(parts, "/")
end

function SprayDroneStation.getPadParamsText(self)
    local spec = SprayDroneDrones.getRoot(self)
    return string.format("dron %s: nádrž %.0f l, záběr %.0f m, hmotnost %.1f kg, baterie %.0f s (%s), vítr max %.0f m/s, čerpadlo %.1f l/s, dosah %.0f m",
        spec.droneName ~= "" and spec.droneName or "žádný", spec.tankCapacity, spec.workWidth, spec.droneMass, spec.batteryCapacity,
        tostring(spec.batteryVariant), spec.sprayMaxWind, spec.pumpRate, spec.maxRange)
end

local function getPadIndex(name)
    for j, padName in ipairs(SprayDroneStation.PAD_NAMES) do
        if padName == name then
            return j
        end
    end
    return 0
end

-- Plošiny, typ baterií (u prázdné plošiny 1 závisí na historii, proto jde po síti taky), skládání dronů ke sundání (foldHold,
-- podle něj klient dron skládá sám) a u Mini poloha dronu (bedna / plošina).
function SprayDroneStation.writePads(self, streamId)
    local spec = SprayDroneDrones.getRoot(self)
    for i = 1, spec.numPads do
        streamWriteUIntN(streamId, getPadIndex(spec.pads[i]), SprayDroneStation.PAD_BITS)
    end
    streamWriteUIntN(streamId, getPadIndex(spec.batteryVariant), SprayDroneStation.PAD_BITS)
    for i = 1, spec.numPads do
        local drone = SprayDroneDrones.getSpec(self, i)
        streamWriteBool(streamId, drone ~= nil and drone.foldHold == true)
    end
    if spec.pad ~= nil then
        streamWriteBool(streamId, spec.pad.onPlate == true)
    end
end

function SprayDroneStation.readPads(self, streamId)
    local spec = SprayDroneDrones.getRoot(self)
    local pads, changed = {}, false
    for i = 1, spec.numPads do
        local index = streamReadUIntN(streamId, SprayDroneStation.PAD_BITS)
        pads[i] = SprayDroneStation.PAD_NAMES[index] or ""
        changed = changed or pads[i] ~= spec.pads[i]
    end
    local batteryVariant = SprayDroneStation.PAD_NAMES[streamReadUIntN(streamId, SprayDroneStation.PAD_BITS)]
    local holds = {}
    for i = 1, spec.numPads do
        holds[i] = streamReadBool(streamId)
    end
    -- poloha dřív než přenačtení dronu: initDroneFold z ní bere cíl rozložení
    if spec.pad ~= nil then
        SprayDronePad.setDroneOnPlate(self, streamReadBool(streamId))
    end
    if changed or (batteryVariant ~= nil and batteryVariant ~= spec.batteryVariant) then
        SprayDroneStation.applyPads(self, pads, batteryVariant)
    end
    for i = 1, spec.numPads do
        local drone = SprayDroneDrones.getSpec(self, i)
        if drone ~= nil then
            drone.foldHold = holds[i] or nil
        end
    end
end
