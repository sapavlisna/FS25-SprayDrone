-- Příkazy vodní hadice z klienta na server: vzít z ventilu, táhnout, pustit, připojit ke zdroji vody, odpojit.
-- Stav (vytažená hadice, nesený konec, zdroj) jde zpět přes stav vozidla (SprayDroneWaterHose, dirty flag).

SprayDroneWaterHoseEvent = {}
local SprayDroneWaterHoseEvent_mt = Class(SprayDroneWaterHoseEvent, Event)
InitEventClass(SprayDroneWaterHoseEvent, "SprayDroneWaterHoseEvent")

function SprayDroneWaterHoseEvent.emptyNew()
    return Event.new(SprayDroneWaterHoseEvent_mt)
end

function SprayDroneWaterHoseEvent.new(vehicle, command, target, arg, x, y, z, dx, dy, dz, hose)
    local self = SprayDroneWaterHoseEvent.emptyNew()
    self.vehicle = vehicle
    self.command = command
    self.target = target
    self.arg = arg
    self.x, self.y, self.z = x, y, z
    self.dx, self.dy, self.dz = dx, dy, dz
    self.hose = hose or 1
    return self
end

local function hasPosition(command)
    local W = SprayDroneWaterHose
    return command == W.CMD_TAKE or command == W.CMD_DRAG or command == W.CMD_CONNECT
end

function SprayDroneWaterHoseEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.command = streamReadUIntN(streamId, SprayDroneWaterHose.CMD_BITS)
    self.arg = streamReadUIntN(streamId, 4)
    self.hose = streamReadUIntN(streamId, SprayDroneWaterHose.HOSE_BITS) + 1
    if streamReadBool(streamId) then
        self.target = NetworkUtil.readNodeObject(streamId)
    end
    if hasPosition(self.command) then
        self.x, self.y, self.z = streamReadFloat32(streamId), streamReadFloat32(streamId), streamReadFloat32(streamId)
        self.dx, self.dy, self.dz = streamReadFloat32(streamId), streamReadFloat32(streamId), streamReadFloat32(streamId)
    end
    self:run(connection)
end

function SprayDroneWaterHoseEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteUIntN(streamId, self.command, SprayDroneWaterHose.CMD_BITS)
    streamWriteUIntN(streamId, self.arg or 0, 4)
    streamWriteUIntN(streamId, (self.hose or 1) - 1, SprayDroneWaterHose.HOSE_BITS)
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

function SprayDroneWaterHoseEvent:run(connection)
    if not connection:getIsServer() and self.vehicle ~= nil and self.vehicle:getIsSynchronized()
        and SprayDroneStation.isConnectionAllowed(self.vehicle, connection) then
        self.vehicle:sprayDroneWaterHoseCommand(self.command, self.target, self.arg, true, self.x, self.y, self.z, self.dx, self.dy, self.dz, self.hose)
    end
end

function SprayDroneWaterHoseEvent.sendEvent(vehicle, command, target, arg, noEventSend, x, y, z, dx, dy, dz, hose)
    if (noEventSend == nil or not noEventSend) and not g_server then
        g_client:getServerConnection():sendEvent(SprayDroneWaterHoseEvent.new(vehicle, command, target, arg, x, y, z, dx, dy, dz, hose))
        return true
    end
    return false
end
