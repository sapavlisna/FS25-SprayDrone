-- Příkaz pro plošinu dronu na vleku z klienta na server: nasadit dronový předmět (s objektem dronu; u Mini PLACE do bedny, PLACE_PLATE na
-- rozloženou plošinu) / sundat dron z plošiny / na Mini přendat dron mezi bednou a plošinou (MOVE_BOX, MOVE_PLATE). Obsazení plošin jde zpět všem ve stavu
-- vozidla (SprayDroneStation.writePads), sundaný dron vyrábí server a klienti ho dostanou jako běžné vozidlo.
-- Server příkaz provede jen hráči z farmy, která k vleku smí, a nejvýš SprayDronePadSlots.COMMAND_DISTANCE od některé plošiny.

SprayDronePadSlotEvent = {}
local SprayDronePadSlotEvent_mt = Class(SprayDronePadSlotEvent, Event)
InitEventClass(SprayDronePadSlotEvent, "SprayDronePadSlotEvent")

SprayDronePadSlotEvent.PLACE = 0
SprayDronePadSlotEvent.TAKE = 1
SprayDronePadSlotEvent.PLACE_PLATE = 2
SprayDronePadSlotEvent.MOVE_BOX = 3
SprayDronePadSlotEvent.MOVE_PLATE = 4
SprayDronePadSlotEvent.CMD_BITS = 3
SprayDronePadSlotEvent.PAD_BITS = 2

-- Nese příkaz předmět dronu (nasazení)?
function SprayDronePadSlotEvent.hasItem(command)
    return command == SprayDronePadSlotEvent.PLACE or command == SprayDronePadSlotEvent.PLACE_PLATE
end

function SprayDronePadSlotEvent.emptyNew()
    return Event.new(SprayDronePadSlotEvent_mt)
end

function SprayDronePadSlotEvent.new(vehicle, command, padIndex, item)
    local self = SprayDronePadSlotEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.padIndex = padIndex
    self.item = item
    return self
end

function SprayDronePadSlotEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDronePadSlotEvent.CMD_BITS)
    self.padIndex = streamReadUIntN(streamId, SprayDronePadSlotEvent.PAD_BITS)
    if SprayDronePadSlotEvent.hasItem(self.command) then
        self.item = NetworkUtil.readNodeObject(streamId)
    end
    self:run(connection)
end

function SprayDronePadSlotEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDronePadSlotEvent.CMD_BITS)
    streamWriteUIntN(streamId, self.padIndex, SprayDronePadSlotEvent.PAD_BITS)
    if SprayDronePadSlotEvent.hasItem(self.command) then
        NetworkUtil.writeNodeObject(streamId, self.item)
    end
end

function SprayDronePadSlotEvent:run(connection)
    if connection:getIsServer() or self.vehicle == nil or not self.vehicle:getIsSynchronized() then
        return
    end
    if SprayDronePadSlotEvent.hasItem(self.command) and self.item == nil then
        return
    end
    local player = SprayDronePadSlots.getAllowedPlayer(self.vehicle, connection)
    if player ~= nil then
        SprayDronePadSlots.command(self.vehicle, self.command, self.padIndex, self.item, player, true)
    end
end

-- true = příkaz odešel na server (klient bez serveru), false = provede ho tento proces (server / hostitel)
function SprayDronePadSlotEvent.sendEvent(vehicle, command, padIndex, item, noEventSend)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDronePadSlotEvent.new(vehicle, command, padIndex, item))
        return true
    end
    return false
end
