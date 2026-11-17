-- Příkazy pro natáčení videa v2 (tools/cinema/v2/review_technik.md kap. 3, přehled a příklady v tools/cinema/v2/prikazy_v2.md):
-- isolate, flightArea, worldLines, coverLines, droneHover, toolboxSet, mark, seq, screenWake, spawnCanister.
-- Kamera `at="vlek#i3dMapping"` je v SprayDroneCinema.lua (resolveNode), canisterPour from=box a bagLift target=mill ve Scene.lua.

local C = SprayDroneCinema

local function release()
    return FS25_SprayDroneTrailer
end

local function parseXZ(text)
    local x, z = tostring(text or ""):match("^%s*(-?[%d%.]+)%s*,%s*(-?[%d%.]+)%s*$")
    return tonumber(x), tonumber(z)
end

local function trailerKind(v)
    for _, kind in ipairs({ "mini", "middle", "max" }) do
        if C.cfg(v):find(C.ALIASES[kind]:lower(), 1, true) ~= nil then
            return kind
        end
    end
end

local function eachDrone(trailer)
    local station = C.getStation(trailer)
    local k = 0
    return function()
        k = k + 1
        if k > (station.numDrones or 1) then
            return nil
        end
        return k, station.drones ~= nil and station.drones[k] or station
    end
end

local function allParked(trailer)
    for _, d in eachDrone(trailer) do
        if d.state ~= 0 then
            return false
        end
    end
    return true
end

---------------------------------------------------------------------------------------------------
-- N1 isolate

C.ISOLATE_PROPS = { "waterPump", "waterTrailer550", "limeHopper", "sdtLimeMill", "limeBigBag", "bigBag_lime", "relayPole" }

-- isolate: keep = vlek, který zůstane (alias), park = "x,z" první místo na parkovišti (výchozí 260,-665), spacing (14) rozestup souprav v ose X, yaw (0);
-- ostatní soupravy SDT: dronům returnHome, počká na zaparkování, složí a přenese placeSetem (hráč jde s nimi, na konci zpět ke keep); props = false nemaže rekvizity
-- (čerpadlo, cisterna, násypka, mlýnek, big bagy, tyče relé, kanystry a pytle); vehicles = true (radius 150) přesune i odpojená cizí vozidla kolem keep, undo = true je vrátí.
C.handlers.isolate = function(a)
    if C.bool(a.undo, false) then
        local n = 0
        for _, o in ipairs(C.isolated or {}) do
            if not o.v.isDeleted then
                C.teleport(o.v, o.x, o.y, o.z, o.yaw)
                n = n + 1
            end
        end
        C.isolated = nil
        return true, "vráceno vozidel: " .. n
    end
    local keep = C.findVehicle(a.keep or "middle")
    if keep == nil or C.getStation(keep) == nil then
        return false, "vlek keep nenalezen"
    end
    local px, pz = parseXZ(a.park)
    px, pz = px or 260, pz or -665
    local spacing, yaw = C.num(a.spacing, 14), C.num(a.yaw, 0)
    local others = {}
    for v in C.eachVehicle() do
        if v ~= keep and not v.isDeleted and C.getStation(v) ~= nil then
            local kind = trailerKind(v)
            if kind ~= nil then
                table.insert(others, { v = v, kind = kind })
            end
        end
    end
    for _, o in ipairs(others) do
        if not allParked(o.v) then
            o.v:sprayDroneCommand(3, 0, nil, 0)
        end
    end

    local phase, queue, current, failed = 1, {}, nil, {}
    local placed = 0
    local function isProp(v)
        for _, pattern in ipairs(C.ISOLATE_PROPS) do
            if C.cfg(v):find(pattern:lower(), 1, true) ~= nil then
                return true
            end
        end
        return release().SprayDroneToolbox.getCanisterKind(v) ~= nil
    end
    local function finish()
        local deleted = 0
        local deleteProps = C.bool(a.props, true)
        if deleteProps then
            for _, pattern in ipairs(C.ISOLATE_PROPS) do
                local _, msg = C.handlers.removeVehicle({ vehicle = pattern, all = "true" })
                deleted = deleted + (tonumber(tostring(msg):match("%d+")) or 0)
            end
            local R = release()
            local canisters = {}
            for v in C.eachVehicle() do
                if not v.isDeleted and R.SprayDroneToolbox.getCanisterKind(v) ~= nil then
                    table.insert(canisters, v)
                end
            end
            for _, v in ipairs(canisters) do
                v:delete()
            end
            deleted = deleted + #canisters
        end
        local moved = 0
        if C.bool(a.vehicles, false) then
            local kx, _, kz = getWorldTranslation(keep.rootNode)
            local radius = C.num(a.radius, 150)
            C.isolated = {}
            for v in C.eachVehicle() do
                local free = not v.isDeleted and v ~= keep and C.getStation(v) == nil and not C.isSetMember(v) and not (deleteProps and isProp(v))
                    and (v.getAttacherVehicle == nil or v:getAttacherVehicle() == nil)
                    and (v.getAttachedImplements == nil or #v:getAttachedImplements() == 0)
                if free then
                    local x, y, z = getWorldTranslation(v.rootNode)
                    if math.sqrt((x - kx) ^ 2 + (z - kz) ^ 2) < radius then
                        local dx, _, dz = localDirectionToWorld(v.rootNode, 0, 0, 1)
                        table.insert(C.isolated, { v = v, x = x, y = y, z = z, yaw = math.atan2(dx, dz) })
                        local tx, tz = px + moved * 8, pz + 25
                        C.teleport(v, tx, C.terrainY(tx, tz) + 0.3, tz, 0)
                        moved = moved + 1
                    end
                end
            end
        end
        local kx, _, kz = getWorldTranslation(keep.rootNode)
        C.playerNear(kx, kz)
        local summary = string.format("souprav parkuje %d, selhalo %d, rekvizit smazáno %d, vozidel přesunuto %d", placed, #failed, deleted, moved)
        if #failed > 0 then
            return false, summary .. " (" .. table.concat(failed, "; ") .. ")"
        end
        return true, summary
    end

    return "pending", function()
        if phase == 1 then
            for _, o in ipairs(others) do
                if not allParked(o.v) then
                    return nil
                end
            end
            for _, o in ipairs(others) do
                if o.v:getFoldAnimTime() < 0.98 then
                    o.v:setFoldState(1, false)
                end
            end
            phase = 2
            return nil
        elseif phase == 2 then
            for _, o in ipairs(others) do
                if o.v:getFoldAnimTime() < 0.98 then
                    return nil
                end
            end
            for i, o in ipairs(others) do
                table.insert(queue, { trailer = o.kind, x = px + (i - 1) * spacing, z = pz, yaw = yaw })
            end
            phase = 3
            return nil
        end
        while true do
            if current == nil then
                local item = table.remove(queue, 1)
                if item == nil then
                    return finish()
                end
                local r1, r2 = C.handlers.placeSet(item)
                if r1 == "pending" then
                    current = { poll = r2, kind = item.trailer }
                else
                    table.insert(failed, item.trailer .. ": " .. tostring(r2))
                end
            else
                local done, msg = current.poll()
                if done == nil then
                    return nil
                end
                if done then
                    placed = placed + 1
                else
                    table.insert(failed, current.kind .. ": " .. tostring(msg))
                end
                current = nil
            end
        end
    end
end

---------------------------------------------------------------------------------------------------
-- N2 flightArea, worldLines

-- flightArea: trailer, field (výchozí vybrané pole; all u clear = všechna), mode = strip | points | clear;
-- strip: pás šířky width (40) od bodu a.back (8) m za vlekem (vlek je pak uvnitř plochy) směrem ke středu pole a do hloubky a.inset (15) m za jeho okraj;
-- points: pts = "x,z;x,z;..." (3 až MAX_AREA_POINTS bodů)
C.handlers.flightArea = function(a)
    local trailer = C.findVehicle(a.trailer or "max")
    local station = trailer ~= nil and C.getStation(trailer) or nil
    local R = release()
    if station == nil or R == nil then
        return false, "vlek nenalezen"
    end
    local mode = (a.mode or "strip"):lower()
    if mode == "clear" and tostring(a.field) == "all" then
        local ids = {}
        for id in pairs(station.flightAreas) do
            table.insert(ids, id)
        end
        for _, id in ipairs(ids) do
            trailer:setSprayDroneFlightArea(id, nil)
        end
        return true, "smazány plochy polí: " .. #ids
    end
    local fieldId = C.num(a.field, station.fieldId)
    if fieldId == nil or fieldId == 0 then
        return false, "není pole (field= nebo vybrat pole)"
    end
    if mode == "clear" then
        trailer:setSprayDroneFlightArea(fieldId, nil)
        return true, "plocha pole " .. fieldId .. " smazána"
    end
    local points = {}
    if mode == "points" then
        for pair in tostring(a.pts or ""):gmatch("[^;]+") do
            local x, z = parseXZ(pair)
            if x == nil then
                return false, "chybný bod: " .. pair
            end
            table.insert(points, { x = x, z = z })
        end
        if #points < 3 then
            return false, "méně než 3 body"
        end
    else
        local field = R.SprayDroneRoute.getFieldById(fieldId)
        if field == nil then
            return false, "pole " .. fieldId .. " nenalezeno"
        end
        local poly = R.SprayDroneRoute.getPolygon(field)
        local hx, hz = R.SprayDroneStation.getHomePosition(trailer)
        local cx, cz = 0, 0
        for _, p in ipairs(poly) do
            cx, cz = cx + p.x / #poly, cz + p.z / #poly
        end
        local len = math.sqrt((cx - hx) ^ 2 + (cz - hz) ^ 2)
        if len < 1 then
            return false, "vlek stojí uprostřed pole"
        end
        local dx, dz = (cx - hx) / len, (cz - hz) / len
        local entry
        for t = 0, len + 300 do
            if R.SprayDroneRoute.isPointInPolygon(poly, hx + dx * t, hz + dz * t) then
                entry = t
                break
            end
        end
        if entry == nil then
            return false, "směr ke středu pole nevede přes pole (použít mode=points)"
        end
        local last = entry + C.num(a.inset, 15)
        while last > entry + 1 and not R.SprayDroneRoute.isPointInPolygon(poly, hx + dx * last, hz + dz * last) do
            last = last - 1
        end
        local back = -C.num(a.back, 8)
        local half = C.num(a.width, 40) * 0.5
        local nx, nz = -dz, dx
        local sx, sz = hx + dx * back, hz + dz * back
        local ex, ez = hx + dx * last, hz + dz * last
        points = {
            { x = sx + nx * half, z = sz + nz * half }, { x = ex + nx * half, z = ez + nz * half },
            { x = ex - nx * half, z = ez - nz * half }, { x = sx - nx * half, z = sz - nz * half },
        }
    end
    trailer:setSprayDroneFlightArea(fieldId, points)
    local corridor = "kontrola jen pro vybrané pole"
    if station.fieldId == fieldId then
        corridor = R.SprayDroneStation.getCorridor(trailer) ~= nil and "koridor OK" or "KORIDOR NEVZNIKL"
    end
    return station.flightAreas[fieldId] ~= nil, string.format("plocha pole %d: %d bodů, %s", fieldId, #points, corridor)
end

-- worldLines: on = true/false; čáry ve světě (obrys pole, letová plocha, řádky, přelety), jinak vypnuté; hra je kreslí jen hráči u vleku
C.handlers.worldLines = function(a)
    local R = release()
    if R == nil then
        return false, "release mód nedostupný"
    end
    R.SprayDroneStation.showWorldLines = C.bool(a.on, true)
    return true, "čáry ve světě " .. tostring(R.SprayDroneStation.showWorldLines)
end

---------------------------------------------------------------------------------------------------
-- N3 coverLines

local function parseLines(text)
    local set = {}
    for chunk in tostring(text):gmatch("[^,%s]+") do
        local lo, hi = chunk:match("^(%d+)%-(%d+)$")
        if lo ~= nil then
            for k = tonumber(lo), tonumber(hi) do
                set[k] = true
            end
        elseif tonumber(chunk) ~= nil then
            set[tonumber(chunk)] = true
        end
    end
    return set
end

-- coverLines: trailer, field (výchozí vybrané), keep = "k0,k1" (čísla řádků od 0, i rozsah 3-4) nebo auto2 (dva sousední řádky uprostřed pole): zbytek pole včetně úvratí
-- a ostrovů se označí za postříkaný (jako dbgCmd coverField), takže drony letí jen keep. Čísla řádků jsou od okraje pole (minN) po šířce záběru
C.handlers.coverLines = function(a)
    local trailer = C.findVehicle(a.trailer or "max")
    local station = trailer ~= nil and C.getStation(trailer) or nil
    local R = release()
    if station == nil or R == nil then
        return false, "vlek nenalezen"
    end
    local fieldId = C.num(a.field, station.fieldId)
    local field = fieldId ~= nil and fieldId ~= 0 and R.SprayDroneRoute.getFieldById(fieldId) or nil
    local sprayType = R.SprayDroneStation.getSprayType(trailer)
    if field == nil or sprayType == nil then
        return false, "pole nebo druh postřiku chybí (vybrat pole, naplnit koncentrát)"
    end
    local frame = R.SprayDroneRoute.getFrame(field)
    local ww = station.workWidth
    local count = 0
    local s = frame.minN + ww * 0.5
    while s < frame.maxN do
        count = count + 1
        s = s + ww
    end
    local keep
    if (a.keep or "auto2"):lower() == "auto2" then
        local first = math.max(math.floor(count / 2) - 1, 0)
        keep = { [first] = true, [first + 1] = true }
    else
        keep = parseLines(a.keep)
    end
    local entry = { type = sprayType.index, ww = ww, hl = station.headlands, lines = {}, headlands = {}, islands = {} }
    for k = 0, count do
        if not keep[k] then
            entry.lines[k] = { { -1e7, 1e7 } }
        end
    end
    for i = 1, station.headlands do
        entry.headlands[i] = { { -1e9, 1e9 } }
    end
    for islandIndex = 1, #R.SprayDroneRoute.getFieldShape(field).islands do
        entry.islands[islandIndex] = {}
        for i = 1, station.headlands do
            entry.islands[islandIndex][i] = { { -1e9, 1e9 } }
        end
    end
    station.coverage[fieldId] = entry
    R.SprayDroneStation.markRouteDirty(trailer)
    R.SprayDroneStation.raiseCoverage(trailer, true)
    local names = {}
    for k in pairs(keep) do
        table.insert(names, k)
    end
    table.sort(names)
    return true, string.format("pole %d: řádků %d, nepokryté %s (záběr %.1f m)", fieldId, count, table.concat(names, ","), ww)
end

---------------------------------------------------------------------------------------------------
-- N4 droneHover

C.hovers = C.hovers or {}

local function hoverFor(self)
    local list = C.hovers
    if #list == 0 then
        return nil
    end
    local R = release()
    local index = R.SprayDroneDrones.getIndex(self)
    for _, j in ipairs(list) do
        if j.trailer == self and j.k == index then
            return j
        end
    end
end

-- Obálka na SprayDroneStation.updateFlight (volá se přes tabulku, takže jde nahradit): dokud visí zakázka, dron ve vzduchu neletí, jen drží pozici a rotory běží
-- (updateDroneParts je zvlášť), baterie se nevybíjí a podmínky letu (vítr, signál, pohyb vleku) se nekontrolují.
local function installHover()
    local R = release()
    if R == nil then
        return false
    end
    local S = R.SprayDroneStation
    if C.origUpdateFlight == nil then
        C.origUpdateFlight = S.updateFlight
    end
    S.updateFlight = function(self, dt)
        local j = hoverFor(self)
        if j ~= nil and self[S.SPEC_NAME].airborne then
            if j.from == nil then
                j.from = g_time + j.delay * 1000
                j.to = j.from + j.seconds * 1000
            end
            if g_time >= j.from and g_time < j.to then
                self:raiseActive()
                return
            end
        end
        return C.origUpdateFlight(self, dt)
    end
    return true
end

-- droneHover: trailer, drone (1; 0 = všechny), seconds (5), delay (s po vzletu, než se dron zastaví; 0), wait = true čeká na konec visení; čas teče až od vzletu
C.handlers.droneHover = function(a)
    local trailer = C.findVehicle(a.trailer or "max")
    if trailer == nil or C.getStation(trailer) == nil then
        return false, "vlek nenalezen"
    end
    if not installHover() then
        return false, "release mód nedostupný"
    end
    local drone = C.num(a.drone, 1)
    local jobs = {}
    for k in eachDrone(trailer) do
        if drone == 0 or drone == k then
            for i = #C.hovers, 1, -1 do
                if C.hovers[i].trailer == trailer and C.hovers[i].k == k then
                    table.remove(C.hovers, i)
                end
            end
            local job = { trailer = trailer, k = k, seconds = C.num(a.seconds, 5), delay = C.num(a.delay, 0) }
            table.insert(C.hovers, job)
            table.insert(jobs, job)
        end
    end
    if #jobs == 0 then
        return false, "dron nenalezen"
    end
    if C.bool(a.wait, false) then
        return "pending", function()
            for _, j in ipairs(jobs) do
                if j.to == nil or g_time < j.to then
                    return nil
                end
            end
            return true, "visení skončilo"
        end
    end
    return true, string.format("dron %s visí %.1f s po vzletu (+%.1f s)", tostring(drone), jobs[1].seconds, jobs[1].delay)
end

---------------------------------------------------------------------------------------------------
-- N5 toolboxSet

-- toolboxSet: trailer, open = true/false (idempotentní; jen když se stav liší), part = all | číslo bedny, fill = true (naplní police kanystry jako dbgCmd toolboxFill),
-- wait = true čeká na doběh víka
C.handlers.toolboxSet = function(a)
    local trailer = C.findVehicle(a.trailer or "mini")
    local station = trailer ~= nil and C.getStation(trailer) or nil
    local R = release()
    if station == nil or R == nil or station.toolbox == nil then
        return false, "vlek nebo bedna nenalezeny"
    end
    local tb = station.toolbox
    if C.bool(a.fill, false) then
        local d = R.SprayDroneDebug
        d.commandId = (d.commandId or 0) + 1
        d.runCommand(trailer, "toolboxFill")
    end
    local parts = {}
    if a.part == nil or a.part == "all" then
        parts = tb.parts
    elseif tb.parts[C.num(a.part, 0)] ~= nil then
        parts = { tb.parts[C.num(a.part, 0)] }
    else
        return false, "bedna " .. tostring(a.part) .. " není"
    end
    local open = C.bool(a.open, nil)
    if open ~= nil then
        for _, part in ipairs(parts) do
            R.SprayDroneToolbox.setOpen(trailer, open, part)
        end
    end
    local function state()
        local out = {}
        for _, part in ipairs(parts) do
            table.insert(out, string.format("bedna %d open=%s lid=%.2f", part.index, tostring(part.open), part.lidT))
        end
        return table.concat(out, ", ")
    end
    if open ~= nil and C.bool(a.wait, false) then
        return "pending", function()
            for _, part in ipairs(parts) do
                if math.abs(part.lidT - (open and 1 or 0)) > 0.01 then
                    return nil
                end
            end
            return true, state()
        end
    end
    return true, state()
end

---------------------------------------------------------------------------------------------------
-- N7 mark, seq

-- mark: name; do logu zapíše "MARK <name>" s časem hry (kotva pro sesynchronizování klipů s logem)
C.handlers.mark = function(a)
    C.log("MARK %s", tostring(a.name or "mark"))
    return true, string.format("mark %s g_time=%d", tostring(a.name or "mark"), g_time)
end

C.seqs = C.seqs or {}

-- seq: steps = "t akce k=v k=v; t akce k=v; ...", t = sekundy od přijetí příkazu (měří se uvnitř hry, bez jitteru souborového dotazu), hodnoty bez mezer a středníků;
-- ack přijde po provedení všech kroků i jejich čekání (pending příkazy), timeout= pro celou sekvenci. Selhání kroku se zapíše a sekvence pokračuje
C.handlers.seq = function(a)
    local steps = {}
    for chunk in tostring(a.steps or ""):gmatch("[^;]+") do
        local t, action, rest = chunk:match("^%s*([%d%.]+)%s+(%S+)%s*(.*)$")
        if t == nil then
            return false, "chybný krok: " .. chunk
        end
        local args = {}
        for k, v in rest:gmatch("(%S+)=(%S+)") do
            args[k] = v
        end
        table.insert(steps, { t = tonumber(t), action = action, args = args, order = #steps })
    end
    table.sort(steps, function(x, y)
        return x.t < y.t or (x.t == y.t and x.order < y.order)
    end)
    local job = { t0 = g_time, steps = steps, next = 1, polls = {}, errors = {} }
    table.insert(C.seqs, job)
    return "pending", function()
        if job.done then
            return #job.errors == 0, #job.errors == 0 and ("sekvence hotová, kroků " .. #steps) or table.concat(job.errors, "; ")
        end
    end
end

local function seqFrame(job)
    while job.next <= #job.steps and g_time - job.t0 >= job.steps[job.next].t * 1000 do
        local step = job.steps[job.next]
        job.next = job.next + 1
        local handler = C.handlers[step.action]
        if handler == nil then
            table.insert(job.errors, step.action .. ": neznámá akce")
        else
            local called, r1, r2 = pcall(handler, step.args)
            if not called then
                table.insert(job.errors, step.action .. ": " .. tostring(r1))
            elseif r1 == "pending" then
                table.insert(job.polls, { poll = r2, action = step.action, deadline = g_time + C.num(step.args.timeout, 120) * 1000 })
            else
                C.log("seq %s t=%.2f -> %s %s", step.action, step.t, r1 and "ok" or "CHYBA", tostring(r2))
                if not r1 then
                    table.insert(job.errors, step.action .. ": " .. tostring(r2))
                end
            end
        end
    end
    for i = #job.polls, 1, -1 do
        local p = job.polls[i]
        local called, ok, msg = pcall(p.poll)
        if not called then
            table.insert(job.errors, p.action .. ": " .. tostring(ok))
            table.remove(job.polls, i)
        elseif ok ~= nil then
            C.log("seq %s dokončeno -> %s %s", p.action, ok and "ok" or "CHYBA", tostring(msg))
            if not ok then
                table.insert(job.errors, p.action .. ": " .. tostring(msg))
            end
            table.remove(job.polls, i)
        elseif g_time > p.deadline then
            table.insert(job.errors, p.action .. ": vypršel čas čekání")
            table.remove(job.polls, i)
        end
    end
    job.done = job.next > #job.steps and #job.polls == 0
end

function C.v2Frame(dt)
    for i = #C.hovers, 1, -1 do
        local j = C.hovers[i]
        if j.trailer.isDeleted or (j.to ~= nil and g_time > j.to + 1000) then
            table.remove(C.hovers, i)
        end
    end
    for i = #C.seqs, 1, -1 do
        local job = C.seqs[i]
        seqFrame(job)
        if job.done then
            table.remove(C.seqs, i)
            job.finished = true
        end
    end
end

---------------------------------------------------------------------------------------------------
-- N10 screenWake

-- screenWake: trailer, off = true displej uspí (pro zkoušku); jinak ho rozsvítí na dalších SCREEN_SLEEP_MS (10 min)
C.handlers.screenWake = function(a)
    local trailer = C.findVehicle(a.trailer or "mini")
    local R = release()
    if trailer == nil or R == nil or C.getStation(trailer) == nil then
        return false, "vlek nenalezen"
    end
    local spec = R.SprayDroneDrones.getRoot(trailer)
    local asleep = C.bool(a.off, false)
    spec.screenWakeTime = asleep and g_time - R.SprayDroneLink.SCREEN_SLEEP_MS - 1000 or g_time
    return true, string.format("displej %s (plannerScreenOn %s)", asleep and "uspán" or "probuzen", spec.plannerScreenOn ~= nil and "je" or "chybí")
end

---------------------------------------------------------------------------------------------------
-- N9 spawnCanister

-- spawnCanister: kind = fertilizer | herbicide | diesel | limebag, x, z, yaw (stupně), liters (20; pytel 50), lift (0.15 m nad terénem), still = true (kinematický, stojí),
-- trailer (kterýkoli vlek SDT s bednou, výchozí první nalezený; kanystr vzniká na zadané poloze, vlek tam stát nemusí)
C.handlers.spawnCanister = function(a)
    local R = release()
    if R == nil then
        return false, "release mód nedostupný"
    end
    local T = R.SprayDroneToolbox
    local kinds = {
        fertilizer = FillType.SDT_CONCENTRATE_FERTILIZER, herbicide = FillType.SDT_CONCENTRATE_HERBICIDE, diesel = FillType.DIESEL,
        limebag = FillType.SDT_FINE_LIME,
    }
    local kind = (a.kind or "fertilizer"):lower()
    local fillType = kinds[kind]
    if fillType == nil then
        return false, "druh neznámý: " .. kind
    end
    local trailer = a.trailer ~= nil and C.findVehicle(a.trailer) or nil
    if trailer == nil then
        for v in C.eachVehicle() do
            local station = C.getStation(v)
            if not v.isDeleted and station ~= nil and station.toolbox ~= nil then
                trailer = v
                break
            end
        end
    end
    if trailer == nil then
        return false, "není vlek SDT s bednou"
    end
    local x, z = C.num(a.x, nil), C.num(a.z, nil)
    if x == nil or z == nil then
        return false, "chybí x, z"
    end
    if C.playerNear ~= nil then
        C.playerNear(x + 8, z + 8)
    end
    local y = C.terrainY(x, z) + C.num(a.lift, 0.15)
    local liters = C.num(a.liters, kind == "limebag" and T.LIME_BAG_LITERS or 20)
    local ok, reason = T.spawnCanister(trailer, fillType, liters, function(success, vehicle)
        if not success then
            C.log("spawnCanister: nevznikl")
            return
        end
        if C.bool(a.still, false) then
            setRigidBodyType(vehicle.rootNode, RigidBodyType.KINEMATIC)
        end
        C.log("spawnCanister %s: id %s", kind, tostring(vehicle.id))
    end, { x, y, z, math.rad(C.num(a.yaw, 0)) })
    return ok ~= false, "spawn " .. kind .. " " .. tostring(reason or "odeslán")
end
