-- Řidič: jízda tahače s vlekem bez hráče. AI job GoTo, po jeho rozjezdu se cíl přepne na přímé "manuální" řízení AI (rovně k bodu, zadaná rychlost).

local C = SprayDroneCinema
C.drives = C.drives or {}

local function stopDrive(d, message)
    if d.job ~= nil then
        pcall(function() d.vehicle:stopCurrentAIJob(AIMessageSuccessStoppedByUser.new()) end)
    end
    d.done = true
    d.result = message
end

-- Zastaví jízdu vozidla (AI job i záznam), bezpečné volat vždy.
function C.stopDriving(v)
    local d = C.drives[v.id]
    if d ~= nil then
        stopDrive(d, "zastaveno")
    end
    if v.getIsAIActive ~= nil and v:getIsAIActive() then
        pcall(function() v:stopCurrentAIJob(AIMessageSuccessStoppedByUser.new()) end)
    end
end

-- driveTo: vehicle = pickup | jd3650 | ..., x, z, kmh (výchozí 20), mode = line (rovně, výchozí) | nav (navigace AI), wait = true (ack po dojezdu, radius m)
C.handlers.driveTo = function(a)
    local v = C.findVehicle(a.vehicle or "pickup")
    if v == nil then
        return false, "vozidlo nenalezeno"
    end
    local x, z = C.num(a.x, nil), C.num(a.z, nil)
    if x == nil or z == nil then
        return false, "chybí x, z"
    end
    C.stopDriving(v)
    if v:getIsInUse(nil) then
        return false, "vozidlo je používané (hráč uvnitř?)"
    end
    local kmh = C.num(a.kmh, 20)
    local farmId = v:getOwnerFarmId()
    local px, _, pz = getWorldTranslation(v.rootNode)
    local angle = math.atan2(x - px, z - pz)
    local ok, job = pcall(function()
        local j = g_currentMission.aiJobTypeManager:createJob(AIJobType.GOTO)
        j:applyCurrentState(v, g_currentMission, farmId, true)
        j.positionAngleParameter:setPosition(x, z)
        j.positionAngleParameter:setAngle(angle)
        j:setValues()
        return j
    end)
    if not ok then
        return false, "job: " .. tostring(job)
    end
    local valid, err = job:validate(farmId)
    if not valid then
        return false, "job neplatný: " .. tostring(err)
    end
    job.driveToTask.maxSpeed = kmh
    pcall(function() v:setCruiseControlMaxSpeed(kmh, kmh) end)
    g_currentMission.aiSystem:startJob(job, farmId)
    local d = {
        vehicle = v, job = job, x = x, z = z, kmh = kmh, dirX = math.sin(angle), dirZ = math.cos(angle), mode = (a.mode or "line"):lower(),
        radius = C.num(a.radius, 3), started = g_time, id = v.id, tel = C.bool(a.tel, false),
    }
    C.drives[v.id] = d
    C.log("jízda %s start -> %.0f,%.0f %.0f km/h (%s)", tostring(v.id), x, z, kmh, d.mode)
    if C.bool(a.wait, false) then
        return "pending", function()
            if d.done then
                return d.arrived == true, d.result
            end
        end
    end
    return true, string.format("jede k %.0f,%.0f", x, z)
end

-- waitDrive: vehicle; čeká, až jízda (driveTo bez wait) skončí
C.handlers.waitDrive = function(a)
    local v = C.findVehicle(a.vehicle or "pickup")
    if v == nil then
        return false, "vozidlo nenalezeno"
    end
    return "pending", function()
        local d = C.drives[v.id]
        if d == nil or d.done then
            return true, d ~= nil and tostring(d.result) or "bez jízdy"
        end
    end
end

C.handlers.stopVehicle = function(a)
    local v = C.findVehicle(a.vehicle or "pickup")
    if v == nil then
        return false, "vozidlo nenalezeno"
    end
    local d = C.drives[v.id]
    if d ~= nil then
        stopDrive(d, "zastaveno")
    else
        pcall(function() v:stopCurrentAIJob(AIMessageSuccessStoppedByUser.new()) end)
    end
    return true, "stop"
end

C.handlers.driveSpeed = function(a)
    local v = C.findVehicle(a.vehicle or "pickup")
    local d = v ~= nil and C.drives[v.id] or nil
    if d == nil then
        return false, "nejede"
    end
    d.kmh = C.num(a.kmh, d.kmh)
    v:setCruiseControlMaxSpeed(d.kmh, d.kmh)
    v.spec_aiDrivable.maxSpeed = d.kmh
    return true, "rychlost " .. d.kmh
end

-- trace: trailer = alias, on = true/false; do logu CINEMA řádky "DRN t trailer k x y z stříká" každých ~250 ms (rozbor, kde drony při záběru byly)
C.handlers.trace = function(a)
    if C.bool(a.on, true) then
        C.trace = { trailer = a.trailer or "max", next = 0 }
    else
        C.trace = nil
    end
    return true, "trace " .. tostring(C.trace ~= nil)
end

local function traceFrame()
    local tr = C.trace
    if tr == nil or g_time < tr.next then
        return
    end
    tr.next = g_time + 250
    local trailer = C.findVehicle(tr.trailer)
    local station = trailer ~= nil and C.getStation(trailer) or nil
    if station == nil then
        return
    end
    for k = 1, station.numDrones or 1 do
        local d = station.drones ~= nil and station.drones[k] or station
        if d.node ~= nil then
            local x, y, z = getWorldTranslation(d.node)
            local spraying = d.lastSprayTime ~= nil and d.lastSprayTime + 150 > g_time
            C.log("DRN %d %s %d %.1f %.1f %.1f %s", g_time, tr.trailer, k, x, y, z, spraying and "1" or "0")
        end
    end
end

function C.driveFrame(dt)
    traceFrame()
    if C.reverseFrame ~= nil then
        C.reverseFrame(dt)
    end
    for id, d in pairs(C.drives) do
        local v = d.vehicle
        if d.done then
            C.drives[id] = nil
        elseif v.rootNode == nil or v.isDeleted then
            C.drives[id] = nil
        else
            local x, _, z = getWorldTranslation(v.rootNode)
            local dist = MathUtil.vector2Length(d.x - x, d.z - z)
            local spec = v.spec_aiDrivable
            local active = v:getIsAIActive()
            if active and d.mode == "line" and spec.isRunning and not spec.useManualDriving then
                v:setAITarget(d.job.driveToTask, d.x, C.terrainY(d.x, d.z), d.z, d.dirX, 0, d.dirZ, d.kmh, true)
                d.manual = true
                C.log("jízda %s: přepnuto na přímé řízení", tostring(id))
            end
            if d.tel then
                local _, ry = getWorldRotation(v.rootNode)
                C.log("TEL %d %.3f %.3f %.4f %.2f", g_time, x, z, ry, v:getLastSpeed())
            end
            if dist < d.radius then
                d.arrived = true
                stopDrive(d, string.format("dojel po %.1f s", (g_time - d.started) * 0.001))
            elseif not active and g_time - d.started > 3000 then
                d.done = true
                d.result = string.format("AI skončilo, zbývá %.0f m", dist)
            elseif g_time - d.started > 4000 and not d.manual and not d.moving then
                if v:getLastSpeed() > 2 then
                    d.moving = true
                end
            end
        end
    end
end

-- stav jízdy: rychlost, poloha, vzdálenost k cíli
C.handlers.driveStatus = function(a)
    local v = C.findVehicle(a.vehicle or "pickup")
    if v == nil then
        return false, "vozidlo nenalezeno"
    end
    local x, y, z = getWorldTranslation(v.rootNode)
    local d = C.drives[v.id]
    local spec = v.spec_aiDrivable
    return true, string.format("pos=%.1f,%.1f,%.1f rychlost=%.1f km/h AI=%s manual=%s %s", x, y, z, v:getLastSpeed(), tostring(v:getIsAIActive()),
        tostring(spec ~= nil and spec.useManualDriving), d ~= nil and string.format("cíl %.0f m", MathUtil.vector2Length(d.x - x, d.z - z)) or "bez jízdy")
end
