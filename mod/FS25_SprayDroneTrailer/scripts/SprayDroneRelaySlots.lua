-- Držáky relé tyčí na vleku (docs/PLAN-rele-energie.md, bod 3). Vlek má v i3d sloty `relaySlot{i}` (prázdný uzel) s dítětem
-- `relaySlot{i}_pole` = maketa uložené tyče; počet slotů dává i3d (Mini 1, Middle 2, Max 4). Princip jako kanystry v bedně
-- (SprayDroneToolbox): tyč (vozidlo sdtRelayPole) se při uložení smaže a slot si zapíše její stav (baterie 0..1, konfigurace
-- síly, farma); při vyndání se z něj vyrobí nové vozidlo tyče (VehicleLoadingData) a slot se uvolní až po úspěšném načtení.
--
-- Obsluha (vanilla „Aktivovat objekt“, R) pěšky u slotu:
--  * ULOŽIT: hráč drží složenou tyč v rukou, nebo složená tyč leží do STORE_POLE_DISTANCE od hráče → tyč jde do prvního volného
--    slotu. Rozloženou ani zapnutou tyč uložit nejde, plný vlek hlásí, že není místo.
--  * SAMO: s tyčí v rukou stačí přijít k držáku (do ACTIVATE_DISTANCE) a uloží se bez R. Jen když hráč do té doby byl s tyčí
--    dál než AUTO_REARM_DISTANCE (getAutoStore), ať se právě vyndaná a zvednutá tyč hned nevrátí zpátky.
--  * VYNDAT: jinak R vyndá tyč z nejbližšího obsazeného slotu; tyč se objeví na zemi metr od hráče (dál od vleku). Do rukou ji
--    hráč zvedne sám (vanilla pickUpTarget běží jen u vlastníka rukou, ze serveru to pro vzdáleného hráče nejde).
--  * NABÍJENÍ: uložené tyče nabíjí centrála vleku (SprayDroneStation.updatePower / getPowerShares, pole relays): nenabitá tyč
--    centrálu rozjede jako nenabitá baterie dronu, plně se nabije za SprayDroneRelay.CHARGE_TIME a pálí RELAY_DIESEL_LOAD naftové
--    zátěže jedné baterie dronu; s běžícím čerpadlem jen podílem výkonu jako baterie.
--
-- Změny dělá server (příkaz z klienta jde SprayDroneRelaySlotEvent), sloty se ukládají do savegame a jdou klientům ve stavu
-- vlek (writeState / readState v SprayDroneStation).

SprayDroneRelaySlots = {}

SprayDroneRelaySlots.MAX_SLOTS = 8
SprayDroneRelaySlots.SLOT_BITS = 3
SprayDroneRelaySlots.CONFIG_BITS = 3
SprayDroneRelaySlots.BATTERY_BITS = 8
SprayDroneRelaySlots.ACTIVATE_DISTANCE = 2.5    -- hráč nejvýš tak daleko od uzlu slotu (m, vodorovně)
SprayDroneRelaySlots.ACTIVATE_HEIGHT = 3        -- … a slot nejvýš tolik m nad nebo pod jeho polohou (slot pod plachtou je vysoko)
SprayDroneRelaySlots.STORE_POLE_DISTANCE = 2.5  -- ležící tyč nejvýš tak daleko od hráče (m)
SprayDroneRelaySlots.COMMAND_DISTANCE = 6       -- server: hráč od nejbližšího slotu (m), rezerva na zpoždění polohy
SprayDroneRelaySlots.SPAWN_GAP = 1              -- vyndaná tyč: o tolik m dál od vleku než hráč
SprayDroneRelaySlots.SPAWN_SIDE_MIN = 0.6       -- … a aspoň tolik m za bokem vleku
SprayDroneRelaySlots.LYING_IGNORE_MS = 15000    -- po vyndání se ležící tyče chvíli nenabízejí k uložení (ať jde vyndat další)
SprayDroneRelaySlots.CANDIDATE_INTERVAL_MS = 200
SprayDroneRelaySlots.AUTO_REARM_DISTANCE = 4    -- samouložení se znovu nabije, až je hráč s tyčí v rukou dál než tohle (m)
SprayDroneRelaySlots.AUTO_RETRY_MS = 1500       -- po samouložení se další pokus nejdřív za tohle
SprayDroneRelaySlots.POLE_FILE = "objects/relay/relayPole.xml"
SprayDroneRelaySlots.modDirectory = g_currentModDirectory

local function getSpec(self)
    return self[SprayDroneStation.SPEC_NAME]
end

local function getRelayState(v)
    return SprayDroneRelay ~= nil and v ~= nil and v[SprayDroneRelay.SPEC_NAME] or nil
end

local function isAlive(v)
    return v ~= nil and not v.isDeleted and v.rootNode ~= nil and entityExists(v.rootNode)
end

---------------------------------------------------------------------------------------------------
-- čistá logika (testy tmp/f/test_relayslots.lua)

-- Samouložení: armed = hráč s tyčí v rukou už byl daleko. Vrací nové armed a jestli uložit teď (jen jednou za příchod).
function SprayDroneRelaySlots.getAutoStore(armed, holding, distance)
    if not holding then
        return armed, false
    end
    if distance > SprayDroneRelaySlots.AUTO_REARM_DISTANCE then
        return true, false
    end
    if armed and distance <= SprayDroneRelaySlots.ACTIVATE_DISTANCE then
        return false, true
    end
    return armed, false
end

-- Slot: { occupied, battery (0..1), config (index konfigurace síly), farmId }.
function SprayDroneRelaySlots.newSlot()
    return { occupied = false, battery = 0, config = 1, farmId = 0 }
end

-- První volný slot (slot, ze kterého se právě vyrábí tyč, je pořád obsazený).
function SprayDroneRelaySlots.getFreeSlot(slots)
    for i, slot in ipairs(slots) do
        if not slot.occupied then
            return i
        end
    end
    return nil
end

-- Nejbližší obsazený slot, ze kterého se zrovna nevyrábí tyč. distances[i] = vzdálenost hráče od slotu i (chybí = nekonečno).
function SprayDroneRelaySlots.getTakeSlot(slots, distances, spawning)
    local best, bestDistance = nil, math.huge
    for i, slot in ipairs(slots) do
        local d = distances ~= nil and distances[i] or math.huge
        if slot.occupied and not (spawning ~= nil and spawning[i]) and (best == nil or d < bestDistance) then
            best, bestDistance = i, d
        end
    end
    return best
end

-- Proč tyč s daným stavem nejde uložit (l10n klíč), nebo nil. relay = { unfolded, powered, progress }.
function SprayDroneRelaySlots.getStoreBlock(slots, relay)
    if relay == nil then
        return "sdt_relaySlot_noPole"
    end
    if relay.powered then
        return "sdt_relaySlot_powered"
    end
    if relay.unfolded or (relay.progress or 0) > 0 then
        return "sdt_relaySlot_unfolded"
    end
    if SprayDroneRelaySlots.getFreeSlot(slots) == nil then
        return "sdt_relaySlot_full"
    end
    return nil
end

-- Počet uložených tyčí, které nejsou plně nabité.
function SprayDroneRelaySlots.countCharging(slots)
    local n = 0
    for _, slot in ipairs(slots) do
        if slot.occupied and slot.battery < 1 then
            n = n + 1
        end
    end
    return n
end

-- Nabije uložené tyče o fraction (podíl plné kapacity). Vrací počet tyčí, které se právě dobily do plna.
function SprayDroneRelaySlots.chargeSlots(slots, fraction)
    local filled = 0
    if fraction == nil or fraction <= 0 then
        return 0
    end
    for _, slot in ipairs(slots) do
        if slot.occupied and slot.battery < 1 then
            slot.battery = math.min(slot.battery + fraction, 1)
            if slot.battery >= 1 then
                filled = filled + 1
            end
        end
    end
    return filled
end

-- Kam se vyndaná tyč postaví, v souřadnicích vleku: od hráče o SPAWN_GAP dál od vleku (před / za vlekem po délce, jinak do
-- strany), vždy aspoň SPAWN_SIDE_MIN za obrysem. Bez hráče vedle slotu za bokem. Vrací lx, lz.
function SprayDroneRelaySlots.getSpawnLocal(halfWidth, halfLength, playerX, playerZ, slotX, slotZ)
    local gap, side = SprayDroneRelaySlots.SPAWN_GAP, SprayDroneRelaySlots.SPAWN_SIDE_MIN
    if playerX == nil then
        local sign = (slotX or 0) < 0 and -1 or 1
        return sign * (halfWidth + side + gap), slotZ or 0
    end
    if math.abs(playerZ) > halfLength and math.abs(playerX) <= halfWidth then
        local sign = playerZ < 0 and -1 or 1
        return playerX, sign * math.max(math.abs(playerZ) + gap, halfLength + side)
    end
    local sign = playerX < 0 and -1 or 1
    return sign * math.max(math.abs(playerX) + gap, halfWidth + side), playerZ
end

---------------------------------------------------------------------------------------------------
-- schéma, načtení, uložení, smazání

function SprayDroneRelaySlots.registerSavegamePaths(savegame, saveKey)
    saveKey = saveKey .. ".relaySlots.slot(?)"
    savegame:register(XMLValueType.INT, saveKey .. "#index", "Číslo držáku tyče na vleku (relaySlot{i})")
    savegame:register(XMLValueType.FLOAT, saveKey .. "#battery", "Nabití uložené tyče (0..1)")
    savegame:register(XMLValueType.INT, saveKey .. "#config", "Konfigurace síly uložené tyče (index sprayDroneRelayStrength)", 1)
    savegame:register(XMLValueType.INT, saveKey .. "#farmId", "Farma, které uložená tyč patří")
end

function SprayDroneRelaySlots.load(self, savegame)
    local spec = getSpec(self)
    local rs = { slots = {}, nodes = {}, poleNodes = {}, spawning = {}, shown = {}, candidateTimer = 0, lyingIgnoreUntil = 0 }
    spec.relaySlots = rs
    for i = 1, SprayDroneRelaySlots.MAX_SLOTS do
        local node = SprayDroneStation.getMappedNode(self, "relaySlot" .. i)
        if node == nil then
            break
        end
        rs.nodes[i] = node
        rs.poleNodes[i] = SprayDroneStation.getMappedNode(self, "relaySlot" .. i .. "_pole")
        rs.slots[i] = SprayDroneRelaySlots.newSlot()
    end
    -- skříňka pod plachtou (Middle, Max) je dostupná jen na rozloženém vleku; držák Mini je venku na bedně
    rs.underTarp = SprayDroneStation.getMappedNode(self, "colTarpHingeL") ~= nil
    if #rs.slots == 0 then
        return
    end
    if savegame ~= nil and not savegame.resetVehicles then
        local saveKey = savegame.key .. "." .. SprayDroneStation.MOD_NAME .. ".sprayDroneStation.relaySlots.slot"
        savegame.xmlFile:iterate(saveKey, function(_, slotKey)
            local slot = rs.slots[savegame.xmlFile:getValue(slotKey .. "#index", 0)]
            local battery = savegame.xmlFile:getValue(slotKey .. "#battery")
            if slot ~= nil and battery ~= nil then
                slot.occupied = true
                slot.battery = math.clamp(battery, 0, 1)
                slot.config = math.max(savegame.xmlFile:getValue(slotKey .. "#config", 1), 1)
                slot.farmId = savegame.xmlFile:getValue(slotKey .. "#farmId", self:getOwnerFarmId())
            end
        end)
    end
    SprayDroneRelaySlots.updateVisuals(self)
    if self.isClient and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        rs.activatable = SprayDroneRelaySlotsActivatable.new(self)
        g_currentMission.activatableObjectsSystem:addActivatable(rs.activatable)
    end
end

function SprayDroneRelaySlots.save(self, xmlFile, key)
    local rs = getSpec(self).relaySlots
    if rs == nil then
        return
    end
    local n = 0
    for i, slot in ipairs(rs.slots) do
        if slot.occupied then
            local slotKey = string.format("%s.relaySlots.slot(%d)", key, n)
            xmlFile:setValue(slotKey .. "#index", i)
            xmlFile:setValue(slotKey .. "#battery", slot.battery)
            xmlFile:setValue(slotKey .. "#config", slot.config)
            xmlFile:setValue(slotKey .. "#farmId", slot.farmId)
            n = n + 1
        end
    end
end

function SprayDroneRelaySlots.delete(self)
    local spec = getSpec(self)
    local rs = spec ~= nil and spec.relaySlots or nil
    if rs ~= nil and rs.activatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(rs.activatable)
        rs.activatable = nil
    end
end

-- Maketa uložené tyče je vidět jen u obsazeného slotu.
function SprayDroneRelaySlots.updateVisuals(self)
    local rs = getSpec(self).relaySlots
    for i, slot in ipairs(rs.slots) do
        local node = rs.poleNodes[i]
        if node ~= nil and rs.shown[i] ~= slot.occupied then
            rs.shown[i] = slot.occupied
            setVisibility(node, slot.occupied)
        end
    end
end

---------------------------------------------------------------------------------------------------
-- síť (voláno z writeState / readState v SprayDroneStation; počet slotů dává i3d, na serveru i klientu stejný)

function SprayDroneRelaySlots.writeState(self, streamId)
    local rs = getSpec(self).relaySlots
    for _, slot in ipairs(rs.slots) do
        if streamWriteBool(streamId, slot.occupied) then
            streamWriteUIntN(streamId, math.floor(math.clamp(slot.battery, 0, 1) * 255 + 0.5), SprayDroneRelaySlots.BATTERY_BITS)
            streamWriteUIntN(streamId, math.clamp(slot.config - 1, 0, 2 ^ SprayDroneRelaySlots.CONFIG_BITS - 1), SprayDroneRelaySlots.CONFIG_BITS)
        end
    end
end

function SprayDroneRelaySlots.readState(self, streamId)
    local rs = getSpec(self).relaySlots
    for _, slot in ipairs(rs.slots) do
        slot.occupied = streamReadBool(streamId)
        if slot.occupied then
            slot.battery = streamReadUIntN(streamId, SprayDroneRelaySlots.BATTERY_BITS) / 255
            slot.config = streamReadUIntN(streamId, SprayDroneRelaySlots.CONFIG_BITS) + 1
        end
    end
    SprayDroneRelaySlots.updateVisuals(self)
end

local function raiseDirty(self)
    self:raiseDirtyFlags(getSpec(self).dirtyFlag)
end

---------------------------------------------------------------------------------------------------
-- nabíjení (server, z SprayDroneStation.updatePower)

-- Kolik uložených tyčí chce proud (pro getPowerShares).
function SprayDroneRelaySlots.getNumCharging(self)
    local rs = getSpec(self).relaySlots
    return rs ~= nil and SprayDroneRelaySlots.countCharging(rs.slots) or 0
end

-- Běžící centrála nabíjí uložené tyče: dt v ms, factor = podíl výkonu (getPowerShares.chargeFactor).
function SprayDroneRelaySlots.charge(self, dt, factor)
    local rs = getSpec(self).relaySlots
    if rs == nil or SprayDroneRelay == nil then
        return
    end
    local fraction = dt * (factor or 1) / SprayDroneRelay.CHARGE_TIME
    if SprayDroneRelaySlots.chargeSlots(rs.slots, fraction) > 0 then
        raiseDirty(self)
    end
end

---------------------------------------------------------------------------------------------------
-- hledání tyče k uložení (klient i server)

local function getPlayerPosition(player)
    if player == nil or player.getPosition == nil then
        return nil
    end
    return player:getPosition()
end

local function isInVehicle(player)
    return player ~= nil and player.getCurrentVehicle ~= nil and player:getCurrentVehicle() ~= nil
end

local function getHeldNode(player)
    local hands = player ~= nil and player.hands or nil
    local handsSpec = hands ~= nil and hands.spec_hands or nil
    return handsSpec ~= nil and handsSpec.heldItemNode or nil
end

local function getPlayers()
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    return system ~= nil and system.players or {}
end

-- Hráč, který tyč drží v rukou (nebo nil).
local function getHolder(pole)
    for _, player in ipairs(getPlayers()) do
        local node = getHeldNode(player)
        if node ~= nil then
            if node == pole.rootNode then
                return player
            end
            for _, component in ipairs(pole.components or {}) do
                if component.node == node then
                    return player
                end
            end
        end
    end
    return nil
end

local function isMounted(v)
    return v.dynamicMountObject ~= nil or v.tensionMountObject ~= nil
        or (v.getDynamicMountObject ~= nil and v:getDynamicMountObject() ~= nil)
end

-- Vzdálenosti hráče od slotů (seznam) a nejmenší z nich.
function SprayDroneRelaySlots.getSlotDistances(self, x, y, z)
    local rs = getSpec(self).relaySlots
    local distances, best = {}, math.huge
    for i, node in ipairs(rs.nodes) do
        local nx, ny, nz = getWorldTranslation(node)
        distances[i] = math.abs(y - ny) <= SprayDroneRelaySlots.ACTIVATE_HEIGHT and MathUtil.vector2Length(x - nx, z - nz) or math.huge
        best = math.min(best, distances[i])
    end
    return distances, best
end

-- Tyč, kterou hráč drží v rukou, nebo nil.
function SprayDroneRelaySlots.getHeldPole(player)
    local held = getHeldNode(player)
    if held == nil or g_currentMission.getNodeObject == nil then
        return nil
    end
    local object = g_currentMission:getNodeObject(held)
    if getRelayState(object) ~= nil and isAlive(object) then
        return object
    end
    return nil
end

-- Tyč, kterou hráč u vleku uloží: drží-li tyč v rukou, ta; jinak nejbližší složená ležící do STORE_POLE_DISTANCE (s ignoreLying
-- se ležící nehledají). Vrací tyč a vzdálenost od hráče, nebo nil.
function SprayDroneRelaySlots.findStorePole(self, player, ignoreLying)
    local x, y, z = getPlayerPosition(player)
    if x == nil or SprayDroneRelay == nil then
        return nil
    end
    if getHeldNode(player) ~= nil then
        local pole = SprayDroneRelaySlots.getHeldPole(player)
        return pole, pole ~= nil and 0 or nil
    end
    if ignoreLying then
        return nil
    end
    local best, bestDistance = nil, SprayDroneRelaySlots.STORE_POLE_DISTANCE
    local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, v in ipairs(vehicles) do
        local state = getRelayState(v)
        if state ~= nil and isAlive(v) and not state.unfolded and state.progress <= 0 and not isMounted(v) then
            local vx, vy, vz = getWorldTranslation(v.rootNode)
            local d = MathUtil.vector3Length(x - vx, y - vy, z - vz)
            if d <= bestDistance then
                best, bestDistance = v, d
            end
        end
    end
    return best, best ~= nil and bestDistance or nil
end

---------------------------------------------------------------------------------------------------
-- příkazy (server)

local function notifyLocal(self, isLocal, key)
    if key ~= nil and isLocal and self.isClient and g_currentMission ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(key), 2500)
    end
end

-- Cesta k xml tyče, jen když je v obchodě (VehicleLoadingData:setFilename hledá storeItem podle xml).
function SprayDroneRelaySlots.getPoleFilename()
    if g_storeManager == nil then
        return nil
    end
    local path = (SprayDroneRelaySlots.modDirectory or "") .. SprayDroneRelaySlots.POLE_FILE
    if g_storeManager:getItemByXMLFilename(path) ~= nil then
        return path
    end
    local tail = string.lower(SprayDroneRelaySlots.POLE_FILE)
    for key, item in pairs(g_storeManager.xmlFilenameToItem or {}) do
        if string.sub(string.lower(key), -#tail) == tail then
            return item.xmlFilename or key
        end
    end
    return nil
end

-- ULOŽIT: tyč (drží ji hráč, nebo leží u něj) se smaže a její stav jde do prvního volného slotu.
function SprayDroneRelaySlots.doStore(self, player, pole, isLocal)
    local rs = getSpec(self).relaySlots
    local state = getRelayState(pole)
    if state == nil or not isAlive(pole) then
        return
    end
    local reason = SprayDroneRelaySlots.getStoreBlock(rs.slots, state)
    if reason == nil and (isMounted(pole) or (pole.getIsControlled ~= nil and pole:getIsControlled())) then
        reason = "sdt_relaySlot_noPole"
    end
    local holder = getHolder(pole)
    if reason == nil and holder ~= nil and holder ~= player then
        reason = "sdt_relaySlot_noPole"
    end
    if reason == nil and holder == nil then
        local px, py, pz = getPlayerPosition(player)
        local vx, vy, vz = getWorldTranslation(pole.rootNode)
        if px ~= nil and MathUtil.vector3Length(px - vx, py - vy, pz - vz) > SprayDroneRelaySlots.STORE_POLE_DISTANCE + 1.5 then
            reason = "sdt_relaySlot_noPole"
        end
    end
    if reason ~= nil then
        notifyLocal(self, isLocal, reason)
        return
    end
    local index = SprayDroneRelaySlots.getFreeSlot(rs.slots)
    local slot = rs.slots[index]
    slot.occupied = true
    slot.battery = SprayDroneRelay.getBatteryFraction(pole)
    slot.config = pole.configurations ~= nil and pole.configurations[SprayDroneStation.RELAY_CONFIG] or 1
    local farmId = pole.getOwnerFarmId ~= nil and pole:getOwnerFarmId() or nil
    slot.farmId = (farmId ~= nil and farmId ~= 0) and farmId or self:getOwnerFarmId()
    if holder ~= nil and holder.hands ~= nil and holder.hands.dropHeldItem ~= nil then
        holder.hands:dropHeldItem()
    end
    pole:delete()
    raiseDirty(self)
    self:raiseActive()
    SprayDroneRelaySlots.updateVisuals(self)
end

-- VYNDAT: ze slotu se vyrobí tyč (s konfigurací síly a baterií slotu) metr od hráče; slot se uvolní až po úspěšném načtení.
function SprayDroneRelaySlots.doTake(self, player, index, isLocal)
    local rs = getSpec(self).relaySlots
    local slot = rs.slots[index]
    if slot == nil or not slot.occupied or rs.spawning[index] then
        return
    end
    local filename = SprayDroneRelaySlots.getPoleFilename()
    if filename == nil then
        Logging.warning("SDT: tyč nejde vyrobit (chybí %s v obchodě)", SprayDroneRelaySlots.POLE_FILE)
        notifyLocal(self, isLocal, "sdt_relaySlot_spawnFailed")
        return
    end
    local slotSystem = g_currentMission.slotSystem
    if slotSystem ~= nil and SlotSystem ~= nil and SlotSystem.LIMITED_OBJECT_PALLET ~= nil
        and not slotSystem:getCanAddLimitedObjects(SlotSystem.LIMITED_OBJECT_PALLET, 1) then
        notifyLocal(self, isLocal, "sdt_toolbox_spawnLimit")
        return
    end
    local data = VehicleLoadingData.new()
    data:setFilename(filename)
    if not data.isValid then
        notifyLocal(self, isLocal, "sdt_relaySlot_spawnFailed")
        return
    end
    local root = self.rootNode
    local halfWidth = (self.size ~= nil and self.size.width or 2.5) / 2
    local halfLength = (self.size ~= nil and self.size.length or 5) / 2
    local sx, _, sz = localToLocal(rs.nodes[index], root, 0, 0, 0)
    local plx, plz = nil, nil
    local px, py, pz = getPlayerPosition(player)
    if px ~= nil then
        plx, _, plz = worldToLocal(root, px, py, pz)
    end
    local lx, lz = SprayDroneRelaySlots.getSpawnLocal(halfWidth, halfLength, plx, plz, sx, sz)
    local x, _, z = localToWorld(root, lx, 0, lz)
    local y = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.1
    local dx, _, dz = localDirectionToWorld(root, 0, 0, 1)
    local config = slot.config
    local battery = slot.battery
    local farmId = slot.farmId ~= 0 and slot.farmId or self:getOwnerFarmId()
    data:setPosition(x, y, z)
    data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(farmId)
    data:setConfigurations({ [SprayDroneStation.RELAY_CONFIG] = config })
    data:setBoughtConfigurations({ [SprayDroneStation.RELAY_CONFIG] = { [config] = true } })
    rs.spawning[index] = true
    data:load(function(_, vehicles, loadState)
        rs.spawning[index] = nil
        local pole = vehicles ~= nil and vehicles[1] or nil
        if loadState ~= VehicleLoadingState.OK or pole == nil then
            Logging.warning("SDT: tyč se nepodařilo načíst (%s)", tostring(filename))
            for _, v in ipairs(vehicles or {}) do
                v:delete()
            end
            notifyLocal(self, isLocal, "sdt_relaySlot_spawnFailed")
            return
        end
        local unit = SprayDroneRelay.getBatteryUnit(pole)
        if unit ~= nil then
            local target = battery * pole:getFillUnitCapacity(unit)
            local delta = target - pole:getFillUnitFillLevel(unit)
            if math.abs(delta) > 0.0001 then
                pole:addFillUnitFillLevel(farmId, unit, delta, FillType.ELECTRICCHARGE, ToolType.UNDEFINED, nil)
            end
        end
        if slot.occupied then
            slot.occupied, slot.battery, slot.config, slot.farmId = false, 0, 1, 0
        end
        if isAlive(self) then
            raiseDirty(self)
            SprayDroneRelaySlots.updateVisuals(self)
        end
    end)
end

-- Příkaz z klienta nebo z místní hry; klient bez serveru ho pošle eventem, server / hostitel ho provede. pole = tyč k uložení
-- (STORE), index = slot (TAKE).
function SprayDroneRelaySlots.command(self, command, pole, index, player, noEventSend)
    if SprayDroneRelaySlotEvent.sendEvent(self, command, pole, index, noEventSend) then
        return
    end
    local rs = getSpec(self).relaySlots
    if rs == nil or #rs.slots == 0 or (rs.underTarp and self.getIsUnfolded ~= nil and not self:getIsUnfolded()) then
        return
    end
    local isLocal = not noEventSend
    player = player or g_localPlayer
    if command == SprayDroneRelaySlotEvent.STORE then
        SprayDroneRelaySlots.doStore(self, player, pole, isLocal)
    elseif command == SprayDroneRelaySlotEvent.TAKE then
        SprayDroneRelaySlots.doTake(self, player, index, isLocal)
    end
end

-- Smí hráč z tohoto spojení držáky ovládat? Farma, která k vleku smí, a vzdálenost od nejbližšího slotu (COMMAND_DISTANCE;
-- polohu, kterou server nezná, nezamítá). Vrací hráče, nebo nil.
function SprayDroneRelaySlots.getAllowedPlayer(self, connection)
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    local player = system ~= nil and system:getPlayerByConnection(connection) or nil
    if player == nil or not g_currentMission.accessHandler:canFarmAccess(player.farmId, self) then
        return nil
    end
    local rs = getSpec(self).relaySlots
    local x, y, z = getPlayerPosition(player)
    if rs ~= nil and x ~= nil then
        local _, best = SprayDroneRelaySlots.getSlotDistances(self, x, y, z)
        if best > SprayDroneRelaySlots.COMMAND_DISTANCE then
            return nil
        end
    end
    return player
end

---------------------------------------------------------------------------------------------------
-- aktivace (vanilla „Aktivovat objekt“, R): uložit tyč / vyndat tyč

SprayDroneRelaySlotsActivatable = {}
local Activatable_mt = Class(SprayDroneRelaySlotsActivatable)

function SprayDroneRelaySlotsActivatable.new(vehicle)
    local self = setmetatable({}, Activatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_relaySlot_store")
    self.distance = math.huge
    return self
end

-- Co by R teď udělalo: "store" (s tyčí), "take" (se slotem), nebo nil. Kandidát se hledá nejvýš jednou za CANDIDATE_INTERVAL_MS.
function SprayDroneRelaySlotsActivatable:evaluate()
    local vehicle = self.vehicle
    local player = g_localPlayer
    self.distance = math.huge
    local spec = getSpec(vehicle)
    local rs = spec ~= nil and spec.relaySlots or nil
    if rs == nil or #rs.slots == 0 or player == nil or isInVehicle(player) or not isAlive(vehicle) or g_gui:getIsGuiVisible() then
        return nil
    end
    if VehiclePropertyState ~= nil and vehicle.propertyState == VehiclePropertyState.SHOP_CONFIG then
        return nil
    end
    if not g_currentMission.accessHandler:canFarmAccess(player.farmId, vehicle) then
        return nil
    end
    if rs.underTarp and vehicle.getIsUnfolded ~= nil and not vehicle:getIsUnfolded() then
        return nil
    end
    local x, y, z = getPlayerPosition(player)
    if x == nil then
        return nil
    end
    local distances, best = SprayDroneRelaySlots.getSlotDistances(vehicle, x, y, z)
    SprayDroneRelaySlots.updateAutoStore(vehicle, rs, player, best)
    if best > SprayDroneRelaySlots.ACTIVATE_DISTANCE then
        rs.lyingIgnoreUntil = 0
        return nil
    end
    if g_time >= rs.candidateTimer then
        rs.candidateTimer = g_time + SprayDroneRelaySlots.CANDIDATE_INTERVAL_MS
        rs.candidate, rs.candidateDistance = SprayDroneRelaySlots.findStorePole(vehicle, player, g_time < rs.lyingIgnoreUntil)
    end
    if rs.candidate ~= nil and isAlive(rs.candidate) then
        self.distance = math.max((rs.candidateDistance or 0) - 0.1, 0)
        return "store", rs.candidate
    end
    rs.candidate = nil
    local index = SprayDroneRelaySlots.getTakeSlot(rs.slots, distances, rs.spawning)
    if index ~= nil then
        self.distance = distances[index]
        return "take", index
    end
    return nil
end

-- Tyč v rukou místního hráče u držáku se uloží sama (getAutoStore); co uložit nejde (rozložená, zapnutá, plno), jen jednou ohlásí.
function SprayDroneRelaySlots.updateAutoStore(vehicle, rs, player, best)
    local pole = SprayDroneRelaySlots.getHeldPole(player)
    local armed, store = SprayDroneRelaySlots.getAutoStore(rs.autoArmed, pole ~= nil, best)
    rs.autoArmed = armed
    if not store then
        return
    end
    if g_time < (rs.autoRetryTime or 0) then
        rs.autoArmed = true
        return
    end
    rs.autoRetryTime = g_time + SprayDroneRelaySlots.AUTO_RETRY_MS
    local reason = SprayDroneRelaySlots.getStoreBlock(rs.slots, getRelayState(pole))
    if reason ~= nil then
        g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
        return
    end
    rs.candidate = nil
    SprayDroneRelaySlots.command(vehicle, SprayDroneRelaySlotEvent.STORE, pole, 1)
end

function SprayDroneRelaySlotsActivatable:getIsActivatable()
    local action, target = self:evaluate()
    if action == nil then
        return false
    end
    if action == "store" then
        self.activateText = g_i18n:getText("sdt_relaySlot_store")
    else
        local slot = getSpec(self.vehicle).relaySlots.slots[target]
        self.activateText = string.format(g_i18n:getText("sdt_relaySlot_take"), math.floor(slot.battery * 100 + 0.5))
    end
    if self.eventId ~= nil then
        g_inputBinding:setActionEventText(self.eventId, self.activateText)
    end
    return true
end

function SprayDroneRelaySlotsActivatable:registerCustomInput(inputContext)
    local _
    _, self.eventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_OBJECT, self, self.run, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(self.eventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(self.eventId, true)
    g_inputBinding:setActionEventText(self.eventId, self.activateText)
end

function SprayDroneRelaySlotsActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    self.eventId = nil
end

function SprayDroneRelaySlotsActivatable:run()
    local vehicle = self.vehicle
    local rs = getSpec(vehicle).relaySlots
    rs.candidateTimer = 0
    local action, target = self:evaluate()
    if action == "store" then
        local reason = SprayDroneRelaySlots.getStoreBlock(rs.slots, getRelayState(target))
        if reason ~= nil then
            g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
            return
        end
        SprayDroneRelaySlots.command(vehicle, SprayDroneRelaySlotEvent.STORE, target, 1)
    elseif action == "take" then
        rs.lyingIgnoreUntil = g_time + SprayDroneRelaySlots.LYING_IGNORE_MS
        rs.candidate = nil
        SprayDroneRelaySlots.command(vehicle, SprayDroneRelaySlotEvent.TAKE, nil, target)
    end
end

-- Pořadí volání getDistance / getIsActivatable systémem aktivací neznáme, proto se vzdálenost počítá i tady.
function SprayDroneRelaySlotsActivatable:getDistance(x, y, z)
    self:evaluate()
    return self.distance or math.huge
end

function SprayDroneRelaySlotsActivatable:activate() end

function SprayDroneRelaySlotsActivatable:deactivate() end

function SprayDroneRelaySlotsActivatable:draw() end
