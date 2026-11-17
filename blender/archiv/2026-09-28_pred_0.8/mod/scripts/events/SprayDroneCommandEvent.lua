-- Příkaz pilota (výběr pole, start, návrat, zapnutí centrály) z klienta na server. Stav letu jde zpět přes update stream vozidla.

SprayDroneCommandEvent = {}
local SprayDroneCommandEvent_mt = Class(SprayDroneCommandEvent, Event)
InitEventClass(SprayDroneCommandEvent, "SprayDroneCommandEvent")

SprayDroneCommandEvent.SELECT_FIELD = 1
SprayDroneCommandEvent.START = 2
SprayDroneCommandEvent.RETURN_HOME = 3
SprayDroneCommandEvent.SET_GENERATOR = 4
SprayDroneCommandEvent.NUM_BITS = 3

function SprayDroneCommandEvent.emptyNew()
    return Event.new(SprayDroneCommandEvent_mt)
end

function SprayDroneCommandEvent.new(vehicle, command, fieldId)
    local self = SprayDroneCommandEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.fieldId = fieldId or 0
    return self
end

function SprayDroneCommandEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDroneCommandEvent.NUM_BITS)
    self.fieldId = streamReadUInt16(streamId)
    self:run(connection)
end

function SprayDroneCommandEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDroneCommandEvent.NUM_BITS)
    streamWriteUInt16(streamId, self.fieldId)
end

function SprayDroneCommandEvent:run(connection)
    if not connection:getIsServer() and self.vehicle ~= nil and self.vehicle:getIsSynchronized() then
        self.vehicle:sprayDroneCommand(self.command, self.fieldId, true)
    end
end

function SprayDroneCommandEvent.sendEvent(vehicle, command, fieldId, noEventSend)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneCommandEvent.new(vehicle, command, fieldId))
        return true
    end
    return false
end
