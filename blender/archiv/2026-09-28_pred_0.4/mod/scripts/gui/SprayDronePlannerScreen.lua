-- Plánovač letu dronu: celoobrazovková mapa (herní InGameMap, stejná jako v menu mapy) s vlekem,
-- kruhem dosahu, poli v okolí a naplánovanou trasou. Klik na pole ho vybere, tlačítka spouští let
-- a volají dron domů. Výběr i start jdou přes SprayDroneStation (a tím eventem na server).

SprayDronePlannerScreen = {}
SprayDronePlannerScreen.MOD_DIR = g_currentModDirectory
SprayDronePlannerScreen.GUI_NAME = "SprayDronePlannerScreen"
SprayDronePlannerScreen.FIELD_REFRESH_TIME = 1000
SprayDronePlannerScreen.MESSAGE_TIME = 5000
SprayDronePlannerScreen.PANEL_WIDTH_PX = 470

SprayDronePlannerScreen.COLOR_RANGE = { 0, 0.9, 1, 1 }
SprayDronePlannerScreen.COLOR_SELECTED = { 0.2, 1, 0.2, 1 }
SprayDronePlannerScreen.COLOR_OWN = { 0.35, 0.75, 1, 0.9 }
SprayDronePlannerScreen.COLOR_CONTRACT = { 1, 0.78, 0.1, 1 }
SprayDronePlannerScreen.COLOR_DENIED = { 0.95, 0.25, 0.2, 0.75 }
SprayDronePlannerScreen.COLOR_HOVER = { 1, 1, 1, 1 }
SprayDronePlannerScreen.COLOR_TRAILER = { 1, 0.45, 0, 1 }
SprayDronePlannerScreen.COLOR_WARNING = { 1, 0.35, 0.3 }
SprayDronePlannerScreen.COLOR_TEXT = { 1, 1, 1 }
SprayDronePlannerScreen.COLOR_DIM = { 0.75, 0.75, 0.75 }

local SprayDronePlannerScreen_mt = Class(SprayDronePlannerScreen, ScreenElement)

function SprayDronePlannerScreen.new()
    local self = ScreenElement.new(nil, SprayDronePlannerScreen_mt)
    self.vehicle = nil
    self.fields = {}
    self.fieldTimer = 0
    self.hoverEntry = nil
    self.message = nil
    self.messageTimer = 0
    self.needsInit = false
    self.mouseX, self.mouseY = 0.5, 0.5
    return self
end

function SprayDronePlannerScreen.show(vehicle)
    if SprayDronePlannerScreen.INSTANCE == nil then
        local screen = SprayDronePlannerScreen.new()
        g_gui:loadGui(SprayDronePlannerScreen.MOD_DIR .. "gui/SprayDronePlannerScreen.xml", SprayDronePlannerScreen.GUI_NAME, screen)
        SprayDronePlannerScreen.INSTANCE = screen
    end
    SprayDronePlannerScreen.INSTANCE.vehicle = vehicle
    g_gui:showGui(SprayDronePlannerScreen.GUI_NAME)
end

function SprayDronePlannerScreen:onOpen()
    SprayDronePlannerScreen:superClass().onOpen(self)
    self.mapBase = g_currentMission.hud:getIngameMap()
    self.ingameMap:setIngameMap(self.mapBase)
    self.ingameMap:setTerrainSize(g_currentMission.terrainSize)
    self.mapBase:restoreDefaultFilter()
    self.closeButton:setText(g_i18n:getText("sdt_button_close"))
    self.startButton:setText(g_i18n:getText("sdt_button_start"))
    self.returnButton:setText(g_i18n:getText("sdt_button_returnHome"))
    self.fieldTimer = 0
    self.hoverEntry = nil
    self.message = nil
    -- mapa se přepne na celou obrazovku až v onOpen svého prvku (volá se po tomhle), proto přiblížení
    -- a vycentrování na vlek až v prvním update
    self.needsInit = true
end

function SprayDronePlannerScreen:onClose()
    SprayDronePlannerScreen:superClass().onClose(self)
    self.vehicle = nil
    self.fields = {}
end

function SprayDronePlannerScreen:onClickBack()
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
    -- na výšku obrazovky se vejde zhruba 2,8× dosah
    local zoom = g_currentMission.terrainSize / (2.8 * spec.range * sizeRatio)
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
    return SprayDronePlannerScreen:superClass().mouseEvent(self, posX, posY, isDown, isUp, button, eventUsed)
end

function SprayDronePlannerScreen:getIsVehicleUsable()
    local vehicle = self.vehicle
    return vehicle ~= nil and not vehicle.isDeleted and not vehicle.isDeleting
        and vehicle:getIsEntered() and vehicle:getIsUnfolded()
end

function SprayDronePlannerScreen:update(dt)
    SprayDronePlannerScreen:superClass().update(self, dt)
    if not self:getIsOpen() then
        return
    end
    if not self:getIsVehicleUsable() then
        g_gui:showGui("")
        return
    end
    if self.needsInit then
        self:initMapView()
    end

    SprayDroneStation.refreshRoutePreview(self.vehicle, dt)
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
    self.startButton:setDisabled(not SprayDroneStation.getCanStart(self.vehicle) or spec.numBatches == 0)
    self.returnButton:setDisabled(not SprayDroneStation.getCanReturnHome(self.vehicle))
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
            if #poly >= 3 and SprayDroneRoute.distanceToPolygon(poly, hx, hz) <= spec.range * 2 then
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
    self.hoverEntry = nil
    if self:getIsInPanel(self.mouseX, self.mouseY) then
        return
    end
    local lx, ly = self.ingameMap:getLocalPosition(self.mouseX, self.mouseY)
    local wx, wz = self.ingameMap:localToWorldPos(lx, ly)
    self.hoverEntry = self:getEntryAt(wx, wz)
end

function SprayDronePlannerScreen:showMessage(text, isWarning)
    self.message = { text = text, isWarning = isWarning }
    self.messageTimer = SprayDronePlannerScreen.MESSAGE_TIME
end

function SprayDronePlannerScreen:onClickMap(element, worldX, worldZ)
    if self.vehicle == nil or self:getIsInPanel(self.mouseX, self.mouseY) then
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

    for _, entry in ipairs(self.fields) do
        if entry.field:getId() ~= spec.fieldId then
            local color = SprayDronePlannerScreen.COLOR_DENIED
            local thickness = 2
            if entry.allowed then
                color = entry.mission ~= nil and SprayDronePlannerScreen.COLOR_CONTRACT or SprayDronePlannerScreen.COLOR_OWN
                thickness = 3
            end
            self:drawWorldPolygon(entry.poly, thickness, color)
        end
    end
    if self.hoverEntry ~= nil and self.hoverEntry.field:getId() ~= spec.fieldId then
        self:drawWorldPolygon(self.hoverEntry.poly, 4, SprayDronePlannerScreen.COLOR_HOVER)
    end
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field ~= nil then
        self:drawWorldPolygon(SprayDroneRoute.getPolygon(field), 5, SprayDronePlannerScreen.COLOR_SELECTED)
    end

    local segments = 96
    for i = 0, segments - 1 do
        local a1, a2 = i / segments * 2 * math.pi, (i + 1) / segments * 2 * math.pi
        self:drawWorldLine(hx + math.cos(a1) * spec.range, hz + math.sin(a1) * spec.range,
            hx + math.cos(a2) * spec.range, hz + math.sin(a2) * spec.range, 3, SprayDronePlannerScreen.COLOR_RANGE)
    end

    local colors = SprayDroneStation.BATCH_COLORS
    for _, leg in ipairs(spec.drawLegs) do
        local c = colors[(leg.batch - 1) % #colors + 1]
        self:drawWorldLine(leg.x1, leg.z1, leg.x2, leg.z2, 2, { c[1], c[2], c[3], 1 })
    end

    if not spec.isLinked and spec.node ~= nil then
        local dx, _, dz = getWorldTranslation(spec.node)
        self:drawMarker(dx, dz, 10, SprayDronePlannerScreen.COLOR_RANGE)
    end
end

function SprayDronePlannerScreen:onDrawPostIngameMapHotspots(element, ingameMap)
    if self.vehicle == nil or self.needsInit then
        return
    end
    local vehicle = self.vehicle
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)
    local sx, sy = self:drawMarker(hx, hz, 14, SprayDronePlannerScreen.COLOR_TRAILER)
    local size = 16 * g_pixelSizeScaledY
    setTextBold(true)
    setTextAlignment(RenderText.ALIGN_CENTER)
    setTextColor(0, 0, 0, 1)
    renderText(sx + g_pixelSizeX, sy + 14 * g_pixelSizeY - g_pixelSizeY, size, g_i18n:getText("sdt_planner_trailer"))
    setTextColor(1, 0.6, 0.2, 1)
    renderText(sx, sy + 14 * g_pixelSizeY, size, g_i18n:getText("sdt_planner_trailer"))

    for _, entry in ipairs(self.fields) do
        if entry.mission ~= nil then
            local fx, fz = entry.field:getCenterOfFieldWorldPosition()
            local lx, ly = self:worldToScreen(fx, fz)
            setTextColor(0, 0, 0, 1)
            renderText(lx + g_pixelSizeX, ly - 22 * g_pixelSizeY - g_pixelSizeY, size, g_i18n:getText("sdt_planner_contractTag"))
            setTextColor(1, 0.78, 0.1, 1)
            renderText(lx, ly - 22 * g_pixelSizeY, size, g_i18n:getText("sdt_planner_contractTag"))
        end
    end
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextBold(false)
    setTextColor(1, 1, 1, 1)

    self:drawPanel()
end

---------------------------------------------------------------------------------------------------
-- panel s popisem

function SprayDronePlannerScreen:beginText(x, y, w)
    self.textX, self.textY, self.textW = x, y, w
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextWrapWidth(w)
end

function SprayDronePlannerScreen:addText(text, sizePx, color, bold)
    local size = sizePx * g_pixelSizeScaledY
    setTextBold(bold == true)
    setTextColor(color[1], color[2], color[3], 1)
    renderText(self.textX, self.textY - size, size, text)
    self.textY = self.textY - getTextHeight(size, text) - size * 0.3
end

function SprayDronePlannerScreen:addGap(px)
    self.textY = self.textY - px * g_pixelSizeScaledY
end

function SprayDronePlannerScreen:endText()
    setTextWrapWidth(0)
    setTextBold(false)
    setTextColor(1, 1, 1, 1)
end

function SprayDronePlannerScreen:getFieldKindText(entry)
    if entry.mission ~= nil then
        local title = entry.mission.title or g_i18n:getText("sdt_planner_contract")
        return string.format(g_i18n:getText("sdt_planner_contractInfo"), title, math.floor((entry.mission.completion or 0) * 100))
    end
    return g_i18n:getText("sdt_planner_ownField")
end

function SprayDronePlannerScreen:drawPanel()
    local vehicle = self.vehicle
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local x, y, w, h = self:getPanelRect()
    drawFilledRect(x, y, w, h, 0.02, 0.03, 0.03, 0.9)
    local pad = 16 * g_pixelSizeScaledX
    self:beginText(x + pad, y + h - 12 * g_pixelSizeScaledY, w - 2 * pad)
    local T, D, W = SprayDronePlannerScreen.COLOR_TEXT, SprayDronePlannerScreen.COLOR_DIM, SprayDronePlannerScreen.COLOR_WARNING
    local fmt = string.format

    self:addText(g_i18n:getText("sdt_planner_title"), 24, T, true)
    self:addGap(4)
    local summary = SprayDroneStation.getRouteSummary(vehicle)
    self:addText(fmt(g_i18n:getText("sdt_planner_trailerTank"), summary.trailerLiters, summary.fillTypeTitle), 17, T)
    self:addText(SprayDroneStation.getDroneStateText(vehicle), 17, T)
    self:addText(fmt(g_i18n:getText("sdt_planner_params"), spec.range, spec.workWidth), 15, D)
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
        if summary.numBatches == 0 then
            self:addText(g_i18n:getText("sdt_status_fieldDone"), 17, T)
        else
            self:addText(fmt(g_i18n:getText("sdt_planner_batches"), summary.numBatches), 17, T)
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
            if summary.clipped then
                self:addText(g_i18n:getText("sdt_status_unreachable"), 16, W)
            end
        end
    end

    local statusText = SprayDroneStation.STATUS_TEXTS[spec.status]
    if statusText ~= nil then
        self:addGap(6)
        self:addText(g_i18n:getText(statusText), 16, W)
    end

    self:addGap(12)
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

    self.textY = y + 150 * g_pixelSizeScaledY
    self:addText(g_i18n:getText("sdt_planner_legend"), 14, D)
    self:addText(g_i18n:getText("sdt_planner_controls"), 14, D)
    self:endText()
end
