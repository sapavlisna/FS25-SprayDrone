-- Mapa skenu pole ze serveru klientům (SprayDroneScanMap): hlavička mřížky a dávka buněk {index, zabalená hodnota (nil =
-- nenaskenováno), čas skenu, čas ošetření (nil = neošetřeno), druhy ošetření, dusík a pH z Precision Farming (nil = bez PF)}.
-- reset = mapa je nová (jiná buňka), klient zahodí svou.

SprayDroneScanEvent = {}
local SprayDroneScanEvent_mt = Class(SprayDroneScanEvent, Event)
InitEventClass(SprayDroneScanEvent, "SprayDroneScanEvent")

function SprayDroneScanEvent.emptyNew()
    return Event.new(SprayDroneScanEvent_mt)
end

function SprayDroneScanEvent.new(map, cells, reset)
    local self = SprayDroneScanEvent.emptyNew()
    self.header = { farmId = map.farmId, fieldId = map.fieldId, cellSize = map.cellSize, originX = map.originX, originZ = map.originZ,
        nx = map.nx, nz = map.nz, updated = map.updated, reset = reset == true }
    self.cells = cells
    return self
end

function SprayDroneScanEvent:readStream(streamId, connection)
    local h = {}
    h.farmId = streamReadUIntN(streamId, FarmManager.FARM_ID_SEND_NUM_BITS)
    h.fieldId = streamReadInt32(streamId)
    h.cellSize = streamReadFloat32(streamId)
    h.originX = streamReadFloat32(streamId)
    h.originZ = streamReadFloat32(streamId)
    h.nx = streamReadInt32(streamId)
    h.nz = streamReadInt32(streamId)
    h.updated = streamReadInt32(streamId)
    h.reset = streamReadBool(streamId)
    self.header = h
    self.cells = {}
    for _ = 1, streamReadUInt16(streamId) do
        local cell = { streamReadInt32(streamId) }
        if streamReadBool(streamId) then
            cell[2] = streamReadUIntN(streamId, SprayDroneScanMap.VALUE_BITS)
            cell[3] = streamReadInt32(streamId)
            if streamReadBool(streamId) then
                cell[6] = streamReadUIntN(streamId, SprayDroneScanMap.PF_BITS)
            end
        end
        if streamReadBool(streamId) then
            cell[4] = streamReadInt32(streamId)
            cell[5] = streamReadUIntN(streamId, SprayDroneScanMap.TREAT_BITS)
        end
        table.insert(self.cells, cell)
    end
    self:run(connection)
end

function SprayDroneScanEvent:writeStream(streamId, connection)
    local h = self.header
    streamWriteUIntN(streamId, h.farmId, FarmManager.FARM_ID_SEND_NUM_BITS)
    streamWriteInt32(streamId, h.fieldId)
    streamWriteFloat32(streamId, h.cellSize)
    streamWriteFloat32(streamId, h.originX)
    streamWriteFloat32(streamId, h.originZ)
    streamWriteInt32(streamId, h.nx)
    streamWriteInt32(streamId, h.nz)
    streamWriteInt32(streamId, h.updated)
    streamWriteBool(streamId, h.reset)
    streamWriteUInt16(streamId, #self.cells)
    for _, cell in ipairs(self.cells) do
        streamWriteInt32(streamId, cell[1])
        if streamWriteBool(streamId, cell[2] ~= nil) then
            streamWriteUIntN(streamId, cell[2], SprayDroneScanMap.VALUE_BITS)
            streamWriteInt32(streamId, cell[3])
            if streamWriteBool(streamId, cell[6] ~= nil) then
                streamWriteUIntN(streamId, cell[6], SprayDroneScanMap.PF_BITS)
            end
        end
        if streamWriteBool(streamId, cell[4] ~= nil) then
            streamWriteInt32(streamId, cell[4])
            streamWriteUIntN(streamId, cell[5], SprayDroneScanMap.TREAT_BITS)
        end
    end
end

function SprayDroneScanEvent:run(connection)
    if connection:getIsServer() then
        SprayDroneScanMap.applyRemote(self.header, self.cells)
    end
end
