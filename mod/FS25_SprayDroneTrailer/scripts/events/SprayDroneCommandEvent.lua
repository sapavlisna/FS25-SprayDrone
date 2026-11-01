-- Příkaz pilota (výběr pole, start, návrat, zapnutí centrály) z klienta na server. Stav letu jde zpět přes update stream vozidla.

SprayDroneCommandEvent = {}
local SprayDroneCommandEvent_mt = Class(SprayDroneCommandEvent, Event)
InitEventClass(SprayDroneCommandEvent, "SprayDroneCommandEvent")

SprayDroneCommandEvent.SELECT_FIELD = 1
SprayDroneCommandEvent.START = 2
SprayDroneCommandEvent.RETURN_HOME = 3
SprayDroneCommandEvent.SET_GENERATOR = 4
SprayDroneCommandEvent.RESET_FIELD = 5
SprayDroneCommandEvent.NUM_BITS = 3
SprayDroneCommandEvent.DRONE_BITS = 2

function SprayDroneCommandEvent.emptyNew()
    return Event.new(SprayDroneCommandEvent_mt)
end

-- value: číslo pole (SELECT_FIELD) nebo 1 / 0 zapnout / vypnout (SET_GENERATOR), viz SprayDroneStation:sprayDroneCommand.
-- droneIndex: 0 = všechny drony v misi, 1 / 2 = jeden dron (START, RETURN_HOME)
function SprayDroneCommandEvent.new(vehicle, command, value, droneIndex)
    local self = SprayDroneCommandEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.value = value or 0
    self.droneIndex = droneIndex or 0
    return self
end

function SprayDroneCommandEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDroneCommandEvent.NUM_BITS)
    self.value = streamReadUInt16(streamId)
    self.droneIndex = streamReadUIntN(streamId, SprayDroneCommandEvent.DRONE_BITS)
    self:run(connection)
end

function SprayDroneCommandEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDroneCommandEvent.NUM_BITS)
    streamWriteUInt16(streamId, self.value)
    streamWriteUIntN(streamId, self.droneIndex, SprayDroneCommandEvent.DRONE_BITS)
end

function SprayDroneCommandEvent:run(connection)
    if not connection:getIsServer() and self.vehicle ~= nil and self.vehicle:getIsSynchronized()
        and SprayDroneStation.isConnectionAllowed(self.vehicle, connection) then
        self.vehicle:sprayDroneCommand(self.command, self.value, true, self.droneIndex)
    end
end

function SprayDroneCommandEvent.sendEvent(vehicle, command, value, noEventSend, droneIndex)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneCommandEvent.new(vehicle, command, value, droneIndex))
        return true
    end
    return false
end
