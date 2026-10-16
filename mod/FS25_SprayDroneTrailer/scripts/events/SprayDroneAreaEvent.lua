-- Letová plocha dronu k poli (mnohoúhelník ve světových souřadnicích) z klienta na server a od něj ostatním klientům.
-- Prázdný seznam bodů plochu smaže.

SprayDroneAreaEvent = {}
local SprayDroneAreaEvent_mt = Class(SprayDroneAreaEvent, Event)
InitEventClass(SprayDroneAreaEvent, "SprayDroneAreaEvent")

SprayDroneAreaEvent.MAX_POINTS = 64

function SprayDroneAreaEvent.emptyNew()
    return Event.new(SprayDroneAreaEvent_mt)
end

function SprayDroneAreaEvent.new(vehicle, fieldId, points)
    local self = SprayDroneAreaEvent.emptyNew()
    self.vehicle = vehicle
    self.fieldId = fieldId
    self.points = points or {}
    return self
end

function SprayDroneAreaEvent.writeArea(streamId, fieldId, points)
    streamWriteUInt16(streamId, fieldId)
    local n = math.min(#points, SprayDroneAreaEvent.MAX_POINTS)
    streamWriteUInt8(streamId, n)
    for i = 1, n do
        streamWriteFloat32(streamId, points[i].x)
        streamWriteFloat32(streamId, points[i].z)
    end
end

-- Vrací pole, body (nejvýš MAX_POINTS) a jestli jsou souřadnice čitelná čísla; celý stream se přečte vždy.
function SprayDroneAreaEvent.readArea(streamId)
    local fieldId = streamReadUInt16(streamId)
    local points, valid = {}, true
    for i = 1, streamReadUInt8(streamId) do
        local x = streamReadFloat32(streamId)
        local z = streamReadFloat32(streamId)
        if x ~= x or z ~= z or math.abs(x) == math.huge or math.abs(z) == math.huge then
            valid = false
        elseif i <= SprayDroneAreaEvent.MAX_POINTS then
            points[i] = { x = x, z = z }
        end
    end
    return fieldId, points, valid
end

function SprayDroneAreaEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.fieldId, self.points, self.valid = SprayDroneAreaEvent.readArea(streamId)
    self:run(connection)
end

function SprayDroneAreaEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    SprayDroneAreaEvent.writeArea(streamId, self.fieldId, self.points)
end

function SprayDroneAreaEvent:run(connection)
    if not self.valid or self.vehicle == nil then
        return
    end
    if not connection:getIsServer() then
        if not SprayDroneStation.isConnectionAllowed(self.vehicle, connection) then
            return
        end
        g_server:broadcastEvent(self, false, connection, self.vehicle)
    end
    if self.vehicle:getIsSynchronized() then
        self.vehicle:setSprayDroneFlightArea(self.fieldId, self.points, true)
    end
end

function SprayDroneAreaEvent.sendEvent(vehicle, fieldId, points, noEventSend)
    if noEventSend == nil or not noEventSend then
        if g_server ~= nil then
            g_server:broadcastEvent(SprayDroneAreaEvent.new(vehicle, fieldId, points), nil, nil, vehicle)
        else
            g_client:getServerConnection():sendEvent(SprayDroneAreaEvent.new(vehicle, fieldId, points))
        end
    end
end
