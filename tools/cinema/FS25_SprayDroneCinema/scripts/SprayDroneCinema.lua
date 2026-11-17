-- Vývojový mód pro natáčení traileru. Bez modSettings/FS25_SprayDroneCinema/cmd.xml nedělá nic.
-- Příkazy: <cmd id="5" action="camPath"><a n="duration" v="5"/><key t="0" x="1" .../></cmd> (viz tmp/trailer/cinema_log.md),
-- výsledek v ack.xml (posledních 12 výsledků). Moduly jsou ve stejné tabulce, takže `reload` je umí za hry nahrát znovu.
-- Příkazy pro video v2 (isolate, flightArea, coverLines, droneHover, toolboxSet, mark, seq, screenWake, spawnCanister, ...): SprayDroneCinemaV2.lua, přehled v tools/cinema/v2/prikazy_v2.md.

SprayDroneCinema = SprayDroneCinema or {}
local C = SprayDroneCinema

C.VERSION = "0.1.5"
C.POLL_MS = 250
C.ACK_KEEP = 12
C.handlers = {}
C.pending = C.pending or {}
C.pollAccum = C.pollAccum or 0
C.acks = C.acks or {}
C.modDir = C.modDir or g_currentModDirectory
C.dir = getUserProfileAppPath() .. "modSettings/FS25_SprayDroneCinema/"
C.cmdPath = C.dir .. "cmd.xml"
C.ackPath = C.dir .. "ack.xml"
C.SPEC_STATION = "spec_FS25_SprayDroneTrailer.sprayDroneStation"
C.KEY_ATTRS = { "t", "x", "y", "z", "rel", "at", "tx", "ty", "tz", "trel", "tat", "fov", "roll", "full" }
C.KEY_STRINGS = { rel = true, at = true, trel = true, tat = true }

C.ALIASES = {
    pickup = "pickup2017", mini = "sprayDroneTrailerMini", middle = "sprayDroneTrailerMiddle", max = "sprayDroneTrailerMax",
    mill = "sdtLimeMill", jd3650 = "series3650", mt655 = "challenger/mt655", mf8570 = "mf8570", rtv = "rtvx1140",
}

function C.log(fmt, ...)
    local stamp = ""
    pcall(function() stamp = getDate("%H:%M:%S") end)
    Logging.info("CINEMA t=%.3f %s " .. fmt, (g_time or 0) * 0.001, stamp, ...)
end

function C.num(v, default)
    local n = tonumber(v)
    if n == nil then
        return default
    end
    return n
end

function C.bool(v, default)
    if v == nil then
        return default
    end
    v = tostring(v):lower()
    return v == "true" or v == "1" or v == "yes"
end

function C.clamp(v, a, b)
    return math.max(a, math.min(b, v))
end

function C.terrainY(x, z)
    return getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
end

C.EASE = {
    linear = function(u) return u end,
    smooth = function(u) return u * u * (3 - 2 * u) end,
    inout = function(u) return u < 0.5 and 4 * u * u * u or 1 - (-2 * u + 2) ^ 3 / 2 end,
    sine = function(u) return (1 - math.cos(math.pi * u)) / 2 end,
    inQuad = function(u) return u * u end,
    outQuad = function(u) return 1 - (1 - u) * (1 - u) end,
    inCubic = function(u) return u * u * u end,
    outCubic = function(u) return 1 - (1 - u) ^ 3 end,
}

function C.ease(name, u)
    u = C.clamp(u, 0, 1)
    return (C.EASE[name or "smooth"] or C.EASE.smooth)(u)
end

---------------------------------------------------------------------------------------------------
-- vozidla

function C.eachVehicle()
    local list = g_currentMission ~= nil and g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    local i = 0
    return function()
        i = i + 1
        return list[i]
    end
end

function C.cfg(v)
    return (v.configFileName or ""):lower()
end

function C.getStation(v)
    local spec = v ~= nil and v[C.SPEC_STATION] or nil
    if spec == nil then
        return nil
    end
    return rawget(spec, "rootSpec") or spec
end

-- Vozidlo patří k soupravě, když je vlek s dronem nebo s ním (přes zapřažení) souvisí.
function C.isSetMember(v)
    if C.getStation(v) ~= nil then
        return true
    end
    if v.getAttachedImplements ~= nil then
        for _, impl in ipairs(v:getAttachedImplements()) do
            if impl.object ~= nil and C.getStation(impl.object) ~= nil then
                return true
            end
        end
    end
    return false
end

-- alias: pickup | mini | middle | max | mill | jd3650 | mt655 | mf8570 | rtv, nebo část cesty xml; "alias#2" = druhý nález
function C.findVehicle(alias)
    if alias == nil or alias == "" then
        return nil
    end
    local name, index = alias:match("^(.-)#(%d+)$")
    name = name or alias
    index = tonumber(index) or 1
    local pattern = (C.ALIASES[name:lower()] or name):lower()
    local found, preferred = {}, {}
    for v in C.eachVehicle() do
        if C.cfg(v):find(pattern, 1, true) ~= nil then
            table.insert(found, v)
            if C.isSetMember(v) then
                table.insert(preferred, v)
            end
        end
    end
    local list = #preferred > 0 and preferred or found
    return list[index]
end

function C.getDroneNode(trailer, k)
    local station = C.getStation(trailer)
    if station == nil then
        return nil
    end
    local d = station.drones ~= nil and station.drones[k] or (k == 1 and station or nil)
    return d ~= nil and d.node or nil
end

-- "pickup", "middle:drone1", "max#chargerLid" (i3dMapping vozidla; za # číslo je pořadí nálezu jako u findVehicle) -> uzel
function C.resolveNode(alias)
    if alias == nil then
        return nil
    end
    local owner, mapping = alias:match("^(.-)#(%a[%w_]*)$")
    if owner ~= nil then
        local v = C.findVehicle(owner)
        local m = v ~= nil and v.i3dMappings ~= nil and v.i3dMappings[mapping] or nil
        local node = m ~= nil and (m.nodeId or m) or nil
        return type(node) == "number" and node or nil
    end
    local base, k = alias:match("^(.-):drone(%d)$")
    if base ~= nil then
        local t = C.findVehicle(base)
        return t ~= nil and C.getDroneNode(t, tonumber(k)) or nil
    end
    local v = C.findVehicle(alias)
    return v ~= nil and v.rootNode or nil
end

-- Bod v souřadnicích uzlu jen s natočením kolem svislé osy (klidnější než celý náklon vozidla při jízdě).
function C.localOffset(node, ox, oy, oz, full)
    if full then
        return localToWorld(node, ox, oy, oz)
    end
    local wx, wy, wz = getWorldTranslation(node)
    local dx, _, dz = localDirectionToWorld(node, 0, 0, 1)
    local yaw = math.atan2(dx, dz)
    local s, c = math.sin(yaw), math.cos(yaw)
    return wx + ox * c + oz * s, wy + oy, wz - ox * s + oz * c
end

---------------------------------------------------------------------------------------------------
-- soubor příkazů a výsledků

local function xmlEscape(s)
    return (tostring(s):gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"):gsub("[\r\n]+", " "))
end

function C.writeAck(id, ok, msg)
    table.insert(C.acks, { id = id, ok = ok, msg = msg })
    while #C.acks > C.ACK_KEEP do
        table.remove(C.acks, 1)
    end
    local f = io.open(C.ackPath, "w")
    if f == nil then
        return
    end
    f:write('<?xml version="1.0" encoding="utf-8"?>\n<ack version="' .. C.VERSION .. '">\n')
    for _, a in ipairs(C.acks) do
        f:write(string.format('  <r id="%s" ok="%s" msg="%s"/>\n', xmlEscape(a.id), a.ok and "true" or "false", xmlEscape(a.msg)))
    end
    f:write("</ack>\n")
    f:close()
end

function C.readCmd()
    if not fileExists(C.cmdPath) then
        return nil
    end
    local h = loadXMLFile("sdcCmd", C.cmdPath)
    if h == nil or h == 0 then
        return nil
    end
    local cmd = { id = getXMLString(h, "cmd#id"), action = getXMLString(h, "cmd#action"), a = {}, keys = {} }
    cmd.code = getXMLString(h, "cmd.code")
    local i = 0
    while true do
        local base = string.format("cmd.a(%d)", i)
        if not hasXMLProperty(h, base) then
            break
        end
        local n = getXMLString(h, base .. "#n")
        if n ~= nil then
            cmd.a[n] = getXMLString(h, base .. "#v")
        end
        i = i + 1
    end
    i = 0
    while true do
        local base = string.format("cmd.key(%d)", i)
        if not hasXMLProperty(h, base) then
            break
        end
        local key = {}
        for _, name in ipairs(C.KEY_ATTRS) do
            local raw = getXMLString(h, base .. "#" .. name)
            if raw ~= nil then
                key[name] = C.KEY_STRINGS[name] and raw or (tonumber(raw) or raw)
            end
        end
        table.insert(cmd.keys, key)
        i = i + 1
    end
    delete(h)
    return cmd
end

function C.execute(cmd)
    local handler = C.handlers[cmd.action or ""]
    if handler == nil then
        C.writeAck(cmd.id, false, "neznámá akce: " .. tostring(cmd.action))
        return
    end
    local called, ok, msg, extra = pcall(handler, cmd.a, cmd)
    if not called then
        C.log("chyba %s: %s", tostring(cmd.action), tostring(ok))
        C.writeAck(cmd.id, false, "lua: " .. tostring(ok))
    elseif ok == "pending" then
        table.insert(C.pending, { id = cmd.id, action = cmd.action, poll = msg, timeout = g_time + C.num(cmd.a.timeout, 120) * 1000 })
    else
        C.writeAck(cmd.id, ok and true or false, msg)
        C.log("%s -> %s %s", tostring(cmd.action), ok and "ok" or "CHYBA", tostring(msg))
    end
end

function C.updatePending(dt)
    local i = 1
    while i <= #C.pending do
        local p = C.pending[i]
        local called, ok, msg = pcall(p.poll, dt)
        local done = false
        if not called then
            C.writeAck(p.id, false, "lua: " .. tostring(ok))
            done = true
        elseif ok ~= nil then
            C.writeAck(p.id, ok and true or false, msg)
            C.log("%s dokončeno -> %s %s", tostring(p.action), ok and "ok" or "CHYBA", tostring(msg))
            done = true
        elseif g_time > p.timeout then
            C.writeAck(p.id, false, "vypršel čas čekání")
            done = true
        end
        if done then
            table.remove(C.pending, i)
        else
            i = i + 1
        end
    end
end

function C:poll()
    local cmd = C.readCmd()
    if cmd == nil or cmd.id == nil or cmd.id == C.lastId then
        return
    end
    C.lastId = cmd.id
    C.execute(cmd)
end

function C.frame(dt)
    if C.cameraFrame ~= nil then
        C.cameraFrame(dt)
    end
    if C.driveFrame ~= nil then
        C.driveFrame(dt)
    end
    if C.worldFrame ~= nil then
        C.worldFrame(dt)
    end
    if C.v2Frame ~= nil then
        C.v2Frame(dt)
    end
    if #C.pending > 0 then
        C.updatePending(dt)
    end
end

---------------------------------------------------------------------------------------------------
-- životní cyklus

function C:loadMap()
    pcall(createFolder, C.dir)
    local existing = C.readCmd()
    if existing ~= nil then
        C.lastId = existing.id
    end
    C.log("načteno, verze %s, příkazy z %s", C.VERSION, C.cmdPath)
end

function C:deleteMap()
    if C.camStop ~= nil then
        pcall(C.camStop)
    end
end

function C:update(dt)
    if g_currentMission == nil or not g_currentMission.isRunning then
        return
    end
    C.frame(dt)
    C.pollAccum = C.pollAccum + dt
    if C.pollAccum >= C.POLL_MS then
        C.pollAccum = 0
        if fileExists(C.cmdPath) then
            local ok, err = pcall(C.poll, C)
            if not ok then
                C.log("chyba pollingu: %s", tostring(err))
            end
        end
    end
end

if not C.registered then
    C.registered = true
    addModEventListener(C)
end

---------------------------------------------------------------------------------------------------
-- obecné příkazy

local FILES = { "SprayDroneCinema", "SprayDroneCinemaCamera", "SprayDroneCinemaWorld", "SprayDroneCinemaScene", "SprayDroneCinemaDrive", "SprayDroneCinemaUi", "SprayDroneCinemaV2" }

-- reload: nahraje moduly znovu ze zdrojové složky (a: dir = cesta ke složce scripts; výchozí složka módu)
C.handlers.reload = function(a)
    local dir = a.dir or ((C.modDir or "") .. "scripts/")
    local done = {}
    for _, name in ipairs(FILES) do
        local path = dir .. name .. ".lua"
        if fileExists(path) then
            source(path)
            table.insert(done, name)
        end
    end
    return true, "nahráno " .. table.concat(done, ",") .. " verze " .. tostring(SprayDroneCinema.VERSION)
end

C.handlers.ping = function()
    return true, "pong " .. C.VERSION .. " čas hry " .. string.format("%.1f", (g_time or 0) * 0.001)
end

-- loadstring v enginu není: eval spouští Lua soubor (a.file), který nastaví SprayDroneCinema.evalResult (klient cinema_client.ev to obalí)
C.handlers.eval = function(a)
    if a.file == nil then
        return false, "chybí file"
    end
    C.evalResult = nil
    source(a.file)
    return true, tostring(C.evalResult)
end

-- výpis členů tabulky (typ první písmeno) a členů jejího __index
function C.keysOf(t)
    if type(t) ~= "table" then
        return "není tabulka: " .. tostring(t)
    end
    local out = {}
    for k, v in pairs(t) do
        table.insert(out, tostring(k) .. ":" .. type(v):sub(1, 1))
    end
    table.sort(out)
    local meta = getmetatable(t)
    if type(meta) == "table" and type(meta.__index) == "table" then
        local inherited = {}
        for k, v in pairs(meta.__index) do
            table.insert(inherited, tostring(k) .. ":" .. type(v):sub(1, 1))
        end
        table.sort(inherited)
        return table.concat(out, " ") .. " | meta: " .. table.concat(inherited, " ")
    end
    return table.concat(out, " ")
end

C.handlers.wait = function(a)
    local untilTime = g_time + C.num(a.seconds, 1) * 1000
    return "pending", function()
        if g_time >= untilTime then
            return true, "čekání hotovo"
        end
    end
end

C.handlers.vehicles = function()
    local out = {}
    for v in C.eachVehicle() do
        local x, y, z = getWorldTranslation(v.rootNode)
        local att = v.getAttacherVehicle ~= nil and v:getAttacherVehicle() or nil
        table.insert(out, string.format("%s id=%s (%.0f,%.0f)%s%s", (v.configFileName or "?"):match("([^/]+)%.xml$") or "?", tostring(v.id), x, z,
            att ~= nil and (" za " .. tostring(att.id)) or "", C.getStation(v) ~= nil and " [SDT]" or ""))
    end
    return true, table.concat(out, "; ")
end
