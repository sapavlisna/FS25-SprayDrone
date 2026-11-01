-- Náklon vleků Middle a Max (Mini má vlastní kontrolu plošiny v SprayDronePad.lua). Vlek nemá nohy ani se nevyrovnává: rozložit
-- jde jen vlek, který stojí dost rovně (vehicle.sprayDrone.tilt#max, podélně i příčně). Náklon složeného vleku je jen řádek
-- v nápovědě; při pokusu o rozložení mimo mez ho na chvíli ukáže blikající varování (checkDeploy).

SprayDroneLevel = {}

SprayDroneLevel.STOWED_TIME = 0.98      -- od tohoto času skládání je vlek složený

function SprayDroneLevel.registerXMLPaths(schema, key)
    schema:register(XMLValueType.FLOAT, key .. ".tilt#max", "Největší náklon paluby (°) podélně i příčně, při kterém jde vlek rozložit", 5)
end

function SprayDroneLevel.load(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    spec.level = nil
    local xml = self.xmlFile
    local key = "vehicle.sprayDrone.tilt"
    if self.getFoldAnimTime == nil or not xml:hasProperty(key) then
        return
    end
    spec.level = { maxTilt = math.rad(xml:getValue(key .. "#max", 5)) }
end

-- Podélný a příčný náklon paluby vleku (rad): kladný podélný = čelo výš.
function SprayDroneLevel.getTilt(self)
    local _, fy = localDirectionToWorld(self.rootNode, 0, 0, 1)
    local _, sy = localDirectionToWorld(self.rootNode, 1, 0, 0)
    return math.asin(math.clamp(fy, -1, 1)), math.asin(math.clamp(sy, -1, 1))
end

-- Rozložit jde jen vlek, který stojí dost rovně. Vrací true, nebo false a text varování.
function SprayDroneLevel.checkDeploy(self)
    local level = self[SprayDroneStation.SPEC_NAME].level
    if level == nil or self:getFoldAnimTime() < SprayDroneLevel.STOWED_TIME then
        return true
    end
    local pitch, roll = SprayDroneLevel.getTilt(self)
    if math.max(math.abs(pitch), math.abs(roll)) > level.maxTilt then
        return false, string.format(g_i18n:getText("sdt_warning_tilt"), math.deg(pitch), math.deg(roll), math.deg(level.maxTilt))
    end
    return true
end

-- Náklon složeného vleku jako řádek v nápovědě (addExtraPrintText), ne trvale uprostřed obrazovky.
function SprayDroneLevel.drawTilt(self)
    local level = self[SprayDroneStation.SPEC_NAME].level
    if level == nil or self:getFoldAnimTime() < SprayDroneLevel.STOWED_TIME then
        return
    end
    local pitch, roll = SprayDroneLevel.getTilt(self)
    local i18n = g_i18n
    g_currentMission:addExtraPrintText(i18n:getText("sdt_hud_tilt") .. " "
        .. string.format(i18n:getText("sdt_hud_tiltLong"), math.deg(pitch)) .. " · "
        .. string.format(i18n:getText("sdt_hud_tiltSide"), math.deg(roll))
        .. string.format(i18n:getText("sdt_hud_tiltMax"), math.deg(level.maxTilt)))
end
