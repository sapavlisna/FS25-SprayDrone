-- Příkaz pro držáky relé tyčí na vleku z klienta na server: uložit tyč (s objektem tyče) / vyndat tyč ze slotu. Stav slotů jde
-- zpět všem ve stavu vozidla (SprayDroneRelaySlots.writeState), vyndanou tyč vyrábí server a klienti ji dostanou jako běžné vozidlo.
-- Server příkaz provede jen hráči z farmy, která k vleku smí, a nejvýš SprayDroneRelaySlots.COMMAND_DISTANCE od slotu.

SprayDroneRelaySlotEvent = {}
local SprayDroneRelaySlotEvent_mt = Class(SprayDroneRelaySlotEvent, Event)
InitEventClass(SprayDroneRelaySlotEvent, "SprayDroneRelaySlotEvent")

SprayDroneRelaySlotEvent.STORE = 0
SprayDroneRelaySlotEvent.TAKE = 1
SprayDroneRelaySlotEvent.CMD_BITS = 1

function SprayDroneRelaySlotEvent.emptyNew()
    return Event.new(SprayDroneRelaySlotEvent_mt)
end

function SprayDroneRelaySlotEvent.new(vehicle, command, pole, index)
    local self = SprayDroneRelaySlotEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.pole = pole
    self.index = index or 1
    return self
end

function SprayDroneRelaySlotEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDroneRelaySlotEvent.CMD_BITS)
    if self.command == SprayDroneRelaySlotEvent.STORE then
        self.pole = NetworkUtil.readNodeObject(streamId)
    else
        self.index = streamReadUIntN(streamId, SprayDroneRelaySlots.SLOT_BITS) + 1
    end
    self:run(connection)
end

function SprayDroneRelaySlotEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDroneRelaySlotEvent.CMD_BITS)
    if self.command == SprayDroneRelaySlotEvent.STORE then
        NetworkUtil.writeNodeObject(streamId, self.pole)
    else
        streamWriteUIntN(streamId, math.clamp(self.index - 1, 0, 2 ^ SprayDroneRelaySlots.SLOT_BITS - 1), SprayDroneRelaySlots.SLOT_BITS)
    end
end

function SprayDroneRelaySlotEvent:run(connection)
    if connection:getIsServer() or self.vehicle == nil or not self.vehicle:getIsSynchronized() then
        return
    end
    if self.command == SprayDroneRelaySlotEvent.STORE and self.pole == nil then
        return
    end
    local player = SprayDroneRelaySlots.getAllowedPlayer(self.vehicle, connection)
    if player ~= nil then
        SprayDroneRelaySlots.command(self.vehicle, self.command, self.pole, self.index, player, true)
    end
end

-- true = příkaz odešel na server (klient bez serveru), false = provede ho tento proces (server / hostitel)
function SprayDroneRelaySlotEvent.sendEvent(vehicle, command, pole, index, noEventSend)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneRelaySlotEvent.new(vehicle, command, pole, index))
        return true
    end
    return false
end
