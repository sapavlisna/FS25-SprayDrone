-- Sdílená geometrie přenosných hadic (mlýnkový vozík na vápno, vodní hadice Maxu): křivka hadice pevné délky, která obchází vozidla
-- a leží na podlaze, rozmístění článků a poloha konce v ruce hráče.

SprayDroneHoseLib = {}
SprayDroneHoseLib.HOSE_MESH_RADIUS = 0.05       -- poloměr trubky článků v modelu; článek se v řezu zmenší na HOSE_RADIUS
SprayDroneHoseLib.HOSE_RADIUS = 0.032
SprayDroneHoseLib.HOSE_REACH = 0.95             -- podíl délky hadice, kam až hráč s koncem dojde (dál ho ruka nepustí)
SprayDroneHoseLib.HOSE_EXTRA_SHARE = 0.12
SprayDroneHoseLib.HOSE_EXTRA_FIXED = 0.9
SprayDroneHoseLib.HOSE_LEAD = 0.30              -- nejmenší rovný nájezd u portu a u koncovky (m), ať se hadice u spojky nelomí
SprayDroneHoseLib.HOSE_HELD_LEAD = 0.55         -- rovný nájezd za koncovkou v ruce hráče
SprayDroneHoseLib.HOSE_STIFF = 0.16              -- délka hadice u koncovky, která zůstává vodorovně ve výšce spojky (m); objímka koncovky je 0,106 m
SprayDroneHoseLib.HOSE_SAMPLES = 64
SprayDroneHoseLib.HOSE_FLOOR_CELL = 0.5         -- mřížka výšek podlahy pod hadicí (m) a doba platnosti zásahu paprsku (ms)
SprayDroneHoseLib.HOSE_FLOOR_TTL = 1500
SprayDroneHoseLib.HOSE_FLOOR_MASK = CollisionFlag.STATIC_OBJECT + CollisionFlag.BUILDING + (CollisionFlag.ROAD or 0)

local function bezier(p0, p1, p2, p3, t)
    local u = 1 - t
    local c0, c1, c2, c3 = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
    return { c0 * p0[1] + c1 * p1[1] + c2 * p2[1] + c3 * p3[1], c0 * p0[2] + c1 * p1[2] + c2 * p2[2] + c3 * p3[2],
        c0 * p0[3] + c1 * p1[3] + c2 * p2[3] + c3 * p3[3] }
end

local function normalize(x, y, z)
    local l = MathUtil.vector3Length(x, y, z)
    if l < 1e-6 then
        return 0, 0, 1
    end
    return x / l, y / l, z / l
end

local function terrainAt(x, z)
    return getTerrainHeightAtWorldPos(g_terrainNode, x, 0, z)
end

local floorCache, floorCount = {}, 0
local floorProbe = {}

function floorProbe:callback(hitObjectId, x, y, z, distance)
    if hitObjectId ~= nil and hitObjectId ~= 0 then
        self.hit, self.y = true, y
    end
    return false
end

-- Výška povrchu, na kterém hadice leží: terén, nebo statický objekt / budova / silnice do 0,6 m nad ním (paprsek shora). Výška
-- nad terénem se drží v mřížce HOSE_FLOOR_CELL po dobu HOSE_FLOOR_TTL, ať se při tažení hadice nestřílí paprsek na každý bod.
local function floorAt(x, z)
    local terrain = terrainAt(x, z)
    local cell = SprayDroneHoseLib.HOSE_FLOOR_CELL
    local key = math.floor(x / cell) * 100003 + math.floor(z / cell)
    local now = g_time or 0
    local entry = floorCache[key]
    if entry == nil or now - entry.t > SprayDroneHoseLib.HOSE_FLOOR_TTL then
        floorProbe.hit = false
        raycastClosest(x, terrain + 0.6, z, 0, -1, 0, 1.2, "callback", floorProbe, SprayDroneHoseLib.HOSE_FLOOR_MASK)
        if floorCount > 4000 then
            floorCache, floorCount = {}, 0
        end
        if entry == nil then
            floorCount = floorCount + 1
        end
        entry = { above = floorProbe.hit and math.max(floorProbe.y - terrain, 0) or 0, t = now }
        floorCache[key] = entry
    end
    return terrain + entry.above
end

-- Překážky: vozidla jako obdélníky v rovině podle v.size (širokou karoserii hadice obchází, pod ni nevede).
local function boxOf(v)
    local size = v.size
    if size == nil or (size.height or 0) < 0.4 or v.rootNode == nil or not entityExists(v.rootNode) then
        return nil
    end
    local cx, _, cz = localToWorld(v.rootNode, size.widthOffset or 0, 0, size.lengthOffset or 0)
    local ux, _, uz = localDirectionToWorld(v.rootNode, 1, 0, 0)
    local wx, _, wz = localDirectionToWorld(v.rootNode, 0, 0, 1)
    ux, _, uz = normalize(ux, 0, uz)
    wx, _, wz = normalize(wx, 0, wz)
    return { x = cx, z = cz, ux = ux, uz = uz, wx = wx, wz = wz, hu = size.width * 0.5, hw = size.length * 0.5, m = 0.4 }
end

local function toBox(box, x, z)
    local dx, dz = x - box.x, z - box.z
    return dx * box.ux + dz * box.uz, dx * box.wx + dz * box.wz
end

local function clipSlab(p, d, h, t0, t1)
    if math.abs(d) < 1e-9 then
        if p < -h or p > h then
            return nil
        end
        return t0, t1
    end
    local ta, tb = (-h - p) / d, (h - p) / d
    if ta > tb then
        ta, tb = tb, ta
    end
    t0, t1 = math.max(t0, ta), math.min(t1, tb)
    if t0 > t1 then
        return nil
    end
    return t0, t1
end

-- Protíná úsečka obdélník zvětšený o m?
local function segmentHitsBox(x1, z1, x2, z2, box, m)
    local u1, w1 = toBox(box, x1, z1)
    local u2, w2 = toBox(box, x2, z2)
    local t0, t1 = clipSlab(u1, u2 - u1, box.hu + m, 0, 1)
    if t0 == nil then
        return false
    end
    t0 = clipSlab(w1, w2 - w1, box.hw + m, t0, t1)
    return t0 ~= nil
end

local function insideBox(box, x, z, m)
    local u, w = toBox(box, x, z)
    return math.abs(u) <= box.hu + m and math.abs(w) <= box.hw + m
end

-- Jak daleko od bodu ve směru (dx, dz) leží okraj obdélníku zvětšeného o m (hadice z portu vede nejdřív ven z karoserie).
local function exitDistance(box, x, z, dx, dz, m)
    local pu, pw = toBox(box, x, z)
    local du, dw = dx * box.ux + dz * box.uz, dx * box.wx + dz * box.wz
    local t = math.huge
    if math.abs(du) > 1e-6 then
        t = math.min(t, ((du > 0 and box.hu + m or -(box.hu + m)) - pu) / du)
    end
    if math.abs(dw) > 1e-6 then
        t = math.min(t, ((dw > 0 and box.hw + m or -(box.hw + m)) - pw) / dw)
    end
    return t == math.huge and 0 or math.max(t, 0)
end

-- Vozidla jako překážky; vlastní vozík a cíl (vlek se vstupem) se obcházejí těsně, ostatní s odstupem.
local function gatherBoxes(owner, target)
    local boxes, byVehicle = {}, {}
    local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
    for _, v in ipairs(vehicles) do
        if not v.isDeleted then
            local box = boxOf(v)
            if box ~= nil then
                if v == owner or v == target then
                    box.m, box.own = 0.08, true
                    byVehicle[v] = box
                end
                boxes[#boxes + 1] = box
            end
        end
    end
    return boxes, byVehicle
end

-- Nejkratší vodorovná cesta z a do b kolem obdélníků (graf viditelnosti přes rohy zvětšených obdélníků); vrací mezilehlé body.
local function routeAround(ax, az, bx, bz, boxes)
    local mx, mz = (ax + bx) * 0.5, (az + bz) * 0.5
    local reach = MathUtil.vector2Length(bx - ax, bz - az) * 0.5 + 2
    local active = {}
    for _, box in ipairs(boxes) do
        if MathUtil.vector2Length(box.x - mx, box.z - mz) <= reach + box.hu + box.hw
            and (box.own or not (insideBox(box, ax, az, box.m) or insideBox(box, bx, bz, box.m))) then
            active[#active + 1] = box
        end
    end
    local function blocked(x1, z1, x2, z2)
        for _, box in ipairs(active) do
            if segmentHitsBox(x1, z1, x2, z2, box, box.m - 0.02) then
                return true
            end
        end
        return false
    end
    if #active == 0 or not blocked(ax, az, bx, bz) then
        return {}
    end
    local nodes = { { ax, az }, { bx, bz } }
    for _, box in ipairs(active) do
        local mt = box.m + 0.3
        for _, su in ipairs({ -1, 1 }) do
            for _, sw in ipairs({ -1, 1 }) do
                local u, w = su * (box.hu + mt), sw * (box.hw + mt)
                local x, z = box.x + u * box.ux + w * box.wx, box.z + u * box.uz + w * box.wz
                local free = true
                for _, other in ipairs(active) do
                    if other ~= box and insideBox(other, x, z, other.m) then
                        free = false
                        break
                    end
                end
                if free then
                    nodes[#nodes + 1] = { x, z }
                end
            end
        end
    end
    local n = #nodes
    local dist, prev, done = {}, {}, {}
    for i = 1, n do
        dist[i] = math.huge
    end
    dist[1] = 0
    for _ = 1, n do
        local best, bi = math.huge, nil
        for i = 1, n do
            if not done[i] and dist[i] < best then
                best, bi = dist[i], i
            end
        end
        if bi == nil or bi == 2 then
            break
        end
        done[bi] = true
        for j = 1, n do
            if not done[j] then
                local a, b = nodes[bi], nodes[j]
                local d = MathUtil.vector2Length(b[1] - a[1], b[2] - a[2])
                if dist[bi] + d < dist[j] and not blocked(a[1], a[2], b[1], b[2]) then
                    dist[j], prev[j] = dist[bi] + d, bi
                end
            end
        end
    end
    if prev[2] == nil then
        return {}
    end
    local way = {}
    local i = prev[2]
    while i ~= nil and i ~= 1 do
        table.insert(way, 1, nodes[i])
        i = prev[i]
    end
    return way
end

-- Centripetální Catmull-Romova křivka přes body (rovina XZ), vzorkovaná hustě; prochází všemi body a nepřestřeluje u krátkých úseků.
local function smoothPath(pts)
    local n = #pts
    local function pt(k)
        if k < 1 then
            return { 2 * pts[1][1] - pts[2][1], 2 * pts[1][2] - pts[2][2] }
        elseif k > n then
            return { 2 * pts[n][1] - pts[n - 1][1], 2 * pts[n][2] - pts[n - 1][2] }
        end
        return pts[k]
    end
    local out = { pts[1] }
    for k = 1, n - 1 do
        local p0, p1, p2, p3 = pt(k - 1), pts[k], pts[k + 1], pt(k + 2)
        local function knot(a, b)
            return math.max(MathUtil.vector2Length(b[1] - a[1], b[2] - a[2]), 1e-3) ^ 0.5
        end
        local t0 = 0
        local t1 = t0 + knot(p0, p1)
        local t2 = t1 + knot(p1, p2)
        local t3 = t2 + knot(p2, p3)
        local len = MathUtil.vector2Length(p2[1] - p1[1], p2[2] - p1[2])
        local steps = math.max(math.ceil(len / 0.08), 2)
        for s = 1, steps do
            local t = t1 + (t2 - t1) * s / steps
            local function lerp2(a, b, ta, tb)
                local f = (t - ta) / (tb - ta)
                return { a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f }
            end
            local a1, a2, a3 = lerp2(p0, p1, t0, t1), lerp2(p1, p2, t1, t2), lerp2(p2, p3, t2, t3)
            local b1, b2 = lerp2(a1, a2, t0, t2), lerp2(a2, a3, t1, t3)
            out[#out + 1] = lerp2(b1, b2, t1, t2)
        end
    end
    return out
end

local function smoothstep(t)
    t = math.clamp(t, 0, 1)
    return t * t * (3 - 2 * t)
end

-- Hadice pevné délky od portu s (hs = vodorovný směr, kterým z něj vychází) ke koncovce e (ed = vodorovný směr, kterým z ní hadice
-- vychází; target = vlek se vstupem, nebo nil, když ji hráč nese). Vodorovně vede nejkratší cestou kolem vozidel (z karoserie nejdřív
-- rovně ven, pak hladká křivka). Svisle leží na podlaze (terén, statický objekt, silnice) a ke koncům stoupá plynulým obloukem; je-li
-- hadice napnutá (odvinutá délka nestačí), zvedá se k přímce mezi konci.
local function hoseCurve(spec, owner, target, hoseLength, s, hs, e, ed)
    local boxes, own = gatherBoxes(owner, target)
    local la, lb = SprayDroneHoseLib.HOSE_LEAD, target ~= nil and SprayDroneHoseLib.HOSE_LEAD or SprayDroneHoseLib.HOSE_HELD_LEAD
    local selfBox, targetBox = own[owner], target ~= nil and own[target] or nil
    if selfBox ~= nil then
        la = math.clamp(exitDistance(selfBox, s[1], s[3], hs[1], hs[2], selfBox.m) + 0.12, la, 1.4)
    end
    if targetBox ~= nil then
        lb = math.clamp(exitDistance(targetBox, e[1], e[3], ed[1], ed[2], targetBox.m) + 0.12, lb, 1.4)
    end
    local a2 = { s[1] + hs[1] * la, s[3] + hs[2] * la }
    local b2 = { e[1] + ed[1] * lb, e[3] + ed[2] * lb }
    local now = g_time or 0
    local cache = spec.route
    if cache == nil or math.abs(cache.ax - a2[1]) > 0.03 or math.abs(cache.az - a2[2]) > 0.03 or math.abs(cache.bx - b2[1]) > 0.03
        or math.abs(cache.bz - b2[2]) > 0.03 or now - cache.t > 800 then
        cache = { ax = a2[1], az = a2[2], bx = b2[1], bz = b2[2], t = now, way = routeAround(a2[1], a2[2], b2[1], b2[2], boxes) }
        spec.route = cache
    end
    local pts = { { s[1], s[3] }, a2 }
    for _, w in ipairs(cache.way) do
        pts[#pts + 1] = w
    end
    pts[#pts + 1] = b2
    pts[#pts + 1] = { e[1], e[3] }
    local dense = smoothPath(pts)

    local cum = { 0 }
    for k = 2, #dense do
        cum[k] = cum[k - 1] + MathUtil.vector2Length(dense[k][1] - dense[k - 1][1], dense[k][2] - dense[k - 1][2])
    end
    local length = cum[#dense]
    local count = math.clamp(math.floor(length / 0.12), 16, SprayDroneHoseLib.HOSE_SAMPLES)
    local xz = {}
    local index = 1
    for i = 0, count do
        local d = length * i / count
        while index < #dense - 1 and cum[index + 1] < d do
            index = index + 1
        end
        local a, b = dense[index], dense[index + 1]
        local span = cum[index + 1] - cum[index]
        local t = span > 1e-6 and math.clamp((d - cum[index]) / span, 0, 1) or 0
        xz[i + 1] = { a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t }
    end

    local clear = SprayDroneHoseLib.HOSE_RADIUS + 0.005
    local floor = {}
    for i = 1, count + 1 do
        floor[i] = floorAt(xz[i][1], xz[i][2]) + clear
    end
    local hA, hB = math.max(s[2] - floor[1], 0), math.max(e[2] - floor[count + 1], 0)
    -- u koncovek hadice nejdřív rovně ve výšce spojky (pod gumovou ochranou ohybu, ta je pevná), teprve potom klesá k podlaze
    local stiff = math.min(SprayDroneHoseLib.HOSE_STIFF, length * 0.2)
    local rA = math.min(math.clamp(hA * 1.1 + 0.25, 0.3, 1.8), length * 0.6 - stiff)
    local rB = math.min(math.clamp(hB * 1.1 + 0.25, 0.3, 1.8), length * 0.6 - stiff)
    local y = {}
    for i = 1, count + 1 do
        local d = length * (i - 1) / count
        local da, db = d - stiff, length - d - stiff
        local riseA = da >= rA and 0 or hA * (1 - smoothstep(da / rA))
        local riseB = db >= rB and 0 or hB * (1 - smoothstep(db / rB))
        y[i] = floor[i] + math.max(riseA, riseB)
    end
    y[1], y[count + 1] = s[2], e[2]
    local curve = {}
    for i = 1, count + 1 do
        curve[i] = { xz[i][1], y[i], xz[i][2] }
    end
    return curve
end

-- Rozmístí články po křivce; koncovka stojí v posledním bodě a míří směrem k hadici (edx..edz je směr od vstupu ven).
local function layoutChain(spec, curve, edx, edy, edz)
    local n = #spec.segments
    if n == 0 then
        return
    end
    local cum = { 0 }
    for k = 2, #curve do
        local a, b = curve[k - 1], curve[k]
        cum[k] = cum[k - 1] + MathUtil.vector3Length(b[1] - a[1], b[2] - a[2], b[3] - a[3])
    end
    local total = cum[#curve]
    local points = {}
    local index = 1
    for i = 0, n do
        local s = total * i / n
        while index < #curve - 1 and cum[index + 1] < s do
            index = index + 1
        end
        local a, b = curve[index], curve[index + 1]
        local len = cum[index + 1] - cum[index]
        local t = len > 1e-6 and math.clamp((s - cum[index]) / len, 0, 1) or 0
        points[i + 1] = { a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t }
    end
    local dirs = {}
    for k = 1, n do
        local a, b = points[k], points[k + 1]
        dirs[k] = { normalize(b[1] - a[1], b[2] - a[2], b[3] - a[3]) }
    end
    local radius = SprayDroneHoseLib.HOSE_RADIUS
    local joint = {}
    for k = 1, n - 1 do
        local d0, d1 = dirs[k], dirs[k + 1]
        local c = math.clamp(d0[1] * d1[1] + d0[2] * d1[2] + d0[3] * d1[3], -1, 1)
        joint[k] = radius * math.tan(math.acos(c) * 0.5)
    end
    for k, node in ipairs(spec.segments) do
        local a, b = points[k], points[k + 1]
        local length = MathUtil.vector3Length(b[1] - a[1], b[2] - a[2], b[3] - a[3])
        local back = math.min(joint[k - 1] or 0, length * 0.5)
        local overlap = back + math.min(joint[k] or 0, length * 0.5)
        local parent = getParent(node)
        local d0 = dirs[k]
        setTranslation(node, worldToLocal(parent, a[1] - d0[1] * back, a[2] - d0[2] * back, a[3] - d0[3] * back))
        if length > 1e-4 then
            local d = dirs[k]
            local dx, dy, dz = worldDirectionToLocal(parent, d[1], d[2], d[3])
            local ux, uy, uz
            if math.abs(d[2]) > 0.95 then
                ux, uy, uz = worldDirectionToLocal(parent, 1, 0, 0)
            else
                ux, uy, uz = worldDirectionToLocal(parent, 0, 1, 0)
            end
            setDirection(node, dx, dy, dz, ux, uy, uz)
        end
        local k = radius / SprayDroneHoseLib.HOSE_MESH_RADIUS
        setScale(node, k, k, math.max(length + overlap, 0.001))
    end
    if spec.hoseEnd ~= nil then
        local e = curve[#curve]
        local parent = getParent(spec.hoseEnd)
        setTranslation(spec.hoseEnd, worldToLocal(parent, e[1], e[2], e[3]))
        local ldx, ldy, ldz = worldDirectionToLocal(parent, edx, edy, edz)
        local ux, uy, uz = worldDirectionToLocal(parent, 0, 1, 0)
        if math.abs(edy) > 0.95 then
            ux, uy, uz = worldDirectionToLocal(parent, 1, 0, 0)
        end
        setDirection(spec.hoseEnd, ldx, ldy, ldz, ux, uy, uz)
    end
end

-- Poloha konce hadice v ruce hráče: kousek před kamerou ve směru pohledu (náklon myší zvedá a sklání konec), nejvýš do délky hadice
-- od portu a nad podlahou. Vrací i směr pohledu: koncovka míří tam a hadice za ní vede dozadu.
local function getHandPosition(spec, nozzle, hoseLength)
    local player = g_localPlayer
    if player == nil or player.getPosition == nil then
        return nil
    end
    local camera = getCamera()
    local ex, ey, ez = getWorldTranslation(camera)
    local dx, dy, dz = normalize(localDirectionToWorld(camera, 0, 0, -1))
    local x, y, z = ex + dx * 0.85, ey - 0.25 + dy * 0.85, ez + dz * 0.85
    y = math.max(y, floorAt(x, z) + 0.1)
    if nozzle ~= nil then
        local nx, ny, nz = getWorldTranslation(nozzle)
        local reach = hoseLength * SprayDroneHoseLib.HOSE_REACH
        local length = MathUtil.vector3Length(x - nx, y - ny, z - nz)
        if length > reach then
            local s = reach / length
            x, y, z = nx + (x - nx) * s, ny + (y - ny) * s, nz + (z - nz) * s
        end
    end
    return x, y, z, dx, dy, dz
end

SprayDroneHoseLib.bezier = bezier
SprayDroneHoseLib.normalize = normalize
SprayDroneHoseLib.terrainAt = terrainAt
SprayDroneHoseLib.floorAt = floorAt
SprayDroneHoseLib.boxOf = boxOf
SprayDroneHoseLib.hoseCurve = hoseCurve
SprayDroneHoseLib.layoutChain = layoutChain
SprayDroneHoseLib.getHandPosition = getHandPosition
