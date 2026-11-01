-- Šachty nabíječky (vlek Mini / Middle / Max, kufr) jako sloty pro bateriové předměty (docs/PLAN-airasi-kufr.md F4, docs/NAVRH-dron-predmet.md kap. 13).
-- Šachta = slot poolu spec.batteries (battery.slot); prázdná šachta = baterie s tím slotem v poolu není, pool má proměnný počet (SprayDroneStation.setBatteryCount,
-- addBattery, removeBattery). R s baterií v ruce u šachty ji vloží (předmět se smaže, nabití jde do poolu), R bez ničeho u obsazené šachty ji vyndá (vyrobí se
-- předmět s nabitím, VehicleLoadingData, vzor SprayDronePadSlots). Velikost musí sedět s typem baterií vozidla (spec.batteryVariant: S / M / L u vleku, C / P
-- u kufru). Šachty jsou přístupné jen na rozloženém vleku / s otevřeným víkem kufru. U kufru se vyndává i baterie z dronu, který v kufru sedí (šachty
-- caseBatterySlot, caseBatterySlot2), a jen když na ni hráč míří (CASE_AIM_RADIUS) nebo u ní stojí do CASE_TAKE_DISTANCE; jinak R ovládá víko (SprayDroneCase). Za letu, při výměně a při skládání dronu se baterie z dronu vyndat nedá.
-- Změny dělá server (příkaz z klienta jde SprayDroneBatterySlotEvent), pool jde klientům ve stavu vozidla (SprayDroneStation.writeState).

SprayDroneBatterySlots = {}

SprayDroneBatterySlots.ACTIVATE_DISTANCE = 2       -- hráč nejvýš tak daleko od šachty (m, vodorovně)
SprayDroneBatterySlots.ACTIVATE_HEIGHT = 2.5       -- … a šachta nejvýš tolik m nad nebo pod hráčem
SprayDroneBatterySlots.CASE_TAKE_DISTANCE = 0.6    -- u kufru R vyndá baterii, když u ní hráč stojí (m, vodorovně) …
SprayDroneBatterySlots.CASE_AIM_RADIUS = 0.25      -- … nebo na ni míří (m kolem uzlu); jinak R otevírá a zavírá víko
SprayDroneBatterySlots.STORE_DISTANCE = 2.5        -- ležící baterie nejvýš tak daleko od hráče (m)
SprayDroneBatterySlots.COMMAND_DISTANCE = 6        -- server: hráč od šachty (m), rezerva na zpoždění polohy
SprayDroneBatterySlots.ITEM_FILE = "objects/battery/battery%s.xml"
SprayDroneBatterySlots.modDirectory = g_currentModDirectory

local function getRoot(self)
    return SprayDroneDrones.getRoot(self)
end

local function helpers()
    return SprayDroneRelaySlots.helpers
end

---------------------------------------------------------------------------------------------------
-- čistá logika (offline test tools/test_batteries.py)

-- Cíl příkazu: 1..MAX_BATTERY_SLOTS = šachta, MAX_BATTERY_SLOTS + d = baterie v dronu d.
function SprayDroneBatterySlots.getDroneTarget(droneIndex)
    return SprayDroneStation.MAX_BATTERY_SLOTS + droneIndex
end

function SprayDroneBatterySlots.getTargetDrone(target)
    if target > SprayDroneStation.MAX_BATTERY_SLOTS then
        return target - SprayDroneStation.MAX_BATTERY_SLOTS
    end
    return nil
end

-- Index baterie v poolu, kterou cíl drží, nebo nil.
function SprayDroneBatterySlots.getTargetBattery(self, target)
    local droneIndex = SprayDroneBatterySlots.getTargetDrone(target)
    if droneIndex ~= nil then
        local droneSpec = SprayDroneDrones.getSpec(self, droneIndex)
        return droneSpec ~= nil and droneSpec.hasDrone and droneSpec.droneBattery or nil
    end
    return SprayDroneDrones.runAs(self, 1, SprayDroneStation.getBatteryInSlot, target)
end

-- Proč teď k šachtám nejde sáhnout (l10n klíč), nebo nil: složený vlek, zavřený kufr.
function SprayDroneBatterySlots.getAccessProblem(self)
    if self.getIsUnfolded ~= nil and not self:getIsUnfolded() then
        return getRoot(self).portable and "sdt_batteryslot_caseClosed" or "sdt_batteryslot_folded"
    end
    return nil
end

-- Proč baterii velikosti size nejde vložit do šachty slot (nil = do první volné), nebo nil.
function SprayDroneBatterySlots.getPutProblem(self, size, slot)
    local spec = getRoot(self)
    local problem = SprayDroneBatterySlots.getAccessProblem(self)
    if problem ~= nil then
        return problem
    end
    if size ~= spec.batteryVariant then
        return "sdt_batteryslot_wrongSize"
    end
    if #spec.batteries >= spec.numBatterySlots then
        return "sdt_batteryslot_full"
    end
    if slot ~= nil and (slot < 1 or slot > spec.numBatterySlots or SprayDroneBatterySlots.getTargetBattery(self, slot) ~= nil) then
        return "sdt_batteryslot_occupied"
    end
    return nil
end

-- Sedí dron v klidu doma, takže z něj jde baterie vyndat (ne za letu, při servisu, výměně ani skládání ke sundání)?
function SprayDroneBatterySlots.getIsDroneIdle(droneSpec)
    return droneSpec ~= nil and droneSpec.hasDrone and droneSpec.isLinked and droneSpec.state == SprayDroneStation.STATE_PARKED
        and not droneSpec.missionActive and not droneSpec.isSwapping and not droneSpec.foldHold
end

-- Proč z cíle nejde baterie vyndat (l10n klíč), nebo nil.
function SprayDroneBatterySlots.getTakeProblem(self, target)
    local spec = getRoot(self)
    local problem = SprayDroneBatterySlots.getAccessProblem(self)
    if problem ~= nil then
        return problem
    end
    if SprayDroneBatterySlots.getTargetBattery(self, target) == nil then
        return "sdt_batteryslot_empty"
    end
    local bs = spec.batterySlots
    if next(spec.batteryMoves or {}) ~= nil or (bs ~= nil and bs.spawning) then
        return "sdt_batteryslot_busy"
    end
    local droneIndex = SprayDroneBatterySlots.getTargetDrone(target)
    if droneIndex ~= nil and not SprayDroneBatterySlots.getIsDroneIdle(SprayDroneDrones.getSpec(self, droneIndex)) then
        return "sdt_batteryslot_droneBusy"
    end
    return nil
end

---------------------------------------------------------------------------------------------------
-- načtení, smazání

function SprayDroneBatterySlots.load(self)
    local spec = getRoot(self)
    local bs = { nodes = {}, spawning = false }
    for i = 1, spec.numBatterySlots do
        bs.nodes[i] = spec.batterySlotDeck ~= nil and spec.batterySlotDeck[i] or nil
    end
    if spec.portable then
        for i = 1, spec.numBatterySlots do
            bs.nodes[i] = bs.nodes[i] or SprayDroneStation.getMappedNode(self, i == 1 and "caseBatterySlot" or ("caseBatterySlot" .. i))
        end
    end
    spec.batterySlots = bs
    if self.isClient and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        bs.activatable = SprayDroneBatterySlotsActivatable.new(self)
        g_currentMission.activatableObjectsSystem:addActivatable(bs.activatable)
    end
end

function SprayDroneBatterySlots.delete(self)
    local spec = self[SprayDroneStation.SPEC_NAME] ~= nil and getRoot(self) or nil
    local bs = spec ~= nil and spec.batterySlots or nil
    if bs ~= nil and bs.activatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(bs.activatable)
        bs.activatable = nil
    end
end

---------------------------------------------------------------------------------------------------
-- hledání (klient i server)

-- Bateriový předmět v rukou hráče, nebo nil.
function SprayDroneBatterySlots.getHeldBattery(player)
    local h = helpers()
    local held = h.getHeldNode(player)
    if held == nil or g_currentMission.getNodeObject == nil then
        return nil
    end
    local object = g_currentMission:getNodeObject(held)
    if SprayDroneItem.getBatterySize(object) ~= nil and h.isAlive(object) then
        return object
    end
    return nil
end

local function getNodeDistance(node, x, y, z)
    if node == nil or not entityExists(node) then
        return math.huge
    end
    local nx, ny, nz = getWorldTranslation(node)
    if math.abs(y - ny) > SprayDroneBatterySlots.ACTIVATE_HEIGHT then
        return math.huge
    end
    return MathUtil.vector2Length(x - nx, z - nz)
end

-- Nejbližší šachta do ACTIVATE_DISTANCE: occupied true = obsazená, false = volná, nil = libovolná. Vrací číslo šachty a vzdálenost, nebo nil.
function SprayDroneBatterySlots.getNearestShaft(self, x, y, z, occupied)
    local bs = getRoot(self).batterySlots
    local best, bestDistance = nil, SprayDroneBatterySlots.ACTIVATE_DISTANCE
    for i, node in pairs(bs.nodes) do
        local full = SprayDroneBatterySlots.getTargetBattery(self, i) ~= nil
        if occupied == nil or full == occupied then
            local d = getNodeDistance(node, x, y, z)
            if d <= bestDistance then
                best, bestDistance = i, d
            end
        end
    end
    return best, best ~= nil and bestDistance or nil
end

-- Smí R u kufru sáhnout po baterii v uzlu node, distance m od hráče? Jen když na ni hráč míří nebo u ní stojí (jinak patří R víku).
function SprayDroneBatterySlots.getIsCaseReach(node, distance)
    return distance <= SprayDroneBatterySlots.CASE_TAKE_DISTANCE
        or (SprayDroneLink ~= nil and SprayDroneLink.isAimedAt ~= nil and SprayDroneLink.isAimedAt(node, SprayDroneBatterySlots.CASE_AIM_RADIUS))
end

-- Co by R bez ničeho v ruce vyndalo: nejbližší obsazená šachta, u kufru i baterie v dronu doma (u vleku ne: tam R u plošiny sundává dron).
-- Vrací cíl a vzdálenost, nebo nil.
function SprayDroneBatterySlots.getNearestTake(self, x, y, z)
    local spec = getRoot(self)
    local best, bestDistance = SprayDroneBatterySlots.getNearestShaft(self, x, y, z, true)
    if spec.portable then
        if best ~= nil and not SprayDroneBatterySlots.getIsCaseReach(spec.batterySlots.nodes[best], bestDistance) then
            best, bestDistance = nil, nil
        end
        for d = 1, spec.numDrones or 1 do
            local droneSpec = SprayDroneDrones.getSpec(self, d)
            if droneSpec ~= nil and droneSpec.droneBattery ~= nil and SprayDroneBatterySlots.getIsDroneIdle(droneSpec) then
                local distance = getNodeDistance(droneSpec.batterySlotDrone, x, y, z)
                if distance <= (bestDistance or SprayDroneBatterySlots.ACTIVATE_DISTANCE)
                    and SprayDroneBatterySlots.getIsCaseReach(droneSpec.batterySlotDrone, distance) then
                    best, bestDistance = SprayDroneBatterySlots.getDroneTarget(d), distance
                end
            end
        end
    end
    return best, bestDistance
end

-- Světová poloha cíle (šachta nebo baterie v dronu), nebo nil.
local function getTargetNode(self, target)
    local droneIndex = SprayDroneBatterySlots.getTargetDrone(target)
    if droneIndex ~= nil then
        local droneSpec = SprayDroneDrones.getSpec(self, droneIndex)
        return droneSpec ~= nil and droneSpec.batterySlotDrone or nil
    end
    return getRoot(self).batterySlots.nodes[target]
end

---------------------------------------------------------------------------------------------------
-- příkazy (server)

-- Cesta k xml bateriového předmětu, jen když je v obchodě (VehicleLoadingData:setFilename hledá storeItem podle xml).
function SprayDroneBatterySlots.getItemFilename(size)
    if g_storeManager == nil then
        return nil
    end
    local relative = string.format(SprayDroneBatterySlots.ITEM_FILE, size)
    local path = (SprayDroneBatterySlots.modDirectory or "") .. relative
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

local function getSpawnProblem(size)
    local filename = size ~= nil and SprayDroneBatterySlots.getItemFilename(size) or nil
    if filename == nil then
        Logging.warning("SDT: baterie %s nejde vyrobit (chybí %s v obchodě)", tostring(size), string.format(SprayDroneBatterySlots.ITEM_FILE, tostring(size)))
        return "sdt_batteryslot_spawnFailed"
    end
    local slotSystem = g_currentMission.slotSystem
    if slotSystem ~= nil and SlotSystem ~= nil and SlotSystem.LIMITED_OBJECT_PALLET ~= nil
        and not slotSystem:getCanAddLimitedObjects(SlotSystem.LIMITED_OBJECT_PALLET, 1) then
        return "sdt_toolbox_spawnLimit"
    end
    return nil, filename
end

-- VLOŽIT: baterie (drží ji hráč, nebo leží u něj) se smaže a její nabití jde do šachty slot (nil / obsazená = první volná).
function SprayDroneBatterySlots.doPut(self, player, item, slot, isLocal)
    local h = helpers()
    local spec = getRoot(self)
    local size = SprayDroneItem.getBatterySize(item)
    if size == nil or not h.isAlive(item) then
        return
    end
    if slot == nil or slot < 1 or slot > spec.numBatterySlots or SprayDroneBatterySlots.getTargetBattery(self, slot) ~= nil then
        slot = SprayDroneDrones.runAs(self, 1, SprayDroneStation.getFreeBatterySlot)
    end
    local reason = SprayDroneBatterySlots.getPutProblem(self, size, slot)
    if reason == nil and (h.isMounted(item) or (item.getIsControlled ~= nil and item:getIsControlled())) then
        reason = "sdt_batteryslot_noBattery"
    end
    local holder = h.getHolder(item)
    if reason == nil and holder ~= nil and holder ~= player then
        reason = "sdt_batteryslot_noBattery"
    end
    if reason == nil and holder == nil then
        local px, py, pz = h.getPlayerPosition(player)
        local vx, vy, vz = getWorldTranslation(item.rootNode)
        if px ~= nil and MathUtil.vector3Length(px - vx, py - vy, pz - vz) > SprayDroneBatterySlots.STORE_DISTANCE + 1.5 then
            reason = "sdt_batteryslot_noBattery"
        end
    end
    if reason ~= nil then
        h.notifyLocal(self, isLocal, reason)
        return
    end
    local level = SprayDroneItem.getBatteryLevel(item)
    SprayDroneStation.addBattery(self, level * spec.batteryCapacity, slot)
    SprayDroneSound.noteAction(string.format("baterie %s (id %s, %.0f %%) vložena do šachty %d vozidla %s, baterií %d", size, tostring(item.id), level * 100, slot,
        tostring(self.id), #spec.batteries))
    if holder ~= nil and holder.hands ~= nil and holder.hands.dropHeldItem ~= nil then
        holder.hands:dropHeldItem()
    end
    item:delete()
    self:raiseActive()
end

-- VYNDAT: z baterie cíle se vyrobí předmět s jejím nabitím u hráče (dál od vozidla); z poolu zmizí až po úspěšném načtení předmětu.
function SprayDroneBatterySlots.doTake(self, player, target, isLocal)
    local h = helpers()
    local spec = getRoot(self)
    local bs = spec.batterySlots
    local size = spec.batteryVariant
    local reason = SprayDroneBatterySlots.getTakeProblem(self, target)
    local filename = nil
    if reason == nil then
        reason, filename = getSpawnProblem(size)
    end
    local data = nil
    if reason == nil then
        data = VehicleLoadingData.new()
        data:setFilename(filename)
        if not data.isValid then
            reason = "sdt_batteryslot_spawnFailed"
        end
    end
    if reason ~= nil then
        h.notifyLocal(self, isLocal, reason)
        return
    end
    local battery = spec.batteries[SprayDroneBatterySlots.getTargetBattery(self, target)]
    local root = self.rootNode
    local halfWidth = (self.size ~= nil and self.size.width or 2.5) / 2
    local halfLength = (self.size ~= nil and self.size.length or 5) / 2
    local node = getTargetNode(self, target) or root
    local sx, _, sz = localToLocal(node, root, 0, 0, 0)
    local plx, plz = nil, nil
    local px, py, pz = h.getPlayerPosition(player)
    if px ~= nil then
        plx, _, plz = worldToLocal(root, px, py, pz)
    end
    local lx, lz = SprayDroneRelaySlots.getSpawnLocal(halfWidth, halfLength, plx, plz, sx, sz)
    local x, _, z = localToWorld(root, lx, 0, lz)
    local y = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
    if spec.portable then
        -- kufr může stát na korbě: baterie vedle něj ve stejné výšce, ne pod korbou
        local _, rootY, _ = getWorldTranslation(root)
        y = math.max(y, rootY)
    end
    y = y + 0.3
    local dx, _, dz = localDirectionToWorld(root, 0, 0, 1)
    local farmId = self:getOwnerFarmId()
    data:setPosition(x, y, z)
    data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(farmId)
    bs.spawning = true
    data:load(function(_, vehicles, loadState)
        bs.spawning = false
        local item = vehicles ~= nil and vehicles[1] or nil
        local function discard(text)
            Logging.warning("SDT: baterii %s se nepodařilo vyndat (%s)", tostring(size), text)
            for _, v in ipairs(vehicles or {}) do
                v:delete()
            end
            h.notifyLocal(self, isLocal, "sdt_batteryslot_spawnFailed")
        end
        if loadState ~= VehicleLoadingState.OK or item == nil then
            discard("načtení předmětu")
            return
        end
        local k = nil
        if h.isAlive(self) then
            for i, b in ipairs(spec.batteries) do
                if b == battery then
                    k = i
                end
            end
        end
        if k == nil or spec.batteryVariant ~= size then
            discard("baterie se mezitím změnila")
            return
        end
        if battery.slot == 0 and not SprayDroneBatterySlots.getIsDroneIdle(SprayDroneDrones.getSpec(self, battery.drone or 1)) then
            discard("dron mezitím odletěl")
            return
        end
        local from = battery.slot
        local charge = SprayDroneStation.removeBattery(self, k)
        SprayDroneItem.setBatteryLevel(item, charge / spec.batteryCapacity)
        SprayDroneSound.noteAction(string.format("baterie %s (id %s, %.0f %%) vyndána z %s vozidla %s, baterií %d", size, tostring(item.id),
            charge / spec.batteryCapacity * 100, from == 0 and "dronu" or ("šachty " .. from), tostring(self.id), #spec.batteries))
        self:raiseActive()
    end)
end

-- Příkaz z klienta nebo z místní hry; klient bez serveru ho pošle eventem, server / hostitel ho provede. item = baterie k vložení (PUT).
function SprayDroneBatterySlots.command(self, command, target, item, player, noEventSend)
    if SprayDroneBatterySlotEvent.sendEvent(self, command, target or 0, item, noEventSend) then
        return
    end
    if getRoot(self).batterySlots == nil then
        return
    end
    local isLocal = not noEventSend
    player = player or g_localPlayer
    if command == SprayDroneBatterySlotEvent.PUT then
        SprayDroneBatterySlots.doPut(self, player, item, target ~= 0 and target or nil, isLocal)
    elseif command == SprayDroneBatterySlotEvent.TAKE then
        SprayDroneBatterySlots.doTake(self, player, target, isLocal)
    end
end

-- Smí hráč z tohoto spojení šachty ovládat? Farma, která k vozidlu smí, a vzdálenost od kořene vozidla nebo některé šachty (COMMAND_DISTANCE).
function SprayDroneBatterySlots.getAllowedPlayer(self, connection)
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    local player = system ~= nil and system:getPlayerByConnection(connection) or nil
    if player == nil or not g_currentMission.accessHandler:canFarmAccess(player.farmId, self) then
        return nil
    end
    local bs = getRoot(self).batterySlots
    local x, y, z = helpers().getPlayerPosition(player)
    if bs ~= nil and x ~= nil then
        local nodes = { self.rootNode }
        for _, node in pairs(bs.nodes) do
            table.insert(nodes, node)
        end
        for _, node in ipairs(nodes) do
            local nx, ny, nz = getWorldTranslation(node)
            if MathUtil.vector3Length(x - nx, y - ny, z - nz) <= SprayDroneBatterySlots.COMMAND_DISTANCE then
                return player
            end
        end
        return nil
    end
    return player
end

---------------------------------------------------------------------------------------------------
-- aktivace (vanilla „Aktivovat objekt“, R): vložit baterii / vyndat baterii

SprayDroneBatterySlotsActivatable = {}
local Activatable_mt = Class(SprayDroneBatterySlotsActivatable)

function SprayDroneBatterySlotsActivatable.new(vehicle)
    local self = setmetatable({}, Activatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_batteryslot_put")
    self.distance = math.huge
    return self
end

-- Co by R teď udělalo: "put" (s baterií v ruce; šachta nil = žádná volná v dosahu), "take" (bez ničeho v ruce u baterie), nebo nil; dál cíl a baterie.
function SprayDroneBatterySlotsActivatable:evaluate()
    local vehicle = self.vehicle
    local player = g_localPlayer
    local h = helpers()
    self.distance = math.huge
    local spec = getRoot(vehicle)
    local bs = spec.batterySlots
    if bs == nil or player == nil or h.isInVehicle(player) or not h.isAlive(vehicle) or g_gui:getIsGuiVisible() then
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
    if h.getHeldNode(player) ~= nil then
        local battery = SprayDroneBatterySlots.getHeldBattery(player)
        if battery == nil then
            return nil
        end
        local _, anyDistance = SprayDroneBatterySlots.getNearestShaft(vehicle, x, y, z, nil)
        if anyDistance == nil then
            return nil
        end
        local free, freeDistance = SprayDroneBatterySlots.getNearestShaft(vehicle, x, y, z, false)
        self.distance = SprayDroneLink.aimDistance(math.max(anyDistance - 0.1, 0), free ~= nil and spec.batterySlots.nodes[free] or nil)
        return "put", free, battery
    end
    if SprayDroneBatterySlots.getAccessProblem(vehicle) ~= nil then
        return nil
    end
    local target, distance = SprayDroneBatterySlots.getNearestTake(vehicle, x, y, z)
    if target ~= nil and not bs.spawning then
        -- u kufru se víko při vyndání baterie nenabízí (SprayDroneCaseActivatable se ptá evaluate), vzdálenost je skutečná
        self.distance = SprayDroneLink.aimDistance(distance, getTargetNode(vehicle, target))
        return "take", target
    end
    return nil
end

function SprayDroneBatterySlotsActivatable:getIsActivatable()
    local action, target = self:evaluate()
    if action == nil then
        return false
    end
    local spec = getRoot(self.vehicle)
    if action == "put" then
        self.activateText = g_i18n:getText("sdt_batteryslot_put")
    else
        local k = SprayDroneBatterySlots.getTargetBattery(self.vehicle, target)
        local battery = k ~= nil and spec.batteries[k] or nil
        local charge = battery ~= nil and battery.charge or 0
        local droneIndex = SprayDroneBatterySlots.getTargetDrone(target)
        if droneIndex ~= nil then
            charge = SprayDroneDrones.getSpec(self.vehicle, droneIndex).battery or charge
        end
        self.activateText = string.format(g_i18n:getText("sdt_batteryslot_take"), charge / math.max(spec.batteryCapacity, 0.001) * 100)
    end
    if self.eventId ~= nil then
        g_inputBinding:setActionEventText(self.eventId, self.activateText)
    end
    return true
end

function SprayDroneBatterySlotsActivatable:registerCustomInput(inputContext)
    local _
    _, self.eventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_OBJECT, self, self.run, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(self.eventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(self.eventId, true)
    g_inputBinding:setActionEventText(self.eventId, self.activateText)
end

function SprayDroneBatterySlotsActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    self.eventId = nil
end

local function warn(vehicle, reason)
    local text = g_i18n:getText(reason)
    if reason == "sdt_batteryslot_wrongSize" then
        text = string.format(text, tostring(getRoot(vehicle).batteryVariant))
    end
    g_currentMission:showBlinkingWarning(text, 2500)
end

function SprayDroneBatterySlotsActivatable:run()
    local vehicle = self.vehicle
    local action, target, battery = self:evaluate()
    if action == "put" then
        local reason = SprayDroneBatterySlots.getPutProblem(vehicle, SprayDroneItem.getBatterySize(battery), target)
        if reason ~= nil then
            warn(vehicle, reason)
            return
        end
        SprayDroneBatterySlots.command(vehicle, SprayDroneBatterySlotEvent.PUT, target, battery)
    elseif action == "take" then
        local reason = SprayDroneBatterySlots.getTakeProblem(vehicle, target)
        if reason ~= nil then
            warn(vehicle, reason)
            return
        end
        SprayDroneBatterySlots.command(vehicle, SprayDroneBatterySlotEvent.TAKE, target)
    end
end

-- Pořadí volání getDistance / getIsActivatable systémem aktivací neznáme, proto se vzdálenost počítá i tady.
function SprayDroneBatterySlotsActivatable:getDistance(x, y, z)
    self:evaluate()
    return self.distance or math.huge
end

function SprayDroneBatterySlotsActivatable:activate() end

function SprayDroneBatterySlotsActivatable:deactivate() end

function SprayDroneBatterySlotsActivatable:draw() end
