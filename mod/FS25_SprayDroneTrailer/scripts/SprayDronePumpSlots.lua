-- Držák přenosné pumpy na vleku (Max, Middle). Princip jako držáky relé tyčí (SprayDroneRelaySlots): pumpa (vozidlo sdtWaterPump) se při uložení smaže a slot si
-- zapíše její stav (hladina nafty, farma); při vyndání se z něj vyrobí nové vozidlo pumpy (VehicleLoadingData) a slot se uvolní až po úspěšném načtení.
-- Slot je jen jeden na vlek. Vlek ho v XML (<sprayDrone><pumpSlot node translation rotation visible/>) zadává jako polohu v prostoru existujícího namapovaného uzlu,
-- uzel slotu (bod, u kterého se pumpa ukládá a vyndává) a volitelná maketa uložené pumpy (visible, vizuální uzel pumpového i3d) se vyrábí za běhu, takže se i3d vleku nemění.
-- Paluba Maxu ani Middle nemá volné místo na 0,9 × 1,1 × 0,8 m, proto je u obou maketa vypnutá (uložení je jen chování, Pavel: „není potřeba viditelně“).
--
-- Obsluha (vanilla „Aktivovat objekt“, R) pěšky u slotu:
--  * ULOŽIT: hráč drží pumpu v rukou, nebo pumpa leží do STORE_DISTANCE od hráče. Pumpa musí mít vypnutý motor; připojené hadice se při uložení odloží.
--  * VYNDAT: jinak R vyndá pumpu ze slotu; objeví se na zemi u hráče, dál od vleku. Do rukou ji hráč zvedne sám (60 kg, limit rukou 200 kg).
-- Uložená pumpa neběží a nepálí naftu. Změny dělá server (příkaz z klienta jde SprayDronePumpSlotEvent), slot se ukládá do savegame a jde klientům ve stavu vleku
-- (writeState / readState v SprayDroneStation).

SprayDronePumpSlots = {}

SprayDronePumpSlots.ACTIVATE_DISTANCE = 2.5    -- hráč nejvýš tak daleko od uzlu slotu (m, vodorovně)
SprayDronePumpSlots.ACTIVATE_HEIGHT = 3        -- … a slot nejvýš tolik m nad nebo pod jeho polohou (slot na palubě je o metr výš než hráč)
SprayDronePumpSlots.STORE_DISTANCE = 2.5       -- ležící pumpa nejvýš tak daleko od hráče (m)
SprayDronePumpSlots.COMMAND_DISTANCE = 6       -- server: hráč od slotu (m), rezerva na zpoždění polohy
SprayDronePumpSlots.SPAWN_GAP = 1.2            -- vyndaná pumpa: o tolik m dál od vleku než hráč
SprayDronePumpSlots.SPAWN_SIDE_MIN = 0.9       -- … a aspoň tolik m za bokem vleku (pumpa je široká 0,9 m)
SprayDronePumpSlots.LYING_IGNORE_MS = 15000    -- po vyndání se ležící pumpa chvíli nenabízí k uložení
SprayDronePumpSlots.CANDIDATE_INTERVAL_MS = 200
SprayDronePumpSlots.DIESEL_MAX_LITERS = 15     -- kapacita nafty pumpy (waterPump.xml), jen pro přenos po síti
SprayDronePumpSlots.DIESEL_BITS = 8
SprayDronePumpSlots.PUMP_FILE = "objects/pump/waterPump.xml"
SprayDronePumpSlots.I3D_FILE = "objects/pump/waterPump.i3d"
SprayDronePumpSlots.VISUAL_INDEX = "0>190"     -- waterPump_vis v i3d pumpy
SprayDronePumpSlots.modDirectory = g_currentModDirectory

local function getSpec(self)
    return self[SprayDroneStation.SPEC_NAME]
end

local function getPumpState(v)
    local pump = SprayDronePump ~= nil and v ~= nil and v[SprayDronePump.SPEC_NAME] or nil
    return pump ~= nil and pump.storable and pump or nil
end

local function raiseDirty(self)
    self:raiseDirtyFlags(getSpec(self).dirtyFlag)
end

---------------------------------------------------------------------------------------------------
-- čistá logika

-- Proč pumpa s daným stavem nejde uložit (l10n klíč), nebo nil. pump = { engineOn }.
function SprayDronePumpSlots.getStoreBlock(slot, pump)
    if pump == nil then
        return "sdt_pumpslot_noPump"
    end
    if slot.occupied then
        return "sdt_pumpslot_full"
    end
    if pump.engineOn then
        return "sdt_pumpslot_running"
    end
    return nil
end

---------------------------------------------------------------------------------------------------
-- schéma, načtení, uložení, smazání

function SprayDronePumpSlots.registerXMLPaths(schema, key)
    key = key .. ".pumpSlot"
    schema:register(XMLValueType.STRING, key .. "#node", "i3dMapping uzlu, v jehož prostoru je slot pumpy (kořen komponenty, paluba)")
    schema:register(XMLValueType.VECTOR_TRANS, key .. "#translation", "Poloha středu podstavy uložené pumpy (m, v prostoru uzlu)", "0 0 0")
    schema:register(XMLValueType.VECTOR_ROT, key .. "#rotation", "Natočení uložené pumpy (°, v prostoru uzlu)", "0 0 0")
    schema:register(XMLValueType.BOOL, key .. "#visible", "Uložená pumpa je na vleku vidět (maketa z i3d pumpy); bez modelu místa pro ni zůstává uložení jen chováním", false)
end

function SprayDronePumpSlots.registerSavegamePaths(savegame, saveKey)
    saveKey = saveKey .. ".pumpSlot"
    savegame:register(XMLValueType.FLOAT, saveKey .. "#diesel", "Nafta v uložené pumpě (l)")
    savegame:register(XMLValueType.INT, saveKey .. "#farmId", "Farma, které uložená pumpa patří")
end

function SprayDronePumpSlots.load(self, savegame)
    local spec = getSpec(self)
    local xml = self.xmlFile
    local key = "vehicle.sprayDrone.pumpSlot"
    local parentName = xml:getValue(key .. "#node")
    local parent = parentName ~= nil and SprayDroneStation.getMappedNode(self, parentName) or nil
    if parent == nil then
        return
    end
    local node = createTransformGroup("pumpSlot")
    link(parent, node)
    setTranslation(node, unpack(xml:getValue(key .. "#translation", "0 0 0", true)))
    setRotation(node, unpack(xml:getValue(key .. "#rotation", "0 0 0", true)))
    local ps = { node = node, visible = xml:getValue(key .. "#visible", false), occupied = false, diesel = 0, farmId = 0, spawning = false, candidateTimer = 0,
        lyingIgnoreUntil = 0 }
    spec.pumpSlot = ps
    if savegame ~= nil and not savegame.resetVehicles then
        local saveKey = savegame.key .. "." .. SprayDroneStation.MOD_NAME .. ".sprayDroneStation.pumpSlot"
        local diesel = savegame.xmlFile:getValue(saveKey .. "#diesel")
        if diesel ~= nil then
            ps.occupied = true
            ps.diesel = math.max(diesel, 0)
            ps.farmId = savegame.xmlFile:getValue(saveKey .. "#farmId", self:getOwnerFarmId())
        end
    end
    SprayDronePumpSlots.updateVisuals(self)
    if self.isClient and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        ps.activatable = SprayDronePumpSlotsActivatable.new(self)
        g_currentMission.activatableObjectsSystem:addActivatable(ps.activatable)
    end
end

function SprayDronePumpSlots.save(self, xmlFile, key)
    local ps = getSpec(self).pumpSlot
    if ps ~= nil and ps.occupied then
        xmlFile:setValue(key .. ".pumpSlot#diesel", ps.diesel)
        xmlFile:setValue(key .. ".pumpSlot#farmId", ps.farmId)
    end
end

function SprayDronePumpSlots.delete(self)
    local spec = getSpec(self)
    local ps = spec ~= nil and spec.pumpSlot or nil
    if ps ~= nil and ps.activatable ~= nil and g_currentMission ~= nil and g_currentMission.activatableObjectsSystem ~= nil then
        g_currentMission.activatableObjectsSystem:removeActivatable(ps.activatable)
        ps.activatable = nil
    end
end

-- Maketa uložené pumpy: vizuální uzel pumpového i3d, načtený jednou při prvním uložení a pak jen skrývaný / ukazovaný. Jen klient.
local function ensureVisual(self, ps)
    if ps.visual ~= nil or not self.isClient then
        return
    end
    local root = g_i3DManager:loadI3DFile(Utils.getFilename(SprayDronePumpSlots.I3D_FILE, SprayDronePumpSlots.modDirectory), false, false)
    if root == nil or root == 0 then
        return
    end
    local visual = I3DUtil.indexToObject(root, SprayDronePumpSlots.VISUAL_INDEX)
    if visual ~= nil and visual ~= 0 then
        link(ps.node, visual)
        setTranslation(visual, 0, 0, 0)
        setRotation(visual, 0, 0, 0)
        ps.visual = visual
    end
    delete(root)
end

function SprayDronePumpSlots.updateVisuals(self)
    local ps = getSpec(self).pumpSlot
    if ps == nil or not self.isClient or not ps.visible then
        return
    end
    if ps.occupied then
        ensureVisual(self, ps)
    end
    if ps.visual ~= nil and ps.shown ~= ps.occupied then
        ps.shown = ps.occupied
        setVisibility(ps.visual, ps.occupied)
    end
end

---------------------------------------------------------------------------------------------------
-- síť (voláno z writeState / readState v SprayDroneStation; slot je jen u vleků, které ho v XML mají, na serveru i klientu stejně)

function SprayDronePumpSlots.writeState(self, streamId)
    local ps = getSpec(self).pumpSlot
    if ps == nil then
        return
    end
    if streamWriteBool(streamId, ps.occupied) then
        local fraction = math.clamp(ps.diesel / SprayDronePumpSlots.DIESEL_MAX_LITERS, 0, 1)
        streamWriteUIntN(streamId, math.floor(fraction * 255 + 0.5), SprayDronePumpSlots.DIESEL_BITS)
    end
end

function SprayDronePumpSlots.readState(self, streamId)
    local ps = getSpec(self).pumpSlot
    if ps == nil then
        return
    end
    ps.occupied = streamReadBool(streamId)
    if ps.occupied then
        ps.diesel = streamReadUIntN(streamId, SprayDronePumpSlots.DIESEL_BITS) / 255 * SprayDronePumpSlots.DIESEL_MAX_LITERS
    end
    SprayDronePumpSlots.updateVisuals(self)
end

---------------------------------------------------------------------------------------------------
-- hledání pumpy k uložení (klient i server)

local function helpers()
    return SprayDroneRelaySlots.helpers
end

function SprayDronePumpSlots.getSlotDistance(self, x, y, z)
    local ps = getSpec(self).pumpSlot
    local nx, ny, nz = getWorldTranslation(ps.node)
    return math.abs(y - ny) <= SprayDronePumpSlots.ACTIVATE_HEIGHT and MathUtil.vector2Length(x - nx, z - nz) or math.huge
end

-- Pumpa, kterou hráč drží v rukou, nebo nil.
function SprayDronePumpSlots.getHeldPump(player)
    local h = helpers()
    local held = h.getHeldNode(player)
    if held == nil or g_currentMission.getNodeObject == nil then
        return nil
    end
    local object = g_currentMission:getNodeObject(held)
    if getPumpState(object) ~= nil and h.isAlive(object) then
        return object
    end
    return nil
end

-- Pumpa, kterou hráč u vleku uloží: drží-li pumpu v rukou, ta; jinak nejbližší ležící do STORE_DISTANCE (s ignoreLying se ležící nehledají).
-- Vrací pumpu a vzdálenost od hráče, nebo nil.
function SprayDronePumpSlots.findStorePump(self, player, ignoreLying)
    local h = helpers()
    local x, y, z = h.getPlayerPosition(player)
    if x == nil or SprayDronePump == nil then
        return nil
    end
    if h.getHeldNode(player) ~= nil then
        local pump = SprayDronePumpSlots.getHeldPump(player)
        return pump, pump ~= nil and 0 or nil
    end
    if ignoreLying then
        return nil
    end
    local best, bestDistance = nil, SprayDronePumpSlots.STORE_DISTANCE
    local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, v in ipairs(vehicles) do
        if getPumpState(v) ~= nil and h.isAlive(v) and not h.isMounted(v) then
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

-- Cesta k xml pumpy, jen když je v obchodě (VehicleLoadingData:setFilename hledá storeItem podle xml).
function SprayDronePumpSlots.getPumpFilename()
    if g_storeManager == nil then
        return nil
    end
    local path = (SprayDronePumpSlots.modDirectory or "") .. SprayDronePumpSlots.PUMP_FILE
    if g_storeManager:getItemByXMLFilename(path) ~= nil then
        return path
    end
    local tail = string.lower(SprayDronePumpSlots.PUMP_FILE)
    for key, item in pairs(g_storeManager.xmlFilenameToItem or {}) do
        if string.sub(string.lower(key), -#tail) == tail then
            return item.xmlFilename or key
        end
    end
    return nil
end

-- ULOŽIT: pumpa (drží ji hráč, nebo leží u něj) se smaže a její nafta jde do slotu. Hadice pumpy se předtím odloží.
function SprayDronePumpSlots.doStore(self, player, pump, isLocal)
    local h = helpers()
    local ps = getSpec(self).pumpSlot
    local state = getPumpState(pump)
    if state == nil or not h.isAlive(pump) then
        return
    end
    local reason = SprayDronePumpSlots.getStoreBlock(ps, state)
    if reason == nil and (h.isMounted(pump) or (pump.getIsControlled ~= nil and pump:getIsControlled())) then
        reason = "sdt_pumpslot_noPump"
    end
    local holder = h.getHolder(pump)
    if reason == nil and holder ~= nil and holder ~= player then
        reason = "sdt_pumpslot_noPump"
    end
    if reason == nil and holder == nil then
        local px, py, pz = h.getPlayerPosition(player)
        local vx, vy, vz = getWorldTranslation(pump.rootNode)
        if px ~= nil and MathUtil.vector3Length(px - vx, py - vy, pz - vz) > SprayDronePumpSlots.STORE_DISTANCE + 1.5 then
            reason = "sdt_pumpslot_noPump"
        end
    end
    if reason ~= nil then
        h.notifyLocal(self, isLocal, reason)
        return
    end
    local hoses = pump[SprayDroneWaterHose.SPEC_NAME]
    for index = 1, hoses ~= nil and #hoses.hoses or 0 do
        pump:sprayDroneWaterHoseCommand(SprayDroneWaterHose.CMD_DROP, nil, nil, nil, nil, nil, nil, nil, nil, nil, index)
    end
    ps.occupied = true
    ps.diesel = pump:getFillUnitFillLevel(state.dieselUnit)
    local farmId = pump.getOwnerFarmId ~= nil and pump:getOwnerFarmId() or nil
    ps.farmId = (farmId ~= nil and farmId ~= 0) and farmId or self:getOwnerFarmId()
    SprayDroneSound.noteAction(string.format("pumpa id %s uložena na vlek %s (nafta %.1f l)", tostring(pump.id), tostring(self.id), ps.diesel))
    if holder ~= nil and holder.hands ~= nil and holder.hands.dropHeldItem ~= nil then
        holder.hands:dropHeldItem()
    end
    pump:delete()
    raiseDirty(self)
    self:raiseActive()
    SprayDronePumpSlots.updateVisuals(self)
end

-- VYNDAT: ze slotu se vyrobí pumpa s naftou slotu u hráče, dál od vleku; slot se uvolní až po úspěšném načtení.
function SprayDronePumpSlots.doTake(self, player, isLocal)
    local h = helpers()
    local ps = getSpec(self).pumpSlot
    if ps == nil or not ps.occupied or ps.spawning then
        return
    end
    local filename = SprayDronePumpSlots.getPumpFilename()
    if filename == nil then
        Logging.warning("SDT: pumpa nejde vyrobit (chybí %s v obchodě)", SprayDronePumpSlots.PUMP_FILE)
        h.notifyLocal(self, isLocal, "sdt_pumpslot_spawnFailed")
        return
    end
    local slotSystem = g_currentMission.slotSystem
    if slotSystem ~= nil and SlotSystem ~= nil and SlotSystem.LIMITED_OBJECT_PALLET ~= nil
        and not slotSystem:getCanAddLimitedObjects(SlotSystem.LIMITED_OBJECT_PALLET, 1) then
        h.notifyLocal(self, isLocal, "sdt_toolbox_spawnLimit")
        return
    end
    local data = VehicleLoadingData.new()
    data:setFilename(filename)
    if not data.isValid then
        h.notifyLocal(self, isLocal, "sdt_pumpslot_spawnFailed")
        return
    end
    local root = self.rootNode
    local halfWidth = (self.size ~= nil and self.size.width or 2.5) / 2
    local halfLength = (self.size ~= nil and self.size.length or 5) / 2
    local sx, _, sz = localToLocal(ps.node, root, 0, 0, 0)
    local plx, plz = nil, nil
    local px, py, pz = h.getPlayerPosition(player)
    if px ~= nil then
        plx, _, plz = worldToLocal(root, px, py, pz)
    end
    local lx, lz = SprayDroneRelaySlots.getSpawnLocal(halfWidth, halfLength, plx, plz, sx, sz)
    local x, _, z = localToWorld(root, lx, 0, lz)
    local y = getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z) + 0.3
    local dx, _, dz = localDirectionToWorld(root, 0, 0, 1)
    local diesel = ps.diesel
    local farmId = ps.farmId ~= 0 and ps.farmId or self:getOwnerFarmId()
    data:setPosition(x, y, z)
    data:setRotation(0, MathUtil.getYRotationFromDirection(dx, dz), 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(farmId)
    ps.spawning = true
    data:load(function(_, vehicles, loadState)
        ps.spawning = false
        local pump = vehicles ~= nil and vehicles[1] or nil
        if loadState ~= VehicleLoadingState.OK or pump == nil then
            Logging.warning("SDT: pumpu se nepodařilo načíst (%s)", tostring(filename))
            for _, v in ipairs(vehicles or {}) do
                v:delete()
            end
            h.notifyLocal(self, isLocal, "sdt_pumpslot_spawnFailed")
            return
        end
        local state = getPumpState(pump)
        if state ~= nil and diesel > 0.001 then
            pump:addFillUnitFillLevel(farmId, state.dieselUnit, diesel, FillType.DIESEL, ToolType.UNDEFINED, nil)
        end
        SprayDroneSound.noteAction(string.format("pumpa id %s vyndána z vleku %s (nafta %.1f l)", tostring(pump.id), tostring(self.id), diesel))
        if ps.occupied then
            ps.occupied, ps.diesel, ps.farmId = false, 0, 0
        end
        if h.isAlive(self) then
            raiseDirty(self)
            SprayDronePumpSlots.updateVisuals(self)
        end
    end)
end

-- Příkaz z klienta nebo z místní hry; klient bez serveru ho pošle eventem, server / hostitel ho provede. pump = pumpa k uložení (STORE).
function SprayDronePumpSlots.command(self, command, pump, player, noEventSend)
    if SprayDronePumpSlotEvent.sendEvent(self, command, pump, noEventSend) then
        return
    end
    local ps = getSpec(self).pumpSlot
    if ps == nil then
        return
    end
    local isLocal = not noEventSend
    player = player or g_localPlayer
    if command == SprayDronePumpSlotEvent.STORE then
        SprayDronePumpSlots.doStore(self, player, pump, isLocal)
    elseif command == SprayDronePumpSlotEvent.TAKE then
        SprayDronePumpSlots.doTake(self, player, isLocal)
    end
end

-- Smí hráč z tohoto spojení slot ovládat? Farma, která k vleku smí, a vzdálenost od slotu (COMMAND_DISTANCE). Vrací hráče, nebo nil.
function SprayDronePumpSlots.getAllowedPlayer(self, connection)
    local system = g_currentMission ~= nil and g_currentMission.playerSystem or nil
    local player = system ~= nil and system:getPlayerByConnection(connection) or nil
    if player == nil or not g_currentMission.accessHandler:canFarmAccess(player.farmId, self) then
        return nil
    end
    local ps = getSpec(self).pumpSlot
    local x, y, z = helpers().getPlayerPosition(player)
    if ps ~= nil and x ~= nil then
        local nx, ny, nz = getWorldTranslation(ps.node)
        if MathUtil.vector3Length(x - nx, y - ny, z - nz) > SprayDronePumpSlots.COMMAND_DISTANCE then
            return nil
        end
    end
    return player
end

---------------------------------------------------------------------------------------------------
-- aktivace (vanilla „Aktivovat objekt“, R): uložit pumpu / vyndat pumpu

SprayDronePumpSlotsActivatable = {}
local Activatable_mt = Class(SprayDronePumpSlotsActivatable)

function SprayDronePumpSlotsActivatable.new(vehicle)
    local self = setmetatable({}, Activatable_mt)
    self.vehicle = vehicle
    self.activateText = g_i18n:getText("sdt_pumpslot_store")
    self.distance = math.huge
    return self
end

-- Co by R teď udělalo: "store" (s pumpou), "take" (se zaplněným slotem), nebo nil. Kandidát se hledá nejvýš jednou za CANDIDATE_INTERVAL_MS.
function SprayDronePumpSlotsActivatable:evaluate()
    local vehicle = self.vehicle
    local player = g_localPlayer
    local h = helpers()
    self.distance = math.huge
    local spec = getSpec(vehicle)
    local ps = spec ~= nil and spec.pumpSlot or nil
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
    local distance = SprayDronePumpSlots.getSlotDistance(vehicle, x, y, z)
    if distance > SprayDronePumpSlots.ACTIVATE_DISTANCE then
        ps.lyingIgnoreUntil = 0
        return nil
    end
    if g_time >= ps.candidateTimer then
        ps.candidateTimer = g_time + SprayDronePumpSlots.CANDIDATE_INTERVAL_MS
        ps.candidate, ps.candidateDistance = SprayDronePumpSlots.findStorePump(vehicle, player, g_time < ps.lyingIgnoreUntil)
    end
    if ps.candidate ~= nil and h.isAlive(ps.candidate) and not ps.occupied then
        self.distance = SprayDroneLink.aimDistance(math.max((ps.candidateDistance or 0) - 0.1, 0), ps.node)
        return "store", ps.candidate
    end
    ps.candidate = nil
    if ps.occupied and not ps.spawning then
        self.distance = SprayDroneLink.aimDistance(distance, ps.node)
        return "take"
    end
    return nil
end

function SprayDronePumpSlotsActivatable:getIsActivatable()
    local action = self:evaluate()
    if action == nil then
        return false
    end
    if action == "store" then
        self.activateText = g_i18n:getText("sdt_pumpslot_store")
    else
        self.activateText = string.format(g_i18n:getText("sdt_pumpslot_take"), getSpec(self.vehicle).pumpSlot.diesel)
    end
    if self.eventId ~= nil then
        g_inputBinding:setActionEventText(self.eventId, self.activateText)
    end
    return true
end

function SprayDronePumpSlotsActivatable:registerCustomInput(inputContext)
    local _
    _, self.eventId = g_inputBinding:registerActionEvent(InputAction.ACTIVATE_OBJECT, self, self.run, false, true, false, true)
    g_inputBinding:setActionEventTextPriority(self.eventId, GS_PRIO_VERY_HIGH)
    g_inputBinding:setActionEventTextVisibility(self.eventId, true)
    g_inputBinding:setActionEventText(self.eventId, self.activateText)
end

function SprayDronePumpSlotsActivatable:removeCustomInput(inputContext)
    g_inputBinding:removeActionEventsByTarget(self)
    self.eventId = nil
end

function SprayDronePumpSlotsActivatable:run()
    local vehicle = self.vehicle
    local ps = getSpec(vehicle).pumpSlot
    ps.candidateTimer = 0
    local action, target = self:evaluate()
    if action == "store" then
        local reason = SprayDronePumpSlots.getStoreBlock(ps, getPumpState(target))
        if reason ~= nil then
            g_currentMission:showBlinkingWarning(g_i18n:getText(reason), 2500)
            return
        end
        SprayDronePumpSlots.command(vehicle, SprayDronePumpSlotEvent.STORE, target)
    elseif action == "take" then
        ps.lyingIgnoreUntil = g_time + SprayDronePumpSlots.LYING_IGNORE_MS
        ps.candidate = nil
        SprayDronePumpSlots.command(vehicle, SprayDronePumpSlotEvent.TAKE)
    end
end

-- Pořadí volání getDistance / getIsActivatable systémem aktivací neznáme, proto se vzdálenost počítá i tady.
function SprayDronePumpSlotsActivatable:getDistance(x, y, z)
    self:evaluate()
    return self.distance or math.huge
end

function SprayDronePumpSlotsActivatable:activate() end

function SprayDronePumpSlotsActivatable:deactivate() end

function SprayDronePumpSlotsActivatable:draw() end
