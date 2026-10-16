-- Příkaz pro retranslační tyč z klienta na server (rozložit / složit zvenku R, zapnout / vypnout B po nástupu). Server ho ověří
-- (SprayDroneRelay.getChangeBlock: vzpřímenost, baterie, obsazenost, pojistky letu) a stav rozešle všem přes stav vozidla
-- (dirty flag); odmítnutý příkaz se nerozesílá a klient zůstane ve stavu ze serveru. Tyč smí ovládat jen hráč z farmy, která k ní smí.

SprayDroneRelayEvent = {}
local SprayDroneRelayEvent_mt = Class(SprayDroneRelayEvent, Event)
InitEventClass(SprayDroneRelayEvent, "SprayDroneRelayEvent")

function SprayDroneRelayEvent.emptyNew()
    return Event.new(SprayDroneRelayEvent_mt)
end

function SprayDroneRelayEvent.new(vehicle, unfolded, powered)
    local self = SprayDroneRelayEvent.emptyNew()
    self.vehicle = vehicle
    self.unfolded = unfolded
    self.powered = powered
    return self
end

function SprayDroneRelayEvent:readStream(streamId, connection)
    self.vehicle = NetworkUtil.readNodeObject(streamId)
    self.unfolded = streamReadBool(streamId)
    self.powered = streamReadBool(streamId)
    self:run(connection)
end

function SprayDroneRelayEvent:writeStream(streamId, connection)
    NetworkUtil.writeNodeObject(streamId, self.vehicle)
    streamWriteBool(streamId, self.unfolded)
    streamWriteBool(streamId, self.powered)
end

function SprayDroneRelayEvent:run(connection)
    if connection:getIsServer() or self.vehicle == nil or not self.vehicle:getIsSynchronized() then
        return
    end
    local farmId = g_currentMission.userManager:getFarmIdByConnection(connection)
    if farmId ~= nil and g_currentMission.accessHandler:canFarmAccess(farmId, self.vehicle) then
        self.vehicle:setSprayDroneRelayState(self.unfolded, self.powered, true)
    end
end

-- Klient bez serveru pošle příkaz na server a lokálně se nic nemění (stav přijde zpátky); server / hostitel ho provede sám
-- (SprayDroneRelay.setState).
function SprayDroneRelayEvent.sendEvent(vehicle, unfolded, powered, noEventSend)
    if noEventSend == true then
        return
    end
    if g_server == nil then
        g_client:getServerConnection():sendEvent(SprayDroneRelayEvent.new(vehicle, unfolded, powered))
    end
end
