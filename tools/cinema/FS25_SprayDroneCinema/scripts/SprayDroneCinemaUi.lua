-- Řízení herního GUI (obchod, konfigurace vozidla, plánovač) z Lua pro natáčení obrazovek bez klávesnice a myši.
-- Příkaz `ui` s parametrem op (viz handler níže); časované operace (plynulý posun seznamu, otáčení kamery) jsou "pending".

local C = SprayDroneCinema
C.ui = C.ui or {}
local U = C.ui

local function planner()
    local r = FS25_SprayDroneTrailer
    return r ~= nil and r.SprayDronePlannerScreen or nil
end

function U.state()
    local m = g_shopMenu
    local page = m ~= nil and m.currentPage ~= nil and m.currentPage.name or "?"
    return string.format("gui=%s shopPage=%s", tostring(g_gui.currentGuiName), tostring(page))
end

-- Pending s časovou osou: steps = { {t=sekundy od startu, fn=function}, ... }, hotovo po poslední položce + tail
local function timeline(steps, tail)
    local t0 = g_time
    local nextIndex = 1
    local lastT = steps[#steps] ~= nil and steps[#steps].t or 0
    return "pending", function()
        local elapsed = (g_time - t0) * 0.001
        while nextIndex <= #steps and elapsed >= steps[nextIndex].t do
            local step = steps[nextIndex]
            nextIndex = nextIndex + 1
            local ok, err = pcall(step.fn, elapsed)
            if not ok then
                return false, "chyba kroku " .. tostring(nextIndex - 1) .. ": " .. tostring(err)
            end
        end
        if nextIndex > #steps and elapsed >= lastT + (tail or 0) then
            return true, string.format("hotovo %.1f s, %s", elapsed, U.state())
        end
    end
end
U.timeline = timeline

local ops = {}

ops.state = function()
    return true, U.state()
end

ops.close = function()
    if g_gui.currentGuiName ~= "" and g_gui.currentGuiName ~= nil then
        g_gui:showGui("")
    end
    return true, U.state()
end

ops.shopOpen = function(a)
    if C.camStop ~= nil then
        pcall(C.camStop)
    end
    g_gui:showGui("ShopMenu")
    local m = g_shopMenu
    local page = m.pageShopVehicles
    if page ~= nil and page.categoryList ~= nil then
        pcall(function() page.categoryList:setSelectedItem(1, 1, true) end)
        pcall(function() page.categoryList:scrollToStart() end)
    end
    return true, U.state()
end

-- plynulý posun seznamu kategorií k sekci BZUK (offset po snímcích, scrollTo(.., true) nastaví okamžitě)
ops.shopScroll = function(a)
    local list = g_shopMenu.pageShopVehicles.categoryList
    local section = C.num(a.section, 20)
    list:setSelectedItem(section, 1, true)
    local target = list.targetViewOffset
    list:scrollTo(0, true)
    local duration = C.num(a.duration, 2.0)
    local t0 = g_time
    return "pending", function()
        local u = math.min((g_time - t0) * 0.001 / duration, 1)
        list:scrollTo(target * C.ease(a.ease or "smooth", u), true)
        if u >= 1 then
            return true, "seznam na sekci " .. section
        end
    end
end

ops.shopCat = function(a)
    local f = g_shopMenu.pageShopVehicles
    local want = (a.id or "SPRAYDRONETRAILERS"):upper()
    for _, list in pairs(f.categories or {}) do
        for _, cat in ipairs(list) do
            if tostring(cat.id):upper() == want then
                g_shopMenu:onClickItemCategory(cat.id)
                return true, U.state()
            end
        end
    end
    return false, "kategorie nenalezena: " .. want
end

ops.shopBack = function()
    g_shopMenu:popDetail()
    return true, U.state()
end

ops.shopItem = function(a)
    local p = g_shopMenu.pageShopItemDetails
    p.itemsList:setSelectedItem(1, C.num(a.n, 1), true)
    local di = p:getSelectedDisplayItem()
    return true, tostring(di ~= nil and di.storeItem ~= nil and di.storeItem.xmlFilename or "?"):match("([^/]+)$") .. " " .. U.state()
end

ops.shopItems = function()
    local p = g_shopMenu.pageShopItemDetails
    local out = {}
    for i, di in ipairs(p.displayItems or {}) do
        table.insert(out, string.format("%d=%s", i, tostring(di.storeItem and di.storeItem.xmlFilename or "?"):match("([^/]+)%.xml$") or "?"))
    end
    return true, table.concat(out, " ")
end

ops.shopConfig = function()
    local p = g_shopMenu.pageShopItemDetails
    local di = p:getSelectedDisplayItem()
    if di == nil then
        return false, "není vybraná položka"
    end
    p.notifyActivatedDisplayItemCallback(di)
    return true, U.state()
end

ops.cfgList = function()
    local s = g_shopConfigScreen
    local out = {}
    for name, el in pairs(s.configurationToListElement or {}) do
        local opt = el.elements[1]
        table.insert(out, string.format("%s=%s/%s", name, tostring(opt.state), tostring(opt.texts and #opt.texts or "-")))
    end
    table.sort(out)
    return true, table.concat(out, " ")
end

ops.cfg = function(a)
    local s = g_shopConfigScreen
    local el = s.configurationToListElement[a.name]
    if el == nil then
        return false, "není volba " .. tostring(a.name)
    end
    el.elements[1]:setState(C.num(a.state, 1), true)
    return true, string.format("%s -> %s, cena %s", a.name, tostring(a.state), tostring(s.totalPrice))
end

ops.cfgScroll = function(a)
    local sl = g_shopConfigScreen.configSlider
    local from = sl.currentValue
    local to = a.value == "max" and sl.maxValue or C.clamp(C.num(a.value, 1), sl.minValue, sl.maxValue)
    local duration = C.num(a.duration, 1.0)
    local t0 = g_time
    return "pending", function()
        local u = math.min((g_time - t0) * 0.001 / duration, 1)
        sl:setValue(from + (to - from) * C.ease("smooth", u))
        if u >= 1 then
            return true, "posun hotov"
        end
    end
end

-- pomalé otáčení náhledu vozidla (rotY o `turn` radiánů) a přiblížení; běží po snímcích
ops.cfgCam = function(a)
    local s = g_shopConfigScreen
    local duration = C.num(a.duration, 4)
    local y0, y1 = s.rotY, s.rotY + C.num(a.turn, 1.0)
    local x0 = s.rotX
    local x1 = a.rotX ~= nil and C.num(a.rotX, x0) or x0
    local z0 = s.zoomTarget
    local z1 = a.zoom ~= nil and C.num(a.zoom, z0) or z0
    local t0 = g_time
    return "pending", function()
        local elapsed = (g_time - t0) * 0.001
        local u = C.ease(a.ease or "smooth", elapsed / duration)
        s.rotY = y0 + (y1 - y0) * u
        s.rotX = x0 + (x1 - x0) * u
        s.zoomTarget = z0 + (z1 - z0) * u
        if elapsed >= duration then
            return true, string.format("rotY=%.2f zoom=%.2f", s.rotY, s.zoomTarget)
        end
    end
end

-- výběr barvy: otevře dialog, po `pick` s zaostří barvu číslo idx a po `ok` s potvrdí
ops.cfgColor = function(a)
    local s = g_shopConfigScreen
    local ce = s.colorElements[C.num(a.which, 1)]
    if ce == nil then
        return false, "není barevné pole"
    end
    local idx = C.num(a.idx, 2)
    local function dialog()
        return g_gui.guis.ColorPickerDialog.target
    end
    return timeline({
        { t = 0, fn = function() ce.onClickCallback(ce.target, ce) end },
        { t = C.num(a.pick, 1.0), fn = function() FocusManager:setFocus(dialog().colorElements[idx]) end },
        { t = C.num(a.ok, 2.2), fn = function() dialog():onClickOk() end },
    }, 0.3)
end

ops.cfgColorOpen = function(a)
    local s = g_shopConfigScreen
    local ce = s.colorElements[C.num(a.which, 1)]
    ce.onClickCallback(ce.target, ce)
    return true, U.state()
end

ops.cfgColorFocus = function(a)
    FocusManager:setFocus(g_gui.guis.ColorPickerDialog.target.colorElements[C.num(a.idx, 2)])
    return true, "ok"
end

ops.cfgColorOk = function()
    g_gui.guis.ColorPickerDialog.target:onClickOk()
    return true, U.state()
end

ops.cfgBack = function()
    local s = g_shopConfigScreen
    s:onClickBack()
    return true, U.state()
end

---------------------------------------------------------------------------------------------------
-- plánovač letu (tablet): otevření, stránky, pole, nastavení, pohled mapy, relé

local function station()
    return FS25_SprayDroneTrailer.SprayDroneStation
end

local function screen()
    local P = planner()
    return P ~= nil and P.INSTANCE or nil
end

-- Střed mapy ve světových souřadnicích (mapCenterX je v souřadnicích zoomu a posunu): po otevření jako v initMapView
-- (uprostřed mezi vlekem a polem), pak poslední střed, který nastavil tento modul.
local function viewCenter(s)
    if U.vx ~= nil then
        return U.vx, U.vz
    end
    local S = station()
    local hx, hz = S.getHomePosition(s.vehicle)
    local field = FS25_SprayDroneTrailer.SprayDroneRoute.getFieldById(s.vehicle[S.SPEC_NAME].fieldId)
    if field ~= nil then
        local fx, fz = field:getCenterOfFieldWorldPosition()
        return (hx + fx) * 0.5, (hz + fz) * 0.5
    end
    return hx, hz
end

local function setView(s, x, z, zoom)
    local m = s.ingameMap
    if zoom ~= nil then
        m:zoom(0, zoom)
    end
    m:setCenterToWorldPosition(x, z)
    s:shiftMapToFreeArea()
    U.vx, U.vz = x, z
end

ops.plannerOpen = function(a)
    local P = planner()
    local v = C.findVehicle(a.trailer or "middle")
    if P == nil or v == nil then
        return false, "plánovač nebo vlek nedostupný"
    end
    U.vx, U.vz = nil, nil
    P.show(v, P["MODE_" .. (a.mode or "tablet"):upper()])
    return true, U.state()
end

-- bublina pole pod kurzorem: vypnutí přepsáním updateHover na instanci (kurzor stojí a mapa se pod ním posouvá, bublina by skákala)
ops.plannerHover = function(a)
    local s = screen()
    if C.bool(a.off, true) then
        s.updateHover = function(self)
            self.hoverEntry = nil
        end
    else
        s.updateHover = nil
    end
    return true, "hover " .. (C.bool(a.off, true) and "vypnut" or "zapnut")
end

ops.plannerPage = function(a)
    screen():setPage(C.num(a.n, 1))
    return true, "stránka " .. tostring(a.n)
end

ops.plannerField = function(a)
    local s = screen()
    local id = C.num(a.id, 4)
    if s.page ~= 1 then
        s:setPage(1)
    end
    s:refreshLists(true)
    for si, section in ipairs(s.fieldSections) do
        for i, item in ipairs(section.items) do
            if item.id == id then
                s.fieldList:setSelectedItem(si, i, true)
                if a.pan == nil then
                    s:onClickFieldList(s.fieldList, si, i)
                    U.vx, U.vz = item.field:getCenterOfFieldWorldPosition()
                    return true, "pole " .. id
                end
                -- výběr bez skoku mapy; střed se plynule posune na pole (a případně změní zoom)
                s:selectField(item.field)
                local m = s.ingameMap
                local x0, z0 = viewCenter(s)
                local x1, z1 = item.field:getCenterOfFieldWorldPosition()
                x1, z1 = x1 + C.num(a.dx, 0), z1 + C.num(a.dz, 0)
                local zoom0 = m.mapZoom
                local zoom1 = C.num(a.zoom, zoom0)
                local duration = C.num(a.pan, 1)
                local t0 = g_time
                return "pending", function()
                    local u = math.min((g_time - t0) * 0.001 / duration, 1)
                    local e = C.ease("smooth", u)
                    setView(s, x0 + (x1 - x0) * e, z0 + (z1 - z0) * e, zoom0 + (zoom1 - zoom0) * e)
                    if u >= 1 then
                        return true, "pole " .. id .. " zoom " .. string.format("%.2f", m.mapZoom)
                    end
                end
            end
        end
    end
    return false, "pole " .. id .. " není v seznamu"
end

ops.plannerSetting = function(a)
    local s = screen()
    local S = station()
    for index, setting in ipairs(S.SETTINGS) do
        if setting.key == a.key then
            local ok = S.changeSetting(s.vehicle, index, C.num(a.delta, 1))
            return true, string.format("%s delta %s -> %s", a.key, tostring(a.delta), tostring(ok))
        end
    end
    return false, "neznámé nastavení " .. tostring(a.key)
end

ops.plannerInfo = function()
    local s = screen()
    local sp = s.vehicle[station().SPEC_NAME]
    local R = FS25_SprayDroneTrailer.SprayDroneLink
    local relays = {}
    for _, r in ipairs(R.getRelays()) do
        table.insert(relays, string.format("(%.0f,%.0f r=%.0f %s)", r.x, r.z, r.radius, tostring(r.active)))
    end
    local ids = {}
    for _, section in ipairs(s.fieldSections or {}) do
        for _, item in ipairs(section.items) do
            table.insert(ids, tostring(item.id))
        end
    end
    return true, string.format("field=%s range=%s maxRange=%s zoom=%.2f page=%s fields=%s relays=%s", tostring(sp.fieldId), tostring(sp.range),
        tostring(sp.maxRange), s.ingameMap.mapZoom, tostring(s.page), table.concat(ids, ","), table.concat(relays, " "))
end

-- plynulý pohled mapy: střed (světové x, z) a zoom, kosinové zpomalení
ops.plannerView = function(a)
    local s = screen()
    local m = s.ingameMap
    local x0, z0 = viewCenter(s)
    local x1, z1 = C.num(a.x, x0), C.num(a.z, z0)
    local zoom0 = m.mapZoom
    local zoom1 = C.num(a.zoom, zoom0)
    local duration = C.num(a.duration, 3)
    local t0 = g_time
    return "pending", function()
        local u = math.min((g_time - t0) * 0.001 / duration, 1)
        local e = C.ease(a.ease or "smooth", u)
        setView(s, x0 + (x1 - x0) * e, z0 + (z1 - z0) * e, zoom0 + (zoom1 - zoom0) * e)
        if u >= 1 then
            return true, string.format("zoom %.2f", m.mapZoom)
        end
    end
end

-- tyč relé: spawn bez přenosu hráče (x, z), rozložit a zapnout
ops.relaySpawn = function(a)
    local mod = g_modManager:getModByName("FS25_SprayDroneTrailer")
    local x, z = C.num(a.x, 0), C.num(a.z, 0)
    local data = VehicleLoadingData.new()
    data:setFilename(mod.modDir .. "objects/relay/relayPole.xml")
    data:setPosition(x, C.terrainY(x, z) + 0.3, z)
    data:setRotation(0, 0, 0)
    data:setPropertyState(VehiclePropertyState.OWNED)
    data:setOwnerFarmId(g_currentMission:getFarmId())
    data:load(function(_, vehicles, state)
        local v = vehicles ~= nil and vehicles[1] or nil
        C.log("relaySpawn: %s id=%s", tostring(state), v ~= nil and tostring(v.id) or "-")
        if v ~= nil then
            local R = FS25_SprayDroneTrailer.SprayDroneRelay
            R.setState(v, true, true, true, true)
        end
    end)
    return true, "spawn odeslán"
end

ops.relayList = function()
    local out = {}
    for v in C.eachVehicle() do
        if C.cfg(v):find("relaypole", 1, true) then
            local x, y, z = getWorldTranslation(v.rootNode)
            table.insert(out, string.format("id=%s (%.0f,%.0f,%.0f)", tostring(v.id), x, y, z))
        end
    end
    return true, table.concat(out, "; ")
end

ops.relayRemove = function()
    local n = 0
    for v in C.eachVehicle() do
        if C.cfg(v):find("relaypole", 1, true) then
            n = n + 1
            v:delete()
        end
    end
    return true, "smazáno " .. n
end

C.handlers.ui = function(a, cmd)
    local fn = ops[a.op or ""]
    if fn == nil then
        return false, "neznámá operace ui: " .. tostring(a.op)
    end
    local first, second = fn(a, cmd)
    if first == "pending" and C.bool(a.bg, false) then
        table.insert(C.pending, { id = "bg", action = "ui:" .. a.op, poll = second, timeout = g_time + C.num(a.timeout, 60) * 1000 })
        return true, "na pozadí"
    end
    return first, second
end
