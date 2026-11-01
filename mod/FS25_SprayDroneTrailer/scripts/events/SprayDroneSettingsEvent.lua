-- Nastavení letu z plánovače (výška přeletu, odstup nad překážkami, boční odstup, počet úvratí, začátek úvratěmi)
-- z klienta na server a od něj ostatním klientům. Hodnoty jsou celá čísla.

SprayDroneSettingsEvent = {}
local SprayDroneSettingsEvent_mt = Class(SprayDroneSettingsEvent, Event)
InitEventClass(SprayDroneSettingsEvent, "SprayDroneSettingsEvent")

function SprayDroneSettingsEvent.emptyNew()
    return Event.new(SprayDroneSettingsEvent_mt)
end

function SprayDroneSettingsEvent.new(vehicle, settings)
    local self = SprayDroneSettingsEvent.emptyNew()
    self.vehicle = vehicle
    self.settings = settings
    return self
end

-- Pořadí a počet hodnot dává SprayDroneStation.SETTINGS, každá je jedno celé číslo v 8 bitech.
function SprayDroneSettingsEvent.writeSettings(streamId, settings)
    for _, setting in ipairs(SprayDroneStation.SETTINGS) do
        streamWriteUInt8(streamId, math.clamp(math.floor((settings[setting.key] or setting.min) + 0.5), 0, 255))
    end
end

function SprayDroneSettingsEvent.readSettings(streamId)
    local settings = {}
    for _, setting in ipairs(SprayDroneStation.SETTINGS) do
        settings[setting.key] = streamReadUInt8(streamId)
    end
    return settings
end

function SprayDroneSettingsEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.settings = SprayDroneSettingsEvent.readSettings(streamId)
    self:run(connection)
end

function SprayDroneSettingsEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    SprayDroneSettingsEvent.writeSettings(streamId, self.settings)
end

function SprayDroneSettingsEvent:run(connection)
    if self.vehicle == nil then
        return
    end
    if not connection:getIsServer() then
        if not SprayDroneStation.isConnectionAllowed(self.vehicle, connection) then
            return
        end
        g_server:broadcastEvent(self, false, connection, self.vehicle)
    end
    if self.vehicle:getIsSynchronized() then
        self.vehicle:setSprayDroneSettings(self.settings, true)
    end
end

function SprayDroneSettingsEvent.sendEvent(vehicle, settings, noEventSend)
    if noEventSend == nil or not noEventSend then
        if g_server ~= nil then
            g_server:broadcastEvent(SprayDroneSettingsEvent.new(vehicle, settings), nil, nil, vehicle)
        else
            g_client:getServerConnection():sendEvent(SprayDroneSettingsEvent.new(vehicle, settings))
        end
    end
end
