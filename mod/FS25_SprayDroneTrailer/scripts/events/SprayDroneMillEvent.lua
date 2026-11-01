-- Příkazy mlýnkového vozíku z klienta na server: motor zapnout / vypnout, ventil výstupu, stav výsypné roury.
-- Stav (motor, mletí, čerpání, ventil, roura) jde zpět přes stav vozidla (SprayDroneMill, dirty flag).

SprayDroneMillEvent = {}
local SprayDroneMillEvent_mt = Class(SprayDroneMillEvent, Event)
InitEventClass(SprayDroneMillEvent, "SprayDroneMillEvent")

function SprayDroneMillEvent.emptyNew()
    return Event.new(SprayDroneMillEvent_mt)
end

function SprayDroneMillEvent.new(vehicle, command, target, x, y, z, dx, dy, dz)
    local self = SprayDroneMillEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.target = target
    self.x, self.y, self.z = x, y, z
    self.dx, self.dy, self.dz = dx, dy, dz
    return self
end

local function hasPosition(command)
    return false
end

function SprayDroneMillEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDroneMill.CMD_BITS)
    if streamReadBool(streamId) then
        self.target = NetworkUtil.readNodeObject(streamId)
    end
    if hasPosition(self.command) then
        self.x, self.y, self.z = streamReadFloat32(streamId), streamReadFloat32(streamId), streamReadFloat32(streamId)
        self.dx, self.dy, self.dz = streamReadFloat32(streamId), streamReadFloat32(streamId), streamReadFloat32(streamId)
    end
    self:run(connection)
end

function SprayDroneMillEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDroneMill.CMD_BITS)
    if streamWriteBool(streamId, self.target ~= nil) then
        NetworkUtil.writeNodeObject(streamId, self.target)
    end
    if hasPosition(self.command) then
        streamWriteFloat32(streamId, self.x or 0)
        streamWriteFloat32(streamId, self.y or 0)
        streamWriteFloat32(streamId, self.z or 0)
        streamWriteFloat32(streamId, self.dx or 0)
        streamWriteFloat32(streamId, self.dy or 0)
        streamWriteFloat32(streamId, self.dz or 0)
    end
end

function SprayDroneMillEvent:run(connection)
    if not connection:getIsServer() and self.vehicle ~= nil and self.vehicle:getIsSynchronized()
        and SprayDroneMill.isConnectionAllowed(self.vehicle, connection) then
        self.vehicle:sprayDroneMillCommand(self.command, self.target, true, self.x, self.y, self.z, self.dx, self.dy, self.dz)
    end
end

function SprayDroneMillEvent.sendEvent(vehicle, command, target, noEventSend, x, y, z, dx, dy, dz)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneMillEvent.new(vehicle, command, target, x, y, z, dx, dy, dz))
        return true
    end
    return false
end
