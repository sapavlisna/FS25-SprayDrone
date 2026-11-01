-- Značka dronu na mapě hry (minimapa i velká mapa) za letu: PlaceableHotspot s vlastní ikonou gui/icons/mapDrone.dds, polohu dává
-- uzel dronu (spec.node). Značka vleku zůstává vanilla (mapHotspot vozidla).

SprayDroneHotspot = {}
local SprayDroneHotspot_mt = Class(SprayDroneHotspot, PlaceableHotspot)

SprayDroneHotspot.ICON = g_currentModDirectory .. "gui/icons/mapDrone.dds"

SprayDroneHotspot.ICON_SIZE = 26

function SprayDroneHotspot.new()
    local self = PlaceableHotspot.new(SprayDroneHotspot_mt)
    self.width, self.height = getNormalizedScreenValues(SprayDroneHotspot.ICON_SIZE, SprayDroneHotspot.ICON_SIZE)
    if self.icon ~= nil then
        self.icon:delete()
    end
    if self.iconSmall ~= nil then
        self.iconSmall:delete()
    end
    self.icon = Overlay.new(SprayDroneHotspot.ICON, 0, 0, self.width, self.height)
    self.iconSmall = Overlay.new(SprayDroneHotspot.ICON, 0, 0, self.width, self.height)
    self.sdtVisible = false
    return self
end

function SprayDroneHotspot.getCategory(self)
    return MapHotspot.CATEGORY_STEERABLE
end

function SprayDroneHotspot.getIsPersistent(self)
    return false
end

function SprayDroneHotspot.getRenderLast(self)
    return true
end

function SprayDroneHotspot.getIsVisible(self)
    return self.sdtVisible
end

-- Založí značku (jen klient); barva a název jsou kosmetika, bez API pro ně zůstane značka bez nich.
function SprayDroneHotspot.create(spec)
    if spec.hotspot ~= nil or g_currentMission == nil or g_dedicatedServer ~= nil then
        return
    end
    local hotspot = SprayDroneHotspot.new()
    local index = spec.droneIndex or 1
    local color = SprayDroneStation.getBatchColors(index)[1]
    for _, icon in ipairs({ hotspot.icon, hotspot.iconSmall }) do
        if icon ~= nil and icon.setColor ~= nil then
            icon:setColor(color[1], color[2], color[3], 1)
        end
    end
    if hotspot.setName ~= nil then
        hotspot:setName(spec.numDrones > 1 and string.format(g_i18n:getText("sdt_hotspot_droneN"), index)
            or g_i18n:getText("sdt_hotspot_drone"))
    end
    g_currentMission:addMapHotspot(hotspot)
    spec.hotspot = hotspot
end

function SprayDroneHotspot.update(spec, flying)
    if flying and spec.hotspot == nil then
        SprayDroneHotspot.create(spec)
    end
    local hotspot = spec.hotspot
    if hotspot ~= nil then
        hotspot.sdtVisible = flying
        if flying and spec.node ~= nil and not spec.isLinked then
            local x, _, z = getWorldTranslation(spec.node)
            hotspot:setWorldPosition(x, z)
        end
    end
end

function SprayDroneHotspot.delete(spec)
    if spec.hotspot ~= nil then
        if g_currentMission ~= nil then
            g_currentMission:removeMapHotspot(spec.hotspot)
        end
        spec.hotspot:delete()
        spec.hotspot = nil
    end
end
