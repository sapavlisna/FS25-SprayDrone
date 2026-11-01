-- Karta plánu vpravo nahoře (jako okno zůstatku v herní mapě): vybrané pole, varování jako barevné štítky, klíčová čísla mise
-- v dlaždicích s ikonami, úspora podle skenu a stav vleku. Metody plánovače, kreslí se z jeho draw() nad herními prvky.

local UI = SprayDronePlannerScreen.UI

local function px(value)
    return value * g_pixelSizeScaledY
end

local function pxX(value)
    return value * g_pixelSizeScaledX
end

local function setColor(c, alpha)
    setTextColor(c[1], c[2], c[3], alpha or c[4] or 1)
end

local function fillRect(x, y, w, h, c)
    drawFilledRect(x, y, w, h, c[1], c[2], c[3], c[4] or 1)
end

function SprayDronePlannerScreen:getFieldKindText(entry)
    if entry.mission ~= nil then
        local title = entry.mission.title or g_i18n:getText("sdt_planner_contract")
        return string.format(g_i18n:getText("sdt_planner_contractInfo"), title, math.floor((entry.mission.completion or 0) * 100))
    end
    return g_i18n:getText("sdt_planner_ownField")
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

function SprayDronePlannerScreen:getFieldEntry(field)
    for _, e in ipairs(self.fields) do
        if e.field == field then
            return e
        end
    end
    return nil
end

-- Obsah karty: { title, subtitle, subtitleColor, chips = { {text, kind} }, tiles = { {icon, label, value, color} }, spot, lines }.
function SprayDronePlannerScreen:getCardModel()
    local vehicle = self.vehicle
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local summary = self:getSummary()
    local fmt = string.format
    local model = { chips = {}, tiles = {}, lines = {}, details = {} }
    local function chip(text, kind)
        table.insert(model.chips, { text = text, kind = kind })
    end
    local function tile(icon, label, value, color)
        table.insert(model.tiles, { icon = icon, label = label, value = value, color = color })
    end

    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field == nil then
        model.title = g_i18n:getText("sdt_ui_noField")
        model.subtitle = g_i18n:getText("sdt_ui_noFieldHint")
        model.subtitleColor = UI.dim
    else
        local entry = self:getFieldEntry(field)
        model.title = fmt(g_i18n:getText("sdt_planner_field"), field:getName())
        model.subtitle = entry ~= nil and self:getFieldKindText(entry) or g_i18n:getText("sdt_planner_ownField")
        model.subtitleColor = entry ~= nil and entry.mission ~= nil and SprayDronePlannerScreen.COLOR_CONTRACT or UI.dim
        if entry ~= nil and not entry.allowed then
            chip(g_i18n:getText(entry.reason), "warn")
        end
    end

    if self.drawMode then
        chip(fmt(g_i18n:getText("sdt_planner_drawing"), #self.draft), "area")
    elseif summary.area ~= nil then
        chip(fmt(g_i18n:getText("sdt_planner_flightArea"), #summary.area), "area")
    end
    if not spec.hasDrone then
        chip(g_i18n:getText("sdt_pad_noDrone"), "warn")
    elseif SprayDroneStation.getFoldedWarning(vehicle) ~= nil then
        chip(g_i18n:getText(SprayDroneStation.getFoldedWarning(vehicle)), "warn")
    end
    if #spec.batteries == 0 then
        chip(g_i18n:getText("sdt_warning_noBatteries"), "warn")
    end
    if summary.hasConcentrateTank and summary.sourceKind == SprayDroneMixer.KIND_NONE and summary.sourceReason ~= "empty" then
        chip(g_i18n:getText(summary.sourceReason == "noConcentrate" and "sdt_planner_noConcentrate" or "sdt_planner_noWater"), "warn")
    end

    local blocker, _, maxWind = SprayDroneStation.getWeatherBlocker(vehicle)
    local wind = SprayDroneScanMap.getWindSpeed()
    if blocker ~= nil then
        chip(fmt(g_i18n:getText("sdt_planner_weather"), wind ~= nil and fmt("%.1f", wind) or "?", maxWind,
            g_i18n:getText("sdt_weather_" .. blocker)), "warn")
    end

    if field ~= nil then
        if summary.noPath ~= nil then
            chip(g_i18n:getText(summary.noPath == SprayDroneStation.NO_PATH_HOME and "sdt_planner_areaHomeOutside" or "sdt_planner_areaNoPath")
                .. " " .. g_i18n:getText("sdt_planner_areaFix"), "warn")
        elseif summary.numBatches == 0 and summary.tooHigh then
            chip(fmt(g_i18n:getText("sdt_planner_tooHigh"), summary.maxTransitHeight), "warn")
        elseif summary.numBatches == 0 and summary.noFuel then
            chip(g_i18n:getText(spec.portable and "sdt_status_noCharge" or "sdt_status_noFuel"), "warn")
        elseif summary.numBatches == 0 and spec.isSamplerDrone then
            local reason = SprayDroneSamples.getStartWarning(vehicle) or "sdt_status_samplesDone"
            chip(g_i18n:getText(reason), reason == "sdt_status_samplesDone" and "ok" or "warn")
        elseif summary.numBatches == 0 then
            chip(g_i18n:getText(summary.isScan and "sdt_status_scanDone" or "sdt_status_fieldDone"), "ok")
        else
            local fuelShort = summary.noFuel or summary.fuelRunsOut
            tile("uiBatches", g_i18n:getText("sdt_ui_batches"), fmt("%d", summary.numBatches))
            tile("uiTime", g_i18n:getText("sdt_ui_time"), fmt("%.1f min", summary.minutes),
                summary.waitMinutes > 0.05 and SprayDronePlannerScreen.COLOR_CONTRACT or nil)
            if spec.isSamplerDrone then
                local s = SprayDroneSamples.getInfo(vehicle)
                tile("uiArea", g_i18n:getText("sdt_ui_samplePoints"), fmt("%d / %d", s.remaining - s.far - s.tall, s.total))
                tile("uiScan", g_i18n:getText("sdt_ui_sampleBox"), fmt("%d / %d", s.box + s.carried, s.boxCapacity),
                    s.box + s.carried >= s.boxCapacity and UI.warn or nil)
            else
                tile("uiArea", g_i18n:getText("sdt_ui_area"), fmt("%.2f ha", summary.areaHa))
            end
            if spec.isSamplerDrone then
                if spec.routeInfo.boxLimited then
                    chip(g_i18n:getText("sdt_sampler_boxLimited"), "info")
                end
            elseif summary.isScan then
                local level = summary.scanLevel
                tile("uiScan", g_i18n:getText("sdt_ui_scanCell"), fmt("%d m · %.0f m", level.cell, level.height))
            else
                local enough = summary.availableLiters + 0.5 >= summary.liters
                tile("uiLiquid", g_i18n:getText("sdt_ui_liquid"), fmt("%.0f / %.0f l", summary.liters, summary.availableLiters),
                    not enough and UI.warn or nil)
                if not enough then
                    chip(g_i18n:getText("sdt_planner_notEnough"), "warn")
                end
            end
            if not spec.portable then
                tile("uiDiesel", g_i18n:getText("sdt_ui_diesel"), fmt("%.1f / %.0f l", summary.dieselUsed, summary.diesel),
                    fuelShort and UI.warn or nil)
            end
            tile("uiBattery", g_i18n:getText("sdt_ui_battery"), fmt("%.0f %% · %d×", summary.batteryPercent, summary.batterySwaps))
            tile("uiTransit", g_i18n:getText("sdt_ui_transit"), fmt("%.0f m · %.1f km", summary.transitHeight, summary.transitLength / 1000),
                summary.obstacleRaised and SprayDronePlannerScreen.COLOR_CONTRACT or nil)
            if summary.noFuel then
                chip(g_i18n:getText(spec.portable and "sdt_planner_noCharge" or "sdt_planner_noFuel"), "warn")
            elseif summary.fuelRunsOut then
                chip(g_i18n:getText("sdt_planner_fuelRunsOut"), "info")
            end
            if summary.tooHigh then
                chip(fmt(g_i18n:getText("sdt_planner_tooHigh"), summary.maxTransitHeight), "warn")
            end
            if summary.partlyOutOfRange then
                chip(g_i18n:getText("sdt_planner_clipped"), "info")
            end
            if summary.clipped and not summary.noFuel then
                chip(g_i18n:getText("sdt_status_unreachable"), "info")
            end
            if summary.obstacleRaised then
                chip(fmt(g_i18n:getText("sdt_planner_transitObstacle"), summary.transitHeight), "info")
            end
            if not summary.isScan then
                model.product = fmt(g_i18n:getText("sdt_planner_product"), summary.fillTypeTitle)
            end
            -- podrobnosti k dlaždicím (servis, výdrž baterie, délky přeletů)
            table.insert(model.details, fmt(g_i18n:getText("sdt_planner_service"), summary.serviceMinutes, summary.waitMinutes))
            table.insert(model.details, fmt(g_i18n:getText("sdt_planner_batteryLife"), summary.batteryMinutesFull, summary.batteryMinutesEmpty))
            table.insert(model.details, fmt(g_i18n:getText(summary.area ~= nil and "sdt_planner_transitLengthArea" or "sdt_planner_transitLength"),
                summary.firstOut, summary.firstBack, summary.transitLength / 1000))
        end
        if summary.spotProblem ~= nil then
            chip(g_i18n:getText(summary.spotProblem == "noMap" and "sdt_spot_noMap" or "sdt_spot_noProduct"), "info")
        end
        local spot = summary.spot
        if spot ~= nil then
            model.spot = { cells = fmt(g_i18n:getText("sdt_spot_cells"), spot.selected, spot.cells, spot.unscanned, spot.margin) }
            if spot.fullLiters ~= nil and summary.numBatches > 0 then
                model.spot.value = fmt("%.0f l · %.0f min", summary.liters, summary.minutes)
                local saving = spot.fullLiters > 0 and (1 - summary.liters / spot.fullLiters) * 100 or 0
                model.spot.full = fmt(g_i18n:getText("sdt_ui_spotFull"), spot.fullLiters, spot.fullMinutes, saving)
            end
            if spot.stale then
                chip(fmt(g_i18n:getText("sdt_spot_stale"), spot.ageHours), "info")
            end
        end
        if spec.isSamplerDrone then
            model.scan = SprayDroneSamples.getCardText(vehicle)
        elseif summary.scanSummary ~= nil then
            local s = summary.scanSummary
            local text = fmt(g_i18n:getText("sdt_planner_scanMap"), s.coverage * 100, summary.scanMapCell, summary.scanAge)
            if s.scanned > 0 then
                text = text .. "\n" .. fmt(g_i18n:getText("sdt_planner_scanFindings"), s.weedCells / s.scanned * 100, s.invisibleWeedCells,
                    s.unfertilizedCells / s.scanned * 100)
            end
            if s.avgNitrogen ~= nil then
                text = text .. "\n" .. fmt(g_i18n:getText("sdt_planner_scanPf"), s.avgNitrogen, s.minNitrogen or 0, s.maxNitrogen or 0)
            end
            model.scan = text
        end
    end
    tile("uiWeather", g_i18n:getText("sdt_ui_weather"), fmt("%s / %.0f m/s", wind ~= nil and fmt("%.1f", wind) or "?", maxWind),
        blocker ~= nil and UI.warn or nil)

    for index = 1, spec.numDrones do
        local statusText = SprayDroneStation.STATUS_TEXTS[spec.drones[index].status]
        if statusText ~= nil then
            chip((spec.numDrones > 1 and fmt("%d: ", index) or "") .. g_i18n:getText(statusText), "info")
        end
    end

    -- stav vleku (nádrže, drony, baterie, centrála)
    local lines = model.lines
    -- kufr skenovacího dronu nádrže nemá
    if not spec.portable then
        table.insert(lines, fmt(g_i18n:getText("sdt_planner_trailerTank"), summary.mainLiters, summary.mainTitle or summary.fillTypeTitle))
    end
    if summary.hasConcentrateTank then
        table.insert(lines, fmt(g_i18n:getText("sdt_planner_concentrateTank"), summary.concentrateLiters, summary.concentrateCapacity,
            summary.concentrateTitle or "-"))
        if summary.sourceKind == SprayDroneMixer.KIND_MIX then
            table.insert(lines, fmt(g_i18n:getText("sdt_planner_mixing"), summary.mixRatio * 100, (1 - summary.mixRatio) * 100, summary.fillTypeTitle))
            local limit = g_i18n:getText(summary.mixLimit == "water" and "sdt_planner_mixLimitWater" or "sdt_planner_mixLimitConcentrate")
            table.insert(lines, fmt(g_i18n:getText("sdt_planner_mixAvailable"), summary.trailerLiters, limit))
        end
    end
    for index, texts in ipairs(SprayDroneStation.getDroneStateTexts(vehicle)) do
        table.insert(lines, (spec.numDrones > 1 and fmt("%d: ", index) or "") .. texts[1] .. " · " .. texts[2])
    end
    local batteryText, generatorText = SprayDroneStation.getPowerTexts(vehicle)
    table.insert(lines, batteryText)
    table.insert(lines, generatorText)
    if spec.hasDrone and (spec.isScanDrone or spec.isSamplerDrone) then
        table.insert(lines, fmt(g_i18n:getText("sdt_planner_scanDrone"), g_i18n:getText("sdt_drone_" .. spec.droneName), spec.batteryKwh, #spec.batteries))
    elseif spec.hasDrone then
        table.insert(lines, fmt(g_i18n:getText("sdt_planner_drone"), g_i18n:getText("sdt_drone_" .. spec.droneName), spec.tankCapacity,
            spec.batteryKwh, #spec.batteries))
    end
    table.insert(lines, fmt(g_i18n:getText("sdt_planner_params"), spec.range, spec.transitHeight, spec.workWidth))
    if field ~= nil then
        table.insert(lines, self.highest ~= nil and fmt(g_i18n:getText("sdt_planner_highestPoint"), self.highest)
            or g_i18n:getText("sdt_planner_highestPointNone"))
    end
    return model
end

SprayDronePlannerScreen.CHIP_COLORS = {
    warn = { UI.warnBg, UI.warn },
    info = { UI.infoBg, UI.info },
    ok = { UI.okBg, UI.accent },
    area = { { 0.15, 0.06, 0.3, 0.95 }, SprayDronePlannerScreen.COLOR_AREA }
}

-- Rozvržení karty: draw = false jen měří (vrací výšku). compact: bez řádků stavu vleku kromě prvních dvou.
function SprayDronePlannerScreen:layoutCard(model, x, top, w, draw, compact)
    local pad = pxX(18)
    local padY = px(16)
    local inner = w - 2 * pad
    local y = top - padY
    setTextAlignment(RenderText.ALIGN_LEFT)

    local function text(t, size, color, bold, tx, width)
        local s = px(size)
        setTextBold(bold == true)
        setTextWrapWidth(width or inner)
        local h = getTextHeight(s, t)
        if draw then
            setColor(color)
            renderText(tx or (x + pad), y - s, s, t)
        end
        y = y - h
        return h
    end

    -- hlavička: štítek, název pole, druh
    if draw then
        fillRect(x, top - px(76), pxX(4), px(60), UI.accent)
    end
    text(utf8ToUpper(g_i18n:getText("sdt_ui_cardTitle")), 13, UI.dim, true)
    y = y - px(3)
    text(utf8ToUpper(model.title), 24, UI.text, true)
    y = y - px(2)
    text(model.subtitle, 15, model.subtitleColor)
    if model.product ~= nil then
        text(model.product, 15, UI.dim)
    end
    y = y - px(12)
    if draw then
        fillRect(x + pad, y, inner, px(1), UI.cardLine)
    end
    y = y - px(12)

    -- štítky (varování, informace, letová plocha)
    for _, c in ipairs(model.chips) do
        local colors = SprayDronePlannerScreen.CHIP_COLORS[c.kind] or SprayDronePlannerScreen.CHIP_COLORS.info
        local s = px(14)
        setTextBold(false)
        setTextWrapWidth(inner - pxX(22))
        local h = getTextHeight(s, c.text) + px(12)
        if draw then
            fillRect(x + pad, y - h, inner, h, colors[1])
            fillRect(x + pad, y - h, pxX(4), h, colors[2])
            setColor(UI.text)
            renderText(x + pad + pxX(14), y - px(6) - s, s, c.text)
        end
        y = y - h - px(6)
    end
    if #model.chips > 0 then
        y = y - px(4)
    end

    -- dlaždice: dva sloupce, ikona, popisek, hodnota
    local gap = pxX(8)
    local tileW = (inner - gap) * 0.5
    local tileH = px(54)
    for i, t in ipairs(model.tiles) do
        local col = (i - 1) % 2
        local tx = x + pad + col * (tileW + gap)
        if draw then
            fillRect(tx, y - tileH, tileW, tileH, UI.tile)
            self:drawIconAt(t.icon, tx + pxX(10), y - tileH * 0.5 - px(13), 26, t.color or UI.accentText)
            setTextWrapWidth(0)
            setTextBold(true)
            setColor(UI.dim)
            renderText(tx + pxX(46), y - px(8) - px(12), px(12), utf8ToUpper(t.label))
            setColor(t.color or UI.text)
            renderText(tx + pxX(46), y - px(26) - px(17), px(17), t.value)
        end
        if col == 1 or i == #model.tiles then
            y = y - tileH - px(8)
        end
    end

    -- úspora podle skenu
    if model.spot ~= nil then
        y = y - px(4)
        local startY = y
        local boxTop = y
        y = y - px(10)
        local function spotLines()
            text(utf8ToUpper(g_i18n:getText("sdt_ui_spotTitle")), 13, UI.accentText, true, x + pad + pxX(14), inner - pxX(24))
            if model.spot.value ~= nil then
                text(model.spot.value, 20, UI.text, true, x + pad + pxX(14), inner - pxX(24))
                text(model.spot.full, 14, UI.dim, false, x + pad + pxX(14), inner - pxX(24))
            end
            text(model.spot.cells, 13, UI.dim, false, x + pad + pxX(14), inner - pxX(24))
        end
        if draw then
            local savedDraw = draw
            draw = false
            spotLines()
            local h = startY - y + px(10)
            y = startY - px(10)
            draw = savedDraw
            fillRect(x + pad, boxTop - h, inner, h, UI.okBg)
            fillRect(x + pad, boxTop - h, pxX(4), h, UI.accent)
        end
        spotLines()
        y = y - px(14)
    end

    if not compact then
        for _, line in ipairs(model.details) do
            text(line, 13, UI.dim)
            y = y - px(2)
        end
        if #model.details > 0 then
            y = y - px(6)
        end
    end
    if model.scan ~= nil then
        text(model.scan, 14, UI.dim)
        y = y - px(8)
    end

    -- stav vleku
    if draw then
        fillRect(x + pad, y, inner, px(1), UI.cardLine)
    end
    y = y - px(10)
    text(utf8ToUpper(g_i18n:getText("sdt_ui_trailer")), 13, UI.dim, true)
    y = y - px(4)
    for i, line in ipairs(model.lines) do
        if compact and i > 2 then
            break
        end
        text(line, 14, UI.text)
        y = y - px(3)
    end
    return top - y + padY
end

function SprayDronePlannerScreen:drawCard()
    local x, bottom, w, maxH = self:getCardBounds()
    local top = bottom + maxH
    local model = self:getCardModel()
    local compact = false
    local h = self:layoutCard(model, x, top, w, false, false)
    if h > maxH then
        compact = true
        h = self:layoutCard(model, x, top, w, false, true)
    end
    h = math.min(h, maxH)
    self.cardRect = { x, top - h, w, h }
    fillRect(x, top - h, w, h, UI.card)
    self:layoutCard(model, x, top, w, true, compact)
end

-- Bublina u kurzoru nad polem: název, druh nebo důvod, proč nejde, a výzva ke kliknutí.
function SprayDronePlannerScreen:drawHoverTip()
    local e = self.hoverEntry
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    if e == nil or self.drawMode then
        return
    end
    local lines = { { string.format(g_i18n:getText("sdt_planner_field"), e.field:getName()), 17, UI.text, true } }
    if e.allowed then
        table.insert(lines, { self:getFieldKindText(e), 14, e.mission ~= nil and SprayDronePlannerScreen.COLOR_CONTRACT or UI.dim })
        if e.field:getId() ~= spec.fieldId then
            table.insert(lines, { g_i18n:getText("sdt_planner_clickToSelect"), 14, UI.accentText, true })
        end
    else
        table.insert(lines, { g_i18n:getText(e.reason), 14, UI.warn })
    end
    local pad = pxX(12)
    local maxWidth = pxX(300)
    local width = 0
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextWrapWidth(0)
    for _, l in ipairs(lines) do
        setTextBold(l[4] == true)
        width = math.max(width, getTextWidth(px(l[2]), l[1]))
    end
    width = math.min(width, maxWidth) + 2 * pad + pxX(4)
    local h = px(8)
    for _, l in ipairs(lines) do
        setTextBold(l[4] == true)
        setTextWrapWidth(width - 2 * pad)
        h = h + getTextHeight(px(l[2]), l[1]) + px(2)
    end
    h = h + px(6)
    local x = math.min(self.mouseX + pxX(18), 1 - width - pxX(8))
    local y = math.max(self.mouseY - px(14), h + px(4))
    fillRect(x, y - h, width, h, UI.card)
    fillRect(x, y - h, pxX(3), h, e.allowed and UI.accent or UI.warn)
    local ty = y - px(8)
    for _, l in ipairs(lines) do
        local s = px(l[2])
        setTextBold(l[4] == true)
        setTextWrapWidth(width - 2 * pad)
        setColor(l[3])
        renderText(x + pad + pxX(4), ty - s, s, l[1])
        ty = ty - getTextHeight(s, l[1]) - px(2)
    end
end

-- Pruh nahoře uprostřed mapy: hláška (zelená / červená) a v režimu kreslení návod.
function SprayDronePlannerScreen:drawBanner()
    local items = {}
    if self.drawMode then
        table.insert(items, { title = string.format(g_i18n:getText("sdt_planner_drawing"), #self.draft),
            text = g_i18n:getText("sdt_planner_drawHint") .. " " .. g_i18n:getText("sdt_planner_controlsDraw"),
            color = SprayDronePlannerScreen.COLOR_AREA })
    end
    if self.message ~= nil then
        table.insert(items, { title = self.message.text, color = self.message.isWarning and UI.warn or UI.accent })
    end
    if #items == 0 then
        return
    end
    local lx, _, lw = self:getLeftRect()
    local cx = self:getCardBounds()
    local left, right = lx + lw + pxX(24), cx - pxX(24)
    local width = pxX(240)
    setTextWrapWidth(0)
    for _, item in ipairs(items) do
        setTextBold(true)
        width = math.max(width, getTextWidth(px(17), item.title) + pxX(40))
        if item.text ~= nil then
            setTextBold(false)
            width = math.max(width, getTextWidth(px(14), item.text) + pxX(40))
        end
    end
    width = math.min(width, pxX(620), right - left)
    local x = (left + right - width) * 0.5
    local y = 1 - px(24)
    local pad = pxX(14)
    setTextAlignment(RenderText.ALIGN_LEFT)
    for _, item in ipairs(items) do
        setTextWrapWidth(width - 2 * pad - pxX(6))
        setTextBold(true)
        local h = getTextHeight(px(17), item.title) + px(16)
        setTextBold(false)
        if item.text ~= nil then
            h = h + getTextHeight(px(14), item.text) + px(4)
        end
        fillRect(x, y - h, width, h, UI.card)
        fillRect(x, y - h, pxX(4), h, item.color)
        local ty = y - px(8)
        setTextBold(true)
        setColor(UI.text)
        renderText(x + pad + pxX(4), ty - px(17), px(17), item.title)
        ty = ty - getTextHeight(px(17), item.title) - px(4)
        if item.text ~= nil then
            setTextBold(false)
            setColor(UI.dim)
            renderText(x + pad + pxX(4), ty - px(14), px(14), item.text)
        end
        y = y - h - px(8)
    end
end
