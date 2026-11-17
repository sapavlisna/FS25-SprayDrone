-- Plánovač letu dronu: celoobrazovková mapa (herní InGameMap, stejná jako v menu mapy) s vlekem, kruhem dosahu, poli
-- v okolí a naplánovanou trasou. Rozložení jako herní mapa: vlevo panel s přepínačem stránek (Pole, Mise, Let, Mapa) z herních
-- prvků GUI (seznamy, volby), vpravo karta plánu s klíčovými čísly, dole lišta tlačítek. Klik na pole ho vybere, tlačítka spouští
-- let a volají dron domů; výběr, nastavení i start jdou přes SprayDroneStation (a tím eventem na server).
-- V režimu kreslení klik přidává vrchol letové plochy vybraného pole (pole nevybírá); uzavřená plocha jde eventem na server.

SprayDronePlannerScreen = {}
SprayDronePlannerScreen.MOD_DIR = g_currentModDirectory
SprayDronePlannerScreen.GUI_NAME = "SprayDronePlannerScreen"
SprayDronePlannerScreen.FIELD_REFRESH_TIME = 1000
SprayDronePlannerScreen.LIST_REFRESH_TIME = 1000
SprayDronePlannerScreen.MESSAGE_TIME = 5000
SprayDronePlannerScreen.SUMMARY_REFRESH_TIME = 250
SprayDronePlannerScreen.CARD_WIDTH_PX = 420
SprayDronePlannerScreen.CARD_MARGIN_PX = 24
SprayDronePlannerScreen.LEFT_MARGIN_PX = 24

SprayDronePlannerScreen.COLOR_RANGE = { 0, 0.9, 1, 1 }
SprayDronePlannerScreen.COLOR_RELAY = { 1, 0.6, 0.1, 1 }
SprayDronePlannerScreen.COLOR_SELECTED = { 0.2, 1, 0.2, 1 }
SprayDronePlannerScreen.COLOR_CONTRACT = { 1, 0.78, 0.1, 1 }
SprayDronePlannerScreen.COLOR_HOVER = { 1, 1, 1, 1 }
SprayDronePlannerScreen.COLOR_AREA = { 0.72, 0.42, 1, 1 }
SprayDronePlannerScreen.COLOR_AREA_FILL = { 0.72, 0.42, 1, 0.22 }
SprayDronePlannerScreen.COLOR_DRAFT = { 1, 0.55, 1, 1 }
SprayDronePlannerScreen.COLOR_UNPLANNED = { 1, 0.15, 0.1, 0.85 }
-- pruhy pole mimo dosah kufru (mimo signál kufru a tyčí, spec.outOfReachLegs)
SprayDronePlannerScreen.COLOR_OUT_OF_REACH = { 0.6, 0.6, 0.6, 0.75 }
SprayDronePlannerScreen.COLOR_BLOCKED = { 0.55, 0.55, 0.55, 1 }
-- ovládaný vlek / kufr a jeho drony (barva kruhu dosahu), ostatní cíle přepínání
SprayDronePlannerScreen.COLOR_TARGET = { 0, 0.9, 1, 1 }
SprayDronePlannerScreen.COLOR_OTHER_TARGET = { 1, 1, 1, 0.85 }
SprayDronePlannerScreen.TARGET_ICON_PX = 20
-- vzorkovač: klik do tolika px od bodu odběru ho najde (pravý klik odebere, levý vrátí odebraný bod mřížky)
SprayDronePlannerScreen.PICK_RADIUS_PX = 12

-- barvy karty a štítků ve stylu herní mapy (lineární RGB jako profily GUI)
SprayDronePlannerScreen.UI = {
    accent = { 0.258, 0.445, 0.004, 1 },
    accentText = { 0.45, 0.75, 0.02, 1 },
    card = { 0.008, 0.009, 0.006, 0.9 },
    cardLine = { 0.06, 0.07, 0.05, 1 },
    tile = { 0.025, 0.027, 0.022, 0.95 },
    text = { 1, 1, 1, 1 },
    dim = { 0.509, 0.521, 0.462, 1 },
    warn = { 0.85, 0.06, 0.02, 1 },
    warnBg = { 0.3, 0.012, 0.004, 0.95 },
    info = { 1, 0.42, 0.02, 1 },
    infoBg = { 0.32, 0.12, 0.004, 0.95 },
    okBg = { 0.06, 0.13, 0.002, 0.95 }
}

-- při otevření se na výšku obrazovky vejde zhruba 2,8× tolik (dosah z baterie bývá přes kilometr)
SprayDronePlannerScreen.VIEW_RADIUS = 350
SprayDronePlannerScreen.FIELD_MARGIN = 400
SprayDronePlannerScreen.CLOSE_DISTANCE_PX = 14
SprayDronePlannerScreen.RELAY_ICON_RANGE = 2

-- stránky levého panelu (přepínač nahoře jako „Druhy plodin“ v herní mapě)
SprayDronePlannerScreen.PAGE_FIELDS = 1
SprayDronePlannerScreen.PAGE_MISSION = 2
SprayDronePlannerScreen.PAGE_FLIGHT = 3
SprayDronePlannerScreen.PAGE_MAP = 4
SprayDronePlannerScreen.PAGES = {
    { text = "sdt_ui_pageFields", element = "pageFields" },
    { text = "sdt_ui_pageMission", element = "pageMission" },
    { text = "sdt_ui_pageFlight", element = "pageFlight" },
    { text = "sdt_ui_pageMap", element = "pageMap" }
}
-- barva čtverce vrstvy v seznamu stránky Mapa (klíč SprayDroneScanOverlay.COLORS): to, co vrstva hlavně ukazuje
SprayDronePlannerScreen.LAYER_COLORS = { off = "unscanned", weed = "weedHigh", fert = "fert1", ripe = "ripeReady",
    stone = "stoneSome", cover = "scanned", nitrogen = "nitrogen3" }
-- nastavení na stránkách Mise a Let po skupinách (klíče SprayDroneStation.SETTINGS)
SprayDronePlannerScreen.SETTING_GROUPS = {
    [2] = { { title = "sdt_ui_groupMission", keys = { "missionMode", "applyMode", "scanCell" } },
        { title = "sdt_ui_groupSamples", keys = { "samplerAuto" } } },
    [3] = { { title = "sdt_ui_groupTransit", keys = { "transitHeight", "obstacleClearance", "sideClearance" } },
        { title = "sdt_ui_groupField", keys = { "headlands", "headlandFirst" } },
        { title = "sdt_ui_groupDrones", keys = { "activeDrones" } } }
}

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
    self.hoverEntry = nil
    self.message = nil
    self.messageTimer = 0
    self.needsInit = false
    self.mouseX, self.mouseY = 0.5, 0.5
    self.drawMode = false
    self.draft = {}
    self.selectedSetting = 1
    self.page = SprayDronePlannerScreen.PAGE_FIELDS
    self.settingElements = {}
    self.fieldSections = {}
    self.legendSections = {}
    self.listTimer = 0
    self.cardRect = nil
    self.icons = {}
    return self
end

-- Ikony mapy a karty plánu; celé cesty, ať je kontrola nepoužitých souborů (TestRunner) najde.
SprayDronePlannerScreen.ICONS = {
    mapDrone = "gui/icons/mapDrone.dds",
    mapRelay = "gui/icons/mapRelay.dds",
    mapRelayOff = "gui/icons/mapRelayOff.dds",
    mapTrailer = "gui/icons/mapTrailer.dds",
    uiBatches = "gui/icons/uiBatches.dds",
    uiTime = "gui/icons/uiTime.dds",
    uiArea = "gui/icons/uiArea.dds",
    uiLiquid = "gui/icons/uiLiquid.dds",
    uiDiesel = "gui/icons/uiDiesel.dds",
    uiBattery = "gui/icons/uiBattery.dds",
    uiTransit = "gui/icons/uiTransit.dds",
    uiWeather = "gui/icons/uiWeather.dds",
    uiScan = "gui/icons/uiScan.dds",
    uiField = "gui/icons/uiField.dds",
    uiDrone = "gui/icons/uiDrone.dds",
    uiHeader = "gui/icons/uiHeader.dds"
}

function SprayDronePlannerScreen:getIcon(name)
    local icon = self.icons[name]
    if icon == nil then
        icon = Overlay.new(SprayDronePlannerScreen.MOD_DIR .. SprayDronePlannerScreen.ICONS[name], 0, 0, 1, 1)
        self.icons[name] = icon
    end
    return icon
end

-- Ikona z ICONS na místě ve světě; px = velikost v pixelech obrazovky.
function SprayDronePlannerScreen:drawIcon(name, x, z, px, color)
    local sx, sy = self:worldToScreen(x, z)
    self:drawIconAt(name, sx - px * 0.5 * g_pixelSizeScaledX, sy - px * 0.5 * g_pixelSizeScaledY, px, color)
    return sx, sy
end

function SprayDronePlannerScreen:drawIconAt(name, x, y, px, color)
    local icon = self:getIcon(name)
    icon:setPosition(x, y)
    icon:setDimension(px * g_pixelSizeScaledX, px * g_pixelSizeScaledY)
    if color ~= nil then
        icon:setColor(color[1], color[2], color[3], color[4] or 1)
    else
        icon:setColor(1, 1, 1, 1)
    end
    icon:render()
end

function SprayDronePlannerScreen:delete()
    for _, icon in pairs(self.icons) do
        icon:delete()
    end
    self.icons = {}
    for _, element in ipairs({ self.settingPrefab, self.settingTitlePrefab }) do
        if element ~= nil then
            element:delete()
        end
    end
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
-- origin = vlek, ze kterého se plánovač otevřel (Alt+7, displej; výchozí vehicle): po přepnutí na jiný cíl (PageUp / PageDown) platí
-- dál podmínka otevření pro origin a cíle se berou z jeho domova.
function SprayDronePlannerScreen.show(vehicle, mode, origin, anywhere)
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
    -- znovuotevření jiným vlekem: zavřením by onClose vlek zahodil až po jeho nastavení
    if SprayDronePlannerScreen.INSTANCE:getIsOpen() then
        g_gui:showGui("")
    end
    SprayDronePlannerScreen.INSTANCE.vehicle = vehicle
    SprayDronePlannerScreen.INSTANCE.openMode = mode or SprayDronePlannerScreen.MODE_VEHICLE
    SprayDronePlannerScreen.INSTANCE.originVehicle = origin or vehicle
    if SprayDroneDebug and SprayDroneDebug.ENABLED then
        SprayDronePlannerScreen.INSTANCE.debugAnywhere = anywhere == true
    end
    g_gui:showGui(SprayDronePlannerScreen.GUI_NAME)
end

-- Volby (MultiTextOption) samy listují na Q / E; v plánovači ty klávesy patří tlačítkům dole (inputEvent obrazovky).
local function ignorePagingInput(element)
    local base = element.inputEvent
    element.inputEvent = function(e, action, value, eventUsed)
        if action == InputAction.MENU_PAGE_PREV or action == InputAction.MENU_PAGE_NEXT then
            return eventUsed
        end
        return base(e, action, value, eventUsed)
    end
end

function SprayDronePlannerScreen:onGuiSetupFinished()
    SprayDronePlannerScreen:superClass().onGuiSetupFinished(self)
    for _, element in ipairs({ self.settingPrefab, self.settingTitlePrefab }) do
        element:unlinkElement()
        FocusManager:removeElement(element)
    end
    local texts = {}
    for _, page in ipairs(SprayDronePlannerScreen.PAGES) do
        table.insert(texts, utf8ToUpper(g_i18n:getText(page.text)))
    end
    self.pageSelector:setTexts(texts)
    ignorePagingInput(self.pageSelector)
    for index, dot in ipairs(self.pageDotBox.elements) do
        dot.getIsSelected = function()
            return self.page == index
        end
    end
    self.fieldList:setDataSource(self)
    self.fieldList:setDelegate(self)
    self.legendList:setDataSource(self)
    self.legendList:setDelegate(self)
    self.headerIcon:setImageFilename(SprayDronePlannerScreen.MOD_DIR .. SprayDronePlannerScreen.ICONS.uiHeader)
    self.headerIcon:setImageUVs(nil, 0, 1, 0, 0, 1, 1, 1, 0)
    -- herní menu má vlevo sloupec ikon stránek, plánovač ne: panel se posune k levému okraji a dostane tmavý podklad přes
    -- celou výšku (záhlaví nad panelem pak není na mapě)
    local shift = self.leftBox.absPosition[1] - SprayDronePlannerScreen.LEFT_MARGIN_PX * g_pixelSizeScaledX
    self.menuContainer:setPosition(self.menuContainer.position[1] - shift, self.menuContainer.position[2])
    local width = self.leftBox.absPosition[1] + self.leftBox.absSize[1] + SprayDronePlannerScreen.LEFT_MARGIN_PX * g_pixelSizeScaledX
    self.leftColumn:setSize(width, 1)
    self.leftColumn:setAbsolutePosition(0, 0)
    self:layoutTargetSelector()
end

-- Výběr ovládaného vleku / kufru pod záhlavím: stránky se zkrátí shora o výšku řádku (spodek zůstane nad lištou tlačítek).
function SprayDronePlannerScreen:layoutTargetSelector()
    local selector, pages = self.targetSelector, self.pagesContainer
    ignorePagingInput(selector)
    local gap = 8 * g_pixelSizeScaledY
    local headerBottom = self.headerTitle.absPosition[2]
    local pagesTop = pages.absPosition[2] + pages.absSize[2]
    local need = selector.absSize[2] + 2 * gap - (headerBottom - pagesTop)
    if need > 0 then
        local bottom = pages.absPosition[2]
        pages:setSize(pages.size[1], pages.size[2] - need)
        pages:move(0, bottom - pages.absPosition[2])
        pagesTop = pages.absPosition[2] + pages.absSize[2]
    end
    selector:setSize(self.leftBox.absSize[1], nil)
    selector:setAbsolutePosition(self.leftBox.absPosition[1], pagesTop + gap)
    if SprayDroneDebug and SprayDroneDebug.ENABLED then
        Logging.info("SDT PLANNER: výběr dronu %.4f %.4f %.4f x %.4f, záhlaví dole %.4f, stránky nahoře %.4f (posun %.4f)", selector.absPosition[1],
            selector.absPosition[2], selector.absSize[1], selector.absSize[2], headerBottom, pagesTop, need)
    end
end

function SprayDronePlannerScreen:onOpen()
    SprayDronePlannerScreen:superClass().onOpen(self)
    self.mapBase = g_currentMission.hud:getIngameMap()
    self.ingameMap:setIngameMap(self.mapBase)
    self.ingameMap:setTerrainSize(g_currentMission.terrainSize)
    self.mapBase:restoreDefaultFilter()
    self.headerTitle:setText(utf8ToUpper(g_i18n:getText("sdt_ui_screenTitle")))
    self.startButton:setText(g_i18n:getText("sdt_button_start"))
    self.returnButton:setText(g_i18n:getText("sdt_button_returnHome"))
    self.undoButton:setText(g_i18n:getText("sdt_button_undoPoint"))
    self.settingDownButton.sdtTextKey, self.settingUpButton.sdtTextKey = nil, nil
    self.deleteAreaButton:setText(g_i18n:getText("sdt_button_deleteArea"))
    self.resetFieldButton.sdtTextKey = nil
    self.closeButton.sdtTextKey, self.drawButton.sdtTextKey = nil, nil
    self.targetSelector.sdtTexts = nil
    self.targets = nil
    self.pendingTarget = nil
    self.fieldTimer = 0
    self.listTimer = 0
    self.summary = nil
    self.hoverEntry = nil
    self.message = nil
    self.drawMode = false
    self.draft = {}
    self:resetScanUi()
    self:buildSettings()
    self:setPage(self.page)
    -- mapa se přepne na celou obrazovku až v onOpen svého prvku (volá se po tomhle), proto přiblížení
    -- a vycentrování na vlek až v prvním update
    self.needsInit = true
end

function SprayDronePlannerScreen:onClose()
    SprayDronePlannerScreen:superClass().onClose(self)
    self.vehicle = nil
    self.openMode = nil
    self.originVehicle = nil
    self.debugAnywhere = false
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

---------------------------------------------------------------------------------------------------
-- stránky a nastavení

function SprayDronePlannerScreen:onClickPageSelector(state)
    self:setPage(state)
end

function SprayDronePlannerScreen:setPage(index)
    self.page = math.clamp(index, 1, #SprayDronePlannerScreen.PAGES)
    if self.pageSelector:getState() ~= self.page then
        self.pageSelector:setState(self.page)
    end
    for i, page in ipairs(SprayDronePlannerScreen.PAGES) do
        self[page.element]:setVisible(i == self.page)
    end
    self.listTimer = 0
    -- fokus jako v herním menu: na stránce nastavení první volba (Q / E a šipky mění její hodnotu), jinak přepínač stránek
    -- (Q / E listují stránkami)
    local first = self.settingElements[self.page] ~= nil and self.settingElements[self.page][1] or nil
    if first ~= nil then
        self.selectedSetting = first.sdtSetting
        FocusManager:setFocus(first)
    else
        FocusManager:setFocus(self.pageSelector)
    end
    SprayDroneSound.noteAction(string.format("plánovač: stránka %d", self.page))
end

function SprayDronePlannerScreen:getIsSettingsPage()
    return self.settingElements[self.page] ~= nil and #self.settingElements[self.page] > 0
end

local function getSettingIndex(key)
    for i, setting in ipairs(SprayDroneStation.SETTINGS) do
        if setting.key == key then
            return i
        end
    end
    return nil
end

-- Texty volby nastavení: hodnoty min..max ve formátu řádku nastavení („Výška přeletu nejméně: 12 m“).
local function getSettingTexts(setting)
    local texts = {}
    for value = setting.min, setting.max do
        local shown = value
        if setting.values ~= nil then
            shown = g_i18n:getText(setting.values[math.clamp(value + 1, 1, #setting.values)])
        end
        table.insert(texts, string.format(g_i18n:getText(setting.text), shown))
    end
    return texts
end

-- Volby nastavení na stránkách Mise a Let (herní MultiTextOption jako u vytvoření úlohy pomocníka v mapě); staví se při každém
-- otevření, protože vlek může mít jiný počet dronů.
function SprayDronePlannerScreen:buildSettings()
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    for page, layoutName in pairs({ [2] = "missionLayout", [3] = "flightLayout" }) do
        local layout = self[layoutName]
        for i = #layout.elements, 1, -1 do
            layout.elements[i]:delete()
        end
        self.settingElements[page] = {}
        for _, group in ipairs(SprayDronePlannerScreen.SETTING_GROUPS[page]) do
            local options = {}
            for _, key in ipairs(group.keys) do
                local index = getSettingIndex(key)
                local setting = SprayDroneStation.SETTINGS[index]
                -- volby jen pro postřik (aplikace podle skenu) skenovací dron nemá, vzorkovač nemá žádné volby druhu mise, jen svoje
                -- (samplerOnly: automatické body)
                local samplerOnly = setting ~= nil and setting.samplerOnly == true
                if setting ~= nil and (setting.minDrones == nil or spec.numDrones >= setting.minDrones)
                    and not (setting.sprayOnly and spec.isScanDrone) and samplerOnly == (spec.isSamplerDrone == true and page == 2) then
                    table.insert(options, index)
                end
            end
            if #options > 0 then
                self.settingTitlePrefab:clone(layout):setText(utf8ToUpper(g_i18n:getText(group.title)))
                for _, index in ipairs(options) do
                    local element = self.settingPrefab:clone(layout)
                    element.sdtSetting = index
                    element:setTexts(getSettingTexts(SprayDroneStation.SETTINGS[index]))
                    ignorePagingInput(element)
                    FocusManager:loadElementFromCustomValues(element)
                    table.insert(self.settingElements[page], element)
                end
            end
        end
        layout:invalidateLayout()
        local elements = self.settingElements[page]
        for i = 2, #elements do
            FocusManager:linkElements(elements[i - 1], FocusManager.BOTTOM, elements[i])
            FocusManager:linkElements(elements[i], FocusManager.TOP, elements[i - 1])
        end
    end
    self:syncSettings(true)
end

-- Stav voleb podle hodnot vleku (mění je i jiný hráč nebo klávesy Q / E) a zákaz podle isSettingEnabled.
function SprayDronePlannerScreen:syncSettings(force)
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    for _, elements in pairs(self.settingElements) do
        for _, element in ipairs(elements) do
            local setting = SprayDroneStation.SETTINGS[element.sdtSetting]
            local state = math.clamp(spec[setting.key] - setting.min + 1, 1, setting.max - setting.min + 1)
            if force or element:getState() ~= state then
                element:setState(state)
            end
            local disabled = not SprayDroneStation.isSettingEnabled(self.vehicle, element.sdtSetting)
            if force or element.sdtDisabled ~= disabled then
                element.sdtDisabled = disabled
                element:setDisabled(disabled)
            end
        end
    end
end

function SprayDronePlannerScreen:onClickSettingOption(state, element)
    if self.vehicle == nil or element == nil or element.sdtSetting == nil then
        return
    end
    self.selectedSetting = element.sdtSetting
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    local setting = SprayDroneStation.SETTINGS[element.sdtSetting]
    local value = setting.min + state - 1
    if not SprayDroneStation.changeSetting(self.vehicle, element.sdtSetting, value - spec[setting.key]) then
        self:syncSettings(true)
    end
end

function SprayDronePlannerScreen:onFocusSettingOption(element)
    if element ~= nil and element.sdtSetting ~= nil then
        self.selectedSetting = element.sdtSetting
    end
end

-- Tlačítka Q / E: na stránce nastavení mění vybranou volbu, jinak listují stránkami (klávesy zpracuje dřív prvek s fokusem,
-- tlačítka slouží myši).
function SprayDronePlannerScreen:onClickSettingDown()
    if self.vehicle == nil or self.drawMode then
        return
    end
    if self:getIsSettingsPage() then
        SprayDroneStation.changeSetting(self.vehicle, self.selectedSetting, -1)
    else
        self:setPage(self.page > 1 and self.page - 1 or #SprayDronePlannerScreen.PAGES)
    end
end

function SprayDronePlannerScreen:onClickSettingUp()
    if self.vehicle == nil or self.drawMode then
        return
    end
    if self:getIsSettingsPage() then
        SprayDroneStation.changeSetting(self.vehicle, self.selectedSetting, 1)
    else
        self:setPage(self.page < #SprayDronePlannerScreen.PAGES and self.page + 1 or 1)
    end
end

---------------------------------------------------------------------------------------------------
-- seznamy (pole, legenda mapy): zdroj dat pro SmoothList

function SprayDronePlannerScreen:getListSections(list)
    return list == self.fieldList and self.fieldSections or self.legendSections
end

function SprayDronePlannerScreen:getNumberOfSections(list)
    return #self:getListSections(list)
end

function SprayDronePlannerScreen:getTitleForSectionHeader(list, section)
    local s = self:getListSections(list)[section]
    return s ~= nil and s.title or ""
end

function SprayDronePlannerScreen:getNumberOfItemsInSection(list, section)
    local s = self:getListSections(list)[section]
    return s ~= nil and #s.items or 0
end

function SprayDronePlannerScreen:populateCellForItemInSection(list, section, index, cell)
    local item = self:getListSections(list)[section].items[index]
    if list == self.fieldList then
        cell:getAttribute("title"):setText(item.title)
        cell:getAttribute("helper"):setText("")
        cell:getAttribute("text"):setText(item.text or "")
        local icon = cell:getAttribute("icon")
        icon:setImageFilename(SprayDronePlannerScreen.MOD_DIR .. SprayDronePlannerScreen.ICONS.uiField)
        icon:setImageUVs(nil, 0, 1, 0, 0, 1, 1, 1, 0)
        local c = item.color
        icon:setImageColor(nil, c[1], c[2], c[3], c[4] or 1)
    else
        cell:getAttribute("name"):setText(item.text)
        -- jako legenda herní mapy: barva je stav „vybráno“ čtverce u položky; vrstvy mapy ji ukazují jen u zvolené vrstvy
        local c = item.color
        local square = cell:getAttribute("iconBg")
        square:setImageColor(GuiOverlay.STATE_SELECTED, c[1], c[2], c[3], math.max(c[4] or 1, 0.85))
        square.getIsSelected = function()
            return true
        end
    end
end

function SprayDronePlannerScreen:onListSelectionChanged(list, section, index)
end

-- Řádky stránky Pole: pole v dosahu vleku (s důvodem, proč nejdou) a ostatní vlastní pole s mapou skenu; stav ze souhrnu skenu.
function SprayDronePlannerScreen:buildFieldSections()
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    local overview = {}
    for _, row in ipairs(self:getScanOverviewRows()) do
        overview[row.id] = row
    end
    -- nejnaléhavější nález skenu a stáří mapy (řádek seznamu je úzký)
    local function scanText(row)
        if row == nil or row.shares == nil then
            return g_i18n:getText("sdt_scanui_notScanned")
        end
        local s = row.shares
        local finding = g_i18n:getText("sdt_ui_findNone")
        for _, f in ipairs({ { s.weed, "sdt_ui_findWeed" }, { s.ripe, "sdt_ui_findRipe" },
            { s.unfertilized, "sdt_ui_findFert" } }) do
            if f[1] > 0.005 then
                finding = string.format(g_i18n:getText(f[2]), f[1] * 100)
                break
            end
        end
        return finding .. " · " .. SprayDroneScanOverlay.formatAge(row.age)
    end
    -- pole v dosahu, kam dron smí (vlastní a přijaté zakázky); cizí pole jsou jen šedě v mapě s důvodem v bublině
    local near, nearIds = {}, {}
    for _, entry in ipairs(self.fields) do
        local id = entry.field:getId()
        if entry.allowed then
            nearIds[id] = true
            local item = { field = entry.field, id = id, title = string.format(g_i18n:getText("sdt_planner_field"), entry.field:getName()) }
            if entry.mission ~= nil then
                item.color = SprayDronePlannerScreen.COLOR_CONTRACT
                item.text = self:getFieldKindText(entry)
            else
                item.color = SprayDronePlannerScreen.UI.accentText
                item.text = scanText(overview[id])
            end
            table.insert(near, item)
        end
    end
    table.sort(near, function(a, b)
        if (a.id == spec.fieldId) ~= (b.id == spec.fieldId) then
            return a.id == spec.fieldId
        end
        return a.id < b.id
    end)
    local others = {}
    for _, row in ipairs(self:getScanOverviewRows()) do
        if not nearIds[row.id] then
            table.insert(others, { field = row.field, id = row.id, title = string.format(g_i18n:getText("sdt_planner_field"), row.name),
                text = scanText(row), color = SprayDronePlannerScreen.COLOR_BLOCKED })
        end
    end
    local sections = { { title = utf8ToUpper(g_i18n:getText("sdt_ui_sectionNear")), items = near } }
    if #others > 0 then
        table.insert(sections, { title = utf8ToUpper(g_i18n:getText("sdt_ui_sectionOwn")), items = others })
    end
    return sections
end

-- Legenda stránky Mapa: vrstvy mapy skenu (klik = zvolit), barvy zvolené vrstvy a čáry trasy.
function SprayDronePlannerScreen:buildLegendSections()
    local layers = {}
    for i, layer in ipairs(SprayDroneScanOverlay.LAYERS) do
        local key = SprayDronePlannerScreen.LAYER_COLORS[layer.id] or "unscanned"
        table.insert(layers, { text = g_i18n:getText(layer.text), layer = i, color = SprayDroneScanOverlay.COLORS[key] })
    end
    local legend = {}
    local layer = self:getScanLayer()
    for _, key in ipairs(layer.legend or {}) do
        table.insert(legend, { text = g_i18n:getText("sdt_scanui_c_" .. key), color = SprayDroneScanOverlay.COLORS[key] })
    end
    if layer.legend ~= nil then
        if layer.id ~= "cover" then
            table.insert(legend, { text = g_i18n:getText("sdt_scanui_unscanned"), color = SprayDroneScanOverlay.COLORS.unscanned })
        end
        table.insert(legend, { text = string.format(g_i18n:getText("sdt_scanui_stale"), SprayDroneScanOverlay.STALE_HOURS),
            color = SprayDroneScanOverlay.getColor(layer.legend[1] .. "|stale") })
    end
    local route = {
        { text = g_i18n:getText("sdt_ui_legendSelected"), color = SprayDronePlannerScreen.COLOR_SELECTED },
        { text = g_i18n:getText("sdt_ui_legendContract"), color = SprayDronePlannerScreen.COLOR_CONTRACT },
        { text = g_i18n:getText("sdt_ui_legendBatches"), color = SprayDroneStation.getBatchColors(1)[1] },
        { text = g_i18n:getText("sdt_ui_legendUnplanned"), color = SprayDronePlannerScreen.COLOR_UNPLANNED },
        { text = g_i18n:getText("sdt_ui_legendArea"), color = SprayDronePlannerScreen.COLOR_AREA },
        { text = g_i18n:getText("sdt_ui_legendRange"), color = SprayDronePlannerScreen.COLOR_RANGE },
        { text = g_i18n:getText("sdt_ui_legendRelay"), color = SprayDronePlannerScreen.COLOR_RELAY },
        { text = g_i18n:getText("sdt_ui_legendTarget"), color = SprayDronePlannerScreen.COLOR_TARGET },
        { text = g_i18n:getText("sdt_ui_legendOtherTarget"), color = SprayDronePlannerScreen.COLOR_OTHER_TARGET }
    }
    if self.vehicle ~= nil and SprayDroneSamples.getIsSampler(self.vehicle) then
        for _, item in ipairs({ { "sdt_ui_legendSamplePending", SprayDroneSamples.COLOR_AUTO }, { "sdt_ui_legendSampleCustom", SprayDroneSamples.COLOR_CUSTOM },
            { "sdt_ui_legendSampleDone", SprayDroneSamples.COLOR_DONE }, { "sdt_ui_legendSampleTall", SprayDroneSamples.COLOR_SKIP },
            { "sdt_ui_legendSampleCover", SprayDroneSamples.COLOR_COVER } }) do
            table.insert(route, { text = g_i18n:getText(item[1]), color = item[2] })
        end
    end
    local sections = { { title = utf8ToUpper(g_i18n:getText("sdt_ui_sectionLayer")), items = layers } }
    if #legend > 0 then
        table.insert(sections, { title = utf8ToUpper(g_i18n:getText(layer.text)), items = legend })
    end
    table.insert(sections, { title = utf8ToUpper(g_i18n:getText("sdt_ui_sectionRoute")), items = route })
    return sections
end

local function getSignature(sections)
    local parts = {}
    for _, s in ipairs(sections) do
        table.insert(parts, s.title)
        for _, item in ipairs(s.items) do
            table.insert(parts, (item.title or item.text) .. "|" .. (item.text or "") .. "|" .. tostring(item.color))
        end
    end
    return table.concat(parts, "\n")
end

-- Seznamy se znovu naplní jen při změně obsahu (reloadData by jinak rušil posun a zvýraznění).
function SprayDronePlannerScreen:refreshLists(force)
    if self.page == SprayDronePlannerScreen.PAGE_FIELDS then
        local sections = self:buildFieldSections()
        local signature = getSignature(sections)
        if force or signature ~= self.fieldSignature then
            self.fieldSections, self.fieldSignature = sections, signature
            self.fieldList:reloadData()
        end
        self:selectCurrentFieldItem()
    elseif self.page == SprayDronePlannerScreen.PAGE_MAP then
        local sections = self:buildLegendSections()
        local signature = getSignature(sections) .. "|" .. tostring(self.scanLayerIndex)
        if force or signature ~= self.legendSignature then
            self.legendSections, self.legendSignature = sections, signature
            self.legendList:reloadData()
        end
        self.legendList:setSelectedItem(1, self.scanLayerIndex, true)
    end
end

-- Vybrané pole vleku zvýrazněné v seznamu; bez vybraného pole (nebo pole mimo seznam) seznam zvýraznění nemá.
function SprayDronePlannerScreen:selectCurrentFieldItem()
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    for s, section in ipairs(self.fieldSections) do
        for i, item in ipairs(section.items) do
            if item.id == spec.fieldId then
                local cs, ci = self.fieldList:getSelectedPath()
                if cs ~= s or ci ~= i or not self.fieldList.selectedWithoutFocus then
                    self.fieldList.selectedWithoutFocus = true
                    self.fieldList:setSelectedItem(s, i, true)
                end
                return
            end
        end
    end
    if self.fieldList.selectedWithoutFocus then
        self.fieldList.selectedWithoutFocus = false
        self.fieldList:applyElementSelection()
    end
end

function SprayDronePlannerScreen:onClickFieldList(list, section, index)
    local item = self.fieldSections[section] ~= nil and self.fieldSections[section].items[index] or nil
    if item == nil then
        return
    end
    self:centerOnField(item.field)
    SprayDroneSound.noteAction(string.format("plánovač: seznam polí, klik na pole %d", item.id))
    if self.drawMode then
        return
    end
    self:selectField(item.field)
end

function SprayDronePlannerScreen:onClickLegendList(list, section, index)
    local item = self.legendSections[section] ~= nil and self.legendSections[section].items[index] or nil
    if item ~= nil and item.layer ~= nil then
        self:setScanLayer(item.layer)
        self.listTimer = 0
    else
        self.legendList:setSelectedItem(1, self.scanLayerIndex, true)
    end
end

function SprayDronePlannerScreen:centerOnField(field)
    local x, z = field:getCenterOfFieldWorldPosition()
    self.ingameMap:setCenterToWorldPosition(x, z)
    self:shiftMapToFreeArea()
end

function SprayDronePlannerScreen:selectField(field)
    local warning = SprayDroneStation.selectField(self.vehicle, field)
    if warning ~= nil then
        self:showMessage(string.format("%s: %s", string.format(g_i18n:getText("sdt_planner_field"), field:getName()),
            g_i18n:getText(warning)), true)
    else
        self:showMessage(string.format(g_i18n:getText("sdt_planner_selected"), field:getName()), false)
        self:playSample(GuiSoundPlayer.SOUND_SAMPLES.CLICK)
    end
    self.listTimer = 0
end

---------------------------------------------------------------------------------------------------
-- rozložení: volná plocha mapy mezi levým panelem a kartou plánu

function SprayDronePlannerScreen:getLeftRect()
    local box = self.leftBox
    return box.absPosition[1], box.absPosition[2], box.absSize[1], box.absSize[2]
end

function SprayDronePlannerScreen:getCardBounds()
    local w = math.min(SprayDronePlannerScreen.CARD_WIDTH_PX * g_pixelSizeScaledX, 0.32)
    local right = 1 - SprayDronePlannerScreen.CARD_MARGIN_PX * g_pixelSizeScaledX
    local top = 1 - SprayDronePlannerScreen.CARD_MARGIN_PX * g_pixelSizeScaledY
    local bottom = self.buttonBox.absPosition[2] + self.buttonBox.absSize[2] + 16 * g_pixelSizeScaledY
    return right - w, bottom, w, top - bottom
end

function SprayDronePlannerScreen:shiftMapToFreeArea()
    local lx, _, lw = self:getLeftRect()
    local cx = self:getCardBounds()
    local center = (lx + lw + cx) * 0.5
    self.ingameMap:moveCenter(center - self.ingameMap.originalMapCenterX, 0)
end

function SprayDronePlannerScreen:getIsOverUi(posX, posY)
    local x, y, w, h = self:getLeftRect()
    if posX >= x and posX <= x + w and posY >= y and posY <= y + h then
        return true
    end
    local r = self.cardRect
    if r ~= nil and posX >= r[1] and posX <= r[1] + r[3] and posY >= r[2] and posY <= r[2] + r[4] then
        return true
    end
    return posY <= self.buttonBox.absPosition[2] + self.buttonBox.absSize[2]
end

function SprayDronePlannerScreen:initMapView()
    self.needsInit = false
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(self.vehicle)
    local layout = self.mapBase.fullScreenLayout
    local sizeRatio = layout.sizeRatio or 1
    local zoom = g_currentMission.terrainSize / (2.8 * math.min(spec.range, SprayDronePlannerScreen.VIEW_RADIUS) * sizeRatio)
    self.ingameMap:zoom(0, zoom)
    -- s vybraným polem střed mezi vlekem a polem, ať je vidět obojí
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field ~= nil then
        local fx, fz = field:getCenterOfFieldWorldPosition()
        hx, hz = (hx + fx) * 0.5, (hz + fz) * 0.5
    end
    self.ingameMap:setCenterToWorldPosition(hx, hz)
    self:shiftMapToFreeArea()
    self:updateDeadzones()
    self.ingameMap:registerActionEvents()
end

function SprayDronePlannerScreen:updateDeadzones()
    self.ingameMap:clearCursorDeadzones()
    local x, y, w, h = self:getLeftRect()
    self.ingameMap:addCursorDeadzone(x, y, w, h)
    -- celý tmavý sloupec vlevo, i se záhlavím a výběrem dronu nad panelem (jinak by klik na jeho šipky spolkla mapa)
    local column = self.leftColumn
    self.ingameMap:addCursorDeadzone(column.absPosition[1], column.absPosition[2], column.absSize[1], column.absSize[2])
    local r = self.cardRect
    if r ~= nil then
        self.ingameMap:addCursorDeadzone(r[1], r[2], r[3], r[4])
    end
    self.ingameMap:addCursorDeadzone(0, 0, 1, self.buttonBox.absPosition[2] + self.buttonBox.absSize[2])
    self.deadzoneCard = r ~= nil and { r[1], r[2], r[3], r[4] } or nil
end

-- Q / E (MENU_PAGE_PREV / NEXT) obslouží plánovač sám dřív než ScreenElement, který by s prvkem pageSelector listoval po svém:
-- na stránce nastavení mění vybranou volbu, jinak listují stránkami (viz onClickSettingDown / Up).
function SprayDronePlannerScreen:inputEvent(action, value, eventUsed)
    -- PageUp / PageDown přepnou ovládaný vlek / kufr (dřív než seznamy, které by jimi listovaly)
    if not eventUsed and (action == InputAction.MENU_LIST_PAGE_PREV or action == InputAction.MENU_LIST_PAGE_NEXT) then
        self:requestTarget(action == InputAction.MENU_LIST_PAGE_PREV and -1 or 1)
        return true
    end
    if not eventUsed and (action == InputAction.MENU_PAGE_PREV or action == InputAction.MENU_PAGE_NEXT) then
        if action == InputAction.MENU_PAGE_PREV then
            self:onClickSettingDown()
        else
            self:onClickSettingUp()
        end
        return true
    end
    return SprayDronePlannerScreen:superClass().inputEvent(self, action, value, eventUsed)
end

-- Přepnutí cíle o step (nebo přímo na vehicle, klik na ikonu v mapě); plánovač se znovu otevře pro nový cíl až v update (ne uprostřed
-- zpracování vstupu). Platí ve všech režimech otevření, cíle dává SprayDroneLink.getPlannerTargets.
function SprayDronePlannerScreen:requestTarget(step, vehicle)
    if self.drawMode then
        return
    end
    self.targets = SprayDroneLink.getPlannerTargets(self.openMode, self.originVehicle)
    if #self.targets < 2 then
        self:showMessage(g_i18n:getText("sdt_tablet_onlyTarget"), false)
        return
    end
    self.pendingTarget = { step = step, vehicle = vehicle }
end

-- Šipky výběru dronu: přímo na zvolený cíl (seznam se mezitím mohl změnit, proto podle vozidla z poslední obnovy).
function SprayDronePlannerScreen:onClickTargetSelector(state)
    local entry = self.targets ~= nil and self.targets[state] or nil
    if entry ~= nil and entry.vehicle ~= self.vehicle then
        self:requestTarget(nil, entry.vehicle)
    end
end

-- Znovu otevře plánovač pro cíl z requestTarget: z tabletu přes openTablet (pamatuje si cíl), jinak se stejným režimem a originem.
function SprayDronePlannerScreen:switchTarget(request)
    if self.openMode == SprayDronePlannerScreen.MODE_TABLET then
        SprayDroneLink.openTablet(request.step or 1, request.vehicle)
        return
    end
    local targets = SprayDroneLink.getPlannerTargets(self.openMode, self.originVehicle)
    local index
    if request.vehicle ~= nil then
        index = SprayDroneLink.pickTarget(targets, request.vehicle)
    else
        index = SprayDroneLink.cycleTarget(targets, self.vehicle, request.step or 1)
    end
    local entry = index ~= nil and targets[index] or nil
    if entry == nil or entry.vehicle == self.vehicle then
        return
    end
    SprayDroneSound.noteAction(string.format("plánovač (%s): cíl %d / %d %s (id %s)", tostring(self.openMode), index, #targets,
        tostring(entry.vehicle.configFileName), tostring(entry.vehicle.id)))
    SprayDronePlannerScreen.show(entry.vehicle, self.openMode, self.originVehicle)
end

-- Výběr cíle pod záhlavím: texty = vleky / kufry ve spojení s pořadím, stav = ovládaný (ve všech režimech, s jediným cílem šedý).
function SprayDronePlannerScreen:updateTargetSelector()
    self.targets = SprayDroneLink.getPlannerTargets(self.openMode, self.originVehicle)
    local texts, state = {}, 1
    for i, entry in ipairs(self.targets) do
        -- krátce (řádek je úzký): pořadí, název, vzdálenost; stav dronu ukazuje karta vpravo
        local name = entry.vehicle.getName ~= nil and entry.vehicle:getName() or ""
        texts[i] = string.format(g_i18n:getText("sdt_button_tabletTarget"), i, #self.targets, name, entry.distance or 0)
        if entry.vehicle == self.vehicle then
            state = i
        end
    end
    local selector = self.targetSelector
    local joined = table.concat(texts, "\n")
    if joined ~= selector.sdtTexts then
        selector.sdtTexts = joined
        selector:setTexts(texts)
    end
    if selector:getState() ~= state then
        selector:setState(state)
    end
    selector:setVisible(#texts > 0)
    selector:setDisabled(self.drawMode or #texts < 2)
end

function SprayDronePlannerScreen:mouseEvent(posX, posY, isDown, isUp, button, eventUsed)
    self.mouseX, self.mouseY = posX, posY
    -- pravé tlačítko mapa sama nepoužívá: u vzorkovače odebere bod odběru
    if not eventUsed and isUp and button == Input.MOUSE_BUTTON_RIGHT and self:onRightClickMap(posX, posY) then
        return true
    end
    return SprayDronePlannerScreen:superClass().mouseEvent(self, posX, posY, isDown, isUp, button, eventUsed)
end

function SprayDronePlannerScreen:onRightClickMap(posX, posY)
    if self.vehicle == nil or self.drawMode or self.needsInit or not SprayDroneSamples.getIsSampler(self.vehicle)
        or self:getIsOverUi(posX, posY) then
        return false
    end
    local lx, ly = self.ingameMap:getLocalPosition(posX, posY)
    local wx, wz = self.ingameMap:localToWorldPos(lx, ly)
    self:pickSamplePoint(wx, wz, false)
    return true
end

-- Kolik metrů ve světě je px pixelů obrazovky v aktuálním přiblížení mapy.
function SprayDronePlannerScreen:getWorldRadius(px)
    local lx1, ly1 = self.ingameMap:getLocalPosition(self.mouseX, self.mouseY)
    local x1, z1 = self.ingameMap:localToWorldPos(lx1, ly1)
    local lx2, ly2 = self.ingameMap:getLocalPosition(self.mouseX + px * g_pixelSizeX, self.mouseY)
    local x2, z2 = self.ingameMap:localToWorldPos(lx2, ly2)
    return MathUtil.vector2Length(x2 - x1, z2 - z1)
end

-- Vzorkovač: přidá (add) nebo odebere bod odběru u (x, z) a ukáže výsledek v hlášce.
function SprayDronePlannerScreen:pickSamplePoint(x, z, add)
    local warning, info = SprayDroneSamples.requestPick(self.vehicle, x, z, add, self:getWorldRadius(SprayDronePlannerScreen.PICK_RADIUS_PX))
    SprayDroneSound.noteAction(string.format("plánovač: %s klik na (%.0f, %.0f), bod odběru %s", add and "levý" or "pravý", x, z,
        tostring(warning or info or "ok")))
    if warning ~= nil then
        self:showMessage(g_i18n:getText(warning), true)
        return
    end
    self:showMessage(g_i18n:getText(info or (add and "sdt_sampler_pickAdded" or "sdt_sampler_pickRemoved")), info ~= nil)
    self:playSample(GuiSoundPlayer.SOUND_SAMPLES.CLICK)
end

local function isGone(vehicle)
    return vehicle == nil or vehicle.isDeleted or vehicle.isDeleting
end

-- Platí ještě podmínka, se kterou se plánovač otevřel? Ve vleku (Alt+7): hráč sedí v originu a ten je rozložený; displej: hráč
-- nesmí od displeje originu odejít dál než SCREEN_CLOSE_DISTANCE; tablet: bez podmínky na origin (hlídá se spojení s cílem).
function SprayDronePlannerScreen:getIsOriginUsable()
    local origin = self.originVehicle or self.vehicle
    if isGone(origin) then
        return false
    end
    if SprayDroneDebug and SprayDroneDebug.ENABLED then
        if self.debugAnywhere then
            return true
        end
    end
    if self.openMode == SprayDronePlannerScreen.MODE_TABLET then
        return true
    elseif self.openMode == SprayDronePlannerScreen.MODE_SCREEN then
        return SprayDroneLink.isPlayerAtScreen(origin, SprayDroneLink.SCREEN_CLOSE_DISTANCE)
    end
    return origin:getIsUnfolded() and SprayDroneStation.getIsEntered(origin)
end

-- Ovládaný cíl: tablet - hráč ve spojení s ním (dosah rádia nebo relé), jinak NO CONNECTION (tablet i displej fungují i u složeného
-- vleku, start letu vlek odmítne); ve vleku a u displeje platí podmínka originu a cíl musí být ve spojení s originem.
function SprayDronePlannerScreen:getIsVehicleUsable()
    local vehicle = self.vehicle
    if isGone(vehicle) then
        return false
    end
    if self.openMode == SprayDronePlannerScreen.MODE_TABLET then
        return SprayDroneLink.isPlayerConnected(vehicle)
    end
    if not self:getIsOriginUsable() then
        return false
    end
    return SprayDroneLink.isStationTargetConnected(self.originVehicle or vehicle, vehicle)
end

function SprayDronePlannerScreen:update(dt)
    SprayDronePlannerScreen:superClass().update(self, dt)
    if not self:getIsOpen() then
        return
    end
    if not self:getIsVehicleUsable() then
        local origin = self.originVehicle
        local back = self.openMode ~= SprayDronePlannerScreen.MODE_TABLET and origin ~= self.vehicle and self:getIsOriginUsable()
        if back or self.openMode == SprayDronePlannerScreen.MODE_TABLET then
            g_currentMission:showBlinkingWarning(g_i18n:getText("sdt_tablet_noConnection"), 2500)
        end
        if back then
            -- cíl ztratil spojení s vlekem, ze kterého se plánovač otevřel: zpět na ten vlek
            SprayDronePlannerScreen.show(origin, self.openMode, origin)
        else
            g_gui:showGui("")
        end
        return
    end
    if self.pendingTarget ~= nil then
        local request = self.pendingTarget
        self.pendingTarget = nil
        self:switchTarget(request)
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
    self.listTimer = self.listTimer - dt
    if self.listTimer <= 0 then
        self.listTimer = SprayDronePlannerScreen.LIST_REFRESH_TIME
        self:refreshLists(false)
        self:updateTargetSelector()
    end
    self:syncSettings(false)
    local focused = FocusManager:getFocusedElement()
    if focused ~= nil and focused.sdtSetting ~= nil then
        self.selectedSetting = focused.sdtSetting
    end
    self:updateHover()

    if self.message ~= nil then
        self.messageTimer = self.messageTimer - dt
        if self.messageTimer <= 0 then
            self.message = nil
        end
    end
    local card = self.cardRect
    local zone = self.deadzoneCard
    if card ~= nil and (zone == nil or math.abs(zone[2] - card[2]) > 0.001 or math.abs(zone[4] - card[4]) > 0.001) then
        self:updateDeadzones()
    end

    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    self.startButton:setDisabled(self.drawMode or not SprayDroneStation.getCanStart(self.vehicle) or not SprayDroneStation.getAnyPlanned(self.vehicle))
    self.returnButton:setDisabled(not SprayDroneStation.getCanReturnHome(self.vehicle))

    local area = SprayDroneStation.getFlightArea(self.vehicle)
    local drawKey = area ~= nil and "sdt_button_editArea" or "sdt_button_drawArea"
    if self.drawMode then
        drawKey = "sdt_button_closeArea"
    end
    local settingsPage = self:getIsSettingsPage()
    local changed = self:updateButton(self.closeButton, true, false, self.drawMode and "sdt_button_cancelDraw" or "sdt_button_close")
    changed = self:updateButton(self.drawButton, true, self.drawMode and #self.draft < 3, drawKey) or changed
    changed = self:updateButton(self.undoButton, self.drawMode, #self.draft == 0) or changed
    -- vzorkovač nemá paměť pokrytí: místo „Pole od začátku“ odesílá vzorky z bedničky do laboratoře
    if spec.isSamplerDrone then
        changed = self:updateButton(self.resetFieldButton, not self.drawMode, (spec.sampleBox or 0) == 0, "sdt_button_sendSamples") or changed
    else
        changed = self:updateButton(self.resetFieldButton, not self.drawMode, spec.fieldId == 0 or SprayDroneStation.getAnyMissionActive(self.vehicle),
            "sdt_button_resetField") or changed
    end
    changed = self:updateButton(self.deleteAreaButton, area ~= nil or (self.drawMode and #self.draft > 0), false) or changed
    if settingsPage then
        local setting = SprayDroneStation.SETTINGS[self.selectedSetting]
        local value = spec[setting.key]
        local enabled = SprayDroneStation.isSettingEnabled(self.vehicle, self.selectedSetting)
        changed = self:updateButton(self.settingDownButton, not self.drawMode, not enabled or value <= setting.min, "sdt_button_settingDown") or changed
        changed = self:updateButton(self.settingUpButton, not self.drawMode, not enabled or value >= setting.max, "sdt_button_settingUp") or changed
    else
        changed = self:updateButton(self.settingDownButton, not self.drawMode, false, "sdt_ui_pagePrev") or changed
        changed = self:updateButton(self.settingUpButton, not self.drawMode, false, "sdt_ui_pageNext") or changed
    end
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

function SprayDronePlannerScreen:updateHover()
    local previous = self.hoverEntry
    self.hoverEntry = nil
    if self:getIsOverUi(self.mouseX, self.mouseY) or self.drawMode then
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
    if spec.isSamplerDrone then
        local warning = SprayDroneSamples.requestSend(self.vehicle)
        self:showMessage(g_i18n:getText(warning or "sdt_sampler_sentShort"), warning ~= nil)
        return
    end
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
    if self.vehicle == nil or self:getIsOverUi(self.mouseX, self.mouseY) then
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
    local target = self:getTargetIconAt(self.mouseX, self.mouseY)
    if target ~= nil then
        self:requestTarget(nil, target)
        return
    end
    local entry = self:getEntryAt(worldX, worldZ)
    -- vzorkovač s vybraným polem: klik do něj (nebo mimo pole) přidá bod odběru, klik do jiného pole ho vybere jako u ostatních dronů
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    if spec.isSamplerDrone and spec.fieldId ~= 0 and (entry == nil or entry.field:getId() == spec.fieldId) then
        self:pickSamplePoint(worldX, worldZ, true)
        return
    end
    if entry == nil then
        self:showMessage(g_i18n:getText("sdt_warning_noField"), true)
        return
    end
    self:selectField(entry.field)
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

-- Polohy prvků v pixelech okna (DEBUG, příkaz plannerLayout) pro skutečné kliky myší: [x, y] středu, y shora.
function SprayDronePlannerScreen:logLayout()
    local function center(name, element)
        if element == nil then
            return
        end
        local x = (element.absPosition[1] + element.absSize[1] * 0.5) * g_screenWidth
        local y = (1 - element.absPosition[2] - element.absSize[2] * 0.5) * g_screenHeight
        Logging.info("SDT UI %s: střed %d %d, velikost %d x %d, viditelný %s", name, x, y, element.absSize[1] * g_screenWidth,
            element.absSize[2] * g_screenHeight, tostring(element:getIsVisible()))
    end
    Logging.info("SDT UI myš: %d %d (okno %d x %d)", self.mouseX * g_screenWidth, (1 - self.mouseY) * g_screenHeight, g_screenWidth, g_screenHeight)
    center("pageSelector", self.pageSelector)
    center("leftBox", self.leftBox)
    center("fieldList", self.fieldList)
    center("legendList", self.legendList)
    for page, elements in pairs(self.settingElements) do
        for i, element in ipairs(elements) do
            center(string.format("setting %d.%d (%s)", page, i, SprayDroneStation.SETTINGS[element.sdtSetting].key), element)
        end
    end
    for _, list in ipairs({ self.fieldList, self.legendList }) do
        for s, section in ipairs(list.sections or {}) do
            for i, cell in ipairs(section.cells or {}) do
                if cell ~= nil and cell.absPosition ~= nil then
                    center(string.format("%s %d.%d", list == self.fieldList and "field" or "legend", s, i), cell)
                end
            end
        end
    end
    local r = self.cardRect
    if r ~= nil then
        Logging.info("SDT UI karta: x %d..%d, y %d..%d", r[1] * g_screenWidth, (r[1] + r[3]) * g_screenWidth,
            (1 - r[2] - r[4]) * g_screenHeight, (1 - r[2]) * g_screenHeight)
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

-- Hranice pole bez "klíčové dírky": vnější hranice a každý ostrov zvlášť (surový polygon by kreslil i můstek k ostrovu).
function SprayDronePlannerScreen:drawFieldShape(field, thicknessPx, color)
    local shape = SprayDroneRoute.getFieldShape(field)
    self:drawWorldPolygon(shape.outer, thicknessPx, color)
    for _, island in ipairs(shape.islands) do
        self:drawWorldPolygon(island, thicknessPx, color)
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
    if last ~= nil and not self:getIsOverUi(self.mouseX, self.mouseY) then
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

-- Obrysy polí v dosahu: vlastní pole zeleně, zakázky zlatě, pole, kam dron nesmí, šedě (tence); vybrané a pod kurzorem silněji.
function SprayDronePlannerScreen:drawFieldOutlines(selectedId)
    for _, entry in ipairs(self.fields) do
        local id = entry.field:getId()
        if id ~= selectedId and entry ~= self.hoverEntry then
            local color = SprayDronePlannerScreen.COLOR_BLOCKED
            if entry.allowed then
                color = entry.mission ~= nil and SprayDronePlannerScreen.COLOR_CONTRACT or SprayDronePlannerScreen.UI.accentText
            end
            self:drawFieldShape(entry.field, entry.allowed and 2 or 1, { color[1], color[2], color[3], 0.7 })
        end
    end
end

function SprayDronePlannerScreen:onDrawPostIngameMap(element, ingameMap)
    if self.vehicle == nil or self.needsInit then
        return
    end
    local vehicle = self.vehicle
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    local hx, hz = SprayDroneStation.getHomePosition(vehicle)

    self:drawScanOverlay()
    self:drawFieldOutlines(spec.fieldId)
    if self.hoverEntry ~= nil and self.hoverEntry.field:getId() ~= spec.fieldId then
        self:drawFieldShape(self.hoverEntry.field, 4, SprayDronePlannerScreen.COLOR_HOVER)
    end
    local field = SprayDroneRoute.getFieldById(spec.fieldId)
    if field ~= nil then
        self:drawFieldShape(field, 5, SprayDronePlannerScreen.COLOR_SELECTED)
    end
    local area = SprayDroneStation.getFlightArea(vehicle)
    if area ~= nil then
        self:fillWorldPolygon(area, SprayDronePlannerScreen.COLOR_AREA_FILL)
        self:drawWorldPolygon(area, self.drawMode and 1 or 3, SprayDronePlannerScreen.COLOR_AREA)
    end

    -- dosah signálu: obrys sjednocení rádia vleku (spec.maxRange, SprayDroneLink.getRadio) a oblastí aktivních tyčí s ním spojených
    -- (kruh všesměrové, výseč směrové; SprayDroneLink.getSignalCircles); tenký kruh je dosah z baterie (spec.range, s relé prodloužený),
    -- když se od rádia liší – za něj dávka nedoletí. Pruhy pole mimo dosah kufru šedě.
    for _, leg in ipairs(spec.outOfReachLegs or {}) do
        self:drawWorldLine(leg.x1, leg.z1, leg.x2, leg.z2, 2, SprayDronePlannerScreen.COLOR_OUT_OF_REACH)
    end
    local segments = 96
    for _, line in ipairs(SprayDroneLink.getCoverageLines(SprayDroneLink.getSignalCircles(vehicle), segments)) do
        self:drawWorldLine(line.x1, line.z1, line.x2, line.z2, 3,
            line.circle == 1 and SprayDronePlannerScreen.COLOR_RANGE or SprayDronePlannerScreen.COLOR_RELAY)
    end
    -- směrové tyče v okolí (i složené a vypnuté): čárka ve směru čela panelu, ať je vidět, kam tyč míří, ještě než se zapne
    local relayNear = spec.maxRange * SprayDronePlannerScreen.RELAY_ICON_RANGE
    for _, relay in ipairs(SprayDroneLink.getRelays()) do
        local s = relay.sectors[1]
        if s ~= nil and MathUtil.vector2Length(relay.x - hx, relay.z - hz) <= relayNear then
            local length = s.r * 0.15
            self:drawWorldLine(relay.x, relay.z, relay.x + math.cos(s.dir) * length, relay.z + math.sin(s.dir) * length, 3,
                relay.active and SprayDronePlannerScreen.COLOR_RELAY or SprayDronePlannerScreen.COLOR_OUT_OF_REACH)
        end
    end
    if math.abs(spec.range - (spec.radioMax or spec.maxRange)) > 1 then
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
    SprayDroneSamples.drawPlannerPoints(self, vehicle)
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
    -- ostatní cíle přepínání (vleky a kufry ve spojení) bíle s pořadím z tlačítka „Dron:“, ovládaný cíl a jeho drony barvou dosahu
    for i, entry in ipairs(self.targets or {}) do
        local other = entry.vehicle
        if other ~= vehicle and not isGone(other) then
            local ox, oz = SprayDroneStation.getHomePosition(other)
            local sx, sy = self:drawIcon("mapTrailer", ox, oz, SprayDronePlannerScreen.TARGET_ICON_PX, SprayDronePlannerScreen.COLOR_OTHER_TARGET)
            self:drawTargetNumber(sx, sy, i, SprayDronePlannerScreen.COLOR_OTHER_TARGET)
            self:drawDroneIcons(other, 18, SprayDronePlannerScreen.COLOR_OTHER_TARGET)
        end
    end
    local sx, sy = self:drawIcon("mapTrailer", hx, hz, 26, SprayDronePlannerScreen.COLOR_TARGET)
    for i, entry in ipairs(self.targets or {}) do
        if entry.vehicle == vehicle and #self.targets > 1 then
            self:drawTargetNumber(sx, sy, i, SprayDronePlannerScreen.COLOR_TARGET)
        end
    end
    self:drawDroneIcons(vehicle, 24, SprayDronePlannerScreen.COLOR_TARGET)
end

-- Ikony dronů vozidla ve vzduchu.
function SprayDronePlannerScreen:drawDroneIcons(vehicle, px, color)
    local spec = vehicle[SprayDroneStation.SPEC_NAME]
    for k = 1, spec.numDrones do
        local d = spec.drones[k]
        if d ~= nil and not d.isLinked and d.node ~= nil and entityExists(d.node) then
            local dx, _, dz = getWorldTranslation(d.node)
            self:drawIcon("mapDrone", dx, dz, px, color)
        end
    end
end

-- Pořadí cíle (jako „n“ v tlačítku „Dron: … (n/m)“) nad ikonou vleku.
function SprayDronePlannerScreen:drawTargetNumber(sx, sy, index, color)
    setTextAlignment(RenderText.ALIGN_CENTER)
    setTextBold(true)
    setTextColor(color[1], color[2], color[3], color[4] or 1)
    renderText(sx, sy + 14 * g_pixelSizeScaledY, 16 * g_pixelSizeScaledY, tostring(index))
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextBold(false)
    setTextColor(1, 1, 1, 1)
end

-- Jiný cíl přepínání, na jehož ikonu ukazuje kurzor (klik na ni plánovač přepne), nebo nil.
function SprayDronePlannerScreen:getTargetIconAt(posX, posY)
    local limit = SprayDronePlannerScreen.TARGET_ICON_PX * 0.5 + 2
    for _, entry in ipairs(self.targets or {}) do
        if entry.vehicle ~= self.vehicle and not isGone(entry.vehicle) then
            local sx, sy = self:worldToScreen(SprayDroneStation.getHomePosition(entry.vehicle))
            if math.abs(sx - posX) / g_pixelSizeScaledX <= limit and math.abs(sy - posY) / g_pixelSizeScaledY <= limit then
                return entry.vehicle
            end
        end
    end
    return nil
end

-- Karta plánu, bublina pole pod kurzorem a hlášky se kreslí nad herními prvky obrazovky (po nich), mapa je pod nimi.
function SprayDronePlannerScreen:draw()
    SprayDronePlannerScreen:superClass().draw(self)
    if self.vehicle == nil or self.needsInit or not self:getIsOpen() then
        return
    end
    self:drawCard()
    self:drawHoverTip()
    self:drawBanner()
    self:drawPickHint()
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextBold(false)
    setTextColor(1, 1, 1, 1)
    setTextWrapWidth(0)
end

-- Nápověda ke klikání bodů odběru vpravo nad dolní lištou na tmavém podkladu (v liště by se kryla s tlačítky); jen vzorkovač s vybraným
-- polem, mimo kreslení plochy.
function SprayDronePlannerScreen:drawPickHint()
    local spec = self.vehicle[SprayDroneStation.SPEC_NAME]
    if not spec.isSamplerDrone or spec.fieldId == 0 or self.drawMode then
        return
    end
    local box = self.buttonBox
    local size = 15 * g_pixelSizeScaledY
    local text = g_i18n:getText("sdt_sampler_pickHint")
    local padX, padY = 8 * g_pixelSizeScaledX, 5 * g_pixelSizeScaledY
    local x = 1 - SprayDronePlannerScreen.CARD_MARGIN_PX * g_pixelSizeScaledX
    local y = box.absPosition[2] + box.absSize[2] + 8 * g_pixelSizeScaledY + padY
    setTextBold(false)
    local w = getTextWidth(size, text)
    drawFilledRect(x - w - padX, y - padY, w + 2 * padX, size + 2 * padY, 0, 0, 0, 0.75)
    setTextAlignment(RenderText.ALIGN_RIGHT)
    setTextColor(1, 1, 1, 1)
    renderText(x, y + size * 0.15, size, text)
    setTextAlignment(RenderText.ALIGN_LEFT)
    setTextColor(1, 1, 1, 1)
end

source(SprayDronePlannerScreen.MOD_DIR .. "scripts/gui/SprayDronePlannerCard.lua")
source(SprayDronePlannerScreen.MOD_DIR .. "scripts/gui/SprayDroneScanOverlay.lua")
