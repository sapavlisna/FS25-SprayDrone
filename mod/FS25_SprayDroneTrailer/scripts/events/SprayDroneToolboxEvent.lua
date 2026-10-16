-- Příkaz pro bednu s kanystry z klienta na server (otevřít / zavřít, vybrat N kanystrů druhu, vypustit
-- N kanystrů z nádrže; u vleku s víc bednami s číslem bedny). Vsátí kanystrů dělá server sám. Stav bedny (otevřeno, sloty) jde zpět všem přes stav
-- vozidla (writeState), bez zvláštního broadcastu; nové objekty kanystrů vyrábí server a klienti je dostanou jako běžná vozidla.
-- Server příkaz provede jen hráči z farmy, která k vozidlu smí, a do COMMAND_DISTANCE od bedny.

SprayDroneToolboxEvent = {}
local SprayDroneToolboxEvent_mt = Class(SprayDroneToolboxEvent, Event)
InitEventClass(SprayDroneToolboxEvent, "SprayDroneToolboxEvent")

SprayDroneToolboxEvent.OPEN = 0
SprayDroneToolboxEvent.CLOSE = 1
SprayDroneToolboxEvent.DRAIN = 3
SprayDroneToolboxEvent.TAKE = 5
SprayDroneToolboxEvent.HAND_POUR_START = 8   -- fillType DIESEL = do elektrocentrály, jinak do koncentrátové nádrže
SprayDroneToolboxEvent.HAND_POUR_STOP = 9
SprayDroneToolboxEvent.GROUND_DRAIN_START = 10   -- Ctrl+I: koncentrátovou nádrž vypouštět na zem
SprayDroneToolboxEvent.GROUND_DRAIN_STOP = 11
SprayDroneToolboxEvent.CMD_BITS = 4
SprayDroneToolboxEvent.COUNT_BITS = 6
SprayDroneToolboxEvent.BOX_BITS = 2

function SprayDroneToolboxEvent.emptyNew()
    return Event.new(SprayDroneToolboxEvent_mt)
end

function SprayDroneToolboxEvent.new(vehicle, command, fillType, count, partIndex)
    local self = SprayDroneToolboxEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.fillType = fillType or FillType.UNKNOWN
    self.count = count or 1
    self.partIndex = partIndex or 1
    return self
end

function SprayDroneToolboxEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDroneToolboxEvent.CMD_BITS)
    self.fillType = streamReadUIntN(streamId, FillTypeManager.SEND_NUM_BITS)
    self.count = streamReadUIntN(streamId, SprayDroneToolboxEvent.COUNT_BITS)
    self.partIndex = streamReadUIntN(streamId, SprayDroneToolboxEvent.BOX_BITS) + 1
    self:run(connection)
end

function SprayDroneToolboxEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDroneToolboxEvent.CMD_BITS)
    streamWriteUIntN(streamId, self.fillType, FillTypeManager.SEND_NUM_BITS)
    streamWriteUIntN(streamId, math.clamp(self.count, 0, 2 ^ SprayDroneToolboxEvent.COUNT_BITS - 1), SprayDroneToolboxEvent.COUNT_BITS)
    streamWriteUIntN(streamId, math.clamp(self.partIndex - 1, 0, 2 ^ SprayDroneToolboxEvent.BOX_BITS - 1), SprayDroneToolboxEvent.BOX_BITS)
end

function SprayDroneToolboxEvent:run(connection)
    if not connection:getIsServer() and self.vehicle ~= nil and self.vehicle:getIsSynchronized()
        and SprayDroneToolbox.isConnectionAllowed(self.vehicle, connection,
            self.command == SprayDroneToolboxEvent.GROUND_DRAIN_START or self.command == SprayDroneToolboxEvent.GROUND_DRAIN_STOP) then
        SprayDroneToolbox.command(self.vehicle, self.command, self.fillType, self.count, true, self.partIndex)
    end
end

-- true = příkaz odešel na server (klient bez serveru), false = provede ho tento proces (server / hostitel)
function SprayDroneToolboxEvent.sendEvent(vehicle, command, fillType, count, noEventSend, partIndex)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneToolboxEvent.new(vehicle, command, fillType, count, partIndex))
        return true
    end
    return false
end
