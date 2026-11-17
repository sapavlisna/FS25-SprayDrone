-- Vlastní kamera: dráha s klíči (Hermite/Catmull-Rom), sledování vozidla, orbit, statický pohled. HUD a hráč se při startu skryjí.

local C = SprayDroneCinema
C.cam = C.cam or { active = false }

C.RAY_MASK = CollisionFlag.STATIC_OBJECT + CollisionFlag.TREE + CollisionFlag.BUILDING

---------------------------------------------------------------------------------------------------
-- interpolace

-- Hermiteova křivka s konečnými rozdíly jako tangentami (Catmull-Rom pro nerovnoměrné časy). vs[i] = pole n čísel.
local function hermite(ts, vs, n, t)
    local count = #ts
    local out = {}
    if count == 1 or t <= ts[1] then
        for c = 1, n do out[c] = vs[1][c] end
        return out
    end
    if t >= ts[count] then
        for c = 1, n do out[c] = vs[count][c] end
        return out
    end
    local i = 1
    while ts[i + 1] < t do
        i = i + 1
    end
    local t1, t2 = ts[i], ts[i + 1]
    local dt = t2 - t1
    local s = (t - t1) / dt
    local s2, s3 = s * s, s * s * s
    local h00, h10, h01, h11 = 2 * s3 - 3 * s2 + 1, s3 - 2 * s2 + s, -2 * s3 + 3 * s2, s3 - s2
    local ia, ib = math.max(i - 1, 1), math.min(i + 2, count)
    for c = 1, n do
        local p1, p2 = vs[i][c], vs[i + 1][c]
        local m1 = i == 1 and (p2 - p1) / dt or (p2 - vs[ia][c]) / (t2 - ts[ia])
        local m2 = i + 1 == count and (p2 - p1) / dt or (vs[ib][c] - p1) / (ts[ib] - t1)
        out[c] = h00 * p1 + h10 * dt * m1 + h01 * p2 + h11 * dt * m2
    end
    return out
end
C.hermite = hermite

-- Bod klíče: pro pos (pre = "") x y z rel at, pro cíl (pre = "t") tx ty tz trel tat.
local function resolvePoint(k, isTarget)
    local x, y, z, rel, at
    if isTarget then
        x, y, z, rel, at = k.tx, k.ty, k.tz, k.trel, k.tat
    else
        x, y, z, rel, at = k.x, k.y, k.z, k.rel, k.at
    end
    if at ~= nil then
        local node = C.resolveNode(at)
        if node ~= nil then
            return C.localOffset(node, x or 0, y or 0, z or 0, k.full == 1)
        end
        if k.missing == nil then
            C.log("kamera: uzel '%s' nenalezen, souřadnice se berou světově", at)
        end
        k.missing = at
    end
    x, y, z = x or 0, y or 0, z or 0
    if rel == "terrain" or rel == "t" then
        y = C.terrainY(x, z) + y
    end
    return x, y, z
end

---------------------------------------------------------------------------------------------------
-- skrytí HUD a hráče

function C.hideScene(hide)
    local cam = C.cam
    pcall(function()
        local hud = g_currentMission.hud
        if hud ~= nil then
            if hud.setIsVisible ~= nil then hud:setIsVisible(not hide) end
            if hud.setInputHelpVisible ~= nil then hud:setInputHelpVisible(not hide) end
        end
    end)
    pcall(function()
        local player = g_localPlayer
        if player == nil then
            return
        end
        if hide then
            local vehicle = player:getCurrentVehicle()
            if vehicle ~= nil then
                vehicle:deleteVehicleCharacter()
                cam.charVehicle = vehicle
            else
                player.graphicsComponent:setModelVisibility(false)
                cam.hidModel = true
            end
        else
            if cam.charVehicle ~= nil then
                cam.charVehicle:restoreVehicleCharacter()
                cam.charVehicle = nil
            end
            if cam.hidModel then
                player.graphicsComponent:setModelVisibility(true)
                cam.hidModel = false
            end
        end
    end)
end

function C.camStart()
    local cam = C.cam
    if cam.active then
        return true
    end
    pcall(function() cam.prevCamera = g_localPlayer:getCurrentCameraNode() end)
    local fov = math.rad(45)
    local px, py, pz, rx, ry, rz = 0, 100, 0, 0, 0, 0
    if cam.prevCamera ~= nil then
        fov = getFovY(cam.prevCamera)
        px, py, pz = getWorldTranslation(cam.prevCamera)
        rx, ry, rz = getWorldRotation(cam.prevCamera)
    end
    cam.rig = createTransformGroup("sdcRig")
    cam.pitchNode = createTransformGroup("sdcPitch")
    cam.node = createCamera("sdcCam", fov, 0.3, 12000)
    link(getRootNode(), cam.rig)
    link(cam.rig, cam.pitchNode)
    link(cam.pitchNode, cam.node)
    setRotation(cam.node, 0, math.pi, 0)
    setWorldTranslation(cam.rig, px, py, pz)
    g_cameraManager:addCamera(cam.node, nil, false)
    g_cameraManager:setActiveCamera(cam.node)
    cam.active = true
    cam.fov = fov
    C.hideScene(true)
    C.log("kamera zapnuta")
    return true
end

function C.camStop()
    local cam = C.cam
    if not cam.active then
        return false
    end
    cam.shot = nil
    C.hideScene(false)
    local prev = cam.prevCamera
    if prev == nil then
        pcall(function() prev = g_localPlayer:getCurrentCameraNode() end)
    end
    if prev ~= nil then
        g_cameraManager:setActiveCamera(prev)
    end
    g_cameraManager:removeCamera(cam.node)
    delete(cam.node)
    delete(cam.pitchNode)
    delete(cam.rig)
    cam.node, cam.pitchNode, cam.rig = nil, nil, nil
    cam.active = false
    C.log("kamera vypnuta, původní kamera vrácena")
    return true
end

---------------------------------------------------------------------------------------------------
-- bezpečnost: terén a překážky na paprsku cíl -> kamera

local probe = { dist = nil }

function probe:callback(hitObjectId, x, y, z, distance)
    if hitObjectId ~= nil and hitObjectId ~= 0 then
        self.dist = distance
    end
    return false
end

function C.safeguard(shot, px, py, pz, tx, ty, tz)
    local ground = C.terrainY(px, pz)
    local warn = nil
    if py < ground + (shot.minClear or 0.5) then
        py = ground + (shot.minClear or 0.5)
        warn = "terén"
    end
    if shot.avoid ~= "none" then
        -- kolizní koule kamery: šest krátkých paprsků, překážka blíž než radius odsune kameru pryč (kmen, sloup, stěna)
        local r = shot.radius or 0.8
        local ox, oy, oz = px, py, pz
        for _, d in ipairs(C.RAY_DIRS) do
            probe.dist = nil
            raycastClosest(ox, oy, oz, d[1], d[2], d[3], r, "callback", probe, C.RAY_MASK)
            if probe.dist ~= nil and probe.dist < r then
                local push = r - probe.dist
                px, py, pz = px - d[1] * push, py - d[2] * push, pz - d[3] * push
                warn = "překážka u kamery"
            end
        end
    end
    return px, py, pz, warn
end

C.RAY_DIRS = { { 1, 0, 0 }, { -1, 0, 0 }, { 0, 1, 0 }, { 0, -1, 0 }, { 0, 0, 1 }, { 0, 0, -1 } }

-- Vzhledem k vertikálnímu paprsku shora: kamera pod nejvyšším bodem překážky (koruna, střecha) je pravděpodobně uvnitř.
function C.insideObstacle(px, py, pz)
    local ground = C.terrainY(px, pz)
    probe.dist = nil
    local top = ground + 40
    raycastClosest(px, math.max(top, py + 5), pz, 0, -1, 0, math.max(top, py + 5) - ground + 1, "callback", probe, C.RAY_MASK)
    if probe.dist ~= nil then
        local hitY = math.max(top, py + 5) - probe.dist
        if hitY > py + 0.2 and hitY - ground > 1.5 then
            return true, hitY
        end
    end
    return false
end

---------------------------------------------------------------------------------------------------
-- záběry: každý vrací funkci eval(shot, dt) -> px,py,pz, tx,ty,tz, fovDeg, rollDeg, hotovo

local function buildPath(a, cmd)
    local keys = cmd.keys
    if #keys < 1 then
        return nil, "chybí <key>"
    end
    local defaultFov = C.num(a.fov, 45)
    local duration = C.num(a.duration, keys[#keys].t or 5)
    local shot = { kind = "path", duration = duration, ease = a.ease or "smooth", keys = keys, defaultFov = defaultFov }
    shot.eval = function(self, time)
        local u = self.duration > 0 and C.clamp(time / self.duration, 0, 1) or 1
        local tp = C.ease(self.ease, u) * self.duration
        local ts, ps, tts, tps, fs, fts, rs, rts = {}, {}, {}, {}, {}, {}, {}, {}
        for _, k in ipairs(self.keys) do
            local t = k.t or 0
            local x, y, z = resolvePoint(k, false)
            table.insert(ts, t)
            table.insert(ps, { x, y, z })
            if k.tx ~= nil or k.tat ~= nil then
                local tx, ty, tz = resolvePoint(k, true)
                table.insert(tts, t)
                table.insert(tps, { tx, ty, tz })
            end
            if k.fov ~= nil then
                table.insert(fts, t)
                table.insert(fs, { k.fov })
            end
            if k.roll ~= nil then
                table.insert(rts, t)
                table.insert(rs, { k.roll })
            end
        end
        local p = hermite(ts, ps, 3, tp)
        local tg = #tts > 0 and hermite(tts, tps, 3, tp) or { p[1], p[2], p[3] + 10 }
        local fov = #fts > 0 and hermite(fts, fs, 1, tp)[1] or self.defaultFov
        local roll = #rts > 0 and hermite(rts, rs, 1, tp)[1] or 0
        return p[1], p[2], p[3], tg[1], tg[2], tg[3], fov, roll, time >= self.duration
    end
    return shot
end

local function buildFollow(a)
    local node = C.resolveNode(a.target or a.vehicle)
    if node == nil then
        return nil, "cíl sledování nenalezen: " .. tostring(a.target or a.vehicle)
    end
    local alias = a.target or a.vehicle
    local shot = {
        kind = "follow", duration = C.num(a.duration, 0), ease = a.ease or "smooth", alias = alias, fov = C.num(a.fov, 45),
        o1 = { C.num(a.ox, 0), C.num(a.oy, 2), C.num(a.oz, -8) }, l1 = { C.num(a.lx, 0), C.num(a.ly, 1), C.num(a.lz, 4) },
        tau = C.num(a.tau, 0.4), tauLook = C.num(a.tauLook, 0.3), full = C.bool(a.full, false),
    }
    shot.o2 = { C.num(a.ox2, shot.o1[1]), C.num(a.oy2, shot.o1[2]), C.num(a.oz2, shot.o1[3]) }
    shot.l2 = { C.num(a.lx2, shot.l1[1]), C.num(a.ly2, shot.l1[2]), C.num(a.lz2, shot.l1[3]) }
    shot.fov2 = C.num(a.fov2, shot.fov)
    shot.eval = function(self, time, dt)
        local n = C.resolveNode(self.alias)
        if n == nil then
            return nil
        end
        local u = self.duration > 0 and C.ease(self.ease, time / self.duration) or 0
        local function mix(p, q, i) return p[i] + (q[i] - p[i]) * u end
        local gx, gy, gz = C.localOffset(n, mix(self.o1, self.o2, 1), mix(self.o1, self.o2, 2), mix(self.o1, self.o2, 3), self.full)
        local lx, ly, lz = C.localOffset(n, mix(self.l1, self.l2, 1), mix(self.l1, self.l2, 2), mix(self.l1, self.l2, 3), self.full)
        if self.px == nil then
            self.px, self.py, self.pz, self.qx, self.qy, self.qz = gx, gy, gz, lx, ly, lz
        else
            local ka = 1 - math.exp(-dt * 0.001 / math.max(self.tau, 0.001))
            local kb = 1 - math.exp(-dt * 0.001 / math.max(self.tauLook, 0.001))
            self.px, self.py, self.pz = self.px + (gx - self.px) * ka, self.py + (gy - self.py) * ka, self.pz + (gz - self.pz) * ka
            self.qx, self.qy, self.qz = self.qx + (lx - self.qx) * kb, self.qy + (ly - self.qy) * kb, self.qz + (lz - self.qz) * kb
        end
        return self.px, self.py, self.pz, self.qx, self.qy, self.qz, self.fov + (self.fov2 - self.fov) * u, 0, self.duration > 0 and time >= self.duration
    end
    return shot
end

local function buildOrbit(a)
    local shot = {
        kind = "orbit", duration = C.num(a.duration, 6), ease = a.ease or "smooth", fov = C.num(a.fov, 45), fov2 = C.num(a.fov2, C.num(a.fov, 45)),
        center = a.target or a.vehicle, center2 = a.target2, cx = C.num(a.x, 0), cy = C.num(a.y, 0), cz = C.num(a.z, 0), crel = a.rel,
        r1 = C.num(a.radius, 10), r2 = C.num(a.radius2, C.num(a.radius, 10)), h1 = C.num(a.height, 3), h2 = C.num(a.height2, C.num(a.height, 3)),
        a1 = math.rad(C.num(a.angle0, 0)), a2 = math.rad(C.num(a.angle1, 90)), lx = C.num(a.lx, 0), ly = C.num(a.ly, 0), lz = C.num(a.lz, 0),
        tau = C.num(a.tau, 0.2),
    }
    shot.eval = function(self, time, dt)
        local u = self.duration > 0 and C.ease(self.ease, time / self.duration) or 0
        local x, y, z
        if self.center ~= nil then
            local n = C.resolveNode(self.center)
            if n == nil then
                return nil
            end
            x, y, z = getWorldTranslation(n)
            -- target2: střed orbitu je střed mezi dvěma uzly (např. dva drony Maxu)
            local n2 = self.center2 ~= nil and C.resolveNode(self.center2) or nil
            if n2 ~= nil then
                local x2, y2, z2 = getWorldTranslation(n2)
                x, y, z = (x + x2) * 0.5, (y + y2) * 0.5, (z + z2) * 0.5
            end
        else
            x, y, z = self.cx, self.cy, self.cz
            if self.crel == "terrain" then
                y = C.terrainY(x, z) + y
            end
        end
        if self.sx == nil then
            self.sx, self.sy, self.sz = x, y, z
        else
            local k = 1 - math.exp(-dt * 0.001 / math.max(self.tau, 0.001))
            self.sx, self.sy, self.sz = self.sx + (x - self.sx) * k, self.sy + (y - self.sy) * k, self.sz + (z - self.sz) * k
        end
        local ang = self.a1 + (self.a2 - self.a1) * u
        local r = self.r1 + (self.r2 - self.r1) * u
        local h = self.h1 + (self.h2 - self.h1) * u
        local px, pz = self.sx + math.sin(ang) * r, self.sz + math.cos(ang) * r
        return px, self.sy + h, pz, self.sx + self.lx, self.sy + self.ly, self.sz + self.lz, self.fov + (self.fov2 - self.fov) * u, 0,
            time >= self.duration
    end
    return shot
end

local function buildStatic(a)
    local shot = { kind = "static", duration = 0, fov = C.num(a.fov, 45) }
    shot.pos = { x = C.num(a.x, 0), y = C.num(a.y, 0), z = C.num(a.z, 0), rel = a.rel, at = a.at }
    shot.tgt = { tx = C.num(a.tx, 0), ty = C.num(a.ty, 0), tz = C.num(a.tz, 0), trel = a.trel, tat = a.tat }
    shot.eval = function(self)
        local px, py, pz = resolvePoint(self.pos, false)
        local tx, ty, tz = resolvePoint(self.tgt, true)
        return px, py, pz, tx, ty, tz, self.fov, 0, false
    end
    return shot
end

---------------------------------------------------------------------------------------------------
-- průběh

local function applyPose(px, py, pz, tx, ty, tz, fovDeg, rollDeg)
    local cam = C.cam
    local dx, dy, dz = tx - px, ty - py, tz - pz
    local len = math.sqrt(dx * dx + dy * dy + dz * dz)
    if len < 0.001 then
        dx, dy, dz, len = 0, 0, 1, 1
    end
    local pitch, yaw = MathUtil.directionToPitchYaw(dx / len, dy / len, dz / len)
    setWorldTranslation(cam.rig, px, py, pz)
    setRotation(cam.rig, 0, yaw, 0)
    setRotation(cam.pitchNode, pitch, 0, 0)
    setRotation(cam.node, 0, math.pi, math.rad(rollDeg or 0))
    if fovDeg ~= cam.fov then
        cam.fov = fovDeg
        setFovY(cam.node, math.rad(fovDeg))
    end
end

function C.cameraFrame(dt)
    local cam = C.cam
    local shot = cam.shot
    if not cam.active or shot == nil then
        return
    end
    shot.time = shot.time + dt * 0.001
    local px, py, pz, tx, ty, tz, fov, roll, finished = shot.eval(shot, shot.time, dt)
    if px == nil then
        return
    end
    -- dolní propust na živě sledovaný cíl a polohu (fyzika vozidla škube a teleobjektiv to zesílí); tsmooth/psmooth = časová konstanta v s
    if shot.tsmooth > 0 or shot.psmooth > 0 then
        local f = shot.filt
        if f == nil then
            f = { px, py, pz, tx, ty, tz }
            shot.filt = f
        else
            local kt = shot.tsmooth > 0 and 1 - math.exp(-dt * 0.001 / shot.tsmooth) or 1
            local kp = shot.psmooth > 0 and 1 - math.exp(-dt * 0.001 / shot.psmooth) or 1
            f[1], f[2], f[3] = f[1] + (px - f[1]) * kp, f[2] + (py - f[2]) * kp, f[3] + (pz - f[3]) * kp
            f[4], f[5], f[6] = f[4] + (tx - f[4]) * kt, f[5] + (ty - f[5]) * kt, f[6] + (tz - f[6]) * kt
        end
        px, py, pz, tx, ty, tz = f[1], f[2], f[3], f[4], f[5], f[6]
    end
    local warn
    px, py, pz, warn = C.safeguard(shot, px, py, pz, tx, ty, tz)
    if warn ~= nil and not shot.warned[warn] then
        shot.warned[warn] = shot.time
        C.log("kamera %s: varování '%s' v čase %.2f s", shot.id, warn, shot.time)
    end
    applyPose(px, py, pz, tx, ty, tz, fov, roll)
    cam.px, cam.py, cam.pz = px, py, pz
    shot.frames = shot.frames + 1
    shot.dtSum = shot.dtSum + dt
    shot.dtMax = math.max(shot.dtMax, dt)
    if dt > 25 then
        shot.over25 = shot.over25 + 1
    end
    if finished and not shot.finished then
        shot.finished = true
        C.log("kamera %s konec (frames=%d dt_prum=%.1f ms dt_max=%.1f ms nad25ms=%d, doba %.2f s)", shot.id, shot.frames,
            shot.dtSum / math.max(shot.frames, 1), shot.dtMax, shot.over25, shot.time)
        shot.result = true
    end
end

local function startShot(id, shot, a)
    local cam = C.cam
    C.camStart()
    shot.id = id
    shot.time = 0
    shot.frames, shot.dtSum, shot.dtMax, shot.over25 = 0, 0, 0, 0
    shot.warned = {}
    shot.tsmooth, shot.psmooth, shot.filt = C.num(a.tsmooth, 0), C.num(a.psmooth, 0), nil
    shot.minClear = C.num(a.minClear, 0.5)
    shot.radius = C.num(a.radius_cam, 0.8)
    shot.avoid = a.avoid
    cam.shot = shot
    C.log("kamera %s start (%s, %.2f s)", id, shot.kind, shot.duration)
    -- první snímek hned, ať se kamera nezastaví na staré poloze
    C.cameraFrame(0)
    if C.bool(a.wait, false) and shot.duration > 0 then
        return "pending", function()
            if shot.finished then
                local warns = {}
                for k, t in pairs(shot.warned) do
                    table.insert(warns, string.format("%s@%.1fs", k, t))
                end
                return true, string.format("hotovo, frames=%d dt_max=%.1f nad25ms=%d varování=[%s]", shot.frames, shot.dtMax, shot.over25, table.concat(warns, ","))
            end
        end
    end
    return true, "kamera běží " .. shot.kind
end

-- Kontrola trasy bez spuštění: vzorky po 0,25 s, hlásí čas, kdy je kamera pod terénem, uvnitř překážky nebo ji paprsek posune.
local function checkShot(shot)
    local issues = {}
    local steps = math.max(math.floor(shot.duration / 0.25), 1)
    shot.warned, shot.minClear, shot.time = {}, shot.minClear or 0.5, 0
    for i = 0, steps do
        local t = shot.duration * i / steps
        local px, py, pz, tx, ty, tz = shot.eval(shot, t, 16)
        if px ~= nil then
            local _, ny, _, warn = C.safeguard(shot, px, py, pz, tx, ty, tz)
            local inside, top = C.insideObstacle(px, py, pz)
            if inside then
                warn = string.format("uvnitř překážky (horní hrana %.1f m, kamera %.1f m)", top, py)
            end
            if warn ~= nil then
                table.insert(issues, string.format("t=%.2f %s", t, warn))
            end
        end
    end
    return issues
end

---------------------------------------------------------------------------------------------------
-- příkazy

local function addShotHandler(name, builder)
    C.handlers[name] = function(a, cmd)
        local shot, err = builder(a, cmd)
        if shot == nil then
            return false, err
        end
        if C.bool(a.check, false) then
            local issues = checkShot(shot)
            if #issues > 0 then
                C.log("kontrola dráhy %s: %s", name, table.concat(issues, "; "))
            end
            if C.bool(a.checkOnly, false) then
                return true, #issues == 0 and "bez problémů" or table.concat(issues, "; ")
            end
        end
        return startShot(cmd.id, shot, a)
    end
end

addShotHandler("camPath", buildPath)
addShotHandler("camFollow", buildFollow)
addShotHandler("camOrbit", buildOrbit)
addShotHandler("camSet", buildStatic)

C.handlers.camStop = function()
    return true, C.camStop() and "kamera vypnuta" or "kamera nebyla zapnutá"
end

C.handlers.camState = function()
    local cam = C.cam
    return true, string.format("active=%s shot=%s pos=%.1f,%.1f,%.1f", tostring(cam.active), cam.shot ~= nil and cam.shot.id or "-", cam.px or 0, cam.py or 0, cam.pz or 0)
end

C.handlers.hud = function(a)
    C.hideScene(not C.bool(a.visible, true))
    return true, "hud"
end
