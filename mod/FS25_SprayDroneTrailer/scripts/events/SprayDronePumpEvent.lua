-- Příkazy přenosné pumpy z klienta na server: motor zapnout / vypnout.
-- Stav (motor, koš ve vodě) jde zpět přes stav vozidla (SprayDronePump, dirty flag).

SprayDronePumpEvent = {}
local SprayDronePumpEvent_mt = Class(SprayDronePumpEvent, Event)
InitEventClass(SprayDronePumpEvent, "SprayDronePumpEvent")

function SprayDronePumpEvent.emptyNew()
    return Event.new(SprayDronePumpEvent_mt)
end

function SprayDronePumpEvent.new(vehicle, command)
    local self = SprayDronePumpEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    return self
end

function SprayDronePumpEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDronePump.CMD_BITS)
    self:run(connection)
end

function SprayDronePumpEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDronePump.CMD_BITS)
end

function SprayDronePumpEvent:run(connection)
    if not connection:getIsServer() and self.vehicle ~= nil and self.vehicle:getIsSynchronized()
        and SprayDronePump.isConnectionAllowed(self.vehicle, connection) then
        self.vehicle:sprayDronePumpCommand(self.command, true)
    end
end

function SprayDronePumpEvent.sendEvent(vehicle, command, noEventSend)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDronePumpEvent.new(vehicle, command))
        return true
    end
    return false
end
