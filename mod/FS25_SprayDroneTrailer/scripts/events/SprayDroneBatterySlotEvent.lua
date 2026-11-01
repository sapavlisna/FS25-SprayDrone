-- Příkaz pro šachtu nabíječky (vlek, kufr) z klienta na server: vložit bateriový předmět (s objektem baterie) do šachty / vyndat baterii ze šachty nebo
-- z dronu doma. Pool baterií jde zpět všem ve stavu vozidla (SprayDroneStation.writeState), vyndanou baterii vyrábí server a klienti ji dostanou jako
-- běžné vozidlo. Server příkaz provede jen hráči z farmy, která k vozidlu smí, a nejvýš SprayDroneBatterySlots.COMMAND_DISTANCE od některé šachty.

SprayDroneBatterySlotEvent = {}
local SprayDroneBatterySlotEvent_mt = Class(SprayDroneBatterySlotEvent, Event)
InitEventClass(SprayDroneBatterySlotEvent, "SprayDroneBatterySlotEvent")

SprayDroneBatterySlotEvent.PUT = 0
SprayDroneBatterySlotEvent.TAKE = 1
SprayDroneBatterySlotEvent.CMD_BITS = 1
-- cíl: 1..MAX_BATTERY_SLOTS = šachta, MAX_BATTERY_SLOTS + d = baterie v dronu d
SprayDroneBatterySlotEvent.TARGET_BITS = 4

function SprayDroneBatterySlotEvent.emptyNew()
    return Event.new(SprayDroneBatterySlotEvent_mt)
end

function SprayDroneBatterySlotEvent.new(vehicle, command, target, item)
    local self = SprayDroneBatterySlotEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.target = target
    self.item = item
    return self
end

function SprayDroneBatterySlotEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDroneBatterySlotEvent.CMD_BITS)
    self.target = streamReadUIntN(streamId, SprayDroneBatterySlotEvent.TARGET_BITS)
    if self.command == SprayDroneBatterySlotEvent.PUT then
        self.item = NetworkUtil.readNodeObject(streamId)
    end
    self:run(connection)
end

function SprayDroneBatterySlotEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDroneBatterySlotEvent.CMD_BITS)
    streamWriteUIntN(streamId, self.target, SprayDroneBatterySlotEvent.TARGET_BITS)
    if self.command == SprayDroneBatterySlotEvent.PUT then
        NetworkUtil.writeNodeObject(streamId, self.item)
    end
end

function SprayDroneBatterySlotEvent:run(connection)
    if connection:getIsServer() or self.vehicle == nil or not self.vehicle:getIsSynchronized() then
        return
    end
    if self.command == SprayDroneBatterySlotEvent.PUT and self.item == nil then
        return
    end
    local player = SprayDroneBatterySlots.getAllowedPlayer(self.vehicle, connection)
    if player ~= nil then
        SprayDroneBatterySlots.command(self.vehicle, self.command, self.target, self.item, player, true)
    end
end

-- true = příkaz odešel na server (klient bez serveru), false = provede ho tento proces (server / hostitel)
function SprayDroneBatterySlotEvent.sendEvent(vehicle, command, target, item, noEventSend)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneBatterySlotEvent.new(vehicle, command, target, item))
        return true
    end
    return false
end
