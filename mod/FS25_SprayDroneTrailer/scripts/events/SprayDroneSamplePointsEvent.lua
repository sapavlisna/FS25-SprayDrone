-- Naklikané body odběru vzorkovače AIRASI k poli (SprayDroneSamples: přidané body a odebrané body mřížky) z klienta na server a od něj
-- ostatním klientům. Posílá se celý stav pole, prázdný ho smaže.

SprayDroneSamplePointsEvent = {}
local SprayDroneSamplePointsEvent_mt = Class(SprayDroneSamplePointsEvent, Event)
InitEventClass(SprayDroneSamplePointsEvent, "SprayDroneSamplePointsEvent")

function SprayDroneSamplePointsEvent.emptyNew()
    return Event.new(SprayDroneSamplePointsEvent_mt)
end

function SprayDroneSamplePointsEvent.new(vehicle, fieldId, picks)
    local self = SprayDroneSamplePointsEvent.emptyNew()
    self.vehicle = vehicle
    self.fieldId = fieldId
    self.picks = picks
    return self
end

local function writeList(streamId, list)
    local n = math.min(#list, SprayDroneSamples.MAX_PICKS)
    streamWriteUInt8(streamId, n)
    for i = 1, n do
        streamWriteFloat32(streamId, list[i].x)
        streamWriteFloat32(streamId, list[i].z)
    end
end

function SprayDroneSamplePointsEvent.writePicks(streamId, fieldId, picks)
    picks = picks or SprayDroneSamples.newPicks()
    streamWriteUInt16(streamId, fieldId)
    writeList(streamId, picks.added)
    writeList(streamId, SprayDroneSamples.getRemovedList(picks))
end

-- Vrací pole, body a jestli jsou souřadnice čitelná čísla; celý stream se přečte vždy.
function SprayDroneSamplePointsEvent.readPicks(streamId)
    local fieldId = streamReadUInt16(streamId)
    local picks, valid = SprayDroneSamples.newPicks(), true
    for _, kind in ipairs({ "added", "removed" }) do
        for _ = 1, streamReadUInt8(streamId) do
            local x = streamReadFloat32(streamId)
            local z = streamReadFloat32(streamId)
            if x ~= x or z ~= z or math.abs(x) == math.huge or math.abs(z) == math.huge then
                valid = false
            else
                SprayDroneSamples.putPick(picks, kind, x, z)
            end
        end
    end
    return fieldId, picks, valid
end

function SprayDroneSamplePointsEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.fieldId, self.picks, self.valid = SprayDroneSamplePointsEvent.readPicks(streamId)
    self:run(connection)
end

function SprayDroneSamplePointsEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    SprayDroneSamplePointsEvent.writePicks(streamId, self.fieldId, self.picks)
end

function SprayDroneSamplePointsEvent:run(connection)
    if not self.valid or self.vehicle == nil or not SprayDroneSamples.getIsSampler(self.vehicle) then
        return
    end
    if not connection:getIsServer() then
        if not SprayDroneStation.isConnectionAllowed(self.vehicle, connection) then
            return
        end
        g_server:broadcastEvent(self, false, connection, self.vehicle)
    end
    if self.vehicle:getIsSynchronized() then
        SprayDroneSamples.setPicks(self.vehicle, self.fieldId, self.picks, true)
    end
end

function SprayDroneSamplePointsEvent.sendEvent(vehicle, fieldId, picks, noEventSend)
    if noEventSend == nil or not noEventSend then
        if g_server ~= nil then
            g_server:broadcastEvent(SprayDroneSamplePointsEvent.new(vehicle, fieldId, picks), nil, nil, vehicle)
        else
            g_client:getServerConnection():sendEvent(SprayDroneSamplePointsEvent.new(vehicle, fieldId, picks))
        end
    end
end
