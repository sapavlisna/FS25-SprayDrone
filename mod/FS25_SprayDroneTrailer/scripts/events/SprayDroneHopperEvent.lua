-- Příkazy násypky na vápno z klienta na server: vysunout / zasunout opěry. Stav jde zpět přes stav vozidla (SprayDroneHopper, dirty flag).

SprayDroneHopperEvent = {}
local SprayDroneHopperEvent_mt = Class(SprayDroneHopperEvent, Event)
InitEventClass(SprayDroneHopperEvent, "SprayDroneHopperEvent")

function SprayDroneHopperEvent.emptyNew()
    return Event.new(SprayDroneHopperEvent_mt)
end

function SprayDroneHopperEvent.new(vehicle, command)
    local self = SprayDroneHopperEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    return self
end

function SprayDroneHopperEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDroneHopper.CMD_BITS)
    self:run(connection)
end

function SprayDroneHopperEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDroneHopper.CMD_BITS)
end

function SprayDroneHopperEvent:run(connection)
    if not connection:getIsServer() and self.vehicle ~= nil and self.vehicle:getIsSynchronized()
        and SprayDroneStation.isConnectionAllowed(self.vehicle, connection) then
        self.vehicle:sprayDroneHopperCommand(self.command, true)
    end
end

function SprayDroneHopperEvent.sendEvent(vehicle, command, noEventSend)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneHopperEvent.new(vehicle, command))
        return true
    end
    return false
end
