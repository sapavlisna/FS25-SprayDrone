-- Plošiny dronů na vleku jako sloty pro dronové předměty (docs/NAVRH-dron-predmet.md, etapa 1). Vlek se kupuje bez dronu; dron (vozidlo sdtDrone, SprayDroneItem) hráč
-- přinese a u plošiny R ho nasadí: předmět se smaže a vlek přepne variantu dronu na plošině (SprayDroneStation.setPadDrone, etapa 0), náplň dronu jde s ním.
-- R bez dronu v ruce u obsazené plošiny dron odepne: vlek variantu skryje a na jejím místě (stejná poloha i natočení, nikam se nepřesouvá) vznikne
-- předmět s náplní (VehicleLoadingData, getTakePose), který zůstane ležet na plošině / palubě a hráč si ho vezme do ruky jako každý předmět.
-- Odepnout jde, když nic neletí ani se neobsluhuje; rozložený dron se nejdřív na místě složí (foldHold, doTake čeká v update), baterie z něj jde do nabíječky
-- vleku (baterie jako předmět je etapa 2). Mini: nasadit i sundat jen u rozložené bedny (SprayDroneStation.getPadBlocker); plošina 1 má dvě místa,
-- bednu (přepravní poloha) a rozloženou plošinu (letová), R vloží dron do bližšího z nich (PLACE / PLACE_PLATE) a vezme ho z toho, kde stojí;
-- s prázdnýma rukama u druhého místa ho R rovnou a okamžitě přendá (MOVE_BOX / MOVE_PLATE, bez animace). Bedna má přednost:
-- do BOX_CATCH_DISTANCE od ní R patří jí (vložit, vzít, přendat do bedny), i když je hráč blíž středu plošiny. S dronem v ruce
-- se R u plošiny hlásí vzdáleností 0, aby ho nepřebila bedna na kanystry, hrdla ani hadice vedle.
-- Změny dělá server (příkaz z klienta jde SprayDronePadSlotEvent), obsazení plošin jde klientům ve stavu vleku (SprayDroneStation.writePads).

SprayDronePadSlots = {}

SprayDronePadSlots.ACTIVATE_DISTANCE = 3.2    -- hráč nejvýš tak daleko od středu plošiny (m, vodorovně)
SprayDronePadSlots.ACTIVATE_HEIGHT = 3.5      -- … a plošina nejvýš tolik m nad nebo pod hráčem (plošina na palubě je o metr výš než hráč)
SprayDronePadSlots.STORE_DISTANCE = 2.5       -- ležící dron nejvýš tak daleko od hráče (m)
SprayDronePadSlots.BOX_CATCH_DISTANCE = 1.5   -- Mini: hráč do tolika m (vodorovně) od bedny ovládá bednu, ne plošinu (střed plošiny je od bedny 2,2 m)
SprayDronePadSlots.COMMAND_DISTANCE = 7       -- server: hráč od plošiny (m), rezerva na zpoždění polohy
SprayDronePadSlots.LYING_IGNORE_MS = 15000    -- po sundání se ležící dron chvíli nenabízí k nasazení
SprayDronePadSlots.CANDIDATE_INTERVAL_MS = 200
SprayDronePadSlots.FOLD_TIMEOUT_MS = 20000    -- nejdéle tak dlouho se čeká na složení dronu před sundáním
SprayDronePadSlots.TAKE_LIFT = 0.05           -- odepnutý dron vznikne o tolik m nad místem na plošině (kolize desky Mini sahá 3 cm nad povrch), pak dosedne
SprayDronePadSlots.ITEM_YAW = -math.pi / 2    -- natočení předmětu dronu proti kořeni dronu na vleku (getTakePose)
SprayDronePadSlots.ITEM_FILE = "objects/drone/drone%s.xml"
SprayDronePadSlots.modDirectory = g_currentModDirectory

local function getSpec(self)
    return self[SprayDroneStation.SPEC_NAME]
end

local function getRoot(self)
    return SprayDroneDrones.getRoot(self)
end

local function helpers()
    return SprayDroneRelaySlots.helpers
end

local function raiseDirty(self)
    self:raiseDirtyFlags(getRoot(self).dirtyFlag)
end

---------------------------------------------------------------------------------------------------
-- čistá logika

-- Proč se na plošinu padIndex nedá nasadit dron varianty variant (l10n klíč), nebo nil.
function SprayDronePadSlots.getPlaceProblem(self, padIndex, variant)
    local spec = getRoot(self)
    if padIndex < 1 or padIndex > spec.numPads then
        return "sdt_pad_unknown"
    end
    if spec.pads[padIndex] ~= "" then
        return "sdt_padslot_full"
    end
    local pads = {}
    for i = 1, spec.numPads do
        pads[i] = spec.pads[i]
    end
    pads[padIndex] = variant
    return SprayDroneStation.getPadsProblem(self, pads) or SprayDroneStation.getPadBlocker(self, padIndex)
end

-- Proč se z plošiny padIndex nedá dron sundat (l10n klíč), nebo nil. Rozložený dron nevadí, před sundáním se složí.
function SprayDronePadSlots.getTakeProblem(self, padIndex)
    local spec = getRoot(self)
    if padIndex < 1 or padIndex > spec.numPads or spec.pads[padIndex] == "" then
        return "sdt_pad_noDrone"
    end
    local pads = {}
    for i = 1, spec.numPads do
        pads[i] = spec.pads[i]
    end
    pads[padIndex] = ""
    return SprayDroneStation.getPadsProblem(self, pads) or SprayDroneStation.getPadBlocker(self, padIndex, true)
end

---------------------------------------------------------------------------------------------------
-- načtení, smazání

function SprayDronePadSlots.load(self)
    local spec = getRoot(self)
    local ps = { nodes = {}, candidateTimer = 0, lyingIgnoreUntil = 0, spawning = {}, folding = {} }
    for i = 1, spec.numPads do
        local variants = i == 2 and spec.secondVariants or nil
        local prefix = nil
        if i == 1 then
            prefix = spec.variants[1] ~= nil and spec.variants[1].prefix or nil
        else
            local _, v = next(variants or {})
            prefix = v ~= nil and v.prefix or nil
        end
        ps.nodes[i] = prefix ~= nil and SprayDroneStation.getMappedNode(self, prefix .. "Root") or nil
    end
    spec.padSlots = ps
    if self.isClient and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        ps.activatable = SprayDronePadSlotsActivatable.new(self)
        g_currentMission.activatableObjectsSystem:addActivatable(ps.activatable)
    end
end

function SprayDronePadSlots.delete(self)
    local spec = getRoot(self)
    local ps = spec ~= nil and spec.padSlots or nil
    if ps ~= nil and ps.activatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(ps.activatable)
        ps.activatable = nil
    end
end

---------------------------------------------------------------------------------------------------
-- hledání dronu k nasazení (klient i server)

function SprayDronePadSlots.getHeldDrone(player)
    local h = helpers()
    local held = h.getHeldNode(player)
    if held == nil or g_currentMission.getNodeObject == nil then
        return nil
    end
    local object = g_currentMission:getNodeObject(held)
    if SprayDroneItem.getVariant(object) ~= nil and h.isAlive(object) then
        return object
    end
    return nil
end

-- Dron, který hráč u vleku nasadí: drží-li dron v rukou, ten; jinak nejbližší ležící do STORE_DISTANCE (s ignoreLying se ležící nehledají).
function SprayDronePadSlots.findDrone(self, player, ignoreLying)
    local h = helpers()
    local x, y, z = h.getPlayerPosition(player)
    if x == nil then
        return nil
    end
    if h.getHeldNode(player) ~= nil then
        local drone = SprayDronePadSlots.getHeldDrone(player)
        return drone, drone ~= nil and 0 or nil
    end
    if ignoreLying then
        return nil
    end
    local best, bestDistance = nil, SprayDronePadSlots.STORE_DISTANCE
    local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, v in ipairs(vehicles) do
        if SprayDroneItem.getVariant(v) ~= nil and h.isAlive(v) and not h.isMounted(v) then
            local vx, vy, vz = getWorldTranslation(v.rootNode)
            local d = MathUtil.vector3Length(x - vx, y - vy, z - vz)
            if d <= bestDistance then
                best, bestDistance = v, d
            end
        end
    end
    return best, best ~= nil and bestDistance or nil
end

-- Místa plošiny padIndex, kde dron stojí nebo kam jde dát: { onPlate, move, x, y, z }. Obvykle uzel dronu; Mini má u plošiny 1 bednu
-- a (rozloženou) plošinu: prázdná nabízí obě k vložení, obsazená místo, kde dron stojí (vzít), a u rozložené bedny i to druhé
-- (move = přendat tam).
function SprayDronePadSlots.getSpots(self, padIndex)
    local spec = getRoot(self)
    local node = spec.padSlots.nodes[padIndex]
    if node == nil then
        return {}
    end
    if padIndex ~= 1 or spec.pad == nil then
        local x, y, z = getWorldTranslation(node)
        return { { onPlate = nil, x = x, y = y, z = z } }
    end
    local occupied = spec.pads[1] ~= ""
    local deployed = SprayDronePad.getDeploy(self) >= 1
    local spots = {}
    for _, onPlate in ipairs({ false, true }) do
        local here = occupied and spec.pad.onPlate == onPlate
        local move = occupied and not here
        if (here or deployed or not onPlate) and (not move or deployed) then
            local x, y, z = SprayDronePad.getSpotPosition(self, onPlate)
            table.insert(spots, { onPlate = onPlate, move = move, x = x, y = y, z = z })
        end
    end
    return spots
end

-- Uzel, na který hráč u místa míří (bonus SprayDroneLink.aimDistance): u Mini pevný bod bedny / plošiny, jinak uzel dronu.
function SprayDronePadSlots.getSpotNode(self, padIndex, onPlate)
    local spec = getRoot(self)
    if onPlate ~= nil and spec.pad ~= nil then
        return onPlate and spec.pad.platePoint or spec.pad.boxPoint
    end
    return spec.padSlots.nodes[padIndex]
end

-- Nejbližší místo plošiny hráče, na které platí occupied (true = obsazená, false = prázdná), do ACTIVATE_DISTANCE; bedna Mini do
-- BOX_CATCH_DISTANCE vyhrává vždy. Vrací index plošiny, vzdálenost, u Mini polohu (true = plošina, false = bedna) a move (obsazená
-- plošina: přendat na tohle místo, ne vzít), nebo nil.
function SprayDronePadSlots.getNearestPad(self, x, y, z, occupied)
    local spec = getRoot(self)
    local best, bestDistance, bestOnPlate, bestMove, bestKey = nil, nil, nil, nil, math.huge
    for i = 1, spec.numPads do
        if (spec.pads[i] ~= "") == occupied then
            for _, spot in ipairs(SprayDronePadSlots.getSpots(self, i)) do
                if math.abs(y - spot.y) <= SprayDronePadSlots.ACTIVATE_HEIGHT then
                    local d = MathUtil.vector2Length(x - spot.x, z - spot.z)
                    local key = d
                    if spot.onPlate == false and d <= SprayDronePadSlots.BOX_CATCH_DISTANCE then
                        key = -1
                    end
                    if d <= SprayDronePadSlots.ACTIVATE_DISTANCE and key <= bestKey then
                        best, bestDistance, bestOnPlate, bestMove, bestKey = i, d, spot.onPlate, spot.move == true, key
                    end
                end
            end
        end
    end
    return best, bestDistance, bestOnPlate, bestMove
end

---------------------------------------------------------------------------------------------------
-- příkazy (server)

-- Cesta k xml dronového předmětu, jen když je v obchodě (VehicleLoadingData:setFilename hledá storeItem podle xml).
function SprayDronePadSlots.getItemFilename(variant)
    if g_storeManager == nil then
        return nil
    end
    local relative = string.format(SprayDronePadSlots.ITEM_FILE, variant)
    local path = (SprayDronePadSlots.modDirectory or "") .. relative
    if g_storeManager:getItemByXMLFilename(path) ~= nil then
        return path
    end
    local tail = string.lower(relative)
    for key, item in pairs(g_storeManager.xmlFilenameToItem or {}) do
        if string.sub(string.lower(key), -#tail) == tail then
            return item.xmlFilename or key
        end
    end
    return nil
end

-- NASADIT: dron (drží ho hráč, nebo leží u něj) se smaže a jeho náplň jde do dronu na plošině. onPlate: Mini, kam na plošině 1 (true = letová
-- plošina, jinak bedna); poloha se nastaví před výměnou dronu, aby se nový dron rovnou rozložil / zůstal složený.
function SprayDronePadSlots.doPlace(self, player, item, padIndex, isLocal, onPlate)
    local h = helpers()
    local variant = SprayDroneItem.getVariant(item)
    if variant == nil or not h.isAlive(item) then
        return
    end
    local reason = SprayDronePadSlots.getPlaceProblem(self, padIndex, variant)
    if reason == nil and (h.isMounted(item) or (item.getIsControlled ~= nil and item:getIsControlled())) then
        reason = "sdt_padslot_noDrone"
    end
    local holder = h.getHolder(item)
    if reason == nil and holder ~= nil and holder ~= player then
        reason = "sdt_padslot_noDrone"
    end
    if reason == nil and holder == nil then
        local px, py, pz = h.getPlayerPosition(player)
        local vx, vy, vz = getWorldTranslation(item.rootNode)
        if px ~= nil and MathUtil.vector3Length(px - vx, py - vy, pz - vz) > SprayDronePadSlots.STORE_DISTANCE + 1.5 then
            reason = "sdt_padslot_noDrone"
        end
    end
    if reason ~= nil then
        h.notifyLocal(self, isLocal, reason)
        return
    end
    local fill, fillType = SprayDroneItem.getFill(item)
    if padIndex == 1 then
        SprayDronePad.setDroneOnPlate(self, onPlate == true)
    end
    local problem = SprayDroneStation.setPadDrone(self, padIndex, variant)
    if problem ~= nil then
        h.notifyLocal(self, isLocal, problem)
        return
    end
    SprayDroneDrones.runAs(self, padIndex, function(s)
        local d = s[SprayDroneStation.SPEC_NAME]
        if d.hasDrone and fill > 0.001 and fillType ~= FillType.UNKNOWN then
            d.droneFillLevel = math.min(fill, d.tankCapacity)
            d.droneFillType = fillType
        end
    end)
    SprayDroneStation.markRouteDirty(self)
    SprayDroneSound.noteAction(string.format("dron %s (id %s) nasazen na plošinu %d%s vleku %s (náplň %.1f l)", variant, tostring(item.id), padIndex,
        getRoot(self).pad ~= nil and (onPlate and " (Mini: na plošinu)" or " (Mini: do bedny)") or "", tostring(self.id), fill))
    if holder ~= nil and holder.hands ~= nil and holder.hands.dropHeldItem ~= nil then
        holder.hands:dropHeldItem()
    end
    item:delete()
    raiseDirty(self)
    self:raiseActive()
end

-- Před sundáním: proč předmět dronu varianty variant teď nejde vyrobit (l10n klíč), jinak nil a cesta k jeho xml.
local function getSpawnProblem(variant)
    local filename = SprayDronePadSlots.getItemFilename(variant)
    if filename == nil then
        Logging.warning("SDT: dron %s nejde vyrobit (chybí %s v obchodě)", variant, string.format(SprayDronePadSlots.ITEM_FILE, variant))
        return "sdt_padslot_spawnFailed"
    end
    local slotSystem = g_currentMission.slotSystem
    if slotSystem ~= nil and SlotSystem ~= nil and SlotSystem.LIMITED_OBJECT_PALLET ~= nil
        and not slotSystem:getCanAddLimitedObjects(SlotSystem.LIMITED_OBJECT_PALLET, 1) then
        return "sdt_toolbox_spawnLimit"
    end
    return nil, filename
end

-- Server: dron na plošině padIndex se skládá ke sundání (hold), nebo se vrací k rozložení podle vleku. Jde klientům ve writePads.
local function setFoldHold(self, padIndex, hold)
    local drone = SprayDroneDrones.getSpec(self, padIndex)
    if drone ~= nil and (drone.foldHold == true) ~= hold then
        drone.foldHold = hold or nil
        raiseDirty(self)
        self:raiseActive()
    end
end

-- Je dron na plošině padIndex složený a v klidu (vrtule dotočené, hadice namotaná)?
local function isDroneStowed(self, padIndex)
    local d = SprayDroneDrones.getSpec(self, padIndex)
    return d == nil or not d.hasDrone or (d.unfold <= 0 and d.rotorSpeed <= 0 and d.rotorsParked and (d.hoseT or 0) <= 0)
end

-- Kde vznikne předmět sundaného dronu: přesně tam, kde (složený) dron na plošině stojí, jen o TAKE_LIFT výš. Kořen dronu na vleku i počátek
-- předmětu leží pod středem trupu na úrovni lyžin (build_trailer_middle.place_drone, build_drone_items), ale nos dronu míří v kořeni
-- na vleku po -Y Blenderu (= +Z i3d), kdežto v předmětu po +X; předmět je proto proti kořeni otočený o ITEM_YAW kolem svislé osy.
-- Vrací x, y, z, rx, ry, rz ve světě, nebo nil (plošina bez uzlu).
function SprayDronePadSlots.getTakePose(self, padIndex)
    local drone = SprayDroneDrones.getSpec(self, padIndex)
    local node = drone ~= nil and drone.hasDrone and drone.isLinked ~= false and drone.node or nil
    node = node or getRoot(self).padSlots.nodes[padIndex]
    if node == nil then
        return nil
    end
    local pose = createTransformGroup("sdtDroneTakePose")
    link(node, pose)
    setTranslation(pose, 0, 0, 0)
    setRotation(pose, 0, SprayDronePadSlots.ITEM_YAW, 0)
    local x, y, z = getWorldTranslation(pose)
    local rx, ry, rz = getWorldRotation(pose)
    delete(pose)
    return x, y + SprayDronePadSlots.TAKE_LIFT, z, rx, ry, rz
end

-- Z dronu na plošině se vyrobí předmět s jeho náplní na místě, kde dron stál (getTakePose: bez přesunu k hráči, leží pak na plošině / palubě);
-- plošina se uvolní až po úspěšném načtení předmětu.
local function spawnTaken(self, player, padIndex, isLocal)
    local h = helpers()
    local spec = getRoot(self)
    local ps = spec.padSlots
    local variant = spec.pads[padIndex]
    local x, y, z, rx, ry, rz = SprayDronePadSlots.getTakePose(self, padIndex)
    if x == nil then
        setFoldHold(self, padIndex, false)
        h.notifyLocal(self, isLocal, "sdt_padslot_spawnFailed")
        return
    end
    local reason, filename = getSpawnProblem(variant)
    local data = nil
    if reason == nil then
        data = VehicleLoadingData.new()
        data:setFilename(filename)
        if not data.isValid then
            reason = "sdt_padslot_spawnFailed"
        end
    end
    if reason ~= nil then
        setFoldHold(self, padIndex, false)
        h.notifyLocal(self, isLocal, reason)
        return
    end
    local drone = SprayDroneDrones.getSpec(self, padIndex)
    local fill, fillType = drone.droneFillLevel or 0, drone.droneFillType or FillType.UNKNOWN
    local farmId = self:getOwnerFarmId()
    data:setPosition(x, y, z)
    data:setRotation(rx, ry, rz)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(farmId)
    ps.spawning[padIndex] = true
    data:load(function(_, vehicles, loadState)
        ps.spawning[padIndex] = false
        local item = vehicles ~= nil and vehicles[1] or nil
        local function discard(text)
            Logging.warning("SDT: dron %s se nepodařilo sundat (%s)", variant, text)
            for _, v in ipairs(vehicles or {}) do
                v:delete()
            end
            if h.isAlive(self) then
                setFoldHold(self, padIndex, false)
            end
            h.notifyLocal(self, isLocal, "sdt_padslot_spawnFailed")
        end
        if loadState ~= VehicleLoadingState.OK or item == nil then
            discard("načtení předmětu")
            return
        end
        if not h.isAlive(self) or spec.pads[padIndex] ~= variant then
            discard("plošina se mezitím změnila")
            return
        end
        -- příznak skládání pryč už před výměnou: setPadDrone ho bere jako probíhající obsluhu a dron 1 (= spec vozidla) by ho
        -- jinak nesl dál i na prázdné plošině
        setFoldHold(self, padIndex, false)
        local problem = SprayDroneStation.setPadDrone(self, padIndex, "")
        if problem ~= nil then
            discard(problem)
            h.notifyLocal(self, isLocal, problem)
            return
        end
        if fill > 0.001 and fillType ~= FillType.UNKNOWN and item.spec_fillUnit ~= nil and item:getFillUnitExists(1) then
            item:addFillUnitFillLevel(farmId, 1, fill, fillType, ToolType.UNDEFINED, nil)
        end
        SprayDroneSound.noteAction(string.format("dron %s (id %s) sundán z plošiny %d vleku %s (náplň %.1f l)", variant, tostring(item.id), padIndex,
            tostring(self.id), fill))
        raiseDirty(self)
    end)
end

-- ODEPNOUT (Pavel 2026-10-29: „dron se jen složí a odepne, jinak zůstane na místě“): rozložený dron se nejdřív složí (foldHold, doběhne
-- v update), pak se z něj na místě vyrobí předmět (spawnTaken).
function SprayDronePadSlots.doTake(self, player, padIndex, isLocal)
    local h = helpers()
    local spec = getRoot(self)
    local ps = spec.padSlots
    local reason = SprayDronePadSlots.getTakeProblem(self, padIndex)
    if reason == nil and (ps.spawning[padIndex] or ps.folding[padIndex] ~= nil) then
        reason = "sdt_padslot_busy"
    end
    if reason == nil then
        reason = getSpawnProblem(spec.pads[padIndex])
    end
    if reason ~= nil then
        h.notifyLocal(self, isLocal, reason)
        return
    end
    if isDroneStowed(self, padIndex) then
        spawnTaken(self, player, padIndex, isLocal)
        return
    end
    ps.folding[padIndex] = { player = player, isLocal = isLocal, variant = spec.pads[padIndex], timeout = g_time + SprayDronePadSlots.FOLD_TIMEOUT_MS }
    setFoldHold(self, padIndex, true)
    SprayDroneSound.noteAction(string.format("dron %s na plošině %d vleku %s se skládá ke sundání", spec.pads[padIndex], padIndex, tostring(self.id)))
end

-- animace (Pavel 2026-10-29): dron se v nové poloze rovnou objeví složený / rozložený (SprayDronePad.setDroneOnPlate). Vrací klíč
-- textu s důvodem, když to nejde, jinak nil.
function SprayDronePadSlots.moveMiniTo(self, onPlate)
    local spec = getRoot(self)
    local ps = spec.padSlots
    if spec.pad == nil or ps == nil then
        return "sdt_pad_unknown"
    end
    if spec.pad.onPlate == onPlate then
        return nil
    end
    local reason = SprayDronePadSlots.getTakeProblem(self, 1)
    if reason == nil and (ps.spawning[1] or ps.folding[1] ~= nil) then
        reason = "sdt_padslot_busy"
    end
    if reason ~= nil then
        return reason
    end
    SprayDronePad.setDroneOnPlate(self, onPlate)
    SprayDroneSound.noteAction(string.format("Mini %s: dron přendán %s", tostring(self.id), onPlate and "na plošinu" or "do bedny"))
    raiseDirty(self)
    return nil
end

-- Server, z onUpdate vleku: složený dron čekající na sundání se sundá. Když se mezitím něco změnilo (mise, přečerpání, Mini zavírá
-- bednu…) nebo se dron nesložil včas, sundání se zruší a dron se zase rozloží podle vleku. Na baterii, která se při skládání vrací
-- do nabíječky, se počká.
function SprayDronePadSlots.update(self)
    local spec = getRoot(self)
    local ps = spec.padSlots
    if ps == nil or next(ps.folding) == nil then
        return
    end
    local batteryMoving = next(spec.batteryMoves or {}) ~= nil
    for padIndex, pending in pairs(ps.folding) do
        local reason = nil
        if spec.pads[padIndex] ~= pending.variant or g_time > pending.timeout then
            reason = "sdt_padslot_spawnFailed"
        elseif not batteryMoving then
            reason = SprayDronePadSlots.getTakeProblem(self, padIndex)
        end
        if reason ~= nil then
            ps.folding[padIndex] = nil
            setFoldHold(self, padIndex, false)
            SprayDroneSound.noteAction(string.format("sundání dronu z plošiny %d vleku %s zrušeno: %s", padIndex, tostring(self.id), reason))
            helpers().notifyLocal(self, pending.isLocal, reason)
        elseif not batteryMoving and isDroneStowed(self, padIndex) then
            ps.folding[padIndex] = nil
            spawnTaken(self, pending.player, padIndex, pending.isLocal)
        end
    end
    self:raiseActive()
end

-- Příkaz z klienta nebo z místní hry; klient bez serveru ho pošle eventem, server / hostitel ho provede. item = dron k nasazení (PLACE,
-- u Mini do bedny; PLACE_PLATE na rozloženou plošinu Mini). MOVE_BOX / MOVE_PLATE přendá dron Mini bez předmětu.
function SprayDronePadSlots.command(self, command, padIndex, item, player, noEventSend)
    if SprayDronePadSlotEvent.sendEvent(self, command, padIndex, item, noEventSend) then
        return
    end
    if getRoot(self).padSlots == nil then
        return
    end
    local isLocal = not noEventSend
    player = player or g_localPlayer
    if command == SprayDronePadSlotEvent.PLACE or command == SprayDronePadSlotEvent.PLACE_PLATE then
        SprayDronePadSlots.doPlace(self, player, item, padIndex, isLocal, command == SprayDronePadSlotEvent.PLACE_PLATE)
    elseif command == SprayDronePadSlotEvent.TAKE then
        SprayDronePadSlots.doTake(self, player, padIndex, isLocal)
    elseif command == SprayDronePadSlotEvent.MOVE_BOX or command == SprayDronePadSlotEvent.MOVE_PLATE then
        local reason = SprayDronePadSlots.moveMiniTo(self, command == SprayDronePadSlotEvent.MOVE_PLATE)
        if reason ~= nil then
            helpers().notifyLocal(self, isLocal, reason)
        end
    end
end

-- Smí hráč z tohoto spojení plošiny ovládat? Farma, která k vleku smí, a vzdálenost od některé plošiny (COMMAND_DISTANCE). Vrací hráče, nebo nil.
function SprayDronePadSlots.getAllowedPlayer(self, connection)
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    local player = system ~= nil and system:getPlayerByConnection(connection) or nil
    if player == nil or not g_currentMission.accessHandler:canFarmAccess(player.farmId, self) then
        return nil
    end
    local ps = getRoot(self).padSlots
    local x, y, z = helpers().getPlayerPosition(player)
    if ps ~= nil and x ~= nil then
        for _, node in pairs(ps.nodes) do
            local nx, ny, nz = getWorldTranslation(node)
            if MathUtil.vector3Length(x - nx, y - ny, z - nz) <= SprayDronePadSlots.COMMAND_DISTANCE then
                return player
            end
        end
        return nil
    end
    return player
end

---------------------------------------------------------------------------------------------------
-- aktivace (vanilla „Aktivovat objekt“, R): nasadit dron / sundat dron / na Mini přendat dron mezi bednou a plošinou

SprayDronePadSlotsActivatable = {}
local Activatable_mt = Class(SprayDronePadSlotsActivatable)

function SprayDronePadSlotsActivatable.new(vehicle)
    local self = setmetatable({}, Activatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_padslot_place")
    self.distance = math.huge
    return self
end

-- Co by R teď udělalo: "place" (s dronem), "take" (u obsazené plošiny bez dronu), "move" (Mini, prázdné ruce u druhého místa), nebo nil;
-- dál index plošiny, dron a u Mini poloha (true = plošina, false = bedna). Kandidát se hledá nejvýš jednou za CANDIDATE_INTERVAL_MS.
function SprayDronePadSlotsActivatable:evaluate()
    local vehicle = self.vehicle
    local player = g_localPlayer
    local h = helpers()
    self.distance = math.huge
    local spec = getRoot(vehicle)
    local ps = spec.padSlots
    if ps == nil or player == nil or h.isInVehicle(player) or not h.isAlive(vehicle) or g_gui:getIsGuiVisible() then
        return nil
    end
    if VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG then
        return nil
    end
    if not g_currentMission.accessHandler:canFarmAccess(player.farmId, vehicle) then
        return nil
    end
    local x, y, z = h.getPlayerPosition(player)
    if x == nil then
        return nil
    end
    local free, freeDistance, freeOnPlate = SprayDronePadSlots.getNearestPad(vehicle, x, y, z, false)
    local taken, takenDistance, takenOnPlate, move = SprayDronePadSlots.getNearestPad(vehicle, x, y, z, true)
    if free == nil and taken == nil then
        ps.lyingIgnoreUntil = 0
        return nil
    end
    if g_time >= ps.candidateTimer then
        ps.candidateTimer = g_time + SprayDronePadSlots.CANDIDATE_INTERVAL_MS
        ps.candidate, ps.candidateDistance = SprayDronePadSlots.findDrone(vehicle, player, g_time < ps.lyingIgnoreUntil)
    end
    if ps.candidate ~= nil and h.isAlive(ps.candidate) and free ~= nil then
        if h.getHeldNode(player) ~= nil then
            self.distance = 0
        else
            self.distance = SprayDroneLink.aimDistance(math.max(freeDistance - 0.1, 0), SprayDronePadSlots.getSpotNode(vehicle, free, freeOnPlate))
        end
        return "place", free, ps.candidate, freeOnPlate
    end
    ps.candidate = nil
    local takenDrone = taken ~= nil and SprayDroneDrones.getSpec(vehicle, taken) or nil
    if taken ~= nil and not ps.spawning[taken] and not (takenDrone ~= nil and takenDrone.foldHold) and h.getHeldNode(player) == nil then
        self.distance = SprayDroneLink.aimDistance(takenDistance, SprayDronePadSlots.getSpotNode(vehicle, taken, takenOnPlate))
        if move then
            return "move", taken, nil, takenOnPlate
        end
        return "take", taken
    end
    return nil
end

function SprayDronePadSlotsActivatable:getIsActivatable()
    local action, padIndex, _, onPlate = self:evaluate()
    if action == nil then
        return false
    end
    if action == "place" then
        local key = "sdt_padslot_place"
        if onPlate ~= nil then
            key = onPlate and "sdt_padslot_placePlate" or "sdt_padslot_placeBox"
        end
        self.activateText = g_i18n:getText(key)
    elseif action == "move" then
        self.activateText = g_i18n:getText(onPlate and "sdt_padslot_movePlate" or "sdt_padslot_moveBox")
    else
        local variant = getRoot(self.vehicle).pads[padIndex]
        self.activateText = string.format(g_i18n:getText("sdt_padslot_take"), g_i18n:getText("sdt_drone_" .. variant))
    end
    if self.eventId ~= nil then
        g_inputBinding:setActionEventText(self.eventId, self.activateText)
    end
    return true
end

function SprayDronePadSlotsActivatable:registerCustomInput(inputContext)
    local _
    _, self.eventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_OBJECT, self, self.run, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(self.eventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(self.eventId, true)
    g_inputBinding:setActionEventText(self.eventId, self.activateText)
end

function SprayDronePadSlotsActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    self.eventId = nil
end

function SprayDronePadSlotsActivatable:run()
    local vehicle = self.vehicle
    local ps = getRoot(vehicle).padSlots
    ps.candidateTimer = 0
    local action, padIndex, target, onPlate = self:evaluate()
    if action == "place" then
        local reason = SprayDronePadSlots.getPlaceProblem(vehicle, padIndex, SprayDroneItem.getVariant(target))
        if reason ~= nil then
            g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
            return
        end
        SprayDronePadSlots.command(vehicle, onPlate and SprayDronePadSlotEvent.PLACE_PLATE or SprayDronePadSlotEvent.PLACE, padIndex, target)
    elseif action == "take" then
        local reason = SprayDronePadSlots.getTakeProblem(vehicle, padIndex)
        if reason ~= nil then
            g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
            return
        end
        ps.lyingIgnoreUntil = g_time + SprayDronePadSlots.LYING_IGNORE_MS
        ps.candidate = nil
        SprayDronePadSlots.command(vehicle, SprayDronePadSlotEvent.TAKE, padIndex)
    elseif action == "move" then
        local reason = SprayDronePadSlots.getTakeProblem(vehicle, padIndex)
        if reason ~= nil then
            g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
            return
        end
        SprayDronePadSlots.command(vehicle, onPlate and SprayDronePadSlotEvent.MOVE_PLATE or SprayDronePadSlotEvent.MOVE_BOX, padIndex)
    end
end

-- Pořadí volání getDistance / getIsActivatable systémem aktivací neznáme, proto se vzdálenost počítá i tady.
function SprayDronePadSlotsActivatable:getDistance(x, y, z)
    self:evaluate()
    return self.distance or math.huge
end

function SprayDronePadSlotsActivatable:activate() end

function SprayDronePadSlotsActivatable:deactivate() end

function SprayDronePadSlotsActivatable:draw() end
