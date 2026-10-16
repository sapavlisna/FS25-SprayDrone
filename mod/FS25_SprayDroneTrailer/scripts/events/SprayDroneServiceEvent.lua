-- Přečerpávání na vleku z klienta na server: vypustit nádrž dronu do vleku, přečerpat nádrž vleku do IBC, zastavit.
-- Průběh jde zpět přes stav vozidla (writeState).

SprayDroneServiceEvent = {}
local SprayDroneServiceEvent_mt = Class(SprayDroneServiceEvent, Event)
InitEventClass(SprayDroneServiceEvent, "SprayDroneServiceEvent")

SprayDroneServiceEvent.NUM_BITS = 2
SprayDroneServiceEvent.DRONE_BITS = 2

function SprayDroneServiceEvent.emptyNew()
    return Event.new(SprayDroneServiceEvent_mt)
end

-- droneIndex: dron, jehož nádrž se vypouští (1 / 2); 0 = ať vybere server (pickDrainDrone)
function SprayDroneServiceEvent.new(vehicle, mode, droneIndex)
    local self = SprayDroneServiceEvent.emptyNew()
    self.vehicle = vehicle
    self.mode = mode
    self.droneIndex = droneIndex or 0
    return self
end

function SprayDroneServiceEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.mode = streamReadUIntN(streamId, SprayDroneServiceEvent.NUM_BITS)
    self.droneIndex = streamReadUIntN(streamId, SprayDroneServiceEvent.DRONE_BITS)
    self:run(connection)
end

function SprayDroneServiceEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.mode, SprayDroneServiceEvent.NUM_BITS)
    streamWriteUIntN(streamId, self.droneIndex, SprayDroneServiceEvent.DRONE_BITS)
end

function SprayDroneServiceEvent:run(connection)
    if not connection:getIsServer() and self.vehicle ~= nil and self.vehicle:getIsSynchronized()
        and SprayDroneStation.isConnectionAllowed(self.vehicle, connection) then
        self.vehicle:setSprayDroneTransfer(self.mode, true, self.droneIndex)
    end
end

function SprayDroneServiceEvent.sendEvent(vehicle, mode, noEventSend, droneIndex)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneServiceEvent.new(vehicle, mode, droneIndex))
        return true
    end
    return false
end
