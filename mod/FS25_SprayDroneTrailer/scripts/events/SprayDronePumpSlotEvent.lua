-- Příkaz pro držák pumpy na vleku z klienta na server: uložit pumpu (s objektem pumpy) / vyndat pumpu ze slotu. Stav slotu jde zpět všem ve stavu vozidla
-- (SprayDronePumpSlots.writeState), vyndanou pumpu vyrábí server a klienti ji dostanou jako běžné vozidlo.
-- Server příkaz provede jen hráči z farmy, která k vleku smí, a nejvýš SprayDronePumpSlots.COMMAND_DISTANCE od slotu.

SprayDronePumpSlotEvent = {}
local SprayDronePumpSlotEvent_mt = Class(SprayDronePumpSlotEvent, Event)
InitEventClass(SprayDronePumpSlotEvent, "SprayDronePumpSlotEvent")

SprayDronePumpSlotEvent.STORE = 0
SprayDronePumpSlotEvent.TAKE = 1
SprayDronePumpSlotEvent.CMD_BITS = 1

function SprayDronePumpSlotEvent.emptyNew()
    return Event.new(SprayDronePumpSlotEvent_mt)
end

function SprayDronePumpSlotEvent.new(vehicle, command, pump)
    local self = SprayDronePumpSlotEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.pump = pump
    return self
end

function SprayDronePumpSlotEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDronePumpSlotEvent.CMD_BITS)
    if self.command == SprayDronePumpSlotEvent.STORE then
        self.pump = NetworkUtil.readNodeObject(streamId)
    end
    self:run(connection)
end

function SprayDronePumpSlotEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDronePumpSlotEvent.CMD_BITS)
    if self.command == SprayDronePumpSlotEvent.STORE then
        NetworkUtil.writeNodeObject(streamId, self.pump)
    end
end

function SprayDronePumpSlotEvent:run(connection)
    if connection:getIsServer() or self.vehicle == nil or not self.vehicle:getIsSynchronized() then
        return
    end
    if self.command == SprayDronePumpSlotEvent.STORE and self.pump == nil then
        return
    end
    local player = SprayDronePumpSlots.getAllowedPlayer(self.vehicle, connection)
    if player ~= nil then
        SprayDronePumpSlots.command(self.vehicle, self.command, self.pump, player, true)
    end
end

-- true = příkaz odešel na server (klient bez serveru), false = provede ho tento proces (server / hostitel)
function SprayDronePumpSlotEvent.sendEvent(vehicle, command, pump, noEventSend)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDronePumpSlotEvent.new(vehicle, command, pump))
        return true
    end
    return false
end
