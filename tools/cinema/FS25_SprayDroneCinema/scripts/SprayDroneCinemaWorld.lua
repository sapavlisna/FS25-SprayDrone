-- Svět: denní doba, počasí, roční období, pole (plodina, růstový stav), mlha.

local C = SprayDroneCinema

local function env()
    return g_currentMission.environment
end

function C.applyTime(hour)
    local e = env()
    local ms = math.floor((hour % 24) * 3600 * 1000)
    local ok = pcall(e.setEnvironmentTime, e, e.currentMonotonicDay, e.currentDay, ms, e.daysPerPeriod, false)
    if not ok then
        e.dayTime = ms
    end
    e:update(1, true)
    if e.lighting ~= nil then
        e.lighting:update(9999, true)
    end
    return ms
end

function C.applyWeather(name, variation)
    local e = env()
    e.weather:consoleCommandWeatherSet(name, variation or 1)
    e:update(1, true)
    if e.lighting ~= nil then
        e.lighting:update(9999, true)
    end
    C.lastWeather = { name = name, variation = variation or 1 }
end

-- setTime: hour (18.2 = 18:12), lock=true drží čas pevný (znovu ho přepisuje každý snímek), timeScale (volitelně)
C.handlers.setTime = function(a)
    local hour = C.num(a.hour, nil)
    if hour == nil then
        return false, "chybí hour"
    end
    local ms = C.applyTime(hour)
    if a.timeScale ~= nil then
        g_currentMission:setTimeScale(C.num(a.timeScale, 1))
    end
    C.timeLock = C.bool(a.lock, false) and ms or nil
    local e = env()
    return true, string.format("čas %.2f h, dayTime=%s, currentHour=%s", hour, tostring(e.dayTime), tostring(e.currentHour))
end

C.handlers.setWeather = function(a)
    local name = (a.weather or "SUN"):upper()
    C.applyWeather(name, C.num(a.variation, 1))
    return true, "počasí " .. name .. " -> " .. tostring(env().weather:getCurrentWeatherType())
end

C.handlers.setSeason = function(a)
    local e = env()
    local period = C.num(a.period, nil)
    e:setFixedPeriod(period)
    e:update(1, true)
    if C.lastWeather ~= nil then
        C.applyWeather(C.lastWeather.name, C.lastWeather.variation)
    end
    return true, "období " .. tostring(period)
end

function C.worldFrame(dt)
    if C.timeLock ~= nil then
        env().dayTime = C.timeLock
    end
end

-- setField: field = herní id (nebo seznam "3,4,5"), crop = jméno plodiny (WHEAT, MAIZE, CANOLA, SUNFLOWER...; NONE = holé), growth = růstový stav,
-- fert, lime, plow, weed, stone (úrovně; neuvedené = 0). Logika podle FieldUpdateTask jako v DashControl.
local function setOneField(a, fieldId)
    local field = g_fieldManager:getFieldById(fieldId)
    if field == nil or field.farmland == nil or field.getDensityMapPolygon == nil then
        return false, "pole " .. tostring(fieldId) .. " nenalezeno"
    end
    local fruitIndex
    if a.crop ~= nil and a.crop ~= "" then
        local name = a.crop:upper()
        fruitIndex = (name == "NONE" or name == "UNKNOWN") and FruitType.UNKNOWN or g_fruitTypeManager:getFruitTypeIndexByName(name)
        if fruitIndex == nil then
            return false, "neznámá plodina " .. a.crop
        end
    end
    local growth = C.num(a.growth, nil)
    local groundType = FieldGroundType.CULTIVATED
    if fruitIndex ~= nil and fruitIndex ~= FruitType.UNKNOWN then
        local ft = g_fruitTypeManager:getFruitTypeByIndex(fruitIndex)
        if tostring(a.growth) == "cut" and (ft.cutState or 0) > 0 then
            growth = ft.cutState
        end
        growth = math.clamp(growth or 1, 1, math.max(ft.numFoliageStates or 1, ft.cutState or 1))
        if ft.getGrowthStateGroundType then
            groundType = ft:getGrowthStateGroundType(growth) or groundType
        end
    end
    if a.ground ~= nil and FieldGroundType[a.ground:upper()] ~= nil then
        groundType = FieldGroundType[a.ground:upper()]
    end
    local fert, lime, plow = C.num(a.fert, 0), C.num(a.lime, 0), C.num(a.plow, 0)
    local task = FieldUpdateTask.new()
    task:setField(field)
    task:setArea(field:getDensityMapPolygon())
    if fruitIndex ~= nil then
        task:setFruit(fruitIndex, growth or 1)
    end
    task:setGroundType(groundType)
    task:setGroundAngle(0)
    task:setWeedState(C.num(a.weed, 0))
    task:setStoneLevel(C.num(a.stone, 0))
    if fert > 0 and SprayType ~= nil then
        task:setSprayType(SprayType.FERTILIZER)
    end
    task:setSprayLevel(fert)
    task:setLimeLevel(lime)
    task:setPlowLevel(plow)
    task:setRollerLevel(C.num(a.roller, 0))
    task:setStubbleShredLevel(C.num(a.stubble, 0))
    task:resetDisplacement()
    task:clearTireTracks()
    task:enqueue(true)
    return true, string.format("pole %d: %s st. %s", fieldId, tostring(a.crop or "-"), tostring(growth or "-"))
end

C.handlers.setField = function(a)
    local out = {}
    for token in tostring(a.field or ""):gmatch("[^,%s]+") do
        local ok, msg = setOneField(a, tonumber(token))
        table.insert(out, msg)
        if not ok then
            return false, msg
        end
    end
    if #out == 0 then
        return false, "chybí field"
    end
    return true, table.concat(out, "; ")
end

-- setFog: pokus o mlhu (weather.fogUpdater); a.height, a.start, a.density zapisuje do polí, která tabulka má (viz keys path=...fogUpdater)
C.handlers.setFog = function(a)
    local fog = env().weather.fogUpdater
    if fog == nil then
        return false, "weather.fogUpdater neexistuje"
    end
    local set = {}
    if C.bool(a.reset, false) then
        -- původní hodnoty mapy MapUS (ráno 3:04-8:31, slabá mlha)
        a = { groundFogMinValleyDepth = 6.54, groundFogGroundLevelDensity = 0.018973, heightFogGroundLevelDensity = 0.055032,
            groundFogStartDayTimeMinutes = 184, groundFogEndDayTimeMinutes = 511, groundFogExtraHeight = 14.39 }
    end
    for _, target in ipairs({ fog.currentFog, fog.targetFog, fog.lastFog }) do
        for name, value in pairs(a) do
            if type(target[name]) == "number" then
                target[name] = tonumber(value)
                set[name] = value
            end
        end
    end
    fog.isDirty = true
    fog.alpha, fog.visibilityAlpha = 1, 1
    env():update(1, true)
    if env().lighting ~= nil then
        env().lighting:update(9999, true)
    end
    local out = {}
    for name, value in pairs(set) do
        table.insert(out, name .. "=" .. value)
    end
    return true, "mlha: " .. table.concat(out, ", ")
end

C.handlers.pauseWorld = function(a)
    g_currentMission:setManualPause(C.bool(a.paused, true))
    return true, "pauza " .. tostring(a.paused)
end
