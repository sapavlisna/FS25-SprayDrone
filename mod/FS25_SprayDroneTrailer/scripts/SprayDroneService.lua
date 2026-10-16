-- Servisní část vleku k SprayDroneStation (docs/DRON.md): úchyty lyžin, modely baterií ve slotech, plnicí hadice
-- a přečerpávání (dron -> vlek, vlek -> IBC). Uzly se hledají přes i3dMapping; když chybí, vizuál se přeskočí.

local function getMappedNode(self, name)
    local mapping = self.i3dMappings ~= nil and self.i3dMappings[name] or nil
    if type(mapping) == "table" then
        return mapping.nodeId
    end
    return nil
end
SprayDroneStation.getMappedNode = getMappedNode

local function getVariantClamps(self, prefix)
    local clamps = {}
    for i = 1, SprayDroneStation.CLAMPS do
        local node = getMappedNode(self, prefix .. "Clamp_" .. i)
        if node ~= nil then
            table.insert(clamps, node)
        end
    end
    return clamps
end

-- Model baterie podle varianty: pod kořenem battery<i> jsou battery<i>S/M/L, ukáže se jen ten varianty.
local function applyBatteryMeshes(self, root, index, variant)
    for _, name in ipairs({ "S", "M", "L" }) do
        local meshName = "battery" .. index .. name
        local node = getMappedNode(self, meshName)
        if node == nil then
            local child = getChild(root, meshName)
            node = child ~= 0 and child or nil
        end
        if node ~= nil then
            setVisibility(node, name == variant)
        end
    end
end

function SprayDroneStation.loadServiceParts(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local default = SprayDroneStation.DEFAULT_DRONE
    spec.batteryNodes, spec.batterySlotDeck = {}, {}
    for i = 1, spec.numBatterySlots do
        spec.batteryNodes[i] = getMappedNode(self, "battery" .. i)
        spec.batterySlotDeck[i] = getMappedNode(self, "batterySlotDeck" .. i)
        if spec.batteryNodes[i] ~= nil then
            applyBatteryMeshes(self, spec.batteryNodes[i], i, spec.batteryVariant or default)
        end
    end
    spec.chargerLeds, spec.chargerLedShown = {}, {}
    for k = 1, spec.numBatterySlots do
        spec.chargerLeds[k], spec.chargerLedShown[k] = {}, {}
        for n = 1, SprayDroneStation.CHARGER_LED_BARS do
            spec.chargerLeds[k][n] = getMappedNode(self, string.format("Charger_Led_%d_%d", k, n - 1))
        end
    end
    spec.batteryParents, spec.batteryShown, spec.batteryMoves = {}, {}, {}
    SprayDroneStation.loadDroneService(self, xml, key)

    spec.drainRate = math.max(xml:getValue(key .. ".transfer#drainRate", 1), 0.01)
    spec.palletRate = math.max(xml:getValue(key .. ".transfer#palletRate", 1.5), 0.01)
    spec.palletDistance = xml:getValue(key .. ".transfer#palletDistance", 6)
    spec.transferMode = SprayDroneStation.TRANSFER_NONE
    spec.transferPallet, spec.transferPalletUnit, spec.palletSearchTime = nil, nil, nil
    spec.transferSyncTimer = 0
end

-- Úchyty lyžin, uzel pro baterii v dronu a plnicí hadice jednoho dronu (spec dronu v kontextu). Hadice mají uzly s prefixem
-- z drone(?)#hosePrefix (fillHose..., u druhého dronu fillHoseB...).
function SprayDroneStation.loadDroneService(self, xml, key)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local prefix = spec.dronePrefix
    local isFirst = SprayDroneDrones.getIndex(self) == 1
    spec.clamps = {}
    if spec.hasDrone then
        spec.clamps = getVariantClamps(self, prefix)
    end
    -- úchyty ostatních variant (a u vleku bez dronu všechny) zůstanou skryté
    local others = {}
    for _, v in ipairs(spec.variants or {}) do
        if isFirst then
            table.insert(others, v)
        end
    end
    if not isFirst then
        for _, v in pairs(spec.secondVariants or {}) do
            table.insert(others, v)
        end
    end
    for _, v in ipairs(others) do
        if v.prefix ~= prefix or not spec.hasDrone then
            for _, node in ipairs(getVariantClamps(self, v.prefix)) do
                setVisibility(node, false)
            end
        end
    end
    spec.batterySlotDrone = nil
    if spec.hasDrone then
        spec.batterySlotDrone = getMappedNode(self, prefix .. "BatterySlot")
    end

    local tag = spec.droneKey ~= nil and xml:getValue(spec.droneKey .. "#hosePrefix") or "fillHose"
    local start, nozzle, park = getMappedNode(self, tag .. "Start"), getMappedNode(self, tag .. "Nozzle"), getMappedNode(self, tag .. "ParkPos")
    local segments, lay = {}, {}
    for i = 1, SprayDroneStation.HOSE_SEGMENTS do
        table.insert(segments, getMappedNode(self, tag .. "Seg" .. i))
    end
    for i = 1, SprayDroneStation.HOSE_LAY_POINTS do
        table.insert(lay, getMappedNode(self, tag .. "Lay" .. i))
    end
    spec.hose = nil
    if start ~= nil and nozzle ~= nil and park ~= nil and #segments >= 2 then
        spec.hose = { start = start, segments = segments, lay = lay, nozzle = nozzle, park = park, coil = getMappedNode(self, tag .. "Coil"),
            port = spec.hasDrone and getMappedNode(self, prefix .. "FillPort") or nil, appliedKey = nil, shown = nil }
        -- bod na přední hraně trupu mezi předními rameny: hadice přes něj přechází nahoru k hrdlu, ne skrz dron
        local tilt, vx, vy, vz = nil, nil, nil, nil
        if spec.hose.port ~= nil then
            tilt = getMappedNode(self, prefix .. "Tilt")
            vx, vy, vz = xml:getValue(spec.droneKey .. "#hoseVia")
        end
        if tilt ~= nil and vx ~= nil then
            local sx = worldToLocal(tilt, getWorldTranslation(start))
            spec.hose.via = createTransformGroup("sdtHoseVia")
            link(tilt, spec.hose.via)
            setTranslation(spec.hose.via, sx < 0 and -math.abs(vx) or math.abs(vx), vy, vz)
        end
    end
    spec.hoseT = 0
end

-- Kontrolky šachet nabíječky: svítí jen šachta s vloženou (dosedlou) baterií, počet čárek odpovídá nabití (po 1/CHARGER_LED_BARS, aspoň
-- jedna), nejvyšší čárka bliká, dokud se baterie nabíjí.
function SprayDroneStation.updateChargerLeds(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local bars = SprayDroneStation.CHARGER_LED_BARS
    local lit, blinking = {}, {}
    for k, battery in pairs(spec.batteries) do
        local parent = spec.batteryParents[k]
        if parent ~= nil and spec.batteryShown[k] and spec.batteryMoves[k] == nil then
            for slot = 1, spec.numBatterySlots do
                if spec.batterySlotDeck[slot] == parent then
                    local level = math.clamp(battery.charge / spec.batteryCapacity, 0, 1)
                    lit[slot] = math.max(math.ceil(level * bars - 0.001), 1)
                    blinking[slot] = spec.generatorRunning and battery.slot > 0 and battery.charge < spec.batteryCapacity
                end
            end
        end
    end
    local blinkOn = math.floor(g_time / 500) % 2 == 0
    for slot = 1, spec.numBatterySlots do
        for n = 1, bars do
            local node = spec.chargerLeds[slot][n]
            if node ~= nil then
                local show = lit[slot] ~= nil and (n < lit[slot] or (n == lit[slot] and (not blinking[slot] or blinkOn)))
                if show ~= spec.chargerLedShown[slot][n] then
                    spec.chargerLedShown[slot][n] = show
                    setVisibility(node, show)
                end
            end
        end
    end
end

-- Úchyty jen se složeným dronem, baterie ve svých slotech (nabíječka v truhle, v dronu), hadice jen na rozloženém vleku;
-- koncovka jede k hrdlu dronu, dokud je dron v servisu nebo se vypouští.
-- Všechno plyne ze synchronizovaného stavu, takže server i klienti kreslí totéž.
function SprayDroneStation.updateServiceVisuals(self, dt)
    SprayDroneStation.updateBatteryVisuals(self, dt)
    SprayDroneDrones.forEach(self, SprayDroneStation.updateDroneServiceVisuals, dt)
end

-- Je node uzel pro baterii v dronu některého z dronů?
function SprayDroneStation.isDroneBatterySlot(self, node)
    if node == nil then
        return false
    end
    local root = SprayDroneDrones.getRoot(self)
    for k = 1, root.numDrones do
        if root.drones[k].batterySlotDrone == node then
            return true
        end
    end
    return false
end

-- Úchyty lyžin dronu a jeho hadice (v kontextu dronu).
function SprayDroneStation.updateDroneServiceVisuals(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local clampsVisible = spec.unfold <= 0
    if clampsVisible ~= spec.clampsVisible then
        spec.clampsVisible = clampsVisible
        for _, node in pairs(spec.clamps) do
            setVisibility(node, clampsVisible)
        end
    end

    local hose = spec.hose
    if hose == nil then
        return
    end
    local shown = spec.unfold > 0
    local connect = shown and hose.port ~= nil and spec.isLinked and spec.unfold >= 1
        and (spec.state == SprayDroneStation.STATE_SERVICING
            or (spec.transferMode == SprayDroneStation.TRANSFER_DRAIN_DRONE and (spec.transferDrone or 1) == SprayDroneDrones.getIndex(self)))
    spec.hoseConnect = connect == true
    local step = dt * 0.001 / SprayDroneStation.HOSE_TIME
    if not spec.isLinked then
        spec.hoseT = 0
    elseif connect then
        spec.hoseT = math.min(spec.hoseT + step, 1)
    else
        spec.hoseT = math.max(spec.hoseT - step, 0)
    end
    -- složený vlek: hadice namotaná na navíječi; rozložený: odvinutá (články a koncovka)
    if shown ~= hose.shown then
        hose.shown = shown
        if hose.coil ~= nil then
            setVisibility(hose.coil, not shown)
        end
        setVisibility(hose.nozzle, shown)
        for _, node in ipairs(hose.segments) do
            setVisibility(node, shown)
        end
        hose.appliedKey = nil
    end
    if not shown then
        return
    end
    -- přepočet jen, když se hýbe koncovka, vlek (skládání) nebo dron (rozkládání)
    local foldTime = self.getFoldAnimTime ~= nil and self:getFoldAnimTime() or 0
    local key = hose.appliedKey
    if key ~= nil and key[1] == spec.hoseT and key[2] == foldTime and key[3] == spec.unfold then
        return
    end
    hose.appliedKey = { spec.hoseT, foldTime, spec.unfold }
    -- koncovka: poloha i natočení z parku k hrdlu (obojí má +z špičkou ven / do hrdla); nejdřív nahoru nad listy,
    -- pak nad hrdlo a do něj shora po jeho ose
    local x, y, z = getWorldTranslation(hose.park)
    local dx1, dy1, dz1 = localDirectionToWorld(hose.park, 0, 0, 1)
    local ux1, uy1, uz1 = localDirectionToWorld(hose.park, 0, 1, 0)
    if hose.port ~= nil and spec.hoseT > 0 then
        local t = spec.hoseT * spec.hoseT * (3 - 2 * spec.hoseT)
        local px, py, pz = getWorldTranslation(hose.port)
        local dx2, dy2, dz2 = localDirectionToWorld(hose.port, 0, 0, 1)
        local lift, approach = SprayDroneStation.HOSE_LIFT, SprayDroneStation.HOSE_PORT_APPROACH
        local u = 1 - t
        local c0, c1, c2, c3 = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
        x = c0 * x + c1 * x + c2 * (px - dx2 * approach) + c3 * px
        y = c0 * y + c1 * (y + lift) + c2 * (py - dy2 * approach) + c3 * py
        z = c0 * z + c1 * z + c2 * (pz - dz2 * approach) + c3 * pz
        local ux2, uy2, uz2 = localDirectionToWorld(hose.port, 0, 1, 0)
        dx1, dy1, dz1 = MathUtil.vector3Normalize(dx1 + (dx2 - dx1) * t, dy1 + (dy2 - dy1) * t, dz1 + (dz2 - dz1) * t)
        ux1, uy1, uz1 = MathUtil.vector3Normalize(ux1 + (ux2 - ux1) * t, uy1 + (uy2 - uy1) * t, uz1 + (uz2 - uz1) * t)
    end
    setWorldTranslation(hose.nozzle, x, y, z)
    local nozzleParent = getParent(hose.nozzle)
    local ndx, ndy, ndz = worldDirectionToLocal(nozzleParent, dx1, dy1, dz1)
    local nux, nuy, nuz = worldDirectionToLocal(nozzleParent, ux1, uy1, uz1)
    setDirection(hose.nozzle, ndx, ndy, ndz, nux, nuy, nuz)
    SprayDroneStation.layoutHose(hose, spec.hoseT)
end

-- Baterie ve slotech nabíječky nebo v dronech a kontrolky nabíječky (vozidlo).
function SprayDroneStation.updateBatteryVisuals(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    -- baterie jsou pořád v nabíječce v truhle; baterie z dronu se při skládání vleku přenese do volného místa nabíječky
    -- dřív, než se zavře víko (víko se zavírá od 1,8 s animace (60 %)), a při rozkládání se po otevření víka vrátí do dronu
    local foldProgress = self.getFoldAnimTime ~= nil and self:getFoldAnimTime() or 0
    local last = spec.lastFoldProgress
    if last == nil then
        spec.batteryStowed = foldProgress > 0.5
    elseif foldProgress > last then
        spec.batteryStowed = foldProgress > spec.batteryStowFrom
    elseif foldProgress < last then
        spec.batteryStowed = foldProgress > spec.batteryStowUntil
    end
    spec.lastFoldProgress = foldProgress
    local occupied = {}
    for _, battery in pairs(spec.batteries) do
        if battery.slot ~= 0 then
            occupied[battery.slot] = true
        end
    end
    -- při skládání vleku každá baterie z dronů dostane další volný slot (jinak by se dvě posadily do téhož)
    local nextFree = 1
    local function takeFreeSlot()
        while occupied[nextFree] and nextFree < spec.numBatterySlots do
            nextFree = nextFree + 1
        end
        local slot = nextFree
        occupied[slot] = true
        return slot
    end
    local root = SprayDroneDrones.getRoot(self)
    for k = 1, spec.numBatterySlots do
        local node = spec.batteryNodes[k]
        if node ~= nil then
            local battery = spec.batteries[k]
            local parent = nil
            if battery ~= nil then
                if battery.slot ~= 0 then
                    parent = spec.batterySlotDeck[battery.slot]
                elseif spec.batteryStowed then
                    parent = spec.batterySlotDeck[takeFreeSlot()]
                else
                    local owner = root.drones[battery.drone or 1] or root
                    parent = owner.batterySlotDrone
                end
            end
            local old = spec.batteryParents[k]
            if parent ~= nil and parent ~= old then
                spec.batteryParents[k] = parent
                local moving = old ~= nil and (SprayDroneStation.isDroneBatterySlot(self, parent) or SprayDroneStation.isDroneBatterySlot(self, old))
                    and spec.batteryShown[k] and not (VehiclePropertyState ~= nil and self.propertyState == VehiclePropertyState.SHOP_CONFIG)
                if moving then
                    SprayDroneStation.startBatteryMove(self, k, node, parent)
                else
                    spec.batteryMoves[k] = nil
                    link(parent, node)
                    setTranslation(node, 0, 0, 0)
                    setRotation(node, 0, 0, 0)
                end
            end
            if spec.batteryMoves[k] ~= nil then
                SprayDroneStation.updateBatteryMove(self, k, node, dt)
            end
            local shown = parent ~= nil
            if shown ~= spec.batteryShown[k] then
                spec.batteryShown[k] = shown
                setVisibility(node, shown)
            end
        end
    end

    SprayDroneStation.updateChargerLeds(self)
end

---------------------------------------------------------------------------------------------------
-- přenos baterie mezi dronem a nabíječkou: baterie se hned přepojí pod nový slot, ale poloha a natočení se
-- vedou z místa, kde byla (v rámci vleku), obloukem nahoru a do slotu shora. Nabitá čeká, než vybitá dojede.

local function smooth(t)
    return t * t * (3 - 2 * t)
end

local function mixDirection(a, b, t)
    local x, y, z = a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t
    local length = MathUtil.vector3Length(x, y, z)
    if length < 1e-3 then
        return b[1], b[2], b[3]
    end
    return x / length, y / length, z / length
end

function SprayDroneStation.startBatteryMove(self, k, node, parent)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local root = self.rootNode
    local toDrone = SprayDroneStation.isDroneBatterySlot(self, parent)
    local delay = 0
    if toDrone then
        local total = SprayDroneStation.BATTERY_MOVE_TIME
        for j, battery in pairs(spec.batteries) do
            local move = spec.batteryMoves[j]
            if j ~= k and move ~= nil and not move.toDrone then
                delay = math.max(delay, move.delay + total - move.time)
            elseif j ~= k and move == nil and battery.slot ~= 0 and SprayDroneStation.isDroneBatterySlot(self, spec.batteryParents[j]) then
                delay = math.max(delay, total)
            end
        end
    end
    spec.batteryMoves[k] = {
        from = { worldToLocal(root, getWorldTranslation(node)) },
        dir = { worldDirectionToLocal(root, localDirectionToWorld(node, 0, 0, 1)) },
        up = { worldDirectionToLocal(root, localDirectionToWorld(node, 0, 1, 0)) },
        time = 0, delay = delay, toDrone = toDrone }
    link(parent, node)
    SprayDroneStation.updateBatteryMove(self, k, node, 0)
end

function SprayDroneStation.updateBatteryMove(self, k, node, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local move = spec.batteryMoves[k]
    move.time = move.time + dt * 0.001
    local s = math.clamp((move.time - move.delay) / SprayDroneStation.BATTERY_MOVE_TIME, 0, 1)
    if s >= 1 then
        spec.batteryMoves[k] = nil
        setTranslation(node, 0, 0, 0)
        setRotation(node, 0, 0, 0)
        return
    end
    self:raiseActive()
    local root, parent = self.rootNode, getParent(node)
    local a = move.from
    local e = { worldToLocal(root, getWorldTranslation(parent)) }
    local lift = SprayDroneStation.BATTERY_MOVE_LIFT
    local t = smooth(s)
    local u = 1 - t
    local c0, c1, c2, c3 = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
    local x = (c0 + c1) * a[1] + (c2 + c3) * e[1]
    local y = (c0 + c1) * a[2] + (c2 + c3) * e[2] + (c1 + c2) * lift
    local z = (c0 + c1) * a[3] + (c2 + c3) * e[3]
    setWorldTranslation(node, localToWorld(root, x, y, z))
    -- natáčí se až venku ze slotu
    local r = smooth(math.clamp((s - 0.2) / 0.6, 0, 1))
    local dx, dy, dz = mixDirection(move.dir, { worldDirectionToLocal(root, localDirectionToWorld(parent, 0, 0, 1)) }, r)
    local ux, uy, uz = mixDirection(move.up, { worldDirectionToLocal(root, localDirectionToWorld(parent, 0, 1, 0)) }, r)
    dx, dy, dz = worldDirectionToLocal(parent, localDirectionToWorld(root, dx, dy, dz))
    ux, uy, uz = worldDirectionToLocal(parent, localDirectionToWorld(root, ux, uy, uz))
    setDirection(node, dx, dy, dz, ux, uy, uz)
end

---------------------------------------------------------------------------------------------------
-- hadice jako řetěz článků (body jsou tabulky {x, y, z} ve světě)

local function sub(a, b)
    return { a[1] - b[1], a[2] - b[2], a[3] - b[3] }
end

local function dist(a, b)
    return MathUtil.vector3Length(a[1] - b[1], a[2] - b[2], a[3] - b[3])
end

local function lerp(a, b, t)
    return { a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t }
end

local function direction(a, b)
    local d = sub(b, a)
    local length = MathUtil.vector3Length(d[1], d[2], d[3])
    if length < 1e-6 then
        return { 0, 0, 1 }
    end
    return { d[1] / length, d[2] / length, d[3] / length }
end

local function makeLine(points)
    local cum = { 0 }
    for i = 2, #points do
        cum[i] = cum[i - 1] + dist(points[i - 1], points[i])
    end
    return { points = points, cum = cum, length = cum[#points] }
end

-- Bod a směr v délce s od začátku lomené čáry.
local function pointAt(line, s)
    local points, cum = line.points, line.cum
    for i = 2, #points do
        if s <= cum[i] or i == #points then
            local length = cum[i] - cum[i - 1]
            local t = length > 1e-6 and math.clamp((s - cum[i - 1]) / length, 0, 1) or 0
            return lerp(points[i - 1], points[i], t), direction(points[i - 1], points[i]), i
        end
    end
    return points[1], { 0, 0, 1 }, 2
end

-- n + 1 bodů po stejných délkách.
local function resample(line, n)
    local result = {}
    for k = 0, n do
        result[k + 1] = (pointAt(line, line.length * k / n))
    end
    return result
end

-- Hladká křivka (Catmull-Rom) přes body a po 'step' vzorkovaná. Poslední dva body (začátek rovného úseku a konec hadice)
-- mají tečnu endDir; v lokálním minimu výšky (y) je tečna vodorovná, aby hadice neprošla deskou.
local function smoothCurve(points, endDir, step)
    local n = #points
    local tangents = {}
    for i = 1, n do
        local a, b = points[math.max(i - 1, 1)], points[math.min(i + 1, n)]
        local k = (i > 1 and i < n) and 0.5 or 1
        tangents[i] = { (b[1] - a[1]) * k, (b[2] - a[2]) * k, (b[3] - a[3]) * k }
    end
    for i = 2, n - 1 do
        if points[i][2] <= points[i - 1][2] + 1e-4 and points[i][2] <= points[i + 1][2] + 1e-4 then
            local t = tangents[i]
            local m = MathUtil.vector3Length(t[1], t[2], t[3])
            local h = MathUtil.vector3Length(t[1], 0, t[3])
            if h > 1e-6 then
                tangents[i] = { t[1] / h * m, 0, t[3] / h * m }
            end
        end
    end
    for i = math.max(n - 1, 1), n do
        local m = MathUtil.vector3Length(tangents[i][1], tangents[i][2], tangents[i][3])
        tangents[i] = { endDir[1] * m, endDir[2] * m, endDir[3] * m }
    end
    local curve = { points[1] }
    for i = 1, n - 1 do
        local p0, p1, m0, m1 = points[i], points[i + 1], tangents[i], tangents[i + 1]
        local steps = math.max(4, math.ceil(dist(p0, p1) / step))
        for k = 1, steps do
            local s = k / steps
            local h00, h10, h01, h11 = 2 * s ^ 3 - 3 * s ^ 2 + 1, s ^ 3 - 2 * s ^ 2 + s, -2 * s ^ 3 + 3 * s ^ 2, s ^ 3 - s ^ 2
            table.insert(curve, { h00 * p0[1] + h10 * m0[1] + h01 * p1[1] + h11 * m1[1], h00 * p0[2] + h10 * m0[2] + h01 * p1[2] + h11 * m1[2],
                h00 * p0[3] + h10 * m0[3] + h01 * p1[3] + h11 * m1[3] })
        end
    end
    return curve
end

-- Konec hadice v přívodu koncovky node (back = o kolik dál proti směru vstupu) a směr, kterým do něj hadice vchází (svět).
local function getInlet(node, back)
    local p, d = SprayDroneStation.HOSE_INLET_POS, SprayDroneStation.HOSE_INLET_DIR
    return { localToWorld(node, p[1] - d[1] * back, p[2] - d[2] * back, p[3] - d[3] * back) },
        { localDirectionToWorld(node, d[1], d[2], d[3]) }
end

-- Klidová hadice: fillHoseStart -> fillHoseLay* -> přívod koncovky v parku, hladká křivka (počítá se v souřadnicích
-- rodiče koncovky, ať se šikmý vlek nepočítá jako nakloněná deska). Body položené hadice, které by ležely uvnitř
-- koncovky (u špičky) nebo těsně před jejím rovným nájezdem, se vynechají; posledních HOSE_NOZZLE_LEAD m je rovně v ose přívodu.
local function getRestLine(hose)
    local lead = SprayDroneStation.HOSE_NOZZLE_LEAD
    local frame = getParent(hose.park)
    local parkTip = { worldToLocal(frame, getWorldTranslation(hose.park)) }
    local leadStart = { worldToLocal(frame, unpack((getInlet(hose.park, lead)))) }
    local points = { { worldToLocal(frame, getWorldTranslation(hose.start)) } }
    local lay = {}
    for _, node in ipairs(hose.lay) do
        table.insert(lay, { worldToLocal(frame, getWorldTranslation(node)) })
    end
    while #lay > 0 and (dist(lay[#lay], parkTip) < 0.3 or dist(lay[#lay], leadStart) < 0.12) do
        table.remove(lay)
    end
    for _, p in ipairs(lay) do
        table.insert(points, p)
    end
    table.insert(points, leadStart)
    local parkEnd, parkAxis = getInlet(hose.park, 0)
    table.insert(points, { worldToLocal(frame, unpack(parkEnd)) })
    local axis = { worldDirectionToLocal(frame, unpack(parkAxis)) }
    local world = {}
    for i, p in ipairs(smoothCurve(points, axis, SprayDroneStation.HOSE_REST_STEP)) do
        world[i] = { localToWorld(frame, p[1], p[2], p[3]) }
    end
    local line = makeLine(world)
    -- délka pevného úseku: k bodu křivky nejblíž fillHoseLay<HOSE_FIXED_LAY>
    line.fixed = 0
    local anchor = hose.lay[SprayDroneStation.HOSE_FIXED_LAY]
    if anchor ~= nil then
        local a, best = { getWorldTranslation(anchor) }, math.huge
        for i, p in ipairs(world) do
            local d = dist(p, a)
            if d < best then
                best, line.fixed = d, line.cum[i]
            end
        end
    end
    return line
end

SprayDroneStation.getHoseRestLine = getRestLine

-- Hadice pevné délky rest.length s koncem v bodě e (vchází do něj po směru ez): od začátku leží po klidové čáře
-- a od bodu q v délce s visí k e jako Bézierova křivka prověšená o HOSE_SAG rozpětí (nejníž do výšky nižšího
-- z konců, aby nešla deskou). s se hledá půlením, aby volná část měla právě zbývající délku; když hadice nestačí,
-- natáhne se (s = 0).
local function bezier(curve, p0, p1, p2, p3, steps)
    for k = 0, steps do
        local t = k / steps
        local u = 1 - t
        local c0, c1, c2, c3 = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
        table.insert(curve, { c0 * p0[1] + c1 * p1[1] + c2 * p2[1] + c3 * p3[1], c0 * p0[2] + c1 * p1[2] + c2 * p2[2] + c3 * p3[2],
            c0 * p0[3] + c1 * p1[3] + c2 * p2[3] + c3 * p3[3] })
    end
end

-- Pro dron na plošině vede volná část přes via (hrana trupu): q -> via prověšená, via -> e oblouk nad trupem do koncovky
-- shora. w (0..1) plynule zapíná přechod přes via; při w = 0 je via = e a tvar je stejný jako bez něj.
local function getHangingLine(rest, e, ez, via, w)
    local steps = SprayDroneStation.HOSE_CURVE_STEPS
    local lead = SprayDroneStation.HOSE_NOZZLE_LEAD
    local tip = e
    e = { e[1] - ez[1] * lead, e[2] - ez[2] * lead, e[3] - ez[3] * lead }
    local free = rest.length - lead
    w = via ~= nil and w or 0
    local v, tv = e, ez
    if w > 0 then
        v = lerp(e, via, w)
        local h = direction({ v[1], 0, v[3] }, { e[1], 0, e[3] })
        tv = { mixDirection(ez, { h[1] * 0.8, 0.6, h[3] * 0.8 }, w) }
    end
    local function build(s)
        local q, _, index = pointAt(rest, s)
        -- směr v q vyhlazený přes okolí, aby se křivka při posunu q přes lom čáry neskokově nezměnila
        local tq = direction((pointAt(rest, math.max(s - 0.15, 0))), (pointAt(rest, math.min(s + 0.15, rest.length))))
        local span = dist(q, v)
        local toEnd = direction(q, v)
        local a = span / 3 * math.max(tq[1] * toEnd[1] + tq[2] * toEnd[2] + tq[3] * toEnd[3], 0.2)
        local b = span / 3
        local low = math.min(q[2], v[2])
        local sag = math.min(span * SprayDroneStation.HOSE_SAG, SprayDroneStation.HOSE_MAX_SAG)
        local p1 = { q[1] + tq[1] * a, math.max(q[2] + tq[2] * a - sag, low), q[3] + tq[3] * a }
        local p2 = { v[1] - tv[1] * b, math.max(v[2] - tv[2] * b - sag, low), v[3] - tv[3] * b }
        local curve = {}
        bezier(curve, q, p1, p2, v, steps)
        if w > 0 then
            table.remove(curve)
            local c1 = { v[1] + tv[1] * 0.12 * w, v[2] + tv[2] * 0.12 * w, v[3] + tv[3] * 0.12 * w }
            local c2 = { e[1] - ez[1] * 0.15 * w, e[2] - ez[2] * 0.15 * w, e[3] - ez[3] * 0.15 * w }
            bezier(curve, v, c1, c2, e, math.ceil(steps / 2))
        end
        local length = 0
        for k = 2, #curve do
            length = length + dist(curve[k - 1], curve[k])
        end
        return curve, length, index
    end
    -- volná část začíná nejdřív na konci pevného úseku (ohyb z vodítka na desku zůstává na místě)
    local fixed = math.min(rest.fixed or 0, free)
    local s = fixed
    local _, length0 = build(fixed)
    if length0 < free - fixed then
        local lo, hi = fixed, free
        for _ = 1, 20 do
            local mid = (lo + hi) * 0.5
            local _, length = build(mid)
            if free - mid > length then
                lo = mid
            else
                hi = mid
            end
        end
        s = lo
    end
    local curve, _, index = build(s)
    local points = {}
    for i = 1, index - 1 do
        if rest.cum[i] < s - 1e-4 then
            table.insert(points, rest.points[i])
        end
    end
    for _, p in ipairs(curve) do
        table.insert(points, p)
    end
    table.insert(points, tip)
    return makeLine(points)
end

-- Rozmístí články po hadici: v klidu po klidové čáře, při připojování plynule do prověšené křivky ke koncovce.
-- Klidový tvar se vůči křivce s koncem v parku přičítá jako posun, který s hoseT mizí, takže konec vždy sedí v koncovce.
function SprayDroneStation.layoutHose(hose, hoseT)
    local n = #hose.segments
    local rest = getRestLine(hose)
    local points = resample(rest, n)
    if hoseT > 0 then
        local e, ez = getInlet(hose.nozzle, 0)
        local w = hoseT * hoseT * (3 - 2 * hoseT)
        local via = hose.via ~= nil and { getWorldTranslation(hose.via) } or nil
        local hanging = resample(getHangingLine(rest, e, ez, via, w), n)
        if w < 1 then
            local parkEnd, parkDir = getInlet(hose.park, 0)
            local base = resample(getHangingLine(rest, parkEnd, parkDir), n)
            for i = 1, n + 1 do
                local r, c = points[i], base[i]
                hanging[i] = { hanging[i][1] + (r[1] - c[1]) * (1 - w), hanging[i][2] + (r[2] - c[2]) * (1 - w),
                    hanging[i][3] + (r[3] - c[3]) * (1 - w) }
            end
        end
        points = hanging
    end
    local dirs = {}
    for k = 1, n do
        dirs[k] = direction(points[k], points[k + 1])
    end
    local radius = SprayDroneStation.HOSE_RADIUS
    for k, node in ipairs(hose.segments) do
        local p0, p1 = points[k], points[k + 1]
        local parent = getParent(node)
        local d = sub(p1, p0)
        local length = MathUtil.vector3Length(d[1], d[2], d[3])
        -- článek přesahuje o radius * tan(ohyb / 2), ať v ohybu nezůstane mezera
        local overlap = 0
        if k < n then
            local c = math.clamp(dirs[k][1] * dirs[k + 1][1] + dirs[k][2] * dirs[k + 1][2] + dirs[k][3] * dirs[k + 1][3], -1, 1)
            overlap = math.min(radius * math.tan(math.acos(c) * 0.5), length * 0.5)
        end
        setTranslation(node, worldToLocal(parent, p0[1], p0[2], p0[3]))
        if length > 1e-4 then
            local dx, dy, dz = worldDirectionToLocal(parent, d[1] / length, d[2] / length, d[3] / length)
            local ux, uy, uz
            if math.abs(d[2] / length) > 0.95 then
                ux, uy, uz = worldDirectionToLocal(parent, 1, 0, 0)
            else
                ux, uy, uz = worldDirectionToLocal(parent, 0, 1, 0)
            end
            setDirection(node, dx, dy, dz, ux, uy, uz)
        end
        setScale(node, 1, 1, math.max(length + overlap, 0.001))
    end
end

-- Vypustit dron do vleku (dron na plošině, vlek přijme jeho přípravek) nebo přečerpat nádrž vleku do IBC poblíž.
-- mode = TRANSFER_*; stejný mód znovu nebo TRANSFER_STOP zastaví. Jde eventem na server, ten přečerpává.
function SprayDroneStation:setSprayDroneTransfer(mode, noEventSend, droneIndex)
    if SprayDroneServiceEvent.sendEvent(self, mode, noEventSend, droneIndex) then
        return
    end
    local spec = SprayDroneDrones.getRoot(self)
    self:raiseActive()
    local k = droneIndex
    if k == nil or k < 1 or k > spec.numDrones then
        k = mode == SprayDroneStation.TRANSFER_DRAIN_DRONE and SprayDroneStation.pickDrainDrone(self) or nil
    end
    k = k or spec.transferDrone or 1
    -- přečerpávání je čerpadlo: bez proudu z centrály se nespustí (a běžící se zastaví v updateTransferDrone)
    local can = mode == SprayDroneStation.TRANSFER_NONE
        or (SprayDroneStation.getHasPower(self) and SprayDroneDrones.runAs(self, k, SprayDroneStation.getCanTransfer, mode))
    if mode == SprayDroneStation.TRANSFER_STOP or mode == spec.transferMode or (mode ~= SprayDroneStation.TRANSFER_NONE and not can) then
        mode = SprayDroneStation.TRANSFER_NONE
    end
    if mode ~= spec.transferMode then
        spec.transferMode = mode
        if mode == SprayDroneStation.TRANSFER_DRAIN_DRONE then
            spec.transferDrone = k
        end
        spec.palletSearchTime = nil
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

-- Který dron se může vypustit (s větší náplní napřed); nil, když žádný.
function SprayDroneStation.pickDrainDrone(self)
    local root = SprayDroneDrones.getRoot(self)
    local best, level = nil, -1
    for k = 1, root.numDrones do
        local d = root.drones[k]
        if d.droneFillLevel > level and SprayDroneDrones.runAs(self, k, SprayDroneStation.getCanTransfer, SprayDroneStation.TRANSFER_DRAIN_DRONE) then
            best, level = k, d.droneFillLevel
        end
    end
    return best
end

-- Přijme hlavní nádrž vleku přípravek z dronu? Jen prázdná, nebo s týmž přípravkem (voda pro míchání ani jiný přípravek
-- se nepřepisuje, i kdyby jí vanilla při nízké hladině druh změnila).
function SprayDroneStation.getCanAcceptDrained(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    return self:getFillUnitSupportsFillType(spec.fillUnitIndex, spec.droneFillType) and SprayDroneMixer.canAcceptDrained(
        self:getFillUnitFillType(spec.fillUnitIndex), self:getFillUnitFillLevel(spec.fillUnitIndex), spec.droneFillType)
end

function SprayDroneStation.getCanTransfer(self, mode)
    local spec = self[SprayDroneStation.SPEC_NAME]
    if mode == SprayDroneStation.TRANSFER_DRAIN_DRONE then
        return spec.isLinked and spec.state == SprayDroneStation.STATE_PARKED and not spec.missionActive and spec.unfold >= 1
            and spec.droneFillLevel > 0.001 and spec.droneFillType ~= FillType.UNKNOWN
            and SprayDroneStation.getCanAcceptDrained(self)
            and self:getFillUnitFreeCapacity(spec.fillUnitIndex) > 0.001
    elseif mode == SprayDroneStation.TRANSFER_TO_PALLET then
        return self:getFillUnitFillLevel(spec.fillUnitIndex) > 0.001 and SprayDroneStation.getTransferPallet(self) ~= nil
    end
    return false
end

-- IBC / paleta s kapalinou do palletDistance od vleku, která přijme přípravek z vleku (celé hledání nejvýš jednou za
-- PALLET_SEARCH_TIME). Vrací vozidlo a číslo jeho nádrže.
function SprayDroneStation.getTransferPallet(self)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local fillType = self:getFillUnitFillType(spec.fillUnitIndex)
    local pallet, unit = spec.transferPallet, spec.transferPalletUnit
    local function isValid(v, i)
        if v == nil or v.isDeleted or v.rootNode == nil or not entityExists(v.rootNode) or fillType == FillType.UNKNOWN then
            return false
        end
        if not v:getFillUnitAllowsFillType(i, fillType) or v:getFillUnitFreeCapacity(i) <= 0.001 then
            return false
        end
        local x, _, z = getWorldTranslation(self.rootNode)
        local px, _, pz = getWorldTranslation(v.rootNode)
        return MathUtil.vector2Length(px - x, pz - z) <= spec.palletDistance
    end
    if spec.palletSearchTime == nil or g_time >= spec.palletSearchTime or (pallet ~= nil and not isValid(pallet, unit)) then
        spec.palletSearchTime = g_time + SprayDroneStation.PALLET_SEARCH_TIME
        pallet, unit = nil, nil
        local farmId = self:getOwnerFarmId()
        local vehicles = g_currentMission.vehicleSystem ~= nil and g_currentMission.vehicleSystem.vehicles or {}
        for _, v in ipairs(vehicles) do
            local isPallet = v.spec_pallet ~= nil or (v.typeName ~= nil and string.find(string.lower(v.typeName), "pallet", 1, true) ~= nil)
            if pallet == nil and v ~= self and isPallet and v.spec_fillUnit ~= nil and g_currentMission.accessHandler:canFarmAccess(farmId, v) then
                for i = 1, #v.spec_fillUnit.fillUnits do
                    if pallet == nil and isValid(v, i) then
                        pallet, unit = v, i
                    end
                end
            end
        end
        spec.transferPallet, spec.transferPalletUnit = pallet, unit
    end
    return pallet, unit
end

-- Přečerpávání (server), nejvýš drainRate / palletRate l/s; skončí samo, když není co nebo kam přečerpat.
function SprayDroneStation.updateTransfer(self, dt)
    local spec = SprayDroneDrones.getRoot(self)
    if spec.transferMode == SprayDroneStation.TRANSFER_NONE then
        return
    end
    SprayDroneDrones.runAs(self, spec.transferDrone or 1, SprayDroneStation.updateTransferDrone, dt)
end

-- Přečerpávání v kontextu dronu, kterého se týká (vypouštění nádrže dronu), nebo kteréhokoli (do IBC).
function SprayDroneStation.updateTransferDrone(self, dt)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local mode = spec.transferMode
    if mode == SprayDroneStation.TRANSFER_NONE then
        return
    end
    if not SprayDroneStation.getCanTransfer(self, mode) or not SprayDroneStation.getHasPower(self) then
        spec.transferMode = SprayDroneStation.TRANSFER_NONE
        self:raiseDirtyFlags(spec.dirtyFlag)
        return
    end
    local s = dt * 0.001
    local farmId = self:getOwnerFarmId()
    if mode == SprayDroneStation.TRANSFER_DRAIN_DRONE then
        local amount = math.min(spec.drainRate * s, spec.droneFillLevel)
        local added = self:addFillUnitFillLevel(farmId, spec.fillUnitIndex, amount, spec.droneFillType, ToolType.UNDEFINED, nil)
        spec.droneFillLevel = math.max(spec.droneFillLevel - added, 0)
        if spec.droneFillLevel <= 0.001 then
            spec.droneFillLevel = 0
            spec.droneFillType = FillType.UNKNOWN
        end
    else
        local pallet, unit = SprayDroneStation.getTransferPallet(self)
        local fillType = self:getFillUnitFillType(spec.fillUnitIndex)
        local amount = math.min(spec.palletRate * s, self:getFillUnitFillLevel(spec.fillUnitIndex), pallet:getFillUnitFreeCapacity(unit))
        local moved = pallet:addFillUnitFillLevel(farmId, unit, amount, fillType, ToolType.UNDEFINED, nil)
        if moved > 0 then
            self:addFillUnitFillLevel(farmId, spec.fillUnitIndex, -moved, fillType, ToolType.UNDEFINED, nil)
        end
    end
    spec.transferSyncTimer = spec.transferSyncTimer - dt
    if spec.transferSyncTimer <= 0 then
        spec.transferSyncTimer = SprayDroneStation.POWER_SYNC_TIME
        self:raiseDirtyFlags(spec.dirtyFlag)
    end
end

function SprayDroneStation.actionEventDrainDrone(self, actionName, inputValue, callbackState, isAnalog)
    local spec = SprayDroneDrones.getRoot(self)
    local mode = SprayDroneStation.TRANSFER_DRAIN_DRONE
    if spec.transferMode == mode then
        self:setSprayDroneTransfer(SprayDroneStation.TRANSFER_STOP)
        return
    end
    local k = SprayDroneStation.pickDrainDrone(self)
    if k ~= nil and not SprayDroneStation.showNoPowerWarning(self) then
        self:setSprayDroneTransfer(mode, nil, k)
    end
end

function SprayDroneStation.actionEventPumpToPallet(self, actionName, inputValue, callbackState, isAnalog)
    local spec = self[SprayDroneStation.SPEC_NAME]
    local mode = SprayDroneStation.TRANSFER_TO_PALLET
    if spec.transferMode ~= mode and self:getFillUnitFillLevel(spec.fillUnitIndex) <= 0.001 then
        return
    end
    if spec.transferMode ~= mode and SprayDroneStation.getTransferPallet(self) == nil then
        g_currentMission:showBlinkingWarning(string.format(g_i18n:getText("sdt_warning_noPallet"), spec.palletDistance), 2500)
        return
    end
    if spec.transferMode ~= mode and SprayDroneStation.showNoPowerWarning(self) then
        return
    end
    self:setSprayDroneTransfer(spec.transferMode == mode and SprayDroneStation.TRANSFER_STOP or mode)
end

-- Čerpadlo bez proudu: ukáže proč (vypnutá centrála / bez nafty) a vrátí true; s proudem false.
function SprayDroneStation.showNoPowerWarning(self)
    if SprayDroneStation.getHasPower(self) then
        return false
    end
    g_currentMission:showBlinkingWarning(string.format(g_i18n:getText("sdt_warning_noPower"),
        g_i18n:getText(SprayDroneStation.getNoPowerTextKey(self))), 2500)
    return true
end

-- Řádek do F1 nápovědy, když se přečerpává; jinak nil.
function SprayDroneStation.getTransferText(self)
    local spec = SprayDroneDrones.getRoot(self)
    if spec.transferMode == SprayDroneStation.TRANSFER_DRAIN_DRONE then
        local d = SprayDroneDrones.getSpec(self, spec.transferDrone or 1) or spec
        return string.format(g_i18n:getText("sdt_hud_draining"), spec.drainRate * 60, d.droneFillLevel)
    elseif spec.transferMode == SprayDroneStation.TRANSFER_TO_PALLET then
        return string.format(g_i18n:getText("sdt_hud_pumpingToPallet"), spec.palletRate * 60, self:getFillUnitFillLevel(spec.fillUnitIndex))
    end
    return nil
end
