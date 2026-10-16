-- Plánovač letu dronu: celoobrazovková mapa (herní InGameMap, stejná jako v menu mapy) s vlekem,
-- kruhem dosahu, poli v okolí a naplánovanou trasou. Klik na pole ho vybere, tlačítka spouští let
-- a volají dron domů. Výběr i start jdou přes SprayDroneStation (a tím eventem na server).
-- V režimu kreslení klik přidává vrchol letové plochy vybraného pole (pole nevybírá); uzavřená plocha jde
-- eventem na server.

SprayDronePlannerScreen = {}
SprayDronePlannerScreen.MOD_DIR = g_currentModDirectory
SprayDronePlannerScreen.GUI_NAME = "SprayDronePlannerScreen"
SprayDronePlannerScreen.FIELD_REFRESH_TIME = 1000
SprayDronePlannerScreen.MESSAGE_TIME = 5000
SprayDronePlannerScreen.PANEL_WIDTH_PX = 470
SprayDronePlannerScreen.SUMMARY_REFRESH_TIME = 250
SprayDronePlannerScreen.MIN_TEXT_PX = 14
SprayDronePlannerScreen.PANEL_GROW_TIME = 500
SprayDronePlannerScreen.LINE_SPACING = 0.3
SprayDronePlannerScreen.PANEL_STAGES = {
    { scale = 1 }, { scale = 0.9 }, { scale = 0.8 }, { scale = 0.7 }, { scale = 0.7, noHint = true },
    { scale = 0.7, noHint = true, noLegend = true }
}

SprayDronePlannerScreen.COLOR_RANGE = { 0, 0.9, 1, 1 }
SprayDronePlannerScreen.COLOR_RELAY = { 1, 0.6, 0.1, 1 }
SprayDronePlannerScreen.COLOR_SELECTED = { 0.2, 1, 0.2, 1 }
SprayDronePlannerScreen.COLOR_CONTRACT = { 1, 0.78, 0.1, 1 }
SprayDronePlannerScreen.COLOR_HOVER = { 1, 1, 1, 1 }
SprayDronePlannerScreen.COLOR_WARNING = { 1, 0.35, 0.3 }
SprayDronePlannerScreen.COLOR_TEXT = { 1, 1, 1 }
SprayDronePlannerScreen.COLOR_DIM = { 0.75, 0.75, 0.75 }
SprayDronePlannerScreen.COLOR_AREA = { 0.72, 0.42, 1, 1 }
SprayDronePlannerScreen.COLOR_AREA_FILL = { 0.72, 0.42, 1, 0.22 }
SprayDronePlannerScreen.COLOR_DRAFT = { 1, 0.55, 1, 1 }
SprayDronePlannerScreen.COLOR_UNPLANNED = { 1, 0.15, 0.1, 0.85 }
SprayDronePlannerScreen.COLOR_SETTING = { 0.15, 0.35, 0.4, 0.9 }
SprayDronePlannerScreen.COLOR_SETTING_BOX = { 0.25, 0.25, 0.25, 1 }
-- při otevření se na výšku obrazovky vejde zhruba 2,8× tolik (dosah z baterie bývá přes kilometr)
SprayDronePlannerScreen.VIEW_RADIUS = 350
SprayDronePlannerScreen.FIELD_MARGIN = 400
SprayDronePlannerScreen.CLOSE_DISTANCE_PX = 14
SprayDronePlannerScreen.RELAY_ICON_RANGE = 2

local SprayDronePlannerScreen_mt = Class(SprayDronePlannerScreen, ScreenElement)

function SprayDronePlannerScreen.new()
    local self = ScreenElement.new(nil, SprayDronePlannerScreen_mt)
    self.vehicle = nil
    self.mission = g_currentMission
    self.fields = {}
    self.fieldTimer = 0
    self.summary = nil
    self.summaryTimer = 0
    self.highest = nil
    self.measuring = false
    self.textScale = 1
    self.hoverEntry = nil
    self.message = nil
    self.messageTimer = 0
    self.needsInit = false
    self.mouseX, self.mouseY = 0.5, 0.5
    self.drawMode = false
    self.draft = {}
    self.selectedSetting = 1
    self.settingRects = {}
    self.icons = {}
    return self
end

-- Ikony mapy plánovače; celé cesty, ať je kontrola nepoužitých souborů (TestRunner) najde.
SprayDronePlannerScreen.ICONS = {
    mapDrone = "gui/icons/mapDrone.dds",
    mapRelay = "gui/icons/mapRelay.dds",
    mapRelayOff = "gui/icons/mapRelayOff.dds",
    mapTrailer = "gui/icons/mapTrailer.dds",
}

-- Ikona z ICONS (vytvoří se při prvním použití); px = velikost v pixelech obrazovky.
function SprayDronePlannerScreen:drawIcon(name, x, z, px)
    local icon = self.icons[name]
    if icon == nil then
        icon = Overlay.new(SprayDronePlannerScreen.MOD_DIR .. SprayDronePlannerScreen.ICONS[name], 0, 0, 1, 1)
        self.icons[name] = icon
    end
    local sx, sy = self:worldToScreen(x, z)
    local w, h = px * g_pixelSizeScaledX, px * g_pixelSizeScaledY
    icon:setPosition(sx - w * 0.5, sy - h * 0.5)
    icon:setDimension(w, h)
    icon:render()
    return sx, sy
end

function SprayDronePlannerScreen:delete()
    for _, icon in pairs(self.icons) do
        icon:delete()
    end
    self.icons = {}
    if SprayDronePlannerScreen.INSTANCE == self then
        SprayDronePlannerScreen.INSTANCE = nil
    end
    SprayDronePlannerScreen:superClass().delete(self)
end

-- Odkud je plánovač otevřený: tablet (hráč musí být ve spojení s vlekem), displej na vleku (hráč musí zůstat u displeje),
-- nebo nastoupený vlek (starší způsob otevření).
SprayDronePlannerScreen.MODE_VEHICLE = "vehicle"
SprayDronePlannerScreen.MODE_TABLET = "tablet"
SprayDronePlannerScreen.MODE_SCREEN = "screen"

-- Obrazovka se načte jednou na hru; po přechodu do jiné hry (třída přežije v Lua stavu) se stará zahodí a načte nová.
function SprayDronePlannerScreen.show(vehicle, mode)
    local old = SprayDronePlannerScreen.INSTANCE
    if old ~= nil and old.mission ~= g_currentMission then
        old:delete()
        SprayDronePlannerScreen.INSTANCE = nil
    end
    if SprayDronePlannerScreen.INSTANCE == nil then
        local screen = SprayDronePlannerScreen.new()
        g_gui:loadGui(SprayDronePlannerScreen.MOD_DIR .. "gui/SprayDronePlannerScreen.xml", SprayDronePlannerScreen.GUI_NAME, screen)
        SprayDronePlannerScreen.INSTANCE = screen
    end
    SprayDronePlannerScreen.INSTANCE.vehicle = vehicle
    SprayDronePlannerScreen.INSTANCE.openMode = mode or SprayDronePlannerScreen.MODE_VEHICLE
    g_gui:showGui(SprayDronePlannerScreen.GUI_NAME)
end

function SprayDronePlannerScreen:onOpen()
    SprayDronePlannerScreen:superClass().onOpen(self)
    self.mapBase = g_currentMission.hud:getIngameMap()
    self.ingameMap:setIngameMap(self.mapBase)
    self.ingameMap:setTerrainSize(g_currentMission.terrainSize)
    self.mapBase:restoreDefaultFilter()
    self.startButton:setText(g_i18n:getText("sdt_button_start"))
    self.returnButton:setText(g_i18n:getText("sdt_button_returnHome"))
    self.undoButton:setText(g_i18n:getText("sdt_button_undoPoint"))
    self.settingDownButton.sdtTextKey, self.settingUpButton.sdtTextKey = nil, nil
    self.deleteAreaButton:setText(g_i18n:getText("sdt_button_deleteArea"))
    self.resetFieldButton:setText(g_i18n:getText("sdt_button_resetField"))
    self.closeButton.sdtTextKey, self.drawButton.sdtTextKey = nil, nil
    self.fieldTimer = 0
    self.summary = nil
    self.hoverEntry = nil
    self.message = nil
    self.drawMode = false
    self.draft = {}
    -- mapa se přepne na celou obrazovku až v onOpen svého prvku (volá se po tomhle), proto přiblížení
    -- a vycentrování na vlek až v prvním update
    self.needsInit = true
end

function SprayDronePlannerScreen:onClose()
    SprayDronePlannerScreen:superClass().onClose(self)
    self.vehicle = nil
    self.openMode = nil
    self.fields = {}
end

function SprayDronePlannerScreen:onClickBack()
    if self.drawMode then
        self.drawMode = false
        self.draft = {}
        self:showMessage(g_i18n:getText("sdt_planner_areaCancelled"), false)
        return false
    end
    g_gui:showGui("")
    return false
end

function SprayDronePlannerScreen:getPanelRect()
    local w = math.min(SprayDronePlannerScreen.PANEL_WIDTH_PX * g_pixelSizeScaledX, 0.4)
    local margin = 20 * g_pixelSizeScaledX
    local top = 1 - 70 * g_pixelSizeScaledY
    local bottom = 110 * g_pixelSizeScaledY
    return 1 - w - margin, bottom, w, top - bottom
end

function SprayDronePlannerScreen:initMapView()
    self.needsInit = false
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(self.vehicle)
    local layout = self.mapBase.fullScreenLayout
    local sizeRatio = layout.sizeRatio or 1
    local zoom = g_currentMission.terrainSize / (2.8 * math.min(spec.range, SprayDronePlannerScreen.VIEW_RADIUS) * sizeRatio)
    self.ingameMap:zoom(0, zoom)
    self.ingameMap:setCenterToWorldPosition(hx, hz)
    -- vlek doprostřed volné plochy vlevo od panelu
    local x, y, w, h = self:getPanelRect()
    self.ingameMap:moveCenter(x * 0.5 - self.ingameMap.originalMapCenterX, 0)
    self.ingameMap:clearCursorDeadzones()
    self.ingameMap:addCursorDeadzone(x, y, w, h)
    self.ingameMap:addCursorDeadzone(0, 0, 1, self.buttonBox.absPosition[2] + self.buttonBox.absSize[2])
    self.ingameMap:registerActionEvents()
end

function SprayDronePlannerScreen:mouseEvent(posX, posY, isDown, isUp, button, eventUsed)
    self.mouseX, self.mouseY = posX, posY
    if not eventUsed and isDown and self.vehicle ~= nil and self:handleSettingsMouse(posX, posY, button) then
        return true
    end
    return SprayDronePlannerScreen:superClass().mouseEvent(self, posX, posY, isDown, isUp, button, eventUsed)
end

local function isInRect(r, x, y)
    return r ~= nil and x >= r[1] and x <= r[1] + r[3] and y >= r[2] and y <= r[2] + r[4]
end

-- Nastavení letu v panelu: klik na − / + změní hodnotu o 1 m, klik na řádek ho vybere (tlačítka Snížit / Zvýšit
-- vybrané pak mění ten), kolečko nad řádkem mění jeho hodnotu.
function SprayDronePlannerScreen:handleSettingsMouse(posX, posY, button)
    if self.drawMode then
        return false
    end
    local wheelUp, wheelDown = Input.MOUSE_BUTTON_WHEEL_UP, Input.MOUSE_BUTTON_WHEEL_DOWN
    for i, rects in pairs(self.settingRects) do
        if isInRect(rects.row, posX, posY) then
            if button == Input.MOUSE_BUTTON_LEFT then
                self.selectedSetting = i
                if isInRect(rects.minus, posX, posY) then
                    SprayDroneStation.changeSetting(self.vehicle, i, -1)
                elseif isInRect(rects.plus, posX, posY) then
                    SprayDroneStation.changeSetting(self.vehicle, i, 1)
                end
                self:playSample(GuiSoundPlayer.SOUND_SAMPLES.CLICK)
                return true
            elseif wheelUp ~= nil and button == wheelUp then
                self.selectedSetting = i
                SprayDroneStation.changeSetting(self.vehicle, i, 1)
                self:playSample(GuiSoundPlayer.SOUND_SAMPLES.CLICK)
                return true
            elseif wheelDown ~= nil and button == wheelDown then
                self.selectedSetting = i
                SprayDroneStation.changeSetting(self.vehicle, i, -1)
                self:playSample(GuiSoundPlayer.SOUND_SAMPLES.CLICK)
                return true
            end
        end
    end
    return false
end

function SprayDronePlannerScreen:onClickSettingDown()
    if self.vehicle ~= nil and not self.drawMode then
        SprayDroneStation.changeSetting(self.vehicle, self.selectedSetting, -1)
    end
end

function SprayDronePlannerScreen:onClickSettingUp()
    if self.vehicle ~= nil and not self.drawMode then
        SprayDroneStation.changeSetting(self.vehicle, self.selectedSetting, 1)
    end
end

function SprayDronePlannerScreen:getIsVehicleUsable()
    local vehicle = self.vehicle
    if vehicle == nil or vehicle.isDeleted or vehicle.isDeleting then
        return false
    end
    -- tablet a displej fungují i u složeného vleku (jen plánování, start letu vlek odmítne)
    if self.openMode == SprayDronePlannerScreen.MODE_VEHICLE and not vehicle:getIsUnfolded() then
        return false
    end
    -- tablet: místo nástupu stačí, že je hráč ve spojení s vlekem (dosah rádia nebo relé), jinak NO CONNECTION;
    -- displej: hráč nesmí od displeje odejít dál než SCREEN_CLOSE_DISTANCE
    if self.openMode == SprayDronePlannerScreen.MODE_TABLET then
        return SprayDroneLink.isPlayerConnected(vehicle)
    elseif self.openMode == SprayDronePlannerScreen.MODE_SCREEN then
        return SprayDroneLink.isPlayerAtScreen(vehicle, SprayDroneLink.SCREEN_CLOSE_DISTANCE)
    end
    return vehicle:getIsEntered()
end

function SprayDronePlannerScreen:update(dt)
    SprayDronePlannerScreen:superClass().update(self, dt)
    if not self:getIsOpen() then
        return
    end
    if not self:getIsVehicleUsable() then
        g_gui:showGui("")
        if self.openMode == SprayDronePlannerScreen.MODE_TABLET and g_currentMission ~= nil then
            g_currentMission:showBlinkingWarning(g_i18n:getText("sdt_tablet_noConnection"), 2500)
        end
        return
    end
    if self.needsInit then
        self:initMapView()
    end

    SprayDroneStation.refreshRoutePreview(self.vehicle, dt)
    self.summaryTimer = self.summaryTimer - dt
    self.fieldTimer = self.fieldTimer - dt
    if self.fieldTimer <= 0 then
        self:updateFields()
    end
    self:updateHover()

    if self.message ~= nil then
        self.messageTimer = self.messageTimer - dt
        if self.messageTimer <= 0 then
            self.message = nil
        end
    end

    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    self.startButton:setDisabled(self.drawMode or not SprayDroneStation.getCanStart(self.vehicle) or not SprayDroneStation.getAnyPlanned(self.vehicle))
    self.returnButton:setDisabled(not SprayDroneStation.getCanReturnHome(self.vehicle))

    local area = SprayDroneStation.getFlightArea(self.vehicle)
    local drawKey = area ~= nil and "sdt_button_editArea" or "sdt_button_drawArea"
    if self.drawMode then
        drawKey = "sdt_button_closeArea"
    end
    local changed = self:updateButton(self.closeButton, true, false, self.drawMode and "sdt_button_cancelDraw" or "sdt_button_close")
    changed = self:updateButton(self.drawButton, true, self.drawMode and #self.draft < 3, drawKey) or changed
    changed = self:updateButton(self.undoButton, self.drawMode, #self.draft == 0) or changed
    changed = self:updateButton(self.resetFieldButton, not self.drawMode, spec.fieldId == 0 or SprayDroneStation.getAnyMissionActive(self.vehicle)) or changed
    changed = self:updateButton(self.deleteAreaButton, area ~= nil or (self.drawMode and #self.draft > 0), false) or changed
    local setting = SprayDroneStation.SETTINGS[self.selectedSetting]
    local value = spec[setting.key]
    local enabled = SprayDroneStation.isSettingEnabled(self.vehicle, self.selectedSetting)
    changed = self:updateButton(self.settingDownButton, not self.drawMode, not enabled or value <= setting.min, "sdt_button_settingDown") or changed
    changed = self:updateButton(self.settingUpButton, not self.drawMode, not enabled or value >= setting.max, "sdt_button_settingUp") or changed
    if changed then
        self.buttonBox:invalidateLayout()
    end
end

-- Viditelnost, zákaz a text tlačítka; vrací true, když se změnila šířka lišty.
function SprayDronePlannerScreen:updateButton(button, visible, disabled, textKey)
    local changed = false
    if button:getIsVisible() ~= visible then
        button:setVisible(visible)
        changed = true
    end
    button:setDisabled(disabled)
    if textKey ~= nil and textKey ~= button.sdtTextKey then
        button.sdtTextKey = textKey
        button:setText(g_i18n:getText(textKey))
        changed = true
    end
    return changed
end

-- Pole v okolí vleku (do dvojnásobku dosahu) s tím, jestli je dron smí ošetřit.
function SprayDronePlannerScreen:updateFields()
    self.fieldTimer = SprayDronePlannerScreen.FIELD_REFRESH_TIME
    local vehicle = self.vehicle
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    self.fields = {}
    for _, field in ipairs(g_fieldManager:getFields()) do
        if field:getId() ~= nil then
            local poly = SprayDroneRoute.getPolygon(field)
            if #poly >= 3 and SprayDroneRoute.distanceToPolygon(poly, hx, hz) <= spec.range + math.min(spec.range, SprayDronePlannerScreen.FIELD_MARGIN) then
                local allowed, reason, mission = SprayDroneStation.getFieldAllowed(vehicle, field)
                table.insert(self.fields, { field = field, poly = poly, allowed = allowed, reason = reason, mission = mission })
            end
        end
    end
end

function SprayDronePlannerScreen:getEntryAt(x, z)
    for _, entry in ipairs(self.fields) do
        if SprayDroneRoute.isPointInPolygon(entry.poly, x, z) then
            return entry
        end
    end
    return nil
end

function SprayDronePlannerScreen:getIsInPanel(posX, posY)
    local x, y, w, h = self:getPanelRect()
    return posX >= x and posX <= x + w and posY >= y and posY <= y + h
end

function SprayDronePlannerScreen:updateHover()
    local previous = self.hoverEntry
    self.hoverEntry = nil
    if self:getIsInPanel(self.mouseX, self.mouseY) or self.drawMode then
        return
    end
    local lx, ly = self.ingameMap:getLocalPosition(self.mouseX, self.mouseY)
    local wx, wz = self.ingameMap:localToWorldPos(lx, ly)
    self.hoverEntry = self:getEntryAt(wx, wz)
    if self.hoverEntry ~= nil and (previous == nil or previous.field ~= self.hoverEntry.field) then
        self:playSample(GuiSoundPlayer.SOUND_SAMPLES.HOVER)
    end
end

-- Je kurzor u prvního vrcholu rozkreslené plochy (klik ji uzavře)?
function SprayDronePlannerScreen:getIsNearFirstPoint()
    local first = self.draft[1]
    if first == nil or #self.draft < 3 then
        return false
    end
    local sx, sy = self:worldToScreen(first.x, first.z)
    local limit = SprayDronePlannerScreen.CLOSE_DISTANCE_PX
    return math.abs(sx - self.mouseX) / g_pixelSizeX <= limit and math.abs(sy - self.mouseY) / g_pixelSizeY <= limit
end

function SprayDronePlannerScreen:onClickDraw()
    if self.vehicle == nil then
        return
    end
    if self.drawMode then
        if #self.draft >= 3 then
            self:commitDraft()
        end
        return
    end
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    if spec.fieldId == 0 then
        self:showMessage(g_i18n:getText("sdt_planner_areaNeedField"), true)
        return
    end
    self.draft = {}
    for _, point in ipairs(SprayDroneStation.getFlightArea(self.vehicle) or {}) do
        table.insert(self.draft, { x = point.x, z = point.z })
    end
    self.drawMode = true
    self.message = nil
end

function SprayDronePlannerScreen:commitDraft()
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    self.vehicle:setSprayDroneFlightArea(spec.fieldId, self.draft)
    self:showMessage(string.format(g_i18n:getText("sdt_planner_areaSaved"), #self.draft), false)
    self.drawMode = false
    self.draft = {}
end

function SprayDronePlannerScreen:onClickUndo()
    if self.drawMode and #self.draft > 0 then
        table.remove(self.draft)
    end
end

function SprayDronePlannerScreen:onClickResetField()
    if self.vehicle == nil then
        return
    end
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    if spec.fieldId == 0 or SprayDroneStation.getAnyMissionActive(self.vehicle) then
        return
    end
    self.vehicle:sprayDroneCommand(SprayDroneCommandEvent.RESET_FIELD, 0)
    self:showMessage(g_i18n:getText("sdt_planner_fieldReset"), false)
end

function SprayDronePlannerScreen:onClickDeleteArea()
    if self.vehicle == nil then
        return
    end
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    if SprayDroneStation.getFlightArea(self.vehicle) ~= nil then
        self.vehicle:setSprayDroneFlightArea(spec.fieldId, nil)
    end
    self.drawMode = false
    self.draft = {}
    self:showMessage(g_i18n:getText("sdt_planner_areaDeleted"), false)
end

function SprayDronePlannerScreen:showMessage(text, isWarning)
    self.message = { text = text, isWarning = isWarning }
    self.messageTimer = SprayDronePlannerScreen.MESSAGE_TIME
end

function SprayDronePlannerScreen:onClickMap(element, worldX, worldZ)
    if self.vehicle == nil or self:getIsInPanel(self.mouseX, self.mouseY) then
        return
    end
    if self.drawMode then
        if self:getIsNearFirstPoint() then
            self:commitDraft()
        elseif #self.draft >= SprayDroneStation.MAX_AREA_POINTS then
            self:showMessage(string.format(g_i18n:getText("sdt_planner_areaMaxPoints"), SprayDroneStation.MAX_AREA_POINTS), true)
        else
            table.insert(self.draft, { x = worldX, z = worldZ })
        end
        return
    end
    local entry = self:getEntryAt(worldX, worldZ)
    if entry == nil then
        self:showMessage(g_i18n:getText("sdt_warning_noField"), true)
        return
    end
    local warning = SprayDroneStation.selectField(self.vehicle, entry.field)
    if warning ~= nil then
        self:showMessage(string.format("%s: %s", entry.field:getName(), g_i18n:getText(warning)), true)
    else
        self:showMessage(string.format(g_i18n:getText("sdt_planner_selected"), entry.field:getName()), false)
        self:playSample(GuiSoundPlayer.SOUND_SAMPLES.CLICK)
    end
end

function SprayDronePlannerScreen:onClickStart()
    if self.vehicle == nil then
        return
    end
    local warning = SprayDroneStation.startFlight(self.vehicle)
    if warning ~= nil then
        self:showMessage(g_i18n:getText(warning), true)
    else
        self:showMessage(g_i18n:getText("sdt_planner_started"), false)
    end
end

function SprayDronePlannerScreen:onClickReturn()
    if self.vehicle ~= nil then
        self.vehicle:sprayDroneCommand(SprayDroneCommandEvent.RETURN_HOME, 0)
        self:showMessage(g_i18n:getText("sdt_planner_returning"), false)
    end
end

---------------------------------------------------------------------------------------------------
-- kreslení do mapy

function SprayDronePlannerScreen:worldToScreen(x, z)
    local map = self.mapBase
    local u = (x + map.worldCenterOffsetX) / map.worldSizeX * map.mapExtensionScaleFactor + map.mapExtensionOffsetX
    local v = (z + map.worldCenterOffsetZ) / map.worldSizeZ * map.mapExtensionScaleFactor + map.mapExtensionOffsetZ
    local sx, sy = map.fullScreenLayout:getMapObjectPosition(u, v, 0, 0, 0, true)
    return sx, sy
end

function SprayDronePlannerScreen:drawWorldLine(x1, z1, x2, z2, thicknessPx, color)
    local sx1, sy1 = self:worldToScreen(x1, z1)
    local sx2, sy2 = self:worldToScreen(x2, z2)
    drawLine2D(sx1, sy1, sx2, sy2, thicknessPx * g_pixelSizeX, color[1], color[2], color[3], color[4] or 1)
end

function SprayDronePlannerScreen:drawWorldPolygon(poly, thicknessPx, color)
    for i = 1, #poly do
        local a, b = poly[i], poly[i % #poly + 1]
        self:drawWorldLine(a.x, a.z, b.x, b.z, thicknessPx, color)
    end
end

-- Výplň polygonu vodorovnými čarami po 3 px (jen část na obrazovce).
function SprayDronePlannerScreen:fillWorldPolygon(poly, color)
    local pts = {}
    local minY, maxY = math.huge, -math.huge
    for i, p in ipairs(poly) do
        local sx, sy = self:worldToScreen(p.x, p.z)
        pts[i] = { sx, sy }
        minY, maxY = math.min(minY, sy), math.max(maxY, sy)
    end
    local step = 3 * g_pixelSizeY
    local y = math.max(minY, 0) + step * 0.5
    maxY = math.min(maxY, 1)
    while y < maxY do
        local xs = {}
        local j = #pts
        for i = 1, #pts do
            local a, b = pts[j], pts[i]
            if (a[2] > y) ~= (b[2] > y) then
                table.insert(xs, a[1] + (b[1] - a[1]) * (y - a[2]) / (b[2] - a[2]))
            end
            j = i
        end
        table.sort(xs)
        for k = 1, #xs - 1, 2 do
            drawLine2D(xs[k], y, xs[k + 1], y, step, color[1], color[2], color[3], color[4])
        end
        y = y + step
    end
end

function SprayDronePlannerScreen:drawDraft()
    local draft = self.draft
    local color = SprayDronePlannerScreen.COLOR_DRAFT
    for i = 1, #draft - 1 do
        self:drawWorldLine(draft[i].x, draft[i].z, draft[i + 1].x, draft[i + 1].z, 3, color)
    end
    local last = draft[#draft]
    if last ~= nil and not self:getIsInPanel(self.mouseX, self.mouseY) then
        local lx, ly = self:worldToScreen(last.x, last.z)
        drawLine2D(lx, ly, self.mouseX, self.mouseY, 2 * g_pixelSizeX, color[1], color[2], color[3], 0.6)
        if #draft >= 2 then
            local fx, fy = self:worldToScreen(draft[1].x, draft[1].z)
            drawLine2D(self.mouseX, self.mouseY, fx, fy, 1 * g_pixelSizeX, color[1], color[2], color[3], 0.35)
        end
    end
    for i, p in ipairs(draft) do
        if i == 1 then
            local closable = self:getIsNearFirstPoint()
            self:drawMarker(p.x, p.z, closable and 16 or 11, closable and SprayDronePlannerScreen.COLOR_HOVER or color)
        else
            self:drawMarker(p.x, p.z, 7, color)
        end
    end
end

function SprayDronePlannerScreen:drawMarker(x, z, sizePx, color)
    local sx, sy = self:worldToScreen(x, z)
    local w, h = sizePx * g_pixelSizeX, sizePx * g_pixelSizeY
    local bw, bh = 2 * g_pixelSizeX, 2 * g_pixelSizeY
    drawFilledRect(sx - w * 0.5 - bw, sy - h * 0.5 - bh, w + 2 * bw, h + 2 * bh, 0, 0, 0, 1)
    drawFilledRect(sx - w * 0.5, sy - h * 0.5, w, h, color[1], color[2], color[3], color[4] or 1)
    return sx, sy
end

function SprayDronePlannerScreen:onDrawPostIngameMap(element, ingameMap)
    if self.vehicle == nil or self.needsInit then
        return
    end
    local vehicle = self.vehicle
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)

    if self.hoverEntry ~= nil and self.hoverEntry.field:getId() ~= spec.fieldId then
        self:drawWorldPolygon(self.hoverEntry.poly, 4, SprayDronePlannerScreen.COLOR_HOVER)
    end
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field ~= nil then
        self:drawWorldPolygon(SprayDroneRoute.getPolygon(field), 5, SprayDronePlannerScreen.COLOR_SELECTED)
    end
    local area = SprayDroneStation.getFlightArea(vehicle)
    if area ~= nil then
        self:fillWorldPolygon(area, SprayDronePlannerScreen.COLOR_AREA_FILL)
        self:drawWorldPolygon(area, self.drawMode and 1 or 3, SprayDronePlannerScreen.COLOR_AREA)
    end

    -- dosah signálu: obrys sjednocení rádia vleku (spec.maxRange) a kruhů aktivních tyčí s ním spojených (SprayDroneLink.isConnected);
    -- tenký kruh je dosah z baterie (spec.range, s relé prodloužený), když se od rádia liší – za něj dávka nedoletí
    local segments = 96
    for _, line in ipairs(SprayDroneLink.getCoverageArcs(SprayDroneLink.getSignalCircles(vehicle), segments)) do
        self:drawWorldLine(line.x1, line.z1, line.x2, line.z2, 3,
            line.circle == 1 and SprayDronePlannerScreen.COLOR_RANGE or SprayDronePlannerScreen.COLOR_RELAY)
    end
    if math.abs(spec.range - spec.maxRange) > 1 then
        local c = SprayDronePlannerScreen.COLOR_RANGE
        local color = { c[1], c[2], c[3], 0.6 }
        for i = 0, segments - 1 do
            local a1, a2 = i / segments * 2 * math.pi, (i + 1) / segments * 2 * math.pi
            self:drawWorldLine(hx + math.cos(a1) * spec.range, hz + math.sin(a1) * spec.range,
                hx + math.cos(a2) * spec.range, hz + math.sin(a2) * spec.range, 1, color)
        end
    end

    for index = 1, spec.numDrones do
        local d = spec.drones[index]
        local colors = SprayDroneStation.getBatchColors(index)
        for _, leg in ipairs(d.drawLegs) do
            local c = colors[(leg.batch - 1) % #colors + 1]
            self:drawWorldLine(leg.x1, leg.z1, leg.x2, leg.z2, 2, { c[1], c[2], c[3], 1 })
        end
        for _, leg in ipairs(d.routeInfo.unplanned or {}) do
            self:drawWorldLine(leg.x1, leg.z1, leg.x2, leg.z2, 2, SprayDronePlannerScreen.COLOR_UNPLANNED)
        end
        for _, turn in ipairs(d.routeInfo.turns or {}) do
            local c = colors[(turn.batch - 1) % #colors + 1]
            for k = 2, #turn.points do
                local a, b = turn.points[k - 1], turn.points[k]
                self:drawWorldLine(a.x, a.z, b.x, b.z, 1, { c[1], c[2], c[3], 0.7 })
            end
        end
    end
    if self.drawMode then
        self:drawDraft()
    end
end

function SprayDronePlannerScreen:onDrawPostIngameMapHotspots(element, ingameMap)
    if self.vehicle == nil or self.needsInit then
        return
    end
    local vehicle = self.vehicle
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    -- tyče v okolí (do RELAY_ICON_RANGE × rádio vleku): aktivní barevně, ostatní šedě
    local near = spec.maxRange * SprayDronePlannerScreen.RELAY_ICON_RANGE
    for _, relay in ipairs(SprayDroneLink.getRelays()) do
        if MathUtil.vector2Length(relay.x - hx, relay.z - hz) <= near then
            self:drawIcon(relay.active and "mapRelay" or "mapRelayOff", relay.x, relay.z, 18)
        end
    end
    self:drawIcon("mapTrailer", hx, hz, 20)
    for k = 1, spec.numDrones do
        local d = spec.drones[k]
        if not d.isLinked and d.node ~= nil then
            local dx, _, dz = getWorldTranslation(d.node)
            self:drawIcon("mapDrone", dx, dz, 20)
        end
    end

    self:drawPanel()
end

---------------------------------------------------------------------------------------------------
-- panel s popisem

-- Panel se kreslí dvakrát: nejdřív „naměřit“ (self.measuring: nic se nekreslí, jen se sčítá výška), pak naostro. Obsah největší
-- konfigurace (Max, dva drony, mixér, vybrané pole) je vyšší než panel, proto se zkouší stupně PANEL_STAGES (menší písmo a mezery,
-- nakonec bez nápovědy k nastavení a bez legendy), dokud se vše nevejde; písmo nikdy nejde pod MIN_TEXT_PX.
function SprayDronePlannerScreen:beginText(x, y, w, stage)
    self.textX, self.textY, self.textW = x, y, w
    self.textScale = stage.scale
    self.textNoHint = stage.noHint == true
    self.textNoLegend = stage.noLegend == true
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextWrapWidth(w)
end

function SprayDronePlannerScreen:getTextSize(sizePx)
    return math.max(sizePx * self.textScale, math.min(sizePx, SprayDronePlannerScreen.MIN_TEXT_PX)) * g_pixelSizeScaledY
end

function SprayDronePlannerScreen:addText(text, sizePx, color, bold)
    local size = self:getTextSize(sizePx)
    setTextBold(bold == true)
    if not self.measuring then
        setTextColor(color[1], color[2], color[3], 1)
        renderText(self.textX, self.textY - size, size, text)
    end
    self.textY = self.textY - getTextHeight(size, text) - size * SprayDronePlannerScreen.LINE_SPACING * self.textScale
end

function SprayDronePlannerScreen:addGap(px)
    self.textY = self.textY - px * self.textScale * g_pixelSizeScaledY
end

function SprayDronePlannerScreen:endText()
    setTextWrapWidth(0)
    setTextBold(false)
    setTextColor(1, 1, 1, 1)
end

-- Řádky nastavení letu (vybraný zvýrazněný) s tlačítky − / +; obdélníky si pamatuje pro myš (handleSettingsMouse).
function SprayDronePlannerScreen:drawSettings(x, w)
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    self:addGap(6)
    self:addText(g_i18n:getText("sdt_planner_settings"), 16, SprayDronePlannerScreen.COLOR_TEXT, true)
    local size = self:getTextSize(15)
    local rowH = size * 1.6
    local boxH = rowH * 0.9
    local boxW = boxH * g_screenHeight / g_screenWidth
    local gap = 6 * g_pixelSizeScaledX
    local measuring = self.measuring
    if not measuring then
        self.settingRects = {}
    end
    setTextWrapWidth(0)
    for i, setting in ipairs(SprayDroneStation.SETTINGS) do
        if setting.minDrones == nil or spec.numDrones >= setting.minDrones then
            local y = self.textY - rowH
            if not measuring then
                if i == self.selectedSetting then
                    local c = SprayDronePlannerScreen.COLOR_SETTING
                    drawFilledRect(x, y, w, rowH, c[1], c[2], c[3], c[4])
                end
                local plus = { x + w - boxW, y + rowH * 0.05, boxW, boxH }
                local minus = { plus[1] - gap - boxW, plus[2], boxW, boxH }
                local c = SprayDronePlannerScreen.COLOR_SETTING_BOX
                drawFilledRect(minus[1], minus[2], minus[3], minus[4], c[1], c[2], c[3], c[4])
                drawFilledRect(plus[1], plus[2], plus[3], plus[4], c[1], c[2], c[3], c[4])
                local textY = y + (rowH - size) * 0.5
                setTextBold(true)
                setTextAlignment(RenderText.ALIGN_CENTER)
                setTextColor(1, 1, 1, 1)
                renderText(minus[1] + boxW * 0.5, textY, size, "–")
                renderText(plus[1] + boxW * 0.5, textY, size, "+")
                setTextAlignment(RenderText.ALIGN_LEFT)
                setTextBold(i == self.selectedSetting)
                local enabled = SprayDroneStation.isSettingEnabled(self.vehicle, i)
                if not enabled then
                    setTextColor(0.5, 0.5, 0.5, 1)
                end
                local value = spec[setting.key]
                if setting.values ~= nil then
                    value = g_i18n:getText(setting.values[math.clamp(value + 1, 1, #setting.values)])
                end
                renderText(x + gap, textY, size, string.format(g_i18n:getText(setting.text), value))
                setTextColor(1, 1, 1, 1)
                setTextBold(false)
                self.settingRects[i] = { row = { x, y, w, rowH }, minus = minus, plus = plus }
            end
            self.textY = y
        end
    end
    setTextWrapWidth(self.textW)
    self:addGap(3)
    if not self.textNoHint then
        self:addText(g_i18n:getText("sdt_planner_settingsHint"), 13, SprayDronePlannerScreen.COLOR_DIM)
    end
end

function SprayDronePlannerScreen:getFieldKindText(entry)
    if entry.mission ~= nil then
        local title = entry.mission.title or g_i18n:getText("sdt_planner_contract")
        return string.format(g_i18n:getText("sdt_planner_contractInfo"), title, math.floor((entry.mission.completion or 0) * 100))
    end
    return g_i18n:getText("sdt_planner_ownField")
end

-- Koncentrátová nádrž, míchání (voda z hlavní nádrže + koncentrát) a co chybí, když v hlavní nádrži není hotový přípravek.
function SprayDronePlannerScreen:drawMixerInfo(summary)
    if not summary.hasConcentrateTank then
        return
    end
    local T, D, W = SprayDronePlannerScreen.COLOR_TEXT, SprayDronePlannerScreen.COLOR_DIM, SprayDronePlannerScreen.COLOR_WARNING
    local fmt = string.format
    self:addText(fmt(g_i18n:getText("sdt_planner_concentrateTank"), summary.concentrateLiters, summary.concentrateCapacity,
        summary.concentrateTitle or "-"), 16, T)
    if summary.sourceKind == SprayDroneMixer.KIND_MIX then
        local limit = g_i18n:getText(summary.mixLimit == "water" and "sdt_planner_mixLimitWater" or "sdt_planner_mixLimitConcentrate")
        self:addText(fmt(g_i18n:getText("sdt_planner_mixing"), summary.mixRatio * 100, (1 - summary.mixRatio) * 100, summary.fillTypeTitle), 15, D)
        self:addText(fmt(g_i18n:getText("sdt_planner_mixAvailable"), summary.trailerLiters, limit), 15, D)
    elseif summary.sourceKind == SprayDroneMixer.KIND_NONE and summary.sourceReason ~= "empty" then
        self:addText(g_i18n:getText(summary.sourceReason == "noConcentrate" and "sdt_planner_noConcentrate" or "sdt_planner_noWater"), 16, W)
    end
end

-- Souhrn trasy všech dronů a nejvyšší překážka na jejich drahách; počítá se nejvýš jednou za SUMMARY_REFRESH_TIME, ne každý snímek.
function SprayDronePlannerScreen:getSummary()
    if self.summary == nil or self.summaryTimer <= 0 then
        local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
        self.summary = SprayDroneStation.getRouteSummaryAll(self.vehicle)
        self.summaryTimer = SprayDronePlannerScreen.SUMMARY_REFRESH_TIME
        self.highest = nil
        for index = 1, spec.numDrones do
            for _, o in ipairs(spec.drones[index].routeInfo.obstacles or {}) do
                self.highest = math.max(self.highest or 0, o.h)
            end
        end
    end
    return self.summary
end

-- Stupeň písma se pamatuje: obvykle stačí jedno měření (vejde se dosavadní stupeň), větší stupeň se zkouší nejvýš jednou
-- za PANEL_GROW_TIME. Texty stavu dronů a nabíječky se skládají jednou za snímek pro všechna měření.
function SprayDronePlannerScreen:drawPanel()
    local x, y, w, h = self:getPanelRect()
    drawFilledRect(x, y, w, h, 0.02, 0.03, 0.03, 0.9)
    self.droneTexts = SprayDroneStation.getDroneStateTexts(self.vehicle)
    self.batteryText, self.generatorText = SprayDroneStation.getPowerTexts(self.vehicle)
    local stages = SprayDronePlannerScreen.PANEL_STAGES
    local bottom = y + 6 * g_pixelSizeScaledY
    local index = math.min(self.panelStage or 1, #stages)
    self.measuring = true
    if index > 1 and g_time >= (self.panelGrowTime or 0) then
        self.panelGrowTime = g_time + SprayDronePlannerScreen.PANEL_GROW_TIME
        self:drawPanelContent(x, y, w, h, stages[index - 1])
        if self.textY >= bottom then
            index = index - 1
        end
    end
    while index < #stages do
        self:drawPanelContent(x, y, w, h, stages[index])
        if self.textY >= bottom then
            break
        end
        index = index + 1
    end
    self.measuring = false
    self.panelStage = index
    local stage = stages[index]
    self:drawPanelContent(x, y, w, h, stage)
    if stage.noLegend then
        self:drawMapLegend(x)
    end
end

-- Legenda a ovládání, když se do panelu nevejdou: malé tmavé pole vlevo dole nad lištou tlačítek.
function SprayDronePlannerScreen:drawMapLegend(panelX)
    local size = self:getTextSize(14)
    local margin = 20 * g_pixelSizeScaledX
    local w = math.min(520 * g_pixelSizeScaledX, panelX - 2 * margin)
    local texts = { g_i18n:getText("sdt_planner_legend"), g_i18n:getText("sdt_planner_legendSignal"),
        g_i18n:getText(self.drawMode and "sdt_planner_controlsDraw" or "sdt_planner_controls") }
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextBold(false)
    setTextWrapWidth(w)
    local total = 0
    for _, text in ipairs(texts) do
        total = total + getTextHeight(size, text) + size * 0.3
    end
    local bottom = (self.buttonBox ~= nil and self.buttonBox.absPosition[2] + self.buttonBox.absSize[2] or 0) + 10 * g_pixelSizeScaledY
    local pad = 6 * g_pixelSizeScaledX
    drawFilledRect(margin - pad, bottom - pad, w + 2 * pad, total + 2 * pad, 0, 0, 0, 0.65)
    local D = SprayDronePlannerScreen.COLOR_DIM
    setTextColor(D[1], D[2], D[3], 1)
    local y = bottom + total
    for _, text in ipairs(texts) do
        renderText(margin, y - size, size, text)
        y = y - getTextHeight(size, text) - size * 0.3
    end
    self:endText()
end

function SprayDronePlannerScreen:drawPanelContent(x, y, w, h, stage)
    local vehicle = self.vehicle
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local pad = 16 * g_pixelSizeScaledX
    self:beginText(x + pad, y + h - 12 * g_pixelSizeScaledY, w - 2 * pad, stage)
    local T, D, W = SprayDronePlannerScreen.COLOR_TEXT, SprayDronePlannerScreen.COLOR_DIM, SprayDronePlannerScreen.COLOR_WARNING
    local fmt = string.format

    self:addText(g_i18n:getText("sdt_planner_title"), 24, T, true)
    self:addGap(4)
    local summary = self:getSummary()
    self:addText(fmt(g_i18n:getText("sdt_planner_trailerTank"), summary.mainLiters, summary.mainTitle or summary.fillTypeTitle), 17, T)
    self:drawMixerInfo(summary)
    for index, texts in ipairs(self.droneTexts) do
        self:addText((spec.numDrones > 1 and string.format("%d: ", index) or "") .. texts[1] .. " | " .. texts[2], 17, T)
    end
    self:addText(self.batteryText, 15, T)
    self:addText(self.generatorText, 15, T)
    self:addText(fmt(g_i18n:getText("sdt_planner_drone"), g_i18n:getText("sdt_drone_" .. spec.droneName), spec.tankCapacity,
        spec.batteryKwh, #spec.batteries), 15, D)
    if #spec.batteries == 0 then
        self:addText(g_i18n:getText("sdt_warning_noBatteries"), 16, W, true)
    end
    self:addText(fmt(g_i18n:getText("sdt_planner_params"), spec.range, spec.transitHeight, spec.workWidth), 15, D)
    self:drawSettings(x + pad, w - 2 * pad)
    if spec.fieldId ~= 0 then
        self:addText(self.highest ~= nil and fmt(g_i18n:getText("sdt_planner_highestPoint"), self.highest)
            or g_i18n:getText("sdt_planner_highestPointNone"), 15, D)
    end
    self:addGap(10)

    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field == nil then
        self:addText(g_i18n:getText("sdt_planner_noField"), 18, T, true)
        self:addText(g_i18n:getText("sdt_planner_hintSelect"), 16, D)
    else
        local entry = nil
        for _, e in ipairs(self.fields) do
            if e.field == field then
                entry = e
            end
        end
        self:addText(fmt(g_i18n:getText("sdt_planner_field"), field:getName()), 20, SprayDronePlannerScreen.COLOR_SELECTED, true)
        if entry ~= nil then
            self:addText(self:getFieldKindText(entry), 16, entry.mission ~= nil and SprayDronePlannerScreen.COLOR_CONTRACT or D)
            if not entry.allowed then
                self:addText(g_i18n:getText(entry.reason), 16, W)
            end
        end
        self:addGap(4)
        if summary.area ~= nil then
            self:addText(fmt(g_i18n:getText("sdt_planner_flightArea"), #summary.area), 17, SprayDronePlannerScreen.COLOR_AREA)
        end
        if summary.noPath ~= nil then
            self:addText(g_i18n:getText(summary.noPath == SprayDroneStation.NO_PATH_HOME and "sdt_planner_areaHomeOutside"
                or "sdt_planner_areaNoPath"), 17, W, true)
            self:addText(g_i18n:getText("sdt_planner_areaFix"), 16, W)
        elseif summary.numBatches == 0 and summary.tooHigh then
            self:addText(fmt(g_i18n:getText("sdt_planner_tooHigh"), summary.maxTransitHeight), 17, W)
        elseif summary.numBatches == 0 and summary.noFuel then
            self:addText(g_i18n:getText("sdt_status_noFuel"), 17, W, true)
        elseif summary.numBatches == 0 then
            self:addText(g_i18n:getText("sdt_status_fieldDone"), 17, T)
        else
            self:addText(fmt(g_i18n:getText("sdt_planner_batches"), summary.numBatches), 17, T)
            self:addText(fmt(g_i18n:getText("sdt_planner_time"), summary.minutes), 17, T)
            self:addText(fmt(g_i18n:getText("sdt_planner_service"), summary.serviceMinutes, summary.waitMinutes), 15,
                summary.waitMinutes > 0.05 and SprayDronePlannerScreen.COLOR_CONTRACT or D)
            local fuelShort = summary.noFuel or summary.fuelRunsOut
            self:addText(fmt(g_i18n:getText("sdt_planner_diesel"), summary.dieselUsed, summary.diesel), 17, fuelShort and W or T)
            if summary.noFuel then
                self:addText(g_i18n:getText("sdt_planner_noFuel"), 16, W)
            elseif summary.fuelRunsOut then
                self:addText(g_i18n:getText("sdt_planner_fuelRunsOut"), 16, W)
            end
            self:addText(fmt(g_i18n:getText("sdt_planner_battery"), summary.batteryPercent, summary.batterySwaps), 17, T)
            self:addText(fmt(g_i18n:getText("sdt_planner_batteryLife"), summary.batteryMinutesFull, summary.batteryMinutesEmpty), 15, D)
            self:addText(fmt(g_i18n:getText(summary.area ~= nil and "sdt_planner_transitLengthArea" or "sdt_planner_transitLength"),
                summary.firstOut, summary.firstBack, summary.transitLength / 1000), 17, T)
            self:addText(fmt(g_i18n:getText(summary.obstacleRaised and "sdt_planner_transitObstacle" or "sdt_planner_transit"),
                summary.transitHeight), 17, summary.obstacleRaised and SprayDronePlannerScreen.COLOR_CONTRACT or T)
            if summary.tooHigh then
                self:addText(fmt(g_i18n:getText("sdt_planner_tooHigh"), summary.maxTransitHeight), 16, W)
            end
            self:addText(fmt(g_i18n:getText("sdt_planner_area"), summary.areaHa), 17, T)
            local enough = summary.availableLiters + 0.5 >= summary.liters
            self:addText(fmt(g_i18n:getText("sdt_planner_liters"), summary.liters, summary.availableLiters), 17, enough and T or W)
            if not enough then
                self:addText(g_i18n:getText("sdt_planner_notEnough"), 16, W)
            end
            self:addText(fmt(g_i18n:getText("sdt_planner_product"), summary.fillTypeTitle), 17, T)
            if summary.partlyOutOfRange then
                self:addText(g_i18n:getText("sdt_planner_clipped"), 16, W)
            end
            if summary.clipped and not summary.noFuel then
                self:addText(g_i18n:getText("sdt_status_unreachable"), 16, W)
            end
        end
    end

    for index = 1, spec.numDrones do
        local statusText = SprayDroneStation.STATUS_TEXTS[spec.drones[index].status]
        if statusText ~= nil then
            self:addGap(6)
            self:addText((spec.numDrones > 1 and string.format("%d: ", index) or "") .. g_i18n:getText(statusText), 16, W)
        end
    end

    self:addGap(12)
    if self.drawMode then
        self:addText(fmt(g_i18n:getText("sdt_planner_drawing"), #self.draft), 17, SprayDronePlannerScreen.COLOR_DRAFT, true)
        self:addText(g_i18n:getText("sdt_planner_drawHint"), 16, D)
    end
    if self.hoverEntry ~= nil and self.hoverEntry.field ~= field then
        local e = self.hoverEntry
        self:addText(fmt(g_i18n:getText("sdt_planner_hover"), e.field:getName()), 17, T, true)
        if e.allowed then
            self:addText(self:getFieldKindText(e), 16, e.mission ~= nil and SprayDronePlannerScreen.COLOR_CONTRACT or D)
            self:addText(g_i18n:getText("sdt_planner_clickToSelect"), 16, SprayDronePlannerScreen.COLOR_SELECTED)
        else
            self:addText(g_i18n:getText(e.reason), 16, W)
        end
    end
    if self.message ~= nil then
        self:addGap(6)
        self:addText(self.message.text, 17, self.message.isWarning and W or SprayDronePlannerScreen.COLOR_SELECTED, true)
    end

    -- legenda dole na panelu, ale nikdy přes text nad ní: když obsah sahá níž, jde legenda hned za něj (a drawPanel zkusí menší stupeň)
    if not self.textNoLegend then
        self.textY = math.min(self.textY - 8 * self.textScale * g_pixelSizeScaledY, y + 150 * g_pixelSizeScaledY)
        self:addText(g_i18n:getText("sdt_planner_legend"), 14, D)
        self:addText(g_i18n:getText("sdt_planner_legendSignal"), 14, D)
        self:addText(g_i18n:getText(self.drawMode and "sdt_planner_controlsDraw" or "sdt_planner_controls"), 14, D)
    end
    self:endText()
end
